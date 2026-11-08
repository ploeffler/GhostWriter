#!/usr/bin/env python3
"""Referenzumsetzung der Befüllungsregeln aus templates/ui/BEFUELLUNG.md.

Aufruf:
  python scripts/render_view.py <projektordner> project            [--text] [--repo owner/name] [--branch main]
                                     (--repo ohne Angabe: GITHUB_REPOSITORY bzw. git remote origin)
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
    'kontinuitaet': re.compile(r'\[KONTINUITÄT PRÜFEN\b'),   # Widerspruch zu einem Vorband (#116)
}
MARKER_LABEL = {'anekdote': 'Platzhalter-Anekdote', 'quelle': 'Quelle prüfen',
                'medizin': 'Medizin prüfen', 'recht': 'Recht prüfen', 'kontinuitaet': 'Kontinuität prüfen'}
MARKER_TEXT = re.compile(r'\[(PLATZHALTER-ANEKDOTE|QUELLE PRÜFEN|MEDIZIN PRÜFEN|RECHT PRÜFEN|KONTINUITÄT PRÜFEN)(?::\s*([^\]]*))?\]')
KIND = {'PLATZHALTER-ANEKDOTE': 'anekdote', 'QUELLE PRÜFEN': 'quelle', 'MEDIZIN PRÜFEN': 'medizin', 'RECHT PRÜFEN': 'recht',
        'KONTINUITÄT PRÜFEN': 'kontinuitaet'}


# ---------- Daten lesen ----------

def load(project):
    base = Path(project)
    config = yaml.safe_load((base / 'ghostwriter.yml').read_text(encoding='utf-8'))
    attach_series(base, config)
    return base, config


def attach_series(base, config):
    """Serie des Buchs (#116): Figuren der Serie kommen zu den Figuren des Buchs (`_series`, Text in `_text`).
    Eine Figur des Buchs mit derselben ID ist eine Kopie (`_copy_of`, `_differs`); sie gilt für dieses Buch.
    Gespeichert wird davon nichts im Buch (characters.write_list lässt `_…`-Einträge weg)."""
    if not isinstance(config, dict) or not ((config.get('structure') or {}).get('chapters') or
                                            str(((config.get('project') or {}).get('title_short')) or '')):
        return
    if (base / 'series').is_dir():   # Standard-Branch selbst: kein Band
        return
    try:
        import series
        ser, items = series.book_characters(base)
    except Exception:   # noqa: BLE001 – ohne Git bzw. Bibliothek keine Serie
        return
    if not ser:
        return
    vols = series.volumes(ser)
    branch = series.branch_of(base)
    config['_series'] = {'id': ser['id'], 'title': ser.get('title', ''), 'subtitle': ser.get('subtitle', ''),
                         'kind': ser.get('kind', ''), 'issn': ser.get('issn', ''), 'volumes': vols,
                         'volume': vols.index(branch) + 1 if branch in vols else None,
                         'also_in_series': ser.get('also_in_series', True), 'branch': branch}
    own = {i['id']: i for i in config.get('characters') or []}
    for it in items:
        if it['id'] in own:
            local = base / own[it['id']]['path']
            text = local.read_text(encoding='utf-8') if local.is_file() else ''
            own[it['id']]['_copy_of'] = ser['id']
            own[it['id']]['_differs'] = text.strip() != it['_text'].strip()
        else:
            if not config.get('characters'):
                config['characters'] = []
            config['characters'].append(it)


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
        if k in (item['kind'], item['id'], item['id'][4:], item['title'].lower(), view_matter_kind(item['kind']).lower()):
            return item
    return None


# Figuren (#53): characters/<char-id>.md, Liste in ghostwriter.yml → characters
ROLE_DE = {'main': 'Hauptfigur', 'supporting': 'Nebenfigur', 'minor': 'Randfigur'}


def character_items(config):
    return list((config or {}).get('characters') or [])


def character_file(base, item):
    """(Kopf, Beschreibung, Notizen) einer Figurendatei; Platzhalter der Vorlage = leer. Figuren der Serie: `_text`."""
    text = item['_text'] if '_text' in item else (base / item['path']).read_text(encoding='utf-8')
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
    """Nur KI-API-Kosten zählen: über das Backend (#13) und aus Actions (#123); alte Chat-Schätzungen nicht."""
    return [e for e in entries if e.get('source', 'backend_api') in ('backend_api', 'action_api')]


def total(entries):
    """(Summe als Decimal oder None, enthält Schätzung)"""
    entries = counted(entries)
    amounts = [Decimal(str(e['cost_amount'])) for e in entries if e['cost_amount'] is not None]
    estimated = any(e['cost_status'] == 'estimated' for e in entries)
    return (sum(amounts) if amounts else None), estimated


def money(amount, estimated, currency='€'):
    if amount is None:
        return '–'
    s = f'{amount:.2f}'.replace('.', '.' if UI.get('language') == 'en' else ',')
    return ('≈ ' if estimated else '') + f'{s} {currency}'


def cost_hint(base_hint, amount, estimated):
    if amount is None:
        return view_message('cost.none')
    return base_hint + (view_message('cost.estimated') if estimated else '')


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


def view_message(key, **values):
    """Nur feste Oberflächentexte übersetzen, keine fertig befüllten Nutztexte."""
    try:
        from .view_i18n import translate
    except ImportError:
        from view_i18n import translate
    return translate(key, UI.get('language', 'de'), **values)


def view_status(code):
    if UI.get('language') == 'en':
        try:
            from .render_view_en import status
        except ImportError:
            from render_view_en import status
        return status(code)
    return STATUS_DE.get(code, code)


def view_plural(number, german_suffix, german_singular=False):
    if UI.get('language') == 'en':
        return '' if number == 1 else 's'
    return german_suffix if (number == 1 if german_singular else number != 1) else ''


def view_series_kind(kind):
    return {'continuous': view_message('continuous_story'),
            'standalone': view_message('standalone_volumes')}.get(kind, '')


def view_matter_kind(kind):
    labels = {'dedication': view_message('dedication'), 'foreword': view_message('foreword'),
              'prologue': view_message('prologue'), 'epilogue': view_message('epilogue'),
              'afterword': view_message('afterword'), 'glossary': view_message('glossary'),
              'acknowledgments': view_message('acknowledgements')}
    return labels.get(kind, MATTER[kind][1])


def view_labels(name):
    """Nur feste Tabellen lokalisieren; die importierbaren deutschen Konstanten bleiben stabil."""
    if name == 'OUTPUT_LABELS':
        return {
            'page_size': (
                view_message('labels.OUTPUT_LABELS.page_size.0'),
                {
                    'a5': view_message('labels.OUTPUT_LABELS.page_size.1.a5'),
                    '12x19': '12 × 19 cm',
                    '13.5x21.5': view_message('labels.OUTPUT_LABELS.page_size.1.13.5x21.5'),
                    'a4': 'A4',
                },
            ),
            'font': (
                view_message('labels.OUTPUT_LABELS.font.0'),
                {
                    'serif': view_message('labels.OUTPUT_LABELS.font.1.serif'),
                    'sans': view_message('labels.OUTPUT_LABELS.font.1.sans'),
                    'pagella': 'Pagella',
                    'termes': 'Termes',
                    'bonum': 'Bonum',
                    'schola': 'Schola',
                    'heros': 'Heros',
                    'adventor': 'Adventor',
                },
            ),
            'font_size': (view_message('labels.OUTPUT_LABELS.font_size.0'), None),
            'heading_font': (
                view_message('labels.OUTPUT_LABELS.heading_font.0'),
                {
                    'same': view_message('labels.OUTPUT_LABELS.heading_font.1.same'),
                    'serif': view_message('labels.OUTPUT_LABELS.heading_font.1.serif'),
                    'sans': view_message('labels.OUTPUT_LABELS.heading_font.1.sans'),
                },
            ),
            'initials': (view_message('labels.OUTPUT_LABELS.initials.0'), None),
            'glossary_marks': (
                view_message('labels.OUTPUT_LABELS.glossary_marks.0'),
                {
                    'arrow': view_message('labels.OUTPUT_LABELS.glossary_marks.1.arrow'),
                    'italic': view_message('labels.OUTPUT_LABELS.glossary_marks.1.italic'),
                    'none': view_message('labels.OUTPUT_LABELS.glossary_marks.1.none'),
                },
            ),
            'margins': (
                view_message('labels.OUTPUT_LABELS.margins.0'),
                {
                    'standard': 'Standard',
                    'classic': view_message('labels.OUTPUT_LABELS.margins.1.classic'),
                    'modern': view_message('labels.OUTPUT_LABELS.margins.1.modern'),
                },
            ),
            'line_spacing': (view_message('labels.OUTPUT_LABELS.line_spacing.0'), None),
            'paragraph': (
                view_message('labels.OUTPUT_LABELS.paragraph.0'),
                {
                    'indent': view_message('labels.OUTPUT_LABELS.paragraph.1.indent'),
                    'spacing': view_message('labels.OUTPUT_LABELS.paragraph.1.spacing'),
                },
            ),
            'hyphenation': (view_message('labels.OUTPUT_LABELS.hyphenation.0'), None),
            'chapter_start': (
                view_message('labels.OUTPUT_LABELS.chapter_start.0'),
                {
                    'any': view_message('labels.OUTPUT_LABELS.chapter_start.1.any'),
                    'right': view_message('labels.OUTPUT_LABELS.chapter_start.1.right'),
                },
            ),
            'running_heads': (
                view_message('labels.OUTPUT_LABELS.running_heads.0'),
                {
                    'sections': view_message('labels.OUTPUT_LABELS.running_heads.1.sections'),
                    'chapter': view_message('labels.OUTPUT_LABELS.running_heads.1.chapter'),
                    'book': view_message('labels.OUTPUT_LABELS.running_heads.1.book'),
                    'none': view_message('labels.OUTPUT_LABELS.running_heads.1.none'),
                },
            ),
            'page_numbers': (
                view_message('labels.OUTPUT_LABELS.page_numbers.0'),
                {
                    'header': view_message('labels.OUTPUT_LABELS.page_numbers.1.header'),
                    'footer_center': view_message('labels.OUTPUT_LABELS.page_numbers.1.footer_center'),
                    'footer_outer': view_message('labels.OUTPUT_LABELS.page_numbers.1.footer_outer'),
                },
            ),
            'title_page': (view_message('labels.OUTPUT_LABELS.title_page.0'), None),
            'imprint': (view_message('labels.OUTPUT_LABELS.imprint.0'), None),
            'toc': (view_message('labels.OUTPUT_LABELS.toc.0'), None),
            'toc_depth': (
                view_message('labels.OUTPUT_LABELS.toc_depth.0'),
                {
                    1: view_message('labels.OUTPUT_LABELS.toc_depth.1.1'),
                    2: view_message('labels.OUTPUT_LABELS.toc_depth.1.2'),
                },
            ),
            'formats': (
                view_message('labels.OUTPUT_LABELS.formats.0'),
                {
                    'pdf': view_message('labels.OUTPUT_LABELS.formats.1.pdf'),
                    'pdf_print': view_message('labels.OUTPUT_LABELS.formats.1.pdf_print'),
                    'cover': view_message('labels.OUTPUT_LABELS.formats.1.cover'),
                    'docx': 'DOCX',
                    'epub': 'EPUB',
                },
            ),
        }
    if name == 'FIXED_TEXT':
        return {
            'strict': view_message('labels.FIXED_TEXT.strict'),
            'required': view_message('labels.FIXED_TEXT.required'),
            'explicit': view_message('labels.FIXED_TEXT.explicit'),
            'balanced': view_message('labels.FIXED_TEXT.balanced'),
            'research': view_message('labels.FIXED_TEXT.research'),
            True: view_message('labels.FIXED_TEXT.True'),
            False: view_message('labels.FIXED_TEXT.False'),
        }
    if name == 'FC_TEXT':
        return {
            'disabled': view_message('labels.FC_TEXT.disabled'),
            'optional': 'optional',
            'requested': view_message('labels.FC_TEXT.requested'),
        }
    if name == 'FIXED_RULES':
        return [
            ('ai_settings', 'hallucination_policy', view_message('labels.FIXED_RULES.0.2')),
            ('ai_settings', 'source_policy', view_message('labels.FIXED_RULES.1.2')),
            ('ai_settings', 'uncertainty_policy', view_message('labels.FIXED_RULES.2.2')),
            ('ai_settings', 'creativity', view_message('labels.FIXED_RULES.3.2')),
            ('ai_settings', 'web_research', view_message('labels.FIXED_RULES.4.2')),
            ('workflow', 'require_section_writing_approval', view_message('labels.FIXED_RULES.5.2')),
            ('workflow', 'require_section_approval', view_message('labels.FIXED_RULES.6.2')),
            ('workflow', 'require_chapter_approval', view_message('labels.FIXED_RULES.7.2')),
        ]
    if name == 'OUTPUT_GROUPS':
        return [
            (
                view_message('labels.OUTPUT_GROUPS.0.0'),
                ['page_size', 'margins', 'chapter_start', 'running_heads', 'page_numbers'],
            ),
            (
                view_message('labels.OUTPUT_GROUPS.1.0'),
                ['font', 'font_size', 'heading_font', 'initials', 'glossary_marks'],
            ),
            (view_message('labels.OUTPUT_GROUPS.2.0'), ['line_spacing', 'paragraph', 'hyphenation']),
            (view_message('labels.OUTPUT_GROUPS.3.0'), ['title_page', 'imprint', 'toc', 'toc_depth']),
            (view_message('labels.OUTPUT_GROUPS.4.0'), ['formats']),
        ]
    if name == 'PUBLICATION_LABELS':
        return [
            (
                'publisher',
                view_message('labels.PUBLICATION_LABELS.0.1'),
                view_message('labels.PUBLICATION_LABELS.0.2'),
            ),
            (
                'isbn_print',
                view_message('labels.PUBLICATION_LABELS.1.1'),
                view_message('labels.PUBLICATION_LABELS.1.2'),
            ),
            (
                'isbn_ebook',
                view_message('labels.PUBLICATION_LABELS.2.1'),
                view_message('labels.PUBLICATION_LABELS.2.2'),
            ),
            (
                'rights',
                view_message('labels.PUBLICATION_LABELS.3.1'),
                view_message('labels.PUBLICATION_LABELS.3.2'),
            ),
        ]
    if name == 'TEMPLATE_DE':
        return {
            'classic': view_message('labels.TEMPLATE_DE.classic'),
            'modern': 'modern',
            'plain': view_message('labels.TEMPLATE_DE.plain'),
        }
    if name == 'ROLE_DE':
        return {
            'main': view_message('labels.ROLE_DE.main'),
            'supporting': view_message('labels.ROLE_DE.supporting'),
            'minor': view_message('labels.ROLE_DE.minor'),
        }
    if name == 'SOURCE_DE':
        return {
            'series': view_message('labels.SOURCE_DE.series'),
            'copy': view_message('labels.SOURCE_DE.copy'),
            'copy_diff': view_message('labels.SOURCE_DE.copy_diff'),
            'own': view_message('labels.SOURCE_DE.own'),
        }
    if name == 'TERM_STATE_DE':
        return {
            'missing': view_message('labels.TERM_STATE_DE.missing'),
            'same': view_message('labels.TERM_STATE_DE.same'),
            'differs': view_message('labels.TERM_STATE_DE.differs'),
            'own': view_message('labels.TERM_STATE_DE.own'),
        }
    if name == 'WEB_TEXT':
        return {
            'native': view_message('labels.WEB_TEXT.native'),
            'via_tool': view_message('labels.WEB_TEXT.via_tool'),
            'none': view_message('labels.WEB_TEXT.none'),
        }
    if name == 'ACCESS_TEXT':
        return {
            'app': view_message('labels.ACCESS_TEXT.app'),
            'api': view_message('labels.ACCESS_TEXT.api'),
            'local': view_message('labels.ACCESS_TEXT.local'),
            'cli': view_message('labels.ACCESS_TEXT.cli'),
            'web': view_message('service.web_access'),
            'github': view_message('service.github_access'),
        }
    if name == 'KEEP_DE':
        return {
            'dedication': view_message('labels.KEEP_DE.dedication'),
            'foreword': view_message('labels.KEEP_DE.foreword'),
            'prologue': view_message('labels.KEEP_DE.prologue'),
            'epilogue': view_message('labels.KEEP_DE.epilogue'),
            'afterword': view_message('labels.KEEP_DE.afterword'),
            'acknowledgments': view_message('labels.KEEP_DE.acknowledgments'),
        }
    if name == 'FIELD_DE':
        return {
            'age': view_message('labels.FIELD_DE.age'),
            'appearance': view_message('labels.FIELD_DE.appearance'),
            'voice': view_message('labels.FIELD_DE.voice'),
            'short': view_message('labels.FIELD_DE.short'),
            'traits': view_message('labels.FIELD_DE.traits'),
        }
    if name == 'MARKER_LABEL':
        return {
            'anekdote': view_message('labels.MARKER_LABEL.anekdote'),
            'quelle': view_message('labels.MARKER_LABEL.quelle'),
            'medizin': view_message('labels.MARKER_LABEL.medizin'),
            'recht': view_message('labels.MARKER_LABEL.recht'),
            'kontinuitaet': view_message('labels.MARKER_LABEL.kontinuitaet'),
        }
    if name == 'MATTER_HINTS':
        return {
            'dedication': view_message('labels.MATTER_HINTS.dedication'),
            'foreword': view_message('labels.MATTER_HINTS.foreword'),
            'prologue': view_message('labels.MATTER_HINTS.prologue'),
            'epilogue': view_message('labels.MATTER_HINTS.epilogue'),
            'afterword': view_message('labels.MATTER_HINTS.afterword'),
            'glossary': view_message('labels.MATTER_HINTS.glossary'),
            'acknowledgments': view_message('labels.MATTER_HINTS.acknowledgments'),
        }
    if name == 'STYLE_DE':
        return {
            'perspective': view_message('labels.STYLE_DE.perspective'),
            'tense': view_message('labels.STYLE_DE.tense'),
            'address': view_message('labels.STYLE_DE.address'),
            'register': view_message('labels.STYLE_DE.register'),
            'tone': view_message('labels.STYLE_DE.tone'),
            'features': view_message('labels.STYLE_DE.features'),
        }
    if name == 'TIMELINE_KIND_DE':
        return {
            'jump': view_message('labels.TIMELINE_KIND_DE.jump'),
            'contradiction': view_message('labels.TIMELINE_KIND_DE.contradiction'),
            'unclear': view_message('labels.TIMELINE_KIND_DE.unclear'),
        }
    if name == 'LANGUAGE_DE':
        return {
            'long_sentence': view_message('labels.LANGUAGE_DE.long_sentence'),
            'repetition': view_message('labels.LANGUAGE_DE.repetition'),
            'same_start': view_message('labels.LANGUAGE_DE.same_start'),
            'filler': view_message('labels.LANGUAGE_DE.filler'),
        }
    raise KeyError(name)


def view_role_info():
    return [
        ('default', view_message('service.role_default'), view_message('service.hint_default')),
        ('research', view_message('service.role_research'), view_message('service.hint_research')),
        ('brainstorming', view_message('service.role_brainstorming'), ''),
        ('writing', view_message('service.role_writing'), view_message('service.hint_writing')),
        ('revision', view_message('service.role_revision'), ''),
        ('fact_check', view_message('service.role_fact_check'), view_message('service.hint_fact_check')),
        ('queue_processing', view_message('service.role_queue_processing'), view_message('service.hint_queue_processing')),
    ]


def view_provider_catalog(catalog):
    """Lokalisierte Anzeige-Metadaten; Zugang, IDs und Konfiguration bleiben unverändert."""
    import copy
    result = copy.deepcopy(catalog)
    notes = {
        'google': view_message('catalog.google.note'),
        'mistral': view_message('catalog.mistral.note'),
        'perplexity': view_message('catalog.perplexity.note'),
        'cohere': view_message('catalog.cohere.note'),
        'deepseek': view_message('catalog.deepseek.note'),
        'qwen': view_message('catalog.qwen.note'),
        'meta_llama': view_message('catalog.meta_llama.note'),
        'openrouter': view_message('catalog.openrouter.note'),
        'aws_bedrock': view_message('catalog.aws_bedrock.note'),
        'azure_ai_foundry': view_message('catalog.azure_ai_foundry.note'),
        'google_vertex': view_message('catalog.google_vertex.note'),
        'local_ollama': view_message('catalog.local_ollama.note'),
        'brave_search': view_message('catalog.brave_search.note'),
        'tavily': view_message('catalog.tavily.note'),
        'exa': view_message('catalog.exa.note'),
        'parallel': view_message('catalog.parallel.note'),
        'perplexity_sonar': view_message('catalog.perplexity_sonar.note'),
        'serpapi': view_message('catalog.serpapi.note'),
        'semantic_scholar': view_message('catalog.semantic_scholar.note'),
        'openalex': view_message('catalog.openalex.note'),
        'github_copilot_agent': view_message('catalog.github_copilot_agent.note'),
        'openai_codex': view_message('catalog.openai_codex.note'),
        'claude_code': view_message('catalog.claude_code.note'),
        'google_jules': view_message('catalog.google_jules.note'),
        'gemini_cli': view_message('catalog.gemini_cli.note'),
        'manual': view_message('catalog.manual.note'),
    }
    names = {
        'meta_llama': view_message('catalog.meta_llama.name'),
        'local_ollama': view_message('catalog.local_ollama.name'),
        'local_lmstudio': view_message('catalog.local_lmstudio.name'),
        'manual': view_message('catalog.manual.name'),
    }
    for group in ('providers', 'search_tools', 'queue_agents'):
        for service in result.get(group) or []:
            if service['id'] in notes:
                service['note'] = notes[service['id']]
            if service['id'] in names:
                service['name'] = names[service['id']]
    return result


def view_choice_labels(spec, steps):
    """Nur die eingebauten Wizard-Beschriftungen übersetzen, nie freie Auswahl-Spezifikationen."""
    labels = {
        'wizard.4': [
            (['title'], view_message('wizard.4.title', step=spec['step'].split('.')[-1], steps=steps)),
            (['subtitle'], view_message('wizard.4.subtitle')),
            (['note'], view_message('wizard.4.note')),
            (['questions', 0, 'header'], view_message('wizard.4.audience.header')),
            (['questions', 0, 'text'], view_message('wizard.4.audience.text')),
            (['questions', 0, 'options', 0, 'label'], view_message('wizard.4.audience.betroffene.label')),
            (['questions', 0, 'options', 0, 'desc'], view_message('wizard.4.audience.betroffene.desc')),
            (['questions', 0, 'options', 1, 'label'], view_message('wizard.4.audience.angehoerige.label')),
            (['questions', 0, 'options', 1, 'desc'], view_message('wizard.4.audience.angehoerige.desc')),
            (['questions', 0, 'options', 2, 'label'], view_message('wizard.4.audience.fachpublikum.label')),
            (['questions', 0, 'options', 2, 'desc'], view_message('wizard.4.audience.fachpublikum.desc')),
            (['questions', 0, 'options', 3, 'label'], view_message('wizard.4.audience.allgemein.label')),
            (['questions', 0, 'options', 3, 'desc'], view_message('wizard.4.audience.allgemein.desc')),
            (['questions', 1, 'header'], view_message('wizard.4.prior_knowledge.header')),
            (['questions', 1, 'text'], view_message('wizard.4.prior_knowledge.text')),
            (['questions', 1, 'options', 0, 'label'], view_message('wizard.4.prior_knowledge.keines.label')),
            (['questions', 1, 'options', 0, 'desc'], view_message('wizard.4.prior_knowledge.keines.desc')),
            (['questions', 1, 'options', 1, 'label'], view_message('wizard.4.prior_knowledge.grundlagen.label')),
            (['questions', 1, 'options', 1, 'desc'], view_message('wizard.4.prior_knowledge.grundlagen.desc')),
            (['questions', 1, 'options', 2, 'label'], view_message('wizard.4.prior_knowledge.fachlich.label')),
            (['questions', 1, 'options', 2, 'desc'], view_message('wizard.4.prior_knowledge.fachlich.desc')),
        ],
        'wizard.5': [
            (['title'], view_message('wizard.5.title', step=spec['step'].split('.')[-1], steps=steps)),
            (['subtitle'], view_message('wizard.5.subtitle')),
            (['note'], view_message('wizard.5.note')),
            (['questions', 0, 'header'], view_message('wizard.5.book_type.header')),
            (['questions', 0, 'text'], view_message('wizard.5.book_type.text')),
            (['questions', 0, 'options', 0, 'label'], view_message('wizard.5.book_type.sachbuch.label')),
            (['questions', 0, 'options', 0, 'desc'], view_message('wizard.5.book_type.sachbuch.desc')),
            (['questions', 0, 'options', 1, 'label'], view_message('wizard.5.book_type.ratgeber.label')),
            (['questions', 0, 'options', 1, 'desc'], view_message('wizard.5.book_type.ratgeber.desc')),
            (['questions', 0, 'options', 2, 'label'], view_message('wizard.5.book_type.fachbuch.label')),
            (['questions', 0, 'options', 2, 'desc'], view_message('wizard.5.book_type.fachbuch.desc')),
            (['questions', 0, 'options', 3, 'label'], view_message('wizard.5.book_type.erfahrungsbericht.label')),
            (['questions', 0, 'options', 3, 'desc'], view_message('wizard.5.book_type.erfahrungsbericht.desc')),
            (['questions', 1, 'header'], view_message('wizard.5.length.header')),
            (['questions', 1, 'text'], view_message('wizard.5.length.text')),
            (['questions', 1, 'options', 0, 'label'], view_message('wizard.5.length.kurz.label')),
            (['questions', 1, 'options', 0, 'desc'], view_message('wizard.5.length.kurz.desc')),
            (['questions', 1, 'options', 1, 'label'], view_message('wizard.5.length.mittel.label')),
            (['questions', 1, 'options', 1, 'desc'], view_message('wizard.5.length.mittel.desc')),
            (['questions', 1, 'options', 2, 'label'], view_message('wizard.5.length.lang.label')),
            (['questions', 1, 'options', 2, 'desc'], view_message('wizard.5.length.lang.desc')),
            (['questions', 1, 'options', 3, 'label'], view_message('wizard.5.length.offen.label')),
            (['questions', 1, 'options', 3, 'desc'], view_message('wizard.5.length.offen.desc')),
        ],
        'wizard.6': [
            (['title'], view_message('wizard.6.title', step=spec['step'].split('.')[-1], steps=steps)),
            (['subtitle'], view_message('wizard.6.subtitle')),
            (['note'], view_message('wizard.6.note')),
            (['questions', 0, 'header'], view_message('wizard.6.language.header')),
            (['questions', 0, 'text'], view_message('wizard.6.language.text')),
            (['questions', 0, 'options', 0, 'label'], view_message('wizard.6.language.de.label')),
            (['questions', 0, 'options', 1, 'label'], view_message('wizard.6.language.en.label')),
            (['questions', 0, 'options', 2, 'label'], view_message('wizard.6.language.fr.label')),
            (['questions', 0, 'options', 3, 'label'], view_message('wizard.6.language.es.label')),
            (['questions', 1, 'header'], view_message('wizard.6.style.header')),
            (['questions', 1, 'text'], view_message('wizard.6.style.text')),
            (['questions', 1, 'options', 0, 'label'], view_message('wizard.6.style.sachlich.label')),
            (['questions', 1, 'options', 0, 'desc'], view_message('wizard.6.style.sachlich.desc')),
            (['questions', 1, 'options', 1, 'label'], view_message('wizard.6.style.zugewandt.label')),
            (['questions', 1, 'options', 1, 'desc'], view_message('wizard.6.style.zugewandt.desc')),
            (['questions', 1, 'options', 2, 'label'], view_message('wizard.6.style.erzaehlend.label')),
            (['questions', 1, 'options', 2, 'desc'], view_message('wizard.6.style.erzaehlend.desc')),
            (['questions', 1, 'options', 3, 'label'], view_message('wizard.6.style.humorvoll.label')),
            (['questions', 1, 'options', 3, 'desc'], view_message('wizard.6.style.humorvoll.desc')),
        ],
        'wizard.12': [
            (['title'], view_message('wizard.12.title', step=spec['step'].split('.')[-1], steps=steps)),
            (['subtitle'], view_message('wizard.12.subtitle')),
            (['note'], view_message('wizard.12.note')),
            (['questions', 0, 'header'], view_message('wizard.12.auto_merge.header')),
            (['questions', 0, 'text'], view_message('wizard.12.auto_merge.text')),
            (['questions', 0, 'options', 0, 'label'], view_message('wizard.12.auto_merge.true.label')),
            (['questions', 0, 'options', 0, 'desc'], view_message('wizard.12.auto_merge.true.desc')),
            (['questions', 0, 'options', 1, 'label'], view_message('wizard.12.auto_merge.false.label')),
            (['questions', 0, 'options', 1, 'desc'], view_message('wizard.12.auto_merge.false.desc')),
        ],
        'wizard.13': [
            (['title'], view_message('wizard.13.title', step=spec['step'].split('.')[-1], steps=steps)),
            (['subtitle'], view_message('wizard.13.subtitle')),
            (['note'], view_message('wizard.13.note')),
            (['questions', 0, 'header'], view_message('wizard.13.translations.header')),
            (['questions', 0, 'text'], view_message('wizard.13.translations.text')),
            (['questions', 0, 'options', 0, 'label'], view_message('wizard.13.translations.keine.label')),
            (['questions', 0, 'options', 1, 'label'], view_message('wizard.13.translations.en.label')),
            (['questions', 0, 'options', 2, 'label'], view_message('wizard.13.translations.fr.label')),
            (['questions', 0, 'options', 3, 'label'], view_message('wizard.13.translations.es.label')),
            (['questions', 0, 'options', 4, 'label'], view_message('wizard.13.translations.it.label')),
        ],
        'wizard.14': [
            (['title'], view_message('wizard.14.title', step=spec['step'].split('.')[-1], steps=steps)),
            (['subtitle'], view_message('wizard.14.subtitle')),
            (['note'], view_message('wizard.14.note')),
            (['questions', 0, 'header'], view_message('wizard.14.ai_disclosure.header')),
            (['questions', 0, 'text'], view_message('wizard.14.ai_disclosure.text')),
            (['questions', 0, 'options', 0, 'label'], view_message('wizard.14.ai_disclosure.short.label')),
            (['questions', 0, 'options', 0, 'desc'], view_message('wizard.14.ai_disclosure.short.desc')),
            (['questions', 0, 'options', 1, 'label'], view_message('wizard.14.ai_disclosure.detailed.label')),
            (['questions', 0, 'options', 1, 'desc'], view_message('wizard.14.ai_disclosure.detailed.desc')),
            (['questions', 0, 'options', 2, 'label'], view_message('wizard.14.ai_disclosure.custom.label')),
            (['questions', 0, 'options', 2, 'desc'], view_message('wizard.14.ai_disclosure.custom.desc')),
            (['questions', 0, 'options', 3, 'label'], view_message('wizard.14.ai_disclosure.none.label')),
        ],
    }
    import copy
    result = copy.deepcopy(spec)
    for path, value in labels.get(spec.get('step'), []):
        target = result
        for key in path[:-1]:
            target = target[key]
        target[path[-1]] = value
    return result


def display_status(code):
    return f'{STATUS_ICON.get(code, "•")} {view_status(code)}'


def limit_row_text(row):
    if UI.get('language') != 'en' or not {'key', 'used', 'total', 'left_pct'} <= row.keys():
        return row['text']
    labels = {'ai_budget': view_message('limit.ai_budget'), 'actions_minutes': view_message('limit.actions_minutes'),
              'api_rate': view_message('limit.api_rate')}
    key = row['key']
    unit = ' €' if key == 'ai_budget' else ' min' if key == 'actions_minutes' else ''
    fmt = (lambda n: f'{n:,.2f}') if key == 'ai_budget' else (lambda n: str(int(n)))
    return view_message('limit.row', label=labels.get(key, key), percent=round(row['left_pct']),
                        used=fmt(row['used']), total=fmt(row['total']), unit=unit)


def view_usage_task(task):
    return {'Recherche': view_message('disclosure.task_research'), 'Ideensammlung': view_message('disclosure.task_brainstorming'),
            'Textentwürfe': view_message('disclosure.task_writing'), 'Faktenprüfung': view_message('disclosure.task_fact_check')}.get(task, task)


def view_service_names(ids, names):
    named = sorted({names.get(i, i) for i in ids if i != 'chat'})
    if 'chat' in ids:
        named.append(view_message('disclosure.chat_assistant'))
    return named[0] if len(named) == 1 else ', '.join(named[:-1]) + view_message('disclosure.and') + named[-1] if named else ''


def view_import_keep(info):
    values = {'first_edition': view_message('import.keep_first'), '30': view_message('import.keep_30'),
              '90': view_message('import.keep_90'), 'forever': view_message('import.keep_forever')}
    return values.get(str(info.get('keep')), info.get('keep_text', ''))


class RenderedWidget(str):
    """Widget-Ausgabe samt unveränderten Rohdaten für alternative native Ansichten."""
    def __new__(cls, text, template, data):
        value = super().__new__(cls, text)
        value.template, value.data = template, data
        return value


def fill(template, values, blocks=None):
    """Widget-Code: Ladezeile für ghostwriter-ui und GW.render mit den Daten.
    Maskieren, Wiederholblöcke und data-gw-if erledigt gw.js im Chat."""
    data = dict(values)
    data.update(blocks or {})
    data['LANGUAGE'] = UI.get('language', 'de')
    if UI.get('head'):
        data['HEAD_SHA'] = UI['head']  # gelesener Stand; gw.js schickt ihn als expected_head_sha zurück
    payload = json.dumps(data, ensure_ascii=False, separators=(',', ':')).replace('</', '<\\/')
    url = UI_URL.format(repo=UI['repo'], ref=UI['ref'])
    return RenderedWidget((f'<div id="gw"></div>\n<script src="{url}"></script>\n'
            f'<script>GW.render({json.dumps(template[:-5])},{payload})</script>\n'), template[:-5], data)


# ---------- Textfassung (Chats ohne Widgets) ----------

STATUS_DE = {'planned': 'geplant', 'in_progress': 'in Arbeit', 'ready_for_assembly': 'bereit zum Zusammenführen',
             'assembly': 'wird zusammengeführt', 'review': 'Durchsicht', 'ready_for_approval': 'bereit zur Freigabe',
             'approved': 'freigegeben', 'research': 'Recherche', 'brainstorming': 'Ideensammlung',
             'ready_to_write': 'bereit zum Schreiben', 'writing': 'Schreiben', 'revision': 'Überarbeitung',
             'fact_check': 'Faktencheck'}
STATUS_ICON = {'planned': '⚪', 'research': '🔎', 'brainstorming': '💡', 'ready_to_write': '🟦', 'writing': '✏️',
               'in_progress': '✏️', 'revision': '🔁', 'fact_check': '🔍', 'review': '🔍', 'ready_for_assembly': '🟡',
               'assembly': '🧩', 'ready_for_approval': '🟡', 'approved': '✅'}
MARKER_ICON = {'anekdote': '💬', 'quelle': '📚', 'medizin': '🩺', 'recht': '⚖️', 'kontinuitaet': '🔗'}
MARKER_LEGEND = 'Marker: 💬 Anekdote · 📚 Quelle prüfen · 🩺 Medizin prüfen · ⚖️ Recht prüfen · 🔗 Kontinuität prüfen'


def status_text(st):
    return f'{STATUS_ICON.get(st, "•")} {STATUS_DE.get(st, st)}'


def progress_bar(approved, total):
    """Zehn Segmente; ohne Abschnitte keinen scheinbaren Fortschritt anzeigen."""
    if not total:
        return '–'
    filled = min(10, max(0, approved * 10 // total))
    return '▰' * filled + '▱' * (10 - filled)


def overview_summary(base, config, cnum=None, language='de'):
    """Freigaben aus Abschnittsdateien; Navigation erteilt keine Freigabe."""
    chapters = config['structure']['chapters']
    entries = []
    for ci, ch in enumerate(chapters, 1):
        if cnum is not None and ci != cnum:
            continue
        for si, section in enumerate(ch['sections'], 1):
            head, _, _, manuscript = section_file(base, section)
            entries.append((f'{ci}.{si}', section['id'], head['status'],
                            sum(marker_counts(manuscript).values())))
    approved = sum(e[2] == 'approved' for e in entries)
    drafts = sum(e[2] not in ('approved', 'planned') for e in entries)
    markers = sum(e[3] for e in entries)
    en = language == 'en'
    bar = progress_bar(approved, len(entries))
    section_unit = 'section' if len(entries) == 1 else 'sections'
    german_unit = 'Abschnitt' if len(entries) == 1 else 'Abschnitten'
    lines = [f'**Approved:** {bar} {approved} of {len(entries)} {section_unit} · **In progress:** {drafts}' if en else
             f'**Freigegeben:** {bar} {approved} von {len(entries)} {german_unit} · **In Arbeit:** {drafts}']
    if markers:
        marker_unit = 'marker' if markers == 1 else 'markers'
        lines.append(f'**Open:** {markers} {marker_unit} to check' if en else f'**Offen:** {markers} Marker prüfen')
    current = (config.get('workflow') or {}).get('current_section_id')
    target = next((e for e in entries if e[1] == current and e[2] != 'approved'), None)
    target = target or next((e for e in entries if e[2] != 'approved'), None)
    if target:
        lines.append(f'**Current:** {target[0]} · {display_status(target[2])}' if en else
                     f'**Aktuell:** {target[0]} · {display_status(target[2])}')
        lines.append(f'**Next step:** `{target[0]}` Open section' if en else
                     f'**Nächster Schritt:** `{target[0]}` Abschnitt öffnen')
    elif not entries:
        key = 'N' if cnum is not None or not chapters else '1'
        action = ('Add section' if cnum is not None else 'Add chapter' if not chapters else 'Open chapter') if en else ('Abschnitt anlegen' if cnum is not None else 'Kapitel anlegen' if not chapters else 'Kapitel öffnen')
        lines.append(f'**Next step:** `{key}` {action}' if en else f'**Nächster Schritt:** `{key}` {action}')
    else:
        lines.append('**All sections approved.** Chapter and edition approvals remain separate.' if en else
                     '**Alle Abschnitte freigegeben.** Kapitel- und Auflagenfreigaben bleiben gesondert.')
    return lines + ['']


def menu(items, intro=None):
    """items: [(kürzel, text)] -> Aktionszeile mit Kürzeln als Inline-Code."""
    intro = view_message('menu.prompt') if intro is None else intro
    primary = ' · '.join(f'`{k}` {t}' for k, t in items[:3])
    more = ' · '.join(f'`{k}` {t}' for k, t in items[3:])
    more_label = 'More actions' if UI.get('language') == 'en' else 'Weitere Aktionen'
    return f'**{intro}:**  \n' + primary + (f'\n\n**{more_label}:** ' + more if more else '')


def field_table(rows):
    out = [view_message('field_table'), '|---|---|']
    for label, value in rows:
        v = str(value).replace('\n', ' ').replace('|', '\\|') if value not in ('', None) else view_message('empty')
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
                parts.append({'PART_KIND': kind, 'PART_TITLE': i['title'] if i else view_matter_kind(kind), 'PART_AREA': area,
                              'PART_ID': i['id'] if i else '', 'PART_STATUS': section_file(base, i)[0]['status'] if i else '',
                              'PART_HINT': view_labels('MATTER_HINTS')[kind]})
            return fill('vor-nachspann.html', {'PROJECT_TITLE_SHORT': short}, {'PARTS': parts})
        lines = [view_message('view.matter.front_and_back_matter'), '', view_message('view.matter.part_area_status'), '|---|---|---|']
        for kind, (area, title, _) in MATTER.items():
            i = have.get(kind)
            state = display_status(section_file(base, i)[0]['status']) if i else view_message('view.matter.not_created')
            lines.append(f'| {i["title"] if i else view_matter_kind(kind)} | {view_message('view.matter.front_matter') if area == "front" else view_message('view.matter.back_matter')} | {state} |')
        lines += ['', view_message('view.matter.only_approved_parts_enter_an_edition_you'), '', '---']
        items = [(i['title'], view_message('view.matter.open')) for _, i in matter_items(config)]
        items += [(f'+ {view_matter_kind(kind)}', view_message('view.matter.create')) for kind, (_, title, _) in MATTER.items() if kind not in have]
        items.append(('Ü', view_message('view.matter.back_to_overview')))
        return '\n'.join(lines + [menu(items)]) + '\n'
    item = find_matter(config, args.where)
    if not item:
        have = ', '.join(i['title'] for _, i in matter_items(config)) or view_message('view.matter.none')
        return (view_message('view.matter.the_book_does_not_yet_contain_available', p_a=args.where, p_b=have))
    head, goal, _, ms = section_file(base, item)
    kind = item['kind']
    area = view_message('view.matter.front_matter') if MATTER[kind][0] == 'front' else view_message('view.matter.back_matter')
    markers = [(KIND[m.group(1)], (m.group(2) or '').strip() or '–') for m in MARKER_TEXT.finditer(ms)]
    yn = lambda v: view_message('view.matter.yes') if v else view_message('view.matter.no')
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
                  'MARKER_COUNT_TEXT': view_message('view.matter.no_open_markers') if not n else view_message('view.matter.open_marker', p_a=n, p_b=view_plural(n, 'r', german_singular=True)),
                  'APPROVAL_WRITING': str(bool(head['approvals']['writing'])).lower(),
                  'APPROVAL_SECTION': str(bool(head['approvals']['section'])).lower(),
                  'SIGNED': '1' if kind in MATTER_SIGNED else '', 'BYLINE': head.get('byline') or '',
                  'PLACE_DATE': head.get('place_date') or '', 'GLOSSARY': '1' if kind == 'glossary' else '',
                  'GLOSSARY_INTRO': intro, 'RESEARCH': '1' if kind in MATTER_RESEARCH else '',
                  'GHOSTWRITING': '1' if kind in MATTER_GHOSTWRITING else '',
                  'PERSONAL_NOTE': (view_message('view.matter.personal_part_you_write_the_text_yourself')) if kind in ('dedication', 'acknowledgments') else ''}
        blocks = {'MARKERS': [{'MARKER_TYPE': k, 'MARKER_LABEL': view_labels('MARKER_LABEL')[k], 'MARKER_TEXT': v} for k, v in markers],
                  'GLOSSARY_ENTRIES': [{'G_TERM': t, 'G_TEXT': e} for t, e in sorted(entries, key=lambda x: german_key(x[0]))]}
        st = series_terms(base, config, entries) if kind == 'glossary' else []
        if st:   # Begriffe der Serie (#116)
            values.update({'SERIES_ID': config['_series']['id'], 'SERIES_TITLE': config['_series']['title']})
            blocks['SERIES_TERMS'] = [{'T_TERM': x['term'], 'T_TEXT': x['text'] or x['book_text'], 'T_BOOK_TEXT': x['book_text'],
                                       'T_STATE': x['state'], 'T_STATE_TEXT': view_labels('TERM_STATE_DE')[x['state']]} for x in st]
        return fill('teil-bearbeiten.html', values, blocks)
    lines = [f'### 📜 {item["title"]}', f'{area} · {display_status(head["status"])}', '',
             '| | |', '|---|---|', view_message('view.matter.goal', p_a=goal or view_message('view.matter.not_set')),
             view_message('view.matter.writing_approval', p_a=yn(head["approvals"]["writing"])),
             view_message('view.matter.approved', p_a=yn(head["approvals"]["section"]))]
    if kind in MATTER_SIGNED:
        lines += [view_message('view.matter.byline', p_a=head.get("byline") or view_message('view.matter.the_book_s_author')),
                  view_message('view.matter.place_date', p_a=head.get("place_date") or view_message('view.matter.unspecified'))]
    lines.append('')
    if markers:
        lines += [view_message('view.matter.open_markers', p_a=len(markers))] + [f'- {MARKER_ICON[k]} {view_labels('MARKER_LABEL')[k]}: {v}' for k, v in markers] + ['']
    if kind == 'glossary':
        intro, entries = glossary_entries('' if ms in EMPTY_MANUSCRIPT else ms)
        dup = glossary_duplicates(entries)
        lines += ['---', '']
        if intro:
            lines += [intro, '']
        if entries:
            lines += [view_message('view.matter.term_alphabetical_in_the_book', p_a=len(entries), p_b=view_plural(len(entries), 'e')), '',
                      view_message('view.matter.term_explanation'), '|---|---|']
            lines += [f'| {t}{view_message('view.matter.duplicate') if t in dup else ""} | {e} |' for t, e in sorted(entries, key=lambda x: german_key(x[0]))]
        else:
            lines += [view_message('view.matter.no_terms_yet')]
        st = series_terms(base, config, entries)
        if st:
            lines += ['', view_message('view.matter.terms_from_series', p_a=config["_series"]["title"]), '', view_message('view.matter.term_status_series_explanation'), '|---|---|---|']
            lines += [f'| {x["term"]} | {"⚠️ " if x["state"] == "differs" else ""}{view_labels('TERM_STATE_DE')[x["state"]]} | {x["text"] or "–"} |' for x in st]
            lines += ['', view_message('view.matter.b_term_copy_from_series_into_book')]
        lines += ['', '---']
        items = [(view_message('view.matter.term_explanation_2'), view_message('view.matter.add')), (view_message('view.matter.term_new_explanation'), view_message('view.matter.edit')), (view_message('view.matter.term'), view_message('view.matter.remove')),
                 ('VB', view_message('view.matter.suggest_terms_from_approved_text')), ('F', view_message('view.matter.title_goal_and_introduction'))]
    else:
        lines += ['---', '', ms or view_message('view.matter.no_text_yet'), '', '---']
        items = [('T', view_message('view.matter.edit_text_send_the_revised_text')),
                 ('F', view_message('view.matter.title_goal_byline_place_and_date') if kind in MATTER_SIGNED else view_message('view.matter.title_and_goal'))]
    items += [('FS', view_message('view.matter.withdraw_writing_permission') if head['approvals']['writing'] else view_message('view.matter.grant_writing_permission')),
              ('FA', view_message('view.matter.withdraw_approval') if head['approvals']['section'] else view_message('view.matter.approve', p_a=item["title"]))]
    if kind in MATTER_RESEARCH:
        items.append(('RS', view_message('view.matter.research_each_term') if kind == 'glossary' else view_message('view.matter.research_now')))
    if kind in MATTER_GHOSTWRITING:
        items.append(('GS', view_message('view.matter.ghostwriting_now')))
    items += [('FV', view_message('view.matter.suggest_characters_from_the_text')), ('Ü', view_message('view.matter.back_to_overview'))]
    lines += [menu(items)]
    return '\n'.join(lines) + '\n'


TERM_STATE_DE = {'missing': 'nur in der Serie (gilt per Verweis)', 'same': 'im Buch, gleich wie Serie',
                 'differs': 'im Buch, weicht von der Serie ab', 'own': 'nur in diesem Buch'}


def series_terms(base, config, entries):
    """Begriffe der Serie im Vergleich zum Glossar dieses Bandes (#116); ohne Serie leer."""
    ser = config.get('_series')
    if not ser:
        return []
    import series
    terms = series.glossary(base, ser['id'])
    return series.compare_terms(entries, terms) if terms else []


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
             'I_SOURCE': {'chat': view_message('view.images.generated_in_chat'), 'copy': view_message('view.images.copied_prompt'), 'own': view_message('view.images.own_image')}.get(v[0].get('source'), ''),
             'I_SIZE': f'{v[0]["width_px"]} × {v[0]["height_px"]} px' if v[0].get('width_px') else '',
             'I_IN_TEXT': '1' if iid in used else ''} for iid, v in imgs]
    chars = [names.get(c, c) for c in head.get('characters') or []]
    if args.text:
        lines = [view_message('view.images.images', p_a=target["title"]), '',
                 view_message('view.images.book_image_style_characters_in_section', p_a=style or view_message('view.images.none_yet_images_style'), p_b=", ".join(chars) or "–"), '']
        if rows:
            lines += [view_message('view.images.image_caption_status_source_in_text'), '|---|---|---|---|---|']
            lines += [f'| `{r["I_ID"]}` | {r["I_CAPTION"] or "–"} | {view_message('view.images.approved') if r["I_STATE"] == "approved" else view_message('view.images.draft')} | '
                      f'{r["I_SOURCE"]} | {view_message('view.images.yes') if r["I_IN_TEXT"] else view_message('view.images.no')} |' for r in rows]
        else:
            lines += [view_message('view.images.no_images_yet')]
        lines += ['', '---', menu([('BI', view_message('view.images.image_prompt_describe_the_scene_scene')), ('BH', view_message('view.images.upload_image_attach_a_file'))]
                                 + [(f'FB {r["I_ID"]}', view_message('view.images.approve') if r['I_STATE'] != 'approved' else view_message('view.images.withdraw_approval')) for r in rows]
                                 + [('Ü', view_message('view.images.back_to_overview'))])]
        return '\n'.join(lines) + '\n'
    p = config['project']
    values = {'PROJECT_TITLE_SHORT': p.get('title_short') or p.get('title') or '', 'TARGET_ID': target['id'],
              'TARGET_TITLE': target['title'], 'IMAGE_STYLE': style, 'TARGET_CHARACTERS': ', '.join(chars)}
    return fill('bilder.html', values, {'IMAGES': rows})


SOURCE_DE = {'series': 'aus der Serie', 'copy': 'Kopie der Serie (gleich)', 'copy_diff': 'Kopie, weicht von der Serie ab',
             'own': 'nur in diesem Buch'}


def character_source(config, item):
    """Herkunft einer Figur in einem Band einer Serie (#116): series | copy | copy_diff | own; ohne Serie leer."""
    if not config.get('_series'):
        return ''
    if '_series' in item:
        return 'series'
    if item.get('_copy_of'):
        return 'copy_diff' if item.get('_differs') else 'copy'
    return 'own'


def characters_view(base, config, args):
    """Figuren (#53): ohne Angabe die Liste (Vorlage figuren), sonst eine Figur (Vorlage figur-bearbeiten)."""
    p = config['project']
    ser = config.get('_series') or {}
    short = p.get('title_short') or p.get('title') or p.get('working_title') or ''
    items = character_items(config)
    used = character_usage(base, config)
    names = {i['id']: i['name'] for i in items}
    if not args.where:
        rows = []
        for i in items:
            head = character_file(base, i)[0]
            src = character_source(config, i)
            rows.append({'C_ID': i['id'], 'C_NAME': i['name'], 'C_ROLE': view_labels('ROLE_DE').get(head.get('role'), ''),
                         'C_SHORT': head.get('short', ''), 'C_USED': ', '.join(used.get(i['id'], [])) or '–',
                         'C_SOURCE': src, 'C_SOURCE_TEXT': view_labels('SOURCE_DE').get(src, '')})
        if args.text:
            lines = [view_message('view.characters.characters'), ''] + ([view_message('view.characters.volume_of_series_series_characters_apply_to', p_a=ser["title"]), ''] if ser else [])
            if rows:
                lines += [view_message('view.characters.character_role_short_description_appears_in') + (view_message('view.characters.source') if ser else ''),
                          '|---|---|---|---|' + ('---|' if ser else '')]
                lines += [f'| {r["C_NAME"]} | {r["C_ROLE"]} | {r["C_SHORT"] or "–"} | {r["C_USED"]} |'
                          + (f' {"⚠️ " if r["C_SOURCE"] == "copy_diff" else ""}{r["C_SOURCE_TEXT"]} |' if ser else '') for r in rows]
            else:
                lines += [view_message('view.characters.no_characters_yet')]
            lines += ['', view_message('view.characters.characters_provide_working_references_for_brainstorming_and'), '', '---']
            lines += [menu([(r['C_NAME'], view_message('view.characters.open')) for r in rows] + [(view_message('view.characters.name'), view_message('view.characters.create_a_character_optional_role_supporting')), ('FV', view_message('view.characters.suggest_characters_from_the_text')),
                                                                     ('Ü', view_message('view.characters.back_to_overview'))])]
            return '\n'.join(lines) + '\n'
        return fill('figuren.html', {'PROJECT_TITLE_SHORT': short, 'SERIES_TITLE': ser.get('title', '')}, {'CHARACTERS': rows})
    item = find_character(config, args.where)
    if not item:
        return view_message('view.characters.there_is_no_character_available', p_a=args.where, p_b=", ".join(names.values()) or view_message('view.characters.none'))
    head, desc, notes = character_file(base, item)
    rel = [{'R_TO': r['to'], 'R_NAME': names.get(r['to'], r['to']), 'R_KIND': r['kind']} for r in head.get('relations') or []]
    if args.text:
        rows = [(view_message('view.characters.role'), view_labels('ROLE_DE').get(head.get('role'), '')), (view_message('view.characters.brief_description'), head.get('short')), (view_message('view.characters.age'), head.get('age')),
                (view_message('view.characters.appearance'), head.get('appearance')), (view_message('view.characters.traits'), ', '.join(head.get('traits') or [])),
                (view_message('view.characters.speech'), head.get('voice')), (view_message('view.characters.image_description'), head.get('visual')),
                (view_message('view.characters.relationships'), '; '.join(view_message('view.characters.of', p_a=r["R_KIND"], p_b=r["R_NAME"]) for r in rel)),
                (view_message('view.characters.appears_in'), ', '.join(used.get(item['id'], [])))]
        src = character_source(config, item)
        if src:
            rows.append((view_message('view.characters.source_2'), view_labels('SOURCE_DE')[src] + view_message('view.characters.series', p_a=ser["title"])))
        lines = [f'### 🎭 {item["name"]}', '', '| | |', '|---|---|'] + [f'| {k} | {v or "–"} |' for k, v in rows]
        lines += ['', view_message('view.characters.description'), '', desc or view_message('view.characters.not_set')]
        if notes:
            lines += ['', view_message('view.characters.notes'), '', notes]
        lines += ['', '---', view_message('view.characters.reply_with_field_new_value_e_g')]
        extra = {'series': [('KO', view_message('view.characters.copy_for_this_book_only'))], 'copy': [('AN', view_message('view.characters.align_with_series')), ('IS', view_message('view.characters.apply_to_series'))],
                 'copy_diff': [('AN', view_message('view.characters.align_with_series')), ('IS', view_message('view.characters.apply_to_series'))], 'own': [('IS', view_message('view.characters.apply_to_series'))]}.get(src)
        if extra:
            lines += ['', (view_message('view.characters.changes_apply_to_all_volumes_in_the') if src == 'series' else '') + menu(extra, view_message('view.characters.series_2'))]
        return '\n'.join(lines) + '\n'
    values = {'PROJECT_TITLE_SHORT': short, 'CHARACTER_ID': item['id'], 'CHARACTER_NAME': item['name'],
              'CHARACTER_ROLE': head.get('role', 'main'), 'CHARACTER_SHORT': head.get('short', ''),
              'CHARACTER_AGE': head.get('age', ''), 'CHARACTER_APPEARANCE': head.get('appearance', ''),
              'CHARACTER_TRAITS': ', '.join(head.get('traits') or []), 'CHARACTER_VOICE': head.get('voice', ''),
              'CHARACTER_VISUAL': head.get('visual', ''), 'CHARACTER_DESCRIPTION': desc, 'CHARACTER_NOTES': notes,
              'CHARACTER_USED': ', '.join(used.get(item['id'], [])) or view_message('view.characters.nowhere_yet')}
    src = character_source(config, item)
    values.update({'CHARACTER_SOURCE': src, 'CHARACTER_SOURCE_TEXT': view_labels('SOURCE_DE').get(src, ''),
                   'SERIES_ID': ser.get('id', ''), 'SERIES_TITLE': ser.get('title', '')})
    others = [{'O_ID': i['id'], 'O_NAME': i['name']} for i in items if i['id'] != item['id']]
    return fill('figur-bearbeiten.html', values, {'RELATIONS': rel, 'OTHERS': others})


def current_branch(base, args):
    """Buch-Branch: --branch, sonst der ausgecheckte Branch des Projektordners."""
    if getattr(args, 'branch', None) and args.branch != 'main':
        return args.branch
    r = subprocess.run(['git', 'rev-parse', '--abbrev-ref', 'HEAD'], cwd=base, capture_output=True, text=True)
    return r.stdout.strip() if r.returncode == 0 and r.stdout.strip() != 'HEAD' else args.branch


def book_series(base, args):
    """(serie, band) des Buchs vom Standard-Branch (#116) oder (None, None)."""
    import series
    try:
        return series.of(series.load_all(base), current_branch(base, args))
    except Exception:   # noqa: BLE001 – ohne Git bzw. Bibliothek keine Serie
        return None, None


def limit_state(base, config, args):
    """(state, text) aus --limits (JSON von limits.py check --json) bzw. ohne Angabe aus den Kosten des Monats (#62)."""
    path = getattr(args, 'limits', None)
    if path:
        data = json.loads(Path(path).read_text(encoding='utf-8'))
        return data.get('state') or 'ok', data.get('text') or ''
    import limits
    rows = limits.evaluate(base, config)
    for state, message in [('pause', lambda details: view_message('limit.paused', details=details)),
                           ('warn', lambda details: view_message('limit.warning', details=details))]:
        selected = [limit_row_text(r) for r in rows if r['state'] == state]
        if selected:
            return state, message('; '.join(selected))
    return 'ok', ''


def limit_summary(base, config):
    import limits
    rows = limits.evaluate(base, config)
    return ('; '.join(limit_row_text(r) for r in rows) + '.') if rows else view_message('view.limit_summary.no_limits_configured')


# Hintergrundläufe (#123, #124): Kürzel und Symbol je Art in der Textfassung der Projektübersicht
ANALYSIS_KEY = {'characters': 'FA', 'summaries': 'KA', 'style': 'SA', 'places': 'OA', 'timeline': 'ZA', 'continuity': 'WA', 'language': 'SPA'}
ANALYSIS_EMOJI = {'characters': '👤', 'summaries': '📝', 'style': '🪶', 'places': '📍', 'timeline': '🕰️', 'continuity': '🔗', 'language': '✍️'}


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
    try:   # Vorschläge aus Hintergrundläufen (#123, #124), je Art ein Hinweis
        import analyze
        open_runs = [(k, h, analyze.KINDS[k]) for k, h in analyze.latest_all(base)]
    except Exception:   # noqa: BLE001
        open_runs = []
    analyses = [{'A_KIND': k, 'A_RUN': h['path'][:-3] + '.json', 'A_ICON': spec['icon'],
                 'A_COUNT': h.get('suggestions', 0), 'A_DATE': str(h.get('created_at') or ''),
                 'A_TEXT': f'{spec["offer"]} vom {de_date(str(h.get("created_at")))} liegen bereit ({h.get("suggestions", 0)})'}
                for k, h, spec in open_runs]
    try:   # Import (#124): Original wird bald entfernt
        import import_book
        imp = import_book.status(base)
    except Exception:   # noqa: BLE001
        imp = None
    if imp and imp.get('soon') and not imp.get('removed'):
        values['IMPORT_SOURCE'], values['IMPORT_EXPIRES'] = Path(imp['source']).name, imp['expires']
        values['IMPORT_TEXT'] = (f'Das Original des Imports ({Path(imp["source"]).name}) wird am '
                                 f'{de_date(imp["expires"])} entfernt (Aufbewahrung {imp["keep_text"]}).')
    ser, vol = book_series(base, args)
    if ser:   # Serie (#116): „Band 2 der Serie …“ mit Link
        values.update({'SERIES_ID': ser['id'], 'SERIES_TITLE': ser['title'], 'SERIES_VOLUME_NUMBER': vol,
                       'SERIES_TEXT': f'Band {vol} der Serie „{ser["title"]}“'})
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
        lines += overview_summary(base, config)
        if changes:
            lines += [f'> ⏳ **{values["PENDING_TEXT"]} noch nicht übernommen** (Änderungspaket #{changes["pull_request"]}) · `M` übernehmen', '']
        if ser:
            lines += [f'📚 {values["SERIES_TEXT"]} · `S` Serie', '']
        for a in analyses:
            lines += [f'> {ANALYSIS_EMOJI.get(a["A_KIND"], "🔎")} **{a["A_TEXT"]}** · `{ANALYSIS_KEY.get(a["A_KIND"], "AN")}` ansehen', '']
        if values.get('IMPORT_TEXT'):
            lines += [f'> 📥 {values["IMPORT_TEXT"]}', '']
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
            lines += [f'| {r["CHAPTER_NUMBER"]} | {r["CHAPTER_TITLE"]} | {r["CHAPTER_COST"]} | {display_status(r["CHAPTER_STATUS"])} | `✎ B{r["CHAPTER_NUMBER"]}` |' for r in rows]
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
            items.append(('M', 'Buchänderungen übernehmen'))
        if upd:
            items.append(('U', 'GhostWriter aktualisieren'))
        if lib_count >= 2:
            items.append(('L', f'Bücherregal ({lib_count} Bücher)'))
        if ser:
            items.append(('S', f'Serie „{ser["title"]}“'))
        items += [(ANALYSIS_KEY.get(a['A_KIND'], 'AN'), f'{a["A_TEXT"].split(" vom ")[0]} aus dem Hintergrundlauf') for a in analyses]
        items += [(m['MATTER_TITLE'], 'öffnen') for m in front + back]
        items += [('D', 'KI-Dienste'), ('P', 'Projektdaten bearbeiten'), ('N', 'Neues Kapitel'), ('R', 'Kapitelreihenfolge'),
                  ('V', 'Vor- und Nachspann'), ('FI', f'Figuren ({n_chars})' if n_chars else 'Figuren'), ('FV', '👤 Figuren aus dem Text vorschlagen'),
                  ('A', 'Neue Auflage'), ('E', 'Einstellungen')]
        lines += [menu(items)]
        if values.get('CREDIT_TEXT'):
            lines += ['', f'<sub>{values["CREDIT_TEXT"]}</sub>']
        return '\n'.join(lines) + '\n'
    blocks = {'CHAPTERS': rows}
    if analyses:
        blocks['ANALYSES'] = analyses
    if front:
        blocks['MATTER_FRONT'] = front
    if back:
        blocks['MATTER_BACK'] = back
    return fill('projektuebersicht.html', values, blocks)


def chapter_view(base, config, args, cnum):
    from chapter_revision import readiness
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
                     'MARKERS_MEDIZIN': counts['medizin'], 'MARKERS_RECHT': counts['recht'],
                     'MARKERS_KONTINUITAET': counts['kontinuitaet']})
    amount, est = combine(parts)
    n = len(ch['sections'])
    _, ch_summary, ch_goal = chapter_readme(base, ch)
    revision_ready = readiness(base, ch)['ready']
    values = {'PROJECT_TITLE_SHORT': p['title_short'] or p['title'], 'CHAPTER_ID': ch['id'], 'CHAPTER_NUMBER': cnum,
              'CHAPTER_GOAL': ch_goal, 'CHAPTER_SUMMARY': ch_summary,
              'CHAPTER_TITLE': ch['title'], 'CHAPTER_SUBTITLE': sub.group(1) if sub else '',
              'SECTION_COUNT_TEXT': f'{n} Abschnitt' + ('' if n == 1 else 'e'),
              'MARKER_COUNT_TEXT': 'keine offenen Marker' if not counts_total else f'{counts_total} offene{"r" if counts_total == 1 else ""} Marker',
              'CHAPTER_COST': money(amount, est), 'CHAPTER_COST_HINT': cost_hint('Summe der Abschnittskosten', amount, est),
              'APPROVED_COUNT_TEXT': f'{approved} von {n}',
              'CHAPTER_APPROVABLE': 'true' if ch['status'] == 'ready_for_approval' and n and approved == n else '',
              'CHAPTER_REVISION_READY': 'true' if revision_ready else ''}
    if args.text:
        def marks(r):
            parts = [f'{MARKER_ICON[k]} {r["MARKERS_" + k.upper()]}' for k in MARKER_ICON if r['MARKERS_' + k.upper()]]
            return ' '.join(parts) or '–'
        lines = [f'### 📖 Kapitel {cnum} · {ch["title"]}']
        lines += [''] + overview_summary(base, config, cnum)
        if values['CHAPTER_SUBTITLE']:
            lines += [f'*{values["CHAPTER_SUBTITLE"]}*']
        lines += ['', f'**Ziel des Kapitels:** {ch_goal or "*noch offen*"}', '',
                  f'**Kurzbeschreibung:** {ch_summary or "*noch offen*"} · `Z` ändern, Kapitelrecherche']
        lines += ['', f'{values["SECTION_COUNT_TEXT"]} · ✅ {values["APPROVED_COUNT_TEXT"]} freigegeben · {values["MARKER_COUNT_TEXT"]} · Kosten **{values["CHAPTER_COST"]}**', '']
        if rows:
            lines += ['| # | Abschnitt | Marker | Kosten | Status |', '|--:|---|---|--:|---|']
            lines += [f'| {r["SECTION_NUMBER"]} | {r["SECTION_TITLE"]} | {marks(r)} | {r["SECTION_COST"]} | {display_status(r["SECTION_STATUS"])} |' for r in rows]
            if counts_total:
                lines += ['', f'<sub>{MARKER_LEGEND}</sub>']
        else:
            lines += ['*Noch keine Abschnitte.*']
        lines += ['', '---']
        items = [(f'{cnum}.1' + (f'–{cnum}.{n}' if n > 1 else ''), 'Abschnitt öffnen')] if rows else []
        if values['CHAPTER_APPROVABLE']:
            items.append(('FK', 'Kapitel freigeben'))
        if revision_ready:
            items.append(('KU', 'Kapitel überarbeiten'))
        items += [('B', 'Kapitel bearbeiten'), ('Z', 'Ziel, Kurzbeschreibung, Kapitelrecherche'), ('N', 'Neuer Abschnitt'),
                  ('R', 'Reihenfolge'), ('FV', '👤 Figuren aus dem Text vorschlagen'), ('Ü', 'Übersicht')]
        lines += [menu(items)]
        return '\n'.join(lines) + '\n'
    return fill('kapitelansicht.html', values, {'SECTIONS': rows})


