#!/usr/bin/env python3
"""Figuren eines Buchs (#53): anlegen, Abschnitten zuordnen, Kontext für KI-Läufe.

Aufruf:
  python scripts/characters.py <projektordner> list
  python scripts/characters.py <projektordner> add "<Name>" [--role main|supporting|minor] [--short "Ein Satz"]
  python scripts/characters.py <projektordner> assign <abschnitt N.M|sec-…|mat-…> [<figur> …]
  python scripts/characters.py <projektordner> context <abschnitt N.M|sec-…|mat-…>
  python scripts/characters.py <projektordner> update <figur> '<json>'
Serien (#116; <projektordner> = Buch, --series-repo = Ordner mit dem Standard-Branch):
  python scripts/characters.py <buch> detach <figur>       Kopie einer Figur der Serie nur für dieses Buch
  python scripts/characters.py <buch> align <figur>        Kopie entfernen, wieder die Figur der Serie
  python scripts/characters.py <buch> adopt <figur> --series-repo <standard>   Figur des Buchs in die Serie übernehmen
  python scripts/characters.py <standard> series-add <ser-id> "<Name>" [--role …] [--short …]
  python scripts/characters.py <standard> series-update <ser-id> <figur> '<json>'

Figuren der Serie liegen unter series/<ser-id>/characters/ auf dem Standard-Branch
und gelten in jedem Band (render_view.load hängt sie an). Hat ein Band eine Figur
mit derselben ID, ist das seine Kopie: Sie gilt nur dort; weicht sie ab, zeigen
die Ansichten das an.

update übernimmt die Daten des Formulars „Figur bearbeiten“ (character.update):
name, role, short, age, appearance, traits (Liste), voice, visual, relations
(Liste {to, kind}), description, notes. Leere Werte entfernen das Feld. Ein neuer
Name ändert auch ghostwriter.yml; die ID bleibt.

add legt characters/<char-id>.md aus templates/character.md an und trägt die
Figur in ghostwriter.yml ein (Block `characters`); der Rest der Datei bleibt
Zeichen für Zeichen erhalten. Die ID entsteht aus dem Namen (char-<slug>).

assign setzt `characters: [...]` im Kopf eines Abschnitts bzw. eines Teils von
Vor- oder Nachspann (ohne Figuren: Zeile entfernt). Figuren gehen nach Name
oder ID.

context gibt die Beschreibungen der Figuren eines Abschnitts als Markdown aus:
Diesen Block bekommen Brainstorming, Ghostwriting, Überarbeiten und Faktencheck
als Kontext (START.md, „Figuren“), damit Namen, Eigenschaften und Sprechweise
stimmig bleiben. Figuren kommen nie ins Buch.

Den Commit schreibt der Assistent (START.md, „Figuren“).
"""
import argparse
import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'scripts'))
from render_view import (ROLE_DE, character_file, character_items, find_character, find_matter,  # noqa: E402
                         load, section_file, tag_slug)


def block(items):
    if not items:   # keine Figuren (mehr): Block entfällt
        return ''
    out = ['characters:']
    for i in items:
        name = yaml.safe_dump(i['name'], allow_unicode=True).splitlines()[0]
        out += [f'- id: {i["id"]}', f'  name: {name}', f'  path: {i["path"]}']
    return '\n'.join(out) + '\n'


def write_list(base, items):
    # Figuren der Serie (#116) gehören nicht ins Buch; Hilfsfelder (`_…`) werden nicht gespeichert
    items = [{k: v for k, v in i.items() if not k.startswith('_')} for i in items if '_series' not in i]
    path = base / 'ghostwriter.yml'
    text = path.read_text(encoding='utf-8')
    m = re.search(r'(?m)^characters:.*\n(?:(?:[ -].*|)\n)*', text)
    if m:
        new = text[:m.start()] + block(items) + text[m.end():]
    else:
        s = re.search(r'(?m)^structure:', text)
        if not s:
            raise SystemExit('ghostwriter.yml: structure nicht gefunden')
        new = text[:s.start()] + block(items) + text[s.start():]
    if (yaml.safe_load(new).get('characters') or []) != items:
        raise SystemExit('ghostwriter.yml ließ sich nicht sicher ändern; bitte von Hand eintragen.')
    path.write_text(new, encoding='utf-8')


