import React, { useState, useEffect, useRef, useCallback } from 'react';
import { WebSocketService } from '../services/websocketService';
import ChatMessage from '../components/ChatMessage';
import ChatInput from '../components/ChatInput';
import './ChatPage.css';

const ChatPage = ({ userInfo: propUserInfo, onLogout }) => {
  const [messages, setMessages] = useState([]);
  const [isConnected, setIsConnected] = useState(false);
  const [userInfo] = useState(() => {
    // Usa userInfo das props ou do localStorage
    if (propUserInfo) return propUserInfo;
    const stored = localStorage.getItem('user');
    return stored ? JSON.parse(stored) : null;
  });
  const wsServiceRef = useRef(null);
  const messagesEndRef = useRef(null);

  const addMessage = useCallback((sender, content) => {
    setMessages(prev => [...prev, { sender, content, timestamp: new Date() }]);
  }, []);

  const addSystemMessage = useCallback((content) => {
    addMessage('SYSTEM', content);
  }, [addMessage]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    if (userInfo) {
      addSystemMessage(`Bem-vindo, ${userInfo.nome} ${userInfo.sobrenome}!`);
    }
  }, [addSystemMessage, userInfo]);

  useEffect(() => {
    const sessionId = localStorage.getItem('sessionId') || userInfo?.session_id;
    if (!sessionId) return;

    const baseUrl = process.env.REACT_APP_WS_URL || 'ws://localhost:8000/ws_chat';
    const separator = baseUrl.includes('?') ? '&' : '?';
    const wsUrl = `${baseUrl}${separator}id=${sessionId}`;

    const wsService = new WebSocketService(
      wsUrl,
      {
        onOpen: () => {
          console.log('WebSocket conectado');
          setIsConnected(true);
          const nome = userInfo?.nome || userInfo?.username || 'Usuário';
          addSystemMessage(`Conectado ao servidor como ${nome}`);
        },
        onMessage: (data) => {
          try {
            const message = JSON.parse(data);
            console.log('Mensagem recebida do WebSocket:', message);
            // Normaliza o sender para garantir compatibilidade
            const sender = message.sender === 'BOT' ? 'BOT' : message.sender;
            addMessage(sender, message.content);
          } catch (error) {
            console.error('Erro ao parsear mensagem:', error);
            console.error('Dados recebidos:', data);
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
  }, [userInfo, addMessage, addSystemMessage]);

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSendMessage = (message) => {
    if (wsServiceRef.current && isConnected && message.trim()) {
      wsServiceRef.current.sendMessage(message);
      addMessage('USER', message);
    }
  };

  const renderUserInfo = () => {
    if (!userInfo) return null;
    return (
      <div className="user-details">
        <div><strong>Usuário:</strong> {userInfo.nome} {userInfo.sobrenome}</div>
        <div><strong>Email:</strong> {userInfo.email}</div>
        {onLogout && (
          <button onClick={onLogout} className="logout-button">Sair</button>
        )}
      </div>
    );
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

        <div className="user-setup">
          {renderUserInfo()}
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
          placeholder="Digite sua mensagem..."
          disabledPlaceholder={userInfo ? 'Conectando...' : 'Crie um usuário para iniciar'}
        />
      </div>
    </div>
  );
};

export default ChatPage;