def section_hints(base, sid):
    """Hinweise zu einem Abschnitt aus story/hints.yml (#124): [{H_KIND_TEXT, H_TEXT, H_QUOTE}]."""
    path = base / 'story' / 'hints.yml'
    if not path.is_file():
        return []
    import analyze
    data = yaml.safe_load(path.read_text(encoding='utf-8')) or {}
    return [{'H_KIND': h['kind'], 'H_KIND_TEXT': view_labels('LANGUAGE_DE').get(h['kind'], h['kind']), 'H_TEXT': h['text'], 'H_QUOTE': h.get('quote', '')}
            for h in data.get('hints') or [] if h.get('section') == sid]


def section_view(base, config, args, cnum, snum):
    p = config['project']
    ch = config['structure']['chapters'][cnum - 1]
    secs = ch['sections']
    s = secs[snum - 1]
    head, goal, summary, ms = section_file(base, s)
    markers = [{'MARKER_TYPE': KIND[m.group(1)], 'MARKER_LABEL': MARKER_LABEL[KIND[m.group(1)]],
                'MARKER_TEXT': (m.group(2) or '').strip() or '–'} for m in MARKER_TEXT.finditer(ms)]
    a, e = total(section_costs(base, ch, s))
    hints = section_hints(base, s['id'])
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
                 f'Kapitel {cnum} · {display_status(head["status"])} · Kosten **{values["SECTION_COST"]}**', '',
                 '| | |', '|---|---|',
                 f'| Ziel | {goal or "*offen*"} |', f'| Kurzbeschreibung | {summary or "*offen*"} |',
                 f'| Faktencheck | {view_labels('FC_TEXT').get(head["fact_check"], head["fact_check"])} |',
                 f'| Schreibfreigabe | {yn(head["approvals"]["writing"])} |', f'| Abschnitt freigegeben | {yn(head["approvals"]["section"])} |']
        if chars:
            names = {c['id']: c['name'] for c in chars}
            lines.append(f'| Figuren | {", ".join(names.get(c, c) for c in in_section) or "–"} |')
        lines.append('')
        if markers:
            lines += [f'**Offene Marker ({n})**'] + [f'- {MARKER_ICON[m["MARKER_TYPE"]]} {m["MARKER_LABEL"]}: {m["MARKER_TEXT"]}' for m in markers] + ['']
        else:
            lines += ['Keine offenen Marker.', '']
        if hints:
            lines += [f'**Sprachliche Hinweise ({len(hints)})** – nur zur Durchsicht, der Text bleibt unverändert'] + \
                     [f'- {h["H_KIND_TEXT"]}: {h["H_TEXT"]}' + (f' („{h["H_QUOTE"]}“)' if h['H_QUOTE'] else '') for h in hints] + ['']
        lines += ['---', '', ms, '', '---']
        items = [('T', 'Text ändern (geänderten Text schicken)'), ('F', 'Ziel, Kurzbeschreibung, Faktencheck'
                                                                  + (', Figuren' if chars else '')),
                 ('FS', 'Schreibfreigabe zurücknehmen' if head['approvals']['writing'] else 'Schreiben freigeben'),
                 ('FA', 'Abschnittsfreigabe zurücknehmen' if head['approvals']['section'] else 'Abschnitt freigeben'),
                 ('RS', 'Recherche sofort'), ('GS', 'Ghostwriting sofort'), ('BI', 'Bilder'), ('FV', '👤 Figuren aus dem Text vorschlagen')]
        if prev_id:
            items.append((f'{cnum}.{snum - 1}', '← vorheriger'))
        if next_id:
            items.append((f'{cnum}.{snum + 1}', 'nächster →'))
        items.append(('K', 'Zum Kapitel'))
        lines += [menu(items)]
        return '\n'.join(lines) + '\n'
    blocks = {'MARKERS': markers}
    if hints:
        blocks['HINTS'] = hints
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
            + ['', view_message('settings.form_hint')]) + '\n'
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
        warn = view_message('edition.no_chapters')
    elif approved < len(chapters):
        warn = view_message('edition.partial_approval', approved=approved, total=len(chapters))
    else:
        warn = ''
    # Was den Bau der Auflage verhindert (scripts/assemble.py check): kein freigegebenes
    # Kapitel, offene Marker, Lücken; dazu ein fehlender Titel (Name und Tag der Auflage)
    from assemble import book_parts, problems
    blockers = [x for x in problems(book_parts(base, config), config) if not x.startswith(('Kein Kapitel', 'Das Buch hat noch keinen Titel'))]
    markers = sum(x.startswith('Offener Marker') for x in blockers)
    parts = []
    if not short:
        parts.append(view_message('edition.no_title'))
    if not approved:
        parts.append(view_message('edition.none_approved'))
    if markers:
        parts.append(view_message('edition.open_markers', number=markers))
    if len(blockers) > markers:
        parts.append(view_message('edition.unapproved_sections'))
    if parts:
        reasons = ', '.join(parts[:-1]) + (view_message('edition.and') if len(parts) > 1 else '') + parts[-1]
        warn = (warn + ' ' if warn else '') + view_message('edition.blocked', reasons=reasons)
    if not short:
        short = 'Ohne Titel'
    values = {'EDITION_NUMBER': n, 'EDITION_NAME': br['name_pattern'].format(title_short=short, edition=n),
              'EDITION_TAG': br['tag_pattern'].format(title_short_slug=tag_slug(short), edition=n),
              'EDITION_DATE_DEFAULT': datetime.date.today().isoformat(), 'APPROVAL_WARNING_TEXT': warn}
    chosen = (config.get('typesetting') or {}).get('formats') or br['assets']   # Ausgabeoptionen (#68)
    short = {'pdf_print': view_message('edition.print_pdf'), 'cover': view_message('edition.cover')}
    formats = [{'FORMAT_LABEL': short.get(a, a.upper())} for a in ['pdf', 'pdf_print', 'cover', 'epub', 'docx'] if a in chosen]
    if args.text:
        return '\n'.join([view_message('edition.heading', number=n), '', '| | |', '|---|---|',
                           view_message('edition.name_row', name=values['EDITION_NAME']),
                           view_message('edition.tag_row', tag=values['EDITION_TAG']),
                           view_message('edition.formats_row', formats=', '.join(f['FORMAT_LABEL'] for f in formats)),
                           view_message('edition.date_row', date=values['EDITION_DATE_DEFAULT'])]
                          + (['', f'> ⚠️ {warn}'] if warn else [])
                          + ['', view_message('edition.form_hint')]) + '\n'
    return fill('auflage-erzeugen.html', values, {'FORMATS': formats})


