# v7 Survival Framework Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rebuild the Survival tab as a data-driven knowledge center (home, topic pages, filters, checklists, two tools), move the 14 existing topics into validated data files, source-check every one of them, fold in the v6 backlog fixes, and release as v7.

**Architecture:** Topics and checklists become one JSON file each under `src/survival/` and `src/checklists/`, validated by `tools/validate.py` and inlined by `build.py` into `window.FK_DATA` next to the protocols. `src/survival.js` is rewritten to draw the home, topic pages and checklists from that data at `#/survival/...` addresses; survival tools are plain Survival pages in `src/survival-tools.js`, not the Emergency tools overlay. Pins, recents and search learn two new key letters.

**Tech Stack:** Vanilla JS in one inlined script (no modules, everything hangs off `window.FK`), Python 3 build and validator, `unittest` for the validator, pytest + Playwright Chromium at 360×640 for the app.

**Spec:** `docs/superpowers/specs/2026-11-17-v7-survival-knowledge-center-design.md` (read it before any task). Earlier design for the patterns being reused: `docs/superpowers/specs/2026-11-16-emergency-survival-overhaul-design.md`.

## Global Constraints

- Edit `src/`, `figs/`, `tools/`, `tests/`, `docs/`, `build.py` only. Root `index.html`, `sw.js`, `manifest.json`, `leaflet.*` are build output; only Task 17 rebuilds them.
- No network after install. No new dependencies. No 911 or phone-dial control.
- No drawings of edible plants. Clove hitch, taut-line, square knot and sheet bend stay text-only. A diagram not recognisable without its caption is removed.
- No instructions for improvised weapons, explosives, or traps meant for people.
- Region: New York and the Northeast US, Central New York first.
- Every number and instruction in content comes from a source that was actually opened and is recorded in `docs/content-review.md`. Do not use the Firecrawl connector; use built-in web search and fetch.
- Stored values that are unknown or malformed are ignored, never rendered. Every string written into markup goes through `FK.esc`.
- Touch targets at least 48px in Survival. Same theme tokens and night mode. No decorative animation.
- Existing topic ids (`surv-<slug>`) are kept exactly.
- Versions are `major` or `major.minor`, set in both `src/app.js` (`APP_VERSION`) and `src/sw.js` (`VERSION`).
- Tests: `python3 -m unittest tests.test_validate && python3 -m pytest tests -q`. Any browser console error fails a test. All existing tests keep passing unless a task says a test changes.
- Commit after every task with the repo's attribution trailer. Work on branch `v7-survival`. Do not push to `main` before Task 17.

## Review Focus

1. A stored pin or recent whose key no longer resolves (`s:` of a deleted topic, `c:`/`u:` of an unknown list or tool, a key letter from a newer version): skipped silently on both homes and in search, no console error. Test in Task 6.
2. A deep link to something that does not exist (`#/survival/nope`, `#/survival/list/nope`, `#/survival/tool/nope`): shows the Survival home and corrects the address without adding a history entry, so Back still leaves the app. Test in Task 4.
3. Daylight and moon with no position yet, with a typed position at a latitude where the sun does not rise or set that day, and on a clock-change day: a prompt to get a fix or type a position; "Does not rise" / "Does not set" instead of a time; times in the phone's local time, correct on both sides of the change. Tests in Task 10.
4. Restoring a v6.2 backup (no `fk.checks`, no `fk.survFilter`, five recents) and a backup with a malformed `fk.checks`: restore succeeds, checklists show zero ticks, nothing throws. Test in Task 8.
5. A filter that leaves a category empty, and a stored filter value that is no longer valid: the category shows "No topics for this filter"; an invalid stored value behaves as Any. Test in Task 5.

---

## File map

