"""#452: Fotos colorieren – nur Farbkanäle, Sperren, Eintrag in bild.yml, Action."""
import base64
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import numpy as np
import yaml
from PIL import Image, ImageFilter

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import colorize  # noqa: E402

META = 'titel: Paar\nart: foto-vom-foto\nminderjaehrige: false\n# Kommentar bleibt\nbearbeitung:\n  - "aufbereitet.jpg: Graustufen"\nbuch:\n  vormerken: false\n'


def gray(w=400, h=300, seed=1):
    rng = np.random.default_rng(seed)
    y, x = np.mgrid[0:h, 0:w]
    g = (128 + 80 * np.sin(x / 30) * np.cos(y / 40) + rng.normal(0, 3, (h, w))).clip(0, 255).astype(np.uint8)
    return Image.fromarray(g, 'L')


def tinted(img, size=None, red_box=True):
    g = np.asarray(img.convert('L'), dtype=np.float64)
    rgb = np.stack([g * 1.0, g * 0.8, g * 0.55], -1).clip(0, 255).astype(np.uint8)
    if red_box:
        rgb[40:120, 40:120] = [255, 0, 0]          # außerhalb des Gamuts nach Helligkeitstausch
    out = Image.fromarray(rgb, 'RGB').filter(ImageFilter.GaussianBlur(1.5))
    return out.resize(size) if size else out


class Book:
    def __init__(self, meta=META):
        self.tmp = tempfile.TemporaryDirectory()
        self.base = Path(self.tmp.name)
        self.folder = self.base / 'quellen' / 'bilder' / 'x'
        self.folder.mkdir(parents=True)
        gray().save(self.folder / 'aufbereitet.jpg', quality=92)
        if meta is not None:
            (self.folder / 'bild.yml').write_text(meta, encoding='utf-8')

    def proposal(self, img):
        path = self.base / 'vorschlag.png'
        img.save(path)
        return path


class ColorTest(unittest.TestCase):
    def test_lab_roundtrip(self):
        rgb = np.random.default_rng(2).random((50, 3))
        self.assertLess(np.abs(colorize.lab_to_rgb(colorize.rgb_to_lab(rgb)) - rgb).max(), 1e-6)

    def test_out_of_gamut_keeps_lightness(self):
        lab = np.array([[[90.0, 80.0, -90.0]]])          # helles, sehr sattes Violett: nicht darstellbar
        rgb = colorize.lab_to_rgb(lab)
        self.assertAlmostEqual(float(colorize.rgb_to_lab(rgb)[0, 0, 0]), 90.0, places=2)

    def test_proposal_only_adds_color(self):
        b = Book()
        base = colorize.open_image(b.folder / 'aufbereitet.jpg')
        r = colorize.colorize(b.base, 'quellen/bilder/x', proposal=b.proposal(tinted(base, (512, 384))),
                              tool='Test (m1)')
        self.assertLess(r['deviation'], 1.0)
        out = Image.open(b.folder / 'coloriert.jpg')
        self.assertEqual(out.size, base.size)
        arr = np.asarray(out.convert('RGB'), dtype=int)
        self.assertGreater(np.abs(arr[..., 0] - arr[..., 2]).mean(), 10)   # wirklich eingefärbt
        text = (b.folder / 'bild.yml').read_text(encoding='utf-8')
        self.assertIn('# Kommentar bleibt', text)
        data = yaml.safe_load(text)
        self.assertEqual(len(data['bearbeitung']), 2)
        self.assertIn('Farbvorschlag Test (m1)', data['bearbeitung'][1])
        self.assertIn('nur Farbkanäle a/b übernommen', data['bearbeitung'][1])
        self.assertEqual(data['buch'], {'vormerken': False})
        self.assertIsNone(r['cost'])
        with self.assertRaises(SystemExit):        # vorhandenes Ergebnis nur mit replace
            colorize.colorize(b.base, 'quellen/bilder/x', proposal=b.proposal(tinted(base)))
        colorize.colorize(b.base, 'quellen/bilder/x', proposal=b.proposal(tinted(base)), replace=True)

    def test_rejects_other_aspect_or_layout(self):
        b = Book()
        base = colorize.open_image(b.folder / 'aufbereitet.jpg')
        with self.assertRaisesRegex(SystemExit, 'Seitenverhältnis'):
            colorize.colorize(b.base, 'quellen/bilder/x', proposal=b.proposal(tinted(base, (400, 400))))
        other = tinted(gray(seed=9).transpose(Image.FLIP_LEFT_RIGHT).rotate(90).resize((400, 300)), red_box=False)
        with self.assertRaisesRegex(SystemExit, 'Bildaufbau'):
            colorize.colorize(b.base, 'quellen/bilder/x', proposal=b.proposal(other))
        self.assertFalse((b.folder / 'coloriert.jpg').exists())


