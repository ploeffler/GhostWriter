#!/usr/bin/env python3
"""Erzeugt den kurzen Instanz-Einstieg und einzeln ladbare Anweisungen (#178).

Die vollständige START.md im Hauptrepository bleibt die zentrale Quelle.
Im Update wird vor dem Überschreiben aus dieser Quelle gerendert; niemals aus
bereits gekürztem Text. Keine Zeitstempel: gleiche Eingaben ergeben gleiche Dateien.
"""
import argparse
import json
import re
import sys
import unicodedata
from pathlib import Path
from string import Template

import yaml

MARKER = '<!-- GhostWriter: generierter Instanz-Einstieg, Format 1 -->'
DIRECTORY = 'docs/start'
# Eigener kurzer Einstieg für die Open-WebUI-Pipe (#204): nur Regeln, die dort gelten.
OPENWEBUI = f'{DIRECTORY}/einstieg-openwebui.md'
REPO = re.compile(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+')


def slug(title):
    title = title.split(' (')[0]
    title = unicodedata.normalize('NFKD', title).encode('ascii', 'ignore').decode().lower()
    return re.sub(r'[^a-z0-9]+', '-', title).strip('-')


def sections(source):
    """Gliedert nur echte Überschriften, keine Beispiele innerhalb von Codeblöcken."""
    result, title, lines, fence = [], 'Start', [], None
    for line in source.splitlines(keepends=True):
        match = re.match(r'^\s*(`{3,}|~{3,})', line)
        if match:
            delimiter = match[1][0]
            if fence is None:
                fence = delimiter
            elif fence == delimiter:
                fence = None
        heading = re.match(r'^#{2,3} (.+?)\s*$', line) if fence is None else None
        if heading:
            if lines:
                result.append((title, ''.join(lines)))
            title, lines = heading[1], []
        lines.append(line)
    if lines:
        result.append((title, ''.join(lines)))
    return result


def module_links(text):
    # Module liegen zwei Ebenen unter der Repository-Wurzel. Nur Markdown- und
    # Bildpfade anpassen; Dateinamen in Codebeispielen bleiben unverändert.
    def replace(match):
        target = match[1]
        if re.match(r'[a-zA-Z][a-zA-Z0-9+.-]*:', target) or target.startswith(('#', '/')):
            return match[0]
        return '](' + '../../' + target + ')'
    text = re.sub(r'\]\(([^)\s]+)\)', replace, text)
    return re.sub(r'(src|srcset)="(assets/[^\"]+)"', r'\1="../../\2"', text)


def render(source, template, *, repo, branch, default_branch, config, profile=None,
           library_present=False, openwebui_template=None):
    if not isinstance(config, dict) or (profile is not None and not isinstance(profile, dict)):
        raise ValueError('Projekt und Assistenten-Profil müssen YAML-Objekte sein.')
    if MARKER in source:
        raise ValueError('Vollständige START.md aus dem Hauptrepository benötigt; Quelle ist bereits generiert.')
    if not REPO.fullmatch(repo or ''):
        raise ValueError('Repository-Name fehlt oder ist ungültig (owner/repo).')
    if not branch or not default_branch or any(c in branch + default_branch for c in '\r\n'):
        raise ValueError('Branch und Standard-Branch müssen ausdrücklich angegeben sein.')
    profile = profile or {}
    if profile.get('repo') and profile['repo'].lower() != repo.lower():
        raise ValueError('Repository im Assistenten-Profil passt nicht zum Update-Ziel.')
    startup = profile.get('startup') or {}
    if not isinstance(startup, dict):
        raise ValueError('startup muss ein Objekt sein.')
    client = startup.get('client') or 'unknown'
    tools = startup.get('tools') or {}
    if not isinstance(tools, dict):
        raise ValueError('startup.tools muss ein Objekt sein.')
    if client not in ('unknown', 'openwebui', 'chatgpt', 'claude', 'text'):
        raise ValueError('Unbekannter startup.client im Assistenten-Profil.')
    for key, value in tools.items():
        if key not in ('read_start', 'read_file') or not isinstance(value, str) or not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*', value):
            raise ValueError('Ungültige Werkzeugzuordnung in startup.tools.')
    language = ((config.get('interface') or {}).get('language') or profile.get('interface_language') or 'de')
    chapters = (config.get('structure') or {}).get('chapters') or []
    phase = (config.get('workflow') or {}).get('current_phase')
    book = branch.startswith('buch/') or bool(chapters)
    ready = bool(chapters) or bool(phase and phase != 'wizard')
    if not book:
        ready = bool(profile) or library_present
    mode = 'resume' if ready else 'setup'
    outputs, entries = {}, []
    for title, text in sections(source):
        path = f'{DIRECTORY}/{slug(title)}.md'
        if path in outputs:
            raise ValueError(f'Doppelte Anweisungsdatei: {path}')
        outputs[path] = module_links(text)
        entries.append(f'- [{title}]({Path(path).name})')
    # Stabile Einstiegspunkte werden explizit geprüft statt still falsche Links zu erzeugen.
    required = ['sprache-der-bedienung', 'nachrichten-aus-den-vorlagen', 'schreiben-ins-repository',
                'freigaben', '1-start-und-github-onboarding', 'neues-buch', 'programmdateien-und-updates']
    for name in required:
        if f'{DIRECTORY}/{name}.md' not in outputs:
            raise ValueError(f'Anweisung fehlt in der zentralen START.md: {name}')
    outputs[f'{DIRECTORY}/index.md'] = '# Ausführliche GhostWriter-Anweisungen\n\nNur die zur aktuellen Aufgabe passende Datei laden.\n\n' + '\n'.join(entries) + '\n'
    values = dict(MARKER=MARKER, REPO=repo, BRANCH=branch, DEFAULT_BRANCH=default_branch,
                  LANGUAGE=language, CLIENT=client, MODE=mode,
                  KIND='book' if book else 'library',
                  READ_START=tools.get('read_start', 'nicht konfiguriert / not configured'),
                  READ_FILE=tools.get('read_file', 'nicht konfiguriert / not configured'),
                  PROFILE='assistant.yml' if profile else 'nicht vorhanden / absent')
    outputs['START.md'] = Template(template).substitute(values)
    if openwebui_template is not None:
        if OPENWEBUI in outputs:
            raise ValueError(f'Doppelte Anweisungsdatei: {OPENWEBUI}')
        outputs[OPENWEBUI] = Template(openwebui_template).substitute(values)
    return outputs


def template_names(language):
    """Vorlagen für Bediensprache: (START.md, Open-WebUI-Einstieg)."""
    name = 'en' if (language or 'de').split('-')[0] == 'en' else 'de'
    return f'templates/start/{name}.md', f'templates/start/openwebui.{name}.md'


def generate(base, *, repo, branch, default_branch, profile=None, library_present=False):
    base = Path(base)
    manifest_path = base / 'ghostwriter-manifest.yml'
    manifest = yaml.safe_load(manifest_path.read_text(encoding='utf-8')) or {} if manifest_path.is_file() else {}
    if ((manifest.get('upstream') or {}).get('repo', '').lower() == repo.lower()
            and branch == default_branch):
        raise ValueError('START.md auf dem Standard-Branch des Hauptrepositorys bleibt die vollständige Quelle.')
    source = (base / 'START.md').read_text(encoding='utf-8')
    cfg = yaml.safe_load((base / 'ghostwriter.yml').read_text(encoding='utf-8')) or {} if (base / 'ghostwriter.yml').is_file() else {}
    language = ((cfg.get('interface') or {}).get('language') or (profile or {}).get('interface_language') or 'de')
    main_name, openwebui_name = template_names(language)
    template = (base / main_name).read_text(encoding='utf-8')
    openwebui = base / openwebui_name
    outputs = render(source, template, repo=repo, branch=branch, default_branch=default_branch,
                     config=cfg, profile=profile,
                     library_present=library_present or (base / 'library.json').is_file(),
                     openwebui_template=openwebui.read_text(encoding='utf-8') if openwebui.is_file() else None)
    for name, text in outputs.items():
        path = base / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding='utf-8')
    return outputs


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    parser.add_argument('base')
    parser.add_argument('--repo', required=True)
    parser.add_argument('--branch', required=True)
    parser.add_argument('--default-branch', required=True)
    parser.add_argument('--profile-json', help='Profil vom Standard-Branch als JSON-Datei; keine Secrets')
    parser.add_argument('--library-present', action='store_true',
                        help='Update hat bereits Buchbranches in der Bibliothek erkannt')
    args = parser.parse_args(argv)
    try:
        if args.profile_json:
            profile = json.loads(Path(args.profile_json).read_text(encoding='utf-8'))
        else:
            path = Path(args.base, 'assistant.yml')
            profile = yaml.safe_load(path.read_text(encoding='utf-8')) if path.is_file() else None
        outputs = generate(args.base, repo=args.repo, branch=args.branch,
                           default_branch=args.default_branch, profile=profile,
                           library_present=args.library_present)
    except (ValueError, OSError, yaml.YAMLError) as error:
        print(f'✗ START.md nicht erzeugt: {error}')
        return 1
    print(f'✓ START.md und {len(outputs) - 1} Anweisungsdateien erzeugt')
    return 0


if __name__ == '__main__':
    sys.exit(main())
