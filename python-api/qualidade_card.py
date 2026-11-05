"""
python-api/qualidade_card.py  —  v76  —  portão de qualidade + ajuste manual do título

Dois recursos, ambos ADITIVOS (se este módulo falhar ao carregar, a plataforma segue como antes):

1) PORTÃO DE QUALIDADE (renderizar_titulo + AvaliadorCard)
   Depois de desenhar o título, mede o que dá para medir e, se reprovar, tenta de novo SÓ o título
   (mesmo fundo, outra seed) até 3 vezes, ficando com a melhor nota. Checagens:
     - contraste do texto contra o fundo real, linha por linha (fração de fundo "parecido" com a cor do texto)
     - fundo muito detalhado atrás do texto (folhas, objetos, bokeh forte)
     - texto sobre rosto (Haar frontal + perfil, independente do que o pipeline já detectou)
     - linha pequena demais para celular
     - texto fora da zona segura
   Nunca bloqueia a aprovação: o resultado vira um aviso no editor.

2) AJUSTE MANUAL (rota POST /ajustar-card)
   Reaproveita o MESMO motor de título sobre o MESMO fundo, com parâmetros novos e opcionais de
   desenhar_titulo: escala_fonte, cor_forcada, y_forcado, x_texto, estrategia_fixa, forma_fixa.
   Ações: "ajustar" (tamanho, cor, deslocamento x/y — sempre relativo ao card original) e
   "novo_texto" (sorteia outra composição do título mantendo o fundo).
   Guarda os últimos cards em memória (só o fundo, em JPEG); se o servidor reiniciar, pede para gerar de novo.
"""
import io, sys, time, base64, random, threading
from collections import OrderedDict

import numpy as np
from PIL import Image
from flask import Blueprint, request, jsonify

W, H = 1080, 1350
SAFE_LEFT, SAFE_RIGHT, SAFE_TOP, SAFE_BOTTOM = 34, 1046, 60, 1290

MAX_TENTATIVAS = 3
ORCAMENTO_SEG = 28.0          # tempo máximo gasto com novas tentativas
NOTA_OK = 72                  # abaixo disso o card é considerado "com problema"
MAX_REGISTROS = 8             # quantos cards ficam disponíveis para ajuste

PALETA_AJUSTE = {             # mesmas cores da identidade (main.py)
    "branco":  (244, 246, 248),
    "marinho": (2, 64, 89),
    "amarelo": (255, 221, 0),
    "laranja": (249, 171, 11),
    "teal":    (4, 157, 191),
    "citrico": (146, 204, 29),
}

bp = Blueprint("qualidade_card", __name__)
_REG = OrderedDict()          # card_id -> dados para ajuste
_LOCK = threading.Lock()


# ───────────────────────────── utilidades ─────────────────────────────
def _m():
    """Módulo main (onde vivem desenhar_titulo e _cards_pendentes)."""
    for nome in ("main", "__main__"):
        mod = sys.modules.get(nome)
        if mod is not None and hasattr(mod, "desenhar_titulo") and hasattr(mod, "_cards_pendentes"):
            return mod
    raise RuntimeError("modulo main indisponivel")


def _lum_rel(rgb):
    """Luminância relativa WCAG (0..1). rgb: array (...,3) 0..255."""
    c = np.asarray(rgb, dtype=np.float32) / 255.0
    c = np.where(c <= 0.03928, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)
    return 0.2126 * c[..., 0] + 0.7152 * c[..., 1] + 0.0722 * c[..., 2]


def _razao(l1, l2):
    a = np.maximum(l1, l2)
    b = np.minimum(l1, l2)
    return (a + 0.05) / (b + 0.05)


