"""
python-api/main.py — API Flask — Render
Identidade Visual AlvoreSer — v7

Regras definitivas:
- Título: tema completo em AGILERA, branco, maiúsculo — SEM divisão, SEM badge
- Overlay: gradiente inferior leve apenas para legibilidade
- Vinheta: suave, não destrói a foto
- Split toning: mínimo, só para harmonizar
- Rodapé: AlvoreSer + CRP 04/57327 — sem "Clínica de Psicologia"
- Encoding: tudo em unicode escape para evitar caracteres quebrados
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
    if origin:
        if origin in ALLOWED_ORIGINS or "localhost" in origin or "onrender.com" in origin:
            response.headers["Access-Control-Allow-Origin"] = origin
    response.headers["Access-Control-Allow-Headers"] = "Content-Type,Authorization"
    response.headers["Access-Control-Allow-Methods"] = "GET,POST,OPTIONS"
    return response

def _dist_index_path():
    folder = app.static_folder
    if not folder:
        return None
    path = os.path.join(os.path.abspath(folder), "index.html")
    return path if os.path.isfile(path) else None

cloudinary.config(
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
    api_key=os.getenv("CLOUDINARY_API_KEY"),
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

# Paleta AlvoreSer
MARINHO      = (2,   64,  89)
PETROLEO     = (27,  121, 125)
TEAL         = (4,   157, 191)
VERDE_NEUTRO = (119, 153, 147)
BRANCO       = (244, 246, 248)
LARANJA      = (249, 171, 11)
VERDE_VIVO   = (122, 181, 0)
VERDE_CITRICO= (146, 204, 29)
AMARELO      = (255, 221, 0)
PRETO        = (20,  20,  20)
PALETA_9     = [MARINHO, PETROLEO, TEAL, VERDE_NEUTRO, BRANCO,
                LARANJA, VERDE_VIVO, VERDE_CITRICO, AMARELO]

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

# ── Fontes ─────────────────────────────────────────────────────────────────────
ROOT_DIR  = os.path.join(os.path.dirname(__file__), "..")
FONTS_DIR = os.path.join(ROOT_DIR, "src", "Brand", "fonts")
_fallback = os.path.join(os.path.dirname(__file__), "fonts")

def _resolve_font_path(nome):
    for base in [FONTS_DIR, _fallback]:
        p = os.path.join(base, nome)
        if os.path.isfile(p):
            return p
        if os.path.isdir(base):
            low = nome.lower()
            for f in os.listdir(base):
                if f.lower() == low:
                    return os.path.join(base, f)
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

# Nomes em MAIUSCULO — igual ao arquivo no disco (case-sensitive no Linux/Render)
def f_display(t): return _font("AGILERA.OTF",  t)
def f_bold(t):    return _font("MALGUNBD.TTF", t)
def f_corpo(t):   return _font("MALGUN.TTF",   t)
def f_light(t):   return _font("MALGUNSL.TTF", t)

for _fn in ["AGILERA.OTF", "MALGUN.TTF", "MALGUNBD.TTF", "MALGUNSL.TTF"]:
    _ok = _resolve_font_path(_fn) is not None
    print(f"[font] {'OK' if _ok else 'FALTANDO'} {_fn}")

# ── IA ─────────────────────────────────────────────────────────────────────────

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

# ── Cloudinary ─────────────────────────────────────────────────────────────────

def buscar_imagem(tema=""):
    t = tema.lower()
    todas = list(set(MAPA_PASTAS.values()))
    pasta = next((MAPA_PASTAS[k] for k in MAPA_PASTAS if k in t), None)
    if pasta:
        todas = [pasta] + [p for p in todas if p != pasta]
    for p in todas:
        try:
            res = cloudinary.api.resources(type="upload", prefix=p+"/", max_results=50)
            rec = [r for r in res.get("resources", [])
                   if CLOUDINARY_POSTS not in r.get("public_id", "")
                   and CLOUDINARY_PREVIEW not in r.get("public_id", "")]
            if rec:
                c = random.choice(rec)
                return c.get("secure_url"), c.get("public_id", "")
        except Exception as e:
            print(f"[busca] {p}: {e}")
    try:
        res = cloudinary.api.resources(type="upload", max_results=50)
        rec = [r for r in res.get("resources", [])
               if CLOUDINARY_POSTS not in r.get("public_id", "")
               and CLOUDINARY_PREVIEW not in r.get("public_id", "")]
        if rec:
            c = random.choice(rec)
            return c.get("secure_url"), c.get("public_id", "")
    except Exception:
        pass
    return None, ""

# ── Utilitários visuais ────────────────────────────────────────────────────────

def _medir(texto, fonte):
    try:
        bb = fonte.getbbox(texto)
        return bb[2] - bb[0]
    except Exception:
        return len(texto) * 30

def distancia_cor(c1, c2):
    return sum((a-b)**2 for a, b in zip(c1, c2)) ** 0.5

def cores_fundo(img):
    p = list(img.resize((60, 75), Image.Resampling.LANCZOS).convert("RGB").getdata())
    cf = tuple(sum(x[i] for x in p)//len(p) for i in range(3))
    ord_ = sorted([c for c in PALETA_9 if c != LARANJA],
                  key=lambda c: distancia_cor(cf, c), reverse=True)
    return (MARINHO, PETROLEO) if sum(cf)/3 < 60 else (ord_[0], ord_[1])

def eh_foto_ronilson(pid):
    return PASTA_RONILSON in pid.lower()

def eh_fundo_claro(img):
    s = img.resize((80, 100), Image.Resampling.LANCZOS).convert("RGB")
    vals = [sum(p)/3 for p in s.getdata()]
    lum = sum(vals)/len(vals)
    var = sum((v-lum)**2 for v in vals)/len(vals)
    return lum > 155 and var < 3000

def remover_fundo_rembg(img):
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return Image.open(io.BytesIO(get_rembg()(buf.getvalue()))).convert("RGBA")

# ── Pipeline fotográfico ──────────────────────────────────────────────────────

def aplicar_vinheta(img, intensidade=0.25):
    """Vinheta muito suave — só escurece levemente as bordas, preserva a foto."""
    mw, mh = max(1, W//8), max(1, H//8)
    cx, cy = mw/2, mh/2
    pixels = []
    for y in range(mh):
        for x in range(mw):
            dx=(x-cx)/cx; dy=(y-cy)/cy
            dist=math.sqrt(dx*dx+dy*dy)
            fade=max(0.0, dist-0.55)/0.45
            pixels.append(max(0, min(255, int((1-fade*fade*intensidade)*255))))
    mask = Image.new("L", (mw, mh))
    mask.putdata(pixels)
    mask = mask.resize((W, H), Image.Resampling.BICUBIC).filter(ImageFilter.GaussianBlur(60))
    r, g, b = img.convert("RGB").split()
    return Image.merge("RGB", [ImageChops.multiply(r, mask),
                                ImageChops.multiply(g, mask),
                                ImageChops.multiply(b, mask)])

def aplicar_contraste(img):
    img = ImageEnhance.Contrast(img).enhance(1.12)
    img = ImageEnhance.Color(img).enhance(1.08)
    img = ImageEnhance.Sharpness(img).enhance(1.15)
    return img

def aplicar_split_toning(img, intensidade=0.05):
    """Split toning minimo — so harmoniza, nao colore."""
    arr = np.array(img.convert("RGB")).astype(np.float32)
    lum = arr.mean(axis=2, keepdims=True)/255.0
    arr += (np.array(MARINHO, dtype=np.float32) - arr) * ((1-lum)**2) * intensidade
    arr += (np.array(LARANJA, dtype=np.float32) - arr) * (lum**2)     * intensidade
    return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))

def gerar_textura(cor1, cor2, seed):
    rng = random.Random(seed)
    base = Image.new("RGB", (W, H))
    draw = ImageDraw.Draw(base)
    off = rng.uniform(0, math.pi*2)
    for y in range(H):
        t = y/H
        t2 = max(0.0, min(1.0, t + math.sin(y/140+off)*0.05))
        r = int(cor1[0]*(1-t2)+cor2[0]*t2)
        g = int(cor1[1]*(1-t2)+cor2[1]*t2)
        b = int(cor1[2]*(1-t2)+cor2[2]*t2)
        for x in range(0, W, 3):
            wx = math.sin(x/200+y/280+off)*0.025
            draw.line([(x, y), (x+3, y)], fill=(
                max(0, min(255, int(r+wx*18))),
                max(0, min(255, int(g+wx*12))),
                max(0, min(255, int(b+wx*8)))))
    return base.filter(ImageFilter.GaussianBlur(1))

def adicionar_ondas_marca(img, cor_onda, seed):
    """Adiciona as ondas orgânicas da identidade visual AlvoreSer no topo e fundo."""
    img_rgba = img.convert("RGBA")
    draw = ImageDraw.Draw(img_rgba, "RGBA")
    rng = random.Random(seed)
    
    # Onda no topo (sutil, opacidade 10-18%)
    h_onda = rng.uniform(H * 0.15, H * 0.30)
    ctrl_y = rng.uniform(H * 0.05, H * 0.20)
    pontos_topo = []
    passos = 40
    for p in range(passos + 1):
        t = p / passos
        x = t * W
        y = (1 - t)**2 * ctrl_y + 2 * (1 - t) * t * h_onda + t**2 * ctrl_y
        pontos_topo.append((x, y))
    pontos_topo.append((W, 0))
    pontos_topo.append((0, 0))
    draw.polygon(pontos_topo, fill=(*cor_onda, rng.randint(25, 45)))
    
    # Outra onda na base (sutil, opacidade 12-20%)
    h_onda_b = H - rng.uniform(H * 0.15, H * 0.30)
    ctrl_y_b = H - rng.uniform(H * 0.05, H * 0.20)
    pontos_base = []
    for p in range(passos + 1):
        t = p / passos
        x = t * W
        y = (1 - t)**2 * ctrl_y_b + 2 * (1 - t) * t * h_onda_b + t**2 * ctrl_y_b
        pontos_base.append((x, y))
    pontos_base.append((W, H))
    pontos_base.append((0, H))
    draw.polygon(pontos_base, fill=(*cor_onda, rng.randint(28, 48)))
    
    return img_rgba.convert("RGB")

def compor_pessoa(pessoa_rgba, fundo_rgb):
    pw, ph = pessoa_rgba.size
    nw = int(pw*H/ph)
    pessoa_rgba = pessoa_rgba.resize((nw, H), Image.Resampling.LANCZOS)
    
    # Alinhamento à direita seguro e inteligente
    x = W - nw + 50
    x = max(int(W * 0.38), min(x, W - 150))
    
    alpha = pessoa_rgba.split()[3]
    sombra = Image.new("RGBA", (W, H), (0,0,0,0))
    sil = Image.new("RGBA", (nw, H), (0,0,0,0))
    sil.paste(Image.new("RGB", (nw, H), MARINHO),
              mask=alpha.point(lambda v: int(v*0.18)))
    sombra.paste(sil, (x-20, 18), sil)
    sombra = sombra.filter(ImageFilter.GaussianBlur(38))
    
    res = fundo_rgb.convert("RGBA")
    res = Image.alpha_composite(res, sombra)
    res.paste(pessoa_rgba, (x, 0), pessoa_rgba)
    return res.convert("RGB")

def preparar_foto(url, pid, cor1, cor2, seed):
    try:
        r = requests.get(url, timeout=20)
        r.raise_for_status()
        img = Image.open(io.BytesIO(r.content)).convert("RGB")
        ratio = max(W/img.width, H/img.height)
        nw, nh = int(img.width*ratio), int(img.height*ratio)
        img = img.resize((nw, nh), Image.Resampling.LANCZOS)
        l = (nw-W)//2; t = (nh-H)//2
        img = img.crop((l, t, l+W, t+H))
        
        # Fundo com a textura da marca
        tex = gerar_textura(cor1, cor2, seed)
        # Ondas elegantes no fundo
        cor_onda = TEAL if sum(cor1)/3 < 120 else PETROLEO
        tex = adicionar_ondas_marca(tex, cor_onda, seed)

        if eh_foto_ronilson(pid):
            print(f"[foto] Ronilson rembg: {pid}")
            try:
                img = compor_pessoa(remover_fundo_rembg(img), tex)
            except Exception as e:
                print(f"[foto] rembg falhou: {e}")
                # Fallback bem contrastado e integrado com a marca em vez de blend puro escuro
                img = Image.blend(tex, img, alpha=0.55)
        else:
            print("[foto] editorial — mantendo fundo original de alta qualidade e inserindo ondas da marca")
            # Para stock photos de outras pastas, MANTEMOS a imagem original e apenas adicionamos as ondas e tratamentos!
            img = adicionar_ondas_marca(img, cor_onda, seed)

        img = aplicar_split_toning(img)
        img = aplicar_contraste(img)
        img = aplicar_vinheta(img)
        return img
    except Exception as e:
        print(f"[foto] ERRO: {e}")
        return None

# ── Overlay — gradiente inferior leve apenas para legibilidade ────────────────

def aplicar_overlay(img):
    """
    Gradiente escuro apenas na base (30% da altura).
    Leve — nao destrói a foto, só garante contraste para o título.
    """
    overlay = Image.new("RGBA", (W, H), (0,0,0,0))
    draw = ImageDraw.Draw(overlay)
    altura = int(H * 0.30)
    for y in range(altura):
        prog = y / altura
        alpha = int((prog ** 1.8) * 175)
        draw.line([(0, H-altura+y), (W, H-altura+y)], fill=(*MARINHO, alpha))
    return Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")

# ── Tipografia — título completo, sem divisão, sem badge ─────────────────────

def _sombra_texto(img_rgba, texto, fonte, x, y, opacidade_suave=0.35, opacidade_nitida=0.55):
    # Sombra suave e profunda
    layer_suave = Image.new("RGBA", (W, H), (0,0,0,0))
    ImageDraw.Draw(layer_suave).text((x+5, y+7), texto, font=fonte, fill=(2, 20, 30, int(255 * opacidade_suave)))
    layer_suave = layer_suave.filter(ImageFilter.GaussianBlur(14))
    img_rgba.paste(layer_suave, (0,0), layer_suave)

    # Sombra nítida para contraste
    layer_nitida = Image.new("RGBA", (W, H), (0,0,0,0))
    ImageDraw.Draw(layer_nitida).text((x+2, y+3), texto, font=fonte, fill=(2, 20, 30, int(255 * opacidade_nitida)))
    layer_nitida = layer_nitida.filter(ImageFilter.GaussianBlur(3))
    img_rgba.paste(layer_nitida, (0,0), layer_nitida)

def desenhar_titulo(img, tema, seed):
    """
    Desenha o título com alta variabilidade e grade editorial premium baseada em seed:
    - Mescla fontes AGILERA (display) e MALGUN (bold/light)
    - Suporta caixa alta/baixa (capitalização exata preservada do input do usuário ou título refinado)
    - Limita a largura para a metade esquerda do card caso haja sujeito na direita, evitando sobreposições
    - Aplica nossa dupla sombra projetada (Figma style) para legibilidade incrível
    """
    img_rgba = img.convert("RGBA")
    
    MARGIN = 80
    MAX_PX = int(W * 0.58) # Limita a largura a 58% do card para não invadir o sujeito na direita
    Y_INI  = int(H * 0.38) # Posicionado na zona do meio-alto (editorial de revista)
    Y_FIM  = int(H * 0.76)
    
    estilo = seed % 6
    
    # Decisão de Capitalização:
    # Se estilo for par (0, 2, 4), respeita e preserva a capitalização EXATA digitada pelo usuário!
    # Se for ímpar (1, 3, 5), força caixa alta para dar impacto.
    if estilo % 2 == 0:
        titulo_texto = tema.strip()
    else:
        titulo_texto = tema.strip().upper()
        
    palavras = titulo_texto.split()
    if not palavras:
        palavras = [titulo_texto]
        
    elementos = [] # Lista de (linha, fonte, cor)
    
    n = len(titulo_texto)
    tam_display = 126 if n <= 10 else 108 if n <= 18 else 88 if n <= 28 else 72
    tam_bold    = 108 if n <= 10 else 90  if n <= 18 else 76 if n <= 28 else 60
    
    if estilo == 0:
        # Estilo 0: Puro Agilera com capitalização preservada
        fonte = f_display(tam_display)
        linhas = _quebrar_texto(titulo_texto, fonte, MAX_PX)
        for l in linhas:
            elementos.append((l, fonte, BRANCO))
            
    elif estilo == 1:
        # Estilo 1: Agilera com destaque da última linha em Laranja/Amarelo
        fonte = f_display(tam_display)
        linhas = _quebrar_texto(titulo_texto, fonte, MAX_PX)
        for i, l in enumerate(linhas):
            cor = BRANCO if i < len(linhas)-1 else (LARANJA if seed % 2 == 0 else AMARELO)
            elementos.append((l, fonte, cor))
            
    elif estilo == 2:
        # Estilo 2: Agilera (display) para todo o título, com a primeira palavra em Malgun Bold
        f_disp = f_display(tam_display)
        f_bld  = f_bold(tam_bold)
        
        l1 = palavras[0]
        elementos.append((l1, f_bld, AMARELO))
        
        resto = " ".join(palavras[1:])
        if resto:
            linhas_resto = _quebrar_texto(resto, f_disp, MAX_PX)
            for l in linhas_resto:
                elementos.append((l, f_disp, BRANCO))
            
    elif estilo == 3:
        # Estilo 3: Primeira linha em Agilera, restante em Malgun Light (Teal/Amarelo)
        fonte_a = f_display(tam_display)
        fonte_l = f_light(tam_bold - 12)
        linhas = _quebrar_texto(titulo_texto, fonte_a, MAX_PX)
        for i, l in enumerate(linhas):
            f = fonte_a if i == 0 else fonte_l
            cor = BRANCO if i == 0 else (AMARELO if seed % 2 == 0 else TEAL)
            elementos.append((l, f, cor))
            
    elif estilo == 4:
        # Estilo 4: Título principal em Agilera, com destaque colorido na primeira linha
        fonte = f_display(tam_display)
        linhas = _quebrar_texto(titulo_texto, fonte, MAX_PX)
        for i, l in enumerate(linhas):
            cor = BRANCO if i == 0 else (LARANJA if seed % 2 == 0 else AMARELO)
            elementos.append((l, fonte, cor))
                
    else: # estilo == 5
        # Estilo 5: Puro Malgun Bold para liberdade tipográfica completa
        fonte = f_bold(tam_bold)
        linhas = _quebrar_texto(titulo_texto, fonte, MAX_PX)
        for l in linhas:
            elementos.append((l, fonte, BRANCO))

    # Calcula altura e desenha
    altura_bloco = 0
    linhas_prontas = []
    for l, f, cor in elementos:
        try:
            bbox = f.getbbox(l)
            h_linha = bbox[3] - bbox[1]
        except Exception:
            h_linha = 50
        esp = int(h_linha * 1.15)
        linhas_prontas.append((l, f, cor, esp))
        altura_bloco += esp
        
    zona = Y_FIM - Y_INI
    y = Y_INI + max(0, (zona - altura_bloco) // 2)
    y = max(Y_INI, min(y, Y_FIM - altura_bloco - 20))
    
    draw = ImageDraw.Draw(img_rgba, "RGBA")
    for l, f, cor, esp in linhas_prontas:
        _sombra_texto(img_rgba, l, f, MARGIN, y)
        draw.text((MARGIN, y), l, font=f, fill=(*cor, 255))
        y += esp
        
    return img_rgba.convert("RGB")

def _quebrar_texto(texto, fonte, max_px):
    palavras = texto.split()
    linhas, atual = [], []
    for p in palavras:
        cand = " ".join(atual + [p])
        if _medir(cand, fonte) <= max_px:
            atual.append(p)
        else:
            if atual:
                linhas.append(" ".join(atual))
            atual = [p]
    if atual:
        linhas.append(" ".join(atual))
    return linhas if linhas else [texto]

# ── Rodapé — AlvoreSer + CRP, sem "Clínica de Psicologia" ────────────────────

def desenhar_rodape(img):
    draw   = ImageDraw.Draw(img, "RGBA")
    MARGIN = 80
    ROD_Y  = H - 88
    # Linha separadora laranja
    draw.line([(MARGIN, ROD_Y-14), (W-MARGIN, ROD_Y-14)],
              fill=(*LARANJA, 170), width=2)
    # AlvoreSer
    f_m = f_bold(32)
    draw.text((MARGIN, ROD_Y), "AlvoreSer", font=f_m, fill=(*BRANCO, 250))
    # CRP alinhado à direita
    f_c   = f_corpo(23)
    crp   = "CRP 04/57327"
    crp_w = _medir(crp, f_c)
    draw.text((W-MARGIN-crp_w, ROD_Y+6), crp, font=f_c, fill=(*VERDE_NEUTRO, 170))
    return img

# ── Geração principal ─────────────────────────────────────────────────────────

def gerar_card_imagem(tema, legenda, imagem_url, pid="", seed=None):
    if seed is None:
        seed = random.randint(0, 999999)
    print(f"[card] tema='{tema}' seed={seed}")

    cor1, cor2 = MARINHO, PETROLEO
    if imagem_url:
        try:
            r = requests.get(imagem_url, timeout=15)
            r.raise_for_status()
            tmp = Image.open(io.BytesIO(r.content)).convert("RGB").resize(
                (120, 150), Image.Resampling.LANCZOS)
            cor1, cor2 = cores_fundo(tmp)
        except Exception:
            pass

    base = Image.new("RGB", (W, H), MARINHO)
    if imagem_url:
        foto = preparar_foto(imagem_url, pid, cor1, cor2, seed)
        if foto:
            base = foto

    base = aplicar_overlay(base)
    base = desenhar_titulo(base, tema, seed) # Passando o seed para variedade tipográfica
    # Rodapé removido permanentemente a pedido do usuário (imagem limpa, contendo apenas o texto digitado)
    return base

# ── Upload ─────────────────────────────────────────────────────────────────────

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

# ── Rotas ──────────────────────────────────────────────────────────────────────

def _env_first(*keys):
    for key in keys:
        val = os.getenv(key)
        if val and str(val).strip():
            return str(val).strip()
    return None

@app.route("/config/firebase", methods=["GET"])
def rota_config_firebase():
    """Config do Firebase em runtime (mesmas vars do .env, sem precisar de VITE_ no build)."""
    cfg = {
        "apiKey":            _env_first("FIREBASE_API_KEY", "VITE_FIREBASE_API_KEY"),
        "authDomain":        _env_first("FIREBASE_AUTH_DOMAIN", "VITE_FIREBASE_AUTH_DOMAIN"),
        "projectId":         _env_first("FIREBASE_PROJECT_ID", "VITE_FIREBASE_PROJECT_ID"),
        "storageBucket":     _env_first("FIREBASE_STORAGE_BUCKET", "VITE_FIREBASE_STORAGE_BUCKET"),
        "messagingSenderId": _env_first("FIREBASE_MESSAGING_SENDER_ID", "VITE_FIREBASE_MESSAGING_SENDER_ID"),
        "appId":             _env_first("FIREBASE_APP_ID", "VITE_FIREBASE_APP_ID"),
    }
    if not cfg["apiKey"]:
        return jsonify({
            "erro": "Firebase nao configurado no Render.",
            "dica": "Environment: adicione FIREBASE_API_KEY, FIREBASE_AUTH_DOMAIN, ... (valores do .env local)",
        }), 503
    return jsonify(cfg)

@app.route("/health", methods=["GET"])
def health():
    fontes = {fn: _resolve_font_path(fn) is not None
              for fn in ["AGILERA.OTF", "MALGUN.TTF", "MALGUNBD.TTF", "MALGUNSL.TTF"]}
    return jsonify({"status": "ok", "dimensoes": f"{W}x{H}",
                    "fontes": fontes, "agilera_ok": fontes.get("AGILERA.OTF", False)})

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
    try:
        seed = data.get("seed")
        card = gerar_card_imagem(tema, legenda, url_img, pid, seed=seed)
        card_id = f"preview_{uuid.uuid4().hex[:10]}"
        
        # Gera os bytes JPEG locais para evitar qualquer upload ao Cloudinary sem a aprovação do usuário!
        buf = io.BytesIO()
        card.save(buf, format="JPEG", quality=93)
        card_bytes = buf.getvalue()
        
        # Converte para Base64 Data URI de forma instantânea e totalmente limpa
        preview_url = f"data:image/jpeg;base64,{base64.b64encode(card_bytes).decode('utf-8')}"
        
        _cards_pendentes[card_id] = {
            "tema": tema, "legenda": legenda,
            "imagem_fundo": url_img, "pid_fundo": pid,
            "preview_url": preview_url, "card_bytes": card_bytes}
    except Exception as e:
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
        # O preview base64 é local, portanto nenhuma exclusão de preview do Cloudinary é necessária!
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
        "dica": "No Render, use Build Command: npm ci && npm run build && pip install -r python-api/requirements.txt",
        "health": "/health",
    }), 503

@app.route("/<path:path>")
def spa_static(path):
    """Assets do Vite (js/css); rotas de API ja foram registradas acima."""
    dist_file = os.path.join(app.static_folder or "", path)
    if app.static_folder and os.path.isfile(dist_file):
        return app.send_static_file(path)
    if _dist_index_path():
        return app.send_static_file("index.html")
    return jsonify({"erro": "Not Found"}), 404

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)))
