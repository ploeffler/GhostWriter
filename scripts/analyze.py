#!/usr/bin/env python3
"""Analysen über das ganze Buch als Hintergrundlauf (#123, #124): Figuren, Kurzbeschreibungen und mehr.

Aufruf:
  python scripts/analyze.py <buch> plan [--kind ART[,ART…]] [--scope book|N] [--json]
  python scripts/analyze.py <buch> run  [--kind ART[,ART…]] [--scope book|N]
  python scripts/analyze.py <buch> latest [--kind ART] [--json]     neuester offener Lauf (für die Übersicht)
  python scripts/analyze.py <buch> applied <run-id> [--kind ART]  Lauf als übernommen bzw. verworfen vermerken
  python scripts/analyze.py <buch> apply <run-id> --kind ART <auswahl.json>   ausgewählte Vorschläge übernehmen
                                                                              (alle Arten außer characters)

Arten (`--kind`, Vorgabe characters; mehrere mit Komma):
  characters  Figuren (#123); übernommen mit scripts/characters.py apply
  summaries   Kurzbeschreibung und Ziel je Abschnitt und Kapitel (#124); übernommen in die Abschnittsdatei
              („## Ziel des Abschnitts“, „## Kurzbeschreibung“) bzw. die README.md des Kapitels
  style       Stilprofil (Erzählperspektive, Zeitform, Anrede, Sprachebene, Ton, Stilmittel) je Abschnitt, dazu
              Zahlen ohne KI (Wörter je Satz, Anteil wörtlicher Rede); übernommen nach ghostwriter.yml (`style`)
  places      Schauplätze mit Art, Beschreibung und Abschnitten; andere Bezeichnungen desselben Orts über
              merge_model; übernommen nach story/places.yml
  timeline    Zeitleiste: Ereignisse je Abschnitt mit Zeitangabe aus dem Text; Zeitsprünge, Widersprüche und
              Unklares als Hinweisliste (merge_model, nur Verweise auf geprüfte Ereignisse); übernommen nach
              story/timeline.yml
  continuity  Widersprüche: je Abschnitt Tatsachen mit Fundstelle, über das ganze Buch Widersprüche (merge_model, nur
              zwischen geprüften Tatsachen); übernommen als Marker [KONTINUITÄT PRÜFEN: …] hinter der Fundstelle
  language    Sprachliche Auffälligkeiten ohne KI (lange Sätze, Wortwiederholungen, gleiche Satzanfänge,
              Füllwörter); mit einem LanguageTool-Server (LANGUAGETOOL_URL, #280) zusätzlich Rechtschreibung,
              Grammatik, Zeichensetzung und Typografie; übernommen als Hinweisliste nach story/hints.yml, der
              Text bleibt unverändert

Läuft in der Action „Analyse im Hintergrund“ (analyse.yml), lokal genauso. Ablauf je Art:
  1. Vorbereiten ohne KI: das Buch je Abschnitt (Vor- und Nachspann je eigener
     Block, nicht bei summaries); je Block ein Fingerabdruck (SHA-256 des
     Textes). Blöcke, deren Fingerabdruck im Zwischenspeicher
     analysis/cache/<art>/ steht, werden nicht neu gelesen.
  2. Je Abschnitt bzw. begrenztem Teil ein KI-Aufruf (parallel, `analysis.model`): Auftrag nur aus dem
     Text, die Abschnitte als `### N.M`; jede Angabe mit wörtlicher Fundstelle
     (`evidence: [{field, where, quote}]`).
  3. Prüfung ohne KI: Eine Fundstelle zählt nur, wenn das Zitat wörtlich im
     angegebenen Abschnitt steht; Angaben ohne gültige Fundstelle fallen weg.
     Figuren: Abschnitte bleiben nur, wenn Name oder ein anderer Name dort
     vorkommt. Kurzbeschreibungen: je Abschnitt mindestens eine Fundstelle in
     diesem Abschnitt, fürs Kapitel eine in einem seiner Abschnitte.
  4. Zusammenführen: Figuren nach gleichen bzw. anderen Namen ohne KI, dann ein
     Aufruf mit `analysis.merge_model` für Spitznamen („Opi“ = „Opa Karl“);
     unterschiedliche Angaben (z. B. Alter) kommen als Widerspruch in die
     Liste, entschieden wird nichts. Kurzbeschreibungen: ohne KI in
     Buchreihenfolge (Kapitel, dann seine Abschnitte). Stilprofil: ohne KI je
     Angabe der häufigste Wert (gewichtet nach Wörtern), abweichende Abschnitte
     als Varianten.
  5. Ablage: analysis/<art>/run-NNN.md (Lauf) und run-NNN.json (Vorschläge,
     `kind` und `items`), Kosten je Aufruf in costs/project.yml (source:
     action_api). Nichts wird automatisch übernommen; ausgewählt wird im Chat
     (Figuren: `render_view.py character-suggest`, sonst `analysis-suggest`;
     START.md, „Analysen im Hintergrund“).

Einstellungen in ghostwriter.yml (alle optional), Block `analysis`:
  provider          anthropic | openai (sonst der erste mit hinterlegtem Schlüssel)
  model, merge_model  Modelle für Schritt 2 und 4 (sonst Vorgaben des Anbieters)
  price_input_per_mtok, price_output_per_mtok  Preise je 1 Mio. Tokens in
                    Projektwährung; ohne Preise: Kosten „unavailable“, Tokens werden
                    trotzdem erfasst
  parallel          gleichzeitige Aufrufe (Vorgabe 4)
  languagetool      Analyse „Sprache“: language, words, disabled_rules
Einstellen im Chat: Formular „Analyse-Einstellungen“ (render_view.py analysis-settings, #299), gespeichert mit
  python scripts/analyze.py <ordner> settings-set '<json>'   (leere Werte = Vorgabe, Feld entfällt)
Schlüssel: Umgebungsvariable mit dem Namen aus providers.yml (ANTHROPIC_API_KEY,
OPENAI_API_KEY), in der Action aus den GitHub-Secrets.

Tests: GHOSTWRITER_FAKE_LLM=<datei.json> ersetzt die KI-Aufrufe durch feste
Antworten ({"extract": {<block>: {...}}, "merge": {...}} für Figuren, für andere
Arten dasselbe unter dem Namen der Art: {"summaries": {"extract": {…}}}).
"""
import argparse
import concurrent.futures
import datetime
import hashlib
import json
import os
import re
import sys
import urllib.parse
import urllib.request
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'scripts'))
from render_view import (character_file, character_items, load, matter_items, section_file)  # noqa: E402

PROVIDERS = {
    'anthropic': {'secret': 'ANTHROPIC_API_KEY', 'model': 'claude-haiku-5-5', 'merge_model': 'claude-sonnet-5-5'},
    'openai': {'secret': 'OPENAI_API_KEY', 'model': 'gpt-5-mini', 'merge_model': 'gpt-5'},
}
CHARS_PER_TOKEN = 3.5     # grobe Schätzung für deutschen Text
PROMPT_TOKENS = 900       # Anweisungen und bekannte Angaben je Aufruf (Schätzung)
FIELDS = ('short', 'age', 'appearance', 'traits', 'voice')
QUOTE_RULE = '"quote": "<kurzes wörtliches Zitat aus dem Text, höchstens 25 Wörter, genau wie im Text>"'

EXTRACT_SYSTEM = """Du liest einen Ausschnitt eines Buchs und nennst die Figuren, die darin handeln, sprechen oder
beschrieben werden. Regeln:
- Nur was im Text steht. Nichts erfinden, nichts aus Weltwissen ergänzen. Was der Text nicht sagt, bleibt leer.
- Personen, die nur als Quelle oder Fachautorität erwähnt werden, nicht aufnehmen.
- Jede Angabe braucht eine Fundstelle: evidence = [{"field": "name|short|age|appearance|traits|voice|relation",
  "where": "<Abschnitt wie in der Überschrift, z. B. 1.2>", "quote": "<kurzes wörtliches Zitat, höchstens 25 Wörter>"}].
- Andere Namen derselben Person unter aliases.
Antworte nur mit JSON: {"items": [{"name": "", "aliases": [], "role": "main|supporting|minor", "short": "",
"age": "", "appearance": "", "traits": [], "voice": "", "relations": [{"to": "", "kind": ""}], "sections": [],
"evidence": []}]}"""

MERGE_SYSTEM = """Du bekommst Figuren, die in verschiedenen Kapiteln eines Buchs gefunden wurden, je mit Namen, anderen
Namen und einem Satz. Gib an, welche Einträge dieselbe Person sind (z. B. Spitzname und voller Name). Nur wenn der
Text das klar nahelegt; im Zweifel getrennt lassen. Antworte nur mit JSON: {"groups": [["Name A", "Name B"], …]}"""

SUMMARIES_SYSTEM = """Du liest einen Abschnitt oder einen begrenzten Teil eines Buchs. Die Abschnitte stehen unter Überschriften wie "### 1.2".
Schreibe für den vorliegenden Abschnitt bzw. Teil:
- "short": Kurzbeschreibung, worum es geht (ein bis drei Sätze, sachlich, im Präsens);
- "goal": Ziel, also was der Abschnitt bzw. Teil für das Buch leistet (ein Satz; im Sachbuch: was der Leser
  danach weiß oder kann; in einer Geschichte: was sich für die Handlung oder die Figuren ändert).
Regeln:
- Nur aus dem Text. Nichts erfinden, nichts aus Weltwissen ergänzen, keine Wertung. Was der Text nicht hergibt,
  bleibt leer.
- Jede Angabe braucht mindestens eine Fundstelle: evidence = [{"field": "short|goal", "where": "<Abschnitt, z. B. 1.2>",
  """ + QUOTE_RULE + """}].
Antworte nur mit JSON: {"sections": [{"where": "1.2", "short": "", "goal": "", "evidence": []}],
"chapter": {}}"""


STYLE_SYSTEM = """Du liest einen Abschnitt oder einen begrenzten Teil eines Buchs und beschreibst seinen Stil, nur aus dem Text:
- "perspective": Erzählperspektive: ich | du | wir | er/sie | auktorial | wechselnd
- "tense": Zeitform des Erzählens: Präsens | Präteritum | Perfekt | wechselnd
- "address": Anrede des Lesers: du | Sie | ihr | keine
- "register": Sprachebene: umgangssprachlich | neutral | gehoben | fachlich
- "tone": Ton in zwei bis vier Wörtern, mit Komma getrennt (z. B. "nüchtern, warmherzig")
- "features": bis zu fünf auffällige Stilmittel in wenigen Wörtern (z. B. "kurze Sätze", "Fragen an den Leser")
Regeln: Nur was der Text zeigt, keine Wertung, keine Verbesserungsvorschläge. Was nicht erkennbar ist, bleibt leer.
Jede Angabe braucht eine Fundstelle: evidence = [{"field": "perspective|tense|address|register|tone|features",
"where": "<Abschnitt, z. B. 1.2>", """ + QUOTE_RULE + """}].
Antworte nur mit JSON: {"perspective": "", "tense": "", "address": "", "register": "", "tone": "", "features": [],
"evidence": []}"""



PLACES_SYSTEM = """Du liest einen Ausschnitt eines Buchs und nennst die Schauplätze: Orte, an denen etwas geschieht
oder die beschrieben werden (Städte, Gegenden, Gebäude, Räume, Landschaften, auch erfundene).
Regeln:
- Nur was im Text steht. Nichts erfinden, nichts aus Weltwissen ergänzen. Was der Text nicht sagt, bleibt leer.
- Orte, die nur nebenbei genannt werden (z. B. Herkunft einer Person), nicht aufnehmen.
- "kind": Art des Orts in einem Wort (Stadt, Gegend, Gebäude, Raum, Landschaft, Fahrzeug …).
- "short": ein Satz, wie der Text den Ort beschreibt.
- Andere Namen desselben Orts unter aliases.
- Jede Angabe braucht eine Fundstelle: evidence = [{"field": "name|kind|short", "where": "<Abschnitt, z. B. 1.2>",
  """ + QUOTE_RULE + """}].
Antworte nur mit JSON: {"items": [{"name": "", "aliases": [], "kind": "", "short": "", "sections": [], "evidence": []}]}"""

