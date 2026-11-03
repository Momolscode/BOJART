"""Bounded French dialogue with optional loopback Ollama adapter.
No model output is code, a device command or an authority over project state.
"""
from __future__ import annotations
from dataclasses import asdict
from decimal import Decimal, InvalidOperation
import http.client, json, math, re, socket, urllib.parse
from core import BaseSpec, Rejected, normalize_text
from figurine.spec import SpecRejected, is_figurine_request, parse_request as parse_figurine

VERSION = 'bojart.dialogue.fr.v2'
SCHEMA = {
    'type':'object', 'additionalProperties':False,
    'properties':{
        'intent':{'type':'string','enum':['create_base','status','show_model','clarify','unsupported']},
        'dimension_quote':{'type':'string','maxLength':80},
        'reason':{'type':'string','maxLength':240}},
    'required':['intent','dimension_quote','reason']}
UNITS = {'mm':Decimal('1'),'millimetre':Decimal('1'),'millimetres':Decimal('1'),
         'cm':Decimal('10'),'centimetre':Decimal('10'),'centimetres':Decimal('10'),
         'pouce':Decimal('25.4'),'pouces':Decimal('25.4')}
ONES = {'zero':0,'un':1,'deux':2,'trois':3,'quatre':4,'cinq':5,'six':6,'sept':7,'huit':8,'neuf':9,
        'dix':10,'onze':11,'douze':12,'treize':13,'quatorze':14,'quinze':15,'seize':16}
TENS = {'vingt':20,'trente':30,'quarante':40,'cinquante':50,'soixante':60}
WORDS = set(ONES)|set(TENS)|{'cent','cents','vingts','et','virgule'}
UNIT_RE = r'(?:millimetres?|centimetres?|pouces?|mm|cm)'
QUANTITY_RE = re.compile(r'(?<![\w.])(?P<number>\d+(?:[.,]\d+)?|(?:[a-z]+[ -]+){0,7}[a-z]+)\s*(?P<unit>'+UNIT_RE+r')\b')
# A positive whitelist avoids silently dropping a manufacturing constraint.
SAFE_WORDS = set('jarvis peux tu vous pouvez pourrais pourrais peux me moi je j aimerais voudrais veux souhaite s il te plait plaît merci bonjour creer cree creer creer prepare preparer genere generer generer faire fais fabriquer construire un le une nouveau socle circulaire rond exposition d de du diametre diametre mesurant mesure mesure a avec en millimetre millimetres centimetre centimetres pouces pouce mm cm et affiche afficher affiche le sur ecran droite droit dans visualiseur montre montre moi modele modele svp'.split()) | WORDS
SAFE_WORDS |= {'l'}
SAFE_WORDS -= {'fabriquer'}  # ambiguous physical intent: explicit creation only
CREATE_WORDS={'cree','creer','prepare','preparer','genere','generer','faire','fais','construire','aimerais','voudrais','veux','souhaite'}
DENIED = re.compile(r'\b(imprime\w*|impression|lance\w*|publie\w*|publicite|paie\w*|achete\w*|supprim\w*|effac\w*|execute\w*|shell|python|systeme|ignore\w*|secret\w*|arret\w*|urgence|arrete\w*|kill|shutdown)\b')
NEGATION = re.compile(r"\b(ne|pas|jamais|sans|sauf|annule\w*|stop|aucun\w*)\b|\bn['’]")
STATUS = {"ou en est le projet","ou en est le dossier","quel est l'etat du dossier","etat du projet","etat du dossier","statut du dossier"}
SHOW = {"affiche le dernier modele","montre le dernier modele","affiche le modele","montre le modele"}


def strict_json(raw):
    def pairs(items):
        obj={}
        for k,v in items:
            if k in obj:raise Rejected('Clé JSON répétée.')
            obj[k]=v
        return obj
    def bad(s):raise Rejected('Nombre non fini.')
    try:return json.loads(raw,object_pairs_hook=pairs,parse_constant=bad)
    except (ValueError,TypeError) as exc:raise Rejected('Réponse JSON invalide.') from exc


