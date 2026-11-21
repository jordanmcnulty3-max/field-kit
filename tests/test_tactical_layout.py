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

# What Ballistics shows for the two pinned starting points, read from #solElev, #solWind, #solSub and the text of the dope card
# table. default_*: the starting profile (.308 Win 175 gr SMK, 24" barrel) with the default inputs (500 yd, 10 mph from
# 3 o'clock). p223_*: the .223 Rem 77 gr MatchKing starting point at 300 yd with a 10 mph wind from 9 o'clock. mil / moa: the
# unit switch. Nothing here was worked out by hand. Since the screen was rebuilt around the sight, the readers are: the mil and
# MOA lines of the show-all view (a profile with no sight), and the Drop, Drift, fps, ft-lb and Time columns of the dope card;
# the unit switch is gone. The one edit to the pinned data: the Drop cell at the zero (100 yd) reads 0.0 where it read -0.0.
# RE-PINNED for the "Built-in loads sourced" ruling in docs/ballistics-rulings.md: the default .308 load changed from G7 0.243
# to the maker's G7 0.25, and the 5.56 NATO 62 gr load these figures were first captured for (id p556) was removed, so the
# second set now pins p223. Before the restyle and before this ruling the same screen was captured from commit a190ff5 and
# was unchanged through the solver check (docs/ballistics-rulings.md, "Solver check").
BEFORE = {'default_mil': {'e': 'U 3.5 mil',
                 'w': 'R 1.2 mil',
                 's': 'At 500 yd: drop 63.6 in, drift 21.2 in, 1782 fps, 1234 ft-lb, 0.70 s flight.',
                 't': 'Yd\tElev mil\tWind mil\tDrop in\tDrift in\tfps\tft-lb\tTime s\n'
                      '50\t0.0\tR 0.1\t-0.1\t0.2\t2510\t2449\t0.06\n'
                      '100\t0.0\tR 0.2\t0.0\t0.7\t2422\t2281\t0.12\n'
                      '150\tU 0.3\tR 0.3\t-1.4\t1.7\t2336\t2121\t0.18\n'
                      '200\tU 0.6\tR 0.4\t-4.4\t3.0\t2252\t1971\t0.25\n'
                      '250\tU 1.0\tR 0.5\t-9.2\t4.8\t2169\t1829\t0.32\n'
                      '300\tU 1.5\tR 0.7\t-15.7\t7.1\t2089\t1696\t0.39\n'
                      '350\tU 1.9\tR 0.8\t-24.3\t9.8\t2010\t1570\t0.46\n'
                      '400\tU 2.4\tR 0.9\t-35.0\t13.0\t1932\t1451\t0.54\n'
                      '450\tU 3.0\tR 1.0\t-48.1\t16.8\t1857\t1340\t0.61\n'
                      '500\tU 3.5\tR 1.2\t-63.6\t21.2\t1782\t1234\t0.70\n'
                      '550\tU 4.1\tR 1.3\t-81.9\t26.2\t1709\t1135\t0.78\n'
                      '600\tU 4.8\tR 1.5\t-103.2\t31.8\t1637\t1042\t0.87\n'
                      '650\tU 5.5\tR 1.6\t-127.7\t38.1\t1567\t954\t0.97\n'
                      '700\tU 6.2\tR 1.8\t-155.8\t45.2\t1498\t872\t1.06\n'
                      '750\tU 7.0\tR 2.0\t-187.8\t53.1\t1430\t795\t1.17\n'
                      '800\tU 7.8\tR 2.1\t-224.0\t61.9\t1363\t723\t1.27\n'
                      '850\tU 8.7\tR 2.3\t-264.9\t71.5\t1299\t656\t1.39\n'
                      '900\tU 9.6\tR 2.5\t-310.9\t82.2\t1236\t594\t1.51\n'
                      '950\tU 10.6\tR 2.7\t-362.6\t94.0\t1176\t537\t1.63\n'
                      '1000\tU 11.7\tR 3.0\t-420.7\t106.9\t1119\t487\t1.76'},
 'default_moa': {'e': 'U 12.2 MOA',
                 'w': 'R 4.0 MOA',
                 's': 'At 500 yd: drop 63.6 in, drift 21.2 in, 1782 fps, 1234 ft-lb, 0.70 s flight.',
                 't': 'Yd\tElev MOA\tWind MOA\tDrop in\tDrift in\tfps\tft-lb\tTime s\n'
                      '50\tU 0.1\tR 0.3\t-0.1\t0.2\t2510\t2449\t0.06\n'
                      '100\t0.0\tR 0.7\t0.0\t0.7\t2422\t2281\t0.12\n'
                      '150\tU 0.9\tR 1.1\t-1.4\t1.7\t2336\t2121\t0.18\n'
                      '200\tU 2.1\tR 1.4\t-4.4\t3.0\t2252\t1971\t0.25\n'
                      '250\tU 3.5\tR 1.8\t-9.2\t4.8\t2169\t1829\t0.32\n'
                      '300\tU 5.0\tR 2.3\t-15.7\t7.1\t2089\t1696\t0.39\n'
                      '350\tU 6.6\tR 2.7\t-24.3\t9.8\t2010\t1570\t0.46\n'
                      '400\tU 8.4\tR 3.1\t-35.0\t13.0\t1932\t1451\t0.54\n'
                      '450\tU 10.2\tR 3.6\t-48.1\t16.8\t1857\t1340\t0.61\n'
                      '500\tU 12.2\tR 4.0\t-63.6\t21.2\t1782\t1234\t0.70\n'
                      '550\tU 14.2\tR 4.5\t-81.9\t26.2\t1709\t1135\t0.78\n'
                      '600\tU 16.4\tR 5.1\t-103.2\t31.8\t1637\t1042\t0.87\n'
                      '650\tU 18.8\tR 5.6\t-127.7\t38.1\t1567\t954\t0.97\n'
                      '700\tU 21.3\tR 6.2\t-155.8\t45.2\t1498\t872\t1.06\n'
                      '750\tU 23.9\tR 6.8\t-187.8\t53.1\t1430\t795\t1.17\n'
                      '800\tU 26.7\tR 7.4\t-224.0\t61.9\t1363\t723\t1.27\n'
                      '850\tU 29.8\tR 8.0\t-264.9\t71.5\t1299\t656\t1.39\n'
                      '900\tU 33.0\tR 8.7\t-310.9\t82.2\t1236\t594\t1.51\n'
                      '950\tU 36.4\tR 9.4\t-362.6\t94.0\t1176\t537\t1.63\n'
                      '1000\tU 40.2\tR 10.2\t-420.7\t106.9\t1119\t487\t1.76'},
 'p223_mil': {'e': 'U 1.2 mil',
              'w': 'L 0.8 mil',
              's': 'At 300 yd: drop 13.0 in, drift 9.1 in, 2036 fps, 709 ft-lb, 0.38 s flight.',
              't': 'Yd\tElev mil\tWind mil\tDrop in\tDrift in\tfps\tft-lb\tTime s\n'
                   '50\tU 0.4\tL 0.1\t-0.7\t0.2\t2598\t1154\t0.06\n'
                   '100\t0.0\tL 0.3\t0.0\t0.9\t2479\t1051\t0.12\n'
                   '150\tU 0.1\tL 0.4\t-0.8\t2.1\t2364\t955\t0.18\n'
                   '200\tU 0.4\tL 0.5\t-3.1\t3.9\t2251\t867\t0.24\n'
                   '250\tU 0.8\tL 0.7\t-7.1\t6.2\t2142\t785\t0.31\n'
                   '300\tU 1.2\tL 0.8\t-13.0\t9.1\t2036\t709\t0.38\n'
                   '350\tU 1.7\tL 1.0\t-21.1\t12.7\t1933\t639\t0.46\n'
                   '400\tU 2.2\tL 1.2\t-31.4\t17.0\t1832\t574\t0.54\n'
                   '450\tU 2.7\tL 1.4\t-44.4\t22.2\t1734\t514\t0.62\n'
                   '500\tU 3.3\tL 1.6\t-60.2\t28.1\t1638\t459\t0.71\n'
                   '550\tU 4.0\tL 1.8\t-79.3\t35.0\t1544\t408\t0.81\n'
                   '600\tU 4.7\tL 2.0\t-102.0\t42.9\t1453\t361\t0.91\n'
                   '650\tU 5.5\tL 2.2\t-128.9\t52.0\t1365\t319\t1.01\n'
                   '700\tU 6.4\tL 2.5\t-160.4\t62.2\t1279\t280\t1.13\n'
                   '750\tU 7.3\tL 2.7\t-197.2\t73.9\t1197\t245\t1.25\n'
                   '800\tU 8.3\tL 3.0\t-240.1\t87.0\t1120\t215\t1.38\n'
                   '850\tU 9.5\tL 3.3\t-290.0\t101.5\t1066\t194\t1.51\n'
                   '900\tU 10.7\tL 3.6\t-347.4\t117.0\t1033\t183\t1.66\n'
                   '950\tU 12.1\tL 3.9\t-413.0\t133.2\t1007\t173\t1.80\n'
                   '1000\tU 13.5\tL 4.2\t-487.2\t150.0\t983\t165\t1.96'},
 'p223_moa': {'e': 'U 4.1 MOA',
              'w': 'L 2.9 MOA',
              's': 'At 300 yd: drop 13.0 in, drift 9.1 in, 2036 fps, 709 ft-lb, 0.38 s flight.',
              't': 'Yd\tElev MOA\tWind MOA\tDrop in\tDrift in\tfps\tft-lb\tTime s\n'
                   '50\tU 1.3\tL 0.4\t-0.7\t0.2\t2598\t1154\t0.06\n'
                   '100\t0.0\tL 0.9\t0.0\t0.9\t2479\t1051\t0.12\n'
                   '150\tU 0.5\tL 1.3\t-0.8\t2.1\t2364\t955\t0.18\n'
                   '200\tU 1.5\tL 1.8\t-3.1\t3.9\t2251\t867\t0.24\n'
                   '250\tU 2.7\tL 2.4\t-7.1\t6.2\t2142\t785\t0.31\n'
                   '300\tU 4.1\tL 2.9\t-13.0\t9.1\t2036\t709\t0.38\n'
                   '350\tU 5.7\tL 3.5\t-21.1\t12.7\t1933\t639\t0.46\n'
                   '400\tU 7.5\tL 4.1\t-31.4\t17.0\t1832\t574\t0.54\n'
                   '450\tU 9.4\tL 4.7\t-44.4\t22.2\t1734\t514\t0.62\n'
                   '500\tU 11.5\tL 5.4\t-60.2\t28.1\t1638\t459\t0.71\n'
                   '550\tU 13.8\tL 6.1\t-79.3\t35.0\t1544\t408\t0.81\n'
                   '600\tU 16.2\tL 6.8\t-102.0\t42.9\t1453\t361\t0.91\n'
                   '650\tU 18.9\tL 7.6\t-128.9\t52.0\t1365\t319\t1.01\n'
                   '700\tU 21.9\tL 8.5\t-160.4\t62.2\t1279\t280\t1.13\n'
                   '750\tU 25.1\tL 9.4\t-197.2\t73.9\t1197\t245\t1.25\n'
                   '800\tU 28.7\tL 10.4\t-240.1\t87.0\t1120\t215\t1.38\n'
                   '850\tU 32.6\tL 11.4\t-290.0\t101.5\t1066\t194\t1.51\n'
                   '900\tU 36.9\tL 12.4\t-347.4\t117.0\t1033\t183\t1.66\n'
                   '950\tU 41.5\tL 13.4\t-413.0\t133.2\t1007\t173\t1.80\n'
                   '1000\tU 46.5\tL 14.3\t-487.2\t150.0\t983\t165\t1.96'}}