def add(base, name, role='main', short=''):
    _, config = load(base)
    items = character_items(config)
    name = name.strip()
    if not name:
        raise SystemExit('Name fehlt.')
    if any(i['name'].casefold() == name.casefold() for i in items):
        raise SystemExit(f'Die Figur „{name}“ gibt es schon.')
    cid, n = 'char-' + (tag_slug(name) or 'figur'), 2
    while any(i['id'] == cid for i in items) or (base / 'characters' / f'{cid}.md').exists():
        cid = f'char-{tag_slug(name) or "figur"}-{n}'
        n += 1
    item = {'id': cid, 'name': name, 'path': f'characters/{cid}.md'}
    tpl = (ROOT / 'templates' / 'character.md').read_text(encoding='utf-8')
    qname = yaml.safe_dump(name, allow_unicode=True, default_style='"').splitlines()[0]
    body = (tpl.replace('<char-ID>', cid).replace('"<NAME>"', qname).replace('# <NAME>', f'# {name}')
            .replace('role: main   # main (Hauptfigur) | supporting (Nebenfigur) | minor (Randfigur)', f'role: {role}')
            .replace('short: ""', 'short: ' + yaml.safe_dump(short or '', allow_unicode=True, default_style='"').splitlines()[0]))
    (base / 'characters').mkdir(exist_ok=True)
    (base / item['path']).write_text(body, encoding='utf-8')
    write_list(base, items + [item])
    return item


def find_target(config, key):
    """Abschnitt (N.M oder sec-…) bzw. Teil (mat-… oder Name) → Eintrag mit path."""
    chapters = config['structure']['chapters']
    if re.fullmatch(r'\d+\.\d+', key):
        c, s = (int(x) for x in key.split('.'))
        return chapters[c - 1]['sections'][s - 1]
    for ch in chapters:
        for s in ch['sections']:
            if s['id'] == key:
                return s
    item = find_matter(config, key)
    if item:
        return item
    raise SystemExit(f'Abschnitt bzw. Teil „{key}“ nicht gefunden')


def assign(base, key, names):
    _, config = load(base)
    target = find_target(config, key)
    ids = []
    for n in names:
        c = find_character(config, n)
        if not c:
            raise SystemExit(f'Figur „{n}“ nicht gefunden')
        if c['id'] not in ids:
            ids.append(c['id'])
    path = base / target['path']
    text = path.read_text(encoding='utf-8')
    m = re.match(r'\A---\n(.*?)\n---\n', text, re.S)
    head = re.sub(r'(?m)^characters:.*\n?', '', m.group(1) + '\n').rstrip('\n')
    if ids:
        line = 'characters: [' + ', '.join(ids) + ']'
        head = re.sub(r'(?m)^approvals:', line + '\napprovals:', head, count=1) if 'approvals:' in head else head + '\n' + line
    path.write_text('---\n' + head + '\n---\n' + text[m.end():], encoding='utf-8')
    return target, ids


def context(base, key):
    """Markdown mit den Figuren eines Abschnitts bzw. Teils (Kontext für KI-Läufe)."""
    _, config = load(base)
    target = find_target(config, key)
    ids = section_file(base, target)[0].get('characters') or []
    if not ids:
        return ''
    by_id = {i['id']: i for i in character_items(config)}
    names = {i['id']: i['name'] for i in character_items(config)}
    out = ['## Figuren in diesem Abschnitt', '']
    for cid in ids:
        item = by_id.get(cid)
        if not item:
            continue
        head, desc, _ = character_file(base, item)
        line = f'### {item["name"]} ({ROLE_DE.get(head.get("role"), head.get("role", ""))})'
        out += [line, '']
        for key, label in (('short', 'Kurz'), ('age', 'Alter'), ('appearance', 'Aussehen'), ('voice', 'Sprechweise')):
            if head.get(key):
                out.append(f'- {label}: {head[key]}')
        if head.get('traits'):
            out.append('- Eigenschaften: ' + ', '.join(head['traits']))
        for r in head.get('relations') or []:
            out.append(f'- Beziehung: {r["kind"]} von {names.get(r["to"], r["to"])}')
        if desc:
            out += ['', desc]
        out.append('')
    return '\n'.join(out).rstrip() + '\n'


HEAD_FIELDS = ['id', 'name', 'role', 'short', 'age', 'appearance', 'traits', 'voice', 'visual', 'relations']


def apply(head, desc, notes, data):
    """Formularwerte auf Kopf, Beschreibung und Notizen anwenden → (geordneter Kopf, Dateitext)."""
    for k in HEAD_FIELDS[1:]:
        if k in data:
            v = data[k]
            if isinstance(v, str):
                v = v.strip()
            if k == 'traits' and isinstance(v, str):
                v = [t.strip() for t in v.split(',') if t.strip()]
            if v in ('', [], None):
                head.pop(k, None)
            else:
                head[k] = v
    if not head.get('name'):
        raise SystemExit('Der Name darf nicht leer sein.')
    desc = data.get('description', desc).strip() if isinstance(data.get('description', desc), str) else desc
    notes = data.get('notes', notes).strip() if isinstance(data.get('notes', notes), str) else notes
    ordered = {k: head[k] for k in HEAD_FIELDS if k in head and head[k] not in ('', [], None)}
    text = ('---\n' + yaml.safe_dump(ordered, allow_unicode=True, sort_keys=False, width=10**6) + '---\n\n'
            + f'# {ordered["name"]}\n\n## Beschreibung\n\n' + (desc + '\n\n' if desc else '') + '## Notizen\n'
            + ('\n' + notes + '\n' if notes else ''))
    return ordered, text


