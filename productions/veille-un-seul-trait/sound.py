# Bed sonore original synthétisé (aucune source tierce) — BOJ.ART « Veille » V1
import numpy as np, wave, sys, json
cfg=json.loads(sys.argv[2]); out=sys.argv[1]
SR=48000; T=cfg['total']; n=int(SR*T); t=np.arange(n)/SR
rng=np.random.default_rng(7)
def env(a,b,att,rel):
    e=np.zeros(n); i0,i1=int(a*SR),int(b*SR)
    seg=np.arange(i1-i0)/SR; L=(i1-i0)/SR
    e[i0:i1]=np.minimum(1,np.minimum(seg/att,(L-seg)/rel)).clip(0,1); return e
def pink(N):
    w=rng.standard_normal(N); f=np.fft.rfft(w); k=np.arange(len(f)); k[0]=1
    return np.fft.irfft(f/np.sqrt(k),N)
def band(x,lo,hi):
    f=np.fft.rfft(x); fr=np.fft.rfftfreq(len(x),1/SR); f[(fr<lo)|(fr>hi)]=0; return np.fft.irfft(f,len(x))
def norm(x): return x/np.max(np.abs(x)+1e-9)
L=np.zeros(n); R=np.zeros(n)
# 1. room tone + drone (A1/A2, très bas), monte doucement jusqu'au carton
room=norm(band(pink(n),40,400))*0.05
drone=(np.sin(2*np.pi*55*t)+0.5*np.sin(2*np.pi*82.41*t+0.3)+0.25*np.sin(2*np.pi*110*t))*0.06
drone*=(0.6+0.4*np.sin(2*np.pi*0.15*t))*np.clip(t/1.5,0,1)*np.clip((T-t)/1.0,0,1)
L+=room+drone; R+=room*0.9+drone
# 2. pinceau : bruit rose filtré, enveloppe sur la durée du trait, léger panoramique
for a,b in cfg['brush']:
    e=env(a,b,0.08,0.25)
    br=norm(band(pink(n),1800,7000))*0.22*e*(0.8+0.2*np.sin(2*np.pi*9*t))
    L+=br*0.8; R+=br
# 3. montée sub avant l'éveil
a,b=cfg['swell']; e=env(a,b,(b-a)*0.85,(b-a)*0.15)
sw=np.sin(2*np.pi*(38+6*(t-a).clip(0))*t)*0.35*e
air=norm(band(pink(n),300,3000))*0.06*e
L+=sw+air; R+=sw+air
# 4. impact grave au carton
h=cfg['hit']; i0=int(h*SR); k=np.arange(n-i0)/SR
hit=np.zeros(n); hit[i0:]=np.sin(2*np.pi*48*k)*np.exp(-k*2.2)*0.55
tick=np.zeros(n); tick[i0:]=norm(band(pink(n-i0),2000,9000))*np.exp(-k*40)*0.15
L+=hit+tick; R+=hit+tick
st=np.stack([L,R],1); st/=np.max(np.abs(st))/0.6
w=wave.open(out,'wb'); w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
w.writeframes((st*32767).astype('<i2').tobytes()); w.close()
