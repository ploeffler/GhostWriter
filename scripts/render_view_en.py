"""Englische Kernansichten mit denselben Rohdaten und Sprachressourcen wie die Widgets."""
import copy
import json
from functools import lru_cache
from pathlib import Path

FORM_TEMPLATES = {'buch-anlegen', 'kapitel-anlegen', 'kapitel-bearbeiten', 'abschnitt-anlegen', 'projektdaten-bearbeiten'}
SUPPORTED = {'abschnitt-bearbeiten', 'projektuebersicht', 'kapitelansicht', 'buecherregal'} | FORM_TEMPLATES
CLI_VIEWS = {'section', 'project', 'chapter', 'library', 'book-create', 'chapter-create', 'chapter-edit', 'section-create', 'project-edit'}
RESOURCE = Path(__file__).resolve().parents[1] / 'templates' / 'ui' / 'i18n'


@lru_cache(maxsize=None)
def texts():
    return json.loads((RESOURCE / 'en.json').read_text(encoding='utf-8'))


def tr(key, **values):
    return texts()[key].format(**values)


def native(key, **values):
    return tr('native.' + key, **values)


def view_message(key, **values):
    try:
        from .view_i18n import translate
    except ImportError:
        from view_i18n import translate
    return translate(key, 'en', **values)


def quantity(key, number):
    return native(key + ('_one' if number == 1 else ''), number=number)


def status(code):
    return texts().get('status.' + str(code), str(code))


