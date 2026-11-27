#!/usr/bin/env python3
"""Prüft ein GhostWriter-Buchprojekt.

Aufruf: python scripts/validate_project.py <projektordner> [<projektordner> ...]

Geprüft werden:
- ghostwriter.yml gegen schemas/ghostwriter.schema.json
- Aufträge der Hintergrund-Warteschlange (request-NNN.yml) gegen schemas/job.schema.json (#480)
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
  angegeben; Papier nur bei kdp; Bilder des Umschlags und eigene Vorderseite (cover.front, #324) vorhanden
- Schauplätze, Zeitleiste und Hinweise (story/places.yml, story/timeline.yml, story/hints.yml, #124;
  Chronologie story/chronology.yml, #354;
  falls vorhanden) gegen ihr Schema, IDs eindeutig, Abschnitte bekannt
- Prüfprotokoll (editorial/checks.yml, #331; falls vorhanden) gegen
  schemas/checks.schema.json, IDs eindeutig, Umfang bekannt, Bericht vorhanden
- editorial/<bericht>.yml (Befunde) und editorial/durchsicht-*.yml (#367) gegen
  schemas/findings.schema.json bzw. schemas/notes-review.schema.json, IDs eindeutig, Abschnitte bekannt
- assistant.yml (falls vorhanden, #136) gegen schemas/assistant.schema.json; der
  persönliche Skill .claude/skills/<skill>/SKILL.md passt dazu (scripts/assistant.py check)
- approvals.yml (falls vorhanden) gegen schemas/approvals.schema.json, IDs bekannt
  oder einzelne historische Verweise ausdrücklich dokumentiert,
  Art passt zur ID (writing: Abschnitt oder Vor-/Nachspann, section: Abschnitt,
  chapter: Kapitel, matter: Vor-/Nachspann)


Hinweise (⚠, kein Fehler): eine weitere `## `-Überschrift nach `## Manuskript` in einer Abschnitts-
oder Vor-/Nachspanndatei, mit Datei und Zeile – meist eine Arbeitsnotiz, die sonst mit ins Buch käme (#435).

Endet mit Code 1, sobald ein Fehler gefunden wurde; Hinweise ändern den Code nicht.
"""
import hashlib
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
REFERENCE_IMAGE_META = validator('reference-image.schema.json')
IMAGE_STYLE = validator('image-style.schema.json')
FIGURE_IMAGES = validator('figure-images.schema.json')
PLACES = validator('places.schema.json')
TIMELINE = validator('timeline.schema.json')
CHRONOLOGY = validator('chronology.schema.json')
HINTS = validator('hints.schema.json')
CHECKS = validator('checks.schema.json')
JOB = validator('job.schema.json')
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


def story_errors(base, config):
    """story/places.yml, timeline.yml, hints.yml (#124): Schema, eindeutige IDs, bekannte Abschnitte."""
    errors = []
    known = {s['id'] for ch in config['structure']['chapters'] for s in ch['sections']}
    known |= {i['id'] for _, i in matter_items(config)}
    for name, v, key, refs in (('places', PLACES, 'places', 'sections'), ('timeline', TIMELINE, 'events', 'section'),
                               ('hints', HINTS, 'hints', 'section')):
        path = base / 'story' / f'{name}.yml'
        if not path.is_file():
            continue
        data = load_yaml(path, errors)
        if data is None:
            continue
        errs = schema_errors(v, data, path)
        errors += errs
        if errs:
            continue
        ids = [x['id'] for x in data[key]]
        errors += [f'{path}: ID doppelt: {i}' for i in sorted({i for i in ids if ids.count(i) > 1})]
        for x in data[key]:
            for sid in ([x[refs]] if isinstance(x.get(refs), str) else x.get(refs) or []):
                if sid not in known:
                    errors.append(f'{path}: {x["id"]}: Abschnitt {sid} unbekannt')
        for n in data.get('notes') or []:
            errors += [f'{path}: Hinweis verweist auf unbekanntes Ereignis {e}' for e in n.get('events') or [] if e not in ids]
    path = base / 'story' / 'chronology.yml'   # Chronologie (#354): Schema, IDs, Figuren, Kapitel, Orte, Datumsangaben
    if path.is_file():
        data = load_yaml(path, errors)
        if data is not None:
            errs = schema_errors(CHRONOLOGY, data, path)
            errors += errs
            if not errs:
                import chronology
                errors += chronology.references(base, config, data)
    tl = base / 'story' / 'timeline.yml'   # Verknüpfung Text-Zeitleiste → Chronologie (#364)
    if tl.is_file():
        import chronology
        chron = chronology.read(base) or {}
        known_chr = {e.get('id') for e in chron.get('entries') or [] if isinstance(e, dict)}
        for ev in chronology.timeline_events(base):
            if ev.get('chronology') and ev['chronology'] not in known_chr:
                errors.append(f'{tl}: {ev.get("id")}: Chronologie-Eintrag {ev["chronology"]} unbekannt')
    return errors


