"""
scripts/gerar_card.py — AlvoreSer
Uso: python3 gerar_card.py "tema" "legenda"
Gera card 1080×1350 com identidade visual AlvoreSer e sobe no Cloudinary.
Saída: imprime a URL do Cloudinary na última linha (consumida pela Netlify Function)

Fontes: AGILERA.otf, MALGUN.ttf, MALGUNBD.ttf, MALGUNSL.ttf
Coloque em scripts/fonts/ ou ../src/Brand/fonts/
"""

import sys, os, io, re, uuid, math, random
import cloudinary, cloudinary.uploader
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageChops

# ── Paleta oficial AlvoreSer ──────────────────────────────────────────────────
MARINHO      = (2,   64,  89)
PETROLEO     = (27,  121, 125)
TEAL         = (4,   157, 191)
VERDE_NEUTRO = (119, 153, 147)
BRANCO       = (244, 246, 248)
LARANJA      = (249, 171, 11)
PRETO        = (20,  20,  20)

W, H = 1080, 1350
CLOUDINARY_FOLDER = "AlvoreSer_Posts"

cloudinary.config(
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
    api_key=os.getenv("CLOUDINARY_API_KEY"),
    api_secret=os.getenv("CLOUDINARY_API_SECRET"),
)

# ── Fontes — mesmo caminho do main.py ────────────────────────────────────────
_script_dir = os.path.dirname(__file__)
CANDIDATOS_FONTS = [
    os.path.join(_script_dir, "fonts"),
    os.path.join(_script_dir, "..", "src", "Brand", "fonts"),
    os.path.join(_script_dir, "..", "python-api", "fonts"),
]
FONTS_DIR = None
for _c in CANDIDATOS_FONTS:
    _n = os.path.normpath(_c)
    if os.path.isdir(_n) and os.path.isfile(os.path.join(_n, "AGILERA.otf")):
        FONTS_DIR = _n
        break
if not FONTS_DIR:
    FONTS_DIR = os.path.normpath(os.path.join(_script_dir, "fonts"))

def _font(nome, tam):
    p = os.path.join(FONTS_DIR, nome)
    if os.path.isfile(p):
        try:
            return ImageFont.truetype(p, tam)
        except Exception:
            pass
    try:
        return ImageFont.load_default(size=tam)
    except Exception:
        return ImageFont.load_default()

def f_display(t): return _font("AGILERA.otf",  t)
def f_bold(t):    return _font("MALGUNBD.ttf", t)
def f_corpo(t):   return _font("MALGUN.ttf",   t)
def f_light(t):   return _font("MALGUNSL.ttf", t)

def _medir(texto, fonte):
    try:
        bb = fonte.getbbox(texto)
        return bb[2] - bb[0]
    except Exception:
        return len(texto) * 30

def _sombra(img_rgba, texto, fonte, x, y, opacidade=140):
    layer = Image.new("RGBA", (W, H), (0,0,0,0))
    ImageDraw.Draw(layer).text((x+3, y+5), texto, font=fonte, fill=(*MARINHO, 255))
    layer = layer.filter(ImageFilter.GaussianBlur(10))
    r2, g2, b2, a2 = layer.split()
    a2 = a2.point(lambda p: int(p*(opacidade/255.0)))
    img_rgba.paste(Image.merge("RGBA", (r2, g2, b2, a2)), (0,0), Image.merge("RGBA", (r2, g2, b2, a2)))

def gerar_fundo(seed=0):
    """Textura de fundo com gradiente orgânico AlvoreSer."""
    rng = random.Random(seed)
    base = Image.new("RGB", (W, H))
    draw = ImageDraw.Draw(base)
    off  = rng.uniform(0, math.pi*2)
    cor1, cor2 = MARINHO, PETROLEO
    for y in range(H):
        t  = y/H
        t2 = max(0.0, min(1.0, t + math.sin(y/140+off)*0.05))
        r  = int(cor1[0]*(1-t2)+cor2[0]*t2)
        g  = int(cor1[1]*(1-t2)+cor2[1]*t2)
        b  = int(cor1[2]*(1-t2)+cor2[2]*t2)
        for x in range(0, W, 3):
            wx = math.sin(x/200+y/280+off)*0.025
            draw.line([(x,y),(x+3,y)], fill=(
                max(0,min(255,int(r+wx*18))),
                max(0,min(255,int(g+wx*12))),
                max(0,min(255,int(b+wx*8))),
            ))
    return base.filter(ImageFilter.GaussianBlur(1))

def aplicar_overlay(img):
    """Overlay gradiente inferior + faixa lateral esquerda."""
    overlay = Image.new("RGBA", (W, H), (0,0,0,0))
    draw = ImageDraw.Draw(overlay)
    altura = int(H*0.42)
    for y in range(altura):
        prog = y/altura
        draw.line([(0, H-altura+y),(W, H-altura+y)], fill=(*MARINHO, int((prog**1.5)*210)))
    largura = int(W*0.42)
    for x in range(largura):
        prog = 1.0-(x/largura)
        draw.line([(x,0),(x,H)], fill=(*MARINHO, int((prog**1.9)*90)))
    return Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")

