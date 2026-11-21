# Ballistics Release 1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ballistics whose maths has been checked against published trajectories, with rifle profiles that carry a sight and zero conditions, an answer written for that sight, correction from a real shot, and range and wind beside the answer.

**Architecture:** `src/ballistics.js` stays the pure solver (`BAL`) and gains zero conditions, a time-step option and the velocity correction. A new pure file `src/bal-sight.js` (`BALS`) turns a solved row plus a sight into the words on screen; it never touches the trajectory. The Ballistics screen code moves out of `src/app.js` into a new `src/bal-ui.js`, which owns profiles, the profile editor sheet and the screen.

**Tech Stack:** Plain JavaScript in one built `index.html` (`python3 build.py`), no libraries added. Tests: pytest + Playwright (`tests/`), reaching pure code with `page.evaluate` the way `tests/test_wmm.py` does.

**Spec:** `docs/superpowers/specs/2026-11-21-ballistics-design.md` (approved by Jordan 2026-11-21). Release 2 (spin drift, zero comparison, close-range table) gets its own plan.

## Global Constraints

- Branch `ballistics`. Nothing reaches `main` without Jordan's go and a phone-check list.
- Edit `src/`, `tests/`, `tools/`, `docs/`, `build.py` only. Root `index.html`, `sw.js`, `manifest.json` are build output: build into another folder (`python3 build.py /tmp/out`) or restore them with `git checkout -- index.html sw.js manifest.json`.
- **Every number comes from a source that was actually opened**, recorded in `docs/content-review.md` under a new heading "Ballistics". Built-in search and fetch only (not Firecrawl, not Bright Data); fetch only URLs exactly as a search returned them.
- A reference trajectory is one computed with a single stated G1 or G7 coefficient. A table built from radar data, a custom drag curve or stepped coefficients is recorded, not judged. The solver is not extended to match one.
- Pass mark while the bullet is above Mach 1.2: elevation and wind within 0.1 mil to 600 yd and 0.2 mil to 1,000 yd; velocity within 1 percent. If the solver fails, fix the solver, never the pass mark, and write the before and after into `docs/ballistics-rulings.md`.
- If the solver passes unchanged, the figures in `BEFORE` (`tests/test_tactical_layout.py`) do not change. They change only with a ruling that gives the before and after.
- **The sight never changes the trajectory.** Only load, zero, conditions and shot do.
- MOA is true MOA (1.047 in at 100 yd). The third unit is inches per 100 yd, shown as `in/100 yd`.
- Units on screen stay yards, inches, fps, grains, °F, feet, inHg, mph.
- Overlays go through `FK.sheet` (read `src/sheet.js` whole first). No `prompt()`, `confirm()`, `alert()`, `AbortSignal.timeout`, `CompressionStream`, `BarcodeDetector`, and no browser feature the iPhone table in `docs/v7.8-rulings.md` lists as missing or doubtful.
- 360 px wide, day and night, every control at least 44 px, nothing cut off with enlarged text. A table wider than the screen scrolls with the "Swipe sideways" cue.
- Wording: "target", "hold", "dial". No text advising action against a person. No internal wording on screen.
- Public repo: no home town; no coordinates are needed here.
- Run the **full** suite after every task: `python3 -m unittest tests.test_validate && python3 -m pytest tests -q` (about 13 minutes). A flaky test is a bug. Commit at least every 15 minutes.
- Every decision made without Jordan goes in `docs/ballistics-rulings.md` with its cost if wrong.

## Review Focus

1. **Blank, zero, negative or pasted-junk input** (range 0, BC blank, wind "abc", a mark list like `1.5,,3`): a plain message or a dash, never `NaN`, `Infinity` or `undefined` on screen. Tests in Tasks 3 and 6.
2. **Old and hostile stored data** (v7.8 profiles and backups; a restored profile with strings for numbers, 500 marks, markup in the name): old data behaves as before; bad fields are dropped, the name is escaped. Tests in Task 4.
3. **Shots the bullet cannot make or the sight cannot express** (never reaches the range; target inside the zero so the need is negative; past the last reticle mark; subsonic): the app says so and gives a plain angle, never a made-up mark or click count. Tests in Tasks 3 and 6.
4. **Unit and rounding edges** (half a click; a correction typed in in/100 yd; a 0.04 mil need; direction letters when the value rounds to zero): one rounding rule everywhere, no "U 0.0". Tests in Tasks 3 and 7.
5. **The selected profile disappearing or changing under the screen** (deleting the selected profile; saving while the 150 ms recalculation is pending; restoring a backup while Ballistics is open): the screen lands on a real profile with a correct answer. Tests in Tasks 5 and 6.

