#!/usr/bin/env python3
"""Ansicht „Alle Einstellungen“ (#299): aktueller Wert, Herkunft und wo man ihn ändert.

Seiten (render_view.py <ordner> settings-overview [wo]):

  - Buch (ohne Angabe oder Gruppe wie `typesetting`): alle Einstellungen aus
    schemas/ghostwriter.schema.json. Wert und Herkunft: eigener Wert im Buch, sonst aus
    der Bibliothek (assistant.yml), sonst Vorgabe des Programms, sonst „nicht gesetzt“.
    Dazu die Serie des Buchs und Abschnitte, deren Faktencheck vom Buch abweicht.
  - `bibliothek` / `library`: das Profil assistant.yml (schemas/assistant.schema.json).
  - `serie <ser-id>` / `series <ser-id>`: Angaben der Serie (series/<id>/series.yml).
  - `sammelband <ser-id>` / `omnibus <ser-id>`: eigene Satz- und Impressumsangaben des
    Sammelbands, sonst die Vorgabe.

Je Einstellung: Formular (Befehl im Chat) oder „nur in der Datei“. Die Listen entstehen aus
den Schemas, neue Einstellungen erscheinen von selbst. Nur lesend.

Ausgabe: Markdown (`markdown`), Widget-Werte (`widget_values`, Vorlage `einstellungen`)
oder JSON (`python scripts/settings_overview.py <ordner> --json`).
"""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCHEMAS = ROOT / 'schemas'

# Zustand und Inhalte, keine Einstellungen
SKIP = {('data_version',), ('characters',), ('structure',), ('workflow', 'current_phase'),
        ('workflow', 'current_chapter_id'), ('workflow', 'current_section_id'), ('project', 'status'),
        ('project', 'current_edition'), ('style', 'source')}

# Formular je Gruppe (Schlüssel aus FORM_NAMES); fehlt = nur in der Datei
GROUP_FORM = {'project': 'project-edit', 'ai_settings': 'rules', 'rules': 'rules',
              'workflow': 'project-settings', 'changes': 'project-settings', 'limits': 'project-settings',
              'ai_providers': 'providers-edit', 'ai_disclosure': 'ai-disclosure', 'publication': 'output',
              'print': 'output', 'cover': 'output', 'typesetting': 'output', 'analysis': 'analysis-settings'}

# Einstellungen, die in keinem Formular vorkommen (bewusst nur in der Datei). Der Test meldet
# jede Schema-Einstellung ohne Formular, die hier nicht steht (#299).
FILE_ONLY = {
    'interface.language', 'updates.auto', 'images.style', 'images.credit_in_imprint', 'images.max_px',
    'limits.actions_minutes_warn_below', 'limits.actions_minutes_pause_below',
    'limits.actions_budget_monthly', 'limits.actions_minutes_included', 'limits.actions_price_per_minute',   # #787: Formularfeld folgt mit der UI-Vorlage
    'limits.actions_warn_used_percent', 'limits.actions_pause_used_percent',
    'limits.pause_below_percent', 'limits.warn_below_percent', 'cover.back_blurb_position',
    'style.perspective', 'style.tense', 'style.address', 'style.register', 'style.tone', 'style.features',
    'style.avoid', 'style.sentence_length_avg', 'style.dialogue_share', 'analysis.auto_after_chapter',
}

# Bibliothek (assistant.yml): Formular bzw. Chatbefehl je Feld
PROFILE_FORM = {'git': 'profile', 'author': 'profile', 'voice': 'profile', 'display': 'display', 'answers': 'answers'}
PROFILE_SKIP = {'format', 'repo', 'skill'}
PROFILE_DEFAULTS = {'interface_language': 'de', 'work_modes': 'ask', 'display': 'uebersichtlich', 'answers': 'einfach',
                    'answer_style': 'standard', 'answer_backup': 'vor_antwort'}
SERIES_FIELDS = ['title', 'subtitle', 'kind', 'description', 'issn', 'also_in_series']
OMNIBUS_GROUPS = ['title', 'subtitle', 'keep_matter', 'foreword', 'afterword', 'formats', 'publication', 'typesetting']

