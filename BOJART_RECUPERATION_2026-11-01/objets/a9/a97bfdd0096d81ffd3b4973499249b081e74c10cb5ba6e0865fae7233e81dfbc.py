import unittest
from import_owner_insights import normalize


class MetricsTests(unittest.TestCase):
    def test_units_and_watch_ratio_above_100_are_not_completion(self):
        p = {'status': 'available', 'accessLevel': 'owner', 'reels': [
            {'reelId': 'synthetic-unit-test', 'durationSeconds': 10,
             'avgWatchTimeMs': 12000, 'playCount': 0, 'shares': None, 'skipRate': .2}]}
        r = normalize(p)['reels'][0]
        self.assertEqual(r['mean_watch_time_s'], 12)
        self.assertEqual(r['mean_watch_ratio_pct'], 120)
        self.assertIsNone(r['completion_rate'])
        self.assertEqual(r['plays'], 0)
        self.assertIsNone(r['shares'])
        self.assertFalse(r['skip_rate_unit_verified'])

    def test_zero_duration_and_missing_values_remain_unknown(self):
        r = normalize({'status': 'available', 'accessLevel': 'owner',
                       'reels': [{'durationSeconds': 0, 'avgWatchTimeMs': 0}]})['reels'][0]
        self.assertIsNone(r['mean_watch_ratio_pct'])
        self.assertEqual(r['mean_watch_time_s'], 0)

    def test_unavailable_and_public_fallback_do_not_turn_into_owner_data(self):
        for p in [{'status': 'unavailable'}, {'status': 'available', 'accessLevel': 'public_fallback'}]:
            with self.assertRaises(ValueError):
                normalize(p)

    def test_nested_response_can_be_imported_without_inventing_window(self):
        p = {'structuredContent': {'structuredContent': {'status': 'available', 'accessLevel': 'owner', 'reels': []}}}
        r = normalize(p)
        self.assertEqual(r['reels'], [])
        self.assertIsNone(r['window'])


if __name__ == '__main__':
    unittest.main()
