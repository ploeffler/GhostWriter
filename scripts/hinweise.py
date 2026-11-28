#!/usr/bin/env python3
"""Hinweisdurchsicht (#367, Teil 1): offene Befunde aus Prüfberichten sammeln und den Dialog zum Durchsehen vorbereiten.

Befunde stehen maschinenlesbar neben dem Bericht in `editorial/<bericht>.yml` (Schema
`schemas/findings.schema.json`). Die Hinweisdurchsicht liest nur diese Dateien, keinen Freitext.

  python3 scripts/hinweise.py collect <buch> [--chapter kap-01 …] [--date JJJJ-MM-TT] [--merge | --new]
      sammelt alle offenen Befunde und schreibt editorial/durchsicht-<datum>.yml; gibt es die Datei schon,
      bricht es ab (#438): --merge hängt neue Befunde an und lässt vorhandene Einträge samt Entscheidungen
      unverändert, --new legt durchsicht-<datum>-2.yml (nächste freie Nummer) an
  python3 scripts/hinweise.py show <buch> [--file editorial/durchsicht-….yml] [--open]
      Textfassung des Dialogs: kapitelweise alt und neu, darunter die Autorenentscheidungen
  python3 scripts/hinweise.py decide <buch> <eintrag> --decision ja|nein|geändert [--new TEXT] [--answer TEXT] [--file …]
      schreibt nur `entscheidung` (und bei „geändert“ `neu`) in die Dialogdatei; `--answer` speichert die Antwort auf
      `frage` getrennt in `antwort` (#675): `neu` bleibt reiner Ersatztext für `alt`
  python3 scripts/hinweise.py lock <buch> --reason TEXT [--file …] | unlock <buch> [--file …]
      Dialogdatei sperren (#675): `apply` und `accept` brechen mit dem Grund ab, `decide` bleibt erlaubt
  python3 scripts/hinweise.py show <buch> --stufen [--round N] [--size 5] [--gering] [--group GRUPPE] | --alle
      Abarbeitung in Stufen (#570): 1. Blockierendes einzeln, 2. gleiche Muster als eine Entscheidung
      (ab drei Einträgen gleicher Art und gleichen Befunds), 3. der Rest in Runden zu höchstens fünf nach
      Schweregrad mit Fortschritt, 4. „gering“ zugeklappt als Zahl. Ab 12 offenen Einträgen ist das die
      Voreinstellung für `show`; `--alle` zeigt die ganze Liste
  python3 scripts/hinweise.py decide <buch> --group GRUPPE --decision ja|nein | --gering
      eine Gruppe wie vorgeschlagen annehmen (ja, nur Einträge mit Vorschlag) bzw. lassen (nein); --gering lässt
      alle geringen offenen Einträge
  python3 scripts/hinweise.py accept <buch> [--chapter …] [--file …]
      Rundumprüfung (#565): alle offenen Einträge mit konkretem Vorschlag (alt → neu) annehmen, auch
      Autorenentscheidungen; nie blockierende, buchweite oder solche mit mehreren Varianten
  python3 scripts/hinweise.py plan <buch> [--chapter …] [--file …]
      vor dem Umsetzen (Teil 2): je Eintrag ✅ umsetzbar, ⚠️ von Hand, ⛔ abgeschlossen (erst wieder öffnen); sieht `neu`
      nach Antwort oder Anweisung statt Ersatztext aus, ⚠️ statt ✅ (#675)
  python3 scripts/hinweise.py apply <buch> [--chapter …] [--file …]
      setzt die ✅-Einträge ins Manuskript um, schreibt den Befundstatus zurück und nennt die Nachprüfung

Prüfung beim Anlegen: `alt` muss im heutigen Manuskript des Abschnitts genau einmal vorkommen, sonst wird
der Befund nicht aufgenommen und unter `ausgelassen` gemeldet. „Ohne Autor lösbar“ ist ein Eintrag nur bei
einer rein sprachlichen Art mit Vorschlag `neu`; alles andere – und im Zweifel – ist eine Autorenentscheidung.
`collect`, `show` und `decide` ändern kein Manuskript. Erst `apply` setzt entschiedene Einträge um, und nur in
Abschnitten, die nicht abgeschlossen sind: Wiederöffnen bleibt eine eigene, ausdrücklich bestätigte Freigabe
(START.md, „Freigaben“). Eine Nachprüfung trägt `apply` nicht selbst ein; sie gehört nach dem Neulesen dazu.
"""
import argparse
import datetime
import hashlib
import json
import math
import re
import subprocess
import sys
from pathlib import Path

import yaml

LANGUAGE_KINDS = ('rechtschreibung', 'zeichensetzung', 'grammatik', 'wiederholung', 'satzbau', 'sprache')
AUTHOR_KINDS = ('fakt', 'kontinuitaet', 'ton', 'aufbau', 'buchweit')
KINDS = LANGUAGE_KINDS + AUTHOR_KINDS
SEVERITIES = ('gering', 'mittel', 'wesentlich', 'blockierend')
FINDING_STATES = ('offen', 'erledigt', 'entschieden')
DECISIONS = ('offen', 'ja', 'nein', 'geändert')
GUIDE = ('Je Eintrag entscheiden: ja = übernehmen, nein = nicht ändern, geändert = mit eigener Fassung in `neu`. '
         'Jede Antwort wird sofort als kleiner Nachtrag gespeichert (docs/SPEICHERN.md). Umgesetzt wird erst am '
         'Ende eines Kapitels oder auf Auftrag; Wiederöffnen abgeschlossener Kapitel braucht eine eigene Bestätigung.')
QUESTION = {'fakt': 'Welche Angabe ist richtig bzw. fehlt?',
            'kontinuitaet': 'Welche Fassung gilt, und wo muss angeglichen werden?', 'ton': 'Soll sich Ton oder Stimme hier ändern?',
            'aufbau': 'Soll der Aufbau so geändert werden?', 'buchweit': 'Soll das im ganzen Buch so gelten?'}
SENTENCE = re.compile(r'[^.!?…\n]+(?:[.!?…]+[»«“”"\')\]]*|\n|$)')
GROUP_MIN = 3        # ab so vielen Einträgen gleicher Art und gleichen Befunds eine Gruppenentscheidung (#570)
ROUND_SIZE = 5       # höchstens so viele Einträge je Runde
STAGE_MIN = 12       # ab so vielen offenen Einträgen zeigt `show` die Stufen von selbst
RANK = {'blockierend': 0, 'wesentlich': 1, 'mittel': 2, 'gering': 3}
GROUP_PREFIX = 'gruppe:'
_LEAD = re.compile(r'^(?:\s|…|\.\.\.)+')
_TRAIL = re.compile(r'(?:\s|…|\.\.\.)+$')


def wording(text, alt, neu):
    """(alt, neu), wie sie im Text zu ersetzen sind, oder None (#522). Erst unverändert (genau ein Treffer), sonst ohne
    einfassende Auslassungspunkte und Leerzeichen, die aus dem Befund mitgekommen sind; bei `neu` fallen nur dieselben
    Ränder weg, damit nichts zusätzlich verschwindet."""
    if text.count(alt) == 1:
        return alt, neu
    lead, trail = _LEAD.match(alt), _TRAIL.search(alt)
    a = alt[(lead.end() if lead else 0):(trail.start() if trail else len(alt))]
    if not a or text.count(a) != 1:
        return None
    n = _LEAD.sub('', neu, count=1) if lead else neu
    n = _TRAIL.sub('', n, count=1) if trail else n
    return a, n


def has_change(e):
    """Hat der Eintrag eine Fassung oder eine Streichung als Vorschlag? Ein leeres `neu` allein heißt „kein Vorschlag“,
    eine Streichung trägt `streichen: true` (#615)."""
    return bool(e.get('neu') or e.get('streichen'))


_INSTRUCTION = re.compile(
    r'(→|->|=>)|\b(?:entsprechend|bitte|überall|jeweils)\b.*\b(?:ändern|anpassen|angleichen|ergänzen|umschreiben|streichen|'
    r'einfügen|ersetzen|korrigieren)\b', re.IGNORECASE | re.DOTALL)
_LIST_LINE = re.compile(r'^\s*(?:[-*•]\s|\d+[.)]\s|\d{3,4}\s*[:–-])')
SHORT_WORDS = 2      # so wenige Wörter in `neu` …
LONG_WORDS = 6       # … für so viele Wörter in `alt` sind eher eine Antwort als ein Ersatz (#675)


def not_replacement(e):
    """Grund, warum `neu` nicht wie ein Ersatztext für `alt` aussieht, sonst '' (#675). Gilt für Antworten auf die Frage
    („Hafen“ für einen ganzen Satz), Anweisungen („… entsprechend ändern“, Pfeile) und Listen bzw. Zeitleisten. Eine Fassung,
    die der Autor ausdrücklich als Text bestätigt hat (`ersatz_bestaetigt`, `decide --as-text`), gilt als Ersatz."""
    neu, alt = str(e.get('neu') or ''), str(e.get('alt') or '')
    if not neu or e.get('streichen') or e.get('ersatz_bestaetigt'):
        return ''
    if e.get('antwort') and neu.strip() == str(e['antwort']).strip():
        return '`neu` ist die Antwort auf die Frage'
    if looks_like_question(neu) and not looks_like_question(alt):
        return '`neu` ist eine Frage'
    if _INSTRUCTION.search(neu) and not _INSTRUCTION.search(alt):
        return '`neu` sieht nach einer Anweisung aus'
    lines = [x for x in neu.splitlines() if x.strip()]
    if len(lines) > max(1, len([x for x in alt.splitlines() if x.strip()])) and any(_LIST_LINE.match(x) for x in lines):
        return '`neu` ist eine Liste bzw. Zeitleiste'
    if len(alt.split()) >= LONG_WORDS and len(neu.split()) <= SHORT_WORDS and len(neu) * 4 < len(alt):
        return '`neu` ist viel kürzer als `alt` (eher eine Antwort als ein Ersatz)'
    return ''


def locked(data):
    """Grund der Sperre der Dialogdatei (`gesperrt`, #675) oder ''."""
    return str(data.get('gesperrt') or '').strip()


