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
    # land pack (v7.7) Task 6: surv-field-dressing-game ships with no deer field-dressing figure (dress-deer was not
    # recognisable and the redraw failed the image-first review; docs/v7.7-rulings.md, Diagrams)
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
def drawn_of(name):
    """Only the <text> content actually drawn on the figure (no alt label), lower-cased, apostrophes straightened."""
    svg, _ = figs.F[name]
    root = ET.fromstring(svg)
    drawn = ' '.join(''.join(t.itertext()) for t in root.iter() if t.tag.split('}')[-1] == 'text')
    return re.sub(r'\s+', ' ', drawn.replace('’', "'")).lower()


def alt_of(name):
    return re.sub(r'\s+', ' ', figs.F[name][1].replace('’', "'")).lower()


def topic_json(tid):
    return open(os.path.join(ROOT, 'src', 'survival', f'{tid}.json'), encoding='utf-8').read().replace('’', "'")


def topic_caption(tid, name):
    t = json.load(open(os.path.join(ROOT, 'src', 'survival', f'{tid}.json'), encoding='utf-8'))
    return [b['cap'] for s in t['sections'] for b in s['blocks'] if b.get('fig') == name][0].replace('’', "'").lower()


WATER_FIGS = {
    'water-safe': 'surv-make-water-safe',
    'water-heater-drain': 'surv-water-in-the-house',
    'toilet-buckets': 'surv-toilet-no-water',
    'latrine': 'surv-latrines',
    'handwash-station': 'surv-handwashing',
}


@pytest.mark.parametrize('name', sorted(WATER_FIGS))
def test_water_figure_exists_and_sits_once_in_its_topic(name):
    assert name in figs.F
    assert topic_figs()[WATER_FIGS[name]].count(name) == 1


def test_drawn_text_helper_excludes_the_alt_label():
    assert 'water heater tank drained' in alt_of('water-heater-drain')
    assert 'water heater tank drained' not in drawn_of('water-heater-drain')


def test_water_safe_carries_the_checked_figures_only():
    d = drawn_of('water-safe')
    topic = topic_json('surv-make-water-safe').lower()
    for word in ('rolling boil', 'at least 1 minute', '3 min above 5,000 ft', '8 drops of 5% to 9%', 'unscented bleach',
                 'per gallon', 'stir, wait 30 minutes'):
        assert word in d, f'missing {word!r} in drawn text: {d}'
    for fact in ('rolling boil for at least 1 minute', 'above 5,000 ft', '8 drops per gallon', '5% to 9%',
                 'unscented', 'stir and let it stand 30 minutes'):
        assert fact in topic, fact
    for old in ('6,500', '6 percent', '6%'):
        assert old not in d, f'still says {old!r}: {d}'
    svg, _ = figs.F['water-safe']
    alt = alt_of('water-safe')
    assert '6,500' not in svg and '6 percent' not in svg and '6%' not in svg
    for word in ('at least 1 minute', '5,000 feet', '8 drops', '5% to 9%', 'unscented', 'per gallon', '30 minutes'):
        assert word in alt, f'alt label missing {word!r}'
    cap = topic_caption('surv-make-water-safe', 'water-safe')
    for word in ('at least 1 minute', '5,000 ft', '8 drops per gallon', 'unscented 5% to 9%',
                 'double it if the water is cloudy, colored or very cold', '30 minutes'):
        assert word in cap, f'caption missing {word!r}'


HEATER_LABELS = ['Power or gas OFF', 'Let it cool', 'Close the water intake valve', 'Open a hot tap',
                 'Container here', 'Open the drain']
HEATER_FOOTER = 'Refill the tank before turning power or gas back on'


def test_water_heater_drain_labels_numbered_in_order():
    t = drawn_of('water-heater-drain')
    pos = -1
    for i, label in enumerate(HEATER_LABELS, 1):
        want = f'{i} {label}'.lower()
        at = t.find(want, pos + 1)
        assert at > pos, f'{want!r} not found in order in drawn text: {t}'
        pos = at
    assert HEATER_FOOTER.lower() in t[pos:], t
    alt = alt_of('water-heater-drain')
    for i, label in enumerate(HEATER_LABELS, 1):
        assert f'{i} {label}'.lower() in alt
    assert HEATER_FOOTER.lower() in alt


def test_toilet_buckets_uses_the_topics_words():
    d = drawn_of('toilet-buckets')
    topic = topic_json('surv-toilet-no-water').lower()
    for word in ('pee', 'poo', 'lid', 'seat', 'cover material', 'half a cup (120 ml)', 'after each poo'):
        assert word in d, f'missing {word!r} in drawn text: {d}'
        assert word in topic, word
    assert 'bleach' not in d and 'sawdust' not in d
    alt = alt_of('toilet-buckets')
    for word in ('pee', 'poo', 'seat', 'cover material', 'half a cup (120 ml)', 'after each poo'):
        assert word in alt


def test_latrine_numbers_all_come_from_the_topic():
    d = drawn_of('latrine')
    topic = topic_json('surv-latrines').lower()
    for phrase in ('at least 200 feet (60 m) from water', 'about 70 steps', '6 to 8 inches (15 to 20 cm) deep',
                   '4 to 6 inches (10 to 15 cm) across', 'soil you dug out'):
        assert phrase in d, f'missing {phrase!r} in drawn text: {d}'
    for phrase in ('200 feet (60 m)', 'about 70 steps', '6 to 8 inches (15 to 20 cm) deep',
                   '4 to 6 inches (10 to 15 cm) across', 'soil you dug out'):
        assert phrase in topic, phrase
    # every number-with-unit drawn must appear in the topic text exactly as drawn
    for m in re.finditer(r'\d[\d,.]*(?: to \d[\d,.]*)? (?:inches|feet|ft|in|cm|m)\b(?: \([^)]*\))?', d):
        assert m.group(0) in topic, f'{m.group(0)!r} drawn but not in the topic'
    assert '911' not in d and '150' not in d


def test_handwash_station_uses_the_topics_words():
    d = drawn_of('handwash-station')
    topic = topic_json('surv-handwashing').lower()
    for phrase in ('jug with an on/off spigot', 'soap in a sock', 'towel', 'catch bucket'):
        assert phrase in d, f'missing {phrase!r} in drawn text: {d}'
    for word in ('on/off spigot', 'soap', 'towel', 'catch bucket', 'sock'):
        assert word in d, f'missing {word!r} in drawn text: {d}'
        assert word in topic, word
    assert 'bleach' not in d and '911' not in d
    assert not re.search(r'\d', d), f'no numbers expected: {d}'


def parts(name):
    root = ET.fromstring(figs.F[name][0])
    return {e.get('data-part'): e for e in root.iter() if e.get('data-part')}


def xs_of(el):
    if el.tag.endswith('line'):
        return [float(el.get('x1')), float(el.get('x2'))]
    return [float(n) for n in re.findall(r'[MLHl] ?(-?\d+(?:\.\d+)?)', el.get('d'))]


