"""Record what the search overlay shows on screen for a list of searches against a built app.

Usage: python3 tools/search_on_screen.py BUILD_DIR QUERIES.json OUT.json [N]
QUERIES.json is a JSON list of searches; OUT.json gets {search: [first N result keys on screen]} (N defaults to 5), read from
#searchBody .sr-item in the real overlay at 360x640 on #/survival, as tests/test_search.py::on_screen does. Requests off localhost
are aborted. Run it on a build of an old commit and of the new one, then compare the two files.
"""
import functools, http.server, json, sys, threading
from urllib.parse import urlparse
from playwright.sync_api import sync_playwright
build, qfile, out = sys.argv[1:4]; N = int(sys.argv[4]) if len(sys.argv) > 4 else 5
qs = json.load(open(qfile))
class H(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a): pass
srv = http.server.ThreadingHTTPServer(('127.0.0.1', 0), functools.partial(H, directory=build))
threading.Thread(target=srv.serve_forever, daemon=True).start()
url = f'http://127.0.0.1:{srv.server_address[1]}/index.html#/survival'
with sync_playwright() as p:
    b = p.chromium.launch()
    ctx = b.new_context(viewport={'width': 360, 'height': 640}, service_workers='block')
    ctx.route('**/*', lambda r: r.continue_() if (urlparse(r.request.url).hostname in ('127.0.0.1','localhost') or r.request.url.startswith(('data:','blob:','about:'))) else r.abort())
    pg = ctx.new_page()
    pg.goto(url); pg.wait_for_function('window.FK && FK.search')
    pg.click('#searchBtn'); pg.wait_for_selector('#searchPane', state='visible')
    res = pg.evaluate("""([qs, n]) => { const input = document.querySelector('#searchInput'); const o = {};
      for (const t of qs) { input.value = t; input.dispatchEvent(new Event('input', {bubbles: true}));
        o[t] = [...document.querySelectorAll('#searchBody .sr-item')].slice(0, n).map(e => e.dataset.key); } return o; }""", [qs, N])
    b.close()
json.dump(res, open(out, 'w'), indent=0, ensure_ascii=False)