def gerar_card(tema: str, legenda: str, seed=None) -> Image.Image:
    if seed is None:
        seed = random.randint(0, 999999)

    base = gerar_fundo(seed)
    base = aplicar_overlay(base)
    img_rgba = base.convert("RGBA")

    MARGIN  = 80
    MAX_PX  = int(W*0.82)
    Y_INI   = int(H*0.54)
    Y_FIM   = int(H*0.88)

    # Divide tema: 1ª palavra = título display, restante = complemento
    palavras = tema.strip().split()
    n = len(palavras)
    if n == 1:
        titulo, complemento = tema.upper(), ""
    elif n == 2:
        titulo, complemento = palavras[0].upper(), palavras[1].title()
    else:
        titulo      = palavras[0].upper()
        complemento = " ".join(palavras[1:]).title()

    nc = len(titulo)
    if   nc <= 8:  tam = 136
    elif nc <= 12: tam = 116
    elif nc <= 16: tam = 100
    elif nc <= 22: tam = 86
    else:          tam = 72

    tam_sub = max(46, int(tam*0.50))
    tam_bdg = 28

    fonte_titulo = f_display(tam)
    fonte_sub    = f_light(tam_sub)
    fonte_badge  = f_corpo(tam_bdg)

    linhas_t = [titulo]   # sem quebra para cards standalone
    linhas_s = [complemento] if complemento else []

    badge_h    = tam_bdg + 16
    badge_gap  = 18
    sub_gap    = 10
    esp_titulo = int(tam  * 1.08)
    esp_sub    = int(tam_sub * 1.22)
    altura_bloco = (badge_h+badge_gap
                    + len(linhas_t)*esp_titulo
                    + (sub_gap+len(linhas_s)*esp_sub if linhas_s else 0))

    zona = Y_FIM - Y_INI
    y0   = Y_INI + max(0, (zona-altura_bloco)//2)
    y0   = max(Y_INI, min(y0, Y_FIM-altura_bloco-16))

    draw = ImageDraw.Draw(img_rgba, "RGBA")

    # Badge
    cat   = "PSICOLOGIA"
    bdg_w = _medir(cat, fonte_badge) + 36
    draw.rounded_rectangle([MARGIN, y0, MARGIN+bdg_w, y0+badge_h], radius=7, fill=(*LARANJA, 235))
    draw.text((MARGIN+18, y0+8), cat, font=fonte_badge, fill=(*PRETO, 255))

    # Título AGILERA
    y = y0 + badge_h + badge_gap
    for linha in linhas_t:
        _sombra(img_rgba, linha, fonte_titulo, MARGIN, y)
        draw = ImageDraw.Draw(img_rgba, "RGBA")
        draw.text((MARGIN, y), linha, font=fonte_titulo, fill=(*BRANCO, 255))
        y += esp_titulo

    # Complemento MALGUNSL
    if linhas_s:
        y += sub_gap
        for linha in linhas_s:
            _sombra(img_rgba, linha, fonte_sub, MARGIN, y, opacidade=110)
            draw = ImageDraw.Draw(img_rgba, "RGBA")
            draw.text((MARGIN, y), linha, font=fonte_sub, fill=(*LARANJA, 235))
            y += esp_sub

    img = img_rgba.convert("RGB")
    draw = ImageDraw.Draw(img, "RGBA")

    # Rodapé
    ROD_Y = H - 90
    draw.line([(MARGIN, ROD_Y-16),(W-MARGIN, ROD_Y-16)], fill=(*LARANJA, 195), width=2)
    f_m = f_bold(33)
    draw.text((MARGIN, ROD_Y), "AlvoreSer", font=f_m, fill=(*BRANCO, 252))
    f_s = f_corpo(24)
    lw  = _medir("AlvoreSer", f_m)
    draw.text((MARGIN+lw+16, ROD_Y+7), "Clínica de Psicologia", font=f_s, fill=(*VERDE_NEUTRO, 200))
    f_c = f_corpo(22)
    crp = "CRP 04/57327"
    draw.text((W-MARGIN-_medir(crp, f_c), ROD_Y+7), crp, font=f_c, fill=(*VERDE_NEUTRO, 165))

    return img


def upload_card(img: Image.Image, public_id: str) -> str:
    buf = io.BytesIO()
    img.save(buf, "JPEG", quality=92)
    buf.seek(0)
    try:
        res = cloudinary.uploader.upload(
            buf, public_id=public_id,
            folder=CLOUDINARY_FOLDER, overwrite=True, resource_type="image")
        return res.get("secure_url", "")
    except Exception as e:
        print(f"Upload erro: {e}", file=sys.stderr)
        return ""


if __name__ == "__main__":
    tema    = sys.argv[1] if len(sys.argv) > 1 else "Saúde Mental"
    legenda = sys.argv[2] if len(sys.argv) > 2 else ""
    seed    = int(sys.argv[3]) if len(sys.argv) > 3 else None

    print(f"Gerando card: {tema}", file=sys.stderr)
    card = gerar_card(tema, legenda, seed)

    uid = f"card_{uuid.uuid4().hex[:8]}"
    print(f"Upload: {uid}", file=sys.stderr)

    url = upload_card(card, uid)
    if url:
        print(f"OK: {url}", file=sys.stderr)
        print(url)   # última linha = URL (consumida pela Netlify Function)
    else:
        print("ERRO: upload falhou", file=sys.stderr)
        sys.exit(1)
