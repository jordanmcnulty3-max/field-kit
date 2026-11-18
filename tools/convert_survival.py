"""HISTORICAL ONE-OFF, kept for the record: the v6 to v7 conversion, already run (v7 Task 2). Do not run it again.
The topics in src/survival/ have since been source-checked and rewritten; running this would overwrite them with the
v6 draft text and placeholder sources. It refuses to write unless given --force.

One-off v6 to v7 conversion: reads tests/fixtures/survival-v6.html, writes src/survival/<id>.json.

Run `python3 tools/convert_survival.py --force`. Text is carried word for word (entities decoded, inline tags dropped);
the only deletions are the ones listed in docs/v7-migration.md and applied in DELETIONS below.
"""
import html
import json
import os
import re
import sys
from html.parser import HTMLParser

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SOURCE = os.path.join(ROOT, 'tests', 'fixtures', 'survival-v6.html')
OUT = os.path.join(ROOT, 'src', 'survival')
FIG_RE = re.compile(r'\{\{fig:([a-z0-9-]+)\|(.*?)\}\}', re.S)

PLACEHOLDER_SOURCE = {'name': 'Not yet source-checked', 'used': 'Converted from v6 text; checked in Tasks 13 to 16'}

# where/when: tagged only where the topic does not apply everywhere. summary: from the topic's own wording.
META = {
    'surv-ten-essentials': dict(
        keywords=['backcountry', 'essentials', 'pack', 'kit', 'headlamp', 'first aid', 'whistle'],
        summary='Pack these on every trip into the backcountry, even a short one.', where=['rural', 'woods']),
    'surv-find-water': dict(
        keywords=['water', 'dew', 'rain', 'transpiration', 'stream', 'thirst'],
        summary='Water runs downhill: check valley bottoms, the base of cliffs and dry stream beds.'),
    'surv-make-water-safe': dict(
        keywords=['boil', 'bleach', 'filter', 'purify', 'treat', 'drinking water', 'tablets'],
        summary='Strain cloudy water, then boil it for 1 minute, or treat it with unscented bleach.'),
    'surv-shelter': dict(
        keywords=['shelter', 'debris hut', 'lean-to', 'tarp', 'snow trench', 'insulation', 'bed'],
        summary='Pick flat, dry ground, insulate from the ground first and keep the shelter small.',
        where=['rural', 'woods']),
    'surv-fire': dict(
        keywords=['fire', 'tinder', 'kindling', 'ferro rod', 'teepee', 'log cabin', 'wet weather'],
        summary='Gather about twice what you think you need, then build and light the fire.'),
    'surv-food-and-wild-plants': dict(
        keywords=['food', 'plants', 'edible', 'hemlock', 'poisonous', 'cattail', 'acorns', 'insects'],
        summary='Food is the lowest priority, and you should only eat a plant you can identify with certainty.',
        where=['rural', 'woods']),
    'surv-traps-and-fishing': dict(
        keywords=['snare', 'trap', 'deadfall', 'fishing', 'gorge hook', 'fish trap', 'squirrel'],
        summary='Set many traps on active game trails, and leave several baited lines out overnight.',
        where=['rural', 'woods']),
    'surv-field-dressing-game': dict(
        keywords=['field dressing', 'deer', 'game', 'rabbit', 'fish', 'tularemia', 'gutting'],
        summary='Open the belly without puncturing the stomach or intestines, then cool the carcass fast.',
        where=['rural', 'woods']),
    'surv-navigation-without-a-compass': dict(
        keywords=['navigation', 'compass', 'shadow stick', 'north star', 'watch', 'moon', 'pace count'],
        summary='Find direction from a shadow stick, an analog watch or the night sky, and stay on course.',
        where=['rural', 'woods']),
    'surv-signal-for-rescue': dict(
        keywords=['signal', 'rescue', 'whistle', 'mirror', 'ground symbols', 'distress', 'aircraft'],
        summary='Three of anything is a distress signal: three fires, three whistle blasts, three flashes.'),
    'surv-weather-and-lightning': dict(
        keywords=['weather', 'lightning', 'thunder', 'storm', 'clouds', 'front'],
        summary='If you can hear thunder, get inside a building or hard-topped vehicle.'),
    'surv-dangerous-animals': dict(
        keywords=['bear', 'bear spray', 'snake', 'tick', 'bite', 'animals', 'wildlife'],
        summary='Never run from a bear, check yourself daily for ticks, and get a snakebite to a hospital.',
        where=['rural', 'woods']),
    'surv-river-crossings': dict(
        keywords=['river', 'crossing', 'ford', 'current', 'strainer', 'pole', 'swept away'],
        summary='Look for a wide, shallow, slow section, and if in doubt, don’t cross.',
        where=['rural', 'woods']),
    'surv-knots': dict(
        keywords=['knots', 'bowline', 'clove hitch', 'taut-line', 'trucker', 'square knot', 'sheet bend'],
        summary='Bowline, clove hitch, taut-line hitch, trucker’s hitch, square knot and sheet bend.'),
}

