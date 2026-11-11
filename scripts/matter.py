#!/usr/bin/env python3
"""Vor- und Nachspann eines Buchs anlegen (#57).

Aufruf:
  python scripts/matter.py <projektordner> add <art> [--title TITEL]
  python scripts/matter.py <projektordner> list
  python scripts/matter.py <projektordner> glossary-set "Begriff" "Erklärung" [--new]
  python scripts/matter.py <projektordner> glossary-remove "Begriff"
  python scripts/matter.py <buch> glossary-from-series "Begriff"     Begriff der Serie ins Buch (Kopie) bzw. angleichen (#116)
  python scripts/matter.py <buch> glossary-to-series "Begriff" --series-repo <standard>   Begriff des Buchs in die Serie

Arten: dedication (Widmung), foreword (Vorwort), prologue (Prolog), epilogue
(Epilog), afterword (Nachwort), glossary (Glossar), acknowledgments (Danksagung);
auch der deutsche Name geht (widmung, Prolog …).

glossary-set nimmt einen Begriff ins Glossar auf bzw. ändert seine Erklärung
(Groß-/Kleinschreibung egal); mit --new bricht es ab, wenn es den Begriff schon
gibt (Prüfung auf Doppelungen beim Anlegen, #58). glossary-remove entfernt ihn.
Beide schreiben die Einträge alphabetisch (DIN 5007-1) unter „## Manuskript“;
eine Einleitung davor bleibt.

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
from render_view import (MATTER, MATTER_AREAS, german_key, glossary_entries, matter_id,  # noqa: E402
                         matter_items, section_file)

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
        out += [f'  - id: {i["id"]}', f'    kind: {i["kind"]}', f'    title: {yaml.safe_dump(i["title"], allow_unicode=True, width=10**6).splitlines()[0]}',
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
    head = yaml.safe_dump(title, allow_unicode=True, width=10**6).splitlines()[0]
    body = re.sub(r'(?m)^kind: <ART>.*$', f'kind: {kind}', tpl.replace('<mat-ID>', item['id']))
    body = body.replace('"<TITEL>"', head).replace('# <TITEL>', f'# {title}')
    if kind == 'glossary':
        body = body.replace('<Was soll dieser Teil leisten? Bei Widmung und Danksagung: an wen?>',
                            'Begriffe, die Leserinnen und Leser nachschlagen können.')
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding='utf-8')
    cfg_path.write_text(new, encoding='utf-8')
    return item


def glossary_write(base, change):
    """Glossar-Einträge ändern: change(einträge) -> neue Einträge; schreibt sortiert zurück."""
    config = yaml.safe_load((base / 'ghostwriter.yml').read_text(encoding='utf-8'))
    item = next((i for _, i in matter_items(config) if i['kind'] == 'glossary'), None)
    if not item:
        raise SystemExit('Es gibt noch kein Glossar; zuerst anlegen: python scripts/matter.py . add glossary')
    path = base / item['path']
    text = path.read_text(encoding='utf-8')
    ms = section_file(base, item)[3]
    intro, entries = glossary_entries('' if ms == 'Noch nicht begonnen.' else ms)
    entries = sorted(change(list(entries)), key=lambda e: german_key(e[0]))
    body = '\n'.join(f'- {t}: {e}' for t, e in entries)
    new_ms = '\n\n'.join(x for x in (intro, body) if x) or 'Noch nicht begonnen.'
    head, sep, _ = text.partition('\n## Manuskript\n')
    path.write_text(head + '\n## Manuskript\n\n' + new_ms + '\n', encoding='utf-8')
    return item


def glossary_set(base, term, explanation, new=False):
    term, explanation = term.strip(), ' '.join(explanation.split())
    if not term or not explanation or ':' in term:
        raise SystemExit('Begriff (ohne Doppelpunkt) und Erklärung angeben.')
    def change(entries):
        hit = [i for i, (t, _) in enumerate(entries) if t.casefold() == term.casefold()]
        if hit and new:
            raise SystemExit(f'„{entries[hit[0]][0]}“ steht schon im Glossar.')
        if hit:
            entries[hit[0]] = (term, explanation)
            return entries
        return entries + [(term, explanation)]
    return glossary_write(base, change)


def glossary_remove(base, term):
    def change(entries):
        left = [e for e in entries if e[0].casefold() != term.strip().casefold()]
        if len(left) == len(entries):
            raise SystemExit(f'„{term}“ steht nicht im Glossar.')
        return left
    return glossary_write(base, change)


def series_term(base, term):
    """(serie, begriff der Serie) für ein Buch einer Serie (#116)."""
    from render_view import load
    import series
    _, config = load(base)
    ser = config.get('_series')
    if not ser:
        raise SystemExit('Dieses Buch gehört zu keiner Serie')
    hit = [x for x in series.glossary(base, ser['id']) if series.term_key(x['term']) == series.term_key(term)]
    return ser, (hit[0] if hit else None)


def glossary_from_series(base, term):
    """Begriff der Serie ins Glossar des Buchs übernehmen bzw. die Kopie angleichen (Erklärung der Serie)."""
    ser, hit = series_term(base, term)
    if not hit:
        raise SystemExit(f'„{term}“ gibt es in der Serie „{ser["title"]}“ nicht')
    glossary_set(base, hit['term'], hit['text'])
    return hit


def glossary_to_series(base, main_dir, term):
    """Begriff des Buchs mit seiner Erklärung in die Serie übernehmen (Standard-Branch, main_dir)."""
    import series
    from render_view import load
    _, config = load(base)
    ser = config.get('_series')
    if not ser:
        raise SystemExit('Dieses Buch gehört zu keiner Serie')
    item = next((i for _, i in matter_items(config) if i['kind'] == 'glossary'), None)
    entries = glossary_entries(section_file(base, item)[3])[1] if item else []
    hit = [(t, e) for t, e in entries if t.casefold() == term.strip().casefold()]
    if not hit:
        raise SystemExit(f'„{term}“ steht nicht im Glossar dieses Buchs')
    series.term_set(main_dir, ser['id'], *hit[0])
    return ser, hit[0]


def main(argv):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('project')
    ap.add_argument('cmd', choices=['add', 'list', 'glossary-set', 'glossary-remove', 'glossary-from-series', 'glossary-to-series'])
    ap.add_argument('--series-repo', help='bei glossary-to-series: Ordner mit dem Standard-Branch (series/)')
    ap.add_argument('kind', nargs='?', help='bei add: Art; bei glossary-*: Begriff')
    ap.add_argument('explanation', nargs='?', help='bei glossary-set: Erklärung')
    ap.add_argument('--title')
    ap.add_argument('--new', action='store_true', help='bei glossary-set: nur neu aufnehmen, nie ändern')
    a = ap.parse_args(argv[1:])
    base = Path(a.project)
    if a.cmd == 'list':
        config = yaml.safe_load((base / 'ghostwriter.yml').read_text(encoding='utf-8'))
        for area, i in matter_items(config):
            print(f'{"Vorspann " if area == "front" else "Nachspann"} {i["id"]:<16} {i["title"]}  ({i["path"]})')
        return 0
    if a.cmd == 'glossary-set':
        glossary_set(base, a.kind or '', a.explanation or '', a.new)
        print(f'✓ Glossar: „{a.kind.strip()}“ eingetragen')
        print(f'Commit-Nachricht: Glossar: „{a.kind.strip()}“ eingetragen')
        return 0
    if a.cmd == 'glossary-from-series':
        hit = glossary_from_series(base, a.kind or '')
        print(f'✓ Glossar: „{hit["term"]}“ aus der Serie übernommen\nCommit-Nachricht: Glossar: „{hit["term"]}“ aus der Serie übernommen')
        return 0
    if a.cmd == 'glossary-to-series':
        if not a.series_repo:
            ap.error('glossary-to-series braucht --series-repo (Standard-Branch)')
        ser, (t, _) = glossary_to_series(base, a.series_repo, a.kind or '')
        print(f'✓ „{t}“ in die Serie „{ser["title"]}“ übernommen\nCommit-Nachricht (Standard-Branch): Serie „{ser["title"]}“: Begriff „{t}“ eingetragen')
        return 0
    if a.cmd == 'glossary-remove':
        glossary_remove(base, a.kind or '')
        print(f'✓ Glossar: „{a.kind.strip()}“ entfernt')
        print(f'Commit-Nachricht: Glossar: „{a.kind.strip()}“ entfernt')
        return 0
    item = add(base, kind_of(a.kind), a.title)
    label = MATTER[item['kind']][1] + ('' if item['title'] == MATTER[item['kind']][1] else f' „{item["title"]}“')
    print(f'✓ {label} angelegt: {item["path"]}, ghostwriter.yml ({MATTER_AREAS[MATTER[item["kind"]][0]]})')
    print(f'Commit-Nachricht: {label} angelegt')
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
