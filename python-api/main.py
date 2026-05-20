"""
python-api/main.py — API Flask completa — Render
Identidade Visual AlvoreSer — 9 cores dominam tudo
Design de excelencia: desfoque seletivo, vinheta, profundidade, texturas, tipografia variada
"""
import os, io, uuid, random, json, textwrap, time, math
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
    "http://localhost:5173",
    "http://localhost:3000",
    "http://localhost:5000",
    "https://alvoreser-python-api.onrender.com"
]

CORS(app, origins=ALLOWED_ORIGINS, supports_credentials=True)

@app.after_request
def add_cors(response):
    origin = request.headers.get("Origin")
    if origin:
        if origin in ALLOWED_ORIGINS or "localhost" in origin or "onrender.com" in origin:
            response.headers["Access-Control-Allow-Origin"] = origin
    response.headers["Access-Control-Allow-Headers"] = "Content-Type,Authorization"
    response.headers["Access-Control-Allow-Methods"] = "GET,POST,OPTIONS"
    return response

@app.route("/")
def index():
    return app.send_static_file("index.html")

cloudinary.config(
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
    api_key=os.getenv("CLOUDINARY_API_KEY"),
    api_secret=os.getenv("CLOUDINARY_API_SECRET"),
)

SPREADSHEET_ID       = "12FT6CQQDNLI9G7KM8wSfHevAKAuRoEi4OsPYy1aH-8A"
SCOPES               = ["https://www.googleapis.com/auth/spreadsheets"]
SERVICE_ACCOUNT_JSON = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON")
GROQ_API_KEY         = os.getenv("GROQ_API_KEY")
GEMINI_API_KEY       = os.getenv("GEMINI_API_KEY")
GROQ_URL             = "https://api.groq.com/openai/v1/chat/completions"

W, H = 1080, 1350
CLOUDINARY_POSTS    = "AlvoreSer_Posts"
CLOUDINARY_PREVIEW  = "AlvoreSer_Preview"
PASTA_RONILSON      = "banco de imagens/ronilson"

SZ_TOP=135; SZ_BOTTOM=1215; SZ_LEFT=125; SZ_RIGHT=955

# 9 cores da identidade + preto/branco para texto
MARINHO=(2,64,89); PETROLEO=(27,121,125); TEAL=(4,157,191)
BRANCO=(244,246,248); LARANJA=(249,171,11); VERDE_NEUTRO=(119,153,147)
VERDE_VIVO=(122,181,0); VERDE_CITRICO=(146,204,29); AMARELO=(255,221,0)
PRETO=(20,20,20)

PALETA_9=[MARINHO,PETROLEO,TEAL,VERDE_NEUTRO,BRANCO,LARANJA,VERDE_VIVO,VERDE_CITRICO,AMARELO]

# Cache de cards pendentes de aprovacao {card_id: dados}
_cards_pendentes = {}

MAPA_PASTAS={
    "autismo":       "Banco de Imagens/Autismo",
    "ansiedade":     "Banco de Imagens/Ansiedade e Estresse",
    "estresse":      "Banco de Imagens/Ansiedade e Estresse",
    "burnout":       "Banco de Imagens/Ansiedade e Estresse",
    "depressao":     "Banco de Imagens/Depressão",
    "luto":          "Banco de Imagens/Depressão",
    "trauma":        "Banco de Imagens/Depressão",
    "borderline":    "Banco de Imagens/Borderline",
    "tdah":          "Banco de Imagens/TDAH",
    "terapia":       "Banco de Imagens/Convite e Terapia",
    "acolhimento":   "Banco de Imagens/Acolhimento",
    "familia":       "Banco de Imagens/Acolhimento",
    "relacionamento":"Banco de Imagens/Acolhimento",
    "recomeco":      "Banco de Imagens/Recomeço e Transformação",
    "transformacao": "Banco de Imagens/Recomeço e Transformação",
}

ROOT_DIR  = os.path.dirname(os.path.abspath(__file__))
FONTS_DIR = os.path.join(ROOT_DIR,"..","src","Brand","fonts")

def _font(nome,tam):
    try: return ImageFont.truetype(os.path.join(FONTS_DIR,nome),tam)
    except:
        try: return ImageFont.load_default(size=tam)
        except: return ImageFont.load_default()

def f_titulo(t): return _font("AGILERA.OTF",t)
def f_bold(t):   return _font("MALGUNBD.TTF",t)
def f_corpo(t):  return _font("MALGUN.TTF",t)
def f_light(t):  return _font("MALGUNSL.TTF",t)

