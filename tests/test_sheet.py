"""Sheets: one history entry each, Back/Escape/backdrop close them, and the six browser pop-ups are gone."""
import glob, os, re

from playwright.sync_api import expect

from .conftest import ROOT
from .tac import store, open_map, open_track, open_save

WP = {'id': 'w1', 'name': 'Camp', 'lat': 43.0, 'lon': -76.0, 'alt': None, 't': 1}
PROFILE = {'id': 'u1', 'name': 'Mine', 'bc': 0.3, 'model': 'G1', 'w': 150, 'mv': 2800, 'sight': 1.5, 'zero': 100}
AREA = {'id': 'a1', 'name': 'Home', 'layer': 'topo', 's': 43.0, 'w': -76.3, 'n': 43.08, 'e': -76.0,
        'zMin': 5, 'zMax': 14, 'tiles': 10, 'bytes': 1000}


def boot(page, app_url, hash_='#/tactical/map'):
    """An entry from outside the app first, so an overshoot would leave Field Kit."""
    page.goto('about:blank')
    store(page, wps=[WP], profiles=[PROFILE], areas=[AREA], advAck=True)
    page.goto(app_url + hash_)
    page.wait_for_function('window.FK && FK.sheet && FK.route')


def wps(page):
    return page.evaluate("JSON.parse(localStorage.getItem('fk.wps') || '[]')")


def test_no_browser_dialogs_in_source():
    bad = []
    for f in glob.glob(os.path.join(ROOT, 'src', '*.js')):
        for n, line in enumerate(open(f, encoding='utf-8'), 1):
            if re.search(r'\b(prompt|confirm|alert)\(', line.replace('installEvt.prompt()', '').replace('FK.sheet.confirm(', '')):
                bad.append(f'{os.path.basename(f)}:{n}: {line.strip()}')
    assert bad == []


def test_mark_opens_the_marker_sheet_and_cancel_adds_nothing(page, app_url):
    boot(page, app_url)
    page.click('#mMark')
    expect(page.locator('#dlgMarker')).to_be_visible()
    expect(page.locator('#mkName')).to_have_value('WP 2')
    page.click('#mkCancel')
    expect(page.locator('#dlgMarker')).to_be_hidden()
    assert [w['id'] for w in wps(page)] == ['w1']


def test_mark_save_adds_the_trimmed_name_and_empty_takes_the_default(page, app_url):
    boot(page, app_url)
    page.click('#mMark')
    page.fill('#mkName', '  Ridge  ')
    page.click('#mkSave')
    expect(page.locator('#dlgMarker')).to_be_hidden()
    page.click('#mMark')
    page.fill('#mkName', '   ')
    page.click('#mkSave')
    expect(page.locator('#dlgMarker')).to_be_hidden()
    assert [w['name'] for w in wps(page)] == ['Camp', 'Ridge', 'WP 3']


def test_back_closes_the_sheet_and_stays_on_the_map(page, app_url):
    boot(page, app_url)
    before = page.evaluate('[history.state.fkIdx, FK.route.index()]')
    page.click('#mMark')
    expect(page.locator('#dlgMarker')).to_be_visible()
    assert page.evaluate('history.state.fkSheet') == 'dlgMarker'
    assert page.evaluate('history.state.fkIdx') == before[0]
    page.go_back()
    expect(page.locator('#dlgMarker')).to_be_hidden()
    assert page.evaluate('location.hash') == '#/tactical/map'
    assert page.evaluate('[history.state.fkIdx, FK.route.index(), history.state.fkSheet === undefined]') == [*before, True]
    page.go_back()
    assert page.url == 'about:blank'


def test_closing_by_button_steps_back_off_its_entry(page, app_url):
    boot(page, app_url)
    page.click('#mMark')
    page.click('#mkCancel')
    page.wait_for_function('history.state.fkSheet === undefined')
    page.go_back()
    assert page.url == 'about:blank'


def test_popping_a_sheet_does_not_rerender_the_screen(page, app_url):
    boot(page, app_url, '#/tactical/position')
    page.evaluate("window.__n = 0; FK.on('route', () => window.__n++); FK.on('history', () => window.__n++)")
    page.evaluate("void FK.sheet.ask({ title: 'T', label: 'L' })")
    expect(page.locator('#dlgAsk')).to_be_visible()
    page.go_back()
    expect(page.locator('#dlgAsk')).to_be_hidden()
    page.wait_for_timeout(100)
    assert page.evaluate('window.__n') == 0


