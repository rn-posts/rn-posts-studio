"""
python-api/main.py — API Flask — Render
Identidade Visual AlvoreSer — Design Editorial Premium v4

Base: layout original que funcionava (AGILERA + rotas + fontes corretas)
Melhorias agregadas:
  - Pipeline fotográfico: split toning, contraste cinematográfico, vinheta elíptica
  - Fundo sólido/claro: integra textura orgânica da marca (mantém rembg para Ronilson)
  - Overlay de marca intencional (gradiente inferior + faixa lateral)
  - Badge de categoria laranja antes do título
  - Tipografia hierárquica: AGILERA (título) + MALGUNSL (complemento)
  - Rodapé com linha laranja separadora + CRP alinhado à direita
  - Rota /preview-card + cache _cards_pendentes + /aprovar-card
  - FONTS_DIR original preservado (../src/Brand/fonts) + fallback python-api/fonts
  - Nomes de arquivo em minúsculo EXATAMENTE como no original (case-sensitive no Linux)
"""

import os, io, re, uuid, random, json, textwrap, time, math
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
    "https://rn-posts.onrender.com"
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

@app.route("/")
def index():
    return app.send_static_file("index.html")

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
GEMINI_URL           = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    "gemini-2.0-flash:generateContent?key=" + (os.getenv("GEMINI_API_KEY") or "")
)

W, H = 1080, 1350
CLOUDINARY_POSTS   = "AlvoreSer_Posts"
CLOUDINARY_PREVIEW = "AlvoreSer_Preview"
PASTA_RONILSON     = "banco de imagens/ronilson"

# ── Paleta oficial AlvoreSer ──────────────────────────────────────────────────
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

PALETA_9 = [MARINHO, PETROLEO, TEAL, VERDE_NEUTRO, BRANCO,
            LARANJA, VERDE_VIVO, VERDE_CITRICO, AMARELO]

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

# ── Fontes — EXATAMENTE como no original que funcionava ──────────────────────
# Caminho: python-api/../src/Brand/fonts  (case-sensitive no Linux/Render)
ROOT_DIR  = os.path.join(os.path.dirname(__file__), "..")   # raiz do repositório
FONTS_DIR = os.path.join(ROOT_DIR, "src", "Brand", "fonts") # caminho original

# Fallback: python-api/fonts/ (cópia local para garantia em produção)
_fallback = os.path.join(os.path.dirname(__file__), "fonts")

def _font(nome_minusculo, tamanho):
    """
    Carrega fonte com fallback em 3 níveis:
    1. ../src/Brand/fonts/<nome> (caminho original)
    2. python-api/fonts/<nome>  (cópia local)
    3. PIL default escalável
    Nomes em minúsculo: AGILERA.otf, MALGUN.ttf, MALGUNBD.ttf, MALGUNSL.ttf
    """
    for base in [FONTS_DIR, _fallback]:
        p = os.path.join(base, nome_minusculo)
        if os.path.isfile(p):
            try:
                return ImageFont.truetype(p, tamanho)
            except Exception as e:
                print(f"[fontes] erro ao carregar {p}: {e}")
    print(f"[fontes] NÃO ENCONTRADO: {nome_minusculo} em {FONTS_DIR} nem {_fallback}")
    try:
        return ImageFont.load_default(size=tamanho)
    except Exception:
        return ImageFont.load_default()

# Aliases — nomes exatamente iguais ao original (minúsculo, case-sensitive)
def f_display(t): return _font("AGILERA.otf",   t)   # títulos display grandes
def f_bold(t):    return _font("MALGUNBD.ttf",  t)   # bold — destaque
def f_corpo(t):   return _font("MALGUN.ttf",    t)   # regular — corpo/badge
def f_light(t):   return _font("MALGUNSL.ttf",  t)   # light — subtítulo/rodapé

# Log de status das fontes na inicialização
for _fn in ["AGILERA.otf", "MALGUN.ttf", "MALGUNBD.ttf", "MALGUNSL.ttf"]:
    _p1 = os.path.join(FONTS_DIR, _fn)
    _p2 = os.path.join(_fallback, _fn)
    _ok = os.path.isfile(_p1) or os.path.isfile(_p2)
    print(f"[fontes] {'✓' if _ok else '✗ FALTANDO'} {_fn}")


