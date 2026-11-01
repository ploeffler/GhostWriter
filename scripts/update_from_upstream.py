#!/usr/bin/env python3
"""Spielt GhostWriter-Updates aus dem Hauptrepository in Buch-Branches ein.

Aufruf (in der Action „GhostWriter aktualisieren“, .github/workflows/update.yml):
  python scripts/update_from_upstream.py [--dry-run] [--branch NAME]

Ablauf je Buch-Branch:
  1. Upstream (ghostwriter-manifest.yml: upstream.repo, upstream.ref) holen.
  2. Nichts tun, wenn das Buch schon auf diesem Stand ist, Updates abgeschaltet
     sind (ghostwriter.yml: updates.auto: false) oder das Buch eine neuere
     Programmversion hat als der Upstream (kein Zurücksetzen).
  3. Die Programmdateien (manifest: managed) durch den Upstream-Stand ersetzen;
     Buchdateien (manifest: book) bleiben unangetastet.
  4. Migrationen (scripts/migrate_project.py), Übersichtsdatei
     (scripts/build_index.py) und Prüfung (scripts/validate_project.py) mit dem
     neuen Stand ausführen. Schlägt die Prüfung fehl, wird nichts eingespielt.
  5. Ein Commit „GhostWriter aktualisiert auf <version>“ mit
     „GhostWriter-Aktion: update“; Stand in .ghostwriter/update.yml.

Welche Branches: In einem eigenen Buch-Repository der Standard-Branch. Liegt
das Buch im Hauptrepository selbst (Testbuch), alle Branches mit Kapiteln außer
update.skip_branches.

Umgebung:
  GITHUB_REPOSITORY        owner/repo dieses Repositorys
  GITHUB_TOKEN             Token der Action (lesen/schreiben dieses Repositorys, Issues)
  GHOSTWRITER_UPDATE_TOKEN optional: Token mit Leserecht auf ein privates Hauptrepository
                           und Workflow-Schreibrecht; ohne ihn bleiben Änderungen an
                           .github/workflows/ aus und werden gemeldet
  GHOSTWRITER_UPSTREAM_URL nur für Tests: Git-URL des Upstreams statt GitHub
  GITHUB_STEP_SUMMARY      optional: Zusammenfassung für die Action
"""
import argparse
import datetime
import fnmatch
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.request
from pathlib import Path

import yaml

MANIFEST = 'ghostwriter-manifest.yml'
STATE = '.ghostwriter/update.yml'
WORKFLOWS = '.github/workflows/'
TRAILER = 'GhostWriter-Aktion: update'
ISSUE_TITLE = 'GhostWriter-Update fehlgeschlagen ({branch})'


def git(*args, cwd=None, check=True, capture=True):
    r = subprocess.run(['git', *args], cwd=cwd, text=True, capture_output=capture)
    if check and r.returncode:
        raise RuntimeError(f'git {" ".join(args)}: {r.stderr.strip() or r.stdout.strip()}')
    return r.stdout.strip() if capture else ''


def show(rev, path, cwd=None):
    r = subprocess.run(['git', 'show', f'{rev}:{path}'], cwd=cwd, text=True, capture_output=True)
    return r.stdout if r.returncode == 0 else None


def version_tuple(v):
    nums = [int(x) for x in re.findall(r'\d+', str(v or '0'))[:3]]
    return tuple(nums + [0] * (3 - len(nums)))


def summary(lines):
    path = os.environ.get('GITHUB_STEP_SUMMARY')
    text = '\n'.join(lines) + '\n'
    print(text)
    if path:
        with open(path, 'a', encoding='utf-8') as f:
            f.write(text)


# ---------- GitHub-Issues bei Fehlern ----------

def api(method, url, data=None):
    token = os.environ.get('GITHUB_TOKEN')
    repo = os.environ.get('GITHUB_REPOSITORY')
    if not token or not repo:
        return None
    req = urllib.request.Request(f'https://api.github.com/repos/{repo}{url}', method=method,
                                 data=json.dumps(data).encode() if data is not None else None,
                                 headers={'Authorization': f'Bearer {token}', 'Accept': 'application/vnd.github+json'})
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return json.loads(r.read() or b'null')
    except Exception as e:  # Meldungen sind Zusatz; ein Fehler hier bricht das Update nicht ab
        print(f'::warning::GitHub-API {method} {url}: {e}')
        return None


def find_issue(title):
    for issue in api('GET', '/issues?state=open&per_page=100') or []:
        if issue.get('title') == title and 'pull_request' not in issue:
            return issue
    return None


def report_failure(branch, text):
    title = ISSUE_TITLE.format(branch=branch)
    issue = find_issue(title)
    if issue:
        api('POST', f'/issues/{issue["number"]}/comments', {'body': text})
    else:
        api('POST', '/issues', {'title': title, 'body': text})