def load_upstream(args):
    """Update-Stand aus --upstream (JSON): behind, upstream, version, installed. Nichts, wenn nicht dahinter."""
    if not getattr(args, 'upstream', None):
        return None
    data = json.loads(Path(args.upstream).read_text(encoding='utf-8'))
    return data if int(data.get('behind') or 0) > 0 else None


def update_text(upd):
    n = int(upd['behind'])
    text = (view_message('update.behind_one', number=n, upstream=upd.get('upstream') or 'ploeffler/GhostWriter:main') if n == 1 else
            view_message('update.behind', number=n, upstream=upd.get('upstream') or 'ploeffler/GhostWriter:main'))
    if upd.get('version') and upd.get('version') != upd.get('installed'):
        text += view_message('update.available', version=upd['version'])
        if upd.get('installed'):
            text += view_message('update.installed', version=upd['installed'])
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
    return view_message('one_change') if n == 1 else view_message('many_changes', number=n)


def change_date(value):
    import datetime
    try:
        return datetime.datetime.fromisoformat(str(value).replace('Z', '+00:00')).strftime('%Y-%m-%d, %H:%M' if UI.get('language') == 'en' else '%d.%m.%Y, %H:%M')
    except ValueError:
        return str(value or '')


def changes_merge_view(base, config, args):
    changes = load_changes(args)
    if not changes:
        msg = view_message('there_are_no_pending_changes')
        return msg + '\n' if args.text else f'<p>{msg}</p>\n'
    rows = [{'CHANGE_MESSAGE': c['message'].splitlines()[0], 'CHANGE_DATE': change_date(c.get('date')),
             'CHANGE_SHA': c['sha'][:7]} for c in changes['commits']]
    values = {'PENDING_TEXT': changes_text(changes), 'PENDING_PR': changes['pull_request'],
              'BOOK_BRANCH': changes['book_branch'], 'WORK_BRANCH': changes['work_branch']}
    if args.text:
        lines = [view_message('apply_changes'), '',
                 view_message('apply_to_from_pull_request', p_a=f"{values['BOOK_BRANCH']}", p_b=f"{values['PENDING_TEXT']}", p_c=f"{values['WORK_BRANCH']}", p_d=f"{values['PENDING_PR']}"), '',
                 view_message('change_date_commit'), '|--:|---|---|---|']
        lines += [f'| {i} | {r["CHANGE_MESSAGE"]} | {r["CHANGE_DATE"]} | `{r["CHANGE_SHA"]}` |' for i, r in enumerate(rows, start=1)]
        lines += ['', view_message('the_changes_become_part_of_the_book_undoing_them_requires_another_change'), '',
                  '---', view_message('ok_applies_x_cancels')]
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
            raise SystemExit(view_message('image_not_found', p_a=f'{args.where}'))
        meta = hit[0]
        target_id, label = meta['id'], view_message('image', p_a=f"{meta.get('caption') or meta['id']}")
        approved = meta.get('status') == 'approved'
        if revoke:
            title, button = view_message('withdraw_image_approval'), view_message('withdraw')
            if not approved:
                add('block', view_message('the_image_is_not_approved'))
            effect = view_message('the_image_returns_to_draft_if_it_appears_in_approved_text_it_prevents_the_next_edition')
        else:
            title, button = view_message('approve_image'), view_message('approve')
            if approved:
                add('block', view_message('the_image_is_already_approved'))
            if not hit[1].is_file():
                add('block', view_message('the_image_file_is_missing'))
            w = meta.get('width_px')
            add('ok' if w and w >= 1500 else 'warn', view_message('width_px', p_a=f'{w}') if w else view_message('size_unknown'))
            add('ok' if meta.get('caption') else 'warn', view_message('caption_provided') if meta.get('caption') else view_message('no_caption'))
            add('ok' if meta.get('alt') else 'warn', view_message('alternative_text_provided') if meta.get('alt') else view_message('no_alternative_text_epub'))
            if meta.get('ai_generated'):
                add('ok', view_message('ai_generated_the_image_credit_in_the_imprint_states_this') if (config.get('images') or {}).get('credit_in_imprint', True)
                    else view_message('ai_generated_the_image_credit_in_the_imprint_is_turned_off'))
            effect = view_message('the_image_becomes_approved_and_is_included_at_its_position_in_the_text_in_the_next_edition')
    elif kind == 'chapter':
        cnum, ch = chapter_number(config, args.where)
        target_id, label = ch['id'], view_message('chapter', p_a=f'{cnum}', p_b=f"{ch['title']}")
        heads = [section_file(base, s)[0] for s in ch['sections']]
        open_ = sum(h['status'] != 'approved' for h in heads)
        if revoke:
            title, button = view_message('withdraw_chapter_approval'), view_message('withdraw')
            if ch['status'] != 'approved':
                add('block', view_message('the_chapter_is_not_approved'))
            effect = view_message('the_chapter_returns_to_in_progress_section_approvals_remain_in_place')
        else:
            title, button = view_message('approve_chapter'), view_message('approve')
            if ch['status'] == 'approved':
                add('block', view_message('the_chapter_is_already_approved'))
            if open_:
                add('block', view_message('of_sections_are_not_yet_approved', p_a=f'{open_}', p_b=f'{len(heads)}'))
            else:
                add('ok', view_message('all_sections_are_approved', p_a=f'{len(heads)}'))
            if ch['status'] not in ('ready_for_approval', 'approved'):
                add('block', view_message('the_chapter_status_is_rather_than_ready_for_approval_assemble_and_review_it_first', p_a=f"{view_status(ch['status'])}"))
            effect = view_message('the_chapter_becomes_approved_you_confirm_the_assembled_chapter_in_this_version')
    else:
        item = None if re.fullmatch(r'\d+\.\d+', args.where or '') else find_matter(config, args.where)
        if item:   # Vor- oder Nachspann (#57): Schreibfreigabe und Freigabe des Teils wie bei einem Abschnitt
            sec, ch, c, s_ = item, {'status': '', 'path': ''}, 0, 0
            head, goal, summary, ms = section_file(base, item)
            target_id, label = item['id'], f"{item['title']} ({view_message('front_matter') if MATTER[item['kind']][0] == 'front' else view_message('back_matter')})"
            if kind == 'section':
                kind = 'matter'
        else:
            c, s_ = (int(x) for x in args.where.split('.'))
            ch = chapters[c - 1]
            sec = ch['sections'][s_ - 1]
            head, goal, summary, ms = section_file(base, sec)
            target_id, label = sec['id'], view_message('section', p_a=f'{c}', p_b=f'{s_}', p_c=f"{sec['title']}")
        ap = head['approvals']
        if kind == 'writing' and revoke:
            title, button = view_message('withdraw_writing_permission'), view_message('withdraw')
            if not ap['writing']:
                add('block', view_message('writing_permission_has_not_been_granted'))
            if ap['section']:
                add('block', view_message('is_approved_withdraw_that_approval_first', p_a=f"{item['title']}") if item else
                    view_message('the_section_is_approved_withdraw_section_approval_first'))
            effect = view_message('writing_permission_is_withdrawn_the_manuscript_stays_as_it_is_but_writing_can_resume_only_after_new_')
        elif kind == 'writing' and item:
            title, button = view_message('grant_writing_permission'), view_message('approve')
            if ap['writing']:
                add('block', view_message('writing_permission_has_already_been_granted'))
            if item['kind'] not in MATTER_GHOSTWRITING:
                add('ok', view_message('you_provide_the_text_ghostwriting_requires_an_explicit_request', p_a=f"{view_matter_kind(item['kind'])}"))
            effect = view_message('writing_permission_is_granted_the_text_may_then_be_written') + \
                (view_message('the_part_moves_to_writing') if head['status'] in ('planned', 'research', 'brainstorming', 'ready_to_write') else '')
        elif kind == 'writing':
            title, button = view_message('grant_writing_permission'), view_message('approve')
            if ap['writing']:
                add('block', view_message('writing_permission_has_already_been_granted'))
            add('ok' if goal else 'warn', view_message('section_goal_provided') if goal else view_message('section_goal_still_missing'))
            add('ok' if summary else 'warn', view_message('summary_provided') if summary else view_message('summary_still_missing'))
            for folder, name in (('research', view_message('research_run')), ('brainstorming', view_message('brainstorming_run'))):
                k = run_count(base, ch, sec['id'], folder)
                add('ok' if k else 'warn', view_message('available', p_a=f'{k}', p_b=f'{name}', p_c=f"{view_plural(k, 'e')}") if k else
                    view_message('no_yet_workflow_yml_requires_this_before_writing_permission', p_a=f'{name}'))
            effect = view_message('writing_permission_is_granted_the_manuscript_may_then_be_written') + \
                (view_message('the_section_moves_to_writing') if head['status'] in ('planned', 'research', 'brainstorming', 'ready_to_write') else '')
        elif revoke and item:
            title, button = view_message('withdraw_approval'), view_message('withdraw')
            if not ap['section']:
                add('block', view_message('is_not_approved', p_a=f"{item['title']}"))
            effect = view_message('approval_is_withdrawn_moves_to_revision_and_is_excluded_from_the_next_edition_until_approved_again', p_a=f"{item['title']}")
        elif item:
            title, button = view_message('approve_2', p_a=f"{item['title']}"), view_message('approve')
            if ap['section']:
                add('block', view_message('is_already_approved', p_a=f"{item['title']}"))
            if not ap['writing']:
                add('block', view_message('writing_permission_is_missing'))
            if ms.strip() in EMPTY_MANUSCRIPT:
                add('block', view_message('there_is_no_text_yet'))
            else:
                add('ok', view_message('text_words', p_a=f'{len(ms.split())}'))
            n = sum(marker_counts(ms).values())
            add('warn' if n else 'ok', view_message('open_marker_these_prevent_an_edition', p_a=f'{n}', p_b=f"{view_plural(n, 'r', german_singular=True)}") if n else view_message('no_open_markers'))
            if item['kind'] == 'glossary':
                entries = glossary_entries(ms)[1]
                dup = glossary_duplicates(entries)
                add('block' if dup else 'ok', view_message('duplicate_terms', p_a=f"{', '.join(dup)}") if dup else
                    view_message('term_with_no_duplicates', p_a=f'{len(entries)}', p_b=f"{view_plural(len(entries), 'e')}"))
            effect = view_message('becomes_approved_and_is_included_in_the_next_edition_you_confirm_the_text_in_this_version', p_a=f"{item['title']}")
        elif revoke:
            title, button = view_message('withdraw_section_approval'), view_message('withdraw')
            if not ap['section']:
                add('block', view_message('the_section_is_not_approved'))
            if ch['status'] == 'approved':
                add('warn', view_message('this_also_withdraws_approval_for_chapter_it_returns_to_in_progress', p_a=f'{c}'))
            effect = view_message('section_approval_is_withdrawn_the_section_moves_to_revision')
        else:
            title, button = view_message('approve_section'), view_message('approve')
            if ap['section']:
                add('block', view_message('the_section_is_already_approved'))
            if not ap['writing']:
                add('block', view_message('writing_permission_is_missing'))
            if ms.strip() in EMPTY_MANUSCRIPT:
                add('block', view_message('there_is_no_manuscript_yet'))
            else:
                add('ok', view_message('manuscript_words', p_a=f'{len(ms.split())}'))
            n = sum(marker_counts(ms).values())
            add('warn' if n else 'ok', view_message('open_marker_these_remain_in_the_approved_text', p_a=f'{n}', p_b=f"{view_plural(n, 'r', german_singular=True)}") if n else view_message('no_open_markers'))
            if head['fact_check'] == 'requested':
                add('warn', view_message('a_fact_check_is_requested_has_it_been_completed'))
            effect = view_message('the_section_becomes_approved_you_confirm_the_text_as_shown_in_the_section_form')
    head_sha = UI.get('head', '')
    values = {'APPROVAL_KIND': kind, 'APPROVAL_REVOKE': 'true' if revoke else '', 'APPROVAL_TITLE': title,
              'APPROVAL_BUTTON': button, 'APPROVAL_EFFECT': effect, 'TARGET_ID': target_id, 'TARGET_LABEL': label,
              'HEAD_SHORT': head_sha[:7] or '–'}
    if args.text:
        icon = {'ok': '✅', 'warn': '⚠️', 'block': '⛔'}
        blocked = any(x['CHECK_STATE'] == 'block' for x in checks)
        lines = [f'### {"↩️" if revoke else "✅"} {title}', '', view_message('version', p_a=f'{label}', p_b=f"{values['HEAD_SHORT']}"), '']
        if checks:
            lines += [f'- {icon[x["CHECK_STATE"]]} {x["CHECK_TEXT"]}' for x in checks] + ['']
        lines += [effect, '', '---',
                  view_message('complete_the_items_before_confirming_x_closes_this_view') if blocked else view_message('ok_confirms_x_cancels')]
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
               'web': view_message('service.web_access'), 'github': view_message('service.github_access')}


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
    catalog = view_provider_catalog(yaml.safe_load((ROOT / 'providers.yml').read_text(encoding='utf-8')))
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
                note = ' · '.join(x for x in (s.get('hq', ''), view_labels('WEB_TEXT').get(s.get('web_research'), ''), s.get('note', '')) if x and x != 'n/a')
            elif group == 'search':
                roles, note = 'search', s.get('note', '')
            else:
                roles, note = 'queue_processing', s.get('note', '')
            services.append({'SERVICE_ID': s['id'], 'SERVICE_NAME': s['name'], 'SERVICE_GROUP': group,
                             'SERVICE_ROLES': roles, 'SERVICE_NOTE': note, 'SERVICE_AVAILABLE': 'true' if s['id'] in available else '',
                             'SERVICE_GUIDE_URL': guide(s, group), 'SERVICE_WEBSITE_URL': s.get('url', ''),
                             **service_settings(s, group, settings.get(s['id']) or {}, present)})
    roles = []
    for rid, label, hint in view_role_info():
        entry = ap.get(rid) or {}
        value = entry.get('agent', 'manual') if rid == 'queue_processing' else entry.get('provider', '')
        roles.append({'ROLE_ID': rid, 'ROLE_LABEL': label, 'ROLE_HINT': hint, 'ROLE_VALUE': value or ''})
    secrets_url = f'https://github.com/{args.repo}/settings/secrets/actions/new'
    if args.text:
        names = {s['SERVICE_ID']: s['SERVICE_NAME'] for s in services}
        names.update({'chat': view_message('view.providers_edit.current_chat'), 'manual': view_message('view.providers_edit.manual'), '': view_message('view.providers_edit.same_as_default')})
        lines = [view_message('view.providers_edit.ai_services'), '', view_message('view.providers_edit.your_services'), '']
        mine = [s for s in services if s['SERVICE_AVAILABLE']]
        def summary(s):
            parts = [view_labels('ACCESS_TEXT')[s['SERVICE_ACCESS']]]
            if s['SERVICE_ACCESS'] == 'api':
                st = {'ok': view_message('view.providers_edit.stored'), 'alt': view_message('view.providers_edit.via', p_a=s["SERVICE_SECRET_ALT"]), 'missing': view_message('view.providers_edit.missing'), '': view_message('view.providers_edit.status_unknown')}[s['SERVICE_SECRET_STATE']]
                parts.append(f'Secret `{s["SERVICE_SECRET"]}` ({st})')
            if s['SERVICE_GROUP'] == 'llm':
                parts.append(view_message('view.providers_edit.model', p_a=s["SERVICE_MODEL"] or view_message('view.providers_edit.default')))
                if s['SERVICE_ACCESS'] == 'app':
                    parts.append(view_message('view.providers_edit.connected_to_github') if s['SERVICE_GITHUB'] else view_message('view.providers_edit.not_connected_to_github'))
            if s['SERVICE_PLAN']:
                parts.append(view_message('view.providers_edit.plan', p_a=s["SERVICE_PLAN"]))
            if s['SERVICE_COST']:
                parts.append(view_message('view.providers_edit.month', p_a=money(Decimal(s["SERVICE_COST"]), False)))
            if s['SERVICE_MEMO']:
                parts.append(s['SERVICE_MEMO'])
            return ' · '.join(parts)
        lines += [f'- `{s["SERVICE_ID"]}` {s["SERVICE_NAME"]}: {summary(s)}' for s in mine] or [view_message('view.providers_edit.none_added_yet_until_then_the_current')]
        lines += ['', view_message('view.providers_edit.task_service'), '|---|---|']
        lines += [f'| {r["ROLE_LABEL"]} | {names.get(r["ROLE_VALUE"], r["ROLE_VALUE"])} |' for r in roles]
        lines += ['', view_message('view.providers_edit.details_summary_add_more_services_summary'), '']
        lines += [view_message('view.providers_edit.guide', p_a=s["SERVICE_ID"], p_b=s["SERVICE_NAME"], p_c=s["SERVICE_GUIDE_URL"])
                  + (f' · [Website]({s["SERVICE_WEBSITE_URL"]})' if s['SERVICE_WEBSITE_URL'] else '')
                  for s in services if not s['SERVICE_AVAILABLE']]
        lines += ['', '</details>', '', '---',
                  view_message('view.providers_edit.reply_one_item_per_line_id_i'),
                  '', view_message('view.providers_edit.never_put_api_keys_in_this_chat', p_a=secrets_url)]
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
            ('Titel', ch['title']), ('Untertitel', subtitle), ('Kurzbeschreibung', summary), ('Ziel', goal)]) + ['', view_message('settings.form_hint')]) + '\n'
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
                           f'und optional `Faktencheck: aus | optional | angefordert` (Vorgabe: {view_labels('FC_TEXT')[fc]}).', '', '**Positionen**']
                          + [f'`{i}` {l}' + (' *(Vorgabe)*' if i == len(labels) - 1 else '') + '  ' for i, l in enumerate(labels)]
                          + ['', '`X` bricht ab.']) + '\n'
    return fill('abschnitt-anlegen.html', {'CHAPTER_ID': ch['id'], 'CHAPTER_NUMBER': n, 'CHAPTER_TITLE': ch['title'],
                                           'FACT_CHECK_DEFAULT': fc}, {'POSITIONS': positions(labels)})


