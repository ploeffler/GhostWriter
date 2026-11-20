#!/usr/bin/env python3
"""Prüfschleife vor einem Pull Request im Programm-Repository (#390).

Führt die festen Prüfschritte nacheinander aus und bricht beim ersten harten
Fehler ab. Ausgabe ist ein Markdown-Bericht, der in die PR-Beschreibung passt:
je Schritt bestanden / nicht bestanden / übersprungen / nicht ausgeführt,
Gesamturteil, eine eigene Zeile „Abnahme im Buch“ und offene Lücken.

  python3 scripts/verify.py                      # alle Schritte, Vergleich mit origin/main
  python3 scripts/verify.py --skip tests         # z. B. wenn die Tests gerade liefen
  python3 scripts/verify.py --abnahme geprüft --abnahme-beleg "chillyconcane/YAWA, 0.7.0, Umschlag gebaut"

Die Secret-Suche meldet nur Muster und Fundstelle, niemals den gefundenen Wert.
Die Durchsicht des Diffs (ungewollte Änderungen, Fehlerbehandlung, Randfälle)
bleibt Handarbeit; der Bericht führt sie als offenen Punkt.
"""
import argparse
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PY = sys.executable

ABNAHME = ('geprüft', 'fehlgeschlagen', 'nicht durchgeführt', 'entfällt')

# Muster für die Secret-Suche: (Name, regulärer Ausdruck). Nur Name und Fundstelle werden gemeldet.
SECRET_PATTERNS = [
    ('GitHub-Token', re.compile(r'\b(gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{40,})\b')),
    ('Anthropic-Schlüssel', re.compile(r'\bsk-ant-[A-Za-z0-9_-]{20,}')),
    ('OpenAI-Schlüssel', re.compile(r'\bsk-(proj-)?[A-Za-z0-9]{32,}')),
    ('Google-API-Schlüssel', re.compile(r'\bAIza[0-9A-Za-z_-]{35}\b')),
    ('AWS-Zugangsschlüssel', re.compile(r'\b(AKIA|ASIA)[0-9A-Z]{16}\b')),
    ('Slack-Token', re.compile(r'\bxox[abposr]-[A-Za-z0-9-]{10,}')),
    ('Privater Schlüssel', re.compile(r'-----BEGIN (RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----')),
    ('Zugangsdaten in URL', re.compile(r'https?://[^/\s:@]+:[^/\s@]{6,}@')),
]


def run(cmd, env=None):
    r = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, env=env)
    return r.returncode, (r.stdout + r.stderr).strip()


def tail(text, n=3):
    lines = [l for l in text.splitlines() if l.strip()]
    return ' / '.join(lines[-n:])[:300]


def step_tests(args):
    env = dict(os.environ, GITHUB_REPOSITORY=os.environ.get('GITHUB_REPOSITORY', 'ploeffler/GhostWriter'))
    code, out = run([PY, '-m', 'unittest', 'discover', '-s', 'tests', '-p', 'test_*.py'], env)
    m = re.search(r'Ran (\d+) tests', out)
    return ('ok' if code == 0 else 'fail'), (f'{m.group(1)} Tests' if m else '') + ('' if code == 0 else f': {tail(out)}')


def step_docs(args):
    cmd = [PY, 'scripts/check_docs.py'] + (['--ui', args.ui] if args.ui else [])
    code, out = run(cmd)
    return ('ok' if code == 0 else 'fail'), ('mit UI-Abgleich' if args.ui else 'ohne UI-Abgleich') + \
        ('' if code == 0 else f': {tail(out)}')


def step_site(args):
    try:
        import bs4, markdown  # noqa: F401,E401
    except ImportError:
        return 'skip', 'Abhängigkeiten fehlen (scripts/docsite/requirements.txt)'
    for cmd in (['scripts/build_docs_site.py'], ['scripts/build_docs_site.py', '--check']):
        code, out = run([PY] + cmd)
        if code != 0:
            return 'fail', tail(out)
    return 'ok', 'aufgebaut und geprüft'


def step_program(args):
    code, out = run([PY, 'scripts/library.py', 'check-program', '--namespace', 'refs/heads'])
    return ('ok' if code == 0 else 'fail'), ('' if code == 0 else tail(out))


def added_lines(base):
    """(Datei, Zeilennummer, Text) aller hinzugefügten Zeilen gegenüber base."""
    code, out = run(['git', 'diff', '--unified=0', '--no-color', f'{base}...HEAD'])
    if code != 0:
        code, out = run(['git', 'diff', '--unified=0', '--no-color', base])
    if code != 0:
        raise RuntimeError(tail(out))
    path, line = None, 0
    for raw in out.splitlines():
        if raw.startswith('+++ '):
            path = raw[6:] if raw.startswith('+++ b/') else None
        elif raw.startswith('@@'):
            m = re.search(r'\+(\d+)', raw)
            line = int(m.group(1)) if m else 0
        elif raw.startswith('+') and path:
            yield path, line, raw[1:]
            line += 1


