#!/usr/bin/env python3
"""Fotos colorieren, nur Farbkanäle übernehmen (#452).

Aufruf:
  python scripts/colorize.py <buch> <bildordner> [--model M] [--consent] [--replace]
  python scripts/colorize.py <buch> <bildordner> --proposal <farbvorschlag> --tool "ImagineArt (seedream-v5-lite)" [--replace]
  python scripts/colorize.py <buch> <bildordner> --check
  python scripts/colorize.py <buch> <bildordner> --consent --hint "Die Fahne ist rot-weiß-rot."
  python scripts/colorize.py <buch> <bildordner> --consent --minors-exception

Ein Bildordner (z. B. quellen/bilder/2026-11-21-ehepaar/) enthält `aufbereitet.jpg`
(Schwarz-Weiß, gleichmäßig aufbereitet) und `bild.yml` mit der Beschreibung. Das
Skript holt einen Farbvorschlag beim eigenen Google-Gemini-Zugang (Secret
GEMINI_API_KEY, nur in der Action „Bild colorieren“) oder nimmt einen vorhandenen
Vorschlag (`--proposal`, z. B. aus einem Bilddienst im Chat) und übernimmt davon
**nur die Farbe**: Die Helligkeit (L im Lab-Farbraum) kommt Pixel für Pixel aus
`aufbereitet.jpg`, aus dem Vorschlag nur a und b. Gesichter, Konturen und
Hintergrund kann der Vorschlag so nicht verändern.

Sperren (vor jedem Aufruf, auch bei --check): `bild.yml` muss da sein,
`minderjaehrige: false` ausdrücklich enthalten und `art` muss `foto` oder
`foto-vom-foto` sein. Kinderbilder und Dokumente gehen nie an einen externen Dienst.
Für den Aufruf bei Google ist `--consent` Pflicht (Abgebildete bzw. Familie sind
einverstanden; das Bild geht an Google).

Ausnahme für Bilder mit Kindern oder Jugendlichen (`--minors-exception`): nur
wenn `minderjaehrige: true` ausdrücklich in `bild.yml` steht und zusammen mit
`--consent` bzw. `--proposal`. Die Entscheidung trifft der Benutzer im Einzelfall;
`bild.yml` bleibt unverändert, der Eintrag unter `bearbeitung` nennt die Ausnahme.
Dokumente bleiben immer gesperrt.

Farbhinweis (`--hint`, nur beim Aufruf bei Gemini): bekannte Farben, z. B. „Die
Fahne ist rot-weiß-rot“, werden an die Anfrage angehängt und im Eintrag unter
`bearbeitung` genannt. Die Farbe bleibt eine Annahme des Modells.

Prüfungen nach dem Einfärben: gleiches Seitenverhältnis (±2 %), Bildaufbau
gleich (Korrelation der Helligkeit ≥ 0,7) und mittlere L-Abweichung zwischen
`coloriert.jpg` und `aufbereitet.jpg` unter 1/255. Sonst Abbruch, nichts wird
geschrieben.

Ergebnis: `coloriert.jpg`, ein Eintrag unter `bearbeitung` in `bild.yml`
(Werkzeug, Modell, Datum, „nur Farbkanäle übernommen“, L-Abweichung) und beim
Aufruf über die API ein Kosteneintrag in costs/project.yml (source: action_api).
Den Commit macht die Action bzw. der Assistent; übernommen wird nur nach
Bestätigung.
"""
import argparse
import base64
import datetime
import io
import json
import os
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

import yaml

SOURCE = 'aufbereitet.jpg'
SOURCE_FRONT = 'aufbereitet-1.jpg'   # Bild mit Rückseite: Vorderseite (aufbereitet-2.jpg = Rückseite)
TARGET = 'coloriert.jpg'
META = 'bild.yml'
ALLOWED_ART = ('foto', 'foto-vom-foto')
DEFAULT_MODEL = 'gemini-2.5-flash-image'
SECRET = 'GEMINI_API_KEY'
API = 'https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent'
PROMPT = ('Colorize this black-and-white photograph with natural, historically plausible colors. '
          'Keep the image exactly as it is: same framing, same size and aspect ratio, same faces, '
          'shapes, edges, background and lighting. Do not add, remove, retouch, sharpen or restore anything. '
          'Only add color. Return only the image.')
