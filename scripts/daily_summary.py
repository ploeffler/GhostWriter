#!/usr/bin/env python3
"""Lesender Tagesbericht für den vorhandenen Update-Lauf; kein Mailversand."""
import datetime
import html
import json
import os
import re
import subprocess
import urllib.request


def _git(*args):
    result = subprocess.run(['git', *args], text=True, capture_output=True)
    if result.returncode:
        raise RuntimeError('Git-Daten nicht verfügbar')
    return result.stdout


def content_paths(manifest):
    allowed = {'chapters', 'matter', 'cover', 'characters', 'story', 'research'}
    return [p for p in (manifest.get('book') or []) if p.rstrip('/') in allowed]


def is_content_file(name, paths):
    return any(name.startswith(p.rstrip('/') + '/') for p in paths)


def _content_activity(branch, paths, since):
    if not paths:
        return 0, 0
    ref = 'refs/remotes/origin/' + branch
    _git('rev-parse', '--verify', ref)
    commits = _git('log', '--full-history', ref, '--since=' + since, '--format=%H', '--', *paths).splitlines()
    files, count = set(), 0
    for commit in commits:
        parents = _git('rev-list', '--parents', '-n', '1', commit).split()[1:]
        # Gegen den ersten Elternstand vergleichen: keine doppelten Merge-Diffs.
        args = ['diff', '--name-only', '-z', parents[0], commit] if parents else [
            'diff-tree', '--root', '--no-commit-id', '--name-only', '-z', '-r', commit]
        changed = set()
        for name in _git(*args).split('\0'):
            if not is_content_file(name, paths):
                continue
            diff_args = ['diff', '--numstat', parents[0], commit, '--', name] if parents else [
                'diff-tree', '--root', '--no-commit-id', '--numstat', '-r', commit, '--', name]
            if _git(*diff_args).startswith('-\t-\t'):
                changed.add(name)
                continue
            patch_args = ['diff', '--unified=0', parents[0], commit, '--', name] if parents else [
                'show', '--format=', '--unified=0', commit, '--', name]
            edits = [line[1:] for line in _git(*patch_args).splitlines()
                     if line[:1] in ('+', '-') and not line.startswith(('+++', '---'))]
            if any(line.strip() and not re.match(
                    r'^\s*(?:status|approved_at|approved_by|updated_at|last_modified)\s*:', line)
                   for line in edits):
                changed.add(name)
        if changed:
            count += 1
            files.update(changed)
    return count, len(files)


def _api(repo, endpoint):
    request = urllib.request.Request('https://api.github.com/repos/' + repo + '/' + endpoint,
                                     headers={'Accept': 'application/vnd.github+json',
                                              'X-GitHub-Api-Version': '2022-11-28'})
    if os.environ.get('GITHUB_TOKEN'):
        request.add_header('Authorization', 'Bearer ' + os.environ['GITHUB_TOKEN'])
    with urllib.request.urlopen(request, timeout=15) as response:
        return json.load(response)


def _pages(repo, endpoint, key=None, stop=None):
    rows = []
    for page in range(1, 11):
        data = _api(repo, endpoint + ('&' if '?' in endpoint else '?') + f'per_page=100&page={page}')
        batch = data[key] if key else data
        if not isinstance(batch, list):
            raise ValueError('Unerwartete GitHub-Antwort')
        rows.extend(batch)
        if len(batch) < 100 or (stop and batch and stop(batch[-1])):
            return rows
    raise RuntimeError('Zu viele GitHub-Ergebnisse; Übersicht unvollständig')


def _text(value):
    return html.escape(str(value), quote=False).replace('|', '&#124;').replace('[', '&#91;').replace(']', '&#93;').replace('\n', ' ').replace('\r', ' ')


def _link(item):
    # URLs aus Kennungen bilden, nicht aus frei änderbaren Titeln.
    number = int(item['number'])
    return f'[#{number} {_text(item.get("title", ""))}]'


def _pulls(lines, repo, since):
    pulls = _pages(repo, 'pulls?state=all&sort=updated&direction=desc',
                   stop=lambda p: p['updated_at'] < since)
    recent = [p for p in pulls if p.get('updated_at', '') >= since]
    lines.extend(['', '## GhostWriter-Pull-Requests – letzte 24 Stunden', ''])
    if recent:
        lines.extend(['| PR | Status |', '|---|---|'])
        for pr in recent:
            state = 'gemergt' if pr.get('merged_at') else 'geschlossen' if pr['state'] == 'closed' else 'offen'
            lines.append(f'| {_link(pr)}(https://github.com/{repo}/pull/{int(pr["number"])}) | {state} |')
    else:
        lines.append('Keine aktualisierten Pull Requests im Berichtszeitraum.')
    lines.extend(['', '## Entscheidungen und offene Vorgänge', ''])
    opened = _pages(repo, 'pulls?state=open')
    if not opened:
        lines.append('Keine offenen Pull Requests.')
    for pr in opened:
        number = int(pr['number'])
        try:
            detail = _api(repo, f'pulls/{number}')
            reviews = _pages(repo, f'pulls/{number}/reviews')
            latest = {}
            for review in reviews:
                if review.get('state') in ('APPROVED', 'CHANGES_REQUESTED', 'DISMISSED'):
                    latest[(review.get('user') or {}).get('login')] = review['state']
            state = detail.get('mergeable_state')
            if pr.get('draft'):
                action = 'Entwurf – Fertigstellung ausstehend'
            elif detail.get('mergeable') is False or state == 'dirty':
                action = 'Blockiert – Zusammenführungskonflikt beheben'
            elif 'CHANGES_REQUESTED' in latest.values():
                action = 'Änderungen angefordert – Überarbeitung ausstehend'
            elif state in ('blocked', 'unstable'):
                action = 'Blockiert oder Prüfungen auffällig – Prüfungen und Freigaben ansehen'
            elif detail.get('requested_reviewers') or detail.get('requested_teams'):
                action = 'Review angefordert – Prüfung ausstehend'
            elif state in ('clean', 'has_hooks'):
                action = 'Entscheidung zur Übernahme ausstehend; keine automatische Freigabe'
            else:
                action = 'Offen – Prüf-/Merge-Status noch unbekannt'
        except (OSError, ValueError, RuntimeError, KeyError):
            action = 'Offen – Detailstatus nicht verfügbar'
        lines.append(f'- {_link(pr)}(https://github.com/{repo}/pull/{number}): {action}.')


