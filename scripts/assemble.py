#!/usr/bin/env python3
"""Fügt freigegebene Abschnitte zu Kapiteln und zum Buch zusammen (#14).

Aufruf:
  python scripts/assemble.py <projektordner> chapter <nummer|kapitel-id> [-o datei.md]
  python scripts/assemble.py <projektordner> book [-o datei.md] [--edition N] [--date JJJJ-MM-TT]
  python scripts/assemble.py <projektordner> check [--edition N]

chapter  Ein Kapitel aus seinen freigegebenen Abschnitten (status approved), in
         der Reihenfolge aus ghostwriter.yml. Nicht freigegebene Abschnitte
         werden ausgelassen und gemeldet.
book     Das Buch für eine Auflage: nur freigegebene Kapitel (Kapitelstatus
         approved), darin nur freigegebene Abschnitte, dazu die Quellen je
         Kapitel. Vorn ein YAML-Block mit den Angaben für den Buchsatz
         (Titel, Autor, Auflage, typesetting aus ghostwriter.yml).
check    Prüft, ob eine Auflage gebaut werden kann: mindestens ein freigegebenes
         Kapitel und keine offenen Marker ([QUELLE PRÜFEN …] usw.) im
         freigegebenen Text. Exit-Code 1 mit Liste der Gründe, sonst 0.

Was ins Buch kommt: je Kapitel Titel, Untertitel (erste kursive Zeile der
Kapitel-README), der Text unter „## Manuskript“ jeder freigegebenen
Abschnittsdatei mit dem Abschnittstitel als Überschrift, und der Abschnitt
„## Quellen“ der Kapitel-README. Nicht ins Buch kommen „Vorspann“,
„Kurzbeschreibung“, „Ziel“, „Prüfliste“ und alle Arbeitsdateien (Läufe,
Kosten). Die Ausgabe ist Markdown für Pandoc (scripts/build_edition.py).

Dieses Skript läuft nur in GitHub Actions oder lokal; den zusammengeführten
Text gibt der Assistent nie im Chat aus (START.md, „Kein ganzes Buch im Chat“).
"""
import argparse
import datetime
import re
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
from render_view import MARKER_TEXT, load, section_file  # noqa: E402

TYPESETTING_DEFAULT = {'page_size': 'a5', 'font': 'serif', 'font_size': 11, 'title_page': True,
                       'imprint': True, 'toc': True, 'toc_depth': 1}


def readme_parts(base, chapter):
    path = base / chapter['path'] / 'README.md'
    text = path.read_text(encoding='utf-8') if path.is_file() else ''
    sub = re.search(r'(?m)^\*([^*].*)\*$', text)
    sources = re.search(r'(?ms)^## Quellen\n(.*?)(?=^## |\Z)', text)
    return (sub.group(1).strip() if sub else ''), (sources.group(1).strip() if sources else '')


def shift_headings(text, top):
    """Überschriften im Manuskript so verschieben, dass die oberste Ebene `top` ist
    (unter der Abschnittsüberschrift ##)."""
    levels = [len(m.group(1)) for m in re.finditer(r'(?m)^(#{1,6})\s', text)]
    if not levels:
        return text
    by = top - min(levels)
    def sub(m):
        level = max(1, min(len(m.group(1)) + by, 6))
        return '#' * level + m.group(2)
    return re.sub(r'(?m)^(#{1,6})(\s)', sub, text)


def chapter_markdown(base, chapter, number):
    """(Markdown, ausgelassene Abschnitte, Marker) eines Kapitels."""
    subtitle, sources = readme_parts(base, chapter)
    out = [f'# {chapter["title"]}', '']
    if subtitle:
        out += [f'*{subtitle}*', '']
    skipped, markers = [], []
    for si, s in enumerate(chapter['sections'], start=1):
        head, _, _, manuscript = section_file(base, s)
        if head.get('status') != 'approved':
            skipped.append(f'{number}.{si} {s["title"]} ({head.get("status")})')
            continue
        out += [f'## {s["title"]}', '', shift_headings(manuscript.strip(), 3), '']
        markers += [(f'{number}.{si}', m.group(0)) for m in MARKER_TEXT.finditer(manuscript)]
    if sources:
        clean = re.sub(r'(?m)^Status aller Einträge:.*\n?', '', sources).strip()
        if clean:
            out += ['## Quellen {.unnumbered .sources}', '', clean, '']
            markers += [(f'{number} Quellen', m.group(0)) for m in MARKER_TEXT.finditer(clean)]
    return '\n'.join(out).rstrip() + '\n', skipped, markers


