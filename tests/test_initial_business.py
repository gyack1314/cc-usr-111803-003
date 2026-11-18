"""名录、逐日公告和周报可以形成可发布的初始业务范围。"""
import tempfile
import unittest
from pathlib import Path
from capture_service.ledger import connect
from capture_service.collection import collect
from capture_service.view import overview
from capture_service.archive import release_verified,get

ROOT=Path(__file__).resolve().parents[1]
COLLECTION='111803-003'

class InitialBusinessFlow(unittest.TestCase):
    def test_pair_is_verifiable_and_releasable(self):
        with tempfile.TemporaryDirectory() as directory:
            c=connect(Path(directory)/'service.sqlite3')
            collect(c,COLLECTION,ROOT/'data'/'normal.json')
            state=overview(c,COLLECTION)
            self.assertTrue(state['publishable'])
            self.assertEqual(len(state['matched_pairs']),1)
            self.assertFalse(state['coverage']['missing_required'])
            self.assertEqual(state['slaughter_week']['status'], '可核实')
            self.assertEqual(state['slaughter_week']['actual_heads'], 13300)
            self.assertEqual([(p['company_id'], len(p['actual_days']))
                              for p in state['slaughter_week']['plants']],
                             [('plant-A', 7), ('plant-B', 7)])
            revision=release_verified(c,COLLECTION)
            self.assertEqual(get(c,COLLECTION,revision),state)
            c.close()
