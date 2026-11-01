#!/usr/bin/env python3
"""BOJ.ART V26: original-poster 2.5D motion-manga, deterministic & reproducible.
Not a true hand-drawn character animation; all pixels derive from the supplied poster.
"""
import os,sys,math,json,argparse,subprocess
from pathlib import Path
import cv2,numpy as np
from PIL import Image,ImageDraw,ImageFont
ap=argparse.ArgumentParser();ap.add_argument('--preview',action='store_true');args=ap.parse_args()
ROOT=Path('/mnt/data/bojart_v26_work')
SOURCE=Path('/mnt/data/a_dramatic_cinematic_high_detail_promotional_col.png')
OUT=Path('/mnt/data')
W,H=(540,960) if args.preview else (720,1280)
S=W/720
FPS=24
BEAT=60/170
SCENE_BEATS=[5,5,4,7,4,6]
SCENE_NAMES=['eyes','back','ink','gallery','details','logo']
CUM=np.cumsum([0]+SCENE_BEATS)*BEAT
DURATION=float(CUM[-1]);N=round(DURATION*FPS)
RNG=np.random.default_rng(262026)
BGR=np.array(Image.open(SOURCE).convert('RGB'))[:,:,::-1].copy()
regions={'eyes':BGR[0:278].copy(),'back':BGR[282:518].copy(),'ink':BGR[524:730].copy(),
'gallery':BGR[755:1095].copy(),'details':BGR[1110:1290].copy(),'logo':BGR[1305:1665].copy()}
fontpath='/usr/share/fonts/opentype/inter/InterDisplay-Black.otf'
fontmed='/usr/share/fonts/opentype/inter/InterDisplay-Medium.otf'

def smooth(x):
 x=np.clip(x,0,1);return x*x*(3-2*x)
def ease(x):
 x=np.clip(x,0,1);return 1-(1-x)**3

def background(img):
 h,w=img.shape[:2];sc=max(W/w,H/h)
 big=cv2.resize(img,(round(w*sc),round(h*sc)),interpolation=cv2.INTER_LINEAR)
 yy=(big.shape[0]-H)//2;xx=(big.shape[1]-W)//2
 b=big[yy:yy+H,xx:xx+W].copy()
 b=cv2.GaussianBlur(b,(0,0),18*S)
 b=(b.astype(np.float32)*.29)
 y,x=np.mgrid[0:H,0:W].astype(np.float32)
 vign=np.clip(1-.29*((x-W*.5)/(W*.68))**2-.34*((y-H*.5)/(H*.66))**2,.4,1)
 b*=vign[:,:,None]
 red=np.exp(-(((x-W*.53)/(W*.56))**2+((y-H*.48)/(H*.56))**2)*2)
 b[:,:,2]+=red*19
 return np.clip(b,0,255).astype(np.uint8)
BGS={name:background(img) for name,img in regions.items()}
Y,X=np.mgrid[0:H,0:W].astype(np.float32)
VIGN=np.clip(1-.24*((X-W*.5)/(W*.66))**2-.25*((Y-H*.50)/(H*.70))**2,.58,1)
# RGB typography on a cached transparent layer.
def title(text,small=None):
 layer=Image.new('RGBA',(W,H),(0,0,0,0));d=ImageDraw.Draw(layer)
 f=ImageFont.truetype(fontpath,round(47*S))
 if text:
  d.text((round(50*S),round(1040*S)),text,font=f,fill=(242,240,239,255))
 if small:
  f2=ImageFont.truetype(fontmed,round(17*S))
  d.text((round(51*S),round(1110*S)),small,font=f2,fill=(216,80,68,255))
 a=np.array(layer)
 return np.dstack([a[:,:,:3][:,:,::-1],a[:,:,3]])
TITLES={'eyes':title('AWAKEN','BOJ.ART / ORIGINAL MOTION MANGA'),
'back':title('BREAK THE FRAME','ONE IMPACT'),
'gallery':title('BEYOND THE FRAME','THE ART BECOMES A WORLD')}
def overlay(bg,rgba,op=1):
 a=rgba[:,:,3:4].astype(np.float32)/255*op
 return np.clip(bg.astype(np.float32)*(1-a)+rgba[:,:,:3].astype(np.float32)*a,0,255).astype(np.uint8)

def panel(img,quad,blur=False):
 h,w=img.shape[:2]
 src=np.float32([[0,0],[w-1,0],[w-1,h-1],[0,h-1]])
 dst=np.float32(quad)*S
 M=cv2.getPerspectiveTransform(src,dst)
 col=cv2.warpPerspective(img,M,(W,H),flags=cv2.INTER_CUBIC,borderMode=cv2.BORDER_CONSTANT)
 mask=cv2.warpPerspective(np.full((h,w),255,np.uint8),M,(W,H),flags=cv2.INTER_LINEAR)
 mask=cv2.GaussianBlur(mask,(0,0),.75*S)
 return np.dstack([col,mask])

