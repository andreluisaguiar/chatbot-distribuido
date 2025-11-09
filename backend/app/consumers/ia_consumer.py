# backend/app/consumers/ia_consumer.py

import pika # type: ignore
import os
import json
import time
import requests
import asyncio
from ..services.rabbitmq_service import get_rabbitmq_connection
from ..services.database_service import save_message_sync 
from ..services.database_service import save_message, AsyncSessionLocal # Para persistência real

# --- Configurações (Lidas do .env) ---
RABBITMQ_HOST = os.getenv("RABBITMQ_HOST", "rabbitmq")
RABBITMQ_USER = os.getenv("RABBITMQ_USER", "user")
RABBITMQ_PASS = os.getenv("RABBITMQ_PASS", "password")
QUEUE_NAME = 'q.ia_request'
EXCHANGE_NAME = 'x.chat_requests'

RESPONSE_QUEUE_NAME = 'q.ia_response'
RESPONSE_EXCHANGE_NAME = 'x.chat_responses'

# Simulação da API Externa de IA (OS2)
def call_external_ai_api(prompt: str):

    print(f" [+] [WORKER] Processando IA para: '{prompt[:30]}...'")
    time.sleep(2) # Simula a latência (2 segundos)
    response_content = f"Resposta do Bot para '{prompt}'. Processado pelo Worker em {time.strftime('%H:%M:%S')}"
    return response_content

# --- Lógica de Publicação de Resposta ---
def publish_response(user_id: str, bot_response: str):

    try:
        connection = get_rabbitmq_connection()
        channel = connection.channel()

        # Garante que a Exchange e a Fila de RESPOSTA existam (Resiliência/OS5)
        channel.exchange_declare(exchange=RESPONSE_EXCHANGE_NAME, exchange_type='direct', durable=True)
        channel.queue_declare(queue=RESPONSE_QUEUE_NAME, durable=True)
        channel.queue_bind(exchange=RESPONSE_EXCHANGE_NAME, queue=RESPONSE_QUEUE_NAME, routing_key=RESPONSE_QUEUE_NAME)

        response_payload = {
            "user_id": user_id,
            "bot_content": bot_response, 
            "timestamp_processed": time.time()
        }
        
        body = json.dumps(response_payload)
        
        channel.basic_publish(
            exchange=RESPONSE_EXCHANGE_NAME,
            routing_key=RESPONSE_QUEUE_NAME,
            body=body,
            properties=pika.BasicProperties(
                delivery_mode=pika.spec.PERSISTENT_DELIVERY_MODE
            )
        )
        
        print(f" [->] Resposta enviada para fila: {RESPONSE_QUEUE_NAME}")
        connection.close()
        return True

    except Exception as e:
        print(f" [!] ERRO ao publicar resposta na fila: {e}")
        return False

# --- Lógica de Callback e Consumo ---
def callback(ch, method, properties, body):

    try:
        message_data = json.loads(body)
        
        user_id = message_data.get("user_id")
        user_prompt = message_data.get("content")
        
        if not user_id or not user_prompt:
             print(" [!] Mensagem incompleta recebida. Ignorando.")
             ch.basic_ack(delivery_tag=method.delivery_tag)
             return

        # 1. Processamento da IA (Etapa Lenta)
        bot_response = call_external_ai_api(user_prompt)
        
        # 2. Persistência da Resposta do Bot
        print(f" [DB] Salvando resposta do BOT no PostgreSQL para usuário {user_id}...")
        
        async def save_bot_message_async():
             async with AsyncSessionLocal() as db_session:
                await save_message(db_session, user_id, "BOT", bot_response)

        # Executa a função assíncrona de forma síncrona
        asyncio.run(save_bot_message_async())
        
        # 3. Publicar a Resposta na Fila q.ia_response
        publish_response(user_id, bot_response)
        
        # 4. Confirmação (ACK)
        ch.basic_ack(delivery_tag=method.delivery_tag) 

    except Exception as e:
        print(f" [!!!] Erro no processamento do Worker: {e}. Rejeitando mensagem.")
        # Rejeita a mensagem para que ela volte à fila ou vá para uma DLQ
        ch.basic_nack(delivery_tag=method.delivery_tag) 


def start_consuming():
    """Conecta ao RabbitMQ e inicia o loop de consumo da fila de requisição."""
    credentials = pika.PlainCredentials(RABBITMQ_USER, RABBITMQ_PASS)
    parameters = pika.ConnectionParameters(
        host=RABBITMQ_HOST,
        credentials=credentials
    )

    try:
        connection = pika.BlockingConnection(parameters)
        channel = connection.channel()

        # Garante que a fila e a exchange existam (durable=True para Resiliência)
        channel.exchange_declare(exchange=EXCHANGE_NAME, exchange_type='direct', durable=True)
        channel.queue_declare(queue=QUEUE_NAME, durable=True)
        channel.queue_bind(exchange=EXCHANGE_NAME, queue=QUEUE_NAME, routing_key=QUEUE_NAME)
        
        # Fair dispatch (Qualidade de Serviço - QoS)
        channel.basic_qos(prefetch_count=1)

        print(f' [*] Worker IA iniciado. Aguardando mensagens na fila {QUEUE_NAME}.')
        
        channel.basic_consume(queue=QUEUE_NAME, on_message_callback=callback)
        channel.start_consuming()

    except pika.exceptions.AMQPConnectionError as e:
        print(f" [!!!] Erro de conexão com RabbitMQ. Tentando reconectar em 5s: {e}")
        time.sleep(5)
        start_consuming() # Tenta reconectar (Resiliência)
    except KeyboardInterrupt:
        print('Worker desligado.')

if __name__ == '__main__':
    start_consuming()