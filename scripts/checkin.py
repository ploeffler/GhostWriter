#!/usr/bin/env python3
"""Rückgabe zu einem Checkout einchecken (#573, Teil 2 zu #209).

  python3 scripts/checkin.py <buch> <datei>… [--checkout GW-XXXX] [--date JJJJ-MM-TT] [--repo owner/name]
  python3 scripts/checkin.py <buch> aufbau <ordner> [--apply a-001,a-002 --confirm]
  python3 scripts/checkin.py <buch> note <ordner> --seite N --text "…" [--abschnitt 3.2] [--alt … --neu …] [--frage …] [--unleserlich]

Nimmt die Arbeitskopie des Gegenlesers zurück: DOCX (auch mit Kommentaren und Änderungsnachverfolgung), PDF (auch mit
PDF-Kommentaren) oder Scan/Handyfoto ausgedruckter Seiten. Die Kennung kommt aus der Dokumenteigenschaft
`ghostwriter_checkout` (DOCX) bzw. dem QR-Code (PDF, Bilder). Dann:

1. Original unverändert ablegen: `checkouts/<id>/rueckgabe-<datum>[-n]/original.<endung>` (mehrere Rückgaben je Checkout).
2. Scans aufbereiten (`seite-NN.jpg`, wie `material.py`), jede Seite über ihren QR-Code einem Kapitel zuordnen;
   ohne Code `unbekannt`, nie raten.
3. DOCX: Text je Abschnitt über die Textmarken `gw_<abschnitt>` mit dem Ausgangsstand (Commit des Checkouts) und dem
   heutigen Stand vergleichen (Dreifachvergleich). Geänderte Stellen werden **Befunde** in
   `editorial/rueckgabe-<id>-<datum>.yml` (Schema `findings`): eindeutig mit `alt`/`neu`; hat sich die Stelle seither
   geändert, mit `frage` und allen Fassungen, nie blind. Kommentare werden Befunde mit `frage`. Änderungsnachverfolgung
   wird nie still angenommen: Sie ist Teil des Vergleichs und wird als Befund zur Entscheidung vorgelegt.
3a. Aufbau-Änderungen (#209): neue, gelöschte, verschobene und umbenannte Abschnitte werden nicht als Befunde, sondern eigens in
   `rueckgabe.yml` (`aufbau`) aufgeführt; `aufbau <ordner> --apply … --confirm` übernimmt ausgewählte nach ausdrücklicher
   Bestätigung und bei beendetem Checkout (über `scripts/sections.py`).
4. `rueckgabe.yml` im Ablageordner: erkannte Seiten und Zuordnung, Zahl der Anmerkungen, `unbekannt`, offene Fragen.
   Handschrift abschreiben und Korrekturzeichen deuten macht der Assistent nach START.md (nie raten) und trägt die
   Befunde in die Befunddatei ein; ab dort gilt die Kette `hinweise.py collect` → Stufen (#570) → `plan`/`apply`.

Der Checkout wird nie automatisch beendet. Nichts wird übernommen oder freigegeben; Manuskriptseiten gehen nie an
externe Texterkennungsdienste.
"""
import argparse
import datetime
import difflib
import json
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
import checkout as co  # noqa: E402

W = 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'
IMAGES = ('.jpg', '.jpeg', '.png', '.tif', '.tiff', '.bmp', '.webp')
PAYLOAD = re.compile(r'^GW1\|([^|]+)\|([^|]*)\|(GW-[A-HJ-NP-Z2-9]{4})(?:\|([^|]+))?$')
SENTENCE = re.compile(r'[^.!?…\n]+(?:[.!?…]+[»«“”"\')\]]*|\n|$)')
SMART = str.maketrans({'„': '"', '“': '"', '”': '"', '»': '"', '«': '"', '‚': "'", '‘': "'", '’': "'", '–': '-', '—': '-', '…': '...'})


def q(tag):
    return f'{{{W}}}{tag}'


# ---------- Erkennen ----------

def parse_payload(text):
    m = PAYLOAD.match((text or '').strip())
    return {'repo': m.group(1), 'branch': m.group(2), 'id': m.group(3), 'chapter': m.group(4)} if m else None


def decode_qr(img):
    """QR-Code in einem Bild (OpenCV-Array) lesen: ganzes Bild, dann Fußzeile links, dann vergrößert. Gibt Nutzdaten oder None."""
    import cv2
    det = cv2.QRCodeDetector()
    h, w = img.shape[:2]
    tries = [img, img[int(h * 0.82):, :int(w * 0.45)], img[int(h * 0.7):, :], img[:int(h * 0.45), :]]
    for part in tries:
        for factor in (1.0, 2.0):
            view = cv2.resize(part, None, fx=factor, fy=factor, interpolation=cv2.INTER_CUBIC) if factor != 1.0 else part
            try:
                value = det.detectAndDecode(view)[0]
            except cv2.error:
                continue
            if parse_payload(value):
                return value
    return None


def kind_of(path):
    s = Path(path).suffix.lower()
    if s == '.docx':
        return 'docx'
    if s == '.pdf':
        return 'pdf'
    if s in IMAGES:
        return 'scan'
    raise ValueError(f'Dateityp {s or "?"} wird nicht eingecheckt (DOCX, PDF oder Bild)')


def docx_properties(path):
    with zipfile.ZipFile(path) as z:
        if 'docProps/custom.xml' not in z.namelist():
            return {}
        from lxml import etree
        root = etree.fromstring(z.read('docProps/custom.xml'))
    return {e.get('name'): ''.join(e.itertext()) for e in root}


def docx_application(path):
    """Programm, das die DOCX zuletzt geschrieben hat (docProps/app.xml): Word, LibreOffice Writer, Google Docs, Pages
    oder `unbekannt` (#209). Nur für Hinweise; der Vergleich hängt nicht davon ab."""
    try:
        with zipfile.ZipFile(path) as z:
            xml = z.read('docProps/app.xml').decode('utf-8', 'replace') if 'docProps/app.xml' in z.namelist() else ''
    except (OSError, zipfile.BadZipFile):
        return 'unbekannt'
    m = re.search(r'<Application>([^<]*)</Application>', xml)
    app = (m.group(1) if m else '').lower()
    for key, name in (('microsoft', 'Word'), ('libreoffice', 'LibreOffice Writer'), ('google', 'Google Docs'), ('pages', 'Pages')):
        if key in app:
            return name
    return 'unbekannt'


def docx_id_fallback(path):
    """Kennung, wenn die Dokumenteigenschaft fehlt (Google Docs und Pages verwerfen sie oft): (Kennung, Quelle) oder (None, '').
    Erst der Text des Titelblatts („Kennung: GW-XXXX“), dann ein QR-Code unter den Bildern der Datei."""
    try:
        from docx import Document
        doc = Document(str(path))
        for p in doc.paragraphs[:40]:
            m = re.search(r'Kennung:\s*(GW-[A-HJ-NP-Z2-9]{4})', p.text)
            if m:
                return m.group(1), 'titelblatt'
    except Exception:   # noqa: BLE001 – beschädigte Datei: weiter mit dem Bild-Versuch
        pass
    try:
        import cv2
        import numpy as np
        with zipfile.ZipFile(path) as z:
            for name in z.namelist():
                if name.startswith('word/media/') and name.lower().endswith(('.png', '.jpg', '.jpeg')):
                    img = cv2.imdecode(np.frombuffer(z.read(name), np.uint8), cv2.IMREAD_COLOR)
                    payload = parse_payload(decode_qr(img) or '') if img is not None else None
                    if payload:
                        return payload['id'], 'qr'
    except Exception:   # noqa: BLE001
        pass
    return None, ''


