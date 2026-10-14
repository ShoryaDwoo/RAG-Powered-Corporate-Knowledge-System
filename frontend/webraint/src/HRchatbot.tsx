import { useState, useRef, useEffect, type KeyboardEvent } from "react";

// ── Types ─────────────────────────────────────────────────────────
interface Message {
  id: number;
  role: "user" | "assistant";
  content: string;
  time: string;
}

// ── Helpers ───────────────────────────────────────────────────────
const getNow = (): string =>
  new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });

const SUGGESTED_QUESTIONS: string[] = [
  "What is the leave policy?",
  "How many casual leaves do I get?",
  "What is the minimum password length?",
  "When is salary credited?",
];

const API_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000";
const EMPLOYEE_ID = "EMP001"; // fixed — no user-facing config

// ── Sub-components ────────────────────────────────────────────────
const BotAvatar: React.FC = () => (
  <div style={{
    width: 32, height: 32, borderRadius: "50%",
    background: "linear-gradient(135deg, #2563eb, #1d4ed8)",
    display: "flex", alignItems: "center", justifyContent: "center",
    flexShrink: 0,
  }}>
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
      <path
        d="M12 2a7 7 0 0 1 7 7c0 2.5-1.3 4.7-3.3 6L17 22H7l1.3-7C6.3 13.7 5 11.5 5 9a7 7 0 0 1 7-7z"
        fill="white" opacity="0.9"
      />
    </svg>
  </div>
);

const ChatMessage: React.FC<{ msg: Message }> = ({ msg }) => {
  const isUser = msg.role === "user";
  return (
    <div style={{
      display: "flex",
      flexDirection: isUser ? "row-reverse" : "row",
      alignItems: "flex-end", gap: 8, marginBottom: 18,
    }}>
      {!isUser && <BotAvatar />}
      <div style={{ maxWidth: "72%", minWidth: 60 }}>
        <div style={{
          background: isUser ? "#2563eb" : "#f9fafb",
          color: isUser ? "#fff" : "#111827",
          borderRadius: isUser ? "18px 18px 4px 18px" : "18px 18px 18px 4px",
          padding: "11px 16px",
          fontSize: 14, lineHeight: 1.6,
          boxShadow: "0 1px 2px rgba(0,0,0,0.06)",
          border: isUser ? "none" : "1px solid #e5e7eb",
          whiteSpace: "pre-wrap",
        }}>
          {msg.content}
          {!isUser && msg.content === "" && (
            <span style={{ color: "#9ca3af", fontStyle: "italic" }}>Thinking…</span>
          )}
        </div>
        <div style={{
          fontSize: 11, color: "#9ca3af", marginTop: 4,
          textAlign: isUser ? "right" : "left", paddingLeft: 2,
        }}>
          {msg.time}
        </div>
      </div>
    </div>
  );
};

// ── Main Component ────────────────────────────────────────────────
const WELCOME_MESSAGE: Message = {
  id: 1,
  role: "assistant",
  content: "Hi! I'm your HR assistant. Ask me anything about company policies, leave, payroll, or IT guidelines.",
  time: getNow(),
};

