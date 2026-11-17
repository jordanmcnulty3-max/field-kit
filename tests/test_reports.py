import json, os, subprocess, sys

from .test_tools import T0, boot

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NINE = '#/emergency/report/9line'
MIST = '#/emergency/report/mist'
LAT, LON = 38.8977, -77.0365


def fix(age_ms, acc=12):
    return {'lat': LAT, 'lon': LON, 'alt': None, 'acc': acc, 'spd': None, 't': T0 - age_ms}


def geo_stub(mode='deny', delay=0, lat=51.5, lon=-0.12):
    """Replace getCurrentPosition so tests never wait on a real GPS. 'ok' answers after `delay` fake ms."""
    return f"""
      Object.defineProperty(navigator, 'geolocation', {{ configurable: true, value: {{
        getCurrentPosition(ok, err) {{
          setTimeout(() => {{ if ({json.dumps(mode)} === 'ok') ok({{ coords: {{ latitude: {lat}, longitude: {lon}, accuracy: 5 }}, timestamp: Date.now() }}); else err({{ code: 1 }}); }}, {delay});
        }},
        watchPosition() {{ return 1; }}, clearWatch() {{}}
      }} }});"""


def mgrs(page, lat=LAT, lon=LON):
    return page.evaluate(f'GEO.toMGRS({lat}, {lon}).text')


def seed_patient(entries, **kw):
    return [{'id': 'p1', 'name': 'Casualty 1', 'created': T0, 'used': T0, 'entries': entries, **kw}]


def e(t, text, kind='note', **kw):
    return {'t': t, 'kind': kind, 'text': text, **kw}


def test_fresh_fix_prefills_mgrs(page, app_url):
    boot(page, app_url, storage={'lastFix': fix(30_000)}, hash_=NINE, init=geo_stub())
    assert page.input_value('#nl1') == mgrs(page)
    assert page.inner_text('#nlAcc') == '±12 m'
    assert page.input_value('#nlOut').split('\n')[0] == '1. ' + mgrs(page)   # accuracy is shown beside the field, never copied


def test_old_fix_shows_age(page, app_url):
    boot(page, app_url, storage={'lastFix': fix(5 * 60_000)}, hash_=NINE, init=geo_stub())
    assert page.input_value('#nl1') == mgrs(page) + ' (fix 5 min old)'


def test_fix_just_under_two_minutes_is_fresh_and_two_minutes_is_old(page, app_url):
    boot(page, app_url, storage={'lastFix': fix(119_000)}, hash_=NINE, init=geo_stub())
    assert page.input_value('#nl1') == mgrs(page)


def test_exactly_two_minutes_is_labelled(page, app_url):
    boot(page, app_url, storage={'lastFix': fix(120_000)}, hash_=NINE, init=geo_stub())
    assert page.input_value('#nl1') == mgrs(page) + ' (fix 2 min old)'


def test_no_fix_leaves_location_blank(page, app_url):
    boot(page, app_url, hash_=NINE, init=geo_stub())
    assert page.input_value('#nl1') == ''
    assert page.input_value('#nlOut').split('\n')[0] == '1.'
    assert page.inner_text('#nlAcc') == ''


def test_screen_asks_for_its_own_fix_and_refreshes_line_one(page, app_url):
    boot(page, app_url, storage={'lastFix': fix(10 * 60_000)}, hash_=NINE, init=geo_stub('ok', delay=1000))
    assert 'min old' in page.input_value('#nl1')
    page.clock.run_for(1500)
    assert page.input_value('#nl1') == mgrs(page, 51.5, -0.12)
    assert page.inner_text('#nlAcc') == '±5 m'


def test_own_fix_works_without_any_stored_fix(page, app_url):
    boot(page, app_url, hash_=NINE, init=geo_stub('ok', delay=500))
    page.clock.run_for(1000)
    assert page.input_value('#nl1') == mgrs(page, 51.5, -0.12)


