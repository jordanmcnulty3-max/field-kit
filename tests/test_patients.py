import json

from .test_tools import T0, boot, proto

BURNS = proto('burns', 'Burns', category='injury', evacuate=['Burn bigger than the casualty palm', '<b>Face</b> or hands burned'],
              notes=['Count <i>only</i> this', 'Second note'])
LOG_STEP = proto('logged', 'Logged', steps=[{'id': 's1', 'text': 'First.', 'log': 'Pressure applied'}, {'id': 's2', 'text': 'Second.'}])


def stored(page):
    return json.loads(page.evaluate("localStorage.getItem('fk.patients')"))


def pts(**kw):
    return {'id': 'p1', 'name': 'Casualty 1', 'created': T0, 'entries': [], **kw}


def e(t, text, kind='note', **kw):
    return {'t': t, 'kind': kind, 'text': text, **kw}


def test_first_log_creates_casualty_1(page, app_url):
    boot(page, app_url)
    assert page.evaluate('FK.patients.all().length') == 0
    assert page.evaluate("FK.log('Tourniquet applied: Left leg')") is True
    s = stored(page)
    assert len(s) == 1 and s[0]['name'] == 'Casualty 1'
    assert [x['text'] for x in s[0]['entries']] == ['Tourniquet applied: Left leg']
    assert s[0]['entries'][0]['kind'] == 'event' and s[0]['entries'][0]['t'] >= T0
    assert page.evaluate('FK.patients.current().name') == 'Casualty 1'


def test_protocol_step_with_log_adds_event_entry(page, app_url):
    boot(page, app_url, fixtures=[LOG_STEP], hash_='#/emergency/logged')
    page.wait_for_selector('#player:not([hidden])')
    page.click('#player .pp-foot .btn:not(.back)')
    entries = stored(page)[0]['entries']
    assert [(x['kind'], x['text']) for x in entries] == [('event', 'Pressure applied')]


def test_rate_counter_15_taps_in_15s_reads_60(page, app_url):
    boot(page, app_url, hash_='#/emergency/tool/rate')
    for _ in range(15):
        page.click('#rateTap')
        page.clock.run_for(900)
    page.clock.run_for(2000)
    assert page.inner_text('#rateResult') == '60'
    assert page.is_disabled('#rateTap')   # window is over: taps do nothing
    page.evaluate("document.getElementById('rateTap').click()")
    assert page.inner_text('#rateResult') == '60'
    page.click('#rateSavePulse')
    s = stored(page)[0]['entries'][-1]
    assert s['kind'] == 'vitals' and s['pulse'] == 60
    page.click('#rateRestart')
    assert page.inner_text('#rateResult') == ''
    for _ in range(4):
        page.click('#rateTap')
        page.clock.run_for(100)
    page.clock.run_for(15000)
    page.click('#rateSaveResp')
    assert stored(page)[0]['entries'][-1]['resp'] == 16


def test_rate_counter_window_starts_on_first_tap_and_counts_down(page, app_url):
    boot(page, app_url, hash_='#/emergency/tool/rate')
    page.clock.run_for(20000)   # waiting does not start the window
    assert '15' in page.inner_text('#rateClock')
    page.click('#rateTap')
    page.clock.run_for(5000)
    assert '10' in page.inner_text('#rateClock')


def burn(page, *names):
    for n in names:
        page.locator(f'#burnSvg [aria-label^="{n}, "]').first.click()


def test_burn_adult_one_arm_and_chest_reads_18(page, app_url):
    boot(page, app_url, hash_='#/emergency/tool/burn')
    burn(page, 'Left arm', 'Chest')
    assert page.inner_text('#burnTotal').strip() == '18%'
    assert 'left arm' in page.inner_text('#burnList').lower() and 'chest' in page.inner_text('#burnList').lower()
    assert page.get_attribute('#burnSvg [aria-label^="Left arm, "]', 'aria-pressed') == 'true'
    assert page.get_attribute('#burnSvg [aria-label^="Left arm, "]', 'aria-label') == 'Left arm, 9 percent'
    page.click('#burnSave')
    assert stored(page)[0]['entries'][-1]['text'] == 'Burn area about 18% (adult): left arm, chest'


def test_burn_adult_table_totals_100(page, app_url):
    boot(page, app_url, hash_='#/emergency/tool/burn')
    page.evaluate("document.querySelectorAll('#burnSvg [role=button]').forEach(b => b.dispatchEvent(new MouseEvent('click', {bubbles: true})))")
    assert page.inner_text('#burnTotal').strip() == '100%'


