export default function Sidebar({ activePage, setActivePage }) {
  const nav = [
    {
      id: "queue",
      label: "Fila de Posts",
      icon: (
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
          <rect x="3" y="3" width="7" height="7" rx="1.5" />
          <rect x="14" y="3" width="7" height="7" rx="1.5" />
          <rect x="3" y="14" width="7" height="7" rx="1.5" />
          <rect x="14" y="14" width="7" height="7" rx="1.5" />
        </svg>
      ),
    },
    {
      id: "editor",
      label: "Novo Post",
      icon: (
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
          <circle cx="12" cy="12" r="9" />
          <line x1="12" y1="8" x2="12" y2="16" />
          <line x1="8" y1="12" x2="16" y2="12" />
        </svg>
      ),
    },
    {
      id: "history",
      label: "Histórico",
      icon: (
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
          <circle cx="12" cy="12" r="9" />
          <polyline points="12 7 12 12 15 15" />
        </svg>
      ),
    },
  ];

  return (
    <aside className="sidebar">
      <div className="sidebar__brand">
        AlvoreSer
        <span>Posts Studio</span>
      </div>

      {nav.map((item) => (
        <button
          key={item.id}
          className={`sidebar__nav-btn ${activePage === item.id ? "sidebar__nav-btn--active" : ""}`}
          onClick={() => setActivePage(item.id)}
        >
          {item.icon}
          <span>{item.label}</span>
        </button>
      ))}

      <div className="sidebar__footer">
        AlvoreSer Clínica<br />Posts Studio v1.0
      </div>
    </aside>
  );
}
