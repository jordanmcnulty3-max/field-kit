# Food from the Land Pack (v7.7) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship the fifth Survival content pack: nine new and three rewritten source-checked topics in a new "Food from the land" category, a kit checklist, up to five diagrams, the v7.5 edits Jordan decided, on top of the search changes already on the branch, released as v7.7.

**Architecture:** Content is JSON under `src/survival/` and `src/checklists/`, exactly as in v7.5. Code changes: a new topic category `land` (home, validator); the search `PACKS` list gains a `land` pack that can name older topics which keep their index place (Task 1). The search list and scoring changes are done (commit `0244043`).

**Tech Stack:** Vanilla JS on `window.FK`, Python build and validator, `unittest` + pytest/Playwright at 360×640.

**Spec:** `docs/superpowers/specs/2026-11-19-food-from-the-land-pack-content-plan.md`, under `docs/superpowers/specs/2026-11-17-v7-survival-knowledge-center-design.md` (sections 5 and 6 bind). Read both. "spec 7" below means the land spec. The writer and reviewer procedure is the **Content contract** at the end of `docs/superpowers/plans/2026-11-19-food-at-home-pack.md`, read with "v7.7" for "v7.5" and the differences listed under "Content contract" below.

## Global Constraints

- Edit `src/`, `figs/`, `tools/`, `tests/`, `docs/`, `build.py` only. Root `index.html`, `sw.js`, `manifest.json`, `leaflet.*` are build output; only Task 8 rebuilds them. To build while working: `python3 build.py /tmp/out-<task>`.
- The repository is public: never write the group's home town into tracked files; say "Central New York".
- Every number, time, temperature, salt strength, smoke time, shelf life, distance, interval and procedure comes from a source that was actually opened and is recorded in `docs/content-review.md`. No Firecrawl or Bright Data; built-in search, then fetch pages the search returned; never a constructed URL. After each fetch confirm the page is the one asked for. Nothing is written from memory when a page fails; say so in the report.
- Source order (spec 9): NYS DEC and NYS DOH; USDA FSIS, CDC, FDA, National Center for Home Food Preservation; extension services (Cornell first); for plants also USDA and Forest Service pages and Poison Control; for fallout the sources v7.4 used. US Army manuals only for points civilian sources do not cover, named with their year. Where sources disagree the more cautious one is used and the question is logged.
- **Preserving labels (spec 9).** Each method in `surv-land-keeping-meat` sits under "Backed by a food-safety agency" or "Traditional: from an extension or historical source, not agency-verified", with its source named; each traditional method states its own risk and what agency sources say against it. A method with no opened source is left out and listed in `docs/v7.7-rulings.md`.
- **Trichinella and temperature (spec 7).** 165°F for all wild game is the cooking rule and is not changed. Every keeping method ends with cooking to 165°F before eating unless an opened agency source says that product is safe as it is for that animal. The jerky pre-heating figure is given as the source gives it, never 160°F as enough for game.
- **No canning procedure. No cured or fermented sausage. No mushroom taught**; the checked sentence "unless an expert has identified it" stays word for word. **No drawing of any plant.** Nothing described for use on a person; no improvised weapon.
- **Plants (spec 10, call 3).** Six to ten plants at most, each with season, part, preparation and look-alikes named as sourced; a plant whose look-alike can kill is left off and named on the never-eat side.
- **New York rules** are stated only in `surv-land-ny-rules`, each as applying in normal times and with the guide year named; other topics link, and state a rule only where safety needs it on the page. Methods New York prohibits (snares, deadfalls and others the sources name) are taught where a source teaches them, with the prohibition stated on the same page.
- Checked content binds new text and is not reworded, except as spec 7 and spec 10 call 9 allow: `surv-food-preserving` (the no-method passages become pointers; agency warnings stay word for word), `surv-food-babies-children` (CDC bottle soak added; the sentence saying it is not on the page reworded), `surv-clean-and-disinfect` (one sentence naming the special-purpose mixes), `surv-fallout-water-and-food` (a second link block), link labels that follow a renamed title, and a sentence a v7.5 page quotes word for word from a rewritten topic (kept identical in both places). Every Emergency protocol is untouched; a conflict is logged in section D marked "Medical professional".
- One rule, one owner (spec 7): shot placement `surv-land-big-game` and `surv-land-small-game`; trap checking as law `surv-land-ny-rules`, as practice `surv-land-trapping`; disease signs `surv-field-dressing-game`; cuts and organs `surv-land-butchering`; fish advisories and fish at 145°F `surv-land-fish-cleaning`; preserving `surv-land-keeping-meat`; plants `surv-food-and-wild-plants`; living food after fallout `surv-land-after-fallout`. Others quote word for word or link.
- A sentence with no source is left out, or labelled in the user-visible text as the app's own caution AND logged in section D.
- No 911 or dial control. No internal wording in user-visible text (question numbers, "Task", "batch", "ruling"), including source lines. US units first, metric in brackets. Plain, direct voice; imperative steps.
- No topic in category `land` carries a `where` or `when` tag (the three rewritten topics lose theirs). Topic tables fit 360 px or scroll with the "Swipe sideways" cue.
- Search (rule 13 and spec 9): the first five on screen for the 123 searches in `tests/fixtures/search_v77_on_screen.json` do not change without a ruling; `GUARD_V77` may shrink, not grow; keywords stay narrow; safety wording is never weakened for a search position.
- Content workers stage only their own files by name; never `git add -A`; no stash, reset, rebase or amend. The three record docs merge by union.
- Tests: `python3 -m unittest tests.test_validate && python3 -m pytest tests -q`; any console error fails. Commit after every task with the session's attribution trailer. Branch `land-pack`. No push to `main` before Task 8.
- Question numbers in `docs/decisions-for-jordan.md` section D: Task 2 uses 152 to 169, Task 3 uses 170 to 179, Task 4 uses 180 to 189, Task 5 uses 190 to 199, Tasks 6 to 8 use 200 onward. Gaps are expected.
- Decisions made without asking go in `docs/v7.7-rulings.md` (exists; add a section per task), each with its cost if wrong, plus a Deferred list that starts with: full plant guide with photos (Jordan's goal; needs his photo files); gardening, livestock and root cellars; cured sausage; canning.

## Review Focus

1. Stored keys: a v7.6-shaped backup, and pins and recents holding `s:surv-traps-and-fishing`, `s:surv-field-dressing-game`, `s:surv-food-and-wild-plants`, still open those topics after their rewrite and category move. Task 1.
2. Filters and home: all twelve `land` topics listed under all 15 Where × When combinations; `surv-land-start` leads the category; the category sits after Food; Basics no longer lists the three moved topics; rows at least 48 px, no overflow at 360 px, day and night. Tasks 1 and 7.
3. Search: the 123 pinned first-fives are unchanged or ruled; "deer", "fish", "fishing", "trap", "snare", "plants", "berries", "jerky", "smoke meat", "butcher", "hunting", "license" each show a `land` page in the first three; "bleeding", "choking", "cut", "bite", "poison", "fall" show what the pre-content build showed; the two first-search speed tests pass ten times alone. Task 7.
4. Links and labels: every `p:`, `s:`, `u:`, `c:` link in new and edited content resolves and its label equals the target title (the three renamed titles are followed everywhere); the hub links every other `land` topic and the checklist; `surv-food-preserving` points to `surv-land-keeping-meat`; an enlarged diagram opens at its top. Task 7.
5. Long topics: `surv-land-butchering`, `surv-field-dressing-game` and `surv-land-keeping-meat` at 360 px: no table overflow, headings usable, the two preserving labels visible above every method without scrolling sideways. Task 8 final drive.

---

## File map

| File | Responsibility |
|---|---|
| `src/survival/surv-land-*.json` | nine new topics |
| `src/survival/surv-traps-and-fishing.json`, `surv-field-dressing-game.json`, `surv-food-and-wild-plants.json` | rewritten, ids kept |
| `src/survival/surv-food-preserving.json`, `surv-food-babies-children.json`, `surv-clean-and-disinfect.json`, `surv-fallout-water-and-food.json` | the allowed edits |
| `src/checklists/land-kit.json` | new checklist |
| `src/survival.js`, `tools/validate.py` | category `land`, its hub lead |
| `src/search.js` | `land` pack with older members |
| `figs/figs.py` | up to five figures; three trap figures move |
| `tests/…` | shipped-data, home, search and figure tests |
| `docs/content-review.md`, `docs/decisions-for-jordan.md`, `docs/v7.7-rulings.md` | records |

Shared names:

- Category id `land`, label "Food from the land", placed after `food` in `CATS`.
- New topic ids: `surv-land-start` (hub), `surv-land-big-game`, `surv-land-small-game`, `surv-land-trapping`, `surv-land-butchering`, `surv-land-fish-cleaning`, `surv-land-keeping-meat`, `surv-land-ny-rules`, `surv-land-after-fallout`.
- Rewritten, ids kept: `surv-traps-and-fishing` (title "Fishing for food"), `surv-field-dressing-game` (title kept), `surv-food-and-wild-plants` (title "Wild plants").
- Checklist id `land-kit`, title "Hunting, fishing and trapping kit", category `land`.

---

### Task 1: The `land` category and the search pack

**Files:** `src/survival.js`, `tools/validate.py`, `src/search.js`, the three existing topic files (category and tags only), `tests/test_survival_home.py`, `tests/test_search.py`, `tests/test_validate.py`, `tests/test_migration.py`.

**Interfaces:**
- Produces: `land` accepted by the validator for topics and checklists; `CATS` entry `['land', 'Food from the land']` after `food`; `LEADS.land = 'surv-land-start'` (no error while the hub does not exist yet); in `src/search.js` a `PACKS` entry `{ topic: 'land', hub: 'surv-land-start', protocols: [], checklists: ['land-kit'], older: ['surv-traps-and-fishing', 'surv-field-dressing-game', 'surv-food-and-wild-plants'] }` where `older` ids keep the index position they have on `origin/main` and every other `land` topic indexes after all older pages, hub first.

- [ ] **Step 1: Failing tests.** `test_land_category_sits_after_food_and_holds_the_three_moved_topics` (home shows "Food from the land" after "Food"; Basics lacks the three); `test_moved_topics_keep_their_index_position` (for "fishing", "dressing", "plants", "trap", "wild", `FK.search.query` returns the same keys in the same order as the fixture, and all 123 pinned first-fives still pass); `test_every_id_in_PACKS_exists_and_each_pack_holds_its_category` extended to accept `older` (every `land` topic is either in `older` or newer than v7.6); `ALWAYS` in `tests/test_survival_home.py` gains the three `s:` keys; a stored-keys test for Review Focus 1.
- [ ] **Step 2:** Run; fail. **Step 3:** Implement. The three topics change `category` to `land` and drop `where`/`when`; no text changes.
- [ ] **Step 4:** Full suite. Commit `survival: Food from the land category; land pack keeps older topics in place`.

### Task 2: Batch A, the safety core, and the plant poisoning gate

**Files:** Rewrite `surv-food-and-wild-plants.json`, `surv-field-dressing-game.json`; create `surv-land-butchering.json`, `surv-land-keeping-meat.json`; edit `surv-food-preserving.json`, `surv-food-babies-children.json`, `surv-clean-and-disinfect.json`; the tests that pin those pages; the three record docs.

**Interfaces:**
- Produces: the four topics checked and out of draft; in `docs/v7.7-rulings.md` sections **"Plant poisoning gate"** (what the sources give a household with no Poison Control line; PASS means a gap in the `poisoning` protocol is logged for Jordan, the protocol is not edited), **"Keeping meat: methods"** (each method, its label, its source, its end step) and **"Quoted sentences"** (each sentence a v7.5 page quotes from a rewritten topic, and whether it was frozen or changed in both places).

- [ ] Writer, independent reviewer, fix round and re-check per the Content contract. Coverage: spec 4 rows 6, 6a, 8, 9; spec 7 in full; spec 10 calls 2, 3, 8.
- [ ] `surv-land-butchering` covers every item in call 8. `surv-field-dressing-game` stops at the cooled carcass and links to it.
- [ ] The test that forbids linking Field dressing game from food pages is replaced by one requiring `surv-food-cooking-no-power` or `surv-food-power-out` to link it; `surv-food-preserving` links `surv-land-keeping-meat` only.
- [ ] Build exits 0; full suite passes; `draft` removed only after the review is approved; commit `land: safety core topics (batch A)`.

Tasks 3 to 5 start only after Task 2 is approved; every later writer reads the four finished topics. They run in parallel in separate git worktrees and are merged in order.

### Task 3: Batch B

**Files:** Create `surv-land-start.json`, `surv-land-big-game.json`, `surv-land-small-game.json`, `src/checklists/land-kit.json`; records.

- [ ] Content contract. Coverage: spec 4 rows 1, 3, 4; spec 8 checklist; spec 10 call 5; insects (spec 12) as a short hub section only if sourced. The hub links every other `land` topic by its final id and title (File map) and the checklist.
- [ ] Commit `land: hub, hunting topics and kit checklist (batch B)`.

### Task 4: Batch C

**Files:** Rewrite `surv-traps-and-fishing.json` (fishing only); create `surv-land-fish-cleaning.json`, `surv-land-trapping.json`; `tests/test_figs.py` and topic `figure` references for `trap-snare`, `trap-squirrel`, `trap-fig4` (they move to `surv-land-trapping` if they match its text, else are removed); records.

- [ ] Content contract. Coverage: spec 4 rows 2, 5, 7; spec 10 calls 4 and 7. Trapping is written for someone who has never trapped.
- [ ] Commit `land: fishing, fish cleaning and trapping (batch C)`.

### Task 5: Batch D

**Files:** Create `surv-land-ny-rules.json`, `surv-land-after-fallout.json`; edit `surv-fallout-water-and-food.json` (second link block) and its test; records.

- [ ] Content contract. Coverage: spec 4 rows 10, 11; spec 7 Fallout and New York rules; spec 10 call 6. The trap-check interval is read from the current NYS DEC trapping guide and recorded with its year. The checked fallout line is quoted first in `surv-land-after-fallout`.
- [ ] Commit `land: New York rules and food sources after fallout (batch D)`.

### Task 6: Diagrams

**Files:** `figs/figs.py`, the topics that take a figure, `tests/test_figs.py`, `docs/content-review.md`.

- [ ] Draw, from the checked text only, whichever the text supports: `fishing` (redrawn to the text), `land-deer-vitals`, `land-field-dressing-cuts`, `land-deer-cuts` (where each cut comes from), `land-trap-set`. Every drawn string is found in its topic; no number the topic lacks; no plant. Render at 360 px, day and night, and view them. A reviewer looks at each image before any text; a figure that fails is fixed or not shipped.
- [ ] Commit `figs: land pack diagrams`.

### Task 7: Home, filters, links, and search against the pre-content build

**Files:** `tests/test_survival_home.py`, `tests/test_search.py`, `tests/test_migration.py`, `tests/fixtures/search_v77_on_screen.json` (only with a ruling); link blocks in `surv-priorities`, `surv-dangerous-animals`, `surv-food-when-short`, `surv-food-power-out`, `surv-food-cooking-no-power` and the cross-links earlier writers listed in `docs/v7.7-rulings.md`.

- [ ] **Step 1:** Failing tests for Review Focus 2, 3 and 4 with their exact cases.
- [ ] **Step 2:** Implement. Fix displaced results by narrowing the new content's `keywords` only (rule 13). Run `/tmp`-built comparisons between commit `0244043` and this build for the 123 pinned searches and for every word and 3- to 5-letter prefix of the new pages' titles and keywords; list every pinned search whose first five changed, with the reason, in `docs/v7.7-rulings.md`. A change is fixed or ruled, never left.
- [ ] **Step 3:** The two speed tests alone ten times; full suite. Commit `survival: land category home, links, search order`.

### Task 8: Whole-pack read, whole-branch review, release v7.7

- [ ] One reviewer reads all twelve topics, the checklist, the edited v7.5 pages and the binding topics and protocols together, looking for: contradictions (temperatures, times, "never" lists, order of steps); a keeping method without its label, its risk or its 165°F end step; a plant sentence that could lead someone to eat something the text cannot make certain; a New York rule outside its owner or without "in normal times"; a rule stated by a page that does not own it and has drifted; summary or Do first that disagrees with its body; missing links at a moment of decision; an unsourced figure; internal wording; the home town. Fixes go to one worker; one re-check.
- [ ] Whole-branch review on the most capable model, building the app and the v7.6 release and driving both at 360×640 in day and night, including walk-throughs as (a) someone who has just shot their first deer at dusk in November, (b) a family in July with a deer and no power, (c) someone who has never trapped and has two traps, (d) a parent whose child ate berries from the yard; one fix wave; one re-check.
- [ ] `APP_VERSION = '7.7'`, `VERSION = 'fieldkit-v7.7'`; `python3 build.py --release .`; full suite; squash onto `main` as one commit (`git commit-tree HEAD^{tree} -p origin/main`); push the working branch and the squashed commit to `main`; confirm the live `sw.js`; update the project doc `claude/FIELD-KIT-STATUS.md`. If the push is refused, stop and tell Jordan.

---

## Content contract (Tasks 2 to 5)

As in `docs/superpowers/plans/2026-11-19-food-at-home-pack.md`, with these differences:

- The record docs are `docs/content-review.md`, `docs/decisions-for-jordan.md` section D (the task's reserved range) and `docs/v7.7-rulings.md`.
- The model topic for layout is `src/survival/surv-food-still-good.json`; for a long how-to, `src/survival/surv-wood-stoves-fireplaces.json`.
- The writer's report also lists: every method or plant left out for want of a source; every New York rule found (for Task 5 to own); every cross-link wanted in a page outside the batch (for Task 7).
- The reviewer also checks: the preserving labels and end step on every method; that no plant on the safe list has a look-alike a source calls deadly; that every New York statement says "in normal times" and names the guide year.
- A rewritten topic keeps its `id`; a sentence another page quotes from it word for word is found with `grep` before the rewrite and handled as the spec's call 9 says.
