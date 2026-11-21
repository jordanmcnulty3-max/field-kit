"""Tactical layout (v7.8, design section 9): Position and Ballistics headings and spacing match the v7.6 home standard,
Ballistics gives the same numbers as before the restyle, and all three Tactical views and every v7.8 sheet fit a 360 px
phone in day and night, with every control at least 44 px and nothing cut off when text is enlarged."""
import pytest
from playwright.sync_api import expect

from .tac import store
from .test_map import tiles_ok
from .test_nav import boot, position, fix, ev, mk, HOME
from .test_position import NO_SHARE, CLIP_STUB
from .test_tac_io import import_sheet, counts_kml
from .test_tactical_existing import go

# What Ballistics showed before the restyle: captured from commit a190ff5 (the build before any v7.8 task-12 change) by reading
# #solElev, #solWind, #solSub and the text of the dope card table. default_*: the starting profile (.308 Win 175 gr SMK) with
# the default inputs (500 yd, 10 mph from 3 o'clock). p556_*: the 5.56 NATO 62 gr starting point at 300 yd with a 10 mph wind
# from 9 o'clock. mil / moa: the unit switch. Nothing here was worked out by hand. (The table shows -0.0 in the Drop column at
# 100 yd; that is how it was, and it is kept as captured.)
BEFORE = {'default_mil': {'e': 'U 3.6 mil',
                 'w': 'R 1.2 mil',
                 's': 'At 500 yd: drop 64.3 in, drift 21.9 in, 1761 fps, 1205 ft-lb, 0.70 s flight.',
                 't': 'Yd\tElev mil\tWind mil\tDrop in\tDrift in\tfps\tft-lb\tTime s\n'
                      '50\t0.0\tR 0.1\t-0.1\t0.2\t2508\t2444\t0.06\n'
                      '100\t0.0\tR 0.2\t-0.0\t0.8\t2417\t2271\t0.12\n'
                      '150\tU 0.3\tR 0.3\t-1.4\t1.7\t2329\t2108\t0.18\n'
                      '200\tU 0.6\tR 0.4\t-4.5\t3.1\t2242\t1954\t0.25\n'
                      '250\tU 1.0\tR 0.6\t-9.2\t5.0\t2158\t1810\t0.32\n'
                      '300\tU 1.5\tR 0.7\t-15.8\t7.3\t2075\t1674\t0.39\n'
                      '350\tU 1.9\tR 0.8\t-24.5\t10.1\t1994\t1546\t0.46\n'
                      '400\tU 2.5\tR 0.9\t-35.3\t13.5\t1915\t1425\t0.54\n'
                      '450\tU 3.0\tR 1.1\t-48.5\t17.4\t1837\t1312\t0.62\n'
                      '500\tU 3.6\tR 1.2\t-64.3\t21.9\t1761\t1205\t0.70\n'
                      '550\tU 4.2\tR 1.4\t-82.9\t27.1\t1686\t1105\t0.79\n'
                      '600\tU 4.8\tR 1.5\t-104.5\t32.9\t1613\t1011\t0.88\n'
                      '650\tU 5.5\tR 1.7\t-129.5\t39.5\t1541\t923\t0.97\n'
                      '700\tU 6.3\tR 1.9\t-158.2\t46.9\t1470\t840\t1.07\n'
                      '750\tU 7.1\tR 2.0\t-190.8\t55.2\t1401\t763\t1.18\n'
                      '800\tU 7.9\tR 2.2\t-227.9\t64.3\t1333\t691\t1.29\n'
                      '850\tU 8.8\tR 2.4\t-269.9\t74.5\t1268\t625\t1.40\n'
                      '900\tU 9.8\tR 2.6\t-317.4\t85.7\t1204\t564\t1.53\n'
                      '950\tU 10.8\tR 2.9\t-370.8\t98.1\t1144\t509\t1.65\n'
                      '1000\tU 12.0\tR 3.1\t-430.8\t111.6\t1091\t463\t1.79'},
 'default_moa': {'e': 'U 12.3 MOA',
                 'w': 'R 4.2 MOA',
                 's': 'At 500 yd: drop 64.3 in, drift 21.9 in, 1761 fps, 1205 ft-lb, 0.70 s flight.',
                 't': 'Yd\tElev MOA\tWind MOA\tDrop in\tDrift in\tfps\tft-lb\tTime s\n'
                      '50\tU 0.1\tR 0.4\t-0.1\t0.2\t2508\t2444\t0.06\n'
                      '100\t0.0\tR 0.7\t-0.0\t0.8\t2417\t2271\t0.12\n'
                      '150\tU 0.9\tR 1.1\t-1.4\t1.7\t2329\t2108\t0.18\n'
                      '200\tU 2.1\tR 1.5\t-4.5\t3.1\t2242\t1954\t0.25\n'
                      '250\tU 3.5\tR 1.9\t-9.2\t5.0\t2158\t1810\t0.32\n'
                      '300\tU 5.0\tR 2.3\t-15.8\t7.3\t2075\t1674\t0.39\n'
                      '350\tU 6.7\tR 2.8\t-24.5\t10.1\t1994\t1546\t0.46\n'
                      '400\tU 8.4\tR 3.2\t-35.3\t13.5\t1915\t1425\t0.54\n'
                      '450\tU 10.3\tR 3.7\t-48.5\t17.4\t1837\t1312\t0.62\n'
                      '500\tU 12.3\tR 4.2\t-64.3\t21.9\t1761\t1205\t0.70\n'
                      '550\tU 14.4\tR 4.7\t-82.9\t27.1\t1686\t1105\t0.79\n'
                      '600\tU 16.6\tR 5.2\t-104.5\t32.9\t1613\t1011\t0.88\n'
                      '650\tU 19.0\tR 5.8\t-129.5\t39.5\t1541\t923\t0.97\n'
                      '700\tU 21.6\tR 6.4\t-158.2\t46.9\t1470\t840\t1.07\n'
                      '750\tU 24.3\tR 7.0\t-190.8\t55.2\t1401\t763\t1.18\n'
                      '800\tU 27.2\tR 7.7\t-227.9\t64.3\t1333\t691\t1.29\n'
                      '850\tU 30.3\tR 8.4\t-269.9\t74.5\t1268\t625\t1.40\n'
                      '900\tU 33.7\tR 9.1\t-317.4\t85.7\t1204\t564\t1.53\n'
                      '950\tU 37.3\tR 9.9\t-370.8\t98.1\t1144\t509\t1.65\n'
                      '1000\tU 41.1\tR 10.7\t-430.8\t111.6\t1091\t463\t1.79'},
 'p556_mil': {'e': 'U 1.0 mil',
              'w': 'L 0.9 mil',
              's': 'At 300 yd: drop 10.3 in, drift 9.9 in, 2138 fps, 630 ft-lb, 0.35 s flight.',
              't': 'Yd\tElev mil\tWind mil\tDrop in\tDrift in\tfps\tft-lb\tTime s\n'
                   '50\tU 0.4\tL 0.1\t-0.8\t0.2\t2860\t1126\t0.05\n'
                   '100\t0.0\tL 0.3\t-0.0\t1.0\t2706\t1008\t0.10\n'
                   '150\tU 0.1\tL 0.4\t-0.4\t2.3\t2557\t900\t0.16\n'
                   '200\tU 0.3\tL 0.6\t-2.2\t4.2\t2413\t802\t0.22\n'
                   '250\tU 0.6\tL 0.7\t-5.4\t6.7\t2273\t712\t0.29\n'
                   '300\tU 1.0\tL 0.9\t-10.3\t9.9\t2138\t630\t0.35\n'
                   '350\tU 1.4\tL 1.1\t-17.2\t13.9\t2008\t555\t0.43\n'
                   '400\tU 1.8\tL 1.3\t-26.2\t18.8\t1882\t488\t0.50\n'
                   '450\tU 2.3\tL 1.5\t-37.6\t24.5\t1762\t428\t0.59\n'
                   '500\tU 2.9\tL 1.7\t-51.9\t31.3\t1648\t374\t0.67\n'
                   '550\tU 3.5\tL 2.0\t-69.3\t39.1\t1540\t326\t0.77\n'
                   '600\tU 4.2\tL 2.2\t-90.4\t48.1\t1439\t285\t0.87\n'
                   '650\tU 4.9\tL 2.5\t-115.8\t58.4\t1346\t250\t0.98\n'
                   '700\tU 5.8\tL 2.8\t-145.9\t69.9\t1262\t219\t1.09\n'
                   '750\tU 6.7\tL 3.1\t-181.5\t82.7\t1189\t195\t1.21\n'
                   '800\tU 7.8\tL 3.4\t-223.2\t96.8\t1127\t175\t1.34\n'
                   '850\tU 8.9\tL 3.7\t-271.8\t112.1\t1075\t159\t1.48\n'
                   '900\tU 10.1\tL 4.0\t-327.9\t128.4\t1032\t147\t1.62\n'
                   '950\tU 11.5\tL 4.3\t-392.1\t145.8\t996\t136\t1.77\n'
                   '1000\tU 12.9\tL 4.6\t-465.2\t164.0\t964\t128\t1.93'},
 'p556_moa': {'e': 'U 3.3 MOA',
              'w': 'L 3.2 MOA',
              's': 'At 300 yd: drop 10.3 in, drift 9.9 in, 2138 fps, 630 ft-lb, 0.35 s flight.',
              't': 'Yd\tElev MOA\tWind MOA\tDrop in\tDrift in\tfps\tft-lb\tTime s\n'
                   '50\tU 1.5\tL 0.5\t-0.8\t0.2\t2860\t1126\t0.05\n'
                   '100\t0.0\tL 0.9\t-0.0\t1.0\t2706\t1008\t0.10\n'
                   '150\tU 0.3\tL 1.5\t-0.4\t2.3\t2557\t900\t0.16\n'
                   '200\tU 1.0\tL 2.0\t-2.2\t4.2\t2413\t802\t0.22\n'
                   '250\tU 2.1\tL 2.6\t-5.4\t6.7\t2273\t712\t0.29\n'
                   '300\tU 3.3\tL 3.2\t-10.3\t9.9\t2138\t630\t0.35\n'
                   '350\tU 4.7\tL 3.8\t-17.2\t13.9\t2008\t555\t0.43\n'
                   '400\tU 6.2\tL 4.5\t-26.2\t18.8\t1882\t488\t0.50\n'
                   '450\tU 8.0\tL 5.2\t-37.6\t24.5\t1762\t428\t0.59\n'
                   '500\tU 9.9\tL 6.0\t-51.9\t31.3\t1648\t374\t0.67\n'
                   '550\tU 12.0\tL 6.8\t-69.3\t39.1\t1540\t326\t0.77\n'
                   '600\tU 14.4\tL 7.7\t-90.4\t48.1\t1439\t285\t0.87\n'
                   '650\tU 17.0\tL 8.6\t-115.8\t58.4\t1346\t250\t0.98\n'
                   '700\tU 19.9\tL 9.5\t-145.9\t69.9\t1262\t219\t1.09\n'
                   '750\tU 23.1\tL 10.5\t-181.5\t82.7\t1189\t195\t1.21\n'
                   '800\tU 26.6\tL 11.6\t-223.2\t96.8\t1127\t175\t1.34\n'
                   '850\tU 30.5\tL 12.6\t-271.8\t112.1\t1075\t159\t1.48\n'
                   '900\tU 34.8\tL 13.6\t-327.9\t128.4\t1032\t147\t1.62\n'
                   '950\tU 39.4\tL 14.7\t-392.1\t145.8\t996\t136\t1.77\n'
                   '1000\tU 44.4\tL 15.7\t-465.2\t164.0\t964\t128\t1.93'}}


