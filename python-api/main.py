"""
python-api/main.py — API Flask completa — Render
"""
import os, io, uuid, random, json, textwrap, time, math
import numpy as np
import requests, cloudinary, cloudinary.uploader, cloudinary.api
from datetime import datetime
from flask import Flask, request, jsonify
from flask_cors import CORS
from PIL import Image, ImageDraw, ImageFont
from rembg import remove as rembg_remove
from google.oauth2 import service_account
from googleapiclient.discovery import build

app = Flask(__name__)
CORS(app)

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

W, H             = 1080, 1350
CLOUDINARY_POSTS = "AlvoreSer_Posts"
PASTA_RONILSON   = "Ronilson"
SZ_TOP=135; SZ_BOTTOM=1215; SZ_LEFT=125; SZ_RIGHT=955

MARINHO=(2,64,89); PETROLEO=(27,121,125); TEAL=(4,157,191)
BRANCO=(244,246,248); LARANJA=(249,171,11); VERDE_NEUTRO=(119,153,147)
VERDE_VIVO=(122,181,0); VERDE_CITRICO=(146,204,29); AMARELO=(255,221,0)

PALETA_COMPLETA=[MARINHO,PETROLEO,TEAL,VERDE_NEUTRO,BRANCO,VERDE_VIVO,VERDE_CITRICO,LARANJA,AMARELO]
PALETA_SOMBRA=[("marinho",MARINHO),("petroleo",PETROLEO),("teal",TEAL),
    ("verde_neutro",VERDE_NEUTRO),("branco",BRANCO),("verde_vivo",VERDE_VIVO),
    ("verde_citrico",VERDE_CITRICO),("laranja",LARANJA),("amarelo",AMARELO)]

TEMAS_PESADOS=["depressao","luto","trauma","burnout","borderline"]
TEMAS_ENERGIA=["tdah","autoestima","motivacao"]
TEMAS_EQUILIBRIO=["autismo","terapia","familia","relacionamento","ansiedade","meditacao"]

def cor_titulo(tema):
    t=tema.lower()
    for p in TEMAS_PESADOS:
        if p in t: return BRANCO
    for e in TEMAS_ENERGIA:
        if e in t: return LARANJA
    for eq in TEMAS_EQUILIBRIO:
        if eq in t: return TEAL
    return LARANJA

ROOT_DIR=os.path.dirname(os.path.abspath(__file__))
FONTS_DIR=os.path.join(ROOT_DIR,"..","src","Brand","fonts")

def _font(nome,tam):
    try: return ImageFont.truetype(os.path.join(FONTS_DIR,nome),tam)
    except:
        try: return ImageFont.load_default(size=tam)
        except: return ImageFont.load_default()

def f_titulo(t): return _font("AGILERA.OTF",t)
def f_bold(t):   return _font("MALGUNBD.TTF",t)
def f_light(t):  return _font("MALGUNSL.TTF",t)

ASSINATURA="\n\n\U0001f468\u200d\U0001f4bc Ronilson Nogueira\n\u270d\ufe0f Psic\u00f3logo e Professor\n\U0001f9e9 Refer\u00eancia em Autismo e TDAH\nCRP 04/57327"

