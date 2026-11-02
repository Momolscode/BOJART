"""Banc de la chaîne vocale Jarvis, de l'audio au reçu d'affichage.

Parcours mesuré pour chaque prise, comme la console ``tower_voice.js`` :

    début de prise (état du dossier figé, réservation du micro)
    → fin de prise (porte d'énergie de ``voice_endpoint.js``, calculée avec le corpus)
    → transcription (``POST /api/voice/transcribe``, vrai ``LocalVoice`` faster-whisper)
    → intention, garde de contexte, distribution (``POST /api/jarvis/turn``, vrai runtime)
    → affichage (écrans appairés : événements, poll, accusé, comme ``tower_screen.js``)
    → reçu (``GET /api/jarvis/turn``).

Tout passe par le vrai serveur consolidé en HTTP local, avec une base temporaire.
Les étapes internes du runtime sont chronométrées par instrumentation, sans
modifier son code. Les écrans sont des clients HTTP qui n'affichent rien : leur
accusé reste logiciel. Aucune imprimante, aucun service distant, aucun Jev.
Les mesures valent pour l'hôte, le corpus et le SHA indiqués dans le rapport.
"""
from __future__ import annotations

import hashlib
import http.client
import importlib.metadata
import json
import math
import os
import platform
import socket
import statistics
import subprocess
import sys
import tempfile
import threading
import time
import uuid
import wave
from collections import defaultdict
from contextlib import ExitStack
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

from bojart_ops import voix_corpus

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / 'jarvis/apps/jarvis/app'
SCHEMA = 'bojart.banc_voix.rapport.v1'
PROJECT = 'BOJ-PILOTE-001'
RUNTIME_SOURCES = ('voice.py', 'jarvis_runtime.py', 'jarvis_http.py', 'display_contracts.py', 'control_tower.py',
                   'tower_voice.js', 'capture.js', 'voice_endpoint.js', 'tower_screen.js')
RECEIPT_TIMEOUT = 20.0
ACK_MESSAGE = 'Banc vocal : accusé logiciel, aucun rendu.'

# Poids faster-whisper épinglés pour comparer des mesures sur des octets identiques.
# Révision Hugging Face et empreinte de model.bin relevées le 2 novembre 2026.
MODELES = {
    'base': {'depot': 'Systran/faster-whisper-base', 'revision': 'ebe41f70d5b6dfa9166e2c581c45c9c0cfc57b66',
             'model_bin_sha256': 'd01c3014881c9c6f3133c182f3d2887eb6ca1c789a7538c5c007196857a0a6a9'},
    'small': {'depot': 'Systran/faster-whisper-small', 'revision': '536b0662742c02347bc0e980a01041f333bce120',
              'model_bin_sha256': '3e305921506d8872816023e4c273e75d2419fb89b24da97b4fe7bce14170d671'},
    'medium': {'depot': 'Systran/faster-whisper-medium', 'revision': '08e178d48790749d25932bbc082711ddcfdfbc4f',
               'model_bin_sha256': '9b45e1009dcc4ab601eff815b61d80e60ce3fd8c74c1a14f4a282258286b51ae'},
    'large-v3-turbo': {'depot': 'mobiuslabsgmbh/faster-whisper-large-v3-turbo',
                       'revision': '0a363e9161cbc7ed1431c9597a8ceaf0c4f78fcf',
                       'model_bin_sha256': 'e76620f83d5f5b69efd3d87e3dc180c1bd21df9fbebacfd4335e5e1efcc018da'},
}
MODEL_FILES = ('model.bin', 'config.json', 'tokenizer.json')

# Variantes de décodage étudiées sans modifier voice.py (paramètres ajoutés à l'appel).
VARIANTES = {
    'runtime': {},  # paramètres de voice.py, vocabulaire de décodage compris
    'sans_vocabulaire': {'initial_prompt': None},  # réglage antérieur au 2 novembre 2026, pour comparaison
}


def _app_modules():
    if str(APP) not in sys.path:
        sys.path.insert(0, str(APP))
    import core
    import consolidated_workbench
    import display_contracts
    import jarvis_runtime
    import voice
    return core, consolidated_workbench, display_contracts, jarvis_runtime, voice


def sha256_bytes(raw):
    return hashlib.sha256(raw).hexdigest()


# --- Statistiques -------------------------------------------------------------

def stats(values):
    """Médiane, p95 au rang le plus proche, maximum. Aucune valeur inventée si vide."""
    values = sorted(v for v in values if v is not None)
    if not values:
        return {'n': 0, 'mediane_ms': None, 'p95_ms': None, 'max_ms': None}
    return {'n': len(values), 'mediane_ms': round(statistics.median(values), 3),
            'p95_ms': round(values[max(0, math.ceil(0.95 * len(values)) - 1)], 3),
            'max_ms': round(values[-1], 3)}


def word_error_rate(reference, hypothesis):
    ref, hyp = reference.split(), hypothesis.split()
    if not ref:
        return 0.0 if not hyp else 1.0
    previous = list(range(len(hyp) + 1))
    for i, word in enumerate(ref, 1):
        current = [i] + [0] * len(hyp)
        for j, other in enumerate(hyp, 1):
            current[j] = min(previous[j] + 1, current[j - 1] + 1, previous[j - 1] + (word != other))
        previous = current
    return previous[-1] / len(ref)


# --- Instrumentation ----------------------------------------------------------

class Instruments:
    """Chronomètres posés autour des vraies méthodes, sans changer leur code.

    Les nœuds du tour (route, garde, distribution, journal) ne sont comptés qu'au
    premier niveau : la garde rejouée dans la distribution reste dans la distribution.
    """
    NODES = ('_route', '_guard', '_dispatch', '_receipt')

    def __init__(self):
        self.lock = threading.Lock()
        self.local = threading.local()
        self.noeuds = defaultdict(lambda: defaultdict(float))
        self.asr = []
        self.validations = []
        self.chargements = []
        self.parametres_asr = None
        self.parametres_chargement = None
        self.pendant_transcription = None

    def node(self, name, function):
        instruments = self
        is_node = name in self.NODES

        def timed(runtime, *args, **kwargs):
            depth = getattr(instruments.local, 'depth', 0)
            if is_node:
                instruments.local.depth = depth + 1
            started = time.perf_counter()
            try:
                return function(runtime, *args, **kwargs)
            finally:
                elapsed = (time.perf_counter() - started) * 1000
                if is_node:
                    instruments.local.depth = depth
                if not is_node or depth == 0:
                    key = args[0].get('request_id', '?') if args and isinstance(args[0], dict) else '?'
                    with instruments.lock:
                        instruments.noeuds[key][name] += elapsed
        return timed

    def take_nodes(self, request_id):
        with self.lock:
            return dict(self.noeuds.pop(request_id, {}))

    def validate(self, function):
        instruments = self

        def timed(raw):
            started = time.perf_counter()
            try:
                return function(raw)
            finally:
                with instruments.lock:
                    instruments.validations.append((time.perf_counter() - started) * 1000)
        return timed


def _timed_whisper(instruments, variante):
    import faster_whisper
    base = faster_whisper.WhisperModel

    class TimedWhisper(base):
        def __init__(self, *args, **kwargs):
            started = time.perf_counter()
            super().__init__(*args, **kwargs)
            with instruments.lock:
                instruments.chargements.append((time.perf_counter() - started) * 1000)
                instruments.parametres_chargement = {k: v for k, v in kwargs.items()}

        def transcribe(self, audio, *args, **kwargs):
            merged = {**kwargs, **variante}
            if instruments.parametres_asr is None:
                instruments.parametres_asr = dict(merged)
            return super().transcribe(audio, *args, **merged)

    return patch.object(faster_whisper, 'WhisperModel', TimedWhisper)


# --- Client HTTP et écrans -----------------------------------------------------

