#!/usr/bin/env python3
"""Assistenten-Profil und persönlicher Skill (#136).

Das Profil `assistant.yml` (auf dem Standard-Branch, Schema schemas/assistant.schema.json)
hält fest, was für dieses Repository gilt: owner/name, Git-Benutzer, Autor,
Standard-Erzählstimme. Daraus entsteht der persönliche Skill
`.claude/skills/<skill>/SKILL.md`, den Claude beim Einbinden des Repositorys
automatisch lädt. Beides gehört dem Buch und wird von Updates nie überschrieben.

Aufruf:
  python scripts/assistant.py <ordner> show                 Profil und Skill-Pfad zeigen
  python scripts/assistant.py <ordner> draft [--repo o/n] [--git-name N --git-email E]
                                                           Vorschlag für ein neues Profil (JSON),
                                                           aus Repo, ghostwriter.yml bzw. library.json
  python scripts/assistant.py <ordner> set '<json>' [--force]
                                                           Profil anlegen bzw. Felder ändern und den
                                                           Skill neu erzeugen; nennt die Commit-Nachricht
  python scripts/assistant.py <ordner> skill [--force]     Skill aus dem Profil neu erzeugen

Ein vorhandener, von Hand geschriebener Skill (ohne die Kennung des erzeugten Skills) wird nicht
überschrieben (#330): `set` und `skill` brechen ab. Mit --force wird er als SKILL.md.bak gesichert und
neu erzeugt. Eigene Ergänzungen im erzeugten Skill gehören zwischen die Markierungen
„Eigene Ergänzungen“; dieser Bereich bleibt beim Neuerzeugen erhalten.
  python scripts/assistant.py <ordner> check               passt der Skill zum Profil? (Exit 1 sonst;
                                                           ohne Profil Exit 0)

Skill-Name: <autor>-auf-<repo> (skill_name), z. B. cyberlefl325-auf-yawa.
"""
import argparse
import json
import re
import sys
import unicodedata
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
PROFILE = 'assistant.yml'
TEMPLATE = ROOT / 'templates' / 'assistant-skill.md'
SCHEMA = ROOT / 'schemas' / 'assistant.schema.json'
GENERAL_SKILL = 'ghostwriter'          # allgemeiner Skill aus dem Hauptrepository (managed)
VOICE_FIELDS = [('perspective', 'Erzählperspektive'), ('tense', 'Zeitform'), ('address', 'Anrede'),
                ('register', 'Sprachebene'), ('tone', 'Ton'), ('features', 'Stilmittel')]
MARKER = 'python scripts/assistant.py . skill'     # Kennung eines erzeugten Skills
OWN_START = '<!-- Eigene Ergänzungen: bleiben beim Neuerzeugen erhalten (#330) -->'
OWN_END = '<!-- Ende eigene Ergänzungen -->'
OWN_RE = re.compile(re.escape(OWN_START) + r'\n?(.*?)' + re.escape(OWN_END), re.S)
DISPLAY = {'einfach': 'Darstellung: einfach', 'uebersichtlich': 'Darstellung: übersichtlich',
           'erweitert': 'Darstellung: erweitert', 'text': 'Nur Text'}
SUBAGENT_DEFAULT = {'proofreading': 'small', 'extraction': 'small', 'language': 'medium', 'continuity': 'medium',
                    'structure': 'large', 'writing': 'large', 'research_search': 'small', 'research_review': 'medium',
                    'chapter_research': 'medium'}
SUBAGENT_DE = {'proofreading': 'Schlusskorrektur/Nachprüfung', 'extraction': 'Herauslesen (Orte, Figuren, Zeitleiste)',
               'language': 'Sprachlektorat', 'continuity': 'Buchgedächtnis', 'structure': 'Strukturlektorat',
               'writing': 'neue Szenen/Textvorschläge', 'research_search': 'Recherche: Suche',
               'research_review': 'Recherche: Abgleich', 'chapter_research': 'Kapitelrecherche'}
SIZE_DE = {'small': 'klein', 'medium': 'mittel', 'large': 'groß'}


