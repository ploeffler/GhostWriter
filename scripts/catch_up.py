#!/usr/bin/env python3
"""Vollständigen Lesestand für Einpflegen/Nachziehen vorbereiten (ohne Schreibzugriff)."""
import argparse
import hashlib
import json
from pathlib import Path

import yaml

from chapter_revision import readiness
from render_view import section_file


def prepare(base, scope='book', material=''):
    base = Path(base)
    config_path = base / 'ghostwriter.yml'
    config_text = config_path.read_text(encoding='utf-8')
    config = yaml.safe_load(config_text)
    chapters = config['structure']['chapters']
    selected = [(i, ch) for i, ch in enumerate(chapters, 1)
                if scope in ('book', 'buch') or str(i) == scope or ch['id'] == scope]
    if not selected:
        raise ValueError('Kapitel nicht gefunden')
    result = {'scope': scope, 'material': material, 'chapters': [], 'issues': [],
              'config_sha256': hashlib.sha256(config_text.encode()).hexdigest(),
              'instructions': 'docs/NACHZIEHEN.md', 'automatic_research_or_editing': False}
    for ci, chapter in selected:
        row = {'id': chapter['id'], 'number': ci, 'title': chapter['title'], 'sections': [],
               'revision_readiness': readiness(base, chapter)}
        for si, section in enumerate(chapter.get('sections') or [], 1):
            entry = {'id': section['id'], 'number': f'{ci}.{si}', 'path': section['path']}
            try:
                raw = (base / section['path']).read_text(encoding='utf-8')
                head, goal, summary, manuscript = section_file(base, section)
                if not isinstance(head, dict):
                    raise ValueError('ungültiger Abschnittskopf')
                entry.update(status=head.get('status'), goal=goal, summary=summary,
                             document=raw, manuscript=manuscript,
                             sha256=hashlib.sha256(raw.encode()).hexdigest())
            except (OSError, ValueError, AttributeError, TypeError, yaml.YAMLError):
                result['issues'].append({'section': section['id'], 'reason': 'Abschnitt nicht lesbar'})
            row['sections'].append(entry)
        result['chapters'].append(row)
    result['complete'] = not result['issues'] and bool(selected) and all(ch['sections'] for ch in result['chapters'])
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('project')
    parser.add_argument('--scope', default='book', help='book, Kapitelnummer oder stabile Kapitel-ID')
    parser.add_argument('--material', type=Path, help='Datei mit neuem Material; optional beim Nachziehen')
    args = parser.parse_args()
    try:
        material = args.material.read_text(encoding='utf-8') if args.material else ''
        result = prepare(args.project, args.scope, material)
    except (OSError, ValueError, KeyError, TypeError, yaml.YAMLError) as error:
        parser.error(str(error))
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result['complete'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
