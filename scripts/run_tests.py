#!/usr/bin/env python3
"""Testmodule parallel ausführen und ihre Laufzeit melden (#485).

Die Suite braucht nacheinander rund 10 Minuten, fast die Hälfte davon in wenigen
Modulen, die echte PDFs setzen. Jedes Modul läuft hier in einem eigenen Prozess,
so viele gleichzeitig wie Kerne da sind; Module mit Satz (pandoc, xelatex) zuerst,
damit die langen nicht am Ende allein laufen. Am Schluss stehen die langsamsten
Module, damit jeder volle Lauf zugleich die Messung ist.

  python scripts/run_tests.py                     # alle tests/test_*.py
  python scripts/run_tests.py test_cover test_x   # nur diese Module
  python scripts/run_tests.py --jobs 1            # nacheinander

Ergebnis: 0, wenn alle Module grün sind; sonst 1 und die Ausgabe der roten Module.
"""
import argparse
import os
import re
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TESTS = ROOT / 'tests'
SATZ = re.compile(r'pandoc|xelatex|build_edition|build_cover|pdftotext')


def order(modules):
    """Module mit Satz zuerst, sonst die größeren Dateien zuerst."""
    def key(name):
        text = (TESTS / f'{name}.py').read_text(encoding='utf-8')
        return (-len(SATZ.findall(text)), -len(text), name)
    return sorted(modules, key=key)


def run_module(name):
    env = dict(os.environ, PYTHONPATH=os.pathsep.join(filter(None, [str(TESTS), os.environ.get('PYTHONPATH')])))
    start = time.monotonic()
    r = subprocess.run([sys.executable, '-m', 'unittest', name], cwd=ROOT, env=env,
                       capture_output=True, text=True)
    return name, r.returncode, time.monotonic() - start, r.stdout + r.stderr


def count(output):
    m = re.search(r'^Ran (\d+) tests?', output, re.M)
    return int(m.group(1)) if m else 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('modules', nargs='*', help='Testmodule (z. B. test_cover); ohne Angabe alle')
    ap.add_argument('--jobs', type=int, default=os.cpu_count() or 1, help='gleichzeitige Prozesse (Vorgabe: Kerne)')
    ap.add_argument('--slowest', type=int, default=10, help='so viele langsamste Module melden')
    a = ap.parse_args(argv)
    modules = a.modules or [f.stem for f in sorted(TESTS.glob('test_*.py'))]
    missing = [m for m in modules if not (TESTS / f'{m}.py').is_file()]
    if missing:
        print('Unbekannte Testmodule: ' + ', '.join(missing), file=sys.stderr)
        return 1
    start = time.monotonic()
    with ThreadPoolExecutor(max_workers=max(1, a.jobs)) as pool:
        results = list(pool.map(run_module, order(modules)))
    wall = time.monotonic() - start
    failed = [r for r in results if r[1] != 0]
    for name, _, _, output in failed:
        print(f'\n===== {name}: rot =====\n{output}')
    total = sum(count(r[3]) for r in results)
    busy = sum(r[2] for r in results)
    print(f'\n{total} Tests in {len(results)} Modulen, {wall:.0f} s '
          f'(nacheinander wären es ~{busy:.0f} s, {a.jobs} Prozesse)')
    print('Langsamste Module:')
    for name, code, secs, _ in sorted(results, key=lambda r: -r[2])[:a.slowest]:
        print(f'  {secs:6.1f} s  {name}' + ('  (rot)' if code else ''))
    if failed:
        print(f'\n{len(failed)} Modul(e) rot: ' + ', '.join(r[0] for r in failed))
        return 1
    print('OK')
    return 0


if __name__ == '__main__':
    sys.exit(main())
