// App.tsx
import HRChatbot from "./HRchatbot";

export default function App() {
  return (
    <div style={{ minHeight: "100vh", background: "#f9fafb", fontFamily: "Inter, sans-serif" }}>

      {/* ── Top Nav ── */}
      <nav style={{
        background: "#fff", borderBottom: "1px solid #e5e7eb",
        padding: "0 32px", height: 60,
        display: "flex", alignItems: "center", justifyContent: "space-between",
        position: "sticky", top: 0, zIndex: 100,
      }}>
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <div style={{
            width: 32, height: 32, borderRadius: 8,
            background: "linear-gradient(135deg, #2563eb, #1d4ed8)",
            display: "flex", alignItems: "center", justifyContent: "center",
          }}>
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2">
              <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" />
              <circle cx="9" cy="7" r="4" />
              <path d="M23 21v-2a4 4 0 0 0-3-3.87" />
              <path d="M16 3.13a4 4 0 0 1 0 7.75" />
            </svg>
          </div>
          <span style={{ fontWeight: 700, fontSize: 16, color: "#111827" }}>PeopleHub</span>
        </div>

        <div style={{ display: "flex", gap: 28 }}>
          {["Dashboard", "Policies", "Leave", "Payroll", "Directory"].map((item) => (
            <span key={item} style={{
              fontSize: 14, color: item === "Dashboard" ? "#2563eb" : "#6b7280",
              cursor: "pointer", fontWeight: item === "Dashboard" ? 600 : 400,
              borderBottom: item === "Dashboard" ? "2px solid #2563eb" : "2px solid transparent",
              paddingBottom: 4,
            }}>
              {item}
            </span>
          ))}
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <div style={{
            width: 8, height: 8, borderRadius: "50%", background: "#22c55e",
          }} />
          <span style={{ fontSize: 13, color: "#374151" }}>EMP001</span>
          <div style={{
            width: 34, height: 34, borderRadius: "50%",
            background: "linear-gradient(135deg, #2563eb, #1d4ed8)",
            display: "flex", alignItems: "center", justifyContent: "center",
            color: "#fff", fontWeight: 600, fontSize: 13,
          }}>
            A
          </div>
        </div>
      </nav>

      {/* ── Page content ── */}
      <div style={{ maxWidth: 1100, margin: "0 auto", padding: "32px 24px" }}>

        {/* Welcome banner */}
        <div style={{
          background: "linear-gradient(135deg, #2563eb, #1d4ed8)",
          borderRadius: 16, padding: "28px 32px", marginBottom: 28,
          display: "flex", justifyContent: "space-between", alignItems: "center",
        }}>
          <div>
            <div style={{ color: "rgba(255,255,255,0.75)", fontSize: 13, marginBottom: 6 }}>
              Wednesday, {new Date().toLocaleDateString("en-IN", { day: "numeric", month: "long", year: "numeric" })}
            </div>
            <h1 style={{ color: "#fff", fontSize: 22, fontWeight: 700, margin: 0 }}>
              Good morning, Arjun 👋
            </h1>
            <p style={{ color: "rgba(255,255,255,0.8)", fontSize: 14, marginTop: 6 }}>
              HR-Admin · Nimbus Technologies India Pvt. Ltd.
            </p>
          </div>
          <div style={{
            background: "rgba(255,255,255,0.15)", borderRadius: 12,
            padding: "16px 24px", textAlign: "center",
          }}>
            <div style={{ color: "#fff", fontSize: 28, fontWeight: 700 }}>8</div>
            <div style={{ color: "rgba(255,255,255,0.8)", fontSize: 12 }}>Leave balance</div>
          </div>
        </div>

        {/* Stat cards */}
        <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 16, marginBottom: 28 }}>
          {[
            { label: "Documents indexed", value: "11", icon: "📄", color: "#eff6ff", border: "#bfdbfe" },
            { label: "Policies active", value: "8",  icon: "📋", color: "#f0fdf4", border: "#bbf7d0" },
            { label: "Open requests",   value: "3",  icon: "📬", color: "#fefce8", border: "#fde68a" },
            { label: "Team members",    value: "42", icon: "👥", color: "#fdf4ff", border: "#e9d5ff" },
          ].map((card) => (
            <div key={card.label} style={{
              background: "#fff", border: "1px solid #e5e7eb",
              borderRadius: 12, padding: "20px 20px",
              display: "flex", alignItems: "center", gap: 14,
            }}>
              <div style={{
                width: 44, height: 44, borderRadius: 10,
                background: card.color, border: `1px solid ${card.border}`,
                display: "flex", alignItems: "center", justifyContent: "center",
                fontSize: 20,
              }}>
                {card.icon}
              </div>
              <div>
                <div style={{ fontSize: 22, fontWeight: 700, color: "#111827" }}>{card.value}</div>
                <div style={{ fontSize: 12, color: "#6b7280" }}>{card.label}</div>
              </div>
            </div>
          ))}
        </div>

        {/* Two-column bottom */}
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 20 }}>

          {/* Recent policies */}
          <div style={{
            background: "#fff", border: "1px solid #e5e7eb",
            borderRadius: 12, padding: "20px 24px",
          }}>
            <div style={{ fontWeight: 600, fontSize: 15, color: "#111827", marginBottom: 16 }}>
              Recent Policies
            </div>
            {[
              { name: "IT & Information Security Policy", date: "1 Apr 2026", tag: "IT" },
              { name: "Employee Handbook & HR Policies", date: "1 Apr 2026", tag: "HR" },
              { name: "Payroll & Compensation Policy",   date: "1 Apr 2026", tag: "Finance" },
              { name: "Travel & Expense Policy",         date: "1 Apr 2026", tag: "Finance" },
              { name: "Exit & Separation Policy",        date: "1 Jan 2026", tag: "HR" },
            ].map((p) => (
              <div key={p.name} style={{
                display: "flex", justifyContent: "space-between",
                alignItems: "center", padding: "10px 0",
                borderBottom: "1px solid #f3f4f6",
              }}>
                <div style={{ fontSize: 13, color: "#374151" }}>{p.name}</div>
                <div style={{ display: "flex", alignItems: "center", gap: 8, flexShrink: 0 }}>
                  <span style={{
                    background: "#eff6ff", color: "#2563eb",
                    fontSize: 11, borderRadius: 6, padding: "2px 8px",
                  }}>
                    {p.tag}
                  </span>
                  <span style={{ fontSize: 11, color: "#9ca3af" }}>{p.date}</span>
                </div>
              </div>
            ))}
          </div>

          {/* Quick links */}
          <div style={{
            background: "#fff", border: "1px solid #e5e7eb",
            borderRadius: 12, padding: "20px 24px",
          }}>
            <div style={{ fontWeight: 600, fontSize: 15, color: "#111827", marginBottom: 16 }}>
              Quick Actions
            </div>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
              {[
                { label: "Apply Leave",       icon: "🏖️" },
                { label: "View Payslip",      icon: "💰" },
                { label: "Raise IT Ticket",   icon: "🖥️" },
                { label: "Submit Expense",    icon: "🧾" },
                { label: "Book Travel",       icon: "✈️" },
                { label: "Exit Checklist",    icon: "📝" },
              ].map((action) => (
                <div key={action.label} style={{
                  border: "1px solid #e5e7eb", borderRadius: 10,
                  padding: "14px 16px", cursor: "pointer",
                  display: "flex", alignItems: "center", gap: 10,
                  transition: "border-color 0.15s",
                }}
                  onMouseEnter={(e) => (e.currentTarget.style.borderColor = "#2563eb")}
                  onMouseLeave={(e) => (e.currentTarget.style.borderColor = "#e5e7eb")}
                >
                  <span style={{ fontSize: 20 }}>{action.icon}</span>
                  <span style={{ fontSize: 13, color: "#374151", fontWeight: 500 }}>
                    {action.label}
                  </span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* ── HR Chatbot (untouched) ── */}
      <HRChatbot />
    </div>
  );
}