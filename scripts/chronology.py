#!/usr/bin/env python3
"""Chronologie aus Unterlagen und Recherche (story/chronology.yml, #354).

Neben der Text-Zeitleiste (story/timeline.yml, aus dem Manuskript) hält die Chronologie fest, was wann geschah,
mit Belegstand und Quelle: für Bücher nach wahren Begebenheiten, Familiengeschichten, Biografien und Sachbücher,
deren Chronologie vor dem Text entsteht, aber für jedes Buch nutzbar. Gefüllt wird sie im Chat aus Figuren,
Schauplätzen, Quellenliste, Rechercheläufen und gesicherten Sitzungen (START.md, „Chronologie“); gespeichert wird nur
nach Auswahl. Nie Teil des Buchs.

Die Prüfung läuft ohne KI und gibt nur Hinweise (nichts ist entschieden):
- overlap   Lebensabschnitte derselben Figur an verschiedenen Orten, die sich sicher überschneiden
- gap       Lebensabschnitte (mit Ort) derselben Figur, die nicht aneinander anschließen
- two_dates mehrere Daten für dasselbe Ereignis (same_as bzw. gleicher Wortlaut), die nicht zusammenpassen
- source    eine Angabe bzw. Erinnerung widerspricht einem belegten Eintrag zum selben Ereignis
- after_death, before_birth  Eintrag einer Figur sicher nach ihrem Tod bzw. vor ihrer Geburt
- age       genanntes Alter passt nicht zum Geburtsdatum
- undated   Eintrag ohne Datum (wird in der Ansicht ans Ende gestellt)

Ungenaue Daten zählen als Zeitraum: „1944“ = 1.1.–31.12.1944, „1944-05“ = Mai 1944. Ein Hinweis entsteht nur,
wenn der Widerspruch für jeden Tag des Zeitraums gilt.

Aufruf:
  python3 scripts/chronology.py <buch> check [--json]
  python3 scripts/render_view.py <buch> timeline --text [--status documented,reported] [--repo …]
"""
import argparse
import calendar
import datetime
import json
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
from render_view import load  # noqa: E402

STATUS = ('documented', 'reported', 'uncertain', 'invented')
STATUS_DE = {'documented': 'belegt', 'reported': 'Angabe', 'uncertain': 'unsicher', 'invented': 'Romanfreiheit'}
STATUS_ICON = {'documented': '●', 'reported': '○', 'uncertain': '◌', 'invented': '✎'}
KIND_DE = {'overlap': 'Überschneidung', 'gap': 'Lücke', 'two_dates': 'zwei Daten', 'source': 'Angabe gegen Beleg',
           'after_death': 'nach dem Tod', 'before_birth': 'vor der Geburt', 'age': 'Alter', 'undated': 'ohne Datum'}
ONE_DAY = datetime.timedelta(days=1)


def path(base):
    return Path(base) / 'story' / 'chronology.yml'


def read(base):
    """Inhalt von story/chronology.yml oder None."""
    p = path(base)
    if not p.is_file():
        return None
    return yaml.safe_load(p.read_text(encoding='utf-8')) or {'entries': []}


def interval(text):
    """„1944“ → (1.1.1944, 31.12.1944), „1944-05“ → Mai, „1944-05-12“ → der Tag; leer → None."""
    if not text:
        return None
    parts = [int(x) for x in str(text).split('-')]
    y = parts[0]
    if len(parts) == 1:
        return datetime.date(y, 1, 1), datetime.date(y, 12, 31)
    m = parts[1]
    if len(parts) == 2:
        return datetime.date(y, m, 1), datetime.date(y, m, calendar.monthrange(y, m)[1])
    d = datetime.date(y, m, parts[2])
    return d, d


def bounds(e):
    """(Beginn, Ende) eines Eintrags als Zeiträume (lo, hi); Ende None = offen; beides None = ohne Datum."""
    if e.get('kind') == 'span':
        return interval(e.get('from')), interval(e.get('to'))
    d = interval(e.get('date'))
    return d, d