def prepare(template, original, config, args):
    """Nur erzeugte Beschriftungen ersetzen; Manuskript, Titel und Beschreibungen bleiben Daten."""
    data = copy.deepcopy(original)
    data['LANGUAGE'] = 'en'
    if template == 'projektuebersicht':
        project = config['project']
        edition = project['current_edition']
        data['PROJECT_EDITION_TEXT'] = native('edition', number=edition) if edition else native('no_edition')
        data['PROJECT_COST_HINT'] = native('project_cost_hint')
        for row in data.get('CHAPTERS', []):
            row['CHAPTER_COST_HINT'] = native('chapter_cost_hint')
        if data.get('PENDING_COUNT'):
            data['PENDING_TEXT'] = quantity('changes', number=data['PENDING_COUNT'])
        if data.get('SERIES_ID'):
            data['SERIES_TEXT'] = native('series_volume', number=data['SERIES_VOLUME_NUMBER'], title=data['SERIES_TITLE'])
        for analysis in data.get('ANALYSES', []):
            analysis['A_TEXT'] = native('analysis', kind=analysis['A_KIND'], number=analysis.get('A_COUNT', 0), date=analysis.get('A_DATE', '')[:10])
        if data.get('IMPORT_SOURCE'):
            data['IMPORT_TEXT'] = native('import_notice', name=data['IMPORT_SOURCE'], date=data.get('IMPORT_EXPIRES', ''))
    elif template == 'kapitelansicht':
        sections = data.get('SECTIONS', [])
        total = len(sections)
        approved = sum(row['SECTION_STATUS'] == 'approved' for row in sections)
        markers = sum(int(value) for row in sections for key, value in row.items() if key.startswith('MARKERS_'))
        data['SECTION_COUNT_TEXT'] = quantity('sections_count', number=total)
        data['APPROVED_COUNT_TEXT'] = native('approved_count', number=approved, total=total)
        data['MARKER_COUNT_TEXT'] = quantity('open_markers', number=markers)
        data['CHAPTER_COST_HINT'] = native('chapter_cost_hint') + (' (' + native('estimated') + ')' if data['CHAPTER_COST'].startswith('≈') else '')
    elif template == 'abschnitt-bearbeiten':
        data['MARKER_COUNT_TEXT'] = quantity('open_markers', len(data.get('MARKERS', [])))
        data['SECTION_COST_HINT'] = view_message('section_ui.section_cost_hint')
        for row in data.get('MARKERS', []):
            row['MARKER_LABEL'] = view_message({'anekdote': 'section_ui.marker_anekdote', 'quelle': 'section_ui.marker_quelle', 'medizin': 'section_ui.marker_medizin', 'recht': 'section_ui.marker_recht', 'kontinuitaet': 'section_ui.marker_kontinuitaet'}[row['MARKER_TYPE']])
        for row in data.get('HINTS', []):
            row['H_KIND_TEXT'] = view_message({'long_sentence': 'section_ui.hint_long_sentence', 'repetition': 'section_ui.hint_repetition', 'same_start': 'section_ui.hint_same_start', 'filler': 'section_ui.hint_filler'}[row['H_KIND']])
        for direction in ('PREV', 'NEXT'):
            if data.get(direction + '_SECTION_ID'):
                number = int(data['SECTION_NUMBER'].split('.')[1]) + (-1 if direction == 'PREV' else 1)
                chapter = config['structure']['chapters'][data['CHAPTER_NUMBER'] - 1]
                data[direction + '_SECTION_PROMPT'] = tr('ui.edit_section_number_title', number=f"{data['CHAPTER_NUMBER']}.{number}", title=chapter['sections'][number - 1]['title'])
    elif template == 'buecherregal':
        for row in data.get('BOOKS', []):
            ready = row['BOOK_STATE'] == 'ready'
            if row['BOOK_TITLE_EMPTY']:
                row['BOOK_TITLE'] = native('untitled')
            row['BOOK_AUTHOR_TEXT'] = native('author', name=row['BOOK_AUTHOR_NAME']) if row['BOOK_AUTHOR_NAME'] else ''
            row['BOOK_STATE_TEXT'] = native('ready' if ready else 'setup')
            row['BOOK_PROGRESS_TEXT'] = native('book_progress', approved=row['BOOK_APPROVED_SECTION_COUNT'], total=row['BOOK_SECTION_COUNT'], chapters=row['BOOK_APPROVED_CHAPTER_COUNT'], chapter_total=row['BOOK_CHAPTER_COUNT'], sections=quantity('section_unit', row['BOOK_SECTION_COUNT']), chapter_word=quantity('chapter_unit', row['BOOK_CHAPTER_COUNT'])) if ready else native('outline_pending')
            edition = row['BOOK_EDITION_NUMBER']
            row['BOOK_EDITION_TEXT'] = native('edition', number=edition) if edition else native('no_edition')
            row['BOOK_PENDING_TEXT'] = quantity('changes', number=row['BOOK_PENDING_COUNT']) if row['BOOK_PENDING_COUNT'] else ''
            row['BOOK_UPDATED_TEXT'] = native('updated' if ready else 'created', date=row['BOOK_UPDATED_AT'][:10]) if row['BOOK_UPDATED_AT'] else ''
            row['BOOK_VOLUME_TEXT'] = native('volume', number=row['BOOK_VOLUME_NUMBER']) if row.get('BOOK_SERIES') else ''
        if not getattr(args, 'repo_known', True):
            data['LIBRARY_NAME'] = native('unknown_repo')
        data['BOOK_COUNT_TEXT'] = quantity('book_count', number=data['BOOK_COUNT_NUMBER'])
        if data['SERIES_COUNT_NUMBER']:
            data['BOOK_COUNT_TEXT'] += ' · ' + quantity('series_count', number=data['SERIES_COUNT_NUMBER'])
    elif template in ('kapitel-anlegen', 'abschnitt-anlegen'):
        if template == 'kapitel-anlegen':
            items = config['structure']['chapters']
            number = None
        else:
            number = data['CHAPTER_NUMBER']
            items = config['structure']['chapters'][number - 1]['sections']
        for i, row in enumerate(data['POSITIONS']):
            if not items:
                row['POSITION_LABEL'] = native('first_chapter' if number is None else 'first_section')
            elif i == 0:
                row['POSITION_LABEL'] = native('chapter_beginning') if number is None else native('section_beginning', number=number)
            else:
                last = i == len(items)
                label = ('chapter_end' if last else 'after_chapter') if number is None else ('section_end' if last else 'after_section')
                row['POSITION_LABEL'] = native(label, number=i if number is None else f'{number}.{i}', title=items[i - 1]['title'])
    elif template == 'buch-anlegen' and data.get('SERIES_ID'):
        data['SERIES_TEXT'] = native('series_volume', number=data['SERIES_VOLUME_NUMBER'], title=data['SERIES_TITLE'])
    return data


def menu(items):
    return '**' + native('menu') + ':**  \n' + ' · '.join(f'`{code}` {label}' for code, label in items)


def cell(value):
    return str(value).replace('|', '\\|').replace('\n', ' ')