def reorder(args, kind, heading, items, chapter_id='', chapter_no=''):
    if args.text:
        return '\n'.join([f'### ↕️ {heading}', '', view_message('current_title'), '|--:|---|']
                          + [f'| `{i["ITEM_NUMBER"]}` | {i["ITEM_TITLE"]} |' for i in items]
                          + ['', view_message('send_the_numbers_in_the_new_order_e_g') + ', '.join(str(i['ITEM_NUMBER']) for i in (items[1::-1] + items[2:4] if len(items) > 1 else items)) + (', …' if len(items) > 4 else '') + view_message('x_cancels')]) + '\n'
    return fill('reihenfolge.html', {'REORDER_KIND': kind, 'REORDER_HEADING': heading, 'CHAPTER_ID': chapter_id,
                                     'CHAPTER_NUMBER': chapter_no}, {'ITEMS': items})


def chapter_reorder_view(base, config, args):
    items = [{'ITEM_ID': ch['id'], 'ITEM_NUMBER': i, 'ITEM_TITLE': ch['title']}
             for i, ch in enumerate(config['structure']['chapters'], start=1)]
    return reorder(args, 'chapter', view_message('change_chapter_order'), items)


def section_reorder_view(base, config, args):
    n, ch = chapter_number(config, args.where)
    items = [{'ITEM_ID': s['id'], 'ITEM_NUMBER': f'{n}.{i}', 'ITEM_TITLE': s['title']}
             for i, s in enumerate(ch['sections'], start=1)]
    return reorder(args, 'section', view_message('change_section_order_in_chapter', p_a=f'{n}'), items, ch['id'], n)


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
    text = view_message('settings.installed', p_a=version or view_message('settings.unknown'))
    when = str(state.get('updated_at') or '')
    if re.match(r'\d{4}-\d{2}-\d{2}', when):
        text += view_message('settings.updated', p_a=when[8:10], p_b=when[5:7], p_c=when[:4])
    mig = state.get('migration') or {}
    if mig.get('to') is not None:
        text += view_message('settings.migrated', p_a=mig["to"])
        if mig.get('changes'):
            text += ' (' + '; '.join(mig['changes'][:3]) + ('; …' if len(mig['changes']) > 3 else '') + ')'
    hint = ''
    if state.get('skipped_workflows'):
        hint = (view_message('settings.workflow_skipped', p_a=len(state["skipped_workflows"])))
    return auto, text, hint