def report_success(branch, text):
    issue = find_issue(ISSUE_TITLE.format(branch=branch))
    if issue:
        api('POST', f'/issues/{issue["number"]}/comments', {'body': text})
        api('PATCH', f'/issues/{issue["number"]}', {'state': 'closed'})


# ---------- Update eines Branchs ----------

def managed_paths(manifest):
    return [p for p in manifest.get('managed') or []]


def apply_update(wt, upstream_rev, manifest, can_workflows):
    """Ersetzt die Programmdateien im Worktree; gibt (geändert, ausgelassene Workflow-Dateien) zurück."""
    for p in managed_paths(manifest):
        git('rm', '-r', '-q', '--ignore-unmatch', '--', p.rstrip('/'), cwd=wt)
        if subprocess.run(['git', 'cat-file', '-e', f'{upstream_rev}:{p.rstrip("/")}'], cwd=wt,
                          capture_output=True).returncode == 0:
            git('checkout', upstream_rev, '--', p.rstrip('/'), cwd=wt)
    skipped = []
    if not can_workflows:
        changed = git('diff', '--cached', '--name-only', 'HEAD', '--', WORKFLOWS, cwd=wt).splitlines()
        if changed:
            skipped = changed
            git('reset', '-q', 'HEAD', '--', WORKFLOWS, cwd=wt)
            git('checkout', 'HEAD', '--', WORKFLOWS, cwd=wt, check=False)
            git('clean', '-fdq', '--', WORKFLOWS, cwd=wt)
    return skipped


def run(cmd, wt):
    r = subprocess.run([sys.executable, *cmd], cwd=wt, text=True, capture_output=True)
    return r.returncode, (r.stdout + r.stderr).strip()


def update_branch(branch, upstream_rev, up_manifest, args, can_workflows):
    """Gibt (status, text) zurück; status: updated | current | skipped | failed."""
    base_rev = f'origin/{branch}'
    config = yaml.safe_load(show(base_rev, 'ghostwriter.yml') or '{}') or {}
    if (config.get('updates') or {}).get('auto') is False:
        return 'skipped', 'automatische Updates abgeschaltet (ghostwriter.yml: updates.auto: false)'
    state = yaml.safe_load(show(base_rev, STATE) or '{}') or {}
    up_sha = git('rev-parse', upstream_rev)
    if state.get('commit') == up_sha and not (state.get('skipped_workflows') and can_workflows):
        return 'current', f'aktuell ({up_manifest.get("version")}, {up_sha[:7]})'
    own = yaml.safe_load(show(base_rev, MANIFEST) or '{}') or {}
    if version_tuple(own.get('version')) > version_tuple(up_manifest.get('version')):
        return 'skipped', f'Buch hat neuere Programmversion ({own.get("version")}) als der Upstream ({up_manifest.get("version")})'

    wt = tempfile.mkdtemp(prefix='gw-update-')
    try:
        git('worktree', 'add', '-q', '--detach', wt, base_rev)
        skipped = apply_update(wt, upstream_rev, up_manifest, can_workflows)
        steps = []
        for cmd in (['scripts/migrate_project.py', '.'], ['scripts/build_index.py', '.'], ['scripts/validate_project.py', '.']):
            if not (Path(wt) / cmd[0]).is_file():
                continue
            code, out = run(cmd, wt)
            steps.append(f'$ python {" ".join(cmd)}\n{out}')
            if code:
                return 'failed', (f'Prüfung mit GhostWriter {up_manifest.get("version")} ({up_sha[:7]}) fehlgeschlagen; '
                                  f'das Update wurde nicht eingespielt.\n\n```\n' + '\n\n'.join(steps)[-6000:] + '\n```')
        state_path = Path(wt) / STATE
        state_path.parent.mkdir(parents=True, exist_ok=True)
        state_path.write_text(yaml.safe_dump({
            'upstream': f'{up_manifest.get("upstream", {}).get("repo")}@{up_manifest.get("upstream", {}).get("ref")}',
            'version': str(up_manifest.get('version')), 'commit': up_sha,
            'updated_at': datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
            'skipped_workflows': skipped,
        }, allow_unicode=True, sort_keys=False), encoding='utf-8')
        git('add', '-A', cwd=wt)
        files = git('diff', '--cached', '--name-only', cwd=wt).splitlines()
        msg = f'GhostWriter aktualisiert auf {up_manifest.get("version")} ({up_sha[:7]})'
        body = [f'{len(files)} Dateien.']
        if skipped:
            body.append('Nicht aktualisiert (Workflow-Dateien brauchen GHOSTWRITER_UPDATE_TOKEN): ' + ', '.join(skipped))
        if args.dry_run:
            return 'updated', f'(Probelauf) {msg}: ' + ', '.join(files[:20]) + (' …' if len(files) > 20 else '')
        git('-c', 'user.name=github-actions[bot]', '-c', 'user.email=41898282+github-actions[bot]@users.noreply.github.com',
            'commit', '-q', '-m', msg, '-m', '\n'.join(body), '-m', TRAILER, cwd=wt)
        push = subprocess.run(['git', 'push', 'origin', f'HEAD:refs/heads/{branch}'], cwd=wt, text=True, capture_output=True)
        if push.returncode:
            return 'failed', f'Push nach {branch} abgelehnt; nächster Lauf versucht es erneut.\n\n```\n{push.stderr.strip()[-2000:]}\n```'
        text = f'{msg}, {len(files)} Dateien.'
        if skipped:
            text += f' ⚠️ {len(skipped)} Workflow-Datei(en) nicht aktualisiert: Secret GHOSTWRITER_UPDATE_TOKEN fehlt (docs/UPDATES.md).'
        return 'updated', text
    finally:
        subprocess.run(['git', 'worktree', 'remove', '--force', wt], capture_output=True)
        shutil.rmtree(wt, ignore_errors=True)


