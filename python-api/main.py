"""
python-api/main.py  —  AlvoreSer Instagram Posts  —  v15

CORREÇÕES v15
=============
- Overlay: mapa esquerda/direita corrigido (overlay vai para o MESMO lado do texto)
- Segmento 'normal' em overlay escuro usa BRANCO ou cor clara garantida
- Quebra de linha: segmentos consecutivos na mesma linha quando cabem (flow inline)
- _detectar_lado_conteudo: invertido para retornar lado do TEXTO, não do rosto

PIPELINE
========
Imagem: Cloudinary → rembg (Ronilson) ou color grade (editorial) → fallback gradiente
Overlay: cor da paleta por contraste com foto, nunca igual ao texto, direção por seed
Tipografia: (sem) AGILERA cor-destaque | * AGILERA est. | : MALGUN | - fundo preenchido
Layout: texto fixo no terço inferior (62–93%), layout 3 no topo
"""

import os, io, uuid, random, json, math, base64
import numpy as np
import requests, cloudinary, cloudinary.uploader, cloudinary.api
from datetime import datetime
from flask import Flask, request, jsonify
from flask_cors import CORS
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance, ImageChops
from google.oauth2 import service_account
from googleapiclient.discovery import build

_rembg_remove = None
def get_rembg():
    global _rembg_remove
    if _rembg_remove is None:
        from rembg import remove as _r
        _rembg_remove = _r
    return _rembg_remove

app = Flask(__name__, static_folder="../dist", static_url_path="/")

ALLOWED_ORIGINS = [
    "http://localhost:5173", "http://localhost:3000", "http://localhost:5000",
    "https://rn-posts.onrender.com", "https://alvoreser-python-api.onrender.com",
]
CORS(app, origins=ALLOWED_ORIGINS, supports_credentials=True)

@app.after_request
def add_cors(response):
    origin = request.headers.get("Origin")
    if origin and (origin in ALLOWED_ORIGINS or "localhost" in origin or "onrender.com" in origin):
        response.headers["Access-Control-Allow-Origin"]  = origin
    response.headers["Access-Control-Allow-Headers"] = "Content-Type,Authorization"
    response.headers["Access-Control-Allow-Methods"] = "GET,POST,OPTIONS"
    return response

def _dist_index_path():
    folder = app.static_folder
    if not folder: return None
    p = os.path.join(os.path.abspath(folder), "index.html")
    return p if os.path.isfile(p) else None

cloudinary.config(
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
    api_key   =os.getenv("CLOUDINARY_API_KEY"),
    api_secret=os.getenv("CLOUDINARY_API_SECRET"),
)

SPREADSHEET_ID       = "12FT6CQQDNLI9G7KM8wSfHevAKAuRoEi4OsPYy1aH-8A"
SCOPES               = ["https://www.googleapis.com/auth/spreadsheets"]
SERVICE_ACCOUNT_JSON = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON")
GROQ_API_KEY         = os.getenv("GROQ_API_KEY")
GEMINI_API_KEY       = os.getenv("GEMINI_API_KEY")
GROQ_URL             = "https://api.groq.com/openai/v1/chat/completions"

W, H = 1080, 1350
CLOUDINARY_POSTS   = "AlvoreSer_Posts"
CLOUDINARY_PREVIEW = "AlvoreSer_Preview"
PASTA_RONILSON     = "banco de imagens/ronilson"

# ── Paleta ────────────────────────────────────────────────────────────────────
MARINHO       = (2,   64,  89)
PETROLEO      = (27,  121, 125)
TEAL          = (4,   157, 191)
VERDE_NEUTRO  = (119, 153, 147)
BRANCO        = (244, 246, 248)
LARANJA       = (249, 171, 11)
VERDE_VIVO    = (122, 181, 0)
VERDE_CITRICO = (146, 204, 29)
AMARELO       = (255, 221, 0)
PALETA_9      = [MARINHO, PETROLEO, TEAL, VERDE_NEUTRO, BRANCO,
                 LARANJA, VERDE_VIVO, VERDE_CITRICO, AMARELO]

_LUM_COR = {
    MARINHO: 0.08, PETROLEO: 0.22, TEAL: 0.45, VERDE_NEUTRO: 0.52,
    VERDE_VIVO: 0.55, VERDE_CITRICO: 0.62, LARANJA: 0.65,
    AMARELO: 0.82, BRANCO: 0.95,
}

# ── Zona Segura ───────────────────────────────────────────────────────────────
SAFE_LEFT   = 34;  SAFE_RIGHT  = 1046
SAFE_TOP    = 60;  SAFE_BOTTOM = 1290
SAFE_W      = 1012; SAFE_H     = 1230
SAFE_MARGIN = SAFE_LEFT + 46   # 80px
SAFE_MAX_PX = SAFE_W - 92      # 920px

# ── Cores de destaque ─────────────────────────────────────────────────────────
CORES_DESTAQUE = [
    LARANJA, AMARELO, TEAL, VERDE_VIVO, VERDE_CITRICO,
    BRANCO, VERDE_NEUTRO, MARINHO, PETROLEO,
]
CORES_FUNDO_TEXTO = {
    LARANJA: MARINHO, AMARELO: MARINHO, TEAL: BRANCO,
    VERDE_VIVO: MARINHO, VERDE_CITRICO: MARINHO, BRANCO: MARINHO,
    VERDE_NEUTRO: BRANCO, PETROLEO: BRANCO, MARINHO: BRANCO,
}

def _escolher_cor_destaque(seed):
    cor = CORES_DESTAQUE[seed % 9]
    return cor, CORES_FUNDO_TEXTO.get(cor, MARINHO)

def distancia_cor(c1, c2):
    return math.sqrt(sum((a - b)**2 for a, b in zip(c1, c2)))

def _escolher_cor_overlay(cor_dominante_foto, cor_destaque_texto, seed=0):
    lum_foto = sum(cor_dominante_foto) / (3 * 255)
    dist_max = math.sqrt(255**2 * 3)

    candidatas = []
    for cor in PALETA_9:
        if cor == cor_destaque_texto:
            continue
        if cor == BRANCO:
            continue
        dist   = distancia_cor(cor_dominante_foto, cor) / dist_max
        lum_ov = _LUM_COR.get(cor, 0.5)
        if lum_foto > 0.55:
            bonus = (1.0 - lum_ov) * 0.7 + dist * 0.3
        elif lum_foto > 0.35:
            bonus = (1.0 - abs(lum_ov - 0.35) * 1.5) * 0.5 + dist * 0.5
        else:
            bonus = (1.0 - abs(lum_ov - 0.45) * 2.0) * 0.6 + dist * 0.4
        bonus = max(0.05, bonus)
        candidatas.append((bonus, cor))

    candidatas.sort(key=lambda x: -x[0])
    top3 = candidatas[:3]
    _, melhor_cor = top3[seed % len(top3)]

    print(f"[overlay_cor] lum_foto={lum_foto:.2f} top3={[c for _,c in top3]} → {melhor_cor}")
    return melhor_cor

