# 🤖 Chatbot Distribuído com Inteligência Artificial e Mensageria

## 📍 1. Visão Geral do Projeto

Este projeto é um **Chatbot Inteligente** desenvolvido sob uma arquitetura de **Sistemas Distribuídos**, focado em escalabilidade horizontal, comunicação assíncrona via filas e alta disponibilidade. O projeto é um requisito da disciplina de Sistemas Distribuídos da UFMA (2025.2).

### 🎯 Objetivo Principal
Desenvolver um chatbot inteligente baseado em arquitetura distribuída, capaz de atender múltiplos usuários simultaneamente, garantindo comunicação eficiente, escalabilidade e tolerância a falhas.

### 📅 Status Atual
✅ **Projeto Concluído** - Todas as fases implementadas e validadas:
- Backend Core operacional
- Frontend React completo
- Métricas e observabilidade implementadas
- Testes unitários passando
- Sistema pronto para uso

---

## 🏗️ 2. Arquitetura e Componentes Distribuídos

O sistema é dividido em microsserviços desacoplados que se comunicam primariamente via filas (RabbitMQ).

### 📦 Componentes Chave

| Módulo | Tecnologia | Função no SD | Critério Atendido |
| :--- | :--- | :--- | :--- |
| **API Gateway** | FastAPI (Python) | Ponto de entrada (WebSocket) e **Produtor** de requisições. Recebe respostas da fila para enviar ao cliente. | OS1, OS3 |
| **IA Worker** | FastAPI (Python) | **Consumidor** assíncrono. Responsável pelo processamento lento (simulação de IA) e persistência da resposta do Bot. | OS2, OS3, OS5 |
| **Mensageria** | **RabbitMQ** | Middleware VITAL para comunicação assíncrona e desacoplamento entre a API e os Workers. | OS1 |
| **Persistência** | **PostgreSQL + SQLAlchemy** | Armazenamento persistente de usuários e histórico de mensagens. | - |
| **Observabilidade** | **Prometheus + Grafana** | Coleta e visualização de métricas de desempenho e *throughput*. | OS4 |
| **Frontend** | **React** | Interface web para interação com o chatbot via WebSocket. | - |

---

## 🚀 3. Guia de Inicialização

### 3.1 Pré-requisitos

1. **Docker** (versão 20.10 ou superior)
2. **Docker Compose** (versão 2.0 ou superior)
3. **Node.js** (versão 16 ou superior) e **npm** (para o frontend)

**Verificar instalação:**
```bash
docker --version
docker compose version
node --version
npm --version
```

### 3.2 Configuração Inicial

#### Verificar arquivo `.env`

Certifique-se de que o arquivo `.env` existe na raiz do projeto:

```bash
# Verificar se o arquivo existe
ls -la .env

# Visualizar conteúdo (opcional)
cat .env
```

O arquivo `.env` deve conter:
```env
ENVIRONMENT=local
BACKEND_HOST=0.0.0.0
BACKEND_PORT=8000

POSTGRES_USER=SEU_USER
POSTGRES_PASSWORD=SUA_SENHA
POSTGRES_DB=db_chatbot
POSTGRES_HOST=postgres
POSTGRES_PORT=5432

RABBITMQ_USER=SEU_USER
RABBITMQ_PASS=SUA_SENHA
RABBITMQ_HOST=rabbitmq
RABBITMQ_PORT=5672

REDIS_HOST=redis
REDIS_PORT=6379
```

### 3.3 Iniciar o Backend

```bash
# 1. Navegar para o diretório do projeto
cd /home/andre-aguiar/Documentos/chatbot-distribuido

# 2. Construir as imagens (primeira vez ou após mudanças)
docker compose build

# 3. Iniciar todos os serviços
docker compose up -d

# 4. Verificar status
docker compose ps
```

**Tempo estimado:** 2-5 minutos (primeira vez)

**O que este comando faz:**
- Cria a rede Docker `chatbot-net`
- Inicia PostgreSQL, RabbitMQ, Redis
- Inicia API Gateway
- Inicia 3 réplicas do IA Worker
- Inicia Prometheus
- Inicia Grafana

**Aguardar:** 10-30 segundos para todos os serviços iniciarem completamente.

### 3.4 Verificar se o Backend Está Funcionando