# ---------- helpers ----------

def ballistics(page, app_url, night=False, **kv):
    """Open the Ballistics screen with the page clock left alone (the screen recalculates on a 150 ms timer)."""
    page.goto('about:blank')
    tiles_ok(page)
    store(page, **{'advAck': True, 'night': night, 'mapFollow': False, **kv})
    page.goto(app_url + '#/tactical/ballistics')
    page.wait_for_function('window.FK && FK.sheet && FK.view && FK.view() === "ballistics"')
    page.wait_for_selector('#dope tr')


def readout(page):
    return page.evaluate("""() => ({ e: document.querySelector('#solElev').textContent, w: document.querySelector('#solWind').textContent,
      s: document.querySelector('#solSub').textContent, t: document.querySelector('#dope').innerText })""")


def settle(page):
    page.wait_for_timeout(450)   # the 150 ms recalculation timer plus a margin


def set_unit(page, unit):
    page.click(f'#unitSeg [data-unit="{unit}"]')
    settle(page)


def style_of(page, sel):
    return page.evaluate("""s => { const c = getComputedStyle(document.querySelector(s));
      return { size: c.fontSize, weight: c.fontWeight, color: c.color, transform: c.textTransform, spacing: c.letterSpacing, top: c.marginTop }; }""", sel)