TAGS_CONTEUDO=["pessoa_sozinha","casal","familia","crianca","adolescente","adulto","idoso","grupo","natureza_chuva","natureza_sol","natureza_mar","natureza_floresta","ambiente_sereno","ambiente_urbano","abstrato","foto_profissional"]
TAGS_CLIMA=["clima_sereno","clima_reflexivo","clima_alegre","clima_pesado","clima_neutro","clima_esperancoso","clima_energetico","clima_acolhedor"]
MAPA_TAGS={
    "ansiedade":{"conteudo":["pessoa_sozinha","adulto"],"clima":["clima_reflexivo","clima_sereno"]},
    "depressao":{"conteudo":["pessoa_sozinha"],"clima":["clima_pesado","clima_reflexivo"]},
    "autismo":{"conteudo":["crianca","familia","adulto"],"clima":["clima_sereno","clima_acolhedor"]},
    "tdah":{"conteudo":["crianca","adolescente","adulto"],"clima":["clima_energetico","clima_neutro"]},
    "borderline":{"conteudo":["pessoa_sozinha","adulto"],"clima":["clima_reflexivo","clima_pesado"]},
    "burnout":{"conteudo":["adulto","pessoa_sozinha"],"clima":["clima_pesado","clima_reflexivo"]},
    "relacionamento":{"conteudo":["casal","duas_pessoas"],"clima":["clima_acolhedor","clima_sereno"]},
    "familia":{"conteudo":["familia","mae_filho"],"clima":["clima_acolhedor","clima_alegre"]},
    "luto":{"conteudo":["pessoa_sozinha"],"clima":["clima_pesado","clima_reflexivo"]},
    "autoestima":{"conteudo":["pessoa_sozinha","adulto"],"clima":["clima_esperancoso","clima_sereno"]},
    "trauma":{"conteudo":["pessoa_sozinha"],"clima":["clima_pesado","clima_reflexivo"]},
    "terapia":{"conteudo":["pessoa_profissional"],"clima":["clima_sereno","clima_acolhedor"]},
    "natureza":{"conteudo":["natureza_sol","natureza_mar"],"clima":["clima_sereno","clima_esperancoso"]},
    "meditacao":{"conteudo":["pessoa_sozinha"],"clima":["clima_sereno","clima_espiritualizado"]},
}

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
            r=requests.post(GROQ_URL,headers={"Authorization":f"Bearer {GROQ_API_KEY}","Content-Type":"application/json"},
                json={"model":m,"messages":[{"role":"user","content":PROMPT_LEGENDA.format(tema=tema)}],"max_tokens":400},timeout=20)
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

def selecionar_tags(tema):
    t=tema.lower()
    for k,v in MAPA_TAGS.items():
        if k in t: return v
    return {"conteudo":random.sample(TAGS_CONTEUDO,2),"clima":random.sample(TAGS_CLIMA,2)}

def buscar_imagem(tags):
    todas=tags.get("conteudo",[])+tags.get("clima",[])
    random.shuffle(todas)
    for tag in todas:
        try:
            res=cloudinary.api.resources_by_tag(tag,type="upload",max_results=30)
            rec=[r for r in res.get("resources",[]) if CLOUDINARY_POSTS not in r.get("public_id","")]
            if rec:
                c=random.choice(rec)
                return c.get("secure_url"),c.get("public_id","")
        except: continue
    try:
        res=cloudinary.api.resources(type="upload",max_results=50)
        rec=[r for r in res.get("resources",[]) if CLOUDINARY_POSTS not in r.get("public_id","")]
        if rec:
            c=random.choice(rec)
            return c.get("secure_url"),c.get("public_id","")
    except: pass
    return None,""

def distancia_cor(c1,c2): return ((c1[0]-c2[0])**2+(c1[1]-c2[1])**2+(c1[2]-c2[2])**2)**0.5
def luminosidade_regiao(img,y1,y2):
    p=list(img.crop((0,y1,W,y2)).convert("L").getdata())
    return sum(p)/len(p)
