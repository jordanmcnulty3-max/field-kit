"""Ballistics profiles: the stored shape, clean-on-load, the old 'Custom' becoming a real profile, and the FK.bal surface."""
import copy, json, os

from playwright.sync_api import expect

from .test_migration import FIX, V5_LS, backup_file, boot, ls, open_ballistics, pick, restore_now, stored_bal

V78 = {'id': 'u1k2j3x', 'name': 'My 6mm ARC', 'bc': 0.31, 'model': 'G7', 'w': 105, 'mv': 2850, 'sight': 1.9, 'zero': 100}
HOSTILE = {'id': 'u1', 'name': '<img src=x onerror=1>' + 'x' * 200, 'bc': '0.3', 'mv': 2700,
           'optic': {'type': 'reticle', 'unit': 'mil', 'marks': [3, 1, 2] + [9] * 500}}


def clean(page, raw):
    return page.evaluate('p => FK.bal.clean(p)', raw)


def screen(page):
    page.wait_for_selector('#dope tr')
    page.wait_for_timeout(450)    # the screen writes and recalculates on a 150 ms timer


def own(page):
    return page.evaluate("JSON.parse(localStorage.getItem('fk.profiles') || '[]')")


# ---------- Old data ----------

def test_v78_profile_loads_and_shows_every_unit(page, app_url):
    raw = json.dumps([V78])
    open_ballistics(page, app_url, stored_bal('u1k2j3x', '0.31', 'G7', '105', '2850', '1.9', '100'), extra={'fk.profiles': raw})
    got = page.evaluate('FK.bal.selected()')
    assert got == V78 and 'optic' not in got
    assert page.evaluate('FK.bal.profiles()') == [V78]
    assert ls(page, 'profiles') == raw                       # nothing is rewritten in storage
    assert page.input_value('#bProfile') == 'u1k2j3x'
    expect(page.locator('#bSight')).to_have_text('No sight set: showing every unit')
    assert len(page.inner_text('#solElev').split('\n')) == 4      # the label and the three lines: every unit


def test_custom_inputs_become_a_profile_named_custom(page, app_url):
    open_ballistics(page, app_url, stored_bal('custom', '0.4', 'G1', '150', '2800', '1.8', '200'))
    got = [p for p in page.evaluate('FK.bal.profiles()') if p['id'] == 'ucustom']
    assert got == [{'id': 'ucustom', 'name': 'Custom', 'bc': 0.4, 'model': 'G1', 'w': 150, 'mv': 2800, 'sight': 1.8, 'zero': 200}]
    assert page.evaluate('FK.bal.selected().id') == 'ucustom'
    assert page.input_value('#bProfile') == 'ucustom'
    assert json.loads(ls(page, 'bal'))['profile'] == 'ucustom'    # the next open must not make it again
    assert page.locator('#bProfile option[value="custom"]').count() == 0
    assert 'Custom (unsaved)' not in page.inner_text('#bProfile')


def test_custom_profile_is_made_once_and_keeps_later_edits(page, app_url):
    open_ballistics(page, app_url, stored_bal('custom', '0.4', 'G1', '150', '2800', '1.8', '200'))
    page.evaluate('FK.bal.save({ ...FK.bal.selected(), mv: 2900 })')
    screen(page)
    page.reload()
    page.wait_for_selector('#dope tr')
    assert page.evaluate('FK.bal.profiles().filter(p => p.id === "ucustom").map(p => p.mv)') == [2900]
    assert page.evaluate('FK.bal.selected().mv') == 2900


def test_custom_with_no_load_typed_selects_a_built_in(page, app_url):
    open_ballistics(page, app_url, stored_bal('custom', '', 'G7', '', '', '', ''))
    assert page.evaluate('FK.bal.profiles()') == []
    assert page.evaluate('FK.bal.selected().id') == 'p308' and page.input_value('#bProfile') == 'p308'
    assert page.evaluate('FK.bal.selected().mv') == 2600
    assert page.input_value('#bRange') == '600'                # the other inputs are restored


def test_selected_profile_missing_falls_back(page, app_url):
    open_ballistics(page, app_url, stored_bal('ugone', '0.4', 'G1', '150', '2800', '1.8', '200'))
    assert page.evaluate('FK.bal.selected().id') == 'p308' and page.input_value('#bProfile') == 'p308'
    assert page.input_value('#bWind') == '5'


