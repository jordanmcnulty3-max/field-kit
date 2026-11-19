# Food at Home Pack (v7.5) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship the fourth Survival content pack: ten source-checked food-at-home topics, a Pantry checklist, up to three diagrams, and a food planner and a botulism protocol only if their gates pass, released as v7.5.

**Architecture:** Content is JSON under `src/survival/`, `src/protocols/`, `src/checklists/` and `src/tooldata/`, exactly as in v7.4. The `food` category already exists in `src/survival.js` and `tools/validate.py`. Code changes: the search index learns an ordered list of packs so each pack's pages index after everything older (Task 8); a planner tool only if Task 1's gate passes (Tasks 2 and 3).

**Tech Stack:** Vanilla JS on `window.FK`, Python build and validator, `unittest` + pytest/Playwright at 360×640.

**Spec:** `docs/superpowers/specs/2026-11-19-food-at-home-pack-content-plan.md`, under `docs/superpowers/specs/2026-11-17-v7-survival-knowledge-center-design.md` (sections 5 and 6 bind). Read both. "spec 7" below means the food spec.

## Global Constraints

- Edit `src/`, `figs/`, `tools/`, `tests/`, `docs/`, `build.py` only. Root `index.html`, `sw.js`, `manifest.json`, `leaflet.*` are build output; only Task 9 rebuilds them. To build while working: `python3 build.py /tmp/out`.
- The repository is public: never write the group's home town into tracked files; say "Central New York".
- Every number, time, temperature, shelf life, amount and procedure comes from a source that was actually opened and is recorded in `docs/content-review.md`. No Firecrawl or Bright Data; built-in search, then fetch pages the search returned; never a constructed URL. After each fetch confirm the page is the one asked for. Nothing is written from memory when a page fails.
- Source order: current federal sources (USDA FSIS, FoodSafety.gov, CDC, FDA, Ready.gov/FEMA), New York State, then state extension services (Cornell first) and the National Center for Home Food Preservation. US Army manuals only for points civilian sources do not cover, named with their year. Where sources disagree the more cautious one is used and the question is logged.
- No canning procedure of any kind (spec 10, call 3). No preserving method beyond what an official source teaches a beginner (call 4). No calorie, weight or infant feeding amount the app derives itself (call 9).
- No sentence may let someone eat food a source says to throw out, or present smell, look or taste as a test.
- Flame indoors (spec 7): `surv-carbon-monoxide`, `surv-portable-heaters`, `surv-wood-stoves-fireplaces`, `surv-generators`, `surv-fire`, `surv-heat-out` are checked and are not reworded. No sentence may be readable as permitting a camp stove, grill, charcoal or generator indoors. Cooking on a gas or propane kitchen range, or on a vented wood stove or fireplace, may be allowed only where an opened source says so in words, with every condition the source gives, beside the two checked prohibitions quoted word for word ("Never heat the house with a gas oven or range"; CDC's line on a stove or fireplace that isn't vented, as it stands in the checked topic). If no source says it, flame cooking is outdoors and food is otherwise eaten cold, labelled as the app's own caution. The fallout sheltering rule is `surv-fallout-shelter-living`'s and is linked, not restated.
- Other checked content binds new text and is not reworded: the water pack topics (`surv-make-water-safe`, `surv-water-store`, `surv-water-in-the-house`, `surv-water-how-much`, `surv-clean-and-disinfect`, `surv-handwashing`, `surv-stomach-illness-in-a-group`, `surv-garbage-and-greywater`), `surv-fallout-water-and-food`, `surv-fallout-get-ready`, `surv-field-dressing-game` (165°F for all wild game), `surv-food-and-wild-plants`, `surv-traps-and-fishing`, `surv-priorities`, and every existing Emergency protocol (`vomiting-diarrhea`, `dehydration`, `poisoning`, the choking protocols, `low-blood-sugar`, `burns` are the likely contacts). A conflict is logged in `docs/decisions-for-jordan.md` section D, never resolved by editing checked text.
- One rule, one owner (spec 7): fridge and freezer hold times `surv-food-power-out`; what to throw out `surv-food-still-good`; cooking temperatures and indoor cooking `surv-food-cooking-no-power`; storage and shelf life `surv-food-storage`; amounts to store `surv-food-how-much`; infant and child feeding `surv-food-babies-children`; botulism signs `surv-food-poisoning`. Others quote word for word or link. Water amounts, boiling times and bleach mixes belong to the water pack: link, never restate.
- Medical care is linked, not restated in Survival. Every medical judgement the sources leave open is logged in section D marked "Medical professional".
- A sentence with no source is left out, or labelled in the user-visible text as the app's own caution or reading AND logged in section D.
- No 911 or dial control. No internal wording in user-visible text (question numbers, "Task", "batch", "ruling"), including source lines. US units first, metric in brackets. Plain, direct voice; imperative steps. New York named where state rules apply, as applying in normal times.
- No food topic in this pack carries a `where` or `when` tag. Topic tables fit 360 px or scroll with the "Swipe sideways" cue.
- Stored or typed values that are unknown or malformed are ignored, never rendered; every string reaching markup goes through `FK.esc`. 48 px touch targets. Night mode on every new screen.
- Search: a new page must not push an older result out of the first three on screen. New keywords stay narrow; no keyword that is an everyday or medical word on its own ("water", "burn", "sick", "bleeding", "fire", "salt", "ice") unless the page is the best answer for it.
- Content workers stage only their own files by name; never `git add -A`; no stash, reset, rebase or amend.
- Tests: `python3 -m unittest tests.test_validate && python3 -m pytest tests -q`; any console error fails. Commit after every task with the session's attribution trailer. Branch `food-pack`. No push to `main` before Task 9.
- Question numbers in `docs/decisions-for-jordan.md` section D: Task 1 uses 117 to 129, Task 4 uses 130 to 139, Task 5 uses 140 to 149, Task 6 uses 150 to 155, Tasks 7 to 9 use 156 onward. Gaps are expected. The first question of the pack (117) is indoor cooking on a range or vented stove, whatever the sources say.
- Decisions made without asking go in `docs/v7.5-rulings.md` (create in Task 1), each with its cost if wrong, plus a Deferred list that starts with: Food from the land (v7.6); canning procedures; gardening, livestock and root cellars.

