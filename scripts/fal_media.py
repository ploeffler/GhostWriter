#!/usr/bin/env python3
"""Medien-Aufträge bei fal.ai (#701): Bild, Video oder Ton über die Warteschlange von fal.ai, aufgerufen aus der Action „Medien erzeugen“.

Ablauf, wie er in chillyconcane/YAWA#440 erprobt ist (Modell `fal-ai/wan/v2.2-a14b/image-to-video/turbo`):
1. Auftrag an `https://queue.fal.run/<modell>` senden. Antwort: `request_id`. **Sofort sichern**, bevor gewartet wird.
2. Status über `https://queue.fal.run/<app>/requests/<id>/status` abfragen (`app` = die ersten zwei Teile des Modells, z. B. `fal-ai/wan`).
3. Ergebnis über `https://queue.fal.run/<app>/requests/<id>` holen; das Video steht unter `video.url`, Bilder unter `images[].url`.
4. Datei laden (Hosts `*.fal.media`, `fal.run`).
Ein Fehler nach dem Senden darf nie ein zweites, bezahltes Senden auslösen: gespeicherte `request_id` → nur abholen.

Der Schlüssel kommt aus der Umgebung (`FAL_KEY`, GitHub-Secret) und steht nie in Dateien oder Ausgaben. Der Kopf `Authorization: Key <FAL_KEY>` folgt der
fal-Dokumentation aus dem Gedächtnis; beim ersten echten Lauf prüfen (die Seiten waren bei der Umsetzung nicht erreichbar).
Dieses Modul ruft nichts auf, solange es nur importiert wird; Tests ersetzen `call` und `download`.
"""
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

BASE = 'https://queue.fal.run'
TIMEOUT = 60
ALLOWED_DOWNLOAD = ('fal.media', 'fal.run', 'fal.ai')


class FalError(Exception):
    pass


def app_of(model):
    parts = str(model).strip('/').split('/')
    if len(parts) < 2 or not all(parts):
        raise FalError(f'Ungültiges Modell {model!r} (erwartet wie fal-ai/wan/v2.2-a14b/image-to-video/turbo).')
    return '/'.join(parts[:2])


def call(url, data=None, key=None):
    """(Status, JSON). HTTP-Fehler kommen als Status zurück, nicht als Ausnahme; der Schlüssel erscheint nie in der Rückgabe."""
    headers = {'Content-Type': 'application/json'}
    if key:
        headers['Authorization'] = f'Key {key}'
    req = urllib.request.Request(url, data=None if data is None else json.dumps(data).encode('utf-8'), headers=headers,
                                 method='GET' if data is None else 'POST')
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            return r.status, json.loads(r.read() or b'{}')
    except urllib.error.HTTPError as e:
        return e.code, {'error': e.read().decode('utf-8', 'replace')[:300]}
    except (urllib.error.URLError, TimeoutError) as e:
        raise FalError(f'fal.ai ist nicht erreichbar: {getattr(e, "reason", e)}') from None


def submit(model, body, key):
    """Auftrag senden → request_id. Abgelehnt (z. B. content_policy_violation) oder Fehler: FalError, nie automatisch wiederholen."""
    status, data = call(f'{BASE}/{model.strip("/")}', body, key)
    if status >= 300 or not data.get('request_id'):
        raise FalError(f'fal.ai hat den Auftrag nicht angenommen (HTTP {status}): {str(data.get("error") or data)[:200]}')
    return str(data['request_id'])


def wait(model, request_id, key, timeout=1500, interval=5, sleep=time.sleep, clock=time.monotonic):
    """Bis COMPLETED warten. Läuft die Frist ab, bleibt der Auftrag beim Anbieter; die request_id reicht zum späteren Abholen."""
    base = f'{BASE}/{app_of(model)}/requests/{request_id}'
    end = clock() + timeout
    while True:
        status, data = call(base + '/status', None, key)
        if data.get('status') == 'COMPLETED':
            return
        if status >= 400 or data.get('status') not in ('IN_QUEUE', 'IN_PROGRESS'):
            raise FalError(f'Status {status}: {str(data)[:200]}')
        if clock() >= end:
            raise FalError('Zeit abgelaufen: der Auftrag läuft bei fal.ai weiter und wird beim nächsten Lauf abgeholt.')
        sleep(interval)


def result(model, request_id, key):
    status, data = call(f'{BASE}/{app_of(model)}/requests/{request_id}', None, key)
    if status >= 300:
        raise FalError(f'Ergebnis nicht abrufbar (HTTP {status}): {str(data.get("error") or data)[:200]}')
    return data


def media_urls(data):
    """[(Art, URL)] aus dem Ergebnis: `video.url`, `images[].url`, `image.url`, `audio.url`."""
    out = []
    for key, kind in (('video', 'video'), ('image', 'image'), ('audio', 'audio'), ('audio_file', 'audio')):
        v = data.get(key)
        if isinstance(v, dict) and v.get('url'):
            out.append((kind, v['url']))
    out += [('image', i['url']) for i in data.get('images') or [] if isinstance(i, dict) and i.get('url')]
    if not out:
        raise FalError('Kein Medium im Ergebnis (Felder: ' + ', '.join(sorted(data)[:8]) + ').')
    return out


def host_ok(url):
    u = urllib.parse.urlparse(url)
    return u.scheme == 'https' and any(u.hostname == h or (u.hostname or '').endswith('.' + h) for h in ALLOWED_DOWNLOAD)


def download(url, dest):
    if not host_ok(url):
        raise FalError('Download nur von https://*.fal.media bzw. fal.run (nicht: ' + (urllib.parse.urlparse(url).hostname or '?') + ').')
    dest = Path(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    urllib.request.urlretrieve(url, dest)   # noqa: S310 (Host oben geprüft)
    return dest


def api_key():
    key = os.environ.get('FAL_KEY', '')
    if not key:
        raise FalError('Kein Schlüssel: Secret FAL_KEY im Repository hinterlegen (docs/DIENSTE-NUTZEN.md, „API-Schlüssel als GitHub-Secret“).')
    return key