def update(base, key, data):
    _, config = load(base)
    item = find_character(config, key)
    if not item:
        raise SystemExit(f'Figur „{key}“ nicht gefunden')
    if '_series' in item:
        raise SystemExit(f'„{item["name"]}“ gehört zur Serie: dort bearbeiten (series_update, gilt für alle Bände) '
                         'oder für dieses Buch eine Kopie anlegen (detach).')
    ordered, text = apply(*character_file(base, item), data)
    (base / item['path']).write_text(text, encoding='utf-8')
    if ordered['name'] != item['name']:
        write_list(base, [dict(i, name=ordered['name']) if i['id'] == item['id'] else i for i in character_items(config)])
    return dict(item, name=ordered['name'])


# ---------- Serien (#116): Figuren der Serie, Kopie je Band ----------

def series_item(config, key):
    item = find_character(config, key)
    if not item:
        raise SystemExit(f'Figur „{key}“ nicht gefunden')
    return item


def detach(base, key):
    """Kopie einer Figur der Serie nur für dieses Buch anlegen (gleiche ID; die Kopie gilt hier)."""
    _, config = load(base)
    item = series_item(config, key)
    if '_series' not in item:
        raise SystemExit(f'„{item["name"]}“ ist keine Figur der Serie' + (' (schon eine Kopie)' if item.get('_copy_of') else ''))
    own = [i for i in character_items(config) if '_series' not in i]
    new = {'id': item['id'], 'name': item['name'], 'path': f'characters/{item["id"]}.md'}
    (base / 'characters').mkdir(exist_ok=True)
    (base / new['path']).write_text(item['_text'], encoding='utf-8')
    write_list(base, own + [new])
    return new


def align(base, key):
    """Kopie entfernen: Das Buch nutzt wieder die Figur der Serie."""
    _, config = load(base)
    item = series_item(config, key)
    if not item.get('_copy_of'):
        raise SystemExit(f'„{item["name"]}“ ist keine Kopie einer Figur der Serie')
    (base / item['path']).unlink(missing_ok=True)
    write_list(base, [i for i in character_items(config) if '_series' not in i and i['id'] != item['id']])
    return item


def adopt(base, main_dir, key):
    """Figur des Buchs (Kopie oder eigene) in die Serie übernehmen: Datei nach series/<sid>/characters/ auf dem
    Standard-Branch (main_dir), im Buch entfernen. Zwei Commits: Standard-Branch und Buch."""
    _, config = load(base)
    ser = config.get('_series')
    if not ser:
        raise SystemExit('Dieses Buch gehört zu keiner Serie')
    item = series_item(config, key)
    if '_series' in item:
        raise SystemExit(f'„{item["name"]}“ gehört schon zur Serie')
    dest = Path(main_dir) / 'series' / ser['id'] / 'characters' / f'{item["id"]}.md'
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text((base / item['path']).read_text(encoding='utf-8'), encoding='utf-8')
    (base / item['path']).unlink()
    write_list(base, [i for i in character_items(config) if '_series' not in i and i['id'] != item['id']])
    return item, ser


def series_add(main_dir, sid, name, role='main', short=''):
    """Neue Figur der Serie unter series/<sid>/characters/ (Standard-Branch)."""
    import series as series_mod
    s, _ = series_mod.get(main_dir, sid)
    folder = Path(main_dir) / 'series' / s['id'] / 'characters'
    existing = series_mod.characters(main_dir, s['id'])
    if any(c['name'].casefold() == name.strip().casefold() for c in existing):
        raise SystemExit(f'Die Figur „{name}“ gibt es in der Serie schon.')
    cid, n = 'char-' + (tag_slug(name) or 'figur'), 2
    while (folder / f'{cid}.md').exists():
        cid = f'char-{tag_slug(name) or "figur"}-{n}'
        n += 1
    ordered, text = apply({'id': cid, 'name': name.strip(), 'role': role}, '', '', {'short': short})
    folder.mkdir(parents=True, exist_ok=True)
    (folder / f'{cid}.md').write_text(text, encoding='utf-8')
    return {'id': cid, 'name': ordered['name'], 'path': f'series/{s["id"]}/characters/{cid}.md'}