class Client:
    def __init__(self, app):
        self.port = app.server_port
        self.headers = {'Cookie': 'boj_session=' + app.token, 'Origin': app.origin}

    def call(self, method, path, body=None, content_type='application/json', headers=None, timeout=300):
        connection = http.client.HTTPConnection('127.0.0.1', self.port, timeout=timeout)
        try:
            data = None
            sent = dict(self.headers)
            if body is not None:
                data = body if isinstance(body, bytes) else json.dumps(body, ensure_ascii=False).encode('utf-8')
                sent['Content-Type'] = content_type
                sent['Content-Length'] = str(len(data))
            sent.update(headers or {})
            connection.putrequest(method, path)
            for name, value in sent.items():
                connection.putheader(name, value)
            connection.endheaders()
            try:
                if data:
                    connection.send(data)
            except ConnectionError:  # BrokenPipe, Reset, Aborted (Windows) selon l'OS
                pass  # le serveur a répondu (413) et fermé avant la fin de l'envoi : lire sa réponse
            try:
                response = connection.getresponse()
                raw = response.read()
            except (ConnectionError, http.client.HTTPException) as error:
                return None, {'error': 'connexion fermée par le serveur (' + type(error).__name__ + ')'}
            return response.status, (json.loads(raw) if raw else None)
        finally:
            connection.close()


class Events(threading.Thread):
    """Client du flux /api/tower/events, comme EventSource (reprise après 250 ms)."""

    def __init__(self, client, callback):
        super().__init__(daemon=True)
        self.client, self.callback = client, callback
        self.stopped = threading.Event()
        self.connection = None

    def run(self):
        while not self.stopped.is_set():
            try:
                self.connection = http.client.HTTPConnection('127.0.0.1', self.client.port, timeout=40)
                self.connection.request('GET', '/api/tower/events', headers=self.client.headers)
                response = self.connection.getresponse()
                if response.status != 200:
                    response.read()
                    self.stopped.wait(0.25)
                    continue
                while not self.stopped.is_set():
                    line = response.fp.readline()
                    if not line:
                        break
                    if line.startswith(b'data:'):
                        self.callback()
            except (OSError, http.client.HTTPException, ValueError, AttributeError):
                pass
            finally:
                try:
                    self.connection.close()
                except Exception:
                    pass
            self.stopped.wait(0.25)

    def close(self):
        self.stopped.set()
        try:
            self.connection.sock.shutdown(socket.SHUT_RDWR)
        except Exception:
            pass


class Screen(threading.Thread):
    """Vue d'écran : appairage, événements, poll et accusé, comme tower_screen.js.

    ``retard`` retarde l'accusé, ``absent`` cesse de demander des commandes,
    ``echec`` accuse un affichage refusé. Aucun rendu n'est fait.
    """

    def __init__(self, client, role):
        super().__init__(daemon=True)
        self.client, self.role = client, role
        status, paired = client.call('POST', '/api/tower/pair', {'role': role, 'label': 'Banc vocal ' + role,
                                                                 'project_id': PROJECT})
        if status != 200:
            raise RuntimeError('Appairage refusé : ' + str(paired))
        self.screen_id = paired['screen_id']
        self.wake = threading.Event()
        self.stopped = threading.Event()
        self.retard = 0.0
        self.absent = False
        self.echec = False
        self.during_delay = None
        self.acks = []
        self.events = Events(client, self.wake.set)

    def run(self):
        self.events.start()
        while not self.stopped.is_set():
            self.wake.wait(5.0)  # repli périodique de tower_screen.js
            self.wake.clear()
            while not self.stopped.is_set() and not self.absent and self._tick():
                pass

    def _tick(self):
        try:
            status, polled = self.client.call('POST', '/api/tower/poll', {'screen_id': self.screen_id}, timeout=30)
        except OSError:
            return False
        command = polled.get('command') if status == 200 and polled else None
        if not command:
            return False
        if self.retard:
            hook, self.during_delay = self.during_delay, None
            if hook:
                hook()
            self.stopped.wait(self.retard)
        outcome = 'failed' if self.echec else 'rendered'
        try:
            status, ack = self.client.call('POST', '/api/tower/ack', {
                'screen_id': self.screen_id, 'request_id': command['request_id'], 'outcome': outcome,
                'message': ACK_MESSAGE}, timeout=30)
        except OSError:
            return False
        self.acks.append({'request_id': command['request_id'], 'http': status,
                          'etat': (ack or {}).get('state') or (ack or {}).get('error')})
        return True

    def close(self):
        self.stopped.set()
        self.wake.set()
        self.events.close()


# --- Banc ---------------------------------------------------------------------

