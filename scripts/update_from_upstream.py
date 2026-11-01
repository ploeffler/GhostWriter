#!/usr/bin/env python3
"""Hält Forks und Buch-Branches auf dem Stand des GhostWriter-Hauptrepositorys.

Aufruf (in der Action „GhostWriter aktualisieren“, .github/workflows/update.yml):
  python scripts/update_from_upstream.py [--dry-run] [--branch NAME] [--status FILE]

Wie GitHubs „Sync fork“, aber sicher für Bücher. Für jeden Branch wird gezählt,
wie viele Commits er hinter seinem Gegenstück im Hauptrepository liegt
(gleichnamiger Branch, sonst upstream.ref aus ghostwriter-manifest.yml).
Liegt er dahinter, werden die Commits eingespielt:

  - Hat der Branch keine eigenen Commits: Fast-Forward, danach ist er identisch.
  - Sonst ein Merge-Commit. Konflikte löst er nach dem Manifest: Programmdateien
    (managed) nimmt er vom Hauptrepository, Buchdateien (book) bleiben wie im
    Buch, auch wenn das Hauptrepository die Vorlagen geändert hat. Konflikte in
    anderen Dateien brechen das Update für diesen Branch ab.
  - Danach Migrationen (scripts/migrate_project.py), Übersichtsdatei und
    Prüfung (scripts/validate_project.py). Schlägt die Prüfung fehl, wird
    nichts eingespielt, sondern ein Issue „GhostWriter-Update fehlgeschlagen“
    geöffnet. Ein Buch wird nie auf eine ältere Programmversion zurückgesetzt.

Danach liegt kein Branch mehr hinter dem Hauptrepository; GitHubs Hinweis
„This branch is N commits behind …“ verschwindet.

Welche Branches: im Fork bzw. eigenen Buch-Repository alle Branches. Im
Hauptrepository selbst nur Bücher nach der Erkennungsregel aus scripts/library.py
(buch/*-Branches, sonst Branches mit Kapiteln wie test/test-book), nie
update.skip_branches.

--status FILE schreibt je Branch behind/ahead/Ergebnis als JSON (für Tests und
die Projektübersicht).

Umgebung:
  GITHUB_REPOSITORY        owner/repo dieses Repositorys
  GITHUB_TOKEN             Token der Action (dieses Repository, Issues)
  GITHUB_EVENT_PATH        Ereignis der Action (Standard-Branch)
  GHOSTWRITER_UPDATE_TOKEN optional: Leserecht auf ein privates Hauptrepository und
                           Workflow-Schreibrecht; ohne ihn bleiben Änderungen an
                           .github/workflows/ aus und werden gemeldet
  GHOSTWRITER_UPSTREAM_URL nur für Tests: Git-URL des Hauptrepositorys
  GITHUB_STEP_SUMMARY      optional: Zusammenfassung für die Action
"""
import argparse
import datetime
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

sys.path.insert(0, str(Path(__file__).resolve().parent))
import library  # noqa: E402  Erkennungsregel der Bibliothek

MANIFEST = 'ghostwriter-manifest.yml'
STATE = '.ghostwriter/update.yml'
WORKFLOWS = '.github/workflows'
TRAILER = 'GhostWriter-Aktion: update'
ISSUE_TITLE = 'GhostWriter-Update fehlgeschlagen ({branch})'
BOT = ['-c', 'user.name=github-actions[bot]', '-c', 'user.email=41898282+github-actions[bot]@users.noreply.github.com']


def git(*args, cwd=None, check=True):
    r = subprocess.run(['git', *args], cwd=cwd, text=True, capture_output=True)
    if check and r.returncode:
        raise RuntimeError(f'git {" ".join(args)}: {r.stderr.strip() or r.stdout.strip()}')
    return r.stdout.strip()


def exists(rev, path, cwd=None):
    return subprocess.run(['git', 'cat-file', '-e', f'{rev}:{path}'], cwd=cwd, capture_output=True).returncode == 0


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
                                 headers={'Authorization': f'Bearer {token}', 'Accept': 'application/vnd.github+json',
                                          'Content-Type': 'application/json', 'X-GitHub-Api-Version': '2022-11-28'})
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




