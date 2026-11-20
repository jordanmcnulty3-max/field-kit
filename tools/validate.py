"""Build-time validation for src/protocols/*.json (schema: design spec section 8)."""
import datetime
import re

CATEGORIES = {'life', 'injury', 'environment', 'bites', 'illness', 'advanced'}
TOOLS = {'tq', 'cpr', 'rate', 'burn'}
ACTION_WARN_LEN = 200
ID_PATTERN = re.compile(r'[a-z0-9][a-z0-9-]{0,59}')
RESERVED_PROTOCOL_IDS = {'tool', 'report', 'all'}
RESERVED_STEP_IDS = {'all'}
ADVANCED_FIELDS = ('indications', 'contraindications', 'equipment', 'complications')
# Every key the shipped data and the app use. Anything else is an error, so a misspelt key cannot be dropped silently.
PROTOCOL_KEYS = {'id', 'title', 'category', 'tier', 'draft', 'keywords', 'summary', 'steps', 'donts', 'evacuate', 'notes',
                 'sources', 'reviewed', 'coach', *ADVANCED_FIELDS}
STEP_KEYS = {'id', 'text', 'detail', 'warn', 'fig', 'tool', 'timer', 'ask', 'end', 'log'}
PROTOCOL_STRINGS = ('summary',)
PROTOCOL_LISTS = ('donts', 'evacuate', 'keywords', 'notes', *ADVANCED_FIELDS)
STEP_STRINGS = ('detail', 'warn', 'log')


def _reachable(steps):
    """Step ids reachable from steps[0]. A step falls through to the next array item,
    unless it has `ask` (yes/no targets) or `end: true`. Unknown targets are ignored here.
    Caller guarantees every step is a dict with a unique string id."""
    ids = [s['id'] for s in steps]
    index = {sid: i for i, sid in enumerate(ids)}
    seen, todo = set(), [ids[0]]
    while todo:
        sid = todo.pop()
        if sid in seen:
            continue
        seen.add(sid)
        step = steps[index[sid]]
        if isinstance(step.get('ask'), dict):
            nxt = [step['ask'].get('yes'), step['ask'].get('no')]
        elif step.get('end') is True:
            nxt = []
        else:
            i = index[sid] + 1
            nxt = [ids[i]] if i < len(ids) else []
        todo.extend(t for t in nxt if isinstance(t, str) and t in index)
    return seen


def _blank(v):
    return not isinstance(v, str) or not v.strip()


def _pos_int(v):
    return isinstance(v, int) and not isinstance(v, bool) and 0 < v <= 99


def _bad_list(v):
    """Not a list of non-blank strings."""
    return not (isinstance(v, list) and all(isinstance(x, str) and x.strip() for x in v))


def _pos_num(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool) and v == v and v > 0 and v != float('inf')


def _unknown_keys(where, obj, allowed, errors):
    for k in sorted(set(obj) - allowed, key=str):
        errors.append(f'{where}: unknown key {k!r}')


def draft_ids(protocols):
    """Ids of protocols marked "draft": true (content not yet checked against its source)."""
    return [p['id'] for p in protocols
            if isinstance(p, dict) and p.get('draft') is True and isinstance(p.get('id'), str)]


REPORT_DRAFT_MARKER = '/* REPORT_WORDING_DRAFT */'


def report_wording_is_draft(source):
    """True while src/reports.js carries the marker line, i.e. the 9-line wording is not yet checked against its source."""
    return any(line.strip() == REPORT_DRAFT_MARKER for line in str(source).splitlines())


