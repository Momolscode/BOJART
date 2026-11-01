#!/usr/bin/env python3
"""Contrôles documentaires Marwin. Aucun appel réseau, lancement ou verdict artistique."""
import argparse
import hashlib
import json
import math
from collections import Counter
from datetime import date, datetime
from pathlib import Path

VERSION = '1.0.0'
KINDS = {'video', 'still', 'carousel_excerpt', 'documentary'}
VISUAL = {'sampled', 'full', 'thumbnail_only', 'not_viewed', 'not_applicable'}
AUDIO = {'not_verified', 'automated_report', 'direct_review', 'not_applicable'}
NONFINAL = {'queued', 'running', 'submitted', 'unknown', 'timeout_unknown'}
FINAL = {'completed', 'failed', 'cancelled'}


def number(value):
    return type(value) in (int, float) and math.isfinite(value)


def reference_errors(ref):
    """Valide la cohérence des déclarations, jamais la vérité de leur contenu."""
    errors = []
    for key in ('id', 'url', 'evidence_ref', 'kind', 'visual_scope', 'audio_mode'):
        if not isinstance(ref.get(key), str) or not ref[key].strip():
            errors.append(f'{key}: champ texte requis')
    kind = ref.get('kind')
    visual = ref.get('visual_scope')
    if kind not in KINDS:
        errors.append('kind: type inconnu')
    if visual not in VISUAL:
        errors.append('visual_scope: valeur inconnue')
    if ref.get('audio_mode') not in AUDIO:
        errors.append('audio_mode: valeur inconnue')
    if ref.get('audio_mode') == 'direct_review' and not ref.get('direct_audio_evidence'):
        errors.append('audio: écoute directe déclarée sans preuve')
    if kind in {'still', 'carousel_excerpt', 'documentary'}:
        if ref.get('duration_seconds') is not None or ref.get('timeline'):
            errors.append('temps: durée et timeline vidéo interdites pour ce type de pièce')
    else:
        duration = ref.get('duration_seconds')
        if duration is not None and (not number(duration) or duration <= 0):
            errors.append('duration_seconds: nombre fini positif ou null requis')
        if visual == 'full' and (not number(duration) or duration <= 0):
            errors.append('full: durée vidéo requise')
        previous_end = 0
        for segment in ref.get('timeline', []):
            start, end = segment.get('start_s'), segment.get('end_s')
            if not (number(start) and number(end) and 0 <= start < end):
                errors.append('timeline: intervalle invalide')
                continue
            if start < previous_end or duration is None or end > duration:
                errors.append('timeline: chevauchement ou dépassement de durée')
            previous_end = end
    if visual in {'thumbnail_only', 'not_viewed', 'not_applicable'} and ref.get('motion_observed') is True:
        errors.append('mouvement: observation incompatible avec le périmètre visuel')
    if ref.get('exact_cuts_observed') is True and not ref.get('frame_cut_evidence'):
        errors.append('coupes: mesure précise sans preuve par image')
    if ref.get('causal_retention_proven') is True and not ref.get('causal_study_evidence'):
        errors.append('rétention: causalité sans étude associée')
    if ref.get('creator_pipeline') == 'confirmed' and not ref.get('creator_pipeline_source'):
        errors.append('pipeline: attribution confirmée sans source')
    if kind == 'carousel_excerpt':
        cards = ref.get('visible_cards', [])
        total = ref.get('carousel_total')
        if not cards or type(total) is not int or total < 1:
            errors.append('carrousel: cartes vues et total requis')
        elif len(set(cards)) != len(cards) or any(type(x) is not int or x < 1 or x > total for x in cards):
            errors.append('carrousel: indices invalides')
        if ref.get('full_post_seen') is True and len(cards) < total:
            errors.append('carrousel: seulement un extrait du post a été vu')
    return errors


def approval_matches(approval, artifact, dimension):
    return (isinstance(approval, dict) and approval.get('approved') is True
            and approval.get('dimension') == dimension
            and bool(artifact.get('sha256'))
            and approval.get('artifact_sha256') == artifact['sha256']
            and bool(approval.get('source')) and bool(approval.get('date')))