class LockTest(unittest.TestCase):
    def check(self, meta, pattern):
        b = Book(meta)
        with self.assertRaisesRegex(SystemExit, pattern):
            colorize.main([str(b.base), 'quellen/bilder/x', '--check'])

    def test_locks(self):
        self.check(None, 'bild.yml fehlt')
        self.check('art: foto\nminderjaehrige: true\n', 'Ausnahme')
        self.check('art: foto\n', 'minderjaehrige: false')
        self.check('art: dokument\nminderjaehrige: false\n', 'Dokumente')
        self.check('minderjaehrige: false\n', 'Dokumente')

    def test_minors_exception(self):
        b = Book('art: foto\nminderjaehrige: true\nbearbeitung: []\n')
        out = io.StringIO()
        with mock.patch('sys.stdout', out):
            colorize.main([str(b.base), 'quellen/bilder/x', '--check', '--minors-exception'])
        self.assertIn('Ausnahme', out.getvalue())
        for meta in ('art: foto\n', 'art: dokument\nminderjaehrige: true\n'):   # fehlende Angabe, Dokument
            c = Book(meta)
            with self.assertRaises(SystemExit):
                colorize.main([str(c.base), 'quellen/bilder/x', '--check', '--minors-exception'])
        with self.assertRaisesRegex(SystemExit, 'Einverständnis'):
            colorize.colorize(b.base, 'quellen/bilder/x', minors_exception=True)
        base = colorize.open_image(b.folder / 'aufbereitet.jpg')
        colorize.colorize(b.base, 'quellen/bilder/x', proposal=b.proposal(tinted(base)), tool='Test',
                          minors_exception=True)
        meta = yaml.safe_load((b.folder / 'bild.yml').read_text(encoding='utf-8'))
        self.assertTrue(meta['minderjaehrige'])                                     # Angabe bleibt
        self.assertIn('Ausnahme: Minderjährige abgebildet', meta['bearbeitung'][-1])

    def test_hint_only_with_gemini(self):
        b = Book()
        base = colorize.open_image(b.folder / 'aufbereitet.jpg')
        with self.assertRaisesRegex(SystemExit, 'Farbhinweis'):
            colorize.colorize(b.base, 'quellen/bilder/x', proposal=b.proposal(tinted(base)), hint='rot')
        with self.assertRaisesRegex(SystemExit, 'zu lang'):
            colorize.colorize(b.base, 'quellen/bilder/x', consent=True, key='k', hint='x' * 301)
        self.assertEqual(colorize.prompt_for(None), colorize.PROMPT)
        self.assertTrue(colorize.prompt_for('  Die Fahne\n ist rot-weiß-rot. ').endswith('Die Fahne ist rot-weiß-rot.'))

    def test_front_side_source(self):
        b = Book()
        (b.folder / 'aufbereitet.jpg').rename(b.folder / 'aufbereitet-1.jpg')
        base = colorize.open_image(b.folder / 'aufbereitet-1.jpg')
        r = colorize.colorize(b.base, 'quellen/bilder/x', proposal=b.proposal(tinted(base)), tool='Test')
        self.assertIn('L-Kanal aus aufbereitet-1.jpg', r['line'])
        (b.folder / 'aufbereitet-1.jpg').unlink()
        with self.assertRaisesRegex(SystemExit, 'aufbereitet-1.jpg'):
            colorize.main([str(b.base), 'quellen/bilder/x', '--check'])

    def test_outside_book(self):
        b = Book()
        (b.base / 'anderes').mkdir()
        with self.assertRaisesRegex(SystemExit, 'nicht im Buch'):
            colorize.main([str(b.base / 'anderes'), '../quellen/bilder/x', '--check'])

    def test_api_needs_consent_and_key(self):
        b = Book()
        with self.assertRaisesRegex(SystemExit, 'Einverständnis'):
            colorize.colorize(b.base, 'quellen/bilder/x')
        with mock.patch.dict('os.environ', {}, clear=True), self.assertRaisesRegex(SystemExit, 'GEMINI_API_KEY'):
            colorize.colorize(b.base, 'quellen/bilder/x', consent=True)


