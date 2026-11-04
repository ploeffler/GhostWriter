#!/usr/bin/env python3
"""Prüft, ob ein Kapitel vollständig für die redaktionelle Überarbeitung vorliegt."""
import argparse
import json
import sys
from pathlib import Path

import yaml

from render_view import section_file


READY_STATES = frozenset({'writing', 'revision', 'fact_check', 'ready_for_approval', 'approved'})
EMPTY_TEXTS = frozenset({'', 'Noch nicht begonnen.'})


def readiness(base, chapter):
    """Nur tatsächlicher Text in jedem Abschnitt und ein Zustand ab Schreiben genügen."""
    missing = []
    sections = chapter.get('sections') or []
    if not sections:
        return {'ready': False, 'issues': [{'section': None, 'reason': 'keine Abschnitte'}]}
    for section in sections:
        sid = section['id']
        try:
            head, _, _, manuscript = section_file(base, section)
            if not isinstance(head, dict):
                raise ValueError('ungültiger Abschnittskopf')
        except (OSError, ValueError, AttributeError, TypeError, yaml.YAMLError):
            missing.append({'section': sid, 'reason': 'Abschnitt nicht lesbar'})
            continue
        if head.get('status') not in READY_STATES:
            missing.append({'section': sid, 'reason': 'Status vor Schreiben oder unbekannt'})
        if manuscript.strip() in EMPTY_TEXTS:
            missing.append({'section': sid, 'reason': 'Manuskript fehlt'})
    return {'ready': not missing, 'issues': missing}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('project')
    parser.add_argument('chapter', help='Kapitelnummer oder Kapitel-ID')
    parser.add_argument('--json', action='store_true')
    args = parser.parse_args()
    base = Path(args.project)
    config = yaml.safe_load((base / 'ghostwriter.yml').read_text(encoding='utf-8'))
    chapters = config['structure']['chapters']
    matches = ([chapters[int(args.chapter) - 1]] if args.chapter.isdigit() and 1 <= int(args.chapter) <= len(chapters)
               else [c for c in chapters if c['id'] == args.chapter])
    if not matches:
        parser.error('Kapitel nicht gefunden')
    result = readiness(base, matches[0])
    if args.json:
        print(json.dumps(result, ensure_ascii=False))
    elif result['ready']:
        print('Kapitelüberarbeitung verfügbar: Alle Abschnitte enthalten Manuskripttext.')
    else:
        print('Kapitelüberarbeitung noch nicht verfügbar:')
        for issue in result['issues']:
            print(f'  - {issue["section"] or "Kapitel"}: {issue["reason"]}')
    return 0 if result['ready'] else 1


if __name__ == '__main__':
    sys.exit(main())