---

### Task 1: Check the solver against published trajectories

**Files:**
- Modify: `src/ballistics.js` (only what the tests below need: `dt` option, `tables` export; solver changes only if a reference fails)
- Create: `tests/test_ballistics_math.py`, `tests/fixtures/ballistics_reference.json`
- Modify: `docs/content-review.md` (new "Ballistics" heading), create `docs/ballistics-rulings.md`

**Interfaces:**
- Produces: `BAL.solve(p)` accepts `p.dt` (seconds, default 0.001). `BAL.tables` is `{ G1: [[mach, cd], ...], G7: [...] }`. Everything else about `BAL.solve` and `BAL.atmosphere(tempF, altFt, pressInHg, rh)` is unchanged.
- Fixture format, one object per reference case:
  `{ "id", "source", "url", "opened", "model": "G1"|"G7", "bc", "w", "mv", "sight", "zero", "temp", "alt", "press", "rh", "wind", "clock", "judged": true|false, "rows": [ { "yd", "dropIn", "windIn", "fps", "tof" } ] }` (any of the four row figures may be absent).

- [ ] **Step 1: Research.** Find and open at least two independent published sources of single-coefficient G1 or G7 trajectories. Cases needed: a .308 match load to 1,000 yd; a 5.56 or .223 load to 600 yd; a load that goes below Mach 1 inside its table. Enter each source's own atmosphere, sight height and zero exactly. Write them to the fixture and to `docs/content-review.md` (source name, URL, date opened, which rows were taken). A source that is not single-coefficient goes in with `"judged": false`.
- [ ] **Step 2: Write the failing tests** in `tests/test_ballistics_math.py` (fixture `ready` as in `tests/test_wmm.py`, waiting for `typeof BAL !== "undefined"`):

```python
def test_no_drag_is_the_textbook_parabola(ready):
    # bc 1e9 removes drag: drop below the bore line at time t is g*t*t/2
    r = solve(ready, bc=1e9, model='G7', mv=2600, sight=0, zero=100, ranges=[100, 500, 1000], wind=0)
    for row in r['rows']:
        t = row['yd'] * 0.9144 / (2600 * 0.3048)
        assert row['tof'] == pytest.approx(t, rel=1e-4)
    # zeroed at 100 yd with no sight height: path at x is -(g/2)(t^2 - t*t100), in inches
    ...assert each dropIn within 0.05 in of that formula

def test_halving_the_time_step_moves_nothing(ready):
    a = solve(ready, **DEFAULT_308, ranges=[300, 600, 1000])
    b = solve(ready, **DEFAULT_308, ranges=[300, 600, 1000], dt=0.0005)
    for x, y in zip(a['rows'], b['rows']):
        assert abs(x['elevMil'] - y['elevMil']) < 0.01 and abs(x['windMil'] - y['windMil']) < 0.01

def test_air_density_matches_the_standard_atmosphere(ready):
    # values from the source recorded in content-review.md, e.g. sea level 59 F 29.92 inHg dry = 1.225 kg/m3
    ...

def test_drag_tables_match_their_published_values(ready):
    # every [mach, cd] pair of BAL.tables.G1 and .G7 against the opened source
    ...

@pytest.mark.parametrize('case', JUDGED_CASES, ids=lambda c: c['id'])
def test_reference_trajectory(ready, case):
    # rows above Mach 1.2 only: elevation and wind as angles within 0.1 mil to 600 yd, 0.2 mil to 1000 yd; fps within 1 %
    ...
```

`DEFAULT_308 = dict(bc=0.243, model='G7', w=175, mv=2600, sight=1.5, zero=100, temp=59, alt=0, press=0, rh=50, wind=10, clock=3)`.
- [ ] **Step 3: Run them.** `python3 -m pytest tests/test_ballistics_math.py -q`. Expected: the `dt` and `tables` tests fail (not implemented); note which reference cases fail.
- [ ] **Step 4: Add `p.dt` and `BAL.tables`.** If a judged reference fails: find the cause, fix the solver, record the before and after figures for the default profile in `docs/ballistics-rulings.md`, and update `BEFORE` in the same commit with that ruling named in a comment. If none fails, `BEFORE` is untouched.
- [ ] **Step 5: Standard atmosphere of the coefficient.** State in `docs/ballistics-rulings.md` which standard atmosphere the solver assumes a coefficient refers to, with its source, and the measured change at 1,000 yd for the default profile if the other standard were assumed. Report only; do not change the solver for it.
- [ ] **Step 6: Full suite, then commit.** `git commit -m "ballistics: solver checked against published trajectories"`