def test_typed_location_is_never_overwritten(page, app_url):
    boot(page, app_url, hash_=NINE, init=geo_stub('ok', delay=1000))
    page.fill('#nl1', 'Trailhead lot')
    page.clock.run_for(1500)
    assert page.input_value('#nl1') == 'Trailhead lot'
    assert json.loads(page.evaluate("localStorage.getItem('fk.nineLine')"))['l1'] == 'Trailhead lot'
    page.evaluate("FK.emit('fix', {})")
    assert page.input_value('#nl1') == 'Trailhead lot'


def test_nine_line_text_has_nine_numbered_lines_in_order(page, app_url):
    boot(page, app_url, hash_=NINE, init=geo_stub())
    t = page.evaluate("""FK.reports.nineLine({ l1: '17S QV 123 456', l2: '146.520 Dustoff 2', l3: { A: 2, C: 1 }, l4: ['B', 'D'], l5: { L: 2, A: 1 },
      l6: 'N', l7: 'C', l7x: 'red', l8: 'A', l8x: '', l9: 'Slope\\nrocky' })""")
    lines = t.split('\n')
    assert [x.split('.')[0] for x in lines] == [str(i) for i in range(1, 10)]
    assert lines[0] == '1. 17S QV 123 456'
    assert lines[2] == '3. A Urgent 2, C Priority 1'
    assert lines[3] == '4. B Hoist, D Ventilator'
    assert lines[4] == '5. L Litter 2, A Ambulatory 1'
    assert lines[5] == '6. N No enemy troops in area'
    assert lines[6] == '7. C Smoke signal, red'
    assert lines[7] == '8. A US military'
    assert lines[8] == '9. Slope / rocky'


def test_empty_nine_line_still_reads_every_line_number(page, app_url):
    boot(page, app_url, hash_=NINE, init=geo_stub())
    assert page.evaluate('FK.reports.nineLine({})') == '\n'.join(f'{i}.' for i in range(1, 10))
    assert page.evaluate("FK.reports.nineLine({ l3: { A: -4, B: 1.5, Z: 9 }, l6: 'Q', l4: ['Z'] })") == '\n'.join(f'{i}.' for i in range(1, 10))
    assert page.evaluate('FK.reports.nineLine(null)') == '\n'.join(f'{i}.' for i in range(1, 10))


def test_form_is_filled_by_tapping_and_survives_reload(page, app_url):
    boot(page, app_url, hash_=NINE, init=geo_stub())
    page.fill('#nl2', '146.520 Dustoff')
    page.click('.rp-count[data-n="3"][data-c="A"] [data-step="1"]')
    page.click('.rp-count[data-n="3"][data-c="A"] [data-step="1"]')
    page.click('.rp-count[data-n="3"][data-c="C"] [data-step="1"]')
    page.click('.rp-count[data-n="3"][data-c="C"] [data-step="-1"]')
    page.click('.rp-opt[data-n="4"][data-c="B"]')
    page.click('.rp-opt[data-n="4"][data-c="D"]')
    page.click('.rp-opt[data-n="4"][data-c="A"]')   # None replaces the others
    page.click('.rp-opt[data-n="6"][data-c="N"]')
    page.click('.rp-opt[data-n="6"][data-c="P"]')   # one choice only
    page.fill('#nl9', 'Open field')
    out = page.input_value('#nlOut').split('\n')
    assert out[1] == '2. 146.520 Dustoff' and out[2] == '3. A Urgent 2' and out[3] == '4. A None' and out[5] == '6. P Possible enemy troops' and out[8] == '9. Open field'
    page.click('.rp-opt[data-n="6"][data-c="P"]')   # tap again to unset
    assert page.input_value('#nlOut').split('\n')[5] == '6.'
    page.reload()
    page.wait_for_function('window.FK && FK.tools && FK.tools.cpr')
    page.wait_for_selector('#nlOut')
    assert page.input_value('#nl2') == '146.520 Dustoff'
    assert page.input_value('#nlOut').split('\n')[2] == '3. A Urgent 2'
    assert page.get_attribute('.rp-opt[data-n="4"][data-c="A"]', 'aria-pressed') == 'true'


