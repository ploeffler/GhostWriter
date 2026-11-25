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
  python3 scripts/hinweise.py decide <buch> <eintrag> --decision ja|nein|geändert [--new TEXT] [--file …]
      schreibt nur `entscheidung` (und bei „geändert“ `neu`) in die Dialogdatei
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
      vor dem Umsetzen (Teil 2): je Eintrag ✅ umsetzbar, ⚠️ von Hand, ⛔ abgeschlossen (erst wieder öffnen)
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
import math
import re
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


def write_yaml(path, data):
    Path(path).write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False, width=100), encoding='utf-8')


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


def latest(base):
    files = dialog_files(base)
    return files[-1] if files else None


def entries(data):
    return [('ohne_autor', e) for e in data.get('ohne_autor') or []] + \
           [('autorenentscheidung', e) for e in data.get('autorenentscheidung') or []]


def decide(path, entry_id, decision, new=None, variant=None):
    if variant is not None:   # #473: Variante N wählen = „geändert“ mit dem Wortlaut der Variante
        decision = 'geändert'
    if decision not in DECISIONS:
        raise ValueError(f'Unbekannte Entscheidung: {decision}')
    if decision == 'geändert' and not new and variant is None:
        raise ValueError('Bei „geändert“ gehört die eigene Fassung dazu (--new)')
    data = read_yaml(path)
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
            e['entscheidung'] = decision
            if new is not None:
                e['neu'] = new
            write_yaml(path, data)
            return e
    raise ValueError(f'Eintrag {entry_id} nicht gefunden')


def proposal(e):
    """Eintrag mit eindeutigem Vorschlag, den die Rundumprüfung ohne Rückfrage annehmen darf (#565): `alt` und `neu`
    vorhanden und verschieden, nicht blockierend, nicht buchweit, keine Auswahl unter mehreren Varianten."""
    return bool(e.get('alt') and e.get('neu') and e['neu'] != e['alt'] and e.get('section_id') != BOOK
                and e.get('schweregrad') != 'blockierend' and not e.get('varianten'))


def accept(path, chapters=None, skip=()):
    """Rundumprüfung (#565): offene, nicht umgesetzte Einträge mit Vorschlag auf `ja` setzen und mit
    `angenommen: rundumpruefung` kennzeichnen. Abgeschlossenes hält danach `plan` zurück (⛔)."""
    chapters = set(chapters or [])
    data = read_yaml(path)
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
    if auto:
        lines += ['#### Ohne Autor lösbar', '']
        chapter = None
        for e in auto:
            if (e['chapter_id'] or e['abschnitt']) != chapter:
                chapter = e['chapter_id'] or e['abschnitt']
                lines += [f'**{where(e)}**' + (f' ({e["chapter_status"]})' if e.get('chapter_status') else ''), '']
            lines += [f'`{e["id"]}` · {e["abschnitt"]} · {e["art"]} · **{e.get("entscheidung", "offen")}** – {e.get("grund", "")}',
                      f'> alt: {e["alt"]}', f'> neu: {e["neu"]}', '']
    if author:
        lines += ['#### Autorenentscheidung', '']
        for e in author:
            mark = '⛔ blockierend · ' if e.get('schweregrad') == 'blockierend' else ''
            lines += [f'`{e["id"]}` · {mark}{e["abschnitt"]} · {e["art"]} · **{e.get("entscheidung", "offen")}** – {e.get("grund", "")}',
                      f'> Frage: {e.get("frage", "")}']
            if e.get('alt'):
                lines += [f'> alt: {e["alt"]}']
            if e.get('neu'):
                lines += [f'> Vorschlag: {e["neu"]}']
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
    if e.get('alt'):
        lines += [f'> alt: {e["alt"]}']
    if e.get('neu'):
        lines += [f'> {"Vorschlag" if e.get("frage") else "neu"}: {e["neu"]}']
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
    lines += [f'Eintrag {n} von {total} · noch {opened} offen', '']
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
        if not e.get('alt') or not e.get('neu'):
            out.append(('⚠️', e, 'ohne alten Wortlaut oder Vorschlag: von Hand umsetzen'))
        elif ch.get('status') == 'approved':
            out.append(('⛔', e, f'Kapitel {e["abschnitt"].split(".")[0]} ist abgeschlossen: erst wieder öffnen'))
        elif head.get('status') == 'approved':
            out.append(('⛔', e, f'{"Abschnitt " if e.get("chapter_id") else ""}{e["abschnitt"]} ist abgeschlossen: '
                                 'erst wieder öffnen'))
        elif _checked_out(base, config, e['section_id']):
            out.append(('⛔', e, f'ausgecheckt: {_checked_out(base, config, e["section_id"])["id"]} (Checkout erst beenden)'))
        elif wording(text, e['alt'], e['neu']) is None:
            out.append(_not_found(base, config, e, text))
        else:
            out.append(('✅', e, 'umsetzbar'))
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
        if wording(other, e['alt'], e['neu']) is not None:
            places.append(number)
    if len(places) == 1:
        return ('⚠️', e, f'Wortlaut steht in {places[0]} statt {e["abschnitt"]}: Abschnitt im Befund prüfen, von Hand umsetzen')
    if places:
        return ('⚠️', e, f'Wortlaut steht in mehreren anderen Abschnitten ({", ".join(places)}): von Hand umsetzen')
    return ('⛔', e, 'Wortlaut nicht gefunden: Text oder Befund prüfen')


