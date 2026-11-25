#!/usr/bin/env python3
"""Referenzbilder an einen Bilddienst übergeben und die Übergabe festhalten (#143, Punkte 5 und 6).

  python3 scripts/image_service.py <buch> services
      zeigt die Bilddienste mit ihrer Fähigkeit (Referenzbilder ja/nein, Anzahl, Formate, Größe)
  python3 scripts/image_service.py <buch> plan --service google --references ref-img-… [--text-only-ok]
      prüft, was an den Dienst gehen würde, ohne etwas zu senden: übergeben, übersprungen (mit Grund), Betriebsart
  python3 scripts/image_service.py <buch> generate --service google --prompt "…" --references ref-img-… --consent
                                                   [--text-only-ok] [--model M] [--out ordner]
      erzeugt einen Bildentwurf über den eigenen Zugang (Secret des Dienstes, nur in der Action „Bild erzeugen“) und schreibt
      `bild.jpg` und das Protokoll `handover.yml` (Dienst, Modell, übergebene Referenz-IDs mit Bildversion = SHA-256 der Datei,
      übersprungene mit Grund, Betriebsart) in einen neuen Ordner unter `quellen/bild-entwuerfe/`

Grundsätze: Es gehen nur **freigegebene** Referenzen an den Dienst, ausgewählt je Auftrag (`reference_images.select`). Die
Fähigkeit je Dienst steht in `providers.yml` unter `image_services`. Kann oder will der Dienst keine Bildreferenzen, wird das
ausdrücklich gemeldet: Es entsteht nie der Eindruck, ein Bild sei übergeben worden, das nicht übergeben wurde. Ein Auftrag
**ohne** Übergabe läuft nur mit `--text-only-ok` und als Ersatz durch die Beschreibung der Referenzen im Text; das Protokoll
nennt dann `modus: text-only`. Bilder mit Personen gehen nur mit `--consent`. Das Ergebnis ist ein Entwurf, kein Buchbild:
Übernehmen und Freigeben bleiben eigene Schritte (`images.py add`). Spätere Änderungen an einer Referenz ändern das Protokoll
nie. Tests laufen nur mit Attrappe (kein Netz, D08).
"""
import argparse
import base64
import datetime
import hashlib
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'scripts'))

DRAFTS = 'quellen/bild-entwuerfe'
MIME = {'.png': 'image/png', '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg'}
API = {'google': 'https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent'}
TIMEOUT = 300


def services(root=ROOT):
    """{id: Eintrag} der Bilddienste aus providers.yml (`image_services`)."""
    try:
        data = yaml.safe_load((Path(root) / 'providers.yml').read_text(encoding='utf-8')) or {}
    except (OSError, yaml.YAMLError):
        data = {}
    return {s['id']: s for s in data.get('image_services') or [] if isinstance(s, dict) and s.get('id')}