def draw_grid(frame,progress):
 # Original BOJ.ART editorial language, but less text than V25.
 cv2.line(frame,(round(38*S),round(48*S)),(round(682*S),round(48*S)),(73,70,82),1,cv2.LINE_AA)
 cv2.line(frame,(round(38*S),round(1190*S)),(round(682*S),round(1190*S)),(61,61,72),1,cv2.LINE_AA)
 cv2.line(frame,(round(38*S),round(1190*S)),(round((38+644*progress)*S),round(1190*S)),(48,43,211),max(2,round(3*S)),cv2.LINE_AA)
 return frame

# Source-pixel eye animation. The eyelid is compressed once, and the hair sways slightly.
EY=regions['eyes'];eyh,eyw=EY.shape[:2]
eyx,eyy=np.meshgrid(np.arange(eyw,dtype=np.float32),np.arange(eyh,dtype=np.float32))
HAIR=np.exp(-((eyx-545)/245)**2)*np.exp(-((eyy-33)/80)**2)
EYE1=np.exp(-((eyx-465)/51)**2-((eyy-97)/16)**2)
EYE2=np.exp(-((eyx-681)/55)**2-((eyy-101)/18)**2)
def eye_source(t):
 blink=np.exp(-((t-.62)/.095)**4)*.90
 sway=2.1*math.sin(2*math.pi*t*.82)
 mapx=eyx+HAIR*sway
 # A narrow local eyelid squeeze, avoiding global face deformation.
 weight=EYE1+EYE2
 mapy=eyy+(eyy-99)*weight*blink*.65
 mapy=np.clip(mapy,0,eyh-1)
 out=cv2.remap(EY,mapx.astype(np.float32),mapy.astype(np.float32),cv2.INTER_LINEAR,borderMode=cv2.BORDER_REFLECT_101)
 if blink>.04:
  # Short eye-close motion: the lid covers the iris with nearby skin pixels,
  # then a dark curved eyelid line is revealed. No generative face changes.
  for cx,cy,rx in [(465,99,52),(681,102,55)]:
   m=np.exp(-((eyx-cx)/rx)**4-((eyy-cy)/19)**4).astype(np.float32)
   m=np.clip(m*blink,0,1)
   lower=out[np.clip((eyy+23).astype(np.int32),0,eyh-1),eyx.astype(np.int32)].astype(np.float32)
   out=np.clip(out.astype(np.float32)*(1-m[...,None])+lower*m[...,None],0,255).astype(np.uint8)
   line=np.zeros_like(out)
   pts=[]
   for xx in range(cx-rx,cx+rx+1,3):
    yy=int(cy+2*math.sin((xx-cx)/rx*math.pi))
    pts.append((xx,yy))
   cv2.polylines(line,[np.array(pts,np.int32)],False,(16,11,16),2,cv2.LINE_AA)
   out=cv2.addWeighted(out,1,line,blink*.85,0)
 return out

def eye_scene(t,d):
 p=t/d
 src=eye_source(t)
 # One-eye extreme close-up (the same poster, no new character).
 left=385+int(28*ease(p));right=565+int(10*ease(p))
 crop=src[:,left:right]
 img=cv2.resize(crop,(W,H),interpolation=cv2.INTER_CUBIC)
 # Controlled eyelight follows the eye rather than a random lens flare.
 y,x=np.mgrid[0:H,0:W].astype(np.float32)
 glint=np.exp(-(((x-W*.43)/(W*.18))**2+((y-H*.34)/(H*.055))**2)*2)
 img[:,:,2]=np.clip(img[:,:,2].astype(np.float32)+glint*(5+11*math.sin(math.pi*p)**2),0,255)
 # A subtle opening from darkness.
 img=(img.astype(np.float32)*(.36+.64*smooth(p*2.8))).astype(np.uint8)
 # Editorial title is smaller and late to preserve the eye.
 if p>.52:
  img=overlay(img,TITLES['eyes'],smooth((p-.52)*4)*.9)
 return img

