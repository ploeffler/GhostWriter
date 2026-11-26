#!/usr/bin/env python3
"""Prüfprotokoll eines Buchs (#331): welche Prüfung lief wann auf welcher Fassung mit welchem Ergebnis.

Datei: editorial/checks.yml im Buch (Schema schemas/checks.schema.json). Jeder Eintrag nennt Prüfart
(`kind`), Umfang (`scope`: `book`, Kapitel- oder Abschnitts-IDs), Datum, Ergebnis, optional den Bericht
und die geprüfte Fassung: `commit` und je Abschnitt einen Fingerabdruck des Manuskripts (`digests`).

Ein Eintrag sagt nur „Prüfung gelaufen mit Ergebnis X“. Er ist keine Freigabe und ändert keinen Status.

Veraltet: Weicht der heutige Fingerabdruck eines geprüften Abschnitts vom gespeicherten ab, gilt die
Prüfung für diesen Abschnitt als „seit Prüfung geändert“. Ohne gespeicherten Fingerabdruck (nachgetragene
Einträge) ist der Stand „unbekannt“.

Aufrufe:
  python3 scripts/checks.py record <buch> --kind language --scope kap-01 --result passed_with_notes \\
      [--report editorial/lektorat-2026-11-17.md] [--date 2026-11-17] [--commit <sha>] [--note …]
  python3 scripts/checks.py list <buch> [--json]
  python3 scripts/checks.py backfill <buch>     # abgeschlossene Analyseläufe einmalig nachtragen
  python3 scripts/checks.py import <buch> [--apply] [--json]   # ältere Berichte ohne Eintrag (#340)
  python3 scripts/checks.py record <buch> … --date JJJJ-MM-TT [--backfill]   # von Hand nachtragen (#344)
  python3 scripts/checks.py set <buch> <pr-NNN> --time HH:MM   # fehlende Angaben ergänzen (#345)
"""
import argparse
import datetime
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'scripts'))

FILE = Path('editorial') / 'checks.yml'
EDITORIAL = ('structure', 'language', 'proofreading', 'story_memory', 'quality_correction')
RESULTS = ('passed', 'passed_with_notes', 'failed', 'incomplete', 'unknown')   # unknown: nachgetragen, Ergebnis nicht im Bericht (#340)

# Bezeichnung und Kürzel je Prüfart (Kürzel für die Textfassung, z. B. „S✓ L✓ K✓“)
LABELS = {
    'de': {'structure': ('Struktur', 'S'), 'language': ('Sprache', 'L'), 'proofreading': ('Korrektur', 'K'),
           'story_memory': ('Gedächtnis', 'G'), 'quality_correction': ('Qualität', 'Q'),
           'analysis': ('Analyse', 'A')},
    'en': {'structure': ('Structure', 'S'), 'language': ('Language', 'L'), 'proofreading': ('Proofreading', 'K'),
           'story_memory': ('Story memory', 'G'), 'quality_correction': ('Quality', 'Q'),
           'analysis': ('Analysis', 'A')},
}
ANALYSIS_LABELS = {
    'de': {'characters': 'Figuren', 'summaries': 'Kurzbeschreibungen', 'style': 'Stil', 'places': 'Schauplätze',
           'timeline': 'Zeitleiste', 'continuity': 'Widersprüche', 'language': 'Sprache', 'chronology': 'Chronologie',
           'portraits': 'Personenbilder'},
    'en': {'characters': 'Characters', 'summaries': 'Summaries', 'style': 'Style', 'places': 'Places',
           'timeline': 'Timeline', 'continuity': 'Continuity', 'language': 'Language', 'chronology': 'Chronology',
           'portraits': 'Character images'},
}
ANALYSIS_SHORT = {'characters': 'AF', 'summaries': 'AK', 'style': 'ASt', 'places': 'AO', 'timeline': 'AZ',
                  'continuity': 'AW', 'language': 'ASp', 'chronology': 'AC', 'portraits': 'AP'}
RESULT_MARK = {'passed': '✓', 'passed_with_notes': '✓·', 'failed': '✗', 'incomplete': '…', 'unknown': '?'}
RESULT_TEXT = {
    'de': {'passed': 'bestanden', 'passed_with_notes': 'bestanden mit Hinweisen', 'failed': 'nicht bestanden',
           'incomplete': 'unvollständig', 'unknown': 'Ergebnis unbekannt'},
    'en': {'passed': 'passed', 'passed_with_notes': 'passed with notes', 'failed': 'failed',
           'incomplete': 'incomplete', 'unknown': 'result unknown'},
}
STATE_TEXT = {
    'de': {'current': 'aktuell', 'changed': 'seit Prüfung geändert', 'unknown': 'Stand unbekannt'},
    'en': {'current': 'current', 'changed': 'changed since check', 'unknown': 'state unknown'},
}
LEGEND = {
    'de': ('Prüfungen: S Struktur · L Sprache · K Korrektur · G Gedächtnis · Q Qualität · A… Analyse · '
           '✓ bestanden · ✓· mit Hinweisen · ✗ nicht bestanden · … unvollständig · * seit Prüfung geändert · '
           '? Stand bzw. Ergebnis unbekannt. Ein Tag zeigt nur die neueste Prüfung je Art; frühere stehen unter '
           '„Frühere Prüfungen“. Ein Tag ist keine Freigabe.'),
    'en': ('Checks: S structure · L language · K proofreading · G story memory · Q quality · A… analysis · '
           '✓ passed · ✓· with notes · ✗ failed · … incomplete · * changed since check · ? state or result unknown. '
           'A tag shows only the latest check per kind; earlier ones are listed under “Earlier checks”. '
           'A tag is not an approval.'),
}
# Legende ohne Verweis auf „Frühere Prüfungen“ für Ansichten, die sie nicht zeigen (#398).
LEGEND_LATEST = {k: v.split(' Ein Tag zeigt')[0].split(' A tag shows')[0] +
                 (' Ein Tag zeigt nur die neueste Prüfung je Art. Ein Tag ist keine Freigabe.' if k == 'de' else
                  ' A tag shows only the latest check per kind. A tag is not an approval.')
                 for k, v in LEGEND.items()}


# ---------- Laden und Speichern ----------

def path(base):
    return Path(base) / FILE


def normalize(data):
    """Von Hand geschriebene Daten (2026-11-17 ohne Anführungszeichen) als Text lesen."""
    if isinstance(data, dict) and isinstance(data.get('checks'), list):
        for e in data['checks']:
            if isinstance(e, dict) and isinstance(e.get('date'), (datetime.date, datetime.datetime)):
                e['date'] = e['date'].isoformat()[:10]
    return data


def load(base):
    p = path(base)
    if not p.is_file():
        return []
    data = normalize(yaml.safe_load(p.read_text(encoding='utf-8')) or {})
    return [e for e in data.get('checks') or [] if isinstance(e, dict) and e.get('kind') and e.get('result')]


def save(base, entries):
    p = path(base)
    p.parent.mkdir(parents=True, exist_ok=True)
    head = ('# Prüfprotokoll (#331): gelaufene Prüfungen mit Umfang, Fassung und Ergebnis.\n'
            '# Ein Eintrag ist keine Freigabe. Pflege: python3 scripts/checks.py record …\n')
    p.write_text(head + yaml.safe_dump({'checks': entries}, allow_unicode=True, sort_keys=False, width=10**6),
                 encoding='utf-8')


