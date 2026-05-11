"""
python-api/main.py
API Flask completa — Render
Fontes: AGILERA (títulos), MALGUN/MALGUNBD/MALGUNSL (corpo)
Cores: Paleta oficial AlvoreSer
Dimensões: 1080x1350 (4:5 Instagram)
"""

import os, io, re, uuid, random, json, textwrap, time
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

# ── IAs para geração de legenda ───────────────────────────────────────────────
GROQ_API_KEY   = os.getenv("GROQ_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

GROQ_URL   = "https://api.groq.com/openai/v1/chat/completions"
GEMINI_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    f"gemini-2.5-flash:generateContent?key={GEMINI_API_KEY}"
)

# ── Dimensões ─────────────────────────────────────────────────────────────────
W, H = 1080, 1350
CLOUDINARY_POSTS = "AlvoreSer_Posts"

# ── Paleta Oficial AlvoreSer ──────────────────────────────────────────────────
MARINHO  = (2,   64,  89)
PETROLEO = (27,  121, 125)
TEAL     = (4,   157, 191)
BRANCO   = (244, 246, 248)
LARANJA  = (249, 171, 11)

# ── Fontes ────────────────────────────────────────────────────────────────────
ROOT_DIR  = os.path.dirname(os.path.abspath(__file__))
FONTS_DIR = os.path.join(ROOT_DIR, "..", "src", "Brand", "fonts")

def _font(nome, tamanho):
    try:
        return ImageFont.truetype(os.path.join(FONTS_DIR, nome), tamanho)
    except Exception:
        try:
            return ImageFont.load_default(size=tamanho)
        except Exception:
            return ImageFont.load_default()

def f_titulo(t): return _font("AGILERA.otf",  t)
def f_corpo(t):  return _font("MALGUN.ttf",   t)
def f_bold(t):   return _font("MALGUNBD.ttf", t)
def f_light(t):  return _font("MALGUNSL.ttf", t)

# ── Assinatura ────────────────────────────────────────────────────────────────
ASSINATURA = (
    "\n\n"
    "👨‍💼 Ronilson Nogueira\n"
    "✍️ Psicólogo e Professor\n"
    "🧩 Referência em Autismo e TDAH em Jovens e Adultos\n"
    "CRP 04/57327"
)

# ── Tags para seleção de imagem ───────────────────────────────────────────────
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

# Mapeamento tema → tags (sem dependência de IA)
MAPA_TAGS = {
    "ansiedade":      {"conteudo": ["pessoa_sozinha", "adulto"],        "clima": ["clima_reflexivo", "clima_sereno"]},
    "depressao":      {"conteudo": ["pessoa_sozinha"],                  "clima": ["clima_pesado", "clima_reflexivo"]},
    "autismo":        {"conteudo": ["crianca", "familia", "adulto"],    "clima": ["clima_sereno", "clima_acolhedor"]},
    "tdah":           {"conteudo": ["crianca", "adolescente", "adulto"],"clima": ["clima_energetico", "clima_neutro"]},
    "borderline":     {"conteudo": ["pessoa_sozinha", "adulto"],        "clima": ["clima_reflexivo", "clima_pesado"]},
    "burnout":        {"conteudo": ["adulto", "pessoa_sozinha"],        "clima": ["clima_pesado", "clima_reflexivo"]},
    "relacionamento": {"conteudo": ["casal", "duas_pessoas"],           "clima": ["clima_acolhedor", "clima_sereno"]},
    "familia":        {"conteudo": ["familia", "mae_filho"],            "clima": ["clima_acolhedor", "clima_alegre"]},
    "luto":           {"conteudo": ["pessoa_sozinha"],                  "clima": ["clima_pesado", "clima_reflexivo"]},
    "autoestima":     {"conteudo": ["pessoa_sozinha", "adulto"],        "clima": ["clima_esperancoso", "clima_sereno"]},
    "trauma":         {"conteudo": ["pessoa_sozinha"],                  "clima": ["clima_pesado", "clima_reflexivo"]},
    "terapia":        {"conteudo": ["pessoa_profissional"],             "clima": ["clima_sereno", "clima_acolhedor"]},
    "natureza":       {"conteudo": ["natureza_sol", "natureza_mar"],    "clima": ["clima_sereno", "clima_esperancoso"]},
    "meditacao":      {"conteudo": ["pessoa_sozinha"],                  "clima": ["clima_sereno", "clima_espiritualizado"]},
}

