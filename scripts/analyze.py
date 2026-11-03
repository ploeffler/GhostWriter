#!/usr/bin/env python3
"""Analysen über das ganze Buch als Hintergrundlauf (#123): zuerst Figuren.

Aufruf:
  python scripts/analyze.py <buch> plan [--kind characters] [--scope book|N] [--json]
  python scripts/analyze.py <buch> run  [--kind characters] [--scope book|N] [--date …]
  python scripts/analyze.py <buch> latest [--kind characters] [--json]     neuester offener Lauf (für die Übersicht)
  python scripts/analyze.py <buch> applied <run-id> [--kind characters]  Lauf als übernommen vermerken

Läuft in der Action „Analyse im Hintergrund“ (analyse.yml), lokal genauso. Ablauf:
  1. Vorbereiten ohne KI: das Buch je Kapitel (Vor- und Nachspann als eigener
     Block); je Block ein Fingerabdruck (SHA-256 des Textes). Blöcke, deren
     Fingerabdruck im Zwischenspeicher analysis/cache/<art>/ steht, werden nicht
     neu gelesen.
  2. Je Block ein KI-Aufruf (parallel, `analysis.model`): Figuren nur aus dem
     Text, jede Angabe mit wörtlicher Fundstelle (`evidence: [{field, where,
     quote}]`).
  3. Prüfung ohne KI: Eine Fundstelle zählt nur, wenn das Zitat wörtlich im
     angegebenen Abschnitt steht; Angaben ohne gültige Fundstelle fallen weg,
     Figuren ohne jede gültige Fundstelle auch. Abschnitte bleiben nur, wenn
     Name oder ein anderer Name dort vorkommt.
  4. Zusammenführen: gleiche Namen bzw. andere Namen ohne KI, dann ein Aufruf
     mit `analysis.merge_model` für Spitznamen („Opi“ = „Opa Karl“).
     Unterschiedliche Angaben (z. B. Alter) kommen als Widerspruch in die
     Liste, entschieden wird nichts.
  5. Ablage: analysis/<art>/run-NNN.md (Lauf) und run-NNN.json (Vorschläge im
     Format von `render_view.py character-suggest`), Kosten je Aufruf in
     costs/project.yml (source: action_api). Nichts wird automatisch angelegt;
     übernommen wird im Chat (START.md, „Figuren“, Schritt 7).

Einstellungen in ghostwriter.yml (alle optional), Block `analysis`:
  provider          anthropic | openai (sonst der erste mit hinterlegtem Schlüssel)
  model, merge_model  Modelle für Schritt 2 und 4 (sonst Vorgaben des Anbieters)
  price_input_per_mtok, price_output_per_mtok  Preise je 1 Mio. Tokens in
                    Projektwährung; ohne Preise: Kosten „unavailable“, Tokens werden
                    trotzdem erfasst
  parallel          gleichzeitige Aufrufe (Vorgabe 4)
Schlüssel: Umgebungsvariable mit dem Namen aus providers.yml (ANTHROPIC_API_KEY,
OPENAI_API_KEY), in der Action aus den GitHub-Secrets.

Tests: GHOSTWRITER_FAKE_LLM=<datei.json> ersetzt die KI-Aufrufe durch feste
Antworten ({"extract": {<block>: {...}}, "merge": {...}}).
"""
import argparse
import concurrent.futures
import datetime
import hashlib
import json
import os
import re
import sys
import urllib.request
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'scripts'))
from render_view import (character_file, character_items, load, matter_items, section_file)  # noqa: E402

KINDS = {'characters': 'Figuren'}
PROVIDERS = {
    'anthropic': {'secret': 'ANTHROPIC_API_KEY', 'model': 'claude-haiku-5-5', 'merge_model': 'claude-sonnet-5-5'},
    'openai': {'secret': 'OPENAI_API_KEY', 'model': 'gpt-5-mini', 'merge_model': 'gpt-5'},
}
CHARS_PER_TOKEN = 3.5     # grobe Schätzung für deutschen Text
PROMPT_TOKENS = 900       # Anweisungen und bekannte Figuren je Aufruf (Schätzung)
OUTPUT_TOKENS = 1500      # Antwort je Block (Schätzung)
FIELDS = ('short', 'age', 'appearance', 'traits', 'voice')

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


