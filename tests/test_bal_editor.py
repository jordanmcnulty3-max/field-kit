"""The rifle profile editor: load, the sight on it, and the conditions it was zeroed in."""
import json

import pytest
from playwright.sync_api import expect

from .test_tactical_layout import ballistics, enlarge_text, overflow, too_small, clipped_buttons

OWN = {'id': 'u1', 'name': 'Mine', 'bc': 0.3, 'model': 'G1', 'w': 150, 'mv': 2800, 'sight': 1.5, 'zero': 100}
RET = {**OWN, 'id': 'u2', 'name': 'Reticle', 'optic': {'type': 'reticle', 'unit': 'mil', 'marks': [1.5, 3, 4.6]}}
DLG = '#dlgRifle'


def open_editor(page, app_url, profiles=(OWN,), select='u1'):
    ballistics(page, app_url, profiles=list(profiles))
    if select:
        page.evaluate('id => FK.bal.select(id)', select)
    page.click('#bEdit')
    expect(page.locator(DLG)).to_be_visible()
    page.wait_for_timeout(250)    # the sheet's own slide-in


def profiles(page):
    return page.evaluate('FK.bal.profiles()')


def msg(page):
    return page.inner_text('#rfMsg')


def refuse(page, text, focus):
    page.click('#rfSave')
    expect(page.locator('#rfMsg')).to_have_text(text)
    expect(page.locator(DLG)).to_be_visible()
    assert page.evaluate('document.activeElement.id') == focus


def test_edit_button_sits_in_the_profile_row(page, app_url):
    ballistics(page, app_url, profiles=[OWN])
    assert page.evaluate("document.querySelector('#bEdit').parentElement === document.querySelector('#bProfile').parentElement")
    expect(page.locator('#bEdit')).to_have_text('Edit')
    assert page.evaluate('Object.keys(FK.bal).includes("edit")')


def test_editor_opens_with_the_profile_and_the_fixed_copy(page, app_url):
    open_editor(page, app_url, profiles=(OWN, RET), select='u2')
    expect(page.locator('#rfTitle')).to_have_text('Edit profile')
    assert page.input_value('#rfName') == 'Reticle' and page.input_value('#rfBC') == '0.3'
    assert page.input_value('#rfOptic') == 'reticle' and page.input_value('#rfUnit') == 'mil'
    assert page.input_value('#rfMarks') == '1.5, 3, 4.6'
    text = page.text_content(DLG)
    for s in ['Rifle and load', 'Sight', 'Zero conditions', 'Name', 'Ballistic coefficient', 'Drag model', 'Bullet weight (gr)',
              'Muzzle velocity (fps)', 'Sight height (in)', 'Zero range (yd)', 'Unit', 'Marks', 'Temperature (°F)', 'Altitude (ft)',
              'Station pressure (inHg)', 'Measure velocity near the temperature you\'ll shoot in.',
              'Some scopes sold as MOA move 1 inch per 100 yd. Check the manual.',
              'Type each mark\'s distance below the centre, from your scope\'s manual. If the manual gives only yardages, this isn\'t supported yet.',
              'If the reticle doesn\'t grow with magnification, the marks are true at one magnification only. The manual says which.',
              'Zero conditions not set: assumed the same as today.']:
        assert s in text, s
    assert page.locator('#rfOptic option').all_inner_texts() == [
        'Not set', 'Scope with turrets', 'Drop reticle (low-power scope)', 'Red dot or iron sights']
    assert page.locator('#rfUnit option').all_inner_texts() == ['Mil', 'MOA (1.047 in at 100 yd)', 'Inches per 100 yd']
    assert page.evaluate('document.querySelector("#rfMsg").getAttribute("aria-live")') == 'polite'
    assert page.evaluate('document.activeElement.id') == 'rfTitle'    # no keyboard pops up


def test_edit_own_profile_saves_in_place(page, app_url):
    open_editor(page, app_url)
    page.fill('#rfBC', '0.35')
    page.click('#rfSave')
    expect(page.locator(DLG)).to_be_hidden()
    got = profiles(page)
    assert [p['id'] for p in got] == ['u1'] and got[0]['bc'] == 0.35 and got[0]['name'] == 'Mine'
    assert page.evaluate('FK.bal.selected().id') == 'u1'
    assert page.evaluate('FK.bal.selected().bc') == 0.35        # the main screen's profile holds the saved numbers


def test_save_as_new_makes_a_new_profile_and_selects_it(page, app_url):
    open_editor(page, app_url)
    page.fill('#rfName', 'Mine, hot load')
    page.fill('#rfMV', '2900')
    page.click('#rfSaveNew')
    expect(page.locator(DLG)).to_be_hidden()
    got = profiles(page)
    assert len(got) == 2 and got[0] == OWN
    assert got[1]['name'] == 'Mine, hot load' and got[1]['mv'] == 2900 and got[1]['id'] != 'u1'
    assert page.evaluate('FK.bal.selected().id') == got[1]['id']
    assert page.evaluate('FK.bal.selected().mv') == 2900


def test_built_in_load_offers_save_as_new_only(page, app_url):
    open_editor(page, app_url, select='p308')
    expect(page.locator('#rfTitle')).to_have_text('Built-in load')
    expect(page.locator('#rfSave')).to_be_hidden()
    expect(page.locator('#rfDelete')).to_be_hidden()
    expect(page.locator('#rfSaveNew')).to_be_visible()
    expect(page.locator('#rfCancel')).to_be_visible()
    assert 'This is a built-in load. Change what you need, then save it as a new profile.' in page.text_content(DLG)
    assert "can't be changed" not in page.text_content(DLG)
    before = page.evaluate('FK.bal.selected()')
    page.fill('#rfMV', '2700')
    page.press('#rfMV', 'Enter')                      # Enter must not save over a built-in load
    expect(page.locator(DLG)).to_be_visible()
    page.click('#rfSaveNew')
    expect(page.locator(DLG)).to_be_hidden()
    assert profiles(page)[-1]['mv'] == 2700 and profiles(page)[-1]['id'] != 'p308'
    assert [p for p in page.evaluate('FK._test.presets()') if p['id'] == 'p308'][0] == before


def test_turret_fields_show_only_for_turrets(page, app_url):
    open_editor(page, app_url)
    vis = lambda i: page.locator('#' + i).is_visible()
    for kind, want in [('none', (0, 0, 0)), ('turret', (1, 1, 0)), ('reticle', (1, 0, 1)), ('dot', (0, 0, 0))]:
        page.select_option('#rfOptic', kind)
        assert (vis('rfUnit'), vis('rfClick'), vis('rfMarks')) == tuple(bool(x) for x in want), kind


