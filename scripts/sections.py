#!/usr/bin/env python3
"""Abschnitte zusammenlegen, entfernen oder in ein anderes Kapitel verschieben (#293).

Aufruf:
  python scripts/sections.py <projektordner> merge <quelle>[,<quelle>…] <ziel> [--manuscript append|archive]
  python scripts/sections.py <projektordner> remove <abschnitt> [--into <ziel>] [--confirm]
  python scripts/sections.py <projektordner> move <abschnitt> <kapitel> [--position N]
  python scripts/sections.py <projektordner> add <kapitel> <titel> [--position N]
  python scripts/sections.py <projektordner> rename <abschnitt> <titel>
  python scripts/sections.py <projektordner> reorder <abschnitt> [--after <abschnitt>]

Abschnitte werden mit ID (`sec-…`) oder Nummer (`7.2`) angegeben, Kapitel mit
ID (`ch-…`) oder Nummer (`7`); `--position` zählt ab 1 (Standard: am Ende).

merge   übernimmt Ziel, Kurzbeschreibung und Recherche-/Brainstorming-Text der
        Quelle unter „## Übernommenes Material aus dem früheren Abschnitt N.M“
        in den Zielabschnitt, verschiebt Laufdateien (research/, brainstorming/,
        images/) und Kosten zum Ziel. Hat die Quelle ein Manuskript, ist
        --manuscript Pflicht: `append` hängt es an das Manuskript des Ziels an,
        `archive` legt die Quelldatei unter archiv/ ab.
remove  entfernt einen Abschnitt. Mit --into wie merge; sonst wandert die Datei
        samt Laufdateien nach archiv/<kapitel>/. Ein Manuskript nur mit --confirm.
move    verschiebt Abschnitt, Laufdateien und Kosten in ein anderes Kapitel. Die
        ID bleibt stabil (auch mit altem Kapitelpräfix), der Dateiname bekommt
        die neue Nummer.

add     legt einen neuen Abschnitt an (aus templates/section.md, Status planned); rename benennt um (ID und Pfad bleiben);
        reorder stellt einen Abschnitt innerhalb seines Kapitels um (#209). Beide ändern keinen Text; rename und reorder
        gehen deshalb auch bei einem abgeschlossenen Abschnitt, nicht bei einem ausgecheckten.

Gemeinsam: abgeschlossene Abschnitte (Status approved bzw. approvals.section)
werden nicht angefasst – erst die Freigabe zurücknehmen. Nummern und
Überschriften der betroffenen Kapitel, ghostwriter.yml (Rest Zeichen für
Zeichen erhalten), die Abschnittslisten der Kapitel-READMEs und Markdown-Verweise
im Buch (alter Pfad, ID) werden nachgezogen; import-data/ und archiv/ bleiben
unverändert. Entfernte IDs landen in structure.retired, damit Einträge in
approvals.yml und editorial/checks.yml gültig bleiben (das Protokoll bleibt
unverändert). Übrig gebliebene Verweise (etwa „Abschnitt 7.3“ im Fließtext)
meldet das Skript. Den Commit schreibt der Assistent (START.md, Aktionen
`section.merge`, `section.remove`, `section.move`).
"""
import argparse
import datetime
import re
import shutil
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
FRONT = re.compile(r'\A---\n(.*?)\n---\n', re.S)
RUN_FOLDERS = ('research', 'brainstorming', 'images')
SKIP = ('import-data', 'archiv', '.git')
EMPTY_MS = ('', 'Noch nicht begonnen.')


# ---------- Lesen ----------

def load(base):
    text = (base / 'ghostwriter.yml').read_text(encoding='utf-8')
    return text, yaml.safe_load(text)


def chapter_of(config, ref):
    chapters = config['structure']['chapters']
    if re.fullmatch(r'\d+', str(ref)):
        i = int(ref)
        if 1 <= i <= len(chapters):
            return chapters[i - 1]
    for ch in chapters:
        if ch['id'] == ref:
            return ch
    raise SystemExit(f'Kapitel „{ref}“ nicht gefunden')


