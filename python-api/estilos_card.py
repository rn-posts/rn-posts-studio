"""
python-api/estilos_card.py  —  v54  —  Estilos visuais de alta qualidade (IA com a paleta da clínica)

Rota própria: POST /preview-card-estilo

ESTILOS VISUAIS:
  * Cinematic: visual cinematográfico sofisticado, iluminação dramática e natural, luz suave e volumétrica,
               profundidade de campo, contraste equilibrado, composição de filme, enquadramento profissional,
               atmosfera envolvente, textura realista, tons elegantes, sombras suaves, aparência fotográfica premium,
               lente cinematográfica, bokeh sutil, alta definição, sem aparência artificial.
  * Showcase: apresentação premium do elemento principal, composição limpa e sofisticada, foco absoluto no
              objeto ou personagem, iluminação de estúdio cuidadosamente posicionada, fundo elegante e discreto,
              profundidade visual, detalhes nítidos, aparência profissional, estética de campanha publicitária,
              realismo elevado, acabamento premium, composição visual equilibrada.
  * Kintsugi, Fumaça, Portal, Gelo, Flutuante, Macro, Museu: metáforas poéticas com a paleta da clínica.
"""
import base64
import io
import json
import os
import random
import sys
import time
import traceback
import uuid

import numpy as np
import requests
from flask import Blueprint, jsonify, request
from PIL import Image, ImageEnhance, ImageFilter

bp = Blueprint("estilos_card", __name__)


def _m():
    """Módulo principal (main.py) já carregado — usado somente para leitura."""
    return sys.modules.get("main") or sys.modules.get("__main__")


class ErroEstilo(Exception):
    """Falha esperada ao montar o card de um estilo (mensagem vai para a tela)."""


_ETAPA = {"v": "inicio"}


# ── Catálogo de estilos visuais ────────────────────────────────────────────────
ESTILOS = {
    "cinematic": {
        "tipo": "cena",
        "rotulo": "Cinematic",
        "luz": "dramatic and natural cinematic lighting, soft and volumetric light, 35mm lens, subtle bokeh",
        "cena": (
            "sophisticated cinematic film still visual, film composition, professional framing, "
            "immersive atmosphere, realistic texture, elegant tones, soft shadows, premium photographic appearance, "
            "cinematic lens, subtle bokeh, high definition, balanced contrast, authentic photographic realism, "
            "without artificial appearance"
        ),
    },
    "showcase": {
        "tipo": "cena",
        "rotulo": "Showcase",
        "luz": "carefully positioned studio lighting, soft key light and gentle fill, elegant refined rim highlights",
        "cena": (
            "premium showcase presentation of the main symbolic element or subject, clean and sophisticated composition, "
            "absolute focus on the central subject, carefully positioned studio lighting, elegant and discreet background, "
            "visual depth, sharp details, professional appearance, advertising campaign aesthetic, elevated realism, "
            "premium finish, balanced visual composition"
        ),
    },
    "gold": {
        "tipo": "cena",
        "rotulo": "Kintsugi",
        "luz": "soft dawn side-light with warm solar-orange glints on the gold",
        "cena": (
            "a single handmade ceramic bowl in matte deep navy and petroleum teal glaze, "
            "broken and beautifully mended with luminous gold seams (kintsugi), resting "
            "on dark stone, shallow depth of field, the gold veins catching light"
        ),
    },
    "smoke": {
        "tipo": "cena",
        "rotulo": "Fumaça",
        "luz": "low warm solar-orange dawn glow backlighting the mist",
        "cena": (
            "slow ribbons of soft mist and smoke dissolving upward into clear air, "
            "deep navy and petroleum teal atmosphere, weightless, calm, tension dissipating"
        ),
    },
    "portal": {
        "tipo": "cena",
        "rotulo": "Portal",
        "luz": "golden-orange sunrise light flooding in from outside the doorway",
        "cena": (
            "an open wooden doorway seen from a quiet dark interior, bright dawn light "
            "and soft sage plants at the threshold, an invitation to take the first step, "
            "no one in frame"
        ),
    },
    "ice": {
        "tipo": "cena",
        "rotulo": "Gelo",
        "luz": "first warm solar-orange light refracting through the ice",
        "cena": (
            "clear ice slowly melting into still transparent water, teal and petroleum "
            "reflections, fine droplets, the thaw of frozen feelings, hope"
        ),
    },
    "floating": {
        "tipo": "cena",
        "rotulo": "Flutuante",
        "luz": "soft diffused dawn light, gentle shadows",
        "cena": (
            "three or four simple symbolic objects gently suspended in mid-air with lots of "
            "empty space: a ceramic cup, a few leaves, a thin golden thread, on a smooth "
            "petroleum teal to navy gradient backdrop, minimal and airy"
        ),
    },
    "macro": {
        "tipo": "cena",
        "rotulo": "Macro",
        "luz": "a single point of solar-orange light in creamy bokeh",
        "cena": (
            "extreme macro close-up of a dewdrop resting on a sage-green leaf vein, razor-thin "
            "depth of field, creamy teal bokeh, jewel-like premium detail"
        ),
    },
    "museum": {
        "tipo": "cena",
        "rotulo": "Museu",
        "luz": "a single soft museum spotlight from above",
        "cena": (
            "one small symbolic object displayed like a work of art in a minimal elegant "
            "gallery: a mended ceramic piece on a low plinth, deep navy wall with a subtle "
            "petroleum gradient, silent, refined, premium"
        ),
    },
}


