import { useState, useEffect } from "react";
import { db } from "../firebase";
import { collection, query, where, orderBy, onSnapshot } from "firebase/firestore";

export default function History({ onNotify }) {
  const [posts, setPosts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filtro, setFiltro] = useState("todos");

  useEffect(() => {
    const q = query(collection(db, "posts"), orderBy("criadoEm", "desc"));
    const unsub = onSnapshot(q, (snap) => {
      setPosts(snap.docs.map((d) => ({ id: d.id, ...d.data() })));
      setLoading(false);
    });
    return unsub;
  }, []);

  const STATUS_OPTS = ["todos", "publicado", "aprovado", "pendente", "erro"];

  const filtrados = filtro === "todos"
    ? posts
    : posts.filter((p) => p.status === filtro);

  const formatDate = (val) => {
    if (!val) return "—";
    const d = val?.toDate ? val.toDate() : new Date(val);
    return d.toLocaleDateString("pt-BR", { day: "2-digit", month: "2-digit", year: "numeric", hour: "2-digit", minute: "2-digit" });
  };

  return (
    <div>
      <div className="section-header">
        <h1>Histórico</h1>
        <p>Todos os posts criados — publicados, pendentes e com erro.</p>
      </div>

      {/* Filtros */}
      <div className="toolbar" style={{ marginBottom: "1.25rem" }}>
        {STATUS_OPTS.map((s) => (
          <button
            key={s}
            className={`btn ${filtro === s ? "btn--primary" : "btn--outline"}`}
            style={{ textTransform: "capitalize", padding: "0.4rem 0.9rem", fontSize: "0.82rem" }}
            onClick={() => setFiltro(s)}
          >
            {s}
          </button>
        ))}
        <div className="toolbar__spacer" />
        <span style={{ fontSize: "0.82rem", color: "var(--texto-suave)" }}>
          {filtrados.length} registro(s)
        </span>
      </div>

      {loading ? (
        <div className="empty-state">
          <div className="spinner" style={{ borderTopColor: "var(--verde-medio)", borderColor: "var(--creme-escuro)" }} />
        </div>
      ) : filtrados.length === 0 ? (
        <div className="empty-state">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
            <circle cx="12" cy="12" r="9" />
            <path d="M12 7v5l3 3" />
          </svg>
          <h3>Nenhum registro</h3>
          <p>Não há posts com o filtro selecionado.</p>
        </div>
      ) : (
        <div style={{ overflowX: "auto" }}>
          <table className="history-table">
            <thead>
              <tr>
                <th>Imagem</th>
                <th>Tema</th>
                <th>Legenda</th>
                <th>Modo</th>
                <th>Status</th>
                <th>Criado em</th>
                <th>Publicado em</th>
              </tr>
            </thead>
            <tbody>
              {filtrados.map((post) => (
                <tr key={post.id}>
                  <td>
                    {post.cloudinaryUrl ? (
                      <img
                        className="history-thumb"
                        src={post.cloudinaryUrl}
                        alt={post.tema}
                      />
                    ) : (
                      <div className="history-thumb" style={{ background: "var(--creme-escuro)", display: "flex", alignItems: "center", justifyContent: "center", fontSize: "0.7rem", color: "var(--texto-suave)" }}>
                        —
                      </div>
                    )}
                  </td>
                  <td style={{ fontWeight: 500, color: "var(--texto-escuro)", maxWidth: 120 }}>{post.tema || "—"}</td>
                  <td style={{ maxWidth: 220, fontSize: "0.82rem" }}>
                    <span style={{ display: "-webkit-box", WebkitLineClamp: 2, WebkitBoxOrient: "vertical", overflow: "hidden" }}>
                      {post.legenda || "—"}
                    </span>
                  </td>
                  <td>
                    <span style={{ fontSize: "0.75rem", padding: "0.2rem 0.55rem", borderRadius: "99px", background: post.modo === "automatico" ? "#E8F5E9" : "#FEF3E2", color: post.modo === "automatico" ? "var(--sucesso)" : "var(--aviso)", fontWeight: 500 }}>
                      {post.modo === "automatico" ? "Auto" : "Manual"}
                    </span>
                  </td>
                  <td>
                    <span className={`post-card__status status--${post.status || "pendente"}`}>
                      {post.status || "pendente"}
                    </span>
                  </td>
                  <td style={{ fontSize: "0.8rem", color: "var(--texto-suave)", whiteSpace: "nowrap" }}>
                    {formatDate(post.criadoEm)}
                  </td>
                  <td style={{ fontSize: "0.8rem", color: "var(--texto-suave)", whiteSpace: "nowrap" }}>
                    {formatDate(post.publicadoEm)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