| File | Responsibility |
|---|---|
| `tools/validate.py` | adds `validate_topics`, `validate_checklists`, `topic_draft_ids` |
| `tools/convert_survival.py` | one-off: old `src/survival.html` → `src/survival/*.json`; kept in the repo for the record |
| `src/survival/<id>.json` | one topic each |
| `src/checklists/<id>.json` | one checklist each |
| `build.py` | loads, validates, inlines topics and checklists; release block on drafts |
| `src/survival.html` | home skeleton only |
| `src/survival.js` | data access, home, filters, topic page, checklist page, routing inside the tab |
| `src/survival-tools.js` | tool registry and the two tools' pages |
| `src/astro.js` | pure sun and moon maths, no DOM |
| `src/emergency.js` | key pattern, recents cap, section-aware lists |
| `src/search.js` | index from data, new key letters, Recent clear |
| `docs/v7-migration.md` | every deletion and every correction made to the old topics |
| `tests/test_survival_*.py`, `tests/test_astro.py` | new browser tests |

Shared names (used across tasks):

- Categories, in display order: `basics`, `water`, `heat`, `radiation`, `food`, `comms`, `staying`, `moving`, `town`. Labels: Basics · Water and sanitation · Heat, shelter and winter · Radiation and fallout · Food · Comms · Staying put · Moving · Town hazards and health.
- `where` values: `town`, `rural`, `woods`, `coast`. `when` values: `cold`, `warm`.
- Keys: `s:<topicId>`, `c:<checklistId>`, `u:<toolName>`.
- Addresses: `#/survival`, `#/survival/<topicId>`, `#/survival/list/<checklistId>`, `#/survival/tool/<toolName>`.
- Storage (through `FK.store`): `survFilter` = `{ where, when }` with `'any'` allowed; `checks` = `{ [checklistId]: string[] of ticked item ids }`; `recent` = up to 20 keys.

---

### Task 1: Topic and checklist validation

**Files:**
- Modify: `tools/validate.py`
- Test: `tests/test_validate.py` (new classes `TopicValidation`, `ChecklistValidation`)

**Interfaces:**
- Produces:
  - `validate_topics(topics: list, fig_names: set[str], link_keys: set[str]) -> tuple[list[str], list[str]]` (errors, warnings). `link_keys` is every key a `link` block may point at.
  - `validate_checklists(lists: list, link_keys: set[str]) -> tuple[list[str], list[str]]`
  - `topic_draft_ids(items: list) -> list[str]` (works for topics and checklists)
  - Constants `TOPIC_CATEGORIES`, `WHERE`, `WHEN`, `RESERVED_TOPIC_IDS = {'tool', 'list'}`.
- Topic schema: spec section 5.3. Block is a dict with exactly one of the shapes `{p}`, `{list}`, `{steps}`, `{warn}`, `{table: {head, rows}}`, `{fig, cap}`, `{link, label}`.
- Checklist schema: `id` (pattern `[a-z0-9][a-z0-9-]{0,59}`), `title`, `category`, optional `summary`, `items: [{id, text, note?}]` with unique item ids, `sources`, `reviewed`, optional `draft`.

- [ ] **Step 1: Write failing tests.** One valid fixture topic and checklist produce no errors. Then one test per rule, each asserting the error text contains the id and the reason:
  - topic id not matching `surv-[a-z0-9-]{1,55}`; duplicate id; id in `RESERVED_TOPIC_IDS`
  - unknown top-level key; unknown block key; a block with two shapes; an empty `sections`; a section without `h`
  - category not in `TOPIC_CATEGORIES`; `where`/`when` value outside the lists
  - `fig` not in `fig_names`; `fig` block without `cap`
  - `link` not in `link_keys`; `link` without `label`
  - `table` rows whose length differs from `head`
  - missing or empty `sources`; a source without `name` or `used`; missing `reviewed`; `asOf` not `YYYY-MM-DD`
  - `draft: true` is a warning, not an error, and appears in `topic_draft_ids`
  - checklist: duplicate item id, empty `items`, blank item `text`
  - inputs that are not dicts (string, `None`) give an error and do not raise
  - the input is not mutated
- [ ] **Step 2:** Run `python3 -m unittest tests.test_validate`; the new tests fail on missing names.
- [ ] **Step 3:** Implement the three functions, reusing `_unknown_keys`, `_blank`, `_bad_list` and the existing error wording style.
- [ ] **Step 4:** Run the same command; all pass.
- [ ] **Step 5:** Commit `validate: topics and checklists`.