def test_clear_form_needs_two_taps_and_ignores_a_bounce(page, app_url):
    boot(page, app_url, storage={'nineLine': {'l2': 'keep me'}}, hash_=NINE, init=geo_stub())
    assert page.input_value('#nl2') == 'keep me'
    page.click('#nlClear')
    assert page.inner_text('#nlClear') == 'Confirm clear'
    page.click('#nlClear')   # bounced second tap: ignored
    assert page.input_value('#nl2') == 'keep me'
    page.clock.run_for(800)
    page.click('#nlClear')
    assert page.input_value('#nl2') == ''
    assert json.loads(page.evaluate("localStorage.getItem('fk.nineLine')"))['l2'] == ''
    page.click('#nlClear')
    page.clock.run_for(6000)   # reverts by itself
    assert page.inner_text('#nlClear') == 'Clear form'


def test_clear_form_prefills_location_again(page, app_url):
    boot(page, app_url, storage={'lastFix': fix(1000)}, hash_=NINE, init=geo_stub())
    page.fill('#nl1', 'typed')
    page.click('#nlClear'); page.clock.run_for(800); page.click('#nlClear')
    assert page.input_value('#nl1') == mgrs(page)


def test_stored_nine_line_is_sanitised(page, app_url):
    boot(page, app_url, storage={'nineLine': {'l1': 5, 'l3': 'x', 'l6': 'Z', 'l4': ['B', 'B', 'Q'], 'l2': 'a' * 999}}, hash_=NINE, init=geo_stub())
    out = page.input_value('#nlOut').split('\n')
    assert out[3] == '4. B Hoist' and out[5] == '6.' and len(out[1]) == 3 + 200


def test_nine_line_screen_marks_draft_wording(page, app_url):
    boot(page, app_url, hash_=NINE, init=geo_stub())
    assert 'Draft wording, not source-checked' in page.inner_text('.rp-draft')


def test_touch_targets_are_at_least_56px(page, app_url):
    boot(page, app_url, hash_=NINE, init=geo_stub())
    small = page.evaluate("""[...document.querySelectorAll('#toolBody button, #toolBody input, #toolBody textarea')]
      .filter(b => b.offsetParent && b.getBoundingClientRect().height < 55.5).map(b => b.id || b.className)""")
    assert small == []


def test_mist_pulls_latest_vitals_and_treatments_from_log(page, app_url):
    entries = [
        e(T0 - 600_000, 'Tourniquet applied: Left leg', 'event'),
        e(T0 - 540_000, 'Vitals: pulse 80', 'vitals', pulse=80),
        e(T0 - 300_000, 'Vitals: pulse 92, breathing 16, AVPU V (voice)', 'vitals', pulse=92, resp=16, avpu='V'),
        e(T0 - 120_000, 'Vitals: AVPU P (pain)', 'vitals', avpu='P'),
        e(T0 - 60_000, 'Pressure dressing on chest', 'event'),
        e(T0 - 30_000, 'Just a note', 'note'),
    ]
    boot(page, app_url, storage={'patients': seed_patient(entries, mech='Fell 3 m from a ledge', inj='Open left leg wound')}, hash_=MIST)
    t = page.evaluate("FK.reports.mist('p1')")
    lines = t.split('\n')
    assert len(lines) == 4
    assert lines[0] == 'M: Fell 3 m from a ledge' and lines[1] == 'I: Open left leg wound'
    import re
    assert re.fullmatch(r'S: pulse 92 at \d\d:\d\d, breathing 16 at \d\d:\d\d, AVPU P \(pain\) at \d\d:\d\d', lines[2]), lines[2]
    assert re.fullmatch(r'T: \d\d:\d\d Tourniquet applied: Left leg; \d\d:\d\d Pressure dressing on chest', lines[3]), lines[3]
    assert page.input_value('#msOut') == t


