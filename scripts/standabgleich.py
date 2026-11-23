#!/usr/bin/env python3
"""Standabgleich zwischen Chats und Apps (#179, Teil 1).

Ein Chat arbeitet mit dem Stand, den er einmal gelesen hat. Nach einer Pause, in einer anderen App oder
nach einem Programmupdate kann dieser Stand veraltet sein. Das Skript hält den gelesenen Stand fest
(`stand`) und vergleicht ihn später mit dem aktuellen (`check`), getrennt nach Bereichen:

- Buch: Buch-Branch und Commit (neuere Fassung, Branch verschwunden oder umgeschrieben)
- Arbeit: Arbeitsbranch und Commit (neuere Fassung, übernommen, auseinandergelaufen)
- Programm: Programmversion und eingespielter Upstream-Commit (`.ghostwriter/update.yml`)
- Anweisungen: START.md, CLAUDE.md, AGENTS.md, allgemeine Skills, docs/start/ (geladene Fassung veraltet)
- Profil: assistant.yml (persönlicher Skill veraltet)
- Abgeleitet: Übersichtsdatei (ghostwriter-index.json) und, im Zusammenfassungsmodus, Buch- und
  Kapitelzusammenfassungen (context/) des gelesenen Stands; nur Hinweis, sperrt nichts
- Daten: Datenversion des Buchs gegen die vom Programm unterstützte (Buch neuer als Programm = Konflikt)

Ergebnis je Bereich: `ok`, `hinweis` (Originaldateien statt abgeleiteter Daten lesen; ändert den Exit-Code nicht), `neuer` (erst neu lesen bzw. Anweisungen neu laden) oder `konflikt` (nicht
schreiben, Unterschied zeigen). Exit 0 = alles unverändert, 1 = neuer Stand, 2 = Konflikt oder
inkompatible Version. Nur lesend; vorher `git fetch`, sonst vergleicht das Skript mit dem lokalen Wissen
(`--fetch` holt den Stand selbst).

Was das Skript nicht abgleichen kann, nennt die Ausgabe ausdrücklich (Chatinhalte, Index einer
Verbindung, nicht gesendete Eingaben); es behauptet nie „alles synchron“.

Aufruf:
  python3 scripts/standabgleich.py <repo> stand --book buch/x [--work ghostwriter/y] [--program-ref main] [--fetch]
  python3 scripts/standabgleich.py <repo> check <stand.json|-> [--fetch] [--json]
"""
import argparse
import contextlib
import hashlib
import io
import json
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
from handover import git, repo_name, resolve, show  # noqa: E402

FORMAT = 1
INSTRUCTIONS = ('START.md', 'CLAUDE.md', 'AGENTS.md', '.claude/skills', 'docs/start', 'ghostwriter-skills.yml')
UPDATE_STATE = '.ghostwriter/update.yml'
NOT_CHECKED = ['Inhalte dieses Chats und nicht gesendete Eingaben', 'Zwischenspeicher oder Suchindex einer Verbindung',
               'Stand anderer Apps, solange dort nichts gespeichert ist']
LABEL = {'ok': '✓', 'hinweis': '⚠', 'neuer': 'ⓘ', 'konflikt': '✗'}


def default_ref(base):
    head = git(base, 'symbolic-ref', '-q', '--short', 'refs/remotes/origin/HEAD', check=False) or ''
    return head.strip().split('/', 1)[1] if '/' in head else None


def tree_hash(base, ref, paths):
    """Fingerabdruck der Dateien unter `paths` (Blob-Kennungen aus Git, ohne Inhalte zu lesen)."""
    listing = git(base, 'ls-tree', '-r', ref, '--', *paths, check=False) or ''
    return hashlib.sha256(listing.encode('utf-8')).hexdigest() if listing.strip() else None


def blob_hash(base, ref, path):
    text = show(base, ref, path)
    return hashlib.sha256(text.encode('utf-8')).hexdigest() if text is not None else None


def collect(base, book, work=None, program_ref=None, repo=None):
    """Gelesenen Stand festhalten. Programm, Anweisungen und Profil liegen in einer Bibliothek auf dem
    Standard-Branch, im Einzelbuch auf dem Buch-Branch selbst."""
    book_head = resolve(base, book)
    if not book_head:
        raise ValueError(f'Buch-Branch {book} nicht gefunden (vorher git fetch)')
    work_head = resolve(base, work) if work else None
    if work and not work_head:
        raise ValueError(f'Arbeitsbranch {work} nicht gefunden (vorher git fetch)')
    program_ref = program_ref or default_ref(base) or book
    prog = collect_program(base, program_ref)
    if prog is None:
        raise ValueError(f'Programmstand {program_ref} nicht gefunden')
    config = yaml.safe_load(show(base, work_head or book_head, 'ghostwriter.yml') or '') or {}
    return {'format': FORMAT, 'repo': repo or repo_name(base),
            'book': {'branch': book, 'head': book_head},
            'work': {'branch': work, 'head': work_head} if work else None,
            'program': {'ref': program_ref, 'version': prog['version'], 'upstream_commit': prog['upstream_commit']},
            'instructions': prog['instructions'], 'profile': prog['profile'],
            'data': {'book': config.get('data_version', 0), 'supported': prog['supported']}}

