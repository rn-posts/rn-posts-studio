import { useState, useEffect } from "react";
import { db } from "../firebase";
import {
  collection, onSnapshot, doc, updateDoc, deleteDoc, query, orderBy,
} from "firebase/firestore";

const MAKE_URL    = import.meta.env.VITE_MAKE_WEBHOOK_URL || "";
const RENDER_URL  = import.meta.env.VITE_RENDER_URL || "";

const STATUS_LABEL = {
  pendente:  "Pendente",
  aprovado:  "Aprovado",
  publicado: "Publicado",
  erro:      "Erro",
};

export default function PostQueue({ onEdit, onNotify }) {
  const [posts,      setPosts]      = useState([]);
  const [loading,    setLoading]    = useState(true);
  const [publishing, setPublishing] = useState(null);

  useEffect(() => {
    const q = query(collection(db, "posts"), orderBy("criadoEm", "desc"));
    const unsub = onSnapshot(q, (snap) => {
      setPosts(snap.docs.map((d) => ({ id: d.id, ...d.data() })));
      setLoading(false);
    });
    return unsub;
  }, []);

  // Aprova o post — muda status para "aprovado" no Firestore
  // Se modo automatico, ja dispara publicacao
  const handleAprovar = async (post) => {
    try {
      await updateDoc(doc(db, "posts", post.id), { status: "aprovado" });
      onNotify("Post aprovado ✓");
      // Modo automatico: publica imediatamente apos aprovacao
      if (post.modo === "automatico") {
        await handlePublicar({ ...post, status: "aprovado" });
      }
    } catch (e) {
      onNotify("Erro ao aprovar: " + e.message, "error");
    }
  };

  // Publica — dispara webhook Make e atualiza status
  const handlePublicar = async (post) => {
    setPublishing(post.id);
    try {
      if (!MAKE_URL) {
        // Make nao configurado — apenas marca como publicado
        await updateDoc(doc(db, "posts", post.id), {
          status: "publicado",
          publicadoEm: new Date().toISOString(),
        });
        onNotify("Post marcado como publicado (Make nao configurado).");
        return;
      }

      const res = await fetch(MAKE_URL, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          cloudinary_url: post.cloudinaryUrl,
          legenda:        post.legenda,
          tema:           post.tema,
          modo:           post.modo || "manual",
        }),
      });

      if (!res.ok) throw new Error(`Make retornou ${res.status}`);

      await updateDoc(doc(db, "posts", post.id), {
        status:       "publicado",
        publicadoEm:  new Date().toISOString(),
      });

      // Atualiza status na planilha Google Sheets tambem
      if (post.linhaSheet) {
        try {
          await fetch(`${RENDER_URL}/atualizar-status`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ linha: post.linhaSheet, status: "Publicado ✅" }),
          });
        } catch (e) { console.warn("Erro ao atualizar planilha:", e); }
      }

      onNotify("Publicado no Instagram ✓");
    } catch (e) {
      await updateDoc(doc(db, "posts", post.id), { status: "erro" });
      onNotify("Erro ao publicar: " + e.message, "error");
    } finally {
      setPublishing(null);
    }
  };

  const handleExcluir = async (post) => {
    if (!window.confirm("Excluir este post da fila?")) return;
    await deleteDoc(doc(db, "posts", post.id));
    onNotify("Post removido.");
  };

  const pendentes  = posts.filter(p => p.status === "pendente").length;
  const aprovados  = posts.filter(p => p.status === "aprovado").length;

  if (loading) {
    return (
      <div className="empty-state">
        <div className="spinner" style={{ borderTopColor: "var(--verde-medio)", borderColor: "var(--creme-escuro)" }} />
      </div>
    );
  }

  return (
    <div>
      <div className="section-header">
        <h1>Fila de Posts</h1>
        <p>
          {pendentes > 0 && <span style={{ color: "var(--aviso)", fontWeight: 600 }}>{pendentes} aguardando aprovação</span>}
          {pendentes > 0 && aprovados > 0 && " · "}
          {aprovados > 0 && <span style={{ color: "var(--sucesso)", fontWeight: 600 }}>{aprovados} prontos para publicar</span>}
          {pendentes === 0 && aprovados === 0 && "Nenhum post pendente"}
        </p>
      </div>

      {posts.length === 0 ? (
        <div className="empty-state">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
            <rect x="3" y="3" width="18" height="18" rx="3" />
            <path d="M9 12h6M12 9v6" />
          </svg>
          <h3>Nenhum post na fila</h3>
          <p>Crie um novo post para começar.</p>
        </div>
      ) : (
        <div className="post-grid">
          {posts.map((post) => (
            <PostCard
              key={post.id}
              post={post}
              onEdit={onEdit}
              onAprovar={handleAprovar}
              onPublicar={handlePublicar}
              onExcluir={handleExcluir}
              isPublishing={publishing === post.id}
            />
          ))}
        </div>
      )}
    </div>
  );
}