# Back-shot body deformation: shoulder movement, breathing and a camera push.
BACK=regions['back'];bh,bw=BACK.shape[:2]
bx,by=np.meshgrid(np.arange(bw,dtype=np.float32),np.arange(bh,dtype=np.float32))
TORSO=np.exp(-((bx-490)/105)**2-((by-92)/56)**2)
ARMLEFT=np.exp(-((bx-402)/50)**2-((by-145)/75)**2)
ARMRIGHT=np.exp(-((bx-577)/50)**2-((by-145)/75)**2)
def back_source(t):
 breath=math.sin(2*math.pi*t*.58)
 mapx=bx+(bx-490)*TORSO*.007*breath+ARMLEFT*1.8*breath-ARMRIGHT*1.8*breath
 mapy=by+TORSO*1.3*breath
 return cv2.remap(BACK,mapx.astype(np.float32),mapy.astype(np.float32),cv2.INTER_LINEAR,borderMode=cv2.BORDER_REFLECT_101)
# One and only one burst of original glass: physically decaying particles in depth layers.
SHARDS=[]
for i in range(15):
 angle=2*math.pi*(i/15)+RNG.uniform(-.20,.20)
 vel=150+RNG.uniform(40,230)
 size=4+RNG.uniform(2,12)
 SHARDS.append((angle,vel,size,i%3,RNG.uniform(-.06,.06)))
def glass(frame,t):
 p=(t-.63)/.85
 if p<0 or p>1:return frame
 layer=np.zeros_like(frame)
 cx,cy=W*.50,H*.48
 for ang,vel,size,depth,offset in SHARDS:
  pp=np.clip(p+offset,0,1)
  r=(70+vel*pp*(1+depth*.35))*S
  x=cx+math.cos(ang)*r;y=cy+math.sin(ang)*r
  a=size*S*(1+pp*.3)
  pts=np.array([[x+math.cos(ang)*a*1.5,y+math.sin(ang)*a*1.5],
                [x+math.cos(ang+2.1)*a,y+math.sin(ang+2.1)*a],
                [x+math.cos(ang-2.1)*a,y+math.sin(ang-2.1)*a]],np.int32)
  cv2.polylines(layer,[pts],True,(180,208,245),max(1,round((1+depth*.3)*S)),cv2.LINE_AA)
  if depth==2:
   cv2.line(layer,(int(x),int(y)),(int(x-math.cos(ang)*42*S),int(y-math.sin(ang)*42*S)),(25,32,184),max(1,round(2*S)),cv2.LINE_AA)
 return cv2.addWeighted(frame,1,layer,(1-p)**.65*.78,0)

def back_scene(t,d):
 p=t/d
 img=BGS['back'].copy()
 src=back_source(t)
 crop=src[:,295:690]
 # Perspective-stable panel with a motivated dolly toward the figure.
 z=1+.085*ease(p)
 quad=[[-45-25*p,245-25*p],[765+20*p,250-30*p],[758+30*p,860+40*p],[-38-20*p,850+35*p]]
 # Crop retains the sculpture and original environmental glass.
 sharp=panel(crop,quad)
 img=overlay(img,sharp)
 img=glass(img,t)
 # One optical camera recoil on the single glass break.
 shock=max(0,1-abs(t-.70)/.12)
 if shock:
  M=cv2.getRotationMatrix2D((W*.5,H*.5),0,1+.018*shock)
  img=cv2.warpAffine(img,M,(W,H),borderMode=cv2.BORDER_REFLECT_101)
 if p>.35:img=overlay(img,TITLES['back'],smooth((p-.35)*3)*.88)
 return img
# A few original ink brush arcs, deliberately restrained.
LINES=[]
for i in range(21):
 a=2*math.pi*i/21+RNG.uniform(-.06,.06)
 LINES.append((a,RNG.uniform(.7,1.35),i%5))
def speed_lines(frame,t,strength=.35):
 layer=np.zeros_like(frame)
 cx,cy=W*.51,H*.47
 for a,v,k in LINES:
  r1=(150+30*math.sin(t*8+k))*S;r2=(460+130*v)*S
  p1=(int(cx+math.cos(a)*r1),int(cy+math.sin(a)*r1))
  p2=(int(cx+math.cos(a)*r2),int(cy+math.sin(a)*r2))
  col=(240,237,230) if k%3 else (25,37,216)
  cv2.line(layer,p1,p2,col,max(1,round((1.5 if k%3 else 3)*S)),cv2.LINE_AA)
 return cv2.addWeighted(frame,1,layer,strength,0)

