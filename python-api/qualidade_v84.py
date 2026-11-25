"""
python-api/qualidade_v84.py  —  v84  —  revisão automática mais exigente e mais honesta (ADITIVO)

O portão do v76 media só a legibilidade do título (contraste, fundo detalhado, rosto, zona segura) e a nota
partia de 100 e só descontava: um título pequeno, sem destaque, sobre uma foto mal integrada ainda tirava 100.
Este módulo ACRESCENTA, sem tirar nada do v76/v83:

  1) TAMANHO e DESTAQUE do título (fonte principal pequena demais; título sem nenhuma palavra em evidência)
     e contraste por PALAVRA (a cor real de cada palavra contra o fundo logo atrás dela).
     Quando reprova, a nova tentativa já corrige: aumenta a fonte (escala_fonte) e põe uma palavra-chave em
     evidência (palavras_estilo), mantendo a estratégia e a forma que já estavam no card.
  2) NOTA HONESTA: critérios separados (legibilidade, tamanho, destaque, foto e cenário). A nota passa a ser o
     MENOR critério medido (não a média) e o que não foi medido aparece como "não avaliado".
  3) REVISÃO DA FOTO/CENÁRIO por visão (Gemini): cor da roupa/pele, coerência com um post profissional,
     integração do recorte e espaço livre para o título. Sem chave, erro ou resposta inválida: não mede
     (nunca bloqueia, nunca derruba a geração).

Tudo é chamado de dentro de qualidade_card.py / estilos_card.py em try/except: se este módulo falhar ao
carregar, a plataforma segue exatamente como no v83.
"""
import base64
import io
import json

import numpy as np
from PIL import Image

W, H = 1080, 1350
NOTA_OK = 72                    # mesmo corte do qualidade_card.py

# ── título ─────────────────────────────────────────────────────────────────────
TAM_MIN_TITULO = 66             # px da fonte principal (tam_ag) abaixo do qual o título é "pequeno para o feed"
TAM_ALVO_TITULO = 72            # tamanho que a nova tentativa procura
ALT_MIN_SUB = 44                # altura de linha (medida "Ag") mínima de uma linha secundária
HERO_ESCALA = 1.25              # quanto a palavra-chave cresce quando o título não tem destaque
RAZAO_MIN_PEQUENA = 3.2         # contraste WCAG mínimo (palavra em linha pequena)
RAZAO_MIN_GRANDE = 2.4          # contraste WCAG mínimo (palavra em linha grande)
FRAC_RUIM_PALAVRA = 0.35        # fração do fundo atrás da palavra abaixo do mínimo que reprova a palavra
ESCALA_MAX = 1.6                # mesmo teto do ajuste manual

# ── foto e cenário ─────────────────────────────────────────────────────────────
MAX_REFAZER_FOTO = 2            # quantas vezes refazer cenário/pose se a foto reprovar (limitado pelo orçamento de tempo)
ORCAMENTO_FOTO_SEG = 45.0       # só começa um refazer se a geração ainda estiver abaixo disto (timeout do Render = 120s)
NOTA_FOTO_OK = 7                # cada critério precisa de 7/10 ou mais
FOTO_MODELOS = ("gemini-2.5-flash", "gemini-3.5-flash")
FOTO_TIMEOUT = 14

ORDEM_DESTAQUE = ("amarelo", "laranja", "citrico", "teal", "branco", "marinho")

_STOP = {
    "que", "com", "para", "por", "uma", "uns", "umas", "como", "mais", "mas", "dos", "das", "nos", "nas", "aos",
    "sua", "seu", "suas", "seus", "tem", "são", "sao", "foi", "ser", "vou", "vai", "ele", "ela", "isso", "esse",
    "essa", "este", "esta", "muito", "também", "tambem", "pelo", "pela", "onde", "quando", "sobre", "entre",
    "até", "depois", "antes", "sem", "ainda", "então", "porque", "pois", "cada", "todo", "toda", "todos",
    "todas", "nem", "dele", "dela", "meu", "minha", "teu", "tua", "nosso", "nossa",
}

_CRITERIOS_FOTO = ("cor_roupa_pele", "coerencia", "integracao", "profissionalismo", "espaco_texto")
_MSG_FOTO = {
    "cor_roupa_pele": "A cor da roupa ou da pele parece tingida pelo ambiente.",
    "coerencia": "O cenário e a roupa não combinam com um post profissional de psicologia.",
    "integracao": "A pessoa parece colada no cenário (borda, escala ou luz).",
    "profissionalismo": "O visual geral não parece sóbrio e profissional o bastante.",
    "espaco_texto": "A área do título está poluída (luz forte, folhas ou objetos).",
}


# ───────────────────────────── utilidades ─────────────────────────────
def _lum_rel(rgb):
    c = np.asarray(rgb, dtype=np.float32) / 255.0
    c = np.where(c <= 0.03928, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)
    return 0.2126 * c[..., 0] + 0.7152 * c[..., 1] + 0.0722 * c[..., 2]


def _razao(l1, l2):
    a = np.maximum(l1, l2)
    b = np.minimum(l1, l2)
    return (a + 0.05) / (b + 0.05)


def _paleta():
    """Mesma paleta do ajuste manual (qualidade_card.PALETA_AJUSTE)."""
    try:
        import qualidade_card as _qc
        return dict(_qc.PALETA_AJUSTE)
    except Exception:
        return {"branco": (244, 246, 248), "marinho": (2, 64, 89), "amarelo": (255, 221, 0),
                "laranja": (249, 171, 11), "teal": (4, 157, 191), "citrico": (146, 204, 29)}


