"""Fault injection for media receipts. The separate CI job runs real FFmpeg."""
import contextlib
import copy
import io
import json
from pathlib import Path
import struct
import subprocess
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from bojart_ops import media_check as media
from tools import diagnose_environment as cli


def metadata():
    return {'format': {'duration': '2.000000'}, 'streams': [
        {'codec_type': 'video', 'codec_name': 'h264', 'width': 720, 'height': 1280,
         'pix_fmt': 'yuv420p', 'avg_frame_rate': '24/1', 'nb_read_frames': '48',
         'duration': '2', 'start_time': '0'},
        {'codec_type': 'audio', 'codec_name': 'aac', 'sample_rate': '48000',
         'channels': 1, 'duration': '2', 'start_time': '0'},
    ]}


PCM = struct.pack('<hh', 700, -700) * 48000


class MediaTests(unittest.TestCase):
    def setUp(self):
        self.directories = []
        self.paths = {key: '/fixture/'+key if key in {'ffmpeg', 'ffprobe'} else None
                      for key in media.EXECUTABLES}
        resolver = patch.object(media, 'resolve_tools', return_value=self.paths)
        versions = patch.object(media, 'executable_report', return_value={
            key: {'version': 'fixture'} for key in media.EXECUTABLES})
        resolver.start(); versions.start()
        self.addCleanup(resolver.stop); self.addCleanup(versions.stop)

    def process(self, executable, args, directory, **kwargs):
        self.directories.append(Path(directory))
        if 'testsrc2=size=720x1280:rate=24:duration=2' in args:
            Path(args[-1]).write_bytes(b'synthetic fixture')
            return b''
        if executable.endswith('ffprobe'):
            return json.dumps(metadata()).encode()
        return PCM if args[-2] == 's16le' else b''

    def check_with(self, process=None):
        with patch.object(media, '_run', side_effect=process or self.process):
            result = media.check_media()
        self.assertTrue(result['temporary_media_removed'])
        self.assertTrue(all(not directory.exists() for directory in self.directories))
        return result

    def test_missing_binary_is_blocked_without_generating_media(self):
        self.paths['ffprobe'] = None
        with patch.object(media, '_run') as run:
            result = media.check_media()
        run.assert_not_called()
        self.assertEqual(result['status'], 'blocked')
        self.assertEqual(result['missing_tools'], ['ffprobe'])
        self.assertEqual(result['synthetic_exports_created'], 0)

    def test_success_has_limited_scope_and_removes_fixture(self):
        result = self.check_with()
        self.assertEqual(result['status'], 'passed')
        self.assertEqual(len(result['stages']), 6)
        self.assertEqual(result['metadata']['frames'], 48)
        self.assertTrue(result['audio']['non_silent'])
        self.assertFalse(result['production_ready'])
        self.assertFalse(result['artistic_approval'])
        self.assertFalse(result['physical_hardware_qualified'])
        self.assertNotIn('/fixture', json.dumps(result))
        self.assertEqual(len(result['artifact']['sha256']), 64)

    def test_decode_failure_does_not_accept_good_metadata(self):
        def fail_decode(executable, args, directory, **kwargs):
            if args[-2] == 'null':
                raise media.CheckFailure('process_failed')
            return self.process(executable, args, directory, **kwargs)
        result = self.check_with(fail_decode)
        self.assertEqual(result['status'], 'failed')
        self.assertEqual(result['stages'][-1]['name'], 'decode')
        self.assertNotIn('audio', result)

    def test_failed_encoding_removes_partial_file(self):
        def failed(executable, args, directory, **kwargs):
            self.process(executable, args, directory, **kwargs)
            raise media.CheckFailure('timeout')
        result = self.check_with(failed)
        self.assertEqual(result['reason'], 'timeout')
        self.assertEqual(result['synthetic_exports_created'], 0)

    def test_successful_process_without_artifact_is_failure(self):
        result = self.check_with(lambda *args, **kwargs: b'')
        self.assertEqual(result['status'], 'failed')
        self.assertEqual(result['reason'], 'invalid_artifact_size')
        self.assertEqual(result['synthetic_exports_created'], 0)

    def test_mutation_after_probe_is_rejected(self):
        def changed(executable, args, directory, **kwargs):
            output = self.process(executable, args, directory, **kwargs)
            if args[-2] == 's16le':
                (Path(directory)/'synthetic-check.mp4').write_bytes(b'changed')
            return output
        result = self.check_with(changed)
        self.assertEqual(result['reason'], 'artifact_changed')

    def test_metadata_rejects_missing_extra_wrong_and_nonfinite_streams(self):
        cases = [None, [], {}, {'streams': []}, metadata()]
        cases[-1]['streams'].append(copy.deepcopy(cases[-1]['streams'][1]))
        for key, value in [('nb_read_frames', '47'), ('avg_frame_rate', '0/0'),
                           ('duration', 'NaN'), ('duration', 'inf'), ('start_time', '1'),
                           ('height', 720), ('pix_fmt', 'yuv444p'), ('codec_name', 'hevc')]:
            bad = metadata(); bad['streams'][0][key] = value; cases.append(bad)
        for key, value in [('codec_name', 'mp3'), ('sample_rate', '44100'), ('channels', 2)]:
            bad = metadata(); bad['streams'][1][key] = value; cases.append(bad)
        for value in cases:
            with self.subTest(value=value), self.assertRaises(media.CheckFailure):
                media._metadata(json.dumps(value).encode())
        for value in (b'invalid json secret', b'\xff'):
            with self.assertRaisesRegex(media.CheckFailure, '^unexpected_metadata$'):
                media._metadata(value)

    def test_silent_short_clipped_and_malformed_audio_is_rejected(self):
        for value in (b'', b'\0' * 192000, PCM[:1000], PCM + PCM,
                      struct.pack('<h', 32767) * 96000, PCM + b'\0'):
            with self.subTest(size=len(value)), self.assertRaises(media.CheckFailure):
                media._audio(value)
        self.assertEqual(media._audio(PCM)['decoded_samples'], 96000)

    def test_audio_failure_marks_receipt_failed(self):
        def silent(executable, args, directory, **kwargs):
            output = self.process(executable, args, directory, **kwargs)
            return b'\0' * len(PCM) if args[-2] == 's16le' else output
        result = self.check_with(silent)
        self.assertEqual(result['status'], 'failed')
        self.assertEqual(result['reason'], 'unexpected_audio_signal')

    def test_process_is_bounded_and_uses_no_shell_or_stderr_capture(self):
        def process(args, **kwargs):
            self.assertEqual(args, ['/tool with spaces', '-version'])
            self.assertIs(kwargs['shell'], False)
            self.assertEqual(kwargs['timeout'], 15)
            self.assertEqual(kwargs['stdin'], subprocess.DEVNULL)
            self.assertEqual(kwargs['stderr'], subprocess.DEVNULL)
            kwargs['stdout'].write(b'answer')
            return SimpleNamespace(returncode=0)
        with patch.object(media.subprocess, 'run', side_effect=process):
            self.assertEqual(media._run('/tool with spaces', ['-version'], '.'), b'answer')
            with self.assertRaisesRegex(media.CheckFailure, 'output_too_large'):
                media._run('/tool with spaces', ['-version'], '.', max_output=3)

    def test_process_errors_disclose_only_reason_codes(self):
        for outcome, reason in [(subprocess.TimeoutExpired('private path', 15), 'timeout'),
                                (OSError('secret'), 'process_unavailable'),
                                (SimpleNamespace(returncode=1), 'process_failed')]:
            kwargs = {'side_effect': outcome} if isinstance(outcome, Exception) else {'return_value': outcome}
            with patch.object(media.subprocess, 'run', **kwargs):
                with self.assertRaisesRegex(media.CheckFailure, '^'+reason+'$'):
                    media._run('/private', [], '.')

    def test_cli_default_never_runs_media_check(self):
        with patch.object(cli, 'report', return_value={}), patch.object(cli, 'check_media') as check, \
             contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(cli.main([]), 0)
        check.assert_not_called()

    def test_cli_explicit_check_returns_failure_code_and_saves_receipt(self):
        for status, code in [('passed', 0), ('blocked', 2), ('failed', 2)]:
            with tempfile.TemporaryDirectory() as directory, \
                 patch.object(cli, 'report', return_value={}), \
                 patch.object(cli, 'check_media', return_value={'status': status}) as check, \
                 contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                target = Path(directory)/'receipt.json'
                self.assertEqual(cli.main(['--check-media', '--output', str(target)]), code)
                self.assertEqual(json.loads(target.read_text())['media_check']['status'], status)
                check.assert_called_once_with(tool_paths={})


if __name__ == '__main__':
    unittest.main()