TEXT = {
    'de': {
        'title': 'Alle Einstellungen', 'library': 'Bibliothek', 'series': 'Serie', 'omnibus': 'Sammelband',
        'intro': '{n} Einstellungen, davon {own} mit eigenem Wert. **Fett** = weicht von der Vorgabe ab. Nur lesend; '
                 'geändert wird im genannten Formular.',
        'head': '| Einstellung | Wert | Herkunft | Ändern |', 'file_only': 'nur in der Datei',
        'yes': 'ja', 'no': 'nein', 'sections': 'Abweichend vom Buch',
        'sections_intro': 'Abschnitte, deren Faktencheck von der Vorgabe des Buchs ({default}) abweicht.',
        'origin': {'book': 'eigener Wert im Buch', 'library': 'aus der Bibliothek', 'default': 'Vorgabe',
                   'unset': 'nicht gesetzt', 'own': 'eigener Wert', 'series': 'aus der Serie',
                   'omnibus': 'nur dieser Sammelband', 'section': 'nur dieser Abschnitt'},
        'forms': {'project-edit': 'Projektdaten', 'project-settings': 'Einstellungen', 'rules': 'Grundregeln',
                  'providers-edit': 'KI-Dienste', 'ai-disclosure': 'KI-Angabe', 'output': 'Ausgabe',
                  'analysis-settings': 'Analyse-Einstellungen', 'profile': 'Profil', 'display': 'Darstellung: …',
                  'answers': 'Erweiterte Antworten an/aus', 'series-edit': 'Serie bearbeiten',
                  'omnibus-edit': 'Sammelband', 'section-edit': 'Abschnitt (Faktencheck)'},
        'groups': {'project': 'Buch', 'interface': 'Bedienung', 'ai_settings': 'Grundregeln für die KI',
                   'rules': 'Stufen der Grundregeln', 'ai_providers': 'KI-Dienste', 'workflow': 'Ablauf',
                   'updates': 'Updates', 'changes': 'Übernehmen', 'ai_disclosure': 'KI-Angabe',
                   'publication': 'Impressum', 'print': 'Druck', 'cover': 'Umschlag', 'typesetting': 'Buchsatz',
                   'analysis': 'Analysen', 'style': 'Stilprofil', 'limits': 'Grenzen', 'images': 'Bilder',
                   'series': 'Serie', 'profile': 'Profil', 'omnibus': 'Sammelband'},
    },
    'en': {
        'title': 'All settings', 'library': 'Library', 'series': 'Series', 'omnibus': 'Omnibus',
        'intro': '{n} settings, {own} with an own value. **Bold** = differs from the default. Read-only; '
                 'change them in the named form.',
        'head': '| Setting | Value | Origin | Change in |', 'file_only': 'file only',
        'yes': 'yes', 'no': 'no', 'sections': 'Different from the book',
        'sections_intro': 'Sections whose fact check differs from the book default ({default}).',
        'origin': {'book': 'own value in the book', 'library': 'from the library', 'default': 'default',
                   'unset': 'not set', 'own': 'own value', 'series': 'from the series',
                   'omnibus': 'this omnibus only', 'section': 'this section only'},
        'forms': {'project-edit': 'Project data', 'project-settings': 'Settings', 'rules': 'Ground rules',
                  'providers-edit': 'AI services', 'ai-disclosure': 'AI disclosure', 'output': 'Output',
                  'analysis-settings': 'Analysis settings', 'profile': 'Profile', 'display': 'Display: …',
                  'answers': 'Extended answers on/off', 'series-edit': 'Edit series',
                  'omnibus-edit': 'Omnibus', 'section-edit': 'Section (fact check)'},
        'groups': {'project': 'Book', 'interface': 'Interface', 'ai_settings': 'AI ground rules',
                   'rules': 'Ground rule levels', 'ai_providers': 'AI services', 'workflow': 'Workflow',
                   'updates': 'Updates', 'changes': 'Merging', 'ai_disclosure': 'AI disclosure',
                   'publication': 'Imprint', 'print': 'Print', 'cover': 'Cover', 'typesetting': 'Typesetting',
                   'analysis': 'Analyses', 'style': 'Style profile', 'limits': 'Limits', 'images': 'Images',
                   'series': 'Series', 'profile': 'Profile', 'omnibus': 'Omnibus'},
    },
}
FORM_NAMES = TEXT['de']['forms']   # Schlüssel der Formulare (Test, render_view)
OWN = ('book', 'own', 'omnibus', 'section')


def t(language):
    return TEXT['en' if language == 'en' else 'de']


def schema(name):
    return json.loads((SCHEMAS / f'{name}.schema.json').read_text(encoding='utf-8'))


def defaults():
    """Vorgaben des Programms, soweit es sie an einer Stelle festhält."""
    sys.path.insert(0, str(ROOT / 'scripts'))
    out = {'interface.language': 'de', 'updates.auto': True, 'changes.auto_merge': False,
           'workflow.fact_checking_default': 'optional'}
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