def subagent_line(profile):
    """Modellklassen der Hilfsagenten (#418); ohne Feld keine Zeile."""
    own = profile.get('subagent_models')
    if not own:
        return ''
    models = dict(SUBAGENT_DEFAULT, **own)
    parts = ', '.join(f'{SUBAGENT_DE[k]} {SIZE_DE[v]}' for k, v in models.items())
    return (f'- Hilfsagenten (#418): {parts}. In Claude klein = haiku, mittel = sonnet, groß = opus; beim Start der '
            'Hilfsagenten in einem Satz nennen, welche Klasse wofür läuft (`docs/LEKTORAT.md`, „Modellwahl“).')


ANSWERS = {'einfach': 'einfacher Modus', 'erweitert': 'erweiterte Antworten (technische Details)'}


class HandwrittenSkill(Exception):
    """Vorhandener Skill ohne Kennung: von Hand geschrieben, nicht überschreiben (#330)."""


def slug(text):
    t = (text or '').translate(str.maketrans({'ä': 'ae', 'ö': 'oe', 'ü': 'ue', 'Ä': 'ae', 'Ö': 'oe', 'Ü': 'ue', 'ß': 'ss'}))
    t = unicodedata.normalize('NFKD', t).encode('ascii', 'ignore').decode()
    return re.sub(r'[^a-z0-9]+', '-', t.lower()).strip('-')


def skill_name(author, repo):
    """<autor>-auf-<repo>; ohne Autor der Besitzer des Repositorys. Nie „claude“/„anthropic“ und nie der allgemeine Name."""
    owner, _, name = (repo or '').partition('/')
    who = slug(author) or slug(owner) or 'autor'
    n = f'{who}-auf-{slug(name) or "buecher"}'
    n = re.sub(r'(claude|anthropic)', 'ki', n)[:64].strip('-')
    return n if n != GENERAL_SKILL else f'{n}-eigen'


def upstream_repo(base=ROOT):
    for b in (Path(base), ROOT):
        m = b / 'ghostwriter-manifest.yml'
        if m.is_file():
            up = ((yaml.safe_load(m.read_text(encoding='utf-8')) or {}).get('upstream') or {}).get('repo')
            if up:
                return up
    return 'ploeffler/GhostWriter'


def load(base):
    p = Path(base, PROFILE)
    return (yaml.safe_load(p.read_text(encoding='utf-8')) or {}) if p.is_file() else None


def errors(profile):
    """Schema-Fehler als Liste von Texten (leer = in Ordnung)."""
    from jsonschema import Draft202012Validator
    v = Draft202012Validator(json.loads(SCHEMA.read_text(encoding='utf-8')))
    out = [f'{"/".join(str(x) for x in e.path) or "(oben)"}: {e.message}' for e in v.iter_errors(profile)]
    if not out and profile.get('skill') == GENERAL_SKILL:
        out.append(f'skill: „{GENERAL_SKILL}“ ist der allgemeine Skill aus dem Hauptrepository')
    return out


def skill_path(base, profile):
    return Path(base, '.claude', 'skills', profile['skill'], 'SKILL.md')


def is_library(base):
    cfg = Path(base, 'ghostwriter.yml')
    data = (yaml.safe_load(cfg.read_text(encoding='utf-8')) or {}) if cfg.is_file() else {}
    return not ((data.get('structure') or {}).get('chapters'))


