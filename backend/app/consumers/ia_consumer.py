# backend/app/consumers/ia_consumer.py

import pika # type: ignore
import os
import json
import time
import requests
import asyncio
import sys
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler # type: ignore
from threading import Thread # type: ignore
from prometheus_client import Counter, generate_latest, CONTENT_TYPE_LATEST # type: ignore
from dotenv import load_dotenv

# Tenta importar a biblioteca oficial do Google Gemini
try:
    from google import genai
    HAS_GOOGLE_GENAI = True
    print(" [INFO] Biblioteca 'google-genai' importada com sucesso!")
except ImportError as e:
    HAS_GOOGLE_GENAI = False
    print(f" [INFO] Biblioteca 'google-genai' não encontrada. Usando método HTTP direto. Erro: {e}")

# Força o flush imediato de stdout/stderr para Docker
sys.stdout.reconfigure(line_buffering=True)
sys.stderr.reconfigure(line_buffering=True)

# Carrega variáveis de ambiente do arquivo .env
load_dotenv()

# Adiciona o diretório raiz ao path para imports absolutos
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.services.rabbitmq_service import get_rabbitmq_connection
from app.services.database_service import save_message, AsyncSessionLocal # Para persistência real

# --- Configurações (Lidas do .env) ---
RABBITMQ_HOST = os.getenv("RABBITMQ_HOST", "rabbitmq")
RABBITMQ_USER = os.getenv("RABBITMQ_USER", "user")
RABBITMQ_PASS = os.getenv("RABBITMQ_PASS", "password")
QUEUE_NAME = 'q.ia_request'
EXCHANGE_NAME = 'x.chat_requests'

RESPONSE_QUEUE_NAME = 'q.ia_response'
RESPONSE_EXCHANGE_NAME = 'x.chat_responses'

# Configurações da API de IA
AI_API_KEY = os.getenv("AI_API_KEY")
AI_MODEL = os.getenv("AI_MODEL", "gpt-3.5-turbo")
AI_API_URL = os.getenv("AI_API_URL") 

# Detecta se é API Gemini baseado no modelo
IS_GEMINI = AI_MODEL.startswith("gemini") if AI_MODEL else False
# Detecta se é API DeepSeek baseado no modelo
IS_DEEPSEEK = AI_MODEL.startswith("deepseek") if AI_MODEL else False
# Detecta se é API Groq baseado no modelo (llama, mixtral, etc)
IS_GROQ = AI_MODEL.startswith("llama") or AI_MODEL.startswith("mixtral") or AI_MODEL.startswith("gemma") if AI_MODEL else False

# Prompt de sistema focado em apoio a estudos
SYSTEM_PROMPT = """
Você é o B.A.S.E. (Bot de Apoio a Sistemas e Estudos), um assistente virtual especializado na disciplina de Sistemas Distribuídos.
Seu nome é um acrônimo para "Basically Available, Soft state, Eventual consistency".

Suas diretrizes de comportamento:
1. IDENTIDADE: Você NÃO deve iniciar toda frase se apresentando. Apresente-se sempre na primeira mensgaem e se o usuário perguntar explicitamente "Quem é você?", "Qual seu nome?" ou na primeira mensagem da conversa.
2. FLUXO: Para perguntas de conteúdo (ex: "O que é RPC?"), vá direto para a explicação técnica, sem saudações longas.
3. REFERÊNCIAS: Sempre que possível, cite conceitos dos livros do Tanenbaum ou Coulouris.
4. DIDÁTICA: Explique termos complexos com analogias do mundo real.
5. OBJETIVO: Ajude o aluno a entender o "porquê" das coisas.
"""

# Métricas de Throughput do Worker
messages_processed_total = Counter(
    'ia_worker_messages_processed_total',
    'Total de mensagens processadas pelo IA Worker',
    ['status']
)