def test_burn_child_head_reads_18_and_child_table_totals_100(page, app_url):
    boot(page, app_url, hash_='#/emergency/tool/burn')
    page.click('#burnMode [data-mode="child"]')
    burn(page, 'Head')
    assert page.inner_text('#burnTotal').strip() == '18%'
    page.evaluate("document.querySelectorAll('#burnSvg [role=button]').forEach(b => { if (b.getAttribute('aria-pressed') !== 'true') b.dispatchEvent(new MouseEvent('click', {bubbles: true})) })")
    assert page.inner_text('#burnTotal').strip() == '100%'


def test_burn_regions_are_at_least_56px_in_both_dimensions_in_both_modes(page, app_url):
    boot(page, app_url, hash_='#/emergency/tool/burn')
    for mode in ('adult', 'child'):
        page.click(f'#burnMode [data-mode="{mode}"]')
        regions = page.locator('#burnSvg [role=button]').all()
        assert len(regions) == (10 if mode == 'adult' else 7)
        for loc in regions:
            loc.scroll_into_view_if_needed()
            b = loc.bounding_box()
            assert min(b['width'], b['height']) >= 56, (mode, loc.get_attribute('aria-label'), b)
    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')


def burn_child(page, age):
    page.click('#burnMode [data-mode="child"]')
    page.select_option('#burnAge', str(age))


def burn_pct(page, name):
    label = page.get_attribute(f'#burnSvg [aria-label^="{name}, "]', 'aria-label')
    return label


def test_burn_mode_labels_and_age_selector_only_in_child_mode(page, app_url):
    boot(page, app_url, hash_='#/emergency/tool/burn')
    assert page.inner_text('#burnMode [data-mode="adult"]').strip() == 'Adult (9 and over)'
    assert page.inner_text('#burnMode [data-mode="child"]').strip() == 'Child (under 9)'
    assert not page.locator('#burnAge').is_visible()
    page.click('#burnMode [data-mode="child"]')
    assert page.locator('#burnAge').is_visible()
    assert page.locator('label[for="burnAge"]').count() == 1
    opts = page.eval_on_selector_all('#burnAge option', 'os => os.map(o => [o.value, o.textContent.trim()])')
    assert [v for v, _ in opts] == [str(i) for i in range(9)]
    assert opts[0][1] == 'Under 1 year'
    assert page.eval_on_selector('#burnAge', 'e => e.getBoundingClientRect().height') >= 56


def test_burn_child_age_0_is_head_18_leg_14(page, app_url):
    boot(page, app_url, hash_='#/emergency/tool/burn')
    page.click('#burnMode [data-mode="child"]')
    assert page.input_value('#burnAge') == '0'
    assert burn_pct(page, 'Head') == 'Head, 18 percent (child, under 1)'
    assert burn_pct(page, 'Left leg') == 'Left leg, 14 percent (child, under 1)'
    assert burn_pct(page, 'Left arm') == 'Left arm, 9 percent (child, under 1)'


def test_burn_child_age_5_is_head_13_leg_16_5_and_note_names_age(page, app_url):
    boot(page, app_url, hash_='#/emergency/tool/burn')
    burn_child(page, 5)
    assert burn_pct(page, 'Head') == 'Head, 13 percent (child, age 5)'
    assert burn_pct(page, 'Right leg') == 'Right leg, 16.5 percent (child, age 5)'
    burn(page, 'Left leg')
    assert page.inner_text('#burnTotal').strip() == '16.5%'
    page.click('#burnSave')
    assert stored(page)[0]['entries'][-1]['text'] == 'Burn area about 16.5% (child, age 5): left leg'


def test_burn_child_age_8_is_head_10_leg_18(page, app_url):
    boot(page, app_url, hash_='#/emergency/tool/burn')
    burn_child(page, 8)
    assert burn_pct(page, 'Head') == 'Head, 10 percent (child, age 8)'
    assert burn_pct(page, 'Left leg') == 'Left leg, 18 percent (child, age 8)'
    assert 'Head 10%' not in page.inner_text('#burnList')   # nothing selected yet
    assert '10%' in page.inner_text('#burnSvg')