PLACES_MERGE_SYSTEM = """Du bekommst Schauplätze, die in verschiedenen Kapiteln eines Buchs gefunden wurden, je mit Namen,
anderen Namen und einem Satz. Gib an, welche Einträge derselbe Ort sind (z. B. "das Haus am See" und "Seehaus"). Nur
wenn der Text das klar nahelegt; im Zweifel getrennt lassen. Antworte nur mit JSON: {"groups": [["Name A", "Name B"], …]}"""

TIMELINE_SYSTEM = """Du liest einen Abschnitt oder einen begrenzten Teil eines Buchs und notierst, wann was geschieht, in der Reihenfolge des Textes.
Je Ereignis:
- "where": Abschnitt (z. B. "1.2");
- "when": die Zeitangabe so, wie sie im Text steht oder sich daraus ergibt (z. B. "Sommer 1989", "drei Tage später",
  "am nächsten Morgen", "vor zwanzig Jahren" für eine Rückblende); ohne Zeitangabe im Text leer lassen;
- "what": was geschieht, in einem kurzen Satz;
- "evidence": [{"where": "<Abschnitt>", """ + QUOTE_RULE + """}], am besten die Stelle mit der Zeitangabe.
Regeln: Nur aus dem Text, nichts erfinden, keine Daten ausrechnen, die der Text nicht nennt. Nur Ereignisse, die für
die Handlung bzw. den Ablauf zählen, höchstens acht je Abschnitt.
Antworte nur mit JSON: {"events": [{"where": "", "when": "", "what": "", "evidence": []}]}"""

TIMELINE_MERGE_SYSTEM = """Du bekommst die Ereignisse eines Buchs in der Reihenfolge des Textes, je mit Nummer, Abschnitt,
Zeitangabe und einem Satz. Nenne nur auffällige Stellen der zeitlichen Abfolge:
- "jump": ein großer oder unklarer Sprung (Rückblende, Zeitsprung ohne Hinweis);
- "contradiction": Zeitangaben, die nicht zusammenpassen (z. B. ein Ereignis "eine Woche später", das vor einem
  früheren liegt; ein Alter oder Jahr, das sich widerspricht);
- "unclear": die Abfolge lässt sich aus dem Text nicht bestimmen, obwohl sie für die Handlung zählt.
Nur was sich aus den genannten Zeitangaben ergibt, nichts vermuten. Jede Stelle nennt die Nummern der beteiligten
Ereignisse. Antworte nur mit JSON: {"issues": [{"kind": "jump|contradiction|unclear", "events": [1, 2], "text": ""}]}"""


CONTINUITY_SYSTEM = """Du liest einen Abschnitt oder einen begrenzten Teil eines Buchs und notierst Tatsachen, die an anderer Stelle des Buchs nicht
anders dargestellt werden dürfen: Alter, Aussehen, Verwandtschaft und Beziehungen von Personen; Namen; Orte und ihre
Beschreibung; Daten, Jahreszahlen und Dauern; Zahlen und Mengen; Besitz und Eigenschaften von Dingen; feste
Behauptungen im Sachbuch (z. B. "die Leitlinie empfiehlt …").
Je Tatsache:
- "about": worum es geht (Person, Ort, Ding, Thema), kurz;
- "fact": die Tatsache in einem kurzen Satz, genau so, wie der Text sie darstellt;
- "where": Abschnitt (z. B. "1.2"); """ + QUOTE_RULE + """.
Regeln: Nur was im Text steht, nichts ergänzen, nichts deuten. Höchstens zwölf Tatsachen je Abschnitt.
Antworte nur mit JSON: {"facts": [{"about": "", "fact": "", "where": "", "quote": ""}]}"""

CONTINUITY_MERGE_SYSTEM = """Du bekommst nummerierte Tatsachen aus einem ganzen Buch in der Reihenfolge des Textes, je mit
Abschnitt, Gegenstand und Satz. Nenne die Stellen, an denen sich Tatsachen widersprechen (z. B. zwei verschiedene Alter
derselben Person zur selben Zeit, ein Ort mit zwei verschiedenen Beschreibungen, zwei verschiedene Zahlen für dasselbe).
Eine Entwicklung über die Zeit ist kein Widerspruch. Nur echte Widersprüche aus den genannten Tatsachen, im Zweifel
weglassen. Je Widerspruch die Nummern der beteiligten Tatsachen (mindestens zwei) und ein kurzer Satz.
Antworte nur mit JSON: {"conflicts": [{"facts": [3, 17], "text": ""}]}"""


def settings(config):
    s = {'provider': None, 'model': None, 'merge_model': None, 'price_input_per_mtok': None,
         'price_output_per_mtok': None, 'parallel': 4}
    s.update((config or {}).get('analysis') or {})
    return s


def clean_settings(data):
    """Eingaben des Formulars „Analyse-Einstellungen“ (#299) prüfen; leere Werte entfallen (= Vorgabe)."""
    out = {}
    if not isinstance(data, dict):
        raise ValueError('Einstellungen müssen ein Objekt sein')
    provider = (data.get('provider') or '').strip()
    if provider:
        if provider not in PROVIDERS:
            raise ValueError(f'unbekannter Anbieter {provider!r} ({", ".join(PROVIDERS)})')
        out['provider'] = provider
    for key in ('model', 'merge_model'):
        if str(data.get(key) or '').strip():
            out[key] = str(data[key]).strip()
    for key in ('price_input_per_mtok', 'price_output_per_mtok'):
        v = data.get(key)
        if v not in (None, ''):
            v = float(str(v).replace(',', '.'))
            if v < 0:
                raise ValueError(f'{key}: Preis darf nicht negativ sein')
            out[key] = int(v) if v == int(v) else v
    par = data.get('parallel')
    if par not in (None, ''):
        if isinstance(par, bool) or int(par) != float(par) or not 1 <= int(par) <= 16:
            raise ValueError('parallel: ganze Zahl von 1 bis 16')
        out['parallel'] = int(par)
    lt_in = data.get('languagetool') or {}
    lt = {}
    lang = str(lt_in.get('language') or '').strip()
    if lang:
        if not re.fullmatch(r'[a-zA-Z]{2,3}([-_][a-zA-Z]{2,8})?', lang):
            raise ValueError(f'languagetool.language: {lang!r} ist keine Sprachvariante wie de-AT')
        lt['language'] = lang
    for key in ('words', 'disabled_rules'):
        items = lt_in.get(key) or []
        if isinstance(items, str):
            items = items.splitlines()
        items = list(dict.fromkeys(str(x).strip() for x in items if str(x).strip()))
        if items:
            lt[key] = items
    if lt:
        out['languagetool'] = lt
    return out


def settings_set(base, data):
    """Block `analysis` in ghostwriter.yml ersetzen (Rest der Datei unverändert). → neuer Block (leer = entfernt)"""
    block = clean_settings(data)
    path = Path(base) / 'ghostwriter.yml'
    text = path.read_text(encoding='utf-8')
    new = yaml.safe_dump({'analysis': block}, allow_unicode=True, sort_keys=False, width=10**6) if block else ''
    m = re.search(r'(?ms)^analysis:.*?(?=^\S|\Z)', text)
    if m:
        text = text[:m.start()] + new + text[m.end():]
    elif new:
        text = text.rstrip('\n') + '\n' + new
    path.write_text(text, encoding='utf-8')
    return block


def pick_provider(s):
    """(anbieter, schlüssel) aus analysis.provider bzw. dem ersten Anbieter mit hinterlegtem Schlüssel."""
    names = [s['provider']] if s.get('provider') else list(PROVIDERS)
    for p in names:
        if p in PROVIDERS and os.environ.get(PROVIDERS[p]['secret']):
            return p, os.environ[PROVIDERS[p]['secret']]
    if os.environ.get('GHOSTWRITER_FAKE_LLM'):
        return names[0] if names[0] in PROVIDERS else 'anthropic', 'fake'
    wanted = ', '.join(PROVIDERS[p]['secret'] for p in names if p in PROVIDERS) or 'ANTHROPIC_API_KEY oder OPENAI_API_KEY'
    raise SystemExit(f'Kein Schlüssel für die Analyse: Secret {wanted} hinterlegen (docs/DIENSTE-NUTZEN.md, „API-Schlüssel als GitHub-Secret“)')


# ---------- 1. Vorbereiten ----------

MAX_BLOCK_CHARS = 12000