def test_click_choices_follow_the_unit(page, app_url):
    open_editor(page, app_url)
    page.select_option('#rfOptic', 'turret')
    opts = lambda: [(o.get_attribute('value'), o.inner_text()) for o in page.locator('#rfClick option').all()]
    page.select_option('#rfUnit', 'mil')
    assert opts() == [('0.1', '0.1 mil'), ('0.05', '0.05 mil')]
    for u in ('moa', 'iphy'):
        page.select_option('#rfUnit', u)
        w = 'MOA' if u == 'moa' else 'in'
        assert opts() == [('0.25', '1/4 ' + w), ('0.125', '1/8 ' + w), ('0.5', '1/2 ' + w), ('1', '1 ' + w)]
    page.select_option('#rfClick', '0.5')
    page.select_option('#rfUnit', 'mil')              # changing the unit resets the click
    assert page.input_value('#rfClick') == '0.1'
    page.click('#rfSave')
    assert profiles(page)[0]['optic'] == {'type': 'turret', 'unit': 'mil', 'click': 0.1}


def reticle(page, marks):
    page.select_option('#rfOptic', 'reticle')
    page.select_option('#rfUnit', 'mil')
    page.fill('#rfMarks', marks)


def test_marks_parse_and_refuse(page, app_url):
    open_editor(page, app_url)
    reticle(page, '3 1.5')
    refuse(page, 'Marks must get larger down the list.', 'rfMarks')
    page.fill('#rfMarks', 'abc')
    refuse(page, 'Marks must be numbers, like 1.5, 3, 4.6.', 'rfMarks')
    page.fill('#rfMarks', '1.5, -3')
    refuse(page, 'Marks must be more than 0.', 'rfMarks')       # a number not above 0 is named as such (it read 'Marks must be numbers')
    page.fill('#rfMarks', ' '.join(str(i) for i in range(1, 12)))
    refuse(page, 'Up to 10 marks.', 'rfMarks')
    assert 'optic' not in profiles(page)[0]
    page.fill('#rfMarks', '1.5, 3 4.6')
    page.click('#rfSave')
    assert profiles(page)[0]['optic'] == {'type': 'reticle', 'unit': 'mil', 'marks': [1.5, 3, 4.6]}
    page.click('#bEdit')
    page.fill('#rfMarks', '1.5,,3')
    page.click('#rfSave')
    assert profiles(page)[0]['optic']['marks'] == [1.5, 3]
    page.click('#bEdit')
    page.fill('#rfMarks', '')
    refuse(page, 'A reticle needs at least one mark.', 'rfMarks')


def test_dot_and_none_save_the_right_sight(page, app_url):
    open_editor(page, app_url, profiles=(RET,), select='u2')
    page.select_option('#rfOptic', 'dot')
    page.click('#rfSave')
    assert profiles(page)[0]['optic'] == {'type': 'dot'}
    page.click('#bEdit')
    page.select_option('#rfOptic', 'none')
    page.click('#rfSave')
    assert 'optic' not in profiles(page)[0]


def test_zero_conditions_optional(page, app_url):
    open_editor(page, app_url)
    expect(page.locator('#rfZHint')).to_be_visible()
    page.click('#rfSave')
    assert 'zeroAtm' not in profiles(page)[0]
    page.click('#bEdit')
    page.fill('#rfZTemp', '40')
    expect(page.locator('#rfZHint')).to_be_hidden()
    refuse(page, 'Zero conditions need a temperature and an altitude or a pressure.', 'rfZAlt')
    page.fill('#rfZTemp', '')
    page.fill('#rfZAlt', '800')
    refuse(page, 'Zero conditions need a temperature and an altitude or a pressure.', 'rfZTemp')
    page.fill('#rfZTemp', '40')
    page.click('#rfSave')
    assert profiles(page)[0]['zeroAtm'] == {'temp': 40, 'alt': 800, 'rh': 50}
    page.click('#bEdit')
    assert (page.input_value('#rfZTemp'), page.input_value('#rfZAlt'), page.input_value('#rfZPress')) == ('40', '800', '')
    page.fill('#rfZAlt', '')
    page.fill('#rfZPress', '29.1')
    page.click('#rfSave')
    assert profiles(page)[0]['zeroAtm'] == {'temp': 40, 'press': 29.1, 'rh': 50}


def test_required_fields(page, app_url):
    open_editor(page, app_url)
    before = profiles(page)
    for field, text in [('rfName', 'Give the profile a name.'), ('rfBC', 'Ballistic coefficient must be between 0.05 and 1.2.'),
                        ('rfMV', 'Muzzle velocity must be between 300 and 5,000 fps.'), ('rfZero', 'Zero range must be between 5 and 1,000 yd.')]:
        old = page.input_value('#' + field)
        page.fill('#' + field, '   ' if field == 'rfName' else '')
        refuse(page, text, field)
        page.fill('#' + field, '0' if field != 'rfName' else '')
        refuse(page, text, field)
        page.fill('#' + field, old)
    assert profiles(page) == before
    # sight height and weight may be blank
    page.fill('#rfSH', '')
    page.fill('#rfW', '')
    page.fill('#rfName', 'Blank weight')            # a copy needs its own name
    page.click('#rfSaveNew')
    expect(page.locator(DLG)).to_be_hidden()
    got = profiles(page)[-1]
    assert got['sight'] == 0 and got['w'] == 0


def test_refusal_message_clears_when_it_is_fixed(page, app_url):
    open_editor(page, app_url)
    page.fill('#rfBC', '')
    refuse(page, 'Ballistic coefficient must be between 0.05 and 1.2.', 'rfBC')
    page.fill('#rfBC', '0.3')
    page.click('#rfSave')
    expect(page.locator(DLG)).to_be_hidden()


def test_back_with_unsaved_typing_asks(page, app_url):
    open_editor(page, app_url)
    page.evaluate("const g = history.go.bind(history); history.go = k => { setTimeout(() => g(k), 250); }; 0")   # a slow phone
    page.fill('#rfName', 'Changed')
    page.go_back()
    expect(page.locator('#cfTitle')).to_have_text('Discard changes to this profile?')
    expect(page.locator('#cfText')).to_have_text('What you typed is not kept.')
    page.click('#cfCancel')                                 # Keep editing
    expect(page.locator('#cfOk')).to_be_hidden()
    expect(page.locator(DLG)).to_be_visible()
    assert page.input_value('#rfName') == 'Changed'
    page.go_back()
    page.click('#cfOk')                                     # Discard
    expect(page.locator(DLG)).to_be_hidden()
    assert profiles(page) == [OWN]
    page.wait_for_timeout(600)
    assert page.evaluate('FK.view()') == 'ballistics'