def tidy_deletion(body, a):
    """`a` einmal aus `body` entfernen und das überzählige Leerzeichen davor oder danach mitnehmen (#615): mitten im Absatz
    bleibt ein Leerzeichen, am Absatzende und -anfang keines, vor Satzzeichen keines."""
    i = body.index(a)
    before, after = body[:i], body[i + len(a):]
    if before.endswith(' ') and (after[:1] in ('', ' ', '\n') or after[:1] in '.,;:!?)'):
        before = before[:-1]
    elif after.startswith(' ') and (before == '' or before.endswith('\n')):
        after = after[1:]
    return before + after


def editorial(base):
    return Path(base) / 'editorial'


def is_findings_file(path):
    return path.suffix == '.yml' and path.name != 'checks.yml' and not path.name.startswith('durchsicht-')


def findings_files(base):
    d = editorial(base)
    return sorted(p for p in d.glob('*.yml') if is_findings_file(p)) if d.is_dir() else []


def dialog_order(path):
    """durchsicht-<datum>.yml vor durchsicht-<datum>-2.yml, -3 … (#438)."""
    m = re.fullmatch(r'durchsicht-(.+?)(?:-(\d+))?\.yml', path.name)
    return (m.group(1), int(m.group(2) or 1)) if m else (path.stem, 0)


def dialog_files(base):
    d = editorial(base)
    return sorted(d.glob('durchsicht-*.yml'), key=dialog_order) if d.is_dir() else []


def merge_dialog(old, new):
    """Vorhandene Einträge bleiben samt `entscheidung`, `neu` und `umgesetzt` unverändert; neue Befunde
    (nach `befund`) kommen mit fortlaufenden IDs dazu (#438)."""
    seen = {e.get('befund') for _, e in entries(old)}
    used = [int(e['id'][2:]) for _, e in entries(old) if re.fullmatch(r'e-\d+', str(e.get('id', '')))]
    n = max(used, default=0)
    added = 0
    for group in ('ohne_autor', 'autorenentscheidung'):
        old.setdefault(group, [])
        for e in new.get(group) or []:
            if e['befund'] in seen:
                continue
            n += 1
            added += 1
            e['id'] = f'e-{n:03d}'
            old[group].append(e)
    old['quelle'] = list(dict.fromkeys((old.get('quelle') or []) + (new.get('quelle') or [])))
    if new.get('fassung'):
        old['fassung'] = new['fassung']
    skipped = [x for x in new.get('ausgelassen') or [] if x.get('befund') not in seen]
    if skipped:
        old['ausgelassen'] = skipped
    else:
        old.pop('ausgelassen', None)
    return old, added


def read_yaml(path):
    return yaml.safe_load(Path(path).read_text(encoding='utf-8')) or {}


def head_comments(text):
    """Führender Kommentarblock einer YAML-Datei (Kommentar- und Leerzeilen bis zur ersten Zeile mit Inhalt)."""
    head = []
    for line in text.splitlines(keepends=True):
        if line.strip() == '' or line.lstrip().startswith('#'):
            head.append(line)
        else:
            break
    while head and head[-1].strip() == '':
        head.pop()
    return ''.join(head)


_TOP_LEVEL_KEY = re.compile(r'^([^\\s#][^:]*):(?:[ \\t].*|[ \\t]*$)')


def _dump_yaml(data):
    """Bisherige YAML-Serialisierung; Fallback für nicht sicher zerlegbare Dateien."""
    return yaml.safe_dump(data, allow_unicode=True, sort_keys=False, width=100)


def _top_blocks(text):
    """Zerlegt eine Top-Level-Zuordnung in Originaltextblöcke.

    Kommentare und Leerzeilen auf Spaltenebene 0 vor einem Schlüssel gehören zu
    dessen Block. Der führende Kommentarblock wird zusätzlich von head_comments
    behandelt. Unbekannte YAML-Formen werden später durch Parsevergleich erkannt.
    """
    blocks, key, current, pending = [], None, [], []
    for line in text.splitlines(keepends=True):
        if not line.startswith((' ', '\\t')) and (not line.strip() or line.startswith('#')):
            pending.append(line)
            continue
        match = _TOP_LEVEL_KEY.match(line)
        if match:
            if key is not None:
                blocks.append((key, current))
            elif current:
                blocks.append((None, current))
            elif pending:
                blocks.append((None, pending))
            key = match.group(1).strip()
            current, pending = pending + [line], []
        else:
            current.extend(pending)
            pending = []
            current.append(line)
    if pending:
        if current:
            current.extend(pending)
        else:
            blocks.append((None, pending))
    if current:
        blocks.append((key, current))
    return blocks


def _block_prefix(lines):
    """Kommentare/Leerzeilen vor dem eigentlichen Top-Level-Schlüssel."""
    for i, line in enumerate(lines):
        if _TOP_LEVEL_KEY.match(line):
            return lines[:i]
    return []


def _list_items(lines):
    """Zerlegt eine YAML-Liste; bei mehrdeutigen Randkommentaren None zurückgeben."""
    head, items, pending = [], [], []
    for line in lines:
        if re.match(r'^  - ', line):
            items.append(pending + [line])
            pending = []
        elif items and (re.match(r'^  #', line) or not line.strip()):
            pending.append(line)
        elif items:
            # Ein nicht eingerückter Kommentar am Blockende lässt sich nicht
            # sicher einem Listenelement zuordnen: lieber vollständig dumpen.
            if line.startswith('#') or not line.strip():
                return None
            items[-1].extend(pending)
            pending = []
            items[-1].append(line)
        else:
            head.append(line)
    if pending:
        return None
    return head, items


def _parsed_list_items(key, items):
    """Liest jedes Originalelement einzeln; None signalisiert eine unsichere Trennung."""
    parsed = []
    for item in items:
        try:
            value = yaml.safe_load(key + ':\\n' + ''.join(item))
        except yaml.YAMLError:
            return None
        if not isinstance(value, dict) or key not in value or not isinstance(value[key], list) or len(value[key]) != 1:
            return None
        parsed.append(value[key][0])
    return parsed


def merge_yaml(old_text, data):
    """Erzeugt YAML und übernimmt unveränderte Originalblöcke zeichengetreu (#717).

    Nur wenn Schlüssel und Listenelemente zweifelsfrei erkannt und einzeln
    zurückgeparst werden können, wird partiell übernommen. Sonst greift der
    bisherige vollständige safe_dump.
    """
    if not isinstance(data, dict):
        return _dump_yaml(data)
    try:
        old = yaml.safe_load(old_text) or {}
    except yaml.YAMLError:
        return _dump_yaml(data)
    if not isinstance(old, dict):
        return _dump_yaml(data)

    scanned = _top_blocks(old_text)
    key_blocks = [(key, lines) for key, lines in scanned if key is not None]
    keys = [key for key, _ in key_blocks]
    if len(keys) != len(old) or len(set(keys)) != len(keys) or set(keys) != set(old):
        return _dump_yaml(data)

    old_blocks = {}
    for key, lines in key_blocks:
        try:
            parsed = yaml.safe_load(''.join(lines))
        except yaml.YAMLError:
            return _dump_yaml(data)
        if parsed != {key: old[key]}:
            return _dump_yaml(data)
        old_blocks[key] = lines

    parts = []
    for key, value in data.items():
        block = old_blocks.get(key)
        if block is not None and old.get(key) == value:
            parts.append(''.join(block))
            continue
        prefix = _block_prefix(block) if block is not None else []
        if block is not None and isinstance(value, list) and isinstance(old.get(key), list):
            split = _list_items(block)
            if split is not None:
                head, items = split
                old_items = _parsed_list_items(key, items)
                fresh = _dump_yaml({key: value}).splitlines(keepends=True)
                fresh_split = _list_items(fresh)
                if fresh_split is not None:
                    _, fresh_items = fresh_split
                    fresh_values = _parsed_list_items(key, fresh_items)
                    if (old_items == old[key] and fresh_values == value
                            and len(items) == len(old_items) == len(fresh_items) == len(value)):
                        parts.append(''.join(head) + ''.join(
                            ''.join(items[i] if old_items[i] == value[i] else fresh_items[i])
                            for i in range(len(items))))
                        continue
        parts.append(''.join(prefix) + _dump_yaml({key: value}))
    return ''.join(parts)


def write_yaml(path, data):
    """Schreibt YAML; unveränderte Einträge und der Kopfkommentar bleiben erhalten (#717).

    Kommentare innerhalb eines geänderten Eintrags können entfallen. Ein
    Kommentar ist nur ein Vermerk, keine wirksame Sperre: dafür gilt das Feld
    `gesperrt` (siehe `locked()`, #675).
    """
    p = Path(path)
    old_text = p.read_text(encoding='utf-8') if p.is_file() else ''
    head = head_comments(old_text)
    body = merge_yaml(old_text, data) if old_text else _dump_yaml(data)
    if head and not body.startswith(head):
        body = head + '\\n' + body if not head.endswith('\\n') else head + body
    p.write_text(body, encoding='utf-8')


BOOK = 'book'   # buchweiter Befund (#423): kein Abschnitt, nur Autorenentscheidung


def section_index(config):
    """{id: (bezeichnung, kapitel, eintrag)}: Abschnitte als „1.2“ mit Kapitel; Teile von Vor- und
    Nachspann (mat-*, #423) mit ihrem Titel und ohne Kapitel; `book` für buchweite Befunde."""
    from render_view import matter_items
    out = {}
    for cn, ch in enumerate(config['structure']['chapters'], start=1):
        for sn, s in enumerate(ch['sections'], start=1):
            out[s['id']] = (f'{cn}.{sn}', ch, s)
    for _, item in matter_items(config):
        out[item['id']] = (item.get('title') or item['id'], None, item)
    out[BOOK] = ('Buch', None, None)
    return out


def where(e):
    """Überschrift einer Gruppe: „Kapitel 2“, sonst Titel des Teils bzw. „Buch“ (#423)."""
    return f'Kapitel {e["abschnitt"].split(".")[0]}' if e.get('chapter_id') else e['abschnitt']


def context(text, alt):
    """Betroffener Satz mit bis zu zwei Sätzen davor und danach (#367)."""
    start = text.index(alt)
    end = start + len(alt)
    spans = [m.span() for m in SENTENCE.finditer(text) if m.group().strip()]
    first = next((i for i, (a, b) in enumerate(spans) if b > start), 0)
    last = next((i for i, (a, b) in enumerate(spans) if b >= end), len(spans) - 1)
    a, b = spans[max(0, first - 2)][0], spans[min(len(spans) - 1, last + 2)][1]
    return re.sub(r'\s+', ' ', text[a:b]).strip()