# ---------- helpers ----------

def ballistics(page, app_url, night=False, **kv):
    """Open the Ballistics screen with the page clock left alone (the screen recalculates on a 150 ms timer)."""
    page.goto('about:blank')
    tiles_ok(page)
    store(page, **{'advAck': True, 'night': night, 'mapFollow': False, **kv})
    page.goto(app_url + '#/tactical/ballistics')
    page.wait_for_function('window.FK && FK.sheet && FK.view && FK.view() === "ballistics"')
    page.wait_for_selector('#dope tr')


def readout(page, unit='mil'):
    """The pinned figures as the screen shows them for a profile with no sight (every unit): the mil or MOA line of the answer,
    the sentence under it, and the dope card's Yd, Elev, Wind, Drop in, Drift in, fps, ft-lb and Time s columns for that unit."""
    return page.evaluate("""unit => {
      const line = id => document.querySelector('#' + id).innerText.split('\\n').filter(x => x.trim())[unit === 'mil' ? 1 : 2];
      const heads = [...document.querySelectorAll('#dope th')].map(h => h.textContent.trim());
      const U = unit === 'mil' ? 'mil' : 'MOA';
      const want = ['Yd', 'Elev ' + U, 'Wind ' + U, 'Drop in', 'Drift in', 'fps', 'ft-lb', 'Time s'];
      const at = want.map(w => heads.indexOf(w));
      const rows = [...document.querySelectorAll('#dope tbody tr')].map(r => at.map(i => r.children[i].textContent).join('\\t'));
      return { e: line('solElev'), w: line('solWind'), s: document.querySelector('#solSub').textContent, t: want.join('\\t') + '\\n' + rows.join('\\n') }; }""", unit)