def section_of(config, ref):
    """(kapitel, abschnitt) zu ID oder Nummer N.M."""
    chapters = config['structure']['chapters']
    m = re.fullmatch(r'(\d+)\.(\d+)', str(ref))
    if m:
        c, s = int(m.group(1)), int(m.group(2))
        if 1 <= c <= len(chapters) and 1 <= s <= len(chapters[c - 1]['sections']):
            return chapters[c - 1], chapters[c - 1]['sections'][s - 1]
    for ch in chapters:
        for s in ch['sections']:
            if s['id'] == ref:
                return ch, s
    raise SystemExit(f'Abschnitt „{ref}“ nicht gefunden')


def number(config, sid):
    for ci, ch in enumerate(config['structure']['chapters'], start=1):
        for si, s in enumerate(ch['sections'], start=1):
            if s['id'] == sid:
                return f'{ci}.{si}'
    return '?'


def read_section(base, sec):
    text = (base / sec['path']).read_text(encoding='utf-8')
    m = FRONT.match(text)
    return yaml.safe_load(m.group(1)) or {}, text


def part(text, name):
    m = re.search(rf'(?m)^## {re.escape(name)}\n\n(.*?)(?=^## |\Z)', text, re.S)
    return m.group(1).strip() if m else ''


def manuscript(text):
    return text.split('\n## Manuskript\n', 1)[1].strip() if '\n## Manuskript\n' in text else ''


def has_manuscript(text):
    return manuscript(text) not in EMPTY_MS


def locked(head):
    return head.get('status') == 'approved' or bool((head.get('approvals') or {}).get('section'))


def check_unlocked(base, *secs):
    for sec in secs:
        head, _ = read_section(base, sec)
        if locked(head):
            raise SystemExit(f'Abschnitt „{sec["title"]}“ ist abgeschlossen; zuerst die Freigabe zurücknehmen '
                             '(START.md, „Freigaben“).')
        import checkout   # Bereich zum Gegenlesen ausgecheckt (#572)
        from render_view import load
        entry = checkout.locked_by_checkout(base, load(base)[1], sec['id'])
        if entry:
            raise SystemExit(f'Abschnitt {checkout.lock_message(entry, section=sec["title"])}')


# ---------- ghostwriter.yml textgenau ändern ----------

def entry_span(text, sid):
    """Start und Ende des Listeneintrags `- id: <sid>` unter sections."""
    m = re.search(rf'(?m)^( *)- id: {re.escape(sid)}[ \t]*\n', text)
    if not m:
        raise SystemExit(f'ghostwriter.yml: Eintrag {sid} nicht gefunden')
    indent = len(m.group(1))
    end = m.end()
    for line in re.finditer(r'(?m)^.*\n?', text[end:]):
        s = line.group(0)
        if not s:
            break
        stripped = s.lstrip(' ')
        if s.strip() and len(s) - len(stripped) <= indent:
            break
        end += len(s)
    return m.start(), end, indent


def remove_entry(text, sid):
    start, end, _ = entry_span(text, sid)
    return text[:start] + text[end:], text[start:end]


def insert_entry(text, chapter, position, block):
    """Eintrag in die sections-Liste des Kapitels an Position (0-basiert) einfügen."""
    secs = chapter['sections']
    if position < len(secs):
        start, _, indent = entry_span(text, secs[position]['id'])
        return text[:start] + reindent(block, indent) + text[start:]
    if secs:
        _, end, indent = entry_span(text, secs[-1]['id'])
        return text[:end] + reindent(block, indent) + text[end:]
    start, end, indent = entry_span(text, chapter['id'])
    body = text[start:end]
    sm = re.search(r'(?m)^( *)sections:[ \t]*(\[\])?[ \t]*\n', body)
    if not sm:
        raise SystemExit(f'ghostwriter.yml: sections von {chapter["id"]} nicht gefunden')
    new = f'{sm.group(1)}sections:\n' + reindent(block, len(sm.group(1)))
    return text[:start] + body[:sm.start()] + new + body[sm.end():] + text[end:]


