#!/usr/bin/env python3
"""Vor- und Nachspann eines Buchs anlegen (#57).

Aufruf:
  python scripts/matter.py <projektordner> add <art> [--title TITEL]
  python scripts/matter.py <projektordner> list

Arten: dedication (Widmung), prologue (Prolog), epilogue (Epilog),
acknowledgments (Danksagung); auch der deutsche Name geht (widmung, Prolog …).

add legt matter/<datei>.md aus templates/matter.md an und trägt den Teil in
ghostwriter.yml ein (structure.front_matter bzw. back_matter, Reihenfolge:
Widmung vor Prolog, Epilog vor Danksagung). Der Rest von ghostwriter.yml bleibt
Zeichen für Zeichen erhalten (keine Neuformatierung, Kommentare bleiben).
Den Commit schreibt der Assistent wie bei jedem Formular (START.md, „Vor- und
Nachspann“); das Skript ändert nur Dateien im Projektordner.
"""
import argparse
import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'scripts'))
from render_view import MATTER, MATTER_AREAS, matter_id, matter_items  # noqa: E402

NAMES = {**{k: k for k in MATTER}, **{v[1].lower(): k for k, v in MATTER.items()}}


def kind_of(name):
    k = NAMES.get((name or '').strip().lower())
    if not k:
        raise SystemExit(f'Unbekannte Art „{name}“; möglich: ' + ', '.join(f'{k} ({v[1]})' for k, v in MATTER.items()))
    return k


def area_block(key, items):
    """YAML-Block `  <key>:` mit den Einträgen, eingerückt wie structure.chapters."""
    out = [f'  {key}:']
    for i in items:
        out += [f'  - id: {i["id"]}', f'    kind: {i["kind"]}', f'    title: {yaml.safe_dump(i["title"], allow_unicode=True).splitlines()[0]}',
                f'    path: {i["path"]}']
    return '\n'.join(out) + '\n'


def set_area(text, key, items):
    """structure.<key> in ghostwriter.yml ersetzen bzw. vor `  chapters:` einfügen, ohne den Rest anzufassen."""
    block = area_block(key, items)
    m = re.search(rf'(?m)^  {key}:.*\n(?:(?:  [ -].*|\s*)\n)*', text)
    if m:
        return text[:m.start()] + block + text[m.end():]
    m = re.search(r'(?m)^  chapters:', text)
    if not m or not re.search(r'(?m)^structure:\s*$', text[:m.start()]):
        raise SystemExit('ghostwriter.yml: structure.chapters nicht gefunden')
    if key == 'front_matter':   # Vorspann vor einem schon vorhandenen Nachspann
        b = re.search(r'(?m)^  back_matter:', text)
        if b and b.start() < m.start():
            m = b
    return text[:m.start()] + block + text[m.start():]


def add(base, kind, title=None):
    cfg_path = base / 'ghostwriter.yml'
    text = cfg_path.read_text(encoding='utf-8')
    config = yaml.safe_load(text)
    area, default_title, filename = MATTER[kind]
    if any(i['kind'] == kind for _, i in matter_items(config)):
        raise SystemExit(f'{default_title} gibt es schon.')
    title = (title or default_title).strip()
    item = {'id': matter_id(kind), 'kind': kind, 'title': title, 'path': f'matter/{filename}'}
    path = base / item['path']
    if path.exists():
        raise SystemExit(f'{item["path"]} gibt es schon, steht aber nicht in ghostwriter.yml; bitte prüfen.')
    order = [k for k, v in MATTER.items() if v[0] == area]
    items = sorted([i for _, i in matter_items(config, area)] + [item], key=lambda i: order.index(i['kind']))
    new = set_area(text, MATTER_AREAS[area], items)
    if (yaml.safe_load(new)['structure'].get(MATTER_AREAS[area]) or []) != items:
        raise SystemExit('ghostwriter.yml ließ sich nicht sicher ändern; bitte von Hand eintragen.')
    tpl = (ROOT / 'templates' / 'matter.md').read_text(encoding='utf-8')
    head = yaml.safe_dump(title, allow_unicode=True).splitlines()[0]
    body = (tpl.replace('<mat-ID>', item['id']).replace('<ART>   # dedication | prologue | epilogue | acknowledgments', kind)
            .replace('"<TITEL>"', head).replace('# <TITEL>', f'# {title}'))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding='utf-8')
    cfg_path.write_text(new, encoding='utf-8')
    return item


def main(argv):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('project')
    ap.add_argument('cmd', choices=['add', 'list'])
    ap.add_argument('kind', nargs='?')
    ap.add_argument('--title')
    a = ap.parse_args(argv[1:])
    base = Path(a.project)
    if a.cmd == 'list':
        config = yaml.safe_load((base / 'ghostwriter.yml').read_text(encoding='utf-8'))
        for area, i in matter_items(config):
            print(f'{"Vorspann " if area == "front" else "Nachspann"} {i["id"]:<16} {i["title"]}  ({i["path"]})')
        return 0
    item = add(base, kind_of(a.kind), a.title)
    label = MATTER[item['kind']][1] + ('' if item['title'] == MATTER[item['kind']][1] else f' „{item["title"]}“')
    print(f'✓ {label} angelegt: {item["path"]}, ghostwriter.yml ({MATTER_AREAS[MATTER[item["kind"]][0]]})')
    print(f'Commit-Nachricht: {label} angelegt')
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