def test_sheets_stack_and_back_closes_one_per_press(page, app_url):
    boot(page, app_url)
    page.evaluate("FK.sheet.open(document.querySelector('#dlgLayers'))")
    page.evaluate("void FK.sheet.confirm({ title: 'Sure?', ok: 'Go' })")
    expect(page.locator('#dlgConfirm')).to_be_visible()
    assert page.evaluate('FK.sheet.top().id') == 'dlgConfirm'
    page.go_back()
    expect(page.locator('#dlgConfirm')).to_be_hidden()
    expect(page.locator('#dlgLayers')).to_be_visible()
    assert page.evaluate('FK.sheet.top().id') == 'dlgLayers'
    page.go_back()
    expect(page.locator('#dlgLayers')).to_be_hidden()
    assert page.evaluate('FK.sheet.top()') is None
    assert page.evaluate('location.hash') == '#/tactical/map'


def test_backdrop_tap_closes_but_a_tap_on_the_sheet_does_not(page, app_url):
    boot(page, app_url)
    page.evaluate("FK.sheet.open(document.querySelector('#dlgLayers'))")
    box = page.locator('#dlgLayers').bounding_box()
    page.mouse.click(box['x'] + 2, box['y'] + 2)   # on the dialog's own padding
    expect(page.locator('#dlgLayers')).to_be_visible()
    page.mouse.click(2, 2)                          # on the backdrop
    expect(page.locator('#dlgLayers')).to_be_hidden()
    page.wait_for_function('history.state.fkSheet === undefined')


def test_on_close_runs_once(page, app_url):
    boot(page, app_url)
    page.evaluate("window.__c = 0; FK.sheet.open(document.querySelector('#dlgLayers'), { onClose: () => window.__c++ })")
    page.keyboard.press('Escape')
    expect(page.locator('#dlgLayers')).to_be_hidden()
    page.wait_for_timeout(100)
    assert page.evaluate('window.__c') == 1


def test_delete_marker_needs_confirm_and_default_is_cancel(page, app_url):
    boot(page, app_url)
    page.evaluate("FK.markers.edit('w1')")
    page.click('#mkDel')
    dlg = page.locator('#dlgConfirm')
    expect(dlg).to_be_visible()
    assert page.evaluate('document.activeElement.textContent.trim()') == 'Cancel'
    expect(dlg.locator('[data-act="ok"]')).to_have_text('Delete marker')
    page.keyboard.press('Enter')
    expect(dlg).to_be_hidden()
    expect(page.locator('#dlgMarker')).to_be_visible()
    assert len(wps(page)) == 1
    page.click('#mkDel')
    page.click('#dlgConfirm [data-act="ok"]')
    expect(dlg).to_be_hidden()
    expect(page.locator('#dlgMarker')).to_be_hidden()
    assert wps(page) == []


def test_clear_track(page, app_url):
    store(page, track=[[43.0, -76.0, None, 1], [43.001, -76.0, None, 2]])
    boot(page, app_url)
    open_track(page)
    page.click('#trkClear')
    expect(page.locator('#dlgConfirm [data-act="ok"]')).to_have_text('Clear track')
    page.click('#dlgConfirm [data-act="cancel"]')
    assert page.evaluate("JSON.parse(localStorage.getItem('fk.track')).length") == 2
    expect(page.locator('#dlgTrack')).to_be_visible()   # still on the Track sheet underneath
    page.click('#trkClear')
    page.click('#dlgConfirm [data-act="ok"]')
    expect(page.locator('#dlgConfirm')).to_be_hidden()
    assert page.evaluate("JSON.parse(localStorage.getItem('fk.track')).length") == 0


def test_delete_saved_map(page, app_url):
    boot(page, app_url)
    open_save(page)
    page.click('#areaList [data-area="del"]')
    expect(page.locator('#dlgConfirm [data-act="ok"]')).to_have_text('Delete saved map')
    page.click('#dlgConfirm [data-act="cancel"]')
    assert page.evaluate("JSON.parse(localStorage.getItem('fk.areas')).length") == 1
    page.click('#areaList [data-area="del"]')
    page.click('#dlgConfirm [data-act="ok"]')
    page.wait_for_function("JSON.parse(localStorage.getItem('fk.areas')).length === 0")


