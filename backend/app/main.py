from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Response # type: ignore
import json
import time
import uuid
from contextlib import asynccontextmanager

# Importar Rotas e Serviços
from .api import chat
from .consumers.response_consumer import start_response_consumer
from .services.database_service import init_db, AsyncSessionLocal, save_message
from .services.rabbitmq_service import publish_message
from .api.websocket import manager # Importa apenas o gerenciador de conexão (manager)
from .services.metrics_service import get_metrics, websocket_message_duration, websocket_messages_total
from prometheus_client import CONTENT_TYPE_LATEST # type: ignore


@asynccontextmanager
async def lifespan(app: FastAPI):
    # --- Evento de STARTUP ---
    await init_db()
    print(" [API] Serviços de Banco de Dados inicializados.")
    
    start_response_consumer() 
    print(" [API] Consumidor de Respostas (RabbitMQ) iniciado.")
    
    print(" [API] Todos os serviços de startup concluídos.")
    yield
    # --- Evento de SHUTDOWN ---
    print(" [API] Desligamento da aplicação.")


app = FastAPI(
    title="Chatbot API Gateway",
    version="1.0.0",
    description="API Gateway com comunicação assíncrona (RabbitMQ) e em tempo real (WebSocket).",
    lifespan=lifespan
)

# Nota: Middleware de métricas removido temporariamente para evitar conflito com WebSocket
# As métricas WebSocket são coletadas diretamente no endpoint

# Registra rotas REST com prefixo
app.include_router(chat.router, prefix="/api/v1", tags=["Chat"])

# Rota de health check
@app.get("/health")
async def health_check():
    return {"status": "ok", "message": "API Gateway está operacional"}

# Endpoint de métricas para Prometheus
@app.get("/metrics")
async def metrics():
    return Response(content=get_metrics(), media_type=CONTENT_TYPE_LATEST)


# --- ROTA WEB SOCKET FINAL E DIRETA ---
@app.websocket("/ws_chat")
async def websocket_endpoint(websocket: WebSocket):
    # Aceita a conexão WebSocket primeiro
    await websocket.accept()
    
    user_id = websocket.query_params.get("id") 
    
    if not user_id:
        await websocket.close(code=1008, reason="ID de usuário ausente.")
        return
    
    # Validação: aceita qualquer string não vazia como user_id
    # (o frontend gera IDs no formato "user-xxx-timestamp")
    if not user_id.strip():
        await websocket.close(code=1008, reason="ID de usuário/sessão inválido.")
        return
        
    await manager.connect(user_id, websocket)
    
    try:
        while True:
            data = await websocket.receive_text()
            
            # Inicia medição de latência para mensagem WebSocket
            start_time = time.time()
            
            # --- Persistência (Database) ---
            async with AsyncSessionLocal() as db_session:
                # O comando save_message deve ser importado
                success = await save_message(db_session, user_id, "USER", data)

            # Formato de mensagem para a fila (JSON)
            message_data = {
                "user_id": user_id,
                "content": data,
                "timestamp_sent": time.time()
            }
            
            publish_message(message_data) 
            
            # 3. Envia ACK imediato
            await manager.send_personal_message(
                json.dumps({"sender": "SYSTEM", "content": "Mensagem recebida e em processamento..."}), 
                user_id
            )
            
            # Registra métricas de WebSocket
            duration = time.time() - start_time
            websocket_message_duration.labels(action="process_message").observe(duration)
            websocket_messages_total.labels(action="process_message").inc()

    except WebSocketDisconnect:
        manager.disconnect(user_id)
    except Exception as e:
        print(f" [WS ERROR] Erro na comunicação WebSocket: {e}")
        manager.disconnect(user_id)