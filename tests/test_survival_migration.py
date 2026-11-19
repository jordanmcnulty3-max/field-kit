"""Task 2 migration checks, narrowed in Task 13 to topics still in draft; plus the real-sources check. Plain pytest, no browser."""
import glob
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, 'figs'))

import figs  # noqa: E402
from tools.validate import TOOL_NAMES, validate_topics  # noqa: E402

FIXTURE = os.path.join(ROOT, 'tests', 'fixtures', 'survival-v6.html')
FIG_RE = re.compile(r'\{\{fig:([a-z0-9-]+)\|(.*?)\}\}', re.S)


def v6():
    return open(FIXTURE, encoding='utf-8').read()


# The 15 topics migrated in v7 (Task 2); content packs add new topics beside them.
MIGRATED = {'surv-dangerous-animals', 'surv-field-dressing-game', 'surv-find-water', 'surv-fire', 'surv-food-and-wild-plants',
            'surv-knots', 'surv-make-water-safe', 'surv-navigation-without-a-compass', 'surv-priorities',
            'surv-river-crossings', 'surv-shelter', 'surv-signal-for-rescue', 'surv-ten-essentials',
            'surv-traps-and-fishing', 'surv-weather-and-lightning'}
# Migrated topics a content pack moved to another category (water pack, Task 5; heat pack, Task 7; drafts while it was written, released in the pack).
REOPENED = {'surv-find-water': 'water', 'surv-make-water-safe': 'water', 'surv-fire': 'heat', 'surv-shelter': 'heat'}
# Exact figure sets are pinned for these topics: find-water keeps both v6 figures; make-water-safe's water-safe was removed in v7 (Task 13)
# and restored with the 5,000 ft / 5% to 9% wording in the water pack's Task 8, which also adds the water-heater,
# bucket-toilet, cat-hole and hand-washing-station figures to the new water topics.
PINNED_FIGS = {'surv-find-water': {'water-bend', 'water-bag'}, 'surv-make-water-safe': {'water-safe'},
                 'surv-water-in-the-house': {'water-heater-drain'}, 'surv-toilet-no-water': {'toilet-buckets'},
                 'surv-latrines': {'latrine'}, 'surv-handwashing': {'handwash-station'},
                 # heat pack Task 7 deepened fire and shelter; heat pack Task 8 restores fire-ferro (push the striker down) and
                 # shelter-tarp (tarp lean-to) redrawn to the checked text, and adds the quinzhee, generator, stove and warm-room figures
                 'surv-fire': {'fire-sizes', 'fire-platform', 'fire-lays', 'fire-ferro'},
                 'surv-shelter': {'shelter-site', 'shelter-debris', 'shelter-leanto', 'shelter-snow', 'shelter-tarp', 'quinzhee'},
                 'surv-generators': {'generator-placement'}, 'surv-wood-stoves-fireplaces': {'heater-clearance'},
                 'surv-heat-out': {'warm-room'},
                 # radiation pack Task 7: where to shelter and coming inside, drawn from their checked text
                 'surv-fallout-where-to-shelter': {'fallout-shelter-spots'}, 'surv-fallout-coming-inside': {'fallout-coming-inside'}}


def new_topics():
    return {t['id']: t for t in (json.load(open(p, encoding='utf-8')) for p in sorted(glob.glob(os.path.join(ROOT, 'src', 'survival', '*.json'))))}


def test_every_topic_has_real_sources():
    """Replaces the word-for-word conversion check once source-checking started (Task 13): every topic is either
    still a draft or has no placeholder source."""
    topics = new_topics()
    assert len(MIGRATED) == 15 and MIGRATED <= set(topics)
    for tid, t in topics.items():
        assert t['sources'], tid
        if t.get('draft') is True:
            continue
        names = [s['name'] for s in t['sources']]
        assert not any('Not yet source-checked' in n for n in names), tid
        assert all(s['name'].strip() and s['used'].strip() for s in t['sources']), tid


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
        if tid in PINNED_FIGS:
            assert figs_now == PINNED_FIGS[tid], tid
        elif tid not in olds:
            assert figs_now == set(), tid
        elif t.get('draft') is True:
            assert figs_now == olds[tid], tid
        else:
            assert figs_now <= olds[tid], tid


def test_draft_topics_keep_placeholder_source_and_all_topics_validate():
    """Topics not yet source-checked keep the placeholder; every topic validates against the real link keys."""
    topics = list(new_topics().values())
    migrated = [t for t in topics if t['id'] in MIGRATED]
    assert len(migrated) == 15
    for t in migrated:
        assert t['category'] == REOPENED.get(t['id'], 'basics')
        if t.get('draft') is True and t['id'] not in REOPENED:
            assert t['reviewed'] == '2026-11-17'
            assert t['sources'] == [{'name': 'Not yet source-checked', 'used': 'Converted from v6 text; checked in Tasks 13 to 16'}]
    keys = {'p:' + os.path.splitext(os.path.basename(p))[0] for p in glob.glob(os.path.join(ROOT, 'src', 'protocols', '*.json'))}
    keys |= {'c:' + os.path.splitext(os.path.basename(p))[0] for p in glob.glob(os.path.join(ROOT, 'src', 'checklists', '*.json'))}
    keys |= {'u:' + n for n in TOOL_NAMES}   # survival tool keys, as build.py allows them
    keys |= {'s:' + t['id'] for t in topics}
    errors, _warnings = validate_topics(topics, set(figs.F), keys)
    assert errors == []


def test_converter_refuses_to_overwrite_topics_without_force(tmp_path):
    """tools/convert_survival.py would replace the source-checked topics with v6 drafts: it must refuse unless --force is given."""
    import shutil, subprocess
    for rel in ('tools/convert_survival.py', 'tests/fixtures/survival-v6.html'):
        os.makedirs(tmp_path / os.path.dirname(rel), exist_ok=True)
        shutil.copy(os.path.join(ROOT, rel), tmp_path / rel)
    shutil.copytree(os.path.join(ROOT, 'src', 'survival'), tmp_path / 'src' / 'survival')
    before = {p.name: p.read_bytes() for p in (tmp_path / 'src' / 'survival').iterdir()}
    r = subprocess.run([sys.executable, str(tmp_path / 'tools' / 'convert_survival.py')], capture_output=True, text=True)
    assert r.returncode != 0
    assert '--force' in r.stderr + r.stdout
    assert {p.name: p.read_bytes() for p in (tmp_path / 'src' / 'survival').iterdir()} == before
