"""Opt-in, local FFmpeg export/decode receipt using only a synthetic fixture."""
from __future__ import annotations

from array import array
from datetime import datetime, timezone
from fractions import Fraction
import hashlib
import json
import math
from pathlib import Path
import subprocess
import sys
import tempfile
import time

from bojart_ops.environment import EXECUTABLES, executable_report, resolve_tools

PROFILE = {'width': 720, 'height': 1280, 'fps': 24, 'frames': 48,
           'duration_seconds': 2, 'video_codec': 'h264', 'pixel_format': 'yuv420p',
           'audio_codec': 'aac', 'sample_rate': 48000, 'channels': 1}
MAX_MEDIA_BYTES = 10 * 1024 * 1024


class CheckFailure(Exception):
    """A fixed reason code, never a subprocess error or local path."""


def _run(executable, args, directory, *, timeout=15, max_output=65536):
    # Spool stdout instead of buffering arbitrary process output in memory.
    with tempfile.TemporaryFile() as output:
        try:
            result = subprocess.run([executable, *args], stdin=subprocess.DEVNULL,
                                    stdout=output, stderr=subprocess.DEVNULL,
                                    cwd=directory, shell=False, timeout=timeout)
        except subprocess.TimeoutExpired:
            raise CheckFailure('timeout') from None
        except OSError:
            raise CheckFailure('process_unavailable') from None
        if result.returncode:
            raise CheckFailure('process_failed')
        output.seek(0)
        data = output.read(max_output + 1)
        if len(data) > max_output:
            raise CheckFailure('output_too_large')
        return data


def _stage(receipt, name, operation):
    started = time.monotonic()
    stage = {'name': name, 'status': 'failed'}
    receipt['stages'].append(stage)
    try:
        value = operation()
        stage['status'] = 'passed'
        return value
    except CheckFailure as exc:
        stage['reason'] = str(exc)
        raise
    except OSError:
        stage['reason'] = 'filesystem_error'
        raise CheckFailure('filesystem_error') from None
    finally:
        stage['elapsed_ms'] = round((time.monotonic() - started) * 1000, 3)


def _metadata(raw):
    try:
        data = json.loads(raw)
        streams = data['streams']
        if len(streams) != 2:
            raise ValueError()
        video, = [s for s in streams if s['codec_type'] == 'video']
        audio, = [s for s in streams if s['codec_type'] == 'audio']
        duration = float(data['format']['duration'])
        video_duration, audio_duration = float(video['duration']), float(audio['duration'])
        start_delta = abs(float(video['start_time']) - float(audio['start_time']))
        valid = (video['codec_name'] == 'h264' and video['width'] == 720
                 and video['height'] == 1280 and video['pix_fmt'] == 'yuv420p'
                 and Fraction(video['avg_frame_rate']) == 24
                 and int(video['nb_read_frames']) == 48
                 and audio['codec_name'] == 'aac' and int(audio['sample_rate']) == 48000
                 and audio['channels'] == 1 and start_delta <= 0.05
                 and all(math.isfinite(v) and abs(v - 2) <= 0.06
                         for v in (duration, video_duration, audio_duration)))
        if not valid:
            raise ValueError()
    except (ValueError, KeyError, TypeError, UnicodeError, ZeroDivisionError, OverflowError):
        raise CheckFailure('unexpected_metadata') from None
    # Whitelist only the measured fields, not tags, paths or build metadata.
    return {**PROFILE, 'duration_seconds': duration,
            'video_duration_seconds': video_duration, 'audio_duration_seconds': audio_duration,
            'start_delta_seconds': start_delta}


def _audio(raw):
    if len(raw) % 2:
        raise CheckFailure('invalid_pcm')
    samples = array('h')
    samples.frombytes(raw)
    if sys.byteorder != 'little':
        samples.byteswap()
    # AAC can add up to two frames of encoder padding to the decoded samples.
    if not 96000 <= len(samples) <= 98048:
        raise CheckFailure('unexpected_sample_count')
    rms = math.sqrt(sum(s * s for s in samples) / len(samples)) / 32768
    peak = max(abs(s) for s in samples) / 32768
    if not (0.005 <= rms <= 0.05 and peak < 0.1):
        raise CheckFailure('unexpected_audio_signal')
    return {'decoded_samples': len(samples), 'rms_full_scale': round(rms, 6),
            'peak_full_scale': round(peak, 6), 'non_silent': True}