def find_chapter(config, key):
    chapters = config['structure']['chapters']
    if key.isdigit():
        n = int(key)
        return n, chapters[n - 1]
    for i, ch in enumerate(chapters, start=1):
        if ch['id'] == key:
            return i, ch
    raise SystemExit(f'Kapitel {key} nicht gefunden')


def book_parts(base, config):
    """Freigegebene Kapitel: [(nummer, kapitel, markdown, ausgelassen, marker)]."""
    parts = []
    for i, ch in enumerate(config['structure']['chapters'], start=1):
        if ch.get('status') != 'approved':
            continue
        md, skipped, markers = chapter_markdown(base, ch, i)
        parts.append((i, ch, md, skipped, markers))
    return parts


def metadata(config, edition, date):
    p = config['project']
    ts = dict(TYPESETTING_DEFAULT)
    ts.update(config.get('typesetting') or {})
    title = p.get('title') or p.get('working_title') or 'Ohne Titel'
    meta = {'title': title, 'subtitle': p.get('subtitle') or '', 'author': p.get('author') or '',
            'lang': p.get('language') or 'de', 'date': date, 'edition': edition,
            'edition_text': f'{edition}. Auflage' if edition else '',
            'description': p.get('description_short') or '', 'typesetting': ts}
    return {k: v for k, v in meta.items() if v not in ('', None)}


def problems(parts, config):
    out = []
    if not parts:
        n = len(config['structure']['chapters'])
        out.append(f'Kein Kapitel ist freigegeben (0 von {n}); eine Auflage enthält nur freigegebene Kapitel.')
    for num, ch, _, skipped, markers in parts:
        if skipped:
            out.append(f'Kapitel {num} „{ch["title"]}“ ist freigegeben, enthält aber nicht freigegebene Abschnitte: '
                       + '; '.join(skipped))
        for where, marker in markers:
            out.append(f'Offener Marker in {where}: {marker}')
    return out


def main(argv):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('project')
    ap.add_argument('what', choices=['chapter', 'book', 'check'])
    ap.add_argument('key', nargs='?')
    ap.add_argument('-o', '--output')
    ap.add_argument('--edition', type=int)
    ap.add_argument('--date', default=datetime.date.today().isoformat())
    args = ap.parse_args(argv[1:])
    base, config = load(args.project)
    edition = args.edition if args.edition is not None else (config['project'].get('current_edition') or 0)

    if args.what == 'chapter':
        if not args.key:
            ap.error('chapter braucht eine Kapitelnummer oder -ID')
        num, ch = find_chapter(config, args.key)
        md, skipped, markers = chapter_markdown(base, ch, num)
        for s in skipped:
            print(f'ausgelassen (nicht freigegeben): {s}', file=sys.stderr)
        if markers:
            print(f'{len(markers)} offene Marker im freigegebenen Text', file=sys.stderr)
    else:
        parts = book_parts(base, config)
        if args.what == 'check':
            found = problems(parts, config)
            for line in found:
                print(f'✗ {line}')
            if not found:
                words = sum(len(re.findall(r'\w+', md)) for _, _, md, _, _ in parts)
                print(f'✓ Auflage {edition} kann gebaut werden: {len(parts)} Kapitel, etwa {words} Wörter')
            return 1 if found else 0
        meta = metadata(config, edition, args.date)
        md = '---\n' + yaml.safe_dump(meta, allow_unicode=True, sort_keys=False) + '---\n\n' + \
             '\n'.join(part[2] for part in parts)
    if args.output:
        Path(args.output).write_text(md, encoding='utf-8')
        print(f'{args.output}: {len(md.split())} Wörter', file=sys.stderr)
    else:
        sys.stdout.write(md)
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
