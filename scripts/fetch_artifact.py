#!/usr/bin/env python3
"""Holt die Dateien eines Artifacts aus einem Lauf einer GitHub Action (#260).

Aufruf:
  python scripts/fetch_artifact.py <owner/repo> --run <lauf-id> [--name manuskript] [--out ordner] [--wait]

Für „Manuskript ausgeben“: Die Action „Manuskript ausgeben“ (manuscript.yml) baut das
PDF und lädt es als Artifact `manuskript` hoch. Der Chat holt es damit ab und übergibt
die Datei (Claude, Codex: als Datei im Chat bzw. im Arbeitsordner). Der Buchtext wird
nie als Chatnachricht ausgegeben (START.md, „Kein ganzes Buch im Chat“).

--wait   wartet, bis der Lauf fertig ist (alle 15 s, höchstens 20 Minuten).

Zugriff: über die GitHub-CLI (`gh api`), sonst über GH_TOKEN bzw. GITHUB_TOKEN aus der
Umgebung. Der Token wird nie ausgegeben. Ausgabe: je Datei eine Zeile `✓ <pfad>`;
Exit-Code 1, wenn der Lauf fehlschlug oder das Artifact fehlt bzw. abgelaufen ist.
"""
import argparse
import io
import json
import os
import shutil
import subprocess
import sys
import time
import urllib.request
import zipfile
from pathlib import Path

API = 'https://api.github.com'


def _token():
    return os.environ.get('GH_TOKEN') or os.environ.get('GITHUB_TOKEN')


def get(path, raw=False):
    """GET auf die REST-API; raw=True liefert Bytes (Zip), sonst JSON."""
    if shutil.which('gh'):
        cmd = ['gh', 'api', path] + (['-H', 'Accept: application/vnd.github+json'] if not raw else [])
        out = subprocess.run(cmd, capture_output=True, check=False)
        if out.returncode != 0:
            raise SystemExit(f'GitHub: {out.stderr.decode("utf-8", "replace").strip() or "Fehler"} ({path})')
        return out.stdout if raw else json.loads(out.stdout)
    token = _token()
    if not token:
        raise SystemExit('Kein Zugriff: weder gh noch GH_TOKEN/GITHUB_TOKEN vorhanden.')
    req = urllib.request.Request(API + '/' + path.lstrip('/'))
    req.add_unredirected_header('Authorization', f'Bearer {token}')   # nicht an den Speicher-Link weitergeben
    req.add_header('Accept', 'application/vnd.github+json')
    with urllib.request.urlopen(req, timeout=120) as resp:
        data = resp.read()
    return data if raw else json.loads(data)


def pick(artifacts, name):
    """Das passende, nicht abgelaufene Artifact oder None."""
    for a in artifacts:
        if a.get('name') == name and not a.get('expired'):
            return a
    return None


def extract(data, out):
    """Zip-Inhalt (nur Dateien, ohne Pfade) nach out; gibt die Pfade zurück."""
    out.mkdir(parents=True, exist_ok=True)
    files = []
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        for info in z.infolist():
            if info.is_dir():
                continue
            target = out / Path(info.filename).name   # keine Unterordner, kein ../
            target.write_bytes(z.read(info))
            files.append(target)
    return files


def main(argv):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('repo')
    ap.add_argument('--run', required=True, type=int)
    ap.add_argument('--name', default='manuskript')
    ap.add_argument('--out', default='.')
    ap.add_argument('--wait', action='store_true')
    args = ap.parse_args(argv[1:])
    base = f'repos/{args.repo}/actions/runs/{args.run}'

    deadline = time.time() + 20 * 60
    while True:
        run = get(base)
        if run.get('status') == 'completed' or not args.wait:
            break
        if time.time() > deadline:
            print(f'✗ Lauf {args.run} ist nach 20 Minuten noch nicht fertig: {run.get("html_url")}')
            return 1
        time.sleep(15)
    if run.get('status') != 'completed':
        print(f'✗ Lauf {args.run} läuft noch ({run.get("status")}): {run.get("html_url")}')
        return 1
    if run.get('conclusion') != 'success':
        print(f'✗ Lauf {args.run} ist fehlgeschlagen ({run.get("conclusion")}): {run.get("html_url")}')
        return 1
    art = pick(get(base + '/artifacts').get('artifacts') or [], args.name)
    if not art:
        print(f'✗ Kein Artifact „{args.name}“ am Lauf (abgelaufen oder nicht erzeugt): {run.get("html_url")}')
        return 1
    for f in extract(get(f'repos/{args.repo}/actions/artifacts/{art["id"]}/zip', raw=True), Path(args.out)):
        print(f'✓ {f}')
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
