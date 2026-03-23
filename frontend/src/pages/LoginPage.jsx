import { useState } from "react";
import { login, register } from "../services/api.js";

export default function LoginPage({ onLogin }) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (mode) => {
    try {
      setLoading(true);
      setError("");
      const result =
        mode === "register"
          ? await register(email, password)
          : await login(email, password);
      onLogin(result.access_token);
    } catch (err) {
      setError(err.message || "ログインに失敗しました。");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center px-6">
      <div className="bg-white/90 backdrop-blur rounded-3xl shadow-panel p-10 w-full max-w-md">
        <p className="text-sm uppercase tracking-[0.2em] text-primary-green">りふぁーむAI</p>
        <h1 className="text-2xl font-bold text-ink mt-2">メンバーログイン</h1>
        <p className="text-sm text-ink/60 mt-2">
          認証済みのメンバーのみアクセスできます。
        </p>

        <div className="mt-6 space-y-4">
          <label className="block">
            <span className="text-xs text-ink/70">メールアドレス</span>
            <input
              type="email"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              className="mt-2 w-full rounded-2xl border border-primary-green/20 px-4 py-3 focus:outline-none focus:ring-2 focus:ring-primary-green/40"
              placeholder="name@example.com"
            />
          </label>
          <label className="block">
            <span className="text-xs text-ink/70">パスワード</span>
            <input
              type="password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              className="mt-2 w-full rounded-2xl border border-primary-green/20 px-4 py-3 focus:outline-none focus:ring-2 focus:ring-primary-green/40"
              placeholder="••••••••"
            />
          </label>
        </div>

        {error && <p className="text-sm text-red-600 mt-4">{error}</p>}

        <div className="mt-6 flex flex-col gap-3">
          <button
            className="bg-primary-green text-white rounded-full py-3 font-semibold hover:bg-primary-green-dark transition"
            onClick={() => handleSubmit("login")}
            disabled={loading}
          >
            {loading ? "ログイン中..." : "ログイン"}
          </button>
          <button
            className="border border-primary-green text-primary-green rounded-full py-3 font-semibold hover:bg-primary-green-soft transition"
            onClick={() => handleSubmit("register")}
            disabled={loading}
          >
            初回登録
          </button>
        </div>
      </div>
    </div>
  );
}
