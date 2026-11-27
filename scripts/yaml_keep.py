#!/usr/bin/env python3
"""YAML schreiben und dabei Unverändertes wörtlich erhalten (#717).

`yaml.safe_dump` verliert Kommentare und bricht jeden Eintrag neu um. `dump_keep(old_text, data)`
setzt die neue Datei aus dem alten Text zusammen:

- Kopfkommentare und Leerzeilen vor dem ersten Schlüssel bleiben stehen.
- Ein Schlüssel der obersten Ebene, dessen Wert gleich geblieben ist, behält seinen alten Text
  samt Kommentaren davor.
- In einer Liste von Einträgen behält jeder unveränderte Eintrag seinen alten Text; nur geänderte
  und neue Einträge werden neu geschrieben.

Kann der alte Text nicht sicher zerlegt werden, oder ergibt das Ergebnis beim Einlesen nicht genau
`data`, schreibt die Funktion neu wie `safe_dump`, stellt aber die Kopfkommentare voran.
"""
from __future__ import annotations

import re
from pathlib import Path

import yaml

DUMP = dict(allow_unicode=True, sort_keys=False, width=100)
_TOP = re.compile(r'^([A-Za-z0-9_][^:#\s]*|"[^"]*"|\'[^\']*\'):(\s|$)')


def _dump(obj) -> str:
    return yaml.safe_dump(obj, **DUMP)


def _header(lines: list[str]) -> list[str]:
    head = []
    for line in lines:
        if line.strip() == '' or line.lstrip().startswith('#'):
            head.append(line)
        else:
            break
    # nur Kommentare zählen zum Kopf; reine Leerzeilen am Ende gehören zum ersten Block
    while head and head[-1].strip() == '':
        head.pop()
    return head if any(h.lstrip().startswith('#') for h in head) else []


def _top_blocks(lines: list[str], start: int):
    """Zerlegt ab `start` in Blöcke je Schlüssel der obersten Ebene: [(key, [zeilen])].
    Kommentare und Leerzeilen direkt vor einem Schlüssel gehören zu dessen Block."""
    blocks, pending, cur = [], [], None
    for line in lines[start:]:
        m = _TOP.match(line)
        if m:
            key = yaml.safe_load(m.group(1) + ': 0')
            key = next(iter(key)) if isinstance(key, dict) else m.group(1)
            cur = (key, pending + [line])
            blocks.append(cur)
            pending = []
        elif cur is None or line.strip() == '' or (line.startswith('#')):
            pending.append(line)
        else:
            cur[1].extend(pending + [line])
            pending = []
    if pending:
        if blocks:
            blocks[-1][1].extend(pending)
        else:
            return None
    return blocks


def _list_items(block: list[str]):
    """Zerlegt den Block eines Listenschlüssels in (Kopfzeilen, Einzug, [Eintragszeilen …])."""
    keyline = next(i for i, l in enumerate(block) if _TOP.match(l))
    if block[keyline].split(':', 1)[1].strip() not in ('',):
        return None
    head, items, indent = block[:keyline + 1], [], None
    pending = []
    for line in block[keyline + 1:]:
        stripped = line.lstrip(' ')
        ind = len(line) - len(stripped)
        if indent is None and stripped.startswith('- '):
            indent = ind
        if indent is not None and ind == indent and (stripped.startswith('- ') or stripped == '-'):
            items.append(pending + [line])
            pending = []
        elif not items:
            if line.strip() == '' or stripped.startswith('#'):
                head.append(line)
            else:
                return None
        elif line.strip() == '' or (stripped.startswith('#') and ind <= indent):
            pending.append(line)
        else:
            items[-1].extend(pending + [line])
            pending = []
    if items and pending:
        items[-1].extend(pending)
    return head, indent or 0, items


def _parse(lines: list[str]):
    try:
        return yaml.safe_load(''.join(lines))
    except yaml.YAMLError:
        return object()


def _item_value(item_lines: list[str], indent: int):
    text = ''.join(l[indent:] if l[:indent].strip() == '' else l for l in item_lines)
    v = _parse([text])
    return v[0] if isinstance(v, list) and len(v) == 1 else object()


def _fresh_item(item, indent: int) -> list[str]:
    text = _dump([item])
    return [(' ' * indent + l) if l.strip() else l for l in text.splitlines(keepends=True)]


def _merge_list(block: list[str], key, new_list):
    parts = _list_items(block)
    if not parts:
        return None
    head, indent, items = parts
    old_vals = [_item_value(it, indent) for it in items]
    used, out = set(), list(head)
    for k, item in enumerate(new_list):
        hit = None
        if k < len(old_vals) and k not in used and old_vals[k] == item:
            hit = k
        else:
            hit = next((j for j, v in enumerate(old_vals) if j not in used and v == item), None)
        if hit is not None:
            used.add(hit)
            out.extend(items[hit])
        else:
            out.extend(_fresh_item(item, indent))
    return out


def dump_keep(old_text: str | None, data) -> str:
    fresh = _dump(data)
    if not old_text or not isinstance(data, dict):
        return fresh
    lines = old_text.splitlines(keepends=True)
    if lines and not lines[-1].endswith('\n'):
        lines[-1] += '\n'
    head = _header(lines)
    try:
        old = yaml.safe_load(old_text)
    except yaml.YAMLError:
        old = None
    blocks = _top_blocks(lines, len(head)) if isinstance(old, dict) else None
    result = None
    if blocks is not None and [b[0] for b in blocks] == list(old.keys()):
        by_key = dict(blocks)
        out = list(head)
        for key, value in data.items():
            block = by_key.get(key)
            if block is not None and old.get(key) == value:
                out.extend(block)
                continue
            if block is not None and isinstance(value, list) and isinstance(old.get(key), list):
                merged = _merge_list(block, key, value)
                if merged is not None:
                    out.extend(merged)
                    continue
            if block is not None:   # Kommentare vor dem Schlüssel bleiben, auch wenn sich der Wert ändert
                out.extend(block[:next(i for i, l in enumerate(block) if _TOP.match(l))])
            out.append(_dump({key: value}))
        result = ''.join(out)
    if result is not None and _parse([result]) == data:
        return result
    return ''.join(head) + fresh


def write_keep(path, data) -> None:
    p = Path(path)
    old = p.read_text(encoding='utf-8') if p.exists() else None
    p.write_text(dump_keep(old, data), encoding='utf-8')