# ───────────────────────────── avaliação ─────────────────────────────
class AvaliadorCard:
    """Mede a legibilidade do título sobre UM fundo (calculado uma vez, reaproveitado nas tentativas)."""

    def __init__(self, base):
        self.base = np.asarray(base.convert("RGB"))
        self.h, self.w = self.base.shape[:2]
        self._lum = None
        self._rostos = None
        self._altfreq = None

    # --- insumos caros, calculados sob demanda ---
    def lum(self):
        if self._lum is None:
            self._lum = _lum_rel(self.base)
        return self._lum

    def altfreq(self):
        """Mapa de detalhe fino da luminância (pixel - versão borrada). Fundo liso ~3-6; bokeh suave ~15-19;
        folhas/objetos nítidos 28+ (medido nos cards reais da clínica)."""
        if self._altfreq is None:
            import cv2
            g = cv2.cvtColor(self.base, cv2.COLOR_RGB2GRAY).astype(np.float32)
            self._altfreq = g - cv2.GaussianBlur(g, (0, 0), 10)
        return self._altfreq

    def rostos(self):
        """Retângulos (x0,y0,x1,y1) de rostos (frontal e perfil, nos dois lados)."""
        if self._rostos is None:
            out = []
            try:
                import cv2
                g = cv2.cvtColor(self.base, cv2.COLOR_RGB2GRAY)
                lado = int(self.w * 0.07)
                kw = dict(scaleFactor=1.1, minNeighbors=6, minSize=(lado, lado))
                fr = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
                for (x, y, w, h) in fr.detectMultiScale(g, **kw):
                    out.append((int(x), int(y), int(x + w), int(y + h)))
                pf = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_profileface.xml")
                for (x, y, w, h) in pf.detectMultiScale(g, **kw):
                    out.append((int(x), int(y), int(x + w), int(y + h)))
                for (x, y, w, h) in pf.detectMultiScale(g[:, ::-1].copy(), **kw):
                    out.append((int(self.w - (x + w)), int(y), int(self.w - x), int(y + h)))
            except Exception as e:
                print(f"[qa] rostos indisponivel: {e}")
            self._rostos = out
        return self._rostos

    # --- extensão horizontal real de uma linha (onde o card difere do fundo) ---
    @staticmethod
    def _extensao_x(dif, y0, y1, x_ini, largura):
        faixa = dif[y0:y1]
        cols = np.where(faixa.max(axis=0) > 22)[0] if faixa.size else []
        if len(cols) > 8:
            return int(cols.min()), int(cols.max()) + 1
        return int(x_ini), int(min(W, x_ini + largura))

    def avaliar(self, card, info):
        """Retorna dict {nota, ok, problemas[], detalhe{}}. Sem `info` do motor, só devolve nota neutra."""
        if not info or not info.get("grupos"):
            return {"nota": None, "ok": True, "problemas": [], "detalhe": {"sem_geometria": True}}
        try:
            return self._avaliar(card, info)
        except Exception as e:  # o portão nunca derruba a geração
            print(f"[qa] avaliacao ignorada: {type(e).__name__}: {e}")
            return {"nota": None, "ok": True, "problemas": [], "detalhe": {"erro": str(e)[:120]}}

    def _avaliar(self, card, info):
        com = np.asarray(card.convert("RGB")).astype(np.int16)
        dif = np.abs(com - self.base.astype(np.int16)).max(axis=2)
        grupos = info["grupos"]
        y_fim = int(info.get("y_fim") or (grupos[-1]["y"] + grupos[-1]["alt"] * 2))
        x_ini = int(info.get("x", SAFE_LEFT + 46))
        larg = int(info.get("w", 400))

        problemas, nota = [], 100.0
        detalhe = {"linhas": []}
        pior_frac, caixas = 0.0, []
        lum = self.lum()
        altfreq = self.altfreq()

        for i, g in enumerate(grupos):
            y0 = max(0, int(g["y"]) - 6)
            prox = grupos[i + 1]["y"] - 4 if i + 1 < len(grupos) else y_fim
            y1 = min(self.h, max(y0 + 12, int(prox)))
            xa, xb = self._extensao_x(dif, y0, y1, x_ini, larg)
            xa, xb = max(0, xa - 10), min(self.w, xb + 10)
            if xb - xa < 20:
                continue
            caixas.append((xa, y0, xb, y1))
            pequena = g["alt"] < 56                    # subtítulos / linhas menores
            limiar = 3.0 if pequena else 2.2           # razão WCAG mínima (folga: sombra/glow ajudam)
            reg_rgb = self.base[y0:y1, xa:xb].reshape(-1, 3).astype(np.float32)
            reg_lum = lum[y0:y1, xa:xb].reshape(-1)
            # fração de pixels do fundo onde a cor da tinta NÃO se destaca
            fr_pior = 0.0
            for cor in g["cores"]:
                lc = float(_lum_rel(np.array(cor, dtype=np.float32)))
                ruim = (_razao(reg_lum, lc) < limiar)
                dist = np.sqrt(((reg_rgb - np.array(cor, dtype=np.float32)) ** 2).sum(axis=1))
                ruim &= dist < 120                     # cor bem diferente também conta como visível
                fr_pior = max(fr_pior, float(ruim.mean()))
            # pior célula (trechos de ~140px): pega texto que só some num pedaço
            cel = 140
            for cx in range(xa, xb, cel):
                cx1 = min(xb, cx + cel)
                if cx1 - cx < 40:
                    continue
                sub_l = lum[y0:y1, cx:cx1].reshape(-1)
                sub_c = self.base[y0:y1, cx:cx1].reshape(-1, 3).astype(np.float32)
                for cor in g["cores"]:
                    lc = float(_lum_rel(np.array(cor, dtype=np.float32)))
                    ruim = (_razao(sub_l, lc) < limiar) & (
                        np.sqrt(((sub_c - np.array(cor, dtype=np.float32)) ** 2).sum(axis=1)) < 120)
                    fr_pior = max(fr_pior, float(ruim.mean()) * 0.85)
            dens = float(np.std(altfreq[y0:y1, xa:xb]))
            detalhe["linhas"].append({"i": i + 1, "fracao_ruim": round(fr_pior, 2),
                                      "detalhe_fundo": round(dens, 1), "alt": g["alt"]})
            pior_frac = max(pior_frac, fr_pior)
            rot = f"linha {i + 1}" + (" (menor)" if pequena else "")
            if fr_pior >= 0.30:
                pen = min(45.0, fr_pior * 100 * 0.9)
                nota -= pen
                problemas.append(f"Contraste baixo na {rot}: {int(fr_pior * 100)}% do fundo é parecido com a cor do texto.")
            if dens > 26.0:
                nota -= min(18.0, (dens - 26.0) * 0.9)
                problemas.append(f"Fundo muito detalhado atrás da {rot} (folhas/objetos competem com o texto).")
            if pequena and g["alt"] < 30:
                nota -= 8
                problemas.append(f"A {rot} está pequena para ler no celular.")
            if xb > SAFE_RIGHT or xa < SAFE_LEFT or y1 > SAFE_BOTTOM or y0 < SAFE_TOP - 10:
                nota -= 25
                problemas.append(f"A {rot} passa da zona segura do Instagram.")

        # rosto
        for (fx0, fy0, fx1, fy1) in self.rostos():
            pw, ph = int((fx1 - fx0) * 0.20), int((fy1 - fy0) * 0.20)
            rx0, ry0, rx1, ry1 = fx0 - pw, fy0 - ph, fx1 + pw, fy1 + ph
            if any(not (bx1 <= rx0 or bx0 >= rx1 or by1 <= ry0 or by0 >= ry1) for (bx0, by0, bx1, by1) in caixas):
                nota -= 45
                problemas.append("O texto passa por cima do rosto.")
                break

        nota = max(0.0, min(100.0, nota))
        grave = any("rosto" in p for p in problemas) or pior_frac >= 0.55
        detalhe["pior_fracao"] = round(pior_frac, 2)
        return {"nota": int(round(nota)), "ok": (nota >= NOTA_OK and not grave),
                "problemas": problemas, "detalhe": detalhe}