# ───────────────────── 1) tamanho, destaque, contraste por palavra ─────────────────────
def _preenchimento_da_linha(grupos, y):
    """v87: cor do preenchimento ("-palavra", pílula/retângulo) se a linha em `y` pertence a um grupo de fundo simples;
    senão None. O texto dessas linhas se lê contra o preenchimento, não contra a foto que fica atrás dele."""
    try:
        alvo = None
        for g in grupos:
            if float(g["y"]) <= float(y) + 6:
                alvo = g
        if alvo is not None and str(alvo.get("est")) == "fundo" and len(alvo.get("cores") or []) == 1:
            return tuple(int(v) for v in alvo["cores"][0])
    except Exception:
        pass
    return None


def complementar(av, res, info, kw=None):
    """Recebe o resultado do portão v76/v83 (`res`) e devolve um novo dict com critérios separados.
    `av` é o AvaliadorCard (fundo, luminância); `info` é a geometria do título; `kw` são os parâmetros do render."""
    problemas = list(res.get("problemas") or [])
    grupos = info.get("grupos") or []
    detalhe = dict(res.get("detalhe") or {})
    sug = {}

    # --- legibilidade: contraste por palavra (só se o v76 ainda não acusou contraste baixo) ---
    nota_leg = float(res.get("nota") or 0)
    pior = []
    if not any("Contraste baixo" in p for p in problemas):
        try:
            lum = av.lum()
            for l in (info.get("linhas_pos") or []):
                y0 = max(0, int(l["y"]) - 4)
                y1 = min(av.h, int(l["y"] + l["h"]) + 4)
                if y1 - y0 < 8:
                    continue
                pequena = l["h"] < 68                       # ~ fonte abaixo de 56px
                lim = RAZAO_MIN_PEQUENA if pequena else RAZAO_MIN_GRANDE
                for p in l["palavras"]:
                    x0 = max(0, int(p["x0"]) - 4)
                    x1 = min(av.w, int(p["x1"]) + 4)
                    if x1 - x0 < 12:
                        continue
                    _fill = _preenchimento_da_linha(grupos, l["y"])  # v87
                    if _fill is not None:   # palavra sobre fundo preenchido: lê-se contra o preenchimento, não contra a foto
                        _lf = float(_lum_rel(np.array(_fill, dtype=np.float32)))
                        _lt = float(_lum_rel(np.array(p["cor"], dtype=np.float32)))
                        if float(_razao(np.float32(_lf), np.float32(_lt))) < RAZAO_MIN_PEQUENA:
                            pior.append((1.0, p.get("t") or p.get("k") or "?"))
                        continue
                    lc = float(_lum_rel(np.array(p["cor"], dtype=np.float32)))
                    reg = lum[y0:y1, x0:x1].reshape(-1)
                    frac = float((_razao(reg, lc) < lim).mean())
                    if frac >= FRAC_RUIM_PALAVRA:
                        pior.append((frac, p.get("t") or p.get("k") or "?"))
        except Exception as e:
            print(f"[qa84] contraste por palavra ignorado: {type(e).__name__}: {e}")
    if pior:
        pior.sort(reverse=True)
        nota_leg -= min(30.0, pior[0][0] * 100 * 0.6)
        nomes = ", ".join(f"“{t}”" for _, t in pior[:3])
        problemas.append(f"Contraste fraco em {nomes}: a cor do texto se perde no fundo atrás dele.")
    detalhe["palavras_contraste_fraco"] = [t for _, t in pior[:5]]

    # --- tamanho ---
    nota_tam = 100.0
    tam = int(info.get("tam_ag") or 0)
    alts = [int(g["alt"]) for g in grupos if g.get("alt")]
    if tam and tam < TAM_MIN_TITULO:
        nota_tam -= min(45.0, (TAM_MIN_TITULO - tam) * 2.6)
        problemas.append(f"Título pequeno para o feed: fonte principal de {tam}px num card de {W}px "
                         f"(o mínimo recomendado é {TAM_MIN_TITULO}px).")
        sug["escala"] = float(np.clip(TAM_ALVO_TITULO / float(tam), 1.08, ESCALA_MAX))
    if alts and min(alts) < ALT_MIN_SUB:
        nota_tam -= 12.0
        problemas.append(f"Há uma linha secundária pequena demais para ler no celular (menos de {ALT_MIN_SUB}px de altura).")
        sug["sub_min"] = True   # v87: o motor passa a garantir o tamanho mínimo só dessa linha (antes inflava o título todo e não resolvia)
    detalhe["tam_ag"] = tam
    detalhe["alturas_linhas"] = alts

    # --- destaque: só cor diferente NÃO conta; precisa de estilo, tamanho ou palavra em evidência ---
    nota_des = 100.0
    ests = {str(g.get("est") or "normal") for g in grupos}
    esc_pal = []
    for o in ((kw or {}).get("palavras_estilo") or {}).values():
        try:
            esc_pal.append(float((o or {}).get("escala") or 1.0))
        except Exception:
            pass
    n_pal = len(info.get("palavras") or [])
    tem_dest = (bool(ests & {"agilera_est", "fundo"})
                or (len(alts) > 1 and max(alts) >= 1.25 * min(alts))
                or any(e >= 1.15 for e in esc_pal)
                or n_pal <= 2)                                 # título de 1-2 palavras já é o próprio destaque
    if not tem_dest:
        nota_des -= 45.0
        problemas.append("Título sem destaque: todas as linhas têm o mesmo tamanho e peso, nenhuma palavra em evidência.")
        sug["destaque"] = True

    criterios = {
        "legibilidade": {"nota": int(round(max(0.0, nota_leg))),
                         "ok": bool(res.get("ok")) and nota_leg >= NOTA_OK and not pior, "medido": True},  # v90: palavra com contraste fraco reprova (antes passava com 76 e ficava só no aviso)
        "tamanho": {"nota": int(round(max(0.0, nota_tam))), "ok": nota_tam >= NOTA_OK, "medido": True},
        "destaque": {"nota": int(round(max(0.0, nota_des))), "ok": nota_des >= NOTA_OK, "medido": True},
    }
    out = dict(res)
    out["nota"] = int(min(c["nota"] for c in criterios.values()))
    out["ok"] = all(c["ok"] for c in criterios.values())
    out["problemas"] = problemas
    out["detalhe"] = detalhe
    out["criterios"] = criterios
    out["sugestoes"] = sug
    # só tamanho/destaque falharam (nada de contraste/rosto/zona segura): dá para corrigir sem trocar de estratégia
    out["so_forma"] = bool(sug) and not (res.get("problemas") or pior)
    return out


