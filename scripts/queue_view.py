#!/usr/bin/env python3
"""Ansicht der Hintergrund-Warteschlange im Chat (#478): Widget `warteschlange` bzw. Textfassung.

Zeigt die Aufträge eines Buchs (scripts/jobs.py) mit Zustand: wartet, wartet auf Bestätigung (Budget), wartet auf
einen anderen Auftrag, fehlgeschlagen, dazu fertige Recherchen, die noch nicht ins Buch übernommen sind. Wartende
Aufträge lassen sich vorziehen (`queue.prioritize`) oder abbrechen (`queue.cancel`). Die Ansicht liest nur.

  python scripts/render_view.py <buch> queue [--text] [--language en]
"""
import json
import re
import subprocess
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
import jobs  # noqa: E402

TEXT = {
    'de': {
        'title': 'Hintergrund-Warteschlange', 'none': 'keine Aufträge', 'one': '1 Auftrag', 'many': '{n} Aufträge',
        'research': 'Recherche', 'analysis': 'Analyse', 'colorize': 'Colorieren', 'import': 'Import',
        'open': 'wartet', 'budget': 'wartet auf Bestätigung (KI-Budget knapp)', 'blocked': 'wartet auf einen anderen Auftrag',
        'blocked_by': 'Erst nach {name}', 'priority': 'vorgezogen', 'queued': 'eingereicht {when}',
        'failed_at': 'fehlgeschlagen {when}', 'done': 'Ergebnis liegt im Änderungspaket', 'empty': 'Keine Aufträge in der Warteschlange.',
        'waiting_h': 'Wartet', 'failed_h': 'Fehlgeschlagen', 'done_h': 'Fertig, noch nicht übernommen',
        'hint': 'Zum Vorziehen oder Abbrechen den Pfad nennen; ein schon laufender Auftrag lässt sich nicht stoppen.',
        'unreadable': 'Auftrag nicht lesbar',
    },
    'en': {
        'title': 'Background queue', 'none': 'no jobs', 'one': '1 job', 'many': '{n} jobs',
        'research': 'Research', 'analysis': 'Analysis', 'colorize': 'Colorize', 'import': 'Import',
        'open': 'waiting', 'budget': 'waiting for confirmation (AI budget low)', 'blocked': 'waiting for another job',
        'blocked_by': 'Only after {name}', 'priority': 'moved up', 'queued': 'queued {when}',
        'failed_at': 'failed {when}', 'done': 'result is in the pending changes', 'empty': 'No jobs in the queue.',
        'waiting_h': 'Waiting', 'failed_h': 'Failed', 'done_h': 'Finished, not yet applied',
        'hint': 'To move up or cancel, name the path; a job that is already running cannot be stopped.',
        'unreadable': 'Job not readable',
    },
}


def t(language, key, **values):
    return TEXT['en' if language == 'en' else 'de'][key].format(**values)


def when(iso, language):
    m = re.match(r'(\d{4})-(\d{2})-(\d{2})[T ](\d{2}):(\d{2})', str(iso or ''))
    if not m:
        return ''
    y, mo, d, h, mi = m.groups()
    return f'{y}-{mo}-{d} {h}:{mi} UTC' if language == 'en' else f'{d}.{mo}.{y}, {h}:{mi} UTC'


def section_label(config, sid):
    """„2.1 Titel“ für Abschnitte, Titel für Teile von Vor- und Nachspann, sonst die ID."""
    structure = (config or {}).get('structure') or {}
    for c, chapter in enumerate(structure.get('chapters') or [], 1):
        for s, section in enumerate(chapter.get('sections') or [], 1):
            if section.get('id') == sid:
                return f'{c}.{s} {section.get("title") or ""}'.strip()
    for group in ('front_matter', 'back_matter'):
        for part in structure.get(group) or []:
            if part.get('id') == sid:
                return str(part.get('title') or sid)
    return sid


def title(job, config, language):
    kind = t(language, job['type'])
    data = job['data']
    where = section_label(config, job['section_id']) if job['type'] == 'research' else ''
    if not where:
        extra = data.get(job['type']) if isinstance(data.get(job['type']), dict) else {}
        where = str(extra.get('kind') or extra.get('folder') or extra.get('step') or '')
    return f'{kind} · {where}' if where else kind


def detail(job):
    data = job['data']
    if job['type'] == 'research':
        return str(data.get('question') or '')
    extra = data.get(job['type']) if isinstance(data.get(job['type']), dict) else {}
    return ', '.join(f'{k}: {v}' for k, v in extra.items() if k in ('kind', 'scope', 'folder', 'file', 'step') and v)


