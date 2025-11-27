import React, { useState, useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import LoginPage from './pages/LoginPage';
import RegisterPage from './pages/RegisterPage';
import ChatPage from './pages/ChatPage';
import './App.css';

function AppContent() {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [userInfo, setUserInfo] = useState(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    // Verifica se há token e usuário salvos
    const token = localStorage.getItem('token');
    const userStr = localStorage.getItem('user');
    
    if (token && userStr) {
      try {
        const user = JSON.parse(userStr);
        setUserInfo(user);
        setIsAuthenticated(true);
      } catch (error) {
        // Token ou usuário inválido, limpa storage
        localStorage.removeItem('token');
        localStorage.removeItem('user');
        localStorage.removeItem('sessionId');
      }
    }
    setIsLoading(false);
  }, []);

  const handleLoginSuccess = (response) => {
    setUserInfo(response.user);
    setIsAuthenticated(true);
  };

  const handleRegisterSuccess = (response) => {
    setUserInfo(response.user);
    setIsAuthenticated(true);
  };

  const handleLogout = () => {
    localStorage.removeItem('token');
    localStorage.removeItem('user');
    localStorage.removeItem('sessionId');
    setUserInfo(null);
    setIsAuthenticated(false);
  };

  if (isLoading) {
    return (
      <div style={{ 
        display: 'flex', 
        justifyContent: 'center', 
        alignItems: 'center', 
        height: '100vh',
        background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)'
      }}>
        <div style={{ color: 'white', fontSize: '18px' }}>Carregando...</div>
      </div>
    );
  }

  // Rotas públicas
  if (!isAuthenticated) {
    return (
      <Routes>
        <Route path="/register" element={<RegisterPage onRegisterSuccess={handleRegisterSuccess} />} />
        <Route path="/login" element={<LoginPage onLoginSuccess={handleLoginSuccess} />} />
        <Route path="*" element={<LoginPage onLoginSuccess={handleLoginSuccess} />} />
      </Routes>
    );
  }

  // Rotas protegidas
  return (
    <Routes>
      <Route path="/chat" element={<ChatPage userInfo={userInfo} onLogout={handleLogout} />} />
      <Route path="/register" element={<Navigate to="/chat" replace />} />
      <Route path="/login" element={<Navigate to="/chat" replace />} />
      <Route path="/" element={<Navigate to="/chat" replace />} />
    </Routes>
  );
}

function App() {
  return (
    <Router>
      <AppContent />
    </Router>
  );
}

export default App;
