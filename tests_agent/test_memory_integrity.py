"""Offline integrity, projection and explicit-rebuild regression scenarios."""
import hashlib
import json
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from bojart_memory.core import Memory, MemoryError, canonical, chunks, digest, now


class MemoryIntegrityTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.inputs = self.root/'inputs'
        self.inputs.mkdir()
        self.m = Memory(self.root/'state')

    def tearDown(self):
        self.m.close()
        self.tmp.cleanup()

    def put(self, text='Source fidèle.\nJev reste un décideur texte.', name='guide.md', project='bojart.jarvis', **kw):
        path = self.inputs/name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding='utf-8')
        return self.m.ingest_file(path, root=self.inputs, project=project,
                                  collection='canonical', provenance='offline test fixture', **kw)

    def mutate(self, sql, args=()):
        self.m.db.execute(sql, args)
        self.m.db.commit()

    def assert_refused(self, query='Jev'):
        result = self.m.search(query, project='bojart.jarvis')
        self.assertEqual(result['results'], [])
        self.assertTrue(result['warnings'])
        self.assertFalse(self.m.verify()['ok'])

    def test_clean_source_and_exact_chunk_are_verified(self):
        item = self.put()
        row = self.m.search('Jev', project='bojart.jarvis')['results'][0]
        self.assertTrue(row['source_bytes_verified'])
        self.assertTrue(row['excerpt_matches_source'])
        self.assertTrue(self.m.validate_passage(row)['ok'])
        self.assertTrue(self.m.validate_version(item['version_id'])['ok'])
        self.assertTrue(self.m.verify()['ok'])

    def test_chunk_text_tamper_is_refused(self):
        self.put()
        self.mutate("UPDATE chunks SET text='Jev peut lancer une machine.'")
        self.assert_refused()

    def test_chunk_and_fts_coordinated_tamper_is_refused(self):
        self.put()
        self.mutate("UPDATE chunks SET text='Jev peut lancer une machine.'")
        self.mutate("UPDATE search SET text='Jev peut lancer une machine.'")
        self.assert_refused()

    def test_line_offsets_tamper_is_refused(self):
        self.put()
        self.mutate('UPDATE chunks SET start_line=90,end_line=91')
        self.assert_refused()

    def test_missing_chunk_is_detected_even_when_not_retrieved(self):
        self.put()
        self.mutate('DELETE FROM chunks')
        verdict = self.m.verify()
        self.assertFalse(verdict['ok'])
        self.assertIn('fts_orphan_row', verdict['issues'])

    def test_missing_fts_row_is_detected(self):
        self.put()
        self.mutate('DELETE FROM search')
        self.assertFalse(self.m.verify()['ok'])
        row = dict(self.m.db.execute('SELECT * FROM chunks').fetchone())
        self.assertFalse(self.m.validate_passage(row)['ok'])

    def test_fts_content_tamper_blocks_even_valid_chunk(self):
        self.put()
        self.mutate("UPDATE search SET text='Jev détourné'")
        self.assert_refused()

    def test_internal_fts_damage_without_content_change_is_detected(self):
        self.put()
        # FTS content and chunks still agree. Only posting index blocks change.
        original = self.m.db.execute('SELECT text FROM search').fetchone()[0]
        self.mutate('DELETE FROM search_data WHERE id>10')
        self.assertEqual(self.m.db.execute('SELECT text FROM search').fetchone()[0], original)
        result = self.m.verify()
        self.assertFalse(result['ok'])
        self.assertIn('fts_internal_integrity', result['issues'])

    def test_unknown_or_missing_extractor_is_not_guessed(self):
        self.put()
        self.mutate("UPDATE versions SET extraction='unrecognized_v999'")
        self.assert_refused()
        with self.assertRaises(MemoryError):
            self.m.rebuild_indexes()

    def test_empty_provenance_is_rejected(self):
        self.put()
        self.mutate("UPDATE versions SET provenance=''")
        self.assert_refused()

    def test_observation_without_timezone_is_not_verified(self):
        self.put()
        self.mutate("UPDATE versions SET observed_at='2026-11-02'")
        self.assert_refused()

    def test_mismatched_source_metadata_is_rejected(self):
        self.put()
        self.mutate("UPDATE sources SET source_path='invented.md'")
        self.assert_refused()

    def test_missing_metadata_record_is_detected(self):
        self.put()
        self.m.db.execute('PRAGMA foreign_keys=OFF')
        self.mutate('DELETE FROM assets')
        self.m.db.execute('PRAGMA foreign_keys=ON')
        self.assert_refused()

    def test_changed_original_blocks_retrieval_and_rebuild(self):
        item = self.put()
        self.m._object(item['sha256']).write_text('Changed.', encoding='utf-8')
        self.assert_refused()
        with self.assertRaises(MemoryError):
            self.m.rebuild_indexes()

    def test_passage_metadata_and_text_must_match_verified_version(self):
        self.put()
        row = self.m.search('Jev', project='bojart.jarvis')['results'][0]
        for field, value in [('text','invented'),('start_line',77),('project','bojart.creative'),
                             ('sha256','0'*64),('id',999)]:
            with self.subTest(field=field):
                self.assertFalse(self.m.validate_passage({**row, field:value})['ok'])
        self.assertFalse(self.m.validate_passage({'version_id':row['version_id']})['ok'])

    def test_validation_cache_is_scoped_by_caller_to_one_operation(self):
        self.put()
        row = self.m.search('Jev', project='bojart.jarvis')['results'][0]
        self.assertTrue(self.m.validate_passage(row, cache={})['ok'])
        self.mutate("UPDATE chunks SET text='changed'")
        self.assertFalse(self.m.validate_passage(row, cache={})['ok'])

    @staticmethod
    def ledger():
        return '\n'.join([canonical({'project':'bojart.jarvis','claim_id':'jarvis','value':'vocalneedle'}),
                           '', canonical({'project':'bojart.creative','claim_id':'art','value':'artneedle'})])+'\n'

    def test_claim_projection_keeps_exact_original_lines_and_useful_search(self):
        text = self.ledger()
        a = self.put(text, 'data/knowledge/claims.jsonl')
        self.put(text, 'data/knowledge/claims.jsonl', project='bojart.creative')
        self.assertEqual(self.m.stats()['assets'], 1)
        row = self.m.search('artneedle', project='bojart.creative')['results'][0]
        self.assertEqual((row['start_line'],row['end_line']), (3,3))
        self.assertEqual(row['text'], text.splitlines()[2])
        self.assertEqual(row['extraction'], 'project_jsonl_v1')
        self.assertFalse(self.m.search('artneedle', project='bojart.jarvis', history=True)['results'])
        self.assertTrue(self.m.search('vocalneedle', project='bojart.jarvis')['results'])
        self.assertEqual(self.m._object(a['sha256']).read_text(encoding='utf-8'), text)
        self.assertTrue(self.m.verify()['ok'])

    def test_general_project_jsonl_auto_projection(self):
        self.put(self.ledger(), 'custom.jsonl')
        self.assertTrue(self.m.search('vocalneedle', project='bojart.jarvis')['results'])
        self.assertFalse(self.m.search('artneedle', project='bojart.jarvis')['results'])

    def test_explicit_projection_rejects_unknown_or_missing_project(self):
        for text in ('{"project":"unknown","value":"x"}', '{"value":"x"}',
                     '{"project":"bojart.jarvis","project":"bojart.creative"}'):
            with self.subTest(text=text), self.assertRaises(MemoryError):
                self.put(text, 'selected.jsonl', projection='project_jsonl_v1')
        self.assertEqual(self.m.stats()['versions'], 0)

    def test_mixed_project_jsonl_cannot_fall_back_to_unscoped_text(self):
        with self.assertRaises(MemoryError):
            self.put(self.ledger()+'{"value":"unscoped"}\n', 'custom.jsonl')
        self.assertEqual(self.m.stats()['assets'], 0)

    def insert_legacy(self):
        text = self.ledger()
        path = self.inputs/'data/knowledge/claims.jsonl'
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding='utf-8')
        sha = digest(text.encode())
        sid = digest(canonical(['bojart.jarvis','canonical','data/knowledge/claims.jsonl']).encode())
        vid = digest(canonical([sid,sha]).encode())
        self.m._object(sha).write_bytes(text.encode())
        with self.m.transaction():
            self.m.db.execute('INSERT INTO assets VALUES(?,?,?)', (sha,len(text.encode()),now()))
            self.m.db.execute('INSERT INTO sources VALUES(?,?,?,?,?)', (sid,'bojart.jarvis','canonical','data/knowledge/claims.jsonl',vid))
            self.m.db.execute('INSERT INTO versions VALUES(?,?,?,?,?,?,?)', (vid,sid,sha,now(),'legacy fixture','project_document','utf8_lines_v1'))
            for start,end,body in chunks(text):
                row=self.m.db.execute('INSERT INTO chunks(version_id,start_line,end_line,text) VALUES(?,?,?,?)',(vid,start,end,body))
                self.m.db.execute('INSERT INTO search(rowid,text) VALUES(?,?)',(row.lastrowid,body))
        return vid

    def test_legacy_projection_requires_explicit_indexing_and_preserves_history(self):
        legacy = self.insert_legacy()
        before = self.m.search('artneedle', project='bojart.jarvis', history=True)
        self.assertFalse(before['results'])
        self.assertIn('legacy_project_projection_required', before['warnings'][0]['issues'])
        with self.assertRaises(MemoryError):
            self.m.rebuild_indexes()
        new = self.put(self.ledger(), 'data/knowledge/claims.jsonl')
        self.assertNotEqual(new['version_id'], legacy)
        self.assertEqual(self.m.stats()['versions'], 2)
        self.assertTrue(self.m.search('vocalneedle', project='bojart.jarvis')['results'])
        self.assertFalse(self.m.search('artneedle', project='bojart.jarvis', history=True)['results'])
        self.assertEqual(self.m.rebuild_indexes()['rebuilt_versions'], 2)
        self.assertTrue(self.m.verify()['ok'])

    def test_projection_handles_long_lines_without_reserializing(self):
        text = canonical({'project':'bojart.jarvis','value':'a'*6000})+'\n'
        self.put(text, 'records.jsonl')
        pieces = self.m.db.execute('SELECT start_line,end_line,text FROM chunks ORDER BY id').fetchall()
        self.assertTrue(all(tuple(row)[:2] == (1,1) for row in pieces))
        self.assertEqual(''.join(row['text'] for row in pieces), text.strip())
        self.assertTrue(self.m.verify()['ok'])

    def add_derivatives_and_episode(self):
        self.m.db.execute('CREATE TABLE agent_vectors(chunk_id INTEGER REFERENCES chunks(id), vector TEXT)')
        self.m.db.execute('INSERT INTO agent_vectors SELECT id,\'[1,2]\' FROM chunks')
        self.m.db.execute('CREATE TABLE agent_episodes(id TEXT PRIMARY KEY, payload TEXT)')
        self.m.db.execute("INSERT INTO agent_episodes VALUES('episode1','preserve original conversation')")
        self.m.db.commit()

    def test_rebuild_repairs_only_derived_indexes_and_invalidates_vectors(self):
        item=self.put()
        self.add_derivatives_and_episode()
        original=self.m._object(item['sha256']).read_bytes()
        self.mutate("UPDATE chunks SET text='tampered'")
        verdict=self.m.rebuild_indexes()
        self.assertEqual(verdict['invalidated_vectors'],1)
        self.assertTrue(self.m.verify()['ok'])
        self.assertTrue(self.m.search('Jev',project='bojart.jarvis')['results'])
        self.assertEqual(self.m._object(item['sha256']).read_bytes(),original)
        self.assertEqual(self.m.db.execute('SELECT payload FROM agent_episodes').fetchone()[0],'preserve original conversation')
        self.assertEqual(self.m.db.execute('SELECT count(*) FROM agent_vectors').fetchone()[0],0)
        self.assertEqual(self.m.db.execute("SELECT count(*) FROM events WHERE event_type='derived_index_rebuilt'").fetchone()[0],1)

    def test_rebuild_recovers_internal_fts_corruption(self):
        self.put()
        self.mutate('DELETE FROM search_data WHERE id>10')
        self.assertFalse(self.m.verify()['ok'])
        self.m.rebuild_indexes()
        self.assertTrue(self.m.verify()['ok'])

    def test_rebuild_failure_rolls_back_chunks_fts_and_vectors(self):
        self.put()
        self.add_derivatives_and_episode()
        self.mutate("UPDATE chunks SET text='tampered'")
        before = self.m.db.execute('SELECT * FROM chunks').fetchall()
        with patch.object(self.m, 'validate_version', side_effect=RuntimeError('injected rebuild failure')):
            with self.assertRaises(RuntimeError):self.m.rebuild_indexes()
        self.assertEqual([tuple(r) for r in self.m.db.execute('SELECT * FROM chunks')], [tuple(r) for r in before])
        self.assertEqual(self.m.db.execute('SELECT count(*) FROM agent_vectors').fetchone()[0],1)
        self.assertEqual(self.m.db.execute('SELECT count(*) FROM search').fetchone()[0],1)

    def test_backup_rejects_corrupted_derived_rows(self):
        self.put()
        self.mutate("UPDATE chunks SET text='tampered'")
        with self.assertRaises(MemoryError):self.m.backup(self.root/'snapshot')
        self.assertFalse((self.root/'snapshot').exists())

    def test_restore_rejects_corrupt_indexes_even_with_recomputed_manifest(self):
        self.put(); self.m.backup(self.root/'snapshot')
        dbpath=self.root/'snapshot/memory.sqlite'
        db=sqlite3.connect(dbpath)
        db.execute("UPDATE chunks SET text='tampered'");db.commit();db.close()
        manifest=self.root/'snapshot/snapshot.json'
        data=json.loads(manifest.read_text(encoding='utf-8'))
        for row in data['files']:
            if row['path']=='memory.sqlite':
                row['bytes']=dbpath.stat().st_size
                row['sha256']=hashlib.sha256(dbpath.read_bytes()).hexdigest()
        manifest.write_text(canonical(data),encoding='utf-8')
        with self.assertRaises(MemoryError):Memory.restore(self.root/'snapshot',self.root/'restored')
        self.assertFalse((self.root/'restored').exists())

    def test_readonly_verify_never_executes_a_write_on_source_connection(self):
        self.put()
        with Memory(self.m.state,readonly=True) as reader:
            statements=[];reader.db.set_trace_callback(statements.append)
            self.assertTrue(reader.verify()['ok'])
            self.assertFalse(any(s.lstrip().upper().startswith(('INSERT','UPDATE','DELETE','CREATE','DROP')) for s in statements))
            self.assertEqual(reader.db.execute('PRAGMA query_only').fetchone()[0],1)
            with self.assertRaises(MemoryError):reader.rebuild_indexes()

    def test_pending_write_is_not_silently_committed_by_verify_or_backup(self):
        self.put()
        self.m.db.execute("UPDATE chunks SET text='pending'")
        self.assertIn('verification_requires_committed_state',self.m.verify()['issues'])
        with self.assertRaises(MemoryError):self.m.backup(self.root/'snapshot')
        self.assertTrue(self.m.db.in_transaction)
        self.m.db.rollback()
        self.assertTrue(self.m.verify()['ok'])

    def cli(self, *args, state=None):
        return subprocess.run([sys.executable,'-X','utf8','-m','bojart_memory','--state',
                               str(state or self.m.state),*args],
                              cwd=Path(__file__).resolve().parents[1],
                              capture_output=True,text=True,encoding='utf-8',timeout=15)

    def test_cli_verify_is_readonly_and_explicit_repair_succeeds(self):
        item=self.put()
        self.mutate("UPDATE chunks SET text='tampered'")
        refused=self.cli('verify')
        self.assertNotEqual(refused.returncode,0)
        self.assertEqual(self.m.db.execute('SELECT text FROM chunks').fetchone()[0],'tampered')
        repaired=self.cli('verify','--repair-index')
        self.assertEqual(repaired.returncode,0,repaired.stderr)
        result=json.loads(repaired.stdout)
        self.assertTrue(result['ok']);self.assertTrue(result['repair']['originals_preserved'])
        self.assertEqual(self.m._object(item['sha256']).read_text(encoding='utf-8'),'Source fidèle.\nJev reste un décideur texte.')

    def test_cli_repair_alias_and_no_creation_on_missing_state(self):
        self.put()
        repaired=self.cli('repair-index')
        self.assertEqual(repaired.returncode,0,repaired.stderr)
        missing=self.root/'missing'
        refused=self.cli('repair-index',state=missing)
        self.assertNotEqual(refused.returncode,0)
        self.assertFalse(missing.exists())

    def test_cli_repair_does_not_guess_unknown_metadata(self):
        self.put()
        self.mutate("UPDATE versions SET extraction='unknown_v999'")
        result=self.cli('repair-index')
        self.assertNotEqual(result.returncode,0)
        self.assertEqual(self.m.db.execute('SELECT extraction FROM versions').fetchone()[0],'unknown_v999')


if __name__ == '__main__':
    unittest.main()
