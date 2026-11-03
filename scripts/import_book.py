#!/usr/bin/env python3
"""Manuskript als Buch importieren (#124), Teil ohne KI: umwandeln, Gliederung erkennen, Vorschau, anlegen.

Aufruf (im Buch-Branch eines neuen Buchs, noch ohne Kapitel):
  python scripts/import_book.py <buch> convert <datei> [--keep first_edition|30|90|forever]
  python scripts/import_book.py <buch> edit '<json-liste von änderungen>'
  python scripts/import_book.py <buch> apply [--writing-approval]
  python scripts/import_book.py <buch> status [--json]          Stand des Imports (Aufbewahrung des Originals)
  python scripts/import_book.py <buch> expire [--today JJJJ-MM-TT]  Original nach Ablauf entfernen

convert: Original unverändert nach import/original/<datei>; Umwandlung mit Pandoc
(DOCX, ODT, EPUB, HTML, Markdown, Text) bzw. pdftotext (PDF, mit Warnung) nach
import/manuscript.md; Bilder nach import/media/. Danach die Gliederung:
  - Überschriften: die oberste Ebene, die mindestens zweimal vorkommt, sind Kapitel,
    die nächste Abschnitte; eine einzelne Überschrift darüber gilt als Buchtitel.
  - Ohne Überschriften: Zeilen „Kapitel N …“ / „Chapter N …“.
  - Kapitel ohne Abschnittsüberschriften: Abschnitte an Szenentrennern (***, * * *, ⁂),
    sonst ein Abschnitt.
  - Widmung, Vorwort, Prolog, Epilog, Nachwort, Danksagung, Glossar (auch englisch)
    werden Teile von Vor- bzw. Nachspann (#57); kurzer Text vor der ersten
    Überschrift (bis 40 Wörter) als Widmung.
  - Wortzahl je Teil gegen die Umwandlung (verlustfrei), Hinweise zu Tabellen,
    Fußnoten, Bildern und sehr langen Abschnitten (> 4000 Wörter).
Ergebnis: import/proposal.json (Vorschlag) und import/import.yml (Quelle, Format,
Aufbewahrung). Am Buch ändert sich noch nichts.

edit: Änderungen am Vorschlag, je {op, …} (Nummern ab 1): rename_chapter
{chapter, title} · rename_section {chapter, section, title} · split_scenes
{chapter, section} · merge_sections {chapter, section} (mit dem folgenden) ·
merge_chapters {chapter} (mit dem folgenden) · split_chapter {chapter, section}
(neues Kapitel ab diesem Abschnitt) · to_matter {chapter, kind} · to_chapter {part}.

apply: legt Kapitel, Abschnitte und Teile an (Status revision; Schreibfreigabe nur
mit --writing-approval, Abschnitts- und Kapitelfreigaben nie), trägt Titel und
Autor ein, wenn sie fehlen, und setzt workflow.current_phase auf writing. Bilder
aus dem Dokument kommen nicht in den Text, sondern als Kandidaten in import.yml
(images, für #54). Der Text der Abschnitte ist der umgewandelte Text des Originals.

Aufbewahrung des Originals (import.yml keep): first_edition (bis zur ersten
Auflage), 30 bzw. 90 (Tage), forever. expire entfernt import/original/ nach
Ablauf (Action „Manuskript importieren“, täglich); die Projektübersicht weist
7 Tage vorher darauf hin.
"""
import argparse
import datetime
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'scripts'))
from render_view import MATTER, tag_slug  # noqa: E402

FORMATS = {'.docx': 'docx', '.odt': 'odt', '.epub': 'epub', '.html': 'html', '.htm': 'html', '.md': 'markdown',
           '.markdown': 'markdown', '.txt': 'text', '.pdf': 'pdf'}
