#!/usr/bin/env python3
"""Bettet den zentralen Profiler in die einzeln installierbare Direkt-Pipe ein."""
import argparse
import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NAMES = {'canonical', 'component', 'request_plan', 'report', 'count', 'provider_usage',
         'Capture', '_OUTPUT_LOCK', 'emit', 'aggregate', 'openwebui_report'}
BEGIN = '# BEGIN GENERATED PROMPT PROFILER'
END = '# END GENERATED PROMPT PROFILER'


def bundled_source():
    source = (ROOT / 'scripts/prompt_profiler.py').read_text(encoding='utf-8')
    lines = source.splitlines()
    chunks = []
    found = set()
    for node in ast.parse(source).body:
        name = getattr(node, 'name', None)
        if isinstance(node, ast.Assign) and isinstance(node.targets[0], ast.Name):
            name = node.targets[0].id
        if name in NAMES:
            found.add(name)
            chunks.append('\n'.join(lines[node.lineno - 1:node.end_lineno]))
    if found != NAMES:
        raise ValueError('Profiler-Bausteine fehlen')
    return '# Automatisch aus scripts/prompt_profiler.py; nicht von Hand ändern.\n' + '\n\n\n'.join(chunks)


def build(check=False):
    path = ROOT / 'integrations/openwebui/ghostwriter_direct.py'
    original = path.read_text(encoding='utf-8')
    before, rest = original.split(BEGIN, 1)
    _, after = rest.split(END, 1)
    expected = before + BEGIN + '\n' + bundled_source() + '\n' + END + after
    if check:
        return original == expected
    path.write_text(expected, encoding='utf-8')
    return True


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    if not build(args.check):
        parser.exit(1, 'Profiler-Bündel veraltet: python3 scripts/build_openwebui_profiler.py ausführen.\n')