def reindent(block, indent):
    lines = block.splitlines(keepends=True)
    cur = len(lines[0]) - len(lines[0].lstrip(' '))
    return ''.join((' ' * indent + l[cur:]) if l.strip() else l for l in lines)


def set_path(block, new_path):
    return re.sub(r'(?m)^(\s*path:\s*).*$', lambda m: m.group(1) + new_path, block, count=1)


def add_retired(text, items):
    """structure.retired ergänzen (vor `  chapters:`)."""
    lines = []
    for r in items:
        lines.append(f'  - id: {r["id"]}')
        lines.append('    title: ' + yaml.safe_dump(r['title'], allow_unicode=True, width=10**6).splitlines()[0])
        for key in ('action', 'merged_into', 'archive'):
            if r.get(key):
                lines.append(f'    {key}: {r[key]}')
        lines.append(f"    at: '{r['at']}'")
    block = '\n'.join(lines) + '\n'
    m = re.search(r'(?m)^  retired:[ \t]*\n((?:    .*\n|  - .*\n)*)', text)
    if m:
        return text[:m.end()] + block + text[m.end():]
    m = re.search(r'(?m)^  chapters:', text)
    return text[:m.start()] + '  retired:\n' + block + text[m.start():]


def set_current(text, old, new):
    return re.sub(rf'(?m)^(\s*current_section_id:\s*){re.escape(old)}\s*$', lambda m: m.group(1) + (new or "''"), text)


# ---------- Dateien ----------

def renumber(base, config):
    """Nummern und Überschriften aller Abschnitte, Abschnittslisten der Kapitel-READMEs."""
    for ci, ch in enumerate(config['structure']['chapters'], start=1):
        rows = []
        for si, sec in enumerate(ch['sections'], start=1):
            path = base / sec['path']
            head, text = read_section(base, sec)
            num = f'{ci}.{si}'
            if str(head.get('number')) != num:
                text = re.sub(r'(?m)^number: .*$', f'number: "{num}"', text, count=1)
                text = re.sub(rf'(?m)^# {re.escape(str(head.get("number")))} ', f'# {num} ', text, count=1)
                path.write_text(text, encoding='utf-8')
            rows.append(f'| {num} | {sec["title"]} | `{head.get("status", "planned")}` |')
        readme = base / ch['path'] / 'README.md'
        if readme.is_file():
            r = readme.read_text(encoding='utf-8')
            r = re.sub(r'(?m)^# Kapitel \d+ ', f'# Kapitel {ci} ', r, count=1)
            table = '| Nummer | Abschnitt | Status |\n|---|---|---|\n' + ''.join(x + '\n' for x in rows)
            r2 = re.sub(r'(?ms)^\| Nummer \| Abschnitt \| Status \|\n\|---\|---\|---\|\n(?:\|.*\n)*', table, r, count=1)
            readme.write_text(r2, encoding='utf-8')


def move_tree(src, dst):
    """Inhalt von src nach dst verschieben; bei gleichen Namen ein Präfix."""
    if not src.exists():
        return []
    dst.mkdir(parents=True, exist_ok=True)
    moved = []
    for f in sorted(src.iterdir()):
        target = dst / f.name
        if target.exists():
            target = dst / f'{src.name}-{f.name}'
        shutil.move(str(f), str(target))
        moved.append((f, target))
    src.rmdir()
    return moved


def move_runs(base, ch_from, sid_from, ch_to, sid_to):
    moved = []
    for folder in RUN_FOLDERS:
        moved += move_tree(base / ch_from['path'] / folder / sid_from, base / ch_to['path'] / folder / sid_to)
    return moved


