"""Correct a profile's muzzle velocity from one real shot, in the profile editor (src/bal-edit.js)."""
import math

import pytest
from playwright.sync_api import expect

from .test_bal_editor import DLG, open_editor as _open, profiles
from .test_tactical_layout import ballistics, enlarge_text, overflow, too_small, clipped_buttons

LOAD = {'id': 'u1', 'name': 'Mine', 'bc': 0.243, 'model': 'G7', 'w': 175, 'mv': 2600, 'sight': 1.5, 'zero': 100}
OWN = LOAD
AIR = dict(temp=59, alt=0, press=0, rh=50)
NEAR = 'Use a shot at 300 yd or more. Closer in, a small error gives a wild velocity.'
SLOW = "At that distance the bullet is near the speed of sound, where velocity isn't the thing in doubt."
FAR = 'That needs a velocity change of more than 15%. Check the distance, the zero and the sight height first.'
WARN = "That's a change of more than 5%. Check the distance, the zero and the sight height first."
ASK = 'Enter the distance and the elevation the rifle needed.'


def open_editor(page, app_url, profiles=(LOAD,), select='u1'):
    _open(page, app_url, profiles=profiles, select=select)


def fresh_load(page):
    """The load without any mv0, as it was first stored, and the editor open on it."""
    page.wait_for_timeout(450)
    page.evaluate('p => { FK.bal.save(p); FK.bal.select(p.id); }', LOAD)
    page.click('#bEdit')
    expect(page.locator(DLG)).to_be_visible()
    page.wait_for_timeout(250)


def shot(page, mv, yd, load=LOAD):
    """The elevation, in radians, the load needs at yd if its velocity were mv, in the main screen's default air."""
    return page.evaluate("""([p, mv, yd, air]) => { const r = BAL.solve({ ...p, ...air, mv, w: p.w, wind: 0, clock: 12, ranges: [yd] }).rows[0];
      return Math.atan(-r.dropIn / (yd * 36)); }""", [load, mv, yd, AIR])


def typed(page, rad, yd, unit):
    return {'mil': rad * 1000, 'moa': rad * 180 / math.pi * 60, 'iphy': math.tan(rad) * 3600, 'in': math.tan(rad) * yd * 36}[unit]


def work(page, yd, val, unit=None):
    page.fill('#rfTrueYd', str(yd))
    page.fill('#rfTrueVal', str(val))
    if unit:
        page.select_option('#rfTrueUnit', unit)
    page.click('#rfTrueGo')


def out(page):
    return page.inner_text('#rfTrueOut')


def reopen(page):
    page.wait_for_timeout(450)
    page.click('#bEdit')
    expect(page.locator(DLG)).to_be_visible()
    page.wait_for_timeout(250)


def correct(page, mv, yd=600):
    work(page, yd, round(typed(page, shot(page, mv, yd), yd, 'mil'), 4), 'mil')
    page.click('#rfTrueSave')


def test_part_sits_after_zero_conditions_with_its_words(page, app_url):
    open_editor(page, app_url)
    page.locator('#rfTruePart').scroll_into_view_if_needed()
    expect(page.locator('#rfTruePart h3')).to_have_text('Correct from a real shot')
    assert page.evaluate("""() => { const z = [...document.querySelectorAll('#dlgRifle h3')].map(h => h.textContent);
      return z.slice(-2).join('|'); }""") == 'Zero conditions|Correct from a real shot'
    text = page.inner_text('#rfTruePart')
    assert 'Enter a distance and the elevation the rifle really needed there. Uses today\'s conditions from the Ballistics screen, a level shot and no wind.' in text
    for s in ['Distance (yd)', 'Elevation needed', 'In', 'Work it out']:
        assert s in text, s
    for i in ('rfTrueYd', 'rfTrueVal'):
        assert page.evaluate(f"[document.getElementById('{i}').type, document.getElementById('{i}').inputMode]") == ['number', 'decimal']
    expect(page.locator('#rfTrueSave')).to_be_hidden()
    expect(page.locator('#rfTrueUndo')).to_be_hidden()
    assert out(page) == ''