def output_value(key, value):
    label, names = view_labels('OUTPUT_LABELS')[key]
    if isinstance(value, bool):
        return view_message('settings.yes') if value else view_message('settings.no')
    if key == 'formats':
        return ', '.join(names.get(v, v) for v in value)
    if key in ('font_size',):
        return str(value).replace('.', '.' if UI.get('language') == 'en' else ',') + ' pt'
    if key == 'line_spacing':
        return str(value).replace('.', '.' if UI.get('language') == 'en' else ',') + view_message('settings.spacing_unit')
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
    lines = [view_message('settings.output_heading'), '', view_message('settings.output_intro'), '']
    for group, keys in view_labels('OUTPUT_GROUPS'):
        lines += [f'**{group}**', '', view_message('settings.fields_table'), '|---|---|---|']
        for k in keys:
            label, names = view_labels('OUTPUT_LABELS')[k]
            if isinstance(TYPESETTING_DEFAULT[k], bool):
                options = view_message('settings.yes_no')
            elif k == 'font_size':
                options = view_message('settings.font_sizes')
            elif k == 'line_spacing':
                options = view_message('settings.line_spacings')
            elif k == 'formats':
                options = view_message('settings.formats')
            else:
                options = ', '.join(names.values())
            lines.append(f'| {label} | {output_value(k, ts[k])} | {options} |')
        lines.append('')
    lines += [view_message('settings.imprint_heading'), '', view_message('settings.hints_table'), '|---|---|---|']
    lines += [f'| {label} | {pub.get(k) or "–"} | {hint} |' for k, label, hint in view_labels('PUBLICATION_LABELS')]
    pr, cv = config.get('print') or {}, config.get('cover') or {}
    prof = {'kdp': 'Amazon KDP', 'bod': 'Books on Demand', 'custom': view_message('settings.custom')}
    paper = {'white': view_message('settings.white'), 'cream': view_message('settings.cream'), 'premium_color': view_message('settings.premium_color')}
    spine = (view_message('settings.fixed_spine', p_a=pr["spine_mm"]) if pr.get('spine_mm') is not None else
             view_message('settings.calculated_spine', p_a=pr["paper_mm_per_page"]) if pr.get('paper_mm_per_page') else
             view_message('settings.paper_spine') if pr.get('profile') == 'kdp' else '–')
    lines += ['', view_message('settings.print_heading'), '', view_message('settings.fields_table'), '|---|---|---|',
              view_message('settings.profile_row', p_a=prof.get(pr.get("profile"), "–")),
              view_message('settings.paper_row', p_a=paper.get(pr.get("paper"), view_message('settings.white') if pr.get("profile") == "kdp" else "–")),
              view_message('settings.spine_row', p_a=spine),
              view_message('settings.bleed_row', p_a=pr.get("bleed_mm", view_message('settings.profile_default')), p_b=" mm" if "bleed_mm" in pr else ""),
              view_message('settings.crop_row', p_a=view_message('settings.yes') if pr.get("crop_marks") else view_message('settings.no')), '',
              view_message('settings.cover_heading'), '', view_message('settings.fields_table'), '|---|---|---|',
              view_message('settings.template_row', p_a=view_labels('TEMPLATE_DE').get(cv.get("template", "classic"), "")),
              view_message('settings.background_row', p_a=cv.get("background", "#1F2A44")),
              view_message('settings.text_color_row', p_a=cv.get("text_color", "#FFFFFF")),
              view_message('settings.cover_image_row', p_a=cv.get("image") or "–"),
              view_message('settings.author_image_row', p_a=cv.get("author_image") or "–"),
              view_message('settings.price_row', p_a=cv.get("price") or "–"),
              view_message('settings.spine_direction_row', p_a=view_message('settings.spine_up') if cv.get("spine_direction") == "up" else view_message('settings.spine_down')),
              '', view_message('settings.cover_note'),
              '', view_message('settings.form_hint')]
    return '\n'.join(lines) + '\n'


def ai_disc_text(config):
    s = (config.get('ai_disclosure') or {})
    mode = s.get('mode', 'none')
    if mode == 'none':
        return view_message('settings.none')
    place = {'imprint': view_message('settings.in_imprint'), 'foreword': view_message('settings.in_foreword'), 'afterword': view_message('settings.in_afterword'), 'page': view_message('settings.own_page')}
    return {'short': view_message('settings.short'), 'detailed': view_message('settings.detailed'), 'custom': view_message('settings.custom_text')}[mode] + ', ' + \
        place.get(s.get('placement', 'imprint'), '') + ('' if s.get('text') else view_message('settings.wording_pending'))


def project_settings_view(base, config, args):
    ts = dict(TYPESETTING_DEFAULT)
    ts.update(config.get('typesetting') or {})
    wf = config.get('workflow') or {}
    fixed = []
    for block, key, label in view_labels('FIXED_RULES'):
        v = (config.get(block) or {}).get(key)
        if v is None:
            continue
        text = view_labels('FIXED_TEXT').get(v, str(v))
        fixed.append({'FIXED_LABEL': label, 'FIXED_VALUE': text if isinstance(v, bool) else f'{text} ({v})'})
    fc = wf.get('fact_checking_default') or 'optional'
    upd_auto, upd_text, upd_hint = update_info(base, config)
    auto_merge = (config.get('changes') or {}).get('auto_merge') is True
    lim = config.get('limits') or {}
    lim_sum = limit_summary(base, config)
    if args.text:
        page = {'a5': view_message('settings.a5'), '12x19': '12 × 19 cm', '13.5x21.5': view_message('settings.page_135'), 'a4': 'A4'}
        jn = lambda v: view_message('settings.yes') if v else view_message('settings.no')
        return '\n'.join([view_message('settings.heading'), '', view_message('settings.fixed_rules'), '',
                           view_message('settings.rules_table'), '|---|---|'] + [f'| {f["FIXED_LABEL"]} | {f["FIXED_VALUE"]} |' for f in fixed]
                          + ['', view_message('settings.editable'), '', view_message('settings.fields_table'), '|---|---|---|',
                             view_message('settings.fact_check_row', p_a=view_labels('FC_TEXT')[fc]),
                             view_message('settings.page_row', p_a=page.get(ts["page_size"], ts["page_size"])),
                             view_message('settings.font_row', p_a=view_message('settings.serif') if ts["font"] == "serif" else view_message('settings.sans')),
                             view_message('settings.font_size_row', p_a=str(ts["font_size"]).replace(".", "." if UI.get('language') == 'en' else ",")),
                             view_message('settings.title_page_row', p_a=jn(ts["title_page"])), view_message('settings.imprint_row', p_a=jn(ts["imprint"])),
                             view_message('settings.toc_row', p_a=jn(ts["toc"])),
                             view_message('settings.toc_depth_row', p_a=view_message('settings.chapters_only') if ts["toc_depth"] == 1 else view_message('settings.chapters_sections')),
                             view_message('settings.updates_row', p_a=jn(upd_auto)),
                             view_message('settings.auto_merge_row', p_a=jn(auto_merge)),
                             view_message('settings.budget_row', p_a=lim.get("ai_budget_monthly") or "–"),
                             view_message('settings.minutes_row', p_a=lim.get("actions_minutes_monthly") or "–"),
                             view_message('settings.disclosure_row', p_a=ai_disc_text(config)),
                             view_message('settings.output_row'),
                             '', f'<sub>{upd_text} · Limits: {lim_sum}</sub>'] + ([f'', f'> ⚠️ {upd_hint}'] if upd_hint else []) + ['', view_message('settings.form_hint')]) + '\n'
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
                  'AI_USED_TEXT': ' · '.join(f'{view_usage_task(t)}: {view_service_names(ids, names)}' for t, ids in used.items()),
                  'AI_PROPOSAL_SHORT': ad.suggest(base, config, 'short', False),
                  'AI_PROPOSAL_SHORT_NAMED': ad.suggest(base, config, 'short', True),
                  'AI_PROPOSAL_DETAILED': ad.suggest(base, config, 'detailed', False),
                  'AI_PROPOSAL_DETAILED_NAMED': ad.suggest(base, config, 'detailed', True),
                  'AI_PLACES_MISSING': ','.join(missing), 'AI_LEGAL_HINT': view_message('disclosure.legal_hint')}
        return fill('ki-angabe.html', values)
    mode_de = {'none': view_message('settings.none'), 'short': view_message('view.ai_disclosure.short_one_sentence'), 'detailed': view_message('view.ai_disclosure.detailed_per_task'), 'custom': view_message('view.ai_disclosure.custom_text')}
    place_de = {'imprint': view_message('view.ai_disclosure.imprint'), 'foreword': view_message('view.ai_disclosure.foreword_at_the_end'), 'afterword': view_message('view.ai_disclosure.afterword_at_the_end'), 'page': view_message('view.ai_disclosure.separate_page_at_the_end')}
    lines = [view_message('view.ai_disclosure.ai_disclosure_in_the_book'), '',
             view_message('view.ai_disclosure.whether_and_how_the_book_discloses_ai'), '',
             view_message('settings.fields_table'), '|---|---|---|',
             view_message('view.ai_disclosure.disclosure_none_short_detailed_custom', p_a=mode_de[s["mode"]]),
             view_message('view.ai_disclosure.placement_imprint_foreword_afterword_separate_page', p_a=place_de[s["placement"]]),
             view_message('view.ai_disclosure.name_services_yes_no', p_a=view_message('view.ai_disclosure.yes') if s["name_services"] else view_message('view.ai_disclosure.no')), '']
    if used:
        lines += [view_message('view.ai_disclosure.used_according_to_the_runs') + ' · '.join(
            f'{view_usage_task(t)}: {view_service_names(ids, names)}' for t, ids in used.items()), '']
    else:
        lines += [view_message('view.ai_disclosure.no_ai_runs_have_been_recorded_yet'), '']
    if s['mode'] != 'none':
        lines += [view_message('view.ai_disclosure.wording_in_the_book') + (view_message('view.ai_disclosure.confirmed') if s['text'] else view_message('view.ai_disclosure.not_confirmed_yet')) + ':**', '']
        lines += ['> ' + l if l else '>' for l in (s['text'] or view_message('view.ai_disclosure.empty')).splitlines()] + ['']
    if proposal and proposal != s['text'] and s['mode'] in ('short', 'detailed'):
        lines += [view_message('view.ai_disclosure.suggestion_based_on_recorded_runs'), ''] + ['> ' + l if l else '>' for l in proposal.splitlines()] + ['']
    lines += [f"<sub>⚖️ {view_message('disclosure.legal_hint')}</sub>", '', '---',
              view_message('view.ai_disclosure.reply_with_disclosure_placement_name_services_yes')
              + (view_message('view.ai_disclosure.ok_accepts_the_suggestion') if proposal and s['mode'] in ('short', 'detailed') else '')
              + view_message('view.ai_disclosure.x_cancels')]
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
    catalog = view_provider_catalog(yaml.safe_load((ROOT / 'providers.yml').read_text(encoding='utf-8')))
    names = {x['id']: x.get('name', x['id']) for x in catalog.get('providers') or []}
    provider = view_message('view.chapter_research.current_chat') if pid == 'chat' else names.get(pid, pid).split(' (')[0]
    when = str(last_head.get('date') or '')
    count = (view_message('view.chapter_research.run', p_a=len(runs)) if len(runs) == 1 else view_message('view.chapter_research.runs', p_a=len(runs))) if runs else view_message('view.chapter_research.no_chapter_research_yet')
    if runs and re.match(r'\d{4}-\d{2}-\d{2}', when):
        count += view_message('view.chapter_research.latest_on', p_a=when[8:10], p_b=when[5:7], p_c=when[:4])
    clean = lambda v: '' if (v or '').strip() in ('', 'Offen.', '–') else v.strip()
    chapters = config['structure']['chapters']
    def neighbour(k):
        if 1 <= k <= len(chapters):
            other = chapters[k - 1]
            return view_message('view.chapter_research.chapter', p_a=k, p_b=other["title"]), chapter_readme(base, other)[1]
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
    note = (view_message('view.chapter_research.the_chapter_has_no_sections_yet_selected') if not k else
            view_message('view.chapter_research.the_chapter_already_has_section_existing_sections', p_a=k, p_b=view_plural(k, 'e')))
    if k and ch.get('status') == 'approved':
        note += view_message('view.chapter_research.the_chapter_is_approved_this_change_returns')
    values = {'CHAPTER_ID': ch['id'], 'CHAPTER_NUMBER': n, 'CHAPTER_TITLE': ch['title'],
              'CHAPTER_GOAL': draft.get('goal', goal), 'CHAPTER_SUMMARY': draft.get('summary', summary),
              'RESEARCH_QUESTION': draft.get('question', last_head.get('question') or ''),
              'RESEARCH_SCOPE': draft.get('scope', last_head.get('scope') or ''),
              'RESEARCH_TASK': task, 'SECTION_COUNT': k, 'SECTIONS_NOTE': note,
              'PREV_CHAPTER': 'true' if prev_label else '', 'PREV_CHAPTER_LABEL': prev_label,
              'PREV_CHAPTER_SUMMARY': prev_summary, 'PREV_WEIGHT': weight('weight_prev'),
              'NEXT_CHAPTER': 'true' if next_label else '', 'NEXT_CHAPTER_LABEL': next_label,
              'NEXT_CHAPTER_SUMMARY': next_summary, 'NEXT_WEIGHT': weight('weight_next'),
              'RESEARCH_PROVIDER_TEXT': view_message('view.chapter_research.research_via', p_a=provider), 'RUN_COUNT_TEXT': count,
              'LAST_RUN': 'true' if runs else '', 'LAST_RUN_ID': last_head.get('id') or (runs[-1].stem if runs else ''),
              'LAST_RUN_TEXT': clean(last.get('Kurzfassung')),
              'SUGGESTED_GOAL': clean(last.get('Vorschlag: Ziel des Kapitels')),
              'SUGGESTED_SUMMARY': clean(last.get('Vorschlag: Kurzbeschreibung'))}
    if args.text:
        lines = [view_message('view.chapter_research.chapter_research_chapter', p_a=n, p_b=ch["title"]), ''] + field_table([
            (view_message('view.chapter_research.goal'), values['CHAPTER_GOAL']), (view_message('view.chapter_research.summary'), values['CHAPTER_SUMMARY'])])
        if values['SUGGESTED_GOAL'] or values['SUGGESTED_SUMMARY']:
            lines += ['', view_message('view.chapter_research.suggestions_from', p_a=values["LAST_RUN_ID"])]
            if values['SUGGESTED_GOAL']:
                lines += [view_message('view.chapter_research.goal_vz_apply', p_a=values["SUGGESTED_GOAL"])]
            if values['SUGGESTED_SUMMARY']:
                lines += [view_message('view.chapter_research.summary_vk_apply', p_a=values["SUGGESTED_SUMMARY"])]
        if values['LAST_RUN_TEXT']:
            lines += ['', f'> {values["LAST_RUN_TEXT"]}']
        if proposals:
            lines += ['', view_message('view.chapter_research.suggested_sections_from', p_a=values["LAST_RUN_ID"]), '']
            lines += [f'{i}. **{x["SUG_TITLE"]}**' + (f' – {x["SUG_SUMMARY"]}' if x['SUG_SUMMARY'] else '')
                      for i, x in enumerate(proposals, start=1)]
            lines += ['', view_message('view.chapter_research.sub_sub_create_as_suggestion_numbers', p_a=note)]
        wtext = [view_message('view.chapter_research.ignore'), view_message('view.chapter_research.distinguish'), view_message('view.chapter_research.connect'), view_message('view.chapter_research.include_strongly')]
        ctx = []
        if prev_label:
            ctx.append(view_message('view.chapter_research.previous', p_a=prev_label, p_b=values["PREV_WEIGHT"], p_c=wtext[values["PREV_WEIGHT"]]))
        if next_label:
            ctx.append(view_message('view.chapter_research.next', p_a=next_label, p_b=values["NEXT_WEIGHT"], p_c=wtext[values["NEXT_WEIGHT"]]))
        if ctx:
            lines += ['', view_message('view.chapter_research.context'), '', view_message('view.chapter_research.chapter_weight'), '|---|---|---|'] + ctx
        tname = {'goal': view_message('view.chapter_research.research_the_chapter_goal'), 'sections': view_message('view.chapter_research.create_sections'), 'summary': view_message('view.chapter_research.create_a_summary')}
        lines += ['', view_message('view.chapter_research.task', p_a=tname.get(task, view_message('view.chapter_research.none_question_only'))),
                  '', f'<sub>{values["RESEARCH_PROVIDER_TEXT"]} · {count}</sub>', '',
                  view_message('view.chapter_research.edit_with_one_goal_or_summary_per')]
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
    data = library.build_library(cwd=base)
    if not data.get('books'):   # ohne Remote (lokale Bibliothek): die lokalen Branches
        data = library.build_library('refs/heads', base)
    return data


def de_date(iso):
    m = re.match(r'(\d{4})-(\d{2})-(\d{2})', iso or '')
    return (m.group(0) if UI.get('language') == 'en' else f'{m.group(3)}.{m.group(2)}.{m.group(1)}') if m else ''


def plural(n, one, many):
    return f'{n} {one if n == 1 else many}'


def book_row(b):
    ready = b['status'] == 'ready'
    st, sa = b.get('sections_total', 0), b.get('sections_approved', 0)
    progress = (f'{sa} von {plural(st, "Abschnitt", "Abschnitten")} freigegeben · '
                f'{b.get("chapters_approved", 0)} von {plural(b.get("chapters_total", 0), "Kapitel", "Kapiteln")}') if ready else 'Gliederung noch offen'
    ed = b.get('current_edition') or 0
    result = {'BOOK_SECTION_COUNT': st, 'BOOK_APPROVED_SECTION_COUNT': sa,
            'BOOK_CHAPTER_COUNT': b.get('chapters_total', 0), 'BOOK_APPROVED_CHAPTER_COUNT': b.get('chapters_approved', 0),
            'BOOK_EDITION_NUMBER': ed, 'BOOK_PENDING_COUNT': b.get('pending') or 0,
            'BOOK_AUTHOR_NAME': b.get('author') or '', 'BOOK_UPDATED_AT': b.get('updated_at') or '',
            'BOOK_TITLE_EMPTY': not (b['title'] or b['title_short']),
            'BOOK_BRANCH': b['branch'], 'BOOK_TITLE': b['title'] or b['title_short'] or 'Ohne Titel',
            'BOOK_TITLE_SHORT': b['title_short'] or b['branch'].split('/')[-1],
            'BOOK_AUTHOR_TEXT': f'von {b["author"]}' if b.get('author') else '',
            'BOOK_STATE': 'ready' if ready else 'setup', 'BOOK_STATE_TEXT': 'eingerichtet' if ready else 'im Aufbau',
            'BOOK_PROGRESS': round(100 * sa / st) if st else 0, 'BOOK_PROGRESS_TEXT': progress,
            'BOOK_EDITION_TEXT': f'Auflage {ed}' if ed else 'noch keine Auflage',
            'BOOK_COST': (b.get('cost') or {}).get('text') or money(0, False),
            'BOOK_PENDING_TEXT': f'{plural(b["pending"], "Änderung", "Änderungen")} offen' if b.get('pending') else '',
            'BOOK_UPDATED_TEXT': f'{"zuletzt geändert" if ready else "angelegt"} am {de_date(b.get("updated_at"))}' if b.get('updated_at') else ''}

    if UI.get('language') == 'en':
        result.update({
            'BOOK_TITLE': b['title'] or b['title_short'] or view_message('book.untitled'),
            'BOOK_STATE_TEXT': view_message('book.ready') if ready else view_message('book.setup'),
            'BOOK_PROGRESS_TEXT': view_message('book.progress', approved=sa, total=st,
                chapters=b.get('chapters_approved', 0), chapter_total=b.get('chapters_total', 0),
                section_word=view_message('book.section_one') if st == 1 else view_message('book.sections'),
                chapter_word=view_message('book.chapter_one') if b.get('chapters_total', 0) == 1 else view_message('book.chapters')) if ready else view_message('book.outline_pending'),
            'BOOK_EDITION_TEXT': view_message('book.edition', number=ed) if ed else view_message('book.no_edition'),
            'BOOK_PENDING_TEXT': (view_message('book.pending_one', number=b['pending']) if b['pending'] == 1 else
                                  view_message('book.pending', number=b['pending'])) if b.get('pending') else '',
            'BOOK_UPDATED_TEXT': (view_message('book.updated', date=de_date(b['updated_at'])) if ready else
                                  view_message('book.created', date=de_date(b['updated_at']))) if b.get('updated_at') else ''})
    return result


def library_series(base, data):
    """Serien (#116) aus library.json bzw. vom Standard-Branch: [{id, title, …, volumes: [branch]}]."""
    if 'series' in data:
        return data['series'] or []
    import series
    return [dict(s, volumes=series.volumes(s)) for s in series.load_all(base).values()]


def library_view(base, config, args):
    data = library_data(base, args)
    books = data.get('books') or []
    by_branch = {b['branch']: b for b in books}
    ser = library_series(base, data)
    rows, seen = [], set()
    # Bücher einer Serie zuerst, gruppiert und in Bandreihenfolge (#116); danach die übrigen
    for si, s in enumerate(ser, start=1):
        for n, br in enumerate(s['volumes'], start=1):
            if br in by_branch:
                r = book_row(by_branch[br])
                r.update({'BOOK_SERIES': s['id'], 'BOOK_SERIES_TITLE': s['title'], 'BOOK_SERIES_KEY': f'S{si}',
                          'BOOK_VOLUME_NUMBER': n, 'BOOK_VOLUME_TEXT': f'Band {n}'})
                rows.append(r)
                seen.add(br)
    for b in books:
        if b['branch'] not in seen:
            rows.append(dict(book_row(b), BOOK_SERIES='', BOOK_SERIES_TITLE='', BOOK_SERIES_KEY='', BOOK_VOLUME_TEXT=''))
    empty_series = [{'S_ID': s['id'], 'S_TITLE': s['title'], 'S_KEY': f'S{i}'} for i, s in enumerate(ser, start=1)
                    if not any(br in by_branch for br in s['volumes'])]
    count = plural(len(rows), 'Buch', 'Bücher') + (f' · {plural(len(ser), "Serie", "Serien")}' if ser else '')
    if args.text:
        out = [f'### 📚 Bücherregal', f'{repo_label(args)} · {count}', '']
        if rows:
            out += ['| # | Buch | Status | Fortschritt | Auflage | Kosten |', '|--:|---|---|---|---|--:|']
            group = None
            for i, r in enumerate(rows, 1):
                if r['BOOK_SERIES'] != group:
                    group = r['BOOK_SERIES']
                    label = f'📚 **Serie „{r["BOOK_SERIES_TITLE"]}“** (`{r["BOOK_SERIES_KEY"]}`)' if group else '**Einzelne Bücher**'
                    out.append(f'| | {label} | | | | |')
                vol = f'{r["BOOK_VOLUME_TEXT"]}: ' if r['BOOK_VOLUME_TEXT'] else ''
                out.append(f'| {i} | {vol}**{r["BOOK_TITLE"]}** ({r["BOOK_TITLE_SHORT"]}){" · ⏳ " + r["BOOK_PENDING_TEXT"] if r["BOOK_PENDING_TEXT"] else ""} | '
                           f'{"✅ eingerichtet" if r["BOOK_STATE"] == "ready" else "🚧 im Aufbau"} | {progress_bar(r["BOOK_APPROVED_SECTION_COUNT"], r["BOOK_SECTION_COUNT"])} {r["BOOK_PROGRESS_TEXT"]} | {r["BOOK_EDITION_TEXT"]} | {r["BOOK_COST"]} |')
        else:
            out += ['*Hier steht noch kein Buch.*']
        if empty_series:
            out += ['', 'Serien ohne Band: ' + ', '.join(f'„{s["S_TITLE"]}“ (`{s["S_KEY"]}`)' for s in empty_series)]
        items = ([('1' if len(rows) == 1 else f'1–{len(rows)}', 'Buch öffnen')] if rows else [])
        if ser:
            items.append(('S1' if len(ser) == 1 else f'S1–S{len(ser)}', 'Serie öffnen'))
        items += [('N', 'Neues Buch'), ('NS', 'Neue Serie'), ('D', 'Daten')]
        out += ['', '---', menu(items)]
        return '\n'.join(out) + '\n'
    blocks = {'BOOKS': rows}
    if empty_series:
        blocks['EMPTY_SERIES'] = empty_series
    return fill('buecherregal.html', {'LIBRARY_NAME': repo_label(args), 'BOOK_COUNT_NUMBER': len(rows), 'SERIES_COUNT_NUMBER': len(ser),
                                      'BOOK_COUNT_TEXT': count, 'EMPTY': '' if rows else '1',
                                      'UPDATED_TEXT': ''}, blocks)


