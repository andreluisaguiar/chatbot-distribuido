# Testes de Carga - Múltiplos Usuários Simultâneos

Este documento descreve como executar testes de carga para validar a escalabilidade do sistema com múltiplos usuários simultâneos.

## Objetivo

Garantir que o sistema suporte **10+ usuários simultâneos** sem degradação crítica de performance, validando:
- ✅ Escalabilidade horizontal com múltiplos workers
- ✅ Distribuição de carga entre workers
- ✅ Latência aceitável (< 5s para 95% das requisições)
- ✅ Taxa de erro baixa (< 10%)
- ✅ Throughput adequado

## 🛠️ Pré-requisitos

### 1. Instalar K6

```bash
# Linux (Ubuntu/Debian)
sudo apt-key adv --keyserver hkp://keyserver.ubuntu.com:80 --recv-keys C5AD17C747E3415A3642D57D77C6C491D6AC1D69
echo "deb https://dl.k6.io/deb stable main" | sudo tee /etc/apt/sources.list.d/k6.list
sudo apt-get update
sudo apt-get install k6

# macOS
brew install k6

# Windows
choco install k6

# Ou via Docker
docker pull grafana/k6
```

### 2. Verificar Serviços

Certifique-se de que todos os serviços estão rodando:

```bash
docker compose up -d
docker compose ps  # Verifica status
```

## 🚀 Executando Testes

### Teste Básico (10 usuários, 2 minutos)

```bash
# Usando o script helper
./tests/run_load_test.sh 10 120

# Ou diretamente com k6
k6 run --vus 10 --duration 120s tests/k6_load_test.js
```

### Teste de Ramp-up Gradual

O script `k6_load_test.js` já inclui um perfil de ramp-up:
- 0-30s: Aumenta para 5 usuários
- 30-90s: Aumenta para 10 usuários
- 90-210s: Mantém 10 usuários
- 210-240s: Reduz para 0 usuários

```bash
k6 run tests/k6_load_test.js
```

### Teste com Mais Usuários

```bash
# 20 usuários por 3 minutos
./tests/run_load_test.sh 20 180

# 50 usuários por 5 minutos
./tests/run_load_test.sh 50 300
```

### Teste com URLs Customizadas

```bash
WS_URL=ws://seu-servidor:8000/ws_chat \
API_URL=http://seu-servidor:8000 \
k6 run tests/k6_load_test.js
```

## 📊 Métricas Coletadas

O teste coleta as seguintes métricas:

### Métricas Customizadas

- **message_latency_ms**: Latência de resposta das mensagens (em milissegundos)
- **messages_sent_total**: Total de mensagens enviadas
- **messages_received_total**: Total de respostas recebidas
- **errors**: Taxa de erros

### Métricas Padrão do K6

- **http_req_duration**: Duração das requisições HTTP
- **ws_connecting**: Taxa de sucesso de conexões WebSocket
- **vus**: Número de usuários virtuais ativos
- **iterations**: Total de iterações completadas

### Thresholds (Limites)

O teste valida automaticamente:
- ✅ 95% das mensagens respondem em menos de 5 segundos
- ✅ Taxa de erro menor que 10%
- ✅ Taxa de falha de conexão menor que 10%

## 📈 Monitoramento Durante o Teste

### 1. Grafana Dashboard

Acesse: http://localhost:3000

**Dashboard de Testes de Carga:**
O sistema inclui um dashboard específico para testes de carga chamado **"Testes de Carga - Múltiplos Usuários"** que exibe:

#### Métricas Principais:
- **Throughput de Mensagens**: Mensagens processadas por segundo (WebSocket e Workers)
- **Latência WebSocket**: p50, p95, p99 com alertas visuais (verde/amarelo/vermelho)
- **Taxa de Erros**: Gráfico de erros vs sucessos em tempo real
- **Distribuição de Carga**: Mensagens processadas por cada worker
- **Requisições HTTP**: Taxa e latência de registro/login
- **Histograma de Latência**: Distribuição completa dos tempos de resposta