# v55b: ajustes pequenos e independentes para Cinematic/Showcase (False desliga)
_AJUSTE_POSICAO_TEXTO = False  # v55c: desligado (dependia do Haar frontal, que nao ve perfil); substituido por _TITULO_INTELIGENTE
_REALISMO_SUAVE = False        # v55c: desligado para o rosto de frente repetir o prompt original (v54)
_ESTILOS_COM_PESSOA = ("cinematic", "showcase")
_TOQUE_REALISMO = (
    "If a person appears: natural unretouched skin with gentle texture, relaxed natural eyes with a soft "
    "natural gaze and normal proportions, no airbrushing, no plastic or glossy look."
)


# v55c: variantes de cena para Cinematic/Showcase (alternam a cada geracao)
_VARIANTES_ATIVAS = True     # False = volta a gerar sempre como na v54
_TITULO_INTELIGENTE = True   # True = Gemini (visao) acha a cabeca e o titulo desvia dela
_VARIANTES = ("frente", "sem_rosto", "perfil", "foto_real")
_DIRETRIZ_VARIANTE = {
    "frente": (
        "Subject: ONE adult person in a natural frontal or three-quarter view, soft directional window light "
        "that clearly and softly lights the face, gentle genuine expression, plain dark or softly blurred background."
    ),
    "perfil": (
        "Subject: ONE adult person in a calm side profile or three-quarter profile, looking toward a window, "
        "face clearly and softly lit by window light (not in deep shadow, not a silhouette), natural human proportions."
    ),
    "sem_rosto": (
        "Subject: ONE adult person seen from behind or in a distant wide shot looking out of a window, or only "
        "hands holding a cup near a window; the face is NOT visible. Soft window light, quiet contemplative "
        "atmosphere with gentle hope."
    ),
}


def _escolher_variante(seed, pedida=None):
    if pedida in _VARIANTES:
        return pedida
    return _VARIANTES[int(seed) % len(_VARIANTES)]


def _prompt(estilo, tema="", variante=None):
    e = ESTILOS[estilo]
    M = _m()
    tema_limpo = (
        M._texto_tema_limpo(tema)
        if (M and hasattr(M, "_texto_tema_limpo"))
        else (tema or "").replace("*", " ").replace(":", " ").replace("-", " ").strip()
    )
    contexto_tema = f' Concept / emotional theme of this post: "{tema_limpo}". ' if tema_limpo else " "

    composicao = (
        "Vertical 4:5 Instagram portrait composition. Keep the UPPER-LEFT third calm, darker and "
        "free of busy detail for large typography; place the main subject in the lower "
        "two thirds, slightly right of center, with generous negative space and clear visual depth."
    )

    realismo = ""
    if _REALISMO_SUAVE and estilo in _ESTILOS_COM_PESSOA:
        realismo = _TOQUE_REALISMO + " "
    diretriz = (_DIRETRIZ_VARIANTE.get(variante, "") + " ") if variante else ""

    return (
        "Photorealistic editorial photograph for AlvoreSer, a Brazilian psychology clinic "
        "whose identity is dawn, hope, emotional care, healing and transformation. "
        f"{contexto_tema}"
        f"Visual style and scene: {e['cena']}. Lighting: {e['luz']}. "
        "Color palette strictly harmonious with clinic identity: deep navy #024059, petroleum teal #1B797D, "
        "soft sage #779993, solar orange #F9AB0B as accent light only, snow white haze #F4F6F8. "
        "Mood: professional, welcoming, intimate, never clinical-cold, never hospital, "
        f"elevated realism, authentic photographic texture. {composicao} {realismo}{diretriz}"
        "No text, no letters, no typography, no words, no logos, no watermark, no borders, "
        "no artificial 3D look, no deformed elements, no extra limbs, high definition, authentic photography."
    )


# ── IA de imagem: Gemini -> Cloudflare (opcional) ─────────────────────────────
_GEMINI_IMAGE_EXTRA = (
    "gemini-3.5-flash",
    "gemini-3.5-flash-preview",
    "gemini-3.0-flash",
    "gemini-3.1-flash-image",
    "gemini-3.1-flash-image-preview",
    "gemini-2.5-flash-image",
    "gemini-2.5-flash",
)


def _gerar_imagem_ia(prompt):
    """Retorna (imagem_PIL, None) ou (None, motivo legivel)."""
    M = _m()
    erros = []

    chave = getattr(M, "GEMINI_API_KEY", None)
    if not chave:
        erros.append("GEMINI_API_KEY nao configurada")
    else:
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "responseModalities": ["TEXT", "IMAGE"],
                "imageConfig": {"aspectRatio": "4:5"},
            },
        }
        modelos_usados = list(getattr(M, "GEMINI_IMAGE_MODELOS", ()))
        for extra in _GEMINI_IMAGE_EXTRA:
            if extra not in modelos_usados:
                modelos_usados.append(extra)
        for modelo in modelos_usados:
            try:
                url = (
                    f"https://generativelanguage.googleapis.com/v1beta/models/"
                    f"{modelo}:generateContent?key={chave}"
                )
                r = requests.post(url, json=payload, timeout=60)
                if r.status_code >= 400:
                    print(f"[estilo] {modelo} HTTP {r.status_code}: {r.text[:200]}")
                    dica = {
                        429: "sem cota — confira plano/faturamento da chave Gemini",
                        404: "modelo nao existe para esta chave",
                        403: "chave sem permissao",
                    }.get(r.status_code, "requisicao recusada")
                    erros.append(f"{modelo}: HTTP {r.status_code} ({dica})")
                    continue
                raw = M._bytes_imagem_gemini(r.json())
                if not raw:
                    erros.append(f"{modelo}: respondeu sem imagem")
                    continue
                print(f"[estilo] imagem ok via Gemini {modelo}")
                return M._fit_canvas(Image.open(io.BytesIO(raw))), None
            except Exception as e:
                print(f"[estilo] {modelo} falhou: {e}")
                erros.append(f"{modelo}: {str(e)[:80]}")

    conta = os.getenv("CLOUDFLARE_ACCOUNT_ID")
    token = os.getenv("CLOUDFLARE_API_TOKEN")
    if conta and token:
        try:
            url = (
                f"https://api.cloudflare.com/client/v4/accounts/{conta}"
                "/ai/run/@cf/black-forest-labs/flux-1-schnell"
            )
            r = requests.post(
                url,
                headers={"Authorization": f"Bearer {token}"},
                json={"prompt": prompt[:2000], "steps": 6},
                timeout=70,
            )
            if r.status_code >= 400:
                print(f"[estilo] cloudflare HTTP {r.status_code}: {r.text[:200]}")
                erros.append(f"Cloudflare: HTTP {r.status_code}")
            else:
                b64 = (r.json().get("result") or {}).get("image")
                if b64:
                    print("[estilo] imagem ok via Cloudflare FLUX.1 schnell")
                    return M._fit_canvas(Image.open(io.BytesIO(base64.b64decode(b64)))), None
                erros.append("Cloudflare: respondeu sem imagem")
        except Exception as e:
            print(f"[estilo] cloudflare falhou: {e}")
            erros.append(f"Cloudflare: {str(e)[:80]}")
    else:
        erros.append("Cloudflare nao configurado")

    return None, " | ".join(erros)