HINT_PREFIX = 'Known facts about the colors in this photo (use them): '
MAX_HINT = 300
MAX_UPLOAD_PX = 1536
MAX_ASPECT_DIFF = 0.02
MIN_CORRELATION = 0.7
MAX_L_DEVIATION = 1.0          # in Stufen von 255

# ---------- Farbraum (sRGB D65 ↔ CIE Lab), ohne zusätzliche Bibliotheken außer numpy ----------

_M = [[0.4124564, 0.3575761, 0.1804375], [0.2126729, 0.7151522, 0.0721750], [0.0193339, 0.1191920, 0.9503041]]
_WHITE = (0.95047, 1.0, 1.08883)
_D = 6 / 29


def _np():
    import numpy
    return numpy


def rgb_to_lab(rgb):
    """rgb: Feld (…, 3) in 0..1 → Lab (L 0..100)."""
    np = _np()
    lin = np.where(rgb <= 0.04045, rgb / 12.92, ((rgb + 0.055) / 1.055) ** 2.4)
    xyz = lin @ np.array(_M).T / np.array(_WHITE)
    f = np.where(xyz > _D ** 3, np.cbrt(xyz), xyz / (3 * _D ** 2) + 4 / 29)
    return np.stack([116 * f[..., 1] - 16, 500 * (f[..., 0] - f[..., 1]), 200 * (f[..., 1] - f[..., 2])], axis=-1)


def _lab_to_linear(lab):
    np = _np()
    fy = (lab[..., 0] + 16) / 116
    f = np.stack([fy + lab[..., 1] / 500, fy, fy - lab[..., 2] / 200], axis=-1)
    xyz = np.where(f > _D, f ** 3, 3 * _D ** 2 * (f - 4 / 29)) * np.array(_WHITE)
    return xyz @ np.linalg.inv(np.array(_M)).T


def lab_to_rgb(lab):
    """Lab → rgb 0..1. Liegt eine Farbe außerhalb von sRGB, wird nur ihre Sättigung (a, b) verringert,
    nie die Helligkeit; so bleibt L erhalten."""
    np = _np()
    lab = lab.copy()
    lin = _lab_to_linear(lab)
    eps = 1e-6
    bad = ((lin < -eps) | (lin > 1 + eps)).any(axis=-1)
    if bad.any():
        lo, hi = np.zeros(bad.sum()), np.ones(bad.sum())
        sub = lab[bad]
        for _ in range(14):
            mid = (lo + hi) / 2
            trial = np.concatenate([sub[:, :1], sub[:, 1:] * mid[:, None]], axis=1)
            ok = ~(((t := _lab_to_linear(trial)) < -eps) | (t > 1 + eps)).any(axis=-1)
            lo, hi = np.where(ok, mid, lo), np.where(ok, hi, mid)
        lab[bad] = np.concatenate([sub[:, :1], sub[:, 1:] * lo[:, None]], axis=1)
        lin = _lab_to_linear(lab)
    lin = np.clip(lin, 0, 1)
    return np.where(lin <= 0.0031308, 12.92 * lin, 1.055 * lin ** (1 / 2.4) - 0.055)


def _array(img):
    np = _np()
    return np.asarray(img.convert('RGB'), dtype=np.float64) / 255


def lightness(img):
    return rgb_to_lab(_array(img))[..., 0]


# ---------- Bild ----------

def open_image(path):
    from PIL import Image, ImageOps
    img = Image.open(path)
    img.load()
    return ImageOps.exif_transpose(img).convert('RGB')


