#!/usr/bin/env python3
"""Grundregeln in Stufen: Faktentreue, Kreativität und Recherche, Freigaben (#300).

Die acht Grundregeln (`ai_settings.*` und `workflow.require_*` in ghostwriter.yml) werden in drei
Gruppen über Stufen gesetzt. Jede Stufe setzt alle Werte ihrer Gruppe gemeinsam; die gewählte Stufe
steht zusätzlich in `rules` (ghostwriter.yml).

- Verschärfen geht jederzeit.
- **Lockern** (schwächer als die Programmvorgabe `global_ai_policy` in workflow.yml bzw. als eine
  Freigabepflicht) braucht eine ausdrückliche Bestätigung des Benutzers, wie eine Freigabe. Sie wird
  im Freigabe-Protokoll `approvals.yml` festgehalten (`kind: rules`, `id: rules-<gruppe>`,
  `action: granted`; die Rückkehr zur Vorgabe als `revoked`).
- **Untergrenzen** gelten immer: keine Stufe schaltet Halluzinationsverbot, Kennzeichnung von
  Unsicherheiten, Recherche bei Rechercheaufträgen, Abschnitts- oder Kapitelabschluss ab.

Aufruf:
  python scripts/rules.py <ordner> show                       Stufen, Werte, Abweichungen (JSON)
  python scripts/rules.py <ordner> choice                     Auswahl für render_view.py choice --spec (JSON)
  python scripts/rules.py <ordner> plan <gruppe> <stufe>      was sich ändert und ob es lockert (JSON)
  python scripts/rules.py <ordner> set <gruppe> <stufe> [--confirmed] [--by NAME] [--commit SHA]
                                                              Stufe setzen; Lockerung nur mit --confirmed
  python scripts/rules.py <ordner> check                      Lockerungen ohne Bestätigung, Untergrenzen
                                                              (Exit 1 bei Fehlern)
"""
import argparse
import datetime
import json
import re
import subprocess
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent

# Gruppe -> (Stufen, Vorgabe). Je Stufe: {(Block, Schlüssel): Wert}
GROUPS = {
    'facts': ({
        'nonfiction': {('ai_settings', 'hallucination_policy'): 'strict', ('ai_settings', 'source_policy'): 'required',
                       ('ai_settings', 'uncertainty_policy'): 'explicit'},
        'fiction': {('ai_settings', 'hallucination_policy'): 'standard', ('ai_settings', 'source_policy'): 'recommended',
                    ('ai_settings', 'uncertainty_policy'): 'normal'},
    }, 'nonfiction'),
    'creativity': ({
        'careful': {('ai_settings', 'creativity'): 'conservative', ('ai_settings', 'web_research'): 'mandatory'},
        'balanced': {('ai_settings', 'creativity'): 'balanced', ('ai_settings', 'web_research'): 'research'},
        'free': {('ai_settings', 'creativity'): 'creative', ('ai_settings', 'web_research'): 'research'},
    }, 'balanced'),
    'approvals': ({
        'strict': {('workflow', 'require_section_writing_approval'): True, ('workflow', 'require_section_approval'): True,
                   ('workflow', 'require_chapter_approval'): True},
        'quick': {('workflow', 'require_section_writing_approval'): False, ('workflow', 'require_section_approval'): True,
                  ('workflow', 'require_chapter_approval'): True},
    }, 'strict'),
}
# Strenge je Wert (größer = strenger); dieselbe Ordnung wie scripts/check_workflow_consistency.py
STRICTNESS = {
    'hallucination_policy': {'off': 0, 'standard': 1, 'strict': 2},
    'source_policy': {'optional': 0, 'recommended': 1, 'required': 2},
    'uncertainty_policy': {'off': 0, 'normal': 1, 'explicit': 2},
    'creativity': {'creative': 0, 'balanced': 1, 'conservative': 2},
    'web_research': {'none': 0, 'research': 1, 'mandatory': 2},
    'require_section_writing_approval': {False: 0, True: 1},
    'require_section_approval': {False: 0, True: 1},
    'require_chapter_approval': {False: 0, True: 1},
}
# Untergrenzen: schwächer geht nie, auch nicht mit Bestätigung
FLOOR = {'hallucination_policy': 'standard', 'source_policy': 'recommended', 'uncertainty_policy': 'normal',
         'creativity': 'creative', 'web_research': 'research', 'require_section_writing_approval': False,
         'require_section_approval': True, 'require_chapter_approval': True}