def ink_scene(t,d):
 p=t/d
 img=BGS['ink'].copy()
 # The same artwork is split into two panels travelling in opposing directions.
 left=regions['ink'][:,0:460];right=regions['ink'][:,440:941]
 leftq=[[-95+70*p,235],[460+50*p,190],[450+65*p,735],[-90+75*p,780]]
 rightq=[[265-70*p,360],[790-85*p,320],[800-80*p,830],[265-70*p,875]]
 img=overlay(img,panel(left,leftq))
 img=overlay(img,panel(right,rightq),.94)
 if .10<p<.90:
  img=speed_lines(img,t,.22+.22*math.sin(math.pi*p)**2)
 # Manga 2-frame black/white snap with no new character.
 if .46<p<.55:
  gray=cv2.cvtColor(img,cv2.COLOR_BGR2GRAY)
  edges=cv2.Canny(gray,65,140)
  dark=gray<100
  graphic=np.full_like(img,(12,9,12))
  graphic[~dark]=(30,22,150)
  graphic[edges>0]=(235,235,241)
  img=cv2.addWeighted(img,.28,graphic,.72,0)
 return img

def gallery_scene(t,d):
 p=t/d
 img=BGS['gallery'].copy()
 # A spatially anchored orbit-like camera move around the central sculpture.
 src=regions['gallery'][:,255:700]
 shift=35*math.sin(math.pi*p)
 quad=[[-80+shift,145-15*p],[800+shift,185-25*p],[775-shift,905+22*p],[-60-shift,870+28*p]]
 img=overlay(img,panel(src,quad))
 # Light moves through architecture, never glass or decorative lightning.
 sweep_x=(W*.12+W*.8*p)
 band=np.exp(-((X-sweep_x)/(W*.12))**2)*np.clip((Y-H*.21)/(H*.75),0,1)
 img[:,:,2]=np.clip(img[:,:,2].astype(np.float32)+band*15,0,255)
 if p>.46:img=overlay(img,TITLES['gallery'],smooth((p-.46)*3)*.85)
 return img

DETAIL_NAMES=['POWER','BEAUTY','SOUL']
DETAIL_CROPS=[regions['details'][:,0:315],regions['details'][:,315:627],regions['details'][:,627:941]]
DETAIL_TITLES=[]
for i,name in enumerate(DETAIL_NAMES):
 layer=Image.new('RGBA',(W,H),(0,0,0,0));d=ImageDraw.Draw(layer)
 f=ImageFont.truetype(fontpath,round(84*S))
 d.text((round(45*S),round(920*S)),name,font=f,fill=(242,239,235,255))
 a=np.array(layer);DETAIL_TITLES.append(np.dstack([a[:,:,:3][:,:,::-1],a[:,:,3]]))
def detail_scene(t,d):
 p=t/d
 which=min(2,int(p*3));sub=(p*3)%1
 img=BGS['details'].copy()
 crop=DETAIL_CROPS[which]
 quad=[[-80+15*sub,260-25*sub],[790+15*sub,265-35*sub],[770-15*sub,790+35*sub],[-60-15*sub,800+30*sub]]
 img=overlay(img,panel(crop,quad))
 img=overlay(img,DETAIL_TITLES[which],smooth(sub*5))
 if sub<.14:
  # One dry ink frame at each new detail, not another glass shatter.
  gray=cv2.cvtColor(img,cv2.COLOR_BGR2GRAY)
  edges=cv2.Canny(gray,75,165)
  graphic=np.full_like(img,(13,11,12))
  graphic[gray>95]=(25,24,146)
  graphic[edges>0]=(235,237,244)
  img=cv2.addWeighted(img,1-smooth(sub/.14)*.82,graphic,(1-smooth(sub/.14))*.82,0)
 return img

def logo_scene(t,d):
 p=t/d
 img=BGS['logo'].copy()
 # The original BOJ.ART artwork/logo remains untouched and legible.
 src=regions['logo'][:,125:810]
 z=1.04-.045*ease(p)
 quad=[[-55+35*p,220-15*p],[780-35*p,240-20*p],[775-35*p,830+10*p],[-45+35*p,820+12*p]]
 img=overlay(img,panel(src,quad))
 # Crimson circular halo, anchored behind the logo.
 dist=np.sqrt(((X-W*.50)/(W*.92))**2+((Y-H*.48)/(H*.85))**2)
 ring=np.exp(-((dist-.52)/.035)**2)
 img[:,:,2]=np.clip(img[:,:,2].astype(np.float32)+ring*(16+6*math.sin(p*math.pi)),0,255)
 # Final deceleration, no unnecessary motion after the logo resolves.
 if p>.80:img=(img.astype(np.float32)*(1-.12*smooth((p-.80)/.20))).astype(np.uint8)
 return img

def render_scene(name,t,d):
 if name=='eyes':return eye_scene(t,d)
 if name=='back':return back_scene(t,d)
 if name=='ink':return ink_scene(t,d)
 if name=='gallery':return gallery_scene(t,d)
 if name=='details':return detail_scene(t,d)
 return logo_scene(t,d)