def _validate_steps(where, steps, fig_names, errors, warnings):
    step_ids, dup, bad = set(), False, False
    for s in steps:
        if isinstance(s, dict) and isinstance(s.get('id'), str) and s['id'].strip():
            step_ids.add(s['id'])
    seen = set()
    for i, s in enumerate(steps):
        if not isinstance(s, dict):
            errors.append(f'{where} step #{i}: step must be an object')
            bad = True
            continue
        sid = s.get('id')
        if _blank(sid):
            errors.append(f'{where} step #{i}: missing or invalid id')
            bad = True
            swhere = f'{where} step #{i}'
        else:
            swhere = f'{where} step {sid!r}'
            if sid in seen:
                errors.append(f'{swhere}: duplicate step id')
                dup = True
            seen.add(sid)
            if sid in RESERVED_STEP_IDS:
                errors.append(f'{swhere}: step id is reserved')
        _unknown_keys(swhere, s, STEP_KEYS, errors)
        for k in STEP_STRINGS:
            if k in s and not isinstance(s[k], str):
                errors.append(f'{swhere}: {k} must be a string')
        if 'end' in s and not isinstance(s['end'], bool):
            errors.append(f'{swhere}: end must be true or false')
        if 'timer' in s:
            t = s['timer']
            if not (isinstance(t, dict) and _pos_num(t.get('seconds')) and not _blank(t.get('label'))):
                errors.append(f'{swhere}: timer must be an object with a positive number of seconds and a label')
        if _blank(s.get('text')):
            errors.append(f'{swhere}: missing text')
        elif len(s['text']) > ACTION_WARN_LEN:
            warnings.append(f'{swhere}: action text is {len(s["text"])} chars (over {ACTION_WARN_LEN}); move extra to detail')
        if 'fig' in s and not (isinstance(s['fig'], str) and s['fig'] in fig_names):
            errors.append(f'{swhere}: unknown fig {s["fig"]!r}')
        if 'tool' in s and not (isinstance(s['tool'], str) and s['tool'] in TOOLS):
            errors.append(f'{swhere}: unknown tool {s["tool"]!r}')
        if 'ask' in s:
            ask = s['ask']
            if not isinstance(ask, dict):
                errors.append(f'{swhere}: ask must be an object')
            else:
                for side in ('yes', 'no'):
                    t = ask.get(side)
                    if t is None:
                        errors.append(f'{swhere}: ask missing {side} target')
                    elif not (isinstance(t, str) and t in step_ids):
                        errors.append(f'{swhere}: ask.{side} target {t!r} does not exist')
    if not (bad or dup):
        reach = _reachable(steps)
        for s in steps:
            if s['id'] not in reach:
                errors.append(f'{where} step {s["id"]!r}: unreachable from first step')