def next_id(entries):
    nums = [int(m.group(1)) for e in entries for m in [re.match(r'^pr-(\d+)$', str(e.get('id', '')))] if m]
    return f'pr-{(max(nums) if nums else 0) + 1:03d}'


# ---------- Umfang und Fingerabdruck ----------

def sections(config):
    """[(kapitel, abschnitt)] in Buchreihenfolge."""
    return [(ch, s) for ch in config['structure']['chapters'] for s in ch['sections']]


def matter(config):
    from render_view import matter_items
    return [i for _, i in matter_items(config)]


def resolve(config, scope):
    """Abschnitts- bzw. Teil-IDs, die ein Umfang abdeckt, in Buchreihenfolge."""
    scope = [scope] if isinstance(scope, str) else list(scope or [])
    out = []
    for ch, s in sections(config):
        if 'book' in scope or ch['id'] in scope or s['id'] in scope:
            out.append(s['id'])
    for i in matter(config):
        if 'book' in scope or i['id'] in scope:
            out.append(i['id'])
    return out


def manuscript(base, config, sid):
    from render_view import section_file
    for _, s in sections(config):
        if s['id'] == sid:
            return section_file(Path(base), s)[3]
    for i in matter(config):
        if i['id'] == sid:
            p = Path(base) / i['path']
            if p.is_file():
                text = p.read_text(encoding='utf-8')
                m = re.match(r'\A---\n.*?\n---\n', text, re.S)
                return text[m.end():] if m else text
    return None


def digest(text):
    return 'sha256:' + hashlib.sha256((text or '').strip().encode('utf-8')).hexdigest()[:16]


def digests(base, config, ids):
    out = {}
    for sid in ids:
        ms = manuscript(base, config, sid)
        if ms is not None:
            out[sid] = digest(ms)
    return out


def digests_at(base, config, ids, commit):
    """Fingerabdrücke der Fassung in commit (#406): Manuskript wie section_file, aus git show gelesen."""
    paths = {s['id']: s['path'] for _, s in sections(config)}
    paths.update({i['id']: i['path'] for i in matter(config)})
    out = {}
    for sid in ids:
        if sid not in paths:
            continue
        r = subprocess.run(['git', '-C', str(base), 'show', f'{commit}:./{paths[sid]}'], capture_output=True, text=True)
        if r.returncode != 0:
            raise ValueError(f'{paths[sid]} gibt es in Commit {commit} nicht; ohne --commit oder mit --backfill eintragen')
        text = r.stdout
        m = re.match(r'\A---\n.*?\n---\n', text, re.S)
        body = text[m.end():] if m else text
        if sid in {s['id'] for _, s in sections(config)}:
            body = body.split('\n## Manuskript\n', 1)[1].strip() if '\n## Manuskript\n' in body else ''
        out[sid] = digest(body)
    return out


def head_commit(base):
    try:
        r = subprocess.run(['git', '-C', str(base), 'rev-parse', 'HEAD'], capture_output=True, text=True, timeout=10)
    except (OSError, subprocess.SubprocessError):
        return None
    return r.stdout.strip() if r.returncode == 0 and r.stdout.strip() else None


# ---------- Eintragen ----------

def when(e):
    """Sortierschlüssel und Anzeige: „JJJJ-MM-TT“ bzw. „JJJJ-MM-TT HH:MM“ (#340, Uhrzeit optional)."""
    return (str(e.get('date') or '') + (' ' + str(e['time']) if e.get('time') else '')).strip()


BACKFILL_NOTE = 'nachgetragen (#340) aus vorhandenem Bericht; geprüfte Fassung nicht gespeichert'


def record(base, config, kind, scope, result, report=None, date=None, commit=None, note=None, run=None, time=None,
           backfill=False, notes=None):
    """Einen Prüflauf eintragen; Fingerabdrücke und Commit werden vom heutigen Stand genommen. Ist ein anderer
    Commit als HEAD angegeben, kommen die Fingerabdrücke aus diesem Commit (#406): Wurde danach korrigiert, zeigt
    der Tag „seit Prüfung geändert“.

    backfill=True (#344): älteren Bericht nachtragen. Dann weder Fingerabdrücke noch HEAD-Commit (die geprüfte
    Fassung ist nicht bekannt, der Stand zeigt „unbekannt“); ein ausdrücklich angegebener Commit bleibt."""
    base = Path(base)
    if kind not in EDITORIAL and not (kind.startswith('analysis:') and kind.split(':', 1)[1]):
        raise ValueError(f'Unbekannte Prüfart: {kind}')
    if result not in RESULTS:
        raise ValueError(f'Unbekanntes Ergebnis: {result}')
    scope = [scope] if isinstance(scope, str) else list(scope)
    ids = resolve(config, scope)
    if not ids:
        raise ValueError(f'Umfang deckt keinen Abschnitt ab: {", ".join(scope)}')
    entries = load(base)
    entry = {'id': next_id(entries), 'kind': kind, 'scope': scope,
             'date': str(date or datetime.date.today().isoformat()), 'result': result}
    if time or not date:   # Uhrzeit (#340): angegeben oder jetzt, bei nachgetragenem Datum ohne Uhrzeit keine
        entry['time'] = str(time or datetime.datetime.now().strftime('%H:%M'))
    head = head_commit(base)
    commit = commit or (None if backfill else head)
    if commit:
        entry['commit'] = commit
    if not backfill:
        same = not commit or not head or head.startswith(commit) or commit.startswith(head)
        entry['digests'] = digests(base, config, ids) if same else digests_at(base, config, ids, commit)
    elif not note:
        note = BACKFILL_NOTE
    if report:
        entry['report'] = str(report)
    if run:
        entry['run'] = run
    if note:
        entry['note'] = note
    if notes is not None:   # offene Hinweise des Berichts (#362)
        if int(notes) < 0:
            raise ValueError('--notes muss 0 oder größer sein')
        entry['notes'] = int(notes)
    entries.append(entry)
    save(base, entries)
    return entry


def record_analysis(base, config, head):
    """Nach einem Analyselauf (analyze.run): Lauf als Prüfung `analysis:<art>` eintragen."""
    scope = head.get('scope') or 'book'
    if str(scope).isdigit():
        chapters = config['structure']['chapters']
        n = int(scope)
        if not 1 <= n <= len(chapters):
            return None
        scope = chapters[n - 1]['id']
    else:
        scope = 'book'
    result = 'passed_with_notes' if head.get('suggestions') else 'passed'
    stamp = str(head.get('created_at') or '')
    day = stamp[:10] or None
    clock = stamp[11:16] if re.match(r'\d{2}:\d{2}', stamp[11:16]) else None
    report = f'analysis/{head["kind"]}/{head["id"]}.md'
    return record(base, config, f'analysis:{head["kind"]}', [scope], result, report=report, date=day, run=head['id'],
                  time=clock)