def checks_errors(base, config):
    """Prüfprotokoll editorial/checks.yml (#331): Schema, dann Inhalt (scripts/checks.py)."""
    import checks
    path = checks.path(base)
    if not path.is_file():
        return []
    errors = []
    data = load_yaml(path, errors)
    if data is None:
        return errors
    data = checks.normalize(data)
    errs = schema_errors(CHECKS, data, path)
    return errs or checks.errors(base, config)


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
    if config.get('team'):   # Team und Rollen (#455)
        import team
        errors += [f'{config_path}: {e}' for e in team.problems(config)]
    if (base / 'assistant.yml').is_file():   # Assistenten-Profil und persönlicher Skill (#136)
        import assistant
        errors += [f'{base}/{e}' for e in assistant.check(base)]

    if (base / 'checkouts.yml').is_file():   # Bereiche zum Gegenlesen (#572)
        import checkout
        errors += [f'{base}/{e}' for e in checkout.problems(base, config)]

    if (base / 'quellen').is_dir():   # eingebrachtes Material (#574)
        import material
        errors += [f'{base}/{e}' for e in material.problems(base)]

    import jobs   # Aufträge der Hintergrund-Warteschlange (#480)
    for path in jobs.files(base):
        data = load_yaml(path, errors)
        if data is not None:
            errors += schema_errors(JOB, data, path)

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
            if head['status'] == 'approved' and (head.get('approvals') or {}).get('section') is not True:
                errors.append(f'{path}: Status approved ohne approvals.section=true')

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
    from cover_design import validate as validate_cover
    from build_cover import PAGE
    size = PAGE.get((config.get('typesetting') or {}).get('page_size', 'a5'), PAGE['a5'])
    errors.extend(f'{config_path}: {error}' for error in validate_cover(cv, *size))
    formats = (config.get('typesetting') or {}).get('formats') or []
    if 'cover' in formats and not pr.get('profile'):
        errors.append(f'{config_path}: typesetting.formats enthält cover, aber print.profile fehlt (kdp, bod oder custom)')
    if pr.get('profile') in ('bod', 'custom') and pr.get('spine_mm') is None and pr.get('paper_mm_per_page') is None:
        errors.append(f'{config_path}: print: bei {pr["profile"]} die Rückenbreite angeben (spine_mm aus dem Rechner '
                      'des Anbieters oder paper_mm_per_page)')
    if pr.get('paper') and pr.get('profile') != 'kdp':
        errors.append(f'{config_path}: print.paper gilt nur für das Profil kdp; sonst spine_mm bzw. paper_mm_per_page')
    for field in ('image', 'author_image', 'front'):   # front: eigene Vorderseite (#324)
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
    try:   # Figuren der Serie (#116) gelten in jedem Band
        import series
        _, sitems = series.book_characters(base)
    except Exception:   # noqa: BLE001
        sitems = None
    char_ids |= {i['id'] for i in sitems or []}
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
            if meta.get('original_file'):
                from media_policy import safe_destination
                try:
                    original = safe_destination(base, Path(folder) / meta['original_file'])
                    if not original.is_file():
                        errors.append(f'{meta_path}: Originaldatei fehlt')
                    elif hashlib.sha256(original.read_bytes()).hexdigest() != meta['original_sha256']:
                        errors.append(f'{meta_path}: Original-Fingerabdruck stimmt nicht überein')
                except (ValueError, OSError) as exc:
                    errors.append(f'{meta_path}: Originaldatei nicht sicher lesbar: {exc}')
            for cid in meta.get('characters') or []:
                if cid not in char_ids:
                    errors.append(f'{meta_path}: unbekannte Figur {cid}')
    for path in refs:
        if path.is_file():
            for iid in images.refs_in(path.read_text(encoding='utf-8')):
                if iid not in image_ids:
                    errors.append(f'{path}: Bild {iid} gibt es nicht')
    sections = {base / s['path'] for ch in config['structure']['chapters'] for s in ch['sections']}
    errors += images.placement_problems([(str(path), path.read_text(encoding='utf-8'), path in sections)
                                         for path in refs if path.is_file()])

    # Figurenbilder (#540): Bildstil des Projekts und Bilder je Figur
    style_path = base / 'images' / 'stil.yml'
    if style_path.is_file():
        style = load_yaml(style_path, errors)
        if style is not None:
            errors += schema_errors(IMAGE_STYLE, style, style_path)
    for fig_path in sorted((base / 'characters').glob('char-*/bilder.yml')):
        data = load_yaml(fig_path, errors)
        if data is None:
            continue
        errs = schema_errors(FIGURE_IMAGES, data, fig_path)
        errors += errs
        if errs:
            continue
        if data['figur'] != fig_path.parent.name:
            errors.append(f'{fig_path}: figur passt nicht zum Ordner {fig_path.parent.name}')
        ids = [i['id'] for i in data['bilder']]
        if len(ids) != len(set(ids)):
            errors.append(f'{fig_path}: Bild-IDs doppelt')
        for img in data['bilder']:
            if not (fig_path.parent / img['datei']).is_file():
                errors.append(f'{fig_path}: Bilddatei fehlt: {img["datei"]}')
            for ref in img.get('eingabe') or []:
                if ref not in ids:
                    errors.append(f'{fig_path}: Eingabebild {ref} unbekannt ({img["id"]})')

    # Projektweite Referenzbilder bleiben von Buchillustrationen getrennt.
    reference_dir = base / 'reference-images'
    reference_ids = set()
    if reference_dir.is_dir():
        for meta_path in sorted(reference_dir.glob('ref-img-*.yml')):
            meta = load_yaml(meta_path, errors)
            if meta is None:
                continue
            errs = schema_errors(REFERENCE_IMAGE_META, meta, meta_path)
            errors += errs
            if errs:
                continue
            if meta['id'] in reference_ids:
                errors.append(f'{meta_path}: Referenzbild-ID doppelt: {meta["id"]}')
            reference_ids.add(meta['id'])
            if meta_path.stem != meta['id']:
                errors.append(f'{meta_path}: Dateiname passt nicht zur ID {meta["id"]}')
            if not (reference_dir / meta['file']).is_file():
                errors.append(f'{reference_dir / meta["file"]}: fehlt')
            for link in meta.get('links') or []:
                if link['kind'] == 'person' and link['id'] not in char_ids:
                    errors.append(f'{meta_path}: unbekannte Figur {link["id"]}')
                if link['kind'] == 'chapter' and link['id'] not in chapter_ids:
                    errors.append(f'{meta_path}: unbekanntes Kapitel {link["id"]}')
                if link['kind'] == 'section' and link['id'] not in section_ids:
                    errors.append(f'{meta_path}: unbekannter Abschnitt {link["id"]}')

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

    errors += story_errors(base, config)
    errors += checks_errors(base, config)
    import hinweise   # Befunde und Hinweisdurchsicht (#367)
    errors += hinweise.errors(base, config)
    import rules   # Grundregeln: Lockerung nur mit Bestätigung, Untergrenzen (#300)
    errors += rules.problems(base, config)
    approvals_path = base / 'approvals.yml'
    if approvals_path.is_file():
        data = load_yaml(approvals_path, errors)
        if data is not None:
            errs = schema_errors(APPROVALS, data, approvals_path)
            errors += errs
            if not errs:
                # Entfernte bzw. zusammengelegte Abschnitte (#293): ihre Protokolleinträge bleiben gültig.
                retired = {r['id'] for r in (config['structure'].get('retired') or [])}
                known_by_kind = {'chapter': (chapter_ids, 'Kapitel'), 'section': (section_ids | retired, 'Abschnitt'),
                                 'matter': (matter_ids, 'Teil des Vor-/Nachspanns'),
                                 'writing': (section_ids | matter_ids | retired, 'Abschnitt bzw. Teil'),
                                 'image': (image_ids, 'Bild'),
                                 'rules': ({'rules-facts', 'rules-creativity', 'rules-approvals'}, 'Regelgruppe')}
                historical = {}
                for ref in data.get('historical_references', []):
                    number = ref['entry']
                    if number in historical:
                        errors.append(f'{approvals_path}: historische Referenz für Eintrag {number} doppelt')
                    elif number > len(data['entries']):
                        errors.append(f'{approvals_path}: historischer Eintrag {number} existiert nicht')
                    else:
                        historical[number] = ref
                        entry = data['entries'][number - 1]
                        if (entry['kind'], entry['id']) != (ref['kind'], ref['id']):
                            errors.append(f'{approvals_path}: historische Referenz für Eintrag {number} passt nicht')
                for i, entry in enumerate(data['entries'], start=1):
                    known, art = known_by_kind[entry['kind']]
                    ref = historical.get(i)
                    documented = ref and (entry['kind'], entry['id']) == (ref['kind'], ref['id'])
                    if entry['id'] not in known and not documented:
                        errors.append(f'{approvals_path}: Eintrag {i}: {art} {entry["id"]} unbekannt')
                    if entry['kind'] in ('section', 'matter') and entry['action'] == 'granted' and not str(entry.get('note', '')).startswith('content_sha256='):
                        errors.append(f'{approvals_path}: Abschnittsfreigabe {entry["id"]} ohne Manuskript-Fingerabdruck in note')

                latest = {}
                for entry in data.get('entries', []):
                    latest[(entry['kind'], entry['id'])] = entry
                for chapter in config['structure']['chapters']:
                    chapter_record = latest.get(('chapter', chapter['id']))
                    if chapter.get('status') == 'approved' and (not chapter_record or chapter_record.get('action') != 'granted'):
                        errors.append(f'{chapter["id"]}: approved ohne letzte gültige Kapitelfreigabe in approvals.yml')
                    elif chapter.get('status') != 'approved' and chapter_record and chapter_record.get('action') == 'granted':
                        errors.append(f'{chapter["id"]}: Kapitelstatus nicht approved, aber Freigabe in approvals.yml nicht zurückgenommen')
                    for section in chapter['sections']:
                        head = section_file(base, section)[0]
                        record = latest.get(('section', section['id']))
                        if head.get('status') == 'approved':
                            manuscript = section_file(base, section)[3]
                            digest = hashlib.sha256(manuscript.encode('utf-8')).hexdigest()
                            if not record or record.get('action') != 'granted':
                                errors.append(f'{section["path"]}: approved ohne letzte gültige Abschnittsfreigabe in approvals.yml')
                            elif record.get('note') != 'content_sha256=' + digest:
                                errors.append(f'{section["path"]}: Manuskript-Fingerabdruck weicht von der letzten Freigabe in approvals.yml ab; Ausweg: `render_view.py . approval-section {config["structure"]["chapters"].index(chapter) + 1}.{chapter["sections"].index(section) + 1}` zeigt „Geänderten Text neu abschließen“ (#563)')
                        elif record and record.get('action') == 'granted':
                            errors.append(f'{section["path"]}: Abschnittsfreigabe in approvals.yml nicht zurückgenommen')
                for _, item in matter_items(config):
                    head, _, _, manuscript = section_file(base, item)
                    record = latest.get(('matter', item['id']))
                    if head.get('status') == 'approved':
                        digest = hashlib.sha256(manuscript.encode('utf-8')).hexdigest()
                        if (head.get('approvals') or {}).get('section') is not True:
                            errors.append(f'{item["path"]}: Status approved ohne approvals.section=true')
                        if not record or record.get('action') != 'granted':
                            errors.append(f'{item["path"]}: freigegebener Vor-/Nachspann ohne letzte Freigabe in approvals.yml')
                        elif record.get('note') != 'content_sha256=' + digest:
                            errors.append(f'{item["path"]}: Manuskript-Fingerabdruck weicht von der letzten Freigabe ab; Ausweg: `render_view.py . approval-section {item["id"][4:]}` zeigt „Geänderten Text neu abschließen“ (#595)')
                    elif record and record.get('action') == 'granted':
                        errors.append(f'{item["path"]}: Freigabe des Vor-/Nachspanns in approvals.yml nicht zurückgenommen')
                    elif record and record.get('action') == 'granted':
                        errors.append(f'{item["path"]}: Freigabe des Vor-/Nachspanns in approvals.yml nicht zurückgenommen')
    return errors


