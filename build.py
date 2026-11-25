"""Build Field Kit.   python3 build.py

Reads src/, figs/ and vendor/ and writes the deployable files to the repo root:
index.html, sw.js, manifest.json, leaflet.js, leaflet.css. Those root files are build
output -- edit src/ instead. (Optional: python3 build.py some/dir writes there instead.)
"""
import glob, json, os, re, shutil, sys

ROOT = os.path.dirname(os.path.abspath(__file__))
ARGS = [a for a in sys.argv[1:] if a != '--release']
RELEASE = '--release' in sys.argv[1:]
_unknown = [a for a in ARGS if a.startswith('-')]
if _unknown or len(ARGS) > 1:
    sys.exit(f'Unknown option {_unknown[0]!r}. Usage: python3 build.py [--release] [output-dir]' if _unknown
             else 'Too many arguments. Usage: python3 build.py [--release] [output-dir]')
OUT = os.path.abspath(ARGS[0]) if ARGS else ROOT
os.chdir(ROOT)
sys.path.insert(0, 'figs')
sys.path.insert(0, ROOT)
import figs
from tools.validate import (TOOL_NAMES, draft_ids, report_wording_is_draft, topic_draft_ids, validate, validate_checklists,
                            validate_tooldata, validate_topics)


def read(p):
    return open(p, encoding='utf-8').read()


# App version and service-worker cache name must move together, or installed phones never update.
app_v = re.search(r"APP_VERSION = '(\d+(?:\.\d+)?)'", read('src/app.js')).group(1)
sw_v = re.search(r"VERSION = 'fieldkit-v(\d+(?:\.\d+)?)'", read('src/sw.js')).group(1)
if app_v != sw_v:
    sys.exit(f'Version mismatch: src/app.js APP_VERSION = {app_v}, src/sw.js VERSION = fieldkit-v{sw_v}. Set both to the same number.')

shell = read('src/shell.html')
surv = read('src/survival.html').strip()
emerg = read('src/emergency.html').strip()

a = shell.index('<section class="tab" id="tab-survival" hidden>')
b = shell.index('</section>', a) + len('</section>')
shell = shell[:a] + surv + shell[b:]
a = shell.index('<section class="tab" id="tab-emergency" hidden>')
b = shell.index('</section>', a) + len('</section>')
shell = shell[:a] + emerg + shell[b:]
shell = shell.replace('</style>', read('figs/figs.css') + '\n</style>', 1)
shell = shell.replace('<body>\n', '<body>\n' + read('figs/markers.html'), 1)
js = '\n'.join(read('src/' + f) for f in ['astro.js', 'geo.js', 'tac-geom.js', 'wmm.js', 'mesh-pb.js', 'mesh-link.js', 'mesh-marker.js', 'ballistics.js', 'bal-spin.js', 'bal-zero.js', 'bal-sight.js', 'app.js', 'sheet.js', 'bal-ui.js', 'bal-edit.js', 'bal-tools.js', 'tac-data.js', 'mesh.js', 'tac-share.js', 'router.js', 'emergency.js', 'emergency-tools.js', 'patients.js', 'reports.js', 'protocol.js', 'search.js', 'map.js', 'tac-markers.js', 'mesh-ui.js', 'tac-team.js', 'tac-tools.js', 'tac-shapes.js', 'tac-nav.js', 'tac-io.js', 'survival.js', 'survival-tools.js'])

# Protocols, topics, checklists and tool data: validate every JSON file, then inline as window.FK_DATA (sorted by id).
def load_json_dir(pattern):
    items = []
    for path in sorted(glob.glob(pattern)):
        try:
            items.append(json.loads(read(path)))
        except ValueError as e:
            sys.exit(f'{path}: invalid JSON: {e}')
    return items


protocols = load_json_dir('src/protocols/*.json')
topics = load_json_dir('src/survival/*.json')
checklists = load_json_dir('src/checklists/*.json')
tooldata = load_json_dir('src/tooldata/*.json')  # the directory may not exist yet: no files, no tool data