def backfill(base, config):
    """Abgeschlossene Analyseläufe ohne Eintrag nachtragen (ohne Fingerabdruck: Stand unbekannt)."""
    base = Path(base)
    entries = load(base)
    known = {(e.get('kind'), e.get('run')) for e in entries if e.get('run')}
    added = []
    for run in sorted((base / 'analysis').glob('*/run-[0-9][0-9][0-9].md')) if (base / 'analysis').is_dir() else []:
        m = re.match(r'\A---\n(.*?)\n---\n', run.read_text(encoding='utf-8'), re.S)
        head = yaml.safe_load(m.group(1)) if m else {}
        kind = head.get('kind') or run.parent.name
        if (f'analysis:{kind}', head.get('id')) in known or not head.get('id'):
            continue
        scope = head.get('scope') or 'book'
        chapters = config['structure']['chapters']
        scope = chapters[int(scope) - 1]['id'] if str(scope).isdigit() and 1 <= int(scope) <= len(chapters) else 'book'
        entry = {'id': next_id(entries), 'kind': f'analysis:{kind}', 'scope': [scope],
                 'date': str(head.get('created_at') or '')[:10] or datetime.date.today().isoformat(),
                 'result': 'passed_with_notes' if head.get('suggestions') else 'passed',
                 'report': str(run.relative_to(base)), 'run': head['id'],
                 **({'time': str(head['created_at'])[11:16]} if re.match(r'.{10}[T ]\d{2}:\d{2}', str(head.get('created_at') or '')) else {}),
                 'note': 'nachgetragen (#331); geprüfte Fassung nicht gespeichert'}
        entries.append(entry)
        added.append(entry)
    if added:
        save(base, entries)
    return added


# ---------- Ältere Berichte nachtragen (#340) ----------

KIND_WORDS = (   # Reihenfolge = Vorrang; Suche in Dateiname und Überschrift
    ('proofreading', ('schlusskorrektur', 'korrektorat', 'proofread')),
    ('structure', ('strukturlektorat', 'struktur', 'structur')),
    ('language', ('sprachlektorat', 'sprache', 'language')),
    ('story_memory', ('buchgedächtnis', 'buchgedaechtnis', 'story-memory', 'story_memory', 'story memory')),
    ('quality_correction', ('qualitätssicherung', 'qualitaetssicherung', 'qualität', 'qualitaet', 'nachprüfung',
                            'nachpruefung', 'redaktionslauf', 'redaktion', 'quality')),
)
RESULT_WORDS = (   # Reihenfolge = Vorrang
    ('failed', (r'nicht\s+bestanden', r'\bfailed\b')),
    ('passed_with_notes', (r'bestanden\s+mit\s+hinweisen', r'passed\s+with\s+notes')),
    ('incomplete', (r'\bunvollständig\b', r'\bincomplete\b')),
    ('passed', (r'\bbestanden\b', r'\bpassed\b')),
)


RESULT_KEY = r'(ergebnis|result|gesamturteil|urteil|gesamtergebnis|fazit|verdict)\b'


def _results_in(line):
    """Alle Ergebnisse einer Zeile; „nicht bestanden“ zählt nicht zusätzlich als „bestanden“."""
    low, out = line.lower(), []
    for res, pats in RESULT_WORDS:
        for p in pats:
            if re.search(p, low):
                out.append(res)
                low = re.sub(p, ' ', low)
    return out


def _result_lines(text):
    """Zeilen, die ein Gesamtergebnis tragen (#347): eine Ergebniszeile („Ergebnis: …“) oder der erste Absatz
    unter einer Überschrift „Ergebnis“ („## Ergebnis“ + „**Bestanden mit Hinweisen.** …“). Tabellenzeilen
    (`|`) zählen nie: Spalten „Ergebnis der erneuten Lektüre“ oder Ergebnisse je Kapitel sind kein Gesamtergebnis."""
    lines = text.splitlines()
    out, i = [], 0
    while i < len(lines):
        line = lines[i].strip()
        if line.startswith('|'):
            i += 1
            continue
        if line.startswith('#') and re.search(RESULT_KEY, line, re.I):
            j = i + 1
            while j < len(lines) and not lines[j].strip():
                j += 1
            while j < len(lines) and lines[j].strip() and not lines[j].lstrip().startswith(('#', '|')):
                out.append(lines[j])
                j += 1
            i = j
            continue
        if re.search(RESULT_KEY, line, re.I):
            out.append(line)
        i += 1
    return out


def _result_from(text):
    """(Ergebnis, mehrdeutig): Ergebnis nur aus Ergebniszeilen bzw. dem Absatz unter „## Ergebnis“, sonst unknown.
    Nennen diese Stellen verschiedene Ergebnisse („nicht bestanden … nach Korrektur bestanden“), wird keines
    gewählt: (`unknown`, [die gefundenen]) – der Bericht gilt dann als nicht eindeutig (#347)."""
    found = []
    for line in _result_lines(text):
        for res in _results_in(line):
            if res not in found:
                found.append(res)
    if len(found) == 1:
        return found[0], []
    return 'unknown', found


def _ids_in(config, hay):
    """Ausdrücklich genannte Kapitel- und Abschnitts-IDs."""
    chapters = config['structure']['chapters']
    ids = {ch['id'] for ch in chapters} | {s['id'] for _, s in sections(config)}
    found = [i for i in sorted(ids, key=len, reverse=True) if re.search(rf'(?<![\w]){re.escape(i)}(?![\w]|-[^\W\d])', hay)]
    return [i for i in found if not any(i != j and j.startswith(i + '-') for j in found)]


CHAPTER_WORD = r'(?:kapitel|kap\.?|chapters?|ch\.?)'
RANGE_SEP = r'(?:[\s_]*[–—-][\s_]*|[\s_-]+(?:bis|to|through)[\s_-]+)'
LIST_SEP = r'(?:[\s_]*,[\s_]*|[\s_-]+(?:und|and|&)[\s_-]+)'


def _numbers_in(config, hay, filename=False):
    """Kapitel und Abschnitte aus Nummern (#347): „Kapitel 1 bis 8“, `kapitel-1-bis-8`, „Kap. 3 und 5“,
    „6.3“, „8.2 und 8.3“, „6.1–6.3“, im Dateinamen auch `6-3`. Liefert IDs; Nummern außerhalb des Buchs fallen weg."""
    chapters = config['structure']['chapters']
    hay = re.sub(r'\d{4}-\d{2}-\d{2}|\d{1,2}\.\d{1,2}\.\d{4}', ' ', hay)   # Daten sind keine Nummern
    chs, secs = [], []

    def chapter(n):
        if 1 <= n <= len(chapters) and chapters[n - 1]['id'] not in chs:
            chs.append(chapters[n - 1]['id'])

    def section(c, s):
        if 1 <= c <= len(chapters) and 1 <= s <= len(chapters[c - 1]['sections']):
            sid = chapters[c - 1]['sections'][s - 1]['id']
            if sid not in secs:
                secs.append(sid)

    sec = r'(\d{1,2})[.](\d{1,2})' if not filename else r'(\d{1,2})[.-](\d{1,2})'
    rest = hay
    # Abschnittsbereiche „6.1–6.3“ und Listen „8.2 und 8.3“
    for m in re.finditer(rf'(?<![\d.]){sec}{RANGE_SEP}{sec}(?![\d.])', rest):
        a, b, c, d = map(int, m.groups())
        if a == c and b < d:
            for s in range(b, d + 1):
                section(a, s)
            rest = rest.replace(m.group(0), ' ')
    # Kapitel mit Wort davor: Bereich oder Liste
    for m in re.finditer(rf'(?<![\w]){CHAPTER_WORD}[\s._-]*((?:0*\d+)(?:(?:{RANGE_SEP}|{LIST_SEP})0*\d+)*)(?![.\d])',
                         rest, re.I):
        part = m.group(1)
        nums = [int(x) for x in re.findall(r'\d+', part)]
        seps = re.findall(rf'{RANGE_SEP}|{LIST_SEP}', part)
        if len(nums) == 2 and seps and re.fullmatch(RANGE_SEP, seps[0]) and nums[0] < nums[1]:
            for n in range(nums[0], nums[1] + 1):
                chapter(n)
        elif len(nums) == 2 and seps and re.fullmatch(RANGE_SEP, seps[0]) and filename:
            section(*nums)              # `kapitel-6-3` im Dateinamen: Abschnitt 6.3
        else:
            for n in nums:
                chapter(n)
        rest = rest.replace(m.group(0), ' ')
    # einzelne Abschnittsnummern
    pat = rf'(?<![\d.\w]){sec}(?![\d]|[.]\d)' if filename else rf'(?<![\d.]){sec}(?![\d]|[.]\d)'
    for m in re.finditer(pat, rest):
        section(int(m.group(1)), int(m.group(2)))
    # genanntes Kapitel, dessen Abschnitte einzeln genannt sind („Kapitel 6, Abschnitt 6.3“): die Abschnitte gelten
    chs = [c for c in chs if not any(s['id'] in secs for ch in chapters if ch['id'] == c for s in ch['sections'])]
    return chs + secs