def validate(protocols, fig_names):
    """Return (errors, warnings), each a list of strings. Never raises on JSON-decodable input."""
    errors, warnings = [], []
    if not isinstance(protocols, list):
        return ['protocols must be a list'], warnings
    seen_ids = set()
    for n, p in enumerate(protocols):
        if not isinstance(p, dict):
            errors.append(f'protocol #{n}: must be an object')
            continue
        pid = p.get('id')
        where = f'protocol {pid!r}' if not _blank(pid) else f'protocol #{n}'
        if _blank(pid):
            errors.append(f'{where}: missing or invalid id')
        else:
            if pid in seen_ids:
                errors.append(f'{where}: duplicate protocol id')
            seen_ids.add(pid)
            if pid in RESERVED_PROTOCOL_IDS:
                errors.append(f'{where}: id is reserved')
            if not ID_PATTERN.fullmatch(pid):
                errors.append(f'{where}: id must be lowercase letters, digits and hyphens, starting with a letter or digit, at most 60 characters')
        _unknown_keys(where, p, PROTOCOL_KEYS, errors)
        if _blank(p.get('title')):
            errors.append(f'{where}: missing title')
        for k in PROTOCOL_STRINGS:
            if k in p and not isinstance(p[k], str):
                errors.append(f'{where}: {k} must be a string')
        for k in PROTOCOL_LISTS:
            if k in p and _bad_list(p[k]):
                errors.append(f'{where}: {k} must be a list of non-blank strings')
        if 'draft' in p and not isinstance(p['draft'], bool):
            errors.append(f'{where}: draft must be true or false')
        if 'tier' in p and p['tier'] != 'advanced':
            errors.append(f'{where}: tier can only be "advanced"')
        cat = p.get('category')
        if _blank(cat):
            errors.append(f'{where}: missing category')
        elif cat not in CATEGORIES:
            errors.append(f'{where}: unknown category {cat!r}')
        if not isinstance(p.get('sources'), list) or not p['sources']:
            errors.append(f'{where}: sources must be a non-empty list')
        elif not all(isinstance(x, dict) and not _blank(x.get('name')) for x in p['sources']):
            errors.append(f'{where}: every source must be an object with a name')
        if _blank(p.get('reviewed')):
            errors.append(f'{where}: missing reviewed date')
        if p.get('tier') == 'advanced':
            for f in ADVANCED_FIELDS:
                if not p.get(f):
                    errors.append(f'{where}: advanced protocol missing {f}')
        if 'coach' in p:
            c = p['coach']
            if not (isinstance(c, dict) and all(_pos_int(c.get(k)) for k in ('compressions', 'breaths'))):
                errors.append(f'{where}: coach must be an object with whole numbers 1 to 99 for compressions and breaths')
        if 'notes' in p and not (isinstance(p['notes'], list) and p['notes'] and all(isinstance(n, str) and n.strip() for n in p['notes'])):
            errors.append(f'{where}: notes must be a non-empty list of non-blank strings')
        if p.get('draft') is True:
            warnings.append(f'{pid if isinstance(pid, str) else where}: draft, not source-checked')

        steps = p.get('steps')
        if not isinstance(steps, list) or not steps:
            errors.append(f'{where}: steps must be a non-empty list')
            continue
        _validate_steps(where, steps, fig_names, errors, warnings)
    return errors, warnings


TOPIC_CATEGORIES = {'basics', 'water', 'heat', 'radiation', 'food', 'land', 'comms', 'staying', 'moving', 'town'}
WHERE = {'town', 'rural', 'woods', 'coast'}
WHEN = {'cold', 'warm'}
RESERVED_TOPIC_IDS = {'tool', 'list'}
TOPIC_ID_PATTERN = re.compile(r'surv-[a-z0-9-]{1,55}')
DATE_PATTERN = re.compile(r'\d{4}-\d{2}-\d{2}')
# fig blocks carry figSvg and figLabel only after the build has run, so they are not allowed in source files.
TOPIC_KEYS = {'id', 'title', 'category', 'keywords', 'summary', 'where', 'when', 'doFirst', 'sections', 'sources',
              'reviewed', 'asOf', 'draft'}
SECTION_KEYS = {'h', 'blocks'}
BLOCK_SHAPES = {'p', 'list', 'steps', 'warn', 'table', 'fig', 'link'}
BLOCK_COMPANIONS = {'fig': 'cap', 'link': 'label'}
TABLE_KEYS = {'head', 'rows'}
CHECKLIST_KEYS = {'id', 'title', 'category', 'summary', 'items', 'sources', 'reviewed', 'draft'}
ITEM_KEYS = {'id', 'text', 'note', 'qty'}
QTY_KEYS = {'amount', 'unit', 'per'}
QTY_PER = ('person', 'personDay')
# Survival tools the app registers (src/survival-tools.js); each one is a link target u:<name>.
TOOL_NAMES = ('daylight', 'sos', 'water', 'windchill')
TOOLDATA_KEYS = {'id', 'title', 'values', 'grid', 'sources', 'reviewed', 'draft'}
TOOLDATA_GRID_KEYS = {'temps', 'winds', 'chill', 'bands', 'bandMinutes'}
TOOLDATA_VALUE_KEYS = {'value', 'unit', 'note'}
TOOLDATA_ID_PATTERN = re.compile(r'[a-z][a-z0-9-]{0,39}')


def _is_date(v):
    if not (isinstance(v, str) and DATE_PATTERN.fullmatch(v)):
        return False
    try:
        datetime.date.fromisoformat(v)
    except ValueError:
        return False
    return True


