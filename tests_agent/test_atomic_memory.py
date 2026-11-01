"""Atomic import, consistent context and forced-process-stop regression cases."""
import json
import os
from pathlib import Path
import queue
import subprocess
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch

from bojart_memory import Memory, MemoryError
from bojart_memory.agent import AgentMemory, REPO

PROJECT = 'bojart.jarvis'


class AtomicMemoryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.repo = self.root / 'repo'
        (self.repo / 'data/knowledge').mkdir(parents=True)
        (self.repo / 'docs').mkdir()
        self.records = [
            {'path': path, 'project': PROJECT, 'provenance': 'Atomic memory test fixture'}
            for path in ('docs/a.md', 'docs/b.md', 'data/knowledge/claims.jsonl')
        ]
        (self.repo / 'data/knowledge/index.json').write_text(json.dumps(self.records), encoding='utf-8')
        self.write_generation('oldgeneration')
        self.agent = AgentMemory(self.root / 'state', repo=self.repo)
        self.agent.index()

    def write_generation(self, generation):
        for name in ('a', 'b'):
            (self.repo / ('docs/' + name + '.md')).write_text(
                'generation ' + generation + ' witness_' + name, encoding='utf-8')
        claim = {
            'claim_id': 'generation', 'subject': 'generation', 'predicate': 'label',
            'value': generation, 'project': PROJECT, 'status': 'observed',
            'sources': ['test-fixture'], 'observed_on': '2026-11-01', 'supersedes': [],
        }
        (self.repo / 'data/knowledge/claims.jsonl').write_text(
            json.dumps(claim) + '\n', encoding='utf-8')

    def pointers(self):
        with Memory(self.agent.state, readonly=True) as memory:
            return dict(memory.db.execute(
                'SELECT source_path,current_version FROM sources ORDER BY source_path'))

    def import_doc(self, memory, name):
        return memory.ingest_file(
            self.repo / ('docs/' + name + '.md'), root=self.repo,
            project=PROJECT, collection='canonical', provenance='Atomic memory test fixture')

    def test_failed_index_rolls_back_all_references_and_search_chunks(self):
        self.agent.note('local.note', 'keep this', 'test fixture', PROJECT)
        before, pointers = self.agent.status(), self.pointers()
        self.write_generation('newgeneration')
        (self.repo / 'docs/b.md').write_bytes(b'\xffinvalid UTF8')
        with self.assertRaises(MemoryError):
            self.agent.index()
        self.assertEqual(self.agent.status(), before)
        self.assertEqual(self.pointers(), pointers)
        self.assertFalse(self.agent.search('newgeneration', PROJECT)['results'])
        self.assertTrue(any(f['key'] == 'local.note' for f in self.agent.facts(PROJECT)))

    def test_retry_after_failed_batch_publishes_once(self):
        self.write_generation('newgeneration')
        (self.repo / 'docs/b.md').write_bytes(b'\xff')
        with self.assertRaises(MemoryError):
            self.agent.index()
        self.write_generation('newgeneration')
        result = self.agent.index()
        self.assertTrue(result['atomic'])
        self.assertEqual(result['new_versions'], 3)
        self.assertEqual(self.agent.index()['new_versions'], 0)
        self.assertEqual(self.agent.facts(PROJECT)[0]['value'], 'newgeneration')

    def test_uncommitted_batch_is_invisible_to_other_connections(self):
        before = self.pointers()
        self.write_generation('newgeneration')
        with Memory(self.agent.state) as memory:
            with memory.transaction():
                self.import_doc(memory, 'a')
                self.assertEqual(self.pointers(), before)
                self.import_doc(memory, 'b')
                self.assertEqual(self.pointers(), before)
        self.assertNotEqual(self.pointers()['docs/a.md'], before['docs/a.md'])
        self.assertNotEqual(self.pointers()['docs/b.md'], before['docs/b.md'])

    def test_nested_failure_keeps_outer_batch_without_inner_changes(self):
        before = self.pointers()
        self.write_generation('newgeneration')
        with Memory(self.agent.state) as memory:
            with memory.transaction():
                self.import_doc(memory, 'a')
                with self.assertRaisesRegex(RuntimeError, 'inner failure'):
                    with memory.transaction():
                        self.import_doc(memory, 'b')
                        raise RuntimeError('inner failure')
        after = self.pointers()
        self.assertNotEqual(after['docs/a.md'], before['docs/a.md'])
        self.assertEqual(after['docs/b.md'], before['docs/b.md'])

    def test_retirement_rolls_back_with_failed_outer_batch(self):
        before = self.pointers()
        with Memory(self.agent.state) as memory:
            with self.assertRaises(RuntimeError):
                with memory.transaction():
                    self.assertEqual(len(memory.reconcile_collection(
                        project=PROJECT, collection='canonical', source_paths=[])), 3)
                    raise RuntimeError('abort')
        self.assertEqual(self.pointers(), before)

    def test_readonly_connection_cannot_open_write_batch(self):
        with Memory(self.agent.state, readonly=True) as memory:
            with self.assertRaises(MemoryError):
                with memory.transaction():
                    self.fail('read-only batch accepted')

    def test_context_keeps_one_snapshot_during_an_index_update(self):
        original_facts = self.agent.facts
        before = self.pointers()
        def publish_after_facts(project, **kwargs):
            facts = original_facts(project, **kwargs)
            self.write_generation('newgeneration')
            self.agent.index()
            return facts
        with patch.object(self.agent, 'facts', side_effect=publish_after_facts):
            context = self.agent.context('generation', PROJECT)
        self.assertEqual(context['consistency'], 'single_committed_sqlite_snapshot')
        self.assertIn('oldgeneration', context['text'])
        self.assertNotIn('newgeneration', context['text'])
        self.assertTrue(context['evidence'])
        for source in context['evidence']:
            self.assertEqual(source['version_id'], before[source['source_path']])
        self.assertIn('newgeneration', self.agent.context('generation', PROJECT)['text'])

    def test_cli_index_rolls_back_if_a_later_file_is_invalid(self):
        before = self.pointers()
        self.write_generation('newgeneration')
        (self.repo / 'docs/b.md').write_bytes(b'\xff')
        result = subprocess.run([
            sys.executable, '-m', 'bojart_memory', '--state', str(self.agent.state),
            'index-repo', '--repo', str(self.repo)],
            cwd=REPO, capture_output=True, text=True, timeout=20)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self.pointers(), before)

    def test_cli_ingest_rolls_back_a_new_collection(self):
        before = self.agent.status()
        incoming = self.root / 'incoming'
        incoming.mkdir()
        (incoming / 'a.md').write_text('new source to import', encoding='utf-8')
        (incoming / 'b.md').write_bytes(b'\xff')
        result = subprocess.run([
            sys.executable, '-m', 'bojart_memory', '--state', str(self.agent.state),
            'ingest', str(incoming), '--project', PROJECT, '--collection', 'incoming',
            '--provenance', 'Atomic batch fixture'],
            cwd=REPO, capture_output=True, text=True, timeout=20)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self.agent.status(), before)

    def kill_worker(self, commit):
        self.write_generation('newgeneration')
        code = """
import sys
from pathlib import Path
from bojart_memory import Memory
state, root = Path(sys.argv[1]), Path(sys.argv[2])
with Memory(state) as memory:
    with memory.transaction():
        for name in ('a', 'b'):
            memory.ingest_file(root/('docs/'+name+'.md'), root=root,
                project='bojart.jarvis', collection='canonical',
                provenance='Atomic memory test fixture')
        if sys.argv[3] == 'pending':
            print('ready', flush=True)
            sys.stdin.read()
    if sys.argv[3] == 'committed':
        print('ready', flush=True)
        sys.stdin.read()
"""
        process = subprocess.Popen(
            [sys.executable, '-c', code, str(self.agent.state), str(self.repo),
             'committed' if commit else 'pending'],
            cwd=REPO, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, env=dict(os.environ, PYTHONUTF8='1'))
        lines = queue.Queue()
        reader = threading.Thread(target=lambda: lines.put(process.stdout.readline()), daemon=True)
        reader.start()
        try:
            self.assertEqual(lines.get(timeout=15).strip(), 'ready')
            process.kill()
            process.wait(timeout=15)
        finally:
            if process.poll() is None:
                process.kill()
                process.wait(timeout=15)
            reader.join(timeout=5)
            for stream in (process.stdin, process.stdout, process.stderr):
                stream.close()

    def test_forced_stop_discards_uncommitted_batch(self):
        before = self.pointers()
        self.kill_worker(commit=False)
        self.assertEqual(self.pointers(), before)
        with Memory(self.agent.state, readonly=True) as memory:
            self.assertTrue(memory.verify()['ok'])
        self.assertFalse(self.agent.search('newgeneration', PROJECT)['results'])

    def test_forced_stop_keeps_committed_documents(self):
        before = self.pointers()
        self.kill_worker(commit=True)
        after = self.pointers()
        self.assertNotEqual(after['docs/a.md'], before['docs/a.md'])
        self.assertNotEqual(after['docs/b.md'], before['docs/b.md'])
        with Memory(self.agent.state, readonly=True) as memory:
            self.assertTrue(memory.verify()['ok'])
        self.assertTrue(self.agent.search('newgeneration', PROJECT)['results'])

    def test_backup_after_failed_batch_restores_previous_context(self):
        before = self.agent.context('generation', PROJECT)
        self.write_generation('newgeneration')
        (self.repo / 'docs/b.md').write_bytes(b'\xff')
        with self.assertRaises(MemoryError):
            self.agent.index()
        with Memory(self.agent.state, readonly=True) as memory:
            memory.backup(self.root / 'snapshot')
        Memory.restore(self.root / 'snapshot', self.root / 'restored')
        restored = AgentMemory(self.root / 'restored', repo=self.root / 'absent')
        self.assertEqual(restored.context('generation', PROJECT)['sha256'], before['sha256'])


if __name__ == '__main__':
    unittest.main()