def test_built_in_load_cannot_be_corrected(page, app_url):
    ballistics(page, app_url)
    page.click('#bEdit')
    expect(page.locator(DLG)).to_be_visible()
    page.wait_for_timeout(250)
    expect(page.locator('#rfTitle')).to_have_text('Built-in load')
    expect(page.locator('#rfTruePart')).to_be_hidden()
    assert 'real shot' not in page.inner_text(DLG)
    page.click('#rfSaveNew')
    expect(page.locator(DLG)).to_be_hidden()
    reopen(page)
    expect(page.locator('#rfTruePart')).to_be_visible()


def test_unit_choices_follow_the_sight_as_typed(page, app_url):
    open_editor(page, app_url)
    names = lambda: page.locator('#rfTrueUnit option').all_inner_texts()
    assert names() == ['Inches of drop', 'Mil', 'MOA', 'Inches per 100 yd']
    page.select_option('#rfOptic', 'dot')
    assert names()[0] == 'Inches of drop'
    page.select_option('#rfOptic', 'turret')
    assert names() == ['Mil', 'MOA', 'Inches per 100 yd', 'Inches of drop']
    page.select_option('#rfUnit', 'moa')
    assert names() == ['MOA', 'Mil', 'Inches per 100 yd', 'Inches of drop']
    assert page.input_value('#rfTrueUnit') == 'moa'
    page.select_option('#rfUnit', 'iphy')
    assert names() == ['Inches per 100 yd', 'Mil', 'MOA', 'Inches of drop']
    page.select_option('#rfTrueUnit', 'in')                    # a choice the person made stays
    page.select_option('#rfUnit', 'mil')
    assert page.input_value('#rfTrueUnit') == 'in'
    page.select_option('#rfOptic', 'none')
    assert names() == ['Inches of drop', 'Mil', 'MOA', 'Inches per 100 yd']


def test_result_text_and_use_button(page, app_url):
    open_editor(page, app_url)
    work(page, 600, round(typed(page, shot(page, 2550, 600), 600, 'mil'), 4), 'mil')
    text = out(page)
    assert text.startswith('Velocity 2,600 fps → 2,55') and text.endswith('%).'), text
    assert '(-1.9%)' in text and 'Check the distance' not in text
    mv = int(text.split('→ ')[1].split(' fps')[0].replace(',', ''))
    assert abs(mv - 2550) <= 2
    expect(page.locator('#rfTrueSave')).to_have_text(f'Use {mv:,} fps')
    assert profiles(page)[0]['mv'] == 2600                        # nothing stored by this
    page.click('#rfTrueSave')
    assert page.input_value('#rfMV') == str(mv)
    assert out(page) == ''
    expect(page.locator('#rfTrueSave')).to_be_hidden()
    assert profiles(page)[0]['mv'] == 2600                        # only the sheet's own Save stores it
    page.click('#rfSave')
    expect(page.locator(DLG)).to_be_hidden()
    assert profiles(page)[0]['mv'] == mv


def test_warning_and_refusals(page, app_url):
    open_editor(page, app_url)
    work(page, 600, round(typed(page, shot(page, 2450, 600), 600, 'mil'), 4), 'mil')
    assert out(page).endswith(' ' + WARN) and out(page).startswith('Velocity 2,600 fps → 2,4'), out(page)
    expect(page.locator('#rfTrueSave')).to_be_visible()
    work(page, 250, 1)
    assert out(page) == NEAR
    expect(page.locator('#rfTrueSave')).to_be_hidden()
    work(page, 1100, round(typed(page, shot(page, 2600, 1100), 1100, 'mil'), 4))
    assert out(page) == SLOW
    work(page, 600, round(2 * typed(page, shot(page, 2600, 600), 600, 'mil'), 4))
    assert out(page) == FAR
    expect(page.locator('#rfTrueSave')).to_be_hidden()
    assert page.input_value('#rfMV') == '2600'