class ProcessingTest(unittest.TestCase):
    def run_add(self, text):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / 'bild.yml'
            p.write_text(text, encoding='utf-8')
            colorize.add_processing(p, 'neu: „x“')
            return p.read_text(encoding='utf-8')

    def test_variants(self):
        self.assertEqual(yaml.safe_load(self.run_add('a: 1\nbearbeitung: []\nb: 2\n'))['bearbeitung'], ['neu: „x“'])
        out = self.run_add('a: 1\nbearbeitung:\n  - eins\n\nb: 2\n')
        self.assertEqual(yaml.safe_load(out), {'a': 1, 'bearbeitung': ['eins', 'neu: „x“'], 'b': 2})
        self.assertEqual(yaml.safe_load(self.run_add('a: 1'))['bearbeitung'], ['neu: „x“'])
        self.assertEqual(yaml.safe_load(self.run_add('bearbeitung:\n- eins\n'))['bearbeitung'], ['eins', 'neu: „x“'])


class GeminiTest(unittest.TestCase):
    def test_request_and_cost(self):
        b = Book()
        base = colorize.open_image(b.folder / 'aufbereitet.jpg')
        buf = io.BytesIO()
        tinted(base, (512, 384)).save(buf, 'PNG')
        answer = {'candidates': [{'content': {'parts': [{'text': 'ok'}, {'inlineData': {
            'mimeType': 'image/png', 'data': base64.b64encode(buf.getvalue()).decode()}}]}}],
            'usageMetadata': {'promptTokenCount': 1300, 'candidatesTokenCount': 1290}}
        seen = {}

        class Resp(io.BytesIO):
            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False

        def fake(req, timeout=0):
            seen['url'], seen['headers'], seen['body'] = req.full_url, dict(req.headers), json.loads(req.data)
            return Resp(json.dumps(answer).encode())

        (b.base / 'ghostwriter.yml').write_text('ai_providers:\n  services:\n    google:\n      model: gemini-x-image\n',
                                                encoding='utf-8')
        with mock.patch('urllib.request.urlopen', fake):
            r = colorize.colorize(b.base, 'quellen/bilder/x', consent=True, key='k',
                                  now='2026-11-21T15:00:00+01:00', hint='Die Fahne ist rot-weiß-rot.')
        self.assertIn('/models/gemini-x-image:generateContent', seen['url'])
        self.assertEqual(seen['headers'].get('X-goog-api-key'), 'k')
        parts = seen['body']['contents'][0]['parts']
        self.assertEqual(parts[1]['inline_data']['mime_type'], 'image/jpeg')
        self.assertTrue(parts[0]['text'].endswith(colorize.HINT_PREFIX + 'Die Fahne ist rot-weiß-rot.'))
        self.assertEqual(seen['body']['generationConfig']['responseModalities'], ['IMAGE'])
        self.assertEqual(seen['body']['generationConfig']['imageConfig'], {'aspectRatio': '4:3'})
        self.assertEqual(r['model'], 'gemini-x-image')
        costs = yaml.safe_load((b.base / 'costs' / 'project.yml').read_text(encoding='utf-8'))
        entry = costs['entries'][0]
        self.assertEqual((entry['source'], entry['provider'], entry['image_units'], entry['input_tokens']),
                         ('action_api', 'google', 1, 1300))
        self.assertEqual(entry['activity_id'], 'act-colorize-001')
        meta = yaml.safe_load((b.folder / 'bild.yml').read_text(encoding='utf-8'))
        self.assertIn('Google Gemini (gemini-x-image', meta['bearbeitung'][-1])
        self.assertIn('Farbhinweis an das Modell: „Die Fahne ist rot-weiß-rot.“', meta['bearbeitung'][-1])

    def test_padding_for_other_aspect(self):
        img = gray(480, 260)                               # 1,85 : 1 wie ein Abzug mit Büttenrand
        padded, name, box = colorize.pad_to_aspect(img)
        self.assertEqual(name, '16:9')
        self.assertEqual(padded.size, (480, 270))
        self.assertEqual(box, (0, 5, 480, 260))
        tinted_pad = tinted(padded, (1376, 774), red_box=False)   # Gemini liefert andere Größe, gleiches Format
        back = colorize.crop_back(tinted_pad, padded.size, box)
        self.assertEqual(back.size, img.size)
        self.assertGreater(colorize.correlation(img.convert('RGB'), back), 0.9)
        with self.assertRaisesRegex(SystemExit, 'Seitenverhältnis'):
            colorize.crop_back(tinted(padded, (1408, 736)), padded.size, box)

    def test_no_image_and_model_default(self):
        b = Book()
        self.assertEqual(colorize.model_for(b.base), colorize.DEFAULT_MODEL)
        (b.base / 'ghostwriter.yml').write_text('ai_providers:\n  services:\n    google:\n      model: gemini-2.5-pro\n',
                                                encoding='utf-8')
        self.assertEqual(colorize.model_for(b.base), colorize.DEFAULT_MODEL)   # kein Bildmodell
        self.assertEqual(colorize.model_for(b.base, 'm-image'), 'm-image')

        class Resp(io.BytesIO):
            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False

        blocked = {'candidates': [{'finishReason': 'IMAGE_SAFETY', 'content': {'parts': []}}]}
        with mock.patch('urllib.request.urlopen', lambda req, timeout=0: Resp(json.dumps(blocked).encode())), \
                self.assertRaisesRegex(SystemExit, 'IMAGE_SAFETY'):
            colorize.colorize(b.base, 'quellen/bilder/x', consent=True, key='k')
        self.assertFalse((b.folder / 'coloriert.jpg').exists())


