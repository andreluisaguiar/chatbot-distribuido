# backend/app/api/users.py

from fastapi import APIRouter, HTTPException, Depends, status # type: ignore
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials # type: ignore
from pydantic import BaseModel, Field, EmailStr # type: ignore
from typing import List, Optional, Annotated
import uuid
from datetime import datetime
from sqlalchemy.exc import IntegrityError # type: ignore
from sqlalchemy import select # type: ignore
from sqlalchemy.ext.asyncio import AsyncSession # type: ignore

from ..services.database_service import AsyncSessionLocal, get_db_session
from ..models.models import User, ChatSession
from ..services.auth_service import (
    get_password_hash,
    verify_password,
    create_access_token,
    decode_access_token
)

router = APIRouter()
security = HTTPBearer()

# ========== MODELS PYDANTIC ==========

class UserRegisterRequest(BaseModel):
    nome: str = Field(min_length=2, max_length=100)
    sobrenome: str = Field(min_length=2, max_length=100)
    email: EmailStr
    senha: str = Field(min_length=6, max_length=72)  # Bcrypt limita a 72 bytes

class UserLoginRequest(BaseModel):
    email: EmailStr
    senha: str

class UserUpdateRequest(BaseModel):
    nome: Optional[str] = Field(None, min_length=2, max_length=100)
    sobrenome: Optional[str] = Field(None, min_length=2, max_length=100)
    senha: Optional[str] = Field(None, min_length=6, max_length=72)  # Bcrypt limita a 72 bytes

class UserResponse(BaseModel):
    id: uuid.UUID
    nome: str
    sobrenome: str
    email: str
    username: Optional[str]
    is_active: str
    role: str
    last_login: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse
    session_id: uuid.UUID

class UserListResponse(BaseModel):
    users: List[UserResponse]
    total: int

# ========== DEPENDENCIES ==========

async def get_db(session: Annotated[AsyncSession, Depends(get_db_session)]):
    """Wrapper para obter sessão do banco"""
    async for db_session in get_db_session():
        yield db_session

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Annotated[AsyncSession, Depends(get_db)] = None
) -> User:
    """Obtém o usuário atual através do token JWT"""
    token = credentials.credentials
    payload = decode_access_token(token)
    
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido ou expirado",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user_id = payload.get("sub")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(User).where(User.id == uuid.UUID(user_id)))
        user = result.scalar_one_or_none()
    
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuário não encontrado",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if user.is_active != "ACTIVE":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Usuário inativo",
        )
    
    return user

# ========== ENDPOINTS ==========

@router.post("/users/register", response_model=LoginResponse, status_code=201)
async def register_user(payload: UserRegisterRequest):
    """Registra um novo usuário e retorna token de autenticação"""
    async with AsyncSessionLocal() as session:
        # Verifica se email já existe
        result = await session.execute(select(User).where(User.email == payload.email))
        existing_user = result.scalar_one_or_none()
        
        if existing_user:
            raise HTTPException(
                status_code=400,
                detail="Email já cadastrado"
            )
        
        user_id = uuid.uuid4()
        session_id = uuid.uuid4()
        
        # Gera username baseado no email se não fornecido
        username = payload.email.split("@")[0]
        
        try:
            # Cria usuário
            new_user = User(
                id=user_id,
                nome=payload.nome,
                sobrenome=payload.sobrenome,
                email=payload.email,
                senha_hash=get_password_hash(payload.senha),
                username=username,
                is_active="ACTIVE",
                role="USER"
            )
            
            # Cria sessão de chat
            new_session = ChatSession(
                id=session_id,
                user_id=user_id,
                status="ACTIVE"
            )
            
            session.add(new_user)
            await session.flush()
            session.add(new_session)
            await session.commit()
            
            # Recarrega o objeto do banco para obter os valores gerados (created_at, updated_at)
            await session.refresh(new_user)
            
            # Gera token JWT
            access_token = create_access_token(data={"sub": str(user_id)})
            
            # Atualiza last_login
            new_user.last_login = datetime.utcnow()
            await session.commit()
            await session.refresh(new_user)  # Recarrega novamente após atualizar last_login
            
            return LoginResponse(
                access_token=access_token,
                user=UserResponse.model_validate(new_user),
                session_id=session_id
            )
            
        except IntegrityError:
            await session.rollback()
            raise HTTPException(status_code=400, detail="Erro ao criar usuário (possível duplicação)")
        except Exception as e:
            await session.rollback()
            raise HTTPException(status_code=500, detail=f"Erro ao criar usuário: {str(e)}")