MANUSCRIPT_MARK = '\n## Manuskript\n'


def checkout_warnings(project_dir):
    """Hinweis ohne Fehler (#572): ausgecheckte Abschnitte, die sich seit dem Checkout geändert haben (z. B. direkt auf GitHub)."""
    base = Path(project_dir)
    if not (base / 'checkouts.yml').is_file():
        return []
    try:
        import checkout
        from render_view import load
        root, config = load(base)
        return [f'{line} (Sperre umgangen? python3 scripts/checkout.py . verify)'
                for line in checkout.verify_text(checkout.verify(root, config)).splitlines()]
    except Exception:   # noqa: BLE001 - Hinweise dürfen die Prüfung nie stören
        return []


def manuscript_warnings(project_dir):
    """Hinweise ohne Fehler (#435): weitere `## `-Überschrift nach `## Manuskript` ist meist eine Arbeitsnotiz,
    die sonst mit ins Buch käme (Grundregel „Ohne Vorrede und Nachwort“). Datei und Zeile."""
    base = Path(project_dir)
    try:
        config = yaml.safe_load((base / 'ghostwriter.yml').read_text(encoding='utf-8')) or {}
    except (OSError, yaml.YAMLError):
        return []   # Lesefehler meldet check_project
    paths = [s['path'] for ch in (config.get('structure') or {}).get('chapters') or [] for s in ch.get('sections') or []]
    paths += [item['path'] for _, item in matter_items(config) if item.get('path')]
    out = []
    for rel in paths:
        path = base / rel
        if not path.is_file():
            continue
        text = path.read_text(encoding='utf-8')
        at = text.find(MANUSCRIPT_MARK)
        if at < 0:
            continue
        line = text[:at + 1].count('\n') + 1   # Zeile von „## Manuskript“
        fence = False
        for offset, row in enumerate(text[at + 1:].split('\n')[1:], start=1):
            if row.lstrip().startswith(('```', '~~~')):
                fence = not fence
            elif not fence and row.startswith('## ') and row[3:].strip():
                out.append(f'{rel}:{line + offset}: Überschrift „{row.strip()}“ nach „## Manuskript“ – '
                           'Arbeitsnotiz? Sie käme so mit ins Buch.')
    return out


