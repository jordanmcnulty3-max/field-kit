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
    assert page.input_value('#bProfile') == 'u1k2j3x' and page.input_value('#bMV') == '2850'


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
    page.fill('#bMV', '2900')
    screen(page)
    page.reload()
    page.wait_for_selector('#dope tr')
    assert page.evaluate('FK.bal.profiles().filter(p => p.id === "ucustom").map(p => p.mv)') == [2900]
    assert page.input_value('#bMV') == '2900'


def test_custom_with_no_load_typed_selects_a_built_in(page, app_url):
    open_ballistics(page, app_url, stored_bal('custom', '', 'G7', '', '', '', ''))
    assert page.evaluate('FK.bal.profiles()') == []
    assert page.evaluate('FK.bal.selected().id') == 'p308' and page.input_value('#bProfile') == 'p308'
    assert page.input_value('#bMV') == '2600'
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
    got = clean(page, {**base, 'optic': {'type': 'reticle', 'unit': 'mil', 'marks': list(range(1, 30))}})
    assert got['optic']['marks'] == list(range(1, 11))     # at most ten
    got = clean(page, {**base, 'optic': {'type': 'reticle', 'unit': 'mil', 'marks': [1, 'a', -2, 2, None, 3]}})
    assert got['optic']['marks'] == [1, 2, 3]              # only finite positive numbers count


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


# ---------- Typing, saving, deleting ----------

def test_typing_in_a_built_in_load_makes_custom_and_selects_it(page, app_url):
    open_ballistics(page, app_url, stored_bal('p308', '0.25', 'G7', '175', '2600', '1.5', '100'))
    page.fill('#bMV', '2650')
    assert page.input_value('#bProfile') == 'ucustom'
    screen(page)
    assert page.evaluate('FK.bal.profiles()') == [{'id': 'ucustom', 'name': 'Custom', 'bc': 0.25, 'model': 'G7', 'w': 175, 'mv': 2650, 'sight': 1.5, 'zero': 100}]
    assert page.evaluate('FK.bal.selected().id') == 'ucustom'
    expect(page.locator('#bDel')).to_be_visible()
    page.select_option('#bProfile', 'p223')
    page.fill('#bBC', '0.2')                                 # a second time overwrites it
    screen(page)
    got = page.evaluate('FK.bal.profiles()')
    assert len(got) == 1 and got[0]['bc'] == 0.2 and got[0]['mv'] == 2720 and got[0]['w'] == 77


def test_typing_in_an_own_load_writes_that_profile(page, app_url):
    open_ballistics(page, app_url, stored_bal('u1k2j3x', '0.31', 'G7', '105', '2850', '1.9', '100'), extra={'fk.profiles': json.dumps([V78])})
    page.fill('#bMV', '2900')
    assert page.input_value('#bProfile') == 'u1k2j3x'
    screen(page)
    assert own(page) == [{**V78, 'mv': 2900}]
    page.fill('#bW', '')                                     # a cleared field does not store zero
    screen(page)
    assert own(page)[0]['w'] == 105


def test_save_as_new_profile_and_delete_land_on_the_right_profile(page, app_url):
    open_ballistics(page, app_url, stored_bal('p223', '0.188', 'G7', '77', '2720', '2.6', '100'))
    page.click('#bSave')
    page.fill('#askInput', 'Range rifle')
    page.click('#askOk')
    expect(page.locator('#bProfile option:checked')).to_have_text('Range rifle')
    got = page.evaluate('FK.bal.selected()')
    assert got['name'] == 'Range rifle' and got['mv'] == 2720 and got['id'] != 'p223'
    page.click('#bDel')
    page.click('#cfOk')
    expect(page.locator('#dlgConfirm')).to_be_hidden()
    assert page.evaluate('FK.bal.profiles()') == []
    assert page.input_value('#bProfile') == 'p308' and page.input_value('#bMV') == '2600'
    expect(page.locator('#bDel')).to_be_hidden()


def test_surface_save_select_remove(page, app_url):
    open_ballistics(page, app_url, stored_bal('p308', '0.25', 'G7', '175', '2600', '1.5', '100'))
    assert page.evaluate('Object.keys(FK.bal).sort()') == ['calc', 'clean', 'init', 'profiles', 'remove', 'save', 'select', 'selected']
    assert page.evaluate('FK.bal.save({ id: "p308", name: "x" })') is None
    saved = page.evaluate('FK.bal.save({ id: "u9", name: "Nine", bc: 0.3, mv: 2500, junk: 1, optic: { type: "dot" } })')
    assert saved == {'id': 'u9', 'name': 'Nine', 'bc': 0.3, 'mv': 2500, 'optic': {'type': 'dot'}}
    assert own(page) == [saved]
    assert page.locator('#bProfile option[value="u9"]').inner_text() == 'Nine'
    page.evaluate('FK.bal.select("u9")')
    assert page.input_value('#bProfile') == 'u9' and page.input_value('#bMV') == '2500'
    assert json.loads(ls(page, 'bal'))['profile'] == 'u9'
    page.evaluate('FK.bal.save({ id: "u9", name: "Nine again", mv: 2400 })')      # replace by id, in place
    assert [p['name'] for p in page.evaluate('FK.bal.profiles()')] == ['Nine again']
    assert page.input_value('#bMV') == '2400'                # the selected profile's fields follow it
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