def test_back_without_typing_closes_and_cancel_asks_like_back(page, app_url):
    """Cancel asks Keep editing / Discard when something was changed, exactly as Back does (it asked nothing before)."""
    open_editor(page, app_url)
    page.go_back()
    expect(page.locator(DLG)).to_be_hidden()
    page.wait_for_timeout(400)    # a tap on the same spot straight after a sheet closes is swallowed (double-tap guard)
    page.click('#bEdit')
    page.evaluate("const g = history.go.bind(history); history.go = k => { setTimeout(() => g(k), 250); }; 0")   # a slow phone
    page.fill('#rfName', 'Changed')
    page.click('#rfCancel')
    expect(page.locator('#cfTitle')).to_have_text('Discard changes to this profile?')
    expect(page.locator('#cfText')).to_have_text('What you typed is not kept.')
    page.click('#cfCancel')                                 # Keep editing
    expect(page.locator('#dlgConfirm')).to_be_hidden()
    page.wait_for_timeout(400)
    expect(page.locator(DLG)).to_be_visible()
    assert page.input_value('#rfName') == 'Changed'
    page.click('#rfCancel')
    page.click('#cfOk')                                     # Discard
    expect(page.locator(DLG)).to_be_hidden()
    expect(page.locator('#dlgConfirm')).to_be_hidden()
    assert profiles(page) == [OWN]
    page.wait_for_timeout(800)
    assert page.evaluate('FK.view()') == 'ballistics'
    page.click('#bEdit')
    expect(page.locator(DLG)).to_be_visible()
    page.wait_for_timeout(250)
    page.click('#rfCancel')                                 # nothing changed: closes at once
    expect(page.locator(DLG)).to_be_hidden()
    expect(page.locator('#dlgConfirm')).to_be_hidden()


def test_typing_and_changing_back_is_not_a_change(page, app_url):
    open_editor(page, app_url)
    page.fill('#rfName', 'Changed')
    page.fill('#rfName', 'Mine')
    page.go_back()
    expect(page.locator(DLG)).to_be_hidden()


def test_delete_selected_profile_lands_on_a_real_one(page, app_url):
    open_editor(page, app_url)
    page.click('#rfDelete')
    expect(page.locator('#cfTitle')).to_have_text('Delete the profile?')
    page.click('#cfCancel')
    expect(page.locator(DLG)).to_be_visible()
    assert profiles(page) == [OWN]
    page.click('#rfDelete')
    page.click('#cfOk')
    expect(page.locator(DLG)).to_be_hidden()
    expect(page.locator('#dlgConfirm')).to_be_hidden()
    assert profiles(page) == []
    sel = page.evaluate('FK.bal.selected()')
    assert sel['id'] in [p['id'] for p in page.evaluate('FK._test.presets()')]
    assert page.inner_text('#solElev') != '—'
    page.wait_for_timeout(500)
    assert page.evaluate('FK.view()') == 'ballistics'


def test_a_name_with_markup_is_kept_as_text(page, app_url):
    hostile = {**OWN, 'name': '<img src=x onerror=window.__x=1>'}
    open_editor(page, app_url, profiles=(hostile,))
    assert page.input_value('#rfName') == hostile['name']
    page.click('#rfDelete')
    assert page.evaluate('document.querySelector("#cfText img") === null && !window.__x')
    page.click('#cfCancel')


def test_editor_makes_no_sight_part_of_the_trajectory(page, app_url):
    """The answer card is the same whichever sight is set."""
    open_editor(page, app_url)
    before = page.inner_text('#solSub')
    page.select_option('#rfOptic', 'turret')
    page.select_option('#rfUnit', 'moa')
    page.click('#rfSave')
    page.wait_for_timeout(300)
    assert page.inner_text('#solSub') == before


@pytest.mark.parametrize('night', [False, True], ids=['day', 'night'])
@pytest.mark.parametrize('sight', ['none', 'turret', 'reticle', 'dot'])
def test_editor_fits_360_day_and_night_with_large_text(page, app_url, sight, night):
    long = {**OWN, 'name': 'A fairly long profile name for a rifle in a long case ' * 1, 'optic': {'type': 'reticle', 'unit': 'mil', 'marks': [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]}}
    ballistics(page, app_url, night=night, profiles=[long])
    page.evaluate("FK.bal.select('u1')")
    page.click('#bEdit')
    expect(page.locator(DLG)).to_be_visible()
    page.select_option('#rfOptic', sight)
    if sight == 'turret':
        page.select_option('#rfUnit', 'moa')
    page.fill('#rfZTemp', '40')
    page.fill('#rfZAlt', '800')
    page.wait_for_timeout(250)
    box = page.locator(DLG).bounding_box()
    assert box['x'] >= -1 and box['x'] + box['width'] <= 361, box
    assert [x for x in overflow(page, DLG) if 'page scrolls' not in x] == []
    assert page.evaluate("d => { const e = document.querySelector(d); return e.scrollWidth <= e.clientWidth + 1; }", DLG)
    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
    assert too_small(page, DLG) == []
    assert clipped_buttons(page, DLG) == []
    enlarge_text(page)
    page.wait_for_timeout(100)
    assert [x for x in overflow(page, DLG) if 'page scrolls' not in x] == []
    assert page.evaluate("d => { const e = document.querySelector(d); return e.scrollWidth <= e.clientWidth + 1; }", DLG)
    assert clipped_buttons(page, DLG) == []
    # the action buttons stay on screen with enlarged text
    r = page.locator('#rfCancel').bounding_box()
    assert r['y'] >= 0 and r['y'] + r['height'] <= 641, r


def test_built_in_editor_fits_with_large_text(page, app_url):
    open_editor(page, app_url, select='p308')
    assert too_small(page, DLG) == [] and clipped_buttons(page, DLG) == []
    enlarge_text(page)
    page.wait_for_timeout(100)
    assert [x for x in overflow(page, DLG) if 'page scrolls' not in x] == [] and clipped_buttons(page, DLG) == []


# ---------- Fix round 1 ----------

def test_station_pressure_must_be_between_8_and_33_inhg(page, app_url):
    open_editor(page, app_url)
    page.fill('#rfZTemp', '40')
    for bad in ('0', '-3', '2.992', '7.9', '33.1', '299.2'):
        page.fill('#rfZPress', bad)
        refuse(page, 'Station pressure must be between 8 and 33 inHg.', 'rfZPress')
    page.fill('#rfZAlt', '800')
    page.fill('#rfZPress', '0.1')
    refuse(page, 'Station pressure must be between 8 and 33 inHg.', 'rfZPress')
    assert 'zeroAtm' not in profiles(page)[0]
    page.fill('#rfZPress', '8')
    page.click('#rfSave')
    expect(page.locator(DLG)).to_be_hidden()
    assert profiles(page)[0]['zeroAtm']['press'] == 8


def test_zero_condition_ranges_are_refused(page, app_url):
    open_editor(page, app_url)
    page.fill('#rfZAlt', '800')
    for t in ('-61', '141'):
        page.fill('#rfZTemp', t)
        refuse(page, 'Temperature must be between -60 and 140 °F.', 'rfZTemp')
    page.fill('#rfZTemp', '40')
    for a in ('-2001', '30001'):
        page.fill('#rfZAlt', a)
        refuse(page, 'Altitude must be between -2,000 and 30,000 ft.', 'rfZAlt')
    page.fill('#rfZTemp', '-60')
    page.fill('#rfZAlt', '-2000')
    page.click('#rfSave')
    assert profiles(page)[0]['zeroAtm'] == {'temp': -60, 'alt': -2000, 'rh': 50}
    page.click('#bEdit')
    page.fill('#rfZTemp', '140')
    page.fill('#rfZAlt', '30000')
    page.click('#rfSave')
    assert profiles(page)[0]['zeroAtm']['alt'] == 30000