def test_handwash_stream_falls_past_the_table_edge_into_the_bucket():
    p = parts('handwash-station')
    assert {'table', 'stream', 'bucket'} <= set(p)
    t0, t1 = min(xs_of(p['table'])), max(xs_of(p['table']))
    sx = xs_of(p['stream'])[0]
    b0, b1 = min(xs_of(p['bucket'])), max(xs_of(p['bucket']))
    assert sx < t0 - 6, f'stream x {sx} is over the tabletop {t0}-{t1}'
    assert b0 < sx < b1, 'bucket must span the stream'
    assert b1 < t0, 'bucket sits beside the table, not under it'
    legs = [xs_of(e)[0] for e in ET.fromstring(figs.F['handwash-station'][0]).iter() if e.get('data-part') == 'leg']
    assert all(abs(sx - l) > 10 for l in legs), 'stream clear of the legs'


def path_end(d):
    """Last point of a path drawn with absolute M, L, H and V commands."""
    x = y = None
    for cmd, args in re.findall(r'([MLHV])\s*([-\d.\s,]+)', d):
        n = [float(v) for v in re.findall(r'-?\d+(?:\.\d+)?', args)]
        if cmd in 'ML':
            x, y = n[-2], n[-1]
        elif cmd == 'H':
            x = n[-1]
        else:
            y = n[-1]
    return x, y


def test_handwash_stream_starts_at_the_spigot_outlet():
    """Final review, Minor 14: the stream is tied to the spigot pipe, so moving the pipe back over the table fails."""
    root = ET.fromstring(figs.F['handwash-station'][0])
    stream = parts('handwash-station')['stream']
    sx, sy = float(stream.get('x1')), min(float(stream.get('y1')), float(stream.get('y2')))
    jug = max((e for e in root.iter() if e.tag.endswith('rect')), key=lambda e: float(e.get('width')) * float(e.get('height')))
    j0, j1 = float(jug.get('x')), float(jug.get('x')) + float(jug.get('width'))
    pipes = []
    for e in root.iter():
        if e.tag.endswith('path') and re.fullmatch(r'M[\d.]+ [\d.]+(?: [HV][\d.]+)+', e.get('d')):
            x0 = float(re.match(r'M([\d.]+)', e.get('d')).group(1))
            ex, ey = path_end(e.get('d'))
            if j0 <= x0 <= j1 and ex == sx and 0 <= sy - ey <= 8:
                pipes.append(e.get('d'))
    assert pipes, 'no pipe runs from the jug to the top of the stream'


def test_handwash_station_alt_and_caption_carry_the_topic_words():
    alt = alt_of('handwash-station')
    for word in ('jug', 'on/off spigot', 'soap', 'sock', 'towel', 'catch bucket'):
        assert word in alt, word
    cap = topic_caption('surv-handwashing', 'handwash-station')
    topic = topic_json('surv-handwashing').lower()
    for word in ('on/off spigot', 'soap', 'towels', 'catch bucket', 'sock', "jug's handle"):
        assert word in cap, word
        assert word in topic, word


# ---- Heat pack Task 8: diagrams carry only what their topic carries ----
def topic_text(tid):
    """The topic's own words, lower-cased, apostrophes straightened: summary, doFirst, headings and every block's text, but
    not the figure captions (written with the figures), keywords or source notes, so a drawn phrase cannot pass on the
    strength of its own caption (review M7)."""
    t = json.load(open(os.path.join(ROOT, 'src', 'survival', f'{tid}.json'), encoding='utf-8'))

    def strings(v):
        if isinstance(v, str):
            yield v
        elif isinstance(v, list):
            for x in v:
                yield from strings(x)
        elif isinstance(v, dict):
            for k, x in v.items():
                if k not in ('fig', 'cap'):
                    yield from strings(x)
    parts = [t.get('summary', '')] + list(strings(t.get('doFirst', [])))
    for sec in t['sections']:
        parts.append(sec['h'])
        parts += list(strings(sec['blocks']))
    return re.sub(r'\s+', ' ', ' '.join(parts).replace('’', "'")).lower()


def fig_section(tid, name):
    t = json.load(open(os.path.join(ROOT, 'src', 'survival', f'{tid}.json'), encoding='utf-8'))
    return [s['h'] for s in t['sections'] for b in s['blocks'] if b.get('fig') == name]


# figure -> (topic, section heading it sits in, phrases drawn on it (each also in the topic), old or unsupported wording
#            that must not be drawn or in the alt text, phrases the caption carries)
HEAT_FIGS = {
    'shelter-tarp': ('surv-shelter', 'Tarp lean-to, step by step',
                     ['high front edge', 'drip stick', 'tree about waist high', 'staked edge',
                      'back into the wind', 'open side', 'faces away from'],
                     [r'a-frame', r'ridgeline', r'low end', r'\d'],
                     ['high front edge', 'staked', 'into the wind']),
    'fire-ferro': ('surv-fire', 'Ways to light it',
                   ['tip at the tinder', 'at a right angle', 'drive it down the rod', 'firm, even pressure',
                    'sparks land in the tinder'],
                   [r'pull', r'\bback\b', r'held still', r'\d'],
                   ['tip at the tinder', 'right angle', 'down the rod']),
    'generator-placement': ('surv-generators', 'Where to run it',
                            ['outside only', 'more than 20 feet (6 m)', 'window, door or vent', 'exhaust',
                             'away from your home', 'never inside a home, garage, basement, crawlspace or shed'],
                            [r'\b15\b', r'\b25\b', r'\b10\b', r'carport is (ok|fine)'],
                            ['more than 20 feet (6 m)', 'exhaust', 'away from your home', 'attached garage']),
    'heater-clearance': ('surv-wood-stoves-fireplaces', 'Before you light it',
                         ['at least 3 feet (1 m)', 'anything that can burn', 'vented to the outside'],
                         [r'36', r'\b2 feet\b', r'\b4 feet\b', r'\bwall\b'],
                         ['anything that can burn', 'at least 3 feet (1 m)', 'vented to the outside']),
    'warm-room': ('surv-heat-out', 'One warm room',
                  ['warm room', 'close off', 'towels', 'cracks under doors', 'blankets', 'at night', 'sheltered side',
                   'heating ducts'],
                  [r'\d', r'kerosene', r'propane', r'heater'],
                  ['smallest space', 'sheltered side', 'close']),
    'quinzhee': ('surv-shelter', 'Quinzhee (snow mound)',
                 ['at least 5 feet (1.5 m) high', 'a foot (30 cm) deep', 'at least 1 foot (30 cm) thick',
                  'ventilation hole', 'raised beds', 'trench', 'down to the ground', 'cold air drains out'],
                 [r'\b2 feet\b', r'\b3 feet\b', r'\b10 feet\b', r'7 to 8', r'90 minutes', r'stove', r'candle', r'entrance'],
                 ['vent', 'raised beds', 'cold air']),
}
NUM_PHRASE = re.compile(r'(?:a|\d[\d,.]*(?: to \d[\d,.]*)?) (?:inches|inch|feet|foot|ft|in|cm|m)\b(?: \([^)]*\))?')


@pytest.mark.parametrize('name', sorted(HEAT_FIGS))
def test_heat_figure_sits_once_in_its_section(name):
    tid, section = HEAT_FIGS[name][:2]
    assert name in figs.F, name
    assert topic_figs()[tid].count(name) == 1, (tid, name)
    assert fig_section(tid, name) == [section]


@pytest.mark.parametrize('name', sorted(HEAT_FIGS))
def test_heat_figure_draws_its_topics_words(name):
    tid, _, words, _, _ = HEAT_FIGS[name]
    d, topic = drawn_of(name), topic_text(tid)
    for w in words:
        assert w in d, f'{name}: missing {w!r} in drawn text: {d}'
        assert w in topic, f'{name}: {w!r} is not in {tid}'


