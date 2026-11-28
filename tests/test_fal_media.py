"""#701: Medien-Aufträge bei fal.ai in der Hintergrund-Warteschlange (ohne echten Aufruf)."""
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import fal_media  # noqa: E402
from image_validation import validate_image  # noqa: E402
import jobs  # noqa: E402
import research  # noqa: E402
import validate_project  # noqa: E402
from tests.test_jobs import Base, git  # noqa: E402

MODEL = 'fal-ai/wan/v2.2-a14b/image-to-video/turbo'
PNG = b'\x89PNG\r\n\x1a\n' + b'0' * 20


class FakeFal:
    """Ersetzt fal_media.call und download; zählt die Aufrufe."""
    def __init__(self, submit_status=200, states=('IN_PROGRESS', 'COMPLETED'), result_status=200, result_data=None):
        self.calls, self.downloads, self.states, self.submit_status = [], [], list(states), submit_status
        self.result_status, self.result_data, self.bodies = result_status, result_data, []

    def call(self, url, data=None, key=None):
        self.calls.append((url, data is not None, key))
        if data is not None:
            self.bodies.append(data)
            return (self.submit_status, {'request_id': 'req-123'} if self.submit_status < 300 else {'error': 'content_policy_violation'})
        if url.endswith('/status'):
            return 200, {'status': self.states.pop(0) if self.states else 'COMPLETED'}
        return self.result_status, self.result_data if self.result_data is not None else {'video': {'url': 'https://v3.fal.media/files/x/out.mp4'}}

    def download(self, url, dest):
        self.downloads.append(url)
        Path(dest).parent.mkdir(parents=True, exist_ok=True)
        Path(dest).write_bytes(b'video')
        return dest


