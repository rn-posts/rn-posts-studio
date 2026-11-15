// v79/v80 — Editor local do título.
// Abre sobre o card: fundo sem título + título como camada. Mover, mexer nas alças e trocar cor/tamanho de palavras
// acontecem só aqui, na tela. Nada vai ao servidor até clicar FORA da caixa (ou em "Aplicar"): aí é UM pedido ao
// /ajustar-card e o card final é refeito pelo motor de título de verdade.
//
// Alças:  quinas = aumentam/diminuem o TEXTO (o texto acompanha ao vivo)
//         laterais (esquerda/direita) = mudam só a LARGURA (as linhas se reorganizam ao aplicar)
//         topo/base = mudam só o ESPAÇO entre as linhas (aparece ao aplicar)
// Teclado (com uma palavra selecionada):  Enter = começa uma nova linha nessa palavra
//                                          Backspace = junta a linha da palavra com a de cima
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

// mesma normalização do servidor (minúscula, só letras e números, sem os símbolos * e : do início)
const chaveJs = (t) => t.replace(/^[*:]+/, "").toLowerCase().replace(/[^\p{L}\p{N}]/gu, "");

// acha, no texto do tema, a N-ésima ocorrência (rank) da palavra de chave k
function acharToken(temaTxt, k, rank) {
  const linhas = String(temaTxt || "").split("\n");
  let n = 0;
  for (let li = 0; li < linhas.length; li++) {
    const toks = linhas[li].split(/\s+/).filter(Boolean);
    for (let ti = 0; ti < toks.length; ti++) {
      if (toks[ti].startsWith("-")) continue;          // palavras de fundo '-palavra' não são editáveis
      if (chaveJs(toks[ti]) === k) {
        if (n === rank) return { linhas, li, ti, toks };
        n++;
      }
    }
  }
  return null;
}