SERIES_KIND_DE = {'continuous': 'durchgehende Handlung', 'standalone': 'eigenständige Bände'}


def find_series(base, data, key):
    ser = library_series(base, data)
    for i, s in enumerate(ser, start=1):
        if key in (s['id'], f'S{i}', f's{i}') or (key or '').lower() == s.get('title', '').lower():
            return s
    raise SystemExit(view_message('series.not_found', name=key))


def series_view(base, config, args):
    """Seite „Serie“ (#116, Vorlage serie): Bände in Reihenfolge, Bücher ohne Serie zum Hinzufügen."""
    data = library_data(base, args)
    s = find_series(base, data, args.where)
    by_branch = {b['branch']: b for b in data.get('books') or []}
    in_any = {br for x in library_series(base, data) for br in x['volumes']}
    vols = []
    for n, br in enumerate(s['volumes'], start=1):
        b = by_branch.get(br)
        r = book_row(b) if b else {'BOOK_BRANCH': br, 'BOOK_TITLE': br, 'BOOK_TITLE_SHORT': br.split('/')[-1], 'BOOK_STATE': 'setup',
                                   'BOOK_STATE_TEXT': view_message('view.series.not_found'), 'BOOK_PROGRESS': 0, 'BOOK_PROGRESS_TEXT': '', 'BOOK_EDITION_TEXT': ''}
        vols.append({'V_NUMBER': n, 'V_BRANCH': br, 'V_TITLE': r['BOOK_TITLE'], 'V_TITLE_SHORT': r['BOOK_TITLE_SHORT'],
                     'V_STATE': r['BOOK_STATE'], 'V_STATE_TEXT': r['BOOK_STATE_TEXT'], 'V_PROGRESS': r['BOOK_PROGRESS'],
                     'V_PROGRESS_TEXT': r['BOOK_PROGRESS_TEXT'], 'V_EDITION_TEXT': r['BOOK_EDITION_TEXT']})
    cands = [{'C_BRANCH': b['branch'], 'C_TITLE': b['title'] or b['title_short'] or b['branch']}
             for b in data.get('books') or [] if b['branch'] not in in_any]
    values = {'SERIES_ID': s['id'], 'SERIES_TITLE': s['title'], 'SERIES_SUBTITLE': s.get('subtitle') or '',
              'SERIES_KIND_TEXT': view_series_kind(s.get('kind')), 'SERIES_DESCRIPTION': s.get('description') or '',
              'VOLUME_COUNT_TEXT': plural(len(vols), view_message('view.series.volume'), view_message('view.series.volumes')), 'LIBRARY_NAME': repo_label(args)}
    import series as series_mod   # gemeinsame Figuren und Begriffe (Stufe 2)
    schars = []
    for c in series_mod.characters(base, s['id']):
        h = character_file(base, c)[0]
        schars.append({'SC_ID': c['id'], 'SC_NAME': c['name'], 'SC_ROLE': view_labels('ROLE_DE').get(h.get('role'), ''), 'SC_SHORT': h.get('short', '')})
    sterms = [{'ST_TERM': x['term'], 'ST_TEXT': x['text']} for x in series_mod.glossary(base, s['id'])]
    om = series_mod.omnibus(base, s['id'])   # Sammelband (Stufe 4)
    if om:
        n = int(om.get('current_edition') or 0)
        values.update({'OMNIBUS_STATE': om.get('status', 'draft'), 'OMNIBUS_TITLE': om.get('title', ''),
                       'OMNIBUS_TEXT': f'{plural(len(om.get("volumes") or []), view_message('view.series.volume'), view_message('view.series.volumes'))} · '
                                       + (view_message('view.series.approved') if om.get('status') == 'approved' else view_message('view.series.draft_not_approved'))
                                       + (view_message('view.series.edition', p_a=n) if n else view_message('view.series.no_edition_yet'))})
    if args.text:
        out = [view_message('view.series.series', p_a=s["title"]), ' · '.join(x for x in (values['SERIES_SUBTITLE'], values['SERIES_KIND_TEXT'],
                                                                  values['VOLUME_COUNT_TEXT']) if x), '']
        if values['SERIES_DESCRIPTION']:
            out += [f'> {values["SERIES_DESCRIPTION"]}', '']
        if vols:
            out += [view_message('view.series.volume_book_status_progress_edition'), '|--:|---|---|---|---|']
            out += [f'| {v["V_NUMBER"]} | **{v["V_TITLE"]}** (`{v["V_BRANCH"]}`) | {v["V_STATE_TEXT"]} | {v["V_PROGRESS_TEXT"] or "–"} | {v["V_EDITION_TEXT"] or "–"} |' for v in vols]
        else:
            out += [view_message('view.series.no_volumes_yet')]
        if cands:
            out += ['', view_message('view.series.outside_a_series') + ', '.join(f'{c["C_TITLE"]} (`{c["C_BRANCH"]}`)' for c in cands)]
        out += ['', view_message('view.series.series_characters', p_a=len(schars)), '']
        out += [f'- {c["SC_NAME"]} ({c["SC_ROLE"]}){": " + c["SC_SHORT"] if c["SC_SHORT"] else ""}' for c in schars] or [view_message('view.series.none')]
        out += ['', view_message('view.series.series_terms', p_a=len(sterms)), '']
        out += [f'- {x["ST_TERM"]}: {x["ST_TEXT"]}' for x in sterms] or [view_message('view.series.none')]
        out += ['', view_message('view.series.these_apply_to_all_volumes_a_volume')]
        out += ['', view_message('view.series.omnibus_sb_edit', p_a=values["OMNIBUS_TITLE"], p_b=values["OMNIBUS_TEXT"])
                if om else view_message('view.series.omnibus_none_yet_sb_create')]
        items = ([('1' if len(vols) == 1 else f'1–{len(vols)}', view_message('view.series.open_volume'))] if vols else [])
        items += ([('H', view_message('view.series.add_volume'))] if cands else []) + ([('R', view_message('view.series.change_order')), ('ENT', view_message('view.series.remove_volume'))] if vols else [])
        items += [('NB', view_message('view.series.new_book_in_this_series')), ('B', view_message('view.series.edit_series')), ('FV', view_message('view.series.suggest_characters_from_all_volumes')),
                  ('Ü', view_message('view.series.library'))]
        out += ['', '---', menu(items)]
        return '\n'.join(out) + '\n'
    blocks = {'VOLUMES': vols}
    if cands:
        blocks['CANDIDATES'] = cands
    if schars:
        blocks['SERIES_CHARACTERS'] = schars
    if sterms:
        blocks['SERIES_TERMS'] = sterms
    return fill('serie.html', values, blocks)


KEEP_DE = {'dedication': 'Widmung', 'foreword': 'Vorwort', 'prologue': 'Prolog', 'epilogue': 'Epilog',
           'afterword': 'Nachwort', 'acknowledgments': 'Danksagung'}


def scope_text(scope, config=None):
    if scope in (None, '', 'book', 'buch'):
        return view_message('view.scope_text.whole_book')
    if re.fullmatch(r'\d+', scope):
        return view_message('view.scope_text.chapter', p_a=scope)
    if re.fullmatch(r'\d+\.\d+', scope):
        return view_message('view.scope_text.section', p_a=scope)
    if scope.startswith('ser-'):
        return view_message('view.scope_text.all_volumes_of_the_series')
    item = find_matter(config or {'structure': {}}, scope) if config else None
    return item['title'] if item else scope


FIELD_DE = {'age': 'Alter', 'appearance': 'Aussehen', 'voice': 'Sprechweise', 'short': 'Kurz', 'traits': 'Eigenschaften'}


def character_suggest_view(base, config, args):
    """Vorschläge „Figuren aus dem Text“ (#53, Vorlage figuren-vorschlag). --draft: JSON (Datei oder Text) des
    Assistenten mit scope und items [{name, aliases, role, short, age, appearance, traits, voice, relations,
    sections, evidence [{where, quote}]}]; where = Bereich (book, N, N.M, Teil bzw. ser-…)."""
    raw = args.draft or '{}'
    data = json.loads(Path(raw).read_text(encoding='utf-8') if Path(raw).is_file() else raw)
    scope = data.get('scope') or args.where or 'book'
    is_series = str(scope).startswith('ser-')
    if is_series:   # Serienebene: auf dem Standard-Branch
        import series as series_mod
        s, _ = series_mod.get(base, scope)
        known = series_mod.characters(base, s['id'])
        ser = {'id': s['id'], 'title': s['title']}
        find = lambda n: next((c for c in known if n.strip().casefold() in (c['id'], c['name'].casefold())), None)
    else:
        ser = config.get('_series') or {}
        known = character_items(config)
        find = lambda n: find_character(config, n)
    rows = []
    for i, it in enumerate(data.get('items') or []):
        hit = None
        for n in [it.get('name', '')] + list(it.get('aliases') or []):
            hit = hit or (find(n) if n else None)
        state = 'new' if not hit else ('series' if ('_series' in hit or is_series) else 'existing')
        details = '; '.join(x for x in (view_message('view.character_suggest.age', p_a=it["age"]) if it.get('age') else '', it.get('appearance') or '',
                                        ', '.join(it.get('traits') or []), view_message('view.character_suggest.speaks', p_a=it["voice"]) if it.get('voice') else '') if x)
        ev = it.get('evidence') or []
        rows.append({'S_IDX': i, 'S_NAME': it.get('name', ''), 'S_ALIASES': ', '.join(it.get('aliases') or []),
                     'S_ROLE': it.get('role') if it.get('role') in view_labels('ROLE_DE') else 'supporting', 'S_SHORT': it.get('short', ''),
                     'S_DETAILS': details, 'S_SECTIONS': ', '.join(str(x) for x in it.get('sections') or []),
                     'S_EVIDENCE': ' · '.join(f'{e.get("where", "")}: „{e.get("quote", "")}“' for e in ev[:3]),
                     'S_STATE': state, 'S_EXISTING': hit['name'] if hit else '',
                     'S_STATE_TEXT': {'new': view_message('view.character_suggest.new'), 'existing': view_message('view.character_suggest.already_exists', p_a=hit["name"]) if hit else '',
                                      'series': view_message('view.character_suggest.series_character', p_a=hit["name"]) if hit else ''}[state]})
    conflicts = '; '.join(f'{c["name"]}, {view_labels('FIELD_DE').get(c["field"], c["field"])}: ' + ' / '.join(str(v) for v in c['values'])
                          for c in data.get('conflicts') or [])
    values = {'RUN_TEXT': view_message('view.character_suggest.background_run_from', p_a=data["run"][4:], p_b=de_date(str(data.get("created_at", "")))) if data.get('run') else '',
              'RUN_ID': data.get('run', ''), 'CONFLICTS_TEXT': conflicts,
              'SCOPE': str(scope), 'SCOPE_TEXT': scope_text(str(scope), config), 'SERIES_ID': ser.get('id', ''),
              'SERIES_TITLE': ser.get('title', ''), 'SERIES_LEVEL': '1' if is_series else '',
              'SUGGEST_COUNT_TEXT': plural(len(rows), view_message('view.character_suggest.suggestion'), view_message('view.character_suggest.suggestions'))}
    if args.text:
        out = [view_message('view.character_suggest.characters_from_the_text', p_a=values["SCOPE_TEXT"]), values['SUGGEST_COUNT_TEXT'] +
               (view_message('view.character_suggest.series', p_a=ser["title"]) if ser else '') + (f' · {values["RUN_TEXT"]}' if values['RUN_TEXT'] else ''), '']
        if conflicts:
            out += [view_message('view.character_suggest.contradictions_in_the_text', p_a=conflicts), '']
        if rows:
            out += [view_message('view.character_suggest.character_role_short_description_details_sections_status'), '|--:|---|---|---|---|---|---|']
            out += [f'| {r["S_IDX"] + 1} | **{r["S_NAME"]}**{" (" + r["S_ALIASES"] + ")" if r["S_ALIASES"] else ""} | {view_labels('ROLE_DE')[r["S_ROLE"]]} | '
                    f'{r["S_SHORT"] or "–"} | {r["S_DETAILS"] or "–"} | {r["S_SECTIONS"] or "–"} | {r["S_STATE_TEXT"]} |' for r in rows]
        else:
            out += [view_message('view.character_suggest.no_characters_found_in_the_text')]
        out += ['', view_message('view.character_suggest.from_the_text_only_the_text_itself'),
                '', '---', menu([(view_message('view.character_suggest.apply'), view_message('view.character_suggest.apply_these')), (view_message('view.character_suggest.all'), view_message('view.character_suggest.apply_all')),
                                 ('2 = Opi', view_message('view.character_suggest.merge_suggestion_with_an_existing_character')), ('X', view_message('view.character_suggest.discard'))]
                                + ([(view_message('view.character_suggest.series_2'), view_message('view.character_suggest.create_as_a_series_character'))] if ser and not is_series else []))]
        return '\n'.join(out) + '\n'
    merge = [{'M_ID': c['id'], 'M_NAME': c['name']} for c in known]
    return fill('figuren-vorschlag.html', values, {'SUGGESTIONS': rows, 'MERGE': merge})


def analysis_suggest_view(base, config, args):
    """Vorschläge eines Hintergrundlaufs (#124) zum Auswählen: --draft = analysis/<art>/run-NNN.json. Figuren gehen an
    character-suggest, die anderen Arten an ihre eigene Vorlage."""
    raw = args.draft or args.where or ''
    path = Path(raw) if Path(raw).is_file() else base / raw
    data = json.loads(path.read_text(encoding='utf-8'))
    kind = data.get('kind') or 'characters'
    if kind == 'characters':
        args.draft = str(path)
        return character_suggest_view(base, config, args)
    run_text = view_message('view.analysis_suggest.background_run_from', p_a=data["run"][4:], p_b=de_date(str(data.get("created_at", "")))) if data.get('run') else ''
    return ANALYSIS_VIEWS[kind](base, config, args, data, run_text)


def summaries_suggest_view(base, config, args, data, run_text):
    """Kurzbeschreibung und Ziel je Kapitel und Abschnitt (Vorlage kurzbeschreibung-vorschlag): Vorschlag, bisheriger
    Text, Fundstellen. Vorangehakt sind nur Felder, die noch leer sind."""
    rows = []
    for i, it in enumerate(data.get('items') or []):
        ch = sec = None
        for c in config['structure']['chapters']:
            if it['level'] == 'chapter' and c['id'] == it['target']:
                ch = c
            for x in c['sections']:
                if it['level'] == 'section' and x['id'] == it['target']:
                    sec = x
        if it['level'] == 'chapter' and ch:
            _, cur_short, cur_goal = chapter_readme(base, ch)
        elif sec:
            _, cur_goal, cur_short, _ = section_file(base, sec)
        else:
            continue   # Kapitel bzw. Abschnitt gibt es nicht mehr
        clean = lambda v: '' if v.startswith('<') and v.endswith('>') else v   # Platzhalter aus der Vorlage
        cur_short, cur_goal = clean(cur_short), clean(cur_goal)
        rows.append({'S_IDX': i, 'S_LEVEL': it['level'], 'S_LABEL': view_message('view.summaries_suggest.chapter', p_a=it["number"]) if it['level'] == 'chapter' else it['number'],
                     'S_TITLE': (ch or sec)['title'], 'S_GOAL': it.get('goal', ''), 'S_SHORT': it.get('short', ''),
                     'S_GOAL_NOW': cur_goal, 'S_SHORT_NOW': cur_short,
                     'S_GOAL_ON': '1' if it.get('goal') and not cur_goal else '', 'S_SHORT_ON': '1' if it.get('short') and not cur_short else '',
                     'S_EVIDENCE': ' · '.join(f'{e.get("where", "")}: „{e.get("quote", "")}“' for e in (it.get('evidence') or [])[:2])})
    values = {'RUN_ID': data.get('run', ''), 'RUN_TEXT': run_text, 'KIND': 'summaries',
              'SUGGEST_COUNT_TEXT': plural(len(rows), view_message('view.summaries_suggest.suggestion'), view_message('view.summaries_suggest.suggestions')), 'SCOPE_TEXT': scope_text(str(data.get('scope') or 'book'), config)}
    if args.text:
        out = [view_message('view.summaries_suggest.summary_and_goal', p_a=values["SCOPE_TEXT"]), values['SUGGEST_COUNT_TEXT'] + (f' · {run_text}' if run_text else ''), '']
        for r in rows:
            out += [f'**{r["S_IDX"] + 1}. {r["S_LABEL"]} {r["S_TITLE"]}**',
                    view_message('view.summaries_suggest.goal', p_a=r["S_GOAL"] or "–") + (view_message('view.summaries_suggest.current', p_a=r["S_GOAL_NOW"]) if r['S_GOAL_NOW'] else view_message('view.summaries_suggest.currently_empty')),
                    view_message('view.summaries_suggest.summary', p_a=r["S_SHORT"] or "–") + (view_message('view.summaries_suggest.current', p_a=r["S_SHORT_NOW"]) if r['S_SHORT_NOW'] else view_message('view.summaries_suggest.currently_empty')),
                    view_message('view.summaries_suggest.cited_passages', p_a=r["S_EVIDENCE"] or "–"), '']
        if not rows:
            out += [view_message('view.summaries_suggest.no_suggestions'), '']
        out += [view_message('view.summaries_suggest.from_the_text_only_the_text_itself'), '', '---',
                menu([(view_message('view.summaries_suggest.apply'), view_message('view.summaries_suggest.apply_these_empty_fields_only')), (view_message('view.summaries_suggest.all'), view_message('view.summaries_suggest.fill_all_empty_fields')),
                      (view_message('view.summaries_suggest.replace'), view_message('view.summaries_suggest.also_replace_existing_text')), ('X', view_message('view.summaries_suggest.discard'))])]
        return '\n'.join(out) + '\n'
    return fill('kurzbeschreibung-vorschlag.html', values, {'SUGGESTIONS': rows})


def style_suggest_view(base, config, args, data, run_text):
    """Stilprofil (Vorlage stilprofil-vorschlag): je Angabe Vorschlag, bisheriger Wert aus `style`, abweichende
    Kapitel, Fundstellen; dazu die Zahlen ohne KI. Vorangehakt: Angaben, die bisher fehlen."""
    import analyze
    now = config.get('style') or {}
    rows = []
    for i, it in enumerate(data.get('items') or []):
        cur = now.get(it['field'])
        cur = ', '.join(cur) if isinstance(cur, list) else str(cur or '')
        rows.append({'S_IDX': i, 'S_FIELD': it['field'], 'S_LABEL': view_labels('STYLE_DE').get(it['field'], it['field']),
                     'S_VALUE': it['value'], 'S_NOW': cur, 'S_ON': '' if cur else '1',
                     'S_VARIANTS': '; '.join(f'{v["value"]} in {", ".join(v["where"])}' for v in it.get('variants') or []),
                     'S_EVIDENCE': ' · '.join(f'{e.get("where", "")}: „{e.get("quote", "")}“' for e in (it.get('evidence') or [])[:2])})
    st = data.get('stats') or {}
    parts = []
    if st.get('sentence_length_avg') is not None:
        parts.append(view_message('view.style_suggest.words_per_sentence', p_a=str(st["sentence_length_avg"]).replace(".", "." if UI.get('language') == 'en' else ",")))
    if st.get('dialogue_share') is not None:
        parts.append(view_message('view.style_suggest.dialogue', p_a=round(st["dialogue_share"] * 100)))
    if st.get('words'):
        parts.append(view_message('view.style_suggest.words', p_a=st["words"]))
    values = {'RUN_ID': data.get('run', ''), 'RUN_TEXT': run_text, 'KIND': 'style',
              'STATS_TEXT': ' · '.join(parts), 'SCOPE_TEXT': scope_text(str(data.get('scope') or 'book'), config),
              'SUGGEST_COUNT_TEXT': plural(len(rows), view_message('view.style_suggest.disclosure'), view_message('view.style_suggest.fields'))}
    if args.text:
        out = [view_message('view.style_suggest.style_profile', p_a=values["SCOPE_TEXT"]), values['SUGGEST_COUNT_TEXT'] + (f' · {run_text}' if run_text else ''), '']
        if rows:
            out += [view_message('view.style_suggest.field_suggestion_current_differs'), '|--:|---|---|---|---|']
            out += [f'| {r["S_IDX"] + 1} | {r["S_LABEL"]} | {r["S_VALUE"]} | {r["S_NOW"] or "–"} | {r["S_VARIANTS"] or "–"} |' for r in rows]
        else:
            out += [view_message('view.style_suggest.no_findings_with_a_cited_passage')]
        out += ['', view_message('view.style_suggest.counted_without_ai', p_a=values["STATS_TEXT"] or "–"), '',
                view_message('view.style_suggest.the_style_profile_is_stored_in_ghostwriter'),
                '', '---', menu([(view_message('view.style_suggest.apply'), view_message('view.style_suggest.apply_these_fields')), (view_message('view.style_suggest.all'), view_message('view.style_suggest.apply_all')),
                                  (view_message('view.style_suggest.past_tense'), view_message('view.style_suggest.set_field_to_another_value')), ('X', view_message('view.style_suggest.discard'))])]
        return '\n'.join(out) + '\n'
    return fill('stilprofil-vorschlag.html', values, {'SUGGESTIONS': rows})


