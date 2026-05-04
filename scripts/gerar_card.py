"""
scripts/gerar_card.py
Gera um card 1080x1080 com identidade visual AlvoreSer e sobe no Cloudinary.
Uso: python3 gerar_card.py "tema" "legenda"
Saída: imprime a URL do Cloudinary no stdout (última linha)

Dependências: pip install pillow cloudinary
Fontes: baixe DM_Sans e Cormorant_Garamond do Google Fonts e coloque em scripts/fonts/
"""

import sys
import os
import re
import uuid
import textwrap
import cloudinary
import cloudinary.uploader
from PIL import Image, ImageDraw, ImageFont

# ── Identidade Visual AlvoreSer ──────────────────────────────────────────────
VERDE_ESCURO  = (45,  80,  22)
VERDE_MEDIO   = (74,  124, 47)
VERDE_CLARO   = (123, 174, 90)
VERDE_PALIDO  = (200, 221, 184)
CREME         = (245, 240, 232)
CREME_ESCURO  = (234, 226, 212)
TERRA         = (139, 110, 82)
BRANCO        = (255, 255, 255)
TEXTO_ESCURO  = (28,  43,  15)
TEXTO_SUAVE   = (122, 140, 110)

SIZE          = 1080
PASTA_FONTS   = os.path.join(os.path.dirname(__file__), "fonts")
CLOUDINARY_FOLDER = "AlvoreSer_Posts"

# ── Cloudinary ───────────────────────────────────────────────────────────────
cloudinary.config(
    cloud_name = os.getenv("CLOUDINARY_CLOUD_NAME"),
    api_key    = os.getenv("CLOUDINARY_API_KEY"),
    api_secret = os.getenv("CLOUDINARY_API_SECRET"),
)

# ── Helpers de fonte ─────────────────────────────────────────────────────────
def _font(nome, tamanho, fallback_bold=False):
    """Carrega fonte da pasta fonts/, com fallback para fonte padrão."""
    try:
        caminho = os.path.join(PASTA_FONTS, nome)
        return ImageFont.truetype(caminho, tamanho)
    except Exception:
        try:
            return ImageFont.load_default(size=tamanho)
        except Exception:
            return ImageFont.load_default()

def fonte_titulo(tamanho=72):
    return _font("CormorantGaramond-SemiBold.ttf", tamanho)

def fonte_corpo(tamanho=38):
    return _font("DMSans-Regular.ttf", tamanho)

def fonte_corpo_bold(tamanho=38):
    return _font("DMSans-Medium.ttf", tamanho)

# ── Desenho do card ──────────────────────────────────────────────────────────
def gerar_card(tema: str, legenda: str) -> Image.Image:
    img = Image.new("RGB", (SIZE, SIZE), CREME)
    draw = ImageDraw.Draw(img)

    # Fundo superior — bloco verde escuro
    draw.rectangle([0, 0, SIZE, 360], fill=VERDE_ESCURO)

    # Detalhe geométrico — círculo decorativo
    draw.ellipse([SIZE - 220, -80, SIZE + 60, 200], fill=VERDE_MEDIO)
    draw.ellipse([SIZE - 180, -40, SIZE + 20, 160], fill=VERDE_ESCURO)

    # Linha decorativa inferior do bloco verde
    draw.rectangle([0, 358, SIZE, 368], fill=VERDE_CLARO)

    # Detalhe inferior — bloco terra sutil
    draw.rectangle([0, SIZE - 80, SIZE, SIZE], fill=CREME_ESCURO)
    draw.rectangle([0, SIZE - 82, SIZE, SIZE - 80], fill=VERDE_PALIDO)

    # ── Texto do tema (topo, área verde) ─────────────────────────────────────
    f_tema = fonte_titulo(tamanho=64)
    tema_display = tema.upper()
    max_chars = 28
    if len(tema_display) > max_chars:
        tema_display = tema_display[:max_chars].rsplit(" ", 1)[0] + "..."

    # Sombra do tema
    draw.text((62, 122), tema_display, font=f_tema, fill=(0, 0, 0, 60))
    draw.text((60, 120), tema_display, font=f_tema, fill=CREME)

    # ── Legenda (área creme) ──────────────────────────────────────────────────
    legenda_limpa = re.sub(r'#\w+', '', legenda).strip()  # Remove hashtags do card
    f_corpo = fonte_corpo(tamanho=36)

    # Quebra de linha automática
    linhas = textwrap.wrap(legenda_limpa, width=38)[:7]  # máx 7 linhas
    y_legenda = 410
    espacamento = 52

    for linha in linhas:
        draw.text((60, y_legenda), linha, font=f_corpo, fill=TEXTO_ESCURO)
        y_legenda += espacamento

    # ── Linha decorativa lateral ──────────────────────────────────────────────
    draw.rectangle([36, 400, 44, y_legenda - 10], fill=VERDE_CLARO)

    # ── Marca AlvoreSer (rodapé) ──────────────────────────────────────────────
    f_marca = fonte_corpo_bold(tamanho=30)
    f_sub   = fonte_corpo(tamanho=22)
    draw.text((60, SIZE - 60), "AlvoreSer", font=f_marca, fill=VERDE_MEDIO)
    draw.text((200, SIZE - 54), "Clínica de Psicologia", font=f_sub, fill=TEXTO_SUAVE)

    # Ponto decorativo
    draw.ellipse([44, SIZE - 52, 58, SIZE - 38], fill=VERDE_CLARO)

    return img


# ── Upload Cloudinary ─────────────────────────────────────────────────────────
def upload_card(img: Image.Image, public_id: str) -> str:
    tmp = f"/tmp/{public_id}.jpg"
    img.save(tmp, "JPEG", quality=92)

    try:
        res = cloudinary.uploader.upload(
            tmp,
            public_id=public_id,
            folder=CLOUDINARY_FOLDER,
            overwrite=True,
            resource_type="image",
        )
        return res.get("secure_url", "")
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)


# ── Main ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    tema   = sys.argv[1] if len(sys.argv) > 1 else "Saúde Mental"
    legenda = sys.argv[2] if len(sys.argv) > 2 else ""

    print(f"Gerando card: {tema}")
    card = gerar_card(tema, legenda)

    uid = f"card_{uuid.uuid4().hex[:8]}"
    print(f"Subindo para Cloudinary: {uid}")

    url = upload_card(card, uid)

    if url:
        print(f"OK: {url}")
        # Última linha = URL (consumida pela Netlify Function)
        print(url)
    else:
        print("ERRO: upload falhou", file=sys.stderr)
        sys.exit(1)
