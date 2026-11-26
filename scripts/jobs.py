#!/usr/bin/env python3
"""Hintergrund-Warteschlange (#476, Teil 1 #480): Aufträge für KI-Arbeiten, die dauern und kosten.

Aufruf:
  python scripts/jobs.py <buch> list [--json]
  python scripts/jobs.py <buch> enqueue --type research --section <id> [--question Q] [--provider P]
                                        [--model M] [--confirm-low-budget] [--requested-by NAME]
                                        [--priority] [--after <auftrag>]
                                        [--not-before <zeitpunkt>] [--when budget_free] [--after-event <ereignis>]
  python scripts/jobs.py <buch> prioritize --request <auftrag>      (vorziehen, #478)
  python scripts/jobs.py <buch> suggest --section <id> [--question Q] [--json]   (Vorschlag vor dem Einreihen, #478)
  python scripts/jobs.py <buch> merge --request <auftrag> --question Q           (Zusammenlegen, #478)
  python scripts/jobs.py <buch> auto [--push-to <branch>]   (Analysen nach Kapitelabschluss einreihen, #123)
  python scripts/jobs.py <buch> cancel --request <auftrag>          (nur wartende Aufträge)
  python scripts/jobs.py <buch> enqueue --type chapter_review --field chapters=ch-03,ch-04|all   (Rundumprüfung, #531)
  python scripts/jobs.py <buch> complete --request <auftrag>        (Übergabe abschließen, wenn der Assistent die KI-Teile erledigt hat)
  python scripts/jobs.py <buch> process [--defaults datei] [--limit 5] [--push-to <arbeits-branch>]
  python scripts/jobs.py <ordner> remote [--start] [--paused] [--dry-run]   (Kontrolllauf, #481)
  python scripts/jobs.py <ordner> report [--json] [--language en]           (Wiedereinstieg, #484)

Auftrag (Schema schemas/job.schema.json): eine Datei `request-NNN.yml`.
- Recherche (`type: research`, Vorgabe, wenn `type` fehlt): am Abschnitt unter
  `<kapitel>/research/<abschnitt>/request-NNN.yml` bzw. `matter/research/<teil>/request-NNN.yml`,
  wie die Claude-Web-App sie schon anlegt. Felder der Art (`section_id`, `question`) stehen oben.
- Arten ohne Abschnitt (#479: Analyse, Colorieren, Import) liegen unter `jobs/request-NNN.yml`
  und tragen ihre Felder unter einem Schlüssel mit dem Namen der Art.
Gemeinsame Felder: `type`, `requested_at`, `requested_by`, `provider`, `model`,
`confirm_low_budget`; Zustand: `error` und `failed_at` (fehlgeschlagen, läuft nicht erneut),
`waiting: budget` (wartet auf Bestätigung, weil das KI-Budget unter der Schwelle ist).

Startbedingungen (#65, alle optional, mehrere kombinierbar: der Auftrag startet erst, wenn **alle** erfüllt sind):
`not_before` (ISO-Zeitpunkt, feste Zeit), `when: budget_free` (nur wenn das KI-Budget des Monats nicht unter der Pausenschwelle
liegt), `after_event` (`chapter_approved[:<kapitel>]`, `edition_created`, `material_added`; gemessen am Stand beim Einreihen,
`event_baseline`). Ein Auftrag mit offener Bedingung bleibt liegen (`start_wait`) und wird vom nächsten Lauf bzw. vom täglichen
Kontrolllauf gestartet, sobald alles erfüllt ist. Es gibt keine eigene zeitgesteuerte Action.

Rundumprüfung (`type: chapter_review`, #531): Weg „Übergabe“. Die Warteschlange hält Reihenfolge, Startbedingungen und Status; sie führt nur
Prüfungen ohne KI aus (Verfügbarkeit, Freigaben, Veraltet-Markierungen, Sprachanalyse mit KI-Mustern) und schreibt das Ergebnis unter
`handover` in den Auftrag (Zustand `handover`, kein Budget nötig). Die KI-Teile arbeitet der Assistent beim nächsten Einstieg ab
(`report` meldet sie); `complete` entfernt den Auftrag danach. Keine KI-Pipeline in der Action, keine Freigabe.

Reihenfolge (#478), in dieser Rangfolge: Vorrang (`priority: true`, „vorziehen“), Abhängigkeit
(`after: <Auftrag>`: der Auftrag wartet, bis der genannte erledigt oder fehlgeschlagen ist;
Ringe werden ignoriert und gemeldet), Buchreihenfolge (Kapitel, Abschnitt; Vor- und Nachspann
danach), `requested_at`, Dateipfad. Die KI sortiert nicht um. Vor dem Einreihen prüft `suggest` einmal gegen die
wartenden Recherchen und bietet „Danach einreihen“ (`--after`), „Zusammenlegen“ (`merge`) oder „Unabhängig“ an; es
ändert nichts, erst die Wahl des Benutzers legt etwas an. Je Auftrag: Budget prüfen (darunter `waiting: budget`, außer
`confirm_low_budget`), ausführen, Ergebnis committen und pushen (`--push-to`). Ein Fehler
stoppt die Warteschlange nicht. `--limit` begrenzt die Aufträge je Lauf; `remaining` nennt,
wie viele danach noch offen sind (die Action startet sich dann selbst neu).
"""
import argparse
import datetime
import json
import os
import re
import subprocess
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'scripts'))
import research  # noqa: E402

TYPES = ('research', 'analysis', 'colorize', 'import', 'chapter_review')
# Felder je Art (Eingaben der bisherigen Actions, #479); sie stehen unter dem Namen der Art
FIELDS = {'analysis': ('kind', 'scope', 'prompt_profile'),
          'colorize': ('folder', 'consent', 'model', 'replace', 'hint', 'minors_exception'),
          'import': ('step', 'file', 'ops', 'writing_approval', 'by', 'prompt_profile'),
          'chapter_review': ('chapters',)}
# Workflow, der eine Art abarbeitet, und der Branch, auf den das Ergebnis kommt
WORKFLOW = {'research': 'research.yml', 'analysis': 'analyse.yml', 'colorize': 'colorize.yml', 'import': 'import.yml',
            'chapter_review': 'analyse.yml'}
TARGET = {'research': 'work', 'colorize': 'work', 'analysis': 'book', 'import': 'book', 'chapter_review': 'book'}
# Arten bzw. Schritte ohne KI-Kosten: keine Budgetprüfung
FREE = {('import', 'convert'), ('import', 'edit'), ('import', 'apply'), ('chapter_review', '')}   # Rundumprüfung (#531): nur Prüfungen ohne KI
REQUEST_RE = research.REQUEST_RE
LIMIT = 5
COMMIT_PATHS = ('chapters', 'matter', 'jobs')


def now_utc():
    return datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0)


def read(path):
    try:
        data = yaml.safe_load(Path(path).read_text(encoding='utf-8'))
    except (OSError, yaml.YAMLError):
        return None
    return data if isinstance(data, dict) else None


def write(path, data):
    Path(path).write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False), encoding='utf-8')


def files(base):
    base = Path(base)
    found = sorted(base.glob('chapters/*/research/*/request-*.yml')) + sorted(base.glob('matter/research/*/request-*.yml')) \
        + sorted(base.glob('jobs/request-*.yml'))
    return [p for p in found if REQUEST_RE.match(p.name)]


def kind(job):
    return job.get('type') or 'research'