def home_heading_style(page, app_url):
    """The Survival home's section heading (Topics), as computed here, in the page's current theme."""
    page.goto(app_url + '#/survival')
    page.wait_for_selector('#survTopics h2.sv-cat')
    return style_of(page, '#survTopics h2.sv-cat')


def home_section_gap(page):
    return page.evaluate("getComputedStyle(document.querySelector('#survTopics')).marginTop")


LUM = """c => { const f = v => { v /= 255; return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4); };
  return 0.2126 * f(c[0]) + 0.7152 * f(c[1]) + 0.0722 * f(c[2]); }"""


def contrast_ratio(page, fg, bg):
    return page.evaluate("""([fg, bg]) => { const L = %s; const a = L(fg), b = L(bg); return (Math.max(a, b) + .05) / (Math.min(a, b) + .05); }""" % LUM, [fg, bg])


def text_contrasts(page, root_sel):
    """Colour contrast of every element under root that has its own visible text, against the first opaque background above it."""
    return page.evaluate("""root => {
      const L = %s, rgb = s => { const n = (s.match(/[\\d.]+/g) || []).map(Number); return s.startsWith('color(srgb') ? [n[0] * 255, n[1] * 255, n[2] * 255, n[3]] : n; };
      const bgOf = el => { for (let e = el; e; e = e.parentElement) { const c = rgb(getComputedStyle(e).backgroundColor);
        if (c.length === 3 || c[3] > 0.5) return c.slice(0, 3); } return rgb(getComputedStyle(document.body).backgroundColor).slice(0, 3); };
      const out = [];
      for (const el of document.querySelector(root).querySelectorAll('*')) {
        if (!el.getBoundingClientRect().width) continue;
        if (![...el.childNodes].some(n => n.nodeType === 3 && n.textContent.trim())) continue;
        const fg = rgb(getComputedStyle(el).color).slice(0, 3), bg = bgOf(el), a = L(fg), b = L(bg);
        out.push({ el: el.tagName + (el.id ? '#' + el.id : '') + '.' + el.className + ' "' + el.textContent.trim().slice(0, 20) + '"', ratio: (Math.max(a, b) + .05) / (Math.min(a, b) + .05) });
      }
      return out; }""" % LUM, root_sel)