@pytest.mark.parametrize('name', sorted(HEAT_FIGS))
def test_heat_figure_draws_no_old_or_unstated_wording(name):
    _, _, _, banned, _ = HEAT_FIGS[name]
    for t in (drawn_of(name), alt_of(name)):
        for pat in banned:
            assert not re.search(pat, t), f'{name}: says {pat!r}: {t}'


@pytest.mark.parametrize('name', sorted(HEAT_FIGS))
def test_heat_figure_numbers_all_come_from_the_topic(name):
    """Every number drawn or in the alt text is part of a distance the topic states with the same value and unit."""
    tid = HEAT_FIGS[name][0]
    topic = topic_text(tid)
    for t in (drawn_of(name), alt_of(name)):
        phrases = NUM_PHRASE.findall(t)
        for p in phrases:   # 'a foot (30 cm)' too (review M8)
            assert p in topic, f'{name}: {p!r} drawn but not in {tid}'
        rest = NUM_PHRASE.sub('', t)
        assert not re.search(r'\d', rest), f'{name}: a number outside a stated distance: {rest}'


@pytest.mark.parametrize('name', sorted(HEAT_FIGS))
def test_heat_figure_alt_and_caption(name):
    tid, _, words, _, cap_words = HEAT_FIGS[name]
    alt = alt_of(name)
    assert len(alt) > 40, alt
    cap = topic_caption(tid, name)
    for w in cap_words:
        assert w in cap, f'{name}: caption missing {w!r}: {cap}'


def test_shelter_has_two_different_lean_tos():
    """The tarp lean-to and the pole-and-bough lean-to are different drawings with their own words."""
    tarp, bough = drawn_of('shelter-tarp'), drawn_of('shelter-leanto')
    assert 'tarp' in alt_of('shelter-tarp') and 'tarp' not in alt_of('shelter-leanto')
    assert 'fire' not in tarp and 'drip stick' not in bough
    assert figs.F['shelter-tarp'][0] != figs.F['shelter-leanto'][0]


def test_tarp_back_edge_is_upwind_and_low():
    """Wind arrows point at the staked back edge, which is lower and further upwind than the high front edge."""
    p = parts('shelter-tarp')
    assert {'high-edge', 'low-edge', 'wind'} <= set(p)
    hi, lo, wind = p['high-edge'], p['low-edge'], p['wind']
    hy = [float(hi.get('y1')), float(hi.get('y2'))]
    ly = [float(lo.get('y1')), float(lo.get('y2'))]
    hx = [float(hi.get('x1')), float(hi.get('x2'))]
    lx = [float(lo.get('x1')), float(lo.get('x2'))]
    assert min(ly) > min(hy) and max(ly) > max(hy), 'the staked edge is lower on the page'
    wx1, wx2 = float(wind.get('x1')), float(wind.get('x2'))
    assert wx2 > wx1, 'wind blows left to right'
    assert max(wx1, wx2) < min(hx) and min(lx) < min(hx), 'the low edge is on the windward (left) side'


def test_ferro_striker_is_square_to_the_rod_and_pushed_toward_the_tip():
    p = parts('fire-ferro')
    assert {'rod', 'striker', 'push', 'tinder'} <= set(p)
    def vec(e):
        return float(e.get('x2')) - float(e.get('x1')), float(e.get('y2')) - float(e.get('y1'))
    (rx, ry), (sx, sy), (px, py) = vec(p['rod']), vec(p['striker']), vec(p['push'])
    cos = abs(rx * sx + ry * sy) / math.hypot(rx, ry) / math.hypot(sx, sy)
    assert cos < 0.05, f'striker not at a right angle to the rod: cos={cos:.3f}'
    assert (rx * px + ry * py) / math.hypot(rx, ry) / math.hypot(px, py) > 0.99, 'push runs down the rod toward its tip'
    tip = float(p['rod'].get('x2')), float(p['rod'].get('y2'))
    tin = p['tinder']
    cx, cy, ex, ey = (float(tin.get(k)) for k in ('cx', 'cy', 'rx', 'ry'))
    assert ((tip[0] - cx) / ex) ** 2 + ((tip[1] - cy) / ey) ** 2 <= 1.2, 'rod tip is at the tinder'


def bbox(el):
    """Bounding box of a line, rect, or path drawn with absolute M/L/H/V commands."""
    tag = el.tag.split('}')[-1]
    if tag == 'line':
        xs, ys = [float(el.get('x1')), float(el.get('x2'))], [float(el.get('y1')), float(el.get('y2'))]
    elif tag == 'rect':
        x, y = float(el.get('x')), float(el.get('y'))
        xs, ys = [x, x + float(el.get('width'))], [y, y + float(el.get('height'))]
    else:
        xs, ys, x, y = [], [], 0.0, 0.0
        for cmd, args in re.findall(r'([MLHVA])\s*([-\d.\s,]*)', el.get('d')):
            n = [float(v) for v in re.findall(r'-?\d+(?:\.\d+)?', args)]
            if cmd in 'ML':
                for i in range(0, len(n), 2):
                    x, y = n[i], n[i + 1]
                    xs.append(x); ys.append(y)
            elif cmd == 'H':
                x = n[-1]; xs.append(x); ys.append(y)
            elif cmd == 'V':
                y = n[-1]; xs.append(x); ys.append(y)
            elif cmd == 'A':
                x, y = n[5], n[6]; xs.append(x); ys.append(y)
    return min(xs), min(ys), max(xs), max(ys)


def test_quinzhee_draws_no_entrance_above_the_beds():
    """Review C1: the topic's rule is a sleeping platform higher than the top of the entrance, and the quinzhee steps give
    no entrance height, so the cut-away draws no entrance; any dashed line sits above the dome (the height mark) only."""
    svg, _ = figs.F['quinzhee']
    root = ET.fromstring(svg)
    assert 'entrance' not in drawn_of('quinzhee') and 'entrance' not in alt_of('quinzhee')
    bed_top = bbox(parts('quinzhee')['beds'])[1]
    for el in root.iter():
        if 'd' in (el.get('class') or '').split():
            assert bbox(el)[3] < bed_top - 60, f'dashed element reaches down to the beds: {ET.tostring(el)[:80]}'


def test_quinzhee_walls_are_at_least_a_foot_at_the_drawn_scale():
    """Review M5: the height mark is 5 feet, so the wall (outer minus inner radius) must be at least a fifth of it."""
    d = parts('quinzhee')['walls'].get('d')
    (orx, ory), (irx, iry) = [tuple(float(v) for v in m) for m in re.findall(r'A(\d+(?:\.\d+)?) (\d+(?:\.\d+)?)', d)]
    foot = ory / 5
    assert ory - iry >= foot and orx - irx >= foot, (orx, ory, irx, iry)
    beds = bbox(parts('quinzhee')['beds'])
    assert abs((196 - beds[1]) - foot) <= 2, 'beds are the last foot of snow'