LABELS = {
    'facts': ('Faktentreue', {'nonfiction': ('Sachbuch', 'Quellen Pflicht, Unsicherheiten ausdrücklich kennzeichnen, '
                                             'nichts erfinden'),
                              'fiction': ('Erzählung', 'Erfundenes ist in der Handlung erlaubt; echte Tatsachen (Orte, '
                                          'Geschichte, Medizin, Recht) bleiben belegt und werden nicht erfunden')}),
    'creativity': ('Kreativität und Recherche', {
        'careful': ('Zurückhaltend', 'nah an den Quellen, Recherche bei jedem Schreibauftrag'),
        'balanced': ('Ausgewogen', 'Beispiele und Bilder erlaubt, Recherche bei Rechercheaufträgen'),
        'free': ('Frei', 'mehr eigene Ideen und Formulierungen, Recherche bei Rechercheaufträgen')}),
    'approvals': ('Freigaben', {
        'strict': ('Streng', 'Schreiben je Abschnitt erlauben, Abschnitt und Kapitel abschließen'),
        'quick': ('Zügig', 'ohne Schreibfreigabe je Abschnitt; Abschnitt und Kapitel abschließen bleibt Pflicht')}),
}
HEADERS = {'facts': 'Faktentreue', 'creativity': 'Kreativität', 'approvals': 'Freigaben'}


def load_config(base):
    return yaml.safe_load((Path(base) / 'ghostwriter.yml').read_text(encoding='utf-8')) or {}


def program_policy():
    """Programmvorgabe: global_ai_policy aus workflow.yml, Freigabepflichten immer an."""
    wf = yaml.safe_load((ROOT / 'workflow.yml').read_text(encoding='utf-8')) or {}
    pol = {('ai_settings', k): v for k, v in (wf.get('global_ai_policy') or {}).items() if k in STRICTNESS}
    pol.update(GROUPS['approvals'][0]['strict'])
    return pol


def current(config, key):
    block, name = key
    v = (config.get(block) or {}).get(name)
    if v is None and block == 'workflow':
        return True   # fehlt = Pflicht
    return v


def looser(key, value, reference):
    levels = STRICTNESS[key[1]]
    return value in levels and reference in levels and levels[value] < levels[reference]


def level_of(config, group):
    levels, default = GROUPS[group]
    values = {k: current(config, k) for k in levels[default]}
    for name, spec in levels.items():
        if all(values[k] == v for k, v in spec.items()):
            return name
    return None   # eigene Werte, passen zu keiner Stufe


def confirmations(base):
    """Letzter Eintrag je Regelgruppe aus approvals.yml (kind: rules)."""
    p = Path(base) / 'approvals.yml'
    data = (yaml.safe_load(p.read_text(encoding='utf-8')) or {}) if p.is_file() else {}
    latest = {}
    for e in data.get('entries') or []:
        if e.get('kind') == 'rules':
            latest[e['id'].removeprefix('rules-')] = e
    return latest


def show(base):
    config, pol, conf = load_config(base), program_policy(), confirmations(base)
    out = {}
    for group, (levels, default) in GROUPS.items():
        values = {k[1]: current(config, k) for k in levels[default]}
        relaxed = [k[1] for k in levels[default] if looser(k, current(config, k), pol[k])]
        lv = level_of(config, group)
        title, names = LABELS[group]
        out[group] = {'title': title, 'level': lv, 'level_label': names[lv][0] if lv else 'eigene Werte',
                      'default': default, 'values': values, 'relaxed': relaxed,
                      'confirmed': bool(relaxed) and (conf.get(group) or {}).get('action') == 'granted'}
    return out