def open_editor(page, profile_id):
    page.evaluate('id => FK.bal.select(id)', profile_id)
    page.click('#bEdit')
    expect(page.locator('#dlgRifle')).to_be_visible()


def test_save_profile_name(page, app_url):
    """New profiles are made in the profile editor (Save as new profile) and named there; there is no separate name sheet."""
    boot(page, app_url, '#/tactical/ballistics')
    open_editor(page, 'p308')
    expect(page.locator('#rfName')).to_have_value('Federal Gold Medal .308 Win 175 gr SMK, 24″ barrel (mine)')   # a name of its own
    page.click('#rfCancel')
    expect(page.locator('#dlgRifle')).to_be_hidden()
    assert len(page.evaluate("JSON.parse(localStorage.getItem('fk.profiles'))")) == 1
    page.click('#bEdit')
    page.fill('#rfName', 'Second')
    page.click('#rfSaveNew')
    page.wait_for_function("JSON.parse(localStorage.getItem('fk.profiles')).length === 2")
    assert page.evaluate("JSON.parse(localStorage.getItem('fk.profiles'))[1].name") == 'Second'


def test_delete_profile(page, app_url):
    boot(page, app_url, '#/tactical/ballistics')
    open_editor(page, 'u1')
    page.click('#rfDelete')
    expect(page.locator('#dlgConfirm [data-act="ok"]')).to_have_text('Delete profile')
    page.click('#dlgConfirm [data-act="cancel"]')
    assert len(page.evaluate("JSON.parse(localStorage.getItem('fk.profiles'))")) == 1
    expect(page.locator('#dlgRifle')).to_be_visible()      # still on the editor underneath
    page.click('#rfDelete')
    page.click('#dlgConfirm [data-act="ok"]')
    page.wait_for_function("JSON.parse(localStorage.getItem('fk.profiles')).length === 0")


def test_escape_cancels_ask(page, app_url):
    boot(page, app_url)
    page.evaluate("window.__r = 'pending'; void FK.sheet.ask({ title: 'T', label: 'L', value: 'x' }).then(v => { window.__r = v; })")
    expect(page.locator('#dlgAsk')).to_be_visible()
    page.keyboard.press('Escape')
    page.wait_for_function('window.__r === null')
    assert [w['id'] for w in wps(page)] == ['w1']


def test_helper_open_map_loads_the_map(page, app_url):
    open_map(page, app_url)
    assert page.evaluate('location.hash') == '#/tactical/map'


def test_marker_wording_in_delete_confirm(page, app_url):
    boot(page, app_url)
    page.evaluate("FK.markers.edit('w1')")
    page.click('#mkDel')
    expect(page.locator('#cfText')).to_have_text('Delete marker Camp? This can’t be undone.')


def test_confirm_right_after_another_sheet_closes_resolves_with_the_answer(page, app_url):
    boot(page, app_url)
    page.evaluate("FK.sheet.open(document.querySelector('#dlgLayers'))")
    page.evaluate("document.querySelector('#layersClose').click(); window.__p = FK.sheet.confirm({ title: 'T', ok: 'Go' }); window.__r = 'pending'; void window.__p.then(v => { window.__r = v; })")
    expect(page.locator('#dlgConfirm')).to_be_visible()
    page.click('#dlgConfirm [data-act="ok"]')
    page.wait_for_function('window.__r === true')
    expect(page.locator('#dlgConfirm')).to_be_hidden()
    page.wait_for_function('history.state.fkSheet === undefined')
    assert page.evaluate('FK.sheet.top()') is None
    page.go_back()
    assert page.url == 'about:blank'


def test_second_ask_in_the_same_tick_resolves_null_and_first_keeps_its_text(page, app_url):
    boot(page, app_url)
    page.evaluate("""window.__a = 'pending'; window.__b = 'pending';
      FK.sheet.ask({ title: 'A', label: 'L' }).then(v => { window.__a = v; });
      void FK.sheet.ask({ title: 'B', label: 'L' }).then(v => { window.__b = v; });""")
    page.wait_for_function('window.__b === null')
    expect(page.locator('#dlgAsk h2')).to_have_text('A')
    page.fill('#dlgAsk input', 'typed')
    page.click('#dlgAsk [data-act="ok"]')
    page.wait_for_function("window.__a === 'typed'")
    assert page.evaluate('window.__b') is None


