#!/usr/bin/env python3
"""Lesender Request-Profiler (#204); JSON von stdin, Metadaten nach stdout."""
import argparse
import hashlib
import json
import math
import sys
import threading
import uuid


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'))


def component(content, *, source, kind, scope='request', priority='unknown',
              activation='submitted', layer='adapter', position=0):
    """Text bleibt ausschließlich im temporären Plan; report() gibt ihn nie aus."""
    return dict(content=content, source=source, kind=kind, scope=scope,
                priority=priority, activation=activation, layer=layer, position=position)


def request_plan(payload, adapter):
    """Nur explizit übergebene Payloads; keine Header, Schlüssel oder Plattformabfragen."""
    if adapter not in ('openai-chat', 'anthropic-messages', 'openwebui-pipe'):
        raise ValueError('Unbekannter Adapter')
    parts = []
    if 'system' in payload:
        parts.append(component(payload['system'], source='$.system', kind='system', position=len(parts)))
    for i, message in enumerate(payload.get('messages', [])):
        parts.append(component(message, source=f'$.messages[{i}]', kind=message.get('role', 'unknown'),
                               position=len(parts)))
    if 'tools' in payload:
        parts.append(component(payload['tools'], source='$.tools', kind='tools', position=len(parts)))
    return {'adapter': adapter, 'model': payload.get('model'), 'components': parts}


def report(plan, payload):
    """Neue Metadatenstruktur; weder Plan noch Payload werden verändert."""
    rows, seen, duplicates = [], {}, []
    for part in plan['components']:
        content = part['content']
        text = content if isinstance(content, str) else canonical(content)
        digest = hashlib.sha256(text.encode('utf-8')).hexdigest()
        row = {k: part[k] for k in ('source', 'kind', 'scope', 'priority', 'activation', 'layer', 'position')}
        row.update(fingerprint=digest, characters=len(text), estimated_tokens=math.ceil(len(text) / 3.5))
        if digest in seen:
            duplicates.append({'kind': 'exact_duplicate', 'sources': [seen[digest], part['source']],
                               'action': 'review_only'})
        else:
            seen[digest] = part['source']
        rows.append(row)
    serialized = canonical(payload)
    return {'format_version': 1, 'adapter': plan['adapter'], 'model': plan['model'],
            'measurement': {'method': 'characters_divided_by_3.5', 'status': 'estimated', 'tokenizer': None,
                            'includes_serialization': True, 'model_framing': 'unknown',
                            'multimodal_tokens': 'unknown'},
            'visible_request': {'characters': len(serialized), 'estimated_tokens': math.ceil(len(serialized) / 3.5),
                                'fingerprint': hashlib.sha256(serialized.encode('utf-8')).hexdigest()},
            'components': rows, 'findings': duplicates,
            'visibility': {'adapter_payload': 'supplied_snapshot', 'ghostwriter_core': 'unattributed',
                           'platform_additions': 'unknown', 'provider_internal': 'unknown'},
            'usage': {'prompt_tokens': None, 'completion_tokens': None, 'cache_read_tokens': None,
                      'cache_write_tokens': None, 'cost': None, 'cost_status': 'unavailable'},
            'limits': ['Keine semantische Konfliktanalyse', 'Keine Aussage über tatsächlichen Versand',
                       'Keine Messung wiederholter Requests oder Cache-Effekte']}



def count(value):
    """Nur tatsächlich gelieferte nichtnegative Ganzzahlen gelten als Messwert."""
    return value if type(value) is int and value >= 0 else None


def provider_usage(response, adapter):
    raw = response.get('usage') or {}
    result = {'prompt_tokens': None, 'completion_tokens': None, 'cache_read_tokens': None,
              'cache_write_tokens': None, 'uncached_input_tokens': None,
              'cost': None, 'cost_status': 'unavailable', 'status': 'unavailable'}
    if adapter == 'openai-chat':
        details = raw.get('prompt_tokens_details') or {}
        result.update(prompt_tokens=count(raw.get('prompt_tokens')),
                      completion_tokens=count(raw.get('completion_tokens')),
                      cache_read_tokens=count(details.get('cached_tokens')),
                      cache_write_tokens=count(details.get('cache_write_tokens')))
    elif adapter == 'anthropic-messages':
        values = [count(raw.get(k)) for k in
                  ('input_tokens', 'cache_creation_input_tokens', 'cache_read_input_tokens')]
        result.update(uncached_input_tokens=values[0], cache_write_tokens=values[1], cache_read_tokens=values[2],
                      completion_tokens=count(raw.get('output_tokens')))
        # Anthropic: input_tokens enthält Cache-Lese-/Schreib-Tokens nicht.
        # Fehlende Felder bleiben unbekannt, statt sie als Null zu addieren.
        if all(v is not None for v in values):
            result['prompt_tokens'] = sum(values)
    if any(result[k] is not None for k in ('prompt_tokens', 'completion_tokens', 'uncached_input_tokens',
                                          'cache_read_tokens', 'cache_write_tokens')):
        result['status'] = 'provider_reported'
    return result