OVERFLOW_JS = """root => {
  /* Elements wider than the screen, and elements whose content is wider than their own box. Skipped on purpose: the map
     (Leaflet's panes are meant to run past the edge), the dope card's scroll box and what is inside it (it says it scrolls
     sideways), the marker list's kind chips and the box that holds them (a full-width scroll strip), the text inside a field, text that ends in an ellipsis, and #view-map's own content box (the
     map runs edge to edge past the screen's side padding on purpose; its parts are measured one by one). */
  const bad = [], W = window.innerWidth, name = el => el.tagName + (el.id ? '#' + el.id : '') + '.' + el.className;
  for (const el of root.querySelectorAll('*')) {
    if (el.closest('#map') || el.closest('.mk-chips')) continue;
    const tw = el.closest('.tablewrap');
    const r = el.getBoundingClientRect();
    if (!r.width && !r.height) continue;
    if (el.classList.contains('vh')) continue;
    if (r.right > W + 1 || r.left < -1) { if (!tw || el === tw) bad.push(name(el) + ' box ' + Math.round(r.left) + '..' + Math.round(r.right)); continue; }
    if (tw || el.id === 'view-map' || el.querySelector(':scope > .mk-chips')) continue;
    if (['INPUT', 'TEXTAREA', 'SELECT'].includes(el.tagName)) continue;   // a long value in a field scrolls inside it
    if (getComputedStyle(el).textOverflow === 'ellipsis') continue;
    if (el.clientWidth > 0 && el.scrollWidth > el.clientWidth + 1) bad.push(name(el) + ' content ' + el.scrollWidth + ' > ' + el.clientWidth);
  }
  if (document.documentElement.scrollWidth > W) bad.push('page scrolls sideways ' + document.documentElement.scrollWidth);
  return bad; }"""


def overflow(page, root_sel):
    return page.evaluate("s => (" + OVERFLOW_JS + ")(document.querySelector(s))", root_sel)


def too_small(page, root_sel):
    """Visible buttons, inputs, selects and textareas under root smaller than 44 x 44 (a checkbox counts by its label row)."""
    return page.evaluate("""root => {
      const bad = [];
      for (const el of document.querySelector(root).querySelectorAll('button, input, select, textarea')) {
        if (el.closest('#map') || el.closest('[hidden]')) continue;
        let t = el;
        if (el.type === 'checkbox' || el.type === 'radio') t = el.closest('label') || el;
        const r = t.getBoundingClientRect();
        if (!r.width && !r.height) continue;
        if (r.height < 43.5 || r.width < 43.5) bad.push(el.tagName + '#' + el.id + '.' + el.className + ' ' + Math.round(r.width) + 'x' + Math.round(r.height));
      }
      return bad; }""", root_sel)


def clipped_buttons(page, root_sel):
    return page.evaluate("""root => [...document.querySelector(root).querySelectorAll('button')]
      .filter(b => b.getBoundingClientRect().width && b.scrollWidth > b.clientWidth + 1)
      .map(b => '#' + b.id + ' ' + b.textContent.trim() + ' ' + b.scrollWidth + ' > ' + b.clientWidth)""", root_sel)


def enlarge_text(page):
    """Stand in for the phone's text size setting, which the app does not have. Setting the root font size to 22px (as asked)
    changes nothing by itself, because the app's sizes are in px, so each element is also scaled from 16px to 22px (x 1.375)
    from its own computed size; that is what Android's font scale does. Safe to call twice: it scales from the first size."""
    page.evaluate("""() => {
      document.documentElement.style.fontSize = '22px';
      const all = [...document.querySelectorAll('body *')];
      for (const el of all) if (el.dataset.fs0 === undefined) el.dataset.fs0 = parseFloat(getComputedStyle(el).fontSize);   // read every size first
      for (const el of all) el.style.fontSize = (el.dataset.fs0 * 22 / 16) + 'px'; }""")