def test_open_that_cannot_show_leaves_stack_and_history_alone(page, app_url):
    boot(page, app_url)
    before = page.evaluate('[history.length, history.state.fkIdx]')
    page.evaluate("window.__c = 0; const d = document.querySelector('#dlgLayers'); d.show(); FK.sheet.open(d, { onClose: () => window.__c++ })")
    page.wait_for_timeout(100)
    assert page.evaluate('window.__c') == 1
    assert page.evaluate('FK.sheet.top()') is None
    assert page.evaluate('[history.length, history.state.fkIdx, history.state.fkSheet === undefined]') == [*before, True]
    page.evaluate("document.querySelector('#dlgLayers').close()")


def test_navigating_while_a_sheet_is_open_closes_it_and_back_returns(page, app_url):
    boot(page, app_url)
    page.evaluate("FK.sheet.open(document.querySelector('#dlgLayers'))")
    page.evaluate("FK.route.go('/tactical/position')")
    expect(page.locator('#dlgLayers')).to_be_hidden()
    assert page.evaluate('FK.sheet.top()') is None
    assert page.evaluate('location.hash') == '#/tactical/position'
    page.go_back()
    page.wait_for_function("location.hash === '#/tactical/map' && FK.view() === 'map'")
    page.wait_for_function('history.state.fkSheet === undefined')
    expect(page.locator('#dlgLayers')).to_be_hidden()
    assert page.evaluate('FK.route.index()') == page.evaluate('history.state.fkIdx')
    page.go_back()
    assert page.url == 'about:blank'


def test_opening_search_while_a_sheet_is_open_closes_it(page, app_url):
    boot(page, app_url)
    page.evaluate("FK.sheet.open(document.querySelector('#dlgLayers'))")
    page.evaluate("FK.route.go('/search')")
    expect(page.locator('#dlgLayers')).to_be_hidden()
    assert page.evaluate('FK.sheet.top()') is None


def settle_sheets(page):
    """Let a sheet's history step finish (it settles on popstate, or after its 500 ms fallback)."""
    page.evaluate("new Promise(r => setTimeout(r, 700))")


def assert_navigated_cleanly(page):
    assert page.evaluate('location.hash') == '#/tactical/position'
    assert page.evaluate("[...document.querySelectorAll('dialog')].filter(d => d.open).length") == 0
    assert page.evaluate('FK.route.index() === history.state.fkIdx')
    assert page.evaluate('FK.route.current().parts[0]') == 'position'
    page.go_back()
    page.wait_for_function("location.hash === '#/tactical/map'")


def test_navigating_in_the_same_tick_as_closing_a_sheet_lands_on_the_new_screen(page, app_url):
    boot(page, app_url)
    page.evaluate("FK.sheet.open(document.querySelector('#dlgTrack'))")
    page.evaluate("() => { FK.sheet.close(document.querySelector('#dlgTrack')); FK.route.go('/tactical/position'); }")
    settle_sheets(page)
    assert_navigated_cleanly(page)


def test_navigating_right_after_a_sheet_button_click_lands_on_the_new_screen(page, app_url):
    boot(page, app_url)
    open_track(page)
    page.evaluate("() => { document.querySelector('#trkClose').click(); FK.route.go('/tactical/position'); }")
    settle_sheets(page)
    assert_navigated_cleanly(page)


# ---------- Layers: a non-dialog screen state (a map tool mode) that owns one history entry, so Back leaves it ----------

LAYER = """window.__ends = []; window.__backs = 0; window.__keep = false;
  window.__L = FK.sheet.layer('t', { onBack: () => { window.__backs++; return window.__keep ? () => { window.__kept = true; } : false; },
                                      onEnd: why => window.__ends.push(why) });"""


def idx_ok(page):
    return page.evaluate('FK.route.index() === history.state.fkIdx')