class Bench:
    def __init__(self, state_dir, model_dir, langgraph=True, loader=None, instruments=None):
        self.state_dir = Path(state_dir)
        self.model_dir = model_dir
        self.langgraph = langgraph
        self.loader = loader
        self.instruments = instruments or Instruments()
        self.app = None
        self.starts = 0

    # Démarrage du vrai serveur consolidé, avec chronomètres.
    def start(self):
        core, consolidated, _, jarvis_runtime, voice = _app_modules()
        self.state_dir.parent.mkdir(parents=True, exist_ok=True)
        config_path = self.state_dir.parent / 'config-banc-voix.json'
        config_path.write_text(json.dumps({
            'version': 'bojart.config.v2',
            'ollama': {'enabled': False, 'url': 'http://127.0.0.1:11434', 'model': '', 'model_digest': '',
                       'offline_verified': False},
            'voice': {'enabled': True, 'model_dir': str(self.model_dir or '')}}), encoding='utf-8')
        config = consolidated.load_config(str(config_path))
        runtime = jarvis_runtime.JarvisRuntime
        with ExitStack() as stack:
            for name in ('_route', '_guard', '_dispatch', '_receipt', 'submit'):
                stack.enter_context(patch.object(runtime, name, self.instruments.node(name, getattr(runtime, name))))
            if not self.langgraph:
                stack.enter_context(patch.dict(sys.modules, {'langgraph.graph': None}))
            voice_engine = voice.LocalVoice(config['voice'], loader=self.loader)
            self.app = consolidated.ConsolidatedWorkbench(('127.0.0.1', 0), core.Store(self.state_dir),
                                                          config=config, voice=voice_engine)
        # Hors du patch de classe : l'instance garde des chronomètres autour des méthodes d'origine
        # (repli sans LangGraph) ; le graphe a déjà lié ses nœuds chronométrés à la construction.
        for name in ('_route', '_guard', '_dispatch', '_receipt', 'submit'):
            setattr(self.app.jarvis, name, self.instruments.node(name, getattr(runtime, name)).__get__(self.app.jarvis))
        original = self.app.voice.transcribe
        instruments = self.instruments

        def transcribe(raw):
            started = time.perf_counter()
            try:
                return original(raw)
            finally:
                with instruments.lock:
                    instruments.asr.append((time.perf_counter() - started) * 1000)
                hook, instruments.pendant_transcription = instruments.pendant_transcription, None
                if hook:
                    hook()
        self.app.voice.transcribe = transcribe
        self.thread = threading.Thread(target=self.app.serve_forever, kwargs={'poll_interval': 0.05}, daemon=True)
        self.thread.start()
        self.client = Client(self.app)
        self.screens = {role: Screen(self.client, role) for role in ('atelier', 'pilotage', 'creation')}
        for screen in self.screens.values():
            screen.start()
        self.console_wake = threading.Event()
        self.console_events = Events(self.client, self.console_wake.set)
        self.console_events.start()
        self.starts += 1
        self.cold = True
        return self

    def stop(self):
        if not self.app:
            return
        for screen in self.screens.values():
            screen.close()
        self.console_events.close()
        self.app.shutdown()
        self.app.server_close()
        self.thread.join(5)
        self.app = None

    def restart(self):
        self.stop()
        return self.start()

    @property
    def engine(self):
        return self.app.jarvis.graph_status

    def command_count(self):
        with self.app.tower.db() as db:
            return db.execute('SELECT COUNT(*) FROM commands').fetchone()[0]

    def bump_revision(self):
        with self.app.store.connect() as db:
            db.execute('INSERT INTO projects(id,revision) VALUES(?,1) '
                       'ON CONFLICT(id) DO UPDATE SET revision=revision+1', (PROJECT,))

    def touch_context(self):
        path = self.app.store.context_path
        path.write_bytes(path.read_bytes() + b'\n')

    # Un tour vocal complet, mesuré étape par étape.
    def voice_turn(self, audio, owner=None, request_id=None, wait_receipt=True, before_turn=None, forced_text=None):
        """``forced_text`` : texte du tour imposé après une vraie transcription, pour les cas d'erreur
        qui testent la suite de la chaîne indépendamment de la qualité de reconnaissance."""
        owner = owner or 'mic_' + uuid.uuid4().hex
        result = {'owner': owner, 'etapes_ms': {}}
        started = time.perf_counter()
        status, snapshot = self.client.call('GET', '/api/state?project_id=' + PROJECT)
        status_lease, lease = self.client.call('POST', '/api/voice/lease', {'client_id': owner, 'release': False})
        result['etapes_ms']['debut_de_prise'] = (time.perf_counter() - started) * 1000
        if status != 200 or status_lease != 200:
            result.update(issue='micro_refuse', http=status_lease, message=(lease or {}).get('error'))
            return result
        cold = self.cold
        self.cold = False
        result['froid'] = cold
        asr_before = len(self.instruments.asr)
        checks_before = len(self.instruments.validations)
        loads_before = len(self.instruments.chargements)
        try:
            t0 = time.perf_counter()
            status, transcript = self.client.call('POST', '/api/voice/transcribe', audio, content_type='audio/wav',
                                                  headers={'X-Boj-Voice-Owner': owner})
            t1 = time.perf_counter()
            result['etapes_ms']['transcription_http'] = (t1 - t0) * 1000
            if len(self.instruments.asr) > asr_before:
                total = self.instruments.asr[-1]
                check = self.instruments.validations[-1] if len(self.instruments.validations) > checks_before else 0.0
                result['etapes_ms']['controle_audio'] = check
                result['etapes_ms']['transcription_moteur'] = max(0.0, total - check)
            if len(self.instruments.chargements) > loads_before:
                result['etapes_ms']['chargement_modele'] = self.instruments.chargements[-1]
            if status != 200:
                result.update(issue='refus_audio', http=status, message=(transcript or {}).get('error'))
                return result
            result['texte'] = transcript.get('text', '')
            result['qualite_audio'] = transcript.get('quality')
            if transcript.get('status') == 'no_speech':
                result['issue'] = 'aucune_parole'
                return result
            if before_turn:
                before_turn()
            request_id = request_id or 'turn_' + uuid.uuid4().hex
            if forced_text is not None:
                result['texte_impose'] = forced_text
            turn = {'request_id': request_id, 'client_id': owner, 'project_id': PROJECT,
                    'revision': snapshot['revision'], 'text': forced_text if forced_text is not None else result['texte'],
                    'operation_id': None,
                    'source': 'voice', 'context_sha256': snapshot['context_sha256']}
            result['tour'] = turn
            before = self.command_count()
            self.console_wake.clear()
            status, receipt = self.client.call('POST', '/api/jarvis/turn', turn)
            t2 = time.perf_counter()
            result['etapes_ms']['tour_http'] = (t2 - t1) * 1000
            nodes = self.instruments.take_nodes(request_id)
            for key, label in (('_route', 'intention'), ('_guard', 'garde'), ('_dispatch', 'distribution'),
                               ('_receipt', 'journal_du_tour')):
                if key in nodes:
                    result['etapes_ms'][label] = nodes[key]
            if 'submit' in nodes:
                inner = sum(nodes.get(k, 0.0) for k in ('_route', '_guard', '_dispatch', '_receipt'))
                result['etapes_ms']['orchestration'] = max(0.0, nodes['submit'] - inner)
            if status != 200:
                result.update(issue='tour_refuse', http=status, message=(receipt or {}).get('error'))
                return result
            result['statut'] = receipt['status']
            result['decision'] = receipt.get('decision')
            if receipt['status'] == 'QUEUED' and wait_receipt:
                receipt = self.wait_receipt(request_id, receipt)
                t3 = time.perf_counter()
                if (receipt.get('display') or {}).get('state') == 'rendered':
                    result['etapes_ms']['affichage'] = (t3 - t2) * 1000
                    result['etapes_ms']['affichage_serveur'] = receipt.get('elapsed_to_display_ms')
                    result['etapes_ms']['apres_fin_de_prise'] = (t3 - t0) * 1000
            result['recu'] = {k: receipt.get(k) for k in ('status', 'message', 'physical_effect', 'approval_source')}
            result['recu']['affichage'] = (receipt.get('display') or {}).get('state')
            result['recu']['vues'] = [d.get('target_role') for d in receipt.get('displays') or []]
            result['nouvelles_commandes'] = self.command_count() - before
            result['issue'] = 'tour'
            return result
        finally:
            self.client.call('POST', '/api/voice/lease', {'client_id': owner, 'release': True})

    def wait_receipt(self, request_id, receipt, timeout=RECEIPT_TIMEOUT):
        """Attend le reçu comme la console : relecture à chaque événement, repli 5 s."""
        deadline = time.perf_counter() + timeout
        while True:
            state = (receipt.get('display') or {}).get('state')
            if state in ('rendered', 'failed', 'stale', 'cancelled', 'cancelled_restore'):
                return receipt
            if receipt.get('status') != 'QUEUED' or time.perf_counter() >= deadline:
                return receipt
            self.console_wake.wait(min(5.0, max(0.0, deadline - time.perf_counter())))
            self.console_wake.clear()
            status, current = self.client.call('GET', '/api/jarvis/turn?request_id=' + request_id)
            if status == 200:
                receipt = current


# --- Classement des issues -----------------------------------------------------

def classify(expected, result, norm):
    issue = result.get('issue')
    dispatched = result.get('nouvelles_commandes', 0) > 0
    choice = (result.get('decision') or {}).get('choice')
    rendered = (result.get('recu') or {}).get('affichage') == 'rendered'
    if expected['type'] == 'refus_audio':
        return 'correct' if issue == 'refus_audio' else ('affichage_non_voulu' if dispatched else 'audio_accepte')
    if expected['type'] == 'aucun_affichage':
        return 'affichage_non_voulu' if dispatched else 'correct'
    if dispatched and choice != expected['choix']:
        return 'mauvaise_vue'
    if dispatched and rendered and set(result['recu']['vues']) == set(expected['vues']):
        return 'correct'
    if dispatched:
        return 'recu_absent'
    return 'commande_manquee'


CRITICAL = ('mauvaise_vue', 'affichage_non_voulu')


# --- Scénarios d'erreur ----------------------------------------------------------

def _wav(samples, rate=16000):
    import io
    buffer = io.BytesIO()
    with wave.open(buffer, 'wb') as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(rate)
        handle.writeframes(samples)
    return buffer.getvalue()


def _pcm(audio):
    import io
    with wave.open(io.BytesIO(audio), 'rb') as handle:
        return handle.readframes(handle.getnframes())


CANONICAL = 'Affiche le dashboard atelier'