def test_true_bad_input(page, app_url):
    open_editor(page, app_url)
    for yd, val in [('', ''), ('600', ''), ('', '2'), ('0', '2'), ('600', '0'), ('-600', '2'), ('600', '-2')]:
        work(page, yd, val)
        assert out(page) == ASK, (yd, val)
    page.evaluate("() => { document.querySelector('#rfTrueVal').value = 'abc'; }")
    page.fill('#rfTrueYd', '600')
    page.click('#rfTrueGo')
    assert out(page) == ASK
    body = page.inner_text('body')
    for bad in ('NaN', 'Infinity', 'undefined', '-0.0'):
        assert bad not in body
    expect(page.locator('#rfTrueSave')).to_be_hidden()
    assert profiles(page)[0]['mv'] == 2600 and page.input_value('#rfMV') == '2600'


def test_the_rifle_and_conditions_must_be_usable(page, app_url):
    open_editor(page, app_url)
    page.fill('#rfBC', '')
    work(page, 600, 3, 'mil')
    assert out(page) == 'Fill in the rifle and load first.'
    page.fill('#rfBC', '0.3')
    page.fill('#rfZTemp', '500')
    page.click('#rfTrueGo')
    assert out(page) == 'Fill in the rifle and load first.'      # zero conditions out of range
    page.fill('#rfZTemp', '')
    page.evaluate("() => { const t = document.querySelector('#bTemp'); t.value = '900'; }")
    page.click('#rfTrueGo')
    assert out(page) == 'Check the conditions on the Ballistics screen first.'


def test_the_sheet_name_is_not_needed(page, app_url):
    open_editor(page, app_url)
    page.fill('#rfName', '')
    work(page, 600, round(typed(page, shot(page, 2550, 600), 600, 'mil'), 4), 'mil')
    assert out(page).startswith('Velocity 2,600 fps')


def test_uses_todays_conditions_from_the_screen(page, app_url):
    open_editor(page, app_url)
    val = round(typed(page, shot(page, 2550, 600), 600, 'mil'), 4)
    work(page, 600, val, 'mil')
    a = out(page)
    page.evaluate("() => { document.querySelector('#bTemp').value = '10'; document.querySelector('#bAlt').value = '6000'; }")
    page.click('#rfTrueGo')
    assert out(page) != a


def test_true_in_each_unit_agrees(page, app_url):
    open_editor(page, app_url)
    rad = shot(page, 2550, 600)
    got = []
    for unit in ('mil', 'moa', 'iphy', 'in'):
        work(page, 600, round(typed(page, rad, 600, unit), 3), unit)
        got.append(int(out(page).split('→ ')[1].split(' fps')[0].replace(',', '')))
    assert max(got) - min(got) <= 3 and abs(got[0] - 2550) <= 2, got


def test_save_keeps_the_original_and_undo_restores_it(page, app_url):
    open_editor(page, app_url)
    correct(page, 2550)
    page.click('#rfSave')
    expect(page.locator(DLG)).to_be_hidden()
    first = profiles(page)[0]
    assert first['mv0'] == 2600 and abs(first['mv'] - 2550) <= 2
    reopen(page)
    expect(page.locator('#rfTrueUndo')).to_have_text('Put back 2,600 fps')
    correct(page, 2500)
    page.click('#rfSave')
    expect(page.locator(DLG)).to_be_hidden()
    second = profiles(page)[0]
    assert second['mv0'] == 2600 and abs(second['mv'] - 2500) <= 2
    reopen(page)
    page.click('#rfTrueUndo')
    assert page.input_value('#rfMV') == '2600'
    page.click('#rfSave')
    expect(page.locator(DLG)).to_be_hidden()
    last = profiles(page)[0]
    assert last['mv'] == 2600 and 'mv0' not in last
    reopen(page)
    expect(page.locator('#rfTrueUndo')).to_be_hidden()


