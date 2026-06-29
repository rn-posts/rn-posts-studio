"""
python-api/main.py  —  AlvoreSer Instagram Posts  —  v16

CORREÇÕES v16
=============
- _parse_inline: \n é quebra de BLOCO forçada — cada linha do editor é um bloco separado
  nunca misturado inline com outros segmentos de tamanho diferente
- Cores: seed varia por hash(tema)+timestamp para nunca repetir a mesma paleta
- Texto nunca sobrepõe rosto: zona de texto limitada à metade esquerda quando pessoa à direita
- Blocos renderizados linha por linha (sem flow inline entre segmentos diferentes)
- Overlay: lógica mantida da v15, sem regressão

PIPELINE
========
Imagem: Cloudinary → rembg (Ronilson) ou color grade (editorial) → fallback gradiente
Overlay: cor da paleta por contraste com foto, nunca igual ao texto, direção detectada
Tipografia: (sem símbolo) AGILERA | * AGILERA estilizada | : MALGUN | - fundo preenchido
Layout: cada linha do tema = um bloco visual independente
"""

import os, io, uuid, random, json, math, base64, hashlib
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
# Overlay: apenas cores frias/escuras — adequado para saúde mental
CORES_OVERLAY_PERMITIDAS = [MARINHO, PETROLEO, TEAL, VERDE_NEUTRO]

