#!/usr/bin/env python3
"""Recherche mit Internet über den eingestellten Recherche-Anbieter (#462, Teil 1).

Aufruf:
  python scripts/research.py <buch> provider [--provider P] [--defaults datei]
  python scripts/research.py <buch> run --section <id> [--question Q] [--provider P] [--model M]
                                        [--defaults datei] [--budget-low] [--confirm-low-budget]
  python scripts/research.py <buch> process [--defaults datei] [--budget-low]

Anbieter: `ai_providers.research.provider` des Buchs (ghostwriter.yml); ist dort keiner
gesetzt, der erste Dienst aus `available`, der in diesem Skript eine eingebaute Websuche
über die API hat und mit `access: api` eingetragen ist. Fehlt beides im Buch, gelten die
Einstellungen aus `--defaults` (ghostwriter.yml des Standard-Branchs einer Bibliothek).
Teil 1 kann: anthropic (Websuche „web_search“), openai (Responses-API mit „web_search“),
google (Gemini mit „Grounding with Google Search“). Andere Anbieter melden einen Hinweis.

Schlüssel: nur aus der Umgebungsvariable GHOSTWRITER_RESEARCH_KEY. Die Action setzt sie
aus dem Secret, dessen Name `provider` ausgibt (`ai_providers.services.<id>.api_key_secret`,
sonst `api_key_secret` aus providers.yml). Der Wert erscheint nie in Ausgaben.

Ergebnis je Lauf:
- `<kapitel>/research/<abschnitt>/run-NNN.md` (Kopf wie templates/research-run.md, dazu
  `web_research: true`, `searches`, `sources`, Tokens, `cost`). Die Quellenliste kommt nur
  aus den Belegen der Websuche (Titel, URL, Abrufdatum), nie aus dem Text des Modells.
- Kosteneintrag in `<kapitel>/costs/<abschnitt>.yml` (`source: action_api`,
  `activity_type: research`, Tokens, Suchanfragen als `other_usage_quantity`). Betrag aus
  den Preisen in `ai_providers.services.<id>` (`price_input_per_mtok`,
  `price_output_per_mtok`, optional `price_per_1k_searches`), sonst `unavailable`.
- Abschnitt `planned` → `research`.

`process` ist der frühere Weg ohne Reihenfolge und ohne Speichern je Auftrag; die Action
nutzt seit #480 die Hintergrund-Warteschlange `scripts/jobs.py`. `process` bearbeitet Aufträge `<kapitel>/research/<abschnitt>/request-NNN.yml` (aus der
Claude-Web-App): Erfolg löscht den Auftrag (und ältere fehlgeschlagene Aufträge desselben
Abschnitts), ein Fehler bleibt mit `error` und `failed_at` im Auftrag stehen. Den Commit
macht die Action „Recherche“. Übernommen wird nur nach Bestätigung.
"""
import argparse
import datetime
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

import yaml

import model_defaults

ROOT = Path(__file__).resolve().parent.parent
KEY_ENV = 'GHOSTWRITER_RESEARCH_KEY'
SECRET_RE = re.compile(r'^[A-Z][A-Z0-9_]*_API_KEY$')
REQUEST_RE = re.compile(r'^request-(\d{3,})\.yml$')
RUN_RE = re.compile(r'^run-(\d{3,})\.md$')
TIMEOUT = 300
MAX_SEARCHES = 5
MAX_MANUSCRIPT = 6000
MAX_PRIOR = 6000        # Vorwissen aus früheren Recherchen je Auftrag (#478), wie das Manuskript
PRIOR_PER_RUN = 1800
PRIOR_CHAPTER = 1500    # davon höchstens für andere Abschnitte desselben Kapitels

# Anbieter mit eingebauter Websuche über die API (Teil 1). Weitere folgen in Teil 2 von #462.
PROVIDERS = {
    'anthropic': {'model': 'claude-sonnet-5-5', 'label': 'Anthropic'},
    'openai': {'model': 'gpt-6.1-terra', 'label': 'OpenAI'},
    'google': {'model': 'gemini-3.8-flash', 'label': 'Google Gemini'},
}
# #554: Die Vorgaben stehen in providers.yml (`model_defaults`); die Werte oben sind nur der Rückfall.
for _pid, _p in PROVIDERS.items():
    _p['model'] = model_defaults.default_model(_pid, 'research', _p['model'])