# ---------- Ablauf ----------

def target_branches(manifest, same_repo, upstream_ref, only):
    if only:
        return [only]
    if not same_repo:
        head = git('symbolic-ref', '-q', '--short', 'refs/remotes/origin/HEAD', check=False)
        return [head.split('/', 1)[1] if head else os.environ.get('GITHUB_REF_NAME', 'main')]
    skip = (manifest.get('update') or {}).get('skip_branches') or []
    out = []
    for ref in git('for-each-ref', '--format=%(refname:short)', 'refs/remotes/origin').splitlines():
        name = ref.split('/', 1)[1] if '/' in ref else ref
        if name in ('HEAD', upstream_ref) or any(fnmatch.fnmatch(name, pat) for pat in skip):
            continue
        cfg = yaml.safe_load(show(ref, 'ghostwriter.yml') or '{}') or {}
        if ((cfg.get('structure') or {}).get('chapters')):
            out.append(name)
    return out


def main(argv):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--dry-run', action='store_true', help='nichts committen oder pushen')
    ap.add_argument('--branch', help='nur diesen Buch-Branch')
    args = ap.parse_args(argv[1:])

    manifest = yaml.safe_load(Path(MANIFEST).read_text(encoding='utf-8'))
    up = manifest.get('upstream') or {}
    repo, ref = up.get('repo'), up.get('ref', 'main')
    here = os.environ.get('GITHUB_REPOSITORY', '')
    same_repo = repo == here and not os.environ.get('GHOSTWRITER_UPSTREAM_URL')
    token = os.environ.get('GHOSTWRITER_UPDATE_TOKEN') or ''
    can_workflows = bool(token)

    git('fetch', '-q', '--prune', 'origin', '+refs/heads/*:refs/remotes/origin/*')
    if same_repo:
        upstream_rev = f'origin/{ref}'
    else:
        url = os.environ.get('GHOSTWRITER_UPSTREAM_URL') or \
            f'https://x-access-token:{token or os.environ.get("GITHUB_TOKEN", "")}@github.com/{repo}.git'
        r = subprocess.run(['git', 'fetch', '-q', url, f'+{ref}:refs/ghostwriter/upstream'], text=True, capture_output=True)
        if r.returncode:
            msg = (f'Hauptrepository {repo} ({ref}) nicht erreichbar. Ist es privat, braucht dieses Repository das Secret '
                   f'GHOSTWRITER_UPDATE_TOKEN mit Leserecht darauf (docs/UPDATES.md).')
            summary(['## GhostWriter-Update', '', f'❌ {msg}'])
            report_failure(target_branches(manifest, False, ref, args.branch)[0], msg)
            return 1
        upstream_rev = 'refs/ghostwriter/upstream'

    up_manifest = yaml.safe_load(show(upstream_rev, MANIFEST) or 'null')
    if not up_manifest:
        summary(['## GhostWriter-Update', '', f'Upstream {repo}@{ref} hat noch kein {MANIFEST}; nichts zu tun.'])
        return 0

    lines = ['## GhostWriter-Update', '', f'Upstream: `{repo}@{ref}` · Version {up_manifest.get("version")} · '
             f'`{git("rev-parse", "--short", upstream_rev)}`', '', '| Branch | Ergebnis |', '|---|---|']
    icon = {'updated': '✅', 'current': '✔️', 'skipped': '⏭️', 'failed': '❌'}
    failed = False
    for branch in target_branches(manifest, same_repo, ref, args.branch):
        try:
            status, text = update_branch(branch, upstream_rev, up_manifest, args, can_workflows)
        except RuntimeError as e:
            status, text = 'failed', str(e)
        lines.append(f'| `{branch}` | {icon[status]} {text.splitlines()[0]} |')
        if status == 'failed':
            failed = True
            if not args.dry_run:
                report_failure(branch, text)
        elif status == 'updated' and not args.dry_run:
            report_success(branch, f'Behoben: {text}')
    summary(lines)
    return 1 if failed else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