def docx_losses(path):
    """Inhalte, die der Vergleich nicht übernimmt (#209): Fußnoten, Tabellen, Bilder und Gestaltung. Gibt Zeilen für den
    Bericht; verglichen wird nur der Text, reine Gestaltungsänderungen (fett, kursiv, Schrift, Abstände) bleiben unberücksichtigt."""
    out = []
    try:
        with zipfile.ZipFile(path) as z:
            names = z.namelist()
            doc = z.read('word/document.xml').decode('utf-8', 'replace')
            notes = z.read('word/footnotes.xml').decode('utf-8', 'replace') if 'word/footnotes.xml' in names else ''
    except (OSError, zipfile.BadZipFile, KeyError):
        return out
    footnotes = len([m for m in re.findall(r'<w:footnote\b([^>]*)>', notes) if 'w:type="separator"' not in m and 'continuationSeparator' not in m])
    tables = doc.count('<w:tbl>')
    images = max(0, doc.count('<w:drawing>') - 1)       # das Titelblatt trägt den QR-Code
    if footnotes:
        out.append(f'{footnotes} Fußnoten: nur der Text im Abschnitt wird verglichen, Änderungen an Fußnoten werden nicht übernommen')
    if tables:
        out.append(f'{tables} Tabellen: nur der Text der Zellen wird verglichen, Tabellenaufbau und -format werden nicht übernommen')
    if images:
        out.append(f'{images} Bilder: Bilder werden nicht verglichen oder übernommen')
    return out


def _fingerprint(config):
    """Gliederung (Kapitel und Abschnitte mit Titel) als Prüfsumme: ändert sie sich, passen offene Aufbau-Änderungen nicht mehr."""
    import hashlib
    text = json.dumps([[c['id'], [[x['id'], x['title']] for x in c['sections']]] for c in config['structure']['chapters']], ensure_ascii=False)
    return hashlib.sha256(text.encode('utf-8')).hexdigest()[:16]


def file_digest(path):
    import hashlib
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


# ---------- Text ----------

def norm(text):
    t = re.sub(r'\[([^\]]*)\]\{[^}]*\}', r'\1', text or '')
    t = re.sub(r'!?\[([^\]]*)\]\([^)]*\)', r'\1', t)
    t = t.replace('\\', '').translate(SMART)
    t = re.sub(r'[*_`]+', '', t)
    return re.sub(r'\s+', ' ', t).strip()


def has_markup(text):
    return bool(re.search(r'[*_`\[\]{}\\]', text))


def paragraphs(text):
    return [p.strip() for p in re.split(r'\n\s*\n', text or '') if p.strip()]


def manuscript_of(text):
    return text.split('\n## Manuskript\n', 1)[1].strip() if '\n## Manuskript\n' in text else ''


def baseline(base, commit, rel):
    r = subprocess.run(['git', '-C', str(base), 'show', f'{commit}:{rel}'], capture_output=True, text=True)
    return manuscript_of(r.stdout) if r.returncode == 0 else None


def read_docx(path, scope=None):
    """{Abschnitts-ID: [Absatz, …]}, Kommentare [(Abschnitt, Autor, Text, Ankertext)], Zähler der Änderungsnachverfolgung,
    Dokumenteigenschaften und die Abschnitte in Dokumentreihenfolge (#209).

    Ein Abschnitt wird über die Textmarke `gw_…` erkannt; fehlt sie (Google Docs, Pages), über die Überschrift „N.M Titel“ aus
    `scope` ({Nummer: (ID, Titel)} des Checkouts): Nummer und Titel gleich = sicher, nur der Titel gleich = verschoben
    (`bestaetigt` nein), nur die Nummer gleich = vermutlich umbenannt. Eine Überschrift ohne Treffer ist ein neuer Abschnitt
    (`sid` None). Reihenfolge-Eintrag: {sid, nummer, titel, absaetze, erkannt, kapitel}."""
    from docx import Document
    props = docx_properties(path)
    mapping = json.loads(props.get('ghostwriter_sections') or '{}')
    by_title = {norm(t).casefold(): (n, sid) for n, (sid, t) in (scope or {}).items()}
    doc = Document(str(path))
    comments = {}
    for rel in doc.part.rels.values():
        if rel.reltype.endswith('/comments'):
            from lxml import etree
            root = etree.fromstring(rel.target_part.blob)
            for c in root.iter(q('comment')):
                comments[c.get(q('id'))] = (c.get(q('author')) or '', ' '.join(''.join(t.itertext()) for t in c.iter(q('p'))).strip())
    out, found, order, current, chapter = {}, [], [], None, None
    body = doc.element.body
    for p in body.iter(q('p')):
        names = [b.get(q('name')) for b in p.iter(q('bookmarkStart'))]
        style = p.find(f'{q("pPr")}/{q("pStyle")}')
        style_val = (style.get(q('val')) if style is not None else '') or ''
        text = ''.join(t.text or '' for t in p.iter(q('t'))).strip()
        level = re.match(r'(?i)(?:heading|berschrift)(\d)$', style_val)
        head = re.match(r'^(\d+)\.(\d+)\s+(.+)$', text)
        sec = next((mapping[n] for n in names if n in mapping), None)
        how = 'textmarke' if sec else None
        if not sec and level and int(level.group(1)) == 2 and text and (head or norm(text).casefold() not in NOT_SECTIONS):
            if head:
                number, title = f'{head.group(1)}.{head.group(2)}', head.group(3).strip()
                hit = (scope or {}).get(number)
                if hit and norm(hit[1]).casefold() == norm(title).casefold():
                    sec, how = hit[0], 'ueberschrift'
                elif norm(title).casefold() in by_title:
                    sec, how = by_title[norm(title).casefold()][1], 'titel'
                elif hit:
                    sec, how = hit[0], 'nummer'
            if not sec:
                sec, how = 'neu:' + (text[:60] or str(len(order) + 1)), 'neu'
        if sec:                                     # Abschnittsüberschrift
            current = sec
            out.setdefault(current, [])
            number = (head.group(1) + '.' + head.group(2)) if head else ''
            title = head.group(3).strip() if head else text
            order.append({'sid': None if how == 'neu' else sec, 'schluessel': sec, 'nummer': number, 'titel': title,
                          'erkannt': how, 'kapitel': chapter, 'absaetze': out[current]})
            continue
        if level and int(level.group(1)) == 1:
            m = re.match(r'^(\d+)\b', text)
            chapter = int(m.group(1)) if m else chapter
        if style_val.lower() in ('title', 'subtitle') or (level and int(level.group(1)) <= 2):
            current = None                          # Kapitelüberschrift, Untertitel, „Quellen“ u. Ä.: gehört zu keinem Abschnitt
            continue
        for cs in p.iter(q('commentRangeStart')):
            cid = cs.get(q('id'))
            if cid in comments and current:
                found.append((current, comments[cid][0], comments[cid][1], text[:120]))
        if current and text:
            out[current].append(text)
    ins = len(list(body.iter(q('ins'))))
    dele = len(list(body.iter(q('del'))))
    return out, found, {'eingefuegt': ins, 'geloescht': dele}, props, order


NOT_SECTIONS = ('quellen', 'literatur', 'quellenverzeichnis', 'anmerkungen', 'fußnoten')   # Überschriften 2. Ebene ohne Abschnitt
STATUS_NOTE = re.compile(r'^Stand: .*nicht abgeschlossen$')


def plain_paragraphs(md):
    """Absätze eines Manuskripttexts so, wie sie nach Pandoc in einer DOCX stehen: gleiche Pipeline wie beim Bau der Datei
    zum Gegenlesen, damit Listen, Tabellen, Anführungszeichen und Markup auf beiden Seiten gleich aussehen."""
    from docx import Document
    with tempfile.TemporaryDirectory() as tmp:
        src, out = Path(tmp) / 'a.md', Path(tmp) / 'a.docx'
        src.write_text(md or '', encoding='utf-8')
        r = subprocess.run(['pandoc', '--from', 'markdown+smart', '-o', str(out), str(src)], capture_output=True, text=True)
        if r.returncode:
            raise ValueError('pandoc: ' + r.stderr.strip()[:200])
        return [''.join(t.text or '' for t in p.iter(q('t'))).strip()
                for p in Document(str(out)).element.body.iter(q('p')) if ''.join(p.itertext()).strip()]


