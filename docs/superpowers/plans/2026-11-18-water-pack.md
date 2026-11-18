# Water and Sanitation Pack (v7.2) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship the first Survival content pack: thirteen source-checked water and sanitation topics, two scaling checklists, a water planner backed by sourced data, five diagrams, released as v7.2.

**Architecture:** Content is JSON under `src/survival/` and `src/checklists/`, exactly as in v7. Two small framework additions: a saved group setting (`people`, `days`) that checklists and the planner read, and a `src/tooldata/` directory of sourced, validated, release-gated numbers for tools. The water planner is one more entry in the Survival tool registry.

**Tech Stack:** Vanilla JS on `window.FK`, Python build and validator, `unittest` + pytest/Playwright at 360×640.

**Spec:** `docs/superpowers/specs/2026-11-18-water-pack-content-plan.md`, under `docs/superpowers/specs/2026-11-17-v7-survival-knowledge-center-design.md` (sections 5 and 6 bind). Read both.

## Global Constraints

- Edit `src/`, `figs/`, `tools/`, `tests/`, `docs/`, `build.py` only. Root `index.html`, `sw.js`, `manifest.json`, `leaflet.*` are build output; only Task 11 rebuilds them.
- The repository is public: never write the group's home town into tracked files; say "Central New York".
- Every number, time, distance, dose and procedure in content comes from a source that was actually opened and is recorded in `docs/content-review.md`. No Firecrawl; built-in search, then fetch pages the search returned; never a constructed URL. After each fetch confirm the page is the one asked for.
- Water decisions already made (v7): boil 1 minute, 3 minutes above 5,000 ft; 8 drops of 5% to 9% unscented bleach per gallon (2 per quart or litre), double for cloudy, coloured or very cold water, wait 30 minutes; bleach and iodine do not work well against parasites; chlorine dioxide "works better, but not fully" against Cryptosporidium; boiling and disinfecting do not fix fuel, chemicals or harmful algal blooms. New text must agree with these or log a question in `docs/decisions-for-jordan.md` section D (next free number).
- Medical treatment is linked, not restated (`p:vomiting-diarrhea`, `p:dehydration`, `p:hypothermia`, `p:poisoning`, `p:carbon-monoxide`).
- No 911 or dial control. No drawings of edible plants. No instructions aimed at harming people.
- US units first, metric in brackets. Plain, direct voice; imperative steps.
- State rules (burning, septic, waste) are stated as applying in normal times, with New York's named.
- Safety-critical topics stay visible under every filter value.
- Stored values that are unknown or malformed are ignored, never rendered; every string reaching markup goes through `FK.esc`. 48 px touch targets in Survival. Night mode on every new screen.
- Content workers stage only their own files by name; never `git add -A`; no stash, reset, rebase or amend.
- Tests: `python3 -m unittest tests.test_validate && python3 -m pytest tests -q`; any console error fails. Commit after every task with the session's attribution trailer. Branch `water-pack`. No push to `main` before Task 11.

## Review Focus

1. A stored `group` that is malformed or absurd (`"x"`, `{people: 0}`, `{people: 1e9, days: -3}`, floats): the planner and scaling checklists fall back to 1 person and the default days, clamp to 1–50 people and 1–365 days, and never show `NaN`, `Infinity` or a negative total. Task 2.
2. Rounding that understates a need: totals of water, bleach and containers always round up (never down) and show the unit; a planner total is never less than people × days × the per-person figure. Task 2.
3. A checklist item quantity for a group of 1 and of 50 over 1 and 365 days: totals stay readable (thousands separators, sensible unit), the page does not overflow at 360 px, and ticks are unaffected by a group change. Task 2.
4. A v7 backup (no `group`, no new checklists) restored on v7.2, and a v7.2 backup with `group` restored: both work; old pins and recents for `surv-find-water` and `surv-make-water-safe` still open after those topics change category. Task 2.
5. The When filter appears for the first time in this pack (a topic has `when: cold`): under When = Warm the winter topic is hidden but no safety-critical topic is; under every Where and When value the protected topics are listed. Task 10.

---

## File map