def image_warnings(project_dir):
    """Hinweise ohne Fehler (#684): Bildordner ohne bekannten Abschnitt bzw. Teil."""
    try:
        import images
        from render_view import load
        root, config = load(Path(project_dir))
        return [f'{folder}: Bildordner ohne Abschnitt' + (f' – gehört vermutlich zu {hint}: python3 scripts/images.py . relink {folder} {hint}' if hint
                else ' – zuordnen mit python3 scripts/images.py . relink <ordner> <abschnitt>')
                for folder, hint in images.orphan_folders(root, config)]
    except Exception:   # noqa: BLE001 - Hinweise dürfen die Prüfung nie stören
        return []


def main(argv):
    if len(argv) < 2:
        print(__doc__)
        return 2
    verify_authority = '--verify-authority' in argv[1:]
    project_dirs = [a for a in argv[1:] if a != '--verify-authority']
    if not project_dirs:
        return 2
    failed = False
    for project_dir in project_dirs:
        errors = check_project(project_dir)
        if verify_authority and not errors:
            import approval_authority
            try:
                approval_authority.verify(project_dir)
            except approval_authority.AuthorityError:
                errors.append('Persönlicher Inhaltsnachweis fehlt oder ist ungültig')
        if errors:
            failed = True
            print(f'✗ {project_dir}: {len(errors)} Fehler')
            for e in errors:
                print(f'  - {e}')
        else:
            print(f'✓ {project_dir}' + (' (persönlicher Inhaltsnachweis geprüft)' if verify_authority else ' (Strukturprüfung; Freigabeperson nicht geprüft)'))
        for w in manuscript_warnings(project_dir):
            print(f'  ⚠ {w}')
        for w in checkout_warnings(project_dir):
            print(f'  ⚠ {w}')
        for w in image_warnings(project_dir):
            print(f'  ⚠ {w}')
    return 1 if failed else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