ASSINATURA = (
    "\n\n👨‍💼 Ronilson Nogueira\n"
    "✍️ Psicólogo e Professor\n"
    "🧩 Referência em Autismo e TDAH\n"
    "CRP 04/57327"
)

PROMPT_LEGENDA = (
    "Crie uma legenda para um post do Instagram sobre: '{tema}'. "
    "Para o psicólogo Ronilson Nogueira, especialista em Autismo e TDAH, "
    "da clínica AlvoreSer em Coronel Fabriciano/MG. "
    "Tom: acolhedor, humano, reflexivo, não-clínico, para o público geral. "
    "Máximo 150 palavras. NAO inclua hashtags. "
    "Retorne APENAS o texto da legenda, sem explicações ou markdown."
)
GROQ_MODELOS = ["llama-3.3-70b-versatile", "llama-3.1-8b-instant", "llama-4-scout"]


def _groq_legenda(tema):
    if not GROQ_API_KEY:
        raise Exception("GROQ_API_KEY nao configurada")
    ultimo = None
    for m in GROQ_MODELOS:
        try:
            r = requests.post(
                GROQ_URL,
                headers={"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"},
                json={"model": m, "messages": [{"role": "user", "content": PROMPT_LEGENDA.format(tema=tema)}], "max_tokens": 400},
                timeout=20,
            )
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
    try:
        return _groq_legenda(tema) + ASSINATURA
    except Exception as e:
        erros.append(f"Groq:{e}")
    try:
        return _gemini_legenda(tema) + ASSINATURA
    except Exception as e:
        erros.append(f"Gemini:{e}")
    raise Exception("Todas as IAs falharam — " + " | ".join(erros))


def buscar_imagem(tema=""):
    t = tema.lower()
    todas_pastas = list(set(MAPA_PASTAS.values()))
    pasta_tema = None
    for chave, pasta in MAPA_PASTAS.items():
        if chave in t:
            pasta_tema = pasta
            break
    if pasta_tema:
        todas_pastas = [pasta_tema] + [p for p in todas_pastas if p != pasta_tema]
    for pasta in todas_pastas:
        try:
            res = cloudinary.api.resources(type="upload", prefix=pasta + "/", max_results=50)
            rec = [r for r in res.get("resources", []) if CLOUDINARY_POSTS not in r.get("public_id", "") and CLOUDINARY_PREVIEW not in r.get("public_id", "")]
            if rec:
                c = random.choice(rec)
                print(f"[busca] {pasta}")
                return c.get("secure_url"), c.get("public_id", "")
        except Exception as e:
            print(f"[busca] erro {pasta}: {e}")
    try:
        res = cloudinary.api.resources(type="upload", max_results=50)
        rec = [r for r in res.get("resources", []) if CLOUDINARY_POSTS not in r.get("public_id", "") and CLOUDINARY_PREVIEW not in r.get("public_id", "")]
        if rec:
            c = random.choice(rec)
            return c.get("secure_url"), c.get("public_id", "")
    except Exception:
        pass
    return None, ""


# ── Utilitários visuais ───────────────────────────────────────────────────────

def _medir(texto, fonte):
    try:
        bb = fonte.getbbox(texto)
        return bb[2] - bb[0]
    except Exception:
        return len(texto) * 30


def luminosidade_regiao(img, y1, y2):
    y2 = min(y2, img.size[1]); y1 = max(y1, 0)
    if y1 >= y2:
        return 128
    p = list(img.crop((0, y1, img.size[0], y2)).convert("L").getdata())
    return sum(p) / len(p)


def distancia_cor(c1, c2):
    return ((c1[0]-c2[0])**2 + (c1[1]-c2[1])**2 + (c1[2]-c2[2])**2) ** 0.5


