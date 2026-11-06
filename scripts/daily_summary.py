#!/usr/bin/env python3
"""Lesender Tagesbericht für den vorhandenen Update-Lauf; kein Mailversand."""
import datetime
import re
import html
import json
import os
import subprocess
import urllib.request


from contextvars import ContextVar
try:
    from .i18n import message, resolve_language
except ImportError:
    from i18n import message, resolve_language

LANGUAGE = ContextVar('ghostwriter_report_language', default='de')


def tr(key, **values):
    return message(LANGUAGE.get(), key, **values)


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


def _content_text(text, name):
    """Verwaltungsfelder nur in Frontmatter und bekannten Kapitelübersichten ausblenden."""
    import yaml

    metadata = ''
    lines = text.splitlines(keepends=True)
    if name.endswith('.md') and lines and lines[0].strip() == '---':
        end = next((i for i in range(1, len(lines)) if lines[i].strip() == '---'), None)
        if end is None:
            raise RuntimeError('Frontmatter nicht lesbar')
        try:
            header = yaml.safe_load(''.join(lines[1:end])) or {}
            if not isinstance(header, dict):
                raise RuntimeError('Frontmatter nicht lesbar')
            for field in ('status', 'approvals', 'approved_at', 'approved_by', 'updated_at', 'last_modified'):
                header.pop(field, None)
            metadata = yaml.safe_dump(header, allow_unicode=True, sort_keys=True) if header else ''
        except yaml.YAMLError as exc:
            raise RuntimeError('Frontmatter nicht lesbar') from exc
        text = ''.join(lines[end + 1:])
    if name.startswith('chapters/') and name.endswith('/README.md'):
        result, status_section, status_table = [], False, False
        for line in text.splitlines(keepends=True):
            if line.startswith('## '):
                status_section = line.strip() == '## Kapitelstatus'
                status_table = False
            if status_section:
                continue
            cells = [cell.strip() for cell in line.strip().strip('|').split('|')]
            if cells == ['Nummer', 'Abschnitt', 'Status']:
                status_table = True
            elif not line.lstrip().startswith('|'):
                status_table = False
            if status_table and len(cells) == 3:
                line = '| ' + ' | '.join(cells[:2]) + ' |\n'
            result.append(line)
        text = ''.join(result)
    return metadata + text


def _file_text(revision, name):
    if revision is None or not _git('ls-tree', '--name-only', revision, '--', name).strip():
        return ''
    return _git('show', revision + ':' + name)


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
            before = _file_text(parents[0] if parents else None, name)
            after = _file_text(commit, name)
            if _content_text(before, name) != _content_text(after, name):
                changed.add(name)
        if changed:
            count += 1
            files.update(changed)
    return count, len(files)