def test_hand_edits_never_touch_mv0(page, app_url):
    open_editor(page, app_url, profiles=({**OWN, 'mv0': 2900},))
    expect(page.locator('#rfTrueUndo')).to_have_text('Put back 2,900 fps')
    page.fill('#rfMV', '2610')
    page.click('#rfSave')
    expect(page.locator(DLG)).to_be_hidden()
    assert profiles(page)[0]['mv'] == 2610 and profiles(page)[0]['mv0'] == 2900
    fresh_load(page)
    page.fill('#rfMV', '2610')
    page.click('#rfSave')
    expect(page.locator(DLG)).to_be_hidden()
    assert 'mv0' not in profiles(page)[0]


def test_save_as_new_carries_mv0_only_after_a_correction(page, app_url):
    open_editor(page, app_url, profiles=({**OWN, 'mv0': 2900},))
    page.fill('#rfName', 'Copy')
    page.click('#rfSaveNew')
    expect(page.locator(DLG)).to_be_hidden()
    new = [p for p in profiles(page) if p['name'] == 'Copy'][0]
    assert 'mv0' not in new
    assert [p for p in profiles(page) if p['id'] == 'u1'][0]['mv0'] == 2900
    fresh_load(page)
    correct(page, 2550)
    page.fill('#rfName', 'Corrected')
    page.click('#rfSaveNew')
    expect(page.locator(DLG)).to_be_hidden()
    new = [p for p in profiles(page) if p['name'] == 'Corrected'][0]
    assert new['mv0'] == 2600 and abs(new['mv'] - 2550) <= 2
    assert 'mv0' not in [p for p in profiles(page) if p['id'] == 'u1'][0]


def test_typing_a_distance_does_not_make_the_sheet_dirty(page, app_url):
    open_editor(page, app_url)
    page.fill('#rfTrueYd', '600')
    page.fill('#rfTrueVal', '3')
    page.go_back()
    expect(page.locator(DLG)).to_be_hidden()
    expect(page.locator('#dlgConfirm')).to_be_hidden()
    open_editor(page, app_url)
    correct(page, 2550)
    page.go_back()
    expect(page.locator('#cfTitle')).to_have_text('Discard changes to this profile?')


def test_a_pending_value_goes_when_the_sheet_changes(page, app_url):
    open_editor(page, app_url)
    work(page, 600, round(typed(page, shot(page, 2550, 600), 600, 'mil'), 4), 'mil')
    expect(page.locator('#rfTrueSave')).to_be_visible()
    page.fill('#rfBC', '0.31')
    expect(page.locator('#rfTrueSave')).to_be_hidden()
    assert out(page) == ''


@pytest.mark.parametrize('night', [False, True])
def test_layout_at_360_with_large_text(page, app_url, night):
    page.set_viewport_size({'width': 360, 'height': 640})
    ballistics(page, app_url, night=night, profiles=[OWN, {**OWN, 'id': 'u3', 'mv0': 2900}])
    page.evaluate("FK.bal.select('u3')")
    page.click('#bEdit')
    expect(page.locator(DLG)).to_be_visible()
    page.wait_for_timeout(250)
    work(page, 600, round(typed(page, shot(page, 2450, 600), 600, 'mil'), 4), 'mil')
    enlarge_text(page)
    assert too_small(page, DLG) == []
    assert clipped_buttons(page, DLG) == []
    assert overflow(page, DLG) == []


def test_a_result_or_refusal_does_not_survive_closing(page, app_url):
    open_editor(page, app_url)
    work(page, 600, round(typed(page, shot(page, 2550, 600), 600, 'mil'), 4), 'mil')
    assert out(page).startswith('Velocity')
    page.click('#rfCancel')
    reopen(page)
    assert out(page) == ''
    expect(page.locator('#rfTrueSave')).to_be_hidden()
    work(page, 250, 1)
    assert out(page) == NEAR
    page.click('#rfCancel')
    reopen(page)
    assert out(page) == ''
    work(page, 600, round(typed(page, shot(page, 2550, 600), 600, 'mil'), 4), 'mil')
    page.go_back()                                   # Back, nothing in the profile changed
    expect(page.locator(DLG)).to_be_hidden()
    reopen(page)
    assert out(page) == ''
    expect(page.locator('#rfTrueSave')).to_be_hidden()


