// v79 — Editor local do título.
// Abre sobre o card: fundo sem título + título como camada. Mover, aumentar (alças) e trocar cor/tamanho de palavras
// acontecem só aqui, na tela, e o texto acompanha na hora. Nada vai ao servidor até clicar FORA da caixa (ou em
// "Aplicar"): aí é UM pedido ao /ajustar-card e o card final é refeito pelo motor de título de verdade.
import { useEffect, useLayoutEffect, useRef, useState } from "react";

const W = 1080;

const PALETA = {
  branco:  { rgb: [244, 246, 248], hex: "#F4F6F8", nome: "Branco" },
  marinho: { rgb: [2, 64, 89],     hex: "#024059", nome: "Marinho" },
  amarelo: { rgb: [255, 221, 0],   hex: "#FFDD00", nome: "Amarelo" },
  laranja: { rgb: [249, 171, 11],  hex: "#F9AB0B", nome: "Laranja" },
  teal:    { rgb: [4, 157, 191],   hex: "#049DBF", nome: "Teal" },
  citrico: { rgb: [146, 204, 29],  hex: "#92CC1D", nome: "Verde" },
};

const ALCAS = [["nw", 0, 0], ["n", 0.5, 0], ["ne", 1, 0], ["e", 1, 0.5],
               ["se", 1, 1], ["s", 0.5, 1], ["sw", 0, 1], ["w", 0, 0.5]];
const CURSOR = { nw: "nwse-resize", se: "nwse-resize", ne: "nesw-resize", sw: "nesw-resize",
                 n: "ns-resize", s: "ns-resize", e: "ew-resize", w: "ew-resize" };

const limitar = (v, min, max) => Math.max(min, Math.min(max, v));

