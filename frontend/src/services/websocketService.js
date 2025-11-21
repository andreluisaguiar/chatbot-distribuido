export class WebSocketService {
  constructor(url, callbacks = {}) {
    this.url = url;
    this.callbacks = callbacks;
    this.ws = null;
    this.reconnectAttempts = 0;
    this.maxReconnectAttempts = 5;
    this.reconnectDelay = 3000;
    this.connect();
  }

  connect() {
    try {
      this.ws = new WebSocket(this.url);

      this.ws.onopen = () => {
        console.log('WebSocket conectado');
        this.reconnectAttempts = 0;
        if (this.callbacks.onOpen) {
          this.callbacks.onOpen();
        }
      };

      this.ws.onmessage = (event) => {
        if (this.callbacks.onMessage) {
          this.callbacks.onMessage(event.data);
        }
      };

      this.ws.onerror = (error) => {
        console.error('Erro no WebSocket:', error);
        if (this.callbacks.onError) {
          this.callbacks.onError(error);
        }
      };

      this.ws.onclose = () => {
        console.log('WebSocket desconectado');
        if (this.callbacks.onClose) {
          this.callbacks.onClose();
        }
        this.attemptReconnect();
      };
    } catch (error) {
      console.error('Erro ao conectar WebSocket:', error);
      if (this.callbacks.onError) {
        this.callbacks.onError(error);
      }
      this.attemptReconnect();
    }
  }

  attemptReconnect() {
    if (this.reconnectAttempts < this.maxReconnectAttempts) {
      this.reconnectAttempts++;
      console.log(`Tentando reconectar... (${this.reconnectAttempts}/${this.maxReconnectAttempts})`);
      setTimeout(() => {
        this.connect();
      }, this.reconnectDelay);
    } else {
      console.error('Número máximo de tentativas de reconexão atingido');
    }
  }

  sendMessage(message) {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(message);
      return true;
    } else {
      console.error('WebSocket não está conectado');
      return false;
    }
  }

  disconnect() {
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
  }
}

