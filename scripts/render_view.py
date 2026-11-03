#!/usr/bin/env python3
"""Referenzumsetzung der Befüllungsregeln aus templates/ui/BEFUELLUNG.md.

Aufruf:
  python scripts/render_view.py <projektordner> project            [--text] [--repo owner/name] [--branch main]
  python scripts/render_view.py <projektordner> chapter <kapitel>  [--text] ...
  python scripts/render_view.py <projektordner> section <kapitel>.<abschnitt> [--text] ...
  python scripts/render_view.py <projektordner> project-edit | project-settings | chapter-create | chapter-reorder | edition-create [--text]
  python scripts/render_view.py <projektordner> chapter-edit | section-create | section-reorder <kapitel> [--text]

Ohne --text wird der Widget-Code ausgegeben: Ladezeile für ghostwriter-ui (fester
Commit aus templates/ui/ghostwriter-ui.yml) plus GW.render mit den Daten. Mit
--text kommt die Textfassung für Chats ohne Widgets. Gezeigt wird höchstens der
Text eines Abschnitts.
"""
import argparse
import json
import subprocess
import re
import sys
import unicodedata
from decimal import Decimal
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
UI_CONFIG = ROOT / 'templates' / 'ui' / 'ghostwriter-ui.yml'
FRONTMATTER = re.compile(r'\A---\n(.*?)\n---\n', re.S)
MARKERS = {
    'anekdote': re.compile(r'\[PLATZHALTER-ANEKDOTE\b'),
    'quelle': re.compile(r'\[QUELLE PRÜFEN\b'),
    'medizin': re.compile(r'\[MEDIZIN PRÜFEN\b'),
    'recht': re.compile(r'\[RECHT PRÜFEN\b'),
}
MARKER_LABEL = {'anekdote': 'Platzhalter-Anekdote', 'quelle': 'Quelle prüfen',
                'medizin': 'Medizin prüfen', 'recht': 'Recht prüfen'}
MARKER_TEXT = re.compile(r'\[(PLATZHALTER-ANEKDOTE|QUELLE PRÜFEN|MEDIZIN PRÜFEN|RECHT PRÜFEN)(?::\s*([^\]]*))?\]')
KIND = {'PLATZHALTER-ANEKDOTE': 'anekdote', 'QUELLE PRÜFEN': 'quelle', 'MEDIZIN PRÜFEN': 'medizin', 'RECHT PRÜFEN': 'recht'}


# ---------- Daten lesen ----------

def load(project):
    base = Path(project)
    config = yaml.safe_load((base / 'ghostwriter.yml').read_text(encoding='utf-8'))
    return base, config


def section_file(base, section):
    text = (base / section['path']).read_text(encoding='utf-8')
    m = FRONTMATTER.match(text)
    head = yaml.safe_load(m.group(1))
    body = text[m.end():]
    def part(name):
        mm = re.search(rf'(?m)^## {re.escape(name)}\n\n(.*?)(?=^## |\Z)', body, re.S)
        return mm.group(1).strip() if mm else ''
    manuscript = body.split('\n## Manuskript\n', 1)[1].strip() if '\n## Manuskript\n' in body else ''
    goal, summary = part('Ziel des Abschnitts'), part('Kurzbeschreibung')
    return head, ('' if goal == 'Offen.' else goal), ('' if summary == 'Offen.' else summary), manuscript


# Vor- und Nachspann (#57, #58): Teile außerhalb der Kapitel, je eine Datei unter matter/.
# Art → (Bereich, Vorgabetitel, Datei). Bereich: front = vor Kapitel 1, back = nach dem letzten Kapitel.
# Die Reihenfolge hier ist die Reihenfolge im Buch.
MATTER = {
    'dedication': ('front', 'Widmung', 'widmung.md'),
    'foreword': ('front', 'Vorwort', 'vorwort.md'),
    'prologue': ('front', 'Prolog', 'prolog.md'),
    'epilogue': ('back', 'Epilog', 'epilog.md'),
    'afterword': ('back', 'Nachwort', 'nachwort.md'),
    'glossary': ('back', 'Glossar', 'glossar.md'),
    'acknowledgments': ('back', 'Danksagung', 'danksagung.md'),
}
MATTER_AREAS = {'front': 'front_matter', 'back': 'back_matter'}
MATTER_HINTS = {'dedication': 'eigene Seite nach der Titelei, ohne Überschrift',
                'foreword': 'vor dem Prolog bzw. Kapitel 1; optional von einer anderen Person',
                'prologue': 'erzählerischer Einstieg vor Kapitel 1',
                'epilogue': 'Ausklang nach dem letzten Kapitel',
                'afterword': 'Nachbetrachtung nach dem Epilog',
                'glossary': 'Begriffe zum Nachschlagen, alphabetisch',
                'acknowledgments': 'Dank am Ende des Buchs'}
# Ghostwriting für Prolog, Epilog, Vorwort und Nachwort; Widmung und Danksagung schreibt der Autor
# selbst, das Glossar besteht aus Einträgen, die er aufnimmt (Vorschläge und Recherche je Begriff erlaubt)
MATTER_GHOSTWRITING = {'prologue', 'epilogue', 'foreword', 'afterword'}
MATTER_RESEARCH = MATTER_GHOSTWRITING | {'glossary'}
# Vorwort und Nachwort: optional Verfasser (byline) und Ort/Datum (place_date) am Ende (#58)
MATTER_SIGNED = {'foreword', 'afterword'}

GLOSSARY_ENTRY = re.compile(r'^[-*]\s+(?:\*\*(.+?)\*\*|([^:]+?))\s*:\s+(.*)$')


def glossary_entries(text):
    """(Einleitung, [(Begriff, Erklärung)]) aus dem Manuskript des Glossars: Einträge als Liste
    `- Begriff: Erklärung` (auch `- **Begriff**: …`); eingerückte Folgezeilen gehören zur Erklärung."""
    intro, entries = [], []
    for line in (text or '').splitlines():
        m = GLOSSARY_ENTRY.match(line)
        if m:
            entries.append([(m.group(1) or m.group(2)).strip(), m.group(3).strip()])
        elif entries and line.startswith((' ', '\t')) and line.strip():
            entries[-1][1] += ' ' + line.strip()
        elif not entries or line.strip():
            intro.append(line)
    return '\n'.join(intro).strip(), [tuple(e) for e in entries]


# Verweis aufs Glossar im Manuskript (#107): [Begriff]{.glossar} oder [Beugungsform]{.glossar term="Begriff"}
GLOSSARY_REF = re.compile(r'\[([^\]\[]+)\]\{\.glossar(?:\s+term="([^"]+)")?\}')


def glossary_ref_term(m):
    """Begriff eines Verweises: term="…" oder der Text selbst."""
    return (m.group(2) or m.group(1)).strip()


def glossary_anchor(term):
    return 'gl-' + tag_slug(term)


def german_key(term):
    """Sortierschlüssel nach DIN 5007-1: Umlaute wie Grundbuchstaben (ä = a), ß = ss,
    Groß/klein egal; bei Gleichstand ohne Umlaut vor mit Umlaut, dann klein vor groß."""
    import unicodedata
    folded = term.casefold().replace('ß', 'ss')
    base = ''.join(c for c in unicodedata.normalize('NFD', folded) if not unicodedata.combining(c))
    return (base, folded, term.swapcase())


def glossary_duplicates(entries):
    seen, dup = set(), []
    for term, _ in entries:
        k = term.casefold()
        if k in seen and term not in dup:
            dup.append(term)
        seen.add(k)
    return dup


def matter_id(kind):
    return 'mat-' + MATTER[kind][2][:-3]


def matter_items(config, area=None):
    """Teile von Vor- und Nachspann in Buchreihenfolge: [(bereich, eintrag)]; area = 'front' oder 'back'."""
    st = config.get('structure') or {}
    out = []
    for a, key in MATTER_AREAS.items():
        if area in (None, a):
            out += [(a, item) for item in st.get(key) or []]
    return out


def find_matter(config, key):
    """Eintrag nach Art (dedication), ID (mat-widmung), Dateiname (widmung) oder Titel (Widmung)."""
    k = (key or '').strip().lower()
    for _, item in matter_items(config):
        if k in (item['kind'], item['id'], item['id'][4:], item['title'].lower(), MATTER[item['kind']][1].lower()):
            return item
    return None


# Figuren (#53): characters/<char-id>.md, Liste in ghostwriter.yml → characters
ROLE_DE = {'main': 'Hauptfigur', 'supporting': 'Nebenfigur', 'minor': 'Randfigur'}


def character_items(config):
    return list((config or {}).get('characters') or [])


def character_file(base, item):
    """(Kopf, Beschreibung, Notizen) einer Figurendatei; Platzhalter der Vorlage = leer."""
    text = (base / item['path']).read_text(encoding='utf-8')
    m = FRONTMATTER.match(text)
    head = yaml.safe_load(m.group(1)) if m else {}
    body = text[m.end():] if m else text
    def part(name):
        mm = re.search(rf'(?ms)^## {name}\n(.*?)(?=^## |\Z)', body)
        v = mm.group(1).strip() if mm else ''
        return '' if v.startswith('<') else v
    return head or {}, part('Beschreibung'), part('Notizen')


def find_character(config, key):
    k = (key or '').strip().casefold()
    for item in character_items(config):
        if k in (item['id'], item['id'][5:], item['name'].casefold()):
            return item
    return None


def character_usage(base, config):
    """{char-id: ['1.2', 'Prolog', …]} – wo die Figuren laut Abschnitts- bzw. Teilkopf vorkommen."""
    out = {}
    for ci, ch in enumerate(config['structure']['chapters'], start=1):
        for si, s in enumerate(ch['sections'], start=1):
            for cid in section_file(base, s)[0].get('characters') or []:
                out.setdefault(cid, []).append(f'{ci}.{si}')
    for _, item in matter_items(config):
        for cid in section_file(base, item)[0].get('characters') or []:
            out.setdefault(cid, []).append(item['title'])
    return out


def cost_entries(base, path):
    if not path.is_file():
        return []
    return yaml.safe_load(path.read_text(encoding='utf-8')).get('entries', [])


def section_costs(base, chapter, section):
    return cost_entries(base, base / chapter['path'] / 'costs' / f'{section["id"]}.yml')


def counted(entries):
    """Nur KI-API-Kosten über das Backend zählen (#13); alte Chat-Schätzungen nicht."""
    return [e for e in entries if e.get('source', 'backend_api') == 'backend_api']


def total(entries):
    """(Summe als Decimal oder None, enthält Schätzung)"""
    entries = counted(entries)
    amounts = [Decimal(str(e['cost_amount'])) for e in entries if e['cost_amount'] is not None]
    estimated = any(e['cost_status'] == 'estimated' for e in entries)
    return (sum(amounts) if amounts else None), estimated


def money(amount, estimated, currency='€'):
    if amount is None:
        return '–'
    s = f'{amount:.2f}'.replace('.', ',')
    return ('≈ ' if estimated else '') + f'{s} {currency}'


def cost_hint(base_hint, amount, estimated):
    if amount is None:
        return 'Keine KI-API-Kosten erfasst (Arbeit im Chat über ein Abo kostet nichts zusätzlich)'
    return base_hint + (', enthält geschätzte Kosten' if estimated else '')


def combine(parts):
    amounts = [a for a, _ in parts if a is not None]
    return (sum(amounts) if amounts else None), any(e for _, e in parts)


def marker_counts(text):
    return {k: len(p.findall(text)) for k, p in MARKERS.items()}


def tag_slug(text):
    t = text.translate(str.maketrans({'ä': 'ae', 'ö': 'oe', 'ü': 'ue', 'Ä': 'ae', 'Ö': 'oe', 'Ü': 'ue', 'ß': 'ss'}))
    t = unicodedata.normalize('NFKD', t).encode('ascii', 'ignore').decode()
    return re.sub(r'[^a-z0-9]+', '-', t.lower()).strip('-')


# ---------- Vorlage befüllen ----------

UI_URL = 'https://cdn.jsdelivr.net/gh/{repo}@{ref}/dist/gw.min.js'  # von jsDelivr verkleinert
UI = {'repo': 'ploeffler/ghostwriter-ui', 'ref': None}


def fill(template, values, blocks=None):
    """Widget-Code: Ladezeile für ghostwriter-ui und GW.render mit den Daten.
    Maskieren, Wiederholblöcke und data-gw-if erledigt gw.js im Chat."""
    data = dict(values)
    data.update(blocks or {})
    if UI.get('head'):
        data['HEAD_SHA'] = UI['head']  # gelesener Stand; gw.js schickt ihn als expected_head_sha zurück
    payload = json.dumps(data, ensure_ascii=False, separators=(',', ':')).replace('</', '<\\/')
    url = UI_URL.format(repo=UI['repo'], ref=UI['ref'])
    return (f'<div id="gw"></div>\n<script src="{url}"></script>\n'
            f'<script>GW.render({json.dumps(template[:-5])},{payload})</script>\n')


# ---------- Textfassung (Chats ohne Widgets) ----------

STATUS_DE = {'planned': 'geplant', 'in_progress': 'in Arbeit', 'ready_for_assembly': 'bereit zum Zusammenführen',
             'assembly': 'wird zusammengeführt', 'review': 'Durchsicht', 'ready_for_approval': 'bereit zur Freigabe',
             'approved': 'freigegeben', 'research': 'Recherche', 'brainstorming': 'Ideensammlung',
             'ready_to_write': 'bereit zum Schreiben', 'writing': 'Schreiben', 'revision': 'Überarbeitung',
             'fact_check': 'Faktencheck'}
STATUS_ICON = {'planned': '⚪', 'research': '🔎', 'brainstorming': '💡', 'ready_to_write': '🟦', 'writing': '✏️',
               'in_progress': '✏️', 'revision': '🔁', 'fact_check': '🔍', 'review': '🔍', 'ready_for_assembly': '🟡',
               'assembly': '🧩', 'ready_for_approval': '🟡', 'approved': '✅'}
MARKER_ICON = {'anekdote': '💬', 'quelle': '📚', 'medizin': '🩺', 'recht': '⚖️'}
MARKER_LEGEND = 'Marker: 💬 Anekdote · 📚 Quelle prüfen · 🩺 Medizin prüfen · ⚖️ Recht prüfen'


def status_text(st):
    return f'{STATUS_ICON.get(st, "•")} {STATUS_DE.get(st, st)}'


def menu(items, intro='Was möchtest du tun? Antworte mit dem Kürzel'):
    """items: [(kürzel, text)] -> Aktionszeile mit Kürzeln als Inline-Code."""
    return f'**{intro}:**  \n' + ' · '.join(f'`{k}` {t}' for k, t in items)


def field_table(rows):
    out = ['| Feld | Aktueller Wert |', '|---|---|']
    for label, value in rows:
        v = str(value).replace('\n', ' ').replace('|', '\\|') if value not in ('', None) else '*(leer)*'
        out.append(f'| {label} | {v} |')
    return out


FORM_HINT = 'Antworte mit den Feldern, die sich ändern sollen, je Zeile `Feld: neuer Wert`. `X` bricht ab.'


# ---------- Ansichten ----------

def credit():
    """Hinweis „Entwickelt mit Unterstützung von Claude (Anthropic)“ aus templates/branding.yml (nie im Buch)."""
    try:
        c = (yaml.safe_load((ROOT / 'templates' / 'branding.yml').read_text(encoding='utf-8')) or {}).get('credit') or {}
    except OSError:
        c = {}
    return c.get('text', ''), c.get('url', '')


def matter_rows(base, config):
    rows = []
    for area, item in matter_items(config):
        head, _, _, ms = section_file(base, item)
        rows.append({'MATTER_ID': item['id'], 'MATTER_KIND': item['kind'], 'MATTER_AREA': area,
                     'MATTER_TITLE': item['title'], 'MATTER_STATUS': head['status'],
                     'MATTER_MARKERS': str(sum(marker_counts(ms).values()))})
    return rows


