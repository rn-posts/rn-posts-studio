"""
python-api/main.py
API Flask completa — Render
Fontes: AGILERA (títulos), MALGUN/MALGUNBD/MALGUNSL (corpo)
Cores: Paleta oficial AlvoreSer
Dimensões: 1080x1350 (4:5 Instagram)
"""

import os, io, re, uuid, random, json, base64, textwrap, time
import requests, cloudinary, cloudinary.uploader, cloudinary.api
from datetime import datetime
from flask import Flask, request, jsonify
from flask_cors import CORS
from PIL import Image, ImageDraw, ImageFont
from google.oauth2 import service_account
from googleapiclient.discovery import build

app = Flask(__name__)
CORS(app)

# ── Cloudinary ────────────────────────────────────────────────────────────────
cloudinary.config(
    cloud_name = os.getenv("CLOUDINARY_CLOUD_NAME"),
    api_key    = os.getenv("CLOUDINARY_API_KEY"),
    api_secret = os.getenv("CLOUDINARY_API_SECRET"),
)

# ── Google Sheets ─────────────────────────────────────────────────────────────
SPREADSHEET_ID       = "12FT6CQQDNLI9G7KM8wSfHevAKAuRoEi4OsPYy1aH-8A"
SCOPES               = ["https://www.googleapis.com/auth/spreadsheets"]
SERVICE_ACCOUNT_JSON = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON")

# ── Gemini ────────────────────────────────────────────────────────────────────
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_URL     = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    f"gemini-2.0-flash:generateContent?key={GEMINI_API_KEY}"
)

# ── Dimensões ─────────────────────────────────────────────────────────────────
W, H = 1080, 1350
CLOUDINARY_BANCO = "AlvoreSer_Banco"
CLOUDINARY_POSTS = "AlvoreSer_Posts"

# ── Paleta Oficial AlvoreSer ──────────────────────────────────────────────────
MARINHO  = (2,   64,  89)    # #024059 — cor principal
PETROLEO = (27,  121, 125)   # #1B797D
TEAL     = (4,   157, 191)   # #049DBF
VERDE_N  = (119, 153, 147)   # #779993
BRANCO   = (244, 246, 248)   # #F4F6F8
VERDE_V  = (122, 181, 0)     # #7AB500
VERDE_C  = (146, 204, 29)    # #92CC1D
LARANJA  = (249, 171, 11)    # #F9AB0B — destaque/alvorecer
AMARELO  = (255, 221, 0)     # #FFDD00

# ── Fontes — caminho relativo à raiz do repositório ───────────────────────────
ROOT_DIR  = os.path.join(os.path.dirname(__file__), "..")
FONTS_DIR = os.path.join(ROOT_DIR, "src", "Brand", "fonts")

def _font(nome, tamanho):
    """Carrega fonte com fallback automático."""
    try:
        return ImageFont.truetype(os.path.join(FONTS_DIR, nome), tamanho)
    except Exception:
        try:
            return ImageFont.load_default(size=tamanho)
        except Exception:
            return ImageFont.load_default()

def f_titulo(t):  return _font("AGILERA.otf",   t)   # títulos/tema
def f_corpo(t):   return _font("MALGUN.ttf",    t)   # corpo legenda
def f_bold(t):    return _font("MALGUNBD.ttf",  t)   # destaque legenda
def f_light(t):   return _font("MALGUNSL.ttf",  t)   # rodapé/subtítulos

# ── Assinatura fixa ───────────────────────────────────────────────────────────
ASSINATURA = (
    "\n\n"
    "👨‍💼 Ronilson Nogueira\n"
    "✍️ Psicólogo e Professor\n"
    "🧩 Referência em Autismo e TDAH em Jovens e Adultos\n"
    "CRP 04/57327"
)

# ── Tags para seleção inteligente de imagem ───────────────────────────────────
TAGS_CONTEUDO = [
    "pessoa_sozinha", "casal", "familia", "crianca", "adolescente",
    "adulto", "idoso", "grupo", "natureza_chuva", "natureza_sol",
    "natureza_mar", "natureza_floresta", "ambiente_sereno",
    "ambiente_urbano", "abstrato", "foto_profissional",
]
TAGS_CLIMA = [
    "clima_sereno", "clima_reflexivo", "clima_alegre",
    "clima_pesado", "clima_neutro", "clima_esperancoso",
    "clima_energetico", "clima_acolhedor",
]

