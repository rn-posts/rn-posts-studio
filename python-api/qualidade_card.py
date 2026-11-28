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
ORCAMENTO_SEG = 40.0          # tempo máximo (contado desde o início do portão) para tentar de novo
NOTA_OK = 72                  # abaixo disso o card é considerado "com problema"
MAX_REGISTROS = 8             # quantos cards ficam disponíveis para ajuste
SCRIM_CORRETIVO = True        # v86: se nenhuma cor de texto contrasta com o fundo, escurece suave a área do título (False desliga só isso)

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
                g0 = cv2.cvtColor(self.base, cv2.COLOR_RGB2GRAY)
                f = 0.5  # detecta em metade da resolução: ~4x mais rápido (o Render free é lento)
                g = cv2.resize(g0, (int(self.w * f), int(self.h * f)), interpolation=cv2.INTER_AREA)
                lado = int(g.shape[1] * 0.07)
                kw = dict(scaleFactor=1.1, minNeighbors=6, minSize=(lado, lado))
                gw = g.shape[1]
                fr = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
                for (x, y, w, h) in fr.detectMultiScale(g, **kw):
                    out.append((int(x / f), int(y / f), int((x + w) / f), int((y + h) / f)))
                pf = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_profileface.xml")
                for (x, y, w, h) in pf.detectMultiScale(g, **kw):
                    out.append((int(x / f), int(y / f), int((x + w) / f), int((y + h) / f)))
                for (x, y, w, h) in pf.detectMultiScale(g[:, ::-1].copy(), **kw):
                    out.append((int((gw - (x + w)) / f), int(y / f), int((gw - x) / f), int((y + h) / f)))
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

    def avaliar(self, card, info, kw=None):
        """Retorna dict {nota, ok, problemas[], detalhe{}}. Sem `info` do motor, só devolve nota neutra."""
        if not info or not info.get("grupos"):
            return {"nota": None, "ok": True, "problemas": [], "detalhe": {"sem_geometria": True}}
        try:
            res = self._avaliar(card, info)
            try:  # v84: tamanho, destaque, contraste por palavra e critérios separados (se falhar, vale a nota do v83)
                import qualidade_v84 as _v84
                res = _v84.complementar(self, res, info, kw)
            except Exception as _e84:
                print(f"[qa] v84 complementar ignorado: {type(_e84).__name__}: {_e84}")
            return res
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
        grave = any("rosto" in p or "zona segura" in p for p in problemas) or pior_frac >= 0.55  # v91: texto fora da zona segura também reprova
        detalhe["pior_fracao"] = round(pior_frac, 2)
        return {"nota": int(round(nota)), "ok": (nota >= NOTA_OK and not grave),
                "problemas": problemas, "detalhe": detalhe}


# ───────────────────── renderização com tentativas ─────────────────────
def _info_motor(M):
    tl = getattr(M, "_TL", None)
    info = getattr(tl, "info", None) if tl is not None else None
    return dict(info) if info else None


ALT_MAX_TITULO = 0.40  # v91: altura máxima do bloco do título (fração da altura do card) quando há pessoa: acima disso vira parede de texto


def _fator_encaixe(info, H, tem_pessoa):
    """v91: quanto o título precisa encolher (<1) para caber na zona segura e, com pessoa, no teto de altura. 1.0 se já cabe.
    Usa a altura REAL desenhada (y_fim do motor), não a estimada."""
    try:
        topo, fim = int(info["y"]), int(info["y_fim"])
        h = max(1, fim - topo)
        f = 1.0
        if fim > SAFE_BOTTOM - 4 or topo < SAFE_TOP - 10:
            f = min(f, max(0.3, ((SAFE_BOTTOM - 4) - (SAFE_TOP + 20)) / h))
        if tem_pessoa and h > ALT_MAX_TITULO * H:
            f = min(f, ALT_MAX_TITULO * H / h)
        return f
    except Exception:
        return 1.0