def retarget_images(base, ch_to, sid_from, sid_to):
    """Bildbeschreibungen nach dem Zusammenlegen dem Zielabschnitt zuordnen (#684)."""
    folder = base / ch_to['path'] / 'images' / sid_to
    if not folder.is_dir():
        return
    for path in sorted(folder.glob('img-*.yml')):
        data = yaml.safe_load(path.read_text(encoding='utf-8')) or {}
        if isinstance(data, dict) and data.get('section_id') == sid_from:
            data['section_id'] = sid_to
            path.write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False, width=10**6), encoding='utf-8')


def move_costs(base, ch_from, sid_from, ch_to, sid_to):
    src = base / ch_from['path'] / 'costs' / f'{sid_from}.yml'
    if not src.is_file():
        return
    data = yaml.safe_load(src.read_text(encoding='utf-8')) or {}
    dst = base / ch_to['path'] / 'costs' / f'{sid_to}.yml'
    out = yaml.safe_load(dst.read_text(encoding='utf-8')) if dst.is_file() else None
    out = out or {k: v for k, v in data.items() if k != 'entries'}
    if 'section_id' in out:
        out['section_id'] = sid_to
    for e in data.get('entries') or []:
        if e.get('section_id') == sid_from:
            e['section_id'] = sid_to
        out.setdefault('entries', []).append(e)
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text(yaml.safe_dump(out, allow_unicode=True, sort_keys=False), encoding='utf-8')
    src.unlink()


def book_files(base):
    for f in base.rglob('*.md'):
        rel = f.relative_to(base)
        if rel.parts and rel.parts[0] in SKIP:
            continue
        yield f


def update_links(base, replacements):
    """Pfade (auch Ordner der Laufdateien) und IDs in Markdown-Dateien ersetzen."""
    changed = set()
    pairs = sorted(replacements.items(), key=lambda kv: -len(kv[0]))
    for f in book_files(base):
        text = f.read_text(encoding='utf-8')
        new = text
        for old, rep in pairs:   # nur ganze Pfade bzw. IDs, nicht sec-01-02 in sec-01-02-x
            new = re.sub(rf'(?<![\w-]){re.escape(old)}(?![\w-])', lambda _m, r=rep: r, new)
        if new != text:
            f.write_text(new, encoding='utf-8')
            changed.add(str(f.relative_to(base)))
    return sorted(changed)


def leftovers(base, ids, numbers):
    """Verweise, die das Skript nicht sicher ersetzen kann: alte IDs, „Abschnitt N.M“."""
    out = []
    pats = [re.escape(i) for i in ids] + [rf'Abschnitt(?:s)? {re.escape(n)}\b' for n in numbers]
    rx = re.compile('|'.join(pats)) if pats else None
    for f in book_files(base) if rx else []:
        for i, line in enumerate(f.read_text(encoding='utf-8').splitlines(), start=1):
            if rx.search(line):
                out.append(f'{f.relative_to(base)}:{i}')
    return out


def material_block(num, text):
    parts = []
    for name in ('Ziel des Abschnitts', 'Kurzbeschreibung', 'Recherche- und Brainstorming-Ergebnisse'):
        v = part(text, name)
        if v and v not in ('Offen.', 'Werden in separaten Laufdateien dokumentiert.'):
            parts.append(f'### {name}\n\n{v}\n')
    if not parts:
        return ''
    return f'## Übernommenes Material aus dem früheren Abschnitt {num}\n\n' + '\n'.join(parts) + '\n'