def scenarios(bench, reference_audio):
    """Cas d'erreur : chaque scénario dit ce qu'il injecte, ce qu'il attend et ce qu'il observe.

    Après la vraie transcription, les cas qui éprouvent la suite de la chaîne imposent le texte
    exact de la commande : leur verdict ne dépend pas de la qualité du modèle.
    """
    results = []
    canonical = {'forced_text': CANONICAL}

    def record(name, family, injected, expected, passed, observed):
        results.append({'nom': name, 'famille': family, 'injection': injected, 'attendu': expected,
                        'reussi': bool(passed), 'observe': observed})

    client = bench.client
    owner = 'mic_' + uuid.uuid4().hex
    client.call('POST', '/api/voice/lease', {'client_id': owner, 'release': False})

    # Coupures côté audio.
    truncated = reference_audio[:-4000]
    before = bench.command_count()
    status, body = client.call('POST', '/api/voice/transcribe', truncated, content_type='audio/wav',
                               headers={'X-Boj-Voice-Owner': owner})
    record('wav_tronque', 'coupure', 'en-tête WAV intact, 4 000 derniers octets perdus',
           'refus 409 « Audio tronqué », aucun tour', status == 409 and bench.command_count() == before,
           {'http': status, 'message': (body or {}).get('error')})

    too_long = _wav(_pcm(reference_audio) + b'\x00\x00' * 16000 * 14)
    checked = len(bench.instruments.validations)
    status, body = client.call('POST', '/api/voice/transcribe', too_long, content_type='audio/wav',
                               headers={'X-Boj-Voice-Owner': owner})
    # Le serveur refuse sur l'en-tête Content-Length sans lire le corps ; selon l'OS, le client
    # reçoit le 413 ou voit la connexion fermée pendant l'envoi. Dans les deux cas : WAV jamais lu.
    unread = len(bench.instruments.validations) == checked
    record('prise_trop_longue', 'coupure', f'{len(too_long)} octets (> 15 s)', 'refus avant lecture du WAV',
           status in (409, 413, None) and unread and bench.command_count() == before,
           {'http': status, 'message': (body or {}).get('error'), 'wav_lu': not unread})

    wrong_rate = _wav(_pcm(reference_audio), rate=48000)
    status, body = client.call('POST', '/api/voice/transcribe', wrong_rate, content_type='audio/wav',
                               headers={'X-Boj-Voice-Owner': owner})
    record('format_non_conforme', 'coupure', 'WAV annoncé à 48 kHz', 'refus 409 du format',
           status == 409, {'http': status, 'message': (body or {}).get('error')})
    client.call('POST', '/api/voice/lease', {'client_id': owner, 'release': True})

    # Micro réservé par une autre fenêtre.
    other = 'mic_' + uuid.uuid4().hex
    client.call('POST', '/api/voice/lease', {'client_id': owner, 'release': False})
    status_lease, lease = client.call('POST', '/api/voice/lease', {'client_id': other, 'release': False})
    status, body = client.call('POST', '/api/voice/transcribe', reference_audio, content_type='audio/wav',
                               headers={'X-Boj-Voice-Owner': other})
    record('micro_reserve_ailleurs', 'coupure', 'une seconde fenêtre demande le micro',
           'réservation et transcription refusées', status_lease == 409 and status == 409,
           {'reservation_http': status_lease, 'transcription_http': status, 'message': (body or {}).get('error')})
    client.call('POST', '/api/voice/lease', {'client_id': owner, 'release': True})

    # Deux envois simultanés de la même prise (double clic) : une seule transcription à la fois.
    client.call('POST', '/api/voice/lease', {'client_id': owner, 'release': False})
    outcomes = []

    def send():
        outcomes.append(client.call('POST', '/api/voice/transcribe', reference_audio, content_type='audio/wav',
                                    headers={'X-Boj-Voice-Owner': owner})[0])
    threads = [threading.Thread(target=send) for _ in range(2)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    record('transcriptions_simultanees', 'reponse_tardive', 'deux envois simultanés de la même prise',
           'une transcription acceptée, l’autre refusée sans file d’attente',
           sorted(outcomes) == [200, 409], {'http': sorted(outcomes)})
    client.call('POST', '/api/voice/lease', {'client_id': owner, 'release': True})

    # Annulation pendant la transcription.
    holder = {}

    def cancel_lease():
        bench.app.jarvis.voice_lease.claim(holder['owner'], release=True)
    before = bench.command_count()
    owner2 = 'mic_' + uuid.uuid4().hex
    holder['owner'] = owner2
    bench.instruments.pendant_transcription = cancel_lease
    turn = bench.voice_turn(reference_audio, owner=owner2)
    record('prise_annulee_pendant_transcription', 'coupure', 'la fenêtre annule la prise pendant la transcription',
           'transcription écartée, aucun tour', turn.get('issue') == 'refus_audio' and bench.command_count() == before,
           {'issue': turn.get('issue'), 'http': turn.get('http'), 'message': turn.get('message')})

    # Contexte ou dossier modifiés pendant la transcription : la prise garde l'état figé au départ.
    for name, mutate, label in (('contexte_modifie_pendant_transcription', bench.touch_context,
                                 'le fichier de contexte change pendant la transcription'),
                                ('dossier_modifie_pendant_transcription', bench.bump_revision,
                                 'une autre fenêtre enregistre une révision du dossier')):
        before = bench.command_count()
        bench.instruments.pendant_transcription = mutate
        turn = bench.voice_turn(reference_audio, **canonical)
        record(name, 'reponse_tardive', label, 'tour STALE, aucune vue servie',
               turn.get('statut') == 'STALE' and bench.command_count() == before,
               {'statut': turn.get('statut'), 'texte': turn.get('texte'), 'nouvelles_commandes': bench.command_count() - before})

    # Écran en retard : pas de reçu prématuré, reçu exact à l'accusé.
    atelier = bench.screens['atelier']
    atelier.retard = 3.0
    turn = bench.voice_turn(reference_audio, **canonical)
    atelier.retard = 0.0
    shown = turn.get('etapes_ms', {}).get('affichage')
    server = turn.get('etapes_ms', {}).get('affichage_serveur')
    # Horloge du serveur (du tour à l'accusé) : la vue reçoit la commande pendant la requête du
    # tour, avant que la console ait sa réponse ; le délai côté console peut donc être un peu < 3 s.
    record('ecran_en_retard', 'reponse_tardive', 'la vue atelier accuse 3 s après réception',
           'reçu « affiché » seulement après l’accusé (≥ 3 000 ms depuis le tour, horloge du serveur)',
           turn.get('recu', {}).get('affichage') == 'rendered' and server is not None and server >= 3000,
           {'affichage_serveur_ms': server, 'affichage_console_ms': shown, 'recu': turn.get('recu')})

    # Accusé tardif après changement de contexte : refusé, jamais compté comme affiché.
    atelier.retard = 2.0
    atelier.during_delay = bench.touch_context
    turn = bench.voice_turn(reference_audio, **canonical)
    atelier.retard = 0.0
    record('accuse_tardif_apres_changement', 'reponse_tardive',
           'le contexte change entre la réception et l’accusé de la vue atelier',
           'accusé refusé, vue « stale », aucun reçu « affiché »',
           turn.get('recu', {}).get('affichage') == 'stale', {'recu': turn.get('recu'), 'acks': atelier.acks[-1:]})

    # Vue absente puis revenue : rien n'est déclaré affiché pendant l'absence.
    atelier.absent = True
    started = time.perf_counter()
    turn = bench.voice_turn(reference_audio, wait_receipt=False, **canonical)
    request_id = turn['tour']['request_id']
    pending = bench.wait_receipt(request_id, {'status': 'QUEUED', 'display': {'state': 'queued'}}, timeout=3.0)
    atelier.absent = False
    atelier.wake.set()
    final = bench.wait_receipt(request_id, pending)
    record('ecran_absent_puis_revenu', 'reponse_tardive', 'la vue atelier ne demande plus de commande pendant 3 s',
           'pas de reçu pendant l’absence, affichage au retour',
           (pending.get('display') or {}).get('state') != 'rendered'
           and (final.get('display') or {}).get('state') == 'rendered',
           {'pendant_absence': (pending.get('display') or {}).get('state'),
            'au_retour': (final.get('display') or {}).get('state'),
            'duree_s': round(time.perf_counter() - started, 3)})

    # Coupure pendant la distribution puis reprise de la même référence.
    request_id = 'turn_' + uuid.uuid4().hex
    original = bench.app.tower.dispatch
    calls = [0]

    def lost(rid):
        calls[0] += 1
        if calls[0] == 1:
            raise OSError('coupure simulée pendant la distribution')
        return original(rid)
    before = bench.command_count()
    with patch.object(bench.app.tower, 'dispatch', side_effect=lost):
        first = bench.voice_turn(reference_audio, request_id=request_id, wait_receipt=False, **canonical)
        status, again = bench.client.call('POST', '/api/jarvis/turn', first['tour'])
    again = bench.wait_receipt(request_id, again)
    record('coupure_pendant_distribution', 'coupure', 'la première distribution échoue (OSError)',
           'tour INTERRUPTED, reprise de la même référence : une seule commande, affichée',
           first.get('statut') == 'INTERRUPTED' and again.get('status') == 'QUEUED'
           and bench.command_count() - before == 1 and (again.get('display') or {}).get('state') == 'rendered',
           {'premier': first.get('statut'), 'reprise': again.get('status'), 'commandes': bench.command_count() - before})

    # Reprise trop tardive (plus de 120 s après la demande) : refus.
    request_id = 'turn_' + uuid.uuid4().hex
    calls[0] = 0
    before = bench.command_count()
    with patch.object(bench.app.tower, 'dispatch', side_effect=lost):
        first = bench.voice_turn(reference_audio, request_id=request_id, wait_receipt=False, **canonical)
    with bench.app.store.connect() as db:
        db.execute('UPDATE jarvis_turns SET created=created-121 WHERE request_id=?', (request_id,))
    status, late = bench.client.call('POST', '/api/jarvis/turn', first['tour'])
    record('reprise_apres_120_s', 'reponse_tardive', 'reprise d’un tour interrompu 121 s après la demande',
           'tour STALE, aucune commande', late.get('status') == 'STALE' and bench.command_count() == before,
           {'premier': first.get('statut'), 'reprise': late.get('status'), 'message': late.get('message')})

    # Double envoi réseau du même tour : idempotent.
    turn = bench.voice_turn(reference_audio, **canonical)
    before = bench.command_count()
    status, replay = bench.client.call('POST', '/api/jarvis/turn', turn['tour'])
    record('double_envoi', 'coupure', 'le même tour est renvoyé après une réponse perdue',
           'même référence, aucune commande supplémentaire',
           status == 200 and bench.command_count() == before and replay.get('request_id') == turn['tour']['request_id'],
           {'http': status, 'statut': replay.get('status')})

    # Redémarrage du serveur avant l'affichage : la commande durable est servie une seule fois.
    for screen in bench.screens.values():
        screen.absent = True
    request_id = 'turn_' + uuid.uuid4().hex
    before = bench.command_count()
    turn = bench.voice_turn(reference_audio, request_id=request_id, wait_receipt=False, **canonical)
    bench.restart()
    status, resumed = bench.client.call('POST', '/api/jarvis/turn', turn['tour'])
    resumed = bench.wait_receipt(request_id, resumed)
    record('redemarrage_avant_affichage', 'coupure',
           'serveur arrêté puis relancé sur le même dossier avant tout accusé ; vues réappairées',
           'commande conservée, affichée une fois, aucune duplication',
           turn.get('statut') == 'QUEUED' and bench.command_count() - before == 1
           and (resumed.get('display') or {}).get('state') == 'rendered',
           {'avant': turn.get('statut'), 'apres': resumed.get('status'),
            'affichage': (resumed.get('display') or {}).get('state'), 'commandes': bench.command_count() - before})
    return results


# --- Environnement et rapport ----------------------------------------------------

def _git(*args):
    try:
        return subprocess.run(['git', *args], cwd=ROOT, capture_output=True, text=True, timeout=30).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return None


def _cpu():
    name = platform.processor()
    try:
        if sys.platform.startswith('linux'):
            for line in Path('/proc/cpuinfo').read_text(encoding='utf-8').splitlines():
                if line.startswith('model name'):
                    return line.split(':', 1)[1].strip()
        if sys.platform == 'win32':
            import winreg
            key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r'HARDWARE\DESCRIPTION\System\CentralProcessor\0')
            return winreg.QueryValueEx(key, 'ProcessorNameString')[0].strip()
    except Exception:
        pass
    return name or None


