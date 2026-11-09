"""Banc vocal : contrats sans moteur réel ni synthèse vocale.

Le vrai serveur, le vrai runtime et les vraies routes HTTP sont utilisés ; seul le
modèle faster-whisper est remplacé par un double qui renvoie un texte connu pour
chaque WAV. Les sorties dangereuses plantées (négation perdue, mauvaise vue) doivent
être comptées comme erreurs critiques.
"""
import array
import hashlib
import io
import json
import math
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from unittest import mock
import wave
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from bojart_ops import banc_voix, voix_corpus  # noqa: E402


def tone_wav(seconds, freq, amplitude=0.2, rate=16000):
    samples = array.array('h', (int(amplitude * 32767 * math.sin(2 * math.pi * freq * i / rate))
                                for i in range(int(seconds * rate))))
    if sys.byteorder != 'little':
        samples.byteswap()
    buffer = io.BytesIO()
    with wave.open(buffer, 'wb') as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(rate)
        handle.writeframes(samples.tobytes())
    return buffer.getvalue()


# Chaque clip : (id, phrase dite, groupe, attendu, texte « entendu » par le double, fréquence du WAV).
CLIPS = [
    ('A1-test-calme', 'Affiche le dashboard atelier.', 'cible', voix_corpus.PHRASES['A1'][2],
     'Affiche le dashboard atelier.', 300),
    ('A2-test-calme', 'Jarvis, affiche le dashboard atelier.', 'cible', voix_corpus.PHRASES['A2'][2],
     'Jarvi, affiche le dashboard atelier.', 310),
    ('B1-test-calme', 'Affiche le dashboard dossiers.', 'catalogue', voix_corpus.PHRASES['B1'][2],
     'Affiche le dashboard Studio.', 320),
    ('D1-test-calme', 'Lance l’impression de la figurine.', 'interdit', voix_corpus.PHRASES['D1'][2],
     'Lance l’impression de la figurine.', 330),
    ('D2-test-calme', 'N’affiche pas le dashboard atelier.', 'interdit', voix_corpus.PHRASES['D2'][2],
     'Affiche le dashboard atelier.', 340),
    ('E-silence', '', 'limite', {'type': 'aucun_affichage', 'raison': 'pas_de_parole'}, None, None),
]


class FakeWhisper:
    def __init__(self, texts):
        self.texts = texts

    def transcribe(self, audio, **kwargs):
        raw = audio.getvalue()
        time.sleep(0.2)  # laisse se chevaucher deux envois simultanés

        class Segment:
            text = self.texts.get(hashlib.sha256(raw).hexdigest(), '')
        return iter([Segment()]), None


class VoiceBenchContracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        root = Path(cls.tmp.name)
        cls.corpus = root / 'corpus'
        (cls.corpus / 'envoi').mkdir(parents=True)
        cls.model = root / 'modele'
        cls.model.mkdir()
        for name in banc_voix.MODEL_FILES:
            (cls.model / name).write_text('double de test', encoding='utf-8')
        texts, clips = {}, []
        for index, (clip_id, phrase, group, expected, heard, freq) in enumerate(CLIPS):
            raw = tone_wav(2.0, freq) if freq else tone_wav(2.0, 100, amplitude=0.0)
            (cls.corpus / 'envoi' / (clip_id + '.wav')).write_bytes(raw)
            digest = hashlib.sha256(raw).hexdigest()
            if heard is not None:
                texts[digest] = heard
            clips.append({'id': clip_id, 'phrase_id': clip_id.split('-')[0] if phrase else None, 'phrase': phrase,
                          'groupe': group, 'attendu': expected, 'voix': 'test' if phrase else None,
                          'condition': 'calme', 'graine': index,
                          'fin_de_prise': {'raison': 'pause', 't_s': 2.0, 'delai_apres_parole_s': 1.1,
                                           'encodage_ms': 1.0},
                          'envoi': {'fichier': 'envoi/' + clip_id + '.wav', 'octets': len(raw), 'sha256': digest}})
        manifest = {'schema': voix_corpus.SCHEMA, 'cree_le': '2026-11-02T00:00:00+00:00',
                    'nature': 'tonalités de test', 'code_navigateur': {}, 'clips': clips}
        (cls.corpus / 'corpus.json').write_text(json.dumps(manifest, ensure_ascii=False), encoding='utf-8')
        cls.output = root / 'rapport.json'
        cls.report = banc_voix.run(cls.corpus, cls.model, cls.output, langgraph=False, repetitions_froid=1,
                                   loader=lambda: FakeWhisper(texts), label='contrat')

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def sample(self, clip_id):
        return next(s for s in self.report['prises'] if s['clip'] == clip_id)

    def test_target_command_reaches_the_atelier_view_with_a_receipt(self):
        sample = self.sample('A1-test-calme')
        self.assertEqual(sample['classement'], 'correct')
        self.assertEqual(sample['recu']['affichage'], 'rendered')
        self.assertEqual(sample['recu']['vues'], ['atelier'])
        self.assertFalse(sample['recu']['physical_effect'])
        for stage in ('transcription_http', 'intention', 'garde', 'distribution', 'affichage', 'bout_en_bout'):
            self.assertIn(stage, sample['etapes_ms'])
        self.assertAlmostEqual(sample['etapes_ms']['bout_en_bout'],
                               1100 + 1.0 + sample['etapes_ms']['apres_fin_de_prise'], places=3)

    def test_misheard_wake_word_is_a_missed_command_not_a_display(self):
        sample = self.sample('A2-test-calme')
        self.assertEqual(sample['classement'], 'commande_manquee')
        self.assertEqual(sample['nouvelles_commandes'], 0)

    def test_planted_dangerous_outcomes_are_critical(self):
        self.assertEqual(self.sample('B1-test-calme')['classement'], 'mauvaise_vue')
        self.assertEqual(self.sample('D2-test-calme')['classement'], 'affichage_non_voulu')
        self.assertEqual(self.report['synthese']['erreurs_critiques'], 2)

    def test_unknown_physical_command_is_refused(self):
        sample = self.sample('D1-test-calme')
        self.assertEqual(sample['classement'], 'correct')
        self.assertEqual(sample['statut'], 'CLARIFY')

    def test_silence_sends_no_turn(self):
        sample = self.sample('E-silence')
        self.assertEqual(sample['issue'], 'aucune_parole')
        self.assertEqual(sample['classement'], 'correct')

    def test_every_error_scenario_behaves(self):
        failed = [s for s in self.report['scenarios'] if not s['reussi']]
        self.assertEqual(failed, [])
        names = {s['nom'] for s in self.report['scenarios']}
        for name in ('wav_tronque', 'prise_annulee_pendant_transcription', 'contexte_modifie_pendant_transcription',
                     'ecran_en_retard', 'accuse_tardif_apres_changement', 'coupure_pendant_distribution',
                     'reprise_apres_120_s', 'redemarrage_avant_affichage'):
            self.assertIn(name, names)

    def test_cold_runs_include_first_display(self):
        cold = self.report['froid'][0]
        self.assertTrue(cold['froid'])
        self.assertEqual(cold['recu']['affichage'], 'rendered')

    def test_report_records_protocol_and_identity(self):
        report = self.report
        self.assertEqual(report['schema'], banc_voix.SCHEMA)
        self.assertEqual(report['moteur_orchestration'], 'missing_dependency')
        self.assertEqual(report['asr']['moteur'], 'double_de_test')
        self.assertEqual(len(report['corpus']['manifeste_sha256']), 64)
        self.assertIn('voice.py', report['depot']['sources_runtime_sha256'])
        warm = report['synthese']['etapes']['chaud']['transcription_http']
        self.assertGreater(warm['n'], 0)
        self.assertLessEqual(warm['mediane_ms'], warm['p95_ms'])
        self.assertIn('Erreurs critiques', banc_voix.markdown(report))
        with self.assertRaises(SystemExit):
            banc_voix.run(self.corpus, self.model, self.output, langgraph=False)

    def test_comparison_refuses_different_corpora(self):
        same = banc_voix.compare(self.report, self.report)
        self.assertTrue(same['comparable'])
        other = json.loads(json.dumps(self.report))
        other['corpus']['manifeste_sha256'] = '0' * 64
        self.assertIn('corpus différents', banc_voix.compare(self.report, other)['ecarts_de_protocole'])
        self.assertIn('Rapport', banc_voix.compare_markdown(same))

    def test_altered_corpus_is_refused(self):
        altered = Path(self.tmp.name) / 'altere'
        shutil.copytree(self.corpus, altered)
        path = altered / 'envoi' / 'A1-test-calme.wav'
        path.write_bytes(path.read_bytes()[:-2] + b'\x01\x00')
        with self.assertRaises(SystemExit):
            voix_corpus.load(altered)


