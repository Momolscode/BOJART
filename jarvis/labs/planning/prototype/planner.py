"""BOJ.ART: laboratoire hors machines, données fictives, sans dépendance.

Heuristique de planning (pas CP-SAT, pas de preuve d'optimalité).
Une imprimante/station reste occupée pendant l'attente de déchargement.
Aucun réseau, modèle IA, compte client ou commande de fabrication.
"""
from __future__ import annotations
from copy import deepcopy
from itertools import permutations
import json
from pathlib import Path
from typing import Any

class PlanningError(ValueError):
    pass

class NoSlot(PlanningError):
    pass

def positive_int(v: Any, name: str, allow_zero: bool = False) -> int:
    if type(v) is not int or v < (0 if allow_zero else 1):
        raise PlanningError(f'{name}: entier {"positif ou nul" if allow_zero else "positif"} requis')
    return v

def validate(config: dict) -> None:
    positive_int(config['horizon'], 'horizon')
    if config.get('mode') != 'simulation_only' or config.get('data_origin') != 'synthetic':
        raise PlanningError('Ce laboratoire n’accepte que des scénarios fictifs explicites.')
    rs = config['resources']
    if not isinstance(rs, dict) or not rs:
        raise PlanningError('Ressources manquantes')
    kinds = {'fdm','resin','operator','postprocess','bench'}
    for r, info in rs.items():
        if info['kind'] not in kinds: raise PlanningError(f'Type inconnu: {r}')
        for a, b in info.get('blocked', []):
            positive_int(a, 'début indisponibilité', True)
            positive_int(b, 'fin indisponibilité')
            if not 0 <= a < b <= config['horizon']: raise PlanningError('Indisponibilité invalide')
    ids = set()
    if not 1 <= len(config['jobs']) <= 6: raise PlanningError('Le laboratoire accepte 1 à 6 dossiers')
    for job in config['jobs']:
        if job['id'] in ids: raise PlanningError('Identifiant de dossier dupliqué')
        ids.add(job['id'])
        if job['process'] not in {'fdm','resin'}: raise PlanningError('Procédé inconnu')
        for field in ['release','due']:
            positive_int(job[field], field, True)
        for field in ['setup','print','unload','finish','qc']:
            positive_int(job[field], field)
        if job['process'] == 'resin':
            for field in ['wash_setup','wash','wash_unload','dry','cure_setup','cure','cure_unload']:
                positive_int(job[field], field)
        for r in job['eligible']:
            if r not in rs or rs[r]['kind'] != job['process']:
                raise PlanningError('Affectation incompatible: '+str(r))
    if not any(r['kind']=='operator' for r in rs.values()): raise PlanningError('Opérateur absent')
    if not any(r['kind']=='bench' for r in rs.values()): raise PlanningError('Établi absent')
    if any(j['process']=='resin' for j in config['jobs']) and not any(r['kind']=='postprocess' for r in rs.values()):
        raise PlanningError('Post-traitement absent')

class Calendar:
    def __init__(self, config: dict):
        self.horizon = config['horizon']
        self.resources = config['resources']
        self.reservations = {r:[{'start':a,'end':b,'job':'INDISPONIBLE','label':'Indisponible','blocked':True} for a,b in info.get('blocked',[])] for r,info in self.resources.items()}
        self.events: list[dict] = []

    def conflict(self, resource: str, start: int, end: int) -> list[dict]:
        return [x for x in self.reservations[resource] if start < x['end'] and end > x['start']]

    def slot(self, resources: list[str], earliest: int, duration: int) -> int:
        t=earliest
        while t+duration <= self.horizon:
            clashes=[x for r in resources for x in self.conflict(r,t,t+duration)]
            if not clashes: return t
            t=max(x['end'] for x in clashes)
        raise NoSlot('Aucun créneau trouvé dans l’horizon')

    def reserve(self, resource: str, start: int, end: int, job: str, label: str) -> None:
        if not (0 <= start < end <= self.horizon) or self.conflict(resource,start,end):
            raise PlanningError('Réservation invalide ou chevauchante')
        self.reservations[resource].append({'start':start,'end':end,'job':job,'label':label,'blocked':False})

    def cycle(self, resource: str, earliest: int, setup: int, run: int, unload: int, job: str, label: str) -> int:
        """Cherche un opérateur de préparation puis de retrait, en gardant la machine."""
        ops=[r for r,i in self.resources.items() if i['kind']=='operator']
        options=[]
        for op in ops:
            t=earliest
            while t < self.horizon:
                try:
                    start=self.slot([resource,op],t,setup)
                    run_start=start+setup; run_end=run_start+run
                    if run_end+unload>self.horizon: break
                    unload_options=[]
                    for op2 in ops:
                        try:
                            at=self.slot([op2],run_end,unload)
                            unload_options.append((at+unload,at,op2))
                        except NoSlot: pass
                    if not unload_options: break
                    finish,at,op2=min(unload_options)
                    clashes=self.conflict(resource,start,finish)
                    if clashes:
                        t=max(x['end'] for x in clashes); continue
                    options.append((finish,start,run_start,run_end,at,op,op2)); break
                except NoSlot: break
        if not options: raise NoSlot('Aucun cycle admissible pour '+resource)
        finish,start,run_start,run_end,at,op,op2=min(options)
        self.reserve(resource,start,finish,job,label+' · réservé jusqu’au retrait')
        self.reserve(op,start,run_start,job,label+' · préparation')
        self.reserve(op2,at,finish,job,label+' · retrait')
        self.events.extend([
            {'job':job,'label':label+' · préparation','start':start,'end':run_start,'resources':[resource,op]},
            {'job':job,'label':label+' · cycle','start':run_start,'end':run_end,'resources':[resource]},
            {'job':job,'label':label+' · retrait','start':at,'end':finish,'resources':[resource,op2]}
        ])
        if at>run_end:
            self.events.append({'job':job,'label':label+' · attente du retrait','start':run_end,'end':at,'resources':[resource]})
        return finish

    def manual(self, earliest: int, duration: int, job: str, label: str) -> int:
        ops=[r for r,i in self.resources.items() if i['kind']=='operator']
        benches=[r for r,i in self.resources.items() if i['kind']=='bench']
        options=[]
        for op in ops:
            for bench in benches:
                try: options.append((self.slot([op,bench],earliest,duration),op,bench))
                except NoSlot: pass
        if not options: raise NoSlot('Aucun créneau manuel')
        start,op,bench=min(options); end=start+duration
        for r in [op,bench]: self.reserve(r,start,end,job,label)
        self.events.append({'job':job,'label':label,'start':start,'end':end,'resources':[op,bench]})
        return end

