# backend/app/services/database_service.py

import os
from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession # type: ignore
from sqlalchemy.orm import sessionmaker # type: ignore
from ..models.models import Base, User, ChatSession, Message
import uuid
from sqlalchemy.exc import IntegrityError # type: ignore

# Carrega variáveis de ambiente do arquivo .env
load_dotenv()

# Lendo configurações do .env
POSTGRES_USER = os.getenv("POSTGRES_USER")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD")
POSTGRES_HOST = os.getenv("POSTGRES_HOST")
POSTGRES_DB = os.getenv("POSTGRES_DB")

# URL de Conexão (usando driver assíncrono: asyncpg)
DATABASE_URL = f"postgresql+asyncpg://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:5432/{POSTGRES_DB}"

# Configuração do Engine
engine = create_async_engine(DATABASE_URL, echo=False)

# Criador de Sessão (Usado para obter uma nova sessão de DB)
AsyncSessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False, # Importante para assincronia
)

async def init_db():
    async with engine.begin() as conn:

        await conn.run_sync(Base.metadata.create_all)
        print(" [DB] Tabelas verificadas/criadas no PostgreSQL.")

async def get_db_session() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        yield session

def normalize_session_uuid(session_id: str) -> uuid.UUID:
    """
    Converte qualquer identificador de sessão em um UUID.
    - Se já for um UUID válido, retorna o próprio.
    - Caso contrário, gera um UUID determinístico usando uuid5.
    """
    try:
        return uuid.UUID(session_id)
    except ValueError:
        return uuid.uuid5(uuid.NAMESPACE_DNS, session_id)


async def ensure_user_and_session(session: AsyncSession, session_uuid: uuid.UUID):
    """
    Garante que exista um usuário e uma sessão no banco para o UUID informado.
    """
    user = await session.get(User, session_uuid)
    if not user:
        session.add(User(id=session_uuid, username=f"user_{str(session_uuid)[:8]}"))
        await session.flush()  # garante que o usuário existe antes da sessão

    chat_session = await session.get(ChatSession, session_uuid)
    if not chat_session:
        session.add(ChatSession(id=session_uuid, user_id=session_uuid, status="ACTIVE"))
        await session.flush()


async def save_message(session: AsyncSession, session_id: str, sender: str, content: str):
    try:
        session_uuid = normalize_session_uuid(session_id)

        # garante usuário e sessão antes de inserir a mensagem
        await ensure_user_and_session(session, session_uuid)

        new_message = Message(
            session_id=session_uuid,
            sender=sender,
            content=content
        )
        session.add(new_message)
        await session.commit()
        return True
    except IntegrityError:
        await session.rollback()
        # retorno esperado em caso de falha de integridade (ex: FK inválida - session_id não existe)
        return False
    except Exception as e:
        await session.rollback()
        print(f" [DB ERROR] Falha ao salvar mensagem: {e}")
        return False