def palavra_destaque(base, info):
    """Escolhe a palavra-chave (a última com 4+ letras que não seja ligação) e uma cor da paleta que se
    destaque do fundo real atrás dela. Devolve {chave: {"cor": rgb, "escala": HERO_ESCALA}} ou None."""
    try:
        pal = info.get("palavras") or []
        cont = [p for p in pal if len(p.get("texto", "")) >= 4 and p["texto"].lower() not in _STOP]
        lista = cont or pal
        if not lista:
            return None
        alvo = lista[-1]
        arr = np.asarray(base.convert("RGB"))
        lum = _lum_rel(arr)
        caixa, cor_atual = None, None
        xs0, xs1, ys0, ys1 = [], [], [], []
        for l in (info.get("linhas_pos") or []):
            for p in l["palavras"]:
                xs0.append(int(p["x0"]))
                xs1.append(int(p["x1"]))
                ys0.append(int(l["y"]))
                ys1.append(int(l["y"] + l["h"]))
                if p["k"] == alvo["id"]:
                    cor_atual = p["cor"]
        if xs0:   # v85: o bloco inteiro, com folga (a palavra muda de lugar quando a fonte cresce)
            bw, bh = max(xs1) - min(xs0), max(ys1) - min(ys0)
            caixa = (min(xs0), min(ys0) - int(bh * 0.35), max(xs1) + int(bw * 0.15), max(ys1) + int(bh * 0.55))
        melhor = None
        for nome, cor in _paleta().items():
            if cor_atual is not None and float(np.linalg.norm(
                    np.array(cor, dtype=np.float32) - np.array(cor_atual, dtype=np.float32))) < 90:
                continue                                       # igual à cor do texto: não destaca
            fr = 0.5
            if caixa:
                x0, y0 = max(0, caixa[0] - 6), max(0, caixa[1] - 4)
                x1, y1 = min(arr.shape[1], caixa[2] + 6), min(arr.shape[0], caixa[3] + 4)
                reg = lum[y0:y1, x0:x1].reshape(-1)
                if reg.size > 50:
                    lc = float(_lum_rel(np.array(cor, dtype=np.float32)))
                    fr = float((_razao(reg, lc) < RAZAO_MIN_PEQUENA).mean())
            ordem = ORDEM_DESTAQUE.index(nome) if nome in ORDEM_DESTAQUE else 99
            chave = (round(fr, 2), ordem)
            if melhor is None or chave < melhor[0]:
                melhor = (chave, cor)
        if melhor is None:
            return None
        print(f"[qa84] palavra em evidência: “{alvo['texto']}” cor={tuple(melhor[1])} fundo_ruim={melhor[0][0]}")
        return {alvo["id"]: {"cor": tuple(int(v) for v in melhor[1]), "escala": HERO_ESCALA}}
    except Exception as e:
        print(f"[qa84] palavra em evidência ignorada: {type(e).__name__}: {e}")
        return None


def proxima_tentativa(base, kw_usado, info, rel, sd_atual, sd_novo):
    """Parâmetros da próxima tentativa do título. Se só tamanho/destaque falharam, corrige ESSES pontos mantendo a
    seed, a estratégia e a forma; senão, segue como no v76 (outra seed, mesmos parâmetros). Retorna (kw, seed)."""
    kw2 = dict(kw_usado)
    sug = rel.get("sugestoes") or {}
    mudou = False
    if sug.get("escala"):
        atual = float(kw2.get("escala_fonte") or 1.0)
        nova = float(min(ESCALA_MAX, atual * float(sug["escala"])))
        if nova > atual + 0.01:
            kw2["escala_fonte"] = nova
            mudou = True
    if sug.get("sub_min"):  # v87: piso da linha secundária (sobe a cada tentativa se ainda ficar abaixo do mínimo)
        _cur = float(kw2.get("altura_min_sub") or 0)
        _novo = float(ALT_MIN_SUB + 4) if _cur <= 0 else min(72.0, _cur * 1.12)
        if _novo > _cur + 0.5:
            kw2["altura_min_sub"] = int(round(_novo))
            mudou = True
    if sug.get("destaque") and info:
        pe = palavra_destaque(base, info)
        if pe:
            mapa = dict(kw2.get("palavras_estilo") or {})
            mapa.update(pe)
            kw2["palavras_estilo"] = mapa
            mudou = True
    sd = sd_novo
    if mudou and rel.get("so_forma") and info:
        kw2["estrategia_fixa"] = info.get("estrategia")
        kw2["forma_fixa"] = info.get("forma")
        sd = sd_atual
    if mudou:
        print(f"[qa84] próxima tentativa: escala_fonte={kw2.get('escala_fonte')} "
              f"destaque={'sim' if kw2.get('palavras_estilo') else 'não'} seed_mantida={sd == sd_atual}")
    return kw2, sd


