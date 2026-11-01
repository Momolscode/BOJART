from pathlib import Path
from copy import deepcopy
import json
from planner import solve
ROOT=Path(__file__).resolve().parents[1]
BASE={
 'name':'Base — deux machines résine, un opérateur', 'mode':'simulation_only','data_origin':'synthetic','horizon':720,
 'assumptions':['Toutes les durées sont inventées pour éprouver les règles, pas des recettes de fabrication.','Machines, matières, dimensions et profils non qualifiés.','Post-traitement : une station partagée pour lavage et cure, changements compris dans les durées fictives.','Pas de transport, multi-plateaux, maintenance réelle, emballage détaillé ou stock dans ce laboratoire.','Un cycle peut attendre un opérateur; la ressource reste réservée.','L’échéance concerne un horizon abstrait; aucune date de livraison réelle.'],
 'resources':{
   'FDM-A':{'kind':'fdm'}, 'RESINE-A':{'kind':'resin'},'RESINE-B':{'kind':'resin'},
   'POSTE-LAVAGE-CURE':{'kind':'postprocess'},'OPERATEUR-1':{'kind':'operator','blocked':[[180,210]]},'ETABLI':{'kind':'bench'}
 },
 'jobs':[
   {'id':'SOCLE','process':'fdm','eligible':['FDM-A'],'release':0,'due':600,'setup':10,'print':150,'unload':10,'finish':45,'qc':15},
   {'id':'TORSE','process':'resin','eligible':['RESINE-A','RESINE-B'],'release':0,'due':600,'setup':10,'print':180,'unload':10,'wash_setup':5,'wash':20,'wash_unload':5,'dry':30,'cure_setup':5,'cure':25,'cure_unload':5,'finish':60,'qc':15},
   {'id':'DETAIL','process':'resin','eligible':['RESINE-A','RESINE-B'],'release':0,'due':600,'setup':10,'print':120,'unload':10,'wash_setup':5,'wash':20,'wash_unload':5,'dry':30,'cure_setup':5,'cure':25,'cure_unload':5,'finish':50,'qc':15}
 ]
}

def build():
    scenarios={'base':deepcopy(BASE)}
    outage=deepcopy(BASE); outage['name']='Machine résine B indisponible'; outage['resources']['RESINE-B']['blocked']=[[0,720]]; scenarios['machine_absente']=outage
    overload=deepcopy(BASE); overload['name']='Finition deux fois plus longue';
    for job in overload['jobs']: job['finish']*=2
    scenarios['finition_plus_longue']=overload
    deadline=deepcopy(BASE); deadline['name']='Échéance trop courte pour ce plan';
    for job in deadline['jobs']: job['due']=200
    scenarios['echeance_courte']=deadline
    missing=deepcopy(BASE); missing['name']='Aucune machine admissible pour le torse'; missing['jobs'][1]['eligible']=[]; scenarios['compatibilite_manquante']=missing
    results={}
    for k,v in scenarios.items():
        (ROOT/'exemples'/f'{k}.json').write_text(json.dumps(v,ensure_ascii=False,indent=2),encoding='utf-8')
        r=solve(v); results[k]=r
        (ROOT/'preuves'/f'planning_{k}.json').write_text(json.dumps(r,ensure_ascii=False,indent=2),encoding='utf-8')
        print(k,r['status'],r.get('score'))
    (ROOT/'preuves'/'resultats.json').write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding='utf-8')
    return results

if __name__=='__main__': build()