# ---------- clean ----------

def test_clean_drops_bad_fields(page, app_url):
    boot(page, app_url)
    got = clean(page, HOSTILE)
    assert len(got['name']) == 60 and 'bc' not in got and got['mv'] == 2700 and 'optic' not in got


def test_clean_rejects_no_id(page, app_url):
    boot(page, app_url)
    for bad in ({'name': 'x'}, {'id': '', 'name': 'x'}, {'id': 'a b', 'name': 'x'}, {'id': 5, 'name': 'x'}, None, 'u1', [], 7,
                {'id': 'p308', 'name': 'Mine'}, {'id': 'p223', 'name': 'Mine'}):
        assert clean(page, bad) is None, bad


def test_clean_keeps_a_good_profile_and_drops_unknown_keys(page, app_url):
    boot(page, app_url)
    good = {**V78, 'optic': {'type': 'turret', 'unit': 'mil', 'click': 0.1}, 'mv0': 2800,
            'zeroAtm': {'temp': 59, 'alt': 500, 'press': 28.5, 'rh': 40}}
    assert clean(page, good) == good
    got = clean(page, {**good, 'extra': 1, 'optic': {**good['optic'], 'x': 1}, 'zeroAtm': {**good['zeroAtm'], 'x': 1}})
    assert got == good


def test_clean_numbers_models_and_names(page, app_url):
    boot(page, app_url)
    got = clean(page, {'id': 'u2', 'name': 'N', 'bc': None, 'model': 'G9', 'w': float('nan'), 'mv': True, 'sight': 'x', 'zero': 1e999})
    assert got == {'id': 'u2', 'name': 'N'}
    assert clean(page, {'id': 'u2', 'name': 7}) is None


def test_clean_optic_rules(page, app_url):
    boot(page, app_url)
    base = {'id': 'u3', 'name': 'O'}
    ok = [{'type': 'turret', 'unit': 'moa', 'click': c} for c in (0.1, 0.05, 0.25, 0.125, 0.5, 1)] + \
         [{'type': 'reticle', 'unit': 'iphy', 'marks': [1, 2, 3]}, {'type': 'dot'}]
    for o in ok:
        assert clean(page, {**base, 'optic': o})['optic'] == o, o
    bad = [{'type': 'turret', 'unit': 'mil', 'click': 0.3}, {'type': 'turret', 'unit': 'mil'}, {'type': 'turret', 'unit': 'rad', 'click': 0.1},
           {'type': 'scope', 'unit': 'mil', 'click': 0.1}, {'type': 'reticle', 'unit': 'mil', 'marks': [1, 1, 2]},
           {'type': 'reticle', 'unit': 'mil', 'marks': []}, {'type': 'reticle', 'unit': 'mil'}, 'turret', 5, [],
           {'type': 'turret', 'unit': 'toString', 'click': 0.1}, {'type': 'toString'}]
    for o in bad:
        assert 'optic' not in clean(page, {**base, 'optic': o}), o
    # one bad mark, or more than ten, drops the whole sight: nothing is renumbered or cut short
    for marks in (list(range(1, 30)), list(range(1, 12)), [1, 'a', 2, 3], [1, -2, 2], [1, None, 3], [0, 1, 2], [1, 2, float('inf')], [2, 1]):
        assert 'optic' not in clean(page, {**base, 'optic': {'type': 'reticle', 'unit': 'mil', 'marks': marks}}), marks
    got = clean(page, {**base, 'optic': {'type': 'reticle', 'unit': 'mil', 'marks': list(range(1, 11))}})
    assert got['optic']['marks'] == list(range(1, 11))     # ten is allowed


def test_clean_zero_conditions_and_mv0(page, app_url):
    boot(page, app_url)
    base = {'id': 'u4', 'name': 'Z'}
    assert clean(page, {**base, 'zeroAtm': {'temp': 40, 'alt': 100}})['zeroAtm'] == {'temp': 40, 'alt': 100, 'rh': 50}
    assert clean(page, {**base, 'zeroAtm': {'temp': 40, 'press': 29.9, 'rh': 'x'}})['zeroAtm'] == {'temp': 40, 'press': 29.9, 'rh': 50}
    for z in ({'alt': 100}, {'temp': 40}, {'temp': 40, 'alt': 'a', 'press': None}, {'temp': '40', 'alt': 1}, 'x', []):
        assert 'zeroAtm' not in clean(page, {**base, 'zeroAtm': z}), z
    assert clean(page, {**base, 'mv0': 2800})['mv0'] == 2800
    for v in (0, -5, '2800', None):
        assert 'mv0' not in clean(page, {**base, 'mv0': v}), v


