"""Claude-Web-App wird aus Teilen gebaut (#662): index.html passt zu den Quellen in apps/shared und apps/claude."""
import importlib.util
import re
import unittest
from pathlib import Path

APP = Path(__file__).resolve().parent.parent / 'apps' / 'claude'
spec = importlib.util.spec_from_file_location('app_build', APP / 'build.py')
app_build = importlib.util.module_from_spec(spec)
spec.loader.exec_module(app_build)


class AppBuild(unittest.TestCase):
    def test_index_html_passt_zu_den_quellen(self):
        self.assertEqual((APP / 'index.html').read_text(encoding='utf-8'), app_build.build(),
                         'python3 apps/claude/build.py ausführen (index.html nie von Hand ändern)')

    def test_alle_teile_eingebunden(self):
        src = (APP / 'index.src.html').read_text(encoding='utf-8')
        used = {(APP / m).resolve() for m in re.findall(r'^@@include (\S+)@@$', src, re.M)}
        files = {p.resolve() for p in (APP.parent / 'shared').iterdir()} | {(APP / 'ports-claude.js').resolve(), (APP / 'boot-claude.js').resolve()}
        self.assertEqual(sorted(map(str, files - used)), [], 'Teil nicht in index.src.html eingebunden')
        self.assertEqual(sorted(map(str, used - files)), [])

    def test_shared_kennt_keinen_konnektor(self):
        for p in sorted((APP.parent / 'shared').glob('*.js')):
            self.assertNotRegex(p.read_text(encoding='utf-8'), r'[^\w.]call\("[a-z_]+"', p.name + ': Konnektor-Aufruf gehört nach apps/claude/ports-claude.js')


if __name__ == '__main__':
    unittest.main()
