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


def test_edit_button_sits_with_the_profile_buttons(page, app_url):
    ballistics(page, app_url, profiles=[OWN])
    assert page.evaluate("document.querySelector('#bEdit').closest('.row') === document.querySelector('#bSave').closest('.row')")
    expect(page.locator('#bEdit')).to_have_text('Edit profile')
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
    assert page.input_value('#bBC') == '0.35'        # the main screen shows the saved numbers


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
    assert page.input_value('#bMV') == '2900'


def test_built_in_load_offers_save_as_new_only(page, app_url):
    open_editor(page, app_url, select='p308')
    expect(page.locator('#rfTitle')).to_have_text('Built-in load')
    expect(page.locator('#rfSave')).to_be_hidden()
    expect(page.locator('#rfDelete')).to_be_hidden()
    expect(page.locator('#rfSaveNew')).to_be_visible()
    expect(page.locator('#rfCancel')).to_be_visible()
    assert "Built-in loads can't be changed. Save as a new profile to edit one." in page.text_content(DLG)
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
    refuse(page, 'Marks must be numbers, like 1.5, 3, 4.6.', 'rfMarks')
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
    for field, text in [('rfName', 'Give the profile a name.'), ('rfBC', 'Ballistic coefficient must be more than 0.'),
                        ('rfMV', 'Muzzle velocity must be more than 0.'), ('rfZero', 'Zero range must be more than 0.')]:
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
    page.click('#rfSaveNew')
    expect(page.locator(DLG)).to_be_hidden()
    got = profiles(page)[-1]
    assert got['sight'] == 0 and got['w'] == 0


def test_refusal_message_clears_when_it_is_fixed(page, app_url):
    open_editor(page, app_url)
    page.fill('#rfBC', '')
    refuse(page, 'Ballistic coefficient must be more than 0.', 'rfBC')
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


def test_back_without_typing_closes_and_cancel_never_asks(page, app_url):
    open_editor(page, app_url)
    page.go_back()
    expect(page.locator(DLG)).to_be_hidden()
    page.wait_for_timeout(400)    # a tap on the same spot straight after a sheet closes is swallowed (double-tap guard)
    page.click('#bEdit')
    page.fill('#rfName', 'Changed')
    page.click('#rfCancel')
    expect(page.locator(DLG)).to_be_hidden()
    expect(page.locator('#dlgConfirm')).to_be_hidden()
    assert profiles(page) == [OWN]
    page.wait_for_timeout(400)
    assert page.evaluate('FK.view()') == 'ballistics'


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