# ───────────────────── renderização com tentativas ─────────────────────
def _info_motor(M):
    tl = getattr(M, "_TL", None)
    info = getattr(tl, "info", None) if tl is not None else None
    return dict(info) if info else None


def _render(M, base, tema, seed, kw):
    """Uma chamada ao motor de título. cor_dest/cor_fundo_txt acompanham a seed quando o chamador os passou."""
    kw2 = dict(kw)
    if kw2.get("cor_dest") is not None:
        kw2["cor_dest"], kw2["cor_fundo_txt"] = M._escolher_cor_destaque(seed)
    card, _ = M.desenhar_titulo(base, tema, seed, **kw2)
    return card, kw2, _info_motor(M)


def renderizar_titulo(M, base, tema, seed, kw, tentativas=MAX_TENTATIVAS):
    """Desenha o título; se o portão reprovar, tenta de novo (outra seed, mesmo fundo). A 1ª tentativa é
    idêntica ao comportamento anterior. Devolve o card (PIL) com .qa_relatorio e .qa_registro anexados."""
    av = AvaliadorCard(base)
    inicio = time.time()
    melhor = None
    n = 0
    for i in range(max(1, tentativas)):
        sd = seed if i == 0 else (int(seed) + i * 7919) % 999983
        try:
            card, kw_usado, info = _render(M, base, tema, sd, kw)
        except Exception:
            if melhor is None:
                raise
            break
        n += 1
        rel = av.avaliar(card, info)
        print(f"[qa] tentativa {n}: nota={rel['nota']} ok={rel['ok']} problemas={len(rel['problemas'])}")
        if melhor is None or (rel["nota"] or 0) > (melhor[1]["nota"] or 0):
            melhor = (card, rel, sd, kw_usado, info)
        if rel["ok"] or rel["nota"] is None:
            break
        if time.time() - inicio > ORCAMENTO_SEG:
            print("[qa] orcamento de tempo esgotado")
            break
    card, rel, sd, kw_usado, info = melhor
    rel = dict(rel)
    rel["tentativas"] = n
    card.qa_relatorio = rel
    card.qa_registro = {"base": base, "kw": kw_usado, "tema": tema, "seed": sd, "info": info}
    return card