def _render(M, base, tema, seed, kw, encaixar=False):
    """Uma chamada ao motor de título. cor_dest/cor_fundo_txt acompanham a seed quando o chamador os passou.
    v91: encaixar=True (só na geração, não nos ajustes manuais) encolhe a fonte até o título caber."""
    kw2 = dict(kw)
    kw2.setdefault("altura_min_sub", 46)  # v87: linha secundária nunca abaixo do mínimo de leitura no celular (já na 1ª tentativa)
    kw2.setdefault("zona_livre", True)  # v87: com pessoa em pé, o título pode usar a área limpa do alto (a pontuação escolhe a zona)
    if kw2.get("cor_dest") is not None:
        kw2["cor_dest"], kw2["cor_fundo_txt"] = M._escolher_cor_destaque(seed)
    try:
        card, _ = M.desenhar_titulo(base, tema, seed, **kw2)
        info = _info_motor(M)
        if encaixar and info and kw2.get("y_forcado") is None:  # v91: encaixe do título (altura real x zona segura x teto)
            chave = "escala_pessoa" if (kw2.get("tem_pessoa") and kw2.get("escala_pessoa")) else "escala_fonte"
            alt_card, tp = int(base.size[1]), bool(kw2.get("tem_pessoa"))
            f0 = _fator_encaixe(info, alt_card, tp)
            if f0 < 0.995:
                # busca a MAIOR escala que cabe: a altura não varia de forma contínua (ao cruzar o limite da quebra de linha ela despenca)
                h0 = int(info["y_fim"]) - int(info["y"])
                esc0 = float(kw2.get(chave) or 1.0)
                hi, lo, melhor_t, ultimo = esc0, None, None, None   # hi = escala que NÃO cabe; lo = maior que cabe
                s = max(0.45, hi * (f0 ** 0.5) * 0.97)
                for _it in range(6):
                    kw3 = dict(kw2)
                    kw3[chave] = s
                    card_t, _ = M.desenhar_titulo(base, tema, seed, **kw3)
                    info_t = _info_motor(M)
                    ultimo = (card_t, info_t, kw3)
                    if _fator_encaixe(info_t, alt_card, tp) >= 0.995:      # cabe
                        lo, melhor_t = s, ultimo
                        if hi - lo <= 0.05 * hi:
                            break
                        s = (lo + hi) / 2.0                                # tenta crescer de volta até o limite
                    else:
                        hi = s
                        if lo is None:
                            if s <= 0.46:
                                break
                            s = max(0.45, s * min(0.85, _fator_encaixe(info_t, alt_card, tp) ** 0.5 * 0.97))
                        else:
                            if hi - lo <= 0.05 * hi:
                                break
                            s = (lo + hi) / 2.0
                card, info, kw2 = melhor_t if melhor_t else ultimo
                print(f"[qa] encaixe do titulo: altura {h0}px -> {int(info['y_fim']) - int(info['y'])}px (topo {int(info['y'])}, fim {int(info['y_fim'])}); escala {esc0:.2f} -> {float(kw2.get(chave)):.2f}")
    finally:  # v78: o estilo por palavra vale só para este render (não vaza para outros desenhos na mesma thread)
        try:
            M._TL.palavras = {}
            M._TL.fundo_pendente = False
            M._TL.linhas_pos = None
        except Exception:
            pass
    return card, kw2, info


