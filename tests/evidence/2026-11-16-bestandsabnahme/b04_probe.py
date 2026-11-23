"""Lokaler B04-Befundnachweis, kein Regressionstest für erwünschtes Verhalten.

Gibt beobachtete Schutzgrenzen aus. Bei späterer Behebung muss dieser Diagnose-
Nachweis neu bewertet werden; die bisherige Lücke wird nicht als Soll festgelegt.
"""
import argparse
import asyncio
import importlib.util
import inspect
import json
import sys
from pathlib import Path
from unittest.mock import patch

ap = argparse.ArgumentParser()
ap.add_argument('--source', required=True)
ap.add_argument('--output', required=True)
args = ap.parse_args()
source = Path(args.source).resolve()
sys.path[:0] = [str(source / 'tests'), str(source / 'scripts')]
import yaml
import assemble
import validate_project
from render_view import load
from test_book_lifecycle import BookLifecycleTest

case = BookLifecycleTest()
case.setUp()
try:
    case.complete_local_lifecycle()
    _, cfg = load(case.repo)
    baseline = validate_project.check_project(case.repo)
    assert not baseline
    ledger_path = case.repo / 'approvals.yml'
    ledger = yaml.safe_load(ledger_path.read_text())
    for entry in ledger['entries']:
        entry['by'] = 'nicht-authentifizierter-testname'
    ledger_path.write_text(yaml.safe_dump(ledger, allow_unicode=True, sort_keys=False))
    forged_by_errors = validate_project.check_project(case.repo)
    forged_by_assembly = assemble.problems(assemble.book_parts(case.repo, cfg), cfg)
    # Vorhandene Inhaltsintegrität wird unabhängig davon nachgewiesen.
    section = case.repo / case.section
    saved = section.read_text()
    section.write_text(saved.replace(case.manuscript, case.manuscript + ' Unbestätigter Text.'))
    changed_text_errors = validate_project.check_project(case.repo)
    changed_text_assembly = assemble.problems(assemble.book_parts(case.repo, cfg), cfg)
    assert changed_text_errors and changed_text_assembly
    result = {'base_commit': '007f529b9b38543b019e9859f195aaf5cb96cff2',
              'baseline_validation_errors': len(baseline),
              'ledger_by_replaced_without_authenticated_identity': True,
              'validation_errors_after_by_change': len(forged_by_errors),
              'assembly_errors_after_by_change': len(forged_by_assembly),
              'manuscript_change_detected_by_validator': bool(changed_text_errors),
              'manuscript_change_detected_by_assembler': bool(changed_text_assembly)}
finally:
    case.doCleanups()

spec = importlib.util.spec_from_file_location('probe_tool', source / 'integrations/openwebui/ghostwriter_github.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
tool = module.Tools()
tool.valves.GITHUB_TOKEN = 'FICTITIOUS_TEST_TOKEN'
tool.valves.ALLOWED_REPOS = 'owner/test'
async def inline(operation):
    # Nur den ohnehin in _run aufgerufenen synchronen Operationsteil ausführen;
    # keine Threads, Netzwerkzugriffe oder echte Zugangsdaten.
    return json.dumps({'ok': True, 'result': operation([])})
sha = 'a' * 40
observations = []
for branch in ['ghostwriter/buch/kiesel', 'buch/kiesel']:
    replies = [{'object': {'sha': sha}}, {'tree': {'sha': 'old-tree'}},
               {'sha': 'blob'}, {'sha': 'new-tree'}, {'sha': 'new-commit'},
               {'object': {'sha': sha}}, {}]
    with patch.object(tool, '_run', side_effect=inline), patch.object(tool, '_http', side_effect=replies) as http:
        response = json.loads(asyncio.run(tool.commit_files('owner/test', branch,
            json.dumps([{'path': 'approvals.yml', 'content': yaml.safe_dump(ledger)}]),
            'Fiktiver B04-Prüfvorgang', sha)))
        observations.append({'branch_kind': 'work' if branch.startswith('ghostwriter/') else 'book',
                             'accepted': bool(response['ok']),
                             'authenticated_requester_supplied': False,
                             'simulated_write_calls': sum(c.args[1] in ('POST', 'PATCH', 'PUT', 'DELETE') for c in http.call_args_list)})
result['openwebui_write_observations'] = observations
result['commit_files_has_user_context_parameter'] = '__user__' in inspect.signature(tool.commit_files).parameters
result['has_user_specific_valves'] = hasattr(module.Tools, 'UserValves')
result['limitations'] = ['Lokale fiktive Daten und simulierter HTTP-Transport, keine echten GitHub-Aufrufe.',
                         'Keine tatsächlichen Konten, Rechte oder Branch-Regeln abgefragt.',
                         'Zeigt Grenzen der Programmprüfungen, keine Umgehung nachgewiesener GitHub-Rechte.',
                         'Kein erfolgreicher Rollenabnahmetest; beobachtete Lücke bleibt offen.']
Path(args.output).write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
print(json.dumps(result, ensure_ascii=False, indent=2))