class MetricsHandler(BaseHTTPRequestHandler):
    """Handler HTTP para expor métricas Prometheus"""
    
    def do_GET(self):
        if self.path == '/metrics':
            self.send_response(200)
            self.send_header('Content-Type', CONTENT_TYPE_LATEST)
            self.end_headers()
            self.wfile.write(generate_latest())
        else:
            self.send_response(404)
            self.end_headers()
    
    def log_message(self, format, *args):
        # Suprime logs do servidor HTTP
        pass


def start_metrics_server(port=8000):
    """Inicia servidor HTTP para expor métricas Prometheus"""
    try:
        server = HTTPServer(('0.0.0.0', port), MetricsHandler)
        print(f" [METRICS] Servidor de métricas iniciado na porta {port}")
        server.serve_forever()
    except OSError as e:
        print(f" [METRICS ERROR] Não foi possível iniciar servidor na porta {port}: {e}")
        # Tenta porta alternativa
        alt_port = 8001
        try:
            server = HTTPServer(('0.0.0.0', alt_port), MetricsHandler)
            print(f" [METRICS] Servidor de métricas iniciado na porta alternativa {alt_port}")
            server.serve_forever()
        except Exception as e2:
            print(f" [METRICS ERROR] Falha ao iniciar servidor de métricas: {e2}")