```bash
# Health check
curl http://localhost:8000/health

# Resposta esperada:
# {"status":"ok","message":"API Gateway está operacional"}

# Verificar métricas
curl http://localhost:8000/metrics | head -20

# Verificar Prometheus
curl http://localhost:9090/-/healthy

# Verificar logs
docker compose logs api_gateway --tail 20
```

### 3.5 Iniciar o Frontend

```bash
# 1. Navegar para o diretório do frontend
cd frontend

# 2. Instalar dependências (primeira vez apenas)
npm install

# 3. Iniciar o servidor de desenvolvimento
npm start
```

O frontend será iniciado e o navegador abrirá automaticamente em: **http://localhost:3000**

**Nota:** O React usa a porta 3000 por padrão. Se estiver em uso (ex: Grafana), o React perguntará se deseja usar outra porta, ou você pode especificar: `PORT=3001 npm start`

---

## 🌐 4. URLs de Acesso

| Serviço | URL | Credenciais |
|---------|-----|-------------|
| **Frontend React** | http://localhost:3000 | - |
| **API Gateway** | http://localhost:8000 | - |
| **API Health** | http://localhost:8000/health | - |
| **API Métricas** | http://localhost:8000/metrics | - |
| **Criar Usuário (POST)** | http://localhost:8000/api/v1/users | body: `{"username":"joao"}` |
| **Prometheus** | http://localhost:9090 | - |
| **Grafana** | http://localhost:3000 | `admin` / `admin` |
| **RabbitMQ Management** | http://localhost:15672 | Ver `.env` |

**⚠️ Nota sobre Porta 3000:**
- O Grafana e o Frontend React usam a mesma porta 3000
- Se ambos estiverem rodando, use: `PORT=3001 npm start` para o frontend
- Ou pare o Grafana temporariamente: `docker compose stop grafana`

---

## 🎨 5. Usando a Interface do Chatbot

### 5.1 Acessar a Interface

1. Abra o navegador: http://localhost:3000 (ou http://localhost:3001 se usar porta alternativa)
2. Verifique o status de conexão no canto superior direito:
   - **"Conectado"** (verde) = tudo funcionando
   - **"Desconectado"** (vermelho) = verifique se o backend está rodando
3. No topo da página, informe um **nome de usuário** e clique em **"Criar usuário"**
   - O frontend chama `POST /api/v1/users`
   - O `session_id` retornado é usado automaticamente na conexão WebSocket

### 5.2 Enviar Mensagens

1. Digite uma mensagem no campo de entrada na parte inferior
2. Pressione **Enter** ou clique no botão **"Enviar"**
3. Aguarde a resposta:
   - Primeiro aparecerá: "Mensagem recebida e em processamento..."
   - Após alguns segundos, aparecerá a resposta do bot

### 5.3 Exemplos de Mensagens

- "Olá, como você está?"
- "Qual é a capital do Brasil?"
- "Explique sobre sistemas distribuídos"
- "O que é uma fila de mensagens?"
- "Como funciona o RabbitMQ?"

---

## 🔄 6. Comandos Úteis de Gerenciamento

### Parar os Serviços

```bash
# Parar todos os serviços (mantém containers)
docker compose stop

# Parar e remover containers
docker compose down

# Parar, remover containers e volumes (CUIDADO: apaga dados)
docker compose down -v
```

### Reiniciar um Serviço Específico

```bash
# Reiniciar API Gateway
docker compose restart api_gateway

# Reiniciar todos os workers
docker compose restart ia_worker_1 ia_worker_2 ia_worker_3
```

### Ver Logs

```bash
# Todos os serviços
docker compose logs -f

# Serviço específico
docker compose logs api_gateway -f
docker compose logs ia_worker_1 -f

# Últimas 50 linhas
docker compose logs --tail 50 api_gateway
```

### Reconstruir após Mudanças no Código

```bash
# Reconstruir e reiniciar
docker compose up -d --build

# Reconstruir apenas um serviço
docker compose build api_gateway
docker compose up -d api_gateway
```

### Limpar Tudo

```bash
# Parar e remover tudo (containers, volumes, redes)
docker compose down -v

# Remover imagens também
docker compose down -v --rmi all
```

---

## 🐛 7. Solução de Problemas

### Problema: Frontend não conecta ao backend

**Sintomas:**
- Mostra "Desconectado" no canto superior direito
- Mensagens não são enviadas