HEADINGS = ['Fragestellung und Suchumfang', 'Rechercheergebnisse', 'Quellen', 'Widersprüche und Unsicherheiten',
            'Offene Fragen', 'Relevanz für den Abschnitt']


class ResearchError(Exception):
    pass


# ---------- Einstellungen ----------

def read_yaml(path):
    try:
        return yaml.safe_load(Path(path).read_text(encoding='utf-8')) or {}
    except (OSError, yaml.YAMLError):
        return {}


def catalog():
    data = read_yaml(ROOT / 'providers.yml')
    return {p['id']: p for p in data.get('providers') or [] if isinstance(p, dict) and p.get('id')}


def _pick(ap, cat):
    """Anbieter-ID aus einem ai_providers-Block oder None."""
    wanted = ((ap.get('research') or {}).get('provider') or '').strip()
    if wanted:
        return wanted
    services = ap.get('services') or {}
    for pid in ap.get('available') or []:
        if pid in PROVIDERS and (services.get(pid) or {}).get('access') == 'api':
            return pid
    return None


def resolve(base, defaults=None, provider=None, model=None):
    """{'provider', 'model', 'secret', 'name', 'service', 'from'} oder ResearchError mit verständlicher Meldung."""
    cat = catalog()
    book = (read_yaml(Path(base) / 'ghostwriter.yml').get('ai_providers') or {})
    lib = (read_yaml(defaults).get('ai_providers') or {}) if defaults else {}
    src, ap = 'buch', book
    pid = (provider or '').strip() or _pick(book, cat)
    if not pid and lib:
        pid, src, ap = _pick(lib, cat), 'bibliothek', lib
    if not pid or pid == 'chat':
        raise ResearchError('Für die Recherche ist kein Anbieter mit API eingestellt. Im Formular „KI-Dienste“ '
                            'bei „Recherche“ einen Anbieter wählen und seinen API-Schlüssel als GitHub-Secret '
                            'hinterlegen; ohne Anbieter wird im Chat recherchiert.')
    info = cat.get(pid)
    if not info:
        raise ResearchError(f'Unbekannter Anbieter {pid!r} (nicht in providers.yml).')
    name = info.get('name') or pid
    if pid not in PROVIDERS:
        if 'api' not in (info.get('access') or []):
            raise ResearchError(f'{name} gibt es nur als Chat-App: Recherche dort im Chat machen.')
        raise ResearchError(f'{name} kann in der Action „Recherche“ noch nicht recherchieren '
                            '(kommt mit Teil 2 von #462). Möglich sind Anthropic, OpenAI und Google.')
    service = (ap.get('services') or {}).get(pid) or {}
    secret = service.get('api_key_secret') or info.get('api_key_secret') or ''
    if not SECRET_RE.match(secret):
        raise ResearchError(f'Ungültiger Secret-Name {secret!r}: erlaubt sind Namen wie GEMINI_API_KEY '
                            '(Großbuchstaben, endet auf _API_KEY).')
    role = ap.get('research') or {}
    smodel = service.get('model') or ''
    use = (model or '').strip() or (role.get('model') or '').strip() or ('' if 'image' in smodel else smodel) \
        or PROVIDERS[pid]['model']
    return {'provider': pid, 'model': use, 'secret': secret, 'name': name, 'service': service, 'from': src}


# ---------- Buch ----------

def load_config(base):
    config = read_yaml(Path(base) / 'ghostwriter.yml')
    if not (config.get('structure') or {}).get('chapters'):
        raise ResearchError('ghostwriter.yml hat keine Gliederung.')
    return config


def find_section(base, config, section_id):
    for ci, ch in enumerate(config['structure']['chapters'], start=1):
        for si, sec in enumerate(ch.get('sections') or [], start=1):
            if sec.get('id') == section_id:
                path = Path(base) / sec['path'] if sec.get('path') else None
                if not path or not path.is_file():
                    raise ResearchError(f'Abschnittsdatei für {section_id} fehlt.')
                return ch, sec, path, f'{ci}.{si}'
    raise ResearchError(f'Abschnitt {section_id} steht nicht in der Gliederung.')