# ── Montagem da imagem-base do estilo ─────────────────────────────────────────
# v55b: libera o topo para o título quando o rosto está alto demais (não mexe no rosto)
_W, _H = 1080, 1350
_DY_MAX = int(_H * 0.30)           # desloca no máximo ~405px
_ALVO_TOPO_ROSTO = int(_H * 0.40)  # topo da folga do rosto (como o motor mede) deve ficar abaixo disto
_cascata_rosto = None


def _medir_rosto(img):
    """(x, y, w, h) do maior rosto frontal (Haar) ou None."""
    global _cascata_rosto
    try:
        import cv2
        if _cascata_rosto is None:
            _cascata_rosto = cv2.CascadeClassifier(
                cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
        arr = np.array(img.convert("L"))
        lado = int(_W * 0.08)
        for sf, mn in ((1.1, 5), (1.05, 4), (1.05, 3)):
            faces = _cascata_rosto.detectMultiScale(
                arr, scaleFactor=sf, minNeighbors=mn, minSize=(lado, lado))
            faces = [f for f in faces if f[1] + f[3] / 2 < _H * 0.80]
            if len(faces):
                fx, fy, fw, fh = max(faces, key=lambda f: f[2] * f[3])
                print(f"[estilo] rosto detectado: x={fx} y={fy} w={fw} h={fh}")
                return int(fx), int(fy), int(fw), int(fh)
    except Exception as e:
        print(f"[estilo] deteccao de rosto falhou: {e}")
    return None


def _dy_necessario(rosto):
    """Quantos px a cena precisa descer para o título caber acima do rosto.
    O motor de título protege o rosto com folga de 0.55*altura acima dele."""
    if rosto is None:
        return 0
    _, fy, _, fh = rosto
    return max(0, _ALVO_TOPO_ROSTO - (fy - int(fh * 0.55)))


def _abrir_espaco_topo(img, dy):
    """Desloca a cena para baixo em dy px; o topo é estendido espelhando e
    desfocando as linhas de cima (fundo escuro fora de foco)."""
    a = np.asarray(img.convert("RGB"))
    n = min(dy, 220)
    ext = np.pad(a[:n], ((dy, 0), (0, 0), (0, 0)), mode="reflect")[:dy]
    cheio = np.concatenate([ext, a], axis=0)
    borrado = np.asarray(
        Image.fromarray(cheio).filter(ImageFilter.GaussianBlur(20))).astype(np.float32)
    cheio = cheio.astype(np.float32)
    feather = 70
    m = np.zeros((cheio.shape[0], 1, 1), dtype=np.float32)
    m[:dy] = 1.0
    m[dy:dy + feather, 0, 0] = np.linspace(1.0, 0.0, feather)
    out = cheio * (1 - m) + borrado * m
    return Image.fromarray(np.clip(out, 0, 255).astype(np.uint8)).crop((0, 0, _W, _H))


# v55c: foto real do banco (Cloudinary) com tratamento leve por estilo
def _grade_estilo(img, estilo):
    a = np.asarray(img.convert("RGB"), dtype=np.float32) / 255.0
    lum = a.mean(axis=2, keepdims=True)
    if estilo == "cinematic":
        # sombras levemente azul-petroleo, altas-luzes levemente quentes, contraste suave
        a = a + np.array([0.00, 0.03, 0.05], dtype=np.float32) * (1 - lum) \
              + np.array([0.04, 0.02, -0.02], dtype=np.float32) * lum
        a = (a - 0.5) * 1.08 + 0.5
        forca = 0.38
    else:
        a = (a - 0.5) * 1.04 + 0.5
        forca = 0.22
    h, w = a.shape[:2]
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    d = np.sqrt(((xx - w / 2) / (w / 2)) ** 2 + ((yy - h * 0.45) / (h * 0.62)) ** 2)
    v = 1 - forca * np.clip(d - 0.55, 0, 1) ** 1.6
    a = a * v[..., None]
    return Image.fromarray((np.clip(a, 0, 1) * 255).astype(np.uint8))


def _foto_real_do_banco(estilo, tema):
    """Foto real do banco de imagens + tratamento. Retorna imagem PIL ou None."""
    M = _m()
    try:
        url, pid = M.buscar_imagem(tema)
        if not url:
            return None
        r = requests.get(url, timeout=25)
        r.raise_for_status()
        img = M._fit_canvas(Image.open(io.BytesIO(r.content)))
        print(f"[estilo] foto real do banco: {pid}")
        return _grade_estilo(img, estilo)
    except Exception as e:
        print(f"[estilo] foto real indisponivel: {e}")
        return None


# v55c: o Gemini (visao) diz onde esta a cabeca, inclusive de perfil, de costas ou em silhueta
def _cabeca_por_visao(img):
    """(x0, y0, x1, y1) em px do canvas, ou None se nao ha cabeca visivel / falhou."""
    M = _m()
    chave = getattr(M, "GEMINI_API_KEY", None)
    if not chave:
        return None
    mini = img.convert("RGB").resize((432, 540), Image.Resampling.LANCZOS)
    buf = io.BytesIO()
    mini.save(buf, format="JPEG", quality=85)
    pergunta = (
        'Look at this image. If a person is visible, answer ONLY with JSON {"cabeca":[ymin,xmin,ymax,xmax]} '
        "giving the bounding box of the person's HEAD (top of the hair to the chin, also for a profile or the "
        "back of the head), coordinates normalized 0-1000. If no head is visible answer {\"cabeca\":null}."
    )
    payload = {
        "contents": [{"parts": [
            {"inlineData": {"mimeType": "image/jpeg", "data": base64.b64encode(buf.getvalue()).decode()}},
            {"text": pergunta},
        ]}],
        "generationConfig": {"responseMimeType": "application/json", "temperature": 0},
    }
    for modelo in ("gemini-2.5-flash", "gemini-3.5-flash"):
        try:
            url = (f"https://generativelanguage.googleapis.com/v1beta/models/"
                   f"{modelo}:generateContent?key={chave}")
            r = requests.post(url, json=payload, timeout=25)
            if r.status_code >= 400:
                print(f"[cabeca] {modelo} HTTP {r.status_code}")
                continue
            partes = r.json()["candidates"][0]["content"]["parts"]
            txt = "".join(p.get("text", "") for p in partes if not p.get("thought"))
            txt = txt.replace("```json", "").replace("```", "").strip()
            caixa = json.loads(txt).get("cabeca")
            if not caixa:
                print(f"[cabeca] {modelo}: sem cabeca visivel")
                return None
            ymin, xmin, ymax, xmax = [max(0.0, min(1000.0, float(v))) for v in caixa]
            if ymax <= ymin or xmax <= xmin:
                continue
            bbox = (int(xmin / 1000 * _W), int(ymin / 1000 * _H),
                    int(xmax / 1000 * _W), int(ymax / 1000 * _H))
            print(f"[cabeca] {modelo}: cabeca em {bbox}")
            return bbox
        except Exception as e:
            print(f"[cabeca] {modelo} falhou: {e}")
    return None


def _card_titulo_inteligente(M, base, tema, seed):
    """Mesmo motor de titulo do gerar_card_imagem, mas com a cabeca real (perfil incluso)."""
    cabeca = _cabeca_por_visao(base)
    cor1 = M.MARINHO
    try:
        cor1, _ = M.cores_fundo(base.convert("RGB").resize((120, 150), Image.Resampling.LANCZOS))
    except Exception as e:
        print(f"[estilo] cores_fundo falhou: {e}")
    img = M.tratar_foto_editorial(base.convert("RGB"), cor1, seed)
    cor_dest, cor_fundo_txt = M._escolher_cor_destaque(seed)
    out, _ = M.desenhar_titulo(img, tema, seed, cor_dest=cor_dest, cor_fundo_txt=cor_fundo_txt,
                               cor_overlay=None, tem_pessoa=False, em_pe=True,
                               cabeca_bbox=cabeca)
    return out


def _base_cena(estilo, seed, tema="", variante_pedida=None):
    M = _m()
    variante = None
    if _VARIANTES_ATIVAS and estilo in _ESTILOS_COM_PESSOA:
        variante = _escolher_variante(seed, variante_pedida)
        print(f"[estilo] variante da cena: {variante}")
        if variante == "foto_real":
            real = _foto_real_do_banco(estilo, tema)
            if real is not None:
                _ETAPA["variante"] = variante
                return real, None
            print("[estilo] sem foto real; usando rosto de frente por IA")
            variante = "frente"
    _ETAPA["variante"] = variante or "-"
    prompt = _prompt(estilo, tema, variante)
    print(f"[estilo] Gerando imagem IA para '{estilo}'...")
    img, motivo = _gerar_imagem_ia(prompt)
    aviso = None
    if img is None:
        print(f"[estilo] Falha na imagem IA ({motivo}), usando gradiente da paleta")
        img = M._gerar_fundo_gradiente(M.MARINHO, M.PETROLEO, seed)
        aviso = f"A imagem por IA falhou ({motivo}); usei o gradiente da paleta."

    # v55b: Cinematic/Showcase — só desloca a cena p/ liberar o topo (rosto não é alterado)
    if _AJUSTE_POSICAO_TEXTO and img is not None and aviso is None and estilo in _ESTILOS_COM_PESSOA:
        try:
            rosto = _medir_rosto(img)
            dy = min(_dy_necessario(rosto), _DY_MAX)
            if rosto is not None and dy > 12:
                print(f"[estilo] abrindo {dy}px de espaco livre no topo para o titulo")
                img = _abrir_espaco_topo(img, dy)
        except Exception as e:
            print(f"[estilo] ajuste de posicao falhou (ignorado): {e}")
    return img, aviso


# ── Rota ──────────────────────────────────────────────────────────────────────
# ══════════════════════════════════════════════════════════════════════════════
# v57 — "Com Ronilson": recorte SEM FUNDO (pasta Cloudinary ronilson_sem_fundo)
# integrado a um cenário criado conforme tema + paleta + estilo escolhido.
# Só adiciona: nada do fluxo dos outros estilos é alterado (ativado por com_ronilson=True).
# Não usa rembg (o recorte já vem pronto) -> leve para os 512MB do Render.
# ══════════════════════════════════════════════════════════════════════════════
_PREFIXOS_SEM_FUNDO = (
    "Banco de Imagens/Ronilson_sem_fundo",
    "Banco de Imagens/ronilson_sem_fundo",
    "Banco de Imagens/Ronilson_Sem_Fundo",
    "banco de imagens/ronilson_sem_fundo",
    "Ronilson_sem_fundo",
    "ronilson_sem_fundo",
)
_cache_recortes = {"t": 0.0, "lista": []}

# desfoque do cenário (profundidade de campo) por estilo
_BLUR_CENARIO = {
    "cinematic": 3.2, "showcase": 2.0, "macro": 4.0, "auto": 1.8,
    "gold": 2.4, "smoke": 2.2, "portal": 2.4, "ice": 2.2, "floating": 1.8, "museum": 2.0,
}


def _listar_recortes_ronilson():
    """Lista (com cache de 10 min) os recortes PNG/WebP da pasta ronilson_sem_fundo."""
    import cloudinary.api
    M = _m()
    if _cache_recortes["lista"] and time.time() - _cache_recortes["t"] < 600:
        return _cache_recortes["lista"]

    def _ok(r):
        pid = r.get("public_id", "")
        return (
            M.CLOUDINARY_POSTS not in pid
            and M.CLOUDINARY_PREVIEW not in pid
            and (r.get("format") or "png").lower() in ("png", "webp", "avif", "tiff", "tif")
        )

    achados = []
    for pref in _PREFIXOS_SEM_FUNDO:
        cursor = None
        for _ in range(5):
            kw = dict(type="upload", prefix=pref + "/", max_results=100)
            if cursor:
                kw["next_cursor"] = cursor
            try:
                res = cloudinary.api.resources(**kw)
            except Exception as e:
                print(f"[ronilson] '{pref}': {e}")
                break
            achados += [r for r in res.get("resources", []) if _ok(r)]
            cursor = res.get("next_cursor")
            if not cursor:
                break
        if achados:
            print(f"[ronilson] {len(achados)} recortes em '{pref}'")
            break

    if not achados:  # varredura geral (caso a pasta tenha outro caminho/caixa)
        cursor = None
        for _ in range(10):
            kw = dict(type="upload", max_results=500)
            if cursor:
                kw["next_cursor"] = cursor
            try:
                res = cloudinary.api.resources(**kw)
            except Exception as e:
                print(f"[ronilson] varredura geral: {e}")
                break
            achados += [
                r for r in res.get("resources", [])
                if _ok(r) and "sem_fundo" in r.get("public_id", "").lower().replace(" ", "_")
            ]
            cursor = res.get("next_cursor")
            if not cursor:
                break

    if achados:
        _cache_recortes.update(t=time.time(), lista=achados)
    return achados


def _carregar_recorte_ronilson():
    """Sorteia (baralho, sem repetir) um recorte e devolve (imagem RGBA, public_id)."""
    M = _m()
    recursos = _listar_recortes_ronilson()
    if not recursos:
        raise ErroEstilo(
            "Nao encontrei imagens na pasta ronilson_sem_fundo do Cloudinary "
            "(PNG/WebP com transparencia)."
        )
    r = M._proxima_foto_baralho("ronilson_sem_fundo", recursos)
    url, pid = r.get("secure_url"), r.get("public_id", "")
    resp = requests.get(url, timeout=30)
    resp.raise_for_status()
    img = Image.open(io.BytesIO(resp.content))
    if img.mode in ("RGBA", "LA") or (img.mode == "P" and "transparency" in img.info):
        img = img.convert("RGBA")
    else:
        raise ErroEstilo(f"A imagem {pid} nao tem transparencia (fundo removido).")
    lado = max(img.size)
    if lado > 2000:  # economiza memoria
        f = 2000 / lado
        img = img.resize((int(img.width * f), int(img.height * f)), Image.Resampling.LANCZOS)
    print(f"[ronilson] recorte: {pid} {img.size}")
    return img, pid


# ── Cenário (sem pessoas) conforme tema + paleta + estilo ─────────────────────
def _prompt_cenario_ronilson(estilo, tema, seed):
    M = _m()
    if estilo == "auto":
        return (
            M._prompt_fundo_ia(tema, seed, True)
            + " The scene needs a believable floor or ground plane and clear depth so a standing "
              "adult can be placed on the right side; soft key light from the upper left."
        )
    e = ESTILOS[estilo]
    tema_limpo = M._texto_tema_limpo(tema) if hasattr(M, "_texto_tema_limpo") else (tema or "")
    contexto = f' Concept / emotional theme of this post: "{tema_limpo}". ' if tema_limpo else " "
    return (
        "Photorealistic editorial photograph of an EMPTY environment (no people) for AlvoreSer, a Brazilian "
        "psychology clinic whose identity is dawn, hope, emotional care, healing and transformation."
        f"{contexto}"
        f"Visual style and scene: {e['cena']}. Lighting: {e['luz']}. "
        "Color palette strictly harmonious with clinic identity: deep navy #024059, petroleum teal #1B797D, "
        "soft sage #779993, solar orange #F9AB0B as accent light only, snow white haze #F4F6F8. "
        "Composition: vertical 4:5, a believable floor or ground plane and clear visual depth. The RIGHT 55% "
        "of the frame is open, softly lit space (wall, air, bokeh or empty floor) reserved for compositing a "
        "real standing adult later; keep the LEFT 40% calm, darker and uncluttered for large typography. "
        "Any symbolic object sits low, small, in the lower-left or center, below the typography area. "
        "Soft key light coming from the upper left. "
        "Absolutely no people, no faces, no hands, no mannequins, no silhouettes, no text, no letters, "
        "no logos, no watermark, no borders, high definition, authentic photographic texture."
    )


def _cenario_ronilson(estilo, tema, seed):
    M = _m()
    img, motivo = _gerar_imagem_ia(_prompt_cenario_ronilson(estilo, tema, seed))
    aviso = None
    if img is None:
        print(f"[ronilson] cenario IA falhou ({motivo}); gradiente da paleta")
        img = M._gerar_fundo_gradiente(M.MARINHO, M.PETROLEO, seed)
        aviso = f"O cenario por IA falhou ({motivo}); usei o gradiente da paleta."
    return img, aviso


# ── Integração: o Ronilson passa a fazer parte da luz e da sombra da cena ────
def _limpar_borda_recorte(rgba):
    """Tira a franja clara do recorte: encolhe 1px o alpha e repinta a borda com a cor de dentro."""
    import cv2
    a = np.asarray(rgba.split()[3]).astype(np.float32) / 255.0
    rgb = np.asarray(rgba.convert("RGB")).astype(np.float32)
    a = np.clip((a - 0.10) / 0.80, 0, 1)
    nucleo = cv2.erode(a, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7)))
    num = cv2.GaussianBlur(rgb * nucleo[..., None], (0, 0), 4)
    den = cv2.GaussianBlur(nucleo, (0, 0), 4)[..., None]
    sangra = num / np.maximum(den, 1e-3)
    w = np.clip(1.0 - nucleo, 0, 1)[..., None] * (den > 0.05)
    rgb = rgb * (1 - w) + sangra * w
    a = cv2.GaussianBlur(cv2.erode(a, np.ones((3, 3), np.uint8)), (0, 0), 0.7)
    return rgb, a


