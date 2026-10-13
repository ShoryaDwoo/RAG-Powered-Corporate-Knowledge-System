import { useState, useRef, useEffect } from "react";

const BOT_AVATAR = (
  <div style={{
    width: 32, height: 32, borderRadius: "50%",
    background: "linear-gradient(135deg, #2563eb, #1d4ed8)",
    display: "flex", alignItems: "center", justifyContent: "center",
    flexShrink: 0
  }}>
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
      <path d="M12 2a7 7 0 0 1 7 7c0 2.5-1.3 4.7-3.3 6L17 22H7l1.3-7C6.3 13.7 5 11.5 5 9a7 7 0 0 1 7-7z" fill="white" opacity="0.9"/>
    </svg>
  </div>
);

const SourceChip = ({ source }) => (
  <span style={{
    display: "inline-flex", alignItems: "center", gap: 4,
    background: "#eff6ff", border: "1px solid #bfdbfe",
    borderRadius: 6, padding: "2px 8px", fontSize: 11,
    color: "#1d4ed8", fontFamily: "monospace", marginRight: 4, marginTop: 4
  }}>
    <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
      <polyline points="14,2 14,8 20,8"/>
    </svg>
    {source}
  </span>
);

const TypingIndicator = () => (
  <div style={{ display: "flex", alignItems: "center", gap: 10, padding: "4px 0" }}>
    {BOT_AVATAR}
    <div style={{
      background: "#f3f4f6", borderRadius: "18px 18px 18px 4px",
      padding: "10px 16px", display: "flex", gap: 4, alignItems: "center"
    }}>
      {[0, 1, 2].map(i => (
        <div key={i} style={{
          width: 7, height: 7, borderRadius: "50%", background: "#9ca3af",
          animation: "bounce 1.2s infinite",
          animationDelay: `${i * 0.2}s`
        }} />
      ))}
    </div>
  </div>
);

const Message = ({ msg }) => {
  const isUser = msg.role === "user";
  return (
    <div style={{
      display: "flex", flexDirection: isUser ? "row-reverse" : "row",
      alignItems: "flex-end", gap: 8, marginBottom: 18
    }}>
      {!isUser && BOT_AVATAR}
      <div style={{ maxWidth: "72%", minWidth: 60 }}>
        <div style={{
          background: isUser ? "#2563eb" : "#f9fafb",
          color: isUser ? "#fff" : "#111827",
          borderRadius: isUser ? "18px 18px 4px 18px" : "18px 18px 18px 4px",
          padding: "11px 16px",
          fontSize: 14, lineHeight: 1.6,
          boxShadow: "0 1px 2px rgba(0,0,0,0.06)",
          border: isUser ? "none" : "1px solid #e5e7eb"
        }}>
          {msg.content}
        </div>
        {msg.sources && msg.sources.length > 0 && (
          <div style={{ marginTop: 6, paddingLeft: 2 }}>
            <div style={{ fontSize: 11, color: "#6b7280", marginBottom: 3 }}>Sources</div>
            <div>{msg.sources.map((s, i) => <SourceChip key={i} source={s} />)}</div>
          </div>
        )}
        <div style={{
          fontSize: 11, color: "#9ca3af", marginTop: 4,
          textAlign: isUser ? "right" : "left", paddingLeft: 2
        }}>
          {msg.time}
        </div>
      </div>
    </div>
  );
};

const SUGGESTED = [
  "What is the leave policy?",
  "How many casual leaves do I get?",
  "What is the minimum password length?",
  "When is salary credited?",
];