@pytest.mark.parametrize('raw,want', [
    ({'temp': 40, 'alt': 800, 'press': 0}, {'temp': 40, 'alt': 800, 'rh': 50}),
    ({'temp': 40, 'alt': 800, 'press': -5}, {'temp': 40, 'alt': 800, 'rh': 50}),
    ({'temp': 40, 'press': 0}, None),
    ({'temp': 40, 'press': 29.1, 'alt': 50000}, {'temp': 40, 'press': 29.1, 'rh': 50}),
    ({'temp': 40, 'alt': -2001}, None),
    ({'temp': 40, 'alt': 30001}, None),
    ({'temp': -61, 'alt': 100}, None),
    ({'temp': 141, 'alt': 100}, None),
    ({'temp': 140, 'alt': 30000}, {'temp': 140, 'alt': 30000, 'rh': 50}),
    ({'temp': -60, 'alt': -2000}, {'temp': -60, 'alt': -2000, 'rh': 50}),
])
def test_clean_drops_impossible_zero_conditions(page, app_url, raw, want):
    ballistics(page, app_url)
    got = page.evaluate('p => FK.bal.clean(p)', {**OWN, 'zeroAtm': raw})
    assert got.get('zeroAtm') == want


def test_marks_box_is_a_plain_text_field_and_comma_or_space_both_separate(page, app_url):
    open_editor(page, app_url)
    page.select_option('#rfOptic', 'reticle')
    el = page.locator('#rfMarks')
    assert el.get_attribute('type') == 'text' and el.get_attribute('inputmode') is None
    assert [el.get_attribute(a) for a in ('autocapitalize', 'autocomplete', 'autocorrect', 'spellcheck')] == ['off', 'off', 'off', 'false']
    assert 'Separate marks with spaces or commas, like 1.5 3 4.6.' in page.text_content(DLG)
    hints = page.locator('#rfMarksHint p').all_text_contents()
    assert hints[0] == 'Separate marks with spaces or commas, like 1.5 3 4.6.' and len(hints) == 3
    for text in ('1.5 3 4.6', '1.5, 3, 4.6', '1.5,3,4.6'):
        page.click('#bEdit') if not page.locator(DLG).is_visible() else None
        page.fill('#rfMarks', text)
        page.click('#rfSave')
        assert profiles(page)[0]['optic']['marks'] == [1.5, 3, 4.6], text
        page.wait_for_timeout(400)


def test_equal_neighbouring_marks_are_refused(page, app_url):
    open_editor(page, app_url)
    reticle(page, '3, 3')
    refuse(page, 'Marks must get larger down the list.', 'rfMarks')
    page.fill('#rfMarks', '1 2 2 3')
    refuse(page, 'Marks must get larger down the list.', 'rfMarks')


def test_escape_with_unsaved_typing_asks(page, app_url):
    open_editor(page, app_url)
    page.keyboard.press('Escape')                       # nothing typed: closes
    expect(page.locator(DLG)).to_be_hidden()
    page.wait_for_timeout(400)
    page.click('#bEdit')
    page.fill('#rfName', 'Changed')
    page.keyboard.press('Escape')
    expect(page.locator('#cfTitle')).to_have_text('Discard changes to this profile?')
    page.click('#cfCancel')
    expect(page.locator(DLG)).to_be_visible()
    assert page.input_value('#rfName') == 'Changed'
    page.keyboard.press('Escape')
    page.click('#cfOk')
    expect(page.locator(DLG)).to_be_hidden()
    assert profiles(page) == [OWN]


def test_backdrop_tap_with_unsaved_typing_asks(page, app_url):
    open_editor(page, app_url)
    page.fill('#rfName', 'Changed')
    page.mouse.click(180, 10)
    expect(page.locator('#cfTitle')).to_have_text('Discard changes to this profile?')
    page.click('#cfCancel')
    expect(page.locator(DLG)).to_be_visible()
    page.mouse.click(180, 10)
    page.click('#cfOk')
    expect(page.locator(DLG)).to_be_hidden()
    assert profiles(page) == [OWN]
    page.wait_for_timeout(400)
    page.click('#bEdit')
    page.mouse.click(180, 10)                           # nothing typed: closes at once
    expect(page.locator(DLG)).to_be_hidden()


def test_changing_only_the_sight_type_is_a_change(page, app_url):
    open_editor(page, app_url)
    page.select_option('#rfOptic', 'dot')
    page.go_back()
    expect(page.locator('#cfTitle')).to_have_text('Discard changes to this profile?')
    page.click('#cfCancel')
    page.select_option('#rfOptic', 'none')              # back to what it opened with
    page.go_back()
    expect(page.locator(DLG)).to_be_hidden()


def test_state_resets_between_openings(page, app_url):
    open_editor(page, app_url, select='p308')
    expect(page.locator('#rfSave')).to_be_hidden()
    page.click('#rfCancel')
    expect(page.locator(DLG)).to_be_hidden()
    page.wait_for_timeout(400)
    page.evaluate("FK.bal.select('u1')")
    page.click('#bEdit')
    expect(page.locator('#rfSave')).to_be_visible()
    expect(page.locator('#rfDelete')).to_be_visible()
    expect(page.locator('#rfBuiltIn')).to_be_hidden()
    expect(page.locator('#rfTitle')).to_have_text('Edit profile')
    page.fill('#rfBC', '')
    refuse(page, 'Ballistic coefficient must be between 0.05 and 1.2.', 'rfBC')
    page.click('#rfCancel')
    page.click('#cfOk')                                 # Discard (Cancel asks: the coefficient was changed)
    expect(page.locator(DLG)).to_be_hidden()
    page.wait_for_timeout(400)
    page.click('#bEdit')
    assert msg(page) == '' and page.input_value('#rfBC') == '0.3'


def test_save_as_new_keeps_the_sight(page, app_url):
    open_editor(page, app_url)
    page.select_option('#rfOptic', 'turret')
    page.select_option('#rfUnit', 'iphy')
    page.select_option('#rfClick', '0.125')
    page.fill('#rfName', 'Turret copy')             # a copy needs its own name
    page.click('#rfSaveNew')
    expect(page.locator(DLG)).to_be_hidden()
    assert profiles(page)[0] == OWN
    assert profiles(page)[1]['optic'] == {'type': 'turret', 'unit': 'iphy', 'click': 0.125}
    page.wait_for_timeout(400)
    page.click('#bEdit')
    reticle(page, '1 2.5 4')
    page.fill('#rfName', 'Reticle copy')
    page.click('#rfSaveNew')
    assert profiles(page)[2]['optic'] == {'type': 'reticle', 'unit': 'mil', 'marks': [1, 2.5, 4]}
    assert profiles(page)[1]['optic']['type'] == 'turret'


def test_negative_weight_and_sight_height_are_refused(page, app_url):
    open_editor(page, app_url)
    page.fill('#rfW', '-1')
    refuse(page, 'Bullet weight must be between 1 and 1,000 gr, or blank.', 'rfW')
    page.fill('#rfW', '150')
    page.fill('#rfSH', '-0.5')
    refuse(page, 'Sight height must be between 0 and 6 in.', 'rfSH')
    assert profiles(page) == [OWN]


