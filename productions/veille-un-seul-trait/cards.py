import sys
from PIL import Image, ImageDraw, ImageFont
F=sys.argv[1]; OUT=sys.argv[2]
W,H=1080,1920
CHAR=(9,9,13); IVORY=(244,240,237); CARMIN=(241,58,84)
def barlow(sz): return ImageFont.truetype(F+'/BarlowCondensed-SemiBold.ttf', sz)
def manrope(sz, w=b'Medium'):
    f=ImageFont.truetype(F+'/Manrope.ttf', sz)
    try: f.set_variation_by_name(w)
    except Exception as e: print('var',e, f.get_variation_names())
    return f
# End card
im=Image.new('RGB',(W,H),CHAR); d=ImageDraw.Draw(im)
t='BOJ.ART'; f=barlow(230); tw=d.textlength(t,font=f)
d.text(((W-tw)/2,700),t,font=f,fill=IVORY)
# carmine tapered stroke under the wordmark
import math
x0,x1,y=(W-tw)/2+10,(W+tw)/2-10,980
for i in range(int(x1-x0)):
    p=i/(x1-x0); th=14*(1-p)**0.8+1.5
    d.line([(x0+i,y-th/2+4*math.sin(p*3)),(x0+i,y+th/2+4*math.sin(p*3))],fill=CARMIN,width=1)
s='Chaque pièce porte un geste.'; f2=manrope(46,b'Regular'); sw=d.textlength(s,font=f2)
d.text(((W-sw)/2,1050),s,font=f2,fill=IVORY)
s2='VEILLE  ·  CONCEPT ORIGINAL'; f3=manrope(28,b'SemiBold'); sw=d.textlength(s2,font=f3)
d.text(((W-sw)/2,1640),s2,font=f3,fill=(150,146,144))
im.save(OUT+'/endcard.png')
# Caption overlays (transparent)
def cap(text,name,y=1560):
    o=Image.new('RGBA',(W,H),(0,0,0,0)); d=ImageDraw.Draw(o); f=manrope(54,b'SemiBold')
    tw=d.textlength(text,font=f)
    d.text(((W-tw)/2+2,y+3),text,font=f,fill=(0,0,0,160))
    d.text(((W-tw)/2,y),text,font=f,fill=IVORY+(255,))
    o.save(OUT+'/'+name+'.png')
cap('Un seul trait.','cap1')
cap('Et la pièce devient quelqu’un.','cap2')
# cover title overlay for the 4:5 cover (1856x2304)
cv=Image.open(OUT+'/../lot/cover.png').convert('RGB'); d=ImageDraw.Draw(cv)
d.text((150,300),'VEILLE',font=barlow(300),fill=IVORY)
d.text((158,640),'Un seul trait.',font=manrope(70,b'Regular'),fill=IVORY)
x0,x1,y=158,700,760
for i in range(x1-x0):
    p=i/(x1-x0); th=12*(1-p)**0.8+1.5
    d.line([(x0+i,y-th/2),(x0+i,y+th/2)],fill=CARMIN,width=1)
d.text((158,2150),'BOJ.ART',font=barlow(80),fill=IVORY)
cv.save(OUT+'/cover_titre.jpg',quality=93)
