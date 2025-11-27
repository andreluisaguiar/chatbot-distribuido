const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

export async function createUser(username) {
  const response = await fetch(`${API_BASE_URL}/api/v1/users`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({ username })
  });

  if (!response.ok) {
    let message = 'Erro ao criar usuário';
    try {
      const data = await response.json();
      if (data?.detail) message = data.detail;
    } catch (error) {
      // ignore erro de parse
    }
    throw new Error(message);
  }

  const data = await response.json();
  return {
    userId: data.user_id,
    sessionId: data.session_id,
    username: data.username,
  };
}