# ---------- On screen ----------

def test_profile_name_is_escaped_on_screen(page, app_url):
    bad = {**HOSTILE, 'id': 'u1'}
    open_ballistics(page, app_url, stored_bal('u1', '0.3', 'G7', '150', '2700', '1.5', '100'), extra={'fk.profiles': json.dumps([bad])})
    shown = page.locator('#bProfile option:checked').inner_text()
    assert shown == bad['name'][:60] and shown.startswith('<img src=x')
    assert page.locator('img[src="x"]').count() == 0 and page.locator('#bProfile img').count() == 0


def test_restored_backup_profiles_pass_through_clean(page, app_url, tmp_path):
    boot(page, app_url)
    b = json.load(open(os.path.join(FIX, 'v5-backup.json')))
    mixed = json.loads(b['data']['fk.profiles']) + [HOSTILE, {'id': 'p308', 'name': 'Clash', 'mv': 1}, {'name': 'No id'}]
    b['data']['fk.profiles'] = json.dumps(mixed)
    pick(page, tmp_path, b)
    restore_now(page)
    got = page.evaluate('FK.bal.profiles()')
    assert [p['id'] for p in got] == ['u1k2j3x', 'u1']
    assert got[0]['name'] == 'My 6mm ARC' and got[1] == {'id': 'u1', 'name': HOSTILE['name'][:60], 'mv': 2700}


def test_picker_lists_my_profiles_then_starting_points_and_no_unsaved_entry(page, app_url):
    open_ballistics(page, app_url, stored_bal('p308', '0.25', 'G7', '175', '2600', '1.5', '100'), extra={'fk.profiles': json.dumps([V78])})
    groups = page.evaluate("[...document.querySelectorAll('#bProfile optgroup')].map(g => [g.label, g.children.length])")
    assert groups == [['My profiles', 1], ['Starting points', 6]]
    assert page.locator('#bProfile > option').count() == 0


# ---------- Saving, deleting ----------

def test_typing_on_the_main_screen_never_touches_the_profiles(page, app_url):
    open_ballistics(page, app_url, stored_bal('u1k2j3x', '0.31', 'G7', '105', '2850', '1.9', '100'), extra={'fk.profiles': json.dumps([V78])})
    raw = ls(page, 'profiles')
    page.fill('#bRange', '420')
    page.fill('#bWind', '3')
    screen(page)
    assert ls(page, 'profiles') == raw and page.evaluate('FK.bal.selected()') == V78
    assert json.loads(ls(page, 'bal'))['bRange'] == '420'


def test_save_as_new_profile_and_delete_land_on_the_right_profile(page, app_url):
    open_ballistics(page, app_url, stored_bal('p223', '0.188', 'G7', '77', '2720', '2.6', '100'))
    page.click('#bEdit')
    page.fill('#rfName', 'Range rifle')
    page.click('#rfSaveNew')
    expect(page.locator('#dlgRifle')).to_be_hidden()
    expect(page.locator('#bProfile option:checked')).to_have_text('Range rifle')
    got = page.evaluate('FK.bal.selected()')
    assert got['name'] == 'Range rifle' and got['mv'] == 2720 and got['id'] != 'p223'
    page.click('#bEdit')
    page.click('#rfDelete')
    page.click('#cfOk')
    expect(page.locator('#dlgRifle')).to_be_hidden()
    expect(page.locator('#dlgConfirm')).to_be_hidden()
    assert page.evaluate('FK.bal.profiles()') == []
    assert page.input_value('#bProfile') == 'p308' and page.evaluate('FK.bal.selected().mv') == 2600