def add_to_target(base, target, block, ms=''):
    path = base / target['path']
    text = path.read_text(encoding='utf-8')
    if block:
        if '\n## Manuskript\n' in text:
            text = text.replace('\n## Manuskript\n', '\n' + block + '## Manuskript\n', 1)
        else:
            text = text.rstrip('\n') + '\n\n' + block
    if ms:
        own = manuscript(text)
        if own in EMPTY_MS:
            text = text[:text.index('\n## Manuskript\n')] + '\n## Manuskript\n\n' + ms + '\n'
        else:
            text = text.rstrip('\n') + '\n\n' + ms + '\n'
    path.write_text(text, encoding='utf-8')


def archive_file(base, ch, sec):
    dst = base / 'archiv' / Path(ch['path']).name / Path(sec['path']).name
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(base / sec['path']), str(dst))
    for folder in RUN_FOLDERS:
        move_tree(base / ch['path'] / folder / sec['id'], dst.parent / folder / sec['id'])
    return str(dst.relative_to(base))


# ---------- Aktionen ----------

def today():
    return datetime.date.today().isoformat()


def retire(base, config, text, ch, sec, action, into=None, manuscript_mode=None, confirm=False):
    """Gemeinsamer Teil von merge und remove für einen Abschnitt."""
    head, stext = read_section(base, sec)
    num = number(config, sec['id'])
    ms = manuscript(stext) if has_manuscript(stext) else ''
    record = {'id': sec['id'], 'title': sec['title'], 'action': action, 'at': today()}
    repl = {}
    if into:
        tch, target = into
        mode = manuscript_mode
        if ms and mode not in ('append', 'archive'):
            raise SystemExit(f'Abschnitt {num} hat ein Manuskript: --manuscript append (an {number(config, target["id"])} '
                             'anhängen) oder archive (unter archiv/ aufbewahren) wählen.')
        add_to_target(base, target, material_block(num, stext), ms if mode == 'append' else '')
        for f, t in move_runs(base, ch, sec['id'], tch, target['id']):
            repl[str(f.relative_to(base))] = str(t.relative_to(base))
        retarget_images(base, tch, sec['id'], target['id'])
        move_costs(base, ch, sec['id'], tch, target['id'])
        record['merged_into'] = target['id']
        if mode == 'archive':
            record['archive'] = archive_file(base, ch, sec)
        else:
            (base / sec['path']).unlink()
        repl[sec['path']] = target['path']
        for folder in RUN_FOLDERS:
            repl[f'{ch["path"]}/{folder}/{sec["id"]}'] = f'{tch["path"]}/{folder}/{target["id"]}'
        repl[sec['id']] = target['id']
        new_current = target['id']
    else:
        if ms and not confirm:
            raise SystemExit(f'Abschnitt {num} hat ein Manuskript; entfernen nur mit --confirm '
                             '(die Datei wandert nach archiv/) oder mit --into in einen anderen Abschnitt übernehmen.')
        record['archive'] = archive_file(base, ch, sec)
        repl[sec['path']] = record['archive']
        new_current = None
    text, _ = remove_entry(text, sec['id'])
    text = set_current(text, sec['id'], new_current)
    ch['sections'] = [s for s in ch['sections'] if s['id'] != sec['id']]
    return text, record, repl, num


def finish(base, config, text, records, repl, ids, numbers):
    if records:
        text = add_retired(text, records)
    (base / 'ghostwriter.yml').write_text(text, encoding='utf-8')
    renumber(base, config)
    changed = update_links(base, repl)
    left = leftovers(base, [i for i in ids if i not in repl or repl[i] == i], numbers)
    return changed, left


def cmd_merge(base, sources, target_ref, manuscript_mode=None):
    text, config = load(base)
    tch, target = section_of(config, target_ref)
    srcs = [section_of(config, s) for s in sources.split(',')]
    if any(s['id'] == target['id'] for _, s in srcs):
        raise SystemExit('Quelle und Ziel sind derselbe Abschnitt')
    check_unlocked(base, target, *[s for _, s in srcs])
    records, repl, numbers = [], {}, []
    for ch, sec in srcs:
        text, rec, r, num = retire(base, config, text, ch, sec, 'merged', (tch, target), manuscript_mode)
        records.append(rec); repl.update(r); numbers.append(num)
    changed, left = finish(base, config, text, records, repl, [], numbers)
    return report(config, 'zusammengelegt', records, changed, left, target)