def state(job):
    """open | waiting_budget | failed | handover (Rundumprüfung vorbereitet, KI-Teile beim nächsten Einstieg, #531)"""
    if job.get('error'):
        return 'failed'
    if job.get('handover'):
        return 'handover'
    if job.get('waiting') == 'budget' and not job.get('confirm_low_budget'):
        return 'waiting_budget'
    return 'open'


def book_order(config):
    """section_id → Rangfolge nach der Gliederung; Vor- und Nachspann hinter den Kapiteln."""
    order = {}
    structure = (config or {}).get('structure') or {}
    for c, chapter in enumerate(structure.get('chapters') or []):
        for s, section in enumerate(chapter.get('sections') or []):
            order[section.get('id')] = (1, c, s)
    for g, group in enumerate(('front_matter', 'back_matter')):
        for i, part in enumerate(structure.get(group) or []):
            order[part.get('id')] = (2 + g, 0, i)
    return order


def pending(job):
    """Auftrag ist noch nicht erledigt und nicht gescheitert (wartet oder wartet auf Bestätigung)."""
    return job['state'] in ('open', 'waiting_budget')


def resolve_after(out, base):
    """`after` auflösen (#478): Ziel je Auftrag, Ringe und fehlende Ziele.
    Ein Ring wird ignoriert und gemeldet (`problem`). Ein fehlendes Ziel ist meist ein erledigter Auftrag (die
    Datei verschwindet beim Erledigen); es blockiert nicht und wird nur als `note` vermerkt."""
    by_rel = {}
    for j in out:
        j['rel'] = str(j['path'].relative_to(base))
        by_rel[j['rel']] = j
    for j in out:
        j['after_job'] = None
        after = str(j['data'].get('after') or '').strip()
        if not after:
            continue
        rel = after if after in by_rel else str(Path(j['rel']).parent / (after if after.endswith('.yml') else after + '.yml'))
        target = by_rel.get(rel)
        if target is None or target is j:
            j['note'] = f'Ziel von „after“ nicht mehr vorhanden: {after}'
        else:
            j['after_job'] = target
    for j in out:   # Ringe: wer über `after` wieder bei sich ankommt
        seen, k = set(), j
        while k is not None and id(k) not in seen:
            seen.add(id(k))
            k = k['after_job']
        if k is j:
            members = [m for m in out if id(m) in seen]
            for m in members:
                m['problem'] = 'Ring bei „after“ ignoriert'
            for m in members:
                m['after_job'] = None
    for j in out:
        t = j['after_job']
        j['blocked_by'] = t['rel'] if t is not None and pending(t) else None


def locked_by(base, config, section_id):
    """Der aktive Checkout, der den Abschnitt sperrt (#572), sonst None. Ohne checkouts.yml oder ohne Abschnitt: None."""
    if not section_id or not Path(base, 'checkouts.yml').is_file():
        return None
    try:
        import checkout
        return checkout.locked_by_checkout(Path(base), config, section_id)
    except Exception:   # noqa: BLE001 – eine unlesbare Sperrdatei hält die Warteschlange nicht an
        return None


EVENTS = ('chapter_approved', 'edition_created', 'material_added')


def event_baseline(base, config=None):
    """Stand der Ereignis-Quellen beim Einreihen: Auflagenzähler und Zahl des eingebrachten Materials."""
    base = Path(base)
    config = config if config is not None else (read(base / 'ghostwriter.yml') or {})
    return {'edition': int((config.get('project') or {}).get('current_edition') or 0),
            'material': len(list(base.glob('quellen/*/material.yml')))}


def _when(value):
    try:
        t = datetime.datetime.fromisoformat(str(value).replace('Z', '+00:00'))
    except ValueError:
        return None
    return t if t.tzinfo else t.replace(tzinfo=datetime.timezone.utc)


def start_wait(base, config, data, now=None, low=None):
    """Offene Startbedingungen eines Auftrags (#65) als Text, leer = darf starten. Geprüft werden `not_before`,
    `when: budget_free` und `after_event`; alle müssen erfüllt sein. Eine unlesbare Angabe blockiert nicht dauerhaft."""
    now = now or now_utc()
    waits = []
    nb = data.get('not_before')
    if nb and (_when(nb) or now) > now:
        waits.append(f'nicht vor {nb}')
    when = data.get('when')
    if when == 'budget_free' or (isinstance(when, list) and 'budget_free' in when):
        if (low or budget_low)(base):
            waits.append('wartet auf freies KI-Budget')
    event = str(data.get('after_event') or '').strip()
    if event:
        name, _, target = event.partition(':')
        done = True
        if name == 'chapter_approved':
            since = _when(data.get('requested_at'))
            entries = (read(Path(base) / 'approvals.yml') or {}).get('entries') or []
            done = any(e.get('kind') == 'chapter' and e.get('action') == 'granted' and (not target or e.get('id') == target)
                       and (since is None or (_when(e.get('at')) or since) > since) for e in entries)
        elif name in ('edition_created', 'material_added'):
            key = 'edition' if name == 'edition_created' else 'material'
            baseline = (data.get('event_baseline') or {}).get(key)   # fehlt (von Hand geschrieben): gilt als erfüllt
            done = baseline is None or event_baseline(base, config)[key] > int(baseline)
        if not done:
            waits.append('wartet auf Ereignis: ' + {'chapter_approved': 'Kapitel abgeschlossen' + (f' ({target})' if target else ''),
                                                    'edition_created': 'Auflage erzeugt', 'material_added': 'Material eingebracht'}.get(name, event))
    return '; '.join(waits)


def jobs(base, config=None, now=None):
    """Alle Aufträge mit Pfad, Daten und Zustand, in Abarbeitungsreihenfolge (#478): Vorrang, dann Buchreihenfolge,
    dann Auftragszeit; ein Auftrag mit `after` steht stets hinter seinem Ziel."""
    base = Path(base)
    config = config if config is not None else (read(base / 'ghostwriter.yml') or {})
    order = book_order(config)
    out = []
    known = {}

    def cache_low(b):   # Budgetprüfung höchstens einmal je Aufruf
        if 'low' not in known:
            known['low'] = budget_low(b, config)
        return known['low']
    for path in files(base):
        data = read(path)
        if data is None:
            out.append({'path': path, 'data': {}, 'state': 'failed', 'rank': (1, 9), 'error': 'Auftrag nicht lesbar'})
            continue
        sid = str(data.get('section_id') or (path.parent.name if 'research' in path.parts else ''))
        rank = (0 if data.get('priority') is True else 1,) + order.get(sid, (8, 0, 0)) \
            + (str(data.get('requested_at') or ''), str(path.relative_to(base)))
        out.append({'path': path, 'data': data, 'state': state(data), 'rank': rank, 'section_id': sid, 'type': kind(data)})
        wait = start_wait(base, config, data, now, low=cache_low) if pending(out[-1]) else ''
        if wait:   # #65: Startbedingung offen; der Auftrag bleibt liegen
            out[-1]['start_wait'] = wait
        lock = locked_by(base, config, sid)
        if lock:   # #572: Abschnitt ist zum Gegenlesen ausgecheckt: der Auftrag wartet, bis der Checkout beendet ist
            out[-1]['locked_by'] = lock['id']
    out.sort(key=lambda j: j['rank'])
    resolve_after(out, base)
    ordered, seen = [], set()

    def emit(j):
        if id(j) in seen:
            return
        seen.add(id(j))
        if j.get('after_job') is not None:
            emit(j['after_job'])
        ordered.append(j)
    for j in out:
        emit(j)
    return ordered