# ─────────────────────────────────────────────────────────────────────────────
# 1. LEGENDA — cascata Groq → Gemini
# ─────────────────────────────────────────────────────────────────────────────
PROMPT_LEGENDA = (
    "Crie uma legenda para um post do Instagram sobre: '{tema}'. "
    "É para o psicólogo Ronilson Nogueira, especialista em Autismo e TDAH, "
    "da clínica AlvoreSer em Coronel Fabriciano/MG. "
    "Tom: acolhedor, humano, reflexivo, não-clínico, para o público geral. "
    "Máximo 150 palavras. Inclua 5 hashtags relevantes no final. "
    "Retorne APENAS o texto da legenda, sem explicações ou markdown."
)

def _groq_legenda(tema: str) -> str:
    if not GROQ_API_KEY:
        raise Exception("GROQ_API_KEY não configurada")
    r = requests.post(
        GROQ_URL,
        headers={"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"},
        json={
            "model": "llama3-8b-8192",
            "messages": [{"role": "user", "content": PROMPT_LEGENDA.format(tema=tema)}],
            "max_tokens": 400,
        },
        timeout=20,
    )
    r.raise_for_status()
    return r.json()["choices"][0]["message"]["content"].strip()

def _gemini_legenda(tema: str) -> str:
    if not GEMINI_API_KEY:
        raise Exception("GEMINI_API_KEY não configurada")
    r = requests.post(
        GEMINI_URL,
        json={"contents": [{"parts": [{"text": PROMPT_LEGENDA.format(tema=tema)}]}]},
        timeout=25,
    )
    if r.status_code == 429:
        raise Exception("Gemini: limite de requisições atingido (429)")
    r.raise_for_status()
    return r.json()["candidates"][0]["content"]["parts"][0]["text"].strip()

def gerar_legenda_ia(tema: str) -> str:
    erros = []

    # 1. Groq
    try:
        legenda = _groq_legenda(tema)
        return legenda + ASSINATURA
    except Exception as e:
        erros.append(f"Groq: {e}")

    # 2. Gemini
    try:
        legenda = _gemini_legenda(tema)
        return legenda + ASSINATURA
    except Exception as e:
        erros.append(f"Gemini: {e}")

    raise Exception("Todas as IAs falharam — " + " | ".join(erros))

# ─────────────────────────────────────────────────────────────────────────────
# 2. SELEÇÃO DE TAGS — por palavras-chave (sem IA)
# ─────────────────────────────────────────────────────────────────────────────
def selecionar_tags(tema: str) -> dict:
    tema_lower = tema.lower()
    for chave, tags in MAPA_TAGS.items():
        if chave in tema_lower:
            return tags
    # fallback aleatório
    return {
        "conteudo": random.sample(TAGS_CONTEUDO, 2),
        "clima": random.sample(TAGS_CLIMA, 2),
    }

