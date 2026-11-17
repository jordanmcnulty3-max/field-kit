# Field Kit v6: Emergency Rebuild Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the four-topic Emergency tab with about 50 guided protocols and procedures, emergency tools, app-wide search and back-button navigation, released as v6.

**Architecture:** Protocols are JSON files validated and inlined by `build.py` as `window.FK_DATA`. One section-agnostic player engine renders them; a hash router gives every screen an address; tools and search are separate modules that attach to the existing `window.FK` namespace. Output stays one self-contained `index.html`.

**Tech Stack:** Vanilla JS (no framework, no bundler), Python 3 build script, `unittest` for build validation, Python Playwright (Chromium, headless) for browser tests served from `http://localhost`.

**Spec:** `docs/superpowers/specs/2026-11-16-emergency-survival-overhaul-design.md` (read it first; this plan implements section 5 to 8, phase 1 only).

## Global Constraints

- Edit `src/`, `figs/`, `tools/`, `tests/`, `docs/` and `build.py` only. Root `index.html`, `sw.js`, `manifest.json`, `leaflet.*` are build output.
- No network calls at runtime. No new runtime dependencies. One `index.html`.
- No 911 or phone-dial button or `tel:` link anywhere.
- Help wording in protocols: "Call 911 if you have signal. If not, send someone for help and prepare to move the casualty."
- Existing storage keys keep their names and shapes: `tq`, `wps`, `target`, `tab`, `view`, `region`, rifle profiles. v5 data must load unchanged.
- New storage keys: `pins`, `recent`, `proto.active`, `patients`, `advAck`. All go through `FK.store` and into backup/restore.
- Emergency touch targets at least 56px. Step action text at least 20px. No step text is cut to fit; action over 200 characters is a build warning, never an error.
- Keep existing colour tokens, dark theme and red night mode. No decorative animation.
- Nothing may require an Android-only API: `navigator.vibrate`, `navigator.wakeLock` and `AudioContext` are all optional at every call site.
- Medical content follows spec section 7 exactly. Sources are looked up at writing time, never recalled. Every protocol has `sources` and `reviewed`.
- Version: `APP_VERSION = '6'` in `src/app.js` and `VERSION = 'fieldkit-v6'` in `src/sw.js`.
- Commit after every task. Commit trailer per repo convention.

## Review Focus

1. **Address points at something that no longer exists** (`#/emergency/removed-id/9`, or `proto.active` naming a deleted step after an update): opens Emergency home with no blank screen and clears the stale value. Test in Task 2 and Task 3.
2. **Stored values with the wrong shape** (`pins` is a string, `patients` holds nulls, `recent` has unknown ids): ignored item by item; the app still starts. Test in Task 4 and Task 6.
3. **Phone without audio, vibration or wake lock** (iPhone, or audio blocked): CPR coach still counts and prompts on screen; no exception. Test in Task 5.
4. **Storage full while writing a patient log or pin:** the existing `FK.FULL_MSG` toast shows; earlier entries are intact. Test in Task 6.
5. **No GPS fix, or an old one, when building a 9-line:** location line is empty and editable, or shows the fix with its age; never a silent stale position. Test in Task 7.

---

## File Structure

| File | Responsibility |
|---|---|
| `src/protocols/<id>.json` | One protocol or procedure each |
| `tools/validate.py` | Pure validation of protocol data |
| `build.py` | Load, validate, inline `FK_DATA`; concatenate new scripts |
| `src/router.js` | Hash parsing, history, `FK.route` |
| `src/protocol.js` | Player engine, all-steps view, resume, advanced acknowledgement |
| `src/emergency.html` | Emergency home markup (replaces the block in `shell.html`) |
| `src/emergency.js` | Home rendering: categories, pins, recents, resume card, active timers |
| `src/emergency-tools.js` | Tourniquet timers, CPR coach, rate counter, burn area |
| `src/patients.js` | Patient log store and UI, `FK.log` |
| `src/reports.js` | MEDEVAC 9-line and MIST builder |
| `src/search.js` | Index and search overlay |
| `figs/figs.py` | New positioning diagrams |
| `tests/test_validate.py` | Build validation tests |
| `tests/conftest.py`, `tests/test_*.py` | Playwright tests against the built app |
| `docs/content-review.md` | Per-protocol sources, numbers checked, source disagreements |

Script concatenation order in `build.py`: `geo.js, ballistics.js, app.js, router.js, protocol.js, emergency-tools.js, patients.js, reports.js, emergency.js, search.js, map.js, survival.js`.