def test_mist_with_empty_log_says_not_recorded(page, app_url):
    boot(page, app_url, storage={'patients': seed_patient([])}, hash_=MIST)
    assert page.evaluate("FK.reports.mist('p1')") == 'M: not recorded\nI: not recorded\nS: not recorded\nT: not recorded'
    assert page.evaluate("FK.reports.mist('nope')") == ''


def test_mist_fields_are_remembered_per_casualty(page, app_url):
    two = seed_patient([]) + [{'id': 'p2', 'name': 'Casualty 2', 'created': T0, 'used': T0 - 1, 'entries': []}]
    boot(page, app_url, storage={'patients': two}, hash_=MIST)
    page.fill('#msM', 'Rollover')
    page.fill('#msI', 'Head cut')
    assert page.input_value('#msOut').split('\n')[:2] == ['M: Rollover', 'I: Head cut']
    page.clock.run_for(500)
    saved = json.loads(page.evaluate("localStorage.getItem('fk.patients')"))
    assert saved[0]['mech'] == 'Rollover' and saved[0]['inj'] == 'Head cut' and 'mech' not in saved[1]
    page.select_option('#msSel', 'p2')
    assert page.input_value('#msM') == '' and page.input_value('#msOut').startswith('M: not recorded')
    page.select_option('#msSel', 'p1')
    assert page.input_value('#msM') == 'Rollover'


def test_mist_text_is_flushed_when_closing_before_the_save_delay(page, app_url):
    boot(page, app_url, storage={'patients': seed_patient([])}, hash_=MIST)
    page.fill('#msM', 'Quick')
    page.click('#toolClose')
    saved = json.loads(page.evaluate("localStorage.getItem('fk.patients')"))
    assert saved[0]['mech'] == 'Quick'


def test_patient_mech_and_inj_validation(page, app_url):
    pts = seed_patient([], mech='x' * 3000, inj=5)
    boot(page, app_url, storage={'patients': pts}, hash_=MIST)
    p = page.evaluate("FK.patients.all()[0]")
    assert len(p['mech']) == 2000 and 'inj' not in p
    assert page.evaluate("FK.patients.setMist('p1', { mech: '', inj: 'ok' })") is True
    p = page.evaluate("FK.patients.all()[0]")
    assert 'mech' not in p and p['inj'] == 'ok'
    assert page.evaluate("FK.patients.setMist('missing', { mech: 'a' })") is False


def test_copy_uses_clipboard_when_it_works(page, app_url):
    boot(page, app_url, hash_=NINE, init=geo_stub() + "window.__copied = null; Object.defineProperty(navigator, 'clipboard', { configurable: true, value: { writeText: async t => { window.__copied = t; } } });")
    page.fill('#nl2', 'Dustoff')
    page.click('[data-rp="copy"]')
    page.wait_for_function('window.__copied !== null')
    assert page.evaluate('window.__copied') == page.input_value('#nlOut')
    assert 'Copied' in page.inner_text('#toast')


def test_copy_falls_back_to_selecting_the_text(page, app_url):
    boot(page, app_url, hash_=NINE, init=geo_stub() + "Object.defineProperty(navigator, 'clipboard', { configurable: true, value: { writeText: async () => { throw new Error('refused'); } } });")
    page.click('[data-rp="copy"]')
    page.wait_for_function("document.activeElement && document.activeElement.id === 'nlOut'")
    assert page.evaluate("document.getElementById('nlOut').selectionEnd - document.getElementById('nlOut').selectionStart") == len(page.input_value('#nlOut'))
    assert 'selected' in page.inner_text('#toast')


def test_copy_without_clipboard_api_does_not_throw(page, app_url):
    boot(page, app_url, hash_=MIST, init="Object.defineProperty(navigator, 'clipboard', { configurable: true, value: undefined });")
    page.click('[data-rp="copy"]')
    assert 'selected' in page.inner_text('#toast')