def paragraph(text, number):
    """Absatz Nr. `number` (1-basiert, durch Leerzeilen getrennt) als Zusammenhang für Einträge ohne alten Wortlaut (#473)."""
    parts = [x.strip() for x in re.split(r'\n\s*\n', text or '') if x.strip()]
    if isinstance(number, int) and 1 <= number <= len(parts):
        return re.sub(r'\s+', ' ', parts[number - 1])
    return ''


def _file_date(path):
    m = re.search(r'(\d{4}-\d{2}-\d{2})', path.stem)
    return m.group(1) if m else ''


def collect_themes(base, config=None):
    """Themen der Befunddateien (#570): ([{id, titel}] in Reihenfolge, {Datei#befund: thema}).

    Reihenfolge (#606): zuerst Themen, die nur buchweite Befunde (`abschnitt: book`) enthalten, danach die übrigen in der
    Reihenfolge der Kapitel (Kapitel der frühesten Befundstelle der Datei); bei gleichem Kapitel gilt die neueste Datei nach
    Datum im Namen (nicht die Namenssortierung), ihre Themen kommen zuerst. Innerhalb einer Datei bleibt die Reihenfolge der
    Liste `themen`. Befunde anderer Berichte werden als `<bericht>.yml#b-001` zugeordnet."""
    index = section_index(config) if config else {}
    chapter_no = {ch['id']: n for n, ch in enumerate((config or {}).get('structure', {}).get('chapters') or [], start=1)}

    def chapter_of(sid):
        if sid == BOOK:
            return 0
        _, ch, _ = index.get(sid, (None, None, None))
        return chapter_no.get((ch or {}).get('id'), len(chapter_no) + 1)   # Vor-/Nachspann und Unbekanntes hinter den Kapiteln

    files = []
    for path in findings_files(base):
        data = read_yaml(path)
        if data.get('themen'):
            places = [chapter_of(f.get('abschnitt')) for f in data.get('befunde') or [] if f.get('abschnitt') != BOOK]
            files.append((path, data, min(places) if places else 0))
    files.sort(key=lambda f: (_file_date(f[0]), f[0].name), reverse=True)   # neueste zuerst …
    files.sort(key=lambda f: f[2])                                          # … stabil nach Kapitel
    kind = {}   # (Datei, Befund-ID) → Abschnitt, für buchweite Themen auch über Berichte hinweg
    for path in findings_files(base):
        for f in read_yaml(path).get('befunde') or []:
            kind[(path.name, f.get('id'))] = f.get('abschnitt')
    bookwide, rest, titles, of = [], [], {}, {}
    for path, data, _ in files:
        for t in data['themen']:
            members = [kind.get((Path(str(r).rpartition('#')[0]).name or path.name, str(r).rpartition('#')[2])) for r in t.get('befunde') or []]
            if t['id'] not in titles:
                titles[t['id']] = t['titel']
                (bookwide if members and all(m == BOOK for m in members) else rest).append(t['id'])
            for ref in t.get('befunde') or []:
                name, _, bid = str(ref).rpartition('#')
                of.setdefault(f'{Path(name).name or path.name}#{bid}', t['id'])
    return [{'id': i, 'titel': titles[i]} for i in bookwide + rest], of


def collect(base, config, chapters=None, date=None, commit=None, mode=None):
    """Offene Befunde sammeln; Rückgabe (Pfad, Daten). Schreibt die Dialogdatei.

    Gibt es die Dialogdatei des Tages schon, ohne `mode` Abbruch (#438); `mode='merge'` hängt an,
    `mode='new'` schreibt durchsicht-<datum>-<n>.yml."""
    import checks
    base = Path(base)
    index = section_index(config)
    chapters = set(chapters or [])
    unknown = chapters - {ch['id'] for ch in config['structure']['chapters']}
    if unknown:
        raise ValueError(f'Unbekanntes Kapitel: {", ".join(sorted(unknown))}')
    auto, author, skipped, sources = [], [], [], []
    themes, theme_of = collect_themes(base, config)
    for path in findings_files(base):
        data = read_yaml(path)
        rel = path.relative_to(base).as_posix()
        for f in data.get('befunde') or []:
            if f.get('status', 'offen') != 'offen':
                continue
            ref = f'{rel}#{f.get("id")}'
            sid = f.get('abschnitt')
            if sid not in index:
                skipped.append({'befund': ref, 'grund': f'Abschnitt {sid} unbekannt'})
                continue
            number, ch, s = index[sid]
            if chapters and (not ch or ch['id'] not in chapters):
                continue   # Kapitelauswahl: Vor-/Nachspann und buchweite Befunde nicht
            if rel not in sources:
                sources.append(rel)
            text = checks.manuscript(base, config, sid) or ''
            alt = f.get('alt') or ''
            entry = {'id': '', 'befund': ref, 'abschnitt': number, 'section_id': sid,
                     'chapter_id': ch['id'] if ch else '', 'chapter_status': ch.get('status', '') if ch else '',
                     'datei': s['path'] if s else ''}
            if f.get('absatz') is not None:
                entry['absatz'] = f['absatz']
            entry.update({'art': f.get('art', ''), 'grund': f.get('befund', '')})
            if alt and sid != BOOK:
                found = wording(text, alt, f.get('neu') or '')
                if found is None:
                    hits = text.count(alt)
                    skipped.append({'befund': ref, 'grund': (f'alter Wortlaut kommt {hits}-mal vor (erwartet: genau einmal)' if hits
                                                             else 'alter Wortlaut nicht gefunden')})
                    continue
                entry.update({'kontext': context(text, found[0]), 'alt': alt})
            else:
                entry.update({'kontext': paragraph(text, f.get('absatz')) if sid != BOOK else '', 'alt': alt})   # #473
            entry['neu'] = f.get('neu') or ''
            thema = f.get('thema') or theme_of.get(f'{Path(rel).name}#{f.get("id")}')
            if thema in {t['id'] for t in themes}:
                entry['thema'] = thema   # #570
            if f.get('muster'):
                entry['muster'] = f['muster']
            if f.get('schweregrad'):
                entry['schweregrad'] = f['schweregrad']
            if f.get('varianten'):
                entry['varianten'] = list(f['varianten'])
            entry['entscheidung'] = 'offen'
            solvable = (f.get('art') in LANGUAGE_KINDS and alt and entry['neu'] and entry['neu'] != alt
                        and sid != BOOK and f.get('schweregrad') != 'blockierend')   # Blockierendes entscheidet der Autor (#447)
            if solvable:
                auto.append(entry)
            else:
                kind = f.get('art') if f.get('art') in AUTHOR_KINDS else 'buchweit' if sid == BOOK \
                    else 'aufbau' if not alt else 'ton'
                entry['art'] = kind
                entry['frage'] = f.get('frage') or f.get('richtung') or QUESTION[kind]
                author.append(entry)
    author.sort(key=lambda e: e.get('schweregrad') != 'blockierend')   # Blockierendes zuerst (#447), sonst Reihenfolge wie gefunden
    for n, e in enumerate(auto + author, start=1):
        e['id'] = f'e-{n:03d}'
    date = str(date or datetime.date.today().isoformat())
    p = config.get('project') or {}
    data = {'buch': p.get('title') or p.get('working_title') or '', 'fassung': commit or checks.head_commit(base) or '',
            'erstellt': date, 'quelle': sources, 'anleitung': GUIDE,
            'ohne_autor': auto, 'autorenentscheidung': author}
    if not data['fassung']:
        del data['fassung']
    used = {e.get('thema') for e in auto + author}
    if any(used):
        data['themen'] = [t for t in themes if t['id'] in used]
    if skipped:
        data['ausgelassen'] = skipped
    out = editorial(base) / f'durchsicht-{date}.yml'
    if out.exists():
        if mode == 'merge':
            data, _ = merge_dialog(read_yaml(out), data)
        elif mode == 'new':
            n = 2
            while (editorial(base) / f'durchsicht-{date}-{n}.yml').exists():
                n += 1
            out = editorial(base) / f'durchsicht-{date}-{n}.yml'
        else:
            raise ValueError(f'{out.relative_to(base).as_posix()} gibt es schon, mit möglichen Entscheidungen. '
                             'Mit --merge neue Befunde anhängen (Entscheidungen bleiben) oder mit --new eine '
                             'weitere Durchsicht für heute anlegen.')
    out.parent.mkdir(parents=True, exist_ok=True)
    write_yaml(out, data)
    return out, data


def suspicious(data):
    """[(eintrag, grund)] für noch nicht umgesetzte Einträge, deren `neu` nicht wie ein Ersatztext aussieht (#675)."""
    return [(e, why) for _, e in entries(data) if not e.get('umgesetzt') and (why := not_replacement(e))]


def latest(base):
    files = dialog_files(base)
    return files[-1] if files else None


def entries(data):
    return [('ohne_autor', e) for e in data.get('ohne_autor') or []] + \
           [('autorenentscheidung', e) for e in data.get('autorenentscheidung') or []]


def looks_like_question(text):
    """Ein Text mit Fragezeichen am Ende (Anführungszeichen und Leerraum ignoriert) ist eine Rückfrage, keine Fassung (#609)."""
    return bool(re.search(r'\?[\s\"„“»«\'’)\]]*$', str(text or '')))


