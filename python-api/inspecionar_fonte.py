from PIL import features, ImageFont, ImageDraw, Image

raqm = features.check("raqm")
print("RAQM disponivel:", raqm)

# Testa renderizacao com features se RAQM disponivel
if raqm:
    font = ImageFont.truetype("fonts/AGILERA.OTF", 80,
                              layout_engine=ImageFont.Layout.RAQM)
    img  = Image.new("RGB", (600, 120), (0,0,0))
    draw = ImageDraw.Draw(img)
    draw.text((10, 10), "Diagnóstico", font=font, fill=(255,255,255),
              features=["liga", "aalt"])
    img.save("teste_agilera_est.jpg")
    print("Imagem salva: teste_agilera_est.jpg")
else:
    print("RAQM nao disponivel — features OpenType nao funcionarao no Pillow padrao")
    print("Alternativa: instalar libraqm ou usar harfbuzz separado")