### Task 2: Source the built-in loads

**Files:**
- Modify: `src/app.js:498-504` (`PRESETS`; this list moves to `src/bal-ui.js` in Task 4, so do this task before Task 4 or after it, never during)
- Modify: `tests/test_ballistics_math.py`, `docs/content-review.md`

**Interfaces:**
- Produces: `PRESETS` entries keep the shape `{ id, name, bc, model, w, mv, sight, zero }`. Existing ids (`p556`, `p223`, `p76239`, `p65cm`, `p308`) keep their meaning if the load stays; a removed load's id is never reused.

- [ ] **Step 1: Research.** For each of the five loads, open a source for its coefficient (the bullet maker) and its velocity (the ammunition maker or an army data sheet), with the barrel length the velocity is for. Add a 55 gr 5.56 load and 16 in barrel velocities for the AR loads **only** where a source gives them. Record each in `docs/content-review.md`.
- [ ] **Step 2: Write the test.**

```python
def test_built_in_loads_are_the_sourced_values(ready):
    assert ready.evaluate('FK._test.presets()') == SOURCED   # SOURCED copied from content-review.md, name included
```

(`FK._test.presets` returns the list; add it beside the other `FK._test` hooks.)
- [ ] **Step 3: Update `PRESETS`.** Names carry the barrel length (for example `5.56 NATO 62 gr M855, 20″ barrel`). A load with no source is removed and listed in `docs/ballistics-rulings.md`. If `p308` changes, `BEFORE` changes with a ruling; say so plainly in the rulings file.
- [ ] **Step 4: Full suite, commit.** `git commit -m "ballistics: built-in loads sourced"`

### Task 3: Zero conditions, and the words for each sight

**Files:**
- Modify: `src/ballistics.js`
- Create: `src/bal-sight.js`; modify `build.py:47` (add `'bal-sight.js'` straight after `'ballistics.js'`)
- Create: `tests/test_bal_sight.py`; modify `tests/test_ballistics_math.py`

**Interfaces:**
- Produces, solver: `BAL.solve(p)` accepts `p.zeroAtm = { temp, alt, press, rh }` (same units as the shot fields; absent or `null` means "same as today"). The zero angle is found in `zeroAtm` air; the shot flies in today's air. Rows are unchanged in shape.
- Produces, words: `BALS.answer(row, sight)` returns `{ elev: { main, sub }, wind: { main, sub } }` (strings; `sub` may be `''`). `row` needs only `yd`, `dropIn`, `windIn`. `sight` is `null` or `{ type: 'turret', unit, click }`, `{ type: 'reticle', unit, marks: number[] }`, `{ type: 'dot' }`, with `unit` one of `'mil' | 'moa' | 'iphy'`.
- `BALS.all(row)` returns `{ elev: [mil, moa, inches], wind: [mil, moa, inches] }` (three strings each) for a profile with no sight and for "Show all units".
- `BALS.cols(sight)` returns the dope-card column headings for elevation and wind, and `BALS.cells(row, sight)` the matching cell strings.
- `BALS.toAngle(value, unit, yd)` converts a typed elevation to radians; `unit` adds `'in'` (inches of drop at `yd`). Used by Task 7.
- Rules, used by every function:
  - Need = the angle up from the line of sight to the bullet's fall: `atan(-dropIn / (yd * 36))`. In a unit: mil = rad × 1000; MOA = degrees × 60; in/100 yd = `tan(rad) × 3600`.
  - Direction letters `U`/`D`, `R`/`L` as today (positive wind value is `R`). A value that rounds to zero at the shown precision has no letter.
  - Angles show one decimal. Inches show one decimal under 10, whole numbers from 10.
  - Clicks = `Math.round(|value in unit| / click)`.
  - Unit labels: `mil`, `MOA`, `in/100 yd`.

- [ ] **Step 1: Write the failing tests** (`tests/test_bal_sight.py`). `ROW = {'yd': 500, 'dropIn': -64.3, 'windIn': -21.9}`:

