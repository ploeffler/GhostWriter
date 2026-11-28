"""Anschlüsse der Claude-Web-App (#662): GitHub nur über GW_PORTS, kein Konnektor-Aufruf in Ansichten und Abläufen."""
import re
import unittest
from pathlib import Path

HTML = (Path(__file__).resolve().parent.parent / 'apps' / 'claude' / 'index.html').read_text(encoding='utf-8')
GIT_METHODS = ['getFile', 'getBlob', 'listDir', 'listPRs', 'prCommits', 'createBranch', 'createPR', 'mergePR',
               'updatePRBranch', 'pushFiles', 'me', 'repoInfo', 'listBranches']


class AppPorts(unittest.TestCase):
    def test_konnektor_nur_im_anschluss(self):
        start = HTML.index('const GW_PORTS = {')
        end = HTML.index('async function getFile(path, ref, fresh, allowStale)')
        outside = HTML[:start] + HTML[end:]
        stray = re.findall(r'[^\w.]call\("[a-z_]+"', outside)
        self.assertEqual(stray, [], 'Konnektor-Aufruf außerhalb von GW_PORTS: über GW_PORTS.git.<Methode> gehen')

    def test_alle_methoden_vorhanden_und_benutzt(self):
        block = HTML[HTML.index('const GW_PORTS = {'):HTML.index('async function getFile(path, ref, fresh, allowStale)')]
        for name in GIT_METHODS:
            self.assertRegex(block, r'async %s\(' % name, name)
            self.assertIn('GW_PORTS.git.%s(' % name, HTML[HTML.index('async function getFile(path, ref, fresh, allowStale)'):], name + ' wird nicht benutzt')


if __name__ == '__main__':
    unittest.main()
