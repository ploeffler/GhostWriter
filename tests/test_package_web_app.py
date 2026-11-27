"""Veröffentlichung der eigenen Web-App (#662): nur Laufzeitdateien, keine Quellen, Tests oder Buchinhalte; Workflows binden sie ein."""
import importlib.util
import tempfile
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location('package_web_app', ROOT / 'scripts' / 'package_web_app.py')
pkg = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pkg)


class PackageWebApp(unittest.TestCase):
    def test_nur_laufzeitdateien(self):
        with tempfile.TemporaryDirectory() as d:
            out = Path(d) / 'app'
            pkg.package(out)
            got = sorted(str(p.relative_to(out)) for p in out.rglob('*') if p.is_file())
            self.assertEqual(got, sorted(pkg.FILES + ['.nojekyll']))
            for name in got:
                self.assertFalse(name.endswith(('.src.html', '.src.js')) or 'test' in name or name in ('build.py', 'README.md'), name)
            self.assertIn('Service Worker', (out / 'sw.js').read_text(encoding='utf-8'))

    def test_bindet_service_worker_relativ_und_ohne_buchinhalt(self):
        html = (ROOT / 'apps' / 'web' / 'index.html').read_text(encoding='utf-8')
        self.assertIn('navigator.serviceWorker.register("sw.js")', html)          # relativ: läuft unter /app/
        self.assertIn('rel="manifest" href="manifest.webmanifest"', html)
        manifest = (ROOT / 'apps' / 'web' / 'manifest.webmanifest').read_text(encoding='utf-8')
        self.assertIn('"start_url": "./"', manifest); self.assertIn('"scope": "./"', manifest)

    def test_ausgabeordner_nicht_in_den_quellen(self):
        for bad in (ROOT, ROOT / 'apps' / 'web', ROOT / 'apps' / 'web' / 'x', ROOT / 'docs' / 'x'):
            with self.assertRaises(ValueError):
                pkg.package(bad)

    def test_workflows(self):
        pages = yaml.safe_load((ROOT / '.github/workflows/pages.yml').read_text(encoding='utf-8'))
        inputs = pages[True]['workflow_dispatch']['inputs'] if True in pages else pages['on']['workflow_dispatch']['inputs']
        self.assertEqual(inputs['web_app']['default'], False)       # nie ohne ausdrückliche Wahl
        self.assertEqual(inputs['docs_ref']['default'], '')
        text = (ROOT / '.github/workflows/pages.yml').read_text(encoding='utf-8')
        self.assertIn('scripts/package_web_app.py --output "$TARGET/app"', text)
        self.assertIn('if: inputs.web_app', text)
        self.assertIn("github.ref == 'refs/heads/main'", text)
        self.assertNotIn('inputs.docs_ref }}"', text.replace('DOCS_REF: ${{ inputs.docs_ref }}', ''))   # Eingabe nie direkt in die Shell
        release = (ROOT / '.github/workflows/release.yml').read_text(encoding='utf-8')
        self.assertIn('scripts/package_web_app.py --output build/pages/app', release)


if __name__ == '__main__':
    unittest.main()