```python
def test_turret_mil(ready):
    assert answer(ready, ROW, {'type': 'turret', 'unit': 'mil', 'click': 0.1}) == {
        'elev': {'main': 'U 3.6 mil', 'sub': '36 clicks'}, 'wind': {'main': 'R 1.2 mil', 'sub': '12 clicks'}}

def test_turret_true_moa_and_inches_per_100(ready):
    assert answer(ready, ROW, {'type': 'turret', 'unit': 'moa', 'click': 0.25})['elev'] == {'main': 'U 12.3 MOA', 'sub': '49 clicks'}
    assert answer(ready, ROW, {'type': 'turret', 'unit': 'iphy', 'click': 0.25})['elev'] == {'main': 'U 12.9 in/100 yd', 'sub': '51 clicks'}

def test_reticle_nearest_mark_and_hold(ready):
    s = {'type': 'reticle', 'unit': 'mil', 'marks': [1.5, 3.0, 4.6, 6.3]}
    assert answer(ready, ROW, s)['elev'] == {'main': 'Mark 2', 'sub': 'hold 10 in high'}
    assert answer(ready, ROW, s)['wind'] == {'main': 'R 1.2 mil', 'sub': '22 in'}

def test_reticle_before_first_mark_and_past_last(ready):
    s = {'type': 'reticle', 'unit': 'mil', 'marks': [1.5, 3.0, 4.6, 6.3]}
    assert answer(ready, {'yd': 200, 'dropIn': -4.2, 'windIn': 0}, s)['elev'] == {'main': 'Centre', 'sub': 'hold 4.2 in high'}
    assert answer(ready, {'yd': 800, 'dropIn': -227.9, 'windIn': 0}, s)['elev'] == {'main': 'Past last mark', 'sub': 'U 7.9 mil'}

def test_reticle_target_inside_the_zero(ready):   # bullet above the line of sight
    s = {'type': 'reticle', 'unit': 'mil', 'marks': [1.5, 3.0]}
    assert answer(ready, {'yd': 100, 'dropIn': 1.7, 'windIn': 0}, s)['elev'] == {'main': 'Centre', 'sub': 'hold 1.7 in low'}

def test_dot(ready):
    assert answer(ready, ROW, {'type': 'dot'}) == {
        'elev': {'main': 'Hold 64 in high', 'sub': ''}, 'wind': {'main': 'Hold 22 in right', 'sub': ''}}
    assert answer(ready, {'yd': 7, 'dropIn': -2.3, 'windIn': 0}, {'type': 'dot'})['elev']['main'] == 'Hold 2.3 in high'
    assert answer(ready, {'yd': 100, 'dropIn': -0.02, 'windIn': 0.01}, {'type': 'dot'}) == {
        'elev': {'main': 'Hold on', 'sub': ''}, 'wind': {'main': 'No hold', 'sub': ''}}

def test_all_units(ready):
    assert ready.evaluate('r => BALS.all(r)', ROW) == {
        'elev': ['U 3.6 mil', 'U 12.3 MOA', 'Hold 64 in high'], 'wind': ['R 1.2 mil', 'R 4.2 MOA', 'Hold 22 in right']}

def test_rounding_edges(ready):
    t = {'type': 'turret', 'unit': 'mil', 'click': 0.1}
    assert answer(ready, {'yd': 100, 'dropIn': -0.14, 'windIn': 0}, t)['elev'] == {'main': '0.0 mil', 'sub': '0 clicks'}   # 0.04 mil
    assert answer(ready, {'yd': 100, 'dropIn': -0.56, 'windIn': 0}, t)['elev'] == {'main': 'U 0.2 mil', 'sub': '2 clicks'}   # 0.156 mil: past half a click rounds up

def test_bad_input_gives_dashes(ready):
    for row in [{'yd': 0, 'dropIn': -1, 'windIn': 0}, {'yd': 500, 'dropIn': None, 'windIn': 0}]:
        a = answer(ready, row, {'type': 'turret', 'unit': 'mil', 'click': 0.1})
        assert a['elev']['main'] == '—' and 'NaN' not in str(a)
```

Reticle rule the tests pin: the mark is the one nearest the need; it is "Centre" when the need is under half the first mark; "Past last mark" when the need is beyond the last mark by more than half the last gap (with one mark: beyond 1.5 times it); a hold under 0.5 in is left out (`sub` is `''`).

And in `tests/test_ballistics_math.py`:

```python
def test_zero_conditions_same_as_today_change_nothing(ready):
    same = dict(temp=59, alt=0, press=0, rh=50)
    assert solve(ready, **DEFAULT_308, ranges=[600], zeroAtm=same)['rows'] == solve(ready, **DEFAULT_308, ranges=[600])['rows']

def test_zeroed_warm_shot_cold_needs_more_elevation(ready):
    cold = {**DEFAULT_308, 'temp': 10}
    warm_zero = solve(ready, **cold, ranges=[100, 600], zeroAtm=dict(temp=90, alt=0, press=0, rh=50))['rows']
    same_air = solve(ready, **cold, ranges=[100, 600])['rows']
    assert warm_zero[1]['elevMil'] > same_air[1]['elevMil']
    assert abs(same_air[0]['elevMil']) < 0.005 and abs(warm_zero[0]['elevMil']) < 0.1
```

