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

CORREÇÕES v17
=============
- CORES_DESTAQUE agora usa as 9 cores da paleta sem repetição (antes MARINHO,
  VERDE_VIVO e VERDE_CITRICO nunca eram sorteados como cor de destaque)
- _escolher_cores_texto: pares agora incluem VERDE_VIVO/VERDE_CITRICO nas
  faixas de luminosidade média/escura
- Busca de zona ótima (antes só na estratégia "posicao_otima", 1 a cada 8
  gerações) agora roda em TODA geração — a posição do texto varia por
  imagem, nunca fixa
- Guarda de contraste real: compara a cor escolhida com a cor MÉDIA real
  (RGB) da zona onde o texto cai, não só a luminosidade — evita letra e
  fundo na mesma cor/tom
- Contorno sutil padrão em todas as estratégias de legibilidade (antes só
  "contorno" e "peso_fonte" desenhavam stroke) + sombra padrão mais forte

CORREÇÕES v18
=============
- CORRIGIDO: rotação de estratégias sempre caindo em "contorno" — causa
  raiz era o disco do Render ser EFÊMERO (reseta a cada deploy/reinicio),
  então o contador persistido sempre voltava a 0. Agora combina o contador
  com o seed da geração, que sempre varia — robusto a reset de disco
- Nova 9ª estratégia "scrim_suave": glow/névoa orgânico (bordas bem
  borradas, nunca um retângulo nítido) atrás do bloco inteiro do título —
  garante contraste independente da cor real da foto por baixo
- Guarda de contraste real agora valida a cor SECUNDÁRIA também, não só a
  principal (corrigia letras sumindo em roupas escuras quando só a
  principal passava no teste)
- Zona mínima do título (Y_MIN_GLOBAL) agora é bem mais alta para fotos
  SEM pessoa (sem risco de cobrir rosto) — antes ficava travada a 44% da
  altura mesmo quando a zona de cima era a mais legível
- Pequeno viés por seed no desempate de zonas — em fundos muito uniformes
  (estúdio, parede lisa) a pontuação de todas as zonas quase empatava e a
  posição acabava sempre igual; o viés garante variedade real sem vencer
  uma zona genuinamente melhor

CORREÇÕES v20
=============
- CORRIGIDO: peso_fonte com stroke 4px (v19) ficava borrado no AGILERA —
  voltou pra 2px
- CORRIGIDO: acento_grafico cobria o corpo da letra e podia usar a mesma
  cor da propria palavra (letra sumindo dentro da barra) — barra agora
  fina, cor sempre oposta a da palavra especifica, com leve sobreposicao
  proposital na base (efeito 3D pedido, v20b) em vez de ficar 100% abaixo
- Y_MIN_GLOBAL para fotos sem pessoa recuado de volta pra 30% da altura
  (era 12% na v18) — reduz o risco em fotos mal-tagueadas como "ronilson"

CORREÇÕES v21
=============
- CORRIGIDO: a rotacao de estrategias (v18) somava seed ao contador do
  disco pra resolver o travamento em "contorno", mas isso tornou a escolha
  praticamente aleatoria — podia repetir estrategia em cards consecutivos,
  sem garantir as 7 em sequencia sem repeticao. Trocado pelo mesmo padrao
  de baralho sem reposicao usado pras fotos (_proxima_foto_baralho):
  embaralha as 7 estrategias, consome uma por vez ate esgotar, so entao
  embaralha um novo ciclo — garante as 7 sem repetir nenhuma antes de
  todas as outras terem sido usadas, e como o baralho embaralhado nunca
  comeca fixo em "contorno", tambem resolve o bug original do disco
  efemero do Render sem precisar do hack de seed

CORREÇÕES v22
=============
- ALTERADO: estrategias de legibilidade agora em sequencia FIXA, sem
  embaralhamento nenhum.
- SUBSTITUIDO: estrategia "cor_por_linha" removida.

CORREÇÕES v23
=============
- REDUZIDO de 7 para 6 estrategias: contorno, glow_glifo, sombra_dupla,
  sombra_adaptativa, peso_fonte, acento_grafico. Indice (0-5) persistido.
- POSICAO CRITERIOSA agora roda SEMPRE em todas as estrategias (nao e
  mais estrategia individual) — leque amplo de zonas candidatas (topo,
  meio, base) testado em toda geracao, texto sempre na melhor posicao.
- REMOVIDO contorno sutil (1px) que sangrava nas estrategias que nao sao
  "contorno" — agora stroke=0 nas demais, destaque vem so da sombra/glow.
- CORRIGIDO peso_fonte: tracking -4 exagerado trocado por -1 sutil,
  stroke 2px trocado por 1px quase invisivel.
- CORRIGIDO acento_grafico: barra agora GROSSA (30% da altura da letra),
  posicionada na base/fundo da palavra como marca-texto, com cantos
  arredondados e palavra redesenhada por cima (ref: imagem da mulher).

CORREÇÕES v25
=============
- REDUZIDO de 6 para 5 estrategias: removido posicao_avancada (a busca
  de zona ja roda em todas as estrategias como parte do pipeline global).
- peso_fonte harmonizado: MALGUN forçado em bold, SEM aumento de tamanho
  do AGILERA — contraste de peso sutil sem exagero (ref: imagem da mulher).
- acento_grafico mais sutil: barra 40% da largura (era 62%), 38% da
  altura (era 52%), sobreposição 12% (era 18%) — âncora visual discreta.

CORREÇÕES v27
=============
- REMOVIDO "acento_grafico" da rotação de estratégias (4 estratégias agora,
  era 5). Passou por várias correções (largura, formato, ancoragem em 1-2
  palavras) e mesmo assim continuou saindo quebrado em geração real — texto
  cruzando o rosto e elemento "vida" flutuando desconectado do resto do
  título. O código da estratégia continua no arquivo (não é chamado mais),
  caso um dia valha revisitar do zero.

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
# Overlay: as 9 cores da paleta — a escolha final é filtrada por contraste
# contra a cor dominante da foto (ver _escolher_cor_overlay), garantindo que
# a cor usada combine com aquela imagem específica.
CORES_OVERLAY_PERMITIDAS = PALETA_9

# Destaque de texto: todas as 9 cores
CORES_DESTAQUE = [
    LARANJA, AMARELO, TEAL, BRANCO, VERDE_NEUTRO,
    PETROLEO, VERDE_VIVO, VERDE_CITRICO, MARINHO,
]
# v17: as 9 posições agora cobrem as 9 cores da paleta sem repetição — antes
# MARINHO, VERDE_VIVO e VERDE_CITRICO nunca eram sorteados como destaque
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

def _extrair_cores_dominantes(img):
    """Amostra os pixels da foto (reduzida) e conta quantos caem mais perto
    de cada uma das 9 cores da paleta — usado para escolher overlay que
    realmente combina com o que existe na imagem, em vez da cor mais
    diferente da média. Retorna dict {cor_paleta: contagem_de_pixels}."""
    small    = img.convert("RGB").resize((40, 50), Image.Resampling.LANCZOS)
    pixels   = list(small.getdata())
    contagem = {c: 0 for c in PALETA_9}
    for px in pixels:
        mais_perto = min(PALETA_9, key=lambda c: distancia_cor(px, c))
        contagem[mais_perto] += 1
    return contagem

def _escolher_cor_overlay(hist_cores, cor_destaque_texto, seed=0):
    """Overlay escolhido apenas entre cores que REALMENTE aparecem na foto:
    usa a contagem de pixels mais próximos de cada cor da paleta
    (ver _extrair_cores_dominantes) e prioriza as mais representadas de
    fato — garante que a cor combine com o conteúdo real da imagem, em vez
    de escolher a cor mais diferente/contrastante da média. Como a
    distribuição de cores muda com cada foto, isso também evita convergir
    sempre para as mesmas 1-2 cores.
    """
    if not hist_cores:
        return MARINHO
    candidatas = [(cnt, cor) for cor, cnt in hist_cores.items()
                  if cor != cor_destaque_texto and cnt > 0]
    if not candidatas:
        return MARINHO
    candidatas.sort(key=lambda x: -x[0])
    top3 = candidatas[:3]
    _, melhor_cor = top3[seed % len(top3)]
    print(f"[overlay_cor] top3={[(c, cnt) for cnt, c in top3]} → {melhor_cor}")
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

def _linha_est(draw, x, y, texto, fonte, cor, stroke_width=0, stroke_fill=None):
    """Renderiza com ligaturas e glifos alternativos via RAQM ou fallback."""
    if _RAQM_OK:
        try:
            draw.text((x, y), texto, font=fonte, fill=cor,
                      stroke_width=stroke_width, stroke_fill=stroke_fill,
                      features=["+liga", "+aalt", "+calt", "+dlig"])
            return
        except Exception as e:
            print(f"[linha_est] RAQM features erro: {e}")
            try:
                draw.text((x, y), texto, font=fonte, fill=cor,
                          stroke_width=stroke_width, stroke_fill=stroke_fill)
                return
            except Exception: pass
    draw.text((x, y), texto, font=fonte, fill=cor,
              stroke_width=stroke_width, stroke_fill=stroke_fill)

# ── IA ────────────────────────────────────────────────────────────────────────
ASSINATURA = (
    "\n\n\U0001f468\u200d\U0001f4bc Ronilson Nogueira\n"
    "\u270d\ufe0f Psicólogo e Professor\n"
    "\U0001f9e9 Referência em Autismo e TDAH\n"
    "CRP 04/57327"
)
PROMPT_LEGENDA = (
    "Escreva uma legenda para um post de Instagram sobre o tema: '{tema}'.\n\n"
    "VARIAR O ESTILO A CADA VEZ! ESCOLHA UMA DAS OPÇÕES ABAIXO (ALEATORIAMENTE) PARA ABRIR E ENCERRAR:\n"
    "Opção 1: Observação do dia a dia profissional → Afirmação reflexiva final\n"
    "Opção 2: Questionamento sobre uma crença comum → Insight final\n"
    "Opção 3: Contraponto a um equívoco comum → Frase de impacto final\n"
    "Opção 4: Reflexão sobre uma tendência → Reflexão final\n"
    "Opção 5: Insight sobre o tema → Pergunta (apenas às vezes)\n\n"
    "TOM DE VOZ E ESTRUTURA (NÃO COPIE FRASES — SIGA OS PADRÕES):\n"
    "1. **VOZ**: Escreva como Ronilson Nogueira, psicólogo especialista em autismo e TDAH — com empatia, autoridade sem arrogância.\n"
    "2. **PÚBLICO**: Fale diretamente com adolescentes, jovens e adultos (+12) — NÃO fale sobre crianças ou pais.\n"
    "3. **DETALHES**:\n"
    "   - Use linguagem coloquial, natural, como se estivesse conversando.\n"
    "   - Fique APENAS no tema principal — NÃO adicione conceitos, termos ou histórias que não tenham conexão DIRETA com o tema.\n"
    "   - Use 1 a 3 emojis relevantes por legenda (não mais que isso).\n"
    "   - DIVERSIFIQUE AS FRASES! NÃO repita 'Isso me', 'No meu', 'vejo' várias vezes na mesma legenda.\n\n"
    "REGRAS ABSOLUTAS (NÃO VIOLAR NENHUMA):\n"
    "- NÃO copie frases prontas de nenhum lugar — crie frases originais.\n"
    "- NÃO comece com '[Tema] é...'\n"
    "- NÃO use nomes de autores.\n"
    "- NÃO dê definições de dicionário.\n"
    "- NÃO fale como se você tivesse o problema — fale como o profissional que acompanha.\n"
    "- NÃO use linguagem rebuscada.\n"
    "- NÃO use saudações, hashtags ou marketing.\n"
    "- NÃO adicione a assinatura (ela é adicionada automaticamente).\n"
    "- NÃO forçe termos técnicos ou conceitos que não cabem no tema.\n\n"
    "TAMANHO: 80-150 palavras.\n"
    "RETORNE APENAS A LEGENDA, SEM NADA MAIS."
)
GROQ_MODELOS = ["llama-3.3-70b-versatile", "llama-3.1-8b-instant", "llama-4-scout"]

def _groq_legenda(tema):
    if not GROQ_API_KEY: raise Exception("GROQ_API_KEY nao configurada")
    ultimo = None
    import random
    seed = random.randint(0, 1000000)
    for m in GROQ_MODELOS:
        try:
            r = requests.post(GROQ_URL,
                headers={"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"},
                json={"model": m, "messages": [{"role": "user", "content": PROMPT_LEGENDA.format(tema=tema)}], "max_tokens": 400, "temperature": 1.0, "top_p": 0.95, "seed": seed},
                timeout=20)
            r.raise_for_status()
            return r.json()["choices"][0]["message"]["content"].strip()
        except Exception as e: ultimo = e
    raise Exception(f"Groq falhou: {ultimo}")

def _gemini_legenda(tema):
    if not GEMINI_API_KEY: raise Exception("GEMINI_API_KEY nao configurada")
    import random
    seed = random.randint(0, 1000000)
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GEMINI_API_KEY}"
    r = requests.post(url, json={"contents": [{"parts": [{"text": PROMPT_LEGENDA.format(tema=tema)}]}], "generationConfig": {"temperature": 1.0, "topP": 0.95, "seed": seed}}, timeout=25)
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
_baralho_fotos = {}  # chave (pasta) -> fila embaralhada restante

def _proxima_foto_baralho(chave, recursos):
    """Baralho sem reposição: consome fotos embaralhadas até esgotar a lista,
    depois embaralha um novo ciclo completo — evita repetir a mesma foto antes
    de todas as outras terem sido usadas ao menos uma vez. Fica em memória,
    reseta se o servidor reiniciar."""
    fila = _baralho_fotos.get(chave)
    if not fila:
        fila = recursos[:]
        random.shuffle(fila)
        _baralho_fotos[chave] = fila
        print(f"[baralho] novo ciclo '{chave}' ({len(fila)} fotos)")
    return fila.pop()

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
                c = _proxima_foto_baralho(p, rec)
                print(f"[busca] {c.get('public_id')}")
                return c.get("secure_url"), c.get("public_id", "")
        except Exception as e: print(f"[busca] '{p}': {e}")
    try:
        res = cloudinary.api.resources(type="upload", max_results=50)
        rec = [r for r in res.get("resources", [])
               if CLOUDINARY_POSTS not in r.get("public_id", "")
               and CLOUDINARY_PREVIEW not in r.get("public_id", "")]
        if rec:
            c = _proxima_foto_baralho("_fallback", rec)
            return c.get("secure_url"), c.get("public_id", "")
    except Exception as e: print(f"[busca] fallback: {e}")
    return None, ""