# ---------- Pfade nach Manifest ----------

def under(path, prefixes):
    return any(path == p.rstrip('/') or path.startswith(p.rstrip('/') + '/') for p in prefixes)


def resolve_paths(wt, up_rev, manifest, can_workflows):
    """Nach dem Merge: Programmdateien vom Hauptrepository, Buchdateien wie im Buch.
    Gibt (ungelöste Konflikte, ausgelassene Workflow-Dateien) zurück."""
    managed = [p for p in manifest.get('managed') or []]
    book = [p for p in manifest.get('book') or []]
    if not can_workflows:
        managed = [p for p in managed if not under(WORKFLOWS, [p]) and p.rstrip('/') != WORKFLOWS]
    # Programmdateien: genau der Stand des Hauptrepositorys
    for p in managed:
        p = p.rstrip('/')
        git('rm', '-r', '-q', '--cached', '--ignore-unmatch', '--', p, cwd=wt)
        shutil.rmtree(Path(wt) / p, ignore_errors=True) if (Path(wt) / p).is_dir() else (Path(wt) / p).unlink(missing_ok=True)
        if exists(up_rev, p, wt):
            git('checkout', up_rev, '--', p, cwd=wt)
    # Buchdateien: wie vor dem Update
    for p in book:
        p = p.rstrip('/')
        if exists('HEAD', p, wt):
            git('rm', '-r', '-q', '--cached', '--ignore-unmatch', '--', p, cwd=wt)
            git('checkout', 'HEAD', '--', p, cwd=wt)
    # Workflow-Dateien ohne Token: wie vor dem Update
    skipped = []
    if not can_workflows:
        skipped = [f for f in git('diff', '--name-only', 'HEAD', up_rev, '--', WORKFLOWS, cwd=wt).splitlines() if f]
        git('rm', '-r', '-q', '--cached', '--ignore-unmatch', '--', WORKFLOWS, cwd=wt)
        shutil.rmtree(Path(wt) / WORKFLOWS, ignore_errors=True)
        if exists('HEAD', WORKFLOWS, wt):
            git('checkout', 'HEAD', '--', WORKFLOWS, cwd=wt)
    unresolved = [f for f in git('diff', '--name-only', '--diff-filter=U', cwd=wt).splitlines() if f]
    return unresolved, skipped


def run(cmd, wt):
    r = subprocess.run([sys.executable, *cmd], cwd=wt, text=True, capture_output=True)
    return r.returncode, (r.stdout + r.stderr).strip()


def commits(n):
    return f'{n} Commit' + ('' if n == 1 else 's')


def counts(base, up):
    behind = int(git('rev-list', '--count', f'{base}..{up}'))
    ahead = int(git('rev-list', '--count', f'{up}..{base}'))
    return behind, ahead


