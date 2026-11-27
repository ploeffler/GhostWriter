#!/usr/bin/env python3
"""Packt die eigene Web-App (apps/web) für die GitHub Page: nur Laufzeitdateien, nie Quellen, Tests oder Buchinhalte (#662).

Aufruf:  python scripts/package_web_app.py --output build/pages/app
Veröffentlicht nichts; die Workflows „Beispielseiten veröffentlichen“ und „Release veröffentlichen“ rufen es auf und laden den Ordner mit hoch.
Geprüft wird vorher, dass apps/web/index.html, sw.js und vendor/ zu den Quellen passen (apps/web/build.py --check).
"""
import argparse
import importlib.util
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WEB = ROOT / 'apps' / 'web'
# Genau diese Dateien gehören zur veröffentlichten App; alles andere (Quellen, Tests, README, Bauskripte) nicht.
FILES = ['index.html', 'sw.js', 'manifest.webmanifest', 'faehigkeiten.json',
         'vendor/gw-lite.js', 'vendor/icons.css', 'vendor/js-yaml.min.js', 'vendor/js-yaml.LICENSE',
         'icons/icon-192.png', 'icons/icon-512.png', 'icons/icon-maskable-512.png', 'icons/icon-180.png', 'icons/icon.svg']


def check():
    spec = importlib.util.spec_from_file_location('web_build', WEB / 'build.py')
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    bad = [str(p.relative_to(WEB)) for p, text in mod.expected().items() if not p.is_file() or p.read_text(encoding='utf-8') != text]
    if bad:
        raise ValueError('apps/web passt nicht zu den Quellen: ' + ', '.join(bad) + ' (python3 apps/web/build.py)')


def package(output):
    output = Path(output).resolve()
    if output == ROOT or output == WEB or output.is_relative_to(ROOT / 'docs') or output.is_relative_to(WEB):
        raise ValueError('Ausgabeordner darf nicht in den Quellen liegen')
    check()
    missing = [f for f in FILES if not (WEB / f).is_file()]
    if missing:
        raise ValueError('Dateien der Web-App fehlen: ' + ', '.join(missing))
    if output.exists():
        shutil.rmtree(output)
    for f in FILES:
        target = output / f
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(WEB / f, target)
    (output / '.nojekyll').write_text('', encoding='utf-8')
    print(f'Web-App vorbereitet: {output} ({len(FILES)} Dateien)')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--output', type=Path, default=ROOT / 'build/pages/app')
    args = parser.parse_args()
    try:
        package(args.output)
    except ValueError as e:
        print('✗ ' + str(e))
        sys.exit(1)