# ───────────────────── 1b) correções que o portão faz sozinho (v85) ─────────────────────
LUGARES_CLINICOS = ("consultorio", "biblioteca", "galeria", "patio")

_PEDIDO_FOTO = {
    "coerencia": "The place must clearly be a sober professional environment for a psychologist (consulting room, "
                 "study, library, gallery or calm clinic courtyard), never a wild landscape.",
    "espaco_texto": "The LEFT 45% of the frame is plain and calm (wall, soft blur or empty space) with no bright "
                    "light shafts, foliage or objects.",
    "cor_roupa_pele": "Neutral, color-balanced light with no strong green, blue or orange color cast anywhere in the "
                      "scene (warm wood, cream and soft white tones), so a white shirt and skin keep their natural color.",
    "integracao": "Soft, even light from the front-left at standing eye level, a clear floor plane and shallow depth "
                  "of field, so a standing person fits the scene naturally.",
    "profissionalismo": "Sober, calm, premium and credible psychology-office look; nothing dramatic, spooky, kitschy "
                        "or like a tourist landscape.",
}


def lugar_clinico(n, evitar=None):
    """Lugar de aparência clínica/profissional para refazer o cenário (rodízio, evitando o último usado)."""
    lista = [k for k in LUGARES_CLINICOS if k != evitar] or list(LUGARES_CLINICOS)
    return lista[(int(n) - 1) % len(lista)]


def instrucoes_da_revisao(foto):
    """Transforma o que a revisão da foto reprovou em instruções para o próximo cenário."""
    partes = [_PEDIDO_FOTO["coerencia"], _PEDIDO_FOTO["espaco_texto"]]
    itens = (foto or {}).get("criterios") or {}
    for k, v in itens.items():
        try:
            if float(v) < NOTA_FOTO_OK and k in _PEDIDO_FOTO and _PEDIDO_FOTO[k] not in partes:
                partes.append(_PEDIDO_FOTO[k])
        except (TypeError, ValueError):
            pass
    notas = " ".join(((foto or {}).get("problemas") or [])[:3]).strip()
    if notas:
        partes.append(f"Reviewer notes about the previous image, fix them: {notas}")
    return " ".join(partes)


def precisa_escurecer(rel):
    """True se o que reprovou o título foi o fundo (contraste ou detalhe), o caso em que só trocar de estilo não basta."""
    return any(("Contraste" in p) or ("Fundo muito detalhado" in p) for p in (rel.get("problemas") or []))


def _bloco(info, folga=0.0):
    """Caixa (x0, y0, x1, y1) do bloco do título; `folga` a amplia (o texto muda de lugar quando a fonte cresce)."""
    lns = info.get("linhas_pos") or []
    if lns:
        x0 = min(p["x0"] for l in lns for p in l["palavras"])
        x1 = max(p["x1"] for l in lns for p in l["palavras"])
        y0 = min(l["y"] for l in lns)
        y1 = max(l["y"] + l["h"] for l in lns)
    else:
        x0, y0 = info.get("x", 0), info.get("y", 0)
        x1, y1 = x0 + info.get("w", 0), info.get("y_fim", y0)
    bw, bh = x1 - x0, y1 - y0
    return x0, y0 - folga * bh * 0.5, x1 + folga * bw, y1 + folga * bh


def escurecer_atras(base, info, forca=0.30, folga=0.0):
    """Correção de último recurso: escurece de forma suave (sem borda visível) a área do título, mais nas partes
    claras, como um ajuste de luz da cena. Devolve uma nova imagem; em qualquer falha devolve a base intacta."""
    try:
        x0, y0, x1, y1 = _bloco(info, folga)
        arr = np.asarray(base.convert("RGB"), dtype=np.float32)
        h, w = arr.shape[:2]
        yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
        dx = np.maximum(np.maximum(x0 - 20 - xx, xx - (x1 + 20)), 0)
        dy = np.maximum(np.maximum(y0 - 20 - yy, yy - (y1 + 20)), 0)
        m = np.clip(1.0 - np.sqrt(dx * dx + dy * dy) / 140.0, 0, 1)
        m = m * m * (3 - 2 * m)                                   # transição suave
        lum01 = np.clip(arr.mean(axis=2) / 255.0, 0, 1)
        fator = 1.0 - float(forca) * m * (0.55 + 0.45 * lum01)    # mexe mais onde está claro
        out = np.clip(arr * fator[..., None], 0, 255).astype(np.uint8)
        print(f"[qa84] escurecendo atras do titulo (forca {forca:.2f})")
        return Image.fromarray(out)
    except Exception as e:
        print(f"[qa84] escurecer ignorado: {type(e).__name__}: {e}")
        return base