# ───────────────────────── registro para ajuste ─────────────────────────
def _publico(rel):
    if not rel:
        return None
    return {"nota": rel.get("nota"), "ok": bool(rel.get("ok")), "problemas": list(rel.get("problemas") or []),
            "tentativas": rel.get("tentativas", 1)}


def _caixa(info):
    if not info:
        return None
    return {"x": int(info.get("x", 0)), "y": int(info.get("y", 0)),
            "w": int(info.get("w", 0)), "h": int(max(1, info.get("y_fim", 0) - info.get("y", 0)))}


def registrar(card_id, card):
    """Chamado pelas rotas depois de gerar o card. Devolve campos extras para a resposta (ou None)."""
    reg = getattr(card, "qa_registro", None)
    if not reg:
        return None
    buf = io.BytesIO()
    reg["base"].convert("RGB").save(buf, format="JPEG", quality=97, subsampling=0)
    with _LOCK:
        _REG[card_id] = {"base_jpg": buf.getvalue(), "kw": reg["kw"], "tema": reg["tema"],
                         "seed": reg["seed"], "info": reg["info"]}
        while len(_REG) > MAX_REGISTROS:
            _REG.popitem(last=False)
    return {"qa": _publico(getattr(card, "qa_relatorio", None)), "ajustavel": bool(reg.get("info")),
            "caixa": _caixa(reg.get("info"))}


def _clamp(v, lo, hi):
    return max(lo, min(hi, v))


@bp.route("/ajustar-card", methods=["POST"])
def rota_ajustar_card():
    M = _m()
    data = request.get_json() or {}
    card_id = data.get("card_id", "")
    with _LOCK:
        reg = _REG.get(card_id)
    pend = M._cards_pendentes.get(card_id)
    if not reg or not pend:
        return jsonify({"erro": "Esse card saiu da memória do servidor (reinício ou muitos cards novos). Gere novamente."}), 410
    base = Image.open(io.BytesIO(reg["base_jpg"])).convert("RGB")
    acao = (data.get("acao") or "ajustar").strip()
    try:
        if acao == "novo_texto":
            sd = random.randint(1, 999982)
            card = renderizar_titulo(M, base, reg["tema"], sd, reg["kw"])
            novo = card.qa_registro
            with _LOCK:
                _REG[card_id] = {"base_jpg": reg["base_jpg"], "kw": novo["kw"], "tema": reg["tema"],
                                 "seed": novo["seed"], "info": novo["info"]}
            info_vis, rel = novo["info"], card.qa_relatorio
        else:
            info = reg["info"] or {}
            kw = dict(reg["kw"])
            kw["estrategia_fixa"] = info.get("estrategia")
            kw["forma_fixa"] = info.get("forma")
            escala = _clamp(float(data.get("escala", 1.0)), 0.5, 1.6)
            dx = int(_clamp(float(data.get("dx", 0)), -700, 700))
            dy = int(_clamp(float(data.get("dy", 0)), -900, 900))
            if abs(escala - 1.0) > 0.005:
                kw["escala_fonte"] = escala
            kw["x_texto"] = int(_clamp(info.get("x", SAFE_LEFT + 46) + dx, SAFE_LEFT, SAFE_RIGHT - 200))
            kw["y_forcado"] = int(info.get("y", SAFE_TOP + 20) + dy)
            if kw.get("max_px_pessoa"):   # título arrastado para a direita não pode passar da zona segura
                kw["max_px_pessoa"] = int(max(240, min(int(kw["max_px_pessoa"]), SAFE_RIGHT - kw["x_texto"])))
            cor = (data.get("cor") or "").strip().lower()
            if cor in PALETA_AJUSTE:
                kw["cor_forcada"] = PALETA_AJUSTE[cor]
            card, kw_usado, info_novo = _render(M, base, reg["tema"], reg["seed"], kw)
            rel = AvaliadorCard(base).avaliar(card, info_novo)
            rel["tentativas"] = 1
            info_vis = info_novo
        buf = io.BytesIO()
        card.save(buf, format="JPEG", quality=93)
        card_bytes = buf.getvalue()
        pend["card_bytes"] = card_bytes
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"erro": f"Erro ao ajustar o título: {type(e).__name__}: {str(e)[:200]}"}), 500
    return jsonify({
        "card_id": card_id,
        "preview_url": f"data:image/jpeg;base64,{base64.b64encode(card_bytes).decode()}",
        "qa": _publico(rel),
        "caixa": _caixa(info_vis),
    })
