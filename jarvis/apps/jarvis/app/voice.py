"""Local-only optional speech transcription. No automatic model downloads.
Input is 16-bit mono PCM WAV, <=15s; no audio is written to the project database.
"""
from __future__ import annotations
import array, importlib.util, io, math, sys, threading, wave
from pathlib import Path
from core import Rejected

MAX_SECONDS=15
MAX_BYTES=500000

def validate_audio(raw):
    if not isinstance(raw,bytes) or not 44<len(raw)<=MAX_BYTES:raise Rejected('Audio absent ou trop volumineux.')
    try:
        with wave.open(io.BytesIO(raw),'rb') as w:
            channels,width,rate,frames=w.getnchannels(),w.getsampwidth(),w.getframerate(),w.getnframes()
            if channels!=1 or width!=2 or rate!=16000 or w.getcomptype()!='NONE':
                raise Rejected('WAV PCM mono 16 bits / 16 kHz requis.')
            seconds=frames/rate
            if not .25<=seconds<=MAX_SECONDS:raise Rejected('Audio limité à 0,25–15 secondes.')
            pcm=w.readframes(frames)
            if len(pcm)!=frames*2:raise Rejected('Audio tronqué.')
    except (wave.Error,EOFError) as e:raise Rejected('WAV non valide.') from e
    values=array.array('h');values.frombytes(pcm)
    if sys.byteorder!='little':values.byteswap()
    peak=max(abs(x) for x in values)/32768
    rms=math.sqrt(sum((x/32768)**2 for x in values)/len(values))
    return {'seconds':round(seconds,3),'rate':rate,'peak':round(peak,5),'rms':round(rms,5),
            'silence':rms<.003,'clipped':sum(abs(x)>=32700 for x in values)/len(values)>.01}

class LocalVoice:
    def __init__(self,config,loader=None):
        self.config=config;self.model=None;self.lock=threading.Lock();self.loader=loader
    def status(self):
        path=self.config.get('model_dir','')
        if not self.config.get('enabled'):return {'status':'disabled','message':'Micro désactivé ; aucun enregistrement.'}
        if not self.loader and importlib.util.find_spec('faster_whisper') is None:
            return {'status':'missing_runtime','message':'Transcripteur local absent ; aucun téléchargement automatique.'}
        if not path or not all((Path(path)/name).is_file() for name in ('model.bin','config.json','tokenizer.json')):
            return {'status':'missing_weights','message':'Poids multilingues locaux à préparer.'}
        return {'status':'available','message':'Fichiers présents ; moteur chargé au premier essai. Qualité non attestée.',
                'engine':'faster-whisper','device':'cpu','loaded':self.model is not None,'microphone_tested':False}
    def transcribe(self,raw):
        quality=validate_audio(raw)
        if quality['silence']:
            return {'status':'no_speech','text':'','quality':quality,'audio_stored':False,'executed':False}
        if quality['clipped']:raise Rejected('Le son sature. Éloignez le microphone puis recommencez.')
        if self.status()['status']!='available':raise Rejected(self.status()['message'])
        if not self.lock.acquire(blocking=False):raise Rejected('Une transcription est déjà en cours.')
        try:
            if self.model is None:
                if self.loader:self.model=self.loader()
                else:
                    from faster_whisper import WhisperModel
                    self.model=WhisperModel(str(Path(self.config['model_dir']).resolve()),device='cpu',
                           compute_type='int8',cpu_threads=4,local_files_only=True)
            segments,info=self.model.transcribe(io.BytesIO(raw),language='fr',beam_size=3,
                        condition_on_previous_text=False,vad_filter=True,word_timestamps=False)
            # Iterate inside the lock: faster-whisper segments is a lazy generator.
            text=' '.join(s.text.strip() for s in segments).strip()
            if len(text)>500:raise Rejected('Phrase trop longue : reformulez en une demande courte.')
            return {'status':'draft' if text else 'no_speech','text':text,'language':'fr',
                    'quality':quality,'engine':'faster-whisper','audio_stored':False,
                    'executed':False,'needs_review':True}
        finally:self.lock.release()