def sort_key(e):
    start, _ = bounds(e)
    return (0, start[0], start[1], e['id']) if start else (1, datetime.date.max, datetime.date.max, e['id'])


def date_label(e):
    """Anzeige: date_text, sonst das Datum bzw. „von–bis“; „~“ für geschätzt."""
    if e.get('date_text'):
        text = e['date_text']
    elif e.get('kind') == 'span':
        text = f'{e.get("from") or "?"}–{e.get("to") or ""}'
    else:
        text = e.get('date') or 'ohne Datum'
    return ('~' if e.get('estimated') and not e.get('date_text') else '') + text


def norm(text):
    return ' '.join(str(text or '').casefold().split())


def age_range(at, birth):
    """Mögliches Alter zwischen zwei Zeiträumen: (jüngstes, ältestes)."""
    def years(day, born):
        return day.year - born.year - ((day.month, day.day) < (born.month, born.day))
    return years(at[0], birth[1]), years(at[1], birth[0])


def findings(data, names=None):
    """Hinweise ohne KI → [{kind, text, entries}]. names: {char-id: Name} für lesbare Texte."""
    names = names or {}
    entries = [e for e in (data or {}).get('entries') or [] if isinstance(e, dict) and e.get('id')]
    by_id = {e['id']: e for e in entries}
    who = lambda c: names.get(c, c)
    out = []

    def add(kind, text, ids):
        out.append({'kind': kind, 'text': text, 'entries': sorted(set(ids))})

    # Lebensabschnitte je Figur (nur mit Ort): Überschneidung an verschiedenen Orten, Lücken
    spans = {}
    for e in entries:
        if e.get('kind') == 'span' and e.get('place') and bounds(e)[0]:
            for c in e.get('characters') or []:
                spans.setdefault(c, []).append(e)
    for c, items in spans.items():
        items.sort(key=sort_key)
        for i, a in enumerate(items):
            a_start, a_end = bounds(a)
            for b in items[i + 1:]:
                b_start, b_end = bounds(b)
                if a.get('place') == b.get('place'):
                    continue
                a_ends_after = a_end is None or b_start[1] < a_end[0]
                b_ends_after = b_end is None or a_start[1] < b_end[0]
                if a_ends_after and b_ends_after:
                    add('overlap', f'{who(c)}: „{a["what"]}“ ({date_label(a)}, {a["place"]}) und „{b["what"]}“ '
                                   f'({date_label(b)}, {b["place"]}) überschneiden sich', [a['id'], b['id']])
        last, reach = None, None   # bisher spätestes Ende; offenes Ende schließt jede Lücke
        for b in items:
            b_start, b_end = bounds(b)
            if last is not None and reach is not None and b_start[0] > reach + ONE_DAY:
                add('gap', f'{who(c)}: zwischen „{last["what"]}“ (bis {last.get("to")}) und „{b["what"]}“ (ab {b.get("from")}) '
                           'fehlt ein Abschnitt', [last['id'], b['id']])
            if last is None or (reach is not None and (b_end is None or b_end[1] > reach)):
                last, reach = b, (b_end[1] if b_end else None)

    # Dasselbe Ereignis mit mehreren Daten: same_as und gleicher Wortlaut bilden Gruppen
    parent = {e['id']: e['id'] for e in entries}

    def root(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def join(a, b):
        if a in parent and b in parent:
            parent[root(a)] = root(b)
    for e in entries:
        if e.get('same_as'):
            join(e['id'], e['same_as'])
    first = {}
    for e in entries:
        people = tuple(sorted(e.get('characters') or []))
        key = (e.get('kind'), people) if e.get('kind') in ('birth', 'death') else (e.get('kind'), people, norm(e.get('what')))
        if key in first:
            join(e['id'], first[key])
        else:
            first[key] = e['id']
    groups = {}
    for e in entries:
        groups.setdefault(root(e['id']), []).append(e)
    for items in groups.values():
        dated = [e for e in items if bounds(e)[0]]
        for i, a in enumerate(dated):
            for b in dated[i + 1:]:
                (alo, ahi), (blo, bhi) = bounds(a)[0], bounds(b)[0]
                if ahi < blo or bhi < alo:
                    doc = [x for x in (a, b) if x.get('status') == 'documented']
                    if len(doc) == 1:
                        other = b if doc[0] is a else a
                        add('source', f'„{other["what"]}“: {STATUS_DE.get(other.get("status"), "")} {date_label(other)} '
                                      f'gegen belegt {date_label(doc[0])}', [a['id'], b['id']])
                    else:
                        add('two_dates', f'„{a["what"]}“: {date_label(a)} und {date_label(b)}', [a['id'], b['id']])

    # Geburt und Tod: erster datierter Eintrag je Figur
    birth, death = {}, {}
    for e in sorted(entries, key=sort_key):
        if e.get('kind') in ('birth', 'death') and bounds(e)[0] and e.get('characters'):
            (birth if e['kind'] == 'birth' else death).setdefault(e['characters'][0], e)
    for e in entries:
        start, end = bounds(e)
        if not start:
            continue
        last = end or start
        for c in e.get('characters') or []:
            b, d = birth.get(c), death.get(c)
            if d and d is not e and e.get('kind') != 'birth' and max(start[0], last[0]) > bounds(d)[0][1]:
                add('after_death', f'{who(c)}: „{e["what"]}“ ({date_label(e)}) nach dem Tod ({date_label(d)})', [e['id'], d['id']])
            if b and b is not e and e.get('kind') != 'death' and start[1] < bounds(b)[0][0]:
                add('before_birth', f'{who(c)}: „{e["what"]}“ ({date_label(e)}) vor der Geburt ({date_label(b)})', [e['id'], b['id']])
        if e.get('age') is not None and e.get('characters') and e['characters'][0] in birth:
            c = e['characters'][0]
            b = birth[c]
            low, high = age_range(start, bounds(b)[0])
            if not low <= e['age'] <= high:
                expect = str(low) if low == high else f'{low}–{high}'
                add('age', f'{who(c)}: „{e["what"]}“ mit {e["age"]} Jahren, nach dem Geburtsdatum ({date_label(b)}) '
                           f'{expect}', [e['id'], b['id']])
    for e in entries:
        if not bounds(e)[0]:
            add('undated', f'„{e["what"]}“ hat kein Datum', [e['id']])
    order = list(KIND_DE)
    out.sort(key=lambda f: (order.index(f['kind']), f['entries']))
    return out


def references(base, config, data):
    """Fehler für validate_project.py: unbekannte Figuren, Kapitel, Orte (pl-…), same_as; Datumsangaben je Art."""
    errors, p = [], path(base)
    known_chars = {c.get('id') for c in (config.get('characters') or [])}
    known_chapters = {ch['id'] for ch in config['structure']['chapters']}
    places = Path(base) / 'story' / 'places.yml'
    known_places = {x.get('id') for x in ((yaml.safe_load(places.read_text(encoding='utf-8')) or {}).get('places') or [])} \
        if places.is_file() else set()
    ids = [e['id'] for e in data['entries']]
    errors += [f'{p}: ID doppelt: {i}' for i in sorted({i for i in ids if ids.count(i) > 1})]
    for e in data['entries']:
        where = f'{p}: {e["id"]}'
        errors += [f'{where}: Figur {c} unbekannt' for c in e.get('characters') or [] if c not in known_chars]
        if e.get('chapter') and e['chapter'] not in known_chapters:
            errors.append(f'{where}: Kapitel {e["chapter"]} unbekannt')
        if str(e.get('place') or '').startswith('pl-') and e['place'] not in known_places:
            errors.append(f'{where}: Ort {e["place"]} unbekannt (story/places.yml)')
        if e.get('same_as') and e['same_as'] not in ids:
            errors.append(f'{where}: same_as {e["same_as"]} unbekannt')
        if e['kind'] == 'span':
            if e.get('date'):
                errors.append(f'{where}: Zeitspanne mit from/to statt date')
            if e.get('from') and e.get('to') and interval(e['to'])[1] < interval(e['from'])[0]:
                errors.append(f'{where}: Ende vor dem Beginn')
            if e.get('to') and not e.get('from'):
                errors.append(f'{where}: Ende ohne Beginn')
        elif e.get('from') or e.get('to'):
            errors.append(f'{where}: from/to nur bei kind: span')
        if e['kind'] in ('birth', 'death') and len(e.get('characters') or []) != 1:
            errors.append(f'{where}: Geburt bzw. Tod mit genau einer Figur')
        for f in ('date', 'from', 'to'):
            try:
                interval(e.get(f))
            except ValueError:
                errors.append(f'{where}: {f} ist kein gültiges Datum')
    return errors


def char_names(config):
    return {c.get('id'): c.get('name') or c.get('id') for c in (config.get('characters') or [])}


def text_view(base, config, status=None):
    """Textfassung von render_view.py timeline: Kasten „Wo die Daten nicht zusammenpassen“, Lebenslinien, Liste."""
    data = read(base)
    if data is None:
        return ('### 🕰️ Chronologie\n\nNoch keine Chronologie (`story/chronology.yml`). Sie entsteht im Chat aus Figuren, '
                'Schauplätzen, Quellen, Recherche und gesicherten Sitzungen; gespeichert wird nur, was du auswählst.\n')
    names = char_names(config)
    entries = sorted(data.get('entries') or [], key=sort_key)
    found = findings(data, names)
    counts = {s: sum(e.get('status') == s for e in entries) for s in STATUS}
    real = [f for f in found if f['kind'] != 'undated']
    lines = ['### 🕰️ Chronologie', '',
             f'**{len(entries)} Einträge** · ' + ' · '.join(f'{STATUS_ICON[s]} {STATUS_DE[s]} {counts[s]}' for s in STATUS if counts[s])
             + f' · {len(real)} {"Hinweis" if len(real) == 1 else "Hinweise"}', '']
    lines += ['**Wo die Daten nicht zusammenpassen**', '']
    lines += [f'- {KIND_DE[f["kind"]]}: {f["text"]} ({", ".join(f["entries"])})' for f in real] or ['- nichts gefunden']
    lines.append('')
    lives = {}
    for e in entries:
        if e.get('kind') == 'span' and e.get('from'):
            for c in e.get('characters') or []:
                lives.setdefault(c, []).append(e)
    if lives:
        lines += ['**Lebenslinien**', '']
        for c, items in lives.items():
            lines.append(f'- **{names.get(c, c)}:** ' + ' · '.join(
                f'{date_label(e)} {e.get("place") or e["what"]}' + ('' if e.get('status') == 'documented' else f' {STATUS_ICON.get(e.get("status"), "")}')
                for e in items))
        lines.append('')
    shown = [e for e in entries if not status or e.get('status') in status]
    lines += ['**Einträge**' + (f' (nur {", ".join(STATUS_DE.get(s, s) for s in status)})' if status else ''), '']
    year = None
    for e in shown:
        start = bounds(e)[0]
        y = start[0].year if start else None
        if y != year:
            lines += ['', f'*{y if y else "ohne Datum"}*']
            year = y
        who = ', '.join(names.get(c, c) for c in e.get('characters') or [])
        extra = ', '.join(x for x in (who, e.get('place') or '') if x)
        lines.append(f'- {date_label(e)} {STATUS_ICON.get(e.get("status"), "")} {e["what"]}' + (f' ({extra})' if extra else '')
                     + (f' – Quelle: {e["source"]}' if e.get('source') else '') + f' `{e["id"]}`')
    if not shown:
        lines.append('*keine*')
    lines += ['', f'Zeichen: {" ".join(f"{STATUS_ICON[s]} {STATUS_DE[s]}" for s in STATUS)}, ~ geschätzt. '
              'Hinweise sind keine Entscheidung; die Chronologie kommt nie ins Buch.']
    return '\n'.join(lines) + '\n'


def place_names(base):
    p = Path(base) / 'story' / 'places.yml'
    items = ((yaml.safe_load(p.read_text(encoding='utf-8')) or {}).get('places') or []) if p.is_file() else []
    return {x.get('id'): x.get('name') or x.get('id') for x in items}


def widget_values(base, config):
    """Werte für die Vorlage zeitleiste (ghostwriter-ui, #354): (values, blocks)."""
    data = read(base) or {'entries': []}
    names, places = char_names(config), place_names(base)
    entries = sorted(data.get('entries') or [], key=sort_key)
    found = findings(data, names)
    flagged = {i for f in found if f['kind'] != 'undated' for i in f['entries']}
    chapters = {ch['id']: (n, ch['title']) for n, ch in enumerate(config['structure']['chapters'], start=1)}
    lanes, rows, band = [], [], {}
    for e in entries:
        start, end = bounds(e)
        keys = list(e.get('characters') or []) or ['@none']
        for k in keys:
            if k not in lanes:
                lanes.append(k)
        place = places.get(e.get('place'), e.get('place') or '')
        ch = chapters.get(e.get('chapter'))
        row = {'id': e['id'], 'kind': e['kind'], 'lo': str(start[0]) if start else '', 'hi': str(start[1]) if start else '',
               'end_lo': str(end[0]) if end and e['kind'] == 'span' else '', 'end_hi': str(end[1]) if end and e['kind'] == 'span' else '',
               'open': e['kind'] == 'span' and bool(start) and not end, 'label': date_label(e), 'what': e['what'],
               'status': e.get('status', ''), 'estimated': bool(e.get('estimated')), 'lanes': keys,
               'people': ', '.join(names.get(c, c) for c in e.get('characters') or []), 'place': place,
               'chapter': f'{ch[0]}: {ch[1]}' if ch else '', 'source': e.get('source', ''), 'flag': e['id'] in flagged}
        rows.append(row)
        if ch and start:
            last = (end or start)[1]
            lo, hi = band.get(ch[0], (start[0], last))
            band[ch[0]] = (min(lo, start[0]), max(hi, last))
    lane_rows = [{'key': k, 'label': 'Ohne Figur' if k == '@none' else names.get(k, k)} for k in lanes]
    chapter_rows = [{'label': f'K{n}', 'lo': str(lo), 'hi': str(hi)} for n, (lo, hi) in sorted(band.items())]
    hints = [f for f in found if f['kind'] != 'undated']
    values = {'PROJECT_TITLE_SHORT': config['project'].get('title_short') or config['project'].get('title') or '',
              'COUNT_TEXT': f'{len(entries)} {"Eintrag" if len(entries) == 1 else "Einträge"} · '
                            + (f'{len(hints)} {"Hinweis" if len(hints) == 1 else "Hinweise"}' if hints else 'keine Hinweise'),
              'TIMELINE_JSON': json.dumps({'entries': rows, 'lanes': lane_rows, 'chapters': chapter_rows}, ensure_ascii=False),
              'EMPTY_TEXT': '' if entries else ('Noch keine Chronologie. Sie entsteht im Chat aus Figuren, Schauplätzen, '
                                                 'Quellen, Recherche und gesicherten Sitzungen; gespeichert wird nur, was du auswählst.')}
    blocks = {'FINDINGS': [{'F_KIND_TEXT': KIND_DE[f['kind']], 'F_TEXT': f['text'], 'F_ENTRIES': ', '.join(f['entries'])} for f in hints]}
    return values, blocks


def main(argv):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('project')
    ap.add_argument('cmd', choices=['check'])
    ap.add_argument('--json', action='store_true')
    a = ap.parse_args(argv[1:])
    base, config = load(a.project)
    data = read(base)
    found = findings(data, char_names(config)) if data else []
    if a.json:
        print(json.dumps({'entries': len((data or {}).get('entries') or []), 'findings': found}, ensure_ascii=False, indent=1))
    else:
        print('\n'.join(f'{KIND_DE[f["kind"]]}: {f["text"]}' for f in found) or 'keine Hinweise')
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
