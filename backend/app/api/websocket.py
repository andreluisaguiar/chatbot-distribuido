# backend/app/api/websocket.py

from fastapi import APIRouter, WebSocket, WebSocketDisconnect # type: ignore
import json
import time
import uuid
from ..services.rabbitmq_service import publish_message
from ..services.database_service import AsyncSessionLocal, save_message 
from sqlalchemy.ext.asyncio import AsyncSession # type: ignore

router = APIRouter()

# Gerenciador de conexões ativas por ID de sessão (crucial para SD)
class ConnectionManager:
    def __init__(self):
        # Mapeia user_id (session) para a conexão WebSocket ativa
        self.active_connections: dict[str, WebSocket] = {}

    async def connect(self, user_id: str, websocket: WebSocket):
        await websocket.accept()
        self.active_connections[user_id] = websocket
        print(f" [WS] Usuário {user_id} conectado.")

    def disconnect(self, user_id: str):
        if user_id in self.active_connections:
            del self.active_connections[user_id]
            print(f" [WS] Usuário {user_id} desconectado.")

    async def send_personal_message(self, message: str, user_id: str):
        """Envia mensagem de volta para um usuário específico (Resposta do Bot)."""
        if user_id in self.active_connections:
            # Envia a mensagem (geralmente JSON stringificado)
            await self.active_connections[user_id].send_text(message)

manager = ConnectionManager()

@router.websocket("/ws/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: str):

    try:
        uuid.UUID(user_id)
    except ValueError:
        await websocket.close(code=1008, reason="ID de usuário/sessão inválido.")
        return
        
    await manager.connect(user_id, websocket)
    
    try:
        while True:
            # 1. Recebe a mensagem do Frontend
            data = await websocket.receive_text()
            
            # --- Persistência (Database) ---
            # O API Gateway salva a mensagem do usuário
            async with AsyncSessionLocal() as db_session:
                success = await save_message(db_session, user_id, "USER", data)
                if not success:
                    print(" [DB] Aviso: Falha ao salvar mensagem do usuário.")

            # Formato de mensagem para a fila (JSON)
            message_data = {
                "user_id": user_id,
                "content": data,
                "timestamp_sent": time.time()
            }
            
            # 2. Publica a mensagem na fila q.ia_request (Produtor)
            publish_message(message_data) 
            
            # 3. Envia ACK imediato ao usuário (Feedback)
            await manager.send_personal_message(
                json.dumps({"sender": "SYSTEM", "content": "Mensagem recebida e em processamento..."}), 
                user_id
            )

    except WebSocketDisconnect:
        manager.disconnect(user_id)
    except Exception as e:
        print(f" [WS ERROR] Erro na comunicação WebSocket: {e}")
        manager.disconnect(user_id)