_cards_pendentes = {}

MAPA_PASTAS = {
    "autismo":        "Banco de Imagens/Autismo",
    "ansiedade":      "Banco de Imagens/Ansiedade e Estresse",
    "estresse":       "Banco de Imagens/Ansiedade e Estresse",
    "burnout":        "Banco de Imagens/Ansiedade e Estresse",
    "depressao":      "Banco de Imagens/Depressão",
    "luto":           "Banco de Imagens/Depressão",
    "trauma":         "Banco de Imagens/Depressão",
    "borderline":     "Banco de Imagens/Borderline",
    "tdah":           "Banco de Imagens/TDAH",
    "terapia":        "Banco de Imagens/Convite e Terapia",
    "acolhimento":    "Banco de Imagens/Acolhimento",
    "familia":        "Banco de Imagens/Acolhimento",
    "relacionamento": "Banco de Imagens/Acolhimento",
    "recomeco":       "Banco de Imagens/Recomeço e Transformação",
    "transformacao":  "Banco de Imagens/Recomeço e Transformação",
}

# ── Fontes ────────────────────────────────────────────────────────────────────
ROOT_DIR    = os.path.join(os.path.dirname(__file__), "..")
_FONTS_DIRS = [
    os.path.join(os.path.dirname(__file__), "fonts"),
    os.path.join(ROOT_DIR, "src", "Brand", "fonts"),
]

def _resolve_font_path(nome):
    low = nome.lower()
    for base in _FONTS_DIRS:
        if not os.path.isdir(base): continue
        p = os.path.join(base, nome)
        if os.path.isfile(p): return p
        try:
            for f in os.listdir(base):
                if f.lower() == low: return os.path.join(base, f)
        except Exception: pass
    return None

def _font(nome, tam):
    p = _resolve_font_path(nome)
    if p:
        try: return ImageFont.truetype(p, tam)
        except Exception as e: print(f"[font] erro {p}: {e}")
    try: return ImageFont.load_default(size=tam)
    except Exception: return ImageFont.load_default()

def f_display(t): return _font("AGILERA.OTF",  t)
def f_bold(t):    return _font("MALGUNBD.TTF", t)
def f_corpo(t):   return _font("MALGUN.TTF",   t)
def f_light(t):   return _font("MALGUNSL.TTF", t)

for _fn in ["AGILERA.OTF", "MALGUN.TTF", "MALGUNBD.TTF", "MALGUNSL.TTF"]:
    _p = _resolve_font_path(_fn)
    print(f"[font] {'OK  ' if _p else 'MISS'} {_fn}" + (f" => {_p}" if _p else ""))

_RAQM_OK = False
try:
    from PIL import features as _pil_features
    _RAQM_OK = _pil_features.check("raqm")
except Exception: pass
print(f"[raqm] {'disponivel' if _RAQM_OK else 'indisponivel'}")

import tempfile as _tempfile
_AGILERA_EST_PATH = None
_LIGA_SUBST       = {}
_PUA_START        = 0xE000

def _preparar_fonte_estilizada():
    global _AGILERA_EST_PATH, _LIGA_SUBST
    if _AGILERA_EST_PATH and os.path.isfile(_AGILERA_EST_PATH):
        return _AGILERA_EST_PATH
    fonte_path = _resolve_font_path("AGILERA.OTF")
    if not fonte_path: return None
    try:
        from fonttools import ttLib
        font = ttLib.TTFont(fonte_path)
        if "GSUB" not in font: return None
        gsub = font["GSUB"].table

        aalt_subst = {}
        for feat in gsub.FeatureList.FeatureRecord:
            if feat.FeatureTag != "aalt": continue
            for idx in feat.Feature.LookupListIndex:
                lk = gsub.LookupList.Lookup[idx]
                if lk.LookupType == 1:
                    for sub in lk.SubTable:
                        for g, alt in sub.mapping.items():
                            if g not in aalt_subst: aalt_subst[g] = alt
                elif lk.LookupType == 3:
                    for sub in lk.SubTable:
                        for g, alts in sub.alternates.items():
                            if g not in aalt_subst and alts: aalt_subst[g] = alts[0]

        cmap        = font.getBestCmap() or {}
        rev_cmap    = {v: k for k, v in cmap.items()}
        liga_glyphs = {}
        for feat in gsub.FeatureList.FeatureRecord:
            if feat.FeatureTag != "liga": continue
            for idx in feat.Feature.LookupListIndex:
                lk = gsub.LookupList.Lookup[idx]
                if lk.LookupType != 4: continue
                for sub in lk.SubTable:
                    for first_g, ligs in sub.ligatures.items():
                        for lig in ligs:
                            seq_glyphs = [first_g] + list(lig.Component)
                            seq_chars  = ""
                            ok = True
                            for g in seq_glyphs:
                                if g in rev_cmap: seq_chars += chr(rev_cmap[g])
                                else: ok = False; break
                            if ok and len(seq_chars) > 1:
                                liga_glyphs[seq_chars] = lig.LigGlyph
        print(f"[liga] {len(liga_glyphs)} pares")

        pua = _PUA_START; text_subst = {}
        for seq, liga_glyph in liga_glyphs.items():
            for tbl in font["cmap"].tables:
                if tbl.format in (4, 12): tbl.cmap[pua] = liga_glyph
            text_subst[seq] = chr(pua); pua += 1

        for tbl in font["cmap"].tables:
            if tbl.format in (4, 12):
                for code, glyph in list(tbl.cmap.items()):
                    if glyph in aalt_subst and code < _PUA_START:
                        tbl.cmap[code] = aalt_subst[glyph]

        tmp = _tempfile.NamedTemporaryFile(suffix=".otf", delete=False)
        font.save(tmp.name)
        _AGILERA_EST_PATH = tmp.name
        _LIGA_SUBST       = text_subst
        print(f"[font_est] OK: {len(aalt_subst)} aalt + {len(text_subst)} liga")
        return tmp.name
    except Exception as e:
        print(f"[font_est] falhou: {e}"); return None

def _aplicar_ligaturas(texto):
    if not _LIGA_SUBST: return texto
    for seq in sorted(_LIGA_SUBST, key=len, reverse=True):
        texto = texto.replace(seq, _LIGA_SUBST[seq])
    return texto