def queue(base, config=None, types=None, now=None):
    """Aufträge, die jetzt ausgeführt werden dürfen: offen, nicht von einem noch offenen Auftrag abhängig und mit
    erfüllten Startbedingungen (#65)."""
    return [j for j in jobs(base, config, now) if j['state'] == 'open' and not j.get('blocked_by') and not j.get('locked_by')
            and not j.get('start_wait') and (not types or j['type'] in types)]


def find(base, request):
    """Auftrag nach Pfad (relativ zum Buch) oder Dateiname; ValueError, wenn nicht eindeutig gefunden."""
    request = str(request).strip().replace('\\', '/')
    hits = [j for j in jobs(base) if j['rel'] == request or j['path'].name == request or j['path'].stem == request]
    if len(hits) != 1:
        raise ValueError(f'Auftrag nicht eindeutig gefunden: {request}' if hits else f'Auftrag nicht gefunden: {request}')
    return hits[0]


def prioritize(base, request):
    """Vorziehen: `priority: true` setzen. Nur wartende Aufträge; Pfad relativ zum Buch."""
    job = find(base, request)
    if not pending(job):
        raise ValueError('Vorziehen geht nur bei wartenden Aufträgen.')
    job['data']['priority'] = True
    write(job['path'], job['data'])
    return job['path']


def retry(base, request):
    """Erneut versuchen (#554): `error` und `failed_at` entfernen, der Auftrag ist wieder offen. Kein zweiter Auftrag.
    Nur fehlgeschlagene Aufträge; Frage, Modell und Anbieter bleiben, wie sie sind."""
    job = find(base, request)
    if job['state'] != 'failed':
        raise ValueError('Erneut versuchen geht nur bei fehlgeschlagenen Aufträgen.')
    for key in ('error', 'failed_at'):
        job['data'].pop(key, None)
    write(job['path'], job['data'])
    return job['path']


def cancel(base, request):
    """Abbrechen: den Auftrag entfernen. Nur wartende Aufträge; ein bereits laufender lässt sich so nicht stoppen."""
    job = find(base, request)
    if not pending(job) and job['state'] != 'handover':
        raise ValueError('Abbrechen geht nur bei wartenden Aufträgen.')
    job['path'].unlink()
    return job['path']


def complete(base, request):
    """Übergabe abschließen (#531): der Assistent hat die KI-Teile einer Rundumprüfung erledigt; der Auftrag wird entfernt.
    Nur bei Aufträgen im Zustand Übergabe."""
    job = find(base, request)
    if job['state'] != 'handover':
        raise ValueError('Abschließen geht nur bei Aufträgen, die auf die KI-Teile im Chat warten.')
    job['path'].unlink()
    return job['path']


def section_path(base, config, section_id):
    ch, sec, _, _ = research.find_section(base, config, section_id)
    return Path(base) / ch['path'] / 'research' / sec['id']


def suggest(base, section, question=None, type_='research'):
    """Vorschlag vor dem Einreihen (#478). Prüft einmal gegen die wartenden Recherchen und ändert nichts.
    Beziehungen: `same_section` (gleicher Abschnitt: Zusammenlegen oder danach einreihen) und `same_chapter`
    (anderer Abschnitt desselben Kapitels: danach einreihen, damit der neue Auftrag die schon erledigte Recherche als
    Vorwissen bekommt). Empfehlung: `merge` bei gleichem Abschnitt, `after` bei gleichem Kapitel, sonst `independent`.
    Ein Auftrag in Prüfung (`locked_by`) oder mit Fehler steht nicht zur Wahl."""
    base = Path(base)
    config = read(base / 'ghostwriter.yml') or {}
    if type_ != 'research':
        return {'recommended': 'independent', 'candidates': [], 'options': ['independent']}
    chapter_of = {}
    for ch in (config.get('structure') or {}).get('chapters') or []:
        for sec in ch.get('sections') or []:
            chapter_of[sec.get('id')] = ch.get('id')
    mine = chapter_of.get(section)
    candidates = []
    for j in jobs(base, config):
        if j['type'] != 'research' or not pending(j) or j.get('locked_by'):
            continue
        sid = j.get('section_id', '')
        relation = 'same_section' if sid == section else 'same_chapter' if mine and chapter_of.get(sid) == mine else None
        if relation:
            d = j['data']
            candidates.append({'request': j['rel'], 'relation': relation, 'section_id': sid, 'question': d.get('question') or '',
                               'state': j['state'], 'requested_at': str(d.get('requested_at') or '')})
    # gleicher Abschnitt zuerst, dann der zuletzt eingereihte (er läuft am spätesten)
    candidates.sort(key=lambda c: c['requested_at'], reverse=True)
    candidates.sort(key=lambda c: c['relation'] != 'same_section')   # stabil: bleibt je Gruppe neueste zuerst
    options = ['independent']
    recommended = 'independent'
    if candidates:
        options = ['after', 'independent']
        recommended = 'after'
        if any(c['relation'] == 'same_section' for c in candidates):
            options = ['merge', 'after', 'independent']
            recommended = 'merge'
    return {'section_id': section, 'question': question or '', 'recommended': recommended, 'options': options,
            'candidates': candidates}


def merge(base, request, question=None):
    """Zusammenlegen (#478): die Frage in einen wartenden Auftrag desselben Abschnitts übernehmen, statt einen zweiten
    anzulegen. Nur wartende Recherchen; eine schon vorhandene Frage bleibt stehen, die neue folgt als eigener Absatz."""
    job = find(base, request)
    if job['type'] != 'research':
        raise ValueError('Zusammenlegen geht nur bei Recherchen.')
    if not pending(job):
        raise ValueError('Zusammenlegen geht nur bei wartenden Aufträgen.')
    question = (question or '').strip()
    if not question:
        raise ValueError('Zum Zusammenlegen die Frage angeben (--question).')
    old = str(job['data'].get('question') or '').strip()
    if question not in old:
        job['data']['question'] = f'{old}\n\n{question}' if old else question
        write(job['path'], job['data'])
    return job['path']