def split_front(text):
    m = re.match(r'^---\n(.*?)\n---\n?', text, re.S)
    return (yaml.safe_load(m.group(1)) or {}, text[m.end():]) if m else ({}, text)


def block(body, heading):
    m = re.search(rf'(?m)^##\s+{re.escape(heading)}\s*$\n(.*?)(?=^##\s|\Z)', body, re.S)
    return m.group(1).strip() if m else ''


def next_number(folder, pattern):
    nums = [int(m.group(1)) for p in folder.glob('*') if (m := pattern.match(p.name))] if folder.is_dir() else []
    return max(nums, default=0) + 1


# ---------- Anfrage ----------

def _run_summary(path):
    """Kurzfassung eines Rechercheeintrags: Ergebnisse, Widersprüche, offene Fragen (ohne Quellenliste), gekürzt."""
    try:
        head, body = split_front(path.read_text(encoding='utf-8'))
    except OSError:
        return ''
    parts = []
    for heading, label in (('Rechercheergebnisse', ''), ('Widersprüche und Unsicherheiten', 'Widersprüche: '),
                           ('Offene Fragen', 'Offene Fragen: ')):
        t = re.sub(r'\s+', ' ', block(body, heading)).strip()
        if t and t not in ('-', '–', 'Keine.', 'Keine'):
            parts.append(label + t)
    if not parts:
        return ''
    text = ' '.join(parts)
    text = text[:PRIOR_PER_RUN].rstrip() + (' …' if len(text) > PRIOR_PER_RUN else '')
    return f'{path.stem} ({head.get("date", "")}): {text}'


def prior_knowledge(base, ch, sec, limit=MAX_PRIOR):
    """Vorwissen (#478): bereits erledigte Recherchen desselben Abschnitts, dazu gekürzt die anderen Abschnitte des Kapitels
    (höchstens PRIOR_CHAPTER Zeichen, nur was vom Platz übrig bleibt). Je Gruppe die neuesten zuerst, zusammen höchstens
    `limit` Zeichen; ausgegeben werden ältere zuerst. Gibt Text oder '' zurück."""
    chapter = Path(base) / ch['path'] / 'research'
    own = chapter / sec['id']

    def lines(paths):
        return [(p, line) for p in paths if (line := _run_summary(p))]

    def take(items, cap):
        chosen, used = [], 0
        for path, line in items:   # neueste zuerst; zu lange überspringen, ältere kürzere dürfen noch passen
            if used + len(line) <= cap:
                chosen.append((path, line))
                used += len(line)
        return chosen, used

    own_runs = sorted((p for p in own.glob('run-*.md') if RUN_RE.match(p.name)), reverse=True) if own.is_dir() else []
    other_runs = sorted((p for d in chapter.glob('*') if d.is_dir() and d.name != sec['id'] for p in d.glob('run-*.md')
                         if RUN_RE.match(p.name)), key=lambda p: (p.stem, str(p)), reverse=True) if chapter.is_dir() else []
    mine, used = take(lines(own_runs), limit)
    others, _ = take(lines(other_runs), min(PRIOR_CHAPTER, limit - used))
    out = ['[anderer Abschnitt] ' + line for _, line in sorted(others, key=lambda c: (c[0].stem, str(c[0])))]
    out += [line for _, line in sorted(mine, key=lambda c: c[0].stem)]
    return '\n'.join(out)