ASSINATURA=(
    "\n\n\U0001f468\u200d\U0001f4bc Ronilson Nogueira\n"
    "\u270d\ufe0f Psic\u00f3logo e Professor\n"
    "\U0001f9e9 Refer\u00eancia em Autismo e TDAH\n"
    "CRP 04/57327"
)

PROMPT_LEGENDA=(
    "Crie uma legenda para um post do Instagram sobre: '{tema}'. "
    "Para o psicologo Ronilson Nogueira, especialista em Autismo e TDAH, "
    "da clinica AlvoreSer em Coronel Fabriciano/MG. "
    "Tom: acolhedor, humano, reflexivo, nao-clinico, para o publico geral. "
    "Maximo 150 palavras. NAO inclua hashtags. "
    "Retorne APENAS o texto da legenda, sem explicacoes ou markdown."
)
GROQ_MODELOS=["llama-3.3-70b-versatile","llama-3.1-8b-instant","llama-4-scout"]

def _groq_legenda(tema):
    if not GROQ_API_KEY: raise Exception("GROQ_API_KEY nao configurada")
    ultimo=None
    for m in GROQ_MODELOS:
        try:
            r=requests.post(GROQ_URL,
                headers={"Authorization":f"Bearer {GROQ_API_KEY}","Content-Type":"application/json"},
                json={"model":m,"messages":[{"role":"user","content":PROMPT_LEGENDA.format(tema=tema)}],"max_tokens":400},
                timeout=20)
            r.raise_for_status()
            return r.json()["choices"][0]["message"]["content"].strip()
        except Exception as e: ultimo=e
    raise Exception(f"Groq falhou: {ultimo}")

def _gemini_legenda(tema):
    if not GEMINI_API_KEY: raise Exception("GEMINI_API_KEY nao configurada")
    url=f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GEMINI_API_KEY}"
    r=requests.post(url,json={"contents":[{"parts":[{"text":PROMPT_LEGENDA.format(tema=tema)}]}]},timeout=25)
    if r.status_code==429: raise Exception("Gemini 429")
    r.raise_for_status()
    return r.json()["candidates"][0]["content"]["parts"][0]["text"].strip()

def gerar_legenda_ia(tema):
    erros=[]
    try: return _groq_legenda(tema)+ASSINATURA
    except Exception as e: erros.append(f"Groq:{e}")
    try: return _gemini_legenda(tema)+ASSINATURA
    except Exception as e: erros.append(f"Gemini:{e}")
    raise Exception("Todas as IAs falharam — "+" | ".join(erros))

def buscar_imagem(tema=""):
    """Busca imagem em qualquer pasta disponivel do banco.
    Tenta pasta tematica primeiro, depois qualquer pasta com imagens."""
    t = tema.lower()
    todas_pastas = list(set(MAPA_PASTAS.values()))

    # Pasta tematica primeiro
    pasta_tema = None
    for chave, pasta in MAPA_PASTAS.items():
        if chave in t:
            pasta_tema = pasta
            break

    if pasta_tema:
        todas_pastas = [pasta_tema] + [p for p in todas_pastas if p != pasta_tema]

    # Tenta cada pasta ate encontrar imagem
    for pasta in todas_pastas:
        try:
            res = cloudinary.api.resources(type="upload", prefix=pasta+"/", max_results=50)
            rec = [r for r in res.get("resources",[]) if CLOUDINARY_POSTS not in r.get("public_id","") and CLOUDINARY_PREVIEW not in r.get("public_id","")]
            if rec:
                c = random.choice(rec)
                print(f"[busca] encontrou em: {pasta}")
                return c.get("secure_url"), c.get("public_id","")
        except Exception as e:
            print(f"[busca] erro em {pasta}: {e}")
            continue

    # Fallback absoluto — qualquer imagem do Cloudinary
    try:
        res = cloudinary.api.resources(type="upload", max_results=50)
        rec = [r for r in res.get("resources",[]) if CLOUDINARY_POSTS not in r.get("public_id","") and CLOUDINARY_PREVIEW not in r.get("public_id","")]
        if rec:
            c = random.choice(rec)
            print(f"[busca] fallback absoluto: {c.get('public_id')}")
            return c.get("secure_url"), c.get("public_id","")
    except Exception as e:
        print(f"[busca] fallback absoluto erro: {e}")

    print("[busca] sem imagem")
    return None, ""

# ── Utilitarios de cor ────────────────────────────────────────────────────────
def distancia_cor(c1,c2): return ((c1[0]-c2[0])**2+(c1[1]-c2[1])**2+(c1[2]-c2[2])**2)**0.5