def cmd_remove(base, ref, into=None, confirm=False, manuscript_mode=None):
    if into:
        return cmd_merge(base, ref, into, manuscript_mode or ('append' if confirm else None))
    text, config = load(base)
    ch, sec = section_of(config, ref)
    check_unlocked(base, sec)
    if len(ch['sections']) == 1:
        raise SystemExit('Jedes Kapitel braucht mindestens einen Abschnitt')
    text, rec, repl, num = retire(base, config, text, ch, sec, 'removed', confirm=confirm)
    changed, left = finish(base, config, text, [rec], repl, [sec['id']], [num])
    return report(config, 'entfernt', [rec], changed, left)


def cmd_move(base, ref, chapter_ref, position=None):
    text, config = load(base)
    ch, sec = section_of(config, ref)
    tch = chapter_of(config, chapter_ref)
    if tch['id'] == ch['id']:
        raise SystemExit('Abschnitt liegt schon in diesem Kapitel; für die Reihenfolge section.reorder verwenden')
    if len(ch['sections']) == 1:
        raise SystemExit('Jedes Kapitel braucht mindestens einen Abschnitt')
    check_unlocked(base, sec)
    old_num = number(config, sec['id'])
    pos = len(tch['sections']) if position is None else max(0, min(int(position) - 1, len(tch['sections'])))
    name = re.sub(r'^\d+-', '', Path(sec['path']).name)
    new_path = f'{tch["path"]}/sections/{pos + 1:02d}-{name}'
    while (base / new_path).exists():
        name = 'v-' + name
        new_path = f'{tch["path"]}/sections/{pos + 1:02d}-{name}'
    text, block = remove_entry(text, sec['id'])
    ch['sections'] = [s for s in ch['sections'] if s['id'] != sec['id']]
    text = insert_entry(text, tch, pos, set_path(block, new_path))
    (base / new_path).parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(base / sec['path']), str(base / new_path))
    repl = {sec['path']: new_path}
    for folder in RUN_FOLDERS:
        src = base / ch['path'] / folder / sec['id']
        if src.exists():
            move_tree(src, base / tch['path'] / folder / sec['id'])
            repl[f'{ch["path"]}/{folder}/{sec["id"]}'] = f'{tch["path"]}/{folder}/{sec["id"]}'
    move_costs(base, ch, sec['id'], tch, sec['id'])
    sec['path'] = new_path
    tch['sections'].insert(pos, sec)
    text = re.sub(rf'(?m)^(\s*current_chapter_id:\s*){re.escape(ch["id"])}\s*$', lambda m: m.group(1) + tch['id'], text) \
        if re.search(rf'(?m)^\s*current_section_id:\s*{re.escape(sec["id"])}\s*$', text) else text
    changed, left = finish(base, config, text, [], repl, [], [old_num])
    return report(config, 'verschoben', [{'id': sec['id'], 'title': sec['title'], 'from': old_num}], changed, left, sec)


def slug_of(title):
    t = re.sub(r'[^a-z0-9]+', '-', (title or '').lower().translate(str.maketrans({'ä': 'ae', 'ö': 'oe', 'ü': 'ue', 'ß': 'ss'}))).strip('-')
    return t[:40].strip('-') or 'abschnitt'


