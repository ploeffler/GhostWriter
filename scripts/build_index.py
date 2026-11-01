#!/usr/bin/env python3
"""Schreibt die Übersichtsdatei ghostwriter-index.json eines Buchprojekts.

Aufruf:
  python scripts/build_index.py <projektordner>           schreibt die Datei
  python scripts/build_index.py <projektordner> --check   meldet nur, ob sie fehlt oder veraltet ist

Die Datei fasst je Kapitel und Abschnitt Status, Freigaben, Kosten-Summen und
Markerzahlen zusammen, dazu Projektsumme und Auflage. Sie enthält keinen
Manuskripttext und keine Zeitstempel, damit sie sich nur ändert, wenn sich
der Inhalt ändert. Projektübersicht und Kapitelansicht werden daraus befüllt
(templates/ui/BEFUELLUNG.md, „Übersichtsdatei“); das Abschnittsformular liest
weiter die Abschnittsdatei.

Ohne Kapitel (Starter vor dem Einrichten) wird keine Datei geschrieben.

API-Schlüssel: Ist die Umgebungsvariable SECRETS_JSON gesetzt (in der Action:
toJSON(secrets)), steht unter "secrets" für jedes Secret, das die eigenen
KI-Dienste brauchen, ob es im Repository hinterlegt ist (true/false). Nur die
Namen werden gelesen, nie die Werte. Ohne SECRETS_JSON bleibt der bisherige
Eintrag stehen.
"""
import json
import os
import re
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
from render_view import (combine, cost_entries, load, marker_counts, money, section_costs,  # noqa: E402
                         section_file, total)

INDEX_NAME = 'ghostwriter-index.json'
FORMAT = 1


def cost(amount, estimated):
    return {'amount': None if amount is None else float(round(amount, 4)), 'estimated': bool(estimated),
            'text': money(amount, estimated)}


def build(base, config):
    p = config['project']
    chapters, parts = [], []
    for ci, ch in enumerate(config['structure']['chapters'], start=1):
        sections, ch_parts, ch_markers, approved = [], [], dict.fromkeys(('anekdote', 'quelle', 'medizin', 'recht'), 0), 0
        for si, s in enumerate(ch['sections'], start=1):
            head, goal, summary, ms = section_file(base, s)
            a, e = total(section_costs(base, ch, s))
            ch_parts.append((a, e))
            counts = marker_counts(ms)
            for k, v in counts.items():
                ch_markers[k] += v
            approved += head['status'] == 'approved'
            sections.append({'id': s['id'], 'number': f'{ci}.{si}', 'title': s['title'], 'path': s['path'],
                             'status': head['status'], 'fact_check': head['fact_check'],
                             'approvals': {'writing': bool(head['approvals']['writing']),
                                           'section': bool(head['approvals']['section'])},
                             'has_goal': bool(goal), 'has_summary': bool(summary),
                             'cost': cost(a, e), 'markers': counts})
        a, e = combine(ch_parts)
        parts.append((a, e))
        readme = base / ch['path'] / 'README.md'
        sub = re.search(r'(?m)^\*([^*].*)\*$', readme.read_text(encoding='utf-8')) if readme.is_file() else None
        chapters.append({'id': ch['id'], 'number': ci, 'title': ch['title'], 'subtitle': sub.group(1) if sub else '',
                         'path': ch['path'], 'status': ch['status'],
                         'sections_total': len(sections), 'sections_approved': approved,
                         'cost': cost(a, e), 'markers': ch_markers, 'sections': sections})
    parts.append(total(cost_entries(base, base / 'costs' / 'project.yml')))
    a, e = combine(parts)
    wf = config.get('workflow') or {}
    return {'format': FORMAT,
            'project': {'title': p.get('title') or p.get('working_title') or '', 'title_short': p.get('title_short') or '',
                        'author': p.get('author') or '', 'current_edition': p.get('current_edition') or 0,
                        'cost': cost(a, e)},
            'workflow': {'current_chapter_id': wf.get('current_chapter_id') or '',
                         'current_section_id': wf.get('current_section_id') or ''},
            'chapters': chapters}


def render(data):
    """JSON mit einem Abschnitt je Zeile: kurz zum Lesen im Chat, gut lesbar in Diffs."""
    one = lambda v: json.dumps(v, ensure_ascii=False, separators=(',', ':'))
    head = {k: v for k, v in data.items() if k != 'chapters'}
    out = ['{' + one(head)[1:-1] + ',', '"chapters":[']
    for i, ch in enumerate(data['chapters']):
        meta = {k: v for k, v in ch.items() if k != 'sections'}
        out.append('{' + one(meta)[1:-1] + ',"sections":[')
        out += [one(s) + (',' if j < len(ch['sections']) - 1 else '') for j, s in enumerate(ch['sections'])]
        out.append(']}' + (',' if i < len(data['chapters']) - 1 else ''))
    out.append(']}')
    return '\n'.join(out) + '\n'


def secret_names(config):
    """Namen der GitHub-Secrets, die die eigenen KI-Dienste mit Zugang „API-Schlüssel“ brauchen."""
    root = Path(__file__).resolve().parent.parent
    try:
        catalog = yaml.safe_load((root / 'providers.yml').read_text(encoding='utf-8')) or {}
    except OSError:
        catalog = {}
    entries = {s['id']: s for sec in ('providers', 'search_tools', 'queue_agents') for s in catalog.get(sec) or []}
    ap = config.get('ai_providers') or {}
    names = set()
    for sid, cfg in (ap.get('services') or {}).items():
        if sid not in (ap.get('available') or []) or (cfg or {}).get('access') != 'api':
            continue
        s = entries.get(sid, {'id': sid})
        names.add((cfg or {}).get('api_key_secret') or s.get('api_key_secret')
                  or re.sub(r'[^A-Z0-9]+', '_', sid.upper()) + '_API_KEY')
        if s.get('api_key_alt'):
            names.add(s['api_key_alt'])
    return sorted(names)


def secrets_presence(config, current_text):
    raw = os.environ.get('SECRETS_JSON')
    if raw is None:
        try:
            return json.loads(current_text).get('secrets') if current_text else None
        except ValueError:
            return None
    try:
        have = set(json.loads(raw))
    except ValueError:
        have = set()
    return {n: n in have for n in secret_names(config)}


def main(argv):
    if len(argv) < 2 or argv[1] in ('-h', '--help'):
        print(__doc__)
        return 2
    base, config = load(argv[1])
    check = '--check' in argv[2:]
    path = base / INDEX_NAME
    if not config['structure']['chapters']:
        if path.is_file():
            print(f'{path}: Projekt ohne Kapitel, Übersichtsdatei sollte fehlen')
            return 1 if check else 0
        print(f'{base}: keine Kapitel, keine Übersichtsdatei')
        return 0
    current = path.read_text(encoding='utf-8') if path.is_file() else None
    data = build(base, config)
    secrets = secrets_presence(config, current)
    if secrets:
        data['secrets'] = secrets
    text = render(data)
    if check:
        if current == text:
            print(f'✓ {path}')
            return 0
        print(f'{path}: {"fehlt" if current is None else "veraltet"}; neu erzeugen mit python scripts/build_index.py {base}')
        return 1
    if current != text:
        path.write_text(text, encoding='utf-8')
        print(f'{path}: geschrieben')
    else:
        print(f'{path}: unverändert')
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