def _api(repo, endpoint, method="GET", data=None):
    request = urllib.request.Request('https://api.github.com/repos/' + repo + '/' + endpoint,
                                     method=method, data=json.dumps(data).encode('utf-8') if data is not None else None,
                                     headers={'Content-Type': 'application/json', 'Accept': 'application/vnd.github+json',
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
    lines.extend(['', tr('report.pulls'), ''])
    if recent:
        lines.extend([tr('report.pr_table'), '|---|---|'])
        for pr in recent:
            state = tr('status.merged') if pr.get('merged_at') else tr('status.closed') if pr['state'] == 'closed' else tr('status.open')
            lines.append(f'| {_link(pr)}(https://github.com/{repo}/pull/{int(pr["number"])}) | {state} |')
    else:
        lines.append(tr('report.no_pulls'))
    lines.extend(['', tr('report.decisions'), ''])
    opened = _pages(repo, 'pulls?state=open')
    if not opened:
        lines.append(tr('report.no_open_pulls'))
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
                action = tr('decision.draft')
            elif detail.get('mergeable') is False or state == 'dirty':
                action = tr('decision.conflict')
            elif 'CHANGES_REQUESTED' in latest.values():
                action = tr('decision.changes')
            elif state in ('blocked', 'unstable'):
                action = tr('decision.blocked')
            elif detail.get('requested_reviewers') or detail.get('requested_teams'):
                action = tr('decision.review')
            elif state in ('clean', 'has_hooks'):
                action = tr('decision.merge')
            else:
                action = tr('decision.unknown')
        except (OSError, ValueError, RuntimeError, KeyError):
            action = tr('decision.unavailable')
        lines.append(f'- {_link(pr)}(https://github.com/{repo}/pull/{number}): {action}.')


def _updates(lines, repo, since):
    lines.extend(['', tr('report.updates'), ''])
    paused = os.environ.get('UPDATE_PAUSED') == 'true'
    outcome = os.environ.get('UPDATE_OUTCOME', '')
    if paused and os.environ.get('GITHUB_EVENT_NAME') != 'workflow_dispatch':
        lines.append(tr('update.paused'))
    else:
        labels = {'success': tr('update.success'), 'failure': tr('update.failure'),
                  'cancelled': tr('update.cancelled'), 'skipped': tr('update.skipped')}
        lines.append(tr('update.current') + labels.get(outcome, tr('update.unknown')) + '.')
        if paused:
            lines.append(tr('update.manual_warning'))
    if os.environ.get('UPDATE_LIMIT_TEXT'):
        lines.append(tr('update.limits') + _text(os.environ['UPDATE_LIMIT_TEXT']))
    try:
        issues = _pages(repo, 'issues?state=open')
        relevant = [i for i in issues if 'pull_request' not in i and (
            i.get('title') == 'GhostWriter-Automatik pausiert' or
            i.get('title', '').startswith('GhostWriter-Update fehlgeschlagen'))]
        for issue in relevant:
            lines.append(f'- {_link(issue)}(https://github.com/{repo}/issues/{int(issue["number"])}): {tr("status.still_open")}')
        runs = _pages(repo, 'actions/workflows/update.yml/runs?created=%3E%3D' + since,
                      key='workflow_runs')
        failed = [r for r in runs if r.get('conclusion') in ('failure', 'cancelled', 'timed_out', 'action_required')]
        for run in failed:
            lines.append(f'- [{tr("update.run")} {int(run["id"])}](https://github.com/{repo}/actions/runs/{int(run["id"])}): '
                         + _text(run['conclusion']) + '.')
        if not relevant and not failed:
            lines.append(tr('update.no_problems'))
    except (OSError, ValueError, RuntimeError, KeyError):
        lines.append(tr('update.unavailable'))


def append_daily_summary(lines, repo, book_branches, manifest):
    since = (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=1)).strftime('%Y-%m-%dT%H:%M:%SZ')
    lines.extend(['', tr('report.books'), ''])
    rows = []
    unavailable = book_branches is None or os.environ.get('SUMMARY_BRANCHES_AVAILABLE') == 'false'
    for branch in sorted(set(book_branches or [])) if not unavailable else []:
        try:
            commits, files = _content_activity(branch, content_paths(manifest), since)
            if commits:
                rows.append(f'| {_text(branch)} | {commits} | {files} |')
        except RuntimeError:
            rows.append(f'| {_text(branch)} | {tr("status.unknown")} | {tr("status.unknown")} |')
    if unavailable:
        lines.append(tr('report.books_unknown'))
    elif rows:
        lines.extend([tr('report.books_table'), '|---|---:|---:|', *rows])
    else:
        lines.append(tr('report.no_books'))
    upstream = (manifest.get('upstream') or {}).get('repo') or repo
    try:
        _pulls(lines, upstream, since)
    except (OSError, ValueError, RuntimeError, KeyError):
        lines.append(tr('report.pr_unavailable'))
    _updates(lines, repo, since)


REPORT_ISSUE_MARKER = '<!-- ghostwriter:daily-report -->'


def publish_daily_report(repo, rendered, recipient, day=None):
    """Genau einen neuen Tageskommentar je UTC-Datum anlegen, nie bestehende ändern."""
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9-]*', recipient or ''):
        raise ValueError('Empfänger fehlt oder ist ungültig')
    day = day or datetime.datetime.now(datetime.timezone.utc).date().isoformat()
    marker = f'<!-- ghostwriter:daily-report:{day} -->'
    issues = _pages(repo, 'issues?state=all')
    issue = next((i for i in issues if 'pull_request' not in i and
                  REPORT_ISSUE_MARKER in (i.get('body') or '')), None)
    if issue and issue.get('state') == 'closed':
        return tr('delivery.paused')
    if issue:
        number = int(issue['number'])
        comments = _pages(repo, f'issues/{number}/comments')
        if any(marker in (c.get('body') or '') for c in comments):
            return tr('delivery.duplicate')
    # GitHubs Kommentargrenze niemals durch Kürzen oder mehrere Kommentare umgehen.
    run_id = os.environ.get('GITHUB_RUN_ID', '')
    run_link = f'\n\n[{tr("update.run")}](https://github.com/{repo}/actions/runs/{int(run_id)})' if run_id.isdigit() else ''
    body = f'{marker}\n# {tr("delivery.heading", day=day)}\n\n@{recipient}\n\n{rendered}{run_link}'
    if len(body.encode('utf-8')) > 65000:
        raise ValueError('Vollständiger Bericht ist zu groß für einen Issue-Kommentar')
    if not issue:
        issue = _api(repo, 'issues', method='POST', data={
            'title': tr('delivery.issue_title'),
            'body': REPORT_ISSUE_MARKER + '\n' + tr('delivery.body')})
        number = int(issue['number'])
    _api(repo, f'issues/{number}/comments', method='POST', data={'body': body})
    return tr('delivery.sent', number=number)


