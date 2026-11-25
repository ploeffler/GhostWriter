"""Referenzbilder an einen Bilddienst übergeben, Fähigkeit je Dienst, Protokoll (#143), nur mit Attrappe (D08)."""
from tests.authority_helpers import fake_github

import base64
import hashlib
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import image_service as svc  # noqa: E402
import reference_images  # noqa: E402
from tests.test_cover import png  # noqa: E402


class ImageServiceTest(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.tmp = Path(tmp.name)
        self.project = self.tmp / 'book'
        shutil.copytree(ROOT / 'tests/fixtures/adhs', self.project)
        fake_github(self, self.project, seal=False)

    def reference(self, name='opi', size=(120, 80), approve=True):
        src = self.tmp / f'{name}.png'
        png(src, *size)
        meta = reference_images.add(self.project, src, caption=f'Referenz {name}', description='Weißer Bart', purpose='Aussehen',
                                    roles=['visual_reference'], origin='provided', links=[{'kind': 'person', 'id': 'char-opi'}],
                                    consent='Vom Benutzer zur Referenz freigegeben')
        if approve:
            reference_images.set_status(self.project, meta['id'], 'approved')
        return meta['id']

    def test_capability_model_in_providers_yml(self):
        found = svc.services()
        self.assertTrue(found['google']['via_action'] and found['google']['references']['supported'])
        self.assertEqual(found['google']['references']['max'], 3)
        self.assertFalse(found['openai']['via_action'])
        self.assertIn('Google Gemini', svc.services_text())

    def test_supported_service_gets_the_bytes_with_a_version_each(self):
        a, b = self.reference('a'), self.reference('b')
        p = svc.plan(self.project, 'google', [a, b])
        self.assertEqual((p['modus'], [h['id'] for h in p['uebergeben']], p['uebersprungen']), ('bytes', [a, b], []))
        data = Path(p['uebergeben'][0]['datei']).read_bytes()
        self.assertEqual(p['uebergeben'][0]['version'], 'sha256:' + hashlib.sha256(data).hexdigest())
        self.assertEqual(p['uebergeben'][0]['mime'], 'image/png')

    def test_too_many_references_are_skipped_with_a_reason(self):
        ids = [self.reference(f'r{i}') for i in range(5)]
        p = svc.plan(self.project, 'google', ids)
        self.assertEqual(len(p['uebergeben']), 3)
        self.assertEqual([s['id'] for s in p['uebersprungen']], ids[3:])
        self.assertIn('höchstens', p['uebersprungen'][0]['grund'])
        self.assertTrue(p['hinweise'])

    def test_unsupported_service_says_so_and_hands_nothing_over(self):
        a = self.reference('a')
        for service in ('openai', 'chat', 'unbekannt'):
            p = svc.plan(self.project, service, [a])
            self.assertEqual((p['modus'], p['uebergeben']), ('text-only', []), service)
            self.assertTrue(p['hinweise'], service)
            self.assertEqual(p['uebersprungen'][0]['id'], a)

    def test_only_approved_references_can_be_selected(self):
        draft = self.reference('d', approve=False)
        with self.assertRaisesRegex(SystemExit, 'nicht als visuelle Referenz freigegeben'):
            svc.plan(self.project, 'google', [draft])

    def test_generate_sends_inline_bytes_and_writes_the_record(self):
        a = self.reference('a')
        sent = {}

        def fake_post(url, body, headers):
            sent.update(url=url, body=body, headers=headers)
            return {'candidates': [{'content': {'parts': [{'inlineData': {'data': base64.b64encode(b'JPEGDATA').decode()}}]}}]}
        with self.assertRaisesRegex(ValueError, '--consent'):
            svc.generate(self.project, 'google', 'Opi im Garten', [a], key='k', post=fake_post)
        self.assertEqual(sent, {})   # ohne Einverständnis nichts gesendet
        folder, rec = svc.generate(self.project, 'google', 'Opi im Garten', [a], key='k', consent=True, post=fake_post,
                                   today=__import__('datetime').date(2026, 11, 25))
        parts = sent['body']['contents'][0]['parts']
        self.assertEqual(parts[0], {'text': 'Opi im Garten'})
        self.assertEqual(base64.b64decode(parts[1]['inline_data']['data']), Path(rec['uebergeben'] and svc.plan(self.project, 'google', [a])['uebergeben'][0]['datei']).read_bytes())
        self.assertEqual(sent['headers'], {'x-goog-api-key': 'k'})
        self.assertIn('gemini-2.5-flash-image', sent['url'])
        self.assertEqual((folder / 'bild.jpg').read_bytes(), b'JPEGDATA')
        saved = yaml.safe_load((folder / 'handover.yml').read_text(encoding='utf-8'))
        self.assertEqual(saved['modus'], 'bytes')
        self.assertEqual([h['id'] for h in saved['uebergeben']], [a])
        self.assertTrue(saved['uebergeben'][0]['version'].startswith('sha256:'))
        self.assertEqual(folder.name, '2026-11-25-01')
        folder2, _ = svc.generate(self.project, 'google', 'Zweiter', [a], key='k', consent=True, post=fake_post,
                                  today=__import__('datetime').date(2026, 11, 25))
        self.assertEqual(folder2.name, '2026-11-25-02')   # nichts überschrieben

    def test_text_only_needs_an_explicit_ok_and_is_recorded_as_such(self):
        a = self.reference('a')
        calls = []

        def fake_post(url, body, headers):
            calls.append(body)
            return {'candidates': [{'content': {'parts': [{'inlineData': {'data': base64.b64encode(b'X').decode()}}]}}]}
        # Dienst ohne Übergabe: erst Fehler, dann mit --text-only-ok nur Beschreibung im Text
        svc_tmp = self.tmp / 'prov'
        svc_tmp.mkdir()
        (svc_tmp / 'providers.yml').write_text(yaml.safe_dump({'image_services': [
            {'id': 'google', 'name': 'G', 'via_action': True, 'api_key_secret': 'K', 'references': {'supported': False}}]}), encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'text-only-ok'):
            svc.generate(self.project, 'google', 'p', [a], key='k', post=fake_post, root=svc_tmp)
        self.assertEqual(calls, [])
        folder, rec = svc.generate(self.project, 'google', 'p', [a], key='k', post=fake_post, root=svc_tmp, text_only_ok=True)
        parts = calls[0]['contents'][0]['parts']
        self.assertEqual(len(parts), 1)   # nur Text, kein Bild
        self.assertIn('NICHT als Bild übergeben', parts[0]['text'])
        self.assertEqual((rec['modus'], rec['uebergeben']), ('text-only', []))

    def test_workflow_exists_and_is_manual(self):
        wf = yaml.safe_load((ROOT / '.github/workflows/image.yml').read_text(encoding='utf-8'))
        triggers = wf.get('on') or wf.get(True)
        self.assertEqual(list(triggers), ['workflow_dispatch'])
        self.assertIn('consent', triggers['workflow_dispatch']['inputs'])


if __name__ == '__main__':
    unittest.main()