def f_display_est(t):
    est_path = _preparar_fonte_estilizada()
    if est_path:
        try: return ImageFont.truetype(est_path, t)
        except Exception as e: print(f"[font_est] erro: {e}")
    p = _resolve_font_path("AGILERA.OTF")
    if p:
        if _RAQM_OK:
            try: return ImageFont.truetype(p, t, layout_engine=ImageFont.Layout.RAQM)
            except Exception: pass
        try: return ImageFont.truetype(p, t)
        except Exception: pass
    try: return ImageFont.load_default(size=t)
    except Exception: return ImageFont.load_default()

def _linha_est(draw, x, y, texto, fonte, cor):
    if _RAQM_OK:
        try:
            draw.text((x, y), texto, font=fonte, fill=cor, features=["liga", "aalt"])
            return
        except Exception: pass
    draw.text((x, y), texto, font=fonte, fill=cor)

# ── IA ────────────────────────────────────────────────────────────────────────
ASSINATURA = (
    "\n\n\U0001f468\u200d\U0001f4bc Ronilson Nogueira\n"
    "\u270d\ufe0f Psicólogo e Professor\n"
    "\U0001f9e9 Referência em Autismo e TDAH\n"
    "CRP 04/57327"
)
PROMPT_LEGENDA = (
    "Crie uma legenda para um post do Instagram sobre: '{tema}'. "
    "Para o psicólogo Ronilson Nogueira, especialista em Autismo e TDAH, "
    "da clínica AlvoreSer em Coronel Fabriciano/MG. "
    "Tom: acolhedor, humano, reflexivo, não-clínico, para o público geral. "
    "Máximo 150 palavras. Não inclua hashtags. "
    "Retorne APENAS o texto da legenda, sem explicações ou markdown."
)
GROQ_MODELOS = ["llama-3.3-70b-versatile", "llama-3.1-8b-instant", "llama-4-scout"]

def _groq_legenda(tema):
    if not GROQ_API_KEY: raise Exception("GROQ_API_KEY nao configurada")
    ultimo = None
    for m in GROQ_MODELOS:
        try:
            r = requests.post(GROQ_URL,
                headers={"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"},
                json={"model": m, "messages": [{"role": "user", "content": PROMPT_LEGENDA.format(tema=tema)}], "max_tokens": 400},
                timeout=20)
            r.raise_for_status()
            return r.json()["choices"][0]["message"]["content"].strip()
        except Exception as e: ultimo = e
    raise Exception(f"Groq falhou: {ultimo}")

def _gemini_legenda(tema):
    if not GEMINI_API_KEY: raise Exception("GEMINI_API_KEY nao configurada")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GEMINI_API_KEY}"
    r = requests.post(url, json={"contents": [{"parts": [{"text": PROMPT_LEGENDA.format(tema=tema)}]}]}, timeout=25)
    if r.status_code == 429: raise Exception("Gemini 429")
    r.raise_for_status()
    return r.json()["candidates"][0]["content"]["parts"][0]["text"].strip()

def gerar_legenda_ia(tema):
    erros = []
    for fn in [_groq_legenda, _gemini_legenda]:
        try: return fn(tema) + ASSINATURA
        except Exception as e: erros.append(str(e))
    raise Exception("IAs falharam: " + " | ".join(erros))

# ── Cloudinary ────────────────────────────────────────────────────────────────
def buscar_imagem(tema=""):
    t     = tema.lower()
    todas = list(set(MAPA_PASTAS.values()))
    pasta = next((MAPA_PASTAS[k] for k in MAPA_PASTAS if k in t), None)
    if pasta: todas = [pasta] + [p for p in todas if p != pasta]
    for p in todas:
        try:
            res = cloudinary.api.resources(type="upload", prefix=p + "/", max_results=50)
            rec = [r for r in res.get("resources", [])
                   if CLOUDINARY_POSTS not in r.get("public_id", "")
                   and CLOUDINARY_PREVIEW not in r.get("public_id", "")]
            if rec:
                c = random.choice(rec)
                print(f"[busca] {c.get('public_id')}")
                return c.get("secure_url"), c.get("public_id", "")
        except Exception as e: print(f"[busca] '{p}': {e}")
    try:
        res = cloudinary.api.resources(type="upload", max_results=50)
        rec = [r for r in res.get("resources", [])
               if CLOUDINARY_POSTS not in r.get("public_id", "")
               and CLOUDINARY_PREVIEW not in r.get("public_id", "")]
        if rec:
            c = random.choice(rec)
            return c.get("secure_url"), c.get("public_id", "")
    except Exception as e: print(f"[busca] fallback: {e}")
    return None, ""

# ── Utilitários ───────────────────────────────────────────────────────────────
def _medir(texto, fonte):
    try:
        bb = fonte.getbbox(texto); return bb[2] - bb[0]
    except Exception: return len(texto) * 30

def _medir_sp(texto, fonte, sp):
    total = 0
    for ch in texto:
        try:
            bb = fonte.getbbox(ch); total += (bb[2] - bb[0]) + sp
        except Exception: total += 30 + sp
    return max(0, total - sp)

def _altura_linha(fonte, texto="Ag"):
    try:
        bb = fonte.getbbox(texto); return bb[3] - bb[1]
    except Exception: return 50

def _quebrar(texto, fonte, max_px, sp=0):
    palavras = texto.split()
    linhas, atual = [], []
    for p in palavras:
        cand = " ".join(atual + [p])
        w = _medir_sp(cand, fonte, sp) if sp else _medir(cand, fonte)
        if w <= max_px: atual.append(p)
        else:
            if atual: linhas.append(" ".join(atual))
            atual = [p]
    if atual: linhas.append(" ".join(atual))
    return linhas or [texto]

