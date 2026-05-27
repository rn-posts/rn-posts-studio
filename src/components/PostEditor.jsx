import { useState } from "react";
import { db } from "../firebase";
import { collection, addDoc, doc, updateDoc, serverTimestamp } from "firebase/firestore";

const RENDER_URL = import.meta.env.DEV
  ? (import.meta.env.VITE_RENDER_URL || "http://localhost:5000")
  : "";

export default function PostEditor({ post, onClose, onNotify }) {
  const isEdit = Boolean(post);

  const [tema,          setTema]          = useState(post?.tema || "");
  const [legenda,       setLegenda]       = useState(post?.legenda || "");
  const [previewUrl,    setPreviewUrl]    = useState(post?.cloudinaryUrl || "");
  const [previewBase64, setPreviewBase64] = useState("");
  const [modo,          setModo]          = useState(post?.modo || "manual");
  const [dadosCard,     setDadosCard]     = useState(null);

  const [loadingCard,    setLoadingCard]    = useState(false);
  const [loadingLegenda, setLoadingLegenda] = useState(false);
  const [loadingAprovar, setLoadingAprovar] = useState(false);

  const handleGerarLegenda = async () => {
    if (!tema.trim()) { onNotify("Informe o tema.", "error"); return; }
    setLoadingLegenda(true);
    try {
      const res  = await fetch(`${RENDER_URL}/gerar-legenda`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ tema }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.erro || "Erro ao gerar legenda");
      setLegenda(data.legenda);
      onNotify("Legenda gerada ✓");
    } catch (e) {
      onNotify(e.message, "error");
    } finally {
      setLoadingLegenda(false);
    }
  };

  const handleGerarCard = async () => {
    if (!tema.trim()) { onNotify("Informe o tema.", "error"); return; }
    setLoadingCard(true);
    setDadosCard(null);
    setPreviewUrl("");
    try {
      const res = await fetch(`${RENDER_URL}/preview-card`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ tema, legenda: legenda || "" }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.erro || "Erro ao gerar card");
      setDadosCard(data);
      setPreviewUrl(data.preview_url);
      setLegenda(data.legenda);
      onNotify("Card gerado — revise e aprove ✓");
    } catch (e) {
      onNotify(e.message, "error");
    } finally {
      setLoadingCard(false);
    }
  };

  const handleAprovar = async () => {
    if (!dadosCard) { onNotify("Gere o card antes de aprovar.", "error"); return; }
    setLoadingAprovar(true);
    try {
      const res = await fetch(`${RENDER_URL}/aprovar-card`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          card_id: dadosCard.card_id,
          tema,
          legenda,
          modo,
        }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.erro || "Erro ao aprovar card");

      const payload = {
        tema,
        legenda,
        cloudinaryUrl: data.cloudinary_url,
        modo,
        linhaSheet: data.linha_planilha,
        status: modo === "automatico" ? "aprovado" : "pendente",
        atualizadoEm: serverTimestamp(),
      };

      if (isEdit) {
        await updateDoc(doc(db, "posts", post.id), payload);
        onNotify("Post atualizado ✓");
      } else {
        await addDoc(collection(db, "posts"), {
          ...payload, criadoEm: serverTimestamp(),
        });
        onNotify("Post aprovado e adicionado à fila ✓");
      }
      onClose();
    } catch (e) {
      onNotify(e.message, "error");
    } finally {
      setLoadingAprovar(false);
    }
  };

  const handleDescartar = () => {
    setDadosCard(null);
    setPreviewUrl("");
    onNotify("Card descartado.");
  };

  return (
    <div>
      <div className="section-header">
        <h1>{isEdit ? "Editar Post" : "Novo Post"}</h1>
        <p>Digite o tema — o sistema gera legenda e card automaticamente.</p>
      </div>

      <div className="editor-card">

        <div className="field">
          <label>Tema / Assunto</label>
          <input
            value={tema}
            onChange={e => setTema(e.target.value)}
            placeholder="Ex: Ansiedade, Autismo, Limites no relacionamento..."
          />
          <p className="field__hint">
            Este campo define o conteúdo da legenda e a escolha da imagem.
          </p>
        </div>

        <div style={{ display: "flex", gap: "0.75rem", marginBottom: "1.5rem", flexWrap: "wrap" }}>
          <button
            className="btn btn--outline"
            onClick={handleGerarLegenda}
            disabled={loadingLegenda || loadingCard}
          >
            {loadingLegenda
              ? <><span className="spinner" style={{ borderTopColor: "var(--verde-medio)" }} /> Gerando...</>
              : "✨ Gerar Legenda"}
          </button>

          <button
            className="btn btn--primary"
            onClick={handleGerarCard}
            disabled={loadingCard || loadingLegenda}
          >
            {loadingCard
              ? <><span className="spinner" /> Gerando card...</>
              : dadosCard ? "🔄 Gerar outro" : "⚡ Gerar Card"}
          </button>
        </div>

        {previewUrl && (
          <div className="field">
            <label>
              Card Gerado — 1080×1350
              <span style={{ fontSize: "0.72rem", color: "var(--aviso)", marginLeft: "0.5rem", fontWeight: 600 }}>
                ⏳ Aguardando aprovação
              </span>
            </label>

            {/* CORREÇÃO: preview maior (420px) para visualização adequada */}
            <div style={{
              width: "100%",
              maxWidth: 420,
              borderRadius: 12,
              overflow: "hidden",
              marginBottom: "0.75rem",
              boxShadow: "var(--sombra-media)",
              border: "2px solid var(--creme-escuro)",
              cursor: "pointer",
            }}
              onClick={() => window.open(previewUrl, "_blank")}
              title="Clique para ver em tamanho real"
            >
              <img src={previewUrl} alt="card preview" style={{ width: "100%", display: "block" }} />
            </div>

            <div style={{ display: "flex", gap: "0.5rem", flexWrap: "wrap", alignItems: "center" }}>
              {/* CORREÇÃO: botão "ver tamanho real" mais destacado */}
              <a
                href={previewUrl}
                target="_blank"
                rel="noreferrer"
                className="btn btn--primary"
                style={{ fontSize: "0.82rem", background: "var(--verde-medio)" }}
              >
                🔍 Ver tamanho real (1080×1350)
              </a>
              <button className="btn btn--outline" style={{ fontSize: "0.8rem" }} onClick={handleGerarCard} disabled={loadingCard}>
                🔄 Gerar outro
              </button>
              <button className="btn btn--outline" style={{ fontSize: "0.8rem", color: "var(--erro)" }} onClick={handleDescartar}>
                🗑 Descartar
              </button>
            </div>
          </div>
        )}

        <div className="field">
          <label>
            Legenda
            {legenda && (
              <span style={{ fontSize: "0.72rem", color: "var(--texto-suave)", marginLeft: "0.5rem" }}>
                — editável antes de aprovar
              </span>
            )}
          </label>
          <textarea
            value={legenda}
            onChange={e => setLegenda(e.target.value)}
            placeholder="A legenda será gerada automaticamente ao clicar em Gerar Card ou Gerar Legenda..."
            rows={9}
          />
          <p className="field__hint">
            A assinatura (Ronilson Nogueira · CRP 04/57327) é incluída automaticamente.
          </p>
        </div>

        <div className="field">
          <label>Modo de Publicação</label>
          <div className="mode-toggle">
            <button className={modo === "manual" ? "active" : ""} onClick={() => setModo("manual")}>
              🖐 Manual
            </button>
            <button className={modo === "automatico" ? "active" : ""} onClick={() => setModo("automatico")}>
              ⚡ Automático
            </button>
          </div>
          <p className="field__hint">
            {modo === "manual"
              ? "O post aguarda sua aprovação na fila antes de ser enviado ao Make."
              : "O post é enviado automaticamente ao Make assim que aprovado."}
          </p>
        </div>

        <div style={{ display: "flex", gap: "0.75rem", marginTop: "0.75rem", flexWrap: "wrap" }}>
          {dadosCard && (
            <button
              className="btn btn--primary"
              onClick={handleAprovar}
              disabled={loadingAprovar}
              style={{ background: "var(--sucesso, #2E7D32)" }}
            >
              {loadingAprovar
                ? <><span className="spinner" /> Aprovando...</>
                : "✅ Aprovar e salvar"}
            </button>
          )}
          <button className="btn btn--outline" onClick={onClose}>
            Cancelar
          </button>
        </div>

      </div>
    </div>
  );
}
