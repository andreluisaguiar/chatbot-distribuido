# 🤖 Chatbot Distribuído com Inteligência Artificial e Mensageria

## 📍 1. Visão Geral do Projeto

[cite_start]Este projeto é [cite: 6] [cite_start]desenvolvido para a disciplina de **Sistemas Distribuídos** [cite: 9] [cite_start]da Universidade Federal do Maranhão (UFMA) [cite: 24, 25][cite_start], no semestre 2025.2[cite: 10]. [cite_start]O objetivo é aplicar conceitos fundamentais de arquitetura distribuída, escalabilidade e tolerância a falhas[cite: 31, 34].

### 🎯 Objetivo Principal

[cite_start]Desenvolver um chatbot inteligente baseado em arquitetura distribuída, capaz de atender múltiplos usuários simultaneamente, garantindo comunicação eficiente, escalabilidade e tolerância a falhas[cite: 39, 41].

### 👨‍💻 Equipe

* [cite_start]**Professor Orientador:** Luiz Henrique Neves Rodrigues [cite: 11, 27]
* [cite_start]**Discentes:** Andre Luis Aguiar do Nascimento, Daniel Lucas Silva Aires, Italo Francisco Almeida de Oliveira, Kaua Ferreira Galeno [cite: 12, 13, 26]

---

## 🏗️ 2. Arquitetura do Sistema Distribuído

O projeto adota uma arquitetura de microsserviços e comunicação assíncrona para garantir o desacoplamento e a escalabilidade.

### 📦 Componentes Chave

| Módulo | Tecnologia | Função no SD |
| :--- | :--- | :--- |
| **Backend (API)** | [cite_start]FastAPI (Python) ou Node.js [cite: 56] | [cite_start]Atua como Produtor de mensagens na fila[cite: 46]. |
| **Mensageria** | [cite_start]**RabbitMQ** [cite: 58] | [cite_start]Canal de comunicação assíncrona para Desacoplamento e Resiliência (OS1)[cite: 43]. |
| **Cache Distribuído** | [cite_start]**Redis** [cite: 60] | [cite_start]Cache distribuído [cite: 46] e gerenciamento rápido de estado de sessão. |
| **Banco de Dados** | [cite_start]**PostgreSQL** [cite: 59] | [cite_start]Armazenamento persistente de dados relacionais[cite: 46]. |
| **Frontend (UI)** | [cite_start]React + WebSocket [cite: 61] | [cite_start]Interface do usuário e comunicação em tempo real[cite: 47]. |
| **IA/Processamento** | [cite_start]API Externa (OpenAI/Hugging Face) [cite: 62] | [cite_start]Serviço externo consumido para geração de respostas[cite: 48]. |

### 🔍 Observabilidade e Testes

[cite_start]Para atender aos requisitos de monitoramento (OS4) e tolerância a falhas (OS5)[cite: 43]:

* [cite_start]**Monitoramento:** **Prometheus** + **Grafana** para coletar e visualizar métricas em tempo real[cite: 64, 49].
* [cite_start]**Testes de Carga:** **k6** para simular 10+ usuários simultâneos[cite: 63, 49].
* [cite_start]**Resiliência:** Validação da Tolerância a falhas (Sistema funcional após desligamento de um worker)[cite: 43, 50].