@pytest.mark.parametrize('night', [False, True], ids=['day', 'night'])
def test_a_refusal_at_enlarged_text_stays_inside_the_screen(page, app_url, night):
    ballistics(page, app_url, night=night, profiles=[OWN])
    page.evaluate("FK.bal.select('u1')")
    page.click('#bEdit')
    page.select_option('#rfOptic', 'reticle')
    page.fill('#rfMarks', '3 1.5')
    enlarge_text(page)
    page.click('#rfSave')
    expect(page.locator('#rfMsg')).to_have_text('Marks must get larger down the list.')
    page.wait_for_timeout(150)
    boxes = page.evaluate("""() => [...document.querySelectorAll('#dlgRifle .mk-act .btn, #rfMsg')]
      .filter(e => e.getBoundingClientRect().width).map(e => { const r = e.getBoundingClientRect(); return [e.id, r.left, r.right, r.top, r.bottom, e.scrollWidth, e.clientWidth, e.scrollHeight, e.clientHeight]; })""")
    assert len(boxes) == 5
    for id_, l, r, t, b, sw, cw, sh, ch in boxes:
        assert l >= -1 and r <= 361 and t >= 0 and b <= 641, (id_, l, r, t, b)
        assert sw <= cw + 1 and sh <= ch + 1, (id_, 'clipped')
    assert page.evaluate("document.querySelector('#dlgRifle').scrollWidth <= document.querySelector('#dlgRifle').clientWidth + 1")


# ---------- Plausible loads and names of their own ----------

def test_load_values_outside_plausible_ranges_are_refused(page, app_url):
    open_editor(page, app_url)
    cases = [('rfBC', ['0.049', '1.21', '5', '0.00001'], ['0.05', '1.2'], 'Ballistic coefficient must be between 0.05 and 1.2.'),
             ('rfMV', ['299', '5001', '99999'], ['300', '5000'], 'Muzzle velocity must be between 300 and 5,000 fps.'),
             ('rfZero', ['4.9', '1001', '2000', '0.001'], ['5', '1000'], 'Zero range must be between 5 and 1,000 yd.'),
             ('rfW', ['0.5', '1001', '-1', '1e308'], ['', '0', '1', '1000'], 'Bullet weight must be between 1 and 1,000 gr, or blank.'),
             ('rfSH', ['-0.1', '6.1', '30'], ['', '0', '6'], 'Sight height must be between 0 and 6 in.')]
    for field, bad, good, text in cases:
        keep = page.input_value('#' + field)
        for v in bad:
            page.fill('#' + field, v)
            refuse(page, text, field)
        for v in good:
            page.fill('#' + field, v)
            page.click('#rfSave')
            expect(page.locator(DLG)).to_be_hidden()
            page.wait_for_timeout(400)
            page.click('#bEdit')
            expect(page.locator(DLG)).to_be_visible()
            page.wait_for_timeout(250)
        page.fill('#' + field, keep)
    assert page.evaluate('document.body.innerText').count('Infinity') == 0


def test_a_name_already_used_is_refused(page, app_url):
    other = {**OWN, 'id': 'u2', 'name': 'Second rifle'}
    open_editor(page, app_url, profiles=(OWN, other))
    for name in ('Second rifle', '  second RIFLE ', 'Federal Gold Medal .308 Win 175 gr SMK, 24″ barrel', 'federal gold medal .308 win 175 gr smk, 24″ barrel'):
        page.fill('#rfName', name)
        refuse(page, 'Give the profile its own name.', 'rfName')
        page.click('#rfSaveNew')
        expect(page.locator('#rfMsg')).to_have_text('Give the profile its own name.')
        assert page.evaluate('document.activeElement.id') == 'rfName'
    page.fill('#rfName', 'Mine')                     # its own name, saved in place, is fine
    page.click('#rfSaveNew')                         # but a copy may not share it
    expect(page.locator('#rfMsg')).to_have_text('Give the profile its own name.')
    assert len(profiles(page)) == 2
    page.fill('#rfName', ' MINE ')
    page.click('#rfSave')
    expect(page.locator(DLG)).to_be_hidden()
    assert [p['name'] for p in profiles(page)] == ['MINE', 'Second rifle']


def test_a_built_in_opens_with_a_name_of_its_own(page, app_url):
    open_editor(page, app_url, select='p308')
    name = 'Federal Gold Medal .308 Win 175 gr SMK, 24″ barrel'
    assert page.input_value('#rfName') == name + ' (mine)'
    page.go_back()                                   # the name is not a change: Back closes at once
    expect(page.locator(DLG)).to_be_hidden()
    page.wait_for_timeout(400)
    page.click('#bEdit')
    expect(page.locator(DLG)).to_be_visible()
    page.wait_for_timeout(250)
    page.click('#rfSaveNew')
    expect(page.locator(DLG)).to_be_hidden()
    assert profiles(page)[-1]['name'] == name + ' (mine)'
    page.wait_for_timeout(400)
    page.evaluate("FK.bal.select('p308')")
    page.click('#bEdit')
    expect(page.locator(DLG)).to_be_visible()
    assert page.input_value('#rfName') == name + ' (mine 2)'
    # the longest built-in name still fits in 60 characters with its suffix
    page.click('#rfCancel')
    page.wait_for_timeout(400)
    longest = page.evaluate('FK._test.presets().map(p => p.id).sort((a, b) => 0)')
    for pid in longest:
        page.evaluate('id => FK.bal.select(id)', pid)
        page.click('#bEdit')
        expect(page.locator(DLG)).to_be_visible()
        v = page.input_value('#rfName')
        assert len(v) <= 60 and v.endswith(')') and ' (mine' in v, v
        page.click('#rfCancel')
        expect(page.locator(DLG)).to_be_hidden()
        page.wait_for_timeout(400)


# ---------- Enter, the keyboards, the marks box's words ----------

def test_enter_never_saves_the_profile(page, app_url):
    open_editor(page, app_url, profiles=(RET,), select='u2')
    assert page.get_attribute('#rfSave', 'type') == 'button'
    page.fill('#rfName', 'Changed by Enter')
    for field in ('rfName', 'rfBC', 'rfW', 'rfMV', 'rfSH', 'rfZero', 'rfMarks', 'rfZTemp', 'rfZAlt', 'rfZPress'):
        page.press('#' + field, 'Enter')
        page.wait_for_timeout(50)
        expect(page.locator(DLG)).to_be_visible()
        assert msg(page) == '', field
    assert profiles(page) == [RET]
    page.click('#rfSave')                            # only the Save buttons save
    expect(page.locator(DLG)).to_be_hidden()
    assert profiles(page)[0]['name'] == 'Changed by Enter'


FIVE = ['bAngle', 'bTemp', 'bAlt', 'rfZTemp', 'rfZAlt']


