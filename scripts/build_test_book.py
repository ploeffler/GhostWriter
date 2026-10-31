#!/usr/bin/env python3
"""Baut das Testbuch für den Branch test/test-book.

Aufruf (im Arbeitsverzeichnis eines frischen Checkouts von main):
  python scripts/build_test_book.py

Das Skript
1. übernimmt tests/fixtures/adhs (ghostwriter.yml, chapters/) in die oberste Ebene,
2. wendet die erfundenen Testdaten aus tests/fixtures/test-book.yml an
   (Projektdaten, Status und Freigaben, Kosteneinträge, aktuelle Auflage),
3. schreibt TESTDATEN.md mit einer Übersicht aller erfundenen Angaben.

Tag und Release der Auflagen legt es nicht an; die Befehle dafür stehen in TESTDATEN.md.
"""
import json
import re
import shutil
import sys
from pathlib import Path

import yaml

ROOT = Path.cwd()
FIXTURE = ROOT / 'tests' / 'fixtures' / 'adhs'
SPEC = ROOT / 'tests' / 'fixtures' / 'test-book.yml'


def slug(text):
    t = text.translate(str.maketrans({'ä': 'ae', 'ö': 'oe', 'ü': 'ue', 'Ä': 'ae', 'Ö': 'oe', 'Ü': 'ue', 'ß': 'ss'}))
    return re.sub(r'[^a-z0-9]+', '-', t.lower()).strip('-')


def set_head(path, status, approved):
    text = path.read_text(encoding='utf-8')
    text = re.sub(r'(?m)^status: .*$', f'status: {status}', text, count=1)
    text = re.sub(r'(?m)^  section: (true|false)$', f'  section: {"true" if approved else "false"}', text, count=1)
    path.write_text(text, encoding='utf-8')


def main():
    if (ROOT / 'chapters').exists():
        sys.exit('chapters/ existiert bereits – auf einem frischen Checkout von main ausführen')
    spec = yaml.safe_load(SPEC.read_text(encoding='utf-8'))
    shutil.copytree(FIXTURE / 'chapters', ROOT / 'chapters')
    config = yaml.safe_load((FIXTURE / 'ghostwriter.yml').read_text(encoding='utf-8'))

    config['project'].update(spec['project'])
    chapters = config['structure']['chapters']
    w = spec['workflow']
    config['workflow']['current_chapter_id'] = chapters[w['current_chapter'] - 1]['id']
    config['workflow']['current_section_id'] = chapters[w['current_chapter'] - 1]['sections'][w['current_section'] - 1]['id']

    for cnum, cspec in spec['chapters'].items():
        chapter = chapters[int(cnum) - 1]
        chapter['status'] = cspec['status']
        sec_spec = cspec.get('sections', {})
        statuses = []
        for snum, section in enumerate(chapter['sections'], start=1):
            status = sec_spec.get('all') or sec_spec.get(snum) or 'writing'
            if status != 'writing':
                set_head(ROOT / section['path'], status, status == 'approved')
            statuses.append(status)
        readme = ROOT / chapter['path'] / 'README.md'
        text = readme.read_text(encoding='utf-8')
        for snum, status in enumerate(statuses, start=1):
            text = re.sub(rf'(?m)^(\| {cnum}\.{snum} \| .*\| )`[a-z_]+`( \|)$', rf'\g<1>`{status}`\g<2>', text)
        text = re.sub(r'(?m)(^## Kapitelstatus\n\n)`[a-z_]+`', rf'\g<1>`{cspec["status"]}`', text)
        readme.write_text(text, encoding='utf-8')

    for key, entries in spec['costs'].items():
        if key == 'project':
            path = ROOT / 'costs' / 'project.yml'
            data = {'scope': 'project', 'entries': entries}
        else:
            c, s = (int(x) for x in key.split('.'))
            chapter = chapters[c - 1]
            sid = chapter['sections'][s - 1]['id']
            path = ROOT / chapter['path'] / 'costs' / f'{sid}.yml'
            data = {'section_id': sid, 'entries': [dict(e, section_id=sid) for e in entries]}
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text('# TESTDATEN – erfundene Kosteneinträge\n' + yaml.safe_dump(data, allow_unicode=True, sort_keys=False), encoding='utf-8')

    (ROOT / 'ghostwriter.yml').write_text(
        '# TESTDATEN – Testbuch auf Basis des ADHS-Manuskripts, siehe TESTDATEN.md\n'
        + yaml.safe_dump(config, allow_unicode=True, sort_keys=False, width=100), encoding='utf-8')

    title_short = config['project']['title_short']
    lines = [
        '# Testdaten in diesem Branch', '',
        'Dieser Branch `test/test-book` ist das Testbuch für GhostWriter bis v0.5. Der Manuskripttext stammt unverändert aus '
        '`tests/fixtures/sources/adhs-im-erwachsenenleben.md`. Alles Folgende ist **erfunden** und dient nur Tests; es wird mit dem Branch nach v0.5 gelöscht.', '',
        '## Erfundene Angaben', '',
        f'- Autorin: {spec["project"]["author"]}',
        '- Kurz- und Langbeschreibung des Buches',
        f'- Projektstatus `{spec["project"]["status"]}`, zuletzt bearbeitet: Kapitel {w["current_chapter"]}, Abschnitt {w["current_chapter"]}.{w["current_section"]}',
    ]
    for cnum, cspec in spec['chapters'].items():
        lines.append(f'- Kapitel {cnum}: Status `{cspec["status"]}`, Abschnitte ' +
                     ', '.join(f'{"alle" if k == "all" else f"{cnum}.{k}"} `{v}`' for k, v in cspec.get('sections', {}).items()))
    lines.append('- Alle übrigen Abschnitte: Status `writing`, Schreibfreigabe erteilt')
    lines += ['', '## Kosteneinträge', '', '| Stelle | Aktivität | Betrag | Status |', '|---|---|---|---|']
    for key, entries in spec['costs'].items():
        for e in entries:
            amount = '–' if e['cost_amount'] is None else f'{e["cost_amount"]:.2f} {e["currency"]}'.replace('.', ',')
            lines.append(f'| {"Projekt" if key == "project" else "Abschnitt " + key} | {e["activity_type"]} | {amount} | `{e["cost_status"]}` |')
    lines += ['', '## Auflagen', '']
    for ed in spec['editions']:
        tag = f'{slug(title_short)}-auflage-{ed["number"]}'
        name = f'{title_short} – Auflage {ed["number"]}'
        lines += [f'- **{name}** (Tag `{tag}`, {ed["date"]}): {ed["notes"]}']
    lines += ['', 'Tag und Release legt `scripts/build_test_book.py` nicht an. Der Release trägt im Namen den Zusatz „(Testdaten)“.', '',
              '## Zurücksetzen', '',
              'Den Branch aus einem frischen Checkout von `main` neu bauen:', '', '```sh',
              'git checkout -B test/test-book origin/main',
              'python scripts/build_test_book.py',
              'git add -A && git commit -m "Testbuch neu aufbauen"',
              'git push --force origin test/test-book', '```', '']
    (ROOT / 'TESTDATEN.md').write_text('\n'.join(lines), encoding='utf-8')
    print(json.dumps({'chapters': len(chapters), 'cost_files': len(spec['costs']), 'editions': len(spec['editions'])}))


if __name__ == '__main__':
    main()
