"""Backup, restore and v5 -> current migration."""
import json, os, re

from .test_tools import T0

FIX = os.path.join(os.path.dirname(__file__), 'fixtures')
V5_LS = json.load(open(os.path.join(FIX, 'v5-localstorage.json')))
V5_BACKUP_PATH = os.path.join(FIX, 'v5-backup.json')


def seed(page, raw):
    """Write raw localStorage strings once, before the app boots (the guard keeps the reload after a restore from re-seeding)."""
    page.add_init_script("if (!sessionStorage.getItem('seeded')) { sessionStorage.setItem('seeded', '1'); const d = %s;"
                         " for (const k in d) localStorage.setItem(k, d[k]); }" % json.dumps(raw))


def boot(page, app_url, raw=None, hash_='', clock=False):
    if clock:
        page.clock.install(time=T0 // 1000)
    seed(page, {'fk.advAck': 'true', **(raw or {})})
    page.goto(app_url + hash_)
    page.wait_for_function('window.FK && FK.tools && FK.tools.cpr')


def ls(page, key):
    return page.evaluate('k => localStorage.getItem(k)', 'fk.' + key)


def open_menu(page):
    page.click('#menuBtn')
    page.wait_for_selector('#dlgMenu[open]')


def backup(page, tmp_path):
    open_menu(page)
    with page.expect_download() as d:
        page.click('#bkSave')
    path = tmp_path / 'b.json'
    d.value.save_as(path)
    return json.loads(path.read_text())


def pick(page, tmp_path, obj):
    path = tmp_path / 'pick.json'
    path.write_text(obj if isinstance(obj, str) else json.dumps(obj))
    open_menu(page)
    page.set_input_files('#bkFile', str(path))


def wait_out_ignore(page):
    page.wait_for_timeout(page.evaluate('FK.tools.confirm.ignoreMs') + 100)


def restore_now(page):
    """Two-step confirm, then wait for the reload the restore ends with."""
    page.wait_for_selector('#bkConfirm:not([hidden])')
    page.click('#bkGo')
    assert page.inner_text('#bkGo') == 'Confirm restore'
    wait_out_ignore(page)
    with page.expect_navigation():
        page.click('#bkGo')
    page.wait_for_function('window.FK && FK.tools && FK.tools.cpr')


def backup_file(data, version='5'):
    return {'app': 'Field Kit', 'version': version, 'saved': '2026-11-10T14:30:00.000Z', 'data': data}


# ---------- Backup ----------

def test_backup_includes_pins_recent_patients_but_not_advAck(page, app_url, tmp_path):
    raw = {'fk.pins': json.dumps(['p:bleeding']), 'fk.recent': json.dumps(['p:cpr-adult']),
           'fk.patients': json.dumps([{'id': 'p1', 'name': 'Casualty 1', 'created': T0, 'entries': []}]),
           'fk.nineLine': json.dumps({'view': 'form', 'form': {}}), 'fk.tq': json.dumps([])}
    boot(page, app_url, raw)
    b = backup(page, tmp_path)
    assert b['app'] == 'Field Kit'
    for k in ('fk.pins', 'fk.recent', 'fk.patients', 'fk.nineLine', 'fk.tq'):
        assert k in b['data'], k
    assert 'fk.advAck' not in b['data']   # a backup handed to someone else must not skip their advanced warning
    assert not {'fk.advAck', 'fk.proto.active', 'fk.lastFix'} & set(b['data'])   # the keys that stay on the phone
    assert json.loads(b['data']['fk.pins']) == ['p:bleeding']
    msg = page.inner_text('#bkMsg')
    assert 'This file includes patient logs. Keep it private.' in msg


def test_backup_message_omits_patient_note_when_no_logs(page, app_url, tmp_path):
    boot(page, app_url, {'fk.patients': '[]'})
    backup(page, tmp_path)
    assert 'patient' not in page.inner_text('#bkMsg')


def test_backup_excludes_proto_active_and_lastFix(page, app_url, tmp_path):
    boot(page, app_url, {'fk.proto.active': json.dumps({'id': 'bleeding', 'step': 1}), 'fk.lastFix': V5_LS['fk.lastFix'], 'fk.night': 'true'})
    b = backup(page, tmp_path)
    assert 'fk.proto.active' not in b['data'] and 'fk.lastFix' not in b['data']
    assert 'fk.night' in b['data']


# ---------- Restore ----------

def test_restore_v5_backup_loads_waypoints_tq_profiles_and_leaves_new_keys_empty(page, app_url, tmp_path):
    boot(page, app_url, {'fk.pins': json.dumps(['p:bleeding'])})
    pick(page, tmp_path, json.load(open(V5_BACKUP_PATH)))
    page.wait_for_selector('#bkConfirm:not([hidden])')
    assert 'Restore the backup from' in page.inner_text('#bkAsk')
    assert 'patient logs' in page.inner_text('#bkAsk')
    restore_now(page)
    assert [w['name'] for w in json.loads(ls(page, 'wps'))] == ['Truck', 'Water cache']
    assert ls(page, 'target') == '"k3a9x1"'
    assert json.loads(ls(page, 'tq'))[0]['limb'] == 'Left leg'
    assert json.loads(ls(page, 'profiles'))[0]['name'] == 'My 6mm ARC'
    for k in ('pins', 'recent', 'patients', 'nineLine', 'proto.active'):
        assert ls(page, k) is None, k
    assert page.evaluate('FK.pins.all().length + FK.recent.all().length + FK.patients.all().length') == 0


def test_restore_ignores_session_only_keys_in_file_and_leaves_phone_ones(page, app_url, tmp_path):
    boot(page, app_url)
    here = page.evaluate('''() => { const p = FK_DATA.protocols[0]; return JSON.stringify({ id: p.id, step: p.steps[0].id, started: 1 }); }''')
    page.evaluate('([a, f]) => { localStorage.setItem("fk.proto.active", a); localStorage.setItem("fk.lastFix", f); }', [here, '{"lat":1,"lon":2,"t":3}'])
    pick(page, tmp_path, backup_file({'fk.proto.active': '{"id":"x"}', 'fk.lastFix': V5_LS['fk.lastFix'], 'fk.night': 'true'}))
    restore_now(page)
    assert ls(page, 'proto.active') == here
    assert ls(page, 'lastFix') == '{"lat":1,"lon":2,"t":3}'
    assert ls(page, 'night') == 'true'


def test_restore_replaces_keys_missing_from_file(page, app_url, tmp_path):
    boot(page, app_url, {'fk.pins': json.dumps(['p:bleeding']), 'fk.wps': '[]', 'fk.night': 'false', 'other.key': 'keep'})
    pick(page, tmp_path, backup_file({'fk.night': 'true'}))
    restore_now(page)
    assert ls(page, 'night') == 'true'
    assert ls(page, 'pins') is None and ls(page, 'wps') is None
    assert page.evaluate("localStorage.getItem('other.key')") == 'keep'


def test_restore_cancel_changes_nothing(page, app_url, tmp_path):
    boot(page, app_url, {'fk.night': 'false'})
    pick(page, tmp_path, backup_file({'fk.night': 'true'}))
    page.wait_for_selector('#bkConfirm:not([hidden])')
    page.click('#bkGo')
    page.click('#bkNo')
    assert page.is_hidden('#bkConfirm')
    assert page.inner_text('#bkGo') == 'Restore'
    assert ls(page, 'night') == 'false'


def test_restore_second_tap_too_fast_is_ignored(page, app_url, tmp_path):
    boot(page, app_url, {'fk.night': 'false'})
    pick(page, tmp_path, backup_file({'fk.night': 'true'}))
    page.wait_for_selector('#bkConfirm:not([hidden])')
    page.click('#bkGo'); page.click('#bkGo')
    page.wait_for_timeout(100)
    assert ls(page, 'night') == 'false'
    assert page.inner_text('#bkGo') == 'Confirm restore'


def test_restore_is_atomic_when_storage_fills(page, app_url, tmp_path):
    before = {'fk.night': 'false', 'fk.wps': '[]', 'fk.pins': json.dumps(['p:bleeding'])}
    boot(page, app_url, before)
    pick(page, tmp_path, backup_file({'fk.night': 'true', 'fk.wps': V5_LS['fk.wps'], 'fk.tq': V5_LS['fk.tq']}))
    page.wait_for_selector('#bkConfirm:not([hidden])')
    page.click('#bkGo')
    wait_out_ignore(page)
    # The third write of the restore fails once, as a full phone would; the rollback writes then succeed.
    page.evaluate("""() => {
      const orig = Storage.prototype.setItem; let n = 0;
      Storage.prototype.setItem = function (k, v) { if (++n === 3) throw new DOMException('full', 'QuotaExceededError'); return orig.call(this, k, v); };
    }""")
    page.click('#bkGo')
    assert 'nothing was changed' in page.inner_text('#bkMsg')
    for k, v in before.items():
        assert page.evaluate('k => localStorage.getItem(k)', k) == v, k
    assert ls(page, 'tq') is None
    assert page.evaluate('performance.getEntriesByType("navigation").length') == 1


def test_restore_rejects_bad_files_and_writes_nothing(page, app_url, tmp_path):
    boot(page, app_url, {'fk.night': 'false'})
    bad = [backup_file({'fk.night': True}), backup_file(['fk.night']), backup_file(None), backup_file({'fk.night': 5}),
           {'app': 'Other', 'version': '5', 'data': {}}, '{not json']
    for obj in bad:
        pick(page, tmp_path, obj)
        page.wait_for_function("document.getElementById('bkMsg').textContent")
        assert 'isn’t a Field Kit backup' in page.inner_text('#bkMsg'), obj
        assert page.is_hidden('#bkConfirm')
        page.click('#menuClose')
        assert ls(page, 'night') == 'false'


def test_restore_refuses_newer_backup_and_accepts_older(page, app_url, tmp_path):
    boot(page, app_url, {'fk.night': 'false'})
    pick(page, tmp_path, backup_file({'fk.night': 'true'}, version='999'))
    page.wait_for_function("document.getElementById('bkMsg').textContent")
    assert page.inner_text('#bkMsg') == 'This backup is from a newer version of Field Kit. Update the app first.'
    assert page.is_hidden('#bkConfirm') and ls(page, 'night') == 'false'
    page.click('#menuClose')
    pick(page, tmp_path, backup_file({'fk.night': 'true'}, version='1'))
    restore_now(page)
    assert ls(page, 'night') == 'true'


def test_restore_accepts_dotted_versions_and_compares_them_as_numbers(page, app_url, tmp_path):
    boot(page, app_url, {'fk.night': 'false'})
    src = open(os.path.join(os.path.dirname(__file__), '..', 'src', 'app.js'), encoding='utf-8').read()
    mine = re.search(r"APP_VERSION = '([\d.]+)'", src).group(1)
    major, _, minor = mine.partition('.')
    newer = f'{major}.{int(minor or 0) + 1}'
    pick(page, tmp_path, backup_file({'fk.night': 'true'}, version=newer))   # one point release ahead: refused
    page.wait_for_function("document.getElementById('bkMsg').textContent")
    assert page.inner_text('#bkMsg') == 'This backup is from a newer version of Field Kit. Update the app first.'
    page.click('#menuClose')
    for v in (mine, '6.1', '5.10'):   # the app's own version, the first dotted release, and an older dotted one
        page.evaluate("localStorage.setItem('fk.night', 'false')")
        pick(page, tmp_path, backup_file({'fk.night': 'true'}, version=v))
        restore_now(page)
        assert ls(page, 'night') == 'true', v


# ---------- Migration: a phone carrying v5 data ----------

def test_v5_localstorage_boots_with_no_console_errors(page, app_url):
    snapshot = dict(V5_LS)
    boot(page, app_url, snapshot, clock=True)
    # Stored tab and view are honoured (no hash given)
    assert page.evaluate('[FK.tab(), FK.view()]') == ['tactical', 'ballistics']
    assert page.evaluate("document.querySelector('.tabbar [aria-current=page]').dataset.tab") == 'tactical'
    # Rifle profile is selectable and fills the load fields
    assert page.input_value('#bProfile') == 'u1k2j3x'
    page.select_option('#bProfile', 'p308')
    assert page.input_value('#bMV') == '2600'
    page.select_option('#bProfile', 'u1k2j3x')
    assert page.input_value('#bMV') == '2850' and page.input_value('#bW') == '105'
    assert page.input_value('#bRange') == '650'
    # Waypoints are listed and the target is still the target
    page.click('#tacSeg [data-view=position]')
    names = page.locator('#wpList li .wname').all_inner_texts()
    assert names == ['Truck', 'Water cache']
    assert page.locator('#wpList li.target .wname').all_inner_texts() == ['Water cache']
    # Tourniquet timer: running, 14:32 elapsed at the fixed clock, listed on the Emergency home
    page.goto(page.url.split('#')[0] + '#/emergency')
    page.wait_for_selector('#emActive .em-active')
    assert 'TQ left leg' in page.inner_text('#emActive')
    assert page.inner_text('#emActive b') == '0:14:32'
    # Nothing was rewritten in a different shape
    for k, v in snapshot.items():
        if k in ('fk.tab', 'fk.view', 'fk.night', 'fk.bal', 'fk.lastFix'):
            continue   # the app legitimately re-saves these on start
        assert page.evaluate('k => localStorage.getItem(k)', k) == v, k


# ---------- Review fixes ----------

def test_restore_reports_when_rollback_also_fails(page, app_url, tmp_path):
    boot(page, app_url, {'fk.night': 'false', 'fk.wps': '[]', 'fk.pins': json.dumps(['p:bleeding'])})
    pick(page, tmp_path, backup_file({'fk.night': 'true', 'fk.wps': V5_LS['fk.wps'], 'fk.tq': V5_LS['fk.tq']}))
    page.wait_for_selector('#bkConfirm:not([hidden])')
    page.click('#bkGo')
    wait_out_ignore(page)
    page.evaluate("""() => {
      const orig = Storage.prototype.setItem; let n = 0;
      Storage.prototype.setItem = function (k, v) { if (++n >= 3) throw new DOMException('full', 'QuotaExceededError'); return orig.call(this, k, v); };
    }""")
    page.click('#bkGo')
    msg = page.inner_text('#bkMsg')
    assert msg == 'Restore failed and some data on this phone may have changed. Back up now if you can, then try again.'
    assert 'nothing was changed' not in msg


def test_restore_refuses_a_backup_with_nothing_to_restore(page, app_url, tmp_path):
    boot(page, app_url, {'fk.night': 'false', 'fk.pins': json.dumps(['p:bleeding'])})
    for data in ({}, {'fk.proto.active': '{}', 'fk.lastFix': '{}'}, {'other.key': 'x'}):
        pick(page, tmp_path, backup_file(data))
        page.wait_for_function("document.getElementById('bkMsg').textContent")
        assert page.inner_text('#bkMsg') == 'That backup is empty, so nothing was restored.'
        assert page.is_hidden('#bkConfirm')
        page.click('#menuClose')
        assert ls(page, 'night') == 'false' and ls(page, 'pins') == json.dumps(['p:bleeding'])


def test_restore_version_missing_is_older_and_garbage_is_not_a_backup(page, app_url, tmp_path):
    boot(page, app_url, {'fk.night': 'false'})
    for v in ('abc', '5.x', '5.1.2', '.5', '', None):
        pick(page, tmp_path, backup_file({'fk.night': 'true'}, version=v))
        page.wait_for_function("document.getElementById('bkMsg').textContent")
        assert 'isn’t a Field Kit backup' in page.inner_text('#bkMsg'), v
        assert page.is_hidden('#bkConfirm')
        page.click('#menuClose')
    assert ls(page, 'night') == 'false'
    f = backup_file({'fk.night': 'true'})
    del f['version']
    pick(page, tmp_path, f)
    restore_now(page)
    assert ls(page, 'night') == 'true'


def test_restore_is_not_overwritten_by_a_pending_mist_note(page, app_url, tmp_path):
    phone = [{'id': 'p1', 'name': 'Casualty 1', 'created': T0, 'entries': []}]
    theirs = [{'id': 'p1', 'name': 'Casualty 1', 'created': T0 + 1, 'entries': [{'t': T0, 'kind': 'note', 'text': 'from file'}]}]
    boot(page, app_url, {'fk.patients': json.dumps(phone)}, hash_='#/emergency/report/mist')
    page.wait_for_selector('#msM')
    path = tmp_path / 'p.json'
    path.write_text(json.dumps(backup_file({'fk.patients': json.dumps(theirs)})))
    page.evaluate("document.getElementById('dlgMenu').showModal()")
    page.set_input_files('#bkFile', str(path))
    page.wait_for_selector('#bkConfirm:not([hidden])')
    page.click('#bkGo')
    wait_out_ignore(page)
    with page.expect_navigation():
        # type and confirm in one synchronous step, so the 300 ms save timer is still pending when the restore runs
        page.evaluate("""() => { const m = document.getElementById('msM'); m.value = 'half-typed note';
          m.dispatchEvent(new Event('input', { bubbles: true })); document.getElementById('bkGo').click(); }""")
    page.wait_for_function('window.FK && FK.tools && FK.tools.cpr')
    assert json.loads(ls(page, 'patients')) == theirs


def test_restore_ignores_advAck_in_the_file_and_keeps_the_phones(page, app_url, tmp_path):
    boot(page, app_url, {'fk.night': 'false'})
    page.evaluate("localStorage.removeItem('fk.advAck')")
    pick(page, tmp_path, backup_file({'fk.advAck': 'true', 'fk.night': 'true'}))
    restore_now(page)
    assert ls(page, 'night') == 'true'
    assert ls(page, 'advAck') is None   # this phone has not seen the warning, so it still shows
    page.evaluate("localStorage.setItem('fk.advAck', 'true')")
    pick(page, tmp_path, backup_file({'fk.night': 'false'}))
    restore_now(page)
    assert ls(page, 'advAck') == 'true'   # and a restore never takes this phone's own acknowledgement away


def test_restore_keeps_tourniquet_timers_running_on_this_phone(page, app_url, tmp_path):
    mine = [{'id': 'mine1', 'limb': 'Left leg', 'start': T0 - 60_000}, {'id': 'both', 'limb': 'Right arm', 'start': T0 - 30_000}]
    boot(page, app_url, {'fk.tq': json.dumps(mine), 'fk.night': 'false'})
    theirs = [{'id': 'both', 'limb': 'Other', 'start': 1}, {'id': 'file1', 'limb': 'Right leg', 'start': T0 - 90_000}]
    pick(page, tmp_path, backup_file({'fk.tq': json.dumps(theirs), 'fk.night': 'true'}))
    page.wait_for_selector('#bkConfirm:not([hidden])')
    assert 'Running tourniquet timers on this phone are kept.' in page.inner_text('#bkAsk')
    restore_now(page)
    got = json.loads(ls(page, 'tq'))
    assert got == mine + [theirs[1]]   # merged by id, this phone's entry wins
    assert ls(page, 'night') == 'true'
    assert sorted(t['id'] for t in page.evaluate('FK.tools.tq.active()')) == ['both', 'file1', 'mine1']


def test_restore_of_a_file_without_tq_keeps_the_phones_timers(page, app_url, tmp_path):
    mine = [{'id': 'mine1', 'limb': 'Left leg', 'start': T0 - 60_000}]
    boot(page, app_url, {'fk.tq': json.dumps(mine)})
    pick(page, tmp_path, backup_file({'fk.night': 'true'}))
    restore_now(page)
    assert json.loads(ls(page, 'tq')) == mine


# ---------- Water pack (v7.2): the saved group, and topics that moved category (plan Review Focus 4) ----------

def _water_pack_boot(page, app_url, raw=None, hash_='#/survival'):
    from .conftest import inject_data
    from .test_survival_group import QCL, WATER
    moved = [{'id': tid, 'title': title, 'category': 'water', 'keywords': [], 'summary': '',
              'sections': [{'h': 'Fixture', 'blocks': [{'p': 'Fixture text.'}]}],
              'sources': [{'name': 'Fixture source', 'used': 'everything'}], 'reviewed': '2026-11-18'}
             for tid, title in (('surv-find-water', 'Find water outside'), ('surv-make-water-safe', 'Make water safe'))]
    inject_data(page, topics=moved, checklists=[QCL], tooldata={'water': WATER})
    boot(page, app_url, raw, hash_=hash_)


def _app_version():
    src = open(os.path.join(os.path.dirname(__file__), '..', 'src', 'app.js'), encoding='utf-8').read()
    return re.search(r"APP_VERSION = '([\d.]+)'", src).group(1)


def test_v7_backup_without_group_restores_with_the_default_group_and_old_water_pins_and_recents_open(page, app_url, tmp_path):
    _water_pack_boot(page, app_url, {'fk.group': json.dumps({'people': 6, 'days': 30})})
    v7 = backup_file({'fk.pins': json.dumps(['s:surv-find-water']), 'fk.recent': json.dumps(['s:surv-make-water-safe', 'c:ten-essentials']),
                      'fk.checks': json.dumps({'ten-essentials': ['item1']}), 'fk.night': 'false'}, version='7')
    pick(page, tmp_path, v7)
    restore_now(page)
    assert ls(page, 'group') is None   # a backup without a group means no saved group: the defaults apply
    assert page.evaluate('FK.survival.group()') == {'people': 1, 'days': 14}
    page.click('#survPinned button[data-key="s:surv-find-water"]')
    page.wait_for_function("location.hash === '#/survival/surv-find-water'")
    assert page.inner_text('#survPage h2') == 'Find water outside'
    page.go_back()
    page.wait_for_function("location.hash === '#/survival'")
    page.click('#survRecent button[data-key="s:surv-make-water-safe"]')
    page.wait_for_function("location.hash === '#/survival/surv-make-water-safe'")
    assert page.inner_text('#survPage h2') == 'Make water safe'
    assert page.evaluate("FK.survival.open('c:store-water')") is True
    page.wait_for_function("location.hash === '#/survival/list/store-water'")
    assert page.inner_text('#survPage [data-qty="water"]') == '14 gal'
    assert page.locator('#survPage .sv-group').count() == 1


def test_backup_with_group_round_trips_and_a_current_version_file_with_group_restores(page, app_url, tmp_path):
    _water_pack_boot(page, app_url, hash_='#/survival/tool/water')
    page.wait_for_function('FK.survival && FK.survival.group')
    assert page.evaluate('FK.survival.setGroup({ people: 5, days: 21 })') is True
    b = backup(page, tmp_path)
    assert b['version'] == _app_version()
    assert json.loads(b['data']['fk.group']) == {'people': 5, 'days': 21}
    page.click('#menuClose')
    page.evaluate("localStorage.removeItem('fk.group')")
    pick(page, tmp_path, b)
    restore_now(page)
    assert json.loads(ls(page, 'group')) == {'people': 5, 'days': 21}
    assert page.evaluate('FK.survival.group()') == {'people': 5, 'days': 21}
    assert page.inner_text('#survPage [data-k="gal"]') == '105 gallons'
    # a hand-made file at this version (7.2 once the pack ships) carrying a group and the pack's other keys
    f = backup_file({'fk.group': json.dumps({'people': 3, 'days': 7}), 'fk.pins': json.dumps(['u:water', 'c:store-water']),
                     'fk.checks': json.dumps({'store-water': ['water']})}, version=_app_version())
    pick(page, tmp_path, f)
    restore_now(page)
    assert page.evaluate('FK.survival.group()') == {'people': 3, 'days': 7}
    assert page.inner_text('#survPage [data-k="gal"]') == '21 gallons'
    assert page.evaluate('FK.pins.all()') == ['u:water', 'c:store-water']


def test_restored_junk_group_falls_back_to_defaults(page, app_url, tmp_path):
    _water_pack_boot(page, app_url, hash_='#/survival/tool/water')
    for junk in ('"x"', '{"people": 1e9, "days": -3}', '[]'):
        pick(page, tmp_path, backup_file({'fk.group': junk}, version='7'))
        restore_now(page)
        g = page.evaluate('FK.survival.group()')
        assert 1 <= g['people'] <= 50 and 1 <= g['days'] <= 365, junk
        assert 'NaN' not in page.inner_text('#survPage')


# ---------- Heat pack (v7.3): Fire and Shelter moved from Basics to "Heat, shelter and winter" (plan Review Focus 4) ----------

def _open_from(page, sel, key, title):
    page.click(f'{sel} button[data-key="{key}"]')
    page.wait_for_function(f"location.hash === '#/survival/{key[2:]}'")
    assert page.inner_text('#survPage h2') == title
    page.go_back()
    page.wait_for_function("location.hash === '#/survival'")


def test_v72_pins_and_recents_for_fire_and_shelter_open_after_the_move(page, app_url):
    """Shipped data: keys saved by v7.2, when Fire and Shelter were in Basics, still open them."""
    boot(page, app_url, {'fk.pins': json.dumps(['s:surv-fire', 's:surv-shelter']),
                         'fk.recent': json.dumps(['s:surv-shelter', 's:surv-fire'])}, hash_='#/survival')
    page.wait_for_selector('#survHome')
    for sel in ('#survPinned', '#survRecent'):
        _open_from(page, sel, 's:surv-fire', 'Fire')
        _open_from(page, sel, 's:surv-shelter', 'Shelter')


def test_v72_backup_with_fire_and_shelter_keys_restores(page, app_url, tmp_path):
    boot(page, app_url, hash_='#/survival')
    v72 = backup_file({'fk.pins': json.dumps(['s:surv-fire']), 'fk.recent': json.dumps(['s:surv-shelter', 's:surv-fire']),
                       'fk.survFilter': json.dumps({'where': 'any', 'when': 'any'}), 'fk.night': 'false'}, version='7.2')
    pick(page, tmp_path, v72)
    restore_now(page)
    assert page.evaluate('FK.pins.all()') == ['s:surv-fire']
    page.wait_for_function("location.hash === '#/survival'")
    _open_from(page, '#survPinned', 's:surv-fire', 'Fire')
    _open_from(page, '#survRecent', 's:surv-shelter', 'Shelter')


# ---------- Radiation pack (v7.4): a v7.3-shaped backup restores and its keys still open ----------

def test_v73_backup_restores_on_v74_and_its_pins_recents_and_filter_open(page, app_url, tmp_path):
    boot(page, app_url, hash_='#/survival')
    v73 = backup_file({'fk.pins': json.dumps(['s:surv-heat-out', 's:surv-carbon-monoxide']),
                       'fk.recent': json.dumps(['s:surv-priorities', 's:surv-heat-out']),
                       'fk.survFilter': json.dumps({'where': 'rural', 'when': 'cold'}), 'fk.night': 'false'}, version='7.3')
    pick(page, tmp_path, v73)
    restore_now(page)
    assert page.evaluate('FK.pins.all()') == ['s:surv-heat-out', 's:surv-carbon-monoxide']
    page.wait_for_function("location.hash === '#/survival'")
    _open_from(page, '#survPinned', 's:surv-heat-out', 'Stay warm when the heat is out')
    _open_from(page, '#survRecent', 's:surv-priorities', 'Priorities')
    # the restored Rural + Cold filter hides no radiation topic: all ten are listed
    page.locator('#survCats summary', has_text='Radiation and fallout').click()
    listed_keys = page.evaluate("[...document.querySelectorAll('#survCats details[data-cat=\"radiation\"] button[data-key]')].map(b => b.dataset.key)")
    assert len(listed_keys) == 10 and listed_keys[0] == 's:surv-fallout-warning'


# ---------- Food pack (v7.5): a v7.4-shaped backup restores and its keys still open ----------

def test_v74_backup_restores_on_v75_and_its_pins_recents_and_filter_open(page, app_url, tmp_path):
    boot(page, app_url, hash_='#/survival')
    v74 = backup_file({'fk.pins': json.dumps(['s:surv-fallout-warning', 's:surv-heat-out']),
                       'fk.recent': json.dumps(['s:surv-fallout-get-ready', 's:surv-priorities']),
                       'fk.survFilter': json.dumps({'where': 'woods', 'when': 'warm'}), 'fk.night': 'false'}, version='7.4')
    pick(page, tmp_path, v74)
    restore_now(page)
    assert page.evaluate('FK.pins.all()') == ['s:surv-fallout-warning', 's:surv-heat-out']
    page.wait_for_function("location.hash === '#/survival'")
    _open_from(page, '#survPinned', 's:surv-fallout-warning', 'Fallout warning: what to do first')
    _open_from(page, '#survRecent', 's:surv-priorities', 'Priorities')
    # the restored Woods + Warm filter hides no food topic: all ten are listed, the hub first
    page.locator('#survCats summary', has_text='Food').first.click()
    keys = page.evaluate("[...document.querySelectorAll('#survCats details[data-cat=\"food\"] button[data-key]')].map(b => b.dataset.key)")
    assert len(keys) == 10 and keys[0] == 's:surv-food-power-out'
    # a v7.4 file holds no food key; the new topics open from search and from the home
    page.evaluate("FK.route.go('/survival/surv-food-power-out')")
    page.wait_for_function("location.hash === '#/survival/surv-food-power-out'")