def renderizar_titulo(M, base, tema, seed, kw, tentativas=MAX_TENTATIVAS, foto_rel=None):
    """Desenha o título; se o portão reprovar, tenta de novo (outra seed, mesmo fundo). A 1ª tentativa é
    idêntica ao comportamento anterior. Devolve o card (PIL) com .qa_relatorio e .qa_registro anexados."""
    av = AvaliadorCard(base)
    inicio = time.time()
    melhor = None
    n = 0
    kw_i = kw
    sd = seed
    base_i, av_i, melhor_base = base, av, base  # v85: base usada em cada tentativa (pode ganhar um ajuste de luz)
    for i in range(max(1, tentativas)):
        sd_prev = sd
        sd = seed if i == 0 else (int(seed) + i * 7919) % 999983
        if i > 0:  # v84: se só tamanho/destaque falharam, a nova tentativa corrige ESSES pontos (fonte maior, palavra em evidência)
            try:
                import qualidade_v84 as _v84
                kw_i, sd = _v84.proxima_tentativa(base, kw_usado, info, rel, sd_prev, sd)
                if _v84.precisa_escurecer(rel):  # v86: o fundo é o problema: mede o fundo, escolhe a cor do texto que contrasta e, se preciso, escurece suave
                    kw_i, base_i = _v84.corrigir_contraste(base, info, kw_i, SCRIM_CORRETIVO)
                    av_i = AvaliadorCard(base_i) if base_i is not base else av
            except Exception as _e84:
                print(f"[qa] v84 proxima tentativa ignorada: {type(_e84).__name__}: {_e84}")
        try:
            card, kw_usado, info = _render(M, base_i, tema, sd, kw_i, encaixar=True)  # v91: encaixe só na geração
        except Exception as _e:
            if melhor is None:
                raise
            print(f"[qa] tentativa {i + 1} falhou: {type(_e).__name__}: {_e}")
            break
        n += 1
        rel = av_i.avaliar(card, info, kw_usado)
        print(f"[qa] tentativa {n}: nota={rel['nota']} ok={rel['ok']} problemas={len(rel['problemas'])} t={time.time() - inicio:.1f}s")
        if melhor is None or (rel["nota"] or 0) >= (melhor[1]["nota"] or 0) + 4:  # v89: só troca a 1ª tentativa por uma claramente melhor (antes: qualquer +1 mudava a composição toda)
            melhor = (card, rel, sd, kw_usado, info)
            melhor_base = base_i
        if rel["ok"] or rel["nota"] is None:
            break
        if time.time() - inicio > ORCAMENTO_SEG:
            print("[qa] orcamento de tempo esgotado")
            break
    card, rel, sd, kw_usado, info = melhor
    rel = dict(rel)
    rel["tentativas"] = n
    try:  # v84: critério "foto e cenário" e nota = menor critério medido (sem foto avaliada, o relatório fica parcial)
        import qualidade_v84 as _v84
        rel = _v84.mesclar_foto(rel, foto_rel)
    except Exception as _e84:
        print(f"[qa] v84 mesclar foto ignorado: {type(_e84).__name__}: {_e84}")
    card.qa_relatorio = rel
    # v84: o registro (base do "Novo texto" e dos ajustes) não congela estratégia/forma da tentativa que corrigiu o tamanho
    kw_reg = {k: v for k, v in kw_usado.items() if k not in ("estrategia_fixa", "forma_fixa")}
    card.qa_registro = {"base": melhor_base, "kw": kw_reg, "tema": tema, "seed": sd, "info": info, "foto_rel": foto_rel}
    return card


# ───────────────────────── registro para ajuste ─────────────────────────
def _publico(rel):
    if not rel:
        return None
    return {"nota": rel.get("nota"), "ok": bool(rel.get("ok")), "problemas": list(rel.get("problemas") or []),
            "tentativas": rel.get("tentativas", 1),
            "criterios": rel.get("criterios") or {}, "parcial": bool(rel.get("parcial"))}  # v84


def _caixa(info):
    """Caixa visível do título em px do card. Usa as palavras realmente desenhadas; sem elas, a estimativa do motor."""
    if not info:
        return None
    try:
        lns = info.get("linhas_pos") or []
        if lns:
            x0 = min(p["x0"] for l in lns for p in l["palavras"])
            x1 = max(p["x1"] for l in lns for p in l["palavras"])
            y0 = min(l["y"] for l in lns)
            y1 = max(l["y"] + l["h"] for l in lns)
            pad = 10
            x0, y0 = max(0, x0 - pad), max(0, y0 - pad)
            x1, y1 = min(W, x1 + pad), min(H, y1 + pad)
            if x1 - x0 > 20 and y1 - y0 > 20:
                return {"x": int(x0), "y": int(y0), "w": int(x1 - x0), "h": int(y1 - y0)}
    except Exception:
        pass
    return {"x": int(info.get("x", 0)), "y": int(info.get("y", 0)),
            "w": int(info.get("w", 0)), "h": int(max(1, info.get("y_fim", 0) - info.get("y", 0)))}


def _linhas_pub(info):
    """Linhas e palavras realmente desenhadas (px do card), para o editor reorganizar o texto ao vivo."""
    out = []
    try:
        ids = {p["id"] for p in (info.get("palavras") or [])}
        for l in (info.get("linhas_pos") or []):
            out.append({"y": l["y"], "h": l["h"], "palavras": [
                {"k": p["k"], "t": p["t"], "x0": p["x0"], "x1": p["x1"], "cor": p["cor"], "ed": p["k"] in ids}
                for p in l["palavras"]]})
    except Exception:
        return []
    return out