def _check_sources(where, item, errors):
    src = item.get('sources')
    if not isinstance(src, list) or not src:
        errors.append(f'{where}: sources must be a non-empty list')
    elif not all(isinstance(x, dict) and not _blank(x.get('name')) and not _blank(x.get('used')) for x in src):
        errors.append(f'{where}: every source must be an object with a name and what it was used for (used)')


def _check_reviewed(where, item, errors):
    if _blank(item.get('reviewed')):
        errors.append(f'{where}: missing reviewed date')
    elif not _is_date(item['reviewed']):
        errors.append(f'{where}: reviewed must be a date written YYYY-MM-DD')


def _check_draft(where, item, ident, errors, warnings):
    if 'draft' in item and not isinstance(item['draft'], bool):
        errors.append(f'{where}: draft must be true or false')
    if item.get('draft') is True:
        warnings.append(f'{ident if isinstance(ident, str) else where}: draft, not source-checked')


def _check_id(where, ident, seen, pattern, pattern_msg, reserved, errors):
    if _blank(ident):
        errors.append(f'{where}: missing or invalid id')
        return
    if ident in seen:
        errors.append(f'{where}: duplicate id')
    seen.add(ident)
    if ident in reserved:
        errors.append(f'{where}: id is reserved')
    if not pattern.fullmatch(ident):
        errors.append(f'{where}: {pattern_msg}')


def topic_draft_ids(items):
    """Ids of topics or checklists marked "draft": true. Same rule as draft_ids."""
    return draft_ids(items)


def _validate_block(where, block, fig_names, link_keys, errors):
    if not isinstance(block, dict):
        errors.append(f'{where}: block must be an object')
        return
    shapes = sorted(k for k in block if k in BLOCK_SHAPES)
    if len(shapes) != 1:
        errors.append(f'{where}: block must have exactly one of {", ".join(sorted(BLOCK_SHAPES))} (has {", ".join(shapes) or "none"})')
        _unknown_keys(where, block, BLOCK_SHAPES | set(BLOCK_COMPANIONS.values()), errors)
        return
    shape = shapes[0]
    companion = BLOCK_COMPANIONS.get(shape)
    _unknown_keys(where, block, {shape} | ({companion} if companion else set()), errors)
    v = block[shape]
    if shape in ('p', 'warn'):
        if _blank(v):
            errors.append(f'{where}: {shape} must be non-blank text')
    elif shape in ('list', 'steps'):
        if not v or _bad_list(v):
            errors.append(f'{where}: {shape} must be a non-empty list of non-blank strings')
    elif shape == 'table':
        if not isinstance(v, dict):
            errors.append(f'{where}: table must be an object with head and rows')
            return
        _unknown_keys(f'{where} table', v, TABLE_KEYS, errors)
        head, rows = v.get('head'), v.get('rows')
        if not head or _bad_list(head):
            errors.append(f'{where}: table head must be a non-empty list of non-blank strings')
            head = None
        if not isinstance(rows, list) or not rows:
            errors.append(f'{where}: table rows must be a non-empty list')
            return
        for n, row in enumerate(rows, 1):
            if _bad_list(row):
                errors.append(f'{where}: table row {n} must be a list of non-blank strings')
            elif head is not None and len(row) != len(head):
                errors.append(f'{where}: table row {n} has {len(row)} cells but head has {len(head)}')
    elif shape == 'fig':
        if _blank(v) or v not in fig_names:
            errors.append(f'{where}: unknown figure {v!r}')
    elif shape == 'link':
        if _blank(v) or v not in link_keys:
            errors.append(f'{where}: unknown link {v!r}')
    if companion and _blank(block.get(companion)):
        errors.append(f'{where}: {shape} block missing {companion}')


