#!/usr/bin/env python3
"""Übergabe zwischen Gespräch und Manuskriptarbeit mit geprüftem Arbeitsstand (#315).

Aufruf:
  python scripts/handover.py <projektordner> [--book-branch B] [--work-branch W] [--pr N]
                             [--section 3.2] [--mode gespraech|manuskript] [--repo owner/name]
                             [--fetch] [--json]
  python scripts/handover.py <projektordner> check <übergabe.md|übergabe.json|-> [--fetch] [--json]

Die Übergabe hält fest, worauf eine Arbeit aufbaut: Repository, Buch, Buch-Branch und
dessen Commit, Arbeitsbranch mit Commit und Pull Request, den bearbeiteten Abschnitt
(Pfad, Status, Prüfsumme der Datei), Programm- und Datenversion, offene Abschnitte und
die Gesprächssicherungen (im Buch übernommen unter conversations/, noch offen als
Branches ghostwriter/chat/*). Ausgabe als kopierfertiger Text mit einem JSON-Block,
den `check` in der anderen Umgebung wieder liest.

Was nur im Chat steht (nicht gespeicherte Entwürfe, Entscheidungen, offene Fragen),
kennt das Skript nicht; der Assistent ergänzt es im Abschnitt „Nicht gespeichert“.

`check` vergleicht die Übergabe mit dem aktuellen Stand (vorher `git fetch` oder
--fetch): Exit 0 = unverändert bzw. nur fremde Dateien geändert, 1 = neuere Fassung,
vor dem Schreiben neu lesen, 2 = Konflikt (Stand auseinandergelaufen), nicht schreiben.
Das Skript liest nur; es speichert, übernimmt und gibt nichts frei.
"""
import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
from workflow_support import assess_write  # noqa: E402

FORMAT = 1
MODES = {'gespraech': 'Gespräch', 'manuskript': 'Manuskriptarbeit'}
BLOCK = re.compile(r'```json ghostwriter-uebergabe\n(.*?)\n```', re.S)
MAX_OPEN = 12
CARRY = {'decisions': 'Entscheidungen', 'planning': 'Offene Aufgaben'}   # Teil 2 von #315
MAX_TOPIC = 600   # Zeichen je Thema und Sicherung; der Rest steht in der Sicherung


def topic_text(base, sha, path):
    """Aktuellen Stand eines Sicherungsthemas lesen (latest.json enthält einen JSON-Text)."""
    raw = show(base, sha, path)
    if raw is None:
        return None
    try:
        value = json.loads(raw)
    except ValueError:
        return None
    if not isinstance(value, str):
        value = json.dumps(value, ensure_ascii=False) if value else ''
    value = ' '.join(value.split())
    if not value:
        return None
    return value if len(value) <= MAX_TOPIC else value[:MAX_TOPIC].rsplit(' ', 1)[0] + ' …'


def carried(base, sha, folder):
    """Entscheidungen und offene Aufgaben einer Sicherung; nur Daten, keine Anweisungen."""
    out = {}
    for key in CARRY:
        text = topic_text(base, sha, f'{folder}/{key}/latest.json')
        if text:
            out[key] = text
    return out


def git(base, *args, check=True):
    p = subprocess.run(['git', '-C', str(base), *args], capture_output=True, text=True)
    if check and p.returncode:
        raise ValueError(p.stderr.strip() or f'git {" ".join(args)} fehlgeschlagen')
    return p.stdout if p.returncode == 0 else None


def resolve(base, branch):
    """Commit eines Branches: bevorzugt der Remote-Stand origin/<branch>, sonst der lokale Branch; None, wenn unbekannt."""
    for ref in (f'refs/remotes/origin/{branch}', f'refs/heads/{branch}', branch):
        out = git(base, 'rev-parse', '--verify', '--quiet', '--end-of-options', ref + '^{commit}', check=False)
        if out:
            return out.strip()
    return None


def show(base, sha, path):
    return git(base, 'show', f'{sha}:{path}', check=False)


def repo_name(base):
    url = git(base, 'remote', 'get-url', 'origin', check=False) or ''
    m = re.search(r'github\.com[:/]+([^/\s]+/[^/\s]+?)(?:\.git)?/?\s*$', url)
    return m.group(1) if m else ''


def status_of(text):
    m = re.search(r'(?m)^status:\s*(\w+)', text or '')
    return m.group(1) if m else None