def done_runs(base, language):
    """Fertige Recherchen aus Aufträgen (`request:` im Kopf der Laufdatei), die noch nicht im Buch-Branch stehen.
    Nur auf einem Arbeits-Branch erkennbar; sonst leer."""
    base = Path(base)
    try:
        import library
        prefix = library.settings(library.load_manifest())['work_prefix']
        branch = jobs.git(base, 'branch', '--show-current', check=False).stdout.strip()
        if not branch.startswith(prefix):
            return []
        merged = set(jobs.git(base, 'ls-tree', '-r', '--name-only', 'origin/' + branch[len(prefix):], '--', 'chapters', 'matter',
                              check=False).stdout.splitlines())
        out = []
        for pattern in jobs.JOB_PATTERNS[:2]:
            run_pattern = pattern.replace('request-*.yml', 'run-*.md')
            for path in sorted(base.glob(run_pattern)):
                rel = str(path.relative_to(base))
                head = path.read_text(encoding='utf-8')[:600]
                if rel not in merged and re.search(r'(?m)^request:\s*request-\d+', head):
                    out.append((path.parent.name, rel))
        return out
    except Exception:   # noqa: BLE001 – ohne Branch-Stand keine „fertig“-Zeilen
        return []


def groups(base, config, language='de'):
    """Zeilen je Gruppe: pending, failed, done."""
    pending, failed = [], []
    for j in jobs.jobs(base, config):
        d = j['data']
        row = {'J_TITLE': title(j, config, language), 'J_DETAIL': detail(j), 'J_WHEN_TEXT': '', 'J_PRIORITY_TEXT': '',
               'J_BLOCKED_TEXT': '', 'J_NOTE': j.get('problem') or '', 'J_PRIO_DISABLED': '', 'J_PATH': j.get('rel') or str(j['path'].relative_to(base)),
               'J_STATE': j['state']}
        if j['state'] == 'failed':
            row['J_DETAIL'] = str(d.get('error') or j.get('error') or t(language, 'unreadable'))
            row['J_WHEN_TEXT'] = t(language, 'failed_at', when=when(d.get('failed_at'), language)).strip() if d.get('failed_at') else ''
            failed.append(row)
            continue
        if j['state'] == 'waiting_budget':
            row['J_STATE'], row['J_STATE_TEXT'] = 'waiting_budget', t(language, 'budget')
        elif j.get('blocked_by'):
            row['J_STATE'], row['J_STATE_TEXT'] = 'blocked', t(language, 'blocked')
            row['J_BLOCKED_TEXT'] = t(language, 'blocked_by', name=j['blocked_by'])
        else:
            row['J_STATE_TEXT'] = t(language, 'open')
        row['J_WHEN_TEXT'] = t(language, 'queued', when=when(d.get('requested_at'), language)) if d.get('requested_at') else ''
        if d.get('priority') is True:
            row['J_PRIORITY_TEXT'] = t(language, 'priority')
            row['J_PRIO_DISABLED'] = 'disabled'
        row['J_ARGS'] = json.dumps({'request': row['J_PATH']}, ensure_ascii=False, separators=(',', ':'))
        pending.append(row)
    done = [{'J_TITLE': f'{t(language, "research")} · {section_label(config, sid)}', 'J_DETAIL': t(language, 'done'), 'J_PATH': rel}
            for sid, rel in done_runs(base, language)]
    return pending, failed, done


def count_text(n, language):
    return t(language, 'none') if not n else t(language, 'one') if n == 1 else t(language, 'many', n=n)


def widget_values(base, config, language='de'):
    pending, failed, done = groups(base, config, language)
    values = {'QUEUE_BOOK': (config.get('project') or {}).get('title_short') or (config.get('project') or {}).get('title') or '',
              'QUEUE_COUNT_TEXT': count_text(len(pending) + len(failed) + len(done), language),
              'QUEUE_EMPTY': '' if pending or failed or done else '1'}
    return values, {'PENDING': pending, 'FAILED': failed, 'DONE': done}


ICON = {'open': '⏳', 'blocked': '⛓️', 'waiting_budget': '🟡', 'failed': '❌'}


def text_view(base, config, language='de'):
    pending, failed, done = groups(base, config, language)
    total = len(pending) + len(failed) + len(done)
    lines = [f'**{t(language, "title")}** · {count_text(total, language)}', '']
    if not total:
        return '\n'.join(lines + [t(language, 'empty')]) + '\n'
    if pending:
        lines.append(f'**{t(language, "waiting_h")}**')
        for r in pending:
            extra = ' · '.join(x for x in (r['J_STATE_TEXT'], r['J_PRIORITY_TEXT'], r['J_BLOCKED_TEXT'], r['J_WHEN_TEXT'], r['J_NOTE']) if x)
            lines.append(f'- {ICON[r["J_STATE"]]} {r["J_TITLE"]} – {extra}' + (f'\n  {r["J_DETAIL"]}' if r['J_DETAIL'] else '')
                         + f'\n  `{r["J_PATH"]}`')
        lines.append('')
    if failed:
        lines.append(f'**{t(language, "failed_h")}**')
        for r in failed:
            lines.append(f'- {ICON["failed"]} {r["J_TITLE"]} – {r["J_DETAIL"]}' + (f' ({r["J_WHEN_TEXT"]})' if r['J_WHEN_TEXT'] else '')
                         + f'\n  `{r["J_PATH"]}`')
        lines.append('')
    if done:
        lines.append(f'**{t(language, "done_h")}**')
        lines += [f'- ✅ {r["J_TITLE"]}' for r in done]
        lines.append('')
    if pending:
        lines.append(t(language, 'hint'))
    return '\n'.join(lines).rstrip() + '\n'