def correlation(base, proposal):
    """Ähnlichkeit des Bildaufbaus: Korrelation der Helligkeit auf 256 px Kantenlänge."""
    np = _np()
    size = (256, max(1, round(256 * base.height / base.width)))
    a, b = lightness(base.resize(size)).ravel(), lightness(proposal.resize(size)).ravel()
    if a.std() == 0 or b.std() == 0:
        return 0.0
    return float(np.corrcoef(a, b)[0, 1])


def transfer(base, proposal):
    """L aus base, a/b aus proposal (auf base-Größe skaliert). → (Bild, Prüfwerte)"""
    from PIL import Image
    np = _np()
    ar_b, ar_p = base.width / base.height, proposal.width / proposal.height
    aspect = abs(ar_p - ar_b) / ar_b
    if aspect > MAX_ASPECT_DIFF:
        raise SystemExit(f'Farbvorschlag hat ein anderes Seitenverhältnis ({proposal.width}×{proposal.height} statt '
                         f'{base.width}×{base.height}); verworfen.')
    corr = correlation(base, proposal)
    if corr < MIN_CORRELATION:
        raise SystemExit(f'Farbvorschlag weicht im Bildaufbau zu stark ab (Korrelation {corr:.2f} < {MIN_CORRELATION}); verworfen.')
    lab = rgb_to_lab(_array(base))
    lab_p = rgb_to_lab(_array(proposal.resize(base.size, Image.LANCZOS)))
    lab[..., 1:] = lab_p[..., 1:]
    rgb = np.clip(np.round(lab_to_rgb(lab) * 255), 0, 255).astype(np.uint8)
    return Image.fromarray(rgb, 'RGB'), {'correlation': round(corr, 3)}


def jpeg_bytes(img, quality=98):
    buf = io.BytesIO()
    img.save(buf, 'JPEG', quality=quality, subsampling=0)
    return buf.getvalue()


def l_deviation(a, b):
    """Mittlere Abweichung der Helligkeit in Stufen von 255."""
    np = _np()
    return float(np.abs(lightness(a) - lightness(b)).mean() * 255 / 100)


# ---------- Beschreibung und Sperren ----------

def load_meta(folder):
    path = Path(folder) / META
    if not path.is_file():
        raise SystemExit(f'{META} fehlt in {folder}: ohne Beschreibung (art, minderjaehrige) wird nicht coloriert.')
    data = yaml.safe_load(path.read_text(encoding='utf-8')) or {}
    if not isinstance(data, dict):
        raise SystemExit(f'{META} ist kein YAML-Objekt.')
    return data


def check_locks(meta, minors_exception=False):
    """Sperren (#452): keine Kinderbilder, keine Dokumente an externe Dienste.

    Ausnahme für Kinderbilder nur ausdrücklich (`minors_exception`) und nur, wenn
    `minderjaehrige: true` in bild.yml steht; fehlt die Angabe, bleibt gesperrt.
    """
    minors = meta.get('minderjaehrige')
    if minors is not False:
        if minors is True and minors_exception:
            pass
        elif minors is True:
            raise SystemExit('Gesperrt: In bild.yml steht „minderjaehrige: true“. Bilder mit Kindern oder Jugendlichen '
                             'werden nur mit ausdrücklicher Ausnahme (minors_exception) coloriert.')
        else:
            raise SystemExit('Gesperrt: In bild.yml steht nicht ausdrücklich „minderjaehrige: false“. Bilder mit Kindern '
                             'oder Jugendlichen werden nicht coloriert.')
    art = meta.get('art')
    if art not in ALLOWED_ART:
        raise SystemExit(f'Gesperrt: art „{art}“ – coloriert werden nur Fotos ({", ".join(ALLOWED_ART)}), '
                         'keine Dokumente.')