def cmd_add(base, chapter_ref, title, position=None, paragraphs=None):
    """Neuen Abschnitt anlegen (#209): aus `templates/section.md`, Status `planned`, am Ende oder an `position` (ab 1);
    `paragraphs` werden zum Manuskript (Fließtext, ohne Formatierung)."""
    text, config = load(base)
    ch = chapter_of(config, chapter_ref)
    ci = config['structure']['chapters'].index(ch) + 1
    title = ' '.join((title or '').split())
    if not title:
        raise SystemExit('Titel fehlt')
    pos = len(ch['sections']) if position is None else max(0, min(int(position) - 1, len(ch['sections'])))
    taken = {s['id'] for c in config['structure']['chapters'] for s in c['sections']} | \
        {r.get('id') for r in (config['structure'].get('retired') or [])}
    sid, n = f'sec-{ci:02d}-{pos + 1:02d}-{slug_of(title)}', 2
    while sid in taken:
        sid, n = f'sec-{ci:02d}-{pos + 1:02d}-{slug_of(title)}-{n}', n + 1
    name = f'{pos + 1:02d}-{slug_of(title)}.md'
    while (base / ch['path'] / 'sections' / name).exists():
        name = 'v-' + name
    rel = f'{ch["path"]}/sections/{name}'
    body = '\n\n'.join(p.strip() for p in paragraphs or [] if p.strip()) or 'Noch nicht begonnen.'
    tpl = (ROOT / 'templates' / 'section.md').read_text(encoding='utf-8')
    quoted = yaml.safe_dump(title, allow_unicode=True, width=10**6).splitlines()[0]
    file_text = (tpl.replace('<STABILE-ID>', sid).replace('<KAPITEL>.<ABSCHNITT>', f'{ci}.{pos + 1}')
                 .replace('title: "<TITEL>"', f'title: {quoted}').replace('<NUMMER> <TITEL>', f'{ci}.{pos + 1} {title}'))
    file_text = re.sub(r'(?s)(## Manuskript\n\n).*\Z', lambda m: m.group(1) + body + '\n', file_text)
    block = f'- id: {sid}\n  title: {quoted}\n  path: {rel}\n'
    text = insert_entry(text, ch, pos, block)
    (base / rel).parent.mkdir(parents=True, exist_ok=True)
    (base / rel).write_text(file_text, encoding='utf-8')
    ch['sections'].insert(pos, {'id': sid, 'title': title, 'path': rel})
    changed, left = finish(base, config, text, [], {}, [], [])
    return f'✓ Abschnitt {ci}.{pos + 1} „{title}“ angelegt ({sid})\n'


def cmd_rename(base, ref, title):
    """Abschnitt umbenennen (#209): Titel in ghostwriter.yml, Abschnittsdatei, Überschrift und Liste im Kapitel-README. ID,
    Pfad, Status und Freigabe bleiben (der Text ändert sich nicht)."""
    text, config = load(base)
    ch, sec = section_of(config, ref)
    title = ' '.join((title or '').split())
    if not title:
        raise SystemExit('Titel fehlt')
    start, end, _ = entry_span(text, sec['id'])
    quoted = yaml.safe_dump(title, allow_unicode=True, width=10**6).splitlines()[0]
    block = re.sub(r'(?m)^(\s*title:\s*).*$', lambda m: m.group(1) + quoted, text[start:end], count=1)
    text = text[:start] + block + text[end:]
    old = sec['title']
    path = base / sec['path']
    head, ftext = read_section(base, sec)
    ftext = re.sub(r'(?m)^title: .*$', f'title: {quoted}', ftext, count=1)
    ftext = re.sub(rf'(?m)^# ({re.escape(str(head.get("number")))}) .*$', lambda m: f'# {m.group(1)} {title}', ftext, count=1)
    path.write_text(ftext, encoding='utf-8')
    sec['title'] = title
    finish(base, config, text, [], {}, [], [])
    return f'✓ Abschnitt {number(config, sec["id"])} umbenannt: „{old}“ → „{title}“\n'