class WorkflowTest(unittest.TestCase):
    def test_workflow(self):
        data = yaml.safe_load((ROOT / '.github' / 'workflows' / 'colorize.yml').read_text(encoding='utf-8'))
        on = data.get('on', data.get(True))
        self.assertEqual(set(on), {'workflow_dispatch'})
        self.assertEqual(set(on['workflow_dispatch']['inputs']),
                         {'folder', 'consent', 'model', 'replace', 'hint', 'minors_exception'})
        self.assertEqual(data['permissions'], {'contents': 'write', 'pull-requests': 'write', 'actions': 'write'})
        self.assertEqual(data['defaults']['run']['shell'], 'bash')
        text = (ROOT / '.github' / 'workflows' / 'colorize.yml').read_text(encoding='utf-8')
        self.assertIn('secrets.GEMINI_API_KEY', text)
        self.assertIn('--field "hint=$HINT"', text)                # Hinweis über env in den Auftrag (#479)
        self.assertNotIn('${{ inputs.hint }}"', text)          # nur über env, nie direkt im Skript
        self.assertIn('GhostWriter: offene Änderungen', text)
        # Ausführung seit #479 in der Hintergrund-Warteschlange (scripts/jobs.py)
        jobs_src = (ROOT / 'scripts' / 'jobs.py').read_text(encoding='utf-8')
        for needle in ("'--check'", "'--minors-exception'", "'--hint'", "'image.colorize'", 'consent'):
            self.assertIn(needle, jobs_src)


if __name__ == '__main__':
    unittest.main()