export default function TituloEditor({ renderUrl, cardId, ajuste, onAplicar, onFechar, onNotify }) {
  const raiz = useRef(null);
  const canvasRef = useRef(null);
  const imgCamada = useRef(null);

  const [larg, setLarg] = useState(420);
  const [dados, setDados] = useState(null);
  const [local, setLocal] = useState({ dx: 0, dy: 0, s: 1 });   // mudanças locais, relativas ao card atual
  const [cores, setCores] = useState({});                        // chave da palavra -> nome da cor ("" = padrão)
  const [escalas, setEscalas] = useState({});                    // chave da palavra -> escala absoluta
  const [sel, setSel] = useState("");                            // palavra selecionada
  const [gesto, setGesto] = useState(null);
  const [aplicando, setAplicando] = useState(false);

  const f = larg / W;

  // largura exibida do card (para converter px do card em px da tela)
  useLayoutEffect(() => {
    const el = raiz.current;
    if (!el) return undefined;
    const medir = () => setLarg(el.getBoundingClientRect().width || 420);
    medir();
    const ro = new ResizeObserver(medir);
    ro.observe(el);
    return () => ro.disconnect();
  }, [dados]);

  // busca o fundo limpo + a camada do título
  useEffect(() => {
    let vivo = true;
    (async () => {
      try {
        const res = await fetch(`${renderUrl}/camada-titulo`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ card_id: cardId }),
        });
        const d = await res.json();
        if (!res.ok) throw new Error(d.erro || "Erro ao abrir o editor do título");
        const im = new Image();
        im.onload = () => {
          if (!vivo) return;
          imgCamada.current = im;
          setDados(d);
        };
        im.src = d.camada_url;
      } catch (e) {
        if (!vivo) return;
        if (onNotify) onNotify(e.message, "error");
        onFechar();
      }
    })();
    return () => { vivo = false; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // desenha a camada e recolore, em tempo real, as palavras que mudaram de cor
  useEffect(() => {
    if (!dados || !canvasRef.current || !imgCamada.current) return;
    const cv = canvasRef.current;
    const ctx = cv.getContext("2d", { willReadFrequently: true });
    const { origem } = dados;
    cv.width = origem.w;
    cv.height = origem.h;
    ctx.clearRect(0, 0, cv.width, cv.height);
    ctx.drawImage(imgCamada.current, 0, 0);
    Object.entries(cores).forEach(([k, nome]) => {
      const alvo = nome && PALETA[nome] ? PALETA[nome].rgb : null;
      if (!alvo) return;                    // "Padrão": o preview não desfaz; volta ao aplicar
      dados.palavras_pos.filter(p => p.k === k).forEach(p => {
        const rx = Math.max(0, Math.round(p.x - origem.x));
        const ry = Math.max(0, Math.round(p.y - origem.y));
        const rw = Math.min(cv.width - rx, Math.round(p.w));
        const rh = Math.min(cv.height - ry, Math.round(p.h));
        if (rw <= 0 || rh <= 0) return;
        const img = ctx.getImageData(rx, ry, rw, rh);
        const d = img.data;
        for (let i = 0; i < d.length; i += 4) {
          if (d[i + 3] < 100) continue;
          const dr = d[i] - p.cor[0];
          const dg = d[i + 1] - p.cor[1];
          const db = d[i + 2] - p.cor[2];
          if (dr * dr + dg * dg + db * db < 90 * 90) {
            d[i] = alvo[0]; d[i + 1] = alvo[1]; d[i + 2] = alvo[2];
          }
        }
        ctx.putImageData(img, rx, ry);
      });
    });
  }, [dados, cores]);

  if (!dados) {
    return (
      <div ref={raiz} onClick={e => e.stopPropagation()}
        style={{ position: "absolute", inset: 0, zIndex: 6, background: "rgba(255,255,255,0.55)",
                 display: "flex", alignItems: "center", justifyContent: "center", fontSize: "0.8rem" }}>
        Abrindo editor do título…
      </div>
    );
  }

  const A = dados.ancora;
  const C = dados.caixa;
  const Acur = { x: A.x + local.dx, y: A.y + local.dy };     // âncora (canto de partida do texto) já deslocada
  const caixa = {                                            // caixa visível, com a mudança local aplicada
    x: Acur.x + (C.x - A.x) * local.s,
    y: Acur.y + (C.y - A.y) * local.s,
    w: C.w * local.s,
    h: C.h * local.s,
  };

  const ponto = (e) => {
    const r = raiz.current.getBoundingClientRect();
    return { x: (e.clientX - r.left) / f, y: (e.clientY - r.top) / f };
  };
  const dentro = (p, b) => p.x >= b.x && p.x <= b.x + b.w && p.y >= b.y && p.y <= b.y + b.h;
  const acharAlca = (p) => {
    const tol = 16 / f;
    for (const [id, lx, ly] of ALCAS) {
      const ax = caixa.x + lx * caixa.w;
      const ay = caixa.y + ly * caixa.h;
      if (Math.abs(p.x - ax) <= tol && Math.abs(p.y - ay) <= tol) return id;
    }
    return "";
  };
  // palavra sob o ponto (desfaz a mudança local para achar o retângulo original)
  const palavraEm = (p) => {
    const q = { x: A.x + (p.x - Acur.x) / local.s, y: A.y + (p.y - Acur.y) / local.s };
    const achada = dados.palavras_pos.find(w => q.x >= w.x && q.x <= w.x + w.w && q.y >= w.y && q.y <= w.y + w.h);
    return achada ? achada.k : "";
  };

  const aplicar = async () => {
    if (aplicando) return;
    const mudouGeo = Math.abs(local.dx) > 0.5 || Math.abs(local.dy) > 0.5 || Math.abs(local.s - 1) > 0.01;
    const chaves = new Set([...Object.keys(cores), ...Object.keys(escalas)]);
    if (!mudouGeo && chaves.size === 0) { onFechar(); return; }
    setAplicando(true);
    const previas = ajuste.palavras || {};
    const mapa = { ...previas };
    chaves.forEach(k => {
      const o = { ...(previas[k] || {}) };
      if (k in cores) o.cor = cores[k];
      if (k in escalas) o.escala = escalas[k];
      if (!o.cor && (!o.escala || Math.abs(o.escala - 1) < 0.01)) delete mapa[k];
      else mapa[k] = o;
    });
    try {
      await onAplicar({
        escala: limitar(+(ajuste.escala * local.s).toFixed(3), 0.5, 1.6),
        dx: Math.round(ajuste.dx + local.dx),
        dy: Math.round(ajuste.dy + local.dy),
        palavras: mapa,
      });
    } finally {
      onFechar();
    }
  };

  const aoPressionar = (e) => {
    if (aplicando) return;
    if (e.target.closest("[data-barra]")) return;           // clique nas barras de ferramentas não conta
    e.preventDefault();
    e.stopPropagation();
    const p = ponto(e);
    const alca = acharAlca(p);
    if (alca) {
      raiz.current.setPointerCapture(e.pointerId);
      setGesto({ tipo: "redim", alca, p0: p, local0: { ...local }, caixa0: { ...caixa } });
    } else if (dentro(p, caixa)) {
      raiz.current.setPointerCapture(e.pointerId);
      setGesto({ tipo: "mover", p0: p, local0: { ...local }, moveu: false });
    } else {
      aplicar();                                            // clicou fora da caixa: aplica
    }
  };

  const aoMover = (e) => {
    if (!gesto) return;
    const p = ponto(e);
    const ddx = p.x - gesto.p0.x;
    const ddy = p.y - gesto.p0.y;
    if (gesto.tipo === "mover") {
      if (!gesto.moveu && Math.abs(ddx) + Math.abs(ddy) > 4 / f) setGesto({ ...gesto, moveu: true });
      setLocal({ ...gesto.local0, dx: gesto.local0.dx + ddx, dy: gesto.local0.dy + ddy });
      return;
    }
    // redimensionar: o lado oposto à alça fica parado
    const b0 = gesto.caixa0;
    const l0 = gesto.local0;
    const a = gesto.alca;
    const sx = a.includes("e") ? (b0.w + ddx) / b0.w : a.includes("w") ? (b0.w - ddx) / b0.w : null;
    const sy = a.includes("s") ? (b0.h + ddy) / b0.h : a.includes("n") ? (b0.h - ddy) / b0.h : null;
    let rel = (sx !== null && sy !== null)
      ? Math.sqrt(Math.max(0.05, sx) * Math.max(0.05, sy))
      : (sx !== null ? sx : sy);
    const sNovo = limitar(l0.s * (rel || 1), 0.5, 2.0);
    rel = sNovo / l0.s;
    const ac0 = { x: A.x + l0.dx, y: A.y + l0.dy };
    const R = b0.x + b0.w;
    const B = b0.y + b0.h;
    const tx = a.includes("w") ? R - (ac0.x + (R - ac0.x) * rel) : 0;
    const ty = a.includes("n") ? B - (ac0.y + (B - ac0.y) * rel) : 0;
    setLocal({ s: sNovo, dx: l0.dx + tx, dy: l0.dy + ty });
  };

  const aoSoltar = (e) => {
    if (!gesto) return;
    const p = ponto(e);
    if (gesto.tipo === "mover" && !gesto.moveu) {            // foi um clique, não um arraste: seleciona a palavra
      const k = palavraEm(p);
      setSel(k && k !== sel ? k : "");
    }
    setGesto(null);
  };

  const mudarCor = (nome) => { if (sel) setCores(c => ({ ...c, [sel]: nome })); };
  const escalaAtual = (k) => (k in escalas
    ? escalas[k]
    : ((ajuste.palavras && ajuste.palavras[k] && ajuste.palavras[k].escala) || 1));
  const mudarEscala = (delta) => {
    if (!sel) return;
    setEscalas(s => ({ ...s, [sel]: limitar(+(escalaAtual(sel) + delta).toFixed(2), 0.6, 1.8) }));
  };
  const limparPalavra = () => {
    if (!sel) return;
    setCores(c => ({ ...c, [sel]: "" }));
    setEscalas(s => ({ ...s, [sel]: 1 }));
  };

  const palavraSel = dados.palavras_pos.find(w => w.k === sel);
  const corSel = sel in cores
    ? cores[sel]
    : ((ajuste.palavras && ajuste.palavras[sel] && ajuste.palavras[sel].cor) || "");
  const barraEmCima = caixa.y * f - 46 > 4;
  const topoBarra = barraEmCima ? caixa.y * f - 46 : (caixa.y + caixa.h) * f + 8;
  const esquerdaBarra = limitar(caixa.x * f, 4, Math.max(4, larg - 270));

  const estiloBtn = (ativo = false) => ({
    fontSize: "0.72rem", padding: "2px 9px", borderRadius: 999, cursor: "pointer",
    border: ativo ? "1.5px solid #F9AB0B" : "1px solid #ccc",
    background: ativo ? "#024059" : "#faf6f0", color: ativo ? "#fff" : "#024059", fontWeight: ativo ? 700 : 500,
  });

  return (
    <div
      ref={raiz}
      onPointerDown={aoPressionar}
      onPointerMove={aoMover}
      onPointerUp={aoSoltar}
      onPointerCancel={() => setGesto(null)}
      onClick={e => e.stopPropagation()}
      onKeyDown={e => { if (e.key === "Escape") onFechar(); }}
      tabIndex={0}
      style={{ position: "absolute", inset: 0, zIndex: 6, touchAction: "none", userSelect: "none", outline: "none",
               cursor: aplicando ? "wait" : "default", overflow: "hidden" }}
    >
      {/* fundo sem título */}
      <img src={dados.base_url} alt="" draggable={false} style={{ width: "100%", height: "100%", display: "block" }} />

      {/* título (camada), acompanha mover e redimensionar em tempo real */}
      <div style={{ position: "absolute", left: A.x * f, top: A.y * f, width: 0, height: 0,
                    transformOrigin: "0 0",
                    transform: `translate(${local.dx * f}px, ${local.dy * f}px) scale(${local.s})` }}>
        <canvas ref={canvasRef}
          style={{ position: "absolute", left: (dados.origem.x - A.x) * f, top: (dados.origem.y - A.y) * f,
                   width: dados.origem.w * f, height: dados.origem.h * f, pointerEvents: "none" }} />
        {palavraSel && dados.palavras_pos.filter(w => w.k === sel).map((w, i) => (
          <div key={i} style={{ position: "absolute", left: (w.x - A.x) * f, top: (w.y - A.y) * f,
                                width: w.w * f, height: w.h * f, border: "1.5px solid #049DBF",
                                background: "rgba(4,157,191,0.14)", borderRadius: 4, pointerEvents: "none" }} />
        ))}
      </div>

      {/* caixa tracejada com as 8 alças */}
      <div style={{ position: "absolute", left: caixa.x * f, top: caixa.y * f, width: caixa.w * f, height: caixa.h * f,
                    border: "1.5px dashed rgba(249,171,11,0.95)", borderRadius: 6, pointerEvents: "none" }}>
        {ALCAS.map(([id, lx, ly]) => (
          <div key={id} style={{ position: "absolute", left: `${lx * 100}%`, top: `${ly * 100}%`, width: 12, height: 12,
                                 transform: "translate(-50%, -50%)", background: "#fff", border: "2px solid #F9AB0B",
                                 borderRadius: 3, cursor: CURSOR[id] }} />
        ))}
      </div>

      {/* ferramentas da palavra selecionada, coladas na caixa */}
      {sel && palavraSel && (
        <div data-barra="1" onClick={e => e.stopPropagation()}
          style={{ position: "absolute", left: esquerdaBarra, top: topoBarra, width: 262, padding: "6px 8px",
                   background: "rgba(255,255,255,0.97)", border: "1px solid #ddd", borderRadius: 10,
                   boxShadow: "0 2px 10px rgba(0,0,0,0.18)", display: "flex", flexDirection: "column", gap: 5,
                   fontSize: "0.72rem", color: "#024059" }}>
          <div style={{ display: "flex", alignItems: "center", gap: 4, flexWrap: "wrap" }}>
            <strong style={{ marginRight: 4 }}>“{palavraSel.t}”</strong>
            <button type="button" style={estiloBtn(!corSel)} onClick={() => mudarCor("")}>Padrão</button>
            {Object.entries(PALETA).map(([id, c]) => (
              <button key={id} type="button" title={c.nome} onClick={() => mudarCor(id)}
                style={{ width: 20, height: 20, borderRadius: "50%", padding: 0, cursor: "pointer", background: c.hex,
                         border: corSel === id ? "2.5px solid #F9AB0B" : "1px solid #9aa" }} />
            ))}
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: 4 }}>
            <span>Tamanho</span>
            <button type="button" style={estiloBtn()} onClick={() => mudarEscala(-0.1)}>A−</button>
            <span style={{ minWidth: 34, textAlign: "center" }}>{Math.round(escalaAtual(sel) * 100)}%</span>
            <button type="button" style={estiloBtn()} onClick={() => mudarEscala(0.1)}>A+</button>
            <button type="button" style={estiloBtn()} onClick={limparPalavra}>↩ Limpar</button>
          </div>
          <div style={{ color: "#6b7c85" }}>
            A cor aparece na hora; o tamanho da palavra aparece ao aplicar.
          </div>
        </div>
      )}

      {/* aplicar / cancelar */}
      <div data-barra="1" onClick={e => e.stopPropagation()}
        style={{ position: "absolute", right: 6, bottom: 6, display: "flex", gap: 6 }}>
        <button type="button" style={{ ...estiloBtn(false), background: "rgba(255,255,255,0.95)" }}
          onClick={onFechar} disabled={aplicando}>✕ Cancelar</button>
        <button type="button" style={estiloBtn(true)} onClick={aplicar} disabled={aplicando}>
          {aplicando ? "Aplicando…" : "✓ Aplicar"}
        </button>
      </div>
      <div style={{ position: "absolute", left: 6, bottom: 6, fontSize: "0.66rem", color: "#fff",
                    background: "rgba(2,64,89,0.72)", padding: "2px 8px", borderRadius: 999, pointerEvents: "none" }}>
        Arraste • puxe as alças • clique numa palavra • clique fora para aplicar
      </div>
    </div>
  );
}
