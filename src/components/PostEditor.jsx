import { useState, useEffect } from "react";
import { db } from "../firebase";
import { collection, addDoc, doc, updateDoc, serverTimestamp } from "firebase/firestore";

const AI_PROVIDERS = ["gemini", "openai", "claude"];

export default function PostEditor({ post, onClose, onNotify }) {
  const isEdit = Boolean(post);

  const [tema, setTema] = useState(post?.tema || "");
  const [legenda, setLegenda] = useState(post?.legenda || "");
  const [modo, setModo] = useState(post?.modo || "manual");
  const [agendamento, setAgendamento] = useState(post?.agendamento || "");
  const [cloudinaryUrl, setCloudinaryUrl] = useState(post?.cloudinaryUrl || "");
  const [aiProvider, setAiProvider] = useState("gemini");

  const [loadingImagem, setLoadingImagem] = useState(false);
  const [loadingLegenda, setLoadingLegenda] = useState(false);
  const [loadingSalvar, setLoadingSalvar] = useState(false);

  // ── Gerar imagem via Netlify Function (Python/Pillow) ──
  const handleGerarImagem = async () => {
    if (!tema.trim()) { onNotify("Informe o tema antes de gerar a imagem.", "error"); return; }
    setLoadingImagem(true);
    try {
      const res = await fetch("/.netlify/functions/gerar-card", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ tema, legenda }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.erro || "Erro na geração");
      setCloudinaryUrl(data.cloudinary_url);
      onNotify("Imagem gerada e salva no Cloudinary ✓");
    } catch (e) {
      onNotify(e.message, "error");
    } finally {
      setLoadingImagem(false);
    }
  };

  // ── Gerar legenda via IA ──
  const handleGerarLegenda = async () => {
    if (!tema.trim()) { onNotify("Informe o tema antes de gerar a legenda.", "error"); return; }
    setLoadingLegenda(true);
    try {
      const res = await fetch("/.netlify/functions/gerar-legenda", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ tema, provider: aiProvider }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.erro || "Erro na IA");
      setLegenda(data.legenda);
      onNotify(`Legenda gerada via ${aiProvider} ✓`);
    } catch (e) {
      onNotify(e.message, "error");
    } finally {
      setLoadingLegenda(false);
    }
  };

  // ── Salvar no Firestore ──
  const handleSalvar = async () => {
    if (!tema.trim()) { onNotify("Informe o tema.", "error"); return; }
    setLoadingSalvar(true);
    try {
      const payload = {
        tema,
        legenda,
        modo,
        agendamento,
        cloudinaryUrl,
        status: modo === "automatico" ? "aprovado" : "pendente",
        atualizadoEm: serverTimestamp(),
      };

      if (isEdit) {
        await updateDoc(doc(db, "posts", post.id), payload);
        onNotify("Post atualizado ✓");
      } else {
        await addDoc(collection(db, "posts"), {
          ...payload,
          criadoEm: serverTimestamp(),
        });
        onNotify("Post criado e adicionado à fila ✓");
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
        <p>Preencha, gere a imagem e defina o modo de publicação.</p>
      </div>

      <div className="editor-card">
        {/* Tema */}
        <div className="field">
          <label>Tema / Assunto</label>
          <input
            value={tema}
            onChange={(e) => setTema(e.target.value)}
            placeholder="Ex: Ansiedade no trabalho, autocuidado, limites..."
          />
        </div>

        {/* Preview + geração de imagem */}
        <div className="field">
          <label>Imagem do Card</label>
          <div className="image-preview">
            {cloudinaryUrl ? (
              <img src={cloudinaryUrl} alt="preview" />
            ) : (
              <div className="image-preview--empty">
                <svg width="36" height="36" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                  <rect x="3" y="3" width="18" height="18" rx="2" />
                  <circle cx="8.5" cy="8.5" r="1.5" />
                  <polyline points="21 15 16 10 5 21" />
                </svg>
                <span>Nenhuma imagem</span>
              </div>
            )}
          </div>
          <div style={{ display: "flex", gap: "0.5rem", flexWrap: "wrap" }}>
            <button
              className="btn btn--primary"
              onClick={handleGerarImagem}
              disabled={loadingImagem}
            >
              {loadingImagem ? <><span className="spinner" /> Gerando...</> : "⚡ Gerar Card"}
            </button>
            {cloudinaryUrl && (
              <a
                href={cloudinaryUrl}
                target="_blank"
                rel="noreferrer"
                className="btn btn--outline"
              >
                Ver no Cloudinary ↗
              </a>
            )}
          </div>
          <p className="field__hint">
            Gerado com Python/Pillow — sem consumo de créditos de IA.
          </p>
        </div>

        {/* Legenda */}
        <div className="field">
          <label>Legenda</label>
          <textarea
            value={legenda}
            onChange={(e) => setLegenda(e.target.value)}
            placeholder="Escreva a legenda ou gere com IA..."
            rows={5}
          />
          <div style={{ display: "flex", gap: "0.5rem", alignItems: "center", marginTop: "0.5rem", flexWrap: "wrap" }}>
            <select
              value={aiProvider}
              onChange={(e) => setAiProvider(e.target.value)}
              style={{ padding: "0.45rem 0.75rem", borderRadius: "8px", border: "1.5px solid var(--creme-escuro)", fontSize: "0.85rem", background: "var(--creme)", color: "var(--texto-escuro)", cursor: "pointer" }}
            >
              {AI_PROVIDERS.map((p) => (
                <option key={p} value={p}>{p.charAt(0).toUpperCase() + p.slice(1)}</option>
              ))}
            </select>
            <button
              className="btn btn--outline"
              onClick={handleGerarLegenda}
              disabled={loadingLegenda}
            >
              {loadingLegenda ? <><span className="spinner" style={{ borderTopColor: "var(--verde-medio)" }} /> Gerando...</> : "✨ Gerar com IA"}
            </button>
          </div>
        </div>

        {/* Modo de publicação */}
        <div className="field">
          <label>Modo de Publicação</label>
          <div className="mode-toggle">
            <button
              className={modo === "manual" ? "active" : ""}
              onClick={() => setModo("manual")}
            >
              🖐 Manual (aprovo antes)
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
              ? "O post ficará em fila até você aprovar e clicar em Publicar."
              : "O post será enviado automaticamente ao Make assim que salvo."}
          </p>
        </div>

        {/* Agendamento */}
        <div className="field">
          <label>Agendar para (opcional)</label>
          <input
            type="datetime-local"
            value={agendamento}
            onChange={(e) => setAgendamento(e.target.value)}
          />
          <p className="field__hint">
            Deixe em branco para publicar imediatamente (ou quando aprovar).
          </p>
        </div>

        {/* Ações */}
        <div style={{ display: "flex", gap: "0.75rem", marginTop: "0.5rem" }}>
          <button
            className="btn btn--primary"
            onClick={handleSalvar}
            disabled={loadingSalvar}
          >
            {loadingSalvar ? <><span className="spinner" /> Salvando...</> : isEdit ? "Salvar alterações" : "Adicionar à fila"}
          </button>
          <button className="btn btn--outline" onClick={onClose}>
            Cancelar
          </button>
        </div>
      </div>
    </div>
  );
}