- [ ] **Step 2: Run, expect failures** (`BALS` not defined; `zeroAtm` ignored).
- [ ] **Step 3: Implement** `zeroAtm` in `BAL.solve` and the whole of `src/bal-sight.js` to the rules above.
- [ ] **Step 4: Run the two test files, then the full suite. Commit.** `git commit -m "ballistics: zero conditions; answers written per sight"`

### Task 4: Profiles: move the screen code, new fields, old data

**Files:**
- Create: `src/bal-ui.js` (the Ballistics section of `src/app.js:497-607` moves here unchanged in behaviour); modify `build.py:47` (add `'bal-ui.js'` after `'sheet.js'`); modify `src/app.js` (remove the section, keep whatever the start-up code at the end of the file calls, through `FK.bal`)
- Create: `tests/test_bal_profiles.py`; modify `tests/test_migration.py` only if a test there names a moved internal

**Interfaces:**
- Produces: `FK.bal = { init(), calc(), profiles(), selected(), select(id), save(profile), remove(id), clean(raw) }`.
- A stored profile: `{ id, name, bc, model, w, mv, sight (height, in), zero, optic?, zeroAtm?, mv0? }` where `optic` is the sight object of Task 3, `zeroAtm` is `{ temp, alt, press, rh }`, `mv0` is the velocity before any correction (Task 7).
- `FK.bal.clean(raw)` returns a safe profile or `null`. It keeps `id` (must pass `okId`) and `name` (string, cut to 60 characters); numbers must be finite or the field is dropped; `optic.type` outside the three kinds drops `optic`; `optic.unit` outside the three units drops `optic`; `optic.click` must be one of `0.1, 0.05, 0.25, 0.125, 0.5, 1`; `optic.marks` keeps at most 10 finite positive numbers and is dropped unless they strictly increase. It is the validator passed to `list('profiles', ...)` and so also runs on a restored backup.
- First open after the update: if the stored `bal.profile` is `'custom'` and a BC and velocity are stored, a profile `{ id: 'ucustom', name: 'Custom', ... }` is created from the stored load fields and selected; otherwise the stored selection stands, and if it names nothing that exists, `p308` (or the first built-in load if `p308` was removed in Task 2) is selected. The stored `unit` key is left alone and no longer read.
- "Show all units" is not stored: it is off whenever the screen opens or the profile changes.

- [ ] **Step 1: Move the code** into `src/bal-ui.js` with no behaviour change. Run the full suite; `BEFORE` and `tests/test_migration.py` must pass untouched. Commit: `git commit -m "ballistics: screen code moved to bal-ui.js"`
- [ ] **Step 2: Write the failing tests** (`tests/test_bal_profiles.py`):

```python
def test_v78_profile_loads_and_shows_every_unit(page, app_url): ...
    # store a v7.8 profile {id,name,bc,model,w,mv,sight,zero}; selected() has no optic; nothing is rewritten in storage
def test_custom_inputs_become_a_profile_named_custom(page, app_url): ...
    # v7.8 'bal' with profile 'custom', bBC 0.4, bMV 2800 ... -> profiles() contains id 'ucustom', name 'Custom', bc 0.4, mv 2800, and it is selected
def test_custom_with_no_load_typed_selects_a_built_in(page, app_url): ...
def test_clean_drops_bad_fields(page, app_url):
    bad = {'id': 'u1', 'name': '<img src=x onerror=1>' + 'x' * 200, 'bc': '0.3', 'mv': 2700,
           'optic': {'type': 'reticle', 'unit': 'mil', 'marks': [3, 1, 2] + [9] * 500}}
    got = page.evaluate('p => FK.bal.clean(p)', bad)
    assert len(got['name']) == 60 and 'bc' not in got and got['mv'] == 2700 and 'optic' not in got
def test_clean_rejects_no_id(page, app_url): ...   # returns None
def test_profile_name_is_escaped_on_screen(page, app_url): ...   # the name above shows as text, no <img> element exists
def test_restored_backup_profiles_pass_through_clean(page, app_url): ...   # restore tests/fixtures/v5-backup.json plus one hostile profile
def test_selected_profile_missing_falls_back(page, app_url): ...   # 'bal'.profile names a deleted id
```

- [ ] **Step 3: Implement** `clean`, the first-open rule and the `FK.bal` surface. The picker loses "Custom (unsaved)".
- [ ] **Step 4: Full suite, commit.** `git commit -m "ballistics: profile fields, clean-on-load, custom becomes a profile"`