const HRChatbot: React.FC = () => {
  const [open, setOpen] = useState<boolean>(false);
  const [messages, setMessages] = useState<Message[]>([WELCOME_MESSAGE]);
  const [input, setInput] = useState<string>("");
  const [loading, setLoading] = useState<boolean>(false);

  const bottomRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, open]);

  useEffect(() => {
    if (open) setTimeout(() => inputRef.current?.focus(), 100);
  }, [open]);

  const resetChat = (): void => {
    setMessages([{ ...WELCOME_MESSAGE, time: getNow() }]);
  };

  const send = async (overrideText?: string): Promise<void> => {
    const q = (overrideText ?? input).trim();
    if (!q || loading) return;
    setInput("");

    const userMsg: Message = { id: Date.now(), role: "user", content: q, time: getNow() };
    const botId = Date.now() + 1;
    const botMsg: Message = { id: botId, role: "assistant", content: "", time: getNow() };

    setMessages((prev) => [...prev, userMsg, botMsg]);
    setLoading(true);

    try {
      const res = await fetch(`${API_URL}/query/stream`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ employee_id: EMPLOYEE_ID, question: q, top_k: 5 }),
      });

      if (!res.ok || !res.body) throw new Error(`HTTP ${res.status}`);

      const reader = res.body.getReader();
      const decoder = new TextDecoder();

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const lines = decoder.decode(value, { stream: true }).split("\n");
        for (const line of lines) {
          if (!line.startsWith("data: ")) continue;
          try {
            const data = JSON.parse(line.slice(6));
            if (data.token) {
              setMessages((prev) =>
                prev.map((m) =>
                  m.id === botId ? { ...m, content: m.content + data.token } : m
                )
              );
            }
          } catch {
            // skip malformed line
          }
        }
      }
    } catch {
      setMessages((prev) =>
        prev.map((m) =>
          m.id === botId
            ? { ...m, content: "Unable to reach the HR service. Please try again." }
            : m
        )
      );
    } finally {
      setLoading(false);
    }
  };

  const handleKey = (e: KeyboardEvent<HTMLTextAreaElement>): void => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      void send();
    }
  };

  const canSend = input.trim().length > 0 && !loading;

  return (
    <>
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&display=swap');
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body { font-family: 'Inter', sans-serif; }
        @keyframes slideUp {
          from { opacity: 0; transform: translateY(16px) scale(0.97); }
          to   { opacity: 1; transform: translateY(0) scale(1); }
        }
        @keyframes fadeIn { from { opacity: 0; } to { opacity: 1; } }
        @keyframes blink { 0%,100%{opacity:1} 50%{opacity:0} }
        .hr-send-btn:hover:not(:disabled) { background: #1d4ed8 !important; }
        .hr-send-btn:disabled { background: #e5e7eb !important; cursor: not-allowed; }
        .hr-suggest:hover { background: #eff6ff !important; border-color: #93c5fd !important; }
        .hr-fab:hover { transform: scale(1.07); box-shadow: 0 8px 24px rgba(37,99,235,0.35) !important; }
        .hr-icon-btn:hover { background: rgba(255,255,255,0.15) !important; }
        ::-webkit-scrollbar { width: 4px; }
        ::-webkit-scrollbar-track { background: transparent; }
        ::-webkit-scrollbar-thumb { background: #e5e7eb; border-radius: 4px; }
        .cursor { display: inline-block; width: 2px; height: 14px; background: #374151; margin-left: 2px; animation: blink 0.8s infinite; vertical-align: middle; }
      `}</style>

      {/* ── FAB ── */}
      <button
        className="hr-fab"
        onClick={() => setOpen((o) => !o)}
        aria-label="Open HR Assistant"
        style={{
          position: "fixed", bottom: 28, right: 28, zIndex: 1000,
          width: 56, height: 56, borderRadius: "50%", border: "none",
          background: "linear-gradient(135deg, #2563eb, #1d4ed8)",
          boxShadow: "0 4px 16px rgba(37,99,235,0.3)",
          cursor: "pointer", display: "flex", alignItems: "center",
          justifyContent: "center", transition: "transform 0.2s, box-shadow 0.2s",
        }}
      >
        {open ? (
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2.5">
            <line x1="18" y1="6" x2="6" y2="18" />
            <line x1="6" y1="6" x2="18" y2="18" />
          </svg>
        ) : (
          <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2">
            <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
          </svg>
        )}
      </button>

      {/* ── Chat window ── */}
      {open && (
        <div style={{
          position: "fixed", bottom: 96, right: 28, zIndex: 999,
          width: 380, height: 580,
          background: "#fff", borderRadius: 20,
          boxShadow: "0 20px 60px rgba(0,0,0,0.15), 0 4px 16px rgba(0,0,0,0.08)",
          display: "flex", flexDirection: "column", overflow: "hidden",
          animation: "slideUp 0.25s ease",
          border: "1px solid #e5e7eb",
        }}>

          {/* Header */}
          <div style={{
            background: "linear-gradient(135deg, #2563eb, #1d4ed8)",
            padding: "14px 16px", display: "flex",
            alignItems: "center", justifyContent: "space-between", flexShrink: 0,
          }}>
            <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
              <div style={{
                width: 36, height: 36, borderRadius: "50%",
                background: "rgba(255,255,255,0.2)",
                display: "flex", alignItems: "center", justifyContent: "center",
              }}>
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2">
                  <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" />
                  <circle cx="9" cy="7" r="4" />
                  <path d="M23 21v-2a4 4 0 0 0-3-3.87" />
                  <path d="M16 3.13a4 4 0 0 1 0 7.75" />
                </svg>
              </div>
              <div>
                <div style={{ color: "#fff", fontWeight: 600, fontSize: 14 }}>HR Assistant</div>
                <div style={{ color: "rgba(255,255,255,0.75)", fontSize: 11, display: "flex", alignItems: "center", gap: 4 }}>
                  <div style={{ width: 6, height: 6, borderRadius: "50%", background: "#4ade80" }} />
                  Online
                </div>
              </div>
            </div>

            {/* Clear only — settings removed */}
            <button
              className="hr-icon-btn"
              onClick={resetChat}
              title="Clear chat"
              style={{
                background: "transparent", border: "none", cursor: "pointer",
                padding: 6, borderRadius: 8, transition: "background 0.15s",
              }}
            >
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2">
                <polyline points="1 4 1 10 7 10" />
                <path d="M3.51 15a9 9 0 1 0 .49-3.48" />
              </svg>
            </button>
          </div>

          {/* Messages */}
          <div style={{
            flex: 1, overflowY: "auto", padding: "16px 14px",
            display: "flex", flexDirection: "column",
          }}>
            {messages.map((msg, idx) => {
              const isLastBot = msg.role === "assistant" && idx === messages.length - 1 && loading;
              return (
                <div key={msg.id} style={{
                  display: "flex",
                  flexDirection: msg.role === "user" ? "row-reverse" : "row",
                  alignItems: "flex-end", gap: 8, marginBottom: 18,
                }}>
                  {msg.role === "assistant" && <BotAvatar />}
                  <div style={{ maxWidth: "72%", minWidth: 60 }}>
                    <div style={{
                      background: msg.role === "user" ? "#2563eb" : "#f9fafb",
                      color: msg.role === "user" ? "#fff" : "#111827",
                      borderRadius: msg.role === "user" ? "18px 18px 4px 18px" : "18px 18px 18px 4px",
                      padding: "11px 16px", fontSize: 14, lineHeight: 1.6,
                      boxShadow: "0 1px 2px rgba(0,0,0,0.06)",
                      border: msg.role === "user" ? "none" : "1px solid #e5e7eb",
                      whiteSpace: "pre-wrap", minHeight: 42,
                    }}>
                      {msg.content === "" && isLastBot
                        ? <span style={{ color: "#9ca3af", fontStyle: "italic" }}>Thinking…</span>
                        : msg.content
                      }
                      {isLastBot && msg.content !== "" && (
                        <span className="cursor" />
                      )}
                    </div>
                    <div style={{
                      fontSize: 11, color: "#9ca3af", marginTop: 4,
                      textAlign: msg.role === "user" ? "right" : "left", paddingLeft: 2,
                    }}>
                      {msg.time}
                    </div>
                  </div>
                </div>
              );
            })}
            <div ref={bottomRef} />
          </div>

          {/* Suggested questions — only on fresh chat */}
          {messages.length === 1 && !loading && (
            <div style={{
              padding: "0 14px 10px", display: "flex",
              flexWrap: "wrap", gap: 6, flexShrink: 0,
            }}>
              {SUGGESTED_QUESTIONS.map((s, i) => (
                <button
                  key={i}
                  className="hr-suggest"
                  onClick={() => void send(s)}
                  style={{
                    background: "#fff", border: "1px solid #e5e7eb",
                    borderRadius: 20, padding: "5px 12px", fontSize: 12,
                    color: "#374151", cursor: "pointer", transition: "all 0.15s",
                  }}
                >
                  {s}
                </button>
              ))}
            </div>
          )}

          {/* Input bar */}
          <div style={{
            padding: "10px 12px 14px", borderTop: "1px solid #f3f4f6",
            display: "flex", gap: 8, alignItems: "flex-end", flexShrink: 0,
          }}>
            <textarea
              ref={inputRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKey}
              rows={1}
              placeholder="Ask about policies, leave, payroll…"
              style={{
                flex: 1, border: "1px solid #e5e7eb", borderRadius: 12,
                padding: "9px 12px", fontSize: 13, resize: "none",
                outline: "none", fontFamily: "inherit", lineHeight: 1.5,
                maxHeight: 80, overflowY: "auto", transition: "border-color 0.15s",
              }}
              onFocus={(e) => (e.target.style.borderColor = "#2563eb")}
              onBlur={(e) => (e.target.style.borderColor = "#e5e7eb")}
            />
            <button
              className="hr-send-btn"
              onClick={() => void send()}
              disabled={!canSend}
              style={{
                width: 38, height: 38, borderRadius: 10, border: "none",
                background: canSend ? "#2563eb" : "#e5e7eb",
                cursor: canSend ? "pointer" : "not-allowed",
                display: "flex", alignItems: "center", justifyContent: "center",
                flexShrink: 0, transition: "background 0.15s",
              }}
            >
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2.5">
                <line x1="22" y1="2" x2="11" y2="13" />
                <polygon points="22 2 15 22 11 13 2 9 22 2" />
              </svg>
            </button>
          </div>
        </div>
      )}
    </>
  );
};

export default HRChatbot;