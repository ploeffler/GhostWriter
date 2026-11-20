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
- text      Ereignis der Text-Zeitleiste passt nicht zum verknüpften Eintrag (#364)
- undated   Eintrag ohne Datum (wird in der Ansicht ans Ende gestellt)

Ungenaue Daten zählen als Zeitraum: „1944“ = 1.1.–31.12.1944, „1944-05“ = Mai 1944. Ein Hinweis entsteht nur,
wenn der Widerspruch für jeden Tag des Zeitraums gilt.

Aufruf:
  python3 scripts/chronology.py <buch> check [--json] [--language en]
  python3 scripts/chronology.py <buch> export [--out story/zeitleiste.html] [--language en]
  python3 scripts/chronology.py <buch> import-md     Tabelle aus story/chronologie.md als Vorschlagslauf (#379)

Erzählzeit (#379): Für eine Handlung ohne Kalenderjahr steht oben `epoch` (label, optional weekday von Tag 0);
Einträge nennen dann `day` (Tag relativ zu Tag 0, bei span `day_to`) statt date/from/to, dazu optional `time`/`time_to`.

Abgleich mit der Text-Zeitleiste (#364, Art text): Ereignisse in story/timeline.yml mit Feld `chronology`
(chr-…, von Hand bzw. im Chat gesetzt) werden geprüft – eindeutige Jahres- bzw. Datumsangabe in `when`, die nicht
zum Eintrag passt, und Ereignis in einem anderen Kapitel als `chapter` des Eintrags. Relative Angaben bleiben ungeprüft.
export schreibt eine eigenständige HTML-Datei (statisches SVG, Hinweise, Liste; ohne Skript und Netz).
  python3 scripts/render_view.py <buch> timeline --text [--status documented,reported] [--repo …]
"""
import argparse
import calendar
import datetime
import html
import json
import re
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
from render_view import load  # noqa: E402

STATUS = ('documented', 'reported', 'uncertain', 'invented')
STATUS_DE = {'documented': 'belegt', 'reported': 'Angabe', 'uncertain': 'unsicher', 'invented': 'Romanfreiheit'}
STATUS_ICON = {'documented': '●', 'reported': '○', 'uncertain': '◌', 'invented': '✎'}
KIND_DE = {'overlap': 'Überschneidung', 'gap': 'Lücke', 'two_dates': 'zwei Daten', 'source': 'Angabe gegen Beleg',
           'after_death': 'nach dem Tod', 'before_birth': 'vor der Geburt', 'age': 'Alter', 'text': 'Text gegen Chronologie',
           'undated': 'ohne Datum'}
STATUS_EN = {'documented': 'documented', 'reported': 'reported', 'uncertain': 'uncertain', 'invented': 'invented'}
KIND_EN = {'overlap': 'overlap', 'gap': 'gap', 'two_dates': 'two dates', 'source': 'report against record',
           'after_death': 'after death', 'before_birth': 'before birth', 'age': 'age', 'text': 'text against chronology',
           'undated': 'undated'}
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


# Erzählzeit (#379): Tag 0 liegt intern auf einem festen Datum, damit Sortierung und Prüfungen gleich bleiben.
# Angezeigt wird nie dieses Datum, sondern „Tag N“.
EPOCH_BASE = datetime.date(2001, 1, 1)
WEEKDAYS = ('monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday')
WEEKDAY_DE = ('Montag', 'Dienstag', 'Mittwoch', 'Donnerstag', 'Freitag', 'Samstag', 'Sonntag')
WEEKDAY_EN = ('Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday')


def relative(e):
    return isinstance(e.get('day'), int)


def day_interval(day):
    d = EPOCH_BASE + datetime.timedelta(days=day)
    return d, d


def day_label(day, language='de'):
    word = 'Day' if language == 'en' else 'Tag'
    return f'{word} 0' if day == 0 else f'{word} {"+" if day > 0 else "−"}{abs(day)}'


def weekday_of(day, epoch, language='de'):
    wd = (epoch or {}).get('weekday')
    if wd not in WEEKDAYS:
        return ''
    return (WEEKDAY_EN if language == 'en' else WEEKDAY_DE)[(WEEKDAYS.index(wd) + day) % 7]


def bounds(e):
    """(Beginn, Ende) eines Eintrags als Zeiträume (lo, hi); Ende None = offen; beides None = ohne Datum."""
    if relative(e):
        start = day_interval(e['day'])
        if e.get('kind') == 'span':
            return start, (day_interval(e['day_to']) if isinstance(e.get('day_to'), int) else None)
        return start, start
    if e.get('kind') == 'span':
        return interval(e.get('from')), interval(e.get('to'))
    d = interval(e.get('date'))
    return d, d


def sort_key(e):
    start, _ = bounds(e)
    if start and relative(e):   # Erzählzeit (#379): innerhalb eines Tags die Reihenfolge der Einträge (Uhrzeit wird nur angezeigt)
        return (0, start[0], start[1], '', e['id'])
    return (0, start[0], start[1], '', e['id']) if start else (1, datetime.date.max, datetime.date.max, '', e['id'])


def time_label(e):
    if not e.get('time'):
        return ''
    return e['time'] + (f'–{e["time_to"]}' if e.get('time_to') else '')


def date_label(e, language='de'):
    """Anzeige: date_text, sonst das Datum bzw. „von–bis“ bzw. „Tag N, HH:MM“; „~“ für geschätzt."""
    if relative(e):
        text = day_label(e['day'], language)
        if e.get('kind') == 'span' and isinstance(e.get('day_to'), int):
            text += '–' + day_label(e['day_to'], language).split(' ', 1)[1]
        if e.get('date_text') and language != 'en':
            text += ' · ' + e['date_text']
        elif e.get('time'):
            text += ', ' + time_label(e)
        return ('~' if e.get('estimated') else '') + text
    if e.get('date_text') and language != 'en':
        text = e['date_text']
    elif e.get('kind') == 'span':
        text = f'{e.get("from") or "?"}–{e.get("to") or ""}'
    else:
        text = e.get('date') or ('undated' if language == 'en' else 'ohne Datum')
    return ('~' if e.get('estimated') and not e.get('date_text') else '') + text


def norm(text):
    return ' '.join(str(text or '').casefold().split())


def age_range(at, birth):
    """Mögliches Alter zwischen zwei Zeiträumen: (jüngstes, ältestes)."""
    def years(day, born):
        return day.year - born.year - ((day.month, day.day) < (born.month, born.day))
    return years(at[0], birth[1]), years(at[1], birth[0])


def findings(data, names=None, language='de'):
    """Hinweise ohne KI → [{kind, text, entries}]. names: {char-id: Name} für lesbare Texte."""
    names = names or {}
    en = language == 'en'
    dl = lambda e: date_label(e, language)
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
                    add('overlap', f'{who(c)}: “{a["what"]}” ({dl(a)}, {a["place"]}) and “{b["what"]}” ({dl(b)}, {b["place"]}) overlap'
                        if en else f'{who(c)}: „{a["what"]}“ ({dl(a)}, {a["place"]}) und „{b["what"]}“ '
                                   f'({dl(b)}, {b["place"]}) überschneiden sich', [a['id'], b['id']])
        last, reach = None, None   # bisher spätestes Ende; offenes Ende schließt jede Lücke
        for b in items:
            b_start, b_end = bounds(b)
            if last is not None and reach is not None and b_start[0] > reach + ONE_DAY:
                add('gap', f'{who(c)}: nothing between “{last["what"]}” (until {last.get("to")}) and “{b["what"]}” (from {b.get("from")})'
                    if en else f'{who(c)}: zwischen „{last["what"]}“ (bis {last.get("to")}) und „{b["what"]}“ (ab {b.get("from")}) '
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
                        add('source', f'“{other["what"]}”: {STATUS_EN.get(other.get("status"), "")} {dl(other)} against documented {dl(doc[0])}'
                            if en else f'„{other["what"]}“: {STATUS_DE.get(other.get("status"), "")} {dl(other)} '
                                      f'gegen belegt {dl(doc[0])}', [a['id'], b['id']])
                    else:
                        add('two_dates', f'“{a["what"]}”: {dl(a)} and {dl(b)}' if en else f'„{a["what"]}“: {dl(a)} und {dl(b)}',
                            [a['id'], b['id']])

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
                add('after_death', f'{who(c)}: “{e["what"]}” ({dl(e)}) after death ({dl(d)})' if en else
                    f'{who(c)}: „{e["what"]}“ ({dl(e)}) nach dem Tod ({dl(d)})', [e['id'], d['id']])
            if b and b is not e and e.get('kind') != 'death' and start[1] < bounds(b)[0][0]:
                add('before_birth', f'{who(c)}: “{e["what"]}” ({dl(e)}) before birth ({dl(b)})' if en else
                    f'{who(c)}: „{e["what"]}“ ({dl(e)}) vor der Geburt ({dl(b)})', [e['id'], b['id']])
        if e.get('age') is not None and e.get('characters') and e['characters'][0] in birth:
            c = e['characters'][0]
            b = birth[c]
            low, high = age_range(start, bounds(b)[0])
            if not low <= e['age'] <= high:
                expect = str(low) if low == high else f'{low}–{high}'
                add('age', f'{who(c)}: “{e["what"]}” at age {e["age"]}, by the date of birth ({dl(b)}) {expect}' if en else
                    f'{who(c)}: „{e["what"]}“ mit {e["age"]} Jahren, nach dem Geburtsdatum ({dl(b)}) '
                           f'{expect}', [e['id'], b['id']])
    for e in entries:
        if not bounds(e)[0]:
            add('undated', f'“{e["what"]}” has no date' if en else f'„{e["what"]}“ hat kein Datum', [e['id']])
    order = list(KIND_DE)
    out.sort(key=lambda f: (order.index(f['kind']), f['entries']))
    return out


# ---------- Abgleich mit der Text-Zeitleiste (#364) ----------

YEAR = re.compile(r'(?<![\d.])(1[0-9]{3}|20[0-9]{2})(?![\d])')
DMY = re.compile(r'(?<!\d)(\d{1,2})\.\s?(\d{1,2})\.\s?(1[0-9]{3}|20[0-9]{2})(?!\d)')
ISO = re.compile(r'(?<!\d)(1[0-9]{3}|20[0-9]{2})-(\d{2})(?:-(\d{2}))?(?!\d)')


def text_interval(when):
    """Eindeutige Zeitangabe aus `when` als Zeitraum: genau ein Datum bzw. genau ein Jahr; sonst None.
    Relative Angaben („drei Tage später“) und mehrere Jahre bleiben ungeprüft."""
    when = str(when or '')
    dates = []
    for m in DMY.finditer(when):
        try:
            d = datetime.date(int(m.group(3)), int(m.group(2)), int(m.group(1)))
            dates.append((d, d))
        except ValueError:
            return None
    for m in ISO.finditer(when):
        try:
            dates.append(interval(m.group(0)))
        except ValueError:
            return None
    if dates:
        return dates[0] if len(dates) == 1 else None
    years = set(YEAR.findall(when))
    return interval(years.pop()) if len(years) == 1 else None


def timeline_events(base):
    p = Path(base) / 'story' / 'timeline.yml'
    if not p.is_file():
        return []
    return [e for e in ((yaml.safe_load(p.read_text(encoding='utf-8')) or {}).get('events') or []) if isinstance(e, dict)]


def text_findings(base, config, data, language='de'):
    """Hinweise (Art text): Ereignisse der Text-Zeitleiste mit Feld `chronology`, die nicht zum Eintrag passen."""
    en = language == 'en'
    by_id = {e['id']: e for e in (data or {}).get('entries') or [] if isinstance(e, dict) and e.get('id')}
    chapter_of = {s['id']: (n, ch) for n, ch in enumerate(config['structure']['chapters'], start=1) for s in ch['sections']}
    out = []
    for ev in timeline_events(base):
        entry = by_id.get(ev.get('chronology'))
        if not entry:
            continue
        ids = sorted({ev['id'], entry['id']})
        start, end = bounds(entry)
        span = (start[0], (end or start)[1]) if start and (entry.get('kind') != 'span' or end) else \
            ((start[0], datetime.date.max) if start else None)
        said = text_interval(ev.get('when'))
        if span and said and (said[1] < span[0] or said[0] > span[1]):
            out.append({'kind': 'text', 'entries': ids, 'text':
                        f'“{ev["what"]}”: the text says “{ev["when"]}”, the chronology {date_label(entry, language)}' if en else
                        f'„{ev["what"]}“: im Text „{ev["when"]}“, in der Chronologie {date_label(entry)}'})
        place = chapter_of.get(ev.get('section'))
        if entry.get('chapter') and place and place[1]['id'] != entry['chapter']:
            want = next((n for n, ch in enumerate(config['structure']['chapters'], start=1) if ch['id'] == entry['chapter']), '?')
            out.append({'kind': 'text', 'entries': ids, 'text':
                        f'“{ev["what"]}” is in chapter {place[0]}, the chronology places it in chapter {want}' if en else
                        f'„{ev["what"]}“ steht in Kapitel {place[0]}, die Chronologie ordnet es Kapitel {want} zu'})
    return out


def all_findings(base, config, data, language='de'):
    """findings() und der Abgleich mit der Text-Zeitleiste, in der Reihenfolge von KIND_DE."""
    found = findings(data, char_names(config), language) + text_findings(base, config, data, language)
    order = list(KIND_DE)
    found.sort(key=lambda f: (order.index(f['kind']), f['entries']))
    return found


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
    rel = [e['id'] for e in data['entries'] if 'day' in e]
    if rel and not data.get('epoch'):
        errors.append(f'{p}: Einträge mit day ({", ".join(rel[:3])}) brauchen epoch (Bezugstag der Erzählzeit)')
    for e in data['entries']:
        where = f'{p}: {e["id"]}'
        if 'day' in e and any(e.get(f) for f in ('date', 'from', 'to')):
            errors.append(f'{where}: day und Kalenderdatum zugleich')
        if 'day_to' in e and (e['kind'] != 'span' or 'day' not in e):
            errors.append(f'{where}: day_to nur bei kind: span mit day')
        if 'day_to' in e and 'day' in e and e['day_to'] < e['day']:
            errors.append(f'{where}: Ende vor dem Beginn')
        if e.get('time_to') and not e.get('time'):
            errors.append(f'{where}: time_to ohne time')
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


TEXT = {
    'de': {'title': '### 🕰️ Chronologie', 'empty': 'Noch keine Chronologie (`story/chronology.yml`). Sie entsteht im Chat aus Figuren, '
           'Schauplätzen, Quellen, Recherche und gesicherten Sitzungen; gespeichert wird nur, was du auswählst.',
           'entries': 'Einträge', 'hint': 'Hinweis', 'hints': 'Hinweise', 'box': 'Wo die Daten nicht zusammenpassen', 'none': 'nichts gefunden',
           'lives': 'Lebenslinien', 'list': 'Einträge', 'only': 'nur', 'undated': 'ohne Datum', 'source': 'Quelle', 'nothing': 'keine',
           'legend': 'Zeichen', 'est': 'geschätzt', 'foot': 'Hinweise sind keine Entscheidung; die Chronologie kommt nie ins Buch.'},
    'en': {'title': '### 🕰️ Chronology', 'empty': 'No chronology yet (`story/chronology.yml`). It is built in chat from characters, '
           'places, sources, research and saved sessions; only what you select is saved.',
           'entries': 'entries', 'hint': 'note', 'hints': 'notes', 'box': 'Where the dates do not fit', 'none': 'nothing found',
           'lives': 'Life lines', 'list': 'Entries', 'only': 'only', 'undated': 'undated', 'source': 'source', 'nothing': 'none',
           'legend': 'Signs', 'est': 'estimated', 'foot': 'Notes are not decisions; the chronology never goes into the book.'},
}


def text_view(base, config, status=None, language='de'):
    """Textfassung von render_view.py timeline: Kasten „Wo die Daten nicht zusammenpassen“, Lebenslinien, Liste."""
    t = TEXT['en' if language == 'en' else 'de']
    st, kd = (STATUS_EN, KIND_EN) if language == 'en' else (STATUS_DE, KIND_DE)
    data = read(base)
    if data is None:
        return f'{t["title"]}\n\n{t["empty"]}\n'
    names = char_names(config)
    entries = sorted(data.get('entries') or [], key=sort_key)
    found = all_findings(base, config, data, language)
    counts = {s: sum(e.get('status') == s for e in entries) for s in STATUS}
    real = [f for f in found if f['kind'] != 'undated']
    lines = [t['title'], '',
             f'**{len(entries)} {t["entries"]}** · ' + ' · '.join(f'{STATUS_ICON[s]} {st[s]} {counts[s]}' for s in STATUS if counts[s])
             + f' · {len(real)} {t["hint"] if len(real) == 1 else t["hints"]}', '']
    ep = data.get('epoch')
    if ep:
        wd = weekday_of(0, ep, language)
        lines += [('Narrative time: Day 0 = ' if language == 'en' else 'Erzählzeit: Tag 0 = ') + ep['label']
                  + (f' ({wd})' if wd else ''), '']
    lines += [f'**{t["box"]}**', '']
    lines += [f'- {kd[f["kind"]]}: {f["text"]} ({", ".join(f["entries"])})' for f in real] or [f'- {t["none"]}']
    lines.append('')
    lives = {}
    for e in entries:
        if e.get('kind') == 'span' and e.get('from'):
            for c in e.get('characters') or []:
                lives.setdefault(c, []).append(e)
    if lives:
        lines += [f'**{t["lives"]}**', '']
        for c, items in lives.items():
            lines.append(f'- **{names.get(c, c)}:** ' + ' · '.join(
                f'{date_label(e, language)} {e.get("place") or e["what"]}' + ('' if e.get('status') == 'documented' else f' {STATUS_ICON.get(e.get("status"), "")}')
                for e in items))
        lines.append('')
    shown = [e for e in entries if not status or e.get('status') in status]
    lines += [f'**{t["list"]}**' + (f' ({t["only"]} {", ".join(st.get(s, s) for s in status)})' if status else ''), '']
    year = None
    for e in shown:
        start = bounds(e)[0]
        if relative(e):   # Erzählzeit (#379): je Tag, mit Wochentag
            y = day_label(e['day'], language)
            wd = weekday_of(e['day'], data.get('epoch'), language)
            y += f' ({wd})' if wd else ''
        else:
            y = start[0].year if start else None
        if y != year:
            lines += ['', f'*{y if y else t["undated"]}*']
            year = y
        who = ', '.join(names.get(c, c) for c in e.get('characters') or [])
        extra = ', '.join(x for x in (who, e.get('place') or '') if x)
        lines.append(f'- {date_label(e, language)} {STATUS_ICON.get(e.get("status"), "")} {e["what"]}' + (f' ({extra})' if extra else '')
                     + (f' – {t["source"]}: {e["source"]}' if e.get('source') else '') + f' `{e["id"]}`')
    if not shown:
        lines.append(f'*{t["nothing"]}*')
    lines += ['', f'{t["legend"]}: {" ".join(f"{STATUS_ICON[s]} {st[s]}" for s in STATUS)}, ~ {t["est"]}. ' + t['foot']]
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
    found = all_findings(base, config, data)
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



# ---------- Ausgabe als Datei (#364) ----------

COLOR = {'documented': '#2f6f4e', 'reported': '#3d6fa8', 'uncertain': '#a8782f', 'invented': '#8a4fa8'}
EXPORT = 'story/zeitleiste.html'


def export_html(base, config, language='de'):
    """Eigenständige HTML-Datei: statisches SVG (Spur je Figur, Punkt bzw. Balken je Eintrag), Hinweise, Liste.
    Ohne Skript und ohne Netz lesbar; nie Teil des Buchs."""
    en = language == 'en'
    t = TEXT['en' if en else 'de']
    st, kd = (STATUS_EN, KIND_EN) if en else (STATUS_DE, KIND_DE)
    data = read(base) or {'entries': []}
    names = char_names(config)
    entries = sorted(data.get('entries') or [], key=sort_key)
    found = [f for f in all_findings(base, config, data, language) if f['kind'] != 'undated']
    flagged = {i for f in found for i in f['entries']}
    dated = [(e, bounds(e)) for e in entries if bounds(e)[0]]
    esc = lambda x: html.escape(str(x or ''), quote=True)
    title = config['project'].get('title_short') or config['project'].get('title') or config['project'].get('working_title') or ''
    svg = ''
    if dated:
        lo = min(b[0][0] for _, b in dated)
        hi = max(((b[1] or b[0])[1] if b[1] else b[0][1]) for _, b in dated)
        rel = any(relative(e) for e, _ in dated)
        y0, y1 = lo.year, max(hi.year, lo.year) + 1
        lanes = []
        for e, _ in dated:
            for k in (e.get('characters') or ['@none']):
                if k not in lanes:
                    lanes.append(k)
        left, width, lane_h, top = 160, 760, 34, 30
        if rel:   # Erzählzeit (#379): Achse in Tagen, Uhrzeit als Bruchteil des Tags
            d0, d1 = lo, hi + ONE_DAY
            total = (d1 - d0).days or 1
            x = lambda d, m=0: left + width * ((d - d0).days + m / 1440) / total
        else:
            total = (datetime.date(y1, 1, 1) - datetime.date(y0, 1, 1)).days or 1
            x = lambda d, m=0: left + width * (d - datetime.date(y0, 1, 1)).days / total
        parts = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {left + width + 20} {top + lane_h * len(lanes) + 30}" '
                 f'role="img" aria-label="{esc(t["title"].lstrip("#🕰️ "))}">']
        if rel:
            days = (d1 - d0).days
            step = max(1, days // 12)
            ticks = [(d0 + datetime.timedelta(days=i), day_label((d0 - EPOCH_BASE).days + i, language)) for i in range(0, days + 1, step)]
        else:
            step = max(1, (y1 - y0) // 10)
            ticks = [(datetime.date(y, 1, 1), str(y)) for y in range(y0, y1 + 1, step)]
        for d, label in ticks:
            xx = x(d)
            parts.append(f'<line x1="{xx:.1f}" y1="{top - 8}" x2="{xx:.1f}" y2="{top + lane_h * len(lanes)}" stroke="#ddd"/>'
                         f'<text x="{xx:.1f}" y="{top - 12}" font-size="11" text-anchor="middle" fill="#555">{esc(label)}</text>')
        for n, k in enumerate(lanes):
            yy = top + lane_h * n + lane_h / 2
            label = ('Without character' if en else 'Ohne Figur') if k == '@none' else names.get(k, k)
            parts.append(f'<text x="{left - 8}" y="{yy + 4:.1f}" font-size="12" text-anchor="end">{esc(label)}</text>'
                         f'<line x1="{left}" y1="{yy:.1f}" x2="{left + width}" y2="{yy:.1f}" stroke="#eee"/>')
        for e, (start, end) in dated:
            color = COLOR.get(e.get('status'), '#666')
            stroke = ' stroke="#c0392b" stroke-width="2"' if e['id'] in flagged else ''
            tip = f'<title>{esc(date_label(e, language))} {esc(e["what"])} ({esc(st.get(e.get("status"), ""))})</title>'
            for k in (e.get('characters') or ['@none']):
                yy = top + lane_h * lanes.index(k) + lane_h / 2
                if e.get('kind') == 'span':
                    a, b = x(start[0]), x(end[1]) if end else left + width
                    parts.append(f'<rect x="{a:.1f}" y="{yy - 6:.1f}" width="{max(b - a, 3):.1f}" height="12" rx="3" '
                                 f'fill="{color}" fill-opacity="0.35"{stroke}>{tip}</rect>')
                else:
                    mins = int(e['time'][:2]) * 60 + int(e['time'][3:]) if rel and e.get('time') else (720 if rel else 0)
                    parts.append(f'<circle cx="{x(start[0], mins):.1f}" cy="{yy:.1f}" r="5" fill="{color}"{stroke}>{tip}</circle>')
        parts.append('</svg>')
        svg = ''.join(parts)
    rows = ''.join(f'<tr><td>{esc(date_label(e, language))}</td><td>{STATUS_ICON.get(e.get("status"), "")} {esc(st.get(e.get("status"), ""))}</td>'
                   f'<td>{esc(e["what"])}</td><td>{esc(", ".join(names.get(c, c) for c in e.get("characters") or []))}</td>'
                   f'<td>{esc(e.get("place"))}</td><td>{esc(e.get("source"))}</td><td><code>{esc(e["id"])}</code></td></tr>'
                   for e in entries)
    hints = ''.join(f'<li><b>{esc(kd[f["kind"]])}:</b> {esc(f["text"])} <code>{esc(", ".join(f["entries"]))}</code></li>' for f in found)
    head = ('Date', 'Status', 'What', 'Who', 'Where', 'Source', 'ID') if en else ('Datum', 'Belegstand', 'Was', 'Wer', 'Wo', 'Quelle', 'ID')
    return (f'<!DOCTYPE html>\n<html lang="{"en" if en else "de"}"><head><meta charset="utf-8">'
            f'<title>{esc(t["title"].lstrip("#🕰️ "))} – {esc(title)}</title>'
            '<style>body{font:14px/1.45 system-ui,sans-serif;margin:2em auto;max-width:960px;color:#222}'
            'table{border-collapse:collapse;width:100%}td,th{border-bottom:1px solid #ddd;padding:4px 6px;text-align:left;vertical-align:top}'
            'svg{width:100%;height:auto}.legend span{margin-right:1em}@media print{body{margin:0}}</style></head><body>'
            f'<h1>{esc(t["title"].lstrip("#🕰️ "))}: {esc(title)}</h1>'
            f'<p>{len(entries)} {t["entries"]} · {len(found)} {t["hint"] if len(found) == 1 else t["hints"]}</p>'
            + (svg or f'<p>{esc(t["empty"] if not entries else t["undated"])}</p>')
            + '<p class="legend">' + ''.join(f'<span style="color:{COLOR[s]}">{STATUS_ICON[s]} {esc(st[s])}</span>' for s in STATUS) + '</p>'
            + f'<h2>{esc(t["box"])}</h2>' + (f'<ul>{hints}</ul>' if hints else f'<p>{esc(t["none"])}</p>')
            + f'<h2>{esc(t["list"])}</h2><table><tr>' + ''.join(f'<th>{h}</th>' for h in head) + f'</tr>{rows}</table>'
            + f'<p><small>{esc(t["foot"])}</small></p></body></html>\n')



# ---------- Ältere Chronologie im Markdown-Format einlesen (#379) ----------

MD_SOURCE = 'story/chronologie.md'
DAY_RX = re.compile(r'^\s*(?:Tag\s*0|([−+-])\s*(\d+)\s*Tage?)\b', re.I)
TIME_RX = re.compile(r'(\d{1,2})[:.](\d{2})(?:\s*[–-]\s*(\d{1,2})[:.](\d{2}))?')
HOUR_RX = re.compile(r'(?<![\d:.])(\d{1,2})\s*Uhr\b')


def md_rows(text):
    """Zeilen der ersten Tabelle: (kopf, [zeilen]) mit Zellen als Liste."""
    rows = [l for l in text.splitlines() if l.strip().startswith('|')]
    cells = [[c.strip() for c in r.strip().strip('|').split('|')] for r in rows]
    cells = [c for c in cells if not all(set(x) <= set('-: ') for x in c)]
    return (cells[0], cells[1:]) if cells else ([], [])


def import_md(base, config, source=MD_SOURCE):
    """Vorschläge aus einer Tabelle in story/chronologie.md (Spalten: Abstand, Wochentag/Zeit, Ereignis, Abschnitt).
    Nichts wird geraten: „Tag 0“, „−3 Tage“, „+14 Tage“ werden zu day, „21:31–21:44“ zu time/time_to; Angaben wie
    „Monate später“ bleiben ohne Tag (nur date_text). → Vorschlagsdaten wie ein Analyselauf (items, epoch)."""
    path = Path(base) / source
    head, rows = md_rows(path.read_text(encoding='utf-8'))
    if len(head) < 3:
        raise SystemExit(f'{source}: keine Tabelle mit mindestens drei Spalten gefunden')
    label = re.sub(r'^Abstand zu[mr]?\s+', '', head[0]).strip() or 'Tag 0'
    by_number = {f'{ci}.{si}': ch['id'] for ci, ch in enumerate(config['structure']['chapters'], start=1)
                 for si, _ in enumerate(ch['sections'], start=1)}
    items, weekday = [], None
    for cells in rows:
        cells += [''] * (4 - len(cells))
        when, clock, what, where = cells[:4]
        if not what:
            continue
        item = {'kind': 'event', 'what': ' '.join(what.split()), 'status': 'invented', 'source': source,
                'evidence': [{'where': source, 'quote': ' '.join(' | '.join(cells[:3]).split())[:200]}]}
        m = DAY_RX.match(when)
        if m and not re.match(r'^\s*vor\b', when, re.I):
            item['day'] = 0 if not m.group(2) else (-1 if m.group(1) in '−-' else 1) * int(m.group(2))
            t = TIME_RX.search(clock)
            h = HOUR_RX.search(clock) if not t else None
            if h and int(h.group(1)) < 24:
                item['time'] = f'{int(h.group(1)):02d}:00'
            if t:
                item['time'] = f'{int(t.group(1)):02d}:{t.group(2)}'
                if t.group(3):
                    item['time_to'] = f'{int(t.group(3)):02d}:{t.group(4)}'
            if item['day'] == 0 and not weekday:
                first = clock.split(',')[0].split()[0] if clock else ''
                weekday = next((WEEKDAYS[i] for i, n in enumerate(WEEKDAY_DE) if first.startswith(n)), None)
        text = clock if 'day' in item else ' · '.join(x for x in (when, clock) if x)
        if text:
            item['date_text'] = text
        num = re.search(r'\d+\.\d+', where or '')
        if num and num.group(0) in by_number:
            item['chapter'] = by_number[num.group(0)]
        items.append(item)
    for n, it in enumerate(items, start=1):   # Reihenfolge der Tabelle bleibt
        it['n'] = n
    have = {(norm(e.get('what'))) for e in (read(base) or {}).get('entries') or [] if isinstance(e, dict)}
    for it in items:
        if norm(it['what']) in have:
            it['existing'] = next(e['id'] for e in read(base)['entries'] if norm(e.get('what')) == norm(it['what']))
    epoch = {'label': label}
    if weekday:
        epoch['weekday'] = weekday
    return {'items': items, 'epoch': epoch}


def import_md_run(base, config, source=MD_SOURCE, now=None):
    """import_md als Lauf analysis/chronology/run-NNN (wie ein Chat-Lauf, ohne KI): ansehen mit analysis-suggest,
    übernehmen nur nach Auswahl mit analyze.py apply --kind chronology."""
    import analyze
    data = import_md(base, config, source)
    now = now or datetime.datetime.now().astimezone().isoformat(timespec='seconds')
    folder = Path(base) / 'analysis' / 'chronology'
    folder.mkdir(parents=True, exist_ok=True)
    run_id = analyze.next_run(folder)
    out = dict({'kind': 'chronology', 'scope': 'book', 'run': run_id, 'created_at': now, 'source': 'import'}, **data)
    (folder / f'{run_id}.json').write_text(json.dumps(out, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    head = {'id': run_id, 'type': 'analysis', 'kind': 'chronology', 'scope': 'book', 'created_at': now, 'source': 'import',
            'provider': None, 'model': None, 'merge_model': None, 'blocks_analysed': 0, 'blocks_cached': 0,
            'suggestions': len(data['items']), 'dropped_without_evidence': 0, 'input_tokens': 0, 'output_tokens': 0,
            'cost': None, 'result': f'{run_id}.json'}
    body = [f'# Chronologie-Analyse {run_id[4:]} (aus {source})', '',
            f'{len(data["items"])} Vorschläge aus der Tabelle, ohne KI. Übernommen wird nichts automatisch.']
    (folder / f'{run_id}.md').write_text('---\n' + yaml.safe_dump(head, allow_unicode=True, sort_keys=False) + '---\n\n'
                                         + '\n'.join(body) + '\n', encoding='utf-8')
    return run_id, data


def main(argv):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('project')
    ap.add_argument('cmd', choices=['check', 'export', 'import-md'])
    ap.add_argument('--json', action='store_true')
    ap.add_argument('--out', help=f'bei export: Zieldatei (Standard {EXPORT})')
    ap.add_argument('--language', choices=['de', 'en'], default='de')
    a = ap.parse_args(argv[1:])
    base, config = load(a.project)
    data = read(base)
    if a.cmd == 'import-md':
        run_id, out = import_md_run(base, config)
        print(f'✓ analysis/chronology/{run_id}.json: {len(out["items"])} Vorschläge aus {MD_SOURCE} '
              f'(Tag 0 = {out["epoch"]["label"]}); ansehen mit render_view.py analysis-suggest --draft analysis/chronology/{run_id}.json')
        return 0
    if a.cmd == 'export':
        out = Path(a.out) if a.out else Path(base) / EXPORT
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(export_html(base, config, a.language), encoding='utf-8')
        print(f'✓ {out}')
        return 0
    found = all_findings(base, config, data, a.language) if data else []
    kd = KIND_EN if a.language == 'en' else KIND_DE
    if a.json:
        print(json.dumps({'entries': len((data or {}).get('entries') or []), 'findings': found}, ensure_ascii=False, indent=1))
    else:
        print('\n'.join(f'{kd[f["kind"]]}: {f["text"]}' for f in found) or ('no notes' if a.language == 'en' else 'keine Hinweise'))
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