def number_fr(raw: str) -> Decimal:
    raw=normalize_text(raw).replace('-', ' ')
    if re.fullmatch(r'\d+(?:[.,]\d+)?',raw):
        try:return Decimal(raw.replace(',','.'))
        except InvalidOperation as exc:raise Rejected('Nombre invalide.') from exc
    parts=raw.split(' virgule ')
    if len(parts)>2:raise Rejected('Nombre ambigu.')
    words=parts[0].split()
    if not words or any(w not in WORDS for w in words):raise Rejected('Nombre français non pris en charge.')
    def under100(ws):
        if not ws:return 0
        s=' '.join(ws)
        if len(ws)==1 and ws[0] in ONES:return ONES[ws[0]]
        if len(ws)==2 and ws[0]=='dix' and ws[1] in {'sept','huit','neuf'}:return 10+ONES[ws[1]]
        if ws[:2] in (['quatre','vingt'],['quatre','vingts']):
            rem=under100(ws[2:]);
            if rem>19:raise Rejected('Nombre ambigu.')
            return 80+rem
        if ws[0] in TENS:
            rest=ws[1:]
            if rest and rest[0]=='et':rest=rest[1:]
            rem=under100(rest)
            if rem>(19 if ws[0]=='soixante' else 9):raise Rejected('Nombre ambigu.')
            return TENS[ws[0]]+rem
        raise Rejected('Nombre français ambigu.')
    positions=[i for i,w in enumerate(words) if w in {'cent','cents'}]
    if len(positions)>1:raise Rejected('Nombre ambigu.')
    if positions:
        i=positions[0]
        if i==0:hundreds=1
        elif i==1 and words[0] in ONES and 1<=ONES[words[0]]<=9:hundreds=ONES[words[0]]
        else:raise Rejected('Nombre français ambigu.')
        n=hundreds*100+under100(words[i+1:])
    else:n=under100(words)
    value=Decimal(n)
    if len(parts)==2:
        dw=parts[1].split()
        if not dw or len(dw)>3 or any(w not in ONES or ONES[w]>9 for w in dw):raise Rejected('Décimales non prises en charge.')
        value+=Decimal('0.'+''.join(str(ONES[w]) for w in dw))
    return value


def clean_command(text):
    if not isinstance(text,str) or not text.strip() or len(text)>500:raise Rejected('Demande vide ou trop longue.')
    s=normalize_text(text)
    if any(ord(c)<32 and c not in '\n\t' for c in s):raise Rejected('Caractères non autorisés.')
    if any(c in s for c in '{}[]<>;`\\=/:'):raise Rejected('Cette demande contient des caractères non pris en charge.')
    return re.sub(r'\s+',' ',s).strip()


def extract_dimension(s):
    """Exactly one explicit dimension; no inferred unit, radius, height or conversion by LLM."""
    tokens=list(re.finditer(r"\d+(?:[.,]\d+)?|[a-z]+(?:-[a-z]+)*",s))
    hits=[]
    for i,t in enumerate(tokens):
        if t.group() not in UNITS:continue
        j=i-1
        if j<0:raise Rejected('Unité sans nombre.')
        if re.fullmatch(r'\d+(?:[.,]\d+)?',tokens[j].group()):start=tokens[j].start()
        else:
            while j>=0 and set(tokens[j].group().split('-'))<=WORDS:j-=1
            start=tokens[j+1].start()
        raw=s[start:t.start()].strip()
        if not raw:raise Rejected('Dimension absente.')
        value=number_fr(raw);unit=t.group()
        hits.append({'quote':s[start:t.end()], 'value':value, 'unit':unit,
                     'mm':value*UNITS[unit], 'start':start, 'end':t.end()})
    if len(hits)!=1:raise Rejected('Précisez une seule dimension avec son unité, par exemple 18 cm de diamètre.')
    hit=hits[0]
    # Numbers outside the selected quantity may represent a quantity, tolerance or second constraint.
    remainder=s[:hit['start']]+' '+s[hit['end']:]
    if re.search(r'\d',remainder):raise Rejected('Plusieurs valeurs : cette recette accepte seulement le diamètre dans la phrase.')
    if hit['start']>0 and s[hit['start']-1]=='-':raise Rejected('Dimension négative.')
    return hit


