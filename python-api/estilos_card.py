"""
python-api/estilos_card.py  —  v45  —  Estilos visuais (caminho ISOLADO)

Rota propria: POST /preview-card-estilo   (a plataforma so chama esta rota quando
um botao de estilo esta selecionado; "Automatico" continua usando /preview-card,
que nao conhece nada daqui).

Este modulo NAO altera nenhuma funcao do main.py: apenas as USA (somente leitura),
para gerar o card com o mesmo motor de titulo/layout de sempre:

  * estilos "cena"   -> imagem-metafora criada por IA (paleta da clinica) vira a
                        foto-base do card.
  * estilos "pessoa" -> foto do Ronilson (recorte rembg) com FUNDO criado por IA.

Como o motor do card recebe uma URL de imagem, a imagem-base e enviada como arquivo
temporario ao Cloudinary (pasta de preview, ja ignorada pelas buscas) e apagada ao
final. Se a IA ou o recorte falharem, a rota devolve erro CLARO — nunca troca em
silencio por uma foto qualquer do banco.

Fontes de IA de imagem (nesta ordem):
  1. Gemini de imagem (mesmos modelos/chave do main.py — GEMINI_API_KEY)
  2. Cloudflare Workers AI FLUX.1 schnell (gratuito), se CLOUDFLARE_ACCOUNT_ID e
     CLOUDFLARE_API_TOKEN estiverem configurados no Render.
"""
import base64
import io
import os
import random
import sys
import time
import traceback
import uuid

import requests
from flask import Blueprint, jsonify, request
from PIL import Image, ImageEnhance

bp = Blueprint("estilos_card", __name__)


def _m():
    """Modulo principal (main.py) ja carregado — usado somente para leitura."""
    return sys.modules.get("main") or sys.modules.get("__main__")


class ErroEstilo(Exception):
    """Falha esperada ao montar o card de um estilo (mensagem vai para a tela)."""


_ETAPA = {"v": "inicio"}                 # etapa em andamento (vai na mensagem de erro)
_CACHE_RONILSON = {"rec": None, "t": 0.0}  # lista de fotos do Ronilson (10 min)


# ── Catalogo de estilos ───────────────────────────────────────────────────────
ESTILOS = {
    "gold": {"tipo": "cena", "rotulo": "Kintsugi",
        "luz": "soft dawn side-light with warm solar-orange glints on the gold",
        "cena": "a single handmade ceramic bowl in matte deep navy and petroleum teal glaze, "
                "broken and beautifully mended with luminous gold seams (kintsugi), resting "
                "on dark stone, shallow depth of field, the gold veins catching light"},
    "smoke": {"tipo": "cena", "rotulo": "Fumaca",
        "luz": "low warm solar-orange dawn glow backlighting the mist",
        "cena": "slow ribbons of soft mist and smoke dissolving upward into clear air, "
                "deep navy and petroleum teal atmosphere, weightless, calm, tension dissipating"},
    "portal": {"tipo": "cena", "rotulo": "Portal",
        "luz": "golden-orange sunrise light flooding in from outside the doorway",
        "cena": "an open wooden doorway seen from a quiet dark interior, bright dawn light "
                "and soft sage plants at the threshold, an invitation to take the first step, "
                "no one in frame"},
    "ice": {"tipo": "cena", "rotulo": "Gelo",
        "luz": "first warm solar-orange light refracting through the ice",
        "cena": "clear ice slowly melting into still transparent water, teal and petroleum "
                "reflections, fine droplets, the thaw of frozen feelings, hope"},
    "floating": {"tipo": "cena", "rotulo": "Flutuante",
        "luz": "soft diffused dawn light, gentle shadows",
        "cena": "three or four simple symbolic objects gently suspended in mid-air with lots of "
                "empty space: a ceramic cup, a few leaves, a thin golden thread, on a smooth "
                "petroleum teal to navy gradient backdrop, minimal and airy"},
    "macro": {"tipo": "cena", "rotulo": "Macro",
        "luz": "a single point of solar-orange light in creamy bokeh",
        "cena": "extreme macro close-up of a dewdrop resting on a sage-green leaf vein, razor-thin "
                "depth of field, creamy teal bokeh, jewel-like premium detail"},
    "museum": {"tipo": "cena", "rotulo": "Museu",
        "luz": "a single soft museum spotlight from above",
        "cena": "one small symbolic object displayed like a work of art in a minimal elegant "
                "gallery: a mended ceramic piece on a low plinth, deep navy wall with a subtle "
                "petroleum gradient, silent, refined, premium"},
    "showcase": {"tipo": "pessoa", "rotulo": "Showcase",
        "luz": "soft magazine-cover studio lighting with a gentle rim light",
        "cena": "premium editorial studio backdrop: seamless smooth gradient in deep navy and "
                "petroleum teal, subtle floor reflection, refined and clean, no objects"},
    "cinematic": {"tipo": "pessoa", "rotulo": "Cinematic",
        "luz": "volumetric dawn haze with warm solar-orange highlights",
        "cena": "cinematic atmosphere, anamorphic bokeh lights, teal shadows and warm highlights, "
                "film-still depth, wide atmospheric background, no objects"},
}


