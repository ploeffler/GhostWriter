"""Sprachtexte der gemeinsamen Text-/Widget-Befüllung; Nutzdaten bleiben unverändert."""
import ast
import json
from functools import lru_cache
from pathlib import Path
from string import Formatter

RESOURCE = Path(__file__).resolve().parents[1] / 'templates' / 'i18n' / 'views'
DIRECT_VIEWS = {'changes-merge', 'chapter-reorder', 'section-reorder', 'series-edit',
                'approval-writing', 'approval-section', 'approval-chapter', 'approval-matter', 'approval-image'}


@lru_cache(maxsize=None)
def catalog(language):
    return json.loads((RESOURCE / (language + '.json')).read_text(encoding='utf-8'))


def translate(key, language='de', **values):
    language = 'en' if str(language).lower().replace('_', '-').split('-')[0] == 'en' else 'de'
    return catalog(language)[key].format(**values)


def validate_resources():
    """Gleiche Schlüssel und Platzhalter sowie tatsächlichen Verbrauch prüfen."""
    import re
    try:
        resources = {language: json.loads((RESOURCE / (language + '.json')).read_text(encoding='utf-8')) for language in ('de', 'en')}
        if not all(isinstance(texts, dict) for texts in resources.values()):
            return ['Ansichtstexte müssen Objekte sein']
        source = Path(__file__).with_name('render_view.py').read_text(encoding='utf-8')
        source += '\n' + Path(__file__).with_name('render_view_en.py').read_text(encoding='utf-8')
        tree = ast.parse(source)
        used = {node.args[0].value for node in ast.walk(tree)
                if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == 'view_message'
                and node.args and isinstance(node.args[0], ast.Constant)}
        used |= {node.value for node in ast.walk(tree) if isinstance(node, ast.Constant) and isinstance(node.value, str) and node.value.startswith('section_ui.')}
        if any(set(texts) != used for texts in resources.values()):
            return ['Ansichtstexte: fehlende oder unbenutzte Schlüssel']
        fields = lambda text: {name for _, name, _, _ in Formatter().parse(text) if name is not None}
        for key, text in resources['de'].items():
            for language, texts in resources.items():
                other = texts[key]
                if not isinstance(other, str) or not other.strip() or fields(text) != fields(other):
                    return ['Ansichtstexte: leere Texte oder abweichende Platzhalter: ' + language + '/' + key]
                if any(not re.fullmatch(r'[a-z_]+', field) for field in fields(other)):
                    return ['Ansichtstexte: ungültiger Platzhalter: ' + key]
    except (OSError, ValueError, TypeError, KeyError):
        return ['Ansichtstexte fehlen oder sind ungültig']
    return []
