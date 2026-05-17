"""
python-api/main.py — API Flask completa — Render
Identidade Visual AlvoreSer — 9 cores dominam tudo
"""
import os, io, uuid, random, json, textwrap, time, math
import numpy as np
import requests, cloudinary, cloudinary.uploader, cloudinary.api
from datetime import datetime
from flask import Flask, request, jsonify
from flask_cors import CORS
from PIL import Image, ImageDraw, ImageFont
from google.oauth2 import service_account
from googleapiclient.discovery import build

_rembg_remove = None
def get_rembg():
    global _rembg_remove
    if _rembg_remove is None:
        from rembg import remove as _r
        _rembg_remove = _r
    return _rembg_remove

app = Flask(__name__)
CORS(app, origins=["https://marvelous-cat-8a8767.netlify.app","http://localhost:5173","http://localhost:3000"], supports_credentials=True)

@app.after_request
def add_cors(response):
    response.headers["Access-Control-Allow-Origin"] = "https://marvelous-cat-8a8767.netlify.app"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type,Authorization"
    response.headers["Access-Control-Allow-Methods"] = "GET,POST,OPTIONS"
    return response

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
CLOUDINARY_POSTS = "AlvoreSer_Posts"
PASTA_RONILSON   = "banco de imagens/ronilson"

SZ_TOP=135; SZ_BOTTOM=1215; SZ_LEFT=125; SZ_RIGHT=955

MARINHO=(2,64,89); PETROLEO=(27,121,125); TEAL=(4,157,191)
BRANCO=(244,246,248); LARANJA=(249,171,11); VERDE_NEUTRO=(119,153,147)
VERDE_VIVO=(122,181,0); VERDE_CITRICO=(146,204,29); AMARELO=(255,221,0)
PRETO=(20,20,20)

PALETA_9=[MARINHO,PETROLEO,TEAL,VERDE_NEUTRO,BRANCO,LARANJA,VERDE_VIVO,VERDE_CITRICO,AMARELO]

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
    t=tema.lower()
    for chave,pasta in MAPA_PASTAS.items():
        if chave in t:
            try:
                res=cloudinary.api.resources(type="upload",prefix=pasta+"/",max_results=50)
                rec=[r for r in res.get("resources",[]) if CLOUDINARY_POSTS not in r.get("public_id","")]
                if rec:
                    c=random.choice(rec); print(f"[busca] {pasta}")
                    return c.get("secure_url"),c.get("public_id","")
            except Exception as e: print(f"[busca] erro {pasta}: {e}")
    pastas=list(set(MAPA_PASTAS.values())); random.shuffle(pastas)
    for pasta in pastas:
        try:
            res=cloudinary.api.resources(type="upload",prefix=pasta+"/",max_results=30)
            rec=[r for r in res.get("resources",[]) if CLOUDINARY_POSTS not in r.get("public_id","")]
            if rec:
                c=random.choice(rec); print(f"[busca] fallback {pasta}")
                return c.get("secure_url"),c.get("public_id","")
        except: continue
    print("[busca] sem imagem"); return None,""

def distancia_cor(c1,c2): return ((c1[0]-c2[0])**2+(c1[1]-c2[1])**2+(c1[2]-c2[2])**2)**0.5

def luminosidade_regiao(img,y1,y2):
    p=list(img.crop((0,y1,W,y2)).convert("L").getdata())
    return sum(p)/len(p)