# ---------- Ballistics: the restyle changed no number ----------

def test_default_profile_output_is_what_it_was_before_the_restyle(page, app_url):
    ballistics(page, app_url)
    assert readout(page) == BEFORE['default_mil']
    set_unit(page, 'moa')
    assert readout(page) == BEFORE['default_moa']


def test_second_profile_output_is_what_it_was_before_the_restyle(page, app_url):
    ballistics(page, app_url)
    page.select_option('#bProfile', 'p556')
    page.fill('#bRange', '300')
    page.fill('#bWind', '10')
    page.select_option('#bClock', '9')
    settle(page)
    assert readout(page) == BEFORE['p556_mil']
    set_unit(page, 'moa')
    assert readout(page) == BEFORE['p556_moa']


def test_the_dope_card_is_a_real_table_with_all_columns(page, app_url):
    """Guards the capture above against being an empty string on both sides."""
    ballistics(page, app_url)
    assert page.locator('#dope tbody tr').count() >= 20
    assert page.locator('#dope th').count() == 8


# ---------- Headings and spacing: the home standard ----------

@pytest.mark.parametrize('night', [False, True], ids=['day', 'night'])
def test_tactical_headings_match_the_survival_home_heading(page, app_url, night):
    store(page, advAck=True, night=night)
    home = home_heading_style(page, app_url)
    assert home['transform'] == 'uppercase' and float(home['size'][:-2]) < 16   # the reference is what v7.6 made it
    gap = home_section_gap(page)
    go(page, '/tactical/ballistics')
    page.wait_for_function('FK.view() === "ballistics"')
    heads = page.locator('#view-ballistics h2')
    expect(heads).to_have_text(['Shot', 'Rifle and load', 'Conditions', 'Dope card'])
    for i in range(heads.count()):
        h = heads.nth(i)
        h.evaluate('(e, i) => e.setAttribute("data-t12", i)', i)
        assert style_of(page, f'[data-t12="{i}"]') == home, h.inner_text()
    go(page, '/tactical/position')
    page.wait_for_function('FK.view() === "position"')
    pos = page.locator('#view-position h2:not(.nv-name)')
    expect(pos).to_have_text(['Position', 'Compass', 'Markers'])
    for i in range(pos.count()):
        pos.nth(i).evaluate('(e, i) => e.setAttribute("data-t12", i)', i)
        assert style_of(page, f'[data-t12="{i}"]') == home, pos.nth(i).inner_text()
    # the space above each section is the home's: 32 px, and the heading is still the first thing inside it
    sections = page.evaluate("""() => [...document.querySelectorAll('#view-position h2:not(.nv-name)')].map(h => {
      const s = h.closest('.pos-sec'); return getComputedStyle(s).marginTop; })""")
    assert sections[1:] == [gap, gap]
    go(page, '/tactical/ballistics')
    page.wait_for_function('FK.view() === "ballistics"')
    tops = page.evaluate("""() => [...document.querySelectorAll('#view-ballistics h2')].map(h => getComputedStyle(h.parentElement).marginTop)""")
    assert tops == [gap] * 4


def test_ballistics_sections_have_clear_space_above_like_the_home(page, app_url):
    ballistics(page, app_url)
    gaps = page.evaluate("""() => [...document.querySelectorAll('#view-ballistics h2')].map(h => {
      let prev = h.parentElement.previousElementSibling;
      while (prev && !prev.getBoundingClientRect().height) prev = prev.previousElementSibling;
      return h.getBoundingClientRect().top - prev.getBoundingClientRect().bottom; })""")
    assert len(gaps) == 4 and all(g >= 24 for g in gaps), gaps


def test_ballistics_fields_did_not_move(page, app_url):
    """Same fields, same order, same ids, in the same sections."""
    ballistics(page, app_url)
    got = page.evaluate("""() => [...document.querySelectorAll('#view-ballistics h2')].map(h => [h.textContent,
      [...h.parentElement.querySelectorAll('input, select, button')].map(e => e.id)])""")
    assert got == [
        ['Shot', ['bRange', 'bAngle', 'bWind', 'bClock']],
        ['Rifle and load', ['bProfile', 'bBC', 'bModel', 'bW', 'bMV', 'bSH', 'bZero', 'bSave', 'bDel']],
        ['Conditions', ['bTemp', 'bAlt', 'bPress', 'bRH']],
        ['Dope card', ['bMax', 'bStep']],
    ]
    ids = page.evaluate("[...document.querySelectorAll('#view-ballistics [id]')].map(e => e.id)")
    assert ids == ['solution', 'solElev', 'solWind', 'solSub', 'unitSeg', 'bRange', 'bAngle', 'bWind', 'bClock', 'bProfile', 'bBC', 'bModel',
                   'bW', 'bMV', 'bSH', 'bZero', 'bSave', 'bDel', 'bTemp', 'bAlt', 'bPress', 'bRH', 'bMax', 'bStep', 'dope']