def decide(path, entry_id, decision, new=None, variant=None, as_text=False, answer=None):
    """Entscheidung speichern. `answer` ist die Antwort auf `frage` (#675) und landet in `antwort`, nie in `neu`; ohne eigene
    Fassung (`--new`) bleibt `neu` dann leer bzw. der bisherige Vorschlag wandert nach `neu_befund`."""
    answer = (answer or '').strip() or None
    delete = decision == 'streichen'   # #615: Streichung als Entscheidung = „ja“ mit `streichen: true`
    if delete:
        decision, new = 'ja', None
    if variant is not None:   # #473: Variante N wählen = „geändert“ mit dem Wortlaut der Variante
        decision = 'geändert'
    if decision not in DECISIONS:
        raise ValueError(f'Unbekannte Entscheidung: {decision}')
    if decision == 'geändert' and not new and variant is None and not answer:
        raise ValueError('Bei „geändert“ gehört die eigene Fassung (--new) oder die Antwort auf die Frage (--answer) dazu')
    if decision == 'geändert' and variant is None and looks_like_question(new) and not as_text:
        raise ValueError('Das sieht wie eine Rückfrage aus, nicht wie eine Fassung: nichts gespeichert. Antworte darauf und zeige '
                         'die Karte erneut (hinweise.py ask); soll der Text trotzdem als Fassung gelten, --as-text angeben.')
    data = read_yaml(path)
    for _, e in entries(data):
        if e.get('id') == entry_id and decision == 'geändert' and variant is None and new and not as_text:
            why = not_replacement(dict(e, neu=new, antwort=answer or e.get('antwort'), ersatz_bestaetigt=False, streichen=False))
            if why:   # #675: Antwort oder Anweisung nicht als Ersatztext speichern
                raise ValueError(f'{why}: nichts gespeichert. Die Antwort auf die Frage gehört nach --answer; als Ersatz für '
                                 '`alt` den neuen Wortlaut mit --new angeben. Ist der Text wirklich die neue Fassung, --as-text.')
    for _, e in entries(data):
        if e.get('id') == entry_id:
            if e.get('umgesetzt'):
                raise ValueError(f'{entry_id} ist schon umgesetzt')
            if variant is not None:
                options = e.get('varianten') or []
                if not 1 <= variant <= len(options):
                    raise ValueError(f'{entry_id} hat {len(options)} Varianten; Variante {variant} gibt es nicht')
                new = options[variant - 1]
                e['variante'] = variant
            if delete and not e.get('alt'):
                raise ValueError(f'{entry_id} hat keinen alten Wortlaut; es gibt nichts zu streichen')
            e['entscheidung'] = decision
            if answer:
                e['antwort'] = answer
            if delete:
                e['streichen'] = True
                e['neu'] = ''
            elif new is not None:
                e['neu'] = new
                e.pop('streichen', None)   # eine neue Fassung ersetzt eine frühere Streichung
            elif answer and decision == 'geändert':
                if e.get('neu') and not e.get('neu_befund'):
                    e['neu_befund'] = e['neu']   # der frühere Vorschlag ist nicht gewählt, bleibt aber nachvollziehbar
                e['neu'] = ''
                e.pop('streichen', None)
            if as_text and decision == 'geändert' and e.get('neu'):
                e['ersatz_bestaetigt'] = True
            elif new is not None or delete or (answer and decision == 'geändert'):
                e.pop('ersatz_bestaetigt', None)
            write_yaml(path, data)
            return e
    raise ValueError(f'Eintrag {entry_id} nicht gefunden')


def propose(path, entry_id, new, variants=None, delete=False):
    """Vorschlag des Assistenten an einen offenen Eintrag schreiben (#609): `neu` (und `varianten`), gekennzeichnet mit
    `vorschlag_von: assistent`. Die Karte zeigt ihn als „neu“ bzw. „Vorschlag“; „Übernehmen“ speichert genau diesen Text."""
    new = (new or '').strip()
    if delete and new:
        raise ValueError('--delete und --new schließen sich aus')
    if not new and not delete:
        raise ValueError('Der Vorschlag ist leer (--new); eine Streichung als Vorschlag mit --delete')
    variants = [v.strip() for v in variants or [] if v and v.strip()]
    if len(variants) > 3:
        raise ValueError('Höchstens drei Varianten')
    data = read_yaml(path)
    for _, e in entries(data):
        if e.get('id') == entry_id:
            if e.get('umgesetzt') or e.get('entscheidung', 'offen') != 'offen':
                raise ValueError(f'{entry_id} ist schon entschieden; ein Vorschlag geht nur bei offenen Einträgen')
            if e.get('neu') and e.get('vorschlag_von') != 'assistent':
                e['neu_befund'] = e['neu']   # Vorschlag aus der Befunddatei bleibt nachvollziehbar
            if delete and not e.get('alt'):
                raise ValueError(f'{entry_id} hat keinen alten Wortlaut; es gibt nichts zu streichen')
            e['neu'] = new
            if delete:
                e['streichen'] = True   # #615: Streichung ist ein gültiger Vorschlag
            else:
                e.pop('streichen', None)
            e['vorschlag_von'] = 'assistent'
            if variants:
                e['varianten'] = variants
            write_yaml(path, data)
            return e
    raise ValueError(f'Eintrag {entry_id} nicht gefunden')


def lock(path, reason=None):
    """Dialogdatei sperren bzw. mit leerem Grund entsperren (#675). `decide` bleibt erlaubt, `apply` und `accept` nicht."""
    data = read_yaml(path)
    if reason and reason.strip():
        data['gesperrt'] = reason.strip()
    else:
        data.pop('gesperrt', None)
    write_yaml(path, data)
    return data


def checkpoint(base, message=None, push_to=None):
    """Zwischenstand der Durchsicht speichern (#609): ein Commit der geänderten Dialogdateien `editorial/durchsicht-*.yml`.
    Gibt (Zahl entschiedener Einträge, Commit oder None) zurück; None, wenn nichts zu speichern ist."""
    base = Path(base)

    def git(*a, check=True):
        return subprocess.run(['git', '-C', str(base), *a], capture_output=True, text=True, check=check)
    files = [p.relative_to(base).as_posix() for p in dialog_files(base)]
    if not files:
        return 0, None
    dirty = [line[3:] for line in git('status', '--porcelain', '--', *files).stdout.splitlines() if line.strip()]
    data = read_yaml(base / files[-1])
    every = entries(data)
    done = sum(1 for _, e in every if e.get('entscheidung', 'offen') != 'offen')
    if not dirty:
        return done, None
    git('add', '--', *files)
    git('commit', '-q', '-m', message or f'Hinweisdurchsicht: Zwischenstand ({done} von {len(every)} entschieden)\n\n'
        'GhostWriter-Aktion: notes_review.checkpoint')
    sha = git('rev-parse', 'HEAD').stdout.strip()
    if push_to:
        out = git('push', 'origin', f'HEAD:refs/heads/{push_to}', check=False)
        if out.returncode:
            raise ValueError(f'Push nach {push_to} fehlgeschlagen: {out.stderr.strip()[:200]}')
    return done, sha


def proposal(e):
    """Eintrag mit eindeutigem Vorschlag, den die Rundumprüfung ohne Rückfrage annehmen darf (#565): `alt` und `neu`
    vorhanden und verschieden, nicht blockierend, nicht buchweit, keine Auswahl unter mehreren Varianten."""
    return bool(e.get('alt') and e.get('neu') and e['neu'] != e['alt'] and e.get('section_id') != BOOK
                and e.get('schweregrad') != 'blockierend' and not e.get('varianten') and not not_replacement(e))   # #675


def accept(path, chapters=None, skip=()):
    """Rundumprüfung (#565): offene, nicht umgesetzte Einträge mit Vorschlag auf `ja` setzen und mit
    `angenommen: rundumpruefung` kennzeichnen. Abgeschlossenes hält danach `plan` zurück (⛔)."""
    chapters = set(chapters or [])
    data = read_yaml(path)
    if locked(data):
        raise ValueError(f'Durchsicht gesperrt: {locked(data)} (entsperren: hinweise.py unlock)')
    taken = []
    for _, e in entries(data):
        if e.get('umgesetzt') or e.get('entscheidung', 'offen') != 'offen' or not proposal(e):
            continue
        if chapters and e.get('chapter_id') not in chapters:
            continue
        if e.get('section_id') in skip:   # ausgecheckt (#572): nichts annehmen
            continue
        e['entscheidung'] = 'ja'
        e['angenommen'] = 'rundumpruefung'
        taken.append(e)
    if taken:
        write_yaml(path, data)
    return taken


def show(data, only_open=False):
    def wanted(e):
        return not only_open or e.get('entscheidung', 'offen') == 'offen'
    auto = [e for e in data.get('ohne_autor') or [] if wanted(e)]
    author = [e for e in data.get('autorenentscheidung') or [] if wanted(e)]
    total = entries(data)
    done = sum(e.get('entscheidung', 'offen') != 'offen' for _, e in total)
    lines = [f'### 🧹 Hinweisdurchsicht · {data.get("buch", "")}',
             f'Stand {data.get("erstellt", "")} · {len(total)} Einträge · {done} entschieden · {len(total) - done} offen', '']
    if locked(data):
        lines += [f'⛔ Gesperrt: {locked(data)} – entscheiden ja, umsetzen nein', '']
    if auto:
        lines += ['#### Ohne Autor lösbar', '']
        chapter = None
        for e in auto:
            if (e['chapter_id'] or e['abschnitt']) != chapter:
                chapter = e['chapter_id'] or e['abschnitt']
                lines += [f'**{where(e)}**' + (f' ({e["chapter_status"]})' if e.get('chapter_status') else ''), '']
            lines += [f'`{e["id"]}` · {e["abschnitt"]} · {e["art"]} · **{e.get("entscheidung", "offen")}** – {e.get("grund", "")}',
                      f'> alt: {e["alt"]}', f'> neu: {e.get("neu") or "(entfällt)"}', '']
    if author:
        lines += ['#### Autorenentscheidung', '']
        for e in author:
            mark = '⛔ blockierend · ' if e.get('schweregrad') == 'blockierend' else ''
            lines += [f'`{e["id"]}` · {mark}{e["abschnitt"]} · {e["art"]} · **{e.get("entscheidung", "offen")}** – {e.get("grund", "")}',
                      f'> Frage: {e.get("frage", "")}']
            if e.get('antwort'):
                lines += [f'> Antwort: {e["antwort"]}']
            if e.get('alt'):
                lines += [f'> alt: {e["alt"]}']
            if has_change(e):
                lines += [f'> Vorschlag: {e.get("neu") or "(entfällt)"}']
            for k, v in enumerate(e.get('varianten') or [], start=1):
                lines += [f'> Variante {k}: {v}']
            lines += ['']
    if data.get('ausgelassen'):
        lines += ['#### Nicht aufgenommen', ''] + [f'- {s["befund"]}: {s["grund"]}' for s in data['ausgelassen']] + ['']
    if not auto and not author:
        lines += ['*Keine offenen Einträge.*', '']
    lines += ['Antwort je Eintrag: `<id> ja` · `<id> nein` · `<id> geändert: <eigene Fassung>`']
    return '\n'.join(lines) + '\n'


# ---------- Abarbeitung in Stufen (#570) ----------

