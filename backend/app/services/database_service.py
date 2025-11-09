# backend/app/services/database_service.py

import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession # type: ignore
from sqlalchemy.orm import sessionmaker # type: ignore
from ..models.models import Base, User, ChatSession, Message
import uuid

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

async def save_message(session: AsyncSession, session_id: str, sender: str, content: str):

    try:
        user = await session.get(User, uuid.UUID(session_id))
        if not user:
             pass

        new_message = Message(
            session_id=uuid.UUID(session_id),
            sender=sender,
            content=content
        )
        session.add(new_message)
        await session.commit()
        return True
    except Exception as e:
        await session.rollback()
        print(f" [DB ERROR] Falha ao salvar mensagem: {e}")
        return False
