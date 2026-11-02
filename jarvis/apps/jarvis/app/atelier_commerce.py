"""Demandes clients, devis versionnés, accords et commandes de l'atelier BOJ.ART.

Tables dans ``missions.sqlite3`` (base des dossiers) : elles suivent donc la sauvegarde
globale existante, sans sixième base. Chaque écriture porte un ``request_id`` :
un rejeu identique renvoie le même reçu, un même identifiant pour une autre demande est
refusé. Un devis émis est figé et vérifié par son empreinte à chaque lecture.
Aucun message n'est envoyé : « envoyé » et « accepté » sont déclarés par l'opérateur
avec leur preuve.
"""
from __future__ import annotations

import hashlib
import json
import re
import threading
from datetime import date, timedelta

from core import Rejected, IntegrityError, now
from atelier_devis import compute, canonical, digest, text, validate_tariffs

ORIGINES = ('vitrine', 'email', 'telephone', 'atelier', 'reseau_social', 'salon', 'autre', 'demonstration')
TRANSITIONS = {
    'recue': {'qualifiee', 'doublon', 'spam', 'non_realisable', 'abandonnee'},
    'qualifiee': {'non_realisable', 'abandonnee'},
    'devis_envoye': {'refusee', 'abandonnee'},
    'acceptee': {'en_production'},
    'en_production': {'livree'},
}
HORS_ENTONNOIR = ('doublon', 'spam')
_REQUEST = re.compile(r'^[A-Za-z0-9_-]{8,96}$')
_NUMERO = re.compile(r'^DV-[0-9]{4}-[0-9]{4}$')
_SHA = re.compile(r'^[0-9a-f]{64}$')

SCHEMA = '''
CREATE TABLE IF NOT EXISTS atelier_journal (
  seq INTEGER PRIMARY KEY AUTOINCREMENT, request_id TEXT NOT NULL UNIQUE, kind TEXT NOT NULL,
  fingerprint TEXT NOT NULL, result_json TEXT NOT NULL, at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS atelier_demandes (
  id TEXT PRIMARY KEY, dossier_id TEXT NOT NULL, origine TEXT NOT NULL, reference_source TEXT NOT NULL,
  recue_le TEXT NOT NULL, resume TEXT NOT NULL, etat TEXT NOT NULL, revision INTEGER NOT NULL,
  motif TEXT, maj TEXT NOT NULL, jalons TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS atelier_devis (
  numero TEXT NOT NULL, version INTEGER NOT NULL, dossier_id TEXT NOT NULL, demande_id TEXT,
  etat TEXT NOT NULL, document_json TEXT NOT NULL, document_sha256 TEXT NOT NULL, cree_le TEXT NOT NULL,
  emis_le TEXT, envoye_le TEXT, moyen_envoi TEXT, PRIMARY KEY (numero, version));
CREATE TABLE IF NOT EXISTS atelier_grilles (
  sha256 TEXT PRIMARY KEY, version TEXT NOT NULL, origine TEXT NOT NULL, grille_json TEXT NOT NULL, enregistree_le TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS atelier_commandes (
  id TEXT PRIMARY KEY, numero TEXT NOT NULL, version INTEGER NOT NULL, document_sha256 TEXT NOT NULL,
  accepte_le TEXT NOT NULL, preuve TEXT NOT NULL, etat TEXT NOT NULL, realise_json TEXT NOT NULL,
  FOREIGN KEY (numero, version) REFERENCES atelier_devis (numero, version));
'''


def iso_day(value, name):
    if not isinstance(value, str) or not re.fullmatch(r'[0-9]{4}-[0-9]{2}-[0-9]{2}', value):
        raise Rejected(f'{name} : date AAAA-MM-JJ attendue.')
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise Rejected(f'{name} : date inexistante.') from exc


def short_id(prefix, request_id):
    return prefix + hashlib.sha256(request_id.encode('utf-8')).hexdigest()[:12].upper()


