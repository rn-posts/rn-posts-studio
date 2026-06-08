import { useState } from "react";
import { db } from "../firebase";
import { collection, addDoc, doc, updateDoc, serverTimestamp } from "firebase/firestore";

const RENDER_URL = import.meta.env.DEV
  ? (import.meta.env.VITE_RENDER_URL || "http://localhost:5000")
  : "";

// Abre o preview em tamanho real convertendo base64 → Blob URL (evita bloqueio do browser)
function abrirTamanhoReal(previewUrl) {
  try {
    if (previewUrl.startsWith("data:")) {
      const [header, data] = previewUrl.split(",");
      const mime = header.match(/:(.*?);/)[1];
      const bin  = atob(data);
      const arr  = new Uint8Array(bin.length);
      for (let i = 0; i < bin.length; i++) arr[i] = bin.charCodeAt(i);
      const blob    = new Blob([arr], { type: mime });
      const blobUrl = URL.createObjectURL(blob);
      const janela  = window.open(blobUrl, "_blank");
      // Revoga o Blob URL após a janela carregar para liberar memória
      if (janela) janela.addEventListener("load", () => URL.revokeObjectURL(blobUrl));
    } else {
      window.open(previewUrl, "_blank");
    }
  } catch (e) {
    console.error("Erro ao abrir preview:", e);
  }
}

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
            placeholder="Ex: Ansiedade Generalizada"
          />
          <p className="field__hint">
            O texto aparece exatamente como você digitar (maiúsculas, minúsculas ou misto).
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
                ⏳ Aguardando aprovação — não enviado ao Cloudinary ainda
              </span>
            </label>

            {/* Layout flex: preview à esquerda, legenda de formatação à direita */}
            <div style={{ display: "flex", gap: "1.25rem", alignItems: "flex-start", flexWrap: "wrap" }}>

              {/* Preview do card */}
              <div
                style={{
                  flex: "1 1 320px",
                  maxWidth: 420,
                  borderRadius: 12,
                  overflow: "hidden",
                  marginBottom: "0.75rem",
                  boxShadow: "var(--sombra-media)",
                  border: "2px solid var(--creme-escuro)",
                  cursor: "zoom-in",
                }}
                onClick={() => abrirTamanhoReal(previewUrl)}
                title="Clique para ver em tamanho real (1080×1350)"
              >
                <img src={previewUrl} alt="card preview" style={{ width: "100%", display: "block" }} />
              </div>

              {/* Legenda de simbologia de formatação */}
              <div style={{
                flex: "0 0 200px",
                background: "var(--creme, #faf6f0)",
                borderRadius: 10,
                padding: "1rem 1.1rem",
                border: "1px solid var(--creme-escuro, #e8ddd0)",
                fontSize: "0.78rem",
                lineHeight: 1.7,
                color: "var(--texto, #333)",
              }}>
                <div style={{ fontWeight: 700, marginBottom: "0.5rem", fontSize: "0.82rem", color: "var(--marinho, #024059)" }}>
                  Formatação do texto
                </div>
                <div style={{ display: "flex", flexDirection: "column", gap: "0.45rem" }}>
                  <div>
                    <span style={{ fontWeight: 700, color: "var(--laranja, #F9AB0B)", fontFamily: "monospace", fontSize: "1rem" }}>:</span>
                    <span style={{ marginLeft: "0.4rem" }}>malgun</span>
                  </div>
                  <div>
                    <span style={{ fontWeight: 700, color: "var(--laranja, #F9AB0B)", fontFamily: "monospace", fontSize: "1rem" }}>*</span>
                    <span style={{ marginLeft: "0.4rem" }}>agilera estilizada</span>
                  </div>
                  <div>
                    <span style={{ fontWeight: 700, color: "var(--laranja, #F9AB0B)", fontFamily: "monospace", fontSize: "1rem" }}>-</span>
                    <span style={{ marginLeft: "0.4rem" }}>efeito fundo</span>
                  </div>
                </div>
              </div>
            </div>

            <div style={{ display: "flex", gap: "0.5rem", flexWrap: "wrap", alignItems: "center" }}>
              <button
                className="btn btn--primary"
                style={{ fontSize: "0.82rem" }}
                onClick={() => abrirTamanhoReal(previewUrl)}
              >
                🔍 Ver tamanho real (1080×1350)
              </button>
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
