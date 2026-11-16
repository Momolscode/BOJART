import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from bojart_ops.preinstallation import build, catalog, local_file, preparation_status, read_json, records, research_search
from bojart_memory.agent import AgentMemory
from bojart_memory.core import Memory
from bojart_memory.mcp import Protocol


class PreparationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.root = self.base / 'repo'
        self.root.mkdir()
        self.card = 'docs/knowledge.txt'
        self.write(self.card, 'Télémétrie Moonraker inconnue après timeout.\n')
        self.book('requirements.json', 'requirements', [{'id': 'voice', 'title': 'voix française'}])
        self.book('tool-registry.json', 'tools', [{'id': 'moonraker', 'name': 'Moonraker', 'status': 'candidate', 'command': 'DO NOT EXECUTE'}])
        self.book('sources-curated.json', 'sources', [{'id': 'official'}])
        self.book('knowledge-cards.json', 'cards', [{'id': 'card', 'path': self.card, 'sha256': hashlib.sha256((self.root/self.card).read_bytes()).hexdigest()}])
        self.book('retrieval-cases.json', 'cases', [{'id': 'e1', 'question': 'Moonraker timeout', 'expected_sources': [self.card]}])
        self.json('data/preinstallation/target-profile.json', {'schema_version': 1, 'target_qualified': False})
        self.json('data/preinstallation/target-inventory.template.json', {'schema_version': 1})
        self.json('data/knowledge/index.json', [{'path': self.card, 'project': 'bojart.jarvis', 'provenance': 'test fixture'}])
        self.json('jarvis/knowledge/metier/data/registres_a_renseigner.json', {})
        self.json('jarvis/apps/jarvis/config.example.json', {})

    def write(self, relative, content):
        path = self.root/relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding='utf-8')

    def json(self, relative, value):
        self.write(relative, json.dumps(value))

    def book(self, name, key, rows):
        self.json('data/preinstallation/'+name, {'schema_version': 1, key: rows})

    def test_catalog_is_description_not_execution(self):
        with patch('subprocess.run', side_effect=AssertionError('No subprocess')):
            result = catalog('tools', 'Moonraker', root=self.root)
        self.assertEqual(result['results'][0]['status'], 'candidate')
        self.assertFalse(result['operational_authority'])
        self.assertEqual(result['tools_executed'], 0)

    def test_invalid_catalog_parameters_are_refused(self):
        for kind, query, limit in [('shell', '', 1), ('tools', 'x'*2001, 1), ('tools', '', True), ('tools', '', 101)]:
            with self.subTest(kind=kind, limit=limit), self.assertRaises(ValueError):
                catalog(kind, query, root=self.root, limit=limit)

    def test_unsafe_source_paths_are_refused(self):
        for name in ['../outside', '/absolute', 'C:/secret', 'x:stream', 'docs\\knowledge.txt']:
            with self.subTest(path=name), self.assertRaises(ValueError):
                local_file(self.root, name)

    def test_duplicate_json_keys_are_refused(self):
        self.write('bad.json', '{"a":1,"a":2}')
        with self.assertRaisesRegex(ValueError, 'Duplicate'):
            read_json(self.root, 'bad.json')

    def test_duplicate_registry_ids_are_refused(self):
        self.book('tool-registry.json', 'tools', [{'id': 'x'}, {'id': 'x'}])
        with self.assertRaises(ValueError):
            records(self.root, 'tool-registry.json', 'tools')

    def test_modified_knowledge_card_blocks_preparation(self):
        self.write(self.card, 'Different source')
        with self.assertRaisesRegex(ValueError, 'changed'):
            preparation_status(self.root)

    def test_malformed_card_is_a_validation_error(self):
        for card in [{'id': 'x'}, {'id': 'x', 'path': self.card, 'sha256': None}]:
            self.book('knowledge-cards.json', 'cards', [card])
            with self.assertRaises(ValueError):
                preparation_status(self.root)

    def test_existing_destination_is_preserved(self):
        destination = self.base/'existing'
        destination.mkdir()
        marker = destination/'keep.txt'
        marker.write_text('keep')
        with self.assertRaises(ValueError):
            build(destination, root=self.root)
        self.assertEqual(marker.read_text(), 'keep')

    def test_malformed_tool_status_is_a_validation_error(self):
        self.book('tool-registry.json', 'tools', [{'id': 'x', 'status': {}}])
        with self.assertRaisesRegex(ValueError, 'status'):
            preparation_status(self.root)

    def test_destination_inside_checkout_is_refused(self):
        with self.assertRaises(ValueError):
            build(self.root/'output', root=self.root)
        self.assertFalse((self.root/'output').exists())

    def test_failed_restore_does_not_publish_partial_bundle(self):
        destination = self.base/'failed'
        with patch.object(Memory, 'restore', side_effect=ValueError('restore fixture error')):
            with self.assertRaises(ValueError):
                build(destination, root=self.root)
        self.assertFalse(destination.exists())
        self.assertEqual(list(self.base.glob('bojart-preparation-*')), [])

    def test_bundle_really_restores_without_models_or_private_episodes(self):
        destination = self.base/'prepared'
        result = build(destination, root=self.root)
        self.assertTrue(result['restore_verified'])
        self.assertEqual(result['retrieval_hits'], 1)
        restored = self.base/'independent'
        Memory.restore(destination/'memory-snapshot', restored)
        service = AgentMemory(restored, repo=self.root)
        self.assertEqual(service.status()['agent_episodes'], 0)
        self.assertFalse(service.status()['chat_configured'])
        self.assertEqual(service.search('Moonraker', 'bojart.jarvis')['results'][0]['source_path'], self.card)
        manifest = json.loads((destination/'manifest.json').read_text('utf-8'))
        for entry in manifest['files']:
            self.assertEqual(hashlib.sha256((destination/entry['path']).read_bytes()).hexdigest(), entry['sha256'])

    def test_mcp_survives_invalid_card_and_valid_read_is_nonmutating(self):
        memory = AgentMemory(self.base/'state', repo=self.root)
        memory.index()
        server = Protocol(memory)
        server.dispatch({'jsonrpc': '2.0', 'id': 1, 'method': 'initialize'})
        server.dispatch({'jsonrpc': '2.0', 'method': 'notifications/initialized'})
        before = memory.status()
        self.book('knowledge-cards.json', 'cards', [{'id': 'missing'}])
        invalid = server.dispatch({'jsonrpc': '2.0', 'id': 2, 'method': 'tools/call', 'params': {'name': 'jarvis_preparation_status', 'arguments': {}}})
        self.assertTrue(invalid['result']['isError'])
        valid = server.dispatch({'jsonrpc': '2.0', 'id': 3, 'method': 'tools/call', 'params': {'name': 'jarvis_tool_catalog', 'arguments': {'query': 'Moonraker'}}})
        self.assertFalse(valid['result']['isError'])
        self.assertEqual(memory.status(), before)

    def test_research_filter_preserves_project_and_default_reference_priority(self):
        self.write('docs/proposal.txt', 'Moonraker proposition spécifique')
        memory = AgentMemory(self.base/'state', repo=self.root)
        memory.index()
        with Memory(memory.state) as db:
            db.ingest_file(self.root/'docs/proposal.txt', root=self.root, project='bojart.jarvis', collection='research', provenance='fixture')
            db.ingest_file(self.root/'docs/proposal.txt', root=self.root, project='bojart.creative', collection='research', provenance='fixture')
        result = research_search(memory.state, 'Moonraker')
        self.assertEqual({r['source_path'] for r in result['results']}, {'docs/proposal.txt'})
        self.assertEqual({r['project'] for r in result['results']}, {'bojart.jarvis'})
        self.assertEqual({r['collection'] for r in result['results']}, {'research'})
        self.assertFalse(result['operational_authority'])
        self.assertEqual(memory.search('Moonraker', 'bojart.jarvis', limit=1)['results'][0]['source_path'], self.card)
        with Memory(memory.state, readonly=True) as db, self.assertRaises(ValueError):
            db.search('Moonraker', project='bojart.jarvis', collection="research' OR 1=1")


if __name__ == '__main__':
    unittest.main()
