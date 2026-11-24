"""GitHub-Attrappe für echte CLI-Aufrufe, keine Umgehungsoption im Programm."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from unittest.mock import patch
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import approval_authority

OWNER = {'id': 1, 'login': 'ploeffler', 'type': 'User'}
REPOSITORY = {'id': 21, 'full_name': 'ploeffler/test-book', 'owner': OWNER}


def fake_github(case, base, edition=0, purpose='edition', seal=True):
    """Jede Testkopie erhält eine eigene API-Attrappe; keinerlei echte Anmeldung."""
    base = Path(base).resolve()
    own_git = (base / '.git').exists()
    if not own_git:
        subprocess.run(['git', '-C', str(base), 'init', '-q', '-b', 'main'], check=True, capture_output=True)
        subprocess.run(['git', '-C', str(base), 'remote', 'add', 'origin', 'https://github.com/ploeffler/test-book.git'], check=True)
    remote = subprocess.run(['git', '-C', str(base), 'remote', 'get-url', 'origin'], capture_output=True, text=True)
    if remote.returncode:
        subprocess.run(['git', '-C', str(base), 'remote', 'add', 'origin', 'https://github.com/ploeffler/test-book.git'], check=True)
    if not (base / 'approvals.yml').exists():
        (base / 'approvals.yml').write_text('entries: []\n')
    # Existierende Serien-Fixtures behalten ihr Repository und ihre Branches.
    repo, branch = approval_authority.context(base)
    info = {**REPOSITORY, 'full_name': repo}
    authority = approval_authority.ReviewAuthority(lambda p: info, repo)
    from render_view import load
    _, config = load(base)
    subprocess.run(['git', '-C', str(base), 'add', '-A'], check=True, capture_output=True)
    subprocess.run(['git', '-C', str(base), '-c', 'user.name=Test author', '-c', 'user.email=test@example.invalid', 'commit', '-qm', 'Teststand', '--allow-empty'], check=True, capture_output=True)
    commit = subprocess.run(['git', '-C', str(base), 'rev-parse', 'HEAD'], check=True, capture_output=True, text=True).stdout.strip()
    body = approval_authority.payload(base, authority, branch, edition, config, purpose)
    review = {'id': 41, 'node_id': 'REVIEW41', 'state': 'COMMENTED', 'submitted_at': '2026-11-23T10:00:00Z',
              'commit_id': commit, 'user': OWNER, 'body': json.dumps(body),
              'pull_request_url': 'https://api.github.com/repos/' + repo + '/pulls/31'}
    node = {'id':'REVIEW41', 'lastEditedAt':None, 'editor':None, 'body':review['body'],
            'state':review['state'], 'author':{'databaseId':OWNER['id'],'login':OWNER['login']},
            'commit':{'oid':review['commit_id']}, 'pullRequest':{'number':31, 'repository':{'databaseId':info['id'],'nameWithOwner':repo}}}
    responses = {'/graphql':{'data':{'node':node}}, '/repos/' + repo: info, '/user': OWNER,
                 '/repos/' + repo + '/pulls/31/reviews/41': review}
    tmp = tempfile.TemporaryDirectory()
    case.addCleanup(tmp.cleanup)
    folder = Path(tmp.name)
    (folder / 'responses.json').write_text(json.dumps(responses))
    gh = folder / 'gh'
    gh.write_text('#!' + sys.executable + '\nimport json,sys\nfrom pathlib import Path\n'
                  + 'responses=json.loads(Path(' + repr(str(folder / 'responses.json')) + ').read_text())\n'
                  + 'path=sys.argv[sys.argv.index("github.com")+1]\n'
                  + 'if path not in responses: sys.exit(1)\n'
                  + 'print(json.dumps(responses[path]))\n')
    gh.chmod(0o700)
    environment = patch.dict(os.environ, {'PATH': str(folder) + os.pathsep + os.environ.get('PATH', ''), 'GITHUB_ACTIONS': 'false'})
    environment.start()
    case.addCleanup(environment.stop)
    if seal:
        path = base / 'approvals.yml'
        data = yaml.safe_load(path.read_text()) if path.exists() else {'entries': []}
        data['authority'] = {'pull_request': 31, 'review_id': 41}
        path.write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False))
    return responses, folder / 'responses.json'
