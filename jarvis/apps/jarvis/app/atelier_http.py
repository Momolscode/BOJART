"""Routes HTTP de l'atelier : demandes, devis et parc simulé.

Les lectures sont des GET authentifiés. Les écritures passent par ``workspace_post`` du
serveur consolidé : session, origine, JSON borné et verrou de l'espace de travail,
donc aucune écriture pendant une sauvegarde globale.
"""
from __future__ import annotations

import re
from pathlib import Path
from urllib.parse import parse_qs

from core import Rejected, IntegrityError
from dialogue import strict_json
from atelier_estimation import parse_slicer_metadata

CONFIG = Path(__file__).resolve().parents[3] / 'config' / 'atelier'
PAGES = {'/atelier': ('atelier.html', 'text/html; charset=utf-8'), '/atelier.js': ('atelier.js', 'text/javascript; charset=utf-8'),
         '/atelier.css': ('atelier.css', 'text/css; charset=utf-8')}
GETS = {*PAGES, '/api/atelier/etat', '/api/atelier/devis', '/api/atelier/grille', '/api/atelier/grille-exemple', '/api/atelier/comparaison'}
POSTS = {'/api/atelier/demande', '/api/atelier/demande/etat', '/api/atelier/devis/calculer', '/api/atelier/devis/emettre',
         '/api/atelier/devis/envoye', '/api/atelier/devis/accepter', '/api/atelier/devis/refuser', '/api/atelier/releve',
         '/api/atelier/machine', '/api/atelier/autorisation', '/api/atelier/autorisation/revoquer', '/api/atelier/ordre',
         '/api/atelier/simulation', '/api/atelier/demo', '/api/atelier/estimer'}


def load_config(name):
    return strict_json((CONFIG / name).read_bytes())


def state(server):
    commerce = server.commerce.overview()
    parc = server.parc.overview()
    return {'schema': 'bojart.atelier.etat.v1', 'commerce': commerce, 'parc': parc,
            'resume': {'machines': len(parc['machines']),
                       'machines_simulees': sum(m['fiche']['origine'] == 'simulee' for m in parc['machines']),
                       'rapprochements': sum(m['rapprochement_requis'] for m in parc['machines']),
                       'demandes_ouvertes': sum(d['etat'] in ('recue', 'qualifiee', 'devis_envoye') for d in commerce['demandes']),
                       'devis_brouillons': sum(q['courant'] and q['etat'] == 'brouillon' for q in commerce['devis']),
                       'devis_emis': sum(q['courant'] and q['etat'] == 'emis' for q in commerce['devis'])},
            'physique': False, 'envoi_externe': False}


def get(handler, parsed, app_root):
    h = handler
    if not h.check_host():
        return
    if not h.authorized():
        return h.j({'error': 'Session locale requise.'}, 401)
    try:
        q = parse_qs(parsed.query, keep_blank_values=True)
        if any(len(v) != 1 for v in q.values()):
            raise Rejected('Paramètre dupliqué.')
        route = parsed.path
        if route in PAGES:
            name, mime = PAGES[route]
            return h.response(200, (app_root / 'app' / name).read_bytes(), mime)
        if route == '/api/atelier/etat':
            if q:
                raise Rejected('Aucun paramètre attendu.')
            return h.j(state(h.server))
        if route == '/api/atelier/devis':
            if set(q) != {'numero', 'version'} or not q['version'][0].isdigit():
                raise Rejected('numero et version requis.')
            return h.j(h.server.commerce.quote(q['numero'][0], int(q['version'][0])))
        if route == '/api/atelier/grille':
            if set(q) != {'sha256'}:
                raise Rejected('sha256 requis.')
            return h.j(h.server.commerce.grid(q['sha256'][0]))
        if route == '/api/atelier/grille-exemple':
            return h.j(load_config('tarifs.exemple.json'))
        if set(q) != {'commande_id'}:
            raise Rejected('commande_id requis.')
        return h.j(h.server.commerce.compare(q['commande_id'][0]))
    except (Rejected, ValueError, UnicodeDecodeError) as exc:
        return h.j({'error': str(exc)}, 409)
    except IntegrityError as exc:
        return h.j({'error': str(exc), 'integrite': False}, 500)
    except OSError:
        return h.j({'error': 'Fichier local indisponible.'}, 500)


