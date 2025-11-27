from sqlalchemy import Column, String, TIMESTAMP, ForeignKey, Text # type: ignore
from sqlalchemy.dialects.postgresql import UUID # type: ignore
from sqlalchemy.ext.declarative import declarative_base # type: ignore
from sqlalchemy.sql import func # type: ignore
import uuid

# Define a base para as classes declarativas
Base = declarative_base()

class User(Base):
    __tablename__ = 'users'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    nome = Column(String(100), nullable=False)
    sobrenome = Column(String(100), nullable=False)
    email = Column(String(255), unique=True, nullable=False, index=True)
    senha_hash = Column(String(255), nullable=False)  # Hash da senha (bcrypt)
    username = Column(String(50), unique=True, nullable=True)  # Opcional, pode ser gerado
    is_active = Column(String(10), default='ACTIVE')  # ACTIVE ou INACTIVE
    role = Column(String(20), default='USER')  # USER, ADMIN, etc.
    last_login = Column(TIMESTAMP(timezone=True), nullable=True)
    created_at = Column(TIMESTAMP(timezone=True), default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), default=func.now(), onupdate=func.now())

class ChatSession(Base):
    __tablename__ = 'chat_sessions'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    start_time = Column(TIMESTAMP(timezone=True), default=func.now())
    end_time = Column(TIMESTAMP(timezone=True), nullable=True)
    status = Column(String(20), default='ACTIVE')

class Message(Base):
    __tablename__ = 'messages'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(UUID(as_uuid=True), ForeignKey('chat_sessions.id', ondelete='CASCADE'), nullable=False)
    sender = Column(String(10), nullable=False) # 'USER' ou 'BOT'
    content = Column(Text, nullable=False)
    sent_at = Column(TIMESTAMP(timezone=True), default=func.now())