# (topic id, exact removed text, reason): mirrors the Deletions list in docs/v7-migration.md.
DELETIONS = {
    'surv-shelter': [' and desert',
                     'In the desert, shade comes first. Two layers of material with an air gap between them are much cooler than one. Stay off the hot ground.',
                     'Desert shade. The air gap keeps the sun-heated top layer from heating the space below.'],
    'surv-navigation-without-a-compass': [
        'Southern Hemisphere: point 12 o’clock at the sun. North is halfway between 12 and the hour hand.',
        'Southern Cross: extend the long axis of the cross about four and a half times its length, then drop straight down to the horizon for south.',
        'The two bright Pointers beside the cross help confirm you have the real one, not the dimmer “false cross.”'],
    'surv-dangerous-animals': [
        'Grizzly (brown) bear attack: leave your pack on, lie flat on your stomach with your hands clasped behind your neck, and play dead. If the attack continues, fight back hard.',
        'Mountain lions',
        'Don’t run or crouch. Make yourself look big, keep eye contact and back away slowly. If attacked, fight back.'],
}
DROPPED_FIGS = {'shelter-desert', 'nav-cross'}
FROSTBITE_REMOVED = ('Check each other for frostbite: white or grey-yellow skin that feels hard or waxy. '
                     'Don’t rub it, and only rewarm it if it won’t freeze again.')


def norm(s):
    return re.sub(r'\s+', ' ', s).strip()


