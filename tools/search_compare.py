"""Record FK.search.query() output (full result objects) for a fixed query list against a built app.

Usage: python3 tools/search_compare.py BUILD_DIR OUT.json
Run it on a build of the old commit and a build of the new one, then diff the two files.
The fixed list is followed by queries generated from the shipped data (every title, every keyword,
the first word and a prefix of each), so the comparison covers real content, not only hand-picked cases.
"""
import functools, http.server, json, sys, threading

from playwright.sync_api import sync_playwright

FIXED = [
    'protocol', 'water', 'fire', 'shelter', 'burn', 'bleach', 'fallout', 'nuke', 'iodine', 'decon', 'radiation', 'shock', 'bleeding',
    'CO', 'MI', 'no', 'KI', 'in', 'to', 'of', 'a', 'x', '9',
    'in shock', 'frost bite', 'dirty bomb', 'heat stroke', 'water purification', 'first aid', 'cold weather', 'snake bite', 'chest pain',
    'potassium iodide', 'carbon monoxide', 'stop the bleeding', 'how to treat a burn', 'shelter in place', 'wash off fallout',
    "don't", "dont", "won't", "can’t", "it's", 'café', 'cafe', 'naïve', 'résumé', 'Ünïcode', 'ÉCOLE', 'tourniquet', 'TOURNIQUET',
    'gen', 'wat', 'rad', 'dec', 'ban', 'sh', 'fr', 'ch', 'ba', 'sur',
    'zzzzqqq', 'nothing matches this at all', 'protocol zzzz',
    '', ' ', '   ', '\t\n', '!!!', "'", '---', '1', '12', '911', '9line', '9 line', 'mist', 'cpr', 'tq',
    'map', 'settings', 'backup', 'ballistics', 'compass', 'gps', 'mgrs', 'checklist', 'kit', 'go bag', 'bug out',
    '  water   purify  ', 'WATER', 'Water Purify', 'water water', 'purify purify water', '°', '5 %', 'fahrenheit', 'celsius',
]

GEN = """() => {
  const q = new Set();
  const add = s => { if (typeof s === 'string' && s.trim()) q.add(s); };
  for (const kind of ['protocols', 'topics', 'checklists']) {
    for (const x of (FK_DATA[kind] || [])) {
      add(x.title);
      add(String(x.title || '').split(/\\s+/)[0]);
      add(String(x.title || '').slice(0, 4));
      for (const k of (Array.isArray(x.keywords) ? x.keywords : [])) { add(k); add(String(k).slice(0, 3)); }
    }
  }
  return [...q];
}"""


def main(build_dir, out_path):
    class H(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *a):
            pass
    srv = http.server.ThreadingHTTPServer(('127.0.0.1', 0), functools.partial(H, directory=build_dir))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    url = f'http://127.0.0.1:{srv.server_address[1]}/index.html#/emergency'
    with sync_playwright() as p:
        b = p.chromium.launch()
        ctx = b.new_context(viewport={'width': 360, 'height': 640}, service_workers='block')
        pg = ctx.new_page()
        errors = []
        pg.on('pageerror', lambda e: errors.append(str(e)))
        pg.goto(url)
        pg.wait_for_function('window.FK && FK.search')
        queries = FIXED + sorted(pg.evaluate(GEN))
        # the very first query is part of the record, so the un-warmed path is compared too
        results = pg.evaluate('qs => qs.map(q => [q, FK.search.query(q)])', queries)
        b.close()
    assert not errors, errors
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=1)
    nonempty = sum(1 for _, r in results if r)
    print(f'{len(results)} queries ({len(FIXED)} fixed), {nonempty} with results, {sum(len(r) for _, r in results)} result objects -> {out_path}')


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