class StatisticsContracts(unittest.TestCase):
    def test_stats(self):
        self.assertEqual(banc_voix.stats([]), {'n': 0, 'mediane_ms': None, 'p95_ms': None, 'max_ms': None})
        result = banc_voix.stats(list(range(1, 101)))
        self.assertEqual((result['n'], result['mediane_ms'], result['p95_ms'], result['max_ms']), (100, 50.5, 95, 100))

    def test_word_error_rate(self):
        self.assertEqual(banc_voix.word_error_rate('affiche le dashboard atelier', 'affiche le dashboard atelier'), 0)
        self.assertEqual(banc_voix.word_error_rate('affiche le dashboard atelier', 'affiche le dash podatelier'), 0.5)

    def test_plan_is_deterministic_and_balanced(self):
        first, second = voix_corpus.plan(), voix_corpus.plan()
        self.assertEqual(first, second)
        self.assertEqual(len({c['id'] for c in first}), len(first))
        target = [c for c in first if c['groupe'] == 'cible']
        self.assertEqual(len(target), 4 * len(voix_corpus.VOICES) * len(voix_corpus.FULL_CONDITIONS))
        self.assertNotIn('tom', voix_corpus.VOICES)


class ClientContracts(unittest.TestCase):
    def test_refusal_sent_before_the_body_is_read_is_not_a_crash(self):
        """Le serveur répond 413 sur l'en-tête puis ferme : le client ne doit pas lever BrokenPipe."""
        import socket
        listener = socket.socket()
        listener.bind(('127.0.0.1', 0))
        listener.listen(1)

        def serve():
            connection, _ = listener.accept()
            data = b''
            while b'\r\n\r\n' not in data:
                data += connection.recv(4096)
            body = b'{"error": "Requ\\u00eate hors limites."}'
            connection.sendall(b'HTTP/1.0 413 Payload Too Large\r\nContent-Type: application/json\r\n'
                               b'Content-Length: ' + str(len(body)).encode() + b'\r\n\r\n' + body)
            connection.close()
            listener.close()

        thread = threading.Thread(target=serve)
        thread.start()
        app = type('App', (), {'server_port': listener.getsockname()[1], 'token': 't', 'origin': 'http://127.0.0.1'})()
        status, body = banc_voix.Client(app).call('POST', '/api/voice/transcribe', b'\x00' * 8_000_000,
                                                 content_type='audio/wav')
        thread.join(10)
        self.assertIn(status, (413, None))
        self.assertIn('error', body)


class BenchLifecycle(unittest.TestCase):
    def test_stop_waits_for_the_requests_still_running(self):
        """Une requête encore en cours après stop() garde la base SQLite ouverte : WinError 32 sous Windows."""
        banc_voix._app_modules()
        import control_tower
        original = control_tower.ControlTower.poll
        started, finished = threading.Event(), threading.Event()

        def slow_poll(tower, screen_id):
            started.set()
            time.sleep(0.8)
            try:
                return original(tower, screen_id)
            finally:
                finished.set()

        with tempfile.TemporaryDirectory() as tmp, mock.patch.object(control_tower.ControlTower, 'poll', slow_poll):
            model = Path(tmp) / 'modele'
            model.mkdir()
            for name in banc_voix.MODEL_FILES:
                (model / name).write_text('double de test', encoding='utf-8')
            bench = banc_voix.Bench(Path(tmp) / 'etat', model, langgraph=False, loader=lambda: FakeWhisper({}))
            bench.start()
            self.assertTrue(started.wait(10), 'aucune vue n’a demandé de commande')
            bench.stop()
            self.assertTrue(finished.is_set(), 'stop() est revenu pendant une requête')
            self.assertEqual([t for t in bench.requests if t.is_alive()], [])