def test_fields_that_can_be_below_zero_open_the_ordinary_keyboard(page, app_url):
    open_editor(page, app_url)
    for i in FIVE:
        el = page.locator('#' + i)
        assert el.get_attribute('type') == 'text' and el.get_attribute('inputmode') is None, i
        assert [el.get_attribute(a) for a in ('autocapitalize', 'autocomplete', 'autocorrect', 'spellcheck')] == ['off', 'off', 'off', 'false'], i
    for i in ['bRange', 'bWind', 'bPress', 'bRH', 'bMax', 'rfBC', 'rfW', 'rfMV', 'rfSH', 'rfZero', 'rfZPress', 'rfTrueYd', 'rfTrueVal']:
        assert page.evaluate(f"[document.getElementById('{i}').type, document.getElementById('{i}').inputMode]") == ['number', 'decimal'], i


def test_the_typographic_minus_counts_as_a_minus_in_the_editor(page, app_url):
    open_editor(page, app_url)
    page.fill('#rfZTemp', '\u221212')
    page.fill('#rfZAlt', '\u2212100')
    page.click('#rfSave')
    expect(page.locator(DLG)).to_be_hidden()
    assert profiles(page)[0]['zeroAtm'] == {'temp': -12, 'alt': -100, 'rh': 50}
    page.wait_for_timeout(400)
    page.click('#bEdit')
    expect(page.locator(DLG)).to_be_visible()
    page.fill('#rfZTemp', 'cold')                    # not a number: refused, never read as nothing
    refuse(page, 'Temperature must be between -60 and 140 \u00b0F.', 'rfZTemp')


def test_marks_typed_with_decimal_commas_or_below_zero_say_what_is_wrong(page, app_url):
    open_editor(page, app_url)
    reticle(page, '2,5 6,5')
    refuse(page, 'Use a point for decimals: 2.5, not 2,5.', 'rfMarks')
    page.fill('#rfMarks', '1,5 3')
    refuse(page, 'Use a point for decimals: 2.5, not 2,5.', 'rfMarks')
    for text in ('-1 3', '0 3 5', '\u22121 2'):
        page.fill('#rfMarks', text)
        refuse(page, 'Marks must be more than 0.', 'rfMarks')
    page.fill('#rfMarks', '1,2,3')                   # commas with no spaces still separate
    page.click('#rfSave')
    expect(page.locator(DLG)).to_be_hidden()
    assert profiles(page)[0]['optic']['marks'] == [1, 2, 3]


def test_the_editor_uses_the_screens_own_rules(page, app_url):
    """One definition of each shared rule (src/bal-ui.js, through FK.balHost): click sizes, ranges, the marks rule, the zero air."""
    open_editor(page, app_url)
    host = page.evaluate('Object.keys(FK.balHost).sort()')
    for k in ('CLICK_SIZES', 'RANGE', 'marksOk', 'parseNum', 'within', 'zeroAir'):
        assert k in host, k
    sizes = page.evaluate('FK.balHost.CLICK_SIZES')
    page.select_option('#rfOptic', 'turret')
    for unit in ('mil', 'moa', 'iphy'):
        page.select_option('#rfUnit', unit)
        got = [float(v) for v in page.locator('#rfClick option').evaluate_all('o => o.map(x => x.value)')]
        assert got == sizes[unit], unit
        for c in got:
            assert page.evaluate('o => !!FK.bal.clean({ id: "u9", name: "x", optic: o }).optic', {'type': 'turret', 'unit': unit, 'click': c})
    rng = page.evaluate('FK.balHost.RANGE')
    page.fill('#rfMV', str(rng['mv'][1] + 1))
    page.click('#rfSave')
    expect(page.locator('#rfMsg')).to_have_text(f"Muzzle velocity must be between {rng['mv'][0]:,} and {rng['mv'][1]:,} fps.")
    assert page.evaluate('FK.balHost.zeroAir({ temp: 40, alt: 300, rh: 50 })') == {'temp': 40, 'alt': 300, 'press': 0, 'rh': 50}


# ---------- Barrel and bullet (for spin drift) ----------

SPIN_ONE = {**OWN, 'w': 175, 'mv': 2600}      # 175 gr, 2600 fps: with a .308, 1.24 in bullet the Miller figure is 2.4 at 1:10
LEN_MSG = 'Bullet length looks wrong for that diameter. Measure the bullet, not the cartridge.'


def miller(w, dia, length, twist, mv, temp=59, press=29.92126):
    """Courtney & Miller equation 1, written out here and not read from the app."""
    t, L = twist / dia, length / dia
    return (30 * w / (t * t * dia ** 3 * L * (1 + L * L)) * (mv / 2800) ** (1 / 3) * (temp + 460) / 519 * 29.92 / press)


def spin(page, twist=None, direction=None, blen=None, bdia=None):
    for i, v in (('rfTwist', twist), ('rfBLen', blen), ('rfBDia', bdia)):
        if v is not None:
            page.fill('#' + i, str(v))
    if direction:
        page.select_option('#rfTwistDir', direction)


def test_spin_fields_are_in_the_editor_in_their_place(page, app_url):
    open_editor(page, app_url)
    heads = page.evaluate("[...document.querySelectorAll('#dlgRifle h3.rf-h')].map(h => h.textContent)")      # as written, not as shown (capitals)
    assert heads.index('Barrel and bullet (for spin drift)') == heads.index('Zero conditions') + 1
    order = page.evaluate("""() => { const f = [...document.querySelectorAll('#rfForm h3, #rfForm input, #rfForm select')].map(e => e.id || e.textContent);
      return f.slice(f.indexOf('rfZPress')); }""")
    assert order[:6] == ['rfZPress', 'Barrel and bullet (for spin drift)', 'rfTwist', 'rfTwistDir', 'rfBLen', 'rfBDia']
    assert 'Correct from a real shot' in order[6:]
    assert page.locator('#rfTwistDir option').evaluate_all('o => o.map(x => [x.value, x.textContent])') == [['R', 'Right'], ['L', 'Left']]
    for i in ('rfTwist', 'rfBLen', 'rfBDia'):
        assert page.get_attribute('#' + i, 'type') == 'number' and page.get_attribute('#' + i, 'inputmode') == 'decimal'
    assert ("Bullet length is the bullet alone, from the maker's data or a caliper. "
            "For a polymer-tipped bullet the stability figure reads a little low.") in page.text_content(DLG)
    assert page.input_value('#rfTwistDir') == 'R' and page.input_value('#rfTwist') == ''


def test_spin_fields_save_and_reopen(page, app_url):
    open_editor(page, app_url, profiles=(SPIN_ONE,))
    spin(page, 8, 'L', 0.994, 0.224)
    page.click('#rfSave')
    expect(page.locator(DLG)).to_be_hidden()
    got = profiles(page)[0]
    assert (got['twist'], got['twistDir'], got['blen'], got['bdia']) == (8, 'L', 0.994, 0.224)
    assert list(got)[-4:] == ['twist', 'twistDir', 'blen', 'bdia']
    page.wait_for_timeout(400)    # a tap on the same spot straight after a sheet closes is swallowed (double-tap guard)
    page.click('#bEdit')
    expect(page.locator(DLG)).to_be_visible()
    assert [page.input_value('#' + i) for i in ('rfTwist', 'rfTwistDir', 'rfBLen', 'rfBDia')] == ['8', 'L', '0.994', '0.224']