### Task 5: The profile editor

**Files:**
- Modify: `src/shell.html` (new `<dialog id="dlgRifle" class="sheet mk-sheet" aria-labelledby="rfTitle">` beside the other sheets; styles), `src/bal-ui.js`
- Create: `tests/test_bal_editor.py`

**Interfaces:**
- Consumes: `FK.bal.save/remove/clean/select`, `FK.sheet.open(dlg, { guard: { dirty, title, text }, onClose })`, `FK.sheet.confirm`.
- Produces: `FK.bal.edit(id)` opens the editor on a profile. Element ids: `rfName, rfBC, rfModel, rfW, rfMV, rfSH, rfZero, rfOptic` (select: `none | turret | reticle | dot`, labels "Not set", "Scope with turrets", "Drop reticle (low-power scope)", "Red dot or iron sights"), `rfUnit` (labels "Mil", "MOA (1.047 in at 100 yd)", "Inches per 100 yd"), `rfClick`, `rfMarks` (one text box, marks separated by commas or spaces), `rfZTemp, rfZAlt, rfZPress`, `rfSave, rfSaveNew, rfDelete, rfCancel`, `rfMsg` (the one place errors show).
- Copy fixed by the spec:
  - Under the unit: "Some scopes sold as MOA move 1 inch per 100 yd. Check the manual."
  - Under the marks: "Type each mark's distance below the centre, from your scope's manual. If the manual gives only yardages, this isn't supported yet." and "If the reticle doesn't grow with magnification, the marks are true at one magnification only. The manual says which."
  - Zero conditions blank: "Zero conditions not set: assumed the same as today."
  - Under velocity: "Measure velocity near the temperature you'll shoot in."
  - Marks out of order: "Marks must get larger down the list."

- [ ] **Step 1: Write the failing tests:**

```python
def test_edit_own_profile_saves_in_place(page, app_url): ...        # same id, changed bc
def test_built_in_load_offers_save_as_new_only(page, app_url): ...  # rfSave and rfDelete hidden, rfSaveNew shown; the built-in is unchanged after
def test_turret_fields_show_only_for_turrets(page, app_url): ...    # rfUnit and rfClick visible for turret; rfUnit and rfMarks for reticle; neither for dot or none
def test_click_choices_follow_the_unit(page, app_url): ...          # mil: 0.1, 0.05; moa and iphy: 1/4, 1/8, 1/2, 1
def test_marks_parse_and_refuse(page, app_url): ...                 # '1.5, 3 4.6' -> [1.5, 3, 4.6]; '1.5,,3' -> [1.5, 3]; '3 1.5' and 'abc' refused in rfMsg, sheet stays open; an 11th mark refused
def test_zero_conditions_optional(page, app_url): ...               # blank -> no zeroAtm on the profile and the hint shows; filled -> zeroAtm saved with rh 50
def test_back_with_unsaved_typing_asks(page, app_url): ...          # Keep editing / Discard, as markers do; the sheet's Cancel does not ask
def test_delete_selected_profile_lands_on_a_real_one(page, app_url): ...   # selected() is a built-in load and the answer is not a dash
def test_editor_fits_360_day_and_night_with_large_text(page, app_url): ...  # no horizontal overflow, controls >= 44 px
def test_required_fields(page, app_url): ...                        # blank name, bc, mv or zero: message in rfMsg, nothing saved
```

- [ ] **Step 2: Run, expect failures. Step 3: Implement.** Zero-conditions humidity is fixed at 50 percent (not asked for). Test Back with a slowed `history.go` as `tests/test_sheet.py` does.
- [ ] **Step 4: Full suite, commit.** `git commit -m "ballistics: profile editor"`

### Task 6: The screen

**Files:**
- Modify: `src/shell.html:961-1031` and its styles (`.solution` at 165-177, `#view-ballistics` at 612), `src/bal-ui.js`
- Create: `tests/test_bal_screen.py`; modify `tests/test_tactical_layout.py` (the `BEFORE` reader and the element-order test at line 323)

