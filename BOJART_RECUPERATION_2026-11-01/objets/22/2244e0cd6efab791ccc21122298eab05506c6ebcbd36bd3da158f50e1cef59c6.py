from pathlib import Path
import numpy as np, math, json
from scipy import signal
from scipy.io import wavfile
P=Path('/mnt/data/bojart_manga')
SR=48000;D=14.5;N=round(D*SR)
RNG=np.random.default_rng(20261030)
tracks={name:np.zeros((N,2),np.float64) for name in ['drums','bass','guitars','lead','atmosphere','sfx']}
BPM=170;BEAT=60/BPM

def add(t,s,track='sfx',pan=0,amp=1):
 i=round(t*SR)
 if i<0 or i>=N:return
 n=min(len(s),N-i)
 if n<=0:return
 s=s[:n]*amp
 tracks[track][i:i+n,0]+=s*math.sqrt((1-pan)/2)
 tracks[track][i:i+n,1]+=s*math.sqrt((1+pan)/2)

def band(x,lo,hi):
 return signal.sosfilt(signal.butter(2,[lo,hi],fs=SR,btype='bandpass',output='sos'),x)
def lp(x,hi):
 return signal.sosfilt(signal.butter(2,hi,fs=SR,btype='lowpass',output='sos'),x)
def hp(x,lo):
 return signal.sosfilt(signal.butter(2,lo,fs=SR,btype='highpass',output='sos'),x)

def kick(t,v=1):
 u=np.arange(int(.38*SR))/SR
 freq=45+108*np.exp(-u/.024)
 phase=2*np.pi*np.cumsum(freq)/SR
 body=np.sin(phase)*np.exp(-u*13)*.31
 click=band(RNG.standard_normal(len(u)),650,7800)*np.exp(-u*95)*.058
 add(t,(body+click)*v,'drums')
def snare(t,v=1):
 u=np.arange(int(.22*SR))/SR
 n=band(RNG.standard_normal(len(u)),430,10000)*np.exp(-u*22)*.13
 body=np.sin(2*np.pi*195*u)*np.exp(-u*32)*.060
 add(t,(n+body)*v,'drums',pan=.12)
def hat(t,v=.6,pan=.2,open=False):
 dur=.17 if open else .07
 u=np.arange(int(dur*SR))/SR
 n=hp(RNG.standard_normal(len(u)),6700)*np.exp(-u*(28 if open else 100))*.037
 add(t,n*v,'drums',pan)
def tom(t,f=110,v=.65,pan=0):
 u=np.arange(int(.26*SR))/SR
 freq=f*(1-.25*(1-np.exp(-u/.045)))
 phase=2*np.pi*np.cumsum(freq)/SR
 add(t,np.sin(phase)*np.exp(-u*15)*.20*v,'drums',pan)
def bass(t,f,dur,v=.8):
 u=np.arange(int((dur+.12)*SR))/SR
 ph=2*np.pi*f*u
 raw=.45*signal.sawtooth(ph)+.40*np.sin(ph)+.15*signal.square(ph)
 dist=np.tanh(raw*2.7)
 env=np.minimum(1,u/.014)*np.minimum(1,np.maximum(0,(dur+.12-u)/.10))*np.exp(-u*.45)
 add(t,lp(dist,680)*env*.12*v,'bass')
 add(t,np.sin(ph)*env*.11*v,'bass')
def guitar(t,f,dur=.38,v=.75):
 u=np.arange(int((dur+.13)*SR))/SR
 ph=2*np.pi*f*u
 tone=np.zeros_like(u)
 for j,ratio in enumerate([1,1.498307,2]):
  pp=ph*ratio
  tone+=(signal.sawtooth(pp)+.18*signal.sawtooth(pp*2))*(.45 if j==0 else .30)
 tone=band(np.tanh(tone*2.9),100,4000)
 env=np.minimum(1,u/.008)*np.minimum(1,np.maximum(0,(dur+.13-u)/.09))*np.exp(-u*.7)
 add(t,tone*env*.062*v,'guitars',pan=-.42)
 add(t+.008,tone*env*.060*v,'guitars',pan=.43)
def lead(t,f,dur=.26,v=.7):
 u=np.arange(int((dur+.15)*SR))/SR
 vib=1+.0018*np.sin(2*np.pi*5.2*u)
 ph=2*np.pi*f*np.cumsum(vib)/SR
 tone=.67*np.sin(ph)+.21*np.sin(2*ph)+.12*np.sin(3*ph)
 env=np.minimum(1,u/.01)*np.minimum(1,np.maximum(0,(dur+.15-u)/.10))*np.exp(-u*.5)
 add(t,lp(tone,4700)*env*.075*v,'lead',pan=.1)
 add(t+.08,lp(tone,4000)*env*.018*v,'lead',pan=-.25)
def pad(t,f,dur,v=.5):
 u=np.arange(int(dur*SR))/SR
 x=.65*np.sin(2*np.pi*f*u)+.25*np.sin(2*np.pi*f*1.498307*u)+.18*np.sin(2*np.pi*f*2*u)
 env=np.sin(np.pi*u/dur)**1.2
 add(t,x*env*.045*v,'atmosphere',pan=-.1)
def whoosh(t,dur=.4,v=.6,pan=0):
 u=np.arange(int(dur*SR))/SR
 n=band(RNG.standard_normal(len(u)),220,6500)
 add(t,n*np.sin(np.pi*u/dur)**2*.046*v,'sfx',pan)