def enqueue(base, type_='research', section=None, question=None, provider=None, model=None,
            confirm_low_budget=False, requested_by=None, now=None, fields=None, priority=False, after=None,
            not_before=None, when=None, after_event=None):
    """Auftrag anlegen; einziger Weg, eine Arbeit in die Warteschlange zu stellen. Gibt den Pfad zurück.
    Recherche am Abschnitt; andere Arten unter jobs/ mit ihren Feldern (`fields`) unter dem Namen der Art."""
    if type_ not in TYPES:
        raise ValueError(f'Unbekannte Art: {type_}')
    base = Path(base)
    start = {}   # Startbedingungen (#65)
    if not_before:
        if _when(not_before) is None:
            raise ValueError(f'--not-before braucht einen Zeitpunkt (ISO 8601), nicht: {not_before}')
        start['not_before'] = str(not_before)
    if when:
        if when != 'budget_free':
            raise ValueError('--when kennt nur budget_free.')
        start['when'] = when
    if after_event:
        if str(after_event).partition(':')[0] not in EVENTS:
            raise ValueError(f'--after-event: {", ".join(EVENTS)} (chapter_approved optional mit :<kapitel>)')
        start['after_event'] = after_event
        start['event_baseline'] = event_baseline(base)
    if type_ != 'research':
        folder = base / 'jobs'
        folder.mkdir(parents=True, exist_ok=True)
        n = research.next_number(folder, REQUEST_RE)
        data = {'type': type_, 'requested_at': (now or now_utc()).isoformat(), 'requested_by': requested_by or 'chat'}
        if model:
            data['model'] = model
        if confirm_low_budget:
            data['confirm_low_budget'] = True
        if priority:
            data['priority'] = True
        if after:
            data['after'] = after
        data.update(start)
        data[type_] = {k: v for k, v in (fields or {}).items() if k in FIELDS[type_] and v not in (None, '')}
        path = folder / f'request-{n:03d}.yml'
        write(path, data)
        return path
    config = read(base / 'ghostwriter.yml') or {}
    if not section:
        raise ValueError('Für eine Recherche den Abschnitt angeben (--section).')
    folder = section_path(base, config, section)
    folder.mkdir(parents=True, exist_ok=True)
    n = research.next_number(folder, REQUEST_RE)
    data = {'type': type_, 'section_id': section,
            'requested_at': (now or now_utc()).isoformat(), 'requested_by': requested_by or 'chat'}
    for key, value in (('question', question), ('provider', provider), ('model', model)):
        if value:
            data[key] = value
    if confirm_low_budget:
        data['confirm_low_budget'] = True
    if priority:
        data['priority'] = True
    if after:
        data['after'] = after
    data.update(start)
    path = folder / f'request-{n:03d}.yml'
    write(path, data)
    return path


def auto_analysis(base, now=None):
    """Analysen nach einem Kapitelabschluss einreihen (#123), wenn das Buch es wünscht
    (`analysis.auto_after_chapter: [characters, …]` in ghostwriter.yml). Je Art ein Auftrag für das ganze Buch,
    sobald ein Kapitel nach dem letzten Lauf der Art abgeschlossen wurde und kein Auftrag der Art mehr wartet; gelesen
    wird dann nur, was sich seit dem letzten Lauf geändert hat (Fingerabdruck). Gibt die angelegten Aufträge zurück."""
    import analyze
    base = Path(base)
    config = read(base / 'ghostwriter.yml') or {}
    kinds = [k for k in (config.get('analysis') or {}).get('auto_after_chapter') or [] if k in analyze.KINDS]
    entries = (read(base / 'approvals.yml') or {}).get('entries') or []
    approved = [t for t in (_when(e.get('at')) for e in entries
                            if e.get('kind') == 'chapter' and e.get('action') == 'granted') if t]
    if not kinds or not approved:
        return []
    latest = max(approved)
    waiting = {str((j['data'].get('analysis') or {}).get('kind') or 'characters') for j in jobs(base, config)
               if j['type'] == 'analysis' and pending(j)}
    made = []
    for kind in kinds:
        if kind in waiting:
            continue
        runs = [t for t in (_when(json.loads(p.read_text(encoding='utf-8')).get('created_at'))
                            for p in sorted((base / 'analysis' / kind).glob('run-[0-9][0-9][0-9].json'))) if t]
        if runs and max(runs) >= latest:
            continue
        made.append(enqueue(base, 'analysis', fields={'kind': kind, 'scope': 'book'}, requested_by='auto', now=now))
    return made


def budget_low(base, config=None):
    """True, wenn das KI-Budget unter der Pausenschwelle liegt (limits.py)."""
    try:
        import limits
        config = config if config is not None else (read(Path(base) / 'ghostwriter.yml') or {})
        return any(r['key'] == 'ai_budget' and r['state'] == 'pause' for r in limits.evaluate(Path(base), config))
    except Exception:   # noqa: BLE001 – ohne Kostendaten kein Halt
        return False


def git(base, *args, check=True):
    r = subprocess.run(['git', *args], cwd=base, capture_output=True, text=True)
    if check and r.returncode:
        raise RuntimeError(f'git {args[0]}: {(r.stderr or r.stdout).strip()[:300]}')
    return r


def commit_push(base, message, branch=None, tries=3, paths=None, action='jobs.process'):
    """Ergebnis eines Auftrags speichern; mit branch auch hochladen (Rebase bei neuerem Stand).
    paths: zusätzlich zu chapters, matter, jobs (je Art, z. B. analysis, costs/project.yml); '*' = alles."""
    if paths == '*':
        git(base, 'add', '-A')
    else:
        found = [p for p in list(COMMIT_PATHS) + list(paths or []) if (Path(base) / p).exists()]
        if found:
            git(base, 'add', '-A', '--', *found)
    if git(base, 'diff', '--cached', '--quiet', check=False).returncode == 0:
        return False
    git(base, 'commit', '-q', '-m', message, '-m', f'GhostWriter-Aktion: {action}')
    if not branch:
        return True
    for _ in range(tries):
        if git(base, 'push', '-q', 'origin', f'HEAD:refs/heads/{branch}', check=False).returncode == 0:
            return True
        git(base, 'fetch', '-q', 'origin', branch, check=False)
        if git(base, 'rebase', '-q', '--autostash', f'origin/{branch}', check=False).returncode:
            git(base, 'rebase', '--abort', check=False)
            break
    raise RuntimeError(f'Ergebnis konnte nicht auf {branch} gespeichert werden.')


def script(base, name, *args, env=None):
    """Bestehendes Skript des Buchs ausführen; Ausgabe zurück, Fehler als ResearchError (Auftrag fehlgeschlagen)."""
    r = subprocess.run([sys.executable, str(Path(base) / 'scripts' / name), '.', *args], cwd=base, capture_output=True,
                       text=True, env=dict(os.environ, **(env or {})))
    out = (r.stdout or '') + (r.stderr or '')
    if r.returncode:
        lines = [l.replace('::error::', '') for l in out.strip().splitlines() if l.strip()]
        raise research.ResearchError((lines[-1] if lines else f'{name} fehlgeschlagen')[:300])
    return out


def run_colorize(base, job):
    f = job['data'].get('colorize') or {}
    folder = str(f.get('folder') or '')
    if not folder:
        raise research.ResearchError('Kein Bildordner (folder) im Auftrag.')
    check = ['--check'] + (['--minors-exception'] if f.get('minors_exception') else [])
    script(base, 'colorize.py', folder, *check)
    if not f.get('consent'):
        raise research.ResearchError('Ohne Einverständnis (consent) geht kein Bild an Google.')
    if not os.environ.get('GEMINI_API_KEY'):
        raise research.ResearchError('Kein Schlüssel: Secret GEMINI_API_KEY hinterlegen (docs/DIENSTE-NUTZEN.md).')
    args = ['--consent'] + (['--model', f['model']] if f.get('model') else []) + (['--replace'] if f.get('replace') else []) \
        + (['--hint', f['hint']] if f.get('hint') else []) + (['--minors-exception'] if f.get('minors_exception') else [])
    script(base, 'colorize.py', folder, *args)
    return {'label': f'Bild coloriert: {Path(folder).name}', 'paths': [folder, 'costs/project.yml'], 'action': 'image.colorize'}


