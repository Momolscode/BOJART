"""Parc d'imprimantes BOJ.ART : inventaire déclaré, autorisations et ordres simulés.

Seul le connecteur ``simulation`` existe. Les interfaces réelles (Moonraker, OctoPrint,
PrusaLink, Bambu LAN, Elegoo SDCP) sont inventoriées mais ne reçoivent aucun ordre :
leur raccordement passe par les portes ``printer_fdm``, ``printer_resin`` et
``production_safety`` de ``launch_readiness.py``.

Règles appliquées à chaque ordre :

* une autorisation par machine ET par capacité, accordée par une personne, qui expire ;
  lire l'état n'autorise ni chauffe, ni téléversement, ni départ ;
* l'intention est écrite avant l'appel (``envoye``) ; une réponse perdue donne
  ``inconnu`` et bloque la machine jusqu'au rapprochement par une lecture d'état ;
* démarrer exige le fichier téléversé exact et la confirmation humaine du plateau libre ;
* l'arrêt logiciel n'est jamais bloqué par une autorisation et ne remplace pas
  l'arrêt d'urgence matériel.
"""
from __future__ import annotations

import json
import math
import re
import threading
import time

from core import Rejected, IntegrityError, now
from atelier_devis import canonical, digest, text

CAPACITES = ('lire_etat', 'televerser', 'chauffer', 'demarrer', 'pause', 'reprendre', 'annuler', 'arret_urgence')
INTERFACES = ('simulation', 'moonraker', 'octoprint', 'prusalink', 'bambu_lan', 'elegoo_sdcp', 'manuelle', 'inconnue')
LECTURE_MAX_MIN = 30 * 24 * 60
ACTION_MAX_MIN = 12 * 60
_MACHINE = re.compile(r'^[A-Z0-9][A-Z0-9-]{1,23}$')
_REQUEST = re.compile(r'^[A-Za-z0-9_-]{8,96}$')
_SHA = re.compile(r'^[0-9a-f]{64}$')

SCHEMA = '''
CREATE TABLE IF NOT EXISTS atelier_machines (
  id TEXT PRIMARY KEY, fiche_json TEXT NOT NULL, origine TEXT NOT NULL, revision INTEGER NOT NULL,
  maj TEXT NOT NULL, rapprochement_requis INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS atelier_autorisations (
  id INTEGER PRIMARY KEY AUTOINCREMENT, machine_id TEXT NOT NULL, capacite TEXT NOT NULL,
  accordee_par TEXT NOT NULL, motif TEXT NOT NULL, accordee_le TEXT NOT NULL, expire_epoch REAL NOT NULL,
  revoquee INTEGER NOT NULL, revocation TEXT,
  FOREIGN KEY (machine_id) REFERENCES atelier_machines (id));
CREATE TABLE IF NOT EXISTS atelier_ordres (
  id TEXT PRIMARY KEY, machine_id TEXT NOT NULL, capacite TEXT NOT NULL, parametres_json TEXT NOT NULL,
  fingerprint TEXT NOT NULL, etat TEXT NOT NULL, cree_le TEXT NOT NULL, termine_le TEXT, recu_json TEXT,
  FOREIGN KEY (machine_id) REFERENCES atelier_machines (id));
CREATE TABLE IF NOT EXISTS atelier_simulateur (
  machine_id TEXT PRIMARY KEY, etat_json TEXT NOT NULL,
  FOREIGN KEY (machine_id) REFERENCES atelier_machines (id));
'''


class LinkLost(Exception):
    """Aucune réponse de la machine : l'effet de l'ordre est inconnu."""


