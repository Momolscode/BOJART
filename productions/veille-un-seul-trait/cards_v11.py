# Habillage « Veille — Un seul trait » V1.1 (prête à poster)
# Tous les textes tiennent dans la zone visible commune à Reels, TikTok et Shorts (1080 x 1920) :
#   x 120-888 et y 288-1248 ; sous y = 840, x 120-780 (colonne de boutons TikTok).
# Sorties : v11_mention.png, v11_cap1.png, v11_cap2.png (calques RGBA), v11_endcard.png,
#           v11_cover_9x16.jpg et v11_layout.json (boîtes des textes, pour le contrôle).
# Usage : python3 cards_v11.py DOSSIER_POLICES DOSSIER_BUILD
import sys, json, math
from PIL import Image, ImageDraw, ImageFont, ImageFilter

F, OUT = sys.argv[1], sys.argv[2]
W, H = 1080, 1920
CHAR = (9, 9, 13); IVORY = (244, 240, 237); CARMIN = (241, 58, 84); GREY = (150, 146, 144)
LEFT = 120                      # marge gauche commune
MENTION = 'Généré par IA'   # libellé court : ne recouvre pas la tête de Veille dans le plan B (x >= 443)
layout = {}

def barlow(sz): return ImageFont.truetype(F + '/BarlowCondensed-SemiBold.ttf', sz)
def manrope(sz, w=b'Medium'):
    f = ImageFont.truetype(F + '/Manrope.ttf', sz); f.set_variation_by_name(w); return f

def stroke(d, x0, x1, y, th0=14):
    # Trait carmin effilé : seul usage de la couleur (« le carmin n'existe que dans le geste »)
    for i in range(int(x1 - x0)):
        p = i / (x1 - x0); th = th0 * (1 - p) ** 0.8 + 1.5; yy = y + 4 * math.sin(p * 3)
        d.line([(x0 + i, yy - th / 2), (x0 + i, yy + th / 2)], fill=CARMIN, width=1)

def tracked(d, xy, text, font, fill, track):
    # Capitales espacées ; renvoie la largeur
    x, y = xy
    for ch in text:
        d.text((x, y), ch, font=font, fill=fill); x += d.textlength(ch, font=font) + track
    return x - track - xy[0]

def tracked_width(d, text, font, track):
    return sum(d.textlength(ch, font=font) for ch in text) + track * (len(text) - 1)

def bbox_of(img):
    return list(img.getchannel('A').point(lambda a: 255 if a > 8 else 0).getbbox())