@router.post("/users/login", response_model=LoginResponse)
async def login_user(payload: UserLoginRequest):
    """Autentica usuário e retorna token"""
    async with AsyncSessionLocal() as session:
        # Busca usuário por email
        result = await session.execute(select(User).where(User.email == payload.email))
        user = result.scalar_one_or_none()
        
        if not user:
            raise HTTPException(
                status_code=401,
                detail="Email ou senha incorretos"
            )
        
        if user.is_active != "ACTIVE":
            raise HTTPException(
                status_code=403,
                detail="Usuário inativo"
            )
        
        # Verifica senha
        if not verify_password(payload.senha, user.senha_hash):
            raise HTTPException(
                status_code=401,
                detail="Email ou senha incorretos"
            )
        
        # Busca ou cria sessão ativa
        result = await session.execute(
            select(ChatSession).where(
                ChatSession.user_id == user.id,
                ChatSession.status == "ACTIVE"
            ).order_by(ChatSession.start_time.desc())
        )
        chat_session = result.scalar_one_or_none()
        
        if not chat_session:
            session_id = uuid.uuid4()
            new_session = ChatSession(
                id=session_id,
                user_id=user.id,
                status="ACTIVE"
            )
            session.add(new_session)
            await session.commit()
            chat_session = new_session
        else:
            session_id = chat_session.id
        
        # Atualiza last_login
        user.last_login = datetime.utcnow()
        await session.commit()
        await session.refresh(user)  # Recarrega para obter valores atualizados
        
        # Gera token JWT
        access_token = create_access_token(data={"sub": str(user.id)})
        
        return LoginResponse(
            access_token=access_token,
            user=UserResponse.model_validate(user),
            session_id=session_id
        )

@router.get("/users/me", response_model=UserResponse)
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    """Retorna informações do usuário autenticado"""
    return UserResponse.model_validate(current_user)

@router.put("/users/me", response_model=UserResponse)
async def update_current_user(
    payload: UserUpdateRequest,
    current_user: User = Depends(get_current_user)
):
    """Atualiza informações do usuário autenticado"""
    if payload.nome:
        current_user.nome = payload.nome
    if payload.sobrenome:
        current_user.sobrenome = payload.sobrenome
    if payload.senha:
        current_user.senha_hash = get_password_hash(payload.senha)
    
    current_user.updated_at = datetime.utcnow()
    
    async with AsyncSessionLocal() as session:
        session.add(current_user)
        try:
            await session.commit()
            await session.refresh(current_user)
            return UserResponse.model_validate(current_user)
        except Exception as e:
            await session.rollback()
            raise HTTPException(status_code=500, detail=f"Erro ao atualizar usuário: {str(e)}")

@router.get("/users", response_model=UserListResponse)
async def list_users(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_user)
):
    """Lista todos os usuários (requer autenticação)"""
    async with AsyncSessionLocal() as session:
        # Conta total
        result = await session.execute(select(User))
        total = len(result.scalars().all())
        
        # Busca com paginação
        result = await session.execute(
            select(User).offset(skip).limit(limit)
        )
        users = result.scalars().all()
        
        return UserListResponse(
            users=[UserResponse.model_validate(user) for user in users],
            total=total
        )

@router.get("/users/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: uuid.UUID,
    current_user: User = Depends(get_current_user)
):
    """Obtém informações de um usuário específico"""
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        
        if not user:
            raise HTTPException(status_code=404, detail="Usuário não encontrado")
        
        return UserResponse.model_validate(user)

@router.delete("/users/me")
async def delete_current_user(
    current_user: User = Depends(get_current_user)
):
    """Desativa (soft delete) o usuário autenticado"""
    current_user.is_active = "INACTIVE"
    current_user.updated_at = datetime.utcnow()
    
    async with AsyncSessionLocal() as session:
        session.add(current_user)
        try:
            await session.commit()
            return {"message": "Usuário desativado com sucesso"}
        except Exception as e:
            await session.rollback()
            raise HTTPException(status_code=500, detail=f"Erro ao desativar usuário: {str(e)}")