def prompts(config, ch, sec, text, number, question=None, prior=''):
    p = config.get('project') or {}
    en = str(p.get('language') or 'de').lower().startswith('en')
    _, body = split_front(text)
    goal, summary = block(body, 'Ziel des Abschnitts'), block(body, 'Kurzbeschreibung')
    ms = block(body, 'Manuskript')[:MAX_MANUSCRIPT]
    heads = [h for h in HEADINGS if h != 'Quellen']
    system = ('Du recherchierst für ein Buchprojekt im Internet. Antworte auf ' + ('Englisch' if en else 'Deutsch')
              + '. Stütze jede Tatsache auf Suchergebnisse; was du nicht belegen kannst, kennzeichne ausdrücklich als '
              'unbelegt. Erfinde keine Quellen, Zitate, Zahlen oder Namen. Nenne im Text keine URLs und keine '
              'Quellenliste – die Quellen übernimmt GhostWriter aus den Belegen der Suche. Gliedere die Antwort '
              'in genau diese Überschriften der Ebene 2: ' + ', '.join(f'„## {h}“' for h in heads) + '. '
              'Davor höchstens zwei Sätze Zusammenfassung. Kein ganzer Buchtext, keine Formulierungen fürs Manuskript.')
    lines = [f'Buch: {p.get("title") or p.get("working_title") or ""}', f'Buchtyp: {p.get("book_type") or ""}',
             f'Zielgruppe: {p.get("target_audience") or ""}', f'Beschreibung: {p.get("description") or ""}',
             f'Kapitel: {ch.get("title") or ""}', f'Abschnitt {number}: {sec.get("title") or ""}',
             f'Ziel des Abschnitts: {goal or "offen"}', f'Kurzbeschreibung: {summary or "offen"}']
    user = '\n'.join(l for l in lines if not l.endswith(': ')) + '\n\n'
    user += f'Fragestellung: {question.strip()}\n' if (question or '').strip() else \
        'Fragestellung: Recherchiere die Fakten, Hintergründe und Zusammenhänge, die dieser Abschnitt braucht.\n'
    if ms and ms not in ('Offen.', '–'):
        user += f'\nBisheriges Manuskript (Auszug, nur zur Orientierung):\n{ms}\n'
    if prior:   # #478: schon Recherchiertes nicht wiederholen
        user += ('\nVorwissen aus früheren Recherchen (bereits erledigt). Bekanntes nicht wiederholen, Widersprüche dazu '
                 'ausdrücklich nennen, offene Fragen daraus aufgreifen:\n' + prior + '\n') if not en else \
                ('\nPrior knowledge from earlier research (already done). Do not repeat what is known, name any contradictions '
                 'explicitly, take up the open questions from it:\n' + prior + '\n')
    return system, user