def cores_fundo(img):
    p    = list(img.resize((60, 75), Image.Resampling.LANCZOS).convert("RGB").getdata())
    cf   = tuple(sum(x[i] for x in p) // len(p) for i in range(3))
    ord_ = sorted([c for c in PALETA_9 if c != LARANJA],
                  key=lambda c: distancia_cor(cf, c), reverse=True)
    return (MARINHO, PETROLEO) if sum(cf) / 3 < 60 else (ord_[0], ord_[1])

def luminosidade_media(img):
    arr = np.array(img.convert("RGB").resize((80, 100))).astype(np.float32)
    return float(arr.mean())

def cor_dominante(img):
    p = list(img.resize((60, 75), Image.Resampling.LANCZOS).convert("RGB").getdata())
    return tuple(sum(x[i] for x in p) // len(p) for i in range(3))

def eh_foto_ronilson(pid):
    return "ronilson" in pid.lower().replace("\\", "/")

def remover_fundo_rembg(img):
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return Image.open(io.BytesIO(get_rembg()(buf.getvalue()))).convert("RGBA")

# ── Fundo rico ────────────────────────────────────────────────────────────────
def gerar_fundo_rico(cor1, cor2, seed):
    rng = random.Random(seed)
    arr = np.zeros((H, W, 3), dtype=np.float32)
    for y in range(H):
        t = y / H
        for ch in range(3):
            arr[y, :, ch] = cor1[ch] * (1 - t) + cor2[ch] * t
    cx = W * rng.uniform(0.30, 0.70); cy = H * rng.uniform(0.10, 0.35)
    ys, xs = np.ogrid[:H, :W]
    dist2  = ((xs - cx) / (W * 0.55))**2 + ((ys - cy) / (H * 0.45))**2
    luz    = np.exp(-dist2 * 1.2) * rng.uniform(20, 35)
    arr[:, :, 0] = np.clip(arr[:, :, 0] + luz,       0, 255)
    arr[:, :, 1] = np.clip(arr[:, :, 1] + luz * 0.8, 0, 255)
    arr[:, :, 2] = np.clip(arr[:, :, 2] + luz * 0.6, 0, 255)
    ruido = np.random.RandomState(seed).normal(0, 4, (H, W, 3))
    arr   = np.clip(arr + ruido, 0, 255).astype(np.uint8)
    return Image.fromarray(arr).filter(ImageFilter.GaussianBlur(1))

# ── Color grade ───────────────────────────────────────────────────────────────
def color_grade_editorial(img, seed):
    rng = random.Random(seed)
    arr = np.array(img.convert("RGB")).astype(np.float32)
    lum = arr.mean(axis=2, keepdims=True) / 255.0
    mask_s = np.clip(1.0 - lum * 2.5, 0, 1)
    arr[:, :, 0] *= 1 + (0.92 - 1) * mask_s[:, :, 0]
    arr[:, :, 1] *= 1 + (0.96 - 1) * mask_s[:, :, 0]
    arr[:, :, 2] *= 1 + (1.06 - 1) * mask_s[:, :, 0]
    mask_m = np.clip(1.0 - abs(lum - 0.45) * 4, 0, 1)
    arr[:, :, 0] = np.clip(arr[:, :, 0] + 6 * mask_m[:, :, 0], 0, 255)
    arr[:, :, 1] = np.clip(arr[:, :, 1] + 3 * mask_m[:, :, 0], 0, 255)
    arr[:, :, 2] = np.clip(arr[:, :, 2] - 4 * mask_m[:, :, 0], 0, 255)
    grain = np.random.RandomState(seed + 1).normal(0, rng.uniform(2.5, 4.5), arr.shape)
    arr   = np.clip(arr + grain, 0, 255)
    out   = Image.fromarray(arr.astype(np.uint8))
    blur  = out.filter(ImageFilter.GaussianBlur(1.8))
    ao    = np.array(out).astype(np.float32)
    ab    = np.array(blur).astype(np.float32)
    return Image.fromarray(np.clip(ao + (ao - ab) * 0.45, 0, 255).astype(np.uint8))

def aplicar_split_toning(img, intensidade=0.045):
    arr = np.array(img.convert("RGB")).astype(np.float32)
    lum = arr.mean(axis=2, keepdims=True) / 255.0
    arr += (np.array(MARINHO, dtype=np.float32) - arr) * ((1 - lum)**2) * intensidade
    arr += (np.array(LARANJA, dtype=np.float32) - arr) * (lum**2)       * intensidade
    return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))

def tratar_foto_editorial(img, cor_paleta, seed):
    img = color_grade_editorial(img, seed)
    img = ImageEnhance.Contrast(img).enhance(1.15)
    img = ImageEnhance.Color(img).enhance(1.10)
    img = ImageEnhance.Sharpness(img).enhance(1.18)
    img = ImageEnhance.Brightness(img).enhance(1.02)
    img = aplicar_split_toning(img)
    return img

def compor_pessoa(pessoa_rgba, fundo_rgb):
    pw, ph = pessoa_rgba.size
    nw     = int(pw * H / ph)
    pessoa_rgba = pessoa_rgba.resize((nw, H), Image.Resampling.LANCZOS)
    x = W - nw + 50
    x = max(int(W * 0.35), min(x, W - 120))
    alpha  = pessoa_rgba.split()[3]
    sombra = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    sil    = Image.new("RGBA", (nw, H), (0, 0, 0, 0))
    sil.paste(Image.new("RGB", (nw, H), MARINHO),
              mask=alpha.point(lambda v: int(v * 0.22)))
    sombra.paste(sil, (x - 24, 22), sil)
    sombra = sombra.filter(ImageFilter.GaussianBlur(45))
    res = fundo_rgb.convert("RGBA")
    res = Image.alpha_composite(res, sombra)
    res.paste(pessoa_rgba, (x, 0), pessoa_rgba)
    return res.convert("RGB")

def preparar_foto(url, pid, cor1, cor2, seed):
    try:
        r = requests.get(url, timeout=25); r.raise_for_status()
        img   = Image.open(io.BytesIO(r.content)).convert("RGB")
        ratio = max(W / img.width, H / img.height)
        nw, nh = int(img.width * ratio), int(img.height * ratio)
        img   = img.resize((nw, nh), Image.Resampling.LANCZOS)
        l = (nw - W) // 2; t = (nh - H) // 2
        img = img.crop((l, t, l + W, t + H))
        if eh_foto_ronilson(pid):
            print(f"[foto] Ronilson: {pid}")
            fundo = gerar_fundo_rico(cor1, cor2, seed)
            try:
                rgba = remover_fundo_rembg(img)
                img  = compor_pessoa(rgba, fundo)
                img  = aplicar_split_toning(img)
                img  = ImageEnhance.Contrast(img).enhance(1.08)
            except Exception as e:
                print(f"[foto] rembg falhou ({e})")
                img = Image.blend(fundo, img, alpha=0.60)
                img = aplicar_split_toning(img)
        else:
            print(f"[foto] editorial: {pid}")
            img = tratar_foto_editorial(img, cor1, seed)
        return img
    except Exception as e:
        print(f"[foto] ERRO: {e}"); return None

