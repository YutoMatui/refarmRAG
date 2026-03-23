const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

async function request(path, options = {}) {
  const { headers: extraHeaders, ...rest } = options;
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...rest,
    headers: {
      "Content-Type": "application/json",
      ...(extraHeaders || {})
    },
  });

  if (!response.ok) {
    let errorMessage = "Request failed";
    try {
      const body = await response.json();
      errorMessage = body.detail || body.message || JSON.stringify(body);
    } catch {
      try {
        errorMessage = await response.text() || errorMessage;
      } catch {
        // レスポンスボディが読めない場合はデフォルトメッセージを使用
      }
    }
    throw new Error(String(errorMessage));
  }

  return response.json();
}

export async function login(email, password) {
  return request("/auth/login", {
    method: "POST",
    body: JSON.stringify({ email, password })
  });
}

export async function register(email, password) {
  return request("/auth/register", {
    method: "POST",
    body: JSON.stringify({ email, password })
  });
}

export async function fetchSessions(token) {
  return request("/history/sessions", {
    headers: {
      Authorization: `Bearer ${token}`
    }
  });
}

export async function createSession(token, title) {
  return request("/history/sessions", {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`
    },
    body: JSON.stringify({ title })
  });
}

export async function fetchMessages(token, sessionId) {
  return request(`/history/sessions/${sessionId}/messages`, {
    headers: {
      Authorization: `Bearer ${token}`
    }
  });
}

export async function sendMessage(token, sessionId, question) {
  return request("/chat", {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`
    },
    body: JSON.stringify({ session_id: sessionId, question })
  });
}
