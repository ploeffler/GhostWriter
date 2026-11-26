"""Testhilfe (#674): Widget-Daten lesen wie gw.js – kompakte Blöcke ausklappen, fehlende Felder gelten als leer."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from render_view import unpack_payload  # noqa: E402


class WidgetData(dict):
    """Fehlende Felder sind leer: pack_payload lässt "", [] und null weg, gw.js setzt sie wieder leer ein."""
    def __missing__(self, key):
        return ''


def widget_json(text):
    """JSON der Widget-Daten (auch mit `<\\/`) lesen und wie im Chat ausklappen."""
    if isinstance(text, str):
        text = json.loads(text.replace('<\\/', '</'))
    data = unpack_payload(text)
    if not isinstance(data, dict):
        return data
    out = WidgetData(data)
    for key, value in out.items():
        if isinstance(value, list):
            out[key] = [WidgetData(r) if isinstance(r, dict) else r for r in value]
    return out


def widget_data(out):
    """Widget-Daten aus der Ausgabe von render_view.py (`GW.render("…",{…})`) lesen."""
    import re
    m = re.search(r'GW\.render\("[^"\n]+",(.*)\)</script>', out)
    if not m:
        raise AssertionError('kein GW.render in der Ausgabe: ' + out[:200])
    return widget_json(m.group(1))


def check_list(value, language='de'):
    """Prüf-Liste eines Widgets (#674) lesen wie gw.js: Zeichenkette (alte Form), Liste oder {k, r, p}; CK_MARK, CK_TAG und CK_TEXT
    werden wie in gw.js zusammengesetzt, wenn sie fehlen. So prüfen die Tests, dass beide Seiten dieselben Texte ergeben."""
    import checks
    if isinstance(value, str):
        value = json.loads(value) if value else []
    if isinstance(value, dict):
        paths = value.get('p') or []
        rows = []
        for row in value['r']:
            item = {c: (row[i] if i < len(row) else '') for i, c in enumerate(value['k'])}
            if isinstance(item.get('CK_REPORT'), int):
                item['CK_REPORT'] = paths[item['CK_REPORT']]
            rows.append(item)
        value = rows
    out = []
    for c in value:
        c = dict(c)
        res, st = c.get('CK_RESULT', ''), c.get('CK_STATE', '')
        if res and 'CK_MARK' not in c:
            mark = checks.RESULT_MARK.get(res, '')
            suffix = {'changed': '*', 'unknown': '?'}.get(st, '')
            suffix = '' if mark == '?' and suffix == '?' else suffix
            c['CK_MARK'] = mark
            if 'CK_TAG' not in c and 'CK_SHORT' in c:
                c['CK_TAG'] = f'{c["CK_SHORT"]}{mark}{suffix}'
            if 'CK_TEXT' not in c and 'CK_LABEL' in c:
                c['CK_TEXT'] = (f'{c["CK_LABEL"]}: {checks.RESULT_TEXT[language][res]}, {c.get("CK_WHEN") or c.get("CK_DATE", "")} · '
                                f'{checks.STATE_TEXT[language][st]}' + ((' · teilweise' if language == 'de' else ' · partial') if c.get('CK_PARTIAL') else ''))
        out.append(c)
    return out
