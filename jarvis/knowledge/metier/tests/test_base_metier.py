import json,sys,unittest,tempfile,shutil,sqlite3
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'app'))
from base_metier import KnowledgeBase,ROOT,tokens,price_from_cost

class CorpusTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.k=KnowledgeBase()
 def test_counts(self):self.assertEqual((len(self.k.cards),len(self.k.sources),len(self.k.procedures)),(54,38,10))
 def test_every_card_is_nonexecuting(self):self.assertTrue(all(c['execution_authority'] is False and c['site_validated'] is False for c in self.k.cards))
 def test_all_sources_primary(self):self.assertTrue(all(s['kind']=='documentation_primaire' for s in self.k.sources))
 def test_scopes_present(self):self.assertTrue(all(s['scope'] and s['section'] for s in self.k.sources))
 def test_documented_have_sources(self):self.assertTrue(all(c['source_ids'] for c in self.k.cards if c['evidence_level']=='documente'))
 def test_proposed_are_explicit(self):self.assertEqual(sum(c['evidence_level']=='regle_bojart_proposee' for c in self.k.cards),12)
 def test_no_universal_settings(self):self.assertTrue(all(c['universal_machine_settings'] is False for c in self.k.cards))
 def test_procedures_nonautomatic(self):self.assertTrue(all(p['automatic_execution'] is False for p in self.k.procedures))
 def test_unknown_hardware(self):self.assertGreaterEqual(len(self.k.context['unknown']),8)
 def test_budget_preserved(self):self.assertEqual(self.k.context['confirmed_intentions']['computer_budget_eur'],[3000,5000])
 def test_templates_not_actual_data(self):
  t=json.loads((ROOT/'data'/'registres_a_renseigner.json').read_text())
  self.assertIsNone(t['machine']['model']);self.assertIsNone(t['recipe']['layer_height_mm']);self.assertIsNone(t['material']['sku'])
 def test_search_hollow(self):self.assertIn('K23',[r['card']['id'] for r in self.k.search('résine creuse drainage')['items']])
 def test_search_tol(self):self.assertEqual(self.k.search('tolérance jeu assemblage',limit=1)['items'][0]['card']['id'],'K04')
 def test_search_maintenance(self):self.assertEqual(self.k.search('maintenance lubrifiant',limit=1)['items'][0]['card']['id'],'K38')
 def test_search_cost(self):self.assertIn('K45',[r['card']['id'] for r in self.k.search('coût devis')['items']])
 def test_search_identity(self):self.assertIn('K50',[r['card']['id'] for r in self.k.search('character fidélité figurine')['items']])
 def test_domain_filter(self):self.assertTrue(all(x['card']['domain']=='resine' for x in self.k.search('résine',domain='resine')['items']))
 def test_empty_browse(self):self.assertEqual(len(self.k.search('',limit=3)['items']),3)
 def test_no_invention_on_no_match(self):self.assertEqual(self.k.search('zyxwvut987654')['items'],[])
 def test_invalid_domain(self):
  with self.assertRaises(ValueError):self.k.search('résine',domain='invented')
 def test_invalid_limit(self):
  for x in [0,21,True,'2']:
   with self.subTest(x=x),self.assertRaises(ValueError):self.k.search('PLA',limit=x)
 def test_long_query(self):
  with self.assertRaises(ValueError):self.k.search('A'*2001)
 def test_fts_injection(self):
  r=self.k.search("\"; DROP TABLE fiches; -- OR * <script>alert(1)</script>")
  self.assertFalse(r['allowed_to_execute']);self.assertEqual(self.k.con.execute('select count(*) from fiches').fetchone()[0],54)
 def test_overdue_warning(self):self.assertTrue(self.k.search('exposition',as_of='2028-01-01')['items'][0]['review_overdue'])
 def test_current_not_overdue(self):self.assertFalse(self.k.search('exposition',as_of='2026-10-30')['items'][0]['review_overdue'])
 def test_warning_local_qualification(self):self.assertTrue(self.k.search('PLA')['items'][0]['warnings'])
 def test_index_exports_and_no_overwrite(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'index.sqlite';self.k.export_index(p)
   with sqlite3.connect(p) as c:self.assertEqual(c.execute('select count(*) from fiches').fetchone()[0],54)
   with self.assertRaises(FileExistsError):self.k.export_index(p)
 def test_no_automatic_execution_from_search(self):self.assertFalse(self.k.search('Lance la machine')['allowed_to_execute'])
 def test_recipe_empty(self):
  r=self.k.documentation_readiness({},{});self.assertEqual(r['status'],'dossier_incomplet_ou_non_concordant');self.assertFalse(r['allowed_to_execute'])
 def sample_recipe(self):
  r={k:'example' for k in ['id','machine_id','firmware','material_sku','material_version','tooling_id','slicer_version','profile_file','orientation_scope','postprocess_id','test_report','approved_by']}
  r.update(layer_height_mm=0.2,settings_sha256='a'*64,status='qualified',approved_at='2026-10-30');return r
 def test_recipe_matching_not_authorized(self):
  r=self.sample_recipe();s=self.k.documentation_readiness(r,r);self.assertEqual(s['status'],'dossier_declare_complet_a_verifier');self.assertFalse(s['allowed_to_execute'])
 def test_recipe_revision_change(self):
  r=self.sample_recipe();c=r|{'firmware':'different'};s=self.k.documentation_readiness(r,c);self.assertIn('firmware',s['mismatch'])
 def test_recipe_bad_hash(self):
  r=self.sample_recipe();r['settings_sha256']='guess';self.assertIn('empreinte_reglages_invalide',self.k.documentation_readiness(r,r)['invalid'])
 def test_recipe_bad_layer(self):
  r=self.sample_recipe();r['layer_height_mm']=True;self.assertIn('hauteur_couche_invalide',self.k.documentation_readiness(r,r)['invalid'])
 def test_price(self):self.assertEqual(price_from_cost(300,'.30','.03')['price'],'447.76')
 def test_missing_cost_not_zero(self):
  with self.assertRaises(ValueError):price_from_cost(None,.3,.03)
 def test_invalid_price(self):
  for values in [(-1,0,0),(10,.9,.2),(10,float('nan'),0),(10,0,float('inf'))]:
   with self.subTest(values=values),self.assertRaises(ValueError):price_from_cost(*values)
 def test_unknown_nozzle_not_completed(self):
  r=self.sample_recipe();del r['tooling_id'];self.assertIn('tooling_id',self.k.documentation_readiness(r,r)['missing'])
 def test_reject_qualified_corpus(self):
  with tempfile.TemporaryDirectory() as d:
   shutil.copytree(ROOT/'data',Path(d)/'data');p=Path(d)/'data'/'fiches.json';v=json.loads(p.read_text());v[0]['site_validated']=True;p.write_text(json.dumps(v))
   with self.assertRaises(ValueError):KnowledgeBase(d)
 def test_reject_missing_source(self):
  with tempfile.TemporaryDirectory() as d:
   shutil.copytree(ROOT/'data',Path(d)/'data');p=Path(d)/'data'/'fiches.json';v=json.loads(p.read_text());v[0]['source_ids']=['SXX'];p.write_text(json.dumps(v))
   with self.assertRaises(ValueError):KnowledgeBase(d)
 def test_reject_duplicate_source(self):
  with tempfile.TemporaryDirectory() as d:
   shutil.copytree(ROOT/'data',Path(d)/'data');p=Path(d)/'data'/'sources.json';v=json.loads(p.read_text());v.append(v[0]);p.write_text(json.dumps(v))
   with self.assertRaises(ValueError):KnowledgeBase(d)

if __name__=='__main__':unittest.main(verbosity=2)