def add_job(cal: Calendar, job: dict, printer: str) -> dict:
    release=cal.cycle(printer,job['release'],job['setup'],job['print'],job['unload'],job['id'],'Impression')
    if job['process']=='resin':
        stations=[r for r,i in cal.resources.items() if i['kind']=='postprocess']
        options=[]
        for station in stations:
            candidate=deepcopy(cal)
            try:
                washed=candidate.cycle(station,release,job['wash_setup'],job['wash'],job['wash_unload'],job['id'],'Lavage')
                candidate.events.append({'job':job['id'],'label':'Délai technique fictif','start':washed,'end':washed+job['dry'],'resources':[]})
                cured=candidate.cycle(station,washed+job['dry'],job['cure_setup'],job['cure'],job['cure_unload'],job['id'],'Cure')
                options.append((cured,station,candidate))
            except NoSlot: pass
        if not options: raise NoSlot('Post-traitement indisponible')
        release,station,chosen=min(options,key=lambda x:(x[0],x[1]))
        cal.reservations=chosen.reservations; cal.events=chosen.events
    finish=cal.manual(release,job['finish'],job['id'],'Finition')
    done=cal.manual(finish,job['qc'],job['id'],'Contrôle / conditionnement fictif')
    return {'id':job['id'],'printer':printer,'complete':done,'due':job['due'],'late_by':max(0,done-job['due'])}

def solve(config: dict) -> dict:
    validate(config)
    digest_source=json.dumps(config,sort_keys=True,ensure_ascii=False).encode()
    import hashlib
    base={'schema':'bojart.planning_lab/1','mode':'simulation_only','data_origin':'synthetic',
          'can_execute':False,'optimality_claim':False,'input_sha256':hashlib.sha256(digest_source).hexdigest(),
          'resources':config['resources'],'horizon':config['horizon'], 'scenario':config['name']}
    if any(not j['eligible'] for j in config['jobs']):
        return {**base,'status':'BLOCKED','reason':'Au moins un dossier ne possède aucune machine admissible déclarée.','results':[],'reservations':{}}
    solutions=[]
    for order in permutations(config['jobs']):
        cal=Calendar(config); done=[]
        try:
            for job in order:
                choices=[]
                for printer in job['eligible']:
                    candidate=deepcopy(cal)
                    try:
                        result=add_job(candidate,job,printer)
                        choices.append((result['late_by'],result['complete'],printer,candidate,result))
                    except NoSlot: pass
                if not choices: raise NoSlot('Aucune affectation trouvée')
                _,_,_,cal,result=min(choices,key=lambda x:x[:3]); done.append(result)
            score=(sum(x['late_by'] for x in done),max(x['complete'] for x in done))
            solutions.append((score,[x['id'] for x in order],cal,done))
        except NoSlot: continue
    if not solutions:
        return {**base,'status':'NO_PLAN_FOUND','reason':'L’heuristique ne trouve pas de plan dans l’horizon. Ce n’est pas une preuve d’impossibilité.','results':[],'reservations':{}}
    score,order,cal,results=min(solutions,key=lambda x:(x[0],x[1]))
    return {**base,'status':'PLAN_FOUND' if score[0]==0 else 'PLAN_LATE','reason':'Meilleur plan trouvé par énumération des ordres de dossiers et placement glouton. Pas d’optimalité certifiée.',
            'order':order,'score':{'total_lateness_minutes':score[0],'completion_minutes':score[1]},
            'results':sorted(results,key=lambda x:x['id']),
            'reservations':{r:sorted(v,key=lambda x:x['start']) for r,v in cal.reservations.items()},
            'events':sorted(cal.events,key=lambda x:(x['start'],x['job'],x['label']))}

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('scenario',type=Path); p.add_argument('--out',type=Path)
    a=p.parse_args()
    try:
        output=json.dumps(solve(json.loads(a.scenario.read_text(encoding='utf-8'))),indent=2,ensure_ascii=False)
    except (ValueError,KeyError,TypeError) as e:
        p.exit(2,f'Scénario refusé : {e}\n')
    if a.out: a.out.write_text(output,encoding='utf-8')
    else: print(output)