def cmd_reorder(base, ref, after=None):
    """Abschnitt innerhalb seines Kapitels umstellen (#209): hinter `after` (Abschnitt) bzw. an den Anfang. Der Text ändert sich
    nicht, ein abgeschlossener Abschnitt darf deshalb umgestellt werden; Nummern und Listen werden nachgezogen."""
    text, config = load(base)
    ch, sec = section_of(config, ref)
    if after:
        ach, asec = section_of(config, after)
        if ach['id'] != ch['id']:
            raise SystemExit('Umstellen geht nur innerhalb eines Kapitels (sonst move)')
        if asec['id'] == sec['id']:
            raise SystemExit('Abschnitt kann nicht hinter sich selbst stehen')
    import checkout
    from render_view import load as load_project
    entry = checkout.locked_by_checkout(base, load_project(base)[1], sec['id'])
    if entry:
        raise SystemExit(f'Abschnitt {checkout.lock_message(entry, section=sec["title"])}')
    old_num = number(config, sec['id'])
    text, block = remove_entry(text, sec['id'])
    ch['sections'] = [x for x in ch['sections'] if x['id'] != sec['id']]
    pos = (next(i for i, x in enumerate(ch['sections']) if x['id'] == asec['id']) + 1) if after else 0
    text = insert_entry(text, ch, pos, block)
    ch['sections'].insert(pos, sec)
    finish(base, config, text, [], {}, [], [])
    return f'✓ Abschnitt {old_num} „{sec["title"]}“ umgestellt, jetzt {number(config, sec["id"])}\n'


def report(config, verb, records, changed, left, target=None):
    lines = []
    for r in records:
        frm = r.get('from')
        if verb == 'verschoben':
            lines.append(f'✓ Abschnitt {frm} „{r["title"]}“ verschoben, jetzt {number(config, r["id"])}')
        elif r.get('merged_into'):
            lines.append(f'✓ „{r["title"]}“ in {number(config, r["merged_into"])} „{target["title"]}“ übernommen'
                         + (f' (Datei aufbewahrt: {r["archive"]})' if r.get('archive') else ''))
        else:
            lines.append(f'✓ „{r["title"]}“ entfernt, Datei aufbewahrt: {r["archive"]}')
    if changed:
        lines.append('Verweise angepasst: ' + ', '.join(changed))
    if left:
        lines.append('⚠️ Bitte prüfen (alte Nummer oder ID): ' + ', '.join(left))
    return '\n'.join(lines) + '\n'


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('project', type=Path)
    sub = ap.add_subparsers(dest='cmd', required=True)
    m = sub.add_parser('merge')
    m.add_argument('sources')
    m.add_argument('target')
    m.add_argument('--manuscript', choices=('append', 'archive'))
    r = sub.add_parser('remove')
    r.add_argument('section')
    r.add_argument('--into')
    r.add_argument('--manuscript', choices=('append', 'archive'))
    r.add_argument('--confirm', action='store_true')
    v = sub.add_parser('move')
    v.add_argument('section')
    v.add_argument('chapter')
    v.add_argument('--position', type=int)
    ad = sub.add_parser('add')
    ad.add_argument('chapter')
    ad.add_argument('title')
    ad.add_argument('--position', type=int)
    rn = sub.add_parser('rename')
    rn.add_argument('section')
    rn.add_argument('title')
    ro = sub.add_parser('reorder')
    ro.add_argument('section')
    ro.add_argument('--after')
    a = ap.parse_args(argv)
    base = a.project.resolve()
    if a.cmd == 'add':
        out = cmd_add(base, a.chapter, a.title, a.position)
    elif a.cmd == 'rename':
        out = cmd_rename(base, a.section, a.title)
    elif a.cmd == 'reorder':
        out = cmd_reorder(base, a.section, a.after)
    elif a.cmd == 'merge':
        out = cmd_merge(base, a.sources, a.target, a.manuscript)
    elif a.cmd == 'remove':
        out = cmd_remove(base, a.section, a.into, a.confirm, a.manuscript)
    else:
        out = cmd_move(base, a.section, a.chapter, a.position)
    sys.stdout.write(out)


if __name__ == '__main__':
    main()