---

### Task 1: Protocol data pipeline

**Files:**
- Create: `tools/validate.py`, `tests/test_validate.py`, `src/protocols/bleeding.json`, `src/protocols/cpr-adult.json`
- Modify: `build.py`

**Interfaces:**
- Produces: `validate(protocols: list[dict], fig_names: set[str]) -> tuple[list[str], list[str]]` returning `(errors, warnings)`.
- Produces at runtime: `window.FK_DATA = { protocols: [...] }`, emitted by `build.py` in a `<script>` before the app scripts, sorted by `id`.
- Constants in `validate.py`: `CATEGORIES = {'life','injury','environment','bites','illness','advanced'}`, `TOOLS = {'tq','cpr','rate','burn'}`, `ACTION_WARN_LEN = 200`.

- [ ] **Step 1: Write failing tests** in `tests/test_validate.py`, one test per rule, each building a minimal valid protocol and breaking one thing:

```python
def test_valid_protocol_has_no_errors(): assert validate([ok()], set()) == ([], [])
def test_duplicate_protocol_id(): assert any('duplicate' in e for e in validate([ok(), ok()], set())[0])
def test_duplicate_step_id(): ...
def test_branch_target_missing(): ...   # ask.yes = 'nope'
def test_unreachable_step(): ...        # a step no path from steps[0] reaches
def test_missing_sources(): ...
def test_missing_reviewed(): ...
def test_unknown_fig(): ...             # fig not in fig_names
def test_unknown_tool(): ...
def test_unknown_category(): ...
def test_advanced_requires_indications_contraindications_equipment_complications(): ...  # four asserts
def test_long_action_is_warning_not_error():
    e, w = validate([ok(text='x' * 201)], set()); assert e == [] and len(w) == 1
def test_long_detail_is_fine():
    assert validate([ok(detail='x' * 5000)], set()) == ([], [])
```

Reachability rule: from a step, the next step is the following array item unless the step has `ask` (then `yes` and `no` targets) or `"end": true`.

- [ ] **Step 2: Run** `python3 -m unittest tests.test_validate -v`. Expected: import error.
- [ ] **Step 3: Implement** `validate` in `tools/validate.py`.
- [ ] **Step 4: Run** the tests. Expected: all pass.
- [ ] **Step 5: Wire `build.py`:** load every `src/protocols/*.json`, call `validate(protocols, set(figs.F))`, print warnings, `sys.exit` listing all errors if any, and insert `<script>window.FK_DATA=…</script>` (JSON with `</` escaped as `<\/`) immediately before the `/*__SCRIPTS__*/` script. Resolve each step's `fig` into inline SVG under `step.figSvg` using the same `figs.F` lookup the survival build uses.
- [ ] **Step 6: Write the two seed protocols** from the existing v5 text in `src/shell.html` (bleeding, adult CPR), each with `"reviewed"` and placeholder-free `sources`. They are rewritten properly in Task 10; this is fixture data for the engine.
- [ ] **Step 7: Run** `python3 build.py /tmp/fk && grep -c FK_DATA /tmp/fk/index.html`. Expected: build prints v5 line, grep prints `1`.
- [ ] **Step 8: Commit.**

### Task 2: Browser test harness and router

**Files:**
- Create: `tests/conftest.py`, `tests/test_router.py`, `src/router.js`
- Modify: `src/app.js` (navigation block, lines 58 to 86), `build.py` (script list)

**Interfaces:**
- Produces: `FK.route.parse(hash: string) -> { tab: 'survival'|'tactical'|'emergency', parts: string[] }`; `FK.route.go(path: string, opts?: { replace: boolean })`; `FK.route.current() -> same shape as parse`; emits `FK.emit('route', route)` on every change.
- Address grammar: `#/<tab>` or `#/<tab>/<part>/<part>`. Empty or unknown tab falls back to the stored `tab`, then `tactical`.
- `tests/conftest.py` produces fixtures: `app_url` (session: builds into a temp dir, serves it on a free localhost port) and `page` (fresh context per test, service workers blocked).

- [ ] **Step 1: Write `tests/conftest.py`** with the two fixtures.
- [ ] **Step 2: Write failing tests** in `tests/test_router.py`:

```python
def test_tab_click_changes_hash(page, app_url)        # click Emergency -> url ends '#/emergency'
def test_back_returns_to_previous_tab(page, app_url)  # tactical -> emergency -> page.go_back() -> Tactical visible
def test_deep_link_opens_tab(page, app_url)           # goto '#/emergency' -> #tab-emergency visible
def test_unknown_tab_falls_back(page, app_url)        # goto '#/nonsense/x' -> a real tab is visible, no console error
def test_v5_stored_tab_still_honoured(page, app_url)  # localStorage fk tab='survival', goto '' -> Survival visible
```

- [ ] **Step 3: Run** `python3 -m pytest tests/test_router.py -v`. Expected: fail.
- [ ] **Step 4: Implement `src/router.js`** and change `showTab` so tab buttons call `FK.route.go('/' + id)` and the router calls `showTab`. `showTab` stays the only function that toggles tab visibility. Expose `showTab` on `FK`.
- [ ] **Step 5: Run** the tests, then the whole suite. Expected: pass.
- [ ] **Step 6: Commit.**

### Task 3: Protocol player

**Files:**
- Create: `src/protocol.js`, `tests/test_player.py`
- Modify: `src/shell.html` (add `<section id="player" hidden>` inside `<main>`, plus CSS), `build.py`

**Interfaces:**
- Consumes: `FK_DATA.protocols`, `FK.route`, `FK.store`, `FK.setWake`.
- Produces: `FK.protocol.get(id) -> protocol | undefined`; `FK.protocol.open(id, stepId?)`; `FK.protocol.close()`; `FK.protocol.active() -> { id, step, started } | null`.
- Addresses: `#/emergency/<id>` (first step), `#/emergency/<id>/<stepId>`, `#/emergency/<id>/all`.
- Storage: `proto.active = { id, step, started }`, written on every step change, cleared on the last step's Done or on explicit "End protocol".
- Step tool hook: a step with `tool` renders a button that calls `FK.tools.start(step.tool, { protocol: id })` (defined in Task 5; until then the button is omitted if `FK.tools` is undefined).
- Step log hook: when a step with `log` is passed with NEXT, call `FK.log && FK.log(step.log)`.
- `advAck`: boolean in storage; opening a protocol with `tier: 'advanced'` when false shows the acknowledgement screen first. Exact copy: "These procedures can kill if done wrong or when they are not needed. They are a reference for people who have trained on them hands-on. Reading this is not training." Button: "I understand, show procedures".

- [ ] **Step 1: Write failing tests** in `tests/test_player.py`:

```python
def test_open_shows_first_step_action_and_progress
def test_next_and_back_move_one_step_and_update_hash
def test_android_back_steps_back_then_leaves_player
def test_branch_yes_and_no_go_to_named_steps          # fixture protocol injected via page.add_init_script
def test_detail_text_is_shown_untruncated             # 3000-char detail present in DOM in full
def test_all_steps_view_lists_every_step_donts_evacuate_sources_reviewed
def test_progress_survives_reload_and_offers_resume   # reload -> FK.protocol.active() matches
def test_unknown_protocol_id_goes_to_emergency_home   # Review Focus 1
def test_stale_active_step_is_cleared                 # Review Focus 1: proto.active.step not in protocol
def test_advanced_requires_acknowledgement_once
def test_focus_moves_to_action_on_step_change
def test_next_button_height_at_least_56px
```

- [ ] **Step 2: Run.** Expected: fail.
- [ ] **Step 3: Implement.** The player is a full-screen section that hides the tab content and tab bar while open; header shows back, title, pin star, all-steps toggle. Wake lock requested on open and released on close, both guarded.
- [ ] **Step 4: Run.** Expected: pass.
- [ ] **Step 5: Commit.**

### Task 4: Emergency home

**Files:**
- Create: `src/emergency.html`, `src/emergency.js`, `tests/test_home.py`
- Modify: `src/shell.html` (remove the old `#tab-emergency` block and its CSS that is no longer used), `build.py` (splice `emergency.html` the same way `survival.html` is spliced)

**Interfaces:**
- Consumes: `FK_DATA`, `FK.protocol`, `FK.route`, `FK.store`.
- Produces: `FK.pins.has(key)`, `FK.pins.toggle(key)`, `FK.pins.all() -> string[]`; `FK.recent.add(key)`, `FK.recent.all() -> string[]` (max 5, newest first). Keys are `p:<protocolId>`, `t:<toolName>`, `s:<survivalTopicId>`.
- Category labels: `life` "Life threats" (rendered as the three fixed buttons Bleeding, Not breathing, Choking, plus the rest under "More life threats"), `injury` "Injuries", `environment` "Heat, cold, environment", `bites` "Bites, stings, poison", `illness` "Sudden illness", `advanced` "Advanced procedures", then "Tools" and "Reports".
- "Not breathing" opens a chooser: Adult, Child, Infant.
- Footer copy unchanged: "Reference only, not a substitute for training. Take a Stop the Bleed, CPR and wilderness first aid course."

