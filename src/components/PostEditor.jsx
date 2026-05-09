import { useState } from "react";
import { db } from "../firebase";
import { collection, addDoc, doc, updateDoc, serverTimestamp } from "firebase/firestore";

const RENDER_URL = import.meta.env.VITE_RENDER_URL || "";

export default function PostEditor({ post, onClose, onNotify }) {
  const isEdit = Boolean(post);

  const [tema,          setTema]          = useState(post?.tema || "");
  const [legenda,       setLegenda]       = useState(post?.legenda || "");
  const [cloudinaryUrl, setCloudinaryUrl] = useState(post?.cloudinaryUrl || "");
  const [modo,          setModo]          = useState(post?.modo || "manual");
  const [linhaSheet,    setLinhaSheet]    = useState(post?.linhaSheet || null);

  const [loadingCard,    setLoadingCard]    = useState(false);
  const [loadingLegenda, setLoadingLegenda] = useState(false);
  const [loadingSalvar,  setLoadingSalvar]  = useState(false);

  // ── Gerar só legenda ────────────────────────────────────────────────────────
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

  // ── Gerar card completo (legenda + imagem + card + planilha) ────────────────
  const handleGerarCard = async () => {
    if (!tema.trim()) { onNotify("Informe o tema.", "error"); return; }
    setLoadingCard(true);
    try {
      const res  = await fetch(`${RENDER_URL}/gerar-card`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        // Envia legenda se já foi gerada/editada, senão o Render gera
        body: JSON.stringify({ tema, legenda: legenda || "" }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.erro || "Erro ao gerar card");

      setCloudinaryUrl(data.cloudinary_url);
      setLegenda(data.legenda);
      setLinhaSheet(data.linha_planilha);
      onNotify("Card gerado e adicionado à planilha ✓");
    } catch (e) {
      onNotify(e.message, "error");
    } finally {
      setLoadingCard(false);
    }
  };

  // ── Salvar no Firestore ─────────────────────────────────────────────────────
  const handleSalvar = async () => {
    if (!cloudinaryUrl) { onNotify("Gere o card antes de salvar.", "error"); return; }
    setLoadingSalvar(true);
    try {
      const payload = {
        tema, legenda, cloudinaryUrl, modo, linhaSheet,
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
        onNotify("Post adicionado à fila ✓");
      }
      onClose();
    } catch (e) {
      onNotify("Erro ao salvar: " + e.message, "error");
    } finally {
      setLoadingSalvar(false);
    }
  };

  return (
    <div>
      <div className="section-header">
        <h1>{isEdit ? "Editar Post" : "Novo Post"}</h1>
        <p>Digite o tema — o sistema gera legenda e card automaticamente.</p>
      </div>

      <div className="editor-card">

        {/* Tema */}
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

        {/* Botões de geração */}
        <div style={{ display: "flex", gap: "0.75rem", marginBottom: "1.5rem", flexWrap: "wrap" }}>
          <button
            className="btn btn--outline"
            onClick={handleGerarLegenda}
            disabled={loadingLegenda || loadingCard}
            title="Gera apenas a legenda sem criar o card"
          >
            {loadingLegenda
              ? <><span className="spinner" style={{ borderTopColor: "var(--verde-medio)" }} /> Gerando...</>
              : "✨ Gerar Legenda"}
          </button>

          <button
            className="btn btn--primary"
            onClick={handleGerarCard}
            disabled={loadingCard || loadingLegenda}
            title="Gera legenda + imagem + card + adiciona à planilha"
          >
            {loadingCard
              ? <><span className="spinner" /> Gerando card...</>
              : "⚡ Gerar Card"}
          </button>
        </div>

        {/* Preview do card */}
        {cloudinaryUrl && (
          <div className="field">
            <label>Card Gerado — 1080×1350</label>
            <div style={{
              maxWidth: 270,
              borderRadius: 12,
              overflow: "hidden",
              marginBottom: "0.75rem",
              boxShadow: "var(--sombra-media)",
              border: "2px solid var(--creme-escuro)"
            }}>
              <img
                src={cloudinaryUrl}
                alt="card gerado"
                style={{ width: "100%", display: "block" }}
              />
            </div>
            <div style={{ display: "flex", gap: "0.5rem", flexWrap: "wrap" }}>
              <a
                href={cloudinaryUrl}
                target="_blank"
                rel="noreferrer"
                className="btn btn--outline"
                style={{ fontSize: "0.8rem" }}
              >
                Ver tamanho real ↗
              </a>
              <button
                className="btn btn--outline"
                style={{ fontSize: "0.8rem" }}
                onClick={handleGerarCard}
                disabled={loadingCard}
              >
                🔄 Gerar outro
              </button>
            </div>
          </div>
        )}

        {/* Legenda editável */}
        <div className="field">
          <label>
            Legenda
            {legenda && (
              <span style={{ fontSize: "0.72rem", color: "var(--texto-suave)", marginLeft: "0.5rem" }}>
                — editável antes de salvar
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
            Se editar a legenda e gerar o card novamente, a versão editada será usada.
          </p>
        </div>

        {/* Modo de publicação */}
        <div className="field">
          <label>Modo de Publicação</label>
          <div className="mode-toggle">
            <button
              className={modo === "manual" ? "active" : ""}
              onClick={() => setModo("manual")}
            >
              🖐 Manual
            </button>
            <button
              className={modo === "automatico" ? "active" : ""}
              onClick={() => setModo("automatico")}
            >
              ⚡ Automático
            </button>
          </div>
          <p className="field__hint">
            {modo === "manual"
              ? "O post aguarda sua aprovação na fila antes de ser enviado ao Make."
              : "O post é enviado automaticamente ao Make assim que salvo."}
          </p>
        </div>

        {/* Ações */}
        <div style={{ display: "flex", gap: "0.75rem", marginTop: "0.75rem" }}>
          <button
            className="btn btn--primary"
            onClick={handleSalvar}
            disabled={loadingSalvar || !cloudinaryUrl}
            title={!cloudinaryUrl ? "Gere o card primeiro" : ""}
          >
            {loadingSalvar
              ? <><span className="spinner" /> Salvando...</>
              : isEdit ? "Salvar alterações" : "Adicionar à fila"}
          </button>
          <button className="btn btn--outline" onClick={onClose}>
            Cancelar
          </button>
        </div>

      </div>
    </div>
  );
}