# ---------- Ballistics behaviour ----------

def test_profile_save_load_and_delete(page, app_url):
    ballistics(page, app_url)
    page.fill('#bBC', '0.4')
    page.fill('#bMV', '2900')
    settle(page)
    page.click('#bSave')
    expect(page.locator('#dlgAsk')).to_be_visible()
    expect(page.locator('#askTitle')).to_have_text('Name this profile')
    page.fill('#askInput', 'Range rifle')
    page.click('#askOk')
    expect(page.locator('#dlgAsk')).to_be_hidden()
    assert page.evaluate("JSON.parse(localStorage.getItem('fk.profiles')).map(p => [p.name, p.bc, p.mv])") == [['Range rifle', 0.4, 2900]]
    expect(page.locator('#bProfile option:checked')).to_have_text('Range rifle')
    expect(page.locator('#bDel')).to_be_visible()
    # load another profile, then come back to the saved one
    page.select_option('#bProfile', 'p556')
    settle(page)
    assert page.input_value('#bBC') == '0.304' and page.input_value('#bMV') == '3020'
    expect(page.locator('#bDel')).to_be_hidden()
    mine = page.evaluate("JSON.parse(localStorage.getItem('fk.profiles'))[0].id")
    page.select_option('#bProfile', mine)
    settle(page)
    assert page.input_value('#bBC') == '0.4' and page.input_value('#bMV') == '2900'
    # delete goes through the confirm sheet; Cancel keeps it, Delete removes it
    page.click('#bDel')
    expect(page.locator('#dlgConfirm')).to_be_visible()
    expect(page.locator('#cfTitle')).to_have_text('Delete the profile?')
    page.click('#cfCancel')
    expect(page.locator('#dlgConfirm')).to_be_hidden()
    assert page.evaluate("JSON.parse(localStorage.getItem('fk.profiles')).length") == 1
    page.click('#bDel')
    page.click('#cfOk')
    expect(page.locator('#dlgConfirm')).to_be_hidden()
    assert page.evaluate("JSON.parse(localStorage.getItem('fk.profiles')).length") == 0
    expect(page.locator('#bProfile option:checked')).to_have_text('Custom (unsaved)')
    expect(page.locator('#bDel')).to_be_hidden()


def test_switching_mil_and_moa_changes_the_units_and_back(page, app_url):
    ballistics(page, app_url)
    expect(page.locator('#solElev small')).to_have_text('mil')
    set_unit(page, 'moa')
    expect(page.locator('#solElev small')).to_have_text('MOA')
    assert 'Elev MOA' in page.locator('#dope th').nth(1).inner_text()
    expect(page.locator('#unitSeg [data-unit="moa"]')).to_have_attribute('aria-selected', 'true')
    set_unit(page, 'mil')
    expect(page.locator('#solElev small')).to_have_text('mil')
    assert readout(page) == BEFORE['default_mil']


# ---------- Night: everything on the Ballistics screen can be read ----------

def test_contrast_check_can_fail(page, app_url):
    ballistics(page, app_url)
    assert contrast_ratio(page, [14, 1, 1], [0, 0, 0]) < 1.2    # near-black on black: unreadable
    assert contrast_ratio(page, [255, 79, 66], [0, 0, 0]) > 4.5   # the night ink on black


@pytest.mark.parametrize('night', [False, True], ids=['day', 'night'])
def test_ballistics_text_is_readable(page, app_url, night):
    ballistics(page, app_url, night=night)
    rows = text_contrasts(page, '#view-ballistics')
    assert len(rows) > 40
    weak = [r for r in rows if r['ratio'] < 4.5]
    assert weak == []
    page.evaluate("document.querySelector('#bProfile').scrollIntoView()")
    heads = [r for r in rows if r['el'].startswith('H2')]
    assert len(heads) == 4
    if night:
        assert page.evaluate("document.documentElement.dataset.theme") == 'night'


# ---------- Layout at 360 px, day and night ----------

def tactical_boot(page, app_url, view, night):
    """Map, Position or Ballistics with enough on it to be busy: markers, a route, a target being walked to, a fix."""
    if view == 'ballistics':
        return ballistics(page, app_url, night=night)
    markers = [mk(f'w{i}', f'Marker with a fairly long name number {i}', HOME[0] + i * 0.001, HOME[1]) for i in range(1, 8)]
    route = {'id': 'r1', 'type': 'route', 'name': 'Route one', 'pts': [[HOME[0] + 0.003, HOME[1]], [HOME[0] + 0.003, HOME[1] + 0.003]], 't': 1}
    boot(page, app_url, markers=markers, shapes=[route], night=night, decl_mode=None)
    fix(page, *HOME)
    ev(page, "FK.tac.setTarget({ type: 'marker', id: 'w1' })")
    if view == 'position':
        position(page)


