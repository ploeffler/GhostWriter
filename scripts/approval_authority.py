#!/usr/bin/env python3
"""Persönliche Freigaberechte und Inhaltsbestätigung über GitHub-Reviews.

Nur lesende GitHub-Aufrufe. prepare erzeugt einen Reviewtext, attach prüft einen
bereits ausdrücklich abgegebenen Review. Kein Review wird automatisch abgegeben.
"""
import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys

import yaml


class AuthorityError(ValueError):
    """Fehlender oder nicht verlässlich prüfbarer Freigabenachweis."""


# BEGIN SHARED REVIEW AUTHORITY
class ReviewAuthority:
    """Der API-Aufrufer liefert ausschließlich Antworten von api.github.com.

    Identität kommt aus /user bzw. review.user, niemals aus by oder Git-Autoren.
    Delegation ist ein ausdrücklicher, weiterhin gültiger Eigentümer-Review.
    """
    def __init__(self, api, repository):
        if not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+', repository):
            raise ValueError('GitHub-Repository fehlt oder ist ungültig')
        self.api, self.repository = api, repository
        self.root = '/repos/' + repository
        self.info = api(self.root)
        if (not isinstance(self.info, dict) or type(self.info.get('id')) is not int
                or str(self.info.get('full_name', '')).casefold() != repository.casefold()):
            raise ValueError('GitHub-Repository konnte nicht verifiziert werden')
        self.repository = self.info['full_name']
        self.root = '/repos/' + self.repository
        self.cache = {}

    @staticmethod
    def person(user):
        return (isinstance(user, dict) and user.get('type') == 'User'
                and type(user.get('id')) is int and user['id'] > 0
                and isinstance(user.get('login'), str)
                and re.fullmatch(r'[A-Za-z0-9-]+', user['login']))

    def owner(self, user):
        owner = self.info.get('owner') or {}
        if not self.person(user):
            return False
        if owner.get('type') == 'User':
            return user['id'] == owner.get('id')
        # Für Organisationen keine bloßen Schreib-/Maintainerrechte als Eigentum
        # ausgeben. Ein aktiver Organisationsinhaber muss über GitHub belegbar sein.
        if owner.get('type') == 'Organization':
            key = ('owner', user['id'])
            if key not in self.cache:
                result = self.api('/orgs/' + owner['login'] + '/memberships/' + user['login'])
                self.cache[key] = (result.get('state') == 'active' and result.get('role') == 'admin'
                                   and (result.get('user') or {}).get('id') == user['id'])
            return self.cache[key]
        return False

    def review(self, receipt):
        if (not isinstance(receipt, dict)
                or any(type(receipt.get(k)) is not int or receipt[k] <= 0
                       for k in ('pull_request', 'review_id'))):
            raise ValueError('GitHub-Reviewnachweis fehlt oder ist ungültig')
        key = (receipt['pull_request'], receipt['review_id'])
        if key not in self.cache:
            path = self.root + '/pulls/' + str(key[0]) + '/reviews/' + str(key[1])
            review = self.api(path)
            if (not isinstance(review, dict) or review.get('id') != key[1]
                    or review.get('state') not in ('APPROVED', 'COMMENTED')
                    or not review.get('submitted_at') or not self.person(review.get('user'))
                    or not re.fullmatch(r'[0-9a-f]{40}', str(review.get('commit_id', '')))
                    or review.get('pull_request_url') != 'https://api.github.com' + self.root + '/pulls/' + str(key[0])):
                raise ValueError('Review nicht abgegeben, zurückgenommen oder nicht persönlich zuordenbar')
            # Reviewtexte sind veränderbar. Daher zusätzlich den unveränderten
            # Originalreview verifizieren; ein unter fremdem Namen bearbeiteter
            # Text darf keine Eigentümer-Bevollmächtigung erzeugen.
            node_id = review.get('node_id')
            if not isinstance(node_id, str) or not node_id:
                raise ValueError('Originalreview nicht verifizierbar')
            query = """query($id:ID!){node(id:$id){... on PullRequestReview{
                id state body lastEditedAt editor{login ... on User{databaseId}} author{login ... on User{databaseId}}
                commit{oid} pullRequest{number repository{databaseId nameWithOwner}}}}}"""
            response = self.api('/graphql', {'query': query, 'variables': {'id': node_id}})
            if not isinstance(response, dict) or not isinstance(response.get('data'), dict):
                raise ValueError('Originalreview-Metadaten fehlen oder sind nicht lesbar')
            node = response['data'].get('node')
            if not isinstance(node, dict):
                raise ValueError('Originalreview nicht vorhanden')
            pull = node.get('pullRequest') if isinstance(node.get('pullRequest'), dict) else {}
            repository = pull.get('repository') if isinstance(pull.get('repository'), dict) else {}
            author = node.get('author') if isinstance(node.get('author'), dict) else {}
            edited = node.get('lastEditedAt')
            editor = node.get('editor')
            unchanged = 'lastEditedAt' in node and 'editor' in node and edited is None and editor is None
            if edited is not None and isinstance(editor, dict):
                try:
                    edit_time = datetime.datetime.fromisoformat(edited.replace('Z', '+00:00'))
                    submit_time = datetime.datetime.fromisoformat(review['submitted_at'].replace('Z', '+00:00'))
                    # Eigene Entwurfskorrekturen vor dem ersten Absenden sind
                    # zulässig. Nachträgliche oder fremde Bearbeitungen nicht.
                    unchanged = (edit_time.tzinfo is not None and submit_time.tzinfo is not None
                                 and edit_time <= submit_time
                                 and editor.get('databaseId') == review['user']['id']
                                 and editor.get('login') == review['user']['login'])
                except (ValueError, TypeError, AttributeError):
                    unchanged = False
            if (response.get('errors') or node.get('id') != node_id
                    or not unchanged
                    or node.get('body') != review.get('body') or node.get('state') != review['state']
                    or author.get('databaseId') != review['user']['id']
                    or author.get('login') != review['user']['login']
                    or (node.get('commit') or {}).get('oid') != review['commit_id']
                    or pull.get('number') != key[0]
                    or repository.get('databaseId') != self.info['id']
                    or str(repository.get('nameWithOwner', '')).casefold() != self.repository.casefold()):
                raise ValueError('Review bearbeitet oder Herkunft nicht eindeutig verifiziert; neuen Review abgeben')
            def unique(pairs):
                value = dict(pairs)
                if len(value) != len(pairs):
                    raise ValueError('Mehrdeutiger Reviewtext')
                return value
            try:
                body = json.loads(review.get('body') or '', object_pairs_hook=unique)
            except (ValueError, TypeError):
                raise ValueError('Review enthält keinen ausdrücklichen GhostWriter-Nachweis') from None
            if not isinstance(body, dict):
                raise ValueError('Review enthält keinen gültigen GhostWriter-Nachweis')
            self.cache[key] = (review, body)
        return self.cache[key]

    def authorize(self, user, delegation=None, book_branch=None):
        if not self.person(user):
            raise ValueError('Persönliches GitHub-Konto erforderlich; Bot oder unbekanntes Konto gesperrt')
        if self.owner(user):
            return user['login']
        if not isinstance(book_branch, str) or not book_branch:
            raise ValueError('Buchzuordnung der Bevollmächtigung fehlt')
        review, body = self.review(delegation)
        expected = {'ghostwriter_delegation': 1, 'repository_id': self.info['id'],
                    'delegate_id': user['id'], 'delegate_login': user['login'], 'book_branch': book_branch, 'permission': 'approve'}
        if json.dumps(body, sort_keys=True) != json.dumps(expected, sort_keys=True) or not self.owner(review['user']):
            raise ValueError('Keine ausdrückliche, gültige Freigabeberechtigung des Eigentümers')
        return user['login']

    def confirmation(self, receipt, payload):
        review, body = self.review(receipt)
        if json.dumps(body, sort_keys=True) != json.dumps(payload, sort_keys=True):
            raise ValueError('Freigabenachweis passt nicht zu Buch, Inhalt oder Auflage')
        login = self.authorize(review['user'], receipt.get('delegation'), payload['book_branch'])
        return {'by': login, 'user_id': review['user']['id'], 'commit': review['commit_id'],
                'pull_request': receipt['pull_request'], 'review_id': receipt['review_id']}
