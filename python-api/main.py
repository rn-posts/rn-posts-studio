"""
python-api/main.py  —  AlvoreSer Instagram Posts  —  v11

PIPELINE DEFINITIVO
===================
Imagem
  1. Busca Cloudinary pela pasta temática (prioridade) ou geral
  2. Ronilson  → rembg remove fundo → compõe sobre fundo da marca
  3. Editorial → color grade cinematográfico + vinheta + split toning
  4. Fallback  → fundo rico gradiente quando Cloudinary não retorna nada

Overlay
  - Adaptativo: mede a luminosidade da foto e ajusta a intensidade
  - Foto clara  → overlay mais pesado para garantir legibilidade
  - Foto escura → overlay mais leve

Tipografia
  AGILERA → chave / palavra-chave (maiúsculo, cor destaque)
  MALGUN  → complemento / texto explicativo (branco, caixa preservada)
  Separadores que dividem: "e", "são", "é", "como", ":", "—", "-"

Layout (varia por seed — 5 estratégias distintas)
  0 → texto no terço inferior esquerdo  (padrão editorial)
  1 → texto centralizado verticalmente  (poster)
  2 → título enorme no centro-baixo     (impacto)
  3 → texto no terço superior esquerdo  (invertido)
  4 → título à direita                  (assimétrico)

Elementos decorativos (varia por seed — não repetitivos)
  0 → duas linhas sinusoidais finas (topo e base)
  1 → apenas uma linha na base
  2 → linha lateral esquerda
  3 → sem linhas (só a foto e o texto)
  4 → duas linhas + bloco de cor atrás do texto

Preview: base64 local — NÃO sobe ao Cloudinary antes da aprovação
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

# ── rembg (lazy load) ─────────────────────────────────────────────────────────
_rembg_remove = None
def get_rembg():
    global _rembg_remove
    if _rembg_remove is None:
        from rembg import remove as _r
        _rembg_remove = _r
    return _rembg_remove

# ── Flask ─────────────────────────────────────────────────────────────────────
app = Flask(__name__, static_folder="../dist", static_url_path="/")

ALLOWED_ORIGINS = [
    "http://localhost:5173",
    "http://localhost:3000",
    "http://localhost:5000",
    "https://rn-posts.onrender.com",
    "https://alvoreser-python-api.onrender.com",
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
    if not folder:
        return None
    p = os.path.join(os.path.abspath(folder), "index.html")
    return p if os.path.isfile(p) else None

# ── Cloudinary config ─────────────────────────────────────────────────────────
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
# IMPORTANTE: path exato como está no Cloudinary — case-sensitive
PASTA_RONILSON     = "banco de imagens/ronilson"

# ── Paleta AlvoreSer ──────────────────────────────────────────────────────────
MARINHO       = (2,   64,  89)
PETROLEO      = (27,  121, 125)
TEAL          = (4,   157, 191)
VERDE_NEUTRO  = (119, 153, 147)
BRANCO        = (244, 246, 248)
LARANJA       = (249, 171, 11)
VERDE_VIVO    = (122, 181, 0)
VERDE_CITRICO = (146, 204, 29)
AMARELO       = (255, 221, 0)
PRETO         = (20,  20,  20)
PALETA_9      = [MARINHO, PETROLEO, TEAL, VERDE_NEUTRO, BRANCO,
                 LARANJA, VERDE_VIVO, VERDE_CITRICO, AMARELO]

# ── Zona Segura Instagram 4:5 (1012×1230 centralizada em 1080×1350) ──────────
SAFE_LEFT   = 34    # (1080 - 1012) / 2
SAFE_RIGHT  = 1046  # 1080 - 34
SAFE_TOP    = 60    # (1350 - 1230) / 2
SAFE_BOTTOM = 1290  # 1350 - 60
SAFE_W      = 1012  # largura útil
SAFE_H      = 1230  # altura útil
SAFE_MARGIN = SAFE_LEFT + 46  # 80px — margem interna para texto
SAFE_MAX_PX = SAFE_W - 92     # largura máxima do texto (920px)

# ── Sistema de Cores Inteligente ─────────────────────────────────────────────
# Cores vibrantes para destaque sobre overlay escuro (bom contraste):
CORES_DESTAQUE = [
    LARANJA,        # 0 — energia, esperança (identidade principal)
    AMARELO,        # 1 — otimismo, vitalidade
    TEAL,           # 2 — frescor, dinamismo
    VERDE_VIVO,     # 3 — renovação, crescimento
    VERDE_CITRICO,  # 4 — jovialidade, leveza
    BRANCO,         # 5 — leveza, transparência
    VERDE_NEUTRO,   # 6 — natureza, equilíbrio
    LARANJA,        # 7 — (repetição p/ balancear probabilidade)
    AMARELO,        # 8 — (repetição p/ balancear probabilidade)
]

# Cor do texto dentro do highlight (fundo preenchido): precisa ter bom
# contraste com a cor de destaque. Escuros sobre claros, claros sobre escuros.
CORES_FUNDO_TEXTO = {
    LARANJA:       MARINHO,     # texto escuro sobre fundo laranja
    AMARELO:       MARINHO,     # texto escuro sobre fundo amarelo
    TEAL:          BRANCO,      # texto claro sobre fundo teal
    VERDE_VIVO:    MARINHO,     # texto escuro sobre fundo verde
    VERDE_CITRICO: MARINHO,     # texto escuro sobre fundo verde cítrico
    BRANCO:        MARINHO,     # texto escuro sobre fundo branco
    VERDE_NEUTRO:  BRANCO,      # texto claro sobre fundo verde neutro
    PETROLEO:      BRANCO,      # texto claro sobre fundo petróleo
    MARINHO:       BRANCO,      # texto claro sobre fundo marinho
}

def _escolher_cor_destaque(seed):
    """Escolhe cor de destaque usando seed % 9 para rotação completa."""
    idx = seed % len(CORES_DESTAQUE)
    cor = CORES_DESTAQUE[idx]
    cor_fundo_txt = CORES_FUNDO_TEXTO.get(cor, MARINHO)
    return cor, cor_fundo_txt

_cards_pendentes = {}

MAPA_PASTAS = {
    "autismo":        "Banco de Imagens/Autismo",
    "ansiedade":      "Banco de Imagens/Ansiedade e Estresse",
    "estresse":       "Banco de Imagens/Ansiedade e Estresse",
    "burnout":        "Banco de Imagens/Ansiedade e Estresse",
    "depressao":      "Banco de Imagens/Depress\u00e3o",
    "luto":           "Banco de Imagens/Depress\u00e3o",
    "trauma":         "Banco de Imagens/Depress\u00e3o",
    "borderline":     "Banco de Imagens/Borderline",
    "tdah":           "Banco de Imagens/TDAH",
    "terapia":        "Banco de Imagens/Convite e Terapia",
    "acolhimento":    "Banco de Imagens/Acolhimento",
    "familia":        "Banco de Imagens/Acolhimento",
    "relacionamento": "Banco de Imagens/Acolhimento",
    "recomeco":       "Banco de Imagens/Recome\u00e7o e Transforma\u00e7\u00e3o",
    "transformacao":  "Banco de Imagens/Recome\u00e7o e Transforma\u00e7\u00e3o",
}

# ── Fontes ────────────────────────────────────────────────────────────────────
ROOT_DIR   = os.path.join(os.path.dirname(__file__), "..")
_FONTS_DIRS = [
    os.path.join(os.path.dirname(__file__), "fonts"),   # python-api/fonts/ — garantido no Render
    os.path.join(ROOT_DIR, "src", "Brand", "fonts"),    # src/Brand/fonts/  — local
]

def _resolve_font_path(nome):
    low = nome.lower()
    for base in _FONTS_DIRS:
        if not os.path.isdir(base):
            continue
        p = os.path.join(base, nome)
        if os.path.isfile(p):
            return p
        try:
            for f in os.listdir(base):
                if f.lower() == low:
                    return os.path.join(base, f)
        except Exception:
            pass
    return None

def _font(nome, tam):
    p = _resolve_font_path(nome)
    if p:
        try:
            return ImageFont.truetype(p, tam)
        except Exception as e:
            print(f"[font] erro {p}: {e}")
    print(f"[font] FALTANDO: {nome}")
    try:
        return ImageFont.load_default(size=tam)
    except Exception:
        return ImageFont.load_default()

def f_display(t): return _font("AGILERA.OTF",  t)
def f_bold(t):    return _font("MALGUNBD.TTF", t)
def f_corpo(t):   return _font("MALGUN.TTF",   t)
def f_light(t):   return _font("MALGUNSL.TTF", t)

for _fn in ["AGILERA.OTF", "MALGUN.TTF", "MALGUNBD.TTF", "MALGUNSL.TTF"]:
    _p  = _resolve_font_path(_fn)
    print(f"[font] {'OK  ' if _p else 'MISS'} {_fn}" + (f" => {_p}" if _p else " <= FALTANDO!"))

# Verifica suporte RAQM (ativa liga+aalt na AGILERA estilizada)
_RAQM_OK = False
try:
    from PIL import features as _pil_features
    _RAQM_OK = _pil_features.check("raqm")
except Exception:
    pass
print(f"[raqm] {'disponivel' if _RAQM_OK else 'indisponivel'}")

import tempfile as _tempfile
_AGILERA_EST_PATH = None  # cache da fonte ornamental
_LIGA_SUBST       = {}    # cache: {"ra": "\uE000", ...} — substituições de texto
_PUA_START        = 0xE000

def _preparar_fonte_estilizada():
    """
    Usa fonttools para criar uma versão ornamental da AGILERA:
    1. Aplica aalt — glifos ornamentais como padrão
    2. Mapeia ligaturas (liga) para caracteres PUA (U+E000+)
       para que sejam renderáveis sem RAQM via substituição de texto
    Resultados cacheados em globais.
    """
    global _AGILERA_EST_PATH, _LIGA_SUBST
    if _AGILERA_EST_PATH and os.path.isfile(_AGILERA_EST_PATH):
        return _AGILERA_EST_PATH
    fonte_path = _resolve_font_path("AGILERA.OTF")
    if not fonte_path:
        return None
    try:
        from fonttools import ttLib
        font = ttLib.TTFont(fonte_path)
        if "GSUB" not in font:
            return None
        gsub = font["GSUB"].table

        # ── 1. Coleta aalt (Single=1, Alternate=3) ──
        aalt_subst = {}
        for feat in gsub.FeatureList.FeatureRecord:
            if feat.FeatureTag != "aalt":
                continue
            for idx in feat.Feature.LookupListIndex:
                lk = gsub.LookupList.Lookup[idx]
                if lk.LookupType == 1:
                    for sub in lk.SubTable:
                        for g, alt in sub.mapping.items():
                            if g not in aalt_subst:
                                aalt_subst[g] = alt
                elif lk.LookupType == 3:
                    for sub in lk.SubTable:
                        for g, alts in sub.alternates.items():
                            if g not in aalt_subst and alts:
                                aalt_subst[g] = alts[0]

        # ── 2. Coleta liga (LookupType 4) ──
        cmap     = font.getBestCmap() or {}
        rev_cmap = {v: k for k, v in cmap.items()}  # glyph_name → char_code
        liga_glyphs = {}   # seq_str → liga_glyph_name
        for feat in gsub.FeatureList.FeatureRecord:
            if feat.FeatureTag != "liga":
                continue
            for idx in feat.Feature.LookupListIndex:
                lk = gsub.LookupList.Lookup[idx]
                if lk.LookupType != 4:
                    continue
                for sub in lk.SubTable:
                    for first_g, ligs in sub.ligatures.items():
                        for lig in ligs:
                            seq_glyphs = [first_g] + list(lig.Component)
                            seq_chars  = ""
                            ok = True
                            for g in seq_glyphs:
                                if g in rev_cmap:
                                    seq_chars += chr(rev_cmap[g])
                                else:
                                    ok = False; break
                            if ok and len(seq_chars) > 1:
                                liga_glyphs[seq_chars] = lig.LigGlyph
        print(f"[liga] {len(liga_glyphs)} pares: {list(liga_glyphs.keys())}")

        # ── 3. Mapeia ligaduras para PUA ──
        pua = _PUA_START
        text_subst = {}
        for seq, liga_glyph in liga_glyphs.items():
            for tbl in font["cmap"].tables:
                if tbl.format in (4, 12):
                    tbl.cmap[pua] = liga_glyph
            text_subst[seq] = chr(pua)
            pua += 1

        # ── 4. Aplica aalt no cmap ──
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
        print(f"[font_est] fonttools falhou: {e}")
        return None

def _aplicar_ligaturas(texto):
    """Substitui sequências de texto por caracteres PUA de ligatura."""
    if not _LIGA_SUBST:
        return texto
    # Ordena do mais longo para o mais curto (evita conflitos)
    for seq in sorted(_LIGA_SUBST, key=len, reverse=True):
        texto = texto.replace(seq, _LIGA_SUBST[seq])
    return texto

def f_display_est(t):
    """
    AGILERA estilizada:
    1. fonttools: aalt + liga via PUA
    2. RAQM fallback
    3. Tamanho maior como último recurso
    """
    est_path = _preparar_fonte_estilizada()
    if est_path:
        try:
            return ImageFont.truetype(est_path, t)
        except Exception as e:
            print(f"[font_est] erro ao carregar ornamental: {e}")
    p = _resolve_font_path("AGILERA.OTF")
    if p:
        if _RAQM_OK:
            try:
                return ImageFont.truetype(p, t, layout_engine=ImageFont.Layout.RAQM)
            except Exception:
                pass
        try:
            return ImageFont.truetype(p, t)
        except Exception:
            pass
    try:
        return ImageFont.load_default(size=t)
    except Exception:
        return ImageFont.load_default()

def _linha_est(draw, x, y, texto, fonte, cor):
    """Renderiza com liga+aalt se RAQM disponivel, caso contrario normal."""
    if _RAQM_OK:
        try:
            draw.text((x, y), texto, font=fonte, fill=cor, features=["liga", "aalt"])
            return
        except Exception:
            pass
    draw.text((x, y), texto, font=fonte, fill=cor)

# ── IA ────────────────────────────────────────────────────────────────────────
ASSINATURA = (
    "\n\n\U0001f468\u200d\U0001f4bc Ronilson Nogueira\n"
    "\u270d\ufe0f Psic\u00f3logo e Professor\n"
    "\U0001f9e9 Refer\u00eancia em Autismo e TDAH\n"
    "CRP 04/57327"
)
PROMPT_LEGENDA = (
    "Crie uma legenda para um post do Instagram sobre: '{tema}'. "
    "Para o psic\u00f3logo Ronilson Nogueira, especialista em Autismo e TDAH, "
    "da cl\u00ednica AlvoreSer em Coronel Fabriciano/MG. "
    "Tom: acolhedor, humano, reflexivo, n\u00e3o-cl\u00ednico, para o p\u00fablico geral. "
    "M\u00e1ximo 150 palavras. N\u00e3o inclua hashtags. "
    "Retorne APENAS o texto da legenda, sem explica\u00e7\u00f5es ou markdown."
)
GROQ_MODELOS = ["llama-3.3-70b-versatile", "llama-3.1-8b-instant", "llama-4-scout"]

def _groq_legenda(tema):
    if not GROQ_API_KEY:
        raise Exception("GROQ_API_KEY nao configurada")
    ultimo = None
    for m in GROQ_MODELOS:
        try:
            r = requests.post(GROQ_URL,
                headers={"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"},
                json={"model": m, "messages": [{"role": "user", "content": PROMPT_LEGENDA.format(tema=tema)}], "max_tokens": 400},
                timeout=20)
            r.raise_for_status()
            return r.json()["choices"][0]["message"]["content"].strip()
        except Exception as e:
            ultimo = e
    raise Exception(f"Groq falhou: {ultimo}")

def _gemini_legenda(tema):
    if not GEMINI_API_KEY:
        raise Exception("GEMINI_API_KEY nao configurada")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GEMINI_API_KEY}"
    r = requests.post(url, json={"contents": [{"parts": [{"text": PROMPT_LEGENDA.format(tema=tema)}]}]}, timeout=25)
    if r.status_code == 429:
        raise Exception("Gemini 429")
    r.raise_for_status()
    return r.json()["candidates"][0]["content"]["parts"][0]["text"].strip()

def gerar_legenda_ia(tema):
    erros = []
    for fn in [_groq_legenda, _gemini_legenda]:
        try:
            return fn(tema) + ASSINATURA
        except Exception as e:
            erros.append(str(e))
    raise Exception("IAs falharam: " + " | ".join(erros))

# ── Cloudinary ────────────────────────────────────────────────────────────────
def buscar_imagem(tema=""):
    t     = tema.lower()
    todas = list(set(MAPA_PASTAS.values()))
    pasta = next((MAPA_PASTAS[k] for k in MAPA_PASTAS if k in t), None)
    if pasta:
        todas = [pasta] + [p for p in todas if p != pasta]
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
        except Exception as e:
            print(f"[busca] pasta '{p}': {e}")
    try:
        res = cloudinary.api.resources(type="upload", max_results=50)
        rec = [r for r in res.get("resources", [])
               if CLOUDINARY_POSTS not in r.get("public_id", "")
               and CLOUDINARY_PREVIEW not in r.get("public_id", "")]
        if rec:
            c = random.choice(rec)
            print(f"[busca] fallback: {c.get('public_id')}")
            return c.get("secure_url"), c.get("public_id", "")
    except Exception as e:
        print(f"[busca] fallback erro: {e}")
    print("[busca] sem imagem")
    return None, ""

# ── Utilitários ───────────────────────────────────────────────────────────────
def _medir(texto, fonte):
    try:
        bb = fonte.getbbox(texto)
        return bb[2] - bb[0]
    except Exception:
        return len(texto) * 30

def _medir_sp(texto, fonte, sp):
    total = 0
    for ch in texto:
        try:
            bb = fonte.getbbox(ch)
            total += (bb[2] - bb[0]) + sp
        except Exception:
            total += 30 + sp
    return max(0, total - sp)

def _altura_linha(fonte, texto="Ag"):
    try:
        bb = fonte.getbbox(texto)
        return bb[3] - bb[1]
    except Exception:
        return 50

def _quebrar(texto, fonte, max_px, sp=0):
    palavras = texto.split()
    linhas, atual = [], []
    for p in palavras:
        cand = " ".join(atual + [p])
        w = _medir_sp(cand, fonte, sp) if sp else _medir(cand, fonte)
        if w <= max_px:
            atual.append(p)
        else:
            if atual:
                linhas.append(" ".join(atual))
            atual = [p]
    if atual:
        linhas.append(" ".join(atual))
    return linhas or [texto]

def distancia_cor(c1, c2):
    return sum((a - b)**2 for a, b in zip(c1, c2)) ** 0.5

def cores_fundo(img):
    p   = list(img.resize((60, 75), Image.Resampling.LANCZOS).convert("RGB").getdata())
    cf  = tuple(sum(x[i] for x in p) // len(p) for i in range(3))
    ord_ = sorted([c for c in PALETA_9 if c != LARANJA],
                  key=lambda c: distancia_cor(cf, c), reverse=True)
    return (MARINHO, PETROLEO) if sum(cf) / 3 < 60 else (ord_[0], ord_[1])

def luminosidade_media(img):
    """Retorna a luminosidade média da imagem (0–255)."""
    arr = np.array(img.convert("RGB").resize((80, 100))).astype(np.float32)
    return float(arr.mean())

def eh_foto_ronilson(pid):
    """
    Detecta fotos do Ronilson comparando o public_id de forma case-insensitive.
    O path no Cloudinary pode ser 'banco de imagens/ronilson/...'
    """
    pid_low = pid.lower().replace("\\", "/")
    return "ronilson" in pid_low

def remover_fundo_rembg(img):
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    resultado = get_rembg()(buf.getvalue())
    return Image.open(io.BytesIO(resultado)).convert("RGBA")

# ── Fundo rico (fallback) ─────────────────────────────────────────────────────
def gerar_fundo_rico(cor1, cor2, seed):
    rng = random.Random(seed)
    arr = np.zeros((H, W, 3), dtype=np.float32)
    for y in range(H):
        t = y / H
        for ch in range(3):
            arr[y, :, ch] = cor1[ch] * (1 - t) + cor2[ch] * t
    cx = W * rng.uniform(0.30, 0.70)
    cy = H * rng.uniform(0.10, 0.35)
    ys, xs = np.ogrid[:H, :W]
    dist2 = ((xs - cx) / (W * 0.55))**2 + ((ys - cy) / (H * 0.45))**2
    luz = np.exp(-dist2 * 1.2) * rng.uniform(20, 35)
    arr[:, :, 0] = np.clip(arr[:, :, 0] + luz,       0, 255)
    arr[:, :, 1] = np.clip(arr[:, :, 1] + luz * 0.8, 0, 255)
    arr[:, :, 2] = np.clip(arr[:, :, 2] + luz * 0.6, 0, 255)
    ruido = np.random.RandomState(seed).normal(0, 4, (H, W, 3))
    arr   = np.clip(arr + ruido, 0, 255).astype(np.uint8)
    return Image.fromarray(arr).filter(ImageFilter.GaussianBlur(1))

# ── Elementos decorativos (variáveis por seed) ────────────────────────────────
def adicionar_elementos_decorativos(img, cor_acento, seed):
    """
    5 estratégias decorativas diferentes, escolhidas pela seed.
    Nenhuma domina o card — são acentos da identidade visual.
    """
    estrategia = seed % 5
    rng  = random.Random(seed)
    rgba = img.convert("RGBA")
    draw = ImageDraw.Draw(rgba, "RGBA")
    opac = rng.randint(35, 60)

    def linha_seno(base_frac, cor, opacidade, largura=5):
        base_y = H * base_frac
        amp    = H * rng.uniform(0.02, 0.045)
        fase   = rng.uniform(0, math.pi * 2)
        pts    = [(x, int(base_y + amp * math.sin(x / W * math.pi * 1.5 + fase)))
                  for x in range(0, W + 1, 4)]
        if len(pts) > 1:
            draw.line(pts, fill=(*cor, opacidade), width=largura)

    if estrategia == 0:
        # Duas linhas sinusoidais (topo + base)
        linha_seno(rng.uniform(0.03, 0.06), cor_acento, opac)
        linha_seno(rng.uniform(0.93, 0.97), cor_acento, opac)

    elif estrategia == 1:
        # Apenas base
        linha_seno(rng.uniform(0.92, 0.96), cor_acento, opac + 10, largura=6)

    elif estrategia == 2:
        # Linha lateral esquerda vertical
        x_lat = int(W * rng.uniform(0.04, 0.07))
        y0    = int(H * 0.08)
        y1    = int(H * 0.92)
        amp   = W * rng.uniform(0.008, 0.018)
        pts   = [(int(x_lat + amp * math.sin(y / H * math.pi * 3 + rng.uniform(0, math.pi))), y)
                 for y in range(y0, y1, 4)]
        if len(pts) > 1:
            draw.line(pts, fill=(*cor_acento, opac), width=5)

    elif estrategia == 3:
        # Sem linhas — só foto + texto (clean)
        pass

    else:  # 4
        # Duas linhas mais grossas + bloco translúcido na borda esquerda
        linha_seno(rng.uniform(0.03, 0.06), cor_acento, opac, largura=7)
        linha_seno(rng.uniform(0.93, 0.97), cor_acento, opac, largura=7)
        draw.rectangle([(0, 0), (int(W * 0.008), H)],
                       fill=(*cor_acento, opac + 20))

    return rgba.convert("RGB")

# ── Color grade editorial ─────────────────────────────────────────────────────
def color_grade_editorial(img, seed):
    rng = random.Random(seed)
    arr = np.array(img.convert("RGB")).astype(np.float32)
    lum = arr.mean(axis=2, keepdims=True) / 255.0
    # Sombras frias (harmoniza MARINHO)
    mask_s = np.clip(1.0 - lum * 2.5, 0, 1)
    arr[:, :, 0] *= 1 + (0.92 - 1) * mask_s[:, :, 0]
    arr[:, :, 1] *= 1 + (0.96 - 1) * mask_s[:, :, 0]
    arr[:, :, 2] *= 1 + (1.06 - 1) * mask_s[:, :, 0]
    # Meio-tons quentes (harmoniza LARANJA)
    mask_m = np.clip(1.0 - abs(lum - 0.45) * 4, 0, 1)
    arr[:, :, 0] = np.clip(arr[:, :, 0] + 6 * mask_m[:, :, 0], 0, 255)
    arr[:, :, 1] = np.clip(arr[:, :, 1] + 3 * mask_m[:, :, 0], 0, 255)
    arr[:, :, 2] = np.clip(arr[:, :, 2] - 4 * mask_m[:, :, 0], 0, 255)
    # Grain
    grain = np.random.RandomState(seed + 1).normal(0, rng.uniform(2.5, 4.5), arr.shape)
    arr   = np.clip(arr + grain, 0, 255)
    out   = Image.fromarray(arr.astype(np.uint8))
    # Unsharp mask leve
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

def aplicar_vinheta(img, seed):
    rng    = random.Random(seed)
    intens = rng.uniform(0.28, 0.44)
    mw, mh = max(1, W // 6), max(1, H // 6)
    cx, cy = mw / 2, mh / 2
    pixels = []
    for y in range(mh):
        for x in range(mw):
            dx = (x - cx) / cx; dy = (y - cy) / cy
            d  = math.sqrt(dx*dx + dy*dy)
            fade = max(0.0, d - 0.50) / 0.50
            pixels.append(max(0, min(255, int((1 - (fade**1.6) * intens) * 255))))
    mask = Image.new("L", (mw, mh))
    mask.putdata(pixels)
    mask = mask.resize((W, H), Image.Resampling.BICUBIC).filter(ImageFilter.GaussianBlur(80))
    r, g, b = img.convert("RGB").split()
    return Image.merge("RGB", [ImageChops.multiply(r, mask),
                                ImageChops.multiply(g, mask),
                                ImageChops.multiply(b, mask)])

def tratar_foto_editorial(img, cor_paleta, seed):
    img = color_grade_editorial(img, seed)
    img = ImageEnhance.Contrast(img).enhance(1.15)
    img = ImageEnhance.Color(img).enhance(1.10)
    img = ImageEnhance.Sharpness(img).enhance(1.18)
    img = ImageEnhance.Brightness(img).enhance(1.02)
    img = aplicar_split_toning(img)
    img = aplicar_vinheta(img, seed)
    return img

# ── Composição Ronilson ────────────────────────────────────────────────────────
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

# ── preparar_foto ─────────────────────────────────────────────────────────────
def preparar_foto(url, pid, cor1, cor2, seed):
    try:
        r = requests.get(url, timeout=25)
        r.raise_for_status()
        img   = Image.open(io.BytesIO(r.content)).convert("RGB")
        ratio = max(W / img.width, H / img.height)
        nw, nh = int(img.width * ratio), int(img.height * ratio)
        img   = img.resize((nw, nh), Image.Resampling.LANCZOS)
        l     = (nw - W) // 2; t = (nh - H) // 2
        img   = img.crop((l, t, l + W, t + H))

        if eh_foto_ronilson(pid):
            print(f"[foto] Ronilson detectado — aplicando rembg: {pid}")
            fundo  = gerar_fundo_rico(cor1, cor2, seed)
            try:
                rgba = remover_fundo_rembg(img)
                img  = compor_pessoa(rgba, fundo)
                img  = aplicar_split_toning(img)
                img  = ImageEnhance.Contrast(img).enhance(1.08)
                print("[foto] rembg OK")
            except Exception as e:
                print(f"[foto] rembg falhou ({e}) — blend suave")
                img = Image.blend(fundo, img, alpha=0.60)
                img = aplicar_split_toning(img)
        else:
            print(f"[foto] editorial: {pid}")
            img = tratar_foto_editorial(img, cor1, seed)

        return img
    except Exception as e:
        print(f"[foto] ERRO: {e}")
        return None

# ── Overlay adaptativo ────────────────────────────────────────────────────────
def aplicar_overlay(img, lum_media, layout):
    """
    Overlay adaptativo:
    - Foto clara (lum > 140) → overlay mais intenso
    - Foto escura (lum < 80) → overlay mais suave
    - Ajuste de altura baseado no layout (texto em cima = overlay no topo tbm)
    """
    # Intensidade adaptativa
    if lum_media > 160:
        alpha_max = 215
    elif lum_media > 120:
        alpha_max = 190
    elif lum_media > 80:
        alpha_max = 165
    else:
        alpha_max = 140

    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw    = ImageDraw.Draw(overlay)

    if layout == 3:
        # Texto no topo → overlay no topo também
        altura = int(H * 0.42)
        for y in range(altura):
            prog  = 1.0 - y / altura
            alpha = int((prog ** 1.5) * alpha_max)
            draw.line([(0, y), (W, y)], fill=(*MARINHO, alpha))
    else:
        # Overlay padrão na base (cobre zona do texto)
        altura = int(H * 0.50)
        for y in range(altura):
            prog  = y / altura
            alpha = int((prog ** 1.4) * alpha_max)
            draw.line([(0, H - altura + y), (W, H - altura + y)],
                      fill=(*MARINHO, alpha))

    return Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")

# ── Tipografia ────────────────────────────────────────────────────────────────
#
# MODO AUTOMÁTICO (tema sem \n):
#   Divide na primeira ocorrência de separadores naturais ("e", "são", "é", etc.)
#   Primeira parte → AGILERA (título, maiúsculo, cor destaque)
#   Segunda parte  → MALGUN (complemento, branco)
#
# MODO MANUAL (tema com \n — linhas separadas):
#   Cada linha tem um símbolo de controle no início:
#   (sem símbolo) → AGILERA normal, branco
#   *             → AGILERA estilizada (letter-spacing expandido), cor destaque
#   :             → MALGUN bold, branco
#   -             → AGILERA com fundo preenchido (highlight)

SEPARADORES = [" e ", " s\u00e3o ", " \u00e9 ", " como ", ": ", " \u2014 ", " - "]

def _split_tema(tema):
    """Modo automático: divide em (chave, complemento) pelos separadores naturais."""
    t = tema.strip()
    for sep in SEPARADORES:
        idx = t.lower().find(sep.lower())
        if idx > 0:
            return t[:idx].strip(), t[idx:].strip()
    return t, ""

import re as _re

def _parse_inline(tema):
    """
    Analisa o tema com símbolos inline — funciona em linha única OU com \\n.

    Símbolos (no início de uma palavra ou sozinhos):
      (sem símbolo)  → AGILERA normal, caixa preservada
      *palavra       → AGILERA estilizada (letter-spacing expandido, cor destaque)
      :palavra       → MALGUN bold, branco
      -palavra       → AGILERA com fundo preenchido (highlight)

    Também interpreta ':' sozinho após uma palavra como abertura de segmento malgun:
      "*Generalizada: Uma desordem" → agilera_est:"Generalizada" + malgun:"Uma desordem"

    Caixa das letras é SEMPRE preservada como digitada.
    """
    MAPA = {"*": "agilera_est", ":": "malgun", "-": "fundo"}

    # Junta todas as linhas em uma só (suporte a multiline via \n)
    texto = " ".join(l.strip() for l in tema.split("\n") if l.strip())

    # "palavra: " (trailing colon) → "palavra : " para virar separador standalone
    texto = _re.sub(r'(\S):\s+', r'\1 : ', texto)

    tokens = texto.split()
    segmentos = []
    estilo_atual = "normal"
    palavras_atual = []

    for token in tokens:
        if token in MAPA:
            # Símbolo standalone (ex: ":" isolado)
            if palavras_atual:
                segmentos.append({"texto": " ".join(palavras_atual), "estilo": estilo_atual})
                palavras_atual = []
            estilo_atual = MAPA[token]
        elif len(token) > 1 and token[0] in MAPA:
            # Símbolo no início do token (ex: "*Generalizada", ":Uma")
            if palavras_atual:
                segmentos.append({"texto": " ".join(palavras_atual), "estilo": estilo_atual})
                palavras_atual = []
            estilo_atual = MAPA[token[0]]
            palavras_atual = [token[1:]]
        else:
            palavras_atual.append(token)

    if palavras_atual:
        segmentos.append({"texto": " ".join(palavras_atual), "estilo": estilo_atual})

    # Se não encontrou nenhum símbolo, usa modo automático (_split_tema)
    tem_simbolo = any(s["estilo"] != "normal" for s in segmentos)
    if not tem_simbolo:
        chave, comp = _split_tema(tema.strip())
        resultado = [{"texto": chave, "estilo": "normal"}]
        if comp:
            resultado.append({"texto": comp, "estilo": "malgun"})
        return resultado

    return segmentos or [{"texto": tema.strip(), "estilo": "normal"}]

def _parse_segmentos(tema):
    """
    Modo manual (tema com \\n).
    Retorna lista de dicts: [{"texto": str, "estilo": str}, ...]
    Estilos: "normal" | "agilera_est" | "malgun" | "fundo"
    """
    segmentos = []
    for linha in tema.split("\n"):
        l = linha.strip()
        if not l:
            continue
        if l.startswith("*"):
            txt = l[1:].strip()
            if txt:
                segmentos.append({"texto": txt, "estilo": "agilera_est"})
        elif l.startswith(":"):
            txt = l[1:].strip()
            if txt:
                segmentos.append({"texto": txt, "estilo": "malgun"})
        elif l.startswith("-"):
            txt = l[1:].strip()
            if txt:
                segmentos.append({"texto": txt, "estilo": "fundo"})
        else:
            segmentos.append({"texto": l, "estilo": "normal"})
    return segmentos if segmentos else [{"texto": tema.strip(), "estilo": "normal"}]

def _sombra(img_rgba, texto, fonte, x, y, sp=0):
    for (ox, oy), blur, opac in [((6, 8), 18, 0.42), ((2, 3), 3, 0.68)]:
        layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        d     = ImageDraw.Draw(layer)
        _linha(d, x + ox, y + oy, texto, fonte, (2, 20, 30, int(255 * opac)), sp)
        layer = layer.filter(ImageFilter.GaussianBlur(blur))
        img_rgba.paste(layer, (0, 0), layer)

def _linha(draw, x, y, texto, fonte, cor, sp=0):
    if sp == 0:
        draw.text((x, y), texto, font=fonte, fill=cor)
        return
    cursor = x
    for ch in texto:
        draw.text((cursor, y), ch, font=fonte, fill=cor)
        try:
            bb = fonte.getbbox(ch)
            cursor += (bb[2] - bb[0]) + sp
        except Exception:
            cursor += 30 + sp

def desenhar_titulo(img, tema, seed):
    """
    Usa _parse_inline — funciona em linha única OU multiline com \\n.
    Caixa das letras SEMPRE preservada como digitada. Sem .upper() forçado.
    5 layouts por seed % 5.
    
    ZONA SEGURA: Todo texto fica dentro de 1012×1230px centralizado.
    CORES: Rotação inteligente das 9 cores da paleta AlvoreSer.
    """
    img_rgba = img.convert("RGBA")
    MARGIN   = SAFE_MARGIN   # 80px (dentro da zona segura)
    MAX_PX   = SAFE_MAX_PX   # 920px (largura útil)
    layout   = seed % 5
    
    # ── Cor de destaque rotativa (9 cores da paleta) ──
    cor_dest, cor_fundo_txt = _escolher_cor_destaque(seed)
    print(f"[titulo] cor_dest=RGB{cor_dest} cor_fundo_txt=RGB{cor_fundo_txt}")

    segmentos = _parse_inline(tema)
    print(f"[titulo] layout={layout} segs={[(s['estilo'],s['texto'][:18]) for s in segmentos]}")

    # Tamanho pelo segmento AGILERA mais longo
    textos_ag = [s["texto"] for s in segmentos if s["estilo"] in ("normal","agilera_est","fundo")]
    n = max((len(t) for t in textos_ag), default=len(tema))
    if layout == 2:
        tam_ag = 160 if n<=8 else 140 if n<=14 else 118 if n<=20 else 96 if n<=28 else 78
    else:
        tam_ag = 148 if n<=6 else 128 if n<=10 else 108 if n<=16 else 90 if n<=24 else 76 if n<=34 else 64

    tam_ml    = max(44, int(tam_ag*0.58))
    ag_sp     = -3 if tam_ag >= 100 else -2
    ag_est_sp = max(4, int(tam_ag*0.06))
    fa = f_display(tam_ag); fm = f_corpo(tam_ml); fb = f_bold(tam_ml)

    blocos = []
    for seg in segmentos:
        txt = seg["texto"].strip(); est = seg["estilo"]
        if not txt: continue
        if est == "agilera_est":
            tam_est = int(tam_ag * 1.38)
            fa_est  = f_display_est(tam_est)
            txt_lig = _aplicar_ligaturas(txt)
            lns     = _quebrar(txt_lig, fa_est, MAX_PX, ag_sp)
            blocos.append((lns, fa_est, cor_dest, ag_sp, est))
        elif est == "malgun":
            blocos.append((_quebrar(txt, fb, MAX_PX), fb, BRANCO, 0, est))
        elif est == "fundo":
            blocos.append((_quebrar(txt, fb, MAX_PX - 48), fb, cor_fundo_txt, 0, est))
        else:  # normal — caixa preservada, sem .upper()
            blocos.append((_quebrar(txt, fa, MAX_PX, ag_sp), fa, BRANCO, ag_sp, est))

    if not blocos: return img_rgba.convert("RGB"), layout

    gap_bloco = max(10, int(tam_ag*0.12))
    h_bloco   = sum(int(_altura_linha(f)*1.10)*len(ls) for ls,f,*_ in blocos) + gap_bloco*max(0,len(blocos)-1)

    # ── Layouts dentro da ZONA SEGURA ──
    # Todos os Y_INI e Y_FIM ficam dentro de [SAFE_TOP, SAFE_BOTTOM]
    if layout==0:   Y_INI,Y_FIM = max(SAFE_TOP, int(H*0.58)), min(SAFE_BOTTOM, int(H*0.90))
    elif layout==1: Y_INI,Y_FIM = max(SAFE_TOP, int(H*0.55)), min(SAFE_BOTTOM, int(H*0.88))
    elif layout==2: Y_INI,Y_FIM = max(SAFE_TOP, int(H*0.62)), min(SAFE_BOTTOM, int(H*0.92))
    elif layout==3: Y_INI,Y_FIM = max(SAFE_TOP, int(H*0.08)), min(SAFE_BOTTOM, int(H*0.38))
    else:           Y_INI,Y_FIM = max(SAFE_TOP, int(H*0.56)), min(SAFE_BOTTOM, int(H*0.89))

    zona = Y_FIM - Y_INI
    y    = Y_INI + max(0,(zona-h_bloco)//2)
    y    = max(Y_INI, min(y, Y_FIM-h_bloco-10))
    # Garantia final: nunca ultrapassar zona segura
    y    = max(SAFE_TOP, min(y, SAFE_BOTTOM - h_bloco))

    for bi,(lns,fonte,cor,sp,est) in enumerate(blocos):
        if bi > 0: y += gap_bloco
        esp = int(_altura_linha(fonte)*1.10)
        for linha in lns:
            draw = ImageDraw.Draw(img_rgba,"RGBA")
            if est == "fundo":
                pad_x, pad_y = 16, 10
                try:
                    bb = fonte.getbbox(linha)
                    rect_x1 = MARGIN - pad_x
                    rect_y1 = y + bb[1] - pad_y
                    rect_x2 = MARGIN + (bb[2] - bb[0]) + pad_x
                    rect_y2 = y + bb[3] + pad_y
                except Exception:
                    rect_x1 = MARGIN - pad_x
                    rect_y1 = y - pad_y
                    rect_x2 = MARGIN + _medir(linha, fonte) + pad_x
                    rect_y2 = y + _altura_linha(fonte, linha) + pad_y
                draw.rounded_rectangle(
                    [(rect_x1, rect_y1),(rect_x2, rect_y2)],
                    radius=8, fill=(*cor_dest, 255))
                draw = ImageDraw.Draw(img_rgba, "RGBA")
                _linha(draw, MARGIN, y, linha, fonte, (*cor_fundo_txt, 255), 0)
            else:
                _sombra(img_rgba,linha,fonte,MARGIN,y,sp)
                draw = ImageDraw.Draw(img_rgba,"RGBA")
                if est == "agilera_est":
                    _linha_est(draw, MARGIN, y, linha, fonte, (*cor, 255))
                else:
                    _linha(draw,MARGIN,y,linha,fonte,(*cor,255),sp)
            y += esp

    return img_rgba.convert("RGB"), layout

# ── Geração principal ─────────────────────────────────────────────────────────
def gerar_card_imagem(tema, legenda, imagem_url, pid="", seed=None):
    if seed is None:
        seed = random.randint(0, 999999)
    print(f"[card] tema='{tema}' seed={seed} layout={seed % 5} decore={seed % 5} cloudinary={'sim' if imagem_url else 'NAO'}")

    cor1, cor2  = MARINHO, PETROLEO
    lum_media   = 100.0  # valor neutro default

    if imagem_url:
        try:
            r = requests.get(imagem_url, timeout=15)
            r.raise_for_status()
            tmp       = Image.open(io.BytesIO(r.content)).convert("RGB").resize((120, 150), Image.Resampling.LANCZOS)
            cor1, cor2 = cores_fundo(tmp)
            lum_media  = luminosidade_media(tmp)
        except Exception as e:
            print(f"[cor] {e}")

    # Base visual
    if imagem_url:
        base = preparar_foto(imagem_url, pid, cor1, cor2, seed)
        if base is None:
            print("[card] foto falhou — fundo rico")
            base = gerar_fundo_rico(cor1, cor2, seed)
            lum_media = luminosidade_media(base)
    else:
        print("[card] sem imagem — fundo rico")
        base = gerar_fundo_rico(cor1, cor2, seed)
        lum_media = luminosidade_media(base)

    # Layout (precisamos saber antes para passar ao overlay)
    layout = seed % 5

    # Overlay adaptativo
    base = aplicar_overlay(base, lum_media, layout)

    # Título
    base, _ = desenhar_titulo(base, tema, seed)
    return base

# ── Planilha / Upload ─────────────────────────────────────────────────────────
def upload_imagem(img, folder, public_id):
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=93)
    buf.seek(0)
    try:
        res = cloudinary.uploader.upload(buf, public_id=public_id, folder=folder,
                                         overwrite=True, resource_type="image")
        return res.get("secure_url", "")
    except Exception as e:
        print(f"[upload] ERRO: {e}")
        return ""

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
    try:
        return int(res["updates"]["updatedRange"].split("!A")[1].split(":")[0])
    except Exception:
        return 0

def atualizar_status(linha, status):
    get_sheets().spreadsheets().values().update(
        spreadsheetId=SPREADSHEET_ID, range=f"G{linha}",
        valueInputOption="RAW", body={"values": [[status]]}).execute()

# ── Rotas ─────────────────────────────────────────────────────────────────────
def _env_first(*keys):
    for key in keys:
        val = os.getenv(key)
        if val and str(val).strip():
            return str(val).strip()
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
        return jsonify({"erro": "Firebase nao configurado.",
                        "dica": "Adicione FIREBASE_API_KEY no Render."}), 503
    return jsonify(cfg)

@app.route("/health", methods=["GET"])
def health():
    fontes   = {fn: _resolve_font_path(fn) is not None
                for fn in ["AGILERA.OTF", "MALGUN.TTF", "MALGUNBD.TTF", "MALGUNSL.TTF"]}
    caminhos = {fn: _resolve_font_path(fn) or "FALTANDO"
                for fn in ["AGILERA.OTF", "MALGUN.TTF", "MALGUNBD.TTF", "MALGUNSL.TTF"]}
    # NAO chamar get_rembg() aqui — importa numba/onnxruntime, JIT compile > 120s mata o worker
    return jsonify({
        "status": "ok", "dimensoes": f"{W}x{H}",
        "fontes": fontes, "caminhos": caminhos,
        "raqm": _RAQM_OK,
        "liga_count": len(_LIGA_SUBST),
        "ronilson_path": PASTA_RONILSON,
    })

@app.route("/gerar-legenda", methods=["POST"])
def rota_gerar_legenda():
    data = request.get_json() or {}
    tema = data.get("tema", "").strip()
    if not tema:
        return jsonify({"erro": "Tema obrigatorio"}), 400
    try:
        return jsonify({"legenda": gerar_legenda_ia(tema)})
    except Exception as e:
        return jsonify({"erro": str(e)}), 500

@app.route("/preview-card", methods=["POST"])
def rota_preview_card():
    data    = request.get_json() or {}
    tema    = data.get("tema",    "").strip()
    legenda = data.get("legenda", "").strip()
    if not tema:
        return jsonify({"erro": "Tema obrigatorio"}), 400

    erros_leg = None
    if not legenda:
        try:
            legenda = gerar_legenda_ia(tema)
        except Exception as e:
            erros_leg = str(e); legenda = ""
    if legenda and "CRP 04/57327" not in legenda:
        legenda = legenda.rstrip() + ASSINATURA

    url_img, pid = buscar_imagem(tema)
    print(f"[preview] tema='{tema}' cloudinary={'sim' if url_img else 'nao'} pid='{pid}'")

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
        import traceback
        traceback.print_exc()
        return jsonify({"erro": f"Erro ao gerar card: {e}"}), 500

    resp = {"card_id": card_id, "preview_url": preview_url,
            "legenda": legenda, "imagem_fundo": url_img}
    if erros_leg:
        resp["aviso_legenda"] = erros_leg
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
        if not card_url:
            return jsonify({"erro": "Falha no upload definitivo"}), 500
        del _cards_pendentes[card_id]
    except Exception as e:
        return jsonify({"erro": f"Erro no upload: {e}"}), 500
    linha = 0
    try:
        linha = escrever_planilha(tema, legenda_final, card_url)
    except Exception as e:
        print(f"[planilha] ERRO: {e}")
    return jsonify({"cloudinary_url": card_url, "linha_planilha": linha,
                    "status": "Aguardando Postagem"})

@app.route("/gerar-card", methods=["POST"])
def rota_gerar_card():
    return rota_preview_card()

@app.route("/atualizar-status", methods=["POST"])
def rota_atualizar_status():
    data   = request.get_json() or {}
    linha  = data.get("linha")
    status = data.get("status", "Postado")
    if not linha:
        return jsonify({"erro": "Linha obrigatoria"}), 400
    try:
        atualizar_status(int(linha), status)
        return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"erro": str(e)}), 500

@app.route("/")
def index():
    if _dist_index_path():
        return app.send_static_file("index.html")
    return jsonify({
        "erro": "Frontend nao compilado.",
        "dica": "Build: npm ci && npm run build && pip install -r python-api/requirements.txt",
        "health": "/health",
    }), 503

@app.route("/<path:path>")
def spa_static(path):
    dist_file = os.path.join(app.static_folder or "", path)
    if app.static_folder and os.path.isfile(dist_file):
        return app.send_static_file(path)
    if _dist_index_path():
        return app.send_static_file("index.html")
    return jsonify({"erro": "Not Found"}), 404

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)))
