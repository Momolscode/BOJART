"""Corpus vocal reproductible pour le banc de la chaîne vocale Jarvis.

Le corpus est généré une fois, puis rejoué à l'identique ailleurs (la tour) :

1. synthèse vocale Piper avec des voix françaises sous licence libre ;
2. flux « micro » simulé à 48 kHz : ambiance, parole calibrée, bruit d'atelier
   synthétique à un rapport signal/bruit connu, graine fixe ;
3. passage par le vrai code navigateur (``voice_endpoint.js`` puis l'encodeur
   WAV de ``capture.js``) exécuté par Node : on obtient exactement le WAV que la
   console enverrait au serveur, et l'instant où la prise se termine.

Seuls les WAV envoyés (16 kHz) et le manifeste ``corpus.json`` sont conservés.
Les fichiers audio restent hors de Git (politique du dépôt public) ; le
manifeste garde leurs empreintes SHA-256. La synthèse vocale n'est pas une voix
humaine prise par un vrai micro : c'est un plafond optimiste pour la
reconnaissance, pas une qualification.
"""
from __future__ import annotations

import hashlib
import json
import os
import platform
import shutil
import subprocess
import tempfile
import wave
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / 'jarvis/apps/jarvis/app'
HARNESS = ROOT / 'tools/banc_voix_navigateur.cjs'
SCHEMA = 'bojart.banc_voix.corpus.v1'
MICRO_RATE = 48000  # taux typique d'un AudioContext sous Windows
STREAM_SECONDS = 15.0  # le micro continue à capter jusqu'à la limite de capture.js
LEAD_SECONDS = 0.6
SPEECH_DBFS = -24.0  # niveau RMS de parole active visé au micro

# Voix Piper retenues : licences de données compatibles avec un usage d'essai.
# Exclues : « tom » (AGPLv3) ; « mls » (locuteurs 1840 et 7423), inintelligible même pour
# large-v3-turbo sur une prise propre (vérifié le 2 novembre 2026).
VOICES = {
    'siwis': {'fichier': 'fr_FR-siwis-medium.onnx', 'locuteur': 0, 'description': 'siwis, voix féminine',
              'licence': 'CC-BY 4.0 (SIWIS, Université d’Édimbourg)'},
    'upmc-jessica': {'fichier': 'fr_FR-upmc-medium.onnx', 'locuteur': 0, 'description': 'upmc jessica, voix féminine',
                     'licence': 'CC-BY-SA 4.0 (UPMC)'},
    'upmc-pierre': {'fichier': 'fr_FR-upmc-medium.onnx', 'locuteur': 1, 'description': 'upmc pierre, voix masculine',
                    'licence': 'CC-BY-SA 4.0 (UPMC)'},
    'gilles': {'fichier': 'fr_FR-gilles-low.onnx', 'locuteur': 0, 'description': 'gilles, voix masculine, 16 kHz',
               'licence': 'CC0'},
}

# Attendu du runtime pour chaque phrase dite. « aucun_affichage » : aucune vue ne
# doit recevoir de commande, quelle que soit la transcription.
PHRASES = {
    'A1': ('Affiche le dashboard atelier.', 'cible', {'type': 'affichage', 'choix': 'planning', 'vues': ['atelier']}),
    'A2': ('Jarvis, affiche le dashboard atelier.', 'cible', {'type': 'affichage', 'choix': 'planning', 'vues': ['atelier']}),
    'A3': ('Affiche le tableau de bord atelier.', 'cible', {'type': 'affichage', 'choix': 'planning', 'vues': ['atelier']}),
    'A4': ('Montre le dashboard atelier.', 'cible', {'type': 'affichage', 'choix': 'planning', 'vues': ['atelier']}),
    'B1': ('Affiche le dashboard dossiers.', 'catalogue', {'type': 'affichage', 'choix': 'workspace', 'vues': ['pilotage']}),
    'B2': ('Affiche le dashboard Studio.', 'catalogue', {'type': 'affichage', 'choix': 'studio', 'vues': ['creation']}),
    'B3': ('Affiche les trois dashboards.', 'catalogue',
           {'type': 'affichage', 'choix': 'tower', 'vues': ['atelier', 'pilotage', 'creation']}),
    'C1': ('Affiche le dashboard de l’atelier.', 'hors_catalogue', {'type': 'aucun_affichage', 'raison': 'formulation_hors_catalogue'}),
    'C2': ('Tu peux m’afficher le dashboard atelier ?', 'hors_catalogue', {'type': 'aucun_affichage', 'raison': 'formulation_hors_catalogue'}),
    'D1': ('Lance l’impression de la figurine.', 'interdit', {'type': 'aucun_affichage', 'raison': 'commande_inconnue_physique'}),
    'D2': ('N’affiche pas le dashboard atelier.', 'interdit', {'type': 'aucun_affichage', 'raison': 'negation'}),
    'D3': ('Affiche le dashboard.', 'interdit', {'type': 'aucun_affichage', 'raison': 'tableau_non_precise'}),
}
BACKGROUND_SENTENCE = 'Le colis de résine arrive demain matin, pense à vérifier la livraison avant midi.'