MATTER_NAMES = {
    'dedication': ['widmung', 'dedication'], 'foreword': ['vorwort', 'geleitwort', 'foreword', 'preface'],
    'prologue': ['prolog', 'prologue'], 'epilogue': ['epilog', 'epilogue'], 'afterword': ['nachwort', 'afterword'],
    'acknowledgments': ['danksagung', 'dank', 'acknowledgments', 'acknowledgements'], 'glossary': ['glossar', 'glossary']}
SCENE = re.compile(r'(?m)^(?:[ \t]*(?:\*[ \t]*\*[ \t]*\*|\\\*[ \t]*\\\*[ \t]*\\\*|⁂|\*{3,}|#)|-{3,}|_{3,})[ \t]*$')
HEADING = re.compile(r'(?m)^(#{1,6})[ \t]+(.+?)[ \t]*#*[ \t]*(?:\{[^}]*\})?[ \t]*$')
CHAPTER_LINE = re.compile(r'(?im)^[ \t]*((?:kapitel|chapter)[ \t]+[\w.]+.*)$')
LONG_WORDS = 4000
KEEP = {'first_edition': 'bis zur ersten Auflage', '30': '30 Tage', '90': '90 Tage', 'forever': 'dauerhaft'}
PDF_WARNING = ('PDF: Absätze, Hervorhebungen, Fußnoten und Bilder können verloren gehen; Kopf- und Fußzeilen, '
               'Seitenzahlen und Silbentrennung wurden entfernt, so gut es ging. DOCX oder ODT ist zuverlässiger.')


def words(text):
    text = re.sub(r'!\[[^\]]*\]\([^)]*\)(\{[^}]*\})?', ' ', text or '')
    text = HEADING.sub(' ', text)
    return len(re.findall(r'[\wÄÖÜäöüß]+(?:[-’\'][\wÄÖÜäöüß]+)*', text))


def run(cmd, cwd=None):
    r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    if r.returncode:
        raise SystemExit(f'Umwandlung fehlgeschlagen ({" ".join(map(str, cmd[:2]))}): {r.stderr.strip()[-600:]}')
    return r.stdout


# ---------- Umwandeln ----------

def pdf_text(path):
    """pdftotext mit Aufräumen: Seitenzahlen, wiederkehrende Kopf-/Fußzeilen, Silbentrennung, harte Umbrüche."""
    raw = run(['pdftotext', '-enc', 'UTF-8', str(path), '-'])
    pages = [p.split('\n') for p in raw.split('\f')]
    edge = {}
    for p in pages:
        lines = [l.strip() for l in p if l.strip()]
        for l in lines[:2] + lines[-2:]:
            k = re.sub(r'\d+', '#', l)
            edge[k] = edge.get(k, 0) + 1
    repeated = {k for k, n in edge.items() if len(pages) > 3 and n >= max(3, len(pages) * 0.3)}
    out = []
    for p in pages:
        for l in p:
            s = l.strip()
            if re.fullmatch(r'[-–— ]*\d{1,4}[-–— ]*', s) or (s and re.sub(r'\d+', '#', s) in repeated):
                continue
            out.append(l.rstrip())
        out.append('')
    text = '\n'.join(out)
    text = re.sub(r'(\w)-\n[ \t]*([a-zäöüß])', r'\1\2', text)                  # Silbentrennung
    paras = [re.sub(r'\s*\n\s*', ' ', p).strip() for p in re.split(r'\n[ \t]*\n', text)]
    return '\n\n'.join(p for p in paras if p) + '\n'


