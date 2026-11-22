#!/usr/bin/env python3
"""Ansicht „Alle Einstellungen“ (#299): aktueller Wert, Herkunft und wo man ihn ändert.

Die Liste entsteht aus schemas/ghostwriter.schema.json, damit neue Einstellungen
von selbst erscheinen. Je Einstellung:

  - Wert: eigener Wert im Buch (ghostwriter.yml), sonst aus der Bibliothek
    (assistant.yml), sonst die Vorgabe des Programms, sonst „–“.
  - Herkunft: „eigener Wert im Buch“, „aus der Bibliothek“, „Vorgabe“, „nicht gesetzt“.
  - Ändern: Formular (Befehl im Chat) oder „nur in der Datei“.

Nur lesend. Ausgabe als Markdown (auch im Widget-Modus, eigenes Widget folgt später):

  python scripts/render_view.py <buch> settings-overview
  python scripts/settings_overview.py <buch> [--group typesetting]
"""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCHEMA = ROOT / 'schemas' / 'ghostwriter.schema.json'

# Zustand und Inhalte, keine Einstellungen
SKIP = {('data_version',), ('characters',), ('structure',), ('workflow', 'current_phase'),
        ('workflow', 'current_chapter_id'), ('workflow', 'current_section_id'), ('project', 'status'),
        ('project', 'current_edition'), ('style', 'source')}

# Formular je Gruppe (Name wie in render_view.py FORMS); fehlt = nur in der Datei
GROUP_FORM = {'project': 'project-edit', 'ai_settings': 'rules', 'rules': 'rules',
              'workflow': 'project-settings', 'changes': 'project-settings', 'limits': 'project-settings',
              'ai_providers': 'providers-edit', 'ai_disclosure': 'ai-disclosure', 'publication': 'output',
              'print': 'output', 'cover': 'output', 'typesetting': 'output', 'analysis': 'analysis-settings'}
FORM_NAMES = {'project-edit': 'Projektdaten', 'project-settings': 'Einstellungen', 'rules': 'Grundregeln',
              'providers-edit': 'KI-Dienste', 'ai-disclosure': 'KI-Angabe', 'output': 'Ausgabe',
              'analysis-settings': 'Analyse-Einstellungen'}   # Befehle im Chat (docs/EINSTELLUNGEN.md)

# Einstellungen, die in keinem Formular vorkommen (bewusst nur in der Datei). Der Test meldet
# jede Schema-Einstellung ohne Formular, die hier nicht steht (#299).
FILE_ONLY = {
    'interface.language', 'updates.auto', 'images.style', 'images.credit_in_imprint', 'images.max_px',
    'limits.actions_minutes_warn_below', 'limits.actions_minutes_pause_below',
    'limits.pause_below_percent', 'limits.warn_below_percent', 'cover.back_blurb_position',
    'style.perspective', 'style.tense', 'style.address', 'style.register', 'style.tone', 'style.features',
    'style.avoid', 'style.sentence_length_avg', 'style.dialogue_share',
}

GROUPS = {'project': 'Buch', 'interface': 'Bedienung', 'ai_settings': 'Grundregeln für die KI', 'rules': 'Stufen der Grundregeln',
          'ai_providers': 'KI-Dienste', 'workflow': 'Ablauf', 'updates': 'Updates', 'changes': 'Übernehmen',
          'ai_disclosure': 'KI-Angabe', 'publication': 'Impressum', 'print': 'Druck', 'cover': 'Umschlag',
          'typesetting': 'Buchsatz', 'analysis': 'Analysen', 'style': 'Stilprofil', 'limits': 'Grenzen',
          'images': 'Bilder'}


def defaults():
    """Vorgaben des Programms, soweit es sie an einer Stelle festhält."""
    sys.path.insert(0, str(ROOT / 'scripts'))
    out = {'interface.language': 'de', 'updates.auto': True, 'changes.auto_merge': False}
    try:
        from render_view import TYPESETTING_DEFAULT
        out.update({f'typesetting.{k}': v for k, v in TYPESETTING_DEFAULT.items()})
    except Exception:
        pass
    for module, attr, group in (('limits', 'DEFAULT', 'limits'), ('ai_disclosure', 'DEFAULT', 'ai_disclosure')):
        try:
            values = getattr(__import__(module), attr)
            out.update({f'{group}.{k}': v for k, v in values.items() if v is not None})
        except Exception:
            pass
    try:
        from images import DEFAULT_MAX_PX
        out['images.max_px'] = DEFAULT_MAX_PX
    except Exception:
        pass
    return out


