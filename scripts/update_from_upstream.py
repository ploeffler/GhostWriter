#!/usr/bin/env python3
"""Hält Forks und Buch-Branches auf dem Stand des GhostWriter-Hauptrepositorys.

Aufruf (in der Action „GhostWriter aktualisieren“, .github/workflows/update.yml):
  python scripts/update_from_upstream.py [--dry-run] [--branch NAME] [--status FILE] [--channel release|rc|main]

Kanal (#604): Bücher holen Updates standardmäßig nur aus veröffentlichten Releases (`release`: neuester Tag
vX.Y[.Z]); `rc` nimmt auch Vorabversionen (vX.Y-rc.N), `main` den laufenden Stand wie früher (`upstream.ref`).
Der Kanal kommt aus `--channel`, sonst aus der Repo-Variable GHOSTWRITER_UPDATE_CHANNEL, sonst `release`. Im Kanal
`release` und `rc` gilt für jeden Branch derselbe Tag (kein gleichnamiger Branch); ein Buch, das schon einen
neueren main-Stand enthält, bleibt unverändert, bis ein höheres Release erscheint.

Wie GitHubs „Sync fork“, aber sicher für Bücher. Für jeden Branch wird gezählt,
wie viele Commits er hinter seinem Gegenstück im Hauptrepository liegt
(gleichnamiger Branch, sonst upstream.ref aus ghostwriter-manifest.yml).
Liegt er dahinter, werden die Commits eingespielt:

  - Hat der Branch keine eigenen Commits: Fast-Forward, danach ist er identisch.
  - Sonst ein Merge-Commit. Konflikte löst er nach dem Manifest: Programmdateien
    (managed) nimmt er vom Hauptrepository, Buchdateien (book) bleiben wie im
    Buch, auch wenn das Hauptrepository die Vorlagen geändert hat. Konflikte in
    anderen Dateien brechen das Update für diesen Branch ab.
  - Danach Migrationen (scripts/migrate_project.py), Projektprüfung
    (scripts/validate_project.py) und erst danach die Übersichtsdatei
    (scripts/build_index.py). Schlägt die Prüfung fehl, wird
    nichts eingespielt, sondern ein Issue „GhostWriter-Update fehlgeschlagen“
    geöffnet. Ein Buch wird nie auf eine ältere Programmversion zurückgesetzt.

Danach liegt kein Branch mehr hinter dem Hauptrepository; GitHubs Hinweis
„This branch is N commits behind …“ verschwindet.

Offene Änderungspakete (#470): Hat ein Buch ein offenes Änderungspaket, also einen
Arbeits-Branch ghostwriter/<buch> mit offenem Pull Request zum Buch, wird danach
der ganze Buchstand in diesen Arbeits-Branch gemergt. So laufen dort Workflows und
Prüfungen mit dem neuen Programmstand. Bei einem Konflikt bleibt das Änderungspaket
unverändert, der Bericht nennt die Dateien; nur die Übersichtsdatei wird bei einem
Konflikt neu erzeugt. Arbeits-Branches ohne offenen Pull Request bleiben, wie sie
sind; der Probelauf zeigt nur an.

Welche Branches: im Fork bzw. eigenen Repository zuerst der Standard-Branch
(Programm einer Bibliothek bzw. das Einzelbuch), dann alle Bücher nach der
Erkennungsregel aus scripts/library.py (#39); Arbeits-Branches (ghostwriter/*)
und andere Branches nicht. Im
Hauptrepository selbst nur Bücher nach der Erkennungsregel aus scripts/library.py
(buch/*-Branches, sonst Branches mit Kapiteln wie test/test-book), nie
update.skip_branches.

--status FILE schreibt je Branch behind/ahead/Ergebnis als JSON (für Tests und
die Projektübersicht).

Umgebung:
  GITHUB_REPOSITORY        owner/repo dieses Repositorys
  GITHUB_TOKEN             Token der Action (dieses Repository, Issues)
  GITHUB_EVENT_PATH        Ereignis der Action (Standard-Branch)
  GHOSTWRITER_UPDATE_CHANNEL optional: release (Vorgabe) | rc | main, aus der Actions-Variable gleichen Namens
  GHOSTWRITER_UPDATE_TOKEN optional: Leserecht auf ein privates Hauptrepository und
                           Workflow-Schreibrecht; ohne ihn bleiben Änderungen an
                           .github/workflows/ aus und werden gemeldet
  GHOSTWRITER_UPSTREAM_URL nur für Tests: Git-URL des Hauptrepositorys
  GHOSTWRITER_OPEN_PRS     nur für Tests: JSON {"ghostwriter/<buch>": <PR-Nummer>} statt GitHub-Abfrage
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


CHANNELS = ('release', 'rc', 'main')
TAG_RE = re.compile(r'^v(\d+)\.(\d+)(?:\.(\d+))?(?:-rc\.(\d+))?$')   # Format aus scripts/release.py (tag_name)
TAG_NS = 'refs/ghostwriter/upstream-tags'


def channel_of(value):
    """Kanal aus Eingabe, Variable oder Vorgabe; ValueError bei unbekanntem Wert."""
    name = (value or '').strip().lower() or 'release'
    if name not in CHANNELS:
        raise ValueError(f'Unbekannter Update-Kanal „{value}“. Erlaubt: release (Vorgabe), rc, main.')
    return name


def pick_tag(names, channel):
    """Neuester Tag nach Version (nicht nach Datum): `release` ohne Vorabversionen, `rc` mit; sonst None.
    Ein Release steht über seinen Vorabversionen (v1.1 > v1.1-rc.2)."""
    best = None
    for name in names:
        m = TAG_RE.match(name)
        if not m or (channel == 'release' and m.group(4)):
            continue
        key = (int(m.group(1)), int(m.group(2)), int(m.group(3) or 0), 0 if m.group(4) else 1, int(m.group(4) or 0))
        if best is None or key > best[0]:
            best = (key, name)
    return best[1] if best else None


def version_tuple(v):
    nums = [int(x) for x in re.findall(r'\d+', str(v or '0'))[:3]]
    return tuple(nums + [0] * (3 - len(nums)))


def summary(lines):
    path = os.environ.get('GITHUB_STEP_SUMMARY')
    text = '\n'.join(lines) + '\n'
    print(text)
    for target in dict.fromkeys(p for p in (path, os.environ.get('DAILY_UPDATE_REPORT_PATH')) if p):
        with open(target, 'a', encoding='utf-8') as f:
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


def repair_hints(output):
    """Reparaturweg für abgeschlossene Abschnitte und Teile, deren Text vom Fingerabdruck der Freigabe abweicht (#595, #563).
    `output` ist die Ausgabe von validate_project.py; leer, wenn keine solche Meldung darin steht."""
    rows, seen = [], set()
    for line in output.splitlines():
        if 'Manuskript-Fingerabdruck weicht' not in line:
            continue
        m = re.search(r'approval-section (\d+\.\d+)', line)
        if m:
            key, what = m.group(1), f'Abschnitt {m.group(1)}'
        else:   # Vor-/Nachspann: Meldung nennt den Dateipfad
            f = re.search(r'(matter/([^\s:]+?)\.md)', line)
            if not f:
                continue
            key, what = f.group(2), f'Teil `{f.group(1)}`'
        if key not in seen:
            seen.add(key)
            rows.append(f'- {what}: `python3 scripts/render_view.py . approval-section {key}` zeigt „Geänderten Text neu abschließen“')
    if not rows:
        return ''
    return ('\n\n**Reparaturweg:** Der Text dieser abgeschlossenen Abschnitte wurde nach dem Abschließen geändert, ohne sie '
            'wieder zu öffnen. Im Buch je Abschnitt die Bestätigung „Geänderten Text neu abschließen“ geben (ein Commit mit '
            '„zurückgenommen“ und „erteilt“ und neuem Fingerabdruck, `docs/SPEICHERN.md`), danach das Update erneut starten:\n'
            + '\n'.join(rows))


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


def start_profile(base):
    """Das Instanzprofil kommt verbindlich vom Standard-Branch, auch für Bücher."""
    standard = f'origin/{default_branch()}'
    rev = standard if git('rev-parse', '--verify', standard, check=False) else base
    return yaml.safe_load(show(rev, 'assistant.yml') or '{}') or {}


def start_library(base):
    """Auch Bibliotheken ohne Profil/Index anhand der aktuellen Branches erkennen."""
    if exists(base, 'library.json'):
        return True
    manifest = yaml.safe_load(show(base, MANIFEST) or '{}') or {}
    for ref in git('for-each-ref', '--format=%(refname)', 'refs/remotes/origin').splitlines():
        if ref.endswith('/HEAD'):
            continue
        name = ref.removeprefix('refs/remotes/origin/')
        config = yaml.safe_load(show(ref, 'ghostwriter.yml') or '{}') or {}
        if name != default_branch() and library.is_book(name, config, manifest, default_branch()):
            return True
    return False


def generated_skill(wt):
    """True, wenn der persönliche Skill aus assistant.yml erzeugt wurde (nicht von Hand geschrieben)."""
    try:
        profile = yaml.safe_load((Path(wt) / 'assistant.yml').read_text(encoding='utf-8')) or {}
        skill = Path(wt, '.claude/skills', str(profile.get('skill') or ''), 'SKILL.md')
        return bool(profile.get('skill')) and skill.is_file() and 'python scripts/assistant.py . skill' in skill.read_text(encoding='utf-8')
    except (OSError, yaml.YAMLError):
        return False


def upstream_module(rev, name):
    """Lädt scripts/<name>.py aus dem neuen Programmstand, nicht aus dem alten Buchstand.

    Sonst rendert ein veralteter Generator die neue Vorlage und scheitert an
    Platzhaltern, die erst mit diesem Update kommen (z. B. $DISPLAY).
    """
    import importlib.util
    code = show(rev, f'scripts/{name}.py')
    if code is None:
        return __import__(name)
    with tempfile.TemporaryDirectory(prefix='gw-upstream-mod-') as tmp:
        path = Path(tmp, f'{name}.py')
        path.write_text(code, encoding='utf-8')
        spec = importlib.util.spec_from_file_location(f'upstream_{name}', path)
        module = importlib.util.module_from_spec(spec)
        try:
            spec.loader.exec_module(module)
        except (Exception, SystemExit) as error:
            raise RuntimeError(f'START.md nicht erzeugt: Generator des neuen Stands lädt nicht ({error})') from error
    return module


def expected_start(base, up_rev, branch):
    """Erwartete generierte Dateien für Drift-Prüfung, ohne den Zielbranch zu ändern.

    Alte Upstream-Versionen ohne Generator behalten den bisherigen Update-Weg.
    Der kanonische START.md-Volltext bleibt im Hauptrepository.
    """
    if not exists(up_rev, 'scripts/build_start.py'):
        return None
    build_start = upstream_module(up_rev, 'build_start')
    repo = os.environ.get('GITHUB_REPOSITORY', '')
    manifest = yaml.safe_load(show(up_rev, MANIFEST) or '{}') or {}
    if ((manifest.get('upstream') or {}).get('repo', '').lower() == repo.lower()
            and branch == default_branch()):
        return None  # Die zentrale START.md niemals durch einen Instanz-Einstieg ersetzen.
    config = yaml.safe_load(show(base, 'ghostwriter.yml') or '{}') or {}
    profile = start_profile(base)
    language = ((config.get('interface') or {}).get('language') or profile.get('interface_language') or 'de')
    main_name, openwebui_name = (build_start.template_names(language) if hasattr(build_start, 'template_names')
                                 else (f"templates/start/{'en' if language.split('-')[0] == 'en' else 'de'}.md", None))
    template = show(up_rev, main_name)
    openwebui = show(up_rev, openwebui_name) if openwebui_name else None
    source = show(up_rev, 'START.md')
    if template is None or source is None:
        raise RuntimeError('START.md nicht erzeugt: zentrale Quelle oder Einstiegsvorlage fehlt.')
    try:
        extra = {'openwebui_template': openwebui} if openwebui is not None else {}
        return build_start.render(source, template, repo=repo, branch=branch,
                                  default_branch=default_branch(), config=config, profile=profile,
                                  library_present=start_library(base), **extra)
    except ValueError as error:
        raise RuntimeError(f'START.md nicht erzeugt: {error}') from error


def update_branch(branch, up_rev, up_label, up_manifest, args, can_workflows, release=None):
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
    try:
        generated = expected_start(base, up_rev, branch)
    except RuntimeError as error:
        return {**res, 'status': 'failed', 'text': f'{error}\nUpdate nicht eingespielt.'}
    drift = [f for f in git('diff', '--name-only', base, up_rev, '--', *managed).splitlines() if f] if managed else []
    if generated is not None:
        # Instanzdateien sind absichtlich anders als die zentrale Quelle.
        drift = [f for f in drift if f != 'START.md' and not f.startswith('docs/start/')]
        drift.extend(path for path, text in generated.items() if show(base, path) != text)
        previous = git('ls-tree', '-r', '--name-only', base, '--', 'docs/start').splitlines()
        drift.extend(path for path in previous if path not in generated)
    own_version = (yaml.safe_load(show(base, MANIFEST) or '{}') or {}).get('version')
    if release and related and behind == 0 and drift and own_version and version_tuple(own_version) >= version_tuple(version):
        # #604: Der Release-Commit steckt schon im Buch, das Buch hat aber einen neueren main-Stand: nicht zurücksetzen
        return {**res, 'status': 'current',
                'text': f'Stand von main ({own_version}+{git("rev-list", "--count", up_rev + ".." + base)}), '
                        f'wartet auf das nächste Release (jetzt {release["tag"]})'}
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
    if generated is None and related and ahead == 0 and (can_workflows or not workflows_differ):
        if args.dry_run:
            return {**res, 'status': 'updated', 'text': f'(Probelauf) Fast-Forward um {commits(behind)} auf {up_label}'}
        code, err = push(f'{up_sha}:refs/heads/{branch}')
        if code:
            return {**res, 'status': 'failed', 'stale': push_kind(err) == 'stale', 'text': push_error(branch, err)}
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
            cmds = [['scripts/migrate_project.py', '.']]
            if (Path(wt) / 'assistant.yml').is_file() and generated_skill(wt):
                # Erzeugter persönlicher Skill folgt der neuen Vorlage; eigene Ergänzungen bleiben.
                cmds.append(['scripts/assistant.py', '.', 'skill'])
            cmds += [['scripts/validate_project.py', '.'], ['scripts/build_index.py', '.']]
            for cmd in cmds:
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
                                     + '\n\n'.join(steps)[-6000:] + '\n```' + repair_hints(out))}
            state_path = Path(wt) / STATE
            state_path.parent.mkdir(parents=True, exist_ok=True)
            state_path.write_text(yaml.safe_dump({
                'upstream': up_label, 'version': str(version), 'commit': up_sha,
                'updated_at': datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
                'skipped_workflows': skipped,
                **({'migration': migration} if migration else {})}, allow_unicode=True, sort_keys=False), encoding='utf-8')
        if generated is not None:
            # Nach Migration/Prüfung aus den neuen zentralen Quellen rendern.
            # Auch ein bisher möglicher Fast-Forward läuft dadurch über genau
            # einen geprüften Update-Commit einschließlich Instanz-Einstieg.
            with tempfile.TemporaryDirectory(prefix='gw-start-profile-') as profile_dir:
                profile_path = Path(profile_dir, 'profile.json')
                profile_path.write_text(json.dumps(start_profile(base)), encoding='utf-8')
                cmd = ['scripts/build_start.py', '.', '--repo', os.environ.get('GITHUB_REPOSITORY', ''),
                       '--branch', branch, '--default-branch', default_branch(),
                       '--profile-json', str(profile_path)]
                if start_library(base):
                    cmd.append('--library-present')
                code, out = run(cmd, wt)
            if code:
                return {**res, 'status': 'failed', 'text': 'START.md nicht erzeugt; Update nicht eingespielt.\n' + out}
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
        code, err = push(f'HEAD:refs/heads/{branch}', cwd=wt)
        if code:
            return {**res, 'status': 'failed', 'stale': push_kind(err) == 'stale', 'text': push_error(branch, err)}
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


# ---------- Offene Änderungspakete (#470) ----------

WORK_PREFIX = 'ghostwriter/'
INDEX_FILE = 'ghostwriter-index.json'


def open_change_package(work, base):
    """Nummer des offenen Pull Requests work → base oder None."""
    if 'GHOSTWRITER_OPEN_PRS' in os.environ:
        return (json.loads(os.environ['GHOSTWRITER_OPEN_PRS'] or '{}') or {}).get(work)
    from urllib.parse import quote
    owner = os.environ.get('GITHUB_REPOSITORY', '').split('/')[0]
    prs = api('GET', f'/pulls?state=open&base={quote(base)}&head={quote(owner + ":" + work)}') or []
    return prs[0].get('number') if prs else None


def follow_work_branch(branch, args, can_workflows, find_pr=open_change_package):
    """Buchstand in das offene Änderungspaket ghostwriter/<branch> mergen. None, wenn es keins gibt
    oder es schon aktuell ist; sonst ein Ergebnis wie update_branch (status updated|skipped|conflict|failed)."""
    work = WORK_PREFIX + branch
    if not git('rev-parse', '-q', '--verify', f'refs/remotes/origin/{work}', check=False):
        return None
    git('fetch', '-q', 'origin', f'+refs/heads/{branch}:refs/remotes/origin/{branch}',
        f'+refs/heads/{work}:refs/remotes/origin/{work}')
    base, head = f'origin/{branch}', f'origin/{work}'
    behind = int(git('rev-list', '--count', f'{head}..{base}'))
    if not behind:
        return None
    res = {'branch': work, 'upstream': branch, 'behind': behind, 'ahead': None}
    pr = find_pr(work, branch)
    if not pr:
        return {**res, 'status': 'skipped', 'text': f'{commits(behind)} hinter {branch}; kein offener Pull Request, nicht angefasst'}
    label = f'Änderungspaket #{pr}'
    workflows = [f for f in git('diff', '--name-only', f'{head}...{base}', '--', WORKFLOWS).splitlines() if f]
    if workflows and not can_workflows:
        return {**res, 'status': 'skipped',
                'text': f'{label}: {commits(behind)} hinter {branch}, aber Workflow-Dateien geändert; ohne '
                        'GHOSTWRITER_UPDATE_TOKEN nicht nachgezogen (im Pull Request „Update branch“ wählen)'}
    if args.dry_run:
        return {**res, 'status': 'updated', 'text': f'(Probelauf) {label}: Buchstand ({commits(behind)}) würde eingespielt'}
    wt = tempfile.mkdtemp(prefix='gw-work-')
    try:
        git('worktree', 'add', '-q', '--detach', wt, head)
        msg = f'Buchstand von {branch} in das Änderungspaket übernommen (GhostWriter-Update)'
        merged = subprocess.run(['git', *BOT, 'merge', '--no-ff', '--no-edit', '-m', msg, '-m', TRAILER, base],
                                cwd=wt, text=True, capture_output=True)
        if merged.returncode:
            conflicts = [f for f in git('diff', '--name-only', '--diff-filter=U', cwd=wt).splitlines() if f]
            if conflicts == [INDEX_FILE] and (Path(wt) / 'scripts/build_index.py').is_file():
                # Die Übersichtsdatei ist abgeleitet: aus dem gemergten Stand neu erzeugen.
                git('checkout', '--theirs', '--', INDEX_FILE, cwd=wt)
                code, out = run(['scripts/build_index.py', '.'], wt)
                if code:
                    conflicts = [f'{INDEX_FILE} (neu erzeugen fehlgeschlagen)']
                else:
                    git('add', '-A', cwd=wt)
                    git(*BOT, 'commit', '-q', '--no-edit', cwd=wt)
                    conflicts = []
            if conflicts:
                subprocess.run(['git', 'merge', '--abort'], cwd=wt, capture_output=True)
                return {**res, 'status': 'conflict',
                        'text': f'{label}: Konflikt in ' + ', '.join(conflicts[:8]) + (' …' if len(conflicts) > 8 else '')
                                + '; Änderungspaket unverändert. Im Pull Request „Update branch“ wählen oder von Hand zusammenführen.'}
        code, err = push(f'HEAD:refs/heads/{work}', cwd=wt)
        if code:
            return {**res, 'status': 'failed', 'text': push_error(work, err)}
        return {**res, 'status': 'updated', 'text': f'{label}: Buchstand ({commits(behind)}) eingespielt'}
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
    out = []
    if not same_repo:
        # Fork bzw. eigenes Repository: zuerst der Standard-Branch (Programm bzw. Einzelbuch),
        # dann die Bücher nach der Erkennungsregel (#39); Arbeits- und andere Branches nicht.
        default = default_branch()
        out = [default] if default in names else []
    for name in names:
        if name in out or (same_repo and name == upstream_ref):
            continue
        text = show(f'origin/{name}', 'ghostwriter.yml')
        cfg = (yaml.safe_load(text) or {}) if text is not None else None
        if library.is_book(name, cfg, manifest, default_branch()):   # Erkennungsregel der Bibliothek (#36)
            out.append(name)
    return out


WORKFLOW_SCOPE_HINT = ('Das Secret GHOSTWRITER_UPDATE_TOKEN darf keine Workflow-Dateien ändern. Fine-grained Token: unter '
                       'Permissions „Workflows: Read and write“ ergänzen (zusätzlich zu „Contents: Read and write“); klassischer '
                       'Token: Scope „workflow“ anhaken. Danach das Update erneut starten (docs/UPDATES.md, „Token für private '
                       'Hauptrepositorys und Workflow-Dateien“).')


TRANSIENT = re.compile(r'Internal Server Error|HTTP 5\d\d|\b50[0-4]\b|remote end hung up|RPC failed|Connection reset|'
                       r'early EOF|timed out|Could not resolve host', re.I)
STALE = re.compile(r'non-fast-forward|fetch first|\(stale info\)|cannot lock ref', re.I)


def push_kind(stderr):
    """Art eines abgelehnten Pushs: 'transient' (Serverfehler, nochmal versuchen), 'stale' (Branch ist inzwischen
    weiter, neu einspielen) oder 'other' (z. B. fehlendes Workflow-Recht)."""
    if STALE.search(stderr or ''):
        return 'stale'
    if TRANSIENT.search(stderr or ''):
        return 'transient'
    return 'other'


def push(refspec, cwd=None, tries=3, wait=5):
    """git push mit Wiederholung bei vorübergehenden Serverfehlern. Gibt (returncode, stderr) zurück."""
    import time
    for n in range(tries):
        r = subprocess.run(['git', 'push', 'origin', refspec], cwd=cwd, text=True, capture_output=True)
        if not r.returncode or push_kind(r.stderr) != 'transient' or n == tries - 1:
            return r.returncode, r.stderr
        time.sleep(wait * (n + 1))
    return r.returncode, r.stderr


def push_error(branch, stderr):
    """Text für einen abgelehnten Push; erkennt den fehlenden Workflow-Scope des Tokens."""
    tail = f'\n\n```\n{stderr.strip()[-2000:]}\n```'
    if 'without `workflow` scope' in stderr or 'without workflow scope' in stderr:
        return f'Push nach {branch} abgelehnt: Token ohne Workflow-Recht. {WORKFLOW_SCOPE_HINT}' + tail
    if push_kind(stderr) == 'transient':
        return (f'Push nach {branch} abgelehnt: GitHub-Serverfehler, auch nach mehreren Versuchen; '
                'der nächste Lauf versucht es erneut (oder von Hand neu starten).' + tail)
    return f'Push nach {branch} abgelehnt; der nächste Lauf versucht es erneut.' + tail


def main(argv):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--dry-run', action='store_true', help='nichts committen oder pushen')
    ap.add_argument('--branch', help='nur diesen Branch')
    ap.add_argument('--status', help='Ergebnis je Branch als JSON in diese Datei schreiben')
    ap.add_argument('--channel', help='release (Vorgabe), rc oder main; sonst GHOSTWRITER_UPDATE_CHANNEL (#604)')
    args = ap.parse_args(argv[1:])

    manifest = yaml.safe_load(Path(MANIFEST).read_text(encoding='utf-8'))
    up = manifest.get('upstream') or {}
    repo, ref = up.get('repo'), up.get('ref', 'main')
    here = os.environ.get('GITHUB_REPOSITORY', '')
    same_repo = repo == here and not os.environ.get('GHOSTWRITER_UPSTREAM_URL')
    token = os.environ.get('GHOSTWRITER_UPDATE_TOKEN') or ''
    try:
        channel = channel_of(args.channel or os.environ.get('GHOSTWRITER_UPDATE_CHANNEL'))
    except ValueError as e:
        summary(['## GhostWriter-Update', '', f'❌ {e}'])
        return 1
    if same_repo:
        channel = 'main'   # im Hauptrepository selbst gibt es nur den laufenden Stand

    git('fetch', '-q', '--prune', 'origin', '+refs/heads/*:refs/remotes/origin/*')
    if same_repo:
        up_ns = 'refs/remotes/origin'
    else:
        url = os.environ.get('GHOSTWRITER_UPSTREAM_URL') or \
            f'https://x-access-token:{token or os.environ.get("GITHUB_TOKEN", "")}@github.com/{repo}.git'
        r = subprocess.run(['git', 'fetch', '-q', '--prune', url, '+refs/heads/*:refs/ghostwriter/upstream/*',
                            f'+refs/tags/*:{TAG_NS}/*'],
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

    release = None
    if channel != 'main':
        names = git('for-each-ref', '--format=%(refname:strip=3)', TAG_NS, check=False).splitlines()
        tag = pick_tag(names, channel)
        if not tag:
            summary(['## GhostWriter-Update', '', f'Hauptrepository: `{repo}` · Kanal `{channel}`', '',
                     f'Im Hauptrepository gibt es noch keinen Release-Tag{" (auch keine Vorabversion)" if channel == "rc" else ""}; '
                     'nichts eingespielt. Für den laufenden Stand die Repo-Variable GHOSTWRITER_UPDATE_CHANNEL auf `main` '
                     'setzen (docs/UPDATES.md, „Update-Kanal“).'])
            return 0
        tag_sha = git('rev-parse', f'{TAG_NS}/{tag}^{{commit}}')
        release = {'tag': tag, 'sha': tag_sha}

    def counterpart(branch):
        if release:
            return release['sha'], f'{repo}@{release["tag"]}'
        if not same_repo and git('rev-parse', '-q', '--verify', f'{up_ns}/{branch}', check=False):
            return f'{up_ns}/{branch}', f'{repo}:{branch}'
        return f'{up_ns}/{ref}', f'{repo}:{ref}'

    if not exists(release['sha'] if release else f'{up_ns}/{ref}', MANIFEST):
        summary(['## GhostWriter-Update', '', f'{repo}:{ref} hat noch kein {MANIFEST}; nichts zu tun.'])
        return 0

    head = f'Hauptrepository: `{repo}`'
    if release:   # #604: Version, Tag und Link zu den Release-Notizen
        rel_version = (yaml.safe_load(show(release['sha'], MANIFEST) or '{}') or {}).get('version') or '?'
        head += (f' · Kanal `{channel}` · Release {rel_version} (Tag `{release["tag"]}`, '
                 f'[Release-Notizen](https://github.com/{repo}/releases/tag/{release["tag"]}))')
    lines = ['## GhostWriter-Update', '', head, '',
             '| Branch | hinter | Ergebnis |', '|---|--:|---|']
    icon = {'updated': '✅', 'current': '✔️', 'skipped': '⏭️', 'failed': '❌', 'conflict': '⚠️'}
    results, failed = [], False
    for branch in branches(manifest, same_repo, ref, args.branch):
        up_rev, up_label = counterpart(branch)
        up_manifest = yaml.safe_load(show(up_rev, MANIFEST) or '{}') or {}
        try:
            res = update_branch(branch, up_rev, up_label, up_manifest, args, bool(token), release)
            if res.pop('stale', False):
                # Branch ist während des Laufs weitergewandert (z. B. „Bücherregal aktualisieren“):
                # neuen Stand holen und das Update für diesen Branch einmal neu einspielen
                git('fetch', '-q', 'origin', f'+refs/heads/{branch}:refs/remotes/origin/{branch}')
                res = update_branch(branch, up_rev, up_label, up_manifest, args, bool(token), release)
                res.pop('stale', None)
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
        if res['status'] in ('updated', 'current') and not branch.startswith(WORK_PREFIX):
            # Offenes Änderungspaket dieses Buchs mitziehen (#470); ein Fehler dort lässt das Buch-Update gelten.
            try:
                work = follow_work_branch(branch, args, bool(token))
            except RuntimeError as e:
                work = {'branch': WORK_PREFIX + branch, 'status': 'failed', 'text': str(e)}
            if work:
                results.append(work)
                lines.append(f'| `{work["branch"]}` | {work.get("behind", "?")} | {icon[work["status"]]} {work["text"].splitlines()[0]} |')
    summary(lines)
    if args.status:
        Path(args.status).write_text(json.dumps(results, ensure_ascii=False, indent=1), encoding='utf-8')
    return 1 if failed else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
