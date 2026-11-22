#!/usr/bin/env python3
"""Hintergrund-Warteschlange (#476, Teil 1 #480): Aufträge für KI-Arbeiten, die dauern und kosten.

Aufruf:
  python scripts/jobs.py <buch> list [--json]
  python scripts/jobs.py <buch> enqueue --type research --section <id> [--question Q] [--provider P]
                                        [--model M] [--confirm-low-budget] [--requested-by NAME]
  python scripts/jobs.py <buch> process [--defaults datei] [--limit 5] [--push-to <arbeits-branch>]

Auftrag (Schema schemas/job.schema.json): eine Datei `request-NNN.yml`.
- Recherche (`type: research`, Vorgabe, wenn `type` fehlt): am Abschnitt unter
  `<kapitel>/research/<abschnitt>/request-NNN.yml` bzw. `matter/research/<teil>/request-NNN.yml`,
  wie die Claude-Web-App sie schon anlegt. Felder der Art (`section_id`, `question`) stehen oben.
- Arten ohne Abschnitt (#479: Analyse, Colorieren, Import) liegen unter `jobs/request-NNN.yml`
  und tragen ihre Felder unter einem Schlüssel mit dem Namen der Art.
Gemeinsame Felder: `type`, `requested_at`, `requested_by`, `provider`, `model`,
`confirm_low_budget`; Zustand: `error` und `failed_at` (fehlgeschlagen, läuft nicht erneut),
`waiting: budget` (wartet auf Bestätigung, weil das KI-Budget unter der Schwelle ist).

Reihenfolge: Buchreihenfolge (Kapitel, Abschnitt; Vor- und Nachspann danach), dann
`requested_at`, dann Dateipfad. Je Auftrag: Budget prüfen (darunter `waiting: budget`, außer
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

TYPES = ('research',)                 # #479: analysis, colorize, import
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


def jobs(base, config=None):
    """Alle Aufträge mit Pfad, Daten und Zustand, in Abarbeitungsreihenfolge."""
    base = Path(base)
    config = config if config is not None else (read(base / 'ghostwriter.yml') or {})
    order = book_order(config)
    out = []
    for path in files(base):
        data = read(path)
        if data is None:
            out.append({'path': path, 'data': {}, 'state': 'failed', 'rank': (9,), 'error': 'Auftrag nicht lesbar'})
            continue
        sid = str(data.get('section_id') or (path.parent.name if 'research' in path.parts else ''))
        rank = order.get(sid, (8, 0, 0)) + (str(data.get('requested_at') or ''), str(path.relative_to(base)))
        out.append({'path': path, 'data': data, 'state': state(data), 'rank': rank, 'section_id': sid, 'type': kind(data)})
    return sorted(out, key=lambda j: j['rank'])


def queue(base, config=None):
    return [j for j in jobs(base, config) if j['state'] == 'open']


def section_path(base, config, section_id):
    ch, sec, _, _ = research.find_section(base, config, section_id)
    return Path(base) / ch['path'] / 'research' / sec['id']


def enqueue(base, type_='research', section=None, question=None, provider=None, model=None,
            confirm_low_budget=False, requested_by=None, now=None):
    """Auftrag anlegen; einziger Weg, eine Arbeit in die Warteschlange zu stellen. Gibt den Pfad zurück."""
    if type_ not in TYPES:
        raise ValueError(f'Unbekannte Art: {type_}')
    base = Path(base)
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


def commit_push(base, message, branch=None, tries=3):
    """Ergebnis eines Auftrags speichern; mit branch auch hochladen (Rebase bei neuerem Stand)."""
    paths = [p for p in COMMIT_PATHS if (Path(base) / p).exists()]
    if paths:
        git(base, 'add', '-A', '--', *paths)
    if git(base, 'diff', '--cached', '--quiet', check=False).returncode == 0:
        return False
    git(base, 'commit', '-q', '-m', message, '-m', 'GhostWriter-Aktion: jobs.process')
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


def run_job(base, job, defaults, now):
    data = job['data']
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


def process(base, defaults=None, limit=LIMIT, push_to=None, commit=True, now=None, low=None):
    """Bis zu `limit` offene Aufträge abarbeiten. Gibt (Ergebnisse, noch offen) zurück."""
    base = Path(base)
    config = read(base / 'ghostwriter.yml') or {}
    results = []
    for job in queue(base, config)[:limit]:
        rel = str(job['path'].relative_to(base))
        stamp = (now or now_utc()).isoformat()
        is_low = low(base) if low else budget_low(base, config)
        if is_low and not job['data'].get('confirm_low_budget'):
            job['data']['waiting'] = 'budget'
            write(job['path'], job['data'])
            results.append({'request': rel, 'ok': False, 'waiting': True,
                            'error': 'Wartet auf Bestätigung: weniger KI-Budget übrig als die Schwelle.'})
            message = f'Warteschlange: {rel} wartet auf Bestätigung (Budget)'
        else:
            try:
                res = run_job(base, job, defaults, now)
                results.append(dict(res, request=rel))
                message = f'{res["label"]} aus der Warteschlange gespeichert'
            except research.ResearchError as e:
                error = str(e)
            except Exception as e:   # noqa: BLE001 – ein Fehler stoppt die Warteschlange nicht
                error = f'Unerwarteter Fehler ({type(e).__name__}). Auftrag bleibt liegen.'
            else:
                error = None
            if error:
                job['data'].update({'error': error, 'failed_at': stamp})
                job['data'].pop('waiting', None)
                write(job['path'], job['data'])
                results.append({'request': rel, 'ok': False, 'error': error})
                message = f'Warteschlange: {rel} fehlgeschlagen'
        if commit:
            commit_push(base, message, push_to)
    return results, len(queue(base, config))


def summary(results, remaining=0):
    lines = []
    for r in results:
        if r['ok']:
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


def listing(base):
    out = []
    for j in jobs(base):
        d = j['data']
        out.append({'request': str(j['path'].relative_to(base)), 'type': j.get('type', 'research'), 'state': j['state'],
                    'section_id': j.get('section_id', ''), 'requested_at': d.get('requested_at'),
                    'question': d.get('question'), 'error': d.get('error') or j.get('error')})
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('base')
    ap.add_argument('cmd', choices=['list', 'enqueue', 'process'])
    ap.add_argument('--type', default='research', choices=TYPES)
    ap.add_argument('--section')
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
                print('\n'.join(f'- {names[x["state"]]}: {x["request"]}' + (f' – {x["error"]}' if x['error'] else '')
                                for x in data) or '- Keine Aufträge.')
            return 0
        if a.cmd == 'enqueue':
            path = enqueue(base, a.type, a.section, a.question, a.provider, a.model, a.confirm_low_budget, a.requested_by)
            if a.push_to:   # Auftrag sofort sichern: geht ein Lauf verloren, bleibt er in der Warteschlange
                commit_push(base, f'Warteschlange: Auftrag {path.relative_to(base)}', a.push_to)
            print(path.relative_to(base))
            return 0
        defaults = a.defaults if a.defaults and Path(a.defaults).is_file() else None
        results, remaining = process(base, defaults, a.limit, a.push_to, not a.no_commit)
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
