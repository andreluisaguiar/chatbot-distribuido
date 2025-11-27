from fastapi import APIRouter, HTTPException # type: ignore
from pydantic import BaseModel, Field # type: ignore
import uuid
from sqlalchemy.exc import IntegrityError # type: ignore
from ..services.database_service import AsyncSessionLocal
from ..models.models import User, ChatSession

router = APIRouter()


class UserCreateRequest(BaseModel):
    username: str = Field(min_length=3, max_length=50)


class UserCreateResponse(BaseModel):
    user_id: uuid.UUID
    session_id: uuid.UUID
    username: str


@router.post("/users", response_model=UserCreateResponse, status_code=201)
async def create_user(payload: UserCreateRequest):
    user_id = uuid.uuid4()
    session_id = uuid.uuid4()

    async with AsyncSessionLocal() as session:
        try:
            new_user = User(id=user_id, username=payload.username)
            new_session = ChatSession(id=session_id, user_id=user_id, status="ACTIVE")

            session.add(new_user)
            await session.flush() # Garante que o usuário existe antes de criar a sessão
            session.add(new_session)
            await session.commit()

            return UserCreateResponse(
                user_id=user_id,
                session_id=session_id,
                username=payload.username
            )
        except IntegrityError:
            await session.rollback()
            raise HTTPException(status_code=400, detail="Nome de usuário já existe.")
        except Exception as e:
            await session.rollback()
            raise HTTPException(status_code=500, detail=f"Erro ao criar usuário: {e}")

