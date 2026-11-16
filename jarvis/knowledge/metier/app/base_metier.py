#!/usr/bin/env python3
"""Bibliothèque documentaire locale BOJ.ART. Aucun réseau, LLM ou action machine.
Recherche lexicale SQLite FTS5 ; les résultats restent des fiches, pas des recettes.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import re
import sqlite3
import unicodedata
from contextlib import closing
from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from typing import Any

ROOT=Path(__file__).resolve().parents[1]
STOP={'un','une','des','les','le','la','de','du','et','en','au','aux','a','à','pour','sur','dans','avec','sans','comment','quel','quelle','quels','quelles','je','tu','on','il','elle','est','ce','ces','que','qui','plus','faire','jarvis','moi','mon','ma','mes','nos','notre','nous','l','d','s'}
SYNONYMS={'resine':['resine','sla','msla','photopolymerisation'], 'fdm':['fdm','fff','filament'], 'humide':['humidite','sechage'], 'fissure':['fissure','cavite','drainage','resine'], 'trous':['trou','drainage'], 'creuse':['evidement','cavite','coque'], 'creux':['evidement','cavite','coque'], 'emboiter':['assemblage','jeu','tolerance'], 'prix':['cout','devis','marge'], 'retard':['planning','delai'], 'graisse':['lubrifiant','maintenance'], 'pouces':['pouce','unite'], 'grand':['grand','segmentation','assemblage'], 'fil':['filament','fdm'], 'short':['character','fidelite'], 'reimprimer':['reprise','doublon']}

def normalized(text: str) -> str:
    return ''.join(c for c in unicodedata.normalize('NFKD',text.lower()) if not unicodedata.combining(c))

def tokens(text: str) -> list[str]:
    if not isinstance(text,str): raise TypeError('La recherche doit être une chaîne.')
    if len(text)>2000: raise ValueError('Recherche trop longue (maximum 2 000 caractères).')
    words=[w for w in re.findall(r'[a-z0-9]+',normalized(text)) if w not in STOP and len(w)>1]
    out=[]
    for w in words:
        for x in SYNONYMS.get(w,[w]):
            if x not in out: out.append(x)
    return out[:32]

class KnowledgeBase:
    def __init__(self, root: Path|str=ROOT):
        self.root=Path(root)
        def read(name:str):
            path=self.root/'data'/name
            if path.stat().st_size>4_000_000: raise ValueError('Corpus au-delà de la limite autorisée.')
            return json.loads(path.read_text(encoding='utf-8'))
        self.sources=read('sources.json'); self.cards=read('fiches.json')
        self.procedures=read('procedures.json'); self.context=read('contexte.json')
        self._validate()
        self.by_source={s['id']:s for s in self.sources}
        self.by_id={c['id']:c for c in self.cards}
        self.con=sqlite3.connect(':memory:')
        self.con.execute("CREATE VIRTUAL TABLE fiches USING fts5(id UNINDEXED, domain UNINDEXED, title, tags, body, tokenize='unicode61 remove_diacritics 2')")
        self.con.executemany('INSERT INTO fiches VALUES (?,?,?,?,?)',[(c['id'],c['domain'],c['title'],' '.join(c['tags']),c['statement']+' '+c['bojart_application']) for c in self.cards])
        self.con.commit()

    def _validate(self):
        for rows,label in [(self.sources,'sources'),(self.cards,'fiches'),(self.procedures,'procedures')]:
            ids=[r.get('id') for r in rows]
            if any(not isinstance(i,str) or not i for i in ids) or len(ids)!=len(set(ids)):
                raise ValueError('Identifiants invalides ou dupliqués : '+label)
        source_ids={s['id'] for s in self.sources}
        for s in self.sources:
            if not s['url'].startswith('https://'): raise ValueError('Source non HTTPS.')
            date.fromisoformat(s['checked_on']); date.fromisoformat(s['next_review_on'])
            if not s['scope']: raise ValueError('Portée source absente.')
        for c in self.cards:
            if c.get('execution_authority') is not False or c.get('site_validated') is not False or c.get('universal_machine_settings') is not False:
                raise ValueError('Le corpus ne doit pas déclarer des recettes ou actions qualifiées.')
            if c['evidence_level'] not in {'documente','regle_bojart_proposee'}: raise ValueError('Niveau inconnu.')
            if c['evidence_level']=='documente' and not c['source_ids']: raise ValueError('Fiche documentaire sans source.')
            if not set(c['source_ids']).issubset(source_ids): raise ValueError('Source introuvable.')
            for key in ['title','statement','bojart_application','scope','domain']:
                if not isinstance(c.get(key),str) or not c[key]: raise ValueError('Champ de fiche absent : '+key)
        card_ids={c['id'] for c in self.cards}
        for p in self.procedures:
            if not set(p['knowledge_ids']).issubset(card_ids): raise ValueError('Fiche de procédure introuvable.')
            if p['automatic_execution'] is not False: raise ValueError('Procédure exécutable interdite.')

    def search(self, query: str, *, domain: str|None=None, limit:int=6, as_of: str|None=None) -> dict[str,Any]:
        if type(limit) is not int or not 1<=limit<=20: raise ValueError('limit doit être compris entre 1 et 20.')
        today=date.fromisoformat(as_of) if as_of else date.today()
        domains={c['domain'] for c in self.cards}
        if domain is not None and domain not in domains: raise ValueError('Domaine inconnu.')
        ts=tokens(query)
        if ts:
            # Tokens strictement alphanumériques, valeurs liées : ni SQL ni syntaxe FTS de l’utilisateur exécutés.
            match=' OR '.join('"'+t+'"*' for t in ts)
            sql='SELECT id,bm25(fiches,0,0,8,5,1) score FROM fiches WHERE fiches MATCH ?'
            args:list[Any]=[match]
            if domain: sql+=' AND domain=?'; args.append(domain)
            sql+=' ORDER BY score,id LIMIT ?'; args.append(limit)
            rows=self.con.execute(sql,args).fetchall()
        else:
            rows=[(c['id'],0.0) for c in self.cards if domain is None or c['domain']==domain][:limit]
        result=[]
        for cid,score in rows:
            c=self.by_id[cid]
            sources=[self.by_source[s] for s in c['source_ids']]
            overdue=[s['id'] for s in sources if today>date.fromisoformat(s['next_review_on'])]
            warnings=['Documentation seulement ; aucune validation du parc réel.']
            if overdue: warnings.append('Relecture documentaire due : '+', '.join(overdue)+'. Cela ne prouve pas que le contenu est faux, mais impose sa vérification avant usage opérationnel.')
            if c['scope']!='principe_general': warnings.append('Portée spécifique : '+c['scope'])
            if c['evidence_level']=='regle_bojart_proposee': warnings.append('Règle de projet proposée, non prescription du fabricant.')
            result.append(dict(card=c,sources=sources,review_overdue=overdue,warnings=warnings))
        return {'query':query,'method':'recherche_lexicale_fts5_pas_de_llm','as_of':str(today),'items':result,'total_returned':len(result),'allowed_to_execute':False}

    def documentation_readiness(self, recipe:dict[str,Any], current:dict[str,Any]) -> dict[str,Any]:
        """Vérifie la présence et concordance déclarées, pas la réalité d’une signature ni de l’essai.
        Toujours non exécutoire. L’autorité de qualification est hors de ce module.
        """
        required=['id','machine_id','firmware','material_sku','material_version','tooling_id','layer_height_mm','slicer_version','settings_sha256','profile_file','orientation_scope','postprocess_id','test_report','approved_by','approved_at']
        missing=[k for k in required if recipe.get(k) is None or recipe.get(k)=='']
        invalid=[]
        if recipe.get('status')!='qualified': invalid.append('status_non_qualifie')
        sha=recipe.get('settings_sha256')
        if sha is not None and not re.fullmatch(r'[0-9a-f]{64}',str(sha)): invalid.append('empreinte_reglages_invalide')
        layer=recipe.get('layer_height_mm')
        if layer is not None and (isinstance(layer,bool) or not isinstance(layer,(float,int)) or not 0<layer<20): invalid.append('hauteur_couche_invalide')
        stamp=recipe.get('approved_at')
        if stamp:
            try: date.fromisoformat(str(stamp)[:10])
            except ValueError: invalid.append('date_approbation_invalide')
        compare=['machine_id','firmware','material_sku','material_version','tooling_id','layer_height_mm','slicer_version','settings_sha256','orientation_scope','postprocess_id']
        mismatch=[k for k in compare if not current.get(k) or current.get(k)!=recipe.get(k)]
        return {'status':'dossier_declare_complet_a_verifier' if not missing and not invalid and not mismatch else 'dossier_incomplet_ou_non_concordant','missing':missing,'invalid':invalid,'mismatch':mismatch,'allowed_to_execute':False,'note':'Présence et concordance seulement. Rapports, approbations, fichiers et sécurité réelle à vérifier par l’autorité atelier.'}

    def export_index(self,path:Path|str):
        path=Path(path)
        if path.exists(): raise FileExistsError('Refus d’écraser un index existant.')
        with closing(sqlite3.connect(path)) as target, target: self.con.backup(target)


def price_from_cost(cost:Any, margin:Any, fees:Any) -> dict[str,str]:
    """Calcul pédagogique sur une seule base cohérente, sans réglage fiscal."""
    if any(v is None or isinstance(v,bool) for v in (cost,margin,fees)): raise ValueError('Coût, marge et frais sont nécessaires.')
    try: c,m,f=map(lambda v:Decimal(str(v)),(cost,margin,fees))
    except Exception as exc: raise ValueError('Entrées numériques requises.') from exc
    if not all(v.is_finite() for v in (c,m,f)) or c<0 or m<0 or f<0 or m+f>=1:
        raise ValueError('Valeurs invalides : coût ≥ 0, taux ≥ 0 et marge + frais < 1.')
    p=(c/(1-m-f)).quantize(Decimal('0.01'),rounding=ROUND_HALF_UP)
    return {'price':str(p),'formula':'C / (1 - m - f)','status':'calcul_pedagogique_non_devis','tax_basis':'a_definir_sans_melanger_HT_TTC'}

if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('query',nargs='?',default='résine creuse drainage')
    ap.add_argument('--domain'); ap.add_argument('--limit',type=int,default=6); ap.add_argument('--as-of'); ap.add_argument('--export-index',type=Path)
    a=ap.parse_args(); kb=KnowledgeBase()
    if a.export_index: kb.export_index(a.export_index)
    print(json.dumps(kb.search(a.query,domain=a.domain,limit=a.limit,as_of=a.as_of),ensure_ascii=False,indent=2))