def corrigir_contraste(base, info, kw, permitir_escurecer=True):
    """Contraste reprovado: em vez de só sortear outro estilo, MEDE o fundo atrás do bloco do título e escolhe a cor
    do texto que mais contrasta (branco, marinho ou amarelo). Se nenhuma resolve, escurece suave a área e escolhe
    de novo. Cores por palavra que não contrastam (ou iguais ao texto) perdem a cor e ficam só com o tamanho.
    Devolve (kw_novo, base_nova); em qualquer falha devolve (kw, base)."""
    try:
        kw2 = dict(kw)
        x0, y0, x1, y1 = _bloco(info, 0.30)
        W_, H_ = base.size
        x0, y0 = max(0, int(x0) - 6), max(0, int(y0) - 6)
        x1, y1 = min(W_, int(x1) + 6), min(H_, int(y1) + 6)
        if x1 - x0 < 40 or y1 - y0 < 40:
            return kw, base
        pal = _paleta()
        cands = [(n, pal[n]) for n in ("branco", "amarelo", "marinho") if n in pal]   # ordem = preferência no empate

        def _lum_regiao(img):
            return _lum_rel(np.asarray(img.convert("RGB")))[y0:y1, x0:x1].reshape(-1)

        def _melhor(img):
            lum = _lum_regiao(img)
            res = []
            for i, (n, c) in enumerate(cands):
                lc = float(_lum_rel(np.array(c, dtype=np.float32)))
                res.append((round(float((_razao(lum, lc) < RAZAO_MIN_PEQUENA).mean()), 2), i, n, c))
            return min(res)

        fr, _, nome, cor = _melhor(base)
        base_i = base
        if fr > 0.15 and permitir_escurecer:
            for forca in (0.35, 0.50):
                b2 = escurecer_atras(base, info, forca, 0.30)
                f2 = _melhor(b2)
                if f2[0] < fr:
                    fr, _, nome, cor = f2
                    base_i = b2
                if fr <= 0.15:
                    break
        kw2["cor_forcada"] = tuple(int(v) for v in cor)
        lum_i = _lum_regiao(base_i)
        pe = {}
        for k, o in (kw2.get("palavras_estilo") or {}).items():
            o2 = dict(o or {})
            c = o2.get("cor")
            if c is not None:
                lc = float(_lum_rel(np.array(c, dtype=np.float32)))
                longe = float(np.linalg.norm(np.array(c, dtype=np.float32) - np.array(cor, dtype=np.float32))) >= 90
                if (not longe) or float((_razao(lum_i, lc) < RAZAO_MIN_PEQUENA).mean()) > FRAC_RUIM_PALAVRA:
                    o2.pop("cor", None)
            pe[k] = o2
        if pe:
            kw2["palavras_estilo"] = pe
        try:  # v87: cor POR LINHA — a cor única do bloco pode falhar numa linha que cai sobre outra parte da foto
            _lum_full = _lum_rel(np.asarray(base_i.convert("RGB")))
            _pe2 = dict(kw2.get("palavras_estilo") or {})
            _n_lin = 0
            for _l in (info.get("linhas_pos") or []):
                if _preenchimento_da_linha(info.get("grupos") or [], _l["y"]) is not None:
                    continue   # linha sobre fundo preenchido: o contraste é com o próprio preenchimento
                _ya, _yb = max(0, int(_l["y"]) - 4), min(H_, int(_l["y"] + _l["h"]) + 4)
                _pl = _l.get("palavras") or []
                if _yb - _ya < 8 or not _pl:
                    continue
                _xa = max(0, int(min(p["x0"] for p in _pl)) - 6)
                _xb = min(W_, int(max(p["x1"] for p in _pl)) + 6)
                if _xb - _xa < 20:
                    continue
                _reg = _lum_full[_ya:_yb, _xa:_xb].reshape(-1)

                def _fr(_c, _reg=_reg):
                    return float((_razao(_reg, float(_lum_rel(np.array(_c, dtype=np.float32)))) < RAZAO_MIN_PEQUENA).mean())
                _atual = _fr(cor)
                if _atual <= FRAC_RUIM_PALAVRA:
                    continue
                _melhor_l = min((_fr(_c), _i, _n, _c) for _i, (_n, _c) in enumerate(cands))
                if _melhor_l[0] + 0.05 < _atual:
                    for _p in _pl:
                        _o = dict(_pe2.get(_p["k"]) or {})
                        _o["cor"] = tuple(int(v) for v in _melhor_l[3])
                        _pe2[_p["k"]] = _o
                    _n_lin += 1
            if _n_lin:
                kw2["palavras_estilo"] = _pe2
                print(f"[qa84] contraste por linha: {_n_lin} linha(s) com cor propria")
        except Exception as _e87:
            print(f"[qa84] cor por linha ignorada: {type(_e87).__name__}: {_e87}")
        try:  # v90: palavras em DESTAQUE (cor diferente do texto principal) são medidas pela cor REAL que têm (o laranja de "aparecer" sobre um raio de sol)
            _lum90 = _lum_rel(np.asarray(base_i.convert("RGB")))
            _lns90 = [l for l in (info.get("linhas_pos") or [])
                      if _preenchimento_da_linha(info.get("grupos") or [], l["y"]) is None]
            _cores90 = [tuple(int(v) for v in p["cor"]) for l in _lns90 for p in (l.get("palavras") or [])]
            if _cores90:
                _principal90 = max(set(_cores90), key=_cores90.count)
                _pe90 = dict(kw2.get("palavras_estilo") or {})
                _n90 = 0
                for _l in _lns90:
                    _ya, _yb = max(0, int(_l["y"]) - 4), min(H_, int(_l["y"] + _l["h"]) + 4)
                    if _yb - _ya < 8:
                        continue
                    for _p in (_l.get("palavras") or []):
                        _c_real = tuple(int(v) for v in _p["cor"])
                        if _c_real == _principal90:
                            continue
                        _xa, _xb = max(0, int(_p["x0"]) - 4), min(W_, int(_p["x1"]) + 4)
                        if _xb - _xa < 12:
                            continue
                        _rg = _lum90[_ya:_yb, _xa:_xb].reshape(-1)
                        _lc0 = float(_lum_rel(np.array(_c_real, dtype=np.float32)))
                        _atual90 = float((_razao(_rg, _lc0) < RAZAO_MIN_PEQUENA).mean())
                        if _atual90 <= FRAC_RUIM_PALAVRA:
                            continue
                        _opc = []
                        for _i, _nm in enumerate(ORDEM_DESTAQUE):
                            if _nm in pal:
                                _lcn = float(_lum_rel(np.array(pal[_nm], dtype=np.float32)))
                                _opc.append((round(float((_razao(_rg, _lcn) < RAZAO_MIN_PEQUENA).mean()), 2), _i, _nm, pal[_nm]))
                        if not _opc:
                            continue
                        _bom = [o for o in _opc if o[0] <= 0.25]
                        _esc = min(_bom, key=lambda o: o[1]) if _bom else min(_opc)   # prefere a cor de destaque que passa; senão a que mais contrasta
                        if _esc[0] + 0.05 < _atual90:
                            _o = dict(_pe90.get(_p["k"]) or {})
                            _o["cor"] = tuple(int(v) for v in _esc[3])
                            _pe90[_p["k"]] = _o
                            _n90 += 1
                if _n90:
                    kw2["palavras_estilo"] = _pe90
                    print(f"[qa84] contraste do destaque: {_n90} palavra(s) com cor propria")
        except Exception as _e90:
            print(f"[qa84] cor do destaque ignorada: {type(_e90).__name__}: {_e90}")
        print(f"[qa84] contraste: texto {nome} (fundo ruim {fr:.2f}), "
              f"{'com' if base_i is not base else 'sem'} escurecimento")
        return kw2, base_i
    except Exception as e:
        print(f"[qa84] corrigir contraste ignorado: {type(e).__name__}: {e}")
        return kw, base


