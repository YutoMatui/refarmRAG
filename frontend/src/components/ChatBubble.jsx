export default function ChatBubble({ role, content, references }) {
  const isUser = role === "user";

  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"}`}>
      <div
        className={`max-w-[70%] rounded-3xl px-5 py-4 shadow-sm ${
          isUser
            ? "bg-primary-green text-white"
            : "bg-white border border-primary-green/10 text-ink"
        }`}
      >
        <p className="whitespace-pre-wrap text-sm leading-relaxed">{content}</p>
        {!isUser && references && references.length > 0 && (
          <div className="mt-3 border-t border-primary-green/10 pt-3 space-y-1">
            <p className="text-xs uppercase tracking-wider text-primary-green">参照</p>
            {references.map((ref) => (
              <a
                key={ref.url}
                href={ref.url}
                target="_blank"
                rel="noreferrer"
                className="block text-xs text-primary-green-dark underline underline-offset-4"
              >
                {ref.title}
              </a>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