def test_surface_save_select_remove(page, app_url):
    open_ballistics(page, app_url, stored_bal('p308', '0.25', 'G7', '175', '2600', '1.5', '100'))
    assert page.evaluate('Object.keys(FK.bal).sort()') == ['calc', 'clean', 'edit', 'init', 'profiles', 'remove', 'save', 'select', 'selected', 'shotAir']
    assert page.evaluate('FK.bal.save({ id: "p308", name: "x" })') is None
    saved = page.evaluate('FK.bal.save({ id: "u9", name: "Nine", bc: 0.3, mv: 2500, junk: 1, optic: { type: "dot" } })')
    assert saved == {'id': 'u9', 'name': 'Nine', 'bc': 0.3, 'mv': 2500, 'optic': {'type': 'dot'}}
    assert own(page) == [saved]
    assert page.locator('#bProfile option[value="u9"]').inner_text() == 'Nine'
    page.evaluate('FK.bal.select("u9")')
    assert page.input_value('#bProfile') == 'u9' and page.evaluate('FK.bal.selected().mv') == 2500
    assert json.loads(ls(page, 'bal'))['profile'] == 'u9'
    page.evaluate('FK.bal.save({ id: "u9", name: "Nine again", mv: 2400 })')      # replace by id, in place
    assert [p['name'] for p in page.evaluate('FK.bal.profiles()')] == ['Nine again']
    assert page.evaluate('FK.bal.selected().mv') == 2400     # the selected profile follows the save
    copy_ = page.evaluate('FK.bal.selected()')
    copy_['name'] = 'mutated'
    assert page.evaluate('FK.bal.selected().name') == 'Nine again'
    page.evaluate('FK.bal.select("nope")')
    assert page.evaluate('FK.bal.selected().id') == 'u9'
    page.evaluate('FK.bal.remove("p308")')                  # a built-in load cannot be removed
    assert page.evaluate('FK.bal.selected().id') == 'u9' and page.locator('#bProfile option[value="p308"]').count() == 1
    page.evaluate('FK.bal.remove("u9")')
    assert page.evaluate('FK.bal.selected().id') == 'p308' and own(page) == []


def test_a_failed_profile_save_says_so_and_changes_nothing(page, app_url):
    open_ballistics(page, app_url, stored_bal('u1k2j3x', '0.31', 'G7', '105', '2850', '1.9', '100'), extra={'fk.profiles': json.dumps([V78])})
    page.evaluate("""() => { const o = Storage.prototype.setItem;
      Storage.prototype.setItem = function (k, v) { if (k === 'fk.profiles') throw new DOMException('full', 'QuotaExceededError'); return o.call(this, k, v); }; }""")
    got = page.evaluate('FK.bal.save({ id: "u7", name: "Seven", mv: 2500 })')
    assert got is None
    expect(page.locator('#toast')).to_contain_text('storage for Field Kit is full')
    assert [p['id'] for p in page.evaluate('FK.bal.profiles()')] == ['u1k2j3x']
    page.evaluate('FK.bal.remove("u1k2j3x")')
    assert [p['id'] for p in page.evaluate('FK.bal.profiles()')] == ['u1k2j3x']


# ---------- The stored screen state holds the selected profile's id and the shot, never the load ----------

LOAD_KEYS = ['bBC', 'bModel', 'bW', 'bMV', 'bSH', 'bZero']


def stored_state(page):
    s = json.loads(ls(page, 'bal'))
    assert not [k for k in LOAD_KEYS if k in s], s       # the load lives in the profile only
    return s['profile']


def test_stored_screen_state_follows_a_picker_change_to_a_built_in(page, app_url):
    open_ballistics(page, app_url, stored_bal('p308', '0.25', 'G7', '175', '2600', '1.5', '100'))
    page.select_option('#bProfile', 'p223')
    assert stored_state(page) == 'p223'


def test_stored_screen_state_follows_select_of_an_own_profile_and_remove(page, app_url):
    open_ballistics(page, app_url, stored_bal('p308', '0.25', 'G7', '175', '2600', '1.5', '100'), extra={'fk.profiles': json.dumps([V78])})
    page.evaluate('FK.bal.select("u1k2j3x")')
    assert stored_state(page) == 'u1k2j3x'
    page.evaluate('FK.bal.remove("u1k2j3x")')
    assert stored_state(page) == 'p308'


def test_stored_screen_state_after_save_as_new(page, app_url):
    open_ballistics(page, app_url, stored_bal('p223', '0.188', 'G7', '77', '2720', '2.6', '100'))
    page.click('#bEdit')
    page.fill('#rfName', 'Mine')
    page.click('#rfSaveNew')
    expect(page.locator('#bProfile option:checked')).to_have_text('Mine')
    assert stored_state(page) == page.evaluate('FK.bal.selected().id') != 'p223'
    assert page.evaluate('FK.bal.selected().mv') == 2720