def validate_sheet(raw):
    required = {'id', 'origine', 'fabricant', 'modele', 'procede', 'volume_utile_mm', 'source_volume', 'matieres', 'interface'}
    if not isinstance(raw, dict) or not required <= set(raw) <= required | {'notes', 'limites'}:
        raise Rejected('Fiche machine : ' + ', '.join(sorted(required)) + ' requis.')
    if not isinstance(raw['id'], str) or not _MACHINE.fullmatch(raw['id']):
        raise Rejected('Identifiant machine : 2 à 24 caractères A-Z, 0-9 ou -.')
    if raw['origine'] not in ('simulee', 'declaree'):
        raise Rejected('Origine de la fiche : simulee ou declaree.')
    if raw['procede'] not in ('FDM', 'RESINE'):
        raise Rejected('Procédé : FDM ou RESINE.')
    volume = raw['volume_utile_mm']
    if volume is not None and (not isinstance(volume, list) or len(volume) != 3 or
                               any(type(v) not in (int, float) or not math.isfinite(v) or not 0 < v <= 2000 for v in volume)):
        raise Rejected('Volume utile : trois mesures en mm, ou null si inconnu.')
    interface = raw['interface']
    if not isinstance(interface, dict) or not {'type'} <= set(interface) <= {'type', 'adresse'} or interface['type'] not in INTERFACES:
        raise Rejected('Interface : ' + ', '.join(INTERFACES))
    if (raw['origine'] == 'simulee') != (interface['type'] == 'simulation'):
        raise Rejected('Une machine simulée utilise l’interface simulation, et elle seule.')
    if not isinstance(raw['matieres'], list) or not 1 <= len(raw['matieres']) <= 16:
        raise Rejected('Matières : 1 à 16 entrées.')
    sheet = {'id': raw['id'], 'origine': raw['origine'], 'fabricant': text(raw['fabricant'], 'Fabricant', 120),
             'modele': text(raw['modele'], 'Modèle', 160), 'procede': raw['procede'],
             'volume_utile_mm': [float(v) for v in volume] if volume else None,
             'source_volume': text(raw['source_volume'], 'Source du volume', 300),
             'matieres': [text(m, 'Matière', 80) for m in raw['matieres']],
             'interface': {'type': interface['type']}}
    if interface.get('adresse'):
        address = text(interface['adresse'], 'Adresse', 200)
        if not re.fullmatch(r'(?:https?|wss?|mqtts?)://[A-Za-z0-9.-]+(?::[0-9]{1,5})?/?', address):
            raise Rejected('Adresse : schéma://hôte[:port], sans identifiant ni secret.')
        sheet['interface']['adresse'] = address
    if 'notes' in raw:
        sheet['notes'] = text(raw['notes'], 'Notes', 2000, empty=True)
    limits = raw.get('limites', {'buse_c': 300, 'plateau_c': 110} if raw['procede'] == 'FDM' else {'cuve_c': 40})
    allowed = {'buse_c', 'plateau_c'} if raw['procede'] == 'FDM' else {'cuve_c'}
    if not isinstance(limits, dict) or set(limits) != allowed or any(type(v) not in (int, float) or not 0 < v <= 350 for v in limits.values()):
        raise Rejected('Limites de température : ' + ', '.join(sorted(allowed)))
    sheet['limites'] = limits
    return sheet


