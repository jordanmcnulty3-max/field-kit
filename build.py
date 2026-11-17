"""Build Field Kit.   python3 build.py

Reads src/, figs/ and vendor/ and writes the deployable files to the repo root:
index.html, sw.js, manifest.json, leaflet.js, leaflet.css. Those root files are build
output -- edit src/ instead. (Optional: python3 build.py some/dir writes there instead.)
"""
import glob, html, json, os, re, shutil, sys

ROOT = os.path.dirname(os.path.abspath(__file__))
ARGS = [a for a in sys.argv[1:] if a != '--release']
RELEASE = '--release' in sys.argv[1:]
OUT = os.path.abspath(ARGS[0]) if ARGS else ROOT
os.chdir(ROOT)
sys.path.insert(0, 'figs')
sys.path.insert(0, ROOT)
import figs
from tools.validate import draft_ids, validate


def read(p):
    return open(p, encoding='utf-8').read()


# App version and service-worker cache name must move together, or installed phones never update.
app_v = re.search(r"APP_VERSION = '(\d+)'", read('src/app.js')).group(1)
sw_v = re.search(r"VERSION = 'fieldkit-v(\d+)'", read('src/sw.js')).group(1)
if app_v != sw_v:
    sys.exit(f'Version mismatch: src/app.js APP_VERSION = {app_v}, src/sw.js VERSION = fieldkit-v{sw_v}. Set both to the same number.')

shell = read('src/shell.html')
surv = read('src/survival.html').strip()
emerg = read('src/emergency.html').strip()


def fig(m):
    name, cap = m.group(1), m.group(2)
    svg, label = figs.F[name]
    return (f'<figure class="fig"><button type="button" aria-label="Enlarge diagram: {html.escape(label)}">{svg}</button>'
            f'<figcaption>{cap}</figcaption></figure>')


surv = re.sub(r'\{\{fig:([\w-]+)\|([^}]*)\}\}', fig, surv)
assert '{{fig' not in surv
a = shell.index('<section class="tab" id="tab-survival" hidden>')
b = shell.index('</section>', a) + len('</section>')
shell = shell[:a] + surv + shell[b:]
a = shell.index('<section class="tab" id="tab-emergency" hidden>')
b = shell.index('</section>', a) + len('</section>')
shell = shell[:a] + emerg + shell[b:]
shell = shell.replace('</style>', read('figs/figs.css') + '\n</style>', 1)
shell = shell.replace('<body>\n', '<body>\n' + read('figs/markers.html'), 1)
js = '\n'.join(read('src/' + f) for f in ['geo.js', 'ballistics.js', 'app.js', 'router.js', 'emergency.js', 'emergency-tools.js', 'protocol.js', 'map.js', 'survival.js'])

# Protocols: validate every src/protocols/*.json, then inline as window.FK_DATA (sorted by id).
protocols = []
for path in sorted(glob.glob('src/protocols/*.json')):
    try:
        protocols.append(json.loads(read(path)))
    except ValueError as e:
        sys.exit(f'{path}: invalid JSON: {e}')
errors, warnings = validate(protocols, set(figs.F))
for w in warnings:
    print('warning:', w)
if RELEASE:
    errors += [f'{pid}: draft protocol not allowed in a --release build' for pid in draft_ids(protocols)]
if errors:
    sys.exit('Protocol validation failed:\n  ' + '\n  '.join(errors))
protocols.sort(key=lambda p: p['id'])
for p in protocols:
    for s in p['steps']:
        if 'fig' in s:
            s['figSvg'], _ = figs.F[s['fig']]
fk_data = json.dumps({'protocols': protocols}, ensure_ascii=False, separators=(',', ':')).replace('</', '<\\/')

os.makedirs(OUT, exist_ok=True)
with open(os.path.join(OUT, 'index.html'), 'w', encoding='utf-8', newline='\n') as f:
    marker = '<script>\n/*__SCRIPTS__*/'
    assert marker in shell, 'scripts marker missing from shell.html'
    shell = shell.replace(marker, '<script>window.FK_DATA=' + fk_data + ';</script>\n' + marker, 1)
    assert shell.count('window.FK_DATA=') == 1, 'FK_DATA script was not inserted'
    f.write(shell.replace('/*__SCRIPTS__*/', js))
for f in ['manifest.json', 'sw.js']:
    shutil.copyfile('src/' + f, os.path.join(OUT, f))
for f in ['leaflet.js', 'leaflet.css']:
    shutil.copyfile('vendor/' + f, os.path.join(OUT, f))
print(f'Built v{app_v} into {OUT}: {surv.count("<figure")} diagrams, index.html {os.path.getsize(os.path.join(OUT, "index.html")):,} bytes')