def cores_fundo_para_imagem(img):
    """Par harmônico da paleta que mais contrasta com a imagem (para textura de fundo)."""
    p = list(img.resize((60, 75), Image.Resampling.LANCZOS).convert("RGB").getdata())
    cf = (sum(x[0] for x in p)//len(p), sum(x[1] for x in p)//len(p), sum(x[2] for x in p)//len(p))
    ord_ = sorted([c for c in PALETA_9 if c != LARANJA], key=lambda c: distancia_cor(cf, c), reverse=True)
    lum = sum(cf)/3
    if lum < 60:
        return MARINHO, PETROLEO
    return ord_[0], ord_[1]


def eh_foto_ronilson(pid):
    return PASTA_RONILSON in pid.lower()


def eh_fundo_claro(img):
    """True se a imagem tem fundo claro (estúdio, branco, cinza claro)."""
    s = img.resize((80, 100), Image.Resampling.LANCZOS).convert("RGB")
    vals = [sum(p)/3 for p in s.getdata()]
    lum = sum(vals)/len(vals)
    var = sum((v-lum)**2 for v in vals)/len(vals)
    return lum > 155 and var < 3000


def remover_fundo_rembg(img):
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return Image.open(io.BytesIO(get_rembg()(buf.getvalue()))).convert("RGBA")


# ── Pipeline fotográfico (agrega ao layout original) ─────────────────────────

def aplicar_vinheta_eliptica(img, intensidade=0.50):
    """Vinheta elíptica — escurece bordas, centro intacto."""
    mw, mh = max(1, W//8), max(1, H//8)
    cx, cy = mw/2, mh/2
    pixels = []
    for y in range(mh):
        for x in range(mw):
            dx = (x-cx)/cx; dy = (y-cy)/cy
            dist = math.sqrt(dx*dx + dy*dy)
            fade = max(0.0, dist-0.45)/0.55
            pixels.append(max(0, min(255, int((1.0-fade*fade*intensidade)*255))))
    mask = Image.new("L", (mw, mh))
    mask.putdata(pixels)
    mask = mask.resize((W, H), Image.Resampling.BICUBIC).filter(ImageFilter.GaussianBlur(50))
    r, g, b = img.convert("RGB").split()
    return Image.merge("RGB", [ImageChops.multiply(r, mask), ImageChops.multiply(g, mask), ImageChops.multiply(b, mask)])


def aplicar_contraste_cinematico(img):
    img = ImageEnhance.Contrast(img).enhance(1.18)
    img = ImageEnhance.Color(img).enhance(1.10)
    img = ImageEnhance.Sharpness(img).enhance(1.18)
    return img


def aplicar_split_toning(img, intensidade=0.08):
    """Sombras frias (marinho), luzes quentes (laranja) — estética editorial."""
    arr = np.array(img.convert("RGB")).astype(np.float32)
    lum = arr.mean(axis=2, keepdims=True)/255.0
    arr += (np.array(MARINHO, dtype=np.float32) - arr) * ((1-lum)**2) * intensidade
    arr += (np.array(LARANJA, dtype=np.float32) - arr) * (lum**2)     * intensidade
    return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))


def gerar_textura_marca(cor1, cor2, seed):
    """Gradiente orgânico com microondas — fundo com identidade visual."""
    rng = random.Random(seed)
    base = Image.new("RGB", (W, H))
    draw = ImageDraw.Draw(base)
    off = rng.uniform(0, math.pi*2)
    for y in range(H):
        t = y/H
        onda = math.sin(y/140+off)*0.05
        t2 = max(0.0, min(1.0, t+onda))
        r = int(cor1[0]*(1-t2)+cor2[0]*t2)
        g = int(cor1[1]*(1-t2)+cor2[1]*t2)
        b = int(cor1[2]*(1-t2)+cor2[2]*t2)
        for x in range(0, W, 3):
            wx = math.sin(x/200+y/280+off)*0.025
            draw.line([(x,y),(x+3,y)], fill=(
                max(0,min(255,int(r+wx*18))),
                max(0,min(255,int(g+wx*12))),
                max(0,min(255,int(b+wx*8))),
            ))
    return base.filter(ImageFilter.GaussianBlur(1))