# Bruit synthétique : pas un enregistrement d'atelier. SNR par rapport à la parole active.
CONDITIONS = {
    'calme': {'snr_db': None, 'description': 'ambiance de pièce à -66 dBFS'},
    'ventilateur': {'snr_db': 20.0, 'description': 'souffle rose + ronflement 50 Hz (ventilation, PC)'},
    'imprimante': {'snr_db': 10.0, 'description': 'moteurs pas à pas variables + ventilateur'},
    'atelier_fort': {'snr_db': 5.0, 'description': 'imprimante et ventilateur proches du micro'},
    'parole_fond': {'snr_db': 10.0, 'description': 'une autre voix parle en fond'},
}
FULL_CONDITIONS = ('calme', 'ventilateur', 'imprimante', 'atelier_fort', 'parole_fond')
LIGHT_CONDITIONS = ('calme', 'imprimante')


def _numpy():
    try:
        import numpy
    except ImportError as exc:  # pragma: no cover - dépend de l'environnement voix
        raise SystemExit('numpy est requis pour générer le corpus (installé avec faster-whisper).') from exc
    return numpy


def sha256_file(path):
    digest = hashlib.sha256()
    with open(path, 'rb') as handle:
        for block in iter(lambda: handle.read(1 << 20), b''):
            digest.update(block)
    return digest.hexdigest()


def plan(voices=None, full_conditions=FULL_CONDITIONS, light_conditions=LIGHT_CONDITIONS):
    """Liste ordonnée et déterministe des clips à produire (sans audio)."""
    voices = list(voices or VOICES)
    clips = []
    seed = 1000
    for phrase_id, (text, group, expected) in PHRASES.items():
        conditions = full_conditions if group == 'cible' else light_conditions
        for voice in voices:
            for condition in conditions:
                seed += 1
                clips.append({'id': f'{phrase_id}-{voice}-{condition}', 'phrase_id': phrase_id, 'phrase': text,
                              'groupe': group, 'attendu': expected, 'voix': voice, 'condition': condition,
                              'graine': seed, 'gain_db': 0.0, 'coupure': None})
    first = voices[0]
    target = PHRASES['A1']
    # Cas limites dérivés de la phrase cible.
    edge = [
        ('E-voix-faible', 'calme', -16.0, None, target[2], 'parole 16 dB plus faible que le niveau de référence'),
        ('E-saturation', 'calme', 30.0, None, {'type': 'refus_audio', 'raison': 'saturation'}, 'gain excessif'),
        ('E-parole-coupee', 'calme', 0.0, 0.55, {'type': 'aucun_affichage', 'raison': 'parole_coupee'},
         'prise interrompue à 55 % de la phrase'),
    ]
    for name, condition, gain, cut, expected, description in edge:
        seed += 1
        clips.append({'id': f'{name}-{first}', 'phrase_id': 'A1', 'phrase': target[0], 'groupe': 'limite',
                      'attendu': expected, 'voix': first, 'condition': condition, 'graine': seed,
                      'gain_db': gain, 'coupure': cut, 'description': description})
    for name, condition in (('E-silence', 'calme'), ('E-bruit-seul', 'imprimante'), ('E-bruit-fort-seul', 'atelier_fort')):
        seed += 1
        clips.append({'id': name, 'phrase_id': None, 'phrase': '', 'groupe': 'limite',
                      'attendu': {'type': 'aucun_affichage', 'raison': 'pas_de_parole'}, 'voix': None,
                      'condition': condition, 'graine': seed, 'gain_db': 0.0, 'coupure': None,
                      'description': 'aucune parole, seulement l’ambiance'})
    return clips


