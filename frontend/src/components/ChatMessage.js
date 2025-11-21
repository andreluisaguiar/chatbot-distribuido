import React from 'react';
import './ChatMessage.css';

const ChatMessage = ({ sender, content, timestamp }) => {
  const isUser = sender === 'USER';
  const isSystem = sender === 'SYSTEM';
  const isBot = sender === 'BOT';

  const formatTime = (date) => {
    if (!date) return '';
    return new Date(date).toLocaleTimeString('pt-BR', {
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  return (
    <div className={`chat-message ${isUser ? 'user' : isSystem ? 'system' : 'bot'}`}>
      <div className="message-content">
        <div className="message-header">
          <span className="message-sender">
            {isUser ? '👤 Você' : isSystem ? '⚙️ Sistema' : '🤖 Bot'}
          </span>
          {timestamp && (
            <span className="message-time">{formatTime(timestamp)}</span>
          )}
        </div>
        <div className="message-text">{content}</div>
      </div>
    </div>
  );
};

export default ChatMessage;