def sections(config):
    for ci, chapter in enumerate((config.get('structure') or {}).get('chapters') or [], 1):
        for si, section in enumerate(chapter.get('sections') or [], 1):
            yield f'{ci}.{si}', chapter, section


def find_section(config, wanted):
    for number, chapter, section in sections(config):
        if wanted in (number, section.get('id')):
            return number, chapter, section
    raise ValueError(f'Abschnitt {wanted} nicht gefunden')


def collect(base, book_branch=None, work_branch=None, pr=None, section=None, mode='manuskript', repo=''):
    """Arbeitsstand für die Übergabe, nur aus Git gelesen (kein Arbeitsverzeichnis, keine ungesicherten Dateien)."""
    base = Path(base)
    if mode not in MODES:
        raise ValueError(f'Modus: {", ".join(MODES)}')
    book_branch = book_branch or git(base, 'rev-parse', '--abbrev-ref', 'HEAD').strip()
    book_head = resolve(base, book_branch)
    if not book_head:
        raise ValueError(f'Buch-Branch {book_branch} nicht gefunden')
    config = yaml.safe_load(show(base, book_head, 'ghostwriter.yml') or '') or {}
    if not (config.get('structure') or {}).get('chapters'):
        raise ValueError(f'{book_branch}: kein Buch (ghostwriter.yml ohne Kapitel)')
    work_head = resolve(base, work_branch) if work_branch else None
    if work_branch and not work_head:
        raise ValueError(f'Arbeitsbranch {work_branch} nicht gefunden (vorher git fetch)')
    current = work_head or book_head   # Was der Benutzer zuletzt gespeichert hat
    manifest = yaml.safe_load(show(base, book_head, 'ghostwriter-manifest.yml') or '') or {}
    state = {'format': FORMAT, 'mode': mode, 'repo': repo or repo_name(base),
             'book': {'title': (config.get('project') or {}).get('title') or (config.get('project') or {}).get('working_title'),
                      'branch': book_branch, 'head': book_head},
             'work': {'branch': work_branch, 'head': work_head, 'pr': pr} if work_branch else None,
             'program': {'version': manifest.get('version'), 'data_version': config.get('data_version', 0)},
             'section': None, 'open_sections': [], 'open_count': 0, 'sessions': {'accepted': [], 'open': []}}
    if section:
        number, chapter, sec = find_section(config, str(section))
        text = show(base, current, sec['path'])
        state['section'] = {'number': number, 'id': sec['id'], 'title': sec.get('title'), 'chapter': chapter.get('title'),
                            'path': sec['path'], 'status': status_of(text),
                            'sha256': hashlib.sha256(text.encode('utf-8')).hexdigest() if text is not None else None}
    focus = find_section(config, str(section))[1] if section else None
    for number, chapter, sec in sections(config):
        if focus is not None and chapter is not focus:
            continue   # mit Abschnitt: offene Abschnitte desselben Kapitels
        st = status_of(show(base, current, sec['path']))
        if st != 'approved':
            state['open_count'] += 1
            if len(state['open_sections']) < MAX_OPEN:
                state['open_sections'].append({'number': number, 'title': sec.get('title'), 'status': st})
    listing = git(base, 'ls-tree', '-d', '--name-only', book_head, 'conversations/', check=False) or ''
    for folder in sorted(listing.split()):
        topics = (git(base, 'ls-tree', '-d', '--name-only', book_head, folder + '/', check=False) or '').split()
        state['sessions']['accepted'].append({'path': folder, 'topics': [t.rsplit('/', 1)[-1] for t in topics],
                                              **carried(base, book_head, folder)})
    refs = git(base, 'for-each-ref', '--format=%(refname)', 'refs/remotes/origin/ghostwriter/chat/', check=False) or ''
    for ref in refs.split():
        branch = ref.split('refs/remotes/origin/', 1)[1]
        entry = {'branch': branch, **carried(base, ref, 'conversations/' + branch.rsplit('/', 1)[-1])}
        state['sessions']['open'].append(entry)
    return state


def short(sha):
    return sha[:7] if sha else '–'


