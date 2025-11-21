# backend/tests/unit/test_database_service.py

import pytest # type: ignore
import pytest_asyncio # type: ignore
import uuid
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession # type: ignore
from sqlalchemy.orm import sessionmaker # type: ignore
from sqlalchemy.future import select # type: ignore
from sqlalchemy import text # type: ignore
from app.services.database_service import Base, save_message
from app.models.models import User, Message, ChatSession

# --- Setup de Ambiente de Teste (DB em Memória) ---
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

@pytest_asyncio.fixture
async def async_session_test():
    # 1. Cria o Engine com evento para habilitar Foreign Keys em cada conexão
    def enable_foreign_keys(dbapi_conn, connection_record):
        dbapi_conn.execute("PRAGMA foreign_keys=ON")
    
    engine = create_async_engine(
        TEST_DATABASE_URL, 
        echo=False,
        connect_args={"check_same_thread": False}
    )
    
    # Registra evento para habilitar Foreign Keys em cada conexão
    from sqlalchemy import event
    @event.listens_for(engine.sync_engine, "connect")
    def set_sqlite_pragma(dbapi_conn, connection_record):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()
    
    # 2. Cria as tabelas
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        
    AsyncSessionLocalTest = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

    # 3. Fornece a sessão para o teste e garante o rollback (limpeza)
    async with AsyncSessionLocalTest() as session:
        yield session
    
    # 4. Dropa todas as tabelas após todos os testes de arquivo
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


async def create_test_session(session: AsyncSession):
    user_id = uuid.uuid4()
    session_id = uuid.uuid4()
    
    # Cria objetos User e ChatSession
    test_user = User(id=user_id, username="test_user")
    test_session = ChatSession(id=session_id, user_id=user_id, status="ACTIVE")
    
    # Adiciona User primeiro e faz flush para garantir que está no DB antes de criar ChatSession
    session.add(test_user)
    await session.flush()  # Garante que o User é inserido antes do ChatSession
    
    session.add(test_session)
    await session.commit()
    return str(session_id)

@pytest.mark.asyncio
async def test_save_message_success(async_session_test: AsyncSession):
    
    # Pré-condição
    session_id = await create_test_session(async_session_test)
    test_content = "Usuário perguntou sobre Sistemas Distribuídos."
    
    # Ação
    success = await save_message(async_session_test, session_id, "USER", test_content)
    
    # Assertiva 1: A operação de salvamento deve ter sido bem-sucedida
    assert success is True
    
    # Assertiva 2: Verifica se a mensagem existe no DB (usando select future)
    stmt = select(Message).where(Message.session_id == uuid.UUID(session_id))
    result = await async_session_test.execute(stmt)
    saved_message = result.scalars().first()
    
    assert saved_message is not None
    assert saved_message.content == test_content
    assert saved_message.sender == "USER"

@pytest.mark.asyncio
async def test_save_message_invalid_session_id(async_session_test: AsyncSession):
    
    # Ação (usando um UUID que não existe no DB)
    invalid_session_id = str(uuid.uuid4())
    
    # O save_message deve lidar com a exceção (rollback) e retornar False
    success = await save_message(async_session_test, invalid_session_id, "BOT", "Resposta falsa.")
    
    assert success is False