def test_layer_owns_one_entry_and_back_ends_it(page, app_url):
    boot(page, app_url)
    n = page.evaluate('history.length')
    page.evaluate(LAYER)
    page.wait_for_function("String(history.state.fkLayer).startsWith('t.')")
    assert page.evaluate('history.length') == n + 1
    assert page.evaluate('__L.active()') is True
    page.go_back()
    page.wait_for_function('window.__ends.length === 1')
    assert page.evaluate('window.__ends') == ['back']
    assert page.evaluate('__L.active()') is False
    assert page.evaluate('history.state.fkLayer === undefined') and idx_ok(page)
    assert page.evaluate('location.hash') == '#/tactical/map'
    page.go_back()
    assert page.url == 'about:blank'


def test_layer_close_steps_back_off_its_entry_without_calling_on_end(page, app_url):
    boot(page, app_url)
    page.evaluate(LAYER)
    page.wait_for_function("String(history.state.fkLayer).startsWith('t.')")
    page.evaluate('__L.close()')
    page.wait_for_function('history.state.fkLayer === undefined')
    settle_sheets(page)
    assert page.evaluate('window.__ends') == [] and page.evaluate('__L.active()') is False
    assert idx_ok(page) and page.evaluate('location.hash') == '#/tactical/map'
    page.go_back()
    assert page.url == 'about:blank'


def test_layer_on_back_can_keep_the_layer(page, app_url):
    boot(page, app_url)
    page.evaluate(LAYER + 'window.__keep = true;')
    page.wait_for_function("String(history.state.fkLayer).startsWith('t.')")
    page.go_back()
    page.wait_for_function('window.__kept === true')
    assert page.evaluate("history.state.fkLayer").startswith('t.') and page.evaluate('__L.active()') is True
    assert page.evaluate('window.__ends') == [] and idx_ok(page)
    page.evaluate('window.__keep = false')
    page.go_back()
    page.wait_for_function('window.__ends.length === 1')
    assert idx_ok(page)


def test_sheet_over_a_layer_closes_by_back_and_the_layer_stays(page, app_url):
    boot(page, app_url)
    page.evaluate(LAYER)
    page.wait_for_function("String(history.state.fkLayer).startsWith('t.')")
    page.evaluate("FK.sheet.open(document.querySelector('#dlgLayers'))")
    expect(page.locator('#dlgLayers')).to_be_visible()
    page.go_back()
    expect(page.locator('#dlgLayers')).to_be_hidden()
    page.wait_for_function("String(history.state.fkLayer).startsWith('t.') && history.state.fkSheet === undefined")
    assert page.evaluate('__L.active()') is True and page.evaluate('window.__backs') == 0


def test_layer_close_right_after_a_sheet_closes_takes_both_steps(page, app_url):
    boot(page, app_url)
    page.evaluate(LAYER)
    page.wait_for_function("String(history.state.fkLayer).startsWith('t.')")
    page.evaluate("FK.sheet.open(document.querySelector('#dlgLayers'))")
    expect(page.locator('#dlgLayers')).to_be_visible()
    page.evaluate("FK.sheet.close(document.querySelector('#dlgLayers')); __L.close()")
    page.wait_for_function('history.state.fkLayer === undefined && history.state.fkSheet === undefined')
    settle_sheets(page)
    assert idx_ok(page) and page.evaluate('window.__ends') == []
    page.go_back()
    assert page.url == 'about:blank'


def test_navigating_while_a_layer_is_on_ends_it_and_back_returns_to_the_map(page, app_url):
    boot(page, app_url)
    page.evaluate(LAYER)
    page.wait_for_function("String(history.state.fkLayer).startsWith('t.')")
    page.evaluate("FK.route.go('/tactical/position')")
    assert page.evaluate('window.__ends') == ['nav'] and page.evaluate('__L.active()') is False
    page.go_back()
    page.wait_for_function("location.hash === '#/tactical/map' && history.state.fkLayer === undefined")
    assert idx_ok(page)
    page.go_back()
    assert page.url == 'about:blank'


def test_reload_on_a_layer_entry_drops_the_marker(page, app_url):
    boot(page, app_url)
    page.evaluate(LAYER)
    page.wait_for_function("String(history.state.fkLayer).startsWith('t.')")
    page.reload()
    page.wait_for_function('window.FK && FK.sheet')
    assert page.evaluate('history.state.fkLayer === undefined') and idx_ok(page)


