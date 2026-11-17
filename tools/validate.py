"""Build-time validation for src/protocols/*.json (schema: design spec section 8)."""

CATEGORIES = {'life', 'injury', 'environment', 'bites', 'illness', 'advanced'}
TOOLS = {'tq', 'cpr', 'rate', 'burn'}
ACTION_WARN_LEN = 200
RESERVED_PROTOCOL_IDS = {'tool', 'report', 'all'}
RESERVED_STEP_IDS = {'all'}
ADVANCED_FIELDS = ('indications', 'contraindications', 'equipment', 'complications')


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


def draft_ids(protocols):
    """Ids of protocols marked "draft": true (content not yet checked against its source)."""
    return [p['id'] for p in protocols
            if isinstance(p, dict) and p.get('draft') is True and isinstance(p.get('id'), str)]


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
        if _blank(p.get('title')):
            errors.append(f'{where}: missing title')
        cat = p.get('category')
        if _blank(cat):
            errors.append(f'{where}: missing category')
        elif cat not in CATEGORIES:
            errors.append(f'{where}: unknown category {cat!r}')
        if not isinstance(p.get('sources'), list) or not p['sources']:
            errors.append(f'{where}: sources must be a non-empty list')
        if _blank(p.get('reviewed')):
            errors.append(f'{where}: missing reviewed date')
        if p.get('tier') == 'advanced':
            for f in ADVANCED_FIELDS:
                if not p.get(f):
                    errors.append(f'{where}: advanced protocol missing {f}')
        if p.get('draft') is True:
            warnings.append(f'{pid if isinstance(pid, str) else where}: draft, not source-checked')

        steps = p.get('steps')
        if not isinstance(steps, list) or not steps:
            errors.append(f'{where}: steps must be a non-empty list')
            continue
        _validate_steps(where, steps, fig_names, errors, warnings)
    return errors, warnings