def _caixa_cabeca(a_f):
    """Zona da cabeça (heurística do salto de largura dos ombros, igual à compor_pessoa)."""
    try:
        m = a_f > 0.04
        linhas = np.where(m.any(axis=1))[0]
        if len(linhas) == 0:
            return None
        larg = np.zeros(m.shape[0], dtype=np.int32)
        for r in linhas:
            cols = np.where(m[r])[0]
            larg[r] = cols.max() - cols.min()
        y_topo = int(linhas[0])
        jan = larg[y_topo: y_topo + max(10, int(_H * 0.05))]
        ref = float(np.median(jan[jan > 0])) if np.any(jan > 0) else 0.0
        y_fim = y_topo + int(_H * 0.30)
        if ref > 0:
            for r in range(y_topo, min(m.shape[0], y_topo + int(_H * 0.55))):
                if larg[r] > ref * 1.5:
                    y_fim = r + int(_H * 0.08)
                    break
        cols = np.where(m[y_topo:y_fim].any(axis=0))[0]
        if len(cols) == 0:
            return None
        return (max(0, int(cols.min()) - 25), max(0, y_topo - 15),
                min(_W, int(cols.max()) + 25), min(_H, y_fim + 25))
    except Exception as e:
        print(f"[ronilson] caixa da cabeca falhou: {e}")
        return None