def leaves(schema=None):
    """(Pfad, Beschreibung) je Einstellung, Unterobjekte aufgelöst."""
    schema = schema or json.loads(SCHEMA.read_text(encoding='utf-8'))
    out = []

    def walk(node, path, inherited=''):
        if path in SKIP:
            return
        props = node.get('properties') if isinstance(node, dict) else None
        if props and node.get('type', 'object') == 'object' and len(path) < 2:
            for key, sub in props.items():
                walk(sub, path + (key,), node.get('description', ''))
        elif path:
            out.append(('.'.join(path), (node.get('description') or '').strip()))
    walk(schema, ())
    return out


def get(config, dotted):
    node = config
    for part in dotted.split('.'):
        if not isinstance(node, dict) or part not in node:
            return None, False
        node = node[part]
    return node, True


def library_value(dotted, profile):
    if dotted == 'interface.language' and profile.get('interface_language'):
        return profile['interface_language']
    if dotted.startswith('style.') and isinstance(profile.get('voice'), dict):
        value = profile['voice'].get(dotted.split('.', 1)[1])
        return value if value not in (None, '', []) else None
    return None


def form_for(dotted):
    if dotted in FILE_ONLY:
        return None
    return GROUP_FORM.get(dotted.split('.')[0])


def rows(config, profile=None, schema=None):
    """Je Einstellung: key, group, value, origin (book|library|default|unset), differs, form, description."""
    profile = profile or {}
    preset = defaults()
    out = []
    for dotted, description in leaves(schema):
        value, present = get(config, dotted)
        if present:
            origin = 'book'
        elif library_value(dotted, profile) is not None:
            value, origin = library_value(dotted, profile), 'library'
        elif dotted in preset:
            value, origin = preset[dotted], 'default'
        else:
            value, origin = None, 'unset'
        differs = origin == 'book' and dotted in preset and value != preset[dotted]
        out.append({'key': dotted, 'group': dotted.split('.')[0], 'value': value, 'origin': origin,
                    'differs': differs, 'form': form_for(dotted), 'description': description})
    return out


ORIGIN = {'book': 'eigener Wert im Buch', 'library': 'aus der Bibliothek', 'default': 'Vorgabe', 'unset': 'nicht gesetzt'}


def show(value):
    if value is None or value == '' or value == []:
        return '–'
    if isinstance(value, bool):
        return 'ja' if value else 'nein'
    text = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False)
    text = ' '.join(text.split())
    text = text if len(text) <= 60 else text[:57] + '…'
    return text.replace('|', '\\|')


def markdown(config, profile=None, group=None, title=None):
    data = [r for r in rows(config, profile) if not group or r['group'] == group]
    own = sum(r['origin'] == 'book' for r in data)
    lines = [f'### Alle Einstellungen{" · " + title if title else ""}', '',
             f'{len(data)} Einstellungen, davon {own} mit eigenem Wert im Buch. **Fett** = weicht von der Vorgabe ab. '
             'Nur lesend; geändert wird im genannten Formular.', '']
    for key in dict.fromkeys(r['group'] for r in data):
        lines += [f'#### {GROUPS.get(key, key)}', '', '| Einstellung | Wert | Herkunft | Ändern |', '|---|---|---|---|']
        for r in (x for x in data if x['group'] == key):
            value = show(r['value'])
            value = f'**{value}**' if r['differs'] else value
            form = FORM_NAMES.get(r['form'], r['form']) if r['form'] else 'nur in der Datei'
            lines.append(f'| `{r["key"]}` | {value} | {ORIGIN[r["origin"]]} | {form} |')
        lines.append('')
    return '\n'.join(lines)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('project')
    ap.add_argument('--group', help='nur diese Gruppe, z. B. typesetting')
    ap.add_argument('--json', action='store_true')
    a = ap.parse_args(argv)
    import yaml
    base = Path(a.project)
    config = yaml.safe_load((base / 'ghostwriter.yml').read_text(encoding='utf-8')) or {}
    profile_path = base / 'assistant.yml'
    profile = yaml.safe_load(profile_path.read_text(encoding='utf-8')) or {} if profile_path.is_file() else {}
    if a.json:
        print(json.dumps(rows(config, profile), ensure_ascii=False, indent=1, default=str))
    else:
        print(markdown(config, profile, a.group, (config.get('project') or {}).get('title')))


if __name__ == '__main__':
    main()
