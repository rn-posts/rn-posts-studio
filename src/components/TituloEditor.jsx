// v81 — Editor local do título (edição direta no card).
// Abre sobre o card: fundo sem título + o título real recortado em "peças" (uma por palavra). Tudo é feito na tela e
// o texto se reorganiza AO VIVO dentro da caixa, com o mesmo visual do motor (sombra, contorno, fonte). Nada vai ao
// servidor até clicar FORA da caixa (ou em "Aplicar"): aí é UM pedido e o card final é refeito pelo motor.
//
// Caixa:   arrastar = mover
//          quinas = aumentar/diminuir o TEXTO
//          laterais = LARGURA (as palavras reorganizam nas linhas, ao vivo)
//          topo/base = ESPAÇO entre as linhas (ao vivo)
// Palavra: clicar seleciona; a alça no canto dela muda o tamanho só dessa palavra; a tira fina (fora do texto)
//          troca a cor. Enter = nova linha nessa palavra; Backspace = junta com a linha de cima.
import { useEffect, useLayoutEffect, useMemo, useRef, useState } from "react";

const W = 1080;
const H = 1350;
const PADBOX = 10;

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

// ── organiza o que o servidor desenhou em blocos de palavras ──
function montarBlocos(dados) {
  const brutas = dados.linhas || [];
  const linhas = [];
  brutas.forEach(l => {                                   // descarta redesenhos duplicados na mesma posição
    const dup = linhas.some(e => Math.abs(e.y - l.y) < 3
      && l.palavras.every(w => e.palavras.some(v => w.x0 < v.x1 && w.x1 > v.x0)));
    if (!dup) linhas.push(l);
  });
  const grupos = (dados.grupos && dados.grupos.length) ? dados.grupos : [{ y: -1e9, est: "normal", n: 2 }];
  const blocos = grupos.map((g, i) => ({ gi: i, g, linhas: [], reflui: g.est !== "fundo" && g.n === 1 }));
  linhas.forEach(l => {
    let gi = 0;
    for (let i = 0; i < grupos.length; i++) if (l.y >= grupos[i].y - 6) gi = i;
    blocos[gi].linhas.push(l);
  });
  let n = 0;
  const lista = blocos.filter(b => b.linhas.length);
  lista.forEach(b => {
    b.linhas.sort((p, q) => p.y - q.y);
    b.palavras = [];
    b.linhas.forEach((l, li) => l.palavras.forEach(w => b.palavras.push({ ...w, y: l.y, h: l.h, li, gid: n++ })));
  });
  return lista;
}

