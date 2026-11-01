"""
python-api/titulo_inteligente_v75.py  —  v75  —  posição do título mais inteligente

Problema: o título (esquerda, largura fixa) atravessava o rosto quando o Haar não detectava (perfil, silhueta escura,
rosto de IA) e quebrava cada linha do usuário em várias linhas.

limite_sujeito_x(): acha, por energia de bordas (luz de contorno, cabelo, rosto), o x onde começa o "sujeito" dentro
de uma faixa horizontal; devolve a largura da imagem se não achar nada (comportamento anterior).
penalidade_largura(): penaliza zonas onde sobra pouca largura livre para o texto (faz o título preferir o topo
livre / a região calma, em vez de espremer 3 linhas ao lado do rosto).
"""
import numpy as np


def limite_sujeito_x(img, y0, y1, x_min=260):
    """x (px) onde começa o sujeito na faixa y0..y1; largura da imagem se não houver sujeito claro."""
    try:
        import cv2
        arr = np.array(img.convert("L")).astype(np.float32)
        h, w = arr.shape
        y0, y1 = max(0, int(y0)), min(h, int(y1))
        if y1 - y0 < 20:
            return w
        zona = cv2.GaussianBlur(arr[y0:y1], (0, 0), 2.0)
        gx = cv2.Sobel(zona, cv2.CV_32F, 1, 0, ksize=3)
        gy = cv2.Sobel(zona, cv2.CV_32F, 0, 1, ksize=3)
        col = np.sqrt(gx * gx + gy * gy).mean(axis=0)
        col = cv2.GaussianBlur(col.reshape(1, -1), (0, 0), sigmaX=16).ravel()
        ref = float(np.percentile(col[: int(w * 0.30)], 70)) + 1.0
        limiar = max(ref * 2.4, float(col.max()) * 0.45)
        if float(col.max()) < limiar:
            return w
        for x in range(int(x_min), w - 40):
            if col[x] >= limiar and float(col[x:x + 30].mean()) >= limiar * 0.85:
                return int(x)
        return w
    except Exception as e:
        print(f"[titulo75] limite_sujeito_x falhou: {e}")
        return int(img.size[0])


def penalidade_largura(disponivel, largura_img):
    """0 quando há >= 60% da largura livre; sobe até 5 quando quase não há espaço."""
    return max(0.0, 1.0 - float(disponivel) / (0.60 * float(largura_img))) * 5.0
