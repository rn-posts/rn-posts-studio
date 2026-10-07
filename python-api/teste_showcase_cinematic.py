"""
Teste LOCAL (sem servidor) dos estilos Showcase e Cinematic.
Roda APENAS os fundos procedural + tratamento final — NÃO precisa de:
   - Flask rodando
   - Cloudinary (não sobe nada, só salva em arquivo local)
   - Gemini / IA de imagem
   - rembg (não recorta pessoa, mostra só o fundo + tratamento)

Como usar:
    cd python-api
    py teste_showcase_cinematic.py

Os arquivos serão salvos em python-api/teste_*.png
"""
import os, sys, random, io, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import numpy as np
from PIL import Image, ImageEnhance, ImageFilter, ImageDraw

# --- Importa estilos_card e configura MÓDULO FAKE (main.py) ---------------
# Como não rodamos Flask/main.py, o _m() de estilos_card busca por sys.modules["main"].
# Criamos um módulo "main" falso só com as constantes que estilos_card realmente usa
# (W, H, MARINHO, PETROLEO etc) — nada do resto.

W, H = 1080, 1350
MARINHO  = (2,   64,  89)
PETROLEO = (27,  121, 125)
TEAL     = (4,   157, 191)
VERDE_NEUTRO = (119, 153, 147)
BRANCO   = (244, 246, 248)
LARANJA  = (249, 171, 11)

fake_main = type(sys)("main")
fake_main.W, fake_main.H = W, H
fake_main.MARINHO, fake_main.PETROLEO = MARINHO, PETROLEO
fake_main.TEAL, fake_main.BRANCO = TEAL, BRANCO
fake_main.VERDE_NEUTRO = VERDE_NEUTRO
fake_main.LARANJA = LARANJA

# Funções que estilos_card pode chamar via M.xxx (todas têm fallback seguro no código novo,
# mas garantimos existência)
def _f_g_gradiente(cor1, cor2, seed):
    rng = random.Random(seed)
    arr = np.zeros((H, W, 3), dtype=np.float32)
    for y in range(H):
        t = y / H
        for ch in range(3):
            arr[y, :, ch] = cor1[ch] * (1 - t) + cor2[ch] * t
    cx = W * rng.uniform(0.30, 0.70); cy = H * rng.uniform(0.10, 0.35)
    ys, xs = np.ogrid[:H, :W]
    dist2 = ((xs - cx) / (W * 0.55))**2 + ((ys - cy) / (H * 0.45))**2
    luz = np.exp(-dist2 * 1.2) * rng.uniform(20, 35)
    arr[:, :, 0] = np.clip(arr[:, :, 0] + luz,       0, 255)
    arr[:, :, 1] = np.clip(arr[:, :, 1] + luz * 0.8, 0, 255)
    arr[:, :, 2] = np.clip(arr[:, :, 2] + luz * 0.6, 0, 255)
    ruido = np.random.RandomState(seed).normal(0, 4, (H, W, 3))
    arr = np.clip(arr + ruido, 0, 255).astype(np.uint8)
    return Image.fromarray(arr).filter(ImageFilter.GaussianBlur(1))

fake_main._gerar_fundo_gradiente = _f_g_gradiente
sys.modules["main"] = fake_main

# --- Agora importa estilos_card (vai achar o "main" falso no sys.modules) ---
import estilos_card as ec

# --- Títulos aleatórios para geração de seed variada -----------------------
TITULOS_TESTE = [
    "É possível :ser feliz tendo -depressão?",
    "O silêncio que :não deixa em paz -ansiedade",
    "Primeiro passo :para recomeçar -terapia",
    "Quando cansar :de ser forte -acolhimento",
    "A cura começa :onde a dor fala -burnout",
    "Pequenos passos :grandes mudanças -recomeço",
]

def titulo_aleatorio():
    return random.choice(TITULOS_TESTE)

def salvar(img, nome):
    caminho = os.path.join(os.path.dirname(__file__), nome)
    img.convert("RGB").save(caminho, format="PNG")
    print(f"  [OK] salvo -> {caminho}")
    return caminho

# --- RODA OS DOIS ESTILOS --------------------------------------------------
def rodar_teste():
    print("=" * 70)
    print("TESTE LOCAL: Showcase e Cinematic (fundos procedural + tratamento final)")
    print("=" * 70)

    t0 = time.time()
    erros = 0

    for estilo_nome, fn_fundo in [
        ("SHOWCASE", ec._fundo_showcase_procedural),
        ("CINEMATIC", ec._fundo_cinematic_procedural),
    ]:
        titulo = titulo_aleatorio()
        seed = hash(titulo) % (2**30) + random.randint(0, 99999)
        print(f"\n▶ {estilo_nome} — título: '{titulo}' | seed={seed}")
        try:
            t1 = time.time()
            fundo = fn_fundo(MARINHO, PETROLEO, seed)
            print(f"   fundo procedural OK ({time.time()-t1:.2f}s), tamanho: {fundo.size}")
            assert fundo.size == (W, H), f"tamanho errado: {fundo.size}"

            # Simula pessoa com um retângulo simbólico para testar tratamento
            print("   simulando pessoa-simbolo (sem rembg) para testar tratamento final completo...")
            fundo_rgba = fundo.convert("RGBA")
            x, y, wp, hp = int(W*0.55), int(H*0.10), int(W*0.42), int(H*0.88)
            pessoa_sim = Image.new("RGBA", (wp, hp), (180, 160, 140, 255))
            # Desenha uma "cabeça" e "corpo" nesse retângulo para testar rim light e sombra
            d = ImageDraw.Draw(pessoa_sim)
            c_y = int(hp * 0.22)
            c_r = int(wp * 0.20)
            d.ellipse([wp//2 - c_r, c_y - c_r, wp//2 + c_r, c_y + c_r], fill=(200, 175, 150))
            fundo_rgba.paste(pessoa_sim, (x, y), pessoa_sim)
            fundo_com_pessoa = fundo_rgba.convert("RGB")

            # Aplica tratamento final do estilo
            t2 = time.time()
            final = ec._aplicar_tratamento_estilo(fundo_com_pessoa, estilo_nome.lower(), seed)
            print(f"   tratamento final OK ({time.time()-t2:.2f}s)")

            # Salva: fundo limpo E fundo+tratamento (para comparar)
            nome_sujo = estilo_nome.lower()
            salvar(fundo, f"teste_{nome_sujo}_1_fundo_PROCEDURAL.png")
            salvar(final, f"teste_{nome_sujo}_2_TRATADO_com_pessoa_simbolo.png")
            print(f"   ✅ {estilo_nome} PASSOU")

        except Exception as e:
            erros += 1
            import traceback
            print(f"   ❌ {estilo_nome} DEU ERRO: {type(e).__name__}: {e}")
            traceback.print_exc()

    print("\n" + "=" * 70)
    print(f"Tempo total: {time.time()-t0:.2f}s | Erros: {erros}")
    print("=" * 70)
    return erros == 0

if __name__ == "__main__":
    ok = rodar_teste()
    sys.exit(0 if ok else 1)
