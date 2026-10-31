"""
python-api/integracao_v74.py  —  v74  —  melhor integração do Ronilson no cenário

  • sombra_projetada(): sombra achatada no chão, na direção oposta à luz da cena (o corpo inteiro só tinha
    sombra de contato nos pés, por isso "flutuava");
  • pose_suspeita(): descarta recortes sentados / com cadeira / com pernas cruzadas pela GEOMETRIA do alpha
    (a classificação por visão do Gemini falha em silêncio e deixava passar foto com cadeira).
"""
import numpy as np


def sombra_projetada(a_f, base_y, luz_x, lum):
    """Máscara 0..1 (H, W) da sombra no chão. luz_x < 0: luz vem da esquerda (sombra para a direita).
    Luz por trás (parte mais clara do cenário no alto) -> a sombra vem em direção ao espectador."""
    import cv2
    H, W = a_f.shape
    sil = (a_f > 0.5).astype(np.float32)
    if float(sil.sum()) < 200:
        return np.zeros((H, W), np.float32)
    thr = float(np.percentile(lum, 92))
    yy, _ = np.where(lum >= thr)
    atras = bool(len(yy)) and float(yy.mean()) < 0.45 * H
    dx = -float(luz_x) * 0.38
    dy = 0.10 if atras else -0.05
    base_y = float(base_y)
    M = np.float32([[1, -dx, dx * base_y], [0, -dy, (1 + dy) * base_y]])
    sh = cv2.warpAffine(sil, M, (W, H), flags=cv2.INTER_LINEAR)
    sh = cv2.GaussianBlur(sh, (0, 0), 9)
    return np.clip(sh, 0, 1)


def pose_suspeita(img):
    """True se o recorte (RGBA) parece sentado/apoiado/com cadeira: não é corpo em pé (proporção < 2.2) e a base
    não é um corte reto de busto (cobertura baixa ou 3+ blocos separados nas últimas linhas)."""
    try:
        a = np.asarray(img.split()[3]) > 128
        ys, xs = np.where(a)
        if len(ys) == 0:
            return False
        a = a[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
        h, w = a.shape
        if h / float(max(w, 1)) >= 2.2:
            return False
        k = max(3, int(h * 0.04))
        cols = a[-k:].any(axis=0)
        cobertura = float(cols.mean())
        blocos, ant = 0, False
        for v in cols:
            if v and not ant:
                blocos += 1
            ant = bool(v)
        suspeita = cobertura < 0.45 or blocos >= 3
        if suspeita:
            print(f"[ronilson] geometria suspeita (sentado/cadeira): cobertura={cobertura:.2f} blocos={blocos}")
        return suspeita
    except Exception as e:
        print(f"[ronilson] pose_suspeita ignorada: {e}")
        return False
