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


def cost_entries(base, path):
    if not path.is_file():
        return []
    return yaml.safe_load(path.read_text(encoding='utf-8')).get('entries', [])


def section_costs(base, chapter, section):
    return cost_entries(base, base / chapter['path'] / 'costs' / f'{section["id"]}.yml')


def total(entries):
    """(Summe als Decimal oder None, enthält Schätzung)"""
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
        return 'Noch keine Kosten erfasst'
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

UI_URL = 'https://cdn.jsdelivr.net/gh/{repo}@{ref}/dist/gw.js'
UI = {'repo': 'ploeffler/ghostwriter-ui', 'ref': None}


def fill(template, values, blocks=None):
    """Widget-Code: Ladezeile für ghostwriter-ui und GW.render mit den Daten.
    Maskieren, Wiederholblöcke und data-gw-if erledigt gw.js im Chat."""
    data = dict(values)
    data.update(blocks or {})
    payload = json.dumps(data, ensure_ascii=False, separators=(',', ':')).replace('</', '<\\/')
    url = UI_URL.format(repo=UI['repo'], ref=UI['ref'])
    return (f'<div id="gw"></div>\n<script src="{url}"></script>\n'
            f'<script>GW.render({json.dumps(template[:-5])},{payload})</script>\n')


# ---------- Ansichten ----------

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
                     'CHAPTER_URL': f'https://github.com/{args.repo}/blob/{args.branch}/{ch["path"]}/README.md'})
    parts.append(total(cost_entries(base, base / 'costs' / 'project.yml')))
    amount, est = combine(parts)
    edition = p['current_edition']
    values = {
        'PROJECT_TITLE': p['title'] or p['working_title'], 'PROJECT_TITLE_SHORT': p['title_short'] or p['title'] or p['working_title'],
        'PROJECT_AUTHOR': p['author'], 'PROJECT_DESCRIPTION_SHORT': p['description_short'], 'PROJECT_DESCRIPTION': p['description'],
        'PROJECT_COST': money(amount, est), 'PROJECT_COST_HINT': cost_hint('Bisherige Gesamtkosten', amount, est),
        'PROJECT_EDITION_TEXT': f'Auflage {edition}' if edition else 'noch keine Auflage',
    }
    if args.text:
        lines = [f'**{values["PROJECT_TITLE"] or "Noch ohne Titel"}** · Buchprojekt · {values["PROJECT_EDITION_TEXT"]}',
                 f'Autor: {values["PROJECT_AUTHOR"] or "noch offen"} · Bisherige Kosten: {values["PROJECT_COST"]}', '']
        if values['PROJECT_DESCRIPTION_SHORT']:
            lines += [f'> {values["PROJECT_DESCRIPTION_SHORT"]}', '']
        if values['PROJECT_DESCRIPTION']:
            lines += [values['PROJECT_DESCRIPTION'], '']
        if rows:
            lines += ['| Nr. | Kapitel | Kosten | Status |', '|---|---|---|---|']
            lines += [f'| {r["CHAPTER_NUMBER"]} | [{r["CHAPTER_TITLE"]}]({r["CHAPTER_URL"]}) | {r["CHAPTER_COST"]} | {r["CHAPTER_STATUS"]} |' for r in rows]
        else:
            lines += ['Noch keine Kapitel.']
        lines += ['', 'Aktionen: 1 Projektdaten bearbeiten · 2 Neues Kapitel anlegen · 3 Kapitelreihenfolge ändern · 4 Neue Auflage erzeugen · 5 Projekteinstellungen']
        return '\n'.join(lines) + '\n'
    return fill('projektuebersicht.html', values, {'CHAPTERS': rows})


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
    values = {'PROJECT_TITLE_SHORT': p['title_short'] or p['title'], 'CHAPTER_ID': ch['id'], 'CHAPTER_NUMBER': cnum,
              'CHAPTER_TITLE': ch['title'], 'CHAPTER_SUBTITLE': sub.group(1) if sub else '',
              'SECTION_COUNT_TEXT': f'{n} Abschnitt' + ('' if n == 1 else 'e'),
              'MARKER_COUNT_TEXT': 'keine offenen Marker' if not counts_total else f'{counts_total} offene{"r" if counts_total == 1 else ""} Marker',
              'CHAPTER_COST': money(amount, est), 'CHAPTER_COST_HINT': cost_hint('Summe der Abschnittskosten', amount, est),
              'APPROVED_COUNT_TEXT': f'{approved} von {n}'}
    if args.text:
        lines = [f'**Kapitel {cnum}: {ch["title"]}**' + (f' – *{values["CHAPTER_SUBTITLE"]}*' if values['CHAPTER_SUBTITLE'] else ''),
                 f'{values["SECTION_COUNT_TEXT"]} · {values["MARKER_COUNT_TEXT"]} · Kosten: {values["CHAPTER_COST"]} · freigegeben: {values["APPROVED_COUNT_TEXT"]}', '',
                 '| Nr. | Abschnitt | Marker (A/Q/M/R) | Kosten | Status |', '|---|---|---|---|---|']
        lines += [f'| {r["SECTION_NUMBER"]} | {r["SECTION_TITLE"]} | {r["MARKERS_ANEKDOTE"]}/{r["MARKERS_QUELLE"]}/{r["MARKERS_MEDIZIN"]}/{r["MARKERS_RECHT"]} | {r["SECTION_COST"]} | {r["SECTION_STATUS"]} |' for r in rows]
        lines += ['', 'Aktionen: Nummer eines Abschnitts zum Bearbeiten · Kapitel bearbeiten · Neuer Abschnitt · Reihenfolge ändern · Zur Übersicht']
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
    if args.text:
        lines = [f'**{cnum}.{snum} {s["title"]}** · Kapitel {cnum} · Status {head["status"]} · Kosten: {values["SECTION_COST"]}',
                 f'Faktencheck: {head["fact_check"]} · Schreibfreigabe: {"ja" if head["approvals"]["writing"] else "nein"} · Abschnitt freigegeben: {"ja" if head["approvals"]["section"] else "nein"}', '',
                 f'Ziel: {goal or "offen"}', f'Kurzbeschreibung: {summary or "offen"}', '', f'Offene Marker ({n}):']
        lines += [f'- {m["MARKER_LABEL"]}: {m["MARKER_TEXT"]}' for m in markers] or ['- keine']
        lines += ['', '---', '', ms, '', '---', '',
                  'Aktionen: Recherche sofort · Ghostwriting sofort · Speichern (geänderten Text schicken) · Vorheriger/Nächster Abschnitt · Zum Kapitel']
        return '\n'.join(lines) + '\n'
    return fill('abschnitt-bearbeiten.html', values, {'MARKERS': markers})