def test_burn_child_total_is_100_at_every_age(page, app_url):
    boot(page, app_url, hash_='#/emergency/tool/burn')
    page.click('#burnMode [data-mode="child"]')
    for age in range(9):
        page.select_option('#burnAge', str(age))
        page.evaluate("document.querySelectorAll('#burnSvg [role=button]').forEach(b => { if (b.getAttribute('aria-pressed') !== 'true') b.dispatchEvent(new MouseEvent('click', {bubbles: true})) })")
        assert page.inner_text('#burnTotal').strip() == '100%', age
        page.click('#burnClear')


def test_burn_changing_age_keeps_selection_and_updates_total(page, app_url):
    boot(page, app_url, hash_='#/emergency/tool/burn')
    page.click('#burnMode [data-mode="child"]')
    burn(page, 'Head', 'Left leg')
    assert page.inner_text('#burnTotal').strip() == '32%'
    page.select_option('#burnAge', '4')
    assert page.get_attribute('#burnSvg [aria-label^="Head, "]', 'aria-pressed') == 'true'
    assert page.get_attribute('#burnSvg [aria-label^="Left leg, "]', 'aria-pressed') == 'true'
    assert page.inner_text('#burnTotal').strip() == '30%'   # head 14 + leg 16
    assert 'Head 14%' in page.inner_text('#burnList') and 'Left leg 16%' in page.inner_text('#burnList')


def test_burn_guidance_and_notes_come_from_protocol_escaped(page, app_url):
    boot(page, app_url, fixtures=[BURNS], hash_='#/emergency/tool/burn')
    assert 'Burn bigger than the casualty palm' in page.inner_text('#burnGuide')
    assert page.locator('#burnGuide b').count() == 0
    assert 'Count <i>only</i> this' in page.inner_text('#burnNotes') and 'Second note' in page.inner_text('#burnNotes')
    assert page.locator('#burnNotes i').count() == 0


def test_burn_has_no_hard_coded_medical_wording(page, app_url):
    boot(page, app_url, hash_='#/emergency/tool/burn', only=True)   # shipped data has its own Burns protocol
    assert page.inner_text('#burnNotes').strip() == ''
    assert 'first-degree' not in page.inner_text('#toolBody').lower()


def test_burn_without_burns_protocol_shows_no_guidance(page, app_url):
    boot(page, app_url, hash_='#/emergency/tool/burn', only=True)   # shipped data has its own Burns protocol
    assert page.inner_text('#burnGuide').strip() == ''


def test_export_text_contains_every_entry_in_time_order(page, app_url):
    seed = [pts(entries=[e(T0 + 120000, 'Second thing', 'event'), e(T0 + 60000, 'First <thing>'),
                         e(T0 + 180000, 'Vitals: pulse 88', 'vitals', pulse=88)])]
    boot(page, app_url, storage={'patients': seed})
    txt = page.evaluate("FK.patients.text('p1')")
    lines = txt.split('\n')
    assert lines[0].startswith('Casualty 1')
    body = [l for l in lines[1:] if l]
    assert [l.split(' ', 1)[1] for l in body] == ['First <thing>', 'Second thing', 'Vitals: pulse 88']
    assert all(len(l.split(' ', 1)[0]) == 5 and l[2] == ':' for l in body)
    assert page.evaluate("FK.patients.text('nope')") == ''


def test_malformed_patients_are_filtered(page, app_url):
    bad = ['x', None, 5, {'id': 'a b', 'name': 'bad id', 'entries': []}, {'id': 'noname', 'entries': []},
           pts(id='ok', name='Good', entries=[
               e(T0, 'keep'), e('x', 'bad time'), e(T0, 5), e(T0, 'kind', 'weird'), e(T0, 'p', 'vitals', pulse='80'),
               e(T0, 'p2', 'vitals', pulse=999), e(T0, 'a', 'vitals', avpu='X'), e(T0 + 1, 'fine', 'vitals', pulse=80, avpu='A'), 'junk']),
           pts(id='noentries', name='NoEntries', entries='nope')]
    boot(page, app_url, storage={'patients': bad})
    assert page.evaluate('FK.patients.all().map(p => p.id)') == ['ok', 'noentries']
    assert page.evaluate("FK.patients.all()[0].entries.map(x => x.text)") == ['keep', 'fine']
    page.evaluate("FK.tools.start('log')")
    page.wait_for_selector('#toolPane:not([hidden])')


