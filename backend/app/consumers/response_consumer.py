# backend/app/consumers/response_consumer.py

import pika # type: ignore
import os
import json
import threading
import asyncio
from ..api.websocket import manager # Importa o ConnectionManager que gerencia as conexões WS

# --- Configurações (Lidas do .env) ---
RABBITMQ_HOST = os.getenv("RABBITMQ_HOST", "rabbitmq")
RABBITMQ_USER = os.getenv("RABBITMQ_USER", "user")
RABBITMQ_PASS = os.getenv("RABBITMQ_PASS", "password")
RESPONSE_QUEUE_NAME = 'q.ia_response'
RESPONSE_EXCHANGE_NAME = 'x.chat_responses' # Nova Exchange para Respostas

def callback(ch, method, properties, body):
    """
    Função chamada quando uma resposta processada é recebida do Worker.
    """
    try:
        response_data = json.loads(body)
        user_id = response_data.get("user_id")
        bot_content = response_data.get("bot_content")
        
        print(f" [<-] Resposta recebida da fila para o usuário: {user_id}")

        # 1. Enviar a resposta via WebSocket
        # Como o callback do pika é síncrono, usamos asyncio.run() para executar
        # a função assíncrona de envio do WebSocket.
        if user_id:
            # Envia a mensagem do Bot de volta para o cliente específico
            asyncio.run(
                manager.send_personal_message(
                    json.dumps({"sender": "BOT", "content": bot_content}), 
                    user_id
                )
            )

        # 2. Confirmação (ACK)
        # Informa ao RabbitMQ que a mensagem foi entregue com sucesso.
        ch.basic_ack(delivery_tag=method.delivery_tag) 

    except Exception as e:
        print(f" [!!!] Erro no processamento da resposta (WS ou JSON): {e}")
        ch.basic_nack(delivery_tag=method.delivery_tag) # NACK para re-enfileirar, se o erro for recuperável

def start_response_consumer_thread():
    """Inicia a conexão e o consumo do RabbitMQ em uma thread separada."""
    credentials = pika.PlainCredentials(RABBITMQ_USER, RABBITMQ_PASS)
    parameters = pika.ConnectionParameters(
        host=RABBITMQ_HOST,
        credentials=credentials
    )

    try:
        connection = pika.BlockingConnection(parameters)
        channel = connection.channel()

        # Garante que a fila e a exchange de RESPOSTA existam (Resiliência/OS5)
        channel.exchange_declare(exchange=RESPONSE_EXCHANGE_NAME, exchange_type='direct', durable=True)
        channel.queue_declare(queue=RESPONSE_QUEUE_NAME, durable=True)
        channel.queue_bind(exchange=RESPONSE_EXCHANGE_NAME, queue=RESPONSE_QUEUE_NAME, routing_key=RESPONSE_QUEUE_NAME)
        
        print(f' [*] Consumidor de Respostas WS iniciado. Escutando: {RESPONSE_QUEUE_NAME}')
        
        channel.basic_consume(queue=RESPONSE_QUEUE_NAME, on_message_callback=callback)
        channel.start_consuming()

    except pika.exceptions.AMQPConnectionError as e:
        print(f" [!!!] Erro de conexão com RabbitMQ (Consumer de Resposta). Não foi possível iniciar.")
    except Exception as e:
        print(f" [!!!] Erro fatal no Consumer de Resposta: {e}")


def start_response_consumer():
    """Cria e inicia a thread do consumidor para não bloquear o servidor FastAPI."""
    consumer_thread = threading.Thread(target=start_response_consumer_thread, daemon=True)
    consumer_thread.start()
    print(" [API] Thread do Consumidor de Resposta iniciada.")