# ─────────────────────────────────────────────────────────────────────────────
# 1. GEMINI — gerar legenda
# ─────────────────────────────────────────────────────────────────────────────
def gerar_legenda_ia(tema: str) -> str:
    prompt = (
        f"Crie uma legenda para um post do Instagram sobre: '{tema}'. "
        "É para o psicólogo Ronilson Nogueira, especialista em Autismo e TDAH, "
        "da clínica AlvoreSer em Coronel Fabriciano/MG. "
        "Tom: acolhedor, humano, reflexivo, não-clínico, para o público geral. "
        "Máximo 150 palavras. Inclua 5 hashtags relevantes no final. "
        "Retorne APENAS o texto da legenda, sem explicações ou markdown."
    )
    try:
        r = requests.post(GEMINI_URL, json={
            "contents": [{"parts": [{"text": prompt}]}]
        }, timeout=20)
        r.raise_for_status()
        legenda = r.json()["candidates"][0]["content"]["parts"][0]["text"]
        return legenda.strip() + ASSINATURA
    except Exception as e:
        return f"Erro ao gerar legenda: {e}"

# ─────────────────────────────────────────────────────────────────────────────
# 2. GEMINI — selecionar tags para imagem usando tema + legenda
# ─────────────────────────────────────────────────────────────────────────────
def selecionar_tags(tema: str, legenda: str) -> dict:
    prompt = (
        f"Tema do post de psicologia: '{tema}'\n"
        f"Legenda: '{legenda[:400]}'\n\n"
        "Escolha tags para selecionar uma imagem de fundo adequada.\n"
        "Responda APENAS em JSON válido, sem markdown:\n"
        '{"conteudo": ["tag1", "tag2"], "clima": ["tag3"]}\n\n'
        f"Tags de conteúdo: {', '.join(TAGS_CONTEUDO)}\n"
        f"Tags de clima: {', '.join(TAGS_CLIMA)}"
    )
    try:
        r = requests.post(GEMINI_URL, json={
            "contents": [{"parts": [{"text": prompt}]}]
        }, timeout=15)
        r.raise_for_status()
        texto = r.json()["candidates"][0]["content"]["parts"][0]["text"]
        texto = texto.strip().replace("```json","").replace("```","").strip()
        return json.loads(texto)
    except Exception:
        return {"conteudo": ["pessoa_sozinha"], "clima": ["clima_reflexivo"]}

def buscar_imagem(tags: dict) -> str | None:
    todas = tags.get("conteudo", []) + tags.get("clima", [])
    random.shuffle(todas)
    for tag in todas:
        try:
            result = cloudinary.api.resources_by_tag(
                tag, type="upload", prefix=CLOUDINARY_BANCO, max_results=30
            )
            recursos = result.get("resources", [])
            if recursos:
                return random.choice(recursos).get("secure_url")
        except Exception:
            continue
    # fallback: qualquer imagem do banco
    try:
        result = cloudinary.api.resources(
            type="upload", prefix=CLOUDINARY_BANCO, max_results=50
        )
        recursos = result.get("resources", [])
        if recursos:
            return random.choice(recursos).get("secure_url")
    except Exception:
        pass
    return None

# ─────────────────────────────────────────────────────────────────────────────
# 3. PREPARAR FUNDO
# ─────────────────────────────────────────────────────────────────────────────
def preparar_fundo(url: str) -> Image.Image | None:
    try:
        r = requests.get(url, timeout=20)
        r.raise_for_status()
        img = Image.open(io.BytesIO(r.content)).convert("RGB")
        # Redimensiona e corta para 1080x810
        ratio = max(W / img.width, 810 / img.height)
        nw, nh = int(img.width * ratio), int(img.height * ratio)
        img = img.resize((nw, nh), Image.Resampling.LANCZOS)
        left = (nw - W) // 2
        top  = (nh - 810) // 2
        img  = img.crop((left, top, left + W, top + 810))
        # Overlay marinho semi-transparente para legibilidade do texto
        overlay = Image.new("RGBA", (W, 810), (*MARINHO, 170))
        img = Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")
        return img
    except Exception as e:
        print(f"Erro fundo: {e}")
        return None