def tokens(text):
    return text.split()


def sentence_pairs(a_par, g_par):
    """Satzweise Gegenüberstellung eines Absatzes: [(alt_roh, neu)] nur geänderte Sätze mit gleicher Zahl auf beiden Seiten."""
    sa = [m.group().strip() for m in SENTENCE.finditer(a_par) if m.group().strip()]
    sg = [m.group().strip() for m in SENTENCE.finditer(g_par) if m.group().strip()]
    sm = difflib.SequenceMatcher(None, [norm(s) for s in sa], [norm(s) for s in sg], autojunk=False)
    pairs = []
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == 'equal':
            continue
        pairs.append((' '.join(sa[i1:i2]), ' '.join(sg[j1:j2])))
    return pairs


def minimal_change(alt_sentence, neu_sentence, unique_in):
    """Kleinste eindeutige Stelle (alt, neu) zwischen zwei Sätzen: Wortvergleich, bei Bedarf mit Nachbarwörtern, bis `alt`
    im Text `unique_in` genau einmal vorkommt. Gibt (alt, neu) oder None, wenn die Änderung nicht eindeutig fassbar ist."""
    ta, tg = tokens(alt_sentence), tokens(neu_sentence)
    sm = difflib.SequenceMatcher(None, [norm(t) for t in ta], [norm(t) for t in tg], autojunk=False)
    ops = [o for o in sm.get_opcodes() if o[0] != 'equal']
    if len(ops) != 1:
        return None
    _, i1, i2, j1, j2 = ops[0]
    for pad in range(0, 5):
        a1, a2 = max(0, i1 - pad), min(len(ta), i2 + pad)
        g1, g2 = max(0, j1 - pad), min(len(tg), j2 + pad)
        alt = ' '.join(ta[a1:a2])
        neu = ' '.join(ta[a1:i1] + tg[j1:j2] + ta[i2:a2])    # Nachbarwörter in der Schreibweise des Manuskripts
        if alt and unique_in.count(alt) == 1:
            return alt, neu
    return None


def compare_section(sid, ours, theirs, today):
    """Befunde (ohne ID und Quelle) für einen Abschnitt: Ausgangsstand `ours` (Manuskripttext), Fassung des Gegenlesers
    `theirs` (Absätze aus der DOCX), heutiger Stand `today` (Text). Beide Seiten gehen durch dieselbe Pandoc-Pipeline."""
    a_par = plain_paragraphs(ours)
    theirs = [p for p in theirs if not STATUS_NOTE.match(p) and p != '(noch kein Text)']
    sm = difflib.SequenceMatcher(None, [norm(p) for p in a_par], [norm(p) for p in theirs], autojunk=False)
    out = []

    def changed_since(alt):
        return today is not None and alt and alt not in today

    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == 'equal':
            continue
        if tag == 'replace' and (i2 - i1) == (j2 - j1):
            for a, g in zip(a_par[i1:i2], theirs[j1:j2]):
                for alt_s, neu_s in sentence_pairs(a, g):
                    hit = minimal_change(alt_s, neu_s, ours) if alt_s and neu_s else None
                    if hit and not changed_since(hit[0]):
                        alt, neu = hit
                        short = len(tokens(alt)) <= 6 and not re.search(r'\d', alt + neu)
                        out.append({'art': 'sprache' if short else 'aufbau', 'alt': alt, 'neu': neu,
                                    'befund': 'Änderung des Gegenlesers', 'frage': 'Änderung des Gegenlesers übernehmen?'})
                    else:
                        out.append({'art': 'kontinuitaet', 'befund': 'Änderung des Gegenlesers, Stelle nicht eindeutig oder seit dem Checkout geändert',
                                    'frage': _three(alt_s, neu_s, today)})
            continue
        old, new = ' '.join(a_par[i1:i2]), ' '.join(theirs[j1:j2])
        kind = 'Absatz gestrichen' if not new else 'Absatz eingefügt' if not old else 'Absätze geändert'
        out.append({'art': 'aufbau', 'befund': f'{kind} (Gegenleser)', 'frage': _three(old, new, today)})
    return out


def _three(old, new, today):
    cut = lambda s: (s[:300] + '…') if len(s) > 300 else s   # noqa: E731
    text = f'Ausgangsstand: „{cut(old)}“ · Gegenleser: „{cut(new)}“'
    if old and today is not None and old not in today:
        text += ' · Die Stelle hat sich seit dem Checkout geändert; heutiger Stand prüfen.'
    return text + ' Welche Fassung gilt?'


# ---------- Aufbau (#209) ----------

def baseline_structure(base, commit):
    """[(Abschnitts-ID, Titel, Kapitelnummer)] der Gliederung beim Checkout (`ghostwriter.yml` im Ausgangscommit) oder None."""
    r = subprocess.run(['git', '-C', str(base), 'show', f'{commit}:ghostwriter.yml'], capture_output=True, text=True)
    if r.returncode:
        return None
    try:
        data = yaml.safe_load(r.stdout) or {}
        return [(sec['id'], sec['title'], ci) for ci, ch in enumerate(data['structure']['chapters'], start=1) for sec in ch['sections']]
    except (yaml.YAMLError, KeyError, TypeError):
        return None


def _lis(values):
    """Indizes einer längsten aufsteigenden Teilfolge (Abschnitte, die ihre Reihenfolge behalten)."""
    best, prev = [], []
    for i, v in enumerate(values):
        best.append(1)
        prev.append(-1)
        for j in range(i):
            if values[j] < v and best[j] + 1 > best[i]:
                best[i], prev[i] = best[j] + 1, j
    if not values:
        return set()
    i = max(range(len(values)), key=lambda k: best[k])
    keep = set()
    while i >= 0:
        keep.add(i)
        i = prev[i]
    return keep


def detect_aufbau(scope_ids, base_struct, structure):
    """Aufbau-Änderungen der Rückgabe (#209): neue, gelöschte, verschobene und umbenannte Abschnitte.

    `scope_ids` = Abschnitte des Checkouts, `base_struct` = Gliederung beim Checkout, `structure` = Abschnitte der DOCX in
    Dokumentreihenfolge (`read_docx`). Ein Abschnitt, der im Dokument fehlt, gilt nur dann als gelöscht, wenn das Dokument
    sonst Abschnitte des Checkouts enthält (eine leere oder nicht erkannte Datei löscht nichts). Jeder Eintrag ist ein
    Vorschlag; übernommen wird er nur nach eigener Bestätigung."""
    out = []
    if base_struct is None:
        return out
    base = {sid: (title, ch) for sid, title, ch in base_struct if sid in scope_ids}
    base_order = [sid for sid, _, _ in base_struct if sid in base]
    recognized = [e for e in structure if e['sid'] in base]
    prev_sid = None
    for e in structure:
        if e['sid'] is None:
            out.append({'art': 'neu', 'titel': e['titel'], 'kapitel': e['kapitel'], 'hinter': prev_sid,
                        'absaetze': len(e['absaetze']), 'text': list(e['absaetze'])})
        prev_sid = e['sid'] or prev_sid
    if recognized:
        seen = {e['sid'] for e in recognized}
        for sid in base_order:
            if sid not in seen:
                out.append({'art': 'geloescht', 'abschnitt': sid, 'titel': base[sid][0], 'kapitel': base[sid][1]})
        order = [base_order.index(e['sid']) for e in recognized]
        keep = _lis(order)
        for k, e in enumerate(recognized):
            moved_chapter = e['kapitel'] and e['kapitel'] != base[e['sid']][1]
            if k not in keep or moved_chapter:
                before = next((r['sid'] for r in reversed(recognized[:k]) if r['kapitel'] == e['kapitel']), None)
                out.append({'art': 'verschoben', 'abschnitt': e['sid'], 'titel': base[e['sid']][0], 'kapitel': e['kapitel'] or base[e['sid']][1],
                            'von_kapitel': base[e['sid']][1], 'hinter': before})
        for e in recognized:
            if e['nummer'] and norm(e['titel']).casefold() != norm(base[e['sid']][0]).casefold():
                out.append({'art': 'umbenannt', 'abschnitt': e['sid'], 'alt': base[e['sid']][0], 'neu': e['titel']})
    for i, item in enumerate(out, start=1):
        item['id'] = f'a-{i:03d}'
        item['status'] = 'offen'
    return out