def luminosidade_regiao(img,y1,y2):
    y2=min(y2,img.size[1]); y1=max(y1,0)
    if y1>=y2: return 128
    p=list(img.crop((0,y1,W,y2)).convert("L").getdata())
    return sum(p)/len(p)

def cor_dominante_regiao(img,y,h):
    p=list(img.crop((0,y,W,min(y+h,img.size[1]))).resize((50,20),Image.Resampling.LANCZOS).convert("RGB").getdata())
    return (sum(x[0] for x in p)//len(p),sum(x[1] for x in p)//len(p),sum(x[2] for x in p)//len(p))

def cores_harmonicas_da_paleta(img):
    cf=cor_dominante_regiao(img,0,img.size[1])
    ordenadas=sorted(PALETA_9,key=lambda c:distancia_cor(cf,c),reverse=True)
    cor_principal=ordenadas[0]; cor_destaque=ordenadas[1]; cor_acento=ordenadas[2]
    for c in ordenadas[2:]:
        if distancia_cor(c,cor_principal)>80 and distancia_cor(c,cor_destaque)>80:
            cor_acento=c; break
    lum=sum(cf)/3
    if lum<60: cor_principal=BRANCO
    return cor_principal,cor_destaque,cor_acento

def complexidade_zona(arr,y1,y2):
    y2=min(y2,arr.shape[0]); y1=max(y1,0)
    if y1>=y2: return 999
    z=arr[y1:y2,:].astype(float)
    return (np.abs(np.diff(z,axis=0)).mean()+np.abs(np.diff(z,axis=1)).mean())/2

def melhor_posicao_titulo(img,altura_bloco):
    uh=SZ_BOTTOM-SZ_TOP
    zonas=[SZ_TOP+20,SZ_TOP+int(uh*0.25),SZ_TOP+int(uh*0.50)-altura_bloco//2,SZ_TOP+int(uh*0.65),SZ_BOTTOM-altura_bloco-20]
    arr=np.array(img.convert("L")); melhor=zonas[-1]; menor=float("inf"); terco=uh/3
    for y in zonas:
        if y<SZ_TOP or y+altura_bloco>SZ_BOTTOM: continue
        c=complexidade_zona(arr,y,y+altura_bloco)
        if y<SZ_TOP+terco or y>SZ_BOTTOM-terco-altura_bloco: c*=0.80
        if c<menor: menor=c; melhor=y
    return melhor

# ── Tecnicas de design de excelencia ─────────────────────────────────────────

def aplicar_vinheta(img, intensidade=0.55):
    """Vinheta fotografica profissional — escurece bordas criando profundidade e foco."""
    vinheta = Image.new("L", (W,H), 255)
    draw = ImageDraw.Draw(vinheta)
    cx,cy = W//2, H//2
    passos = 180
    for i in range(passos,0,-1):
        t = i/passos
        rx = int(cx * t * 1.05)
        ry = int(cy * t * 1.05)
        alpha = int(255 * (1 - (1-t)**1.8 * intensidade * 2.5))
        alpha = max(0,min(255,alpha))
        draw.ellipse([cx-rx,cy-ry,cx+rx,cy+ry],fill=alpha)
    vinheta = vinheta.filter(ImageFilter.GaussianBlur(60))
    r,g,b = img.split() if img.mode=="RGB" else img.convert("RGB").split()
    r=ImageChops.multiply(r,vinheta)
    g=ImageChops.multiply(g,vinheta)
    b=ImageChops.multiply(b,vinheta)
    return Image.merge("RGB",[r,g,b])

def aplicar_desfoque_profundidade(img, zona_foco_y, zona_foco_h, intensidade=2.5):
    """
    Simula profundidade de campo fotografica:
    - Zona de foco: nitida
    - Fora do foco: desfoque gaussiano progressivo
    Cria sensacao de camera profissional com abertura larga.
    """
    arr_original = np.array(img)
    img_desfocada = img.filter(ImageFilter.GaussianBlur(intensidade))
    arr_desfocado = np.array(img_desfocada)
    mask = np.zeros((H,W),dtype=np.float32)
    # Zona de foco nitida
    y1 = max(0,zona_foco_y)
    y2 = min(H,zona_foco_y+zona_foco_h)
    for y in range(H):
        if y1 <= y <= y2:
            mask[y,:] = 0.0
        elif y < y1:
            dist = (y1-y)/max(y1,1)
            mask[y,:] = min(1.0, dist*2.5)
        else:
            dist = (y-y2)/max(H-y2,1)
            mask[y,:] = min(1.0, dist*2.5)
    mask3 = np.stack([mask,mask,mask],axis=2)
    resultado = (arr_original*(1-mask3) + arr_desfocado*mask3).astype(np.uint8)
    return Image.fromarray(resultado)

def aplicar_perspectiva_leve(img, direcao="esquerda"):
    """
    Simula leve perspectiva/angulo de camera — da sensacao de movimento e tridimensionalidade.
    Usa transformacao de perspectiva manual com PIL.
    """
    src = img.convert("RGBA")
    if direcao == "esquerda":
        coef = 0.06
        dados = src.transform(
            (W,H), Image.Transform.QUAD,
            (int(W*coef),int(H*coef), W-int(W*coef),0, W,H, 0,H-int(H*coef)),
            Image.Resampling.BICUBIC
        )
    elif direcao == "direita":
        coef = 0.06
        dados = src.transform(
            (W,H), Image.Transform.QUAD,
            (0,0, W-int(W*coef),int(H*coef), W-int(W*coef),H-int(H*coef), int(W*coef),H),
            Image.Resampling.BICUBIC
        )
    else:
        return img
    return dados.convert("RGB")

def aplicar_contraste_dramatico(img, fator=1.25):
    """Aumenta contraste e saturacao para imagem mais impactante visualmente."""
    img = ImageEnhance.Contrast(img).enhance(fator)
    img = ImageEnhance.Color(img).enhance(1.15)
    img = ImageEnhance.Sharpness(img).enhance(1.3)
    return img

def aplicar_overlay_cromatico(img, cor, opacidade=40):
    """Overlay sutil de uma cor da paleta sobre a imagem — harmoniza com identidade visual."""
    overlay = Image.new("RGBA",(W,H),(*cor,opacidade))
    return Image.alpha_composite(img.convert("RGBA"),overlay).convert("RGB")

def aplicar_split_toning(img, cor_sombras, cor_luzes, intensidade=0.12):
    """
    Split toning fotografico profissional:
    - Sombras recebem tom frio (azul/petróleo)
    - Luzes recebem tom quente (laranja/amarelo)
    Cria coerencia cromatica sofisticada.
    """
    arr = np.array(img.convert("RGB")).astype(np.float32)
    lum = arr.mean(axis=2,keepdims=True)/255.0
    sombra = np.array(cor_sombras[:3],dtype=np.float32)
    luz    = np.array(cor_luzes[:3],  dtype=np.float32)
    mask_sombra = (1-lum)**2
    mask_luz    = lum**2
    arr += (sombra - arr) * mask_sombra * intensidade
    arr += (luz    - arr) * mask_luz    * intensidade
    arr  = np.clip(arr,0,255).astype(np.uint8)
    return Image.fromarray(arr)

def gerar_textura_organica(cor1, cor2, seed):
    """Fundo com textura organica — ondas suaves como no padrao AlvoreSer."""
    rng = random.Random(seed)
    base = Image.new("RGB",(W,H))
    draw = ImageDraw.Draw(base)
    for y in range(H):
        tv = y/H
        # Onda suave usando seno
        onda = math.sin(y/120 + rng.uniform(0,2*math.pi)) * 0.08
        tv2  = max(0,min(1,tv + onda))
        r = int(cor1[0]*(1-tv2)+cor2[0]*tv2)
        g = int(cor1[1]*(1-tv2)+cor2[1]*tv2)
        b = int(cor1[2]*(1-tv2)+cor2[2]*tv2)
        # Variacao horizontal sutil
        for x in range(0,W,4):
            onda_x = math.sin(x/180 + y/240) * 0.04
            r2 = max(0,min(255,int(r + onda_x*30)))
            g2 = max(0,min(255,int(g + onda_x*20)))
            b2 = max(0,min(255,int(b + onda_x*15)))
            draw.line([(x,y),(x+4,y)],fill=(r2,g2,b2))
    return base.filter(ImageFilter.GaussianBlur(1))

def eh_foto_ronilson(pid): return PASTA_RONILSON in pid.lower()

def eh_fundo_solido(img):
    s=img.resize((100,125),Image.Resampling.LANCZOS).convert("RGB")
    rv=[p[0] for p in s.getdata()]; m=sum(rv)/len(rv)
    var=sum((v-m)**2 for v in rv)/len(rv)
    lum=luminosidade_regiao(img,0,H)
    eh_claro=lum>190 and var<1500; eh_escuro=lum<40 and var<800
    print(f"[fundo] lum={lum:.1f} var={var:.1f} claro={eh_claro} escuro={eh_escuro}")
    return eh_claro or eh_escuro

def remover_fundo(img):
    buf=io.BytesIO(); img.save(buf,format="PNG")
    return Image.open(io.BytesIO(get_rembg()(buf.getvalue()))).convert("RGBA")

def compor_com_fundo(pessoa_rgba, fundo, cor_sombras, cor_luzes):
    """Compoe pessoa sem fundo sobre fundo da identidade com sombra projetada."""
    pw,ph=pessoa_rgba.size; nw=int(pw*H/ph)
    pessoa_rgba=pessoa_rgba.resize((nw,H),Image.Resampling.LANCZOS)
    # Sombra projetada sutil
    sombra = Image.new("RGBA",(W,H),(0,0,0,0))
    sombra_pessoa = Image.new("RGBA",(nw,H),(0,0,0,0))
    alpha = pessoa_rgba.split()[3]
    sombra_mask = alpha.point(lambda x: int(x*0.35))
    sombra_pessoa.paste(Image.new("RGB",(nw,H),(0,0,0)), mask=sombra_mask)
    sombra.paste(sombra_pessoa, ((W-nw)//2+18, 18), sombra_pessoa)
    sombra = sombra.filter(ImageFilter.GaussianBlur(22))
    res = fundo.convert("RGBA")
    res = Image.alpha_composite(res, sombra)
    res.paste(pessoa_rgba, ((W-nw)//2,0), pessoa_rgba)
    resultado = res.convert("RGB")
    # Split toning para coerencia cromatica
    resultado = aplicar_split_toning(resultado, cor_sombras, cor_luzes)
    return resultado

def preparar_fundo(url, pid="", cor1=MARINHO, cor2=PETROLEO, seed=0, tema=""):
    try:
        r=requests.get(url,timeout=20); r.raise_for_status()
        img=Image.open(io.BytesIO(r.content)).convert("RGB")
        ratio=max(W/img.width,H/img.height); nw,nh=int(img.width*ratio),int(img.height*ratio)
        img=img.resize((nw,nh),Image.Resampling.LANCZOS)
        l=(nw-W)//2; t=(nh-H)//2; img=img.crop((l,t,l+W,t+H))

        if eh_foto_ronilson(pid):
            print(f"[fundo] Ronilson: {pid}")
            try:
                # Fundo com textura organica da identidade
                fundo_idv = gerar_textura_organica(cor1,cor2,seed)
                pessoa_rgba = remover_fundo(img)
                img = compor_com_fundo(pessoa_rgba, fundo_idv, MARINHO, AMARELO)
                print("[fundo] rembg + composicao OK")
            except Exception as e: print(f"[fundo] rembg falhou: {e}")
        elif eh_fundo_solido(img):
            print("[fundo] solido, textura organica")
            fundo_idv = gerar_textura_organica(cor1,cor2,seed)
            img = Image.blend(fundo_idv.convert("RGBA"),img.convert("RGBA"),alpha=0.55).convert("RGB")
        else:
            print("[fundo] imagem normal")

        # Pipeline de tratamento fotografico profissional
        estilo_foto = seed % 4

        if estilo_foto == 0:
            # Profundidade de campo — foco no centro, desfoque top/base
            img = aplicar_desfoque_profundidade(img, H//3, H//3, intensidade=2.0)
            img = aplicar_contraste_dramatico(img, fator=1.2)
            img = aplicar_vinheta(img, intensidade=0.5)

        elif estilo_foto == 1:
            # Perspectiva leve + overlay cromatico
            direcao = "esquerda" if seed%2==0 else "direita"
            img = aplicar_perspectiva_leve(img, direcao)
            img = aplicar_overlay_cromatico(img, cor1, opacidade=35)
            img = aplicar_contraste_dramatico(img, fator=1.3)
            img = aplicar_vinheta(img, intensidade=0.6)

        elif estilo_foto == 2:
            # Split toning cinematografico + vinheta forte
            img = aplicar_split_toning(img, MARINHO, LARANJA, intensidade=0.15)
            img = aplicar_contraste_dramatico(img, fator=1.25)
            img = aplicar_vinheta(img, intensidade=0.65)

        else:
            # Overlay + profundidade + vinheta suave
            img = aplicar_overlay_cromatico(img, cor2, opacidade=25)
            img = aplicar_desfoque_profundidade(img, H//4, H//2, intensidade=1.8)
            img = aplicar_contraste_dramatico(img, fator=1.15)
            img = aplicar_vinheta(img, intensidade=0.45)

        return img
    except Exception as e: print(f"[fundo] erro: {e}"); return None

# ── Elementos graficos da identidade ─────────────────────────────────────────
def adicionar_elementos_brand(img, cor_acento, estilo):
    draw=ImageDraw.Draw(img,"RGBA"); e=estilo%6
    if e==0:
        for y in range(SZ_BOTTOM-280,H):
            a=int(150*(y-(SZ_BOTTOM-280))/max(1,H-(SZ_BOTTOM-280)))
            draw.line([(0,y),(W,y)],fill=(*MARINHO,min(a,150)))
    elif e==1:
        for x in range(SZ_LEFT-18,SZ_LEFT-10):
            draw.line([(x,SZ_TOP),(x,SZ_BOTTOM)],fill=(*cor_acento,200))
    elif e==2:
        for x in range(0,120):
            a=int(120*(1-x/120)); draw.line([(x,0),(x,H)],fill=(*MARINHO,a))
    elif e==3:
        for i in range(SZ_TOP,SZ_TOP+5): draw.line([(SZ_LEFT,i),(SZ_RIGHT,i)],fill=(*cor_acento,220))
        for i in range(SZ_BOTTOM-5,SZ_BOTTOM): draw.line([(SZ_LEFT,i),(SZ_RIGHT,i)],fill=(*cor_acento,220))
    elif e==4:
        for y in range(0,220):
            a=int(110*(1-y/220)); draw.line([(0,y),(W,y)],fill=(*PETROLEO,a))
    else:
        for y in range(H-200,H):
            a=int(160*(y-(H-200))/max(1,200)); draw.line([(0,y),(W,y)],fill=(*cor_acento,min(a,120)))
    return img

# ── Tipografia — 7 estrategias visuais ───────────────────────────────────────
def formatar_titulo(tema, estilo_idx, cor_principal, cor_destaque):
    palavras=tema.split(); e=estilo_idx%7; elementos=[]
    # Tamanho adaptativo ao comprimento do tema
    n = len(tema)
    tam_base = 104 if n<=12 else 88 if n<=20 else 72 if n<=30 else 60
    w_base   = 13  if n<=12 else 14 if n<=20 else 16 if n<=30 else 18

    if e==0:
        linhas=textwrap.wrap(tema.upper(),width=w_base)
        for l in linhas: elementos.append((l,f_titulo,tam_base,cor_principal))
    elif e==1:
        if len(palavras)>=2:
            elementos.append((palavras[0].upper(),f_titulo,min(130,tam_base+16),cor_principal))
            for l in textwrap.wrap(" ".join(palavras[1:]).title(),width=w_base+2):
                elementos.append((l,f_bold,max(54,tam_base-22),cor_destaque))
        else: elementos.append((tema.upper(),f_titulo,tam_base,cor_principal))
    elif e==2:
        linhas=textwrap.wrap(tema.title(),width=w_base)
        for i,l in enumerate(linhas):
            elementos.append((l,f_titulo,tam_base,cor_principal if i==0 else cor_destaque))
    elif e==3:
        for l in textwrap.wrap(tema.upper(),width=w_base): elementos.append((l,f_bold,tam_base,cor_principal))
        for l in textwrap.wrap(tema.title(),width=w_base+4): elementos.append((l,f_light,max(50,tam_base-28),cor_destaque))
    elif e==4:
        linhas=textwrap.wrap(tema.title(),width=w_base)
        for i,l in enumerate(linhas):
            elementos.append((l,f_titulo,tam_base,cor_destaque if i==len(linhas)-1 else cor_principal))
    elif e==5:
        if len(palavras)>=3:
            elementos.append((" ".join(palavras[:2]).title(),f_bold,tam_base,cor_principal))
            elementos.append((" ".join(palavras[2:]).title(),f_corpo,max(54,tam_base-20),cor_destaque))
        else: elementos.append((tema.title(),f_bold,tam_base,cor_principal))
    else:
        linhas=textwrap.wrap(tema.upper(),width=w_base)
        for l in linhas: elementos.append((l,f_titulo,tam_base,cor_principal))
    return elementos

def aplicar_sombra_texto(draw, texto, fonte, x, y, lum_fundo, cor_sombra=None):
    """Sombra profissional adaptativa — nao deforma a fonte."""
    if cor_sombra is None:
        cor_sombra = PRETO if lum_fundo > 150 else MARINHO
    opacidade = 140 if lum_fundo > 100 else 80
    if lum_fundo > 40:
        for ox,oy in [(2,2),(3,3),(1,3)]:
            draw.text((x+ox,y+oy),texto,font=fonte,fill=(*cor_sombra,opacidade))

# ── Gerar Card ────────────────────────────────────────────────────────────────
def gerar_card_imagem(tema, legenda, imagem_url, pid=""):
    """Gera a imagem PIL do card com todas as tecnicas de design."""
    img=Image.new("RGB",(W,H),MARINHO)
    fundo=None
    seed = hash(tema.lower()+pid) % 1000

    # Analisa cores antes de tudo
    temp_img=None
    if imagem_url:
        try:
            r=requests.get(imagem_url,timeout=15); r.raise_for_status()
            temp_img=Image.open(io.BytesIO(r.content)).convert("RGB").resize((200,250),Image.Resampling.LANCZOS)
        except: pass

    if temp_img: cor_principal,cor_destaque,cor_acento=cores_harmonicas_da_paleta(temp_img)
    else: cor_principal,cor_destaque,cor_acento=LARANJA,BRANCO,TEAL
    print(f"[cores] p={cor_principal} d={cor_destaque} a={cor_acento}")

    # Prepara fundo com pipeline fotografico completo
    if imagem_url:
        fundo=preparar_fundo(imagem_url,pid,cor_principal,cor_destaque,seed,tema)
        if fundo: img.paste(fundo,(0,0))

    # Elementos graficos da identidade
    img=adicionar_elementos_brand(img,cor_acento,seed%6)

    # Tipografia
    estilo_tipo=(seed)%7
    elementos=formatar_titulo(tema,estilo_tipo,cor_principal,cor_destaque)
    altura_bloco=sum(e[2]+18 for e in elementos)

    if fundo:
        yt=melhor_posicao_titulo(fundo,altura_bloco)
        lum_zona=luminosidade_regiao(fundo,max(0,yt-10),min(yt+altura_bloco+10,H))
    else:
        yt=SZ_TOP+60; lum_zona=30

    draw=ImageDraw.Draw(img,"RGBA"); ya=yt
    for (texto,fonte_fn,tamanho,cor) in elementos:
        fonte=fonte_fn(tamanho)
        aplicar_sombra_texto(draw,texto,fonte,SZ_LEFT,ya,lum_zona)
        draw.text((SZ_LEFT,ya),texto,font=fonte,fill=cor)
        ya+=tamanho+18

    return img

def upload_imagem(img, folder, public_id):
    buf=io.BytesIO(); img.save(buf,format="JPEG",quality=92); buf.seek(0)
    try:
        res=cloudinary.uploader.upload(buf,public_id=public_id,folder=folder,overwrite=True,resource_type="image")
        return res.get("secure_url","")
    except Exception as e: print(f"Upload erro:{e}"); return ""

def get_sheets():
    creds=service_account.Credentials.from_service_account_info(json.loads(SERVICE_ACCOUNT_JSON),scopes=SCOPES)
    return build("sheets","v4",credentials=creds)

def escrever_planilha(tema,legenda,url):
    svc=get_sheets(); agora=datetime.now().strftime("%Y-%m-%d %H:%M")
    linha=[agora,tema,tema,legenda,"Profissional e acolhedor","Pronta","Aguardando Postagem",url]
    res=svc.spreadsheets().values().append(spreadsheetId=SPREADSHEET_ID,range="A:H",
        valueInputOption="RAW",insertDataOption="INSERT_ROWS",body={"values":[linha]}).execute()
    try: return int(res["updates"]["updatedRange"].split("!A")[1].split(":")[0])
    except: return 0

def atualizar_status(linha,status):
    get_sheets().spreadsheets().values().update(spreadsheetId=SPREADSHEET_ID,
        range=f"G{linha}",valueInputOption="RAW",body={"values":[[status]]}).execute()

# ── Rotas ─────────────────────────────────────────────────────────────────────

@app.route("/health",methods=["GET"])
def health():
    return jsonify({"status":"ok","dimensoes":f"{W}x{H}","fontes_dir":FONTS_DIR,"fontes_existem":os.path.exists(FONTS_DIR)})

@app.route("/gerar-legenda",methods=["POST"])
def rota_gerar_legenda():
    data=request.get_json() or {}; tema=data.get("tema","").strip()
    if not tema: return jsonify({"erro":"Tema obrigatorio"}),400
    try: return jsonify({"legenda":gerar_legenda_ia(tema)})
    except Exception as e: return jsonify({"erro":str(e)}),500

@app.route("/preview-card",methods=["POST"])
def rota_preview_card():
    """
    Gera o card e faz upload em pasta temporaria de preview.
    NAO grava na planilha. NAO salva no Firestore.
    Retorna URL de preview e card_id para uso posterior na aprovacao.
    """
    data=request.get_json() or {}
    tema=data.get("tema","").strip(); legenda=data.get("legenda","").strip()
    if not tema: return jsonify({"erro":"Tema obrigatorio"}),400

    erros_leg=None
    if not legenda:
        try: legenda=gerar_legenda_ia(tema)
        except Exception as e: erros_leg=str(e); legenda=""
    if legenda and "CRP 04/57327" not in legenda:
        legenda=legenda.rstrip()+ASSINATURA

    url_img,pid=buscar_imagem(tema)

    try:
        card=gerar_card_imagem(tema,legenda,url_img,pid)
        card_id=f"preview_{uuid.uuid4().hex[:10]}"
        # Upload na pasta de preview (temporario)
        preview_url=upload_imagem(card,CLOUDINARY_PREVIEW,card_id)
        if not preview_url: return jsonify({"erro":"Falha no upload do preview"}),500

        # Guarda dados em cache para aprovacao posterior
        _cards_pendentes[card_id]={
            "tema":tema,"legenda":legenda,
            "imagem_fundo":url_img,"pid_fundo":pid,
            "preview_url":preview_url,"card_pil":None,
        }
        # Salva imagem PIL em buffer para reusar na aprovacao
        buf=io.BytesIO(); card.save(buf,format="JPEG",quality=92)
        _cards_pendentes[card_id]["card_bytes"]=buf.getvalue()

    except Exception as e: return jsonify({"erro":f"Erro ao gerar card:{e}"}),500

    resp={
        "card_id":card_id,
        "preview_url":preview_url,
        "legenda":legenda,
        "imagem_fundo":url_img,
    }
    if erros_leg: resp["aviso_legenda"]=erros_leg
    return jsonify(resp)

@app.route("/aprovar-card",methods=["POST"])
def rota_aprovar_card():
    """
    Aprovacao do card:
    - Move imagem para pasta permanente no Cloudinary
    - Grava na planilha Google Sheets
    - Remove do cache de pendentes
    """
    data=request.get_json() or {}
    card_id=data.get("card_id","")
    tema=data.get("tema","").strip()
    legenda=data.get("legenda","").strip()

    if not card_id or card_id not in _cards_pendentes:
        return jsonify({"erro":"Card nao encontrado. Gere novamente."}),400

    dados=_cards_pendentes[card_id]
    # Usa legenda editada pelo usuario se diferente
    legenda_final=legenda if legenda else dados["legenda"]

    try:
        # Faz upload definitivo na pasta permanente
        uid=f"post_{uuid.uuid4().hex[:8]}"
        buf=io.BytesIO(dados["card_bytes"])
        res=cloudinary.uploader.upload(buf,public_id=uid,folder=CLOUDINARY_POSTS,overwrite=True,resource_type="image")
        card_url=res.get("secure_url","")
        if not card_url: return jsonify({"erro":"Falha no upload definitivo"}),500

        # Deleta preview do Cloudinary
        try: cloudinary.uploader.destroy(f"{CLOUDINARY_PREVIEW}/{card_id}")
        except: pass

        # Remove do cache
        del _cards_pendentes[card_id]

    except Exception as e: return jsonify({"erro":f"Erro no upload: {e}"}),500

    # Grava na planilha
    linha=0
    try: linha=escrever_planilha(tema,legenda_final,card_url)
    except Exception as e: print(f"Erro planilha:{e}")

    return jsonify({
        "cloudinary_url":card_url,
        "linha_planilha":linha,
        "status":"Aguardando Postagem",
    })

@app.route("/gerar-card",methods=["POST"])
def rota_gerar_card():
    """Rota legada — mantida para compatibilidade. Usa o novo fluxo de preview."""
    return rota_preview_card()

@app.route("/atualizar-status",methods=["POST"])
def rota_atualizar_status():
    data=request.get_json() or {}; linha=data.get("linha"); status=data.get("status","Postado")
    if not linha: return jsonify({"erro":"Linha obrigatoria"}),400
    try: atualizar_status(int(linha),status); return jsonify({"ok":True})
    except Exception as e: return jsonify({"erro":str(e)}),500

if __name__=="__main__":
    app.run(host="0.0.0.0",port=int(os.getenv("PORT",5000)))
