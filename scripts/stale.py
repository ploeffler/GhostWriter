#!/usr/bin/env python3
"""Abschnitte als „veraltet“ kennzeichnen, ohne die Freigabe zurückzunehmen (#510).

  python3 scripts/stale.py <buch> mark 1.2 --reason "Zeitzeugin widerspricht" [--source editorial/x.md] [--date 2026-11-24]
  python3 scripts/stale.py <buch> clear 1.2
  python3 scripts/stale.py <buch> list

Das Feld `stale: {since, reason, source}` steht im Kopf der Abschnittsdatei. Es ändert weder Status noch
`approvals` noch den Fingerabdruck des Manuskripts (der Text bleibt unverändert). Beim erneuten Abschließen des
Abschnitts entfernt der Assistent das Feld (`clear`); ein bloßes Wiederöffnen lässt es stehen.
"""
import argparse
import datetime
import re
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
from render_view import load, section_file  # noqa: E402

BLOCK = re.compile(r'(?m)^stale:\n(?:[ \t]+.*\n)+')


def locate(base, config, number):
    m = re.fullmatch(r'(\d+)\.(\d+)', str(number))
    if not m:
        raise ValueError('Abschnittsnummer wie 1.2 angeben')
    try:
        return config['structure']['chapters'][int(m[1]) - 1]['sections'][int(m[2]) - 1]
    except IndexError:
        raise ValueError(f'Abschnitt {number} gibt es nicht') from None


def _split(text):
    m = re.match(r'(---\n)(.*?\n)(---\n)', text, re.S)
    if not m:
        raise ValueError('Abschnittsdatei ohne Kopf')
    return m


def mark(base, config, number, reason, source='', date=None):
    reason = ' '.join((reason or '').split())
    if not reason:
        raise ValueError('--reason fehlt')
    section = locate(base, config, number)
    path = Path(base) / section['path']
    text = path.read_text(encoding='utf-8')
    m = _split(text)
    entry = {'since': str(date or datetime.date.today().isoformat()), 'reason': reason}
    if source:
        entry['source'] = source
    block = yaml.safe_dump({'stale': entry}, allow_unicode=True, sort_keys=False)
    head = BLOCK.sub('', m.group(2))
    path.write_text(m.group(1) + head + block + m.group(3) + text[m.end():], encoding='utf-8')
    return path


def clear(base, config, number):
    """True, wenn ein Vermerk entfernt wurde."""
    path = Path(base) / locate(base, config, number)['path']
    text = path.read_text(encoding='utf-8')
    m = _split(text)
    head = BLOCK.sub('', m.group(2))
    if head == m.group(2):
        return False
    path.write_text(m.group(1) + head + m.group(3) + text[m.end():], encoding='utf-8')
    return True


def stale_sections(base, config):
    """[(Nummer, Abschnitt, Vermerk)] aller als veraltet markierten Abschnitte."""
    out = []
    for c, ch in enumerate(config['structure']['chapters'], start=1):
        for s, sec in enumerate(ch['sections'], start=1):
            note = section_file(Path(base), sec)[0].get('stale')
            if note:
                out.append((f'{c}.{s}', sec, note))
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('project')
    ap.add_argument('cmd', choices=['mark', 'clear', 'list'])
    ap.add_argument('number', nargs='?')
    ap.add_argument('--reason')
    ap.add_argument('--source', default='')
    ap.add_argument('--date')
    a = ap.parse_args(argv)
    base, config = load(a.project)
    try:
        if a.cmd == 'list':
            rows = stale_sections(base, config)
            print('\n'.join(f'{n} {sec["title"]}: seit {note["since"]} – {note["reason"]}' for n, sec, note in rows)
                  or 'Keine Abschnitte als veraltet markiert.')
        elif a.cmd == 'mark':
            print(mark(base, config, a.number, a.reason, a.source, a.date).relative_to(base))
        else:
            print('Vermerk entfernt.' if clear(base, config, a.number) else 'Kein Vermerk vorhanden.')
    except ValueError as exc:
        print(exc, file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