def aufbau_text(item, numbers):
    """Eine Zeile je Aufbau-Änderung für Bericht und Chat; `numbers` = {Abschnitts-ID: „N.M“}."""
    n = numbers.get(item.get('abschnitt'), '')
    art = item['art']
    if art == 'neu':
        after = f' nach {numbers.get(item["hinter"], "?")}' if item.get('hinter') else ' am Anfang'
        return f'neuer Abschnitt „{item["titel"]}“ in Kapitel {item["kapitel"] or "?"}{after} ({item["absaetze"]} Absätze)'
    if art == 'geloescht':
        return f'Abschnitt {n} „{item["titel"]}“ fehlt in der Rückgabe (gelöscht?)'
    if art == 'verschoben':
        after = f'nach {numbers.get(item["hinter"], "?")}' if item.get('hinter') else 'an den Anfang'
        return f'Abschnitt {n} „{item["titel"]}“ verschoben: in Kapitel {item["kapitel"]} {after}'
    return f'Abschnitt {n} umbenannt: „{item["alt"]}“ → „{item["neu"]}“'


# ---------- Ablage ----------

def folder_for(base, cid, date):
    root = Path(base) / 'checkouts' / cid
    n, name = 1, f'rueckgabe-{date}'
    while (root / name).exists():
        n += 1
        name = f'rueckgabe-{date}-{n}'
    return root / name


def write_findings(base, cid, date, folder, items):
    base = Path(base)
    ed = base / 'editorial'
    ed.mkdir(exist_ok=True)
    n, name = 1, f'rueckgabe-{cid}-{date}'
    while (ed / f'{name}.yml').exists():
        n += 1
        name = f'rueckgabe-{cid}-{date}-{n}'
    findings = []
    for i, it in enumerate(items, start=1):
        f = {'id': f'b-{i:03d}', 'abschnitt': it['abschnitt'], 'art': it['art'], 'befund': it['befund'], 'status': 'offen',
             'schweregrad': 'mittel', 'quelle': it.get('quelle', ''), 'gegenleser': it.get('gegenleser', '')}
        for key in ('alt', 'neu', 'frage'):
            if it.get(key):
                f[key] = it[key]
        findings.append({k: v for k, v in f.items() if v != ''})
    path = ed / f'{name}.yml'
    path.write_text(yaml.safe_dump({'bericht': (folder / 'rueckgabe.yml').relative_to(base).as_posix(), 'befunde': findings},
                                   allow_unicode=True, sort_keys=False), encoding='utf-8')
    return path


def _scope_numbers(config, entry):
    """{„N.M“: (Abschnitts-ID, Titel)} der Abschnitte des Checkouts (aktuelle Gliederung) für den Überschriften-Rückfall."""
    known = set(entry.get('abschnitte') or {})
    return {f'{ci}.{si}': (sec['id'], sec['title']) for ci, ch in enumerate(config['structure']['chapters'], start=1)
            for si, sec in enumerate(ch['sections'], start=1) if sec['id'] in known}