def leaves(node=None, skip=SKIP, depth=2):
    """(Pfad, Beschreibung) je Einstellung; Unterobjekte bis `depth` Ebenen aufgelöst."""
    node = node or schema('ghostwriter')
    out = []

    def walk(sub, path):
        if path in skip:
            return
        props = sub.get('properties') if isinstance(sub, dict) else None
        if props and sub.get('type', 'object') == 'object' and len(path) < depth:
            for key, child in props.items():
                walk(child, path + (key,))
        elif path:
            out.append(('.'.join(path), (sub.get('description') or '').strip()))
    walk(node, ())
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


def row(key, group, value, origin, differs=False, form=None, description=''):
    return {'key': key, 'group': group, 'value': value, 'origin': origin, 'differs': differs, 'form': form,
            'description': description}


def rows(config, profile=None, node=None):
    """Buch: je Einstellung key, group, value, origin (book|library|default|unset|series), differs, form, description."""
    profile = profile or {}
    preset = defaults()
    out = []
    for dotted, description in leaves(node):
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
        out.append(row(dotted, dotted.split('.')[0], value, origin, differs, form_for(dotted), description))
    ser = config.get('_series') if isinstance(config.get('_series'), dict) else None
    if ser:   # Serie des Buchs (#116): Angaben gelten für alle Bände
        for key in SERIES_FIELDS:
            if ser.get(key) not in (None, ''):
                out.append(row(f'series.{key}', 'series', ser[key], 'series', form='series-edit'))
        if ser.get('volume'):
            out.append(row('series.volume', 'series', ser['volume'], 'series', form='series-edit'))
    return out


def section_rows(base, config):
    """Abschnitte, deren Faktencheck von der Vorgabe des Buchs abweicht (Kapitel haben keine eigenen Einstellungen)."""
    sys.path.insert(0, str(ROOT / 'scripts'))
    try:
        from render_view import section_file
    except Exception:
        return []
    default = (config.get('workflow') or {}).get('fact_checking_default') or 'optional'
    out = []
    for cnum, chapter in enumerate((config.get('structure') or {}).get('chapters') or [], start=1):
        for snum, section in enumerate(chapter.get('sections') or [], start=1):
            try:
                head = section_file(base, section)[0] or {}
            except Exception:
                continue
            value = head.get('fact_check')
            if value and value != default:
                out.append(row(f'{cnum}.{snum}', 'sections', value, 'section', True, 'section-edit',
                               section.get('title') or ''))
    return out


def profile_rows(profile):
    """Bibliothek: Felder von assistant.yml."""
    out = []
    for key, description in leaves(schema('assistant'), skip=set(), depth=1):
        if key in PROFILE_SKIP:
            continue
        if key in profile:
            value, origin = profile[key], 'own'
        elif key in PROFILE_DEFAULTS:
            value, origin = PROFILE_DEFAULTS[key], 'default'
        else:
            value, origin = None, 'unset'
        differs = origin == 'own' and key in PROFILE_DEFAULTS and value != PROFILE_DEFAULTS[key]
        out.append(row(key, 'profile', value, origin, differs, PROFILE_FORM.get(key), description))
    return out


def series_rows(ser):
    return [row(k, 'series', ser.get(k), 'own' if ser.get(k) not in (None, '') else 'unset', form='series-edit')
            for k in SERIES_FIELDS]


def omnibus_rows(om):
    preset = defaults()
    out = []
    for group in OMNIBUS_GROUPS:
        if group == 'typesetting':
            own_ts = om.get('typesetting') or {}
            keys = sorted({k.split('.', 1)[1] for k in preset if k.startswith('typesetting.')} | set(own_ts))
            for k in keys:
                own = k in own_ts
                value = own_ts[k] if own else preset.get(f'typesetting.{k}')
                out.append(row(f'typesetting.{k}', 'typesetting', value, 'omnibus' if own else 'default',
                               own and value != preset.get(f'typesetting.{k}'), 'omnibus-edit'))
        elif group == 'publication':
            for k, value in (om.get('publication') or {}).items():
                out.append(row(f'publication.{k}', 'publication', value, 'omnibus', form='omnibus-edit'))
        else:
            out.append(row(group, 'omnibus', om.get(group), 'omnibus' if om.get(group) not in (None, '', []) else 'unset',
                           form='omnibus-edit'))
    return out


def show(value, language='de'):
    if value is None or value == '' or value == [] or value == {}:
        return '–'
    if isinstance(value, bool):
        return t(language)['yes'] if value else t(language)['no']
    text = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False)
    text = ' '.join(text.split())
    return text if len(text) <= 60 else text[:57] + '…'


