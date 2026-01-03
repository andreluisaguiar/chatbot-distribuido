#!/bin/bash

# Script para executar teste de carga com múltiplos usuários
# Uso: ./run_load_test.sh [número_de_usuários] [duração_em_segundos]

# Cores para output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  Teste de Carga - Chatbot Distribuído${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

# Verifica se k6 está instalado
if ! command -v k6 &> /dev/null; then
    echo -e "${RED}Erro: k6 não está instalado!${NC}"
    echo "Instale com:"
    echo "  Linux: sudo apt-get install k6"
    echo "  macOS: brew install k6"
    echo "  Windows: choco install k6"
    exit 1
fi

# Configurações padrão
VUS=${1:-10}        # Número de usuários virtuais (padrão: 10)
DURATION=${2:-120}  # Duração em segundos (padrão: 120s = 2 minutos)

echo -e "${YELLOW}Configuração do teste:${NC}"
echo "  - Usuários simultâneos: $VUS"
echo "  - Duração: ${DURATION}s"
echo "  - WebSocket URL: ws://localhost:8000/ws_chat"
echo "  - API URL: http://localhost:8000"
echo ""

# Verifica se os serviços estão rodando
echo -e "${YELLOW}Verificando serviços...${NC}"
if ! curl -s http://localhost:8000/health > /dev/null; then
    echo -e "${RED}Erro: API Gateway não está respondendo em http://localhost:8000${NC}"
    echo "Certifique-se de que os serviços estão rodando:"
    echo "  docker compose up -d"
    exit 1
fi

echo -e "${GREEN}✓ API Gateway está respondendo${NC}"
echo ""

# Executa o teste
echo -e "${YELLOW}Iniciando teste de carga...${NC}"
echo ""

k6 run --vus $VUS --duration ${DURATION}s tests/k6_load_test.js

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  Teste concluído!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "${YELLOW}Próximos passos:${NC}"
echo "  1. Verifique as métricas no Grafana: http://localhost:3000"
echo "  2. Analise os logs dos workers: docker compose logs -f ia_worker_1"
echo "  3. Verifique o throughput no Prometheus: http://localhost:9090"
echo ""
