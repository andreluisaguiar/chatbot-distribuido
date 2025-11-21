# backend/app/services/metrics_service.py

from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST # type: ignore
from starlette.middleware.base import BaseHTTPMiddleware # type: ignore
from starlette.requests import Request # type: ignore
from starlette.responses import Response # type: ignore
import time

# Métricas de Latência HTTP (exportadas para uso no main.py)
http_request_duration = Histogram(
    'http_request_duration_seconds',
    'Latência das requisições HTTP em segundos',
    ['method', 'endpoint', 'status_code'],
    buckets=[0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0]
)

# Métricas de Contagem de Requisições HTTP (exportadas para uso no main.py)
http_request_total = Counter(
    'http_requests_total',
    'Total de requisições HTTP',
    ['method', 'endpoint', 'status_code']
)

# Métricas de Latência WebSocket
websocket_message_duration = Histogram(
    'websocket_message_duration_seconds',
    'Latência de processamento de mensagens WebSocket em segundos',
    ['action'],
    buckets=[0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0]
)

# Métricas de Contagem de Mensagens WebSocket
websocket_messages_total = Counter(
    'websocket_messages_total',
    'Total de mensagens WebSocket processadas',
    ['action']
)


class MetricsMiddleware(BaseHTTPMiddleware):
    """Middleware para coletar métricas de latência e contagem de requisições HTTP"""
    
    async def dispatch(self, request: Request, call_next):
        # Ignora o endpoint /metrics para evitar loop de métricas
        if request.url.path == "/metrics":
            return await call_next(request)
        
        # Ignora requisições WebSocket (não são HTTP normais)
        if request.headers.get("upgrade", "").lower() == "websocket":
            return await call_next(request)
        
        start_time = time.time()
        
        # Processa a requisição
        response = await call_next(request)
        
        # Calcula a latência
        duration = time.time() - start_time
        
        # Extrai informações da requisição
        method = request.method
        endpoint = request.url.path
        status_code = response.status_code
        
        # Registra as métricas
        http_request_duration.labels(
            method=method,
            endpoint=endpoint,
            status_code=status_code
        ).observe(duration)
        
        http_request_total.labels(
            method=method,
            endpoint=endpoint,
            status_code=status_code
        ).inc()
        
        return response


def get_metrics():
    """Retorna as métricas no formato Prometheus"""
    return generate_latest()

