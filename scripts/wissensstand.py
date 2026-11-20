#!/usr/bin/env python3
"""Wissensstand eines Buchs als Arbeitswissen für den Chat (#369).

Beim Wechsel ins Buch liest der Assistent eine kompakte Übersicht dessen, was schon bekannt ist, damit er
nichts Besprochenes als neu einführt und verworfene Ideen nicht wieder vorschlägt:

- Buchwissen: Figuren (`characters/`, auch Figuren der Serie), Schauplätze (`story/places.yml`),
  Begriffe (Glossar des Buchs), Chronologie (`story/chronology.yml`) bzw. Zeitleiste (`story/timeline.yml`)
- Gesprächsstand: alle gesicherten Sitzungen unter `conversations/` (Entscheidungen, Brainstorming,
  Recherche, Planung, Entwürfe), jüngste zuerst, je mit Sitzung als Quelle

Nur lesend: das Skript schreibt nichts und legt keine Felder an. Einträge sind gekürzt; Details liest der
Assistent bei Bedarf in der genannten Datei nach. Nicht gemergte Sitzungen (Branch `ghostwriter/chat/<id>`)
sind nicht enthalten; dafür `Session laden` (docs/SESSION-SICHERUNG.md).

Aufruf:
  python3 scripts/wissensstand.py <buch> [--json] [--width 240] [--sessions 10]
"""
import argparse
import json
import re
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
from render_view import FRONTMATTER, glossary_entries, load, matter_items, section_file  # noqa: E402

TOPICS = ('decisions', 'brainstorming', 'research', 'planning', 'drafts')
TOPIC_DE = {'decisions': 'Entscheidungen', 'brainstorming': 'Brainstorming', 'research': 'Recherche',
            'planning': 'Planung und offene Punkte', 'drafts': 'Entwürfe'}
ROLE_DE = {'main': 'Hauptfigur', 'supporting': 'Nebenfigur', 'minor': 'Randfigur'}


def short(text, width):
    text = ' '.join(str(text or '').split())
    return text if len(text) <= width else text[:width - 1].rstrip() + '…'


def yaml_file(path, key):
    if not path.is_file():
        return []
    data = yaml.safe_load(path.read_text(encoding='utf-8')) or {}
    return data.get(key) or []


def characters(base, config):
    out = []
    for item in config.get('characters') or []:
        head = {}
        path = base / item.get('path', '') if item.get('path') else None
        if path and path.is_file():
            m = FRONTMATTER.match(path.read_text(encoding='utf-8'))
            head = (yaml.safe_load(m.group(1)) or {}) if m else {}
        out.append({'id': item.get('id') or head.get('id', ''), 'name': item.get('name') or head.get('name', ''),
                    'role': head.get('role', ''), 'short': head.get('short', ''),
                    'source': 'Serie' if '_series' in item else item.get('path', '')})
    return out


def places(base):
    return [{'id': p.get('id', ''), 'name': p.get('name', ''), 'aliases': p.get('aliases') or [],
             'kind': p.get('kind', ''), 'short': p.get('short', '')}
            for p in yaml_file(base / 'story' / 'places.yml', 'places')]


def glossary(base, config):
    item = next((i for _, i in matter_items(config) if i.get('kind') == 'glossary'), None)
    if not item or not (base / item['path']).is_file():
        return []
    ms = section_file(base, item)[3]
    return [{'term': t, 'text': e} for t, e in glossary_entries('' if ms == 'Noch nicht begonnen.' else ms)[1]]


def chronology(base):
    out = []
    for e in yaml_file(base / 'story' / 'chronology.yml', 'entries'):
        when = e.get('date_text') or e.get('date') or '–'.join(str(e.get(k)) for k in ('from', 'to') if e.get(k))
        out.append({'id': e.get('id', ''), 'when': str(when or ''), 'what': e.get('what', ''),
                    'status': e.get('status', '')})
    for e in yaml_file(base / 'story' / 'timeline.yml', 'events'):
        out.append({'id': e.get('id', ''), 'when': str(e.get('when') or ''), 'what': e.get('what', ''),
                    'section': e.get('section', '')})
    return out


def topic_text(value):
    """Themeninhalt als Text: Zeichenkette bleibt, Listen und Objekte werden kompakt zusammengefügt."""
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        return ' · '.join(topic_text(v) for v in value if v)
    if isinstance(value, dict):
        for key in ('text', 'summary', 'content'):
            if isinstance(value.get(key), str):
                return value[key]
        return ' · '.join(f'{k}: {topic_text(v)}' for k, v in value.items() if v and not str(k).startswith('_'))
    return '' if value is None else str(value)