def _main():
    import yaml
    import library
    from pathlib import Path

    lines = [tr('report.title')]
    try:
        manifest = yaml.safe_load(Path('ghostwriter-manifest.yml').read_text(encoding='utf-8')) or {}
        configs = library.branch_configs()
        default = library.default_branch() or os.environ.get('GHOSTWRITER_DEFAULT_BRANCH') or 'main'
        books = library.books(configs, manifest, default)
        append_daily_summary(lines, os.environ.get('GITHUB_REPOSITORY', ''), [b['branch'] for b in books] if configs else None, manifest)
    except Exception:
        # Berichtsteil darf den Update-Lauf weder scheitern lassen noch Fehlerdetails/Secrets ausgeben.
        lines.append(tr('report.partial'))
    rendered = '\n'.join(lines) + '\n'
    print(rendered)
    if os.environ.get('GITHUB_STEP_SUMMARY'):
        with open(os.environ['GITHUB_STEP_SUMMARY'], 'a', encoding='utf-8') as stream:
            stream.write(rendered)
    if os.environ.get('DAILY_REPORT_SEND') == 'true':
        try:
            from pathlib import Path
            update_path = os.environ.get('DAILY_UPDATE_REPORT_PATH')
            update_report = Path(update_path).read_text(encoding='utf-8') if update_path and Path(update_path).exists() else ''
            print(publish_daily_report(os.environ.get('GITHUB_REPOSITORY', ''), update_report + '\n' + rendered,
                                       os.environ.get('DAILY_REPORT_RECIPIENT', '')))
        except Exception:
            warning = '\n' + tr('delivery.warning') + '\n'
            print('::warning::' + tr('delivery.annotation'))
            if os.environ.get('GITHUB_STEP_SUMMARY'):
                with open(os.environ['GITHUB_STEP_SUMMARY'], 'a', encoding='utf-8') as stream:
                    stream.write(warning)


def main(language=None):
    import yaml
    from pathlib import Path
    try:
        config = yaml.safe_load(Path('ghostwriter.yml').read_text(encoding='utf-8')) or {}
    except (OSError, yaml.YAMLError):
        config = {}
    profile = {}
    default = os.environ.get('GHOSTWRITER_DEFAULT_BRANCH', 'main')
    try:
        profile = yaml.safe_load(_git('show', f'refs/remotes/origin/{default}:assistant.yml')) or {}
    except (RuntimeError, yaml.YAMLError):
        pass
    token = LANGUAGE.set(resolve_language(language or os.environ.get('GHOSTWRITER_INTERFACE_LANGUAGE'), config, profile))
    try:
        _main()
    finally:
        LANGUAGE.reset(token)


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--language', help='Bediensprache, z. B. de oder en; unabhängig von der Buchsprache')
    main(parser.parse_args().language)