export default function TituloEditor({ renderUrl, cardId, ajuste, tema, onAplicar, onFechar, onNotify }) {
  const raiz = useRef(null);
  const canvasRef = useRef(null);
  const imgCamada = useRef(null);

  const [larg, setLarg] = useState(420);
  const [dados, setDados] = useState(null);
  const [local, setLocal] = useState({ dx: 0, dy: 0, s: 1, wf: 1, hf: 1 }); // mudanças locais, relativas ao card atual
  const [cores, setCores] = useState({});                        // chave da palavra -> nome da cor ("" = padrão)
  const [escalas, setEscalas] = useState({});                    // chave da palavra -> escala absoluta
  const [sel, setSel] = useState("");                            // chave da palavra selecionada
  const [selIdx, setSelIdx] = useState(-1);                      // qual retângulo foi clicado (para Enter/Backspace)
  const [temaNovo, setTemaNovo] = useState(null);                // tema com linhas divididas/juntas (aplica ao final)
  const [aviso, setAviso] = useState("");
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

  // devolve o foco ao editor para o teclado (Enter/Backspace/Esc) funcionar
  useEffect(() => { if (dados && raiz.current) raiz.current.focus(); }, [dados]);

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
    w: C.w * local.s * local.wf,
    h: C.h * local.s * local.hf,
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
  // índice da palavra sob o ponto (desfaz a mudança local para achar o retângulo original)
  const palavraEm = (p) => {
    const q = { x: A.x + (p.x - Acur.x) / local.s, y: A.y + (p.y - Acur.y) / local.s };
    return dados.palavras_pos.findIndex(w => q.x >= w.x && q.x <= w.x + w.w && q.y >= w.y && q.y <= w.y + w.h);
  };

  const aplicar = async () => {
    if (aplicando) return;
    const mudouGeo = Math.abs(local.dx) > 0.5 || Math.abs(local.dy) > 0.5 || Math.abs(local.s - 1) > 0.01
      || Math.abs(local.wf - 1) > 0.01 || Math.abs(local.hf - 1) > 0.01;
    const chaves = new Set([...Object.keys(cores), ...Object.keys(escalas)]);
    if (!mudouGeo && chaves.size === 0 && temaNovo === null) { onFechar(); return; }
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
        escala: limitar(+((ajuste.escala || 1) * local.s).toFixed(3), 0.5, 1.6),
        largura: limitar(+((ajuste.largura || 1) * local.wf).toFixed(3), 0.4, 2.5),
        espaco: limitar(+((ajuste.espaco || 1) * local.hf).toFixed(3), 0.6, 2.2),
        dx: Math.round(ajuste.dx + local.dx),
        dy: Math.round(ajuste.dy + local.dy),
        palavras: mapa,
        ...(temaNovo !== null ? { tema: temaNovo } : {}),
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
    if (raiz.current) raiz.current.focus();
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
    const b0 = gesto.caixa0;
    const l0 = gesto.local0;
    const a = gesto.alca;

    if (a === "e" || a === "w") {                           // laterais: só a largura (as linhas se reorganizam ao aplicar)
      const fator = a === "e" ? (b0.w + ddx) / b0.w : (b0.w - ddx) / b0.w;
      const wf = limitar(l0.wf * Math.max(0.05, fator), 0.4, 2.5);
      const novoW = C.w * l0.s * wf;
      const extraDx = a === "w" ? (b0.x + b0.w - novoW) - b0.x : 0;   // 'w': a borda direita fica parada
      setLocal({ ...l0, wf, dx: l0.dx + extraDx });
      return;
    }
    if (a === "n" || a === "s") {                           // topo/base: só o espaço entre as linhas
      const fator = a === "s" ? (b0.h + ddy) / b0.h : (b0.h - ddy) / b0.h;
      const hf = limitar(l0.hf * Math.max(0.05, fator), 0.6, 2.2);
      const novoH = C.h * l0.s * hf;
      const extraDy = a === "n" ? (b0.y + b0.h - novoH) - b0.y : 0;   // 'n': a borda de baixo fica parada
      setLocal({ ...l0, hf, dy: l0.dy + extraDy });
      return;
    }
    // quinas: aumentam/diminuem o TEXTO; o canto oposto à alça fica parado
    const sx = a.includes("e") ? (b0.w + ddx) / b0.w : (b0.w - ddx) / b0.w;
    const sy = a.includes("s") ? (b0.h + ddy) / b0.h : (b0.h - ddy) / b0.h;
    let rel = Math.sqrt(Math.max(0.05, sx) * Math.max(0.05, sy));
    const sNovo = limitar(l0.s * rel, 0.5, 2.0);
    rel = sNovo / l0.s;
    const ac0 = { x: A.x + l0.dx, y: A.y + l0.dy };
    const R = b0.x + b0.w;
    const B = b0.y + b0.h;
    const tx = a.includes("w") ? R - (ac0.x + (R - ac0.x) * rel) : 0;
    const ty = a.includes("n") ? B - (ac0.y + (B - ac0.y) * rel) : 0;
    setLocal({ ...l0, s: sNovo, dx: l0.dx + tx, dy: l0.dy + ty });
  };

  const aoSoltar = (e) => {
    if (!gesto) return;
    const p = ponto(e);
    if (gesto.tipo === "mover" && !gesto.moveu) {            // foi um clique, não um arraste: seleciona a palavra
      const i = palavraEm(p);
      if (i >= 0 && dados.palavras_pos[i].k !== sel) { setSel(dados.palavras_pos[i].k); setSelIdx(i); }
      else if (i >= 0) { setSelIdx(i); }
      else { setSel(""); setSelIdx(-1); }
      setAviso("");
    }
    setGesto(null);
  };

  // ── linhas: Enter divide, Backspace junta ──
  const localizar = () => {
    if (selIdx < 0 || !dados.palavras_pos[selIdx]) { setAviso("Clique numa palavra primeiro."); return null; }
    const k = dados.palavras_pos[selIdx].k;
    const rank = dados.palavras_pos.slice(0, selIdx).filter(p => p.k === k).length;
    const r = acharToken(temaNovo !== null ? temaNovo : tema, k, rank);
    if (!r) setAviso("Não achei essa palavra no texto do tema.");
    return r;
  };
  const dividirLinha = () => {
    const r = localizar();
    if (!r) return;
    const { linhas, li, ti, toks } = r;
    if (ti === 0) { setAviso("Essa palavra já começa uma linha."); return; }
    const ini = (linhas[li].trim()[0]) || "";
    const simb = (ini === ":" || ini === "*") ? ini : "";
    const a = toks.slice(0, ti).join(" ");
    let b = toks.slice(ti).join(" ");
    if (simb && !/^[:*-]/.test(b)) b = simb + b;               // a nova linha mantém o estilo da anterior
    linhas.splice(li, 1, a, b);
    setTemaNovo(linhas.join("\n"));
    setAviso("Linha dividida — aparece ao aplicar.");
  };
  const juntarLinha = () => {
    const r = localizar();
    if (!r) return;
    const { linhas, li, ti } = r;
    if (ti !== 0) {
      setAviso("Backspace junta quando a palavra começa uma linha. Para juntar linhas quebradas pela largura, puxe a alça lateral da caixa.");
      return;
    }
    if (li === 0) { setAviso("Essa já é a primeira linha."); return; }
    const prev = linhas[li - 1].trim();
    let cur = linhas[li].trim();
    if ((cur[0] === ":" || cur[0] === "*") && cur[0] === prev[0]) cur = cur.slice(1);
    linhas.splice(li - 1, 2, `${prev} ${cur}`.trim());
    setTemaNovo(linhas.join("\n"));
    setAviso("Linhas juntadas — aparece ao aplicar.");
  };
  const aoTeclar = (e) => {
    if (e.key === "Escape") { onFechar(); return; }
    if (aplicando) return;
    if (e.key === "Enter") { e.preventDefault(); dividirLinha(); }
    else if (e.key === "Backspace") { e.preventDefault(); juntarLinha(); }
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
  const barraEmCima = caixa.y * f - 62 > 4;
  const topoBarra = barraEmCima ? caixa.y * f - 62 : (caixa.y + caixa.h) * f + 8;
  const esquerdaBarra = limitar(caixa.x * f, 4, Math.max(4, larg - 270));
  const pendenteReflow = Math.abs(local.wf - 1) > 0.01 || Math.abs(local.hf - 1) > 0.01;

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
      onKeyDown={aoTeclar}
      tabIndex={0}
      style={{ position: "absolute", inset: 0, zIndex: 6, touchAction: "none", userSelect: "none", outline: "none",
               cursor: aplicando ? "wait" : "default", overflow: "hidden" }}
    >
      {/* fundo sem título */}
      <img src={dados.base_url} alt="" draggable={false} style={{ width: "100%", height: "100%", display: "block" }} />

      {/* título (camada), acompanha mover e o tamanho (quinas) em tempo real */}
      <div style={{ position: "absolute", left: A.x * f, top: A.y * f, width: 0, height: 0,
                    transformOrigin: "0 0",
                    transform: `translate(${local.dx * f}px, ${local.dy * f}px) scale(${local.s})` }}>
        <canvas ref={canvasRef}
          style={{ position: "absolute", left: (dados.origem.x - A.x) * f, top: (dados.origem.y - A.y) * f,
                   width: dados.origem.w * f, height: dados.origem.h * f, pointerEvents: "none" }} />
        {palavraSel && dados.palavras_pos.map((w, i) => (w.k === sel ? (
          <div key={i} style={{ position: "absolute", left: (w.x - A.x) * f, top: (w.y - A.y) * f,
                                width: w.w * f, height: w.h * f,
                                border: i === selIdx ? "2px solid #049DBF" : "1px dashed #049DBF",
                                background: i === selIdx ? "rgba(4,157,191,0.20)" : "rgba(4,157,191,0.08)",
                                borderRadius: 4, pointerEvents: "none" }} />
        ) : null))}
      </div>

      {/* caixa tracejada com as 8 alças */}
      <div style={{ position: "absolute", left: caixa.x * f, top: caixa.y * f, width: caixa.w * f, height: caixa.h * f,
                    border: "1.5px dashed rgba(249,171,11,0.95)", borderRadius: 6, pointerEvents: "none" }}>
        {ALCAS.map(([id, lx, ly]) => (
          <div key={id} style={{ position: "absolute", left: `${lx * 100}%`, top: `${ly * 100}%`,
                                 width: id.length === 2 ? 12 : 10, height: id.length === 2 ? 12 : 10,
                                 transform: "translate(-50%, -50%)", background: id.length === 2 ? "#fff" : "#F9AB0B",
                                 border: "2px solid #F9AB0B", borderRadius: id.length === 2 ? 3 : 6,
                                 cursor: CURSOR[id] }} />
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
          <div style={{ display: "flex", alignItems: "center", gap: 4 }}>
            <button type="button" style={estiloBtn()} onClick={dividirLinha}>↵ Nova linha aqui</button>
            <button type="button" style={estiloBtn()} onClick={juntarLinha}>⌫ Juntar com a de cima</button>
          </div>
          <div style={{ color: "#6b7c85" }}>
            A cor aparece na hora; tamanho da palavra e linhas aparecem ao aplicar. Teclas: Enter / Backspace.
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
      <div style={{ position: "absolute", left: 6, bottom: 6, maxWidth: "62%", fontSize: "0.64rem", color: "#fff",
                    background: "rgba(2,64,89,0.78)", padding: "3px 9px", borderRadius: 10, pointerEvents: "none",
                    lineHeight: 1.35 }}>
        {aviso
          || (pendenteReflow ? "Largura/espaço: as linhas se reorganizam ao aplicar."
            : "Quinas = tamanho • laterais = largura • topo/base = espaço • clique numa palavra • clique fora aplica")}
      </div>
    </div>
  );
}