**Solução:**
```bash
# 1. Verificar se o backend está rodando
docker compose ps api_gateway

# 2. Verificar se a porta 8000 está acessível
curl http://localhost:8000/health

# 3. Verificar logs do backend
docker compose logs api_gateway | tail -20

# 4. Verificar console do navegador (F12 -> Console)
# Procure por erros de conexão WebSocket
```

### Problema: Porta já em uso

```bash
# Verificar qual processo está usando a porta
sudo lsof -i :8000
sudo lsof -i :3000
sudo lsof -i :9090

# Parar o processo ou mudar a porta no .env
```

### Problema: Containers não iniciam

```bash
# Ver logs de erro
docker compose logs

# Verificar se há containers antigos
docker ps -a

# Remover containers órfãos
docker compose down --remove-orphans
```

### Problema: Workers não processam mensagens

```bash
# Verificar conexão com RabbitMQ
docker compose logs ia_worker_1 | grep -i error

# Verificar se RabbitMQ está rodando
docker compose ps rabbitmq

# Verificar filas no RabbitMQ Management
# Acessar http://localhost:15672
```

### Problema: Bot não responde

**Sintomas:**
- Mensagem é enviada
- Aparece "Mensagem recebida e em processamento..."
- Mas não chega resposta do bot

**Solução:**
```bash
# 1. Verificar se os workers estão rodando
docker compose ps | grep worker

# 2. Verificar logs dos workers
docker compose logs ia_worker_1 | tail -20

# 3. Verificar fila RabbitMQ
# Acessar http://localhost:15672
# Verificar se há mensagens na fila q.ia_request
```

### Problema: Erro "Module not found" no frontend

```bash
# Limpar cache e reinstalar
cd frontend
rm -rf node_modules package-lock.json
npm install
npm start
```

---

## 📊 8. Métricas e Observabilidade

### 8.1 Métricas Disponíveis

#### API Gateway
- `http_request_duration_seconds`: Latência de requisições HTTP
- `http_requests_total`: Total de requisições HTTP
- `websocket_message_duration_seconds`: Latência de mensagens WebSocket
- `websocket_messages_total`: Total de mensagens WebSocket

#### IA Worker
- `ia_worker_messages_processed_total{status="success"}`: Mensagens processadas com sucesso
- `ia_worker_messages_processed_total{status="error"}`: Mensagens com erro

### 8.2 Acessar Grafana

1. Abra o navegador: http://localhost:3000 (ou pare o frontend temporariamente)
2. Login:
   - **Usuário:** `admin`
   - **Senha:** `admin`
3. O dashboard "Chatbot Distribuído - Métricas" deve estar disponível automaticamente

**Painéis disponíveis:**
- Latência HTTP (p50, p95)
- Throughput IA Worker
- Total de Requisições HTTP
- Latência WebSocket (p50, p95)

### 8.3 Acessar Prometheus

1. Abra o navegador: http://localhost:9090
2. Use a interface de consulta para ver métricas em tempo real
3. Acesse "Targets" para verificar se todos os serviços estão sendo coletados

---

## 🧪 9. Testes

### 9.1 Testes Unitários

```bash
# Executar testes unitários
cd backend
python -m pytest tests/unit/ -v

# Resultado esperado: 4 testes passando
```

### 9.2 Testar WebSocket via Python

Crie um arquivo `test_websocket.py`:

```python
import asyncio
import websockets
import json
import uuid

async def test_chatbot():
    user_id = str(uuid.uuid4())
    uri = f"ws://localhost:8000/ws_chat?id={user_id}"
    
    async with websockets.connect(uri) as websocket:
        print("✅ Conectado!")
        
        # Envia mensagem
        await websocket.send("Olá, como você está?")
        
        # Recebe confirmação
        resposta_sistema = await websocket.recv()
        print(f"Sistema: {resposta_sistema}")
        
        # Recebe resposta do bot
        resposta_bot = await websocket.recv()
        print(f"Bot: {resposta_bot}")

asyncio.run(test_chatbot())
```

**Executar:**
```bash
pip install websockets
python test_websocket.py
```

### 9.3 Testes de Carga com k6

```bash
# Instalar k6 (se necessário)
# Linux: sudo apt-get install k6
# macOS: brew install k6

# Executar teste de carga
k6 run tests/k6_load_test.js
```

---

## 📦 10. Estrutura do Projeto