export default function HRChatbot() {
  const [open, setOpen] = useState(false);
  const [messages, setMessages] = useState([
    {
      id: 1, role: "assistant",
      content: "Hi! I'm your HR assistant. Ask me anything about company policies, leave, payroll, or IT guidelines.",
      time: now(), sources: []
    }
  ]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [employeeId, setEmployeeId] = useState("EMP001");
  const [showConfig, setShowConfig] = useState(false);
  const bottomRef = useRef(null);
  const inputRef = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading, open]);

  useEffect(() => {
    if (open) setTimeout(() => inputRef.current?.focus(), 100);
  }, [open]);

  function now() {
    return new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  }

  async function send(text) {
    const q = (text || input).trim();
    if (!q || loading) return;
    setInput("");

    const userMsg = { id: Date.now(), role: "user", content: q, time: now() };
    setMessages(prev => [...prev, userMsg]);
    setLoading(true);

    try {
      const res = await fetch("http://localhost:8000/query", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ employee_id: employeeId, question: q, top_k: 5 }),
      });
      const data = await res.json();
      setMessages(prev => [...prev, {
        id: Date.now() + 1, role: "assistant",
        content: data.answer || "Sorry, I couldn't get a response.",
        sources: data.sources || [],
        time: now()
      }]);
    } catch {
      setMessages(prev => [...prev, {
        id: Date.now() + 1, role: "assistant",
        content: "Unable to reach the HR service. Please try again.",
        sources: [], time: now()
      }]);
    } finally {
      setLoading(false);
    }
  }

  const handleKey = e => {
    if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); send(); }
  };

  return (
    <>
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&display=swap');
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body { font-family: 'Inter', sans-serif; }
        @keyframes bounce {
          0%, 80%, 100% { transform: translateY(0); }
          40% { transform: translateY(-6px); }
        }
        @keyframes slideUp {
          from { opacity: 0; transform: translateY(16px) scale(0.97); }
          to   { opacity: 1; transform: translateY(0) scale(1); }
        }
        @keyframes fadeIn {
          from { opacity: 0; } to { opacity: 1; }
        }
        .send-btn:hover { background: #1d4ed8 !important; }
        .send-btn:disabled { background: #e5e7eb !important; cursor: not-allowed; }
        .suggest-btn:hover { background: #eff6ff !important; border-color: #93c5fd !important; }
        .fab:hover { transform: scale(1.07); box-shadow: 0 8px 24px rgba(37,99,235,0.35) !important; }
        .close-btn:hover { background: rgba(255,255,255,0.15) !important; }
        ::-webkit-scrollbar { width: 4px; }
        ::-webkit-scrollbar-track { background: transparent; }
        ::-webkit-scrollbar-thumb { background: #e5e7eb; border-radius: 4px; }
      `}</style>

      {/* FAB */}
      <button
        className="fab"
        onClick={() => setOpen(o => !o)}
        style={{
          position: "fixed", bottom: 28, right: 28, zIndex: 1000,
          width: 56, height: 56, borderRadius: "50%", border: "none",
          background: "linear-gradient(135deg, #2563eb, #1d4ed8)",
          boxShadow: "0 4px 16px rgba(37,99,235,0.3)",
          cursor: "pointer", display: "flex", alignItems: "center",
          justifyContent: "center", transition: "transform 0.2s, box-shadow 0.2s"
        }}
        aria-label="Open HR Assistant"
      >
        {open ? (
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2.5">
            <line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>
          </svg>
        ) : (
          <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2">
            <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>
          </svg>
        )}
      </button>

      {/* Chat window */}
      {open && (
        <div style={{
          position: "fixed", bottom: 96, right: 28, zIndex: 999,
          width: 380, height: 580,
          background: "#fff", borderRadius: 20,
          boxShadow: "0 20px 60px rgba(0,0,0,0.15), 0 4px 16px rgba(0,0,0,0.08)",
          display: "flex", flexDirection: "column", overflow: "hidden",
          animation: "slideUp 0.25s ease",
          border: "1px solid #e5e7eb"
        }}>

          {/* Header */}
          <div style={{
            background: "linear-gradient(135deg, #2563eb, #1d4ed8)",
            padding: "14px 16px", display: "flex",
            alignItems: "center", justifyContent: "space-between", flexShrink: 0
          }}>
            <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
              <div style={{
                width: 36, height: 36, borderRadius: "50%",
                background: "rgba(255,255,255,0.2)",
                display: "flex", alignItems: "center", justifyContent: "center"
              }}>
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2">
                  <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/>
                  <circle cx="9" cy="7" r="4"/>
                  <path d="M23 21v-2a4 4 0 0 0-3-3.87"/>
                  <path d="M16 3.13a4 4 0 0 1 0 7.75"/>
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
            <div style={{ display: "flex", gap: 4 }}>
              <button
                className="close-btn"
                onClick={() => setShowConfig(s => !s)}
                style={{
                  background: "transparent", border: "none", cursor: "pointer",
                  padding: 6, borderRadius: 8, transition: "background 0.15s",
                  color: "white"
                }}
                title="Settings"
              >
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2">
                  <circle cx="12" cy="12" r="3"/>
                  <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"/>
                </svg>
              </button>
              <button
                className="close-btn"
                onClick={() => setMessages([{
                  id: 1, role: "assistant",
                  content: "Hi! I'm your HR assistant. Ask me anything about company policies, leave, payroll, or IT guidelines.",
                  time: now(), sources: []
                }])}
                style={{
                  background: "transparent", border: "none", cursor: "pointer",
                  padding: 6, borderRadius: 8, transition: "background 0.15s"
                }}
                title="Clear chat"
              >
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2">
                  <polyline points="1 4 1 10 7 10"/>
                  <path d="M3.51 15a9 9 0 1 0 .49-3.48"/>
                </svg>
              </button>
            </div>
          </div>

          {/* Config panel */}
          {showConfig && (
            <div style={{
              padding: "10px 16px", background: "#f8fafc",
              borderBottom: "1px solid #e5e7eb", flexShrink: 0,
              animation: "fadeIn 0.15s ease"
            }}>
              <label style={{ fontSize: 12, color: "#6b7280", fontWeight: 500 }}>Employee ID</label>
              <input
                value={employeeId}
                onChange={e => setEmployeeId(e.target.value)}
                style={{
                  display: "block", marginTop: 4, width: "100%",
                  border: "1px solid #d1d5db", borderRadius: 8,
                  padding: "6px 10px", fontSize: 13, outline: "none",
                  fontFamily: "monospace"
                }}
                placeholder="e.g. EMP001"
              />
            </div>
          )}

          {/* Messages */}
          <div style={{
            flex: 1, overflowY: "auto", padding: "16px 14px",
            display: "flex", flexDirection: "column"
          }}>
            {messages.map(msg => <Message key={msg.id} msg={msg} />)}
            {loading && <TypingIndicator />}
            <div ref={bottomRef} />
          </div>

          {/* Suggestions — show only if just the welcome message */}
          {messages.length === 1 && !loading && (
            <div style={{
              padding: "0 14px 10px", display: "flex",
              flexWrap: "wrap", gap: 6, flexShrink: 0
            }}>
              {SUGGESTED.map((s, i) => (
                <button
                  key={i}
                  className="suggest-btn"
                  onClick={() => send(s)}
                  style={{
                    background: "#fff", border: "1px solid #e5e7eb",
                    borderRadius: 20, padding: "5px 12px", fontSize: 12,
                    color: "#374151", cursor: "pointer", transition: "all 0.15s"
                  }}
                >
                  {s}
                </button>
              ))}
            </div>
          )}

          {/* Input */}
          <div style={{
            padding: "10px 12px 14px", borderTop: "1px solid #f3f4f6",
            display: "flex", gap: 8, alignItems: "flex-end", flexShrink: 0
          }}>
            <textarea
              ref={inputRef}
              value={input}
              onChange={e => setInput(e.target.value)}
              onKeyDown={handleKey}
              rows={1}
              placeholder="Ask about policies, leave, payroll…"
              style={{
                flex: 1, border: "1px solid #e5e7eb", borderRadius: 12,
                padding: "9px 12px", fontSize: 13, resize: "none",
                outline: "none", fontFamily: "inherit", lineHeight: 1.5,
                maxHeight: 80, overflowY: "auto",
                transition: "border-color 0.15s"
              }}
              onFocus={e => e.target.style.borderColor = "#2563eb"}
              onBlur={e => e.target.style.borderColor = "#e5e7eb"}
            />
            <button
              className="send-btn"
              onClick={() => send()}
              disabled={!input.trim() || loading}
              style={{
                width: 38, height: 38, borderRadius: 10, border: "none",
                background: input.trim() && !loading ? "#2563eb" : "#e5e7eb",
                cursor: input.trim() && !loading ? "pointer" : "not-allowed",
                display: "flex", alignItems: "center", justifyContent: "center",
                flexShrink: 0, transition: "background 0.15s"
              }}
            >
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2.5">
                <line x1="22" y1="2" x2="11" y2="13"/>
                <polygon points="22 2 15 22 11 13 2 9 22 2"/>
              </svg>
            </button>
          </div>
        </div>
      )}
    </>
  );
}