def _palavras_pos(info):
    """Retângulos (px do card) das palavras editáveis, para o editor local clicar nelas."""
    out = []
    try:
        ids = {p["id"] for p in (info.get("palavras") or [])}
        for l in (info.get("linhas_pos") or []):
            for p in l["palavras"]:
                if p["k"] in ids:
                    out.append({"k": p["k"], "t": p["t"], "x": p["x0"], "y": l["y"],
                                "w": round(p["x1"] - p["x0"], 1), "h": l["h"], "cor": p["cor"]})
    except Exception:
        pass
    return out


def registrar(card_id, card):
    """Chamado pelas rotas depois de gerar o card. Devolve campos extras para a resposta (ou None)."""
    reg = getattr(card, "qa_registro", None)
    if not reg:
        return None
    buf = io.BytesIO()
    reg["base"].convert("RGB").save(buf, format="JPEG", quality=97, subsampling=0)
    with _LOCK:
        _REG[card_id] = {"base_jpg": buf.getvalue(), "kw": reg["kw"], "tema": reg["tema"],
                         "seed": reg["seed"], "info": reg["info"], "info_atual": reg["info"],
                         "foto_rel": reg.get("foto_rel")}  # v84
        while len(_REG) > MAX_REGISTROS:
            _REG.popitem(last=False)
    return {"qa": _publico(getattr(card, "qa_relatorio", None)), "ajustavel": bool(reg.get("info")),
            "caixa": _caixa(reg.get("info")), "palavras": (reg.get("info") or {}).get("palavras", [])}


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
            card = renderizar_titulo(M, base, reg["tema"], sd, reg["kw"], foto_rel=reg.get("foto_rel"))  # v84
            novo = card.qa_registro
            with _LOCK:
                _REG[card_id] = {"base_jpg": reg["base_jpg"], "kw": novo["kw"], "tema": reg["tema"],
                                 "seed": novo["seed"], "info": novo["info"], "info_atual": novo["info"],
                                 "foto_rel": reg.get("foto_rel")}
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
                kw["escala_fonte"] = escala * float(reg["kw"].get("escala_fonte") or 1.0)  # v84: relativo ao tamanho que o portão já corrigiu
            # v80: largura (o texto reflui) e espaçamento entre linhas; a largura acompanha o tamanho para manter as quebras
            largura = _clamp(float(data.get("largura") or 1.0), 0.4, 2.5)
            espaco = _clamp(float(data.get("espaco") or 1.0), 0.6, 2.2)
            max_px0 = info.get("max_px")
            if max_px0 and (abs(escala - 1.0) > 0.005 or abs(largura - 1.0) > 0.005):
                kw["largura_px"] = int(max_px0 * escala * largura)
            if abs(espaco - 1.0) > 0.005:
                kw["respiro"] = _clamp(float(kw.get("respiro") or 1.10) * espaco, 0.8, 2.4)
            tema_novo = data.get("tema")
            tema_uso = (tema_novo.strip() if isinstance(tema_novo, str) and tema_novo.strip()
                        and len(tema_novo) <= 600 else reg["tema"])
            kw["x_texto"] = int(_clamp(info.get("x", SAFE_LEFT + 46) + dx, SAFE_LEFT, SAFE_RIGHT - 200))
            kw["y_forcado"] = int(info.get("y", SAFE_TOP + 20) + dy)
            if kw.get("max_px_pessoa"):   # título arrastado para a direita não pode passar da zona segura
                kw["max_px_pessoa"] = int(max(240, min(int(kw["max_px_pessoa"]), SAFE_RIGHT - kw["x_texto"])))
            cor = (data.get("cor") or "").strip().lower()
            if cor in PALETA_AJUSTE:
                kw["cor_forcada"] = PALETA_AJUSTE[cor]
            # v78: cor/tamanho por palavra ({chave: {"cor": nome, "escala": 1.2}}), sempre relativo ao original
            pal_estilo = {}
            for chave, o in (data.get("palavras") or {}).items():
                if not isinstance(o, dict) or not isinstance(chave, str):
                    continue
                item = {}
                cnome = (o.get("cor") or "").strip().lower()
                if cnome in PALETA_AJUSTE:
                    item["cor"] = PALETA_AJUSTE[cnome]
                try:
                    esc = float(o.get("escala") or 1.0)
                except (TypeError, ValueError):
                    esc = 1.0
                if abs(esc - 1.0) > 0.01:
                    item["escala"] = _clamp(esc, 0.6, 1.8)
                if item:
                    pal_estilo[chave[:40]] = item
            if pal_estilo:
                kw["palavras_estilo"] = pal_estilo
            card, kw_usado, info_novo = _render(M, base, tema_uso, reg["seed"], kw)
            rel = AvaliadorCard(base).avaliar(card, info_novo, kw_usado)
            rel["tentativas"] = 1
            try:  # v84: mantém o critério da foto (a foto não muda quando só o título é ajustado)
                import qualidade_v84 as _v84
                rel = _v84.mesclar_foto(rel, reg.get("foto_rel"))
            except Exception as _e84:
                print(f"[qa] v84 mesclar foto ignorado: {type(_e84).__name__}: {_e84}")
            info_vis = info_novo
            with _LOCK:
                if card_id in _REG:
                    _REG[card_id]["info_atual"] = info_novo
                    _REG[card_id]["tema"] = tema_uso
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
        "palavras": (info_vis or {}).get("palavras", []),
    })