def leave_and_reopen(page):
    page.click('#rfSave')
    expect(page.locator(DLG)).to_be_hidden()
    reopen(page)


def test_mv0_after_put_back_and_corrections(page, app_url):
    keep = {**LOAD, 'mv0': 2900}
    # put back, then save as new: no mv0 on the copy (the velocity is the original, 2900, not the opened 2600)
    open_editor(page, app_url, profiles=(keep,))
    correct(page, 2500)
    page.click('#rfTrueUndo')
    assert page.input_value('#rfMV') == '2900'
    page.fill('#rfName', 'Back copy')
    page.click('#rfSaveNew')
    expect(page.locator(DLG)).to_be_hidden()
    copy = [p for p in profiles(page) if p['name'] == 'Back copy'][0]
    assert copy['mv'] == 2900 and 'mv0' not in copy
    # put back, correct again, save: the profile's own mv0 stays
    page.wait_for_timeout(450)
    page.evaluate('p => { FK.bal.save(p); FK.bal.select(p.id); }', keep)
    page.click('#bEdit')
    expect(page.locator(DLG)).to_be_visible()
    page.wait_for_timeout(250)
    correct(page, 2500)
    page.click('#rfTrueUndo')
    correct(page, 2800)
    page.click('#rfSave')
    expect(page.locator(DLG)).to_be_hidden()
    got = [p for p in profiles(page) if p['id'] == 'u1'][0]
    assert got['mv0'] == 2900 and abs(got['mv'] - 2800) <= 2
    # a profile with no mv0: correct, hand-edit the velocity back to the opened value, save: none is made
    fresh_load(page)
    correct(page, 2550)
    page.fill('#rfMV', '2600')
    page.click('#rfSave')
    expect(page.locator(DLG)).to_be_hidden()
    got = profiles(page)[0]
    assert got['mv'] == 2600 and 'mv0' not in got
    # the same, saved as a new profile
    reopen(page)
    correct(page, 2550)
    page.fill('#rfMV', '2600')
    page.fill('#rfName', 'Same velocity')
    page.click('#rfSaveNew')
    expect(page.locator(DLG)).to_be_hidden()
    assert 'mv0' not in [p for p in profiles(page) if p['name'] == 'Same velocity'][0]
    # put back leaves nothing pending for a profile that had mv0, even when the velocity field is edited after
    page.wait_for_timeout(450)
    page.evaluate('p => { FK.bal.save(p); FK.bal.select(p.id); }', keep)
    page.click('#bEdit')
    expect(page.locator(DLG)).to_be_visible()
    page.wait_for_timeout(250)
    page.click('#rfTrueUndo')
    page.click('#rfSave')
    expect(page.locator(DLG)).to_be_hidden()
    got = [p for p in profiles(page) if p['id'] == 'u1'][0]
    assert got['mv'] == 2900 and 'mv0' not in got


# ---------- The result is seen and never lost without a question ----------

def boxes(page):
    return page.evaluate("""() => { const r = s => document.querySelector(s).getBoundingClientRect();
      return { body: r('#dlgRifle .mk-body'), act: r('#dlgRifle .mk-act'), out: r('#rfTrueOut'), use: r('#rfTrueSave') }; }""")


def test_work_it_out_brings_the_result_and_use_into_view(page, app_url):
    page.set_viewport_size({'width': 360, 'height': 640})
    open_editor(page, app_url)
    page.locator('#rfTrueGo').scroll_into_view_if_needed()
    work(page, 600, round(typed(page, shot(page, 2550, 600), 600, 'mil'), 4), 'mil')
    page.wait_for_timeout(100)
    b = boxes(page)
    assert b['out']['top'] >= b['body']['top'] and b['use']['bottom'] <= b['body']['bottom'] <= b['act']['top'] + 1, b
    assert b['use']['height'] >= 44
    assert page.get_attribute('#rfTrueOut', 'aria-live') == 'polite'
    # a refusal is brought into view too
    page.locator('#rfTitle').scroll_into_view_if_needed()
    page.evaluate("document.querySelector('#dlgRifle .mk-body').scrollTop = document.querySelector('#rfTrueGo').offsetTop - 300")
    work(page, 250, 1)
    page.wait_for_timeout(100)
    b = boxes(page)
    assert out(page) == NEAR
    assert b['out']['top'] >= b['body']['top'] and b['out']['bottom'] <= b['body']['bottom'], b