def _memory_gb():
    try:
        if hasattr(os, 'sysconf') and 'SC_PHYS_PAGES' in os.sysconf_names:
            return round(os.sysconf('SC_PHYS_PAGES') * os.sysconf('SC_PAGE_SIZE') / 2 ** 30, 1)
        if sys.platform == 'win32':
            import ctypes

            class Status(ctypes.Structure):
                _fields_ = [('dwLength', ctypes.c_ulong), ('dwMemoryLoad', ctypes.c_ulong),
                            ('ullTotalPhys', ctypes.c_ulonglong), ('ullAvailPhys', ctypes.c_ulonglong),
                            ('ullTotalPageFile', ctypes.c_ulonglong), ('ullAvailPageFile', ctypes.c_ulonglong),
                            ('ullTotalVirtual', ctypes.c_ulonglong), ('ullAvailVirtual', ctypes.c_ulonglong),
                            ('ullAvailExtendedVirtual', ctypes.c_ulonglong)]
            status = Status()
            status.dwLength = ctypes.sizeof(Status)
            ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status))
            return round(status.ullTotalPhys / 2 ** 30, 1)
    except Exception:
        pass
    return None


def _version(package):
    try:
        return importlib.metadata.version(package)
    except importlib.metadata.PackageNotFoundError:
        return None


def environment():
    gpu = None
    try:
        out = subprocess.run(['nvidia-smi', '--query-gpu=name,driver_version,memory.total', '--format=csv,noheader'],
                             capture_output=True, text=True, timeout=10)
        gpu = out.stdout.strip() or None
    except (OSError, subprocess.SubprocessError):
        gpu = None
    return {'systeme': platform.platform(), 'python': platform.python_version(), 'processeur': _cpu(),
            'coeurs_logiques': os.cpu_count(), 'memoire_go': _memory_gb(), 'gpu_nvidia': gpu,
            'paquets': {name: _version(name) for name in ('faster-whisper', 'ctranslate2', 'av', 'onnxruntime',
                                                         'numpy', 'langgraph', 'langgraph-checkpoint-sqlite')}}


def _jsonable(value):
    return json.loads(json.dumps(value, default=str)) if value is not None else None


def model_identity(model_dir):
    model_dir = Path(model_dir)
    files = {}
    for name in MODEL_FILES:
        path = model_dir / name
        files[name] = voix_corpus.sha256_file(path) if path.is_file() else None
    known = None
    for name, spec in MODELES.items():
        if spec.get('model_bin_sha256') and spec['model_bin_sha256'] == files['model.bin']:
            known = name
    return {'dossier': model_dir.name, 'modele_connu': known, 'empreintes': files}


def summarize(samples, norm):
    by_outcome = defaultdict(int)
    for sample in samples:
        by_outcome[sample['classement']] += 1
    stage_names = ('debut_de_prise', 'fin_de_prise_apres_parole', 'encodage_wav', 'transcription_http',
                   'controle_audio', 'transcription_moteur', 'chargement_modele', 'tour_http', 'intention', 'garde', 'distribution',
                   'journal_du_tour', 'orchestration', 'affichage', 'affichage_serveur', 'apres_fin_de_prise',
                   'bout_en_bout')
    stages = {}
    for temperature in ('chaud', 'froid'):
        chosen = [s for s in samples if s.get('froid') == (temperature == 'froid')]
        stages[temperature] = {name: stats([s['etapes_ms'].get(name) for s in chosen]) for name in stage_names}
    errors = defaultdict(int)
    for sample in samples:
        if sample.get('issue') in ('refus_audio', 'tour_refuse', 'micro_refuse') and \
                sample['attendu']['type'] != 'refus_audio':
            errors[sample['issue']] += 1
    by_condition = {}
    for condition in sorted({s['condition'] for s in samples}):
        chosen = [s for s in samples if s['condition'] == condition and s['groupe'] in ('cible', 'catalogue')]
        if not chosen:
            continue
        by_condition[condition] = {
            'prises': len(chosen),
            'affichages_corrects': sum(s['classement'] == 'correct' for s in chosen),
            'transcriptions_exactes': sum(s.get('transcription_exacte') is True for s in chosen),
            'taux_erreur_mots_moyen': round(statistics.mean(s['taux_erreur_mots'] for s in chosen
                                                            if s.get('taux_erreur_mots') is not None), 4)
            if any(s.get('taux_erreur_mots') is not None for s in chosen) else None,
            'fin_de_prise_automatique': {k: sum((s.get('fin_de_prise') or {}).get('raison') == k for s in chosen)
                                         for k in ('pause', 'limit', 'no_speech')},
            'bout_en_bout': stats([s['etapes_ms'].get('bout_en_bout') for s in chosen if not s.get('froid')]),
            'transcription_moteur': stats([s['etapes_ms'].get('transcription_moteur') for s in chosen
                                           if not s.get('froid')]),
        }
    by_group = {}
    for group in sorted({s['groupe'] for s in samples}):
        chosen = [s for s in samples if s['groupe'] == group]
        counts = defaultdict(int)
        for sample in chosen:
            counts[sample['classement']] += 1
        by_group[group] = {'prises': len(chosen), 'correct': counts.get('correct', 0), 'issues': dict(sorted(counts.items()))}
    return {'issues': dict(sorted(by_outcome.items())), 'erreurs_critiques': sum(by_outcome[k] for k in CRITICAL),
            'erreurs_techniques': dict(errors), 'etapes': stages, 'par_condition': by_condition,
            'par_groupe': by_group}