class Parser(HTMLParser):
    """Turns a topic body into events: ('h3', t) ('p', t) ('list', [t]) ('steps', [t]) ('fig', name, cap) ('knot', title, rest)."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.events, self.buf, self.target = [], [], None
        self.items, self.kind, self.knot = None, None, None

    def _open(self, target):
        self.target, self.buf = target, []

    def _close(self):
        text = norm(''.join(self.buf))
        self.target, self.buf = None, []
        return text

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag in ('h3', 'p'):
            self._open(tag)
        elif tag in ('ul', 'ol'):
            self.items, self.kind = [], 'steps' if tag == 'ol' else 'list'
        elif tag == 'li':
            self._open('li')
        elif tag == 'div' and a.get('class') == 'knot':
            self.knot = {'title': None}
        elif tag == 'b' and self.knot is not None and self.knot['title'] is None and self.target is None:
            self._open('ktitle')
        elif tag == 'figm':
            self.events.append(('fig', a['n'], norm(a['c'])))

    def handle_endtag(self, tag):
        if tag in ('h3', 'p') and self.target == tag:
            self.events.append((tag, self._close()))
        elif tag == 'li' and self.target == 'li':
            self.items.append(self._close())
        elif tag in ('ul', 'ol'):
            self.events.append((self.kind, self.items))
            self.items = None
        elif tag == 'b' and self.target == 'ktitle':
            self.knot['title'] = self._close()
            self._open('krest')
        elif tag == 'div' and self.knot is not None:
            rest = self._close() if self.target == 'krest' else ''
            self.events.append(('knot', self.knot['title'], rest))
            self.knot = None

    def handle_data(self, data):
        if self.target:
            self.buf.append(data)


def parse(fragment):
    fragment = FIG_RE.sub(lambda m: '<figm n="%s" c="%s">' % (m.group(1), m.group(2).replace('"', '&quot;')), fragment)
    p = Parser()
    p.feed(fragment)
    p.close()
    return p.events


def blocks_from(events, title, added):
    """Group events into sections. Text before the first h3 gets the topic title as its heading (recorded in added)."""
    sections, cur = [], None

    def need():
        nonlocal cur
        if cur is None:
            cur = {'h': title, 'blocks': []}
            sections.append(cur)
            added.append(title)
        return cur

    for ev in events:
        kind = ev[0]
        if kind == 'h3':
            cur = {'h': ev[1], 'blocks': []}
            sections.append(cur)
        elif kind == 'knot':
            cur = {'h': ev[1], 'blocks': [{'p': ev[2]}]}
            sections.append(cur)
        elif kind == 'p':
            need()['blocks'].append({'p': ev[1]})
        elif kind in ('list', 'steps'):
            need()['blocks'].append({kind: ev[1]})
        elif kind == 'fig':
            need()['blocks'].append({'fig': ev[1], 'cap': ev[2]})
    return sections


def apply_deletions(tid, sections):
    """Remove each listed text from the converted topic: a whole block or list item, a heading, or a heading suffix."""
    for text in DELETIONS.get(tid, []):
        done = False
        for sec in sections:
            if sec['h'] == text:                      # a whole section heading, with its blocks (Mountain lions)
                sec['h'] = None
                done = True
            elif sec['h'] and sec['h'].endswith(text) and text.startswith(' '):
                sec['h'] = sec['h'][:-len(text)]
                done = True
            if done:
                break
            for b in list(sec['blocks']):
                if b.get('p') == text or b.get('cap') == text:
                    sec['blocks'].remove(b)
                    done = True
                    break
                for k in ('list', 'steps'):
                    if k in b:
                        match = [i for i in b[k] if i == text]
                        if match:
                            b[k].remove(text)
                            done = True
                if done:
                    break
            if done:
                break
        assert done, (tid, text)
    sections[:] = [s for s in sections if s['h'] is not None]
    for sec in sections:
        sec['blocks'] = [b for b in sec['blocks'] if b.get('list') != [] and b.get('steps') != []]
    sections[:] = [s for s in sections if s['blocks']]


def topic_dict(tid, title, sections):
    meta = META[tid]
    t = {'id': tid, 'title': title, 'category': 'basics', 'keywords': meta['keywords'], 'summary': meta['summary']}
    if 'where' in meta:
        t['where'] = meta['where']
    if 'when' in meta:
        t['when'] = meta['when']
    t.update(sections=sections, sources=[dict(PLACEHOLDER_SOURCE)], reviewed='2026-11-17', draft=True)
    return t


def priorities(src):
    prio = re.search(r'<h2>Priorities</h2>(.*?)</div>', src, re.S).group(1)
    sections = [{'h': 'Priorities', 'blocks': [{'p': e[1]} for e in parse(prio) if e[0] == 'p']}]
    for region, heading in (('temperate', 'Forest'), ('cold', 'Cold and snow'), ('coastal', 'Coast and sea')):
        frag = re.search(r'<div class="region" data-region="%s"[^>]*>(.*?)</div>' % region, src, re.S).group(1)
        items = [e for e in parse(frag) if e[0] == 'list'][0][1]
        if region == 'cold':
            items = [i.replace(' ' + FROSTBITE_REMOVED, '') for i in items]
            assert not any('frostbite' in i for i in items)
        blocks = [{'list': items}]
        if region == 'cold':
            blocks.append({'link': 'p:frostbite', 'label': 'Frostbite care'})
        sections.append({'h': heading, 'blocks': blocks})
    return topic_dict_priorities(sections)


def topic_dict_priorities(sections):
    return {'id': 'surv-priorities', 'title': 'Priorities', 'category': 'basics',
            'keywords': ['priorities', 'rule of threes', 'STOP', 'lost', 'hypothermia', 'frostbite', 'seawater'],
            'summary': 'Work the problem in order: air, shelter, water, food. If you’re lost, STOP: Stop, Think, Observe, Plan.',
            'sections': sections, 'sources': [dict(PLACEHOLDER_SOURCE)], 'reviewed': '2026-11-17', 'draft': True}


def convert():
    src = open(SOURCE, encoding='utf-8').read()
    topics, added = [], {}
    for chunk in src.split('</details>')[:-1]:
        tid = re.search(r'<details class="ref" id="(surv-[^"]+)"', chunk).group(1)
        title = html.unescape(norm(re.sub(r'<[^>]+>', '', re.search(r'<summary>(.*?)</summary>', chunk, re.S).group(1))))
        body = chunk[chunk.index('<div class="body">') + len('<div class="body">'):chunk.rindex('</div>')]
        added[tid] = []
        sections = blocks_from(parse(body), title, added[tid])
        apply_deletions(tid, sections)
        topics.append(topic_dict(tid, title, sections))
    topics.insert(0, priorities(src))
    return topics, added


def main():
    if '--force' not in sys.argv[1:]:
        print('convert_survival.py is a historical one-off: running it would overwrite the source-checked topics in '
              'src/survival/ with v6 draft text. Nothing was written. Pass --force only to redo the original conversion.',
              file=sys.stderr)
        return 2
    os.makedirs(OUT, exist_ok=True)
    topics, added = convert()
    for t in topics:
        with open(os.path.join(OUT, t['id'] + '.json'), 'w', encoding='utf-8') as f:
            json.dump(t, f, ensure_ascii=False, indent=2)
            f.write('\n')
    print(f'wrote {len(topics)} topics to {OUT}')
    for tid, heads in added.items():
        if heads:
            print('added heading:', tid, '||', heads[0])


if __name__ == '__main__':
    sys.exit(main())
