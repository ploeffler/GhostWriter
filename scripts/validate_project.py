#!/usr/bin/env python3
"""Prüft ein GhostWriter-Buchprojekt.

Aufruf: python scripts/validate_project.py <projektordner> [<projektordner> ...]

Geprüft werden:
- ghostwriter.yml gegen schemas/ghostwriter.schema.json
- jede Abschnittsdatei aus structure.chapters: Datei vorhanden, Kopf gegen
  schemas/section.schema.json, ID und Titel wie in ghostwriter.yml, Nummer
  passend zur Reihenfolge
- eindeutige Kapitel- und Abschnitts-IDs, Kapitelordner mit README.md
- workflow.current_chapter_id / current_section_id verweisen auf vorhandene IDs
- jede Kostendatei (chapters/*/costs/*.yml, costs/project.yml) gegen
  schemas/costs.schema.json, eindeutige activity_id, Abschnitts-ID bekannt
- ai_providers: Dienste in `available` stehen in providers.yml; ist `available`
  gesetzt, verwenden die Aufgaben nur diese Dienste (oder chat bzw. manual);
  Einstellungen unter `services` nur für Dienste aus `available`
- Vor- und Nachspann (structure.front_matter/back_matter, #57): Datei vorhanden,
  Kopf gegen schemas/matter.schema.json, ID, Art und Titel wie in ghostwriter.yml,
  ID passt zur Art (mat-widmung …), Datei unter matter/, jede Art höchstens einmal;
  Verfasser und Ort/Datum nur bei Vorwort und Nachwort; Glossar ohne doppelte Begriffe
- Figuren (characters, #53): Datei, Kopf gegen schemas/character.schema.json,
  ID und Name wie in ghostwriter.yml, Beziehungen und `characters` in Abschnitten
  bzw. Teilen verweisen auf bekannte Figuren
- Illustrationen (images/…/img-*.yml, #54): Beschreibung gegen
  schemas/image.schema.json, Bilddatei vorhanden, IDs eindeutig, Abschnitt passt
  zum Ordner, Figuren bekannt; Verweise ![](bild:img-…) im Text zeigen auf Bilder
- publication.isbn_print/isbn_ebook (#68): gültige ISBN-10 bzw. ISBN-13 (Prüfziffer)
- print/cover (#68): Umschlag nur mit Druckprofil; bei bod/custom Rückenbreite
  angegeben; Papier nur bei kdp; Bilder des Umschlags vorhanden
- approvals.yml (falls vorhanden) gegen schemas/approvals.schema.json, IDs bekannt,
  Art passt zur ID (writing: Abschnitt oder Vor-/Nachspann, section: Abschnitt,
  chapter: Kapitel, matter: Vor-/Nachspann)

Endet mit Code 1, sobald ein Fehler gefunden wurde.
"""
import json
import re
import sys
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator, FormatChecker

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'scripts'))
from render_view import (MATTER, MATTER_SIGNED, glossary_duplicates, glossary_entries,  # noqa: E402
                         matter_id, matter_items, section_file)
SCHEMAS = ROOT / 'schemas'


def validator(name):
    schema = json.loads((SCHEMAS / name).read_text(encoding='utf-8'))
    return Draft202012Validator(schema, format_checker=FormatChecker())


GHOSTWRITER = validator('ghostwriter.schema.json')
SECTION = validator('section.schema.json')
COSTS = validator('costs.schema.json')
APPROVALS = validator('approvals.schema.json')
MATTER_HEAD = validator('matter.schema.json')
CHARACTER_HEAD = validator('character.schema.json')
IMAGE_META = validator('image.schema.json')
FRONTMATTER = re.compile(r'\A---\n(.*?)\n---\n', re.S)


def schema_errors(v, data, where):
    return [f'{where}: {"/".join(map(str, e.absolute_path)) or "(Wurzel)"}: {e.message}'
            for e in sorted(v.iter_errors(data), key=lambda e: list(e.absolute_path))]


def load_yaml(path, errors):
    try:
        return yaml.safe_load(path.read_text(encoding='utf-8'))
    except Exception as exc:  # noqa: BLE001 - jede Lesefehlermeldung ist ein Befund
        errors.append(f'{path}: nicht lesbar: {exc}')
        return None


def isbn_ok(value):
    """ISBN-10 oder ISBN-13 mit gültiger Prüfziffer (Bindestriche und Leerzeichen erlaubt)."""
    d = re.sub(r'[ -]', '', value or '').upper()
    if re.fullmatch(r'\d{13}', d):
        return sum(int(c) * (1 if i % 2 == 0 else 3) for i, c in enumerate(d)) % 10 == 0
    if re.fullmatch(r'\d{9}[\dX]', d):
        return sum((10 - i) * (10 if c == 'X' else int(c)) for i, c in enumerate(d)) % 11 == 0
    return False


