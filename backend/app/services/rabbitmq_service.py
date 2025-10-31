import pika # type: ignore
import os
import json

# Configuração de conexão do RabbitMQ (lendo do .env)
RABBITMQ_HOST = os.getenv("RABBITMQ_HOST", "rabbitmq")
RABBITMQ_PORT = int(os.getenv("RABBITMQ_PORT", 5672))
RABBITMQ_USER = os.getenv("RABBITMQ_USER", "user")
RABBITMQ_PASS = os.getenv("RABBITMQ_PASS", "password")

QUEUE_NAME = 'q.ia_request'
EXCHANGE_NAME = 'x.chat_requests'

def get_rabbitmq_connection():
    """Tenta estabelecer e retornar uma conexão com o RabbitMQ."""
    credentials = pika.PlainCredentials(RABBITMQ_USER, RABBITMQ_PASS)
    parameters = pika.ConnectionParameters(
        host=RABBITMQ_HOST,
        port=RABBITMQ_PORT,
        credentials=credentials,
        # Timeout para falha de conexão (boa prática em SD)
        connection_attempts=5, 
        retry_delay=5 
    )
    return pika.BlockingConnection(parameters)

def publish_message(message_data: dict):
    """
    Publica uma mensagem na Exchange do RabbitMQ para processamento assíncrono.
    """
    try:
        connection = get_rabbitmq_connection()
        channel = connection.channel()

        # 1. Declarar a Exchange (Garante que ela exista)
        channel.exchange_declare(
            exchange=EXCHANGE_NAME, 
            exchange_type='direct',
            durable=True # 'durable=True' para garantir que a Exchange sobreviva a reinicializações (Resiliência/OS5)
        )
        
        # 2. Declarar a Fila (Garante que ela exista)
        channel.queue_declare(
            queue=QUEUE_NAME, 
            durable=True # 'durable=True' para garantir que a Fila e mensagens sobrevivam (Resiliência/OS5)
        )
        
        # 3. Vincular a Fila à Exchange
        channel.queue_bind(
            exchange=EXCHANGE_NAME,
            queue=QUEUE_NAME,
            routing_key=QUEUE_NAME # Usamos o nome da fila como routing key
        )

        # 4. Publicar a Mensagem
        body = json.dumps(message_data)
        
        channel.basic_publish(
            exchange=EXCHANGE_NAME,
            routing_key=QUEUE_NAME,
            body=body,
            properties=pika.BasicProperties(
                delivery_mode=pika.spec.PERSISTENT_DELIVERY_MODE # Persistente: A mensagem sobreviverá a reinicialização do RabbitMQ (Resiliência/OS5)
            )
        )
        
        print(f" [x] Mensagem enviada para a fila: {QUEUE_NAME}")
        connection.close()
        return True

    except pika.exceptions.AMQPConnectionError as e:
        print(f" [!] ERRO: Não foi possível conectar ao RabbitMQ: {e}")
        return False
    except Exception as e:
        print(f" [!] ERRO ao publicar mensagem: {e}")
        return False