# --- Signal -----------------------------------------------------------------

def _rms(np, x):
    return float(np.sqrt(np.mean(np.square(x)))) if len(x) else 0.0


def _active_rms(np, x, rate):
    """RMS des trames de 20 ms au-dessus de -50 dBFS (parole active)."""
    frame = int(rate * 0.02)
    frames = [x[i:i + frame] for i in range(0, len(x) - frame + 1, frame)]
    energies = [(_rms(np, f)) for f in frames]
    active = [e for e in energies if e > 10 ** (-50 / 20)]
    return float(np.sqrt(np.mean(np.square(active)))) if active else _rms(np, x)


def _pink(np, n, rng):
    spectrum = np.fft.rfft(rng.standard_normal(n))
    freqs = np.fft.rfftfreq(n, 1 / MICRO_RATE)
    freqs[0] = freqs[1]
    signal = np.fft.irfft(spectrum / np.sqrt(freqs), n)
    return signal / (_rms(np, signal) or 1.0)


def _hum(np, n):
    t = np.arange(n) / MICRO_RATE
    tone = sum(a * np.sin(2 * np.pi * f * t) for f, a in ((50, 1.0), (100, 0.5), (150, 0.25)))
    return tone / _rms(np, tone)


def _steppers(np, n, rng):
    """Moteurs pas à pas : tonalités qui changent par segments, harmoniques et clics."""
    out = np.zeros(n)
    position = 0
    phase = 0.0
    while position < n:
        length = int(rng.uniform(0.25, 1.2) * MICRO_RATE)
        end = min(n, position + length)
        moving = rng.random() > 0.2
        freq = rng.uniform(250, 1400)
        t = np.arange(end - position) / MICRO_RATE
        if moving:
            ramp = np.minimum(1.0, np.minimum(t, t[::-1]) / 0.03)
            segment = sum(a * np.sin(2 * np.pi * freq * k * t + phase) for k, a in ((1, 1.0), (2, 0.35), (3, 0.2)))
            out[position:end] = segment * ramp
            phase += 2 * np.pi * freq * t[-1] if len(t) else 0
        position = end
    clicks = rng.random(n) < 4 / MICRO_RATE
    out += np.convolve(clicks.astype(float), np.exp(-np.arange(240) / 40.0), mode='same') * 3.0
    return out / (_rms(np, out) or 1.0)


def noise(np, condition, n, rng, background=None):
    if condition == 'calme':
        return rng.standard_normal(n) * 10 ** (-66 / 20)
    if condition == 'ventilateur':
        return 0.9 * _pink(np, n, rng) + 0.3 * _hum(np, n)
    if condition in ('imprimante', 'atelier_fort'):
        fan = 0.9 * _pink(np, n, rng) + 0.3 * _hum(np, n)
        return (_steppers(np, n, rng) + 0.7 * fan) / 1.22
    if condition == 'parole_fond':
        if background is None:
            raise ValueError('Voix de fond requise.')
        reps = int(np.ceil(n / len(background)))
        signal = np.tile(background, reps)[:n]
        return signal / (_rms(np, signal) or 1.0) + rng.standard_normal(n) * 10 ** (-66 / 20)
    raise ValueError('Condition inconnue : ' + condition)


def _read_wav_float(np, path):
    with wave.open(str(path), 'rb') as handle:
        if handle.getnchannels() != 1 or handle.getsampwidth() != 2:
            raise ValueError('WAV mono 16 bits attendu : ' + str(path))
        data = handle.readframes(handle.getnframes())
        rate = handle.getframerate()
    return np.frombuffer(data, dtype='<i2').astype(np.float64) / 32768.0, rate


def _resample(np, x, rate_in, rate_out):
    """Rééchantillonnage à bande limitée par FFT (sans dépendance externe)."""
    if rate_in == rate_out:
        return x
    padded = np.concatenate([x, np.zeros(int(0.05 * rate_in))])
    n_out = int(round(len(padded) * rate_out / rate_in))
    y = np.fft.irfft(np.fft.rfft(padded), n_out) * (n_out / len(padded))
    return y[:int(round(len(x) * rate_out / rate_in))]


