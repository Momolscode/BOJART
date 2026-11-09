#!/usr/bin/env python3
"""Décoder un son synthétique exactement comme Jarvis avant de transcrire, sans poids ni micro.

LocalVoice passe le WAV reçu à faster-whisper, qui le décode avec PyAV. Si ce décodage casse
(par exemple une version de PyAV incompatible), chaque transcription échoue sur la tour.
Ce contrôle ne charge aucun modèle : il vérifie seulement la chaîne fichier → échantillons.

  python tools/verifier_voix.py     # JSON ; code 0 si le décodage réussit, 1 sinon
"""
import io
import json
import math
import struct
import sys
import wave

RATE = 16000


def synthetic_wav(seconds=1.0, rate=RATE, frequency=440.0):
    frames = int(seconds * rate)
    samples = (int(8000 * math.sin(2 * math.pi * frequency * i / rate)) for i in range(frames))
    buffer = io.BytesIO()
    with wave.open(buffer, 'wb') as out:
        out.setnchannels(1)
        out.setsampwidth(2)
        out.setframerate(rate)
        out.writeframes(b''.join(struct.pack('<h', s) for s in samples))
    return buffer.getvalue()


def versions():
    found = {}
    for name in ('faster_whisper', 'av', 'ctranslate2'):
        try:
            found[name] = __import__(name).__version__
        except Exception:  # absent or broken package: reported as missing, the decode result says the rest
            found[name] = None
    return found


def check(decode=None):
    if decode is None:
        from faster_whisper.audio import decode_audio as decode
    raw = synthetic_wav()
    result = {'versions': versions(), 'attendu': RATE}
    try:
        samples = decode(io.BytesIO(raw), sampling_rate=RATE)  # same entry point as WhisperModel.transcribe(BytesIO)
    except Exception as exc:  # any failure here would surface as an HTTP 500 on /api/voice/transcribe
        return result | {'ok': False, 'detail': f'Décodage audio impossible : {type(exc).__name__}: {exc}'}
    count = len(samples)
    ok = abs(count - RATE) <= RATE // 100
    return result | {'ok': ok, 'echantillons': count,
                     **({} if ok else {'detail': f'{count} échantillons décodés pour 1 s à {RATE} Hz.'})}


def main():
    result = check()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result['ok'] else 1


if __name__ == '__main__':
    sys.exit(main())
