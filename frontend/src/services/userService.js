const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

// Função auxiliar para fazer requisições autenticadas
async function authenticatedFetch(url, options = {}) {
  const token = localStorage.getItem('token');
  const headers = {
    'Content-Type': 'application/json',
    ...options.headers
  };

  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  try {
    const response = await fetch(url, {
      ...options,
      headers
    });

    if (!response.ok) {
      let message = 'Erro na requisição';
      try {
        const data = await response.json();
        if (data?.detail) message = data.detail;
      } catch (error) {
        // ignore erro de parse
        message = `Erro ${response.status}: ${response.statusText}`;
      }
      throw new Error(message);
    }

    return response.json();
  } catch (error) {
    // Se for erro de rede (Failed to fetch)
    if (error.message === 'Failed to fetch' || error.name === 'TypeError') {
      throw new Error('Não foi possível conectar ao servidor. Verifique se o backend está rodando em http://localhost:8000');
    }
    throw error;
  }
}

// Registro de novo usuário
export async function registerUser(userData) {
  return authenticatedFetch(`${API_BASE_URL}/api/v1/users/register`, {
    method: 'POST',
    body: JSON.stringify({
      nome: userData.nome,
      sobrenome: userData.sobrenome,
      email: userData.email,
      senha: userData.senha
    })
  });
}

// Login de usuário
export async function loginUser(email, senha) {
  return authenticatedFetch(`${API_BASE_URL}/api/v1/users/login`, {
    method: 'POST',
    body: JSON.stringify({ email, senha })
  });
}

// Obter informações do usuário atual
export async function getCurrentUser() {
  return authenticatedFetch(`${API_BASE_URL}/api/v1/users/me`);
}

// Atualizar informações do usuário
export async function updateUser(userData) {
  return authenticatedFetch(`${API_BASE_URL}/api/v1/users/me`, {
    method: 'PUT',
    body: JSON.stringify(userData)
  });
}

// Listar todos os usuários (requer autenticação)
export async function listUsers(skip = 0, limit = 100) {
  return authenticatedFetch(`${API_BASE_URL}/api/v1/users?skip=${skip}&limit=${limit}`);
}

// Obter usuário por ID
export async function getUserById(userId) {
  return authenticatedFetch(`${API_BASE_URL}/api/v1/users/${userId}`);
}

// Desativar conta do usuário atual
export async function deleteCurrentUser() {
  return authenticatedFetch(`${API_BASE_URL}/api/v1/users/me`, {
    method: 'DELETE'
  });
}

// Função de compatibilidade (mantida para não quebrar código existente)
export async function createUser(username) {
  // Esta função está obsoleta, mas mantida para compatibilidade
  // Em produção, deve ser removida ou redirecionar para registro
  console.warn('createUser está obsoleto. Use registerUser ou loginUser.');
  throw new Error('Esta função está obsoleta. Use o sistema de registro/login.');
}
