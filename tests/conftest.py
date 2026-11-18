"""Browser test harness: builds the app once, serves it on localhost, gives each test a fresh page.

Any console error or uncaught page error fails the test at teardown. Requests to non-localhost
hosts (map tiles) are aborted, and the console noise those aborts cause is ignored.
"""
import functools, http.server, json, os, subprocess, sys, threading
from urllib.parse import urlparse

import pytest
from playwright.sync_api import sync_playwright

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOCAL_HOSTS = ('127.0.0.1', 'localhost')


@pytest.fixture(scope='session')
def app_url(tmp_path_factory):
    out = tmp_path_factory.mktemp('fk-build')
    subprocess.run([sys.executable, os.path.join(ROOT, 'build.py'), str(out)], check=True, capture_output=True)
    handler = functools.partial(_QuietHandler, directory=str(out))
    server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    yield f'http://127.0.0.1:{server.server_address[1]}/index.html'
    server.shutdown()
    server.server_close()


class _QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


@pytest.fixture(scope='session')
def browser():
    with sync_playwright() as p:
        b = p.chromium.launch()
        yield b
        b.close()


def _is_local(url):
    return urlparse(url).hostname in LOCAL_HOSTS or url.startswith(('data:', 'blob:', 'about:'))


@pytest.fixture
def page(browser):
    ctx = browser.new_context(viewport={'width': 360, 'height': 640}, service_workers='block')
    ctx.route('**/*', lambda route: route.continue_() if _is_local(route.request.url) else route.abort())
    pg = ctx.new_page()
    errors = []
    pg.on('pageerror', lambda e: errors.append(f'pageerror: {e}'))

    def on_console(msg):
        if msg.type != 'error':
            return
        if not _is_local(msg.location.get('url') or ''):
            return  # aborted off-host request (map tiles)
        errors.append(f'console: {msg.text}')

    pg.on('console', on_console)
    yield pg
    ctx.close()
    assert errors == [], 'browser errors:\n' + '\n'.join(errors)


def inject_data(page, protocols=None, topics=None, checklists=None, only=False):
    """FK_DATA is assigned by an inline script after init scripts run, so trap the assignment and
    add the fixtures to each kind passed (None leaves that kind untouched). A fixture with the same id
    as a shipped item replaces it. only=True drops the shipped items of each kind passed, so the page
    sees the fixtures alone (for tests whose expectations depend on exactly which items exist)."""
    extra = {'protocols': protocols, 'topics': topics, 'checklists': checklists}
    extra = {k: v for k, v in extra.items() if v is not None}
    page.add_init_script(f"""
      (() => {{
        const extra = {json.dumps(extra)}, ONLY = {json.dumps(bool(only))};
        let val;
        Object.defineProperty(window, 'FK_DATA', {{
          configurable: true,
          get() {{ return val; }},
          set(v) {{
            for (const kind of Object.keys(extra)) {{
              const add = extra[kind], ids = new Set(add.map(x => x && x.id));
              v[kind] = (ONLY ? [] : (v[kind] || []).filter(x => !ids.has(x.id))).concat(add);
            }}
            val = v;
          }}
        }});
      }})();
    """)


def inject_protocols(page, fixtures, only=False):
    """Protocol-only shorthand for inject_data."""
    inject_data(page, protocols=fixtures, only=only)
