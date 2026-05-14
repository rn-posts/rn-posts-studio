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
    f"gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"
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
VERDE_NEUTRO  = (119, 153, 147)
VERDE_VIVO    = (122, 181, 0)
AMARELO       = (255, 221, 0)

# ── Cor do título por clima do tema ──────────────────────────────────────────
TEMAS_PESADOS   = ["depressao", "luto", "trauma", "burnout", "borderline"]
TEMAS_ENERGIA   = ["tdah", "autoestima", "motivacao"]
TEMAS_EQUILIBRIO= ["autismo", "terapia", "familia", "relacionamento", "ansiedade", "meditacao"]

def cor_titulo(tema: str) -> tuple:
    t = tema.lower()
    for p in TEMAS_PESADOS:
        if p in t:
            return BRANCO
    for e in TEMAS_ENERGIA:
        if e in t:
            return LARANJA
    for eq in TEMAS_EQUILIBRIO:
        if eq in t:
            return TEAL
    return LARANJA

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

def f_titulo(t): return _font("AGILERA.OTF",  t)
def f_corpo(t):  return _font("MALGUN.TTF",   t)
def f_bold(t):   return _font("MALGUNBD.TTF", t)
def f_light(t):  return _font("MALGUNSL.TTF", t)

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
    "Máximo 150 palavras. NÃO inclua hashtags. "
    "Retorne APENAS o texto da legenda, sem explicações ou markdown."
)

GROQ_MODELOS = ["llama3-70b-8192", "llama3-8b-8192", "mixtral-8x7b-32768"]

def _groq_legenda(tema: str) -> str:
    if not GROQ_API_KEY:
        raise Exception("GROQ_API_KEY não configurada")
    ultimo_erro = None
    for modelo in GROQ_MODELOS:
        try:
            r = requests.post(
                GROQ_URL,
                headers={"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"},
                json={
                    "model": modelo,
                    "messages": [{"role": "user", "content": PROMPT_LEGENDA.format(tema=tema)}],
                    "max_tokens": 400,
                },
                timeout=20,
            )
            r.raise_for_status()
            return r.json()["choices"][0]["message"]["content"].strip()
        except Exception as e:
            ultimo_erro = e
            continue
    raise Exception(f"Groq falhou em todos os modelos: {ultimo_erro}")

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
# 3. ANÁLISE DE IMAGEM — luminosidade e sombra dinâmica
# ─────────────────────────────────────────────────────────────────────────────

# Paleta completa para sombra — apenas cores da identidade visual
PALETA_SOMBRA = [
    (2,   64,  89),   # MARINHO
    (27,  121, 125),  # PETROLEO
    (4,   157, 191),  # TEAL
    (119, 153, 147),  # VERDE_NEUTRO
    (122, 181, 0),    # VERDE_VIVO
]

def luminosidade_regiao(img: Image.Image, y_inicio: int, y_fim: int) -> float:
    """Retorna luminosidade média (0=escuro, 255=claro) de uma faixa horizontal."""
    region = img.crop((0, y_inicio, W, y_fim)).convert("L")
    pixels = list(region.getdata())
    return sum(pixels) / len(pixels)

def aplicar_halo(draw, texto, fonte, x, y, cor_halo, raio=8):
    """Halo profissional: camadas concentíricas de opacidade decrescente ao redor do texto.
    Simula blur real usando múltiplos offsets em distâncias variadas."""
    for dist in range(raio, 0, -1):
        alpha = int(180 * (1 - dist / raio))  # mais opaco perto, transparente longe
        for angle in range(0, 360, 30):       # 12 direções ao redor
            import math
            ox = int(dist * math.cos(math.radians(angle)))
            oy = int(dist * math.sin(math.radians(angle)))
            draw.text((x + ox, y + oy), texto, font=fonte, fill=(*cor_halo, alpha))