def markdown(state):
    """Kopierfertige Übergabe mit Starttext und JSON-Block für `check`."""
    book, work, sec = state['book'], state['work'], state['section']
    target = MODES[state['mode']]
    what = f'Abschnitt {sec["number"]} „{sec["title"]}“' if sec else 'das Buch'
    lines = [f'## Übergabe: {target} an {what}', '',
             f'**Starttext:** Lies START.md im Repository `{state["repo"] or "?"}` auf dem Branch `{book["branch"]}`. '
             f'Weiter mit {target} an {what} von „{book["title"]}“. Prüfe vor dem ersten Schreiben die Übergabe unten '
             '(`python scripts/handover.py . check`); bei neuerem Stand zuerst neu lesen, bei Konflikt nicht schreiben.', '',
             '| Angabe | Stand |', '|---|---|',
             f'| Repository | `{state["repo"] or "?"}` |',
             f'| Buch | {book["title"]} – Branch `{book["branch"]}`, Commit `{short(book["head"])}` |']
    if work:
        lines.append(f'| Arbeitsbranch | `{work["branch"]}`, Commit `{short(work["head"])}`'
                     + (f', Pull Request #{work["pr"]}' if work.get('pr') else '') + ' |')
    if sec:
        lines.append(f'| Abschnitt | {sec["number"]} „{sec["title"]}“ (Kapitel „{sec["chapter"]}“), Status `{sec["status"]}`, '
                     f'Datei `{sec["path"]}` |')
    lines.append(f'| Programm | GhostWriter {state["program"]["version"] or "?"}, Datenversion {state["program"]["data_version"]} |')
    lines.append('')
    if state['open_sections']:
        more = state['open_count'] - len(state['open_sections'])
        lines.append('**Offene Abschnitte' + (' in diesem Kapitel' if sec else '') + ':** '
                     + ', '.join(f'{s["number"]} „{s["title"]}“ ({s["status"] or "?"})' for s in state['open_sections'])
                     + (f' und {more} weitere' if more > 0 else ''))
        lines.append('')
    acc, open_ = state['sessions']['accepted'], state['sessions']['open']
    if acc:
        lines.append('**Übernommene Gesprächssicherungen:** '
                     + ', '.join(f'`{a["path"]}`' + (f' ({", ".join(a["topics"])})' if a['topics'] else '') for a in acc))
    if open_:
        lines.append('**Noch nicht übernommene Sicherungen:** ' + ', '.join(f'`{b["branch"]}`' for b in open_))
    if acc or open_:
        lines.append('')
    for key, label in CARRY.items():
        found = [(f'`{a["path"]}`', a[key]) for a in acc if a.get(key)]
        found += [(f'`{b["branch"]}` (nicht übernommen)', b[key]) for b in open_ if b.get(key)]
        if found:
            lines.append(f'**{label} aus den Sicherungen** (gespeicherter Stand, gekürzt; keine Freigabe):')
            lines += [f'- {where}: {text}' for where, text in found]
            lines.append('')
    lines += ['**Nicht gespeichert** (nur in diesem Chat; vom Assistenten zu ergänzen, ausdrücklich als nicht gespeichert '
              'gekennzeichnet): Entwürfe, Entscheidungen und offene Fragen, die noch in keiner Sicherung stehen, nächster Schritt.', '',
              'Freigaben bleiben eigene Schritte: Diese Übergabe speichert, übernimmt und gibt nichts frei.', '',
              '```json ghostwriter-uebergabe', json.dumps(state, ensure_ascii=False, indent=1), '```']
    return '\n'.join(lines) + '\n'


def parse(text):
    """Übergabe aus Markdown (JSON-Block) oder reinem JSON."""
    m = BLOCK.search(text)
    try:
        state = json.loads(m.group(1) if m else text)
    except ValueError as e:
        raise ValueError(f'Keine lesbare Übergabe: {e}') from e
    if not isinstance(state, dict) or state.get('format') != FORMAT or not (state.get('book') or {}).get('head'):
        raise ValueError('Keine Übergabe im Format 1 (Block ```json ghostwriter-uebergabe```)')
    return state