def settings(config):
    s = {'provider': None, 'model': None, 'merge_model': None, 'price_input_per_mtok': None,
         'price_output_per_mtok': None, 'parallel': 4}
    s.update((config or {}).get('analysis') or {})
    return s


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

def blocks(base, config, scope=None):
    """[(schlüssel, titel, {abschnitt: text})] je Kapitel; Vor- und Nachspann als Block „Vor- und Nachspann“."""
    out = []
    chapters = config['structure']['chapters']
    want = None if scope in (None, '', 'book', 'buch') else int(scope)
    if want is None:
        texts = {i['title']: section_file(base, i)[3] for _, i in matter_items(config)}
        texts = {k: v for k, v in texts.items() if v.strip() and v.strip() != 'Noch nicht begonnen.'}
        if texts:
            out.append(('matter', 'Vor- und Nachspann', texts))
    for ci, ch in enumerate(chapters, start=1):
        if want is not None and ci != want:
            continue
        texts = {}
        for si, s in enumerate(ch['sections'], start=1):
            ms = section_file(base, s)[3].strip()
            if ms and ms != 'Noch nicht begonnen.':
                texts[f'{ci}.{si}'] = ms
        if texts:
            out.append((ch['id'], f'Kapitel {ci}: {ch["title"]}', texts))
    return out


def block_text(texts):
    return '\n\n'.join(f'### {k}\n\n{v}' for k, v in texts.items())


def fingerprint(texts):
    return hashlib.sha256(block_text(texts).encode('utf-8')).hexdigest()


def cache_dir(base, kind):
    return Path(base) / 'analysis' / 'cache' / kind


def cached(base, kind, key, fp):
    p = cache_dir(base, kind) / f'{key}.json'
    if p.is_file():
        data = json.loads(p.read_text(encoding='utf-8'))
        if data.get('fingerprint') == fp:
            return data
    return None


def plan(base, config, kind='characters', scope=None):
    s = settings(config)
    rows, chars_new = [], 0
    for key, title, texts in blocks(base, config, scope):
        fp = fingerprint(texts)
        hit = cached(base, kind, key, fp) is not None
        n = len(block_text(texts))
        rows.append({'key': key, 'title': title, 'chars': n, 'cached': hit})
        if not hit:
            chars_new += n
    todo = [r for r in rows if not r['cached']]
    tin = int(chars_new / CHARS_PER_TOKEN) + PROMPT_TOKENS * len(todo) + (2000 if todo else 0)
    tout = OUTPUT_TOKENS * len(todo) + (500 if todo else 0)
    cost = None
    if s.get('price_input_per_mtok') is not None and s.get('price_output_per_mtok') is not None:
        cost = round(tin / 1e6 * float(s['price_input_per_mtok']) + tout / 1e6 * float(s['price_output_per_mtok']), 2)
    return {'kind': kind, 'scope': scope or 'book', 'blocks': rows, 'todo': len(todo), 'cached': len(rows) - len(todo),
            'input_tokens': tin, 'output_tokens': tout, 'cost_estimate': cost}


# ---------- 2. KI-Aufrufe ----------

