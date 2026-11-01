import dataclasses,importlib.util,json,sqlite3,sys,tempfile,unittest
from pathlib import Path
from decision_gate_demo import Request,Gate,FakeAdapter
script=Path(__file__).parents[1]/'02_Audit_PC/audit_pc_v2.py'
spec=importlib.util.spec_from_file_location('audit_pc',script);audit=importlib.util.module_from_spec(spec);spec.loader.exec_module(audit)

class ProofTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.path=Path(self.tmp.name)/'journal.sqlite';self.g=Gate(self.path)
  self.r=Request('op-1','projet-test',1,'a'*64,'profil-v1','SIM-FDM-1')
  self.c=dataclasses.asdict(self.r)|dict(profile_qualified=True,machine_ready=True,operator_prepared=True,approval_valid=True)
 def tearDown(self):self.g.close();self.tmp.cleanup()
 def test_01_valid_simulated_ack(self):
  a=FakeAdapter();self.assertEqual(self.g.execute(self.r,self.c,a),'SIMULATED_ACK');self.assertEqual(a.calls,1)
 def test_02_duplicate_not_resent(self):
  a=FakeAdapter();self.g.execute(self.r,self.c,a);self.g.execute(self.r,self.c,a);self.assertEqual(a.calls,1)
 def test_03_duplicate_after_restart_not_resent(self):
  a=FakeAdapter();self.g.execute(self.r,self.c,a);self.g.close();self.g=Gate(self.path);self.g.execute(self.r,self.c,a);self.assertEqual(a.calls,1)
 def test_04_unknown_not_resent(self):
  a=FakeAdapter(True);self.assertEqual(self.g.execute(self.r,self.c,a),'UNKNOWN');self.g.execute(self.r,self.c,a);self.assertEqual(a.calls,1)
 def test_05_unknown_blocks_new_key(self):
  a=FakeAdapter(True);self.g.execute(self.r,self.c,a)
  with self.assertRaises(ValueError):self.g.execute(dataclasses.replace(self.r,operation_id='op-2'),self.c,a)
  self.assertEqual(a.calls,1)
 def test_06_stale_project(self):
  with self.assertRaises(ValueError):self.g.execute(self.r,self.c|{'project_id':'other'},FakeAdapter())
 def test_07_stale_revision(self):
  with self.assertRaises(ValueError):self.g.execute(self.r,self.c|{'revision':2},FakeAdapter())
 def test_08_changed_file(self):
  with self.assertRaises(ValueError):self.g.execute(self.r,self.c|{'artifact_sha256':'b'*64},FakeAdapter())
 def test_09_changed_profile(self):
  with self.assertRaises(ValueError):self.g.execute(self.r,self.c|{'profile_revision':'v2'},FakeAdapter())
 def test_10_wrong_machine(self):
  with self.assertRaises(ValueError):self.g.execute(self.r,self.c|{'machine_id':'SIM-2'},FakeAdapter())
 def test_11_unprepared_bed(self):
  with self.assertRaises(ValueError):self.g.execute(self.r,self.c|{'operator_prepared':False},FakeAdapter())
 def test_12_missing_approval(self):
  with self.assertRaises(ValueError):self.g.execute(self.r,self.c|{'approval_valid':False},FakeAdapter())
 def test_13_unknown_machine_state(self):
  with self.assertRaises(ValueError):self.g.execute(self.r,self.c|{'machine_ready':None},FakeAdapter())
 def test_14_unqualified_profile(self):
  with self.assertRaises(ValueError):self.g.execute(self.r,self.c|{'profile_qualified':False},FakeAdapter())
 def test_15_reused_id_different_content(self):
  self.g.execute(self.r,self.c,FakeAdapter())
  with self.assertRaises(ValueError):self.g.execute(dataclasses.replace(self.r,revision=2),self.c|{'revision':2},FakeAdapter())
 def test_16_unlisted_action(self):
  with self.assertRaises(ValueError):self.g.execute(dataclasses.replace(self.r,action='shell_command'),self.c,FakeAdapter())
 def test_17_persisted_dispatching_blocks_replay(self):
  from decision_gate_demo import fingerprint
  self.g.db.execute('INSERT INTO jobs VALUES(?,?,?,?)',(self.r.operation_id,fingerprint(self.r),self.r.machine_id,'DISPATCHING'));self.g.db.commit()
  a=FakeAdapter();self.assertEqual(self.g.execute(self.r,self.c,a),'DISPATCHING');self.assertEqual(a.calls,0)
 def test_18_nvidia_parser(self):
  self.assertEqual(audit.parse_nvidia('Demo GPU, 24576, 000.0')[0]['dedicated_vram_mib'],24576)
 def test_19_bad_vram_not_guessed(self):self.assertEqual(audit.parse_nvidia('Demo, N/A, 000.0'),[])
 def test_20_memory_parser(self):self.assertEqual(audit.parse_meminfo('MemTotal: 16777216 kB')['total_gib'],16)
 def test_21_missing_tool(self):self.assertEqual(audit.probe(['bojart_unavailable_command'])['status'],'unavailable')
 def test_22_sqlite_restore_snapshot(self):
  a=FakeAdapter();self.g.execute(self.r,self.c,a)
  p=Path(self.tmp.name)/'restored.sqlite';db=sqlite3.connect(p);self.g.db.backup(db);db.close();restored=Gate(p)
  try:self.assertEqual(restored.execute(self.r,self.c,a),'SIMULATED_ACK');self.assertEqual(a.calls,1)
  finally:restored.close()

if __name__=='__main__':
 suite=unittest.defaultTestLoader.loadTestsFromTestCase(ProofTests)
 result=unittest.TextTestRunner(verbosity=2).run(suite)
 report={'scope':'isolated simulation in generation environment; not V11 nor target PC','tests':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),'status':'passed' if result.wasSuccessful() else 'failed','no_real_printer_or_llm':True}
 (Path(__file__).parent/'RESULTATS_TESTS.json').write_text(json.dumps(report,indent=2,ensure_ascii=False))
 sys.exit(not result.wasSuccessful())
