import pika # type: ignore
import os
import json
import time
import requests

# --- Configurações (Lidas do .env) ---
RABBITMQ_HOST = os.getenv("RABBITMQ_HOST", "rabbitmq")
RABBITMQ_USER = os.getenv("RABBITMQ_USER", "user")
RABBITMQ_PASS = os.getenv("RABBITMQ_PASS", "password")
QUEUE_NAME = 'q.ia_request'
EXCHANGE_NAME = 'x.chat_requests'

# Simulação da API Externa de IA (OS2)
def call_external_ai_api(prompt: str):

    print(f" [+] [WORKER] Processando IA para: '{prompt[:30]}...'")
    time.sleep(2) # Simula a latência (2 segundos)
    response_content = f"Resposta do Bot para '{prompt}'. Processado pelo Worker em {time.strftime('%H:%M:%S')}"
    return response_content

# --- Lógica de Callback e Consumo ---
def callback(ch, method, properties, body):

    try:
        message_data = json.loads(body)
        
        message_id = message_data.get("message_id")
        user_prompt = message_data.get("content")
        timestamp_sent = message_data.get("timestamp_sent")
        
        # 1. Processamento da IA (Etapa Lenta)
        bot_response = call_external_ai_api(user_prompt)
        
        # 2. Cálculo da Latência (OS4)
        process_time = time.time() - timestamp_sent
        print(f" [V] [WORKER] Processamento concluído (ID: {message_id}). Tempo: {process_time:.2f}s")
        
        # 3. Confirmação (ACK)
        ch.basic_ack(delivery_tag=method.delivery_tag) 

    except Exception as e:
        print(f" [!] Erro no processamento do Worker: {e}")
        ch.basic_ack(delivery_tag=method.delivery_tag) # ACK for now

def start_consuming():

    credentials = pika.PlainCredentials(RABBITMQ_USER, RABBITMQ_PASS)
    parameters = pika.ConnectionParameters(
        host=RABBITMQ_HOST,
        credentials=credentials
    )

    try:
        connection = pika.BlockingConnection(parameters)
        channel = connection.channel()

        channel.exchange_declare(exchange=EXCHANGE_NAME, exchange_type='direct', durable=True)
        channel.queue_declare(queue=QUEUE_NAME, durable=True)
        channel.queue_bind(exchange=EXCHANGE_NAME, queue=QUEUE_NAME, routing_key=QUEUE_NAME)
        
        channel.basic_qos(prefetch_count=1)

        print(f' [*] Worker iniciado. Aguardando mensagens na fila {QUEUE_NAME}. Para sair, pressione CTRL+C')
        
        channel.basic_consume(queue=QUEUE_NAME, on_message_callback=callback)
        channel.start_consuming()

    except pika.exceptions.AMQPConnectionError as e:
        print(f" [!!!] Erro de conexão com RabbitMQ. Tentando reconectar em 5s: {e}")
        time.sleep(5)
        start_consuming()
    except KeyboardInterrupt:
        print('Worker desligado.')

if __name__ == '__main__':
    start_consuming()