def settle(page):
    page.wait_for_timeout(450)   # the 150 ms recalculation timer plus a margin


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
    assert readout(page, 'moa') == BEFORE['default_moa']


def test_second_profile_output_is_what_it_was_pinned_at(page, app_url):
    ballistics(page, app_url)
    page.select_option('#bProfile', 'p223')
    page.fill('#bRange', '300')
    page.fill('#bWind', '10')
    page.select_option('#bClock', '9')
    settle(page)
    assert readout(page) == BEFORE['p223_mil']
    assert readout(page, 'moa') == BEFORE['p223_moa']


def test_the_dope_card_is_a_real_table_with_all_columns(page, app_url):
    """Guards the capture above against being an empty string on both sides."""
    ballistics(page, app_url)
    assert page.locator('#dope tbody tr').count() >= 20
    assert page.locator('#dope th').count() == 10        # no sight: Yd, Elev mil, Elev MOA, Wind mil, Wind MOA, Drop, Drift, fps, ft-lb, Time


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
    expect(heads).to_have_text(['Conditions', 'Dope card'])
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
    assert tops == [gap] * 2


def test_ballistics_sections_have_clear_space_above_like_the_home(page, app_url):
    ballistics(page, app_url)
    gaps = page.evaluate("""() => [...document.querySelectorAll('#view-ballistics h2')].map(h => {
      let prev = h.parentElement.previousElementSibling;
      while (prev && !prev.getBoundingClientRect().height) prev = prev.previousElementSibling;
      return h.getBoundingClientRect().top - prev.getBoundingClientRect().bottom; })""")
    assert len(gaps) == 2 and all(g >= 24 for g in gaps), gaps


