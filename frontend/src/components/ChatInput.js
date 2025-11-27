import React, { useState } from 'react';
import './ChatInput.css';

const ChatInput = ({
  onSendMessage,
  disabled,
  placeholder = "Digite sua mensagem...",
  disabledPlaceholder = "Conectando..."
}) => {
  const [message, setMessage] = useState('');

  const handleSubmit = (e) => {
    e.preventDefault();
    if (message.trim() && !disabled) {
      onSendMessage(message);
      setMessage('');
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  return (
    <div className="chat-input-container">
      <form onSubmit={handleSubmit} className="chat-input-form">
        <input
          type="text"
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          onKeyPress={handleKeyPress}
          placeholder={disabled ? disabledPlaceholder : placeholder}
          disabled={disabled}
          className="chat-input"
        />
        <button
          type="submit"
          disabled={disabled || !message.trim()}
          className="send-button"
        >
          Enviar
        </button>
      </form>
    </div>
  );
};

export default ChatInput;