# Destaque de texto: todas as 9 cores
CORES_DESTAQUE = [
    LARANJA, AMARELO, TEAL, BRANCO, VERDE_NEUTRO,
    PETROLEO, LARANJA, AMARELO, TEAL,
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
    """Overlay sempre em cores frias/escuras — nunca verde-limão ou amarelo."""
    dist_max = math.sqrt(255**2 * 3)
    candidatas = []
    for cor in CORES_OVERLAY_PERMITIDAS:
        if cor == cor_destaque_texto: continue
        dist  = distancia_cor(cor_dominante_foto, cor) / dist_max
        bonus = dist  # prefere cor mais diferente da foto
        candidatas.append((bonus, cor))
    if not candidatas:
        return MARINHO
    candidatas.sort(key=lambda x: -x[0])
    top3 = candidatas[:3]
    _, melhor_cor = top3[seed % len(top3)]
    print(f"[overlay_cor] top3={[c for _,c in top3]} → {melhor_cor}")
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
def aplicar_overlay(img, lum_media, layout, seed=0,
                    cor_dominante_foto=None, cor_destaque_texto=None,
                    tem_pessoa=False):
    """
    Direções: base(0), topo(1), esquerda(2), direita(3).
    Para fotos Ronilson (rembg): pessoa está à direita → overlay à esquerda (direcao=2).
    Para fotos editoriais: seed % 4, mas nunca lateral (só base ou topo).
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
        # Pessoa composta à direita → overlay à esquerda (onde fica o texto)
        direcao = 2
        print(f"[overlay] pessoa → direcao=2 (esquerda)")
    else:
        # Fotos editoriais: só base — overlay em toda a base da foto
        direcao = 0

    if direcao == 1:
        altura = int(H * 0.48)
        for y in range(altura):
            prog  = 1.0 - y / altura
            alpha = int((prog ** 1.5) * alpha_max)
            draw.line([(0, y), (W, y)], fill=(*cor_ov, alpha))

    elif direcao == 2:
        # Esquerda: cobre ~55% da largura, opaco na borda esq
        for x in range(W):
            prog  = max(0.0, 1.0 - x / (W * 0.55))
            alpha = int((prog ** 1.6) * alpha_max)
            if alpha > 0:
                draw.line([(x, 0), (x, H)], fill=(*cor_ov, alpha))

    elif direcao == 3:
        # Direita
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
def _parse_blocos(tema):
    """
    Converte o tema em lista de blocos independentes.

    MODO 1 — Multiline (editor com \n):
      Cada linha = um bloco. Símbolo no INÍCIO da linha define o estilo.
        (sem)  → normal
        *texto → agilera_est
        :texto → malgun
        -texto → fundo

    MODO 2 — Linha única com símbolos inline:
      `Autismo na *Vida Adulta :oque -ninguém entende?`
      Cada token que começa com *, :, - inicia um novo bloco.
      Tokens sem símbolo acumulam no bloco normal corrente.

    Cada bloco ocupa suas próprias linhas verticais.
    """
    linhas_raw = [l.strip() for l in tema.split("\n") if l.strip()]

    if len(linhas_raw) > 1:
        blocos = []
        for t in linhas_raw:
            if t.startswith("*"):   estilo, texto = "agilera_est", t[1:].strip()
            elif t.startswith(":"): estilo, texto = "malgun",      t[1:].strip()
            elif t.startswith("-"): estilo, texto = "fundo",       t[1:].strip()
            else:                   estilo, texto = "normal",      t
            if texto:
                blocos.append({"texto": texto, "estilo": estilo})
        return blocos or [{"texto": tema.strip(), "estilo": "normal"}]

    linha  = linhas_raw[0] if linhas_raw else tema.strip()
    tokens = linha.split()

    # Regras:
    # * e : mudam o estilo CORRENTE — palavras seguintes do mesmo estilo
    #   ficam no mesmo bloco (sem fechar desnecessariamente)
    # - afeta APENAS a palavra colada a ele; o restante volta ao estilo anterior

    blocos       = []
    estilo_atual = "normal"
    palavras     = []

    def _fechar():
        if palavras:
            blocos.append({"texto": " ".join(palavras), "estilo": estilo_atual})
            palavras.clear()

    for tok in tokens:
        if tok.startswith("-") and len(tok) > 1:
            # Fundo: isola só esta palavra; estilo anterior continua depois
            estilo_antes = estilo_atual
            _fechar()
            blocos.append({"texto": tok[1:], "estilo": "fundo"})
            estilo_atual = estilo_antes   # volta ao estilo anterior

        elif tok.startswith("*") and len(tok) > 1:
            novo = "agilera_est"
            if estilo_atual != novo: _fechar(); estilo_atual = novo
            palavras.append(tok[1:])

        elif tok.startswith(":") and len(tok) > 1:
            novo = "malgun"
            if estilo_atual != novo: _fechar(); estilo_atual = novo
            palavras.append(tok[1:])

        elif tok == "-":
            pass   # traço isolado sem palavra — ignora

        elif tok == "*":
            if estilo_atual != "agilera_est": _fechar(); estilo_atual = "agilera_est"

        elif tok == ":":
            if estilo_atual != "malgun": _fechar(); estilo_atual = "malgun"

        else:
            # Palavra sem símbolo — se estilo mudou para normal, fecha o bloco atual
            if estilo_atual not in ("normal", "malgun", "agilera_est"):
                _fechar(); estilo_atual = "normal"
            palavras.append(tok)

    _fechar()
    return blocos or [{"texto": linha, "estilo": "normal"}]

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

# ── Variações tipográficas ───────────────────────────────────────────────────
# 6 modos selecionados pelo seed — aplicados a TODOS os blocos
#
# Modo 0: padrão (tracking normal, sem ligaturas)         — sempre disponível
# Modo 1: tracking aberto  (sp positivo, letras espaçadas) — sempre disponível
# Modo 2: tracking fechado (sp negativo, letras condensadas)— sempre disponível
# Modo 3: ligaturas via fonttools (aalt+liga)               — quando disponível
# Modo 4: ligaturas + tracking aberto                       — quando disponível
# Modo 5: fonte estilizada + tamanho levemente menor        — quando disponível
#
# Se fonttools falhar nos modos 3/4/5, cai em variante pura de tracking

def _modo_tipografico(seed):
    """Retorna o modo tipográfico (0-5) baseado no seed."""
    return seed % 6

def _sp_para_modo(modo, tam_base):
    """
    Retorna o letter-spacing (sp) para o modo dado.
    Aplicado a AGILERA (normal e agilera_est).
    MALGUN usa sp=0 sempre (fonte proporcional, sp prejudica).
    """
    if modo == 1 or modo == 4:  # tracking aberto
        return max(2, int(tam_base * 0.04))
    if modo == 2:               # tracking fechado
        return min(-1, int(tam_base * -0.02))
    if modo == 3 or modo == 5:  # ligaturas — tracking padrão
        return -3 if tam_base >= 100 else -2
    return -3 if tam_base >= 100 else -2  # padrão

def _fonte_agilera_para_modo(modo, tam):
    """
    Retorna a fonte AGILERA correta para o modo.
    Modos 3/4/5 tentam usar a fonte estilizada; se falhar, usa normal.
    """
    if modo in (3, 4, 5):
        est = _preparar_fonte_estilizada()
        if est:
            try:
                return ImageFont.truetype(est, tam), True  # (fonte, tem_ligaturas)
            except Exception:
                pass
        # fallback: AGILERA normal com RAQM se disponível
        p = _resolve_font_path("AGILERA.OTF")
        if p and _RAQM_OK:
            try:
                return ImageFont.truetype(p, tam, layout_engine=ImageFont.Layout.RAQM), True
            except Exception:
                pass
        return f_display(tam), False
    return f_display(tam), False

def _texto_para_modo(modo, texto):
    """Aplica ligaturas ao texto se o modo suporta."""
    if modo in (3, 4, 5) and _LIGA_SUBST:
        return _aplicar_ligaturas(texto)
    return texto

def _renderizar_linha_agilera(draw, img_rgba, x, y, texto, fonte, cor, sp,
                               tem_liga, sombra_forte):
    """Renderiza uma linha AGILERA com sombra, respeitando o modo tipográfico."""
    _sombra(img_rgba, texto, fonte, x, y, sp, forte=sombra_forte)
    draw = ImageDraw.Draw(img_rgba, "RGBA")
    if tem_liga:
        _linha_est(draw, x, y, texto, fonte, (*cor, 255))
    else:
        _linha(draw, x, y, texto, fonte, (*cor, 255), sp)
    return draw

def desenhar_titulo(img, tema, seed, cor_dest=None, cor_fundo_txt=None,
                    cor_overlay=None, tem_pessoa=False):
    img_rgba = img.convert("RGBA")
    MARGIN   = SAFE_MARGIN
    # Para fotos com pessoa à direita: texto na terça parte esquerda
    # Para editoriais: texto na zona segura completa, mas posicionado na base
    MAX_PX   = (int(W * 0.44) - MARGIN) if tem_pessoa else SAFE_MAX_PX
    layout   = seed % 5

    if cor_dest is None:
        cor_dest, cor_fundo_txt = _escolher_cor_destaque(seed)

    lum_overlay  = _LUM_COR.get(cor_overlay, 0.3) if cor_overlay else 0.3
    sombra_forte = lum_overlay > 0.45
    print(f"[titulo] layout={layout} lum_overlay={lum_overlay:.2f} MAX_PX={MAX_PX}")

    blocos = _parse_blocos(tema)
    if not blocos:
        return img_rgba.convert("RGB"), layout

    # Tamanho de fonte: baseado no bloco mais longo que usa AGILERA
    n = max((len(b["texto"]) for b in blocos if b["estilo"] in ("normal", "agilera_est")),
            default=len(tema))

    # MAX_PX real para cálculo de fonte (metade esquerda se tem pessoa)
    max_px_fonte = MAX_PX

    if layout == 2:
        tam_ag = 148 if n <= 8 else 128 if n <= 14 else 108 if n <= 20 else 88 if n <= 28 else 72
    elif layout == 4:
        tam_ag = 100 if n <= 10 else 86 if n <= 16 else 74 if n <= 24 else 62
    else:
        tam_ag = 132 if n <= 6 else 112 if n <= 10 else 96 if n <= 16 else 82 if n <= 24 else 68 if n <= 34 else 56

    # Quando pessoa está presente, reduz fonte para caber na metade esquerda
    if tem_pessoa:
        tam_ag = max(44, int(tam_ag * 0.72))

    # agilera_est é 20% maior — garante destaque claro sobre normal
    # malgun é 52% de tam_ag — hierarquia clara
    tam_ml = max(36, int(tam_ag * 0.52))
    modo = _modo_tipografico(seed)
    print(f"[titulo] modo_tipo={modo}")

    # Fonte AGILERA base com variação de modo
    fa_base, tem_liga_base = _fonte_agilera_para_modo(modo, tam_ag)
    ag_sp = _sp_para_modo(modo, tam_ag)
    fa    = fa_base  # usado para blocos 'normal'
    fb    = f_bold(tam_ml)

    # MALGUN: 3 variações por seed — regular, bold, light
    _malgun_vars = [f_bold(tam_ml), f_corpo(tam_ml), f_light(tam_ml)]
    fb = _malgun_vars[(seed // 6) % 3]

    # Todas as 9 cores da paleta disponíveis para texto
    _paleta_blocos = [
        LARANJA, AMARELO, VERDE_CITRICO, TEAL, VERDE_VIVO,
        BRANCO, VERDE_NEUTRO, PETROLEO, MARINHO,
    ]
    def _cor_b(idx, estilo):
        base = (seed + idx * 4) % 9
        return _paleta_blocos[base]

    # Monta lista de (linhas[], fonte, cor, sp, estilo, cor_rect)
    blocos_render = []
    for idx_b, bloco in enumerate(blocos):
        txt = bloco["texto"].strip()
        est = bloco["estilo"]
        if not txt: continue

        cor_b = _cor_b(idx_b, est)

        if est == "agilera_est":
            # Modo tipográfico aplicado: tamanho 22% maior, fonte e sp do modo
            tam_est = int(tam_ag * 1.22)
            if modo == 5: tam_est = int(tam_est * 0.88)  # modo 5: levemente menor
            fa_est, tem_liga_est = _fonte_agilera_para_modo(modo, tam_est)
            sp_est  = _sp_para_modo(modo, tam_est)
            txt_out = _texto_para_modo(modo, txt)
            lns     = _quebrar(txt_out, fa_est, MAX_PX, sp_est)
            blocos_render.append((lns, fa_est, cor_b, sp_est, est, None, tem_liga_est))

        elif est == "malgun":
            lum_b  = _LUM_COR.get(cor_b, 0.5)
            cor_ml = cor_b if lum_b > 0.42 else BRANCO
            blocos_render.append((_quebrar(txt, fb, MAX_PX), fb, cor_ml, 0, est, None, False))

        elif est == "fundo":
            cor_rect_f = TEAL if (seed % 2 == 0) else LARANJA
            cor_txt_f  = CORES_FUNDO_TEXTO.get(cor_rect_f, MARINHO)
            lns = _quebrar(txt, fb, MAX_PX - 36)
            blocos_render.append((lns, fb, cor_txt_f, 0, est, cor_rect_f, False))

        else:  # normal — modo tipográfico aplicado
            txt_out = _texto_para_modo(modo, txt)
            lns     = _quebrar(txt_out, fa, MAX_PX, ag_sp)
            blocos_render.append((lns, fa, cor_b, ag_sp, est, None, tem_liga_base))

    if not blocos_render:
        return img_rgba.convert("RGB"), layout

    gap_bloco = max(8, int(tam_ag * 0.12))

    # Agrupa blocos consecutivos de mesmo nível (malgun + fundo + malgun)
    # em "linhas compostas" para renderização horizontal coesa
    # Regra: blocos malgun e fundo consecutivos ficam na mesma linha se cabem
    def _agrupar_linhas_compostas(blocos_r, max_px, fb):
        grupos = []
        i = 0
        while i < len(blocos_r):
            lns, fonte, cor, sp, est, cor_rect, tem_liga = blocos_r[i]
            if est in ("malgun", "fundo"):
                grupo = [blocos_r[i]]
                j = i + 1
                while j < len(blocos_r):
                    lns2, f2, c2, sp2, est2, cr2, tl2 = blocos_r[j]
                    if est2 in ("malgun", "fundo"):
                        grupo.append(blocos_r[j])
                        j += 1
                    else:
                        break
                grupos.append(grupo)
                i = j
            else:
                grupos.append([blocos_r[i]])
                i += 1
        return grupos

    grupos = _agrupar_linhas_compostas(blocos_render, MAX_PX, fb)
    h_total = 0
    for grupo in grupos:
        alt = max(int(_altura_linha(f) * 1.10) for _, f, *_ in grupo)
        h_total += alt
    h_total += gap_bloco * max(0, len(grupos) - 1)

    # Zona mínima: 55% da altura — abaixo do rosto em qualquer foto
    Y_MIN_GLOBAL = int(H * 0.55)

    if not tem_pessoa:
        Y_INI_raw = int(H * 0.55)
        Y_FIM_raw = int(H * 0.88)
    else:
        zonas = [
            (int(H * 0.55), int(H * 0.82)),
            (int(H * 0.55), int(H * 0.80)),
            (int(H * 0.57), int(H * 0.84)),
            (int(H * 0.55), int(H * 0.82)),
            (int(H * 0.56), int(H * 0.83)),
        ]
        Y_INI_raw, Y_FIM_raw = zonas[layout % len(zonas)]

    Y_INI = max(Y_MIN_GLOBAL, max(SAFE_TOP, Y_INI_raw))
    Y_FIM = min(SAFE_BOTTOM,  Y_FIM_raw)

    zona = Y_FIM - Y_INI
    y    = Y_INI + max(0, (zona - h_total) // 2)
    y    = max(Y_INI, min(y, Y_FIM - h_total - 8))
    y    = max(SAFE_TOP + 20, min(y, SAFE_BOTTOM - h_total - 20))

    for gi, grupo in enumerate(grupos):
        if gi > 0: y += gap_bloco
        lns0, f0, *_ = grupo[0]
        esp = int(_altura_linha(f0) * 1.10)

        if len(grupo) == 1:
            lns, fonte, cor_txt, sp, est, cor_rect, tem_liga = grupo[0]
            for linha in lns:
                draw = ImageDraw.Draw(img_rgba, "RGBA")
                if est == "fundo":
                    pad_x, pad_y = 18, 10
                    try:
                        bb  = fonte.getbbox(linha)
                        rx1 = MARGIN - pad_x;         ry1 = y + bb[1] - pad_y
                        rx2 = MARGIN + (bb[2]-bb[0]) + pad_x; ry2 = y + bb[3] + pad_y
                    except Exception:
                        rx1 = MARGIN - pad_x;  ry1 = y - pad_y
                        rx2 = MARGIN + _medir(linha, fonte) + pad_x
                        ry2 = y + _altura_linha(fonte) + pad_y
                    draw.rounded_rectangle([(rx1, ry1), (rx2, ry2)],
                                           radius=8, fill=(*(cor_rect or cor_dest), 255))
                    draw = ImageDraw.Draw(img_rgba, "RGBA")
                    _linha(draw, MARGIN, y, linha, fonte, (*cor_txt, 255), 0)
                else:
                    _renderizar_linha_agilera(draw, img_rgba, MARGIN, y, linha,
                                              fonte, cor_txt, sp, tem_liga, sombra_forte)
                y += esp
        else:
            total_w = 0
            esp_entre = 10
            pad_x_fundo = 14
            for lns, fonte, cor_txt, sp, est, cor_rect, tem_liga in grupo:
                linha = lns[0] if lns else ""
                if not linha: continue
                w = _medir_sp(linha, fonte, sp) if sp else _medir(linha, fonte)
                if est == "fundo":
                    total_w += w + pad_x_fundo * 2 + esp_entre
                else:
                    total_w += w + esp_entre

            if total_w > MAX_PX:
                for lns, fonte, cor_txt, sp, est, cor_rect, tem_liga in grupo:
                    for linha in lns:
                        draw = ImageDraw.Draw(img_rgba, "RGBA")
                        if est == "fundo":
                            pad_x, pad_y = 14, 8
                            try:
                                bb  = fonte.getbbox(linha)
                                rx1 = MARGIN - pad_x; ry1 = y + bb[1] - pad_y
                                rx2 = MARGIN + (bb[2]-bb[0]) + pad_x; ry2 = y + bb[3] + pad_y
                            except Exception:
                                rx1 = MARGIN - pad_x; ry1 = y - pad_y
                                rx2 = MARGIN + _medir(linha, fonte) + pad_x
                                ry2 = y + _altura_linha(fonte) + pad_y
                            draw.rounded_rectangle([(rx1, ry1), (rx2, ry2)],
                                                   radius=8, fill=(*(cor_rect or cor_dest), 255))
                            draw = ImageDraw.Draw(img_rgba, "RGBA")
                            _linha(draw, MARGIN, y, linha, fonte, (*cor_txt, 255), 0)
                        else:
                            _renderizar_linha_agilera(draw, img_rgba, MARGIN, y, linha,
                                                      fonte, cor_txt, sp, tem_liga, sombra_forte)
                        y += int(_altura_linha(fonte) * 1.10)
            else:
                x_cursor = MARGIN
                for lns, fonte, cor_txt, sp, est, cor_rect, tem_liga in grupo:
                    linha = lns[0] if lns else ""
                    if not linha: continue
                    w = _medir(linha, fonte)
                    draw = ImageDraw.Draw(img_rgba, "RGBA")
                    if est == "fundo":
                        pad_x, pad_y = pad_x_fundo, 8
                        try:
                            bb  = fonte.getbbox(linha)
                            rx1 = x_cursor - pad_x;     ry1 = y + bb[1] - pad_y
                            rx2 = x_cursor + (bb[2]-bb[0]) + pad_x; ry2 = y + bb[3] + pad_y
                        except Exception:
                            rx1 = x_cursor - pad_x; ry1 = y - pad_y
                            rx2 = x_cursor + w + pad_x; ry2 = y + _altura_linha(fonte) + pad_y
                        draw.rounded_rectangle([(rx1, ry1), (rx2, ry2)],
                                               radius=8, fill=(*(cor_rect or cor_dest), 255))
                        draw = ImageDraw.Draw(img_rgba, "RGBA")
                        _linha(draw, x_cursor, y, linha, fonte, (*cor_txt, 255), 0)
                        x_cursor += w + pad_x * 2 + esp_entre
                    else:
                        _renderizar_linha_agilera(draw, img_rgba, x_cursor, y, linha,
                                                  fonte, cor_txt, sp, tem_liga, sombra_forte)
                        x_cursor += (_medir_sp(linha, fonte, sp) if sp else w) + esp_entre
                y += esp

    return img_rgba.convert("RGB"), layout

# ── Seed variável ─────────────────────────────────────────────────────────────
def _seed_variavel(tema, seed_externo=None):
    """
    Se seed não foi passado, gera um seed que combina hash do tema
    com timestamp em milissegundos → mesmos temas sempre produzem
    cores diferentes a cada geração.
    """
    if seed_externo is not None:
        return int(seed_externo)
    h   = int(hashlib.md5(tema.encode()).hexdigest()[:8], 16)
    ms  = datetime.now().microsecond
    return (h + ms) % 999983  # primo grande para boa distribuição

# ── Geração principal ─────────────────────────────────────────────────────────
def gerar_card_imagem(tema, legenda, imagem_url, pid="", seed=None):
    seed = _seed_variavel(tema, seed)
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
                              cor_overlay=cor_ov_usada,
                              tem_pessoa=tem_pessoa)
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