def convert(base, src, keep='first_edition', today=None):
    base, src = Path(base), Path(src)
    fmt = FORMATS.get(src.suffix.lower())
    if not fmt:
        raise SystemExit(f'{src.name}: Format nicht unterstützt (DOCX, ODT, EPUB, HTML, Markdown, Text, PDF)')
    if keep not in KEEP:
        raise SystemExit(f'Aufbewahrung: {", ".join(KEEP)}')
    imp = base / 'import'
    (imp / 'original').mkdir(parents=True, exist_ok=True)
    orig = imp / 'original' / src.name
    if src.resolve() != orig.resolve():
        shutil.copyfile(src, orig)
    meta, warnings = {}, []
    if fmt == 'pdf':
        md = pdf_text(orig)
        warnings.append(PDF_WARNING)
    elif fmt == 'text':
        md = orig.read_text(encoding='utf-8', errors='replace')
    else:
        media = imp / 'media'
        md = run(['pandoc', '--from', {'markdown': 'markdown', 'html': 'html'}.get(fmt, fmt), '--to', 'markdown-smart',
                  '--wrap=none', '--standalone', f'--extract-media={media}', str(orig)])
        m = re.match(r'\A---\n(.*?)\n---\n', md, re.S)
        if m:
            meta = yaml.safe_load(m.group(1)) or {}
            md = md[m.end():]
    md = md.replace(str(imp / 'media') + '/', 'import/media/')
    (imp / 'manuscript.md').write_text(md, encoding='utf-8')
    title = meta.get('title') if isinstance(meta.get('title'), str) else ''
    author = meta.get('author')
    author = ', '.join(author) if isinstance(author, list) else (author or '')
    proposal = detect(md, title, str(author), fmt)
    proposal['warnings'] = warnings + proposal['warnings']
    save_proposal(base, proposal)
    today = today or datetime.date.today()
    info = {'source': f'import/original/{src.name}', 'format': fmt, 'imported_at': today.isoformat(), 'keep': keep,
            'words': proposal['stats']['words_original']}
    if keep in ('30', '90'):
        info['keep_until'] = (today + datetime.timedelta(days=int(keep))).isoformat()
    (imp / 'import.yml').write_text(yaml.safe_dump(info, allow_unicode=True, sort_keys=False), encoding='utf-8')
    return proposal


# ---------- Gliederung ----------

def matter_kind(title):
    t = re.sub(r'[^a-zäöüß ]', '', (title or '').casefold()).strip()
    for kind, names in MATTER_NAMES.items():
        if t in names:
            return kind
    return None


def scenes(text):
    return [p.strip('\n') for p in SCENE.split(text or '')]


def section_from(title, text):
    return {'title': title, 'text': text.strip('\n') + '\n', 'words': words(text), 'scenes': len(scenes(text))}