def _scope_from(config, name, text):
    """Umfang eines Berichts (#347): zuerst Dateiname und Titel, erst dann eine Umfangszeile im Kopf
    („Umfang: …“, „Geprüft: …“). Kapitel, die im übrigen Text nur erwähnt werden, zählen nicht."""
    chapters = config['structure']['chapters']
    order = ['book'] + [ch['id'] for ch in chapters] + [s['id'] for _, s in sections(config)]
    lines = text.splitlines()
    title = next((l for l in lines if l.startswith('#')), '')
    head = [l for l in lines[:25] if re.match(r'\W*(umfang|prüfumfang|geprüft|gegenstand|scope|reviewed)\b', l.strip(), re.I)]
    for hay, filename in ((name, True), (title, False), ('\n'.join(head), False)):
        found = _ids_in(config, hay) or _numbers_in(config, hay, filename)
        if not found and re.search(r'\b(gesamtes buch|ganzes buch|whole book|buchweit|book-wide)\b',
                                   hay.replace('-', ' ').replace('_', ' '), re.I):
            found = ['book']
        if found:
            return sorted(set(found), key=order.index)
    found = _ids_in(config, '\n'.join(lines[:15]))   # ausdrückliche IDs im Kopf bleiben wie bisher gültig
    return sorted(set(found), key=order.index) if found else []


def report_time(text):
    """Uhrzeit (HH:MM) aus dem Kopf eines Berichts, sonst ''."""
    # „14:05“ oder „14.05 Uhr“; ein Datum wie „19.11.2026“ ist keine Uhrzeit
    t = (re.search(r'(?<![\d:.])([01]?\d|2[0-3]):([0-5]\d)(?![\d:])', text[:2000])
         or re.search(r'(?<![\d.])([01]?\d|2[0-3])\.([0-5]\d)\s*Uhr', text[:2000]))
    return f'{int(t.group(1)):02d}:{t.group(2)}' if t else ''


def missing_times(base, entries):
    """[(eintrag, uhrzeit)] für Einträge ohne `time`, deren Bericht eine Uhrzeit nennt (#345)."""
    out = []
    for e in entries:
        if e.get('time') or not e.get('report'):
            continue
        f = Path(base) / str(e['report'])
        if f.is_file():
            clock = report_time(f.read_text(encoding='utf-8', errors='replace'))
            if clock:
                out.append((e, clock))
    return out


def complete(base, entry_id, time=None, date=None, commit=None):
    """Fehlende Angaben eines Eintrags ergänzen (#345); vorhandene werden nie überschrieben.
    Rückgabe: Liste der gesetzten Felder."""
    if time and not re.fullmatch(r'([01]\d|2[0-3]):[0-5]\d', time):
        raise ValueError(f'Uhrzeit nicht im Format HH:MM: {time}')
    entries = load(base)
    e = next((x for x in entries if str(x.get('id')) == entry_id), None)
    if e is None:
        raise ValueError(f'Eintrag nicht gefunden: {entry_id}')
    done = []
    for key, value in (('time', time), ('date', date), ('commit', commit)):
        if value and not e.get(key):
            e[key] = value
            done.append(key)
        elif value and str(e.get(key)) != value:
            raise ValueError(f'{entry_id}: {key} ist schon gesetzt ({e[key]}) und wird nicht überschrieben')
    if done:
        save(base, entries)
    return done


def candidates(base, config, entries=None):
    """Berichte unter analysis/ und editorial/ ohne Eintrag im Prüfprotokoll, mit erkannten Angaben.

    Analyseläufe (analysis/<art>/run-NNN.md) übernimmt backfill(). Rückgabe je Bericht: report, kind, scope,
    date, result (`unknown`, wenn der Bericht keine Ergebniszeile hat), ready (kind und scope erkannt)."""
    base = Path(base)
    entries = load(base) if entries is None else entries
    known = {str(e.get('report')) for e in entries if e.get('report')}
    files = []
    for folder in ('analysis', 'editorial'):
        d = base / folder
        if d.is_dir():
            files += sorted(p for p in d.rglob('*.md')
                            if not re.fullmatch(r'run-\d{3}', p.stem) and 'cache' not in p.relative_to(d).parts)
    out = []
    for f in files:
        rel = str(f.relative_to(base))
        if rel in known:
            continue
        text = f.read_text(encoding='utf-8', errors='replace')
        title = next((l for l in text.splitlines() if l.startswith('#')), '')
        hay = (f.stem + ' ' + title).lower()
        kind = next((k for k, words in KIND_WORDS if any(w in hay for w in words)), '')
        m = re.search(r'(\d{4}-\d{2}-\d{2})', f.name) or re.search(r'(\d{4}-\d{2}-\d{2})', text[:2000])
        date = m.group(1) if m else ''
        clock = report_time(text) if date else ''
        scope = _scope_from(config, f.stem, text)
        result, mixed = _result_from(text)
        c = {'report': rel, 'kind': kind, 'scope': scope, 'date': date, 'time': clock, 'result': result,
             'ready': bool(kind and scope and date and not mixed)}
        if mixed:
            c['results'] = mixed   # verschiedene Ergebnisse im Bericht: nicht eindeutig (#347)
        out.append(c)
    return out


def _report_key(base, report):
    """Bericht als Pfad relativ zum Buch, auch wenn er mit Buchordner oder nur als Dateiname angegeben ist."""
    p = Path(str(report))
    try:
        return str(p.resolve().relative_to(Path(base).resolve()))
    except (ValueError, OSError):
        return str(p)


def select(base, found, only=None, skip=None, fix=None):
    """Kandidaten eingrenzen und berichtigen (#347).

    only/skip: Berichte (Pfad relativ zum Buch oder Dateiname). fix: {kind, scope, result, date, time} – nur mit
    genau einem Bericht in `only`; Umfang wird gegen das Buch geprüft, Ergebnis muss eines von RESULTS sein."""
    def match(c, names):
        return any(c['report'] == _report_key(base, n) or Path(c['report']).name == Path(str(n)).name for n in names)
    out = [c for c in found if (not only or match(c, only)) and not (skip and match(c, skip))]
    if only:
        missing = [n for n in only if not any(match(c, [n]) for c in found)]
        if missing:
            raise ValueError('Kein Bericht ohne Eintrag: ' + ', '.join(map(str, missing)))
    fix = {k: v for k, v in (fix or {}).items() if v}
    if fix:
        if not only or len(out) != 1:
            raise ValueError('Berichtigen (--kind/--scope/--result/--date/--time) nur mit genau einem --only <bericht>')
        c = out[0] = dict(out[0])
        if 'result' in fix and fix['result'] not in RESULTS:
            raise ValueError(f'Unbekanntes Ergebnis: {fix["result"]}')
        if 'kind' in fix and fix['kind'] not in EDITORIAL and not re.fullmatch(r'analysis:\w+', fix['kind']):
            raise ValueError(f'Unbekannte Prüfart: {fix["kind"]}')
        c.update(fix)
        c.pop('results', None) if 'result' in fix else None
        c['ready'] = bool(c['kind'] and c['scope'] and c['date'] and not c.get('results'))
        c['corrected'] = sorted(fix)
    return out