def scan_secrets(lines):
    """Fundstellen als (Datei, Zeile, Mustername); nie der Wert selbst."""
    return [(p, n, name) for p, n, text in lines for name, rx in SECRET_PATTERNS if rx.search(text)]


def step_secrets(args):
    try:
        hits = scan_secrets(added_lines(args.base))
    except RuntimeError as e:
        return 'fail', f'Diff gegen {args.base} nicht lesbar: {e}'
    if hits:
        return 'fail', '; '.join(f'{name} in {p}:{n}' for p, n, name in hits[:10])
    return 'ok', f'hinzugefügte Zeilen gegen {args.base}'


def step_diffcheck(args):
    code, out = run(['git', 'diff', '--check', f'{args.base}...HEAD'])
    return ('ok' if code == 0 else 'fail'), ('' if code == 0 else tail(out))


STEPS = [
    ('tests', 'Tests', step_tests),
    ('docs', 'Doku-Prüfung (check_docs)', step_docs),
    ('site', 'Website lokal bauen', step_site),
    ('program', 'Programm-Repository sauber (check-program)', step_program),
    ('secrets', 'Secret-Suche im Diff', step_secrets),
    ('diffcheck', 'Leerzeichen und Konfliktmarker (git diff --check)', step_diffcheck),
]
LABEL = {'ok': '✅ bestanden', 'fail': '❌ nicht bestanden', 'skip': '⏭️ übersprungen', 'todo': '– nicht ausgeführt'}


def verify(args, steps=STEPS):
    results, stopped = [], False
    for key, title, fn in steps:
        if stopped:
            results.append((title, 'todo', 'nach vorherigem Fehler abgebrochen'))
        elif key in args.skip:
            results.append((title, 'skip', 'ausdrücklich ausgelassen'))
        else:
            state, detail = fn(args)
            results.append((title, state, detail))
            stopped = state == 'fail'
    return results


def report(args, results):
    ready = all(s in ('ok', 'skip') for _, s, _ in results)
    out = ['## Prüfbericht', '', '| Schritt | Ergebnis | Hinweis |', '|---|---|---|']
    out += [f'| {t} | {LABEL[s]} | {d or ""} |' for t, s, d in results]
    out += ['', f'**Gesamturteil: {"bereit für PR" if ready else "nicht bereit"}**', '']
    beleg = f' ({args.abnahme_beleg})' if args.abnahme_beleg else ''
    out += [f'Abnahme im Buch: {args.abnahme}{beleg}']
    nxt = args.next or ('Pull Request anlegen; Merge erst nach grünem `validate`' if ready
                        else 'ersten fehlgeschlagenen Schritt beheben und erneut prüfen')
    out += [f'Nächster erlaubter Schritt: {nxt}', '', '**Offene Lücken**', '',
            '- Durchsicht des Diffs von Hand: ungewollte Änderungen, Fehlerbehandlung, Randfälle']
    skipped = [t for t, s, _ in results if s == 'skip']
    if skipped:
        out.append(f'- Ausgelassen: {", ".join(skipped)}')
    if args.abnahme in ('nicht durchgeführt', 'fehlgeschlagen'):
        out.append('- Abnahme in einer echten Bibliothek steht aus; grüne Tests ersetzen sie nicht')
    out.append('- Doku-Checkliste (docs/DOKUMENTATION-PFLEGE.md, „Prüfbericht vor dem Pull Request“) von Hand abhaken')
    return '\n'.join(out) + '\n', ready


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--base', default='origin/main', help='Vergleichsstand für Diff und Secret-Suche')
    ap.add_argument('--ui', help='Ordner mit ghostwriter-ui für check_docs --ui')
    ap.add_argument('--skip', action='append', default=[], choices=[k for k, _, _ in STEPS])
    ap.add_argument('--abnahme', choices=ABNAHME, default='nicht durchgeführt')
    ap.add_argument('--abnahme-beleg', default='', help='Bibliothek, Programmversion, Beleg')
    ap.add_argument('--next', default='', help='nächster erlaubter Schritt, falls abweichend')
    ap.add_argument('--out', type=Path, help='Bericht zusätzlich in diese Datei schreiben')
    args = ap.parse_args(argv)
    text, ready = report(args, verify(args))
    print(text, end='')
    if args.out:
        args.out.write_text(text, encoding='utf-8')
    return 0 if ready else 1


if __name__ == '__main__':
    sys.exit(main())
