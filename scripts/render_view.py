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
        'PROJECT_COST': money(amount, est), 'PROJECT_COST_HINT': cost_hint('Bisherige Gesamtkosten', amount, est),
        'PROJECT_EDITION_TEXT': f'Auflage {edition}' if edition else 'noch keine Auflage',
    }
    changes = load_changes(args)
    if changes:
        values.update({'PENDING_COUNT': len(changes['commits']), 'PENDING_TEXT': changes_text(changes),
                       'PENDING_PR': changes['pull_request']})
    if args.text:
        lines = [f'### 📘 {values["PROJECT_TITLE"] or "Noch ohne Titel"}',
                 f'**{values["PROJECT_EDITION_TEXT"]}** · Autor: {values["PROJECT_AUTHOR"] or "noch offen"} · Kosten bisher: **{values["PROJECT_COST"]}**', '']
        if changes:
            lines += [f'> ⏳ **{values["PENDING_TEXT"]} noch nicht übernommen** (Pull Request #{changes["pull_request"]}) · `M` übernehmen', '']
        if values['PROJECT_DESCRIPTION_SHORT']:
            lines += [f'> {values["PROJECT_DESCRIPTION_SHORT"]}', '']
        if values['PROJECT_DESCRIPTION']:
            lines += [values['PROJECT_DESCRIPTION'], '']
        if rows:
            # Letzte Spalte: Kürzel zum Bearbeiten des Kapitels (wie der Bearbeiten-Knopf der Kapitelansicht).
            lines += ['| # | Kapitel | Kosten | Status | |', '|--:|---|--:|---|:-:|']
            lines += [f'| {r["CHAPTER_NUMBER"]} | {r["CHAPTER_TITLE"]} | {r["CHAPTER_COST"]} | {status_text(r["CHAPTER_STATUS"])} | `✎ B{r["CHAPTER_NUMBER"]}` |' for r in rows]
        else:
            lines += ['*Noch keine Kapitel.*']
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
        items += [('D', 'KI-Dienste'), ('P', 'Projektdaten bearbeiten'), ('N', 'Neues Kapitel'), ('R', 'Kapitelreihenfolge'),
                  ('A', 'Neue Auflage'), ('E', 'Einstellungen')]
        lines += [menu(items)]
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
              'APPROVED_COUNT_TEXT': f'{approved} von {n}',
              'CHAPTER_APPROVABLE': 'true' if ch['status'] == 'ready_for_approval' and n and approved == n else ''}
    if args.text:
        def marks(r):
            parts = [f'{MARKER_ICON[k]} {r["MARKERS_" + k.upper()]}' for k in MARKER_ICON if r['MARKERS_' + k.upper()]]
            return ' '.join(parts) or '–'
        lines = [f'### 📖 Kapitel {cnum} · {ch["title"]}']
        if values['CHAPTER_SUBTITLE']:
            lines += [f'*{values["CHAPTER_SUBTITLE"]}*']
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
        items += [('B', 'Kapitel bearbeiten'), ('N', 'Neuer Abschnitt'), ('R', 'Reihenfolge'), ('Ü', 'Übersicht')]
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
    if args.text:
        yn = lambda v: '✅ ja' if v else '— nein'
        lines = [f'### ✏️ {cnum}.{snum} · {s["title"]}',
                 f'Kapitel {cnum} · {status_text(head["status"])} · Kosten **{values["SECTION_COST"]}**', '',
                 '| | |', '|---|---|',
                 f'| Ziel | {goal or "*offen*"} |', f'| Kurzbeschreibung | {summary or "*offen*"} |',
                 f'| Faktencheck | {FC_TEXT.get(head["fact_check"], head["fact_check"])} |',
                 f'| Schreibfreigabe | {yn(head["approvals"]["writing"])} |', f'| Abschnitt freigegeben | {yn(head["approvals"]["section"])} |', '']
        if markers:
            lines += [f'**Offene Marker ({n})**'] + [f'- {MARKER_ICON[m["MARKER_TYPE"]]} {m["MARKER_LABEL"]}: {m["MARKER_TEXT"]}' for m in markers] + ['']
        else:
            lines += ['Keine offenen Marker.', '']
        lines += ['---', '', ms, '', '---']
        items = [('T', 'Text ändern (geänderten Text schicken)'), ('F', 'Ziel, Kurzbeschreibung, Faktencheck'),
                 ('FS', 'Schreibfreigabe zurücknehmen' if head['approvals']['writing'] else 'Schreiben freigeben'),
                 ('FA', 'Abschnittsfreigabe zurücknehmen' if head['approvals']['section'] else 'Abschnitt freigeben'),
                 ('RS', 'Recherche sofort'), ('GS', 'Ghostwriting sofort')]
        if prev_id:
            items.append((f'{cnum}.{snum - 1}', '← vorheriger'))
        if next_id:
            items.append((f'{cnum}.{snum + 1}', 'nächster →'))
        items.append(('K', 'Zum Kapitel'))
        lines += [menu(items)]
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
    warn = '' if chapters and approved == len(chapters) else \
        (f'Bisher {"ist" if approved == 1 else "sind"} {approved} von {len(chapters)} Kapiteln freigegeben; '
         'nur freigegebene Kapitel kommen in die Auflage.')
    values = {'EDITION_NUMBER': n, 'EDITION_NAME': br['name_pattern'].format(title_short=short, edition=n),
              'EDITION_TAG': br['tag_pattern'].format(title_short_slug=tag_slug(short), edition=n),
              'EDITION_DATE_DEFAULT': datetime.date.today().isoformat(), 'APPROVAL_WARNING_TEXT': warn}
    formats = [{'FORMAT_LABEL': a.upper()} for a in br['assets']]
    if args.text:
        return '\n'.join([f'### 📚 Neue Auflage erzeugen · Auflage {n}', '', '| | |', '|---|---|', f'| Name | {values["EDITION_NAME"]} |',
                           f'| Tag | `{values["EDITION_TAG"]}` |', f'| Formate | {", ".join(f["FORMAT_LABEL"] for f in formats)} |',
                           f'| Erscheinungsdatum | {values["EDITION_DATE_DEFAULT"]} *(Vorschlag)* |']
                          + (['', f'> ⚠️ {warn}'] if warn else [])
                          + ['', 'Schicke `Datum: JJJJ-MM-TT` und optional `Anmerkungen: …`. `OK` übernimmt den Vorschlag, `X` bricht ab.']) + '\n'
    return fill('auflage-erzeugen.html', values, {'FORMATS': formats})


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
    if kind == 'chapter':
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
                add('block', 'Der Abschnitt ist freigegeben; zuerst die Abschnittsfreigabe zurücknehmen.')
            effect = 'Die Schreibfreigabe wird zurückgenommen; das Manuskript bleibt, wie es ist, darf aber erst nach einer neuen Freigabe weiter geschrieben werden.'
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
    state = 'ok' if present.get(secret) else 'alt' if alt and present.get(alt) else ('missing' if secret in present else '')
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
    hint = ''
    if state.get('skipped_workflows'):
        hint = (f'{len(state["skipped_workflows"])} Workflow-Datei(en) wurden nicht aktualisiert; dafür braucht das '
                'Repository das Secret GHOSTWRITER_UPDATE_TOKEN (docs/UPDATES.md).')
    return auto, text, hint


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
                             '', f'<sub>{upd_text}</sub>'] + ([f'', f'> ⚠️ {upd_hint}'] if upd_hint else []) + ['', FORM_HINT]) + '\n'
    def b(v):
        return 'true' if v else 'false'
    return fill('projekteinstellungen.html', {'FACT_CHECK_DEFAULT': fc, 'PAGE_SIZE': ts['page_size'], 'FONT': ts['font'],
                                              'FONT_SIZE': str(ts['font_size']).rstrip('0').rstrip('.') if isinstance(ts['font_size'], float) else str(ts['font_size']),
                                              'TITLE_PAGE': b(ts['title_page']), 'IMPRINT': b(ts['imprint']), 'TOC': b(ts['toc']),
                                              'TOC_DEPTH': str(ts['toc_depth']), 'UPDATES_AUTO': b(upd_auto),
                                              'GW_VERSION_TEXT': upd_text, 'GW_UPDATE_HINT': upd_hint}, {'FIXED': fixed})


