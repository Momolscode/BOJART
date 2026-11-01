"""Software receipts with synthetic hardware; these tests do not qualify a target PC."""
import contextlib
import io
import json
import os
from pathlib import Path
import subprocess
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from bojart_ops import environment as env
from tools import diagnose_environment as cli
from tools import doctor


class EnvironmentTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def paths(self, **values):
        return {key: values.get(key) for key in env.EXECUTABLES}

    def test_nvidia_memory_remains_per_device(self):
        output = 'NVIDIA GeForce RTX 4060 Ti, 16380, 580.12\nNVIDIA GeForce RTX 4060 Ti, 8188, 580.12\n'
        with patch.object(env, 'command', return_value=('ok', output)):
            result = env.gpu_report('/fixture/nvidia-smi')
        self.assertEqual(result['status'], 'observed')
        self.assertEqual([g['vram_mib'] for g in result['devices']], [16380, 8188])
        self.assertEqual(result['devices'][0]['vram_gib'], 16380/1024)
        self.assertNotIn('total_vram', result)

    def test_unavailable_gpu_values_are_unknown_not_zero(self):
        with patch.object(env, 'command', return_value=('ok', 'NVIDIA Test, N/A, N/A\n')):
            result = env.gpu_report('/fixture/nvidia-smi')
        self.assertIsNone(result['devices'][0]['vram_gib'])
        self.assertIsNone(result['devices'][0]['driver_version'])

    def test_absent_nvidia_does_not_mean_no_gpu(self):
        with patch.object(env, 'command') as command:
            result = env.gpu_report(None)
        command.assert_not_called()
        self.assertEqual(result['status'], 'not_detected')
        self.assertEqual(result['other_gpu_vendors'], 'not_probed')

    def test_invalid_gpu_output_rejects_the_whole_observation(self):
        for output in ('', 'NVIDIA Test, -1, 580.12\n', 'NVIDIA Test, nan, 580.12\n',
                       'NVIDIA Test, 8192, /private/secret\n',
                       'NVIDIA Test, 8192, 580.12\nbad\n', 'NVIDIA Test, 8192, 580.12, extra\n'):
            with self.subTest(output=output), patch.object(env, 'command', return_value=('ok', output)):
                result = env.gpu_report('/fixture/nvidia-smi')
                self.assertEqual(result['status'], 'invalid_output')
                self.assertEqual(result['devices'], [])

    def test_tool_versions_only_expose_parsed_values(self):
        outputs = {'/ffmpeg': 'ffmpeg version 7.1 Copyright\n/private/build/secret\n',
                   '/blender': 'Blender 4.5.2\nprivate build paths\n', '/node': 'v22.3.0\n'}
        with patch.object(env, 'command', side_effect=lambda path, args: ('ok', outputs[path])):
            result = env.executable_report(self.paths(ffmpeg='/ffmpeg', blender='/blender', node='/node'))
        self.assertEqual(result['ffmpeg']['version'], '7.1')
        self.assertEqual(result['blender']['version'], '4.5.2')
        self.assertEqual(result['node']['version_probe'], 'verified')
        self.assertFalse(result['blender']['integration_qualified'])
        self.assertNotIn('private', json.dumps(result))

    def test_gui_tools_and_ollama_are_detected_without_launching(self):
        paths = self.paths(ollama='/ollama', aftereffects='/aerender', orcaslicer='/OrcaSlicer', uvtools='/UVtools')
        with patch.object(env, 'command') as command:
            result = env.executable_report(paths)
        command.assert_not_called()
        for key in ('ollama', 'aftereffects', 'orcaslicer', 'uvtools'):
            self.assertTrue(result[key]['detected'])
            self.assertEqual(result[key]['version_probe'], 'not_run')
            self.assertIsNone(result[key]['version'])

    def test_failed_or_unrecognized_version_does_not_claim_verified(self):
        for status, output in [('failed', None), ('timeout', None), ('ok', 'no version')]:
            with self.subTest(status=status), patch.object(env, 'command', return_value=(status, output)):
                result = env.executable_report(self.paths(ffmpeg='/ffmpeg'))['ffmpeg']
                self.assertNotEqual(result['version_probe'], 'verified')
                self.assertIsNone(result['version'])
                self.assertTrue(result['detected'])

    def test_process_uses_argument_array_timeout_and_discards_stderr(self):
        with patch.object(env.subprocess, 'run', return_value=SimpleNamespace(returncode=0, stdout=b'v22.3.0\n')) as run:
            self.assertEqual(env.command('/installed path/node', ('--version',)), ('ok', 'v22.3.0\n'))
        args, kw = run.call_args
        self.assertEqual(args[0], ['/installed path/node', '--version'])
        self.assertFalse(kw['shell'])
        self.assertEqual(kw['timeout'], env.TIMEOUT)
        self.assertEqual(kw['stderr'], subprocess.DEVNULL)
        self.assertEqual(kw['stdin'], subprocess.DEVNULL)

    def test_process_timeout_bad_encoding_size_and_failure_have_no_raw_errors(self):
        for result, expected in [(subprocess.TimeoutExpired('secret', 4), 'timeout'),
                                 (OSError('secret'), 'failed'),
                                 (SimpleNamespace(returncode=1, stdout=b'secret'), 'failed'),
                                 (SimpleNamespace(returncode=0, stdout=b'\xff'), 'failed'),
                                 (SimpleNamespace(returncode=0, stdout=b'x'*(env.MAX_OUTPUT+1)), 'invalid_output')]:
            with self.subTest(expected=expected):
                kwargs = {'side_effect': result} if isinstance(result, Exception) else {'return_value': result}
                with patch.object(env.subprocess, 'run', **kwargs):
                    self.assertEqual(env.command('/fixture', ('--version',)), (expected, None))

    def test_explicit_tool_path_is_a_single_existing_path(self):
        tool = self.root/'tool with spaces.exe'
        tool.write_text('fixture')
        tool.chmod(0o700)
        with patch.object(env.shutil, 'which', return_value=None):
            resolved = env.resolve_tools({'blender': str(tool)})
        self.assertEqual(resolved['blender'], str(tool.resolve()))
        for value in ({'unknown': str(tool)}, {'blender': 'relative'}, {'blender': str(tool)+' --python-expr bad'}):
            with self.assertRaises(ValueError):
                env.resolve_tools(value)

    def test_batch_wrappers_are_not_executed(self):
        tool = self.root/'tool.cmd';tool.write_text('echo fixture');tool.chmod(0o700)
        with self.assertRaises(ValueError):
            env.resolve_tools({'blender': str(tool)})
        with patch.object(env.shutil, 'which', return_value=str(tool)):
            self.assertTrue(all(v is None for v in env.resolve_tools().values()))

    def test_report_does_not_promote_hardware_or_package_metadata(self):
        with patch.object(env, 'resolve_tools', return_value=self.paths()), \
             patch.object(env, 'ram_bytes', return_value=32*1024**3), \
             patch.object(env.importlib.metadata, 'version', return_value='fixture'), \
             patch('urllib.request.OpenerDirector.open', side_effect=AssertionError('No network')):
            result = env.report()
        self.assertEqual(result['target_hardware_dataset']['values']['ram_gib'], 32)
        self.assertFalse(result['target_hardware_dataset']['complete'])
        self.assertIsNone(result['target_hardware_dataset']['values']['cuda_runtime'])
        self.assertIn('monitor_ids', result['target_hardware_dataset']['missing_fields'])
        self.assertFalse(result['target_identity_confirmed'])
        self.assertFalse(result['production_ready'])
        self.assertEqual(result['provider_calls'], 0)
        self.assertEqual(result['scope'], 'host_running_this_command')
        self.assertFalse(result['python_packages']['docling']['import_tested'])
        self.assertEqual(result['python_packages']['docling']['status'], 'metadata_found')

    def test_ram_failure_is_unknown_and_linux_units_are_bytes(self):
        with patch.object(env.os, 'sysconf', side_effect=[1024, 4096], create=True):
            self.assertEqual(env.ram_bytes('Linux'), 4194304)
        with patch.object(env.os, 'sysconf', side_effect=OSError('fixture'), create=True):
            self.assertIsNone(env.ram_bytes('Linux'))
        self.assertIsNone(env.ram_bytes('unsupported'))

    def test_catalog_mappings_and_dataset_fields_match_research(self):
        base = env.ROOT/'docs/research/launch-toolchain-2026-11-01'
        ids = {row['id'] for row in json.loads((base/'TOOLCHAIN.json').read_text())['tools']}
        self.assertTrue(set(env.PACKAGES.values()) <= ids)
        self.assertTrue({value[3] for value in env.EXECUTABLES.values() if value[3]} <= ids)
        self.assertTrue(set(env.UNPROBED) <= ids)
        data = next(d for d in json.loads((base/'DATA_REQUIREMENTS.json').read_text())['datasets'] if d['id'] == 'target_hardware')
        with patch.object(env, 'resolve_tools', return_value=self.paths()):
            result = env.report()
        self.assertEqual(set(result['target_hardware_dataset']['values']), set(data['required_fields']))

    def test_default_cli_does_not_write_and_invalid_args_do_not_probe(self):
        fixture = {'schema': 'fixture', 'production_ready': False}
        with patch.object(cli, 'report', return_value=fixture), patch.object(cli, 'save_report') as save, \
             contextlib.redirect_stdout(io.StringIO()) as output:
            self.assertEqual(cli.main([]), 0)
        save.assert_not_called()
        self.assertEqual(json.loads(output.getvalue()), fixture)
        with patch.object(cli, 'report') as report, contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit):
                cli.main(['--tool-path', 'not_a_tool=/bad'])
        report.assert_not_called()

    def test_saved_report_is_new_private_and_outside_repository(self):
        destination = self.root/'diagnostics/report.json'
        self.assertEqual(cli.save_report({'fixture': True}, destination), destination.resolve())
        self.assertEqual(json.loads(destination.read_text()), {'fixture': True})
        if os.name != 'nt':
            self.assertEqual(destination.stat().st_mode & 0o777, 0o600)
        with self.assertRaises(FileExistsError):
            cli.save_report({'fixture': False}, destination)
        self.assertEqual(json.loads(destination.read_text()), {'fixture': True})
        with self.assertRaises(ValueError):
            cli.save_report({}, cli.ROOT/'private-report.json')

    def test_failed_save_removes_partial_receipt(self):
        destination = self.root/'broken.json'
        with self.assertRaises(TypeError):
            cli.save_report({'bad': object()}, destination)
        self.assertFalse(destination.exists())

    def test_existing_diagnostic_only_probes_environment_when_requested(self):
        with patch.object(doctor, 'environment_report', return_value={'fixture': True}) as inventory:
            result = doctor.report(memory_state=self.root/'memory', runtime_state=self.root/'work')
            inventory.assert_not_called()
            self.assertNotIn('environment', result)
            expanded = doctor.report(memory_state=self.root/'memory', runtime_state=self.root/'work', check_tools=True)
        self.assertEqual(expanded['environment'], {'fixture': True})
        self.assertEqual(result['launch_blockers'], expanded['launch_blockers'])
        self.assertFalse((self.root/'memory').exists())
        self.assertFalse((self.root/'work').exists())


if __name__ == '__main__':
    unittest.main()