def _validate_sections(where, sections, fig_names, link_keys, errors):
    if not isinstance(sections, list) or not sections:
        errors.append(f'{where}: sections must be a non-empty list')
        return
    for sn, sec in enumerate(sections, 1):
        sw = f'{where} section {sn}'
        if not isinstance(sec, dict):
            errors.append(f'{sw}: must be an object')
            continue
        _unknown_keys(sw, sec, SECTION_KEYS, errors)
        if _blank(sec.get('h')):
            errors.append(f'{sw}: missing h (heading)')
        blocks = sec.get('blocks')
        if not isinstance(blocks, list) or not blocks:
            errors.append(f'{sw}: blocks must be a non-empty list')
            continue
        for bn, block in enumerate(blocks, 1):
            _validate_block(f'{sw} block {bn}', block, fig_names, link_keys, errors)


def validate_topics(topics, fig_names, link_keys):
    """Return (errors, warnings) for src/survival/*.json topics (spec section 5.3). Never raises on JSON-decodable input."""
    errors, warnings = [], []
    if not isinstance(topics, list):
        return ['topics must be a list'], warnings
    seen = set()
    for n, t in enumerate(topics):
        if not isinstance(t, dict):
            errors.append(f'topic #{n}: must be an object')
            continue
        tid = t.get('id')
        where = f'topic {tid!r}' if not _blank(tid) else f'topic #{n}'
        _check_id(where, tid, seen, TOPIC_ID_PATTERN,
                  'id must be "surv-" followed by 1 to 55 lowercase letters, digits or hyphens', RESERVED_TOPIC_IDS, errors)
        _unknown_keys(where, t, TOPIC_KEYS, errors)
        if _blank(t.get('title')):
            errors.append(f'{where}: missing title')
        if 'summary' in t and not isinstance(t['summary'], str):
            errors.append(f'{where}: summary must be a string')
        for k in ('keywords', 'doFirst'):
            if k in t and _bad_list(t[k]):
                errors.append(f'{where}: {k} must be a list of non-blank strings')
        cat = t.get('category')
        if _blank(cat):
            errors.append(f'{where}: missing category')
        elif cat not in TOPIC_CATEGORIES:
            errors.append(f'{where}: unknown category {cat!r}')
        for k, allowed in (('where', WHERE), ('when', WHEN)):
            if k not in t:
                continue
            if _bad_list(t[k]):
                errors.append(f'{where}: {k} must be a list of non-blank strings')
            else:
                for x in t[k]:
                    if x not in allowed:
                        errors.append(f'{where}: unknown {k} value {x!r}')
        _check_sources(where, t, errors)
        _check_reviewed(where, t, errors)
        if 'asOf' in t and not _is_date(t['asOf']):
            errors.append(f'{where}: asOf must be a date written YYYY-MM-DD')
        _check_draft(where, t, tid, errors, warnings)
        _validate_sections(where, t.get('sections'), fig_names, link_keys, errors)
    return errors, warnings


def _check_qty(where, q, errors):
    qw = f'{where} qty'
    if not isinstance(q, dict):
        errors.append(f'{qw}: must be an object with amount, unit and per')
        return
    _unknown_keys(qw, q, QTY_KEYS, errors)
    if not _pos_num(q.get('amount')):
        errors.append(f'{qw}: amount must be a number greater than 0')
    if _blank(q.get('unit')):
        errors.append(f'{qw}: unit must be non-blank text')
    if q.get('per') not in QTY_PER:
        errors.append(f'{qw}: per must be one of {", ".join(QTY_PER)} (got {q.get("per")!r})')