def run_analysis(base, job):
    f = job['data'].get('analysis') or {}
    kind, scope = str(f.get('kind') or 'characters'), str(f.get('scope') or 'book')
    env = {'GHOSTWRITER_PROMPT_PROFILE': '1' if f.get('prompt_profile') else '0'}
    script(base, 'analyze.py', 'plan', '--kind', kind, '--scope', scope)
    script(base, 'analyze.py', 'run', '--kind', kind, '--scope', scope, env=env)
    return {'label': f'Analyse im Hintergrund: {kind} ({scope})', 'paths': ['analysis', 'costs/project.yml'], 'action': 'analysis.start'}


def run_import(base, job):
    f = job['data'].get('import') or {}
    step = str(f.get('step') or 'convert')
    env = {'GHOSTWRITER_PROMPT_PROFILE': '1' if f.get('prompt_profile') else '0'}
    if step == 'convert':
        script(base, 'import_book.py', 'convert', str(f.get('file') or ''))
        label = 'Manuskript umgewandelt: Vorschlag für die Gliederung'
    elif step == 'edit':
        ops = f.get('ops') if isinstance(f.get('ops'), str) else json.dumps(f.get('ops') or [], ensure_ascii=False)
        script(base, 'import_book.py', 'edit', ops)
        label = 'Import: Gliederung geändert'
    elif step == 'outline':
        if not (os.environ.get('ANTHROPIC_API_KEY') or os.environ.get('OPENAI_API_KEY')):
            raise research.ResearchError('Kein KI-Schlüssel: Secret ANTHROPIC_API_KEY oder OPENAI_API_KEY hinterlegen.')
        script(base, 'import_book.py', 'outline', '--plan')
        script(base, 'import_book.py', 'outline', env=env)
        label = 'Import: KI-Vorschlag für die Gliederung'
    elif step == 'apply':
        args = ['apply']
        if f.get('writing_approval'):
            args += ['--writing-approval', '--by', str(f.get('by') or 'chat'), '--commit', git(base, 'rev-parse', 'HEAD').stdout.strip()]
        script(base, 'import_book.py', *args)
        script(base, 'validate_project.py')
        label = 'Manuskript importiert'
    else:
        raise research.ResearchError(f'Unbekannter Import-Schritt: {step}')
    return {'label': label, 'paths': '*', 'step': step, 'action': f'import.{step}'}


AI_STEPS = ('structure', 'language', 'proofreading', 'rules', 'story_memory')   # Prüfarten, die der Assistent beim Einstieg erledigt


def review_chapters(config, wanted):
    """Kapitel einer Rundumprüfung in Buchreihenfolge: [(Nummer, Kapitel)]. `wanted`: Liste oder Text mit Komma,
    Kapitel-IDs oder Nummern; leer oder `all` = alle."""
    chapters = ((config or {}).get('structure') or {}).get('chapters') or []
    if isinstance(wanted, str):
        wanted = [w.strip() for w in wanted.split(',') if w.strip()]
    wanted = [str(w) for w in (wanted or [])]
    if not wanted or 'all' in wanted:
        return list(enumerate(chapters, 1))
    numbers, missing = set(), []
    for w in wanted:
        hit = next((n for n, c in enumerate(chapters, 1) if c.get('id') == w or str(n) == w), None)
        if hit:
            numbers.add(hit)
        else:
            missing.append(w)
    if missing:
        raise research.ResearchError('Kapitel nicht gefunden: ' + ', '.join(missing))
    return [(n, chapters[n - 1]) for n in sorted(numbers)]


def run_chapter_review(base, job):
    """Rundumprüfung als Übergabe (#531, Entscheidung Peter 26.11.2026): nur Prüfungen ohne KI laufen hier (Verfügbarkeit,
    Freigaben und Veraltet-Markierungen, Sprachanalyse ohne KI mit KI-Mustern). Das Ergebnis steht im Auftrag unter `handover`;
    die KI-Teile arbeitet der Assistent beim nächsten Einstieg ab (`jobs.py … complete`). Keine KI-Pipeline, keine Freigabe."""
    import chapter_revision
    from render_view import section_file
    base = Path(base)
    config = read(base / 'ghostwriter.yml') or {}
    f = job['data'].get('chapter_review') or {}
    rows = []
    approvals = (read(base / 'approvals.yml') or {}).get('entries') or []
    for number, chapter in review_chapters(config, f.get('chapters')):
        ready = chapter_revision.readiness(base, chapter)
        approved, stale = 0, []
        for section in chapter.get('sections') or []:
            try:
                head = section_file(base, section)[0]
            except Exception:   # noqa: BLE001 – unlesbarer Abschnitt steht schon in `ready`
                continue
            if (head.get('approvals') or {}).get('section') is True:
                approved += 1
            if head.get('stale'):
                stale.append(section['id'])
        closed = False
        for e in approvals:   # letzter Eintrag zum Kapitel entscheidet
            if e.get('kind') == 'chapter' and e.get('id') == chapter['id']:
                closed = e.get('action') == 'granted'
        row = {'id': chapter['id'], 'number': number, 'title': chapter.get('title') or '', 'ready': ready['ready'],
               'issues': ready['issues'], 'sections': len(chapter.get('sections') or []), 'sections_approved': approved,
               'stale': stale, 'chapter_approved': closed, 'language_run': '', 'ai_steps': []}
        if ready['ready']:
            folder = base / 'analysis' / 'language'
            before = {p.name for p in folder.glob('run-*.json')} if folder.is_dir() else set()
            script(base, 'analyze.py', 'run', '--kind', 'language', '--scope', str(number))
            new = sorted({p.name for p in folder.glob('run-*.json')} - before)
            row['language_run'] = new[-1] if new else ''
            row['ai_steps'] = list(AI_STEPS)
        rows.append(row)
    job['data']['handover'] = {'prepared_at': now_utc().isoformat(), 'commit': git(base, 'rev-parse', 'HEAD', check=False).stdout.strip(),
                               'chapters': rows,
                               'note': 'Offen für den Assistenten: ' + ', '.join(AI_STEPS) + ' (Ablauf docs/LEKTORAT.md, Rundumprüfung). '
                                       'Nach der Bearbeitung `jobs.py . complete --request <auftrag>`.'}
    write(job['path'], job['data'])
    ok = sum(1 for r in rows if r['ready'])
    return {'label': f'Rundumprüfung vorbereitet: {ok} von {len(rows)} Kapiteln, KI-Teile beim nächsten Einstieg', 'keep': True,
            'paths': ['analysis', 'story', 'editorial', 'costs/project.yml'], 'action': 'chapter_review.prepare'}


RUNNERS = {'colorize': run_colorize, 'analysis': run_analysis, 'import': run_import, 'chapter_review': run_chapter_review}


def run_job(base, job, defaults, now):
    data = job['data']
    if job['type'] in RUNNERS:
        res = RUNNERS[job['type']](base, job)
        if not res.pop('keep', False):   # Übergabe (#531): der Auftrag bleibt, bis der Assistent ihn abschließt
            job['path'].unlink()
        return dict(res, ok=True)
    if job['type'] == 'research':
        head = research.run(base, job['section_id'], data.get('question'), data.get('provider'), data.get('model'),
                            defaults, now, request=job['path'].stem)
        job['path'].unlink()
        for old in job['path'].parent.glob('request-*.yml'):   # ältere fehlgeschlagene desselben Abschnitts
            if REQUEST_RE.match(old.name) and (read(old) or {}).get('error'):
                old.unlink()
        return {'ok': True, 'run': head['path'], 'searches': head['searches'], 'sources': head['sources'],
                'cost': head['cost'], 'label': f'Recherche {head["number"]}'}
    raise research.ResearchError(f'Art {job["type"]} wird noch nicht abgearbeitet.')