def compor_pessoa_em_fundo(pessoa_rgba, fundo_rgb):
    """Compõe pessoa recortada sobre textura: à direita, sombra realista."""
    pw, ph = pessoa_rgba.size
    nh = H; nw = int(pw*nh/ph)
    pessoa_rgba = pessoa_rgba.resize((nw, nh), Image.Resampling.LANCZOS)
    x_pos = max(int(W*0.38), W-nw+30)
    x_pos = min(x_pos, W-int(nw*0.80))
    alpha = pessoa_rgba.split()[3]
    # Sombra
    sombra = Image.new("RGBA", (W, H), (0,0,0,0))
    sil = Image.new("RGBA", (nw, H), (0,0,0,0))
    smask = alpha.point(lambda x: int(x*0.18))
    sil.paste(Image.new("RGB", (nw, H), MARINHO), mask=smask)
    sombra.paste(sil, (x_pos-18, 26), sil)
    sombra = sombra.filter(ImageFilter.GaussianBlur(40))
    resultado = fundo_rgb.convert("RGBA")
    resultado = Image.alpha_composite(resultado, sombra)
    resultado.paste(pessoa_rgba, (x_pos, 0), pessoa_rgba)
    return resultado.convert("RGB")


def preparar_foto_fullcard(url, pid, cor1, cor2, seed):
    """
    Prepara a foto para ocupar o card completo (1080×1350).
    3 casos condicionais — estratégia certa para cada tipo de foto:
      A. Ronilson → rembg + composição sobre textura + split toning
      B. Fundo claro/estúdio → tenta rembg; fallback: blend com textura
      C. Foto editorial/ambiente → pipeline direto
    """
    try:
        r = requests.get(url, timeout=20)
        r.raise_for_status()
        img = Image.open(io.BytesIO(r.content)).convert("RGB")
        # Redimensiona e recorta para 1080×1350
        ratio = max(W/img.width, H/img.height)
        nw, nh = int(img.width*ratio), int(img.height*ratio)
        img = img.resize((nw, nh), Image.Resampling.LANCZOS)
        l = (nw-W)//2; t = (nh-H)//2
        img = img.crop((l, t, l+W, t+H))

        textura = gerar_textura_marca(cor1, cor2, seed)

        if eh_foto_ronilson(pid):
            # CASO A — Ronilson: remove fundo e compõe sobre textura da marca
            print(f"[foto] CASO A — Ronilson rembg: {pid}")
            try:
                pessoa = remover_fundo_rembg(img)
                img = compor_pessoa_em_fundo(pessoa, textura)
                print("[foto] rembg OK")
            except Exception as e:
                print(f"[foto] rembg falhou ({e}) → blend")
                img = Image.blend(textura, img, alpha=0.72)

        elif eh_fundo_claro(img):
            # CASO B — fundo claro (estúdio, branco): integra textura
            print("[foto] CASO B — fundo claro")
            try:
                pessoa = remover_fundo_rembg(img)
                img = compor_pessoa_em_fundo(pessoa, textura)
            except Exception:
                # Fallback: blend sutil — textura aparece como fundo
                img = Image.blend(textura, img, alpha=0.70)

        else:
            # CASO C — foto editorial
            print("[foto] CASO C — foto editorial")

        # Pipeline fotográfico comum aos 3 casos
        img = aplicar_split_toning(img, intensidade=0.08)
        img = aplicar_contraste_cinematico(img)
        img = aplicar_vinheta_eliptica(img, intensidade=0.50)
        return img

    except Exception as e:
        print(f"[foto] ERRO: {e}")
        return None


# ── Overlay de marca contextual ───────────────────────────────────────────────

def aplicar_overlay_marca(img):
    """
    Dois gradientes intencionais:
    1. Inferior (42% da altura) — escurece para o texto ser legível
    2. Lateral esquerdo (42% da largura) — ancora o bloco de texto
    Curva suave (potência) — sem corte brusco.
    """
    overlay = Image.new("RGBA", (W, H), (0,0,0,0))
    draw = ImageDraw.Draw(overlay)
    # Gradiente inferior
    altura = int(H*0.42)
    for y in range(altura):
        prog = y/altura
        alpha = int((prog**1.5)*210)
        draw.line([(0, H-altura+y), (W, H-altura+y)], fill=(*MARINHO, alpha))
    # Faixa lateral esquerda
    largura = int(W*0.42)
    for x in range(largura):
        prog = 1.0-(x/largura)
        alpha = int((prog**1.9)*90)
        draw.line([(x, 0), (x, H)], fill=(*MARINHO, alpha))
    return Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")


# ── Tipografia hierárquica ────────────────────────────────────────────────────