| File | Responsibility |
|---|---|
| `tools/validate.py` | `validate_tooldata`; checklist item quantities; `TOOL_NAMES` |
| `build.py` | loads `src/tooldata/*.json` → `FK_DATA.tooldata`; link keys from `TOOL_NAMES`; release gate covers tool data |
| `src/tooldata/water.json` | every number the water planner uses, with sources |
| `src/survival.js` | group setting (`FK.survival.group`, `setGroup`), checklist quantities |
| `src/survival-tools.js` | water planner tool |
| `src/survival/surv-*.json` | 11 new topics, 2 deepened |
| `src/checklists/home-water-store.json`, `sanitation-kit.json` | new checklists |
| `figs/figs.py` | five figures |
| `docs/content-review.md`, `docs/decisions-for-jordan.md` | records |

Shared names:

- Group: storage key `group` = `{ people: int 1–50, days: int 1–365 }`; defaults `{ people: 1, days: 14 }` unless Task 3's sources give a different planning period, in which case the default days come from `FK_DATA.tooldata.water`.
- `FK.survival.group(): { people, days }` (always valid); `FK.survival.setGroup({ people, days }): boolean` (false when storage is full); event `group` emitted on change.
- Checklist item quantity: optional `qty: { amount: number > 0, unit: string, per: 'person' | 'personDay' }`.
- Tool data file: `{ id, title, values: { <name>: { value: number, unit: string, note?: string } }, sources: [{ name, used }], reviewed, draft? }`.
- Tool name `water`, key `u:water`, address `#/survival/tool/water`.

---

### Task 1: Validator and build for tool data and quantities

**Files:** Modify `tools/validate.py`, `build.py`, `tests/conftest.py`. Test: `tests/test_validate.py`, `tests/test_build.py`.

**Interfaces:**
- Produces: `validate_tooldata(items: list) -> (errors, warnings)`; `TOOL_NAMES = ('daylight', 'sos', 'water')` in `tools/validate.py`, used by `build.py` for `u:` link keys (replacing the hard-coded set); checklist `ITEM_KEYS` gains `qty`; `FK_DATA.tooldata` = object keyed by id; `--release` fails on draft tool data; `conftest.inject_data(..., tooldata=None)`.

- [ ] **Step 1: Failing tests.** `validate_tooldata`: a valid fixture passes; errors (naming id and reason) for unknown keys, bad id (`[a-z][a-z0-9-]{0,39}`), duplicate id, empty `values`, a value that is not a finite number, missing unit, missing sources or `reviewed`, non-dict input; draft is a warning. Checklist `qty`: valid passes; errors for amount ≤ 0 or non-number, blank unit, `per` outside the two values, unknown key. Build: `FK_DATA.tooldata` is `{}` with no files; a draft tool-data file fails `--release` naming it; a topic linking `u:water` builds and one linking `u:nope` fails.
- [ ] **Step 2:** Run them; they fail.
- [ ] **Step 3:** Implement.
- [ ] **Step 4:** Full suite passes.
- [ ] **Step 5:** Commit `validate and build: tool data, checklist quantities`.

### Task 2: Group setting, scaling checklists, water planner

**Files:** Modify `src/survival.js`, `src/survival-tools.js`, `src/shell.html`. Test: `tests/test_survival_group.py`, `tests/test_survival_tools.py`, `tests/test_migration.py`.

**Interfaces:**
- Consumes: Task 1; `FK_DATA.tooldata.water.values` with these names (Task 3 supplies the real file; tests use a fixture): `drinkPerPersonDay`, `planDays`, and any number of optional extras named `extra<Name>PerPersonDay` (each `{ value, unit: 'gal', note }`), `lbPerGallon`, `litersPerGallon`.
- Produces: `FK.survival.group()`, `FK.survival.setGroup()`, event `group`; a compact group editor (two number fields with labels, steppers at 48 px) used on the planner page and on any checklist that has a `qty` item; checklist rows show the scaled total after the item text; tool `water`, label "Water planner", keywords for search.
- Planner page: group editor; a toggle per optional extra using its `note` as the label; results: gallons and litres, weight in pounds, and container counts for 1-gallon jugs, 5-gallon containers and 55-gallon drums (each rounded up); the per-person figure and its source name shown under the result; a line that says what the total does not cover, taken from the data's `title`/notes, not invented. If `FK_DATA.tooldata.water` is missing or draft the page says the planner's numbers are not available and shows no totals.