- [ ] **Step 1: Write failing tests:**

```python
def test_three_life_threat_buttons_visible_without_scrolling   # viewport 360x640
def test_any_protocol_reachable_in_two_taps                    # for every id in FK_DATA: category tap, protocol tap
def test_pin_appears_under_pinned_and_survives_reload
def test_recent_lists_last_five_newest_first
def test_resume_card_shows_only_when_protocol_active
def test_malformed_pins_and_recent_are_ignored                 # Review Focus 2
def test_no_tel_links_or_dial_buttons                          # page.locator('a[href^="tel:"]').count() == 0
```

- [ ] **Step 2: Run.** Expected: fail.
- [ ] **Step 3: Implement.**
- [ ] **Step 4: Run** the whole suite. Expected: pass.
- [ ] **Step 5: Commit.**

### Task 5: Tourniquet timers and CPR coach

**Files:**
- Create: `src/emergency-tools.js`, `tests/test_tools.py`
- Modify: `src/app.js` (delete the tourniquet and CPR blocks, lines 434 to 491), `src/emergency.html`

**Interfaces:**
- Consumes: `FK.store`, `FK.list`, `FK.okId`, `FK.fin`, `FK.setWake`.
- Produces: `FK.tools.start(name: 'tq'|'cpr'|'rate'|'burn', opts?)` opening the tool as an overlay addressable at `#/emergency/tool/<name>`; `FK.tools.tq.active() -> { id, limb, start }[]`.
- Storage `tq`: unchanged shape `[{ id, limb, start }]`.
- CPR coach values: 110 per minute; modes `adult`, `child`, `infant`; 30 compressions then a "2 breaths" prompt held for 4 seconds unless compression-only is on; cycle counter; rescuer-swap prompt every 120 seconds of compressions. Mode-specific depth and hand-position text comes from the matching protocol's steps, not hard-coded here.

- [ ] **Step 1: Write failing tests:**

```python
def test_v5_running_tourniquet_timer_survives_update   # seed localStorage 'tq' in v5 shape, load, timer shows elapsed
def test_start_timer_adds_row_and_persists
def test_active_timers_strip_on_home_links_to_tool
def test_cpr_counts_to_30_then_prompts_breaths          # page.clock to advance time
def test_cpr_compression_only_never_prompts_breaths
def test_cpr_swap_prompt_at_120_seconds
def test_cpr_works_without_audio_vibrate_wakelock       # Review Focus 3: delete the three APIs in init script
```

- [ ] **Step 2: Run.** Expected: fail.
- [ ] **Step 3: Implement** by moving the existing code and extending it. Every `AudioContext`, `navigator.vibrate` and `navigator.wakeLock` use is guarded.
- [ ] **Step 4: Run** the whole suite. Expected: pass.
- [ ] **Step 5: Commit.**

### Task 6: Patient log, rate counter, burn area

**Files:**
- Create: `src/patients.js`, `tests/test_patients.py`
- Modify: `src/emergency-tools.js`, `src/emergency.html`

**Interfaces:**
- Storage `patients`: `[{ id, name, created, entries: [{ t, kind, text, pulse?, resp?, avpu? }] }]`; `kind` is `note|vitals|event`; `avpu` is `A|V|P|U`.
- Produces: `FK.patients.all()`, `FK.patients.current() -> patient` (creates "Casualty 1" on first use), `FK.patients.setCurrent(id)`, `FK.patients.add(entry) -> boolean` (false when storage is full), `FK.patients.text(id) -> string` (plain-text export, one entry per line with local time), `FK.log(text)` = add an `event` entry to the current patient.
- Rate counter: 15-second tap window, result = taps × 4, "Save as pulse" and "Save as breathing" buttons.
- Burn area: tappable regions with adult rule-of-nines values (head 9, each arm 9, chest 9, abdomen 9, upper back 9, lower back 9, each leg 18, groin 1) and child values (head 18, each arm 9, front torso 18, back torso 18, each leg 14); output total percent. Guidance text beside the total is taken from the burns protocol's `evacuate` list, not hard-coded. Confirm both tables against the burn source used in Task 11 and correct here if they differ.

- [ ] **Step 1: Write failing tests:**