def matter_view(base, config, args):
    """Vor- und Nachspann (#57, #58): ohne Teil die Liste (Vorlage vor-nachspann), sonst das Formular
    eines Teils (Vorlage teil-bearbeiten); mit --text die Textfassung."""
    p = config['project']
    short = p.get('title_short') or p.get('title') or p.get('working_title') or ''
    if not args.where:   # Übersicht „Vor- und Nachspann“: vorhandene Teile und was sich anlegen lässt
        have = {i['kind']: i for _, i in matter_items(config)}
        if not args.text:
            parts = []
            for kind, (area, title, _) in MATTER.items():
                i = have.get(kind)
                parts.append({'PART_KIND': kind, 'PART_TITLE': i['title'] if i else title, 'PART_AREA': area,
                              'PART_ID': i['id'] if i else '', 'PART_STATUS': section_file(base, i)[0]['status'] if i else '',
                              'PART_HINT': MATTER_HINTS[kind]})
            return fill('vor-nachspann.html', {'PROJECT_TITLE_SHORT': short}, {'PARTS': parts})
        lines = ['### 📜 Vor- und Nachspann', '', '| Teil | Bereich | Stand |', '|---|---|---|']
        for kind, (area, title, _) in MATTER.items():
            i = have.get(kind)
            state = status_text(section_file(base, i)[0]['status']) if i else '*nicht angelegt*'
            lines.append(f'| {i["title"] if i else title} | {"Vorspann" if area == "front" else "Nachspann"} | {state} |')
        lines += ['', 'Nur freigegebene Teile kommen in eine Auflage. Widmung und Danksagung schreibst du selbst; '
                  'für Vorwort, Prolog, Epilog und Nachwort gibt es Recherche und Ghostwriting wie bei Abschnitten, '
                  'fürs Glossar Vorschläge und Recherche je Begriff.', '', '---']
        items = [(i['title'], 'öffnen') for _, i in matter_items(config)]
        items += [(f'+ {title}', 'anlegen') for kind, (_, title, _) in MATTER.items() if kind not in have]
        items.append(('Ü', 'Zur Übersicht'))
        return '\n'.join(lines + [menu(items)]) + '\n'
    item = find_matter(config, args.where)
    if not item:
        have = ', '.join(i['title'] for _, i in matter_items(config)) or 'keine'
        return (f'Im Buch gibt es „{args.where}“ noch nicht (vorhanden: {have}). '
                f'Anlegen mit `python scripts/matter.py . add <art>` (START.md, „Vor- und Nachspann“).\n')
    head, goal, _, ms = section_file(base, item)
    kind = item['kind']
    area = 'Vorspann' if MATTER[kind][0] == 'front' else 'Nachspann'
    markers = [(KIND[m.group(1)], (m.group(2) or '').strip() or '–') for m in MARKER_TEXT.finditer(ms)]
    yn = lambda v: '✅ ja' if v else '— nein'
    goal_m = re.search(r'(?ms)^## Ziel\n\n(.*?)(?=^## |\Z)', (base / item['path']).read_text(encoding='utf-8'))
    goal = goal_m.group(1).strip() if goal_m else ''
    if goal.startswith('<'):
        goal = ''
    if not args.text:
        n = len(markers)
        intro, entries = glossary_entries('' if ms in EMPTY_MANUSCRIPT else ms) if kind == 'glossary' else ('', [])
        values = {'PROJECT_TITLE_SHORT': short, 'MATTER_ID': item['id'], 'MATTER_KIND': kind, 'MATTER_TITLE': item['title'],
                  'MATTER_AREA_TEXT': area, 'MATTER_STATUS': head['status'], 'MATTER_GOAL': goal,
                  'MATTER_MANUSCRIPT': '' if kind == 'glossary' or ms in EMPTY_MANUSCRIPT else ms,
                  'MARKER_COUNT_TEXT': 'keine offenen Marker' if not n else f'{n} offene{"r" if n == 1 else ""} Marker',
                  'APPROVAL_WRITING': str(bool(head['approvals']['writing'])).lower(),
                  'APPROVAL_SECTION': str(bool(head['approvals']['section'])).lower(),
                  'SIGNED': '1' if kind in MATTER_SIGNED else '', 'BYLINE': head.get('byline') or '',
                  'PLACE_DATE': head.get('place_date') or '', 'GLOSSARY': '1' if kind == 'glossary' else '',
                  'GLOSSARY_INTRO': intro, 'RESEARCH': '1' if kind in MATTER_RESEARCH else '',
                  'GHOSTWRITING': '1' if kind in MATTER_GHOSTWRITING else '',
                  'PERSONAL_NOTE': ('Persönlicher Teil: Den Text schreibst du selbst; Vorschläge gibt es nur, wenn du '
                                    'ausdrücklich darum bittest.') if kind in ('dedication', 'acknowledgments') else ''}
        blocks = {'MARKERS': [{'MARKER_TYPE': k, 'MARKER_LABEL': MARKER_LABEL[k], 'MARKER_TEXT': v} for k, v in markers],
                  'GLOSSARY_ENTRIES': [{'G_TERM': t, 'G_TEXT': e} for t, e in sorted(entries, key=lambda x: german_key(x[0]))]}
        return fill('teil-bearbeiten.html', values, blocks)
    lines = [f'### 📜 {item["title"]}', f'{area} · {status_text(head["status"])}', '',
             '| | |', '|---|---|', f'| Ziel | {goal or "*offen*"} |',
             f'| Schreibfreigabe | {yn(head["approvals"]["writing"])} |',
             f'| Freigegeben | {yn(head["approvals"]["section"])} |']
    if kind in MATTER_SIGNED:
        lines += [f'| Verfasser | {head.get("byline") or "*der Autor des Buchs*"} |',
                  f'| Ort, Datum | {head.get("place_date") or "*keine Angabe*"} |']
    lines.append('')
    if markers:
        lines += [f'**Offene Marker ({len(markers)})**'] + [f'- {MARKER_ICON[k]} {MARKER_LABEL[k]}: {v}' for k, v in markers] + ['']
    if kind == 'glossary':
        intro, entries = glossary_entries('' if ms in EMPTY_MANUSCRIPT else ms)
        dup = glossary_duplicates(entries)
        lines += ['---', '']
        if intro:
            lines += [intro, '']
        if entries:
            lines += [f'**{len(entries)} Begriff{"e" if len(entries) != 1 else ""}** (im Buch alphabetisch)', '',
                      '| Begriff | Erklärung |', '|---|---|']
            lines += [f'| {t}{" ⚠️ doppelt" if t in dup else ""} | {e} |' for t, e in sorted(entries, key=lambda x: german_key(x[0]))]
        else:
            lines += ['*Noch keine Begriffe.*']
        lines += ['', '---']
        items = [('+ Begriff: Erklärung', 'aufnehmen'), ('Begriff: neue Erklärung', 'ändern'), ('- Begriff', 'entfernen'),
                 ('VB', 'Begriffe aus dem freigegebenen Text vorschlagen'), ('F', 'Titel, Ziel und Einleitung')]
    else:
        lines += ['---', '', ms or '*Noch kein Text.*', '', '---']
        items = [('T', 'Text ändern (geänderten Text schicken)'),
                 ('F', 'Titel, Ziel, Verfasser, Ort und Datum' if kind in MATTER_SIGNED else 'Titel und Ziel')]
    items += [('FS', 'Schreibfreigabe zurücknehmen' if head['approvals']['writing'] else 'Schreiben freigeben'),
              ('FA', 'Freigabe zurücknehmen' if head['approvals']['section'] else f'{item["title"]} freigeben')]
    if kind in MATTER_RESEARCH:
        items.append(('RS', 'Recherche je Begriff' if kind == 'glossary' else 'Recherche sofort'))
    if kind in MATTER_GHOSTWRITING:
        items.append(('GS', 'Ghostwriting sofort'))
    items.append(('Ü', 'Zur Übersicht'))
    lines += [menu(items)]
    return '\n'.join(lines) + '\n'


def images_view(base, config, args):
    """Illustrationen eines Abschnitts bzw. Teils (#54): Liste mit Status; Textfassung bzw. Vorlage bilder."""
    import images
    target, folder = images.find_target(config, args.where)
    imgs = [(iid, v) for iid, v in images.all_images(base, config).items() if v[0].get('section_id') == target['id']]
    head = section_file(base, target)[0]
    used = set(images.refs_in(section_file(base, target)[3]))
    names = {c['id']: c['name'] for c in character_items(config)}
    style = images.settings(config)['style']
    rows = [{'I_ID': iid, 'I_CAPTION': v[0].get('caption', ''), 'I_STATE': v[0].get('status', 'draft'),
             'I_SOURCE': {'chat': 'im Chat erzeugt', 'copy': 'Auftrag kopiert', 'own': 'eigenes Bild'}.get(v[0].get('source'), ''),
             'I_SIZE': f'{v[0]["width_px"]} × {v[0]["height_px"]} px' if v[0].get('width_px') else '',
             'I_IN_TEXT': '1' if iid in used else ''} for iid, v in imgs]
    chars = [names.get(c, c) for c in head.get('characters') or []]
    if args.text:
        lines = [f'### 🖼️ Bilder · {target["title"]}', '',
                 f'Bildstil des Buchs: {style or "*noch keiner (images.style)*"} · Figuren im Abschnitt: {", ".join(chars) or "–"}', '']
        if rows:
            lines += ['| Bild | Bildunterschrift | Stand | Herkunft | im Text |', '|---|---|---|---|---|']
            lines += [f'| `{r["I_ID"]}` | {r["I_CAPTION"] or "–"} | {"✅ freigegeben" if r["I_STATE"] == "approved" else "✏️ Entwurf"} | '
                      f'{r["I_SOURCE"]} | {"ja" if r["I_IN_TEXT"] else "nein"} |' for r in rows]
        else:
            lines += ['*Noch keine Bilder.*']
        lines += ['', '---', menu([('BI', 'Bild-Auftrag: Szene beschreiben (`Szene: …`)'), ('BH', 'Bild hochladen (Datei anhängen)')]
                                 + [(f'FB {r["I_ID"]}', 'freigeben' if r['I_STATE'] != 'approved' else 'Freigabe zurücknehmen') for r in rows]
                                 + [('Ü', 'Zur Übersicht')])]
        return '\n'.join(lines) + '\n'
    p = config['project']
    values = {'PROJECT_TITLE_SHORT': p.get('title_short') or p.get('title') or '', 'TARGET_ID': target['id'],
              'TARGET_TITLE': target['title'], 'IMAGE_STYLE': style, 'TARGET_CHARACTERS': ', '.join(chars)}
    return fill('bilder.html', values, {'IMAGES': rows})


def characters_view(base, config, args):
    """Figuren (#53): ohne Angabe die Liste (Vorlage figuren), sonst eine Figur (Vorlage figur-bearbeiten)."""
    p = config['project']
    short = p.get('title_short') or p.get('title') or p.get('working_title') or ''
    items = character_items(config)
    used = character_usage(base, config)
    names = {i['id']: i['name'] for i in items}
    if not args.where:
        rows = []
        for i in items:
            head = character_file(base, i)[0]
            rows.append({'C_ID': i['id'], 'C_NAME': i['name'], 'C_ROLE': ROLE_DE.get(head.get('role'), ''),
                         'C_SHORT': head.get('short', ''), 'C_USED': ', '.join(used.get(i['id'], [])) or '–'})
        if args.text:
            lines = ['### 🎭 Figuren', '']
            if rows:
                lines += ['| Figur | Rolle | Kurz | kommt vor in |', '|---|---|---|---|']
                lines += [f'| {r["C_NAME"]} | {r["C_ROLE"]} | {r["C_SHORT"] or "–"} | {r["C_USED"]} |' for r in rows]
            else:
                lines += ['*Noch keine Figuren.*']
            lines += ['', 'Figuren sind Arbeitsgrundlage für Brainstorming und Ghostwriting; sie kommen nicht ins Buch.', '', '---']
            lines += [menu([(r['C_NAME'], 'öffnen') for r in rows] + [('+ Name', 'neue Figur anlegen (optional `Rolle: Nebenfigur`)'),
                                                                     ('Ü', 'Zur Übersicht')])]
            return '\n'.join(lines) + '\n'
        return fill('figuren.html', {'PROJECT_TITLE_SHORT': short}, {'CHARACTERS': rows})
    item = find_character(config, args.where)
    if not item:
        return f'Eine Figur „{args.where}“ gibt es nicht (vorhanden: {", ".join(names.values()) or "keine"}).\n'
    head, desc, notes = character_file(base, item)
    rel = [{'R_TO': r['to'], 'R_NAME': names.get(r['to'], r['to']), 'R_KIND': r['kind']} for r in head.get('relations') or []]
    if args.text:
        rows = [('Rolle', ROLE_DE.get(head.get('role'), '')), ('Kurz', head.get('short')), ('Alter', head.get('age')),
                ('Aussehen', head.get('appearance')), ('Eigenschaften', ', '.join(head.get('traits') or [])),
                ('Sprechweise', head.get('voice')), ('Bildbeschreibung', head.get('visual')),
                ('Beziehungen', '; '.join(f'{r["R_KIND"]} von {r["R_NAME"]}' for r in rel)),
                ('kommt vor in', ', '.join(used.get(item['id'], [])))]
        lines = [f'### 🎭 {item["name"]}', '', '| | |', '|---|---|'] + [f'| {k} | {v or "–"} |' for k, v in rows]
        lines += ['', '**Beschreibung**', '', desc or '*offen*']
        if notes:
            lines += ['', '**Notizen**', '', notes]
        lines += ['', '---', 'Antworte mit `Feld: neuer Wert` (z. B. `Alter: 78`, `Eigenschaften: geduldig, brummig`, '
                  '`Beziehung: Besitzer von Strolchi`, `Beschreibung: …`). `X` bricht ab, `FI` zeigt alle Figuren.']
        return '\n'.join(lines) + '\n'
    values = {'PROJECT_TITLE_SHORT': short, 'CHARACTER_ID': item['id'], 'CHARACTER_NAME': item['name'],
              'CHARACTER_ROLE': head.get('role', 'main'), 'CHARACTER_SHORT': head.get('short', ''),
              'CHARACTER_AGE': head.get('age', ''), 'CHARACTER_APPEARANCE': head.get('appearance', ''),
              'CHARACTER_TRAITS': ', '.join(head.get('traits') or []), 'CHARACTER_VOICE': head.get('voice', ''),
              'CHARACTER_VISUAL': head.get('visual', ''), 'CHARACTER_DESCRIPTION': desc, 'CHARACTER_NOTES': notes,
              'CHARACTER_USED': ', '.join(used.get(item['id'], [])) or 'noch nirgends'}
    others = [{'O_ID': i['id'], 'O_NAME': i['name']} for i in items if i['id'] != item['id']]
    return fill('figur-bearbeiten.html', values, {'RELATIONS': rel, 'OTHERS': others})


def limit_state(base, config, args):
    """(state, text) aus --limits (JSON von limits.py check --json) bzw. ohne Angabe aus den Kosten des Monats (#62)."""
    path = getattr(args, 'limits', None)
    if path:
        data = json.loads(Path(path).read_text(encoding='utf-8'))
        return data.get('state') or 'ok', data.get('text') or ''
    import limits
    return limits.summary(limits.evaluate(base, config))


def limit_summary(base, config):
    import limits
    rows = limits.evaluate(base, config)
    return ('; '.join(r['text'] for r in rows) + '.') if rows else 'Keine Limits eingestellt.'


