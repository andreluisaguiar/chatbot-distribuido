import ws from 'k6/ws';
import http from 'k6/http';
import { check, sleep } from 'k6';
import { Rate, Trend, Counter } from 'k6/metrics';

// Métricas customizadas
const messageLatency = new Trend('message_latency_ms');
const messagesSent = new Counter('messages_sent_total');
const messagesReceived = new Counter('messages_received_total');
const errorRate = new Rate('errors');

// Configuração do teste
export const options = {
  stages: [
    { duration: '30s', target: 5 },   // Ramp-up: 5 usuários em 30s
    { duration: '60s', target: 10 },  // Aumenta para 10 usuários em 60s
    { duration: '120s', target: 10 }, // Mantém 10 usuários por 2 minutos
    { duration: '30s', target: 0 },   // Ramp-down: volta para 0
  ],
  thresholds: {
    'message_latency_ms': ['p(95)<5000'], // 95% das mensagens devem responder em menos de 5s
    'errors': ['rate<0.1'],              // Menos de 10% de erros
    'ws_connecting': ['p(95)<2000'],     // 95% das conexões WebSocket em menos de 2s
  },
};

// URL base (pode ser sobrescrita por variável de ambiente)
const WS_URL = __ENV.WS_URL || 'ws://localhost:8000/ws_chat';
const API_URL = __ENV.API_URL || 'http://localhost:8000';

// Função para criar um usuário de teste (registro + login)
function createTestUser(vu) {
  const email = `test_user_${vu}_${Date.now()}@test.com`;
  const password = 'test123456';
  const nome = `Teste${vu}`;
  const sobrenome = 'Usuario';

  // Registro
  const registerRes = http.post(`${API_URL}/api/v1/users/register`, JSON.stringify({
    nome: nome,
    sobrenome: sobrenome,
    email: email,
    senha: password
  }), {
    headers: { 'Content-Type': 'application/json' },
  });

  if (registerRes.status !== 201 && registerRes.status !== 400) {
    console.log(`Erro no registro: ${registerRes.status} - ${registerRes.body}`);
    return null;
  }

  // Login
  const loginRes = http.post(`${API_URL}/api/v1/users/login`, JSON.stringify({
    email: email,
    senha: password
  }), {
    headers: { 'Content-Type': 'application/json' },
  });

  if (loginRes.status !== 200) {
    console.log(`Erro no login: ${loginRes.status} - ${loginRes.body}`);
    return null;
  }

  const loginData = JSON.parse(loginRes.body);
  return {
    token: loginData.access_token,
    user_id: loginData.user.id,
    email: email
  };
}

// Função principal de teste
export default function () {
  // Cria usuário de teste
  const user = createTestUser(__VU);
  if (!user) {
    errorRate.add(1);
    return;
  }

  // Gera ID único para a sessão WebSocket
  const sessionId = `${user.user_id}-${Date.now()}`;
  const wsUrl = `${WS_URL}?id=${sessionId}`;

  // Mensagens de teste
  const testMessages = [
    'O que é um sistema distribuído?',
    'Explique o conceito de escalabilidade horizontal',
    'Como funciona o padrão pub/sub?',
    'Qual a diferença entre síncrono e assíncrono?',
    'O que é um message broker?'
  ];

  let messageStartTime = Date.now();
  let messageIndex = 0;
  let messagesToSend = testMessages.length;
  let responsesReceived = 0;

  // Conecta via WebSocket
  const response = ws.connect(wsUrl, {}, function (socket) {
    socket.on('open', () => {
      console.log(`[VU ${__VU}] WebSocket conectado`);
      
      // Envia primeira mensagem imediatamente
      if (messageIndex < testMessages.length) {
        messageStartTime = Date.now();
        socket.send(testMessages[messageIndex]);
        messagesSent.add(1);
        console.log(`[VU ${__VU}] Mensagem ${messageIndex + 1} enviada`);
        messageIndex++;
      }
    });

    socket.on('message', (data) => {
      try {
        const message = JSON.parse(data);
        messagesReceived.add(1);
        
        // Verifica se é resposta do bot
        if (message.sender === 'BOT') {
          const latency = Date.now() - messageStartTime;
          messageLatency.add(latency);
          responsesReceived++;
          console.log(`[VU ${__VU}] Resposta ${responsesReceived} recebida em ${latency}ms`);
          
          // Envia próxima mensagem após receber resposta
          if (messageIndex < testMessages.length) {
            sleep(2); // Aguarda 2 segundos antes de enviar próxima
            messageStartTime = Date.now();
            socket.send(testMessages[messageIndex]);
            messagesSent.add(1);
            console.log(`[VU ${__VU}] Mensagem ${messageIndex + 1} enviada`);
            messageIndex++;
          } else if (responsesReceived >= messagesToSend) {
            // Recebeu todas as respostas, fecha conexão
            sleep(2);
            socket.close();
          }
        }
      } catch (e) {
        console.log(`[VU ${__VU}] Erro ao processar mensagem: ${e}`);
        errorRate.add(1);
      }
    });

    socket.on('error', (e) => {
      console.log(`[VU ${__VU}] Erro WebSocket: ${e}`);
      errorRate.add(1);
    });

    socket.on('close', () => {
      console.log(`[VU ${__VU}] WebSocket fechado`);
    });

    // Timeout de segurança (2 minutos)
    setTimeout(() => {
      if (socket.readyState === 1) { // WebSocket.OPEN
        socket.close();
      }
    }, 120000);
  });

  // Verifica se a conexão foi bem-sucedida
  const connectionSuccess = check(response, {
    'WebSocket conectado': (r) => r && r.status === 101,
  });

  if (!connectionSuccess) {
    errorRate.add(1);
  }

  // Aguarda um pouco antes de iniciar próximo ciclo
  sleep(1);
}

// Função de setup (executada uma vez antes de todos os VUs)
export function setup() {
  console.log('Iniciando teste de carga com múltiplos usuários...');
  console.log(`WebSocket URL: ${WS_URL}`);
  console.log(`API URL: ${API_URL}`);
  return {};
}

// Função de teardown (executada uma vez após todos os VUs)
export function teardown(data) {
  console.log('Teste de carga concluído!');
}