def _inferir_categoria(tema):
    t = tema.lower()
    mapa = {
        "autismo":        "Saúde Mental · Neurodesenv.",
        "tdah":           "Saúde Mental · TDAH",
        "ansiedade":      "Saúde Mental",
        "depressao":      "Saúde Mental",
        "burnout":        "Saúde Mental",
        "estresse":       "Bem-Estar",
        "terapia":        "Terapia",
        "relacionamento": "Relacionamentos",
        "familia":        "Família",
        "recomeco":       "Recomeço",
        "transformacao":  "Transformação",
        "luto":           "Acolhimento",
        "trauma":         "Acolhimento",
        "borderline":     "Saúde Mental",
    }
    for k, v in mapa.items():
        if k in t:
            return v
    return "Psicologia"


def _dividir_tema(tema):
    """
    Divide em (titulo_display, complemento_leve) — semanticamente correto.
    1 palavra como título para máximo impacto visual (exceto temas curtos).
    Ex: "Autismo Após Os 40 Anos" → ("AUTISMO", "Após os 40 Anos")
    """
    palavras = tema.strip().split()
    n = len(palavras)
    if n == 1:
        return tema.upper(), ""
    if n == 2:
        return palavras[0].upper(), palavras[1].title()
    # 1 palavra display = maior impacto; complemento acomoda o restante
    n_titulo = 1 if n >= 3 else 2
    titulo      = " ".join(palavras[:n_titulo]).upper()
    complemento = " ".join(palavras[n_titulo:]).title()
    return titulo, complemento


def _quebrar_linhas(texto, fonte_fn, tam, max_px=900):
    fonte = fonte_fn(tam)
    palavras = texto.split()
    linhas, linha_atual = [], []
    for palavra in palavras:
        cand = " ".join(linha_atual+[palavra])
        if _medir(cand, fonte) <= max_px:
            linha_atual.append(palavra)
        else:
            if linha_atual:
                linhas.append(" ".join(linha_atual))
            linha_atual = [palavra]
    if linha_atual:
        linhas.append(" ".join(linha_atual))
    return linhas or [texto]


def _sombra(img_rgba, texto, fonte, x, y, opacidade=140):
    layer = Image.new("RGBA", (W, H), (0,0,0,0))
    ImageDraw.Draw(layer).text((x+3, y+5), texto, font=fonte, fill=(*MARINHO, 255))
    layer = layer.filter(ImageFilter.GaussianBlur(10))
    r2, g2, b2, a2 = layer.split()
    a2 = a2.point(lambda p: int(p*(opacidade/255.0)))
    sombra = Image.merge("RGBA", (r2, g2, b2, a2))
    img_rgba.paste(sombra, (0,0), sombra)


