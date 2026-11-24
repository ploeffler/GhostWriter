#!/usr/bin/env python3
"""Release veröffentlichen (#488, Phase 2): Prüfungen und Hilfen für den Workflow.

Unterbefehle:
  check   Freigabe prüfen: Version = Manifest = Bestätigung, Release Notes vorhanden.
  tag     Tag-Namen zur Version ausgeben (0.9.0 -> v0.9, 1.0.1 -> v1.0.1).
  notes   Release Notes der Version aus docs/UPDATES.md ausgeben.
  site    Öffentliche Website auf die Version prüfen (build-info.json und Seiten je Sprache).

Veröffentlicht selbst nichts; Tag, Release und Website legt der Workflow
.github/workflows/release.yml an.
"""
import argparse
import json
import re
import sys
import urllib.request
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
VERSION_RE = re.compile(r'^\d+\.\d+\.\d+$')


def manifest_version(root=ROOT):
    return str(yaml.safe_load((root / 'ghostwriter-manifest.yml').read_text(encoding='utf-8'))['version'])


def tag_name(version):
    """Bisherige Tags heißen v0.7, v0.8, v0.9; nur ein Patch-Stand bekommt drei Stellen."""
    if not VERSION_RE.match(version):
        raise ValueError(f'Version „{version}“ hat nicht die Form X.Y.Z')
    major, minor, patch = version.split('.')
    return f'v{major}.{minor}' if patch == '0' else f'v{version}'


def notes(version, root=ROOT, lang='de'):
    """Absatz „**<version>:** …“ bzw. „**<version>** …“ aus docs/UPDATES.md (bzw. UPDATES.en.md)."""
    name = 'UPDATES.md' if lang == 'de' else 'UPDATES.en.md'
    text = (root / 'docs' / name).read_text(encoding='utf-8')
    for paragraph in re.split(r'\n\s*\n', text):
        head = paragraph.strip()
        if head.startswith(f'**{version}:**') or head.startswith(f'**{version}** '):
            return paragraph.strip()
    return None


def check(version, confirm, root=ROOT):
    """Liste der Gründe, warum nicht veröffentlicht werden darf (leer = darf)."""
    problems = []
    if not VERSION_RE.match(version or ''):
        problems.append(f'Version „{version}“ hat nicht die Form X.Y.Z')
    current = manifest_version(root)
    if version != current:
        problems.append(f'Version {version} passt nicht zum Manifest ({current})')
    if confirm != version:
        problems.append(f'Bestätigung „{confirm}“ stimmt nicht mit der Version {version} überein')
    for lang in ('de', 'en'):
        if VERSION_RE.match(version or '') and not notes(version, root, lang):
            problems.append(f'Release Notes für {version} fehlen in docs/UPDATES{"" if lang == "de" else ".en"}.md')
    return problems


def fetch(url):
    with urllib.request.urlopen(url, timeout=30) as response:  # nosec - öffentliche Seite
        return response.read().decode('utf-8')


def check_site(base, version, get=fetch):
    """Öffentliche Dokumentation prüfen; liefert Liste der Probleme."""
    base = base.rstrip('/')
    problems = []
    try:
        info = json.loads(get(f'{base}/build-info.json'))
        if str(info.get('version')) != version:
            problems.append(f'Website zeigt Version {info.get("version")} statt {version}')
    except Exception as exc:  # noqa: BLE001 - jeder Fehler ist ein Befund
        problems.append(f'build-info.json nicht lesbar: {exc}')
    for lang in ('de', 'en'):
        try:
            page = get(f'{base}/{lang}/index.html')
            if f'<strong>{version}</strong>' not in page:
                problems.append(f'Startseite {lang} zeigt nicht Version {version}')
        except Exception as exc:  # noqa: BLE001
            problems.append(f'Startseite {lang} nicht erreichbar: {exc}')
    return problems


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest='cmd', required=True)
    c = sub.add_parser('check'); c.add_argument('--version', required=True); c.add_argument('--confirm', required=True)
    t = sub.add_parser('tag'); t.add_argument('--version', required=True)
    n = sub.add_parser('notes'); n.add_argument('--version', required=True)
    s = sub.add_parser('site'); s.add_argument('--version', required=True)
    s.add_argument('--url', default='https://ploeffler.github.io/GhostWriter/documentation')
    args = parser.parse_args(argv)
    if args.cmd == 'tag':
        print(tag_name(args.version)); return 0
    if args.cmd == 'notes':
        de, en = notes(args.version), notes(args.version, lang='en')
        if not de:
            print(f'Release Notes für {args.version} fehlen', file=sys.stderr); return 1
        print(de + ('\n\n---\n\n' + en if en else '')); return 0
    problems = check(args.version, args.confirm) if args.cmd == 'check' else check_site(args.url, args.version)
    for problem in problems:
        print(f'- {problem}', file=sys.stderr)
    if problems:
        return 1
    print('in Ordnung')
    return 0


if __name__ == '__main__':
    sys.exit(main())
