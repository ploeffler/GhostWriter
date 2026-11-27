"""Eigene Web-App (#662, Schritt 3): gebaut aus apps/shared, eigener Anschluss ohne Konnektor."""
import importlib.util
import json
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
        self.assertEqual({p.name for p in used - shared}, {'ports-web.js', 'net-web.js', 'merge3.js', 'outbox-web.js', 'konflikt-web.js', 'fehler-web.js', 'einstellungen-web.js', 'boot-web.js', 'web.css'})

    def test_kein_claude_anschluss_und_kein_fremder_host(self):
        for name in ('ports-web.js', 'boot-web.js'):
            text = (WEB / name).read_text(encoding='utf-8')
            self.assertNotIn('window.claude', text, name)
            self.assertNotIn('S.mcp.callTool', text, name)
        ports = (WEB / 'ports-web.js').read_text(encoding='utf-8')
        self.assertEqual(sorted(set(re.findall(r'https://[a-z.]+', ports.split('/* Startseite')[0]))), ['https://api.github.com'])

    def test_fehlerberichte_ohne_persoenliches(self):
        # die Meldung geht nur an das Hauptrepository (feste Vorgabe oder upstream aus der Bibliothek), nie an ein Buch-Repository
        text = (WEB / 'fehler-web.js').read_text(encoding='utf-8')
        self.assertIn('https://github.com/${errUpstream()}/issues/new', text)
        self.assertIn('UPSTREAM_DEFAULT = "ploeffler/GhostWriter"', text)
        self.assertNotIn('S.owner', text.split('function errIssueUrl')[1].split('function errReport')[0])
        matrix = json.loads((WEB / 'faehigkeiten.json').read_text(encoding='utf-8'))
        for f in matrix['functions']:
            for k in ('name', 'reason', 'fallback'):
                self.assertTrue(f[k]['de'] and f[k]['en'], f['id'] + ': ' + k + ' DE/EN')
        self.assertIn('faehigkeiten.json', (WEB / 'sw.js').read_text(encoding='utf-8'))
        self.assertIn('GhostWriter Web-App', (WEB / 'index.html').read_text(encoding='utf-8'))
        self.assertNotIn('@@APP_VERSION@@', (WEB / 'index.html').read_text(encoding='utf-8'))

    def test_token_nie_in_der_seite(self):
        html = (WEB / 'index.html').read_text(encoding='utf-8')
        self.assertNotRegex(html, r'github_pat_[A-Za-z0-9_]{20,}|gh[pousr]_[A-Za-z0-9]{20,}')

    def test_pwa_dateien(self):
        manifest = json.loads((WEB / 'manifest.webmanifest').read_text(encoding='utf-8'))
        self.assertEqual((manifest['start_url'], manifest['scope'], manifest['display']), ('./', './', 'standalone'))
        sizes = {i['sizes'] for i in manifest['icons']}
        self.assertTrue({'192x192', '512x512'} <= sizes)
        for icon in manifest['icons']:
            self.assertTrue((WEB / icon['src']).is_file(), icon['src'])
        sw = (WEB / 'sw.js').read_text(encoding='utf-8')
        for f in re.findall(r'"([^"]+\.(?:html|js|css|png|svg|webmanifest))"', sw.split('const SHELL = ')[1].split(';')[0]):
            self.assertTrue((WEB / f).is_file(), f + ' ist in der App-Hülle des Service Workers, fehlt aber')
        html = (WEB / 'index.html').read_text(encoding='utf-8')
        self.assertIn('rel="manifest" href="manifest.webmanifest"', html)
        self.assertNotIn('@@VERSION@@', sw)

    @unittest.skipUnless(shutil.which('node'), 'Node nicht vorhanden')
    def test_node_tests(self):
        for name in ('ports-web.test.cjs', 'sw.test.cjs', 'outbox.test.cjs', 'merge3.test.cjs', 'fehler.test.cjs'):
            r = subprocess.run(['node', str(WEB / 'tests' / name)], capture_output=True, text=True, timeout=60)
            self.assertEqual(r.returncode, 0, name + '\n' + r.stdout + r.stderr)


if __name__ == '__main__':
    unittest.main()
