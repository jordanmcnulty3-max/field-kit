"""Task 3: build.py loads, validates and inlines topics and checklists. Plain pytest, no browser.
Each test builds a throwaway copy of the source tree so it can plant bad input."""
import glob
import json
import os
import re
import shutil
import subprocess
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
COPIED = ('src', 'figs', 'tools', 'vendor')


@pytest.fixture
def tree(tmp_path):
    t = tmp_path / 'tree'
    t.mkdir()
    shutil.copy(os.path.join(ROOT, 'build.py'), t)
    for d in COPIED:
        shutil.copytree(os.path.join(ROOT, d), t / d, ignore=shutil.ignore_patterns('__pycache__'))
    return t


def build(tree, *flags):
    out = tree / 'out'
    r = subprocess.run([sys.executable, str(tree / 'build.py'), *flags, str(out)], capture_output=True, text=True)
    return r, out / 'index.html'


def topic_ids():
    return sorted(os.path.basename(p)[:-5] for p in glob.glob(os.path.join(ROOT, 'src', 'survival', '*.json')))


def test_normal_build_inlines_all_topics(tree):
    r, index = build(tree)
    assert r.returncode == 0, r.stderr
    text = index.read_text(encoding='utf-8')
    assert '"topics":[' in text and '"checklists":[{' in text and '"id":"ten-essentials"' in text
    ids = topic_ids()
    assert len(ids) == 45   # the 15 migrated topics, the water pack's 11, heat pack batches A, B and C (4 each), radiation batches A (4) and B (3)
    for tid in ids:
        assert f'"id":"{tid}"' in text
    assert re.search(r'"figSvg":"<svg', text) and '"figLabel":"' in text


def test_release_fails_on_draft_topic(tree):
    p = tree / 'src' / 'survival' / 'surv-fire.json'
    topic = json.loads(p.read_text(encoding='utf-8'))
    topic['draft'] = True  # plant a draft: surv-fire itself is source-checked now
    p.write_text(json.dumps(topic), encoding='utf-8')
    r, _ = build(tree, '--release')
    assert r.returncode != 0
    assert 'surv-fire' in r.stderr and 'draft topic' in r.stderr


def test_invalid_topic_json_names_the_file(tree):
    (tree / 'src' / 'survival' / 'surv-broken.json').write_text('{not json', encoding='utf-8')
    r, _ = build(tree)
    assert r.returncode != 0
    assert 'surv-broken.json' in r.stderr and 'invalid JSON' in r.stderr


def test_script_close_tag_in_topic_text_is_escaped(tree):
    path = tree / 'src' / 'survival' / 'surv-fire.json'
    t = json.loads(path.read_text(encoding='utf-8'))
    t['summary'] = 'marker </script><b>x</b>'
    path.write_text(json.dumps(t), encoding='utf-8')
    r, index = build(tree)
    assert r.returncode == 0, r.stderr
    text = index.read_text(encoding='utf-8')
    assert 'marker <\\/script><b>x<\\/b>' in text and 'marker </script>' not in text


def test_topic_id_equal_to_protocol_id_fails(tree):
    proto = json.loads((tree / 'src' / 'protocols' / 'altitude.json').read_text(encoding='utf-8'))
    path = tree / 'src' / 'survival' / 'surv-fire.json'
    t = json.loads(path.read_text(encoding='utf-8'))
    proto['id'] = t['id']
    (tree / 'src' / 'protocols' / 'clash.json').write_text(json.dumps(proto), encoding='utf-8')
    r, _ = build(tree)
    assert r.returncode != 0
    assert 'surv-fire' in r.stderr and 'equals a protocol id' in r.stderr


def test_checklists_are_inlined_sorted_and_release_checked(tree):
    d = tree / 'src' / 'checklists'
    d.mkdir(exist_ok=True)   # the shipped Ten essentials is already there
    for cid in ('zeta', 'alpha'):
        (d / f'{cid}.json').write_text(json.dumps({
            'id': cid, 'title': cid, 'category': 'basics', 'draft': True, 'reviewed': '2026-11-17',
            'sources': [{'name': 'Test', 'used': 'Test'}],
            'items': [{'id': 'one', 'text': 'Item one'}]}), encoding='utf-8')
    r, index = build(tree)
    assert r.returncode == 0, r.stderr
    text = index.read_text(encoding='utf-8')
    assert text.index('"id":"alpha"') < text.index('"id":"zeta"')
    r, _ = build(tree, '--release')
    assert r.returncode != 0 and 'draft checklist' in r.stderr and 'alpha' in r.stderr


def tooldata_file(tree, tid='water', **over):
    d = tree / 'src' / 'tooldata'
    d.mkdir(exist_ok=True)
    item = {'id': tid, 'title': 'Water', 'values': {'boilMinutes': {'value': 1, 'unit': 'minute'}},
            'sources': [{'name': 'Test', 'used': 'Test'}], 'reviewed': '2026-11-18'}
    item.update(over)
    (d / f'{tid}.json').write_text(json.dumps(item), encoding='utf-8')
    return item