def add_processing(path, line):
    """Eintrag unter `bearbeitung` anhängen; Rest der Datei bleibt, wie er ist."""
    path = Path(path)
    text = path.read_text(encoding='utf-8')
    quoted = json.dumps(line, ensure_ascii=False)
    lines = text.splitlines(keepends=True)
    out, done = [], False
    i = 0
    while i < len(lines):
        ln = lines[i]
        m = re.match(r'^bearbeitung:\s*(\[\s*\])?\s*(#.*)?$', ln.rstrip('\n'))
        if m and not done:
            if m.group(1) is not None:
                out.append(f'bearbeitung:\n  - {quoted}\n')
                i += 1
            else:
                out.append(ln)
                i += 1
                while i < len(lines) and (lines[i].startswith((' ', '\t', '-')) or not lines[i].strip()):
                    out.append(lines[i])
                    i += 1
                while out and not out[-1].strip():
                    lines.insert(i, out.pop())
                indent = next((re.match(r'^(\s*)-', x).group(1) for x in reversed(out) if re.match(r'^\s*-', x)), '  ')
                out.append(f'{indent}- {quoted}\n')
            done = True
            continue
        out.append(ln)
        i += 1
    if not done:
        sep = '' if not text or text.endswith('\n') else '\n'
        out.append(f'{sep}bearbeitung:\n  - {quoted}\n')
    new = ''.join(out)
    try:
        data = yaml.safe_load(new) or {}
    except yaml.YAMLError:
        data = {}
    if not isinstance(data.get('bearbeitung'), list) or data['bearbeitung'][-1] != line:
        old = yaml.safe_load(text) or {}
        old['bearbeitung'] = list(old.get('bearbeitung') or []) + [line]
        new = yaml.safe_dump(old, allow_unicode=True, sort_keys=False, width=10 ** 6)
    path.write_text(new, encoding='utf-8')


# ---------- Gemini ----------

def model_for(base, wanted=None):
    if wanted:
        return wanted
    try:
        config = yaml.safe_load((Path(base) / 'ghostwriter.yml').read_text(encoding='utf-8')) or {}
    except OSError:
        config = {}
    service = (((config.get('ai_providers') or {}).get('services') or {}).get('google') or {})
    model = service.get('model') or ''
    return model if 'image' in model else DEFAULT_MODEL


def prompt_for(hint=None):
    hint = ' '.join((hint or '').split())
    return f'{PROMPT} {HINT_PREFIX}{hint}' if hint else PROMPT


def gemini_proposal(img, model, key, timeout=180, hint=None):
    """Farbvorschlag von Gemini. → (Bild, usageMetadata)"""
    from PIL import Image
    small = img.copy()
    small.thumbnail((MAX_UPLOAD_PX, MAX_UPLOAD_PX))
    body = {'contents': [{'parts': [{'text': prompt_for(hint)},
                                    {'inline_data': {'mime_type': 'image/jpeg',
                                                     'data': base64.b64encode(jpeg_bytes(small, 92)).decode()}}]}],
            'generationConfig': {'responseModalities': ['IMAGE']}}
    req = urllib.request.Request(API.format(model=model), data=json.dumps(body).encode(), method='POST',
                                 headers={'Content-Type': 'application/json', 'x-goog-api-key': key})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            data = json.loads(r.read())
    except urllib.error.HTTPError as e:
        detail = e.read().decode('utf-8', 'replace')[:400]
        raise SystemExit(f'Gemini meldet HTTP {e.code}: {detail}')
    for cand in data.get('candidates') or []:
        for part in ((cand.get('content') or {}).get('parts') or []):
            blob = part.get('inlineData') or part.get('inline_data')
            if blob and blob.get('data'):
                out = Image.open(io.BytesIO(base64.b64decode(blob['data'])))
                out.load()
                return out.convert('RGB'), data.get('usageMetadata') or {}
    reason = ', '.join(filter(None, [c.get('finishReason') for c in data.get('candidates') or []]
                              + [str((data.get('promptFeedback') or {}).get('blockReason') or '')]))
    raise SystemExit(f'Gemini hat kein Bild geliefert ({reason or "ohne Grund"}).')


