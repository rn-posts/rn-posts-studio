import { useState, useRef } from "react";
import { db } from "../firebase";
import { collection, addDoc, doc, updateDoc, serverTimestamp } from "firebase/firestore";

const RENDER_URL = import.meta.env.DEV
  ? (import.meta.env.VITE_RENDER_URL || "http://localhost:5000")
  : "";

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
      if (janela) janela.addEventListener("load", () => URL.revokeObjectURL(blobUrl));
    } else {
      window.open(previewUrl, "_blank");
    }
  } catch (e) {
    console.error("Erro ao abrir preview:", e);
  }
}

// Insere um símbolo no início de uma nova linha no textarea
function inserirSimbolo(valor, cursor, simbolo, setTema, ref) {
  const antes  = valor.substring(0, cursor);
  const depois = valor.substring(cursor);
  // Se o cursor está no meio de uma linha, quebra a linha antes
  const prefixo = antes.length > 0 && !antes.endsWith("\n") ? "\n" : "";
  const novo    = antes + prefixo + simbolo + depois;
  setTema(novo);
  // Reposiciona o cursor após o símbolo inserido
  setTimeout(() => {
    if (ref.current) {
      const pos = (antes + prefixo + simbolo).length;
      ref.current.selectionStart = pos;
      ref.current.selectionEnd   = pos;
      ref.current.focus();
    }
  }, 0);
}

// Pré-visualização do que cada linha vai gerar no card
function PreviewLinhas({ tema }) {
  if (!tema.trim()) return null;
  const linhas = tema.split("\n").filter(l => l.trim());
  return (
    <div style={{ marginTop: "0.5rem", display: "flex", flexDirection: "column", gap: "0.2rem" }}>
      {linhas.map((linha, i) => {
        const l = linha.trim();
        let estilo = "normal";
        let icone  = "✦";
        let cor    = "var(--branco, #f4f6f8)";
        let fundo  = "transparent";
        let label  = "Agilera";
        if (l.startsWith(":")) { estilo = "malgun";      icone = ":"; cor = "#aac9d0"; label = "Malgun"; }
        if (l.startsWith("*")) { estilo = "agilera_est"; icone = "*"; cor = "var(--laranja, #F9AB0B)"; label = "Agilera estilizada"; }
        if (l.startsWith("-")) { estilo = "fundo";       icone = "-"; cor = "var(--marinho, #024059)"; fundo = "var(--laranja, #F9AB0B)"; label = "Fundo preenchido"; }
        const texto = l.replace(/^[:*-]/, "").trim() || "(vazio)";
        return (
          <div key={i} style={{ display: "flex", alignItems: "center", gap: "0.5rem", fontSize: "0.74rem" }}>
            <span style={{
              fontFamily: "monospace", fontWeight: 700, fontSize: "0.9rem",
              color: "var(--laranja, #F9AB0B)", minWidth: 14,
            }}>{icone}</span>
            <span style={{
              background: fundo, color: cor,
              padding: fundo !== "transparent" ? "1px 8px" : "0",
              borderRadius: 4, fontWeight: estilo === "malgun" ? 400 : 600,
              fontStyle: estilo === "agilera_est" ? "italic" : "normal",
              letterSpacing: estilo === "agilera_est" ? "0.12em" : "normal",
              opacity: texto === "(vazio)" ? 0.4 : 1,
            }}>{texto}</span>
            <span style={{ color: "var(--texto-suave, #888)", fontSize: "0.68rem" }}>({label})</span>
          </div>
        );
      })}
    </div>
  );
}