def scene_gate(scene, stage):
    """Évalue les pièces déclarées. Même un passage ne soumet ni ne publie rien."""
    reasons = []
    if stage not in {'develop', 'render', 'publish'}:
        raise ValueError('étape inconnue')
    if scene.get('rejected') is True:
        reasons.append('direction écartée')
    if scene.get('status') == 'reserve':
        reasons.append('piste en réserve, hors développement actif')
    if stage == 'develop':
        if not scene.get('next_action'):
            reasons.append('prochaine action manquante')
        return reasons
    if scene.get('video_deferred') is True:
        reasons.append('vidéo différée par Morgan')
    for key in ('goal_visible', 'causal_action_visible', 'resolution_visible', 'spatial_continuity'):
        if scene.get('checks', {}).get(key) != 'observed_pass':
            reasons.append(f'{key}: reste à démontrer')
    if not scene.get('method_by_shot'):
        reasons.append('procédé par plan manquant')
    elif scene.get('method_capability_checked') != 'observed_pass':
        reasons.append('procédé candidat : capacité pour ces plans non testée')
    if not scene.get('identity_original_refs'):
        reasons.append('originaux du protagoniste non rattachés')
    if stage == 'publish':
        artifact = scene.get('artifact', {})
        if artifact.get('media_type') != 'video' or not artifact.get('sha256'):
            reasons.append('film identifié par empreinte manquant')
        if artifact.get('technical_pass') is not True:
            reasons.append('export non contrôlé')
        for dimension in ('artistic', 'likeness'):
            if not any(approval_matches(a, artifact, dimension) for a in scene.get('approvals', [])):
                reasons.append(f'{dimension}: accord attaché à ce fichier manquant')
        if scene.get('sound_review') != 'observed_pass':
            reasons.append('son et lecture mobile non contrôlés')
        for key in ('rights_checked', 'account_ready', 'publication_authorized'):
            if scene.get(key) is not True:
                reasons.append(f'{key}: non établi')
    return reasons


def submission_gate(request, jobs, policy):
    reasons = []
    quote, cap = request.get('quoted_credits'), policy.get('cap_credits')
    if policy.get('video_deferred') is True:
        reasons.append('vidéo différée')
    if policy.get('authorized') is not True:
        reasons.append('plan de dépense non autorisé')
    if not number(quote) or quote < 0 or not number(cap) or cap < 0 or quote > cap:
        reasons.append('devis absent, invalide ou au-dessus du plafond')
    if not request.get('logical_key'):
        reasons.append('clé logique de l’essai manquante')
    active = []
    for job in jobs:
        status = job.get('status')
        if status not in NONFINAL | FINAL:
            reasons.append('état de tâche inconnu du schéma')
            active.append(job)
        elif status in NONFINAL:
            active.append(job)
        if job.get('logical_key') == request.get('logical_key') and status in NONFINAL:
            reasons.append('même essai déjà lancé ou état incertain : retrouver la tâche')
    if any(x.get('status') in {'unknown', 'timeout_unknown'} for x in active):
        reasons.append('tâche incertaine à rapprocher avant un autre lancement')
    if len(active) >= policy.get('max_in_progress', 3):
        reasons.append('limite de travaux en réalisation atteinte')
    if request.get('exploratory') is True and any(x.get('exploratory') is True for x in active):
        reasons.append('un essai exploratoire est déjà actif')
    return list(dict.fromkeys(reasons))


def metrics_errors(metrics):
    errors = []
    for key in ('platform', 'surface', 'window', 'denominator_name', 'definition_source'):
        if not metrics.get(key):
            errors.append(f'{key}: définition de mesure manquante')
    for key in ('reach', 'views', 'sends', 'shares', 'attributed_follows', 'average_watch_seconds'):
        value = metrics.get(key)
        if value is not None and (not number(value) or value < 0):
            errors.append(f'{key}: valeur finie positive, zéro observé ou null')
    if metrics.get('completion_rate') is not None and not metrics.get('native_completion_source'):
        errors.append('complétion: mesure native et définition requises')
    if metrics.get('audience_result') is True and not metrics.get('publication_ref'):
        errors.append('audience: publication source manquante')
    return errors