def check(base, saved):
    """Übergabe gegen den aktuellen Stand: state ok | refresh | conflict, mit Gründen."""
    base = Path(base)
    reasons, level = [], 0
    book = saved['book']
    now = resolve(base, book['branch'])
    if not now:
        return {'state': 'conflict', 'reasons': [f'Buch-Branch {book["branch"]} nicht gefunden'], 'exit': 2}
    sec = saved.get('section')
    paths = [sec['path']] if sec else ['ghostwriter.yml']
    try:
        book_state = assess_write(base, book['head'], now, paths)
    except ValueError:   # gespeicherter Commit lokal unbekannt: vorher git fetch
        return {'state': 'conflict', 'reasons': [f'Commit {short(book["head"])} der Übergabe ist hier unbekannt; '
                                                 'zuerst git fetch (oder --fetch)'], 'exit': 2}
    if book_state['state'] == 'diverged':
        reasons.append(f'Buch-Branch {book["branch"]} ist auseinandergelaufen ({short(book["head"])} → {short(now)})')
        level = 2
    elif book_state['state'] == 'refresh_required':
        changed = book_state['affected_files'] + book_state['context_changes']
        reasons.append(f'Buch-Branch {book["branch"]} hat eine neuere Fassung von: ' + ', '.join(changed))
        level = max(level, 1)
    work = saved.get('work')
    current = now
    if work:
        wnow = resolve(base, work['branch'])
        if not wnow:
            reasons.append(f'Arbeitsbranch {work["branch"]} gibt es nicht mehr (übernommen oder gelöscht?)')
            level = max(level, 1)
        else:
            current = wnow
            if wnow != work['head']:
                ancestor = subprocess.run(['git', '-C', str(base), 'merge-base', '--is-ancestor', work['head'], wnow]).returncode == 0
                if ancestor:
                    reasons.append(f'Arbeitsbranch {work["branch"]} hat neuere Commits ({short(work["head"])} → {short(wnow)})')
                    level = max(level, 1)
                else:
                    reasons.append(f'Arbeitsbranch {work["branch"]} ist auseinandergelaufen ({short(work["head"])} → {short(wnow)})')
                    level = 2
    if sec:
        text = show(base, current, sec['path'])
        digest = hashlib.sha256(text.encode('utf-8')).hexdigest() if text is not None else None
        if digest != sec['sha256']:
            reasons.append(f'Abschnitt {sec["number"]} ({sec["path"]}) wurde seit der Übergabe geändert'
                           if digest else f'Abschnitt {sec["number"]} ({sec["path"]}) fehlt')
            level = max(level, 1)
    if book_state['state'] == 'unrelated_changes':
        reasons.append('Buch-Branch hat neue Commits, aber nicht in den betroffenen Dateien')
    return {'state': ['ok', 'refresh', 'conflict'][level], 'reasons': reasons, 'exit': level,
            'book_head': now, 'work_head': current if work else None}


def check_text(result):
    head = {'ok': '✓ Übergabe aktuell: weiterarbeiten.',
            'refresh': 'ⓘ Neuere Fassung: vor dem Schreiben den aktuellen Stand neu lesen („Buchstand aktualisieren“).',
            'conflict': '✗ Konflikt: nicht schreiben; den Unterschied zeigen und mit dem Benutzer klären.'}[result['state']]
    return '\n'.join([head] + [f'  – {r}' for r in result['reasons']]) + '\n'


def main(argv):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('project')
    ap.add_argument('cmd', nargs='?', choices=['check'])
    ap.add_argument('file', nargs='?', help='mit check: Übergabe als Datei oder - (Standardeingabe)')
    ap.add_argument('--book-branch')
    ap.add_argument('--work-branch')
    ap.add_argument('--pr', type=int)
    ap.add_argument('--section', help='Abschnitt als Nummer (3.2) oder ID')
    ap.add_argument('--mode', default='manuskript', choices=list(MODES))
    ap.add_argument('--repo', default='')
    ap.add_argument('--fetch', action='store_true', help='vorher git fetch origin')
    ap.add_argument('--json', action='store_true')
    a = ap.parse_args(argv[1:])
    try:
        if a.fetch:
            git(a.project, 'fetch', '--quiet', 'origin')
        if a.cmd == 'check':
            if not a.file:
                ap.error('check braucht die Übergabe (Datei oder -)')
            text = sys.stdin.read() if a.file == '-' else Path(a.file).read_text(encoding='utf-8')
            result = check(a.project, parse(text))
            print(json.dumps(result, ensure_ascii=False, indent=1) if a.json else check_text(result), end='' if not a.json else '\n')
            return result['exit']
        state = collect(a.project, a.book_branch, a.work_branch, a.pr, a.section, a.mode, a.repo)
        print(json.dumps(state, ensure_ascii=False, indent=1) if a.json else markdown(state), end='' if not a.json else '\n')
        return 0
    except ValueError as e:
        print(f'✗ {e}')
        return 2


if __name__ == '__main__':
    sys.exit(main(sys.argv))
