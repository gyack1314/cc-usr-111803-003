"""分页日报接续成周、重叠页去重、单日更正传播与已发布视图回查。"""
import tempfile
import unittest
from pathlib import Path

from capture_service.archive import get, release_verified
from capture_service.collection import collect, coverage
from capture_service.ledger import connect
from capture_service.view import overview

ROOT = Path(__file__).resolve().parents[1]
COLLECTION = '111803-003'


class PagedReconciliation(unittest.TestCase):
    def test_pages_merge_then_single_day_correction_propagates(self):
        with tempfile.TemporaryDirectory() as directory:
            connection = connect(Path(directory) / 'week.sqlite3')

            # 名录 v2 与周一至周四页先到：周五至周日缺失，不能按零计入，也不能发布。
            collect(connection, COLLECTION, ROOT / 'data' / 'fragments-page1.json')
            pending = overview(connection, COLLECTION)['slaughter_week']
            self.assertEqual(pending['status'], '覆盖或汇总待核')
            self.assertEqual(pending['missing_days'], ['2026-11-13', '2026-11-14', '2026-11-15'])
            self.assertEqual(pending['actual_heads'], 7600)
            self.assertEqual([(row['company_id'], len(row['actual_days']), row['actual_heads'])
                              for row in pending['plants']],
                             [('plant-A', 3, 3000), ('plant-B', 3, 2700), ('plant-C', 1, 1900)])
            self.assertEqual(pending['estimate_heads'], 0)
            self.assertEqual(coverage(connection, COLLECTION)['missing_required'],
                             ['https://local-source-003.example.test/records/daily_slaughter-C'])
            with self.assertRaises(ValueError):
                release_verified(connection, COLLECTION)

            # 周四至周日页到达：周四重叠记录只计一次，整周 13,300 头可核实并发布。
            collect(connection, COLLECTION, ROOT / 'data' / 'fragments-page2.json')
            complete = overview(connection, COLLECTION)['slaughter_week']
            self.assertEqual(complete['status'], '可核实')
            self.assertEqual(complete['missing_days'], [])
            self.assertEqual(complete['actual_heads'], 13300)
            self.assertEqual(complete['summary_heads'], 13300)
            self.assertEqual([(row['company_id'], len(row['actual_days']), row['actual_heads'])
                              for row in complete['plants']],
                             [('plant-A', 3, 3000), ('plant-B', 3, 2700), ('plant-C', 4, 7600)])
            original = release_verified(connection, COLLECTION)
            published = get(connection, COLLECTION, original)

            # 周三甲厂记录由 1000 修订为 950：只替代该日旧记录，合计 13,250 头。
            collect(connection, COLLECTION, ROOT / 'data' / 'fragments-corrected.json')
            revised = overview(connection, COLLECTION)['slaughter_week']
            self.assertEqual(revised['status'], '可核实')
            self.assertEqual(revised['actual_heads'], 13250)
            self.assertEqual(revised['summary_heads'], 13250)
            self.assertEqual([(row['company_id'], len(row['actual_days']), row['actual_heads'])
                              for row in revised['plants']],
                             [('plant-A', 3, 2950), ('plant-B', 3, 2700), ('plant-C', 4, 7600)])
            self.assertFalse(coverage(connection, COLLECTION)['stale_required'])
            correction = release_verified(connection, COLLECTION)

            # 已发布的 13,300 头视图保留原依据；新视图反映修订后的记录与来源范围。
            self.assertEqual(get(connection, COLLECTION, original), published)
            self.assertEqual(published['slaughter_week']['actual_heads'], 13300)
            self.assertEqual(published['slaughter_week']['summary_scope'],
                             ['plant-A', 'plant-B', 'plant-C'])
            current_view = get(connection, COLLECTION, correction)
            self.assertEqual(current_view['slaughter_week']['actual_heads'], 13250)
            self.assertEqual(current_view['slaughter_week']['summary_scope'],
                             ['plant-A', 'plant-B', 'plant-C'])
            connection.close()