def plan(base, service_id, reference_ids, root=ROOT):
    """Was an den Dienst ginge: {'service', 'modus': 'bytes'|'text-only', 'uebergeben': [...], 'uebersprungen': [...], 'hinweise': [...]}.
    Sendet nichts. Nicht freigegebene Referenzen bricht `select` mit Meldung ab."""
    import reference_images
    refs = reference_images.select(Path(base), list(reference_ids or []))
    cap = services(root).get(service_id)
    out = {'service': service_id, 'modus': 'bytes', 'uebergeben': [], 'uebersprungen': [], 'hinweise': []}
    if not refs:
        out['modus'] = 'keine'
        return out
    if cap is None:
        out['hinweise'].append(f'Bilddienst „{service_id}“ steht nicht in providers.yml (image_services); es wird nichts übergeben.')
    elif not cap.get('via_action'):
        out['hinweise'].append(f'{cap.get("name", service_id)} wird von GhostWriter nicht angesprochen: die Bildbytes der Referenzen '
                               f'gehen nicht an diesen Dienst. {cap.get("note", "").strip()}'.strip())
    elif not (cap.get('references') or {}).get('supported'):
        out['hinweise'].append(f'{cap.get("name", service_id)} unterstützt keine Referenzbilder; es wird nichts übergeben.')
    if out['hinweise']:
        out['modus'] = 'text-only'
        out['uebersprungen'] = [{'id': r['id'], 'grund': 'Dienst nimmt keine Bildreferenzen von GhostWriter an'} for r in refs]
        return out
    limits = cap['references']
    formats = [str(f).lower() for f in limits.get('formats') or []]
    for r in refs:
        path = Path(r['file'])
        mime = MIME.get(path.suffix.lower(), '')
        fmt = {'image/png': 'png', 'image/jpeg': 'jpeg'}.get(mime, path.suffix.lstrip('.').lower())
        data = path.read_bytes() if path.is_file() else None
        if data is None:
            out['uebersprungen'].append({'id': r['id'], 'grund': 'Bilddatei fehlt'})
        elif formats and fmt not in formats:
            out['uebersprungen'].append({'id': r['id'], 'grund': f'Format {fmt} wird vom Dienst nicht unterstützt ({", ".join(formats)})'})
        elif limits.get('max_bytes') and len(data) > int(limits['max_bytes']):
            out['uebersprungen'].append({'id': r['id'], 'grund': f'{len(data)} Bytes: größer als die Grenze des Dienstes ({limits["max_bytes"]})'})
        elif limits.get('max') and len(out['uebergeben']) >= int(limits['max']):
            out['uebersprungen'].append({'id': r['id'], 'grund': f'mehr als {limits["max"]} Referenzen: der Dienst nimmt höchstens so viele'})
        else:
            out['uebergeben'].append({'id': r['id'], 'datei': str(path), 'mime': mime, 'bytes': len(data),
                                      'version': 'sha256:' + hashlib.sha256(data).hexdigest()})
    if out['uebersprungen']:
        out['hinweise'].append(f'{len(out["uebersprungen"])} von {len(refs)} Referenzen gehen nicht an den Dienst; die Gründe stehen im Protokoll.')
    if not out['uebergeben']:
        out['modus'] = 'text-only'
    return out


def describe(base, reference_ids):
    """Ersatz durch Beschreibung (kenntlich im Prompt): Bildunterschrift und Beschreibung der Referenzen."""
    import reference_images
    lines = []
    for r in reference_images.select(Path(base), list(reference_ids or [])):
        lines.append(f'- {r["caption"]}' + (f': {r["description"]}' if r.get('description') else ''))
    return ('\nHinweis: Die folgenden Referenzbilder wurden NICHT als Bild übergeben, nur beschrieben:\n' + '\n'.join(lines)) if lines else ''


def request_body(prompt, handed):
    """Anfrage an die Gemini-API: Text, dann die Referenzbilder als inline_data (Bildbytes)."""
    parts = [{'text': prompt}]
    for h in handed:
        parts.append({'inline_data': {'mime_type': h['mime'], 'data': base64.b64encode(Path(h['datei']).read_bytes()).decode()}})
    return {'contents': [{'parts': parts}], 'generationConfig': {'responseModalities': ['IMAGE']}}


def post_json(url, body, headers, timeout=TIMEOUT):
    req = urllib.request.Request(url, data=json.dumps(body).encode('utf-8'), method='POST',
                                 headers=dict(headers, **{'Content-Type': 'application/json'}))
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
        raise ValueError(f'Der Bilddienst antwortet mit HTTP {e.code}: {e.read().decode("utf-8", "replace")[:300]}') from None
    except (urllib.error.URLError, TimeoutError) as e:
        raise ValueError(f'Der Bilddienst ist nicht erreichbar: {getattr(e, "reason", e)}') from None


def image_from(data):
    for cand in data.get('candidates') or []:
        for part in (cand.get('content') or {}).get('parts') or []:
            blob = part.get('inlineData') or part.get('inline_data')
            if blob and blob.get('data'):
                return base64.b64decode(blob['data'])
    return None


