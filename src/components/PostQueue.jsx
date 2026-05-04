import { useState, useEffect } from "react";
import { db } from "../firebase";
import {
  collection, onSnapshot, doc, updateDoc, deleteDoc, query, orderBy,
} from "firebase/firestore";

const STATUS_LABEL = {
  pendente:  "Pendente",
  aprovado:  "Aprovado",
  publicado: "Publicado",
  erro:      "Erro",
};

export default function PostQueue({ onEdit, onNotify }) {
  const [posts, setPosts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [publishing, setPublishing] = useState(null);

  // Escuta tempo real no Firestore
  useEffect(() => {
    const q = query(collection(db, "posts"), orderBy("criadoEm", "desc"));
    const unsub = onSnapshot(q, (snap) => {
      setPosts(snap.docs.map((d) => ({ id: d.id, ...d.data() })));
      setLoading(false);
    });
    return unsub;
  }, []);

  const handleAprovar = async (post) => {
    await updateDoc(doc(db, "posts", post.id), { status: "aprovado" });
    onNotify("Post aprovado ✓");
  };

  const handlePublicar = async (post) => {
    setPublishing(post.id);
    try {
      // Dispara webhook do Make
      const res = await fetch(import.meta.env.VITE_MAKE_WEBHOOK_URL, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          cloudinary_url: post.cloudinaryUrl,
          legenda: post.legenda,
          modo: post.modo || "manual",
        }),
      });

      if (!res.ok) throw new Error("Make retornou erro");

      await updateDoc(doc(db, "posts", post.id), {
        status: "publicado",
        publicadoEm: new Date().toISOString(),
      });
      onNotify("Publicado no Instagram ✓");
    } catch (e) {
      await updateDoc(doc(db, "posts", post.id), { status: "erro" });
      onNotify("Erro ao publicar. Tente novamente.", "error");
    } finally {
      setPublishing(null);
    }
  };

  const handleExcluir = async (post) => {
    if (!window.confirm("Excluir este post da fila?")) return;
    await deleteDoc(doc(db, "posts", post.id));
    onNotify("Post removido.");
  };

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
        <p>{posts.filter(p => p.status === "pendente").length} aguardando aprovação</p>
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
  return (
    <div className="post-card">
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
            <span>Imagem não gerada</span>
          </div>
        )}
      </div>

      <div className="post-card__body">
        {post.tema && <div className="post-card__tema">{post.tema}</div>}
        <div className="post-card__legenda">
          {post.legenda || <em style={{ color: "var(--texto-suave)" }}>Sem legenda</em>}
        </div>
      </div>

      <div className="post-card__footer">
        <span className={`post-card__status status--${post.status || "pendente"}`}>
          {STATUS_LABEL[post.status] || "Pendente"}
        </span>

        <div className="post-card__actions">
          {/* Editar */}
          <button className="btn--icon" onClick={() => onEdit(post)} title="Editar">
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M11 4H4a2 2 0 00-2 2v14a2 2 0 002 2h14a2 2 0 002-2v-7" />
              <path d="M18.5 2.5a2.121 2.121 0 013 3L12 15l-4 1 1-4 9.5-9.5z" />
            </svg>
          </button>

          {/* Aprovar (só se pendente) */}
          {post.status === "pendente" && (
            <button className="btn btn--outline" onClick={() => onAprovar(post)}>
              Aprovar
            </button>
          )}

          {/* Publicar (se aprovado ou modo auto) */}
          {(post.status === "aprovado" || post.modo === "automatico") && post.status !== "publicado" && (
            <button
              className="btn btn--primary"
              onClick={() => onPublicar(post)}
              disabled={isPublishing}
            >
              {isPublishing ? <span className="spinner" /> : "Publicar"}
            </button>
          )}

          {/* Excluir */}
          <button className="btn--icon" onClick={() => onExcluir(post)} title="Excluir"
            style={{ color: "var(--erro)", borderColor: "#FBBDB7" }}>
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <polyline points="3 6 5 6 21 6" />
              <path d="M19 6l-1 14H6L5 6" />
              <path d="M10 11v6M14 11v6" />
              <path d="M9 6V4h6v2" />
            </svg>
          </button>
        </div>
      </div>
    </div>
  );
}