def process(base, defaults=None, limit=LIMIT, push_to=None, commit=True, now=None, low=None, types=None):
    """Bis zu `limit` offene Aufträge (der Arten `types`, sonst aller) abarbeiten. Gibt (Ergebnisse, noch offen) zurück."""
    base = Path(base)
    config = read(base / 'ghostwriter.yml') or {}
    results = []
    for _ in range(limit):
        ready = queue(base, config, types, now)   # jedes Mal neu: ein erledigter Auftrag gibt abhängige frei (#478)
        if not ready:
            break
        job = ready[0]
        rel = str(job['path'].relative_to(base))
        stamp = (now or now_utc()).isoformat()
        free = (job['type'], str((job['data'].get(job['type']) or {}).get('step') or '')) in FREE
        is_low = False if free else (low(base) if low else budget_low(base, config))
        paths, action = None, 'jobs.process'
        if is_low and not job['data'].get('confirm_low_budget'):
            job['data']['waiting'] = 'budget'
            write(job['path'], job['data'])
            results.append({'request': rel, 'ok': False, 'waiting': True,
                            'error': 'Wartet auf Bestätigung: weniger KI-Budget übrig als die Schwelle.'})
            message = f'Warteschlange: {rel} wartet auf Bestätigung (Budget)'
        else:
            try:
                res = run_job(base, job, defaults, now)
                paths = res.pop('paths', None)
                action = res.pop('action', 'research.web' if job['type'] == 'research' else 'jobs.process')
                results.append(dict(res, request=rel))
                message = f'{res["label"]} aus der Warteschlange gespeichert'
            except research.ResearchError as e:
                error = str(e)
            except Exception as e:   # noqa: BLE001 – ein Fehler stoppt die Warteschlange nicht
                error = f'Unerwarteter Fehler ({type(e).__name__}). Auftrag bleibt liegen.'
            else:
                error = None
            if error:
                if commit and job['type'] in RUNNERS:
                    # Halbfertiges eines abgebrochenen Skripts nicht in den nächsten Auftrag mitnehmen
                    git(base, 'reset', '-q', '--hard', 'HEAD', check=False)
                    git(base, 'clean', '-fdq', check=False)
                job['data'].update({'error': error, 'failed_at': stamp})
                job['data'].pop('waiting', None)
                write(job['path'], job['data'])
                results.append({'request': rel, 'ok': False, 'error': error})
                message = f'Warteschlange: {rel} fehlgeschlagen'
        if commit:
            commit_push(base, message, push_to, paths=paths, action=action)
    return results, len(queue(base, config, types, now))


def summary(results, remaining=0):
    lines = []
    for r in results:
        if r['ok'] and 'run' not in r:
            lines.append(f'- {r["label"]}')
        elif r['ok']:
            cost = 'Kosten ohne Preisangabe' if r.get('cost') is None else f'etwa {r["cost"]:.4f}'.replace('.', ',')
            lines.append(f'- {r["label"]} gespeichert: {r["run"]} ({r["searches"]} Suchanfragen, {r["sources"]} Quellen, {cost})')
        elif r.get('waiting'):
            lines.append(f'- Wartet ({r["request"]}): {r["error"]}')
        else:
            lines.append(f'- Fehlgeschlagen ({r["request"]}): {r["error"]}')
    if not results:
        lines.append('- Keine offenen Aufträge.')
    if remaining:
        lines.append(f'- Noch offen: {remaining} (nächster Lauf startet von selbst)')
    return '\n'.join(lines)


JOB_PATTERNS = ('chapters/*/research/*/request-*.yml', 'matter/research/*/request-*.yml', 'jobs/request-*.yml')


def branch_jobs(base='.', ref_prefix='refs/remotes/origin/'):
    """Aufträge auf allen Branches, ohne Checkout: (buch, branch-art, pfad, daten). Recherche und Colorieren
    liegen auf dem Arbeits-Branch, Analyse und Import auf dem Buch-Branch (TARGET)."""
    import fnmatch
    import library
    prefix = library.settings(library.load_manifest())['work_prefix']
    chat = library.CHAT_PREFIX if hasattr(library, 'CHAT_PREFIX') else 'ghostwriter/chat/'
    for ref in git(base, 'for-each-ref', '--format=%(refname)', ref_prefix).stdout.split():
        branch = ref[len(ref_prefix):]
        if branch == 'HEAD' or branch.startswith(chat):
            continue
        kind = 'work' if branch.startswith(prefix) else 'book'
        book = branch[len(prefix):] if kind == 'work' else branch
        names = git(base, 'ls-tree', '-r', '--name-only', ref, '--', 'chapters', 'matter', 'jobs', check=False).stdout.splitlines()
        for name in names:
            if not (any(fnmatch.fnmatch(name, pat) for pat in JOB_PATTERNS) and REQUEST_RE.match(Path(name).name)):
                continue
            try:
                data = yaml.safe_load(git(base, 'show', f'{ref}:{name}').stdout) or {}
            except (RuntimeError, yaml.YAMLError):
                data = None
            if isinstance(data, dict) and TARGET.get(kind_of(data)) != kind:
                continue   # liegt auf dem falschen Branch: wird dort nicht abgearbeitet
            yield book, kind, ref, name, data


def kind_of(data):
    return (data or {}).get('type') or 'research'


def remote_pending(base='.', ref_prefix='refs/remotes/origin/'):
    """Offene Aufträge auf Buch- und Arbeits-Branches, ohne Checkout (#481, #479): {buch: {workflow: Zahl}}.
    Gezählt wird, was die Abarbeitung ausführen würde: ohne `error` und nicht „wartet auf Bestätigung“."""
    out = {}
    for book, _, _, _, data in branch_jobs(base, ref_prefix):
        if isinstance(data, dict) and state(data) == 'open':
            if data.get('not_before') and (_when(data['not_before']) or now_utc()) > now_utc():
                continue   # #65: feste Zeit noch nicht erreicht, der Kontrolllauf startet ihn erst danach
            wf = WORKFLOW[kind_of(data)]
            out.setdefault(book, {})
            out[book][wf] = out[book].get(wf, 0) + 1
    return out


RUN_PATTERNS = ('chapters/*/research/*/run-*.md', 'matter/research/*/run-*.md')