## Review Focus

1. Planner inputs (if it ships): the group setting blank, non-numeric, negative, zero, decimal or huge: a plain message, never `NaN` or `Infinity`; amounts always round up; missing or damaged `tooldata/food.json` shows "numbers not available", never a figure. Task 3.
2. Pantry checklist: quantities for 1 person and for many read naturally; the Days field shows only if an item is per day; ticks and the group setting survive a reload and a v7.4-shaped backup restore. Task 4.
3. Filters and home: all ten food topics listed under all 15 Where × When combinations; `surv-food-power-out` leads the Food category; header and rows do not overflow at 360 px and are at least 48 px high, day and night. Task 8.
4. Search: for the 29 queries pinned in `tests/test_search.py` and for "food", "water", "cook", "fire", "stove", "burn", "sick", "vomiting", "baby", "choking", "milk", "can", "salt", "ice", "freezer", "power", "generator", the on-screen first three equal v7.4's unless a food page is plainly the best answer and the controller has ruled so; "food", "freezer", "pantry", "spoiled", "botulism", "formula", "canning", "power out" each show a food page in the first three; the two first-search speed tests pass ten times alone on an idle machine. Task 8.
5. Links and labels: every `p:`, `s:`, `u:`, `c:` link in the new content resolves and its label equals the target title; the hub links every other food topic and the checklist; an enlarged diagram opens at its top; a v7.4-shaped backup restores. Task 8.

---

## File map

| File | Responsibility |
|---|---|
| `src/survival/surv-food-*.json` | ten new topics |
| `src/checklists/pantry.json` | new checklist |
| `src/protocols/botulism.json` | conditional: new protocol |
| `tools/validate.py`, `src/survival-tools.js`, `src/tooldata/food.json` | conditional: tool name `food`, planner, its numbers |
| `src/search.js` | ordered packs in the index |
| `src/survival.js` | hub lead for `food` |
| `figs/figs.py` | up to three figures |
| `tests/…` | shipped-data, search, tool and figure tests |
| `docs/content-review.md`, `docs/decisions-for-jordan.md`, `docs/v7.5-rulings.md` | records |

Shared names:

- Topic ids: `surv-food-power-out` (hub), `surv-food-still-good`, `surv-food-cooking-no-power`, `surv-food-poisoning`, `surv-food-how-much`, `surv-food-storage`, `surv-food-when-short`, `surv-food-clean-kitchen`, `surv-food-babies-children`, `surv-food-preserving`. Category `food`.
- Checklist id `pantry`. Protocol id (conditional) `botulism`.
- Tool (conditional): name `food`, key `u:food`, address `#/survival/tool/food`, label "Food planner". It reads and writes the existing group setting exactly as the Water planner does.

---

### Task 1: Batch A, the food-safety core, and the two gates

**Files:** Create `src/survival/surv-food-power-out.json`, `surv-food-still-good.json`, `surv-food-cooking-no-power.json`, `surv-food-poisoning.json`, `docs/v7.5-rulings.md`. Modify `docs/content-review.md`, `docs/decisions-for-jordan.md`.

**Interfaces:**
- Produces: the four topics, checked and out of draft; in `docs/v7.5-rulings.md` three sections later tasks read: **"Tool gate"** (`PASS` with the source, its exact wording and every per-person figure it gives, or `FAIL` with what was looked for), **"Botulism protocol gate"** (`PASS` with the sources and the lay actions they give, or `FAIL`), and **"Indoor cooking"** (what each opened source says about a gas or propane range in a power cut and about cooking on a wood stove or fireplace, verbatim, and what the topic therefore says).

- [ ] Writer, independent reviewer, fix round and re-check per the Content contract. Coverage: spec section 4 rows; spec 7 in full.
- [ ] `surv-food-cooking-no-power` carries the cooking-temperature table (must not contradict 165°F for wild game in `surv-field-dressing-game`) and the indoor-cooking rule as Global Constraints give it; question 117 is logged whatever the outcome.
- [ ] Tool gate: PASS only if a current federal source or a state extension service states per-person amounts as text or a table and the reviewer confirms it by re-opening the source.
- [ ] Botulism gate: PASS only if CDC or another opened medical source gives recognition signs AND actions a lay person can take when no hospital is reachable; "get medical care immediately" alone is FAIL.
- [ ] Build exits 0; full suite passes; `draft` removed only after the review is approved; commit `food: safety core topics (batch A)`.

Tasks 2 to 6 start only after Task 1 is approved; every later writer reads the four finished topics. Tasks 4, 5 and 6 may run in parallel in separate git worktrees and are merged in that order.

### Task 2 (only if the tool gate is PASS): Validator accepts the food planner

**Files:** Modify `tools/validate.py`. Test: `tests/test_validate.py`, `tests/test_build.py`.

- [ ] **Step 1: Failing tests.** `TOOL_NAMES` contains `'food'`; a topic linking `u:food` builds; tool data `food` with the existing `values` shape validates; the existing rejections still hold.
- [ ] **Step 2:** Run; fail. **Step 3:** Implement. **Step 4:** Full suite passes. **Step 5:** Commit `validate: food planner tool name`.

### Task 3 (only if the tool gate is PASS): Food planner and its numbers

**Files:** Modify `src/survival-tools.js`; create `src/tooldata/food.json`; modify `docs/content-review.md`. Test: `tests/test_survival_tools.py`.

**Interfaces:**
- Consumes: Task 2; the figures recorded under "Tool gate"; the group setting and the Water planner's group fields (`TOOLS.water`, `mountGroup`).
- Produces: `TOOLS.food = { label: 'Food planner', keywords, draw }`: the "Your group" box (People and Days, the shared setting), a result block listing each of the source's own categories with its amount for the group, each rounded up, the source named under the result, and links to `s:surv-food-how-much` and `c:pantry`, each rendered only if its key resolves.
- Exact copy. Under any result: "These are planning figures from the source named below, not a diet. Children, pregnant and nursing women, sick people and people doing hard work have different needs." Missing data: "The food planner’s numbers are not available yet. Nothing is shown until they have been checked against sources."