def generate(base, service_id, prompt, reference_ids=(), *, key, model=None, out=None, consent=False, text_only_ok=False,
             post=None, today=None, root=ROOT):
    """Bildentwurf erzeugen und protokollieren. Gibt (Ordner, Protokoll) zurück. `post(url, body, headers)` ist für Tests
    austauschbar."""
    import model_defaults
    base = Path(base)
    if service_id not in API:
        raise ValueError(f'Für den Dienst „{service_id}“ gibt es keinen Aufruf in GhostWriter (möglich: {", ".join(API)}).')
    p = plan(base, service_id, reference_ids, root)
    if p['modus'] == 'text-only' and not text_only_ok:
        raise ValueError('Referenzen werden nicht als Bild übergeben: ' + ' '.join(p['hinweise'])
                         + ' Mit --text-only-ok läuft der Auftrag nur mit der Beschreibung im Text; das Protokoll hält das fest.')
    if p['uebergeben'] and not consent:
        raise ValueError('Die Referenzbilder gehen an den Bilddienst: --consent (Einverständnis der Abgebildeten bzw. der Familie) ist nötig.')
    if not key:
        raise ValueError('Der API-Schlüssel des Dienstes fehlt (Secret).')
    model = model or model_defaults.default_model(service_id, 'image', 'gemini-2.5-flash-image', root)
    text = prompt + (describe(base, reference_ids) if p['modus'] == 'text-only' and reference_ids else '')
    body = request_body(text, p['uebergeben'])
    data = (post or post_json)(API[service_id].format(model=model), body, {'x-goog-api-key': key})
    image = image_from(data)
    if not image:
        raise ValueError('Der Bilddienst hat kein Bild geliefert.')
    day = (today or datetime.date.today()).isoformat()
    folder = Path(out) if out else base / DRAFTS / f'{day}-{_next(base / DRAFTS, day):02d}'
    folder.mkdir(parents=True, exist_ok=False)
    (folder / 'bild.jpg').write_bytes(image)
    record = {'dienst': service_id, 'modell': model, 'datum': day, 'modus': p['modus'], 'prompt': prompt,
              'uebergeben': [{k: h[k] for k in ('id', 'version', 'mime', 'bytes')} for h in p['uebergeben']],
              'uebersprungen': p['uebersprungen'], 'hinweise': p['hinweise'],
              'ergebnis': {'datei': 'bild.jpg', 'bytes': len(image), 'version': 'sha256:' + hashlib.sha256(image).hexdigest()},
              'hinweis': 'Entwurf, kein Buchbild: Übernehmen und Freigeben sind eigene Schritte (images.py add).'}
    (folder / 'handover.yml').write_text(yaml.safe_dump(record, allow_unicode=True, sort_keys=False), encoding='utf-8')
    return folder, record


def _next(root, day):
    n = 1
    while (root / f'{day}-{n:02d}').exists():
        n += 1
    return n


def services_text(root=ROOT):
    lines = ['| Dienst | Über GhostWriter | Referenzbilder | Anzahl | Formate | geprüft |', '|---|---|---|---|---|---|']
    for s in services(root).values():
        ref = s.get('references') or {}
        lines.append(f'| {s.get("name", s["id"])} (`{s["id"]}`) | {"ja" if s.get("via_action") else "nein"} | '
                     f'{"ja" if ref.get("supported") else "nein"} | {ref.get("max") or "–"} | {", ".join(ref.get("formats") or []) or "–"} | '
                     f'{s.get("checked_at", "–")} |')
    return '\n'.join(lines) + '\n'


def main(argv=None):
    import os
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('base')
    sub = ap.add_subparsers(dest='cmd', required=True)
    sub.add_parser('services')
    for name in ('plan', 'generate'):
        p = sub.add_parser(name)
        p.add_argument('--service', required=True)
        p.add_argument('--references', nargs='*', default=[])
        p.add_argument('--text-only-ok', action='store_true')
    g = sub.choices['generate']
    g.add_argument('--prompt', required=True)
    g.add_argument('--consent', action='store_true')
    g.add_argument('--model')
    g.add_argument('--out')
    a = ap.parse_args(argv)
    try:
        if a.cmd == 'services':
            print(services_text(), end='')
        elif a.cmd == 'plan':
            r = plan(a.base, a.service, a.references)
            print(yaml.safe_dump(r, allow_unicode=True, sort_keys=False), end='')
            return 0 if r['modus'] != 'text-only' or a.text_only_ok else 1
        else:
            secret = (services().get(a.service) or {}).get('api_key_secret', '')
            folder, rec = generate(a.base, a.service, a.prompt, a.references, key=os.environ.get(secret, ''), model=a.model,
                                   out=a.out, consent=a.consent, text_only_ok=a.text_only_ok)
            print(f'✓ Entwurf: {folder}/bild.jpg · Modus {rec["modus"]} · {len(rec["uebergeben"])} Referenzen übergeben, '
                  f'{len(rec["uebersprungen"])} übersprungen')
            for h in rec['hinweise']:
                print(f'⚠ {h}')
    except (ValueError, SystemExit) as exc:
        print(exc if isinstance(exc, ValueError) else exc.code, file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
