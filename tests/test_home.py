import json

from .conftest import inject_protocols


def proto(pid, title, category, draft=False, steps=3):
    p = {'id': pid, 'title': title, 'category': category, 'reviewed': '2026-11-16',
         'sources': [{'name': 'Fixture'}],
         'steps': [{'id': f's{i}', 'text': f'{title} step {i}'} for i in range(1, steps + 1)]}
    if draft:
        p['draft'] = True
    return p


FIXTURES = [
    proto('bleeding', 'Severe bleeding', 'life', draft=True, steps=7),
    proto('cpr-adult', 'CPR adult', 'life'),
    proto('cpr-child', 'CPR child', 'life'),
    proto('cpr-infant', 'CPR infant', 'life'),
    proto('choking', 'Choking', 'life'),
    proto('shock', 'Shock', 'life'),
    proto('burns', 'Burns', 'injury'),
    proto('splint', 'Splinting', 'injury'),
    proto('frostbite', 'Frostbite', 'environment'),
    proto('snakebite', 'Snakebite', 'bites'),
    proto('fever', 'Fever', 'illness'),
    proto('iv', 'IV access', 'advanced'),
]
IDS = [p['id'] for p in FIXTURES]


def boot(page, app_url, fixtures=FIXTURES, storage=None, hash_='#/emergency'):
    """Load the app on the Emergency tab with only the fixtures (no shipped protocols) and optional pre-seeded storage."""
    inject_protocols(page, fixtures, only=True)
    seed = {'advAck': True, **(storage or {})}
    page.add_init_script(
        "if (!sessionStorage.getItem('seeded')) { sessionStorage.setItem('seeded', '1');"
        + ''.join(f"localStorage.setItem('fk.{k}', {json.dumps(json.dumps(v))});" for k, v in seed.items()) + '}')
    page.goto(app_url + hash_)


def life(page):
    return page.locator('#emLife button')


def test_three_life_threat_buttons_visible_without_scrolling(page, app_url):
    boot(page, app_url)
    names = [b.inner_text().split('\n')[0].strip().lower() for b in life(page).all()]
    assert names == ['bleeding', 'not breathing', 'choking']
    tabbar_top = page.eval_on_selector('.tabbar', 'e => e.getBoundingClientRect().top')
    for b in life(page).all():
        box = b.bounding_box()
        assert box['y'] >= 0 and box['y'] + box['height'] <= min(640, tabbar_top)
        assert box['height'] >= 56 and box['width'] >= 56


def test_life_buttons_use_danger_colour_and_nothing_else_on_home_does(page, app_url):
    boot(page, app_url)
    blaze = page.evaluate("getComputedStyle(document.documentElement).getPropertyValue('--blaze').trim()")
    rgb = page.evaluate("c => { const e = document.createElement('i'); e.style.color = c; document.body.append(e); const v = getComputedStyle(e).color; e.remove(); return v; }", blaze)
    bg = page.eval_on_selector('#emLife button', 'e => getComputedStyle(e).backgroundColor')
    assert bg == rgb
    page.click('#emCats summary')
    others = page.evaluate("""rgb => [...document.querySelectorAll('#emHome button, #emHome summary, #emHome a')]
        .filter(e => !e.closest('#emLife') && e.offsetParent !== null)
        .filter(e => { const s = getComputedStyle(e); return s.backgroundColor === rgb || s.color === rgb || s.borderTopColor === rgb; })
        .map(e => e.id || e.className || e.tagName)""", rgb)
    assert others == []


def test_any_protocol_reachable_in_two_taps(page, app_url):
    boot(page, app_url)
    for pid in IDS:
        page.goto(app_url + '#/emergency')
        page.reload()   # fresh home each time: no category left open by the previous protocol
        page.wait_for_selector('#emHome', state='visible')
        if pid in ('bleeding', 'choking'):
            page.click(f'#emLife [data-open="{pid}"]')
        elif pid.startswith('cpr-'):
            page.click('#emLife [data-act="breathing"]')
            page.click(f'#emChooser [data-open="{pid}"]')
        else:
            category = next(p['category'] for p in FIXTURES if p['id'] == pid)
            page.click(f'#emCats summary[data-cat="{category}"]')
            page.click(f'#emCats [data-open="{pid}"]')
        page.wait_for_function(f"location.hash === '#/emergency/{pid}'")
        assert page.locator('#player').is_visible()


def test_fixed_button_or_chooser_option_hidden_when_protocol_missing(page, app_url):
    boot(page, app_url, fixtures=[p for p in FIXTURES if p['id'] not in ('choking', 'cpr-child', 'cpr-infant')])
    assert [b.get_attribute('data-open') or b.get_attribute('data-act') for b in life(page).all()] == ['bleeding', 'breathing']
    page.click('#emLife [data-act="breathing"]')
    assert [b.get_attribute('data-open') for b in page.locator('#emChooser button').all()] == ['cpr-adult']


def test_categories_are_data_driven_empty_ones_hidden_tools_and_reports_stay(page, app_url):
    boot(page, app_url, fixtures=[p for p in FIXTURES if p['category'] in ('life', 'injury')])
    cats = [s.get_attribute('data-cat') for s in page.locator('#emCats summary').all()]
    assert cats == ['life', 'injury', 'tools', 'reports']
    assert [b.get_attribute('data-tool') for b in page.locator('#emCats details[data-cat="tools"] [data-tool]').all()] == ['tq', 'cpr', 'rate', 'burn', 'log']
    assert 'Reports' in page.inner_text('#emCats summary[data-cat="reports"]')


def test_more_life_threats_lists_only_protocols_without_a_fixed_button(page, app_url):
    boot(page, app_url)
    page.click('#emCats summary[data-cat="life"]')
    assert [b.get_attribute('data-open') for b in page.locator('#emCats details[data-cat="life"] [data-open]').all()] == ['shock']


