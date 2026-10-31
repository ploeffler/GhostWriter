#!/usr/bin/env python3
"""Zerlegt ein Manuskript (eine Markdown-Datei, ein H1 „Kapitel N: Titel“ je Kapitel)
in die GhostWriter-Projektstruktur.

Aufruf:
  python scripts/import_manuscript.py <manuskript.md> <zielordner> --title "Buchtitel" [--title-short "Kurztitel"]

Regeln:
- Kapitel beginnen mit „# Kapitel N: Titel“.
- Die erste kursive Zeile nach der Kapitelüberschrift ist der Untertitel.
- Alles bis zur ersten „## “-Überschrift ist der Vorspann des Kapitels (README).
- Jede „## “-Überschrift beginnt einen Abschnitt; ab „## Quellenverzeichnis“ gehört
  der Rest des Kapitels (Quellen, Prüfliste) in die Kapitel-README.
- Ein Zwischenteil („---“ gefolgt von einer „# “-Überschrift, etwa „# Teil A“) wird
  dem folgenden Abschnitt vorangestellt.
- Der Manuskripttext wird nicht verändert.
"""
import argparse
import json
import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent

UMLAUTE = str.maketrans({'ä': 'ae', 'ö': 'oe', 'ü': 'ue', 'Ä': 'ae', 'Ö': 'oe', 'Ü': 'ue', 'ß': 'ss'})


def slug(text, words=5):
    s = re.sub(r'[^a-z0-9]+', '-', text.translate(UMLAUTE).lower()).strip('-')
    return '-'.join(s.split('-')[:words])


def q(text):
    """YAML-sicherer String (JSON ist gültiges YAML)."""
    return json.dumps(text, ensure_ascii=False)


def split_chapters(text):
    parts = re.split(r'(?m)^(?=# Kapitel \d+: )', text)
    return [p for p in parts if p.startswith('# Kapitel ')]


def parse_chapter(block):
    lines = block.rstrip('\n').split('\n')
    m = re.match(r'# Kapitel (\d+): (.+)', lines[0])
    number, title = int(m.group(1)), m.group(2).strip()
    body = lines[1:]
    # Abschnittsgrenzen
    idx = [i for i, l in enumerate(body) if l.startswith('## ')]
    pre = body[:idx[0]] if idx else body
    sections, tail = [], []
    for k, start in enumerate(idx):
        end = idx[k + 1] if k + 1 < len(idx) else len(body)
        heading = body[start][3:].strip()
        if heading.startswith('Quellenverzeichnis'):
            tail = body[start:]
            break
        sections.append([heading, body[start + 1:end]])
    # Zwischenteile („---“ + „# …“) an den folgenden Abschnitt hängen
    cuts = []
    for k in range(len(sections)):
        content, cut = sections[k][1], None
        for i, l in enumerate(content):
            if l.strip() == '---':
                rest = [x for x in content[i + 1:] if x.strip()]
                if rest and rest[0].startswith('# '):
                    cut = i
        cuts.append(cut)
    for k in range(len(sections) - 2, -1, -1):
        cut = cuts[k]
        if cut is not None:
            sections[k + 1][1] = sections[k][1][cut:] + [''] + sections[k + 1][1]
            sections[k][1] = sections[k][1][:cut]
    # Untertitel
    subtitle = ''
    for i, l in enumerate(pre):
        if l.strip():
            if re.fullmatch(r'\*[^*].*\*', l.strip()):
                subtitle = l.strip()[1:-1]
                pre = pre[:i] + pre[i + 1:]
            break
    return number, title, subtitle, pre, sections, tail


def tidy(lines):
    text = '\n'.join(lines).strip('\n')
    return re.sub(r'\n{3,}', '\n\n', text)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('manuscript')
    ap.add_argument('target')
    ap.add_argument('--title', required=True)
    ap.add_argument('--title-short', default='')
    ap.add_argument('--section-status', default='writing')
    ap.add_argument('--chapter-status', default='in_progress')
    args = ap.parse_args()

    target = Path(args.target)
    if (target / 'chapters').exists():
        sys.exit(f'{target}/chapters existiert bereits')
    text = Path(args.manuscript).read_text(encoding='utf-8')

    config = yaml.safe_load((ROOT / 'ghostwriter.yml').read_text(encoding='utf-8'))
    config['project']['title'] = args.title
    config['project']['title_short'] = args.title_short or args.title
    config['workflow']['current_phase'] = 'writing'
    chapters = []

    for block in split_chapters(text):
        number, title, subtitle, pre, sections, tail = parse_chapter(block)
        cdir = f'chapters/{number:02d}-{slug(title)}'
        cid = f'ch-{number:02d}-{slug(title)}'
        entry = {'id': cid, 'title': title, 'path': cdir, 'status': args.chapter_status, 'sections': []}
        rows = []
        for sn, (stitle, content) in enumerate(sections, start=1):
            sslug = slug(stitle)
            sid = f'sec-{number:02d}-{sn:02d}-{sslug}'
            spath = f'{cdir}/sections/{sn:02d}-{sslug}.md'
            entry['sections'].append({'id': sid, 'title': stitle, 'path': spath})
            rows.append(f'| {number}.{sn} | {stitle} | `{args.section_status}` |')
            head = '\n'.join([
                '---', f'id: {sid}', f'number: "{number}.{sn}"', f'title: {q(stitle)}',
                f'status: {args.section_status}', 'fact_check: optional', 'approvals:',
                '  writing: true', '  section: false', '---'])
            doc = (f'{head}\n\n# {number}.{sn} {stitle}\n\n## Ziel des Abschnitts\n\nOffen.\n\n'
                   f'## Kurzbeschreibung\n\nOffen.\n\n## Recherche- und Brainstorming-Ergebnisse\n\n'
                   f'Werden in separaten Laufdateien dokumentiert.\n\n## Manuskript\n\n{tidy(content)}\n')
            p = target / spath
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(doc, encoding='utf-8')
        readme = [f'# Kapitel {number} – {title}', '']
        if subtitle:
            readme += [f'*{subtitle}*', '']
        readme += ['## Kurzbeschreibung', '', 'Offen.', '', '## Ziel des Kapitels', '', 'Offen.', '']
        vorspann = tidy(pre)
        if vorspann:
            readme += ['## Vorspann', '', vorspann, '']
        readme += ['## Abschnitte', '', '| Nummer | Abschnitt | Status |', '|---|---|---|'] + rows + ['']
        readme += ['## Kapitelstatus', '', f'`{args.chapter_status}`', '', '## Kapitelzusammenführung', '', 'Noch nicht begonnen.', '']
        if tail:
            t = tail[1:]
            pruef = next((i for i, l in enumerate(t) if l.startswith('## Prüfliste')), None)
            quellen = t[:pruef] if pruef is not None else t
            quellen = [l for l in quellen if l.strip() != '---']
            readme += ['## Quellen', '', tidy(quellen), '']
            if pruef is not None:
                readme += ['## Prüfliste für den Autor', '', tidy(t[pruef + 1:]), '']
        (target / cdir / 'README.md').write_text('\n'.join(readme).rstrip('\n') + '\n', encoding='utf-8')
        chapters.append(entry)

    config['structure']['chapters'] = chapters
    target.mkdir(parents=True, exist_ok=True)
    (target / 'ghostwriter.yml').write_text(
        yaml.safe_dump(config, allow_unicode=True, sort_keys=False, width=100), encoding='utf-8')
    print(f'{len(chapters)} Kapitel, {sum(len(c["sections"]) for c in chapters)} Abschnitte nach {target}')


if __name__ == '__main__':
    main()
