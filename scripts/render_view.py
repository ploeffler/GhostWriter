#!/usr/bin/env python3
"""Referenzumsetzung der Befüllungsregeln aus templates/ui/BEFUELLUNG.md.

Aufruf:
  python scripts/render_view.py <projektordner> project            [--text] [--repo owner/name] [--branch main]
  python scripts/render_view.py <projektordner> chapter <kapitel>  [--text] ...
  python scripts/render_view.py <projektordner> section <kapitel>.<abschnitt> [--text] ...

Ohne --text wird die befüllte HTML-Vorlage ausgegeben, mit --text die Textfassung
für Chats ohne Widgets. Gezeigt wird höchstens der Text eines Abschnitts.
"""
import argparse
import html
import json
import re
import sys
import unicodedata
from decimal import Decimal
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
TEMPLATES = ROOT / 'templates' / 'ui'
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

WIDGET = {'on': False, 'ref': 'main'}
UI_URL = 'https://cdn.jsdelivr.net/gh/ploeffler/ghostwriter-ui@{ref}/dist/gw.js'


def widget(template, values, blocks):
    data = dict(values)
    data.update(blocks or {})
    payload = json.dumps(data, ensure_ascii=False, separators=(',', ':')).replace('</', '<\\/')
    return (f'<div id="gw"></div>\n<script src="{UI_URL.format(ref=WIDGET["ref"])}"></script>\n'
            f'<script>GW.render({json.dumps(template[:-5])},{payload})</script>\n')


def fill(template, values, blocks=None):
    if WIDGET['on']:
        return widget(template, values, blocks)
    text = re.sub(r'\A<!--.*?-->\n', '', (TEMPLATES / template).read_text(encoding='utf-8'), flags=re.S)
    for name, rows in (blocks or {}).items():
        m = re.search(r'\{\{#' + name + r'\}\}\n?(.*?)[ \t]*\{\{/' + name + r'\}\}\n?', text, re.S)
        rendered = ''.join(fill_text(m.group(1), r) for r in rows)
        text = text[:m.start()] + rendered + text[m.end():]
    return fill_text(text, values)


def fill_text(text, values):
    def sub(m):
        key = m.group(1)
        if key not in values:
            return m.group(0)
        return html.escape(str(values[key]), quote=True)
    out = re.sub(r'\{\{([A-Z_]+)\}\}', sub, text)
    # Vorlagen-Kommentar entfernen, damit nur die Ansicht ausgegeben wird
    return re.sub(r'\A<!--.*?-->\n', '', out, flags=re.S)


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
    out = fill('projektuebersicht.html', values, {'CHAPTERS': rows})
    if not rows and not WIDGET['on']:
        # Bereich „Kapitel“ entfällt, solange es keine Kapitel gibt
        out = re.sub(r'\n\s*<div style="border-top:0.5px solid var\(--border\);padding-top:var\(--pad-md\)">\n\s*<div style="font-size:12px;color:var\(--text-muted\);margin-bottom:8px">Kapitel</div>.*?</div>\n\s*</div>', '', out, count=1, flags=re.S)
    return out


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
    if not markers and not WIDGET['on']:
        # Bereich „Offene Marker“ entfällt, wenn es keine gibt
        tpl = (TEMPLATES / 'abschnitt-bearbeiten.html').read_text(encoding='utf-8')
        tpl = re.sub(r'\n\s*<div style="border-top:0.5px solid var\(--border\);padding-top:var\(--pad-md\)">\n\s*<div class="gw-lbl">Offene Marker</div>.*?\{\{/MARKERS\}\}\n\s*</div>\n\s*</div>', '', tpl, flags=re.S)
        return fill_text(tpl, values)
    return fill('abschnitt-bearbeiten.html', values, {'MARKERS': markers})


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('project')
    ap.add_argument('view', choices=['project', 'chapter', 'section'])
    ap.add_argument('where', nargs='?')
    ap.add_argument('--text', action='store_true')
    ap.add_argument('--repo', default='ploeffler/GhostWriter')
    ap.add_argument('--branch', default='main')
    ap.add_argument('--widget', action='store_true', help='Daten plus Ladezeile für ghostwriter-ui statt fertigem HTML')
    ap.add_argument('--ui-ref', default='main', help='Commit oder Branch von ghostwriter-ui für jsDelivr')
    args = ap.parse_args()
    WIDGET['on'], WIDGET['ref'] = args.widget, args.ui_ref
    base, config = load(args.project)
    if args.view == 'project':
        out = project_view(base, config, args)
    elif args.view == 'chapter':
        out = chapter_view(base, config, args, int(args.where))
    else:
        c, s = (int(x) for x in args.where.split('.'))
        out = section_view(base, config, args, c, s)
    sys.stdout.write(out)


if __name__ == '__main__':
    main()