def caption(name, lines, y_top, size=60, lh=74):
    # Texte ivoire aligné à gauche, halo charbon derrière les lettres (pas de bandeau).
    # Halo serré + voile large : contraste mesuré sur la peau claire du plan A ≥ 6:1 en médiane
    # et ≥ 3:1 sur les 10 % les plus clairs du pourtour (seuil WCAG du grand texte).
    f = manrope(size, b'SemiBold')
    txt = Image.new('RGBA', (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(txt)
    for i, s in enumerate(lines): d.text((LEFT, y_top + i * lh), s, font=f, fill=IVORY + (255,))
    box = bbox_of(txt); A = txt.getchannel('A'); out = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    for grow, blur, alpha in [(13, 8, 0.92), (1, 30, 0.45)]:
        halo = Image.new('RGBA', (W, H), CHAR + (0,))
        a = (A.filter(ImageFilter.MaxFilter(grow)) if grow > 1 else A).filter(ImageFilter.GaussianBlur(blur))
        halo.putalpha(a.point(lambda v, k=alpha: int(v * k))); out = Image.alpha_composite(out, halo)
    out = Image.alpha_composite(out, txt); out.save(f'{OUT}/{name}.png')
    layout[name] = {'text_bbox': box, 'halo_bbox': bbox_of(out)}

# 1. Mention IA permanente (de la première à la dernière image), en haut à gauche de la zone visible
m = Image.new('RGBA', (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(m)
f = manrope(36, b'SemiBold'); tw = d.textlength(MENTION, font=f)
asc, desc = f.getmetrics(); px, py, y0 = 20, 11, 300
d.rounded_rectangle([LEFT, y0, LEFT + tw + 2 * px, y0 + asc + desc + 2 * py], radius=(asc + desc) // 2 + py, fill=CHAR + (165,))
d.text((LEFT + px, y0 + py), MENTION, font=f, fill=IVORY + (242,))
m.save(f'{OUT}/v11_mention.png'); layout['v11_mention'] = {'text_bbox': bbox_of(m)}
mention_bottom = layout['v11_mention']['text_bbox'][3]

# 2. Sous-titres : accroche dès la première image, sous la mention ; phrase 2 en bas de la zone visible
caption('v11_cap1', ['Un seul trait.'], mention_bottom + 34)
caption('v11_cap2', ['Et la pièce', 'devient quelqu’un.'], 1084)

# 3. Carton final (2 s) : bloc principal au-dessus de y = 840, pied étroit dessous
im = Image.new('RGB', (W, H), CHAR); d = ImageDraw.Draw(im); boxes = []
t = 'BOJ.ART'; f1 = barlow(210); x0, yb0, x1, yb1 = d.textbbox((0, 0), t, font=f1); tw = x1 - x0
top = 470; d.text(((W - tw) / 2 - x0, top - yb0), t, font=f1, fill=IVORY); boxes.append([(W - tw) / 2, top, (W + tw) / 2, top + yb1 - yb0])
stroke(d, (W - tw) / 2 + 10, (W + tw) / 2 - 10, top + (yb1 - yb0) + 48); boxes.append([(W - tw) / 2 + 10, top + (yb1 - yb0) + 38, (W + tw) / 2 - 10, top + (yb1 - yb0) + 60])
s = 'Chaque pièce porte un geste.'; f2 = manrope(46, b'Regular'); x0, sy0, x1, sy1 = d.textbbox((0, 0), s, font=f2); sw = x1 - x0
ty = top + (yb1 - yb0) + 96; d.text(((W - sw) / 2 - x0, ty - sy0), s, font=f2, fill=IVORY); boxes.append([(W - sw) / 2, ty, (W + sw) / 2, ty + sy1 - sy0])
f3 = manrope(26, b'SemiBold')
for i, s in enumerate(['VEILLE  ·  CONCEPT ORIGINAL', 'PAS ENCORE SCULPTÉE']):
    sw = tracked_width(d, s, f3, 3); fy = 1070 + i * 42
    tracked(d, ((W - sw) / 2, fy), s, f3, GREY, 3); boxes.append([(W - sw) / 2, fy + 4, (W + sw) / 2, fy + 30])
im.save(f'{OUT}/v11_endcard.png'); layout['v11_endcard'] = {'text_boxes': [[round(v) for v in b] for b in boxes]}

# 4. Couverture 9:16 : image 4:5 de couverture au centre (survit aux recadrages 3:4 et 4:5), fondue dans le charbon
cv = Image.open(OUT + '/../lot/cover.png').convert('RGB'); ch = round(cv.size[1] * W / cv.size[0])
cv = cv.resize((W, ch), Image.LANCZOS); oy = (H - ch) // 2
base = Image.new('RGB', (W, H), CHAR); base.paste(cv, (0, oy))
fade = Image.new('L', (W, H), 255); fd = ImageDraw.Draw(fade)
for k in range(140):   # fondu haut et bas sur 140 px pour effacer les jointures
    a = int(255 * (k / 140) ** 1.6); fd.line([(0, oy + k), (W, oy + k)], fill=a); fd.line([(0, oy + ch - 1 - k), (W, oy + ch - 1 - k)], fill=a)
fd.rectangle([0, 0, W, oy], fill=0); fd.rectangle([0, oy + ch, W, H], fill=0)
cover = Image.composite(base, Image.new('RGB', (W, H), CHAR), fade); d = ImageDraw.Draw(cover)
ty = oy + 150; d.text((LEFT - 30, ty), 'VEILLE', font=barlow(180), fill=IVORY)
d.text((LEFT - 24, ty + 222), 'Un seul trait.', font=manrope(44, b'Regular'), fill=IVORY); stroke(d, LEFT - 24, LEFT + 300, ty + 296, 10)
d.text((LEFT - 24, oy + ch - 230), 'BOJ.ART', font=barlow(56), fill=IVORY)
cm = Image.new('RGBA', (W, H), (0, 0, 0, 0)); dm = ImageDraw.Draw(cm); fm = manrope(30, b'SemiBold'); lab = 'Image générée par IA'
lw = dm.textlength(lab, font=fm); a2, d2 = fm.getmetrics(); ly = oy + ch - 150
dm.rounded_rectangle([LEFT - 24, ly, LEFT - 24 + lw + 36, ly + a2 + d2 + 18], radius=(a2 + d2) // 2 + 9, fill=CHAR + (170,))
dm.text((LEFT - 6, ly + 9), lab, font=fm, fill=IVORY + (242,))
cover = Image.alpha_composite(cover.convert('RGBA'), cm).convert('RGB')
cover.save(f'{OUT}/v11_cover_9x16.jpg', quality=94)
layout['cover'] = {'image_band': [0, oy, W, oy + ch]}

json.dump(layout, open(f'{OUT}/v11_layout.json', 'w'), indent=1)
print(json.dumps(layout))