def checkin(base, config, files, checkout_id=None, date=None, repo=None):
    """Rückgabe einchecken; gibt (Ablageordner, Bericht) zurück. Fehler: ValueError, es bleibt nichts liegen."""
    import checks
    date = date or datetime.date.today().isoformat()
    files = [Path(f) for f in files]
    if not files:
        raise ValueError('Mindestens eine Datei angeben')
    kinds = {kind_of(f) for f in files}
    if len(kinds) > 1:
        raise ValueError('Eine Rückgabe besteht aus Dateien einer Art (DOCX, PDF oder Bilder)')
    kind = kinds.pop()
    for f in files:
        if not f.is_file():
            raise ValueError(f'Datei nicht gefunden: {f}')

    pages, found_ids = [], set()
    props, docx_data, report_extra = {}, None, {}
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        if kind == 'docx':
            report_extra['programm'] = docx_application(files[0])
            props = docx_properties(files[0])
            if props.get('ghostwriter_checkout'):
                found_ids.add(props['ghostwriter_checkout'])
                report_extra['kennung_aus'] = 'eigenschaft'
            else:
                fid, how = docx_id_fallback(files[0])
                if fid:
                    found_ids.add(fid)
                    report_extra['kennung_aus'] = how
        else:
            import cv2
            images = []
            for f in files:
                if kind == 'pdf':
                    prefix = tmp / f'{f.stem}'
                    subprocess.run(['pdftoppm', '-r', '300', '-png', str(f), str(prefix)], check=True, capture_output=True)
                    images += sorted(tmp.glob(f'{f.stem}-*.png'))
                else:
                    images.append(f)
            for k, img_path in enumerate(images, start=1):
                img = cv2.imread(str(img_path), cv2.IMREAD_COLOR)
                if img is None:
                    pages.append({'seite': k, 'datei': img_path.name, 'zuordnung': 'unbekannt', 'grund': 'Bild nicht lesbar'})
                    continue
                payload = parse_payload(decode_qr(img) or '')
                rec = {'seite': k, 'datei': img_path.name, 'zuordnung': 'qr' if payload else 'unbekannt'}
                if payload:
                    rec['kennung'], rec['kapitel'] = payload['id'], payload['chapter'] or ''
                    found_ids.add(payload['id'])
                    if repo and payload['repo'] not in ('unbekannt', repo):
                        raise ValueError(f'Der Code gehört zu {payload["repo"]}, nicht zu {repo}; nichts abgelegt')
                else:
                    rec['grund'] = 'kein QR-Code erkannt'
                pages.append(rec)
                pages[-1]['_img'] = img_path

        if checkout_id:
            if found_ids and found_ids != {checkout_id}:
                raise ValueError(f'Die Datei gehört zu {", ".join(sorted(found_ids))}, nicht zu {checkout_id}; nichts abgelegt')
            found_ids = {checkout_id}
        if not found_ids:
            raise ValueError('Keine Kennung erkannt (weder Dokumenteigenschaft noch QR-Code); nichts abgelegt. '
                             'Mit --checkout GW-XXXX kann die Kennung von Hand angegeben werden.')
        if len(found_ids) > 1:
            raise ValueError(f'Mehrere Kennungen in einer Rückgabe: {", ".join(sorted(found_ids))}; nichts abgelegt')
        cid = found_ids.pop()
        data = co.load(base)
        entry = next((e for e in data['checkouts'] if e['id'] == cid), None)
        if not entry:
            raise ValueError(f'Checkout {cid} gibt es in diesem Buch nicht; nichts abgelegt')

        digests = [file_digest(f) for f in files]
        for r in entry.get('rueckgaben') or []:
            if r.get('pruefsummen') == digests:
                raise ValueError(f'Diese Rückgabe wurde schon eingecheckt ({r["ordner"]}); nichts abgelegt, nichts doppelt')
        folder = folder_for(base, cid, date)
        folder.mkdir(parents=True)
        report = {'kennung': cid, 'art': kind, 'datum': date, 'checkout_status': entry['status'],
                  'spaet': entry['status'] != 'ausgecheckt', 'dateien': [], **report_extra}
        if kind == 'docx':
            docx_data = read_docx(files[0], _scope_numbers(config, entry))
        for i, f in enumerate(files, start=1):
            target = f'original{"" if len(files) == 1 else f"-{i}"}{f.suffix.lower()}'
            shutil.copyfile(f, folder / target)
            report['dateien'].append(target)

        items, unknown, comments_n = [], [], 0
        if kind == 'docx':
            sections, comments, tracked, props, structure = docx_data
            report['aenderungsnachverfolgung'] = tracked
            if docx_losses(files[0]):
                report['nicht_uebernommen'] = docx_losses(files[0])
            if not (tracked['eingefuegt'] or tracked['geloescht']) and not comments:
                report['vergleich'] = ('keine Änderungsverfolgung und keine Kommentare gefunden, Vergleich über den Text'
                                       + (f' ({report["programm"]})' if report.get('programm') not in (None, 'unbekannt') else ''))
            how = {s_['erkannt'] for s_ in structure}
            if how - {'textmarke'}:
                report['zuordnung_abschnitte'] = ('Textmarken fehlen, Abschnitte über die Überschriften zugeordnet'
                                                  if 'textmarke' not in how else 'teils über die Überschriften zugeordnet')
            known = {s for s in (entry.get('abschnitte') or {})}
            for sid, theirs in sections.items():
                if sid.startswith('neu:'):
                    continue                                   # neuer Abschnitt: steht unter `aufbau`
                if sid not in known:
                    unknown.append({'abschnitt': sid, 'grund': 'nicht Teil des Checkouts'})
                    continue
                rel = next(s['path'] for c in config['structure']['chapters'] for s in c['sections'] if s['id'] == sid)
                ours = baseline(base, entry.get('commit', ''), rel) if entry.get('commit') else None
                if ours is None:
                    unknown.append({'abschnitt': sid, 'grund': 'Ausgangsstand nicht lesbar (Commit fehlt)'})
                    continue
                today = checks.manuscript(base, config, sid) or ''
                for it in compare_section(sid, ours, theirs, today):
                    items.append({**it, 'abschnitt': sid, 'quelle': f'{report["dateien"][0]}#{sid}', 'gegenleser': entry.get('gegenleser', '')})
            base_struct = baseline_structure(base, entry.get('commit', '')) if entry.get('commit') else None
            report['aufbau'] = detect_aufbau(set(entry.get('abschnitte') or {}), base_struct, structure)
            report['gliederung'] = _fingerprint(config)
            for sid, author, text, anchor in comments:
                if sid in known:
                    items.append({'abschnitt': sid, 'art': 'aufbau', 'befund': f'Kommentar von {author or "Gegenleser"}: {text}'[:400],
                                  'frage': f'Kommentar zu „{anchor}“: {text}', 'quelle': f'{report["dateien"][0]}#{sid}',
                                  'gegenleser': entry.get('gegenleser', '')})
                    comments_n += 1
            if tracked['eingefuegt'] or tracked['geloescht']:
                report['hinweis'] = ('Änderungsnachverfolgung enthalten: nicht angenommen, jede Änderung steht als Befund '
                                     'zur Entscheidung.')
        else:
            steps = []
            if kind == 'scan':
                import material
                import cv2
                for rec in pages:
                    img = rec.get('_img')
                    if img is None:
                        continue
                    out, steps = material.enhance(cv2.imread(str(img)))
                    name = f'seite-{rec["seite"]:02d}.jpg'
                    cv2.imwrite(str(folder / name), out, [cv2.IMWRITE_JPEG_QUALITY, 92])
                    rec['aufbereitet'] = name
            report['aufbereitung'] = steps
            for rec in pages:
                rec.pop('_img', None)
            for rec in pages:   # Hilfe fürs Abschreiben: welche Abschnitte hat das Kapitel dieser Seite (#573)
                ch = next(((ci, c) for ci, c in enumerate(config['structure']['chapters'], start=1) if c['id'] == rec.get('kapitel')), None)
                if ch:
                    rec['abschnitte_im_kapitel'] = [f'{ch[0]}.{si} {sec["title"]}' for si, sec in enumerate(ch[1]['sections'], start=1)]
            report['seiten'] = pages
            report['anmerkungen'] = []          # vom Assistenten abgeschrieben: Seite, Nummer, Text, sicher
            report['offene_fragen'] = [f'Seite {p["seite"]}: keine Zuordnung (kein QR-Code)' for p in pages if p['zuordnung'] == 'unbekannt']
            if kind == 'pdf':
                comments_n = _pdf_comments(files[0], pages, report, config, set(entry.get('abschnitte') or {}))
                for c in report.pop('pdf_kommentare', []):
                    if c.get('abschnitt'):
                        items.append({'abschnitt': c['abschnitt'], 'art': 'aufbau', 'befund': f'PDF-Kommentar: {c["text"]}'[:400],
                                      'frage': f'Kommentar zu „{c.get("markiert", "")}“: {c["text"]}' if c.get('markiert') else f'Kommentar: {c["text"]}',
                                      'quelle': f'{report["dateien"][0]}#Seite {c["seite"]}', 'gegenleser': entry.get('gegenleser', '')})
                    else:
                        report['offene_fragen'].append(f'PDF-Kommentar auf Seite {c["seite"]} ohne Abschnitt: {c["text"][:80]}')
        report['unbekannt'] = unknown
        report['befunde'] = len(items)
        report['kommentare'] = comments_n
        if items:
            fpath = write_findings(base, cid, date, folder, items)
            report['befunddatei'] = fpath.relative_to(base).as_posix()
        (folder / 'rueckgabe.yml').write_text(yaml.safe_dump(report, allow_unicode=True, sort_keys=False), encoding='utf-8')
        # Befunddatei verweist auf den Bericht; nach dem Schreiben des Berichts gültig
        entry.setdefault('rueckgaben', []).append({'ordner': folder.relative_to(base).as_posix(), 'art': kind, 'datum': date,
                                                   'befunde': len(items), 'pruefsummen': digests})
        co.save(base, data)
        return folder, report


HEADING = re.compile(r'^(\d+)\.(\d+)$')
BBOX_PAGE = re.compile(r'<page width="([\d.]+)" height="([\d.]+)">(.*?)</page>', re.S)
BBOX_WORD = re.compile(r'<word xMin="([\d.]+)" yMin="([\d.]+)" xMax="([\d.]+)" yMax="([\d.]+)">(.*?)</word>', re.S)


def pdf_words(path):
    """Wörter je Seite mit Lage (Punkte, y von oben) aus `pdftotext -bbox`: [(Breite, Höhe, [(x0, y0, x1, y1, Text)])]."""
    try:
        out = subprocess.run(['pdftotext', '-bbox', str(path), '-'], check=True, capture_output=True, text=True).stdout
    except (OSError, subprocess.CalledProcessError):
        return []
    import html
    pages = []
    for m in BBOX_PAGE.finditer(out):
        words = [(float(a), float(b), float(c), float(d), html.unescape(t)) for a, b, c, d, t in BBOX_WORD.findall(m.group(3))]
        pages.append((float(m.group(1)), float(m.group(2)), words))
    return pages


def pdf_headings(pages, valid):
    """Abschnittsüberschriften „N.M“ am Zeilenanfang: [(Seite, y, 'N.M')] in Lesereihenfolge; `valid` = bekannte Nummern."""
    found = []
    for k, (_, _, words) in enumerate(pages, start=1):
        left = min((w[0] for w in words), default=0)
        for x0, y0, _x1, _y1, text in words:
            if HEADING.match(text) and text in valid and x0 <= left + 12:
                found.append((k, y0, text))
    return found