def test_share_button_only_when_share_exists(page, app_url):
    boot(page, app_url, hash_=NINE, init=geo_stub() + "Object.defineProperty(navigator, 'share', { configurable: true, value: undefined });")
    assert page.locator('[data-rp="share"]').count() == 0


def test_share_sends_the_report_text(page, app_url):
    boot(page, app_url, hash_=NINE, init=geo_stub() + "window.__shared = null; navigator.share = async d => { window.__shared = d; };")
    page.fill('#nl2', 'Dustoff')
    page.click('[data-rp="share"]')
    page.wait_for_function('window.__shared !== null')
    assert page.evaluate('window.__shared.text') == page.input_value('#nlOut')


def test_reports_buttons_on_home_open_the_overlay_and_close_returns(page, app_url):
    boot(page, app_url, init=geo_stub())
    page.click('summary[data-cat="reports"]')
    page.click('#emReports [data-tool="9line"]')
    page.wait_for_selector('#toolPane:not([hidden])')
    assert page.evaluate('location.hash') == NINE
    assert page.inner_text('#toolTitle') == 'MEDEVAC 9-line'
    page.click('#toolClose')
    page.wait_for_selector('#toolPane', state='hidden')
    assert page.evaluate('location.hash') == '#/emergency'
    assert page.evaluate("document.querySelector('details[data-cat=reports]').open")
    page.click('#emReports [data-tool="mist"]')
    assert page.inner_text('#toolTitle') == 'MIST report'
    page.go_back()
    page.wait_for_selector('#toolPane', state='hidden')


def test_report_address_does_not_open_the_protocol_player(page, app_url):
    boot(page, app_url, hash_=MIST)
    assert page.locator('#toolPane').is_visible() and not page.locator('#player').is_visible()


def test_unknown_report_address_goes_home(page, app_url):
    boot(page, app_url, hash_='#/emergency/report/nope')
    page.wait_for_function("location.hash === '#/emergency'")
    assert not page.locator('#toolPane').is_visible()
    boot_hash = '#/emergency/tool/9line'   # a report is not a tool address
    page.goto(page.url.split('#')[0] + boot_hash)
    page.wait_for_function("location.hash === '#/emergency'")


def test_reports_pin_and_recent_use_r_keys(page, app_url):
    boot(page, app_url, hash_=NINE, init=geo_stub())
    page.click('#toolPin')
    assert json.loads(page.evaluate("localStorage.getItem('fk.pins')")) == ['r:9line']
    assert 'r:9line' in json.loads(page.evaluate("localStorage.getItem('fk.recent')"))
    page.click('#toolClose')
    assert 'MEDEVAC 9-line' in page.inner_text('#emPinned')
    assert 'MEDEVAC 9-line' in page.inner_text('#emRecent')
    page.click('#emPinned [data-tool="9line"]')
    assert page.evaluate('location.hash') == NINE


def test_wrong_key_prefix_for_a_report_or_tool_is_not_rendered(page, app_url):
    boot(page, app_url, storage={'pins': ['t:9line', 'r:log', 'r:mist', 'x:mist']})
    txt = page.inner_text('#emPinned')
    assert 'MIST report' in txt and 'MEDEVAC' not in txt and 'Patient log' not in txt


def test_backup_includes_the_form(page, app_url):
    boot(page, app_url, hash_=NINE, init=geo_stub())
    page.fill('#nl2', 'backup me')
    keys = page.evaluate("Object.keys(localStorage).filter(k => k.startsWith('fk.'))")
    assert 'fk.nineLine' in keys   # backup copies every fk.-prefixed key


def test_release_build_fails_while_wording_is_draft(tmp_path):
    r = subprocess.run([sys.executable, os.path.join(ROOT, 'build.py'), '--release', str(tmp_path)], capture_output=True, text=True)
    assert r.returncode != 0 and 'REPORT_WORDING_DRAFT' in r.stderr + r.stdout


def test_normal_build_still_works_while_draft(tmp_path):
    r = subprocess.run([sys.executable, os.path.join(ROOT, 'build.py'), str(tmp_path)], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