def buscar_imagem(tags: dict) -> str | None:
    todas = tags.get("conteudo", []) + tags.get("clima", [])
    random.shuffle(todas)
    for tag in todas:
        try:
            result = cloudinary.api.resources_by_tag(tag, type="upload", max_results=30)
            recursos = [r for r in result.get("resources", []) if CLOUDINARY_POSTS not in r.get("public_id","")]
            if recursos:
                return random.choice(recursos).get("secure_url")
        except Exception:
            continue
    try:
        result = cloudinary.api.resources(type="upload", max_results=50)
        recursos = [r for r in result.get("resources", []) if CLOUDINARY_POSTS not in r.get("public_id","")]
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
        ratio = max(W / img.width, 810 / img.height)
        nw, nh = int(img.width * ratio), int(img.height * ratio)
        img = img.resize((nw, nh), Image.Resampling.LANCZOS)
        left = (nw - W) // 2
        top  = (nh - 810) // 2
        img  = img.crop((left, top, left + W, top + 810))
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

    if imagem_url:
        fundo = preparar_fundo(imagem_url)
        if fundo:
            img.paste(fundo, (0, 0))
        else:
            draw.rectangle([0, 0, W, 810], fill=MARINHO)
    else:
        draw.rectangle([0, 0, W, 810], fill=MARINHO)

    draw = ImageDraw.Draw(img)
    draw.rectangle([0, 0, 12, 810], fill=LARANJA)
    draw.rectangle([0, 800, W, 822], fill=LARANJA)
    draw.ellipse([W - 280, -100, W + 60, 240], fill=PETROLEO)
    draw.ellipse([W - 230, -55,  W + 10, 185], fill=MARINHO)

    ft = f_titulo(88)
    linhas_tema = textwrap.wrap(tema.upper(), width=14)[:3]
    y_tema = 90
    for linha in linhas_tema:
        draw.text((53, y_tema + 3), linha, font=ft, fill=(0, 0, 0))
        draw.text((50, y_tema),     linha, font=ft, fill=BRANCO)
        y_tema += 108

    fl = f_light(26)
    tag_y = y_tema + 18
    draw.rounded_rectangle([50, tag_y, 400, tag_y + 46], radius=23, fill=LARANJA)
    draw.text((70, tag_y + 11), "AlvoreSer · Saúde Mental", font=fl, fill=MARINHO)

    draw.rectangle([0, 822, W, H - 90], fill=BRANCO)
    draw.rectangle([36, 838, 46, H - 100], fill=TEAL)

    legenda_card = legenda.split("👨")[0].strip()
    legenda_card = re.sub(r'#\w+', '', legenda_card).strip()

    y = 845
    linhas = textwrap.wrap(legenda_card, width=34)[:10]
    for i, linha in enumerate(linhas):
        fonte = f_bold(34) if i == 0 else f_corpo(34)
        draw.text((62, y), linha, font=fonte, fill=MARINHO)
        y += 50

    draw.rectangle([0, H - 90, W, H], fill=MARINHO)
    draw.text((60, H - 70), "Ronilson Nogueira", font=f_bold(28), fill=BRANCO)
    draw.text((60, H - 38), "@alvoreser.psi  |  Psicólogo · CRP 04/57327", font=f_light(22), fill=TEAL)
    draw.ellipse([W - 72, H - 72, W - 20, H - 20], fill=LARANJA)

    return img

# ─────────────────────────────────────────────────────────────────────────────
# 5. UPLOAD DO CARD
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
        agora, tema, tema, legenda,
        "Profissional e acolhedor", "✅ Pronta", "Aguardando Postagem", url,
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
    try:
        return jsonify({"legenda": gerar_legenda_ia(tema)})
    except Exception as e:
        return jsonify({"erro": str(e)}), 500

@app.route("/gerar-card", methods=["POST"])
def rota_gerar_card():
    data    = request.get_json() or {}
    tema    = data.get("tema", "").strip()
    legenda = data.get("legenda", "").strip()

    if not tema:
        return jsonify({"erro": "Tema obrigatório"}), 400

    erros_legenda = None

    # 1. Legenda — independente do card
    if not legenda:
        try:
            legenda = gerar_legenda_ia(tema)
        except Exception as e:
            erros_legenda = str(e)
            legenda = ""

    if legenda and "CRP 04/57327" not in legenda:
        legenda = legenda.rstrip() + ASSINATURA

    # 2. Tags e imagem — sem dependência de IA
    tags       = selecionar_tags(tema)
    imagem_url = buscar_imagem(tags)

    # 3. Gera card — sempre executa independente da legenda
    try:
        card     = gerar_card(tema, legenda, imagem_url)
        uid      = f"post_{uuid.uuid4().hex[:8]}"
        card_url = upload_card(card, uid)
        if not card_url:
            return jsonify({"erro": "Falha no upload do card"}), 500
    except Exception as e:
        return jsonify({"erro": f"Erro ao gerar card: {e}"}), 500

    # 4. Planilha
    linha = 0
    try:
        linha = escrever_planilha(tema, legenda, card_url)
    except Exception as e:
        print(f"Erro planilha: {e}")

    resposta = {
        "cloudinary_url": card_url,
        "legenda": legenda,
        "tags_usadas": tags,
        "imagem_fundo": imagem_url,
        "linha_planilha": linha,
        "status": "Aguardando Postagem",
    }

    if erros_legenda:
        resposta["aviso_legenda"] = erros_legenda

    return jsonify(resposta)

@app.route("/atualizar-status", methods=["POST"])
def rota_atualizar_status():
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