def derived_metrics(metrics):
    if metrics_errors(metrics):
        raise ValueError('mesures insuffisamment définies')
    reach = metrics.get('reach')
    out = {}
    for key in ('sends', 'shares', 'attributed_follows'):
        value = metrics.get(key)
        out[key + '_per_1000_reached'] = 1000 * value / reach if number(value) and number(reach) and reach > 0 else None
    duration, average = metrics.get('duration_seconds'), metrics.get('average_watch_seconds')
    out['average_portion_watched'] = average / duration if number(average) and number(duration) and duration > 0 else None
    out['completion_rate'] = metrics.get('completion_rate')
    return out


def audit_document(document):
    errors, warnings = [], []
    references = document.get('references', [])
    ids = [r.get('id') for r in references]
    if len(ids) != len(set(ids)):
        errors.append('identifiants de références en double')
    for ref in references:
        errors.extend(f"{ref.get('id')}: {e}" for e in reference_errors(ref))
    sources = {r.get('id') for r in references}
    gates = []
    for scene in document.get('scenes', []):
        for ref in scene.get('reference_ids', []):
            if ref not in sources:
                errors.append(f"{scene['id']}: référence {ref} non résolue")
        gates.append({'id': scene['id'], 'title': scene['title'],
                      'develop': scene_gate(scene, 'develop'),
                      'render': scene_gate(scene, 'render'),
                      'publish': scene_gate(scene, 'publish')})
    for asset in document.get('assets', []):
        for key in ('id', 'sha256', 'library_file_id', 'technical_evidence_ref'):
            if not asset.get(key):
                errors.append(f"asset {asset.get('id')}: {key} absent")
        if asset.get('expected_sha256') and asset['expected_sha256'] != asset['sha256']:
            errors.append(f"asset {asset['id']}: empreinte différente de la mémoire")
    for proposal in document.get('next_requests', []):
        reasons = submission_gate(proposal, document.get('jobs', []), document.get('policy', {}))
        gates.append({'request': proposal['logical_key'], 'submission': reasons})
    for metric in document.get('metrics_templates', []):
        errors.extend(metrics_errors(metric))
    for slot in document.get('historical_slots', []):
        if slot.get('proposed_at') and not slot.get('published'):
            warnings.append({'type': 'historical_slot', 'id': slot['id'],
                             'decision': 'archive ; ne pas transformer en programmation'})
    return {'schema': 'marwin.control-report/v1', 'tool_version': VERSION,
            'snapshot_at': document.get('snapshot_at'),
            'document_valid': not errors, 'errors': errors, 'warnings': warnings,
            'counts': {'references': len(references),
                       'reference_kinds': dict(Counter(r.get('kind') for r in references)),
                       'scenes': len(document.get('scenes', [])), 'assets': len(document.get('assets', []))},
            'gates': gates,
            'scope': 'Cohérence documentaire uniquement ; aucune qualité, audience ou autorisation créée.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('file', type=Path)
    parser.add_argument('--out', type=Path)
    parser.add_argument('--scene', help='identifiant exact de scène dans l’instantané')
    parser.add_argument('--stage', choices=('develop', 'render', 'publish'))
    args = parser.parse_args()
    if bool(args.scene) != bool(args.stage):
        parser.error('--scene et --stage doivent être fournis ensemble')
    document = json.loads(args.file.read_text(encoding='utf-8'))
    report = audit_document(document)
    blocked = False
    if args.scene:
        selected = [s for s in document.get('scenes', []) if s['id'] == args.scene]
        if len(selected) != 1:
            parser.error('scène absente ou ambiguë')
        reasons = scene_gate(selected[0], args.stage)
        report['selected_stage'] = {'scene': args.scene, 'stage': args.stage,
                                    'eligible_on_declared_evidence': not reasons, 'reasons': reasons}
        blocked = bool(reasons)
    output = json.dumps(report, ensure_ascii=False, indent=2) + '\n'
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(output, encoding='utf-8')
    print(output)
    return 2 if not report['document_valid'] else 3 if blocked else 0


if __name__ == '__main__':
    raise SystemExit(main())