def choice_spec(base):
    config = load_config(base)
    qs = []
    for group, (levels, default) in GROUPS.items():
        title, names = LABELS[group]
        qs.append({'key': group, 'header': HEADERS[group], 'text': title, 'field': f'rules.{group}',
                   'options': [{'value': n, 'label': names[n][0], 'desc': names[n][1], 'recommended': n == default}
                               for n in levels]})
    return {'step': 'rules', 'title': 'Grundregeln', 'questions': qs,
            'subtitle': 'Jede Stufe setzt die Regeln ihrer Gruppe gemeinsam.',
            'note': 'Lockern (schwächer als die Vorgabe) braucht danach eine eigene Bestätigung und wird im '
                    'Freigabe-Protokoll festgehalten. Untergrenzen bleiben immer: nichts als Tatsache erfinden, '
                    'Abschnitt und Kapitel abschließen.'}


def plan(base, group, level):
    if group not in GROUPS:
        raise SystemExit(f'Unbekannte Gruppe {group!r} (facts, creativity, approvals)')
    levels, default = GROUPS[group]
    if level not in levels:
        raise SystemExit(f'Unbekannte Stufe {level!r} für {group} ({", ".join(levels)})')
    config, pol = load_config(base), program_policy()
    changes = [{'key': f'{b}.{k}', 'from': current(config, (b, k)), 'to': v}
               for (b, k), v in levels[level].items() if current(config, (b, k)) != v]
    relaxes = [f'{b}.{k}' for (b, k), v in levels[level].items() if looser((b, k), v, pol[(b, k)])]
    title, names = LABELS[group]
    return {'group': group, 'title': title, 'level': level, 'label': names[level][0], 'description': names[level][1],
            'changes': changes, 'relaxes': relaxes, 'needs_confirmation': bool(relaxes),
            'back_to_default': level == default and level_of(config, group) != default}


def set_value(text, block, key, value):
    """Wert in ghostwriter.yml setzen, Rest der Datei unverändert lassen."""
    lit = ('true' if value else 'false') if isinstance(value, bool) else f'"{value}"'
    m = re.search(rf'(?m)^{block}:\s*\n((?:[ \t]+.*\n|\s*\n)*)', text)
    if not m:
        return text.rstrip('\n') + f'\n{block}:\n  {key}: {lit}\n'
    body = m.group(1)
    new, n = re.subn(rf'(?m)^(  {key}:)[ \t]*[^\n#]*?([ \t]*#.*)?$', lambda x: f'{x.group(1)} {lit}{x.group(2) or ""}', body, count=1)
    if not n:
        new = f'  {key}: {lit}\n' + body
    return text[:m.start(1)] + new + text[m.end(1):]


def head_commit(base):
    return subprocess.run(['git', 'rev-parse', 'HEAD'], cwd=base, capture_output=True, text=True).stdout.strip()


