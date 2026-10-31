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

Endet mit Code 1, sobald ein Fehler gefunden wurde.
"""
import json
import re
import sys
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator, FormatChecker

ROOT = Path(__file__).resolve().parent.parent
SCHEMAS = ROOT / 'schemas'


def validator(name):
    schema = json.loads((SCHEMAS / name).read_text(encoding='utf-8'))
    return Draft202012Validator(schema, format_checker=FormatChecker())


GHOSTWRITER = validator('ghostwriter.schema.json')
SECTION = validator('section.schema.json')
COSTS = validator('costs.schema.json')
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
