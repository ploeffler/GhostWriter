"""#445: Fehler vor „| tee“ dürfen nicht verloren gehen – Schritte mit tee-Pipe laufen mit pipefail."""
import pathlib
import re
import unittest

import yaml

ROOT = pathlib.Path(__file__).resolve().parent.parent
WORKFLOWS = sorted((ROOT / '.github' / 'workflows').glob('*.yml'))
TEE_PIPE = re.compile(r'[^|]\|\s*tee\b')


def shell_of(data, job, step):
    """Wirksame Shell eines Schritts: Schritt, Job-Vorgabe, Workflow-Vorgabe."""
    for src in (step, (job.get('defaults') or {}).get('run') or {}, (data.get('defaults') or {}).get('run') or {}):
        if src.get('shell'):
            return src['shell']
    return None


def pipefail(shell, script):
    # shell: bash ⇒ GitHub startet „bash --noprofile --norc -eo pipefail {0}“; sonst muss das Skript es selbst setzen.
    return shell == 'bash' or 'pipefail' in (shell or '') or 'set -o pipefail' in script


class WorkflowPipefailTest(unittest.TestCase):
    def test_tee_pipes_keep_exit_code(self):
        self.assertTrue(WORKFLOWS)
        for path in WORKFLOWS:
            data = yaml.safe_load(path.read_text(encoding='utf-8'))
            for jname, job in (data.get('jobs') or {}).items():
                for step in job.get('steps') or []:
                    script = step.get('run') or ''
                    if TEE_PIPE.search(script):
                        self.assertTrue(pipefail(shell_of(data, job, step), script),
                                        f'{path.name}/{jname}/{step.get("name")}: „| tee“ ohne pipefail')

    def test_outline_checks_key_first(self):
        text = (ROOT / '.github' / 'workflows' / 'import.yml').read_text(encoding='utf-8')
        outline = text[text.index('outline) '):text.index('apply) ')]
        self.assertLess(outline.index('Kein KI-Schlüssel'), outline.index('outline --plan'))


if __name__ == '__main__':
    unittest.main()
