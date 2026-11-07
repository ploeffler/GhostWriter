#!/usr/bin/env python3
"""Session themenweise sichern, laden sowie geprüft und bestätigt übernehmen."""
import argparse
import datetime
import hashlib
import json
import re
import subprocess
import tempfile
from pathlib import Path


LABELS = {'conversation': 'Gesprächsstand', 'decisions': 'Entscheidungen',
          'research': 'Recherche', 'brainstorming': 'Brainstorming',
          'drafts': 'Entwürfe', 'planning': 'Planung'}


def run(*args, cwd=None, timeout=60):
    try:
        result = subprocess.run(args, cwd=cwd, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        raise ValueError(f'{args[0]}: Zeitüberschreitung; tatsächlichen Stand prüfen') from None
    if result.returncode:
        # Fremde Fehlermeldungen können Zugangsdaten oder Inhalte enthalten.
        raise ValueError(f'{args[0]}: Vorgang fehlgeschlagen (Code {result.returncode})')
    return result.stdout.strip()


def identifier(value):
    if not isinstance(value, str) or not re.fullmatch(r'[a-z0-9][a-z0-9-]{0,79}', value):
        raise ValueError('Kennung: 1–80 Kleinbuchstaben, Ziffern oder Bindestriche erforderlich')
    return value


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + '\n'


def validate(payload):
    if not isinstance(payload, dict) or set(payload) != {'context', 'coverage', 'messages', 'topics'}:
        raise ValueError('Erforderliche Felder: context, coverage, messages, topics')
    if not isinstance(payload['context'], dict) or not payload['context'].get('project'):
        raise ValueError('context.project muss das Buch oder Programm eindeutig benennen')
    coverage = payload['coverage']
    if (not isinstance(coverage, dict) or set(coverage) != {'description', 'gaps'}
            or not isinstance(coverage['description'], str) or not coverage['description'].strip()
            or not isinstance(coverage['gaps'], list)
            or not all(isinstance(x, str) for x in coverage['gaps'])):
        raise ValueError('coverage braucht description und gaps (Liste ausdrücklich bekannter Lücken)')
    if not isinstance(payload['messages'], list) or not payload['messages']:
        raise ValueError('Verfügbare Gesprächsbeiträge fehlen; keine reine Zusammenfassung sichern')
    for message in payload['messages']:
        if (not isinstance(message, dict) or set(message) != {'id', 'role', 'content'}
                or message['role'] not in ('user', 'assistant')
                or not isinstance(message['id'], str) or not message['id']
                or not isinstance(message['content'], str) or not message['content']):
            raise ValueError('Beiträge benötigen id, role (user/assistant) und content; keine internen Nachrichten')
    ids = [m['id'] for m in payload['messages']]
    if len(ids) != len(set(ids)):
        raise ValueError('Doppelte Nachrichtenkennungen')
    topics = payload['topics']
    if not isinstance(topics, dict) or any(k not in LABELS or k == 'conversation' for k in topics):
        raise ValueError('Themen: decisions, research, brainstorming, drafts, planning')
    if any(not isinstance(v, str) or not v.strip() for v in topics.values()):
        raise ValueError('Themeninhalte müssen nichtleere Texte sein')
    return {**topics, 'conversation': {k: payload[k] for k in ('context', 'coverage', 'messages')}}


def session_prs(repo, branch, work):
    return json.loads(run('gh', 'pr', 'list', '--repo', repo, '--head', branch, '--state', 'all',
                          '--json', 'url,baseRefName,state', '--limit', '10', cwd=work))


def open_pr(repo, base, branch, session, work):
    prs = session_prs(repo, branch, work)
    if len(prs) > 1 or (prs and prs[0]['baseRefName'] != base):
        raise ValueError('Sicherungs-PR ist nicht eindeutig oder hat eine andere Zielbasis')
    if prs:
        if prs[0]['state'] != 'OPEN':
            raise ValueError('Sitzungs-PR ist geschlossen; keine zweite PR automatisch anlegen')
        return prs[0]['url']
    body = Path(work) / 'pr-body.txt'
    body.write_text('Gesprächsarbeit dauerhaft gesichert: ein Commit je geändertem Themengebiet.\n\n'
                    'Enthält verfügbare Gesprächsbeiträge, Ergebnisse und ausgewiesene Lücken. '
                    'Keine Übernahme ins Manuskript und keine inhaltliche Freigabe. '
                    'Dieser PR wird nicht automatisch zusammengeführt.\n', encoding='utf-8')
    return run('gh', 'pr', 'create', '--repo', repo, '--base', base, '--head', branch,
               '--title', f'Chat-Sicherung: {session}', '--body-file', str(body), cwd=work)


def save(repository, base, session, payload, expected_head, *, github_repo=None,
         author_name='GhostWriter', author_email='ghostwriter@users.noreply.github.com'):
    """Vollständigen verfügbaren Snapshot übergeben; remote vor Erfolg bestätigen."""
    session = identifier(session)
    topics = validate(payload)  # vor jedem Schreibzugriff prüfen
    if not re.fullmatch(r'[0-9a-f]{40,64}', expected_head):
        raise ValueError('expected-head muss der vollständig gelesene Commit sein')
    branch = f'ghostwriter/chat/{session}'
    with tempfile.TemporaryDirectory(prefix='ghostwriter-chat-') as temp:
        work = Path(temp) / 'repo'
        run('git', 'clone', '--quiet', '--no-checkout', '--', repository, str(work))
        def git(*args):
            return run('git', *args, cwd=work)
        remote = git('ls-remote', '--heads', 'origin', f'refs/heads/{branch}')
        existing = remote.split()[0] if remote else None
        source = existing or git('rev-parse', '--verify', '--end-of-options', f'origin/{base}^{{commit}}')
        if source != expected_head:
            raise ValueError('Stand inzwischen geändert; Sicherung neu lesen und abgleichen')
        git('checkout', '--quiet', '--detach', source)
        git('config', 'user.name', author_name)
        git('config', 'user.email', author_email)
        root = work / 'conversations' / session
        for path in (work / 'conversations', root):
            if path.is_symlink():
                raise ValueError('Sicherungsordner darf kein symbolischer Link sein')
        if root.exists() and any(p.is_symlink() for p in root.rglob('*')):
            raise ValueError('Sicherung enthält symbolische Links')
        manifest = root / 'session.json'
        info = json.loads(manifest.read_text(encoding='utf-8')) if manifest.exists() else None
        if existing and not info:
            raise ValueError('Bestehender Branch enthält keine passende Sitzung')
        if info and (info['base'] != base or info['session'] != session):
            raise ValueError('Sitzung oder Zielbasis stimmt nicht überein')
        if info and github_repo:
            prs = session_prs(github_repo, branch, work)
            if len(prs) > 1 or any(p['state'] != 'OPEN' or p['baseRefName'] != base for p in prs):
                raise ValueError('Sitzung abgeschlossen oder PR uneindeutig; neue Sitzung verwenden')
        if info and info['context'] != payload['context']:
            raise ValueError('Sitzungskontext geändert; neue Sitzung verwenden')
        if not info:
            info = {'format_version': 1, 'session': session, 'base': base,
                    'source_commit': source, 'context': payload['context']}
        # Nachrichten sind append-only; gekürzte oder veränderte Historie nicht ersetzen.
        previous_path = root / 'conversation' / 'latest.json'
        if previous_path.exists():
            previous = json.loads(previous_path.read_text(encoding='utf-8'))['messages']
            if payload['messages'][:len(previous)] != previous:
                raise ValueError('Frühere Beiträge fehlen oder wurden verändert; vollständigen Stand laden')
        commits = []
        for topic, content in topics.items():
            folder = root / topic
            folder.mkdir(parents=True, exist_ok=True)
            latest = folder / 'latest.json'
            value = canonical(content)
            if latest.exists() and latest.read_text(encoding='utf-8') == value:
                continue
            digest = hashlib.sha256(value.encode('utf-8')).hexdigest()
            (folder / f'{digest}.json').write_text(value, encoding='utf-8')
            latest.write_text(value, encoding='utf-8')
            if topic == 'conversation':
                manifest.write_text(canonical(info), encoding='utf-8')
            git('add', '--', str(folder.relative_to(work)))
            if topic == 'conversation':
                git('add', '--', str(manifest.relative_to(work)))
            git('commit', '--quiet', '-m', f'Chat sichern: {LABELS[topic]} ({session})',
                '-m', 'GhostWriter-Aktion: chat.save')
            commits.append({'topic': topic, 'commit': git('rev-parse', 'HEAD')})
        head = git('rev-parse', 'HEAD')
        # Compare-and-swap: auch einen während der Sicherung neu angelegten Branch erkennen.
        lease = f'--force-with-lease=refs/heads/{branch}:{existing or ""}'
        git('push', '--quiet', lease, 'origin', f'HEAD:refs/heads/{branch}')
        observed = git('ls-remote', '--heads', 'origin', f'refs/heads/{branch}').split()
        if not observed or observed[0] != head:
            raise ValueError('Remote-Sicherung konnte nicht bestätigt werden')
        result = {'status': 'remote_saved', 'session': session, 'branch': branch, 'head': head,
                  'saved_at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
                  'commits': commits, 'coverage': payload['coverage'], 'pr': None}
        if github_repo:
            try:
                result['pr'] = open_pr(github_repo, base, branch, session, work)
            except (ValueError, KeyError, TypeError, json.JSONDecodeError):
                result['status'] = 'remote_saved_pr_pending'
                result['warning'] = 'Inhalte gesichert; PR noch nicht bestätigt. Erneut ausführen.'
        return result


def resume(repository, session, base=None):
    session = identifier(session)
    with tempfile.TemporaryDirectory(prefix='ghostwriter-chat-read-') as temp:
        run('git', 'clone', '--quiet', '--no-checkout', '--', repository, temp)
        branch = f'ghostwriter/chat/{session}'
        found = run('git', 'ls-remote', '--heads', 'origin', f'refs/heads/{branch}', cwd=temp)
        if not found and not base:
            raise ValueError('Sicherungsbranch fehlt; bei übernommener Session --base angeben')
        ref = f'origin/{branch if found else base}'
        run('git', 'checkout', '--quiet', '--detach', ref, cwd=temp)
        root = Path(temp) / 'conversations' / session
        if root.is_symlink() or (Path(temp) / 'conversations').is_symlink() or any(p.is_symlink() for p in root.rglob('*')):
            raise ValueError('Sicherung enthält symbolische Links')
        info = json.loads((root / 'session.json').read_text(encoding='utf-8'))
        topics = {p.parent.name: json.loads(p.read_text(encoding='utf-8'))
                  for p in sorted(root.glob('*/latest.json'))}
        return {'session': info, 'head': run('git', 'rev-parse', 'HEAD', cwd=temp), 'topics': topics}


def accept_once(repository, github_repo, session, expected_head, expected_base, *, confirmed=False):
    """Ausdrücklich bestätigten Sicherungs-PR prüfen und per Merge-Commit übernehmen."""
    identifier(session)
    if not confirmed:
        raise ValueError('Übernehmen braucht ausdrückliche Bestätigung des geprüften Stands')
    if not all(re.fullmatch(r'[0-9a-f]{40,64}', x) for x in (expected_head, expected_base)):
        raise ValueError('Vollständige bestätigte Commit-Kennungen erforderlich')
    branch = f'ghostwriter/chat/{session}'
    prs = json.loads(run('gh', 'pr', 'list', '--repo', github_repo, '--head', branch,
                         '--state', 'open', '--json', 'number', '--limit', '10'))
    if len(prs) != 1:
        raise ValueError('Genau ein offener Sitzungs-PR erforderlich')
    number = str(prs[0]['number'])
    pr = json.loads(run('gh', 'pr', 'view', number, '--repo', github_repo, '--json',
                        'headRefOid,baseRefName,headRefName,mergeable,mergeStateStatus,statusCheckRollup,isCrossRepository'))
    pr['baseRefOid'] = run('gh', 'api', f'repos/{github_repo}/pulls/{number}', '--jq', '.base.sha')
    if (pr['isCrossRepository'] or pr['headRefName'] != branch or pr['headRefOid'] != expected_head
            or pr['baseRefOid'] != expected_base or pr['mergeable'] != 'MERGEABLE'
            or pr['mergeStateStatus'] != 'CLEAN'):
        raise ValueError('PR-Stand geändert, konfliktbehaftet oder noch nicht übernehmbar')
    for check in pr.get('statusCheckRollup') or []:
        state = check.get('conclusion') or check.get('state')
        if state not in ('SUCCESS', 'NEUTRAL', 'SKIPPED'):
            raise ValueError('Prüfungen sind noch offen oder fehlgeschlagen')
    with tempfile.TemporaryDirectory(prefix='ghostwriter-chat-accept-') as temp:
        run('git', 'clone', '--quiet', '--no-checkout', '--', repository, temp)
        def git(*args):
            return run('git', *args, cwd=temp)
        if (git('rev-parse', f'origin/{branch}') != expected_head
                or git('rev-parse', f'origin/{pr["baseRefName"]}') != expected_base):
            raise ValueError('Repository-Stand inzwischen geändert')
        paths = git('diff', '--name-only', f'origin/{pr["baseRefName"]}...origin/{branch}').splitlines()
        prefix = f'conversations/{session}/'
        if not paths or any(not x.startswith(prefix) for x in paths):
            raise ValueError('PR enthält andere Änderungen als die zugehörige Session-Sicherung')
        if git('diff', '--diff-filter=D', '--name-only', f'origin/{pr["baseRefName"]}...origin/{branch}'):
            raise ValueError('Sicherungs-PR darf keine Dateien löschen')
        git('checkout', '--quiet', '--detach', expected_head)
        root = Path(temp) / 'conversations' / session
        if root.is_symlink() or (Path(temp) / 'conversations').is_symlink() or any(p.is_symlink() for p in root.rglob('*')):
            raise ValueError('Sicherung enthält symbolische Links')
        info = json.loads((root / 'session.json').read_text(encoding='utf-8'))
        if info['session'] != session or info['base'] != pr['baseRefName']:
            raise ValueError('Sicherungsmanifest passt nicht zum PR')
        conversation = json.loads((root / 'conversation/latest.json').read_text(encoding='utf-8'))
        topics = {p.parent.name: json.loads(p.read_text(encoding='utf-8'))
                  for p in root.glob('*/latest.json') if p.parent.name != 'conversation'}
        validate({**conversation, 'topics': topics})
        for latest in root.glob('*/latest.json'):
            value = latest.read_text(encoding='utf-8')
            digest = hashlib.sha256(value.encode('utf-8')).hexdigest()
            if (latest.parent / f'{digest}.json').read_text(encoding='utf-8') != value:
                raise ValueError('Sicherungsinhalt und archivierter Stand weichen ab')
    # Kopf beim Merge nochmals atomar durch GitHub prüfen; Branchschutz schützt die Basis.
    run('gh', 'pr', 'merge', number, '--repo', github_repo, '--merge', '--match-head-commit', expected_head)
    result = json.loads(run('gh', 'pr', 'view', number, '--repo', github_repo,
                            '--json', 'state,mergeCommit,url'))
    if result['state'] != 'MERGED' or not result.get('mergeCommit'):
        raise ValueError('Zusammenführung noch nicht bestätigt')
    return {'status': 'merged', 'session': session, 'pr': result['url'],
            'commit': result['mergeCommit']['oid']}


def accept(repository, github_repo, session, expected_head, expected_base, *, confirmed=False):
    """Vor Abbruch Diagnose; höchstens ein sicherer Reparatur-/Wiederholungsversuch."""
    identifier(session)
    if not confirmed:
        raise ValueError('Ausdrückliche Bestätigung erforderlich')
    try:
        return accept_once(repository, github_repo, session, expected_head, expected_base, confirmed=True)
    except (ValueError, OSError, KeyError) as error:
        diagnosis = {'status': 'blocked', 'session': session, 'merged': False,
                     'diagnosis': 'Prüfung oder Zugriff fehlgeschlagen',
                     'repair_attempted': False, 'next_step': 'Zugriff und Sicherungsdateien prüfen; nichts verworfen.'}
        try:
            prs = json.loads(run('gh', 'pr', 'list', '--repo', github_repo, '--head',
                                 f'ghostwriter/chat/{session}', '--state', 'all', '--json', 'number', '--limit', '10'))
            if len(prs) != 1:
                return diagnosis
            number = str(prs[0]['number'])
            pr = json.loads(run('gh', 'pr', 'view', number, '--repo', github_repo, '--json',
                                'state,headRefOid,mergeable,mergeStateStatus,mergeCommit,url,statusCheckRollup'))
            pr['baseRefOid'] = run('gh', 'api', f'repos/{github_repo}/pulls/{number}', '--jq', '.base.sha')
            diagnosis['pr'] = pr['url']
            if pr['headRefOid'] != expected_head:
                diagnosis.update(diagnosis='Sicherungsstand geändert', next_step='Neuen Stand sichten und bestätigen.')
                return diagnosis
            # Ein Verbindungsfehler nach erfolgreichem Merge darf keinen zweiten Merge auslösen.
            if pr['state'] == 'MERGED' and pr.get('mergeCommit'):
                return {'status': 'merged', 'session': session, 'pr': pr['url'],
                        'commit': pr['mergeCommit']['oid'], 'recovery': 'Bereits erfolgten Merge bestätigt'}
            if pr['baseRefOid'] != expected_base:
                diagnosis.update(diagnosis='Zielstand geändert', next_step='Vergleich auf neuer Basis prüfen und bestätigen.')
                return diagnosis
            if pr['mergeable'] == 'CONFLICTING':
                diagnosis.update(diagnosis='Inhaltlicher Konflikt', next_step='Unterschiede prüfen; keine automatische Inhaltsentscheidung.')
                return diagnosis
            if pr['state'] != 'OPEN':
                diagnosis.update(diagnosis='PR geschlossen', next_step='Schließen prüfen; nicht automatisch wieder öffnen.')
                return diagnosis
            checks = pr.get('statusCheckRollup') or []
            failed = [c for c in checks if (c.get('conclusion') or c.get('state')) in
                      ('FAILURE', 'ERROR', 'CANCELLED', 'TIMED_OUT', 'ACTION_REQUIRED', 'STARTUP_FAILURE')]
            if failed:
                diagnosis.update(diagnosis='Prüfung fehlgeschlagen',
                                 checks=[{'name': c.get('name') or c.get('context'),
                                          'result': c.get('conclusion') or c.get('state'),
                                          'url': c.get('detailsUrl') or c.get('targetUrl')} for c in failed],
                                 next_step='Fehlerausgabe der benannten Prüfung analysieren, technische Ursache beheben und betroffene Prüfungen erneut ausführen; keine Prüfung umgehen.')
                return diagnosis
            diagnosis['repair_attempted'] = True
            if pr['mergeStateStatus'] != 'CLEAN':
                # Laufende Prüfungen kurz abwarten; fehlgeschlagene Tests nicht überspringen.
                run('gh', 'pr', 'checks', number, '--repo', github_repo,
                    '--watch', '--fail-fast', '--interval', '3', timeout=20)
            result = accept_once(repository, github_repo, session, expected_head, expected_base, confirmed=True)
            result['recovery'] = 'Nach automatischer Diagnose erneut geprüft und übernommen'
            return result
        except (ValueError, OSError, KeyError):
            return diagnosis


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='action', required=True)
    s = sub.add_parser('save')
    s.add_argument('repository', help='Git-URL oder lokales Repository; keine Zugangsdaten in URLs')
    s.add_argument('session')
    s.add_argument('input', help='JSON-Datei mit vollständigem verfügbaren Sitzungsstand')
    s.add_argument('--base', required=True)
    s.add_argument('--expected-head', required=True)
    s.add_argument('--github-repo', required=True, help='owner/repo für gemeinsamen PR')
    s.add_argument('--author-name', default='GhostWriter')
    s.add_argument('--author-email', default='ghostwriter@users.noreply.github.com')
    r = sub.add_parser('resume')
    r.add_argument('repository')
    r.add_argument('session')
    r.add_argument('--base', help='Zielbranch für bereits übernommene Session bei gelöschtem Sicherungsbranch')
    a = sub.add_parser('accept')
    a.add_argument('repository')
    a.add_argument('session')
    a.add_argument('--github-repo', required=True)
    a.add_argument('--expected-head', required=True)
    a.add_argument('--expected-base', required=True)
    a.add_argument('--confirmed', action='store_true')
    args = parser.parse_args()
    try:
        if args.action == 'save':
            payload = json.loads(Path(args.input).read_text(encoding='utf-8'))
            result = save(args.repository, args.base, args.session, payload, args.expected_head,
                          github_repo=args.github_repo, author_name=args.author_name, author_email=args.author_email)
        elif args.action == 'accept':
            result = accept(args.repository, args.github_repo, args.session, args.expected_head,
                            args.expected_base, confirmed=args.confirmed)
        else:
            result = resume(args.repository, args.session, args.base)
        print(canonical(result), end='')
        if result.get('status') in ('remote_saved_pr_pending', 'blocked'):
            raise SystemExit(2)
    except (ValueError, OSError, KeyError) as exc:
        # Keine Inhalte aus fehlerhaftem JSON oder fremden Fehlermeldungen ausgeben.
        parser.exit(1, f'Chat-Sicherung nicht abgeschlossen ({type(exc).__name__}). Eingaben und Zugriff prüfen.\n')


if __name__ == '__main__':
    main()
