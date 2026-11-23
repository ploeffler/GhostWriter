"""Freigaberecht nicht aus frei editierbarem Namen ableiten, ohne Live-GitHub."""
import copy
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import approval_authority as aa
import build_openwebui_authority
from tests.authority_helpers import OWNER, REPOSITORY, fake_github


class AuthorityTest(unittest.TestCase):
    def setUp(self):
        self.data = {'/repos/ploeffler/test-book': copy.deepcopy(REPOSITORY), '/user': copy.deepcopy(OWNER)}
        self.authority = aa.ReviewAuthority(self.api, 'ploeffler/test-book')
        self.receipt = {'pull_request': 31, 'review_id': 41}
        self.payload = {'ghostwriter_approval': 1, 'repository_id': 21, 'book_branch': 'buch/a',
                        'edition': 1, 'purpose': 'edition', 'content_sha256': 'a' * 64}
        self.review = {'id': 41, 'node_id':'REVIEW41', 'user': copy.deepcopy(OWNER), 'state': 'COMMENTED',
                       'submitted_at': '2026-11-23T10:00:00Z', 'commit_id': 'a' * 40,
                       'pull_request_url': 'https://api.github.com/repos/ploeffler/test-book/pulls/31',
                       'body': json.dumps(self.payload)}
        self.data['/repos/ploeffler/test-book/pulls/31/reviews/41'] = self.review

    def api(self, path, data=None):
        if path == '/graphql':
            review=next(v for v in self.data.values() if v.get('node_id') == data['variables']['id'])
            return {'data':{'node':{'id':review['node_id'], 'lastEditedAt':review.get('_edited'),
                    'editor':review.get('_editor'), 'body':review['body'], 'state':review['state'],
                    'author':{'databaseId':review['user']['id'],'login':review['user']['login']},
                    'commit':{'oid':review['commit_id']}, 'pullRequest':{'number':31,
                    'repository':{'databaseId':21,'nameWithOwner':'ploeffler/test-book'}}}}}
        return self.data[path]

    def test_owner_review_and_personal_identity(self):
        result = self.authority.confirmation(self.receipt, self.payload)
        self.assertEqual(result['user_id'], OWNER['id'])
        self.assertEqual(result['by'], OWNER['login'])

    def test_repository_casing_uses_github_canonical_context(self):
        authority=aa.ReviewAuthority(lambda p,d=None:self.data['/repos/ploeffler/test-book'] if p.startswith('/repos/ploeffler/TEST-BOOK') else self.api(p,d),'ploeffler/TEST-BOOK')
        self.assertEqual(authority.confirmation(self.receipt,self.payload)['by'],'ploeffler')

    def test_same_login_with_another_id_is_not_owner(self):
        with self.assertRaises(ValueError):
            self.authority.authorize({**OWNER, 'id': 999})

    def test_organization_requires_active_owner_membership_for_exact_person(self):
        repository = copy.deepcopy(REPOSITORY)
        repository['owner'] = {'id': 10, 'login': 'writers', 'type': 'Organization'}
        membership_path = '/orgs/writers/memberships/ploeffler'
        for membership, permitted in (
                ({'state': 'active', 'role': 'admin', 'user': OWNER}, True),
                ({'state': 'active', 'role': 'member', 'user': OWNER}, False),
                ({'state': 'pending', 'role': 'admin', 'user': OWNER}, False),
                ({'state': 'active', 'role': 'admin', 'user': {**OWNER, 'id': 999}}, False),
                ({}, False)):
            with self.subTest(membership=membership):
                def api(path):
                    return membership if path == membership_path else repository
                authority = aa.ReviewAuthority(api, 'ploeffler/test-book')
                if permitted:
                    self.assertEqual(authority.authorize(OWNER), OWNER['login'])
                else:
                    with self.assertRaises(ValueError):
                        authority.authorize(OWNER)

    def test_unreadable_organization_membership_cannot_grant_owner_rights(self):
        repository = {**REPOSITORY, 'owner': {'id': 10, 'login': 'writers', 'type': 'Organization'}}
        def api(path):
            if path.startswith('/orgs/'):
                raise aa.AuthorityError('Mitgliedschaft nicht lesbar')
            return repository
        authority = aa.ReviewAuthority(api, 'ploeffler/test-book')
        with self.assertRaises(aa.AuthorityError):
            authority.authorize(OWNER)

    def test_partial_graphql_error_cannot_confirm_even_matching_review(self):
        def api(path, data=None):
            result = self.api(path, data)
            if path == '/graphql':
                result['errors'] = [{'message': 'Teilantwort nicht verlässlich'}]
            return result
        authority = aa.ReviewAuthority(api, 'ploeffler/test-book')
        with self.assertRaises(ValueError):
            authority.confirmation(self.receipt, self.payload)

    def test_reject_bot_pending_dismissed_and_foreign_review(self):
        for change in ({'state': 'PENDING'}, {'state': 'DISMISSED'}, {'state': 'CHANGES_REQUESTED'},
                       {'user': {**OWNER, 'type': 'Bot'}}, {'submitted_at': None},
                       {'pull_request_url': 'https://api.github.com/repos/evil/copy/pulls/31'}, {'id': 99}):
            with self.subTest(change=change):
                self.data['/repos/ploeffler/test-book/pulls/31/reviews/41'] = {**self.review, **change}
                authority = aa.ReviewAuthority(self.api, 'ploeffler/test-book')
                with self.assertRaises(ValueError): authority.confirmation(self.receipt, self.payload)

    def test_no_partial_match_or_replay_for_other_content_branch_edition_or_purpose(self):
        for key, value in (('content_sha256','b'*64), ('book_branch','buch/b'), ('repository_id',22),
                           ('edition',2), ('purpose','omnibus:ser-a')):
            with self.subTest(key=key), self.assertRaises(ValueError):
                self.authority.confirmation(self.receipt, {**self.payload, key: value})

    def test_explicit_owner_delegation_and_withdrawal(self):
        delegate = {'id': 2, 'login': 'editor', 'type': 'User'}
        grant = {'id': 42, 'node_id':'REVIEW42', 'user': OWNER, 'state': 'COMMENTED', 'submitted_at': 'now',
                 'commit_id': 'a'*40, 'pull_request_url': self.review['pull_request_url'],
                 'body': json.dumps({'ghostwriter_delegation':1,'repository_id':21,
                                    'delegate_id':2,'delegate_login':'editor','book_branch':'buch/a','permission':'approve'})}
        self.data['/repos/ploeffler/test-book/pulls/31/reviews/42'] = grant
        self.review['user'] = delegate
        proof = {**self.receipt, 'delegation': {'pull_request':31,'review_id':42}}
        self.assertEqual(self.authority.confirmation(proof,self.payload)['by'],'editor')
        with self.assertRaises(ValueError):
            self.authority.confirmation(proof,{**self.payload,'book_branch':'buch/b'})
        grant['state'] = 'DISMISSED'
        authority = aa.ReviewAuthority(self.api, 'ploeffler/test-book')
        with self.assertRaises(ValueError): authority.confirmation(proof,self.payload)

    def test_delegate_cannot_delegate_or_use_another_persons_grant(self):
        stranger = {'id':3,'login':'stranger','type':'User'}
        self.review['body'] = json.dumps({'ghostwriter_delegation':1,'repository_id':21,
                                         'delegate_id':2,'delegate_login':'editor','book_branch':'buch/a','permission':'approve'})
        with self.assertRaises(ValueError): self.authority.authorize(stranger,self.receipt,'buch/a')
        self.review['user'] = {'id':2,'login':'editor','type':'User'}
        with self.assertRaises(ValueError):
            aa.ReviewAuthority(self.api,'ploeffler/test-book').authorize(self.review['user'],self.receipt,'buch/a')

    def test_edited_owner_review_is_not_a_personal_authorization(self):
        self.review['_edited']='2026-11-23T12:00:00Z'
        with self.assertRaises(ValueError):self.authority.confirmation(self.receipt,self.payload)

    def test_own_draft_edit_before_submission_is_still_personally_attributed(self):
        self.review['_edited']='2026-11-23T09:59:00Z'
        self.review['_editor']={'databaseId':OWNER['id'],'login':OWNER['login']}
        self.assertEqual(self.authority.confirmation(self.receipt,self.payload)['by'],'ploeffler')

    def test_foreign_edit_even_at_submission_time_cannot_impersonate_owner(self):
        self.review['_edited']=self.review['submitted_at']
        self.review['_editor']={'databaseId':2,'login':'editor'}
        with self.assertRaises(ValueError):self.authority.confirmation(self.receipt,self.payload)

    def test_missing_original_review_metadata_fails_closed(self):
        del self.review['node_id']
        with self.assertRaises(ValueError):self.authority.confirmation(self.receipt,self.payload)

    def test_ambiguous_json_does_not_grant(self):
        self.review['body']=json.dumps(self.payload)[:-1]+', "edition": 1}'
        with self.assertRaises(ValueError):self.authority.confirmation(self.receipt,self.payload)

    def test_api_failure_does_not_grant(self):
        def failed(path): raise aa.AuthorityError('unavailable')
        with self.assertRaises(ValueError): aa.ReviewAuthority(failed,'ploeffler/test-book')

    def test_preparation_workflow_has_no_write_permissions_or_approval_action(self):
        workflow=yaml.safe_load((ROOT/'.github/workflows/approval.yml').read_text())
        self.assertEqual(workflow['permissions'],{'contents':'read','pull-requests':'read'})
        scripts='\n'.join(step.get('run','') for step in workflow['jobs']['prepare']['steps'])
        self.assertIn('approval_authority.py . "$ACTION"',scripts)
        self.assertIn('prepare|check',scripts)
        self.assertEqual(workflow[True]['workflow_dispatch']['inputs']['action']['options'],['prepare','check'])
        self.assertNotIn('approval_authority.py . attach',scripts)
        self.assertNotIn('git push',scripts)
        self.assertIn('"${args[@]}"',scripts)

    def test_standalone_openwebui_verifier_matches_shared_core(self):
        self.assertTrue(build_openwebui_authority.build(check=True))