# ─────────────────────────────────────────────────────────────────────────────
# 4. GERAR CARD 1080x1350
# ─────────────────────────────────────────────────────────────────────────────
def gerar_card(tema: str, legenda: str, imagem_url: str | None) -> Image.Image:
    img  = Image.new("RGB", (W, H), BRANCO)
    draw = ImageDraw.Draw(img)

    # ── Área superior (810px) — imagem ou cor sólida ──────────────────────────
    if imagem_url:
        fundo = preparar_fundo(imagem_url)
        if fundo:
            img.paste(fundo, (0, 0))
        else:
            draw.rectangle([0, 0, W, 810], fill=MARINHO)
    else:
        draw.rectangle([0, 0, W, 810], fill=MARINHO)

    draw = ImageDraw.Draw(img)

    # Linha lateral laranja (identidade AlvoreSer)
    draw.rectangle([0, 0, 12, 810], fill=LARANJA)

    # Faixa laranja divisora (conceito alvorecer)
    draw.rectangle([0, 800, W, 822], fill=LARANJA)

    # Elemento decorativo — círculo teal canto superior direito
    draw.ellipse([W - 280, -100, W + 60, 240], fill=PETROLEO)
    draw.ellipse([W - 230, -55,  W + 10, 185], fill=MARINHO)

    # ── Tema — fonte AGILERA ──────────────────────────────────────────────────
    ft = f_titulo(88)
    linhas_tema = textwrap.wrap(tema.upper(), width=14)[:3]
    y_tema = 90
    for linha in linhas_tema:
        # Sombra sutil
        draw.text((53, y_tema + 3), linha, font=ft, fill=(0, 0, 0))
        draw.text((50, y_tema),     linha, font=ft, fill=BRANCO)
        y_tema += 108

    # Tag AlvoreSer — fonte MALGUNSL
    fl = f_light(26)
    tag_y = y_tema + 18
    draw.rounded_rectangle([50, tag_y, 400, tag_y + 46], radius=23, fill=LARANJA)
    draw.text((70, tag_y + 11), "AlvoreSer · Saúde Mental", font=fl, fill=MARINHO)

    # ── Área inferior (540px) — legenda ──────────────────────────────────────
    draw.rectangle([0, 822, W, H - 90], fill=BRANCO)

    # Linha teal lateral na área de legenda
    draw.rectangle([36, 838, 46, H - 100], fill=TEAL)

    # Legenda — remove assinatura e hashtags do card visual
    legenda_card = legenda.split("👨")[0].strip()
    legenda_card = re.sub(r'#\w+', '', legenda_card).strip()

    y = 845
    linhas = textwrap.wrap(legenda_card, width=34)[:10]
    for i, linha in enumerate(linhas):
        fonte = f_bold(34) if i == 0 else f_corpo(34)
        draw.text((62, y), linha, font=fonte, fill=MARINHO)
        y += 50

    # ── Rodapé ────────────────────────────────────────────────────────────────
    draw.rectangle([0, H - 90, W, H], fill=MARINHO)
    draw.text((60, H - 70), "Ronilson Nogueira",
              font=f_bold(28), fill=BRANCO)
    draw.text((60, H - 38), "@alvoreser.psi  |  Psicólogo · CRP 04/57327",
              font=f_light(22), fill=TEAL)
    # Ponto laranja decorativo
    draw.ellipse([W - 72, H - 72, W - 20, H - 20], fill=LARANJA)

    return img

# ─────────────────────────────────────────────────────────────────────────────
# 5. UPLOAD DO CARD NO CLOUDINARY
# ─────────────────────────────────────────────────────────────────────────────
def upload_card(img: Image.Image, public_id: str) -> str:
    buffer = io.BytesIO()
    img.save(buffer, format="JPEG", quality=92)
    buffer.seek(0)
    try:
        res = cloudinary.uploader.upload(
            buffer, public_id=public_id,
            folder=CLOUDINARY_POSTS,
            overwrite=True, resource_type="image"
        )
        return res.get("secure_url", "")
    except Exception as e:
        print(f"Upload erro: {e}")
        return ""