def test_opening_with_a_stale_built_in_shows_the_current_numbers_and_drops_the_old_load_keys(page, app_url):
    open_ballistics(page, app_url, stored_bal('p308', '0.243', 'G7', '175', '2500', '1.5', '100'))
    assert stored_state(page) == 'p308'
    assert page.evaluate('FK.bal.selected()') == page.evaluate('FK._test.presets().find(p => p.id === "p308")')
    assert page.evaluate('FK.bal.selected().mv') == 2600


def test_a_failed_profile_write_leaves_custom_stored_so_the_migration_is_retried(page, app_url):
    page.add_init_script("""(() => { const o = Storage.prototype.setItem;
      Storage.prototype.setItem = function (k, v) { if (k === 'fk.profiles' && sessionStorage.getItem('failProfiles')) throw new DOMException('full', 'QuotaExceededError'); return o.call(this, k, v); }; })()""")
    page.add_init_script("if (!sessionStorage.getItem('seeded')) sessionStorage.setItem('failProfiles', '1')")
    open_ballistics(page, app_url, stored_bal('custom', '0.4', 'G1', '150', '2800', '1.8', '200'))
    s = json.loads(ls(page, 'bal'))
    assert s['profile'] == 'custom' and [s[k] for k in LOAD_KEYS] == ['0.4', 'G1', '150', '2800', '1.8', '200']     # left as it was
    assert ls(page, 'profiles') is None
    page.evaluate("sessionStorage.removeItem('failProfiles')")
    page.reload()
    page.wait_for_selector('#dope tr')
    assert page.evaluate('FK.bal.profiles()') == [{'id': 'ucustom', 'name': 'Custom', 'bc': 0.4, 'model': 'G1', 'w': 150, 'mv': 2800, 'sight': 1.8, 'zero': 200}]
    assert stored_state(page) == 'ucustom'


# ---------- Ranges a real rifle and real air can have ----------

def test_clean_keeps_pressure_only_between_8_and_33_inhg(page, app_url):
    boot(page, app_url)
    base = {'id': 'u5', 'name': 'P'}
    for press in (8, 29.92, 33):
        assert clean(page, {**base, 'zeroAtm': {'temp': 40, 'press': press}})['zeroAtm'] == {'temp': 40, 'press': press, 'rh': 50}
    for press in (2.992, 0.1, 7.99, 33.01, 299.2):
        assert 'zeroAtm' not in clean(page, {**base, 'zeroAtm': {'temp': 40, 'press': press}}), press
        assert clean(page, {**base, 'zeroAtm': {'temp': 40, 'alt': 300, 'press': press}})['zeroAtm'] == {'temp': 40, 'alt': 300, 'rh': 50}


def test_a_stored_profile_outside_the_plausible_ranges_is_kept_and_asks_for_an_edit(page, app_url):
    from .test_bal_screen import open_screen
    ok = {'id': 'u6', 'name': 'Odd', 'bc': 0.3, 'model': 'G7', 'w': 150, 'mv': 2700, 'sight': 1.5, 'zero': 100}
    ask = 'This profile needs a ballistic coefficient, a velocity and a zero range. Tap Edit.'
    for bad in ({'bc': 0.00001}, {'bc': 5}, {'w': 1e308}, {'w': 0.5}, {'mv': 99999}, {'mv': 299}, {'zero': 0.001}, {'zero': 2000}, {'sight': 30}, {'sight': -1}):
        p = {**ok, **bad}
        open_screen(page, app_url, profile='u6', profiles=[p])
        assert page.evaluate('FK.bal.selected()') == p, bad
        assert page.inner_text('#solSub') == ask, bad
        assert page.locator('#dope tbody tr').count() == 0
    for edge in ({'bc': 0.05}, {'bc': 1.2}, {'w': 0}, {'w': 1}, {'w': 1000}, {'mv': 300}, {'mv': 5000}, {'zero': 5}, {'zero': 1000}, {'sight': 0}, {'sight': 6}):
        open_screen(page, app_url, profile='u6', profiles=[{**ok, **edge}])
        assert page.inner_text('#solSub') != ask, edge