def ids_of(items):
    return [x['id'] for x in items if isinstance(x, dict) and isinstance(x.get('id'), str)]


# Link keys a topic block may point at (spec section 5.3).
link_keys = {f'p:{i}' for i in ids_of(protocols)} | {f's:{i}' for i in ids_of(topics)} | {f'c:{i}' for i in ids_of(checklists)}
link_keys |= {f'u:{n}' for n in TOOL_NAMES}
link_keys |= {'t:tq', 't:cpr', 't:rate', 't:burn', 'r:9line', 'r:mist'}
link_keys |= {f'a:{n}' for n in ('map', 'position', 'ballistics', 'areas', 'waypoints', 'settings')}

errors, warnings = validate(protocols, set(figs.F))
for check in (validate_topics(topics, set(figs.F), link_keys), validate_checklists(checklists, link_keys),
              validate_tooldata(tooldata)):
    errors += check[0]
    warnings += check[1]
errors += [f'topic {i!r}: id equals a protocol id' for i in sorted(set(ids_of(topics)) & set(ids_of(protocols)))]
for w in warnings:
    print('warning:', w)
if RELEASE:
    errors += [f'{pid}: draft protocol not allowed in a --release build' for pid in draft_ids(protocols)]
    errors += [f'{tid}: draft topic not allowed in a --release build' for tid in topic_draft_ids(topics)]
    errors += [f'{cid}: draft checklist not allowed in a --release build' for cid in topic_draft_ids(checklists)]
    errors += [f'{tid}: draft tool data not allowed in a --release build' for tid in topic_draft_ids(tooldata)]
if RELEASE and report_wording_is_draft(read('src/reports.js')):
    errors.append('src/reports.js: report wording is still marked draft (REPORT_WORDING_DRAFT); check it against its source, then remove the marker line and set draft: false')
if errors:
    sys.exit('Validation failed:\n  ' + '\n  '.join(errors))
protocols.sort(key=lambda p: p['id'])
topics.sort(key=lambda t: t['id'])
checklists.sort(key=lambda c: c['id'])
tooldata_by_id = {d['id']: d for d in sorted(tooldata, key=lambda d: d['id'])}
for p in protocols:
    for s in p['steps']:
        if 'fig' in s:
            s['figSvg'], _ = figs.F[s['fig']]
for t in topics:
    for sec in t['sections']:
        for blk in sec['blocks']:
            if 'fig' in blk:
                blk['figSvg'], blk['figLabel'] = figs.F[blk['fig']]
fk_data = json.dumps({'protocols': protocols, 'topics': topics, 'checklists': checklists, 'tooldata': tooldata_by_id},
                     ensure_ascii=False, separators=(',', ':')).replace('</', '<\\/')

# Every check runs before the output file is opened, so a failure cannot leave an empty index.html behind.
marker = '<script>\n/*__SCRIPTS__*/'
if marker not in shell:
    sys.exit('src/shell.html: scripts marker missing')
shell = shell.replace(marker, '<script>window.FK_DATA=' + fk_data + ';</script>\n' + marker, 1)
if shell.count('window.FK_DATA=') != 1:
    sys.exit('FK_DATA script was not inserted exactly once')
page = shell.replace('/*__SCRIPTS__*/', js)

os.makedirs(OUT, exist_ok=True)
with open(os.path.join(OUT, 'index.html'), 'w', encoding='utf-8', newline='\n') as f:
    f.write(page)
for f in ['manifest.json', 'sw.js']:
    shutil.copyfile('src/' + f, os.path.join(OUT, f))
for f in ['leaflet.js', 'leaflet.css']:
    shutil.copyfile('vendor/' + f, os.path.join(OUT, f))
fig_count = sum('fig' in blk for t in topics for sec in t['sections'] for blk in sec['blocks'])
print(f'Built v{app_v} into {OUT}: {fig_count} diagrams, index.html {os.path.getsize(os.path.join(OUT, "index.html")):,} bytes')