def detect(md, title='', author='', fmt=''):
    warnings = []
    heads = [(len(m.group(1)), m.group(2).strip(), m.start(), m.end()) for m in HEADING.finditer(md)]
    if not heads:   # Klartext: Zeilen „Kapitel N …“ als Überschriften
        lines = [(1, m.group(1).strip(), m.start(), m.end()) for m in CHAPTER_LINE.finditer(md)]
        if len(lines) >= 2:
            heads = lines
    levels = sorted({h[0] for h in heads})
    chap_level = next((lv for lv in levels if sum(1 for h in heads if h[0] == lv) >= 2), levels[0] if levels else None)
    if chap_level and levels and levels[0] < chap_level:
        tops = [h for h in heads if h[0] < chap_level]
        if len(tops) == 1 and not title:
            title = tops[0][1]
    sec_level = next((lv for lv in levels if chap_level and lv > chap_level), None)
    parts, chapters = [], []
    chap_heads = [h for h in heads if h[0] == chap_level] if chap_level else []
    if not chap_heads:
        warnings.append('Keine Gliederung erkannt: das Manuskript ist ein Kapitel. Kapitel lassen sich in der Vorschau teilen '
                        'oder mit KI vorschlagen.')
        chapters.append({'title': title or 'Kapitel 1', 'sections': [section_from(f'Abschnitt {i}', t) for i, t in
                                                                      enumerate(scenes(md), start=1) if t.strip()] or
                         [section_from('Abschnitt 1', md)]})
    else:
        pre = md[:chap_heads[0][2]]
        pre = HEADING.sub('', pre).strip()
        if pre:
            if words(pre) <= 40:
                parts.append({'kind': 'dedication', 'title': MATTER['dedication'][1], 'text': pre + '\n', 'words': words(pre)})
            else:
                chapters.append({'title': 'Einleitung', 'sections': [section_from('Einleitung', pre)]})
        for i, h in enumerate(chap_heads):
            end = chap_heads[i + 1][2] if i + 1 < len(chap_heads) else len(md)
            body = md[h[3]:end]
            kind = matter_kind(h[1])
            if kind and not any(p['kind'] == kind for p in parts):
                text = HEADING.sub(lambda m: m.group(0) if len(m.group(1)) > chap_level else '', body).strip()
                parts.append({'kind': kind, 'title': h[1], 'text': text + '\n', 'words': words(text),
                              'area': MATTER[kind][0], 'position': 'before' if not chapters else 'after'})
                continue
            ctitle = re.sub(r'(?i)^(kapitel|chapter)\s+\w+[.:]?\s*[-–:]?\s*', '', h[1]) or h[1]
            subs = [x for x in HEADING.finditer(body) if sec_level and len(x.group(1)) == sec_level]
            secs = []
            if subs:
                intro = body[:subs[0].start()].strip()
                if intro:
                    secs.append(section_from(ctitle, intro))
                for j, s in enumerate(subs):
                    e = subs[j + 1].start() if j + 1 < len(subs) else len(body)
                    secs.append(section_from(s.group(2).strip(), body[s.end():e]))
            else:
                sc = [t for t in scenes(body) if t.strip()]
                secs = [section_from(ctitle if len(sc) == 1 else f'{ctitle} ({k})', t) for k, t in enumerate(sc, start=1)] \
                    or [section_from(ctitle, body)]
            chapters.append({'title': ctitle, 'sections': secs})
    # Teile nach dem letzten Kapitel gehören in den Nachspann, auch wenn ihre Art eigentlich vorn steht
    for p in parts:
        p.setdefault('area', MATTER[p['kind']][0])
    tables = len(re.findall(r'(?m)^\|.*\|\s*$\n^\|[-:| ]+\|\s*$', md)) + len(re.findall(r'(?m)^\+[-=+:]+\+\s*\n(?!\|)', md)) // 2 \
        + len(re.findall(r'(?m)^[ \t]+-{3,}(?:[ \t]+-{3,})+[ \t]*$', md))
    notes = len(re.findall(r'(?m)^\[\^[^\]]+\]:', md))
    images = re.findall(r'!\[[^\]]*\]\(([^)\s]+)', md)
    if tables:
        warnings.append(f'{tables} Tabelle(n): als Markdown-Tabelle übernommen, bitte im Probedruck prüfen.')
    if notes:
        warnings.append(f'{notes} Fußnote(n): bleiben als Fußnoten im Text.')
    if images:
        warnings.append(f'{len(images)} Bild(er): nicht im Text, sondern als Kandidaten für Illustrationen (#54).')
    for ci, c in enumerate(chapters, start=1):
        for si, s in enumerate(c['sections'], start=1):
            if s['words'] > LONG_WORDS:
                warnings.append(f'Abschnitt {ci}.{si} ist sehr lang ({s["words"]} Wörter): teilen?'
                                + (f' ({s["scenes"]} Szenen)' if s['scenes'] > 1 else ''))
    p = {'title': title, 'author': author, 'format': fmt, 'parts': parts, 'chapters': chapters, 'warnings': warnings,
         'images': images}
    p['stats'] = stats(p, md)
    return p


def stats(p, md=None):
    total = sum(x['words'] for x in p['parts']) + sum(s['words'] for c in p['chapters'] for s in c['sections'])
    st = dict(p.get('stats') or {})
    if md is not None:
        st['words_original'] = words(md)
    st.update({'words_proposal': total, 'chapters': len(p['chapters']),
               'sections': sum(len(c['sections']) for c in p['chapters']), 'images': len(p.get('images') or [])})
    st['lossless'] = st['words_original'] == total
    return st