def import_reports(base, config, apply=False, only=None, skip=None, fix=None):
    """Kandidaten auflisten; mit apply=True die erkannten (ready) ohne Fingerabdruck eintragen.
    Ergebnisse werden nie erfunden: ohne Ergebniszeile bleibt `unknown`, bei verschiedenen Ergebnissen wird
    nichts eingetragen. only/skip/fix wie in select() (#347)."""
    base = Path(base)
    entries = load(base)
    found = select(base, candidates(base, config, entries), only, skip, fix)
    if fix and fix.get('scope'):
        scope = [fix['scope']] if isinstance(fix['scope'], str) else list(fix['scope'])
        if not resolve(config, scope):
            raise ValueError(f'Umfang deckt keinen Abschnitt ab: {", ".join(scope)}')
    added = []
    if apply:
        for c in found:
            if not c['ready']:
                continue
            entry = {'id': next_id(entries), 'kind': c['kind'], 'scope': c['scope'], 'date': c['date'],
                     **({'time': c['time']} if c.get('time') else {}),
                     'result': c['result'], 'report': c['report'],
                     'note': BACKFILL_NOTE + ('; berichtigt: ' + ', '.join(c['corrected']) if c.get('corrected') else '')}
            entries.append(entry)
            added.append(entry)
        # #345: Uhrzeit bestehender Einträge aus dem Bericht ergänzen (nicht bei eingegrenztem Import)
        timed = [] if (only or skip) else missing_times(base, entries)
        for e, clock in timed:
            e['time'] = clock
        if added or timed:
            save(base, entries)
    return found, added


# ---------- Auswerten ----------

def label(kind, language='de'):
    lang = language if language in LABELS else 'de'
    if kind.startswith('analysis:'):
        art = kind.split(':', 1)[1]
        name = ANALYSIS_LABELS[lang].get(art, art)
        return f'{LABELS[lang]["analysis"][0]} {name}', ANALYSIS_SHORT.get(art, 'A')
    return LABELS[lang].get(kind, (kind, kind[:1].upper()))


def state(base, config, entry, ids, now_digests):
    """'current' | 'changed' | 'unknown' für die Abschnitte `ids` eines Eintrags."""
    saved = entry.get('digests') or {}
    if not saved:
        return 'unknown'
    covered = [i for i in ids if i in saved]
    if not covered:
        return 'unknown'
    return 'changed' if any(now_digests.get(i) != saved[i] for i in covered) else 'current'


def tags(base, config, unit_ids, entries=None, language='de', now_digests=None):
    """Tags für eine Einheit (Liste von Abschnitts-IDs): je Prüfart der neueste Eintrag, der sie berührt.

    Rückgabe: [{CK_KIND, CK_LABEL, CK_SHORT, CK_RESULT, CK_RESULT_TEXT, CK_MARK, CK_DATE, CK_REPORT,
    CK_STATE, CK_STATE_TEXT, CK_PARTIAL, CK_TEXT, CK_TAG}] in fester Reihenfolge der Prüfarten.
    """
    entries = load(base) if entries is None else entries
    lang = language if language in LABELS else 'de'
    unit = set(unit_ids)
    if not unit:
        return []
    now_digests = now_digests if now_digests is not None else digests(base, config, list(unit))
    latest = {}
    for i, e, hit in touching(config, entries, unit):
        key = e['kind']
        rank = (when(e), i)
        if key not in latest or rank >= latest[key][0]:
            latest[key] = (rank, e, hit)
    order = {k: n for n, k in enumerate(EDITORIAL)}
    out = []
    for key, (_, e, hit) in sorted(latest.items(), key=lambda kv: (order.get(kv[0], 99), kv[0])):
        out.append(dict(localize({'CK_KIND': key, 'CK_RESULT': e['result'], 'CK_DATE': str(e.get('date') or ''),
                                  'CK_WHEN': when(e), 'CK_REPORT': e.get('report') or '',
                                  'CK_STATE': state(base, config, e, hit, now_digests),
                                  'CK_PARTIAL': '1' if len(hit) < len(unit) else ''}, lang),
                        CK_ID=str(e.get('id') or ''), CK_NOTE=e.get('note') or ''))
    return out


def touching(config, entries, unit):
    """[(index, eintrag, berührte_ids)] aller Einträge, die die Einheit berühren."""
    out = []
    for i, e in enumerate(entries):
        hit = [x for x in resolve(config, e.get('scope') or []) if x in unit]
        if hit:
            out.append((i, e, hit))
    return out


def history(base, config, unit_ids, entries=None, language='de', now_digests=None):
    """Frühere Prüfungen (#340): alle Einträge, die die Einheit berühren, außer dem neuesten je Prüfart;
    neueste zuerst. Felder wie bei tags() plus CK_ID und CK_NOTE."""
    entries = load(base) if entries is None else entries
    lang = language if language in LABELS else 'de'
    unit = set(unit_ids)
    if not unit or not entries:
        return []
    now_digests = now_digests if now_digests is not None else digests(base, config, list(unit))
    hits = sorted(touching(config, entries, unit), key=lambda t: (when(t[1]), t[0]), reverse=True)
    seen, out = set(), []
    for _, e, hit in hits:
        if e['kind'] not in seen:
            seen.add(e['kind'])
            continue
        out.append(dict(localize({'CK_KIND': e['kind'], 'CK_RESULT': e['result'], 'CK_DATE': str(e.get('date') or ''),
                                  'CK_WHEN': when(e),
                                  'CK_REPORT': e.get('report') or '',
                                  'CK_STATE': state(base, config, e, hit, now_digests),
                                  'CK_PARTIAL': '1' if len(hit) < len(unit) else ''}, lang),
                        CK_ID=str(e.get('id') or ''), CK_NOTE=e.get('note') or ''))
    return out


def history_text(items, language='de'):
    """Textfassung „Frühere Prüfungen“, nach Prüfart gruppiert; je Eintrag Datum, Uhrzeit und Ergebniszeichen."""
    if not items:
        return []
    head = 'Frühere Prüfungen' if language != 'en' else 'Earlier checks'
    groups = {}
    for t in items:
        groups.setdefault(t['CK_LABEL'], []).append(t)
    lines = [f'**{head} ({len(items)}):**']
    for name, ts in groups.items():
        lines.append(f'- {name}: ' + ' · '.join(
            f'{t["CK_WHEN"]} {t["CK_MARK"]}{ {"changed": "*", "unknown": "?"}.get(t["CK_STATE"], "") if t["CK_MARK"] != "?" else ""}'
            for t in ts))
    return lines


HISTORY_KEYS = ('CK_KIND', 'CK_LABEL', 'CK_WHEN', 'CK_DATE', 'CK_TAG', 'CK_MARK', 'CK_TEXT', 'CK_RESULT', 'CK_STATE', 'CK_REPORT',
                'CK_ID', 'CK_NOTE')