def series_update(main_dir, sid, key, data):
    """Figur der Serie bearbeiten (gilt für alle Bände ohne eigene Kopie)."""
    import series as series_mod
    s, _ = series_mod.get(main_dir, sid)
    k = (key or '').casefold()
    hit = [c for c in series_mod.characters(main_dir, s['id']) if k in (c['id'], c['id'][5:], c['name'].casefold())]
    if not hit:
        raise SystemExit(f'Figur „{key}“ gibt es in der Serie nicht')
    item = hit[0]
    ordered, text = apply(*character_file(Path(main_dir), item), data)
    (Path(main_dir) / item['path']).write_text(text, encoding='utf-8')
    return dict(item, name=ordered['name'])


def main(argv):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('project')
    ap.add_argument('cmd', choices=['list', 'add', 'assign', 'context', 'update', 'detach', 'align', 'adopt',
                                    'series-add', 'series-update'])
    ap.add_argument('--series-repo', help='bei adopt, series-add, series-update: Ordner mit dem Standard-Branch (series/)')
    ap.add_argument('args', nargs='*')
    ap.add_argument('--role', default='main', choices=list(ROLE_DE))
    ap.add_argument('--short', default='')
    a = ap.parse_args(argv[1:])
    base = Path(a.project)
    if a.cmd == 'list':
        _, config = load(base)
        for i in character_items(config):
            head = character_file(base, i)[0]
            print(f'{i["id"]:<24} {i["name"]} ({ROLE_DE.get(head.get("role"), "")})')
        return 0
    if a.cmd == 'add':
        if len(a.args) != 1:
            ap.error('add braucht genau einen Namen')
        item = add(base, a.args[0], a.role, a.short)
        print(f'✓ Figur „{item["name"]}“ angelegt: {item["path"]}')
        print(f'Commit-Nachricht: Figur „{item["name"]}“ angelegt')
        return 0
    if a.cmd in ('detach', 'align', 'adopt'):
        if len(a.args) != 1:
            ap.error(f'{a.cmd} braucht eine Figur')
        if a.cmd == 'detach':
            item = detach(base, a.args[0])
            print(f'✓ Kopie von „{item["name"]}“ für dieses Buch angelegt\nCommit-Nachricht: Figur „{item["name"]}“: Kopie für dieses Buch')
        elif a.cmd == 'align':
            item = align(base, a.args[0])
            print(f'✓ „{item["name"]}“ wieder wie in der Serie\nCommit-Nachricht: Figur „{item["name"]}“ an die Serie angeglichen')
        else:
            if not a.series_repo:
                ap.error('adopt braucht --series-repo (Standard-Branch)')
            item, ser = adopt(base, a.series_repo, a.args[0])
            print(f'✓ „{item["name"]}“ in die Serie „{ser["title"]}“ übernommen\n'
                  f'Commit-Nachricht (Standard-Branch): Figur „{item["name"]}“ in die Serie übernommen\n'
                  f'Commit-Nachricht (Buch): Figur „{item["name"]}“ gehört jetzt zur Serie')
        return 0
    if a.cmd in ('series-add', 'series-update'):
        import json
        if len(a.args) != (2 if a.cmd == 'series-add' else 3):
            ap.error('series-add braucht Serie und Name; series-update Serie, Figur und JSON')
        repo = a.series_repo or a.project
        if a.cmd == 'series-add':
            item = series_add(repo, a.args[0], a.args[1], a.role, a.short)
            print(f'✓ Figur „{item["name"]}“ in der Serie angelegt: {item["path"]}\nCommit-Nachricht: Figur „{item["name"]}“ in der Serie angelegt')
        else:
            item = series_update(repo, a.args[0], a.args[1], json.loads(a.args[2]))
            print(f'✓ Figur „{item["name"]}“ der Serie gespeichert\nCommit-Nachricht: Figur „{item["name"]}“ der Serie gespeichert')
        return 0
    if not a.args:
        ap.error(f'{a.cmd} braucht einen Abschnitt')
    if a.cmd == 'update':
        import json
        if len(a.args) != 2:
            ap.error('update braucht Figur und JSON')
        item = update(base, a.args[0], json.loads(a.args[1]))
        print(f'✓ Figur „{item["name"]}“ gespeichert')
        print(f'Commit-Nachricht: Figur „{item["name"]}“ gespeichert')
        return 0
    if a.cmd == 'assign':
        target, ids = assign(base, a.args[0], a.args[1:])
        print(f'✓ Figuren in „{target["title"]}“: {", ".join(ids) or "keine"}')
        print(f'Commit-Nachricht: Figuren in „{target["title"]}“ zugeordnet')
        return 0
    sys.stdout.write(context(base, a.args[0]) or 'Diesem Abschnitt sind keine Figuren zugeordnet.\n')
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