def fk_data(index):
    text = index.read_text(encoding='utf-8')
    m = re.search(r'window\.FK_DATA=(.*?);</script>', text, re.S)
    return json.loads(m.group(1).replace('<\\/', '</'))


def test_tooldata_is_an_empty_object_with_no_files(tree):
    shutil.rmtree(tree / 'src' / 'tooldata', ignore_errors=True)   # the shipped tree now has src/tooldata/water.json
    r, index = build(tree)
    assert r.returncode == 0, r.stderr
    assert fk_data(index)['tooldata'] == {}


def test_tooldata_is_inlined_keyed_by_id(tree):
    shutil.rmtree(tree / 'src' / 'tooldata', ignore_errors=True)   # only this test's two files (the shipped tree also has windchill.json)
    item = tooldata_file(tree)
    tooldata_file(tree, 'aaa')
    r, index = build(tree)
    assert r.returncode == 0, r.stderr
    data = fk_data(index)['tooldata']
    assert list(data) == ['aaa', 'water'] and data['water'] == item


def test_invalid_tooldata_fails_the_build_naming_the_id(tree):
    tooldata_file(tree, values={})
    r, _ = build(tree)
    assert r.returncode != 0 and 'water' in r.stderr and 'values' in r.stderr


def test_release_fails_on_draft_tooldata(tree):
    tooldata_file(tree, draft=True)
    r, index = build(tree)
    assert r.returncode == 0, r.stderr
    r, _ = build(tree, '--release')
    assert r.returncode != 0
    assert 'water' in r.stderr and 'draft tool data' in r.stderr


def test_invalid_tooldata_json_names_the_file(tree):
    d = tree / 'src' / 'tooldata'
    d.mkdir(exist_ok=True)
    (d / 'broken.json').write_text('{nope', encoding='utf-8')
    r, _ = build(tree)
    assert r.returncode != 0 and 'broken.json' in r.stderr and 'invalid JSON' in r.stderr


def link_topic(tree, link):
    path = tree / 'src' / 'survival' / 'surv-fire.json'
    t = json.loads(path.read_text(encoding='utf-8'))
    t['sections'][0]['blocks'].append({'link': link, 'label': 'Tool'})
    path.write_text(json.dumps(t), encoding='utf-8')


def test_topic_may_link_u_water_but_not_an_unknown_tool(tree):
    link_topic(tree, 'u:water')
    r, _ = build(tree)
    assert r.returncode == 0, r.stderr
    link_topic(tree, 'u:nope')
    r, _ = build(tree)
    assert r.returncode != 0 and "unknown link 'u:nope'" in r.stderr


def test_every_tool_name_is_a_link_key(tree):
    for name in ('daylight', 'sos', 'water', 'windchill'):
        link_topic(tree, f'u:{name}')
    r, _ = build(tree)
    assert r.returncode == 0, r.stderr


def test_topic_may_link_u_windchill_and_a_gridded_tool_builds(tree):
    link_topic(tree, 'u:windchill')
    tooldata_file(tree, 'windchill', title='Wind chill', grid={
        'temps': [10, 0], 'winds': [5, 10], 'chill': [[6, -5], [3, -10]], 'bands': [[0, 30], [0, 30]],
        'bandMinutes': [30]})
    r, index = build(tree)
    assert r.returncode == 0, r.stderr
    assert fk_data(index)['tooldata']['windchill']['grid']['bandMinutes'] == [30]


def test_damaged_grid_fails_the_build_naming_the_tool(tree):
    tooldata_file(tree, 'windchill', title='Wind chill', grid={
        'temps': [0, 10], 'winds': [5, 10], 'chill': [[6, -5], [3, -10]], 'bands': [[0, 30], [0, 30]],
        'bandMinutes': [30]})
    r, _ = build(tree)
    assert r.returncode != 0 and 'windchill' in r.stderr and 'temps' in r.stderr


def test_checklist_quantity_is_validated_and_inlined(tree):
    path = tree / 'src' / 'checklists' / 'ten-essentials.json'
    c = json.loads(path.read_text(encoding='utf-8'))
    c['items'][0]['qty'] = {'amount': 1, 'unit': 'gallon', 'per': 'personDay'}
    path.write_text(json.dumps(c), encoding='utf-8')
    r, index = build(tree)
    assert r.returncode == 0, r.stderr
    got = [x for x in fk_data(index)['checklists'] if x['id'] == 'ten-essentials'][0]
    assert got['items'][0]['qty'] == {'amount': 1, 'unit': 'gallon', 'per': 'personDay'}
    c['items'][0]['qty']['per'] = 'week'
    path.write_text(json.dumps(c), encoding='utf-8')
    r, _ = build(tree)
    assert r.returncode != 0 and 'qty' in r.stderr
