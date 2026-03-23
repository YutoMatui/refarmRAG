import { useEffect, useState } from "react";
import Sidebar from "../components/Sidebar.jsx";
import ChatBubble from "../components/ChatBubble.jsx";
import { createSession, fetchMessages, fetchSessions, sendMessage } from "../services/api.js";

export default function ChatPage({ token, onLogout }) {
  const [sessions, setSessions] = useState([]);
  const [activeSessionId, setActiveSessionId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [question, setQuestion] = useState("");
  const [loading, setLoading] = useState(false);

  const loadSessions = async () => {
    const result = await fetchSessions(token);
    setSessions(result);
    if (result.length > 0 && !activeSessionId) {
      setActiveSessionId(result[0].id);
    }
  };

  const loadMessages = async (sessionId) => {
    if (!sessionId) {
      setMessages([]);
      return;
    }
    const result = await fetchMessages(token, sessionId);
    setMessages(result);
  };

  useEffect(() => {
    loadSessions();
  }, []);

  useEffect(() => {
    loadMessages(activeSessionId);
  }, [activeSessionId]);

  const handleNewSession = async () => {
    const created = await createSession(token, "新しい相談");
    setSessions((prev) => [created, ...prev]);
    setActiveSessionId(created.id);
  };

  const handleSend = async () => {
    if (!question.trim()) return;

    const optimisticUser = {
      id: `local-${Date.now()}`,
      role: "user",
      content: question,
      references: []
    };

    setMessages((prev) => [...prev, optimisticUser]);
    setQuestion("");
    setLoading(true);

    try {
      const result = await sendMessage(token, activeSessionId, optimisticUser.content);
      if (result.session) {
        setActiveSessionId(result.session.id);
        setSessions((prev) => {
          const filtered = prev.filter((session) => session.id !== result.session.id);
          return [result.session, ...filtered];
        });
      }
      setMessages((prev) => [...prev, result.message]);
    } catch (error) {
      setMessages((prev) => [
        ...prev,
        {
          id: `error-${Date.now()}`,
          role: "assistant",
          content: "回答の取得に失敗しました。もう一度お試しください。",
          references: []
        }
      ]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex">
      <Sidebar
        sessions={sessions}
        activeSessionId={activeSessionId}
        onSelect={setActiveSessionId}
        onNewSession={handleNewSession}
      />
      <main className="flex-1 flex flex-col">
        <header className="flex items-center justify-between px-10 py-6">
          <div>
            <h2 className="text-2xl font-bold text-ink">りふぁーむAIアシスタント</h2>
            <p className="text-sm text-ink/60">Notionの知識を元に回答します。</p>
          </div>
          <button
            onClick={onLogout}
            className="text-sm font-semibold text-primary-green hover:text-primary-green-dark"
          >
            ログアウト
          </button>
        </header>

        <section className="flex-1 px-10 pb-6 overflow-y-auto space-y-4">
          {messages.length === 0 && (
            <div className="bg-white/80 rounded-3xl p-6 shadow-panel">
              <p className="text-sm text-ink/70">
                左の「新しいスレッド」から相談を始めましょう。
              </p>
            </div>
          )}
          {messages.map((message) => (
            <ChatBubble
              key={message.id}
              role={message.role}
              content={message.content}
              references={message.references}
            />
          ))}
          {loading && (
            <div className="flex justify-start">
              <div className="bg-white border border-primary-green/10 rounded-3xl px-5 py-4 text-sm text-ink/60">
                回答を生成中...
              </div>
            </div>
          )}
        </section>

        <footer className="px-10 pb-8">
          <div className="bg-white/90 rounded-3xl shadow-panel p-4 flex gap-4 items-end">
            <textarea
              value={question}
              onChange={(event) => setQuestion(event.target.value)}
              className="flex-1 resize-none border-none focus:outline-none text-sm"
              rows={3}
              placeholder="知りたいことを入力してください"
            />
            <button
              onClick={handleSend}
              className="bg-primary-green text-white rounded-2xl px-6 py-3 font-semibold hover:bg-primary-green-dark transition"
              disabled={loading}
            >
              送信
            </button>
          </div>
        </footer>
      </main>
    </div>
  );
}