**Interfaces:**
- Consumes: `BALS.answer/all/cols/cells`, `FK.bal.edit`, `BAL.solve` with `zeroAtm`.
- Produces: order on screen: profile row (`#bProfile` picker, a line naming the sight, `#bEdit`), answer card (`#solution`: `#solElev`, `#solWind`, `#solSub`, `#bAll` "Show all units" as a pressed-or-not button), shot inputs (`#bRange`, `#bAngle`, `#bWind`, `#bClock`), conditions line (`#bCond` summary such as `59°F · 0 ft · 50%` with `#bCondBtn` "Change" that shows the four existing fields), dope card (`#bMax`, `#bStep`, `#dope`). `#unitSeg`, `#bSave`, `#bDel` and the load fields leave the main screen.
- With no sight, or with `#bAll` pressed, `#solElev` and `#solWind` each show the three lines of `BALS.all`, and the dope card shows Elev mil, Elev MOA, Wind mil, Wind MOA, Drop in, Drift in, fps, ft-lb, Time s.
- `#solSub` is the existing sentence. Range accepts 1 to 3,000 yd.
- The `BEFORE` test keeps its figures: it now reads the mil and MOA lines of the show-all view and the Drop, Drift, fps, ft-lb and Time columns, except that the Drop cell at the zero reads `0.0` where it read `-0.0`. That one change is the only edit to `BEFORE`, noted in a comment.

- [ ] **Step 1: Write the failing tests:**

```python
def test_first_screen_holds_profile_answer_and_shot_inputs(page, app_url): ...   # 360x640: #bProfile, #solution, #bRange, #bAngle, #bWind, #bClock all within the viewport without scrolling
def test_answer_stays_visible_with_the_keyboard_up(page, app_url): ...          # viewport 360x340, #bRange focused: #solution still fully in view
def test_answer_follows_the_sight(page, app_url): ...   # same load as three profiles: turret -> 'U 3.6 mil' + '36 clicks'; dot -> 'Hold 64 in high'; reticle [1.5,3,4.6,6.3] -> 'Mark 2' + 'hold 10 in high'
def test_no_sight_shows_every_unit(page, app_url): ...
def test_show_all_units_is_temporary(page, app_url): ...   # press -> three lines; change profile or reload -> off
def test_dope_columns_follow_the_sight(page, app_url): ...   # turret: 'Elev mil', 'Clicks'; reticle: 'Mark', 'Hold in'; dot: 'Hold in'
def test_dope_table_scrolls_with_the_cue_when_wide(page, app_url): ...
def test_no_minus_zero_anywhere(page, app_url): ...   # no cell text matches r'^-0\.0+$' for every built-in load, both views
def test_zero_row_marked_for_a_fractional_zero(page, app_url): ...   # zero 36.5 yd: exactly one row has class 'zero'
def test_short_range_for_a_dot(page, app_url): ...   # range 7 yd, sight height 2.6: 'Hold 2.x in high'
def test_bad_shot_inputs_never_show_nan(page, app_url): ...   # range '', 0, -5, 99999; wind 'abc': a dash and a plain sentence; the page text never contains NaN, Infinity or undefined
def test_bullet_that_cannot_reach(page, app_url): ...   # 9 mm-like load at 3000 yd: "Bullet doesn't reach that range with these inputs."; no clicks, no mark
def test_subsonic_says_so_for_every_sight(page, app_url): ...
def test_conditions_line_and_change(page, app_url): ...
def test_zero_conditions_reach_the_answer(page, app_url): ...   # profile zeroed at 90 F, today 10 F: elevation at 600 yd larger than the same profile without zero conditions
def test_save_while_recalculation_is_pending(page, app_url): ...   # type a range, save the editor within 150 ms: the answer matches the saved profile and the typed range
def test_restore_backup_while_on_ballistics(page, app_url): ...   # the screen shows a profile that exists after the restore
def test_ballistics_fits_360_day_night_large_text(page, app_url): ...
```

- [ ] **Step 2: Run, expect failures. Step 3: Implement.** Keep `aria-live="polite"` on the answer card. Keep the transonic hint and the line "Spin drift and Coriolis are not included yet."
- [ ] **Step 4: Full suite** (other files read this screen: `tests/test_router.py`, `tests/test_search.py`, `tests/test_sheet.py:177-191`, `tests/test_iphone.py:329`). Commit. `git commit -m "ballistics: answer by sight, range and wind beside it"`

### Task 7: Correct a profile from a real shot

**Files:**
- Modify: `src/ballistics.js`, `src/bal-ui.js`, `src/shell.html` (a "Correct from a real shot" part of `dlgRifle`)
- Modify: `tests/test_ballistics_math.py`; create `tests/test_bal_true.py`