@unittest.skipUnless(shutil.which('node'), 'Node absent : code navigateur non exécutable')
class BrowserCodeContracts(unittest.TestCase):
    """Le harnais exécute voice_endpoint.js et l'encodeur de capture.js tels quels."""

    def run_harness(self, samples, rate=48000):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            micro = tmp / 'flux.f32'
            micro.write_bytes(array.array('f', samples).tobytes())
            plan = tmp / 'plan.json'
            plan.write_text(json.dumps({'clips': [{'id': 'x', 'micro': str(micro), 'taux': rate,
                                                   'envoi': str(tmp / 'envoi.wav')}]}), encoding='utf-8')
            out = subprocess.run(['node', str(voix_corpus.HARNESS), str(plan)], capture_output=True, text=True,
                                 check=True, encoding='utf-8')
            result = json.loads(out.stdout)['resultats'][0]
            result['wav'] = (tmp / 'envoi.wav').read_bytes()
            return result

    def test_pause_after_speech(self):
        rate = 48000
        samples = [0.0] * int(0.6 * rate)
        samples += [0.1 * math.sin(2 * math.pi * 220 * i / rate) for i in range(rate)]
        samples += [0.0] * int(13.4 * rate)
        result = self.run_harness(samples)
        self.assertEqual(result['raison'], 'pause')
        self.assertAlmostEqual(result['fin_de_prise_s'], 1.6 + 1.1, delta=0.01)
        sys.path.insert(0, str(banc_voix.APP))
        import voice
        quality = voice.validate_audio(result['wav'])
        self.assertEqual(quality['rate'], 16000)
        self.assertAlmostEqual(quality['seconds'], result['fin_de_prise_s'], delta=0.01)

    def test_continuous_noise_runs_to_the_fifteen_second_limit(self):
        rate = 48000
        samples = [0.03 * math.sin(2 * math.pi * 700 * i / rate) for i in range(15 * rate)]
        result = self.run_harness(samples)
        self.assertEqual(result['raison'], 'limit')
        self.assertAlmostEqual(result['fin_de_prise_s'], 15.0, delta=0.01)

    def test_silence_ends_without_speech_after_six_seconds(self):
        result = self.run_harness([0.0] * (15 * 48000))
        self.assertEqual(result['raison'], 'no_speech')
        self.assertAlmostEqual(result['fin_de_prise_s'], 6.0, delta=0.01)

    def test_noise_probe_counts_a_command_invented_from_noise(self):
        try:
            import numpy  # noqa: F401
        except ImportError:
            self.skipTest('numpy absent')
        heard = []

        class Hallucinating:
            def transcribe(self, audio, **kwargs):
                heard.append(len(audio.getvalue()))

                class Segment:
                    text = 'Jarvis, affiche le dashboard atelier.'
                return iter([Segment()]), None

        with tempfile.TemporaryDirectory() as tmp:
            model = Path(tmp) / 'modele'
            model.mkdir()
            for name in banc_voix.MODEL_FILES:
                (model / name).write_bytes(b'double')
            output = Path(tmp) / 'bruit.json'
            report = banc_voix.noise_probe(model, output, seeds=1, levels=(0.0,),
                                           conditions=('calme', 'imprimante'), variantes=('runtime',),
                                           loader=Hallucinating)
            self.assertTrue(output.is_file())
            self.assertIn('Commande déclenchée', banc_voix.noise_markdown(report))
        rows = {row['condition']: row for row in report['resultats']['runtime']}
        self.assertEqual(rows['calme']['statut'], 'no_speech')  # le silence n'atteint jamais le modèle
        self.assertEqual(rows['imprimante']['fin_de_prise'], 'limit')
        self.assertEqual(rows['imprimante']['commande'], 'planning')
        self.assertEqual(report['synthese']['runtime']['commandes_declenchees'], 1)
        self.assertEqual(len(heard), 1)


if __name__ == '__main__':
    unittest.main()