def test_ballistics_fields_and_their_order(page, app_url):
    """The screen's controls, in order: the profile row, the shot, the conditions (folded) and the dope card. The load fields,
    Save, Delete and the unit switch are gone from this screen (the profile editor holds the load)."""
    ballistics(page, app_url)
    got = page.evaluate("""() => [...document.querySelectorAll('#view-ballistics h2')].map(h => [h.textContent,
      [...h.parentElement.querySelectorAll('input, select, button')].map(e => e.id)])""")
    assert got == [
        ['Conditions', ['bCondBtn', 'bTemp', 'bAlt', 'bPress', 'bRH']],
        ['Dope card', ['bMax', 'bStep']],
    ]
    ids = page.evaluate("[...document.querySelectorAll('#view-ballistics [id]')].map(e => e.id)")
    assert ids == ['bProfile', 'bEdit', 'bSight', 'bZeroLine', 'solution', 'solElev', 'solWind', 'solSub', 'bAll', 'bRange', 'bAngle', 'bWind',
                   'bClock', 'bCond', 'bCondBtn', 'bCondFields', 'bTemp', 'bAlt', 'bPress', 'bRH', 'bMax', 'bStep', 'dopeCue', 'dope']


# ---------- Ballistics behaviour ----------

def test_profile_save_load_and_delete(page, app_url):
    """Made, switched to and deleted through the profile editor (the main screen has no Save or Delete)."""
    ballistics(page, app_url)
    page.click('#bEdit')
    expect(page.locator('#rfTitle')).to_have_text('Built-in load')
    page.fill('#rfName', 'Range rifle')
    page.fill('#rfBC', '0.4')
    page.fill('#rfMV', '2900')
    page.click('#rfSaveNew')
    expect(page.locator('#dlgRifle')).to_be_hidden()
    assert page.evaluate("JSON.parse(localStorage.getItem('fk.profiles')).map(p => [p.name, p.bc, p.mv])") == [['Range rifle', 0.4, 2900]]
    expect(page.locator('#bProfile option:checked')).to_have_text('Range rifle')
    # load another profile, then come back to the saved one
    page.select_option('#bProfile', 'p223')
    settle(page)
    assert page.evaluate('[FK.bal.selected().bc, FK.bal.selected().mv]') == [0.188, 2720]
    mine = page.evaluate("JSON.parse(localStorage.getItem('fk.profiles'))[0].id")
    page.select_option('#bProfile', mine)
    settle(page)
    assert page.evaluate('[FK.bal.selected().bc, FK.bal.selected().mv]') == [0.4, 2900]
    # delete goes through the confirm sheet from the editor; Cancel keeps it, Delete removes it
    page.click('#bEdit')
    page.click('#rfDelete')
    expect(page.locator('#dlgConfirm')).to_be_visible()
    expect(page.locator('#cfTitle')).to_have_text('Delete the profile?')
    page.click('#cfCancel')
    expect(page.locator('#dlgConfirm')).to_be_hidden()
    assert page.evaluate("JSON.parse(localStorage.getItem('fk.profiles')).length") == 1
    page.click('#rfDelete')
    page.click('#cfOk')
    expect(page.locator('#dlgConfirm')).to_be_hidden()
    expect(page.locator('#dlgRifle')).to_be_hidden()
    assert page.evaluate("JSON.parse(localStorage.getItem('fk.profiles')).length") == 0
    expect(page.locator('#bProfile option:checked')).to_have_text('Federal Gold Medal .308 Win 175 gr SMK, 24″ barrel')   # deleting lands on a built-in load


