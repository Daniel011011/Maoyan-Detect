import json
from pathlib import Path
import tempfile
import unittest
from datetime import datetime
from unittest.mock import patch
import cinema_monitor as m


def payload(cinema, slots=None, movie='测试影片'):
    hall = '5号杜比影院' if cinema['id'] == '24311' else '7号IMAX激光厅'
    return {'showData': {'cinemaId': cinema['id'], 'movies': [
        {'id': 42, 'nm': movie, 'dur': 181, 'shows': [
            {'showDate': '2099-01-03', 'plist': [
                {'th': hall, 'tm': t, 'dt': '2099-01-03', 'enterShowSeat': 1} for t in (slots if slots is not None else ['12:00'])
            ]}
        ]}
    ]}}


class MonitorTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.state = self.root / 'state.json'
        self.calls = []

    def sender(self, *args):
        self.calls.append(args)

    def run_check(self, fetcher=payload, **kwargs):
        return m.check_once(self.state, self.root, 'fake-key', fetcher=fetcher, sender=kwargs.pop('sender', self.sender), **kwargs)

    def test_strict_halls(self):
        dolby, imax = m.CINEMAS
        self.assertTrue(m.matches_hall(dolby, '5号杜比影院'))
        self.assertTrue(m.matches_hall(dolby, 'Dolby Cinema'))
        self.assertFalse(m.matches_hall(dolby, 'PRIME杜比全景声厅'))
        self.assertTrue(m.matches_hall(imax, '7号激光ＩＭＡＸ厅'))
        self.assertTrue(m.matches_hall(imax, 'IMAX Laser'))
        for hall in ['IMAX厅', '3号激光厅', '杜比影院']:
            self.assertFalse(m.matches_hall(imax, hall))

    def test_baseline_addition_removal_and_restart(self):
        self.assertTrue(self.run_check())
        self.assertEqual(self.calls, [])
        self.assertTrue(self.run_check(lambda c: payload(c, ['12:00', '16:00'])))
        self.assertEqual(len(self.calls), 2)
        self.assertTrue(all(call[2][0]['time'] == '16:00' for call in self.calls))
        self.assertTrue(all(call[3] is False for call in self.calls))
        self.run_check(lambda c: payload(c, ['16:00']))
        self.run_check(lambda c: payload(c, ['12:00', '16:00']))
        self.assertEqual(len(self.calls), 2)

    def test_new_date_and_chinese_notification(self):
        self.run_check()
        def next_day(c):
            data = payload(c)
            group = data['showData']['movies'][0]['shows'][0]
            group['showDate'] = '2099-01-04'
            group['plist'][0]['dt'] = '2099-01-04'
            return data
        self.run_check(next_day)
        self.assertTrue(all(call[3] for call in self.calls))
        with patch.object(m, 'request_json', return_value={'code': 200}) as request:
            m.notify(*self.calls[0])
            body = request.call_args.args[1]['body']
            self.assertIn('2099年01月04日（周日）', body)
            self.assertIn('12:00', body)
            self.assertIn('测试影片', body)

    def test_initial_saturday_avengers(self):
        self.run_check(lambda c: payload(c, movie='复仇者联盟4：终局之战'))
        self.assertEqual(len(self.calls), 2)
        self.assertTrue(m.special(self.calls[0][2][0]))
        self.run_check(lambda c: payload(c, movie='复仇者联盟4：终局之战'))
        self.assertEqual(len(self.calls), 2)

    def test_failed_push_retries_persisted_queue(self):
        self.run_check()
        def broken(*args):
            raise TimeoutError('fake')
        changed = lambda c: payload(c, ['12:00', '18:00'])
        self.assertFalse(self.run_check(changed, sender=broken))
        self.assertEqual(len(m.read_state(self.state)['cinemas']['24311']['pending']), 1)
        self.assertTrue(self.run_check(changed))
        self.assertEqual(len(self.calls), 2)
        self.assertEqual(m.read_state(self.state)['cinemas']['24311']['pending'], {})
        self.run_check(changed)
        self.assertEqual(len(self.calls), 2)

    def test_partial_failure_preserves_other_cinema_and_cache(self):
        self.run_check()
        def partial(c):
            if c['id'] == '24311':
                return {'verify': True}
            return payload(c, ['12:00', '16:00'])
        self.assertFalse(self.run_check(partial))
        public = json.loads((self.root / 'schedules.json').read_text(encoding='utf-8'))
        self.assertEqual(len(public['cinemas'][0]['slots']), 1)
        self.assertIsNotNone(public['cinemas'][0]['error'])
        self.assertEqual(len(self.calls), 1)
        self.run_check()
        self.assertIsNone(m.read_state(self.state)['cinemas']['24311']['error'])

    def test_empty_clears_exports_no_deletion_notification(self):
        self.run_check()
        self.run_check(lambda c: payload(c, []))
        self.assertNotIn('BEGIN:VEVENT', (self.root / 'movies.ics').read_text())
        self.assertEqual(self.calls, [])

    def test_bad_schema_and_wrong_cinema_fail(self):
        for data in [{}, {'showData': {}}, {'showData': {'cinemaId': '39869', 'movies': []}}]:
            with self.assertRaises(ValueError):
                m.parse(data, m.CINEMAS[0])

    def test_duplicate_slots_and_elapsed_filter(self):
        data = payload(m.CINEMAS[0], ['12:00', '12:00', '16:00'])
        rows = m.parse(data, m.CINEMAS[0], datetime(2099, 1, 3, 13, tzinfo=m.TZ))
        self.assertEqual([r['time'] for r in rows], ['16:00'])

    def test_no_notify_baseline_and_notification_splitting(self):
        self.run_check(no_notify=True, notify_initial=True)
        times = [f'{h:02}:00' for h in range(1, 23)]
        self.run_check(lambda c: payload(c, times))
        self.assertEqual(len(self.calls), 6)
        self.assertEqual(sum(len(call[2]) for call in self.calls), 42)
        self.assertTrue(all(len(call[2]) <= 8 for call in self.calls))

    def test_bark_validation(self):
        self.assertEqual(m.bark_settings('https://api.day.app/example/原来的内容'), ('https://api.day.app/push', 'example'))
        with self.assertRaises(ValueError):
            m.bark_settings('http://example.com/key')
        slots = m.parse(payload(m.CINEMAS[0]), m.CINEMAS[0])
        with patch.object(m, 'request_json', return_value={'code': 400}):
            with self.assertRaises(RuntimeError):
                m.notify('key', m.CINEMAS[0], slots, False)

    def test_ics_utc_duration_and_byte_folding(self):
        self.run_check()
        raw = (self.root / 'movies.ics').read_bytes()
        self.assertTrue(all(len(line) <= 75 for line in raw.split(b'\r\n')))
        content = raw.replace(b'\r\n ', b'').decode('utf-8')
        self.assertIn('DTSTART:20990103T040000Z', content)
        self.assertIn('DTEND:20990103T070100Z', content)
        self.assertIn('西安万达影城', content)
        self.assertIn('寰映影城', content)
        self.assertEqual(content.count('BEGIN:VEVENT'), 2)

    def test_cloud_entry_never_sends_even_with_bark_configured(self):
        import runpy
        from urllib.parse import parse_qs, urlparse
        def request(url, payload_body=None):
            self.assertEqual(urlparse(url).hostname, 'm.maoyan.com')
            self.assertIsNone(payload_body)
            cid = parse_qs(urlparse(url).query)['cinemaId'][0]
            return payload(next(c for c in m.CINEMAS if c['id'] == cid), movie='复仇者联盟4')
        args = ['run3.py', '--state', str(self.state), '--output-dir', str(self.root), '--notify-initial']
        with patch.dict('os.environ', {'BARK_URL': 'https://api.day.app/test-key'}), patch('sys.argv', args), patch.object(m, 'request_json', side_effect=request) as requests:
            with self.assertRaises(SystemExit) as done:
                runpy.run_path(str(m.ROOT / 'run3.py'), run_name='__main__')
            self.assertEqual(done.exception.code, 0)
            self.assertEqual(requests.call_count, 2)
        self.assertTrue((self.root / 'schedules.json').exists())
        for cinema in m.read_state(self.state)['cinemas'].values():
            self.assertEqual(cinema['pending'], {})

    def test_corrupt_state_does_not_reset(self):
        self.state.write_text('{invalid')
        with self.assertRaises(json.JSONDecodeError):
            self.run_check()
        self.assertEqual(self.state.read_text(), '{invalid')


if __name__ == '__main__':
    unittest.main()
