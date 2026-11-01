import unittest
from copy import deepcopy
from planner import Calendar, PlanningError, solve, NoSlot
from build_examples import BASE

class PlannerTests(unittest.TestCase):
 def setUp(self): self.cfg=deepcopy(BASE)
 def test_baseline_feasible(self): self.assertEqual(solve(self.cfg)['status'],'PLAN_FOUND')
 def test_no_commands(self): self.assertFalse(solve(self.cfg)['can_execute'])
 def test_no_optimality_claim(self): self.assertFalse(solve(self.cfg)['optimality_claim'])
 def test_no_overlap(self):
  for spans in solve(self.cfg)['reservations'].values():
   spans=sorted(spans,key=lambda x:x['start'])
   for a,b in zip(spans,spans[1:]): self.assertLessEqual(a['end'],b['start'])
 def test_calendar_break(self):
  r=solve(self.cfg)
  for x in r['reservations']['OPERATEUR-1']:
   if not x['blocked']: self.assertTrue(x['end']<=180 or x['start']>=210)
 def test_station_not_double_counted(self):
  r=solve(self.cfg); st=[x for x in r['reservations']['POSTE-LAVAGE-CURE'] if not x['blocked']]
  self.assertEqual(len(st),4)
  for a,b in zip(st,st[1:]): self.assertLessEqual(a['end'],b['start'])
 def test_print_hold_until_unload(self):
  c=deepcopy(BASE); c['resources']['OPERATEUR-1']['blocked']=[[30,200]]
  cal=Calendar(c); end=cal.cycle('FDM-A',0,10,50,10,'A','Print')
  self.assertEqual(end,210); self.assertEqual(cal.reservations['FDM-A'][0]['end'],210)
  self.assertTrue(cal.conflict('FDM-A',100,120))
 def test_fixed_downtime_no_overlap(self):
  c=deepcopy(BASE); c['resources']['FDM-A']['blocked']=[[20,100]]
  cal=Calendar(c); cal.cycle('FDM-A',0,10,50,10,'A','Print')
  reserved=[x for x in cal.reservations['FDM-A'] if not x['blocked']][0]
  self.assertGreaterEqual(reserved['start'],100)
 def test_unavailable_printer(self):
  self.cfg['resources']['RESINE-B']['blocked']=[[0,720]]
  r=solve(self.cfg); self.assertIn(r['status'],['PLAN_FOUND','PLAN_LATE'])
  self.assertTrue(all(x['printer']!='RESINE-B' for x in r['results']))
 def test_missing_compatibility_blocked(self):
  self.cfg['jobs'][1]['eligible']=[]; self.assertEqual(solve(self.cfg)['status'],'BLOCKED')
 def test_wrong_process_rejected(self):
  self.cfg['jobs'][0]['eligible']=['RESINE-A']
  with self.assertRaises(PlanningError): solve(self.cfg)
 def test_no_real_data_permitted(self):
  self.cfg['mode']='production'
  with self.assertRaises(PlanningError): solve(self.cfg)
 def test_negative_duration(self):
  self.cfg['jobs'][0]['print']=-1
  with self.assertRaises(PlanningError): solve(self.cfg)
 def test_bool_not_minutes(self):
  self.cfg['jobs'][0]['print']=True
  with self.assertRaises(PlanningError): solve(self.cfg)
 def test_duplicate_job(self):
  self.cfg['jobs'][1]['id']='SOCLE'
  with self.assertRaises(PlanningError): solve(self.cfg)
 def test_no_operator(self):
  del self.cfg['resources']['OPERATEUR-1']
  with self.assertRaises(PlanningError): solve(self.cfg)
 def test_late_status(self):
  for j in self.cfg['jobs']: j['due']=200
  r=solve(self.cfg); self.assertEqual(r['status'],'PLAN_LATE'); self.assertGreater(r['score']['total_lateness_minutes'],0)
 def test_no_plan_not_infeasibility_proof(self):
  self.cfg['horizon']=30; self.cfg['resources']['OPERATEUR-1']['blocked']=[]
  self.assertEqual(solve(self.cfg)['status'],'NO_PLAN_FOUND')
 def test_precedences(self):
  r=solve(self.cfg)
  for job in self.cfg['jobs']:
   ev=[x for x in r['events'] if x['job']==job['id']]
   ends={x['label']:x['end'] for x in ev}; starts={x['label']:x['start'] for x in ev}
   self.assertGreaterEqual(starts['Finition'],ends['Impression · retrait'])
   self.assertGreaterEqual(starts['Contrôle / conditionnement fictif'],ends['Finition'])
   if job['process']=='resin':
    self.assertGreaterEqual(starts['Lavage · préparation'],ends['Impression · retrait'])
    self.assertGreaterEqual(starts['Cure · préparation'],ends['Délai technique fictif'])
    self.assertGreaterEqual(starts['Finition'],ends['Cure · retrait'])
 def test_input_not_mutated(self):
  before=deepcopy(self.cfg); solve(self.cfg); self.assertEqual(self.cfg,before)
 def test_reproducible(self): self.assertEqual(solve(self.cfg),solve(self.cfg))
 def test_digest_changes(self):
  first=solve(self.cfg)['input_sha256']; self.cfg['jobs'][0]['finish']+=1
  self.assertNotEqual(first,solve(self.cfg)['input_sha256'])

if __name__=='__main__': unittest.main(verbosity=2)