**Interfaces:**
- Consumes: `BALS.toAngle(value, unit, yd)`.
- Produces: `BAL.trueMv(p, yd, angleRad)` where `p` is a full `BAL.solve` input (the day's conditions included). Returns `{ mv, change }` (`change` is the fraction, signed), plus `warn: true` when `|change| > 0.05`; or `{ error: 'near' }` when `yd < 300`, `{ error: 'slow' }` when the bullet is below Mach 1.2 at `yd` with the current velocity, `{ error: 'far' }` when `|change| > 0.15` or no velocity between 0.85 and 1.15 times the current one reproduces the angle. `mv` is a whole number of fps.
- Element ids: `rfTrueYd`, `rfTrueVal`, `rfTrueUnit` (the profile's sight unit first, then "Inches of drop"), `rfTrueGo`, `rfTrueOut`, `rfTrueSave`, `rfTrueUndo`.
- Messages: near: "Use a shot at 300 yd or more. Closer in, a small error gives a wild velocity." slow: "At that distance the bullet is near the speed of sound, where velocity isn't the thing in doubt." far: "That needs a velocity change of more than 15%. Check the distance, the zero and the sight height first." warn (shown with the result): "That's a change of more than 5%. Check the distance, the zero and the sight height first."
- Saving sets `mv` and, if `mv0` is absent, sets `mv0` to the old velocity. `rfTrueUndo` ("Put back NNNN fps") restores `mv0` and removes it; shown only when `mv0` exists.

- [ ] **Step 1: Write the failing tests:**

```python
def test_true_recovers_a_known_velocity(ready):
    for real in (2550, 2600, 2680):
        seen = solve(ready, **{**DEFAULT_308, 'mv': real}, ranges=[600])['rows'][0]
        got = true_mv(ready, DEFAULT_308, 600, math.atan(-seen['dropIn'] / (600 * 36)))
        assert abs(got['mv'] - real) <= 2
def test_true_refusals(ready): ...   # 250 yd -> near; default .308 at 1100 yd -> slow; an angle twice the predicted -> far
def test_true_warns_past_five_percent(ready): ...   # real 2450 -> warn True, mv within 2 of 2450
def test_true_in_each_unit_agrees(page, app_url): ...   # the same shot typed as mil, MOA, in/100 yd and inches gives velocities within 3 fps of each other
def test_save_keeps_the_original_and_undo_restores_it(page, app_url): ...   # correct twice: mv0 stays the first velocity; undo -> mv is mv0 and mv0 is gone
def test_built_in_load_cannot_be_corrected(page, app_url): ...   # the part is hidden until "Save as new profile"
def test_true_bad_input(page, app_url): ...   # blank, 0, negative, 'abc': a message, no NaN, nothing saved
```

- [ ] **Step 2: Run, expect failures. Step 3: Implement** (bisection on velocity; the day's conditions are the ones on the main screen, and the part says so: "Uses today's conditions from the Ballistics screen.").
- [ ] **Step 4: Full suite, commit.** `git commit -m "ballistics: correct velocity from a real shot"`

### Task 8: Final reviews and the release stop

**Files:**
- Modify: `src/app.js` (`APP_VERSION`), `src/sw.js` (`VERSION`), `docs/ballistics-rulings.md`, `docs/content-review.md`; update project doc `claude/FIELD-KIT-STATUS.md` after the push
- Build output at the repo root, written only by `python3 build.py --release .`

- [ ] **Step 1: Whole-branch code review** by a fresh reviewer told to read `src/bal-ui.js`, `src/bal-sight.js` and the `src/ballistics.js` changes as one design, to check the sight can never reach the trajectory, and to triage every deferred minor.
- [ ] **Step 2: Maths review** by a fresh reviewer who re-opens every source in `docs/content-review.md` "Ballistics" and re-enters two reference cases by hand.
- [ ] **Step 3: Final drive.** A tester builds the app (`python3 build.py /tmp/out`, copy the icon PNGs in), uses it at 360 x 640 as a person setting up three rifles (mil turrets, a drop reticle, a red dot), with screenshots, day and night, and judges from the screen. Fix what is found; fixes get the same review as new code.
- [ ] **Step 4: Version.** Read `origin/main`: if it is still v7.8, set both versions to `7.9`; otherwise the next free `major.minor`. Confirm `build.py` and the update banner order a two-digit minor correctly before ever using `7.10`.
- [ ] **Step 5: Full suite on the release build.** Then **stop**. Give Jordan: the rulings ledger, what could not be tested, and the phone-check list (Settings shows the version; v7.8 profiles survived; set up one real rifle with its sight; compare the card with elevations he already knows at two distances; count clicks on a real turret; read a real drop reticle's marks from its manual; change Range with the keyboard up and watch the answer; Back on the editor with typing in it; night mode).
- [ ] **Step 6: After Jordan's go:** squash onto `main` as one commit, push `main` and the branch, ask Jordan to confirm the version in Settings, update `claude/FIELD-KIT-STATUS.md`.
