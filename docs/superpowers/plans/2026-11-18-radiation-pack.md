# Radiation and Fallout Pack (v7.4) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship the third Survival content pack: ten source-checked radiation and fallout topics, two new Emergency protocols (decontamination, radiation sickness), one checklist, up to three diagrams, and a shelter-time tool only if its rule is confirmed from a source, released as v7.4.

**Architecture:** Content is JSON under `src/survival/`, `src/protocols/` and `src/checklists/`, exactly as in v7.3. The `radiation` category already exists in `src/survival.js` and `tools/validate.py`. The only possible framework addition is conditional: tool data may carry a validated `table`, used by a new Survival tool `fallout` (Tasks 2 and 3, which run only if Task 1's gate passes).

**Tech Stack:** Vanilla JS on `window.FK`, Python build and validator, `unittest` + pytest/Playwright at 360×640.

**Spec:** `docs/superpowers/specs/2026-11-18-radiation-pack-content-plan.md`, under `docs/superpowers/specs/2026-11-17-v7-survival-knowledge-center-design.md` (sections 5 and 6 bind). Read both. Section numbers below ("spec 7") refer to the radiation spec.

## Global Constraints

- Edit `src/`, `figs/`, `tools/`, `tests/`, `docs/`, `build.py` only. Root `index.html`, `sw.js`, `manifest.json`, `leaflet.*` are build output; only Task 9 rebuilds them. To build while working: `python3 build.py /tmp/out`.
- The repository is public: never write the group's home town, or its distance from any target or plant, into tracked files; say "Central New York".
- Every number, time, distance, dose and procedure comes from a source that was actually opened and is recorded in `docs/content-review.md`. No Firecrawl; built-in search, then fetch pages the search returned; never a constructed URL. After each fetch confirm the page is the one asked for. Nothing is written from memory when a page fails. If Ready.gov will not load: spec 10, call 13.
- Source order: current federal and New York sources first. Older civil defence publications fill only what current guidance leaves open (above all how long to stay in when no instruction comes); they are named with their year in the topic text and the source line, marked as dated, never override a current source, and where two disagree the longer stay is used (spec 1 and 9).
- Never the word "safe" for going outside on a time rule alone. No dose, exposure limit or potassium iodide dose anywhere (spec 2; spec 10, calls 3 and 12).
- Existing checked text binds new text and is not reworded: `surv-carbon-monoxide`, `surv-portable-heaters`, `surv-wood-stoves-fireplaces`, `surv-generators`, `surv-heat-out`, `surv-water-store`, `surv-water-in-the-house`, `surv-make-water-safe`, `surv-priorities`, `surv-shelter`, and every existing Emergency protocol (`burns`, `vomiting-diarrhea`, `wound-care`, `dehydration`, `shock` are the likely contacts). A conflict is logged in `docs/decisions-for-jordan.md` section D, never resolved by editing checked text.
- Winter heat in a closed-up house (Jordan, spec 1 and 7): no-flame warmth first for the sheltering period; if the cold itself becomes a danger to life, the stove or heater runs under the checked carbon monoxide rules in full, accepting outside air. No sentence may be readable as permitting anything to burn in a sealed room.
- One rule, one owner (spec 7): sheltering period `surv-fallout-how-long`; where to shelter `surv-fallout-where-to-shelter`; cleaning-off steps `p:radiation-decontamination`; closed-house air `surv-fallout-shelter-living`; leaving shelter, including for a medical emergency, `surv-fallout-leaving`. Others quote word for word or link.
- Medical care is linked, not restated in Survival. The two new protocols follow the Emergency content rules; every judgement the sources leave open is logged in section D marked "medical professional".
- No 911 or dial control. Nothing about constructing or sourcing any device; the dirty bomb topic covers effects and response only. No internal wording in user-visible text (question numbers, "Task", "batch"), including source lines.
- US units first, metric in brackets. Plain, direct voice; imperative steps. State rules as applying in normal times, with New York named.
- No radiation topic carries a `where` or `when` tag. Topic tables fit 360 px or scroll with the "Swipe sideways" cue.
- Stored or typed values that are unknown or malformed are ignored, never rendered; every string reaching markup goes through `FK.esc`. 48 px touch targets. Night mode on every new screen.
- Content workers stage only their own files by name; never `git add -A`; no stash, reset, rebase or amend.
- Tests: `python3 -m unittest tests.test_validate && python3 -m pytest tests -q`; any console error fails. Commit after every task with the session's attribution trailer. Branch `radiation-pack`. No push to `main` before Task 9.
- Question numbers in `docs/decisions-for-jordan.md` section D: Task 1 uses 68 to 79, Task 4 uses 80 to 89, Task 5 uses 90 to 99, Task 6 uses 100 to 109, Tasks 7 to 9 use 110 onward. Gaps are expected.
- Decisions made without asking go in `docs/v7.4-rulings.md` (create in Task 1), each with its cost if wrong, plus a Deferred list that starts with: nuclear plant accidents; potassium iodide doses; meter guidance; dug or purpose-built shelters.

## Review Focus

1. Shelter-time tool inputs that are blank, non-numeric, negative, zero, decimal or huge (`""`, `"abc"`, `-3`, `0`, `2.5`, `1e9`): a plain message, never `NaN`, `Infinity`, a fraction or the word "safe". Task 3.
2. Hours between table rows, before the first row and past the last: the tool uses the last row at or before the entered hours (never overstates the drop); before the first row it says radiation is at its strongest and shows no figure; past the last row it shows the last row and says the source gives nothing further. Task 3.
3. `FK_DATA.tooldata.fallout` missing, draft or damaged (rows not ascending, divisor below 1, lengths differ): the validator rejects it at build, and at run time the tool says its numbers are not available and shows nothing. Tasks 2 and 3.
4. Filters and home: all ten radiation topics are listed under all 15 Where × When combinations; `surv-fallout-warning` leads the category; the category header and ten rows do not overflow at 360 px, day or night. Task 8.
5. Search and links: "fallout", "nuke", "nuclear", "radiation", "dirty bomb", "KI", "iodine", "decon" each return a radiation topic or protocol in the first three results, and the v7.3 results for "CO", "bleach" and "burn" are unchanged in order; every `p:`, `s:`, `u:` and `c:` link in the new content resolves; a v7.3-shaped backup restores on v7.4. Task 8.

---

## File map

| File | Responsibility |
|---|---|
| `src/survival/surv-fallout-*.json`, `surv-dirty-bomb.json`, `surv-potassium-iodide.json` | ten new topics |
| `src/protocols/radiation-decontamination.json`, `radiation-sickness.json` | two new protocols |
| `src/checklists/fallout-shelter-kit.json` | new checklist |
| `src/survival.js` | hub topic for `radiation` leads its list (the existing hub mechanism) |
| `tools/validate.py`, `src/survival-tools.js`, `src/tooldata/fallout.json` | conditional: tool data `table`, tool `fallout` |
| `figs/figs.py` | up to three figures |
| `tests/test_survival_home.py`, `tests/test_search.py`, `tests/test_survival_tools.py`, `tests/test_validate.py`, `tests/test_figs.py` | shipped-data and tool tests |
| `docs/content-review.md`, `docs/decisions-for-jordan.md`, `docs/v7.4-rulings.md` | records |

Shared names:

- Topic ids: `surv-fallout-warning` (hub), `surv-fallout-where-to-shelter`, `surv-fallout-how-long`, `surv-fallout-shelter-living`, `surv-fallout-coming-inside`, `surv-fallout-water-and-food`, `surv-fallout-leaving`, `surv-dirty-bomb`, `surv-potassium-iodide`, `surv-fallout-get-ready`. Category `radiation`.
- Protocol ids: `radiation-decontamination`, `radiation-sickness`. Checklist id: `fallout-shelter-kit`.
- Tool (conditional): name `fallout`, key `u:fallout`, address `#/survival/tool/fallout`, label "Fallout: time since the blast".
- Tool data `fallout` (conditional): `table: { hours: number[] (each > 0, strictly ascending), divisor: number[] (each ≥ 1, strictly ascending, same length) }`, meaning "at `hours[i]` after the detonation, fallout radiation is `1/divisor[i]` of its level at `hours[0]`". Rows are only those an opened source states.
- Lookup: the largest `i` with `hours[i] ≤ entered hours`.

---

### Task 1: Batch A, the safety core, and the tool gate

**Files:** Create `src/survival/surv-fallout-warning.json`, `surv-fallout-where-to-shelter.json`, `surv-fallout-how-long.json`, `surv-fallout-shelter-living.json`, `docs/v7.4-rulings.md`. Modify `docs/content-review.md`, `docs/decisions-for-jordan.md`.

**Interfaces:**
- Produces: the four topics, checked and out of draft; in `docs/v7.4-rulings.md` a section **"Tool gate"** stating one of: `PASS` with the source, its exact wording and the rows it gives; or `FAIL` with what was looked for. Also a section **"Meter"** stating whether an official source gives public-actionable meter readings (spec 6). Later tasks read both.

- [ ] Writer, independent reviewer, fix round and re-check per the Content contract. Coverage: spec section 4 rows; spec 7 in full. `surv-fallout-shelter-living` states the winter heat default in the words of Global Constraints and links `s:surv-heat-out` and `s:surv-carbon-monoxide`.
- [ ] `surv-fallout-how-long` states the current official sheltering period first, then the dated civil defence periods, each with its publication and year in the sentence. Its "If you have a meter" section follows the Meter finding.
- [ ] Gate: PASS only if a current federal source (FEMA, HHS REMM, CDC, EPA, or a national laboratory document FEMA publishes) states the decay rule as text or a table and the reviewer confirms it by re-opening the source. A rule found only in a pre-2000 publication is FAIL for the tool; it may still appear in the topic as dated text.
- [ ] Build exits 0; full suite passes; `draft` removed only after the review is approved; commit `radiation: safety core topics (batch A)`.

Tasks 2 to 6 start only after Task 1 is approved; every later writer is given the four finished topics to read. Tasks 4, 5 and 6 may run in parallel in separate git worktrees and are merged in that order.

### Task 2 (only if the gate is PASS): Validator accepts a table in tool data

**Files:** Modify `tools/validate.py`. Test: `tests/test_validate.py`, `tests/test_build.py`.

**Interfaces:**
- Produces: `TOOLDATA_KEYS` gains `table`; `TOOL_NAMES` gains `'fallout'`; `validate_tooldata` checks an optional `table` as under Shared names.

- [ ] **Step 1: Failing tests.** A valid fixture with `table` passes. Errors naming id and reason for: `table` not an object; unknown key; `hours` or `divisor` empty, non-numeric or non-finite; `hours` ≤ 0 or not strictly ascending; `divisor` < 1 or not strictly ascending; lengths differ. Tool data without `table` validates as before. A topic linking `u:fallout` builds.
- [ ] **Step 2:** Run; fail. **Step 3:** Implement. **Step 4:** Full suite passes.
- [ ] **Step 5:** Commit `validate: table in tool data, fallout tool name`.

### Task 3 (only if the gate is PASS): Shelter-time tool and its numbers

**Files:** Modify `src/survival-tools.js`; create `src/tooldata/fallout.json`; modify `docs/content-review.md`. Test: `tests/test_survival_tools.py`.

**Interfaces:**
- Consumes: Task 2; the rows recorded under "Tool gate".
- Produces: `TOOLS.fallout = { label: 'Fallout: time since the blast', keywords, draw }`; one labelled whole-number field with steppers (hours since the detonation, 48 px targets, the wind chill tool's pattern); a result block; links to `s:surv-fallout-how-long` and `s:surv-fallout-warning`, each rendered only if its key resolves. Nothing is saved.
- Exact copy. Result: "About 1/N of the level at H hour(s) after the blast" (N = `divisor[i]`, H = `hours[0]`; when N is 1, "Radiation is at its strongest. Stay in the best shelter you have."), followed by the source name from the data. Always shown under any result: "This is a rule of thumb, not a measurement. Only a radiation meter or an official can tell you the level where you are. It does not mean it is safe to go out." Before the first row: "Radiation is at its strongest. Stay in the best shelter you have." and no figure. Past the last row: the last row's result plus "The source gives nothing further." Blank or invalid: "Enter a whole number of hours." Missing data: "The fallout tool’s numbers are not available yet. Nothing is shown until they have been checked against sources."

- [ ] **Step 1: Failing tests,** including Review Focus 1 to 3 with their exact cases, plus: every fixture row returns its own divisor; one hour before each row returns the previous row; keyboard-only use; no overflow at 360 px; night mode; the tool is on the Survival home and in search for "fallout"; the page never contains the word "safe" except inside the fixed caution sentence.
- [ ] **Step 2:** Run; fail. **Step 3:** Implement the tool.
- [ ] **Step 4:** Write `src/tooldata/fallout.json` from the gate's rows with `draft: true`; add a shipped-data test that `divisor[0] == 1`. An independent reviewer re-opens the source and checks every row, then `draft` is removed.
- [ ] **Step 5:** Full suite passes. Commit `survival: fallout shelter-time tool`.

If the gate is FAIL, skip Tasks 2 and 3 and record under Deferred in `docs/v7.4-rulings.md`: "No shelter-time tool: no current federal source states the decay rule as text."

### Task 4: Batch P, the two Emergency protocols

**Files:** Create `src/protocols/radiation-decontamination.json`, `src/protocols/radiation-sickness.json`. Modify `docs/content-review.md`, `docs/decisions-for-jordan.md`. Test: add both ids to whatever shipped-data protocol count or list tests exist (`grep -n "54" tests/`).

- [ ] Writer, independent reviewer, fix round and re-check per the Content contract, reading `src/protocols/carbon-monoxide.json` and `src/protocols/vomiting-diarrhea.json` as the pattern and the Emergency rules in `docs/superpowers/specs/2026-11-16-emergency-survival-overhaul-design.md`. Coverage: spec section 5.
- [ ] Neither protocol carries its own rule about leaving shelter; each links `s:surv-fallout-leaving` (spec 10, call 14). If the protocol schema requires an `evacuate` list, its entries are what the sources say needs medical care, worded as needs, not as an instruction to go outside.
- [ ] Every medical judgement the sources leave open is logged in section D marked "medical professional".
- [ ] Build exits 0; full suite passes; commit `emergency: radiation decontamination and radiation sickness protocols`.

### Task 5: Batch B

**Files:** Create `src/survival/surv-fallout-coming-inside.json`, `surv-fallout-water-and-food.json`, `surv-fallout-leaving.json`; records.

- [ ] Content contract. Coverage: spec section 4 rows. `surv-fallout-water-and-food` restates no water pack number; it links `s:surv-water-store`, `s:surv-water-in-the-house` and `s:surv-make-water-safe`. `surv-fallout-leaving` owns leaving shelter, including for fire, collapse or medical need (spec 10, call 14).
- [ ] After Task 4 is merged, the writer aligns `surv-fallout-coming-inside` with `p:radiation-decontamination` (same order, same "never" list, steps by link) and the reviewer checks the pair.
- [ ] Build, suite, commit `radiation: coming inside, water and food, leaving (batch B)`.

### Task 6: Batch C and the checklist

**Files:** Create `src/survival/surv-dirty-bomb.json`, `surv-potassium-iodide.json`, `surv-fallout-get-ready.json`, `src/checklists/fallout-shelter-kit.json`; records.

- [ ] Content contract. Coverage: spec section 4 rows and section 8. Potassium iodide: spec 10, calls 3 and 12 (no dose table; if an opened CDC or FDA page tells the public to take it after a nuclear detonation, stop and report instead of writing). Checklist items carry no links; water and food links sit in `surv-fallout-get-ready` (spec 10, call 15). Pattern: `src/checklists/home-heat-kit.json`.
- [ ] Build, suite, commit `radiation: dirty bomb, potassium iodide, get ready, shelter kit (batch C)`.

### Task 7: Diagrams

**Files:** `figs/figs.py`, the topics that take a figure, `tests/test_figs.py`, `docs/content-review.md`.

- [ ] Draw, from the checked text only, whichever the text supports: `fallout-shelter-spots` (best and worst places in a house and a larger building), `fallout-coming-inside` (undress, bag, wash), `fallout-decay` (only if the gate is PASS; the gate's rows and nothing else). Tests assert label wording against the topics' key words and forbid wording the text does not carry. Render each at 360 px, day and night, and view them. A reviewer who looks at each image before its caption judges recognisability and compares every label with the topic; a figure that fails is not shipped.
- [ ] Commit `figs: radiation pack diagrams`.

### Task 8: Home, filters, links and search

**Files:** `src/survival.js` (hub), `tests/test_survival_home.py`, `tests/test_search.py`, `tests/test_migration.py`; one link block each in `surv-priorities`, `surv-shelter`, `surv-heat-out`, `surv-carbon-monoxide`, `surv-water-store`, `surv-water-in-the-house` (spec 4, "Existing topics").

**Interfaces:**
- Consumes: all ten topic ids, both protocol ids, the checklist id.

- [ ] **Step 1: Failing tests** for Review Focus 4 and 5 with their exact cases: `ALWAYS` gains the ten `s:` keys; `surv-fallout-warning` is first under "Radiation and fallout"; a shipped-data test that no topic in category `radiation` has a `where` or `when` key; the search cases; a test that the six existing topics' text is byte-identical to `main` apart from the one added link block each.
- [ ] **Step 2:** Run; fail. **Step 3:** Implement. Search keywords are fixed in the new content's `keywords`, not by changing the ranking code; if a case cannot pass without a ranking change, stop and report.
- [ ] **Step 4:** Full suite passes. Commit `survival: radiation category home, protected topics, links, search`.

### Task 9: Whole-pack read, whole-branch review, release v7.4

- [ ] One reviewer reads all ten topics, both protocols, the checklist, the tool data if any, and the binding topics and protocols in Global Constraints together, looking only for: contradictions (times, "never" lists, order of steps); any sentence readable as permitting burning in a sealed room or as "safe to go out"; a rule stated by a topic that does not own it and has drifted; links into the wrong place; a dose or meter threshold that slipped in; internal wording in user-visible text; the home town. Fixes go to one worker; one re-review.
- [ ] Whole-branch review on the most capable model, building the app and driving it at 360×640 in day and night; one fix wave; one re-review.
- [ ] `APP_VERSION = '7.4'`, `VERSION = 'fieldkit-v7.4'`; `python3 build.py --release .`; full suite; squash onto `main` as one commit; `git push origin radiation-pack:main` and push the working branch; update the project doc `claude/FIELD-KIT-STATUS.md` (including the correction that Jordan confirmed "Version 7.3" on his phone on 2026-11-18). If the push is refused, stop and tell Jordan; do not try another route.

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

**Fix round.** The writer fixes every Critical and Important finding or records in `docs/v7.4-rulings.md` why not, removes `draft`, rebuilds, runs the suite, commits. The same reviewer re-checks only the fixes.