def render(template, data, config, renderer):
    if template in FORM_TEMPLATES:
        return render_form(template, data)
    if template == 'projektuebersicht':
        rows = data.get('CHAPTERS', [])
        lines = ['### 📘 ' + (data['PROJECT_TITLE'] or native('untitled')),
                 native('project_meta', edition=data['PROJECT_EDITION_TEXT'], author=data['PROJECT_AUTHOR'] or tr('ui.not_yet_set'), cost=data['PROJECT_COST']), '']
        if data.get('PENDING_COUNT'):
            lines += ['> ⏳ ' + native('pending', changes=data['PENDING_TEXT'], number=data['PENDING_PR']), '']
        if data.get('SERIES_TEXT'):
            lines += ['📚 ' + data['SERIES_TEXT'] + ' · `S`', '']
        for analysis in data.get('ANALYSES', []):
            lines += ['> ' + analysis['A_TEXT'] + ' · `' + renderer.ANALYSIS_KEY.get(analysis['A_KIND'], 'AN') + '`', '']
        for field in ('IMPORT_TEXT', 'PROJECT_DESCRIPTION_SHORT', 'PROJECT_DESCRIPTION'):
            if data.get(field):
                lines += [data[field], '']
        for field, label in [('LIMIT_TEXT', 'original_limits'), ('UPDATE_TEXT', 'original_update')]:
            if data.get(field):
                lines += ['> **' + native(label) + ':** ' + data[field], '']
        for area, label in [('MATTER_FRONT', 'ui.front_matter'), ('MATTER_BACK', 'ui.back_matter')]:
            if data.get(area):
                lines += ['**' + tr(label) + ':** ' + ' · '.join(m['MATTER_TITLE'] + ' (' + status(m['MATTER_STATUS']) + ')' for m in data[area]), '']
        if rows:
            lines += [native('project_table'), '|--:|---|--:|---|:-:|']
            lines += [f'| {r["CHAPTER_NUMBER"]} | {cell(r["CHAPTER_TITLE"])} | {r["CHAPTER_COST"]} | {status(r["CHAPTER_STATUS"])} | `B{r["CHAPTER_NUMBER"]}` |' for r in rows]
            current = (config.get('workflow') or {}).get('current_chapter_id')
            chips = [('**`' + str(r['CHAPTER_NUMBER']) + '`**' if r['CHAPTER_ID'] == current else '`' + str(r['CHAPTER_NUMBER']) + '`') for r in rows]
            lines += ['', '**' + native('open_chapters') + ':** ' + ' '.join(chips)]
        else:
            lines += [native('no_chapters')]
        items = []
        workflow = config.get('workflow') or {}
        for ci, chapter in enumerate(config['structure']['chapters'], 1):
            for si, section in enumerate(chapter['sections'], 1):
                if section['id'] == workflow.get('current_section_id'):
                    items.append((f'{ci}.{si}', native('open_latest')))
        if data.get('PENDING_COUNT'):
            items.append(('M', tr('ui.apply_changes')))
        if data.get('UPDATE_TEXT'):
            items.append(('U', tr('ui.install_update')))
        if data.get('LIBRARY_COUNT'):
            items.append(('L', tr('ui.library_2')))
        if data.get('SERIES_ID'):
            items.append(('S', tr('ui.show_series')))
        items += [(m['MATTER_TITLE'], tr('ui.open')) for m in data.get('MATTER_FRONT', []) + data.get('MATTER_BACK', [])]
        items += [('D', tr('ui.ai_services')), ('P', tr('ui.edit_project_details')), ('N', tr('ui.add_a_new_chapter')), ('R', native('chapter_order')), ('V', tr('ui.front_and_back_matter')), ('FI', native('figures', number=data.get('CHARACTER_COUNT', 0))), ('FV', tr('ui.suggest_characters_from_the_text_whole_book')), ('A', tr('ui.create_a_new_edition')), ('E', tr('ui.project_settings'))]
        lines += ['', '---', menu(items)]
        if data.get('CREDIT_TEXT'):
            lines += ['', '<sub>' + data['CREDIT_TEXT'] + '</sub>']
    elif template == 'kapitelansicht':
        rows = data.get('SECTIONS', [])
        lines = [native('chapter_heading', number=data['CHAPTER_NUMBER'], title=data['CHAPTER_TITLE'])]
        if data.get('CHAPTER_SUBTITLE'):
            lines += ['*' + data['CHAPTER_SUBTITLE'] + '*']
        for key, label in [('CHAPTER_GOAL', 'ui.chapter_goal'), ('CHAPTER_SUMMARY', 'ui.summary')]:
            lines += ['', '**' + tr(label) + ':** ' + (data[key] or tr('ui.not_yet_set'))]
        lines += ['', native('chapter_stats', sections=data['SECTION_COUNT_TEXT'], approved=data['APPROVED_COUNT_TEXT'], markers=data['MARKER_COUNT_TEXT'], cost=data['CHAPTER_COST']), '']
        if rows:
            lines += [native('chapter_table'), '|--:|---|---|--:|---|']
            for row in rows:
                marks = ' '.join(renderer.MARKER_ICON[k] + ' ' + str(row['MARKERS_' + k.upper()]) for k in renderer.MARKER_ICON if row['MARKERS_' + k.upper()]) or '–'
                lines += [f'| {row["SECTION_NUMBER"]} | {cell(row["SECTION_TITLE"])} | {marks} | {row["SECTION_COST"]} | {status(row["SECTION_STATUS"])} |']
            lines += ['', native('marker_legend')]
        else:
            lines += [native('no_sections')]
        number = str(data['CHAPTER_NUMBER'])
        span = number + '.1' + ('–' + number + '.' + str(len(rows)) if len(rows) > 1 else '')
        items = [(span, native('open_section'))] if rows else []
        if data.get('CHAPTER_APPROVABLE'):
            items.append(('FK', tr('ui.approve_chapter')))
        if data.get('CHAPTER_REVISION_READY'):
            items.append(('KU', tr('ui.revise_chapter_2')))
        items += [('B', tr('ui.edit_chapter_2')), ('Z', native('chapter_research')), ('N', tr('ui.new_section')), ('R', native('section_order')), ('FV', native('chapter_characters', number=data['CHAPTER_NUMBER'])), ('Ü', tr('ui.project_overview'))]
        lines += ['', '---', menu(items)]
    elif template == 'abschnitt-bearbeiten':
        lines = [f"### ✏️ {data['SECTION_NUMBER']} · {data['SECTION_TITLE']}",
                 view_message('section_ui.section_meta', number=data['CHAPTER_NUMBER'], status=status(data['SECTION_STATUS']), cost=data['SECTION_COST']), '']
        fact = {'disabled': 'ui.off', 'optional': 'ui.optional', 'requested': 'ui.requested'}.get(data['FACT_CHECK'])
        yesno = lambda value: view_message('section_ui.yes' if value == 'true' else 'section_ui.no')
        rows = [(tr('ui.section_goal'), data['SECTION_GOAL']), (tr('ui.summary'), data['SECTION_SUMMARY']),
                (tr('ui.fact_check'), tr(fact) if fact else data['FACT_CHECK']),
                (view_message('section_ui.writing_approval'), yesno(data['APPROVAL_WRITING'])),
                (view_message('section_ui.section_approved'), yesno(data['APPROVAL_SECTION']))]
        if data.get('CHARACTERS_ENABLED'):
            rows.append((tr('ui.characters_3'), ', '.join(r['C_NAME'] for r in data.get('ALL_CHARACTERS', []) if r['C_ON']) or '–'))
        lines += field_table(rows) + ['', '**' + tr('ui.open_markers') + '**']
        lines += [f"- {renderer.MARKER_ICON[r['MARKER_TYPE']]} {r['MARKER_LABEL']}: {r['MARKER_TEXT']}" for r in data.get('MARKERS', [])] or [tr('ui.no_markers')]
        if data.get('HINTS'):
            lines += ['', '**' + tr('ui.language_notes') + '** · ' + tr('ui.for_review_only_the_text_remains_unchanged')]
            lines += [f"- {r['H_KIND_TEXT']}: {r['H_TEXT']}" + (' (“' + r['H_QUOTE'] + '”)' if r['H_QUOTE'] else '') for r in data['HINTS']]
        lines += ['', '---', '', data['SECTION_MANUSCRIPT'], '', '---']
        items = [('T', view_message('section_ui.edit_text')), ('F', view_message('section_ui.section_fields')),
                 ('FS', view_message('section_ui.revoke_writing' if data['APPROVAL_WRITING'] == 'true' else 'section_ui.grant_writing')),
                 ('FA', view_message('section_ui.revoke_section' if data['APPROVAL_SECTION'] == 'true' else 'section_ui.grant_section')),
                 ('RS', view_message('section_ui.research_now')), ('GS', view_message('section_ui.ghostwriting_now')), ('BI', tr('ui.images')),
                 ('FV', tr('ui.suggest_characters_from_the_text'))]
        for direction, offset, key in [('PREV', -1, 'ui.previous_section'), ('NEXT', 1, 'ui.next_section')]:
            if data.get(direction + '_SECTION_ID'):
                number = int(data['SECTION_NUMBER'].split('.')[1]) + offset
                items.append((f"{data['CHAPTER_NUMBER']}.{number}", tr(key)))
        lines += [menu(items + [('K', tr('ui.to_chapter'))])]
    elif template == 'buecherregal':
        rows = data.get('BOOKS', [])
        lines = ['### 📚 ' + tr('ui.library_2'), data['LIBRARY_NAME'] + ' · ' + data['BOOK_COUNT_TEXT'], '']
        if rows:
            lines += [native('library_table'), '|--:|---|---|---|---|--:|']
            group = None
            for i, row in enumerate(rows, 1):
                if row['BOOK_SERIES'] != group:
                    group = row['BOOK_SERIES']
                    label = native('series_heading', title=row['BOOK_SERIES_TITLE']) + ' (`' + row['BOOK_SERIES_KEY'] + '`)' if group else tr('ui.standalone_books')
                    lines += ['| | **' + cell(label) + '** | | | | |']
                title = (row['BOOK_VOLUME_TEXT'] + ': ' if row['BOOK_VOLUME_TEXT'] else '') + row['BOOK_TITLE']
                pending = ' · ⏳ ' + row['BOOK_PENDING_TEXT'] if row['BOOK_PENDING_TEXT'] else ''
                lines += [f'| {i} | **{cell(title)}** ({cell(row["BOOK_TITLE_SHORT"])}){pending} | {row["BOOK_STATE_TEXT"]} | {row["BOOK_PROGRESS_TEXT"]} | {row["BOOK_EDITION_TEXT"]} | {row["BOOK_COST"]} |']
        else:
            lines += [native('no_books')]
        if data.get('EMPTY_SERIES'):
            lines += ['', tr('ui.series_without_volumes') + ' ' + ', '.join(s['S_TITLE'] + ' (`' + s['S_KEY'] + '`)' for s in data['EMPTY_SERIES'])]
        items = [('1' if len(rows) == 1 else f'1–{len(rows)}', native('open_book'))] if rows else []
        keys = {r.get('BOOK_SERIES_KEY') for r in rows if r.get('BOOK_SERIES_KEY')} | {s['S_KEY'] for s in data.get('EMPTY_SERIES', [])}
        if keys:
            items.append(('S1' if len(keys) == 1 else f'S1–S{len(keys)}', native('open_series')))
        lines += ['', '---', menu(items + [('N', tr('ui.new_book')), ('NS', tr('ui.new_series')), ('D', tr('ui.data'))])]
    else:
        raise ValueError('English view not yet supported: ' + template)
    return '\n'.join(lines) + '\n'


