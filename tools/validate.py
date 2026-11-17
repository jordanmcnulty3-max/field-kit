"""Build-time validation for src/protocols/*.json (schema: design spec section 8)."""

CATEGORIES = {'life', 'injury', 'environment', 'bites', 'illness', 'advanced'}
TOOLS = {'tq', 'cpr', 'rate', 'burn'}
ACTION_WARN_LEN = 200
RESERVED_PROTOCOL_IDS = {'tool', 'report', 'all'}
RESERVED_STEP_IDS = {'all'}
ADVANCED_FIELDS = ('indications', 'contraindications', 'equipment', 'complications')


def _reachable(steps):
    """Step ids reachable from steps[0]. A step falls through to the next array item,
    unless it has `ask` (yes/no targets) or `end: true`. Unknown targets are ignored here."""
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
        todo.extend(t for t in nxt if t in index)
    return seen


def _blank(v):
    return not isinstance(v, str) or not v.strip()


def validate(protocols, fig_names):
    """Return (errors, warnings), each a list of strings."""
    errors, warnings = [], []
    seen_ids = set()
    for n, p in enumerate(protocols):
        pid = p.get('id')
        where = f'protocol {pid!r}' if not _blank(pid) else f'protocol #{n}'
        if _blank(pid):
            errors.append(f'{where}: missing id')
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

        steps = p.get('steps')
        if not isinstance(steps, list) or not steps:
            errors.append(f'{where}: steps must be a non-empty list')
            continue
        step_ids, ids_ok = set(), True
        for i, s in enumerate(steps):
            sid = s.get('id')
            swhere = f'{where} step {sid!r}' if not _blank(sid) else f'{where} step #{i}'
            if _blank(sid):
                errors.append(f'{swhere}: missing id')
                ids_ok = False
            else:
                if sid in step_ids:
                    errors.append(f'{swhere}: duplicate step id')
                step_ids.add(sid)
                if sid in RESERVED_STEP_IDS:
                    errors.append(f'{swhere}: step id is reserved')
            if _blank(s.get('text')):
                errors.append(f'{swhere}: missing text')
            elif len(s['text']) > ACTION_WARN_LEN:
                warnings.append(f'{swhere}: action text is {len(s["text"])} chars (over {ACTION_WARN_LEN}); move extra to detail')
            if 'fig' in s and s['fig'] not in fig_names:
                errors.append(f'{swhere}: unknown fig {s["fig"]!r}')
            if 'tool' in s and s['tool'] not in TOOLS:
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
                        elif t not in {x.get('id') for x in steps}:
                            errors.append(f'{swhere}: ask.{side} target {t!r} does not exist')
        if ids_ok and not any('duplicate step id' in e for e in errors if e.startswith(where)):
            reach = _reachable(steps)
            for s in steps:
                if s['id'] not in reach:
                    errors.append(f'{where} step {s["id"]!r}: unreachable from first step')
    return errors, warnings