def call_llm(provider, key, model, system, user):
    """(antwort-text, input_tokens, output_tokens). GHOSTWRITER_FAKE_LLM: feste Antworten für Tests."""
    fake = os.environ.get('GHOSTWRITER_FAKE_LLM')
    if fake:
        data = json.loads(Path(fake).read_text(encoding='utf-8'))
        if system is MERGE_SYSTEM:
            return json.dumps(data.get('merge') or {'groups': []}), 100, 20
        m = re.search(r'^BLOCK: (\S+)$', user, re.M)
        return json.dumps((data.get('extract') or {}).get(m.group(1) if m else '', {'items': []})), len(user) // 4, 300
    if provider == 'anthropic':
        req = urllib.request.Request('https://api.anthropic.com/v1/messages', method='POST', data=json.dumps({
            'model': model, 'max_tokens': 8000, 'system': system, 'messages': [{'role': 'user', 'content': user}]}).encode(),
            headers={'x-api-key': key, 'anthropic-version': '2023-06-01', 'content-type': 'application/json'})
        with urllib.request.urlopen(req, timeout=300) as r:
            data = json.loads(r.read())
        text = ''.join(b.get('text', '') for b in data.get('content') or [])
        u = data.get('usage') or {}
        return text, int(u.get('input_tokens') or 0), int(u.get('output_tokens') or 0)
    req = urllib.request.Request('https://api.openai.com/v1/chat/completions', method='POST', data=json.dumps({
        'model': model, 'response_format': {'type': 'json_object'},
        'messages': [{'role': 'system', 'content': system}, {'role': 'user', 'content': user}]}).encode(),
        headers={'authorization': f'Bearer {key}', 'content-type': 'application/json'})
    with urllib.request.urlopen(req, timeout=300) as r:
        data = json.loads(r.read())
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


def verify(items, texts):
    """Nur Angaben mit wörtlicher Fundstelle; → (geprüfte Figuren, Zahl verworfener Angaben)."""
    ntexts = {k: norm(v) for k, v in texts.items()}
    every = ' '.join(ntexts.values())
    out, dropped = [], 0
    for it in items or []:
        name = (it.get('name') or '').strip()
        if not name:
            continue
        ok = []
        for e in it.get('evidence') or []:
            q = norm(e.get('quote'))
            where = str(e.get('where') or '')
            if len(q) >= 3 and (q in ntexts.get(where, '') or (where not in ntexts and q in every)):
                ok.append({'field': e.get('field') or 'name', 'where': where if where in ntexts else
                           next((k for k, v in ntexts.items() if q in v), where), 'quote': e.get('quote', '').strip()})
            else:
                dropped += 1
        if not ok:
            dropped += 1
            continue
        names = [name] + [a for a in it.get('aliases') or [] if a]
        fields = {f for f in (e['field'] for e in ok)}
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


# ---------- 5. Lauf ----------

def next_run(folder):
    nums = [int(p.stem[4:]) for p in folder.glob('run-[0-9][0-9][0-9].md')]
    return f'run-{max(nums, default=0) + 1:03d}'


def cost_entry(s, provider, model, run_id, tin, tout, when, n):
    price = None
    if s.get('price_input_per_mtok') is not None and s.get('price_output_per_mtok') is not None:
        price = round(tin / 1e6 * float(s['price_input_per_mtok']) + tout / 1e6 * float(s['price_output_per_mtok']), 4)
    wf = yaml.safe_load((ROOT / 'workflow.yml').read_text(encoding='utf-8'))
    cur = ((wf.get('cost_tracking') or {}).get('project_currency') or 'EUR')
    return {'activity_id': f'act-{run_id}-{n:03d}', 'occurred_at': when, 'source': 'action_api', 'run_id': run_id,
            'provider': provider, 'model': model, 'activity_type': 'other', 'currency': cur,
            'cost_amount': price, 'cost_status': 'estimated' if price is not None else 'unavailable',
            'input_tokens': tin, 'output_tokens': tout, 'note': 'Figuren-Analyse (Hintergrundlauf)'}