// ── posição de cada palavra: igual ao original, ou reorganizada pela largura/espaço/quebras/tamanho da palavra ──
function calcularLayout(blocos, { lim, hf, escalaPal, quebras, limSeguro = Infinity }) {
  const out = [];
  // O motor limita a largura do texto à zona segura do Instagram; se mover o texto para a direita faz as linhas
  // originais não caberem mais, elas se reorganizam como o motor fará.
  let larguraOrig = 0;
  blocos.forEach(b => { if (b.reflui) b.linhas.forEach(l => { larguraOrig = Math.max(larguraOrig, l.palavras[l.palavras.length - 1].x1 - l.palavras[0].x0); }); });
  const limEf = Math.min(lim === null ? Infinity : lim, limSeguro);
  const guloso = lim !== null || limEf < larguraOrig - 1;
  const limite = guloso ? limEf : null;
  let yCur = null;
  let baseAnt = null;
  blocos.forEach((b, bi) => {
    const topo0 = b.linhas[0].y;
    const ult = b.linhas[b.linhas.length - 1];
    const base0 = ult.y + ult.h;
    const gap = baseAnt === null ? 0 : topo0 - baseAnt;
    const topo = yCur === null ? topo0 : yCur + gap;
    let fundo;
    if (!b.reflui) {                                       // fundos '-palavra' e linhas lado a lado: a linha inteira acompanha a posição
      const dy = topo - topo0;
      b.linhas.forEach((l, li) => {
        const lx0 = l.palavras[0].x0;
        const lx1 = l.palavras[l.palavras.length - 1].x1;
        out.push({
          gid: -(bi * 100 + li + 1), k: "", t: "", ed: false, cor: [0, 0, 0],
          sx: lx0, sy: l.y, sw: lx1 - lx0, sh: l.h, x: lx0, y: l.y + dy, w: lx1 - lx0, h: l.h,
          ini: true, primeiro: li === 0, bi, fixo: true, esp: 20, x0b: lx0, padX: 40, padY: 16,
        });
      });
      fundo = base0 + dy;
    } else {
      const x0 = b.linhas[0].palavras[0].x0;
      const altLinha = b.linhas[0].h;
      const passo = Math.max(10, (b.linhas.length > 1 ? (b.linhas[1].y - b.linhas[0].y) : altLinha * 1.1) * hf);
      const vaos = [];
      b.linhas.forEach(l => { for (let i = 1; i < l.palavras.length; i++) vaos.push(l.palavras[i].x0 - l.palavras[i - 1].x1); });
      vaos.sort((p, q) => p - q);
      const espaco = vaos.length ? vaos[Math.floor(vaos.length / 2)] : altLinha * 0.28;
      let x = 0;
      let linhaN = 0;
      b.palavras.forEach((w, i) => {
        const esc = escalaPal[w.k] || 1;
        const ww = (w.x1 - w.x0) * esc;
        const hh = w.h * esc;
        let ini = i === 0;
        if (i > 0) {
          const forca = quebras.has(w.gid);
          const quebra = limite !== null ? (x > 0 && x + ww > limite) : (w.li !== b.palavras[i - 1].li);
          if (forca || quebra) { x = 0; linhaN++; ini = true; }
        }
        out.push({
          ...w, sx: w.x0, sy: w.y, sw: w.x1 - w.x0, sh: w.h,
          x: x0 + x, y: topo + linhaN * passo + (altLinha - hh), w: ww, h: hh,
          ini, primeiro: i === 0, bi, fixo: false, esp: espaco, x0b: x0,
          linha: linhaN, ly: topo + linhaN * passo, lh: altLinha,
        });
        x += ww + espaco;
      });
      fundo = topo + linhaN * passo + altLinha;
    }
    yCur = fundo;
    baseAnt = base0;
  });
  return out;
}

function caixaDoLayout(lay) {
  if (!lay.length) return null;
  const x0 = Math.min(...lay.map(p => p.x));
  const x1 = Math.max(...lay.map(p => p.x + p.w));
  const y0 = Math.min(...lay.map(p => p.y));
  const y1 = Math.max(...lay.map(p => p.y + p.h));
  return { x: x0 - PADBOX, y: y0 - PADBOX, w: x1 - x0 + 2 * PADBOX, h: y1 - y0 + 2 * PADBOX };
}

function recolorir(ctx, x, y, w, h, corOrig, alvo) {
  const rx = Math.max(0, Math.round(x));
  const ry = Math.max(0, Math.round(y));
  const rw = Math.min(ctx.canvas.width - rx, Math.round(w));
  const rh = Math.min(ctx.canvas.height - ry, Math.round(h));
  if (rw <= 0 || rh <= 0) return;
  const img = ctx.getImageData(rx, ry, rw, rh);
  const d = img.data;
  for (let i = 0; i < d.length; i += 4) {
    if (d[i + 3] < 8) continue;                       // inclui as bordas suaves das letras (sem sobrar rastro da cor antiga)
    const dr = d[i] - corOrig[0];
    const dg = d[i + 1] - corOrig[1];
    const db = d[i + 2] - corOrig[2];
    if (dr * dr + dg * dg + db * db < 45 * 45) { d[i] = alvo[0]; d[i + 1] = alvo[1]; d[i + 2] = alvo[2]; }
  }
  ctx.putImageData(img, rx, ry);
}

