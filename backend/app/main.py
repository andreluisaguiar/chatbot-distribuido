from fastapi import FastAPI # type: ignore
from .api import chat, websocket 
from .consumers.response_consumer import start_response_consumer
from .services.database_service import init_db 
from contextlib import asynccontextmanager


@asynccontextmanager
async def lifespan(app: FastAPI):
    # --- Evento de STARTUP (Inicialização dos Serviços) ---
    
    # 1. Inicializa o Banco de Dados (Cria tabelas se não existirem)
    await init_db()
    print(" [API] Serviços de Banco de Dados inicializados.")
    
    # 2. Inicia o Consumidor de Respostas (RabbitMQ) em background
    start_response_consumer() 
    print(" [API] Consumidor de Respostas (RabbitMQ) iniciado.")
    
    print(" [API] Todos os serviços de startup concluídos.")
    yield
    # --- Evento de SHUTDOWN (Opcional) ---
    print(" [API] Desligamento da aplicação.")


app = FastAPI(
    title="Chatbot API Gateway",
    version="1.0.0",
    description="API Gateway com comunicação assíncrona (RabbitMQ) e em tempo real (WebSocket).",
    lifespan=lifespan # Associa o gerenciador de contexto ao ciclo de vida da aplicação
)

# Registra as rotas da API e WebSocket
app.include_router(chat.router, prefix="/api/v1", tags=["Chat"])
app.include_router(websocket.router) 

# Rota de health check
@app.get("/health")
async def health_check():
    return {"status": "ok", "message": "API Gateway está operacional"}