def worked(page):
    work(page, 600, round(typed(page, shot(page, 2550, 600), 600, 'mil'), 4), 'mil')
    return int(out(page).split('→ ')[1].split(' fps')[0].replace(',', ''))


@pytest.mark.parametrize('button', ['#rfSave', '#rfSaveNew'])
def test_saving_with_an_unused_result_asks_and_can_use_it(page, app_url, button):
    open_editor(page, app_url)
    mv = worked(page)
    if button == '#rfSaveNew':
        page.fill('#rfName', 'Corrected copy')
        mv = worked(page)                            # typing a name clears the result: work it out again
    page.click(button)
    expect(page.locator('#cfTitle')).to_have_text('Use the corrected velocity?')
    expect(page.locator('#cfText')).to_have_text(f"You worked out {mv:,} fps but haven't used it.")
    expect(page.locator('#cfOk')).to_have_text('Use it and save')
    expect(page.locator('#cfCancel')).to_have_text('Save without it')
    page.click('#cfOk')
    expect(page.locator(DLG)).to_be_hidden()
    expect(page.locator('#dlgConfirm')).to_be_hidden()
    got = [p for p in profiles(page) if p['name'] == ('Mine' if button == '#rfSave' else 'Corrected copy')][0]
    assert got['mv'] == mv and got['mv0'] == 2600
    page.wait_for_timeout(600)
    assert page.evaluate('FK.view()') == 'ballistics'


def test_saving_with_an_unused_result_can_save_without_it(page, app_url):
    open_editor(page, app_url)
    page.fill('#rfBC', '0.25')
    worked(page)
    page.click('#rfSave')
    page.click('#cfCancel')                          # Save without it
    expect(page.locator(DLG)).to_be_hidden()
    got = profiles(page)[0]
    assert got['mv'] == 2600 and got['bc'] == 0.25 and 'mv0' not in got


def test_closing_the_question_saves_nothing_and_keeps_the_sheet(page, app_url):
    open_editor(page, app_url)
    page.evaluate("const g = history.go.bind(history); history.go = k => { setTimeout(() => g(k), 250); }; 0")   # a slow phone
    mv = worked(page)
    page.click('#rfSave')
    expect(page.locator('#cfTitle')).to_have_text('Use the corrected velocity?')
    page.go_back()
    expect(page.locator('#dlgConfirm')).to_be_hidden()
    page.wait_for_timeout(400)
    expect(page.locator(DLG)).to_be_visible()
    assert profiles(page)[0]['mv'] == 2600
    expect(page.locator('#rfTrueSave')).to_have_text(f'Use {mv:,} fps')      # the result is still waiting
    page.click('#rfSave')
    expect(page.locator('#cfTitle')).to_have_text('Use the corrected velocity?')
    page.keyboard.press('Escape')
    expect(page.locator('#dlgConfirm')).to_be_hidden()
    expect(page.locator(DLG)).to_be_visible()
    page.click('#rfSave')
    page.click('#cfOk')
    expect(page.locator(DLG)).to_be_hidden()
    assert profiles(page)[0]['mv'] == mv
    page.wait_for_timeout(800)
    assert page.evaluate('FK.view()') == 'ballistics'


def test_cancel_after_use_asks(page, app_url):
    open_editor(page, app_url)
    correct(page, 2550)
    page.click('#rfCancel')
    expect(page.locator('#cfTitle')).to_have_text('Discard changes to this profile?')
    page.click('#cfCancel')                          # Keep editing
    expect(page.locator(DLG)).to_be_visible()
    assert page.input_value('#rfMV') != '2600'
    page.click('#rfCancel')
    page.click('#cfOk')                              # Discard
    expect(page.locator(DLG)).to_be_hidden()
    assert profiles(page)[0]['mv'] == 2600