def test_the_unit_switch_is_gone_and_the_answer_names_its_units(page, app_url):
    """The old MIL / MOA switch is replaced by the profile's sight (and Show all units); the stored 'unit' is not read."""
    ballistics(page, app_url, unit='moa')
    assert page.locator('#unitSeg').count() == 0
    assert 'U 3.5 mil' in page.inner_text('#solElev') and 'U 12.2 MOA' in page.inner_text('#solElev')
    assert readout(page) == BEFORE['default_mil'] and readout(page, 'moa') == BEFORE['default_moa']


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
    assert len(heads) == 2
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
    page.evaluate("() => { FK.sheet.ask({ title: 'Name this route', label: 'Name, e.g. Ridge loop' }); }")      # not awaited: it resolves when the sheet closes
    return '#dlgAsk'


def sheet_confirm(page):
    go(page, '/tactical/ballistics')
    page.wait_for_function('FK.view() === "ballistics"')
    page.select_option('#bProfile', 'u1')
    page.click('#bEdit')
    page.click('#rfDelete')
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
    before = (size('#bEdit'), size('#view-ballistics h2'), size('#solElev .v'))
    enlarge_text(page)
    enlarge_text(page)   # twice changes nothing more
    after = (size('#bEdit'), size('#view-ballistics h2'), size('#solElev .v'))
    assert [round(a / b, 2) for a, b in zip(after, before)] == [1.38] * 3