def validate_checklists(lists, link_keys):
    """Return (errors, warnings) for checklist files. link_keys is accepted for symmetry with validate_topics;
    checklist items carry no links, so it is unused. Never raises on JSON-decodable input."""
    errors, warnings = [], []
    if not isinstance(lists, list):
        return ['checklists must be a list'], warnings
    seen = set()
    for n, c in enumerate(lists):
        if not isinstance(c, dict):
            errors.append(f'checklist #{n}: must be an object')
            continue
        cid = c.get('id')
        where = f'checklist {cid!r}' if not _blank(cid) else f'checklist #{n}'
        _check_id(where, cid, seen, ID_PATTERN,
                  'id must be lowercase letters, digits and hyphens, starting with a letter or digit, at most 60 characters',
                  (), errors)
        _unknown_keys(where, c, CHECKLIST_KEYS, errors)
        if _blank(c.get('title')):
            errors.append(f'{where}: missing title')
        if 'summary' in c and not isinstance(c['summary'], str):
            errors.append(f'{where}: summary must be a string')
        cat = c.get('category')
        if _blank(cat):
            errors.append(f'{where}: missing category')
        elif cat not in TOPIC_CATEGORIES:
            errors.append(f'{where}: unknown category {cat!r}')
        _check_sources(where, c, errors)
        _check_reviewed(where, c, errors)
        _check_draft(where, c, cid, errors, warnings)
        items = c.get('items')
        if not isinstance(items, list) or not items:
            errors.append(f'{where}: items must be a non-empty list')
            continue
        seen_items = set()
        for i, it in enumerate(items, 1):
            iw = f'{where} item {i}'
            if not isinstance(it, dict):
                errors.append(f'{iw}: must be an object')
                continue
            _unknown_keys(iw, it, ITEM_KEYS, errors)
            iid = it.get('id')
            if _blank(iid) or not ID_PATTERN.fullmatch(iid):
                errors.append(f'{iw}: missing or invalid item id')
            elif iid in seen_items:
                errors.append(f'{iw}: duplicate item id {iid!r}')
            else:
                seen_items.add(iid)
            if _blank(it.get('text')):
                errors.append(f'{iw}: text must be non-blank')
            if 'note' in it and _blank(it['note']):
                errors.append(f'{iw}: note must be non-blank text')
            if 'qty' in it:
                _check_qty(iw, it['qty'], errors)
    return errors, warnings


def _finite_num(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool) and v == v and v not in (float('inf'), float('-inf'))


def _num_list(where, name, v, errors, order, positive=False):
    """Check a non-empty list of finite numbers in strict order ('asc' or 'desc'), optionally all > 0. True when valid."""
    if not isinstance(v, list) or not v:
        errors.append(f'{where}: {name} must be a non-empty list of numbers')
        return False
    if not all(_finite_num(x) for x in v):
        errors.append(f'{where}: {name} must hold only finite numbers')
        return False
    if positive and any(x <= 0 for x in v):
        errors.append(f'{where}: {name} must all be greater than 0')
        return False
    pairs = list(zip(v, v[1:]))
    if not all((a < b) if order == 'asc' else (a > b) for a, b in pairs):
        errors.append(f'{where}: {name} must be strictly {"ascending" if order == "asc" else "descending"}')
        return False
    return True


def _grid_rows(where, name, v, n_rows, n_cols, errors):
    """Check a winds-by-temps matrix of n_rows lists of n_cols cells. True when the shape is right."""
    if not isinstance(v, list) or len(v) != n_rows:
        errors.append(f'{where}: {name} must have {n_rows} rows (one per wind)')
        return False
    ok = True
    for r, row in enumerate(v):
        if not isinstance(row, list) or len(row) != n_cols:
            errors.append(f'{where}: {name} row {r} must be a list of {n_cols} columns (one per temperature)')
            ok = False
    return ok