def desenhar_tipografia(img, tema):
    """
    Hierarquia em 3 camadas sobre overlay escuro:
      1. Badge laranja com categoria (Saúde Mental · Neurodesenv.)
      2. Título AGILERA display — palavra-chave, branco
      3. Complemento MALGUNSL leve — restante do tema, laranja
    Zona: 54%–88% da altura do card.
    """
    img_rgba = img.convert("RGBA")
    MARGIN  = 80
    MAX_PX  = int(W * 0.82)
    Y_INI   = int(H * 0.54)
    Y_FIM   = int(H * 0.88)

    titulo, complemento = _dividir_tema(tema)

    # Tamanho do título — adaptativo ao comprimento
    n = len(titulo)
    if   n <= 8:  tam_titulo = 136
    elif n <= 12: tam_titulo = 116
    elif n <= 16: tam_titulo = 100
    elif n <= 22: tam_titulo = 86
    elif n <= 30: tam_titulo = 72
    else:         tam_titulo = 60

    tam_sub   = max(46, int(tam_titulo * 0.50))
    tam_badge = 28

    linhas_titulo = _quebrar_linhas(titulo,      f_display, tam_titulo, MAX_PX)
    linhas_sub    = _quebrar_linhas(complemento, f_light,   tam_sub,    MAX_PX) if complemento else []

    badge_h   = tam_badge + 16
    badge_gap = 18
    sub_gap   = 10
    esp_titulo = int(tam_titulo * 1.08)
    esp_sub    = int(tam_sub    * 1.22)

    altura_bloco = (
        badge_h + badge_gap
        + len(linhas_titulo) * esp_titulo
        + (sub_gap + len(linhas_sub) * esp_sub if linhas_sub else 0)
    )

    zona = Y_FIM - Y_INI
    y0 = Y_INI + max(0, (zona - altura_bloco)//2)
    y0 = max(Y_INI, min(y0, Y_FIM - altura_bloco - 16))

    draw = ImageDraw.Draw(img_rgba, "RGBA")

    # ── Badge categoria ───────────────────────────────────────────────────────
    categoria   = _inferir_categoria(tema).upper()
    fonte_badge = f_corpo(tam_badge)
    badge_w     = _medir(categoria, fonte_badge) + 36
    draw.rounded_rectangle([MARGIN, y0, MARGIN+badge_w, y0+badge_h],
                           radius=7, fill=(*LARANJA, 235))
    draw.text((MARGIN+18, y0+8), categoria, font=fonte_badge, fill=(*PRETO, 255))

    # ── Título AGILERA ────────────────────────────────────────────────────────
    y = y0 + badge_h + badge_gap
    fonte_titulo = f_display(tam_titulo)
    for linha in linhas_titulo:
        _sombra(img_rgba, linha, fonte_titulo, MARGIN, y)
        draw = ImageDraw.Draw(img_rgba, "RGBA")
        draw.text((MARGIN, y), linha, font=fonte_titulo, fill=(*BRANCO, 255))
        y += esp_titulo

    # ── Complemento MALGUNSL ─────────────────────────────────────────────────
    if linhas_sub:
        y += sub_gap
        fonte_sub = f_light(tam_sub)
        for linha in linhas_sub:
            _sombra(img_rgba, linha, fonte_sub, MARGIN, y, opacidade=110)
            draw = ImageDraw.Draw(img_rgba, "RGBA")
            draw.text((MARGIN, y), linha, font=fonte_sub, fill=(*LARANJA, 235))
            y += esp_sub

    return img_rgba.convert("RGB")


# ── Rodapé institucional ──────────────────────────────────────────────────────

def desenhar_rodape(img):
    """
    Rodapé limpo: linha fina laranja + AlvoreSer bold + CRP alinhado à direita.
    """
    draw    = ImageDraw.Draw(img, "RGBA")
    MARGIN  = 80
    ROD_Y   = H - 90

    # Linha separadora laranja
    draw.line([(MARGIN, ROD_Y-16), (W-MARGIN, ROD_Y-16)], fill=(*LARANJA, 195), width=2)

    # "AlvoreSer"
    f_m = f_bold(33)
    draw.text((MARGIN, ROD_Y), "AlvoreSer", font=f_m, fill=(*BRANCO, 252))

    # "Clínica de Psicologia"
    f_s = f_corpo(24)
    larg_m = _medir("AlvoreSer", f_m)
    draw.text((MARGIN+larg_m+16, ROD_Y+7), "Clínica de Psicologia",
              font=f_s, fill=(*VERDE_NEUTRO, 200))

    # CRP à direita
    f_c = f_corpo(22)
    crp = "CRP 04/57327"
    crp_w = _medir(crp, f_c)
    draw.text((W-MARGIN-crp_w, ROD_Y+7), crp, font=f_c, fill=(*VERDE_NEUTRO, 165))

    return img


# ── Geração principal ─────────────────────────────────────────────────────────

def gerar_card_imagem(tema, legenda, imagem_url, pid="", seed=None):
    """
    Gera card 1080×1350 com todas as estratégias agregadas:
      1. Pipeline fotográfico condicional (Ronilson / fundo claro / editorial)
      2. Overlay de marca contextual
      3. Tipografia hierárquica (badge + AGILERA + MALGUNSL)
      4. Rodapé institucional limpo
    """
    if seed is None:
        seed = random.randint(0, 999999)
    print(f"[card] tema='{tema}' seed={seed}")

    cor1, cor2 = MARINHO, PETROLEO
    if imagem_url:
        try:
            r = requests.get(imagem_url, timeout=15)
            r.raise_for_status()
            tmp = Image.open(io.BytesIO(r.content)).convert("RGB").resize((120, 150), Image.Resampling.LANCZOS)
            cor1, cor2 = cores_fundo_para_imagem(tmp)
        except Exception:
            pass

    base = Image.new("RGB", (W, H), MARINHO)
    if imagem_url:
        foto = preparar_foto_fullcard(imagem_url, pid, cor1, cor2, seed)
        if foto:
            base = foto

    base = aplicar_overlay_marca(base)
    base = desenhar_tipografia(base, tema)
    base = desenhar_rodape(base)
    return base


# ── Upload ────────────────────────────────────────────────────────────────────

def upload_imagem(img, folder, public_id):
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=92)
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
    linha = [agora, tema, tema, legenda, "Profissional e acolhedor", "Pronta", "Aguardando Postagem", url]
    res   = svc.spreadsheets().values().append(
        spreadsheetId=SPREADSHEET_ID, range="A:H",
        valueInputOption="RAW", insertDataOption="INSERT_ROWS",
        body={"values": [linha]},
    ).execute()
    try:
        return int(res["updates"]["updatedRange"].split("!A")[1].split(":")[0])
    except Exception:
        return 0


