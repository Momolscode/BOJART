import gc, sqlite3, sys, tempfile, unittest, warnings
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'apps/jarvis/app'))
from core import Store, verify_backup
from display_contracts import DisplayProposals

class ConnectionLifetimeTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.store=Store(self.temp.name)
 def tearDown(self):self.temp.cleanup()
 def test_store_closes_after_success(self):
  with self.store.connect() as con:self.assertEqual(con.execute('SELECT 1').fetchone()[0],1)
  with self.assertRaises(sqlite3.ProgrammingError):con.execute('SELECT 1')
 def test_store_commits(self):
  with self.store.connect() as con:con.execute("INSERT INTO projects VALUES ('TEST',1)")
  self.assertEqual(self.store.project_revision('TEST'),1)
 def test_store_rolls_back_and_closes(self):
  con=None
  with self.assertRaisesRegex(RuntimeError,'forced'):
   with self.store.connect() as con:
    con.execute("INSERT INTO projects VALUES ('TEST',5)");raise RuntimeError('forced')
  self.assertEqual(self.store.project_revision('TEST'),0)
  with self.assertRaises(sqlite3.ProgrammingError):con.execute('SELECT 1')
 def test_display_closes(self):
  book=DisplayProposals(self.store)
  with book.db() as con:self.assertEqual(con.execute('SELECT 2').fetchone()[0],2)
  with self.assertRaises(sqlite3.ProgrammingError):con.execute('SELECT 1')
 def test_display_rolls_back_and_closes(self):
  book=DisplayProposals(self.store)
  with self.assertRaises(ValueError):
   with book.db() as con:
    con.execute("INSERT INTO proposals VALUES ('x','x','{}')");raise ValueError('forced')
  with book.db() as read:self.assertEqual(read.execute('SELECT count(*) FROM proposals').fetchone()[0],0)
  with self.assertRaises(sqlite3.ProgrammingError):con.execute('SELECT 1')
 def test_empty_backup_still_verifies(self):
  p=Path(self.temp.name)/'backup.zip';self.store.backup(p)
  self.assertTrue(verify_backup(p)['ok'])
 def test_repeated_connections_do_not_emit_resource_warning(self):
  gc.collect()
  with warnings.catch_warnings(record=True) as caught:
   warnings.simplefilter('always',ResourceWarning)
   book=DisplayProposals(self.store)
   for _ in range(50):
    self.store.project_revision()
    with book.db() as con:con.execute('SELECT 1').fetchone()
   gc.collect()
  self.assertEqual([str(w.message) for w in caught if issubclass(w.category,ResourceWarning)],[])
if __name__=='__main__':unittest.main()