def post_json(url, body, headers, provider='', model=''):
    req = urllib.request.Request(url, method='POST', data=json.dumps(body).encode('utf-8'),
                                 headers=dict(headers, **{'content-type': 'application/json'}))
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            return json.loads(r.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
        detail = e.read().decode('utf-8', 'replace')[:300]
        raise ResearchError(model_defaults.classify_http_error(
            e.code, detail, (PROVIDERS.get(provider) or {}).get('label') or provider or 'Der Anbieter', model)) from None
    except (urllib.error.URLError, TimeoutError) as e:
        raise ResearchError(f'Der Anbieter ist nicht erreichbar: {getattr(e, "reason", e)}') from None


def _sources(pairs):
    out, seen = [], set()
    for title, url in pairs:
        if url and url not in seen:
            seen.add(url)
            out.append({'title': (title or '').strip() or url, 'url': url})
    return out


def call_anthropic(key, model, system, user):
    data = post_json('https://api.anthropic.com/v1/messages', {
        'model': model, 'max_tokens': 8000, 'system': system, 'messages': [{'role': 'user', 'content': user}],
        'tools': [{'type': 'web_search_20250305', 'name': 'web_search', 'max_uses': MAX_SEARCHES}]},
        {'x-api-key': key, 'anthropic-version': '2023-06-01'}, 'anthropic', model)
    text, cited, found = [], [], []
    for b in data.get('content') or []:
        if b.get('type') == 'text':
            text.append(b.get('text') or '')
            cited += [(c.get('title'), c.get('url')) for c in b.get('citations') or [] if c.get('url')]
        elif b.get('type') == 'web_search_tool_result' and isinstance(b.get('content'), list):
            found += [(c.get('title'), c.get('url')) for c in b['content'] if c.get('url')]
    u = data.get('usage') or {}
    return {'text': ''.join(text), 'sources': _sources(cited or found), 'input_tokens': u.get('input_tokens') or 0,
            'output_tokens': u.get('output_tokens') or 0,
            'searches': (u.get('server_tool_use') or {}).get('web_search_requests') or 0, 'request_id': data.get('id')}


def call_openai(key, model, system, user):
    data = post_json('https://api.openai.com/v1/responses', {
        'model': model, 'instructions': system, 'input': user, 'tools': [{'type': 'web_search'}]},
        {'authorization': f'Bearer {key}'}, 'openai', model)
    text, cited, searches = [], [], 0
    for item in data.get('output') or []:
        if item.get('type') == 'web_search_call':
            searches += 1
        elif item.get('type') == 'message':
            for c in item.get('content') or []:
                if c.get('type') == 'output_text':
                    text.append(c.get('text') or '')
                    cited += [(a.get('title'), a.get('url')) for a in c.get('annotations') or []
                              if a.get('type') == 'url_citation']
    u = data.get('usage') or {}
    return {'text': '\n'.join(text), 'sources': _sources(cited), 'input_tokens': u.get('input_tokens') or 0,
            'output_tokens': u.get('output_tokens') or 0, 'searches': searches, 'request_id': data.get('id')}


def call_google(key, model, system, user):
    data = post_json(f'https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent', {
        'systemInstruction': {'parts': [{'text': system}]}, 'contents': [{'role': 'user', 'parts': [{'text': user}]}],
        'tools': [{'google_search': {}}]}, {'x-goog-api-key': key}, 'google', model)
    cand = (data.get('candidates') or [{}])[0]
    text = ''.join(p.get('text') or '' for p in (cand.get('content') or {}).get('parts') or [])
    gm = cand.get('groundingMetadata') or {}
    chunks = [(c['web'].get('title'), c['web'].get('uri')) for c in gm.get('groundingChunks') or [] if c.get('web')]
    u = data.get('usageMetadata') or {}
    return {'text': text, 'sources': _sources(chunks), 'input_tokens': u.get('promptTokenCount') or 0,
            'output_tokens': (u.get('candidatesTokenCount') or 0) + (u.get('thoughtsTokenCount') or 0),
            'searches': len(gm.get('webSearchQueries') or []), 'request_id': data.get('responseId')}


CALLS = {'anthropic': call_anthropic, 'openai': call_openai, 'google': call_google}

# Gemini liefert Quellen als befristete Weiterleitungen (vertexaisearch.cloud.google.com/grounding-api-redirect/…)
# und als Titel nur die Domain. In der Action werden sie zur echten Adresse und zum Seitentitel aufgelöst.
REDIRECT_HOSTS = ('vertexaisearch.cloud.google.com',)
RESOLVE_TIMEOUT = 10


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


def _title(url):
    try:
        req = urllib.request.Request(url, headers={'user-agent': 'Mozilla/5.0 (GhostWriter Recherche)'})
        with urllib.request.urlopen(req, timeout=RESOLVE_TIMEOUT) as r:
            if 'html' not in (r.headers.get('content-type') or ''):
                return ''
            raw = r.read(65536).decode(r.headers.get_content_charset() or 'utf-8', 'replace')
        m = re.search(r'(?is)<title[^>]*>(.*?)</title>', raw)
        import html
        return re.sub(r'\s+', ' ', html.unescape(m.group(1))).strip()[:200] if m else ''
    except Exception:
        return ''


def resolve_source(src):
    """Weiterleitung auflösen (Location-Kopf, ohne ihr zu folgen) und Seitentitel holen; Fehler lassen die Quelle unverändert."""
    url = src['url']
    if urllib.parse.urlparse(url).hostname not in REDIRECT_HOSTS:
        return src
    try:
        opener = urllib.request.build_opener(_NoRedirect)
        target = None
        for method in ('HEAD', 'GET'):          # manche Weiterleitungen antworten nur auf GET
            req = urllib.request.Request(url, method=method, headers={'user-agent': 'Mozilla/5.0 (GhostWriter Recherche)'})
            try:
                opener.open(req, timeout=RESOLVE_TIMEOUT)
                return src
            except urllib.error.HTTPError as e:
                target = e.headers.get('location') if 300 <= e.code < 400 else None
            if target:
                break
        if not target or not target.startswith('http'):
            return src
        domain = src['title']
        title = _title(target)
        return {'title': f'{title} ({domain})' if title and domain and domain not in title else (title or domain or target),
                'url': target}
    except Exception:
        return src


def resolve_sources(sources):
    if not any(urllib.parse.urlparse(s['url']).hostname in REDIRECT_HOSTS for s in sources):
        return sources
    from concurrent.futures import ThreadPoolExecutor
    with ThreadPoolExecutor(max_workers=8) as pool:
        out = list(pool.map(resolve_source, sources))
    return _sources([(s['title'], s['url']) for s in out])


# ---------- Ergebnis ----------

def strip_sources(text):
    """Eigene Quellenlisten und nackte URLs des Modells entfernen: Quellen kommen nur aus den Suchbelegen."""
    text = re.sub(r'(?ms)^##\s+Quellen\s*$.*?(?=^##\s|\Z)', '', text)
    return re.sub(r'\n{3,}', '\n\n', text).strip()


def with_sources(text, sources, today, en=False):
    if sources:
        lst = '\n'.join(f'- [{s["title"]}]({s["url"]}) – {"retrieved" if en else "abgerufen am"} {today}'
                        for s in sources)
        note = ('Aus den Belegen der Websuche. Inhalt und Belegstelle vor der Verwendung prüfen.' if not en else
                'From the web search evidence. Check content and passage before use.')
        part = f'## Quellen\n\n{note}\n\n{lst}\n'
    else:
        part = ('## Quellen\n\nDie Suche hat keine Belege geliefert. Die Angaben oben sind nicht belegt und vor der '
                'Verwendung zu prüfen.\n')
    m = re.search(r'(?m)^##\s+Widersprüche und Unsicherheiten\s*$', text)
    return (text[:m.start()] + part + '\n' + text[m.start():]) if m else (text.rstrip() + '\n\n' + part)


def price(service, tin, tout, searches):
    try:
        pin, pout = service.get('price_input_per_mtok'), service.get('price_output_per_mtok')
        if pin is None or pout is None:
            return None, False
        amount = tin / 1e6 * float(pin) + tout / 1e6 * float(pout)
        ps = service.get('price_per_1k_searches')
        if searches and ps is not None:
            amount += searches / 1000 * float(ps)
        return round(amount, 4), bool(searches and ps is None)
    except (TypeError, ValueError):
        return None, False


def set_status(text):
    return re.sub(r'(?m)\A(---\n(?:.*\n)*?)status:\s*planned\s*$', r'\1status: research', text, count=1)


def write_cost(base, ch, sec, entry):
    path = Path(base) / ch['path'] / 'costs' / f'{sec["id"]}.yml'
    path.parent.mkdir(parents=True, exist_ok=True)
    data = read_yaml(path) if path.is_file() else {}
    data = data or {'section_id': sec['id']}
    data['entries'] = (data.get('entries') or []) + [entry]
    path.write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False, width=10**6), encoding='utf-8')
    return path