def proposal_path(base):
    return Path(base) / 'import' / 'proposal.json'


def load_proposal(base):
    p = proposal_path(base)
    if not p.is_file():
        raise SystemExit('Es gibt noch keinen Import-Vorschlag (zuerst convert)')
    return json.loads(p.read_text(encoding='utf-8'))


def save_proposal(base, p):
    p['stats'] = stats(p)
    proposal_path(base).parent.mkdir(parents=True, exist_ok=True)
    proposal_path(base).write_text(json.dumps(p, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')


# ---------- Änderungen am Vorschlag ----------

def edit(base, ops):
    p = load_proposal(base)
    ch = p['chapters']
    def c(i):
        if not 1 <= int(i) <= len(ch):
            raise SystemExit(f'Kapitel {i} gibt es im Vorschlag nicht')
        return ch[int(i) - 1]
    def s(i, j):
        secs = c(i)['sections']
        if not 1 <= int(j) <= len(secs):
            raise SystemExit(f'Abschnitt {i}.{j} gibt es im Vorschlag nicht')
        return secs, int(j) - 1
    for op in ops:
        kind = op.get('op')
        if kind == 'rename_chapter':
            c(op['chapter'])['title'] = op['title'].strip()
        elif kind == 'rename_section':
            secs, k = s(op['chapter'], op['section'])
            secs[k]['title'] = op['title'].strip()
        elif kind == 'split_scenes':
            secs, k = s(op['chapter'], op['section'])
            parts = [t for t in scenes(secs[k]['text']) if t.strip()]
            if len(parts) > 1:
                base_title = secs[k]['title']
                secs[k:k + 1] = [section_from(f'{base_title} ({n})', t) for n, t in enumerate(parts, start=1)]
        elif kind == 'merge_sections':
            secs, k = s(op['chapter'], op['section'])
            if k + 1 < len(secs):
                title = re.sub(r' \(\d+\)$', '', secs[k]['title'])
                secs[k:k + 2] = [section_from(title, secs[k]['text'].rstrip('\n') + '\n\n\\* \\* \\*\n\n' + secs[k + 1]['text'])]
        elif kind == 'merge_chapters':
            i = int(op['chapter'])
            if i < len(ch):
                c(i)['sections'] += ch[i]['sections']
                del ch[i]
        elif kind == 'split_chapter':
            secs, k = s(op['chapter'], op['section'])
            if k > 0:
                i = int(op['chapter'])
                ch.insert(i, {'title': op.get('title') or secs[k]['title'], 'sections': secs[k:]})
                del secs[k:]
        elif kind == 'to_matter':
            if op['kind'] not in MATTER or any(x['kind'] == op['kind'] for x in p['parts']):
                raise SystemExit(f'{op["kind"]}: unbekannt oder schon vorhanden')
            i = int(op['chapter'])
            cc = c(i)
            text = '\n\n'.join(x['text'].strip('\n') for x in cc['sections']) + '\n'
            p['parts'].append({'kind': op['kind'], 'title': MATTER[op['kind']][1], 'text': text, 'words': words(text),
                               'area': MATTER[op['kind']][0]})
            del ch[i - 1]
        elif kind == 'to_chapter':
            k = int(op['part']) - 1
            if not 0 <= k < len(p['parts']):
                raise SystemExit(f'Teil {op["part"]} gibt es im Vorschlag nicht')
            part = p['parts'].pop(k)
            sec = section_from(part['title'], part['text'])
            ch.insert(0 if part.get('area') == 'front' else len(ch), {'title': part['title'], 'sections': [sec]})
        else:
            raise SystemExit(f'Unbekannte Änderung: {kind}')
    save_proposal(base, p)
    return p


# ---------- Anlegen ----------

def q(text):
    return yaml.safe_dump(text, allow_unicode=True, default_style='"', width=10**6).splitlines()[0]


def approval_entries(base, ids, by='chat', commit=None):
    """Schreibfreigabe beim Import im Freigabe-Protokoll festhalten (approvals.yml, START.md „Freigaben“)."""
    commit = commit or (subprocess.run(['git', 'rev-parse', 'HEAD'], cwd=base, capture_output=True, text=True).stdout.strip())
    if not re.fullmatch(r'[0-9a-f]{7,40}', commit or ''):
        raise SystemExit('Schreibfreigabe beim Import braucht den bestätigten Stand (Commit); ohne Git --commit angeben')
    p = Path(base) / 'approvals.yml'
    data = (yaml.safe_load(p.read_text(encoding='utf-8')) or {}) if p.is_file() else {}
    at = datetime.datetime.now().astimezone().isoformat(timespec='seconds')
    data['entries'] = (data.get('entries') or []) + [
        {'kind': 'writing', 'id': i, 'action': 'granted', 'at': at, 'by': by, 'commit': commit,
         'note': 'beim Import erteilt (alle importierten Abschnitte und Teile)'} for i in ids]
    p.write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False, width=10**6), encoding='utf-8')