def _is_open(e):
    return e.get('entscheidung', 'offen') == 'offen' and not e.get('umgesetzt')


def _severity(e):
    return e.get('schweregrad') or 'mittel'


def group_key(e):
    """Gleiche Art und gleicher Befund (Zahlen und Anführungszeichen ignoriert, `muster` hat Vorrang) = ein Muster."""
    norm = re.sub(r'[\d"„“»«\'‚‘’]+', '', (e.get('muster') or e.get('grund') or '')).lower()
    norm = re.sub(r'\s+', ' ', norm).strip()
    return f"{e.get('art', '')}-{hashlib.sha1(norm.encode('utf-8')).hexdigest()[:6]}"


def stages(data, size=ROUND_SIZE):
    """Offene Einträge in vier Stufen (#570): blockierend (einzeln), Gruppen, Runden zu `size`, gering (zugeklappt)."""
    every = [e for _, e in entries(data)]
    counts = {}
    for e in every:
        if _severity(e) not in ('blockierend', 'gering') and not (e.get('thema') in {t['id'] for t in data.get('themen') or []}):
            counts[group_key(e)] = counts.get(group_key(e), 0) + 1
    grouped = {k for k, n in counts.items() if n >= GROUP_MIN}

    known = [t['id'] for t in data.get('themen') or []]

    def themed(e):   # #607: auch geringe Befunde gehören zu ihrem Thema; Blockierendes bleibt in Stufe 1
        return e.get('thema') in known and _severity(e) != 'blockierend'

    def middle(e):
        return _severity(e) not in ('blockierend', 'gering') and not themed(e)
    opened = [e for e in every if _is_open(e)]
    groups = {}
    for e in opened:
        if middle(e) and group_key(e) in grouped:
            groups.setdefault(group_key(e), []).append(e)
    singles = sorted((e for e in opened if middle(e) and group_key(e) not in grouped),
                     key=lambda e: RANK[_severity(e)])
    done = sum(1 for e in every if middle(e) and group_key(e) not in grouped and not _is_open(e))
    rounds = [singles[i:i + size] for i in range(0, len(singles), size)]
    titles = {t['id']: t['titel'] for t in data.get('themen') or []}
    theme_rounds = [(tid, titles[tid], [e for e in opened if themed(e) and e['thema'] == tid]) for tid in known]
    theme_total = sum(1 for tid in known if any(themed(e) and e['thema'] == tid for e in every))
    open_themes = [r for r in theme_rounds if r[2]]
    return {'blocking': [e for e in opened if _severity(e) == 'blockierend'], 'themes': open_themes,
            'theme_no': theme_total - len(open_themes) + 1, 'theme_total': theme_total, 'groups': groups, 'rounds': rounds,
            'gering': [e for e in opened if _severity(e) == 'gering' and not themed(e)], 'open': len(opened),
            'theme_blocking': {tid: [e['id'] for e in every if e.get('thema') == tid and _severity(e) == 'blockierend']
                               for tid in known},
            'round_no': done // size + 1, 'round_total': math.ceil((done + len(singles)) / size) if singles else 0}


def staged(data):
    """Ob `show` und das Widget die Stufen von selbst verwenden (viele offene Einträge)."""
    return sum(1 for _, e in entries(data) if _is_open(e)) >= STAGE_MIN


def current(data, size=ROUND_SIZE, gering=False, group=None):
    """Aktuelle Stufe: (name, Einträge, Kopfzeile). `group` öffnet eine Gruppe zum einzelnen Ansehen, `gering`
    klappt die geringen Einträge auf."""
    st = stages(data, size)
    left = f'noch {st["open"]} offen'
    if group:
        items = st['groups'].get(group.removeprefix(GROUP_PREFIX)) or []
        return 'gruppe', items, f'Gruppe einzeln ansehen · {len(items)} Einträge · {left}'
    if st['blocking']:
        return 'blockierend', st['blocking'], f'Stufe 1 · Blockierendes, einzeln · {len(st["blocking"])} offen · {left}'
    if st['themes']:   # #570: ein Thema je Runde, in der Reihenfolge der Abhängigkeit
        tid, title, items = st['themes'][0]
        minor = [e for e in items if _severity(e) == 'gering']
        hidden = minor if (minor and len(minor) < len(items) and not gering) else []   # #607: am Ende zugeklappt, außer das Thema besteht nur aus Geringem
        shown = [e for e in items if e not in hidden]
        more = f' (+ {len(hidden)} geringe zu diesem Thema)' if hidden else ''
        refs = st['theme_blocking'].get(tid) or []
        link = f' · Blockierendes dazu: {", ".join(refs)} (Stufe 1)' if refs else ''
        return 'thema', shown, (f'Stufe 2 · Thema {st["theme_no"]} von {st["theme_total"]}: {title} · {len(shown)} offen{more}'
                                f'{link} · {left}')
    if st['groups']:
        return 'gruppen', st['groups'], f'Stufe 2 · Gleiche Muster · {len(st["groups"])} Gruppen · {left}'
    if st['rounds']:
        return 'runde', st['rounds'][0], f'Stufe 3 · Runde {st["round_no"]} von {st["round_total"]} · {left}'
    if st['gering']:
        if gering:
            return 'gering', st['gering'], f'Stufe 4 · Geringes · {len(st["gering"])} offen'
        return 'gering-zu', [], f'Stufe 4 · {len(st["gering"])} geringe Hinweise zugeklappt'
    return 'fertig', [], 'Alle Einträge entschieden'


def _entry_lines(e):
    mark = '⛔ blockierend · ' if e.get('schweregrad') == 'blockierend' else ''
    lines = [f'`{e["id"]}` · {mark}{e["abschnitt"]} · {e["art"]} · **{e.get("entscheidung", "offen")}** – {e.get("grund", "")}']
    if e.get('frage'):
        lines += [f'> Frage: {e["frage"]}']
    if e.get('antwort'):
        lines += [f'> Antwort: {e["antwort"]}']   # #675: getrennt vom Ersatztext
    if e.get('alt'):
        lines += [f'> alt: {e["alt"]}']
    if has_change(e):
        lines += [f'> {"Vorschlag" if e.get("frage") else "neu"}: {e.get("neu") or "(entfällt)"}']
    if not_replacement(e):
        lines += [f'> ⚠️ {not_replacement(e)}: wird nicht automatisch umgesetzt']
    for k, v in enumerate(e.get('varianten') or [], start=1):
        lines += [f'> Variante {k}: {v}']
    return lines + ['']


# ---------- Einzeln vorlegen (#473) ----------

def ordered(data):
    """Alle Einträge in der Reihenfolge, in der sie einzeln vorgelegt werden: Blockierendes, Themen in ihrer Reihenfolge,
    übrige nach Schweregrad, Geringes zuletzt."""
    every = [e for _, e in entries(data)]
    pos = {t['id']: i for i, t in enumerate(data.get('themen') or [])}

    def key(e):
        sev = _severity(e)
        if sev == 'blockierend':
            return (0, 0, 0)
        if sev == 'gering' and e.get('thema') not in pos:
            return (3, 0, 0)
        if e.get('thema') in pos:
            return (1, pos[e['thema']], 1 if sev == 'gering' else 0)   # #607: Geringes am Ende seines Themas
        return (2, RANK[sev], 0)
    return sorted(every, key=key)   # stabil: sonst Reihenfolge der Datei


def card_head(data, e):
    """Stufe, Thema und Fortschritt im Thema für die Einzelkarte (#608), z. B.
    „Stufe 2 · Thema 1 von 22: Titel · 1 von 2 in diesem Thema“. Leer, wenn die Durchsicht weder Themen hat noch in Stufen läuft."""
    if not (data.get('themen') or staged(data)):
        return ''
    every = [x for _, x in entries(data)]
    sev = _severity(e)
    if sev == 'blockierend':
        return f'Stufe 1 · Blockierendes, einzeln · {sum(1 for x in every if _is_open(x) and _severity(x) == "blockierend")} offen'
    known = {t['id']: t['titel'] for t in data.get('themen') or []}
    if e.get('thema') in known:
        with_entries = [t for t in known if any(x.get('thema') == t and _severity(x) != 'blockierend' for x in every)]
        members = [x for x in ordered(data) if x.get('thema') == e['thema'] and _severity(x) != 'blockierend']
        pos = next((i for i, x in enumerate(members, start=1) if x.get('id') == e.get('id')), 1)
        return (f'Stufe 2 · Thema {with_entries.index(e["thema"]) + 1} von {len(with_entries)}: {known[e["thema"]]}'
                f' · {pos} von {len(members)} in diesem Thema')
    return 'Stufe 4 · Geringes' if sev == 'gering' else 'Stufe 3 · Übrige nach Schweregrad'


def unit_done(data, e):
    """Name der Einheit („Thema „X““, „Stufe 1“), die mit der Entscheidung zu `e` abgeschlossen wurde, sonst ''. (#609)"""
    every = [x for _, x in entries(data)]
    if _severity(e) == 'blockierend':
        return 'Stufe 1 (Blockierendes)' if not any(_is_open(x) and _severity(x) == 'blockierend' for x in every) else ''
    titles = {t['id']: t['titel'] for t in data.get('themen') or []}
    if e.get('thema') in titles and not any(_is_open(x) and x.get('thema') == e['thema'] and _severity(x) != 'blockierend'
                                            for x in every):
        return f'Thema „{titles[e["thema"]]}“'
    return ''


def single(data, entry_id=None):
    """(Eintrag oder None, Nummer, Gesamtzahl, offen): der genannte Eintrag bzw. der nächste offene."""
    seq = ordered(data)
    opened = sum(1 for e in seq if _is_open(e))
    if entry_id:
        for n, e in enumerate(seq, start=1):
            if e.get('id') == entry_id:
                return e, n, len(seq), opened
        raise ValueError(f'Eintrag {entry_id} nicht gefunden')
    for n, e in enumerate(seq, start=1):
        if _is_open(e):
            return e, n, len(seq), opened
    return None, len(seq), len(seq), 0


def show_single(data, entry_id=None):
    """Textfassung: eine Karte mit Fortschritt („8 von 21“), Zusammenhang und wählbaren Varianten (#473)."""
    e, n, total, opened = single(data, entry_id)
    lines = [f'### 🧹 Hinweisdurchsicht · {data.get("buch", "")}']
    if e is None:
        return '\n'.join(lines + ['Alle Einträge entschieden. Als Nächstes: Umsetzen prüfen (`hinweise.py plan`).', '']) + '\n'
    head = card_head(data, e)
    lines += [(head + ' · ' if head else '') + f'Eintrag {n} von {total} · noch {opened} offen', '']
    card = _entry_lines(e)
    if e.get('kontext'):
        card.insert(len(card) - 1 - len(e.get('varianten') or []), f'> Zusammenhang: {e["kontext"]}')
    lines += card
    if e.get('varianten'):
        lines += ['Antwort: ' + ' · '.join(f'`{e["id"]} variante {k}`' for k in range(1, len(e['varianten']) + 1))
                  + f' · `{e["id"]} nein` · `{e["id"]} geändert: <eigene Fassung>`']
    else:
        lines += [f'Antwort: `{e["id"]} ja` · `{e["id"]} nein` · `{e["id"]} geändert: <eigene Fassung>`']
    return '\n'.join(lines) + '\n'


def show_stufen(data, size=ROUND_SIZE, gering=False, group=None):
    """Textfassung der aktuellen Stufe (#570)."""
    name, items, head = current(data, size, gering, group)
    lines = [f'### 🧹 Hinweisdurchsicht · {data.get("buch", "")}', head, '']
    if name == 'gruppen':
        for key, es in items.items():
            first = es[0]
            lines += [f'**{GROUP_PREFIX}{key}** · {len(es)} × {first["art"]} – {first.get("grund", "")}']
            if first.get('alt'):
                lines += [f'> z. B. alt: {first["alt"]}']
            if first.get('neu'):
                lines += [f'> z. B. neu: {first["neu"]}']
            lines += ['']
        lines += ['Antwort je Gruppe: `<gruppe> ja` (alle wie vorgeschlagen) · `<gruppe> nein` (alle lassen) · '
                  '`<gruppe> einzeln` (die Einträge einzeln ansehen)']
        return '\n'.join(lines) + '\n'
    if name == 'thema':
        lines += ['Diese Einträge hängen zusammen und werden gemeinsam entschieden.', '']
        hidden = [e for e in current(data, size, True)[1] if e not in items]   # #607
        if hidden:
            lines += [f'+ {len(hidden)} geringe zu diesem Thema zugeklappt; aufklappen: `hinweise.py show . --gering`', '']
    for e in items:
        lines += _entry_lines(e)
    if name == 'gering-zu':
        lines += ['Auf Wunsch aufklappen (`gering`) oder gesammelt lassen (`gering lassen`).']
    elif name == 'fertig':
        lines += ['*Keine offenen Einträge.*']
    else:
        lines += ['Antwort je Eintrag: `<id> ja` · `<id> nein` · `<id> geändert: <eigene Fassung>`', '',
                  'Jederzeit aufhören; die nächste Durchsicht macht an dieser Stelle weiter.']
    return '\n'.join(lines) + '\n'


def decide_group(path, key, decision):
    """Eine Gruppe entscheiden (#570): `ja` nimmt Einträge mit Vorschlag an, `nein` lässt alle. Gibt (geändert, übersprungen)."""
    if decision not in ('ja', 'nein'):
        raise ValueError('Für eine Gruppe gilt nur ja (wie vorgeschlagen) oder nein (alle lassen)')
    key = key.removeprefix(GROUP_PREFIX)
    data = read_yaml(path)
    changed, skipped = [], []
    for _, e in entries(data):
        if not _is_open(e) or group_key(e) != key or _severity(e) in ('blockierend', 'gering'):
            continue
        if decision == 'ja' and not proposal(e):
            skipped.append(e)
            continue
        e['entscheidung'] = decision
        changed.append(e)
    if not changed and not skipped:
        raise ValueError(f'Gruppe {key} nicht gefunden oder schon entschieden')
    if changed:
        write_yaml(path, data)
    return changed, skipped


def decide_gering(path):
    """Alle offenen geringen Einträge lassen (#570): `nein`, ohne Änderung am Manuskript."""
    data = read_yaml(path)
    changed = [e for _, e in entries(data) if _is_open(e) and _severity(e) == 'gering']
    for e in changed:
        e['entscheidung'] = 'nein'
    if changed:
        write_yaml(path, data)
    return changed


# ---------- Umsetzen (Teil 2) ----------

def _section(base, config, sid):
    number, ch, s = section_index(config)[sid]
    from render_view import section_file
    head = section_file(Path(base), s)[0]
    return number, ch, s, head


def _checked_out(base, config, sid):
    """Aktiver Checkout zum Gegenlesen, der den Abschnitt sperrt (#572), sonst None."""
    import checkout
    return checkout.locked_by_checkout(base, config, sid)


def plan(base, config, data, chapters=None):
    """[(zeichen, eintrag, grund)] für alle entschiedenen, noch nicht umgesetzten Einträge."""
    import checks
    chapters = set(chapters or [])
    out = []
    for _, e in entries(data):
        if e.get('umgesetzt') or e.get('entscheidung') not in ('ja', 'geändert'):
            continue
        if chapters and e['chapter_id'] not in chapters:
            continue
        if e['section_id'] == BOOK:
            out.append(('⚠️', e, 'buchweit: von Hand in den betroffenen Abschnitten umsetzen'))
            continue
        if e['section_id'] not in section_index(config):
            out.append(('⛔', e, 'Abschnitt gibt es nicht mehr'))
            continue
        _, ch, _, head = _section(base, config, e['section_id'])
        ch = ch or {}
        text = checks.manuscript(base, config, e['section_id']) or ''
        if not e.get('alt') or not has_change(e):
            out.append(('⚠️', e, 'Antwort des Autors ohne neuen Wortlaut: von Hand umsetzen' if e.get('antwort')
                        else 'ohne alten Wortlaut oder Vorschlag: von Hand umsetzen'))
        elif ch.get('status') == 'approved':
            out.append(('⛔', e, f'Kapitel {e["abschnitt"].split(".")[0]} ist abgeschlossen: erst wieder öffnen'))
        elif head.get('status') == 'approved':
            out.append(('⛔', e, f'{"Abschnitt " if e.get("chapter_id") else ""}{e["abschnitt"]} ist abgeschlossen: '
                                 'erst wieder öffnen'))
        elif _checked_out(base, config, e['section_id']):
            out.append(('⛔', e, f'ausgecheckt: {_checked_out(base, config, e["section_id"])["id"]} (Checkout erst beenden)'))
        elif wording(text, e['alt'], e.get('neu') or '') is None:
            out.append(_not_found(base, config, e, text))
        elif not_replacement(e):   # #675: Antwort oder Anweisung nie wörtlich ins Manuskript
            out.append(('⚠️', e, f'{not_replacement(e)}: von Hand umsetzen oder den neuen Wortlaut eintragen '
                                 '(decide --new …; ist es wirklich die Fassung: --as-text)'))
        else:
            out.append(('✅', e, 'streichen' if e.get('streichen') else 'umsetzbar'))
    return out


def _not_found(base, config, e, text):
    """Grund, warum der Wortlaut im genannten Abschnitt nicht eindeutig steht (#522): mehrfach, woanders oder gar nicht.
    Das Skript prüft nicht, ob sich der Text geändert hat, und behauptet es deshalb nicht."""
    import checks
    hits = text.count(e['alt'])
    if hits > 1:
        return ('⛔', e, f'alter Wortlaut kommt {hits}-mal in {e["abschnitt"]} vor: die Stelle von Hand wählen')
    places = []
    for sid, (number, _, entry) in section_index(config).items():
        if sid in (BOOK, e['section_id']) or entry is None:
            continue
        try:
            other = checks.manuscript(base, config, sid) or ''
        except Exception:   # noqa: BLE001 – ein nicht lesbarer Abschnitt ist hier kein Treffer
            continue
        if wording(other, e['alt'], e.get('neu') or '') is not None:
            places.append(number)
    if len(places) == 1:
        return ('⚠️', e, f'Wortlaut steht in {places[0]} statt {e["abschnitt"]}: Abschnitt im Befund prüfen, von Hand umsetzen')
    if places:
        return ('⚠️', e, f'Wortlaut steht in mehreren anderen Abschnitten ({", ".join(places)}): von Hand umsetzen')
    return ('⛔', e, 'Wortlaut nicht gefunden: Text oder Befund prüfen')


def plan_text(items, data=None):
    head = [f'⛔ Durchsicht gesperrt: {locked(data)} – `apply` setzt nichts um (entsperren: hinweise.py unlock)', ''] \
        if data and locked(data) else []
    if not items:
        return '\n'.join(head + ['Keine entschiedenen Einträge zum Umsetzen.']) + '\n'
    lines = head + [f'{mark} `{e["id"]}` · {e["abschnitt"]} · {why}' for mark, e, why in items]
    blocked = sorted({e['abschnitt'] for mark, e, _ in items if mark == '⛔' and 'abgeschlossen' in _})
    if blocked:
        lines += ['', 'Wieder öffnen braucht eine eigene Bestätigung (START.md, „Freigaben“): ' + ', '.join(blocked)]
    return '\n'.join(lines) + '\n'


def _replace_in_manuscript(path, alt, neu, delete=False):
    text = Path(path).read_text(encoding='utf-8')
    marker = '\n## Manuskript\n'
    head, sep, body = text.partition(marker)
    found = wording(body, alt, neu) if sep else None
    if found is None:
        raise ValueError(f'{path}: alter Wortlaut nicht genau einmal im Manuskript')
    new_body = tidy_deletion(body, found[0]) if delete else body.replace(found[0], found[1], 1)
    Path(path).write_text(head + sep + new_body, encoding='utf-8')
    return found[1]


def _write_back(base, data):
    """Befundstatus in die Befunddateien (Punkt 6): umgesetzt -> erledigt, nein -> entschieden."""
    targets = {}
    for _, e in entries(data):
        state = 'erledigt' if e.get('umgesetzt') else 'entschieden' if e.get('entscheidung') == 'nein' else None
        if state and e.get('befund'):   # Dialog ohne Befundverweis (z. B. aus Markdown-Lektorat, #386): nichts zurückschreiben
            f, _, fid = e['befund'].partition('#')
            targets.setdefault(f, {})[fid] = state
    changed = []
    for f, ids in targets.items():
        path = Path(base) / f
        if not path.is_file():
            continue
        fd = read_yaml(path)
        hit = False
        for b in fd.get('befunde') or []:
            if b.get('id') in ids and b.get('status') == 'offen':
                b['status'] = ids[b['id']]
                hit = True
        if hit:
            write_yaml(path, fd)
            changed.append(f)
    return changed


def apply(base, config, path, chapters=None):
    """✅-Einträge umsetzen. Rückgabe: {'applied', 'skipped', 'reports', 'chapters', 'context'}."""
    import checks
    base = Path(base)
    data = read_yaml(path)
    if locked(data):
        raise ValueError(f'Durchsicht gesperrt: {locked(data)}. Nichts umgesetzt (entsperren: hinweise.py unlock).')
    items = plan(base, config, data, chapters)
    applied, skipped, touched, ctx = [], [], [], []
    for mark, e, why in items:
        if mark == '✅' and not_replacement(e):   # #675: zweite Sicherung direkt vor dem Ersetzen
            mark, why = '⚠️', f'{not_replacement(e)}: von Hand umsetzen'
        if mark != '✅':
            skipped.append((mark, e, why))
            continue
        used = _replace_in_manuscript(base / e['datei'], e['alt'], e.get('neu') or '', bool(e.get('streichen')))
        e['umgesetzt'] = True
        applied.append(e)
        scope = e['chapter_id'] or e['section_id']   # Teil von Vor-/Nachspann: eigener Prüfbereich
        if scope not in touched:
            touched.append(scope)
        text = checks.manuscript(base, config, e['section_id']) or ''
        ctx.append((e, context(text, used) if used and text.count(used) == 1 else (e.get('neu') or '(entfällt)')))
    write_yaml(path, data)
    reports = _write_back(base, data)
    return {'applied': applied, 'skipped': skipped, 'reports': reports, 'chapters': touched, 'context': ctx}


def apply_text(result):
    lines = [f'{len(result["applied"])} Einträge umgesetzt, {len(result["skipped"])} nicht umgesetzt.', '']
    if result['context']:
        lines += ['**Im Zusammenhang neu lesen:**', '']
        lines += [f'`{e["id"]}` · {e["abschnitt"]}: {c}' for e, c in result['context']] + ['']
    if result['skipped']:
        lines += ['**Nicht umgesetzt:**', ''] + [f'{m} `{e["id"]}` · {e["abschnitt"]} · {w}' for m, e, w in result['skipped']] + ['']
    if result['reports']:
        lines += ['Befundstatus zurückgeschrieben: ' + ', '.join(result['reports']), '']
    if result['chapters']:
        scope = ' '.join(f'--scope {c}' for c in result['chapters'])
        lines += ['**Nachprüfung** nach dem Neulesen eintragen (nicht automatisch):',
                  f'`python3 scripts/checks.py record <buch> --kind proofreading {scope} --result … --notes <n>`',
                  f'`python3 scripts/checks.py record <buch> --kind quality_correction {scope} --result … --notes <n>`',
                  'Danach eigens fragen, ob die Kapitel neu abgeschlossen werden sollen; Abschließen bleibt eine eigene Entscheidung.']
    return '\n'.join(lines) + '\n'


# ---------- Widget (ghostwriter-ui, Vorlage hinweisdurchsicht) ----------

STATUS_TEXT = {'planned': 'geplant', 'in_progress': 'in Arbeit', 'ready_for_assembly': 'bereit zum Zusammenführen',
               'assembly': 'im Zusammenführen', 'review': 'in Prüfung', 'ready_for_approval': 'bereit zum Abschluss',
               'approved': 'abgeschlossen'}


def widget_values(base, path, stufen=None, size=ROUND_SIZE, gering=False, group=None, entry=None):
    """Werte für die Vorlage hinweisdurchsicht (#367): (values, blocks). Mit `stufen` (Voreinstellung: ab STAGE_MIN
    offenen Einträgen) zeigt das Widget nur die aktuelle Stufe (#570); Gruppen erscheinen als eine Zeile mit der
    ID `gruppe:<schlüssel>`, deren Antwort `ja` bzw. `nein` die ganze Gruppe entscheidet."""
    data = read_yaml(path)
    all_entries = entries(data)
    if stufen is None:
        stufen = staged(data) or bool(group)
    done = sum(e.get('entscheidung', 'offen') != 'offen' for _, e in all_entries)
    y, m, d = (str(data.get('erstellt', '')).split('-') + ['', '', ''])[:3]

    def row(e, author):
        r = {'E_ID': e['id'], 'E_WHERE': e['abschnitt'],
             'E_CHAPTER_TEXT': where(e) + (' · ' + STATUS_TEXT.get(e['chapter_status'], e['chapter_status'])
                                           if e.get('chapter_status') else ''),
             'E_KIND': e.get('art', ''),
             'E_REASON': ('⛔ blockierend: ' if e.get('schweregrad') == 'blockierend' else '') + e.get('grund', ''),
             'E_CONTEXT': e.get('kontext', ''),
             'E_OLD': e.get('alt', ''), 'E_NEW': e.get('neu') or ('(entfällt)' if e.get('streichen') else ''),
             'E_DECISION': 'umgesetzt' if e.get('umgesetzt') else e.get('entscheidung', 'offen')}
        if author:
            r['E_PROPOSED'] = '1' if e.get('vorschlag_von') == 'assistent' else ''   # #609
            r['E_VARIANTS_JSON'] = json.dumps([str(v) for v in e.get('varianten') or []], ensure_ascii=False) if e.get('varianten') else ''   # #630: Knopf je Variante (UI ab 0.70.0)
            r['E_QUESTION'] = e.get('frage', '') + ''.join(f' · Variante {k}: {v}' for k, v in
                                                          enumerate(e.get('varianten') or [], start=1)) \
                + (f' · Antwort: {e["antwort"]}' if e.get('antwort') else '') \
                + (f' · ⚠️ {not_replacement(e)}: wird nicht automatisch umgesetzt' if not_replacement(e) else '')   # #447, #675
        return r
    rel = Path(path).resolve().relative_to(Path(base).resolve()).as_posix()
    values = {'REVIEW_FILE': rel, 'REVIEW_BOOK': data.get('buch', ''),
              'REVIEW_DATE_TEXT': f'Stand {d}.{m}.{y}' if d else '',
              'REVIEW_COUNT_TEXT': f'{len(all_entries)} Einträge · {done} entschieden · {len(all_entries) - done} offen'}
    lock_text = f'⛔ Gesperrt: {locked(data)} · ' if locked(data) else ''   # #675
    blocks = {}
    shown = None
    name = ''
    if entry:   # #473: genau eine Karte; entry = Eintrags-ID oder „next“
        e, n, total, opened = single(data, None if entry == 'next' else entry)
        head = card_head(data, e) if e else ''
        values['REVIEW_COUNT_TEXT'] = (((head + ' · ') if head else '') + f'Eintrag {n} von {total} · noch {opened} offen' if e else
                                       'Alle Einträge entschieden · als Nächstes: Umsetzen prüfen')
        shown = {e['id']} if e else set()
        stufen = False
    if stufen:
        name, items, head = current(data, size, gering, group)
        values['REVIEW_COUNT_TEXT'] = head
        if name == 'gruppen':
            items = [dict(es[0], id=GROUP_PREFIX + key, abschnitt=f'{len(es)} Stellen', chapter_id='', chapter_status='',
                          frage=f'Alle {len(es)} Stellen: wie vorgeschlagen (ja) · alle lassen (nein) · '
                                'einzeln ansehen (sag „' + GROUP_PREFIX + key + ' einzeln“)',
                          varianten=[], schweregrad='') for key, es in items.items()]
        shown = {e['id'] for e in items}
    auto = [row(e, False) for e in data.get('ohne_autor') or [] if shown is None or e['id'] in shown]
    author = [row(e, True) for e in data.get('autorenentscheidung') or [] if shown is None or e['id'] in shown]
    if shown and name == 'gruppen':
        author = [row(e, True) for e in items]
    values['REVIEW_COUNT_TEXT'] = lock_text + values['REVIEW_COUNT_TEXT']
    skipped = [{'SK_REF': s['befund'], 'SK_REASON': s['grund']} for s in data.get('ausgelassen') or []]
    if auto:
        blocks['AUTO'] = auto
    if author:
        blocks['AUTHOR'] = author
    if skipped:
        blocks['SKIPPED'] = skipped
    return values, blocks


# ---------- Prüfung (validate_project.py) ----------

def errors(base, config):
    """Befunddateien und Dialogdateien: Schema, eindeutige IDs, bekannte Abschnitte."""
    import json
    from jsonschema import Draft202012Validator
    schemas = Path(__file__).resolve().parents[1] / 'schemas'
    fv = Draft202012Validator(json.loads((schemas / 'findings.schema.json').read_text(encoding='utf-8')))
    dv = Draft202012Validator(json.loads((schemas / 'notes-review.schema.json').read_text(encoding='utf-8')))
    index = section_index(config)
    out = []
    for path, v, kind in [(p, fv, 'f') for p in findings_files(base)] + [(p, dv, 'd') for p in dialog_files(base)]:
        try:
            data = read_yaml(path)
        except Exception as exc:   # noqa: BLE001
            out.append(f'{path}: {exc}')
            continue
        if kind == 'f' and 'befunde' not in data:
            continue   # andere YAML-Dateien unter editorial/ sind keine Befunde
        errs = [f'{path}: {"/".join(map(str, e.absolute_path)) or "(Wurzel)"}: {e.message}' for e in v.iter_errors(data)]
        if errs:
            out += errs
            continue
        items = data['befunde'] if kind == 'f' else [e for _, e in entries(data)]
        ids = [e['id'] for e in items]
        out += [f'{path}: ID doppelt: {i}' for i in sorted({i for i in ids if ids.count(i) > 1})]
        key = 'abschnitt' if kind == 'f' else 'section_id'
        out += [f'{path}: {e["id"]}: Abschnitt {e[key]} unbekannt' for e in items if e[key] not in index]
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest='cmd', required=True)
    c = sub.add_parser('collect', help='offene Befunde sammeln und Dialogdatei schreiben')
    c.add_argument('project')
    c.add_argument('--chapter', action='append', help='nur dieses Kapitel (mehrfach möglich)')
    c.add_argument('--date')
    how = c.add_mutually_exclusive_group()
    how.add_argument('--merge', action='store_true', help='an die Durchsicht des Tages anhängen (#438)')
    how.add_argument('--new', action='store_true', help='weitere Durchsicht für denselben Tag anlegen (#438)')
    s = sub.add_parser('show', help='Dialog als Text zeigen')
    s.add_argument('project')
    s.add_argument('--file')
    s.add_argument('--open', action='store_true', help='nur offene Einträge')
    s.add_argument('--stufen', action='store_true', help='Stufen erzwingen (#570)')
    s.add_argument('--alle', action='store_true', help='ganze Liste, keine Stufen')
    s.add_argument('--size', type=int, default=ROUND_SIZE, help='Einträge je Runde')
    s.add_argument('--gering', action='store_true', help='geringe Einträge aufklappen')
    s.add_argument('--group', help='Gruppe einzeln ansehen')
    s.add_argument('--entry', help='nur diesen Eintrag als Karte zeigen (#473)')
    s.add_argument('--next', action='store_true', help='nächsten offenen Eintrag als Karte zeigen (#473)')
    pr = sub.add_parser('propose', help='Vorschlag des Assistenten an einen Eintrag schreiben (#609)')
    pr.add_argument('project')
    pr.add_argument('entry')
    pr.add_argument('--new', default='')
    pr.add_argument('--delete', action='store_true', help='Streichung des alten Wortlauts als Vorschlag (#615)')
    pr.add_argument('--variant', action='append', default=[], help='Variante (bis zu drei, mehrfach angeben)')
    pr.add_argument('--file')
    pr.add_argument('--next-card', action='store_true', help='danach dieselbe Karte ausgeben')
    pr.add_argument('--repo')
    pr.add_argument('--text', action='store_true')
    ak = sub.add_parser('ask', help='Rückfrage zu einem Eintrag: entscheidet nichts, zeigt dieselbe Karte erneut (#609)')
    ak.add_argument('project')
    ak.add_argument('entry')
    ak.add_argument('--question')
    ak.add_argument('--file')
    ak.add_argument('--repo')
    ak.add_argument('--text', action='store_true')
    cp = sub.add_parser('checkpoint', help='Zwischenstand der Durchsicht als einen Commit speichern (#609)')
    cp.add_argument('project')
    cp.add_argument('--message')
    cp.add_argument('--push-to', help='Arbeits-Branch, auf den der Commit hochgeladen wird')
    d = sub.add_parser('decide', help='Entscheidung zu einem Eintrag speichern')
    d.add_argument('project')
    d.add_argument('entry', nargs='?')
    d.add_argument('--group', help='ganze Gruppe entscheiden (#570)')
    d.add_argument('--gering', action='store_true', help='alle geringen offenen Einträge lassen (#570)')
    d.add_argument('--decision', choices=DECISIONS[1:] + ('streichen',), help='streichen: alten Wortlaut entfernen (#615)')
    d.add_argument('--new')
    d.add_argument('--answer', help='Antwort auf die Frage des Eintrags, getrennt vom Ersatztext (#675)')
    d.add_argument('--variant', type=int, help='Variante N wählen (#473)')
    d.add_argument('--as-text', action='store_true', help='„geändert“ mit einem Fragetext trotzdem als Fassung speichern (#609)')
    d.add_argument('--next-card', action='store_true', help='danach die nächste Karte ausgeben (#609)')
    d.add_argument('--repo', help='owner/repo für die Karte (mit --next-card)')
    d.add_argument('--text', action='store_true', help='mit --next-card: Textfassung statt Widget')
    d.add_argument('--file')
    lk = sub.add_parser('lock', help='Dialogdatei sperren: kein apply/accept, decide bleibt erlaubt (#675)')
    lk.add_argument('project')
    lk.add_argument('--reason', required=True)
    lk.add_argument('--file')
    uk = sub.add_parser('unlock', help='Sperre der Dialogdatei aufheben (#675)')
    uk.add_argument('project')
    uk.add_argument('--file')
    for name, text in (('accept', 'Vorschläge annehmen (Rundumprüfung, #565)'), ('plan', 'vor dem Umsetzen zeigen, was geht'),
                       ('apply', 'entschiedene Einträge umsetzen')):
        x = sub.add_parser(name, help=text)
        x.add_argument('project')
        x.add_argument('--chapter', action='append')
        x.add_argument('--file')
    argv = list(sys.argv[1:] if argv is None else argv)
    if len(argv) > 1 and argv[1] in sub.choices and argv[0] not in sub.choices:
        argv[0], argv[1] = argv[1], argv[0]   # auch „hinweise.py <buch> <befehl>“ wie die übrigen Skripte (#383)
    args = ap.parse_args(argv)
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from render_view import load
    base, config = load(args.project)
    base = Path(base)
    try:
        if args.cmd == 'collect':
            path, data = collect(base, config, args.chapter, args.date,
                                 mode='merge' if args.merge else 'new' if args.new else None)
            print(f'{path.relative_to(base).as_posix()}: {len(data["ohne_autor"])} ohne Autor lösbar, '
                  f'{len(data["autorenentscheidung"])} Autorenentscheidungen, {len(data.get("ausgelassen") or [])} nicht aufgenommen')
            for e, why in suspicious(data):   # #675: auffällige `neu` in vorhandenen Einträgen melden
                print(f'⚠️ {e["id"]} ({e["abschnitt"]}): {why} – wird nicht automatisch umgesetzt; Antwort nach `antwort`, '
                      'Ersatztext nach `neu` (hinweise.py decide … --answer/--new)')
            return 0
        if args.cmd == 'checkpoint':
            done, sha = checkpoint(base, args.message, args.push_to)
            print(f'Zwischenstand gespeichert ({done} entschieden), Commit {sha[:7]}' if sha else 'Nichts zu speichern.')
            return 0
        path = Path(args.file) if args.file else latest(base)
        if path and not path.is_absolute() and not path.exists():
            path = base / path
        if not path or not path.is_file():
            print('Keine Durchsichtsdatei gefunden (zuerst collect).', file=sys.stderr)
            return 1
        if args.cmd == 'show':
            data = read_yaml(path)
            if args.entry or args.next:
                print(show_single(data, args.entry), end='')
            elif args.stufen or args.group or (staged(data) and not args.alle and not args.open):
                print(show_stufen(data, args.size, args.gering, args.group), end='')
            else:
                print(show(data, args.open), end='')
            return 0
        if args.cmd in ('propose', 'ask'):
            if args.cmd == 'propose':
                e = propose(path, args.entry, args.new, args.variant, args.delete)
                print(f'{e["id"]}: Vorschlag gespeichert', file=sys.stderr if not args.text else sys.stdout)
            else:
                find = [e for _, e in entries(read_yaml(path)) if e.get('id') == args.entry]
                if not find:
                    raise ValueError(f'Eintrag {args.entry} nicht gefunden')
                print(f'{args.entry}: Rückfrage notiert, nichts entschieden; beantworten, dann die Karte erneut zeigen.',
                      file=sys.stderr if not args.text else sys.stdout)
            if args.cmd == 'ask' or args.next_card:
                cmd = [sys.executable, str(Path(__file__).resolve().parent / 'render_view.py'), str(base), 'notes-review', str(path),
                       '--entry', args.entry] + (['--text'] if args.text else []) + (['--repo', args.repo] if args.repo else [])
                card = subprocess.run(cmd, capture_output=True, text=True)
                sys.stdout.write(card.stdout)
                if card.returncode:
                    print(card.stderr, file=sys.stderr)
                    return 1
            return 0
        if args.cmd in ('lock', 'unlock'):
            lock(path, args.reason if args.cmd == 'lock' else None)
            print(f'{path.relative_to(base).as_posix() if path.is_relative_to(base) else path}: '
                  + (f'gesperrt ({args.reason.strip()})' if args.cmd == 'lock' else 'entsperrt'))
            return 0
        if args.cmd == 'plan':
            data = read_yaml(path)
            print(plan_text(plan(base, config, data, args.chapter), data), end='')
            return 0
        if args.cmd == 'accept':
            import checkout
            skip = {s for s in section_index(config) if checkout.locked_by_checkout(base, config, s)}
            taken = accept(path, args.chapter, skip)
            print(f'{len(taken)} Vorschläge angenommen' + ''.join(f'\n- {e["id"]} ({e["abschnitt"]}): {e["alt"]} → {e["neu"]}'
                                                               for e in taken))
            return 0
        if args.cmd == 'apply':
            print(apply_text(apply(base, config, path, args.chapter)), end='')
            return 0
        if args.gering:
            changed = decide_gering(path)
            print(f'{len(changed)} geringe Einträge gelassen')
            return 0
        group = args.group or (args.entry if (args.entry or '').startswith(GROUP_PREFIX) else None)
        if group:
            if not args.decision:
                raise ValueError('--decision ja|nein fehlt')
            changed, skipped = decide_group(path, group, args.decision)
            print(f'{len(changed)} Einträge: {args.decision}' + (f'; {len(skipped)} ohne Vorschlag bleiben offen' if skipped else ''))
            return 0
        if args.answer and not args.decision and args.variant is None:
            args.decision = 'geändert'   # #675: nur die Antwort auf die Frage, ohne neuen Wortlaut
        if not args.entry or not (args.decision or args.variant):
            raise ValueError('Eintrag und --decision (oder --variant) angeben (oder --group / --gering)')
        e = decide(path, args.entry, args.decision, args.new, args.variant, args.as_text, args.answer)
        print(f'{e["id"]}: {e["entscheidung"]}', file=sys.stderr if args.next_card and not args.text else sys.stdout)
        if args.next_card:
            done = unit_done(read_yaml(path), e)
            if done:   # #609: Zwischenstand je abgeschlossenem Thema bzw. Stufe (Schreibregel in START.md)
                print(f'✓ {done} abgeschlossen: Zwischenstand jetzt speichern (ein Commit, siehe „Speichern der Durchsicht“).',
                      file=sys.stderr)
            cmd = [sys.executable, str(Path(__file__).resolve().parent / 'render_view.py'), str(base), 'notes-review', str(path),
                   '--next'] + (['--text'] if args.text else []) + (['--repo', args.repo] if args.repo else [])
            card = subprocess.run(cmd, capture_output=True, text=True)
            sys.stdout.write(card.stdout)
            if card.returncode:
                print(card.stderr, file=sys.stderr)
                return 1
        return 0
    except ValueError as exc:
        print(exc, file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