def atualizar_status(linha, status):
    get_sheets().spreadsheets().values().update(
        spreadsheetId=SPREADSHEET_ID, range=f"G{linha}",
        valueInputOption="RAW", body={"values": [[status]]},
    ).execute()


# ── Rotas ─────────────────────────────────────────────────────────────────────

@app.route("/health", methods=["GET"])
def health():
    fontes = {}
    for fn in ["AGILERA.otf", "MALGUN.ttf", "MALGUNBD.ttf", "MALGUNSL.ttf"]:
        p1 = os.path.join(FONTS_DIR, fn)
        p2 = os.path.join(_fallback,  fn)
        fontes[fn] = os.path.isfile(p1) or os.path.isfile(p2)
    return jsonify({
        "status": "ok",
        "dimensoes": f"{W}x{H}",
        "fonts_dir_original": FONTS_DIR,
        "fonts_dir_fallback":  _fallback,
        "fontes": fontes,
        "agilera_ok": fontes.get("AGILERA.otf", False),
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
            erros_leg = str(e)
            legenda = ""
    if legenda and "CRP 04/57327" not in legenda:
        legenda = legenda.rstrip() + ASSINATURA

    url_img, pid = buscar_imagem(tema)

    try:
        seed = data.get("seed")
        card = gerar_card_imagem(tema, legenda, url_img, pid, seed=seed)
        card_id = f"preview_{uuid.uuid4().hex[:10]}"
        preview_url = upload_imagem(card, CLOUDINARY_PREVIEW, card_id)
        if not preview_url:
            return jsonify({"erro": "Falha no upload do preview"}), 500

        buf = io.BytesIO()
        card.save(buf, format="JPEG", quality=92)
        _cards_pendentes[card_id] = {
            "tema": tema, "legenda": legenda,
            "imagem_fundo": url_img, "pid_fundo": pid,
            "preview_url": preview_url,
            "card_bytes": buf.getvalue(),
        }
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
    tema    = data.get("tema",    "").strip()
    legenda = data.get("legenda", "").strip()

    if not card_id or card_id not in _cards_pendentes:
        return jsonify({"erro": "Card nao encontrado. Gere novamente."}), 400

    dados = _cards_pendentes[card_id]
    legenda_final = legenda if legenda else dados["legenda"]

    try:
        uid = f"post_{uuid.uuid4().hex[:8]}"
        res = cloudinary.uploader.upload(
            io.BytesIO(dados["card_bytes"]), public_id=uid,
            folder=CLOUDINARY_POSTS, overwrite=True, resource_type="image")
        card_url = res.get("secure_url", "")
        if not card_url:
            return jsonify({"erro": "Falha no upload definitivo"}), 500
        try:
            cloudinary.uploader.destroy(f"{CLOUDINARY_PREVIEW}/{card_id}")
        except Exception:
            pass
        del _cards_pendentes[card_id]
    except Exception as e:
        return jsonify({"erro": f"Erro no upload: {e}"}), 500

    linha = 0
    try:
        linha = escrever_planilha(tema, legenda_final, card_url)
    except Exception as e:
        print(f"[planilha] ERRO: {e}")

    return jsonify({"cloudinary_url": card_url, "linha_planilha": linha, "status": "Aguardando Postagem"})


@app.route("/gerar-card", methods=["POST"])
def rota_gerar_card():
    """Rota legada — compatibilidade total com o frontend."""
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


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)))