# ── Utilitários ───────────────────────────────────────────────────────────────
def _medir(texto, fonte):
    if not texto: return 0
    try:
        # Para palavras individuais em blocos inline, o bbox pode incluir
        # espaços laterais da fonte. Medimos apenas o conteúdo visível.
        bb = fonte.getbbox(texto)
        return bb[2] - bb[0]
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

_FORMAS_FUNDO = ["pilula", "bandeira", "retangulo_arredondado", "paralelogramo", "capsula_reta"]
_forma_fundo_idx = 0
def _proxima_forma_fundo():
    """Contador sequencial (sem sorteio) — percorre a rotação fixa de formas,
    uma por geração, ciclando ao chegar no fim da lista."""
    global _forma_fundo_idx
    forma = _FORMAS_FUNDO[_forma_fundo_idx % len(_FORMAS_FUNDO)]
    _forma_fundo_idx += 1
    return forma

# ── Estratégias de legibilidade (rotação FIXA: Card1 + 4 estratégias da MULHER) ─
# ROTAÇÃO 1→2→3→4→5→1 (persistida em disco, não é aleatória):
#   1) contorno                 → Card 1 (stroke, permanece)
#   2) glow_glifo               → Card 2 da mulher (Glow Orgânico / Halo de Glifo)
#   3) sombra_adaptativa        → Card 4 da mulher (Sombra Adaptativa / por Linha)
#   4) peso_fonte               → Card 5 da mulher (Peso de Fonte Adaptativo)
#   5) acento_grafico           → Card 6 da mulher (Acento Gráfico Pequeno / Ancoragem Visual)
#
# POSIÇÃO CRITERIOSA (busca de zona ótima) roda SEMPRE em TODAS as estratégias
# (não é mais estratégia individual — a busca de zona já é global).
#
# NÃO MEXEMOS nos preenchimentos (`*`, `-`, `:`) — eles continuam 100% como estão.
_ESTRATEGIAS_LEGIBILIDADE = [
    "contorno", "glow_glifo", "sombra_adaptativa",
    "peso_fonte",
]
_ESTADO_ESTRATEGIA_PATH = os.path.join(os.path.dirname(__file__), "_estado_estrategia.json")

def _proxima_estrategia_legibilidade(seed=None):
    """v25: rotação FIXA de 5 estratégias.
    - Card 1 = contorno (permanece)
    - Cards 2-5 = 4 estratégias da imagem da mulher (glow, sombra adaptativa,
      peso de fonte, acento gráfico)
    Sequência determinística, índice persistido em disco para sobreviver a reinícios.
    POSIÇÃO CRITERIOSA já roda SEMPRE em TODAS (busca de zona global, não é estratégia separada)."""
    indice = 0
    try:
        with open(_ESTADO_ESTRATEGIA_PATH, "r") as f:
            dados = json.load(f)
            indice_salvo = dados.get("indice")
            if isinstance(indice_salvo, int) and 0 <= indice_salvo < len(_ESTRATEGIAS_LEGIBILIDADE):
                indice = indice_salvo
            else:
                indice = 0  # reset se índice antigo (era 0-5, agora 0-4)
    except Exception:
        indice = 0
    estrategia = _ESTRATEGIAS_LEGIBILIDADE[indice]
    proximo = (indice + 1) % len(_ESTRATEGIAS_LEGIBILIDADE)
    print(f"[estrategia_leg] #{indice+1}/5: {estrategia}  (próxima #{proximo+1})")
    try:
        with open(_ESTADO_ESTRATEGIA_PATH, "w") as f:
            json.dump({"indice": proximo}, f)
    except Exception as e:
        print(f"[estrategia_leg] falha ao persistir: {e}")
    return estrategia