def render(base, profile):
    """Inhalt des persönlichen Skills."""
    repo = profile['repo']
    up = profile.get('upstream') or upstream_repo(base)
    git = profile.get('git') or {}
    kind = 'Bibliothek' if is_library(base) else 'Buch'
    author = (profile.get('author') or '').strip()
    title = f'{author or repo.split("/")[0]} auf {repo.split("/")[1]}'
    if git:
        git_lines = (f'- Git-Benutzer für Commits: `git config user.name "{git["name"]}"` und '
                     f'`git config user.email "{git["email"]}"` im Klon, damit Commits dem Benutzer zugeordnet sind.')
    else:
        git_lines = '- Git-Benutzer: noch nicht im Profil; beim ersten Commit den GitHub-Login des Benutzers vorschlagen und fragen.'
    voice = profile.get('voice') or {}
    lines = []
    if (voice.get('text') or '').strip():
        lines.append('Standard-Erzählstimme:\n\n' + '\n'.join('> ' + l if l else '>' for l in voice['text'].strip().splitlines()))
    details = []
    for key, label in VOICE_FIELDS:
        val = voice.get(key)
        if isinstance(val, list):
            items = [str(v).strip() for v in val if str(v or '').strip()]
            # Stilmittel immer, Ton bei längeren Einträgen als eigene Punkte (#330): Kommas im Text bleiben lesbar
            if items and (key == 'features' or any(',' in v or len(v) > 40 for v in items)):
                details.append(f'- {label}:\n' + '\n'.join(f'  - {v}' for v in items))
                continue
            val = ', '.join(items)
        if val:
            details.append(f'- {label}: {val}')
    if details:
        lines.append('\n'.join(details))
    if not lines:
        lines.append('- Standard-Erzählstimme: noch nicht festgelegt; dann gilt das Stilprofil des Buchs bzw. der Wizard (Schritt 6).')
    values = {'SKILL': profile['skill'], 'TITLE': title, 'KIND': kind, 'REPO': repo, 'UPSTREAM': up,
              'GIT_LOGIN': git.get('name') or repo.split('/')[0], 'GIT_LINES': git_lines,
              'AUTHOR_LINE': f'- Autor: {author} (Vorbelegung bei „Neues Buch“; je Buch gilt `project.author`).' if author
                             else '- Autor: noch nicht im Profil; je Buch gilt `project.author`.',
              'VOICE_LINES': '\n\n'.join(lines),
              'WORK_MODE_LINE': ('- Gespräch und Manuskriptarbeit (#315): automatisch nach Auftrag wechseln, ohne nachzufragen; '
                                 'den Wechsel in einer kurzen Zeile nennen (`START.md`, „Gespräch und Manuskriptarbeit“).'
                                 if profile.get('work_modes') == 'auto' else
                                 '- Gespräch und Manuskriptarbeit (#315): vor dem Wechsel in die Manuskriptarbeit einmal fragen '
                                 '(`START.md`, „Gespräch und Manuskriptarbeit“).' if profile.get('work_modes') == 'ask' else
                                 ''),   # ohne Feld keine Zeile: bestehende Skills bleiben unverändert gültig
              'DISPLAY_LINE': display_line(profile),
              'SUBAGENT_LINE': subagent_line(profile),
              'OWN_START': OWN_START, 'OWN_END': OWN_END}
    text = TEMPLATE.read_text(encoding='utf-8')
    for k, v in values.items():
        text = text.replace('{{' + k + '}}', v)
    return re.sub(r'\n{3,}', '\n\n', text)


def display_line(profile):
    """Darstellungsmodus und Antwortmodus als Standard dieses Repositorys (#330)."""
    disp, ans = profile.get('display'), profile.get('answers')
    if not disp and not ans:
        return '- Darstellungsmodus in Claude: Widget (`render_view.py` ohne `--text`).'
    parts = []
    if disp:
        parts.append(f'- Darstellungsmodus: „{DISPLAY[disp]}“ ist der Standard dieses Repositorys, in jedem neuen Chat; '
                     'eine Wahl im Chat geht für diesen Chat vor. In Claude Widgets (ohne `--text`), außer bei „Nur Text“.')
    else:
        parts.append('- Darstellungsmodus in Claude: Widget (`render_view.py` ohne `--text`).')
    if ans:
        parts.append(f'- Antwortmodus: {ANSWERS[ans]} als Standard dieses Repositorys; „Erweiterte Antworten an/aus“ im Chat geht vor.')
    return '\n'.join(parts)


def own_part(text):
    """Inhalt des Bereichs „Eigene Ergänzungen“ (ohne Markierungen) oder ''."""
    m = OWN_RE.search(text or '')
    return m.group(1) if m else ''


def with_own(text, own):
    return OWN_RE.sub(lambda m: OWN_START + '\n' + own + OWN_END, text, count=1) if own else text


def is_generated(text):
    return MARKER in (text or '')


def handwritten(base, profile):
    """Pfad des vorhandenen, von Hand geschriebenen Skills oder None."""
    p = skill_path(base, profile)
    return p if p.is_file() and not is_generated(p.read_text(encoding='utf-8')) else None


