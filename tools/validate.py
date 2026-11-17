"""Build-time validation for src/protocols/*.json (schema: design spec section 8)."""
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