# ── Formas de preenchimento ("-palavra"): 6 variações na rotação — cada uma
# calcula seu próprio raio/corte máximo para nunca ultrapassar o padding e
# encostar no texto ─
def _desenhar_forma_fundo(img_rgba, xy, fill, forma="bandeira", pad_x=14, pad_y=10):
    """Cola em img_rgba o preenchimento de destaque (usado com '-antes-da-
    palavra'), em uma de várias formas geométricas. Todas usam o mesmo
    padding (pad_x/pad_y) para posicionar o texto — cada forma calcula
    internamente o maior raio/corte que garante não encostar nas letras.

    Formas disponíveis (na rotação aleatória por seed):
      retangulo             — sem arredondamento, cantos retos
      pilula                — cápsula: as duas pontas totalmente arredondadas
      bandeira              — diagonal: canto superior-esquerdo e inferior-direito
                              arredondados (raio longo), os outros dois retos
      retangulo_arredondado — cantos moderadamente arredondados com borda quadricolor
      paralelogramo         — retângulo inclinado (lados paralelos em diagonal)
      capsula_reta          — lado esquerdo cápsula arredondada, lado direito com
                              canto superior arredondado e inferior reto

    Implementadas mas fora da rotação (disponíveis chamando forma=... direto):
      cupula    — base reta, topo arredondado nos dois cantos superiores
      hexagono  — as duas pontas (esquerda e direita) terminam em ponta
      flamula   — lado esquerdo reto, lado direito termina em ponta
    """
    (x1, y1), (x2, y2) = xy
    x1i, y1i = int(round(x1)), int(round(y1))
    x2i, y2i = int(round(x2)), int(round(y2))
    w, h = x2i - x1i, y2i - y1i
    if w <= 0 or h <= 0:
        return
    SS = 4  # fator de supersampling para bordas suaves
    lw, lh = w * SS, h * SS
    pxs, pys = pad_x * SS, pad_y * SS
    layer = Image.new("RGBA", (lw, lh), (0, 0, 0, 0))
    ld = ImageDraw.Draw(layer)

    def _raio_seguro(ry_local):
        """Maior raio horizontal (rx) tal que a curva elíptica não ultrapassa
        a margem pad_x na altura em que o texto encosta (pad_y da borda)."""
        if ry_local <= 0 or pys >= ry_local:
            return lw
        k = (ry_local - pys) / ry_local
        f = math.sqrt(max(0.0, 1 - k * k))
        if f >= 0.999:
            return lw
        return int((pxs / (1 - f)) * 0.9)

    def _corte_seguro():
        """Maior chanfro reto (ponta de flâmula/hexágono) que ainda garante
        pad_x de folga na altura em que o texto encosta (pad_y da borda)."""
        meio = lh / 2
        if pys >= meio:
            return 0
        return int((pxs / (1 - pys / meio)) * 0.9)

    def _shift_seguro():
        """Maior deslocamento (paralelogramo) que ainda garante pad_x de
        folga na altura em que o texto encosta (pad_y da borda)."""
        if pys >= lh:
            return 0
        return int((pxs / (1 - pys / lh)) * 0.9)

    if forma == "retangulo":
        ld.rectangle([0, 0, lw, lh], fill=fill)

    elif forma == "pilula":
        r = max(0, min(lh // 2, _raio_seguro(lh // 2)))
        if r <= 0:
            ld.rectangle([0, 0, lw, lh], fill=fill)
        else:
            ld.rectangle([r, 0, lw - r, lh], fill=fill)
            ld.ellipse([0, 0, 2 * r, lh], fill=fill)
            ld.ellipse([lw - 2 * r, 0, lw, lh], fill=fill)

    elif forma == "cupula":
        ry = max(1, int(lh * 0.55))
        rx = max(0, min(int(lw * 0.5), _raio_seguro(ry)))
        if rx <= 0:
            ld.rectangle([0, 0, lw, lh], fill=fill)
        else:
            ld.rectangle([0, ry, lw, lh], fill=fill)
            ld.rectangle([rx, 0, lw - rx, ry], fill=fill)
            ld.pieslice([0, 0, 2 * rx, 2 * ry], 180, 270, fill=fill)
            ld.pieslice([lw - 2 * rx, 0, lw, 2 * ry], 270, 360, fill=fill)

    elif forma == "flamula":
        cw = max(0, min(int(lw * 0.35), _corte_seguro()))
        if cw <= 0:
            ld.rectangle([0, 0, lw, lh], fill=fill)
        else:
            ld.polygon([(0, 0), (lw - cw, 0), (lw, lh / 2), (lw - cw, lh), (0, lh)], fill=fill)

    elif forma == "hexagono":
        cw = max(0, min(int(lw * 0.28), _corte_seguro()))
        if cw <= 0 or cw * 2 >= lw:
            ld.rectangle([0, 0, lw, lh], fill=fill)
        else:
            ld.polygon([(cw, 0), (lw - cw, 0), (lw, lh / 2),
                        (lw - cw, lh), (cw, lh), (0, lh / 2)], fill=fill)

    elif forma == "retangulo_arredondado":
        r_alvo = max(1, int(lh * 0.22))
        r = max(0, min(r_alvo, _raio_seguro(r_alvo)))
        if r <= 0:
            ld.rectangle([0, 0, lw, lh], fill=fill)
        else:
            # ── Borda quadricolor: cada lado recebe uma cor da paleta ──
            bw = max(3 * SS, int(min(lh, lw) * 0.085))  # espessura da borda
            fill_a = fill[3] if len(fill) == 4 else 255
            border_colors = [
                (*TEAL,          fill_a),  # topo     — Azul Claro #049DBF
                (*VERDE_CITRICO, fill_a),  # direita  — Verde Cítrico #92CC1D
                (*LARANJA,       fill_a),  # baixo    — Laranja Solar #F9AB0B
                (*MARINHO,       fill_a),  # esquerda — Azul Marinho #024059
            ]
            cx, cy = lw // 2, lh // 2

            # Camada de cores: 4 zonas triangulares a partir do centro
            color_layer = Image.new("RGBA", (lw, lh), (0, 0, 0, 0))
            cd = ImageDraw.Draw(color_layer)
            cd.polygon([(0, 0), (lw, 0), (cx, cy)], fill=border_colors[0])       # topo
            cd.polygon([(lw, 0), (lw, lh), (cx, cy)], fill=border_colors[1])      # direita
            cd.polygon([(lw, lh), (0, lh), (cx, cy)], fill=border_colors[2])      # baixo
            cd.polygon([(0, lh), (0, 0), (cx, cy)], fill=border_colors[3])        # esquerda

            # Máscara externa (retângulo arredondado)
            outer_mask = Image.new("L", (lw, lh), 0)
            om = ImageDraw.Draw(outer_mask)
            om.rectangle([r, 0, lw - r, lh], fill=255)
            om.rectangle([0, r, lw, lh - r], fill=255)
            om.pieslice([0, 0, 2 * r, 2 * r], 180, 270, fill=255)
            om.pieslice([lw - 2 * r, 0, lw, 2 * r], 270, 360, fill=255)
            om.pieslice([0, lh - 2 * r, 2 * r, lh], 90, 180, fill=255)
            om.pieslice([lw - 2 * r, lh - 2 * r, lw, lh], 0, 90, fill=255)

            # Máscara interna (preenchimento — ligeiramente menor)
            ri = max(0, r - bw)
            inner_mask = Image.new("L", (lw, lh), 0)
            im_d = ImageDraw.Draw(inner_mask)
            if ri > 0:
                im_d.rectangle([bw + ri, bw, lw - bw - ri, lh - bw], fill=255)
                im_d.rectangle([bw, bw + ri, lw - bw, lh - bw - ri], fill=255)
                im_d.pieslice([bw, bw, bw + 2 * ri, bw + 2 * ri], 180, 270, fill=255)
                im_d.pieslice([lw - bw - 2 * ri, bw, lw - bw, bw + 2 * ri], 270, 360, fill=255)
                im_d.pieslice([bw, lh - bw - 2 * ri, bw + 2 * ri, lh - bw], 90, 180, fill=255)
                im_d.pieslice([lw - bw - 2 * ri, lh - bw - 2 * ri, lw - bw, lh - bw], 0, 90, fill=255)
            else:
                im_d.rectangle([bw, bw, lw - bw, lh - bw], fill=255)

            # Aplicar máscara externa na camada de cores (recorta o contorno)
            color_layer.putalpha(ImageChops.multiply(color_layer.split()[3], outer_mask))

            # Camada de preenchimento interno
            fill_layer = Image.new("RGBA", (lw, lh), (0, 0, 0, 0))
            fd = ImageDraw.Draw(fill_layer)
            if ri > 0:
                fd.rectangle([bw + ri, bw, lw - bw - ri, lh - bw], fill=fill)
                fd.rectangle([bw, bw + ri, lw - bw, lh - bw - ri], fill=fill)
                fd.pieslice([bw, bw, bw + 2 * ri, bw + 2 * ri], 180, 270, fill=fill)
                fd.pieslice([lw - bw - 2 * ri, bw, lw - bw, bw + 2 * ri], 270, 360, fill=fill)
                fd.pieslice([bw, lh - bw - 2 * ri, bw + 2 * ri, lh - bw], 90, 180, fill=fill)
                fd.pieslice([lw - bw - 2 * ri, lh - bw - 2 * ri, lw - bw, lh - bw], 0, 90, fill=fill)
            else:
                fd.rectangle([bw, bw, lw - bw, lh - bw], fill=fill)

            # Compor: borda colorida + preenchimento
            layer = Image.alpha_composite(color_layer, fill_layer)

    elif forma == "paralelogramo":
        shift = max(0, min(int(lw * 0.25), _shift_seguro()))
        if shift <= 0:
            ld.rectangle([0, 0, lw, lh], fill=fill)
        else:
            ld.polygon([(shift, 0), (lw, 0), (lw - shift, lh), (0, lh)], fill=fill)

    elif forma == "capsula_reta":
        # Lado esquerdo: cápsula (totalmente arredondado)
        # Lado direito: canto superior arredondado, canto inferior reto
        r_esq = max(0, min(lh // 2, _raio_seguro(lh // 2)))  # raio cápsula esquerda
        r_dir = max(1, int(lh * 0.42))  # canto sup-direito bem mais intenso
        r_dir = max(0, min(r_dir, _raio_seguro(r_dir)))
        if r_esq <= 0 and r_dir <= 0:
            ld.rectangle([0, 0, lw, lh], fill=fill)
        else:
            r_esq = max(r_esq, 1)
            r_dir = max(r_dir, 1)
            # Corpo central (entre a cápsula esquerda e o canto direito)
            ld.rectangle([r_esq, 0, lw - r_dir, lh], fill=fill)
            # Cápsula esquerda: elipse completa — cobre até x=2*r_esq, com
            # sobreposição no corpo central garantindo emenda sem costura.
            # (SEM retangulo quadrado por baixo — isso deixava os cantos
            # superior/inferior esquerdos retos por baixo da curva)
            ld.ellipse([0, 0, 2 * r_esq, lh], fill=fill)
            # Lado direito: canto superior arredondado
            ld.rectangle([lw - r_dir, r_dir, lw, lh], fill=fill)  # coluna direita abaixo do arco
            ld.pieslice([lw - 2 * r_dir, 0, lw, 2 * r_dir], 270, 360, fill=fill)  # arco sup-dir
            # Canto inferior direito: reto (já coberto pelo rectangle central + coluna direita)

    else:  # "bandeira" (padrão) — diagonal SUP-ESQUERDO / INF-DIREITO
        ry = max(1, int(lh * 0.30))
        rx = max(0, min(int(lw * 0.5), _raio_seguro(ry)))
        if rx <= 0:
            ld.rectangle([0, 0, lw, lh], fill=fill)
        else:
            ld.rectangle([0, ry, lw, lh - ry], fill=fill)
            ld.rectangle([rx, 0, lw, ry], fill=fill)
            ld.rectangle([0, lh - ry, lw - rx, lh], fill=fill)
            ld.pieslice([0, 0, 2 * rx, 2 * ry], 180, 270, fill=fill)
            ld.pieslice([lw - 2 * rx, lh - 2 * ry, lw, lh], 0, 90, fill=fill)

    layer = layer.resize((w, h), Image.Resampling.LANCZOS)
    img_rgba.paste(layer, (x1i, y1i), layer)

def cores_fundo(img):
    p    = list(img.resize((60, 75), Image.Resampling.LANCZOS).convert("RGB").getdata())
    cf   = tuple(sum(x[i] for x in p) // len(p) for i in range(3))
    ord_ = sorted([c for c in PALETA_9 if c != LARANJA],
                  key=lambda c: distancia_cor(cf, c), reverse=True)
    return (MARINHO, PETROLEO) if sum(cf) / 3 < 60 else (ord_[0], ord_[1])

def luminosidade_media(img):
    arr = np.array(img.convert("RGB").resize((80, 100))).astype(np.float32)
    return float(arr.mean())

def _luminosidade_zona_texto(img):
    """Amostra a luminosidade real (0-255) da região aproximada onde o
    título é desenhado, usando a imagem final (pós color-grade e overlay) —
    evita basear a cor do texto num palpite feito antes do processamento."""
    x0, y0 = SAFE_LEFT, int(H * 0.44)
    x1, y1 = int(W * 0.60), int(H * 0.88)
    recorte = img.crop((x0, y0, x1, y1))
    arr = np.array(recorte.convert("RGB")).astype(np.float32)
    return float(arr.mean())

def cor_dominante(img):
    p = list(img.resize((60, 75), Image.Resampling.LANCZOS).convert("RGB").getdata())
    return tuple(sum(x[i] for x in p) // len(p) for i in range(3))

def eh_foto_ronilson(pid):
    return "ronilson" in pid.lower().replace("\\", "/")

def _avaliar_silhueta_pessoa(rgba):
    """v28: decide se o recorte do rembg encontrou mesmo uma PESSOA (nao uma
    foto de cenario/paisagem onde nao havia assunto real pra separar do
    fundo) — silhueta cobrindo uma fatia plausivel do quadro. Cobertura
    muito baixa (<6%) tende a ser ruido/erro do rembg; cobertura quase
    total (>92%) tende a indicar que a foto inteira ficou como "objeto"
    (sem fundo real pra remover), nao uma pessoa recortada."""
    try:
        alpha = np.array(rgba.split()[3])
        cobertura = float((alpha > 10).sum()) / alpha.size
        print(f"[pessoa] cobertura_silhueta={cobertura:.2f}")
        return 0.06 <= cobertura <= 0.92
    except Exception as e:
        print(f"[pessoa] erro avaliando silhueta: {e}")
        return False

def remover_fundo_rembg(img):
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return Image.open(io.BytesIO(get_rembg()(buf.getvalue()))).convert("RGBA")

def _detectar_pose_em_pe(pessoa_rgba):
    """Heurística (não é um classificador de pose real): usa a máscara alpha
    do recorte rembg para medir a altura da silhueta da pessoa como proporção
    da altura total da imagem. Foto em pé de corpo inteiro tende a preencher
    quase toda a altura (~80%+); foto sentado ocupa uma fatia menor."""
    try:
        alpha = np.array(pessoa_rgba.split()[3])
        linhas = np.where(alpha.max(axis=1) > 10)[0]
        if len(linhas) == 0:
            return True
        proporcao = (linhas[-1] - linhas[0]) / alpha.shape[0]
        em_pe = proporcao >= 0.80
        print(f"[pose] proporcao_altura={proporcao:.2f} -> {'em_pe' if em_pe else 'sentado'}")
        return em_pe
    except Exception as e:
        print(f"[pose] erro: {e}")
        return True

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
    """Retorna (imagem_composta, cabeca_bbox). cabeca_bbox e a faixa
    (x0,y0,x1,y1) em coordenadas do CANVAS final ocupada pela CABEÇA da
    pessoa (topo ~22% da altura do recorte) — usada depois por
    desenhar_titulo pra garantir que o titulo nunca seja desenhado por cima
    do rosto, mesmo quando a pessoa nao fica coladinha na borda direita
    (fotos de gesto/corpo mais largo empurram a faixa da cabeca pra dentro
    da zona onde o texto normalmente vai). v19."""
    pw, ph = pessoa_rgba.size
    nw     = int(pw * H / ph)
    pessoa_rgba = pessoa_rgba.resize((nw, H), Image.Resampling.LANCZOS)
    x = W - nw + 50
    x = max(int(W * 0.35), min(x, W - 120))
    alpha  = pessoa_rgba.split()[3]

    cabeca_bbox = None
    try:
        # v26: a faixa fixa de 22% da ALTURA DO CANVAS so funciona em fotos
        # de CORPO INTEIRO (cabeca e mesmo uma fatia pequena do total). Em
        # fotos de BUSTO/CLOSE (ombros pra cima, ex. retrato) a cabeca ocupa
        # uma fatia bem maior do enquadramento e a faixa fixa ficava curta
        # demais -> o titulo cruzava o rosto (fotos de busto/close).
        # Nova heuristica: acha o SALTO DE LARGURA onde os OMBROS comecam
        # (largura da silhueta aumenta bem alem da largura da cabeca) e usa
        # esse ponto real como fim da faixa da cabeca, em vez de uma % fixa.
        alpha_np = np.array(alpha)
        larguras = np.zeros(alpha_np.shape[0], dtype=np.int32)
        for row in range(alpha_np.shape[0]):
            cols_row = np.where(alpha_np[row] > 10)[0]
            if len(cols_row) > 0:
                larguras[row] = cols_row.max() - cols_row.min()
        linhas_pessoa = np.where(larguras > 0)[0]
        if len(linhas_pessoa) > 0:
            y_topo = int(linhas_pessoa[0])
            janela = larguras[y_topo: y_topo + max(10, int(H * 0.05))]
            largura_cabeca_ref = float(np.median(janela[janela > 0])) if np.any(janela > 0) else 0.0
            y_fim_cabeca = y_topo + int(H * 0.22)  # fallback = comportamento antigo
            if largura_cabeca_ref > 0:
                limite_salto = largura_cabeca_ref * 1.6
                limite_busca = min(alpha_np.shape[0], y_topo + int(H * 0.55))
                for row in range(y_topo, limite_busca):
                    if larguras[row] > limite_salto:
                        y_fim_cabeca = row
                        break
            faixa_cols = np.where(alpha_np[y_topo:y_fim_cabeca, :].max(axis=0) > 10)[0]
            if len(faixa_cols) > 0:
                cx0, cx1 = int(faixa_cols.min()), int(faixa_cols.max())
                cabeca_bbox = (x + cx0 - 20, max(0, y_topo - 10), x + cx1 + 20, y_fim_cabeca + 20)
    except Exception as e:
        print(f"[cabeca] erro: {e}")

    sombra = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    sil    = Image.new("RGBA", (nw, H), (0, 0, 0, 0))
    sil.paste(Image.new("RGB", (nw, H), MARINHO),
              mask=alpha.point(lambda v: int(v * 0.22)))
    sombra.paste(sil, (x - 24, 22), sil)
    sombra = sombra.filter(ImageFilter.GaussianBlur(45))
    res = fundo_rgb.convert("RGBA")
    res = Image.alpha_composite(res, sombra)
    res.paste(pessoa_rgba, (x, 0), pessoa_rgba)
    return res.convert("RGB"), cabeca_bbox

def preparar_foto(url, pid, cor1, cor2, seed):
    """Retorna (img, em_pe, tem_pessoa, cabeca_bbox). v30: REVERTIDO pra v28
    (rembg em toda foto) — ficou lento demais em produção porque roda o
    recorte de fundo em toda geracao, inclusive fotos sem pessoa. Volta a
    decidir tem_pessoa pelo nome do arquivo/pasta (precisa conter
    "ronilson"), como era antes da v28 — so chama rembg quando esse nome
    bate, evitando o custo na maioria das geracoes. Ciente do trade-off:
    fotos dele fora da pasta "banco de imagens/ronilson" voltam a nao ter
    protecao de rosto (ver v28 se precisar reativar). em_pe so tem efeito
    quando tem_pessoa e True. cabeca_bbox (ver compor_pessoa) e None quando
    nao ha pessoa ou o rembg falha."""
    em_pe       = True
    tem_pessoa  = eh_foto_ronilson(pid)
    cabeca_bbox = None
    try:
        r = requests.get(url, timeout=25); r.raise_for_status()
        img   = Image.open(io.BytesIO(r.content)).convert("RGB")
        ratio = max(W / img.width, H / img.height)
        nw, nh = int(img.width * ratio), int(img.height * ratio)
        img   = img.resize((nw, nh), Image.Resampling.LANCZOS)
        l = (nw - W) // 2; t = (nh - H) // 2
        img = img.crop((l, t, l + W, t + H))

        if tem_pessoa:
            print(f"[foto] Ronilson: {pid}")
            fundo = gerar_fundo_rico(cor1, cor2, seed)
            try:
                rgba  = remover_fundo_rembg(img)
                em_pe = _detectar_pose_em_pe(rgba)
                img, cabeca_bbox = compor_pessoa(rgba, fundo)
                img   = aplicar_split_toning(img)
                img   = ImageEnhance.Contrast(img).enhance(1.08)
            except Exception as e:
                print(f"[foto] rembg falhou ({e})")
                img = Image.blend(fundo, img, alpha=0.60)
                img = aplicar_split_toning(img)
        else:
            print(f"[foto] editorial: {pid}")
            img = tratar_foto_editorial(img, cor1, seed)

        return img, em_pe, tem_pessoa, cabeca_bbox
    except Exception as e:
        print(f"[foto] ERRO: {e}"); return None, em_pe, False, None

# ── Overlay ───────────────────────────────────────────────────────────────────
def aplicar_overlay(img, lum_media, layout, seed=0,
                    hist_cores=None, cor_destaque_texto=None,
                    tem_pessoa=False):
    """
    Direções: base(0), topo(1), esquerda(2), direita(3).
    Para fotos com pessoa (rembg): pessoa está à direita → overlay à esquerda (direcao=2).
    Para fotos editoriais: só base ou topo (nunca lateral).
    """
    if lum_media > 160:   alpha_max = 218
    elif lum_media > 120: alpha_max = 192
    elif lum_media > 80:  alpha_max = 168
    else:                 alpha_max = 148

    cor_ov = (_escolher_cor_overlay(hist_cores, cor_destaque_texto or LARANJA, seed)
              if hist_cores else MARINHO)
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
            # v25: *palavras ADJACENTES (só espaço entre elas, ex. "*Nível *2")
            # ficam no MESMO bloco agilera_est — juntas formam uma única unidade
            # de sentido ("Nível 2") e devem poder quebrar linha naturalmente
            # (_quebrar), nunca ser forçadas cada uma pra sua própria linha.
            # Só fecha o bloco corrente quando o estilo realmente muda (igual
            # ao comportamento de ":palavra" abaixo).
            novo = "agilera_est"
            if estilo_atual != novo:
                _fechar()
                estilo_atual = novo
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
def _cor_sombra_adaptativa(cor_fundo, escuro=0.24):
    """v31: sombra_adaptativa agora deriva a cor da propria cor REAL do
    fundo (cor_zona_real, amostrada de verdade na foto) em vez de uma cor
    fixa (8,12,45) que nunca combinava com fundos claros/coloridos (ficava
    'mancha' sobre parede verde, por ex). Escurece a cor real do fundo —
    imita como uma sombra natural se comporta (tom mais escuro do que ja
    esta ali), sempre combinando com a cena em vez de introduzir uma cor
    estranha a ela."""
    if not cor_fundo:
        return (8, 12, 45)
    return tuple(max(0, min(255, int(c * escuro))) for c in cor_fundo)

def _sombra(img_rgba, texto, fonte, x, y, sp=0, forte=False, dupla=False,
            intensidade=None, leve=False, cor_base=None):
    """Sombra do texto — usada pelas estratégias da mulher:
      - padrão (forte=True/False)  → usado por peso_fonte e fallback
      - leve=True                  → contato bem sutil, usado por glow_glifo
                                     pra nao apagar o halo
      - intensidade=0..1           → Card 4 (Sombra Adaptativa / por Linha):
                                     blur e opacidade ESCALAM CONTINUAMENTE
                                     de acordo com a dificuldade da zona;
                                     cor_base (cor real do fundo) define o
                                     tom da sombra (ver _cor_sombra_adaptativa)
      - dupla=True                 → reservado (não está na mulher, não usado)
    Ajustado para a referência visual: SEMPRE suave, sem ser pesado."""
    NEUTRA = (2, 18, 28)
    if intensidade is not None:
        # Card 4 = Sombra Adaptativa (por Linha) — intensidade continua
        blur   = 6 + 22 * intensidade
        opac   = 0.20 + 0.42 * intensidade
        params = [((4, 5), blur, opac, _cor_sombra_adaptativa(cor_base))]
    elif dupla:
        params = [((3, 4), 7, 0.48, NEUTRA), ((18, 24), 46, 0.44, (6, 80, 100))]
    elif leve:
        # Contato bem leve — só ancora a letra no fundo sem competir com
        # o glow (ver glow_glifo em _renderizar_linha_agilera)
        params = [((3, 4), 5, 0.16, NEUTRA)]
    elif forte:
        params = [((5, 6), 13, 0.36, NEUTRA)]
    else:
        # Padrão mulher = mais suave
        params = [((4, 5), 11, 0.30, NEUTRA)]
    for (ox, oy), blur, opac, cor_sombra in params:
        layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        d     = ImageDraw.Draw(layer)
        _linha(d, x + ox, y + oy, texto, fonte, (*cor_sombra, int(255 * opac)), sp)
        layer = layer.filter(ImageFilter.GaussianBlur(blur))
        img_rgba.paste(layer, (0, 0), layer)

def _linha(draw, x, y, texto, fonte, cor, sp=0, stroke_width=0, stroke_fill=None):
    if sp == 0:
        if stroke_width:
            draw.text((x, y), texto, font=fonte, fill=cor,
                      stroke_width=stroke_width, stroke_fill=stroke_fill)
        else:
            draw.text((x, y), texto, font=fonte, fill=cor)
        return
    cursor = x
    for ch in texto:
        if stroke_width:
            draw.text((cursor, y), ch, font=fonte, fill=cor,
                      stroke_width=stroke_width, stroke_fill=stroke_fill)
        else:
            draw.text((cursor, y), ch, font=fonte, fill=cor)
        try:
            bb = fonte.getbbox(ch); cursor += (bb[2] - bb[0]) + sp
        except Exception: cursor += 30 + sp

def _cor_contraste(cor):
    """Retorna BRANCO ou MARINHO — o que mais contrasta com a cor dada —
    usado por contorno/glow, que precisam se opor ao PREENCHIMENTO do texto,
    nao ao fundo da foto."""
    lum = _LUM_COR.get(cor, 0.5)
    return MARINHO if lum > 0.5 else BRANCO

def _cor_acento(cor_pd, seed):
    """v22b: cor do acento gráfico — precisa DESTACAR a palavra sem BRIGAR
    com ela. Quando a palavra é clara, o branco já funciona bem sozinho,
    então continua sendo a opção mais frequente; quando não é branco,
    alterna entre tons escuros com opacidade reduzida (suavização), pra
    funcionar como uma base suave atrás da palavra, não como um bloco de
    cor competindo por atenção. Retorna (cor, alpha)."""
    lum_pd = _LUM_COR.get(cor_pd, 0.5)
    if lum_pd > 0.5:
        opcoes = [(MARINHO, 255), (PETROLEO, 195), (MARINHO, 195)]
    else:
        opcoes = [(BRANCO, 255), (BRANCO, 255), (VERDE_NEUTRO, 175)]
    return opcoes[seed % len(opcoes)]

def _cor_glow_vivida(cor_texto, seed):
    """v27: glow SUAVE tipo retroiluminacao (ref. mulher, Card 2) — NUNCA
    mais um halo neon colorido (v22). A referencia mostra uma luz quase
    branca/creme por tras da letra, nao uma cor saturada da paleta — uma
    cor viva ali competia com o texto e o halo praticamente sumia. Sempre
    um tom claro e quente neutro, funcionando como luz suave atras da
    letra, nunca uma segunda cor de destaque."""
    opcoes = [(250, 244, 225), (255, 250, 236), (246, 238, 214)]
    return opcoes[seed % len(opcoes)]

def _glow_glifo(img_rgba, texto, fonte, x, y, cor_glow, sp=0, raio=40, alpha=235, bulk=7):
    """2. Glow com a silhueta das letras — desenha o texto ENGROSSADO (stroke
    de `bulk` px) numa camada separada, borra bem mais forte que antes
    (raio maior) e cola atras do texto principal. O engrossamento antes de
    borrar e o raio maior sao o que faz a luz aparecer como uma auréola
    visivel ao redor das letras (ref. mulher), em vez de ficar quase toda
    escondida atras do proprio glifo (bug do raio 22px antigo)."""
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    _linha(d, x, y, texto, fonte, (*cor_glow, alpha), sp,
           stroke_width=bulk, stroke_fill=(*cor_glow, alpha))
    layer = layer.filter(ImageFilter.GaussianBlur(raio))
    img_rgba.paste(layer, (0, 0), layer)

def _scrim_suave(img_rgba, x0, y0, x1, y1, cor, alpha=150, raio=60):
    """9. v18: glow/névoa orgânico atrás de TODO o bloco do título (não só das
    letras) — desenha um retângulo arredondado e borra tanto que as bordas
    somem por completo antes de chegar na foto ao redor (nunca fica um
    retângulo nítido). Dá contraste garantido independente da cor real da
    foto por baixo — permite usar qualquer cor de texto mesmo sobre fundos
    difíceis (roupas escuras, texturas, fotos muito claras)."""
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    pad = int(raio * 0.4)
    try:
        d.rounded_rectangle([x0 - pad, y0 - pad, x1 + pad, y1 + pad],
                             radius=max(8, pad), fill=(*cor, alpha))
    except Exception:
        d.rectangle([x0 - pad, y0 - pad, x1 + pad, y1 + pad], fill=(*cor, alpha))
    layer = layer.filter(ImageFilter.GaussianBlur(raio))
    img_rgba.paste(layer, (0, 0), layer)

def _cor_linha_por_fundo(img_rgba, x, y, w, h, idx_linha=0, evitar=()):
    """8. Reavalia a cor do texto POR LINHA, amostrando a luminosidade real
    do fundo exatamente onde aquela linha cai. v22: paleta expandida pra 3
    opções por faixa (era 2) e agora EVITA coincidir com as cores
    principal/secundária que o resto do título já usa (parâmetro `evitar`)
    — antes podia escolher exatamente os mesmos 2 tons do resto do texto,
    ficando visualmente idêntica a qualquer outra estratégia."""
    try:
        x1 = max(0, int(x)); y1 = max(0, int(y))
        x2 = min(W, int(x + max(10, w))); y2 = min(H, int(y + max(10, h)))
        crop = img_rgba.convert("RGB").crop((x1, y1, x2, y2))
        lum  = float(np.array(crop).astype(np.float32).mean()) / 255.0
    except Exception:
        lum = 0.4
    if lum < 0.35:   pares = (BRANCO, AMARELO, VERDE_CITRICO)
    elif lum < 0.5:  pares = (BRANCO, LARANJA, VERDE_VIVO)
    else:            pares = (MARINHO, TEAL, PETROLEO)
    candidatas = [c for c in pares if c not in evitar] or list(pares)
    return candidatas[idx_linha % len(candidatas)]

# ── Variações tipográficas ───────────────────────────────────────────────────
# 6 modos selecionados pelo seed — aplicados a TODOS os blocos
#
# Modo 0: padrão (tracking normal, sem ligaturas)           — sempre disponível
# Modo 1: tracking aberto  (sp positivo, letras espaçadas)   — sempre disponível
# Modo 2: tracking fechado (sp negativo, letras condensadas)  — sempre disponível
# Modo 3: ligaturas via fonttools (aalt+liga)                 — quando disponível
# Modo 4: ligaturas + tracking aberto                        — quando disponível
# Modo 5: fonte estilizada + tamanho levemente menor          — quando disponível
#
# IMPORTANTE: blocos com estilo 'agilera_est' (*palavra) SEMPRE usam
# a fonte estilizada com ligaturas, independentemente do modo.
# O modo tipográfico afeta apenas o tracking (sp) nesses blocos.

# Prepara a fonte estilizada logo no startup para evitar falha em runtime
_preparar_fonte_estilizada()

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

def _fonte_agilera_est_garantida(tam):
    """
    Retorna (fonte, tem_liga) para blocos agilera_est (*palavra).
    RAQM está disponível no Render — usa ele diretamente para ligaturas OpenType.
    Fonttools é tentado primeiro mas raramente funciona no Render.
    Hierarquia:
      1. RAQM com layout_engine (liga+aalt nativas via draw.text features)
      2. fonttools (aalt+liga embutido na fonte)
      3. AGILERA normal (sem ligaturas)
    """
    p = _resolve_font_path("AGILERA.OTF")

    # Tentativa 1: RAQM (funciona no Render)
    if p and _RAQM_OK:
        try:
            fonte = ImageFont.truetype(p, tam, layout_engine=ImageFont.Layout.RAQM)
            print(f"[font_est] RAQM OK tam={tam}")
            return fonte, True
        except Exception as e:
            print(f"[font_est] erro RAQM tam={tam}: {e}")

    # Tentativa 2: fonttools
    est = _preparar_fonte_estilizada()
    if est:
        try:
            fonte = ImageFont.truetype(est, tam)
            print(f"[font_est] fonttools OK tam={tam}")
            return fonte, True
        except Exception as e:
            print(f"[font_est] erro fonttools tam={tam}: {e}")

    # Tentativa 3: AGILERA normal sem ligaturas
    print(f"[font_est] fallback normal tam={tam}")
    return f_display(tam), False

def _fonte_agilera_para_modo(modo, tam):
    """
    Para blocos 'normal': varia pelo modo tipográfico.
    Modos 3/4/5 tentam usar fonte estilizada.
    """
    if modo in (3, 4, 5):
        return _fonte_agilera_est_garantida(tam)
    return f_display(tam), False

def _texto_para_modo(modo, texto):
    """Aplica ligaturas ao texto se o modo suporta."""
    if modo in (3, 4, 5) and _LIGA_SUBST:
        return _aplicar_ligaturas(texto)
    return texto

def _renderizar_linha_agilera(draw, img_rgba, x, y, texto, fonte, cor, sp,
                               tem_liga, sombra_forte, estrategia_leg=None,
                               intensidade_sombra=None, cor_glow=None, seed=0,
                               cor_fundo_zona=None):
    """Renderiza uma linha AGILERA aplicando a estratégia da vez (rotação de 5,
    Card1+4 da mulher). Cada estratégia tem sua assinatura visual própria,
    igual à imagem da mulher de referência:
      - contorno (Card1)        → stroke 3px
      - glow_glifo (Card2)      → halo orgânico colorido atrás das letras
      - sombra_adaptativa (Card4) → intensidade contínua por dificuldade da zona
      - peso_fonte (Card5)      → MALGUN em negrito (contraste de peso harmonizado)
      - acento_grafico (Card6)  → traço sutil na base da última linha (feito depois)
    POSIÇÃO CRITERIOSA roda em TODAS as estratégias (busca global de zona).
    NENHUM contorno/stroke fora da estratégia "contorno".
    Os preenchimentos `*`, `-`, `:` NÃO são mexidos aqui."""

    # PASSO 1: Efeitos de fundo (glow / sombra) — renderizados ANTES do texto
    if estrategia_leg == "glow_glifo":
        # Card 2 = Glow Orgânico (Halo de Glifo) — luz suave atras da letra
        # (ref. mulher) — raio/alpha default da funcao ja calibrados pra
        # essa referencia, so passa a cor. v31: sombra por cima trocada pra
        # "leve" (contato bem sutil) — a sombra padrao (forte) quase apagava
        # o halo, que devia ser o efeito principal desta estrategia.
        _glow_glifo(img_rgba, texto, fonte, x, y, cor_glow or _cor_glow_vivida(cor, seed), sp)
        _sombra(img_rgba, texto, fonte, x, y, sp, leve=True)
    elif estrategia_leg == "sombra_adaptativa" and intensidade_sombra is not None:
        # Card 4 = Sombra Adaptativa (por Linha) — intensidade continua;
        # v31: cor da sombra agora deriva da cor REAL do fundo (cor_fundo_zona)
        # em vez de um azul-escuro fixo que nao combinava com fundos claros
        _sombra(img_rgba, texto, fonte, x, y, sp, intensidade=intensidade_sombra,
                cor_base=cor_fundo_zona)
    else:
        # Restante: sombra padrão suave (igual a mulher)
        _sombra(img_rgba, texto, fonte, x, y, sp, forte=sombra_forte)

    draw = ImageDraw.Draw(img_rgba, "RGBA")
    # PASSO 2: Stroke — EXCLUSIVO do Card 1 (contorno). Fora dele: ZERO stroke.
    if estrategia_leg == "contorno":
        stroke_w, stroke_c = 3, (*_cor_contraste(cor), 255)
    else:
        stroke_w, stroke_c = 0, (0, 0, 0, 0)
    if tem_liga:
        _linha_est(draw, x, y, texto, fonte, (*cor, 255), stroke_w, stroke_c)
    else:
        _linha(draw, x, y, texto, fonte, (*cor, 255), sp, stroke_w, stroke_c)
    return draw

def desenhar_titulo(img, tema, seed, cor_dest=None, cor_fundo_txt=None,
                    cor_overlay=None, tem_pessoa=False, em_pe=True,
                    cabeca_bbox=None):
    img_rgba = img.convert("RGBA")
    MARGIN   = SAFE_MARGIN
    # Para fotos com pessoa à direita: texto na terça parte esquerda
    # Para editoriais: texto na zona segura completa, mas posicionado na base
    MAX_PX   = (int(W * 0.44) - MARGIN) if tem_pessoa else SAFE_MAX_PX
    layout   = seed % 5

    # Estratégia de legibilidade da vez (rotação persistida de 8, ver
    # _proxima_estrategia_legibilidade) — decidida uma vez por card e usada
    # em vários pontos abaixo (posição, fonte, sombra/contorno/glow, cor,
    # acento gráfico).
    estrategia_leg = _proxima_estrategia_legibilidade(seed)
    print(f"[titulo] estrategia_legibilidade={estrategia_leg}")

    if cor_dest is None:
        cor_dest, cor_fundo_txt = _escolher_cor_destaque(seed)

    lum_overlay  = _LUM_COR.get(cor_overlay, 0.3) if cor_overlay else 0.3
    sombra_forte = lum_overlay > 0.45
    print(f"[titulo] layout={layout} lum_overlay={lum_overlay:.2f} MAX_PX={MAX_PX}")

    # Zona vertical do título — calculada CEDO (só depende de tem_pessoa/em_pe/
    # layout) para servir de base tanto na escolha da cor do texto quanto no
    # scrim, usando a luminosidade REAL da área onde o texto vai cair. Antes,
    # essa amostra usava uma faixa fixa que não acompanhava a zona real
    # (calculada só depois) — causava cor de texto e scrim desalinhados com
    # o lugar de fato usado.
    # v18: para fotos SEM pessoa (fundo/textura/ambiente) não existe risco de
    # cobrir rosto — libera o mínimo bem mais alto, permitindo o título subir
    # de verdade quando a zona de cima for a mais legível. Para fotos COM
    # pessoa mantém o mínimo mais baixo (evita cobrir cabeça/rosto).
    Y_MIN_GLOBAL = int(H * 0.44) if tem_pessoa else int(H * 0.30)

    def _avaliar_zona(y_ini_raw, y_fim_raw):
        y_ini = max(Y_MIN_GLOBAL, max(SAFE_TOP, y_ini_raw))
        y_fim = min(SAFE_BOTTOM,  y_fim_raw)
        try:
            crop = img_rgba.convert("RGB").crop(
                (MARGIN, y_ini, min(W, MARGIN + MAX_PX), max(y_ini + 1, y_fim)))
            arr_crop  = np.array(crop).astype(np.float32)
            lum       = float(arr_crop.mean()) / 255.0
            comp      = float(np.array(crop.convert("L")).astype(np.float32).std()) / 90.0
            # v17: cor MÉDIA real (RGB) da zona — usada pela guarda de
            # contraste, que compara cor de verdade, não só luminosidade
            cor_media = tuple(float(arr_crop[:, :, c].mean()) for c in range(3))
            # v26: alem da media do RETANGULO INTEIRO, amostra uma GRADE de
            # sub-regioes (3 linhas x 2 colunas) — fundos mistos (ilustracao
            # com folhas verdes sobre creme, mesa de cor solida dentro de
            # uma foto de ambiente) podem ter media geral "segura" mas uma
            # sub-regiao especifica onde o texto realmente cai pode bater
            # quase na mesma cor do texto escolhido. cor_zona_grid guarda
            # essas sub-medias pra guarda de contraste checar TODAS, nao so
            # a media do retangulo inteiro.
            # v29: grade mais densa (5 linhas x 3 colunas = 15 celulas, era
            # 3x2=6) — grade rala deixava passar bolsoes de cor (camisa
            # branca, parede verde, blazer azul) que ficavam entre as poucas
            # celulas amostradas. Mais celulas = mais dificil um objeto de
            # cor solida escapar de todas elas.
            cor_zona_grid = []
            gh, gw = arr_crop.shape[0], arr_crop.shape[1]
            if gh > 0 and gw > 0:
                n_lin, n_col = 5, 3
                for li in range(n_lin):
                    for ci in range(n_col):
                        y0c = int(gh * li / n_lin); y1c = int(gh * (li + 1) / n_lin)
                        x0c = int(gw * ci / n_col); x1c = int(gw * (ci + 1) / n_col)
                        bloco = arr_crop[y0c:y1c, x0c:x1c]
                        if bloco.size > 0:
                            cor_zona_grid.append(tuple(float(bloco[:, :, c].mean()) for c in range(3)))
        except Exception:
            lum, comp, cor_media, cor_zona_grid = 0.3, 0.5, (90.0, 90.0, 90.0), []
        return y_ini, y_fim, lum, comp, cor_media, cor_zona_grid

    # v23: posição criteriosa SEMPRE ATIVA — leque amplo de zonas candidatas
    # para TODAS as estratégias (não é mais estratégia individual). O texto
    # sempre busca a melhor posição na foto inteira.
    if not tem_pessoa:
        _zona_default     = (int(H * 0.44), int(H * 0.82))
        _candidatas_zona  = [
            (int(H * 0.08), int(H * 0.38)),   # topo
            (int(H * 0.15), int(H * 0.45)),   # topo-meio
            (int(H * 0.25), int(H * 0.55)),   # meio-alto
            (int(H * 0.35), int(H * 0.65)),   # meio
            _zona_default,                      # meio-baixo (padrao)
            (int(H * 0.50), int(H * 0.80)),   # baixo
            (int(H * 0.55), int(H * 0.85)),   # baixo-fundo
            (int(H * 0.60), int(H * 0.90)),   # base
        ]
    else:
        _zonas_pessoa = [
            (int(H * 0.46), int(H * 0.76)),
            (int(H * 0.44), int(H * 0.74)),
            (int(H * 0.48), int(H * 0.78)),
            (int(H * 0.46), int(H * 0.76)),
            (int(H * 0.47), int(H * 0.77)),
        ]
        _zona_default    = _zonas_pessoa[layout % len(_zonas_pessoa)]
        _candidatas_zona = [
            (int(H * 0.12), int(H * 0.40)),   # topo
            (int(H * 0.22), int(H * 0.50)),   # topo-meio
            (int(H * 0.35), int(H * 0.65)),   # meio
            _zona_default,                      # padrao do layout
            (int(H * 0.50), int(H * 0.80)),   # baixo
            (int(H * 0.55), int(H * 0.85)),   # baixo-fundo
            (int(H * 0.60), int(H * 0.92)),   # base
        ]

    # v17: a busca pela zona ótima (antes exclusiva da estratégia
    # "posicao_otima", 1 a cada 8 gerações) agora roda em TODA geração — a
    # posição vertical do texto varia por imagem, nunca fica travada no
    # mesmo lugar. Testa as zonas candidatas e escolhe a que combina MENOR
    # complexidade visual com uma zona mais ESCURA (mais "ancorada", como se
    # tivesse mais sombra natural ali) — evita a zona ruim em vez de tentar
    # compensar depois.
    def _intersecta_cabeca(rx0, ry0, rx1, ry1):
        """v19: True se o retângulo do texto cruza a faixa da cabeça
        (cabeca_bbox, ver compor_pessoa) — usado pra NUNCA escolher uma
        zona que passe por cima do rosto, mesmo em fotos onde a pessoa
        ocupa mais espaço horizontal que o normal (gestos, braços abertos)."""
        if not cabeca_bbox:
            return False
        bx0, by0, bx1, by1 = cabeca_bbox
        return not (rx1 <= bx0 or rx0 >= bx1 or ry1 <= by0 or ry0 >= by1)

    melhor = None; melhor_score = None
    total_zonas = len(_candidatas_zona)
    for _i_c, (yi_raw, yf_raw) in enumerate(_candidatas_zona):
        yi, yf = yi_raw, yf_raw
        if tem_pessoa and em_pe:
            yi -= 35; yf -= 35
        cand = _avaliar_zona(yi, yf)
        _, _, _lum, _comp, _, _ = cand
        # v18: pequeno viés pelo seed — em fundos muito uniformes (estúdio,
        # parede lisa) lum/complexidade quase não variam entre zonas, e sem
        # isso a escolha sempre "empatava" pro mesmo candidato (a variedade
        # ficava só na teoria). O viés é pequeno o bastante pra não vencer
        # uma zona genuinamente melhor.
        vies  = ((seed + _i_c * 37) % 100) / 100.0 * 0.08
        # VIÉS DE POSIÇÃO (v31 — CORRIGIDO): a formula anterior dizia
        # priorizar zonas de BASE/BAIXO, mas o calculo dava o bonus MAIOR
        # (0.45) justamente ao indice 0 (TOPO) — direcao invertida. Alem
        # disso 0.45 e maior que os proprios termos de conteudo real
        # (_comp*0.55 e _lum*0.30, ambos 0..1), entao esse vies sozinho
        # decidia a zona vencedora quase sempre, ignorando o conteudo real
        # de cada foto — por isso a posicao nao variava entre cards. Agora:
        # direcao corrigida (bonus cresce em direcao a base) e peso reduzido
        # pra ser so um desempate leve, deixando luminosidade/complexidade
        # reais decidirem a zona na maioria dos casos.
        vies_posicao = (_i_c / max(1, total_zonas - 1)) * 0.10
        score = _comp * 0.55 + _lum * 0.30 - vies - vies_posicao
        # v19: penalidade forte se a zona cruzar a cabeça — nunca escolhe
        # essa zona a menos que TODAS as outras também cruzem
        if _intersecta_cabeca(MARGIN, yi, MARGIN + MAX_PX, yf):
            score += 5.0
        if melhor is None or score < melhor_score:
            melhor, melhor_score = cand, score
    Y_INI, Y_FIM, lum_zona_real, complexidade_zona, cor_zona_real, cor_zona_grid = melhor
    print(f"[titulo] zona ótima escolhida (busca ativa sempre, v17): "
          f"complexidade={complexidade_zona:.2f} lum={lum_zona_real:.2f}")

    # v19: última rede de segurança — se mesmo assim a zona escolhida ainda
    # cruza a cabeça (caso extremo: todas as candidatas cruzavam), reduz a
    # largura do texto pra parar antes da cabeça, ou empurra a zona pra
    # baixo dela. Texto sobre o rosto é inaceitável, então isso nunca fica
    # só na pontuação — há sempre um corretivo final.
    if _intersecta_cabeca(MARGIN, Y_INI, MARGIN + MAX_PX, Y_FIM):
        cbx0, cby0, cbx1, cby1 = cabeca_bbox
        if cbx0 - MARGIN >= 220:
            MAX_PX = min(MAX_PX, cbx0 - MARGIN - 24)
            print(f"[titulo] MAX_PX reduzido pra nao cruzar a cabeca: {MAX_PX}")
        else:
            Y_INI = min(SAFE_BOTTOM - 150, max(Y_INI, cby1 + 10))
            print(f"[titulo] zona empurrada pra baixo da cabeca: Y_INI={Y_INI}")
        Y_INI, Y_FIM, lum_zona_real, complexidade_zona, cor_zona_real, cor_zona_grid = _avaliar_zona(Y_INI, Y_FIM)

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

    # Forma do preenchimento ("-palavra"): percorre a rotação fixa (sem
    # sorteio), uma forma por geração — mas fica a MESMA em toda a imagem
    # (todas as palavras com "-" usam a mesma forma aqui)
    forma_fundo = _proxima_forma_fundo()
    print(f"[titulo] forma_fundo={forma_fundo}")

    # Fonte AGILERA base com variação de modo
    fa_base, tem_liga_base = _fonte_agilera_para_modo(modo, tam_ag)
    ag_sp = _sp_para_modo(modo, tam_ag)
    fa    = fa_base  # usado para blocos 'normal'
    fb    = f_bold(tam_ml)

    # MALGUN: 3 variações por seed — regular, bold, light
    _malgun_vars = [f_bold(tam_ml), f_corpo(tam_ml), f_light(tam_ml)]
    fb = _malgun_vars[(seed // 6) % 3]

    if estrategia_leg == "peso_fonte":
        # Card 5 = Peso de Fonte Adaptativo (harmonizado):
        # Contraste de peso entre linhas do título — AGILERA em tamanho normal
        # (sem alteração), MALGUN forçado em BOLD para criar contraste natural
        # entre o título e o texto complementar. NENHUM stroke, NENHUM tracking
        # apertado, NENHUM aumento de tamanho — só a variação de peso tipográfico
        # faz o trabalho visual (igual à referência da mulher: "Ansiedade"
        # em peso normal + "Generalizada" em bold, sem exagero).
        fb = f_bold(tam_ml)  # MALGUN sempre em bold nesta estratégia
        print(f"[titulo] peso_fonte (card5): malgun forçado em bold (harmonizado)")
    # contorno, glow_glifo, sombra_adaptativa, acento_grafico não precisam de
    # ajuste de tamanho aqui (glow/sombra/contorno são feitos na renderização;
    # acento_grafico é aplicado no final da função).

    # Paleta de blocos: cores escolhidas para CONTRASTAR com a foto
    # Analisa luminosidade e tom dominante da foto para escolher texto legível
    def _escolher_cores_texto(cor_overlay, lum_overlay):
        """
        Escolhe par de cores (principal, secundaria) de uma lista de PARES
        pré-definidos que já combinam entre si — evita que cada linha do
        título saia de uma cor diferente e sem relação com a outra (ex.:
        laranja + verde na mesma peça). Regras:
        - Fundo escuro (marinho/petróleo) → par claro (branco/amarelo/verde-cítrico)
        - Fundo claro → par escuro (marinho/petróleo/teal/verde-vivo)
        - Sempre varia pelo seed dentro do conjunto coerente, sem misturar
          conjuntos diferentes
        v17: pares expandidos para cobrir as 9 cores da paleta (antes
        VERDE_VIVO e VERDE_CITRICO nunca apareciam aqui)
        """
        if lum_overlay < 0.25:  # fundo muito escuro
            pares = [(BRANCO, AMARELO), (AMARELO, LARANJA),
                     (BRANCO, LARANJA), (TEAL, BRANCO),
                     (VERDE_CITRICO, BRANCO), (AMARELO, VERDE_CITRICO)]
        elif lum_overlay < 0.45:  # fundo escuro-medio
            pares = [(BRANCO, AMARELO), (BRANCO, LARANJA), (AMARELO, TEAL),
                     (VERDE_CITRICO, BRANCO), (LARANJA, VERDE_VIVO)]
        else:  # fundo claro — só cores realmente escuras (nunca BRANCO/AMARELO aqui)
            pares = [(MARINHO, PETROLEO), (MARINHO, TEAL), (PETROLEO, TEAL),
                     (MARINHO, VERDE_CITRICO), (PETROLEO, VERDE_VIVO)]

        return pares[seed % len(pares)]

    _cor_principal, _cor_sec = _escolher_cores_texto(cor_overlay, lum_zona_real)

    # v17: guarda de contraste real — compara a cor escolhida com a cor
    # MÉDIA de verdade (RGB) da zona onde o texto cai (cor_zona_real), não
    # só a luminosidade. Evita letra e fundo na mesma cor/tom (ex.: teal
    # sobre foto azulada) mesmo quando o brilho geral parecia suficiente.
    def _contraste_real_ok(cor):
        # v29: limiar da grade IGUALADO ao da media geral (era mais
        # PERMISSIVO, 70 contra 90 — inconsistente, ja que a grade existe
        # justamente pra pegar os casos que a media mascara, nao pra ser
        # mais tolerante que ela). Ambos em 110 agora (subiu de 90), pra
        # exigir contraste real mais forte e reduzir bordas onde a cor
        # ainda "quase" bate (branco-no-branco, verde-no-verde, azul-no-azul).
        if distancia_cor(cor, cor_zona_real) < 110:
            return False
        for _cg in cor_zona_grid:
            if distancia_cor(cor, _cg) < 110:
                return False
        return True

    if not _contraste_real_ok(_cor_principal):
        _pares_fallback = ([(BRANCO, AMARELO), (AMARELO, LARANJA), (BRANCO, LARANJA),
                            (TEAL, BRANCO), (VERDE_CITRICO, BRANCO)]
                           if lum_zona_real < 0.5 else
                           [(MARINHO, PETROLEO), (MARINHO, TEAL), (PETROLEO, TEAL),
                            (MARINHO, VERDE_CITRICO)])
        for _cp, _cs in _pares_fallback:
            if _contraste_real_ok(_cp) and _contraste_real_ok(_cs):
                _cor_principal, _cor_sec = _cp, _cs
                break
        else:
            _cor_principal, _cor_sec = (
                (BRANCO, AMARELO)
                if distancia_cor(BRANCO, cor_zona_real) >= distancia_cor(MARINHO, cor_zona_real)
                else (MARINHO, BRANCO)
            )
        print(f"[titulo] cor ajustada por baixo contraste real com o fundo: {_cor_principal}")

    # v18: valida a SECUNDÁRIA separadamente da principal — antes só a
    # principal era checada, então um bloco usando a cor secundária podia
    # sumir mesmo com a principal ok (ex.: terno escuro engolindo a cor
    # secundária numa das linhas do título)
    if not _contraste_real_ok(_cor_sec):
        _cor_sec = BRANCO if lum_zona_real < 0.5 else MARINHO
        print(f"[titulo] cor secundária ajustada por baixo contraste real: {_cor_sec}")

    _paleta_blocos = [_cor_principal, _cor_sec, _cor_principal,
                      _cor_sec, _cor_principal, _cor_sec,
                      _cor_principal, _cor_sec, _cor_principal]

    def _cor_b(idx, estilo):
        return _paleta_blocos[idx % len(_paleta_blocos)]

    # Monta lista de (linhas[], fonte, cor, sp, estilo, cor_rect)
    blocos_render = []
    for idx_b, bloco in enumerate(blocos):
        txt = bloco["texto"].strip()
        est = bloco["estilo"]
        if not txt: continue

        cor_b = _cor_b(idx_b, est)

        if est == "agilera_est":
            # agilera_est (*palavra): sempre maior que normal (1.30x)
            # e tracking varia por bloco para criar diversidade visual
            tam_est = int(tam_ag * 1.30)  # 30% maior — diferença clara
            sub_modo = (modo + idx_b) % 3
            sp_est   = _sp_para_modo(sub_modo, tam_est)
            fa_est, tem_liga_est = _fonte_agilera_est_garantida(tam_est)
            txt_out = _aplicar_ligaturas(txt) if tem_liga_est and _LIGA_SUBST else txt
            lns     = _quebrar(txt_out, fa_est, MAX_PX, sp_est)
            blocos_render.append((lns, fa_est, cor_b, sp_est, est, None, tem_liga_est))

        elif est == "malgun":
            lum_b  = _LUM_COR.get(cor_b, 0.5)
            cor_ml = cor_b if lum_b > 0.42 else BRANCO
            # v29: valida a cor do MALGUN individualmente contra o fundo real
            # — antes so o par principal (_cor_principal/_cor_sec) passava
            # pela guarda de contraste; um bloco malgun especifico (ex.
            # "pouco se fala") herdava a cor sem checagem propria e podia
            # cair em branco-no-branco/verde-no-verde quando aquele bloco
            # caia sobre uma parte da foto (camisa, parede) diferente da
            # zona amostrada pro par principal.
            if not _contraste_real_ok(cor_ml):
                for _cand in (BRANCO, MARINHO, AMARELO, TEAL, PETROLEO):
                    if _contraste_real_ok(_cand):
                        cor_ml = _cand
                        break
            blocos_render.append((_quebrar(txt, fb, MAX_PX), fb, cor_ml, 0, est, None, False))

        elif est == "fundo":
            # Retângulo justo — padding reduzido para ficar colado à palavra
            cor_rect_f = _cor_principal
            cor_txt_f  = CORES_FUNDO_TEXTO.get(cor_rect_f, MARINHO)
            lns = _quebrar(txt, fb, MAX_PX - 20)
            blocos_render.append((lns, fb, cor_txt_f, 0, est, cor_rect_f, False))

        else:  # normal — modo tipográfico aplicado
            txt_out = _texto_para_modo(modo, txt)
            lns     = _quebrar(txt_out, fa, MAX_PX, ag_sp)
            blocos_render.append((lns, fa, cor_b, ag_sp, est, None, tem_liga_base))

    if not blocos_render:
        return img_rgba.convert("RGB"), layout

    gap_bloco = max(4, int(tam_ag * 0.06))  # gap menor entre blocos

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

    zona = Y_FIM - Y_INI
    y    = Y_INI + max(0, (zona - h_total) // 2)
    y    = max(Y_INI, min(y, Y_FIM - h_total - 8))
    y    = max(SAFE_TOP + 20, min(y, SAFE_BOTTOM - h_total - 20))

    # Legibilidade do título — a ESTRATÉGIA ATIVA nesta geração decide como o
    # texto se destaca do fundo (contorno, glow, sombra dupla/adaptativa, ou
    # a sombra padrão usada pelas estratégias que atuam em outro ponto:
    # peso de fonte, posição, acento gráfico, cor por linha). Nenhuma delas
    # aplica véu/blur/retângulo sobre a foto — todas atuam no próprio texto.
    largura_titulo = MAX_PX
    try:
        _larguras_titulo = []
        for _lns, _fonte, _cor_txt, _sp, _est, _cor_rect, _tem_liga in blocos_render:
            for _ln in _lns:
                _larguras_titulo.append(_medir_sp(_ln, _fonte, _sp) if _sp else _medir(_ln, _fonte))
        largura_titulo = max(_larguras_titulo) if _larguras_titulo else MAX_PX

        lum_txt            = _LUM_COR.get(_cor_principal, 0.5)
        diff               = abs(lum_zona_real - lum_txt)
        necessidade_cor    = 1 - diff
        necessidade_textu  = min(1.0, complexidade_zona)
        intensidade_sombra = max(0.15, min(1.0, max(necessidade_cor, necessidade_textu)))
        sombra_forte       = sombra_forte or necessidade_cor > 0.55 or necessidade_textu > 0.5
        print(f"[legibilidade] estrategia={estrategia_leg} intensidade_sombra={intensidade_sombra:.2f} "
              f"necessidade_cor={necessidade_cor:.2f} complexidade={complexidade_zona:.2f}")
    except Exception as e:
        intensidade_sombra = 0.5
        print(f"[legibilidade] erro: {e}")

    # (contador _idx_cor_linha removido — cor_por_linha substituida por posicao_criteriosa)
    _palavra_destaque_rect = None  # (x,y,largura,altura) da PALAVRA VENCEDORA
                                     # (ver _candidatos_destaque abaixo), usado
                                     # pelo acento_grafico para ancorar o traco
                                     # bem na base dela
    _palavra_destaque_info = None  # (texto, fonte, cor, sp, tem_liga) da mesma
                                     # palavra, para redesenha-la por cima da barra
    _candidatos_destaque = []      # [(largura_px, rect, info), ...] — todos os
                                     # blocos agilera_est desta geracao; o mais
                                     # LARGO vence como ancora do acento_grafico
                                     # (v25: antes o ULTIMO processado vencia por
                                     # simples sobrescrita — uma palavra curta como
                                     # "2" podia vencer sobre "Nivel", deixando a
                                     # barra do acento quase sem letras por baixo)
    # Variaveis de TRACKING da POSICAO REAL da ultima linha renderizada —
    # usadas pelo acento_grafico para NÃO MAIS errar a posição (que antes
    # usava Y_FIM aproximado e errava feio).
    _ultima_linha_x1 = None        # X1 (inicio, alinhado a esquerda) da ULTIMA linha
    _ultima_linha_y_top = None     # Y de TOPO da ULTIMA linha (topo da bbox)
    _ultima_linha_y_bottom = None  # Y de FUNDO (bottom da bbox) da ULTIMA linha
    _ultima_linha_largura = None   # Largura REAL ocupada pelo texto na ultima linha
    _ultima_linha_cor = None       # Cor usada na ultima linha (para escolher cor do acento)
    _ultima_linha_fonte = None     # Fonte usada na ultima linha
    _ultima_linha_sp = 0           # Tracking (sp) da ultima linha
    _ultima_linha_texto = ""       # Texto da ultima linha (para fallback)

    for gi, grupo in enumerate(grupos):
        if gi > 0: y += gap_bloco
        lns0, f0, *_ = grupo[0]
        esp = int(_altura_linha(f0) * 1.10)

        if len(grupo) == 1:
            lns, fonte, cor_txt, sp, est, cor_rect, tem_liga = grupo[0]
            for linha in lns:
                draw = ImageDraw.Draw(img_rgba, "RGBA")
                if est == "fundo":
                    pad_x, pad_y_top, pad_y_bottom = 14, 10, 10
                    try:
                        w_texto = _medir(linha, fonte)
                        bb = fonte.getbbox(linha)
                        rx1 = MARGIN
                        ry1 = y + bb[1] - pad_y_top
                        rx2 = MARGIN + w_texto + (pad_x * 2)
                        ry2 = y + bb[3] + pad_y_bottom

                        _desenhar_forma_fundo(img_rgba, [(rx1, ry1), (rx2, ry2)],
                                               fill=(*(cor_rect or cor_dest), 235),
                                               forma=forma_fundo, pad_x=pad_x, pad_y=pad_y_top)
                        draw = ImageDraw.Draw(img_rgba, "RGBA")
                        _linha(draw, rx1 + pad_x - bb[0], y, linha, fonte, (*cor_txt, 255), 0)
                        # Tracking: ultima linha = texto do bloco fundo (apenas o texto interno)
                        _ultima_linha_x1 = rx1 + pad_x - bb[0]
                        _ultima_linha_y_top = y + bb[1]
                        _ultima_linha_y_bottom = y + bb[3]
                        _ultima_linha_largura = bb[2] - bb[0]
                        _ultima_linha_cor = cor_txt
                        _ultima_linha_fonte = fonte
                        _ultima_linha_sp = 0
                        _ultima_linha_texto = linha
                    except Exception:
                        _linha(draw, MARGIN, y, linha, fonte, (*cor_txt, 255), 0)
                        # Tracking (fallback)
                        try:
                            bb = fonte.getbbox(linha)
                            _ultima_linha_x1 = MARGIN
                            _ultima_linha_y_top = y + bb[1]
                            _ultima_linha_y_bottom = y + bb[3]
                            _ultima_linha_largura = bb[2] - bb[0]
                        except Exception:
                            _ultima_linha_x1 = MARGIN
                            _ultima_linha_y_top = y
                            _ultima_linha_y_bottom = y + _altura_linha(fonte)
                            _ultima_linha_largura = _medir_sp(linha, fonte, 0) if 0 else _medir(linha, fonte)
                        _ultima_linha_cor = cor_txt
                        _ultima_linha_fonte = fonte
                        _ultima_linha_sp = 0
                        _ultima_linha_texto = linha
                else:
                    _cor_render = cor_txt
                    _renderizar_linha_agilera(draw, img_rgba, MARGIN, y, linha,
                                              fonte, _cor_render, sp, tem_liga, sombra_forte,
                                              estrategia_leg, intensidade_sombra, seed=seed,
                                              cor_fundo_zona=cor_zona_real)
                    # Tracking: atualiza para a linha renderizada
                    try:
                        if tem_liga and _RAQM_OK:
                            _bb = draw.textbbox((MARGIN, y), linha, font=fonte,
                                               features=["+liga", "+aalt", "+calt", "+dlig"])
                        else:
                            _bb = fonte.getbbox(linha)
                        _ultima_linha_x1 = MARGIN
                        _ultima_linha_y_top = y + _bb[1]
                        _ultima_linha_y_bottom = y + _bb[3]
                        if tem_liga and _RAQM_OK:
                            _ultima_linha_largura = _bb[2] - _bb[0]
                        else:
                            _ultima_linha_largura = (_medir_sp(linha, fonte, sp) if sp else _medir(linha, fonte))
                    except Exception:
                        _ultima_linha_x1 = MARGIN
                        _ultima_linha_y_top = y
                        _ultima_linha_y_bottom = y + _altura_linha(fonte)
                        _ultima_linha_largura = _medir_sp(linha, fonte, sp) if sp else _medir(linha, fonte)
                    _ultima_linha_cor = _cor_render
                    _ultima_linha_fonte = fonte
                    _ultima_linha_sp = sp
                    _ultima_linha_texto = linha
                    if est == "agilera_est":
                        # v22b: CORRIGIDO — a largura estimada manualmente
                        # (soma de cada caractere) nao sabia que a palavra
                        # e desenhada com LIGATURAS via RAQM (que conectam/
                        # estreitam as letras de verdade), entao sempre
                        # superestimava a largura real e a barra do acento
                        # sobrava pra direita, passando da letra. Agora mede
                        # o bbox real pos-shaping quando ha ligatura.
                        if tem_liga and _RAQM_OK:
                            try:
                                _bb_real = draw.textbbox((MARGIN, y), linha, font=fonte,
                                                          features=["+liga", "+aalt", "+calt", "+dlig"])
                                _w_est = _bb_real[2] - MARGIN
                            except Exception:
                                _w_est = _medir_sp(linha, fonte, sp) if sp else _medir(linha, fonte)
                        else:
                            _w_est = _medir_sp(linha, fonte, sp) if sp else _medir(linha, fonte)
                        _candidatos_destaque.append((
                            _w_est,
                            (MARGIN, y, _w_est, _altura_linha(fonte)),
                            (linha, fonte, _cor_render, sp, tem_liga),
                        ))
                y += esp
        else:
            total_w = 0
            esp_entre = 8  # valor padrão seguro
            pad_x_fundo = 10 # valor padrão seguro
            for idx_g2, (lns, fonte, cor_txt, sp, est, cor_rect, tem_liga) in enumerate(grupo):
                linha = lns[0] if lns else ""
                if not linha: continue
                w = _medir_sp(linha, fonte, sp) if sp else _medir(linha, fonte)
                if idx_g2 > 0:
                    total_w += esp_entre
                if est == "fundo":
                    total_w += w + pad_x_fundo * 2
                else:
                    total_w += w

            if total_w > MAX_PX:
                # Não cabe inline: renderiza cada bloco em linha própria
                # mas agrupa malgun+fundo+malgun que se seguem
                # em sublinha: malgun antes | fundo | malgun depois
                # Isso evita "onde nada é o" em linha e "suficiente" em outra
                sublinha_tokens = []  # (texto, fonte, cor, sp, est, cor_rect, tem_liga)
                for lns, fonte, cor_txt, sp, est, cor_rect, tem_liga in grupo:
                    for ln in lns:
                        sublinha_tokens.append((ln, fonte, cor_txt, sp, est, cor_rect, tem_liga))

                # Tenta agrupar em até 2 sublinhas
                linha_atual = []; w_atual = 0
                sublinhas = []
                for tok in sublinha_tokens:
                    ln, fonte, cor_txt, sp, est, cor_rect, tem_liga = tok
                    w = _medir_sp(ln, fonte, sp) if sp else _medir(ln, fonte)
                    w_tok = (w + pad_x_fundo * 2) if est == "fundo" else w
                    espaco = esp_entre if linha_atual else 0
                    if w_atual + espaco + w_tok <= MAX_PX:
                        linha_atual.append(tok)
                        w_atual += espaco + w_tok
                    else:
                        if linha_atual: sublinhas.append(linha_atual)
                        linha_atual = [tok]; w_atual = w_tok
                if linha_atual: sublinhas.append(linha_atual)

                for sublinha in sublinhas:
                    x_cursor = MARGIN
                    # Para tracking: pega o bbox combinado de TODOS tokens da sublinha
                    _sl_y_top_list = []
                    _sl_y_bottom_list = []
                    _sl_x_left = x_cursor
                    _sl_x_right = x_cursor
                    _sl_last_cor = None
                    _sl_last_fonte = None
                    _sl_last_sp = 0
                    _sl_last_texto = ""
                    for idx_sl, (ln, fonte, cor_txt, sp, est, cor_rect, tem_liga) in enumerate(sublinha):
                        if idx_sl > 0: x_cursor += esp_entre
                        w = _medir(ln, fonte)
                        draw = ImageDraw.Draw(img_rgba, "RGBA")
                        if est == "fundo":
                            pad_x, pad_y_top, pad_y_bottom = 14, 10, 10
                            gap_before = 7 if idx_sl > 0 else 0
                            x_cursor += gap_before
                            try:
                                bb = fonte.getbbox(ln)
                                rx1=x_cursor; ry1=y+bb[1]-pad_y_top
                                rx2=x_cursor+(bb[2]-bb[0])+(pad_x*2); ry2=y+bb[3]+pad_y_bottom
                                bb0 = bb[0]
                                _txt_x = rx1 + pad_x - bb0
                                _txt_y = y
                                _txt_w = bb[2] - bb[0]
                                _txt_h_top = y + bb[1]
                                _txt_h_bottom = y + bb[3]
                                _sl_y_top_list.append(_txt_h_top)
                                _sl_y_bottom_list.append(_txt_h_bottom)
                                _sl_x_right = max(_sl_x_right, _txt_x + _txt_w)
                                _sl_last_cor = cor_txt
                                _sl_last_fonte = fonte
                                _sl_last_sp = 0
                                _sl_last_texto = ln
                            except Exception:
                                rx1=x_cursor; ry1=y-pad_y_top
                                rx2=x_cursor+w+(pad_x*2); ry2=y+_altura_linha(fonte)+pad_y_bottom
                                bb0 = 0
                                _txt_x = rx1 + pad_x
                                _txt_y = y
                                _txt_w = w
                                _txt_h_top = y
                                _txt_h_bottom = y + _altura_linha(fonte)
                                _sl_y_top_list.append(_txt_h_top)
                                _sl_y_bottom_list.append(_txt_h_bottom)
                                _sl_x_right = max(_sl_x_right, _txt_x + _txt_w)
                                _sl_last_cor = cor_txt
                                _sl_last_fonte = fonte
                                _sl_last_sp = 0
                                _sl_last_texto = ln
                            _desenhar_forma_fundo(img_rgba, [(rx1,ry1),(rx2,ry2)],
                                                  fill=(*(cor_rect or cor_dest),235),
                                                  forma=forma_fundo, pad_x=pad_x, pad_y=pad_y_top)
                            draw = ImageDraw.Draw(img_rgba, "RGBA")
                            _linha(draw, rx1 + pad_x - bb0, y, ln, fonte, (*cor_txt, 255), 0)
                            x_cursor = rx2 + 7
                        else:
                            _cor_render = cor_txt
                            _renderizar_linha_agilera(draw, img_rgba, x_cursor, y, ln,
                                                      fonte, _cor_render, sp, tem_liga, sombra_forte,
                                                      estrategia_leg, intensidade_sombra, seed=seed,
                                                      cor_fundo_zona=cor_zona_real)
                            # Tracking para este token dentro da sublinha
                            try:
                                if tem_liga and _RAQM_OK:
                                    _bb = draw.textbbox((x_cursor, y), ln, font=fonte,
                                                       features=["+liga", "+aalt", "+calt", "+dlig"])
                                    _tw = _bb[2] - _bb[0]
                                else:
                                    _bb = fonte.getbbox(ln)
                                    _tw = _medir_sp(ln, fonte, sp) if sp else (_bb[2] - _bb[0])
                                _sl_y_top_list.append(y + _bb[1])
                                _sl_y_bottom_list.append(y + _bb[3])
                                _sl_x_right = max(_sl_x_right, x_cursor + _tw)
                            except Exception:
                                _tw = _medir_sp(ln, fonte, sp) if sp else w
                                _sl_y_top_list.append(y)
                                _sl_y_bottom_list.append(y + _altura_linha(fonte))
                                _sl_x_right = max(_sl_x_right, x_cursor + _tw)
                            _sl_last_cor = _cor_render
                            _sl_last_fonte = fonte
                            _sl_last_sp = sp
                            _sl_last_texto = ln
                            x_cursor += (_medir_sp(ln, fonte, sp) if sp else w)
                    # Apos todos os tokens da sublinha: atualiza tracking
                    _ultima_linha_x1 = _sl_x_left
                    _ultima_linha_largura = _sl_x_right - _sl_x_left
                    if _sl_y_top_list and _sl_y_bottom_list:
                        _ultima_linha_y_top = min(_sl_y_top_list)
                        _ultima_linha_y_bottom = max(_sl_y_bottom_list)
                    else:
                        _ultima_linha_y_top = y
                        _ultima_linha_y_bottom = y + _altura_linha(sublinha[0][1])
                    _ultima_linha_cor = _sl_last_cor
                    _ultima_linha_fonte = _sl_last_fonte
                    _ultima_linha_sp = _sl_last_sp
                    _ultima_linha_texto = _sl_last_texto
                    y += int(_altura_linha(sublinha[0][1]) * 1.10)
            else:
                x_cursor = MARGIN
                _gi_y_top_list = []
                _gi_y_bottom_list = []
                _gi_x_left = x_cursor
                _gi_x_right = x_cursor
                _gi_last_cor = None
                _gi_last_fonte = None
                _gi_last_sp = 0
                _gi_last_texto = ""
                for idx_g, (lns, fonte, cor_txt, sp, est, cor_rect, tem_liga) in enumerate(grupo):
                    linha = lns[0] if lns else ""
                    if not linha: continue
                    w = _medir(linha, fonte)
                    # Adiciona espaço entre elementos (exceto antes do primeiro)
                    if idx_g > 0:
                        x_cursor += esp_entre
                    draw = ImageDraw.Draw(img_rgba, "RGBA")
                    if est == "fundo":
                        # Espaço simétrico antes/depois da caixa (não cola nas palavras
                        # vizinhas). Padding vertical centralizado — mesma folga em
                        # cima e embaixo do texto, em todas as formas.
                        pad_x, pad_y_top, pad_y_bottom = 14, 10, 10
                        try:
                            w_texto = _medir(linha, fonte)
                            bb = fonte.getbbox(linha)
                            offset_x = 7 if idx_g > 0 else 0
                            rx1 = x_cursor + offset_x
                            ry1 = y + bb[1] - pad_y_top
                            rx2 = x_cursor + offset_x + w_texto + (pad_x * 2)
                            ry2 = y + bb[3] + pad_y_bottom

                            _desenhar_forma_fundo(img_rgba, [(rx1, ry1), (rx2, ry2)],
                                                   fill=(*(cor_rect or cor_dest), 235),
                                                   forma=forma_fundo, pad_x=pad_x, pad_y=pad_y_top)

                            draw = ImageDraw.Draw(img_rgba, "RGBA")
                            _txt_x = rx1 + pad_x - bb[0]
                            _linha(draw, _txt_x, y, linha, fonte, (*cor_txt, 255), 0)
                            _txt_w = bb[2] - bb[0]
                            _gi_y_top_list.append(y + bb[1])
                            _gi_y_bottom_list.append(y + bb[3])
                            _gi_x_right = max(_gi_x_right, _txt_x + _txt_w)
                            _gi_last_cor = cor_txt
                            _gi_last_fonte = fonte
                            _gi_last_sp = 0
                            _gi_last_texto = linha

                            x_cursor = rx2 + 7
                        except Exception as e:
                            print(f"[render] erro bloco fundo: {e}")
                            _gi_y_top_list.append(y)
                            _gi_y_bottom_list.append(y + _altura_linha(fonte))
                            _gi_x_right = max(_gi_x_right, x_cursor + w)
                            _gi_last_cor = cor_txt
                            _gi_last_fonte = fonte
                            _gi_last_sp = 0
                            _gi_last_texto = linha
                            x_cursor += w + 20
                    else:
                        _cor_render = cor_txt
                        _renderizar_linha_agilera(draw, img_rgba, x_cursor, y, linha,
                                                  fonte, _cor_render, sp, tem_liga, sombra_forte,
                                                  estrategia_leg, intensidade_sombra, seed=seed,
                                                  cor_fundo_zona=cor_zona_real)
                        try:
                            if tem_liga and _RAQM_OK:
                                _bb = draw.textbbox((x_cursor, y), linha, font=fonte,
                                                   features=["+liga", "+aalt", "+calt", "+dlig"])
                                _tw = _bb[2] - _bb[0]
                            else:
                                _bb = fonte.getbbox(linha)
                                _tw = _medir_sp(linha, fonte, sp) if sp else (_bb[2] - _bb[0])
                            _gi_y_top_list.append(y + _bb[1])
                            _gi_y_bottom_list.append(y + _bb[3])
                            _gi_x_right = max(_gi_x_right, x_cursor + _tw)
                        except Exception:
                            _tw = _medir_sp(linha, fonte, sp) if sp else w
                            _gi_y_top_list.append(y)
                            _gi_y_bottom_list.append(y + _altura_linha(fonte))
                            _gi_x_right = max(_gi_x_right, x_cursor + _tw)
                        _gi_last_cor = _cor_render
                        _gi_last_fonte = fonte
                        _gi_last_sp = sp
                        _gi_last_texto = linha
                        x_cursor += (_medir_sp(linha, fonte, sp) if sp else w)
                # Após todos os tokens do grupo horizontal inline: atualiza tracking
                _ultima_linha_x1 = _gi_x_left
                _ultima_linha_largura = _gi_x_right - _gi_x_left
                if _gi_y_top_list and _gi_y_bottom_list:
                    _ultima_linha_y_top = min(_gi_y_top_list)
                    _ultima_linha_y_bottom = max(_gi_y_bottom_list)
                else:
                    _ultima_linha_y_top = y
                    _ultima_linha_y_bottom = y + _altura_linha(grupo[0][1])
                _ultima_linha_cor = _gi_last_cor
                _ultima_linha_fonte = _gi_last_fonte
                _ultima_linha_sp = _gi_last_sp
                _ultima_linha_texto = _gi_last_texto
                y += esp

    # v25: entre todos os blocos agilera_est desta geracao, o acento_grafico
    # ancora na palavra MAIS LARGA renderizada (nunca na ultima processada) —
    # corrige o caso de um numero/palavra curta ("2") virar a ancora sozinho.
    if _candidatos_destaque:
        _largura_venc, _rect_venc, _info_venc = max(_candidatos_destaque, key=lambda c: c[0])
        _palavra_destaque_rect = _rect_venc
        _palavra_destaque_info = _info_venc
    elif (_ultima_linha_texto and _ultima_linha_fonte is not None and
          _ultima_linha_x1 is not None and _ultima_linha_y_top is not None):
        # v26: SEM nenhuma *palavra nesta geracao, o acento NAO pode ancorar
        # na ULTIMA LINHA INTEIRA (pode ter 4-5 palavras) — precisa das
        # MESMAS 1-2 palavras de sentido, seja o bloco agilera ou nao. Pega
        # as ultimas 1-2 palavras da ultima linha realmente renderizada
        # (malgun ou normal) e mede a posicao exata delas dentro da linha,
        # pra desenhar a barra e redesenhar so essas palavras por cima —
        # igual ja acontece com *palavras.
        _palavras_linha = _ultima_linha_texto.split()
        if _palavras_linha:
            _n_alvo   = 2 if len(_palavras_linha) >= 2 else 1
            _alvo_txt = " ".join(_palavras_linha[-_n_alvo:])
            _prefixo  = " ".join(_palavras_linha[:-_n_alvo])
            _sp_l     = _ultima_linha_sp or 0
            _off_x = 0
            if _prefixo:
                _off_x = (_medir_sp(_prefixo + " ", _ultima_linha_fonte, _sp_l)
                          if _sp_l else _medir(_prefixo + " ", _ultima_linha_fonte))
            _w_alvo = (_medir_sp(_alvo_txt, _ultima_linha_fonte, _sp_l)
                       if _sp_l else _medir(_alvo_txt, _ultima_linha_fonte))
            _altura_alvo = (_ultima_linha_y_bottom - _ultima_linha_y_top
                            if _ultima_linha_y_bottom else _altura_linha(_ultima_linha_fonte))
            _palavra_destaque_rect = (_ultima_linha_x1 + _off_x, _ultima_linha_y_top,
                                       _w_alvo, _altura_alvo)
            _palavra_destaque_info = (_alvo_txt, _ultima_linha_fonte, _ultima_linha_cor,
                                       _sp_l, False)

    # Card 6 = Acento Gráfico Pequeno (Ancoragem Visual — IGUAL A MULHER):
    # 1) POSIÇÃO: SEMPRE se sobrepõe SÓ aos ~15-20% DE BAIXO da ÚLTIMA LINHA REAL
    #    renderizada (não usa mais Y_FIM estimado, usa os valores trackeados
    #    DURANTE a renderização — x1, y_top, y_bottom, largura REAIS). Serve
    #    como LINHA DE APOIO visual, ancorando o bloco tipográfico na base.
    # 2) COR: NUNCA cor parecida com o texto. Se texto for da família AZUL /
    #    TEAL / MARINHO / PETRÓLEO, acento é CREME (amarelo quente, igual a
    #    mulher). Se texto for claro, acento é MARINHO.
    # 3) LARGURA: ~60% da LARGURA REAL da última linha (medida, não estimada),
    #    mín. 180px, altura fina (~22-26px, igual a mulher).
    # 4) FORMA: cantos arredondados, traço fino alinhado a ESQUERDA com a
    #    última linha do texto (igual a mulher).
    # Os preenchimentos inline `-palavra` não são afetados.
    if estrategia_leg == "acento_grafico":
        try:
            CREME_ACENTO = (247, 231, 173)  # cor da mulher: off-white amarelado

            # 1) COLETA DA POSIÇÃO REAL DA ÚLTIMA LINHA (do tracking durante render)
            # Prioridade:
            #   a) tem palavra destaque (agilera_est via "*palavra*") → usa rect dela
            #   b) tem tracking real de ultima linha (_ultima_linha_*) → usa esses valores
            #   c) fallback: valores aproximados (raríssimo de ocorrer)
            if _palavra_destaque_rect and _palavra_destaque_info:
                px, py, pw, ph = _palavra_destaque_rect
                txt_pd, fonte_pd, cor_pd, sp_pd, liga_pd = _palavra_destaque_info
                ultimo_x1 = px
                ultimo_y_top = py
                ultimo_largura = pw
                ultimo_altura = ph
                ultimo_cor = cor_pd
                ultimo_fonte = fonte_pd
                ultimo_sp = sp_pd
                tem_palavra_destaque = True
            elif (_ultima_linha_y_bottom is not None and
                  _ultima_linha_y_top is not None and
                  _ultima_linha_x1 is not None):
                # Usa tracking REAL da última linha (100% preciso, nunca mais erra)
                ultimo_x1 = _ultima_linha_x1
                ultimo_y_top = _ultima_linha_y_top
                ultimo_largura = _ultima_linha_largura if _ultima_linha_largura else int(min(largura_titulo, MAX_PX) * 0.60)
                ultimo_altura = _ultima_linha_y_bottom - _ultima_linha_y_top
                ultimo_cor = _ultima_linha_cor if _ultima_linha_cor else _cor_principal
                ultimo_fonte = _ultima_linha_fonte if _ultima_linha_fonte else fa
                ultimo_sp = _ultima_linha_sp if _ultima_linha_sp else ag_sp
                tem_palavra_destaque = False
            else:
                # Fallback (extremamente raro): valores estimados
                ultimo_x1 = MARGIN
                ultimo_largura = max(180, int(min(largura_titulo, MAX_PX) * 0.60))
                ultimo_altura = int(tam_ag * 0.60)
                ultimo_y_top = Y_FIM - ultimo_altura
                ultimo_cor = _cor_principal
                ultimo_fonte = fa
                ultimo_sp = ag_sp
                tem_palavra_destaque = False

            # 2) COR DO ACENTO (regra da mulher, 100% contraste com o texto)
            lum_txt = _LUM_COR.get(ultimo_cor, 0.5)
            # Se texto for da família AZUL / TEAL / MARINHO / PETRÓLEO (escuros)
            # → acento sempre CREME (cor quente da mulher)
            azul_ou_petroleo = (
                ultimo_cor in (MARINHO, PETROLEO, TEAL)
                or (lum_txt < 0.60 and 10 < ultimo_cor[2] < 230 and ultimo_cor[0] < 80)
            )
            if azul_ou_petroleo or lum_txt < 0.55:
                acento_cor = CREME_ACENTO
                cor_texto_sobre = MARINHO  # texto sobre creme: azul escuro
            else:
                # texto claro: acento escuro
                acento_cor = MARINHO
                cor_texto_sobre = BRANCO

            # 3) LARGURA DA BARRA (ref. "Generalizada"): cobre a
            #    palavra/frase-alvo INTEIRA — nunca uma fração dela — com
            #    folga pequena fixa pra cada lado. "1-2 palavras que dão
            #    sentido" significa a barra abraçar essas palavras por
            #    completo, não uma porcentagem arbitrária de largura.
            largura_barra = max(24, ultimo_largura)

            # 4) POSICIONAMENTO FINAL (sutil — âncora visual discreta):
            #    - SOBREPÕE SÓ 12% DA ALTURA da última linha (ANCORAGEM VISUAL
            #      na BASE dos glifos — quase imperceptível como elemento isolado)
            sobrerpoe = max(8, int(ultimo_altura * 0.12))  # 12% da altura da linha
            altura_barra = max(12, int(ultimo_altura * 0.38))  # mais fina, 38% da linha
            rx1 = max(MARGIN, ultimo_x1 - 8)
            ry1 = (ultimo_y_top + ultimo_altura) - sobrerpoe
            rx2 = rx1 + largura_barra + 16
            ry2 = ry1 + altura_barra
            # Nunca ultrapassa a zona segura
            ry2 = min(SAFE_BOTTOM, ry2)
            ry1 = max(SAFE_TOP, min(ry1, ry2 - 16))
            # Desenha a forma: TRAÇO QUASE RETO (ref. "Generalizada") — cantos
            # só levemente arredondados. NUNCA cápsula/pílula: o raio antigo
            # (altura_barra // 2) é por definição um semicírculo em cada
            # ponta, o formato de pílula que a referência não tem.
            draw = ImageDraw.Draw(img_rgba, "RGBA")
            raio_barra = max(4, int(altura_barra * 0.18))
            try:
                draw.rounded_rectangle([(rx1, ry1), (rx2, ry2)],
                                       radius=raio_barra,
                                       fill=(*acento_cor, 245))
            except Exception:
                draw.rectangle([(rx1, ry1), (rx2, ry2)],
                               fill=(*acento_cor, 245))
            # Se tem palavra destaque: REDESENHA ela POR CIMA da barra,
            # com cor de contraste total (igual mulher: texto azul escuro sobre creme)
            if tem_palavra_destaque and _palavra_destaque_rect and _palavra_destaque_info:
                px, py, pw, ph = _palavra_destaque_rect
                txt_pd, fonte_pd, cor_pd, sp_pd, liga_pd = _palavra_destaque_info
                if liga_pd:
                    _linha_est(draw, px, py, txt_pd, fonte_pd, (*cor_texto_sobre, 255))
                else:
                    _linha(draw, px, py, txt_pd, fonte_pd, (*cor_texto_sobre, 255), ultimo_sp)
        except Exception as e:
            print(f"[acento_grafico] card6 (igual mulher): {e}")

    # Card 5 = Peso de Fonte — v31: quando o tema NAO tem nenhum bloco
    # MALGUN (titulo 100% AGILERA, ex. "Autismo e Ansiedade"), a estrategia
    # nao tinha efeito nenhum (so forcava bold no MALGUN, que nem existia
    # nesse tema). Pedido explicito: nao e so sobre engrossar a fonte
    # (AGILERA nao tem variacao de peso via OpenType) — e sobre DESTACAR.
    # Redesenha a ULTIMA PALAVRA do titulo por cima do que ja foi
    # renderizado, usando a cor de destaque da geracao (cor_dest) — um
    # "hero word" real, reconhecivel como estrategia propria mesmo sem
    # nenhum MALGUN no tema. Passa pela mesma guarda de contraste real do
    # resto da funcao antes de usar cor_dest.
    if estrategia_leg == "peso_fonte":
        _tem_malgun_no_tema = any(b["estilo"] == "malgun" for b in blocos)
        if (not _tem_malgun_no_tema and _ultima_linha_texto
                and _ultima_linha_fonte is not None
                and _ultima_linha_x1 is not None
                and _ultima_linha_y_top is not None):
            try:
                _palavras_pf = _ultima_linha_texto.split()
                _alvo_pf     = _palavras_pf[-1] if _palavras_pf else _ultima_linha_texto
                _prefixo_pf  = " ".join(_palavras_pf[:-1])
                _sp_pf       = _ultima_linha_sp or 0
                _off_x_pf = 0
                if _prefixo_pf:
                    _off_x_pf = (_medir_sp(_prefixo_pf + " ", _ultima_linha_fonte, _sp_pf)
                                 if _sp_pf else _medir(_prefixo_pf + " ", _ultima_linha_fonte))
                _cor_hero = cor_dest if _contraste_real_ok(cor_dest) else (
                    BRANCO if lum_zona_real < 0.5 else MARINHO)
                draw = ImageDraw.Draw(img_rgba, "RGBA")
                _linha(draw, _ultima_linha_x1 + _off_x_pf, _ultima_linha_y_top,
                       _alvo_pf, _ultima_linha_fonte, (*_cor_hero, 255), _sp_pf)
                print(f"[peso_fonte] destaque hero-word aplicado: '{_alvo_pf}' cor={_cor_hero}")
            except Exception as e:
                print(f"[peso_fonte] destaque hero-word falhou: {e}")

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
    hist_cores = None
    tem_pessoa = False
    em_pe      = True
    cabeca_bbox = None

    if imagem_url:
        try:
            r = requests.get(imagem_url, timeout=15); r.raise_for_status()
            tmp        = Image.open(io.BytesIO(r.content)).convert("RGB")\
                              .resize((120, 150), Image.Resampling.LANCZOS)
            cor1, cor2 = cores_fundo(tmp)
            lum_media  = luminosidade_media(tmp)
            hist_cores = _extrair_cores_dominantes(tmp)
        except Exception as e: print(f"[cor] {e}")

    if imagem_url:
        base, em_pe, tem_pessoa, cabeca_bbox = preparar_foto(imagem_url, pid, cor1, cor2, seed)
        if base is None:
            base = gerar_fundo_rico(cor1, cor2, seed)
            lum_media  = luminosidade_media(base)
            hist_cores = _extrair_cores_dominantes(base)
            tem_pessoa = False
    else:
        base = gerar_fundo_rico(cor1, cor2, seed)
        lum_media  = luminosidade_media(base)
        hist_cores = _extrair_cores_dominantes(base)
        tem_pessoa = False

    layout = seed % 5
    cor_dest, cor_fundo_txt = _escolher_cor_destaque(seed)

    cor_ov_usada = None

    base, _ = desenhar_titulo(base, tema, seed,
                              cor_dest=cor_dest,
                              cor_fundo_txt=cor_fundo_txt,
                              cor_overlay=cor_ov_usada,
                              tem_pessoa=tem_pessoa,
                              em_pe=em_pe,
                              cabeca_bbox=cabeca_bbox)
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
                    "raqm": _RAQM_OK,
                    "liga_count": len(_LIGA_SUBST),
                    "fonte_estilizada_ok": _AGILERA_EST_PATH is not None,
                    "fonte_estilizada_path": _AGILERA_EST_PATH or "NAO_GERADA",
                    "ronilson_path": PASTA_RONILSON})

@app.route("/inspect-font", methods=["GET"])
def rota_inspect_font():
    fonte_path = _resolve_font_path("AGILERA.OTF")
    if not fonte_path:
        return jsonify({"erro": "AGILERA.OTF nao encontrada"}), 404
    try:
        import struct
        with open(fonte_path, "rb") as f:
            data = f.read()
        def ru32(o): return struct.unpack_from(">I",data,o)[0]
        def ru16(o): return struct.unpack_from(">H",data,o)[0]
        def ri16(o): return struct.unpack_from(">h",data,o)[0]
        def rtag(o): return data[o:o+4].decode("latin1")

        num_tables = ru16(4)
        tables = {}
        for i in range(num_tables):
            b = 12 + i*16
            tables[rtag(b)] = ru32(b+8)

        # cmap glyph_id -> codepoint
        cmap_dict = {}
        if "cmap" in tables:
            co = tables["cmap"]
            ns = ru16(co+2)
            for i in range(ns):
                plat = ru16(co+4+i*8)
                so   = co + ru32(co+4+i*8+4)
                fmt  = ru16(so)
                if fmt == 4 and plat in (0,3):
                    sc = ru16(so+6)//2
                    ea = [ru16(so+14+j*2) for j in range(sc)]
                    sa = [ru16(so+16+sc*2+j*2) for j in range(sc)]
                    da = [ri16(so+16+sc*4+j*2) for j in range(sc)]
                    ra = [ru16(so+16+sc*6+j*2) for j in range(sc)]
                    rb = so+16+sc*6
                    for s in range(sc):
                        for cp in range(sa[s], ea[s]+1):
                            if ra[s]==0:
                                gid=(cp+da[s])&0xFFFF
                            else:
                                ix=rb+s*2+ra[s]+(cp-sa[s])*2
                                if ix+2>len(data): continue
                                gid=ru16(ix)
                                if gid: gid=(gid+da[s])&0xFFFF
                            if gid: cmap_dict[gid]=cp
                    break
        gid2ch = {g: chr(cp) for g,cp in cmap_dict.items()}

        resultado = {"total_glyphs_mapeados": len(cmap_dict)}

        # GPOS pares com kern
        pares_kern = []
        if "GPOS" in tables:
            go = tables["GPOS"]
            flo = go + ru16(go+4)
            llo = go + ru16(go+6)
            fc  = ru16(flo)
            feat_tags = {}
            for i in range(fc):
                b = flo+2+i*6
                feat_tags[rtag(b)] = feat_tags.get(rtag(b),0)+1
            resultado["gpos_features"] = feat_tags

            lc = ru16(llo)
            for li in range(lc):
                loff = llo + ru16(llo+2+li*2)
                lt   = ru16(loff)      # lookup type
                sc2  = ru16(loff+4)    # subtable count
                if lt != 2: continue   # PairPos
                for si in range(sc2):
                    soff = loff + ru16(loff+6+si*2)
                    fmt  = ru16(soff)
                    if fmt == 1:  # PairSet
                        cov_off = soff + ru16(soff+2)
                        cov_fmt = ru16(cov_off)
                        glyphs1 = []
                        if cov_fmt == 1:
                            gc = ru16(cov_off+2)
                            glyphs1 = [ru16(cov_off+4+k*2) for k in range(gc)]
                        ps_count = ru16(soff+8)
                        vf1 = ru16(soff+4); vf2 = ru16(soff+6)
                        v1sz = bin(vf1).count('1')*2
                        v2sz = bin(vf2).count('1')*2
                        for pi in range(ps_count):
                            pso = soff + ru16(soff+10+pi*2)
                            ppc = ru16(pso)
                            rec_sz = 2 + v1sz + v2sz
                            for ri2 in range(ppc):
                                g2 = ru16(pso+2+ri2*rec_sz)
                                g1 = glyphs1[pi] if pi < len(glyphs1) else 0
                                c1 = gid2ch.get(g1,"?")
                                c2 = gid2ch.get(g2,"?")
                                if c1 != "?" and c2 != "?":
                                    pares_kern.append(c1+c2)
                    if len(pares_kern) > 200: break
                if len(pares_kern) > 200: break

        resultado["pares_kern_sample"] = pares_kern[:100]
        resultado["total_pares_kern"]  = len(pares_kern)
        resultado["maiusculas_kern"]   = [p for p in pares_kern if p[0].isupper()][:50]
        resultado["minusculas_kern"]   = [p for p in pares_kern if p[0].islower()][:50]
        return jsonify(resultado)
    except Exception as e:
        import traceback
        return jsonify({"erro": str(e), "trace": traceback.format_exc()}), 500

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