def run(corpus_dir, model_dir, output, langgraph=True, variante='runtime', limit=None, repetitions_froid=3,
        with_scenarios=True, loader=None, label=None, progress=None):
    output = Path(output)
    if output.exists():
        raise SystemExit('Rapport existant : choisir un nouveau nom.')
    corpus = voix_corpus.load(corpus_dir)
    clips = corpus['clips'][:limit] if limit else corpus['clips']
    _, _, display_contracts, _, _ = _app_modules()
    norm = display_contracts.norm
    corpus_dir = Path(corpus_dir)
    reference = next(c for c in corpus['clips'] if c['phrase_id'] == 'A1' and c['condition'] == 'calme'
                     and c['groupe'] == 'cible')
    reference_audio = (corpus_dir / reference['envoi']['fichier']).read_bytes()
    samples, cold_runs, scenario_results = [], [], []
    started_at = datetime.now(timezone.utc)
    head = _git('rev-parse', 'HEAD')
    dirty = bool(_git('status', '--porcelain', '--untracked-files=no'))
    instruments = Instruments()
    _, _, _, _, voice_module = _app_modules()
    with tempfile.TemporaryDirectory(prefix='bojart-banc-voix-') as tmp, ExitStack() as stack:
        tmp = Path(tmp)
        stack.enter_context(patch.object(voice_module, 'validate_audio', instruments.validate(voice_module.validate_audio)))
        if loader is None:
            stack.enter_context(_timed_whisper(instruments, VARIANTES[variante]))
        # Démarrages à froid répétés : chargement du modèle et premier tour.
        for index in range(repetitions_froid):
            cold = Bench(tmp / f'froid-{index}' / 'etat', model_dir, langgraph, loader, instruments)
            cold.start()
            try:
                result = cold.voice_turn(reference_audio, forced_text=CANONICAL)
                result.update(clip=reference['id'], condition=reference['condition'], groupe='froid',
                              attendu=reference['attendu'])
                cold_runs.append(result)
            finally:
                cold.stop()
        bench = Bench(tmp / 'mesures' / 'etat', model_dir, langgraph, loader, instruments)
        bench.start()
        engine = bench.engine
        try:
            # Prise d'échauffement exclue des statistiques chaudes.
            bench.voice_turn(reference_audio, forced_text=CANONICAL)
            for position, clip in enumerate(clips, 1):
                audio = (corpus_dir / clip['envoi']['fichier']).read_bytes()
                result = bench.voice_turn(audio)
                result['froid'] = False
                end = clip['fin_de_prise']
                if end.get('delai_apres_parole_s') is not None:
                    result['etapes_ms']['fin_de_prise_apres_parole'] = end['delai_apres_parole_s'] * 1000
                result['etapes_ms']['encodage_wav'] = end.get('encodage_ms')
                if 'apres_fin_de_prise' in result['etapes_ms'] and end.get('delai_apres_parole_s') is not None:
                    result['etapes_ms']['bout_en_bout'] = (end['delai_apres_parole_s'] * 1000
                                                           + (end.get('encodage_ms') or 0)
                                                           + result['etapes_ms']['apres_fin_de_prise'])
                result.update(clip=clip['id'], phrase_id=clip['phrase_id'], phrase=clip['phrase'],
                              groupe=clip['groupe'], condition=clip['condition'], voix=clip['voix'],
                              attendu=clip['attendu'], fin_de_prise=end)
                if clip['phrase'] and 'texte' in result:
                    try:
                        spoken, heard = norm(clip['phrase']), norm(result['texte'])
                    except Exception:
                        spoken, heard = norm(clip['phrase']), ''
                    result['transcription_exacte'] = spoken == heard
                    result['taux_erreur_mots'] = round(word_error_rate(spoken, heard), 4)
                result['classement'] = classify(clip['attendu'], result, norm)
                result.pop('owner', None)
                samples.append(result)
                if progress:
                    progress(position, len(clips), result)
            if with_scenarios:
                scenario_results = scenarios(bench, reference_audio)
            engine = bench.engine
        finally:
            bench.stop()
    for result in cold_runs:
        result['froid'] = True
        result['classement'] = 'mesure_a_froid'
        result.pop('owner', None)
    asr_parameters = instruments.parametres_asr
    summary = summarize(samples + cold_runs, norm)
    report = {
        'schema': SCHEMA,
        'libelle': label,
        'debut': started_at.isoformat(timespec='seconds'),
        'fin': datetime.now(timezone.utc).isoformat(timespec='seconds'),
        'depot': {'sha': head, 'modifications_locales': dirty,
                  'sources_runtime_sha256': {name: voix_corpus.sha256_file(APP / name) for name in RUNTIME_SOURCES}},
        'environnement': environment(),
        'moteur_orchestration': engine,
        'asr': {'moteur': 'faster-whisper' if loader is None else 'double_de_test',
                'modele': model_identity(model_dir) if model_dir else None,
                'variante': variante, 'parametres_ajoutes': VARIANTES[variante],
                'parametres_transcription': _jsonable(asr_parameters),
                'parametres_chargement': _jsonable(instruments.parametres_chargement)},
        'corpus': {'schema': corpus['schema'], 'manifeste_sha256': corpus['manifeste_sha256'],
                   'cree_le': corpus['cree_le'], 'nature': corpus['nature'], 'clips': len(clips),
                   'code_navigateur': corpus['code_navigateur']},
        'protocole': {
            'serveur': 'ConsolidatedWorkbench réel, HTTP 127.0.0.1, base temporaire neuve',
            'ecrans': 'trois clients HTTP (atelier, pilotage, création) : événements, poll, accusé ; aucun rendu',
            'console': 'reçu relu à chaque événement /api/tower/events, repli 5 s, comme tower_voice.js',
            'froid': f'{repetitions_froid} démarrages neufs, première prise de chacun (chargement du modèle inclus) ; '
                     'texte du tour imposé pour mesurer aussi la première distribution ; cache disque du système chaud',
            'chaud': 'une prise d’échauffement exclue, puis chaque clip du corpus une fois, dans l’ordre du manifeste',
            'fin_de_prise': 'temps audio entre la fin de la parole et la décision de voice_endpoint.js (corpus)',
            'encodage_wav': 'mesuré par Node lors de la génération du corpus, sur l’hôte du corpus',
            'bout_en_bout': 'fin de prise après parole + encodage + transcription + tour + reçu d’affichage',
            'statistiques': 'médiane ; p95 au rang le plus proche ; maximum ; n',
        },
        'synthese': summary,
        'scenarios': scenario_results,
        'froid': cold_runs,
        'prises': samples,
        'limites': [
            'Voix de synthèse Piper et bruit synthétique : pas une voix humaine, pas le micro de la tour.',
            'Traitements audio du navigateur (réduction de bruit, gain automatique, annulation d’écho) non simulés.',
            'Écrans simulés par des clients HTTP : aucun rendu, aucun moniteur physique.',
            'Jev, LLM et GPU non utilisés ; la transcription suit voice.py (CPU, int8, 4 fils).',
            'Une mesure ne vaut que pour cet hôte, ce SHA, ce corpus et ce modèle.',
        ],
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    with open(output, 'x', encoding='utf-8') as handle:
        json.dump(report, handle, ensure_ascii=False, indent=1)
        handle.write('\n')
    return report


# --- Rapport lisible et comparaison --------------------------------------------------

STAGE_LABELS = (
    ('fin_de_prise_apres_parole', 'Fin de prise après la parole (porte d’énergie, temps audio)'),
    ('encodage_wav', 'Encodage WAV navigateur'),
    ('controle_audio', 'Contrôle du WAV (voice.validate_audio)'),
    ('transcription_moteur', 'Transcription (moteur faster-whisper)'),
    ('transcription_http', 'Transcription (requête HTTP complète)'),
    ('intention', 'Intention (routeur local)'),
    ('garde', 'Garde de contexte'),
    ('distribution', 'Distribution aux vues'),
    ('journal_du_tour', 'Journal du tour'),
    ('orchestration', 'Orchestration (hors nœuds)'),
    ('tour_http', 'Tour complet (requête HTTP)'),
    ('affichage', 'Affichage jusqu’au reçu (client)'),
    ('apres_fin_de_prise', 'De la fin de prise au reçu'),
    ('bout_en_bout', 'Bout en bout depuis la fin de la parole'),
    ('chargement_modele', 'Chargement du modèle (froid)'),
)


def _ms(value):
    if value is None:
        return '—'
    return f'{value:,.1f}'.replace(',', ' ').replace('.', ',')


def markdown(report):
    summary = report['synthese']
    env = report['environnement']
    asr = report['asr']
    lines = [f"# Banc vocal — {report.get('libelle') or asr.get('modele', {}).get('dossier')}", '',
             f"Mesuré du {report['debut']} au {report['fin']} sur `{report['depot']['sha']}`"
             + (' (modifications locales)' if report['depot']['modifications_locales'] else '') + '.', '',
             f"Hôte : {env['processeur']}, {env['coeurs_logiques']} cœurs logiques, {env['memoire_go']} Go, "
             f"{env['systeme']}, Python {env['python']}. GPU NVIDIA : {env['gpu_nvidia'] or 'aucun détecté'}.", '',
             f"Orchestration : `{report['moteur_orchestration']}`. ASR : {asr['moteur']} "
             f"`{(asr.get('modele') or {}).get('dossier')}`, variante `{asr['variante']}`. "
             f"Corpus `{report['corpus']['manifeste_sha256'][:16]}…` ({report['corpus']['clips']} prises).", '',
             '## Résultat', '',
             f"Erreurs critiques (mauvaise vue ou affichage non voulu) : **{summary['erreurs_critiques']}**.", '',
             '| Groupe | Prises | Correctes | Issues |', '|---|---:|---:|---|']
    for group, data in summary['par_groupe'].items():
        issues = ', '.join(f'{k} {v}' for k, v in data['issues'].items())
        lines.append(f"| {group} | {data['prises']} | {data['correct']} | {issues} |")
    lines += ['', '## Par condition sonore (phrases du catalogue)', '',
              '| Condition | Prises | Affichages corrects | Transcriptions exactes | Fin auto pause / limite / sans parole | Bout en bout médiane | p95 |',
              '|---|---:|---:|---:|---|---:|---:|']
    for condition, data in summary['par_condition'].items():
        end = data['fin_de_prise_automatique']
        lines.append(f"| {condition} | {data['prises']} | {data['affichages_corrects']} | "
                     f"{data['transcriptions_exactes']} | {end['pause']} / {end['limit']} / {end['no_speech']} | "
                     f"{_ms(data['bout_en_bout']['mediane_ms'])} | {_ms(data['bout_en_bout']['p95_ms'])} |")
    lines += ['', '## Latence par étape (ms)', '', '| Étape | n chaud | Médiane | p95 | Max | n froid | Médiane froid |',
              '|---|---:|---:|---:|---:|---:|---:|']
    for key, label in STAGE_LABELS:
        warm, cold = summary['etapes']['chaud'][key], summary['etapes']['froid'][key]
        if not warm['n'] and not cold['n']:
            continue
        lines.append(f"| {label} | {warm['n']} | {_ms(warm['mediane_ms'])} | {_ms(warm['p95_ms'])} | "
                     f"{_ms(warm['max_ms'])} | {cold['n']} | {_ms(cold['mediane_ms'])} |")
    if report['scenarios']:
        passed = sum(s['reussi'] for s in report['scenarios'])
        lines += ['', f"## Cas d’erreur : {passed}/{len(report['scenarios'])} conformes", '',
                  '| Cas | Famille | Injection | Attendu | Conforme |', '|---|---|---|---|---|']
        for scenario in report['scenarios']:
            lines.append(f"| {scenario['nom']} | {scenario['famille']} | {scenario['injection']} | "
                         f"{scenario['attendu']} | {'oui' if scenario['reussi'] else '**non**'} |")
    wrong = [s for s in report['prises'] if s['classement'] != 'correct']
    if wrong:
        lines += ['', '## Prises non conformes (extrait)', '', '| Prise | Entendu | Issue |', '|---|---|---|']
        for sample in wrong[:40]:
            heard = (sample.get('texte') or sample.get('message') or '').replace('|', '/')
            lines.append(f"| {sample['clip']} | {heard[:90]} | {sample['classement']} |")
        if len(wrong) > 40:
            lines.append(f'| … | {len(wrong) - 40} autres dans le JSON | |')
    lines += ['', '## Limites', ''] + [f'- {item}' for item in report['limites']]
    return '\n'.join(lines) + '\n'


# --- Sonde « bruit seul » : la reconnaissance invente-t-elle une commande ? ----------

SCHEMA_BRUIT = 'bojart.banc_voix.bruit.v1'
BRUIT_CONDITIONS = ('calme', 'ventilateur', 'imprimante', 'atelier_fort')
BRUIT_NIVEAUX_DB = (0.0, 10.0)  # niveau du corpus, puis bruit 10 dB plus fort


def _noise_clips(seeds, levels, conditions):
    clips, seed = [], 5000
    for condition in conditions:
        for level in (levels if condition != 'calme' else (0.0,)):
            for index in range(seeds):
                seed += 1
                clips.append({'id': f'bruit-{condition}-{level:+.0f}dB-{index + 1}', 'condition': condition,
                              'bruit_gain_db': level, 'graine': seed, 'gain_db': 0.0, 'coupure': None})
    return clips


def noise_probe(model_dir, output, seeds=8, levels=BRUIT_NIVEAUX_DB, conditions=BRUIT_CONDITIONS,
                variantes=('runtime', 'sans_vocabulaire'), node='node', loader=None, label=None, progress=None):
    """Flux micro sans parole → vrai code navigateur → LocalVoice → routeur exact du runtime.

    Une commande reconnue sur du bruit seul serait un affichage non voulu. Le rapport
    garde chaque texte entendu, la décision de fin de prise et la commande qu'il aurait
    déclenchée. Aucun serveur, aucun écran : seule la reconnaissance est en cause ici.
    """
    output = Path(output)
    np = voix_corpus._numpy()
    started_at = datetime.now(timezone.utc)
    core, _, display_contracts, jarvis_runtime, voice = _app_modules()
    clips = _noise_clips(seeds, levels, conditions)
    with tempfile.TemporaryDirectory(prefix='bojart-sonde-bruit-') as tmp:
        tmp = Path(tmp)
        harness_plan = []
        for clip in clips:
            stream, _, _ = voix_corpus.build_stream(np, None, clip)
            micro = tmp / (clip['id'] + '.f32')
            micro.write_bytes(stream.tobytes())
            harness_plan.append({'id': clip['id'], 'micro': str(micro), 'taux': voix_corpus.MICRO_RATE,
                                 'envoi': str(tmp / (clip['id'] + '.wav'))})
        plan_path = tmp / 'plan.json'
        plan_path.write_text(json.dumps({'clips': harness_plan}), encoding='utf-8')
        run_node = subprocess.run([node, str(voix_corpus.HARNESS), str(plan_path)], capture_output=True, text=True,
                                  check=True, encoding='utf-8')
        browser = json.loads(run_node.stdout)
        by_id = {r['id']: r for r in browser['resultats']}
        audio = {clip['id']: (tmp / (clip['id'] + '.wav')).read_bytes() for clip in clips}
    results, parameters = {}, {}
    total = len(clips) * len(variantes)
    position = 0
    for variante in variantes:
        instruments = Instruments()
        rows = []
        with ExitStack() as stack:
            if loader is None:
                stack.enter_context(_timed_whisper(instruments, VARIANTES[variante]))
            engine = voice.LocalVoice({'enabled': True, 'model_dir': str(model_dir or '')}, loader=loader)
            for clip in clips:
                started = time.perf_counter()
                try:
                    heard = engine.transcribe(audio[clip['id']])
                    status, text, message = heard['status'], heard.get('text') or '', None
                except core.Rejected as error:
                    status, text, message = 'refus', '', str(error)
                elapsed = (time.perf_counter() - started) * 1000
                command, ambiguous = None, False
                if text:
                    try:
                        normalized = display_contracts.norm(text)
                        command = jarvis_runtime.ALIASES.get(normalized)
                        ambiguous = normalized in jarvis_runtime.AMBIGUOUS_DASHBOARDS
                    except core.Rejected:
                        pass
                browser_result = by_id[clip['id']]
                rows.append({'clip': clip['id'], 'condition': clip['condition'], 'bruit_gain_db': clip['bruit_gain_db'],
                             'fin_de_prise': browser_result['raison'],
                             'duree_envoyee_s': round(browser_result['fin_de_prise_s'], 3),
                             'envoi_sha256': browser_result['envoi_sha256'], 'statut': status, 'texte': text,
                             'message': message, 'commande': command, 'ambigu': ambiguous,
                             'transcription_ms': round(elapsed, 1)})
                position += 1
                if progress:
                    progress(position, total, {'clip': clip['id'], 'classement': command or status})
        parameters[variante] = {'ajoutes': VARIANTES[variante], 'transcription': _jsonable(instruments.parametres_asr)}
        results[variante] = rows
    synthese = {}
    for variante, rows in results.items():
        texts = defaultdict(int)
        for row in rows:
            if row['texte']:
                texts[row['texte']] += 1
        synthese[variante] = {
            'prises': len(rows),
            'sans_parole': sum(r['statut'] == 'no_speech' for r in rows),
            'refus_audio': sum(r['statut'] == 'refus' for r in rows),
            'textes_non_vides': sum(bool(r['texte']) for r in rows),
            'commandes_declenchees': sum(r['commande'] is not None for r in rows),
            'tableau_ambigu': sum(r['ambigu'] for r in rows),
            'fin_de_prise': {reason: sum(r['fin_de_prise'] == reason for r in rows)
                             for reason in sorted({r['fin_de_prise'] for r in rows})},
            'transcription_ms': stats([r['transcription_ms'] for r in rows if r['statut'] != 'refus']),
            'textes_entendus': dict(sorted(texts.items(), key=lambda item: -item[1])),
        }
    head, dirty = _git('rev-parse', 'HEAD'), bool(_git('status', '--porcelain', '--untracked-files=no'))
    report = {
        'schema': SCHEMA_BRUIT, 'libelle': label,
        'debut': started_at.isoformat(timespec='seconds'),
        'fin': datetime.now(timezone.utc).isoformat(timespec='seconds'),
        'depot': {'sha': head, 'modifications_locales': dirty},
        'environnement': environment(),
        'asr': {'moteur': 'faster-whisper' if loader is None else 'double_de_test',
                'modele': model_identity(model_dir) if model_dir else None, 'variantes': parameters},
        'sonde': {'conditions': {c: voix_corpus.CONDITIONS[c] for c in conditions}, 'niveaux_db': list(levels),
                  'graines_par_cas': seeds, 'flux_s': voix_corpus.STREAM_SECONDS,
                  'reference': 'bruit au niveau du corpus (SNR par rapport à une parole à -24 dBFS), puis renforcé',
                  'code_navigateur': {'node': browser['node'], 'sources_sha256': browser['sources']}},
        'synthese': synthese,
        'resultats': results,
        'limites': ['Bruit synthétique, pas un enregistrement de l’atelier ; pas de voix de fond seule.',
                    'Seule la reconnaissance et le routeur exact sont rejoués ; le reste de la chaîne est mesuré '
                    'par la sous-commande mesurer.'],
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    with open(output, 'x', encoding='utf-8') as handle:
        json.dump(report, handle, ensure_ascii=False, indent=1)
        handle.write('\n')
    return report


def noise_markdown(report):
    model = (report['asr'].get('modele') or {}).get('dossier')
    lines = [f"# Sonde bruit seul — {report.get('libelle') or model}", '',
             f"Mesuré du {report['debut']} au {report['fin']} sur `{report['depot']['sha']}`"
             + (' (modifications locales)' if report['depot']['modifications_locales'] else '') + f", modèle `{model}`.",
             '', f"{report['synthese'][next(iter(report['synthese']))]['prises']} flux de "
             f"{report['sonde']['flux_s']:g} s sans parole ; niveaux de bruit {report['sonde']['niveaux_db']} dB "
             f"au-dessus du corpus ; {report['sonde']['graines_par_cas']} graines par cas.", '',
             '| Variante | Prises | Sans parole | Refus audio | Texte inventé | Commande déclenchée | Tableau ambigu |',
             '|---|---:|---:|---:|---:|---:|---:|']
    for variante, data in report['synthese'].items():
        lines.append(f"| {variante} | {data['prises']} | {data['sans_parole']} | {data['refus_audio']} | "
                     f"{data['textes_non_vides']} | **{data['commandes_declenchees']}** | {data['tableau_ambigu']} |")
    for variante, data in report['synthese'].items():
        if data['textes_entendus']:
            lines += ['', f'Textes entendus ({variante}) :', '']
            lines += [f"- « {text[:100]} » × {count}" for text, count in data['textes_entendus'].items()]
    lines += ['', '## Limites', ''] + [f'- {item}' for item in report['limites']]
    return '\n'.join(lines) + '\n'


def compare(reference, other):
    """Compare deux rapports étape par étape ; refuse de mélanger corpus ou modèles différents."""
    problems = []
    if reference['corpus']['manifeste_sha256'] != other['corpus']['manifeste_sha256']:
        problems.append('corpus différents')
    ref_model = (reference['asr'].get('modele') or {}).get('empreintes')
    other_model = (other['asr'].get('modele') or {}).get('empreintes')
    if ref_model != other_model:
        problems.append('poids du modèle différents')
    if reference['asr']['variante'] != other['asr']['variante']:
        problems.append('variantes de décodage différentes')
    elif reference['asr'].get('parametres_transcription') != other['asr'].get('parametres_transcription'):
        problems.append('paramètres de transcription différents (voice.py modifié entre les deux mesures)')
    rows = []
    for key, label in STAGE_LABELS:
        a, b = reference['synthese']['etapes']['chaud'][key], other['synthese']['etapes']['chaud'][key]
        if not a['n'] and not b['n']:
            continue
        ratio = (round(b['mediane_ms'] / a['mediane_ms'], 2) if a['mediane_ms'] and b['mediane_ms'] else None)
        rows.append({'etape': key, 'libelle': label, 'reference': a, 'autre': b, 'rapport_medianes': ratio})
    return {'comparable': not problems, 'ecarts_de_protocole': problems,
            'reference': {'libelle': reference.get('libelle'), 'hote': reference['environnement']['processeur'],
                          'sha': reference['depot']['sha']},
            'autre': {'libelle': other.get('libelle'), 'hote': other['environnement']['processeur'],
                      'sha': other['depot']['sha']},
            'erreurs_critiques': [reference['synthese']['erreurs_critiques'], other['synthese']['erreurs_critiques']],
            'etapes': rows}


def compare_markdown(result):
    lines = ['# Comparaison de deux mesures vocales', '',
             f"Référence : {result['reference']['libelle']} ({result['reference']['hote']}, `{result['reference']['sha']}`).",
             f"Autre : {result['autre']['libelle']} ({result['autre']['hote']}, `{result['autre']['sha']}`).", '']
    if result['ecarts_de_protocole']:
        lines += ['**Non comparables directement** : ' + ', '.join(result['ecarts_de_protocole']) + '.', '']
    lines += ['| Étape | Médiane réf. | p95 réf. | Médiane autre | p95 autre | Rapport |', '|---|---:|---:|---:|---:|---:|']
    for row in result['etapes']:
        lines.append(f"| {row['libelle']} | {_ms(row['reference']['mediane_ms'])} | {_ms(row['reference']['p95_ms'])} | "
                     f"{_ms(row['autre']['mediane_ms'])} | {_ms(row['autre']['p95_ms'])} | "
                     f"{row['rapport_medianes'] if row['rapport_medianes'] is not None else '—'} |")
    return '\n'.join(lines) + '\n'


def download_model(name, destination):
    """Téléchargement explicite d'un modèle épinglé, puis contrôle de ses empreintes."""
    if name not in MODELES:
        raise SystemExit('Modèle inconnu. Choix : ' + ', '.join(MODELES))
    destination = Path(destination)
    if destination.exists() and any(destination.iterdir()):
        raise SystemExit('Dossier non vide : choisir un dossier neuf.')
    from huggingface_hub import snapshot_download
    spec = MODELES[name]
    snapshot_download(spec['depot'], revision=spec['revision'], local_dir=str(destination),
                      allow_patterns=list(MODEL_FILES) + ['vocabulary.*', 'preprocessor_config.json'])
    identity = model_identity(destination)
    expected = spec.get('model_bin_sha256')
    if expected and identity['empreintes']['model.bin'] != expected:
        raise SystemExit('Empreinte de model.bin différente de la référence : fichier refusé.')
    return identity
