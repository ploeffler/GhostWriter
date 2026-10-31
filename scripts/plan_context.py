#!/usr/bin/env python3
"""Read-only startup context plan; never emits manuscript text.

Usage: python3 scripts/plan_context.py PROJECT [--limited-context]
"""
import argparse
import hashlib
import json
import re
from pathlib import Path

import yaml

WORD_LIMIT = 15000  # User configuration deferred until v1.1.


def manuscript(text):
    """Only the Manuskript part counts, never frontmatter or section notes."""
    body = re.sub(r'\A---\r?\n.*?\r?\n---\r?\n', '', text, count=1, flags=re.S)
    match = re.search(r'^## Manuskript\s*\n(.*?)(?=^## |\Z)', body, re.M | re.S)
    result = match.group(1).strip() if match else ''
    return '' if result == 'Noch nicht begonnen.' else result


def word_count(text):
    # Unicode words; hyphenated words count as one. Markdown punctuation does not.
    return len(re.findall(r"[^\W_]+(?:[-’'][^\W_]+)*", text, re.UNICODE))


def fingerprint(sources):
    return hashlib.sha256(json.dumps(sources, ensure_ascii=False).encode()).hexdigest()


def summary_state(base, path, digest):
    file = base / path
    if not file.is_file():
        return 'missing'
    text = file.read_text(encoding='utf-8')
    match = re.match(r'\A---\n(.*?)\n---\n', text, re.S)
    try:
        head = yaml.safe_load(match.group(1)) if match else None
    except yaml.YAMLError:
        return 'stale'
    if not isinstance(head, dict):
        return 'stale'
    if not re.fullmatch(r'[0-9a-f]{40}', str(head.get('source_commit', ''))):
        return 'stale'
    if head.get('source_digest') != digest or not text[match.end():].strip():
        return 'stale'
    return 'current'


def plan(base, limited_context=False):
    base = Path(base).resolve()
    config = yaml.safe_load((base / 'ghostwriter.yml').read_text(encoding='utf-8'))
    sources, chapters, words = [], [], 0
    for chapter in config['structure']['chapters']:
        chapter_sources = []
        for section in chapter['sections']:
            path = section['path']
            resolved = (base / path).resolve()
            if not resolved.is_relative_to(base):
                raise ValueError('Section path outside project')
            content = manuscript(resolved.read_text(encoding='utf-8'))
            words += word_count(content)
            chapter_sources.append([section['id'], path, content])
        sources.append([chapter['id'], chapter['title'], chapter_sources])
        chapters.append({'chapter_id': chapter['id'], 'path': f"context/{chapter['id']}.md",
                         'source_digest': fingerprint([chapter['id'], chapter['title'], chapter_sources]),
                         'section_paths': [s['path'] for s in chapter['sections']]})
    book = {'path': 'context/book.md', 'source_digest': fingerprint(sources)}
    for item in [book, *chapters]:
        item['state'] = summary_state(base, item['path'], item['source_digest'])
    mode = 'full' if words <= WORD_LIMIT and not limited_context else 'summaries'
    return {'word_count': words, 'word_limit': WORD_LIMIT, 'mode': mode,
            'reason': 'limited_context' if limited_context else 'word_count',
            'book_summary': book, 'chapter_summaries': chapters,
            'manuscript_paths': [s['path'] for c in config['structure']['chapters'] for s in c['sections']] if mode == 'full' else [],
            'reload_required': [c['chapter_id'] for c in chapters if c['state'] != 'current']}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('project')
    parser.add_argument('--limited-context', action='store_true')
    args = parser.parse_args()
    print(json.dumps(plan(args.project, args.limited_context), ensure_ascii=False, indent=2))
