"""Cross-layer reception: fake model, exact source corruption, real HTTP elsewhere."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from bojart_memory.agent import AgentMemory
from bojart_memory.core import Memory, MemoryError, canonical
from bojart_memory.conversation import select_exchanges

J='bojart.jarvis'
C='bojart.creative'

class Embed:
    calls=0
    def key(self): return 'fixture'
    def embed(self, texts):
        self.calls+=1
        return [[1.,0.] for _ in texts]

class HardeningIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(); self.root=Path(self.temp.name)
        self.agent=AgentMemory(self.root/'state')
        self.doc=self.root/'reference.txt'; self.doc.write_text('Mémoire persistante documentée.',encoding='utf-8')
        with Memory(self.agent.state) as m:
            self.version=m.ingest_file(self.doc,root=self.root,project=J,collection='canonical',provenance='fixture')
    def tearDown(self): self.temp.cleanup()
    def corrupt(self):
        with Memory(self.agent.state) as m,m.db:
            m.db.execute("UPDATE chunks SET text='mensonge coordonné'")
            m.db.execute("UPDATE search SET text='mensonge coordonné'")
    def test_semantic_path_excludes_coordinated_excerpt_tamper(self):
        self.agent.embed(Embed()); self.corrupt()
        r=self.agent.search('synonyme absent',J,embedder=Embed())
        self.assertEqual(r['results'],[])
        self.assertEqual(len(r['warnings']),1)
        self.assertEqual(r['warnings'][0]['reason'],'derived_excerpt_inconsistent')
    def test_embedding_never_sends_already_corrupt_excerpt(self):
        self.corrupt(); fake=Embed()
        with self.assertRaises(MemoryError): self.agent.embed(fake)
        self.assertEqual(fake.calls,0)
    def test_mutation_during_embedding_cannot_commit_stale_vector(self):
        agent=self.agent; root=self.root; doc=self.doc
        class Changing(Embed):
            def embed(self,texts):
                doc.write_text('Nouvelle version du document.',encoding='utf-8')
                with Memory(agent.state) as m:
                    m.ingest_file(doc,root=root,project=J,collection='canonical',provenance='fixture')
                return super().embed(texts)
        with self.assertRaises(MemoryError): self.agent.embed(Changing())
        with Memory(self.agent.state) as m:
            self.assertEqual(m.db.execute('SELECT count(*) FROM agent_vectors').fetchone()[0],0)
    def test_history_withholds_answer_after_derived_excerpt_corruption(self):
        pack=self.agent.context('persistante',J)
        self.assertTrue(pack['evidence'][0]['excerpt_matches_source'])
        self.agent.episode('old','session',J,{'question':'persistante','context':pack,'response':{'answer':'réponse'}})
        self.corrupt()
        with Memory(self.agent.state,readonly=True) as m:
            history=select_exchanges(m,session='session',project=J,facts=[])
        self.assertNotIn('answer',history[0]);self.assertEqual(history[0]['answer_status'],'withheld_excerpts_changed')
    def test_foreign_supersession_does_not_remove_project_fact(self):
        ledger=self.root/'data/knowledge/claims.jsonl';ledger.parent.mkdir(parents=True)
        a={'claim_id':'own','project':J,'subject':'gpu','predicate':'model','value':'4060 Ti','status':'user_decision','sources':['fixture'],'observed_on':'2026-11-02'}
        b={**a,'claim_id':'foreign','project':C,'supersedes':['own'],'value':'other'}
        ledger.write_text(canonical(a)+'\n'+canonical(b)+'\n',encoding='utf-8')
        with Memory(self.agent.state) as m:
            for project in (J,C):m.ingest_file(ledger,root=self.root,project=project,collection='canonical',provenance='fixture')
        self.assertEqual([f['id'] for f in self.agent.facts(J)],['claim-own'])
        with Memory(self.agent.state) as m:
            for project in (J,C):
                rows=m.search('gpu',project=project)['results']
                for row in rows:
                    if row['source_path']== 'data/knowledge/claims.jsonl':
                        self.assertEqual(json.loads(row['text'])['project'],project)
    def test_repair_restores_search_and_backup_without_modifying_original(self):
        with Memory(self.agent.state) as m:original=m._object(self.version['sha256']).read_bytes()
        self.corrupt()
        with Memory(self.agent.state) as m:
            self.assertFalse(m.verify()['ok']);m.rebuild_indexes();self.assertTrue(m.verify()['ok'])
            self.assertEqual(m._object(self.version['sha256']).read_bytes(),original)
            m.backup(self.root/'snapshot')
        Memory.restore(self.root/'snapshot',self.root/'restored')
        restored=AgentMemory(self.root/'restored')
        self.assertEqual(restored.search('persistante',J)['results'][0]['text'],self.doc.read_text('utf-8'))

if __name__=='__main__':unittest.main()
