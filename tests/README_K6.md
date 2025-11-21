# Testes de Carga com k6

## Pré-requisitos

Instale o k6:
```bash
# Linux
sudo apt-key adv --keyserver hkp://keyserver.ubuntu.com:80 --recv-keys C5AD17C747E3415A3642D57D77C6C491D6AC1D69
echo "deb https://dl.k6.io/deb stable main" | sudo tee /etc/apt/sources.list.d/k6.list
sudo apt-get update
sudo apt-get install k6

# macOS
brew install k6

# Windows
choco install k6
```

## Executar Teste de Carga

```bash
# Teste básico (10 usuários, 60 segundos)
k6 run tests/k6_load_test.js

# Com URL customizada
WS_URL=ws://localhost:8000/ws_chat k6 run tests/k6_load_test.js

# Com mais usuários (ajustar no arquivo)
k6 run tests/k6_load_test.js --vus 20 --duration 120s
```

## Métricas Coletadas

- **Latência**: Tempo de resposta das mensagens
- **Throughput**: Mensagens processadas por segundo
- **Taxa de Erro**: Percentual de conexões/mensagens com falha
- **Conexões Simultâneas**: Número de usuários conectados

## Validação de Tolerância a Falhas

Durante a execução do teste, execute em outro terminal:

```bash
# Parar uma réplica do IA Worker
docker stop <container_id_ia_worker>

# Observar no Grafana que o throughput se mantém estável
# As mensagens devem ser redistribuídas para os workers restantes
```