def apply(base, writing_approval=False, by='chat', commit=None):
    base = Path(base)
    import library
    import matter as matter_mod
    p = load_proposal(base)
    cfg_path = base / 'ghostwriter.yml'
    text = cfg_path.read_text(encoding='utf-8')
    cfg = yaml.safe_load(text)
    if (cfg.get('structure') or {}).get('chapters'):
        raise SystemExit('Das Buch hat schon Kapitel; ein Import ist nur in ein neues Buch möglich')
    if not p['chapters']:
        raise SystemExit('Der Vorschlag hat kein Kapitel')
    status = 'revision'
    sec_tpl = (ROOT / 'templates' / 'section.md').read_text(encoding='utf-8')
    entries = []
    for ci, c in enumerate(p['chapters'], start=1):
        cslug = tag_slug(c['title'])[:40].strip('-') or f'kapitel-{ci}'
        cpath = f'chapters/{ci:02d}-{cslug}'
        entry = {'id': f'ch-{ci:02d}-{cslug}', 'title': c['title'], 'path': cpath, 'status': 'in_progress', 'sections': []}
        rows = []
        for si, s in enumerate(c['sections'], start=1):
            sslug = tag_slug(s['title'])[:40].strip('-') or f'abschnitt-{si}'
            sid = f'sec-{ci:02d}-{si:02d}-{sslug}'
            spath = f'{cpath}/sections/{si:02d}-{sslug}.md'
            body = re.sub(r'!\[[^\]]*\]\([^)]*\)(\{[^}]*\})?\n?', '', s['text']).strip()
            doc = (sec_tpl.replace('<STABILE-ID>', sid).replace('"<KAPITEL>.<ABSCHNITT>"', f'"{ci}.{si}"')
                   .replace('"<TITEL>"', q(s['title'])).replace('status: planned', f'status: {status}')
                   .replace('  writing: false', f'  writing: {"true" if writing_approval else "false"}')
                   .replace('# <NUMMER> <TITEL>', f'# {ci}.{si} {s["title"]}')
                   .replace('<Was soll dieser Abschnitt leisten?>', 'Offen.').replace('<Inhaltliche Zusammenfassung.>', 'Offen.')
                   .replace('## Manuskript\n\nNoch nicht begonnen.', f'## Manuskript\n\n{body or "Noch nicht begonnen."}'))
            (base / spath).parent.mkdir(parents=True, exist_ok=True)
            (base / spath).write_text(doc, encoding='utf-8')
            entry['sections'].append({'id': sid, 'title': s['title'], 'path': spath})
            rows.append(f'| {ci}.{si} | {s["title"]} | `{status}` |')
        readme = [f'# Kapitel {ci} – {c["title"]}', '', '## Kurzbeschreibung', '', 'Offen.', '', '## Ziel des Kapitels', '',
                  'Offen.', '', '## Abschnitte', '', '| Nummer | Abschnitt | Status |', '|---|---|---|'] + rows + \
                 ['', '## Kapitelstatus', '', '`in_progress`', '', '## Kapitelzusammenführung', '', 'Noch nicht begonnen.', '']
        (base / cpath / 'README.md').write_text('\n'.join(readme), encoding='utf-8')
        entries.append(entry)
    block = yaml.safe_dump({'chapters': entries}, allow_unicode=True, sort_keys=False, width=10**6)
    block = ''.join('  ' + l + '\n' for l in block.splitlines())
    if not re.search(r'(?m)^  chapters: \[\]\s*$', text):
        raise SystemExit('ghostwriter.yml: structure.chapters: [] nicht gefunden; bitte von Hand eintragen')
    text = re.sub(r'(?m)^  chapters: \[\]\s*\n', lambda m: block, text, count=1)
    proj = cfg.get('project') or {}
    fields = {}
    if p.get('title') and not (proj.get('title') or proj.get('working_title')):
        fields['working_title'] = p['title']
    if p.get('author') and not proj.get('author'):
        fields['author'] = p['author']
    if fields:
        text = library.set_project_fields(text, fields)
    text = re.sub(r'(?m)^(  current_phase: )"?wizard"?', r'\1"writing"', text, count=1)
    cfg_path.write_text(text, encoding='utf-8')
    if (yaml.safe_load(text)['structure']['chapters'] or []) != entries:
        raise SystemExit('ghostwriter.yml ließ sich nicht sicher ändern')
    for part in p['parts']:   # Vor- und Nachspann über matter.py (Reihenfolge, Vorlage)
        item = matter_mod.add(base, part['kind'], part['title'] if part['title'] != MATTER[part['kind']][1] else None)
        mp = base / item['path']
        t = mp.read_text(encoding='utf-8')
        t = re.sub(r'(?m)^status: planned', f'status: {status}', t, count=1)
        t = t.replace('  writing: false', f'  writing: {"true" if writing_approval else "false"}', 1)
        body = re.sub(r'!\[[^\]]*\]\([^)]*\)(\{[^}]*\})?\n?', '', part['text']).strip()
        if part['kind'] == 'glossary':
            body = '\n'.join(re.sub(r'^\s*[-*]?\s*\**([^:*]+?)\**\s*[:–-]\s+', r'- \1: ', l) if l.strip() else l
                             for l in body.splitlines())
        head, _, _ = t.partition('\n## Manuskript\n')
        mp.write_text(head + '\n## Manuskript\n\n' + (body or 'Noch nicht begonnen.') + '\n', encoding='utf-8')
    if writing_approval:
        _, cfg2 = __import__('render_view').load(base)
        ids = [s['id'] for e in entries for s in e['sections']] + \
              [i['id'] for a in ('front_matter', 'back_matter') for i in (cfg2['structure'].get(a) or [])]
        approval_entries(base, ids, by, commit)
    info_p = base / 'import' / 'import.yml'
    info = yaml.safe_load(info_p.read_text(encoding='utf-8')) or {} if info_p.is_file() else {}
    info.update({'applied_at': datetime.date.today().isoformat(), 'chapters': len(entries),
                 'sections': sum(len(e['sections']) for e in entries), 'matter': [x['kind'] for x in p['parts']],
                 'writing_approval': bool(writing_approval), 'images': p.get('images') or []})
    info_p.write_text(yaml.safe_dump(info, allow_unicode=True, sort_keys=False), encoding='utf-8')
    return info


