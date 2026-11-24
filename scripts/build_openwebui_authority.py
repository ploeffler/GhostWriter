#!/usr/bin/env python3
"""Gemeinsame Reviewprüfung in das einzeln installierbare GitHub-Werkzeug einbetten."""
import argparse
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
BEGIN = '# BEGIN GENERATED REVIEW AUTHORITY'
END = '# END GENERATED REVIEW AUTHORITY'


def build(check=False):
    source = (ROOT / 'scripts/approval_authority.py').read_text()
    shared = source.split('# BEGIN SHARED REVIEW AUTHORITY\n', 1)[1].split('# END SHARED REVIEW AUTHORITY', 1)[0]
    path = ROOT / 'integrations/openwebui/ghostwriter_github.py'
    original = path.read_text()
    before, rest = original.split(BEGIN, 1)
    _, after = rest.split(END, 1)
    expected = before + BEGIN + '\n# Erzeugt aus scripts/approval_authority.py; nicht von Hand ändern.\n' + shared + END + after
    if check:
        return expected == original
    path.write_text(expected)
    return True


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    if not build(parser.parse_args().check):
        parser.exit(1, 'Reviewprüfung veraltet: python3 scripts/build_openwebui_authority.py ausführen.\n')