# END SHARED REVIEW AUTHORITY


def api(path, data=None):
    """GitHub-CLI verwendet vorhandene Anmeldung; keine Schlüsselwerte lesen."""
    try:
        command = ['gh', 'api', '--hostname', 'github.com', path, '-H', 'Accept: application/vnd.github+json']
        if data is not None:
            command += ['--method', 'POST', '--input', '-']
        result = subprocess.run(command, input=json.dumps(data) if data is not None else None,
                                capture_output=True, text=True, timeout=45)
        if result.returncode:
            raise AuthorityError('GitHub-Nachweis nicht abrufbar; Anmeldung und Leserechte prüfen')
        return json.loads(result.stdout)
    except (OSError, subprocess.TimeoutExpired, json.JSONDecodeError):
        raise AuthorityError('GitHub-Nachweis nicht abrufbar; keine Freigabe bestätigt') from None


def git(base, *args):
    result = subprocess.run(['git', '-C', str(base), *args], capture_output=True, text=True)
    if result.returncode:
        raise AuthorityError('Repository-/Buchzuordnung nicht verlässlich bestimmbar')
    return result.stdout.strip()


def context(base):
    """Nur echte Arbeitskopie, kein aus Buchdateien behauptetes Repository."""
    base = Path(base).resolve()
    if Path(git(base, 'rev-parse', '--show-toplevel')).resolve() != base:
        raise AuthorityError('Freigabenachweis braucht die Wurzel der Buch-Arbeitskopie')
    remote = git(base, 'remote', 'get-url', 'origin')
    match = re.fullmatch(r'(?:https://github\.com/|git@github\.com:)([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+?)(?:\.git)?', remote)
    if not match:
        raise AuthorityError('Freigabenachweis benötigt eine eindeutige GitHub-Herkunft')
    result = subprocess.run(['git', '-C', str(base), 'symbolic-ref', '-q', '--short', 'HEAD'],
                            capture_output=True, text=True)
    branch = result.stdout.strip()
    if not branch:
        # GitHub Actions checkt getrennte Commitstände aus. Herkunft und Workspace
        # werden abgeglichen, statt einen frei gespeicherten Buchbranch zu glauben.
        workspace = os.environ.get('GITHUB_WORKSPACE', '')
        if (os.environ.get('GITHUB_ACTIONS') != 'true' or not workspace
                or Path(workspace).resolve() != base
                or os.environ.get('GITHUB_REPOSITORY', '').casefold() != match[1].casefold()):
            raise AuthorityError('Buchbranch bei getrenntem Commitstand nicht verifiziert')
        branch = os.environ.get('GITHUB_REF_NAME', '')
    if branch.startswith('ghostwriter/'):
        branch = branch[len('ghostwriter/'):]
    if not branch or branch.startswith(('refs/', 'ghostwriter/', 'chat/')):
        raise AuthorityError('Kein eindeutiger Buchbranch für die Freigabe')
    return match[1], branch