def test_generator_geometry():
    """Review M9: the garage generator is crossed out, the distance runs from the house wall to the generator, and the
    exhaust arrow starts past the generator and points away from the house."""
    p = parts('generator-placement')
    assert {'garage', 'house', 'never', 'distance', 'exhaust', 'generator'} <= set(p)
    house, never, dist, ex = bbox(p['house']), bbox(p['never']), bbox(p['distance']), p['exhaust']
    gx0, _, gx1, _ = bbox(p['garage'])
    assert gx0 <= never[0] and never[2] <= gx1 + 2 and gx1 <= house[0], 'X over the garage beside the house'
    gen = [float(r.get('x')) for r in p['generator'].iter() if r.tag.split('}')[-1] == 'rect']
    assert dist[0] == house[2], 'distance starts at the house wall'
    assert abs(dist[2] - min(gen)) <= 1, 'distance ends at the generator'
    x1, x2 = float(ex.get('x1')), float(ex.get('x2'))
    assert x1 >= max(gen) and x2 > x1, 'exhaust points away from the house'
    assert ex.get('marker-end')


def test_warm_room_towel_is_its_own_shape_beside_the_door():
    """Review M4: the towel is not a straight bar that merges with the door leaf at night."""
    towel = parts('warm-room')['towel']
    assert towel.tag.split('}')[-1] == 'path' and towel.get('d').count('l') >= 4


# ---- Radiation pack Task 7: diagrams carry only what their topic carries ----
def protocol_json(pid):
    return json.load(open(os.path.join(ROOT, 'src', 'protocols', f'{pid}.json'), encoding='utf-8'))


def protocol_text(pid):
    p = protocol_json(pid)
    parts = [p['summary']] + [s[k] for s in p['steps'] for k in ('text', 'detail', 'warn') if k in s] + p['donts']
    return re.sub(r'\s+', ' ', ' '.join(parts).replace('’', "'")).lower()


# figure -> (topic, section heading it sits in, phrases drawn on it (each also in the topic's own text), wording that must
#            not be drawn or in the alt text, phrases the caption carries, protocol whose text drawn lines may also come from)
RAD_FIGS = {
    'fallout-shelter-spots': (
        'surv-fallout-where-to-shelter', 'Best to worst',
        ['best spot in a house', 'basement: go there first', 'apartments and large buildings', 'basement is best',
         'otherwise go to the center of the building, as far from the roof and windows as you can',
         'stay away from areas near the roof, fire escapes and balconies'],
        [r'\bsafe', r'\d', r'radiation', r'fallout', r'worst', r'floor', r'airtight', r'corner', r'shield', r'protect',
         r'no basement', r'middle of the house'],
        ['basement: go there first', 'going to the basement is best', 'otherwise go to the center of the building'],
        None),
    'fallout-coming-inside': (
        'surv-fallout-coming-inside', 'The steps',
        ['save a life first', 'take off the outer layer of clothes and shoes', 'away from others', 'bag them',
         'far from people and pets', 'wash gently with soap and water, or wipe off', 'no conditioner, no scrubbing',
         'blow the nose and wipe the eyes and ears', 'put on clean clothes from a closet, drawer or other covered place',
         'care for wounds', 'then help others and pets, and clean yourself again afterwards'],
        [r'\bsafe', r'90', r'\bhot\b', r'bleach', r'sanitizer', r'scrub(?!bing)', r'shake', r'vacuum', r'hose'],
        ['save a life first. ', 'the cleaning-off steps are in the emergency protocol radiation decontamination, one at a time.'],
        'radiation-decontamination'),
}


@pytest.mark.parametrize('name', sorted(RAD_FIGS))
def test_radiation_figure_sits_once_in_its_section(name):
    tid, section = RAD_FIGS[name][:2]
    assert name in figs.F, name
    assert topic_figs()[tid].count(name) == 1, (tid, name)
    assert fig_section(tid, name) == [section]


@pytest.mark.parametrize('name', sorted(RAD_FIGS))
def test_radiation_figure_draws_its_topics_words(name):
    tid, _, words, _, _, _ = RAD_FIGS[name]
    d, topic = drawn_of(name), topic_text(tid)
    for w in words:
        assert w in d, f'{name}: missing {w!r} in drawn text: {d}'
        assert w in topic, f'{name}: {w!r} is not in {tid}'


def _texts(name):
    root = ET.fromstring(figs.F[name][0])
    return [(float(t.get('x')), float(t.get('y')), re.sub(r'\s+', ' ', ''.join(t.itertext()).replace('’', "'")).lower())
            for t in root.iter() if t.tag.split('}')[-1] == 'text']


@pytest.mark.parametrize('name', sorted(RAD_FIGS))
def test_radiation_figure_every_drawn_line_is_in_the_text(name):
    """Every text string drawn (not only chosen phrases) is word for word in the topic's own text or its protocol's,
    apart from step badges; trailing punctuation that only ends a line is ignored."""
    tid, protocol = RAD_FIGS[name][0], RAD_FIGS[name][5]
    source = topic_text(tid) + ' | ' + (protocol_text(protocol) if protocol else '')
    for _, _, s in _texts(name):
        if re.fullmatch(r'\d', s):
            continue
        line = s.strip().rstrip(':,.').strip()
        assert line and line in source, f'{name}: drawn {s!r} is not in {tid}' + (f' or {protocol}' if protocol else '')


@pytest.mark.parametrize('name', sorted(RAD_FIGS))
def test_radiation_figure_draws_no_unstated_wording(name):
    banned = RAD_FIGS[name][3]
    for t in (drawn_of(name), alt_of(name)):
        for pat in banned:
            assert not re.search(pat, t), f'{name}: says {pat!r}: {t}'


@pytest.mark.parametrize('name', sorted(RAD_FIGS))
def test_radiation_figure_alt_and_caption(name):
    tid, _, _, _, cap_words, _ = RAD_FIGS[name]
    alt = alt_of(name)
    assert len(alt) > 40, alt
    cap = topic_caption(tid, name)
    for w in cap_words:
        assert w in cap, f'{name}: caption missing {w!r}: {cap}'
    assert not re.search(r'\bsafe', cap)
    for sentence in [x.strip() for x in re.split(r'(?<=\.)\s', cap) if x.strip()]:
        body = re.sub(r'^apartments and large buildings: ', '', sentence).rstrip('.')
        assert body in topic_text(tid), f'{name}: caption sentence not in the topic: {sentence!r}'


def test_shelter_spots_has_no_arrows_and_no_numbers():
    """No arrow (nothing that could read as the direction radiation comes from) and no number, distance or ranking."""
    svg, _ = figs.F['fallout-shelter-spots']
    assert 'marker-end' not in svg and 'marker-start' not in svg
    assert not re.search(r'\d', drawn_of('fallout-shelter-spots'))


def _shaded(name):
    root = ET.fromstring(figs.F[name][0])
    return [e for e in root.iter() if set((e.get('class') or '').split()) & {'af', 'hfl', 'gf', 'wf'}]


def test_shelter_spots_basement_label_first_and_no_floor_marked():
    """Review: the basement label is read first (first place label in the SVG and highest in its panel), and nothing marks
    an above-ground floor of the stacked building: no shading and no text inside it."""
    texts = _texts('fallout-shelter-spots')
    order = [s for _, _, s in texts]
    i = next(k for k, s in enumerate(order) if 'basement is best' in s)
    for later in ('otherwise', 'stay away from areas'):
        j = next(k for k, s in enumerate(order) if later in s)
        assert i < j, (later, order)
    by = {s: y for _, y, s in texts}
    assert by['basement is best'] < min(y for s, y in by.items() if 'otherwise' in s or 'stay away from areas' in s)
    p = parts('fallout-shelter-spots')
    bx0, by0, bx1, by1 = bbox(p['bldg'])
    for e in _shaded('fallout-shelter-spots'):
        x0, y0, x1, y1 = bbox(e)
        assert x1 <= bx0 or x0 >= bx1 or y1 <= by0 or y0 >= by1, f'shading inside the building above ground: {e.attrib}'
    for x, y, s in texts:
        assert not (bx0 < x < bx1 and by0 < y < by1), f'text inside the building above ground: {s!r}'


