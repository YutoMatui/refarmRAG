export default function Sidebar({ sessions, activeSessionId, onSelect, onNewSession }) {
  return (
    <aside className="w-80 bg-white/80 backdrop-blur border-r border-primary-green/10 shadow-panel p-6 flex flex-col gap-6">
      <div>
        <p className="text-sm uppercase tracking-[0.2em] text-primary-green">りふぁーむAI</p>
        <h1 className="text-2xl font-bold text-ink mt-2">チャット履歴</h1>
      </div>
      <button
        className="bg-primary-green text-white rounded-full py-2 px-4 text-sm font-semibold hover:bg-primary-green-dark transition"
        onClick={onNewSession}
      >
        + 新しいスレッド
      </button>
      <div className="flex-1 overflow-y-auto space-y-3">
        {sessions.length === 0 && (
          <p className="text-sm text-ink/60">まだ履歴がありません。</p>
        )}
        {sessions.map((session) => (
          <button
            key={session.id}
            onClick={() => onSelect(session.id)}
            className={`w-full text-left rounded-2xl px-4 py-3 border transition ${
              session.id === activeSessionId
                ? "border-primary-green bg-primary-green-soft text-primary-green-dark"
                : "border-transparent hover:border-primary-green/30 hover:bg-primary-green-soft/60"
            }`}
          >
            <p className="font-semibold text-sm text-ink">{session.title || "無題"}</p>
            <p className="text-xs text-ink/60 mt-1">{new Date(session.created_at).toLocaleString()}</p>
          </button>
        ))}
      </div>
    </aside>
  );
}