def plan_text(items):
    if not items:
        return 'Keine entschiedenen Einträge zum Umsetzen.\n'
    lines = [f'{mark} `{e["id"]}` · {e["abschnitt"]} · {why}' for mark, e, why in items]
    blocked = sorted({e['abschnitt'] for mark, e, _ in items if mark == '⛔' and 'abgeschlossen' in _})
    if blocked:
        lines += ['', 'Wieder öffnen braucht eine eigene Bestätigung (START.md, „Freigaben“): ' + ', '.join(blocked)]
    return '\n'.join(lines) + '\n'


def _replace_in_manuscript(path, alt, neu):
    text = Path(path).read_text(encoding='utf-8')
    marker = '\n## Manuskript\n'
    head, sep, body = text.partition(marker)
    found = wording(body, alt, neu) if sep else None
    if found is None:
        raise ValueError(f'{path}: alter Wortlaut nicht genau einmal im Manuskript')
    Path(path).write_text(head + sep + body.replace(found[0], found[1], 1), encoding='utf-8')
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
    items = plan(base, config, data, chapters)
    applied, skipped, touched, ctx = [], [], [], []
    for mark, e, why in items:
        if mark != '✅':
            skipped.append((mark, e, why))
            continue
        used = _replace_in_manuscript(base / e['datei'], e['alt'], e['neu'])
        e['umgesetzt'] = True
        applied.append(e)
        scope = e['chapter_id'] or e['section_id']   # Teil von Vor-/Nachspann: eigener Prüfbereich
        if scope not in touched:
            touched.append(scope)
        text = checks.manuscript(base, config, e['section_id']) or ''
        ctx.append((e, context(text, used) if used and text.count(used) == 1 else e['neu']))
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
             'E_OLD': e.get('alt', ''), 'E_NEW': e.get('neu', ''),
             'E_DECISION': 'umgesetzt' if e.get('umgesetzt') else e.get('entscheidung', 'offen')}
        if author:
            r['E_QUESTION'] = e.get('frage', '') + ''.join(f' · Variante {k}: {v}' for k, v in
                                                          enumerate(e.get('varianten') or [], start=1))   # #447
        return r
    rel = Path(path).resolve().relative_to(Path(base).resolve()).as_posix()
    values = {'REVIEW_FILE': rel, 'REVIEW_BOOK': data.get('buch', ''),
              'REVIEW_DATE_TEXT': f'Stand {d}.{m}.{y}' if d else '',
              'REVIEW_COUNT_TEXT': f'{len(all_entries)} Einträge · {done} entschieden · {len(all_entries) - done} offen'}
    blocks = {}
    shown = None
    name = ''
    if entry:   # #473: genau eine Karte; entry = Eintrags-ID oder „next“
        e, n, total, opened = single(data, None if entry == 'next' else entry)
        values['REVIEW_COUNT_TEXT'] = (f'Eintrag {n} von {total} · noch {opened} offen' if e else
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
    d = sub.add_parser('decide', help='Entscheidung zu einem Eintrag speichern')
    d.add_argument('project')
    d.add_argument('entry', nargs='?')
    d.add_argument('--group', help='ganze Gruppe entscheiden (#570)')
    d.add_argument('--gering', action='store_true', help='alle geringen offenen Einträge lassen (#570)')
    d.add_argument('--decision', choices=DECISIONS[1:])
    d.add_argument('--new')
    d.add_argument('--variant', type=int, help='Variante N wählen (#473)')
    d.add_argument('--file')
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
        if args.cmd == 'plan':
            print(plan_text(plan(base, config, read_yaml(path), args.chapter)), end='')
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
        if not args.entry or not (args.decision or args.variant):
            raise ValueError('Eintrag und --decision (oder --variant) angeben (oder --group / --gering)')
        e = decide(path, args.entry, args.decision, args.new, args.variant)
        print(f'{e["id"]}: {e["entscheidung"]}')
        return 0
    except ValueError as exc:
        print(exc, file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