FORMS = {'project-edit': project_edit_view, 'project-settings': project_settings_view, 'chapter-create': chapter_create_view,
         'chapter-reorder': chapter_reorder_view, 'edition-create': edition_create_view, 'chapter-edit': chapter_edit_view,
         'section-create': section_create_view, 'section-reorder': section_reorder_view,
         'changes-merge': changes_merge_view, 'providers-edit': providers_edit_view,
         'approval-writing': lambda b, c, a: approval_view(b, c, a, 'writing'),
         'approval-section': lambda b, c, a: approval_view(b, c, a, 'section'),
         'approval-chapter': lambda b, c, a: approval_view(b, c, a, 'chapter')}


def git_head(base):
    try:
        return subprocess.run(['git', '-C', str(base), 'rev-parse', 'HEAD'], capture_output=True, text=True,
                              check=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return ''


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('project')
    ap.add_argument('view', choices=['project', 'chapter', 'section'] + list(FORMS))
    ap.add_argument('where', nargs='?')
    ap.add_argument('--text', action='store_true')
    ap.add_argument('--repo', default='ploeffler/GhostWriter')
    ap.add_argument('--branch', default='main')
    ap.add_argument('--revoke', action='store_true', help='bei approval-*: Freigabe zurücknehmen statt erteilen')
    ap.add_argument('--changes', help='JSON-Datei mit den offenen Änderungen (Pull Request, Branches, Commits) für Projektübersicht und changes-merge')
    ap.add_argument('--head-sha', help='Commit des gelesenen Stands (HEAD_SHA); ohne Angabe der HEAD des Projektordners, wenn er ein Git-Repository ist')
    ap.add_argument('--ui-ref', help='Commit oder Branch von ghostwriter-ui statt des festen Commits aus templates/ui/ghostwriter-ui.yml (nur zum Testen)')
    args = ap.parse_args()
    ui = yaml.safe_load(UI_CONFIG.read_text(encoding='utf-8'))
    UI['repo'], UI['ref'] = ui['repo'], args.ui_ref or ui['commit']
    base, config = load(args.project)
    UI['head'] = args.head_sha or git_head(base)
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