```python
def test_first_log_creates_casualty_1
def test_protocol_step_with_log_adds_event_entry
def test_rate_counter_15_taps_in_15s_reads_60
def test_burn_adult_one_arm_and_chest_reads_18
def test_burn_child_head_reads_18
def test_export_text_contains_every_entry_in_time_order
def test_malformed_patients_are_filtered                # Review Focus 2
def test_storage_full_shows_message_and_keeps_entries   # Review Focus 4: stub Storage.setItem to throw
```

- [ ] **Step 2 to 5:** run failing, implement, run passing, commit.

### Task 7: MEDEVAC 9-line and MIST

**Files:**
- Create: `src/reports.js`, `tests/test_reports.py`
- Modify: `src/emergency.html`

**Interfaces:**
- Consumes: `FK.getFix() -> { lat, lon, acc, t } | null`, MGRS conversion from `src/geo.js`, `FK.patients`.
- Produces: `FK.reports.nineLine(fields) -> string`, `FK.reports.mist(patientId) -> string`; overlay at `#/emergency/report/9line` and `#/emergency/report/mist`.
- 9-line fields in order: 1 location (MGRS), 2 frequency and callsign, 3 patients by precedence, 4 special equipment, 5 patients by type (litter, ambulatory), 6 security at pickup site, 7 marking method, 8 patient nationality and status, 9 terrain or hazards. Confirm the line wording against the TCCC source during Task 15 and correct here if it differs.
- MIST: Mechanism, Injuries, Signs (latest vitals from the log), Treatment (event entries).
- Location rule: fix newer than 2 minutes pre-fills line 1; older pre-fills with "(fix N min old)"; no fix leaves it blank. Always editable.
- Output actions: Copy, and Share via `navigator.share` when present.

- [ ] **Step 1: Write failing tests:**

```python
def test_fresh_fix_prefills_mgrs
def test_old_fix_shows_age                    # Review Focus 5
def test_no_fix_leaves_location_blank         # Review Focus 5
def test_nine_line_text_has_nine_numbered_lines_in_order
def test_mist_pulls_latest_vitals_and_treatments_from_log
```

- [ ] **Step 2 to 5:** run failing, implement, run passing, commit.

### Task 8: App-wide search

**Files:**
- Create: `src/search.js`, `tests/test_search.py`
- Modify: `src/shell.html` (magnifier button in the header, overlay markup), `src/survival.html` (add stable `id` to each `details.ref`)

**Interfaces:**
- Produces: `FK.search.query(q: string) -> { key, title, where, snippet }[]`, best first; overlay at `#/search`.
- Indexed: every protocol (title weight 5, keywords 4, summary 3, step text and detail 1); every survival topic (summary title 5, body 1); app screens with fixed keywords: Map, Position and compass, Ballistics, Saved areas, Waypoints, Settings and backup, each tool, each report.
- Matching: case-insensitive, all query words must match, prefix match counts.
- Opening a survival result switches to the Survival tab, opens that `details`, and scrolls to it.

- [ ] **Step 1: Write failing tests:**

```python
def test_every_protocol_found_by_title            # loop over FK_DATA
def test_every_protocol_found_by_first_keyword
def test_title_match_ranks_above_body_match
def test_survival_topic_result_opens_that_topic
def test_app_screen_result_opens_ballistics
def test_empty_query_shows_pinned_and_recent
def test_back_closes_search
```

- [ ] **Step 2 to 5:** run failing, implement, run passing, commit.

### Task 9: Backup, restore and migration

**Files:**
- Modify: `src/app.js` (settings and backup block, around line 536)
- Create: `tests/test_migration.py`, `tests/fixtures/v5-backup.json`, `tests/fixtures/v5-localstorage.json`

- [ ] **Step 1: Write failing tests:**

```python
def test_backup_includes_pins_recent_patients_advAck
def test_backup_excludes_proto_active
def test_restore_v5_backup_loads_waypoints_tq_profiles_and_leaves_new_keys_empty
def test_v5_localstorage_boots_with_no_console_errors
```

- [ ] **Step 2 to 5:** run failing, implement, run passing, commit.

### Tasks 10 to 15: Content

Each content task follows the same steps. Protocol ids are fixed here so search keywords, cross-links and tests agree.