class GateTest(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.base=Path(self.tmp.name)/'book'
        shutil.copytree(ROOT/'tests/fixtures/adhs',self.base)

    def test_unverified_legacy_by_blocks_output_before_writing(self):
        out=Path(self.tmp.name)/'book.md'
        result=subprocess.run([sys.executable,str(ROOT/'scripts/assemble.py'),str(self.base),'book','-o',str(out)],capture_output=True,text=True)
        self.assertNotEqual(result.returncode,0)
        self.assertFalse(out.exists())
        self.assertIn('Persönlicher Inhaltsnachweis',result.stderr)

    def test_real_cli_accepts_owner_review_and_rejects_tampering_without_network(self):
        fake_github(self,self.base,edition=3)
        self.assertEqual(aa.verify(self.base,3)['by'],'ploeffler')
        log=self.base/'approvals.yml'; data=yaml.safe_load(log.read_text())
        data['entries'].append({'by':'forged'})
        log.write_text(yaml.safe_dump(data))
        with self.assertRaises(aa.AuthorityError): aa.verify(self.base,3)

    def test_actual_review_commit_must_contain_the_confirmed_data(self):
        responses, path=fake_github(self,self.base,edition=1)
        chapter=next((self.base/'chapters').glob('*/sections/*.md'))
        chapter.write_text(chapter.read_text()+'\nUncommitted change.\n')
        repo, branch=aa.context(self.base)
        checker=aa.ReviewAuthority(lambda p:responses['/repos/'+repo],repo)
        from render_view import load
        _, config=load(self.base)
        body=json.dumps(aa.payload(self.base,checker,branch,1,config))
        responses['/repos/'+repo+'/pulls/31/reviews/41']['body']=body
        responses['/graphql']['data']['node']['body']=body
        path.write_text(json.dumps(responses))
        with self.assertRaises(aa.AuthorityError):aa.verify(self.base,1)

    def test_valid_legacy_by_change_still_passes_structure_but_not_personal_gate(self):
        from tests.test_assemble import AssembleTests
        AssembleTests.approve(self,1)
        fake_github(self,self.base,edition=1)
        log=self.base/'approvals.yml';data=yaml.safe_load(log.read_text())
        data['entries'][0]['by']='forged-name'
        log.write_text(yaml.safe_dump(data))
        from validate_project import check_project
        self.assertEqual(check_project(self.base),[])
        with self.assertRaises(aa.AuthorityError):aa.verify(self.base,1)

    def test_local_rule_relaxation_fails_before_file_changes_for_editor(self):
        responses,path=fake_github(self,self.base,seal=False)
        responses['/user']={'id':2,'login':'editor','type':'User'}
        path.write_text(json.dumps(responses))
        before=(self.base/'ghostwriter.yml').read_bytes()
        import rules
        with self.assertRaises(aa.AuthorityError):
            rules.apply(self.base,'facts','fiction',confirmed=True,by='ploeffler',commit='a'*40)
        self.assertEqual(before,(self.base/'ghostwriter.yml').read_bytes())

    def test_text_image_and_policy_changes_invalidate(self):
        fake_github(self,self.base,edition=1)
        for relative in ('chapters/new.md','images/new.png','ghostwriter.yml'):
            path=self.base/relative;path.parent.mkdir(parents=True,exist_ok=True)
            old=path.read_bytes() if path.exists() else None
            path.write_bytes((old or b'')+b'\nchanged')
            with self.subTest(path=relative),self.assertRaises(aa.AuthorityError): aa.verify(self.base,1)
            if old is None:path.unlink()
            else:path.write_bytes(old)

    def test_receipt_is_excluded_but_historical_names_are_bound(self):
        fake_github(self,self.base,seal=False)
        before=aa.snapshot(self.base)
        log=self.base/'approvals.yml'; data=yaml.safe_load(log.read_text())
        data['authority']={'pull_request':31,'review_id':41}
        log.write_text(yaml.safe_dump(data))
        self.assertEqual(before,aa.snapshot(self.base))

    def test_worker_can_only_prepare_review_text_without_changing_approvals(self):
        import io
        responses,path=fake_github(self,self.base,seal=False)
        del responses['/user']
        path.write_text(json.dumps(responses))
        before=(self.base/'approvals.yml').read_bytes()
        output=io.StringIO()
        with patch.dict(os.environ,{'GITHUB_ACTIONS':'true'}),patch('sys.stdout',output):
            self.assertEqual(aa.main([str(self.base),'prepare','--edition','1']),0)
        self.assertIn('content_sha256',json.loads(output.getvalue()))
        self.assertEqual(before,(self.base/'approvals.yml').read_bytes())

    def test_automated_worker_cannot_grant_as_a_person_even_with_a_user_token(self):
        with patch.dict(os.environ,{'GITHUB_ACTIONS':'true'}),patch.object(aa,'api') as api:
            with self.assertRaises(aa.AuthorityError):aa.require_actor(self.base,by='ploeffler')
        api.assert_not_called()

    def test_no_shared_token_or_claimed_name_is_an_identity(self):
        fake_github(self,self.base,seal=False)
        with self.assertRaises(aa.AuthorityError): aa.require_actor(self.base,by='someone-else')
        self.assertEqual(aa.require_actor(self.base,by='chat'),'ploeffler')

    def test_no_write_when_attach_review_missing(self):
        fake_github(self,self.base,seal=False)
        before=(self.base/'approvals.yml').read_bytes()
        self.assertEqual(aa.main([str(self.base),'attach','--pull-request','31','--review-id','999']),1)
        self.assertEqual(before,(self.base/'approvals.yml').read_bytes())

    def test_symlink_or_nested_checkout_cannot_be_authorized(self):
        fake_github(self,self.base)
        (self.base/'images').mkdir(exist_ok=True)
        (self.base/'images'/'foreign').symlink_to('/tmp')
        with self.assertRaises(aa.AuthorityError): aa.snapshot(self.base)
        with self.assertRaises(aa.AuthorityError): aa.context(self.base/'chapters')




try:
    import pydantic
except ImportError:
    pydantic = None


@unittest.skipIf(pydantic is None, 'Open-WebUI-Abhängigkeit pydantic fehlt')
class OpenWebUIAuthorityTest(unittest.TestCase):
    def setUp(self):
        import importlib.util
        path=ROOT/'integrations/openwebui/ghostwriter_github.py'
        spec=importlib.util.spec_from_file_location('authority_tool_test',path)
        self.module=importlib.util.module_from_spec(spec);spec.loader.exec_module(self.module)
        self.tool=self.module.Tools()
        self.tool.valves.GITHUB_TOKEN='SHARED_READ_ONLY_TEST_TOKEN'
        self.tool.valves.ALLOWED_REPOS='ploeffler/test-book'
        self.user={'valves':{'GITHUB_TOKEN':'PERSONAL_TEST_TOKEN'}}

    def run_tool(self,coroutine):
        import asyncio
        return json.loads(asyncio.run(coroutine))

    def test_shared_token_never_falls_back_to_writing(self):
        with patch.object(self.tool,'_http') as http:
            result=self.run_tool(self.tool.create_branch('ploeffler/test-book','ghostwriter/main','main'))
        self.assertFalse(result['ok']);http.assert_not_called()

    def test_known_shared_credential_cannot_be_resubmitted_as_personal_identity(self):
        for value in (self.tool.valves.GITHUB_TOKEN, ' '+self.tool.valves.GITHUB_TOKEN+' '):
            with self.subTest(value=value),patch.object(self.tool,'_http') as http:
                result=self.run_tool(self.tool.create_branch('ploeffler/test-book','ghostwriter/main','main',
                    __user__={'valves':{'GITHUB_TOKEN':value}}))
            self.assertFalse(result['ok']);http.assert_not_called()

    def test_personal_token_used_and_redacted_without_mutating_shared_config(self):
        class Response:
            status_code=200;headers={};content=b'{}'
            def json(self):return OWNER
        with patch.object(self.module.requests,'request',return_value=Response()) as request:
            result=self.run_tool(self.tool._write_run('ploeffler/test-book',lambda trace:'PERSONAL_TEST_TOKEN',self.user))
        self.assertTrue(result['ok'])
        self.assertNotIn('PERSONAL_TEST_TOKEN',json.dumps(result))
        self.assertEqual(request.call_args.kwargs['headers']['Authorization'],'Bearer PERSONAL_TEST_TOKEN')
        self.assertEqual(self.tool.valves.GITHUB_TOKEN,'SHARED_READ_ONLY_TEST_TOKEN')
        self.assertEqual(self.module._WRITE_TOKEN.get(),'')

    def test_bot_or_unknown_identity_never_writes(self):
        for principal in ({**OWNER,'type':'Bot'}, {'login':'ploeffler'}):
            with self.subTest(principal=principal),patch.object(self.tool,'_http',return_value=principal) as http:
                result=self.run_tool(self.tool.create_branch('ploeffler/test-book','ghostwriter/main','main',__user__=self.user))
                self.assertFalse(result['ok']);self.assertEqual(http.call_count,1)

    def test_forged_ledger_by_editor_is_rejected_before_any_post(self):
        def http(trace,method,path,*args,**kwargs):
            self.assertEqual(method,'GET')
            if path=='/user':return {'id':2,'login':'editor','type':'User'}
            if path=='/repos/ploeffler/test-book':return REPOSITORY
            if '/git/ref/' in path:return {'object':{'sha':'a'*40}}
            if '/contents/approvals.yml' in path:
                import base64
                return {'type':'file','sha':'x','encoding':'base64','content':base64.b64encode(b'entries: []\n').decode()}
            raise AssertionError(path)
        entries=json.dumps([{'path':'approvals.yml','content':'entries: [{by: ploeffler}]'}])
        with patch.object(self.tool,'_http',side_effect=http):
            result=self.run_tool(self.tool.commit_files('ploeffler/test-book','ghostwriter/main',entries,'Abschluss','a'*40,__user__=self.user))
        self.assertFalse(result['ok'])

    def test_editor_can_change_manuscript_without_changing_approval_state(self):
        old='---\nid: sec-a\nstatus: revision\napprovals:\n  writing: true\n  section: false\n---\nAlt'
        entries=[{'path':'chapters/a/sections/a.md','content':old.replace('Alt','Neu')}]
        with patch.object(self.tool,'_read_utf8',return_value={'content':old}),patch.object(self.tool,'_http') as http:
            self.tool._guard_approval_changes([], 'ploeffler/test-book','a'*40,entries)
        http.assert_not_called()

    def test_new_approval_cannot_use_a_different_actor_label(self):
        token=self.module._WRITE_USER.set(OWNER)
        try:
            with patch.object(self.tool,'_read_utf8',return_value={'content':'entries: []'}),patch.object(self.tool,'_http',return_value=REPOSITORY):
                with self.assertRaises(ValueError):
                    self.tool._guard_approval_changes([], 'ploeffler/test-book','a'*40,
                        [{'path':'approvals.yml','content':'entries: [{by: forged}]'}],'main')
        finally:self.module._WRITE_USER.reset(token)

    def test_approved_text_cannot_be_silently_changed(self):
        old='---\nstatus: approved\napprovals: {writing: true, section: true}\n---\nAlt'
        with patch.object(self.tool,'_read_utf8',return_value={'content':old}),patch.object(self.tool,'_http') as http:
            with self.assertRaises(ValueError):
                self.tool._guard_approval_changes([], 'ploeffler/test-book','a'*40,
                    [{'path':'chapters/a/sections/a.md','content':old.replace('Alt','Neu')}],'main')
        http.assert_not_called()

    def test_concurrent_users_keep_credentials_and_identity_separate(self):
        import asyncio
        import threading
        barrier=threading.Barrier(2,timeout=10)
        def http(trace,method,path,*args,**kwargs):
            token=self.module._WRITE_TOKEN.get()
            return {'id':1 if token=='A_TOKEN' else 2,'login':'alice' if token=='A_TOKEN' else 'bob','type':'User'}
        def operation(trace):
            barrier.wait()
            return {'login':self.module._WRITE_USER.get()['login'],'token':self.module._WRITE_TOKEN.get()}
        async def run():
            return await asyncio.gather(*(self.tool._write_run('ploeffler/test-book',operation,{'valves':{'GITHUB_TOKEN':token}}) for token in ('A_TOKEN','B_TOKEN')))
        with patch.object(self.tool,'_http',side_effect=http):
            output=asyncio.run(run())
        values=[json.loads(s)['result'] for s in output]
        self.assertEqual([r['login'] for r in values],['alice','bob'])
        self.assertEqual([r['token'] for r in values],['[TOKEN ENTFERNT]','[TOKEN ENTFERNT]'])
        self.assertEqual(self.module._WRITE_TOKEN.get(),'')

    def test_personal_credential_cannot_be_written_in_pr_or_file_contents(self):
        token=self.module._WRITE_TOKEN.set('PERSONAL_TEST_TOKEN')
        try:
            with patch.object(self.module.requests,'request') as request:
                with self.assertRaises(ValueError):
                    self.tool._http([], 'POST','/repos/ploeffler/test-book/pulls',data={'body':'PERSONAL_TEST_TOKEN'})
                request.assert_not_called()
        finally:self.module._WRITE_TOKEN.reset(token)

    def test_normal_editor_merge_does_not_decode_binary_images(self):
        self.tool.valves.ALLOW_WORKFLOW_DISPATCH=True
        calls=[]
        def http(trace,method,path,*args,**kwargs):
            calls.append((method,path))
            if path=='/user':return {'id':2,'login':'editor','type':'User'}
            if method=='PUT':return {'merged':True}
            if '/pulls/' in path:return {'head':{'sha':'b'*40},'base':{'sha':'a'*40,'ref':'main'}}
            if '/compare/' in path:return {'files':[{'filename':'images/picture.png','status':'added'}]}
            if '/git/ref/' in path:return {'object':{'sha':'a'*40}}
            raise AssertionError(path)
        with patch.object(self.tool,'_http',side_effect=http):
            result=self.run_tool(self.tool.merge_pull_request('ploeffler/test-book',1,'b'*40,__user__=self.user))
        self.assertTrue(result['ok'])
        self.assertEqual(sum(method=='PUT' for method,path in calls),1)
        self.assertFalse(any('/contents/' in path for method,path in calls))

    def test_preparation_dispatch_cannot_be_used_to_submit_or_attach_approvals(self):
        self.tool.valves.ALLOW_WORKFLOW_DISPATCH=True
        with patch.object(self.tool,'_http',return_value=OWNER) as http:
            result=self.run_tool(self.tool.dispatch_workflow('ploeffler/test-book','approval.yml','main',
                '{"action":"attach","edition":"1"}',__user__=self.user))
        self.assertFalse(result['ok'])
        self.assertTrue(all(call.args[1]=='GET' for call in http.call_args_list))

    def test_new_draft_is_not_a_privileged_grant(self):
        value=self.tool._privileged_state('chapters/a/sections/a.md','---\nstatus: revision\napprovals: {writing: false, section: false}\n---\nNeu')
        self.assertEqual(value,self.tool._privileged_state('chapters/a/sections/a.md',None))

if __name__ == '__main__':
    unittest.main()