def text_parts(text, limit=MAX_BLOCK_CHARS):
    """Begrenzte, verlustfreie Teile; Absatz-/Satzgrenzen bevorzugen."""
    while len(text) > limit:
        cut = text.rfind('\n\n', limit // 2, limit)
        if cut < 0:
            candidates = list(re.finditer(r'[.!?]\s+', text[:limit]))
            cut = candidates[-1].end() if candidates and candidates[-1].end() >= limit // 2 else limit
        else:
            cut += 2
        yield text[:cut]
        text = text[cut:]
    if text:
        yield text


def blocks(base, config, scope=None, matter=True, split=True):
    """Ein Abschnitt je Block; überlange Abschnitte in begrenzte Teile zerlegen."""
    want = None if scope in (None, '', 'book', 'buch') else int(scope)
    units = []
    if want is None and matter:
        units.extend((i['id'], i['title'], i) for _, i in matter_items(config))
    for ci, ch in enumerate(config['structure']['chapters'], start=1):
        if want is not None and ci != want:
            continue
        units.extend((s['id'], f'{ci}.{si}', s) for si, s in enumerate(ch['sections'], start=1))
    for key, where, section in units:
        ms = section_file(base, section)[3].strip()
        if not ms or ms == 'Noch nicht begonnen.':
            continue
        parts = list(text_parts(ms)) if split else [ms]
        for n, part in enumerate(parts, 1):
            suffix = f'--part-{n:04d}' if len(parts) > 1 else ''
            yield key + suffix, f'Abschnitt {where}' + (f' (Teil {n}/{len(parts)})' if suffix else ''), {where: part}


def block_text(texts):
    return '\n\n'.join(f'### {k}\n\n{v}' for k, v in texts.items())


def fingerprint(texts):
    return hashlib.sha256(block_text(texts).encode('utf-8')).hexdigest()


def extraction_fingerprint(base, config, kind, texts, context=None):
    spec = KINDS[kind]
    s = settings(config)
    if context is None:
        context = spec['context'](base, config) if spec['context'] else ''
    if len(context) > MAX_BLOCK_CHARS:
        raise ValueError('Figurenkontext ist zu groß; vor der Analyse gezielt eingrenzen.')
    material = [fingerprint(texts), spec['system'], context, s.get('provider'), s.get('model')]
    return hashlib.sha256(json.dumps(material, ensure_ascii=False).encode()).hexdigest()


def cache_dir(base, kind):
    return Path(base) / 'analysis' / 'cache' / kind


def cached(base, kind, key, fp):
    p = cache_dir(base, kind) / f'{key}.json'
    if p.is_file():
        data = json.loads(p.read_text(encoding='utf-8'))
        if data.get('version') == 2 and data.get('fingerprint') == fp:
            return data
    return None


def plan(base, config, kind='characters', scope=None):
    s = settings(config)
    spec = KINDS[kind]
    rows, chars_new, results = [], 0, {}
    context = spec['context'](base, config) if spec['context'] else ''
    for key, title, texts in blocks(base, config, scope, spec['matter'], split=not spec.get('local')):
        fp = extraction_fingerprint(base, config, kind, texts, context)
        data = cached(base, kind, key, fp)
        hit = data is not None
        if hit:
            results[key] = data['items']
        n = len(block_text(texts))
        rows.append({'key': key, 'title': title, 'chars': n, 'cached': hit})
        if not hit:
            chars_new += n
    todo = [r for r in rows if not r['cached']]
    merge_in, merge_out = spec['merge_tokens']
    # A different scope may require a fresh merge even when all extractions are cached.
    merge_needed = bool(todo)
    if spec['merge'] and not todo and any(results.values()):
        previous = sorted((Path(base) / 'analysis' / kind).glob('run-[0-9][0-9][0-9].json'))
        previous = json.loads(previous[-1].read_text(encoding='utf-8')) if previous else {}
        ordered = {k: results[k] for k in ordered_results(config, results)}
        merge_model = s.get('merge_model') or PROVIDERS[s.get('provider') or 'anthropic']['merge_model']
        digest = hashlib.sha256(json.dumps([ordered, merge_model], sort_keys=True, ensure_ascii=False).encode()).hexdigest()
        merge_needed = previous.get('result_digest') != digest
    tin = int(chars_new / CHARS_PER_TOKEN) + PROMPT_TOKENS * len(todo) + (merge_in if merge_needed else 0)
    tout = spec['output_tokens'] * len(todo) + (merge_out if merge_needed else 0)
    if spec.get('local'):   # ohne KI
        tin = tout = 0
    cost = None
    if s.get('price_input_per_mtok') is not None and s.get('price_output_per_mtok') is not None:
        cost = round(tin / 1e6 * float(s['price_input_per_mtok']) + tout / 1e6 * float(s['price_output_per_mtok']), 2)
    return {'kind': kind, 'label': spec['label'], 'scope': scope or 'book', 'blocks': rows, 'todo': len(todo),
            'cached': len(rows) - len(todo), 'input_tokens': tin, 'output_tokens': tout, 'cost_estimate': cost,
            'estimate_note': ('Zusammenführen großer Ergebnislisten kann zusätzliche paarweise Aufrufe benötigen; keine Kostenobergrenze.'
                              if spec['merge'] else '')}


# ---------- 2. KI-Aufrufe ----------

def send_llm(req, adapter, core_plan=None):
    """Identischer Transport, optional ausschließlich Metadaten nach stderr."""
    capture = None
    if os.environ.get('GHOSTWRITER_PROMPT_PROFILE') == '1':
        try:
            from prompt_profiler import Capture
            capture = Capture(json.loads(req.data), adapter, core_plan=core_plan, transport_body=req.data)
        except Exception:
            print('Prompt-Profil konnte nicht vorbereitet werden.', file=sys.stderr)
    try:
        with urllib.request.urlopen(req, timeout=300) as response:
            data = json.loads(response.read())
    except Exception:
        if capture is not None:
            publish_profile(capture, None, succeeded=False)
        raise
    if capture is not None:
        publish_profile(capture, data)
    return data


def publish_profile(capture, data, *, succeeded=True):
    try:
        from prompt_profiler import emit
        emit(capture.finish(data, succeeded=succeeded))
    except Exception:
        # Profiling darf den Modelllauf nicht verändern oder Fehlertexte leaken.
        print('Prompt-Profil konnte nicht ausgegeben werden.', file=sys.stderr)


def call_llm(provider, key, model, system, user, kind='characters', step='extract'):
    """(antwort-text, input_tokens, output_tokens). GHOSTWRITER_FAKE_LLM: feste Antworten für Tests."""
    fake = os.environ.get('GHOSTWRITER_FAKE_LLM')
    if fake:
        data = json.loads(Path(fake).read_text(encoding='utf-8'))
        data = data if kind == 'characters' else (data.get(kind) or {})
        if step == 'merge':
            return json.dumps(data.get('merge') or {'groups': []}), 100, 20
        m = re.search(r'^BLOCK: (\S+)$', user, re.M)
        answer = (data.get('extract') or {}).get(m.group(1), {}) if m else data.get('answer', {})   # answer: ohne Kapitel
        return json.dumps(answer), len(user) // 4, 300
    core_plan = None
    if os.environ.get('GHOSTWRITER_PROMPT_PROFILE') == '1':
        try:
            from prompt_profiler import component
            # Der Benutzertext enthält bereits kombinierten Kontext.
            # Keine feinere Herkunft oder Regelpriorität erfinden.
            core_plan = [
                component(system, source='scripts/analyze.py:call_llm.system', kind='instruction',
                          layer='core', scope='task', activation='model_call', position=0),
                component(user, source='scripts/analyze.py:call_llm.user', kind='task_and_context',
                          layer='core', scope='task', activation='model_call', position=1)]
        except Exception:
            print('Prompt-Core-Profil konnte nicht vorbereitet werden.', file=sys.stderr)
    if provider == 'anthropic':
        req = urllib.request.Request('https://api.anthropic.com/v1/messages', method='POST', data=json.dumps({
            'model': model, 'max_tokens': 8000, 'system': system, 'messages': [{'role': 'user', 'content': user}]}).encode(),
            headers={'x-api-key': key, 'anthropic-version': '2023-06-01', 'content-type': 'application/json'})
        data = send_llm(req, 'anthropic-messages', core_plan)
        text = ''.join(b.get('text', '') for b in data.get('content') or [])
        u = data.get('usage') or {}
        return text, int(u.get('input_tokens') or 0), int(u.get('output_tokens') or 0)
    req = urllib.request.Request('https://api.openai.com/v1/chat/completions', method='POST', data=json.dumps({
        'model': model, 'response_format': {'type': 'json_object'},
        'messages': [{'role': 'system', 'content': system}, {'role': 'user', 'content': user}]}).encode(),
        headers={'authorization': f'Bearer {key}', 'content-type': 'application/json'})
    data = send_llm(req, 'openai-chat', core_plan)
    u = data.get('usage') or {}
    return data['choices'][0]['message']['content'], int(u.get('prompt_tokens') or 0), int(u.get('completion_tokens') or 0)


def parse_json(text):
    m = re.search(r'\{.*\}', text or '', re.S)
    try:
        return json.loads(m.group(0)) if m else {}
    except ValueError:
        return {}


# ---------- 3. Prüfung ohne KI ----------

def norm(s):
    s = (s or '').replace('„', '"').replace('“', '"').replace('”', '"').replace('‚', "'").replace('‘', "'").replace('’', "'")
    s = re.sub(r'[*_]', '', s)
    return re.sub(r'\s+', ' ', s).strip().casefold()


def check_quote(e, ntexts, only=None):
    """Geprüfte Fundstelle {field, where, quote} oder None. Das Zitat muss wörtlich im genannten Abschnitt stehen;
    fehlt der Abschnitt bzw. ist er unbekannt, zählt jeder Abschnitt des Blocks (bzw. die aus only)."""
    if not isinstance(e, dict):
        return None
    q = norm(e.get('quote'))
    where = str(e.get('where') or '')
    pool = {k: v for k, v in ntexts.items() if only is None or k in only}
    if len(q) < 3:
        return None
    if where in pool:
        hit = where if q in pool[where] else None
    elif where in ntexts:   # Abschnitt außerhalb von only
        hit = None
    else:
        hit = next((k for k, v in pool.items() if q in v), None)
    return {'field': e.get('field') or '', 'where': hit, 'quote': (e.get('quote') or '').strip()} if hit else None


def verify(items, texts):
    """Figuren: nur Angaben mit wörtlicher Fundstelle; → (geprüfte Figuren, Zahl verworfener Angaben)."""
    ntexts = {k: norm(v) for k, v in texts.items()}
    out, dropped = [], 0
    for it in items or []:
        name = (it.get('name') or '').strip()
        if not name:
            continue
        ok = []
        for e in it.get('evidence') or []:
            hit = check_quote(e, ntexts)
            if hit:
                hit['field'] = hit['field'] or 'name'
                ok.append(hit)
            else:
                dropped += 1
        if not ok:
            dropped += 1
            continue
        names = [name] + [a for a in it.get('aliases') or [] if a]
        fields = {e['field'] for e in ok}
        clean = {'name': name, 'aliases': [a for a in it.get('aliases') or [] if a and a != name],
                 'role': it.get('role') if it.get('role') in ('main', 'supporting', 'minor') else 'supporting',
                 'evidence': ok}
        for f in FIELDS:
            if it.get(f) and f in fields:
                clean[f] = it[f]
            elif it.get(f):
                dropped += 1
        if it.get('relations') and 'relation' in fields:
            clean['relations'] = [r for r in it['relations'] if r.get('to') and r.get('kind')]
        secs = []
        for k in list(it.get('sections') or []) + [e['where'] for e in ok]:
            k = str(k)
            if k in ntexts and k not in secs and any(norm(n) in ntexts[k] for n in names):
                secs.append(k)
        clean['sections'] = secs
        out.append(clean)
    return out, dropped


def verify_summaries(answer, texts):
    """Kurzbeschreibung und Ziel: je Abschnitt nur mit Fundstelle in diesem Abschnitt, fürs Kapitel mit Fundstelle in
    einem seiner Abschnitte. Ein Feld ohne eigene Fundstelle zählt, wenn der Eintrag mindestens eine gültige hat
    (ein Ziel lässt sich selten wörtlich belegen). → ({sections: [...], chapter: {...}|None}, verworfen)"""
    ntexts = {k: norm(v) for k, v in texts.items()}
    dropped, sections, seen = 0, [], set()
    for it in (answer or {}).get('sections') or []:
        where = str(it.get('where') or '')
        if where not in ntexts or where in seen:
            dropped += 1
            continue
        ok = [h for h in (check_quote(e, ntexts, only={where}) for e in it.get('evidence') or []) if h]
        dropped += len(it.get('evidence') or []) - len(ok)
        vals = {f: (it.get(f) or '').strip() for f in ('short', 'goal')}
        if not ok or not any(vals.values()):
            dropped += 1
            continue
        seen.add(where)
        sections.append(dict({f: v for f, v in vals.items() if v}, where=where, evidence=ok[:3]))
    ch = (answer or {}).get('chapter') or {}
    chapter = None
    ok = [h for h in (check_quote(e, ntexts) for e in ch.get('evidence') or []) if h]
    vals = {f: (ch.get(f) or '').strip() for f in ('short', 'goal')}
    if ok and any(vals.values()):
        chapter = dict({f: v for f, v in vals.items() if v}, evidence=ok[:3])
    elif any(vals.values()):
        dropped += 1
    return {'sections': sections, 'chapter': chapter}, dropped


# ---------- 4. Zusammenführen ----------

def merge(found, groups=()):
    """Figuren aller Blöcke zusammenführen: gleiche Namen und andere Namen, dazu groups (Listen von Namen) aus der KI.
    → (figuren, widersprüche)"""
    parent = list(range(len(found)))
    def root(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i
    index = {}
    for i, it in enumerate(found):
        for n in [it['name']] + it.get('aliases', []):
            k = norm(n)
            if k in index:
                parent[root(i)] = root(index[k])
            else:
                index[k] = i
    for g in groups or []:
        hits = [index[norm(n)] for n in g if norm(n) in index]
        for h in hits[1:]:
            parent[root(h)] = root(hits[0])
    clusters = {}
    for i in range(len(found)):
        clusters.setdefault(root(i), []).append(found[i])
    out, conflicts = [], []
    for members in clusters.values():
        main = max(members, key=lambda m: (len(m.get('evidence', [])), len(m['name'])))
        names = []
        for m in members:
            for n in [m['name']] + m.get('aliases', []):
                if n not in names:
                    names.append(n)
        it = {'name': main['name'], 'aliases': [n for n in names if n != main['name']],
              'role': min((m['role'] for m in members), key=['main', 'supporting', 'minor'].index),
              'sections': [], 'evidence': []}
        for f in FIELDS:
            vals = []
            for m in members:
                v = m.get(f)
                if v and v not in vals:
                    vals.append(v)
            if vals:
                it[f] = vals[0] if f != 'traits' else sorted({t for v in vals for t in v}, key=str.casefold)
                if f in ('age', 'appearance', 'voice') and len(vals) > 1:
                    conflicts.append({'name': it['name'], 'field': f, 'values': vals})
        rels = []
        for m in members:
            for r in m.get('relations') or []:
                if r not in rels:
                    rels.append(r)
        if rels:
            it['relations'] = rels
        for m in members:
            it['sections'] += [s for s in m['sections'] if s not in it['sections']]
            it['evidence'] += m['evidence']
        it['evidence'] = it['evidence'][:6]
        out.append(it)
    out.sort(key=lambda x: (['main', 'supporting', 'minor'].index(x['role']), -len(x['sections']), x['name'].casefold()))
    return out, conflicts


# ---------- Arten ----------

def characters_context(base, config):
    known = '\n'.join(f'- {c["name"]}' + (': ' + character_file(base, c)[0]['short'] if character_file(base, c)[0].get('short') else '')
                      for c in character_items(config)) or '- (keine)'
    return f'Bekannte Figuren:\n{known}'


def characters_combine(base, config, results, todo, prev, ask):
    """Figuren: zusammenführen, Spitznamen über merge_model. → (vorschläge, md-zeilen)"""
    found = [it for key in results for it in results[key]]
    groups = ((prev or {}).get('groups') or []) if not todo else []   # nichts Neues gelesen: Zuordnung vom letzten Lauf
    if len(found) > 1 and todo:   # Spitznamen: ein Aufruf mit dem stärkeren Modell
        listing = '\n'.join(f'- {it["name"]}' + (f' (auch: {", ".join(it["aliases"])})' if it.get('aliases') else '')
                            + (f': {it["short"]}' if it.get('short') else '') for it in found)
        groups = [g for g in parse_json(ask(MERGE_SYSTEM, listing)).get('groups') or [] if isinstance(g, list) and len(g) > 1]
    items, conflicts = merge(found, groups)
    body = ['## Vorschläge', '']
    body += [f'- **{it["name"]}**' + (f' (auch: {", ".join(it["aliases"])})' if it['aliases'] else '') +
             (f': {it["short"]}' if it.get('short') else '') + (f' – {", ".join(it["sections"])}' if it['sections'] else '')
             for it in items] or ['*keine*']
    body += ['', '## Widersprüche', '']
    body += [f'- {c["name"]}, {c["field"]}: ' + ' / '.join(str(v) for v in c['values']) for c in conflicts] or ['*keine*']
    return {'items': items, 'conflicts': conflicts, 'groups': groups}, body


def summaries_combine(base, config, results, todo, prev, ask):
    """Kurzbeschreibungen: in Buchreihenfolge, je Kapitel erst das Kapitel, dann seine Abschnitte. → (vorschläge, md)"""
    items, body = [], ['## Vorschläge', '']
    for ci, ch in enumerate(config['structure']['chapters'], start=1):
        entries = []
        for si, s in enumerate(ch['sections'], 1):
            found = [e for k, r in results.items() if k == s['id'] or k.startswith(s['id'] + '--part-')
                     for e in r.get('sections') or [] if e['where'] == f'{ci}.{si}']
            if not found:
                continue
            entry = {f: ' '.join(dict.fromkeys(e[f] for e in found if e.get(f))) for f in ('short', 'goal')}
            entry['evidence'] = [v for e in found for v in e['evidence']][:3]
            entries.append(dict(entry, level='section', target=s['id'], number=f'{ci}.{si}', title=s['title']))
        if entries:
            # Transparente Zusammenstellung geprüfter Abschnittsergebnisse, kein erneuter Volltextaufruf.
            chapter = {f: ' '.join(e[f] for e in entries if e.get(f)) for f in ('short', 'goal')}
            chapter['evidence'] = [v for e in entries for v in e['evidence']][:3]
            items.append(dict(chapter, level='chapter', target=ch['id'], number=str(ci), title=ch['title']))
            items.extend(entries)
    for it in items:
        label = f'Kapitel {it["number"]}' if it['level'] == 'chapter' else it['number']
        body += [f'- **{label} {it["title"]}**' + (f' – Ziel: {it["goal"]}' if it.get('goal') else '')
                 + (f' – Kurz: {it["short"]}' if it.get('short') else '')]
    if not items:
        body.append('*keine*')
    return {'items': items}, body


# Stilprofil (#124): Angaben je Abschnitt, Zahlen ohne KI

STYLE_FIELDS = ('perspective', 'tense', 'address', 'register', 'tone', 'features')
STYLE_LISTS = ('tone', 'features')   # mehrere Werte, mit Komma


def text_stats(texts):
    """Zahlen ohne KI: Wörter, Sätze, Wörter in wörtlicher Rede."""
    words = sentences = dialogue = 0
    for t in texts.values():
        t = re.sub(r'\[[^\]]*\]', ' ', t)   # Marker
        words += len(re.findall(r"[^\W_]+(?:[-’'][^\W_]+)*", t))
        sentences += len(re.findall(r'[^.!?…]*[^\W_][^.!?…]*[.!?…]+', t)) or 0
        for q in re.findall(r'„([^“”]*)[“”]|»([^«]*)«|"([^"]*)"', t):
            dialogue += len(re.findall(r"[^\W_]+", ''.join(q)))
    return {'words': words, 'sentences': max(sentences, 1), 'dialogue_words': dialogue}


def as_list(v):
    if isinstance(v, list):
        return [str(x).strip() for x in v if str(x).strip()]
    return [x.strip() for x in str(v or '').split(',') if x.strip()]


def verify_style(answer, texts):
    """Stil eines Blocks: nur Angaben mit eigener Fundstelle; dazu die Zahlen ohne KI. → (angaben, verworfen)"""
    ntexts = {k: norm(v) for k, v in texts.items()}
    answer = answer or {}
    ok, dropped = [], 0
    for e in answer.get('evidence') or []:
        h = check_quote(e, ntexts)
        if h and h['field'] in STYLE_FIELDS:
            ok.append(h)
        else:
            dropped += 1
    have = {e['field'] for e in ok}
    out = {'stats': text_stats(texts), 'evidence': ok}
    for f in STYLE_FIELDS:
        v = as_list(answer.get(f)) if f in STYLE_LISTS else str(answer.get(f) or '').strip()
        if v and f in have:
            out[f] = v
        elif v:
            dropped += 1
    return out, dropped


def block_labels(config):
    labels = {i['id']: i['title'] for _, i in matter_items(config)}
    for ci, ch in enumerate(config['structure']['chapters'], start=1):
        labels[ch['id']] = f'Kapitel {ci}'
        for si, s in enumerate(ch['sections'], 1):
            labels[s['id']] = f'Abschnitt {ci}.{si}'
    return labels


def ordered_results(config, results):
    return [k for key in block_labels(config) for k in sorted(results)
            if k == key or k.startswith(key + '--part-')]


def style_combine(base, config, results, todo, prev, ask):
    """Stilprofil fürs ganze Buch: je Angabe der häufigste Wert (gewichtet nach Wörtern), abweichende Abschnitte als
    Varianten; bei Ton und Stilmitteln die häufigsten Werte. Zahlen über alle Blöcke. → (vorschläge, md)"""
    labels = block_labels(config)
    order = ordered_results(config, results)
    total = {'words': 0, 'sentences': 0, 'dialogue_words': 0}
    for k in order:
        for x in total:
            total[x] += (results[k].get('stats') or {}).get(x, 0)
    items = []
    for f in STYLE_FIELDS:
        tally, where, ev = {}, {}, {}
        for k in order:
            r = results[k]
            vals = r.get(f) if f in STYLE_LISTS else ([r[f]] if r.get(f) else [])
            w = (r.get('stats') or {}).get('words', 1) or 1
            for v in vals or []:
                key = v.casefold()
                tally[key] = tally.get(key, 0) + w
                where.setdefault(key, (v, []))[1].append(labels.get(k.split('--part-')[0], k))
                ev.setdefault(key, []).extend(e for e in r.get('evidence') or [] if e['field'] == f)
        if not tally:
            continue
        ranked = sorted(tally, key=lambda x: -tally[x])
        if f in STYLE_LISTS:
            top = ranked[:4 if f == 'tone' else 6]
            items.append({'field': f, 'value': ', '.join(where[x][0] for x in top), 'variants': [],
                          'evidence': [e for x in top for e in ev[x][:1]][:3]})
        else:
            items.append({'field': f, 'value': where[ranked[0]][0],
                          'variants': [{'value': where[x][0], 'where': where[x][1]} for x in ranked[1:]],
                          'evidence': ev[ranked[0]][:2]})
    stats = {'words': total['words'],
             'sentence_length_avg': round(total['words'] / max(total['sentences'], 1), 1) if total['words'] else None,
             'dialogue_share': round(total['dialogue_words'] / total['words'], 2) if total['words'] else None}
    body = ['## Vorschläge', '']
    body += [f'- **{STYLE_DE[it["field"]]}:** {it["value"]}' + (' (abweichend: ' + '; '.join(
        f'{v["value"]} in {", ".join(v["where"])}' for v in it['variants']) + ')' if it['variants'] else '') for it in items] or ['*keine*']
    body += ['', '## Zahlen (ohne KI)', '', f'- Wörter: {stats["words"]}',
             f'- Wörter je Satz im Mittel: {stats["sentence_length_avg"]}', f'- Anteil wörtlicher Rede: {stats["dialogue_share"]}']
    return {'items': items, 'stats': stats}, body


STYLE_DE = {'perspective': 'Erzählperspektive', 'tense': 'Zeitform', 'address': 'Anrede', 'register': 'Sprachebene',
            'tone': 'Ton', 'features': 'Stilmittel'}


# Schauplätze (#124): wie Figuren, mit Art und Beschreibung

PLACE_FIELDS = ('kind', 'short')


def verify_places(answer, texts):
    """Schauplätze: nur Angaben mit wörtlicher Fundstelle; Abschnitte nur, wo Name oder anderer Name vorkommt.
    → (orte, verworfen)"""
    ntexts = {k: norm(v) for k, v in texts.items()}
    out, dropped = [], 0
    for it in (answer or {}).get('items') or []:
        name = ' '.join(str(it.get('name') or '').split())
        if not name:
            continue
        ok = []
        for e in it.get('evidence') or []:
            h = check_quote(e, ntexts)
            if h:
                h['field'] = h['field'] if h['field'] in PLACE_FIELDS else 'name'
                ok.append(h)
            else:
                dropped += 1
        names = [name] + [a for a in it.get('aliases') or [] if a and a != name]
        if not ok or not any(norm(n) in ntexts[e['where']] for e in ok for n in names):
            dropped += 1
            continue
        clean = {'name': name, 'aliases': names[1:], 'evidence': ok[:4]}
        fields = {e['field'] for e in ok}
        for f in PLACE_FIELDS:
            v = ' '.join(str(it.get(f) or '').split())
            if v and (f in fields or f == 'kind'):   # die Art ergibt sich aus der Fundstelle des Namens
                clean[f] = v
            elif v:
                dropped += 1
        secs = []
        for k in [str(x) for x in it.get('sections') or []] + [e['where'] for e in ok]:
            if k in ntexts and k not in secs and any(norm(n) in ntexts[k] for n in names):
                secs.append(k)
        clean['sections'] = secs
        out.append(clean)
    return out, dropped


def places_combine(base, config, results, todo, prev, ask):
    """Schauplätze aller Blöcke nach Namen zusammen, dazu groups aus merge_model (andere Bezeichnungen).
    → (vorschläge, md)"""
    found = [dict(it, role='supporting') for k in results for it in results[k]]
    groups = ((prev or {}).get('groups') or []) if not todo else []
    if len(found) > 1 and todo:
        listing = '\n'.join(f'- {it["name"]}' + (f' (auch: {", ".join(it["aliases"])})' if it.get('aliases') else '')
                            + (f': {it["short"]}' if it.get('short') else '') for it in found)
        groups = [g for g in parse_json(ask(PLACES_MERGE_SYSTEM, listing)).get('groups') or [] if isinstance(g, list) and len(g) > 1]
    merged, _ = merge(found, groups)
    items = []
    for m in merged:
        members = [it for it in found if norm(it['name']) in {norm(x) for x in [m['name']] + m['aliases']}]
        out = {'name': m['name'], 'aliases': m['aliases'], 'sections': m['sections'], 'evidence': m['evidence']}
        for f in PLACE_FIELDS:
            v = next((x.get(f) for x in members if x.get(f)), '')
            if v:
                out[f] = v
        items.append(out)
    items.sort(key=lambda x: (-len(x['sections']), x['name'].casefold()))
    body = ['## Vorschläge', '']
    body += [f'- **{it["name"]}**' + (f' ({it["kind"]})' if it.get('kind') else '') + (f': {it["short"]}' if it.get('short') else '')
             + (f' – {", ".join(it["sections"])}' if it['sections'] else '') for it in items] or ['*keine*']
    return {'items': items, 'groups': groups}, body


# Zeitleiste (#124): Ereignisse je Abschnitt, Auffälligkeiten über das ganze Buch

def verify_timeline(answer, texts):
    """Ereignisse: nur mit wörtlicher Fundstelle im genannten Abschnitt, in der Reihenfolge der Abschnitte.
    → (ereignisse, verworfen)"""
    ntexts = {k: norm(v) for k, v in texts.items()}
    order = list(texts)
    out, dropped = [], 0
    for ev in (answer or {}).get('events') or []:
        where = str(ev.get('where') or '')
        what = ' '.join(str(ev.get('what') or '').split())
        if where not in ntexts or not what:
            dropped += 1
            continue
        ok = [h for h in (check_quote(e, ntexts, only={where}) for e in ev.get('evidence') or []) if h]
        if not ok:
            dropped += 1
            continue
        out.append({'where': where, 'when': ' '.join(str(ev.get('when') or '').split()), 'what': what, 'evidence': ok[:2]})
    out.sort(key=lambda e: order.index(e['where']))   # stabil: Reihenfolge im Abschnitt bleibt
    return out, dropped


def timeline_combine(base, config, results, todo, prev, ask):
    """Zeitleiste: Ereignisse in Buchreihenfolge (Nummer 1 …), dazu Auffälligkeiten über merge_model; jede
    Auffälligkeit verweist nur auf Ereignisse mit geprüfter Fundstelle. → (vorschläge, md)"""
    labels = block_labels(config)
    events = []
    for k in ordered_results(config, results):
        for e in results[k]:
            events.append(dict(e, n=len(events) + 1))
    issues = []
    if len(events) > 1 and todo:
        listing = '\n'.join(f'{e["n"]}. [{e["where"]}] {e["when"] or "(ohne Zeitangabe)"}: {e["what"]}' for e in events)
        raw = parse_json(ask(TIMELINE_MERGE_SYSTEM, listing)).get('issues') or []
        known = {e['n'] for e in events}
        for x in raw:
            ids = [int(i) for i in x.get('events') or [] if str(i).isdigit() and int(i) in known]
            text = ' '.join(str(x.get('text') or '').split())
            if ids and text:
                issues.append({'kind': x.get('kind') if x.get('kind') in ('jump', 'contradiction', 'unclear') else 'unclear',
                               'events': sorted(set(ids)), 'text': text})
    elif not todo and prev:
        issues = prev.get('issues') or []
    body = ['## Ereignisse', '']
    body += [f'{e["n"]}. {e["where"]} – {e["when"] or "ohne Zeitangabe"}: {e["what"]}' for e in events] or ['*keine*']
    body += ['', '## Auffälligkeiten', '']
    body += [f'- {TIMELINE_KIND_DE[i["kind"]]} (Ereignisse {", ".join(map(str, i["events"]))}): {i["text"]}' for i in issues] or ['*keine*']
    return {'items': events, 'issues': issues}, body


TIMELINE_KIND_DE = {'jump': 'Zeitsprung', 'contradiction': 'Widerspruch', 'unclear': 'unklar'}


# Widersprüche (#124): Tatsachen je Abschnitt mit Fundstelle, Widersprüche über das ganze Buch

def verify_continuity(answer, texts):
    """Tatsachen: nur mit wörtlicher Fundstelle im genannten Abschnitt. → (tatsachen, verworfen)"""
    ntexts = {k: norm(v) for k, v in texts.items()}
    order = list(texts)
    out, dropped = [], 0
    for f in (answer or {}).get('facts') or []:
        about, fact = (' '.join(str(f.get(k) or '').split()) for k in ('about', 'fact'))
        h = check_quote({'where': f.get('where'), 'quote': f.get('quote')}, ntexts, only={str(f.get('where') or '')}) \
            if str(f.get('where') or '') in ntexts else None
        if not h or not fact:
            dropped += 1
            continue
        out.append({'about': about, 'fact': fact, 'where': h['where'], 'quote': h['quote']})
    out.sort(key=lambda x: order.index(x['where']))
    return out, dropped


def continuity_combine(base, config, results, todo, prev, ask):
    """Widersprüche: alle Tatsachen in Buchreihenfolge nummeriert an merge_model; nur Widersprüche zwischen
    mindestens zwei geprüften Tatsachen bleiben. → (vorschläge, md)"""
    labels = block_labels(config)
    facts = []
    for k in ordered_results(config, results):
        for f in results[k]:
            facts.append(dict(f, n=len(facts) + 1))
    items = []
    if len(facts) > 1 and todo:
        listing = '\n'.join(f'{f["n"]}. [{f["where"]}] {f["about"]}: {f["fact"]}' for f in facts)
        raw = parse_json(ask(CONTINUITY_MERGE_SYSTEM, listing)).get('conflicts') or []
        by_n = {f['n']: f for f in facts}
        for c in raw:
            ns = sorted({int(i) for i in c.get('facts') or [] if str(i).isdigit() and int(i) in by_n})
            text = ' '.join(str(c.get('text') or '').split())
            if len(ns) >= 2 and text:
                items.append({'text': text, 'facts': [by_n[n] for n in ns]})
    elif not todo and prev:
        items = prev.get('items') or []
    body = ['## Widersprüche', '']
    for it in items:
        body.append(f'- {it["text"]}')
        body += [f'  - {f["where"]}: „{f["quote"]}“' for f in it['facts']]
    if not items:
        body.append('*keine*')
    body += ['', f'Geprüfte Tatsachen: {len(facts)}.']
    return {'items': items, 'facts': len(facts)}, body


# Sprache (#124): Auffälligkeiten je Abschnitt, ganz ohne KI

LONG_SENTENCE = 40          # Wörter
REPEAT_WINDOW = 80          # Wörter
REPEAT_MIN = 3
HINTS_PER_SECTION = 12
FILLERS = ('eigentlich', 'irgendwie', 'halt', 'eben', 'wirklich', 'einfach', 'quasi', 'sozusagen', 'gewissermaßen',
           'ziemlich', 'durchaus', 'natürlich', 'total', 'echt')
STOPWORDS = set("""aber alle allem allen aller alles also andere anderen anderer anderes auch auf aus außer bei beim
bevor bin bis bist bleibt damit dann darauf darum dass dein deine deinem deinen deiner dem den denen denn der deren
des deshalb dessen die dies diese diesem diesen dieser dieses doch dort durch eine einem einen einer eines einige
einmal etwas euch euer eure für gegen gerade gewesen habe haben hast hatte hatten hier hinter ihre ihrem ihren ihrer
immer indem jede jedem jeden jeder jedes jetzt kann kannst keine keinem keinen keiner können könnte machen manche
manchmal mehr meine meinem meinen meiner mich mir mit muss musste nach nicht nichts noch nun oder ohne schon sehr
sein seine seinem seinen seiner seit selbst sich sie sind soll sollte sondern sowie über unter viel viele vom von vor
während waren warst was weil weiter welche welchem welchen welcher wenn werden wieder will wird wirst wollen würde
würden zum zur zwar zwischen dabei davon dazu daher wurde wurden worden sodass einfach""".split())


def sentences(text):
    t = re.sub(r'\[[^\]]*\]', ' ', text)
    t = re.sub(r'(?m)^\s*(?:#+|[-*>]|\d+\.)\s+', '', t)
    parts = re.split(r'(?<=[.!?…])["“”»«]?\s+(?=[„"»«(]?[A-ZÄÖÜ0-9])|\n\s*\n', t)
    return [' '.join(p.split()) for p in parts if re.search(r'[^\W\d_]', p)]


def words_of(text):
    return re.findall(r"[^\W\d_]+(?:[-’'][^\W\d_]+)*", text)


def short_quote(sentence, n=14):
    w = sentence.split()
    return ' '.join(w[:n])


def check_language(texts, languagetool=None):
    """Sprachliche Auffälligkeiten je Abschnitt ohne KI: lange Sätze, Wortwiederholungen auf engem Raum, gleiche
    Satzanfänge hintereinander, viele Füllwörter; mit `languagetool` (#280) zuerst Rechtschreibung, Grammatik,
    Zeichensetzung und Typografie. Jede Fundstelle stammt wörtlich aus dem Text. → (hinweise, 0)"""
    out = []
    for where, text in texts.items():
        if languagetool:
            lt = languagetool_hints(text, lt_check(languagetool['url'], languagetool['language'], lt_plain(text),
                                                   languagetool['disabled_rules']), languagetool['words'])
            out.extend(dict(h, where=where) for h in lt[:LT_HINTS_PER_SECTION])
        found = []
        sents = sentences(text)
        for snt in sents:
            n = len(words_of(snt))
            if n > LONG_SENTENCE:
                found.append({'kind': 'long_sentence', 'text': f'Satz mit {n} Wörtern', 'quote': short_quote(snt)})
        run = 1
        for i in range(1, len(sents) + 1):
            a = words_of(sents[i - 1])[:1]
            b = words_of(sents[i])[:1] if i < len(sents) else []
            if a and b and a[0].casefold() == b[0].casefold():
                run += 1
                continue
            if run >= 3 and a:
                found.append({'kind': 'same_start', 'text': f'{run} Sätze hintereinander beginnen mit „{a[0]}“',
                              'quote': short_quote(sents[i - run])})
            run = 1
        ws = words_of(text)
        seen = set()
        for i, w in enumerate(ws):
            k = w.casefold()
            if len(k) < 5 or k in STOPWORDS or k in seen:
                continue
            hits = [j for j in range(i, min(len(ws), i + REPEAT_WINDOW)) if ws[j].casefold() == k]
            if len(hits) >= REPEAT_MIN:
                seen.add(k)
                snt = next((x for x in sents if re.search(rf'(?<![^\W\d_]){re.escape(w)}(?![^\W\d_])', x)), w)
                found.append({'kind': 'repetition', 'text': f'„{w}“ {len(hits)}× innerhalb von {REPEAT_WINDOW} Wörtern',
                              'quote': short_quote(snt) if w in short_quote(snt) else w})
        fill = {}
        for w in ws:
            if w.casefold() in FILLERS:
                fill[w.casefold()] = fill.get(w.casefold(), 0) + 1
        nf = sum(fill.values())
        if nf >= 5 and ws and nf / len(ws) > 0.01:
            top = sorted(fill.items(), key=lambda x: -x[1])[:4]
            first = next(w for w in ws if w.casefold() == top[0][0])
            found.append({'kind': 'filler', 'text': 'Füllwörter: ' + ', '.join(f'{w} ({n})' for w, n in top), 'quote': first})
        for h in found[:HINTS_PER_SECTION]:
            out.append(dict(h, where=where))
    return out, 0


LANGUAGE_DE = {'long_sentence': 'Langer Satz', 'repetition': 'Wortwiederholung', 'same_start': 'Gleiche Satzanfänge',
               'filler': 'Füllwörter', 'spelling': 'Rechtschreibung', 'grammar': 'Grammatik',
               'punctuation': 'Zeichensetzung', 'typography': 'Typografie'}


# Rechtschreibung und Grammatik mit LanguageTool (#280): ein lokaler LanguageTool-Server (in der Action „Analyse im
# Hintergrund“ im Runner gestartet), ohne KI, ohne Schlüssel und ohne Kosten. Nur aktiv, wenn LANGUAGETOOL_URL
# gesetzt ist; sonst bleibt die Analyse „Sprache“ wie bisher. Kategorien, die nicht hierher gehören (Stil,
# Redundanz, Umgangssprache …), werden nicht gemeldet: Stil prüfen die eigenen Regeln oben bzw. die Erzählstimme.

LT_ENV = 'LANGUAGETOOL_URL'
LT_HINTS_PER_SECTION = 15
LT_TIMEOUT = 180
LT_CATEGORIES = {'TYPOS': 'spelling', 'CASING': 'spelling', 'COMPOUNDING': 'spelling', 'GRAMMAR': 'grammar',
                 'CONFUSED_WORDS': 'grammar', 'PUNCTUATION': 'punctuation', 'TYPOGRAPHY': 'typography'}
LT_DEFAULT_VARIANT = {'de': 'de-DE', 'en': 'en-US'}


def lt_language(config):
    """Sprachcode für LanguageTool: analysis.languagetool.language, sonst project.language (de → de-DE)."""
    lt = settings(config).get('languagetool') or {}
    code = str(lt.get('language') or ((config or {}).get('project') or {}).get('language') or 'de').strip()
    head, _, tail = code.replace('_', '-').partition('-')
    return f'{head.lower()}-{tail.upper()}' if tail else LT_DEFAULT_VARIANT.get(head.lower(), head.lower())


def lt_words(base, config):
    """Eigene Wörter des Buchs, die nie als Tippfehler gelten: Figurennamen (und ihre Teile), Schauplätze samt
    anderen Bezeichnungen aus story/places.yml und analysis.languagetool.words."""
    names = [c.get('name') or '' for c in (config or {}).get('characters') or []]
    path = story_file(base, 'places')
    if path.is_file():
        for pl in (yaml.safe_load(path.read_text(encoding='utf-8')) or {}).get('places') or []:
            names += [pl.get('name') or ''] + list(pl.get('aliases') or [])
    names += list((settings(config).get('languagetool') or {}).get('words') or [])
    out = set()
    for n in names:
        n = ' '.join(str(n).split())
        if n:
            out.add(n)
            out.update(w for w in words_of(n) if len(w) > 1)
    return sorted(out, key=str.casefold)


def languagetool_options(base, config):
    """Einstellungen der LanguageTool-Prüfung oder None, wenn kein Server angegeben ist (LANGUAGETOOL_URL)."""
    url = (os.environ.get(LT_ENV) or '').strip()
    if not url:
        return None
    lt = settings(config).get('languagetool') or {}
    return {'url': url, 'language': lt_language(config), 'disabled_rules': sorted(lt.get('disabled_rules') or []),
            'words': lt_words(base, config)}


def language_context(base, config):
    """Fingerabdruck-Material der Analyse „Sprache“: ohne LanguageTool leer (wie bisher), mit LanguageTool Sprache,
    abgeschaltete Regeln und eigene Wörter, damit ein Lauf mit anderen Einstellungen nicht den Zwischenspeicher nutzt."""
    opts = languagetool_options(base, config)
    if not opts:
        return ''
    return 'languagetool:' + json.dumps({k: opts[k] for k in ('language', 'disabled_rules', 'words')},
                                        ensure_ascii=False, sort_keys=True)


def lt_plain(text):
    """Text für LanguageTool: Marker, Bild- und Linkziele, Überschriften- und Listenzeichen sowie Hervorhebungen durch
    gleich viele Leerzeichen ersetzt; die Stellen (offset) passen damit weiter zum Originaltext."""
    blank = lambda m: re.sub(r'\S', ' ', m.group())
    t = re.sub(r'!?\[[^\]\n]*\]\([^)\n]*\)', blank, text)
    t = re.sub(r'\[[^\]]*\]', blank, t)
    t = re.sub(r'(?m)^[ \t]*(?:#+|[-*>]|\d+\.)[ \t]+', blank, t)
    return re.sub(r'[*`]+', blank, t)


def lt_check(url, language, text, disabled_rules=()):
    """Antwort des LanguageTool-Servers (POST /v2/check) → Liste der Treffer (matches)."""
    data = {'text': text, 'language': language}
    if disabled_rules:
        data['disabledRules'] = ','.join(disabled_rules)
    req = urllib.request.Request(url.rstrip('/') + '/v2/check', data=urllib.parse.urlencode(data).encode('utf-8'),
                                 headers={'Accept': 'application/json'}, method='POST')
    try:
        with urllib.request.urlopen(req, timeout=LT_TIMEOUT) as r:
            return json.loads(r.read().decode('utf-8')).get('matches') or []
    except (OSError, ValueError) as e:
        raise RuntimeError(f'LanguageTool unter {url} antwortet nicht ({e}). Ohne LanguageTool: {LT_ENV} leer lassen.') from e


def languagetool_hints(text, matches, words=()):
    """Treffer von LanguageTool → Hinweise {kind, text, quote}. Eigene Wörter (Namen, Orte) gelten nicht als
    Tippfehler, gleiche Fehler (Regel und Wort) nur einmal, Fundstelle wörtlich aus dem Text."""
    known = {w.casefold() for w in words}
    out, seen = [], set()
    for m in matches:
        rule = m.get('rule') or {}
        kind = LT_CATEGORIES.get((rule.get('category') or {}).get('id', ''))
        off, n = int(m.get('offset') or 0), int(m.get('length') or 0)
        bad = text[off:off + n]
        if not kind or not bad.strip() or off < 0 or off + n > len(text):
            continue
        key = bad.strip().casefold()
        if kind == 'spelling' and (key in known or (key.endswith('s') and key[:-1] in known)
                                   or (key.endswith("'s") and key[:-2] in known)):
            continue
        if (rule.get('id'), key) in seen:
            continue
        seen.add((rule.get('id'), key))
        msg = ' '.join((m.get('shortMessage') or m.get('message') or LANGUAGE_DE[kind]).split()).rstrip('.')
        reps = [r.get('value') for r in m.get('replacements') or [] if (r.get('value') or '').strip()][:3]
        info = f'{msg}: „{" ".join(bad.split())}“' + (' → ' + ' / '.join(f'„{r}“' for r in reps) if reps else '')
        left = re.search(r'(?:\S+\s+){0,4}\S*$', text[:off]).group()
        right = re.match(r'\S*(?:\s+\S+){0,4}', text[off + n:]).group()
        out.append({'kind': kind, 'text': info, 'quote': ' '.join((left + bad + right).split())})
    return out


def language_combine(base, config, results, todo, prev, ask):
    """Sprache: Hinweise in Buchreihenfolge. → (vorschläge, md)"""
    labels = block_labels(config)
    items = [h for k in ordered_results(config, results) for h in results[k]]
    lt = languagetool_options(base, config)
    body = ['## Hinweise (ohne KI)', '',
            (f'Rechtschreibung und Grammatik: LanguageTool ({lt["language"]}), {len(lt["words"])} eigene Wörter.'
             if lt else 'Rechtschreibung und Grammatik: nicht geprüft (kein LanguageTool-Server).'), '']
    body += [f'- {h["where"]}: {LANGUAGE_DE[h["kind"]]} – {h["text"]} („{h["quote"]}“)' for h in items] or ['*keine*']
    return {'items': items}, body


# Je Art: label (für Texte), offer (Hinweis in der Übersicht), icon (Tabler-Symbol), system (Auftrag je Block),
# context (zusätzlicher Text vor dem Abschnitt), verify, combine, matter (Vor- und Nachspann lesen), output_tokens
# (Schätzung je Block), merge_tokens (Schätzung Zusammenführen), merge (Zusammenführen mit merge_model).
KINDS = {
    'characters': {'label': 'Figuren', 'offer': 'Figurenvorschläge', 'icon': 'user-search', 'system': EXTRACT_SYSTEM,
                   'context': characters_context, 'verify': lambda answer, texts: verify((answer or {}).get('items'), texts),
                   'combine': characters_combine, 'matter': True, 'output_tokens': 1500, 'merge_tokens': (2000, 500),
                   'merge': True},
    'summaries': {'label': 'Kurzbeschreibungen', 'offer': 'Kurzbeschreibungen und Ziele', 'icon': 'file-description',
                  'system': SUMMARIES_SYSTEM, 'context': None, 'verify': verify_summaries, 'combine': summaries_combine,
                  'matter': False, 'output_tokens': 1200, 'merge_tokens': (0, 0), 'merge': False},
    'style': {'label': 'Stilprofil', 'offer': 'Stilprofil', 'icon': 'feather', 'system': STYLE_SYSTEM, 'context': None,
              'verify': verify_style, 'combine': style_combine, 'matter': True, 'output_tokens': 500,
              'merge_tokens': (0, 0), 'merge': False},
    'places': {'label': 'Schauplätze', 'offer': 'Schauplätze', 'icon': 'map-pin', 'system': PLACES_SYSTEM, 'context': None,
               'verify': verify_places, 'combine': places_combine, 'matter': True, 'output_tokens': 1000,
               'merge_tokens': (1500, 300), 'merge': True},
    'timeline': {'label': 'Zeitleiste', 'offer': 'Zeitleiste', 'icon': 'timeline', 'system': TIMELINE_SYSTEM, 'context': None,
                 'verify': verify_timeline, 'combine': timeline_combine, 'matter': True, 'output_tokens': 1500,
                 'merge_tokens': (3000, 800), 'merge': True},
    'continuity': {'label': 'Widersprüche', 'offer': 'Mögliche Widersprüche', 'icon': 'link', 'system': CONTINUITY_SYSTEM,
                   'context': None, 'verify': verify_continuity, 'combine': continuity_combine, 'matter': True,
                   'output_tokens': 2000, 'merge_tokens': (6000, 800), 'merge': True},
    'language': {'label': 'Sprache', 'offer': 'Sprachliche Hinweise', 'icon': 'text-spellcheck', 'system': None,
                 'context': language_context, 'verify': None, 'local': check_language,
                 'local_options': lambda base, config: {'languagetool': languagetool_options(base, config)},
                 'combine': language_combine, 'matter': True,
                 'output_tokens': 0, 'merge_tokens': (0, 0), 'merge': False},
}


# ---------- 5. Lauf ----------

def next_run(folder):
    nums = [int(p.stem[4:]) for p in folder.glob('run-[0-9][0-9][0-9].md')]
    return f'run-{max(nums, default=0) + 1:03d}'


def cost_entry(s, provider, model, run_id, tin, tout, when, n, label='Figuren', kind='characters'):
    price = None
    if s.get('price_input_per_mtok') is not None and s.get('price_output_per_mtok') is not None:
        price = round(tin / 1e6 * float(s['price_input_per_mtok']) + tout / 1e6 * float(s['price_output_per_mtok']), 4)
    wf = yaml.safe_load((ROOT / 'workflow.yml').read_text(encoding='utf-8'))
    cur = ((wf.get('cost_tracking') or {}).get('project_currency') or 'EUR')
    act = f'act-{run_id}-{n:03d}' if kind == 'characters' else f'act-{kind}-{run_id}-{n:03d}'   # Läufe je Art zählen getrennt
    return {'activity_id': act, 'occurred_at': when, 'source': 'action_api', 'run_id': f'{kind}/{run_id}' if kind != 'characters' else run_id,
            'provider': provider, 'model': model, 'activity_type': 'other', 'currency': cur,
            'cost_amount': price, 'cost_status': 'estimated' if price is not None else 'unavailable',
            'input_tokens': tin, 'output_tokens': tout, 'note': f'{label}-Analyse (Hintergrundlauf)'}


def run(base, kind='characters', scope=None, now=None):
    base = Path(base)
    _, config = load(base)
    spec = KINDS[kind]
    s = settings(config)
    now = now or datetime.datetime.now().astimezone().isoformat(timespec='seconds')
    folder = base / 'analysis' / kind
    folder.mkdir(parents=True, exist_ok=True)
    run_id = next_run(folder)
    todo, results, calls = [], {}, []
    context = spec['context'](base, config) if spec['context'] else ''
    for bkey, title, texts in blocks(base, config, scope, spec['matter'], split=not spec.get('local')):
        fp = extraction_fingerprint(base, config, kind, texts, context)
        hit = cached(base, kind, bkey, fp)
        if hit:
            results[bkey] = hit['items']
        else:
            todo.append((bkey, title, texts, fp))
    local = spec.get('local')   # Art ohne KI (Sprache): kein Schlüssel, keine Kosten
    local_options = spec['local_options'](base, config) if local and spec.get('local_options') and todo else {}
    provider, key = pick_provider(s) if todo and not local else (s.get('provider') or 'anthropic', None)
    model = s.get('model') or PROVIDERS[provider]['model']
    merge_model = s.get('merge_model') or PROVIDERS[provider]['merge_model']
    context = spec['context'](base, config) if spec['context'] else ''
    if len(context) > MAX_BLOCK_CHARS:
        raise ValueError('Figurenkontext ist zu groß; vor der Analyse gezielt eingrenzen.')

    def extract(job):
        bkey, title, texts, fp = job
        if local:
            items, dropped = local(texts, **local_options)
            return bkey, fp, items, dropped, 0, 0
        user = f'BLOCK: {bkey}\n\n' + (f'{context}\n\n' if context else '') + f'## {title}\n\n{block_text(texts)}'
        text, tin, tout = call_llm(provider, key, model, spec['system'], user, kind)
        items, dropped = spec['verify'](parse_json(text), texts)
        return bkey, fp, items, dropped, tin, tout

    dropped_total = 0
    with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, int(s.get('parallel') or 4))) as pool:
        for bkey, fp, items, dropped, tin, tout in pool.map(extract, todo):
            results[bkey] = items
            dropped_total += dropped
            if not local:
                calls.append((model, tin, tout))
            cdir = cache_dir(base, kind)
            cdir.mkdir(parents=True, exist_ok=True)
            (cdir / f'{bkey}.json').write_text(json.dumps({'version': 2, 'fingerprint': fp, 'model': None if local else model, 'items': items},
                                                          ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    results = {k: results[k] for k in ordered_results(config, results)}
    result_digest = hashlib.sha256(json.dumps([results, merge_model], sort_keys=True, ensure_ascii=False).encode()).hexdigest()
    prev = sorted(folder.glob('run-[0-9][0-9][0-9].json'))
    prev = json.loads(prev[-1].read_text(encoding='utf-8')) if prev else None
    reuse = prev and prev.get('result_digest') == result_digest
    combine_todo = todo if todo else ([] if reuse else [True])
    if spec['merge'] and combine_todo and any(results.values()) and not key:
        provider, key = pick_provider(s)

    def ask(system, user):
        # Compare every pair of bounded result batches, including distant chapters.
        # Only extracted facts/events/names travel here, never the whole manuscript.
        batches, lines, size = [], [], 0
        for line in user.splitlines():
            if len(line) > MAX_BLOCK_CHARS // 2:
                raise ValueError('Ein Analyseergebnis ist zu lang zum sicheren Zusammenführen.')
            if lines and size + len(line) + 1 > MAX_BLOCK_CHARS // 2:
                batches.append('\n'.join(lines)); lines, size = [], 0
            lines.append(line); size += len(line) + 1
        if lines:
            batches.append('\n'.join(lines))
        requests = (batches[0],) if len(batches) == 1 else (
            batches[i] + '\n' + batches[j] for i in range(len(batches)) for j in range(i + 1, len(batches)))
        combined = {}
        for request in requests:
            text, tin, tout = call_llm(provider, key, merge_model, system, request, kind, 'merge')
            calls.append((merge_model, tin, tout))
            for field, values in parse_json(text).items():
                if isinstance(values, list):
                    target = combined.setdefault(field, [])
                    for value in values:
                        if value not in target:
                            target.append(value)
        return json.dumps(combined, ensure_ascii=False)

    result, body = spec['combine'](base, config, results, combine_todo, prev if reuse else None, ask)
    suggestions = dict({'kind': kind, 'scope': scope or 'book', 'run': run_id, 'created_at': now, 'result_digest': result_digest}, **result)
    (folder / f'{run_id}.json').write_text(json.dumps(suggestions, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    tin = sum(c[1] for c in calls)
    tout = sum(c[2] for c in calls)
    entries = [cost_entry(s, provider, m, run_id, a, b, now, i, spec['label'], kind) for i, (m, a, b) in enumerate(calls, start=1)]
    cost = sum(e['cost_amount'] or 0 for e in entries) if all(e['cost_amount'] is not None for e in entries) else None
    n = len(result.get('items') or [])
    head = {'id': run_id, 'type': 'analysis', 'kind': kind, 'scope': scope or 'book', 'created_at': now,
            'provider': None if local else provider, 'model': None if local else model,
            'merge_model': merge_model if spec['merge'] else None,
            'blocks_analysed': len(todo), 'blocks_cached': len(results) - len(todo), 'suggestions': n,
            'dropped_without_evidence': dropped_total, 'input_tokens': tin, 'output_tokens': tout,
            'cost': cost, 'result': f'{run_id}.json'}
    used = f'{model}, Zusammenführen: {merge_model}' if spec['merge'] else model
    lines = [f'# {spec["label"]}-Analyse {run_id[4:]}', '',
             f'{n} Vorschläge aus {len(results)} Blöcken ({len(todo)} neu gelesen, {len(results) - len(todo)} aus dem '
             f'Zwischenspeicher). {dropped_total} Angaben ohne wörtliche Fundstelle verworfen.'
             + ('' if local else (f' Der Buchtext ging an {provider} ({used}).' if todo else '')), '']
    lines += body + ['', f'Übernommen wird nichts automatisch: im Chat „{spec["offer"]} … liegen bereit“ öffnen.']
    (folder / f'{run_id}.md').write_text('---\n' + yaml.safe_dump(head, allow_unicode=True, sort_keys=False) + '---\n\n'
                                         + '\n'.join(lines) + '\n', encoding='utf-8')
    if entries:
        cpath = base / 'costs' / 'project.yml'
        cpath.parent.mkdir(exist_ok=True)
        data = (yaml.safe_load(cpath.read_text(encoding='utf-8')) or {}) if cpath.is_file() else {'scope': 'project'}
        data.setdefault('entries', [])
        data['entries'] = (data['entries'] or []) + entries
        cpath.write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False, width=10**6), encoding='utf-8')
    return head


def applied_file(base, kind):
    return Path(base) / 'analysis' / kind / 'applied.yml'


def latest(base, kind='characters'):
    """Neuester Lauf, der noch nicht übernommen bzw. verworfen ist: Kopf des Laufs oder None. Läufe anderer Arten ohne
    Vorschläge zählen nicht."""
    folder = Path(base) / 'analysis' / kind
    runs = sorted(folder.glob('run-[0-9][0-9][0-9].md')) if folder.is_dir() else []
    if not runs:
        return None
    done = set((yaml.safe_load(applied_file(base, kind).read_text(encoding='utf-8')) or {}).get('runs') or []) \
        if applied_file(base, kind).is_file() else set()
    m = re.match(r'\A---\n(.*?)\n---\n', runs[-1].read_text(encoding='utf-8'), re.S)
    head = yaml.safe_load(m.group(1)) if m else {}
    if head.get('id') in done or (kind != 'characters' and not head.get('suggestions')):
        return None
    return dict(head, path=str(runs[-1].relative_to(base)))


def latest_all(base):
    """[(art, kopf)] aller Arten mit offenem Lauf, in der Reihenfolge von KINDS."""
    return [(k, h) for k, h in ((k, latest(base, k)) for k in KINDS) if h]


def mark_applied(base, run_id, kind='characters'):
    p = applied_file(base, kind)
    data = (yaml.safe_load(p.read_text(encoding='utf-8')) or {}) if p.is_file() else {}
    data['runs'] = sorted(set((data.get('runs') or []) + [run_id]))
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(yaml.safe_dump(data, sort_keys=False), encoding='utf-8')


# ---------- Übernehmen ----------

def set_part(text, heading, value, before='## Manuskript'):
    """Inhalt unter „## heading“ ersetzen (bis zur nächsten Überschrift ##); fehlt die Überschrift, vor `before`
    bzw. am Ende einfügen."""
    block = f'## {heading}\n\n{value.strip()}\n\n'
    m = re.search(rf'(?m)^## {re.escape(heading)}\n.*?(?=^## |\Z)', text, re.S)
    if m:
        rest = text[m.end():]
        return text[:m.start()] + (block + rest if rest else block.rstrip('\n') + '\n')
    i = text.find(f'\n{before}\n') if before else -1
    if i >= 0:
        return text[:i + 1] + block + text[i + 1:]
    return text.rstrip('\n') + '\n\n' + block.rstrip('\n') + '\n'


def summary_target(config, item):
    """(Datei relativ zum Buch, Kapitel bzw. Abschnitt) eines Kurzbeschreibungs-Vorschlags oder (None, None)."""
    for ch in config['structure']['chapters']:
        if item['level'] == 'chapter' and ch['id'] == item['target']:
            return f'{ch["path"]}/README.md', ch
        for s in ch['sections']:
            if item['level'] == 'section' and s['id'] == item['target']:
                return s['path'], s
    return None, None


def apply_summaries(base, config, data, choices):
    """Ausgewählte Kurzbeschreibungen und Ziele eintragen. choices: [{index, short?, goal?}]; nur die genannten,
    nicht leeren Felder werden geschrieben (auch über einen vorhandenen Text). → [geänderte Dateien]"""
    items = data.get('items') or []
    changed = []
    for c in choices:
        it = items[int(c['index'])]
        rel, obj = summary_target(config, it)
        if not rel:
            raise SystemExit(f'Ziel von Vorschlag {c["index"]} ({it.get("number")}) gibt es nicht mehr')
        path = Path(base) / rel
        text = path.read_text(encoding='utf-8') if path.is_file() else f'# Kapitel {it["number"]} – {obj["title"]}\n'
        if it['level'] == 'chapter':
            heads, before = {'short': 'Kurzbeschreibung', 'goal': 'Ziel des Kapitels'}, '## Abschnitte'
        else:
            heads, before = {'goal': 'Ziel des Abschnitts', 'short': 'Kurzbeschreibung'}, '## Recherche- und Brainstorming-Ergebnisse'
        new = text
        for f, h in heads.items():
            v = (c.get(f) or '').strip()
            if v:
                new = set_part(new, h, v, before if f'\n{before}\n' in new else '## Manuskript')
        if new != text:
            path.write_text(new, encoding='utf-8')
            changed.append(rel)
    return changed


def set_top_block(text, key, data):
    """Oberste Ebene `key:` in einer YAML-Datei ersetzen bzw. anhängen; der Rest bleibt Zeichen für Zeichen."""
    block = yaml.safe_dump({key: data}, allow_unicode=True, sort_keys=False, width=10**6)
    m = re.search(rf'(?m)^{re.escape(key)}:.*\n(?:(?:[ \t]+.*|[ \t]*)\n)*', text)
    if m:
        return text[:m.start()] + block + text[m.end():]
    return text.rstrip('\n') + '\n' + block


def apply_style(base, config, data, choices):
    """Stilprofil in ghostwriter.yml (`style`): die gewählten Angaben (mit geändertem Wert), dazu die Zahlen ohne KI
    und der Lauf. choices: [{index, value}]. → [geänderte Dateien]"""
    items = data.get('items') or []
    style = {}
    for c in choices:
        it = items[int(c['index'])]
        v = c.get('value', it['value'])
        v = as_list(v) if it['field'] in STYLE_LISTS else str(v or '').strip()
        if v:
            style[it['field']] = v
    if not style:
        return []
    old = dict(config.get('style') or {})
    old.update(style)
    stats = data.get('stats') or {}
    for k in ('sentence_length_avg', 'dialogue_share'):
        if stats.get(k) is not None:
            old[k] = stats[k]
    old['source'] = f'analysis/style/{data.get("run")}'
    path = Path(base) / 'ghostwriter.yml'
    path.write_text(set_top_block(path.read_text(encoding='utf-8'), 'style', old), encoding='utf-8')
    return ['ghostwriter.yml']


def story_file(base, name):
    return Path(base) / 'story' / f'{name}.yml'


def section_ids(config):
    """{„N.M“ bzw. Titel eines Teils: ID} für Abschnitte und Teile von Vor- und Nachspann."""
    out = {i['title']: i['id'] for _, i in matter_items(config)}
    for ci, ch in enumerate(config['structure']['chapters'], start=1):
        for si, sec in enumerate(ch['sections'], start=1):
            out[f'{ci}.{si}'] = sec['id']
    return out


def apply_places(base, config, data, choices):
    """Schauplätze nach story/places.yml. choices: [{index, name?, kind?, short?, merge_into?}]; merge_into = ID
    eines vorhandenen Orts: dort werden nur leere Felder gefüllt, Namen und Abschnitte ergänzt. → [geänderte Dateien]"""
    from render_view import tag_slug
    items = data.get('items') or []
    ids = section_ids(config)
    path = story_file(base, 'places')
    have = (yaml.safe_load(path.read_text(encoding='utf-8')) or {}) if path.is_file() else {}
    places = have.get('places') or []
    n0 = json.dumps(places, sort_keys=True)
    for c in choices:
        it = items[int(c['index'])]
        name = ' '.join(str(c.get('name') or it['name']).split())
        secs = [ids[s] for s in it.get('sections') or [] if s in ids]
        target = next((p for p in places if p['id'] == c.get('merge_into')), None) or \
            next((p for p in places if norm(p['name']) in {norm(x) for x in [name] + it.get('aliases', [])}), None)
        if target:
            for f in PLACE_FIELDS:
                v = str(c[f] if f in c else it.get(f) or '').strip()
                if v and not target.get(f):
                    target[f] = v
            target['aliases'] = list(dict.fromkeys((target.get('aliases') or []) +
                                                   [x for x in [name] + it.get('aliases', []) if x != target['name']]))
            target['sections'] = list(dict.fromkeys((target.get('sections') or []) + secs))
            continue
        pid, n = 'pl-' + (tag_slug(name) or 'ort'), 2
        while any(p['id'] == pid for p in places):
            pid, n = f'pl-{tag_slug(name) or "ort"}-{n}', n + 1
        new = {'id': pid, 'name': name, 'aliases': [a for a in it.get('aliases') or [] if a != name]}
        for f in PLACE_FIELDS:
            v = str(c[f] if f in c else it.get(f) or '').strip()
            if v:
                new[f] = v
        new['sections'] = secs
        places.append(new)
    if json.dumps(places, sort_keys=True) == n0:
        return []
    path.parent.mkdir(exist_ok=True)
    path.write_text(yaml.safe_dump({'places': places}, allow_unicode=True, sort_keys=False, width=10**6), encoding='utf-8')
    return [str(path.relative_to(base))]


def apply_timeline(base, config, data, choices):
    """Zeitleiste nach story/timeline.yml: gewählte Ereignisse (choices [{index, when?, what?}]) und Auffälligkeiten
    ({issue, text?}); ersetzt die bisherige Zeitleiste der betroffenen Abschnitte nicht, sondern ergänzt sie
    (gleiche Abschnitt-Zeit-Beschreibung nur einmal). → [geänderte Dateien]"""
    items = data.get('items') or []
    issues = data.get('issues') or []
    ids = section_ids(config)
    path = story_file(base, 'timeline')
    have = (yaml.safe_load(path.read_text(encoding='utf-8')) or {}) if path.is_file() else {}
    events, notes = have.get('events') or [], have.get('notes') or []
    n0 = json.dumps([events, notes], sort_keys=True)
    num = {}
    for c in [c for c in choices if 'index' in c]:
        it = items[int(c['index'])]
        ev = {'section': ids.get(it['where'], it['where']), 'when': ' '.join(str(c.get('when', it['when'])).split()),
              'what': ' '.join(str(c.get('what') or it['what']).split()), 'quote': it['evidence'][0]['quote']}
        same = next((e for e in events if (e['section'], e['what']) == (ev['section'], ev['what'])), None)
        if same:
            num[it['n']] = same['id']
            continue
        ev = dict({'id': f'ev-{max([int(e["id"][3:]) for e in events] + [0]) + 1:03d}'}, **ev)
        events.append(ev)
        num[it['n']] = ev['id']
    for c in [c for c in choices if 'issue' in c]:
        x = issues[int(c['issue'])]
        refs = [num[n] for n in x['events'] if n in num]
        note = {'kind': x['kind'], 'text': ' '.join(str(c.get('text') or x['text']).split()), 'events': refs,
                'sections': list(dict.fromkeys(ids.get(e['where'], e['where']) for e in items if e['n'] in x['events']))}
        if note not in notes:
            notes.append(note)
    order = {sid: i for i, sid in enumerate(ids.values())}
    events.sort(key=lambda e: order.get(e['section'], 10**6))   # Buchreihenfolge, stabil
    if json.dumps([events, notes], sort_keys=True) == n0:
        return []
    path.parent.mkdir(exist_ok=True)
    out = {'events': events}
    if notes:
        out['notes'] = notes
    path.write_text(yaml.safe_dump(out, allow_unicode=True, sort_keys=False, width=10**6), encoding='utf-8')
    return [str(path.relative_to(base))]


def section_paths(config):
    """{„N.M“ bzw. Titel eines Teils: Pfad der Datei}."""
    out = {i['title']: i['path'] for _, i in matter_items(config)}
    for ci, ch in enumerate(config['structure']['chapters'], start=1):
        for si, sec in enumerate(ch['sections'], start=1):
            out[f'{ci}.{si}'] = sec['path']
    return out


def insert_marker(text, quote, marker):
    """Marker hinter den Satz mit dem Zitat setzen, nur im Manuskript. → neuer Text oder None (Zitat nicht gefunden)."""
    head, sep, ms = text.partition('\n## Manuskript\n')
    if not sep:
        return None
    words = re.findall(r'[^\W_]+', quote)
    if not words:
        return None
    m = re.search(r'(?<![^\W_])' + r'[\W_]+'.join(map(re.escape, words)) + r'(?![^\W_])', ms)
    if not m:
        return None
    end = re.compile(r'[.!?…]+["“”»«)]*(?=\s|$)|\n\s*\n|$').search(ms, m.end())
    i = end.end() if end and end.group(0).strip() else (end.start() if end else len(ms))
    if marker in ms[i:i + len(marker) + 2]:
        return text   # steht schon da
    return head + sep + ms[:i] + ' ' + marker + ms[i:]


def apply_continuity(base, config, data, choices):
    """Gewählte Widersprüche als Marker [KONTINUITÄT PRÜFEN: …] in den Text setzen, hinter den Satz der gewählten
    Fundstelle(n). choices: [{index, text?, mark: [Nummer der Fundstelle im Widerspruch, ab 0]}]; ohne mark die letzte.
    Sonst ändert sich am Text nichts. → [geänderte Dateien]"""
    items = data.get('items') or []
    paths = section_paths(config)
    changed, missing = [], []
    for c in choices:
        it = items[int(c['index'])]
        text = ' '.join(str(c.get('text') or it['text']).replace('[', '(').replace(']', ')').split())
        marks = c.get('mark') if c.get('mark') is not None else [len(it['facts']) - 1]
        for k in marks:
            f = it['facts'][int(k)]
            rel = paths.get(f['where'])
            if not rel:
                missing.append(f['where'])
                continue
            path = Path(base) / rel
            old = path.read_text(encoding='utf-8')
            new = insert_marker(old, f['quote'], f'[KONTINUITÄT PRÜFEN: {text}]')
            if new is None:
                missing.append(f['where'])
            elif new != old:
                path.write_text(new, encoding='utf-8')
                if rel not in changed:
                    changed.append(rel)
    if missing:
        print(f'Fundstelle nicht mehr im Text, kein Marker gesetzt: {", ".join(missing)}', file=sys.stderr)
    return changed


def apply_language(base, config, data, choices):
    """Sprachliche Hinweise nach story/hints.yml (der Text bleibt unverändert). Ersetzt die bisherigen Hinweise der
    Abschnitte, die der Lauf gelesen hat (ganzes Buch bzw. Kapitel). choices: [{index}]. → [geänderte Dateien]"""
    items = data.get('items') or []
    ids = section_ids(config)
    scope = str(data.get('scope') or 'book')
    if scope in ('book', 'buch', ''):
        covered = set(ids.values())
    else:
        ch = config['structure']['chapters'][int(scope) - 1]
        covered = {x['id'] for x in ch['sections']}
    path = story_file(base, 'hints')
    have = (yaml.safe_load(path.read_text(encoding='utf-8')) or {}) if path.is_file() else {}
    hints = [h for h in have.get('hints') or [] if h.get('source') != 'language' or h['section'] not in covered]
    n0 = json.dumps(have.get('hints') or [], sort_keys=True)
    nxt = max([int(h['id'][3:]) for h in hints] + [0]) + 1
    for c in choices:
        it = items[int(c['index'])]
        if it['where'] not in ids:
            continue
        hints.append({'id': f'hi-{nxt:03d}', 'section': ids[it['where']], 'source': 'language', 'kind': it['kind'],
                      'text': it['text'], 'quote': it['quote']})
        nxt += 1
    order = {sid: i for i, sid in enumerate(ids.values())}
    hints.sort(key=lambda h: order.get(h['section'], 10**6))
    if json.dumps(hints, sort_keys=True) == n0:
        return []
    path.parent.mkdir(exist_ok=True)
    path.write_text(yaml.safe_dump({'hints': hints}, allow_unicode=True, sort_keys=False, width=10**6), encoding='utf-8')
    return [str(path.relative_to(base))]


APPLY = {'summaries': apply_summaries, 'style': apply_style, 'places': apply_places, 'timeline': apply_timeline,
         'continuity': apply_continuity, 'language': apply_language}


def apply(base, run_id, kind, choices):
    """Ausgewählte Vorschläge eines Laufs übernehmen und den Lauf als erledigt vermerken. → [geänderte Dateien]"""
    base = Path(base)
    if kind not in APPLY:
        raise SystemExit(f'{kind}: übernehmen mit scripts/characters.py apply' if kind == 'characters' else f'unbekannte Art {kind}')
    data = json.loads((base / 'analysis' / kind / f'{run_id}.json').read_text(encoding='utf-8'))
    _, config = load(base)
    changed = APPLY[kind](base, config, data, choices)
    mark_applied(base, run_id, kind)
    return changed


def main(argv):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('project')
    ap.add_argument('cmd', choices=['plan', 'run', 'latest', 'applied', 'apply', 'settings-set'])
    ap.add_argument('args', nargs='*')
    ap.add_argument('--kind', default='characters', help='Art bzw. mehrere mit Komma: ' + ', '.join(KINDS))
    ap.add_argument('--scope')
    ap.add_argument('--json', action='store_true')
    a = ap.parse_intermixed_args(argv[1:])
    kinds = [k.strip() for k in a.kind.split(',') if k.strip()]
    for k in kinds:
        if k not in KINDS:
            ap.error(f'unbekannte Art {k} (möglich: {", ".join(KINDS)})')
    base = Path(a.project)
    if a.cmd == 'settings-set':
        if not a.args:
            ap.error('settings-set braucht die Einstellungen (JSON-Datei oder JSON-Text)')
        raw = a.args[0]
        try:
            data = json.loads(Path(raw).read_text(encoding='utf-8') if Path(raw).is_file() else raw)
            block = settings_set(base, data)
        except (ValueError, TypeError) as e:
            print(f'✗ {e}')
            return 1
        print('✓ Analyse-Einstellungen gespeichert: ghostwriter.yml' + ('' if block else ' (alles auf Vorgabe)'))
        return 0
    _, config = load(base)
    if a.cmd == 'plan':
        plans = [plan(base, config, k, a.scope) for k in kinds]
        if a.json:
            print(json.dumps(plans[0] if len(plans) == 1 else plans, ensure_ascii=False, indent=1))
            return 0
        for p in plans:
            cost = (f', geschätzt {p["cost_estimate"]:.2f} €'.replace('.', ',')) if p['cost_estimate'] is not None else ', Kosten ohne Preisangabe nicht schätzbar'
            print(f'{p["label"]}-Analyse ({p["scope"]}): {p["todo"]} von {len(p["blocks"])} Blöcken neu zu lesen, '
                  f'{p["cached"]} unverändert · etwa {p["input_tokens"]} Tokens Eingabe, {p["output_tokens"]} Ausgabe{cost}')
            if p['estimate_note']:
                print(p['estimate_note'])
        return 0
    if a.cmd == 'latest':
        head = latest(base, kinds[0])
        print(json.dumps(head, ensure_ascii=False, default=str) if a.json else
              (f'{head["id"]}: {head["suggestions"]} Vorschläge vom {str(head["created_at"])[:10]} ({head["path"]})' if head else 'keiner offen'))
        return 0
    if a.cmd == 'applied':
        if not a.args:
            ap.error('applied braucht die Lauf-ID')
        mark_applied(base, a.args[0], kinds[0])
        print(f'✓ {a.args[0]} als erledigt vermerkt')
        return 0
    if a.cmd == 'apply':
        if len(a.args) < 2:
            ap.error('apply braucht die Lauf-ID und die Auswahl (JSON-Datei oder JSON-Text)')
        raw = a.args[1]
        choices = json.loads(Path(raw).read_text(encoding='utf-8') if Path(raw).is_file() else raw)
        choices = choices.get('choices', []) if isinstance(choices, dict) else choices
        changed = apply(base, a.args[0], kinds[0], choices)
        print(f'✓ {KINDS[kinds[0]]["label"]}: {len(changed)} Dateien geändert, {a.args[0]} als erledigt vermerkt')
        for c in changed:
            print(f'  {c}')
        return 0
    for k in kinds:
        head = run(base, k, a.scope)
        label = KINDS[k]['label']
        print(f'✓ {label}-Analyse {head["id"]}: {head["suggestions"]} Vorschläge, {head["blocks_analysed"]} Blöcke gelesen, '
              f'{head["blocks_cached"]} aus dem Zwischenspeicher, {head["dropped_without_evidence"]} Angaben ohne Fundstelle verworfen')
        summary = os.environ.get('GITHUB_STEP_SUMMARY')
        if summary:
            with open(summary, 'a', encoding='utf-8') as f:
                f.write(f'## {label}-Analyse {head["id"]}\n\n{head["suggestions"]} Vorschläge · {head["blocks_analysed"]} Blöcke gelesen · '
                        f'{head["input_tokens"]} / {head["output_tokens"]} Tokens · Kosten: '
                        f'{"nicht bekannt (keine Preise in analysis)" if head["cost"] is None else head["cost"]}\n\n')
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
