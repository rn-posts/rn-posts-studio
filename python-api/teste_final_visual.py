"""
python-api/teste_final_visual.py
=================================
GERA CARDS COMPLETOS (fundo procedural + texto do título) com o
MOTOR IDÊNTICO ao estilos_card.py + estilos de texto do main.py.

NÃO usa: rembg, Cloudinary, Gemini, Flask, ou qualquer coisa de rede.
SÓ roda PIL + numpy + as fontes reais da pasta fonts/ (AGILERA.OTF, MALGUN.TTF).
Usa os ALGORITMOS idênticos do estilos_card.py para fundo e tratamento.

Saída: 2 PNGs em python-api/output_cards_TESTE/:
  1) card_SHOWCASE_{seed}.png  —  card completo (1080x1350)
  2) card_CINEMATIC_{seed}.png —  card completo (1080x1350)

Como rodar:
  D:/Users/Gleice/AppData/Local/Python/bin/python.exe teste_final_visual.py
"""
import os, sys, random, time, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import numpy as np
from PIL import Image, ImageEnhance, ImageFilter, ImageDraw, ImageFont

# --- CONSTANTES (iguais ao main.py) ---
W, H = 1080, 1350
MARINHO  = (2,   64,  89)
PETROLEO = (27, 121, 125)
TEAL     = (4, 157, 191)
SAGE     = (119, 153, 147)
BRANCO   = (244, 246, 248)
LARANJA  = (249, 171, 11)

ROOT = os.path.dirname(os.path.abspath(__file__))
FONTS_DIR = os.path.join(ROOT, "fonts")

# --- Fontes ---
def carregar_fonte(nome_arquivo, tamanho):
    caminho = os.path.join(FONTS_DIR, nome_arquivo)
    if os.path.isfile(caminho):
        try:
            return ImageFont.truetype(caminho, tamanho)
        except Exception:
            pass
    return ImageFont.load_default()

# =========================================================================
# COPIA LITERAL (1:1) DAS FUNÇÕES DO estilos_card.py QUE FORAM ALTERADAS
# =========================================================================
def _fundo_cinematic_procedural(cor1, cor2, seed):
    rng = random.Random(seed)
    arr = np.zeros((H, W, 3), dtype=np.float32)
    for y in range(H):
        for x in range(W):
            ty = y / H
            tx = x / W
            t = ty * 0.75 + tx * 0.25
            for ch in range(3):
                arr[y, x, ch] = cor1[ch] * (1 - t) + cor2[ch] * t
    ys, xs = np.ogrid[:H, :W]
    cores_bokeh = [LARANJA, BRANCO, PETROLEO, SAGE]
    n_bokeh = 28 + (seed % 12)
    for i in range(n_bokeh):
        cor = cores_bokeh[i % len(cores_bokeh)]
        cx = rng.uniform(0.05, 0.95) * W
        cy = rng.uniform(0.05, 0.90) * H
        raio_x = rng.uniform(18, 120) * (rng.uniform(0.4, 1.0))
        raio_y = raio_x * rng.uniform(0.25, 0.55)
        intensidade = rng.uniform(0.12, 0.55)
        dx = (xs - cx) / raio_x
        dy = (ys - cy) / raio_y
        d2 = dx*dx + dy*dy
        masc = np.exp(-d2 * 2.0) * intensidade
        for ch in range(3):
            arr[:, :, ch] = np.clip(arr[:, :, ch] + masc * cor[ch], 0, 255)
    cx_fim = W * rng.uniform(0.35, 0.55)
    cy_fim = H * rng.uniform(0.45, 0.65)
    cx_ini = W * rng.uniform(0.82, 0.96)
    cy_ini = H * rng.uniform(-0.05, 0.08)
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
    cor_feixe_arr = np.array([249 * 0.6, 200 * 0.6, 100 * 0.6], dtype=np.float32)
    for ch in range(3):
        arr[:, :, ch] += masc_feixe * intens_feixe * cor_feixe_arr[ch]
    t_nevoa = np.clip((ys - H*0.55) / (H*0.45), 0, 1)
    for ch in range(3):
        arr[:, :, ch] = np.clip(arr[:, :, ch] * (1 - t_nevoa * 0.45) + 244 * t_nevoa * 0.45, 0, 255)
    ruido = np.random.RandomState(seed).normal(0, 2.2, (H, W))
    arr[:, :, 0] = np.clip(arr[:, :, 0] + ruido, 0, 255)
    arr[:, :, 1] = np.clip(arr[:, :, 1] + ruido * 0.9, 0, 255)
    arr[:, :, 2] = np.clip(arr[:, :, 2] + ruido * 0.8, 0, 255)
    arr = np.clip(arr, 0, 255).astype(np.uint8)
    return Image.fromarray(arr).filter(ImageFilter.GaussianBlur(0.4))