### Task 2: Convert the 14 topics to data

**Files:**
- Create: `tools/convert_survival.py`, `src/survival/surv-*.json` (14 files plus `surv-priorities.json`), `docs/v7-migration.md`, `tests/fixtures/survival-v6.html`
- Test: `tests/test_survival_migration.py` (plain pytest, no browser)

**Interfaces:**
- Consumes: Task 1 schema.
- Produces: 15 topic files, every one with `"draft": true`, `"reviewed": "2026-11-17"`, and a placeholder source `{"name": "Not yet source-checked", "used": "Converted from v6 text; checked in Tasks 13 to 16"}`. Category for all 15 is `basics` (packs move them later). `{{fig:name|caption}}` markers become `{fig, cap}` blocks.

- [ ] **Step 1: Write the failing test** `test_converted_text_equals_old_text_minus_listed_deletions`: parse `tests/fixtures/survival-v6.html` (a copy of the v6.2 `src/survival.html`, saved by this task before the file is changed), flatten each `details.ref` to whitespace-normalised text with headings, list items and figure captions in order; flatten each JSON topic the same way; assert equality after removing the passages listed under "Deletions" in `docs/v7-migration.md` (each entry: topic id, exact removed text, reason). Second test: `surv-priorities` contains the old Priorities block text and the Forest, Cold-and-snow and Coast picker bullets, minus the frostbite sentence, which is replaced by a `link` block to `p:frostbite`. Third test: the set of `fig` names used equals the old set minus `shelter-desert`.
- [ ] **Step 2:** Run `python3 -m pytest tests/test_survival_migration.py -q`; fails (no files).
- [ ] **Step 3:** Write `tools/convert_survival.py` (HTML → JSON, `python3 tools/convert_survival.py` writes the files) and run it. Apply only the deletions the spec lists in section 5.3 step 1; record each in `docs/v7-migration.md`. Tag `where`/`when` per topic by reading it (untagged when it applies everywhere). Write `keywords` (5 to 10 search words) and a one-sentence `summary` for each, taken from the topic's own wording.
- [ ] **Step 4:** Run the test and `python3 -c "..."` calling `validate_topics` over the files with all fig names and `{'p:frostbite'}`; no errors.
- [ ] **Step 5:** Commit `survival: existing topics as data files (draft)`.

### Task 3: Build pipeline and test harness

**Files:**
- Modify: `build.py`, `tests/conftest.py`
- Test: `tests/test_build.py` (new; runs `build.py` into a temp dir)

**Interfaces:**
- Consumes: Tasks 1 and 2.
- Produces:
  - `window.FK_DATA = { protocols, topics, checklists }`, topics and checklists sorted by id. Every `fig` block gains `figSvg` and `figLabel` from `figs.F`.
  - `link_keys` built in `build.py` as: `p:<id>` for every protocol, `s:<id>` for every topic, `c:<id>` for every checklist, `u:daylight`, `u:sos`, `t:tq`, `t:cpr`, `t:rate`, `t:burn`, `r:9line`, `r:mist`, and `a:` + each of `map`, `position`, `ballistics`, `areas`, `waypoints`, `settings`.
  - `--release` fails listing every draft topic and checklist.
  - `conftest.inject_data(page, protocols=None, topics=None, checklists=None, only=False)`; `inject_protocols` stays and calls it.
- The old `{{fig}}` substitution in `build.py` and the "N diagrams" count in the final print are replaced by a count of `fig` blocks across topics.

- [ ] **Step 1: Failing tests:** a normal build succeeds and its `index.html` contains `"topics":[` and all 15 topic ids; `--release` exits non-zero and names a draft topic; a topic file with invalid JSON exits non-zero naming the file; `</` inside topic text is escaped in the inlined script.
- [ ] **Step 2:** Run `python3 -m pytest tests/test_build.py -q`; fails.
- [ ] **Step 3:** Implement. `src/survival.html` is still the old file at this point, so keep its substitution working until Task 4 replaces the file.
- [ ] **Step 4:** Run the full suite; all pass.
- [ ] **Step 5:** Commit `build: inline topics and checklists`.