# Chamada real à API Externa de IA
def call_external_ai_api(user_prompt: str):
    """
    Chama a API de IA (OpenAI ou compatível) para gerar resposta focada em estudos.
    
    Args:
        user_prompt: Mensagem do usuário
        
    Returns:
        Resposta gerada pela IA ou mensagem de erro
    """
    if not AI_API_KEY:
        error_msg = "Erro: AI_API_KEY não configurada. Configure a variável de ambiente AI_API_KEY."
        print(f" [!!!] {error_msg}")
        return error_msg
    
    api_type = "Groq" if IS_GROQ else ("DeepSeek" if IS_DEEPSEEK else ("Gemini" if IS_GEMINI else "OpenAI"))
    print(f" [+] [WORKER] Processando IA ({api_type}) para: '{user_prompt[:50]}...'")
    print(f" [+] [WORKER] Modelo: {AI_MODEL}, IS_GEMINI: {IS_GEMINI}, IS_DEEPSEEK: {IS_DEEPSEEK}, IS_GROQ: {IS_GROQ}, API_KEY presente: {bool(AI_API_KEY)}")
    
    try:
        # Determina URL e formato baseado no tipo de API
        if IS_GEMINI:
            # Tenta usar a biblioteca oficial do Google Gemini se disponível
            if HAS_GOOGLE_GENAI:
                model_name = AI_MODEL if AI_MODEL else "gemini-2.0-flash"
                
                # Verifica se o modelo está disponível no plano gratuito
                if model_name in ["gemini-3-pro-preview", "gemini-3-pro"]:
                    print(f" [!!!] AVISO: Modelo '{model_name}' não está disponível no plano gratuito. Usando 'gemini-2.0-flash'.")
                    model_name = "gemini-2.0-flash"
                
                max_retries_lib = 3
                retry_delay_lib = 2
                
                for attempt_lib in range(max_retries_lib):
                    try:
                        # Cria o cliente
                        client = genai.Client(api_key=AI_API_KEY)
                        
                        # Combina system prompt com user prompt
                        full_prompt = f"{SYSTEM_PROMPT}\n\nUsuário: {user_prompt}\n\nAssistente:"
                        
                        print(f" [+] [WORKER] Usando biblioteca oficial Google Gemini (modelo: {model_name}, tentativa {attempt_lib + 1}/{max_retries_lib})")
                        
                        # Gera conteúdo usando a biblioteca oficial
                        response = client.models.generate_content(
                            model=model_name,
                            contents=full_prompt
                        )
                        
                        bot_response = response.text
                        if bot_response:
                            print(f" [+] [WORKER] Resposta da IA (Gemini) gerada com sucesso ({len(bot_response)} caracteres)")
                            return bot_response
                        else:
                            return "Erro: A API retornou uma resposta vazia."
                            
                    except Exception as lib_error:
                        error_str = str(lib_error)
                        print(f" [!!!] Erro ao usar biblioteca oficial (tentativa {attempt_lib + 1}/{max_retries_lib}): {error_str}")
                        
                        # Se for rate limit (429) ou quota esgotada, verifica se é quota 0
                        if "429" in error_str or "rate limit" in error_str.lower() or "quota" in error_str.lower() or "RESOURCE_EXHAUSTED" in error_str:
                            # Verifica se é quota 0 (limit: 0) - significa que não tem acesso ao plano gratuito
                            if "limit: 0" in error_str or '"limit": 0' in error_str:
                                # Se for quota 0, retorna mensagem clara sobre o problema
                                error_msg = (
                                    "❌ Erro: Sua API key do Google Gemini não tem acesso ao plano gratuito ou a quota está zerada.\n\n"
                                    "🔍 O que fazer:\n"
                                    "1. Acesse https://aistudio.google.com/\n"
                                    "2. Verifique se sua API key está ativa\n"
                                    "3. Verifique o uso e quotas em: https://ai.dev/usage?tab=rate-limit\n"
                                    "4. Certifique-se de que o projeto tem acesso ao plano gratuito habilitado\n"
                                    "5. Se necessário, gere uma nova API key em um projeto diferente\n\n"
                                    "💡 Nota: Alguns modelos podem ter quota 0 no plano gratuito. Tente usar uma API key de um projeto que tenha acesso ao plano gratuito habilitado."
                                )
                                print(f" [!!!] {error_msg}")
                                return error_msg
                            
                            # Se for rate limit normal (não quota 0), tenta novamente
                            if attempt_lib < max_retries_lib - 1:
                                wait_time = retry_delay_lib * (2 ** attempt_lib)
                                print(f" [!!!] Rate limit detectado. Aguardando {wait_time}s antes de tentar novamente...")
                                time.sleep(wait_time)
                                continue
                            else:
                                return "Erro: Rate limit da API de IA (muitas requisições). Por favor, aguarde alguns instantes e tente novamente."
                        
                        # Se for erro 404 (modelo não encontrado), retorna mensagem específica
                        if "404" in error_str or "NOT_FOUND" in error_str or "is not found" in error_str.lower():
                            error_msg = (
                                f"❌ Erro: Modelo '{model_name}' não encontrado na API v1beta.\n\n"
                                "🔍 O que fazer:\n"
                                "1. Verifique se o nome do modelo está correto\n"
                                "2. Tente usar um modelo disponível no plano gratuito\n"
                                "3. Consulte a documentação: https://ai.google.dev/gemini-api/docs/models\n"
                                f"4. Modelo atual configurado: {AI_MODEL}"
                            )
                            print(f" [!!!] {error_msg}")
                            return error_msg
                        
                        # Se não for rate limit e for a última tentativa, faz fallback para HTTP
                        if attempt_lib == max_retries_lib - 1:
                            print(f" [!!!] Todas as tentativas com biblioteca oficial falharam. Tentando método HTTP direto como fallback...")
                            break
                        else:
                            # Para outros erros, tenta novamente
                            time.sleep(retry_delay_lib)
                            continue
            
            # Método HTTP direto (fallback ou quando biblioteca não está disponível)
            # API do Google Gemini via HTTP
            # URL: https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={API_KEY}
            # Modelos válidos no plano gratuito: gemini-2.0-flash, gemini-1.5-flash
            # NOTA: gemini-3-pro-preview NÃO está disponível no plano gratuito (quota: 0)
            model_name = AI_MODEL if AI_MODEL else "gemini-2.0-flash"
            
            # Lista de modelos inválidos ou não disponíveis no plano gratuito - substitui por modelo válido
            # gemini-3-pro-preview não está disponível no plano gratuito (quota: 0)
            invalid_models = ["gemini-3", "gemini-pro", "gemini-pro-1.0", "gemini-3-pro-preview", "gemini-3-pro"]
            if model_name in invalid_models:
                print(f" [!!!] AVISO: Modelo '{model_name}' não está disponível no plano gratuito. Usando 'gemini-2.0-flash' como alternativa.")
                model_name = "gemini-2.0-flash"
            
            api_url = AI_API_URL or f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent"
            print(f" [+] [WORKER] URL da API Gemini: {api_url.split('?')[0]} (modelo: {model_name})")
            
            # Combina system prompt com user prompt para Gemini
            full_prompt = f"{SYSTEM_PROMPT}\n\nUsuário: {user_prompt}\n\nAssistente:"
            
            headers = {
                "Content-Type": "application/json"
            }
            
            payload = {
                "contents": [{
                    "parts": [{
                        "text": full_prompt
                    }]
                }],
                "generationConfig": {
                    "temperature": 0.7,
                    "maxOutputTokens": 1000
                }
            }
            
            # Adiciona a chave como parâmetro na URL para Gemini
            if "?" in api_url:
                api_url = f"{api_url}&key={AI_API_KEY}"
            else:
                api_url = f"{api_url}?key={AI_API_KEY}"
                
        elif IS_DEEPSEEK:
            # API DeepSeek (compatível com OpenAI)
            api_url = AI_API_URL or "https://api.deepseek.com/v1/chat/completions"
            
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {AI_API_KEY}"
            }
            
            payload = {
                "model": AI_MODEL,
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt}
                ],
                "temperature": 0.7,
                "max_tokens": 1000
            }
        elif IS_GROQ:
            # API Groq (compatível com OpenAI)
            api_url = AI_API_URL or "https://api.groq.com/openai/v1/chat/completions"
            
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {AI_API_KEY}"
            }
            
            payload = {
                "model": AI_MODEL,
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt}
                ],
                "temperature": 0.7,
                "max_tokens": 1000
            }
        else:
            # API OpenAI (padrão)
            api_url = AI_API_URL or "https://api.openai.com/v1/chat/completions"
            
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {AI_API_KEY}"
            }
            
            payload = {
                "model": AI_MODEL,
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt}
                ],
                "temperature": 0.7,
                "max_tokens": 1000
            }
        
        # Faz a requisição HTTP com retry para rate limiting (429)
        print(f" [+] [WORKER] Enviando requisição para API de IA...")
        
        max_retries = 3
        retry_delay = 2  # Começa com 2 segundos
        
        for attempt in range(max_retries):
            response = requests.post(
                api_url,
                headers=headers,
                json=payload,
                timeout=30  # Timeout de 30 segundos
            )
            
            print(f" [+] [WORKER] Resposta recebida: Status {response.status_code} (tentativa {attempt + 1}/{max_retries})")
            
            # Se for 429 (rate limit), verifica se é quota 0 ou rate limit normal
            if response.status_code == 429:
                try:
                    error_data = response.json()
                    error_text = json.dumps(error_data)
                    # Verifica se é quota 0 (limit: 0)
                    if "limit: 0" in error_text or '"limit": 0' in error_text:
                        error_msg = (
                            "❌ Erro: Sua API key do Google Gemini não tem acesso ao plano gratuito ou a quota está zerada.\n\n"
                            "🔍 O que fazer:\n"
                            "1. Acesse https://aistudio.google.com/\n"
                            "2. Verifique se sua API key está ativa\n"
                            "3. Verifique o uso e quotas em: https://ai.dev/usage?tab=rate-limit\n"
                            "4. Certifique-se de que o projeto tem acesso ao plano gratuito habilitado\n"
                            "5. Se necessário, gere uma nova API key em um projeto diferente\n\n"
                            "💡 Nota: Alguns modelos podem ter quota 0 no plano gratuito. Tente usar uma API key de um projeto que tenha acesso ao plano gratuito habilitado."
                        )
                        print(f" [!!!] {error_msg}")
                        return error_msg
                except:
                    pass
                
                # Se for rate limit normal (não quota 0), tenta novamente
                if attempt < max_retries - 1:
                    wait_time = retry_delay * (2 ** attempt)  # Backoff exponencial: 2s, 4s, 8s
                    print(f" [!!!] Rate limit atingido (429). Aguardando {wait_time}s antes de tentar novamente...")
                    time.sleep(wait_time)
                    continue
                else:
                    error_msg = "Erro: Rate limit da API de IA (muitas requisições). Por favor, aguarde alguns instantes e tente novamente."
                    print(f" [!!!] {error_msg}")
                    return error_msg
            
            # Se não for 429, sai do loop de retry
            break
        
        # Verifica se a requisição foi bem-sucedida
        if response.status_code == 200:
            response_data = response.json()
            
            # Extrai a resposta baseado no tipo de API
            if IS_GEMINI:
                # Formato Gemini: {"candidates": [{"content": {"parts": [{"text": "..."}]}}]}
                if "candidates" in response_data and len(response_data["candidates"]) > 0:
                    candidate = response_data["candidates"][0]
                    if "content" in candidate and "parts" in candidate["content"]:
                        bot_response = candidate["content"]["parts"][0].get("text", "")
                        if bot_response:
                            print(f" [+] [WORKER] Resposta da IA (Gemini) gerada com sucesso ({len(bot_response)} caracteres)")
                            return bot_response
                
                error_msg = "Erro: Resposta da API Gemini não contém 'candidates' válido."
                print(f" [!!!] {error_msg}")
                print(f" [!!!] Resposta da API: {response_data}")
                return error_msg
            else:
                # Formato OpenAI/DeepSeek/Groq: {"choices": [{"message": {"content": "..."}}]}
                if "choices" in response_data and len(response_data["choices"]) > 0:
                    bot_response = response_data["choices"][0]["message"]["content"]
                    api_name = "Groq" if IS_GROQ else ("DeepSeek" if IS_DEEPSEEK else "OpenAI")
                    print(f" [+] [WORKER] Resposta da IA ({api_name}) gerada com sucesso ({len(bot_response)} caracteres)")
                    return bot_response
                else:
                    error_msg = "Erro: Resposta da API não contém 'choices' válido."
                    print(f" [!!!] {error_msg}")
                    print(f" [!!!] Resposta da API: {response_data}")
                    return error_msg
        else:
            error_msg = f"Erro na API de IA: Status {response.status_code} - {response.text[:500]}"
            print(f" [!!!] {error_msg}")
            print(f" [!!!] Resposta completa: {response.text}")
            
            # Tratamento específico para diferentes códigos de erro
            if response.status_code == 400:
                # Erro 400: Pode ser modelo descontinuado ou inválido
                try:
                    error_data = response.json()
                    error_text = json.dumps(error_data)
                    if "decommissioned" in error_text.lower() or "no longer supported" in error_text.lower():
                        return (
                            f"❌ Erro: O modelo '{AI_MODEL}' foi descontinuado e não é mais suportado.\n\n"
                            "🔍 O que fazer:\n"
                            "1. Verifique os modelos disponíveis em: https://console.groq.com/docs/models\n"
                            "2. Atualize o modelo no arquivo .env\n"
                            "3. Modelos sugeridos: llama-3.3-70b-versatile, llama-3.3-8b-instant, mixtral-8x7b-32768\n\n"
                            f"💡 Modelo atual configurado: {AI_MODEL}"
                        )
                except:
                    pass
            elif response.status_code == 402:
                # Erro 402: Saldo insuficiente (DeepSeek)
                try:
                    error_data = response.json()
                    if "Insufficient Balance" in str(error_data) or "insufficient" in str(error_data).lower():
                        return (
                            "❌ Erro: Saldo insuficiente na conta da API DeepSeek.\n\n"
                            "🔍 O que fazer:\n"
                            "1. Acesse https://platform.deepseek.com/\n"
                            "2. Verifique o saldo da sua conta\n"
                            "3. Adicione créditos se necessário\n"
                            "4. Verifique se a API key está correta e ativa\n\n"
                            "💡 Nota: A API DeepSeek requer créditos na conta para funcionar."
                        )
                except:
                    pass
                return "Erro: Saldo insuficiente na conta da API. Por favor, adicione créditos à sua conta."
            elif response.status_code == 404 and IS_GEMINI:
                return f"Erro: O modelo '{AI_MODEL}' não foi encontrado. Por favor, verifique se o modelo está correto (ex: gemini-2.0-flash, gemini-1.5-flash)."
            elif response.status_code == 429:
                return f"Erro: Rate limit da API de IA (muitas requisições). Por favor, aguarde alguns instantes e tente novamente."
            elif response.status_code == 401:
                return f"Erro: Chave de API inválida ou expirada. Por favor, verifique a configuração da API."
            elif response.status_code == 403:
                return f"Erro: Acesso negado à API. Verifique as permissões da sua chave de API."
            else:
                return f"Desculpe, ocorreu um erro ao processar sua mensagem (Status {response.status_code}). Por favor, tente novamente."
            
    except requests.exceptions.Timeout:
        error_msg = "Erro: Timeout ao chamar API de IA (mais de 30 segundos)."
        print(f" [!!!] {error_msg}")
        return "Desculpe, a resposta está demorando mais que o esperado. Por favor, tente novamente."
    except requests.exceptions.RequestException as e:
        error_msg = f"Erro de conexão com API de IA: {str(e)}"
        print(f" [!!!] {error_msg}")
        return "Desculpe, não foi possível conectar ao serviço de IA. Por favor, tente novamente mais tarde."
    except Exception as e:
        error_msg = f"Erro inesperado ao chamar API de IA: {str(e)}"
        print(f" [!!!] {error_msg}")
        import traceback
        traceback.print_exc()
        return "Desculpe, ocorreu um erro inesperado. Por favor, tente novamente."