def _prompt(estilo, para_pessoa):
    e = ESTILOS[estilo]
    if para_pessoa:
        composicao = (
            "Vertical 4:5 Instagram portrait. EMPTY background plate only, no people. "
            "Keep the LEFT 40% calm and slightly darker for large typography; soft depth "
            "so a standing person can be composited on the right side."
        )
    else:
        composicao = (
            "Vertical 4:5 Instagram portrait. Keep the UPPER-LEFT third calm, darker and "
            "free of detail for large typography; place the main subject in the lower "
            "two thirds, slightly right of center, with generous negative space."
        )
    return (
        "Photorealistic editorial photograph for AlvoreSer, a Brazilian psychology "
        "clinic whose identity is dawn, hope and emotional care. "
        f"Scene: {e['cena']}. Lighting: {e['luz']}. "
        "Color palette strictly: deep navy #024059, petroleum teal #1B797D, "
        "soft sage #779993, solar orange #F9AB0B as accent light only, snow white "
        "haze #F4F6F8. Mood: professional, welcoming, intimate, never clinical-cold, "
        f"never hospital. {composicao} "
        "No people, no faces, no hands, no text, no letters, no logos, no watermark, no borders."
    )


# ── IA de imagem: Gemini -> Cloudflare (opcional) ─────────────────────────────
_GEMINI_IMAGE_EXTRA = (
    "gemini-3.5-flash",
    "gemini-3.5-flash-preview",
    "gemini-3.0-flash",
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
                url = ("https://generativelanguage.googleapis.com/v1beta/models/"
                       f"{modelo}:generateContent?key={chave}")
                r = requests.post(url, json=payload, timeout=60)
                if r.status_code >= 400:
                    print(f"[estilo] {modelo} HTTP {r.status_code}: {r.text[:200]}")
                    dica = {429: "sem cota — confira plano/faturamento da chave Gemini",
                            404: "modelo nao existe para esta chave",
                            403: "chave sem permissao"}.get(r.status_code, "requisicao recusada")
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
            url = (f"https://api.cloudflare.com/client/v4/accounts/{conta}"
                   "/ai/run/@cf/black-forest-labs/flux-1-schnell")
            r = requests.post(url, headers={"Authorization": f"Bearer {token}"},
                              json={"prompt": prompt[:2000], "steps": 6}, timeout=70)
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


# ── Foto do Ronilson (Cloudinary com pastas dinamicas ou fixas) ───────────────
def _buscar_foto_ronilson():
    """Retorna (url, public_id) ou (None, diagnostico)."""
    import cloudinary.api
    M = _m()

    def valido(r):
        pid = r.get("public_id", "")
        return M.CLOUDINARY_POSTS not in pid and M.CLOUDINARY_PREVIEW not in pid

    def eh_ronilson(r):
        alvo = " ".join(str(r.get(k) or "") for k in
                        ("public_id", "asset_folder", "folder", "display_name"))
        return "ronilson" in alvo.lower().replace("\\", "/")

    rec, pastas, total = [], set(), 0
    if _CACHE_RONILSON["rec"] and time.time() - _CACHE_RONILSON["t"] < 600:
        c = M._proxima_foto_baralho("_ronilson", _CACHE_RONILSON["rec"])
        return c.get("secure_url"), c.get("public_id", "")
    try:
        for pasta in ("Banco de Imagens/Ronilson", "banco de imagens/ronilson",
                      "Banco de imagens/Ronilson", "Ronilson", "ronilson",
                      "banco de imagens/Ronilson", M.PASTA_RONILSON):
            try:
                res = cloudinary.api.resources(type="upload", prefix=pasta + "/", max_results=500)
                achados = [r for r in res.get("resources", []) if valido(r)]
                if achados:
                    rec = achados
                    break
            except Exception as e:
                print(f"[estilo] prefixo '{pasta}': {e}")

        if not rec:
            cursor = None
            for _ in range(6):
                kw = dict(type="upload", max_results=500)
                if cursor:
                    kw["next_cursor"] = cursor
                res = cloudinary.api.resources(**kw)
                lote = res.get("resources", [])
                total += len(lote)
                for r in lote:
                    for k in ("asset_folder", "folder"):
                        if r.get(k):
                            pastas.add(r[k])
                rec += [r for r in lote if eh_ronilson(r) and valido(r)]
                cursor = res.get("next_cursor")
                if not cursor:
                    break
    except Exception as e:
        return None, f"erro ao consultar o Cloudinary: {e}"

    if not rec:
        return None, (f"{total} imagens verificadas; pastas encontradas: "
                      f"{sorted(pastas)[:15] or 'nenhuma informada'}")
    _CACHE_RONILSON["rec"], _CACHE_RONILSON["t"] = rec, time.time()
    c = M._proxima_foto_baralho("_ronilson", rec)
    print(f"[estilo] foto do Ronilson: {c.get('public_id')} ({c.get('asset_folder') or c.get('folder')})")
    return c.get("secure_url"), c.get("public_id", "")


# ── Montagem da imagem-base de cada tipo de estilo ────────────────────────────
def _base_cena(estilo, seed):
    M = _m()
    img, motivo = _gerar_imagem_ia(_prompt(estilo, False))
    aviso = None
    if img is None:
        img = M._gerar_fundo_gradiente(M.MARINHO, M.PETROLEO, seed)
        aviso = f"A imagem por IA falhou ({motivo}); usei o gradiente da paleta."
    return img, aviso


def _base_pessoa(estilo, seed):
    M = _m()
    rgba, img_original, ultimo_erro, tentativas = None, None, None, 3
    for n in range(1, tentativas + 1):
        _ETAPA["v"] = f"buscar foto do Ronilson (tentativa {n}/{tentativas})"
        url, info = _buscar_foto_ronilson()
        if not url:
            raise ErroEstilo(f"Nenhuma foto do Ronilson encontrada no Cloudinary ({info}).")
        try:
            r = requests.get(url, timeout=30)
            r.raise_for_status()
            img = Image.open(io.BytesIO(r.content)).convert("RGB")
            ratio = max(M.W / img.width, M.H / img.height)
            nw, nh = int(img.width * ratio), int(img.height * ratio)
            img = img.resize((nw, nh), Image.Resampling.LANCZOS)
            esq, topo = (nw - M.W) // 2, (nh - M.H) // 2
            img = img.crop((esq, topo, esq + M.W, topo + M.H))
            img_original = img
        except Exception as e:
            ultimo_erro = f"download da foto: {e}"
            print(f"[estilo] tentativa {n}: {ultimo_erro}")
            continue
        _ETAPA["v"] = f"recortar a pessoa (tentativa {n}/{tentativas})"
        try:
            rgba = M.remover_fundo_rembg(img)
        except Exception as e:
            ultimo_erro = f"recorte: {type(e).__name__}: {e}"
            print(f"[estilo] tentativa {n}: {ultimo_erro}")
            rgba = None
        if rgba is None:
            ultimo_erro = ultimo_erro or "o recorte nao achou uma pessoa nessa foto"
            print(f"[estilo] tentativa {n}: {ultimo_erro}")
            continue
        try:
            if not M._avaliar_silhueta_pessoa(rgba):
                print(f"[estilo] tentativa {n}: silhueta ruim — mantendo ultima mesmo assim")
        except Exception:
            pass
        break
    if rgba is None:
        if img_original is not None:
            print("[estilo] recorte falhou em todas as tentativas — usando foto original SEM fundo novo")
            fundo = M._gerar_fundo_gradiente(M.MARINHO, M.PETROLEO, seed)
            composto = Image.blend(fundo, img_original, 0.92)
            composto = ImageEnhance.Sharpness(composto).enhance(1.08)
            composto = ImageEnhance.Contrast(composto).enhance(1.03)
            aviso = (f"Nao consegui recortar nenhuma das {tentativas} fotos sorteadas "
                     f"({ultimo_erro}); mantive a foto original com fundo suave.")
            return composto, aviso
        raise ErroEstilo(f"nao consegui recortar nenhuma das {tentativas} fotos sorteadas "
                         f"({ultimo_erro}).")
    _ETAPA["v"] = "gerar fundo por IA"
    aviso = None
    fundo, motivo = _gerar_imagem_ia(_prompt(estilo, True))
    if fundo is None:
        fundo = M._gerar_fundo_gradiente(M.MARINHO, M.PETROLEO, seed)
        aviso = f"O fundo por IA falhou ({motivo}); usei o gradiente da paleta."

    try:
        composto, _bbox = M.compor_pessoa(rgba, fundo)
    except Exception as e:
        print(f"[estilo] compor_pessoa falhou: {e}")
        fundo2 = M._gerar_fundo_gradiente(M.MARINHO, M.PETROLEO, seed)
        composto = fundo2.convert("RGBA")
        composto.paste(rgba, (int(M.W * 0.35), 0), rgba)
        composto = composto.convert("RGB")
        aviso = (aviso + " " if aviso else "") + f"Composicao automatica (erro: {e})."
    composto = ImageEnhance.Sharpness(composto).enhance(1.08)
    composto = ImageEnhance.Contrast(composto).enhance(1.03)
    return composto, aviso


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
        if ESTILOS[estilo]["tipo"] == "cena":
            base, aviso = _base_cena(estilo, seed)
        else:
            base, aviso = _base_pessoa(estilo, seed)

        # O motor do card recebe URL: envia a base como arquivo temporario.
        _ETAPA["v"] = "upload temporario no Cloudinary"
        buf = io.BytesIO()
        base.convert("RGB").save(buf, format="JPEG", quality=95)
        buf.seek(0)
        res = cloudinary.uploader.upload(
            buf, public_id=f"{M.CLOUDINARY_PREVIEW}/estilo_tmp_{uuid.uuid4().hex[:10]}",
            resource_type="image", overwrite=True)
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
            "tema": tema, "legenda": legenda,
            "imagem_fundo": "", "pid_fundo": f"estilo:{estilo}",
            "card_bytes": card_bytes}
    except ErroEstilo as e:
        return jsonify({"erro": f"Estilo {ESTILOS[estilo]['rotulo']}: {e}"}), 502
    except Exception as e:
        traceback.print_exc()
        return jsonify({"erro": f"Erro no estilo {ESTILOS[estilo]['rotulo']} "
                                f"(etapa: {_ETAPA['v']}): {type(e).__name__}: {str(e)[:200]}"}), 500
    finally:
        if tmp_pid:
            try:
                cloudinary.uploader.destroy(tmp_pid)
            except Exception as e:
                print(f"[estilo] nao apagou temporario {tmp_pid}: {e}")

    resp = {"card_id": card_id, "preview_url": preview_url,
            "legenda": legenda, "imagem_fundo": ""}
    if erros_leg:
        resp["aviso_legenda"] = erros_leg
    if aviso:
        resp["aviso_estilo"] = aviso
    return jsonify(resp)