### Task 4: Survival data access, routing and topic page

**Files:**
- Modify: `src/survival.html` (becomes: `#survHome` and `#survPage` containers, a live region), `src/survival.js` (rewrite), `src/shell.html` (styles)
- Test: `tests/test_survival_topic.py`

**Interfaces:**
- Consumes: `FK_DATA.topics`, `FK.route` (`go`, `current`), `FK.on('route', fn)`, `FK.esc`, `FK.pins`, `FK.recent`.
- Produces on `FK.survival`:
  - `topics(): Topic[]` (well-formed only: object with string `id`, `title`, array `sections`), `topic(id): Topic | null`
  - `open(key: string, opts?: { replace?: boolean }): boolean` for `s:`, `c:` and `u:` keys (this task handles `s:`; unknown letters return false)
  - `renderHome()` (stub that shows category names; Task 5 completes it)
  - `registerPage(segment: 'list' | 'tool', fn: (id: string, el: HTMLElement) => boolean | (() => void))`: a page provider returns false when `id` is unknown, otherwise draws into `el` and may return a cleanup function called when the page closes. Tasks 8 to 10 use this.
- Topic page content and order: spec section 5.2. Pin star is a button with `data-act="pin"` and `aria-pressed`. Jump list when a topic has four or more sections. Tables sit in a horizontally scrolling box. Diagrams keep the tap-to-enlarge dialog (`#dlgFig`).
- Opening a topic calls `FK.recent.add('s:' + id)`. Focus moves to the topic title (`tabindex="-1"`).

- [ ] **Step 1: Failing tests** (fixture topics injected with `only=True`, one fixture exercising every block type):
  - `#/survival/surv-fix` shows title, Do first items in order, each block type with its text, sources, "Reviewed" date, and "As of" only when present
  - a `draft` fixture shows a Draft tag
  - a `link` block to `p:bleeding` opens the protocol; to `s:` another topic opens it and Back returns to the first topic
  - Back from a topic opened from the home returns to `#/survival`; history length grew by exactly one on open
  - **Review Focus 2:** `#/survival/nope`, `#/survival/list/nope`, `#/survival/tool/nope` each end at `#/survival` showing the home, with `history.length` unchanged from load
  - text containing `<img onerror>` renders as text
  - at 360px wide the page does not scroll sideways with a six-column table fixture (`document.documentElement.scrollWidth <= 360`)
  - the pin star toggles `FK.pins.has('s:surv-fix')`
- [ ] **Step 2:** Run the new file; fails.
- [ ] **Step 3:** Implement. The Survival tab shows either `#survHome` or `#survPage`, decided only from the route, so Back and reload need no extra state.
- [ ] **Step 4:** Run the full suite. Existing tests that relied on `#survTopics details` or `#survSearch` (in `tests/test_search.py` and any Survival test) are updated in Task 7; mark only those `xfail` with reason "Task 7" for now.
- [ ] **Step 5:** Commit `survival: topic pages from data`.

### Task 5: Survival home and filters

**Files:**
- Modify: `src/survival.js`, `src/shell.html`
- Test: `tests/test_survival_home.py`

**Interfaces:**
- Consumes: Task 4.
- Produces: `FK.survival.filter(): { where: string, when: string }`; storage key `survFilter`. Home sections in order: filters, Pinned, Recent (both filled in Task 6), Topics by category, Tools, Checklists (filled by Tasks 8 to 10 through `FK.survival.homeItems(kind: 'tool' | 'list', fn: () => { key, title, badge? }[])`).
- A topic matches a filter when the filter is `any`, or the topic has no tags for that dimension, or its tags include the value. Categories with no topics at all are not shown; `surv-priorities` is listed first in Basics, the rest by title.