def apply(base, group, level, confirmed=False, by='chat', commit=None):
    base = Path(base)
    p = plan(base, group, level)
    if p['needs_confirmation'] and not confirmed:
        raise SystemExit(f'✗ {p["title"]}: „{p["label"]}“ lockert {", ".join(p["relaxes"])} – nur nach ausdrücklicher '
                         'Bestätigung des Benutzers (--confirmed)')
    cfg_path = base / 'ghostwriter.yml'
    text = cfg_path.read_text(encoding='utf-8')
    for (b, k), v in GROUPS[group][0][level].items():
        text = set_value(text, b, k, v)
    text = set_value(text, 'rules', group, level)
    cfg_path.write_text(text, encoding='utf-8')
    files = ['ghostwriter.yml']
    previous = (confirmations(base).get(group) or {}).get('action')
    action = 'granted' if p['relaxes'] else ('revoked' if previous == 'granted' else None)
    if action:
        commit = commit or head_commit(base)
        if not re.fullmatch(r'[0-9a-f]{7,40}', commit or ''):
            raise SystemExit('Bestätigung braucht den bestätigten Stand (Commit); ohne Git --commit angeben')
        ap = base / 'approvals.yml'
        data = (yaml.safe_load(ap.read_text(encoding='utf-8')) or {}) if ap.is_file() else {}
        changes = ', '.join(f'{c["key"]} {c["from"]}→{c["to"]}' for c in p['changes']) or 'keine Werte geändert'
        data['entries'] = (data.get('entries') or []) + [{
            'kind': 'rules', 'id': f'rules-{group}', 'action': action,
            'at': datetime.datetime.now().astimezone().isoformat(timespec='seconds'), 'by': by, 'commit': commit,
            'note': f'Stufe {level} ({p["label"]}): {changes}'}]
        ap.write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False, width=10**6), encoding='utf-8')
        files.append('approvals.yml')
    verb = 'gelockert' if p['relaxes'] else 'gesetzt'
    return {'files': files, 'message': f'Grundregeln: {p["title"]} auf „{p["label"]}“ {verb}', 'plan': p}


def problems(base, config=None):
    """Lockerungen ohne gültige Bestätigung und unterschrittene Untergrenzen."""
    config = config if config is not None else load_config(base)
    pol, conf, errs = program_policy(), confirmations(base), []
    for group, (levels, default) in GROUPS.items():
        relaxed = []
        for key in levels[default]:
            v = current(config, key)
            levels_k = STRICTNESS[key[1]]
            if v not in levels_k:
                continue   # unbekannte Werte meldet die Programmprüfung
            if levels_k[v] < levels_k[FLOOR[key[1]]]:
                errs.append(f'ghostwriter.yml: {key[0]}.{key[1]}: {v!r} unterschreitet die Untergrenze '
                            f'{FLOOR[key[1]]!r} (scripts/rules.py)')
            elif looser(key, v, pol[key]):
                relaxed.append(f'{key[0]}.{key[1]}')
        if relaxed and (conf.get(group) or {}).get('action') != 'granted':
            errs.append(f'ghostwriter.yml: {", ".join(relaxed)} gelockert ohne Bestätigung im Freigabe-Protokoll '
                        f'(approvals.yml, rules-{group}; scripts/rules.py set … --confirmed)')
        chosen = (config.get('rules') or {}).get(group)
        if chosen and chosen != level_of(config, group):
            errs.append(f'ghostwriter.yml: rules.{group}: {chosen!r} passt nicht zu den Werten der Gruppe '
                        f'(scripts/rules.py set {group} <stufe>)')
    return errs


def main(argv):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('base')
    ap.add_argument('cmd', choices=['show', 'choice', 'plan', 'set', 'check'])
    ap.add_argument('group', nargs='?')
    ap.add_argument('level', nargs='?')
    ap.add_argument('--confirmed', action='store_true', help='Lockerung wurde vom Benutzer ausdrücklich bestätigt')
    ap.add_argument('--by', default='chat')
    ap.add_argument('--commit')
    a = ap.parse_args(argv[1:])
    if a.cmd == 'show':
        print(json.dumps(show(a.base), ensure_ascii=False, indent=2))
    elif a.cmd == 'choice':
        print(json.dumps(choice_spec(a.base), ensure_ascii=False, indent=2))
    elif a.cmd == 'plan':
        print(json.dumps(plan(a.base, a.group, a.level), ensure_ascii=False, indent=2))
    elif a.cmd == 'set':
        r = apply(a.base, a.group, a.level, a.confirmed, a.by, a.commit)
        print(f'✓ {r["message"]}: ' + ', '.join(r['files']))
    else:
        errs = problems(a.base)
        for e in errs:
            print(f'✗ {e}')
        if errs:
            return 1
        print('✓ Grundregeln in Ordnung')
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