@bp.route("/aplicar-manual", methods=["POST"])
def rota_aplicar_manual():
    """v83: a edição manual é SOBERANA. O editor compõe a imagem final no navegador (fundo + título exatamente como
    foi editado) e envia pronta; o servidor só valida e guarda como o card. O motor de título NÃO refaz nada aqui,
    então posição, tamanho, cor e quebras ficam como o usuário deixou (inclusive sobre o rosto)."""
    M = _m()
    data = request.get_json(silent=True) or {}
    card_id = data.get("card_id", "")
    with _LOCK:
        reg = _REG.get(card_id)
    pend = M._cards_pendentes.get(card_id)
    if not reg or not pend:
        return jsonify({"erro": "Esse card saiu da memória do servidor (reinício ou muitos cards novos). Gere novamente."}), 410
    try:
        uri = data.get("imagem") or ""
        if not uri.startswith("data:image/jpeg;base64,") or len(uri) > 12_000_000:
            return jsonify({"erro": "Imagem da edição inválida."}), 400
        img = Image.open(io.BytesIO(base64.b64decode(uri.split(",", 1)[1]))).convert("RGB")
        if img.size != (W, H):
            return jsonify({"erro": f"Tamanho inesperado da imagem: {img.size[0]}x{img.size[1]}."}), 400
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=93)
        card_bytes = buf.getvalue()

        # estado do título (onde cada palavra ficou) para a próxima abertura do editor
        est = data.get("estado") or {}
        linhas = []
        for l in (est.get("linhas") or [])[:60]:
            ps = [{"k": str(p.get("k", ""))[:40], "t": str(p.get("t", ""))[:60],
                   "x0": float(p["x0"]), "x1": float(p["x1"]),
                   "cor": [int(c) for c in (p.get("cor") or [0, 0, 0])[:3]]}
                  for p in (l.get("palavras") or [])[:40]]
            if ps:
                linhas.append({"y": float(l["y"]), "h": int(float(l["h"])), "palavras": ps})
        grupos = [{"y": float(g["y"]), "alt": int(float(g["alt"])), "est": str(g.get("est") or "normal")[:20],
                   "cores": [[0, 0, 0]] * max(1, int(g.get("n") or 1))}
                  for g in (est.get("grupos") or [])[:30]]
        ancora = est.get("ancora") or {}
        antigo = reg.get("info_atual") or reg.get("info") or {}
        info_novo = {
            "estrategia": antigo.get("estrategia"), "forma": antigo.get("forma"),
            "x": int(float(ancora.get("x", antigo.get("x", 0)))), "y": int(float(ancora.get("y", antigo.get("y", 0)))),
            "w": 0, "h": 0, "tam_ag": antigo.get("tam_ag", 0), "grupos": grupos,
            "y_fim": int(max([l["y"] + l["h"] for l in linhas] or [0])),
            "palavras": antigo.get("palavras", []),
            "max_px": int(float(est.get("max_px") or antigo.get("max_px") or 0)),
            "linhas_pos": linhas,
        }
        pend["card_bytes"] = card_bytes
        with _LOCK:
            if card_id in _REG:
                _REG[card_id]["info_atual"] = info_novo
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"erro": f"Erro ao guardar a edição manual: {type(e).__name__}: {str(e)[:160]}"}), 500
    return jsonify({
        "card_id": card_id,
        "preview_url": f"data:image/jpeg;base64,{base64.b64encode(card_bytes).decode()}",
        "qa": {"nota": None, "ok": True, "problemas": [], "tentativas": 1, "manual": True},
        "caixa": _caixa(info_novo),
        "palavras": info_novo["palavras"],
    })