# ── Overlay ───────────────────────────────────────────────────────────────────
def _detectar_lado_texto(img):
    """
    Detecta em qual lado da imagem está o rosto/pessoa e retorna o lado OPOSTO,
    que é onde o texto deve ser colocado e onde o overlay deve ser aplicado.

    Divide a imagem em metades esquerda/direita e mede luminosidade média.
    O lado com mais luminosidade tende a ter a pessoa (fundo claro + figura).

    Retorna o lado onde deve ir o TEXTO (= overlay):
      'esquerda' → texto à esq  → overlay à esquerda (direcao=2)
      'direita'  → texto à dir  → overlay à direita  (direcao=3)
      'base'     → fallback base (direcao=0)
    """
    arr  = np.array(img.convert("RGB").resize((40, 50))).astype(np.float32)
    lum  = arr.mean(axis=2)  # 50 linhas × 40 colunas

    # Analisa só a metade superior da imagem (onde está o rosto geralmente)
    lum_top = lum[:25, :]
    esq  = lum_top[:, :20].mean()
    dir_ = lum_top[:, 20:].mean()

    diff = abs(esq - dir_)
    if diff < 6:
        # Sem diferença significativa → base (padrão)
        print(f"[overlay] lado: sem diferença clara (esq={esq:.1f} dir={dir_:.1f}) → base")
        return "base"

    if esq > dir_:
        # Rosto/pessoa à esquerda → texto vai à esquerda também (mesmo lado)
        print(f"[overlay] pessoa à esq → texto/overlay à esquerda (esq={esq:.1f} dir={dir_:.1f})")
        return "esquerda"
    else:
        # Rosto/pessoa à direita → texto vai à direita
        print(f"[overlay] pessoa à dir → texto/overlay à direita (esq={esq:.1f} dir={dir_:.1f})")
        return "direita"


def aplicar_overlay(img, lum_media, layout, seed=0,
                    cor_dominante_foto=None, cor_destaque_texto=None,
                    tem_pessoa=False):
    """
    Direções: base(0), topo(1), esquerda(2), direita(3).
    - Layout 3 → sempre topo
    - tem_pessoa=True → overlay no mesmo lado onde fica o texto (esq por padrão em fotos Ronilson)
    - Sem pessoa → direção por seed % 4
    """
    if lum_media > 160:   alpha_max = 218
    elif lum_media > 120: alpha_max = 192
    elif lum_media > 80:  alpha_max = 168
    else:                 alpha_max = 148

    cor_ov = (_escolher_cor_overlay(cor_dominante_foto, cor_destaque_texto or LARANJA, seed)
              if cor_dominante_foto else MARINHO)
    print(f"[overlay] cor={cor_ov} lum={lum_media:.0f} alpha={alpha_max}")

    lum_ov = _LUM_COR.get(cor_ov, 0.5)
    if lum_ov > 0.5:
        alpha_max = min(255, int(alpha_max * 1.30))

    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw    = ImageDraw.Draw(overlay)

    if layout == 3:
        direcao = 1  # topo forçado
    elif tem_pessoa:
        lado = _detectar_lado_texto(img)
        # Mapa direto: lado onde vai o texto → direção do overlay
        mapa = {"esquerda": 2, "direita": 3, "base": 0}
        direcao = mapa.get(lado, 0)
        print(f"[overlay] pessoa: lado_texto={lado} → direcao={direcao}")
    else:
        direcao = seed % 4

    if direcao == 1:
        # Topo
        altura = int(H * 0.48)
        for y in range(altura):
            prog  = 1.0 - y / altura
            alpha = int((prog ** 1.5) * alpha_max)
            draw.line([(0, y), (W, y)], fill=(*cor_ov, alpha))

    elif direcao == 2:
        # Esquerda — opaco na borda esq, zero no centro
        for x in range(W):
            prog  = max(0.0, 1.0 - x / (W * 0.55))
            alpha = int((prog ** 1.6) * alpha_max)
            if alpha > 0:
                draw.line([(x, 0), (x, H)], fill=(*cor_ov, alpha))

    elif direcao == 3:
        # Direita — opaco na borda dir, zero no centro
        for x in range(W):
            prog  = max(0.0, 1.0 - (W - 1 - x) / (W * 0.55))
            alpha = int((prog ** 1.6) * alpha_max)
            if alpha > 0:
                draw.line([(x, 0), (x, H)], fill=(*cor_ov, alpha))

    else:
        # Base
        altura = int(H * 0.55)
        for y in range(altura):
            prog  = y / altura
            alpha = int((prog ** 1.3) * alpha_max)
            draw.line([(0, H - altura + y), (W, H - altura + y)],
                      fill=(*cor_ov, alpha))

    return Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")

# ── Parser ────────────────────────────────────────────────────────────────────
SEPARADORES = [" e ", " são ", " é ", " como ", ": ", " — ", " - "]

def _split_tema(tema):
    t = tema.strip()
    for sep in SEPARADORES:
        idx = t.lower().find(sep.lower())
        if idx > 0: return t[:idx].strip(), t[idx:].strip()
    return t, ""

def _parse_inline(tema):
    """
    Parser inline token a token.

    Símbolos (prefixo colado à palavra):
      (sem)     → normal      : AGILERA normal, cor destaque
      *palavra  → agilera_est : AGILERA estilizada, cor destaque
      :palavra  → malgun      : MALGUN bold
      -palavra  → fundo       : fundo preenchido

    Regras:
    - Tokens consecutivos com mesmo símbolo agrupados no mesmo segmento
    - '-' após ':' herda MALGUN; '-' em qualquer outro contexto usa AGILERA
    - Sem símbolos → modo automático (_split_tema)
    """
    texto  = " ".join(l.strip() for l in tema.split("\n") if l.strip())
    tokens = texto.split()

    segmentos      = []
    estilo_atual   = None
    palavras_atual = []
    ultimo_estilo_fechado = None

    def _fechar():
        nonlocal palavras_atual, estilo_atual, ultimo_estilo_fechado
        if palavras_atual:
            segmentos.append({"texto": " ".join(palavras_atual),
                              "estilo": estilo_atual or "normal"})
            ultimo_estilo_fechado = estilo_atual
            palavras_atual = []

    for token in tokens:
        if not token:
            continue

        if token[0] == "*" and len(token) > 1:
            novo_estilo = "agilera_est"; palavra = token[1:]
        elif token[0] == ":" and len(token) > 1:
            novo_estilo = "malgun"; palavra = token[1:]
        elif token[0] == "-" and len(token) > 1:
            if estilo_atual == "malgun" or ultimo_estilo_fechado == "malgun":
                novo_estilo = "fundo_malgun"
            else:
                novo_estilo = "fundo_agilera"
            palavra = token[1:]
        elif token in ("*", ":", "-"):
            _fechar()
            if token == "*":   estilo_atual = "agilera_est"
            elif token == ":": estilo_atual = "malgun"
            else:
                estilo_atual = ("fundo_malgun"
                                if ultimo_estilo_fechado == "malgun"
                                else "fundo_agilera")
            continue
        else:
            novo_estilo = "normal"; palavra = token

        if novo_estilo == estilo_atual:
            palavras_atual.append(palavra)
        else:
            _fechar()
            estilo_atual   = novo_estilo
            palavras_atual = [palavra]

    _fechar()

    estilos_usados = {s["estilo"] for s in segmentos}
    if estilos_usados == {"normal"} or not estilos_usados:
        chave, comp = _split_tema(tema.strip())
        resultado   = [{"texto": chave, "estilo": "normal"}]
        if comp: resultado.append({"texto": comp, "estilo": "malgun"})
        return resultado

    return segmentos or [{"texto": tema.strip(), "estilo": "normal"}]