def inspect_intent(text):
    s=clean_command(text)
    if DENIED.search(s):raise Rejected("Action physique, publication ou commande système indisponible. Aucune action envoyée.")
    if NEGATION.search(s):raise Rejected('Négation ou annulation détectée. Reformulez uniquement la demande à préparer.')
    stripped=re.sub(r"^jarvis[ ,]*",'',s).rstrip(' .!?')
    if stripped in STATUS:return {'intent':'status','normalized':s}
    if stripped in SHOW:return {'intent':'show_model','normalized':s}
    if 'socle' not in s.split() and is_figurine_request(s):
        # Même point d'entrée que le socle ; spécification bornée, sans LLM ni exécution.
        try:spec=parse_figurine(text,source='typed')
        except SpecRejected as exc:raise Rejected(str(exc)) from exc
        return {'intent':'create_figurine','normalized':s,'spec':spec}
    if 'socle' not in s.split():raise Rejected('Cette mission concerne uniquement un socle circulaire ou la consultation du dossier.')
    tokens=re.findall(r'[a-z]+',s)
    if not any(t in CREATE_WORDS for t in tokens):raise Rejected('Précisez ce que vous souhaitez préparer.')
    unknown=set(tokens)-SAFE_WORDS
    if unknown:raise Rejected('Contraintes non prises en charge : '+', '.join(sorted(unknown))+'. Rien ne sera ignoré.')
    dim=extract_dimension(s)
    rest=s[:dim['start']]+' '+s[dim['end']:]
    # Number words left elsewhere may be a hidden quantity.
    numberish=set(re.findall(r'[a-z]+',rest)) & (WORDS-{'un','et'})
    if numberish:raise Rejected('Quantité ou autre dimension ambiguë.')
    d=round(float(dim['mm']),5)
    spec=BaseSpec(diameter_mm=d,upper_diameter_mm=round(d*5/6,5),pitch_mm=round(d*8/15,5));spec.validate()
    return {'intent':'create_base','normalized':s,'dimension_quote':dim['quote'],
            'input_unit':dim['unit'],'input_value':str(dim['value']),'params':asdict(spec)}