def project_view(base, config, args):
    p = config['project']
    chapters = config['structure']['chapters']
    rows, parts = [], []
    for i, ch in enumerate(chapters, start=1):
        ch_amount, ch_est = combine([total(section_costs(base, ch, s)) for s in ch['sections']])
        parts.append((ch_amount, ch_est))
        rows.append({'CHAPTER_NUMBER': i, 'CHAPTER_TITLE': ch['title'], 'CHAPTER_STATUS': ch['status'],
                     'CHAPTER_COST': money(ch_amount, ch_est),
                     'CHAPTER_COST_HINT': cost_hint('Summe der Abschnittskosten', ch_amount, ch_est),
                     'CHAPTER_ID': ch['id']})
    parts.append(total(cost_entries(base, base / 'costs' / 'project.yml')))
    amount, est = combine(parts)
    edition = p['current_edition']
    values = {
        'PROJECT_TITLE': p['title'] or p['working_title'], 'PROJECT_TITLE_SHORT': p['title_short'] or p['title'] or p['working_title'],
        'PROJECT_AUTHOR': p['author'], 'PROJECT_DESCRIPTION_SHORT': p['description_short'], 'PROJECT_DESCRIPTION': p['description'],
        'PROJECT_COST': money(amount, est), 'PROJECT_COST_HINT': cost_hint('Zusätzliche KI-API-Kosten über das GhostWriter-Backend', amount, est),
        'PROJECT_EDITION_TEXT': f'Auflage {edition}' if edition else 'noch keine Auflage',
    }
    values['CREDIT_TEXT'], values['CREDIT_URL'] = credit()
    changes = load_changes(args)
    if changes:
        values.update({'PENDING_COUNT': len(changes['commits']), 'PENDING_TEXT': changes_text(changes),
                       'PENDING_PR': changes['pull_request']})
    lib_count = len((json.loads(Path(args.library).read_text(encoding='utf-8')).get('books') or [])) if getattr(args, 'library', None) else 0
    if lib_count >= 2:
        values['LIBRARY_COUNT'] = lib_count
    n_chars = len(character_items(config))
    if n_chars:   # Figuren (#53): Knopf „Figuren (n)“
        values['CHARACTER_COUNT'] = n_chars
    upd = load_upstream(args)
    if upd:
        values.update({'UPDATE_BEHIND': upd['behind'], 'UPDATE_TEXT': update_text(upd)})
    lim_state, lim_text = limit_state(base, config, args)
    if lim_state != 'ok':   # Limitwarnung (#62)
        values.update({'LIMIT_STATE': lim_state, 'LIMIT_TEXT': lim_text})
    matter = matter_rows(base, config)
    front = [m for m in matter if m['MATTER_AREA'] == 'front']
    back = [m for m in matter if m['MATTER_AREA'] == 'back']
    def matter_line(ms, label):
        return f'**{label}:** ' + ' · '.join(f'{m["MATTER_TITLE"]} {STATUS_ICON.get(m["MATTER_STATUS"], "")}'.strip() for m in ms)
    if args.text:
        lines = [f'### 📘 {values["PROJECT_TITLE"] or "Noch ohne Titel"}',
                 f'**{values["PROJECT_EDITION_TEXT"]}** · Autor: {values["PROJECT_AUTHOR"] or "noch offen"} · KI-API-Kosten: **{values["PROJECT_COST"]}**', '']
        if changes:
            lines += [f'> ⏳ **{values["PENDING_TEXT"]} noch nicht übernommen** (Pull Request #{changes["pull_request"]}) · `M` übernehmen', '']
        if lim_state != 'ok':
            lines += [f'> {"⏸" if lim_state == "pause" else "⚠️"} **{lim_text}** · `E` Einstellungen', '']
        if upd:
            lines += [f'> 🔄 **GhostWriter-Update:** {values["UPDATE_TEXT"]} · `U` einspielen', '']
        if values['PROJECT_DESCRIPTION_SHORT']:
            lines += [f'> {values["PROJECT_DESCRIPTION_SHORT"]}', '']
        if values['PROJECT_DESCRIPTION']:
            lines += [values['PROJECT_DESCRIPTION'], '']
        if front:
            lines += [matter_line(front, 'Vorspann'), '']
        if rows:
            # Letzte Spalte: Kürzel zum Bearbeiten des Kapitels (wie der Bearbeiten-Knopf der Kapitelansicht).
            lines += ['| # | Kapitel | Kosten | Status | |', '|--:|---|--:|---|:-:|']
            lines += [f'| {r["CHAPTER_NUMBER"]} | {r["CHAPTER_TITLE"]} | {r["CHAPTER_COST"]} | {status_text(r["CHAPTER_STATUS"])} | `✎ B{r["CHAPTER_NUMBER"]}` |' for r in rows]
        else:
            lines += ['*Noch keine Kapitel.*']
        if back:
            lines += ['', matter_line(back, 'Nachspann')]
        lines += ['', '---']
        wf = config.get('workflow') or {}
        if rows:
            # Ein Kürzel je Kapitel; das zuletzt bearbeitete Kapitel ist fett.
            chips = [(f'**`📖 {i}`**' if ch['id'] == wf.get('current_chapter_id') else f'`📖 {i}`')
                     for i, ch in enumerate(chapters, start=1)]
            lines += ['**Kapitel öffnen:**  ', ' '.join(chips), '', '---']
        items = []
        for ci, ch in enumerate(chapters, start=1):
            for si, sec in enumerate(ch['sections'], start=1):
                if sec['id'] == wf.get('current_section_id'):
                    items.append((f'{ci}.{si}', 'öffnen (zuletzt bearbeitet)'))
        if changes:
            items.append(('M', 'Änderungen übernehmen'))
        if upd:
            items.append(('U', 'Update einspielen'))
        if lib_count >= 2:
            items.append(('L', f'Bücherregal ({lib_count} Bücher)'))
        items += [(m['MATTER_TITLE'], 'öffnen') for m in front + back]
        items += [('D', 'KI-Dienste'), ('P', 'Projektdaten bearbeiten'), ('N', 'Neues Kapitel'), ('R', 'Kapitelreihenfolge'),
                  ('V', 'Vor- und Nachspann'), ('FI', f'Figuren ({n_chars})' if n_chars else 'Figuren'),
                  ('A', 'Neue Auflage'), ('E', 'Einstellungen')]
        lines += [menu(items)]
        if values.get('CREDIT_TEXT'):
            lines += ['', f'<sub>{values["CREDIT_TEXT"]}</sub>']
        return '\n'.join(lines) + '\n'
    blocks = {'CHAPTERS': rows}
    if front:
        blocks['MATTER_FRONT'] = front
    if back:
        blocks['MATTER_BACK'] = back
    return fill('projektuebersicht.html', values, blocks)


def chapter_view(base, config, args, cnum):
    p = config['project']
    ch = config['structure']['chapters'][cnum - 1]
    readme = (base / ch['path'] / 'README.md').read_text(encoding='utf-8')
    sub = re.search(r'(?m)^\*([^*].*)\*$', readme)
    rows, parts, counts_total, approved = [], [], 0, 0
    for si, s in enumerate(ch['sections'], start=1):
        head, _, _, ms = section_file(base, s)
        counts = marker_counts(ms)
        counts_total += sum(counts.values())
        approved += head['status'] == 'approved'
        a, e = total(section_costs(base, ch, s))
        parts.append((a, e))
        rows.append({'SECTION_ID': s['id'], 'SECTION_NUMBER': f'{cnum}.{si}', 'SECTION_TITLE': s['title'],
                     'SECTION_STATUS': head['status'], 'SECTION_COST': money(a, e),
                     'MARKERS_ANEKDOTE': counts['anekdote'], 'MARKERS_QUELLE': counts['quelle'],
                     'MARKERS_MEDIZIN': counts['medizin'], 'MARKERS_RECHT': counts['recht']})
    amount, est = combine(parts)
    n = len(ch['sections'])
    _, ch_summary, ch_goal = chapter_readme(base, ch)
    values = {'PROJECT_TITLE_SHORT': p['title_short'] or p['title'], 'CHAPTER_ID': ch['id'], 'CHAPTER_NUMBER': cnum,
              'CHAPTER_GOAL': ch_goal, 'CHAPTER_SUMMARY': ch_summary,
              'CHAPTER_TITLE': ch['title'], 'CHAPTER_SUBTITLE': sub.group(1) if sub else '',
              'SECTION_COUNT_TEXT': f'{n} Abschnitt' + ('' if n == 1 else 'e'),
              'MARKER_COUNT_TEXT': 'keine offenen Marker' if not counts_total else f'{counts_total} offene{"r" if counts_total == 1 else ""} Marker',
              'CHAPTER_COST': money(amount, est), 'CHAPTER_COST_HINT': cost_hint('Summe der Abschnittskosten', amount, est),
              'APPROVED_COUNT_TEXT': f'{approved} von {n}',
              'CHAPTER_APPROVABLE': 'true' if ch['status'] == 'ready_for_approval' and n and approved == n else ''}
    if args.text:
        def marks(r):
            parts = [f'{MARKER_ICON[k]} {r["MARKERS_" + k.upper()]}' for k in MARKER_ICON if r['MARKERS_' + k.upper()]]
            return ' '.join(parts) or '–'
        lines = [f'### 📖 Kapitel {cnum} · {ch["title"]}']
        if values['CHAPTER_SUBTITLE']:
            lines += [f'*{values["CHAPTER_SUBTITLE"]}*']
        lines += ['', f'**Ziel des Kapitels:** {ch_goal or "*noch offen*"}', '',
                  f'**Kurzbeschreibung:** {ch_summary or "*noch offen*"} · `Z` ändern, Kapitelrecherche']
        lines += ['', f'{values["SECTION_COUNT_TEXT"]} · ✅ {values["APPROVED_COUNT_TEXT"]} freigegeben · {values["MARKER_COUNT_TEXT"]} · Kosten **{values["CHAPTER_COST"]}**', '']
        if rows:
            lines += ['| # | Abschnitt | Marker | Kosten | Status |', '|--:|---|---|--:|---|']
            lines += [f'| {r["SECTION_NUMBER"]} | {r["SECTION_TITLE"]} | {marks(r)} | {r["SECTION_COST"]} | {status_text(r["SECTION_STATUS"])} |' for r in rows]
            if counts_total:
                lines += ['', f'<sub>{MARKER_LEGEND}</sub>']
        else:
            lines += ['*Noch keine Abschnitte.*']
        lines += ['', '---']
        items = [(f'{cnum}.1' + (f'–{cnum}.{n}' if n > 1 else ''), 'Abschnitt öffnen')] if rows else []
        if values['CHAPTER_APPROVABLE']:
            items.append(('FK', 'Kapitel freigeben'))
        items += [('B', 'Kapitel bearbeiten'), ('Z', 'Ziel, Kurzbeschreibung, Kapitelrecherche'), ('N', 'Neuer Abschnitt'),
                  ('R', 'Reihenfolge'), ('Ü', 'Übersicht')]
        lines += [menu(items)]
        return '\n'.join(lines) + '\n'
    return fill('kapitelansicht.html', values, {'SECTIONS': rows})


def section_view(base, config, args, cnum, snum):
    p = config['project']
    ch = config['structure']['chapters'][cnum - 1]
    secs = ch['sections']
    s = secs[snum - 1]
    head, goal, summary, ms = section_file(base, s)
    markers = [{'MARKER_TYPE': KIND[m.group(1)], 'MARKER_LABEL': MARKER_LABEL[KIND[m.group(1)]],
                'MARKER_TEXT': (m.group(2) or '').strip() or '–'} for m in MARKER_TEXT.finditer(ms)]
    a, e = total(section_costs(base, ch, s))
    def nav(k):
        if 1 <= k <= len(secs):
            return secs[k - 1]['id'], f'Abschnitt {cnum}.{k} „{secs[k - 1]["title"]}“ bearbeiten'
        return '', ''
    prev_id, prev_text = nav(snum - 1)
    next_id, next_text = nav(snum + 1)
    n = len(markers)
    values = {'PROJECT_TITLE_SHORT': p['title_short'] or p['title'], 'CHAPTER_ID': ch['id'], 'CHAPTER_NUMBER': cnum,
              'SECTION_ID': s['id'], 'SECTION_NUMBER': f'{cnum}.{snum}', 'SECTION_TITLE': s['title'],
              'SECTION_STATUS': head['status'], 'SECTION_COST': money(a, e),
              'SECTION_COST_HINT': cost_hint('Summe der Kosteneinträge', a, e),
              'SECTION_GOAL': goal, 'SECTION_SUMMARY': summary, 'SECTION_MANUSCRIPT': ms,
              'MARKER_COUNT_TEXT': 'keine offenen Marker' if not n else f'{n} offene{"r" if n == 1 else ""} Marker',
              'FACT_CHECK': head['fact_check'], 'APPROVAL_WRITING': str(head['approvals']['writing']).lower(),
              'APPROVAL_SECTION': str(head['approvals']['section']).lower(),
              'PREV_SECTION_ID': prev_id, 'PREV_SECTION_PROMPT': prev_text,
              'NEXT_SECTION_ID': next_id, 'NEXT_SECTION_PROMPT': next_text}
    chars = character_items(config)
    in_section = head.get('characters') or []
    if chars:   # Figuren (#53): Auswahl im Abschnittsformular
        values['CHARACTERS_ENABLED'] = '1'
    if args.text:
        yn = lambda v: '✅ ja' if v else '— nein'
        lines = [f'### ✏️ {cnum}.{snum} · {s["title"]}',
                 f'Kapitel {cnum} · {status_text(head["status"])} · Kosten **{values["SECTION_COST"]}**', '',
                 '| | |', '|---|---|',
                 f'| Ziel | {goal or "*offen*"} |', f'| Kurzbeschreibung | {summary or "*offen*"} |',
                 f'| Faktencheck | {FC_TEXT.get(head["fact_check"], head["fact_check"])} |',
                 f'| Schreibfreigabe | {yn(head["approvals"]["writing"])} |', f'| Abschnitt freigegeben | {yn(head["approvals"]["section"])} |']
        if chars:
            names = {c['id']: c['name'] for c in chars}
            lines.append(f'| Figuren | {", ".join(names.get(c, c) for c in in_section) or "–"} |')
        lines.append('')
        if markers:
            lines += [f'**Offene Marker ({n})**'] + [f'- {MARKER_ICON[m["MARKER_TYPE"]]} {m["MARKER_LABEL"]}: {m["MARKER_TEXT"]}' for m in markers] + ['']
        else:
            lines += ['Keine offenen Marker.', '']
        lines += ['---', '', ms, '', '---']
        items = [('T', 'Text ändern (geänderten Text schicken)'), ('F', 'Ziel, Kurzbeschreibung, Faktencheck'
                                                                  + (', Figuren' if chars else '')),
                 ('FS', 'Schreibfreigabe zurücknehmen' if head['approvals']['writing'] else 'Schreiben freigeben'),
                 ('FA', 'Abschnittsfreigabe zurücknehmen' if head['approvals']['section'] else 'Abschnitt freigeben'),
                 ('RS', 'Recherche sofort'), ('GS', 'Ghostwriting sofort'), ('BI', 'Bilder')]
        if prev_id:
            items.append((f'{cnum}.{snum - 1}', '← vorheriger'))
        if next_id:
            items.append((f'{cnum}.{snum + 1}', 'nächster →'))
        items.append(('K', 'Zum Kapitel'))
        lines += [menu(items)]
        return '\n'.join(lines) + '\n'
    blocks = {'MARKERS': markers}
    if chars:
        blocks['ALL_CHARACTERS'] = [{'C_ID': c['id'], 'C_NAME': c['name'], 'C_ON': '1' if c['id'] in in_section else ''}
                                    for c in chars]
    return fill('abschnitt-bearbeiten.html', values, blocks)


def project_values(config):
    p = config['project']
    title = p['title'] or p['working_title'] or ''
    return {'PROJECT_TITLE': title, 'PROJECT_TITLE_SHORT': p['title_short'] or '', 'PROJECT_AUTHOR': p['author'] or '',
            'PROJECT_DESCRIPTION_SHORT': p['description_short'] or '', 'PROJECT_DESCRIPTION': p['description'] or ''}


def project_edit_view(base, config, args):
    values = project_values(config)
    if args.text:
        return '\n'.join(['### 📝 Projektdaten bearbeiten', ''] + field_table([
            ('Titel', values['PROJECT_TITLE']), ('Kurztitel', values['PROJECT_TITLE_SHORT']), ('Autor', values['PROJECT_AUTHOR']),
            ('Kurzbeschreibung', values['PROJECT_DESCRIPTION_SHORT']), ('Beschreibung', values['PROJECT_DESCRIPTION'])])
            + ['', FORM_HINT]) + '\n'
    return fill('projektdaten-bearbeiten.html', values)


def chapter_create_view(base, config, args):
    chapters = config['structure']['chapters']
    if not chapters:
        labels = ['Als erstes Kapitel']
    else:
        labels = ['Am Anfang (vor Kapitel 1)']
        labels += [f'Nach Kapitel {i} „{ch["title"]}“' for i, ch in enumerate(chapters[:-1], start=1)]
        labels += [f'Am Ende (nach Kapitel {len(chapters)} „{chapters[-1]["title"]}“)']
    rows = positions(labels)
    if args.text:
        return '\n'.join(['### ➕ Neues Kapitel anlegen', '', 'Schicke je Zeile `Titel: …` (Pflicht), `Kurzbeschreibung: …`, `Ziel: …` und `Position: Nummer`.', '',
                           '**Positionen**'] + [f'`{i}` {l}' + (' *(Vorgabe)*' if r['POSITION_SELECTED'] else '') + '  ' for i, (l, r) in enumerate(zip(labels, rows))]
                          + ['', '`X` bricht ab.']) + '\n'
    return fill('kapitel-anlegen.html', {}, {'POSITIONS': rows})


