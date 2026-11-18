"""周中企业合并只改变生效后的主体归属，汇总与旧周报均可复核。"""
import tempfile
import unittest
from pathlib import Path

from capture_service.archive import get, release_verified
from capture_service.collection import collect
from capture_service.ledger import connect
from capture_service.view import overview

ROOT = Path(__file__).resolve().parents[1]


class MergeReconciliation(unittest.TestCase):
    def test_merge_reassigns_only_effective_dates(self):
        with tempfile.TemporaryDirectory() as directory:
            connection = connect(Path(directory) / 'plants.sqlite3')
            collect(connection, 'week', ROOT / 'data' / 'normal.json')
            original = release_verified(connection, 'week')
            before = get(connection, 'week', original)
            collect(connection, 'week', ROOT / 'data' / 'event-pending.json')
            with self.assertRaises(ValueError):
                release_verified(connection, 'week')
            collect(connection, 'week', ROOT / 'data' / 'event-complete.json')
            current = overview(connection, 'week')['slaughter_week']
            self.assertEqual(current['status'], '可核实')
            self.assertEqual(current['actual_heads'], 13300)
            self.assertEqual(current['summary_scope'], ['plant-A', 'plant-B', 'plant-C'])
            self.assertEqual([(row['company_id'], len(row['actual_days']), row['actual_heads'])
                              for row in current['plants']],
                             [('plant-A', 3, 3000), ('plant-B', 3, 2700), ('plant-C', 4, 7600)])
            self.assertEqual([(row['company_id'], len(row['actual_days']))
                              for row in before['slaughter_week']['plants']],
                             [('plant-A', 7), ('plant-B', 7)])
            self.assertEqual(get(connection, 'week', original), before)
            connection.close()