class Capture:
    """Erfasst vor Versand; hält nach Konstruktion keine Request-Volltexte."""
    def __init__(self, payload, adapter, core_plan=None, transport_body=None):
        self.metadata = report(request_plan(payload, adapter), payload)
        self.metadata['call_id'] = uuid.uuid4().hex
        if transport_body is not None:
            self.metadata['transport_body'] = {
                'bytes': len(transport_body),
                'fingerprint': hashlib.sha256(transport_body).hexdigest()}
        if core_plan is not None:
            self.metadata['core_components'] = report(
                {'adapter': adapter, 'model': payload.get('model'), 'components': core_plan}, payload)['components']
            self.metadata['visibility']['ghostwriter_core'] = 'captured_call_arguments'
        self.metadata['visibility']['adapter_payload'] = 'captured_before_transport'
        self.metadata['limits'] = ['Keine semantische Konfliktanalyse',
                                   'Provider-interne Verarbeitung bleibt unbekannt',
                                   'Wiederholte Inhalte belegen keine Cache-Einsparung']

    def finish(self, response=None, *, succeeded=True):
        result = dict(self.metadata)
        result['transport_status'] = 'response_received' if succeeded else 'failed'
        result['usage'] = provider_usage(response or {}, result['adapter'])
        return result


_OUTPUT_LOCK = threading.Lock()


def emit(result):
    """Explizit eingeschaltete Metadaten nach stderr, nie Antwort-/Requesttexte."""
    with _OUTPUT_LOCK:
        print('GHOSTWRITER_PROFILE ' + canonical(result), file=sys.stderr)


def aggregate(reports):
    """Keine Volltexte nötig; fehlende Messwerte werden nicht als Null summiert."""
    reports = list(reports)
    totals = {}
    for field in ('prompt_tokens', 'completion_tokens', 'cache_read_tokens', 'cache_write_tokens'):
        values = [count(r.get('usage', {}).get(field)) for r in reports]
        totals[field] = {'known_sum': sum(v for v in values if v is not None),
                         'known_calls': sum(v is not None for v in values),
                         'unknown_calls': sum(v is None for v in values)}
    seen, repeated = set(), []
    for index, entry in enumerate(reports):
        current = set()
        for row in entry['components']:
            key = (row['fingerprint'], row['kind'])
            if key in seen:
                repeated.append({'call_index': index, 'source': row['source'],
                                 'fingerprint': row['fingerprint'], 'characters': row['characters'],
                                 'transport_status': entry.get('transport_status', 'unknown')})
            current.add(key)
        seen.update(current)
    return {'calls': len(reports), 'usage': totals, 'repeated_components': repeated,
            'cost_status': 'unavailable', 'cache_savings': 'unknown'}


def openwebui_report(payload, origins=None):
    """Nur Modellfelder an der Pipe-Grenze; Metadaten können Callables enthalten."""
    fields = {'model', 'messages', 'system', 'tools', 'options', 'stream', 'temperature',
              'top_p', 'top_k', 'num_ctx', 'max_tokens', 'seed', 'stop', 'response_format'}
    visible = {key: value for key, value in payload.items() if key in fields}
    result = report(request_plan(visible, 'openwebui-pipe'), visible)
    allowed = {'openwebui.input.messages', 'read_start_md.content', 'pipe.current_context'}
    for row in result['components']:
        match = row['source'].removeprefix('$.messages[').removesuffix(']')
        label = origins[int(match)] if match.isdigit() and origins and int(match) < len(origins) else None
        row['origin'] = label['source'] if isinstance(label, dict) and label.get('source') in allowed else 'unknown'
        if isinstance(label, dict) and row['origin'] != 'unknown' and count(label.get('position')) is not None:
            row['origin_position'] = label['position']
    result['visibility']['ghostwriter_core'] = 'injected_sources_labeled' if origins else 'unattributed'
    result['visibility']['adapter_payload'] = 'pipe_boundary_model_fields'
    result['coverage'] = {'excluded_top_level_fields': len(set(payload) - fields),
                          'complete_provider_request': False}
    result['transport_status'] = 'not_observed'
    result['limits'] = ['Pipe-Grenze vor Open-WebUI-Verarbeitung',
                        'Metadaten und andere nicht erfasste Felder sind ausgeschlossen',
                        'Provider-Request, Usage und Kosten bleiben unbekannt',
                        'Keine semantische Konfliktanalyse']
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--aggregate', action='store_true', help='Metadaten-JSONL aggregieren')
    parser.add_argument('--adapter', choices=['openai-chat', 'anthropic-messages', 'openwebui-pipe'])
    args = parser.parse_args()
    try:
        if args.aggregate:
            result = aggregate(json.loads(line.removeprefix('GHOSTWRITER_PROFILE '))
                               for line in sys.stdin if line.strip())
        else:
            if not args.adapter:
                parser.error('--adapter fehlt')
            payload = json.load(sys.stdin)
            result = (openwebui_report(payload) if args.adapter == 'openwebui-pipe'
                      else report(request_plan(payload, args.adapter), payload))
    except (ValueError, TypeError, KeyError, AttributeError):
        parser.exit(2, 'Ungültiger Request; Eingabe wird aus Datenschutzgründen nicht ausgegeben.\n')
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