def cor_dominante_regiao(img,y,h):
    p=list(img.crop((0,y,W,min(y+h,H))).resize((50,20),Image.Resampling.LANCZOS).convert("RGB").getdata())
    return (sum(x[0] for x in p)//len(p),sum(x[1] for x in p)//len(p),sum(x[2] for x in p)//len(p))

def cores_harmonicas_da_paleta(img):
    """Analisa imagem e retorna 3 cores da paleta que mais harmonizam."""
    cf=cor_dominante_regiao(img,0,img.size[1])
    ordenadas=sorted(PALETA_9,key=lambda c:distancia_cor(cf,c),reverse=True)
    cor_principal=ordenadas[0]; cor_destaque=ordenadas[1]
    cor_acento=ordenadas[2]
    for c in ordenadas[2:]:
        if distancia_cor(c,cor_principal)>80 and distancia_cor(c,cor_destaque)>80:
            cor_acento=c; break
    lum=sum(cf)/3
    if lum<60:
        cor_principal=BRANCO
    return cor_principal,cor_destaque,cor_acento

def complexidade_zona(arr,y1,y2):
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

def criar_fundo_identidade(cor1,cor2,estilo):
    base=Image.new("RGB",(W,H)); draw=ImageDraw.Draw(base); e=estilo%4
    if e==0:
        for y in range(H):
            tv=y/H
            draw.line([(0,y),(W,y)],fill=(int(cor1[0]*(1-tv)+cor2[0]*tv),int(cor1[1]*(1-tv)+cor2[1]*tv),int(cor1[2]*(1-tv)+cor2[2]*tv)))
    elif e==1:
        for y in range(H):
            for x in range(0,W,3):
                tv=(x/W+y/H)/2; n=random.randint(-8,8)
                draw.line([(x,y),(x+3,y)],fill=(max(0,min(255,int(cor1[0]*(1-tv)+cor2[0]*tv)+n)),max(0,min(255,int(cor1[1]*(1-tv)+cor2[1]*tv)+n)),max(0,min(255,int(cor1[2]*(1-tv)+cor2[2]*tv)+n))))
    elif e==2:
        for y in range(H):
            tv=y/H
            draw.line([(0,y),(W,y)],fill=(int(cor1[0]*(1-tv)+cor2[0]*tv),int(cor1[1]*(1-tv)+cor2[1]*tv),int(cor1[2]*(1-tv)+cor2[2]*tv)))
        cx,cy=W//2,H
        for raio in range(200,1400,150): draw.ellipse([cx-raio,cy-raio,cx+raio,cy+raio],outline=BRANCO,width=1)
    else:
        arr=np.zeros((H,W,3),dtype=np.uint8); cx,cy=W//2,int(H*0.75)
        for y in range(H):
            for x in range(W):
                d=math.sqrt((x-cx)**2+(y-cy)**2); tv=min(d/900,1.0)
                arr[y,x]=[int(cor2[0]*(1-tv)+cor1[0]*tv),int(cor2[1]*(1-tv)+cor1[1]*tv),int(cor2[2]*(1-tv)+cor1[2]*tv)]
        base=Image.fromarray(arr,"RGB")
    return base

def compor_com_fundo(pessoa_rgba,fundo):
    pw,ph=pessoa_rgba.size; nw=int(pw*H/ph)
    pessoa_rgba=pessoa_rgba.resize((nw,H),Image.Resampling.LANCZOS)
    res=fundo.convert("RGBA"); res.paste(pessoa_rgba,((W-nw)//2,0),pessoa_rgba)
    return res.convert("RGB")

def tratar_fundo_solido(img,cor1,cor2):
    base=Image.new("RGB",(W,H)); draw=ImageDraw.Draw(base)
    for y in range(H):
        tv=y/H
        draw.line([(0,y),(W,y)],fill=(int(cor1[0]*(1-tv)+cor2[0]*tv),int(cor1[1]*(1-tv)+cor2[1]*tv),int(cor1[2]*(1-tv)+cor2[2]*tv)))
    return Image.blend(base.convert("RGBA"),img.convert("RGBA"),alpha=0.55).convert("RGB")

def preparar_fundo(url,pid="",cor1=MARINHO,cor2=PETROLEO):
    try:
        r=requests.get(url,timeout=20); r.raise_for_status()
        img=Image.open(io.BytesIO(r.content)).convert("RGB")
        ratio=max(W/img.width,H/img.height); nw,nh=int(img.width*ratio),int(img.height*ratio)
        img=img.resize((nw,nh),Image.Resampling.LANCZOS)
        l=(nw-W)//2; t=(nh-H)//2; img=img.crop((l,t,l+W,t+H))
        if eh_foto_ronilson(pid):
            print(f"[fundo] Ronilson: {pid}")
            try:
                fi=criar_fundo_identidade(cor1,cor2,hash(pid)%4)
                img=compor_com_fundo(remover_fundo(img),fi)
                print("[fundo] rembg OK")
            except Exception as e: print(f"[fundo] rembg falhou: {e}")
        elif eh_fundo_solido(img):
            print("[fundo] solido, aplicando gradiente")
            img=tratar_fundo_solido(img,cor1,cor2)
        else:
            print("[fundo] imagem normal")
        return img
    except Exception as e: print(f"[fundo] erro: {e}"); return None

def adicionar_elementos_brand(img,cor_acento,estilo):
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
        for y in range(H-180,H):
            for x in range(W-180,W):
                d=math.sqrt((x-(W-180))**2+(y-(H-180))**2)
                if d<180:
                    a=int(80*(1-d/180)); draw.point((x,y),fill=(*cor_acento,a))
    return img

def formatar_titulo(tema,estilo_idx,cor_principal,cor_destaque):
    palavras=tema.split(); e=estilo_idx%7; elementos=[]
    if e==0:
        linhas=textwrap.wrap(tema.upper(),width=11)[:3]
        for l in linhas: elementos.append((l,f_titulo,104,cor_principal))
    elif e==1:
        if len(palavras)>=2:
            elementos.append((palavras[0].upper(),f_titulo,130,cor_principal))
            for l in textwrap.wrap(" ".join(palavras[1:]).title(),width=14)[:2]:
                elementos.append((l,f_bold,68,cor_destaque))
        else: elementos.append((tema.upper(),f_titulo,120,cor_principal))
    elif e==2:
        linhas=textwrap.wrap(tema.title(),width=13)[:2]
        for i,l in enumerate(linhas):
            elementos.append((l,f_titulo,96,cor_principal if i==0 else cor_destaque))
    elif e==3:
        for l in textwrap.wrap(tema.upper(),width=12)[:1]: elementos.append((l,f_bold,110,cor_principal))
        for l in textwrap.wrap(tema.title(),width=16)[:2]: elementos.append((l,f_light,58,cor_destaque))
    elif e==4:
        linhas=textwrap.wrap(tema.title(),width=14)[:3]
        for i,l in enumerate(linhas):
            elementos.append((l,f_titulo,88,cor_destaque if i==len(linhas)-1 else cor_principal))
    elif e==5:
        if len(palavras)>=3:
            elementos.append((" ".join(palavras[:2]).title(),f_bold,82,cor_principal))
            elementos.append((" ".join(palavras[2:]).title(),f_corpo,66,cor_destaque))
        else: elementos.append((tema.title(),f_bold,88,cor_principal))
    else:
        if len(tema)<=12: elementos.append((tema.upper(),f_titulo,120,cor_principal))
        else:
            for l in textwrap.wrap(tema.upper(),width=10)[:3]: elementos.append((l,f_titulo,92,cor_principal))
    return elementos

def aplicar_sombra_texto(draw,texto,fonte,x,y,lum_fundo):
    if lum_fundo>150:
        for ox,oy in [(2,2),(3,3)]: draw.text((x+ox,y+oy),texto,font=fonte,fill=(*PRETO,120))
    elif lum_fundo>=80:
        for ox,oy in [(2,2),(3,3)]: draw.text((x+ox,y+oy),texto,font=fonte,fill=(*MARINHO,140))

def gerar_card(tema,legenda,imagem_url,pid=""):
    img=Image.new("RGB",(W,H),MARINHO); fundo=None
    temp_img=None
    if imagem_url:
        try:
            r=requests.get(imagem_url,timeout=15); r.raise_for_status()
            temp_img=Image.open(io.BytesIO(r.content)).convert("RGB").resize((200,250),Image.Resampling.LANCZOS)
        except: pass
    if temp_img: cor_principal,cor_destaque,cor_acento=cores_harmonicas_da_paleta(temp_img)
    else: cor_principal,cor_destaque,cor_acento=LARANJA,BRANCO,TEAL
    print(f"[cores] p={cor_principal} d={cor_destaque} a={cor_acento}")
    if imagem_url:
        fundo=preparar_fundo(imagem_url,pid,cor_principal,cor_destaque)
        if fundo: img.paste(fundo,(0,0))
    img=adicionar_elementos_brand(img,cor_acento,hash(tema.lower())%6)
    estilo_tipo=(hash(tema.lower())+hash(pid))%7
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
        draw.text((SZ_LEFT,ya),texto,font=fonte,fill=cor); ya+=tamanho+18
    return img

def upload_card(img,pid):
    buf=io.BytesIO(); img.save(buf,format="JPEG",quality=92); buf.seek(0)
    try:
        res=cloudinary.uploader.upload(buf,public_id=pid,folder=CLOUDINARY_POSTS,overwrite=True,resource_type="image")
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

@app.route("/health",methods=["GET"])
def health():
    return jsonify({"status":"ok","dimensoes":f"{W}x{H}","fontes_dir":FONTS_DIR,"fontes_existem":os.path.exists(FONTS_DIR)})

@app.route("/gerar-legenda",methods=["POST"])
def rota_gerar_legenda():
    data=request.get_json() or {}; tema=data.get("tema","").strip()
    if not tema: return jsonify({"erro":"Tema obrigatorio"}),400
    try: return jsonify({"legenda":gerar_legenda_ia(tema)})
    except Exception as e: return jsonify({"erro":str(e)}),500

@app.route("/gerar-card",methods=["POST"])
def rota_gerar_card():
    data=request.get_json() or {}
    tema=data.get("tema","").strip(); legenda=data.get("legenda","").strip()
    if not tema: return jsonify({"erro":"Tema obrigatorio"}),400
    erros_leg=None
    if not legenda:
        try: legenda=gerar_legenda_ia(tema)
        except Exception as e: erros_leg=str(e); legenda=""
    if legenda and "CRP 04/57327" not in legenda: legenda=legenda.rstrip()+ASSINATURA
    url_img,pid=buscar_imagem(tema)
    try:
        card=gerar_card(tema,legenda,url_img,pid)
        uid=f"post_{uuid.uuid4().hex[:8]}"
        card_url=upload_card(card,uid)
        if not card_url: return jsonify({"erro":"Falha no upload"}),500
    except Exception as e: return jsonify({"erro":f"Erro ao gerar card:{e}"}),500
    linha=0
    try: linha=escrever_planilha(tema,legenda,card_url)
    except Exception as e: print(f"Erro planilha:{e}")
    resp={"cloudinary_url":card_url,"legenda":legenda,"imagem_fundo":url_img,"linha_planilha":linha,"status":"Aguardando Postagem"}
    if erros_leg: resp["aviso_legenda"]=erros_leg
    return jsonify(resp)

@app.route("/atualizar-status",methods=["POST"])
def rota_atualizar_status():
    data=request.get_json() or {}; linha=data.get("linha"); status=data.get("status","Postado")
    if not linha: return jsonify({"erro":"Linha obrigatoria"}),400
    try: atualizar_status(int(linha),status); return jsonify({"ok":True})
    except Exception as e: return jsonify({"erro":str(e)}),500

if __name__=="__main__":
    app.run(host="0.0.0.0",port=int(os.getenv("PORT",5000)))