```
chatbot-distribuido/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   ├── chat.py
│   │   │   └── websocket.py
│   │   ├── consumers/
│   │   │   ├── ia_consumer.py
│   │   │   └── response_consumer.py
│   │   ├── services/
│   │   │   ├── database_service.py
│   │   │   ├── metrics_service.py
│   │   │   └── rabbitmq_service.py
│   │   └── main.py
│   ├── tests/
│   │   └── unit/
│   │       ├── test_database_service.py
│   │       └── test_rabbitmq_service.py
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   ├── pages/
│   │   └── services/
│   ├── Dockerfile
│   ├── nginx.conf
│   └── package.json
├── infra/
│   ├── prometheus/
│   │   └── prometheus.yml
│   └── grafana/
│       └── provisioning/
├── tests/
│   └── k6_load_test.js
├── docker-compose.yml
└── README.md
```

---

## ✅ 11. Checklist de Verificação

Antes de começar a usar:

- [ ] Docker e Docker Compose instalados
- [ ] Arquivo `.env` configurado
- [ ] Backend está rodando (`docker compose ps`)
- [ ] API Gateway responde (`curl http://localhost:8000/health`)
- [ ] Frontend está rodando (`npm start` executado)
- [ ] Navegador aberto em http://localhost:3000 (ou 3001)
- [ ] Status mostra "Conectado" (verde)
- [ ] Campo de mensagem está visível
- [ ] Botão "Enviar" está funcionando

---

## 📝 12. Notas Importantes

1. **Primeira execução:** Pode levar 2-5 minutos para baixar imagens e construir containers
2. **Portas:** Certifique-se de que as portas 8000, 3000, 9090, 5672, 15672 não estão em uso
3. **Memória:** O sistema requer pelo menos 2GB de RAM disponível
4. **Dados:** Os dados do PostgreSQL são persistidos em volumes Docker
5. **Ordem de inicialização:**
   - Primeiro: Backend (Docker Compose)
   - Depois: Frontend (npm start)
6. **Desenvolvimento:**
   - O frontend em modo desenvolvimento recarrega automaticamente quando você faz mudanças
   - O backend precisa ser reconstruído para aplicar mudanças: `docker compose up -d --build`

---

## 🎯 13. Resumo Rápido (Comandos Essenciais)

```bash
# 1. Ir para o diretório do projeto
cd /home/andre-aguiar/Documentos/chatbot-distribuido

# 2. Construir imagens (primeira vez)
docker compose build

# 3. Iniciar serviços backend
docker compose up -d

# 4. Verificar status
docker compose ps

# 5. Iniciar frontend (em outro terminal)
cd frontend
npm install  # primeira vez apenas
npm start

# 6. Acessar interface
# http://localhost:3000 (ou 3001 se porta 3000 estiver ocupada)

# 7. Parar serviços
docker compose down
```

---

## 🎓 14. Implementação e Funcionalidades

### 14.1 Funcionalidades Implementadas

- ✅ **Backend Core:** API Gateway com WebSocket, Workers, RabbitMQ, PostgreSQL
- ✅ **Frontend React:** Interface completa com conexão WebSocket
- ✅ **Métricas:** Prometheus e Grafana configurados
- ✅ **Testes:** Testes unitários passando (4/4)
- ✅ **Observabilidade:** Métricas de latência e throughput
- ✅ **Escalabilidade:** 3 réplicas de workers processando em paralelo
- ✅ **Tolerância a Falhas:** Sistema continua funcionando mesmo com falha de workers

### 14.2 Fluxo de Comunicação

1. **Cliente** envia mensagem via WebSocket → **API Gateway**
2. **API Gateway** salva mensagem no **PostgreSQL**
3. **API Gateway** publica mensagem na fila **RabbitMQ** (`q.ia_request`)
4. **IA Worker** consome mensagem da fila
5. **IA Worker** processa (simula IA) e gera resposta
6. **IA Worker** salva resposta no **PostgreSQL**
7. **IA Worker** publica resposta na fila **RabbitMQ** (`q.ia_response`)
8. **API Gateway** consome resposta da fila
9. **API Gateway** envia resposta ao **Cliente** via WebSocket

---

## 🆘 15. Suporte

Se encontrar problemas:
1. Verifique os logs: `docker compose logs`
2. Verifique o status: `docker compose ps`
3. Consulte a seção "Solução de Problemas" acima
4. Verifique o console do navegador (F12) para erros do frontend

---

## 📄 Licença

Projeto acadêmico - UFMA 2025.2