def test_draft_protocol_shows_draft_tag(page, app_url):
    boot(page, app_url)
    assert 'Draft' in page.inner_text('#emLife [data-open="bleeding"]')
    assert 'Draft' not in page.inner_text('#emLife [data-open="choking"]')


def test_pin_appears_under_pinned_and_survives_reload(page, app_url):
    boot(page, app_url, hash_='#/emergency/burns')
    page.click('#player [data-act="pin"]')
    assert json.loads(page.evaluate("localStorage.getItem('fk.pins')")) == ['p:burns']
    page.goto(app_url + '#/emergency')
    page.reload()
    assert page.inner_text('#emPinned [data-open="burns"]').startswith('Burns')
    page.click('#emPinned [data-open="burns"]')
    page.wait_for_function("location.hash === '#/emergency/burns'")
    assert page.get_attribute('#player [data-act="pin"]', 'aria-pressed') == 'true'


def test_pin_button_present_when_opened_by_deep_link(page, app_url):
    boot(page, app_url, hash_='#/emergency/burns')
    assert page.locator('#player [data-act="pin"]').count() == 1


def test_recent_lists_last_five_newest_first(page, app_url):
    boot(page, app_url)
    order = ['burns', 'splint', 'frostbite', 'snakebite', 'fever', 'iv']
    for pid in order:
        page.evaluate(f"FK.protocol.open('{pid}')")
        page.wait_for_function(f"location.hash === '#/emergency/{pid}'")
    page.evaluate("FK.protocol.close()")
    page.wait_for_function("location.hash === '#/emergency'")
    got = [b.get_attribute('data-open') for b in page.locator('#emRecent [data-open]').all()]
    assert got == ['iv', 'fever', 'snakebite', 'frostbite', 'splint']
    assert json.loads(page.evaluate("localStorage.getItem('fk.recent')")) == ['p:' + g for g in got]


def test_reopening_moves_protocol_to_front_without_duplicates(page, app_url):
    boot(page, app_url)
    for pid in ['burns', 'splint', 'burns']:
        page.evaluate(f"FK.protocol.open('{pid}')")
        page.wait_for_function(f"location.hash === '#/emergency/{pid}'")
    assert page.evaluate("FK.recent.all()") == ['p:burns', 'p:splint']


def test_resume_card_shows_only_when_protocol_active(page, app_url):
    boot(page, app_url)
    assert page.locator('#emResume button').count() == 0
    page.evaluate("FK.protocol.open('bleeding', 's3')")
    page.wait_for_function("location.hash === '#/emergency/bleeding/s3'")
    page.evaluate("FK.protocol.close()")
    page.wait_for_function("location.hash === '#/emergency'")
    card = page.locator('#emResume button')
    assert card.inner_text().strip() == 'Resume: Severe bleeding, 3/7'
    card.click()
    page.wait_for_function("location.hash === '#/emergency/bleeding/s3'")


def test_malformed_pins_and_recent_are_ignored(page, app_url):
    boot(page, app_url, storage={'pins': ['p:burns', 'p:nonexistent', 7, None, {'a': 1}, 'x:burns', 'p:<img src=x onerror=alert(1)>', 'p:burns'],
                                 'recent': 'not a list'})
    assert page.evaluate("FK.pins.all()") == ['p:burns', 'p:nonexistent']   # well-formed but unknown: kept, never rendered
    assert page.evaluate("FK.recent.all()") == []
    assert [b.get_attribute('data-open') for b in page.locator('#emPinned [data-open]').all()] == ['burns']
    assert page.locator('#emRecent [data-open]').count() == 0
    boot_again = page.evaluate("(() => { localStorage.setItem('fk.pins', '{bad'); return FK.pins.all(); })()")
    assert boot_again == []


def test_pins_toggle_has_and_all_api(page, app_url):
    boot(page, app_url)
    assert page.evaluate("[FK.pins.has('p:burns'), (FK.pins.toggle('p:burns'), FK.pins.has('p:burns')), FK.pins.all(), (FK.pins.toggle('p:burns'), FK.pins.all())]") \
        == [False, True, ['p:burns'], []]


def test_no_tel_links_or_dial_buttons(page, app_url):
    boot(page, app_url)
    page.click('#emLife [data-act="breathing"]')
    assert page.locator('a[href^="tel:"]').count() == 0
    assert page.locator('#tab-emergency').inner_text().lower().count('dial') == 0


def test_emergency_touch_targets_at_least_56px(page, app_url):
    boot(page, app_url)
    page.click('#emLife [data-act="breathing"]')
    for cat in ('life', 'injury'):
        page.click(f'#emCats summary[data-cat="{cat}"]')
    heights = page.evaluate("""[...document.querySelectorAll('#emHome button[data-open], #emHome button[data-act], #emHome summary')]
        .filter(e => e.offsetParent !== null).map(e => e.getBoundingClientRect().height)""")
    assert heights and min(heights) >= 56


def test_footer_copy_kept(page, app_url):
    boot(page, app_url)
    assert 'Reference only, not a substitute for training. Take a Stop the Bleed, CPR and wilderness first aid course.' in page.inner_text('#tab-emergency')


def test_open_category_stays_open_when_home_rerenders(page, app_url):
    boot(page, app_url)
    page.click('#emCats summary[data-cat="injury"]')
    page.evaluate("FK.pins.toggle('p:burns')")
    page.evaluate("FK.protocol.open('burns')")
    page.wait_for_function("location.hash === '#/emergency/burns'")
    page.evaluate("FK.protocol.close()")
    page.wait_for_function("location.hash === '#/emergency'")
    assert page.locator('#emCats details[data-cat="injury"]').get_attribute('open') is not None
