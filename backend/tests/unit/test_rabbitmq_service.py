import pytest # type: ignore
from unittest.mock import patch, MagicMock
import json
import pika.exceptions # type: ignore
from app.services.rabbitmq_service import publish_message, QUEUE_NAME, EXCHANGE_NAME

# Mocka a função BlockingConnection para simular o comportamento do RabbitMQ
@patch('app.services.rabbitmq_service.pika.BlockingConnection') 
def test_publish_message_success(mock_connection):

    mock_conn_instance = mock_connection.return_value
    mock_channel = mock_conn_instance.channel.return_value
    
    test_data = {"user_id": "test_ws", "content": "Hello"}
    
    # Ação
    result = publish_message(test_data)
    
    # 1. Verifica se a exchange e a fila foram declaradas
    mock_channel.exchange_declare.assert_called_once_with(
        exchange=EXCHANGE_NAME, exchange_type='direct', durable=True
    )
    mock_channel.queue_declare.assert_called_once_with(
        queue=QUEUE_NAME, durable=True
    )
    
    # 2. Verifica se a mensagem foi publicada corretamente
    mock_channel.basic_publish.assert_called_once()
    
    # 3. Verifica o modo de entrega (Resiliência: PERSISTENT_DELIVERY_MODE=2)
    args, kwargs = mock_channel.basic_publish.call_args
    assert kwargs['body'] == json.dumps(test_data)
    assert kwargs['properties'].delivery_mode == 2
    
    # 4. Verifica o resultado
    assert result is True

@patch('app.services.rabbitmq_service.pika.BlockingConnection', 
       side_effect=pika.exceptions.AMQPConnectionError)
def test_publish_message_connection_failure(mock_connection):

    test_data = {"user_id": "test_ws", "content": "Hello"}
    
    result = publish_message(test_data)
    
    # A conexão foi tentada, mas falhou
    mock_connection.assert_called_once()
    
    # O resultado deve ser False (indicando falha no serviço)
    assert result is False