def section_at(headings, page, top):
    """Letzte Überschrift vor der Stelle (Seite, y von oben): die Nummer „N.M“ oder None."""
    before = [h for h in headings if h[0] < page or (h[0] == page and h[1] <= top + 2)]
    return before[-1][2] if before else None


def _pdf_comments(path, pages, report, config=None, known=None):
    """PDF-Kommentare (Anmerkungen mit Text) auslesen: Seite, Text, markierte Stelle und Abschnitt. Der Abschnitt ist die
    letzte Überschrift „N.M“ vor der Stelle (nur Abschnitte des Checkouts, `known`); ohne Überschrift `unbekannt`.
    Gibt die Zahl zurück; `report['pdf_kommentare']` hält sie für die Befunde."""
    try:
        from pypdf import PdfReader
    except ImportError:
        return 0
    valid, ids = set(), {}
    for ci, ch in enumerate((config or {}).get('structure', {}).get('chapters', []), start=1):
        for si, sec in enumerate(ch['sections'], start=1):
            valid.add(f'{ci}.{si}')
            ids[f'{ci}.{si}'] = sec['id']
    words = pdf_words(path) if valid else []
    heads = pdf_headings(words, valid)
    n = 0
    report.setdefault('pdf_kommentare', [])
    for k, page in enumerate(PdfReader(str(path)).pages, start=1):
        for annot in page.get('/Annots') or []:
            obj = annot.get_object()
            text = str(obj.get('/Contents') or '').strip()
            if not (text and obj.get('/Subtype') in ('/Text', '/Highlight', '/FreeText', '/Underline', '/StrikeOut', '/Caret')):
                continue
            rec = next((p for p in pages if p['seite'] == k), {})
            item = {'seite': k, 'kapitel': rec.get('kapitel', ''), 'text': text, 'sicher': 'ja', 'quelle': 'PDF-Kommentar'}
            rect = [float(v) for v in obj.get('/Rect') or []]
            if len(rect) == 4 and k <= len(words):
                height = words[k - 1][1]
                x0, x1, top, bottom = min(rect[0], rect[2]), max(rect[0], rect[2]), height - max(rect[1], rect[3]), height - min(rect[1], rect[3])
                marked = ' '.join(w[4] for w in words[k - 1][2] if w[0] < x1 and w[2] > x0 and w[1] < bottom and w[3] > top)
                if marked:
                    item['markiert'] = marked[:200]
                number = section_at(heads, k, top)
                if number and ids.get(number) in (known or ids):
                    item['abschnitt'], item['nummer'], item['zuordnung'] = ids[number], number, 'ueberschrift'
            item.setdefault('zuordnung', 'unbekannt')
            report['anmerkungen'].append(item)
            report['pdf_kommentare'].append(item)
            n += 1
    return n


def note(base, config, folder, seite, text, abschnitt=None, alt=None, neu=None, frage=None, unleserlich=False, art='sprache'):
    """Eine vom Assistenten abgeschriebene Anmerkung einer Scan-Seite eintragen (#573): in `rueckgabe.yml` und, wenn sie
    einen Befund ergibt, in die Befunddatei. Nie raten: `unleserlich` oder ohne Abschnitt wird nur als offene Frage vermerkt.
    Eindeutig = `alt` und `neu` (beide aus dem Text, `alt` muss im Abschnitt stehen); unklar = `frage`. → Anmerkung."""
    base, folder = Path(base), Path(folder)
    if not folder.is_absolute():
        folder = base / folder
    path = folder / 'rueckgabe.yml'
    if not path.is_file():
        raise ValueError(f'{folder}: keine rueckgabe.yml (Ordner einer Rückgabe angeben)')
    report = yaml.safe_load(path.read_text(encoding='utf-8')) or {}
    if report.get('art') != 'scan' and not any(p.get('seite') == seite for p in report.get('seiten') or []):
        raise ValueError(f'Seite {seite} gibt es in dieser Rückgabe nicht')
    page = next((p for p in report.get('seiten') or [] if p.get('seite') == seite), None)
    if page is None:
        raise ValueError(f'Seite {seite} gibt es in dieser Rückgabe nicht')
    cid = report['kennung']
    entry = next(e for e in co.load(base)['checkouts'] if e['id'] == cid)
    sid, number = None, None
    if abschnitt:
        for ci, ch in enumerate(config['structure']['chapters'], start=1):
            for si, sec in enumerate(ch['sections'], start=1):
                if abschnitt in (f'{ci}.{si}', sec['id']):
                    sid, number = sec['id'], f'{ci}.{si}'
        if not sid:
            raise ValueError(f'Abschnitt {abschnitt} gibt es nicht')
        if sid not in (entry.get('abschnitte') or {}):
            raise ValueError(f'Abschnitt {abschnitt} gehört nicht zu diesem Checkout')
    nr = max((a.get('nr', 0) for a in report.get('anmerkungen') or []), default=0) + 1
    item = {'nr': nr, 'seite': seite, 'text': text.strip(), 'sicher': 'nein' if unleserlich else 'ja', 'quelle': 'Scan, abgeschrieben'}
    if number:
        item['abschnitt'], item['nummer'] = sid, number
    if unleserlich:
        item['unleserlich'] = True
    finding = None
    if not unleserlich and sid:
        if alt and neu:
            today = __import__('checks').manuscript(base, config, sid) or ''
            ours = baseline(base, entry.get('commit', ''), next(s['path'] for c in config['structure']['chapters'] for s in c['sections'] if s['id'] == sid)) or ''
            if alt not in ours:
                raise ValueError('„alt“ steht nicht wörtlich im Ausgangsstand des Abschnitts; als Frage eintragen (--frage)')
            finding = {'art': art, 'alt': alt, 'neu': neu, 'befund': f'Randnotiz Seite {seite}, Nr. {nr}',
                       'frage': ('Die Stelle hat sich seit dem Checkout geändert. ' if alt not in today else '') + 'Randnotiz übernehmen?'}
        else:
            finding = {'art': 'aufbau', 'befund': f'Randnotiz Seite {seite}, Nr. {nr}: {text.strip()}'[:400], 'frage': frage or text.strip()}
    if finding:
        finding.update({'abschnitt': sid, 'quelle': f'seite-{seite:02d}#{nr}', 'gegenleser': entry.get('gegenleser', '')})
        date = report.get('datum') or datetime.date.today().isoformat()
        if report.get('befunddatei'):
            fpath = base / report['befunddatei']
            data = yaml.safe_load(fpath.read_text(encoding='utf-8')) or {}
        else:
            fpath, data = None, {'bericht': path.relative_to(base).as_posix(), 'befunde': []}
        fid = f'b-{len(data["befunde"]) + 1:03d}'
        row = {'id': fid, 'abschnitt': sid, 'art': finding['art'], 'befund': finding['befund'], 'status': 'offen', 'schweregrad': 'mittel',
               'quelle': finding['quelle'], 'gegenleser': finding['gegenleser']}
        for key in ('alt', 'neu', 'frage'):
            if finding.get(key):
                row[key] = finding[key]
        data['befunde'].append({k: v for k, v in row.items() if v != ''})
        if fpath is None:
            fpath = write_findings(base, cid, date, folder, [])
        fpath.write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False), encoding='utf-8')
        report['befunddatei'] = fpath.relative_to(base).as_posix()
        report['befunde'] = len(data['befunde'])
        item['befund'] = fid
    else:
        why = 'unleserlich' if unleserlich else 'ohne Abschnitt'
        report.setdefault('offene_fragen', []).append(f'Seite {seite}, Nr. {nr} ({why}): {text.strip()[:80]}')
    report.setdefault('anmerkungen', []).append(item)
    path.write_text(yaml.safe_dump(report, allow_unicode=True, sort_keys=False), encoding='utf-8')
    for r in entry.get('rueckgaben') or []:
        if r['ordner'] == folder.relative_to(base).as_posix():
            r['befunde'] = report.get('befunde', 0)
    data_all = co.load(base)
    for e in data_all['checkouts']:
        if e['id'] == cid:
            e['rueckgaben'] = entry.get('rueckgaben')
    co.save(base, data_all)
    return item