@pytest.mark.parametrize('night', [False, True], ids=['day', 'night'])
@pytest.mark.parametrize('view', ['map', 'position', 'ballistics'])
def test_view_fits_360px(page, app_url, view, night):
    tactical_boot(page, app_url, view, night)
    assert page.viewport_size['width'] == 360
    assert page.evaluate('FK.view()') == view
    if view == 'map':
        box = page.locator('#map').bounding_box()
        assert box['x'] >= 0 and box['x'] + box['width'] <= 361
    assert overflow(page, '#tab-tactical') == []
    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
    assert page.evaluate("document.documentElement.dataset.theme === 'night'") == night


@pytest.mark.parametrize('night', [False, True], ids=['day', 'night'])
@pytest.mark.parametrize('view', ['map', 'position', 'ballistics'])
def test_view_fits_with_enlarged_text(page, app_url, view, night):
    tactical_boot(page, app_url, view, night)
    enlarge_text(page)
    assert overflow(page, '#tab-tactical') == []
    assert [b for b in clipped_buttons(page, '#tab-tactical') if not b.startswith('#mLayers')] == []


# The v7.8 controls on the three views, by id (comment markers in src/shell.html: v7.8 markers, units, tools, nav, position, io, iphone).
V78_POSITION = ['#declSeg [data-decl="auto"]', '#declSeg [data-decl="manual"]', '#shareBtn', '#wpName', '#wpMark', '#wpCoord', '#wpAdd',
                '#wpOpenList', '#posExport', '#wakeBtn', '#nvPrev', '#nvNext', '#nvStop']
V78_MAP = ['#mTools', '#mList', '#navStrip']


@pytest.mark.parametrize('night', [False, True], ids=['day', 'night'])
def test_v78_position_controls_are_44px_and_tappable(page, app_url, night):
    tactical_boot(page, app_url, 'position', night)
    ev(page, "FK.tac.setTarget({ type: 'route', id: 'r1' })")
    page.click('#declSeg [data-decl="manual"]')
    seen = []
    for sel in V78_POSITION + ['#decl']:
        loc = page.locator(sel)
        if loc.count() == 0 or not loc.first.is_visible():
            continue
        b = loc.first.bounding_box()
        seen.append(sel)
        assert b['height'] >= 44 and b['width'] >= 44, (sel, b)
    assert {'#shareBtn', '#wpMark', '#posExport', '#nvStop', '#decl', '#declSeg [data-decl="auto"]'} <= set(seen)


@pytest.mark.parametrize('night', [False, True], ids=['day', 'night'])
def test_v78_map_controls_are_44px_and_tappable(page, app_url, night):
    tactical_boot(page, app_url, 'map', night)
    expect(page.locator('#navStrip')).to_be_visible()
    for sel in V78_MAP:
        b = page.locator(sel).bounding_box()
        assert b['height'] >= 44 and b['width'] >= 44, (sel, b)
    # the Measure tool's bar, and the strip Go to grid leaves on the map
    page.click('#mTools')
    page.click('#dlgTools [data-tool="measure"]')
    expect(page.locator('#toolBar')).to_be_visible()
    page.click('#tbAdd')
    shown = [sel for sel in ['#tbAdd', '#tbPlace', '#tbUndo', '#tbSaveRoute', '#tbDone', '#tbCancel'] if page.locator(sel).is_visible()]
    assert {'#tbAdd', '#tbUndo', '#tbSaveRoute', '#tbDone'} <= set(shown)
    for sel in shown:
        b = page.locator(sel).bounding_box()
        assert b['height'] >= 44 and b['width'] >= 44, (sel, b)
    assert too_small(page, '#toolBar') == []
    assert overflow(page, '#tab-tactical') == []
    enlarge_text(page)
    assert overflow(page, '#tab-tactical') == []
    assert clipped_buttons(page, '#toolBar') == []
    page.click('#tbDone')
    expect(page.locator('#toolBar')).to_be_hidden()
    page.evaluate("FK.tac.setTarget(null)")
    page.click('#mTools')
    page.click('#dlgTools [data-tool="goto"]')
    page.fill('#gtInput', '%s, %s' % (HOME[0] + 0.01, HOME[1]))
    page.click('#gtGo')
    expect(page.locator('#dlgGoto')).to_be_hidden()
    b = page.locator('#mMark').bounding_box()
    assert b['height'] >= 44 and b['width'] >= 44, b
    assert overflow(page, '#tab-tactical') == []


# ---------- The v7.8 sheets at 360 px and with enlarged text ----------

def sheet_markers_new(page):
    page.click('#mMark')
    return '#dlgMarker'