class SimulatedPrinter:
    """Machine virtuelle à état persistant. Horloge injectée ; accélération explicite."""

    def __init__(self, sheet, state, clock):
        self.sheet, self.state, self.clock = sheet, state, clock

    @staticmethod
    def initial(acceleration=1.0):
        return {'etat': 'pret', 'fichier': None, 'temperatures': {}, 'consignes': {}, 'debut_epoch': None, 'ecoule_s': 0.0,
                'acceleration': acceleration, 'panne': None, 'travaux_termines': 0, 'evenements': []}

    def _advance(self):
        s = self.state
        if s['etat'] == 'impression' and s['debut_epoch'] is not None:
            elapsed = s['ecoule_s'] + (self.clock() - s['debut_epoch']) * s['acceleration']
            if elapsed >= s['fichier']['duree_s']:
                s.update(etat='termine', ecoule_s=s['fichier']['duree_s'], debut_epoch=None, consignes={})
                s['travaux_termines'] += 1
                s['evenements'] = (s['evenements'] + [{'type': 'fin', 'a': self.clock()}])[-20:]

    def status(self):
        self._advance()
        s = self.state
        if s['panne'] == 'perte_liaison':
            raise LinkLost('Machine simulée injoignable.')
        progress = 0.0
        if s['fichier'] and s['fichier']['duree_s']:
            elapsed = s['ecoule_s'] + ((self.clock() - s['debut_epoch']) * s['acceleration'] if s['debut_epoch'] else 0)
            progress = min(100.0, max(0.0, elapsed / s['fichier']['duree_s'] * 100))
        return {'etat': s['etat'], 'fichier': s['fichier'], 'progression_pct': round(progress, 1),
                'consignes': s['consignes'], 'travaux_termines': s['travaux_termines'], 'source': 'simulation'}

    def execute(self, capacite, params):
        self._advance()
        s = self.state
        fault = s['panne']
        if fault == 'perte_liaison':
            raise LinkLost('Aucune réponse de la machine simulée.')
        before = s['etat']
        if capacite == 'arret_urgence':
            s.update(etat='arret_urgence', debut_epoch=None, consignes={})
        elif s['etat'] == 'arret_urgence':
            raise Rejected('Machine en arrêt d’urgence : réarmement manuel sur place requis.')
        elif capacite == 'lire_etat':
            pass
        elif capacite == 'televerser':
            if s['etat'] in ('impression', 'pause', 'chauffe'):
                raise Rejected('Téléversement refusé pendant un travail en cours.')
            s.update(fichier={'sha256': params['fichier_sha256'], 'nom': params['nom'], 'duree_s': params['temps_machine_s']},
                     etat='pret', ecoule_s=0.0)
        elif capacite == 'chauffer':
            if s['etat'] not in ('pret', 'termine', 'chauffe'):
                raise Rejected('Chauffe refusée dans l’état ' + s['etat'] + '.')
            s.update(etat='chauffe', consignes=dict(params['consignes']))
        elif capacite == 'demarrer':
            if s['etat'] not in ('pret', 'chauffe'):
                raise Rejected('Départ refusé dans l’état ' + s['etat'] + '.')
            if not s['fichier'] or s['fichier']['sha256'] != params['fichier_sha256']:
                raise Rejected('Le fichier présent sur la machine n’est pas celui demandé.')
            s.update(etat='impression', debut_epoch=self.clock(), ecoule_s=0.0)
        elif capacite == 'pause':
            if s['etat'] != 'impression':
                raise Rejected('Aucune impression à mettre en pause.')
            s['ecoule_s'] += (self.clock() - s['debut_epoch']) * s['acceleration']
            s.update(etat='pause', debut_epoch=None)
        elif capacite == 'reprendre':
            if s['etat'] != 'pause':
                raise Rejected('Aucune impression en pause.')
            s.update(etat='impression', debut_epoch=self.clock())
        elif capacite == 'annuler':
            if s['etat'] not in ('impression', 'pause', 'chauffe'):
                raise Rejected('Rien à annuler.')
            s.update(etat='pret', debut_epoch=None, ecoule_s=0.0, consignes={}, fichier=None)
        if fault == 'erreur_buse' and capacite == 'demarrer':
            s.update(etat='erreur', debut_epoch=None)
        s['evenements'] = (s['evenements'] + [{'type': capacite, 'a': self.clock()}])[-20:]
        late = fault == 'reponse_tardive' and capacite not in ('lire_etat', 'arret_urgence')
        if late:
            s['panne'] = None  # l'effet est appliqué, mais l'accusé n'arrive pas à temps
            raise LinkLost('Délai dépassé avant l’accusé de la machine simulée.')
        return {'etat_avant': before, 'etat_apres': s['etat'], 'source': 'simulation'}


