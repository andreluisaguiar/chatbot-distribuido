# 🤖 Chatbot Distribuído com Inteligência Artificial e Mensageria

## 📍 1. Visão Geral do Projeto

Este projeto é um **Chatbot Inteligente** desenvolvido sob uma arquitetura de **Sistemas Distribuídos**, focado em escalabilidade horizontal, comunicação assíncrona via filas e alta disponibilidade. O projeto é um requisito da disciplina de Sistemas Distribuídos da UFMA (2025.2).

### 🎯 Objetivo Principal
Desenvolver um chatbot inteligente baseado em arquitetura distribuída, capaz de atender múltiplos usuários simultaneamente, garantindo comunicação eficiente, escalabilidade e tolerância a falhas.

### 📅 Status Atual (09/11/2025)
A Fase de Execução do **Backend Core está concluída e validada** através de testes de integração de ponta a ponta. O ciclo completo de comunicação assíncrona (WebSocket $\rightarrow$ Fila $\rightarrow$ Worker $\rightarrow$ DB) está operacional.

---

## 🏗️ 2. Arquitetura e Componentes Distribuídos

O sistema é dividido em microsserviços desacoplados que se comunicam primariamente via filas (RabbitMQ).

### 📦 Componentes Chave

| Módulo | Tecnologia | Função no SD | Critério Atendido (Exemplos) |
| :--- | :--- | :--- | :--- |
| **API Gateway** | FastAPI (Python) | Ponto de entrada (WebSocket) e **Produtor** de requisições. Recebe respostas da fila para enviar ao cliente. | OS1, OS3 |
| **IA Worker** | FastAPI (Python) | **Consumidor** assíncrono. Responsável pelo processamento lento (simulação de IA) e persistência da resposta do Bot. | OS2, OS3, OS5 |
| **Mensageria** | **RabbitMQ** | Middleware VITAL para comunicação assíncrona e desacoplamento entre a API e os Workers. | OS1 |
| **Persistência** | **PostgreSQL + SQLAlchemy** | Armazenamento persistente de usuários e histórico de mensagens. | - |
| **Observabilidade** | **Prometheus + Grafana** | Previsto para coletar e visualizar métricas de desempenho e *throughput*. | OS4 |

---

## 🚀 3. Guia de Inicialização

### Pré-requisitos
1.  **Git**, **Docker** (v2+) e **Docker Compose** (v2+).
2.  **Node.js/npm** (necessário para a ferramenta de teste `wscat`).

### 1. Iniciar o Ambiente Distribuído
Execute na pasta raiz do projeto. O ambiente contém 10+ serviços e 3 réplicas do Worker.

```bash
# Sobe todos os serviços com reconstrução
docker compose up --build -d

## Teste de Conexão

export TEST_USER_ID=$(uuidgen)
docker compose exec postgres psql -U user -d db_chatbot -c "
  INSERT INTO users (id, username) VALUES ('$TEST_USER_ID', 'test_user');
  INSERT INTO chat_sessions (id, user_id, status) VALUES ('$TEST_USER_ID', '$TEST_USER_ID', 'ACTIVE');
"