- [ ] **Step 1:** For each protocol, find the current edition of the governing source (spec section 7 order) on the web and read the relevant section. Record source name, year and URL.
- [ ] **Step 2:** Write `src/protocols/<id>.json`. Action text is the thing to do now; put how, why, what to watch for, variations and common mistakes in `detail` with no length limit. Add `keywords` (lay words people would type), `donts`, `evacuate`, `log` on steps that record a treatment, `tool` where a tool applies, `ask` where the next step depends on an answer.
- [ ] **Step 3:** Second pass: re-open the source and check every number (depths, rates, ratios, times, temperatures, sizes, doses). Record each checked value in `docs/content-review.md` under the protocol id.
- [ ] **Step 4:** Where two sources disagree, write both positions under "Open questions for Jordan" in `docs/content-review.md` and use the higher-authority source meanwhile.
- [ ] **Step 5:** `python3 build.py /tmp/fk` with zero errors, then `python3 -m pytest tests -q`. Expected: pass (search and two-tap tests iterate over all protocols).
- [ ] **Step 6:** Commit.

**Task 10: Life threats.** `bleeding`, `cpr-adult`, `cpr-child`, `cpr-infant`, `choking`, `choking-infant`, `recovery-position`, `anaphylaxis`, `chest-wound`, `shock`. `bleeding` uses tool `tq`; the three CPR protocols use tool `cpr`; `chest-wound` links to `needle-decompression`.

**Task 11: Injuries.** `march`, `head-injury`, `spine-injury`, `fracture`, `sprain-dislocation`, `burns`, `eye-injury`, `amputation`, `impaled-object`, `abdominal-wound`, `wound-care`, `blisters`. `burns` uses tool `burn`; confirm the Task 6 burn tables here.

**Task 12: Heat, cold, environment.** `hypothermia`, `frostbite`, `heat-illness`, `dehydration`, `altitude`, `lightning`, `drowning`, `carbon-monoxide`.

**Task 13: Bites, stings, poison.** `snakebite`, `tick`, `stings`, `spider-scorpion`, `animal-bite`, `poisoning`, `poison-plants`.

**Task 14: Sudden illness.** `chest-pain`, `stroke`, `seizure`, `low-blood-sugar`, `asthma`, `overdose`, `fainting`, `vomiting-diarrhea`.

**Task 15: Advanced procedures.** `npa`, `needle-decompression`, `cricothyrotomy`, `hemostatic-packing`, `junctional-bleeding`, `pelvic-binder`, `traction-splint`, `tourniquet-conversion`, `wound-closure`, `dislocation-reduction`. All `tier: "advanced"` with `indications`, `contraindications`, `equipment`, `complications`. Sources: current TCCC guidelines and skill sheets, Wilderness Medical Society guidelines. A procedure the sources do not describe at any published tier is left out and noted in `docs/content-review.md`. Confirm the Task 7 nine-line wording here.

### Task 16: Emergency diagrams

**Files:**
- Modify: `figs/figs.py`, the protocols that reference them

- [ ] **Step 1:** Add to `figs.F`, in the existing drawing style: `tq-placement`, `recovery-position`, `cpr-hands-adult`, `cpr-infant-fingers`, `back-blows`, `abdominal-thrusts`, `splint-forearm`, `pressure-dressing`. Positioning only; no wounds or anatomy cross-sections.
- [ ] **Step 2:** Reference each from its protocol step with `"fig"`.
- [ ] **Step 3:** Build and open each in the browser test `test_every_fig_step_renders_an_svg` (add to `tests/test_player.py`). Expected: pass.
- [ ] **Step 4:** Commit.

### Task 17: Release v6

- [ ] **Step 1:** Set `APP_VERSION = '6'` and `VERSION = 'fieldkit-v6'`.
- [ ] **Step 2:** `python3 build.py` (into the repo root) and `python3 -m unittest tests.test_validate && python3 -m pytest tests -q`. Expected: all pass, zero build errors.
- [ ] **Step 3:** Screenshot Emergency home, one protocol step and the CPR coach at 360×640 in day and night themes; look at each for clipped text and unreadable contrast; fix what is found.
- [ ] **Step 4:** Send Jordan `docs/content-review.md` "Open questions" and the screenshots. Wait for answers; apply them.
- [ ] **Step 5:** Commit `v6: Emergency rebuild`, tag `v6`.
- [ ] **Step 6:** Push with Jordan's short-lived token, or hand him the changed file list for manual upload.
- [ ] **Step 7:** After he confirms Settings shows "Version 6" on the phone, update the project doc `claude/FIELD-KIT-STATUS.md`: current version, changelog row, backlog (phases 2 to 4, mass-casualty triage, team medical cards, hosting decision for a closed system).