def update_branch(branch, up_rev, up_label, up_manifest, args, can_workflows):
    """Gibt ein dict mit behind, ahead, status (updated|current|skipped|failed) und text zurück."""
    base = f'origin/{branch}'
    # Repository aus dem Template (oder Import) teilt keine Historie mit dem Hauptrepository:
    # dann wird nicht gemergt, sondern der Stand aus .ghostwriter/update.yml verglichen.
    related = bool(git('merge-base', base, up_rev, check=False))
    if related:
        behind, ahead = counts(base, up_rev)
    else:
        last = (yaml.safe_load(show(base, STATE) or '{}') or {}).get('commit')
        if last and git('cat-file', '-t', last, check=False) == 'commit':
            behind = int(git('rev-list', '--count', f'{last}..{up_rev}'))
        else:
            behind = 0 if last == git('rev-parse', up_rev) else 1
        ahead = None
    res = {'branch': branch, 'upstream': up_label, 'behind': behind, 'ahead': ahead}
    version = up_manifest.get('version')
    up_sha = git('rev-parse', up_rev)
    managed = [m.rstrip('/') for m in up_manifest.get('managed') or []]
    if not can_workflows:
        managed = [m for m in managed if m != WORKFLOWS]
    drift = [f for f in git('diff', '--name-only', base, up_rev, '--', *managed).splitlines() if f] if managed else []
    if behind == 0 and not drift:
        return {**res, 'status': 'current', 'text': f'aktuell, nicht hinter {up_label}'}
    config = yaml.safe_load(show(base, 'ghostwriter.yml') or '{}') or {}
    if (config.get('updates') or {}).get('auto') is False:
        return {**res, 'status': 'skipped', 'text': f'{commits(behind)} hinter {up_label}; automatische Updates abgeschaltet'}
    own = yaml.safe_load(show(base, MANIFEST) or '{}') or {}
    if own and version_tuple(own.get('version')) > version_tuple(version):
        return {**res, 'status': 'skipped',
                'text': f'{commits(behind)} hinter {up_label}, aber neuere Programmversion ({own.get("version")} > {version}); kein Zurücksetzen'}
    workflows_differ = bool(git('diff', '--name-only', base, up_rev, '--', WORKFLOWS))
    if not up_manifest and not (related and ahead == 0 and (can_workflows or not workflows_differ)):
        return {**res, 'status': 'skipped',
                'text': f'{commits(behind)} hinter {up_label}; dort gibt es kein {MANIFEST}, daher nur von Hand zusammenführen'}

    # Ohne eigene Commits: Fast-Forward wie „Sync fork“
    if related and ahead == 0 and (can_workflows or not workflows_differ):
        if args.dry_run:
            return {**res, 'status': 'updated', 'text': f'(Probelauf) Fast-Forward um {commits(behind)} auf {up_label}'}
        push = subprocess.run(['git', 'push', 'origin', f'{up_sha}:refs/heads/{branch}'], text=True, capture_output=True)
        if push.returncode:
            return {**res, 'status': 'failed', 'text': f'Push nach {branch} abgelehnt.\n\n```\n{push.stderr.strip()[-2000:]}\n```'}
        return {**res, 'status': 'updated', 'text': f'{commits(behind)} von {up_label} übernommen (Fast-Forward)'}

    wt = tempfile.mkdtemp(prefix='gw-update-')
    try:
        git('worktree', 'add', '-q', '--detach', wt, base)
        if behind and related:
            subprocess.run(['git', *BOT, 'merge', '--no-ff', '--no-commit', '-X', 'theirs', up_rev],
                           cwd=wt, text=True, capture_output=True)
        unresolved, skipped = resolve_paths(wt, up_rev, up_manifest, can_workflows)
        if unresolved:
            return {**res, 'status': 'failed',
                    'text': f'{commits(behind)} hinter {up_label}; Konflikt in Dateien, die weder Programm noch Buch sind: '
                            + ', '.join(unresolved) + '. Bitte von Hand zusammenführen.'}
        steps, migration = [], {}
        if (Path(wt) / 'ghostwriter.yml').is_file():
            for cmd in (['scripts/migrate_project.py', '.'], ['scripts/build_index.py', '.'], ['scripts/validate_project.py', '.']):
                if not (Path(wt) / cmd[0]).is_file():
                    continue
                code, out = run(cmd, wt)
                steps.append(f'$ python {" ".join(cmd)}\n{out}')
                if cmd[0].endswith('migrate_project.py') and not code:
                    changes = [l[len('migriert: '):] for l in out.splitlines() if l.startswith('migriert: ')]
                    m = re.search(r'Datenversion (\d+) → (\d+)', out)
                    if changes or m:
                        migration = {'from': int(m.group(1)) if m else None, 'to': int(m.group(2)) if m else None,
                                     'changes': changes,
                                     'at': datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')}
                if code:
                    return {**res, 'status': 'failed',
                            'text': (f'{commits(behind)} hinter {up_label}; Prüfung mit GhostWriter {version} ({up_sha[:7]}) '
                                     'fehlgeschlagen, das Update wurde nicht eingespielt.\n\n```\n'
                                     + '\n\n'.join(steps)[-6000:] + '\n```')}
            state_path = Path(wt) / STATE
            state_path.parent.mkdir(parents=True, exist_ok=True)
            state_path.write_text(yaml.safe_dump({
                'upstream': up_label, 'version': str(version), 'commit': up_sha,
                'updated_at': datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
                'skipped_workflows': skipped,
                **({'migration': migration} if migration else {})}, allow_unicode=True, sort_keys=False), encoding='utf-8')
        git('add', '-A', cwd=wt)
        files = [f for f in git('diff', '--cached', '--name-only', 'HEAD', cwd=wt).splitlines() if f]
        msg = f'GhostWriter aktualisiert auf {version} ({up_sha[:7]})'
        body = [f'{commits(behind)} von {up_label} eingespielt, {len(files)} Dateien geändert.' if behind else
                f'Programmdateien an {up_label} angeglichen (z. B. zuvor ausgelassene Workflow-Dateien), {len(files)} Dateien.']
        if migration:
            body.append('Daten migriert' + (f' (Datenversion {migration["from"]} → {migration["to"]})' if migration.get('to') is not None else '')
                        + (': ' + '; '.join(migration['changes']) if migration.get('changes') else '') + '.')
        if skipped:
            body.append('Nicht aktualisiert (Workflow-Dateien brauchen GHOSTWRITER_UPDATE_TOKEN): ' + ', '.join(skipped))
        if args.dry_run:
            return {**res, 'status': 'updated', 'text': f'(Probelauf) {body[0]}: ' + ', '.join(files[:15]) + (' …' if len(files) > 15 else '')}
        git(*BOT, 'commit', '-q', '-m', msg, '-m', '\n'.join(body), '-m', TRAILER, cwd=wt)
        push = subprocess.run(['git', 'push', 'origin', f'HEAD:refs/heads/{branch}'], cwd=wt, text=True, capture_output=True)
        if push.returncode:
            return {**res, 'status': 'failed',
                    'text': f'Push nach {branch} abgelehnt; der nächste Lauf versucht es erneut.\n\n```\n{push.stderr.strip()[-2000:]}\n```'}
        text = (f'{commits(behind)} von {up_label} eingespielt (GhostWriter {version})' if behind else
                f'Programmdateien an {up_label} angeglichen: ' + ', '.join(drift[:5]) + (' …' if len(drift) > 5 else ''))
        if migration:
            text += ' · Daten migriert' + (f' auf Datenversion {migration["to"]}' if migration.get('to') is not None else '')
        if skipped:
            text += f' ⚠️ {len(skipped)} Workflow-Datei(en) ausgelassen: Secret GHOSTWRITER_UPDATE_TOKEN fehlt'
        return {**res, 'status': 'updated', 'text': text}
    finally:
        subprocess.run(['git', 'worktree', 'remove', '--force', wt], capture_output=True)
        shutil.rmtree(wt, ignore_errors=True)


# ---------- Ablauf ----------

def default_branch():
    """Standard-Branch dieses Repositorys (im Fork: der Buch-Branch)."""
    event = os.environ.get('GITHUB_EVENT_PATH')
    if event and Path(event).is_file():
        try:
            name = (json.loads(Path(event).read_text(encoding='utf-8')).get('repository') or {}).get('default_branch')
            if name:
                return name
        except ValueError:
            pass
    head = git('symbolic-ref', '-q', '--short', 'refs/remotes/origin/HEAD', check=False)
    return head.split('/', 1)[1] if head else (os.environ.get('GITHUB_REF_NAME') or 'main')


def branches(manifest, same_repo, upstream_ref, only):
    names = [r.split('/', 1)[1] for r in git('for-each-ref', '--format=%(refname:short)', 'refs/remotes/origin').splitlines()
             if '/' in r and not r.endswith('/HEAD')]
    if only:
        return [only]
    if not same_repo:
        return sorted(names, key=lambda n: (n != default_branch(), n))
    out = []
    for name in names:
        if name == upstream_ref:
            continue
        text = show(f'origin/{name}', 'ghostwriter.yml')
        cfg = (yaml.safe_load(text) or {}) if text is not None else None
        if library.is_book(name, cfg, manifest):   # Erkennungsregel der Bibliothek (#36)
            out.append(name)
    return out


def main(argv):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--dry-run', action='store_true', help='nichts committen oder pushen')
    ap.add_argument('--branch', help='nur diesen Branch')
    ap.add_argument('--status', help='Ergebnis je Branch als JSON in diese Datei schreiben')
    args = ap.parse_args(argv[1:])

    manifest = yaml.safe_load(Path(MANIFEST).read_text(encoding='utf-8'))
    up = manifest.get('upstream') or {}
    repo, ref = up.get('repo'), up.get('ref', 'main')
    here = os.environ.get('GITHUB_REPOSITORY', '')
    same_repo = repo == here and not os.environ.get('GHOSTWRITER_UPSTREAM_URL')
    token = os.environ.get('GHOSTWRITER_UPDATE_TOKEN') or ''

    git('fetch', '-q', '--prune', 'origin', '+refs/heads/*:refs/remotes/origin/*')
    if same_repo:
        up_ns = 'refs/remotes/origin'
    else:
        url = os.environ.get('GHOSTWRITER_UPSTREAM_URL') or \
            f'https://x-access-token:{token or os.environ.get("GITHUB_TOKEN", "")}@github.com/{repo}.git'
        r = subprocess.run(['git', 'fetch', '-q', '--prune', url, '+refs/heads/*:refs/ghostwriter/upstream/*'],
                           text=True, capture_output=True)
        if r.returncode:
            msg = (f'Hauptrepository {repo} nicht erreichbar. Ist es privat, braucht dieses Repository das Secret '
                   'GHOSTWRITER_UPDATE_TOKEN mit Leserecht darauf'
                   + (' – das vorhandene Secret reicht dafür offenbar nicht' if token else '')
                   + ' (docs/UPDATES.md, „Eigenes Buch anlegen“).')
            summary(['## GhostWriter-Update', '', f'❌ {msg}'])
            if not args.dry_run:
                report_failure(default_branch(), msg)
            return 1
        up_ns = 'refs/ghostwriter/upstream'

    def counterpart(branch):
        if not same_repo and git('rev-parse', '-q', '--verify', f'{up_ns}/{branch}', check=False):
            return f'{up_ns}/{branch}', f'{repo}:{branch}'
        return f'{up_ns}/{ref}', f'{repo}:{ref}'

    if not exists(f'{up_ns}/{ref}', MANIFEST):
        summary(['## GhostWriter-Update', '', f'{repo}:{ref} hat noch kein {MANIFEST}; nichts zu tun.'])
        return 0

    lines = ['## GhostWriter-Update', '', f'Hauptrepository: `{repo}`', '',
             '| Branch | hinter | Ergebnis |', '|---|--:|---|']
    icon = {'updated': '✅', 'current': '✔️', 'skipped': '⏭️', 'failed': '❌'}
    results, failed = [], False
    for branch in branches(manifest, same_repo, ref, args.branch):
        up_rev, up_label = counterpart(branch)
        up_manifest = yaml.safe_load(show(up_rev, MANIFEST) or '{}') or {}
        try:
            res = update_branch(branch, up_rev, up_label, up_manifest, args, bool(token))
        except RuntimeError as e:
            res = {'branch': branch, 'upstream': up_label, 'status': 'failed', 'text': str(e)}
        results.append(res)
        lines.append(f'| `{branch}` | {res.get("behind", "?")} | {icon[res["status"]]} {res["text"].splitlines()[0]} |')
        if res['status'] == 'failed':
            failed = True
            if not args.dry_run:
                report_failure(branch, res['text'])
        elif res['status'] == 'updated' and not args.dry_run:
            report_success(branch, f'Behoben: {res["text"]}')
    summary(lines)
    if args.status:
        Path(args.status).write_text(json.dumps(results, ensure_ascii=False, indent=1), encoding='utf-8')
    return 1 if failed else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
