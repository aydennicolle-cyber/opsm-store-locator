from datetime import datetime, timedelta, timezone
import json
import csv
from pathlib import Path
import tempfile
import unittest

from scripts.refresh_sources import collect, compare, due


class SourceRefreshTests(unittest.TestCase):
    def setUp(self):
        self.row = dict(id='store-1', name='Example', full_address='1 Main St, Sydney NSW 2000',
                        latitude='-33.86', longitude='151.20', country='Australia', status='Active', phone='123')

    def test_unchanged_and_phone_update_are_automatic(self):
        current = {**self.row, 'phone': '456', 'fetched_at': '2026-11-09'}
        result = compare([self.row], [current])
        self.assertFalse(result['requires_review'])
        self.assertEqual(result['edits'][0]['fields'], ['phone'])

    def test_identity_location_status_and_services_changes_require_review(self):
        for field, value in [('name', 'Another'), ('full_address', '2 Main St'), ('latitude', '-33.87'),
                             ('status', 'Closed'), ('services', 'Optometry')]:
            with self.subTest(field=field):
                self.assertTrue(compare([self.row], [{**self.row, field: value}])['requires_review'])
        self.assertTrue(compare([self.row], [self.row, {**self.row, 'id': 'store-2'}])['requires_review'])
        self.assertTrue(compare([self.row, {**self.row, 'id': 'store-2'}], [self.row])['requires_review'])

    def test_invalid_feeds_never_pass(self):
        for records in [[], [self.row, self.row], [{**self.row, 'id': ''}],
                        [{**self.row, 'latitude': 'nan'}], [{**self.row, 'country': 'New Zealand'}]]:
            with self.assertRaises(ValueError):
                compare([self.row], records)

    def test_receipt_only_change_has_stable_content_digest(self):
        first = compare([self.row], [self.row])
        second = compare([self.row], [{**self.row, 'fetched_at': '2026-11-09', 'longitude': '151.20'}])
        self.assertEqual(first['content_sha256'], second['content_sha256'])

    def test_retry_backoff_and_success_cadence(self):
        now = datetime.now(timezone.utc)
        job = dict(interval_days=7, retry_days=2)
        state = dict(last_attempt_at=(now-timedelta(days=3)).isoformat(), status='refreshed')
        self.assertFalse(due(job,state,now))
        state['status']='failed'
        self.assertTrue(due(job,state,now))

    def test_failed_collector_cannot_replace_live_feed(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for folder in ['scripts','data','retailers/example']:
                (root/folder).mkdir(parents=True)
            target=root/'retailers/example/stores.csv'
            target.write_text('original feed')
            def fails(command, **kwargs):
                (kwargs['cwd']/'retailers/example/stores.csv').write_text('broken feed')
                raise ValueError('remote failure')
            job=dict(commands=[['fake']],folders=['example'],outputs=['retailers/example/stores.csv'])
            result=collect(job,root,root/'output',datetime.now(timezone.utc),runner=fails)
            self.assertEqual(result['status'],'failed')
            self.assertEqual(target.read_text(),'original feed')

    def test_registered_jobs_have_existing_outputs_and_bounded_commands(self):
        root=Path(__file__).resolve().parents[1]
        jobs=json.loads((root/'data/source_refresh_jobs.json').read_text())['jobs']
        self.assertEqual(len({j['id'] for j in jobs}),len(jobs))
        for job in jobs:
            self.assertGreater(job['interval_days'],0)
            self.assertLessEqual(job['timeout_seconds'],900)
            for output in job['outputs']:
                self.assertTrue((root/output).parent.is_dir(),output)
                self.assertNotIn('..',Path(output).parts)

    def test_success_is_adopted_but_changed_identity_is_only_exported(self):
        for changed in (False, True):
            with self.subTest(changed=changed), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                for folder in ['scripts', 'data', 'retailers/example']:
                    (root/folder).mkdir(parents=True)
                target = root/'retailers/example/stores.csv'
                def write(path, row):
                    with path.open('w', newline='') as stream:
                        writer=csv.DictWriter(stream,fieldnames=list(row))
                        writer.writeheader();writer.writerow(row)
                write(target,self.row)
                original=target.read_bytes()
                now=datetime.now(timezone.utc)
                def succeeds(command, **kwargs):
                    folder=kwargs['cwd']/'retailers/example'
                    write(folder/'stores.csv',{**self.row, 'name': 'Relocated' if changed else 'Example', 'phone':'456'})
                    (folder/'source_snapshot.json').write_text(json.dumps({'fetched_at':now.isoformat()}))
                job=dict(commands=[['fake']],folders=['example'],outputs=['retailers/example/stores.csv','retailers/example/source_snapshot.json'])
                result=collect(job,root,root/'output',now,runner=succeeds)
                if changed:
                    self.assertEqual(result['status'],'needs_review')
                    self.assertEqual(target.read_bytes(),original)
                    self.assertTrue((root/'output/candidate/retailers/example/stores.csv').exists())
                else:
                    self.assertEqual(result['status'],'refreshed')
                    self.assertIn('456',target.read_text())


if __name__ == '__main__':
    unittest.main()
