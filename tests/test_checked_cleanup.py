"""B03: Action und CLI gegen ein lokales Git-Remote mit konkurrierenden Commits.

Der gh-Ersatz bildet nur die dokumentierte GraphQL-CAS-Semantik nach. Kein
GitHub-Zugriff, keine Aussage über tatsächliche Server-/Tokenberechtigungen.
"""
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import yaml

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('checked_delete', ROOT / 'scripts/delete_checked_branch.py')
checked = importlib.util.module_from_spec(spec)
spec.loader.exec_module(checked)

# Echte Git-CAS-Transaktion statt bloßer Erfolgsmeldung des Mocks.
GH_STUB = r'''#!/usr/bin/env python3
import json,os,subprocess,sys
from pathlib import Path
p=Path(os.environ['FAKE_STATE']);state=json.loads(p.read_text());args=sys.argv[1:]
path=args[1] if len(args)>1 else ''
def git(*a, **kw):
 return subprocess.run(['git','--git-dir',state['remote'],*a],capture_output=True,text=True,**kw)
if args[:2]==['api','graphql']:
 d=json.load(sys.stdin);inp=d['variables']['input'];updates=inp['refUpdates'];state['mutations']+=1
 ref=updates[0]['name']
 if state.get('race'):
  git('update-ref',ref,state['new'],state['old'],check=True);state['race']=False
 if state.get('tag_race'):
  git('update-ref','refs/tags/v0.1',state['new'],check=True);state['tag_race']=False
 transaction='start\n'
 for u in updates:
  if 'beforeOid' not in u: raise SystemExit('Missing beforeOid')
  if u['afterOid']=='0'*40: transaction+='delete '+u['name']+' '+u['beforeOid']+'\n'
  elif u['afterOid']==u['beforeOid']: transaction+='verify '+u['name']+' '+u['beforeOid']+'\n'
  else: raise SystemExit('Unexpected write')
 transaction+='prepare\ncommit\n'
 r=git('update-ref','--stdin',input=transaction)
 if r.returncode: print(json.dumps({'errors':[{'message':'head/tag changed'}]}))
 else: print(json.dumps({'data':{'updateRefs':{'clientMutationId':inp['clientMutationId']}}}))
 p.write_text(json.dumps(state));sys.exit(0)
if path.endswith('/branches'): print('codex/merged')
elif '/branches/' in path: print(state['old'])
elif '/pulls?' in path: print('7' if 'state=closed' in path else '0')
elif '/compare/' in path: print('0')
elif path=='repos/owner/test': print('R_test')
else: raise SystemExit('Unexpected gh call: '+repr(args))
'''


class CheckedCleanupTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.repo = self.root / 'repo'
        self.remote = self.root / 'remote.git'
        subprocess.run(['git', 'init', '-q', '--bare', str(self.remote)], check=True)
        self.repo.mkdir()
        self.git('init', '-q', '-b', 'main')
        self.git('config', 'user.name', 'Test')
        self.git('config', 'user.email', 'test@example.invalid')
        (self.repo / 'text.md').write_text('alt')
        self.git('add', '.')
        self.git('commit', '-qm', 'Alt')
        self.old = self.git('rev-parse', 'HEAD')
        (self.repo / 'text.md').write_text('neu')
        self.git('commit', '-qam', 'Neu')
        self.new = self.git('rev-parse', 'HEAD')
        self.git('remote', 'add', 'origin', str(self.remote))
        self.git('branch', 'codex/merged', self.old)
        self.git('branch', 'v0.1', self.old)
        self.git('push', '-q', 'origin', 'main', 'codex/merged', 'v0.1')
        self.git('fetch', '-q', 'origin')
        (self.repo / 'scripts').mkdir()
        shutil.copy(ROOT / 'scripts/delete_checked_branch.py', self.repo / 'scripts/delete_checked_branch.py')
        bin_dir = self.root / 'bin';bin_dir.mkdir()
        (bin_dir / 'gh').write_text(GH_STUB.replace('#!/usr/bin/env python3', '#!' + sys.executable, 1))
        (bin_dir / 'gh').chmod(0o755)
        self.state = self.root / 'state.json'
        self.env = {**os.environ, 'PATH': str(bin_dir) + os.pathsep + os.environ['PATH'],
                    'FAKE_STATE': str(self.state), 'GITHUB_REPOSITORY': 'owner/test',
                    'GITHUB_STEP_SUMMARY': str(self.root / 'summary'), 'GH_TOKEN': 'FAKE',
                    'R': 'owner/test', 'OWNER': 'owner', 'BASE': 'main', 'DRY': 'false',
                    'PATTERN': '^(codex|ghostwriter)/', 'KEEP': '^test/test-book$'}

    def git(self, *args):
        return subprocess.run(['git', '-C', str(self.repo), *args],check=True,capture_output=True,text=True).stdout.strip()

    def action(self, version=False, race=False, tag_race=False, dry=False):
        self.state.write_text(json.dumps({'remote': str(self.remote), 'old': self.old, 'new': self.new,
                                         'race': race, 'tag_race': tag_race, 'mutations': 0}))
        workflow = yaml.safe_load((ROOT / '.github/workflows/cleanup.yml').read_text())
        steps = workflow['jobs']['cleanup']['steps']
        script = next(s['run'] for s in steps if s.get('name') == ('Versions-Branches zu Tags' if version else 'Erledigte Branches löschen'))
        env = {**self.env, 'DRY': 'true' if dry else 'false'}
        r = subprocess.run(['bash', '-e', '-o', 'pipefail', '-c', script], cwd=self.repo, env=env,capture_output=True,text=True)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        return json.loads(self.state.read_text())

    def remote_head(self, branch):
        r = subprocess.run(['git', '--git-dir', str(self.remote), 'rev-parse', '--verify', 'refs/heads/' + branch], capture_output=True,text=True)
        return r.stdout.strip() if r.returncode == 0 else None

    def test_action_deletes_matching_head(self):
        state = self.action()
        self.assertEqual(state['mutations'], 1)
        self.assertIsNone(self.remote_head('codex/merged'))

    def test_action_keeps_commit_arriving_after_precheck(self):
        state = self.action(race=True)
        self.assertEqual(state['mutations'], 1)
        self.assertEqual(self.remote_head('codex/merged'), self.new)
        self.assertIn('Löschung unbestätigt', (self.root / 'summary').read_text())

    def test_version_branch_deletion_preserves_tag(self):
        self.action(version=True)
        self.assertIsNone(self.remote_head('v0.1'))
        target = subprocess.check_output(['git', '--git-dir', str(self.remote), 'rev-parse', 'refs/tags/v0.1^{commit}'],text=True).strip()
        self.assertEqual(target, self.old)

    def test_version_branch_keeps_new_commit(self):
        self.action(version=True, race=True)
        self.assertEqual(self.remote_head('v0.1'), self.new)

    def test_version_branch_kept_if_preserving_tag_changes(self):
        self.action(version=True, tag_race=True)
        self.assertEqual(self.remote_head('v0.1'), self.old)

    def test_dry_runs_make_no_mutation(self):
        for version in (False, True):
            with self.subTest(version=version):
                self.assertEqual(self.action(version=version, dry=True)['mutations'], 0)
                self.assertIn('würde' if version else 'Würden', (self.root / 'summary').read_text())
        self.assertEqual(self.remote_head('codex/merged'), self.old)
        self.assertEqual(self.remote_head('v0.1'), self.old)

    def test_cli_rejects_incomplete_or_unsafe_candidates_without_gh(self):
        for branch, head in [('main', self.old), ('buch/test', self.old), ('test/test-book', self.old),
                             ('codex/a', '0'*40), ('codex/a', 'bad')]:
            with self.subTest(branch=branch,head=head), patch.object(checked.subprocess, 'run') as run:
                # Validierung von Branch-Format wird ggf. lokal ausgeführt, nie gh.
                run.return_value.returncode = 0
                with self.assertRaises(ValueError):
                    checked.request_payload('R_test', branch, head)
                self.assertTrue(all(c.args[0][0] != 'gh' for c in run.call_args_list))
        with self.assertRaises(ValueError):
            checked.request_payload('R_test', 'codex/a..b', self.old)

    def test_cli_uncertain_or_error_response_never_reports_success_or_retries(self):
        for stdout, code in [('{}',0), ('{"errors":[{}]}',0), ('not json',0), ('',1),
                             ('{"data":{"updateRefs":{"clientMutationId":"wrong"}}}',0)]:
            with self.subTest(stdout=stdout), patch.object(checked, 'request_payload', return_value={}), \
                 patch.object(checked.subprocess, 'run', return_value=subprocess.CompletedProcess([],code,stdout,'secret must not be printed')) as run:
                self.assertEqual(checked.main(['--repository-id','R_test','--branch','codex/a','--expected-head',self.old]),1)
                self.assertEqual(run.call_count,1)