def seed_demo(server):
    """Démonstration idempotente : identifiants fixes, origine « simulee » / « demonstration »."""
    demo = load_config('demonstration.json')
    store, commerce, parc = server.store, server.commerce, server.parc
    store.create_project(demo['dossier']['id'], demo['dossier']['nom'])
    machines = []
    for sheet in demo['machines']:
        try:
            machines.append(parc.declare({'fiche': sheet, 'revision_attendue': 0}))
        except Rejected:
            machines.append({'machine_id': sheet['id'], 'replayed': True})
        overview = {m['fiche']['id']: m for m in parc.overview()['machines']}
        if not any(g['capacite'] == 'lire_etat' for g in overview[sheet['id']]['autorisations']):
            parc.grant({'machine_id': sheet['id'], 'capacite': 'lire_etat', 'accordee_par': 'démonstration',
                        'motif': 'Afficher l’état simulé sur le tableau atelier', 'duree_min': 7 * 24 * 60})
    received = commerce.receive({'request_id': 'demo-atelier-demande-001', 'dossier_id': demo['dossier']['id'], **demo['demande']})
    if not received['replayed']:
        commerce.transition({'request_id': 'demo-atelier-demande-qualif', 'demande_id': received['demande_id'], 'revision_attendue': 1,
                             'etat': 'qualifiee', 'motif': 'Démonstration : faisable sur le parc simulé.'})
    quote = commerce.calculate({'request_id': 'demo-atelier-devis-001', 'entree': demo['entree'],
                                'tarifs': load_config('tarifs.exemple.json'), 'demande_id': received['demande_id']})
    return {'dossier_id': demo['dossier']['id'], 'machines': machines, 'demande': received, 'devis': quote,
            'avertissement': demo['avertissement']}


def estimate(data):
    """Le navigateur n'envoie que les lignes de commentaires utiles et l'empreinte du fichier."""
    if set(data) != {'lignes', 'fichier_sha256', 'octets'}:
        raise Rejected('lignes, fichier_sha256 et octets requis.')
    if not isinstance(data['lignes'], list) or not 1 <= len(data['lignes']) <= 80 or any(not isinstance(x, str) or len(x) > 300 for x in data['lignes']):
        raise Rejected('Au plus 80 lignes de commentaires du G-code.')
    if any(not x.startswith(';') for x in data['lignes']):
        raise Rejected('Seuls les commentaires du G-code sont acceptés.')
    if type(data['octets']) is not int or data['octets'] <= 0:
        raise Rejected('Taille de fichier invalide.')
    if not isinstance(data['fichier_sha256'], str) or not re.fullmatch(r'[0-9a-f]{64}', data['fichier_sha256']):
        raise Rejected('Empreinte SHA-256 requise.')
    return parse_slicer_metadata('\n'.join(data['lignes']), sha256=data['fichier_sha256'], size=data['octets'])


def dispatch(server, path, data):
    commerce, parc = server.commerce, server.parc
    routes = {
        '/api/atelier/demande': commerce.receive, '/api/atelier/demande/etat': commerce.transition,
        '/api/atelier/devis/calculer': commerce.calculate, '/api/atelier/devis/emettre': commerce.issue,
        '/api/atelier/devis/envoye': commerce.mark_sent, '/api/atelier/devis/accepter': commerce.accept,
        '/api/atelier/devis/refuser': commerce.refuse, '/api/atelier/releve': commerce.record_actual,
        '/api/atelier/machine': parc.declare, '/api/atelier/autorisation': parc.grant,
        '/api/atelier/autorisation/revoquer': parc.revoke, '/api/atelier/ordre': parc.order,
        '/api/atelier/simulation': parc.simulate, '/api/atelier/estimer': estimate,
    }
    if path == '/api/atelier/demo':
        if data:
            raise Rejected('Aucun paramètre attendu.')
        return seed_demo(server)
    return routes[path](data)