def test_shelter_spots_geometry():
    """House: the whole basement is marked, under the house, below the ground. Building: the basement is marked below the
    ground, more strongly than the centre of the floor plan. Floor plan: one floor, windows on every side, the centre
    marked in the middle and clear of the outside walls."""
    p = parts('fallout-shelter-spots')
    need = {'house-a', 'ground-a', 'basement-a', 'bldg', 'ground-c', 'basement-c', 'plan', 'plan-center'}
    assert need <= set(p), need - set(p)
    ga, gc = bbox(p['ground-a'])[1], bbox(p['ground-c'])[1]
    ha, ba = bbox(p['house-a']), bbox(p['basement-a'])
    assert ba[1] >= ga and abs(ba[0] - ha[0]) <= 1 and abs(ba[2] - ha[2]) <= 1, 'whole house basement, below ground'
    bc = bbox(p['basement-c'])
    assert bc[1] >= gc, 'building basement below ground'
    op = lambda e: float(re.search(r'fill-opacity:([\d.]+)', e.get('style')).group(1))
    assert op(p['basement-c']) > op(p['plan-center']) and op(p['basement-a']) > op(p['plan-center'])
    pl, pc = bbox(p['plan']), bbox(p['plan-center'])
    assert pl[1] > bbox(p['basement-c'])[3], 'the plan is drawn apart from the building section'
    assert abs((pc[0] + pc[2]) / 2 - (pl[0] + pl[2]) / 2) <= 1 and abs((pc[1] + pc[3]) / 2 - (pl[1] + pl[3]) / 2) <= 1
    assert min(pc[0] - pl[0], pl[2] - pc[2], pc[1] - pl[1], pl[3] - pc[3]) >= 12, 'centre clear of the outside walls'
    wins = [e for e in p['plan-windows'].iter() if e.tag.split('}')[-1] == 'rect']
    sides = set()
    for w in wins:
        x, y = float(w.get('x')), float(w.get('y'))
        sides.add('t' if abs(y + 3 - pl[1]) < 1 else 'b' if abs(y + 3 - pl[3]) < 1 else 'l' if abs(x + 3 - pl[0]) < 1 else
                  'r' if abs(x + 3 - pl[2]) < 1 else '?')
    assert sides == {'t', 'b', 'l', 'r'}, sides


def test_coming_inside_numbers_are_the_badges_only():
    nums = [s for _, _, s in _texts('fallout-coming-inside') if re.search(r'\d', s)]
    assert sorted(nums) == ['1', '2', '3', '4', '5', '6'], nums


# panel's first label -> protocol step it draws, and a phrase of that step's text
COMING_STEPS = [('take off the outer layer', 's2', 'Take off the outer layer'), ('bag them', 's3', 'plastic bag'),
                ('wash gently', 's4', 'Wash gently'), ('blow the nose', 's5', 'blow the nose'),
                ('put on clean clothes', 's6', 'Put on clean clothes'), ('care for wounds', 's7', 'Wounds:')]


def test_coming_inside_panels_follow_the_protocol_with_none_skipped():
    """Badges read left to right, top to bottom; each badge's panel carries its step; the panels are the protocol's steps
    s2 to s7 in the protocol's order with none skipped (the nose, eyes and ears step included); "Save a life first" is
    above them and "Then help others ... clean yourself again" below."""
    texts = _texts('fallout-coming-inside')
    badges = {s: (x, y) for x, y, s in texts if re.fullmatch(r'\d', s)}
    order = sorted(badges, key=lambda s: (badges[s][1], badges[s][0]))
    assert order == ['1', '2', '3', '4', '5', '6'], badges
    rows = sorted({y for _, y in badges.values()})

    def cell(x, y):
        row = max((r for r in rows if r - 10 <= y), default=None)
        if row is None:
            return None
        cands = [b for b, (bx, by) in badges.items() if by == row and bx - 15 <= x]
        return max(cands, key=lambda b: badges[b][0]) if cands else None
    steps = protocol_json('radiation-decontamination')['steps']
    ids = [s['id'] for s in steps]
    for n, (phrase, sid, key) in enumerate(COMING_STEPS, 1):
        hits = [(x, y) for x, y, s in texts if s.startswith(phrase)]
        assert hits, phrase
        assert cell(*hits[0]) == str(n), (phrase, cell(*hits[0]))
        assert key in next(s['text'] for s in steps if s['id'] == sid), (sid, key)
    drawn = [sid for _, sid, _ in COMING_STEPS]
    assert ids[ids.index(drawn[0]):ids.index(drawn[-1]) + 1] == drawn, 'a protocol step between the first and last is skipped'
    top, bottom = min(rows), max(rows)
    assert next(y for _, y, s in texts if 'save a life first' in s) < top
    assert next(y for _, y, s in texts if s.startswith('then help others')) > bottom + 60
    assert ids.index('s8') == ids.index('s7') + 1, 'helping others comes straight after wounds'


def test_coming_inside_bag_is_drawn_far_from_the_person_and_pet():
    """Review: "far" is visible, not only labelled: the gap between the bag and the person is at least twice the bag's width."""
    p = parts('fallout-coming-inside')
    def box(el):
        out = []
        for e in el.iter():
            tag = e.tag.split('}')[-1]
            if tag in ('circle', 'ellipse'):
                cx, cy = float(e.get('cx')), float(e.get('cy'))
                rx, ry = float(e.get('r') or e.get('rx')), float(e.get('r') or e.get('ry'))
                out.append((cx - rx, cy - ry, cx + rx, cy + ry))
            elif tag in ('line', 'rect') or (tag == 'path' and re.match(r'M', e.get('d', ''))):
                out.append(bbox(e))
        return min(b[0] for b in out), min(b[1] for b in out), max(b[2] for b in out), max(b[3] for b in out)
    bag, who = box(p['bag-shape']), box(p['people-pets'])
    assert who[0] - bag[2] >= 2 * (bag[2] - bag[0]), (bag, who)