def test_an_unknown_stored_wind_clock_or_card_step_falls_back_to_the_default(page, app_url):
    from .test_bal_screen import open_screen
    for clock, step in (('13', '30'), ('0', 'x'), ('', '')):
        open_screen(page, app_url, shot={'bClock': clock, 'bStep': step, 'bWind': '10'})
        assert page.input_value('#bClock') == '3' and page.input_value('#bStep') == '50', (clock, step)
        assert page.inner_text('#solWind').split('\n')[1].startswith('R '), clock     # a crosswind from the right, not a head wind


# ---------- Twist and bullet fields (Ballistics release 2) ----------

SPIN_KEYS = ['twist', 'twistDir', 'blen', 'bdia']
V711 = {'id': 'u711', 'name': 'Seven eleven', 'bc': 0.31, 'model': 'G7', 'w': 105, 'mv': 2850, 'sight': 1.9, 'zero': 100,
        'optic': {'type': 'turret', 'unit': 'mil', 'click': 0.1}, 'zeroAtm': {'temp': 59, 'alt': 500, 'rh': 50}, 'mv0': 2900}
SPIN_BASE = {'id': 'u8', 'name': 'Spin', 'bc': 0.3, 'model': 'G7', 'w': 175, 'mv': 2600, 'sight': 1.5, 'zero': 100}


def test_v711_profiles_load_unchanged_and_gain_no_fields(page, app_url):
    raw = json.dumps([V78, V711])
    open_ballistics(page, app_url, stored_bal('u711', '0.31', 'G7', '105', '2850', '1.9', '100'), extra={'fk.profiles': raw})
    assert page.evaluate('FK.bal.profiles()') == [V78, V711]
    assert [k for p in page.evaluate('FK.bal.profiles()') for k in SPIN_KEYS if k in p] == []
    assert ls(page, 'profiles') == raw                       # nothing is rewritten in storage
    assert list(page.evaluate('FK.bal.selected()')) == list(V711)     # and the key order is what v7.11 wrote


def test_bad_spin_fields_are_dropped_one_by_one(page, app_url):
    boot(page, app_url)
    got = clean(page, {**SPIN_BASE, 'twist': '8', 'twistDir': '<b>', 'blen': -1, 'bdia': 0.308})
    assert got == {**SPIN_BASE, 'bdia': 0.308}              # the name and the load are intact
    for bad in ({'twist': 2}, {'twist': 31}, {'twist': None}, {'twist': True}, {'twist': float('inf')}, {'twist': [8]},
                {'blen': 0.19}, {'blen': 3.01}, {'blen': 0}, {'blen': '1.2'},
                {'bdia': 0.16}, {'bdia': 0.61}, {'bdia': '0.308'}, {'bdia': -0.308},
                {'twistDir': 'R'}, {'twistDir': 'l'}, {'twistDir': 'Left'}, {'twistDir': '<img src=x>'}, {'twistDir': 1}, {'twistDir': ['L']}):
        got = clean(page, {**SPIN_BASE, **bad})
        assert got == SPIN_BASE, bad
    only = clean(page, {**SPIN_BASE, 'twist': 8, 'twistDir': '<b>', 'blen': '1.2', 'bdia': 5})
    assert only == {**SPIN_BASE, 'twist': 8}


def test_good_spin_fields_are_kept_and_independent(page, app_url):
    boot(page, app_url)
    full = {**SPIN_BASE, 'twist': 8, 'twistDir': 'L', 'blen': 1.24, 'bdia': 0.308}
    assert clean(page, full) == full
    for k in SPIN_KEYS:
        got = clean(page, {**SPIN_BASE, k: full[k]})
        assert got == {**SPIN_BASE, k: full[k]}, k
    for k, edge in (('twist', 3), ('twist', 30), ('blen', 0.2), ('blen', 3), ('bdia', 0.17), ('bdia', 0.6)):
        assert clean(page, {**SPIN_BASE, k: edge})[k] == edge, (k, edge)
    assert page.evaluate('FK.balHost.RANGE.twist') == [3, 30]
    assert page.evaluate('FK.balHost.RANGE.blen') == [0.2, 3]
    assert page.evaluate('FK.balHost.RANGE.bdia') == [0.17, 0.6]