class Commerce:
    def __init__(self, store, today=date.today):
        self.store = store
        self.today = today
        self.lock = threading.RLock()
        with store.connect() as db:
            db.executescript(SCHEMA)

    # -- reçus idempotents ------------------------------------------------------------
    def _run(self, kind, payload, apply):
        request_id = payload.get('request_id') if isinstance(payload, dict) else None
        if not isinstance(request_id, str) or not _REQUEST.fullmatch(request_id):
            raise Rejected('request_id : 8 à 96 caractères A-Z, a-z, 0-9, _ ou -.')
        fingerprint = digest({'kind': kind, 'payload': payload})
        with self.lock, self.store.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            old = db.execute('SELECT kind, fingerprint, result_json FROM atelier_journal WHERE request_id=?', (request_id,)).fetchone()
            if old:
                if old['kind'] != kind or old['fingerprint'] != fingerprint:
                    raise Rejected('Identifiant déjà utilisé pour une autre demande. Rien n’a été modifié.')
                return {**json.loads(old['result_json']), 'replayed': True}
            result = apply(db)
            result = {**result, 'request_id': request_id, 'kind': kind, 'replayed': False, 'external_message_sent': False}
            db.execute('INSERT INTO atelier_journal (request_id, kind, fingerprint, result_json, at) VALUES (?,?,?,?,?)',
                       (request_id, kind, fingerprint, canonical(result), now()))
            return result

    def _demande(self, db, demande_id):
        row = db.execute('SELECT * FROM atelier_demandes WHERE id=?', (demande_id,)).fetchone()
        if not row:
            raise Rejected('Demande inconnue.')
        return row

    def _set_demande(self, db, demande_id, etat, motif=None):
        row = self._demande(db, demande_id)
        milestones = json.loads(row['jalons'])
        milestones.setdefault(etat, self.today().isoformat())
        db.execute('UPDATE atelier_demandes SET etat=?, motif=COALESCE(?, motif), revision=revision+1, maj=?, jalons=? WHERE id=?',
                   (etat, motif, now(), canonical(milestones), demande_id))

    # -- demandes ------------------------------------------------------------------------
    def receive(self, payload):
        required = {'request_id', 'dossier_id', 'origine', 'reference_source', 'recue_le', 'resume'}
        if not isinstance(payload, dict) or set(payload) != required:
            raise Rejected('Demande : ' + ', '.join(sorted(required)) + ' requis.')
        if payload['origine'] not in ORIGINES:
            raise Rejected('Origine inconnue : ' + ', '.join(ORIGINES))
        received = iso_day(payload['recue_le'], 'Date de réception')
        if received > self.today():
            raise Rejected('Date de réception dans le futur.')
        reference = text(payload['reference_source'], 'Référence source', 120)
        summary = text(payload['resume'], 'Résumé technique', 2000)
        if re.search(r'[\w.+-]+@[\w-]+\.[\w.]+|(?:\+33|0)[1-9](?:[ .-]?[0-9]{2}){4}', summary):
            raise Rejected('Le résumé technique ne doit contenir ni e-mail ni téléphone : ils restent dans la boîte source.')
        self.store.require_project(payload['dossier_id'])

        def apply(db):
            demande_id = short_id('DEM-', payload['request_id'])
            db.execute('INSERT INTO atelier_demandes VALUES (?,?,?,?,?,?,?,?,?,?,?)',
                       (demande_id, payload['dossier_id'], payload['origine'], reference, received.isoformat(), summary,
                        'recue', 1, None, now(), canonical({'recue': received.isoformat()})))
            return {'demande_id': demande_id, 'etat': 'recue', 'revision': 1}
        return self._run('demande.recevoir', payload, apply)

    def transition(self, payload):
        required = {'request_id', 'demande_id', 'revision_attendue', 'etat', 'motif'}
        if not isinstance(payload, dict) or set(payload) != required:
            raise Rejected('Changement d’état : ' + ', '.join(sorted(required)) + ' requis.')
        motif = text(payload['motif'], 'Motif', 300)

        def apply(db):
            row = self._demande(db, payload['demande_id'])
            if type(payload['revision_attendue']) is not int or payload['revision_attendue'] != row['revision']:
                raise Rejected('La demande a changé depuis son affichage : relire avant de modifier.')
            if payload['etat'] not in TRANSITIONS.get(row['etat'], set()):
                raise Rejected(f'Passage {row["etat"]} → {payload["etat"]} non permis ici.')
            self._set_demande(db, row['id'], payload['etat'], motif)
            return {'demande_id': row['id'], 'etat': payload['etat'], 'revision': row['revision'] + 1}
        return self._run('demande.etat', payload, apply)

    # -- devis --------------------------------------------------------------------------
    def calculate(self, payload):
        required = {'request_id', 'entree', 'tarifs'}
        if not isinstance(payload, dict) or not required <= set(payload) <= required | {'numero', 'demande_id'}:
            raise Rejected('Calcul : request_id, entree, tarifs (+ numero ou demande_id) attendus.')
        document = compute(payload['entree'], payload['tarifs'], today=self.today())
        self.store.require_project(document['dossier_id'])

        def apply(db):
            demande_id = payload.get('demande_id')
            numero = payload.get('numero')
            if demande_id is not None:
                demande = self._demande(db, demande_id)
                if demande['dossier_id'] != document['dossier_id']:
                    raise Rejected('Cette demande appartient à un autre dossier.')
                if demande['etat'] not in ('qualifiee', 'devis_envoye'):
                    raise Rejected('Qualifier la demande avant de la chiffrer.')
            if numero is None:
                year = self.today().year
                count = db.execute("SELECT COUNT(DISTINCT numero) FROM atelier_devis WHERE numero LIKE ?", (f'DV-{year}-%',)).fetchone()[0]
                numero, version = f'DV-{year}-{count + 1:04d}', 1
            else:
                if not isinstance(numero, str) or not _NUMERO.fullmatch(numero):
                    raise Rejected('Numéro de devis DV-AAAA-NNNN attendu.')
                last = db.execute('SELECT * FROM atelier_devis WHERE numero=? ORDER BY version DESC LIMIT 1', (numero,)).fetchone()
                if not last:
                    raise Rejected('Devis inconnu.')
                if last['dossier_id'] != document['dossier_id']:
                    raise Rejected('Une révision garde le dossier du devis.')
                if last['etat'] in ('accepte', 'refuse'):
                    raise Rejected('Devis clos : en créer un nouveau.')
                if demande_id is not None and last['demande_id'] not in (None, demande_id):
                    raise Rejected('Une révision garde la demande du devis.')
                demande_id = demande_id or last['demande_id']
                version = last['version'] + 1
                db.execute("UPDATE atelier_devis SET etat='remplace' WHERE numero=? AND etat='brouillon'", (numero,))
            doc = {**document, 'numero': numero, 'version': version}
            grid = validate_tariffs(payload['tarifs'])
            # La grille exacte reste consultable : le devis se recalcule à l'identique.
            db.execute('INSERT OR IGNORE INTO atelier_grilles VALUES (?,?,?,?,?)',
                       (document['tarifs_sha256'], grid['version'], grid['origine'], canonical(grid), now()))
            sha = digest(doc)
            db.execute('INSERT INTO atelier_devis (numero, version, dossier_id, demande_id, etat, document_json, document_sha256, cree_le) '
                       'VALUES (?,?,?,?,?,?,?,?)', (numero, version, doc['dossier_id'], demande_id, 'brouillon', canonical(doc), sha, now()))
            return {'numero': numero, 'version': version, 'etat': 'brouillon', 'document_sha256': sha,
                    'emettable': doc['emettable'], 'bloquants_emission': doc['bloquants_emission'], 'totaux': doc['totaux']}
        return self._run('devis.calculer', payload, apply)

    def _version(self, db, numero, version, sha=None):
        row = db.execute('SELECT * FROM atelier_devis WHERE numero=? AND version=?', (numero, version)).fetchone()
        if not row:
            raise Rejected('Version de devis inconnue.')
        doc = json.loads(row['document_json'])
        if digest(doc) != row['document_sha256']:
            raise IntegrityError(f'Devis {numero} v{version} altéré : empreinte différente.')
        if sha is not None and sha != row['document_sha256']:
            raise Rejected('Cette version a changé depuis son affichage : relire le document avant de continuer.')
        return row, doc

    def issue(self, payload):
        required = {'request_id', 'numero', 'version', 'document_sha256', 'destinataire'}
        if not isinstance(payload, dict) or set(payload) != required:
            raise Rejected('Émission : ' + ', '.join(sorted(required)) + ' requis.')
        recipient = text(payload['destinataire'], 'Destinataire (nom et adresse)', 400)

        def apply(db):
            row, doc = self._version(db, payload['numero'], payload['version'], payload['document_sha256'])
            if row['etat'] != 'brouillon':
                raise Rejected('Seul un brouillon courant peut être émis.')
            if not doc['emettable']:
                raise Rejected('Émission impossible : ' + ' '.join(doc['bloquants_emission']))
            today = self.today()
            days = (date.fromisoformat(doc['valide_jusqu_au']) - date.fromisoformat(doc['date_calcul'])).days
            issued = {**doc, 'statut': 'emis', 'emis_le': today.isoformat(),
                      'valide_jusqu_au': (today + timedelta(days=days)).isoformat(), 'destinataire': recipient}
            sha = digest(issued)
            db.execute("UPDATE atelier_devis SET etat='remplace' WHERE numero=? AND etat='emis'", (payload['numero'],))
            db.execute("UPDATE atelier_devis SET etat='emis', document_json=?, document_sha256=?, emis_le=? WHERE numero=? AND version=?",
                       (canonical(issued), sha, now(), payload['numero'], payload['version']))
            return {'numero': payload['numero'], 'version': payload['version'], 'etat': 'emis', 'document_sha256': sha,
                    'valide_jusqu_au': issued['valide_jusqu_au']}
        return self._run('devis.emettre', payload, apply)

    def mark_sent(self, payload):
        required = {'request_id', 'numero', 'version', 'document_sha256', 'moyen', 'envoye_le'}
        if not isinstance(payload, dict) or set(payload) != required:
            raise Rejected('Envoi déclaré : ' + ', '.join(sorted(required)) + ' requis.')
        means = text(payload['moyen'], 'Moyen d’envoi', 120)
        sent = iso_day(payload['envoye_le'], 'Date d’envoi')

        def apply(db):
            row, doc = self._version(db, payload['numero'], payload['version'], payload['document_sha256'])
            if row['etat'] != 'emis':
                raise Rejected('Seule la version émise courante peut être déclarée envoyée.')
            if sent < date.fromisoformat(doc['emis_le']) or sent > self.today():
                raise Rejected('Date d’envoi incohérente avec l’émission.')
            db.execute('UPDATE atelier_devis SET envoye_le=?, moyen_envoi=? WHERE numero=? AND version=?',
                       (sent.isoformat(), means, payload['numero'], payload['version']))
            if row['demande_id']:
                demande = self._demande(db, row['demande_id'])
                if demande['etat'] == 'qualifiee':
                    self._set_demande(db, demande['id'], 'devis_envoye')
            return {'numero': payload['numero'], 'version': payload['version'], 'envoye_le': sent.isoformat(), 'declare_par_operateur': True}
        return self._run('devis.envoye', payload, apply)

    def accept(self, payload):
        required = {'request_id', 'numero', 'version', 'document_sha256', 'preuve', 'accepte_le'}
        if not isinstance(payload, dict) or set(payload) != required:
            raise Rejected('Accord : ' + ', '.join(sorted(required)) + ' requis.')
        proof = text(payload['preuve'], 'Preuve de l’accord', 400)
        accepted = iso_day(payload['accepte_le'], 'Date d’accord')

        def apply(db):
            row, doc = self._version(db, payload['numero'], payload['version'], payload['document_sha256'])
            if row['etat'] == 'remplace':
                raise Rejected('Cette version a été remplacée : l’accord doit porter sur la version émise courante.')
            if row['etat'] != 'emis':
                raise Rejected('Seule une version émise peut être acceptée.')
            if not row['envoye_le']:
                raise Rejected('Déclarer l’envoi au client avant d’enregistrer son accord.')
            if accepted < date.fromisoformat(row['envoye_le']) or accepted > self.today():
                raise Rejected('Date d’accord incohérente.')
            if accepted > date.fromisoformat(doc['valide_jusqu_au']):
                raise Rejected('Devis expiré à cette date : émettre une nouvelle version.')
            command_id = short_id('CMD-', payload['request_id'])
            db.execute("UPDATE atelier_devis SET etat='accepte' WHERE numero=? AND version=?", (payload['numero'], payload['version']))
            db.execute('INSERT INTO atelier_commandes VALUES (?,?,?,?,?,?,?,?)',
                       (command_id, payload['numero'], payload['version'], row['document_sha256'], accepted.isoformat(), proof, 'acceptee', '{}'))
            if row['demande_id']:
                demande = self._demande(db, row['demande_id'])
                if demande['etat'] in ('qualifiee', 'devis_envoye'):
                    self._set_demande(db, demande['id'], 'acceptee')
            return {'commande_id': command_id, 'numero': payload['numero'], 'version': payload['version'],
                    'document_sha256': row['document_sha256'], 'production_autorisee': False,
                    'note': 'L’accord crée la commande. Chaque impression garde sa propre autorisation machine.'}
        return self._run('devis.accepter', payload, apply)

    def refuse(self, payload):
        required = {'request_id', 'numero', 'version', 'document_sha256', 'motif'}
        if not isinstance(payload, dict) or set(payload) != required:
            raise Rejected('Refus : ' + ', '.join(sorted(required)) + ' requis.')
        motif = text(payload['motif'], 'Motif', 300)

        def apply(db):
            row, _ = self._version(db, payload['numero'], payload['version'], payload['document_sha256'])
            if row['etat'] != 'emis':
                raise Rejected('Seule une version émise peut être refusée.')
            db.execute("UPDATE atelier_devis SET etat='refuse' WHERE numero=? AND version=?", (payload['numero'], payload['version']))
            if row['demande_id']:
                demande = self._demande(db, row['demande_id'])
                if demande['etat'] in ('qualifiee', 'devis_envoye'):
                    self._set_demande(db, demande['id'], 'refusee', motif)
            return {'numero': payload['numero'], 'version': payload['version'], 'etat': 'refuse'}
        return self._run('devis.refuser', payload, apply)

    def record_actual(self, payload):
        """Prévu / réel : relevé opérateur ou résultat simulé, jamais confondus."""
        required = {'request_id', 'commande_id', 'piece_id', 'temps_machine_s', 'matiere', 'source'}
        if not isinstance(payload, dict) or set(payload) != required:
            raise Rejected('Relevé : ' + ', '.join(sorted(required)) + ' requis.')
        if payload['source'] not in ('mesure_operateur', 'simulation'):
            raise Rejected('Source du relevé : mesure_operateur ou simulation.')
        for field in ('temps_machine_s', 'matiere'):
            value = payload[field]
            if type(value) not in (int, float) or not value > 0 or value > 1e7:
                raise Rejected(f'{field} : nombre positif attendu.')

        def apply(db):
            command = db.execute('SELECT * FROM atelier_commandes WHERE id=?', (payload['commande_id'],)).fetchone()
            if not command:
                raise Rejected('Commande inconnue.')
            _, doc = self._version(db, command['numero'], command['version'], command['document_sha256'])
            if payload['piece_id'] not in {line['ref'] for line in doc['lignes'] if line['type'] == 'machine'}:
                raise Rejected('Pièce absente du devis accepté.')
            actual = json.loads(command['realise_json'])
            actual.setdefault(payload['piece_id'], []).append(
                {'temps_machine_s': payload['temps_machine_s'], 'matiere': payload['matiere'], 'source': payload['source'], 'releve_le': now()})
            db.execute('UPDATE atelier_commandes SET realise_json=? WHERE id=?', (canonical(actual), command['id']))
            return {'commande_id': command['id'], 'piece_id': payload['piece_id'], 'releves': len(actual[payload['piece_id']])}
        return self._run('commande.releve', payload, apply)

    # -- lectures ------------------------------------------------------------------------
    def quote(self, numero, version):
        with self.store.connect() as db:
            row, doc = self._version(db, numero, version)
        return {'numero': numero, 'version': version, 'etat': self._state(row, doc), 'document_sha256': row['document_sha256'],
                'envoye_le': row['envoye_le'], 'moyen_envoi': row['moyen_envoi'], 'document': doc}

    def grid(self, sha256):
        if not isinstance(sha256, str) or not _SHA.fullmatch(sha256):
            raise Rejected('Empreinte de grille invalide.')
        with self.store.connect() as db:
            row = db.execute('SELECT grille_json FROM atelier_grilles WHERE sha256=?', (sha256,)).fetchone()
        if not row:
            raise Rejected('Grille inconnue.')
        grid = json.loads(row['grille_json'])
        if digest(grid) != sha256:
            raise IntegrityError('Grille tarifaire altérée.')
        return grid

    def _state(self, row, doc):
        if row['etat'] == 'emis' and row['envoye_le'] and self.today() > date.fromisoformat(doc['valide_jusqu_au']):
            return 'expire'
        return row['etat']

    def compare(self, command_id):
        with self.store.connect() as db:
            command = db.execute('SELECT * FROM atelier_commandes WHERE id=?', (command_id,)).fetchone()
            if not command:
                raise Rejected('Commande inconnue.')
            _, doc = self._version(db, command['numero'], command['version'], command['document_sha256'])
        entry_hours = {line['ref']: line['base'] for line in doc['lignes'] if line['type'] == 'machine'}
        actual = json.loads(command['realise_json'])
        rows = []
        for ref in entry_hours:
            records = actual.get(ref, [])
            rows.append({'piece_id': ref, 'prevu': entry_hours[ref], 'releves': records,
                         'sources': sorted({r['source'] for r in records})})
        return {'commande_id': command_id, 'numero': command['numero'], 'version': command['version'], 'pieces': rows,
                'note': 'Un résultat simulé ne remplace pas une mesure ; la grille n’est jamais corrigée automatiquement.'}

    def overview(self):
        with self.store.connect() as db:
            demandes = [{**dict(r), 'jalons': json.loads(r['jalons'])} for r in db.execute('SELECT * FROM atelier_demandes ORDER BY recue_le DESC, id LIMIT 200')]
            versions = db.execute('SELECT * FROM atelier_devis ORDER BY numero DESC, version DESC LIMIT 400').fetchall()
            commandes = [dict(r) for r in db.execute('SELECT id, numero, version, accepte_le, etat FROM atelier_commandes ORDER BY accepte_le DESC LIMIT 200')]
        quotes, seen = [], set()
        for row in versions:
            doc = json.loads(row['document_json'])
            intact = digest(doc) == row['document_sha256']
            quotes.append({'numero': row['numero'], 'version': row['version'], 'dossier_id': row['dossier_id'], 'demande_id': row['demande_id'],
                           'etat': self._state(row, doc) if intact else 'altere', 'courant': row['numero'] not in seen,
                           'document_sha256': row['document_sha256'], 'titre': doc.get('titre'), 'totaux': doc.get('totaux'),
                           'emettable': doc.get('emettable'), 'bloquants_emission': doc.get('bloquants_emission'),
                           'valide_jusqu_au': doc.get('valide_jusqu_au'), 'envoye_le': row['envoye_le'], 'grille': doc.get('grille')})
            seen.add(row['numero'])
        return {'schema': 'bojart.atelier.commerce.v1', 'demandes': demandes, 'devis': quotes, 'commandes': commandes,
                'entonnoir': self.funnel(demandes, quotes, commandes)}

    def funnel(self, demandes, quotes, commandes):
        """Comptes réels seulement ; la démonstration est comptée à part."""
        real = [d for d in demandes if d['origine'] != 'demonstration']
        counted = [d for d in real if d['etat'] not in HORS_ENTONNOIR]
        reached = {'recues': len(counted)}
        for label, stage in (('qualifiees', 'qualifiee'), ('devis_envoyes', 'devis_envoye'), ('acceptees', 'acceptee'), ('livrees', 'livree')):
            reached[label] = sum(stage in d['jalons'] for d in counted)
        ratio = None
        if reached['devis_envoyes']:
            ratio = {'acceptees_sur_envoyes': f"{reached['acceptees']}/{reached['devis_envoyes']}"}
        return {'demandes_reelles': reached, 'exclues': {e: sum(d['etat'] == e for d in real) for e in HORS_ENTONNOIR},
                'demonstration': len(demandes) - len(real), 'rapport': ratio,
                'note': 'Comptes issus des demandes enregistrées ; aucun taux extrapolé ni source publicitaire déduite.'}