# ---- Food pack Task 7: diagrams carry only what their topic carries ----
# figure -> (topic, section heading it sits in, phrases drawn on it (each also in the topic's own text), wording that must
#            not be drawn or in the alt text, phrases the caption carries)
FOOD_FIGS = {
    'food-fridge-freezer': (
        'surv-food-power-out', 'How long it stays cold',
        ['keep the fridge and freezer doors shut', 'fridge', 'full freezer', 'half-full freezer', 'keeps food cold for',
         'about 4 hours', 'about 48 hours', 'about 24 hours', 'with the door shut',
         'before you eat, cook or refreeze anything', 'check it in is it still good?'],
        [r'\bsafe', r'\bok\b', r'\bfine\b', r'\bfresh', r'°', r'\bdays?\b', r'\bminutes?\b', r'\bopen', r'outside',
         r'\bice\b', r'cooler', r'generator', r'thermometer', r'throw', r'\b(?!4\b|48\b|24\b)\d+'],
        ['keep the fridge and freezer doors shut.', 'a fridge keeps food cold for about 4 hours',
         'a full freezer about 48 hours and a half-full freezer about 24 hours',
         'before you eat, cook or refreeze anything, check it in is it still good?']),
    'food-cans-to-discard': (
        'surv-food-still-good', 'Cans and jars',
        ['any of these signs', 'throw it out', 'leaking, bulging', 'or swollen', 'looks damaged', 'cracked or abnormal',
         'spurts liquid or foam', 'when opened', 'food is discolored', 'moldy or smells bad',
         'you cannot see, smell or taste', 'the toxin that causes botulism', 'and even a small taste of food that has it',
         'can be deadly', 'it can be in cans that look normal', 'and in food that smells and tastes normal',
         'how to get rid of a suspect can or jar', 'without touching what is inside', 'food poisoning and botulism'],
        [r'\bsafe', r'\bok\b', r'\bfine\b', r'\bgood\b', r'\bkeep\b', r'\bsave', r'\d', r'flood', r'pull', r'screw',
         r'rust', r'small dent', r'boil', r'sniff', r'taste it', r'\beat\b'],
        ['any of these signs means home-canned or store-bought food might be contaminated',
         'you cannot see, smell or taste the toxin that causes botulism, and even a small taste of food that has it can be deadly',
         'it can be in cans that look normal and in food that smells and tastes normal',
         'how to get rid of a suspect can or jar without touching what is inside, and the signs of botulism, are in food '
         'poisoning and botulism.']),
}


@pytest.mark.parametrize('name', sorted(FOOD_FIGS))
def test_food_figure_sits_once_in_its_section(name):
    tid, section = FOOD_FIGS[name][:2]
    assert name in figs.F, name
    assert topic_figs()[tid].count(name) == 1, (tid, name)
    assert fig_section(tid, name) == [section]


@pytest.mark.parametrize('name', sorted(FOOD_FIGS))
def test_food_figure_draws_its_topics_words(name):
    tid, _, words, _, _ = FOOD_FIGS[name]
    d, topic = drawn_of(name), topic_text(tid)
    for w in words:
        assert w in d, f'{name}: missing {w!r} in drawn text: {d}'
        assert w in topic, f'{name}: {w!r} is not in {tid}'


@pytest.mark.parametrize('name', sorted(FOOD_FIGS))
def test_food_figure_every_drawn_line_is_in_the_text(name):
    """Every text string drawn is word for word in the topic's own text (not its captions or sources); trailing punctuation
    that only ends a line is ignored. No step badges: neither figure is a sequence."""
    tid = FOOD_FIGS[name][0]
    source = topic_text(tid)
    for _, _, s in _texts(name):
        line = s.strip().rstrip(':,.').strip()
        assert line and line in source, f'{name}: drawn {s!r} is not in {tid}'


@pytest.mark.parametrize('name', sorted(FOOD_FIGS))
def test_food_figure_draws_no_unstated_wording(name):
    banned = FOOD_FIGS[name][3]
    for t in (drawn_of(name), alt_of(name)):
        for pat in banned:
            assert not re.search(pat, t), f'{name}: says {pat!r}: {t}'


@pytest.mark.parametrize('name', sorted(FOOD_FIGS))
def test_food_figure_alt_and_caption(name):
    """The caption is the topic's own sentences, word for word, and carries what the picture shows."""
    tid, _, _, _, cap_words = FOOD_FIGS[name]
    alt = alt_of(name)
    assert len(alt) > 40, alt
    cap = topic_caption(tid, name)
    for w in cap_words:
        assert w in cap, f'{name}: caption missing {w!r}: {cap}'
    assert not re.search(r'\bsafe|\bfine\b|\bok\b', cap)
    for sentence in [x.strip() for x in re.split(r'(?<=[.?])\s', cap) if x.strip()]:
        assert sentence.rstrip('.') in topic_text(tid), f'{name}: caption sentence not in the topic: {sentence!r}'


def _rows(name):
    """Drawn texts grouped into the horizontal bands between the figure's full-width dashed dividers."""
    root = ET.fromstring(figs.F[name][0])
    cuts = sorted(float(e.get('y1')) for e in root.iter() if e.tag.split('}')[-1] == 'line' and 'd' in e.get('class', '').split()
                  and e.get('y1') == e.get('y2') and float(e.get('x2')) - float(e.get('x1')) > 250)
    bands = [-1e9] + cuts + [1e9]
    out = [[] for _ in range(len(bands) - 1)]
    for x, y, s in _texts(name):
        out[next(i for i in range(len(bands) - 1) if bands[i] < y < bands[i + 1])].append(s)
    return out


def test_fridge_freezer_hold_times_carry_their_condition_and_appliance():
    """Each hold time is drawn in its own band with its appliance, "keeps food cold for" and "with the door shut" (never the
    number alone), in the table's order: fridge, full freezer, half-full freezer. The only numbers are the three hold times."""
    rows = _rows('food-fridge-freezer')
    want = [('fridge', 'about 4 hours'), ('full freezer', 'about 48 hours'), ('half-full freezer', 'about 24 hours')]
    held = [r for r in rows if any(re.search(r'\d', s) for s in r)]
    assert len(held) == 3, rows
    for r, (who, hours) in zip(held, want):
        assert r[0] == who, (r, who)
        assert hours in r and 'keeps food cold for' in r and 'with the door shut' in r, r
        assert [s for s in r if re.search(r'\d', s)] == [hours], r
    assert rows[0] == ['keep the fridge and freezer doors shut'], rows[0]
    assert rows[-1] == ['before you eat, cook or refreeze anything,', 'check it in', 'is it still good?'], rows[-1]
    title = [t for t in ET.fromstring(figs.F['food-fridge-freezer'][0]).iter() if t.tag.split('}')[-1] == 'text'
             and ''.join(t.itertext()) == 'Is it still good?']
    assert len(title) == 1 and {'tb', 'tl'} & set(title[0].get('class').split()), 'the page name stands on its own line, in bold'
    plain = [t for t in ET.fromstring(figs.F['food-fridge-freezer'][0]).iter() if t.tag.split('}')[-1] == 'text'
             and ''.join(t.itertext()) == 'check it in']
    assert len(plain) == 1 and 'tb' not in (plain[0].get('class') or '').split()
    assert sorted(re.findall(r'\d+', alt_of('food-fridge-freezer'))) == ['24', '4', '48']
    for s in ('about 4 hours', 'about 48 hours', 'about 24 hours', 'with the door', 'doors shut', 'check it in is it still good?'):
        assert s in alt_of('food-fridge-freezer'), s


def _box(el):
    out = []
    for e in el.iter():
        if e.tag.split('}')[-1] in ('rect', 'line', 'path'):
            out.append(bbox(e))
    return min(b[0] for b in out), min(b[1] for b in out), max(b[2] for b in out), max(b[3] for b in out)