class LocalOllama:
    """Loopback only. No proxy, redirect, download, cloud fallback, arbitrary tool calls."""
    def __init__(self,config):
        self.config=config
        url=urllib.parse.urlsplit(config.get('url','http://127.0.0.1:11434'))
        if (url.scheme!='http' or url.hostname!='127.0.0.1' or url.path not in {'','/'} or
            url.username or url.password or url.query or url.fragment):raise Rejected('Ollama doit être sur 127.0.0.1, sans redirection.')
        self.port=url.port or 11434
        self.model=config.get('model','')
        if self.model and not re.fullmatch(r'[A-Za-z0-9_.:/-]{1,120}',self.model):raise Rejected('Nom de modèle invalide.')
        if 'cloud' in self.model.lower():raise Rejected('Un modèle cloud n’est pas autorisé ici.')
    def request(self,path,payload=None,timeout=3):
        if path not in {'/api/tags','/api/show','/api/chat'}:raise Rejected('Route fournisseur non autorisée.')
        conn=http.client.HTTPConnection('127.0.0.1',self.port,timeout=timeout)
        try:
            conn.request('POST' if payload is not None else 'GET',path,
                         body=json.dumps(payload,allow_nan=False) if payload is not None else None,
                         headers={'Content-Type':'application/json','Connection':'close'})
            r=conn.getresponse()
            if r.status!=200:raise Rejected('Le service local n’a pas accepté la demande ('+str(r.status)+').')
            body=r.read(131073)
            if len(body)>131072:raise Rejected('Réponse fournisseur trop volumineuse.')
            return strict_json(body)
        except (OSError,TimeoutError,http.client.HTTPException) as e:raise Rejected('Ollama local indisponible ; aucun repli cloud.') from e
        finally:conn.close()
    def check(self):
        if not self.config.get('enabled'):return {'status':'disabled','message':'Adaptateur désactivé ; règles locales actives.'}
        if not self.model or not self.config.get('model_digest') or self.config.get('offline_verified') is not True:
            return {'status':'not_configured','message':'Modèle local, empreinte et contrôle hors ligne à qualifier.'}
        tags=self.request('/api/tags')
        entries=[m for m in tags.get('models',[]) if m.get('name') in {self.model,self.model+':latest'}]
        if len(entries)!=1:raise Rejected('Modèle local non installé ou ambigu.')
        m=entries[0]
        if (m.get('digest')!=self.config['model_digest'] or type(m.get('size')) is not int or
                m['size']<1000000 or m.get('remote_host') or m.get('remote_model')):
            raise Rejected('Le modèle ne correspond pas à la version locale qualifiée.')
        details=self.request('/api/show',{'model':self.model})
        if details.get('remote_host') or details.get('remote_model'):raise Rejected('Modèle distant refusé.')
        return {'status':'ready','model':self.model,'digest':m['digest'],
                'scope':'Service et poids présents ; qualité et absence de trafic externe à qualifier sur la tour.'}
    def interpret(self,text,grounded):
        if self.check().get('status')!='ready':raise Rejected('Activer uniquement un modèle local qualifié.')
        r=self.request('/api/chat',{
            'model':self.model,'stream':False,'format':SCHEMA,'keep_alive':0,
            'options':{'temperature':0,'num_predict':150,'num_ctx':2048},
            'messages':[{'role':'system','content':
                'Tu classes une demande BOJ.ART. Tu ne déclenches rien. Réponds au schéma fourni. '
                'intent=create_base seulement pour un socle circulaire. dimension_quote recopie exactement '
                'la dimension explicite de la demande normalisée. Aucune unité inventée. '
                'Toute demande ambiguë devient clarify. Pas de code, pas d’outils.'},
                {'role':'user','content':grounded['normalized']}]},timeout=25)
        if r.get('done') is not True:raise Rejected('Réponse locale incomplète.')
        result=strict_json(r.get('message',{}).get('content',''))
        if (not isinstance(result,dict) or set(result)!={'intent','dimension_quote','reason'} or
            any(not isinstance(v,str) for v in result.values()) or
            len(result['reason'])>240 or len(result['dimension_quote'])>80):raise Rejected('Contrat de réponse du modèle invalide.')
        if result['intent']!=grounded['intent'] or result['dimension_quote']!=grounded.get('dimension_quote',''):
            raise Rejected('Le modèle et la demande vérifiable ne concordent pas ; aucune création préparée.')
        # Reasons/confidence never authorize the action or replace the deterministic parameter calculation.
        return {'provider':'ollama_local','model':self.model,'digest':self.config['model_digest'],
                'reason_model':result['reason'],'executed':False}


def interpret(text,provider=None):
    grounded=inspect_intent(text)
    info={'provider':'rules_fr','model':None,'executed':False}
    if grounded['intent']=='create_figurine':
        # Le schéma du modèle local ne couvre pas cette intention : règles seules.
        spec=grounded['spec']
        return {**grounded,'engine':VERSION,**info,'requires_confirmation':True,
                'message':f"Figurine « {spec['character']['label']} », {spec['height_mm']:g} mm, {spec['process']} {spec['material']}. "
                          'Relisez la spécification ; la génération passe par la chaîne figurine.'}
    if provider and provider.config.get('enabled'):
        info=provider.interpret(text,grounded)
    result={**grounded,'engine':VERSION,**info,'requires_confirmation':grounded['intent']=='create_base'}
    if grounded['intent']=='create_base':
        result['message']=f"Socle circulaire Ø {grounded['params']['diameter_mm']:g} mm. Relisez la recette avant de créer."
        result['assumptions']=['Hauteur 24 mm ; quatre perçages Ø 6 mm ; plateau supérieur 4 mm ; chanfrein 1 mm.',
                               'La phrase ne valide ni charge, ni stabilité, ni matière, ni fabrication.']
    return result
