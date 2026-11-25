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