def test_right_twist_stores_no_direction(page, app_url):
    open_editor(page, app_url, profiles=(SPIN_ONE,))
    spin(page, 8, 'L', 1.0, 0.308)
    page.click('#rfSave')
    expect(page.locator(DLG)).to_be_hidden()
    assert profiles(page)[0]['twistDir'] == 'L'
    page.wait_for_timeout(400)
    page.click('#bEdit')
    expect(page.locator(DLG)).to_be_visible()
    page.select_option('#rfTwistDir', 'R')
    page.click('#rfSave')
    expect(page.locator(DLG)).to_be_hidden()
    got = profiles(page)[0]
    assert 'twistDir' not in got and got['twist'] == 8


def test_blank_fields_are_removed_from_the_profile_and_each_is_independent(page, app_url):
    full = {**SPIN_ONE, 'twist': 8, 'twistDir': 'L', 'blen': 1.24, 'bdia': 0.308}
    open_editor(page, app_url, profiles=(full,))
    page.fill('#rfTwist', '')
    page.fill('#rfBLen', '')
    page.click('#rfSave')
    expect(page.locator(DLG)).to_be_hidden()
    assert profiles(page)[0] == {**SPIN_ONE, 'twistDir': 'L', 'bdia': 0.308}
    page.wait_for_timeout(400)
    page.click('#bEdit')
    page.fill('#rfBDia', '')
    page.select_option('#rfTwistDir', 'R')
    page.click('#rfSave')
    expect(page.locator(DLG)).to_be_hidden()
    assert profiles(page)[0] == SPIN_ONE


def test_a_profile_saved_without_spin_fields_stays_without_them(page, app_url):
    open_editor(page, app_url)
    page.fill('#rfBC', '0.35')
    page.click('#rfSave')
    expect(page.locator(DLG)).to_be_hidden()
    assert profiles(page)[0] == {**OWN, 'bc': 0.35}


def test_save_as_new_from_a_built_in_load_carries_the_spin_fields_typed(page, app_url):
    open_editor(page, app_url, select='p308')
    assert [page.input_value('#' + i) for i in ('rfTwist', 'rfBLen', 'rfBDia')] == ['', '', '']
    spin(page, 10, None, 1.24, 0.308)
    page.click('#rfSaveNew')
    expect(page.locator(DLG)).to_be_hidden()
    got = profiles(page)[-1]
    assert (got['twist'], got['blen'], got['bdia']) == (10, 1.24, 0.308)
    assert [k for k in ('twist', 'blen', 'bdia') if k in page.evaluate('FK._test.presets().find(p => p.id === "p308")')] == []


def test_editor_refuses_a_length_wrong_for_the_diameter(page, app_url):
    open_editor(page, app_url, profiles=(SPIN_ONE,))
    for length in ('0.5', '2.3'):                        # under 2 and over 7 calibers of .308
        spin(page, 10, None, length, 0.308)
        refuse(page, LEN_MSG, 'rfBLen')
    spin(page, None, None, '1.24')
    page.click('#rfSave')
    expect(page.locator(DLG)).to_be_hidden()
    assert profiles(page)[0]['blen'] == 1.24


def test_editor_refuses_values_out_of_range(page, app_url):
    open_editor(page, app_url, profiles=(SPIN_ONE,))
    for field, bad, text in (('rfTwist', '2', 'Twist must be between 3 and 30 inches per turn.'),
                             ('rfTwist', '31', 'Twist must be between 3 and 30 inches per turn.'),
                             ('rfBLen', '0.1', 'Bullet length must be between 0.2 and 3 in.'),
                             ('rfBLen', '3.5', 'Bullet length must be between 0.2 and 3 in.'),
                             ('rfBDia', '0.1', 'Bullet diameter must be between 0.17 and 0.6 in.'),
                             ('rfBDia', '0.7', 'Bullet diameter must be between 0.17 and 0.6 in.')):
        page.fill('#' + field, bad)
        refuse(page, text, field)
        page.fill('#' + field, '')
    assert profiles(page) == [SPIN_ONE]
    page.fill('#rfTwist', '3'); page.fill('#rfBDia', '0.6'); page.fill('#rfBLen', '3')
    page.click('#rfSave')
    expect(page.locator(DLG)).to_be_hidden()


SHOT_LOAD = {**SPIN_ONE, 'bc': 0.243, 'model': 'G7'}


def work_out(page, mv_true=2550, yd=600):
    """Type the elevation (mil) the load would need at yd if it left the muzzle at mv_true, and press Work it out."""
    from .test_bal_true import shot
    page.fill('#rfTrueYd', str(yd))
    page.select_option('#rfTrueUnit', 'mil')
    page.fill('#rfTrueVal', f"{shot(page, mv_true, yd, SHOT_LOAD) * 1000:.3f}")
    page.click('#rfTrueGo')


def test_a_bad_spin_field_does_not_stop_a_shot_correction(page, app_url):
    open_editor(page, app_url, profiles=(SHOT_LOAD,))
    page.fill('#rfTwist', '99')
    work_out(page)
    expect(page.locator('#rfTrueOut')).to_contain_text('Velocity')
    assert 'Twist' not in page.inner_text('#rfTrueOut')


def test_typing_in_the_spin_fields_keeps_a_worked_out_velocity(page, app_url):
    open_editor(page, app_url, profiles=(SHOT_LOAD,))
    work_out(page)
    expect(page.locator('#rfTrueSave')).to_be_visible()
    spin(page, 10, 'L', 1.24, 0.308)
    expect(page.locator('#rfStab')).to_be_visible()
    expect(page.locator('#rfTrueSave')).to_be_visible()


def stab_text(sg, grade):
    one = f'{sg:.1f}'
    return {'stable': f'Stability {one}.',
            'marginal': f'Stability {one}: marginal for this twist. Spin drift is still shown.',
            'unstable': f'Stability {one}: by this formula the bullet is not stable in this twist. Spin drift is not shown.'}[grade]


def test_stability_line_follows_typing(page, app_url):
    open_editor(page, app_url, profiles=(SPIN_ONE,))
    stab = page.locator('#rfStab')
    assert page.evaluate('document.querySelector("#rfStab").className') == 'hint' and page.get_attribute('#rfStab', 'aria-live') == 'polite'
    expect(stab).to_be_hidden()
    spin(page, 10)
    expect(stab).to_be_hidden()                          # length and diameter still missing
    page.fill('#rfBDia', '0.308')
    expect(stab).to_be_hidden()
    page.fill('#rfBLen', '1.24')
    sg = miller(175, 0.308, 1.24, 10, 2600)
    assert 2.0 < sg
    expect(stab).to_have_text(stab_text(sg, 'stable'))
    page.fill('#rfTwist', '14')
    sg = miller(175, 0.308, 1.24, 14, 2600)
    assert 1.0 < sg < 1.4 - 0.05
    expect(stab).to_have_text(stab_text(sg, 'marginal'))
    page.fill('#rfTwist', '16')
    sg = miller(175, 0.308, 1.24, 16, 2600)
    assert sg < 0.95
    expect(stab).to_have_text(stab_text(sg, 'unstable'))
    page.fill('#rfTwist', '')
    expect(stab).to_be_hidden()