def api_key(provider):
    """Schlüssel für den Anbieter: GHOSTWRITER_RESEARCH_KEY_<ANBIETER> (je Auftrag kann der Anbieter
    wechseln, #480); nur wenn die Action keine Schlüssel je Anbieter setzt, der allgemeine."""
    specific = {k: v for k, v in os.environ.items() if k.startswith(KEY_ENV + '_')}
    if specific:
        return specific.get(f'{KEY_ENV}_{provider.upper()}', '')
    return os.environ.get(KEY_ENV, '')


def run(base, section_id, question=None, provider=None, model=None, defaults=None, now=None, request=None):
    base = Path(base)
    cfg = resolve(base, defaults, provider, model)
    key = api_key(cfg['provider'])
    if not key:
        raise ResearchError(f'Kein Schlüssel: Secret {cfg["secret"]} im Repository hinterlegen '
                            '(docs/DIENSTE-NUTZEN.md, „API-Schlüssel als GitHub-Secret“).')
    config = load_config(base)
    ch, sec, spath, number = find_section(base, config, section_id)
    text = spath.read_text(encoding='utf-8')
    head, _ = split_front(text)
    if (head.get('approvals') or {}).get('section'):
        raise ResearchError(f'Abschnitt {number} ist abgeschlossen. Zum Recherchieren zuerst wieder öffnen.')
    system, user = prompts(config, ch, sec, text, number, question, prior_knowledge(base, ch, sec))
    res = CALLS[cfg['provider']](key, cfg['model'], system, user)
    res['sources'] = resolve_sources(res['sources'])
    body = strip_sources(res['text'])
    if not body:
        raise ResearchError('Der Anbieter hat keinen Text geliefert. Bitte später noch einmal versuchen.')
    now = now or datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0)
    today = now.date().isoformat()
    en = str((config.get('project') or {}).get('language') or 'de').lower().startswith('en')
    folder = base / ch['path'] / 'research' / sec['id']
    folder.mkdir(parents=True, exist_ok=True)
    n = f'{next_number(folder, RUN_RE):03d}'
    amount, no_search_price = price(cfg['service'], res['input_tokens'], res['output_tokens'], res['searches'])
    run_id = f'run-{n}'
    meta = {'id': run_id, 'type': 'research', 'section_id': sec['id'], 'status': 'completed', 'date': today,
            'provider': cfg['provider'], 'model': cfg['model'], 'web_research': True, 'searches': res['searches'],
            'sources': len(res['sources']), 'input_tokens': res['input_tokens'], 'output_tokens': res['output_tokens'],
            'cost': amount}
    if request:
        meta['request'] = request
    intro = (f'> Recherche mit Internet über {cfg["name"]} ({cfg["model"]}) in der Action „Recherche“: '
             f'{res["searches"]} Suchanfragen, {len(res["sources"])} Quellen. Angaben vor der Verwendung prüfen.')
    md = ('---\n' + yaml.safe_dump(meta, allow_unicode=True, sort_keys=False) + '---\n\n'
          + f'# Recherchelauf {n}\n\n{intro}\n\n' + with_sources(body, res['sources'], today, en).rstrip() + '\n')
    (folder / f'{run_id}.md').write_text(md, encoding='utf-8')
    wf = read_yaml(ROOT / 'workflow.yml')
    note = f'Recherche mit Internet ({res["searches"]} Suchanfragen)' + (', ohne Suchkosten' if no_search_price else '')
    entry = {'activity_id': f'act-research-{sec["id"]}-{run_id}', 'occurred_at': now.isoformat(),
             'source': 'action_api', 'run_id': f'research/{sec["id"]}/{run_id}', 'provider': cfg['provider'],
             'model': cfg['model'], 'activity_type': 'research', 'section_id': sec['id'],
             'currency': (wf.get('cost_tracking') or {}).get('project_currency') or 'EUR',
             'cost_amount': amount, 'cost_status': 'estimated' if amount is not None else 'unavailable',
             'input_tokens': res['input_tokens'], 'output_tokens': res['output_tokens'],
             'other_usage_quantity': res['searches'], 'note': note}
    if res.get('request_id'):
        entry['request_id'] = str(res['request_id'])[:200]
    write_cost(base, ch, sec, entry)
    new = set_status(text)
    if new != text:
        spath.write_text(new, encoding='utf-8')
    return dict(meta, number=number, path=str((folder / f'{run_id}.md').relative_to(base)), name=cfg['name'])


