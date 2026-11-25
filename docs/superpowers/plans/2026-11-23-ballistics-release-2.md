# Ballistics Release 2 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Spin drift in the windage answer and dope card for profiles that carry twist and bullet dimensions, plus two AR tools: a close-range holds table and a zero comparison.

**Architecture:** `BAL.solve` is not touched. Spin drift is a new pure file `src/bal-spin.js` (`BSPIN`) whose result `src/bal-ui.js` adds to each solved row's `windIn` before the row reaches `BALS`. The two tools are a new pure file `src/bal-zero.js` (`BALZ`, built on `BAL.solve`) and a new screen file `src/bal-tools.js` with two sheets.

**Tech Stack:** Plain JavaScript in one built `index.html` (`python3 build.py`), no libraries. Tests: pytest + Playwright, pure code reached with `page.evaluate` as in `tests/test_ballistics_math.py`.

**Spec:** `docs/superpowers/specs/2026-11-21-ballistics-design.md`, "Release 2" (sections 5 to 7), approved by Jordan 2026-11-21. Lines below marked **(call)** are the planner's choices, not Jordan's; each goes into `docs/ballistics-rulings.md` under a new heading "Release 2" with its cost if wrong.

## Global Constraints

- Branch `ballistics-2`, from `main` at `f74c5db` (v7.11). Nothing reaches `main` without Jordan's go and a phone-check list. Release number: the next free one at release time (7.12 if `main` has not moved); `git fetch origin main` and merge before the release step.
- Edit `src/`, `tests/`, `tools/`, `docs/`, `build.py` only. Before each push: `python3 build.py`, commit the rebuilt root files (GitHub's check fails otherwise).
- **`BAL.solve`, `BAL.trueMv` and the drag tables do not change.** The pinned `BEFORE` figures in `tests/test_tactical_layout.py` do not change. A profile without the new fields behaves exactly as in v7.11.
- **The sight never changes the trajectory:** nothing in `BALS` computes spin drift; it only words a row it is given.
- **Every number comes from a source that was actually opened**, recorded in `docs/content-review.md` under "Ballistics". Built-in search and fetch only (not Firecrawl, not Bright Data); fetch only URLs exactly as a search returned them.
- Units stay yards, inches, fps, grains, °F, feet, inHg, mph. MOA is true MOA.
- New sheets go through `FK.sheet` (read `src/sheet.js` whole first). A sheet built on `mk-sheet` never gives a flex item `flex: 1`; use `flex: 1 1 auto`. No `prompt()`, `confirm()`, `alert()`.
- 360 px wide, day and night, controls at least 44 px, nothing cut off with enlarged text; a table wider than its box scrolls with the "Swipe sideways" cue.
- Wording: "target", "hold", "dial". No text advising action against a person. No internal wording on screen. Never `NaN`, `Infinity`, `undefined` or `-0.0` on screen.
- Fields that can hold a decimal use `inputmode="decimal"`; none of the new fields can be negative.
- Run the **whole** suite after every task, in the foreground, in three chunks of test files: `python3 -m unittest tests.test_validate`, then `python3 -m pytest -q -n 4 -p no:cacheprovider --ignore=tests/test_search.py` split by file list, then `tests/test_search.py` alone. A flaky test is a bug. New tests wait for the condition, never a fixed sleep, and hold any clock they install. Commit at least every 15 minutes.

## Review Focus

1. **Partly filled or absurd spin inputs** (twist without length; weight blank; a 0.3 in length on a .308 bullet; left-hand twist): the screen says spin drift is not included and why, or the editor refuses the value; never a confident wrong windage. Tests in Tasks 2 and 3.
2. **Old and hostile stored profiles** (v7.11 profiles and backups; `twist: "8"`, `twistDir: "<b>"`, `blen: -1`): old data behaves as before, bad fields are dropped one by one, the default card is unchanged. Tests in Task 2.
3. **Spin against the wind** (wind from the right, right-hand twist: the two oppose and the net drift changes side along the card): each row's direction letter and the answer's L or R follow the net, with no `R 0.0` and no `-0.0`. Tests in Task 3.
4. **A zero with no second crossing, or none inside the table** (a zero at the top of the path; a 25 yd zero that crosses again past 500 yd; a bullet that never reaches 500 yd; the same zero ticked and typed): the sheet says which case it is and invents no distance. Tests in Tasks 4 and 6.
5. **The profile under an open tool is unusable or changes** (no sight height; numbers out of range; a built-in load on "Use this zero"; storage full on save): a plain message, the stored profile untouched. Tests in Tasks 5 and 6.

---

### Task 1: Sources, and the pure spin drift module

**Files:**
- Create: `src/bal-spin.js`, `tests/test_bal_spin.py`, `tests/fixtures/spin_reference.json`
- Modify: `build.py` (add `bal-spin.js` to the list straight after `ballistics.js`), `docs/content-review.md` ("Ballistics"), `docs/ballistics-rulings.md` (new "Release 2" heading)

**Interfaces:**
- Produces, on a top-level `BSPIN`:
  - `BSPIN.stability({ w, dia, len, twist, mv, temp, press }) -> number` (grains, in, in, in per turn, fps, °F, station inHg). The Miller formula with its velocity and air corrections. `NaN` when any input is not a finite number above 0 (temperature: any finite number).
  - `BSPIN.drift(sg, tof) -> number`: inches, never signed. `NaN` unless both are finite and above 0.
  - `BSPIN.grade(sg) -> 'unstable' | 'marginal' | 'stable'`.
  - `BSPIN.of(profile, air) -> { sg, grade, sign } | { missing: string[] }`. `profile` carries `w, mv, twist, twistDir, blen, bdia` (Task 2's names); `air` is `{ temp, press }` with `press` the station pressure. `sign` is `+1` for a right-hand twist, `-1` for `twistDir === 'L'`. `missing` lists, in this order, whichever of `'twist'`, `'bullet length'`, `'bullet diameter'`, `'bullet weight'` is absent or not above 0.
- Fixture: `{ "stability": { "source", "url", "opened", "examples": [ { inputs…, "sg" } ], "marginalBelow", "unstableBelow" }, "drift": { "source", "url", "opened", "examples": [ { "sg", "tof", "inches" } ] }, "bullets": [ { "preset", "dia", "len", "source", "url", "opened" } ] }`.

- [ ] **Step 1: Research.** Open and record: (a) the Miller stability formula with velocity, temperature and pressure corrections (a search on 2026-11-23 returned it as equation 1 of Courtney and Miller, arXiv 1410.5340: `30 m / (t² d³ L (1 + L²)) × (V/2800)^(1/3) × (FT+460)/(59+460) × 29.92/P`, `t` and `L` in calibers); (b) the Litz spin drift approximation, expected `1.25 × (Sg + 1.2) × tof^1.83` inches; (c) at least one worked example for each, from the source itself; (d) the source's own thresholds for marginal and unstable (expected 1.5 and 1.0); (e) bullet diameter and length for each of the six built-in loads' bullets. Write all of it to the fixture and `docs/content-review.md`. If no worked example for the drift formula can be opened, record two independent statements of the formula that agree, and log it as a ruling. A bullet length that cannot be opened is left out (that built-in then asks for it).
- [ ] **Step 2: Write the failing tests** in `tests/test_bal_spin.py`:

```python
def test_stability_matches_every_source_example(ready, ref):
    for ex in ref['stability']['examples']:
        assert js_stability(ready, ex) == pytest.approx(ex['sg'], abs=0.01)

def test_stability_matches_the_formula_written_out_in_python(ready):
    # 175 gr, .308, 1.24 in, 1:10, 2600 fps, 59 F, 29.92 inHg; expected computed here, not copied from the app
    assert js_stability(ready, CASE) == pytest.approx(miller(CASE), rel=1e-9)

def test_colder_denser_air_lowers_stability(ready): ...        # 0 F below 59 F below 100 F; 29.92 below 25.0
def test_drift_matches_every_source_example(ready, ref): ...   # abs=0.05 in
def test_drift_is_never_negative_and_is_nan_for_bad_input(ready): ...   # sg 0, tof 0, None, 'x', Infinity
def test_grade_uses_the_source_thresholds(ready, ref): ...     # just below and at each threshold
def test_of_lists_what_is_missing_in_order(ready): ...         # {} -> all four; twist only -> the other three
def test_of_left_twist_is_minus_one(ready): ...
def test_of_ignores_strings_and_negatives(ready): ...          # twist '8', blen -1 -> listed as missing
```

- [ ] **Step 3:** Run them: FAIL, `BSPIN is not defined`.
- [ ] **Step 4:** Implement `BSPIN` in `src/bal-spin.js` and add the file to `build.py`.
- [ ] **Step 5:** Run the new file, then the whole suite. PASS.
- [ ] **Step 6:** Commit: `Ballistics 2: spin drift and stability formulas, sourced and checked`.

### Task 2: Twist and bullet fields on the profile and in the editor

**Files:**
- Modify: `src/bal-ui.js` (`RANGE`, `clean`, `ordered`, `PRESETS`, `FK.balHost`), `src/bal-edit.js`, `src/shell.html` (`#dlgRifle`)
- Test: `tests/test_bal_profiles.py`, `tests/test_bal_editor.py`

**Interfaces:**
- Consumes: `BSPIN.of`, `BSPIN.grade` (Task 1); the fixture's `bullets`.
- Produces: optional profile fields `twist` (in per turn), `twistDir` (`'L'` stored only for a left-hand twist; absent means right), `blen`, `bdia` (in). `RANGE` gains `twist: [3, 30]`, `blen: [0.2, 3]`, `bdia: [0.17, 0.6]` **(call)**. `ordered()` appends them after `mv0`. Each built-in load gains `bdia`, and `blen` where Task 1 sourced it; never a twist. Editor ids: `rfTwist`, `rfTwistDir` (select, `R` Right / `L` Left), `rfBLen`, `rfBDia`, `rfStab` (a hint line), under a heading "Barrel and bullet (for spin drift)" placed after "Zero conditions" and before "Correct from a real shot".

Rules:
- All four are optional and independent; whatever is valid is stored. `clean()` drops a field that is not a finite number inside its range, and any `twistDir` other than `'L'`.
- **(call)** With length and diameter both typed, the length must be 2 to 7 times the diameter; otherwise the editor refuses with "Bullet length looks wrong for that diameter. Measure the bullet, not the cartridge." (focus `rfBLen`), and `clean()` drops `blen`.
- `rfStab` is recomputed on input with today's air from `FK.bal.shotAir()` (59 °F and 29.92 inHg when that is null): hidden while anything is missing; "Stability 1.3: marginal for this twist. Spin drift is still shown." for `marginal`; "Stability 0.9: by this formula the bullet is not stable in this twist. Spin drift is not shown." for `unstable`; "Stability 2.4." for `stable`. One decimal. It never blocks Save.
- A hint under the fields: "Bullet length is the bullet alone, from the maker's data or a caliper. For a polymer-tipped bullet the stability figure reads a little low." **(call: no tip-length correction in this release.)**
- The four new ids join the editor's `E` list, so the unsaved-changes guard covers them.

- [ ] **Step 1: Write the failing tests.**

```python
# test_bal_profiles.py
def test_v711_profiles_load_unchanged_and_gain_no_fields(page, app_url): ...
def test_bad_spin_fields_are_dropped_one_by_one(page, app_url):
    # twist '8', twistDir '<b>', blen -1, bdia 0.308 -> only bdia survives; the name and load are intact
def test_length_outside_2_to_7_calibers_is_dropped(page, app_url): ...      # blen 0.3 with bdia 0.308
def test_builtin_loads_carry_a_diameter_and_no_twist(page, app_url): ...
def test_default_card_is_unchanged(page, app_url): ...                        # the BEFORE figures, read through the screen
# test_bal_editor.py
def test_spin_fields_save_and_reopen(page, app_url): ...                      # 8, Left, 0.994, 0.224
def test_right_twist_stores_no_direction(page, app_url): ...
def test_editor_refuses_a_length_wrong_for_the_diameter(page, app_url): ...   # exact message, focus on rfBLen
def test_editor_refuses_values_out_of_range(page, app_url): ...               # twist 2, twist 31, bdia 0.1
def test_stability_line_follows_typing(page, app_url): ...                    # hidden, then stable, marginal, unstable texts
def test_typing_a_twist_makes_the_sheet_dirty(page, app_url): ...             # Back asks Keep editing / Discard
def test_rifle_sheet_still_fits_360_day_and_night_with_enlarged_text(page, app_url, night): ...
```

- [ ] **Step 2:** Run: FAIL. **Step 3:** Implement. **Step 4:** New files then whole suite: PASS. **Step 5:** Commit.

### Task 3: Spin drift on the screen

**Files:**
- Modify: `src/bal-ui.js` (`calc`), `src/bal-sight.js` (`path`), `src/shell.html` (the static "Spin drift and Coriolis are not included yet." hint becomes `<p class="hint" id="bSpin">`)
- Test: `tests/test_bal_screen.py`, `tests/test_bal_sight.py`

**Interfaces:**
- Consumes: `BSPIN.of(profile, { temp, press: res.atm.pIn })`, `BSPIN.drift`.
- Produces: in `calc()`, `rowFor` returns each row with `spinIn` (signed inches, right positive; 0 when not applied) and `windIn` already including it. `BALS.path(row)` appends ` (spin drift 5.2 in right included)` after the drift words when `row.spinIn` is finite and rounds to at least 0.1.

Rules:
- Spin drift is applied only when `BSPIN.of` returns a grade of `stable` or `marginal`. **(call: `unstable` shows none.)**
- `#bSpin` text, exactly one of:
  - `Spin drift not included: add twist and bullet length to the profile. Coriolis is not included.` (the list is `missing` joined with commas and a final "and")
  - `Spin drift not included: by the Miller formula this bullet is not stable in this twist (stability 0.9). Coriolis is not included.`
  - `Windage includes spin drift (stability 2.4, right-hand twist). Coriolis is not included.` ("left-hand" for `L`; ", marginal" after the figure when marginal)
- Dope card, when spin drift is applied and the Drift column is shown: each cell is the net drift with its side, `21.9 L` or `5.2 R`, and `0.0` with no letter when it rounds to zero; the key reads `Drift: inches the wind and the spin move the bullet; R right, L left.` Without spin drift the column and key are as in v7.11.
- "Show all units", turrets, reticle and red dot answers need no change: they read the adjusted `windIn`.

- [ ] **Step 1: Write the failing tests.** `SPIN = {**LOAD, 'id': 'us', 'name': 'Spin rifle', 'twist': 10, 'blen': 1.24, 'bdia': 0.308}`.

```python
def test_no_wind_gives_a_left_hold_that_grows_with_range(page, app_url):
    # wind 0: windage reads L at 600 and at 1000, larger at 1000; a profile without twist reads no windage at all
def test_windage_equals_wind_alone_plus_the_formula(page, app_url):
    # same shot on PLAIN and SPIN: (SPIN drift in) - (PLAIN drift in) == 1.25*(sg+1.2)*tof**1.83 within 0.1 in, tof read from the card
def test_left_twist_mirrors_it(page, app_url): ...
def test_spin_against_the_wind_changes_side_along_the_card(page, app_url):
    # wind 2 mph from 3 o'clock: some rows end ' L', later rows ' R'; no cell matches NASTY or r'[RL] 0\.0'
def test_answer_line_names_the_spin_share(page, app_url): ...           # '(spin drift … in right included)'
def test_spin_line_three_texts(page, app_url): ...                      # missing list, unstable, included; exact strings
def test_builtin_load_says_what_to_add(page, app_url): ...              # 'add twist…'
def test_marginal_is_shown_and_still_applied(page, app_url): ...
def test_card_without_spin_is_byte_for_byte_v711(page, app_url): ...    # headers, key and every cell for PLAIN
# test_bal_sight.py
def test_path_without_spinIn_is_unchanged(ready): ...
def test_path_drops_a_spin_share_that_rounds_to_zero(ready): ...
```

- [ ] **Step 2:** Run: FAIL. **Step 3:** Implement. **Step 4:** Whole suite: PASS (`BEFORE` untouched). **Step 5:** Commit.

### Task 4: The pure zero and close-range module

**Files:**
- Create: `src/bal-zero.js`, `tests/test_bal_zero.py`
- Modify: `build.py` (after `bal-spin.js`)

**Interfaces:**
- Consumes: `BAL.solve`.
- Produces, on a top-level `BALZ`. `load` is a `BAL.solve` input without `ranges`, `wind`, `clock`, `angle` (`{ bc, model, w, mv, sight, zero, zeroAtm, temp, alt, press, rh }`); every solve is level with no wind.
  - `BALZ.CLOSE = [3, 5, 7, 10, 15, 25]`, `BALZ.YDS = [5, 10, 15, 25, 36, 50, 75, 100, 125, 150, 175, 200, 225, 250, 275, 300]`, `BALZ.LIMIT = 500`.
  - `BALZ.close(load) -> { rows: [{ yd, dropIn }] } | { error }`: the path at `CLOSE` with the load's own zero (`dropIn` as `BAL.solve` gives it: negative below the line of sight).
  - `BALZ.compare(load, zeros) -> { cols: [{ zero, path: number[], other, past, peak }] } | { error }`. `zeros`: 2 or 3 distinct numbers; `path[i]` is the path in inches at `YDS[i]` with that zero; `other` is the whole-yard distance of the crossing that is not the zero itself, or `null`; `past` is `true` when there is no other crossing inside `LIMIT` because the bullet is still above the line of sight there; `peak` is `{ yd, pathIn }` for the highest point above the line of sight, or `null` when the path never rises 0.05 in above it.
  - Method: one solve per zero at every whole yard from 1 to `LIMIT`. A value within 0.005 in of zero has no sign. `other` is the sign change more than 2 yd from the zero, placed by linear interpolation. A solve that returns fewer rows than asked (the bullet stops short) uses what it has; `past` is then `false`.

- [ ] **Step 1: Write the failing tests** (`M193` = the `p556m193` built-in's numbers, standard air):

```python
def test_close_rows_are_the_solver_rows(ready): ...                 # equal to BAL.solve at the same six ranges
def test_at_three_yards_the_bullet_is_nearly_a_sight_height_low(ready):
    # dropIn at 3 yd is between -sight and -sight*0.9 for a 100 yd zero
def test_the_other_crossing_is_a_real_zero(ready):
    # zero 36: other is between 200 and 400; solving with zero=other puts the path within 0.15 in of 0 at 36 yd
def test_a_200_yard_zero_first_crosses_inside_100(ready): ...
def test_peak_sits_between_the_two_crossings_and_is_positive(ready): ...
def test_a_zero_at_the_top_of_the_path_has_no_other_crossing_and_no_peak(ready):
    # find the apex zero by scanning; other is None, past False, peak None
def test_past_the_limit_is_reported_not_invented(ready): ...        # a 10 yd zero with 2.6 in sight: other None, past True
def test_bullet_that_stops_short_gives_what_it_has(ready): ...      # bc 0.05, mv 400
def test_path_has_one_value_per_YDS_and_zero_at_its_own_row(ready): ...   # zero 50: |path at 50| < 0.01
def test_bad_zero_lists_are_an_error(ready): ...                    # one zero, four, duplicates, 0, 'x'
def test_solver_error_is_passed_through(ready): ...                 # bc 0
```

- [ ] **Step 2:** Run: FAIL. **Step 3:** Implement. **Step 4:** Whole suite: PASS. **Step 5:** Commit.

### Task 5: Close-range holds sheet

**Files:**
- Create: `src/bal-tools.js` (in `build.py` after `bal-edit.js`)
- Modify: `src/bal-ui.js` (add `FK.bal.load()`), `src/shell.html` (a "Tools" block under the dope card; `<dialog id="dlgClose" class="sheet mk-sheet">`)
- Test: `tests/test_bal_tools.py`; `tests/test_iphone.py` already covers every `mk-sheet`

**Interfaces:**
- Consumes: `BALZ.close`, `BALS.answer(row, { type: 'dot' }).elev.main` for the hold words.
- Produces: `FK.bal.load() -> load | { error: string }` for the selected profile and today's air: the object `calc()` passes to `BAL.solve`, without the shot; the error is the screen's own message (`MSG.profile` or `MSG.cond`). Buttons `#bClose` "Close-range holds" and `#bZeros` "Compare zeros" (the second is wired in Task 6 and hidden until then).

The sheet: title "Close-range holds"; the profile's name; a line "Sight height 2.6 in · zero 100 yd"; a two-column table, "Yd" and "Hold", one row per `BALZ.CLOSE` distance, the hold worded as the red dot answer is ("Hold 2.4 in high"); a line "Level, no wind. Inside the zero the bullet strikes low, so the hold is high."; one button, "Close". With no sight height on the profile: "This profile has no sight height, so every hold reads zero. Tap Edit and set it." above the table **(call: shown, not blocked)**. With `FK.bal.load()` in error: the message and no table. The sheet reads the profile when it opens; it has nothing to save and no guard.

- [ ] **Step 1: Write the failing tests.**

```python
def test_six_rows_and_each_hold_matches_the_solver(page, app_url): ...
def test_every_hold_is_high_for_a_100_yard_zero(page, app_url): ...
def test_no_sight_height_says_so(page, app_url): ...
def test_unusable_profile_shows_the_message_and_no_table(page, app_url): ...   # bc 0 stored
def test_bad_conditions_show_the_conditions_message(page, app_url): ...
def test_back_and_close_both_close_it_and_leave_the_screen_as_it_was(page, app_url): ...
def test_fits_360_day_and_night_with_enlarged_text_and_44px_controls(page, app_url, night): ...
def test_the_tools_block_does_not_move_the_first_screen(page, app_url): ...     # #bWind's top is where it was in v7.11
```

- [ ] **Step 2:** Run: FAIL. **Step 3:** Implement. **Step 4:** Whole suite: PASS. **Step 5:** Commit.

### Task 6: Compare zeros sheet

**Files:**
- Modify: `src/bal-tools.js`, `src/shell.html` (`<dialog id="dlgZeros" class="sheet mk-sheet">`)
- Test: `tests/test_bal_tools.py`

**Interfaces:**
- Consumes: `BALZ.compare`, `BALZ.YDS`, `FK.bal.load()`, `FK.bal.selected()`, `FK.balHost.find`, `FK.bal.save`, `FK.sheet.confirm`.

The sheet:
- Tick boxes for 25, 36, 50, 100 and 200 yd and a field "Other (yd)" accepting 10 to 300 **(call)**. It opens with the profile's own zero ticked (typed into Other when it is not one of the five) plus 50 and 200; when the profile's zero is 50 or 200, 36 takes its place.
- Fewer than two chosen: "Pick two or three zeros." More than three: the last tick is refused with "Up to three at a time." A typed value equal to a ticked one counts once. An unreadable or out-of-range Other: "Enter a zero from 10 to 300 yd." and it is left out.
- The table: "Yd" then one column per zero headed "25 yd zero"; rows at `BALZ.YDS`; cells to one decimal, a minus for below the line of sight, never `-0.0`; key "Inches above the line of sight; a minus means below. Level, no wind."
- Under it, one line per zero: "50 yd zero: crosses the line of sight again at 214 yd. Highest 1.6 in above it, at 130 yd." Or "…does not cross it again inside 500 yd." (`past`). Or "…touches the line of sight there and stays below it." (no `other`, no `peak`).
- For the person's own profile, a button per compared zero that is not the profile's current one: "Use 50 yd zero". It asks, through `FK.sheet.confirm`: title "Set the zero to 50 yd?", text "The card changes now. The rifle itself still has to be re-zeroed at the range.", ok "Set zero". On yes: `FK.bal.save({ ...selected, zero })`, toast "Zero set to 50 yd", the sheet redraws. If the save is refused the sheet stays as it was (the storage message has shown). Zero conditions and a corrected velocity on the profile are kept **(call)**.
- For a built-in load: no Use buttons, and the line "Built-in loads can't be changed. Tap Edit, set the zero range and save it as a new profile."

- [ ] **Step 1: Write the failing tests.**

```python
def test_opens_with_the_profiles_zero_and_two_more(page, app_url): ...           # zero 100 -> 100, 50, 200; zero 50 -> 50, 36, 200; zero 75 -> Other=75
def test_table_cells_match_BALZ(page, app_url): ...
def test_summary_lines_for_other_past_and_touch(page, app_url): ...               # three exact sentences
def test_one_zero_and_four_zeros_are_refused_with_their_messages(page, app_url): ...
def test_typed_zero_same_as_a_ticked_one_counts_once(page, app_url): ...
def test_junk_or_out_of_range_other_is_refused(page, app_url): ...               # '', 'abc', 5, 301
def test_use_this_zero_asks_then_writes_the_profile_and_the_card(page, app_url):
    # the confirm text carries 're-zeroed at the range'; after yes the stored profile's zero is 50, zeroAtm and mv0 intact, #bLoad says 'zero 50 yd'
def test_declining_the_question_changes_nothing(page, app_url): ...
def test_storage_full_leaves_the_profile_and_the_sheet(page, app_url): ...
def test_builtin_load_has_no_use_buttons_and_says_why(page, app_url): ...
def test_back_closes_the_question_first_then_the_sheet(page, app_url): ...       # with a slowed history.go
def test_fits_360_day_and_night_with_enlarged_text(page, app_url, night): ...   # three zeros: the table fits or carries the swipe cue
def test_no_cell_or_line_is_nasty_for_any_builtin(page, app_url): ...           # NASTY over every built-in load
```

- [ ] **Step 2:** Run: FAIL. **Step 3:** Implement. **Step 4:** Whole suite: PASS. **Step 5:** Commit.

### Task 7: Zero comparison chart (kept only if it reads)

**Files:**
- Modify: `src/bal-tools.js`, `src/shell.html`
- Test: `tests/test_bal_tools.py`

The spec allows "a small chart if it reads clearly at phone width in night mode; otherwise the table alone".

An inline SVG above the table in `#dlgZeros`: distance 0 to 300 yd across, inches up, the line of sight as a solid rule at 0, one path per zero. Paths differ by dash pattern (solid, long dash, dot), never by colour alone, and each carries its zero as a text label at its right-hand end. Axis labels at 0, 100, 200, 300 yd and at the lowest and highest whole inch shown. `role="img"` with an `aria-label` naming the zeros and pointing to the table below. Colours from the existing CSS variables.

- [ ] **Step 1: Write the failing tests.**

```python
def test_one_path_per_zero_each_with_its_own_dash_and_label(page, app_url): ...
def test_each_path_meets_the_line_of_sight_at_its_zero(page, app_url): ...      # the path's y at x=zero is the rule's y within 1 px
def test_chart_has_a_text_alternative(page, app_url): ...
def test_labels_do_not_overlap_each_other_or_leave_the_box_at_360(page, app_url, night): ...
```

- [ ] **Step 2:** Run: FAIL. **Step 3:** Implement. **Step 4:** Whole suite: PASS. **Step 5:** Commit.
- [ ] **Step 6: Image-first review.** A reviewer who has not seen the code is given screenshots only (360 x 640, day and night; 25/50/200 and 36/100) and writes down, from the picture alone, which zero each line is, where each crosses the line of sight again, and which path is highest at 150 yd. Two answers wrong on either screenshot: remove the chart, keep the table, log it in the rulings.

### Task 8: Reviews, record, release stop

- [ ] **Step 1:** Three reviews in parallel, each by a reviewer who has not seen the build: (a) whole-branch code review, told to read `bal-ui.js`'s `calc()` and `bal-tools.js` whole and to triage every deferred minor; (b) a maths and sources review that re-opens every source in the fixture and re-computes three spin cases and two zero comparisons with a script of its own; (c) a tester who drives the built app at phone size from screenshots as four rifles (a .308 with mil turrets and a 1:10 twist; an AR with a red dot; an AR with a drop reticle and a left-hand twist typed by mistake; a built-in load), judging from the screen.
- [ ] **Step 2:** One fix round with a ruling beside each finding, then a re-check that reads the fix diff **and** drives the app (the last three releases each had a fault introduced by the fix round).
- [ ] **Step 3:** Write `docs/ballistics-rulings.md` "Release 2" (every call above and every one made during the build, each with its cost if wrong; accepted limits; what could not be tested) and the phone-check list, which must include: a real rifle's known twist and bullet, the windage at 600 and 1,000 yd compared with what it needs in still air; the compare table against a real 50 yd and 100 yd zero at 25 and 200 yd; the close-range holds at 7 and 25 yd on paper; both sheets on the iPhone.
- [ ] **Step 4:** Build, whole suite, push the branch, confirm GitHub's three checks are green on it. **Stop: hand Jordan the rulings ledger and the phone-check list and wait for his go.** On his go: fetch and merge `main`, set both version constants, `python3 build.py --release .`, squash onto `main`, push, confirm the Pages deployment, update `claude/FIELD-KIT-STATUS.md` in the project.