def edition_create_view(base, config, args):
    import datetime
    p = config['project']
    wf_path = base / 'workflow.yml' if (base / 'workflow.yml').is_file() else ROOT / 'workflow.yml'
    workflow = yaml.safe_load(wf_path.read_text(encoding='utf-8'))
    br = workflow['book_releases']
    n = (p['current_edition'] or 0) + 1
    short = p['title_short'] or p['title'] or p['working_title'] or ''
    chapters = config['structure']['chapters']
    approved = sum(ch['status'] == 'approved' for ch in chapters)
    if not chapters:
        warn = 'Das Buch hat noch keine Kapitel.'
    elif approved < len(chapters):
        warn = (f'Bisher {"ist" if approved == 1 else "sind"} {approved} von {len(chapters)} Kapiteln freigegeben; '
                'nur freigegebene Kapitel kommen in die Auflage.')
    else:
        warn = ''
    # Was den Bau der Auflage verhindert (scripts/assemble.py check): kein freigegebenes
    # Kapitel, offene Marker, Lücken; dazu ein fehlender Titel (Name und Tag der Auflage)
    from assemble import book_parts, problems
    blockers = [x for x in problems(book_parts(base, config), config) if not x.startswith(('Kein Kapitel', 'Das Buch hat noch keinen Titel'))]
    markers = sum(x.startswith('Offener Marker') for x in blockers)
    parts = []
    if not short:
        parts.append('das Buch hat noch keinen Titel')
    if not approved:
        parts.append('noch kein Kapitel ist freigegeben')
    if markers:
        parts.append(f'{markers} offene Marker im freigegebenen Text')
    if len(blockers) > markers:
        parts.append('freigegebene Kapitel mit nicht freigegebenen Abschnitten')
    if parts:
        warn = (warn + ' ' if warn else '') + ('So kann die Auflage nicht gebaut werden: ' + ', '.join(parts[:-1])
                                              + (' und ' if len(parts) > 1 else '') + parts[-1] + '. Bitte zuerst klären.')
    if not short:
        short = 'Ohne Titel'
    values = {'EDITION_NUMBER': n, 'EDITION_NAME': br['name_pattern'].format(title_short=short, edition=n),
              'EDITION_TAG': br['tag_pattern'].format(title_short_slug=tag_slug(short), edition=n),
              'EDITION_DATE_DEFAULT': datetime.date.today().isoformat(), 'APPROVAL_WARNING_TEXT': warn}
    chosen = (config.get('typesetting') or {}).get('formats') or br['assets']   # Ausgabeoptionen (#68)
    short = {'pdf_print': 'Druck-PDF', 'cover': 'Umschlag'}
    formats = [{'FORMAT_LABEL': short.get(a, a.upper())} for a in ['pdf', 'pdf_print', 'cover', 'epub', 'docx'] if a in chosen]
    if args.text:
        return '\n'.join([f'### 📚 Neue Auflage erzeugen · Auflage {n}', '', '| | |', '|---|---|', f'| Name | {values["EDITION_NAME"]} |',
                           f'| Tag | `{values["EDITION_TAG"]}` |', f'| Formate | {", ".join(f["FORMAT_LABEL"] for f in formats)} |',
                           f'| Erscheinungsdatum | {values["EDITION_DATE_DEFAULT"]} *(Vorschlag)* |']
                          + (['', f'> ⚠️ {warn}'] if warn else [])
                          + ['', 'Schicke `Datum: JJJJ-MM-TT` und optional `Anmerkungen: …`. `OK` übernimmt den Vorschlag, `X` bricht ab.']) + '\n'
    return fill('auflage-erzeugen.html', values, {'FORMATS': formats})


def load_upstream(args):
    """Update-Stand aus --upstream (JSON): behind, upstream, version, installed. Nichts, wenn nicht dahinter."""
    if not getattr(args, 'upstream', None):
        return None
    data = json.loads(Path(args.upstream).read_text(encoding='utf-8'))
    return data if int(data.get('behind') or 0) > 0 else None


def update_text(upd):
    n = int(upd['behind'])
    text = f'{n} Commit{"" if n == 1 else "s"} hinter {upd.get("upstream") or "ploeffler/GhostWriter:main"}'
    if upd.get('version') and upd.get('version') != upd.get('installed'):
        text += f' · Version {upd["version"]} verfügbar' + (f' (installiert {upd["installed"]})' if upd.get('installed') else '')
    return text


def load_changes(args):
    """Offene Änderungen aus --changes (JSON): pull_request, book_branch, work_branch,
    commits [{sha, message, date}], älteste zuerst. Der Assistent liest sie aus GitHub."""
    if not getattr(args, 'changes', None):
        return None
    data = json.loads(Path(args.changes).read_text(encoding='utf-8'))
    # Automatische Commits (Übersichtsdatei, Updates) sind keine Änderung des Benutzers und zählen nicht mit.
    auto = ('GhostWriter-Aktion: index.build', 'GhostWriter-Aktion: update')
    data['commits'] = [c for c in data.get('commits') or [] if not any(a in c.get('message', '') for a in auto)]
    return data if data['commits'] else None


def changes_text(changes):
    n = len(changes['commits'])
    return '1 Änderung' if n == 1 else f'{n} Änderungen'


def change_date(value):
    import datetime
    try:
        return datetime.datetime.fromisoformat(str(value).replace('Z', '+00:00')).strftime('%d.%m.%Y, %H:%M')
    except ValueError:
        return str(value or '')


def changes_merge_view(base, config, args):
    changes = load_changes(args)
    if not changes:
        msg = 'Es gibt keine offenen Änderungen.'
        return msg + '\n' if args.text else f'<p>{msg}</p>\n'
    rows = [{'CHANGE_MESSAGE': c['message'].splitlines()[0], 'CHANGE_DATE': change_date(c.get('date')),
             'CHANGE_SHA': c['sha'][:7]} for c in changes['commits']]
    values = {'PENDING_TEXT': changes_text(changes), 'PENDING_PR': changes['pull_request'],
              'BOOK_BRANCH': changes['book_branch'], 'WORK_BRANCH': changes['work_branch']}
    if args.text:
        lines = ['### 🔀 Änderungen übernehmen', '',
                 f'In `{values["BOOK_BRANCH"]}` übernehmen: {values["PENDING_TEXT"]} aus `{values["WORK_BRANCH"]}` '
                 f'(Pull Request #{values["PENDING_PR"]}).', '',
                 '| # | Änderung | Datum | Commit |', '|--:|---|---|---|']
        lines += [f'| {i} | {r["CHANGE_MESSAGE"]} | {r["CHANGE_DATE"]} | `{r["CHANGE_SHA"]}` |' for i, r in enumerate(rows, start=1)]
        lines += ['', 'Danach gehören die Änderungen zum Buch; rückgängig machen geht nur mit einer neuen Änderung.', '',
                  '---', '`OK` übernimmt · `X` bricht ab']
        return '\n'.join(lines) + '\n'
    return fill('aenderungen-uebernehmen.html', values, {'CHANGES': rows})


EMPTY_MANUSCRIPT = ('', 'Noch nicht begonnen.')


def run_count(base, ch, sid, kind):
    folder = base / ch['path'] / kind / sid
    return len(list(folder.glob('*.md'))) if folder.is_dir() else 0


def approval_view(base, config, args, kind):
    """Bestätigung einer Freigabe (writing, section, chapter); --revoke nimmt sie zurück."""
    chapters = config['structure']['chapters']
    revoke = bool(getattr(args, 'revoke', False))
    checks = []
    def add(state, text):
        checks.append({'CHECK_STATE': state, 'CHECK_TEXT': text})
    if kind == 'image':   # Illustration (#54): Freigabe des Bilds
        import images
        hit = images.all_images(base, config).get(args.where or '')
        if not hit:
            raise SystemExit(f'Bild {args.where} nicht gefunden')
        meta = hit[0]
        target_id, label = meta['id'], f'Bild „{meta.get("caption") or meta["id"]}“'
        approved = meta.get('status') == 'approved'
        if revoke:
            title, button = 'Bildfreigabe zurücknehmen', 'Zurücknehmen'
            if not approved:
                add('block', 'Das Bild ist nicht freigegeben.')
            effect = 'Das Bild wird wieder Entwurf; steht es in freigegebenem Text, verhindert das die nächste Auflage.'
        else:
            title, button = 'Bild freigeben', 'Freigeben'
            if approved:
                add('block', 'Das Bild ist bereits freigegeben.')
            if not hit[1].is_file():
                add('block', 'Die Bilddatei fehlt.')
            w = meta.get('width_px')
            add('ok' if w and w >= 1500 else 'warn', f'{w} px breit.' if w else 'Größe unbekannt.')
            add('ok' if meta.get('caption') else 'warn', 'Bildunterschrift vorhanden.' if meta.get('caption') else 'Keine Bildunterschrift.')
            add('ok' if meta.get('alt') else 'warn', 'Alternativtext vorhanden.' if meta.get('alt') else 'Kein Alternativtext (EPUB).')
            if meta.get('ai_generated'):
                add('ok', 'KI-erzeugt; der Bildnachweis im Impressum nennt das.' if (config.get('images') or {}).get('credit_in_imprint', True)
                    else 'KI-erzeugt; der Bildnachweis im Impressum ist ausgeschaltet.')
            effect = 'Das Bild wird „freigegeben“ und kommt an seiner Stelle im Text in die nächste Auflage.'
    elif kind == 'chapter':
        cnum, ch = chapter_number(config, args.where)
        target_id, label = ch['id'], f'Kapitel {cnum} „{ch["title"]}“'
        heads = [section_file(base, s)[0] for s in ch['sections']]
        open_ = sum(h['status'] != 'approved' for h in heads)
        if revoke:
            title, button = 'Kapitelfreigabe zurücknehmen', 'Zurücknehmen'
            if ch['status'] != 'approved':
                add('block', 'Das Kapitel ist nicht freigegeben.')
            effect = 'Das Kapitel wechselt zu „in Arbeit“; die Abschnittsfreigaben bleiben bestehen.'
        else:
            title, button = 'Kapitel freigeben', 'Freigeben'
            if ch['status'] == 'approved':
                add('block', 'Das Kapitel ist bereits freigegeben.')
            if open_:
                add('block', f'{open_} von {len(heads)} Abschnitten sind noch nicht freigegeben.')
            else:
                add('ok', f'Alle {len(heads)} Abschnitte sind freigegeben.')
            if ch['status'] not in ('ready_for_approval', 'approved'):
                add('block', f'Das Kapitel steht auf „{STATUS_DE.get(ch["status"], ch["status"])}“, nicht auf „bereit zur Freigabe“ '
                             '(erst zusammenführen und durchsehen).')
            effect = 'Das Kapitel wird „freigegeben“. Du bestätigst damit das zusammengeführte Kapitel in diesem Stand.'
    else:
        item = None if re.fullmatch(r'\d+\.\d+', args.where or '') else find_matter(config, args.where)
        if item:   # Vor- oder Nachspann (#57): Schreibfreigabe und Freigabe des Teils wie bei einem Abschnitt
            sec, ch, c, s_ = item, {'status': '', 'path': ''}, 0, 0
            head, goal, summary, ms = section_file(base, item)
            target_id, label = item['id'], f'{item["title"]} ({"Vorspann" if MATTER[item["kind"]][0] == "front" else "Nachspann"})'
            if kind == 'section':
                kind = 'matter'
        else:
            c, s_ = (int(x) for x in args.where.split('.'))
            ch = chapters[c - 1]
            sec = ch['sections'][s_ - 1]
            head, goal, summary, ms = section_file(base, sec)
            target_id, label = sec['id'], f'Abschnitt {c}.{s_} „{sec["title"]}“'
        ap = head['approvals']
        if kind == 'writing' and revoke:
            title, button = 'Schreibfreigabe zurücknehmen', 'Zurücknehmen'
            if not ap['writing']:
                add('block', 'Die Schreibfreigabe ist nicht erteilt.')
            if ap['section']:
                add('block', f'{item["title"]} ist freigegeben; zuerst diese Freigabe zurücknehmen.' if item else
                    'Der Abschnitt ist freigegeben; zuerst die Abschnittsfreigabe zurücknehmen.')
            effect = 'Die Schreibfreigabe wird zurückgenommen; das Manuskript bleibt, wie es ist, darf aber erst nach einer neuen Freigabe weiter geschrieben werden.'
        elif kind == 'writing' and item:
            title, button = 'Schreiben freigeben', 'Freigeben'
            if ap['writing']:
                add('block', 'Die Schreibfreigabe ist bereits erteilt.')
            if item['kind'] not in MATTER_GHOSTWRITING:
                add('ok', f'{MATTER[item["kind"]][1]}: Der Text kommt von dir; Ghostwriting nur auf ausdrücklichen Wunsch.')
            effect = 'Die Schreibfreigabe wird erteilt; danach darf der Text geschrieben werden.' + \
                (' Der Teil wechselt zu „Schreiben“.' if head['status'] in ('planned', 'research', 'brainstorming', 'ready_to_write') else '')
        elif kind == 'writing':
            title, button = 'Schreiben freigeben', 'Freigeben'
            if ap['writing']:
                add('block', 'Die Schreibfreigabe ist bereits erteilt.')
            add('ok' if goal else 'warn', 'Ziel des Abschnitts ist eingetragen.' if goal else 'Ziel des Abschnitts fehlt noch.')
            add('ok' if summary else 'warn', 'Kurzbeschreibung ist eingetragen.' if summary else 'Kurzbeschreibung fehlt noch.')
            for folder, name in (('research', 'Recherchelauf'), ('brainstorming', 'Brainstorminglauf')):
                k = run_count(base, ch, sec['id'], folder)
                add('ok' if k else 'warn', f'{k} {name}{"e" if k != 1 else ""} vorhanden.' if k else
                    f'Noch kein {name} (laut workflow.yml vor der Schreibfreigabe vorgesehen).')
            effect = 'Die Schreibfreigabe wird erteilt; danach darf das Manuskript geschrieben werden.' + \
                (' Der Abschnitt wechselt zu „Schreiben“.' if head['status'] in ('planned', 'research', 'brainstorming', 'ready_to_write') else '')
        elif revoke and item:
            title, button = 'Freigabe zurücknehmen', 'Zurücknehmen'
            if not ap['section']:
                add('block', f'{item["title"]} ist nicht freigegeben.')
            effect = f'Die Freigabe wird zurückgenommen; {item["title"]} wechselt zu „Überarbeitung“ und fehlt in der nächsten Auflage, bis du wieder freigibst.'
        elif item:
            title, button = f'{item["title"]} freigeben', 'Freigeben'
            if ap['section']:
                add('block', f'{item["title"]} ist bereits freigegeben.')
            if not ap['writing']:
                add('block', 'Die Schreibfreigabe fehlt.')
            if ms.strip() in EMPTY_MANUSCRIPT:
                add('block', 'Es gibt noch keinen Text.')
            else:
                add('ok', f'Text: {len(ms.split())} Wörter.')
            n = sum(marker_counts(ms).values())
            add('warn' if n else 'ok', f'{n} offene{"r" if n == 1 else ""} Marker; sie verhindern die Auflage.' if n else 'Keine offenen Marker.')
            if item['kind'] == 'glossary':
                entries = glossary_entries(ms)[1]
                dup = glossary_duplicates(entries)
                add('block' if dup else 'ok', f'Begriffe mehrfach eingetragen: {", ".join(dup)}.' if dup else
                    f'{len(entries)} Begriff{"e" if len(entries) != 1 else ""}, keiner doppelt.')
            effect = f'{item["title"]} wird „freigegeben“ und kommt in die nächste Auflage. Du bestätigst damit den Text in diesem Stand.'
        elif revoke:
            title, button = 'Abschnittsfreigabe zurücknehmen', 'Zurücknehmen'
            if not ap['section']:
                add('block', 'Der Abschnitt ist nicht freigegeben.')
            if ch['status'] == 'approved':
                add('warn', f'Damit wird auch die Freigabe von Kapitel {c} aufgehoben; es wechselt zu „in Arbeit“.')
            effect = 'Die Abschnittsfreigabe wird zurückgenommen; der Abschnitt wechselt zu „Überarbeitung“.'
        else:
            title, button = 'Abschnitt freigeben', 'Freigeben'
            if ap['section']:
                add('block', 'Der Abschnitt ist bereits freigegeben.')
            if not ap['writing']:
                add('block', 'Die Schreibfreigabe fehlt.')
            if ms.strip() in EMPTY_MANUSCRIPT:
                add('block', 'Es gibt noch kein Manuskript.')
            else:
                add('ok', f'Manuskript: {len(ms.split())} Wörter.')
            n = sum(marker_counts(ms).values())
            add('warn' if n else 'ok', f'{n} offene{"r" if n == 1 else ""} Marker; sie bleiben im freigegebenen Text.' if n else 'Keine offenen Marker.')
            if head['fact_check'] == 'requested':
                add('warn', 'Ein Faktencheck ist angefordert; ist er erledigt?')
            effect = 'Der Abschnitt wird „freigegeben“. Du bestätigst damit den Text, wie er im Abschnittsformular steht.'
    head_sha = UI.get('head', '')
    values = {'APPROVAL_KIND': kind, 'APPROVAL_REVOKE': 'true' if revoke else '', 'APPROVAL_TITLE': title,
              'APPROVAL_BUTTON': button, 'APPROVAL_EFFECT': effect, 'TARGET_ID': target_id, 'TARGET_LABEL': label,
              'HEAD_SHORT': head_sha[:7] or '–'}
    if args.text:
        icon = {'ok': '✅', 'warn': '⚠️', 'block': '⛔'}
        blocked = any(x['CHECK_STATE'] == 'block' for x in checks)
        lines = [f'### {"↩️" if revoke else "✅"} {title}', '', f'**{label}** · Stand `{values["HEAD_SHORT"]}`', '']
        if checks:
            lines += [f'- {icon[x["CHECK_STATE"]]} {x["CHECK_TEXT"]}' for x in checks] + ['']
        lines += [effect, '', '---',
                  'Bestätigen geht erst, wenn die ⛔-Punkte erledigt sind. `X` schließt.' if blocked else '`OK` bestätigt · `X` bricht ab']
        return '\n'.join(lines) + '\n'
    return fill('freigabe-bestaetigen.html', values, {'CHECKS': checks})


