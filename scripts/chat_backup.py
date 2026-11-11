#!/usr/bin/env python3
"""Session themenweise sichern, laden sowie geprüft und bestätigt übernehmen."""
import argparse
import datetime
import hashlib
import json
import re
import subprocess
import tempfile
import time
import urllib.parse
from pathlib import Path


LABELS = {'conversation': 'Gesprächsstand', 'decisions': 'Entscheidungen',
          'research': 'Recherche', 'brainstorming': 'Brainstorming',
          'drafts': 'Entwürfe', 'planning': 'Planung', 'section_dialogue': 'Abschnittsdialog',
          'section_answer': 'Abschnittsantwort'}


def run(*args, cwd=None, timeout=60):
    try:
        result = subprocess.run(args, cwd=cwd, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        raise ValueError(f'{args[0]}: Zeitüberschreitung; tatsächlichen Stand prüfen') from None
    if result.returncode:
        # Fremde Fehlermeldungen können Zugangsdaten oder Inhalte enthalten; nur den
        # HTTP-Status von GitHub übernehmen, damit die Ursache sichtbar bleibt (#253).
        status = re.search(r'\bHTTP (\d{3})\b', result.stderr or '')
        hint = f', GitHub HTTP {status.group(1)}' if status else ''
        raise ValueError(f'{args[0]}: Vorgang fehlgeschlagen (Code {result.returncode}{hint})')
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
        raise ValueError('Themen: decisions, research, brainstorming, drafts, planning, section_dialogue, section_answer')
    if any(not isinstance(v, str) or not v.strip() for v in topics.values()):
        raise ValueError('Themeninhalte müssen nichtleere Texte sein')
    return {**topics, 'conversation': {k: payload[k] for k in ('context', 'coverage', 'messages')}}


# GitHub nur über REST (`gh api`) ansprechen: `gh pr …` nutzt GraphQL, das in
# Claude-Code-Sitzungen gesperrt ist (#253).

def gh_api(repo, path, *fields, method='GET', query=None, cwd=None, timeout=60):
    url = f'repos/{repo}/{path}' if path else f'repos/{repo}'
    if query:
        url += '?' + urllib.parse.urlencode(query, safe='/:')
    args = ['gh', 'api', '-X', method, url]
    for key, value in fields:
        args += ['-f', f'{key}={value}']
    output = run(*args, cwd=cwd, timeout=timeout)
    return json.loads(output) if output else None


def pr_state(pr):
    if pr.get('merged') or pr.get('merged_at'):
        return 'MERGED'
    return str(pr.get('state', '')).upper()


def find_prs(repo, branch, state='all', cwd=None):
    """PRs eines Sitzungsbranchs im selben Repository, vereinheitlicht."""
    owner = repo.split('/')[0]
    prs = gh_api(repo, 'pulls', query={'head': f'{owner}:{branch}', 'state': state,
                                       'per_page': 10}, cwd=cwd)
    return [{'number': p['number'], 'url': p['html_url'], 'state': pr_state(p),
             'baseRefName': p['base']['ref']} for p in prs or []]


def session_prs(repo, branch, work):
    return find_prs(repo, branch, 'all', cwd=work)


def check_rollup(repo, sha, cwd=None):
    """Check-Runs und Commit-Status im Format von `statusCheckRollup`."""
    checks = []
    runs = gh_api(repo, f'commits/{sha}/check-runs', query={'per_page': 100}, cwd=cwd) or {}
    for item in runs.get('check_runs', []):
        done = item.get('status') == 'completed'
        checks.append({'name': item.get('name'), 'detailsUrl': item.get('details_url') or item.get('html_url'),
                       'conclusion': str(item.get('conclusion') or '').upper() if done else None,
                       'state': None if done else str(item.get('status') or 'queued').upper()})
    status = gh_api(repo, f'commits/{sha}/status', cwd=cwd) or {}
    for item in status.get('statuses', []):
        checks.append({'context': item.get('context'), 'targetUrl': item.get('target_url'),
                       'state': str(item.get('state') or '').upper()})
    return checks


def pr_info(repo, number, cwd=None):
    """PR-Stand über REST; Felder wie bisher bei `gh pr view --json`."""
    pr = gh_api(repo, f'pulls/{number}', cwd=cwd)
    head_repo = (pr['head'].get('repo') or {}).get('full_name')
    mergeable = {True: 'MERGEABLE', False: 'CONFLICTING'}.get(pr.get('mergeable'), 'UNKNOWN')
    merged = pr_state(pr) == 'MERGED'
    return {'number': pr['number'], 'url': pr['html_url'], 'state': pr_state(pr),
            'headRefOid': pr['head']['sha'], 'headRefName': pr['head']['ref'],
            'baseRefOid': pr['base']['sha'], 'baseRefName': pr['base']['ref'],
            'isCrossRepository': head_repo != pr['base']['repo']['full_name'],
            'mergeable': mergeable,
            'mergeStateStatus': str(pr.get('mergeable_state') or 'unknown').upper(),
            'mergeCommit': {'oid': pr['merge_commit_sha']} if merged and pr.get('merge_commit_sha') else None,
            'statusCheckRollup': check_rollup(repo, pr['head']['sha'], cwd=cwd)}


def pending(pr):
    """Mergebarkeit noch unbekannt oder eine Prüfung läuft noch."""
    return pr['mergeable'] == 'UNKNOWN' or any(
        not c.get('conclusion') and c.get('state') in ('QUEUED', 'IN_PROGRESS', 'PENDING', 'WAITING', 'REQUESTED')
        for c in pr.get('statusCheckRollup') or [])


def wait_for_pr(repo, number, timeout=20, interval=3):
    """Ausstehende Prüfungen und Mergebarkeit begrenzt abwarten (statt `gh pr checks --watch`)."""
    deadline = time.monotonic() + timeout
    pr = pr_info(repo, number)
    while pending(pr) and time.monotonic() < deadline:
        time.sleep(interval)
        pr = pr_info(repo, number)
    return pr


def open_pr(repo, base, branch, session, work):
    prs = session_prs(repo, branch, work)
    if len(prs) > 1 or (prs and prs[0]['baseRefName'] != base):
        raise ValueError('Sicherungs-PR ist nicht eindeutig oder hat eine andere Zielbasis')
    if prs:
        if prs[0]['state'] != 'OPEN':
            raise ValueError('Sitzungs-PR ist geschlossen; keine zweite PR automatisch anlegen')
        return prs[0]['url']
    body = ('Gesprächsarbeit dauerhaft gesichert: ein Commit je geändertem Themengebiet.\n\n'
            'Enthält verfügbare Gesprächsbeiträge, Ergebnisse und ausgewiesene Lücken. '
            'Keine Übernahme ins Manuskript und keine inhaltliche Freigabe. '
            'Dieser PR wird nicht automatisch zusammengeführt.\n')
    try:
        created = gh_api(repo, 'pulls', ('title', f'Chat-Sicherung: {session}'), ('head', branch),
                         ('base', base), ('body', body), method='POST', cwd=work)
        return created['html_url']
    except ValueError:
        # GitHub legt den PR bei 502 o. ä. manchmal trotzdem an: nachsehen statt doppelt anlegen.
        prs = session_prs(repo, branch, work)
        if len(prs) == 1 and prs[0]['state'] == 'OPEN' and prs[0]['baseRefName'] == base:
            return prs[0]['url']
        raise


def save(repository, base, session, payload, expected_head, *, github_repo=None,
         author_name='GhostWriter', author_email='ghostwriter@users.noreply.github.com', atomic=False):
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
        commits, changed = [], []
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
            changed.append(topic)
            if not atomic:
                git('commit', '--quiet', '-m', f'Chat sichern: {LABELS[topic]} ({session})',
                    '-m', 'GhostWriter-Aktion: chat.save')
                commits.append({'topic': topic, 'commit': git('rev-parse', 'HEAD')})
        if atomic and changed:
            git('commit', '--quiet', '-m', f'Abschnittsantwort sichern ({session})',
                '-m', 'GhostWriter-Aktion: chat.save')
            commits.append({'topic': 'section_answer', 'topics': changed, 'commit': git('rev-parse', 'HEAD')})
        head = git('rev-parse', 'HEAD')
        # Compare-and-swap: auch einen während der Sicherung neu angelegten Branch erkennen.
        lease = f'--force-with-lease=refs/heads/{branch}:{existing or ""}'
        if commits:
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
            except (ValueError, KeyError, TypeError) as error:
                result['status'] = 'remote_saved_pr_pending'
                result['warning'] = 'Inhalte gesichert; PR noch nicht bestätigt. Erneut ausführen.'
                result['cause'] = reason(error)
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
    prs = find_prs(github_repo, branch, 'open')
    if len(prs) != 1:
        raise ValueError('Genau ein offener Sitzungs-PR erforderlich')
    number = str(prs[0]['number'])
    pr = pr_info(github_repo, number)
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
    # `sha` entspricht `--match-head-commit`: GitHub lehnt bei verändertem Kopf ab.
    gh_api(github_repo, f'pulls/{number}/merge', ('merge_method', 'merge'), ('sha', expected_head),
           method='PUT')
    result = pr_info(github_repo, number)
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
            diagnosis['cause'] = reason(error)
            prs = find_prs(github_repo, f'ghostwriter/chat/{session}', 'all')
            if len(prs) != 1:
                return diagnosis
            number = str(prs[0]['number'])
            pr = pr_info(github_repo, number)
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
                wait_for_pr(github_repo, number)
            result = accept_once(repository, github_repo, session, expected_head, expected_base, confirmed=True)
            result['recovery'] = 'Nach automatischer Diagnose erneut geprüft und übernommen'
            return result
        except (ValueError, OSError, KeyError):
            return diagnosis


def reason(error):
    """Eigene Fehlermeldung zeigen; JSON-Fehler und Fremdtexte nur als Art."""
    if isinstance(error, ValueError) and not isinstance(error, json.JSONDecodeError):
        return str(error)
    return type(error).__name__


def validate_review(payload, review, *, answer=False):
    """Gesprächsbelege prüfen, bevor ein Schreibzugriff möglich ist."""
    validate(payload)
    fields = {'section_id', 'source_commit', 'dialogue_complete', 'awaiting_reply', 'items'}
    if answer:
        fields.add('answer_message_id')
    if not isinstance(review, dict) or set(review) != fields:
        raise ValueError('Abschnittsdialog braucht section_id, source_commit, dialogue_complete, awaiting_reply, items')
    identifier(review['section_id'])
    if not isinstance(review['source_commit'], str) or not re.fullmatch(r'[0-9a-f]{40,64}', review['source_commit']):
        raise ValueError('Gelesener Buchstand fehlt')
    if type(review['dialogue_complete']) is not bool or type(review['awaiting_reply']) is not bool:
        raise ValueError('Dialogabschluss und ausstehende Antwort müssen boolesch sein')
    items = review['items']
    if not isinstance(items, list) or not items:
        raise ValueError('Besprochene Punkte mit Belegen erforderlich')
    messages = {m['id']: m for m in payload['messages']}
    seen = set()
    for item in items:
        if (not isinstance(item, dict) or set(item) != {'id', 'question', 'status', 'evidence'}
                or not isinstance(item['id'], str) or not item['id'] or item['id'] in seen
                or not isinstance(item['question'], str) or not item['question'].strip()
                or item['status'] not in ('open', 'answered', 'decided', 'deferred')
                or not isinstance(item['evidence'], list) or not item['evidence']
                or not all(isinstance(x, str) and x in messages for x in item['evidence'])):
            raise ValueError('Ungültiger Gesprächspunkt oder fehlender Nachrichtenbeleg')
        seen.add(item['id'])
        if item['status'] in ('decided', 'deferred') and not any(
                messages[x]['role'] == 'user' for x in item['evidence']):
            raise ValueError('Entscheidung oder Vertagung braucht einen Benutzerbeitrag als Beleg')
    if answer:
        answer_id = review['answer_message_id']
        if (not isinstance(answer_id, str) or answer_id != payload['messages'][-1]['id']
                or payload['messages'][-1]['role'] != 'user'
                or not any(answer_id in item['evidence'] for item in items)):
            raise ValueError('Antwortsicherung braucht die letzte Benutzerantwort als belegten aktuellen Beitrag')


def answer_checkpoint(repository, base, session, payload, expected_head, review, **kwargs):
    """Ausgewertete Antwort vor sichtbarer Folgeantwort sichern, auch bei offenen Fragen."""
    validate_review(payload, review, answer=True)
    enriched = {**payload, 'topics': {**payload['topics'], 'section_answer': canonical(review)}}
    result = save(repository, base, session, enriched, expected_head, atomic=True, **kwargs)
    result.update(trigger='section_answer_evaluated', section_id=review['section_id'],
                  answer_message_id=review['answer_message_id'],
                  reply_ready=result['status'] in ('remote_saved', 'remote_saved_pr_pending'))
    return result


def section_checkpoint(repository, base, session, payload, expected_head, review, **kwargs):
    """Zusätzlicher Abschlussnachweis; Zwischenantworten über answer_checkpoint sichern."""
    validate_review(payload, review)
    if (not review['dialogue_complete'] or review['awaiting_reply']
            or any(x['status'] == 'open' for x in review['items'])):
        return {'status': 'not_due', 'section_id': review['section_id'],
                'reason': 'Abschnittsdialog läuft noch oder eine Antwort steht aus'}
    # Eingabe unverändert lassen; Nachweis als eigenes Themengebiet mit sichern.
    enriched = {**payload, 'topics': {**payload['topics'], 'section_dialogue': canonical(review)}}
    result = save(repository, base, session, enriched, expected_head, **kwargs)
    result['trigger'] = 'section_dialogue_completed'
    result['section_id'] = review['section_id']
    return result


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
    c = sub.add_parser('checkpoint', parents=[s], add_help=False, help='Nach abgeschlossenem Abschnittsdialog automatisch sichern')
    c.add_argument('--review', required=True, help='JSON-Datei mit belegtem Abschluss der besprochenen Punkte')
    q = sub.add_parser('answer-checkpoint', parents=[s], add_help=False, help='Ausgewertete Antwort sofort und vor weiterer Chat-Ausgabe sichern')
    q.add_argument('--review', required=True, help='JSON-Datei mit answer_message_id und belegtem Fragenstand')
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
        if args.action in ('save', 'checkpoint', 'answer-checkpoint'):
            payload = json.loads(Path(args.input).read_text(encoding='utf-8'))
            options = dict(github_repo=args.github_repo, author_name=args.author_name, author_email=args.author_email)
            if args.action in ('checkpoint', 'answer-checkpoint'):
                review = json.loads(Path(args.review).read_text(encoding='utf-8'))
                checkpoint = answer_checkpoint if args.action == 'answer-checkpoint' else section_checkpoint
                result = checkpoint(args.repository, args.base, args.session, payload, args.expected_head, review, **options)
            else:
                result = save(args.repository, args.base, args.session, payload, args.expected_head, **options)
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
        parser.exit(1, f'Chat-Sicherung nicht abgeschlossen ({reason(exc)}). Eingaben und Zugriff prüfen.\n')


if __name__ == '__main__':
    main()