# Inhalt und sämtliche Buchdaten, die in die Ausgabe einfließen können. Programm-
# code bleibt die separat vertrauenswürdige Installation. Anhänge/Sitzungen werden
# nicht übertragen; nur lokale Hashes gehen in den Reviewtext ein.
ROOT_FILES = ('ghostwriter.yml', 'approvals.yml', 'assistant.yml')
ROOT_DIRS = ('chapters', 'matter', 'images', 'reference-images', 'cover', 'characters',
             'story', 'series', 'research', 'context', 'costs', 'editions', 'import')


def snapshot(base, config=None, tree_commit=None):
    base = Path(base).resolve()
    files = []
    def unreadable(error):
        raise AuthorityError('Buchablage nicht vollständig lesbar')
    for name in ROOT_FILES + ROOT_DIRS:
        path = base / name
        if path.is_symlink():
            raise AuthorityError('Verlinkte Buchablage kann nicht freigegeben werden')
        if not path.exists():
            continue
        if path.is_dir():
            for folder, dirs, names in os.walk(path, followlinks=False, onerror=unreadable):
                for entry in dirs + names:
                    if (Path(folder) / entry).is_symlink():
                        raise AuthorityError('Verlinkte Buchdatei kann nicht freigegeben werden')
                files.extend(Path(folder) / n for n in names)
        else:
            files.append(path)
    hashes = {'approvals.yml': hashlib.sha256(json.dumps({'entries': []}, sort_keys=True).encode()).hexdigest()}
    contents = {}
    if tree_commit is not None:
        if not re.fullmatch(r'[0-9a-f]{40}', tree_commit):
            raise AuthorityError('Review-Ausgangsstand ungültig')
        tree = subprocess.run(['git', '-C', str(base), 'ls-tree', '-rz', tree_commit], capture_output=True)
        if tree.returncode:
            raise AuthorityError('Review-Ausgangsstand lokal nicht vorhanden; erst den PR-Stand abrufen')
        for entry in tree.stdout.split(b'\0'):
            if not entry:
                continue
            header, name = entry.split(b'\t', 1)
            relative = name.decode('utf-8')
            if relative not in ROOT_FILES and not relative.startswith(tuple(n + '/' for n in ROOT_DIRS)):
                continue
            mode, kind, object_id = header.split(b' ')
            if kind != b'blob' or mode == b'120000':
                raise AuthorityError('Verlinkte oder fremde Buchablage im Reviewstand')
            value = subprocess.run(['git', '-C', str(base), 'cat-file', 'blob', object_id.decode('ascii')], capture_output=True)
            if value.returncode:
                raise AuthorityError('Review-Inhalt nicht lesbar')
            contents[relative] = value.stdout
    else:
        for path in sorted(set(files)):
            contents[path.relative_to(base).as_posix()] = path.read_bytes()
    for relative, data in contents.items():
        if relative == 'approvals.yml':
            log = yaml.safe_load(data.decode('utf-8')) or {}
            if not isinstance(log, dict):
                raise AuthorityError('Freigabeprotokoll ungültig')
            log = {k: v for k, v in log.items() if k != 'authority'}
            log.setdefault('entries', [])
            data = json.dumps(log, sort_keys=True, ensure_ascii=False, default=str).encode()
        hashes[relative] = hashlib.sha256(data).hexdigest()
    if config is not None and config.get('_series'):
        # Tatsächlich geladene Seriendaten zusätzlich binden (können aus main
        # kommen und deshalb außerhalb des Buch-Arbeitsbaums liegen).
        hashes[':effective_series'] = hashlib.sha256(
            json.dumps(config['_series'], sort_keys=True, ensure_ascii=False, default=str).encode()).hexdigest()
        import series
        hashes[':series_glossary'] = hashlib.sha256(
            json.dumps(series.glossary(base, config['_series']['id']), sort_keys=True,
                       ensure_ascii=False, default=str).encode()).hexdigest()
        hashes[':series_also'] = hashlib.sha256(series.also_markdown(base, config['_series']).encode()).hexdigest()
    # Sammelbände lesen veröffentlichte Bände aus Tags, nicht nur lokale Dateien.
    refs = subprocess.run(['git', '-C', str(base), 'for-each-ref', '--format=%(refname) %(objectname)', 'refs/tags'], capture_output=True, text=True)
    if refs.returncode == 0:
        hashes[':published_refs'] = hashlib.sha256(refs.stdout.encode()).hexdigest()
    return hashlib.sha256(json.dumps(hashes, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def ledger(base):
    path = Path(base) / 'approvals.yml'
    value = yaml.safe_load(path.read_text(encoding='utf-8')) if path.is_file() else {}
    if not isinstance(value, dict):
        raise AuthorityError('Freigabeprotokoll ungültig')
    return value


def payload(base, authority, branch, edition, config=None, purpose='edition'):
    return {'ghostwriter_approval': 1, 'repository_id': authority.info['id'],
            'book_branch': branch, 'edition': edition, 'purpose': purpose, 'content_sha256': snapshot(base, config)}


def require_actor(base, by=None, api_call=None):
    if os.environ.get('GITHUB_ACTIONS') == 'true':
        raise AuthorityError('Automatisierte Jobs dürfen keine neuen persönlichen Freigaben erteilen')
    repo, branch = context(base)
    try:
        authority = ReviewAuthority(api_call or api, repo)
        user = authority.api('/user')
        receipt = ledger(base).get('authority') or {}
        login = authority.authorize(user, receipt.get('delegation'), branch)
        if by not in (None, '', 'chat') and str(by).casefold() != login.casefold():
            raise AuthorityError('Protokollname stimmt nicht mit dem verifizierten GitHub-Konto überein')
        return login
    except (ValueError, KeyError, TypeError, OSError, yaml.YAMLError):
        raise AuthorityError('Freigabe gesperrt: persönliches Konto oder ausdrückliches Freigaberecht nicht verifiziert') from None


def verify(base, edition=None, config=None, receipt=None, api_call=None, purpose='edition'):
    """Fehlender Zugang, Legacy-Eintrag oder abweichender Inhalt: immer sperren."""
    try:
        proof = receipt if receipt is not None else ledger(base).get('authority')
        if not proof:
            raise AuthorityError('Persönlicher Inhaltsnachweis fehlt; Probedruck bleibt möglich')
        repo, branch = context(base)
        if config is None:
            from render_view import load
            _, config = load(base)
        from validate_project import check_project
        if check_project(base):
            raise AuthorityError('Buchstruktur ungültig; erst die Projektfehler beheben')
        paths = [c['path'] for c in config['structure']['chapters']]
        paths += [s['path'] for c in config['structure']['chapters'] for s in c['sections']]
        paths += [m['path'] for side in ('front_matter', 'back_matter') for m in config['structure'].get(side, [])]
        paths += [c['path'] for c in config.get('characters', [])]
        paths += [v for k, v in (config.get('cover') or {}).items() if k in ('image', 'front', 'author_image') and v]
        if any(Path(p).is_absolute() or '\\' in p or any(part in ('', '.', '..') for part in p.split('/')) for p in paths):
            raise AuthorityError('Buchdatei außerhalb der bestätigten Ablage')
        authority = ReviewAuthority(api_call or api, repo)
        edition = config['project'].get('current_edition', 0) if edition is None else edition
        expected = payload(base, authority, branch, edition, config, purpose)
        result = authority.confirmation(proof, expected)
        if snapshot(base, config, tree_commit=result['commit']) != expected['content_sha256']:
            raise AuthorityError('Aktueller Inhalt stimmt nicht mit dem tatsächlichen Review-Commit überein')
        return result
    except AuthorityError:
        raise
    except (ValueError, KeyError, TypeError, OSError, yaml.YAMLError):
        raise AuthorityError('Persönlicher Inhaltsnachweis ungültig, veraltet oder nicht abrufbar') from None


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('project', type=Path)
    parser.add_argument('action', choices=('actor', 'prepare', 'attach', 'check', 'delegate'))
    parser.add_argument('--edition', type=int)
    parser.add_argument('--omnibus', help='Serienkennung für einen Sammelbandnachweis')
    parser.add_argument('--pull-request', type=int)
    parser.add_argument('--review-id', type=int)
    parser.add_argument('--delegation-pull-request', type=int)
    parser.add_argument('--delegation-review-id', type=int)
    parser.add_argument('--delegate-login')
    args = parser.parse_args(argv)
    try:
        purpose = 'omnibus:' + args.omnibus if args.omnibus else 'edition'
        if args.delegate_login and not re.fullmatch(r'[A-Za-z0-9-]+', args.delegate_login):
            raise AuthorityError('Ungültiges Zielkonto')
        repo, branch = context(args.project)
        authority = ReviewAuthority(api, repo)
        if args.action == 'actor':
            if os.environ.get('GITHUB_ACTIONS') == 'true':
                raise AuthorityError('Automatisierter Job ist keine persönliche Freigabe')
            body = {'by': authority.authorize(api('/user'), (ledger(args.project).get('authority') or {}).get('delegation'), branch)}
        elif args.action == 'delegate':
            user = api('/users/' + (args.delegate_login or ''))
            if not authority.person(user):
                raise AuthorityError('Persönliches Zielkonto für die Bevollmächtigung fehlt')
            body = {'ghostwriter_delegation': 1, 'repository_id': authority.info['id'],
                    'delegate_id': user['id'], 'delegate_login': user['login'], 'book_branch': branch, 'permission': 'approve'}
        elif args.action == 'prepare':
            from render_view import load
            _, config = load(args.project)
            edition = config['project'].get('current_edition', 0) if args.edition is None else args.edition
            body = payload(args.project, authority, branch, edition, config, purpose)
        elif args.action == 'check':
            body = verify(args.project, args.edition, purpose=purpose)
        else:
            proof = {'pull_request': args.pull_request, 'review_id': args.review_id}
            if args.delegation_pull_request or args.delegation_review_id:
                proof['delegation'] = {'pull_request': args.delegation_pull_request,
                                       'review_id': args.delegation_review_id}
            body = verify(args.project, args.edition, receipt=proof, purpose=purpose)
            # Erst nach erfolgreicher Prüfung schreiben. Kein automatischer Commit,
            # keine Übertragung und keine fingierte Freigabe bei API-Fehlern.
            path = args.project / 'approvals.yml'
            data = ledger(args.project)
            data.setdefault('entries', [])
            data['authority'] = proof
            path.write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False), encoding='utf-8')
        print(json.dumps(body, ensure_ascii=False, indent=2))
        return 0
    except (AuthorityError, ValueError, KeyError, TypeError, OSError, yaml.YAMLError) as error:
        # Fremde API-/Dateiinhalte niemals in Fehlermeldungen übernehmen.
        print('✗ Persönliche Freigabe nicht bestätigt. Konto, Review und aktuellen Inhalt prüfen.', file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