# ---------- Aufbewahrung des Originals ----------

def status(base, today=None):
    """{source, keep, keep_text, expires (Datum|None), due (bool), soon (≤ 7 Tage), removed} oder None."""
    p = Path(base) / 'import' / 'import.yml'
    if not p.is_file():
        return None
    info = yaml.safe_load(p.read_text(encoding='utf-8')) or {}
    today = today or datetime.date.today()
    out = {'source': info.get('source'), 'keep': info.get('keep'), 'keep_text': KEEP.get(str(info.get('keep')), ''),
           'removed': bool(info.get('removed_at')), 'expires': None, 'due': False, 'soon': False}
    if out['removed'] or not (Path(base) / str(info.get('source', ''))).is_file():
        out['removed'] = True
        return out
    if info.get('keep_until'):
        exp = datetime.date.fromisoformat(str(info['keep_until']))
        out.update({'expires': exp.isoformat(), 'due': today >= exp, 'soon': 0 <= (exp - today).days <= 7})
    elif info.get('keep') == 'first_edition':
        cfg = yaml.safe_load((Path(base) / 'ghostwriter.yml').read_text(encoding='utf-8')) or {}
        out['due'] = bool((cfg.get('project') or {}).get('current_edition'))
    return out


def expire(base, today=None):
    st = status(base, today)
    if not st or st['removed'] or not st['due']:
        return False
    base = Path(base)
    shutil.rmtree(base / 'import' / 'original', ignore_errors=True)
    p = base / 'import' / 'import.yml'
    info = yaml.safe_load(p.read_text(encoding='utf-8')) or {}
    info['removed_at'] = (today or datetime.date.today()).isoformat()
    p.write_text(yaml.safe_dump(info, allow_unicode=True, sort_keys=False), encoding='utf-8')
    return True