# Projektübersicht (#497): je Kapitel nur, was die Kurzliste zeigt (Art, Zeit, Marke, Stand, Kurztext als Tooltip); Notiz und
# Bericht stehen in der Kapitelansicht. Höchstens die neuesten HISTORY_CAP Einträge; die Gesamtzahl nennt die Prüfdetails-Zeile.
HISTORY_KEYS_SLIM = ('CK_LABEL', 'CK_WHEN', 'CK_DATE', 'CK_MARK', 'CK_TEXT', 'CK_RESULT', 'CK_STATE')
HISTORY_CAP = 10


def history_json(items, keep=HISTORY_KEYS):
    """Widget: frühere Prüfungen kompakt (ab UI 0.74.0, #674): gepackt, ohne CK_MARK und CK_TEXT (die setzt gw.js zusammen).
    Das Widget gruppiert nach CK_LABEL und zeigt je Eintrag CK_WHEN."""
    return as_payload(items, tuple(k for k in keep if k not in COMPOSED_KEYS))


def localize(tag, language='de'):
    """Beschriftungen eines Tags (neu) setzen; Rohwerte CK_KIND, CK_RESULT, CK_DATE, CK_STATE, CK_PARTIAL bleiben."""
    lang = language if language in LABELS else 'de'
    name, short = label(tag['CK_KIND'], lang)
    st, res = tag['CK_STATE'], tag['CK_RESULT']
    mark = RESULT_MARK.get(res, '')
    suffix = {'changed': '*', 'unknown': '?'}.get(st, '')
    if mark == '?' and suffix == '?':
        suffix = ''
    text = (f'{name}: {RESULT_TEXT[lang].get(res, res)}, {tag.get("CK_WHEN") or tag["CK_DATE"]} · {STATE_TEXT[lang][st]}'
            + ((' · teilweise' if lang == 'de' else ' · partial') if tag.get('CK_PARTIAL') else ''))
    return dict(tag, CK_LABEL=name, CK_SHORT=short, CK_RESULT_TEXT=RESULT_TEXT[lang].get(res, res), CK_MARK=mark,
                CK_STATE_TEXT=STATE_TEXT[lang][st], CK_TEXT=text, CK_TAG=f'{short}{mark}{suffix}',
                CK_PILL=f'{name} {mark}{suffix}'.strip())   # Widget-Tag mit Klartext wie „Qualität ✓·“ (#340)


JSON_KEYS = ('CK_TAG', 'CK_PILL', 'CK_TEXT', 'CK_RESULT', 'CK_STATE', 'CK_REPORT')
# Projektübersicht liest CK_PILL nicht (#360).
JSON_KEYS_SLIM = ('CK_TAG', 'CK_TEXT', 'CK_RESULT', 'CK_STATE', 'CK_REPORT')
# Erweiterte Darstellung der Projektübersicht (#398): zusätzlich Prüf-ID und Notiz im Tooltip.
JSON_KEYS_DETAIL = JSON_KEYS_SLIM + ('CK_ID', 'CK_NOTE')


def as_json(tag_list, keep=JSON_KEYS):
    """Widget (ghostwriter-ui, data-gw-checks), alte Form: JSON-Liste der Tags als Text. Für Clients ohne UI 0.74.0."""
    return json.dumps([{k: t.get(k, '') for k in keep} for t in tag_list], ensure_ascii=False, separators=(',', ':'))


# Kompakte Form (#674, ab UI 0.74.0): Felder, die gw.js aus den übrigen zusammensetzt, werden nicht gesendet.
COMPOSED_KEYS = ('CK_TAG', 'CK_TEXT', 'CK_MARK')
COMPACT_KEYS = ('CK_SHORT', 'CK_LABEL', 'CK_RESULT', 'CK_STATE', 'CK_WHEN', 'CK_PARTIAL', 'CK_REPORT')
COMPACT_KEYS_DETAIL = COMPACT_KEYS + ('CK_ID', 'CK_NOTE')


def as_payload(tag_list, keep=COMPACT_KEYS):
    """Prüf-Tags als echtes JSON statt als Zeichenkette, gepackt: {"k": [Schlüssel], "r": [[Werte], …], "p": [Berichtspfade]}.
    Jeder Berichtspfad steht einmal in `p`, `CK_REPORT` ist der Index. Leere Werte am Zeilenende entfallen. Keine Tags: ''."""
    if not tag_list:
        return ''
    reports, rows = [], []
    for t in tag_list:
        row = []
        for k in keep:
            v = t.get(k, '')
            if k == 'CK_REPORT' and v:
                if v not in reports:
                    reports.append(v)
                v = reports.index(v)
            row.append(v)
        while row and row[-1] == '':
            row.pop()
        rows.append(row)
    out = {'k': list(keep), 'r': rows}
    if reports:
        out['p'] = reports
    return out


TODO_MAX = 8   # höchstens so viele Kapitel in „Handlungsbedarf“, der Rest als Zahl (#538)
TODO_TEXT = {
    'de': {'head': 'Handlungsbedarf', 'chapter': 'Kapitel', 'failed': 'nicht bestanden', 'changed': 'Text seit der Prüfung geändert, neu prüfen',
           'notes': 'offene Hinweise', 'note': 'offener Hinweis', 'more': 'weitere Kapitel', 'book': 'Buch neu prüfen'},
    'en': {'head': 'Needs attention', 'chapter': 'Chapter', 'failed': 'failed', 'changed': 'text changed since the check, check again',
           'notes': 'open notes', 'note': 'open note', 'more': 'more chapters', 'book': 'Check the book again'},
}


def chapter_need_parts(row, language='de'):
    """Handlungsbedarf eines Kapitels (#538, #672): nicht bestandene Prüfungen, seit der Prüfung geänderter Text, offene Hinweise."""
    t = TODO_TEXT['en' if language == 'en' else 'de']
    parts = []
    for tag in row.get('CHAPTER_CHECKS') or []:
        name = tag.get('CK_LABEL') or tag.get('CK_TAG', '')
        if tag.get('CK_RESULT') == 'failed':
            parts.append(f'{name} {t["failed"]}')
        elif tag.get('CK_STATE') == 'changed':
            parts.append(f'{name}: {t["changed"]}')
    notes = row.get('CHAPTER_NOTES') or 0
    if notes:
        parts.append(f'{notes} ' + (t['note'] if notes == 1 else t['notes']))
    return parts


def chapter_need(row, language='de'):
    """Eine kurze Zeile je Kapitel für die erweiterte Projektübersicht (#672); leer, wenn nichts zu tun ist."""
    return ' · '.join(chapter_need_parts(row, language))


def todo_items(rows, language='de', book_stale=()):
    """Einträge des Handlungsbedarfs (#538, #593): [{'text', 'chapter_id', 'number', 'notes'}], zuerst buchweite Prüfungen
    („Buch neu prüfen“), dann je Kapitel nur, was jetzt zu tun ist (nicht bestanden, seit der Prüfung geändert, offene Hinweise)."""
    t = TODO_TEXT['en' if language == 'en' else 'de']
    items = []
    for b in book_stale or ():   # #538: buchweite Prüfung, seither wurde ein Abschnitt geändert
        items.append({'text': f'{t["book"]} ({b["label"][("en" if language == "en" else "de")]})', 'chapter_id': '',
                      'number': 0, 'notes': 0})
    for r in rows:
        parts = chapter_need_parts(r, language)
        if parts:
            items.append({'text': f'{t["chapter"]} {r["CHAPTER_NUMBER"]}: ' + ' · '.join(parts), 'chapter_id': r.get('CHAPTER_ID', ''),
                          'number': r['CHAPTER_NUMBER'], 'notes': r.get('CHAPTER_NOTES') or 0})
    return items