def page(base, config, profile, where=None):
    """(Seitenart, Untertitel, Zeilen) für den Aufruf; where wie bei render_view.py."""
    parts = (where or '').split()
    kind = parts[0].casefold() if parts else ''
    if kind in ('bibliothek', 'library'):
        return 'library', '', profile_rows(profile)
    if kind in ('serie', 'series', 'sammelband', 'omnibus'):
        import series
        if len(parts) < 2:
            raise SystemExit('Serie angeben, z. B. settings-overview "serie ser-krimi"')
        ser, _ = series.get(base, parts[1])
        if kind in ('serie', 'series'):
            return 'series', ser.get('title', ''), series_rows(ser)
        om = series.omnibus(base, ser['id'])
        if om is None:
            raise SystemExit(f'Serie {ser["id"]} hat noch keinen Sammelband.')
        return 'omnibus', om.get('title') or ser.get('title', ''), omnibus_rows(om)
    data = rows(config, profile) + section_rows(base, config)
    if kind:
        data = [r for r in data if r['group'] == kind]
    return 'book', (config.get('project') or {}).get('title') or '', data


def heading(kind, subtitle, language):
    tx = t(language)
    return tx['title'] + (f' · {tx[kind]}' if kind in ('library', 'series', 'omnibus') else '') + (f' · {subtitle}' if subtitle else '')


def markdown(base, config, profile=None, where=None, language='de'):
    tx = t(language)
    kind, subtitle, data = page(base, config, profile or {}, where)
    own = sum(r['origin'] in OWN for r in data)
    lines = [f'### {heading(kind, subtitle, language)}', '', tx['intro'].format(n=len(data), own=own), '']
    for group in dict.fromkeys(r['group'] for r in data):
        if group == 'sections':
            default = (config.get('workflow') or {}).get('fact_checking_default') or 'optional'
            lines += [f'#### {tx["sections"]}', '', tx['sections_intro'].format(default=default), '']
        else:
            lines += [f'#### {tx["groups"].get(group, group)}', '']
        lines += [tx['head'], '|---|---|---|---|']
        for r in (x for x in data if x['group'] == group):
            value = show(r['value'], language).replace('|', '\\|')
            value = f'**{value}**' if r['differs'] else value
            form = tx['forms'].get(r['form'], r['form']) if r['form'] else tx['file_only']
            label = f'`{r["key"]}`' + (f' {r["description"]}' if group == 'sections' and r['description'] else '')
            lines.append(f'| {label} | {value} | {tx["origin"][r["origin"]]} | {form} |')
        lines.append('')
    return '\n'.join(lines)


def widget_values(base, config, profile=None, where=None, language='de'):
    """Werte und Blöcke für die Vorlage `einstellungen` (ghostwriter-ui): je Gruppe eine Zeile mit JSON-Liste."""
    tx = t(language)
    kind, subtitle, data = page(base, config, profile or {}, where)
    groups = []
    for group in dict.fromkeys(r['group'] for r in data):
        items = [x for x in data if x['group'] == group]
        groups.append({'G_KEY': group, 'G_TITLE': tx['sections'] if group == 'sections' else tx['groups'].get(group, group),
                       'G_ROWS': json.dumps([{'key': r['key'], 'label': r['description'] if group == 'sections' else '',
                                              'value': show(r['value'], language), 'origin': r['origin'],
                                              'origin_text': tx['origin'][r['origin']], 'differs': bool(r['differs']),
                                              'form_text': tx['forms'].get(r['form'], r['form']) if r['form'] else tx['file_only']}
                                             for r in items], ensure_ascii=False)})
    values = {'SETTINGS_KIND': kind, 'SETTINGS_TITLE': heading(kind, subtitle, language),
              'SETTINGS_INTRO': tx['intro'].format(n=len(data), own=sum(r['origin'] in OWN for r in data))
                                  .replace('**Fett**', 'Hervorgehoben').replace('**Bold**', 'Highlighted'),
              'SETTINGS_COUNT': len(data)}
    return values, {'GROUPS': groups}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('project')
    ap.add_argument('where', nargs='?', help='Gruppe, „bibliothek“, „serie <id>“ oder „sammelband <id>“')
    ap.add_argument('--language', default='de')
    ap.add_argument('--json', action='store_true')
    a = ap.parse_args(argv)
    import yaml
    base = Path(a.project)
    path = base / 'ghostwriter.yml'
    config = (yaml.safe_load(path.read_text(encoding='utf-8')) or {}) if path.is_file() else {}
    profile_path = base / 'assistant.yml'
    profile = yaml.safe_load(profile_path.read_text(encoding='utf-8')) or {} if profile_path.is_file() else {}
    if a.json:
        print(json.dumps(page(base, config, profile, a.where)[2], ensure_ascii=False, indent=1, default=str))
    else:
        print(markdown(base, config, profile, a.where, a.language))


if __name__ == '__main__':
    main()