#### Painéis Disponíveis:
1. **Throughput de Mensagens**: Gráfico de linha mostrando mensagens/s
2. **Total de Mensagens Processadas**: Contador total
3. **Mensagens por Worker**: Estatísticas por instância
4. **Latência WebSocket (p50, p95, p99)**: Gráfico com thresholds
5. **Latência Média e p95**: Cards com cores indicativas
6. **Taxa de Erros**: Gráfico de linha erro vs sucesso
7. **Taxa de Sucesso vs Erro**: Gráfico de pizza
8. **Requisições HTTP**: Registro/login
9. **Latência HTTP**: p50, p95, p99 para endpoints de usuários
10. **Distribuição de Carga por Worker**: Gráfico de barras horizontal
11. **Total de Mensagens por Status**: Tabela com contadores
12. **Histograma de Latência**: Heatmap de distribuição

O dashboard atualiza automaticamente a cada 5 segundos durante os testes.

**Como acessar o dashboard:**
1. Acesse http://localhost:3000
2. Faça login (admin/admin)
3. No menu lateral, vá em **Dashboards** → **Browse**
4. Procure por **"Testes de Carga - Múltiplos Usuários"**
5. Ou acesse diretamente: http://localhost:3000/d/load-test-dashboard

**Nota:** Se o dashboard não aparecer, reinicie o Grafana:
```bash
docker compose restart grafana
```

### 2. Logs dos Workers

```bash
# Ver logs de todos os workers
docker compose logs -f ia_worker_1 ia_worker_2 ia_worker_3

# Ver apenas um worker
docker compose logs -f ia_worker_1
```

### 3. Prometheus

Acesse: http://localhost:9090

Consultas úteis:
```promql
# Throughput de mensagens processadas
rate(ia_worker_messages_processed_total[1m])

# Latência média
rate(websocket_message_duration_seconds_sum[1m]) / rate(websocket_message_duration_seconds_count[1m])

# Mensagens por worker
sum by (instance) (ia_worker_messages_processed_total)
```

### 4. RabbitMQ Management

Acesse: http://localhost:15672 (guest/guest)

Verifique:
- Número de mensagens na fila `q.ia_request`
- Taxa de consumo
- Workers conectados

## 🧪 Teste de Tolerância a Falhas

Durante a execução do teste, você pode simular falhas:

### Parar um Worker

```bash
# Em outro terminal, durante o teste
docker compose stop ia_worker_1

# Observe que:
# - As mensagens continuam sendo processadas
# - Os outros workers assumem a carga
# - O throughput pode diminuir temporariamente, mas se recupera
```

### Reiniciar um Worker

```bash
docker compose start ia_worker_1
```

## 📝 Interpretando Resultados

### Teste Bem-Sucedido ✅

```
✓ WebSocket conectado: 100%
✓ message_latency_ms: p(95) < 5000ms
✓ errors: rate < 0.1
✓ messages_received ≈ messages_sent
```

### Possíveis Problemas

1. **Alta latência (> 5s)**
   - Verifique se há workers suficientes
   - Aumente o número de workers: `docker compose up -d --scale ia_worker_1=5`
   - Verifique a API de IA (Groq/Gemini) para rate limits

2. **Alta taxa de erro (> 10%)**
   - Verifique logs dos workers
   - Verifique conexão com RabbitMQ
   - Verifique se a API de IA está respondendo

3. **Mensagens não recebidas**
   - Verifique se o response_consumer está rodando
   - Verifique logs do api_gateway
   - Verifique conexões WebSocket

## 🔧 Ajustando Configurações

### Modificar Número de Workers

```bash
# Aumentar para 5 workers
docker compose up -d --scale ia_worker_1=5

# Ou editar docker-compose.yml e adicionar mais réplicas
```

### Modificar Perfil de Teste

Edite `tests/k6_load_test.js` e modifique a seção `options`:

```javascript
export const options = {
  stages: [
    { duration: '30s', target: 10 },   // Ramp-up rápido
    { duration: '120s', target: 10 },  // Mantém 10 usuários
    { duration: '30s', target: 0 },    // Ramp-down
  ],
  // ...
};
```

## 📚 Referências

- [Documentação K6](https://k6.io/docs/)
- [K6 WebSocket](https://k6.io/docs/javascript-api/k6-ws/)
- [Grafana Dashboard](./README.md#métricas-e-observabilidade)

## 🎯 Resultados Esperados

Para validar o objetivo de **10+ usuários simultâneos**:

- ✅ Sistema processa todas as mensagens sem perda
- ✅ Latência p95 < 5 segundos
- ✅ Taxa de erro < 10%
- ✅ Workers distribuem carga uniformemente
- ✅ Sistema se recupera de falhas de workers