- [ ] **Step 1: Failing tests,** including Review Focus 1 with its exact cases, plus: every fixture category scales linearly with people × days and rounds up; changing the group in the planner changes the Water planner and the checklists; keyboard-only use; no overflow at 360 px; night mode; the tool is on the Survival home and in search for "food planner".
- [ ] **Step 2:** Run; fail. **Step 3:** Implement, reusing the Water planner's structure.
- [ ] **Step 4:** Write `src/tooldata/food.json` from the gate's figures with `draft: true`. An independent reviewer re-opens the source and checks every figure, then `draft` is removed.
- [ ] **Step 5:** Full suite passes. Commit `survival: food planner`.

If the gate is FAIL, skip Tasks 2 and 3 and record under Deferred: "No food planner: no source states per-person amounts."

### Task 4: Batch B and the checklist

**Files:** Create `src/survival/surv-food-how-much.json`, `surv-food-storage.json`, `surv-food-when-short.json`, `src/checklists/pantry.json`; records.

- [ ] Content contract. Coverage: spec section 4 rows and section 8. Checklist items carry no links; pattern `src/checklists/home-water-store.json`; per-person and per-person-per-day quantities only where a source gives the figure.
- [ ] `surv-food-when-short` gives no instruction to restrict a child, a pregnant or nursing woman or a sick person unless a source says so in words.
- [ ] Build, suite, commit `food: how much, storage, when short, pantry checklist (batch B)`.

### Task 5: Batch C

**Files:** Create `src/survival/surv-food-clean-kitchen.json`, `surv-food-babies-children.json`, `surv-food-preserving.json`; records.

- [ ] Content contract. Coverage: spec section 4 rows. `surv-food-babies-children` must agree with `surv-fallout-water-and-food` "Babies" and the water pack on water for formula, and logs every open medical point for a medical professional. `surv-food-preserving` follows spec 10 calls 3 and 4 exactly.
- [ ] Build, suite, commit `food: clean kitchen, babies and children, preserving (batch C)`.

### Task 6 (only if the botulism gate is PASS): Botulism protocol

**Files:** Create `src/protocols/botulism.json`; records; shipped-data protocol tests.