def check_media(*, tool_paths=None):
    """Encode, inspect and fully decode a temporary clip; no user media or GPU."""
    started = time.monotonic()
    paths = resolve_tools(tool_paths)
    versions = executable_report({key: paths[key] if key in {'ffmpeg', 'ffprobe'} else None
                                  for key in EXECUTABLES})
    receipt = {
        'schema': 'bojart.synthetic-media-check.v1',
        'observed_at': datetime.now(timezone.utc).isoformat(),
        'scope': 'host_running_this_command', 'status': 'blocked',
        'expected_profile': dict(PROFILE),
        'tools': {key: versions[key] for key in ('ffmpeg', 'ffprobe')},
        'missing_tools': [key for key in ('ffmpeg', 'ffprobe') if not paths[key]],
        'stages': [], 'synthetic_exports_created': 0, 'temporary_media_removed': True,
        'production_ready': False, 'artistic_approval': False,
        'physical_hardware_qualified': False, 'provider_calls': 0,
        'limits': ['Synthetic CPU export only; no production asset or project was rendered.',
                   'Signal measurement does not assess sound design or listening quality.',
                   'No Blender, After Effects, GPU, model, microphone or publishing test.'],
        'probe_source_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    }
    if receipt['missing_tools']:
        receipt['reason'] = 'missing_tools'
        receipt['elapsed_ms'] = round((time.monotonic() - started) * 1000, 3)
        return receipt
    try:
        with tempfile.TemporaryDirectory(prefix='bojart-media-check-') as directory:
            clip = Path(directory) / 'synthetic-check.mp4'
            receipt['temporary_media_removed'] = False
            _stage(receipt, 'encode', lambda: _run(paths['ffmpeg'], [
                '-nostdin', '-hide_banner', '-v', 'error', '-n', '-filter_threads', '1',
                '-f', 'lavfi', '-i', 'testsrc2=size=720x1280:rate=24:duration=2',
                '-f', 'lavfi', '-i', 'sine=frequency=1000:sample_rate=48000:duration=2',
                '-map', '0:v:0', '-map', '1:a:0', '-af', 'volume=0.25',
                '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '23', '-threads', '2',
                '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-b:a', '128k', '-ar', '48000',
                '-ac', '1', '-t', '2', '-movflags', '+faststart', str(clip),
            ], directory, timeout=30))
            def inspect():
                if not clip.is_file() or not 0 < clip.stat().st_size <= MAX_MEDIA_BYTES:
                    raise CheckFailure('invalid_artifact_size')
                content = clip.read_bytes()
                return {'bytes': len(content), 'sha256': hashlib.sha256(content).hexdigest()}

            receipt['artifact'] = _stage(receipt, 'artifact', inspect)
            receipt['synthetic_exports_created'] = 1
            input_options = ['-protocol_whitelist', 'file', '-format_whitelist', 'mov',
                             '-probesize', '10000000', '-analyzeduration', '3000000']
            receipt['metadata'] = _stage(receipt, 'probe', lambda: _metadata(_run(paths['ffprobe'], [
                '-v', 'error', '-max_alloc', '67108864', *input_options,
                '-count_frames', '-of', 'json', '-show_entries',
                'format=duration:stream=codec_type,codec_name,width,height,pix_fmt,avg_frame_rate,'
                'nb_read_frames,duration,start_time,sample_rate,channels', str(clip),
            ], directory)))
            decode_input = ['-nostdin', '-hide_banner', '-v', 'error', '-xerror',
                            '-err_detect', 'explode', '-threads', '2', *input_options,
                            '-i', str(clip)]
            _stage(receipt, 'decode', lambda: _run(paths['ffmpeg'], [
                *decode_input, '-map', '0:v:0', '-map', '0:a:0', '-threads', '2',
                '-f', 'null', '-',
            ], directory))
            receipt['audio'] = _stage(receipt, 'audio_signal', lambda: _audio(_run(paths['ffmpeg'], [
                *decode_input, '-map', '0:a:0', '-vn', '-c:a', 'pcm_s16le',
                '-ar', '48000', '-ac', '1', '-f', 's16le', '-',
            ], directory, max_output=262144)))

            def unchanged():
                if inspect() != receipt['artifact']:
                    raise CheckFailure('artifact_changed')

            _stage(receipt, 'unchanged_artifact', unchanged)
        receipt['temporary_media_removed'] = True
        receipt['status'] = 'passed'
    except (CheckFailure, OSError) as exc:
        receipt['status'] = 'failed'
        receipt['reason'] = str(exc) if isinstance(exc, CheckFailure) else 'filesystem_error'
        receipt['temporary_media_removed'] = 'clip' not in locals() or not clip.exists()
    receipt['elapsed_ms'] = round((time.monotonic() - started) * 1000, 3)
    return receipt