def _numbers(config):
    return {sec['id']: f'{ci}.{si}' for ci, ch in enumerate(config['structure']['chapters'], start=1)
            for si, sec in enumerate(ch['sections'], start=1)}


def aufbau_list(base, config, folder):
    """Aufbau-Änderungen einer Rückgabe (#209) als Zeilen: (ID, Status, Text)."""
    report = yaml.safe_load((Path(base) / folder / 'rueckgabe.yml').read_text(encoding='utf-8')) or {}
    numbers = _numbers(config)
    return [(a['id'], a.get('status', 'offen'), aufbau_text(a, numbers) + (f' – {a["grund"]}' if a.get('grund') else ''))
            for a in report.get('aufbau') or []]


def aufbau_apply(base, config, folder, ids, confirm=False):
    """Ausgewählte Aufbau-Änderungen übernehmen (#209), jede nur nach eigener Bestätigung (`confirm`). Voraussetzung: Der
    Checkout ist beendet (wie bei den Befunden). Abgeschlossene Abschnitte und Kapitel bleiben geschützt: umbenennen und
    umstellen im Kapitel ändern den Text nicht und gehen auch bei einem abgeschlossenen Abschnitt, Löschen und Verschieben in
    ein anderes Kapitel erst nach der Rücknahme der Freigabe. Nie ohne `confirm`. → [(ID, Ergebnis)]"""
    import sections
    base, folder = Path(base), Path(folder)
    if not confirm:
        raise ValueError('Ohne ausdrückliche Bestätigung wird nichts übernommen (--confirm)')
    path = (folder if folder.is_absolute() else base / folder) / 'rueckgabe.yml'
    report = yaml.safe_load(path.read_text(encoding='utf-8')) or {}
    entry = next(e for e in co.load(base)['checkouts'] if e['id'] == report['kennung'])
    if entry['status'] == 'ausgecheckt':
        raise ValueError(f'Checkout {entry["id"]} läuft noch: erst ausdrücklich beenden (checkout.py end), dann übernehmen')
    from render_view import load as _load
    if report.get('gliederung') and report['gliederung'] != _fingerprint(_load(base)[1]):
        raise ValueError('Die Gliederung hat sich seit der Rückgabe geändert; die Rückgabe bitte erneut prüfen (checkin.py … aufbau zeigt die Liste), nichts übernommen')
    items = {a['id']: a for a in report.get('aufbau') or []}
    wanted = [items[i] for i in ids if i in items]
    unknown = [i for i in ids if i not in items]
    if unknown:
        raise ValueError(f'Unbekannte Aufbau-Änderung: {", ".join(unknown)}')
    order = {'umbenannt': 0, 'neu': 1, 'verschoben': 2, 'geloescht': 3}
    results = []
    for a in sorted(wanted, key=lambda x: order[x['art']]):
        if a.get('status') == 'uebernommen':
            results.append((a['id'], 'schon übernommen'))
            continue
        try:
            from render_view import load
            cfg = load(base)[1]
            if a['art'] == 'umbenannt':
                msg = sections.cmd_rename(base, a['abschnitt'], a['neu'])
            elif a['art'] == 'neu':
                if not a.get('kapitel'):
                    raise ValueError('Kapitel des neuen Abschnitts unbekannt')
                chapter = cfg['structure']['chapters'][int(a['kapitel']) - 1]
                pos = 1
                if a.get('hinter'):
                    ids_in = [x['id'] for x in chapter['sections']]
                    pos = ids_in.index(a['hinter']) + 2 if a['hinter'] in ids_in else len(ids_in) + 1
                msg = sections.cmd_add(base, chapter['id'], a['titel'], pos, a.get('text'))
            elif a['art'] == 'verschoben':
                chapter = cfg['structure']['chapters'][int(a['kapitel']) - 1]
                current = next(c for c in cfg['structure']['chapters'] if any(x['id'] == a['abschnitt'] for x in c['sections']))
                if current['id'] == chapter['id']:
                    msg = sections.cmd_reorder(base, a['abschnitt'], a.get('hinter'))
                else:
                    ids_in = [x['id'] for x in chapter['sections']]
                    pos = (ids_in.index(a['hinter']) + 2) if a.get('hinter') in ids_in else 1
                    msg = sections.cmd_move(base, a['abschnitt'], chapter['id'], pos)
            else:
                msg = sections.cmd_remove(base, a['abschnitt'], confirm=True)
            a['status'] = 'uebernommen'
            results.append((a['id'], msg.strip().splitlines()[0]))
        except (SystemExit, ValueError, KeyError, IndexError) as exc:
            a['status'] = 'nicht-moeglich'
            a['grund'] = str(exc)[:200]
            results.append((a['id'], f'nicht möglich: {exc}'))
    report['aufbau'] = list(items.values())
    report['gliederung'] = _fingerprint(_load(base)[1])      # nach der Übernahme gilt die neue Gliederung für weitere Auswahlen
    path.write_text(yaml.safe_dump(report, allow_unicode=True, sort_keys=False), encoding='utf-8')
    return results


# ---------- Anzeige (#573, #209, #630) ----------

def view_values(base, config, folder, language='de'):
    """Werte für die Vorlage `rueckgabe` (ghostwriter-ui ab 0.70.0): (values, blocks) aus `rueckgabe.yml` im Ablageordner."""
    base = Path(base)
    folder = Path(folder) if Path(folder).is_absolute() else base / folder
    report = yaml.safe_load((folder / 'rueckgabe.yml').read_text(encoding='utf-8')) or {}
    en = language == 'en'
    t = (lambda de, en_: en_ if en else de)
    entry = next((e for e in co.load(base)['checkouts'] if e['id'] == report.get('kennung')), {})
    ended = entry.get('status', 'ausgecheckt') != 'ausgecheckt'
    kinds = {'docx': t('Word-Datei (DOCX)', 'Word file (DOCX)'), 'pdf': 'PDF', 'scan': t('Scan oder Foto der Ausdrucke', 'Scan or photo of the printouts')}
    kind = kinds.get(report.get('art'), str(report.get('art')))
    if report.get('programm') and report['programm'] != 'unbekannt':
        kind += f' · {report["programm"]}'
    date = str(report.get('datum') or '')
    shown = f'{date[8:10]}.{date[5:7]}.{date[:4]}' if en is False and len(date) == 10 else date
    n, c = report.get('befunde') or 0, report.get('kommentare') or 0
    stats = (f'{n} findings · {c} comments' if en else f'{n} Befunde · {c} Kommentare')
    aufbau = report.get('aufbau') or []
    if aufbau:
        stats += (f' · {len(aufbau)} structure changes' if en else f' · {len(aufbau)} Aufbau-Änderungen')
    notes = [x for x in (report.get('nicht_uebernommen') or [])]
    notes = [t('Nicht übernommen: ', 'Not taken over: ') + x for x in notes]
    for key in ('vergleich', 'zuordnung_abschnitte', 'hinweis'):
        if report.get(key):
            notes.append(str(report[key]))
    pages = []
    for p in report.get('seiten') or []:
        pages.append(f'{t("Seite", "Page")} {p["seite"]}: ' + (f'{t("Kapitel", "chapter")} {p.get("kapitel") or "?"} (QR)' if p.get('zuordnung') == 'qr' else t('unbekannt', 'unknown')))
    rows = aufbau_list(base, config, folder.relative_to(base)) if aufbau else []
    values = {'RET_ID': report.get('kennung', ''), 'RET_KIND_TEXT': kind, 'RET_DATE_TEXT': shown, 'RET_STATS_TEXT': stats,
              'RET_LATE_TEXT': (t(f'Späte Rückgabe: Der Checkout ist {report.get("checkout_status")}; Zwischenänderungen erscheinen als Frage.',
                                  f'Late return: the checkout is {report.get("checkout_status")}; changes in between appear as questions.') if report.get('spaet') else ''),
              'RET_FOLDER': folder.relative_to(base).as_posix(), 'RET_FINDINGS_FILE': report.get('befunddatei') or '',
              'RET_END_ARGS': '' if ended else json.dumps({'id': report.get('kennung')}, separators=(',', ':')),
              'RET_CAN_APPLY': '1' if ended else '',
              'RET_APPLY_HINT': '' if ended or not aufbau else t('Der Checkout läuft noch: erst beenden, dann lassen sich Aufbau-Änderungen übernehmen.',
                                                                'The checkout is still running: end it first, then structure changes can be applied.')}
    blocks = {'NOTES': [{'N_TEXT': x} for x in notes], 'PAGES': [{'P_TEXT': x} for x in pages],
              'QUESTIONS': [{'Q_TEXT': x} for x in report.get('offene_fragen') or []],
              'AUFBAU': [{'A_ID': i, 'A_TEXT': text, 'A_STATE': st} for i, st, text in rows]}
    return values, blocks


