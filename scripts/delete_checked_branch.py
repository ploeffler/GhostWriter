#!/usr/bin/env python3
"""Entfernt einen geprüften Aufräumkandidaten nur beim erwarteten Remote-Head.

Die Aufräum-Action prüft zuvor Übernahme/Erhalt des Inhalts. Dieser Helfer bindet
nur die abschließende Ref-Änderung atomar an den geprüften Stand. Kein REST-DELETE
als Rückfall, keine automatische Wiederholung nach unklarem Ergebnis.
"""
import argparse
import json
import re
import subprocess
import sys

ZERO_OID = '0' * 40
CLIENT_ID = 'ghostwriter-checked-delete'
MUTATION = '''mutation DeleteCheckedBranch($input: UpdateRefsInput!) {
  updateRefs(input: $input) { clientMutationId }
}'''


def request_payload(repository_id, branch, expected_head, preserve_tag=None, tag_oid=None):
    if not isinstance(repository_id, str) or not repository_id.strip():
        raise ValueError('Repository-Node-ID fehlt.')
    if not re.fullmatch(r'(?:feat|fix|docs|ui|chore|media|test|codex|claude|ghostwriter|release)/.+|v[0-9]+\.[0-9]+', branch or '') or branch == 'test/test-book':
        raise ValueError('Kein zulässiger Aufräumkandidat.')
    if subprocess.run(['git', 'check-ref-format', 'refs/heads/' + branch], capture_output=True).returncode:
        raise ValueError('Ungültiger Branchname.')
    if not re.fullmatch(r'[0-9a-f]{40}', expected_head or '') or expected_head == ZERO_OID:
        raise ValueError('Vollständiger geprüfter Head erforderlich.')
    updates = [{'name': 'refs/heads/' + branch, 'beforeOid': expected_head,
                'afterOid': ZERO_OID, 'force': False}]
    if preserve_tag is not None or tag_oid is not None:
        if not preserve_tag or subprocess.run(['git', 'check-ref-format', 'refs/tags/' + preserve_tag], capture_output=True).returncode:
            raise ValueError('Ungültiger Erhaltungstag.')
        if not re.fullmatch(r'[0-9a-f]{40}', tag_oid or '') or tag_oid == ZERO_OID:
            raise ValueError('Geprüfte Tag-Objekt-ID erforderlich.')
        # Atomare unveränderte Tag-Referenz: ohne diesen Erhalt keine Löschung.
        updates.append({'name': 'refs/tags/' + preserve_tag, 'beforeOid': tag_oid,
                        'afterOid': tag_oid, 'force': False})
    return {'query': MUTATION, 'variables': {'input': {
        'repositoryId': repository_id, 'clientMutationId': CLIENT_ID, 'refUpdates': updates}}}


def confirmed(response):
    return (isinstance(response, dict) and not response.get('errors')
            and isinstance(response.get('data'), dict)
            and isinstance(response['data'].get('updateRefs'), dict)
            and response['data']['updateRefs'].get('clientMutationId') == CLIENT_ID)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--repository-id', required=True)
    ap.add_argument('--branch', required=True)
    ap.add_argument('--expected-head', required=True)
    ap.add_argument('--preserve-tag')
    ap.add_argument('--tag-oid')
    args = ap.parse_args(argv)
    try:
        payload = request_payload(args.repository_id, args.branch, args.expected_head, args.preserve_tag, args.tag_oid)
        run = subprocess.run(['gh', 'api', 'graphql', '--input', '-'],
                             input=json.dumps(payload), capture_output=True, text=True)
        if run.returncode or not confirmed(json.loads(run.stdout)):
            raise ValueError('Löschung nicht bestätigt. Remote-Stand neu prüfen; keine unbedingte Löschung versucht.')
    except (ValueError, OSError):
        # CLI-/API-Fehler können Zugangsdaten enthalten; keine Rohantwort ausgeben.
        print('Branchlöschung nicht bestätigt. Stand, Erhaltungstag und Berechtigungen neu prüfen. Kein unbedingter Löschversuch.', file=sys.stderr)
        return 1
    print('Geprüften Branch gelöscht: ' + args.branch)
    return 0


if __name__ == '__main__':
    sys.exit(main())