def main(argv):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('project')
    ap.add_argument('cmd', choices=['convert', 'edit', 'apply', 'status', 'expire'])
    ap.add_argument('args', nargs='*')
    ap.add_argument('--keep', default='first_edition', choices=list(KEEP))
    ap.add_argument('--writing-approval', action='store_true')
    ap.add_argument('--by', default='chat', help='bei apply --writing-approval: GitHub-Login (sonst chat)')
    ap.add_argument('--commit', help='bei apply --writing-approval: bestätigter Stand (sonst HEAD)')
    ap.add_argument('--today')
    ap.add_argument('--json', action='store_true')
    a = ap.parse_args(argv[1:])
    base = Path(a.project)
    today = datetime.date.fromisoformat(a.today) if a.today else None
    if a.cmd == 'convert':
        if not a.args:
            ap.error('convert braucht die Datei')
        p = convert(base, a.args[0], a.keep, today)
        st = p['stats']
        print(f'✓ Vorschlag: {st["chapters"]} Kapitel, {st["sections"]} Abschnitte, {len(p["parts"])} Teile von Vor- und '
              f'Nachspann · {st["words_proposal"]} von {st["words_original"]} Wörtern'
              + (' (vollständig)' if st['lossless'] else ' ⚠️ Abweichung'))
        for w in p['warnings']:
            print(f'ⓘ {w}')
        return 0
    if a.cmd == 'edit':
        if not a.args:
            ap.error('edit braucht die Änderungen als JSON')
        p = edit(base, json.loads(a.args[0]))
        print(f'✓ Vorschlag geändert: {p["stats"]["chapters"]} Kapitel, {p["stats"]["sections"]} Abschnitte')
        return 0
    if a.cmd == 'apply':
        info = apply(base, a.writing_approval, a.by, a.commit)
        print(f'✓ Importiert: {info["chapters"]} Kapitel, {info["sections"]} Abschnitte'
              + (f', {", ".join(MATTER[k][1] for k in info["matter"])}' if info['matter'] else '')
              + (' · Schreibfreigabe erteilt' if info['writing_approval'] else ''))
        print('Commit-Nachricht: Manuskript importiert')
        return 0
    if a.cmd == 'status':
        st = status(base, today)
        print(json.dumps(st, ensure_ascii=False) if a.json else (st and json.dumps(st, ensure_ascii=False)) or 'kein Import')
        return 0
    print('✓ Original entfernt (Aufbewahrung abgelaufen)' if expire(base, today) else 'nichts zu entfernen')
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
