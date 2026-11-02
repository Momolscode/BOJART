"""Prevent stale, contradicted or merely planned facts from becoming live evidence."""
from __future__ import annotations
from datetime import datetime, timezone
import hashlib, json

CATEGORIES={'user_constraint','verified_here','historical_claim','proposed','unknown'}


def validate_context(doc):
    if doc.get('project_id')!='BOJART_JARVIS':raise ValueError('Projet de contexte incorrect.')
    seen=set()
    for f in doc.get('facts',[]):
        key=f['key']
        if key in seen:raise ValueError('Fait dupliqué ou contradictoire : '+key)
        seen.add(key)
        if f['status'] not in CATEGORIES:raise ValueError('Statut inconnu.')
        if not f.get('source') or not f.get('scope'):raise ValueError('Source et portée obligatoires.')
        if f['status']=='unknown' and f.get('value') is not None:raise ValueError('Une inconnue ne doit pas se déguiser en fait.')
        if f['status']=='verified_here' and not f.get('evidence'):raise ValueError('Vérification sans preuve.')
    return True


def operational_value(fact, current_time=None):
    """May only return fresh measured states, never a requirement/plan/historical claim."""
    if fact.get('status')!='verified_here':return None
    if not fact.get('observed_at') or not fact.get('max_age_seconds'):return None
    try:
        observed=datetime.fromisoformat(fact['observed_at'])
        current=current_time or datetime.now(timezone.utc)
        age=(current-observed).total_seconds()
    except (ValueError, TypeError):return None
    if not 0<=age<=fact['max_age_seconds']:return None
    return fact.get('value')


def render_brief(doc):
    validate_context(doc)
    lines=['# Contexte de référence BOJ.ART / Jarvis',f"Version : {doc['version']} | date : {doc['updated_at']}",
           '\nCe dossier est distinct d’UNUM et de M-Tek. Ne pas déduire le matériel cible de leurs configurations.']
    for status,title in [('user_constraint','Contraintes exprimées'),('verified_here','Vérifié dans cet environnement'),
                         ('historical_claim','Historique non réaudité ici'),('proposed','Propositions'),('unknown','Inconnues à lever')]:
        lines += ['\n## '+title]
        for f in doc['facts']:
            if f['status']==status:lines.append(f"- {f['label']} : {json.dumps(f['value'],ensure_ascii=False)}. Portée : {f['scope']}. Source : {f['source']}.")
    lines+=['\n## Mode de travail','Ne pas appeler le réseau, publier, engager une dépense ou lancer une imprimante à partir de ce seul contexte.',
            'Vérifier les fichiers et l’état courant avant une décision ; les versions terminées restent immuables.',
            'Les observations d’atelier ont une date et une durée de validité ; une ancienne note ne prouve pas un état présent.']
    return '\n'.join(lines)+'\n'