export default function TituloEditor({ renderUrl, cardId, ajuste, tema, onAplicar, onManualAplicado, onFechar, onNotify }) {
  const raiz = useRef(null);
  const canvasRef = useRef(null);
  const imgCamada = useRef(null);
  const imgBase = useRef(null);

  const [larg, setLarg] = useState(420);
  const [dados, setDados] = useState(null);
  // mudanças locais, relativas ao card atual: deslocamento, tamanho do texto (s), largura da caixa (lim), espaço entre linhas (hf)
  const [local, setLocal] = useState({ dx: 0, dy: 0, s: 1, lim: null, hf: 1 });
  const [cores, setCores] = useState({});          // chave da palavra -> nome da cor ("" = padrão)
  const [wsPal, setWsPal] = useState({});          // chave da palavra -> fator de tamanho (relativo ao card atual)
  const [quebras, setQuebras] = useState([]);      // palavras que começam linha nova (Enter)
  const [selGid, setSelGid] = useState(-1);        // palavra selecionada (id no layout)
  const [temaNovo, setTemaNovo] = useState(null);  // tema com linhas divididas/juntas (aplica ao final)
  const [aviso, setAviso] = useState("");
  const [gesto, setGesto] = useState(null);
  const [aplicando, setAplicando] = useState(false);

  const f = larg / W;

  useLayoutEffect(() => {
    const el = raiz.current;
    if (!el) return undefined;
    const medir = () => setLarg(el.getBoundingClientRect().width || 420);
    medir();
    const ro = new ResizeObserver(medir);
    ro.observe(el);
    return () => ro.disconnect();
  }, [dados]);

  // busca o fundo limpo + o título
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
        const carregar = (src) => new Promise((ok, falha) => {
          const i = new Image();
          i.onload = () => ok(i);
          i.onerror = () => falha(new Error("Falha ao carregar a imagem do editor"));
          i.src = src;
        });
        const [im, ib] = await Promise.all([carregar(d.camada_url), carregar(d.base_url)]);
        if (!vivo) return;
        imgCamada.current = im;
        imgBase.current = ib;
        setDados(d);
      } catch (e) {
        if (!vivo) return;
        if (onNotify) onNotify(e.message, "error");
        onFechar();
      }
    })();
    return () => { vivo = false; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => { if (dados && raiz.current) raiz.current.focus(); }, [dados]);

  const blocos = useMemo(() => (dados ? montarBlocos(dados) : []), [dados]);
  const limSeguro = dados ? (1046 - (dados.ancora.x + local.dx)) / local.s : Infinity;   // largura máxima que o motor aceita (zona segura)
  const lay = useMemo(
    () => calcularLayout(blocos, { lim: local.lim, hf: local.hf, escalaPal: wsPal, quebras: new Set(quebras), limSeguro }),
    [blocos, local.lim, local.hf, wsPal, quebras, limSeguro],
  );
  const modif = local.lim !== null || Math.abs(local.hf - 1) > 0.005 || quebras.length > 0
    || Object.values(wsPal).some(v => Math.abs(v - 1) > 0.005)
    || lay.some(p => !p.fixo && (Math.abs(p.x - p.sx) > 1.5 || Math.abs(p.y - p.sy) > 1.5));

  // desenha o título: original, ou palavra por palavra nas novas posições; recolore ao vivo
  useEffect(() => {
    if (!dados || !canvasRef.current || !imgCamada.current) return;
    const cv = canvasRef.current;
    const ctx = cv.getContext("2d", { willReadFrequently: true });
    const { origem } = dados;
    cv.width = W;
    cv.height = H;
    ctx.clearRect(0, 0, W, H);
    if (!modif) {
      ctx.drawImage(imgCamada.current, origem.x, origem.y);
      lay.forEach(p => {
        const nome = cores[p.k];
        if (nome && PALETA[nome]) recolorir(ctx, p.sx, p.sy, p.sw, p.sh, p.cor, PALETA[nome].rgb);
      });
      return;
    }
    const tmp = document.createElement("canvas");
    lay.forEach(p => {
      const padX = p.padX !== undefined ? p.padX : limitar(Math.floor(p.esp / 2) - 1, 3, 20);   // não pega as letras vizinhas
      const padY = p.padY !== undefined ? p.padY : 6;
      const sw = p.sw + 2 * padX;
      const sh = p.sh + 2 * padY;
      tmp.width = sw;
      tmp.height = sh;
      const tc = tmp.getContext("2d", { willReadFrequently: true });
      tc.clearRect(0, 0, sw, sh);
      tc.drawImage(imgCamada.current, p.sx - padX - origem.x, p.sy - padY - origem.y, sw, sh, 0, 0, sw, sh);
      const nome = cores[p.k];
      if (nome && PALETA[nome]) recolorir(tc, padX, padY, p.sw, p.sh, p.cor, PALETA[nome].rgb);
      const esc = p.sw > 0 ? p.w / p.sw : 1;
      ctx.drawImage(tmp, 0, 0, sw, sh, p.x - padX * esc, p.y - padY * esc, sw * esc, sh * esc);
    });
  }, [dados, cores, lay, modif]);

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
  const Acur = { x: A.x + local.dx, y: A.y + local.dy };       // âncora (canto de partida do texto) já deslocada
  const bb = modif ? caixaDoLayout(lay) : null;
  const base = bb
    ? { x: bb.x, y: bb.y, w: local.lim !== null ? local.lim + 2 * PADBOX : bb.w, h: bb.h }
    : C;
  const caixa = {
    x: Acur.x + (base.x - A.x) * local.s,
    y: Acur.y + (base.y - A.y) * local.s,
    w: base.w * local.s,
    h: base.h * local.s,
  };
  const paraTela = (px, py) => ({ x: Acur.x + (px - A.x) * local.s, y: Acur.y + (py - A.y) * local.s });
  const instSel = lay.find(p => p.gid === selGid) || null;
  const sel = instSel ? instSel.k : "";

  const ponto = (e) => {
    const r = raiz.current.getBoundingClientRect();
    return { x: (e.clientX - r.left) / f, y: (e.clientY - r.top) / f };
  };
  const dentro = (p, b) => p.x >= b.x && p.x <= b.x + b.w && p.y >= b.y && p.y <= b.y + b.h;
  const acharAlca = (p) => {
    const tol = 16 / f;
    for (const [id, lx, ly] of ALCAS) {
      if (Math.abs(p.x - (caixa.x + lx * caixa.w)) <= tol && Math.abs(p.y - (caixa.y + ly * caixa.h)) <= tol) return id;
    }
    return "";
  };
  const instEm = (p) => {                                       // palavra sob o ponto (desfaz mover/tamanho local)
    const q = { x: A.x + (p.x - Acur.x) / local.s, y: A.y + (p.y - Acur.y) / local.s };
    return lay.find(w => w.ed && q.x >= w.x && q.x <= w.x + w.w && q.y >= w.y && q.y <= w.y + w.h) || null;
  };
  // alça de tamanho da palavra selecionada (canto inferior direito dela)
  const alcaPalavra = instSel && !instSel.fixo ? paraTela(instSel.x + instSel.w, instSel.y + instSel.h) : null;

  // v83: a edição manual é SOBERANA. A imagem final é composta aqui, exatamente como está na tela (fundo + título
  // com as posições, tamanhos e cores que você deixou), e o servidor só a guarda: o motor de título não refaz nada.
  const aplicar = async () => {
    if (aplicando) return;
    const mudouGeo = Math.abs(local.dx) > 0.5 || Math.abs(local.dy) > 0.5 || Math.abs(local.s - 1) > 0.01 || modif;
    if (!mudouGeo && Object.keys(cores).length === 0) { onFechar(); return; }
    setAplicando(true);
    try {
      const cv = document.createElement("canvas");
      cv.width = W;
      cv.height = H;
      const ctx = cv.getContext("2d");
      ctx.imageSmoothingEnabled = true;
      ctx.imageSmoothingQuality = "high";
      ctx.drawImage(imgBase.current, 0, 0, W, H);
      ctx.save();
      ctx.translate(Acur.x, Acur.y);
      ctx.scale(local.s, local.s);
      ctx.translate(-A.x, -A.y);
      ctx.drawImage(canvasRef.current, 0, 0);
      ctx.restore();
      const imagem = cv.toDataURL("image/jpeg", 0.93);

      // onde cada palavra ficou (para a próxima abertura do editor)
      const T = (px, py) => ({ x: Acur.x + (px - A.x) * local.s, y: Acur.y + (py - A.y) * local.s });
      const linhasFinal = [];
      const gruposFinal = [];
      blocos.forEach((b, bi) => {
        const doBloco = lay.filter(p => p.bi === bi);
        if (!doBloco.length) return;
        if (!b.reflui) {
          b.linhas.forEach((l, li) => {
            const e = doBloco[li];
            if (!e) return;
            const dy = e.y - l.y;
            linhasFinal.push({
              y: T(0, l.y + dy).y, h: l.h * local.s,
              palavras: l.palavras.map(w => ({ k: w.k, t: w.t, x0: T(w.x0, 0).x, x1: T(w.x1, 0).x, cor: w.cor })),
            });
          });
        } else {
          const porLinha = new Map();
          doBloco.forEach(p => { if (!porLinha.has(p.linha)) porLinha.set(p.linha, []); porLinha.get(p.linha).push(p); });
          [...porLinha.keys()].sort((a, c) => a - c).forEach(ln => {
            const ps = porLinha.get(ln);
            linhasFinal.push({
              y: T(0, ps[0].ly).y, h: ps[0].lh * local.s,
              palavras: ps.map(p => ({
                k: p.k, t: p.t, x0: T(p.x, 0).x, x1: T(p.x + p.w, 0).x,
                cor: (cores[p.k] && PALETA[cores[p.k]]) ? PALETA[cores[p.k]].rgb : p.cor,
              })),
            });
          });
        }
        const topo = Math.min(...doBloco.map(p => (p.ly !== undefined ? p.ly : p.y)));
        gruposFinal.push({ y: T(0, topo).y, alt: b.linhas[0].h * local.s, est: b.g.est, n: b.g.n });
      });
      const maxPx = (local.lim !== null ? local.lim : (dados.max_px || 0)) * local.s;

      const res = await fetch(`${renderUrl}/aplicar-manual`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          card_id: cardId, imagem,
          estado: { ancora: Acur, max_px: maxPx, linhas: linhasFinal, grupos: gruposFinal },
        }),
      });
      const d = await res.json();
      if (!res.ok) throw new Error(d.erro || "Erro ao aplicar a edição manual");
      if (onManualAplicado) onManualAplicado(d);
      onFechar();
    } catch (e) {
      if (onNotify) onNotify(e.message, "error");
      setAplicando(false);                                    // mantém o editor aberto para não perder a edição
    }
  };

  const aoPressionar = (e) => {
    if (aplicando) return;
    if (e.target.closest("[data-barra]")) return;             // clique na tira de ferramentas não conta
    e.preventDefault();
    e.stopPropagation();
    if (raiz.current) raiz.current.focus();
    const p = ponto(e);
    if (alcaPalavra && Math.abs(p.x - alcaPalavra.x) <= 16 / f && Math.abs(p.y - alcaPalavra.y) <= 16 / f) {
      raiz.current.setPointerCapture(e.pointerId);
      setGesto({ tipo: "palavra", p0: p, k: instSel.k, ws0: wsPal[instSel.k] || 1, w0: instSel.w, s0: local.s });
      return;
    }
    const alca = acharAlca(p);
    if (alca) {
      raiz.current.setPointerCapture(e.pointerId);
      setGesto({ tipo: "redim", alca, p0: p, local0: { ...local }, caixa0: { ...caixa } });
    } else if (dentro(p, caixa)) {
      raiz.current.setPointerCapture(e.pointerId);
      setGesto({ tipo: "mover", p0: p, local0: { ...local }, moveu: false });
    } else {
      aplicar();                                              // clicou fora da caixa: aplica
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
    if (gesto.tipo === "palavra") {                           // tamanho só da palavra selecionada
      const novaW = Math.max(8, gesto.w0 + ddx / gesto.s0);
      const ws = limitar(gesto.ws0 * (novaW / gesto.w0), 0.6, 1.8);
      setWsPal(m => ({ ...m, [gesto.k]: +ws.toFixed(3) }));
      return;
    }
    const b0 = gesto.caixa0;
    const l0 = gesto.local0;
    const a = gesto.alca;

    if (a === "e" || a === "w") {                             // laterais: largura; as palavras reorganizam ao vivo
      const novaCaixaW = a === "e" ? b0.w + ddx : b0.w - ddx;
      const lim = limitar(novaCaixaW / l0.s - 2 * PADBOX, 80, 1000);
      const extraDx = a === "w" ? b0.w - (lim + 2 * PADBOX) * l0.s : 0;   // 'w': a borda direita fica parada
      setLocal({ ...l0, lim, dx: l0.dx + extraDx });
      return;
    }
    if (a === "n" || a === "s") {                             // topo/base: espaço entre as linhas, ao vivo
      const fator = a === "s" ? (b0.h + ddy) / b0.h : (b0.h - ddy) / b0.h;
      const hf = limitar(l0.hf * Math.max(0.05, fator), 0.5, 2.5);
      let extraDy = 0;
      if (a === "n") {
        const lay2 = calcularLayout(blocos, { lim: l0.lim, hf, escalaPal: wsPal, quebras: new Set(quebras),
                                              limSeguro: (1046 - (A.x + l0.dx)) / l0.s });
        const bb2 = caixaDoLayout(lay2);
        if (bb2) extraDy = b0.h - bb2.h * l0.s;                // 'n': a borda de baixo fica parada
      }
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
    if (gesto.tipo === "mover" && !gesto.moveu) {              // foi um clique: seleciona a palavra
      const w = instEm(ponto(e));
      setSelGid(w ? w.gid : -1);
      setAviso("");
    }
    setGesto(null);
  };

  // ── linhas: Enter divide, Backspace junta ──
  const localizar = () => {
    if (!instSel) { setAviso("Clique numa palavra primeiro."); return null; }
    const idx = lay.findIndex(p => p.gid === instSel.gid);
    const rank = lay.slice(0, idx).filter(p => p.ed && p.k === instSel.k).length;
    return acharToken(temaNovo !== null ? temaNovo : tema, instSel.k, rank);
  };
  const editarTema = (r, modo) => {
    if (!r) return false;
    const { linhas, li, ti, toks } = r;
    if (modo === "dividir") {
      if (ti === 0) return false;
      const ini = (linhas[li].trim()[0]) || "";
      const simb = (ini === ":" || ini === "*") ? ini : "";
      const a = toks.slice(0, ti).join(" ");
      let b = toks.slice(ti).join(" ");
      if (simb && !/^[:*-]/.test(b)) b = simb + b;             // a nova linha mantém o estilo da anterior
      linhas.splice(li, 1, a, b);
    } else {
      if (ti !== 0 || li === 0) return false;
      const prev = linhas[li - 1].trim();
      let cur = linhas[li].trim();
      if ((cur[0] === ":" || cur[0] === "*") && cur[0] === prev[0]) cur = cur.slice(1);
      linhas.splice(li - 1, 2, `${prev} ${cur}`.trim());
    }
    setTemaNovo(linhas.join("\n"));
    return true;
  };
  const dividirLinha = () => {
    if (!instSel) { setAviso("Clique numa palavra primeiro."); return; }
    if (instSel.primeiro) { setAviso("Essa palavra já começa um bloco."); return; }
    if (instSel.fixo) { setAviso("Essa linha tem estilo especial e não se divide aqui."); return; }
    setQuebras(q => (q.includes(instSel.gid) ? q : [...q, instSel.gid]));
    editarTema(localizar(), "dividir");
    setAviso("Nova linha criada.");
  };
  const juntarLinha = () => {
    if (!instSel) { setAviso("Clique numa palavra primeiro."); return; }
    if (!instSel.ini) { setAviso("Backspace junta quando a palavra começa uma linha."); return; }
    if (instSel.primeiro) {                                     // início de bloco: junta os blocos do tema (aparece ao aplicar)
      setAviso(editarTema(localizar(), "juntar") ? "Linhas juntadas — aparece ao aplicar." : "Essa já é a primeira linha.");
      return;
    }
    if (quebras.includes(instSel.gid)) {                        // desfaz a nova linha criada por Enter
      setQuebras(q => q.filter(g => g !== instSel.gid));
      editarTema(localizar(), "juntar");
      setAviso("Linhas juntadas.");
      return;
    }
    const idx = lay.findIndex(p => p.gid === instSel.gid);      // quebra automática: alarga a caixa para caber
    const ant = lay[idx - 1];
    if (!ant) return;
    const precisa = (ant.x + ant.w - instSel.x0b) + instSel.esp + instSel.w;
    const atual = local.lim !== null ? local.lim : Math.max(...lay.map(p => p.x + p.w - p.x0b));
    setLocal(l => ({ ...l, lim: Math.max(atual, precisa) }));
    setAviso("Caixa alargada para a palavra caber na linha de cima.");
  };
  const aoTeclar = (e) => {
    if (e.key === "Escape") { onFechar(); return; }
    if (aplicando) return;
    if (e.key === "Enter") { e.preventDefault(); dividirLinha(); }
    else if (e.key === "Backspace") { e.preventDefault(); juntarLinha(); }
  };

  const mudarCor = (nome) => { if (sel) setCores(c => ({ ...c, [sel]: nome })); };
  const mudarEscalaPalavra = (delta) => {
    if (!sel) return;
    setWsPal(m => ({ ...m, [sel]: limitar(+(((m[sel] || 1)) + delta).toFixed(3), 0.6, 1.8) }));
  };
  const limparPalavra = () => {
    if (!sel) return;
    setCores(c => ({ ...c, [sel]: "" }));
    setWsPal(m => { const n = { ...m }; delete n[sel]; return n; });
  };

  const corSel = sel in cores
    ? cores[sel]
    : ((ajuste.palavras && ajuste.palavras[sel] && ajuste.palavras[sel].cor) || "");
  const pctSel = Math.round((((ajuste.palavras && ajuste.palavras[sel] && ajuste.palavras[sel].escala) || 1) * (wsPal[sel] || 1)) * 100);

  // tira de ferramentas: fica FORA do texto (acima da caixa; abaixo se não houver espaço)
  const tiraEmCima = caixa.y * f > 70;
  const tiraTopo = tiraEmCima ? caixa.y * f - 5 : (caixa.y + caixa.h) * f + 6;
  const tiraEsq = limitar(caixa.x * f, 4, Math.max(4, larg - 120));

  const btn = (ativo = false) => ({
    fontSize: "0.7rem", padding: "1px 8px", borderRadius: 999, cursor: "pointer", lineHeight: 1.5,
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

      {/* título: acompanha mover e o tamanho do texto; as palavras se reorganizam dentro do canvas */}
      <div style={{ position: "absolute", left: A.x * f, top: A.y * f, width: 0, height: 0, transformOrigin: "0 0",
                    transform: `translate(${local.dx * f}px, ${local.dy * f}px) scale(${local.s})` }}>
        <canvas ref={canvasRef}
          style={{ position: "absolute", left: -A.x * f, top: -A.y * f, width: W * f, height: H * f, pointerEvents: "none" }} />
        {lay.map(w => (w.k === sel && !w.fixo ? (
          <div key={w.gid} style={{ position: "absolute", left: (w.x - A.x) * f, top: (w.y - A.y) * f,
                                    width: w.w * f, height: w.h * f, borderRadius: 4, pointerEvents: "none",
                                    border: w.gid === selGid ? "2px solid #049DBF" : "1px dashed #049DBF",
                                    background: w.gid === selGid ? "rgba(4,157,191,0.18)" : "rgba(4,157,191,0.07)" }} />
        ) : null))}
      </div>

      {/* caixa tracejada com as 8 alças */}
      <div style={{ position: "absolute", left: caixa.x * f, top: caixa.y * f, width: caixa.w * f, height: caixa.h * f,
                    border: "1.5px dashed rgba(249,171,11,0.95)", borderRadius: 6, pointerEvents: "none" }}>
        {ALCAS.map(([id, lx, ly]) => (
          <div key={id} style={{ position: "absolute", left: `${lx * 100}%`, top: `${ly * 100}%`,
                                 width: id.length === 2 ? 12 : 10, height: id.length === 2 ? 12 : 10,
                                 transform: "translate(-50%, -50%)", background: id.length === 2 ? "#fff" : "#F9AB0B",
                                 border: "2px solid #F9AB0B", borderRadius: id.length === 2 ? 3 : 6, cursor: CURSOR[id] }} />
        ))}
      </div>

      {/* alça de tamanho da palavra selecionada */}
      {alcaPalavra && (
        <div title="Arraste para aumentar/diminuir esta palavra"
          style={{ position: "absolute", left: alcaPalavra.x * f, top: alcaPalavra.y * f, width: 12, height: 12,
                   transform: "translate(-50%, -50%)", background: "#049DBF", border: "2px solid #fff",
                   borderRadius: "50%", cursor: "nwse-resize", pointerEvents: "none", boxShadow: "0 0 0 1px #049DBF" }} />
      )}

      {/* tira fina de ferramentas da palavra (fora do texto) */}
      {instSel && (
        <div data-barra="1" onClick={e => e.stopPropagation()}
          style={{ position: "absolute", left: tiraEsq, top: tiraTopo, maxWidth: larg - 8,
                   transform: tiraEmCima ? "translateY(-100%)" : "none",
                   display: "flex", alignItems: "center", gap: 4, flexWrap: "wrap", padding: "3px 7px",
                   background: "rgba(255,255,255,0.97)", border: "1px solid #ddd", borderRadius: 14,
                   boxShadow: "0 1px 6px rgba(0,0,0,0.2)", fontSize: "0.7rem", color: "#024059" }}>
          <strong style={{ marginRight: 2 }}>“{instSel.t}”</strong>
          <button type="button" style={btn(!corSel)} onClick={() => mudarCor("")}>Padrão</button>
          {Object.entries(PALETA).map(([id, c]) => (
            <button key={id} type="button" title={c.nome} onClick={() => mudarCor(id)}
              style={{ width: 17, height: 17, borderRadius: "50%", padding: 0, cursor: "pointer", background: c.hex,
                       border: corSel === id ? "2.5px solid #F9AB0B" : "1px solid #9aa" }} />
          ))}
          <span style={{ color: "#aaa" }}>|</span>
          <button type="button" style={btn()} onClick={() => mudarEscalaPalavra(-0.1)}>A−</button>
          <span style={{ minWidth: 28, textAlign: "center" }}>{pctSel}%</span>
          <button type="button" style={btn()} onClick={() => mudarEscalaPalavra(0.1)}>A+</button>
          <span style={{ color: "#aaa" }}>|</span>
          <button type="button" title="Nova linha aqui (Enter)" style={btn()} onClick={dividirLinha}>↵</button>
          <button type="button" title="Juntar com a linha de cima (Backspace)" style={btn()} onClick={juntarLinha}>⌫</button>
          <button type="button" title="Voltar esta palavra ao padrão" style={btn()} onClick={limparPalavra}>↩</button>
        </div>
      )}

      {/* aplicar / cancelar */}
      <div data-barra="1" onClick={e => e.stopPropagation()}
        style={{ position: "absolute", right: 6, bottom: 6, display: "flex", gap: 6 }}>
        <button type="button" style={{ ...btn(false), background: "rgba(255,255,255,0.95)" }}
          onClick={onFechar} disabled={aplicando}>✕ Cancelar</button>
        <button type="button" style={btn(true)} onClick={aplicar} disabled={aplicando}>
          {aplicando ? "Aplicando…" : "✓ Aplicar"}
        </button>
      </div>
      <div style={{ position: "absolute", left: 6, bottom: 6, maxWidth: "58%", fontSize: "0.62rem", color: "#fff",
                    background: "rgba(2,64,89,0.78)", padding: "3px 9px", borderRadius: 10, pointerEvents: "none",
                    lineHeight: 1.35 }}>
        {aviso || "Quinas = tamanho • laterais = largura • topo/base = espaço • clique numa palavra • clique fora aplica"}
      </div>
    </div>
  );
}