def todo(rows, language='de', book_stale=()):
    """Kompakte Zeilen „Handlungsbedarf“ für die Textfassung der Projektübersicht (#538): ohne Bedarf keine Zeile. Die
    Prüfhistorie bleibt in den Prüfdetails bzw. der Kapitelansicht."""
    t = TODO_TEXT['en' if language == 'en' else 'de']
    items = [f'- {i["text"]}' for i in todo_items(rows, language, book_stale)]
    if not items:
        return []
    shown = items[:TODO_MAX]
    if len(items) > TODO_MAX:
        shown.append(f'- … {len(items) - TODO_MAX} {t["more"]}')
    return [f'**{t["head"]}:**'] + shown + ['']


def todo_widget(rows, language='de', book_stale=()):
    """Block `TODO` der Vorlage projektuebersicht (#593): je Eintrag Klick zum Kapitel (view.chapter), bei offenen Hinweisen
    zweiter Knopf „Hinweise durchsehen“ (view.notes_review); buchweite Einträge sind nicht klickbar."""
    out = []
    for i in todo_items(rows, language, book_stale)[:TODO_MAX]:
        out.append({'TODO_TEXT': i['text'], 'TODO_ACTION': 'view.chapter' if i['chapter_id'] else '',
                    'TODO_ARGS': json.dumps({'chapter_id': i['chapter_id']} if i['chapter_id'] else {}, ensure_ascii=False, separators=(',', ':')),
                    'TODO_ACTION2': 'view.notes_review' if i['notes'] else '', 'TODO_ARGS2': '{}'})
    return out


def short_text(tag_list):
    """Textfassung: „S✓ L✓· K✓*“ bzw. „–“."""
    return ' '.join(t['CK_TAG'] for t in tag_list) or '–'


def recent(base, config, entries=None, language='de', limit=3):
    """Kopfzeile „Letzte Prüfungen“: die neuesten Einträge buchweit, je einer pro Prüfart.
    Rückgabe: [{CK_KIND, CK_RESULT, CK_MARK, CK_DATE, CK_LABEL}]."""
    entries = load(base) if entries is None else entries
    seen, out = set(), []
    for i, e in sorted(enumerate(entries), key=lambda ie: (when(ie[1]), ie[0]), reverse=True):
        if e['kind'] in seen:
            continue
        seen.add(e['kind'])
        out.append({'CK_KIND': e['kind'], 'CK_RESULT': e['result'], 'CK_MARK': RESULT_MARK.get(e['result'], ''),
                    'CK_DATE': str(e.get('date') or ''), 'CK_LABEL': label(e['kind'], language)[0]})
        if len(out) >= limit:
            break
    return out


def recent_text(items, language='de'):
    """„Sprache ✓· 2026-11-17 · Korrektur ✓ 2026-11-16“"""
    return ' · '.join(f'{label(i["CK_KIND"], language)[0]} {i["CK_MARK"]} {i["CK_DATE"]}'.strip() for i in items)


class Index:
    """Einmal laden, dann Tags für Buch, Kapitel und Abschnitte liefern (für die Ansichten)."""

    def __init__(self, base, config, language='de'):
        self.base, self.config, self.language = Path(base), config, language
        self.entries = load(base)
        all_ids = [s['id'] for _, s in sections(config)] + [i['id'] for i in matter(config)]
        self.now = digests(base, config, all_ids) if self.entries else {}

    def __bool__(self):
        return bool(self.entries)

    def chapter(self, ch):
        return tags(self.base, self.config, [s['id'] for s in ch['sections']], self.entries, self.language, self.now) \
            if self.entries else []

    def section(self, sid):
        return tags(self.base, self.config, [sid], self.entries, self.language, self.now) if self.entries else []

    def chapter_history(self, ch):
        return history(self.base, self.config, [s['id'] for s in ch['sections']], self.entries, self.language,
                       self.now) if self.entries else []

    def section_history(self, sid):
        return history(self.base, self.config, [sid], self.entries, self.language, self.now) if self.entries else []

    def book_stale(self):
        """Prüfarten (#538), deren neuester buchweiter Eintrag nicht mehr zum Text passt: ein Abschnitt hat sich seit der
        Prüfung geändert. [{'kind': …, 'label': {'de': …, 'en': …}}], nach Prüfart sortiert."""
        latest = {}
        for i, e in enumerate(self.entries):
            if 'book' in (e.get('scope') or []):
                rank = (when(e), i)
                if e['kind'] not in latest or rank >= latest[e['kind']][0]:
                    latest[e['kind']] = (rank, e)
        ids = list(self.now)
        out = []
        for kind, (_, e) in sorted(latest.items()):
            if state(self.base, self.config, e, ids, self.now) == 'changed':
                out.append({'kind': kind, 'label': {lang: label(kind, lang)[0] for lang in ('de', 'en')}})
        return out

    def open_notes(self, ch):
        """Offene Hinweise (#362): Summe von `notes` aus dem neuesten Eintrag je Prüfart, der das Kapitel berührt;
        nennen mehrere dieser Einträge denselben Bericht, zählt er nur einmal (#437).
        None, wenn keiner dieser Einträge `notes` führt (dann nichts anzeigen statt raten)."""
        unit = {s['id'] for s in ch['sections']}
        latest = {}
        for i, e, _ in touching(self.config, self.entries, unit):
            rank = (when(e), i)
            if e['kind'] not in latest or rank >= latest[e['kind']][0]:
                latest[e['kind']] = (rank, e)
        per_report = {}   # #437: ein Bericht mit mehreren Prüfarten zählt nur einmal (neuester Eintrag)
        for rank, e in latest.values():
            key = ('report', e['report']) if e.get('report') else ('kind', e['kind'])
            if key not in per_report or rank >= per_report[key][0]:
                per_report[key] = (rank, e)
        found = [e['notes'] for _, e in per_report.values() if isinstance(e.get('notes'), int)]
        return sum(found) if found else None

    def recent(self, limit=3):
        return recent(self.base, self.config, self.entries, self.language, limit) if self.entries else []


# ---------- Prüfung (validate_project.py) ----------

def errors(base, config):
    """Inhaltliche Prüfung über das Schema hinaus: eindeutige IDs, bekannter Umfang, Bericht vorhanden."""
    base = Path(base)
    p = path(base)
    out = []
    entries = load(base)
    ids = [e.get('id') for e in entries]
    out += [f'{p}: ID doppelt: {i}' for i in sorted({i for i in ids if ids.count(i) > 1})]
    known = {'book'} | {ch['id'] for ch in config['structure']['chapters']} | \
            {s['id'] for _, s in sections(config)} | {i['id'] for i in matter(config)} | \
            {r['id'] for r in (config['structure'].get('retired') or [])}   # historisch (#293)
    for e in entries:
        for sid in e.get('scope') or []:
            if sid not in known:
                out.append(f'{p}: {e.get("id")}: Umfang {sid} unbekannt')
        for sid in (e.get('digests') or {}):
            if sid not in known:
                out.append(f'{p}: {e.get("id")}: Fingerabdruck für unbekannten Abschnitt {sid}')
        if e.get('report') and not (base / e['report']).is_file():
            out.append(f'{p}: {e.get("id")}: Bericht {e["report"]} fehlt')
    return out