# ───────────────────── 2) nota honesta (mescla com a revisão da foto) ─────────────────────
def mesclar_foto(rel, foto):
    """Acrescenta o critério "foto e cenário" ao relatório. `foto` = resultado de revisar_foto (ou None = não medido).
    A nota final é o MENOR critério medido; sem a foto, o relatório fica marcado como parcial."""
    rel = dict(rel)
    crit = dict(rel.get("criterios") or {})
    if not crit:                                 # sem geometria do título: não há o que mesclar
        return rel
    if foto is None:
        crit["foto"] = {"nota": None, "ok": None, "medido": False}
        rel["parcial"] = True
    else:
        crit["foto"] = {"nota": int(foto["nota"]), "ok": bool(foto["ok"]), "medido": True,
                        "itens": dict(foto.get("criterios") or {})}
        rel["parcial"] = False
        rel["problemas"] = list(rel.get("problemas") or []) + \
            [f"Foto e cenário: {p}" for p in (foto.get("problemas") or [])]
        if rel.get("nota") is not None:
            rel["nota"] = int(min(int(rel["nota"]), int(foto["nota"])))
        rel["ok"] = bool(rel.get("ok")) and bool(foto["ok"])
    rel["criterios"] = crit
    return rel


# ───────────────────── 3) revisão da foto e do cenário por visão ─────────────────────
def _json_de(txt):
    txt = (txt or "").replace("```json", "").replace("```", "").strip()
    i, j = txt.find("{"), txt.rfind("}")
    if i >= 0 and j > i:
        txt = txt[i:j + 1]
    return json.loads(txt)