class MediaJobTest(Base):
    @staticmethod
    def image_bytes(fmt='PNG'):
        from PIL import Image
        out = io.BytesIO()
        Image.new('RGB', (8, 8), 'white').save(out, format=fmt)
        return out.getvalue()

    def enqueue(self, **extra):
        fields = {'model': MODEL, 'prompt': 'Locked wide shot', 'seed': '7', 'confirm': True, 'price_usd': '0.10'}
        fields.update(extra)
        return jobs.enqueue(self.base, 'media', fields=fields)

    def run_jobs(self, fake, key='K', **kw):
        env = {'FAL_KEY': key} if key else {}
        with mock.patch.dict('os.environ', env, clear=False), mock.patch.object(fal_media, 'call', fake.call), \
                mock.patch.object(fal_media, 'download', fake.download), mock.patch.object(fal_media.time, 'sleep', lambda s: None), \
                mock.patch.object(jobs, 'budget_low', return_value=False), mock.patch('pricing.rates_for', return_value=None):
            if not key:
                import os
                os.environ.pop('FAL_KEY', None)
            return jobs.process(self.base, commit=kw.get('commit', False), push_to=kw.get('push_to'), types=['media'])

    def test_enqueue_goes_to_work_branch_with_schema(self):
        path = self.enqueue(params='{"resolution":"720p"}')
        data = yaml.safe_load(path.read_text())
        self.assertEqual(data['type'], 'media')
        self.assertTrue(data['media']['confirm'])
        import json, jsonschema
        jsonschema.validate(data, json.loads((ROOT / 'schemas/job.schema.json').read_text()))
        self.assertEqual(jobs.TARGET['media'], 'work')
        self.assertEqual(jobs.WORKFLOW['media'], 'media.yml')

    def test_request_number_and_cost_id_are_not_reused_after_a_job_is_done(self):   # #719
        first = self.enqueue()
        self.assertEqual(first.name, 'request-001.yml')
        results, _ = self.run_jobs(FakeFal())
        self.assertTrue(results[0]['ok'], results)
        self.assertFalse(first.exists())                                              # erledigte Aufträge werden gelöscht
        second = self.enqueue()
        self.assertEqual(second.name, 'request-002.yml')                              # nicht wieder 001
        results, _ = self.run_jobs(FakeFal())
        self.assertTrue(results[0]['ok'], results)
        ids = [e['activity_id'] for e in yaml.safe_load((self.base / 'costs' / 'project.yml').read_text())['entries']]
        self.assertEqual(ids, ['act-media-request-001', 'act-media-request-002'])    # zwei verschiedene Kosten-IDs

    def test_cost_id_stays_unique_even_if_an_old_entry_collides(self):   # #719, Sicherung in run_media
        costs = self.base / 'costs' / 'project.yml'
        costs.parent.mkdir(exist_ok=True)
        costs.write_text(yaml.safe_dump({'scope': 'project', 'entries': [{'activity_id': 'act-media-request-001'}]}), encoding='utf-8')
        self.assertEqual(jobs.unique_activity_id(self.base, 'act-media-request-001'), 'act-media-request-001-2')
        self.assertEqual(jobs.unique_activity_id(self.base, 'act-media-request-009'), 'act-media-request-009')

    def test_truncated_input_is_rejected_before_enqueue_or_submit(self):
        image = self.base / 'broken.png'
        valid = self.image_bytes()
        image.write_bytes(valid[:len(valid) // 3])
        with self.assertRaisesRegex(research.ResearchError, 'beschädigt oder unvollständig'):
            jobs.enqueue(self.base, 'media', fields={'model': MODEL, 'prompt': 'test', 'confirm': True, 'input': 'broken.png'})
        self.assertEqual(jobs.files(self.base), [])
        path = self.enqueue()
        data = yaml.safe_load(path.read_text())
        data['media']['input'] = 'broken.png'   # bereits vorhandener Auftrag aus einer älteren Programmversion
        path.write_text(yaml.safe_dump(data))
        fake = FakeFal()
        results, _ = self.run_jobs(fake)
        self.assertFalse(results[0]['ok'])
        self.assertIn('beschädigt oder unvollständig', results[0]['error'])
        self.assertEqual(fake.calls, [])
        saved = yaml.safe_load(path.read_text())
        self.assertNotIn('submitted', saved)
        self.assertFalse((self.base / 'costs/project.yml').exists())

    def test_valid_png_jpeg_and_webp_inputs_are_submitted(self):
        for fmt, ext, mime in [('PNG', '.png', 'image/png'), ('JPEG', '.jpg', 'image/jpeg'), ('WEBP', '.webp', 'image/webp')]:
            with self.subTest(format=fmt):
                (self.base / f'input{ext}').write_bytes(self.image_bytes(fmt))
                self.enqueue(input=f'input{ext}')
                fake = FakeFal()
                results, _ = self.run_jobs(fake)
                self.assertTrue(results[0]['ok'], results)
                self.assertEqual(len(fake.bodies), 1)
                self.assertTrue(fake.bodies[0]['image_url'].startswith(f'data:{mime};base64,'))

    def test_image_validation_fallback_without_pillow(self):
        valid = self.image_bytes()
        with mock.patch.dict(sys.modules, {'PIL': None}):
            validate_image(valid, 'valid.png', 'image/png')
            with self.assertRaisesRegex(ValueError, 'beschädigt oder unvollständig'):
                validate_image(valid[:len(valid) // 3], 'broken.png', 'image/png')
            with self.assertRaisesRegex(ValueError, 'beschädigt oder unvollständig'):
                validate_image(b'not-a-png' + bytes.fromhex('0000000049454e44ae426082'), 'fake.png', 'image/png')

    def test_fal_error_text_extracts_message_and_type(self):
        raw = json.dumps({'detail': [{'msg': 'Failed to load the image. Please ensure the image file is not corrupted.',
                                      'type': 'image_load_error', 'loc': ['body', 'input.image_url']}]})
        self.assertEqual(fal_media._error_text(raw),
                         'Failed to load the image. Please ensure the image file is not corrupted. [image_load_error]')
        self.assertEqual(fal_media._error_text('plain provider error'), 'plain provider error')

    def test_final_4xx_result_allows_retry_with_new_submission(self):
        (self.base / 'input.png').write_bytes(self.image_bytes())
        path = self.enqueue(input='input.png')
        failed = FakeFal(result_status=422, result_data={'error': 'Failed to load the image. [image_load_error]'})
        results, _ = self.run_jobs(failed)
        self.assertFalse(results[0]['ok'])
        self.assertIn('image_load_error', results[0]['error'])
        data = yaml.safe_load(path.read_text())
        self.assertNotIn('submitted', data)
        self.assertEqual(data['previous_request']['request_id'], 'req-123')
        self.assertEqual(data['previous_request']['http_status'], 422)
        jobs.retry(self.base, path.name)
        retry_fake = FakeFal()
        results, _ = self.run_jobs(retry_fake)
        self.assertTrue(results[0]['ok'], results)
        self.assertEqual(len([call for call in retry_fake.calls if call[1]]), 1)

    def test_final_5xx_keeps_request_id(self):
        path = self.enqueue()
        failed = FakeFal(result_status=503, result_data={'error': 'provider unavailable'})
        results, _ = self.run_jobs(failed)
        self.assertFalse(results[0]['ok'])
        data = yaml.safe_load(path.read_text())
        self.assertEqual(data['submitted']['request_id'], 'req-123')
        self.assertNotIn('previous_request', data)

    def test_runs_submits_once_saves_result_and_cost(self):
        self.enqueue()
        fake = FakeFal()
        results, remaining = self.run_jobs(fake)
        self.assertTrue(results[0]['ok'], results)
        posts = [c for c in fake.calls if c[1]]
        self.assertEqual(len(posts), 1)                                              # genau ein bezahlter Aufruf
        self.assertEqual(posts[0][0], f'https://queue.fal.run/{MODEL}')
        self.assertTrue(all(c[2] == 'K' for c in fake.calls))                         # Schlüssel nur im Aufruf
        self.assertTrue(any(c[0].endswith('fal-ai/wan/requests/req-123/status') for c in fake.calls))
        self.assertEqual(fake.downloads, ['https://v3.fal.media/files/x/out.mp4'])
        self.assertTrue((self.base / 'media/request-001/video-1.mp4').is_file())
        meta = yaml.safe_load((self.base / 'media/request-001/media.yml').read_text())
        self.assertNotIn('req-123', str(meta))                                       # request_id steht nicht im Ergebnis
        cost = yaml.safe_load((self.base / 'costs/project.yml').read_text())['entries'][-1]
        self.assertEqual((cost['provider'], cost['cost_amount'], cost['cost_status'], cost['currency']), ('fal', 0.1, 'estimated', 'USD'))   # ohne Kurs bleibt die Originalwährung
        self.assertEqual(cost['exchange_rate_status'], 'unavailable')
        self.assertEqual(jobs.files(self.base), [])                                  # Auftrag erledigt
        self.assertEqual(validate_project.schema_errors(validate_project.COSTS, yaml.safe_load((self.base / 'costs/project.yml').read_text()), 'costs'), [])

    def test_no_payment_without_confirm_or_key(self):
        self.enqueue(confirm='')
        fake = FakeFal()
        results, _ = self.run_jobs(fake)
        self.assertFalse(results[0]['ok'])
        self.assertIn('bestätigung', results[0]['error'].lower())
        self.assertEqual(fake.calls, [])
        self.base_job = jobs.files(self.base)[0]
        data = yaml.safe_load(self.base_job.read_text())
        data.pop('error'); data.pop('failed_at', None); data['media']['confirm'] = True
        self.base_job.write_text(yaml.safe_dump(data))
        results, _ = self.run_jobs(fake, key='')
        self.assertIn('FAL_KEY', results[0]['error'])
        self.assertEqual(fake.calls, [])

    def test_rejection_is_not_retried_and_nothing_saved(self):
        self.enqueue()
        fake = FakeFal(submit_status=422)
        results, _ = self.run_jobs(fake)
        self.assertFalse(results[0]['ok'])
        self.assertIn('nicht angenommen', results[0]['error'])
        self.assertEqual(len([c for c in fake.calls if c[1]]), 1)
        data = yaml.safe_load(jobs.files(self.base)[0].read_text())
        self.assertNotIn('submitted', data)                                          # nichts gesendet worden

    def test_resume_never_submits_twice(self):
        path = self.enqueue()
        data = yaml.safe_load(path.read_text())
        data['submitted'] = {'request_id': 'req-123', 'at': '2026-11-26T10:00:00+00:00'}   # früherer Lauf: gesendet, dann Abbruch
        path.write_text(yaml.safe_dump(data))
        fake = FakeFal()
        results, _ = self.run_jobs(fake)
        self.assertTrue(results[0]['ok'], results)
        self.assertEqual([c for c in fake.calls if c[1]], [])                         # kein zweiter bezahlter Aufruf

    def test_timeout_keeps_request_id_for_next_run(self):
        self.enqueue()
        fake = FakeFal(states=['IN_PROGRESS'] * 500)
        with mock.patch.dict('os.environ', {'FAL_WAIT_SECONDS': '0'}):
            results, _ = self.run_jobs(fake)
        self.assertFalse(results[0]['ok'])
        self.assertIn('Zeit abgelaufen', results[0]['error'])
        data = yaml.safe_load(jobs.files(self.base)[0].read_text())
        self.assertEqual(data['submitted']['request_id'], 'req-123')                  # bleibt erhalten
        jobs.retry(self.base, jobs.files(self.base)[0].name)
        fake2 = FakeFal()
        results, _ = self.run_jobs(fake2)
        self.assertTrue(results[0]['ok'])
        self.assertEqual([c for c in fake2.calls if c[1]], [])

    def test_submitted_is_committed_before_waiting(self):
        self.enqueue()
        fake = FakeFal(states=['IN_PROGRESS'] * 500)
        with mock.patch.dict('os.environ', {'FAL_WAIT_SECONDS': '0'}):
            self.run_jobs(fake, commit=True, push_to='ghostwriter/buch/b')
        git(self.base, 'fetch', '-q', 'origin')
        log = git(self.base, 'log', '--format=%s', 'origin/ghostwriter/buch/b')
        self.assertIn('Medien-Auftrag request-001 gesendet', log)                    # gesichert, bevor gewartet wurde

    def test_input_must_be_inside_book_and_download_host_checked(self):
        (self.base / 'bild.png').write_bytes(PNG)
        self.enqueue(input='../draussen.png')
        results, _ = self.run_jobs(FakeFal())
        self.assertIn('Bilddatei im Buch', results[0]['error'])
        self.assertTrue(fal_media.host_ok('https://v3b.fal.media/a.mp4'))
        self.assertFalse(fal_media.host_ok('https://evil.example/a.mp4'))
        self.assertFalse(fal_media.host_ok('http://v3.fal.media/a.mp4'))
        self.assertEqual(fal_media.app_of(MODEL), 'fal-ai/wan')
        with self.assertRaises(fal_media.FalError):
            fal_media.app_of('nur-eins')

    def test_owner_budget_pauses_media_until_confirmed(self):
        """Das Monatsbudget legt der Eigentümer fest (limits); ist es knapp, wartet der Auftrag, ohne dass etwas gesendet wird."""
        self.enqueue()
        fake = FakeFal()
        with mock.patch.dict('os.environ', {'FAL_KEY': 'K'}), mock.patch.object(fal_media, 'call', fake.call), \
                mock.patch.object(jobs, 'budget_low', return_value=True):
            results, _ = jobs.process(self.base, commit=False, types=['media'])
        self.assertTrue(results[0].get('waiting'))
        self.assertEqual(fake.calls, [])
        self.assertEqual(jobs.files(self.base)[0].exists(), True)

    def test_images_and_audio_are_saved_too(self):
        self.assertEqual(fal_media.media_urls({'images': [{'url': 'https://v3.fal.media/a.png'}, {'url': 'https://v3.fal.media/b.png'}]}),
                         [('image', 'https://v3.fal.media/a.png'), ('image', 'https://v3.fal.media/b.png')])
        self.assertEqual(fal_media.media_urls({'audio': {'url': 'https://v3.fal.media/a.mp3'}}), [('audio', 'https://v3.fal.media/a.mp3')])
        with self.assertRaises(fal_media.FalError):
            fal_media.media_urls({'other': 1})

    def test_workflow_and_remote_start(self):
        wf = yaml.safe_load((ROOT / '.github/workflows/media.yml').read_text())
        proc = wf['jobs']['process']
        self.assertEqual(proc['concurrency']['group'], 'jobs-${{ needs.prep.outputs.book }}')
        text = (ROOT / '.github/workflows/media.yml').read_text()
        self.assertIn('--types media', text)
        self.assertIn('secrets.FAL_KEY', text)
        self.assertNotIn('GEMINI', text)
        self.assertRegex(text, r'pip install [^\n]*pillow')


if __name__ == '__main__':
    unittest.main()