def remote_status(base='.', ref_prefix='refs/remotes/origin/'):
    """Stand der Warteschlange je Buch aus Auftrags- und Laufdateien, ohne KI (#484):
    {buch: {done, failed, waiting, waiting_budget, done_sections, failed_reasons}}. Fertig heißt: Recherche-Lauf
    aus einem Auftrag (`request:` im Kopf) im Änderungspaket, aber noch nicht im Buch übernommen. Andere Arten
    erscheinen, solange sie warten oder fehlgeschlagen sind."""
    import fnmatch
    import library
    prefix = library.settings(library.load_manifest())['work_prefix']
    out = {}
    blank = lambda: {'done': 0, 'failed': 0, 'waiting': 0, 'waiting_budget': 0, 'handover': 0, 'handover_requests': [], 'done_sections': [],
                     'failed_reasons': [], 'model_failed': []}
    for book, _, _, name, data in branch_jobs(base, ref_prefix):
        info = out.setdefault(book, blank())
        st = state(data) if isinstance(data, dict) else 'failed'
        if st == 'failed':
            info['failed'] += 1
            where = Path(name).parent.name if kind_of(data) == 'research' else kind_of(data)
            info['failed_reasons'].append(f'{where}: {str((data or {}).get("error") or "")[:120]}')
            if 'nicht mehr verfügbar' in str((data or {}).get('error') or ''):   # #596: Fehlerklasse „Modell nicht mehr verfügbar“
                info['model_failed'].append(name)
        elif st == 'waiting_budget':
            info['waiting_budget'] += 1
        elif st == 'handover':   # #531: Rundumprüfung vorbereitet, die KI-Teile macht der Assistent
            info['handover'] += 1
            info['handover_requests'].append(name)
        else:
            info['waiting'] += 1
    for ref in git(base, 'for-each-ref', '--format=%(refname)', ref_prefix + prefix).stdout.split():
        book = ref[len(ref_prefix) + len(prefix):]
        merged = set(git(base, 'ls-tree', '-r', '--name-only', ref_prefix + book, '--', 'chapters', 'matter', check=False).stdout.splitlines())
        for name in git(base, 'ls-tree', '-r', '--name-only', ref, '--', 'chapters', 'matter', check=False).stdout.splitlines():
            if any(fnmatch.fnmatch(name, pat) for pat in RUN_PATTERNS) and name not in merged:
                head = git(base, 'show', f'{ref}:{name}', check=False).stdout[:600]
                if re.search(r'(?m)^request:\s*request-\d+', head):
                    info = out.setdefault(book, blank())
                    info['done'] += 1
                    info['done_sections'].append(Path(name).parent.name)
    return {b: i for b, i in out.items() if any(i[k] for k in ('done', 'failed', 'waiting', 'waiting_budget', 'handover'))}


def status_text(info, language='de'):
    """„2 fertig · 1 fehlgeschlagen · 3 warten“ bzw. leer."""
    en = language == 'en'
    parts = []
    if info.get('done'):
        parts.append(f'{info["done"]} ' + ('done' if en else 'fertig'))
    if info.get('failed'):
        parts.append(f'{info["failed"]} ' + ('failed' if en else 'fehlgeschlagen'))
    waiting = (info.get('waiting') or 0) + (info.get('waiting_budget') or 0)
    if waiting:
        parts.append(f'{waiting} ' + ('waiting' if en else 'warten' if waiting != 1 else 'wartet'))
    if info.get('handover'):
        parts.append(f'{info["handover"]} ' + ('review(s) waiting for the AI parts in chat' if en else
                     'Rundumprüfung wartet auf die KI-Teile im Chat' if info['handover'] == 1 else 'Rundumprüfungen warten auf die KI-Teile im Chat'))
    return ' · '.join(parts)


def report(status, language='de'):
    """Meldung beim Wiedereinstieg (#484); leer, wenn es nichts zu melden gibt."""
    if not status:
        return ''
    en = language == 'en'
    total = {k: sum(i.get(k, 0) for i in status.values()) for k in ('done', 'failed', 'waiting', 'waiting_budget', 'handover')}
    lines = [('Since your last visit: ' if en else 'Seit deinem letzten Besuch: ') + status_text(total, language)
             + (' (background queue)' if en else ' (Hintergrund-Warteschlange)')]
    for book, info in sorted(status.items()):
        line = f'- {book}: {status_text(info, language)}'
        if info['done_sections']:
            line += (' – results: ' if en else ' – Ergebnisse: ') + ', '.join(sorted(set(info['done_sections']))[:5])
        lines.append(line)
        lines += [f'  - {"failed" if en else "fehlgeschlagen"}: {r}' for r in info['failed_reasons'][:3]]
        for request in info.get('model_failed', [])[:3]:   # #596: Weg zum erneuten Versuch nennen
            lines.append('  - ' + (f'model no longer available: change the model in “AI services” or update GhostWriter, then '
                                   f'retry: `python3 scripts/jobs.py . retry --request {request}`' if en else
                                   f'Modell nicht mehr verfügbar: im Formular „KI-Dienste“ ein anderes Modell eintragen oder '
                                   f'GhostWriter aktualisieren, dann erneut versuchen: `python3 scripts/jobs.py . retry --request {request}`'))
        for request in info.get('handover_requests', [])[:3]:   # #531: Rundumprüfung vorbereitet
            lines.append('  - ' + (f'review prepared ({request}): do the AI parts now (docs/EDITORIAL-REVIEW.en.md), then '
                                   f'`python3 scripts/jobs.py . complete --request {request}`' if en else
                                   f'Rundumprüfung vorbereitet ({request}): die KI-Teile jetzt abarbeiten (docs/LEKTORAT.md, „Rundumprüfung“), danach '
                                   f'`python3 scripts/jobs.py . complete --request {request}`'))
        if info['waiting_budget']:
            lines.append('  - ' + (f'{info["waiting_budget"]} waiting for confirmation (budget)' if en else
                                   f'{info["waiting_budget"]} warten auf Bestätigung (Budget): „Trotzdem starten“'))
    return '\n'.join(lines)


def start_pending(pending, paused=False, dry_run=False, base='.', run=None):
    """Je Buch und Art mit offenen Aufträgen die Abarbeitung starten (workflow_dispatch auf dem Buch-Branch,
    ohne Eingaben = nur abarbeiten). Pausierte Automatik oder Probelauf: nichts starten, nur melden."""
    run = run or (lambda args: subprocess.run(args, capture_output=True, text=True))
    counts = {b: (w if isinstance(w, dict) else {'research.yml': w}) for b, w in pending.items()}
    total = sum(sum(w.values()) for w in counts.values())
    if not total:
        return ['Hintergrund-Warteschlange: keine liegengebliebenen Aufträge.']
    if paused:
        return [f'Hintergrund-Warteschlange: {total} Aufträge warten; Automatik pausiert, nichts gestartet.']
    lines = []
    for book, flows in sorted(counts.items()):
        if git(base, 'rev-parse', '-q', '--verify', f'refs/remotes/origin/{book}', check=False).returncode:
            lines.append(f'- {book}: {sum(flows.values())} Aufträge, aber kein Buch-Branch; nicht gestartet')
            continue
        for wf, count in sorted(flows.items()):
            if dry_run:
                lines.append(f'- {book} ({wf}): {count} Aufträge (Probelauf: würde starten)')
                continue
            r = run(['gh', 'workflow', 'run', wf, '--ref', book] + (['-f', 'step=queue'] if wf == 'import.yml' else []))
            lines.append(f'- {book} ({wf}): {count} Aufträge, Abarbeitung ' + ('gestartet' if r.returncode == 0 else
                         f'nicht gestartet ({(r.stderr or r.stdout).strip()[:120]})'))
    return [f'Hintergrund-Warteschlange: {total} liegengebliebene Aufträge'] + lines


