"""Offline scheduling experiment. Synthetic inputs only; no mesh or printer driver.

Bounding boxes are already oriented and scaled in millimetres. Durations are
assumed per part AND machine, not extrapolated from a printer's advertised speed.
This screening cannot establish printability, joints, strength or character fidelity.
"""
from __future__ import annotations

import hashlib
import math
from core import Rejected, canonical


def number(value, name, *, zero=False):
    if type(value) not in (int, float) or not math.isfinite(value) or value < 0 or (not zero and value == 0):
        raise Rejected(f'{name}: nombre fini {"positif ou nul" if zero else "strictement positif"} requis.')
    return float(value)


def preparation_requirements(subject, target_height_mm):
    number(target_height_mm, 'target_height_mm')
    if not isinstance(subject, str) or not subject.strip() or len(subject) > 120:
        raise Rejected('Sujet manquant ou trop long.')
    return {
        'status':'NEEDS_INPUT', 'subject':subject, 'target_height_mm':target_height_mm,
        'can_print':False, 'mesh_created':False, 'spoken_command_connected':False,
        'missing':[
            {'id':'mesh', 'detail':'Fichier 3D source identifié, unités et hauteur mesurées ; aucune géométrie de personnage livrée.'},
            {'id':'fleet', 'detail':'Inventaire réel : volumes utiles, procédé, matière, profils et disponibilités.'},
            {'id':'parts', 'detail':'Découpe, orientations, assemblages et supports vérifiés à la hauteur cible.'},
            {'id':'slicer', 'detail':'Durée et matière estimées par le slicer pour chaque couple pièce / profil machine.'},
        ],
        'reply':f'Je prépare le dossier {subject}, hauteur {target_height_mm:g} mm. Il me manque le modèle 3D et les profils réels des imprimantes pour découper et chiffrer le travail.',
        'reply_kind':'template_for_simulation_not_live_voice',
    }


def _validate(data):
    if not isinstance(data, dict) or data.get('data_kind') != 'synthetic_scheduling_fixture':
        raise Rejected('Ce simulateur accepte uniquement un jeu de données explicitement fictif.')
    height = number(data.get('target_height_mm'), 'target_height_mm')
    if number(data.get('parts_height_basis_mm'), 'parts_height_basis_mm') != height:
        raise Rejected('Hauteur changée : redécoupe et nouvelles estimations nécessaires.')
    printers, parts = data.get('printers'), data.get('parts')
    if not isinstance(printers, list) or not 1 <= len(printers) <= 32:
        raise Rejected('Entre 1 et 32 machines fictives requises.')
    if not isinstance(parts, list) or not 1 <= len(parts) <= 500:
        raise Rejected('Entre 1 et 500 pièces fictives requises.')
    for rows, label in ((printers, 'printer'), (parts, 'part')):
        ids = [r.get('id') for r in rows if isinstance(r, dict)]
        if len(ids) != len(rows) or any(not isinstance(i, str) or not i or len(i) > 80 for i in ids) or len(set(ids)) != len(ids):
            raise Rejected(f'Identifiants {label} manquants ou dupliqués.')
    printer_ids = {p['id'] for p in printers}
    for p in printers:
        if p.get('process') not in ('FDM', 'RESIN') or type(p.get('online')) is not bool:
            raise Rejected('Procédé ou disponibilité de machine invalide.')
        if not isinstance(p.get('materials'), list) or not p['materials'] or any(not isinstance(m, str) or not m for m in p['materials']):
            raise Rejected('Matières de machine manquantes.')
        number(p.get('ready_after_min'), 'ready_after_min', zero=True)
        number(p.get('turnaround_min'), 'turnaround_min', zero=True)
        number(p.get('clearance_mm'), 'clearance_mm', zero=True)
        volume = p.get('volume')
        if not isinstance(volume, dict) or volume.get('shape') not in ('box', 'cylinder'):
            raise Rejected('Volume utile box ou cylinder requis.')
        keys = ('x', 'y', 'z') if volume['shape'] == 'box' else ('diameter', 'z')
        for key in keys:
            if number(volume.get(key), key) <= 2*p['clearance_mm']:
                raise Rejected('Marge plus grande que le volume utile.')
    for p in parts:
        bbox = p.get('bbox_mm')
        if not isinstance(bbox, list) or len(bbox) != 3:
            raise Rejected('Trois dimensions de boîte orientée requises.')
        for value in bbox:number(value, 'bbox_mm')
        if p.get('process') not in ('FDM', 'RESIN') or not isinstance(p.get('material'), str) or not p['material']:
            raise Rejected('Procédé ou matière de pièce invalide.')
        if p.get('state') not in ('unstarted', 'printing', 'unknown', 'completed'):
            raise Rejected('État de pièce invalide.')
        times = p.get('minutes_by_printer')
        if not isinstance(times, dict) or not set(times) <= printer_ids:
            raise Rejected('Estimations avec référence de machine inconnue.')
        for value in times.values():number(value, 'estimated_minutes')
    return printers, parts