def _fundo_showcase_procedural(cor1, cor2, seed):
    rng = random.Random(seed)
    arr = np.zeros((H, W, 3), dtype=np.float32)
    ys, xs = np.ogrid[:H, :W]
    horizonte_y = H * rng.uniform(0.58, 0.65)
    curvatura = (xs - W*0.5)**2 / (W**2) * H * rng.uniform(0.08, 0.14)
    y_parede = np.clip((ys - (horizonte_y - curvatura)) / (H - horizonte_y), 0, 1)
    for ch in range(3):
        arr[:, :, ch] = cor1[ch] * (1 - y_parede) + cor2[ch] * y_parede
    t_parede = np.clip(ys / horizonte_y, 0, 1)
    for ch in range(3):
        arr[:, :, ch] *= (0.85 + 0.15 * t_parede)
    cx_k = W * rng.uniform(0.15, 0.28)
    cy_k = H * rng.uniform(0.06, 0.14)
    r_k = max(W, H) * 0.7
    d2k = ((xs - cx_k)/r_k)**2 + ((ys - cy_k)/r_k)**2
    keylight = np.exp(-d2k * 1.5) * 0.32
    cor_k = np.array([249 * 0.9, 205 * 0.9, 130 * 0.9], dtype=np.float32)
    for ch in range(3):
        arr[:, :, ch] = np.clip(arr[:, :, ch] + keylight * cor_k[ch], 0, 255)
    cx_f = W * rng.uniform(0.80, 0.92)
    cy_f = H * rng.uniform(0.45, 0.58)
    r_f = max(W, H) * rng.uniform(0.55, 0.75)
    d2f = ((xs - cx_f)/r_f)**2 + ((ys - cy_f)/r_f)**2
    fill = np.exp(-d2f * 2.0) * 0.18
    cor_f = np.array([119 * 0.8, 153 * 0.8, 147 * 0.8], dtype=np.float32)
    for ch in range(3):
        arr[:, :, ch] = np.clip(arr[:, :, ch] + fill * cor_f[ch], 0, 255)
    masc_refl = (ys >= horizonte_y).astype(np.float32)
    if masc_refl.ndim == 3:
        masc_refl = masc_refl[:, :, 0]
    t_refl = np.clip((ys - horizonte_y) / (H * 0.28), 0, 1)
    if t_refl.ndim == 3:
        t_refl = t_refl[:, :, 0]
    intens_refl = (1 - t_refl) * 0.22 * masc_refl
    for ch in range(3):
        arr[:, :, ch] = np.clip(arr[:, :, ch] + intens_refl * 244, 0, 255)
    cx_s = W * rng.uniform(0.70, 0.82)
    cy_s = H * rng.uniform(0.78, 0.84)
    rx_s = W * 0.18
    ry_s = H * 0.06
    d2s = ((xs - cx_s)/rx_s)**2 + ((ys - cy_s)/ry_s)**2
    sombra = np.exp(-d2s * 2.5) * 0.25
    for ch in range(3):
        arr[:, :, ch] = np.clip(arr[:, :, ch] * (1 - sombra), 0, 255)
    ruido = np.random.RandomState(seed + 777).normal(0, 1.3, (H, W))
    arr[:, :, 0] = np.clip(arr[:, :, 0] + ruido, 0, 255)
    arr[:, :, 1] = np.clip(arr[:, :, 1] + ruido * 0.95, 0, 255)
    arr[:, :, 2] = np.clip(arr[:, :, 2] + ruido * 0.9, 0, 255)
    arr = np.clip(arr, 0, 255).astype(np.uint8)
    return Image.fromarray(arr).filter(ImageFilter.GaussianBlur(0.3))