def test_length_outside_2_to_7_calibers_is_dropped(page, app_url):
    boot(page, app_url)
    for blen in (0.3, 0.6, 2.2, 3):                          # under 2 and over 7 calibers of .308
        assert 'blen' not in clean(page, {**SPIN_BASE, 'blen': blen, 'bdia': 0.308}), blen
        assert clean(page, {**SPIN_BASE, 'blen': blen, 'bdia': 0.308})['bdia'] == 0.308
    for blen in (0.616, 1.0, 1.24, 2.156):                   # 2.0 and 7.0 calibers are allowed
        assert clean(page, {**SPIN_BASE, 'blen': blen, 'bdia': 0.308})['blen'] == blen, blen
    assert clean(page, {**SPIN_BASE, 'blen': 0.3})['blen'] == 0.3           # the rule needs both
    assert clean(page, {**SPIN_BASE, 'blen': 0.3, 'bdia': 5})['blen'] == 0.3    # a diameter that is itself dropped decides nothing


def test_builtin_loads_carry_none_of_the_spin_fields(page, app_url):
    boot(page, app_url)
    presets = page.evaluate('FK._test.presets()')
    assert len(presets) == 6
    for p in presets:
        assert [k for k in SPIN_KEYS if k in p] == [], p['id']


def test_stored_order_puts_the_spin_fields_after_mv0(page, app_url):
    open_ballistics(page, app_url, stored_bal('p308', '0.25', 'G7', '175', '2600', '1.5', '100'))
    page.evaluate('p => FK.bal.save(p)', {'bdia': 0.308, 'twistDir': 'L', 'blen': 1.24, 'twist': 10, 'mv0': 2650, **SPIN_BASE})
    assert list(own(page)[0]) == ['id', 'name', 'bc', 'model', 'w', 'mv', 'sight', 'zero', 'mv0', 'twist', 'twistDir', 'blen', 'bdia']


def test_default_card_is_unchanged(page, app_url):
    from .test_tactical_layout import ballistics, pinned
    ballistics(page, app_url)
    assert pinned(page, 'default_mil', 'mil') == 'left'
    assert pinned(page, 'default_moa', 'moa') == 'left'


def test_spin_fields_change_only_the_windage_on_the_card(page, app_url):
    """Task 2 stored the fields and the card ignored them; since Task 3 spin drift reaches the windage and the drift words and nothing
    else. Everything spin cannot change is compared exactly: all of #solution but the windage column and the drift clause of the
    sentence (so the elevation column, the sentence's other words, Show all units and the card's state), and every dope column but
    the two wind columns and Drift (Yd, both Elev columns, Path, fps, ft-lb, Time)."""
    from .test_bal_screen import open_screen
    plain = {**SPIN_BASE}
    grab = lambda: page.evaluate("""() => {
      const card = document.querySelector('#solution').cloneNode(true);
      card.querySelector('#solWind').remove();
      const sub = card.querySelector('#solSub');
      sub.textContent = sub.textContent.replace(/drift \\d+\\.\\d in(?: left| right)?(?: \\(spin drift \\d+\\.\\d in (?:left|right) included\\))?, /, '');
      return { card: card.innerText, cls: card.className, all: document.querySelector('#bAll').outerHTML,
        wind: document.querySelector('#solWind').innerText, sub: document.querySelector('#solSub').innerText,
        head: [...document.querySelectorAll('#dope th')].map(c => c.textContent),
        rows: [...document.querySelectorAll('#dope tbody tr')].map(r => [...r.children].map(c => c.textContent)) } }""")
    open_screen(page, app_url, profile='u8', profiles=[plain])
    before = grab()
    open_screen(page, app_url, profile='u8', profiles=[{**plain, 'twist': 8, 'twistDir': 'L', 'blen': 1.24, 'bdia': 0.308}])
    after = grab()
    assert before['head'] == after['head'] == ['Yd', 'Elev mil', 'Elev MOA', 'Wind mil', 'Wind MOA', 'Path in', 'Drift in', 'fps', 'ft-lb', 'Time s']
    assert 'drift' not in before['card'].split('\n')[-1] and before['card'] == after['card'] and before['cls'] == after['cls'] and before['all'] == after['all']
    assert after['wind'] != before['wind'] and 'spin drift' in after['sub'] and 'spin drift' not in before['sub']
    keep = lambda rows: [r[:3] + r[5:6] + r[7:] for r in rows]
    assert keep(after['rows']) == keep(before['rows']) and len(after['rows']) > 10
    assert [r[3:5] + r[6:7] for r in after['rows']] != [r[3:5] + r[6:7] for r in before['rows']]