def boom(t,v=1):
 u=np.arange(int(.70*SR))/SR
 f=65-35*(1-np.exp(-u/.07))
 ph=2*np.pi*np.cumsum(f)/SR
 s=np.sin(ph)*np.exp(-u*8)*.30
 snap=band(RNG.standard_normal(len(u)),400,7000)*np.exp(-u*65)*.065
 add(t,(s+snap)*v,'sfx')
def glass_event(t):
 boom(t,.9)
 for i in range(13):
  at=t+.07+RNG.uniform(0,.52)
  dur=RNG.uniform(.08,.26)
  u=np.arange(int(dur*SR))/SR
  f=RNG.uniform(1700,6600)
  x=(np.sin(2*np.pi*f*u)+.3*np.sin(2*np.pi*f*1.48*u))*np.exp(-u*RNG.uniform(15,38))*.017
  add(at,x,'sfx',pan=RNG.uniform(-.8,.8))
# Act I: isolated heartbeat and rising atmosphere.
pad(0.0,41.2,3.6,.65)
for t in [.42,1.16]:boom(t,.17)
lead(.70,329.63,.55,.28)
lead(1.24,392,.44,.32)
# Act II: one controlled break and percussion build.
glass_event(1.88)
whoosh(1.58,.44,.75,-.25)
for i,t in enumerate(np.arange(2.25,4.08,BEAT)):
 if i%2==0:kick(float(t),.55+.045*i)
 else:snare(float(t),.36+.05*i)
 if i>1:hat(float(t+BEAT/2),.34)
for i,t in enumerate([3.25,3.48,3.68,3.87]):tom(t,130-i*12,.30+.11*i,pan=-.4+.2*i)
whoosh(3.78,.38,.8,.25)
# Act III: original guitar/synth anime motif, not an existing opening.
roots=[82.407,65.406,73.416,61.735,82.407,65.406,73.416,61.735]
start=4.10
for k,t in enumerate(np.arange(start,9.0,BEAT)):
 bar=k//4;beat=k%4
 f=roots[min(bar,len(roots)-1)]
 kick(float(t),1 if beat==0 else .65)
 if beat in [1,3]:snare(float(t),.85)
 for j in range(2):hat(float(t+j*BEAT/2),.52,pan=(-.28 if j else .28),open=(beat==3 and j==1))
 bass(float(t),f/2,BEAT*.83,.83)
 guitar(float(t),f,.22,.85 if beat in [0,2] else .55)
 if beat==0:pad(float(t),f/2,4*BEAT,.24)
melody=[(0,659.25),(.5,783.99),(1,880.0),(1.5,783.99),(2,739.99),(2.5,587.33),(3,659.25),(3.5,493.88)]
for bar in range(3):
 for off,f in melody:
  t=start+bar*4*BEAT+off*BEAT
  if t<9.1:lead(t,f,BEAT*.40,.78 if bar>0 else .65)
boom(4.10,.72)
whoosh(5.78,.55,.6,-.3)
boom(6.15,.52)
# Act IV: gallery breathes and gains depth.
pad(6.20,41.2,3.0,.6)
whoosh(7.30,.85,.32,.20)
# Act V: power/beauty/soul triptych, three different accents.
for i,t in enumerate([9.10,9.90,10.70]):
 boom(t,.57+.09*i)
 whoosh(t-.16,.25,.45,(-.4+i*.4))
 guitar(t,82.407 if i==0 else (65.406 if i==1 else 73.416),.42,.62)
# Act VI: final logo, sub impact and original resolving chord.
whoosh(11.18,.48,.68,-.1)
boom(11.50,.92)
pad(11.47,41.203,2.65,.88)
for f,a in [(82.407,.05),(123.47,.03),(164.814,.022),(246.942,.009)]:
 u=np.arange(int(2.5*SR))/SR
 x=np.sin(2*np.pi*f*u)*np.exp(-u*1.5)*a
 add(11.60,x,'atmosphere')
lead(12.0,659.25,.6,.42)
lead(12.67,493.88,.68,.36)
# One short break before the final logo; dynamics over raw loudness.
raw=sum(tracks.values())
t=np.arange(N)/SR
vol=np.ones(N)
vol[(t>=0)&(t<1.6)]*=.55
vol[(t>=5.8)&(t<6.12)]*=.52
mask=(t>=11.24)&(t<11.5)
vol[mask]=np.interp(t[mask],[11.24,11.43,11.5],[1,.09,.03])
raw*=vol[:,None]
raw[-int(.22*SR):]*=np.linspace(1,0,int(.22*SR))[:,None]
raw=np.tanh(raw*1.12)
peak=float(np.max(np.abs(raw)))
raw*=min(1,.88/max(peak,1e-9))
path=P/'BOJART_MANGA_ORIGINAL_SCORE.wav'
wavfile.write(path,SR,(raw*32767).astype('<i2'))
for name,stem in tracks.items():
 stem=np.tanh(stem)
 pk=float(np.max(np.abs(stem)))
 stem*=min(1,.85/max(pk,1e-9))
 wavfile.write(P/f'STEM_{name}.wav',SR,(stem*32767).astype('<i2'))
print(json.dumps({'audio':str(path),'seconds':D,'bpm':BPM,'peak':float(np.max(np.abs(raw))),'rms':float(np.sqrt(np.mean(raw**2))),'original_music':True,'glass_break_count':1}))
