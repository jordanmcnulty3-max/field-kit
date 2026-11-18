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
    'river': ([r'slightly downstream', r'stay well upstream'], ['45', 'downstream', 'never cross just above them']),
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


# ---- Water pack Task 8: diagrams carry only what their topic carries ----
def topic_json(tid):
    return open(os.path.join(ROOT, 'src', 'survival', f'{tid}.json'), encoding='utf-8').read().replace('’', "'")


WATER_FIGS = {
    'water-safe': 'surv-make-water-safe',
    'water-heater-drain': 'surv-water-in-the-house',
    'toilet-buckets': 'surv-toilet-no-water',
    'latrine': 'surv-latrines',
}


@pytest.mark.parametrize('name', sorted(WATER_FIGS))
def test_water_figure_exists_and_sits_once_in_its_topic(name):
    assert name in figs.F
    assert topic_figs()[WATER_FIGS[name]].count(name) == 1


def test_water_safe_carries_the_checked_figures_only():
    t = text_of('water-safe')
    topic = topic_json('surv-make-water-safe').lower()
    for word in ('1 minute', '3 min', '5,000 ft', '8 drops', '5% to 9%', 'per gallon', '30 minutes'):
        assert word in t, f'missing {word!r}: {t}'
    for fact in ('1 minute', '5,000 ft', '8 drops per gallon', '5% to 9%', '30 minutes'):
        assert fact in topic, fact
    for old in ('6,500', '6 percent', '6%'):
        assert old not in t, f'still says {old!r}: {t}'
    svg, label = figs.F['water-safe']
    assert '6,500' not in svg and '6 percent' not in svg and '6%' not in svg


HEATER_LABELS = ['Power or gas OFF', 'Let it cool', 'Close the water intake valve', 'Open a hot tap',
                 'Container here', 'Open the drain']
HEATER_FOOTER = 'Refill the tank before turning power or gas back on'


def test_water_heater_drain_labels_numbered_in_order():
    t = text_of('water-heater-drain')
    pos = -1
    for i, label in enumerate(HEATER_LABELS, 1):
        want = f'{i} {label}'.lower()
        at = t.find(want, pos + 1)
        assert at > pos, f'{want!r} not found in order in: {t}'
        pos = at
    assert HEATER_FOOTER.lower() in t[pos:]


def test_toilet_buckets_uses_the_topics_words():
    t = text_of('toilet-buckets')
    topic = topic_json('surv-toilet-no-water').lower()
    for word in ('pee', 'poo', 'lid', 'seat', 'cover material', 'half a cup (120 ml)', 'after each poo'):
        assert word in t, f'missing {word!r}: {t}'
        assert word in topic or word == 'lid', word
    assert 'bleach' not in t and 'sawdust' not in t


def test_latrine_numbers_all_come_from_the_topic():
    t = text_of('latrine')
    topic = topic_json('surv-latrines').lower()
    for phrase in ('6 to 8 inches (15 to 20 cm)', '200 feet (60 m)'):
        assert phrase in t, f'missing {phrase!r}: {t}'
        assert phrase in topic
    # every number-with-unit drawn must appear in the topic text exactly as drawn
    for m in re.finditer(r'\d[\d,.]*(?: to \d[\d,.]*)? (?:inches|feet|ft|in|cm|m)\b(?: \([^)]*\))?', t):
        assert m.group(0) in topic, f'{m.group(0)!r} drawn but not in the topic'
    assert '911' not in t
