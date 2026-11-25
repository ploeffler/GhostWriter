#!/usr/bin/env python3
"""Hintergrund-Warteschlange (#476, Teil 1 #480): Aufträge für KI-Arbeiten, die dauern und kosten.

Aufruf:
  python scripts/jobs.py <buch> list [--json]
  python scripts/jobs.py <buch> enqueue --type research --section <id> [--question Q] [--provider P]
                                        [--model M] [--confirm-low-budget] [--requested-by NAME]
                                        [--priority] [--after <auftrag>]
  python scripts/jobs.py <buch> prioritize --request <auftrag>      (vorziehen, #478)
  python scripts/jobs.py <buch> cancel --request <auftrag>          (nur wartende Aufträge)
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

Reihenfolge (#478), in dieser Rangfolge: Vorrang (`priority: true`, „vorziehen“), Abhängigkeit
(`after: <Auftrag>`: der Auftrag wartet, bis der genannte erledigt oder fehlgeschlagen ist;
Ringe werden ignoriert und gemeldet), Buchreihenfolge (Kapitel, Abschnitt; Vor- und Nachspann
danach), `requested_at`, Dateipfad. Die KI sortiert nicht um. Je Auftrag: Budget prüfen (darunter `waiting: budget`, außer
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

TYPES = ('research', 'analysis', 'colorize', 'import')
# Felder je Art (Eingaben der bisherigen Actions, #479); sie stehen unter dem Namen der Art
FIELDS = {'analysis': ('kind', 'scope', 'prompt_profile'),
          'colorize': ('folder', 'consent', 'model', 'replace', 'hint', 'minors_exception'),
          'import': ('step', 'file', 'ops', 'writing_approval', 'by', 'prompt_profile')}
# Workflow, der eine Art abarbeitet, und der Branch, auf den das Ergebnis kommt
WORKFLOW = {'research': 'research.yml', 'analysis': 'analyse.yml', 'colorize': 'colorize.yml', 'import': 'import.yml'}
TARGET = {'research': 'work', 'colorize': 'work', 'analysis': 'book', 'import': 'book'}
# Arten bzw. Schritte ohne KI-Kosten: keine Budgetprüfung
FREE = {('import', 'convert'), ('import', 'edit'), ('import', 'apply')}
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
    """open | waiting_budget | failed"""
    if job.get('error'):
        return 'failed'
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


def jobs(base, config=None):
    """Alle Aufträge mit Pfad, Daten und Zustand, in Abarbeitungsreihenfolge (#478): Vorrang, dann Buchreihenfolge,
    dann Auftragszeit; ein Auftrag mit `after` steht stets hinter seinem Ziel."""
    base = Path(base)
    config = config if config is not None else (read(base / 'ghostwriter.yml') or {})
    order = book_order(config)
    out = []
    for path in files(base):
        data = read(path)
        if data is None:
            out.append({'path': path, 'data': {}, 'state': 'failed', 'rank': (1, 9), 'error': 'Auftrag nicht lesbar'})
            continue
        sid = str(data.get('section_id') or (path.parent.name if 'research' in path.parts else ''))
        rank = (0 if data.get('priority') is True else 1,) + order.get(sid, (8, 0, 0)) \
            + (str(data.get('requested_at') or ''), str(path.relative_to(base)))
        out.append({'path': path, 'data': data, 'state': state(data), 'rank': rank, 'section_id': sid, 'type': kind(data)})
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


def queue(base, config=None, types=None):
    """Aufträge, die jetzt ausgeführt werden dürfen: offen und nicht von einem noch offenen Auftrag abhängig."""
    return [j for j in jobs(base, config) if j['state'] == 'open' and not j.get('blocked_by') and not j.get('locked_by')
            and (not types or j['type'] in types)]


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
    if not pending(job):
        raise ValueError('Abbrechen geht nur bei wartenden Aufträgen.')
    job['path'].unlink()
    return job['path']


def section_path(base, config, section_id):
    ch, sec, _, _ = research.find_section(base, config, section_id)
    return Path(base) / ch['path'] / 'research' / sec['id']


def enqueue(base, type_='research', section=None, question=None, provider=None, model=None,
            confirm_low_budget=False, requested_by=None, now=None, fields=None, priority=False, after=None):
    """Auftrag anlegen; einziger Weg, eine Arbeit in die Warteschlange zu stellen. Gibt den Pfad zurück.
    Recherche am Abschnitt; andere Arten unter jobs/ mit ihren Feldern (`fields`) unter dem Namen der Art."""
    if type_ not in TYPES:
        raise ValueError(f'Unbekannte Art: {type_}')
    base = Path(base)
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
    path = folder / f'request-{n:03d}.yml'
    write(path, data)
    return path


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


RUNNERS = {'colorize': run_colorize, 'analysis': run_analysis, 'import': run_import}


def run_job(base, job, defaults, now):
    data = job['data']
    if job['type'] in RUNNERS:
        res = RUNNERS[job['type']](base, job)
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
        ready = queue(base, config, types)   # jedes Mal neu: ein erledigter Auftrag gibt abhängige frei (#478)
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
    return results, len(queue(base, config, types))


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
    blank = lambda: {'done': 0, 'failed': 0, 'waiting': 0, 'waiting_budget': 0, 'done_sections': [], 'failed_reasons': [],
                     'model_failed': []}
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
    return {b: i for b, i in out.items() if any(i[k] for k in ('done', 'failed', 'waiting', 'waiting_budget'))}


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
    return ' · '.join(parts)


def report(status, language='de'):
    """Meldung beim Wiedereinstieg (#484); leer, wenn es nichts zu melden gibt."""
    if not status:
        return ''
    en = language == 'en'
    total = {k: sum(i[k] for i in status.values()) for k in ('done', 'failed', 'waiting', 'waiting_budget')}
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
                    'blocked_by': j.get('blocked_by') or '', 'locked_by': j.get('locked_by') or '', 'note': j.get('problem') or j.get('note') or ''})
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('base')
    ap.add_argument('cmd', choices=['list', 'enqueue', 'prioritize', 'retry', 'cancel', 'process', 'remote', 'report'])
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
                names = {'open': 'wartet', 'waiting_budget': 'wartet auf Bestätigung (Budget)', 'failed': 'fehlgeschlagen'}
                print('\n'.join(f'- {names[x["state"]]}: {x["request"]}' + (' (vorgezogen)' if x['priority'] else '')
                                + (f' – wartet auf {x["blocked_by"]}' if x['blocked_by'] else '')
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
        if a.cmd in ('prioritize', 'cancel', 'retry'):
            if not a.request:
                raise ValueError('--request angeben.')
            path = {'prioritize': prioritize, 'cancel': cancel, 'retry': retry}[a.cmd](base, a.request)
            if a.push_to:
                commit_push(base, f'Warteschlange: {path.relative_to(base)} '
                            + {'prioritize': 'vorgezogen', 'cancel': 'abgebrochen', 'retry': 'erneut versuchen'}[a.cmd], a.push_to)
            print(path.relative_to(base))
            return 0
        if a.cmd == 'enqueue':
            fields = {}
            for item in a.field:
                key, _, value = item.partition('=')
                fields[key.strip()] = {'true': True, 'false': False}.get(value.strip().lower(), value) if value.strip().lower() in ('true', 'false') else value
            path = enqueue(base, a.type, a.section, a.question, a.provider, a.model, a.confirm_low_budget, a.requested_by,
                           fields=fields, priority=a.priority, after=a.after)
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