def transition(a,b,progress,mode):
 p=smooth(progress)
 if mode=='ink':
  threshold=(-.30+1.70*p)*W
  noise=5*S*np.sin((Y*.07+X*.015))
  edge=X+.32*Y+noise
  m=np.clip((threshold-edge)/(15*S),0,1)
 elif mode=='vertical':
  edge=Y+.25*X
  threshold=(-.2+1.6*p)*H
  m=np.clip((threshold-edge)/(15*S),0,1)
 elif mode=='flash':
  m=np.full((H,W),p,np.float32)
  if .42<progress<.65:
   a=cv2.convertScaleAbs(a,alpha=1.2,beta=12)
 else:
  m=np.full((H,W),p,np.float32)
 return np.clip(a.astype(np.float32)*(1-m[...,None])+b.astype(np.float32)*m[...,None],0,255).astype(np.uint8)

# Fine-grain color finishing, with deliberate high dynamic contrast.
NOISE=RNG.standard_normal((H,W)).astype(np.float32)
GRAIN=.7 if not args.preview else .3
OUTFILE=OUT/('BOJART_V26_PREVIEW_SILENT.mp4' if args.preview else 'BOJART_V26_SILENT.mp4')
cmd=['ffmpeg','-hide_banner','-loglevel','error','-y','-f','rawvideo','-pix_fmt','bgr24','-s',f'{W}x{H}','-r',str(FPS),'-i','-','-an','-c:v','libx264','-preset','veryfast' if args.preview else 'fast','-crf','23' if args.preview else '18','-pix_fmt','yuv420p','-movflags','+faststart',str(OUTFILE)]
proc=subprocess.Popen(cmd,stdin=subprocess.PIPE)
CONTACT=[];scene_indices=[]
try:
 for i in range(N):
  t=i/FPS
  si=int(np.searchsorted(CUM,t,side='right')-1);si=min(si,len(SCENE_NAMES)-1)
  name=SCENE_NAMES[si];local=t-CUM[si];d=CUM[si+1]-CUM[si]
  frame=render_scene(name,local,d)
  # Fast intentional wipes, not dissolves at every cut.
  width=.15
  if si<len(SCENE_NAMES)-1 and d-local<width:
   nxt=render_scene(SCENE_NAMES[si+1],0,CUM[si+2]-CUM[si+1])
   mode=['ink','flash','ink','vertical','fade'][si]
   frame=transition(frame,nxt,1-(d-local)/width,mode)
  frame=np.clip(frame.astype(np.float32)*VIGN[:,:,None]+NOISE[:,:,None]*GRAIN,0,255).astype(np.uint8)
  frame=draw_grid(frame,t/DURATION)
  proc.stdin.write(frame.tobytes())
  if i%12==0:
   im=Image.fromarray(cv2.cvtColor(frame,cv2.COLOR_BGR2RGB));im.thumbnail((180,320))
   CONTACT.append((t,im))
finally:
 proc.stdin.close()
rc=proc.wait()
if rc:raise RuntimeError(f'FFmpeg exited {rc}')
cols=5;rows=math.ceil(len(CONTACT)/cols)
contact=Image.new('RGB',(cols*185,rows*345),'#141414');draw=ImageDraw.Draw(contact)
for j,(t,im) in enumerate(CONTACT):
 x=(j%cols)*185+(185-im.width)//2;y=(j//cols)*345+23
 contact.paste(im,(x,y));draw.text(((j%cols)*185+5,(j//cols)*345+5),f'{t:.2f}s',fill='white')
contact.save(OUT/('BOJART_V26_PREVIEW_CONTACT.jpg' if args.preview else 'BOJART_V26_CONTACT.jpg'),quality=76)
(OUT/'BOJART_V26_EDIT_DECISIONS.json').write_text(json.dumps({'duration':DURATION,'frames':N,'fps':FPS,'scenes':SCENE_NAMES,'beats':SCENE_BEATS,'scene_start_seconds':list(map(float,CUM[:-1])),'source':SOURCE.name,'changes':['animated single eye blink and hair sway','subtle back/shoulder breathing warp','one glass impact','two-layer ink manga motion','gallery parallax light sweep','3 editorial detail cuts','original BOJ.ART artwork logo'], 'limitations':['motion manga 2.5D, not hand-drawn full animation','concept poster character is not verified physical sculpture']},indent=2))
print(json.dumps({'file':str(OUTFILE),'frames':N,'seconds':DURATION,'size':OUTFILE.stat().st_size,'preview':args.preview}))