# ─────────────────────────────────────────────────────────────────────────────
# 6. GOOGLE SHEETS
# ─────────────────────────────────────────────────────────────────────────────
def get_sheets():
    creds = service_account.Credentials.from_service_account_info(
        json.loads(SERVICE_ACCOUNT_JSON), scopes=SCOPES
    )
    return build("sheets", "v4", credentials=creds)

def escrever_planilha(tema: str, legenda: str, url: str) -> int:
    service = get_sheets()
    agora   = datetime.now().strftime("%Y-%m-%d %H:%M")
    linha   = [
        agora,                        # A — Data/Hora
        tema,                         # B — Tema/Insight
        tema,                         # C — Título
        legenda,                      # D — Legenda Sugerida
        "Profissional e acolhedor",   # E — Tom de Voz
        "✅ Pronta",                  # F — Status da Arte
        "Aguardando Postagem",        # G — Status da Postagem
        url,                          # H — Link da Imagem Final
    ]
    result = service.spreadsheets().values().append(
        spreadsheetId=SPREADSHEET_ID,
        range="A:H",
        valueInputOption="RAW",
        insertDataOption="INSERT_ROWS",
        body={"values": [linha]}
    ).execute()
    try:
        return int(result["updates"]["updatedRange"].split("!A")[1].split(":")[0])
    except Exception:
        return 0

def atualizar_status(linha: int, status: str):
    get_sheets().spreadsheets().values().update(
        spreadsheetId=SPREADSHEET_ID,
        range=f"G{linha}",
        valueInputOption="RAW",
        body={"values": [[status]]}
    ).execute()

# ─────────────────────────────────────────────────────────────────────────────
# 7. ROTAS
# ─────────────────────────────────────────────────────────────────────────────
@app.route("/health", methods=["GET"])
def health():
    return jsonify({
        "status": "ok",
        "dimensoes": f"{W}x{H}",
        "fontes_dir": FONTS_DIR,
        "fontes_existem": os.path.exists(FONTS_DIR),
    })

@app.route("/gerar-legenda", methods=["POST"])
def rota_gerar_legenda():
    data = request.get_json() or {}
    tema = data.get("tema", "").strip()
    if not tema:
        return jsonify({"erro": "Tema obrigatório"}), 400
    return jsonify({"legenda": gerar_legenda_ia(tema)})

@app.route("/gerar-card", methods=["POST"])
def rota_gerar_card():
    data    = request.get_json() or {}
    tema    = data.get("tema", "").strip()
    legenda = data.get("legenda", "").strip()

    if not tema:
        return jsonify({"erro": "Tema obrigatório"}), 400

    try:
        # 1. Gera legenda se não veio editada do painel
        if not legenda:
            legenda = gerar_legenda_ia(tema)

        # 2. Garante assinatura no final
        if "CRP 04/57327" not in legenda:
            legenda = legenda.rstrip() + ASSINATURA

        # 3. Seleciona tags usando tema + legenda completa
        tags = selecionar_tags(tema, legenda)

        # 4. Busca imagem compatível no Cloudinary
        imagem_url = buscar_imagem(tags)

        # 5. Gera card com fontes e cores AlvoreSer
        card = gerar_card(tema, legenda, imagem_url)

        # 6. Sobe card no Cloudinary
        uid      = f"post_{uuid.uuid4().hex[:8]}"
        card_url = upload_card(card, uid)
        if not card_url:
            return jsonify({"erro": "Falha no upload do card"}), 500

        # 7. Escreve linha completa na planilha
        linha = escrever_planilha(tema, legenda, card_url)

        return jsonify({
            "cloudinary_url": card_url,
            "legenda": legenda,
            "tags_usadas": tags,
            "imagem_fundo": imagem_url,
            "linha_planilha": linha,
            "status": "Aguardando Postagem",
        })

    except Exception as e:
        print(f"Erro gerar-card: {e}")
        return jsonify({"erro": str(e)}), 500

@app.route("/atualizar-status", methods=["POST"])
def rota_atualizar_status():
    """Chamada pelo Make após postar. Atualiza coluna G."""
    data   = request.get_json() or {}
    linha  = data.get("linha")
    status = data.get("status", "Postado ✅")
    if not linha:
        return jsonify({"erro": "Linha obrigatória"}), 400
    try:
        atualizar_status(int(linha), status)
        return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"erro": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)))
