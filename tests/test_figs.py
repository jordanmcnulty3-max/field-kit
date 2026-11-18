"""Diagram labels agree with the source-checked Survival topics (Task 16b): old wrong wording is gone, the
checked wording is drawn, and each restored figure sits once in its topic."""
import glob, json, math, os, re, sys
import xml.etree.ElementTree as ET

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'figs'))
import figs  # noqa: E402


def text_of(name):
    """All drawn label text plus the alt text, flattened and lower-cased (apostrophes straightened)."""
    svg, label = figs.F[name]
    root = ET.fromstring(svg)
    drawn = ' '.join(''.join(t.itertext()) for t in root.iter() if t.tag.split('}')[-1] == 'text')
    return re.sub(r'\s+', ' ', f'{drawn} {label}'.replace('’', "'")).lower()


# figure -> (old wrong wording as regexes, new wording that must be drawn)
CASES = {
    'shelter-debris': ([r'\bhip\b', r"arm's length"], ['waist height', '3 ft (1 m)']),
    'fire-sizes': ([r'pencil-thick', r'wrist'], ['pencil lead', 'thumb', 'forearm']),
    'fire-platform': ([r'flat rocks', r'wet ground', r'sticks'], ['green logs', 'deep snow']),
    'river': ([r'slightly downstream'], ['45', 'downstream']),
    'trap-snare': ([r'(?<!\d)3 in\b', r'fist'], ['head']),
    'dress-deer': ([r'head uphill', r'uphill', r'breastbone to pelvis'], ['pelvis to breastbone']),
}


@pytest.mark.parametrize('name', sorted(CASES))
def test_old_wording_gone_and_checked_wording_drawn(name):
    old, new = CASES[name]
    t = text_of(name)
    for pat in old:
        assert not re.search(pat, t), f'{name}: still says {pat!r}: {t}'
    for word in new:
        assert word in t, f'{name}: missing {word!r}: {t}'


def test_tinder_kindling_fuel_use_the_topics_wording():
    t = text_of('fire-sizes')
    for word in ('tinder', 'kindling', 'fuel', 'dry', 'fine'):
        assert word in t


def test_river_path_runs_about_45_degrees_from_straight_across():
    svg, _ = figs.F['river']
    d = re.search(r'<path d="(M[^"]+)" class="k d" marker-end', svg).group(1)
    nums = [float(n) for n in re.findall(r'-?\d+(?:\.\d+)?', d)]
    (x0, y0), (x1, y1) = nums[:2], nums[-2:]
    angle = math.degrees(math.atan2(abs(x1 - x0), abs(y1 - y0)))  # 0 = straight across the river
    assert 40 <= angle <= 50, angle
    assert x1 > x0, 'the current runs left to right, so downstream is to the right'


def test_snare_has_no_dimension_marker():
    svg, _ = figs.F['trap-snare']
    assert '≈' not in svg and 'M228 153' not in svg


def test_every_svg_parses_as_xml():
    for name, (svg, label) in figs.F.items():
        ET.fromstring(svg)
        assert label.strip(), name


def topic_figs():
    out = {}
    for path in sorted(glob.glob(os.path.join(ROOT, 'src', 'survival', 'surv-*.json'))):
        t = json.load(open(path, encoding='utf-8'))
        out[t['id']] = [b['fig'] for s in t['sections'] for b in s['blocks'] if 'fig' in b]
    return out


RESTORED = {
    'surv-shelter': ['shelter-debris'],
    'surv-fire': ['fire-sizes', 'fire-platform'],
    'surv-river-crossings': ['river'],
    'surv-traps-and-fishing': ['trap-snare'],
    'surv-field-dressing-game': ['dress-deer'],
}


@pytest.mark.parametrize('tid', sorted(RESTORED))
def test_restored_figures_appear_exactly_once(tid):
    used = topic_figs()[tid]
    for name in RESTORED[tid]:
        assert used.count(name) == 1, (tid, name, used)


def test_every_figure_a_topic_uses_exists():
    for tid, names in topic_figs().items():
        for n in names:
            assert n in figs.F, (tid, n)