ROLE_INFO = [('default', 'Standard', 'gilt für alle Aufgaben, die unten nicht eigens belegt sind'),
             ('research', 'Recherche', 'braucht Internetrecherche'),
             ('brainstorming', 'Brainstorming', ''),
             ('writing', 'Schreiben', 'Sprachqualität im Deutschen, lange Texte'),
             ('revision', 'Überarbeiten', ''),
             ('fact_check', 'Faktencheck', 'am besten ein anderer Dienst als beim Schreiben'),
             ('queue_processing', 'Aufgaben-Warteschlange', 'Agent, der GitHub-Issues abarbeitet; Standard: manuell')]
WEB_TEXT = {'native': 'mit Websuche', 'via_tool': 'Websuche über Werkzeug', 'none': 'ohne Websuche'}
ACCESS_TEXT = {'app': 'Chat-App oder Website', 'api': 'API-Schlüssel', 'local': 'auf meinem Rechner', 'cli': 'Kommandozeile',
               'web': 'über die Websuche (kostenlos)', 'github': 'in GitHub zugewiesen'}


def access_options(s, group):
    """Mögliche Zugangsarten eines Dienstes; die erste ist die Vorgabe."""
    if group == 'agent':
        return ['github', 'api'] if s.get('api_key_secret') else ['github']
    if group == 'search':
        return ['web', 'api'] if s.get('kind') == 'scholarly_index' else ['api']
    if s.get('kind') == 'local':
        return ['local']
    acc = list(s.get('access') or [])
    return [a for a in ('app', 'api', 'cli') if a in acc] or ['api']


def secret_default(s):
    return s.get('api_key_secret') or (re.sub(r'[^A-Z0-9]+', '_', s['id'].upper()) + '_API_KEY')


def secrets_state(base):
    """Welche Secrets es im Repository gibt, laut ghostwriter-index.json (von der Action ermittelt)."""
    path = base / 'ghostwriter-index.json'
    try:
        return json.loads(path.read_text(encoding='utf-8')).get('secrets') or {}
    except (OSError, ValueError):
        return {}


def service_settings(s, group, cfg, present=None):
    opts = access_options(s, group)
    access = cfg.get('access') if cfg.get('access') in opts else opts[0]
    cost = cfg.get('monthly_cost')
    secret = cfg.get('api_key_secret') or secret_default(s)
    alt = s.get('api_key_alt') or ''
    present = present or {}
    state = 'ok' if present.get(secret) else 'alt' if alt and present.get(alt) else ('missing' if present.get(secret) is False else '')
    return {'SERVICE_ACCESS_OPTIONS': ','.join(opts), 'SERVICE_ACCESS': access,
            'SERVICE_SECRET': secret, 'SERVICE_SECRET_DEFAULT': secret_default(s), 'SERVICE_SECRET_ALT': alt,
            'SERVICE_KEY_URL': s.get('api_key_url') or s.get('url', ''), 'SERVICE_SECRET_STATE': state,
            'SERVICE_MODEL': cfg.get('model') or '', 'SERVICE_GITHUB': 'true' if cfg.get('github_connected') else '',
            'SERVICE_PLAN': cfg.get('plan') or '', 'SERVICE_COST': '' if cost is None else f'{cost:g}',
            'SERVICE_MEMO': cfg.get('note') or ''}


def providers_edit_view(base, config, args):
    """Formular „KI-Dienste“: vorhandene Dienste und Zuteilung je Aufgabe."""
    catalog = yaml.safe_load((ROOT / 'providers.yml').read_text(encoding='utf-8'))
    ap = config.get('ai_providers') or {}
    available = list(ap.get('available') or [])
    settings = ap.get('services') or {}
    present = secrets_state(base)
    def guide(s, group):
        setup = s.get('setup')
        if not setup:
            if group == 'search':
                setup = 'docs/DIENSTE-NUTZEN.md#recherchequellen'
            elif group == 'agent':
                setup = 'docs/DIENSTE-NUTZEN.md#agenten-für-die-aufgaben-warteschlange'
            elif s.get('kind') == 'local':
                setup = 'docs/DIENSTE-NUTZEN.md#weg-3-lokale-modelle-auf-deinem-rechner'
            elif s.get('kind') == 'llm' and 'app' in (s.get('access') or []):
                setup = 'docs/DIENSTE-NUTZEN.md#weg-2-ein-anderer-chat-dienst-auftrag-kopieren'
            else:
                setup = 'docs/DIENSTE-NUTZEN.md#weg-4-dienste-nur-mit-api-schlüssel'
        path, _, anchor = setup.partition('#')
        return f'https://github.com/{args.repo}/blob/{args.branch}/{path}' + (f'#{anchor}' if anchor else '')
    services = []
    for section, group in (('providers', 'llm'), ('search_tools', 'search'), ('queue_agents', 'agent')):
        for s in catalog.get(section) or []:
            if s['id'] == 'manual':
                continue
            if group == 'llm':
                roles = ','.join(s.get('roles') or [])
                note = ' · '.join(x for x in (s.get('hq', ''), WEB_TEXT.get(s.get('web_research'), ''), s.get('note', '')) if x and x != 'n/a')
            elif group == 'search':
                roles, note = 'search', s.get('note', '')
            else:
                roles, note = 'queue_processing', s.get('note', '')
            services.append({'SERVICE_ID': s['id'], 'SERVICE_NAME': s['name'], 'SERVICE_GROUP': group,
                             'SERVICE_ROLES': roles, 'SERVICE_NOTE': note, 'SERVICE_AVAILABLE': 'true' if s['id'] in available else '',
                             'SERVICE_GUIDE_URL': guide(s, group), 'SERVICE_WEBSITE_URL': s.get('url', ''),
                             **service_settings(s, group, settings.get(s['id']) or {}, present)})
    roles = []
    for rid, label, hint in ROLE_INFO:
        entry = ap.get(rid) or {}
        value = entry.get('agent', 'manual') if rid == 'queue_processing' else entry.get('provider', '')
        roles.append({'ROLE_ID': rid, 'ROLE_LABEL': label, 'ROLE_HINT': hint, 'ROLE_VALUE': value or ''})
    secrets_url = f'https://github.com/{args.repo}/settings/secrets/actions/new'
    if args.text:
        names = {s['SERVICE_ID']: s['SERVICE_NAME'] for s in services}
        names.update({'chat': 'Aktueller Chat', 'manual': 'manuell', '': 'wie Standard'})
        lines = ['### 🤖 KI-Dienste', '', '**Deine Dienste**', '']
        mine = [s for s in services if s['SERVICE_AVAILABLE']]
        def summary(s):
            parts = [ACCESS_TEXT[s['SERVICE_ACCESS']]]
            if s['SERVICE_ACCESS'] == 'api':
                st = {'ok': '✅ hinterlegt', 'alt': f'✅ über `{s["SERVICE_SECRET_ALT"]}`', 'missing': '⚠️ fehlt', '': 'Status unbekannt'}[s['SERVICE_SECRET_STATE']]
                parts.append(f'Secret `{s["SERVICE_SECRET"]}` ({st})')
            if s['SERVICE_GROUP'] == 'llm':
                parts.append(f'Modell: {s["SERVICE_MODEL"] or "Standard"}')
                if s['SERVICE_ACCESS'] == 'app':
                    parts.append('mit GitHub verbunden' if s['SERVICE_GITHUB'] else 'nicht mit GitHub verbunden')
            if s['SERVICE_PLAN']:
                parts.append(f'Tarif: {s["SERVICE_PLAN"]}')
            if s['SERVICE_COST']:
                parts.append(f'{money(Decimal(s["SERVICE_COST"]), False)} / Monat')
            if s['SERVICE_MEMO']:
                parts.append(s['SERVICE_MEMO'])
            return ' · '.join(parts)
        lines += [f'- `{s["SERVICE_ID"]}` {s["SERVICE_NAME"]}: {summary(s)}' for s in mine] or ['- *noch keine eingetragen; bis dahin macht alles der aktuelle Chat*']
        lines += ['', '| Aufgabe | Dienst |', '|---|---|']
        lines += [f'| {r["ROLE_LABEL"]} | {names.get(r["ROLE_VALUE"], r["ROLE_VALUE"])} |' for r in roles]
        lines += ['', '<details><summary>Weitere Dienste hinzufügen</summary>', '']
        lines += [f'- `{s["SERVICE_ID"]}` {s["SERVICE_NAME"]} · [Anleitung]({s["SERVICE_GUIDE_URL"]})'
                  + (f' · [Website]({s["SERVICE_WEBSITE_URL"]})' if s['SERVICE_WEBSITE_URL'] else '')
                  for s in services if not s['SERVICE_AVAILABLE']]
        lines += ['', '</details>', '', '---',
                  'Antworte je Zeile: `+ id` (Dienst habe ich), `- id` (habe ich nicht mehr), `Aufgabe: id` (zuteilen, z. B. `Recherche: perplexity`), '
                  '`id.Einstellung: Wert` mit Zugang, Modell, GitHub (ja/nein), Secret (Name des GitHub-Secrets), Tarif, Kosten (€ pro Monat) oder Notiz (z. B. `openai.Modell: gpt-5`). `X` bricht ab.',
                  '', f'🔑 API-Schlüssel nie hier in den Chat schreiben. Sie gehören als Secret in GitHub: [Secret anlegen]({secrets_url}).']
        return '\n'.join(lines) + '\n'
    connector = f'https://github.com/{args.repo}/blob/{args.branch}/docs/CONNECTOR-SETUP.md'
    keys_guide = f'https://github.com/{args.repo}/blob/{args.branch}/docs/DIENSTE-NUTZEN.md#api-schlüssel-als-github-secret'
    return fill('ki-dienste.html', {'CONNECTOR_GUIDE_URL': connector, 'SECRETS_URL': secrets_url, 'KEYS_GUIDE_URL': keys_guide},
                {'SERVICES': services, 'ROLES': roles})


# Buchsatz (typesetting): Vorgaben = Satz bis v0.6; Ausgabeoptionen (#68) ändern nur, was gesetzt ist
TYPESETTING_DEFAULT = {'page_size': 'a5', 'font': 'serif', 'font_size': 11, 'title_page': True,
                      'imprint': True, 'toc': True, 'toc_depth': 1,
                      'heading_font': 'same', 'margins': 'standard', 'line_spacing': 1.1, 'paragraph': 'indent',
                      'hyphenation': True, 'chapter_start': 'any', 'running_heads': 'sections',
                      'page_numbers': 'header', 'initials': False, 'formats': ['pdf', 'docx', 'epub'],
                      'glossary_marks': 'arrow'}
# Werte → deutsche Bezeichnung (Formular „Ausgabe“, Textfassung)
OUTPUT_LABELS = {
    'page_size': ('Seitenformat', {'a5': 'A5 (14,8 × 21 cm)', '12x19': '12 × 19 cm', '13.5x21.5': '13,5 × 21,5 cm', 'a4': 'A4'}),
    'font': ('Grundschrift', {'serif': 'Serifenschrift (Pagella)', 'sans': 'serifenlos (Heros)', 'pagella': 'Pagella',
                              'termes': 'Termes', 'bonum': 'Bonum', 'schola': 'Schola', 'heros': 'Heros', 'adventor': 'Adventor'}),
    'font_size': ('Schriftgröße', None),
    'heading_font': ('Überschriften', {'same': 'wie Grundschrift', 'serif': 'Serifenschrift', 'sans': 'serifenlos'}),
    'initials': ('Initialen am Kapitelanfang', None),
    'glossary_marks': ('Glossar-Verweise im Text', {'arrow': 'mit Pfeil (→ Begriff)', 'italic': 'kursiv', 'none': 'ohne Kennzeichnung'}),
    'margins': ('Ränder', {'standard': 'Standard', 'classic': 'klassisch (breit)', 'modern': 'modern (schmal)'}),
    'line_spacing': ('Zeilenabstand', None),
    'paragraph': ('Absätze', {'indent': 'mit Einzug', 'spacing': 'mit Abstand'}),
    'hyphenation': ('Silbentrennung', None),
    'chapter_start': ('Kapitelbeginn', {'any': 'nächste Seite', 'right': 'immer rechte Seite'}),
    'running_heads': ('Kolumnentitel', {'sections': 'Kapitel und Abschnitt', 'chapter': 'Kapiteltitel',
                                        'book': 'Buch- und Kapiteltitel', 'none': 'keine'}),
    'page_numbers': ('Seitenzahlen', {'header': 'oben außen', 'footer_center': 'unten Mitte', 'footer_outer': 'unten außen'}),
    'title_page': ('Titelseite', None), 'imprint': ('Impressum', None), 'toc': ('Inhaltsverzeichnis', None),
    'toc_depth': ('Verzeichnistiefe', {1: 'nur Kapitel', 2: 'Kapitel und Abschnitte'}),
    'formats': ('Formate einer Auflage', {'pdf': 'PDF (Bildschirm)', 'pdf_print': 'Druck-PDF (Innenteil)',
                                          'cover': 'Umschlag-PDF', 'docx': 'DOCX', 'epub': 'EPUB'}),
}
FIXED_RULES = [('ai_settings', 'hallucination_policy', 'Halluzinationen'), ('ai_settings', 'source_policy', 'Quellen'),
               ('ai_settings', 'uncertainty_policy', 'Unsicherheiten'), ('ai_settings', 'creativity', 'Kreativität'),
               ('ai_settings', 'web_research', 'Internetrecherche'),
               ('workflow', 'require_section_writing_approval', 'Schreibfreigabe je Abschnitt'),
               ('workflow', 'require_section_approval', 'Freigabe je Abschnitt'),
               ('workflow', 'require_chapter_approval', 'Freigabe je Kapitel')]
FIXED_TEXT = {'strict': 'strikt ausgeschlossen', 'required': 'Pflicht', 'explicit': 'ausdrücklich kennzeichnen',
              'balanced': 'ausgewogen', 'research': 'bei Rechercheaufträgen', True: 'Pflicht', False: 'aus'}
FC_TEXT = {'disabled': 'aus', 'optional': 'optional', 'requested': 'angefordert'}


def chapter_number(config, where):
    n = int(where)
    return n, config['structure']['chapters'][n - 1]


def chapter_readme(base, ch):
    path = base / ch['path'] / 'README.md'
    text = path.read_text(encoding='utf-8') if path.is_file() else ''
    sub = re.search(r'(?m)^\*([^*].*)\*$', text)
    def part(name):
        m = re.search(rf'(?m)^## {re.escape(name)}\n\n(.*?)(?=^## |\Z)', text, re.S)
        v = m.group(1).strip() if m else ''
        return '' if v == 'Offen.' else v
    return (sub.group(1) if sub else ''), part('Kurzbeschreibung'), part('Ziel des Kapitels')


def positions(labels):
    return [{'POSITION_LABEL': l, 'POSITION_SELECTED': 'selected' if i == len(labels) - 1 else ''} for i, l in enumerate(labels)]


def chapter_edit_view(base, config, args):
    n, ch = chapter_number(config, args.where)
    subtitle, summary, goal = chapter_readme(base, ch)
    values = {'CHAPTER_ID': ch['id'], 'CHAPTER_NUMBER': n, 'CHAPTER_TITLE': ch['title'], 'CHAPTER_SUBTITLE': subtitle,
              'CHAPTER_SUMMARY': summary, 'CHAPTER_GOAL': goal}
    if args.text:
        return '\n'.join([f'### 📝 Kapitel {n} bearbeiten', ''] + field_table([
            ('Titel', ch['title']), ('Untertitel', subtitle), ('Kurzbeschreibung', summary), ('Ziel', goal)]) + ['', FORM_HINT]) + '\n'
    return fill('kapitel-bearbeiten.html', values)


def section_create_view(base, config, args):
    n, ch = chapter_number(config, args.where)
    secs = ch['sections']
    if not secs:
        labels = ['Als erster Abschnitt']
    else:
        labels = [f'Am Anfang (vor {n}.1)']
        labels += [f'Nach {n}.{i} „{s["title"]}“' for i, s in enumerate(secs[:-1], start=1)]
        labels += [f'Am Ende (nach {n}.{len(secs)} „{secs[-1]["title"]}“)']
    fc = (config.get('workflow') or {}).get('fact_checking_default') or 'optional'
    if args.text:
        return '\n'.join([f'### ➕ Neuer Abschnitt in Kapitel {n}', '',
                           'Schicke je Zeile `Titel: …` (Pflicht), `Ziel: …`, `Kurzbeschreibung: …`, `Position: Nummer` '
                           f'und optional `Faktencheck: aus | optional | angefordert` (Vorgabe: {FC_TEXT[fc]}).', '', '**Positionen**']
                          + [f'`{i}` {l}' + (' *(Vorgabe)*' if i == len(labels) - 1 else '') + '  ' for i, l in enumerate(labels)]
                          + ['', '`X` bricht ab.']) + '\n'
    return fill('abschnitt-anlegen.html', {'CHAPTER_ID': ch['id'], 'CHAPTER_NUMBER': n, 'CHAPTER_TITLE': ch['title'],
                                           'FACT_CHECK_DEFAULT': fc}, {'POSITIONS': positions(labels)})


