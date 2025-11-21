import React, { useState, useEffect, useRef } from 'react';
import { WebSocketService } from '../services/websocketService';
import ChatMessage from '../components/ChatMessage';
import ChatInput from '../components/ChatInput';
import './ChatPage.css';

const ChatPage = () => {
  const [messages, setMessages] = useState([]);
  const [isConnected, setIsConnected] = useState(false);
  const [userId, setUserId] = useState(null);
  const wsServiceRef = useRef(null);
  const messagesEndRef = useRef(null);

  useEffect(() => {
    // Gera um ID único para o usuário
    const newUserId = generateUserId();
    setUserId(newUserId);

    // Conecta ao WebSocket
    const wsUrl = process.env.REACT_APP_WS_URL || `ws://localhost:8000/ws_chat?id=${newUserId}`;
    const wsService = new WebSocketService(
      wsUrl,
      {
        onOpen: () => {
          console.log('WebSocket conectado');
          setIsConnected(true);
          addSystemMessage('Conectado ao servidor');
        },
        onMessage: (data) => {
          try {
            const message = JSON.parse(data);
            addMessage(message.sender, message.content);
          } catch (error) {
            console.error('Erro ao parsear mensagem:', error);
          }
        },
        onError: (error) => {
          console.error('Erro no WebSocket:', error);
          addSystemMessage('Erro na conexão');
        },
        onClose: () => {
          console.log('WebSocket desconectado');
          setIsConnected(false);
          addSystemMessage('Desconectado do servidor');
        }
      }
    );

    wsServiceRef.current = wsService;

    return () => {
      if (wsServiceRef.current) {
        wsServiceRef.current.disconnect();
      }
    };
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const generateUserId = () => {
    return 'user-' + Math.random().toString(36).substr(2, 9) + '-' + Date.now();
  };

  const addMessage = (sender, content) => {
    setMessages(prev => [...prev, { sender, content, timestamp: new Date() }]);
  };

  const addSystemMessage = (content) => {
    addMessage('SYSTEM', content);
  };

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  const handleSendMessage = (message) => {
    if (wsServiceRef.current && isConnected && message.trim()) {
      wsServiceRef.current.sendMessage(message);
      addMessage('USER', message);
    }
  };

  return (
    <div className="chat-page">
      <div className="chat-container">
        <div className="chat-header">
          <h1>🤖 Chatbot Distribuído</h1>
          <div className={`connection-status ${isConnected ? 'connected' : 'disconnected'}`}>
            <span className="status-dot"></span>
            {isConnected ? 'Conectado' : 'Desconectado'}
          </div>
        </div>

        <div className="chat-messages">
          {messages.map((msg, index) => (
            <ChatMessage
              key={index}
              sender={msg.sender}
              content={msg.content}
              timestamp={msg.timestamp}
            />
          ))}
          <div ref={messagesEndRef} />
        </div>

        <ChatInput
          onSendMessage={handleSendMessage}
          disabled={!isConnected}
        />
      </div>
    </div>
  );
};

export default ChatPage;

