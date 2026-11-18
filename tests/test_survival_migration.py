"""Task 2 migration checks, narrowed in Task 13 to topics still in draft; plus the real-sources check. Plain pytest, no browser."""
import glob
import html
import json
import os
import re
import sys

import pytest

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


def test_every_topic_has_real_sources():
    """Replaces the word-for-word conversion check once source-checking started (Task 13): every topic is either
    still a draft or has no placeholder source."""
    topics = new_topics()
    assert len(topics) == 15
    for tid, t in topics.items():
        assert t['sources'], tid
        if t.get('draft') is True:
            continue
        names = [s['name'] for s in t['sources']]
        assert not any('Not yet source-checked' in n for n in names), tid
        assert all(s['name'].strip() and s['used'].strip() for s in t['sources']), tid


def test_priorities_has_old_priorities_and_picker_bullets_with_frostbite_replaced_by_link():
    """Word-for-word check against the v6 fixture; applies only while surv-priorities is still a draft."""
    if new_topics()['surv-priorities'].get('draft') is not True:
        pytest.skip('surv-priorities has been source-checked (Task 13); its text no longer matches v6 word for word')
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


def test_figures_used_equal_old_set_minus_shelter_desert_and_nav_cross():
    """Draft topics keep exactly their v6 figures; source-checked topics may only drop figures, never add new ones
    here (a figure removed in checking is listed in docs/v7-migration.md)."""
    old_html = v6()
    old = {m[0] for m in FIG_RE.findall(old_html)}
    assert {'shelter-desert', 'nav-cross'} <= old
    olds = {}
    for chunk in old_html.split('</details>')[:-1]:
        tid = re.search(r'<details class="ref" id="(surv-[^"]+)"', chunk).group(1)
        olds[tid] = {m[0] for m in FIG_RE.findall(chunk)} - {'shelter-desert', 'nav-cross'}
    for tid, t in new_topics().items():
        figs_now = {b['fig'] for s in t['sections'] for b in s['blocks'] if 'fig' in b}
        if tid not in olds:
            assert figs_now == set(), tid
        elif t.get('draft') is True:
            assert figs_now == olds[tid], tid
        else:
            assert figs_now <= olds[tid], tid


def test_draft_topics_keep_placeholder_source_and_all_topics_validate():
    """Topics not yet source-checked keep the placeholder; every topic validates against the real link keys."""
    topics = list(new_topics().values())
    assert len(topics) == 15
    for t in topics:
        assert t['category'] == 'basics'
        if t.get('draft') is True:
            assert t['reviewed'] == '2026-11-17'
            assert t['sources'] == [{'name': 'Not yet source-checked', 'used': 'Converted from v6 text; checked in Tasks 13 to 16'}]
    keys = {'p:' + os.path.splitext(os.path.basename(p))[0] for p in glob.glob(os.path.join(ROOT, 'src', 'protocols', '*.json'))}
    keys |= {'c:' + os.path.splitext(os.path.basename(p))[0] for p in glob.glob(os.path.join(ROOT, 'src', 'checklists', '*.json'))}
    keys |= {'u:daylight', 'u:sos'}   # survival tool keys, as build.py allows them
    errors, _warnings = validate_topics(topics, set(figs.F), keys)
    assert errors == []