@bp.route("/camada-titulo", methods=["POST"])
def rota_camada_titulo():
    """v79: entrega o card SEM o título (fundo limpo) e o título como camada transparente (recorte em volta da
    caixa), mais a posição de cada palavra. O editor local move/aumenta a camada no navegador, sem ir ao servidor.
    A camada é extraída da diferença entre o card atual e o fundo; sobrepor camada + fundo reproduz o card."""
    M = _m()
    data = request.get_json() or {}
    card_id = data.get("card_id", "")
    with _LOCK:
        reg = _REG.get(card_id)
    pend = M._cards_pendentes.get(card_id)
    if not reg or not pend:
        return jsonify({"erro": "Esse card saiu da memória do servidor (reinício ou muitos cards novos). Gere novamente."}), 410
    try:
        info = reg.get("info_atual") or reg.get("info") or {}
        caixa = _caixa(info)
        if not caixa:
            return jsonify({"erro": "Este card não tem a geometria do título registrada."}), 422
        base = np.asarray(Image.open(io.BytesIO(reg["base_jpg"])).convert("RGB")).astype(np.int16)
        atual = np.asarray(Image.open(io.BytesIO(pend["card_bytes"])).convert("RGB")).astype(np.int16)
        if base.shape != atual.shape:
            return jsonify({"erro": "Tamanhos diferentes entre o fundo e o card."}), 422
        x0, y0 = max(0, caixa["x"] - 90), max(0, caixa["y"] - 70)
        x1 = min(base.shape[1], caixa["x"] + caixa["w"] + 90)
        y1 = min(base.shape[0], caixa["y"] + caixa["h"] + 90)
        B = base[y0:y1, x0:x1]
        F = atual[y0:y1, x0:x1]
        D = np.abs(F - B).max(axis=2).astype(np.float32)
        alfa = np.clip((D - 6.0) / 26.0, 0.0, 1.0)            # ignora o ruído de JPEG (<6)
        cor = np.clip(B + (F - B) / np.maximum(alfa, 1e-3)[..., None], 0, 255)
        rgba = np.dstack([cor, alfa * 255.0]).astype(np.uint8)
        buf_png = io.BytesIO()
        Image.fromarray(rgba, "RGBA").save(buf_png, format="PNG")
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"erro": f"Erro ao preparar o editor do título: {type(e).__name__}: {str(e)[:160]}"}), 500
    return jsonify({
        "card_id": card_id,
        "base_url": "data:image/jpeg;base64," + base64.b64encode(reg["base_jpg"]).decode(),
        "camada_url": "data:image/png;base64," + base64.b64encode(buf_png.getvalue()).decode(),
        "origem": {"x": int(x0), "y": int(y0), "w": int(x1 - x0), "h": int(y1 - y0)},
        "caixa": caixa,
        "ancora": {"x": int(info.get("x", caixa["x"])), "y": int(info.get("y", caixa["y"]))},
        "palavras_pos": _palavras_pos(info),
        "linhas": _linhas_pub(info),
        "grupos": [{"y": g["y"], "alt": g["alt"], "est": g.get("est"), "n": len(g.get("cores") or [])}
                   for g in (info.get("grupos") or [])],
        "max_px": int(info.get("max_px") or 0),
    })
