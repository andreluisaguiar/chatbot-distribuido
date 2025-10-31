# backend/app/main.py

from fastapi import FastAPI, HTTPException # pyright: ignore[reportMissingImports]
from pydantic import BaseModel # pyright: ignore[reportMissingImports]
import uuid
import time
# Importar o serviço que acabamos de criar
from .services.rabbitmq_service import publish_message 

app = FastAPI(title="Chatbot API Gateway")

# Modelo de dados Pydantic para a entrada da requisição
class ChatMessage(BaseModel):
    user_id: str
    message: str

# Rota principal para receber mensagens do usuário
@app.post("/api/v1/chat")
async def send_chat_message(msg: ChatMessage):
    
    # 1. Gerar ID da Mensagem (UUID, bom para SD)
    message_id = str(uuid.uuid4())
    
    # 2. Preparar dados para a fila

    message_data = {
        "message_id": message_id,
        "session_id": msg.user_id, # Usando user_id como session_id simplificado
        "content": msg.message,
        "timestamp_sent": time.time() 
    }

    # 3. Publicar na Fila (Ação Assíncrona Principal)
    if publish_message(message_data):
        
        return {
            "status": "accepted",
            "message_id": message_id,
            "detail": "Mensagem enfileirada para processamento assíncrono."
        }
    else:
        raise HTTPException(
            status_code=503, 
            detail="Serviço de Mensageria (RabbitMQ) Indisponível."
        )

# Rota de health check
@app.get("/health")
def health_check():
    return {"status": "ok", "service": "API Gateway"}