def listing(base):
    out = []
    for j in jobs(base):
        d = j['data']
        out.append({'request': str(j['path'].relative_to(base)), 'type': j.get('type', 'research'), 'state': j['state'],
                    'section_id': j.get('section_id', ''), 'requested_at': d.get('requested_at'),
                    'question': d.get('question'), 'error': d.get('error') or j.get('error'),
                    'priority': d.get('priority') is True, 'after': d.get('after') or '',
                    'blocked_by': j.get('blocked_by') or '', 'start_wait': j.get('start_wait') or '', 'locked_by': j.get('locked_by') or '', 'note': j.get('problem') or j.get('note') or ''})
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('base')
    ap.add_argument('cmd', choices=['list', 'enqueue', 'prioritize', 'retry', 'cancel', 'complete', 'suggest', 'merge', 'auto', 'process', 'remote', 'report'])
    ap.add_argument('--language', default='de')
    ap.add_argument('--start', action='store_true', help='remote: Abarbeitung je Buch starten')
    ap.add_argument('--paused', action='store_true', help='remote: Automatik pausiert, nur melden')
    ap.add_argument('--dry-run', action='store_true')
    ap.add_argument('--type', default='research', choices=TYPES, help='enqueue: Art; process: nur diese Art(en), mehrfach möglich')
    ap.add_argument('--types', help='process: nur diese Arten, mit Komma (Vorgabe: alle)')
    ap.add_argument('--field', action='append', default=[], metavar='NAME=WERT',
                    help='enqueue: Feld der Art (z. B. folder=…, kind=characters,style); true/false werden zu Wahrheitswerten')
    ap.add_argument('--section')
    ap.add_argument('--request', help='prioritize/retry/cancel: Auftrag (Pfad im Buch oder Dateiname)')
    ap.add_argument('--priority', action='store_true', help='enqueue: vorziehen')
    ap.add_argument('--after', help='enqueue: erst nach diesem Auftrag (Pfad im Buch)')
    ap.add_argument('--not-before', help='enqueue: erst ab diesem Zeitpunkt (ISO 8601, #65)')
    ap.add_argument('--when', help='enqueue: budget_free = nur bei freiem KI-Budget (#65)')
    ap.add_argument('--after-event', help='enqueue: chapter_approved[:<kapitel>] | edition_created | material_added (#65)')
    ap.add_argument('--question')
    ap.add_argument('--provider')
    ap.add_argument('--model')
    ap.add_argument('--confirm-low-budget', action='store_true')
    ap.add_argument('--requested-by')
    ap.add_argument('--defaults')
    ap.add_argument('--limit', type=int, default=LIMIT)
    ap.add_argument('--push-to', help='Arbeits-Branch: nach jedem Auftrag committen und hochladen')
    ap.add_argument('--no-commit', action='store_true')
    ap.add_argument('--json', action='store_true')
    a = ap.parse_args(argv)
    base = Path(a.base)
    try:
        if a.cmd == 'list':
            data = listing(base)
            if a.json:
                print(json.dumps(data, ensure_ascii=False, indent=1))
            else:
                names = {'open': 'wartet', 'waiting_budget': 'wartet auf Bestätigung (Budget)', 'failed': 'fehlgeschlagen', 'handover': 'wartet auf die KI-Teile im Chat'}
                print('\n'.join(f'- {names[x["state"]]}: {x["request"]}' + (' (vorgezogen)' if x['priority'] else '')
                                + (f' – wartet auf {x["blocked_by"]}' if x['blocked_by'] else '')
                                + (f' – Startbedingung: {x["start_wait"]}' if x.get('start_wait') else '')
                                + (f' – wartet: ausgecheckt ({x["locked_by"]})' if x.get('locked_by') else '')
                                + (f' – {x["error"]}' if x['error'] else '') + (f' [{x["note"]}]' if x['note'] else '')
                                for x in data) or '- Keine Aufträge.')
            return 0
        if a.cmd == 'report':
            status = remote_status(base)
            print(json.dumps(status, ensure_ascii=False, indent=1) if a.json else report(status, a.language) or
                  ('Nothing new in the background queue.' if a.language == 'en' else 'Nichts Neues in der Hintergrund-Warteschlange.'))
            return 0
        if a.cmd == 'remote':
            pending = remote_pending(base)
            lines = start_pending(pending, a.paused, a.dry_run or not a.start, base)
            text = '\n'.join(lines)
            print(text)
            summary_path = os.environ.get('GITHUB_STEP_SUMMARY')
            if summary_path:
                with open(summary_path, 'a', encoding='utf-8') as f:
                    f.write('\n' + text + '\n')
            return 0
        if a.cmd == 'suggest':
            if not a.section:
                raise ValueError('--section angeben.')
            data = suggest(base, a.section, a.question, a.type)
            if a.json:
                print(json.dumps(data, ensure_ascii=False, indent=1))
            else:
                names = {'merge': 'Zusammenlegen', 'after': 'Danach einreihen', 'independent': 'Unabhängig'}
                print('Empfehlung: ' + names[data['recommended']] + ' (' + ', '.join(names[o] for o in data['options']) + ')')
                for c in data['candidates']:
                    print(f'- {c["request"]} ({"gleicher Abschnitt" if c["relation"] == "same_section" else "gleiches Kapitel"})'
                          + (f': {c["question"]}' if c['question'] else ''))
            return 0
        if a.cmd == 'auto':
            made = auto_analysis(base)
            if made and a.push_to:
                commit_push(base, 'Warteschlange: Analyse nach Kapitelabschluss eingereiht', a.push_to, paths=['jobs'])
            print('\n'.join(str(p.relative_to(base)) for p in made) or 'Nichts einzureihen.')
            return 0
        if a.cmd == 'merge':
            if not a.request:
                raise ValueError('--request angeben.')
            path = merge(base, a.request, a.question)
            if a.push_to:
                commit_push(base, f'Warteschlange: Frage in {path.relative_to(base)} zusammengelegt', a.push_to)
            print(path.relative_to(base))
            return 0
        if a.cmd in ('prioritize', 'cancel', 'retry', 'complete'):
            if not a.request:
                raise ValueError('--request angeben.')
            path = {'prioritize': prioritize, 'cancel': cancel, 'retry': retry, 'complete': complete}[a.cmd](base, a.request)
            if a.push_to:
                commit_push(base, f'Warteschlange: {path.relative_to(base)} '
                            + {'prioritize': 'vorgezogen', 'cancel': 'abgebrochen', 'retry': 'erneut versuchen', 'complete': 'abgeschlossen'}[a.cmd], a.push_to)
            print(path.relative_to(base))
            return 0
        if a.cmd == 'enqueue':
            fields = {}
            for item in a.field:
                key, _, value = item.partition('=')
                fields[key.strip()] = {'true': True, 'false': False}.get(value.strip().lower(), value) if value.strip().lower() in ('true', 'false') else value
            path = enqueue(base, a.type, a.section, a.question, a.provider, a.model, a.confirm_low_budget, a.requested_by,
                           fields=fields, priority=a.priority, after=a.after, not_before=a.not_before, when=a.when,
                           after_event=a.after_event)
            if a.push_to:   # Auftrag sofort sichern: geht ein Lauf verloren, bleibt er in der Warteschlange
                commit_push(base, f'Warteschlange: Auftrag {path.relative_to(base)}', a.push_to)
            print(path.relative_to(base))
            return 0
        defaults = a.defaults if a.defaults and Path(a.defaults).is_file() else None
        types = [t.strip() for t in (a.types or '').split(',') if t.strip()] or None
        results, remaining = process(base, defaults, a.limit, a.push_to, not a.no_commit, types=types)
        print(summary(results, remaining))
        out = os.environ.get('GITHUB_OUTPUT')
        if out:
            with open(out, 'a', encoding='utf-8') as f:
                f.write(f'remaining={remaining}\n')
        return 0
    except (ValueError, research.ResearchError, RuntimeError) as e:
        print(f'::error::{e}')
        return 2


if __name__ == '__main__':
    sys.exit(main())
