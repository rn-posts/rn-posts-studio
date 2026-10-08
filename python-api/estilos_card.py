"""
python-api/estilos_card.py  —  v46  —  Estilos visuais (caminho ISOLADO)

Rota propria: POST /preview-card-estilo   (a plataforma so chama esta rota quando
um botao de estilo esta selecionado; "Automatico" continua usando /preview-card,
que nao conhece nada daqui).

NOVIDADES v46:
  * Cinematic e Showcase com FUNDO PROCEDURAL 100% local (sem depender de IA de
    imagem). Cinematic = luzes bokeh anamórficas + feixe de luz + névoa + color
    grade teal/laranja + vinheta + grão. Showcase = estúdio editorial limpo com
    reflexão sutil + luz contorno.
  * Blindagem total contra estouro de memória do rembg no Render free (512MB).
    Qualquer falha no recorte cai em composição suave SEM erro 500.

Este modulo NAO altera nenhuma funcao do main.py: apenas as USA (somente leitura),
para gerar o card com o mesmo motor de titulo/layout de sempre.
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
from PIL import Image, ImageEnhance, ImageFilter, ImageDraw

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


# ── Fundos PROCEDURAIS (sem IA) para Cinematic e Showcase ────────────────────
def _fundo_cinematic_procedural(cor1, cor2, seed):
    """Fundo cinematográfico 100% procedural, sem IA.
    Componentes:
    - Gradiente base teal→petróleo com deslocamento vertical
    - Luzes bokeh anamórficas (elipses horizontais) de várias cores/tamanhos
    - Feixe de luz volumétrico diagonal (luz do amanhecer)
    - Névoa atmosférica baixa
    - Ruído cinematográfico sutil
    """
    M = _m()
    W_, H_ = M.W, M.H
    rng = random.Random(seed)

    arr = np.zeros((H_, W_, 3), dtype=np.float32)

    # 1) Gradiente base (vertical com leve diagonal) — VETORIZADO (v47): o laco
    #    pixel a pixel em Python levava dezenas de segundos no Render free.
    _yy = (np.arange(H_, dtype=np.float32) / H_)[:, None]
    _xx = (np.arange(W_, dtype=np.float32) / W_)[None, :]
    _t = _yy * 0.75 + _xx * 0.25
    for ch in range(3):
        arr[:, :, ch] = cor1[ch] * (1 - _t) + cor2[ch] * _t

    # 2) Bokeh anamórfico (elipses achatadas horizontalmente)
    ys, xs = np.ogrid[:H_, :W_]
    cores_bokeh = [
        (249, 171, 11),   # laranja solar (realce)
        (244, 246, 248),  # branco névoa
        (27, 121, 125),   # petróleo
        (119, 153, 147),  # sage
    ]
    n_bokeh = 28 + (seed % 12)
    for i in range(n_bokeh):
        cor = cores_bokeh[i % len(cores_bokeh)]
        cx = rng.uniform(0.05, 0.95) * W_
        cy = rng.uniform(0.05, 0.90) * H_
        raio_x = rng.uniform(18, 120) * (rng.uniform(0.4, 1.0))
        raio_y = raio_x * rng.uniform(0.25, 0.55)
        intensidade = rng.uniform(0.12, 0.55)
        # v47: calcula so numa janela (+-3 raios) — fora disso exp(-d2*2) ~ 0
        x0 = max(0, int(cx - raio_x * 3)); x1 = min(W_, int(cx + raio_x * 3) + 1)
        y0 = max(0, int(cy - raio_y * 3)); y1 = min(H_, int(cy + raio_y * 3) + 1)
        if x1 <= x0 or y1 <= y0:
            continue
        dx = (xs[:, x0:x1] - cx) / raio_x
        dy = (ys[y0:y1, :] - cy) / raio_y
        d2 = dx*dx + dy*dy
        masc = (np.exp(-d2 * 2.0) * intensidade).astype(np.float32)
        for ch in range(3):
            arr[y0:y1, x0:x1, ch] = np.clip(arr[y0:y1, x0:x1, ch] + masc * cor[ch], 0, 255)

    # 3) Feixe de luz volumétrico (diagonal, do canto superior direito → meio)
    cx_fim = W_ * rng.uniform(0.35, 0.55)
    cy_fim = H_ * rng.uniform(0.45, 0.65)
    cx_ini = W_ * rng.uniform(0.82, 0.96)
    cy_ini = H_ * rng.uniform(-0.05, 0.08)
    dx, dy = cx_fim - cx_ini, cy_fim - cy_ini
    len_feixe = (dx*dx + dy*dy)**0.5
    ux, uy = dx / len_feixe, dy / len_feixe
    px = xs - cx_ini
    py = ys - cy_ini
    proj = px * ux + py * uy
    perp = np.abs(-px * uy + py * ux)
    masc_feixe = (proj >= 0) & (proj <= len_feixe * 1.2)
    largura_feixe = 140 + proj * 0.35
    intens_feixe = np.exp(-(perp / largura_feixe)**2) * np.exp(-proj / (len_feixe * 0.8)) * 0.28
    for ch in range(3):
        cor_feixe = [249 * 0.6, 200 * 0.6, 100 * 0.6][ch]
        arr[:, :, ch] += masc_feixe * intens_feixe * cor_feixe

    # 4) Névoa baixa (rodapé atmosférico)
    t_nevoa = np.clip((ys - H_*0.55) / (H_*0.45), 0, 1)
    for ch in range(3):
        arr[:, :, ch] = np.clip(
            arr[:, :, ch] * (1 - t_nevoa * 0.45) + 244 * t_nevoa * 0.45,
            0, 255
        )

    # 5) Ruído cinematográfico sutil (apenas luminância)
    ruido = np.random.RandomState(seed).normal(0, 2.2, (H_, W_))
    arr[:, :, 0] += ruido
    arr[:, :, 1] += ruido * 0.9
    arr[:, :, 2] += ruido * 0.8

    arr = np.clip(arr, 0, 255).astype(np.uint8)
    img = Image.fromarray(arr)
    return img.filter(ImageFilter.GaussianBlur(0.4))


def _fundo_showcase_procedural(cor1, cor2, seed):
    """Fundo de estúdio editorial procedural (estilo revista/magazine cover).
    Componentes:
    - Gradiente seamless de parede (superior) com curvatura sutil para o chão
    - Hotspot de luz principal (key light) no topo-esquerdo
    - Reflexão sutil no "piso" (fade out para o infinito)
    - Luz de preenchimento suave do lado direito
    - Grão ultra-fino
    """
    M = _m()
    W_, H_ = M.W, M.H
    rng = random.Random(seed)

    arr = np.zeros((H_, W_, 3), dtype=np.float32)
    ys, xs = np.ogrid[:H_, :W_]

    # 1) Gradiente parede→piso com curvatura (curva horizonte)
    horizonte_y = H_ * rng.uniform(0.58, 0.65)
    curvatura = (xs - W_*0.5)**2 / (W_**2) * H_ * rng.uniform(0.08, 0.14)
    y_parede = np.clip((ys - (horizonte_y - curvatura)) / (H_ - horizonte_y), 0, 1)
    for ch in range(3):
        arr[:, :, ch] = cor1[ch] * (1 - y_parede) + cor2[ch] * y_parede

    # Leve escurecimento vertical na parede (topo mais escuro → realce dramático)
    t_parede = np.clip(ys / horizonte_y, 0, 1)
    for ch in range(3):
        arr[:, :, ch] *= (0.85 + 0.15 * t_parede)

    # 2) Key light (luz principal quente, topo-esquerdo)
    cx_k = W_ * rng.uniform(0.15, 0.28)
    cy_k = H_ * rng.uniform(0.06, 0.14)
    r_k = max(W_, H_) * 0.7
    d2k = ((xs - cx_k)/r_k)**2 + ((ys - cy_k)/r_k)**2
    keylight = np.exp(-d2k * 1.5) * 0.32
    for ch in range(3):
        cor_k = [249 * 0.9, 205 * 0.9, 130 * 0.9][ch]
        arr[:, :, ch] = np.clip(arr[:, :, ch] + keylight * cor_k, 0, 255)

    # 3) Fill light (direita, mais suave, tom frio/sage)
    cx_f = W_ * rng.uniform(0.80, 0.92)
    cy_f = H_ * rng.uniform(0.45, 0.58)
    r_f = max(W_, H_) * rng.uniform(0.55, 0.75)
    d2f = ((xs - cx_f)/r_f)**2 + ((ys - cy_f)/r_f)**2
    fill = np.exp(-d2f * 2.0) * 0.18
    for ch in range(3):
        cor_f = [119 * 0.8, 153 * 0.8, 147 * 0.8][ch]
        arr[:, :, ch] = np.clip(arr[:, :, ch] + fill * cor_f, 0, 255)

    # 4) Reflexão no piso (faixa sutil clara pós-horizonte)
    masc_refl = (ys >= horizonte_y).astype(np.float32)
    if masc_refl.ndim == 3:
        masc_refl = masc_refl[:, :, 0]
    t_refl = np.clip((ys - horizonte_y) / (H_ * 0.28), 0, 1)
    if t_refl.ndim == 3:
        t_refl = t_refl[:, :, 0]
    intens_refl = (1 - t_refl) * 0.22 * masc_refl
    for ch in range(3):
        arr[:, :, ch] = np.clip(arr[:, :, ch] + intens_refl * 244, 0, 255)

    # 5) Sombra projetada sutil no chão (lugar onde a pessoa vai ficar)
    cx_s = W_ * rng.uniform(0.70, 0.82)
    cy_s = H_ * rng.uniform(0.78, 0.84)
    rx_s = W_ * 0.18
    ry_s = H_ * 0.06
    d2s = ((xs - cx_s)/rx_s)**2 + ((ys - cy_s)/ry_s)**2
    sombra = np.exp(-d2s * 2.5) * 0.25
    for ch in range(3):
        arr[:, :, ch] = np.clip(arr[:, :, ch] * (1 - sombra), 0, 255)

    # 6) Grão ultra-fino
    ruido = np.random.RandomState(seed + 777).normal(0, 1.3, (H_, W_))
    arr[:, :, 0] += ruido
    arr[:, :, 1] += ruido * 0.95
    arr[:, :, 2] += ruido * 0.9

    arr = np.clip(arr, 0, 255).astype(np.uint8)
    return Image.fromarray(arr).filter(ImageFilter.GaussianBlur(0.3))


def _color_grade_cinematic(img):
    """Split toning cinematográfico: sombras teal/azul-petróleo, realces quentes
    (laranja solar). Preserva tons de pele naturais. Aplica vinheta e contraste."""
    arr = np.array(img.convert("RGB"), dtype=np.float32)
    lum = 0.299 * arr[:, :, 0] + 0.587 * arr[:, :, 1] + 0.114 * arr[:, :, 2]
    t_sombra = np.clip((160 - lum) / 160, 0, 1)
    t_realce = np.clip((lum - 130) / 125, 0, 1)

    # Sombras: teal + petróleo (azulado frio)
    sombra_r = -14;  sombra_g = +4;   sombra_b = +18
    # Realces: laranja solar quente
    realce_r = +14;  realce_g = +6;   realce_b = -8

    for ch, s, r in [(0, sombra_r, realce_r), (1, sombra_g, realce_g), (2, sombra_b, realce_b)]:
        arr[:, :, ch] += t_sombra * s + t_realce * r

    # Contraste sutil (S-curve leve)
    arr = arr / 255.0
    arr = np.where(arr < 0.5,
                   0.5 * (2 * arr) ** 1.15,
                   1 - 0.5 * (2 * (1 - arr)) ** 1.15)
    arr = np.clip(arr * 255, 0, 255).astype(np.uint8)
    out = Image.fromarray(arr)

    # Saturação levemente reduzida para ar de filme
    out = ImageEnhance.Color(out).enhance(0.94)
    return out


def _vinheta(img, intensidade=0.32):
    """Vinheta cinematográfica (escurecimento suave nas bordas), radial com
    queda suave (não é uma moldura dura)."""
    W_, H_ = img.size
    ys, xs = np.ogrid[:H_, :W_]
    cx, cy = W_ * 0.5, H_ * 0.5
    d = ((xs - cx) / (W_ * 0.5))**2 + ((ys - cy) / (H_ * 0.5))**2
    vinheta_masc = np.clip(d ** 1.8 * intensidade, 0, 1)
    arr = np.array(img.convert("RGB"), dtype=np.float32)
    for ch in range(3):
        arr[:, :, ch] *= (1 - vinheta_masc)
    arr = np.clip(arr, 0, 255).astype(np.uint8)
    return Image.fromarray(arr)


def _grain_filme(img, seed, intensidade=1.1):
    """Grão de filme 35mm sutil. Não uniforme (luminância, não RGB amarrado)
    para parecer orgânico."""
    W_, H_ = img.size
    rng = np.random.RandomState(seed + 31337)
    arr = np.array(img.convert("RGB"), dtype=np.float32)
    g1 = rng.normal(0, intensidade, (H_, W_))
    g2 = rng.normal(0, intensidade * 0.55, (H_, W_))
    g3 = rng.normal(0, intensidade * 0.45, (H_, W_))
    arr[:, :, 0] += g1
    arr[:, :, 1] += g1 * 0.85 + g2 * 0.3
    arr[:, :, 2] += g1 * 0.70 + g3 * 0.5
    arr = np.clip(arr, 0, 255).astype(np.uint8)
    return Image.fromarray(arr)


def _luz_contorno_pessoa(rgba, fundo, x, seed):
    """Desenha uma luz de contorno (rim light) suave do lado esquerdo da pessoa
    (direção da key light de ambos estilos). Efeito 'cortar' a pessoa do fundo,
    ela não parece uma colagem."""
    M = _m()
    alpha = rgba.split()[3]
    # Expandir alpha 1-2px e subtrair do original → borda
    dil = alpha.filter(ImageFilter.MaxFilter(3))
    contorno = ImageChops_subtract_arr(dil, alpha)
    contorno = contorno.filter(ImageFilter.GaussianBlur(1.5))

    layer = Image.new("RGBA", fundo.size, (0, 0, 0, 0))
    sil = Image.new("RGBA", rgba.size, (255, 220, 150, 0))
    # Cor do contorno: tons quentes (laranja+solar) — intensidade baixa
    arr_sil = np.array(sil, dtype=np.uint8)
    arr_sil[:, :, 3] = np.array(contorno, dtype=np.uint8) // 6
    sil = Image.fromarray(arr_sil)
    layer.paste(sil, (x, 0), sil)
    return Image.alpha_composite(fundo.convert("RGBA"), layer)


def ImageChops_subtract_arr(a_img, b_img):
    a = np.array(a_img, dtype=np.int16)
    b = np.array(b_img, dtype=np.int16)
    out = np.clip(a - b, 0, 255).astype(np.uint8)
    return Image.fromarray(out)


def _compor_pessoa_safe(rgba, fundo, estilo, seed):
    """Composição à prova de falhas. Tenta M.compor_pessoa primeiro; se der
    qualquer erro, faz manualmente (sempre dá certo). NUNCA gera 500."""
    M = _m()
    W_, H_ = M.W, M.H
    try:
        if hasattr(M, "compor_pessoa"):
            return M.compor_pessoa(rgba, fundo)
    except Exception as e:
        print(f"[estilo] compor_pessoa falhou: {e} — fazendo manual")

    # Fallback manual 100% seguro
    pw, ph = rgba.size
    nw = max(1, int(pw * H_ / ph))
    rgba = rgba.resize((nw, H_), Image.Resampling.LANCZOS)
    x = W_ - nw + 50
    x = max(int(W_ * 0.35), min(x, W_ - 120))
    alpha = rgba.split()[3]

    # Sombra sutil no chão
    sombra = Image.new("RGBA", (W_, H_), (0, 0, 0, 0))
    sil = Image.new("RGBA", (nw, H_), (0, 0, 0, 0))
    sil.paste(Image.new("RGB", (nw, H_), (10, 20, 35)),
              mask=alpha.point(lambda v: int(v * 0.12)))
    sombra.paste(sil, (x - 10, 12), sil)
    sombra = sombra.filter(ImageFilter.GaussianBlur(16))

    res = fundo.convert("RGBA")
    res = Image.alpha_composite(res, sombra)
    res = _luz_contorno_pessoa(rgba, res, x, seed)
    res.paste(rgba, (x, 0), rgba)
    return res.convert("RGB"), None


# ── v51: composicao profissional (Cinematic / Showcase) ────────────────────────────────────────────────
def _fundo_cinematic_v2(cor1, cor2, seed, foco):
    """Fundo cinematografico: gradiente escuro (marinho->petroleo), brilho teal
    atras do sujeito (foco), luz quente de amanhecer no canto superior direito,
    feixes volumetricos suaves, nevoa baixa e poucos discos de bokeh anamorfico
    bem desfocados (profundidade de campo, sem aspecto de confete)."""
    import math
    M = _m()
    W_, H_ = M.W, M.H
    rng = random.Random(seed)
    fx, fy = foco
    ys = np.arange(H_, dtype=np.float32)[:, None]
    xs = np.arange(W_, dtype=np.float32)[None, :]

    t = (ys / H_) * 0.8 + (xs / W_) * 0.2
    arr = np.empty((H_, W_, 3), dtype=np.float32)
    for ch in range(3):
        arr[:, :, ch] = cor1[ch] * 0.55 * (1 - t) + cor2[ch] * 0.80 * t

    g = np.exp(-(((xs - fx) / (W_ * 0.55)) ** 2 + ((ys - fy) / (H_ * 0.45)) ** 2) * 1.6)
    for ch, v in enumerate((120, 185, 175)):
        arr[:, :, ch] += g * (v * 0.38)

    w = np.exp(-(((xs - W_ * 0.95) / (W_ * 0.6)) ** 2 + ((ys - H_ * 0.02) / (H_ * 0.5)) ** 2) * 1.8)
    for ch, v in enumerate((255, 190, 110)):
        arr[:, :, ch] += w * (v * 0.22)

    for _ in range(3):
        ang = rng.uniform(0.45, 0.95)
        ox = W_ * rng.uniform(0.85, 1.02)
        oy = -H_ * 0.05
        ux, uy = -math.sin(ang), math.cos(ang)
        px, py = xs - ox, ys - oy
        proj = px * ux + py * uy
        perp = np.abs(-px * uy + py * ux)
        larg = 90 + np.maximum(proj, 0) * 0.22
        inten = (np.exp(-(perp / larg) ** 2) * np.clip(1 - proj / (H_ * 1.3), 0, 1)
                 * (proj > 0) * rng.uniform(0.07, 0.13))
        for ch, v in enumerate((255, 215, 150)):
            arr[:, :, ch] += inten * v

    fog = np.clip((ys - H_ * 0.62) / (H_ * 0.38), 0, 1) * 0.22
    for ch, v in enumerate((90, 150, 155)):
        arr[:, :, ch] = arr[:, :, ch] * (1 - fog) + v * fog

    base = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8)).convert("RGBA")
    del arr
    # v52: paineis de luz bem fora de foco ao fundo (janelas/ambiente), da profundidade de cena
    paineis = Image.new("RGBA", (W_, H_), (0, 0, 0, 0))
    dp = ImageDraw.Draw(paineis)
    for _ in range(5):
        px0 = rng.uniform(0.0, 0.62) * W_
        dp.rectangle([px0, 0, px0 + rng.uniform(0.05, 0.11) * W_, rng.uniform(0.45, 0.80) * H_],
                     fill=(255, 215, 150, rng.randint(14, 30)))
    base = Image.alpha_composite(base, paineis.filter(ImageFilter.GaussianBlur(40)))
    del paineis
    camada = Image.new("RGBA", (W_, H_), (0, 0, 0, 0))
    d = ImageDraw.Draw(camada)
    paleta = [(255, 200, 110)] * 5 + [(244, 246, 248)] * 3 + [(80, 190, 190)] * 3
    for _ in range(12):
        cor = rng.choice(paleta)
        cx = rng.uniform(0.03, 0.78) * W_
        cy = rng.uniform(0.03, 0.80) * H_
        r = rng.uniform(22, 80)
        rx, ry = r * 1.15, r * 0.85
        a = rng.randint(22, 52)
        d.ellipse([cx - rx, cy - ry, cx + rx, cy + ry],
                  fill=cor + (a,), outline=cor + (min(255, a + 18),), width=2)
    camada = camada.filter(ImageFilter.GaussianBlur(6.5))
    return Image.alpha_composite(base, camada).convert("RGB")


def _fundo_showcase_v2(cor1, cor2, seed, foco):
    """Fundo de estudio de campanha: gradiente discreto marinho->petroleo, piscina
    de luz suave atras do sujeito, nucleo claro sutil, luz de chave lateral e
    queda de luz no piso. Limpo, elegante, sem objetos."""
    M = _m()
    W_, H_ = M.W, M.H
    rng = random.Random(seed)
    fx, fy = foco
    ys = np.arange(H_, dtype=np.float32)[:, None]
    xs = np.arange(W_, dtype=np.float32)[None, :]

    t = ys / H_
    arr = np.empty((H_, W_, 3), dtype=np.float32)
    for ch in range(3):
        arr[:, :, ch] = cor1[ch] * 0.62 * (1 - t) + cor2[ch] * 0.72 * t

    g = np.exp(-(((xs - fx) / (W_ * 0.42)) ** 2 + ((ys - (fy + H_ * 0.05)) / (H_ * 0.38)) ** 2) * 1.5)
    for ch, v in enumerate((150, 205, 200)):
        arr[:, :, ch] += g * (v * 0.42)
    nucleo = np.exp(-(((xs - fx) / (W_ * 0.20)) ** 2 + ((ys - (fy + H_ * 0.02)) / (H_ * 0.20)) ** 2) * 1.6)
    for ch, v in enumerate((235, 240, 235)):
        arr[:, :, ch] += nucleo * (v * 0.14)
    kx = W_ * rng.uniform(0.04, 0.14)
    k = np.exp(-(((xs - kx) / (W_ * 0.8)) ** 2 + ((ys + H_ * 0.05) / (H_ * 0.7)) ** 2) * 1.4)
    for ch, v in enumerate((255, 225, 180)):
        arr[:, :, ch] += k * (v * 0.10)
    # v52: faixas de sombra difusa diagonal (luz de estudio recortada), dao textura editorial
    for c_diag, larg_d, forca_d in ((W_ * rng.uniform(0.55, 0.75), W_ * 0.10, 0.16),
                                    (W_ * rng.uniform(0.95, 1.15), W_ * 0.07, 0.12)):
        banda = np.exp(-(((xs * 0.6 + ys * 0.8) - c_diag) / larg_d) ** 2)
        arr *= (1 - banda * forca_d)[:, :, None]
    piso = np.clip((ys - H_ * 0.80) / (H_ * 0.20), 0, 1) * 0.35
    arr *= (1 - piso)[:, :, None]
    return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))


def _compor_pessoa_estilo(rgba, estilo, seed):
    """Composicao profissional: recorta a pessoa pelo contorno real (antes o quadro
    inteiro da foto era empurrado para a direita e o corpo saia cortado), posiciona
    com respiro, cria o fundo ja sabendo onde ela fica e integra com sombra
    ambiente, 'light wrap' (luz do fundo envolvendo a borda) e luz de contorno.
    Retorna (RGB, cabeca_bbox)."""
    from PIL import ImageChops
    M = _m()
    W_, H_ = M.W, M.H
    a0 = rgba.split()[3]
    bb = a0.point(lambda v: 255 if v > 40 else 0).getbbox()
    if not bb:
        raise ErroEstilo("recorte vazio")
    pessoa = rgba.crop(bb)
    pw, ph = pessoa.size
    esc = min(H_ / ph, (W_ * 0.56) / pw, 1.6)
    nw, nh = max(1, int(pw * esc)), max(1, int(ph * esc))
    pessoa = pessoa.resize((nw, nh), Image.Resampling.LANCZOS)
    x = max(int(W_ * 0.44), W_ - nw - int(W_ * 0.02))
    y = H_ - nh

    # v52 — recorte limpo: (1) fecha buracos da mascara; (2) suaviza e come ~4px da borda
    # (some a franja clara do fundo original); (3) descontamina a cor da borda copiando a
    # cor de dentro da pessoa, para nao sobrar halo claro/azul em volta.
    # v53: moldura transparente de 20px. Os filtros do PIL NAO processam a borda da imagem e
    # deixavam um retangulo cru (fundo original) no limite do recorte (topo da cabeca, punho).
    import cv2
    pad = 20
    arr0 = np.asarray(pessoa)
    pad_arr = np.zeros((nh + 2 * pad, nw + 2 * pad, 4), dtype=np.uint8)
    pad_arr[pad:pad + nh, pad:pad + nw] = arr0
    if bb[3] >= rgba.size[1] - 2:   # tocava a base da foto: segue ate o fim do quadro
        pad_arr[pad + nh:, pad:pad + nw] = arr0[-1:, :]
    pessoa = Image.fromarray(pad_arr, "RGBA")
    x, y = x - pad, y - pad
    nw, nh = pessoa.size

    # v53: preenche buracos PEQUENOS e fechados da mascara (rosto/camisa com furos); vaos
    # grandes (ex.: entre braco e tronco) continuam transparentes.
    al = pessoa.split()[3]
    a_np = np.asarray(al)
    inv = (a_np <= 90).astype(np.uint8)
    _n, lab, stats, _c = cv2.connectedComponentsWithStats(inv, connectivity=4)
    ok = stats[:, cv2.CC_STAT_AREA] < 9000
    ok[0] = False
    ok[lab[0, 0]] = False
    buracos = ok[lab]
    if buracos.any():
        al = Image.fromarray(np.where(buracos, 255, a_np).astype(np.uint8))
        print(f"[estilo] mascara: {int(buracos.sum())}px de buracos preenchidos")
    al = al.filter(ImageFilter.MaxFilter(15)).filter(ImageFilter.MinFilter(15))
    al = al.filter(ImageFilter.GaussianBlur(2.2)).point(
        lambda v: 0 if v < 110 else 255 if v > 190 else int((v - 110) * 255 / 80))
    al = al.filter(ImageFilter.MinFilter(9)).filter(ImageFilter.GaussianBlur(1.1))
    rgb_i = np.asarray(pessoa.convert("RGB"), dtype=np.float32)
    interior = al.filter(ImageFilter.MinFilter(25)).filter(ImageFilter.GaussianBlur(6))
    ai = np.asarray(interior, dtype=np.float32)[:, :, None] / 255.0
    pre = np.asarray(Image.fromarray((rgb_i * ai).astype(np.uint8)).filter(
        ImageFilter.GaussianBlur(10)), dtype=np.float32)
    den = np.asarray(interior.filter(ImageFilter.GaussianBlur(10)), dtype=np.float32)[:, :, None] / 255.0
    cor_int = np.clip(pre / np.maximum(den, 0.02), 0, 255)
    w_borda = 1.0 - ai
    limpo = rgb_i * (1.0 - w_borda) + cor_int * w_borda
    pessoa = Image.fromarray(np.clip(limpo, 0, 255).astype(np.uint8)).convert("RGBA")
    pessoa.putalpha(al)
    del rgb_i, ai, pre, den, cor_int, limpo

    # cabeca/rosto (para o titulo nao cruzar) e ponto de foco da luz do fundo
    pa = np.asarray(al.resize((max(1, nw // 4), max(1, nh // 4))))
    linhas = np.where(pa.max(axis=1) > 40)[0]
    r0 = int(linhas[0]) if len(linhas) else 0
    faixa = max(2, int(len(pa) * 0.34))
    cols = np.where(pa[r0:r0 + faixa].max(axis=0) > 40)[0]
    c0, c1 = (int(cols.min()), int(cols.max())) if len(cols) else (0, pa.shape[1] - 1)
    cabeca = (x + c0 * 4 - 20, max(0, y + r0 * 4 - 15),
              x + c1 * 4 + 20, y + (r0 + faixa) * 4 + 20)
    foco = (x + (c0 + c1) * 2, y + r0 * 4 + faixa * 2)

    criar = _fundo_cinematic_v2 if estilo == "cinematic" else _fundo_showcase_v2
    fundo = criar(M.MARINHO, M.PETROLEO, seed, foco)
    comp = fundo.convert("RGBA")
    alpha_c = Image.new("L", (W_, H_), 0)
    alpha_c.paste(al, (x, y))

    # sombra ambiente suave ao redor da pessoa
    sombra = alpha_c.filter(ImageFilter.MaxFilter(15)).filter(
        ImageFilter.GaussianBlur(30)).point(lambda v: int(v * 0.30))
    comp = Image.composite(Image.new("RGBA", comp.size, (4, 10, 20, 255)), comp, sombra)
    comp.paste(pessoa, (x, y), pessoa)
    rgb = comp.convert("RGB")
    del comp

    # light wrap: a luz desfocada do fundo envolve a borda interna da pessoa
    borda = ImageChops.subtract(alpha_c, alpha_c.filter(ImageFilter.MinFilter(15))).filter(
        ImageFilter.GaussianBlur(3))
    envolve = fundo.filter(ImageFilter.GaussianBlur(28))
    rgb = Image.composite(envolve, rgb, borda.point(lambda v: int(v * 0.30)))

    # luz de contorno (rim light) no lado voltado para a luz principal
    d = 7
    a = np.asarray(alpha_c, dtype=np.float32) / 255.0
    if estilo == "cinematic":
        dx, dy, cor_rim, forca = d, -d, (255, 190, 120), 0.50   # amanhecer, vindo da direita
    else:
        dx, dy, cor_rim, forca = -d, -d, (215, 238, 242), 0.32  # luz de estudio, vinda da esquerda
    ap = np.pad(a, d, mode="edge")
    viz = ap[d + dy:d + dy + H_, d + dx:d + dx + W_]
    rim = np.clip(a - viz, 0, 1)
    rim_img = Image.fromarray((rim * 255).astype(np.uint8)).filter(
        ImageFilter.GaussianBlur(2.0)).point(lambda v: min(255, int(v * forca)))
    luz = ImageChops.screen(rgb, Image.new("RGB", rgb.size, cor_rim))
    rgb = Image.composite(luz, rgb, rim_img)
    return rgb, cabeca


def _bloom(img, limiar=190, raio=20, forca=0.22):
    """Halacao suave nas altas luzes (aparencia de lente cinematografica)."""
    from PIL import ImageChops
    img = img.convert("RGB")
    k = 255.0 / max(1, 255 - limiar)
    mascara = img.convert("L").point(lambda v: min(255, int(max(0, v - limiar) * k)))
    mascara = mascara.filter(ImageFilter.GaussianBlur(raio))
    brilho = ImageChops.multiply(mascara.convert("RGB"), Image.new("RGB", img.size, (255, 225, 190)))
    brilho = brilho.point(lambda v: int(v * forca))
    return ImageChops.screen(img, brilho)


def _aplicar_tratamento_estilo(img, estilo, seed):
    """Aplica o pipeline de pós-processamento do estilo (no final, depois de
    colar a pessoa). Cinematic = color grade + vinheta + grão. Showcase =
    grão leve + nitidez."""
    if estilo == "cinematic":
        img = _bloom(img, 190, 20, 0.22)
        img = _color_grade_cinematic(img)
        img = _vinheta(img, 0.30)
        img = _grain_filme(img, seed, 1.0)
        img = ImageEnhance.Sharpness(img).enhance(1.06)
    elif estilo == "showcase":
        img = _vinheta(img, 0.18)
        img = _grain_filme(img, seed, 0.6)
        img = ImageEnhance.Sharpness(img).enhance(1.10)
        img = ImageEnhance.Contrast(img).enhance(1.04)
    return img


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


_ORT_U2NETP = {"sess": None}
_U2NETP_URL = "https://github.com/danielgatis/rembg/releases/download/v0.0.0/u2netp.onnx"
_U2NETP_LADO = 320  # o modelo u2netp so aceita entrada 320x320 (256 da INVALID_ARGUMENT)


def _mem(rotulo):
    """v49: loga a memoria do processo (Linux/Render) para achar onde estoura."""
    try:
        rss = pico = 0
        with open("/proc/self/status") as f:
            for linha in f:
                if linha.startswith("VmRSS:"):
                    rss = int(linha.split()[1]) // 1024
                elif linha.startswith("VmHWM:"):
                    pico = int(linha.split()[1]) // 1024
        print(f"[mem] {rotulo}: atual={rss}MB pico={pico}MB")
    except Exception:
        pass


def _caminho_u2netp():
    import tempfile
    home = os.environ.get("U2NET_HOME") or ""
    destino = os.path.join(tempfile.gettempdir(), "u2netp.onnx")
    for p in (os.path.join(home, "models", "u2netp", "u2netp.onnx"),
              os.path.join(home, "u2netp.onnx"), destino):
        if os.path.isfile(p) and os.path.getsize(p) > 1_000_000:
            return p
    r = requests.get(_U2NETP_URL, timeout=60)
    r.raise_for_status()
    with open(destino, "wb") as f:
        f.write(r.content)
    return destino


def _sessao_u2netp():
    """Sessao ONNX propria (sem importar o rembg): 1 thread, sem arena de memoria."""
    s = _ORT_U2NETP["sess"]
    if s is None:
        import onnxruntime as ort
        op = ort.SessionOptions()
        op.enable_cpu_mem_arena = False
        op.enable_mem_pattern = False
        op.intra_op_num_threads = 1
        op.inter_op_num_threads = 1
        op.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_BASIC
        s = ort.InferenceSession(_caminho_u2netp(), sess_options=op,
                                 providers=["CPUExecutionProvider"])
        _ORT_U2NETP["sess"] = s
    return s


def _mascara_u2netp(original):
    """Mascara alpha (L, tamanho original) da pessoa, mesmo pre/pos-processamento
    que o rembg usa para o u2netp."""
    ow, oh = original.size
    lado = _U2NETP_LADO
    a = np.asarray(original.resize((lado, lado), Image.Resampling.LANCZOS), dtype=np.float32)
    a = a / max(float(a.max()), 1e-6)
    media = np.array([0.485, 0.456, 0.406], dtype=np.float32)
    desvio = np.array([0.229, 0.224, 0.225], dtype=np.float32)
    x = ((a - media) / desvio).transpose(2, 0, 1)[None].astype(np.float32)
    sess = _sessao_u2netp()
    _mem("sessao u2netp pronta")
    saida = sess.run(None, {sess.get_inputs()[0].name: x})[0]
    pred = saida[0, 0]
    mi, ma = float(pred.min()), float(pred.max())
    pred = (pred - mi) / max(ma - mi, 1e-6)
    m = Image.fromarray((pred * 255).astype(np.uint8))
    return m.resize((ow, oh), Image.Resampling.BICUBIC)


def _evitar_pymatting():
    """v48: o rembg importa pymatting (so usado em alpha matting, que nao usamos) e
    o pymatting compila funcoes numba NO IMPORT. No Render (Python 3.14, sem cache)
    isso passa dos 300s do gunicorn -> worker abortado e SIGKILL -> 500. Registra
    modulos vazios para esses 3 imports antes de importar o rembg. Se o pymatting
    real ja foi carregado (fluxo normal do main.py), nao faz nada."""
    if "pymatting" in sys.modules:
        return
    import types

    def _desativado(*a, **k):
        raise RuntimeError("pymatting desativado (alpha matting nao usado)")

    for nome, attrs in (
        ("pymatting", {}),
        ("pymatting.alpha", {}),
        ("pymatting.alpha.estimate_alpha_cf", {"estimate_alpha_cf": _desativado}),
        ("pymatting.foreground", {}),
        ("pymatting.foreground.estimate_foreground_ml", {"estimate_foreground_ml": _desativado}),
        ("pymatting.util", {}),
        ("pymatting.util.util", {"stack_images": _desativado}),
    ):
        m = types.ModuleType(nome)
        m.__dict__.update(attrs)
        m.__path__ = []
        sys.modules[nome] = m
    print("[estilo] pymatting/numba evitado (sem compilacao JIT)")


def _recortar_pessoa_leve(img):
    """v47: recorte com UM unico modelo leve (u2netp). O remover_fundo_rembg do
    main.py cai no u2net_human_seg (~170MB) quando a silhueta vem ruim, e junto
    com o resto isso estoura os 512MB do Render free (SIGKILL -> 500). Aqui,
    silhueta ruim devolve None e o chamador tenta outra foto."""
    import gc
    M = _m()
    original = img.convert("RGB")
    ow, oh = original.size
    _mem("antes do recorte")
    alpha = _mascara_u2netp(original)
    _mem("depois da mascara")
    r, g, b = original.split()
    rgba = M._afinar_mascara(Image.merge("RGBA", (r, g, b, alpha)))
    del alpha
    gc.collect()
    if M._avaliar_silhueta_pessoa(rgba):
        print("[estilo] recorte leve ok (u2netp)")
        return rgba
    print("[estilo] recorte leve: silhueta ruim")
    return None


def _base_pessoa(estilo, seed):
    M = _m()
    rgba, img_original, ultimo_erro, tentativas = None, None, None, 3
    # v47: dados da pessoa para o titulo respeitar a coluna livre / o rosto
    meta = {"tem_pessoa": False, "bbox": None, "em_pe": True}
    _mem("inicio do estilo pessoa")

    cor_parede, cor_piso = M.MARINHO, M.PETROLEO

    # 1) Baixar 1 foto do Ronilson e tentar recortar (até 3 tentativas com fotos diferentes)
    for n in range(1, tentativas + 1):
        _ETAPA["v"] = f"buscar foto do Ronilson (tentativa {n}/{tentativas})"
        try:
            url, info = _buscar_foto_ronilson()
        except Exception as e:
            ultimo_erro = f"busca Cloudinary: {type(e).__name__}: {e}"
            print(f"[estilo] tentativa {n}: {ultimo_erro}")
            url, info = None, ultimo_erro
        if not url:
            continue
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
            ultimo_erro = f"download da foto: {type(e).__name__}: {e}"
            print(f"[estilo] tentativa {n}: {ultimo_erro}")
            continue
        _ETAPA["v"] = f"recortar a pessoa (tentativa {n}/{tentativas})"
        try:
            rgba = _recortar_pessoa_leve(img)
        except Exception as e:
            ultimo_erro = f"recorte: {type(e).__name__}: {e}"
            print(f"[estilo] tentativa {n}: {ultimo_erro}")
            rgba = None
        if rgba is None:
            ultimo_erro = ultimo_erro or "o recorte nao achou uma pessoa nessa foto"
            print(f"[estilo] tentativa {n}: {ultimo_erro}")
            continue
        try:
            if hasattr(M, "_avaliar_silhueta_pessoa") and not M._avaliar_silhueta_pessoa(rgba):
                print(f"[estilo] tentativa {n}: silhueta ruim — mantendo ultima mesmo assim")
        except Exception:
            pass
        break

    # 2) Gerar FUNDO — PROCEDURAL primeiro para Showcase/Cinematic, IA só opcional
    _ETAPA["v"] = "montar fundo do estilo"
    aviso = None
    if estilo in ("cinematic", "showcase"):
        # v51: com a pessoa recortada, o fundo e criado em _compor_pessoa_estilo (so depois
        # de saber onde ela fica). Sem recorte (blend), usa o fundo v51 com foco padrao.
        fundo = None
        if rgba is None:
            _foco = (int(M.W * 0.68), int(M.H * 0.30))
            _criar = _fundo_cinematic_v2 if estilo == "cinematic" else _fundo_showcase_v2
            fundo = _criar(cor_parede, cor_piso, seed, _foco)
            print(f"[estilo] fundo {estilo.upper()} v51 pronto (sem IA)")
    else:
        # Outros estilos pessoa (futuros): tenta IA, cai em gradiente
        fundo, motivo = _gerar_imagem_ia(_prompt(estilo, True))
        if fundo is None:
            fundo = M._gerar_fundo_gradiente(cor_parede, cor_piso, seed)
            aviso = f"O fundo por IA falhou ({motivo}); usei o gradiente da paleta."

    # 3) Compor pessoa sobre fundo
    _ETAPA["v"] = "compor pessoa sobre o fundo"
    if rgba is not None:
        try:
            composto = None
            if estilo in ("cinematic", "showcase"):
                try:
                    composto, _bbox = _compor_pessoa_estilo(rgba, estilo, seed)
                    print(f"[estilo] composicao profissional v51 ok ({estilo})")
                    _mem("depois da composicao v51")
                except Exception as e_v51:
                    print(f"[estilo] composicao v51 falhou ({type(e_v51).__name__}: {e_v51}) — usando a anterior")
                    composto = None
            if composto is None:
                if fundo is None:
                    _fb = _fundo_cinematic_procedural if estilo == "cinematic" else _fundo_showcase_procedural
                    fundo = _fb(cor_parede, cor_piso, seed)
                composto, _bbox = _compor_pessoa_safe(rgba, fundo, estilo, seed)
            meta["bbox"] = _bbox
        except Exception as e:
            print(f"[estilo] composicao falhou inesperadamente: {e} — fallback colagem simples")
            fundo2 = fundo.convert("RGBA")
            try:
                pw, ph = rgba.size
                nw = max(1, int(pw * M.H / ph))
                rgba_r = rgba.resize((nw, M.H), Image.Resampling.LANCZOS)
                x = max(int(M.W * 0.35), min(M.W - nw + 50, M.W - 120))
                fundo2.paste(rgba_r, (x, 0), rgba_r)
            except Exception as e2:
                print(f"[estilo] colagem simples tambem falhou: {e2} — usando blend")
                fundo2 = Image.blend(fundo, img_original or fundo, 0.90)
            composto = fundo2.convert("RGB")
            aviso = (aviso + " " if aviso else "") + f"Composicao manual (erro: {e})."
    else:
        # NENHUM recorte deu certo — blend suave SEMPRE funciona
        if img_original is None:
            # Nenhuma foto baixou também — retorna só o fundo (melhor que 500)
            print("[estilo] nenhuma foto baixou — usando só fundo procedural")
            composto = fundo
            aviso = (aviso + " " if aviso else "") + (
                f"Nenhuma foto do Ronilson disponivel ({ultimo_erro or 'erro de busca'}); "
                "card com apenas o fundo do estilo.")
        else:
            print("[estilo] recorte falhou em todas as tentativas — blend suave sobre fundo procedural")
            # Blend suave: fundo + foto com opacidade 0.90. A foto mantém 100% nítida,
            # só as bordas se misturam suavemente.
            overlay = fundo.copy()
            arr_fundo = np.array(overlay, dtype=np.float32)
            arr_foto = np.array(img_original, dtype=np.float32)
            # Vinheta de transição: centro = foto (92%), bordas = mais fundo
            ys, xs = np.ogrid[:M.H, :M.W]
            cx, cy = M.W * 0.65, M.H * 0.5
            d = ((xs - cx) / (M.W * 0.42))**2 + ((ys - cy) / (M.H * 0.50))**2
            vinheta = np.clip(1.0 - (d ** 1.2) * 0.8, 0.15, 1.0)
            v3 = vinheta[:, :, None]
            arr_out = np.clip(arr_foto * v3 * 0.92 + arr_fundo * (1 - v3 * 0.92), 0, 255).astype(np.uint8)
            composto = Image.fromarray(arr_out)
            aviso = (aviso + " " if aviso else "") + (
                f"Nao consegui recortar nenhuma das {tentativas} fotos "
                f"({ultimo_erro or 'recorte vazio'}); fiz uma composicao suave "
                "da foto sobre o fundo do estilo.")

    # v47: fecha os dados da pessoa (o titulo usa coluna esquerda livre + protecao do rosto)
    meta["tem_pessoa"] = (rgba is not None) or (img_original is not None)
    if meta["tem_pessoa"]:
        try:
            if rgba is not None:
                meta["em_pe"] = bool(M._detectar_pose_em_pe(rgba))
        except Exception as e:
            print(f"[estilo] pose: {e}")
        try:
            _bb = M._detectar_rosto(composto)
            if _bb:
                meta["bbox"] = _bb
        except Exception as e:
            print(f"[estilo] rosto: {e}")
        if not meta["bbox"]:
            meta["bbox"] = (int(M.W * 0.35), int(M.H * 0.05), M.W, int(M.H * 0.55))

    # 4) Tratamento FINAL do estilo (color grade, vinheta, grão) — nunca falha
    try:
        composto = _aplicar_tratamento_estilo(composto, estilo, seed)
    except Exception as e:
        print(f"[estilo] tratamento final pulado: {e}")

    # 5) Nitidez final (se não tiver sido aplicado já)
    try:
        composto = ImageEnhance.Sharpness(composto).enhance(1.05)
        composto = ImageEnhance.Contrast(composto).enhance(1.02)
    except Exception:
        pass

    return composto, aviso, meta


def _card_pessoa(tema, base, seed, meta):
    """v47: titulo para Showcase/Cinematic SEM passar pelo gerar_card_imagem.
    Antes, o card ia por um URL temporario cujo nome nao tem 'ronilson', entao
    tem_pessoa=False: o titulo ocupava a largura toda (cruzando a pessoa) e
    ainda recebia um segundo color grade editorial por cima do estilo. Aqui o
    desenhar_titulo recebe tem_pessoa/em_pe/cabeca_bbox reais, como no fluxo
    normal do Ronilson, e a imagem do estilo segue intacta."""
    M = _m()
    seed = M._seed_variavel(tema, seed)
    cor_dest, cor_fundo_txt = M._escolher_cor_destaque(seed)
    tem = bool(meta.get("tem_pessoa"))
    img, _ = M.desenhar_titulo(
        base, tema, seed,
        cor_dest=cor_dest, cor_fundo_txt=cor_fundo_txt,
        cor_overlay=None,
        tem_pessoa=tem,
        em_pe=bool(meta.get("em_pe", True)),
        cabeca_bbox=meta.get("bbox") if tem else None)
    return img


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
        meta = None
        if ESTILOS[estilo]["tipo"] == "cena":
            base, aviso = _base_cena(estilo, seed)
        else:
            base, aviso, meta = _base_pessoa(estilo, seed)

        if meta is not None:
            # v47: Showcase/Cinematic montam o titulo direto (sem upload temporario)
            _ETAPA["v"] = "montar o card (titulo/layout)"
            card = _card_pessoa(tema, base, seed, meta)
        else:
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