def cost_entry(base, model, usage, folder, when):
    try:
        wf = yaml.safe_load((Path(__file__).resolve().parent.parent / 'workflow.yml').read_text(encoding='utf-8')) or {}
    except OSError:
        wf = {}
    cur = (wf.get('cost_tracking') or {}).get('project_currency') or 'EUR'
    path = Path(base) / 'costs' / 'project.yml'
    path.parent.mkdir(exist_ok=True)
    data = (yaml.safe_load(path.read_text(encoding='utf-8')) or {}) if path.is_file() else {'scope': 'project'}
    entries = data.get('entries') or []
    n = sum(1 for e in entries if str(e.get('activity_id', '')).startswith('act-colorize-')) + 1
    entry = {'activity_id': f'act-colorize-{n:03d}', 'occurred_at': when, 'source': 'action_api',
             'run_id': f'colorize/{Path(folder).name}', 'provider': 'google', 'model': model, 'activity_type': 'other',
             'currency': cur, 'cost_amount': None, 'cost_status': 'unavailable', 'image_units': 1,
             'note': f'Bild coloriert: {Path(folder).name} (Hintergrundlauf)'}
    if usage.get('promptTokenCount') is not None:
        entry['input_tokens'] = int(usage['promptTokenCount'])
    if usage.get('candidatesTokenCount') is not None:
        entry['output_tokens'] = int(usage['candidatesTokenCount'])
    data['entries'] = entries + [entry]
    path.write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False, width=10 ** 6), encoding='utf-8')
    return entry


# ---------- Ablauf ----------

def source_in(folder):
    """aufbereitet.jpg, bei Bildern mit Rückseite die Vorderseite aufbereitet-1.jpg. → Pfad oder None"""
    for name in (SOURCE, SOURCE_FRONT):
        if (Path(folder) / name).is_file():
            return Path(folder) / name
    return None


def resolve_folder(base, folder):
    base = Path(base).resolve()
    path = (base / folder).resolve()
    if base != path and base not in path.parents:
        raise SystemExit(f'{folder} liegt nicht im Buch.')
    if not path.is_dir():
        raise SystemExit(f'Bildordner {folder} gibt es nicht.')
    return path


