"""EasyMDE: reale Browserprüfung des Editor-/Textfeld-Vertrags."""
import os
import re
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EDITOR = ROOT / 'apps' / 'web' / 'editor-web.js'
DEMO = ROOT / 'apps' / 'web' / 'editor-prototype.html'
BROWSER = os.environ.get('GW_TEST_BROWSER') or shutil.which('google-chrome')


@unittest.skipUnless(BROWSER, 'Chrome nicht vorhanden; GW_TEST_BROWSER setzen')
class EditorPrototype(unittest.TestCase):
    def browser(self, query, page=DEMO):
        with tempfile.TemporaryDirectory() as profile:
            r = subprocess.run([BROWSER, '--headless', '--no-sandbox', '--disable-gpu',
                '--user-data-dir=' + profile, '--virtual-time-budget=6000', '--dump-dom',
                page.as_uri() + query], capture_output=True, text=True, timeout=45)
        self.assertEqual(r.returncode, 0, r.stderr[-1000:])
        return r.stdout

    def test_speichern_sperre_vorschau_und_abschnittswechsel(self):
        html = self.browser('?test=1')
        result = re.search(r'<p id="test-result"[^>]*>(.*?)</p>', html)
        self.assertIsNotNone(result)
        self.assertTrue(result.group(1).startswith('PASS:'), result.group(1))

    def test_einfache_textansicht_laesst_textfeld_unveraendert(self):
        html = self.browser('?editor=text')
        self.assertNotIn('class="EasyMDEContainer"', html)
        self.assertNotIn('src="vendor/easymde.min.js"', html)
        self.assertIn('id="gw-ms"', html)

    @unittest.skipUnless(os.environ.get('GW_TEST_PLAYWRIGHT'), 'Echter IndexedDB-Test: GW_TEST_PLAYWRIGHT auf playwright-core setzen')
    def test_abschnittsformular_online_offline_und_rechte(self):
        runner = ROOT / 'apps' / 'web' / 'tests' / 'editor-browser.cjs'
        page = ROOT / 'apps' / 'web' / 'tests' / 'editor-flow.html'
        r = subprocess.run([shutil.which('node'), str(runner), page.as_uri()], capture_output=True, text=True, timeout=45)
        self.assertEqual(r.returncode, 0, r.stderr)
        html = r.stdout
        result = re.search(r'<p id="result"[^>]*>(.*?)</p>', html, re.S)
        self.assertIsNotNone(result)
        self.assertTrue(result.group(1).startswith('PASS:'), result.group(1))