def places_suggest_view(base, config, args, data, run_text):
    """Schauplätze (Vorlage orte-vorschlag): Name, Art, ein Satz, Abschnitte, Fundstellen, Stand gegenüber
    story/places.yml; „Zusammenlegen mit“ einem vorhandenen Ort."""
    import analyze
    p = analyze.story_file(base, 'places')
    known = ((yaml.safe_load(p.read_text(encoding='utf-8')) or {}).get('places') or []) if p.is_file() else []
    rows = []
    for i, it in enumerate(data.get('items') or []):
        names = {analyze.norm(x) for x in [it['name']] + list(it.get('aliases') or [])}
        hit = next((k for k in known if names & {analyze.norm(x) for x in [k['name']] + list(k.get('aliases') or [])}), None)
        rows.append({'S_IDX': i, 'S_NAME': it['name'], 'S_ALIASES': ', '.join(it.get('aliases') or []), 'S_KIND': it.get('kind', ''),
                     'S_SHORT': it.get('short', ''), 'S_SECTIONS': ', '.join(it.get('sections') or []),
                     'S_EVIDENCE': ' · '.join(f'{e.get("where", "")}: „{e.get("quote", "")}“' for e in (it.get('evidence') or [])[:2]),
                     'S_STATE': 'existing' if hit else 'new', 'S_STATE_TEXT': view_message('view.places_suggest.already_exists', p_a=hit["name"]) if hit else view_message('view.places_suggest.new'),
                     'S_EXISTING': hit['id'] if hit else ''})
    values = {'RUN_ID': data.get('run', ''), 'RUN_TEXT': run_text, 'KIND': 'places',
              'SCOPE_TEXT': scope_text(str(data.get('scope') or 'book'), config), 'SUGGEST_COUNT_TEXT': plural(len(rows), view_message('view.places_suggest.location'), view_message('view.places_suggest.places'))}
    if args.text:
        out = [view_message('view.places_suggest.places_from_the_text', p_a=values["SCOPE_TEXT"]), values['SUGGEST_COUNT_TEXT'] + (f' · {run_text}' if run_text else ''), '']
        if rows:
            out += [view_message('view.places_suggest.place_kind_description_sections_status'), '|--:|---|---|---|---|---|']
            out += [f'| {r["S_IDX"] + 1} | **{r["S_NAME"]}**{" (" + r["S_ALIASES"] + ")" if r["S_ALIASES"] else ""} | {r["S_KIND"] or "–"} | '
                    f'{r["S_SHORT"] or "–"} | {r["S_SECTIONS"] or "–"} | {r["S_STATE_TEXT"]} |' for r in rows]
        else:
            out += [view_message('view.places_suggest.no_places_with_a_cited_passage')]
        out += ['', view_message('view.places_suggest.from_the_text_only_applied_to_story'),
                '', '---', menu([(view_message('view.places_suggest.apply'), view_message('view.places_suggest.apply_these')), (view_message('view.places_suggest.all'), view_message('view.places_suggest.apply_all')),
                                  ('2 = Seehaus', view_message('view.places_suggest.merge_suggestion_with_an_existing_place')), ('X', view_message('view.places_suggest.discard'))])]
        return '\n'.join(out) + '\n'
    merge = [{'M_ID': k['id'], 'M_NAME': k['name']} for k in known]
    return fill('orte-vorschlag.html', values, {'SUGGESTIONS': rows, 'MERGE': merge})


def timeline_suggest_view(base, config, args, data, run_text):
    """Zeitleiste (Vorlage zeitleiste-vorschlag): Ereignisse in Buchreihenfolge mit Zeitangabe und Fundstelle, dazu
    die Auffälligkeiten (Zeitsprung, Widerspruch, unklar) mit Verweis auf die Ereignisse."""
    import analyze
    issues = data.get('issues') or []
    flagged = {n for x in issues for n in x['events']}
    events = [{'E_IDX': i, 'E_N': e['n'], 'E_WHERE': e['where'], 'E_WHEN': e.get('when', ''), 'E_WHAT': e['what'],
               'E_FLAG': '1' if e['n'] in flagged else '',
               'E_EVIDENCE': ' · '.join(f'„{x.get("quote", "")}“' for x in (e.get('evidence') or [])[:1])}
              for i, e in enumerate(data.get('items') or [])]
    rows = [{'I_IDX': i, 'I_KIND': x['kind'], 'I_KIND_TEXT': view_labels('TIMELINE_KIND_DE').get(x['kind'], x['kind']),
             'I_EVENTS': ', '.join(map(str, x['events'])), 'I_TEXT': x['text']} for i, x in enumerate(issues)]
    values = {'RUN_ID': data.get('run', ''), 'RUN_TEXT': run_text, 'KIND': 'timeline',
              'SCOPE_TEXT': scope_text(str(data.get('scope') or 'book'), config),
              'SUGGEST_COUNT_TEXT': plural(len(events), view_message('view.timeline_suggest.event'), view_message('view.timeline_suggest.events')) + ' · ' + plural(len(rows), view_message('view.timeline_suggest.finding'), view_message('view.timeline_suggest.findings'))}
    if args.text:
        out = [view_message('view.timeline_suggest.timeline', p_a=values["SCOPE_TEXT"]), values['SUGGEST_COUNT_TEXT'] + (f' · {run_text}' if run_text else ''), '']
        if rows:
            out += [view_message('view.timeline_suggest.events_2', p_a=r["I_KIND_TEXT"], p_b=r["I_EVENTS"], p_c=r["I_TEXT"]) for r in rows] + ['']
        if events:
            out += [view_message('view.timeline_suggest.section_when_what'), '|--:|---|---|---|']
            out += [f'| {e["E_N"]}{" ⚠️" if e["E_FLAG"] else ""} | {e["E_WHERE"]} | {e["E_WHEN"] or "–"} | {e["E_WHAT"]} |' for e in events]
        else:
            out += [view_message('view.timeline_suggest.no_events_with_a_cited_passage')]
        out += ['', view_message('view.timeline_suggest.from_the_text_only_findings_are_notes'), '', '---',
                menu([(view_message('view.timeline_suggest.all'), view_message('view.timeline_suggest.apply_all_events_and_notes')), (view_message('view.timeline_suggest.without'), view_message('view.timeline_suggest.apply_all_except_these_events')),
                      (view_message('view.timeline_suggest.notes_without'), view_message('view.timeline_suggest.omit_this_note')), ('X', view_message('view.timeline_suggest.discard'))])]
        return '\n'.join(out) + '\n'
    blocks = {'EVENTS': events}
    if rows:
        blocks['ISSUES'] = rows
    return fill('zeitleiste-vorschlag.html', values, blocks)


def continuity_suggest_view(base, config, args, data, run_text):
    """Mögliche Widersprüche (Vorlage widerspruch-vorschlag): je Widerspruch ein Satz und die beteiligten Fundstellen;
    gewählt wird, hinter welche Fundstellen ein Marker [KONTINUITÄT PRÜFEN: …] kommt (vorgewählt: die letzte)."""
    rows, facts = [], []
    for i, it in enumerate(data.get('items') or []):
        rows.append({'S_IDX': i, 'S_TEXT': it['text'], 'S_COUNT': len(it['facts'])})
        for k, f in enumerate(it['facts']):
            facts.append({'F_IDX': i, 'F_K': k, 'F_WHERE': f['where'], 'F_ABOUT': f.get('about', ''), 'F_FACT': f['fact'],
                          'F_QUOTE': f['quote'], 'F_ON': '1' if k == len(it['facts']) - 1 else ''})
    values = {'RUN_ID': data.get('run', ''), 'RUN_TEXT': run_text, 'KIND': 'continuity',
              'SCOPE_TEXT': scope_text(str(data.get('scope') or 'book'), config),
              'SUGGEST_COUNT_TEXT': plural(len(rows), view_message('view.continuity_suggest.possible_contradiction'), view_message('view.continuity_suggest.possible_contradictions')),
              'FACTS_TEXT': view_message('view.continuity_suggest.facts_compared_with_cited_passages', p_a=data.get("facts", 0))}
    if args.text:
        out = [view_message('view.continuity_suggest.possible_contradictions_2', p_a=values["SCOPE_TEXT"]), values['SUGGEST_COUNT_TEXT'] + f' · {values["FACTS_TEXT"]}'
               + (f' · {run_text}' if run_text else ''), '']
        for r in rows:
            out += [f'**{r["S_IDX"] + 1}. {r["S_TEXT"]}**']
            out += [f'- {chr(97 + f["F_K"])}) {f["F_WHERE"]}: „{f["F_QUOTE"]}“' for f in facts if f['F_IDX'] == r['S_IDX']] + ['']
        if not rows:
            out += [view_message('view.continuity_suggest.no_contradictions_found'), '']
        out += [view_message('view.continuity_suggest.applying_inserts_kontinuit_t_pr_fen_after'), '', '---',
                menu([(view_message('view.continuity_suggest.apply'), view_message('view.continuity_suggest.marker_at_the_last_cited_passage')), ('2: a, b', view_message('view.continuity_suggest.markers_at_these_cited_passages')),
                      ('X', view_message('view.continuity_suggest.discard'))])]
        return '\n'.join(out) + '\n'
    return fill('widerspruch-vorschlag.html', values, {'SUGGESTIONS': rows, 'FACTS': facts})


def language_suggest_view(base, config, args, data, run_text):
    """Sprachliche Hinweise (Vorlage sprache-vorschlag): je Abschnitt die Auffälligkeiten mit Fundstelle; übernommen
    wird nur in die Hinweisliste, der Text bleibt unverändert."""
    import analyze
    rows = [{'S_IDX': i, 'S_WHERE': h['where'], 'S_KIND': h['kind'], 'S_KIND_TEXT': view_labels('LANGUAGE_DE').get(h['kind'], h['kind']),
             'S_TEXT': h['text'], 'S_QUOTE': h['quote']} for i, h in enumerate(data.get('items') or [])]
    values = {'RUN_ID': data.get('run', ''), 'RUN_TEXT': run_text, 'KIND': 'language',
              'SCOPE_TEXT': scope_text(str(data.get('scope') or 'book'), config),
              'SUGGEST_COUNT_TEXT': plural(len(rows), view_message('view.language_suggest.note'), view_message('view.language_suggest.notes')),
              'RULES_TEXT': view_message('view.language_suggest.sentences_over_words_one_word_within_words', p_a=analyze.LONG_SENTENCE, p_b=analyze.REPEAT_MIN, p_c=analyze.REPEAT_WINDOW)}
    if args.text:
        out = [view_message('view.language_suggest.language_notes', p_a=values["SCOPE_TEXT"]), values['SUGGEST_COUNT_TEXT'] + (f' · {run_text}' if run_text else ''),
               view_message('view.language_suggest.counted_without_ai', p_a=values["RULES_TEXT"]), '']
        if rows:
            out += [view_message('view.language_suggest.section_kind_note_passage'), '|--:|---|---|---|---|']
            out += [f'| {r["S_IDX"] + 1} | {r["S_WHERE"]} | {r["S_KIND_TEXT"]} | {r["S_TEXT"]} | „{r["S_QUOTE"]}“ |' for r in rows]
        else:
            out += [view_message('view.language_suggest.no_findings')]
        out += ['', view_message('view.language_suggest.applied_only_to_the_section_notes_story'),
                '', '---', menu([(view_message('view.language_suggest.all'), view_message('view.language_suggest.apply_all_notes')), (view_message('view.language_suggest.without'), view_message('view.language_suggest.apply_all_except_these')), ('X', view_message('view.language_suggest.discard'))])]
        return '\n'.join(out) + '\n'
    return fill('sprache-vorschlag.html', values, {'SUGGESTIONS': rows})


ANALYSIS_VIEWS = {'summaries': summaries_suggest_view, 'style': style_suggest_view, 'places': places_suggest_view,
                  'timeline': timeline_suggest_view, 'continuity': continuity_suggest_view, 'language': language_suggest_view}


def import_preview_view(base, config, args):
    """Vorschau „Manuskript importieren“ (#124, Vorlage import-vorschau): Gliederung aus import/proposal.json."""
    import import_book
    p = import_book.load_proposal(base)
    st = p['stats']
    info = import_book.status(base) or {}
    rows = []
    for ci, c in enumerate(p['chapters'], start=1):
        rows.append({'R_TYPE': 'chapter', 'R_CHAPTER': ci, 'R_SECTION': '', 'R_LABEL': view_message('view.import_preview.chapter', p_a=ci), 'R_TITLE': c['title'],
                     'R_WORDS': sum(s['words'] for s in c['sections']), 'R_SCENES': '', 'R_LONG': '',
                     'R_COUNT': plural(len(c['sections']), view_message('view.import_preview.section'), view_message('view.import_preview.sections'))})
        for si, s in enumerate(c['sections'], start=1):
            rows.append({'R_TYPE': 'section', 'R_CHAPTER': ci, 'R_SECTION': si, 'R_LABEL': f'{ci}.{si}', 'R_TITLE': s['title'],
                         'R_WORDS': s['words'], 'R_SCENES': s['scenes'] if s['scenes'] > 1 else '',
                         'R_LONG': '1' if s['words'] > import_book.LONG_WORDS else '', 'R_COUNT': ''})
    parts = [{'P_IDX': k, 'P_KIND': x['kind'], 'P_AREA': x.get('area') or MATTER[x['kind']][0], 'P_TITLE': x['title'],
              'P_WORDS': x['words'], 'P_LABEL': view_matter_kind(x['kind'])} for k, x in enumerate(p['parts'], start=1)]
    stats_text = (view_message('view.import_preview.chapters_sections_front_back_matter_parts_of', p_a=st["chapters"], p_b=st["sections"], p_c=len(parts), p_d=st["words_proposal"], p_e=st["words_original"]))
    values = {'IMPORT_TITLE': p.get('title') or '', 'IMPORT_AUTHOR': p.get('author') or '', 'IMPORT_FORMAT': (p.get('format') or '').upper(),
              'STATS_TEXT': stats_text, 'LOSSLESS': '1' if st.get('lossless') else '', 'KEEP_TEXT': view_import_keep(info),
              'KINDS_TEXT': ', '.join(f'{k}={view_matter_kind(k)}' for k, v in MATTER.items())}
    outline = import_book.open_outline(base)
    if outline:   # KI-Vorschlag für die Gliederung liegt bereit
        values['OUTLINE_TEXT'] = (view_message('view.import_preview.an_ai_outline_suggestion_is_ready_chapters', p_a=len(outline["chapters"]), p_b=sum(len(c["sections"]) for c in outline["chapters"])))
    elif p.get('structure') == 'none' and len(p['chapters']) == 1:
        values['NO_STRUCTURE'] = '1'
    warns = [{'W_TEXT': (view_message('import.original_notice') + ': ' if UI.get('language') == 'en' else '') + w} for w in p.get('warnings') or []]
    if args.text:
        out = [view_message('view.import_preview.import_manuscript', p_a=values["IMPORT_TITLE"] or view_message('view.import_preview.untitled')),
               view_message('view.import_preview.author', p_a=values["IMPORT_FORMAT"], p_b=values["IMPORT_AUTHOR"] or "–", p_c=stats_text)
               + ('' if values['LOSSLESS'] else view_message('view.import_preview.incomplete')), '']
        out += [f'> ⚠️ {w["W_TEXT"]}' for w in warns] + ([''] if warns else [])
        out += [view_message('view.import_preview.part_words_note'), '|---|---|--:|---|']
        out += [f'| {x["P_LABEL"]} ({view_message('view.import_preview.front_matter') if x["P_AREA"] == "front" else view_message('view.import_preview.back_matter')}) | {x["P_TITLE"]} | {x["P_WORDS"]} | `T{x["P_IDX"]}` |'
                for x in parts if x['P_AREA'] == 'front']
        for r in rows:
            hint = (view_message('view.import_preview.very_long') if r['R_LONG'] else '') + (view_message('view.import_preview.scenes', p_a=r["R_SCENES"]) if r['R_SCENES'] else '')
            out.append(f'| **{r["R_LABEL"]}** | **{r["R_TITLE"]}** · {r["R_COUNT"]} | {r["R_WORDS"]} | |' if r['R_TYPE'] == 'chapter'
                       else f'| {r["R_LABEL"]} | {r["R_TITLE"]} | {r["R_WORDS"]} | {hint.strip(" ·")} |')
        out += [view_message('view.import_preview.back_matter_t', p_a=x["P_LABEL"], p_b=x["P_TITLE"], p_c=x["P_WORDS"], p_d=x["P_IDX"]) for x in parts if x['P_AREA'] != 'front']
        if values.get('OUTLINE_TEXT'):
            out += ['', view_message('import.view_outline', text=values['OUTLINE_TEXT'])]
        elif values.get('NO_STRUCTURE'):
            out += ['', view_message('view.import_preview.no_outline_detected_gk_suggest_an_outline')]
        out += ['', view_message('view.import_preview.request_changes_in_text_e_g_chapter'), '',
                '---', menu([('A', view_message('view.import_preview.create_book_as_shown')), ('AS', view_message('view.import_preview.create_and_grant_writing_permission_for_all')),
                             ('X', view_message('import.cancel'))])]
        return '\n'.join(out) + '\n'
    blocks = {'ROWS': rows}
    if parts:
        blocks['PARTS'] = parts
    if warns:
        blocks['WARNINGS'] = warns
    return fill('import-vorschau.html', values, blocks)


def import_outline_view(base, config, args):
    """KI-Vorschlag für die Gliederung beim Import (#124, Vorlage gliederung-vorschlag) aus import/outline.json:
    Kapitel und Abschnitte mit Titel, Wortzahl, Anfang (wörtlich) und Begründung."""
    import import_book
    o = import_book.open_outline(base)
    if not o:
        raise SystemExit(view_message('view.import_outline.there_is_no_pending_ai_outline_suggestion'))
    rows = []
    for ci, c in enumerate(o['chapters'], start=1):
        rows.append({'O_TYPE': 'chapter', 'O_CHAPTER': ci, 'O_SECTION': '', 'O_LABEL': view_message('view.import_outline.chapter', p_a=ci), 'O_TITLE': c['title'],
                     'O_START': c['start'], 'O_WORDS': c['words'], 'O_QUOTE': c['quote'], 'O_REASON': c.get('reason', ''),
                     'O_COUNT': plural(len(c['sections']), view_message('view.import_outline.section'), view_message('view.import_outline.sections'))})
        for si, sec in enumerate(c['sections'], start=1):
            rows.append({'O_TYPE': 'section', 'O_CHAPTER': ci, 'O_SECTION': si, 'O_LABEL': f'{ci}.{si}', 'O_TITLE': sec['title'],
                         'O_START': sec['start'], 'O_WORDS': sec['words'], 'O_QUOTE': sec['quote'],
                         'O_REASON': sec.get('reason', '') if si > 1 else '', 'O_COUNT': ''})
    n_secs = sum(len(c['sections']) for c in o['chapters'])
    values = {'RUN_ID': o['run'], 'RUN_TEXT': view_message('view.import_outline.suggestion_from', p_a=o["run"][8:], p_b=de_date(str(o.get("created_at", ""))), p_c=o.get("model", "")),
              'STATS_TEXT': view_message('view.import_outline.chapters_sections_from_paragraphs_openings_without_a', p_a=len(o["chapters"]), p_b=n_secs, p_c=o["paragraphs"], p_d=o["dropped"]),
              'PARTIAL_TEXT': '' if o.get('full_text', True) else view_message('view.import_outline.very_long_manuscript_the_ai_read_only')}
    if args.text:
        out = [view_message('view.import_outline.ai_outline_suggestion'), f'{values["STATS_TEXT"]} · {values["RUN_TEXT"]}', '']
        if values['PARTIAL_TEXT']:
            out += [f'> ⚠️ {values["PARTIAL_TEXT"]}', '']
        out += [view_message('view.import_outline.title_words_starts_with_reason'), '|---|---|--:|---|---|']
        out += [f'| **{r["O_LABEL"]}** | **{r["O_TITLE"]}** · {r["O_COUNT"]} | {r["O_WORDS"]} | „{r["O_QUOTE"]}“ | {r["O_REASON"]} |'
                if r['O_TYPE'] == 'chapter' else f'| {r["O_LABEL"]} | {r["O_TITLE"]} | {r["O_WORDS"]} | „{r["O_QUOTE"]}“ | {r["O_REASON"]} |'
                for r in rows]
        out += ['', view_message('view.import_outline.splits_occur_only_at_paragraph_boundaries_no'), '', '---',
                menu([(view_message('view.import_outline.apply'), view_message('view.import_outline.apply_outline_as_shown')), (view_message('view.import_outline.chapter_2'), view_message('view.import_outline.start_a_new_chapter_from')),
                      (view_message('view.import_outline.chapter_omit'), view_message('view.import_outline.merge_chapter_with_the_previous_one')), (view_message('view.import_outline.title'), view_message('view.import_outline.change_title')),
                      ('X', view_message('view.import_outline.discard'))])]
        return '\n'.join(out) + '\n'
    return fill('gliederung-vorschlag.html', values, {'ROWS': rows})


def omnibus_edit_view(base, config, args):
    """Formular „Sammelband“ (#116, Vorlage sammelband): Titel, Bände mit Auflage, Teile der Bände, Vor-/Nachwort."""
    import series as series_mod
    data = library_data(base, args)
    s = find_series(base, data, args.where)
    om = series_mod.omnibus(base, s['id']) or {}
    picked = {v['branch']: v.get('edition') for v in om.get('volumes') or []}
    by_branch = {b['branch']: b for b in data.get('books') or []}
    published = {v['branch']: v for v in series_mod.published_volumes(base, s)}   # Auflagen aus den Tags
    vols = []
    for n, br in enumerate(s['volumes'], start=1):
        b = by_branch.get(br) or {}
        last = (published.get(br) or {}).get('edition') or (b.get('last_edition') or {}).get('number') or 0
        title = (published.get(br) or {}).get('title') or b.get('title') or br
        vols.append({'OV_NUMBER': n, 'OV_BRANCH': br, 'OV_TITLE': title, 'OV_LAST': last,
                     'OV_ON': '1' if br in picked else '', 'OV_EDITION': picked.get(br) or '',
                     'OV_TEXT': view_message('view.omnibus_edit.latest_edition', p_a=last) if last else view_message('view.omnibus_edit.no_edition_yet')})
    keep = om.get('keep_matter', ['prologue', 'epilogue'])
    pub = om.get('publication') or {}
    values = {'SERIES_ID': s['id'], 'SERIES_TITLE': s['title'], 'OMNIBUS_TITLE': om.get('title') or view_message('view.omnibus_edit.omnibus', p_a=s["title"]),
              'OMNIBUS_SUBTITLE': om.get('subtitle', ''), 'OMNIBUS_STATE': om.get('status', '') if om else '',
              'OMNIBUS_FOREWORD': om.get('foreword', ''), 'OMNIBUS_AFTERWORD': om.get('afterword', ''),
              'OMNIBUS_ISBN_PRINT': pub.get('isbn_print', ''), 'OMNIBUS_ISBN_EBOOK': pub.get('isbn_ebook', ''),
              'OMNIBUS_EDITION': str(int(om.get('current_edition') or 0)),
              'OMNIBUS_TAG': series_mod.omnibus_tag(s, int(om.get('current_edition') or 0) + 1)}
    keeps = [{'K_KIND': k, 'K_LABEL': v, 'K_ON': '1' if k in keep else ''} for k, v in view_labels('KEEP_DE').items()]
    if args.text:
        out = [view_message('view.omnibus_edit.omnibus_2', p_a=values["OMNIBUS_TITLE"]), view_message('view.omnibus_edit.series', p_a=s["title"]) +
               ({'approved': view_message('view.omnibus_edit.approved'), 'draft': view_message('view.omnibus_edit.draft')}.get(values['OMNIBUS_STATE'], view_message('view.omnibus_edit.not_created_yet'))), '']
        out += [view_message('view.omnibus_edit.volume_book_in_omnibus_edition'), '|--:|---|---|---|']
        out += [f'| {v["OV_NUMBER"]} | {v["OV_TITLE"]} | {"✅" if v["OV_ON"] else "—"} | {v["OV_EDITION"] or v["OV_TEXT"]} |' for v in vols]
        out += ['', view_message('view.omnibus_edit.volume_parts_to_keep') + (', '.join(view_labels('KEEP_DE')[k] for k in keep) or view_message('view.omnibus_edit.none')), '']
        out += field_table([(view_message('view.omnibus_edit.title'), values['OMNIBUS_TITLE']), (view_message('view.omnibus_edit.subtitle'), values['OMNIBUS_SUBTITLE']),
                            (view_message('view.omnibus_edit.omnibus_foreword'), values['OMNIBUS_FOREWORD']), (view_message('view.omnibus_edit.afterword'), values['OMNIBUS_AFTERWORD']),
                            (view_message('view.omnibus_edit.print_isbn'), values['OMNIBUS_ISBN_PRINT']), (view_message('view.omnibus_edit.e_book_isbn'), values['OMNIBUS_ISBN_EBOOK'])])
        items = [(view_message('view.omnibus_edit.volumes'), view_message('view.omnibus_edit.set_selection')), ('FA', view_message('view.omnibus_edit.withdraw_approval') if values['OMNIBUS_STATE'] == 'approved' else view_message('view.omnibus_edit.approve_omnibus'))]
        if values['OMNIBUS_STATE'] == 'approved':
            items.append(('V', view_message('view.omnibus_edit.publish_edition', p_a=int(values["OMNIBUS_EDITION"]) + 1)))
        out += ['', view_message('settings.form_hint'), '', menu(items)]
        return '\n'.join(out) + '\n'
    return fill('sammelband.html', values, {'OVOLUMES': vols, 'KEEP': keeps})