def _check_grid(where, grid, errors):
    """The transcribed chart in tool data: temps (F, descending), winds (mph, ascending), chill[w][t], bands[w][t]."""
    gw = f'{where} grid'
    if not isinstance(grid, dict):
        errors.append(f'{gw}: must be an object')
        return
    _unknown_keys(gw, grid, TOOLDATA_GRID_KEYS, errors)
    for k in sorted(TOOLDATA_GRID_KEYS - set(grid)):
        errors.append(f'{gw}: missing {k}')
    temps = grid.get('temps')
    winds = grid.get('winds')
    minutes = grid.get('bandMinutes')
    ok_t = 'temps' in grid and _num_list(gw, 'temps', temps, errors, 'desc')
    ok_w = 'winds' in grid and _num_list(gw, 'winds', winds, errors, 'asc', positive=True)
    ok_m = 'bandMinutes' in grid and _num_list(gw, 'bandMinutes', minutes, errors, 'asc', positive=True)
    shape = {}
    for name in ('chill', 'bands'):
        if name in grid and ok_t and ok_w:
            shape[name] = _grid_rows(gw, name, grid[name], len(winds), len(temps), errors)
        else:
            shape[name] = False
    if shape['chill']:
        for w, row in enumerate(grid['chill']):
            for t, cell in enumerate(row):
                if not _finite_num(cell):
                    errors.append(f'{gw}: chill cell [{w}][{t}] must be a finite number')
    if not shape['bands']:
        return
    cells_ok = True
    for w, row in enumerate(grid['bands']):
        for t, cell in enumerate(row):
            if isinstance(cell, bool) or not isinstance(cell, (int, float)) or not (cell == 0 or (ok_m and cell in minutes)):
                errors.append(f'{gw}: bands cell [{w}][{t}] must be 0 or one of bandMinutes')
                cells_ok = False
    if not cells_ok:
        return

    def severity(cell):    # 0 is least severe; fewer minutes is more severe
        return 0 if cell == 0 else 1 / cell

    bands = grid['bands']
    for w, row in enumerate(bands):
        for t, cell in enumerate(row):
            if t and severity(cell) < severity(row[t - 1]):
                errors.append(f'{gw}: bands cell [{w}][{t}] is less severe than the warmer cell beside it')
            if w and severity(cell) < severity(bands[w - 1][t]):
                errors.append(f'{gw}: bands cell [{w}][{t}] is less severe than the calmer cell above it')


def validate_tooldata(items):
    """Return (errors, warnings) for src/tooldata/*.json: the numbers the Survival tools use. Never raises on JSON-decodable input."""
    errors, warnings = [], []
    if not isinstance(items, list):
        return ['tool data must be a list'], warnings
    seen = set()
    for n, t in enumerate(items):
        if not isinstance(t, dict):
            errors.append(f'tool data #{n}: must be an object')
            continue
        tid = t.get('id')
        where = f'tool data {tid!r}' if not _blank(tid) else f'tool data #{n}'
        _check_id(where, tid, seen, TOOLDATA_ID_PATTERN,
                  'id must be lowercase letters, digits and hyphens, starting with a letter, at most 40 characters',
                  (), errors)
        _unknown_keys(where, t, TOOLDATA_KEYS, errors)
        if _blank(t.get('title')):
            errors.append(f'{where}: missing title')
        _check_sources(where, t, errors)
        _check_reviewed(where, t, errors)
        _check_draft(where, t, tid, errors, warnings)
        if 'grid' in t:
            _check_grid(where, t['grid'], errors)
        values = t.get('values')
        if not isinstance(values, dict) or not values:
            errors.append(f'{where}: values must be a non-empty object')
            continue
        for name, v in values.items():
            vw = f'{where} value {name!r}'
            if _blank(name):
                errors.append(f'{where}: value name must be non-blank text')
            if not isinstance(v, dict):
                errors.append(f'{vw}: must be an object with value and unit')
                continue
            _unknown_keys(vw, v, TOOLDATA_VALUE_KEYS, errors)
            if not _finite_num(v.get('value')):
                errors.append(f'{vw}: value must be a finite number')
            elif v['value'] <= 0:
                errors.append(f'{vw}: value must be greater than 0 (got {v["value"]!r})')
            if isinstance(name, str) and name.startswith('extra') and _blank(v.get('note')):
                errors.append(f'{vw}: an extra needs a note (the planner shows it as the toggle label)')
            if _blank(v.get('unit')):
                errors.append(f'{vw}: unit must be non-blank text')
            if 'note' in v and _blank(v['note']):
                errors.append(f'{vw}: note must be non-blank text')
    return errors, warnings