def label(key, **fields):
    """UI-Platzhalter nur im festen Sprachtext füllen, niemals in Nutzdaten."""
    import re
    return re.sub(r'\{\{([A-Z_]+)\}\}', lambda m: str(fields.get(m[1], m[0])), texts()[key])


def field_table(rows):
    lines = [native('field_table'), '|---|---|']
    for title, value in rows:
        content = native('empty') if value is None or value == '' else cell(value)
        lines.append(f'| {title} | {content} |')
    return lines


def render_form(template, data):
    required = lambda key: native('required', field=tr(key))
    if template == 'projektdaten-bearbeiten':
        lines = ['### 📝 ' + tr('ui.edit_project_details'), '']
        rows = [(required('ui.title'), data['PROJECT_TITLE']), (tr('ui.short_title'), data['PROJECT_TITLE_SHORT']),
                (tr('ui.author'), data['PROJECT_AUTHOR']), (tr('ui.summary'), data['PROJECT_DESCRIPTION_SHORT']),
                (tr('ui.description'), data['PROJECT_DESCRIPTION'])]
        hint = native('form_hint')
    elif template == 'kapitel-bearbeiten':
        lines = ['### 📝 ' + label('ui.edit_chapter', CHAPTER_NUMBER=data['CHAPTER_NUMBER']), '']
        rows = [(required('ui.title'), data['CHAPTER_TITLE']), (tr('ui.subtitle'), data['CHAPTER_SUBTITLE']),
                (tr('ui.summary'), data['CHAPTER_SUMMARY']), (tr('ui.chapter_goal'), data['CHAPTER_GOAL'])]
        hint = native('form_hint')
    elif template in ('kapitel-anlegen', 'abschnitt-anlegen'):
        chapter = template == 'kapitel-anlegen'
        heading = tr('ui.add_a_new_chapter') if chapter else label('ui.new_section_in_chapter', CHAPTER_NUMBER=data['CHAPTER_NUMBER'])
        lines = ['### ➕ ' + heading, '']
        selected = next((i for i, row in enumerate(data['POSITIONS']) if row['POSITION_SELECTED']), 0)
        rows = [(required('ui.title'), ''), (tr('ui.summary'), ''),
                (tr('ui.chapter_goal' if chapter else 'ui.section_goal'), ''), (tr('ui.position'), selected)]
        if not chapter:
            fact_check = data['FACT_CHECK_DEFAULT']
            choice = {'disabled': 'ui.off', 'optional': 'ui.optional', 'requested': 'ui.requested'}.get(fact_check)
            rows.append((tr('ui.fact_check'), tr(choice) if choice else fact_check))
        hint = native('create_chapter_hint' if chapter else 'create_section_hint')
    elif template == 'buch-anlegen':
        lines = ['### 📗 ' + tr('ui.new_book'), '', tr('ui.book_create_intro'), '']
        if data.get('SERIES_TEXT'):
            lines += ['📚 ' + data['SERIES_TEXT'], '']
        if data.get('ERROR_TEXT'):
            lines += ['> ' + native('original_error') + ': ' + data['ERROR_TEXT'], '']
        rows = [(required('ui.working_title'), data['WORKING_TITLE']), (tr('ui.short_title'), data['TITLE_SHORT']), (tr('ui.author'), data['AUTHOR'])]
        hint = native('book_create_hint', prefix=data['BRANCH_PREFIX'])
    else:
        raise ValueError('English form not yet supported: ' + template)
    lines += field_table(rows)
    if data.get('POSITIONS'):
        lines += ['', '**' + tr('ui.position') + '**']
        for i, row in enumerate(data['POSITIONS']):
            default = ' ' + native('default_position') if row['POSITION_SELECTED'] else ''
            lines.append(f'`{i}` {row["POSITION_LABEL"]}{default}  ')
    if data.get('TAKEN'):
        lines += ['', native('already_taken') + ' ' + ', '.join('`' + row['TAKEN_SLUG'] + '` (' + row['TAKEN_BRANCH'] + ')' for row in data['TAKEN'])]
    lines += ['', hint]
    return '\n'.join(lines) + '\n'


