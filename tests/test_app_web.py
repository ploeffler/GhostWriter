"""Eigene Web-App (#662, Schritt 3): gebaut aus apps/shared, eigener Anschluss ohne Konnektor."""
import importlib.util
import re
import shutil
import subprocess
import unittest
from pathlib import Path

APPS = Path(__file__).resolve().parent.parent / 'apps'
WEB = APPS / 'web'
spec = importlib.util.spec_from_file_location('web_build', WEB / 'build.py')
web_build = importlib.util.module_from_spec(spec)
spec.loader.exec_module(web_build)


class WebApp(unittest.TestCase):
    def test_gebaut_und_aktuell(self):
        for path, text in web_build.expected().items():
            self.assertEqual(path.read_text(encoding='utf-8'), text, f'{path.name}: python3 apps/web/build.py ausführen')

    def test_alle_gemeinsamen_teile_eingebunden(self):
        src = (WEB / 'index.src.html').read_text(encoding='utf-8')
        used = {(WEB / m).resolve() for m in re.findall(r'^@@include (\S+)@@$', src, re.M)}
        shared = {p.resolve() for p in (APPS / 'shared').iterdir()}
        self.assertTrue(shared <= used, 'Die Web-App muss alle Teile aus apps/shared binden')
        self.assertEqual({p.name for p in used - shared}, {'ports-web.js', 'boot-web.js'})

    def test_kein_claude_anschluss_und_kein_fremder_host(self):
        for name in ('ports-web.js', 'boot-web.js'):
            text = (WEB / name).read_text(encoding='utf-8')
            self.assertNotIn('window.claude', text, name)
            self.assertNotIn('S.mcp.callTool', text, name)
        ports = (WEB / 'ports-web.js').read_text(encoding='utf-8')
        self.assertEqual(sorted(set(re.findall(r'https://[a-z.]+', ports.split('/* Startseite')[0]))), ['https://api.github.com'])

    def test_token_nie_in_der_seite(self):
        html = (WEB / 'index.html').read_text(encoding='utf-8')
        self.assertNotRegex(html, r'github_pat_|ghp_[A-Za-z0-9]{20}')

    @unittest.skipUnless(shutil.which('node'), 'Node nicht vorhanden')
    def test_anschluss_mit_nachgestelltem_fetch(self):
        r = subprocess.run(['node', str(WEB / 'tests' / 'ports-web.test.cjs')], capture_output=True, text=True, timeout=60)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)


if __name__ == '__main__':
    unittest.main()