def run(base, kind='characters', scope=None, now=None):
    base = Path(base)
    _, config = load(base)
    s = settings(config)
    provider, key = pick_provider(s)
    model = s.get('model') or PROVIDERS[provider]['model']
    merge_model = s.get('merge_model') or PROVIDERS[provider]['merge_model']
    now = now or datetime.datetime.now().astimezone().isoformat(timespec='seconds')
    folder = base / 'analysis' / kind
    folder.mkdir(parents=True, exist_ok=True)
    run_id = next_run(folder)
    known = '\n'.join(f'- {c["name"]}' + (': ' + character_file(base, c)[0]['short'] if character_file(base, c)[0].get('short') else '')
                      for c in character_items(config)) or '- (keine)'
    todo, results, calls = [], {}, []
    for bkey, title, texts in blocks(base, config, scope):
        fp = fingerprint(texts)
        hit = cached(base, kind, bkey, fp)
        if hit:
            results[bkey] = (hit['items'], texts, True)
        else:
            todo.append((bkey, title, texts, fp))

    def extract(job):
        bkey, title, texts, fp = job
        user = f'BLOCK: {bkey}\n\nBekannte Figuren:\n{known}\n\n## {title}\n\n{block_text(texts)}'
        text, tin, tout = call_llm(provider, key, model, EXTRACT_SYSTEM, user)
        items, dropped = verify(parse_json(text).get('items'), texts)
        return bkey, texts, fp, items, dropped, tin, tout

    dropped_total = 0
    with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, int(s.get('parallel') or 4))) as pool:
        for bkey, texts, fp, items, dropped, tin, tout in pool.map(extract, todo):
            results[bkey] = (items, texts, False)
            dropped_total += dropped
            calls.append((model, tin, tout))
            cdir = cache_dir(base, kind)
            cdir.mkdir(parents=True, exist_ok=True)
            (cdir / f'{bkey}.json').write_text(json.dumps({'fingerprint': fp, 'model': model, 'items': items},
                                                          ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    found = [it for key in results for it in results[key][0]]
    groups = []
    prev = sorted(folder.glob('run-[0-9][0-9][0-9].json'))
    if prev and not todo:   # nichts Neues gelesen: Zuordnung der Spitznamen vom letzten Lauf
        groups = json.loads(prev[-1].read_text(encoding='utf-8')).get('groups') or []
    if len(found) > 1 and todo:   # Spitznamen: ein Aufruf mit dem stärkeren Modell
        listing = '\n'.join(f'- {it["name"]}' + (f' (auch: {", ".join(it["aliases"])})' if it.get('aliases') else '')
                            + (f': {it["short"]}' if it.get('short') else '') for it in found)
        text, tin, tout = call_llm(provider, key, merge_model, MERGE_SYSTEM, listing)
        groups = [g for g in parse_json(text).get('groups') or [] if isinstance(g, list) and len(g) > 1]
        calls.append((merge_model, tin, tout))
    items, conflicts = merge(found, groups)
    suggestions = {'scope': scope or 'book', 'run': run_id, 'created_at': now, 'items': items, 'conflicts': conflicts,
                   'groups': groups}
    (folder / f'{run_id}.json').write_text(json.dumps(suggestions, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    tin = sum(c[1] for c in calls)
    tout = sum(c[2] for c in calls)
    entries = [cost_entry(s, provider, m, run_id, a, b, now, i) for i, (m, a, b) in enumerate(calls, start=1)]
    cost = sum(e['cost_amount'] or 0 for e in entries) if all(e['cost_amount'] is not None for e in entries) else None
    head = {'id': run_id, 'type': 'analysis', 'kind': kind, 'scope': scope or 'book', 'created_at': now,
            'provider': provider, 'model': model, 'merge_model': merge_model,
            'blocks_analysed': len(todo), 'blocks_cached': len(results) - len(todo), 'suggestions': len(items),
            'dropped_without_evidence': dropped_total, 'input_tokens': tin, 'output_tokens': tout,
            'cost': cost, 'result': f'{run_id}.json'}
    body = [f'# {KINDS[kind]}-Analyse {run_id[4:]}', '',
            f'{len(items)} Vorschläge aus {len(results)} Blöcken ({len(todo)} neu gelesen, {len(results) - len(todo)} aus dem '
            f'Zwischenspeicher). {dropped_total} Angaben ohne wörtliche Fundstelle verworfen. Der Buchtext ging an {provider} '
            f'({model}, Zusammenführen: {merge_model}).', '', '## Vorschläge', '']
    body += [f'- **{it["name"]}**' + (f' (auch: {", ".join(it["aliases"])})' if it['aliases'] else '') +
             (f': {it["short"]}' if it.get('short') else '') + (f' – {", ".join(it["sections"])}' if it['sections'] else '')
             for it in items] or ['*keine*']
    body += ['', '## Widersprüche', '']
    body += [f'- {c["name"]}, {c["field"]}: ' + ' / '.join(str(v) for v in c['values']) for c in conflicts] or ['*keine*']
    body += ['', 'Übernommen wird nichts automatisch: im Chat „Figurenvorschläge … liegen bereit“ öffnen.']
    (folder / f'{run_id}.md').write_text('---\n' + yaml.safe_dump(head, allow_unicode=True, sort_keys=False) + '---\n\n'
                                         + '\n'.join(body) + '\n', encoding='utf-8')
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
    """Neuester Lauf, der noch nicht übernommen bzw. verworfen ist: Kopf des Laufs oder None."""
    folder = Path(base) / 'analysis' / kind
    runs = sorted(folder.glob('run-[0-9][0-9][0-9].md')) if folder.is_dir() else []
    if not runs:
        return None
    done = set((yaml.safe_load(applied_file(base, kind).read_text(encoding='utf-8')) or {}).get('runs') or []) \
        if applied_file(base, kind).is_file() else set()
    m = re.match(r'\A---\n(.*?)\n---\n', runs[-1].read_text(encoding='utf-8'), re.S)
    head = yaml.safe_load(m.group(1)) if m else {}
    return None if head.get('id') in done else dict(head, path=str(runs[-1].relative_to(base)))


def mark_applied(base, run_id, kind='characters'):
    p = applied_file(base, kind)
    data = (yaml.safe_load(p.read_text(encoding='utf-8')) or {}) if p.is_file() else {}
    data['runs'] = sorted(set((data.get('runs') or []) + [run_id]))
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(yaml.safe_dump(data, sort_keys=False), encoding='utf-8')


def main(argv):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('project')
    ap.add_argument('cmd', choices=['plan', 'run', 'latest', 'applied'])
    ap.add_argument('args', nargs='*')
    ap.add_argument('--kind', default='characters', choices=list(KINDS))
    ap.add_argument('--scope')
    ap.add_argument('--json', action='store_true')
    a = ap.parse_args(argv[1:])
    base = Path(a.project)
    _, config = load(base)
    if a.cmd == 'plan':
        p = plan(base, config, a.kind, a.scope)
        if a.json:
            print(json.dumps(p, ensure_ascii=False, indent=1))
            return 0
        cost = (f', geschätzt {p["cost_estimate"]:.2f} €'.replace('.', ',')) if p['cost_estimate'] is not None else ', Kosten ohne Preisangabe nicht schätzbar'
        print(f'{KINDS[a.kind]}-Analyse ({p["scope"]}): {p["todo"]} von {len(p["blocks"])} Blöcken neu zu lesen, '
              f'{p["cached"]} unverändert · etwa {p["input_tokens"]} Tokens Eingabe, {p["output_tokens"]} Ausgabe{cost}')
        return 0
    if a.cmd == 'latest':
        head = latest(base, a.kind)
        print(json.dumps(head, ensure_ascii=False, default=str) if a.json else
              (f'{head["id"]}: {head["suggestions"]} Vorschläge vom {str(head["created_at"])[:10]} ({head["path"]})' if head else 'keiner offen'))
        return 0
    if a.cmd == 'applied':
        if not a.args:
            ap.error('applied braucht die Lauf-ID')
        mark_applied(base, a.args[0], a.kind)
        print(f'✓ {a.args[0]} als erledigt vermerkt')
        return 0
    head = run(base, a.kind, a.scope)
    print(f'✓ {KINDS[a.kind]}-Analyse {head["id"]}: {head["suggestions"]} Vorschläge, {head["blocks_analysed"]} Blöcke gelesen, '
          f'{head["blocks_cached"]} aus dem Zwischenspeicher, {head["dropped_without_evidence"]} Angaben ohne Fundstelle verworfen')
    summary = os.environ.get('GITHUB_STEP_SUMMARY')
    if summary:
        with open(summary, 'a', encoding='utf-8') as f:
            f.write(f'## {KINDS[a.kind]}-Analyse {head["id"]}\n\n{head["suggestions"]} Vorschläge · {head["blocks_analysed"]} Blöcke gelesen · '
                    f'{head["input_tokens"]} / {head["output_tokens"]} Tokens · Kosten: '
                    f'{"nicht bekannt (keine Preise in analysis)" if head["cost"] is None else head["cost"]}\n')
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