def melhor_posicao_titulo(img: Image.Image, n_linhas: int) -> int:
    """Encontra a faixa com maior contraste para o título.
    Para imagens claras, prefere a base. Para escuras, prefere o topo."""
    altura_bloco = n_linhas * 108 + 60
    zonas = [
        (H - altura_bloco - 100, H - 100),
        (80, 80 + altura_bloco),
        ((H - altura_bloco) // 2, (H + altura_bloco) // 2),
    ]
    melhor_y = 80
    melhor_score = -1
    for y_ini, y_fim in zonas:
        if y_ini < 0 or y_fim > H:
            continue
        lum = luminosidade_regiao(img, y_ini, y_fim)
        # Score composto: prioriza zonas escuras mas considera extremos (muito claro também lida)
        score = max(255 - lum, lum - 180) if lum > 180 else 255 - lum
        if score > melhor_score:
            melhor_score = score
            melhor_y = y_ini
    return melhor_y

# Paleta completa de sombras — todas as 9 cores da identidade visual
PALETA_SOMBRA = [
    ("marinho",       (2,   64,  89)),
    ("petroleo",      (27,  121, 125)),
    ("teal",          (4,   157, 191)),
    ("verde_neutro",  (119, 153, 147)),
    ("branco",        (244, 246, 248)),
    ("verde_vivo",    (122, 181, 0)),
    ("verde_citrico", (146, 204, 29)),
    ("laranja",       (249, 171, 11)),
    ("amarelo",       (255, 221, 0)),
]

def cor_dominante_regiao(img: Image.Image, y: int, n_linhas: int) -> tuple:
    """Retorna a cor média RGB da região onde o título vai aparecer."""
    altura = min(n_linhas * 108, H - y)
    region = img.crop((0, y, W, y + altura)).resize((50, 20), Image.Resampling.LANCZOS)
    pixels = list(region.convert("RGB").getdata())
    r = sum(p[0] for p in pixels) // len(pixels)
    g = sum(p[1] for p in pixels) // len(pixels)
    b = sum(p[2] for p in pixels) // len(pixels)
    return (r, g, b)

def distancia_cor(c1: tuple, c2: tuple) -> float:
    """Distância euclidiana entre duas cores RGB."""
    return ((c1[0]-c2[0])**2 + (c1[1]-c2[1])**2 + (c1[2]-c2[2])**2) ** 0.5

def sombra_dinamica(img: Image.Image, y: int, n_linhas: int) -> tuple | None:
    """Escolhe a cor de sombra da paleta que mais contrasta com o fundo.
    Sem embaralhamento — sempre a de maior distância real."""
    lum = luminosidade_regiao(img, y, min(y + n_linhas * 108, H))
    if lum < 40:
        return None
    cor_fundo = cor_dominante_regiao(img, y, n_linhas)
    # Sem shuffle — escolhe sempre a cor com maior distância real do fundo
    melhor_cor = max(PALETA_SOMBRA, key=lambda x: distancia_cor(cor_fundo, x[1]))
    return melhor_cor[1]

def preparar_fundo(url: str) -> Image.Image | None:
    try:
        r = requests.get(url, timeout=20)
        r.raise_for_status()
        img = Image.open(io.BytesIO(r.content)).convert("RGB")
        ratio = max(W / img.width, H / img.height)
        nw, nh = int(img.width * ratio), int(img.height * ratio)
        img = img.resize((nw, nh), Image.Resampling.LANCZOS)
        left = (nw - W) // 2
        top  = (nh - H) // 2
        img  = img.crop((left, top, left + W, top + H))
        return img
    except Exception as e:
        print(f"Erro fundo: {e}")
        return None

# ─────────────────────────────────────────────────────────────────────────────
# 4. GERAR CARD 1080x1350
# ─────────────────────────────────────────────────────────────────────────────
def gerar_card(tema: str, legenda: str, imagem_url: str | None) -> Image.Image:
    img  = Image.new("RGB", (W, H), MARINHO)
    draw = ImageDraw.Draw(img)

    fundo = None
    if imagem_url:
        fundo = preparar_fundo(imagem_url)
        if fundo:
            img.paste(fundo, (0, 0))

    draw = ImageDraw.Draw(img)

    # Cor do título baseada no tema / identidade visual
    ct = cor_titulo(tema)

    ft = f_titulo(88)
    linhas_tema = textwrap.wrap(tema.upper(), width=14)[:3]
    n_linhas = len(linhas_tema)

    # Posição dinâmica: encontra melhor zona da imagem para o título
    if fundo:
        y_tema = melhor_posicao_titulo(fundo, n_linhas)
        cor_sombra = sombra_dinamica(fundo, y_tema, n_linhas)
    else:
        y_tema = 90
        cor_sombra = None

    for linha in linhas_tema:
        if cor_sombra:
            aplicar_halo(draw, linha, ft, 50, y_tema, cor_sombra, raio=10)
        draw.text((50, y_tema), linha, font=ft, fill=ct)
        y_tema += 108

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