def text_view(base, config, folder, language='de'):
    values, blocks = view_values(base, config, folder, language)
    en = language == 'en'
    lines = [f'### 📥 {"Return checked in" if en else "Rückgabe eingecheckt"} · {values["RET_ID"]}', '',
             f'{values["RET_KIND_TEXT"]} · {values["RET_DATE_TEXT"]} · {values["RET_STATS_TEXT"]}', '']
    if values['RET_LATE_TEXT']:
        lines += [f'⚠️ {values["RET_LATE_TEXT"]}', '']
    lines += [f'- {n["N_TEXT"]}' for n in blocks['NOTES']] + [f'- {p["P_TEXT"]}' for p in blocks['PAGES']]
    if blocks['QUESTIONS']:
        lines += ['', '**' + ('Open questions' if en else 'Offene Fragen') + '**'] + [f'- {q["Q_TEXT"]}' for q in blocks['QUESTIONS']]
    if blocks['AUFBAU']:
        lines += ['', '**' + ('Structure changes' if en else 'Aufbau-Änderungen') + '**'] + [f'- `{a["A_ID"]}` [{a["A_STATE"]}] {a["A_TEXT"]}' for a in blocks['AUFBAU']]
        lines += ['', values['RET_APPLY_HINT'] or ('Apply with: `checkin.py <book> aufbau <folder> --apply a-001 --confirm`, only after your own confirmation.' if en
                                                      else 'Übernehmen: `checkin.py <buch> aufbau <ordner> --apply a-001 --confirm`, nur nach deiner ausdrücklichen Bestätigung.')]
    if values['RET_FINDINGS_FILE']:
        lines += ['', f'{"Findings" if en else "Befunde"}: `{values["RET_FINDINGS_FILE"]}`']
    return '\n'.join(lines) + '\n'


def summary(report):
    lines = [f'{report["kennung"]}: {report["art"]}-Rückgabe eingecheckt ({report["datum"]})']
    if report.get('spaet'):
        lines.append(f'Der Checkout ist {report["checkout_status"]}: späte Rückgabe, Zwischenänderungen erscheinen als Frage.')
    if report.get('seiten'):
        ok = sum(1 for p in report['seiten'] if p['zuordnung'] == 'qr')
        lines.append(f'{len(report["seiten"])} Seiten, {ok} über den QR-Code zugeordnet, {len(report["seiten"]) - ok} unbekannt')
    lines.append(f'{report["befunde"]} Befunde, {report["kommentare"]} Kommentare/Anmerkungen')
    if report.get('aufbau'):
        lines.append(f'{len(report["aufbau"])} Aufbau-Änderungen zur eigenen Bestätigung (checkin.py <buch> aufbau <ordner>)')
    for line in report.get('nicht_uebernommen') or []:
        lines.append(f'Nicht übernommen: {line}')
    for key in ('programm', 'vergleich', 'zuordnung_abschnitte'):
        if report.get(key):
            lines.append(f'{key.capitalize()}: {report[key]}')
    if report.get('hinweis'):
        lines.append(report['hinweis'])
    if report.get('befunddatei'):
        lines.append(f'Befunde: {report["befunddatei"]} (weiter mit hinweise.py collect)')
    lines.append('Der Checkout bleibt bestehen; beenden nur ausdrücklich.')
    return '\n'.join(lines) + '\n'


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if len(argv) > 1 and argv[1] == 'aufbau':
        ap2 = argparse.ArgumentParser(prog='checkin.py <buch> aufbau', description='Aufbau-Änderungen einer Rückgabe (#209)')
        ap2.add_argument('project')
        ap2.add_argument('cmd')
        ap2.add_argument('folder')
        ap2.add_argument('--apply', help='IDs, durch Komma getrennt (a-001,a-003); nur mit --confirm')
        ap2.add_argument('--confirm', action='store_true', help='ausdrückliche Bestätigung des Benutzers')
        a = ap2.parse_args(argv)
        from render_view import load
        base, config = load(a.project)
        try:
            if a.apply:
                for aid, text in aufbau_apply(base, config, a.folder, [x.strip() for x in a.apply.split(',') if x.strip()], a.confirm):
                    print(f'{aid}: {text}')
            else:
                rows = aufbau_list(base, config, a.folder)
                print('\n'.join(f'{i} [{st}] {t}' for i, st, t in rows) or 'Keine Aufbau-Änderungen.')
        except (ValueError, OSError) as exc:
            print(exc, file=sys.stderr)
            return 1
        return 0
    if len(argv) > 1 and argv[1] == 'note':
        np = argparse.ArgumentParser(prog='checkin.py <buch> note', description='Abgeschriebene Randnotiz eintragen (#573)')
        np.add_argument('project')
        np.add_argument('cmd')
        np.add_argument('folder', help='Ordner der Rückgabe, z. B. checkouts/GW-7F3A/rueckgabe-2026-11-25')
        np.add_argument('--seite', type=int, required=True)
        np.add_argument('--text', required=True, help='abgeschriebener Wortlaut der Notiz')
        np.add_argument('--abschnitt', help='Nummer (3.2) oder ID; ohne: nur offene Frage')
        np.add_argument('--alt')
        np.add_argument('--neu')
        np.add_argument('--frage')
        np.add_argument('--art', default='sprache')
        np.add_argument('--unleserlich', action='store_true')
        a = np.parse_args(argv)
        from render_view import load
        base, config = load(a.project)
        try:
            item = note(base, config, a.folder, a.seite, a.text, a.abschnitt, a.alt, a.neu, a.frage, a.unleserlich, a.art)
        except ValueError as exc:
            print(exc, file=sys.stderr)
            return 1
        print(f'Anmerkung {item["nr"]} auf Seite {item["seite"]} eingetragen' + (f' (Befund {item["befund"]})' if item.get('befund') else ' (offene Frage)'))
        return 0
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('project')
    ap.add_argument('files', nargs='+')
    ap.add_argument('--checkout')
    ap.add_argument('--date')
    ap.add_argument('--repo')
    args = ap.parse_args(argv)
    from render_view import load
    base, config = load(args.project)
    try:
        folder, report = checkin(base, config, args.files, args.checkout, args.date, args.repo)
    except ValueError as exc:
        print(exc, file=sys.stderr)
        return 1
    print(summary(report), end='')
    return 0


if __name__ == '__main__':
    sys.exit(main())