def _reason(part, printer):
    if not printer['online']:return 'offline'
    if part['process'] != printer['process']:return 'process'
    if part['material'] not in printer['materials']:return 'material'
    x, y, z = part['bbox_mm']
    margin = 2*printer['clearance_mm']
    volume = printer['volume']
    if z > volume['z']-margin:return 'height'
    if volume['shape'] == 'box':
        if x > volume['x']-margin or y > volume['y']-margin:return 'footprint'
    elif math.hypot(x, y) > volume['diameter']-margin:
        return 'circular_footprint'  # Both corners must fit; x and y alone are insufficient.
    if printer['id'] not in part['minutes_by_printer']:return 'missing_time_estimate'
    return None


def schedule(data, *, strategy='earliest_finish'):
    """Return a deterministic draft; never authorize or export machine instructions.

    One piece per job; no plate nesting, automatic rotation, assembly precedence,
    working-hours calendar or material refill model. Ready time and turnaround
    are explicit assumptions. The objective ends at the last print completion;
    post-processing and assembly are outside it.
    """
    if strategy not in ('earliest_finish', 'round_robin'):raise Rejected('Stratégie inconnue.')
    printers, parts = _validate(data)
    result = {
        'schema':'bojart.fleet-simulation.v1', 'status':'SIMULATION_ONLY',
        'input_sha256':hashlib.sha256(canonical(data).encode()).hexdigest(),
        'data_kind':data['data_kind'], 'target_height_mm':data['target_height_mm'],
        'strategy':strategy, 'can_print':False, 'mesh_created':False,
        'geometry_checked':False, 'physical_commands':False, 'jobs':[],
        'completed_excluded':[p['id'] for p in parts if p['state']=='completed'],
        'assumptions':['synthetic boxes and per-printer durations', 'one part per job',
                       'fixed orientation, supports and brim must be included in box',
                       'no human calendar, assembly, post-processing or failure forecast'],
    }
    uncertain = [p['id'] for p in parts if p['state'] in ('unknown', 'printing')]
    if uncertain:
        return {**result, 'status':'NEEDS_RECONCILIATION', 'blocked_parts':uncertain}
    pending = [p for p in parts if p['state']=='unstarted']
    eligible, excluded = {}, {}
    for part in pending:
        reasons = {p['id']:_reason(part, p) for p in printers}
        eligible[part['id']] = [p for p in printers if reasons[p['id']] is None]
        excluded[part['id']] = {k:v for k,v in reasons.items() if v}
    result['excluded_candidates'] = excluded
    impossible = [p['id'] for p in pending if not eligible[p['id']]]
    if impossible:
        return {**result, 'status':'INFEASIBLE', 'blocked_parts':impossible}
    loads = {p['id']:float(p['ready_after_min']) for p in printers}
    rows = sorted(pending, key=lambda p:(-min(p['minutes_by_printer'][m['id']] for m in eligible[p['id']]), p['id'])) if strategy=='earliest_finish' else pending
    cursor = 0
    for part in rows:
        choices = eligible[part['id']]
        if strategy == 'earliest_finish':
            machine = min(choices, key=lambda p:(loads[p['id']]+part['minutes_by_printer'][p['id']], p['id']))
        else:
            indices = [i for i in range(len(printers)) if printers[i] in choices]
            chosen = min(indices, key=lambda i:((i-cursor) % len(printers), i))
            machine = printers[chosen];cursor=(chosen+1) % len(printers)
        pid = machine['id']; duration = part['minutes_by_printer'][pid]
        start = loads[pid]; finish = start+duration
        result['jobs'].append({'part_id':part['id'], 'printer_id':pid, 'start_min':start,
                               'finish_min':finish, 'assumed_duration_min':duration})
        loads[pid] = finish+machine['turnaround_min']
    makespan = max((r['finish_min'] for r in result['jobs']), default=0.0)
    active = {p['id'] for choices in eligible.values() for p in choices}
    min_times = [min(p['minutes_by_printer'][m['id']] for m in eligible[p['id']]) for p in pending]
    # Optimistic lower bound, ignoring sequencing/setup and some compatibility.
    earliest_completion = [min(m['ready_after_min']+p['minutes_by_printer'][m['id']] for m in eligible[p['id']]) for p in pending]
    bound = max([sum(min_times)/len(active) if active else 0.0, *earliest_completion])
    result.update(makespan_min=makespan, optimistic_lower_bound_min=bound,
                  gap_to_lower_bound_percent=(100*(makespan-bound)/bound if bound else 0.0),
                  printers_used=len({r['printer_id'] for r in result['jobs']}),
                  total_assumed_print_minutes=sum(r['assumed_duration_min'] for r in result['jobs']),
                  optimality_proven=False)
    return result
