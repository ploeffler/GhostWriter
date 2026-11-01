#!/usr/bin/env python3
"""Gibt die Angaben einer Auflage für die Action „Auflage veröffentlichen“ aus (#16).

Aufruf:
  python scripts/edition_info.py <projektordner> [--before <commit>] [--edition N]

Ausgabe (für $GITHUB_OUTPUT): build=true|false, edition, tag, name, notes, reason.

build=true, wenn diese Änderung project.current_edition erhöht hat (Vergleich mit
--before, dem Stand vor dem Push) oder --edition ausdrücklich angegeben ist. Ein
Push, der die Auflage nicht ändert, baut nichts. Ob es den Tag schon gibt, prüft
die Action selbst (veröffentlichte Auflagen bleiben unverändert).
"""
import argparse
import subprocess
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
from render_view import load, tag_slug  # noqa: E402


def edition_at(commit):
    r = subprocess.run(['git', 'show', f'{commit}:ghostwriter.yml'], text=True, capture_output=True)
    if r.returncode:
        return 0
    return ((yaml.safe_load(r.stdout) or {}).get('project') or {}).get('current_edition') or 0


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument('project')
    ap.add_argument('--before')
    ap.add_argument('--edition', type=int)
    args = ap.parse_args(argv[1:])
    base, config = load(args.project)
    p = config['project']
    now = p.get('current_edition') or 0
    if args.edition:
        edition, build, reason = args.edition, True, 'von Hand angefordert'
    else:
        before = edition_at(args.before) if args.before and set(args.before) != {'0'} else None
        edition = now
        build = before is not None and now > before
        reason = (f'Auflage von {before} auf {now} erhöht' if build else
                  'Auflage unverändert' if before is not None else 'kein Vergleichsstand')
    br = yaml.safe_load((ROOT / 'workflow.yml').read_text(encoding='utf-8'))['book_releases']
    short = p.get('title_short') or p.get('title') or p.get('working_title') or 'Ohne Titel'
    out = {'build': 'true' if build and edition > 0 else 'false', 'edition': edition,
           'tag': br['tag_pattern'].format(title_short_slug=tag_slug(short), edition=edition),
           'name': br['name_pattern'].format(title_short=short, edition=edition),
           'notes': f'editions/auflage-{edition}.md', 'reason': reason}
    for k, v in out.items():
        print(f'{k}={v}')
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
