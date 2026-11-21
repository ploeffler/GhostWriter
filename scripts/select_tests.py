#!/usr/bin/env python3
"""Tests für einen Pull Request nach den geänderten Dateien auswählen (#439).

Spart Actions-Minuten: Ein Pull Request, der nur Doku oder einzelne Skripte ändert,
lässt nur die Tests laufen, die diese Dateien betreffen, und installiert die
Satzpakete (TeX, pandoc) nur, wenn ein ausgewählter Test sie braucht.

Im Zweifel die volle Suite: bei Programmdateien ohne zugeordneten Test, bei
Workflows, Schemas, Vorlagen, Manifest, START.md, Testdaten und gelöschten Dateien.
Auf dem Standard-Branch läuft immer die volle Suite (validate.yml).

  python scripts/select_tests.py --files <datei-mit-pfaden> [--removed <datei>] [--github-output <datei>]

Ausgabe: mode=full|subset, tests=<module, durch Leerzeichen>, satz=0|1.
"""
import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TESTS = ROOT / 'tests'

# Diese Dateien betreffen Ablauf, Daten oder Verteilung so breit, dass die volle Suite läuft.
FULL_FILES = {'START.md', 'CLAUDE.md', 'AGENTS.md', 'workflow.yml', 'ghostwriter-manifest.yml',
              'requirements.txt'}
FULL_PREFIXES = ('.github/', 'schemas/', 'templates/', 'tests/data/', 'tests/fixtures/', 'testdata/',
                 'scripts/docsite/', '.claude/', 'starter/')
SATZ = re.compile(r'pandoc|xelatex|pdftotext|qpdf')
DOC_REF = re.compile(r"""docs/|['"]docs['"]""")
FULL_SHARE = 0.6   # mehr als 60 % der Tests ausgewählt: gleich alles


def test_files():
    return sorted(TESTS.glob('test_*.py'))


def doc_tests(files):
    """Tests, die Dateien unter docs/ lesen oder prüfen."""
    return {f.stem for f in files if DOC_REF.search(f.read_text(encoding='utf-8'))}


def users_of(module, files):
    """Tests, die ein Skript importieren, aufrufen oder nennen."""
    pattern = re.compile(rf'\b{re.escape(module)}\b')
    return {f.stem for f in files if pattern.search(f.read_text(encoding='utf-8'))}


def importers(module, scripts=None):
    """Das Skript selbst und alle Skripte, die es direkt oder über andere importieren."""
    scripts = sorted((ROOT / 'scripts').glob('*.py')) if scripts is None else scripts
    text = {f.stem: f.read_text(encoding='utf-8') for f in scripts}
    found, todo = {module}, [module]
    while todo:
        name = todo.pop()
        pattern = re.compile(rf'^\s*(?:from\s+{re.escape(name)}\s+import|import\s+(?:[\w, ]*,\s*)?{re.escape(name)}\b)', re.M)
        for stem, body in text.items():
            if stem not in found and pattern.search(body):
                found.add(stem)
                todo.append(stem)
    return found


def is_doc(path):
    return path.endswith(('.md', '.svg', '.png', '.jpg')) and '/' not in path.strip('/') \
        or path.startswith(('docs/', 'assets/'))


def select(changed, removed=(), files=None):
    """Liefert (mode, tests, satz) für die geänderten Pfade."""
    files = test_files() if files is None else files
    known = {f.stem for f in files}
    if not changed or removed:
        return 'full', [], True
    chosen = set()
    for path in changed:
        name = Path(path).name
        if path in FULL_FILES or path.startswith(FULL_PREFIXES):
            return 'full', [], True
        if path.startswith('tests/') and name.startswith('test_') and name.endswith('.py'):
            chosen.add(Path(path).stem)
        elif path.startswith('scripts/') and path.endswith('.py') and path.count('/') == 1:
            stem = Path(path).stem
            users = set()
            for module in importers(stem):
                users |= users_of(module, files)
            if not users_of(stem, files):
                return 'full', [], True
            chosen |= users
        elif is_doc(path):
            chosen |= doc_tests(files)
        else:
            return 'full', [], True
    chosen &= known
    if not chosen or len(chosen) > FULL_SHARE * len(known):
        return 'full', [], True
    by_stem = {f.stem: f for f in files}
    satz = any(SATZ.search(by_stem[t].read_text(encoding='utf-8')) for t in chosen)
    return 'subset', sorted(chosen), satz


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--files', required=True, help='Datei mit den geänderten Pfaden, einer je Zeile')
    ap.add_argument('--removed', help='Datei mit gelöschten Pfaden, einer je Zeile')
    ap.add_argument('--github-output', help='Ergebnis zusätzlich an diese Datei anhängen ($GITHUB_OUTPUT)')
    a = ap.parse_args(argv)
    read = lambda p: [l.strip() for l in Path(p).read_text(encoding='utf-8').splitlines() if l.strip()] if p else []
    mode, tests, satz = select(read(a.files), read(a.removed))
    lines = [f'mode={mode}', f'tests={" ".join(tests)}', f'satz={int(satz)}']
    print('\n'.join(lines))
    if mode == 'subset':
        print(f'{len(tests)} von {len(test_files())} Testdateien', file=sys.stderr)
    if a.github_output:
        with open(a.github_output, 'a', encoding='utf-8') as fh:
            fh.write('\n'.join(lines) + '\n')
    return 0


if __name__ == '__main__':
    sys.exit(main())