def known_services():
    path = ROOT / 'providers.yml'
    if not path.is_file():
        return None
    data = yaml.safe_load(path.read_text(encoding='utf-8'))
    return {s['id']: section for section in ('special', 'providers', 'search_tools', 'queue_agents')
            for s in data.get(section) or []}


def provider_errors(config, config_path):
    errors, known = [], known_services()
    ap = config.get('ai_providers') or {}
    available = ap.get('available')
    if known is None or available is None:
        return errors
    for sid in available:
        if sid not in known:
            errors.append(f'{config_path}: ai_providers.available: unbekannter Dienst {sid} (nicht in providers.yml)')
    for sid in ap.get('services') or {}:
        if sid not in available:
            errors.append(f'{config_path}: ai_providers.services.{sid}: Dienst steht nicht in available')
    if not available:
        return errors
    allowed = set(available) | {'chat', ''}
    for role, entry in ap.items():
        if role in ('available', 'rules', 'services') or not isinstance(entry, dict):
            continue
        if role == 'queue_processing':
            agent = entry.get('agent', '')
            if agent not in set(available) | {'manual', ''}:
                errors.append(f'{config_path}: ai_providers.queue_processing.agent {agent} steht nicht in available')
            continue
        if entry.get('provider', '') not in allowed:
            errors.append(f'{config_path}: ai_providers.{role}.provider {entry["provider"]} steht nicht in available')
        for tool in entry.get('search_tools') or []:
            if tool not in available:
                errors.append(f'{config_path}: ai_providers.{role}.search_tools: {tool} steht nicht in available')
    return errors