# --- Lógica de Publicação de Resposta ---
def publish_response(user_id: str, bot_response: str):

    try:
        connection = get_rabbitmq_connection()
        channel = connection.channel()

        # Garante que a Exchange e a Fila de RESPOSTA existam (Resiliência/OS5)
        channel.exchange_declare(exchange=RESPONSE_EXCHANGE_NAME, exchange_type='direct', durable=True)
        channel.queue_declare(queue=RESPONSE_QUEUE_NAME, durable=True)
        channel.queue_bind(exchange=RESPONSE_EXCHANGE_NAME, queue=RESPONSE_QUEUE_NAME, routing_key=RESPONSE_QUEUE_NAME)

        response_payload = {
            "user_id": user_id,
            "bot_content": bot_response, 
            "timestamp_processed": time.time()
        }
        
        body = json.dumps(response_payload)
        
        channel.basic_publish(
            exchange=RESPONSE_EXCHANGE_NAME,
            routing_key=RESPONSE_QUEUE_NAME,
            body=body,
            properties=pika.BasicProperties(
                delivery_mode=pika.spec.PERSISTENT_DELIVERY_MODE
            )
        )
        
        print(f" [->] Resposta enviada para fila: {RESPONSE_QUEUE_NAME}")
        connection.close()
        return True

    except Exception as e:
        print(f" [!] ERRO ao publicar resposta na fila: {e}")
        return False