def requests(base):
    base = Path(base)
    out = []
    for path in sorted(base.glob('chapters/*/research/*/request-*.yml')) + sorted(base.glob('matter/research/*/request-*.yml')):
        if REQUEST_RE.match(path.name):
            data = read_yaml(path)
            if not data.get('error'):
                out.append((path, data))
    return out


def process(base, defaults=None, budget_low=False, now=None):
    results = []
    for path, data in requests(base):
        sid = str(data.get('section_id') or path.parent.name)
        try:
            if budget_low and not data.get('confirm_low_budget'):
                raise ResearchError('Weniger als 10 % des KI-Budgets übrig. Den Auftrag mit „trotzdem starten“ '
                                    'erneut stellen oder das Budget anpassen.')
            head = run(base, sid, data.get('question'), data.get('provider'), data.get('model'), defaults, now,
                       request=path.stem)
            path.unlink()
            for old in path.parent.glob('request-*.yml'):
                if REQUEST_RE.match(old.name) and read_yaml(old).get('error'):
                    old.unlink()
            results.append({'request': str(path.relative_to(base)), 'ok': True, 'run': head['path'],
                            'searches': head['searches'], 'sources': head['sources'], 'cost': head['cost']})
        except ResearchError as e:
            data.update({'error': str(e), 'failed_at': (now or datetime.datetime.now(datetime.timezone.utc))
                         .replace(microsecond=0).isoformat()})
            path.write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False), encoding='utf-8')
            results.append({'request': str(path.relative_to(base)), 'ok': False, 'error': str(e)})
    return results