def test_storage_full_shows_message_and_keeps_entries(page, app_url):
    boot(page, app_url, storage={'patients': [pts(entries=[e(T0, 'before')])]}, hash_='#/emergency/tool/log')
    page.evaluate("Storage.prototype.setItem = () => { throw new DOMException('full', 'QuotaExceededError'); }; 0")
    page.fill('#ptNote', 'after')
    page.click('#ptAddNote')
    assert 'storage' in page.inner_text('#toast').lower()
    assert page.evaluate('FK.patients.all()[0].entries.map(x => x.text)') == ['before']
    assert page.input_value('#ptNote') == 'after'   # typed text is not lost


def test_add_validation_returns_false_without_writing(page, app_url):
    boot(page, app_url)
    bad = ["{kind: 'x', text: 'a'}", "{kind: 'note', text: 5}", "{kind: 'note', text: '  '}", "{kind: 'vitals', text: 'v', pulse: 0}",
           "{kind: 'vitals', text: 'v', pulse: 301}", "{kind: 'vitals', text: 'v', pulse: 80.5}", "{kind: 'vitals', text: 'v', resp: 121}",
           "{kind: 'vitals', text: 'v', avpu: 'X'}", "{kind: 'note', text: 'x'.repeat(2001)}", 'null']
    for b in bad:
        assert page.evaluate(f'FK.patients.add({b})') is False, b
    assert page.evaluate("localStorage.getItem('fk.patients')") is None
    assert page.evaluate("FK.patients.add({kind: 'vitals', text: 'v', pulse: 300, resp: 120, avpu: 'U'})") is True


def test_limits_refuse_with_toast(page, app_url):
    many = [pts(id=f'p{i}', name=f'C{i}') for i in range(50)]
    boot(page, app_url, storage={'patients': many})
    assert page.evaluate('FK.patients.create()') is None
    assert 'casualties' in page.inner_text('#toast').lower()
    full = [pts(entries=[e(T0 + i, f'n{i}') for i in range(500)])]
    page.evaluate("(v) => localStorage.setItem('fk.patients', JSON.stringify(v))", full)
    assert page.evaluate("FK.patients.add({kind: 'note', text: 'one more'})") is False
    assert '500' in page.inner_text('#toast')
    assert page.evaluate('FK.patients.all()[0].entries.length') == 500


def test_log_ui_note_vitals_list_switch_rename_delete(page, app_url):
    boot(page, app_url, hash_='#/emergency/tool/log')
    assert page.inner_text('#ptName') == 'Casualty 1'
    page.fill('#ptNote', '<img src=x onerror=alert(1)> bleeding')
    page.click('#ptAddNote')
    assert page.input_value('#ptNote') == ''
    assert page.locator('#ptList img').count() == 0 and '<img' in page.inner_text('#ptList')
    page.click('#ptAddVitals')   # nothing entered: refused
    assert len(stored(page)[0]['entries']) == 1
    page.fill('#ptPulse', '88'); page.fill('#ptResp', '16'); page.click('#ptAvpu [data-avpu="V"]')
    page.click('#ptAddVitals')
    ent = stored(page)[0]['entries'][-1]
    assert (ent['kind'], ent['pulse'], ent['resp'], ent['avpu']) == ('vitals', 88, 16, 'V')
    first = page.locator('#ptList li').first.inner_text()
    assert 'pulse 88' in first.lower() and first[:5].count(':') == 1   # newest first, HH:MM
    page.fill('#ptPulse', '999'); page.click('#ptAddVitals')
    assert len(stored(page)[0]['entries']) == 2
    page.click('#ptNew')
    assert page.inner_text('#ptName') == 'Casualty 2'
    page.click('#ptRename'); page.fill('#ptRenameIn', 'Sam'); page.click('#ptRenameSave')
    assert page.inner_text('#ptName') == 'Sam'
    page.select_option('#ptSel', page.evaluate('FK.patients.all()[0].id'))
    assert page.inner_text('#ptName') == 'Casualty 1'
    assert page.evaluate('FK.patients.current().name') == 'Casualty 1'
    page.reload()
    page.wait_for_function('window.FK && FK.patients')
    assert page.evaluate('FK.patients.current().name') == 'Casualty 1'   # current survives reload


def test_delete_casualty_is_two_step_with_ignore_window(page, app_url):
    boot(page, app_url, storage={'patients': [pts(entries=[e(T0, 'x')])]}, hash_='#/emergency/tool/log')
    dialogs = []
    page.on('dialog', lambda d: (dialogs.append(d.message), d.dismiss()))
    page.click('#ptDelete')
    page.click('#ptDelete')   # bounced: ignored
    assert len(stored(page)) == 1
    page.clock.run_for(5100)
    assert page.inner_text('#ptDelete') == 'Delete casualty'
    page.click('#ptDelete'); page.clock.run_for(800); page.click('#ptDelete')
    after = stored(page)
    assert len(after) == 1 and after[0]['name'] == 'Casualty 1' and after[0]['entries'] == [] and after[0]['id'] != 'p1'   # a fresh one takes its place
    assert dialogs == []