def cor_dominante_regiao(img,y,h):
    p=list(img.crop((0,y,W,min(y+h,H))).resize((50,20),Image.Resampling.LANCZOS).convert("RGB").getdata())
    return (sum(x[0] for x in p)//len(p),sum(x[1] for x in p)//len(p),sum(x[2] for x in p)//len(p))

def eh_foto_ronilson(pid): return PASTA_RONILSON.lower() in pid.lower()
def eh_fundo_solido(img):
    s=img.resize((100,125),Image.Resampling.LANCZOS).convert("RGB")
    rv=[p[0] for p in s.getdata()]; m=sum(rv)/len(rv)
    var=sum((v-m)**2 for v in rv)/len(rv)
    lum=luminosidade_regiao(img,0,H)
    return var<800 and (lum>220 or lum<30)

def remover_fundo(img):
    buf=io.BytesIO(); img.save(buf,format="PNG")
    return Image.open(io.BytesIO(rembg_remove(buf.getvalue()))).convert("RGBA")

def criar_fundo_identidade(tema,estilo):
    t=tema.lower()
    if any(p in t for p in ["depressao","luto","trauma","burnout"]): cor1,cor2=MARINHO,PETROLEO
    elif any(p in t for p in ["tdah","autoestima","motivacao"]): cor1,cor2=LARANJA,AMARELO
    elif any(p in t for p in ["natureza","crescimento","renovacao"]): cor1,cor2=VERDE_VIVO,PETROLEO
    elif any(p in t for p in ["autismo","familia","acolhimento"]): cor1,cor2=TEAL,VERDE_NEUTRO
    else: cor1,cor2=PETROLEO,TEAL
    base=Image.new("RGB",(W,H)); draw=ImageDraw.Draw(base); e=estilo%4
    if e==0:
        for y in range(H):
            tv=y/H; draw.line([(0,y),(W,y)],fill=(int(cor1[0]*(1-tv)+cor2[0]*tv),int(cor1[1]*(1-tv)+cor2[1]*tv),int(cor1[2]*(1-tv)+cor2[2]*tv)))
    elif e==1:
        for y in range(H):
            for x in range(0,W,3):
                tv=(x/W+y/H)/2; n=random.randint(-6,6)
                draw.line([(x,y),(x+3,y)],fill=(max(0,min(255,int(cor1[0]*(1-tv)+cor2[0]*tv)+n)),max(0,min(255,int(cor1[1]*(1-tv)+cor2[1]*tv)+n)),max(0,min(255,int(cor1[2]*(1-tv)+cor2[2]*tv)+n))))
    elif e==2:
        for y in range(H):
            tv=y/H; draw.line([(0,y),(W,y)],fill=(int(cor1[0]*(1-tv)+cor2[0]*tv),int(cor1[1]*(1-tv)+cor2[1]*tv),int(cor1[2]*(1-tv)+cor2[2]*tv)))
        cx,cy=W//2,H
        for raio in range(200,1400,120): draw.ellipse([cx-raio,cy-raio,cx+raio,cy+raio],outline=BRANCO,width=1)
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

def tratar_fundo_solido(img,tema):
    lum=luminosidade_regiao(img,0,H)
    c1,c2=(MARINHO,PETROLEO) if lum>220 else (PETROLEO,TEAL)
    base=Image.new("RGB",(W,H)); draw=ImageDraw.Draw(base)
    for y in range(H):
        tv=y/H; draw.line([(0,y),(W,y)],fill=(int(c1[0]*(1-tv)+c2[0]*tv),int(c1[1]*(1-tv)+c2[1]*tv),int(c1[2]*(1-tv)+c2[2]*tv)))
    return Image.blend(base.convert("RGBA"),img.convert("RGBA"),alpha=0.6).convert("RGB")

def complexidade_zona(arr,y1,y2):
    z=arr[y1:y2,:].astype(float)
    return (np.abs(np.diff(z,axis=0)).mean()+np.abs(np.diff(z,axis=1)).mean())/2

def melhor_posicao_titulo(img,n_lin):
    ab=n_lin*108+40; uh=SZ_BOTTOM-SZ_TOP
    zonas=[SZ_TOP+20,SZ_TOP+int(uh*0.25),SZ_TOP+int(uh*0.50)-ab//2,SZ_TOP+int(uh*0.65),SZ_BOTTOM-ab-20]
    arr=np.array(img.convert("L")); melhor=zonas[-1]; menor=float("inf"); terco=uh/3
    for y in zonas:
        if y<SZ_TOP or y+ab>SZ_BOTTOM: continue
        c=complexidade_zona(arr,y,y+ab)
        if y<SZ_TOP+terco or y>SZ_BOTTOM-terco-ab: c*=0.80
        if c<menor: menor=c; melhor=y
    return melhor

def sombra_dinamica(img,y,n_lin):
    lum=luminosidade_regiao(img,y,min(y+n_lin*108,H))
    if lum<40: return None
    cf=cor_dominante_regiao(img,y,n_lin*108)
    return max(PALETA_SOMBRA,key=lambda x:distancia_cor(cf,x[1]))[1]

def aplicar_halo(draw,texto,fonte,x,y,cor,raio=12):
    for dist in range(raio,0,-1):
        alpha=int(200*(1-dist/(raio+1)))
        for ang in range(0,360,30):
            ox=int(dist*math.cos(math.radians(ang))); oy=int(dist*math.sin(math.radians(ang)))
            draw.text((x+ox,y+oy),texto,font=fonte,fill=(*cor,alpha))

def adicionar_elementos_brand(img,tema):
    draw=ImageDraw.Draw(img,"RGBA")
    cf=cor_dominante_regiao(img,H//2,H//2)
    ca=max(PALETA_COMPLETA,key=lambda c:distancia_cor(cf,c))
    e=hash(tema.lower())%4
    if e==0:
        for y in range(SZ_BOTTOM-200,SZ_BOTTOM+50):
            a=int(160*(y-(SZ_BOTTOM-200))/250); draw.line([(0,y),(W,y)],fill=(*MARINHO,min(a,160)))
    elif e==1:
        for i in range(0,180,3):
            a=int(100*(1-i/180)); draw.line([(0,i),(W,i+60)],fill=(*PETROLEO,a),width=2)
    elif e==2:
        cx,cy=W-200,200
        for r in range(300,0,-10):
            a=int(60*(1-r/300)); draw.ellipse([cx-r,cy-r,cx+r,cy+r],outline=(*ca,a),width=2)
    else:
        for y in range(SZ_BOTTOM-120,H):
            a=int(140*(y-(SZ_BOTTOM-120))/max(1,H-SZ_BOTTOM+120)); draw.line([(0,y),(W,y)],fill=(*ca,min(a,140)))
    return img

def preparar_fundo(url,pid="",tema=""):
    try:
        r=requests.get(url,timeout=20); r.raise_for_status()
        img=Image.open(io.BytesIO(r.content)).convert("RGB")
        ratio=max(W/img.width,H/img.height); nw,nh=int(img.width*ratio),int(img.height*ratio)
        img=img.resize((nw,nh),Image.Resampling.LANCZOS)
        l=(nw-W)//2; t=(nh-H)//2; img=img.crop((l,t,l+W,t+H))
        if eh_foto_ronilson(pid):
            try:
                fi=criar_fundo_identidade(tema,hash(tema.lower())%4)
                img=compor_com_fundo(remover_fundo(img),fi)
            except Exception as e: print(f"rembg falhou:{e}")
        elif eh_fundo_solido(img):
            img=tratar_fundo_solido(img,tema)
        return img
    except Exception as e: print(f"Erro fundo:{e}"); return None

def gerar_card(tema,legenda,imagem_url,pid=""):
    img=Image.new("RGB",(W,H),MARINHO); fundo=None
    if imagem_url:
        fundo=preparar_fundo(imagem_url,pid,tema)
        if fundo: img.paste(fundo,(0,0))
    img=adicionar_elementos_brand(img,tema)
    draw=ImageDraw.Draw(img,"RGBA"); ct=cor_titulo(tema); ft=f_titulo(88)
    linhas=textwrap.wrap(tema.upper(),width=15)[:3]; nl=len(linhas)
    if fundo: yt=melhor_posicao_titulo(fundo,nl); cs=sombra_dinamica(fundo,yt,nl)
    else: yt=SZ_TOP+40; cs=PETROLEO
    ya=yt
    for l in linhas:
        if cs: aplicar_halo(draw,l,ft,SZ_LEFT,ya,cs,raio=12)
        draw.text((SZ_LEFT,ya),l,font=ft,fill=ct); ya+=108
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
    tags=selecionar_tags(tema); url_img,pid=buscar_imagem(tags)
    try:
        card=gerar_card(tema,legenda,url_img,pid)
        uid=f"post_{uuid.uuid4().hex[:8]}"
        card_url=upload_card(card,uid)
        if not card_url: return jsonify({"erro":"Falha no upload"}),500
    except Exception as e: return jsonify({"erro":f"Erro ao gerar card:{e}"}),500
    linha=0
    try: linha=escrever_planilha(tema,legenda,card_url)
    except Exception as e: print(f"Erro planilha:{e}")
    resp={"cloudinary_url":card_url,"legenda":legenda,"tags_usadas":tags,"imagem_fundo":url_img,"linha_planilha":linha,"status":"Aguardando Postagem"}
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