def is_ancestor(base, old, new):
    return git(base, 'merge-base', '--is-ancestor', old, new, check=False) is not None


def count(base, old, new):
    out = git(base, 'rev-list', '--count', f'{old}..{new}', check=False)
    return int(out) if out else 0


def known(base, sha):
    return bool(sha) and git(base, 'cat-file', '-e', sha + '^{commit}', check=False) is not None


def compare(base, old):
    """Gelesenen Stand mit dem aktuellen vergleichen; Liste von (Bereich, Ergebnis, Hinweis)."""
    if not isinstance(old, dict) or old.get('format') != FORMAT:
        raise ValueError('Kein Stand im Format 1 (python3 scripts/standabgleich.py . stand …)')
    out = []
    book = old['book']
    head = resolve(base, book['branch'])
    if not head:
        out.append(('Buch', 'konflikt', f'Buch-Branch {book["branch"]} gibt es nicht mehr'))
    elif head == book['head']:
        out.append(('Buch', 'ok', f'{book["branch"]} unverändert ({head[:7]})'))
    elif known(base, book['head']) and is_ancestor(base, book['head'], head):
        out.append(('Buch', 'neuer', f'{book["branch"]}: {count(base, book["head"], head)} neue Commits '
                                     f'({book["head"][:7]} → {head[:7]}); betroffene Dateien neu lesen'))
    else:
        out.append(('Buch', 'konflikt', f'{book["branch"]} wurde umgeschrieben oder der gelesene Commit '
                                        f'{book["head"][:7]} ist unbekannt'))
    work = old.get('work')
    if work:
        whead = resolve(base, work['branch'])
        if whead == work['head']:
            out.append(('Arbeit', 'ok', f'{work["branch"]} unverändert ({whead[:7]})'))
        elif not whead:
            if head and known(base, work['head']) and is_ancestor(base, work['head'], head):
                out.append(('Arbeit', 'neuer', f'{work["branch"]} ist ins Buch übernommen; ab jetzt vom Buch-Branch lesen'))
            else:
                out.append(('Arbeit', 'konflikt', f'{work["branch"]} gibt es nicht mehr und ist nicht im Buch enthalten'))
        elif known(base, work['head']) and is_ancestor(base, work['head'], whead):
            out.append(('Arbeit', 'neuer', f'{work["branch"]}: {count(base, work["head"], whead)} neue Commits, '
                                           'z. B. aus einer anderen App; erst neu lesen'))
        else:
            out.append(('Arbeit', 'konflikt', f'{work["branch"]} ist auseinandergelaufen; nicht schreiben, Unterschied zeigen'))
    now = collect_program(base, old['program']['ref'])
    if now is None:
        out.append(('Programm', 'konflikt', f'Programmstand {old["program"]["ref"]} nicht gefunden'))
        return out
    prog_old = old['program']
    if (now['version'], now['upstream_commit']) == (prog_old['version'], prog_old['upstream_commit']):
        out.append(('Programm', 'ok', f'GhostWriter {now["version"] or "?"}'))
    else:
        out.append(('Programm', 'neuer', f'Programm aktualisiert: {prog_old["version"] or "?"} → {now["version"] or "?"}'))
    out.append(('Anweisungen', 'ok', 'geladene Anweisungen aktuell') if now['instructions'] == old['instructions'] else
               ('Anweisungen', 'neuer', 'START.md, CLAUDE.md oder Skills geändert; vor der nächsten Aufgabe neu laden'))
    if now['profile'] == old['profile']:
        out.append(('Profil', 'ok', 'assistant.yml unverändert' if now['profile'] else 'kein assistant.yml'))
    else:
        out.append(('Profil', 'neuer', 'assistant.yml geändert; persönlichen Skill neu lesen'))
    current = (resolve(base, work['branch']) if work else None) or head
    config = (yaml.safe_load(show(base, current, 'ghostwriter.yml') or '') or {}) if current else {}
    have, can = config.get('data_version', 0) if current else old['data']['book'], now['supported']
    if can is not None and have > can:
        out.append(('Daten', 'konflikt', f'Buch hat Datenversion {have}, das Programm kennt nur {can}; '
                                         'erst Programm aktualisieren, bis dahin nicht schreiben'))
    elif can is not None and have < can:
        out.append(('Daten', 'neuer', f'Buch hat Datenversion {have}, das Programm {can}; die Migration läuft beim '
                                      'nächsten Update (python3 scripts/migrate_project.py --check zeigt sie)'))
    else:
        out.append(('Daten', 'ok', f'Datenversion {have}'))
    if current:
        d = derived(base, current)
        if d:
            out.append(('Abgeleitet', *d))
    return out


def collect_program(base, ref):
    prog = resolve(base, ref)
    if not prog:
        return None
    manifest = yaml.safe_load(show(base, prog, 'ghostwriter-manifest.yml') or '') or {}
    update = yaml.safe_load(show(base, prog, UPDATE_STATE) or '') or {}
    supported = yaml.safe_load(show(base, prog, 'schemas/data-version.yml') or '') or {}
    return {'version': manifest.get('version'), 'upstream_commit': update.get('commit'),
            'instructions': tree_hash(base, prog, INSTRUCTIONS), 'profile': blob_hash(base, prog, 'assistant.yml'),
            'supported': supported.get('data_version')}


