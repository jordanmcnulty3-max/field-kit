import json


def tab_visible(page, name):
    return page.locator(f'#tab-{name}').is_visible()


def test_tab_click_changes_hash(page, app_url):
    page.goto(app_url)
    page.click('.tabbar button[data-tab="emergency"]')
    assert page.url.endswith('#/emergency')


def test_back_returns_to_previous_tab(page, app_url):
    page.goto(app_url)
    page.click('.tabbar button[data-tab="survival"]')
    page.click('.tabbar button[data-tab="emergency"]')
    page.go_back()
    assert tab_visible(page, 'survival')
    assert not tab_visible(page, 'emergency')


def test_deep_link_opens_tab(page, app_url):
    page.goto(app_url + '#/emergency')
    assert page.locator('#tab-emergency').is_visible()
    assert page.evaluate('FK.route.current().tab') == 'emergency'


def test_unknown_tab_falls_back(page, app_url):
    page.goto(app_url + '#/nonsense/x')
    visible = [t for t in ('survival', 'tactical', 'emergency') if tab_visible(page, t)]
    assert len(visible) == 1
    assert 'nonsense' not in page.url


def test_v5_stored_tab_still_honoured(page, app_url):
    page.goto(app_url)
    page.evaluate("localStorage.setItem('fk.tab', JSON.stringify('survival'))")
    page.goto('about:blank')
    page.goto(app_url)
    assert tab_visible(page, 'survival')
    assert page.url.endswith('#/survival')


def test_initial_route_adds_no_history_entry(page, app_url):
    page.goto('about:blank')
    page.goto(app_url)
    assert page.evaluate('history.length') == 2  # blank + app, no extra entry for the route


def test_tactical_views_have_addresses_and_back_works(page, app_url):
    page.goto(app_url + '#/tactical/map')
    page.click('#tacSeg button[data-view="position"]')
    assert page.url.endswith('#/tactical/position')
    page.click('#tacSeg button[data-view="ballistics"]')
    assert page.url.endswith('#/tactical/ballistics')
    page.go_back()
    assert page.locator('#view-position').is_visible()
    assert not page.locator('#view-ballistics').is_visible()
    page.go_back()
    assert page.locator('#view-map').is_visible()


def test_v5_stored_view_honoured_with_no_hash(page, app_url):
    page.goto(app_url)
    page.evaluate("localStorage.setItem('fk.view', JSON.stringify('ballistics'))")
    page.goto('about:blank')
    page.goto(app_url)
    assert page.locator('#view-ballistics').is_visible()
    assert page.url.endswith('#/tactical/ballistics')


def test_route_event_and_go_replace(page, app_url):
    page.goto(app_url)
    page.evaluate("window.seen = []; FK.on('route', r => seen.push(r.tab))")
    page.evaluate("FK.route.go('/emergency')")
    page.evaluate("FK.route.go('/survival', { replace: true })")
    assert page.evaluate('seen') == ['emergency', 'survival']
    page.go_back()  # replace left no entry for emergency, so this returns to the initial tactical route
    assert tab_visible(page, 'tactical')
