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


# ── v55: Cinematic/Showcase — rosto realista + espaço livre no topo para o título ─
_ESTILOS_COM_PESSOA = ("cinematic", "showcase")

_COMPOSICAO_PESSOA = (
    "Vertical 4:5 Instagram portrait. If a person appears, frame a medium close-up (head, shoulders and "
    "upper chest): the face is NOT huge, it occupies only about 22 to 26 percent of the image width, "
    "placed slightly right of center and LOW in the frame, with the top of the head at about 45 percent "
    "of the image height and never cropped. The entire UPPER 40 percent of the frame is calm, dark, "
    "softly out-of-focus background (shadowed wall or curtain, gentle bokeh) with no lamp, no window, "
    "no picture frame, no bright spot and no high-contrast detail, reserved for large typography. "
    "If no person appears, place the main subject in the lower two thirds with the same calm dark upper area."
)

_REALISMO_PESSOA = (
    "If a real person appears, the portrait must be indistinguishable from an unretouched photograph of a real, "
    "ordinary adult shot on a full-frame camera with an 85mm f/1.8 lens: natural skin with visible pores, fine "
    "lines, subtle uneven tone, slight redness and natural under-eye shadows, a few stray flyaway hairs, slight "
    "natural facial asymmetry, sharp realistic eyes with natural catchlights and detailed irises, natural lips and "
    "teeth, believable fabric texture with real wrinkles, genuine candid expression (not a posed stock-photo smile), "
    "soft natural film grain. Avoid anything that reads as AI-generated: no airbrushed, waxy or plastic skin, "
    "no beauty-filter smoothing, no perfectly symmetrical idealized face, no glossy over-sharpened eyes, "
    "no oversaturated colors, no HDR halo, no illustration or 3D-render look."
)

_REFORCO_ENQUADRAMENTO = (
    " IMPORTANT FRAMING: pull the camera back to a medium shot; the face must be small (about 20 percent of the "
    "image width) and sit in the lower half of the frame, leaving the whole upper 45 percent empty, dark and out of focus."
)


def _prompt(estilo, tema=""):
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
    if estilo in _ESTILOS_COM_PESSOA:
        composicao = _COMPOSICAO_PESSOA
        realismo = _REALISMO_PESSOA + " "

    return (
        "Photorealistic editorial photograph for AlvoreSer, a Brazilian psychology clinic "
        "whose identity is dawn, hope, emotional care, healing and transformation. "
        f"{contexto_tema}"
        f"Visual style and scene: {e['cena']}. Lighting: {e['luz']}. "
        "Color palette strictly harmonious with clinic identity: deep navy #024059, petroleum teal #1B797D, "
        "soft sage #779993, solar orange #F9AB0B as accent light only, snow white haze #F4F6F8. "
        "Mood: professional, welcoming, intimate, never clinical-cold, never hospital, "
        f"elevated realism, authentic photographic texture. {composicao} {realismo}"
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
# v55: reenquadramento (espaço livre no topo p/ o título) e acabamento fotográfico
_W, _H = 1080, 1350
_DY_MAX = int(_H * 0.30)          # desloca no máximo ~405px (senão corta demais o corpo)
_ALVO_TOPO_ROSTO = int(_H * 0.40)  # topo da folga do rosto (como o motor mede) deve ficar abaixo disto
_cascata_rosto = None


def _medir_rosto(img):
    """(x, y, w, h) do maior rosto frontal (Haar, tolerante) ou None."""
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


def _acabamento_fotografico(img, seed):
    """Grão de filme fino + microcontraste: tira o ar liso/plástico de imagem gerada."""
    rng = np.random.default_rng(int(seed) % (2 ** 32))
    a = np.asarray(img.convert("RGB"), dtype=np.float32)
    lum = a.mean(axis=2, keepdims=True) / 255.0
    amp = 3.2 * (1.15 - 0.6 * lum)
    a = (a
         + rng.normal(0.0, 1.0, a.shape[:2] + (1,)).astype(np.float32) * amp
         + rng.normal(0.0, 0.7, a.shape).astype(np.float32))
    out = Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))
    return out.filter(ImageFilter.UnsharpMask(radius=1.2, percent=40, threshold=3))


def _base_cena(estilo, seed, tema=""):
    M = _m()
    prompt = _prompt(estilo, tema)
    print(f"[estilo] Gerando imagem IA para '{estilo}'...")
    img, motivo = _gerar_imagem_ia(prompt)
    aviso = None
    if img is None:
        print(f"[estilo] Falha na imagem IA ({motivo}), usando gradiente da paleta")
        img = M._gerar_fundo_gradiente(M.MARINHO, M.PETROLEO, seed)
        aviso = f"A imagem por IA falhou ({motivo}); usei o gradiente da paleta."

    # v55: Cinematic/Showcase — libera o topo para o título e dá acabamento fotográfico
    if img is not None and aviso is None and estilo in _ESTILOS_COM_PESSOA:
        try:
            rosto = _medir_rosto(img)
            dy = _dy_necessario(rosto)
            if rosto is not None and dy > _DY_MAX:
                print(f"[estilo] rosto grande/alto demais (dy={dy}); tentando 1 nova geracao")
                img2, _ = _gerar_imagem_ia(prompt + _REFORCO_ENQUADRAMENTO)
                if img2 is not None:
                    rosto2 = _medir_rosto(img2)
                    if rosto2 is not None and _dy_necessario(rosto2) < dy:
                        img, rosto, dy = img2, rosto2, _dy_necessario(rosto2)
            if rosto is not None and dy > 12:
                dy = min(dy, _DY_MAX)
                print(f"[estilo] abrindo {dy}px de espaco livre no topo para o titulo")
                img = _abrir_espaco_topo(img, dy)
            img = _acabamento_fotografico(img, seed)
        except Exception as e:
            print(f"[estilo] enquadramento/acabamento falhou: {e}")
    return img, aviso


# ── Rota ──────────────────────────────────────────────────────────────────────
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
    if estilo not in ESTILOS:
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

    tmp_pid = ""
    _ETAPA["v"] = "gerar imagem-base"
    try:
        base, aviso = _base_cena(estilo, seed, tema)

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
    if aviso:
        resp["aviso_estilo"] = aviso
    return jsonify(resp)
