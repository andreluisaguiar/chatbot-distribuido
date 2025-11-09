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
    username = Column(String(50), unique=True, nullable=False)
    created_at = Column(TIMESTAMP(timezone=True), default=func.now())

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