class Parc:
    def __init__(self, store, clock=time.time):
        self.store, self.clock = store, clock
        self.lock = threading.RLock()
        with store.connect() as db:
            db.executescript(SCHEMA)
            # Après un arrêt brutal, un ordre écrit sans accusé a un effet inconnu.
            stale = db.execute("SELECT DISTINCT machine_id FROM atelier_ordres WHERE etat='envoye'").fetchall()
            db.execute("UPDATE atelier_ordres SET etat='inconnu', termine_le=? WHERE etat='envoye'", (now(),))
            for (machine_id,) in stale:
                db.execute('UPDATE atelier_machines SET rapprochement_requis=1 WHERE id=?', (machine_id,))

    # -- inventaire ---------------------------------------------------------------------
    def declare(self, payload):
        if not isinstance(payload, dict) or set(payload) != {'fiche', 'revision_attendue'}:
            raise Rejected('Déclaration : fiche et revision_attendue requis (0 pour une nouvelle machine).')
        sheet = validate_sheet(payload['fiche'])
        expected = payload['revision_attendue']
        if type(expected) is not int or expected < 0:
            raise Rejected('Révision attendue invalide.')
        with self.lock, self.store.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            row = db.execute('SELECT * FROM atelier_machines WHERE id=?', (sheet['id'],)).fetchone()
            current = row['revision'] if row else 0
            if expected != current:
                raise Rejected('Fiche modifiée ailleurs : relire avant d’enregistrer.')
            if row and row['origine'] != sheet['origine']:
                raise Rejected('Une fiche simulée ne devient pas une machine réelle : créer une autre fiche.')
            if row and json.loads(row['fiche_json']) == sheet:
                return {'machine_id': sheet['id'], 'revision': current, 'replayed': True}
            if row:
                db.execute('UPDATE atelier_machines SET fiche_json=?, revision=?, maj=? WHERE id=?', (canonical(sheet), current + 1, now(), sheet['id']))
                # Une fiche modifiée invalide les autorisations accordées sur l'ancienne.
                db.execute("UPDATE atelier_autorisations SET revoquee=1, revocation='fiche_modifiee' WHERE machine_id=? AND revoquee=0", (sheet['id'],))
            else:
                db.execute('INSERT INTO atelier_machines VALUES (?,?,?,?,?,0)', (sheet['id'], canonical(sheet), sheet['origine'], 1, now()))
                if sheet['origine'] == 'simulee':
                    db.execute('INSERT INTO atelier_simulateur VALUES (?,?)', (sheet['id'], canonical(SimulatedPrinter.initial())))
            return {'machine_id': sheet['id'], 'revision': current + 1, 'replayed': False}

    def _machine(self, db, machine_id):
        row = db.execute('SELECT * FROM atelier_machines WHERE id=?', (machine_id,)).fetchone()
        if not row:
            raise Rejected('Machine inconnue.')
        return row, json.loads(row['fiche_json'])

    # -- autorisations -------------------------------------------------------------------
    def grant(self, payload):
        required = {'machine_id', 'capacite', 'accordee_par', 'motif', 'duree_min'}
        if not isinstance(payload, dict) or set(payload) != required:
            raise Rejected('Autorisation : ' + ', '.join(sorted(required)) + ' requis.')
        capacite = payload['capacite']
        if capacite not in CAPACITES or capacite == 'arret_urgence':
            raise Rejected('Capacité inconnue ; l’arrêt ne demande pas d’autorisation.')
        minutes = payload['duree_min']
        limit = LECTURE_MAX_MIN if capacite == 'lire_etat' else ACTION_MAX_MIN
        if type(minutes) is not int or not 1 <= minutes <= limit:
            raise Rejected(f'Durée : 1 à {limit} minutes pour cette capacité.')
        person = text(payload['accordee_par'], 'Personne qui autorise', 120)
        motif = text(payload['motif'], 'Motif', 300)
        with self.lock, self.store.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            row, sheet = self._machine(db, payload['machine_id'])
            if sheet['interface']['type'] != 'simulation' and capacite != 'lire_etat':
                raise Rejected('Connecteur réel non qualifié : seule la lecture d’état peut être préparée pour cette machine.')
            expires = self.clock() + minutes * 60
            cursor = db.execute('INSERT INTO atelier_autorisations (machine_id, capacite, accordee_par, motif, accordee_le, expire_epoch, revoquee) '
                                'VALUES (?,?,?,?,?,?,0)', (row['id'], capacite, person, motif, now(), expires))
            return {'autorisation_id': cursor.lastrowid, 'machine_id': row['id'], 'capacite': capacite, 'expire_epoch': expires}

    def revoke(self, payload):
        if not isinstance(payload, dict) or set(payload) != {'autorisation_id', 'motif'} or type(payload['autorisation_id']) is not int:
            raise Rejected('Révocation : autorisation_id et motif requis.')
        with self.lock, self.store.connect() as db:
            changed = db.execute('UPDATE atelier_autorisations SET revoquee=1, revocation=? WHERE id=? AND revoquee=0',
                                 (text(payload['motif'], 'Motif', 300), payload['autorisation_id'])).rowcount
        return {'autorisation_id': payload['autorisation_id'], 'revoquee': True, 'deja_revoquee': not changed}

    def _authorized(self, db, machine_id, capacite):
        return db.execute('SELECT id, accordee_par FROM atelier_autorisations WHERE machine_id=? AND capacite=? AND revoquee=0 AND expire_epoch>? '
                          'ORDER BY expire_epoch DESC LIMIT 1', (machine_id, capacite, self.clock())).fetchone()

    # -- ordres --------------------------------------------------------------------------
    def _params(self, capacite, sheet, raw):
        if not isinstance(raw, dict):
            raise Rejected('Paramètres : objet attendu.')
        if capacite == 'televerser':
            if set(raw) != {'fichier_sha256', 'nom', 'temps_machine_s', 'marque_simulation'}:
                raise Rejected('Téléversement : fichier_sha256, nom, temps_machine_s, marque_simulation.')
            if not isinstance(raw['fichier_sha256'], str) or not _SHA.fullmatch(raw['fichier_sha256']):
                raise Rejected('Empreinte SHA-256 du fichier requise.')
            if type(raw['temps_machine_s']) not in (int, float) or not 0 < raw['temps_machine_s'] <= 30 * 86400:
                raise Rejected('Durée estimée du fichier invalide.')
            if type(raw['marque_simulation']) is not bool:
                raise Rejected('marque_simulation : booléen.')
            if raw['marque_simulation'] and sheet['origine'] != 'simulee':
                raise Rejected('Fichier tranché avec un profil de simulation : interdit sur une machine réelle.')
            return {'fichier_sha256': raw['fichier_sha256'], 'nom': text(raw['nom'], 'Nom de fichier', 160),
                    'temps_machine_s': float(raw['temps_machine_s']), 'marque_simulation': raw['marque_simulation']}
        if capacite == 'chauffer':
            if set(raw) != {'consignes'} or not isinstance(raw['consignes'], dict) or not raw['consignes']:
                raise Rejected('Chauffe : consignes {nom: °C}.')
            for key, value in raw['consignes'].items():
                if key not in sheet['limites']:
                    raise Rejected(f'Consigne {key} absente des limites de cette machine.')
                if type(value) not in (int, float) or not 0 <= value <= sheet['limites'][key]:
                    raise Rejected(f'Consigne {key} hors limite ({sheet["limites"][key]} °C).')
            return {'consignes': dict(raw['consignes'])}
        if capacite == 'demarrer':
            if set(raw) != {'fichier_sha256', 'plateau_libre_confirme', 'operateur'}:
                raise Rejected('Départ : fichier_sha256, plateau_libre_confirme, operateur.')
            if raw['plateau_libre_confirme'] is not True:
                raise Rejected('Confirmer sur place que le plateau est libre et propre avant le départ.')
            if not isinstance(raw['fichier_sha256'], str) or not _SHA.fullmatch(raw['fichier_sha256']):
                raise Rejected('Empreinte SHA-256 du fichier requise.')
            return {'fichier_sha256': raw['fichier_sha256'], 'plateau_libre_confirme': True, 'operateur': text(raw['operateur'], 'Opérateur', 120)}
        if raw:
            raise Rejected('Cette capacité ne prend aucun paramètre.')
        return {}

    def order(self, payload):
        required = {'request_id', 'machine_id', 'capacite', 'parametres'}
        if not isinstance(payload, dict) or set(payload) != required:
            raise Rejected('Ordre : ' + ', '.join(sorted(required)) + ' requis.')
        if not isinstance(payload['request_id'], str) or not _REQUEST.fullmatch(payload['request_id']):
            raise Rejected('request_id : 8 à 96 caractères A-Z, a-z, 0-9, _ ou -.')
        capacite = payload['capacite']
        if capacite not in CAPACITES:
            raise Rejected('Capacité inconnue. Aucun ordre envoyé.')
        fingerprint = digest(payload)
        with self.lock:
            with self.store.connect() as db:
                db.execute('BEGIN IMMEDIATE')
                old = db.execute('SELECT * FROM atelier_ordres WHERE id=?', (payload['request_id'],)).fetchone()
                if old:
                    if old['fingerprint'] != fingerprint:
                        raise Rejected('Identifiant déjà utilisé pour un autre ordre. Rien n’a été envoyé.')
                    return {'ordre_id': old['id'], 'etat': old['etat'], 'recu': json.loads(old['recu_json'] or 'null'), 'replayed': True}
                row, sheet = self._machine(db, payload['machine_id'])
                params = self._params(capacite, sheet, payload['parametres'])
                if sheet['interface']['type'] != 'simulation':
                    raise Rejected(f'Connecteur {sheet["interface"]["type"]} non raccordé : aucun ordre envoyé.')
                if row['rapprochement_requis'] and capacite not in ('lire_etat', 'arret_urgence'):
                    raise Rejected('Résultat d’un ordre précédent inconnu : lire l’état de la machine avant tout nouvel ordre.')
                grant = None
                if capacite != 'arret_urgence':
                    grant = self._authorized(db, row['id'], capacite)
                    if not grant:
                        raise Rejected(f'Aucune autorisation active « {capacite} » pour {row["id"]}. Aucun ordre envoyé.')
                # L'intention est durable avant l'appel : un arrêt brutal la rendra « inconnue ».
                db.execute('INSERT INTO atelier_ordres (id, machine_id, capacite, parametres_json, fingerprint, etat, cree_le) VALUES (?,?,?,?,?,?,?)',
                           (payload['request_id'], row['id'], capacite, canonical(params), fingerprint, 'envoye', now()))
            with self.store.connect() as db:
                db.execute('BEGIN IMMEDIATE')
                sim_row = db.execute('SELECT etat_json FROM atelier_simulateur WHERE machine_id=?', (row['id'],)).fetchone()
                if not sim_row:
                    raise IntegrityError('État du simulateur absent.')
                printer = SimulatedPrinter(sheet, json.loads(sim_row['etat_json']), self.clock)
                receipt = {'ordre_id': payload['request_id'], 'machine_id': row['id'], 'capacite': capacite, 'autorisation_id': grant['id'] if grant else None,
                           'autorise_par': grant['accordee_par'] if grant else None, 'connecteur': 'simulation', 'physique': False,
                           'accuse': 'logiciel_simule'}
                try:
                    outcome = printer.execute(capacite, params)
                    state, receipt = 'confirme', {**receipt, **outcome}
                except LinkLost as lost:
                    state, receipt = 'inconnu', {**receipt, 'erreur': str(lost), 'consigne': 'Lire l’état avant tout nouvel ordre ; ne pas relancer à l’aveugle.'}
                    db.execute('UPDATE atelier_machines SET rapprochement_requis=1 WHERE id=?', (row['id'],))
                except Rejected as refused:
                    state, receipt = 'refuse_machine', {**receipt, 'erreur': str(refused)}
                if state == 'confirme' and capacite == 'lire_etat':
                    receipt['observation'] = printer.status()
                    unknown = db.execute("SELECT id, recu_json FROM atelier_ordres WHERE machine_id=? AND etat IN ('inconnu','inconnu_restauration')",
                                         (row['id'],)).fetchall()
                    for item in unknown:
                        merged = {**json.loads(item['recu_json'] or '{}'), 'rapproche_par': payload['request_id'], 'etat_observe': receipt['observation']['etat']}
                        db.execute("UPDATE atelier_ordres SET etat='rapproche', recu_json=? WHERE id=?", (canonical(merged), item['id']))
                    db.execute('UPDATE atelier_machines SET rapprochement_requis=0 WHERE id=?', (row['id'],))
                    receipt['ordres_rapproches'] = [item['id'] for item in unknown]
                receipt['horodatage'] = now()
                db.execute('UPDATE atelier_simulateur SET etat_json=? WHERE machine_id=?', (canonical(printer.state), row['id']))
                db.execute('UPDATE atelier_ordres SET etat=?, termine_le=?, recu_json=? WHERE id=?', (state, now(), canonical(receipt), payload['request_id']))
            return {'ordre_id': payload['request_id'], 'etat': state, 'recu': receipt, 'replayed': False}

    # -- simulation : pannes et vitesse (essais seulement) -----------------------------
    def simulate(self, payload):
        if not isinstance(payload, dict) or set(payload) != {'machine_id', 'panne', 'acceleration'}:
            raise Rejected('Simulation : machine_id, panne, acceleration.')
        if payload['panne'] not in (None, 'perte_liaison', 'reponse_tardive', 'erreur_buse'):
            raise Rejected('Panne simulée inconnue.')
        speed = payload['acceleration']
        if type(speed) not in (int, float) or not 1 <= speed <= 3600:
            raise Rejected('Accélération : 1 à 3600.')
        with self.lock, self.store.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            row, sheet = self._machine(db, payload['machine_id'])
            if sheet['origine'] != 'simulee':
                raise Rejected('Une panne ne se simule que sur une machine simulée.')
            sim = db.execute('SELECT etat_json FROM atelier_simulateur WHERE machine_id=?', (row['id'],)).fetchone()
            printer = SimulatedPrinter(sheet, json.loads(sim['etat_json']), self.clock)
            printer._advance()
            state = printer.state
            if state['etat'] == 'impression':
                state['ecoule_s'] += (self.clock() - state['debut_epoch']) * state['acceleration']
                state['debut_epoch'] = self.clock()
            state.update(panne=payload['panne'], acceleration=float(speed))
            db.execute('UPDATE atelier_simulateur SET etat_json=? WHERE machine_id=?', (canonical(state), row['id']))
        return {'machine_id': row['id'], 'panne': payload['panne'], 'acceleration': float(speed), 'simulation': True}

    # -- lecture ------------------------------------------------------------------------
    def overview(self):
        with self.store.connect() as db:
            machines = db.execute('SELECT * FROM atelier_machines ORDER BY id').fetchall()
            out = []
            for row in machines:
                sheet = json.loads(row['fiche_json'])
                grants = [dict(g) for g in db.execute('SELECT id, capacite, accordee_par, motif, expire_epoch FROM atelier_autorisations '
                                                      'WHERE machine_id=? AND revoquee=0 AND expire_epoch>? ORDER BY capacite', (row['id'], self.clock()))]
                observation = {'lu': False, 'raison': 'Autorisation « lire_etat » requise.'}
                if sheet['interface']['type'] != 'simulation':
                    observation = {'lu': False, 'raison': f'Connecteur {sheet["interface"]["type"]} non raccordé.'}
                elif any(g['capacite'] == 'lire_etat' for g in grants):
                    sim = db.execute('SELECT etat_json FROM atelier_simulateur WHERE machine_id=?', (row['id'],)).fetchone()
                    try:
                        observation = {'lu': True, **SimulatedPrinter(sheet, json.loads(sim['etat_json']), self.clock).status()}
                    except LinkLost as lost:
                        observation = {'lu': False, 'raison': str(lost)}
                orders = [{'id': o['id'], 'capacite': o['capacite'], 'etat': o['etat'], 'cree_le': o['cree_le'], 'termine_le': o['termine_le'],
                           'recu': json.loads(o['recu_json'] or 'null')} for o in db.execute(
                    'SELECT id, capacite, etat, cree_le, termine_le, recu_json FROM atelier_ordres WHERE machine_id=? ORDER BY cree_le DESC LIMIT 8', (row['id'],))]
                out.append({'fiche': sheet, 'revision': row['revision'], 'rapprochement_requis': bool(row['rapprochement_requis']),
                            'autorisations': grants, 'observation': observation, 'derniers_ordres': orders})
        return {'schema': 'bojart.atelier.parc.v1', 'machines': out, 'connecteurs_reels': False,
                'note': 'États simulés : aucune imprimante réelle contactée. L’arrêt logiciel ne remplace pas l’arrêt d’urgence matériel.'}