def test_layer_on_back_can_open_a_confirm_that_stays_open(page, app_url):
    boot(page, app_url)
    page.evaluate("""window.__r = 'pending'; window.__L = FK.sheet.layer('t', { onBack: () => () => {
      FK.sheet.confirm({ title: 'Leave?', ok: 'Leave' }).then(v => { window.__r = v; if (v) window.__L.close(); }); } });""")
    page.wait_for_function("String(history.state.fkLayer).startsWith('t.')")
    page.go_back()
    expect(page.locator('#dlgConfirm')).to_be_visible()
    page.click('#cfOk')
    page.wait_for_function('window.__r === true && !history.state.fkLayer && !history.state.fkSheet')
    page.wait_for_timeout(100)
    assert page.evaluate('FK.route.index() === history.state.fkIdx')
    page.go_back()
    assert page.url == 'about:blank'


def test_layer_close_with_a_sheet_open_on_top_closes_both(page, app_url):
    boot(page, app_url)
    page.evaluate(LAYER)
    page.wait_for_function("String(history.state.fkLayer).startsWith('t.')")
    page.evaluate("FK.sheet.open(document.querySelector('#dlgLayers'))")
    expect(page.locator('#dlgLayers')).to_be_visible()
    page.evaluate('__L.close()')
    page.wait_for_function('!history.state.fkLayer && !history.state.fkSheet')
    settle_sheets(page)
    assert page.evaluate("[...document.querySelectorAll('dialog')].filter(d => d.open).length") == 0
    assert page.evaluate('FK.sheet.top()') is None and idx_ok(page)
    # a new layer afterwards ends on one Back, and Back again leaves the app as before
    page.evaluate(LAYER)
    page.wait_for_function("String(history.state.fkLayer).startsWith('t.')")
    page.go_back()
    page.wait_for_function('window.__ends.length === 1')
    assert idx_ok(page) and page.evaluate('location.hash') == '#/tactical/map'
    page.go_back()
    assert page.url == 'about:blank'


def test_each_layer_gets_its_own_entry_id(page, app_url):
    boot(page, app_url)
    ids = page.evaluate("""async () => { const a = FK.sheet.layer('t', {}); await new Promise(r => setTimeout(r, 50)); const x = history.state.fkLayer;
      a.close(); await new Promise(r => setTimeout(r, 200)); FK.sheet.layer('t', {}); await new Promise(r => setTimeout(r, 50)); return [x, history.state.fkLayer]; }""")
    assert ids[0] != ids[1] and all(i.startswith('t.') for i in ids)


# ---------- The same dialog closed and opened again at once (a confirm after a confirm, a tap right after Close) ----------

REOPEN = """async () => {
  const d = document.querySelector('#dlgLayers');
  FK.sheet.open(d);
  await new Promise(r => setTimeout(r, 50));
  FK.sheet.close(d); FK.sheet.open(d);   // same tick
  await new Promise(r => setTimeout(r, 100));
  const ok = d.open && FK.sheet.top() === d && history.state.fkSheet === 'dlgLayers' && FK.route.index() === history.state.fkIdx;
  FK.sheet.close(d);
  await new Promise(r => setTimeout(r, 100));
  return ok && !d.open && !history.state.fkSheet;
}"""


def test_reopening_the_same_sheet_in_the_same_tick_keeps_it_open(page, app_url):
    boot(page, app_url)
    n = page.evaluate('history.length')
    fails = sum(0 if page.evaluate(REOPEN) else 1 for _ in range(20))
    assert fails == 0, f'{fails} of 20'
    page.evaluate("FK.sheet.close(document.querySelector('#dlgLayers'))")
    page.wait_for_timeout(100)
    # Back closes a reopened sheet, and only one entry was ever left for it
    page.evaluate("(async () => { const d = document.querySelector('#dlgLayers'); FK.sheet.open(d); await new Promise(r => setTimeout(r, 50)); FK.sheet.close(d); FK.sheet.open(d); })()")
    page.wait_for_timeout(150)
    expect(page.locator('#dlgLayers')).to_be_visible()
    page.go_back()
    expect(page.locator('#dlgLayers')).to_be_hidden()
    page.wait_for_function('!history.state.fkSheet')
    assert page.evaluate('FK.route.index() === history.state.fkIdx')
    page.go_back()
    assert page.url == 'about:blank'