def colorize(base, folder, *, proposal=None, tool=None, model=None, consent=False, replace=False, key=None, today=None,
             now=None, hint=None, minors_exception=False):
    folder = resolve_folder(base, folder)
    meta = load_meta(folder)
    check_locks(meta, minors_exception)
    exception = meta.get('minderjaehrige') is True
    hint = ' '.join((hint or '').split())
    if len(hint) > MAX_HINT:
        raise SystemExit(f'Farbhinweis zu lang (höchstens {MAX_HINT} Zeichen).')
    if hint and proposal:
        raise SystemExit('Ein Farbhinweis wirkt nur beim Aufruf bei Gemini, nicht mit --proposal.')
    src = source_in(folder)
    if src is None:
        raise SystemExit(f'{SOURCE} (bzw. {SOURCE_FRONT}) fehlt in {folder.name}: zuerst aufbereiten.')
    target = folder / TARGET
    if target.exists() and not replace:
        raise SystemExit(f'{TARGET} gibt es schon; zum Ersetzen „replace“ setzen (die alte Fassung bleibt in der Historie).')
    base_img = open_image(src)
    today = today or datetime.date.today()
    when = now or datetime.datetime.now().astimezone().isoformat(timespec='seconds')
    usage = None
    if proposal:
        prop_img = open_image(proposal)
        origin = f'Farbvorschlag {tool or Path(proposal).name}'
    else:
        if not consent:
            raise SystemExit('Ohne Einverständnis (consent) geht kein Bild an Google: Die Abgebildeten bzw. die Familie '
                             'müssen zugestimmt haben.')
        key = key or os.environ.get(SECRET)
        if not key:
            raise SystemExit(f'Kein Schlüssel: Secret {SECRET} hinterlegen (docs/DIENSTE-NUTZEN.md, '
                             '„API-Schlüssel als GitHub-Secret“).')
        model = model_for(base, model)
        prop_img, usage = gemini_proposal(base_img, model, key, hint=hint)
        origin = f'Farbvorschlag Google Gemini ({model}, Bildbearbeitung über eigenen Zugang, GitHub Action)'
    result, info = transfer(base_img, prop_img)
    data = jpeg_bytes(result)
    from PIL import Image
    saved = Image.open(io.BytesIO(data)).convert('RGB')
    dev = l_deviation(saved, base_img)
    if dev >= MAX_L_DEVIATION:
        raise SystemExit(f'Helligkeit weicht im Mittel um {dev:.2f}/255 ab (erlaubt unter {MAX_L_DEVIATION:g}); verworfen.')
    target.write_bytes(data)
    de = lambda x: f'{x:.2f}'.replace('.', ',')
    extra = ''
    if hint:
        extra += f'; Farbhinweis an das Modell: „{hint}“'
    if exception:
        extra += ('; Ausnahme: Minderjährige abgebildet, im Einzelfall ausdrücklich freigegeben '
                  '(Einverständnis der Abgebildeten bzw. der Familie)')
    line = (f'{TARGET}: {origin}, {today.strftime("%d.%m.%Y")}{extra}; nur Farbkanäle a/b übernommen, L-Kanal aus '
            f'{src.name}; mittlere L-Abweichung {de(dev)}/255, Bildaufbau-Korrelation {de(info["correlation"])}. '
            'Farben sind Annahme, kein Beleg')
    add_processing(folder / META, line)
    cost = cost_entry(base, model, usage, folder, when) if usage is not None else None
    rel = folder.relative_to(Path(base).resolve()).as_posix()
    return {'folder': rel, 'target': f'{rel}/{TARGET}', 'deviation': round(dev, 3), 'correlation': info['correlation'],
            'model': model, 'line': line, 'cost': cost}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('base')
    ap.add_argument('folder')
    ap.add_argument('--proposal', help='vorhandener Farbvorschlag statt Aufruf bei Gemini')
    ap.add_argument('--tool', help='Werkzeug des Farbvorschlags (für bearbeitung), mit --proposal')
    ap.add_argument('--model', help=f'Gemini-Bildmodell (Vorgabe: ai_providers.services.google.model, sonst {DEFAULT_MODEL})')
    ap.add_argument('--consent', action='store_true', help='Abgebildete bzw. Familie einverstanden; Bild geht an Google')
    ap.add_argument('--replace', action='store_true', help='vorhandenes coloriert.jpg ersetzen')
    ap.add_argument('--check', action='store_true', help='nur Sperren und Dateien prüfen, nichts senden')
    ap.add_argument('--hint', help='bekannte Farben als Hinweis an Gemini, z. B. „Die Fahne ist rot-weiß-rot.“')
    ap.add_argument('--minors-exception', action='store_true',
                    help='Ausnahme: Bild mit Kindern (minderjaehrige: true) trotzdem colorieren; Entscheidung des Benutzers')
    ap.add_argument('--json', action='store_true')
    a = ap.parse_args(argv)
    if a.check:
        folder = resolve_folder(a.base, a.folder)
        meta = load_meta(folder)
        check_locks(meta, a.minors_exception)
        src = source_in(folder)
        if src is None:
            raise SystemExit(f'{SOURCE} (bzw. {SOURCE_FRONT}) fehlt in {folder.name}: zuerst aufbereiten.')
        note = ' – Ausnahme: Minderjährige abgebildet' if meta.get('minderjaehrige') is True else ''
        print(f'✓ {folder.name}: darf coloriert werden ({src.name} vorhanden, keine Sperre){note}')
        return 0
    r = colorize(a.base, a.folder, proposal=a.proposal, tool=a.tool, model=a.model, consent=a.consent, replace=a.replace,
                 hint=a.hint, minors_exception=a.minors_exception)
    if a.json:
        print(json.dumps(r, ensure_ascii=False))
        return 0
    print(f'✓ Coloriert: {r["target"]} · mittlere L-Abweichung {r["deviation"]:.2f}/255 · Bildaufbau {r["correlation"]:.2f}')
    print(f'Commit-Nachricht: Bild coloriert: {Path(r["folder"]).name}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