function PostCard({ post, onEdit, onAprovar, onPublicar, onExcluir, isPublishing }) {
  const [expandido, setExpandido] = useState(false);

  return (
    <div className="post-card">
      {/* Imagem */}
      <div className="post-card__image">
        {post.cloudinaryUrl ? (
          <img src={post.cloudinaryUrl} alt={post.tema} loading="lazy" />
        ) : (
          <div className="post-card__image post-card__image--placeholder">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
              <rect x="3" y="3" width="18" height="18" rx="2" />
              <circle cx="8.5" cy="8.5" r="1.5" />
              <polyline points="21 15 16 10 5 21" />
            </svg>
            <span>Sem imagem</span>
          </div>
        )}
      </div>

      {/* Corpo */}
      <div className="post-card__body">
        {post.tema && (
          <div className="post-card__tema">{post.tema}</div>
        )}
        <div className="post-card__legenda" style={{ cursor: "pointer" }} onClick={() => setExpandido(!expandido)}>
          {expandido
            ? post.legenda
            : (post.legenda?.slice(0, 100) + (post.legenda?.length > 100 ? "…" : "")) || <em style={{ color: "var(--texto-suave)" }}>Sem legenda</em>}
          {post.legenda?.length > 100 && (
            <span style={{ fontSize: "0.72rem", color: "var(--verde-medio)", marginLeft: 4 }}>
              {expandido ? "↑ menos" : "↓ mais"}
            </span>
          )}
        </div>
      </div>

      {/* Rodapé */}
      <div className="post-card__footer">
        <span className={`post-card__status status--${post.status || "pendente"}`}>
          {STATUS_LABEL[post.status] || "Pendente"}
        </span>

        <div className="post-card__actions">
          {/* Ver tamanho real */}
          {post.cloudinaryUrl && (
            <a href={post.cloudinaryUrl} target="_blank" rel="noreferrer"
              className="btn--icon" title="Ver imagem completa">
              <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M18 13v6a2 2 0 01-2 2H5a2 2 0 01-2-2V8a2 2 0 012-2h6"/>
                <polyline points="15 3 21 3 21 9"/>
                <line x1="10" y1="14" x2="21" y2="3"/>
              </svg>
            </a>
          )}

          {/* Editar */}
          <button className="btn--icon" onClick={() => onEdit(post)} title="Editar">
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M11 4H4a2 2 0 00-2 2v14a2 2 0 002 2h14a2 2 0 002-2v-7"/>
              <path d="M18.5 2.5a2.121 2.121 0 013 3L12 15l-4 1 1-4 9.5-9.5z"/>
            </svg>
          </button>

          {/* Aprovar — so se pendente */}
          {post.status === "pendente" && (
            <button
              className="btn btn--outline"
              onClick={() => onAprovar(post)}
              style={{ fontSize: "0.8rem", padding: "0.3rem 0.7rem" }}
            >
              ✅ Aprovar
            </button>
          )}

          {/* Publicar — so se aprovado e nao publicado */}
          {post.status === "aprovado" && (
            <button
              className="btn btn--primary"
              onClick={() => onPublicar(post)}
              disabled={isPublishing}
              style={{ fontSize: "0.8rem", padding: "0.3rem 0.7rem" }}
            >
              {isPublishing
                ? <span className="spinner" style={{ width: 12, height: 12 }} />
                : "📤 Publicar"}
            </button>
          )}

          {/* Excluir */}
          <button
            className="btn--icon"
            onClick={() => onExcluir(post)}
            title="Excluir"
            style={{ color: "var(--erro)" }}
          >
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <polyline points="3 6 5 6 21 6"/>
              <path d="M19 6l-1 14H6L5 6"/>
              <path d="M10 11v6M14 11v6"/>
              <path d="M9 6V4h6v2"/>
            </svg>
          </button>
        </div>
      </div>
    </div>
  );
}
