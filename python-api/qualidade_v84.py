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
        sug.setdefault("escala", 1.2)
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
                         "ok": bool(res.get("ok")) and nota_leg >= NOTA_OK, "medido": True},
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


def escurecer_atras(base, info, forca=0.30):
    """Correção de último recurso: escurece de forma suave (sem borda visível) a área do título, mais nas partes
    claras, como um ajuste de luz da cena. Devolve uma nova imagem; em qualquer falha devolve a base intacta."""
    try:
        lns = info.get("linhas_pos") or []
        if lns:
            x0 = min(p["x0"] for l in lns for p in l["palavras"])
            x1 = max(p["x1"] for l in lns for p in l["palavras"])
            y0 = min(l["y"] for l in lns)
            y1 = max(l["y"] + l["h"] for l in lns)
        else:
            x0, y0 = info.get("x", 0), info.get("y", 0)
            x1, y1 = x0 + info.get("w", 0), info.get("y_fim", y0)
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


def revisar_foto(M, img, tema="", estilo=""):
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
        return None
    except Exception as e:
        print(f"[qa-foto] revisão ignorada: {type(e).__name__}: {e}")
        return None
