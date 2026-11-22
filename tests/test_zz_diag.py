"""TEMPORARY diagnostic (reticle-fix-test branch only): which element in the rifle editor is too wide in WebKit."""
import json
from playwright.sync_api import expect
from .test_tactical_layout import ballistics, enlarge_text
from .test_bal_editor import OWN, DLG


def test_diag(page, app_url):
    long = {**OWN, 'name': 'A fairly long profile name for a rifle in a long case ', 'optic': {'type': 'reticle', 'unit': 'mil', 'marks': [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]}}
    ballistics(page, app_url, profiles=[long])
    page.evaluate("FK.bal.select('u1')")
    page.click('#bEdit')
    expect(page.locator(DLG)).to_be_visible()
    page.select_option('#rfOptic', 'reticle')
    page.fill('#rfZTemp', '40')
    page.fill('#rfZAlt', '800')
    page.wait_for_timeout(250)
    enlarge_text(page)
    page.wait_for_timeout(100)
    info = page.evaluate("""d => [...document.querySelectorAll(d + ' label.f')].filter(l => l.scrollWidth > l.clientWidth + 1).map(l => ({
        label: l.id || l.firstChild.textContent.trim(), sw: l.scrollWidth, cw: l.clientWidth,
        kids: [...l.childNodes].map(n => n.nodeType === 3 ? {text: n.textContent.trim(), w: (() => { const r = document.createRange(); r.selectNodeContents(n); return Math.round(r.getBoundingClientRect().width); })()}
          : {tag: n.tagName, id: n.id, w: Math.round(n.getBoundingClientRect().width), sw: n.scrollWidth, minW: getComputedStyle(n).minWidth, fs: getComputedStyle(n).fontSize})}))""", DLG)
    sc = "d => { const e = document.querySelector(d); return [e.scrollWidth, e.clientWidth, document.documentElement.scrollWidth, innerWidth]; }"
    after = page.evaluate(sc, DLG)
    page.evaluate("document.querySelector('#rfOptic').style.overflow = 'visible'")
    before = page.evaluate(sc, DLG)
    page.evaluate("document.querySelector('#rfOptic').style.overflow = ''")
    print('DIAG ' + json.dumps({'labels': info, 'dialog_and_page_scroll_with_fix': after, 'without_fix': before}))
    assert info == [], json.dumps(info)
