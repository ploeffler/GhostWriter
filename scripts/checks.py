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
           'timeline': 'Zeitleiste', 'continuity': 'Widersprüche', 'language': 'Sprache'},
    'en': {'characters': 'Characters', 'summaries': 'Summaries', 'style': 'Style', 'places': 'Places',
           'timeline': 'Timeline', 'continuity': 'Continuity', 'language': 'Language'},
}
ANALYSIS_SHORT = {'characters': 'AF', 'summaries': 'AK', 'style': 'ASt', 'places': 'AO', 'timeline': 'AZ',
                  'continuity': 'AW', 'language': 'ASp'}
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
           backfill=False):
    """Einen Prüflauf eintragen; Fingerabdrücke und Commit werden vom heutigen Stand genommen.

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
    commit = commit or (None if backfill else head_commit(base))
    if commit:
        entry['commit'] = commit
    if not backfill:
        entry['digests'] = digests(base, config, ids)
    elif not note:
        note = BACKFILL_NOTE
    if report:
        entry['report'] = str(report)
    if run:
        entry['run'] = run
    if note:
        entry['note'] = note
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


def _result_from(text):
    """Ergebnis nur aus einer ausdrücklichen Ergebniszeile („Ergebnis: …“, „Result: …“), sonst unknown."""
    lines = [l for l in text.splitlines() if re.search(r'(ergebnis|result|gesamturteil|urteil)\b', l, re.I)]
    for line in lines:
        low = line.lower()
        for res, pats in RESULT_WORDS:
            if any(re.search(p, low) for p in pats):
                return res
    return 'unknown'


def _scope_from(config, name, text):
    chapters = config['structure']['chapters']
    ids = {ch['id'] for ch in chapters} | {s['id'] for _, s in sections(config)}
    hay = name + '\n' + '\n'.join(text.splitlines()[:15])
    found = [i for i in sorted(ids, key=len, reverse=True) if re.search(rf'(?<![\w]){re.escape(i)}(?![\w]|-[^\W\d])', hay)]
    found = [i for i in found if not any(i != j and j.startswith(i + '-') for j in found)]
    if found:
        order = [ch['id'] for ch in chapters] + [s['id'] for _, s in sections(config)]
        return sorted(set(found), key=order.index)
    m = re.search(r'(?:kapitel|kap|chapter)[\s._-]*0*(\d+)', hay, re.I)
    if m and 1 <= int(m.group(1)) <= len(chapters):
        return [chapters[int(m.group(1)) - 1]['id']]
    if re.search(r'\b(gesamtes buch|ganzes buch|whole book|buchweit)\b', hay, re.I):
        return ['book']
    return []


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
        out.append({'report': rel, 'kind': kind, 'scope': scope, 'date': date, 'time': clock, 'result': _result_from(text),
                    'ready': bool(kind and scope and date)})
    return out


def import_reports(base, config, apply=False):
    """Kandidaten auflisten; mit apply=True die erkannten (ready) ohne Fingerabdruck eintragen.
    Ergebnisse werden nie erfunden: ohne Ergebniszeile bleibt `unknown`."""
    base = Path(base)
    entries = load(base)
    found = candidates(base, config, entries)
    added = []
    if apply:
        for c in found:
            if not c['ready']:
                continue
            entry = {'id': next_id(entries), 'kind': c['kind'], 'scope': c['scope'], 'date': c['date'],
                     **({'time': c['time']} if c.get('time') else {}),
                     'result': c['result'], 'report': c['report'],
                     'note': BACKFILL_NOTE}
            entries.append(entry)
            added.append(entry)
        timed = missing_times(base, entries)   # #345: Uhrzeit bestehender Einträge aus dem Bericht ergänzen
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
        out.append(localize({'CK_KIND': key, 'CK_RESULT': e['result'], 'CK_DATE': str(e.get('date') or ''), 'CK_WHEN': when(e),
                             'CK_REPORT': e.get('report') or '', 'CK_STATE': state(base, config, e, hit, now_digests),
                             'CK_PARTIAL': '1' if len(hit) < len(unit) else ''}, lang))
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


def history_json(items):
    """Widget: frühere Prüfungen kompakt als JSON; das Widget gruppiert nach CK_LABEL und zeigt je Eintrag CK_WHEN."""
    keep = ('CK_KIND', 'CK_LABEL', 'CK_WHEN', 'CK_DATE', 'CK_TAG', 'CK_MARK', 'CK_TEXT', 'CK_RESULT', 'CK_STATE', 'CK_REPORT')
    return json.dumps([{k: t.get(k, '') for k in keep} for t in items], ensure_ascii=False, separators=(',', ':'))


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


def as_json(tag_list):
    """Widget (ghostwriter-ui, data-gw-checks): kompakte JSON-Liste der Tags."""
    keep = ('CK_TAG', 'CK_PILL', 'CK_TEXT', 'CK_RESULT', 'CK_STATE', 'CK_REPORT')
    return json.dumps([{k: t.get(k, '') for k in keep} for t in tag_list], ensure_ascii=False, separators=(',', ':'))


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
            {s['id'] for _, s in sections(config)} | {i['id'] for i in matter(config)}
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
    im.add_argument('--json', action='store_true')
    args = ap.parse_args(argv)
    from render_view import load as load_project
    base, config = load_project(args.project)
    base = Path(base)
    if args.cmd == 'record':
        try:
            past = bool(args.date) and str(args.date) < datetime.date.today().isoformat() and not args.commit
            e = record(base, config, args.kind, args.scope, args.result, args.report, args.date, args.commit, args.note,
                       time=args.time, backfill=args.backfill or past)
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
        timed = [] if args.apply else missing_times(base, load(base))
        found, added = import_reports(base, config, args.apply)
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
            print(f'{mark} {c["report"]}: {what}, {", ".join(c["scope"]) or "Umfang ?"}, {c["date"] or "Datum ?"}, '
                  f'{RESULT_TEXT["de"][c["result"]]}')
        rest = [c for c in found if not c['ready']]
        if args.apply:
            print(f'{len(added)} Berichte nachgetragen.')
        else:
            print('Vorschlag. Eintragen mit --apply (nur vollständig erkannte, ·).')
        if rest:
            print(f'{len(rest)} Berichte nicht eindeutig (?): mit record … --report <bericht> --date … von Hand nachtragen '
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