def _updates(lines, repo, since):
    lines.extend(['', '## Update-Lauf und Automatik', ''])
    paused = os.environ.get('UPDATE_PAUSED') == 'true'
    outcome = os.environ.get('UPDATE_OUTCOME', '')
    if paused and os.environ.get('GITHUB_EVENT_NAME') != 'workflow_dispatch':
        lines.append('Aktueller Lauf: Automatik wegen Limits pausiert; Update übersprungen.')
    else:
        labels = {'success': 'Update-Schritt erfolgreich', 'failure': 'Update-Schritt fehlgeschlagen',
                  'cancelled': 'Update-Schritt abgebrochen', 'skipped': 'Update-Schritt übersprungen'}
        lines.append('Aktueller Lauf: ' + labels.get(outcome, 'Update-Status unbekannt') + '.')
        if paused:
            lines.append('Limitwarnung aktiv; dieser manuelle Lauf durfte trotzdem fortfahren.')
    if os.environ.get('UPDATE_LIMIT_TEXT'):
        lines.append('Limits: ' + _text(os.environ['UPDATE_LIMIT_TEXT']))
    try:
        issues = _pages(repo, 'issues?state=open')
        relevant = [i for i in issues if 'pull_request' not in i and (
            i.get('title') == 'GhostWriter-Automatik pausiert' or
            i.get('title', '').startswith('GhostWriter-Update fehlgeschlagen'))]
        for issue in relevant:
            lines.append(f'- {_link(issue)}(https://github.com/{repo}/issues/{int(issue["number"])}): weiterhin offen.')
        runs = _pages(repo, 'actions/workflows/update.yml/runs?created=%3E%3D' + since,
                      key='workflow_runs')
        failed = [r for r in runs if r.get('conclusion') in ('failure', 'cancelled', 'timed_out', 'action_required')]
        for run in failed:
            lines.append(f'- [Update-Lauf {int(run["id"])}](https://github.com/{repo}/actions/runs/{int(run["id"])}): '
                         + _text(run['conclusion']) + '.')
        if not relevant and not failed:
            lines.append('Keine offenen Update-/Pausenmeldungen und keine fehlgeschlagenen oder abgebrochenen Update-Läufe der letzten 24 Stunden.')
    except (OSError, ValueError, RuntimeError, KeyError):
        lines.append('Frühere Update-/Pausenmeldungen nicht verfügbar; Status unbekannt.')


def append_daily_summary(lines, repo, book_branches, manifest):
    since = (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=1)).strftime('%Y-%m-%dT%H:%M:%SZ')
    lines.extend(['', '## Buchinhalte – letzte 24 Stunden', ''])
    rows = []
    unavailable = book_branches is None or os.environ.get('SUMMARY_BRANCHES_AVAILABLE') == 'false'
    for branch in sorted(set(book_branches or [])) if not unavailable else []:
        try:
            commits, files = _content_activity(branch, content_paths(manifest), since)
            if commits:
                rows.append(f'| {_text(branch)} | {commits} | {files} |')
        except RuntimeError:
            rows.append(f'| {_text(branch)} | unbekannt | unbekannt |')
    if unavailable:
        lines.append('Buchaktivität unbekannt; aktuelle Branch-Daten nicht verfügbar.')
    elif rows:
        lines.extend(['| Buch-Branch | Inhalts-Commits | geänderte Inhaltsdateien |', '|---|---:|---:|', *rows])
    else:
        lines.append('Keine Buchinhaltsänderungen im Berichtszeitraum.')
    upstream = (manifest.get('upstream') or {}).get('repo') or repo
    try:
        _pulls(lines, upstream, since)
    except (OSError, ValueError, RuntimeError, KeyError):
        lines.append('PR-Übersicht nicht verfügbar; Aktivität und Entscheidungen unbekannt.')
    _updates(lines, repo, since)


def main():
    import yaml
    import library
    from pathlib import Path

    lines = ['## Tägliche GitHub-Übersicht']
    try:
        manifest = yaml.safe_load(Path('ghostwriter-manifest.yml').read_text(encoding='utf-8')) or {}
        configs = library.branch_configs()
        default = library.default_branch() or os.environ.get('GHOSTWRITER_DEFAULT_BRANCH') or 'main'
        books = library.books(configs, manifest, default)
        append_daily_summary(lines, os.environ.get('GITHUB_REPOSITORY', ''), [b['branch'] for b in books] if configs else None, manifest)
    except Exception:
        # Berichtsteil darf den Update-Lauf weder scheitern lassen noch Fehlerdetails/Secrets ausgeben.
        lines.append('Tagesbericht nicht vollständig verfügbar; Update-Ergebnis siehe vorherige Zusammenfassung.')
    rendered = '\n'.join(lines) + '\n'
    print(rendered)
    if os.environ.get('GITHUB_STEP_SUMMARY'):
        with open(os.environ['GITHUB_STEP_SUMMARY'], 'a', encoding='utf-8') as stream:
            stream.write(rendered)


if __name__ == '__main__':
    main()
