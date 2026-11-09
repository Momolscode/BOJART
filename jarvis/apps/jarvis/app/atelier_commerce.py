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
from statistics import median

from core import Rejected, IntegrityError, now
from atelier_devis import compute, canonical, digest, grid_blockers, text, validate_tariffs

ORIGINES = ('vitrine', 'email', 'telephone', 'atelier', 'reseau_social', 'salon', 'autre', 'demonstration')
TRANSITIONS = {
    'recue': {'qualifiee', 'doublon', 'spam', 'non_realisable', 'abandonnee'},
    'qualifiee': {'non_realisable', 'abandonnee'},
    'devis_envoye': {'refusee', 'abandonnee'},
    'acceptee': {'en_production'},
    'en_production': {'livree'},
}
HORS_ENTONNOIR = ('doublon', 'spam')
OUVERTES = ('recue', 'qualifiee', 'devis_envoye')
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
CREATE TABLE IF NOT EXISTS atelier_grille_declarations (
  rang INTEGER PRIMARY KEY AUTOINCREMENT, sha256 TEXT NOT NULL REFERENCES atelier_grilles (sha256), declaree_le TEXT NOT NULL);
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

    def _set_demande(self, db, demande_id, etat, motif=None, on=None):
        """``on`` : date déclarée de l'étape (envoi, accord) ; sinon la date de saisie."""
        row = self._demande(db, demande_id)
        milestones = json.loads(row['jalons'])
        milestones.setdefault(etat, (on or self.today()).isoformat())
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

    # -- grille tarifaire déclarée ------------------------------------------------------
    @staticmethod
    def _current_row(db):
        return db.execute('SELECT d.rang, d.sha256, d.declaree_le, g.grille_json FROM atelier_grille_declarations d '
                          'JOIN atelier_grilles g ON g.sha256 = d.sha256 ORDER BY d.rang DESC LIMIT 1').fetchone()

    def declare_grid(self, payload):
        """Fait d'une grille d'origine « declare » la grille courante. ``courante_attendue`` est
        l'empreinte lue (ou null) : une déclaration concurrente est refusée, pas écrasée."""
        required = {'request_id', 'grille', 'courante_attendue'}
        if not isinstance(payload, dict) or set(payload) != required:
            raise Rejected('Grille : request_id, grille et courante_attendue (empreinte lue, ou null) requis.')
        expected = payload['courante_attendue']
        if expected is not None and (not isinstance(expected, str) or not _SHA.fullmatch(expected)):
            raise Rejected('courante_attendue : empreinte SHA-256 lue, ou null.')
        grid = validate_tariffs(payload['grille'])
        if grid['origine'] != 'declare':
            raise Rejected('Seule une grille d’origine « declare » devient la grille courante ; la grille d’exemple reste un essai.')
        if iso_day(grid['declare_le'], 'Date de déclaration') > self.today():
            raise Rejected('Date de déclaration dans le futur.')
        sha = digest(grid)

        def apply(db):
            current = self._current_row(db)
            if (current['sha256'] if current else None) != expected:
                raise Rejected('La grille courante a changé depuis ta lecture : relis-la avant de déclarer.')
            if current and current['sha256'] == sha:
                raise Rejected('Grille identique à la grille courante : rien à déclarer.')
            if db.execute('SELECT 1 FROM atelier_grilles WHERE version=? AND sha256<>?', (grid['version'], sha)).fetchone():
                raise Rejected('Cette version de grille désigne déjà un autre contenu : choisir un nouveau libellé de version.')
            db.execute('INSERT OR IGNORE INTO atelier_grilles VALUES (?,?,?,?,?)', (sha, grid['version'], grid['origine'], canonical(grid), now()))
            rang = db.execute('INSERT INTO atelier_grille_declarations (sha256, declaree_le) VALUES (?,?)', (sha, now())).lastrowid
            return {'sha256': sha, 'version': grid['version'], 'rang': rang, 'bloquants_grille': grid_blockers(grid)}
        return self._run('grille.declarer', payload, apply)

    def current_grid(self):
        with self.store.connect() as db:
            row = self._current_row(db)
            history = db.execute('SELECT d.rang, d.sha256, d.declaree_le, g.grille_json FROM atelier_grille_declarations d '
                                 'JOIN atelier_grilles g ON g.sha256 = d.sha256 ORDER BY d.rang DESC LIMIT 20').fetchall()
        if not row:
            return {'grille': None, 'sha256': None, 'historique': []}
        grid = json.loads(row['grille_json'])
        if digest(grid) != row['sha256']:
            raise IntegrityError('Grille tarifaire courante altérée.')
        past = []
        for h in history:
            g = json.loads(h['grille_json'])
            past.append({'rang': h['rang'], 'sha256': h['sha256'], 'version': g.get('version'), 'declare_par': g.get('declare_par'),
                         'declare_le': g.get('declare_le'), 'enregistree_le': h['declaree_le'], 'intacte': digest(g) == h['sha256']})
        return {'grille': grid, 'sha256': row['sha256'], 'rang': row['rang'], 'enregistree_le': row['declaree_le'],
                'bloquants_grille': grid_blockers(grid), 'historique': past}

    # -- devis --------------------------------------------------------------------------
    def calculate(self, payload):
        required = {'request_id', 'entree'}
        if (not isinstance(payload, dict) or not required <= set(payload) <= required | {'tarifs', 'tarifs_sha256', 'numero', 'demande_id'}
                or ('tarifs' in payload) == ('tarifs_sha256' in payload)):
            raise Rejected('Calcul : request_id, entree, et tarifs ou tarifs_sha256 (+ numero ou demande_id) attendus.')
        # Une grille enregistrée se désigne par son empreinte : elle est relue et vérifiée, jamais recopiée.
        tariffs = payload['tarifs'] if 'tarifs' in payload else self.grid(payload['tarifs_sha256'])
        document = compute(payload['entree'], tariffs, today=self.today())
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
            grid = validate_tariffs(tariffs)
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
            current = self._current_row(db)
            if current and current['sha256'] != doc['tarifs_sha256']:
                raise Rejected('La grille courante a changé depuis ce calcul : recalculer le devis avec la grille courante avant de l’émettre.')
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
            if sent > date.fromisoformat(doc['valide_jusqu_au']):
                raise Rejected('Devis expiré à la date d’envoi : émettre une nouvelle version.')
            db.execute('UPDATE atelier_devis SET envoye_le=?, moyen_envoi=? WHERE numero=? AND version=?',
                       (sent.isoformat(), means, payload['numero'], payload['version']))
            if row['demande_id']:
                demande = self._demande(db, row['demande_id'])
                if demande['etat'] == 'qualifiee':
                    self._set_demande(db, demande['id'], 'devis_envoye', on=sent)
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
                    self._set_demande(db, demande['id'], 'acceptee', on=accepted)
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
        if not isinstance(payload, dict) or not required <= set(payload) <= required | {'mesure_par'}:
            raise Rejected('Relevé : ' + ', '.join(sorted(required)) + ' requis (+ mesure_par).')
        if payload['source'] not in ('mesure_operateur', 'simulation'):
            raise Rejected('Source du relevé : mesure_operateur ou simulation.')
        if payload['source'] == 'mesure_operateur':
            if 'mesure_par' not in payload:
                raise Rejected('Mesure opérateur : indiquer qui a mesuré (mesure_par).')
            measured_by = text(payload['mesure_par'], 'Mesure faite par', 80)
        elif 'mesure_par' in payload:
            raise Rejected('Un résultat simulé n’a pas de mesureur.')
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
            record = {'temps_machine_s': payload['temps_machine_s'], 'matiere': payload['matiere'], 'source': payload['source'], 'releve_le': now()}
            if payload['source'] == 'mesure_operateur':
                record['mesure_par'] = measured_by
            actual.setdefault(payload['piece_id'], []).append(record)
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
        if row['etat'] == 'emis' and self.today() > date.fromisoformat(doc['valide_jusqu_au']):
            return 'expire'
        return row['etat']

    @staticmethod
    def _planned(doc):
        """Prévu unitaire de chaque pièce, tiré de l'estimation figée dans le devis accepté."""
        planned = {}
        for piece in doc.get('pieces', []):
            est = piece.get('estimation')
            if not est:
                continue
            fdm = piece['procede'] == 'FDM'
            planned[piece['id']] = {'procede': piece['procede'], 'quantite': doc['exemplaires'] * piece['par_exemplaire'],
                                    'prevu_unitaire': {'temps_machine_s': float(est['temps_machine_s']),
                                                       'matiere': float(est['matiere_g' if fdm else 'matiere_ml']),
                                                       'unite_matiere': 'g' if fdm else 'ml'}}
        return planned

    def _pieces_vs_actual(self, command, doc):
        """Un relevé = une pièce imprimée. Seules les mesures opérateur entrent dans l'écart."""
        actual = json.loads(command['realise_json'])
        rows = []
        for ref, plan in self._planned(doc).items():
            records = actual.get(ref, [])
            measured = [r for r in records if r['source'] == 'mesure_operateur']
            row = {'piece_id': ref, **plan, 'mesures': len(measured), 'releves_operateur': measured,
                   'releves_simulation': [r for r in records if r['source'] == 'simulation'],
                   'sources': sorted({r['source'] for r in records}),
                   'ratio_temps': None, 'ratio_matiere': None, 'ecart_temps_pct': None, 'ecart_matiere_pct': None}
            if measured:
                unit = plan['prevu_unitaire']
                row['ratio_temps'] = median(r['temps_machine_s'] for r in measured) / unit['temps_machine_s']
                row['ratio_matiere'] = median(r['matiere'] for r in measured) / unit['matiere']
                row['ecart_temps_pct'] = round((row['ratio_temps'] - 1) * 100, 1)
                row['ecart_matiere_pct'] = round((row['ratio_matiere'] - 1) * 100, 1)
            rows.append(row)
        return rows

    def compare(self, command_id):
        with self.store.connect() as db:
            command = db.execute('SELECT * FROM atelier_commandes WHERE id=?', (command_id,)).fetchone()
            if not command:
                raise Rejected('Commande inconnue.')
            _, doc = self._version(db, command['numero'], command['version'], command['document_sha256'])
        return {'commande_id': command_id, 'numero': command['numero'], 'version': command['version'],
                'pieces': self._pieces_vs_actual(command, doc),
                'note': 'Écart = médiane des mesures opérateur par pièce, comparée au prévu unitaire. '
                        'Un résultat simulé ne remplace pas une mesure ; la grille n’est jamais corrigée automatiquement.'}

    def _calibration(self, db):
        """Dérive des estimations par procédé, sur toutes les commandes intactes ayant des mesures opérateur."""
        ratios, skipped = {}, 0
        for command in db.execute('SELECT * FROM atelier_commandes').fetchall():
            row = db.execute('SELECT document_json FROM atelier_devis WHERE numero=? AND version=?',
                             (command['numero'], command['version'])).fetchone()
            doc = json.loads(row['document_json']) if row else None
            if doc is None or digest(doc) != command['document_sha256']:
                skipped += 1
                continue
            for piece in self._pieces_vs_actual(command, doc):
                if piece['mesures']:
                    bucket = ratios.setdefault(piece['procede'], {'temps': [], 'matiere': []})
                    bucket['temps'].append(piece['ratio_temps'])
                    bucket['matiere'].append(piece['ratio_matiere'])
        out = {proc: {'pieces_mesurees': len(b['temps']), 'ratio_temps_median': f"{median(b['temps']):.3f}",
                      'ratio_matiere_median': f"{median(b['matiere']):.3f}"} for proc, b in sorted(ratios.items())}
        if skipped:
            out['commandes_ignorees_integrite'] = skipped
        return out

    def overview(self):
        with self.store.connect() as db:
            demandes = [{**dict(r), 'jalons': json.loads(r['jalons'])} for r in db.execute('SELECT * FROM atelier_demandes ORDER BY recue_le DESC, id LIMIT 200')]
            # Les comptes portent sur toutes les demandes, pas sur la seule liste affichée.
            every = [{'origine': r['origine'], 'etat': r['etat'], 'jalons': json.loads(r['jalons'])}
                     for r in db.execute('SELECT origine, etat, jalons FROM atelier_demandes')]
            calibration = self._calibration(db)
            versions = db.execute('SELECT * FROM atelier_devis ORDER BY numero DESC, version DESC LIMIT 400').fetchall()
            commandes = [dict(r) for r in db.execute('SELECT id, numero, version, accepte_le, etat FROM atelier_commandes ORDER BY accepte_le DESC LIMIT 200')]
            current = self._current_row(db)
        grid_now = None
        if current:
            g = json.loads(current['grille_json'])
            grid_now = {'sha256': current['sha256'], 'version': g['version'], 'declare_par': g.get('declare_par'), 'declare_le': g.get('declare_le'),
                        'intacte': digest(g) == current['sha256'], 'bloquants_grille': grid_blockers(g)}
        quotes, seen = [], set()
        for row in versions:
            doc = json.loads(row['document_json'])
            intact = digest(doc) == row['document_sha256']
            quotes.append({'numero': row['numero'], 'version': row['version'], 'dossier_id': row['dossier_id'], 'demande_id': row['demande_id'],
                           'etat': self._state(row, doc) if intact else 'altere', 'courant': row['numero'] not in seen,
                           'document_sha256': row['document_sha256'], 'titre': doc.get('titre'), 'totaux': doc.get('totaux'),
                           'emettable': doc.get('emettable'), 'bloquants_emission': doc.get('bloquants_emission'),
                           'valide_jusqu_au': doc.get('valide_jusqu_au'), 'envoye_le': row['envoye_le'], 'grille': doc.get('grille'),
                           'grille_a_jour': None if not grid_now or (doc.get('grille') or {}).get('origine') != 'declare'
                           else doc.get('tarifs_sha256') == grid_now['sha256']})
            seen.add(row['numero'])
        return {'schema': 'bojart.atelier.commerce.v1', 'demandes': demandes, 'devis': quotes, 'commandes': commandes,
                'entonnoir': self.funnel(every), 'calibration': calibration, 'grille_courante': grid_now,
                'compteurs': {'demandes': len(every), 'demandes_ouvertes': sum(d['etat'] in OUVERTES for d in every)}}

    @staticmethod
    def _delays(pairs):
        days = [(date.fromisoformat(end) - date.fromisoformat(start)).days for start, end in pairs]
        if not days:
            return None
        middle = median(days)
        return {'n': len(days), 'mediane_jours': int(middle) if middle == int(middle) else middle, 'max_jours': max(days)}

    def funnel(self, demandes):
        """Comptes réels seulement ; la démonstration est comptée à part."""
        real = [d for d in demandes if d['origine'] != 'demonstration']
        counted = [d for d in real if d['etat'] not in HORS_ENTONNOIR]
        reached = {'recues': len(counted)}
        for label, stage in (('qualifiees', 'qualifiee'), ('devis_envoyes', 'devis_envoye'), ('acceptees', 'acceptee'), ('livrees', 'livree')):
            reached[label] = sum(stage in d['jalons'] for d in counted)
        ratio = None
        if reached['devis_envoyes']:
            ratio = {'acceptees_sur_envoyes': f"{reached['acceptees']}/{reached['devis_envoyes']}"}
        sent = [d['jalons'] for d in counted if 'devis_envoye' in d['jalons']]
        delays = {'reception_a_envoi': self._delays((j['recue'], j['devis_envoye']) for j in sent),
                  'envoi_a_reponse': self._delays((j['devis_envoye'], j.get('acceptee') or j['refusee'])
                                                  for j in sent if 'acceptee' in j or 'refusee' in j)}
        return {'demandes_reelles': reached, 'exclues': {e: sum(d['etat'] == e for d in real) for e in HORS_ENTONNOIR},
                'demonstration': len(demandes) - len(real), 'rapport': ratio, 'delais': delays,
                'note': 'Comptes et délais (en jours, dates déclarées) issus des demandes enregistrées ; aucun taux extrapolé.'}