def _integrar_ronilson(fundo, recorte, estilo, seed):
    """Retorna (imagem RGB, corpo_inteiro, caixa_da_cabeca)."""
    import cv2
    rgb_r, a_r = _limpar_borda_recorte(recorte)
    ys, xs = np.where(a_r > 0.04)
    if len(ys) == 0:
        raise ErroEstilo("O recorte do Ronilson veio vazio.")
    x_a, x_b, y_a, y_b = xs.min(), xs.max() + 1, ys.min(), ys.max() + 1
    rgb_r, a_r = rgb_r[y_a:y_b, x_a:x_b], a_r[y_a:y_b, x_a:x_b]
    ph, pw = a_r.shape
    prop = ph / pw

    # tamanho/posição: corpo inteiro pisa no chão; busto/meio corpo é cortado pela base do card
    corpo = prop >= 2.2
    if corpo:
        alt = int(_H * 0.80)
    else:
        larg_alvo = int(_W * (0.52 if prop >= 1.35 else 0.58))
        alt = min(int(larg_alvo * prop), int(_H * 1.0))
    nw = max(1, int(alt / prop))
    rgb_s = cv2.resize(rgb_r, (nw, alt), interpolation=cv2.INTER_AREA)
    a_s = cv2.resize(a_r, (nw, alt), interpolation=cv2.INTER_AREA)
    x0 = max(int(_W * 0.42), _W - nw - int(_W * 0.03))
    y0 = int(_H * 0.975) - alt if corpo else _H - alt

    sub = np.zeros((_H, _W, 3), np.float32)
    a_f = np.zeros((_H, _W), np.float32)
    sx0, sy0 = max(0, -x0), max(0, -y0)
    dx0, dy0 = max(0, x0), max(0, y0)
    cw, ch = min(nw - sx0, _W - dx0), min(alt - sy0, _H - dy0)
    sub[dy0:dy0 + ch, dx0:dx0 + cw] = rgb_s[sy0:sy0 + ch, sx0:sx0 + cw]
    a_f[dy0:dy0 + ch, dx0:dx0 + cw] = a_s[sy0:sy0 + ch, sx0:sx0 + cw]

    # cenário com profundidade de campo
    fundo = fundo.convert("RGB").resize((_W, _H), Image.Resampling.LANCZOS)
    fundo = fundo.filter(ImageFilter.GaussianBlur(_BLUR_CENARIO.get(estilo, 2.0)))
    bg = np.asarray(fundo).astype(np.float32)

    # direção da luz: lado mais claro do cenário
    lum = bg.mean(axis=2)
    luz_x = -1.0 if lum[:, : _W // 2].mean() >= lum[:, _W // 2:].mean() * 0.95 else 1.0

    # cor/luz ambiente em volta dele
    solido = (a_f > 0.5).astype(np.uint8)
    anel = cv2.dilate(solido, np.ones((41, 41), np.uint8)) - solido
    amb = bg[anel > 0].mean(axis=0) if anel.any() else bg.reshape(-1, 3).mean(axis=0)

    # 1) ajusta cor e exposição do Ronilson à cena (sem pintar a pele)
    media = sub[solido > 0].mean(axis=0)
    ganho = (amb / max(amb.mean(), 1)) / (media / max(media.mean(), 1))
    ganho = np.clip(1 + 0.30 * (ganho - 1), 0.80, 1.20)
    expo = float(np.clip((amb.mean() + 55) / (media.mean() + 55), 0.62, 1.08))
    sub = sub * ganho * (expo ** 0.65)

    # 2) luz direcional na pessoa: lado da luz mais claro, lado oposto mais escuro
    X = np.linspace(0, 1, _W, dtype=np.float32)[None, :]
    t = np.clip((X - x0 / _W) / max(nw / _W, 1e-3), 0, 1)
    t = t if luz_x > 0 else 1 - t  # t=0 no lado da luz
    sub *= (1.06 - 0.16 * t)[..., None]
    sub *= (1.0 - 0.06 * np.linspace(0, 1, _H, dtype=np.float32))[:, None, None]

    # 3) light wrap + contorno de luz na borda
    bg_suave = cv2.GaussianBlur(bg, (0, 0), 20)
    nucleo = cv2.GaussianBlur(cv2.erode(a_f, np.ones((13, 13), np.uint8)), (0, 0), 3)
    borda = np.clip(a_f - nucleo, 0, 1)[..., None]
    sub = sub * (1 - 0.38 * borda) + bg_suave * 1.08 * 0.38 * borda
    lado = np.clip(1 - np.abs(t - 0.0) * 2.0, 0, 1)[..., None]
    rim = np.array([255, 205, 130], np.float32) * 0.5 + amb * 0.6
    sub = sub + 0.28 * borda * lado * rim * (1 - sub / 255.0)

    # 4) sombras no cenário: projetada + de contato no chão
    sil = cv2.GaussianBlur(a_f, (0, 0), 26)
    desloc = np.float32([[1, 0, -luz_x * 34], [0, 1, 14]])
    sombra = cv2.warpAffine(sil, desloc, (_W, _H))
    if corpo:
        base_y = int(y0 + alt - 4)
        fx = np.where(a_f[max(0, base_y - 40):min(_H, base_y), :].max(axis=0) > 0.3)[0]
        cx = int(fx.mean()) if len(fx) else x0 + nw // 2
        chao = np.zeros((_H, _W), np.float32)
        cv2.ellipse(chao, (cx, base_y), (int(nw * 0.62), int(_H * 0.016) + 6), 0, 0, 360, 1.0, -1)
        chao = cv2.GaussianBlur(chao, (0, 0), 14)
        sombra = np.clip(sombra + 0.9 * chao, 0, 1)
        degrade = np.clip((np.arange(_H, dtype=np.float32) - (base_y - 30)) / 160.0, 0, 1)
        bg = bg * (1 - 0.22 * degrade)[:, None, None]
    cor_sombra = amb * 0.20
    s = (0.50 * sombra)[..., None]
    bg = bg * (1 - s) + cor_sombra * s

    # 5) composição + grão único em cena e pessoa (esconde emenda de recorte)
    out = bg * (1 - a_f[..., None]) + sub * a_f[..., None]
    out += np.random.RandomState(int(seed) % 100000).normal(0, 2.4, (_H, _W, 1)).astype(np.float32)
    img = Image.fromarray(np.clip(out, 0, 255).astype(np.uint8))
    img = _grade_estilo(img, "cinematic" if estilo == "cinematic" else "showcase")
    return img, corpo, _caixa_cabeca(a_f)


def _responder_com_ronilson(M, tema, legenda, erros_leg, estilo, seed):
    """Card = cenário por estilo/tema + Ronilson (ronilson_sem_fundo) integrado + título."""
    rotulo = ESTILOS[estilo]["rotulo"] if estilo in ESTILOS else "Automático"
    aviso = None
    try:
        _ETAPA["v"] = "escolher recorte do Ronilson"
        recorte, pid = _carregar_recorte_ronilson()
        _ETAPA["v"] = "gerar cenario"
        fundo, aviso = _cenario_ronilson(estilo, tema, seed)
        _ETAPA["v"] = "integrar o Ronilson ao cenario"
        img, em_pe, cabeca = _integrar_ronilson(fundo, recorte, estilo, seed)
        try:
            haar = M._detectar_rosto(img)
            if haar:
                cabeca = haar
        except Exception as e:
            print(f"[ronilson] Haar ignorado: {e}")
        _ETAPA["v"] = "montar o card (titulo/layout)"
        cor_dest, cor_fundo_txt = M._escolher_cor_destaque(seed)
        card, _ = M.desenhar_titulo(
            img, tema, seed, cor_dest=cor_dest, cor_fundo_txt=cor_fundo_txt,
            cor_overlay=None, tem_pessoa=True, em_pe=em_pe, cabeca_bbox=cabeca)
        card_id = f"preview_{uuid.uuid4().hex[:10]}"
        saida = io.BytesIO()
        card.save(saida, format="JPEG", quality=93)
        card_bytes = saida.getvalue()
        M._cards_pendentes[card_id] = {
            "tema": tema, "legenda": legenda, "imagem_fundo": "",
            "pid_fundo": f"ronilson_sem_fundo:{estilo}:{pid}", "card_bytes": card_bytes,
        }
    except ErroEstilo as e:
        return jsonify({"erro": f"Com Ronilson ({rotulo}): {e}"}), 502
    except Exception as e:
        traceback.print_exc()
        return jsonify({"erro": f"Erro Com Ronilson ({rotulo}) (etapa: {_ETAPA['v']}): "
                                f"{type(e).__name__}: {str(e)[:200]}"}), 500
    resp = {
        "card_id": card_id,
        "preview_url": f"data:image/jpeg;base64,{base64.b64encode(card_bytes).decode()}",
        "legenda": legenda, "imagem_fundo": "", "foto_ronilson": pid,
    }
    if erros_leg:
        resp["aviso_legenda"] = erros_leg
    if aviso:
        resp["aviso_estilo"] = aviso
    return jsonify(resp)


@bp.route("/preview-card-estilo", methods=["POST"])
def rota_preview_card_estilo():
    import cloudinary.uploader

    M = _m()

    data = request.get_json() or {}
    tema = data.get("tema", "").strip()
    legenda = data.get("legenda", "").strip()
    estilo = (data.get("estilo") or "").strip().lower()
    if not tema:
        return jsonify({"erro": "Tema obrigatorio"}), 400
    com_ronilson = bool(data.get("com_ronilson"))  # v57: foto sem fundo do Ronilson integrada ao cenario
    if com_ronilson and estilo in ("", "auto"):
        estilo = "auto"
    elif estilo not in ESTILOS:
        return jsonify({"erro": "Estilo invalido"}), 400

    # Legenda: mesmo tratamento do /preview-card
    erros_leg = None
    if not legenda:
        try:
            legenda = M.gerar_legenda_ia(tema)
        except Exception as e:
            erros_leg = str(e)
            legenda = ""
    if legenda and "CRP 04/57327" not in legenda:
        legenda = legenda.rstrip() + M.ASSINATURA

    seed = M._seed_variavel(tema, data.get("seed"))
    print(f"[estilo] tema='{tema}' estilo='{estilo}' seed={seed}")

    if com_ronilson:  # v57: caminho novo; os demais estilos seguem abaixo, intactos
        return _responder_com_ronilson(M, tema, legenda, erros_leg, estilo, seed)

    tmp_pid = ""
    _ETAPA["v"] = "gerar imagem-base"
    try:
        base, aviso = _base_cena(estilo, seed, tema, data.get("variante"))

        # Envia a base como arquivo temporário no Cloudinary para usar o motor de tipografia
        _ETAPA["v"] = "upload temporario no Cloudinary"
        buf = io.BytesIO()
        base.convert("RGB").save(buf, format="JPEG", quality=95)
        buf.seek(0)
        res = cloudinary.uploader.upload(
            buf,
            public_id=f"{M.CLOUDINARY_PREVIEW}/estilo_tmp_{uuid.uuid4().hex[:10]}",
            resource_type="image",
            overwrite=True,
        )
        url_tmp = res.get("secure_url", "")
        tmp_pid = res.get("public_id", "")
        if not url_tmp:
            raise ErroEstilo("Falha ao preparar a imagem do estilo (upload temporario).")

        _ETAPA["v"] = "montar o card (titulo/layout)"
        card = None
        if _TITULO_INTELIGENTE and estilo in _ESTILOS_COM_PESSOA:
            try:
                card = _card_titulo_inteligente(M, base, tema, seed)
            except Exception as e:
                print(f"[estilo] titulo inteligente falhou, usando o caminho padrao: {e}")
                card = None
        if card is None:
            card = M.gerar_card_imagem(tema, legenda, url_tmp, tmp_pid, seed=seed)

        card_id = f"preview_{uuid.uuid4().hex[:10]}"
        saida = io.BytesIO()
        card.save(saida, format="JPEG", quality=93)
        card_bytes = saida.getvalue()
        preview_url = f"data:image/jpeg;base64,{base64.b64encode(card_bytes).decode()}"
        M._cards_pendentes[card_id] = {
            "tema": tema,
            "legenda": legenda,
            "imagem_fundo": "",
            "pid_fundo": f"estilo:{estilo}",
            "card_bytes": card_bytes,
        }
    except ErroEstilo as e:
        return jsonify({"erro": f"Estilo {ESTILOS[estilo]['rotulo']}: {e}"}), 502
    except Exception as e:
        traceback.print_exc()
        return (
            jsonify(
                {
                    "erro": f"Erro no estilo {ESTILOS[estilo]['rotulo']} "
                    f"(etapa: {_ETAPA['v']}): {type(e).__name__}: {str(e)[:200]}"
                }
            ),
            500,
        )
    finally:
        if tmp_pid:
            try:
                cloudinary.uploader.destroy(tmp_pid)
            except Exception as e:
                print(f"[estilo] nao apagou temporario {tmp_pid}: {e}")

    resp = {
        "card_id": card_id,
        "preview_url": preview_url,
        "legenda": legenda,
        "imagem_fundo": "",
    }
    if erros_leg:
        resp["aviso_legenda"] = erros_leg
    if _ETAPA.get("variante") and _ETAPA["variante"] != "-":
        resp["variante"] = _ETAPA["variante"]
    if aviso:
        resp["aviso_estilo"] = aviso
    return jsonify(resp)
