import React, { useState, useEffect, useRef, useCallback } from 'react';
import { WebSocketService } from '../services/websocketService';
import { createUser } from '../services/userService';
import ChatMessage from '../components/ChatMessage';
import ChatInput from '../components/ChatInput';
import './ChatPage.css';

const ChatPage = () => {
  const [messages, setMessages] = useState([]);
  const [isConnected, setIsConnected] = useState(false);
  const [userInfo, setUserInfo] = useState(null);
  const [usernameInput, setUsernameInput] = useState('');
  const [isCreatingUser, setIsCreatingUser] = useState(false);
  const [creationError, setCreationError] = useState('');
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
    addSystemMessage('Crie um usuário para iniciar a conversa.');
  }, [addSystemMessage]);

  useEffect(() => {
    if (!userInfo?.sessionId) return;

    const baseUrl = process.env.REACT_APP_WS_URL || 'ws://localhost:8000/ws_chat';
    const separator = baseUrl.includes('?') ? '&' : '?';
    const wsUrl = `${baseUrl}${separator}id=${userInfo.sessionId}`;

    const wsService = new WebSocketService(
      wsUrl,
      {
        onOpen: () => {
          console.log('WebSocket conectado');
          setIsConnected(true);
          addSystemMessage(`Conectado ao servidor como ${userInfo.username}`);
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
  }, [userInfo?.sessionId, userInfo?.username, addMessage, addSystemMessage]);

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleCreateUser = async (event) => {
    event.preventDefault();
    if (!usernameInput.trim()) {
      setCreationError('Informe um nome de usuário.');
      return;
    }

    setIsCreatingUser(true);
    setCreationError('');
    try {
      const data = await createUser(usernameInput.trim());
      setUserInfo(data);
      addSystemMessage(`Usuário ${data.username} criado com sucesso. Sessão pronta!`);
    } catch (error) {
      setCreationError(error.message);
    } finally {
      setIsCreatingUser(false);
    }
  };

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
        <div><strong>Usuário:</strong> {userInfo.username}</div>
        <div><strong>User ID:</strong> {userInfo.userId}</div>
        <div className="session-id"><strong>Session ID:</strong> {userInfo.sessionId}</div>
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
          <form className="user-form" onSubmit={handleCreateUser}>
            <input
              type="text"
              value={usernameInput}
              onChange={(e) => setUsernameInput(e.target.value)}
              placeholder="Nome do usuário"
              className="user-input"
            />
            <button type="submit" disabled={isCreatingUser}>
              {isCreatingUser ? 'Criando...' : 'Criar usuário'}
            </button>
          </form>
          {creationError && <div className="error-message">{creationError}</div>}
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