def write_skill(base, profile, force=False):
    """Skill erzeugen; eigene Ergänzungen bleiben. Von Hand geschriebener Skill: Abbruch, mit force Sicherung .bak."""
    p = skill_path(base, profile)
    p.parent.mkdir(parents=True, exist_ok=True)
    old = p.read_text(encoding='utf-8') if p.is_file() else None
    if old is not None and not is_generated(old):
        if not force:
            raise HandwrittenSkill(str(p.relative_to(base)))
        p.with_name('SKILL.md.bak').write_text(old, encoding='utf-8')
        old = None
    text = with_own(render(base, profile), own_part(old))
    changed = old != text
    if changed:
        p.write_text(text, encoding='utf-8')
    return p, changed


def handwritten_error(path):
    return (f'{path} ist von Hand geschrieben (keine Kennung „{MARKER}“) und wird nicht überschrieben. '
            'Inhalt sichern bzw. in den Bereich „Eigene Ergänzungen“ übernehmen, einen anderen Skill-Namen wählen '
            'oder mit --force neu erzeugen (das Original bleibt als SKILL.md.bak).')


def stale_skills(base, profile):
    """Frühere persönliche Skills (anderer Name), die beim Umbenennen verwaist sind: nur solche mit unserer Kennung."""
    d = Path(base, '.claude', 'skills')
    out = []
    for p in sorted(d.glob('*/SKILL.md')) if d.is_dir() else []:
        if p.parent.name not in (GENERAL_SKILL, profile['skill']) and is_generated(p.read_text(encoding='utf-8')):
            out.append(p)
    return out


def draft(base, repo='', git_name='', git_email=''):
    """Vorschlag für ein neues Profil aus dem, was im Repository steht."""
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    if not repo:
        import render_view
        repo = render_view.detect_repo(base)
    author = ''
    cfg = Path(base, 'ghostwriter.yml')
    if cfg.is_file():
        author = ((yaml.safe_load(cfg.read_text(encoding='utf-8')) or {}).get('project') or {}).get('author') or ''
    lib = Path(base, 'library.json')
    if not author and lib.is_file():
        books = json.loads(lib.read_text(encoding='utf-8')).get('books') or []
        author = next((b.get('author') for b in sorted(books, key=lambda b: b.get('updated_at') or '', reverse=True) if b.get('author')), '')
    prof = {'format': 1, 'repo': repo, 'skill': skill_name(author, repo) if repo else ''}
    if git_name and git_email:
        prof['git'] = {'name': git_name, 'email': git_email}
    if author:
        prof['author'] = author
    return prof


class _Dumper(yaml.SafeDumper):
    """Mehrzeilige Texte (Stimme) als lesbarer Block („|“)."""


_Dumper.add_representer(str, lambda d, s: d.represent_scalar('tag:yaml.org,2002:str', s, style='|' if '\n' in s else None))


def set_profile(base, changes, force=False):
    """Profil anlegen bzw. ändern (Felder aus changes; voice und git werden zusammengeführt) und Skill erzeugen.
    Ein von Hand geschriebener Skill gleichen Namens bricht ab, bevor etwas geschrieben wird (außer force)."""
    old = load(base)
    prof = dict(old or {'format': 1})
    for k, v in changes.items():
        if k in ('voice', 'git') and isinstance(v, dict) and isinstance(prof.get(k), dict):
            prof[k] = {**prof[k], **v}
        else:
            prof[k] = v
    for k in ('voice', 'git'):
        if isinstance(prof.get(k), dict):
            prof[k] = {kk: vv for kk, vv in prof[k].items() if vv not in ('', None, [])}
            if not prof[k]:
                prof.pop(k)
    for k in ('author', 'upstream'):
        if prof.get(k) in ('', None):
            prof.pop(k, None)
    if not prof.get('skill') and prof.get('repo'):
        prof['skill'] = skill_name(prof.get('author'), prof['repo'])
    errs = errors(prof)
    if errs:
        return None, errs, None
    hand = handwritten(base, prof)
    if hand and not force:
        return None, [handwritten_error(hand.relative_to(base))], None
    order = ['format', 'repo', 'skill', 'interface_language', 'work_modes', 'display', 'answers', 'subagent_models', 'startup', 'git',
             'author', 'voice', 'upstream']
    prof = {k: prof[k] for k in order if k in prof}
    header = '# Assistenten-Profil (#136): gilt für alle Bücher dieses Repositorys; daraus entsteht\n' \
             '# .claude/skills/<skill>/SKILL.md (python scripts/assistant.py . skill). Keine Secrets, keine Manuskripttexte.\n'
    Path(base, PROFILE).write_text(header + yaml.dump(prof, Dumper=_Dumper, allow_unicode=True, sort_keys=False, width=100), encoding='utf-8')
    write_skill(base, prof, force=force)
    removed = []
    if old and old.get('skill') and old.get('skill') != prof['skill']:
        for p in stale_skills(base, prof):
            p.unlink()
            try:
                p.parent.rmdir()
            except OSError:
                pass
            removed.append(str(p.relative_to(base)))
    msg = 'Assistenten-Profil angelegt' if old is None else 'Assistenten-Profil gespeichert'
    files = [PROFILE, str(skill_path(base, prof).relative_to(base))]
    if hand:
        files.append(str(hand.with_name('SKILL.md.bak').relative_to(base)))
    return prof, [], {'message': msg, 'files': files + removed}


