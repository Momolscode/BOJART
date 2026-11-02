import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'app'))
from base_metier import KnowledgeBase


class ExportLifetimeTests(unittest.TestCase):
    def test_export_closes_the_destination_on_success_and_failure(self):
        real_connect = sqlite3.connect
        for fails in (False, True):
            with self.subTest(fails=fails), tempfile.TemporaryDirectory() as td:
                kb = KnowledgeBase()
                source = kb.con
                opened = []
                def connect(*args, **kwargs):
                    con = real_connect(*args, **kwargs)
                    opened.append(con)
                    return con
                class BrokenSource:
                    def backup(self, _target): raise RuntimeError('controlled backup failure')
                try:
                    if fails: kb.con = BrokenSource()
                    with patch('base_metier.sqlite3.connect', side_effect=connect):
                        if fails:
                            with self.assertRaisesRegex(RuntimeError, 'controlled'):
                                kb.export_index(Path(td)/'export.sqlite')
                        else: kb.export_index(Path(td)/'export.sqlite')
                    self.assertEqual(len(opened), 1)
                    # Holding this reference avoids a false success caused by garbage collection.
                    with self.assertRaises(sqlite3.ProgrammingError):
                        opened[0].execute('SELECT 1')
                finally:
                    for con in opened: con.close()
                    source.close()


if __name__ == '__main__': unittest.main()