- [ ] **Step 1: Failing tests,** including Review Focus 1 to 4 with their exact cases, plus: group persists and both the planner and a fixture checklist update live on the `group` event; storage full keeps the typed group for the page and shows the toast; keyboard-only use; no overflow at 360 px; planner with fixture data computes `people × days × (drink + chosen extras)` and rounds up.
- [ ] **Step 2:** Run; fail.
- [ ] **Step 3:** Implement.
- [ ] **Step 4:** Full suite passes.
- [ ] **Step 5:** Commit `survival: group setting, scaling checklists, water planner`.

### Task 3: Planner numbers (content)

**Files:** Create `src/tooldata/water.json`; modify `docs/content-review.md`.

- [ ] Source and record every value the planner uses: the per-person daily amount and what it covers; the planning period; each extra a source quantifies (do not include an extra no source quantifies; describe it in the note of the base value instead); weight and litres per US gallon. Sources: FEMA/Ready.gov, CDC, Red Cross, USGS or NIST for the physical constants. Independent review as in Tasks 4 to 7. Remove `draft` only after review.

### Tasks 4 to 7: Topic batches

Each batch: one writer, then an independent reviewer who re-opens the sources, then fixes and a scoped re-review. Procedure and report format: the content contract the controller supplies. New topics are written from sources, not from memory; deepened topics keep their checked text unless a source requires a change (recorded in `docs/v7-migration.md`).

| Task | Files |
|---|---|
| 4 | `surv-water-how-much`, `surv-water-store`, `surv-water-in-the-house`, checklist `home-water-store` |
| 5 | `surv-find-water` (deepen, move to `water`), `surv-make-water-safe` (deepen, move), `surv-water-winter`, `surv-wells-without-power` |
| 6 | `surv-toilet-no-water`, `surv-latrines`, `surv-garbage-and-greywater`, checklist `sanitation-kit` |
| 7 | `surv-handwashing`, `surv-clean-and-disinfect`, `surv-stomach-illness-in-a-group` |

Each batch ends with: build exits 0; full suite passes; `draft` removed only after its review is approved (the writer leaves `draft: true`; the fix round removes it).

### Task 8: Diagrams

**Files:** `figs/figs.py`, the topics that take a figure, `tests/test_figs.py`, `docs/content-review.md`.

- [ ] Draw, from the checked text only: `toilet-buckets`, `handwash-station`, `latrine`, `water-heater-drain`, and `water-safe` relabelled to 5,000 ft. Tests assert label wording against the topics' key words and forbid wording the text does not carry. Render each at 360 px, day and night, and view them. A reviewer compares every label and caption with the topic and judges recognisability without the caption; a figure that fails is not shipped.

### Task 9: Cross-pack consistency review

- [ ] One reviewer reads all thirteen topics, both checklists, the planner data and the four related Emergency protocols together, looking only for contradictions between them (amounts, dilutions, distances, times), links into the wrong place, duplicated advice that will drift, and anything hidden by a filter. Fixes go to one worker; one re-review.

### Task 10: Filters and protected topics

**Files:** `tests/test_survival_home.py`, tags in topics if needed.

- [ ] Extend the v7 shipped-data test (Review Focus 5): protected topics now include `surv-make-water-safe`, `surv-find-water`, `surv-toilet-no-water`, `surv-handwashing`, `surv-water-how-much`; the When row appears; `surv-water-winter` is hidden under Warm and shown under Cold and Any.

### Task 11: Whole-branch review and release v7.2

- [ ] Whole-branch review on the most capable model, one fix wave, one re-review.
- [ ] `APP_VERSION = '7.2'`, `VERSION = 'fieldkit-v7.2'`; `python3 build.py --release .`; full suite; phone-size look in day and night; squash onto `main`; push; update the project status doc.