# --- Lógica de Callback e Consumo ---
def callback(ch, method, properties, body):

    try:
        message_data = json.loads(body)
        
        user_id = message_data.get("user_id")
        user_prompt = message_data.get("content")
        
        if not user_id or not user_prompt:
             print(" [!] Mensagem incompleta recebida. Ignorando.")
             ch.basic_ack(delivery_tag=method.delivery_tag)
             return

        # 1. Processamento da IA (Etapa Lenta)
        bot_response = call_external_ai_api(user_prompt)
        
        # 2. Persistência da Resposta do Bot
        print(f" [DB] Salvando resposta do BOT no PostgreSQL para usuário {user_id}...")
        
        async def save_bot_message_async():
             async with AsyncSessionLocal() as db_session:
                await save_message(db_session, user_id, "BOT", bot_response)

        # Executa a função assíncrona de forma síncrona
        asyncio.run(save_bot_message_async())
        
        # 3. Publicar a Resposta na Fila q.ia_response
        publish_response(user_id, bot_response)
        
        # 4. Registra métrica de throughput (mensagem processada com sucesso)
        messages_processed_total.labels(status='success').inc()
        
        # 5. Confirmação (ACK)
        ch.basic_ack(delivery_tag=method.delivery_tag) 

    except Exception as e:
        print(f" [!!!] Erro no processamento do Worker: {e}. Rejeitando mensagem.")
        # Registra métrica de falha
        messages_processed_total.labels(status='error').inc()
        # Rejeita a mensagem para que ela volte à fila ou vá para uma DLQ
        ch.basic_nack(delivery_tag=method.delivery_tag) 


