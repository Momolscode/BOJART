"""HTTP boundary for M06. Slow recognition/decision never holds the workspace lock."""
import json, time
from urllib.parse import parse_qs
from core import Rejected, IntegrityError
from dialogue import strict_json
from voice import MAX_BYTES

GETS={'/api/jarvis/status','/api/jarvis/turn','/api/tower/events','/tower_voice.js'}
POSTS={'/api/jarvis/turn','/api/jarvis/confirm','/api/jarvis/cancel','/api/voice/lease','/api/voice/transcribe','/api/transcribe'}


def get(handler, parsed, root):
    h=handler
    if not h.check_host():return
    if not h.authorized():return h.j({'error':'Session locale requise.'},401)
    try:
        q=parse_qs(parsed.query,keep_blank_values=True)
        if parsed.path=='/api/jarvis/turn':
            if set(q)!={'request_id'} or len(q['request_id'])!=1:raise Rejected('Référence unique requise.')
            return h.j(h.server.jarvis.get(q['request_id'][0]))
        if q:raise Rejected('Paramètres inattendus.')
        if parsed.path=='/api/jarvis/status':return h.j(h.server.jarvis.status())
        if parsed.path=='/tower_voice.js':return h.response(200,(root/'app/tower_voice.js').read_bytes(),'text/javascript; charset=utf-8')
        bus=h.server.events
        if not bus.slots.acquire(blocking=False):return h.j({'error':'Trop de vues connectées.'},429)
        try:
            h.send_response(200)
            for key,value in {'Content-Type':'text/event-stream','Cache-Control':'no-store','Connection':'close',
                              'X-Content-Type-Options':'nosniff','X-Accel-Buffering':'no'}.items():h.send_header(key,value)
            h.end_headers()
            end=time.monotonic()+25
            sequence=bus.sequence
            h.wfile.write(('retry: 250\ndata: '+str(sequence)+'\n\n').encode());h.wfile.flush()
            while not bus.closed and time.monotonic()<end:
                sequence=bus.wait(sequence)
                h.wfile.write(('data: '+str(sequence)+'\n\n').encode());h.wfile.flush()
        except (OSError,TimeoutError):pass
        finally:bus.slots.release();h.close_connection=True
    except (Rejected,ValueError,IntegrityError) as exc:return h.j({'error':str(exc)},409)


def post(handler):
    h=handler
    if not h.check_host():return
    if not h.authorized():return h.j({'error':'Session locale requise.'},401)
    if h.headers.get('Origin')!=h.server.origin:return h.j({'error':'Origine refusée.'},403)
    if h.headers.get('Transfer-Encoding'):return h.j({'error':'Encodage refusé.'},400)
    if h.server.workspace.closing:return h.j({'error':'Fermeture en cours.'},503)
    if not h.server.requests_gate.acquire(blocking=False):return h.j({'error':'Trop de requêtes.'},429)
    try:
        audio=h.path in ('/api/voice/transcribe','/api/transcribe')
        if h.headers.get_content_type()!=('audio/wav' if audio else 'application/json'):
            return h.j({'error':'Type de contenu invalide.'},415)
        n=int(h.headers.get('Content-Length','-1'))
        if not 0<n<=(MAX_BYTES if audio else 8192):return h.j({'error':'Requête hors limites.'},413)
        raw=h.rfile.read(n)
        if len(raw)!=n:raise Rejected('Requête incomplète.')
        runtime=h.server.jarvis
        if audio:
            owner=h.headers.get('X-Boj-Voice-Owner','')
            if not runtime.voice_lease.owns(owner):raise Rejected('Le microphone n’est pas réservé par cette fenêtre.')
            return h.j(h.server.voice.transcribe(raw))
        data=strict_json(raw)
        if not isinstance(data,dict):raise Rejected('Objet JSON requis.')
        if h.path=='/api/jarvis/turn':return h.j(runtime.submit(data))
        if h.path=='/api/voice/lease':
            if set(data)!={'client_id','release'} or type(data['release']) is not bool:raise Rejected('Contrat audio invalide.')
            return h.j(runtime.voice_lease.claim(data['client_id'],data['release']))
        if set(data)!={'request_id','client_id'}:raise Rejected('Référence et fenêtre requises.')
        if h.path=='/api/jarvis/confirm':return h.j(runtime.confirm(data['request_id'],data['client_id']))
        return h.j(runtime.cancel(data['request_id'],data['client_id']))
    except (Rejected,IntegrityError,ValueError,UnicodeDecodeError) as exc:return h.j({'error':str(exc)},409)
    except Exception:return h.j({'error':'Traitement interrompu. Vérifiez le journal de ce tour avant de reprendre.'},500)
    finally:h.server.requests_gate.release()