def revisar_foto(M, img, tema="", estilo="", _tentativa=1):
    """Nota a foto/cenário SEM o título (pessoa recortada + cenário). Retorna
    {"nota": 0-100 (menor critério x10), "ok": bool, "problemas": [...], "criterios": {nome: 0-10}} ou None."""
    try:
        import requests
        chave = getattr(M, "GEMINI_API_KEY", None)
        if not chave:
            return None
        limpar = getattr(M, "_texto_tema_limpo", None)
        tema_limpo = (limpar(tema) if callable(limpar) else str(tema or "")).replace("\n", " ").strip()[:160]
        buf = io.BytesIO()
        img.convert("RGB").resize((540, 675), Image.Resampling.LANCZOS).save(buf, format="JPEG", quality=85)
        pergunta = (
            "You are a strict art director reviewing the BACKGROUND IMAGE of an Instagram post (4:5) for the "
            "Brazilian clinic of a licensed psychologist. The image shows a real man (the psychologist, wearing "
            "a business-casual dress shirt) composited into a generated scene; a large headline will be added "
            "later on the LEFT side. Score each criterion from 0 to 10 (10 = flawless, 7 = acceptable, below 7 = "
            "must be redone). Be strict, do not be generous.\n"
            "1. cor_roupa_pele: the shirt, skin, face and hands keep natural colors. Score low if the shirt or "
            "skin looks tinted by the environment (greenish, bluish, muddy), stained, patchy or discolored.\n"
            "2. coerencia: the place makes sense for this person and for a professional psychology post. A man "
            "in a dress shirt in a rough forest trail, jungle, beach or ruins looks incoherent; score low when "
            "clothing, pose and place do not belong together or the place looks like a random stock landscape.\n"
            "3. integracao: he looks physically present in the scene (scale, light direction, soft clean edges "
            "without halo or fringe, feet grounded) instead of pasted on top. If he leans on or sits on a chair or "
            "furniture that came with the cut-out and does not belong to the scene, score low.\n"
            "4. profissionalismo: overall credible, calm, welcoming and sober for a psychologist's feed; not "
            "dramatic, kitschy, spooky or advertising-like.\n"
            "5. espaco_texto: the left ~45% of the frame is calm and uncluttered (no bright light rays, strong "
            "highlights, busy foliage or objects) so a large headline stays readable.\n"
            f'Post theme (context only): "{tema_limpo}".\n'
            'Answer ONLY with JSON: {"cor_roupa_pele":n,"coerencia":n,"integracao":n,"profissionalismo":n,'
            '"espaco_texto":n,"problemas":["..."]} where "problemas" has up to 3 short sentences in Brazilian '
            "Portuguese naming the worst defects (empty list if there are none)."
        )
        payload = {
            "contents": [{"parts": [
                {"inline_data": {"mime_type": "image/jpeg", "data": base64.b64encode(buf.getvalue()).decode()}},
                {"text": pergunta},
            ]}],
            "generationConfig": {"responseMimeType": "application/json", "temperature": 0},
        }
        for modelo in FOTO_MODELOS:
            try:
                r = requests.post(
                    f"https://generativelanguage.googleapis.com/v1beta/models/{modelo}:generateContent?key={chave}",
                    json=payload, timeout=FOTO_TIMEOUT)
                if r.status_code >= 400:
                    print(f"[qa-foto] {modelo} HTTP {r.status_code}")
                    continue
                partes = r.json()["candidates"][0]["content"]["parts"]
                txt = "".join(p.get("text", "") for p in partes if not p.get("thought"))
                d = _json_de(txt)
                notas = {}
                for k in _CRITERIOS_FOTO:
                    try:
                        notas[k] = max(0.0, min(10.0, float(d.get(k))))
                    except (TypeError, ValueError):
                        pass
                if len(notas) < 3:
                    print(f"[qa-foto] {modelo}: resposta incompleta")
                    continue
                menor = min(notas.values())
                ok = menor >= NOTA_FOTO_OK
                problemas = [str(p).strip() for p in (d.get("problemas") or []) if str(p).strip()][:3]
                if not ok and not problemas:
                    problemas = [_MSG_FOTO[k] for k, v in notas.items() if v < NOTA_FOTO_OK][:3]
                out = {"nota": int(round(menor * 10)), "ok": ok, "problemas": problemas,
                       "criterios": {k: int(round(v)) for k, v in notas.items()}, "modelo": modelo}
                print(f"[qa-foto] {modelo}: nota={out['nota']} ok={ok} criterios={out['criterios']}")
                return out
            except Exception as e:
                print(f"[qa-foto] {modelo} falhou: {type(e).__name__}: {e}")
        if _tentativa < 2:  # v87: sem resposta de nenhum modelo (timeout/limite) -> uma segunda tentativa antes de deixar "não avaliada"
            print("[qa-foto] sem resposta; tentando de novo")
            import time as _tm87
            _tm87.sleep(1.5)
            return revisar_foto(M, img, tema, estilo, _tentativa=2)
        return None
    except Exception as e:
        print(f"[qa-foto] revisão ignorada: {type(e).__name__}: {e}")
        return None