def test_stability_line_hides_for_anything_unusable_and_never_blocks_save(page, app_url):
    open_editor(page, app_url, profiles=(SPIN_ONE,))
    spin(page, 16, None, 1.24, 0.308)
    expect(page.locator('#rfStab')).to_contain_text('not stable')
    for field, bad in (('rfMV', ''), ('rfMV', '99999'), ('rfW', '0'), ('rfW', ''), ('rfTwist', '2'), ('rfBLen', '0.5'), ('rfBDia', '0.7')):
        good = page.input_value('#' + field)
        page.fill('#' + field, bad)
        expect(page.locator('#rfStab')).to_be_hidden()
        page.fill('#' + field, good)
        expect(page.locator('#rfStab')).to_be_visible()
    text = page.inner_text('#dlgRifle')
    import re
    assert not re.search(r'NaN|Infinity|undefined|-0\.0', text), text
    page.click('#rfSave')                                # an unstable bullet saves
    expect(page.locator(DLG)).to_be_hidden()
    assert profiles(page)[0]['twist'] == 16


def test_stability_line_uses_todays_air_from_the_screen(page, app_url):
    ballistics(page, app_url, profiles=[SPIN_ONE])
    page.click('#bCondBtn')
    page.fill('#bTemp', '-20')
    page.fill('#bAlt', '8000')
    page.evaluate("FK.bal.select('u1')")
    page.click('#bEdit')
    expect(page.locator(DLG)).to_be_visible()
    spin(page, 11, None, 1.24, 0.308)
    press = 29.92126 * (1 - 6.8755856e-6 * 8000) ** 5.2558797
    sg = miller(175, 0.308, 1.24, 11, 2600, temp=-20, press=press)
    expect(page.locator('#rfStab')).to_have_text(stab_text(sg, 'stable' if sg >= 1.4 else 'marginal' if sg >= 1.0 else 'unstable'))
    assert sg != pytest.approx(miller(175, 0.308, 1.24, 11, 2600), abs=0.2)     # the air made a difference


def test_stability_line_falls_back_to_standard_air_when_the_screens_air_is_out_of_range(page, app_url):
    ballistics(page, app_url, profiles=[SPIN_ONE])
    page.click('#bCondBtn')
    page.fill('#bTemp', '900')
    page.evaluate("FK.bal.select('u1')")
    page.click('#bEdit')
    expect(page.locator(DLG)).to_be_visible()
    spin(page, 10, None, 1.24, 0.308)
    expect(page.locator('#rfStab')).to_have_text(stab_text(miller(175, 0.308, 1.24, 10, 2600, press=29.92126), 'stable'))


def test_typing_a_twist_makes_the_sheet_dirty(page, app_url):
    open_editor(page, app_url, profiles=(SPIN_ONE,))
    page.evaluate("const g = history.go.bind(history); history.go = k => { setTimeout(() => g(k), 250); }; 0")   # a slow phone
    page.fill('#rfTwist', '8')
    page.go_back()
    expect(page.locator('#cfTitle')).to_have_text('Discard changes to this profile?')
    expect(page.locator('#cfCancel')).to_have_text('Keep editing')
    expect(page.locator('#cfOk')).to_have_text('Discard')
    page.click('#cfCancel')
    expect(page.locator('#cfOk')).to_be_hidden()
    expect(page.locator(DLG)).to_be_visible()
    assert page.input_value('#rfTwist') == '8'
    page.go_back()
    page.click('#cfOk')
    expect(page.locator(DLG)).to_be_hidden()
    assert profiles(page) == [SPIN_ONE]


@pytest.mark.parametrize('field,value', [('rfTwistDir', 'L'), ('rfBLen', '1.2'), ('rfBDia', '0.308')])
def test_each_new_field_makes_the_sheet_dirty(page, app_url, field, value):
    open_editor(page, app_url, profiles=(SPIN_ONE,))
    page.evaluate("const g = history.go.bind(history); history.go = k => { setTimeout(() => g(k), 250); }; 0")
    if field == 'rfTwistDir':
        page.select_option('#' + field, value)
    else:
        page.fill('#' + field, value)
    page.click('#rfCancel')
    expect(page.locator('#cfTitle')).to_have_text('Discard changes to this profile?')
    page.click('#cfCancel')


def test_untouched_spin_fields_do_not_make_the_sheet_dirty(page, app_url):
    full = {**SPIN_ONE, 'twist': 8, 'twistDir': 'L', 'blen': 1.24, 'bdia': 0.308}
    open_editor(page, app_url, profiles=(full,))
    page.click('#rfCancel')
    expect(page.locator(DLG)).to_be_hidden()
    expect(page.locator('#dlgConfirm')).to_be_hidden()


@pytest.mark.parametrize('night', [False, True], ids=['day', 'night'])
def test_rifle_sheet_still_fits_360_day_and_night_with_enlarged_text(page, app_url, night):
    full = {**SPIN_ONE, 'name': 'A fairly long profile name for a rifle in a long case', 'twist': 16, 'twistDir': 'L', 'blen': 1.24, 'bdia': 0.308,
            'optic': {'type': 'reticle', 'unit': 'mil', 'marks': [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]}}
    ballistics(page, app_url, night=night, profiles=[full])
    page.evaluate("FK.bal.select('u1')")
    page.click('#bEdit')
    expect(page.locator(DLG)).to_be_visible()
    expect(page.locator('#rfStab')).to_be_visible()           # the longest of the three lines is on screen
    page.fill('#rfZTemp', '40')
    page.fill('#rfZAlt', '800')
    page.locator('#rfBDia').scroll_into_view_if_needed()
    box = page.locator(DLG).bounding_box()
    assert box['x'] >= -1 and box['x'] + box['width'] <= 361, box
    assert [x for x in overflow(page, DLG) if 'page scrolls' not in x] == []
    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
    assert too_small(page, DLG) == [] and clipped_buttons(page, DLG) == []
    enlarge_text(page)
    page.locator('#rfStab').scroll_into_view_if_needed()
    assert [x for x in overflow(page, DLG) if 'page scrolls' not in x] == []
    assert page.evaluate("d => { const e = document.querySelector(d); return e.scrollWidth <= e.clientWidth + 1; }", DLG)
    assert clipped_buttons(page, DLG) == []
    assert too_small(page, DLG) == []
    for i in ('rfTwist', 'rfTwistDir', 'rfBLen', 'rfBDia', 'rfStab'):      # every new control lies inside the sheet's own width
        r = page.locator('#' + i).bounding_box()
        assert r['x'] >= 0 and r['x'] + r['width'] <= 361, (i, r)
    r = page.locator('#rfCancel').bounding_box()
    assert r['y'] >= 0 and r['y'] + r['height'] <= 641, r