def reorder(args, kind, heading, items, chapter_id='', chapter_no=''):
    if args.text:
        return '\n'.join([f'### ↕️ {heading}', '', '| Jetzt | Titel |', '|--:|---|']
                          + [f'| `{i["ITEM_NUMBER"]}` | {i["ITEM_TITLE"]} |' for i in items]
                          + ['', 'Schicke die Nummern in der neuen Reihenfolge, z. B. `' + ', '.join(str(i['ITEM_NUMBER']) for i in (items[1::-1] + items[2:4] if len(items) > 1 else items)) + (', …' if len(items) > 4 else '') + '`. `X` bricht ab.']) + '\n'
    return fill('reihenfolge.html', {'REORDER_KIND': kind, 'REORDER_HEADING': heading, 'CHAPTER_ID': chapter_id,
                                     'CHAPTER_NUMBER': chapter_no}, {'ITEMS': items})


def chapter_reorder_view(base, config, args):
    items = [{'ITEM_ID': ch['id'], 'ITEM_NUMBER': i, 'ITEM_TITLE': ch['title']}
             for i, ch in enumerate(config['structure']['chapters'], start=1)]
    return reorder(args, 'chapter', 'Kapitelreihenfolge ändern', items)


def section_reorder_view(base, config, args):
    n, ch = chapter_number(config, args.where)
    items = [{'ITEM_ID': s['id'], 'ITEM_NUMBER': f'{n}.{i}', 'ITEM_TITLE': s['title']}
             for i, s in enumerate(ch['sections'], start=1)]
    return reorder(args, 'section', f'Abschnittsreihenfolge in Kapitel {n} ändern', items, ch['id'], n)


def update_info(base, config):
    """(automatisch ja/nein, Versionstext, Hinweis) aus ghostwriter.yml, Manifest und .ghostwriter/update.yml."""
    auto = (config.get('updates') or {}).get('auto') is not False
    def read_yaml(path):
        try:
            return yaml.safe_load(path.read_text(encoding='utf-8')) or {}
        except (OSError, yaml.YAMLError):
            return {}
    version = read_yaml(base / 'ghostwriter-manifest.yml').get('version') or read_yaml(ROOT / 'ghostwriter-manifest.yml').get('version')
    state = read_yaml(base / '.ghostwriter' / 'update.yml')
    text = f'Installiert: GhostWriter {version or "unbekannt"}'
    when = str(state.get('updated_at') or '')
    if re.match(r'\d{4}-\d{2}-\d{2}', when):
        text += f' · zuletzt aktualisiert am {when[8:10]}.{when[5:7]}.{when[:4]}'
    mig = state.get('migration') or {}
    if mig.get('to') is not None:
        text += f' · Daten auf Version {mig["to"]} umgestellt'
        if mig.get('changes'):
            text += ' (' + '; '.join(mig['changes'][:3]) + ('; …' if len(mig['changes']) > 3 else '') + ')'
    hint = ''
    if state.get('skipped_workflows'):
        hint = (f'{len(state["skipped_workflows"])} Workflow-Datei(en) wurden nicht aktualisiert; dafür braucht das '
                'Repository das Secret GHOSTWRITER_UPDATE_TOKEN (docs/UPDATES.md).')
    return auto, text, hint


def output_value(key, value):
    label, names = OUTPUT_LABELS[key]
    if isinstance(value, bool):
        return 'ja' if value else 'nein'
    if key == 'formats':
        return ', '.join(names.get(v, v) for v in value)
    if key in ('font_size',):
        return str(value).replace('.', ',') + ' pt'
    if key == 'line_spacing':
        return str(value).replace('.', ',') + '-fach'
    return names.get(value, str(value)) if names else str(value)


OUTPUT_GROUPS = [('Seite', ['page_size', 'margins', 'chapter_start', 'running_heads', 'page_numbers']),
                 ('Schrift', ['font', 'font_size', 'heading_font', 'initials', 'glossary_marks']),
                 ('Absatz', ['line_spacing', 'paragraph', 'hyphenation']),
                 ('Titelei', ['title_page', 'imprint', 'toc', 'toc_depth']),
                 ('Formate', ['formats'])]
PUBLICATION_LABELS = [('publisher', 'Verlag', '„Selbstverlag“ oder Name des Verlags'),
                      ('isbn_print', 'ISBN Druckausgabe', 'ISBN-13 mit Prüfziffer'),
                      ('isbn_ebook', 'ISBN E-Book', 'ISBN-13 mit Prüfziffer'),
                      ('rights', 'Rechtehinweis', 'z. B. „Alle Rechte vorbehalten.“')]


TEMPLATE_DE = {'classic': 'klassisch', 'modern': 'modern', 'plain': 'schlicht'}


def output_view(base, config, args):
    """Formular „Ausgabeoptionen“ (#68): Vorlage ausgabeoptionen bzw. Textfassung."""
    ts = dict(TYPESETTING_DEFAULT)
    ts.update(config.get('typesetting') or {})
    pub = config.get('publication') or {}
    if not args.text:
        import build_cover
        blurb, bio = build_cover.back_texts(base)
        data = {'typesetting': ts, 'publication': pub, 'print': config.get('print') or {}, 'cover': config.get('cover') or {},
                'blurb': blurb, 'author_bio': bio}
        return fill('ausgabeoptionen.html', {'OUTPUT_JSON': json.dumps(data, ensure_ascii=False)})
    lines = ['### 🖨️ Ausgabeoptionen', '', 'Wie Auflagen und Probedrucke aussehen. Geänderte Werte gelten ab dem nächsten '
             'Probedruck; ohne Angabe bleibt alles wie bisher.', '']
    for group, keys in OUTPUT_GROUPS:
        lines += [f'**{group}**', '', '| Feld | Aktueller Wert | Mögliche Werte |', '|---|---|---|']
        for k in keys:
            label, names = OUTPUT_LABELS[k]
            if isinstance(TYPESETTING_DEFAULT[k], bool):
                options = 'ja, nein'
            elif k == 'font_size':
                options = '10, 10,5, 11, 11,5, 12'
            elif k == 'line_spacing':
                options = '1,0, 1,1, 1,2, 1,3, 1,5'
            elif k == 'formats':
                options = 'PDF, Druck-PDF, Umschlag, DOCX, EPUB (mehrere, mit Komma)'
            else:
                options = ', '.join(names.values())
            lines.append(f'| {label} | {output_value(k, ts[k])} | {options} |')
        lines.append('')
    lines += ['**Angaben im Impressum**', '', '| Feld | Aktueller Wert | Hinweis |', '|---|---|---|']
    lines += [f'| {label} | {pub.get(k) or "–"} | {hint} |' for k, label, hint in PUBLICATION_LABELS]
    pr, cv = config.get('print') or {}, config.get('cover') or {}
    prof = {'kdp': 'Amazon KDP', 'bod': 'Books on Demand', 'custom': 'eigene Werte'}
    paper = {'white': 'weiß', 'cream': 'creme', 'premium_color': 'Premiumfarbe'}
    spine = (f'{pr["spine_mm"]} mm (fest)' if pr.get('spine_mm') is not None else
             f'aus Seitenzahl × {pr["paper_mm_per_page"]} mm' if pr.get('paper_mm_per_page') else
             'aus Seitenzahl und Papier' if pr.get('profile') == 'kdp' else '–')
    lines += ['', '**Druck**', '', '| Feld | Aktueller Wert | Mögliche Werte |', '|---|---|---|',
              f'| Druckprofil | {prof.get(pr.get("profile"), "–")} | Amazon KDP, Books on Demand, eigene Werte |',
              f'| Papier | {paper.get(pr.get("paper"), "weiß" if pr.get("profile") == "kdp" else "–")} | weiß, creme, Premiumfarbe (nur KDP) |',
              f'| Rückenbreite | {spine} | Zahl in mm (BoD: aus dem BoD-Rechner) |',
              f'| Beschnitt | {pr.get("bleed_mm", "Vorgabe des Profils")}{" mm" if "bleed_mm" in pr else ""} | Zahl in mm |',
              f'| Schnittmarken | {"ja" if pr.get("crop_marks") else "nein"} | ja, nein |', '',
              '**Umschlag**', '', '| Feld | Aktueller Wert | Mögliche Werte |', '|---|---|---|',
              f'| Vorlage | {TEMPLATE_DE.get(cv.get("template", "classic"), "")} | klassisch, modern, schlicht |',
              f'| Hintergrund | {cv.get("background", "#1F2A44")} | Farbe als #RRGGBB |',
              f'| Schriftfarbe | {cv.get("text_color", "#FFFFFF")} | Farbe als #RRGGBB |',
              f'| Bild vorne | {cv.get("image") or "–"} | Datei unter cover/ (JPG, PNG, mind. 300 dpi) |',
              f'| Autorenbild | {cv.get("author_image") or "–"} | Datei unter cover/ |',
              f'| Preis | {cv.get("price") or "–"} | z. B. 18,00 € (D) |',
              f'| Rückentext | {"von unten nach oben" if cv.get("spine_direction") == "up" else "von oben nach unten"} | von oben nach unten, von unten nach oben |',
              '', '<sub>Klappentext und Autorentext stehen in `cover/rueckseite.md` (`## Klappentext`, `## Über …`). '
              'Die Vorgaben der Druckanbieter ändern sich; Maße vor dem Hochladen mit deren Rechner abgleichen.</sub>',
              '', FORM_HINT]
    return '\n'.join(lines) + '\n'


def ai_disc_text(config):
    s = (config.get('ai_disclosure') or {})
    mode = s.get('mode', 'none')
    if mode == 'none':
        return 'keine'
    place = {'imprint': 'im Impressum', 'foreword': 'im Vorwort', 'afterword': 'im Nachwort', 'page': 'eigene Seite'}
    return {'short': 'kurz', 'detailed': 'ausführlich', 'custom': 'eigener Text'}[mode] + ', ' + \
        place.get(s.get('placement', 'imprint'), '') + ('' if s.get('text') else ' (Wortlaut offen)')


def project_settings_view(base, config, args):
    ts = dict(TYPESETTING_DEFAULT)
    ts.update(config.get('typesetting') or {})
    wf = config.get('workflow') or {}
    fixed = []
    for block, key, label in FIXED_RULES:
        v = (config.get(block) or {}).get(key)
        if v is None:
            continue
        text = FIXED_TEXT.get(v, str(v))
        fixed.append({'FIXED_LABEL': label, 'FIXED_VALUE': text if isinstance(v, bool) else f'{text} ({v})'})
    fc = wf.get('fact_checking_default') or 'optional'
    upd_auto, upd_text, upd_hint = update_info(base, config)
    auto_merge = (config.get('changes') or {}).get('auto_merge') is True
    lim = config.get('limits') or {}
    lim_sum = limit_summary(base, config)
    if args.text:
        page = {'a5': 'A5 (14,8 × 21 cm)', '12x19': '12 × 19 cm', '13.5x21.5': '13,5 × 21,5 cm', 'a4': 'A4'}
        jn = lambda v: 'ja' if v else 'nein'
        return '\n'.join(['### ⚙️ Projekteinstellungen', '', '**🔒 Feste Regeln** *(nur im Chat mit ausdrücklicher Bestätigung änderbar)*', '',
                           '| Regel | Wert |', '|---|---|'] + [f'| {f["FIXED_LABEL"]} | {f["FIXED_VALUE"]} |' for f in fixed]
                          + ['', '**Bearbeitbar**', '', '| Feld | Aktueller Wert | Mögliche Werte |', '|---|---|---|',
                             f'| Faktencheck | {FC_TEXT[fc]} | aus, optional, angefordert |',
                             f'| Seitenformat | {page.get(ts["page_size"], ts["page_size"])} | A5, 12×19, 13,5×21,5, A4 |',
                             f'| Schrift | {"Serifenschrift" if ts["font"] == "serif" else "serifenlos"} | Serif, Serifenlos |',
                             f'| Schriftgröße | {str(ts["font_size"]).replace(".", ",")} pt | 10, 10,5, 11, 11,5, 12 |',
                             f'| Titelseite | {jn(ts["title_page"])} | ja, nein |', f'| Impressum | {jn(ts["imprint"])} | ja, nein |',
                             f'| Inhaltsverzeichnis | {jn(ts["toc"])} | ja, nein |',
                             f'| Verzeichnistiefe | {"nur Kapitel" if ts["toc_depth"] == 1 else "Kapitel und Abschnitte"} | Kapitel, Abschnitte |',
                             f'| Updates automatisch | {jn(upd_auto)} | ja, nein |',
                             f'| Änderungen sofort übernehmen | {jn(auto_merge)} | ja, nein |',
                             f'| KI-Budget je Monat | {lim.get("ai_budget_monthly") or "–"} | Betrag in Projektwährung, leer = keins |',
                             f'| Actions-Minuten je Monat | {lim.get("actions_minutes_monthly") or "–"} | Minuten, leer = nicht prüfen |',
                             f'| KI-Angabe im Buch | {ai_disc_text(config)} | Formular `KI-Angabe` |',
                             '| Weitere Ausgabeoptionen | Ränder, Zeilenabstand, Kolumnentitel, Formate, ISBN … | Formular `Ausgabe` |',
                             '', f'<sub>{upd_text} · Limits: {lim_sum}</sub>'] + ([f'', f'> ⚠️ {upd_hint}'] if upd_hint else []) + ['', FORM_HINT]) + '\n'
    def b(v):
        return 'true' if v else 'false'
    return fill('projekteinstellungen.html', {'FACT_CHECK_DEFAULT': fc, 'PAGE_SIZE': ts['page_size'], 'FONT': ts['font'],
                                              'FONT_SIZE': str(ts['font_size']).rstrip('0').rstrip('.') if isinstance(ts['font_size'], float) else str(ts['font_size']),
                                              'TITLE_PAGE': b(ts['title_page']), 'IMPRINT': b(ts['imprint']), 'TOC': b(ts['toc']),
                                              'TOC_DEPTH': str(ts['toc_depth']), 'UPDATES_AUTO': b(upd_auto), 'CHANGES_AUTO_MERGE': b(auto_merge),
                                              'GW_VERSION_TEXT': upd_text, 'GW_UPDATE_HINT': upd_hint,
                                              'AI_DISCLOSURE_TEXT': ai_disc_text(config),
                                              'LIMIT_BUDGET': num_text(lim.get('ai_budget_monthly')),
                                              'LIMIT_MINUTES': num_text(lim.get('actions_minutes_monthly')),
                                              'LIMIT_SUMMARY': lim_sum}, {'FIXED': fixed})


def num_text(v):
    if v in (None, ''):
        return ''
    return str(int(v)) if float(v).is_integer() else str(v)


def ai_disclosure_view(base, config, args):
    """Formular „KI-Angabe im Buch“ (#78), Vorlage ki-angabe bzw. Textfassung: Einstellung, Vorschlag, Hinweis."""
    import ai_disclosure as ad
    s = ad.settings(config)
    proposal = ad.suggest(base, config) if s['mode'] in ('none', 'short', 'detailed') else ''
    used = ad.usage(base)
    names = ad.provider_names()
    if not args.text:
        kinds = {i['kind'] for _, i in matter_items(config)}
        missing = [k for k in ('foreword', 'afterword') if k not in kinds]
        if not (config.get('typesetting') or {}).get('imprint', True):
            missing.append('imprint')
        values = {'AI_MODE': s['mode'], 'AI_PLACEMENT': s['placement'], 'AI_NAME_SERVICES': str(bool(s['name_services'])).lower(),
                  'AI_TEXT': s.get('text') or '',
                  'AI_USED_TEXT': ' · '.join(f'{t}: {ad.service_text(ids, names)}' for t, ids in used.items()),
                  'AI_PROPOSAL_SHORT': ad.suggest(base, config, 'short', False),
                  'AI_PROPOSAL_SHORT_NAMED': ad.suggest(base, config, 'short', True),
                  'AI_PROPOSAL_DETAILED': ad.suggest(base, config, 'detailed', False),
                  'AI_PROPOSAL_DETAILED_NAMED': ad.suggest(base, config, 'detailed', True),
                  'AI_PLACES_MISSING': ','.join(missing), 'AI_LEGAL_HINT': ad.LEGAL_HINT}
        return fill('ki-angabe.html', values)
    mode_de = {'none': 'keine', 'short': 'kurz (ein Satz)', 'detailed': 'ausführlich (je Aufgabe)', 'custom': 'eigener Text'}
    place_de = {'imprint': 'Impressum', 'foreword': 'Vorwort (am Ende)', 'afterword': 'Nachwort (am Ende)', 'page': 'eigene Seite am Ende'}
    lines = ['### 🤖 KI-Angabe im Buch', '',
             'Ob und wie im Buch steht, wie bei diesem Buch KI genutzt wurde. Der Hinweis auf die Entwicklung von '
             'GhostWriter kommt nie ins Buch.', '',
             '| Feld | Aktueller Wert | Mögliche Werte |', '|---|---|---|',
             f'| Angabe | {mode_de[s["mode"]]} | keine, kurz, ausführlich, eigener Text |',
             f'| Ort | {place_de[s["placement"]]} | Impressum, Vorwort, Nachwort, eigene Seite |',
             f'| Dienste nennen | {"ja" if s["name_services"] else "nein"} | ja, nein |', '']
    if used:
        lines += ['**Laut den Läufen genutzt:** ' + ' · '.join(
            f'{t}: {ad.service_text(ids, names)}' for t, ids in used.items()), '']
    else:
        lines += ['*Bisher sind keine KI-Läufe protokolliert.*', '']
    if s['mode'] != 'none':
        lines += ['**Wortlaut im Buch' + (' (bestätigt)' if s['text'] else ' – noch nicht bestätigt') + ':**', '']
        lines += ['> ' + l if l else '>' for l in (s['text'] or '*(leer)*').splitlines()] + ['']
    if proposal and proposal != s['text'] and s['mode'] in ('short', 'detailed'):
        lines += ['**Vorschlag aus den Läufen:**', ''] + ['> ' + l if l else '>' for l in proposal.splitlines()] + ['']
    lines += [f'<sub>⚖️ {ad.LEGAL_HINT}</sub>', '', '---',
              'Antworte mit `Angabe: …`, `Ort: …`, `Dienste nennen: ja|nein` oder `Text: …` (eigener Wortlaut)'
              + (' · `OK` übernimmt den Vorschlag' if proposal and s['mode'] in ('short', 'detailed') else '')
              + ' · `X` bricht ab']
    return '\n'.join(lines) + '\n'


