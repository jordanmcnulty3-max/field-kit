"""Task 2: the 14 converted topics equal the v6 text minus the listed deletions. Plain pytest, no browser."""
import glob
import html
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, 'figs'))

import figs  # noqa: E402
from tools.validate import validate_topics  # noqa: E402

FIXTURE = os.path.join(ROOT, 'tests', 'fixtures', 'survival-v6.html')
MIGRATION = os.path.join(ROOT, 'docs', 'v7-migration.md')
FIG_RE = re.compile(r'\{\{fig:([a-z0-9-]+)\|(.*?)\}\}', re.S)


def norm(s):
    return re.sub(r'\s+', ' ', s).strip()


def v6():
    return open(FIXTURE, encoding='utf-8').read()


def plain(fragment):
    """Old HTML to text: figure markers become captions, tags become spaces, entities are decoded."""
    fragment = FIG_RE.sub(lambda m: ' ' + m.group(2) + ' ', fragment)
    return norm(html.unescape(re.sub(r'<[^>]+>', ' ', fragment)))


def old_topics():
    out = {}
    for chunk in v6().split('</details>')[:-1]:
        tid = re.search(r'<details class="ref" id="(surv-[^"]+)"', chunk).group(1)
        out[tid] = plain(chunk[chunk.index('<details'):])
    return out


def migration_list(section):
    """Entries under '## <section>' as lists of fields split on ' || ' (quoted text unquoted)."""
    doc = open(MIGRATION, encoding='utf-8').read()
    body = re.search(r'^## %s\n(.*?)(?=^## |\Z)' % re.escape(section), doc, re.S | re.M).group(1)
    entries = []
    for line in body.splitlines():
        if line.startswith('- ') and ' || ' in line:
            fields = [f.strip() for f in line[2:].split(' || ')]
            entries.append([re.fullmatch(r'"(.*)"', f, re.S).group(1) if f.startswith('"') else f for f in fields])
    return entries


def new_topics():
    return {t['id']: t for t in (json.load(open(p, encoding='utf-8')) for p in sorted(glob.glob(os.path.join(ROOT, 'src', 'survival', '*.json'))))}


def flatten(topic, skip_headings=()):
    """Title, then headings, list items, paragraphs, cells and figure captions in order. Link blocks are ignored."""
    parts = [topic['title']]
    for sec in topic['sections']:
        if sec['h'] not in skip_headings:
            parts.append(sec['h'])
        for b in sec['blocks']:
            if 'p' in b or 'warn' in b:
                parts.append(b.get('p') or b['warn'])
            elif 'list' in b or 'steps' in b:
                parts.extend(b.get('list') or b['steps'])
            elif 'table' in b:
                parts.extend(b['table']['head'])
                for row in b['table']['rows']:
                    parts.extend(row)
            elif 'fig' in b:
                parts.append(b['cap'])
    return norm(' '.join(parts))


def test_converted_text_equals_old_text_minus_listed_deletions():
    old, new = old_topics(), new_topics()
    assert len(old) == 14
    assert set(new) == set(old) | {'surv-priorities'}
    deletions, added = migration_list('Deletions'), migration_list('Added headings')
    for tid, text in old.items():
        for d_id, removed, _reason in deletions:
            if d_id == tid:
                assert removed in text, f'{tid}: listed deletion not found in v6 text: {removed!r}'
                text = text.replace(removed, '', 1)
        skip = {h[0] for h_id, *h in added if h_id == tid}
        assert flatten(new[tid], skip) == norm(text), tid


def test_priorities_has_old_priorities_and_picker_bullets_with_frostbite_replaced_by_link():
    src = v6()
    prio = plain(re.search(r'<h2>Priorities</h2>(.*?)</div>', src, re.S).group(1))
    removed = [r for tid, r, _ in migration_list('Deletions') if tid == 'surv-priorities']
    assert len(removed) == 1
    parts = ['Priorities', prio]
    for region, heading in (('temperate', 'Forest'), ('cold', 'Cold and snow'), ('coastal', 'Coast and sea')):
        frag = re.search(r'<div class="region" data-region="%s"[^>]*>(.*?)</div>' % region, src, re.S).group(1)
        parts.append(heading)
        parts.extend(plain(li) for li in re.findall(r'<li>(.*?)</li>', frag, re.S))
    expected = norm(' '.join(parts))
    assert removed[0] in expected
    expected = norm(expected.replace(' ' + removed[0], '', 1))
    topic = new_topics()['surv-priorities']
    assert flatten(topic) == norm('Priorities ' + expected)
    links = [b for s in topic['sections'] for b in s['blocks'] if 'link' in b]
    assert [b['link'] for b in links] == ['p:frostbite']
    cold = [s for s in topic['sections'] if s['h'] == 'Cold and snow'][0]
    assert cold['blocks'][-1]['link'] == 'p:frostbite'
    assert 'frostbite' not in json.dumps(cold['blocks'][:-1]).lower()


def test_figures_used_equal_old_set_minus_shelter_desert():
    old = {m[0] for m in FIG_RE.findall(v6())}
    new = {b['fig'] for t in new_topics().values() for s in t['sections'] for b in s['blocks'] if 'fig' in b}
    assert 'shelter-desert' in old
    assert new == old - {'shelter-desert'}


def test_every_topic_is_a_draft_with_placeholder_source_and_validates():
    topics = list(new_topics().values())
    for t in topics:
        assert t['draft'] is True and t['reviewed'] == '2026-11-17' and t['category'] == 'basics'
        assert t['sources'] == [{'name': 'Not yet source-checked', 'used': 'Converted from v6 text; checked in Tasks 13 to 16'}]
    errors, _warnings = validate_topics(topics, set(figs.F), {'p:frostbite'})
    assert errors == []