def start_consuming():
    """Conecta ao RabbitMQ e inicia o loop de consumo da fila de requisição."""
    credentials = pika.PlainCredentials(RABBITMQ_USER, RABBITMQ_PASS)
    parameters = pika.ConnectionParameters(
        host=RABBITMQ_HOST,
        credentials=credentials
    )

    try:
        connection = pika.BlockingConnection(parameters)
        channel = connection.channel()

        # Garante que a fila e a exchange existam (durable=True para Resiliência)
        channel.exchange_declare(exchange=EXCHANGE_NAME, exchange_type='direct', durable=True)
        channel.queue_declare(queue=QUEUE_NAME, durable=True)
        channel.queue_bind(exchange=EXCHANGE_NAME, queue=QUEUE_NAME, routing_key=QUEUE_NAME)
        
        # Fair dispatch (Qualidade de Serviço - QoS)
        channel.basic_qos(prefetch_count=1)

        print(f' [*] Worker IA iniciado. Aguardando mensagens na fila {QUEUE_NAME}.')
        
        channel.basic_consume(queue=QUEUE_NAME, on_message_callback=callback)
        channel.start_consuming()

    except pika.exceptions.AMQPConnectionError as e:
        print(f" [!!!] Erro de conexão com RabbitMQ. Tentando reconectar em 5s: {e}")
        time.sleep(5)
        start_consuming() # Tenta reconectar (Resiliência)
    except KeyboardInterrupt:
        print('Worker desligado.')

if __name__ == '__main__':
    # Log de inicialização com informações de configuração
    print("=" * 60)
    print(" [WORKER] Iniciando IA Worker...")
    print(f" [WORKER] Modelo configurado: {AI_MODEL}")
    api_type_startup = "Groq" if IS_GROQ else ("DeepSeek" if IS_DEEPSEEK else ("Gemini" if IS_GEMINI else "OpenAI"))
    print(f" [WORKER] Tipo de API: {api_type_startup}")
    print(f" [WORKER] API Key presente: {'Sim' if AI_API_KEY else 'NÃO - ERRO!'}")
    print(f" [WORKER] URL da API: {AI_API_URL or 'Usando padrão'}")
    print("=" * 60)
    
    if not AI_API_KEY:
        print(" [!!!] ERRO CRÍTICO: AI_API_KEY não configurada!")
        print(" [!!!] Configure a variável AI_API_KEY no arquivo .env")
        exit(1)
    
    # Inicia servidor de métricas em thread separada
    metrics_port = int(os.getenv("METRICS_PORT", "8000"))
    metrics_thread = Thread(target=start_metrics_server, args=(metrics_port,), daemon=True)
    metrics_thread.start()
    
    # Inicia consumo de mensagens
    start_consuming()