def derived(base, sha):
    """Übersichtsdatei und Zusammenfassungen des Stands `sha` prüfen (#179). Liest den Stand aus Git in einen
    temporären Ordner; das Arbeitsverzeichnis bleibt unberührt. Ergebnis: (Zustand, Hinweis) oder None ohne Buch."""
    import build_index
    import plan_context
    data = subprocess.run(['git', '-C', str(base), 'archive', '--format=tar', sha], capture_output=True)
    if data.returncode:
        return None
    with tempfile.TemporaryDirectory() as tmp:
        with tarfile.open(fileobj=io.BytesIO(data.stdout)) as tar:
            tar.extractall(tmp, filter='data')
        config = yaml.safe_load((Path(tmp) / 'ghostwriter.yml').read_text(encoding='utf-8')) \
            if (Path(tmp) / 'ghostwriter.yml').is_file() else None
        if not ((config or {}).get('structure') or {}).get('chapters'):
            return None
        problems = []
        with contextlib.redirect_stdout(io.StringIO()):
            try:
                index_ok = build_index.main(['build_index.py', tmp, '--check']) == 0
            except Exception:   # kaputte Projektdatei: das meldet validate_project, hier nur Hinweis
                index_ok = False
        if not index_ok:
            problems.append('Übersichtsdatei veraltet oder fehlt (Ansichten aus den Originaldateien befüllen; '
                            'die Action „Übersichtsdatei aktualisieren“ bzw. build_index.py erneuert sie)')
        try:
            ctx = plan_context.plan(tmp)
        except (OSError, ValueError, KeyError):
            ctx = None
        if ctx and ctx['mode'] == 'summaries':
            stale = [s['path'] for s in [ctx['book_summary'], *ctx['chapter_summaries']] if s['state'] != 'current']
            if stale:
                more = f' und {len(stale) - 5} weitere' if len(stale) > 5 else ''
                problems.append('Zusammenfassungen veraltet oder fehlend: ' + ', '.join(stale[:5]) + more
                                + ' (Originalabschnitte lesen, docs/CONTEXT.md)')
    if problems:
        return 'hinweis', '; '.join(problems)
    return 'ok', 'Übersichtsdatei und Zusammenfassungen passen zum Stand'


def verdict(results):
    states = {r[1] for r in results} - {'hinweis'}
    return 'konflikt' if 'konflikt' in states else 'neuer' if 'neuer' in states else 'ok'


def report(old, results):
    lines = [f'Standabgleich für {old.get("repo") or "?"} (gelesen: {old["book"]["branch"]} {old["book"]["head"][:7]})', '']
    lines += [f'{LABEL[state]} {area}: {text}' for area, state, text in results]
    lines += ['', 'Nicht abgeglichen: ' + '; '.join(NOT_CHECKED) + '.']
    v = verdict(results)
    lines.append({'ok': 'Weiterarbeiten.', 'neuer': 'Erst neu lesen bzw. neu laden, dann weiterarbeiten.',
                  'konflikt': 'Nicht schreiben und nichts freigeben, bis der Konflikt geklärt ist.'}[v])
    return '\n'.join(lines) + '\n'


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    p.add_argument('base', type=Path)
    sub = p.add_subparsers(dest='action', required=True)
    s = sub.add_parser('stand', help='gelesenen Stand als JSON ausgeben')
    s.add_argument('--book', required=True)
    s.add_argument('--work')
    s.add_argument('--program-ref')
    s.add_argument('--repo')
    s.add_argument('--fetch', action='store_true')
    c = sub.add_parser('check', help='gelesenen Stand mit dem aktuellen vergleichen')
    c.add_argument('stand', help='Datei mit dem Stand oder - für die Standardeingabe')
    c.add_argument('--fetch', action='store_true')
    c.add_argument('--json', action='store_true')
    a = p.parse_args(argv)
    try:
        if a.fetch:
            git(a.base, 'fetch', '-q', '--prune', 'origin')
        if a.action == 'stand':
            print(json.dumps(collect(a.base, a.book, a.work, a.program_ref, a.repo), ensure_ascii=False, indent=1))
            return 0
        text = sys.stdin.read() if a.stand == '-' else Path(a.stand).read_text(encoding='utf-8')
        old = json.loads(text)
        results = compare(a.base, old)
    except (ValueError, OSError) as e:
        print(f'✗ {e}', file=sys.stderr)
        return 2
    v = verdict(results)
    if a.json:
        print(json.dumps({'state': v, 'results': [{'area': r[0], 'state': r[1], 'text': r[2]} for r in results],
                          'not_checked': NOT_CHECKED}, ensure_ascii=False, indent=1))
    else:
        print(report(old, results), end='')
    return {'ok': 0, 'neuer': 1, 'konflikt': 2}[v]


if __name__ == '__main__':
    sys.exit(main())
