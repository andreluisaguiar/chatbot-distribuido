from fastapi import WebSocket # type: ignore

# Gerenciador de conexões ativas por ID de sessão
class ConnectionManager:
    def __init__(self):
        self.active_connections: dict[str, WebSocket] = {}

    async def connect(self, user_id: str, websocket: WebSocket):
        # WebSocket já foi aceito no endpoint, apenas registra a conexão
        self.active_connections[user_id] = websocket
        print(f" [WS] Usuário {user_id} conectado.")

    def disconnect(self, user_id: str):
        if user_id in self.active_connections:
            del self.active_connections[user_id]
            print(f" [WS] Usuário {user_id} desconectado.")

    async def send_personal_message(self, message: str, user_id: str):
        if user_id in self.active_connections:
            await self.active_connections[user_id].send_text(message)

manager = ConnectionManager()