def check(base):
    prof = load(base)
    if prof is None:
        return []
    errs = errors(prof)
    if errs:
        return [f'{PROFILE}: {e}' for e in errs]
    p = skill_path(base, prof)
    if not p.is_file():
        return [f'{p.relative_to(base)} fehlt (python scripts/assistant.py . skill)']
    have = p.read_text(encoding='utf-8')
    if not is_generated(have):
        return [handwritten_error(p.relative_to(base))]
    if have != with_own(render(base, prof), own_part(have)):
        return [f'{p.relative_to(base)} passt nicht zu {PROFILE} (python scripts/assistant.py . skill)']
    return []


def main(argv):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('base')
    ap.add_argument('cmd', choices=['show', 'draft', 'set', 'skill', 'check'])
    ap.add_argument('arg', nargs='?')
    ap.add_argument('--repo', default='')
    ap.add_argument('--git-name', default='')
    ap.add_argument('--git-email', default='')
    ap.add_argument('--force', action='store_true', help='von Hand geschriebenen Skill als SKILL.md.bak sichern und neu erzeugen')
    a = ap.parse_args(argv[1:])
    base = Path(a.base)
    if a.cmd == 'draft':
        print(json.dumps(draft(base, a.repo, a.git_name, a.git_email), ensure_ascii=False, indent=2))
        return 0
    if a.cmd == 'set':
        try:
            changes = json.loads(Path(a.arg).read_text(encoding='utf-8') if a.arg and Path(a.arg).is_file() else (a.arg or '{}'))
        except ValueError as e:
            print(f'✗ kein gültiges JSON: {e}')
            return 1
        prof, errs, result = set_profile(base, changes, force=a.force)
        for e in errs:
            print(f'✗ {e}')
        if errs:
            return 1
        print(f'✓ {result["message"]}: ' + ', '.join(result['files']))
        print(json.dumps(result, ensure_ascii=False))
        return 0
    prof = load(base)
    if prof is None:
        print(f'kein {PROFILE} – Profil anlegen mit: python scripts/assistant.py . draft, dann … set')
        return 0 if a.cmd in ('show', 'check') else 1
    if a.cmd == 'show':
        print(yaml.safe_dump(prof, allow_unicode=True, sort_keys=False).rstrip())
        print(f'Skill: {skill_path(base, prof).relative_to(base)}')
        return 0
    if a.cmd == 'skill':
        errs = errors(prof)
        if errs:
            for e in errs:
                print(f'✗ {PROFILE}: {e}')
            return 1
        try:
            p, changed = write_skill(base, prof, force=a.force)
        except HandwrittenSkill as e:
            print(f'✗ {handwritten_error(e)}')
            return 1
        print(f'{p.relative_to(base)}: {"geschrieben" if changed else "unverändert"}')
        return 0
    problems = check(base)
    for e in problems:
        print(f'✗ {e}')
    if not problems:
        print(f'✓ {PROFILE} und Skill passen zusammen')
    return 1 if problems else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
