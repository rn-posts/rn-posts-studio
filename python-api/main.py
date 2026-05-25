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

import os, io, uuid, random, json, math
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

def _font(nome, tam):
    for base in [FONTS_DIR, _fallback]:
        p = os.path.join(base, nome)
        if os.path.isfile(p):
            try:
                return ImageFont.truetype(p, tam)
            except Exception as e:
                print(f"[font] erro {p}: {e}")
    print(f"[font] FALTANDO: {nome}")
    try:
        return ImageFont.load_default(size=tam)
    except Exception:
        return ImageFont.load_default()

# Nomes em minusculo — case-sensitive no Linux/Render
def f_display(t): return _font("AGILERA.otf",  t)
def f_bold(t):    return _font("MALGUNBD.ttf", t)
def f_corpo(t):   return _font("MALGUN.ttf",   t)
def f_light(t):   return _font("MALGUNSL.ttf", t)

for _fn in ["AGILERA.otf", "MALGUN.ttf", "MALGUNBD.ttf", "MALGUNSL.ttf"]:
    _ok = (os.path.isfile(os.path.join(FONTS_DIR, _fn)) or
           os.path.isfile(os.path.join(_fallback, _fn)))
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

def compor_pessoa(pessoa_rgba, fundo_rgb):
    pw, ph = pessoa_rgba.size
    nw = int(pw*H/ph)
    pessoa_rgba = pessoa_rgba.resize((nw, H), Image.Resampling.LANCZOS)
    x = max(int(W*0.38), W-nw+30)
    x = min(x, W-int(nw*0.80))
    alpha = pessoa_rgba.split()[3]
    sombra = Image.new("RGBA", (W, H), (0,0,0,0))
    sil = Image.new("RGBA", (nw, H), (0,0,0,0))
    sil.paste(Image.new("RGB", (nw, H), MARINHO),
              mask=alpha.point(lambda v: int(v*0.15)))
    sombra.paste(sil, (x-16, 22), sil)
    sombra = sombra.filter(ImageFilter.GaussianBlur(36))
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
        tex = gerar_textura(cor1, cor2, seed)

        if eh_foto_ronilson(pid):
            print(f"[foto] Ronilson rembg: {pid}")
            try:
                img = compor_pessoa(remover_fundo_rembg(img), tex)
            except Exception as e:
                print(f"[foto] rembg falhou: {e}")
                img = Image.blend(tex, img, alpha=0.75)
        elif eh_fundo_claro(img):
            print("[foto] fundo claro")
            try:
                img = compor_pessoa(remover_fundo_rembg(img), tex)
            except Exception:
                img = Image.blend(tex, img, alpha=0.72)
        else:
            print("[foto] editorial — pipeline direto")

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

def _sombra_texto(img_rgba, texto, fonte, x, y, opacidade=120):
    layer = Image.new("RGBA", (W, H), (0,0,0,0))
    ImageDraw.Draw(layer).text((x+2, y+4), texto, font=fonte, fill=(*MARINHO, 255))
    layer = layer.filter(ImageFilter.GaussianBlur(8))
    r2, g2, b2, a2 = layer.split()
    a2 = a2.point(lambda p: int(p*(opacidade/255.0)))
    s = Image.merge("RGBA", (r2, g2, b2, a2))
    img_rgba.paste(s, (0,0), s)

def desenhar_titulo(img, tema):
    """
    Título: tema completo em AGILERA, branco, maiúsculo.
    Quebra linha automaticamente se ultrapassar largura.
    Posicionado na zona inferior (62%–87%).
    Sem badge, sem complemento — apenas o título.
    """
    img_rgba = img.convert("RGBA")
    MARGIN = 80
    MAX_PX = int(W * 0.85)
    Y_INI  = int(H * 0.62)
    Y_FIM  = int(H * 0.87)

    titulo = tema.strip().upper()

    # Tamanho adaptativo ao comprimento total
    n = len(titulo)
    if   n <= 6:  tam = 158
    elif n <= 10: tam = 144
    elif n <= 14: tam = 126
    elif n <= 18: tam = 108
    elif n <= 24: tam = 90
    elif n <= 32: tam = 76
    else:         tam = 62

    fonte = f_display(tam)

    # Quebra em linhas respeitando largura máxima
    palavras = titulo.split()
    linhas, atual = [], []
    for p in palavras:
        cand = " ".join(atual + [p])
        if _medir(cand, fonte) <= MAX_PX:
            atual.append(p)
        else:
            if atual:
                linhas.append(" ".join(atual))
            atual = [p]
    if atual:
        linhas.append(" ".join(atual))
    if not linhas:
        linhas = [titulo]

    esp = int(tam * 1.06)
    altura_bloco = len(linhas) * esp
    zona = Y_FIM - Y_INI
    y = Y_INI + max(0, (zona - altura_bloco) // 2)
    y = max(Y_INI, min(y, Y_FIM - altura_bloco - 16))

    draw = ImageDraw.Draw(img_rgba, "RGBA")
    for linha in linhas:
        _sombra_texto(img_rgba, linha, fonte, MARGIN, y)
        draw = ImageDraw.Draw(img_rgba, "RGBA")
        draw.text((MARGIN, y), linha, font=fonte, fill=(*BRANCO, 255))
        y += esp

    return img_rgba.convert("RGB")

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
    base = desenhar_titulo(base, tema)
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

@app.route("/health", methods=["GET"])
def health():
    fontes = {fn: (os.path.isfile(os.path.join(FONTS_DIR, fn)) or
                   os.path.isfile(os.path.join(_fallback, fn)))
              for fn in ["AGILERA.otf", "MALGUN.ttf", "MALGUNBD.ttf", "MALGUNSL.ttf"]}
    return jsonify({"status": "ok", "dimensoes": f"{W}x{H}",
                    "fontes": fontes, "agilera_ok": fontes.get("AGILERA.otf", False)})

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
        preview_url = upload_imagem(card, CLOUDINARY_PREVIEW, card_id)
        if not preview_url:
            return jsonify({"erro": "Falha no upload do preview"}), 500
        buf = io.BytesIO()
        card.save(buf, format="JPEG", quality=93)
        _cards_pendentes[card_id] = {
            "tema": tema, "legenda": legenda,
            "imagem_fundo": url_img, "pid_fundo": pid,
            "preview_url": preview_url, "card_bytes": buf.getvalue()}
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

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)))