- [ ] Content contract, with `src/protocols/radiation-sickness.json` as the pattern and the Emergency rules in `docs/superpowers/specs/2026-11-16-emergency-survival-overhaul-design.md`. Linked protocols are named by exact title and not edited. Keywords narrow (no "weak", "vision" or other symptom word that leads another protocol's results).
- [ ] After it merges, `surv-food-poisoning` is aligned with it (same signs, same order, steps by pointer) and the reviewer checks the pair.
- [ ] Build, suite, commit `emergency: botulism protocol`.

If the gate is FAIL, skip and record under Deferred with the reason.

### Task 7: Diagrams

**Files:** `figs/figs.py`, the topics that take a figure, `tests/test_figs.py`, `docs/content-review.md`.

- [ ] Draw, from the checked text only, whichever the text supports: `food-fridge-freezer` (a power cut: doors shut, the hold times, thermometer), `food-cans-to-discard` (only if a source describes the signs precisely enough to draw), `food-drying` (only if the preserving topic teaches a method). Every drawn string is found in its topic; no number the topic lacks. Tests as in v7.4: every drawn string in the topic's text; forbidden wording absent. Render at 360 px, day and night, and view them. A reviewer looks at each image before any text; a figure that fails is fixed or not shipped.
- [ ] Commit `figs: food pack diagrams`.

### Task 8: Home, filters, links, and search against v7.4

**Files:** `src/search.js`, `src/survival.js`, `tests/test_survival_home.py`, `tests/test_search.py`, `tests/test_migration.py`; one link block each in `surv-priorities`, `surv-stomach-illness-in-a-group`, `surv-generators`, `surv-fallout-water-and-food`, `surv-fallout-get-ready`, `surv-water-store`, `surv-heat-out` (spec 4, "Existing topics"), plus the cross-links earlier writers listed in `docs/v7.5-rulings.md`.

**Interfaces:**
- Consumes: all topic ids, the checklist id, the protocol id and tool key if they exist.
- Produces: in `src/search.js` `build()`, an ordered list of packs replacing the single radiation special case: every pre-v7.4 document in v7.3 order; then the radiation pack exactly as today (its protocols, its hub, its other topics, its checklist); then the food pack (its protocol if any, its hub `s:surv-food-power-out`, its other topics, `c:pantry`, `u:food` if any). No weight, scoring or tokenisation change.

- [ ] **Step 1: Record the v7.4 baseline.** From a temporary worktree at `origin/main`, build and record the on-screen first three for every query in Review Focus 4; remove the worktree. Pin them in `tests/test_search.py` beside the v7.3 lists.
- [ ] **Step 2: Failing tests** for Review Focus 3, 4 and 5 with their exact cases: `ALWAYS` gains the ten `s:` keys by name; no `where`/`when` on any `food`-category topic created in this pack; the hub first under "Food"; every existing pinned v7.3 test still passes; the seven existing checked topics equal `origin/main` (commit `4375170`; `pytest.skip` with a reason if absent) plus exactly one link block each.
- [ ] **Step 3:** Run; fail. **Step 4:** Implement. Fix displaced results by index order and by narrowing the new content's `keywords` only. Run `tools/search_compare.py` between the v7.4 build and this build over the union of its generated queries and every word and 3- to 5-letter prefix of the new pages' titles and keywords; list every query whose v7.4 first on-screen result is no longer first, split into "tie" (must be zero) and "outscored" (listed for a ruling). If a pinned query cannot keep its first three without a scoring change, stop and report both lists.
- [ ] **Step 5:** The two speed tests alone ten times on an idle machine; full suite. Commit `survival: food category home, protected topics, links, search order`.

### Task 9: Whole-pack read, whole-branch review, release v7.5

- [ ] One reviewer reads all ten topics, the checklist, the protocol and tool data if any, and the binding topics and protocols together, looking for: contradictions (times, temperatures, "never" lists, order of steps); any sentence readable as permitting flame indoors beyond what the cooking topic's sourced rule allows, or as eating food a source says to throw out; a rule stated by a page that does not own it and has drifted; summary or Do first that disagrees with its body; missing links at a moment of decision; an unsourced amount; internal wording; the home town. Fixes go to one worker; one re-check.
- [ ] Whole-branch review on the most capable model, building the app and the v7.4 release and driving both at 360×640 in day and night, including walk-throughs as (a) a household on day 2 of a winter power cut with a full chest freezer and no generator, (b) a parent of a one-year-old with a week of food, (c) someone handed home-canned food by a neighbour; one fix wave; one re-check.
- [ ] `APP_VERSION = '7.5'`, `VERSION = 'fieldkit-v7.5'`; `python3 build.py --release .`; full suite; squash onto `main` as one commit (`git commit-tree HEAD^{tree} -p origin/main`); push the working branch and the squashed commit to `main`; update the project doc `claude/FIELD-KIT-STATUS.md` (including that Jordan said on 2026-11-19 the v7.4 phone check was complete). If the push is refused, stop and tell Jordan.

---

## Content contract (Tasks 1, 3 to 6)

**Writer.**
1. Read the spec rows for the batch, the Global Constraints, the finished batch A topics (after Task 1), an existing topic of the same kind (`src/survival/surv-carbon-monoxide.json`) and the tail of `docs/content-review.md` for the record format.
2. Search, then fetch pages the search returned. Use only what a fetched page says. Confirm each page is the one asked for.
3. Write each item to its schema with `draft: true`, a `doFirst` box where the topic is urgent, `sources` naming every source used (older publications with their year), `reviewed` set to today, and keywords people would actually type.
4. Record in `docs/content-review.md`, per item: every number, table cell, "never" and step order, with the source name, URL and the section or sentence it came from; what was looked for and not found; conflicts between sources and which was used.
5. Log each question that is Jordan's in `docs/decisions-for-jordan.md` section D, in the task's reserved range, with what the app says today.
6. Run `python3 build.py /tmp/out` and the full suite; commit only the batch's files.
7. Report: files, sources opened, pages that failed to load, conflicts, D numbers used, anything left out and why.

**Reviewer** (did not write the batch). Re-open every source in the record. For each item compare every number, table cell, "never" and step order with the source; check agreement with the binding topics and protocols; check the owner rule (Global Constraints); check every link key; check there is no tag; check tables at 360 px in the built app. Report findings as Critical (unsafe or contradicts a source), Important (wrong, misleading or hidden), Minor. Do not edit.

**Fix round.** The writer fixes every Critical and Important finding or records in `docs/v7.5-rulings.md` why not, removes `draft`, rebuilds, runs the suite, commits. The same reviewer re-checks only the fixes.
