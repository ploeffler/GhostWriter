"""Bediensprache und geprüfte Sprachressourcen; Manuskripttexte bleiben unverändert."""
import ast
import json
from functools import lru_cache
from pathlib import Path
from string import Formatter

RESOURCES = Path(__file__).resolve().parents[1] / 'templates' / 'i18n'
SUPPORTED = ('de', 'en')


def normalize_language(value):
    base = str(value or '').lower().replace('_', '-').split('-')[0]
    return base if base in SUPPORTED else 'de'


def resolve_language(explicit=None, config=None, profile=None):
    """Chat/CLI → Buch-Einstellung → Standard-Branch-Profil → Deutsch; nie project.language."""
    config = config if isinstance(config, dict) else {}
    profile = profile if isinstance(profile, dict) else {}
    for value in (explicit, (config.get('interface') or {}).get('language'), profile.get('interface_language')):
        if value:
            return normalize_language(value)
    return 'de'


@lru_cache(maxsize=None)
def catalog(language):
    return json.loads((RESOURCES / (normalize_language(language) + '.json')).read_text(encoding='utf-8'))


def message(language, key, **values):
    return catalog(language)[key].format(**values)


def validate_catalogs(directory=RESOURCES):
    errors, resources = [], {}
    for language in SUPPORTED:
        try:
            data = json.loads((Path(directory) / (language + '.json')).read_text(encoding='utf-8'))
            if not isinstance(data, dict):
                raise ValueError('Sprachdatei muss ein Objekt sein')
            resources[language] = data
        except (OSError, ValueError) as exc:
            errors.append(f'{language}.json: {exc}')
    reference = resources.get('de', {})
    for language, data in resources.items():
        for key in sorted(set(reference) - set(data)):
            errors.append(f'{language}.json: Übersetzung fehlt: {key}')
        for key in sorted(set(data) - set(reference)):
            errors.append(f'{language}.json: unbekannter Schlüssel: {key}')
        for key, value in data.items():
            if not isinstance(value, str) or not value.strip():
                errors.append(f'{language}.json: leere/ungültige Übersetzung: {key}')
                continue
            try:
                fields = {f for _, f, _, _ in Formatter().parse(value) if f is not None}
                expected = {f for _, f, _, _ in Formatter().parse(reference.get(key, '') if isinstance(reference.get(key, ''), str) else '') if f is not None}
                if fields != expected:
                    errors.append(f'{language}.json: abweichende Platzhalter: {key}')
            except ValueError:
                errors.append(f'{language}.json: ungültige Platzhalter: {key}')
    if Path(directory).resolve() == RESOURCES.resolve():
        source = RESOURCES.parents[1] / 'scripts' / 'daily_summary.py'
        tree = ast.parse(source.read_text(encoding='utf-8'))
        used = {n.args[0].value for n in ast.walk(tree)
                if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == 'tr'
                and n.args and isinstance(n.args[0], ast.Constant)}
        for key in sorted(used - set(reference)):
            errors.append(f'de.json: verwendeter Schlüssel fehlt: {key}')
        for key in sorted(set(reference) - used):
            errors.append(f'de.json: unbenutzter Schlüssel: {key}')
    return errors