- [ ] **Step 1: Failing tests:** categories shown are exactly those with topics, in the shared order; a category opens in place and lists its topics; choosing Town hides a `woods`-only fixture and keeps an untagged one; the choice survives reload; **Review Focus 5:** a category whose topics are all filtered out shows "No topics for this filter", and a stored `survFilter` of `{"where":"moon","when":7}` or `"x"` behaves as Any with no error; filter buttons are `aria-pressed` toggles at least 48px high; opened categories stay open when a filter changes.
- [ ] **Step 2:** Run; fails.
- [ ] **Step 3:** Implement.
- [ ] **Step 4:** Run the full suite.
- [ ] **Step 5:** Commit `survival: home and filters`.

### Task 6: Keys, pins and recents across both homes

**Files:**
- Modify: `src/emergency.js`, `src/survival.js`
- Test: `tests/test_home.py`, `tests/test_survival_home.py`

**Interfaces:**
- Produces:
  - Key pattern becomes `/^[ptsracu]:[\w-]{1,60}$/`.
  - `FK.recent.all(): string[]` returns up to 20, newest first. `FK.recent.add` stores up to 20. `FK.recent.clear()` unchanged.
  - `FK.recent.forSection(section: 'emergency' | 'survival'): string[]` returns the newest 5: for `emergency` of every key kind (today's behaviour), for `survival` of `s:`, `c:`, `u:` keys only. `FK.pins.forSection` likewise (no cap).
  - Emergency home uses `forSection('emergency')`; its button builder (`keyBtns`) renders `c:` and `u:` keys through `FK.search.describe`, as it does `s:` and `a:`.
  - Survival home Pinned and Recent, with the same Clear button markup and behaviour as Emergency (`data-act="clear-recent"`; focus moves to the first filter button).

- [ ] **Step 1: Failing tests:** 12 opens across protocols and topics leave 12 stored, Emergency home shows the newest 5 of any kind, Survival home shows the newest 5 survival ones; Clear on the Survival home empties storage and both homes; a pinned topic appears on both homes, a pinned protocol only on Emergency; **Review Focus 1:** storage seeded with `['s:surv-gone', 'c:nope', 'u:nope', 'z:what', 'p:bleeding']` for both pins and recent renders only what exists, with no console error. Update `test_recent_lists_last_five_newest_first` to expect five shown and six stored.
- [ ] **Step 2:** Run; fails.
- [ ] **Step 3:** Implement.
- [ ] **Step 4:** Run the full suite.
- [ ] **Step 5:** Commit `pins and recents: survival keys, per-section lists`.

### Task 7: Search over the new data

**Files:**
- Modify: `src/search.js`
- Test: `tests/test_search.py`

**Interfaces:**
- Consumes: `FK.survival.topics()`, `FK.survival.open`, and from Tasks 8 to 10 `FK.survival.checklists()` and `FK.survival.tools()` (each may be absent; guard with `?.`).
- Produces: index entries for topics (title weight 5; keywords 4; summary and Do first 3; section headings and all block text 1), checklists (kind `Checklist`: title, item text) and survival tools (kind `Tool`). `describe` and `go` handle `s:`, `c:`, `u:` through the data, not the DOM. `KINDS` gains `'Checklist'`. The empty-query screen's Recent heading gets a Clear button (`data-act="clear-recent"`) that calls `FK.recent.clear()`.

- [ ] **Step 1: Failing tests:** a word found only in a topic's table cell finds the topic with a snippet; a keyword outranks body text; selecting a topic result opens `#/survival/<id>` and Back returns to the screen that was open before search (not to search); search results ignore the home filter; Clear in the search screen empties Recent on both homes. Remove the Task 4 `xfail` marks and rewrite those tests against the new markup.
- [ ] **Step 2:** Run; fails.
- [ ] **Step 3:** Implement.
- [ ] **Step 4:** Run the full suite; no `xfail` left.
- [ ] **Step 5:** Commit `search: topics, checklists and survival tools from data`.

### Task 8: Checklists

**Files:**
- Create: `src/checklists/ten-essentials.json`
- Modify: `src/survival.js`, `src/shell.html`, `src/survival/surv-ten-essentials.json` (add a `link` block to `c:ten-essentials`)
- Test: `tests/test_survival_checklists.py`, `tests/test_migration.py`

**Interfaces:**
- Consumes: `registerPage('list', …)`, `homeItems('list', …)`, `FK.tools.confirm` if it is usable outside the tools overlay, otherwise an in-page two-step button ("Clear ticks" → "Confirm clear", reverting after 5 seconds). Never `window.confirm`.
- Produces: `FK.survival.checklists()`, `FK.survival.checklist(id)`, `FK.survival.ticks(id): string[]`. Page at `#/survival/list/<id>`: title, pin star, items as native checkboxes with labels (whole row tappable, 48px), optional note under an item, "n/m" count, Clear ticks, sources and review date. Home badge "n/m".
- The Ten essentials checklist is draft with the placeholder source until Task 16 checks it with its topic.

- [ ] **Step 1: Failing tests:** ticking two items stores them under `fk.checks` and shows "2/10" on the page and the home after reload; Clear ticks needs the second tap and then empties; ticks for an item id that no longer exists are ignored in the count; the backup file contains `fk.checks` and restore brings ticks back; **Review Focus 4:** restoring a backup with no `fk.checks` and five recents works, and `fk.checks` seeded as `"x"`, `[]` or `{"ten-essentials": "oops"}` gives zero ticks and no error; storage full on tick shows the existing storage-full toast and leaves the box unticked.
- [ ] **Step 2:** Run; fails.
- [ ] **Step 3:** Implement.
- [ ] **Step 4:** Run the full suite.
- [ ] **Step 5:** Commit `survival: checklists`.

### Task 9: SOS light

**Files:**
- Create: `src/survival-tools.js` (add to the script list in `build.py` after `survival.js`)
- Modify: `src/shell.html`
- Test: `tests/test_survival_tools.py`

**Interfaces:**
- Consumes: `registerPage('tool', …)`, `homeItems('tool', …)`.
- Produces: `FK.survival.tools(): { name, label }[]`; tool `sos`, label "SOS light". Page: Start/Stop SOS, Steady light, and the warning "A flashing screen can be seen from far away and gives away your position." While running, a full-screen white panel flashes Morse SOS with unit 200 ms (dot 1 unit, dash 3, gap inside a letter 1, between letters 3, after the group 7), holds a screen wake lock when the browser has one, and stops on tap, on Back, on leaving the page and when the tab is hidden. Under `prefers-reduced-motion` nothing changes (the flashing is the function), but the Start button says so in its description.

- [ ] **Step 1: Failing tests** (Playwright clock installed): the panel's on/off sequence over one full group matches `... --- ...` at 200 ms units; Stop, Back and switching tab each end it and hide the panel; Steady keeps it lit; no wake-lock support causes no error; opening the tool adds `u:sos` to Recent.
- [ ] **Step 2:** Run; fails.
- [ ] **Step 3:** Implement.
- [ ] **Step 4:** Run the full suite.
- [ ] **Step 5:** Commit `survival: SOS light`.

### Task 10: Daylight and moon

**Files:**
- Create: `src/astro.js` (first in the script list, pure functions on `window.FK_ASTRO`, no DOM), `tests/fixtures/almanac-syracuse.json`
- Modify: `src/survival-tools.js`, `build.py`, `docs/content-review.md`
- Test: `tests/test_astro.py`, `tests/test_survival_tools.py`

**Interfaces:**
- Produces:
  - `FK_ASTRO.sun(dayStartMs: number, lat: number, lon: number): { dawn, rise, set, dusk }` where each is epoch ms or `null` (never happens that day); `dawn`/`dusk` are civil twilight (sun 6° below the horizon), rise/set use the standard −0.833°.
  - `FK_ASTRO.moon(dayStartMs, lat, lon): { rise, set, phase, illum, name }` (`phase` 0 to 1 from new moon, `illum` 0 to 1, `name` one of the eight usual phase names).
  - Tool `daylight`, label "Daylight and moon": position line (last GPS fix with its age, or typed latitude/longitude, validated to ±90/±180), then seven day cards (today first) with first light, sunrise, sunset, last light, day length, moonrise, moonset, phase name and percent lit. Times in the phone's local time via `Intl.DateTimeFormat`.
- Read how `src/app.js` stores the last fix (`store.set('lastFix', …)`) and reuse that value; do not start GPS from this tool.

- [ ] **Step 1: Gather the reference values.** Fetch US Naval Observatory data (aa.usno.navy.mil "Complete Sun and Moon Data for One Day" or its API) for Syracuse, NY (43.05 N, 76.15 W) for 2026-03-07, 2026-03-08, 2026-03-09, 2026-03-20, 2026-06-21, 2026-09-22, 2026-10-31, 2026-11-01, 2026-11-02 and 2026-12-21, plus Utqiagvik, AK (71.29 N, 156.79 W) for 2026-06-21 and 2026-12-21. Save as `tests/fixtures/almanac-syracuse.json` and record the source and fetch date in `docs/content-review.md`. If USNO cannot be reached, use NOAA's solar calculator for the sun and timeanddate.com for the moon, and say so in the record. Do not invent values; if no source can be opened, stop and report.
- [ ] **Step 2: Failing tests:** `tests/test_astro.py` loads the page, calls `FK_ASTRO` for each fixture row and asserts sun times within 2 minutes and moon times within 5 minutes; **Review Focus 3:** Utqiagvik in June returns `rise: null, set: null` and the tool shows "Does not set", in December "Does not rise"; the tool with no stored fix shows "No position yet. Get a fix on the Position screen, or type one here." and accepts a typed position; typed `91` latitude is refused with a message; the March and November clock-change days show local times that match the fixture's local times.
- [ ] **Step 3:** Run; fails.
- [ ] **Step 4:** Implement with a published method (NOAA solar equations; Meeus low-precision lunar position with iterative rise/set search). Moonrise or moonset that does not occur on a day shows a dash.
- [ ] **Step 5:** Run the full suite.
- [ ] **Step 6:** Commit `survival: daylight and moon`.

### Task 11: Backlog fix, step timers

**Files:**
- Modify: `src/protocol.js`, `src/emergency.js`
- Test: `tests/test_player.py`

Two defects from the status doc, both in the step-timer code:

- [ ] **Step 1: Failing tests:** (a) with a step timer running in protocol A, opening protocol B, or re-opening A from its home tile, shows the toast "Timer stopped: <protocol title>" once; resuming through Resume shows none. (b) A stored run whose step timer ended while the app was closed: on load there is no `navigator.vibrate` call (spy it) and the Emergency home strip does not show a "Done" timer.
- [ ] **Step 2:** Run; fails.
- [ ] **Step 3:** Implement the smallest change in each place; do not restructure the player's history logic.
- [ ] **Step 4:** Run the full suite.
- [ ] **Step 5:** Commit `player: timer-stopped notice; no stale finished timer at startup`.

### Task 12: Backlog fix, CPR clicks and update banner

**Files:**
- Modify: `src/emergency-tools.js`, `src/app.js`, `src/shell.html`
- Test: `tests/test_tools.py`, `tests/test_search.py`

- [ ] **Step 1: Failing tests:** (a) with the CPR coach running, when the audio context reports `interrupted`/`suspended` and then resumes, no click is scheduled for a time earlier than the resume moment (inspect the scheduled start times through the test hook the tool already exposes, or add `FK.tools.cpr._scheduled()` returning pending start times). (b) With the update banner visible and search open, the banner does not overlap the search input or results (bounding boxes do not intersect).
- [ ] **Step 2:** Run; fails.
- [ ] **Step 3:** Implement: cancel or disconnect queued click sources on interruption and restart the schedule from the resume time; place the banner below the search overlay in stacking order or hide it while search is open.
- [ ] **Step 4:** Run the full suite.
- [ ] **Step 5:** Commit `cpr: drop queued clicks on interruption; banner clear of search`.

### Tasks 13 to 16: Source-check the existing topics

One task per batch. Each batch is written by one worker and then checked by a **different** reviewer who has not seen the worker's reasoning.

| Task | Topics |
|---|---|
| 13 | `surv-find-water`, `surv-make-water-safe`, `surv-priorities` |
| 14 | `surv-shelter`, `surv-fire`, `surv-weather-and-lightning`, `surv-river-crossings` |
| 15 | `surv-food-and-wild-plants`, `surv-traps-and-fishing`, `surv-field-dressing-game`, `surv-dangerous-animals` |
| 16 | `surv-navigation-without-a-compass`, `surv-signal-for-rescue`, `surv-knots`, `surv-ten-essentials` and the `ten-essentials` checklist |

**Files (each batch):** the batch's `src/survival/*.json`, `docs/content-review.md`, `docs/v7-migration.md`.

**Preferred sources:** spec section 6.2. Blocked from this environment: ahajournals.org, guidelines.redcross.org. Two-column PDFs extract out of order; check step order by hand.

- [ ] **Step 1: Trace.** For every number, time, distance, temperature, dose, and every instruction that could hurt someone if wrong, open a source and compare. Record in `docs/content-review.md`: topic id, the statement, the source name and section, and the outcome (matches, corrected, removed, or open question).
- [ ] **Step 2: Correct.** Where the source disagrees, change the text to match the source and list the change (old text, new text, source) under "Corrections" in `docs/v7-migration.md`. Where no opened source supports a statement, remove it and list it. Where the Northeast needs a different statement (for example bears: black bear only; moose; coastal tides), write it from a source. Do not expand the topic beyond what it covers today.
- [ ] **Step 3: Region and links.** Check `where`/`when` tags against the corrected text. Replace restated treatment with a `link` to the Emergency protocol where one exists (hypothermia, frostbite, heat illness, bites, lightning). Confirm each remaining diagram is still right against the corrected text.
- [ ] **Step 4: Finish the files.** Replace the placeholder source with the real `sources` (`name`, `used`), set `reviewed` to the day of checking, remove `draft`.
- [ ] **Step 5: Verify.** `python3 build.py /tmp/fk-check` builds with no validation error; the full test suite passes. Delete `test_converted_text_equals_old_text_minus_listed_deletions` in the first batch that corrects text and replace it with `test_every_topic_has_real_sources` (no topic's sources mention "Not yet source-checked" unless it is still `draft`).
- [ ] **Step 6: Independent review.** A fresh reviewer gets the batch's files, `docs/content-review.md` and the sources list, and looks for: a number that does not match its source, a step that contradicts another topic or an Emergency protocol, a link into the wrong place, advice wrong for its tags or for the Northeast, anything that breaks a Global Constraint (plants, knots, weapons). Fix what it finds with the smallest change, then have the reviewer re-check the fixes.
- [ ] **Step 7:** Commit `content: <batch> source-checked`.

Open questions that only Jordan or a medical professional can settle go into `docs/decisions-for-jordan.md`; they do not block the task unless the statement in question is still in the app, in which case the statement is removed until answered.

### Task 17: Release v7

**Files:** `src/app.js`, `src/sw.js`, root build output, `README.md` if it describes Survival, the project status doc.

- [ ] **Step 1:** Set `APP_VERSION = '7'` and `VERSION = 'fieldkit-v7'`.
- [ ] **Step 2:** `python3 build.py --release .` succeeds (no draft topic, checklist or protocol).
- [ ] **Step 3:** `python3 -m unittest tests.test_validate && python3 -m pytest tests -q`; all pass.
- [ ] **Step 4:** Look at the built app at 360×640 in both day and night mode: Survival home, one long topic, a table, the checklist, both tools, search for a topic, Back from each. Screenshots go to Jordan with the release note.
- [ ] **Step 5:** Whole-branch review by a fresh reviewer against the spec and this plan's Review Focus; fix and re-review.
- [ ] **Step 6:** Commit `v7: Survival knowledge center framework`, push `v7-survival:main`.
- [ ] **Step 7:** Update `claude/FIELD-KIT-STATUS.md` in the project (current version, changelog, backlog, what Jordan should check on the phone).