def check_project(project_dir):
    errors = []
    base = Path(project_dir)
    config_path = base / 'ghostwriter.yml'
    if not config_path.is_file():
        return [f'{config_path}: fehlt']
    config = load_yaml(config_path, errors)
    if config is None:
        return errors
    errors += schema_errors(GHOSTWRITER, config, config_path)
    if errors:
        return errors
    if (base / 'series').is_dir():   # Serien auf dem Standard-Branch einer Bibliothek (#116)
        import series
        errors += [f'{base}/{e}' for e in series.problems(base)]

    chapter_ids, section_ids = set(), set()
    for ci, chapter in enumerate(config['structure']['chapters'], start=1):
        cid = chapter['id']
        if cid in chapter_ids:
            errors.append(f'{config_path}: Kapitel-ID doppelt: {cid}')
        chapter_ids.add(cid)
        if not (base / chapter['path'] / 'README.md').is_file():
            errors.append(f'{base / chapter["path"]}: README.md fehlt')
        for si, section in enumerate(chapter['sections'], start=1):
            sid = section['id']
            if sid in section_ids:
                errors.append(f'{config_path}: Abschnitts-ID doppelt: {sid}')
            section_ids.add(sid)
            if not section['path'].startswith(chapter['path'] + '/sections/'):
                errors.append(f'{config_path}: {sid}: Pfad liegt nicht im Kapitelordner {chapter["path"]}')
            path = base / section['path']
            if not path.is_file():
                errors.append(f'{path}: fehlt')
                continue
            m = FRONTMATTER.match(path.read_text(encoding='utf-8'))
            if not m:
                errors.append(f'{path}: Kopf (--- … ---) fehlt')
                continue
            try:
                head = yaml.safe_load(m.group(1))
            except Exception as exc:  # noqa: BLE001
                errors.append(f'{path}: Kopf nicht lesbar: {exc}')
                continue
            errs = schema_errors(SECTION, head, path)
            errors += errs
            if errs:
                continue
            if head['id'] != sid:
                errors.append(f'{path}: ID {head["id"]} statt {sid} wie in ghostwriter.yml')
            if head['title'] != section['title']:
                errors.append(f'{path}: Titel weicht von ghostwriter.yml ab')
            if head['number'] != f'{ci}.{si}':
                errors.append(f'{path}: Nummer {head["number"]} statt {ci}.{si} laut Reihenfolge')

    matter_ids = set()
    seen_kinds = set()
    for _, item in matter_items(config):
        mid, kind = item['id'], item['kind']
        if mid in matter_ids:
            errors.append(f'{config_path}: Vor-/Nachspann-ID doppelt: {mid}')
        matter_ids.add(mid)
        if kind in seen_kinds:
            errors.append(f'{config_path}: {MATTER[kind][1]} steht mehrfach im Vor-/Nachspann')
        seen_kinds.add(kind)
        if mid != matter_id(kind):
            errors.append(f'{config_path}: {mid}: ID passt nicht zur Art {kind} (erwartet {matter_id(kind)})')
        path = base / item['path']
        if not path.is_file():
            errors.append(f'{path}: fehlt')
            continue
        m = FRONTMATTER.match(path.read_text(encoding='utf-8'))
        if not m:
            errors.append(f'{path}: Kopf (--- … ---) fehlt')
            continue
        try:
            head = yaml.safe_load(m.group(1))
        except Exception as exc:  # noqa: BLE001
            errors.append(f'{path}: Kopf nicht lesbar: {exc}')
            continue
        errs = schema_errors(MATTER_HEAD, head, path)
        errors += errs
        if errs:
            continue
        if head['id'] != mid:
            errors.append(f'{path}: ID {head["id"]} statt {mid} wie in ghostwriter.yml')
        if head['kind'] != kind:
            errors.append(f'{path}: Art {head["kind"]} statt {kind} wie in ghostwriter.yml')
        if head['title'] != item['title']:
            errors.append(f'{path}: Titel weicht von ghostwriter.yml ab')
        for field in ('byline', 'place_date'):
            if field in head and kind not in MATTER_SIGNED:
                errors.append(f'{path}: {field} gibt es nur bei Vorwort und Nachwort')
        if kind == 'glossary':
            for term in glossary_duplicates(glossary_entries(section_file(base, item)[3])[1]):
                errors.append(f'{path}: Begriff mehrfach eingetragen: {term}')

    pr, cv = config.get('print') or {}, config.get('cover') or {}
    formats = (config.get('typesetting') or {}).get('formats') or []
    if 'cover' in formats and not pr.get('profile'):
        errors.append(f'{config_path}: typesetting.formats enthält cover, aber print.profile fehlt (kdp, bod oder custom)')
    if pr.get('profile') in ('bod', 'custom') and pr.get('spine_mm') is None and pr.get('paper_mm_per_page') is None:
        errors.append(f'{config_path}: print: bei {pr["profile"]} die Rückenbreite angeben (spine_mm aus dem Rechner '
                      'des Anbieters oder paper_mm_per_page)')
    if pr.get('paper') and pr.get('profile') != 'kdp':
        errors.append(f'{config_path}: print.paper gilt nur für das Profil kdp; sonst spine_mm bzw. paper_mm_per_page')
    for field in ('image', 'author_image'):
        if cv.get(field) and not (base / cv[field]).is_file():
            errors.append(f'{config_path}: cover.{field}: {cv[field]} fehlt')
    for field in ('isbn_print', 'isbn_ebook'):
        value = (config.get('publication') or {}).get(field)
        if value and not isbn_ok(value):
            errors.append(f'{config_path}: publication.{field}: {value} ist keine gültige ISBN (Prüfziffer)')

    # Figuren (#53): Datei, Kopf, ID und Name wie in ghostwriter.yml, Beziehungen und Verweise bekannt
    char_ids, char_heads = set(), {}
    for item in config.get('characters') or []:
        cid = item['id']
        if cid in char_ids:
            errors.append(f'{config_path}: Figuren-ID doppelt: {cid}')
        char_ids.add(cid)
        path = base / item['path']
        if not path.is_file():
            errors.append(f'{path}: fehlt')
            continue
        m = FRONTMATTER.match(path.read_text(encoding='utf-8'))
        head = None
        try:
            head = yaml.safe_load(m.group(1)) if m else None
        except Exception as exc:  # noqa: BLE001
            errors.append(f'{path}: Kopf nicht lesbar: {exc}')
            continue
        if head is None:
            errors.append(f'{path}: Kopf (--- … ---) fehlt')
            continue
        errs = schema_errors(CHARACTER_HEAD, head, path)
        errors += errs
        if errs:
            continue
        if head['id'] != cid:
            errors.append(f'{path}: ID {head["id"]} statt {cid} wie in ghostwriter.yml')
        if head['name'] != item['name']:
            errors.append(f'{path}: Name weicht von ghostwriter.yml ab')
        char_heads[path] = head
    for path, head in char_heads.items():
        for r in head.get('relations') or []:
            if r['to'] not in char_ids:
                errors.append(f'{path}: Beziehung zu unbekannter Figur {r["to"]}')
    refs = [(base / s['path']) for ch in config['structure']['chapters'] for s in ch['sections']] + \
           [(base / i['path']) for _, i in matter_items(config)]
    for path in refs:
        if not path.is_file():
            continue
        m = FRONTMATTER.match(path.read_text(encoding='utf-8'))
        try:
            head = yaml.safe_load(m.group(1)) if m else {}
        except Exception:  # noqa: BLE001 - Lesefehler meldet die Abschnittsprüfung
            continue
        for cid in (head or {}).get('characters') or []:
            if cid not in char_ids:
                errors.append(f'{path}: unbekannte Figur {cid}')

    # Illustrationen (#54): Beschreibung gegen das Schema, Datei da, IDs eindeutig, Abschnitt passt, Verweise bekannt
    import images
    image_ids = set()
    for target, folder in images.image_folders(config):
        d = base / folder
        if not d.is_dir():
            continue
        for meta_path in sorted(d.glob('img-*.yml')):
            meta = load_yaml(meta_path, errors)
            if meta is None:
                continue
            errs = schema_errors(IMAGE_META, meta, meta_path)
            errors += errs
            if errs:
                continue
            if meta['id'] in image_ids:
                errors.append(f'{meta_path}: Bild-ID doppelt: {meta["id"]}')
            image_ids.add(meta['id'])
            if meta_path.stem != meta['id']:
                errors.append(f'{meta_path}: Dateiname passt nicht zur ID {meta["id"]}')
            if meta['section_id'] != target['id']:
                errors.append(f'{meta_path}: section_id {meta["section_id"]} statt {target["id"]} (Ordner)')
            if not (d / meta['file']).is_file():
                errors.append(f'{d / meta["file"]}: fehlt')
            for cid in meta.get('characters') or []:
                if cid not in char_ids:
                    errors.append(f'{meta_path}: unbekannte Figur {cid}')
    for path in refs:
        if path.is_file():
            for iid in images.refs_in(path.read_text(encoding='utf-8')):
                if iid not in image_ids:
                    errors.append(f'{path}: Bild {iid} gibt es nicht')

    wf = config['workflow']
    if wf['current_chapter_id'] and wf['current_chapter_id'] not in chapter_ids:
        errors.append(f'{config_path}: workflow.current_chapter_id unbekannt: {wf["current_chapter_id"]}')
    if wf['current_section_id'] and wf['current_section_id'] not in section_ids:
        errors.append(f'{config_path}: workflow.current_section_id unbekannt: {wf["current_section_id"]}')

    activity_ids = set()
    cost_files = sorted(base.glob('chapters/*/costs/*.yml'))
    if (base / 'costs' / 'project.yml').is_file():
        cost_files.append(base / 'costs' / 'project.yml')
    for path in cost_files:
        data = load_yaml(path, errors)
        if data is None:
            continue
        errs = schema_errors(COSTS, data, path)
        errors += errs
        if errs:
            continue
        file_section = data.get('section_id')
        if file_section and file_section not in section_ids:
            errors.append(f'{path}: unbekannte Abschnitts-ID {file_section}')
        if file_section and path.stem != file_section:
            errors.append(f'{path}: Dateiname passt nicht zu section_id {file_section}')
        for entry in data['entries']:
            if entry['activity_id'] in activity_ids:
                errors.append(f'{path}: activity_id doppelt: {entry["activity_id"]}')
            activity_ids.add(entry['activity_id'])
            if file_section and entry.get('section_id') not in (None, file_section):
                errors.append(f'{path}: {entry["activity_id"]}: section_id passt nicht zur Datei')
    errors += provider_errors(config, config_path)

    approvals_path = base / 'approvals.yml'
    if approvals_path.is_file():
        data = load_yaml(approvals_path, errors)
        if data is not None:
            errs = schema_errors(APPROVALS, data, approvals_path)
            errors += errs
            if not errs:
                known_by_kind = {'chapter': (chapter_ids, 'Kapitel'), 'section': (section_ids, 'Abschnitt'),
                                 'matter': (matter_ids, 'Teil des Vor-/Nachspanns'),
                                 'writing': (section_ids | matter_ids, 'Abschnitt bzw. Teil'),
                                 'image': (image_ids, 'Bild')}
                for i, entry in enumerate(data['entries'], start=1):
                    known, art = known_by_kind[entry['kind']]
                    if entry['id'] not in known:
                        errors.append(f'{approvals_path}: Eintrag {i}: {art} {entry["id"]} unbekannt')
    return errors


def main(argv):
    if len(argv) < 2:
        print(__doc__)
        return 2
    failed = False
    for project_dir in argv[1:]:
        errors = check_project(project_dir)
        if errors:
            failed = True
            print(f'✗ {project_dir}: {len(errors)} Fehler')
            for e in errors:
                print(f'  - {e}')
        else:
            print(f'✓ {project_dir}')
    return 1 if failed else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