def validate_resources():
    """Geteilten UI-Katalog und die von dieser Textfassung verbrauchten Schlüssel prüfen."""
    import ast
    import re
    errors = []
    try:
        resources = {lang: json.loads((RESOURCE / (lang + '.json')).read_text(encoding='utf-8')) for lang in ('de', 'en')}
        reference = resources['de']
        if not all(isinstance(value, dict) for value in resources.values()):
            raise ValueError('Sprachdateien müssen Objekte sein')
        native_keys = set(json.loads((RESOURCE / 'native-keys.json').read_text(encoding='utf-8')))
        template_keys = set(json.loads((RESOURCE / 'template-keys.json').read_text(encoding='utf-8')))
        if set(reference) != native_keys | template_keys:
            errors.append('UI-Katalog: fehlende oder unbenutzte Schlüssel')
        tree = ast.parse(Path(__file__).read_text(encoding='utf-8'))
        constants = {n.value for n in ast.walk(tree) if isinstance(n, ast.Constant) and isinstance(n.value, str)}
        if {key for key in native_keys if key.removeprefix('native.') not in constants and not (key.endswith('_one') and key.removeprefix('native.')[:-4] in constants)}:
            errors.append('Textansichten: unbenutzte Übersetzungsschlüssel')
        for lang, texts in resources.items():
            if set(texts) != set(reference):
                errors.append(lang + ': abweichende UI-Schlüssel')
            for key, value in texts.items():
                if not isinstance(value, str) or not value.strip():
                    errors.append(lang + ': leere UI-Übersetzung: ' + key)
                    continue
                fields = lambda text: set(re.findall(r'\{\{[A-Z_]+\}\}|(?<!\{)\{[a-z_]+\}(?!\})', text))
                if fields(value) != fields(reference.get(key, '')):
                    errors.append(lang + ': abweichende UI-Platzhalter: ' + key)
    except (OSError, ValueError, TypeError):
        errors.append('UI-Sprachressourcen fehlen oder sind ungültig')
    return errors