def sessions(base, limit):
    root = base / 'conversations'
    if not root.is_dir() or root.is_symlink():
        return []
    out = []
    for d in sorted(p for p in root.iterdir() if p.is_dir() and not p.is_symlink()):
        info_path = d / 'session.json'
        if not info_path.is_file():
            continue
        info = json.loads(info_path.read_text(encoding='utf-8'))
        try:
            import chat_backup
            topics = chat_backup.read_topics(d, info)
        except Exception:   # noqa: BLE001 – beschädigte Nachträge: nur den Vollstand lesen
            topics = {p.parent.name: json.loads(p.read_text(encoding='utf-8')) for p in sorted(d.glob('*/latest.json'))}
        at = ((info.get('last_saved') or {}).get('at')) or ''
        out.append({'session': info.get('session') or d.name, 'at': at,
                    'topics': {t: topic_text(topics[t]) for t in TOPICS if topics.get(t)}})
    out.sort(key=lambda s: (s['at'] or s['session']), reverse=True)
    return out[:limit] if limit else out


def collect(base, limit=10):
    base, config = load(base)
    return {'title': ((config.get('project') or {}).get('title')) or '',
            'characters': characters(base, config), 'places': places(base), 'glossary': glossary(base, config),
            'chronology': chronology(base), 'sessions': sessions(base, limit)}


def text(data, width=240):
    lines = [f'# Wissensstand: {data["title"] or "Buch"}', '',
             'Arbeitswissen, nur lesend. Vor neuen Figuren, Orten, Begriffen oder Vorschlägen hiermit abgleichen.', '']
    if data['characters']:
        lines.append(f'## Figuren ({len(data["characters"])})')
        for c in data['characters']:
            role = ROLE_DE.get(c['role'], c['role'])
            extra = ', '.join(x for x in (role, 'Serie' if c['source'] == 'Serie' else '') if x)
            lines.append(f'- {c["name"]}' + (f' ({extra})' if extra else '') + (f': {short(c["short"], width)}' if c['short'] else ''))
        lines.append('')
    if data['places']:
        lines.append(f'## Schauplätze ({len(data["places"])})')
        for p in data['places']:
            alias = f' – auch: {", ".join(p["aliases"])}' if p['aliases'] else ''
            kind = f' ({p["kind"]})' if p['kind'] else ''
            lines.append(f'- {p["name"]}{kind}{alias}' + (f': {short(p["short"], width)}' if p['short'] else ''))
        lines.append('')
    if data['glossary']:
        lines.append(f'## Begriffe ({len(data["glossary"])})')
        lines += [f'- {g["term"]}: {short(g["text"], width)}' for g in data['glossary']]
        lines.append('')
    if data['chronology']:
        lines.append(f'## Zeitpunkte ({len(data["chronology"])})')
        lines += [f'- {e["when"] or "ohne Datum"}: {short(e["what"], width)}' for e in data['chronology']]
        lines.append('')
    if data['sessions']:
        lines.append(f'## Frühere Gespräche ({len(data["sessions"])}, jüngste zuerst)')
        for s in data['sessions']:
            lines.append(f'### {s["session"]}' + (f' ({s["at"][:10]})' if s['at'] else ''))
            for t, value in s['topics'].items():
                lines.append(f'- {TOPIC_DE[t]}: {short(value, width * 3)}')
        lines.append('')
    if len(lines) == 4:
        lines.append('Noch nichts gespeichert: keine Figuren, Orte, Begriffe, Zeitpunkte oder gesicherten Gespräche.')
    return '\n'.join(lines).rstrip() + '\n'


def main(argv=None):
    ap = argparse.ArgumentParser(description='Wissensstand eines Buchs (nur lesend)')
    ap.add_argument('project')
    ap.add_argument('--json', action='store_true')
    ap.add_argument('--width', type=int, default=240, help='Höchstlänge einer Beschreibung')
    ap.add_argument('--sessions', type=int, default=10, help='Anzahl der jüngsten Sitzungen (0 = alle)')
    args = ap.parse_args(argv)
    data = collect(args.project, args.sessions)
    print(json.dumps(data, ensure_ascii=False, indent=2) if args.json else text(data, args.width), end='' if not args.json else '\n')


if __name__ == '__main__':
    main()