def test_fridge_freezer_doors_shut_and_full_versus_half_full():
    """The fridge door and both freezer lids are drawn shut (the lid sits on the body and spans it); the full freezer's food
    reaches most of the way up, the half-full one's no more than about half; the half-full freezer's food is kept close
    together (one block, no gaps wider than the drawn line)."""
    p = parts('food-fridge-freezer')
    need = {'fridge', 'fridge-handle', 'lid-full', 'body-full', 'food-full', 'lid-half', 'body-half', 'food-half'}
    assert need <= set(p), need - set(p)
    for k in ('full', 'half'):
        lx0, ly0, lx1, ly1 = bbox(p[f'lid-{k}'])
        bx0, by0, bx1, by1 = bbox(p[f'body-{k}'])
        assert lx0 <= bx0 and lx1 >= bx1 and ly1 == by0, (k, (lx0, ly0, lx1, ly1), (bx0, by0, bx1, by1))
        fx0, fy0, fx1, fy1 = _box(p[f'food-{k}'])
        assert bx0 < fx0 and fx1 < bx1 and by0 < fy0 and fy1 < by1, f'{k}: food inside the freezer'
    bx0, by0, bx1, by1 = bbox(p['body-full'])
    fill_full = (by1 - _box(p['food-full'])[1]) / (by1 - by0)
    bx0, by0, bx1, by1 = bbox(p['body-half'])
    fill_half = (by1 - _box(p['food-half'])[1]) / (by1 - by0)
    assert fill_full >= 0.8 and 0.35 <= fill_half <= 0.55, (fill_full, fill_half)
    hx0, hy0, hx1, hy1 = bbox(p['fridge-handle'])
    fx0, fy0, fx1, fy1 = bbox(p['fridge'])
    assert fx0 < hx0 and hx1 < fx1 and fy0 < hy0 and hy1 < fy1, 'the handle is on the closed door'


def test_cans_signs_in_the_topics_order_with_the_warning_and_pointer_below():
    """The four signs read left to right, top to bottom in the order of the topic's list; "Any of these signs" and "Throw it
    out" are above them; the whole botulism warning, then the disposal pointer, are below them."""
    texts = _texts('food-cans-to-discard')
    first = ['leaking, bulging', 'looks damaged,', 'spurts liquid or foam', 'food is discolored,']
    pos = [next((x, y) for x, y, s in texts if s == f) for f in first]
    assert pos[0][1] == pos[1][1] < pos[2][1] == pos[3][1] and pos[0][0] < pos[1][0] and pos[2][0] < pos[3][0], pos
    top = [y for x, y, s in texts if s in ('any of these signs:', 'throw it out')]
    assert len(top) == 2 and max(top) < min(y for _, y in pos) - 60
    order = [s for _, y, s in sorted(texts, key=lambda t: t[1]) if y > max(y for _, y in pos)]
    assert order[2:] == ['you cannot see, smell or taste', 'the toxin that causes botulism,',
                         'and even a small taste of food that has it', 'can be deadly.', 'it can be in cans that look normal',
                         'and in food that smells and tastes normal.', 'how to get rid of a suspect can or jar',
                         'without touching what is inside:', 'food poisoning and botulism'], order
    alt = alt_of('food-cans-to-discard')
    for w in ('and even a small taste of food that has it can be deadly',
              'it can be in cans that look normal and in food that smells and tastes normal',
              'how to get rid of a suspect can or jar without touching what is inside', 'food poisoning and botulism'):
        assert w in alt, w


def _path_points(d):
    """Every end and control point of a path (absolute and relative M L H V Q A Z), enough for a bounding box."""
    pts, x, y, sx, sy = [], 0.0, 0.0, 0.0, 0.0
    for cmd, args in re.findall(r'([MLHVQAZmlhvqaz])([^MLHVQAZmlhvqaz]*)', d):
        n = [float(v) for v in re.findall(r'-?\d+(?:\.\d+)?', args)]
        rel = cmd.islower()
        c = cmd.upper()
        step = {'M': 2, 'L': 2, 'H': 1, 'V': 1, 'Q': 4, 'A': 7, 'Z': 0}[c]
        if c == 'Z':
            x, y = sx, sy
            continue
        for i in range(0, len(n), step):
            a = n[i:i + step]
            if c in 'ML':
                x, y = (x + a[0], y + a[1]) if rel else (a[0], a[1])
                if c == 'M' and i == 0:
                    sx, sy = x, y
            elif c == 'H':
                x = x + a[0] if rel else a[0]
            elif c == 'V':
                y = y + a[0] if rel else a[0]
            elif c == 'Q':
                pts.append((x + a[0], y + a[1]) if rel else (a[0], a[1]))
                x, y = (x + a[2], y + a[3]) if rel else (a[2], a[3])
            elif c == 'A':
                x, y = (x + a[5], y + a[6]) if rel else (a[5], a[6])
            pts.append((x, y))
    return pts


def _shape_box(el):
    xs, ys = [], []
    for e in el.iter():
        tag = e.tag.split('}')[-1]
        if tag in ('circle', 'ellipse'):
            cx, cy = float(e.get('cx')), float(e.get('cy'))
            rx, ry = float(e.get('r') or e.get('rx')), float(e.get('r') or e.get('ry'))
            if e.get('transform'):   # rotated: take the larger radius both ways
                rx = ry = max(rx, ry)
            xs += [cx - rx, cx + rx]; ys += [cy - ry, cy + ry]
        elif tag in ('rect', 'line'):
            b = bbox(e); xs += [b[0], b[2]]; ys += [b[1], b[3]]
        elif tag == 'path':
            for px, py in _path_points(e.get('d')):
                xs.append(px); ys.append(py)
    return min(xs), min(ys), max(xs), max(ys)


CAN_SIGNS = {'sign-1': 'leaking, bulging', 'sign-2': 'looks damaged,', 'sign-3': 'spurts liquid or foam',
             'sign-4': 'food is discolored,'}


@pytest.mark.parametrize('part', sorted(CAN_SIGNS))
def test_cans_each_drawing_sits_over_its_own_label(part):
    """Each sign's drawing is centred over the label naming it and just above it, inside the same panel, so swapping two
    drawings fails."""
    texts = _texts('food-cans-to-discard')
    lx, ly = next((x, y) for x, y, s in texts if s == CAN_SIGNS[part])
    x0, y0, x1, y1 = _shape_box(parts('food-cans-to-discard')[part])
    assert abs((x0 + x1) / 2 - lx) <= 20, (part, (x0, x1), lx)
    assert y1 < ly - 10 and ly - y1 <= 45, (part, y1, ly)
    for other, label in CAN_SIGNS.items():
        if other != part:
            ox, oy = next((x, y) for x, y, s in texts if s == label)
            assert not (x0 <= ox <= x1 and y0 <= oy <= y1), (part, 'overlaps the label of', other)


def test_cans_no_can_or_jar_drawn_without_a_sign():
    """Every shape in the figure belongs to one of the four sign drawings, apart from the dashed dividers: no can or jar is
    drawn as if a can without these signs were fine."""
    root = ET.fromstring(figs.F['food-cans-to-discard'][0])
    assert set(CAN_SIGNS) <= set(parts('food-cans-to-discard'))
    loose = []
    for g in root:
        tag = g.tag.split('}')[-1]
        if tag == 'text' or g.get('data-part') in CAN_SIGNS:
            continue
        if tag == 'line' and set(g.get('class', '').split()) >= {'m', 'd'}:
            continue
        loose.append(ET.tostring(g, encoding='unicode'))
    assert loose == [], loose