CHAPTER_RESEARCH_DIR = 'research/kapitel'   # workflow.yml, runs.chapter_research


def run_parts(path):
    """(Kopf, {Überschrift: Text}) einer Lauf-Datei."""
    text = path.read_text(encoding='utf-8')
    head, body = {}, text
    m = re.match(r'---\n(.*?)\n---\n', text, re.S)
    if m:
        head = yaml.safe_load(m.group(1)) or {}
        body = text[m.end():]
    parts = {k.strip(): v.strip() for k, v in re.findall(r'(?m)^## ([^\n]+)\n(.*?)(?=^## |\Z)', body, re.S)}
    return head, parts


def chapter_research_view(base, config, args):
    """Formular „Kapitelrecherche“: Ziel und Kurzbeschreibung ändern, Recherche für das Kapitel starten."""
    n, ch = chapter_number(config, args.where)
    _, summary, goal = chapter_readme(base, ch)
    runs = sorted((base / ch['path'] / CHAPTER_RESEARCH_DIR).glob('run-*.md'))
    last_head, last = run_parts(runs[-1]) if runs else ({}, {})
    draft = {}
    if getattr(args, 'draft', None):
        draft = json.loads(Path(args.draft).read_text(encoding='utf-8'))
    ap = config.get('ai_providers') or {}
    pid = (ap.get('research') or {}).get('provider') or (ap.get('default') or {}).get('provider') or 'chat'
    catalog = yaml.safe_load((ROOT / 'providers.yml').read_text(encoding='utf-8'))
    names = {x['id']: x.get('name', x['id']) for x in catalog.get('providers') or []}
    provider = 'aktueller Chat' if pid == 'chat' else names.get(pid, pid).split(' (')[0]
    when = str(last_head.get('date') or '')
    count = (f'{len(runs)} Lauf' if len(runs) == 1 else f'{len(runs)} Läufe') if runs else 'noch keine Kapitelrecherche'
    if runs and re.match(r'\d{4}-\d{2}-\d{2}', when):
        count += f', zuletzt am {when[8:10]}.{when[5:7]}.{when[:4]}'
    clean = lambda v: '' if (v or '').strip() in ('', 'Offen.', '–') else v.strip()
    chapters = config['structure']['chapters']
    def neighbour(k):
        if 1 <= k <= len(chapters):
            other = chapters[k - 1]
            return f'Kapitel {k} · {other["title"]}', chapter_readme(base, other)[1]
        return '', ''
    prev_label, prev_summary = neighbour(n - 1)
    next_label, next_summary = neighbour(n + 1)
    def weight(key):
        v = draft.get(key, last_head.get(key, 2))
        return v if isinstance(v, int) and 0 <= v <= 3 else 2
    current_goal = draft.get('goal', goal)
    if 'task' in draft:
        task = draft.get('task') or ''
    elif 'task' in last_head:
        task = last_head.get('task') or ''
    elif 'goal_search' in last_head:            # Läufe vor 0.19: goal_search true/false
        task = 'goal' if last_head.get('goal_search') is True else ''
    else:
        task = '' if current_goal else 'goal'
    task = task if task in ('goal', 'sections', 'summary') else ''
    existing = {sec['title'].strip().lower() for sec in ch['sections']}
    proposals = []
    for line in clean(last.get('Vorschlag: Abschnitte')).splitlines():
        m = re.match(r'\s*[-*]\s+(.+?)(?::\s+(.*))?$', line)
        if m and m.group(1).strip().lower() not in existing:
            proposals.append({'SUG_TITLE': m.group(1).strip(), 'SUG_SUMMARY': (m.group(2) or '').strip()})
    k = len(ch['sections'])
    note = ('Das Kapitel hat noch keine Abschnitte; ausgewählte werden in dieser Reihenfolge angelegt.' if not k else
            f'Das Kapitel hat schon {k} Abschnitt{"" if k == 1 else "e"}. Sie bleiben unverändert; ausgewählte neue '
            'kommen ans Ende (Reihenfolge danach über „Abschnittsreihenfolge“).')
    if k and ch.get('status') == 'approved':
        note += ' Das Kapitel ist freigegeben und wird dadurch wieder „in Arbeit“.'
    values = {'CHAPTER_ID': ch['id'], 'CHAPTER_NUMBER': n, 'CHAPTER_TITLE': ch['title'],
              'CHAPTER_GOAL': draft.get('goal', goal), 'CHAPTER_SUMMARY': draft.get('summary', summary),
              'RESEARCH_QUESTION': draft.get('question', last_head.get('question') or ''),
              'RESEARCH_SCOPE': draft.get('scope', last_head.get('scope') or ''),
              'RESEARCH_TASK': task, 'SECTION_COUNT': k, 'SECTIONS_NOTE': note,
              'PREV_CHAPTER': 'true' if prev_label else '', 'PREV_CHAPTER_LABEL': prev_label,
              'PREV_CHAPTER_SUMMARY': prev_summary, 'PREV_WEIGHT': weight('weight_prev'),
              'NEXT_CHAPTER': 'true' if next_label else '', 'NEXT_CHAPTER_LABEL': next_label,
              'NEXT_CHAPTER_SUMMARY': next_summary, 'NEXT_WEIGHT': weight('weight_next'),
              'RESEARCH_PROVIDER_TEXT': f'Recherche über: {provider}', 'RUN_COUNT_TEXT': count,
              'LAST_RUN': 'true' if runs else '', 'LAST_RUN_ID': last_head.get('id') or (runs[-1].stem if runs else ''),
              'LAST_RUN_TEXT': clean(last.get('Kurzfassung')),
              'SUGGESTED_GOAL': clean(last.get('Vorschlag: Ziel des Kapitels')),
              'SUGGESTED_SUMMARY': clean(last.get('Vorschlag: Kurzbeschreibung'))}
    if args.text:
        lines = [f'### 🔎 Kapitelrecherche · Kapitel {n} „{ch["title"]}“', ''] + field_table([
            ('Ziel', values['CHAPTER_GOAL']), ('Kurzbeschreibung', values['CHAPTER_SUMMARY'])])
        if values['SUGGESTED_GOAL'] or values['SUGGESTED_SUMMARY']:
            lines += ['', f'**Vorschläge aus {values["LAST_RUN_ID"]}:**']
            if values['SUGGESTED_GOAL']:
                lines += [f'- Ziel: {values["SUGGESTED_GOAL"]} · `VZ` übernehmen']
            if values['SUGGESTED_SUMMARY']:
                lines += [f'- Kurzbeschreibung: {values["SUGGESTED_SUMMARY"]} · `VK` übernehmen']
        if values['LAST_RUN_TEXT']:
            lines += ['', f'> {values["LAST_RUN_TEXT"]}']
        if proposals:
            lines += ['', f'**Vorgeschlagene Abschnitte aus {values["LAST_RUN_ID"]}:**', '']
            lines += [f'{i}. **{x["SUG_TITLE"]}**' + (f' – {x["SUG_SUMMARY"]}' if x['SUG_SUMMARY'] else '')
                      for i, x in enumerate(proposals, start=1)]
            lines += ['', f'<sub>{note}</sub> Anlegen: `AS 1, 3` (Nummern der Vorschläge).']
        wtext = ['nicht berücksichtigen', 'abgrenzen', 'anschließen', 'stark einbeziehen']
        ctx = []
        if prev_label:
            ctx.append(f'| Vorher | {prev_label} | {values["PREV_WEIGHT"]} · {wtext[values["PREV_WEIGHT"]]} |')
        if next_label:
            ctx.append(f'| Nachher | {next_label} | {values["NEXT_WEIGHT"]} · {wtext[values["NEXT_WEIGHT"]]} |')
        if ctx:
            lines += ['', '**Zusammenhang**', '', '| | Kapitel | Gewichtung |', '|---|---|---|'] + ctx
        tname = {'goal': 'Ziel des Kapitels recherchieren', 'sections': 'Abschnitte erstellen', 'summary': 'Kurzbeschreibung erstellen'}
        lines += ['', f'Aufgabe: **{tname.get(task, "keine (nur Fragestellung)")}**',
                  '', f'<sub>{values["RESEARCH_PROVIDER_TEXT"]} · {count}</sub>', '',
                  'Ändern: je Zeile `Ziel: …` bzw. `Kurzbeschreibung: …`. Recherche starten: `Frage: …` (optional `Schwerpunkte: …`, '
                  '`Aufgabe: Ziel|Abschnitte|Kurzbeschreibung|keine`, `Vorher: 0–3`, `Nachher: 0–3`; 0 nicht berücksichtigen, 1 abgrenzen, 2 anschließen, 3 stark einbeziehen). `X` bricht ab.']
        return '\n'.join(lines) + '\n'
    return fill('kapitelrecherche.html', values, {'SUGGESTED_SECTIONS': proposals})


# ---------- Bücherregal (#37) ----------

LIBRARY_FILE = 'library.json'


def library_data(base, args):
    """library.json (--library oder im Projektordner); fehlt sie, live aus den Branches (scripts/library.py)."""
    path = Path(args.library) if getattr(args, 'library', None) else base / LIBRARY_FILE
    if path.is_file():
        return json.loads(path.read_text(encoding='utf-8'))
    import library
    return library.build_library(cwd=base)


def de_date(iso):
    m = re.match(r'(\d{4})-(\d{2})-(\d{2})', iso or '')
    return f'{m.group(3)}.{m.group(2)}.{m.group(1)}' if m else ''


def plural(n, one, many):
    return f'{n} {one if n == 1 else many}'


def library_view(base, config, args):
    data = library_data(base, args)
    rows = []
    for b in data.get('books') or []:
        ready = b['status'] == 'ready'
        st, sa = b.get('sections_total', 0), b.get('sections_approved', 0)
        progress = (f'{sa} von {plural(st, "Abschnitt", "Abschnitten")} freigegeben · '
                    f'{b.get("chapters_approved", 0)} von {plural(b.get("chapters_total", 0), "Kapitel", "Kapiteln")}') if ready else 'Gliederung noch offen'
        ed = b.get('current_edition') or 0
        rows.append({'BOOK_BRANCH': b['branch'], 'BOOK_TITLE': b['title'] or b['title_short'] or 'Ohne Titel',
                     'BOOK_TITLE_SHORT': b['title_short'] or b['branch'].split('/')[-1],
                     'BOOK_AUTHOR_TEXT': f'von {b["author"]}' if b.get('author') else '',
                     'BOOK_STATE': 'ready' if ready else 'setup', 'BOOK_STATE_TEXT': 'eingerichtet' if ready else 'im Aufbau',
                     'BOOK_PROGRESS': round(100 * sa / st) if st else 0, 'BOOK_PROGRESS_TEXT': progress,
                     'BOOK_EDITION_TEXT': f'Auflage {ed}' if ed else 'noch keine Auflage',
                     'BOOK_COST': (b.get('cost') or {}).get('text') or money(0, False),
                     'BOOK_PENDING_TEXT': f'{plural(b["pending"], "Änderung", "Änderungen")} offen' if b.get('pending') else '',
                     'BOOK_UPDATED_TEXT': f'{"zuletzt geändert" if ready else "angelegt"} am {de_date(b.get("updated_at"))}' if b.get('updated_at') else ''})
    count = plural(len(rows), 'Buch', 'Bücher')
    if args.text:
        out = [f'### 📚 Bücherregal', f'{args.repo} · {count}', '']
        if rows:
            out += ['| # | Buch | Status | Fortschritt | Auflage | Kosten |', '|--:|---|---|---|---|--:|']
            for i, r in enumerate(rows, 1):
                out.append(f'| {i} | **{r["BOOK_TITLE"]}** ({r["BOOK_TITLE_SHORT"]}){" · ⏳ " + r["BOOK_PENDING_TEXT"] if r["BOOK_PENDING_TEXT"] else ""} | '
                           f'{"✅ eingerichtet" if r["BOOK_STATE"] == "ready" else "🚧 im Aufbau"} | {r["BOOK_PROGRESS_TEXT"]} | {r["BOOK_EDITION_TEXT"]} | {r["BOOK_COST"]} |')
        else:
            out += ['*Hier steht noch kein Buch.*']
        items = ([('1' if len(rows) == 1 else f'1–{len(rows)}', 'Buch öffnen')] if rows else []) + [('N', 'Neues Buch'), ('D', 'Daten')]
        out += ['', '---', menu(items)]
        return '\n'.join(out) + '\n'
    return fill('buecherregal.html', {'LIBRARY_NAME': args.repo, 'BOOK_COUNT_TEXT': count, 'EMPTY': '' if rows else '1',
                                      'UPDATED_TEXT': ''}, {'BOOKS': rows})



def book_create_view(base, config, args):
    """Formular „Neues Buch“ (#38). Vorhandene Bücher aus library.json bzw. live; --draft: gesendete Werte und error."""
    import library
    data = library_data(base, args)
    books = data.get('books') or []
    draft = json.loads(args.draft) if args.draft else {}
    latest = sorted((b for b in books if b.get('author')), key=lambda b: b.get('updated_at') or '')
    author = draft.get('author', latest[-1]['author'] if latest else '')
    prefix = library.settings(library.load_manifest())['book_prefix']
    if args.text:
        out = ['### 📗 Neues Buch', '', 'Das Buch bekommt einen eigenen Bereich in dieser Bibliothek; danach folgt der Einstiegsdialog.', '']
        if draft.get('error'):
            out += [f'> ✗ {draft["error"]}', '']
        out += field_table([('Titel (Arbeitstitel, Pflicht)', draft.get('working_title', '')),
                            ('Kurztitel (optional)', draft.get('title_short', '')), ('Autor (optional)', author)])
        if books:
            out += ['', 'Schon vergeben: ' + ', '.join(f'`{b["slug"]}` ({b["branch"]})' for b in books if b.get('slug'))]
        out += ['', f'Der Bereich heißt `{prefix}<kurztitel>`. Antworte mit `Titel: …`, optional `Kurztitel: …` und `Autor: …`. `X` bricht ab.']
        return '\n'.join(out) + '\n'
    return fill('buch-anlegen.html', {'BRANCH_PREFIX': prefix, 'WORKING_TITLE': draft.get('working_title', ''),
                                      'TITLE_SHORT': draft.get('title_short', ''), 'AUTHOR': author,
                                      'ERROR_TEXT': draft.get('error', '')},
                {'TAKEN': [{'TAKEN_SLUG': b.get('slug') or '', 'TAKEN_BRANCH': b['branch']} for b in books]})



# ---------- Seite „Daten“ (#71, Teil 1) ----------

PROOF_DAYS = 14   # Aufbewahrung der Probedruck-Artefakte (proof.yml)
RUN_NAMES = {'validate': 'Projektdateien prüfen', 'proof': 'Probedruck'}


def de_datetime_plus(iso, days=0):
    import datetime
    try:
        d = datetime.datetime.fromisoformat((iso or '').replace('Z', '+00:00')) + datetime.timedelta(days=days)
    except ValueError:
        return ''
    return d.strftime('%d.%m.%Y')


def github_data(args):
    """Rohdaten der GitHub-API aus --github (JSON): repo, branches, pulls, runs; fehlt die Datei, None."""
    if not getattr(args, 'github', None):
        return None
    return json.loads(Path(args.github).read_text(encoding='utf-8'))


