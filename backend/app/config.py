# backend/app/config.py
"""
Configurações da aplicação para diferentes ambientes
"""
import os
from typing import List

class Settings:
    """Configurações da aplicação"""
    
    # Ambiente
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    
    # CORS - Origens permitidas
    # Em produção, defina as URLs reais do frontend
    CORS_ORIGINS: List[str] = os.getenv(
        "CORS_ORIGINS",
        "http://localhost:3000,http://localhost:3001"
    ).split(",")
    
    # Se CORS_ORIGINS não estiver definido e estiver em desenvolvimento, permite tudo
    if ENVIRONMENT == "development" and not os.getenv("CORS_ORIGINS"):
        CORS_ORIGINS = ["*"]
    
    # Backend
    BACKEND_HOST: str = os.getenv("BACKEND_HOST", "0.0.0.0")
    BACKEND_PORT: int = int(os.getenv("BACKEND_PORT", "8000"))
    
    # PostgreSQL
    POSTGRES_HOST: str = os.getenv("POSTGRES_HOST", os.getenv("PGHOST", "postgres"))
    POSTGRES_PORT: int = int(os.getenv("POSTGRES_PORT", os.getenv("PGPORT", "5432")))
    POSTGRES_USER: str = os.getenv("POSTGRES_USER", os.getenv("PGUSER", "user"))
    POSTGRES_PASSWORD: str = os.getenv("POSTGRES_PASSWORD", os.getenv("PGPASSWORD", "password"))
    POSTGRES_DB: str = os.getenv("POSTGRES_DB", os.getenv("PGDATABASE", "db_chatbot"))
    
    # Se DATABASE_URL estiver disponível (Railway, Render), use ela
    DATABASE_URL: str = os.getenv("DATABASE_URL", "")
    if DATABASE_URL:
        # Extrai informações da DATABASE_URL se necessário
        pass
    
    # RabbitMQ
    RABBITMQ_URL: str = os.getenv("RABBITMQ_URL", "")
    RABBITMQ_HOST: str = os.getenv("RABBITMQ_HOST", "rabbitmq")
    RABBITMQ_PORT: int = int(os.getenv("RABBITMQ_PORT", "5672"))
    RABBITMQ_USER: str = os.getenv("RABBITMQ_USER", "user")
    RABBITMQ_PASS: str = os.getenv("RABBITMQ_PASS", "password")
    
    # Redis
    REDIS_HOST: str = os.getenv("REDIS_HOST", "redis")
    REDIS_PORT: int = int(os.getenv("REDIS_PORT", "6379"))
    REDIS_URL: str = os.getenv("REDIS_URL", "")
    
    # API de IA
    AI_API_KEY: str = os.getenv("AI_API_KEY", "")
    AI_MODEL: str = os.getenv("AI_MODEL", "gpt-3.5-turbo")
    AI_API_URL: str = os.getenv("AI_API_URL", "")

# Instância global de configurações
settings = Settings()