# ---- Land pack (v7.7) Task 6: the deer diagrams carry only what their topic carries ----
# figure -> (topic, section heading it sits in, phrases drawn on it (each also in the topic's own text), wording that must
#            not be drawn or in the alt text, phrases the caption carries)
LAND_FIGS = {
    'land-deer-vitals': (
        'surv-land-big-game', 'Shot placement',
        ['broadside (side-on)', 'aim just behind the shoulder', 'pick one small spot there,', 'smaller than a pie plate',
         'heart and lungs', 'about one third', 'of the way up from', 'the bottom of the chest', 'follow the back edge',
         'of the front leg nearest you'],
        [r'\d', r'\bhead\b', r'\bneck\b', r'quartering', r'facing you', r'liver', r'gut', r'spine', r'backbone', r'brain',
         r'shoulder blade', r'diaphragm', r'\bsafe', r'yards?'],
        ['aim just behind the shoulder', 'one third of the way up from the bottom of the chest', 'smaller than a pie plate']),
    'land-deer-cuts': (
        'surv-land-butchering', 'The cuts and what each is good for',
        ['backstrap (loin)', 'tenderloin', 'inside, along the underside', 'of the spine, near the pelvis', 'neck', 'shoulder',
         'ribs', 'flank', 'hind leg', 'sirloin', 'top round, bottom round,', 'eye of round', 'shank'],
        [r'\d', r'brain', r'spinal cord', r'lymph', r'spleen', r'\bsaw', r'brisket', r'tongue', r'liver', r'heart',
         r'steak', r'roast', r'\bsafe'],
        ['tenderloins', 'inside, along the underside of the spine, near the pelvis']),
}


def _drawn_lines(name):
    """Every drawn text string."""
    return [s for _, _, s in _texts(name)]


@pytest.mark.parametrize('name', sorted(LAND_FIGS))
def test_land_figure_sits_once_in_its_section(name):
    tid, section = LAND_FIGS[name][:2]
    assert name in figs.F, name
    assert topic_figs()[tid].count(name) == 1, (tid, name)
    assert fig_section(tid, name) == [section]


@pytest.mark.parametrize('name', sorted(LAND_FIGS))
def test_land_figure_svg_parses(name):
    root = ET.fromstring(figs.F[name][0])
    assert root.get('viewBox').startswith('0 0 340 '), root.get('viewBox')
    assert root.get('role') == 'img' and root.get('aria-label') == figs.F[name][1]


@pytest.mark.parametrize('name', sorted(LAND_FIGS))
def test_land_figure_draws_its_topics_words(name):
    tid, _, words, _, _ = LAND_FIGS[name]
    d, topic = drawn_of(name), topic_text(tid)
    for w in words:
        assert w in d, f'{name}: missing {w!r} in drawn text: {d}'
        assert w.rstrip(',') in topic, f'{name}: {w!r} is not in {tid}'


@pytest.mark.parametrize('name', sorted(LAND_FIGS))
def test_land_figure_every_drawn_line_is_in_the_text(name):
    """Every text string drawn is word for word in the topic's own text (not its captions or sources); trailing punctuation
    that only ends a line is ignored."""
    tid = LAND_FIGS[name][0]
    source = topic_text(tid)
    for s in _drawn_lines(name):
        line = s.strip().rstrip(':,.').strip()
        assert line and line in source, f'{name}: drawn {s!r} is not in {tid}'


@pytest.mark.parametrize('name', sorted(LAND_FIGS))
def test_land_figure_draws_no_unstated_wording(name):
    banned = LAND_FIGS[name][3]
    for t in (' '.join(_drawn_lines(name)), alt_of(name)):
        for pat in banned:
            assert not re.search(pat, t), f'{name}: says {pat!r}: {t}'


@pytest.mark.parametrize('name', sorted(LAND_FIGS))
def test_land_figure_alt_and_caption(name):
    """The caption is the topic's own sentences, word for word."""
    tid, _, _, _, cap_words = LAND_FIGS[name]
    assert len(alt_of(name)) > 40
    cap = topic_caption(tid, name)
    for w in cap_words:
        assert w in cap, f'{name}: caption missing {w!r}: {cap}'
    for sentence in [x.strip() for x in re.split(r'(?<=[.?])\s', cap) if x.strip()]:
        assert sentence.rstrip('.') in topic_text(tid), f'{name}: caption sentence not in the topic: {sentence!r}'


def test_land_figures_draw_no_plant_and_no_person():
    """Land pack constraint: no drawing of any plant; nothing showing use on a person."""
    for name in LAND_FIGS:
        svg, label = figs.F[name]
        t = (svg + label).lower()
        for word in ('leaf', 'leaves', 'plant', 'person', 'hand', 'skin'):
            assert word not in t, (name, word)


def test_deer_vitals_aim_is_on_the_leg_line_a_third_of_the_way_up():
    """The aim mark sits on the line up the back edge of the near front leg, one third of the way from the bottom of the
    chest to the top of the back, inside the shaded heart and lungs."""
    root = ET.fromstring(figs.F['land-deer-vitals'][0])
    els = {}
    for e in root.iter():
        if e.get('data-part'):
            els.setdefault(e.get('data-part'), []).append(e)
    dx, dy = (float(v) for v in re.findall(r'-?\d+(?:\.\d+)?', els['deer'][0].get('transform')))
    leg = els['leg-line'][0]
    thirds = sorted(float(e.get('y1')) for e in els['third'])
    assert len(thirds) == 3, 'bottom, one third and top only: a two-thirds tick reads as a second aim mark'
    top, bot = thirds[0], thirds[-1]
    assert abs(thirds[1] - (bot - (bot - top) / 3)) < 0.2
    aim = els['aim'][0]
    ax, ay = float(aim.get('cx')) - dx, float(aim.get('cy')) - dy
    assert ax == float(leg.get('x1')) == float(leg.get('x2'))
    assert abs(ay - (bot - (bot - top) / 3)) < 0.2, (ay, top, bot)
    v = els['vital'][0]
    cx, cy, rx, ry = (float(v.get(k)) for k in ('cx', 'cy', 'rx', 'ry'))
    assert ((ax - cx) / rx) ** 2 + ((ay - cy) / ry) ** 2 < 1, 'the aim spot is inside the heart and lungs'


def test_deer_cuts_tenderloin_is_drawn_dashed_as_inside():
    root = ET.fromstring(figs.F['land-deer-cuts'][0])
    t = [e for e in root.iter() if e.get('data-part') == 'tenderloin']
    assert len(t) == 1 and 'd' in t[0].get('class').split()


def test_field_dressing_deer_steps_carry_no_figure():
    """Controller ruling (docs/v7.7-rulings.md, Diagrams): the deer steps ship text-only; neither the failed redraw nor the
    old top view is drawn or kept."""
    assert topic_figs()['surv-field-dressing-game'] == ['dress-fish']
    assert fig_section('surv-field-dressing-game', 'dress-fish') == ['Small game and fish']
    assert 'dress-deer' not in figs.F and 'land-field-dressing-cuts' not in figs.F


def test_deer_cuts_shank_is_a_label_only():
    """The text names where the shank starts (the knee joint) but not where it ends, so no shank boundary or shading is drawn."""
    root = ET.fromstring(figs.F['land-deer-cuts'][0])
    assert not [e for e in root.iter() if e.get('data-part') == 'shank']
    assert not [e for e in root.iter() if 'wf' in (e.get('class') or '').split()]
    assert 'shank' in drawn_of('land-deer-cuts')
