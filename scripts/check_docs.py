#!/usr/bin/env python3
"""Prüft, ob die Doku zum Programm passt (läuft in validate.yml).

Aufruf:
  python scripts/check_docs.py [--ui <ordner von ghostwriter-ui>]

Geprüft wird:
1. Aktionen: Jede Aktion, die eine Vorlage in ghostwriter-ui schickt, steht in
   der Aktionstabelle von templates/ui/BEFUELLUNG.md. Schreibende Aktionen
   (Spalte „API“ mit POST, PATCH, PUT oder DELETE) stehen auch in START.md, und
   ihr Endpunkt steht in docs/API-CONTRACT.md.
2. Platzhalter: Jeder Platzhalter {{NAME}} einer Vorlage ist in BEFUELLUNG.md
   beschrieben.
3. Datenmodell: Jedes Feld der obersten und zweiten Ebene aus ghostwriter.yml
   und jedes Feld der obersten Ebene aus dem Schema steht in docs/DATA-MODEL.md.
4. Läufe: Jede Lauf-Art aus workflow.yml (runs) steht mit ihrem Pfad in
   docs/DATA-MODEL.md.
5. Links: Relative Links in den Markdown-Dateien zeigen auf vorhandene Dateien.

Ohne --ui entfallen 1 und 2 (Hinweis). Exit-Code 1, wenn etwas fehlt.
"""
import argparse
import json
import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
DOCS = ['START.md', 'README.md', 'templates/ui/BEFUELLUNG.md', 'templates/ui/README.md'] + \
       sorted(str(p.relative_to(ROOT)) for p in (ROOT / 'docs').glob('*.md'))
# Platzhalter, die gw.js selbst setzt bzw. die kein Befüllen brauchen
PLACEHOLDER_SKIP = {'HEAD_SHA'}
# Aktionen ohne Zeile in der Aktionstabelle (reine Steuerung im Chat)
ACTION_SKIP = set()


def read(rel):
    return (ROOT / rel).read_text(encoding='utf-8')


def action_table(text):
    """{aktion: api-spalte} aus der Aktionstabelle von BEFUELLUNG.md."""
    out = {}
    for line in text.splitlines():
        m = re.match(r'\|\s*`([a-z_]+(?:\.[a-z_]+)+)`\s*\|(.*)\|\s*$', line)
        if m:
            cells = [c.strip() for c in m.group(2).split('|')]
            out.setdefault(m.group(1), cells[-1] if cells else '')
    return out


def ui_templates(ui):
    return sorted((Path(ui) / 'templates').glob('*.html'))


def check_actions(ui, problems):
    bef, start, api = read('templates/ui/BEFUELLUNG.md'), read('START.md'), read('docs/API-CONTRACT.md')
    table = action_table(bef)
    sent = {}
    for t in ui_templates(ui):
        src = t.read_text(encoding='utf-8')
        names = set(re.findall(r'data-a="([a-z_.]+)"', src))
        names |= set(re.findall(r"gwSend\([^;]*?,\s*'([a-z_]+(?:\.[a-z_]+)+)'", src))
        for n in names:
            sent.setdefault(n, t.name)
    for n, where in sorted(sent.items()):
        if n in ACTION_SKIP:
            continue
        if n not in table:
            problems.append(f'Aktion `{n}` ({where}) fehlt in der Aktionstabelle von templates/ui/BEFUELLUNG.md')
            continue
        col = table[n]
        if not re.search(r'\b(POST|PATCH|PUT|DELETE)\b', col):   # nur schreibende Aktionen
            continue
        if f'`{n}`' not in start:
            problems.append(f'Schreibende Aktion `{n}` fehlt in START.md (Tabelle „Was jedes Formular schreibt“ bzw. Ablauf)')
        for path in re.findall(r'`(?:[A-Z]+ )?(…/[^`]*|/v1/[^`]*)`', col):
            full = path.replace('…/', '/v1/projects/{owner}/{repo}/')
            if full not in api:
                problems.append(f'Endpunkt `{full}` der Aktion `{n}` fehlt in docs/API-CONTRACT.md')


def check_placeholders(ui, problems):
    bef = read('templates/ui/BEFUELLUNG.md')
    for t in ui_templates(ui):
        src = t.read_text(encoding='utf-8')
        body = re.sub(r'\A<!--.*?-->', '', src, flags=re.S)
        for name in sorted(set(re.findall(r'\{\{([A-Z][A-Z0-9_]*)\}\}', body)) - PLACEHOLDER_SKIP):
            if not re.search(rf'`{name}`', bef):
                problems.append(f'Platzhalter `{name}` ({t.name}) ist in templates/ui/BEFUELLUNG.md nicht beschrieben')


def check_data_model(problems):
    dm = read('docs/DATA-MODEL.md')
    cfg = yaml.safe_load(read('ghostwriter.yml')) or {}
    schema = json.loads(read('schemas/ghostwriter.schema.json'))
    keys = set(schema.get('properties', {}))
    for top, val in cfg.items():
        keys.add(top)
        if isinstance(val, dict) and top not in ('ai_providers',):   # ai_providers: docs/PROVIDERS.md
            keys |= {f'{top}.{sub}' for sub in val}
    for k in sorted(keys):
        top, _, sub = k.partition('.')
        if sub:
            if f'`{k}`' in dm or re.search(rf'`{re.escape(sub)}`', dm):
                continue
            problems.append(f'Feld `{k}` aus ghostwriter.yml fehlt in docs/DATA-MODEL.md')
        elif f'`{top}' not in dm:
            problems.append(f'Feld `{top}` (ghostwriter.yml/Schema) fehlt in docs/DATA-MODEL.md')


def check_runs(problems):
    dm = read('docs/DATA-MODEL.md')
    wf = yaml.safe_load(read('workflow.yml'))
    for name, run in (wf.get('runs') or {}).items():
        path = (run or {}).get('path', '')
        folder = path.split('{chapter_id}/')[-1].split('/{')[0].split('/run-')[0]
        if folder and folder not in dm:
            problems.append(f'Lauf `{name}` (Ablage `{path}`) fehlt in docs/DATA-MODEL.md')


def check_links(problems):
    for rel in DOCS:
        path = ROOT / rel
        if not path.is_file():
            continue
        text = re.sub(r'```.*?```', '', path.read_text(encoding='utf-8'), flags=re.S)
        for target in re.findall(r'\]\(([^)\s]+)\)', text):
            if re.match(r'[a-z]+:', target) or target.startswith('#'):
                continue
            file = target.split('#')[0]
            if file and not (path.parent / file).exists():
                problems.append(f'Link in {rel} zeigt ins Leere: {target}')


def main(argv):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--ui', help='Ordner mit ghostwriter-ui (Vorlagen unter templates/)')
    args = ap.parse_args(argv[1:])
    problems = []
    if args.ui:
        check_actions(args.ui, problems)
        check_placeholders(args.ui, problems)
    else:
        print('Hinweis: ohne --ui keine Prüfung der Aktionen und Platzhalter')
    check_data_model(problems)
    check_runs(problems)
    check_links(problems)
    for p in problems:
        print(f'✗ {p}')
    if not problems:
        print('✓ Doku passt zum Programm')
    return 1 if problems else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