def test_copy_and_share(page, app_url):
    boot(page, app_url, storage={'patients': [pts(entries=[e(T0, 'x')])]}, hash_='#/emergency/tool/log',
         init="window.shared = []; navigator.share = d => { shared.push(d.text); return Promise.resolve(); };"
              "Object.defineProperty(navigator, 'clipboard', {value: {writeText: t => { window.copied = t; return Promise.resolve(); }}});")
    page.click('#ptCopy')
    page.wait_for_function('window.copied')
    assert 'Casualty 1' in page.evaluate('copied')
    page.click('#ptShare')
    assert 'Casualty 1' in page.evaluate('shared[0]')


def test_share_hidden_without_navigator_share(page, app_url):
    boot(page, app_url, hash_='#/emergency/tool/log', init="delete Navigator.prototype.share; delete navigator.share;")
    assert page.locator('#ptShare').count() == 0


def test_cpr_coach_logs_start_and_stop(page, app_url):
    boot(page, app_url, hash_='#/emergency/tool/cpr')
    page.click('#cprBtn')
    page.clock.run_for(800)
    page.click('#cprBtn'); page.clock.run_for(800); page.click('#cprBtn')
    texts = [x['text'] for x in stored(page)[0]['entries']]
    assert texts[0] == 'CPR started (adult)' and texts[-1] == 'CPR stopped after 0 cycles'


def test_tools_category_lists_new_tools(page, app_url):
    boot(page, app_url)
    page.click('summary[data-cat="tools"]')
    for t in ('rate', 'burn', 'log'):
        assert page.locator(f'.em-btn[data-tool="{t}"]').is_visible()
    page.click('.em-btn[data-tool="log"]')
    page.wait_for_function("location.hash === '#/emergency/tool/log'")
    assert page.inner_text('#toolTitle') == 'Patient log'


def test_new_controls_are_at_least_56px(page, app_url):
    boot(page, app_url, hash_='#/emergency/tool/log')
    for sel in ('#ptAddNote', '#ptAddVitals', '#ptNew', '#ptCopy', '#ptDelete', '#ptAvpu button'):
        for loc in page.locator(sel).all():
            assert loc.bounding_box()['height'] >= 56, sel
    page.evaluate("FK.tools.start('rate')")
    page.wait_for_selector('#rateTap')
    assert page.locator('#rateTap').bounding_box()['height'] >= 56


def test_set_current_works_when_clock_is_behind_stored_values(page, app_url):
    seed = [pts(id='p1', used=T0 + 10**9), pts(id='p2', name='Two', used=T0 + 5)]
    boot(page, app_url, storage={'patients': seed})
    assert page.evaluate('FK.patients.current().id') == 'p1'
    assert page.evaluate("FK.patients.setCurrent('p2')") is True
    assert page.evaluate('FK.patients.current().id') == 'p2'
    page.evaluate("FK.patients.create('Three')")
    assert page.evaluate('FK.patients.current().name') == 'Three'


def test_avpu_buttons_show_their_names_and_are_56px(page, app_url):
    boot(page, app_url, hash_='#/emergency/tool/log')
    for b in page.locator('#ptAvpu button').all():
        txt = b.inner_text().replace('\n', ' ')
        assert txt in ('A Alert', 'V Voice', 'P Pain', 'U Unresponsive'), txt
        assert b.get_attribute('aria-label') is None
        assert b.bounding_box()['height'] >= 56


def test_rename_with_full_storage_shows_storage_message(page, app_url):
    boot(page, app_url, hash_='#/emergency/tool/log')
    page.click('#ptRename'); page.fill('#ptRenameIn', 'Sam')
    page.evaluate("Storage.prototype.setItem = () => { throw new DOMException('full', 'QuotaExceededError'); }; 0")
    page.click('#ptRenameSave')
    assert 'storage' in page.inner_text('#ptMsg').lower() and 'type a name' not in page.inner_text('#ptMsg').lower()
    page.fill('#ptRenameIn', '  '); page.click('#ptRenameSave')
    assert 'type a name' in page.inner_text('#ptMsg').lower()