def _trim(np, x, rate):
    """Retire le silence de tête et de queue produit par la synthèse."""
    frame = int(rate * 0.01)
    level = 10 ** (-45 / 20)
    energies = [_rms(np, x[i:i + frame]) for i in range(0, len(x), frame)]
    voiced = [i for i, e in enumerate(energies) if e > level]
    if not voiced:
        return x
    return x[voiced[0] * frame:min(len(x), (voiced[-1] + 1) * frame)]


def synthesize(piper, voices_dir, voice, texts, destination):
    """Une seule exécution de Piper par voix (processus séparé) ; un WAV par ligne, dans l'ordre."""
    spec = VOICES[voice]
    model = Path(voices_dir) / spec['fichier']
    destination = Path(destination)
    destination.mkdir(parents=True)
    subprocess.run([str(piper), '-m', str(model), '-s', str(spec['locuteur']), '-d', str(destination)],
                   input='\n'.join(texts).encode('utf-8'), check=True, stdout=subprocess.DEVNULL,
                   stderr=subprocess.DEVNULL, env={**os.environ, 'PYTHONUTF8': '1', 'PYTHONIOENCODING': 'utf-8'})
    files = sorted(destination.glob('*.wav'), key=lambda path: int(path.stem))
    if len(files) != len(texts):
        raise SystemExit(f'Piper a produit {len(files)} fichiers pour {len(texts)} phrases ({voice}).')
    return dict(zip(texts, files))


def build_stream(np, speech, clip, background=None):
    """Flux micro de 15 s : ambiance, parole calibrée à 0,6 s, bruit au SNR visé."""
    rng = np.random.default_rng(clip['graine'])
    n = int(STREAM_SECONDS * MICRO_RATE)
    condition = CONDITIONS[clip['condition']]
    reference = 10 ** (SPEECH_DBFS / 20)
    voiced = np.zeros(n)
    start = int(LEAD_SECONDS * MICRO_RATE)
    speech_end = start
    if speech is not None:
        level = _active_rms(np, speech, MICRO_RATE)
        calibrated = speech * (reference / level) * 10 ** (clip['gain_db'] / 20)
        if clip['coupure']:
            calibrated = calibrated[:int(len(calibrated) * clip['coupure'])]
        speech_end = min(n, start + len(calibrated))
        voiced[start:speech_end] = calibrated[:speech_end - start]
    ambient = noise(np, clip['condition'], n, rng, background)
    if condition['snr_db'] is not None:
        ambient = ambient * (reference / 10 ** (condition['snr_db'] / 20)) / (_rms(np, ambient) or 1.0)
    ambient = ambient * 10 ** (clip.get('bruit_gain_db', 0.0) / 20)  # sonde bruit seul : bruit renforcé
    stream = np.clip(voiced + ambient, -1.0, 1.0)
    return stream.astype('<f4'), (LEAD_SECONDS if speech is not None else None), \
        (speech_end / MICRO_RATE if speech is not None else None)


def _package_version(name):
    try:
        from importlib.metadata import version
        return version(name)
    except Exception:
        return None