# ---------- Aufruf ----------

def main(argv=None):
    ap = argparse.ArgumentParser(description='Prüfprotokoll eines Buchs (#331)')
    sub = ap.add_subparsers(dest='cmd', required=True)
    r = sub.add_parser('record', help='Prüflauf eintragen')
    r.add_argument('project')
    r.add_argument('--kind', required=True, help=', '.join(EDITORIAL) + ' oder analysis:<art>')
    r.add_argument('--scope', required=True, action='append', help='book, Kapitel- oder Abschnitts-ID (mehrfach möglich)')
    r.add_argument('--result', required=True, choices=RESULTS)
    r.add_argument('--report')
    r.add_argument('--date')
    r.add_argument('--time', help='Uhrzeit HH:MM (Standard: jetzt, bei --date ohne Uhrzeit)')
    r.add_argument('--commit')
    r.add_argument('--note')
    r.add_argument('--notes', type=int, help='Zahl der offenen Hinweise im Bericht (#362), für die Projektübersicht')
    r.add_argument('--backfill', action='store_true',
                   help='älteren Bericht nachtragen: ohne Fingerabdruck und HEAD-Commit (#344); '
                        'automatisch bei --date vor heute ohne --commit')
    st = sub.add_parser('set', help='fehlende Angaben eines Eintrags ergänzen, nichts überschreiben (#345)')
    st.add_argument('project')
    st.add_argument('id', help='Eintrag, z. B. pr-007')
    st.add_argument('--time', help='HH:MM')
    st.add_argument('--commit')
    ls = sub.add_parser('list', help='Prüfungen je Kapitel anzeigen')
    ls.add_argument('project')
    ls.add_argument('--json', action='store_true')
    ls.add_argument('--language', default='de')
    bf = sub.add_parser('backfill', help='abgeschlossene Analyseläufe nachtragen')
    bf.add_argument('project')
    im = sub.add_parser('import', help='ältere Berichte unter analysis/ und editorial/ ohne Eintrag auflisten (#340)')
    im.add_argument('project')
    im.add_argument('--apply', action='store_true', help='erkannte Berichte eintragen (ohne Fingerabdruck)')
    im.add_argument('--only', action='append', metavar='BERICHT',
                    help='nur diesen Bericht (mehrfach möglich; Pfad relativ zum Buch oder Dateiname) (#347)')
    im.add_argument('--skip', action='append', metavar='BERICHT', help='diesen Bericht auslassen (mehrfach möglich)')
    im.add_argument('--kind', help='mit genau einem --only: Prüfart berichtigen')
    im.add_argument('--scope', action='append', help='mit genau einem --only: Umfang berichtigen (mehrfach möglich)')
    im.add_argument('--result', choices=RESULTS, help='mit genau einem --only: Ergebnis berichtigen')
    im.add_argument('--date', help='mit genau einem --only: Datum berichtigen')
    im.add_argument('--time', help='mit genau einem --only: Uhrzeit HH:MM berichtigen')
    im.add_argument('--json', action='store_true')
    args = ap.parse_args(argv)
    from render_view import load as load_project
    base, config = load_project(args.project)
    base = Path(base)
    if args.cmd == 'record':
        try:
            past = bool(args.date) and str(args.date) < datetime.date.today().isoformat() and not args.commit
            e = record(base, config, args.kind, args.scope, args.result, args.report, args.date, args.commit, args.note,
                       time=args.time, backfill=args.backfill or past, notes=args.notes)
        except ValueError as exc:
            print(exc, file=sys.stderr)
            return 1
        print(f'{e["id"]} eingetragen: {label(e["kind"])[0]}, {RESULT_TEXT["de"][e["result"]]}, {e["date"]}'
              + ('' if 'digests' in e else ' (nachgetragen, ohne Fingerabdruck: Stand unbekannt)'))
        return 0
    if args.cmd == 'set':
        try:
            done = complete(base, args.id, time=args.time, commit=args.commit)
        except ValueError as exc:
            print(exc, file=sys.stderr)
            return 1
        print(f'{args.id}: ' + (', '.join(done) + ' ergänzt.' if done else 'nichts zu ergänzen.'))
        return 0
    if args.cmd == 'backfill':
        added = backfill(base, config)
        print(f'{len(added)} Analyseläufe nachgetragen.')
        return 0
    if args.cmd == 'import':
        narrowed = bool(args.only or args.skip)
        timed = [] if args.apply or narrowed else missing_times(base, load(base))
        fix = {'kind': args.kind, 'scope': args.scope, 'result': args.result, 'date': args.date, 'time': args.time}
        if args.time and not re.fullmatch(r'([01]\d|2[0-3]):[0-5]\d', args.time):
            print(f'Uhrzeit nicht im Format HH:MM: {args.time}', file=sys.stderr)
            return 1
        try:
            found, added = import_reports(base, config, args.apply, args.only, args.skip, fix)
        except ValueError as exc:
            print(exc, file=sys.stderr)
            return 1
        for e, clock in timed:
            print(f'· {e["id"]}: Uhrzeit {clock} aus {e["report"]} ergänzbar (mit --apply)')
        if args.json:
            print(json.dumps({'candidates': found, 'added': added}, ensure_ascii=False, indent=1))
            return 0
        if not found:
            print('Keine Berichte ohne Eintrag.' + (' Uhrzeiten ergänzt, wo der Bericht eine nennt.' if args.apply else ''))
            return 0
        for c in found:
            what = label(c['kind'])[0] if c['kind'] else 'Prüfart ?'
            mark = '+' if c['ready'] and args.apply else ('·' if c['ready'] else '?')
            result = (RESULT_TEXT['de'][c['result']] if not c.get('results') else
                      'Ergebnis nicht eindeutig (' + ' / '.join(RESULT_TEXT['de'][r] for r in c['results']) + ')')
            print(f'{mark} {c["report"]}: {what}, {", ".join(c["scope"]) or "Umfang ?"}, {c["date"] or "Datum ?"}, '
                  f'{result}' + (' [berichtigt: ' + ', '.join(c['corrected']) + ']' if c.get('corrected') else ''))
        rest = [c for c in found if not c['ready']]
        if args.apply:
            print(f'{len(added)} Berichte nachgetragen.')
        else:
            print('Vorschlag. Bitte jede Zeile mit dem Bericht vergleichen: Eintragen mit --apply (nur vollständig '
                  'erkannte, ·); einzelne auslassen mit --skip <bericht>, nur einzelne mit --only <bericht>; '
                  'Umfang oder Ergebnis berichtigen mit --only <bericht> --scope … --result … (eingetragene Werte '
                  'lassen sich später nicht mehr ändern).')
        if rest:
            print(f'{len(rest)} Berichte nicht eindeutig (?): mit --only <bericht> und --scope/--result/--date berichtigen '
                  'oder mit record … --report <bericht> --date … von Hand nachtragen '
                  '(Datum vor heute: ohne Fingerabdruck, Stand unbekannt).')
        return 0
    idx = Index(base, config, args.language)
    rows = [{'chapter': ch['id'], 'title': ch['title'], 'tags': idx.chapter(ch)} for ch in config['structure']['chapters']]
    if args.json:
        print(json.dumps(rows, ensure_ascii=False, indent=1))
    else:
        for n, row in enumerate(rows, 1):
            print(f'{n}. {row["title"]}: {short_text(row["tags"])}')
        print(LEGEND.get(args.language, LEGEND['de']))
    return 0


if __name__ == '__main__':
    sys.exit(main())