def project_values(config):
    p = config['project']
    title = p['title'] or p['working_title'] or ''
    return {'PROJECT_TITLE': title, 'PROJECT_TITLE_SHORT': p['title_short'] or '', 'PROJECT_AUTHOR': p['author'] or '',
            'PROJECT_DESCRIPTION_SHORT': p['description_short'] or '', 'PROJECT_DESCRIPTION': p['description'] or ''}


def project_edit_view(base, config, args):
    values = project_values(config)
    if args.text:
        return '\n'.join(['**Projektdaten bearbeiten** – schicke die geänderten Felder als Antwort:', '',
                          f'- Titel: {values["PROJECT_TITLE"] or "(leer)"}', f'- Kurztitel: {values["PROJECT_TITLE_SHORT"] or "(leer)"}',
                          f'- Autor: {values["PROJECT_AUTHOR"] or "(leer)"}', f'- Kurzbeschreibung: {values["PROJECT_DESCRIPTION_SHORT"] or "(leer)"}',
                          f'- Beschreibung: {values["PROJECT_DESCRIPTION"] or "(leer)"}']) + '\n'
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
        return '\n'.join(['**Neues Kapitel anlegen** – schicke Titel, Kurzbeschreibung, Ziel und Position:', '',
                          'Positionen:'] + [f'{i}. {l}' + (' (Vorauswahl)' if r['POSITION_SELECTED'] else '') for i, (l, r) in enumerate(zip(labels, rows))]) + '\n'
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
    warn = '' if chapters and approved == len(chapters) else \
        f'Bisher sind {approved} von {len(chapters)} Kapiteln freigegeben; nur diese kommen in die Auflage.'
    values = {'EDITION_NUMBER': n, 'EDITION_NAME': br['name_pattern'].format(title_short=short, edition=n),
              'EDITION_TAG': br['tag_pattern'].format(title_short_slug=tag_slug(short), edition=n),
              'EDITION_DATE_DEFAULT': datetime.date.today().isoformat(), 'APPROVAL_WARNING_TEXT': warn}
    formats = [{'FORMAT_LABEL': a.upper()} for a in br['assets']]
    if args.text:
        return '\n'.join([f'**Neue Auflage erzeugen** – Auflage {n}', '', f'- Name: {values["EDITION_NAME"]}', f'- Tag: {values["EDITION_TAG"]}',
                          f'- Formate: {", ".join(f["FORMAT_LABEL"] for f in formats)}', f'- Erscheinungsdatum: {values["EDITION_DATE_DEFAULT"]} (Vorschlag)']
                         + ([f'', f'Hinweis: {warn}'] if warn else []) + ['', 'Schicke Erscheinungsdatum und Anmerkungen, oder „abbrechen“.']) + '\n'
    return fill('auflage-erzeugen.html', values, {'FORMATS': formats})