export default function PostEditor({ post, onClose, onNotify }) {
  const isEdit = Boolean(post);

  const [tema,          setTema]          = useState(post?.tema || "");
  const [legenda,       setLegenda]       = useState(post?.legenda || "");
  const [previewUrl,    setPreviewUrl]    = useState(post?.cloudinaryUrl || "");
  const [modo,          setModo]          = useState(post?.modo || "manual");
  const [dadosCard,     setDadosCard]     = useState(null);

  const [loadingCard,    setLoadingCard]    = useState(false);
  const [loadingLegenda, setLoadingLegenda] = useState(false);
  const [loadingAprovar, setLoadingAprovar] = useState(false);

  const temaRef = useRef(null);

  const getCursor = () => temaRef.current?.selectionStart ?? tema.length;

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
        body: JSON.stringify({ card_id: dadosCard.card_id, tema, legenda, modo }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.erro || "Erro ao aprovar card");

      const payload = {
        tema, legenda,
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
        await addDoc(collection(db, "posts"), { ...payload, criadoEm: serverTimestamp() });
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

  // Botões de inserção de símbolo
  const botoesFormato = [
    { simbolo: "",  label: "Agilera",           desc: "Título principal",      cor: "#f4f6f8" },
    { simbolo: ":", label: ": Malgun",           desc: "Texto complementar",    cor: "#aac9d0" },
    { simbolo: "*", label: "* Agilera estilizada", desc: "Destaque expandido", cor: "#F9AB0B" },
    { simbolo: "-", label: "- Fundo preenchido", desc: "Highlight com cor",    cor: "#024059", bg: "#F9AB0B" },
  ];

  return (
    <div>
      <div className="section-header">
        <h1>{isEdit ? "Editar Post" : "Novo Post"}</h1>
        <p>Digite o tema — cada linha pode ter um estilo diferente usando os símbolos abaixo.</p>
      </div>

      <div className="editor-card">

        {/* ── Campo Tema ── */}
        <div className="field">
          <label>Tema / Assunto</label>

          {/* Botões de formatação acima do campo */}
          <div style={{ display: "flex", gap: "0.4rem", marginBottom: "0.5rem", flexWrap: "wrap" }}>
            {botoesFormato.map(({ simbolo, label, desc, cor, bg }) => (
              <button
                key={label}
                title={desc}
                style={{
                  fontSize: "0.72rem", padding: "3px 10px", borderRadius: 6, cursor: "pointer",
                  border: "1px solid var(--creme-escuro, #ddd)",
                  background: bg || "var(--creme, #faf6f0)",
                  color: cor, fontWeight: 600, fontFamily: "monospace",
                  transition: "opacity 0.15s",
                }}
                onClick={() => inserirSimbolo(tema, getCursor(), simbolo, setTema, temaRef)}
              >
                {label}
              </button>
            ))}
            <span style={{ fontSize: "0.68rem", color: "var(--texto-suave)", alignSelf: "center", marginLeft: "0.25rem" }}>
              — clique para inserir na posição do cursor
            </span>
          </div>

          {/* Textarea multiline — suporta \n para múltiplas linhas formatadas */}
          <textarea
            ref={temaRef}
            value={tema}
            onChange={e => setTema(e.target.value)}
            placeholder={"Ansiedade Generalizada\n:Uma desordem sem fim"}
            rows={3}
            style={{ fontFamily: "monospace", fontSize: "0.92rem", resize: "vertical" }}
          />

          {/* Pré-visualização das linhas */}
          {tema.trim() && (
            <div style={{
              marginTop: "0.5rem", padding: "0.6rem 0.8rem",
              background: "var(--marinho, #024059)", borderRadius: 8,
            }}>
              <div style={{ fontSize: "0.68rem", color: "#aac9d0", marginBottom: "0.35rem", fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.05em" }}>
                Pré-visualização das linhas
              </div>
              <PreviewLinhas tema={tema} />
            </div>
          )}

          <p className="field__hint" style={{ marginTop: "0.5rem" }}>
            Cada linha = um bloco de texto no card. Sem símbolo = Agilera (título). Use <code>:</code> <code>*</code> <code>-</code> no início da linha para mudar o estilo.
          </p>
        </div>

        {/* ── Botões de geração ── */}
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

        {/* ── Preview do card gerado ── */}
        {previewUrl && (
          <div className="field">
            <label>
              Card Gerado — 1080×1350
              <span style={{ fontSize: "0.72rem", color: "var(--aviso)", marginLeft: "0.5rem", fontWeight: 600 }}>
                ⏳ Aguardando aprovação — não enviado ao Cloudinary ainda
              </span>
            </label>

            <div
              style={{
                width: "100%", maxWidth: 420,
                borderRadius: 12, overflow: "hidden",
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

            <div style={{ display: "flex", gap: "0.5rem", flexWrap: "wrap", alignItems: "center" }}>
              <button className="btn btn--primary" style={{ fontSize: "0.82rem" }}
                onClick={() => abrirTamanhoReal(previewUrl)}>
                🔍 Ver tamanho real (1080×1350)
              </button>
              <button className="btn btn--outline" style={{ fontSize: "0.8rem" }}
                onClick={handleGerarCard} disabled={loadingCard}>
                🔄 Gerar outro
              </button>
              <button className="btn btn--outline" style={{ fontSize: "0.8rem", color: "var(--erro)" }}
                onClick={handleDescartar}>
                🗑 Descartar
              </button>
            </div>
          </div>
        )}

        {/* ── Legenda ── */}
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

        {/* ── Modo de publicação ── */}
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

        {/* ── Ações finais ── */}
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