# ── Texto ─────────────────────────────────────────────────────────────────────
def _sombra(img_rgba, texto, fonte, x, y, sp=0, forte=False):
    params = [((8, 10), 22, 0.55), ((3, 4), 5, 0.75)] if forte \
             else [((6, 8), 18, 0.42), ((2, 3), 3, 0.68)]
    for (ox, oy), blur, opac in params:
        layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        d     = ImageDraw.Draw(layer)
        _linha(d, x + ox, y + oy, texto, fonte, (2, 20, 30, int(255 * opac)), sp)
        layer = layer.filter(ImageFilter.GaussianBlur(blur))
        img_rgba.paste(layer, (0, 0), layer)

def _linha(draw, x, y, texto, fonte, cor, sp=0):
    if sp == 0:
        draw.text((x, y), texto, font=fonte, fill=cor); return
    cursor = x
    for ch in texto:
        draw.text((cursor, y), ch, font=fonte, fill=cor)
        try:
            bb = fonte.getbbox(ch); cursor += (bb[2] - bb[0]) + sp
        except Exception: cursor += 30 + sp

def _cor_segmento_clara(seed):
    """
    Retorna sempre uma cor clara/legível garantida para segmentos 'normal'
    quando o fundo/overlay for escuro (Ronilson com camisa escura, overlay escuro).
    Prioriza BRANCO, AMARELO, LARANJA — sempre visíveis sobre fundo escuro.
    """
    claras = [BRANCO, AMARELO, LARANJA, VERDE_CITRICO, TEAL]
    return claras[seed % len(claras)]

def _cor_segmento(idx, cor_dest, seed, lum_overlay=0.3):
    """
    Retorna cor de texto para o segmento de índice idx.
    - Se overlay escuro (lum < 0.45): usa cor de destaque normal (já é clara)
    - Se overlay claro (lum >= 0.45): usa cor clara forçada para garantir contraste
    - Varia entre segmentos para criar diversidade
    """
    if lum_overlay >= 0.45:
        # Overlay claro → garante cor escura para contraste
        escuras = [MARINHO, PETROLEO]
        return escuras[idx % len(escuras)]

    if idx % 2 == 0:
        return cor_dest
    idx_sec = (seed % 9 + 3) % 9
    cor_sec = CORES_DESTAQUE[idx_sec]
    if cor_sec == cor_dest:
        cor_sec = CORES_DESTAQUE[(seed % 9 + 5) % 9]
    return cor_sec

