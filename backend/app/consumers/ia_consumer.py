# backend/app/consumers/ia_consumer.py

import pika # type: ignore
import os
import json
import time
import requests
import asyncio
import sys
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler # type: ignore
from threading import Thread # type: ignore
from prometheus_client import Counter, generate_latest, CONTENT_TYPE_LATEST # type: ignore

# Adiciona o diretório raiz ao path para imports absolutos
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.services.rabbitmq_service import get_rabbitmq_connection
from app.services.database_service import save_message, AsyncSessionLocal # Para persistência real

# --- Configurações (Lidas do .env) ---
RABBITMQ_HOST = os.getenv("RABBITMQ_HOST", "rabbitmq")
RABBITMQ_USER = os.getenv("RABBITMQ_USER", "user")
RABBITMQ_PASS = os.getenv("RABBITMQ_PASS", "password")
QUEUE_NAME = 'q.ia_request'
EXCHANGE_NAME = 'x.chat_requests'

RESPONSE_QUEUE_NAME = 'q.ia_response'
RESPONSE_EXCHANGE_NAME = 'x.chat_responses'

# Métricas de Throughput do Worker
messages_processed_total = Counter(
    'ia_worker_messages_processed_total',
    'Total de mensagens processadas pelo IA Worker',
    ['status']
)


class MetricsHandler(BaseHTTPRequestHandler):
    """Handler HTTP para expor métricas Prometheus"""
    
    def do_GET(self):
        if self.path == '/metrics':
            self.send_response(200)
            self.send_header('Content-Type', CONTENT_TYPE_LATEST)
            self.end_headers()
            self.wfile.write(generate_latest())
        else:
            self.send_response(404)
            self.end_headers()
    
    def log_message(self, format, *args):
        # Suprime logs do servidor HTTP
        pass


def start_metrics_server(port=8000):
    """Inicia servidor HTTP para expor métricas Prometheus"""
    try:
        server = HTTPServer(('0.0.0.0', port), MetricsHandler)
        print(f" [METRICS] Servidor de métricas iniciado na porta {port}")
        server.serve_forever()
    except OSError as e:
        print(f" [METRICS ERROR] Não foi possível iniciar servidor na porta {port}: {e}")
        # Tenta porta alternativa
        alt_port = 8001
        try:
            server = HTTPServer(('0.0.0.0', alt_port), MetricsHandler)
            print(f" [METRICS] Servidor de métricas iniciado na porta alternativa {alt_port}")
            server.serve_forever()
        except Exception as e2:
            print(f" [METRICS ERROR] Falha ao iniciar servidor de métricas: {e2}")

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
        
        # 4. Registra métrica de throughput (mensagem processada com sucesso)
        messages_processed_total.labels(status='success').inc()
        
        # 5. Confirmação (ACK)
        ch.basic_ack(delivery_tag=method.delivery_tag) 

    except Exception as e:
        print(f" [!!!] Erro no processamento do Worker: {e}. Rejeitando mensagem.")
        # Registra métrica de falha
        messages_processed_total.labels(status='error').inc()
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
    # Inicia servidor de métricas em thread separada
    metrics_port = int(os.getenv("METRICS_PORT", "8000"))
    metrics_thread = Thread(target=start_metrics_server, args=(metrics_port,), daemon=True)
    metrics_thread.start()
    
    # Inicia consumo de mensagens
    start_consuming()