def series_edit_view(base, config, args):
    """Formular „Neue Serie“ bzw. „Serie bearbeiten“ (#116, Vorlage serie-bearbeiten); --draft: gesendete Werte und error."""
    data = library_data(base, args)
    s = find_series(base, data, args.where) if args.where else None
    draft = json.loads(args.draft) if args.draft else {}
    v = lambda k, d='': draft.get(k, (s or {}).get(k, d))
    values = {'SERIES_ID': (s or {}).get('id', ''), 'SERIES_TITLE': v('title'), 'SERIES_SUBTITLE': v('subtitle'),
              'SERIES_KIND': v('kind', 'continuous'), 'SERIES_DESCRIPTION': v('description'), 'ERROR_TEXT': draft.get('error', ''),
              'SERIES_ISSN': v('issn'), 'SERIES_ALSO': 'false' if v('also_in_series', True) is False else 'true'}
    taken = [{'TAKEN_TITLE': x['title']} for x in library_series(base, data) if not s or x['id'] != s['id']]
    if args.text:
        out = [f"### 📚 {view_message('edit_series') if s else view_message('new_series')}", '']
        if values['ERROR_TEXT']:
            out += [f'> ✗ {values["ERROR_TEXT"]}', '']
        out += field_table([(view_message('series_title_required'), values['SERIES_TITLE']), (view_message('subtitle'), values['SERIES_SUBTITLE']),
                            (view_message('type'), view_series_kind(values['SERIES_KIND'])), (view_message('description'), values['SERIES_DESCRIPTION']),
                            (view_message('series_issn'), values['SERIES_ISSN']),
                            (view_message('also_in_this_series_page'), view_message('no') if values['SERIES_ALSO'] == 'false' else view_message('yes'))])
        out += ['', view_message('type_continuous_story_or_standalone_volumes'), '', view_message('form_hint')]
        return '\n'.join(out) + '\n'
    return fill('serie-bearbeiten.html', values, {'TAKEN': taken})


def book_create_view(base, config, args):
    """Formular „Neues Buch“ (#38). Vorhandene Bücher aus library.json bzw. live; --draft: gesendete Werte und error."""
    import library
    data = library_data(base, args)
    books = data.get('books') or []
    draft = json.loads(args.draft) if args.draft else {}
    latest = sorted((b for b in books if b.get('author')), key=lambda b: b.get('updated_at') or '')
    ser, series_text = None, ''
    if draft.get('series_id'):   # Neues Buch in einer Serie (#116): nächster Band, Autor vom letzten Band
        ser = find_series(base, data, draft['series_id'])
        series_text = f'Band {len(ser["volumes"]) + 1} der Serie „{ser["title"]}“'
        in_ser = [b for b in latest if b['branch'] in ser['volumes']]
        latest = in_ser or latest
    prof_path = Path(base, 'assistant.yml')   # Assistenten-Profil (#136): Autor der Bibliothek, außer in einer Serie
    prof_author = ((yaml.safe_load(prof_path.read_text(encoding='utf-8')) or {}).get('author') or '') if prof_path.is_file() else ''
    author = draft.get('author', (latest[-1]['author'] if latest and (ser or not prof_author) else prof_author)
                       if latest or prof_author else '')
    prefix = library.settings(library.load_manifest())['book_prefix']
    if args.text:
        out = ['### 📗 Neues Buch', '', 'Das Buch bekommt einen eigenen Bereich in dieser Bibliothek; danach folgt der Einstiegsdialog.', '']
        if series_text:
            out += [f'📚 {series_text}', '']
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
                                      'ERROR_TEXT': draft.get('error', ''),
                                      'SERIES_ID': ser['id'] if ser else '', 'SERIES_TITLE': ser['title'] if ser else '',
                                      'SERIES_VOLUME_NUMBER': len(ser['volumes']) + 1 if ser else 0, 'SERIES_TEXT': series_text},
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
    return d.strftime('%Y-%m-%d' if UI.get('language') == 'en' else '%d.%m.%Y')


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

    unknown = view_message('view.data.unknown_without_a_github_query')
    if upd:
        prog_update = update_text(upd)
    elif getattr(args, 'upstream', None):
        prog_update = view_message('view.data.current_2')
    else:
        prog_update = view_message('view.data.not_queried')
    full = ((gh or {}).get('repo') or {}).get('full_name') or ''
    if full and not args.repo_known:   # Rohdaten der GitHub-API nennen das Repository (#134)
        args.repo, args.repo_known = full, True
    values = {
        'LIBRARY_NAME': repo_label(args),
        'PROGRAM_VERSION_TEXT': view_message('view.data.ghostwriter_upstream_repository', p_a=prog.get("version") or "?", p_b=prog.get("upstream") or "?"),
        'PROGRAM_UPDATE_TEXT': prog_update, 'PROGRAM_BEHIND': upd['behind'] if upd else '',
        'PROGRAM_LAST_UPDATE_TEXT': view_message('view.data.last_update_run_on', p_a=de_datetime_plus(prog["last_update"])) if prog.get('last_update') else view_message('view.data.no_update_run_yet'),
        'PROGRAM_SKIPPED_TEXT': (view_message('view.data.workflow_files_skipped_ghostwriter_update_token_secret') + ', '.join(prog['skipped_workflows']))
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
        size_text = (f'{size / 1024:.1f} MB'.replace('.', '.' if UI.get('language') == 'en' else ',') if size and size >= 1024 else f'{size} KB') if size is not None else view_message('view.data.size_unknown')
        branches = gh.get('branches')
        visibility = {True: view_message('view.data.private'), False: view_message('view.data.public')}.get(repo.get('private'), view_message('view.data.visibility_unknown'))
        branch_text = plural(len(branches), view_message('view.data.branch'), view_message('view.data.branches')) if isinstance(branches, list) else view_message('view.data.branch_count_unknown')
        values['REPO_TEXT'] = f'{visibility} · {size_text} · {branch_text}'
    books = []
    for b in lib.get('books') or []:
        pr = next((p for p in pulls if (p.get('head') or {}).get('ref') == b.get('work_branch')), None)
        pending = b.get('pending') or 0
        pend_text = (view_message('view.data.pending', p_a=plural(pending, view_message('view.data.change'), view_message('view.data.changes'))) + (f' · {"Pull Request" if UI.get("language") == "en" else "Änderungspaket"} #{pr["number"]}' if pr else '')) if pending else view_message('view.data.no_pending_changes')
        ed = b.get('last_edition')
        v = last_run(RUN_NAMES['validate'], b['branch'])
        pr_run = last_run(RUN_NAMES['proof'], b['branch'])
        if gh is None or not isinstance(gh.get('runs'), list):
            check, check_text, proof_text = '', view_message('view.data.validation_unknown'), view_message('view.data.proof_unknown')
        else:
            check = {'success': 'ok', 'failure': 'fail'}.get((v or {}).get('conclusion'), '')
            check_text = (view_message('view.data.validation_on_last_push') + {'ok': view_message('view.data.passed'), 'fail': view_message('view.data.failed')}.get(check, (v or {}).get('status') or view_message('view.data.not_run_yet'))) if v else view_message('view.data.validation_no_runs_yet')
            if pr_run:
                proof_text = (view_message('view.data.proof_from_download_available_until', p_a=de_datetime_plus(pr_run.get("created_at")), p_b=de_datetime_plus(pr_run.get("created_at"), PROOF_DAYS)))
            else:
                proof_text = view_message('view.data.no_proof_yet')
        books.append({
            'B_TITLE': b.get('title') or b.get('title_short') or b['branch'], 'B_BRANCH': b['branch'],
            'B_COMMIT_TEXT': f'{de_date(b.get("updated_at"))} · {b.get("last_commit") or ""}'.strip(' ·'),
            'B_PENDING_TEXT': pend_text, 'B_PENDING': '1' if pending else '',
            'B_AUTOMERGE_TEXT': view_message('view.data.apply_changes_immediately') + (view_message('view.data.on') if b.get('auto_merge') else view_message('view.data.off')),
            'B_EDITION_TEXT': view_message('view.data.edition_of', p_a=ed["number"], p_b=de_date(ed["date"]), p_c=ed["tag"]) if ed else view_message('view.data.no_edition_yet'),
            'B_PROOF_TEXT': proof_text,
            'B_DATA_TEXT': view_message('view.data.data_version', p_a=b.get("data_version", "?")) + (view_message('view.data.migration_pending_included_in_the_next_update') if b.get('migration_pending') else view_message('view.data.current')),
            'B_MIGRATION': '1' if b.get('migration_pending') else '',
            'B_CHECK': check, 'B_CHECK_TEXT': check_text})
    secrets = lib.get('secrets')
    srows = []
    for n in lib.get('secret_names') or []:
        v = None if secrets is None else secrets.get(n)
        state = '' if v is None else ('yes' if v else 'no')
        srows.append({'S_NAME': n, 'S_STATE': state or 'unknown',
                      'S_TEXT': {'yes': view_message('view.data.stored'), 'no': view_message('view.data.missing'), 'unknown': view_message('view.data.unknown')}[state or 'unknown']})
    rrows = []
    seen = set()
    for r in runs:
        if r.get('name') in seen:
            continue
        seen.add(r.get('name'))
        c = r.get('conclusion') or r.get('status') or ''
        rrows.append({'R_NAME': r.get('name') or '', 'R_STATE': {'success': 'ok', 'failure': 'fail'}.get(c, 'other'),
                      'R_TEXT': f'{ {"success": view_message('view.data.successful'), "failure": view_message('view.data.failed'), "cancelled": view_message('view.data.cancelled'), "skipped": view_message('view.data.skipped'), "in_progress": view_message('view.data.in_progress'), "queued": view_message('view.data.queued'), "action_required": view_message('view.data.awaiting_approval')}.get(c, c)} · '
                                f'{de_datetime_plus(r.get("created_at"))} · {r.get("head_branch") or ""}',
                      'R_URL': r.get('html_url') or ''})
    lrows, lim_text = limit_rows(base, config, args, gh)
    values['LIMITS_TEXT'] = lim_text
    if args.text:
        out = [view_message('view.data.data'), f'{repo_label(args)}', '', view_message('view.data.program'), '',
               f'- {values["PROGRAM_VERSION_TEXT"]}', f'- Update: {values["PROGRAM_UPDATE_TEXT"]} · {values["PROGRAM_LAST_UPDATE_TEXT"]}',
               f'- {values["UI_TEXT"]}'] + ([f'- ⚠️ {values["PROGRAM_SKIPPED_TEXT"]}'] if values['PROGRAM_SKIPPED_TEXT'] else [])
        out += ['', view_message('view.data.books'), '', view_message('view.data.book_latest_state_changes_edition_proof_data'), '|---|---|---|---|---|---|---|']
        for r in books:
            out.append(f'| {r["B_TITLE"]} (`{r["B_BRANCH"]}`) | {r["B_COMMIT_TEXT"]} | {r["B_PENDING_TEXT"]}; {r["B_AUTOMERGE_TEXT"]} | '
                       f'{r["B_EDITION_TEXT"]} | {r["B_PROOF_TEXT"]} | {"⚠️ " if r["B_MIGRATION"] else ""}{r["B_DATA_TEXT"]} | '
                       f'{ {"ok": "✅ ", "fail": "❌ "}.get(r["B_CHECK"], "")}{r["B_CHECK_TEXT"]} |')
        out += ['', '**Repository**', '', f'- {values["REPO_TEXT"]}',
                view_message('view.data.completed_branches_clean_up_branches_deletion_tasks', p_a=values["CLEANUP_URL"], p_b=values["TASKS_URL"])]
        if srows:
            out += [view_message('view.data.secrets_names_only') + ', '.join(f'`{r["S_NAME"]}` { {"yes": "✅", "no": "❌", "unknown": "❔"}[r["S_STATE"]]} {r["S_TEXT"]}' for r in srows)]
        if lrows:
            out += ['', view_message('view.data.usage_limits'), '', view_message('view.data.limit_state'), '|---|---|']
            out += [f'| {r["L_LABEL"]} | { {"ok": "🟢", "warn": "🟡", "pause": "🔴"}[r["L_STATE"]]} {r["L_TEXT"]} |' for r in lrows]
            if lim_text:
                out += ['', f'> ⏸ {lim_text}']
        if rrows:
            out += ['', view_message('view.data.latest_runs'), '', view_message('view.data.action_result'), '|---|---|'] + [f'| [{r["R_NAME"]}]({r["R_URL"]}) | {r["R_TEXT"]} |' for r in rrows]
        out += ['', '---', menu([('Ü', view_message('view.data.library'))] + ([('U', view_message('view.data.install_update'))] if upd else []))]
        return '\n'.join(out) + '\n'
    blocks = {'BOOKS': books, 'SECRETS': srows, 'RUNS': rrows}
    if lrows:
        blocks['LIMITS'] = lrows
    return fill('daten.html', values, blocks)


def limit_rows(base, config, args, gh):
    """Nutzungsgrenzen für „Daten“ (#71, #62): aus --limits (limits.py check --json) bzw. aus den Kosten des Monats und,
    wenn github.json `rate_limit` (GET /rate_limit) enthält, dem API-Rate-Limit. → ([{L_LABEL, L_STATE, L_TEXT}], text)."""
    import limits
    if getattr(args, 'limits', None):
        data = json.loads(Path(args.limits).read_text(encoding='utf-8'))
        rows, state = data.get('limits') or [], data.get('state')
    else:
        live = {}
        core = (((gh or {}).get('rate_limit') or {}).get('resources') or {}).get('core') or {}
        if core.get('limit'):
            live['api_rate'] = (core['limit'] - core.get('remaining', 0), core['limit'])
        rows = limits.evaluate(base, config, live=live)
        state = limits.summary(rows)[0]
    labels = {'ai_budget': view_message('limit.ai_budget'), 'actions_minutes': view_message('limit.actions_minutes'),
              'api_rate': view_message('limit.api_rate')}
    out = []
    for row in rows:
        text = limit_row_text(row)
        label = labels.get(row.get('key'), row['label']) if UI.get('language') == 'en' else row['label']
        out.append({'L_LABEL': label, 'L_STATE': row['state'],
                    'L_TEXT': text[len(label) + 1:] if text.startswith(label + ' ') else text})
    paused = [r for r in rows if r['state'] == 'pause']
    text = (view_message('view.limit_rows.automatic_updates_paused') + '; '.join(limit_row_text(r) for r in paused)) if state == 'pause' and paused else ''
    return out, text


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
        raise SystemExit(view_message('view.choice_spec.unknown_choice_available', p_a=step, p_b=", ".join(lib["steps"])))
    spec = view_choice_labels(dict(lib['steps'][step], step=step), lib.get('steps_total', ''))
    num = step.split('.')[-1]
    for k in ('title', 'subtitle', 'note'):
        if spec.get(k):
            spec[k] = spec[k].replace('{step}', num).replace('{steps}', str(lib.get('steps_total', '')))
    return spec


def check_choice_spec(spec):
    qs = spec.get('questions') or []
    if not 1 <= len(qs) <= 4:
        raise SystemExit(view_message('view.check_choice_spec.choice_questions'))
    for q in qs:
        opts = q.get('options') or []
        if not 2 <= len(opts) <= 6:
            raise SystemExit(view_message('view.check_choice_spec.choice_answers', p_a=q.get("key")))
        if len(q.get('header', '')) > 12:
            raise SystemExit(view_message('view.check_choice_spec.choice_label_must_not_exceed_characters', p_a=q.get("key")))
        if sum(bool(o.get('recommended')) for o in opts) > 1:
            raise SystemExit(view_message('view.check_choice_spec.choice_at_most_one_recommendation', p_a=q.get("key")))


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
        out = [f'### {spec.get("title", view_message('view.choice.choice'))}']
        if spec.get('subtitle'):
            out += ['', spec['subtitle']]
        for i, q in enumerate(qs, 1):
            cur = config_value(config, q.get('field'))
            out += ['', f'**{i}. {q["text"]}**' + (view_message('view.choice.multiple_selections_allowed') if q.get('multi') else '')]
            for letter, o in zip(LETTERS, q['options']):
                tags = (view_message('view.choice.recommended') if o.get('recommended') else '') + (view_message('view.choice.current') if is_selected(cur, str(o['value'])) else '')
                out.append(f'- `{i}{letter}` {o["label"]}' + (f' – {o["desc"]}' if o.get('desc') else '') + tags)
        example = ', '.join(f'{i}{"a c" if q.get("multi") else "a"}' for i, q in enumerate(qs, 1))
        out += ['', view_message('view.choice.reply_with_the_codes_e_g_enter', p_a=example)
                + (view_message('view.choice.s_skips') if spec.get('skippable') else '')]
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
    return fill('auswahl.html', {'STEP': spec['step'], 'TITLE': spec.get('title', view_message('view.choice.choice')), 'SUBTITLE': spec.get('subtitle', ''),
                                 'NOTE': spec.get('note', ''), 'SKIPPABLE': '1' if spec.get('skippable') else ''},
                {'QUESTIONS': questions, 'OPTIONS': options})


FORMS = {'choice': choice_view, 'book-create': book_create_view, 'series-edit': series_edit_view, 'omnibus-edit': omnibus_edit_view,
         'character-suggest': character_suggest_view, 'analysis-suggest': analysis_suggest_view, 'import-preview': import_preview_view, 'import-outline': import_outline_view, 'project-edit': project_edit_view, 'chapter-research': chapter_research_view, 'project-settings': project_settings_view, 'chapter-create': chapter_create_view,
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


REPO_URL = re.compile(r'([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+?)(?:\.git)?/?$')
UNKNOWN_REPO = 'unbekanntes Repository'


def detect_repo(base):
    """owner/name des Buch-Repositorys ohne --repo (#134): GITHUB_REPOSITORY (Actions), sonst die
    Adresse von origin im Projektordner. Nie das Hauptrepository als Vorgabe; nichts gefunden = ''."""
    import os
    env = os.environ.get('GITHUB_REPOSITORY', '').strip()
    if REPO_URL.fullmatch(env):
        return env
    url = subprocess.run(['git', '-C', str(base), 'remote', 'get-url', 'origin'], capture_output=True, text=True).stdout.strip()
    m = REPO_URL.search(url.replace(':', '/')) if url and not Path(url).is_dir() else None
    return f'{m.group(1)}/{m.group(2)}' if m else ''


def repo_label(args):
    """Name des Repositorys für Überschriften (Bücherregal, Serie, Daten)."""
    return args.repo if getattr(args, 'repo_known', True) else view_message('repo.unknown')


def resolve_repo(base, args):
    """args.repo setzen: --repo, sonst ermittelt. Unbekannt: Anzeige „unbekanntes Repository“, Links auf
    das Hauptrepository aus dem Manifest (dort liegen dieselben Programmdateien und die Anleitung)."""
    repo = (args.repo or '').strip() or detect_repo(base)
    args.repo_known = bool(repo)
    if not repo:
        manifest = ROOT / 'ghostwriter-manifest.yml'
        up = (yaml.safe_load(manifest.read_text(encoding='utf-8')) or {}).get('upstream') or {} if manifest.is_file() else {}
        repo = up.get('repo') or 'ploeffler/GhostWriter'
    args.repo = repo


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('project')
    ap.add_argument('view', choices=['project', 'chapter', 'section', 'matter', 'characters', 'images', 'library', 'data', 'series'] + list(FORMS))
    ap.add_argument('where', nargs='?')
    ap.add_argument('--text', action='store_true')
    ap.add_argument('--language', help='Bediensprache de/en; Englisch für die migrierten Ansichten und Formulare')
    ap.add_argument('--repo', help='owner/name des Buch-Repositorys; ohne Angabe aus GITHUB_REPOSITORY bzw. git remote origin (#134)')
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
    resolve_repo(base, args)
    try:
        from .i18n import resolve_language
        from . import render_view_en, view_i18n
    except ImportError:
        from i18n import resolve_language
        import render_view_en, view_i18n
    default = subprocess.run(['git', '-C', str(base), 'symbolic-ref', '-q', '--short', 'refs/remotes/origin/HEAD'], capture_output=True, text=True).stdout.strip().removeprefix('origin/') or 'main'
    raw_profile = subprocess.run(['git', '-C', str(base), 'show', f'refs/remotes/origin/{default}:assistant.yml'], capture_output=True, text=True)
    try:
        profile = yaml.safe_load(raw_profile.stdout) or {} if raw_profile.returncode == 0 else {}
    except yaml.YAMLError:
        profile = {}
    language = resolve_language(args.language, config, profile)
    UI['language'] = language
    requested_text = args.text
    if language == 'en':
        if args.view not in (render_view_en.CLI_VIEWS | view_i18n.DIRECT_VIEWS) and (not args.ui_ref or args.text):
            raise SystemExit('English native text output is not yet available for this view. Use --language de, or preview the translated UI templates with --ui-ref <checked-ui-commit> without --text.')
        # Englisch bleibt standardmäßig nativ; grafische Testfassungen werden ausdrücklich mit --ui-ref gewählt.
        requested_text = requested_text or not args.ui_ref
        args.text = requested_text if args.view in view_i18n.DIRECT_VIEWS else False
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
    elif args.view == 'series':
        out = series_view(base, config, args)
    elif args.view == 'project':
        out = project_view(base, config, args)
    elif args.view == 'chapter':
        out = chapter_view(base, config, args, int(args.where))
    else:
        c, s = (int(x) for x in args.where.split('.'))
        out = section_view(base, config, args, c, s)
    if language == 'en' and args.view not in view_i18n.DIRECT_VIEWS:
        data = render_view_en.prepare(out.template, out.data, config, args)
        out = render_view_en.render(out.template, data, config, sys.modules[__name__], base) if requested_text else fill(out.template + '.html', data)
    sys.stdout.write(out)


if __name__ == '__main__':
    main()