TYPESETTING_DEFAULT = {'page_size': 'a5', 'font': 'serif', 'font_size': 11, 'title_page': True,
                      'imprint': True, 'toc': True, 'toc_depth': 1}
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
        return '\n'.join([f'**Kapitel {n} bearbeiten** – schicke die geänderten Felder als Antwort:', '',
                          f'- Titel: {ch["title"]}', f'- Untertitel: {subtitle or "(leer)"}',
                          f'- Kurzbeschreibung: {summary or "(leer)"}', f'- Ziel: {goal or "(leer)"}']) + '\n'
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
        return '\n'.join([f'**Neuer Abschnitt in Kapitel {n}** – schicke Titel, Ziel, Kurzbeschreibung und Position:', '',
                          f'Faktencheck: {FC_TEXT[fc]} (Vorgabe)', '', 'Positionen:']
                         + [f'{i}. {l}' + (' (Vorauswahl)' if i == len(labels) - 1 else '') for i, l in enumerate(labels)]) + '\n'
    return fill('abschnitt-anlegen.html', {'CHAPTER_ID': ch['id'], 'CHAPTER_NUMBER': n, 'CHAPTER_TITLE': ch['title'],
                                           'FACT_CHECK_DEFAULT': fc}, {'POSITIONS': positions(labels)})


def reorder(args, kind, heading, items, chapter_id='', chapter_no=''):
    if args.text:
        return '\n'.join([f'**{heading}** – schicke die Nummern in der neuen Reihenfolge, z. B. „3, 1, 2, …“:', '']
                         + [f'{i["ITEM_NUMBER"]}. {i["ITEM_TITLE"]}' for i in items]) + '\n'
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
    if args.text:
        return '\n'.join(['**Projekteinstellungen**', '', 'Feste Regeln (nur im Chat mit ausdrücklicher Bestätigung änderbar):']
                         + [f'- {f["FIXED_LABEL"]}: {f["FIXED_VALUE"]}' for f in fixed]
                         + ['', f'Faktencheck für neue Abschnitte: {FC_TEXT[fc]}', '',
                            'Buchsatz:', f'- Seitenformat: {ts["page_size"]}', f'- Schrift: {ts["font"]}, {ts["font_size"]} pt',
                            f'- Titelseite: {"ja" if ts["title_page"] else "nein"}, Impressum: {"ja" if ts["imprint"] else "nein"}',
                            f'- Inhaltsverzeichnis: ' + (('nur Kapitel' if ts['toc_depth'] == 1 else 'Kapitel und Abschnitte') if ts['toc'] else 'nein'),
                            '', 'Schicke die gewünschten Änderungen als Antwort.']) + '\n'
    def b(v):
        return 'true' if v else 'false'
    return fill('projekteinstellungen.html', {'FACT_CHECK_DEFAULT': fc, 'PAGE_SIZE': ts['page_size'], 'FONT': ts['font'],
                                              'FONT_SIZE': str(ts['font_size']).rstrip('0').rstrip('.') if isinstance(ts['font_size'], float) else str(ts['font_size']),
                                              'TITLE_PAGE': b(ts['title_page']), 'IMPRINT': b(ts['imprint']), 'TOC': b(ts['toc']),
                                              'TOC_DEPTH': str(ts['toc_depth'])}, {'FIXED': fixed})


FORMS = {'project-edit': project_edit_view, 'project-settings': project_settings_view, 'chapter-create': chapter_create_view,
         'chapter-reorder': chapter_reorder_view, 'edition-create': edition_create_view, 'chapter-edit': chapter_edit_view,
         'section-create': section_create_view, 'section-reorder': section_reorder_view}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('project')
    ap.add_argument('view', choices=['project', 'chapter', 'section'] + list(FORMS))
    ap.add_argument('where', nargs='?')
    ap.add_argument('--text', action='store_true')
    ap.add_argument('--repo', default='ploeffler/GhostWriter')
    ap.add_argument('--branch', default='main')
    ap.add_argument('--ui-ref', help='Commit oder Branch von ghostwriter-ui statt des festen Commits aus templates/ui/ghostwriter-ui.yml (nur zum Testen)')
    args = ap.parse_args()
    ui = yaml.safe_load(UI_CONFIG.read_text(encoding='utf-8'))
    UI['repo'], UI['ref'] = ui['repo'], args.ui_ref or ui['commit']
    base, config = load(args.project)
    if args.view in FORMS:
        out = FORMS[args.view](base, config, args)
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
