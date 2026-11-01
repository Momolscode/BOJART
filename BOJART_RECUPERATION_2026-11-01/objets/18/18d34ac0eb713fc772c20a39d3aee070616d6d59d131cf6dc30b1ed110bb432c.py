import json, unittest
from pathlib import Path
R=Path(__file__).resolve().parents[1]
D=R/'research/readiness-2026-10-30'
class ResearchTests(unittest.TestCase):
 def load(self,n):return json.loads((D/n).read_text(encoding='utf8'))
 def test_sources(self):
  s=self.load('SOURCES.json')['sources'];self.assertEqual(len(s),13)
  self.assertEqual(len({x['id'] for x in s}),len(s))
  self.assertTrue(all(x['url'].startswith('https://') and x['type']=='primary' for x in s))
 def test_cards(self):
  cards=self.load('FICHES_ENRICHISSEMENT.json')['cards'];self.assertEqual(len(cards),8)
  ids={x['id'] for x in self.load('SOURCES.json')['sources']}
  for c in cards:
   self.assertTrue(set(c['sources'])<=ids);self.assertTrue(c['not_done']);self.assertTrue(c['acceptance'])
 def test_cases_not_misrepresented(self):
  c=self.load('RECETTE_FR_36_CAS.json')['cases'];self.assertEqual(len(c),36)
  self.assertEqual(len({x['id'] for x in c}),36)
  self.assertTrue(all(x['execution_status']=='not_run_on_target' for x in c))
 def test_cases_cover_six_domains(self):
  c=self.load('RECETTE_FR_36_CAS.json')['cases']
  self.assertEqual({x['family'] for x in c},{'VOC','CAD','FAB','STU','COM','SYS'})
  self.assertTrue(all(sum(x['family']==f for x in c)==6 for f in ['VOC','CAD','FAB','STU','COM','SYS']))
 def test_no_stale_destination_in_active_context(self):
  for p in [R/'context/START_HERE.md',R/'docs/TRANSFER_GITHUB.md']:
   self.assertNotIn('non choisie entre',p.read_text());self.assertIn('Momolscode/bojart-jarvis',p.read_text())
 def test_destination_decision(self):
  d=json.loads((R/'context/DECISIONS.json').read_text());g=next(x for x in d['decisions'] if x['id']=='github')
  self.assertEqual(g['status'],'user_constraint');self.assertIn('Momolscode/bojart-jarvis',g['value'])
 def test_local_module_still_honest(self):
  t=(R/'apps/jarvis/app/consolidated_workbench.py').read_text()
  self.assertIn("'screen_pairing':'browser_tabs_local_only'",t);self.assertIn("'physical_commands':False",t)
 def test_no_material_capability_promised(self):
  self.assertIn('Aucune détection vision ni commande',self.load('FICHES_ENRICHISSEMENT.json')['cards'][2]['not_done'])
if __name__=='__main__':unittest.main()