def desenhar_titulo(img, tema, seed, cor_dest=None, cor_fundo_txt=None, cor_overlay=None):
    """
    Renderiza segmentos do tema.
    Segmentos 'normal' recebem cor garantidamente legível sobre o overlay.
    """
    img_rgba = img.convert("RGBA")
    MARGIN   = SAFE_MARGIN
    MAX_PX   = SAFE_MAX_PX
    layout   = seed % 5

    if cor_dest is None:
        cor_dest, cor_fundo_txt = _escolher_cor_destaque(seed)

    lum_overlay  = _LUM_COR.get(cor_overlay, 0.3) if cor_overlay else 0.3
    sombra_forte = lum_overlay > 0.45
    print(f"[titulo] cor_dest={cor_dest} layout={layout} lum_overlay={lum_overlay:.2f} sombra_forte={sombra_forte}")

    segmentos = _parse_inline(tema)

    textos_ag = [s["texto"] for s in segmentos
                 if s["estilo"] in ("normal", "agilera_est", "fundo_agilera", "fundo_malgun")]
    n = max((len(t) for t in textos_ag), default=len(tema))

    if layout == 2:
        tam_ag = 148 if n <= 8 else 128 if n <= 14 else 108 if n <= 20 else 88 if n <= 28 else 72
    elif layout == 4:
        tam_ag = 100 if n <= 10 else 86 if n <= 16 else 74 if n <= 24 else 62
    else:
        tam_ag = 132 if n <= 6 else 112 if n <= 10 else 96 if n <= 16 else 82 if n <= 24 else 68 if n <= 34 else 56

    tam_ml = max(40, int(tam_ag * 0.56))
    ag_sp  = -3 if tam_ag >= 100 else -2
    fa     = f_display(tam_ag)
    fb     = f_bold(tam_ml)

    # ── Renderização inline: segmentos na mesma linha quando cabem ──────────
    # Converte segmentos em "tokens visuais" com fonte e cor, depois quebra
    # respeitando MAX_PX — isso evita que "oque" e "ninguém entende?" fiquem
    # em blocos separados quando poderiam estar na mesma linha.

    # Primeiro: monta lista de tokens (palavra, fonte, cor, estilo, cor_rect)
    tokens_visuais = []
    for idx_seg, seg in enumerate(segmentos):
        txt = seg["texto"].strip()
        est = seg["estilo"]
        if not txt: continue

        cor_seg = _cor_segmento(idx_seg, cor_dest, seed, lum_overlay)

        if est == "agilera_est":
            tam_est = int(tam_ag * 1.32)
            fa_est  = f_display_est(tam_est)
            for palavra in txt.split():
                tokens_visuais.append({
                    "palavra": _aplicar_ligaturas(palavra),
                    "fonte": fa_est, "cor": cor_seg,
                    "estilo": est, "cor_rect": None, "sp": ag_sp
                })
        elif est == "malgun":
            lum_seg = _LUM_COR.get(cor_seg, 0.5)
            cor_ml  = cor_seg if lum_seg > 0.42 else BRANCO
            for palavra in txt.split():
                tokens_visuais.append({
                    "palavra": palavra,
                    "fonte": fb, "cor": cor_ml,
                    "estilo": est, "cor_rect": None, "sp": 0
                })
        elif est in ("fundo_agilera", "fundo_malgun"):
            fonte_f = fb if est == "fundo_malgun" else fa
            cor_txt_f = CORES_FUNDO_TEXTO.get(cor_seg, MARINHO)
            for palavra in txt.split():
                tokens_visuais.append({
                    "palavra": palavra,
                    "fonte": fonte_f, "cor": cor_txt_f,
                    "estilo": est, "cor_rect": cor_seg, "sp": 0
                })
        else:  # normal
            for palavra in txt.split():
                tokens_visuais.append({
                    "palavra": palavra,
                    "fonte": fa, "cor": cor_seg,
                    "estilo": est, "cor_rect": None, "sp": ag_sp
                })

    if not tokens_visuais:
        return img_rgba.convert("RGB"), layout

    # Agrupa tokens em linhas respeitando MAX_PX
    # Tokens de estilos diferentes podem coexistir na mesma linha
    linhas_render = []   # cada item: lista de tokens que cabem na linha
    linha_atual   = []
    largura_atual = 0

    for tok in tokens_visuais:
        palavra = tok["palavra"]
        fonte   = tok["fonte"]
        sp      = tok.get("sp", 0)
        w_tok   = (_medir_sp(palavra, fonte, sp) if sp else _medir(palavra, fonte))
        espaco  = (_medir(" ", fonte) if linha_atual else 0)

        if linha_atual and largura_atual + espaco + w_tok > MAX_PX:
            linhas_render.append(linha_atual)
            linha_atual   = [tok]
            largura_atual = w_tok
        else:
            linha_atual.append(tok)
            largura_atual += espaco + w_tok

    if linha_atual:
        linhas_render.append(linha_atual)

    # Calcula altura total para posicionamento
    alt_linha = _altura_linha(fa)  # usa a maior fonte como referência
    esp_linha = int(alt_linha * 1.12)
    h_total   = esp_linha * len(linhas_render)

    zonas = [
        (int(H * 0.55), int(H * 0.80)),
        (int(H * 0.42), int(H * 0.72)),
        (int(H * 0.58), int(H * 0.85)),
        (int(H * 0.25), int(H * 0.55)),
        (int(H * 0.45), int(H * 0.75)),
    ]
    Y_INI_raw, Y_FIM_raw = zonas[layout]
    Y_INI = max(SAFE_TOP,    Y_INI_raw)
    Y_FIM = min(SAFE_BOTTOM, Y_FIM_raw)

    zona = Y_FIM - Y_INI
    y    = Y_INI + max(0, (zona - h_total) // 2)
    y    = max(Y_INI, min(y, Y_FIM - h_total - 8))
    y    = max(SAFE_TOP + 20, min(y, SAFE_BOTTOM - h_total - 20))

    # Renderiza linha por linha
    for linha_toks in linhas_render:
        draw = ImageDraw.Draw(img_rgba, "RGBA")
        x = MARGIN
        for tok in linha_toks:
            palavra = tok["palavra"]
            fonte   = tok["fonte"]
            cor     = tok["cor"]
            est     = tok["estilo"]
            cor_rect = tok.get("cor_rect")
            sp      = tok.get("sp", 0)

            w_tok = (_medir_sp(palavra, fonte, sp) if sp else _medir(palavra, fonte))

            if est in ("fundo_agilera", "fundo_malgun"):
                pad_x, pad_y = 18, 10
                try:
                    bb  = fonte.getbbox(palavra)
                    rx1 = x - pad_x;       ry1 = y + bb[1] - pad_y
                    rx2 = x + (bb[2] - bb[0]) + pad_x; ry2 = y + bb[3] + pad_y
                except Exception:
                    rx1 = x - pad_x;  ry1 = y - pad_y
                    rx2 = x + w_tok + pad_x; ry2 = y + alt_linha + pad_y
                draw.rounded_rectangle([(rx1, ry1), (rx2, ry2)],
                                       radius=8, fill=(*(cor_rect or cor_dest), 255))
                draw = ImageDraw.Draw(img_rgba, "RGBA")
                _linha(draw, x, y, palavra, fonte, (*cor, 255), 0)
            else:
                _sombra(img_rgba, palavra, fonte, x, y, sp, forte=sombra_forte)
                draw = ImageDraw.Draw(img_rgba, "RGBA")
                if est == "agilera_est":
                    _linha_est(draw, x, y, palavra, fonte, (*cor, 255))
                else:
                    _linha(draw, x, y, palavra, fonte, (*cor, 255), sp)

            # Avança x pelo token + espaço
            espaco_px = _medir(" ", fonte)
            x += w_tok + espaco_px

        y += esp_linha

    return img_rgba.convert("RGB"), layout

# ── Geração principal ─────────────────────────────────────────────────────────
def gerar_card_imagem(tema, legenda, imagem_url, pid="", seed=None):
    if seed is None:
        seed = random.randint(0, 999999)
    print(f"[card] seed={seed} layout={seed % 5}")

    cor1, cor2 = MARINHO, PETROLEO
    lum_media  = 100.0
    cor_dom    = None
    tem_pessoa = eh_foto_ronilson(pid)

    if imagem_url:
        try:
            r = requests.get(imagem_url, timeout=15); r.raise_for_status()
            tmp        = Image.open(io.BytesIO(r.content)).convert("RGB")\
                              .resize((120, 150), Image.Resampling.LANCZOS)
            cor1, cor2 = cores_fundo(tmp)
            lum_media  = luminosidade_media(tmp)
            cor_dom    = cor_dominante(tmp)
        except Exception as e: print(f"[cor] {e}")

    if imagem_url:
        base = preparar_foto(imagem_url, pid, cor1, cor2, seed)
        if base is None:
            base = gerar_fundo_rico(cor1, cor2, seed)
            lum_media = luminosidade_media(base)
            cor_dom   = cor_dominante(base)
            tem_pessoa = False
    else:
        base = gerar_fundo_rico(cor1, cor2, seed)
        lum_media = luminosidade_media(base)
        cor_dom   = cor_dominante(base)
        tem_pessoa = False

    layout = seed % 5
    cor_dest, cor_fundo_txt = _escolher_cor_destaque(seed)

    base = aplicar_overlay(base, lum_media, layout, seed=seed,
                           cor_dominante_foto=cor_dom,
                           cor_destaque_texto=cor_dest,
                           tem_pessoa=tem_pessoa)

    cor_ov_usada = (_escolher_cor_overlay(cor_dom, cor_dest, seed)
                   if cor_dom else MARINHO)

    base, _ = desenhar_titulo(base, tema, seed,
                              cor_dest=cor_dest,
                              cor_fundo_txt=cor_fundo_txt,
                              cor_overlay=cor_ov_usada)
    return base

# ── Planilha ──────────────────────────────────────────────────────────────────
def get_sheets():
    creds = service_account.Credentials.from_service_account_info(
        json.loads(SERVICE_ACCOUNT_JSON), scopes=SCOPES)
    return build("sheets", "v4", credentials=creds)

def escrever_planilha(tema, legenda, url):
    svc   = get_sheets()
    agora = datetime.now().strftime("%Y-%m-%d %H:%M")
    linha = [agora, tema, tema, legenda,
             "Profissional e acolhedor", "Pronta", "Aguardando Postagem", url]
    res = svc.spreadsheets().values().append(
        spreadsheetId=SPREADSHEET_ID, range="A:H",
        valueInputOption="RAW", insertDataOption="INSERT_ROWS",
        body={"values": [linha]}).execute()
    try: return int(res["updates"]["updatedRange"].split("!A")[1].split(":")[0])
    except Exception: return 0

def atualizar_status(linha, status):
    get_sheets().spreadsheets().values().update(
        spreadsheetId=SPREADSHEET_ID, range=f"G{linha}",
        valueInputOption="RAW", body={"values": [[status]]}).execute()

# ── Rotas ─────────────────────────────────────────────────────────────────────
def _env_first(*keys):
    for key in keys:
        val = os.getenv(key)
        if val and str(val).strip(): return str(val).strip()
    return None

@app.route("/config/firebase", methods=["GET"])
def rota_config_firebase():
    cfg = {
        "apiKey":            _env_first("FIREBASE_API_KEY", "VITE_FIREBASE_API_KEY"),
        "authDomain":        _env_first("FIREBASE_AUTH_DOMAIN", "VITE_FIREBASE_AUTH_DOMAIN"),
        "projectId":         _env_first("FIREBASE_PROJECT_ID", "VITE_FIREBASE_PROJECT_ID"),
        "storageBucket":     _env_first("FIREBASE_STORAGE_BUCKET", "VITE_FIREBASE_STORAGE_BUCKET"),
        "messagingSenderId": _env_first("FIREBASE_MESSAGING_SENDER_ID", "VITE_FIREBASE_MESSAGING_SENDER_ID"),
        "appId":             _env_first("FIREBASE_APP_ID", "VITE_FIREBASE_APP_ID"),
    }
    if not cfg["apiKey"]:
        return jsonify({"erro": "Firebase nao configurado."}), 503
    return jsonify(cfg)

@app.route("/health", methods=["GET"])
def health():
    fontes   = {fn: _resolve_font_path(fn) is not None
                for fn in ["AGILERA.OTF", "MALGUN.TTF", "MALGUNBD.TTF", "MALGUNSL.TTF"]}
    caminhos = {fn: _resolve_font_path(fn) or "FALTANDO"
                for fn in ["AGILERA.OTF", "MALGUN.TTF", "MALGUNBD.TTF", "MALGUNSL.TTF"]}
    return jsonify({"status": "ok", "dimensoes": f"{W}x{H}",
                    "fontes": fontes, "caminhos": caminhos,
                    "raqm": _RAQM_OK, "liga_count": len(_LIGA_SUBST),
                    "ronilson_path": PASTA_RONILSON})

@app.route("/gerar-legenda", methods=["POST"])
def rota_gerar_legenda():
    data = request.get_json() or {}
    tema = data.get("tema", "").strip()
    if not tema: return jsonify({"erro": "Tema obrigatorio"}), 400
    try: return jsonify({"legenda": gerar_legenda_ia(tema)})
    except Exception as e: return jsonify({"erro": str(e)}), 500

@app.route("/preview-card", methods=["POST"])
def rota_preview_card():
    data    = request.get_json() or {}
    tema    = data.get("tema",    "").strip()
    legenda = data.get("legenda", "").strip()
    if not tema: return jsonify({"erro": "Tema obrigatorio"}), 400

    erros_leg = None
    if not legenda:
        try: legenda = gerar_legenda_ia(tema)
        except Exception as e: erros_leg = str(e); legenda = ""
    if legenda and "CRP 04/57327" not in legenda:
        legenda = legenda.rstrip() + ASSINATURA

    url_img, pid = buscar_imagem(tema)
    print(f"[preview] tema='{tema}' pid='{pid}'")

    try:
        seed    = data.get("seed")
        card    = gerar_card_imagem(tema, legenda, url_img, pid, seed=seed)
        card_id = f"preview_{uuid.uuid4().hex[:10]}"
        buf     = io.BytesIO()
        card.save(buf, format="JPEG", quality=93)
        card_bytes  = buf.getvalue()
        preview_url = f"data:image/jpeg;base64,{base64.b64encode(card_bytes).decode()}"
        _cards_pendentes[card_id] = {
            "tema": tema, "legenda": legenda,
            "imagem_fundo": url_img, "pid_fundo": pid,
            "card_bytes": card_bytes}
    except Exception as e:
        import traceback; traceback.print_exc()
        return jsonify({"erro": f"Erro ao gerar card: {e}"}), 500

    resp = {"card_id": card_id, "preview_url": preview_url,
            "legenda": legenda, "imagem_fundo": url_img}
    if erros_leg: resp["aviso_legenda"] = erros_leg
    return jsonify(resp)

@app.route("/aprovar-card", methods=["POST"])
def rota_aprovar_card():
    data    = request.get_json() or {}
    card_id = data.get("card_id", "")
    legenda = data.get("legenda", "").strip()
    tema    = data.get("tema",    "").strip()
    if not card_id or card_id not in _cards_pendentes:
        return jsonify({"erro": "Card nao encontrado. Gere novamente."}), 400
    dados         = _cards_pendentes[card_id]
    legenda_final = legenda if legenda else dados["legenda"]
    try:
        uid = f"post_{uuid.uuid4().hex[:8]}"
        res = cloudinary.uploader.upload(
            io.BytesIO(dados["card_bytes"]), public_id=uid,
            folder=CLOUDINARY_POSTS, overwrite=True, resource_type="image")
        card_url = res.get("secure_url", "")
        if not card_url: return jsonify({"erro": "Falha no upload"}), 500
        del _cards_pendentes[card_id]
    except Exception as e: return jsonify({"erro": f"Erro no upload: {e}"}), 500
    linha = 0
    try: linha = escrever_planilha(tema, legenda_final, card_url)
    except Exception as e: print(f"[planilha] ERRO: {e}")
    return jsonify({"cloudinary_url": card_url, "linha_planilha": linha,
                    "status": "Aguardando Postagem"})

@app.route("/gerar-card", methods=["POST"])
def rota_gerar_card(): return rota_preview_card()

@app.route("/atualizar-status", methods=["POST"])
def rota_atualizar_status():
    data   = request.get_json() or {}
    linha  = data.get("linha"); status = data.get("status", "Postado")
    if not linha: return jsonify({"erro": "Linha obrigatoria"}), 400
    try: atualizar_status(int(linha), status); return jsonify({"ok": True})
    except Exception as e: return jsonify({"erro": str(e)}), 500

@app.route("/")
def index():
    if _dist_index_path(): return app.send_static_file("index.html")
    return jsonify({"erro": "Frontend nao compilado."}), 503

@app.route("/<path:path>")
def spa_static(path):
    dist_file = os.path.join(app.static_folder or "", path)
    if app.static_folder and os.path.isfile(dist_file): return app.send_static_file(path)
    if _dist_index_path(): return app.send_static_file("index.html")
    return jsonify({"erro": "Not Found"}), 404

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)))