def generate(output, piper, voices_dir, voices=None, node='node', full_conditions=FULL_CONDITIONS,
             light_conditions=LIGHT_CONDITIONS):
    np = _numpy()
    output = Path(output)
    if output.exists() and any(output.iterdir()):
        raise SystemExit('Dossier de corpus non vide : choisir un dossier neuf.')
    if shutil.which(node) is None:
        raise SystemExit('Node est requis pour exécuter le code navigateur réel.')
    (output / 'envoi').mkdir(parents=True)
    clips = plan(voices, full_conditions, light_conditions)
    voices_used = sorted({c['voix'] for c in clips if c['voix']} | {'gilles'})
    with tempfile.TemporaryDirectory(prefix='bojart-corpus-voix-') as tmp:
        tmp = Path(tmp)
        cache = {}
        wanted = defaultdict(list)
        for clip in clips:
            if clip['voix'] and clip['phrase'] not in wanted[clip['voix']]:
                wanted[clip['voix']].append(clip['phrase'])
        wanted['gilles'].append(BACKGROUND_SENTENCE)
        for voice, texts in wanted.items():
            for text, path in synthesize(piper, voices_dir, voice, texts, tmp / ('tts-' + voice)).items():
                samples, rate = _read_wav_float(np, path)
                cache[(voice, text)] = (_trim(np, _resample(np, samples, rate, MICRO_RATE), MICRO_RATE),
                                        sha256_file(path), rate)

        def speech_for(voice, text):
            return cache[(voice, text)][:2]

        background, background_sha = speech_for('gilles', BACKGROUND_SENTENCE)
        harness_plan = []
        for clip in clips:
            speech, speech_sha = (speech_for(clip['voix'], clip['phrase']) if clip['voix'] else (None, None))
            stream, start, end = build_stream(np, speech, clip, background)
            micro = tmp / (clip['id'] + '.f32')
            micro.write_bytes(stream.tobytes())
            clip['parole_debut_s'] = start
            clip['parole_fin_s'] = None if end is None else round(end, 4)
            clip['synthese_sha256'] = speech_sha
            harness_plan.append({'id': clip['id'], 'micro': str(micro), 'taux': MICRO_RATE,
                                 'envoi': str(output / 'envoi' / (clip['id'] + '.wav'))})
        plan_path = tmp / 'plan.json'
        plan_path.write_text(json.dumps({'clips': harness_plan}), encoding='utf-8')
        run = subprocess.run([node, str(HARNESS), str(plan_path)], capture_output=True, text=True, check=True,
                             encoding='utf-8')
        browser = json.loads(run.stdout)
    by_id = {r['id']: r for r in browser['resultats']}
    for clip in clips:
        result = by_id[clip['id']]
        end = clip['parole_fin_s']
        clip['fin_de_prise'] = {
            'raison': result['raison'], 't_s': round(result['fin_de_prise_s'], 4),
            'delai_apres_parole_s': None if end is None else round(result['fin_de_prise_s'] - end, 4),
            'encodage_ms': result['encodage_ms']}
        clip['envoi'] = {'fichier': 'envoi/' + clip['id'] + '.wav', 'octets': result['envoi_octets'],
                         'sha256': result['envoi_sha256']}
    voices_meta = {}
    for voice in voices_used:
        spec = VOICES[voice]
        voices_meta[voice] = {**spec, 'onnx_sha256': sha256_file(Path(voices_dir) / spec['fichier'])}
    manifest = {
        'schema': SCHEMA,
        'cree_le': datetime.now(timezone.utc).isoformat(timespec='seconds'),
        'nature': 'synthèse vocale Piper + bruit synthétique ; pas une voix humaine ni un micro réel',
        'flux_micro': {'taux_hz': MICRO_RATE, 'duree_s': STREAM_SECONDS, 'parole_dbfs': SPEECH_DBFS,
                       'debut_parole_s': LEAD_SECONDS,
                       'non_simule': ['getUserMedia', 'AudioWorklet', 'annulation d’écho', 'réduction de bruit',
                                      'gain automatique du navigateur']},
        'code_navigateur': {'node': browser['node'], 'sources_sha256': browser['sources']},
        'outils': {'piper_tts': _package_version('piper-tts'), 'onnxruntime': _package_version('onnxruntime'),
                   'numpy': np.__version__, 'python': platform.python_version(),
                   'reechantillonnage': 'FFT à bande limitée (numpy) vers 48 kHz'},
        'voix': voices_meta,
        'voix_de_fond': {'voix': 'gilles', 'phrase': BACKGROUND_SENTENCE, 'synthese_sha256': background_sha},
        'conditions': CONDITIONS,
        'clips': clips,
    }
    body = json.dumps(manifest, ensure_ascii=False, indent=1)
    (output / 'corpus.json').write_text(body + '\n', encoding='utf-8')
    return manifest


def load(corpus_dir, verify=True):
    """Charge un corpus et vérifie l'empreinte de chaque WAV envoyé."""
    corpus_dir = Path(corpus_dir)
    raw = (corpus_dir / 'corpus.json').read_bytes()
    manifest = json.loads(raw)
    if manifest.get('schema') != SCHEMA:
        raise SystemExit('Corpus inconnu : schéma ' + str(manifest.get('schema')))
    manifest['manifeste_sha256'] = hashlib.sha256(raw).hexdigest()
    if verify:
        for clip in manifest['clips']:
            path = corpus_dir / clip['envoi']['fichier']
            if not path.is_file() or sha256_file(path) != clip['envoi']['sha256']:
                raise SystemExit('Corpus altéré ou incomplet : ' + clip['envoi']['fichier'])
    return manifest