def data_view(base, config, args):
    lib = library_data(base, args)
    gh = github_data(args)
    prog = lib.get('program') or {}
    upd = load_upstream(args)
    known = '' if gh is None else '1'
    runs = sorted((gh or {}).get('runs') or [], key=lambda r: r.get('created_at') or '', reverse=True)
    pulls = (gh or {}).get('pulls') or []

    def last_run(name, branch=None):
        for r in runs:
            if r.get('name') == name and (branch is None or r.get('head_branch') == branch):
                return r
        return None

    unknown = 'unbekannt (ohne GitHub-Abfrage)'
    if upd:
        prog_update = update_text(upd)
    elif getattr(args, 'upstream', None):
        prog_update = 'aktuell'
    else:
        prog_update = 'nicht abgefragt'
    values = {
        'LIBRARY_NAME': args.repo,
        'PROGRAM_VERSION_TEXT': f'GhostWriter {prog.get("version") or "?"} · Hauptrepository {prog.get("upstream") or "?"}',
        'PROGRAM_UPDATE_TEXT': prog_update, 'PROGRAM_BEHIND': upd['behind'] if upd else '',
        'PROGRAM_LAST_UPDATE_TEXT': f'letzter Update-Lauf am {de_datetime_plus(prog["last_update"])}' if prog.get('last_update') else 'noch kein Update-Lauf',
        'PROGRAM_SKIPPED_TEXT': ('Workflow-Dateien ausgelassen (Secret GHOSTWRITER_UPDATE_TOKEN fehlt): ' + ', '.join(prog['skipped_workflows']))
                                if prog.get('skipped_workflows') else '',
        'UI_TEXT': f'ghostwriter-ui {prog.get("ui_version") or "?"} · Commit {(prog.get("ui_commit") or "")[:7]}',
        'GITHUB_KNOWN': known,
        'CLEANUP_URL': f'https://github.com/{args.repo}/actions/workflows/cleanup.yml',
        'TASKS_URL': f'https://github.com/{args.repo}/issues?q=is%3Aissue+is%3Aopen+L%C3%B6schaufgaben',
    }
    repo = (gh or {}).get('repo') or {}
    if gh is None:
        values['REPO_TEXT'] = unknown
    else:
        size = repo.get('size')
        size_text = (f'{size / 1024:.1f} MB'.replace('.', ',') if size and size >= 1024 else f'{size} KB') if size is not None else 'Größe ?'
        nb = len((gh or {}).get('branches') or [])
        values['REPO_TEXT'] = (f'{"privat" if repo.get("private") else "öffentlich"} · {size_text} · '
                               f'{plural(nb, "Branch", "Branches")}')
    books = []
    for b in lib.get('books') or []:
        pr = next((p for p in pulls if (p.get('head') or {}).get('ref') == b.get('work_branch')), None)
        pending = b.get('pending') or 0
        pend_text = (f'{plural(pending, "Änderung", "Änderungen")} offen' + (f' · Pull Request #{pr["number"]}' if pr else '')) if pending else 'keine offenen Änderungen'
        ed = b.get('last_edition')
        v = last_run(RUN_NAMES['validate'], b['branch'])
        pr_run = last_run(RUN_NAMES['proof'], b['branch'])
        if gh is None:
            check, check_text, proof_text = '', 'Prüfung: unbekannt', 'Probedruck: unbekannt'
        else:
            check = {'success': 'ok', 'failure': 'fail'}.get((v or {}).get('conclusion'), '')
            check_text = ('Prüfung beim letzten Push: ' + {'ok': 'bestanden', 'fail': 'fehlgeschlagen'}.get(check, (v or {}).get('status') or 'noch nicht gelaufen')) if v else 'Prüfung: noch kein Lauf'
            if pr_run:
                proof_text = (f'Probedruck vom {de_datetime_plus(pr_run.get("created_at"))}, Download bis '
                              f'{de_datetime_plus(pr_run.get("created_at"), PROOF_DAYS)}')
            else:
                proof_text = 'noch kein Probedruck'
        books.append({
            'B_TITLE': b.get('title') or b.get('title_short') or b['branch'], 'B_BRANCH': b['branch'],
            'B_COMMIT_TEXT': f'{de_date(b.get("updated_at"))} · {b.get("last_commit") or ""}'.strip(' ·'),
            'B_PENDING_TEXT': pend_text, 'B_PENDING': '1' if pending else '',
            'B_AUTOMERGE_TEXT': 'Änderungen sofort übernehmen: ' + ('an' if b.get('auto_merge') else 'aus'),
            'B_EDITION_TEXT': f'Auflage {ed["number"]} vom {de_date(ed["date"])} ({ed["tag"]})' if ed else 'noch keine Auflage',
            'B_PROOF_TEXT': proof_text,
            'B_DATA_TEXT': f'Datenversion {b.get("data_version", "?")}' + (' · Migration steht aus (kommt mit dem nächsten Update)' if b.get('migration_pending') else ' · aktuell'),
            'B_MIGRATION': '1' if b.get('migration_pending') else '',
            'B_CHECK': check, 'B_CHECK_TEXT': check_text})
    secrets = lib.get('secrets')
    srows = []
    for n in lib.get('secret_names') or []:
        v = None if secrets is None else secrets.get(n)
        state = '' if v is None else ('yes' if v else 'no')
        srows.append({'S_NAME': n, 'S_STATE': state or 'unknown',
                      'S_TEXT': {'yes': 'hinterlegt', 'no': 'fehlt', 'unknown': 'unbekannt'}[state or 'unknown']})
    rrows = []
    seen = set()
    for r in runs:
        if r.get('name') in seen:
            continue
        seen.add(r.get('name'))
        c = r.get('conclusion') or r.get('status') or ''
        rrows.append({'R_NAME': r.get('name') or '', 'R_STATE': {'success': 'ok', 'failure': 'fail'}.get(c, 'other'),
                      'R_TEXT': f'{ {"success": "erfolgreich", "failure": "fehlgeschlagen", "cancelled": "abgebrochen", "skipped": "übersprungen", "in_progress": "läuft", "queued": "wartet", "action_required": "wartet auf Freigabe"}.get(c, c)} · '
                                f'{de_datetime_plus(r.get("created_at"))} · {r.get("head_branch") or ""}',
                      'R_URL': r.get('html_url') or ''})
    if args.text:
        out = ['### 🗂️ Daten', f'{args.repo}', '', '**Programm**', '',
               f'- {values["PROGRAM_VERSION_TEXT"]}', f'- Update: {values["PROGRAM_UPDATE_TEXT"]} · {values["PROGRAM_LAST_UPDATE_TEXT"]}',
               f'- {values["UI_TEXT"]}'] + ([f'- ⚠️ {values["PROGRAM_SKIPPED_TEXT"]}'] if values['PROGRAM_SKIPPED_TEXT'] else [])
        out += ['', '**Bücher**', '', '| Buch | Letzter Stand | Änderungen | Auflage | Probedruck | Daten | Prüfung |', '|---|---|---|---|---|---|---|']
        for r in books:
            out.append(f'| {r["B_TITLE"]} (`{r["B_BRANCH"]}`) | {r["B_COMMIT_TEXT"]} | {r["B_PENDING_TEXT"]}; {r["B_AUTOMERGE_TEXT"]} | '
                       f'{r["B_EDITION_TEXT"]} | {r["B_PROOF_TEXT"]} | {"⚠️ " if r["B_MIGRATION"] else ""}{r["B_DATA_TEXT"]} | '
                       f'{ {"ok": "✅ ", "fail": "❌ "}.get(r["B_CHECK"], "")}{r["B_CHECK_TEXT"]} |')
        out += ['', '**Repository**', '', f'- {values["REPO_TEXT"]}',
                f'- Erledigte Branches: [Branches aufräumen]({values["CLEANUP_URL"]}) · [Löschaufgaben]({values["TASKS_URL"]})']
        if srows:
            out += ['- Secrets (nur Namen): ' + ', '.join(f'`{r["S_NAME"]}` { {"yes": "✅", "no": "❌", "unknown": "❔"}[r["S_STATE"]]} {r["S_TEXT"]}' for r in srows)]
        if rrows:
            out += ['', '**Letzte Läufe**', '', '| Action | Ergebnis |', '|---|---|'] + [f'| [{r["R_NAME"]}]({r["R_URL"]}) | {r["R_TEXT"]} |' for r in rrows]
        out += ['', '---', menu([('Ü', 'Bücherregal')] + ([('U', 'Update einspielen')] if upd else []))]
        return '\n'.join(out) + '\n'
    return fill('daten.html', values, {'BOOKS': books, 'SECRETS': srows, 'RUNS': rrows})


WIZARD_CHOICES = Path(__file__).resolve().parent.parent / 'templates' / 'wizard-choices.yml'
LETTERS = 'abcdef'


def choice_spec(args):
    """Auswahl-Spezifikation: Schritt aus templates/wizard-choices.yml (where) oder --spec (JSON-Datei bzw. JSON-Text)."""
    if args.spec:
        raw = Path(args.spec).read_text(encoding='utf-8') if Path(args.spec).is_file() else args.spec
        spec = json.loads(raw)
        spec.setdefault('step', args.where or 'choice')
        return spec
    lib = yaml.safe_load(WIZARD_CHOICES.read_text(encoding='utf-8'))
    step = args.where or ''
    if step not in lib['steps']:
        raise SystemExit(f'Auswahl „{step}“ unbekannt; vorhanden: {", ".join(lib["steps"])}')
    spec = dict(lib['steps'][step], step=step)
    num = step.split('.')[-1]
    for k in ('title', 'subtitle', 'note'):
        if spec.get(k):
            spec[k] = spec[k].replace('{step}', num).replace('{steps}', str(lib.get('steps_total', '')))
    return spec


def check_choice_spec(spec):
    qs = spec.get('questions') or []
    if not 1 <= len(qs) <= 4:
        raise SystemExit('Auswahl: 1–4 Fragen')
    for q in qs:
        opts = q.get('options') or []
        if not 2 <= len(opts) <= 6:
            raise SystemExit(f'Auswahl „{q.get("key")}“: 2–6 Antworten')
        if len(q.get('header', '')) > 12:
            raise SystemExit(f'Auswahl „{q.get("key")}“: Etikett höchstens 12 Zeichen')
        if sum(bool(o.get('recommended')) for o in opts) > 1:
            raise SystemExit(f'Auswahl „{q.get("key")}“: höchstens eine Empfehlung')


def config_value(config, path):
    v = config
    for part in (path or '').split('.'):
        if not part or not isinstance(v, dict) or part not in v:
            return None
        v = v[part]
    return v


def is_selected(current, value):
    if current is None or current == '' or current == []:
        return False
    if isinstance(current, list):
        return value in [str(x) for x in current]
    if isinstance(current, bool):
        return value == ('true' if current else 'false')
    return str(current) == value


def choice_view(base, config, args):
    spec = choice_spec(args)
    check_choice_spec(spec)
    qs = spec['questions']
    if args.text:
        out = [f'### {spec.get("title", "Auswahl")}']
        if spec.get('subtitle'):
            out += ['', spec['subtitle']]
        for i, q in enumerate(qs, 1):
            cur = config_value(config, q.get('field'))
            out += ['', f'**{i}. {q["text"]}**' + (' *(mehrere möglich)*' if q.get('multi') else '')]
            for letter, o in zip(LETTERS, q['options']):
                tags = (' · *empfohlen*' if o.get('recommended') else '') + (' · *bisher*' if is_selected(cur, str(o['value'])) else '')
                out.append(f'- `{i}{letter}` {o["label"]}' + (f' – {o["desc"]}' if o.get('desc') else '') + tags)
        example = ', '.join(f'{i}{"a c" if q.get("multi") else "a"}' for i, q in enumerate(qs, 1))
        out += ['', f'Antworte mit den Kürzeln, z. B. `{example}`; eigene Antwort als `1: Text`.'
                + (' `S` überspringt.' if spec.get('skippable') else '')]
        if spec.get('note'):
            out += ['', f'<sub>{spec["note"]}</sub>']
        return '\n'.join(out) + '\n'
    questions, options = [], []
    for i, q in enumerate(qs, 1):
        cur = config_value(config, q.get('field'))
        questions.append({'Q_INDEX': str(i), 'Q_KEY': q['key'], 'Q_HEADER': q.get('header', ''), 'Q_TEXT': q['text'],
                          'Q_MULTI': '1' if q.get('multi') else ''})
        for o in q['options']:
            v = str(o['value'])
            options.append({'OPT_Q': str(i), 'OPT_VALUE': v, 'OPT_LABEL': o['label'], 'OPT_DESC': o.get('desc', ''),
                            'OPT_RECOMMENDED': '1' if o.get('recommended') else '', 'OPT_SELECTED': '1' if is_selected(cur, v) else ''})
    return fill('auswahl.html', {'STEP': spec['step'], 'TITLE': spec.get('title', 'Auswahl'), 'SUBTITLE': spec.get('subtitle', ''),
                                 'NOTE': spec.get('note', ''), 'SKIPPABLE': '1' if spec.get('skippable') else ''},
                {'QUESTIONS': questions, 'OPTIONS': options})


FORMS = {'choice': choice_view, 'book-create': book_create_view, 'project-edit': project_edit_view, 'chapter-research': chapter_research_view, 'project-settings': project_settings_view, 'chapter-create': chapter_create_view,
         'chapter-reorder': chapter_reorder_view, 'edition-create': edition_create_view, 'chapter-edit': chapter_edit_view,
         'section-create': section_create_view, 'section-reorder': section_reorder_view,
         'changes-merge': changes_merge_view, 'providers-edit': providers_edit_view,
         'approval-writing': lambda b, c, a: approval_view(b, c, a, 'writing'),
         'approval-section': lambda b, c, a: approval_view(b, c, a, 'section'),
         'approval-chapter': lambda b, c, a: approval_view(b, c, a, 'chapter'),
         'approval-matter': lambda b, c, a: approval_view(b, c, a, 'section'),
         'approval-image': lambda b, c, a: approval_view(b, c, a, 'image'),
         'ai-disclosure': ai_disclosure_view, 'output': output_view}


def git_head(base):
    try:
        return subprocess.run(['git', '-C', str(base), 'rev-parse', 'HEAD'], capture_output=True, text=True,
                              check=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return ''


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('project')
    ap.add_argument('view', choices=['project', 'chapter', 'section', 'matter', 'characters', 'images', 'library', 'data'] + list(FORMS))
    ap.add_argument('where', nargs='?')
    ap.add_argument('--text', action='store_true')
    ap.add_argument('--repo', default='ploeffler/GhostWriter')
    ap.add_argument('--branch', default='main')
    ap.add_argument('--revoke', action='store_true', help='bei approval-*: Freigabe zurücknehmen statt erteilen')
    ap.add_argument('--upstream', help='JSON-Datei mit dem Update-Stand (behind, upstream, version, installed) für die Projektübersicht')
    ap.add_argument('--limits', help='JSON-Datei von limits.py check --json (Projektübersicht: Hinweis Vorwarnung bzw. Automatik pausiert); ohne Angabe nur das KI-Budget aus costs/')
    ap.add_argument('--changes', help='JSON-Datei mit den offenen Änderungen (Pull Request, Branches, Commits) für Projektübersicht und changes-merge')
    ap.add_argument('--head-sha', help='Commit des gelesenen Stands (HEAD_SHA); ohne Angabe der HEAD des Projektordners, wenn er ein Git-Repository ist')
    ap.add_argument('--draft', help='bei chapter-research bzw. book-create: JSON mit noch nicht gespeicherten Werten (goal, summary, question, scope bzw. working_title, title_short, author, error)')
    ap.add_argument('--library', help='library.json vom Standard-Branch (Bücherregal; in der Projektübersicht ab 2 Büchern der Link „Bücherregal“)')
    ap.add_argument('--github', help='bei data: JSON mit Rohdaten der GitHub-API (repo, branches, pulls, runs), siehe BEFUELLUNG.md, „Daten“')
    ap.add_argument('--spec', help='bei choice: JSON-Datei oder JSON-Text mit einer eigenen Auswahl (Aufbau wie templates/wizard-choices.yml)')
    ap.add_argument('--ui-ref', help='Commit oder Branch von ghostwriter-ui statt des festen Commits aus templates/ui/ghostwriter-ui.yml (nur zum Testen)')
    args = ap.parse_args()
    ui = yaml.safe_load(UI_CONFIG.read_text(encoding='utf-8'))
    UI['repo'], UI['ref'] = ui['repo'], args.ui_ref or ui['commit']
    base, config = load(args.project)
    UI['head'] = args.head_sha or git_head(base)
    if args.view in FORMS:
        out = FORMS[args.view](base, config, args)
    elif args.view == 'library':
        out = library_view(base, config, args)
    elif args.view == 'data':
        out = data_view(base, config, args)
    elif args.view == 'matter':
        out = matter_view(base, config, args)
    elif args.view == 'characters':
        out = characters_view(base, config, args)
    elif args.view == 'images':
        out = images_view(base, config, args)
    elif args.view == 'project':
        out = project_view(base, config, args)
    elif args.view == 'chapter':
        out = chapter_view(base, config, args, int(args.where))
    else:
        c, s = (int(x) for x in args.where.split('.'))
        out = section_view(base, config, args, c, s)
    sys.stdout.write(out)


if __name__ == '__main__':
    main()