def _color_grade_cinematic(img):
    arr = np.array(img.convert("RGB"), dtype=np.float32)
    lum = 0.299 * arr[:, :, 0] + 0.587 * arr[:, :, 1] + 0.114 * arr[:, :, 2]
    t_sombra = np.clip((160 - lum) / 160, 0, 1)
    t_realce = np.clip((lum - 130) / 125, 0, 1)
    sombra = np.array([-14, +4, +18], dtype=np.float32)
    realce = np.array([+14, +6, -8], dtype=np.float32)
    for ch in range(3):
        arr[:, :, ch] += t_sombra * sombra[ch] + t_realce * realce[ch]
    arr = arr / 255.0
    arr = np.where(arr < 0.5,
                   0.5 * (2 * arr) ** 1.15,
                   1 - 0.5 * (2 * (1 - arr)) ** 1.15)
    arr = np.clip(arr * 255, 0, 255).astype(np.uint8)
    out = Image.fromarray(arr)
    out = ImageEnhance.Color(out).enhance(0.94)
    return out

def _vinheta(img, intensidade=0.32):
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

def _aplicar_tratamento_estilo(img, estilo, seed):
    if estilo == "cinematic":
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

# =========================================================================
# RENDER DE TEXTO NO CARD (blocos como no main.py)
# =========================================================================
def parse_blocos(texto):
    """Cada linha do tema é um bloco com estilo próprio."""
    blocos = []
    for linha in texto.splitlines():
        if not linha.strip():
            continue
        estilo = "agilera"
        txt = linha
        if txt.startswith("*"):
            estilo = "agilera_estilizada"
            txt = txt[1:]
        elif txt.startswith(":"):
            estilo = "malgun"
            txt = txt[1:]
        elif txt.startswith("-"):
            estilo = "fundo_preenchido"
            txt = txt[1:]
        blocos.append((estilo, txt.strip()))
    return blocos

