import { useState } from "react";
import LoginPage from "./pages/LoginPage.jsx";
import ChatPage from "./pages/ChatPage.jsx";

const STORAGE_KEY = "refarm_ai_token";

export default function App() {
  const [token, setToken] = useState(() => localStorage.getItem(STORAGE_KEY));

  const handleLogin = (nextToken) => {
    localStorage.setItem(STORAGE_KEY, nextToken);
    setToken(nextToken);
  };

  const handleLogout = () => {
    localStorage.removeItem(STORAGE_KEY);
    setToken(null);
  };

  return token ? (
    <ChatPage token={token} onLogout={handleLogout} />
  ) : (
    <LoginPage onLogin={handleLogin} />
  );
}