def sheet_markers_edit(page):
    page.click('#mList')
    page.click('#lsList [data-id]')
    return '#dlgMarker'


def sheet_list(page):
    page.click('#mList')
    return '#dlgList'


def sheet_tools(page):
    page.click('#mTools')
    return '#dlgTools'


def sheet_shape(page):
    page.click('#mList')
    page.click('#lsList [data-shape]')
    return '#dlgShape'


def sheet_ring(page):
    page.click('#mTools')
    page.click('#dlgTools [data-tool="ring"]')
    return '#dlgRing'


def sheet_goto(page):
    page.click('#mTools')
    page.click('#dlgTools [data-tool="goto"]')
    return '#dlgGoto'


def sheet_export(page):
    page.click('#mTools')
    page.click('#dlgTools [data-tool="export"]')
    return '#dlgExport'


def sheet_import(page):
    import_sheet(page, 'many.kml', counts_kml())
    return '#dlgImport'


def sheet_share(page):
    position(page)
    page.click('#shareBtn')
    return '#dlgShare'


def sheet_ask(page):
    go(page, '/tactical/ballistics')
    page.wait_for_function('FK.view() === "ballistics"')
    page.click('#bSave')
    return '#dlgAsk'


def sheet_confirm(page):
    go(page, '/tactical/ballistics')
    page.wait_for_function('FK.view() === "ballistics"')
    page.select_option('#bProfile', 'u1')
    page.click('#bDel')
    return '#dlgConfirm'


SHEETS = [sheet_markers_new, sheet_markers_edit, sheet_list, sheet_tools, sheet_shape, sheet_ring, sheet_goto, sheet_export,
          sheet_import, sheet_share, sheet_ask, sheet_confirm]
PROFILE = {'id': 'u1', 'name': 'Mine', 'bc': 0.3, 'model': 'G1', 'w': 150, 'mv': 2800, 'sight': 1.5, 'zero': 100}


@pytest.mark.parametrize('night', [False, True], ids=['day', 'night'])
@pytest.mark.parametrize('opener', SHEETS, ids=[s.__name__[6:] for s in SHEETS])
def test_sheet_fits_and_enlarged_text_does_not_cut_it(page, app_url, opener, night):
    page.add_init_script(NO_SHARE)
    page.add_init_script(CLIP_STUB)
    markers = [mk(f'w{i}', f'Marker with a fairly long name number {i}', HOME[0] + i * 0.001, HOME[1]) for i in range(1, 14)]
    kinds = ['point', 'camp', 'vehicle', 'water', 'friend', 'hostile', 'neutral', 'unknown']
    for m, k in zip(markers, kinds):
        m['kind'] = k
    route = {'id': 'r1', 'type': 'route', 'name': 'Route one', 'pts': [[HOME[0] + 0.003, HOME[1]], [HOME[0] + 0.003, HOME[1] + 0.003]], 't': 1}
    boot(page, app_url, markers=markers, shapes=[route], night=night, decl_mode=None, profiles=[PROFILE])
    fix(page, *HOME)
    sel = opener(page)
    page.wait_for_selector(sel + '[open]')
    page.wait_for_timeout(250)   # the sheet's own slide-in
    if sel == '#dlgShare':
        expect(page.locator('#psText')).not_to_be_empty()
    d = page.locator(sel)
    box = d.bounding_box()
    assert box['x'] >= -1 and box['x'] + box['width'] <= 361, box
    inner = [x for x in overflow(page, sel) if 'page scrolls' not in x]
    assert inner == [], inner
    assert page.evaluate("s => { const d = document.querySelector(s); return d.scrollWidth <= d.clientWidth + 1; }", sel)
    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
    assert too_small(page, sel) == []
    assert clipped_buttons(page, sel) == []
    enlarge_text(page)
    page.wait_for_timeout(100)
    inner = [x for x in overflow(page, sel) if 'page scrolls' not in x]
    assert inner == [], inner
    assert page.evaluate("s => { const d = document.querySelector(s); return d.scrollWidth <= d.clientWidth + 1; }", sel)
    assert clipped_buttons(page, sel) == []
    box = page.locator(sel).bounding_box()
    assert box['x'] >= -1 and box['x'] + box['width'] <= 361, box


def test_the_text_enlarging_stand_in_really_enlarges(page, app_url):
    """Guards the checks above against passing because nothing grew."""
    ballistics(page, app_url)
    size = lambda sel: page.evaluate("s => parseFloat(getComputedStyle(document.querySelector(s)).fontSize)", sel)
    before = (size('#bSave'), size('#view-ballistics h2'), size('#solElev'))
    enlarge_text(page)
    enlarge_text(page)   # twice changes nothing more
    after = (size('#bSave'), size('#view-ballistics h2'), size('#solElev'))
    assert [round(a / b, 2) for a, b in zip(after, before)] == [1.38] * 3