def summary(results):
    lines = []
    for r in results:
        if r['ok']:
            cost = 'Kosten ohne Preisangabe' if r['cost'] is None else f'etwa {r["cost"]:.4f}'.replace('.', ',')
            lines.append(f'- Recherche gespeichert: {r["run"]} ({r["searches"]} Suchanfragen, {r["sources"]} Quellen, {cost})')
        else:
            lines.append(f'- Nicht recherchiert ({r["request"]}): {r["error"]}')
    return '\n'.join(lines) or '- Keine offenen Rechercheaufträge.'


def main(argv=None):
    ap = argparse.ArgumentParser(description='Recherche mit Internet über den eingestellten Anbieter (#462).')
    ap.add_argument('base')
    ap.add_argument('cmd', choices=['provider', 'run', 'process'])
    ap.add_argument('--section')
    ap.add_argument('--question')
    ap.add_argument('--provider')
    ap.add_argument('--model')
    ap.add_argument('--defaults', help='ghostwriter.yml des Standard-Branchs (Einstellungen der Bibliothek)')
    ap.add_argument('--budget-low', action='store_true', help='limits.py meldet: weniger als 10 % Budget übrig')
    ap.add_argument('--confirm-low-budget', action='store_true')
    ap.add_argument('--each', action='store_true',
                    help='provider: Secret-Namen je Anbieter (secret_<id>) für die Action, je Auftrag kann der Anbieter wechseln')
    a = ap.parse_args(argv)
    defaults = a.defaults if a.defaults and Path(a.defaults).is_file() else None
    try:
        if a.cmd == 'provider' and a.each:
            lines = []
            for pid in PROVIDERS:
                try:
                    lines.append(f'secret_{pid}={resolve(a.base, defaults, pid)["secret"]}')
                except ResearchError:
                    continue
            print('\n'.join(lines) or 'Kein Anbieter mit API eingestellt.')
            out = os.environ.get('GITHUB_OUTPUT')
            if out and lines:
                with open(out, 'a', encoding='utf-8') as f:
                    f.write('\n'.join(lines) + '\n')
            return 0
        if a.cmd == 'provider':
            c = resolve(a.base, defaults, a.provider, a.model)
            print(json.dumps({k: c[k] for k in ('provider', 'model', 'secret', 'name', 'from')}, ensure_ascii=False))
            out = os.environ.get('GITHUB_OUTPUT')
            if out:
                with open(out, 'a', encoding='utf-8') as f:
                    f.write(f'provider={c["provider"]}\nsecret={c["secret"]}\nname={c["name"]}\n')
            return 0
        if a.cmd == 'run':
            if not a.section:
                raise ResearchError('--section fehlt.')
            if a.budget_low and not a.confirm_low_budget:
                raise ResearchError('Weniger als 10 % des KI-Budgets übrig. Mit confirm_low_budget trotzdem starten.')
            h = run(a.base, a.section, a.question, a.provider, a.model, defaults)
            print(summary([{'ok': True, 'run': h['path'], 'searches': h['searches'], 'sources': h['sources'],
                            'cost': h['cost']}]))
            return 0
        res = process(a.base, defaults, a.budget_low)
        print(summary(res))
        return 0 if all(r['ok'] for r in res) else 1
    except ResearchError as e:
        print(f'::error::{e}')
        return 2


if __name__ == '__main__':
    sys.exit(main())