def desenhar_card(tema, fundo_img, seed):
    """Desenha o título do card sobre o fundo, com o mesmo layout da plataforma.
    Zona de texto: esquerda 45%, vertical centralizada, com proteção contra
    queda em áreas muito escuras. Usa as fontes reais da pasta fonts/."""
    card = fundo_img.convert("RGB").copy()
    draw = ImageDraw.Draw(card, "RGBA")

    blocos = parse_blocos(tema)
    if not blocos:
        return card

    # Medir tamanhos de fonte para caber no espaço
    max_largura_texto = int(W * 0.42)
    y_min = int(H * 0.18)
    y_max = int(H * 0.85)
    area_altura = y_max - y_min

    # Calcular tamanho base por número de blocos
    n_blocos = len(blocos)
    tam_titulo_n = max(52, min(88, int(area_altura / (n_blocos * 1.35))))
    tam_corpo_n  = max(36, min(54, int(area_altura / (n_blocos * 1.80))))

    # Render blocos com ajuste automático
    def renderizar_blocos(fator=1.0):
        lines = []
        total_h = 0
        for i, (estilo, txt) in enumerate(blocos):
            if not txt:
                continue
            if estilo == "agilera_estilizada":
                tam = int(tam_titulo_n * 1.08 * fator)
                font = carregar_fonte("AGILERA.OTF", tam)
                cor_texto = LARANJA
                stroke = 0
            elif estilo == "agilera":
                tam = int(tam_titulo_n * fator)
                font = carregar_fonte("AGILERA.OTF", tam)
                cor_texto = BRANCO
                stroke = 0
            elif estilo == "malgun":
                tam = int(tam_corpo_n * fator)
                font = carregar_fonte("MALGUN.TTF", tam)
                cor_texto = BRANCO
                stroke = 0
            else:  # fundo_preenchido (barra marinho)
                tam = int(tam_corpo_n * 0.95 * fator)
                font = carregar_fonte("MALGUN.TTF", tam)
                cor_texto = LARANJA
                stroke = 0
            # Largura da linha
            try:
                bbox = draw.textbbox((0,0), txt, font=font, stroke_width=stroke)
                lw = bbox[2] - bbox[0]
                lh = bbox[3] - bbox[1]
            except Exception:
                lw, lh = len(txt) * tam * 0.55, tam * 1.2
            # Wrap se estourar largura
            if lw > max_largura_texto and len(txt.split()) > 1:
                palavras = txt.split()
                linha_atual = ""
                sub_linhas = []
                for p in palavras:
                    teste = (linha_atual + " " + p).strip()
                    try:
                        bb = draw.textbbox((0,0), teste, font=font)
                        tl = bb[2] - bb[0]
                    except Exception:
                        tl = len(teste)*tam*0.55
                    if tl <= max_largura_texto:
                        linha_atual = teste
                    else:
                        if linha_atual:
                            sub_linhas.append(linha_atual)
                        linha_atual = p
                if linha_atual:
                    sub_linhas.append(linha_atual)
                for sl in sub_linhas:
                    lines.append((estilo, sl, tam, font, cor_texto, stroke, lh))
                    total_h += int(lh * 1.18)
            else:
                lines.append((estilo, txt, tam, font, cor_texto, stroke, lh))
                total_h += int(lh * 1.18)
        return lines, total_h

    # Ajustar fator para caber
    fator = 1.0
    for _ in range(8):
        lines, th = renderizar_blocos(fator)
        if th <= area_altura * 0.98:
            break
        fator *= 0.92
    else:
        lines, th = renderizar_blocos(fator)

    # Scrim suave atrás da zona do texto (contraste garantido — igual ao main)
    x_left_pad = int(W * 0.05)
    scrim_x0 = x_left_pad - 20
    scrim_x1 = max_largura_texto + x_left_pad + 30
    # Centro vertical
    y_total = th
    start_y = y_min + max(0, (area_altura - y_total) // 2)

    # Sombreado (scrim) suave radial atrás do texto (não um retângulo duro)
    scrim_layer = Image.new("RGBA", (W, H), (0,0,0,0))
    sc_d = ImageDraw.Draw(scrim_layer)
    cx_s = (scrim_x0 + scrim_x1) // 2
    cy_s = start_y + y_total // 2
    rx_s = (scrim_x1 - scrim_x0) // 2 + 40
    ry_s = y_total // 2 + 60
    ys_arr, xs_arr = np.ogrid[:H, :W]
    d2 = ((xs_arr - cx_s)/rx_s)**2 + ((ys_arr - cy_s)/ry_s)**2
    masc_sc = np.exp(-d2 * 1.8) * 0.55
    sc_arr = np.zeros((H, W, 4), dtype=np.uint8)
    sc_arr[:, :, 0] = (MARINHO[0] * masc_sc).astype(np.uint8)
    sc_arr[:, :, 1] = (MARINHO[1] * masc_sc).astype(np.uint8)
    sc_arr[:, :, 2] = (MARINHO[2] * masc_sc).astype(np.uint8)
    sc_arr[:, :, 3] = (255 * masc_sc).astype(np.uint8)
    scrim_layer = Image.fromarray(sc_arr, mode="RGBA").filter(ImageFilter.GaussianBlur(22))
    card_rgba = card.convert("RGBA")
    card_rgba = Image.alpha_composite(card_rgba, scrim_layer)
    card = card_rgba.convert("RGB")
    draw = ImageDraw.Draw(card, "RGBA")

    # Desenhar blocos de texto
    y = start_y
    for (estilo, txt, tam, font, cor_texto, stroke, lh) in lines:
        if estilo == "fundo_preenchido":
            try:
                bb = draw.textbbox((x_left_pad, y), txt, font=font, stroke_width=stroke)
                pad_x, pad_y = int(tam * 0.28), int(tam * 0.22)
                box = (bb[0]-pad_x, bb[1]-pad_y, bb[2]+pad_x, bb[3]+pad_y)
                # cantos arredondados
                r = int(tam * 0.18)
                draw.rounded_rectangle(box, radius=r, fill=MARINHO + (235,))
                # sombra padrão para legibilidade
                draw.text((x_left_pad+3, y+3), txt, font=font, fill=(0,0,0,90), stroke_width=stroke)
                draw.text((x_left_pad, y), txt, font=font, fill=cor_texto, stroke_width=stroke)
            except Exception as e:
                draw.text((x_left_pad, y), txt, font=font, fill=cor_texto)
        else:
            # Sombra padrão (sutil)
            draw.text((x_left_pad+3, y+4), txt, font=font, fill=(0,0,0,120), stroke_width=stroke)
            draw.text((x_left_pad, y), txt, font=font, fill=cor_texto, stroke_width=stroke)
        y += int(lh * 1.18)

    # Logo / rodapé AlvoreSer (discreto, inferior esquerdo)
    try:
        logo_font = carregar_fonte("AGILERA.OTF", 34)
        logo_text = "AlvoreSer"
        cor_logo = (244, 246, 248, 210)
        draw.text((x_left_pad, int(H * 0.92)), logo_text, font=logo_font, fill=cor_logo)
        sub_font = carregar_fonte("MALGUNSL.TTF", 22)
        draw.text((x_left_pad, int(H * 0.92) + 36),
                  "Clínica de Psicologia · CRP 04/57327",
                  font=sub_font, fill=(244, 246, 248, 170))
    except Exception:
        pass

    # Rodapé semente (opcional, debug)
    try:
        mini = carregar_fonte("MALGUNSL.TTF", 16)
        draw.text((int(W * 0.78), int(H * 0.965)), f"seed {seed}",
                  font=mini, fill=(244,246,248,110))
    except Exception:
        pass

    return card


# =========================================================================
# RODAR OS DOIS ESTILOS
# =========================================================================
def main():
    TEMA_TESTE = "*É possível\n:ser feliz tendo\n-depressão?"
    seed = random.randint(10000, 9999999)
    print(f"Tema: {TEMA_TESTE!r}\nSeed: {seed}\n")
    output_dir = os.path.join(ROOT, "output_cards_TESTE")
    os.makedirs(output_dir, exist_ok=True)
    print(f"Arquivos em: {output_dir}\n")

    t0 = time.time()
    for estilo, fn_fundo in [
        ("showcase", _fundo_showcase_procedural),
        ("cinematic", _fundo_cinematic_procedural),
    ]:
        t1 = time.time()
        # 1) Fundo procedural
        fundo = fn_fundo(MARINHO, PETROLEO, seed)
        print(f"[{estilo.upper()}] fundo procedural pronto ({time.time()-t1:.2f}s)")
        # 2) Tratamento final DO FUNDO (passar pelo pipeline de tratamento também)
        fundo_tratado = _aplicar_tratamento_estilo(fundo, estilo, seed)
        print(f"[{estilo.upper()}] tratamento de cor + vinheta + grão aplicado")
        # 3) Desenhar texto do card sobre o fundo tratado
        t2 = time.time()
        card = desenhar_card(TEMA_TESTE, fundo_tratado, seed)
        print(f"[{estilo.upper()}] texto renderizado no card ({time.time()-t2:.2f}s)")
        # 4) Nitidez final
        card = ImageEnhance.Sharpness(card).enhance(1.04)
        # 5) Salvar
        arq = os.path.join(output_dir, f"card_{estilo.upper()}_{seed}.png")
        card.save(arq, format="PNG", optimize=True)
        print(f"[{estilo.upper()}] SALVO -> {arq} ({time.time()-t1:.2f}s total)\n")

    print(f"\nPRONTO! Tudo salvo em {output_dir}  |  total {time.time()-t0:.2f}s")
    print("Abra a pasta e confira os dois PNGs.")

if __name__ == "__main__":
    main()