# ───────────────────── 4) correção local da zona do título (v87) ─────────────────────
def acalmar_zona_titulo(img, lado_x="dir", x_esq=None, x_dir=None):
    """v87: a revisão reprovou o espaço do título (luz forte, sombra dura, estante/objetos). Em vez de gastar outra geração de IA,
    acalma só a zona oposta à pessoa: desfoque de profundidade de campo, menos contraste local e luzes estouradas contidas,
    com transição suave (sem borda, sem retângulo). A pessoa não é tocada. Em qualquer falha devolve a mesma imagem."""
    try:
        import cv2
        arr = np.asarray(img.convert("RGB"))
        h, w = arr.shape[:2]
        if lado_x == "esq":
            xa, xb = int(min(w, (x_dir if x_dir is not None else int(w * 0.5)) + 24)), w
        else:
            xa, xb = 0, int(max(0, (x_esq if x_esq is not None else int(w * 0.5)) - 24))
        if xb - xa < 120:
            return img
        reg = arr[:, xa:xb].astype(np.float32)
        lw = xb - xa
        mx = np.ones(lw, np.float32)
        fe = min(110, lw // 2)
        if lado_x == "esq":
            mx[:fe] = np.linspace(0.0, 1.0, fe, dtype=np.float32)      # lado voltado para a pessoa: transição suave
        else:
            mx[lw - fe:] = np.linspace(1.0, 0.0, fe, dtype=np.float32)
        my = np.ones(h, np.float32)
        y_fade = int(h * 0.80)
        my[y_fade:] = np.linspace(1.0, 0.0, h - y_fade, dtype=np.float32)   # o chão perto dos pés fica como está
        m = (my[:, None] * mx[None, :])[..., None]
        borrada = cv2.GaussianBlur(reg, (0, 0), 9)
        media = borrada.reshape(-1, 3).mean(axis=0)
        calma = media + (borrada - media) * 0.55                    # menos contraste local (sombra dura, faixa de luz)
        lum = calma.mean(axis=2, keepdims=True)
        exc = np.clip(lum - (float(media.mean()) + 28.0), 0, None)
        calma = calma - exc * 0.6                                   # contenção de luzes estouradas
        calma = calma + np.random.RandomState(87).normal(0, 2.0, (h, lw, 1)).astype(np.float32)   # grão igual ao do resto
        out = arr.copy()
        out[:, xa:xb] = np.clip(reg * (1 - m) + calma * m, 0, 255).astype(np.uint8)
        print(f"[qa-foto] zona do titulo acalmada (x {xa}-{xb})")
        return Image.fromarray(out)
    except Exception as e:
        print(f"[qa-foto] acalmar zona do titulo ignorado: {type(e).__name__}: {e}")
        return img


def corrigir_foto_local(M, img, foto, tema, estilo, lado_x, x_esq, x_dir, reintegrar=None, estado=None):
    """v87/v90: o que a revisão reprovou e dá para corrigir SEM gerar outro cenário é corrigido aqui:
      - integração ("pessoa colada"): refaz a integração com luz, contorno e sombras reforçados (`reintegrar(reforço)`);
      - espaço do título (luz forte, objetos): acalma a zona do título.
    Depois revisa de novo (1 chamada) e só mantém a correção se a nota não piorar. Retorna (imagem, relatório_da_foto, corrigiu).
    Se a reintegração foi mantida, a nova geometria fica em estado["geom"] = (img, corpo, cabeça, x_esq, lado, x_dir)."""
    try:
        if not foto or foto.get("ok"):
            return img, foto, False
        crit = foto.get("criterios") or {}

        def _ruim(k):
            try:
                return crit.get(k) is not None and float(crit[k]) < NOTA_FOTO_OK
            except (TypeError, ValueError):
                return False

        novo, geom, feito = img, None, []
        if reintegrar is not None and _ruim("integracao"):
            try:
                import gc
                gc.collect()
                geom = reintegrar(1.8)
                novo = geom[0]
                lado_x, x_esq, x_dir = geom[4], geom[3], geom[5]
                feito.append("integracao")
            except Exception as e:
                geom, novo = None, img
                print(f"[qa-foto] reintegracao reforcada ignorada: {type(e).__name__}: {e}")
        if _ruim("espaco_texto"):
            calmo = acalmar_zona_titulo(novo, lado_x, x_esq, x_dir)
            if calmo is not novo:
                novo = calmo
                feito.append("zona_titulo")
        if not feito:
            return img, foto, False
        nova = revisar_foto(M, novo, tema, estilo)
        if nova is not None and int(nova["nota"]) >= int(foto["nota"]):
            print(f"[qa-foto] correcao local mantida ({'+'.join(feito)}): nota {foto['nota']} -> {nova['nota']}")
            if estado is not None and geom is not None:
                estado["geom"] = geom
            return novo, nova, True
        print("[qa-foto] correcao local descartada (nao melhorou ou sem nova revisao)")
        return img, foto, False
    except Exception as e:
        print(f"[qa-foto] correcao local ignorada: {type(e).__name__}: {e}")
        return img, foto, False


def suavizar_luz_dramatica(img):
    """v90: cenário com luz dramática (raios de sol, janela estourada, sombra dura) não combina com a luz suave de estúdio do
    recorte: é a causa nº 1 de "pessoa colada" e de texto ilegível sobre um raio de luz. Mede o drama (distância entre as luzes
    altas e o meio-tom) e, só se houver, comprime as luzes altas, reduz o contraste local e dessatura levemente.
    Cenário calmo: devolve a mesma imagem. Em qualquer falha também."""
    try:
        import cv2
        a = np.asarray(img.convert("RGB"), dtype=np.float32)
        lum = a.mean(axis=2) / 255.0
        p60, p98 = np.percentile(lum[::4, ::4], [60, 98])
        drama = float(np.clip((float(p98) - float(p60) - 0.22) / 0.28, 0.0, 1.0))
        if drama < 0.12:
            return img
        joelho = float(p60) + 0.06
        exc = np.clip(lum - joelho, 0.0, None)
        ganho = ((lum - exc * (0.55 * drama)) + 1e-3) / (lum + 1e-3)
        a = a * ganho[..., None]
        k = 0.30 * drama
        a = a * (1.0 - k) + cv2.GaussianBlur(a, (0, 0), 18) * k
        cz = a.mean(axis=2, keepdims=True)
        d = 0.12 * drama
        a = a * (1.0 - d) + cz * d
        print(f"[cenario] luz dramatica (drama {drama:.2f}): suavizada")
        return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))
    except Exception as e:
        print(f"[cenario] suavizar luz dramatica ignorado: {type(e).__name__}: {e}")
        return img