CONFIRM_TWICE = """async () => {
  // history.go()'s popstate can take a while under load (sheet.js allows 3 s): poll, never a fixed sleep.
  const until = async (f, ms = 4000) => { const end = performance.now() + ms; while (!f()) { if (performance.now() > end) return false; await new Promise(r => setTimeout(r, 10)); } return true; };
  window.__second = 'pending';
  const first = FK.sheet.confirm({ title: 'One', ok: 'Yes' });
  await until(() => document.querySelector('#dlgConfirm').open && document.querySelector('#cfTitle').textContent === 'One');
  document.querySelector('#cfOk').click();
  const a = await first;
  const second = FK.sheet.confirm({ title: 'Two', ok: 'Yes' });   // in the continuation
  second.then(v => { window.__second = v; });
  const open = await until(() => document.querySelector('#dlgConfirm').open && document.querySelector('#cfTitle').textContent === 'Two');
  if (open) document.querySelector('#cfOk').click();
  await until(() => window.__second !== 'pending' && !history.state.fkSheet);
  return a === true && open && window.__second === true && FK.route.index() === history.state.fkIdx && !history.state.fkSheet;
}"""


def test_a_confirm_right_after_a_confirm_stays_open_and_answers(page, app_url):
    boot(page, app_url)
    fails = sum(0 if page.evaluate(CONFIRM_TWICE) else 1 for _ in range(20))
    assert fails == 0, f'{fails} of 20'


def test_escape_and_a_plain_close_still_end_the_sheet_entry(page, app_url):
    boot(page, app_url)
    page.evaluate("FK.sheet.open(document.querySelector('#dlgLayers'))")
    page.wait_for_function("history.state.fkSheet === 'dlgLayers'")
    page.keyboard.press('Escape')
    page.wait_for_function('!history.state.fkSheet && FK.sheet.top() === null')
    page.evaluate("FK.sheet.open(document.querySelector('#dlgLayers'))")
    page.wait_for_function("history.state.fkSheet === 'dlgLayers'")
    page.evaluate("document.querySelector('#dlgLayers').close()")
    page.wait_for_function('!history.state.fkSheet && FK.sheet.top() === null')
    assert page.evaluate('FK.route.index() === history.state.fkIdx')
    page.go_back()
    assert page.url == 'about:blank'


def test_a_confirm_with_two_choices_tells_a_close_from_either_choice(page, app_url):
    """choice: true resolves 'ok' or 'cancel' for the two buttons and null when the sheet is closed any other way."""
    boot(page, app_url)
    page.evaluate("const g = history.go.bind(history); history.go = k => { setTimeout(() => g(k), 250); }; 0")   # a slow phone
    ask = "window.__r = 'pending'; void FK.sheet.confirm({ title: 'Which?', ok: 'A', cancel: 'B', choice: true }).then(v => { window.__r = v; })"
    for how, want in [('#cfOk', 'ok'), ('#cfCancel', 'cancel'), ('back', None), ('Escape', None)]:
        page.wait_for_timeout(400)
        page.evaluate(ask)
        expect(page.locator('#dlgConfirm')).to_be_visible()
        expect(page.locator('#cfOk')).to_have_text('A')
        expect(page.locator('#cfCancel')).to_have_text('B')
        assert page.evaluate('document.activeElement.id') == 'cfTitle'      # neither choice is taken by a stray Enter
        if how == 'back':
            page.go_back()
        elif how == 'Escape':
            page.keyboard.press('Escape')
        else:
            page.click(how)
        expect(page.locator('#dlgConfirm')).to_be_hidden()
        page.wait_for_function("window.__r !== 'pending'")
        assert page.evaluate('window.__r') == want, how
    page.wait_for_timeout(400)
    # without choice the answer is still true or false
    page.evaluate("window.__r = 'pending'; void FK.sheet.confirm({ title: 'Sure?', ok: 'Go' }).then(v => { window.__r = v; })")
    assert page.evaluate('document.activeElement.id') == 'cfCancel'
    page.go_back()
    page.wait_for_function("window.__r !== 'pending'")
    assert page.evaluate('window.__r') is False
