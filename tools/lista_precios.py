from PIL import Image, ImageDraw, ImageFont
F="/System/Library/Fonts/HelveticaNeue.ttc"
def f(size, idx): return ImageFont.truetype(F, size, index=idx)  # 0 regular, 1 bold, 4 condensed bold? 
B=lambda s: f(s,1); R=lambda s: f(s,0); M=lambda s: f(s,10)
W,H=1080,1700
im=Image.new("RGB",(W,H),"#f4f2ee"); d=ImageDraw.Draw(im)
NEG="#16181b"; GR="#6b6f76"; AM="#f5b301"; LIN="#dcd8d0"
# encabezado
d.rectangle([0,0,W,300],fill=NEG)
d.text((70,70),"LISTA DE PRECIOS",font=B(78),fill="white")
d.text((70,170),"Para gomerías · compra en cantidad",font=R(40),fill="#c9ccd1")
d.rectangle([70,245,190,253],fill=AM)
filas=[("Llanta de aleación","Rodado 14","$115.000"),
       ("Llanta de aleación","Rodado 15","$126.500"),
       ("Llanta de aleación","Rodado 16","$138.000"),
       ("Llanta de aleación","Rodado 17","$149.500"),
       ("Llanta de chapa","Auto","$51.750"),
       ("Llanta de chapa","Camioneta","$80.500"),
       ("Auxilio sin rodar","Llanta + cubierta","$97.750")]
y=350
d.text((70,y),"PRODUCTO",font=B(26),fill=GR); t="PRECIO POR UNIDAD"; d.text((W-70-d.textlength(t,font=B(26)),y),t,font=B(26),fill=GR)
y+=55
for i,(a,b,p) in enumerate(filas):
    alto=125
    if i%2==0: d.rounded_rectangle([40,y,W-40,y+alto],radius=18,fill="white")
    d.text((70,y+22),a,font=B(44),fill=NEG)
    d.text((70,y+76),b,font=R(32),fill=GR)
    d.text((W-70-d.textlength(p,font=B(58)),y+30),p,font=B(58),fill=NEG)
    y+=alto+10
y+=25
d.line([70,y,W-70,y],fill=LIN,width=3); y+=35
for t in ["Precios por unidad, en pesos. Sujetos a stock.",
          "Mirá lo disponible en cubiertasmdz.github.io"]:
    d.text((70,y),t,font=R(34),fill=NEG); y+=52
# pie
d.rectangle([0,H-150,W,H],fill=NEG)
d.text((70,H-112),"Pedidos por WhatsApp",font=R(34),fill="#c9ccd1")
t="261 554-0670"; d.text((W-70-d.textlength(t,font=B(56)),H-122),t,font=B(56),fill=AM)
d.text((70,H-66),"Mendoza · hacemos envíos",font=R(30),fill="#c9ccd1")
import sys
im.save(sys.argv[1]+".png"); im.save(sys.argv[1]+".pdf",resolution=150)
print(y)
