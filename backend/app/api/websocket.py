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
            try:
                await self.active_connections[user_id].send_text(message)
                print(f" [WS] Mensagem enviada para {user_id}: {message[:50]}...")
            except Exception as e:
                print(f" [WS ERROR] Erro ao enviar mensagem para {user_id}: {e}")
                # Remove conexão inválida
                if user_id in self.active_connections:
                    del self.active_connections[user_id]
        else:
            print(f" [WS WARNING] Usuário {user_id} não está conectado. Conexões ativas: {list(self.active_connections.keys())}")

manager = ConnectionManager()