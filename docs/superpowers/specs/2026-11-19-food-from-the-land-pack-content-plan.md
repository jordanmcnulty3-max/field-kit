# Food from the land pack: content plan (v7.7)

Date: 2026-11-19. Fifth content pack under `2026-11-17-v7-survival-knowledge-center-design.md` (the v7 design),
whose sections 5 and 6 bind everything here. Built the same way as the food at home pack
(`2026-11-19-food-at-home-pack-content-plan.md`, `../plans/2026-11-19-food-at-home-pack.md`, whose "Content
contract" is the writer and reviewer procedure). Calls made here are in section 10. Decisions made during the
build go in `docs/v7.7-rulings.md`, which already holds the search record.

It was planned as v7.6; a fix release (retired USGS map layer, home headings) took that number on 2026-11-19.

## 1. Intent

The second of Jordan's two food releases. v7.5 got a household from one week of food to several and kept it
edible. This pack is for when the pantry is running down: getting food from the land around Central New York
without wasting effort, poisoning anyone or losing the meat.

Jordan (2026-11-19), in the brainstorm:

- **Who knows what.** In the group there is "a mix of fishing knowledge, some hunting, but probably little to no
  trapping". So fishing and hunting topics build on experience and go to what changes when it is for food;
  trapping is taught from zero.
- **Wild plants: text only now, a short safe list** (his choice A). "The ultimate goal is a full guide with
  photos"; that is a later release and needs photo files from him.
- **Keeping game meat: the agency-backed methods plus traditional methods** (his choice; it overrules the v7.5
  call against teaching meat drying, which was made without asking him).
- **Bleach: two household mixes plus named special-purpose mixes** exactly as their source gives them (his
  choice A on D123 and D141). The CDC bottle soak is added.
- **Home screen: its own category, "Food from the land"** (his choice A), hub first. The three v7 topics move
  out of Basics into it.
- **Search first:** one list in rank order, and a whole keyword outranks a title prefix (both his decisions;
  built and tested before this plan, `docs/v7.7-rulings.md`).

What follows from that: the pack's first job is to tell an inexperienced, hungry group where effort pays in
each season and what will hurt them; its second is to make sure an animal, once taken, becomes safe food and
not waste.

## 2. Goals, non-goals, anti-goals

- **Goals:** a person can decide what to go after this week given the season and what they own; catch fish for
  food with a rod, and with set lines, nets and traps where the text can teach them; take deer, small game and
  birds with a firearm or bow they already own, placing the shot to kill quickly and finding the animal after;
  set and check traps having never trapped; field dress, skin and butcher a deer and smaller animals, and
  clean fish, knowing the signs that an animal is not safe to eat; keep meat and fish edible without a freezer,
  knowing which methods a food-safety agency backs and which are traditional; eat a small set of common plants
  safely and never eat the deadly ones; know New York's normal-times rules; know what to do about game, fish,
  milk and garden produce after fallout.
- **Non-goals:** a full plant identification guide (later release, with photos); mushrooms as food (the app
  says never, section 10); gardening, seed saving, livestock, root cellars (Staying put pack); firearm
  selection, ballistics and marksmanship (Tactical has the ballistics tool); making or modifying weapons;
  commercial processing; tanning hides beyond what a source gives for keeping one from rotting; cooking
  recipes; hunting as sport (trophies, calling contests, regulations trivia).
- **Anti-goals:** any sentence that helps someone eat a plant or mushroom the text cannot make them certain of;
  a drawing of an edible plant; a temperature, time, salt strength, smoke time or shelf life nobody sourced; a
  traditional preserving method shown without its label and its specific risk; any trap, snare or set described
  for use on a person; instructions for an improvised weapon or explosive; a New York rule stated from memory
  or without "in normal times"; text that contradicts a checked topic or protocol (165°F for game, the carbon
  monoxide rules, the v7.5 throw-out rules); treatment text in Survival that competes with an Emergency
  protocol; anything that names the group's home town.

## 3. Approaches

1. **A: a new Survival category of topics with a hub and a Do first box where an action is urgent; injuries and
   illness by link to Emergency protocols (chosen; the pattern of v7.2 to v7.5).** Jordan picked the separate
   category over folding the topics into Food (21 topics in one list) or leaving them in Basics (hard to find).
2. B: one release with a photo plant guide. Rejected by Jordan for now: no photo files exist; text-only ships
   and the guide is on the backlog.
3. C: agency-backed preserving only. Rejected by Jordan: he wants traditional methods too, labelled.

One release (v7.7), built like the food at home pack, after the search changes already on the branch.

## 4. Survival topics (new category `land`, "Food from the land", listed after `food`)

Ids are final unless a batch finds a reason; titles may be tuned. "Existing" topics are rewritten and keep
their ids (stored pins and recents point at them).

| # | id | Title | Notes |
|---|---|---|---|
| 1 | `surv-land-start` | Food from the land: where to start | **Hub.** What is worth the effort by season in Central New York; calories against effort; who should not go; links to everything. |
| 2 | `surv-traps-and-fishing` (existing, split) | Fishing for food | Rod and reel briefly; set lines, nets, traps and ice fishing as sources teach them; where fish are by season. Keeps the id; becomes fishing only. |
| 3 | `surv-land-big-game` | Hunting deer and big game | Shot placement, after the shot, tracking, safety (tree stands, identifying the target). |
| 4 | `surv-land-small-game` | Small game and birds | Squirrel, rabbit, turkey, waterfowl, grouse as sources cover them; what is worth a cartridge. |
| 5 | `surv-land-trapping` | Trapping | From zero: trap types, sets, where, checking, dispatch, safety. New York's legal and illegal devices stated. |
| 6 | `surv-field-dressing-game` (existing) | Field dressing game | Deepened: deer step by step, small game, birds, cooling, signs of disease (CWD, rabies, tularemia, trichinella as sourced), 165°F (D10 stays). |
| 7 | `surv-land-fish-cleaning` | Cleaning and keeping fish | Kill, gut, fillet or cook whole; keeping on ice or cold; New York fish consumption advisories. |
| 8 | `surv-land-keeping-meat` | Keeping game meat | **Owner of meat preserving.** Cold and time; winter as the freezer; jerky per USDA and NCHFP (D149); traditional methods, labelled. |
| 9 | `surv-food-and-wild-plants` (existing) | Wild plants | Short safe list, never-eat list, no mushrooms, text only. |
| 10 | `surv-land-ny-rules` | New York rules for hunting, fishing and trapping | **Owner of every New York rule.** Licences, seasons, legal methods, trap-check intervals, tagging; "in normal times". |
| 11 | `surv-land-after-fallout` | Game, fish, milk and gardens after fallout | Closes D91. `surv-fallout-water-and-food` stays owner of stored food and water and links here. |

`surv-dangerous-animals` stays in Basics and gains one link block.

## 5. Emergency

No new protocol is planned. Hunting and trapping injuries link to existing protocols (`bleeding`,
`impaled-object`, `fracture`, `hypothermia`, `animal-bite`, `poisoning`, `tick`). **Plant poisoning gate:** if
the sources (Poison Control, CDC, NYS DOH) give steps for a household with no Poison Control line and no
hospital that the `poisoning` protocol lacks, the gap is logged for Jordan; the checked protocol is not changed
in this pack.

## 6. Tool

None planned. **Gate:** a "legal hours" or season lookup is not built: seasons change yearly and a stale table
in an offline app is worse than none. The rules topic gives dates as of the guide year it names.

## 7. Rules this pack must agree with

- **Game temperature.** 165°F for all wild game (D10) stays as the cooking rule in `surv-field-dressing-game` and
  `surv-food-cooking-no-power`, unchanged. D149 is NCHFP's 170°F for game jerky against that 165°F. The two are
  different steps: `surv-land-keeping-meat` gives the jerky pre-heating figure as the source gives it (the more
  cautious where sources differ, each named), says in the same sentence that it is above the 165°F cooking rule,
  and never presents 160°F as enough for game. D149 is closed by that and logged.
- **Trichinella.** `surv-field-dressing-game` (checked) says freezing, smoking or curing does not reliably kill
  trichinella in game. That binds this pack: "winter as the freezer" and every traditional method are ways to
  keep meat, never ways to make it ready to eat. Every method in `surv-land-keeping-meat` ends with cooking to
  165°F before eating unless an opened agency source says that method's product is safe as it is, for that
  animal.
- **v7.5 food safety.** `surv-food-still-good` owns what to throw out; `surv-food-cooking-no-power` owns cooking
  temperatures and cooking with flame; `surv-food-poisoning` owns botulism signs. Quote or link, never restate
  differently.
- **`surv-food-preserving` (v7.5) is revised** wherever it says the app gives no method for drying meat, salting,
  curing or smoking (its summary, Drying meat, Salting and curing, Smoking). Those passages become pointers to
  `surv-land-keeping-meat`; every agency warning in them is kept word for word. Its canning position (no
  procedure) stands and covers meat and fish. The pointer goes to `surv-land-keeping-meat` only.
- **Bleach.** Rule: two household mixes, plus special-purpose mixes exactly as their source gives them, each
  labelled for its one use and "never for drinking water". The NCHFP 1:5 botulism mix stands; the CDC bottle
  soak is added to `surv-food-babies-children`. `surv-clean-and-disinfect` stays the owner of the two household
  mixes and gains one sentence naming the special mixes and where they are.
- **Fallout.** One rule, one owner: stored food and water after fallout stay with
  `surv-fallout-water-and-food`; living food sources go to topic 11. The checked line there ("don't use them
  until officials say you can") stays word for word and is quoted first in topic 11. Topic 11 then follows
  Jordan's v7.4 decision for when no official instruction ever comes: the older federal civil defence
  publications, named with their year and marked dated, and the app never says "safe". The checked page gains a
  second link block pointing to topic 11 (its test is updated to allow exactly that).
- **Flame, carbon monoxide, generators.** Checked topics are not reworded. Smoking and drying meat is outdoors.
- **New York rules** live only in topic 10; other topics say "check the rules" with a link and state a rule
  only where safety needs it on the page (for example a trap that is illegal because it is dangerous).
- **Illegal in normal times.** Snares, deadfalls and any other method New York prohibits are taught where a
  source teaches them, each with the prohibition stated on the page as applying in normal times (v7 decision:
  state rules are stated as applying in normal times; trapping animals for food is in).
- **One rule, one owner** inside the pack: shot placement (3 and 4), trap checking interval as law (10) and as
  practice (5), disease signs (6), fish advisories (7), preserving (8), plants (9).
- **Standing rules:** no 911 or dial button; never the home town; no internal wording in user-visible text;
  no drawings of edible plants; nothing for use against people.

## 8. Checklist and diagrams

- **Checklist `land-kit`** ("Hunting, fishing and trapping kit"): from the sources as opened (NYS DEC hunter
  and trapper education material, extension game-processing guides): knives and sharpening, game bags, gloves,
  cordage, fishing tackle, traps, salt, thermometer. No quantities unless a source gives them.
- **Diagrams**, drawn after the text is checked and from it, each reviewed by someone who looks at the image
  first; one not recognisable without its caption is not shipped. Candidates, each only if the text supports
  it: `fishing` redrawn to match the text (the old one drew a stake funnel against a basket-trap text); deer
  vital area for shot placement; field dressing cut lines; one basic trap set. **No diagram of any plant.**

## 9. Batches and sources

**Batches** (writer, independent reviewer who re-opens the sources, fix, re-check; then diagrams, whole-pack
read, final drive of the built app at 360x640 as a person in a situation):

- **A, safety core, first and alone:** `surv-food-and-wild-plants`, `surv-field-dressing-game`,
  `surv-land-keeping-meat`, and the two v7.5 edits (`surv-food-preserving`, the CDC bottle soak with the
  `surv-clean-and-disinfect` sentence). Its report also records the **plant poisoning gate**.
- Then in parallel in separate git worktrees, each with a reserved range of question numbers:
  - **B:** `surv-land-start`, `surv-land-big-game`, `surv-land-small-game`, checklist `land-kit`.
  - **C:** `surv-traps-and-fishing`, `surv-land-fish-cleaning`, `surv-land-trapping`.
  - **D:** `surv-land-ny-rules`, `surv-land-after-fallout`.

**Sources.** Primary: NYS DEC (hunting and trapping regulations guide and freshwater fishing guide for the
current year, hunter and trapper education manuals, CWD and wildlife disease pages); NYS DOH (fish consumption
advisories, tularemia, rabies); USDA FSIS (game from field to table, jerky, safe temperatures); National Center
for Home Food Preservation (jerky, curing and smoking, fish); CDC (trichinellosis, tularemia, CWD, botulism,
infant feeding items); FDA (fish). Extension services for processing and for the traditional methods: Cornell
Cooperative Extension first, then Penn State, Minnesota, Alaska (UAF) and others as found. Plants: Cornell,
USDA Plants database and Forest Service pages, NYS DEC, Poison Control, university extension foraging and
poisonous-plant pages. Fallout: FDA, EPA, CDC, FEMA, and the older federal civil defence publications already
used in v7.4, named with their year and marked dated. US Army field manuals (survival) only for points civilian
sources do not cover, named with their year.

Every rule in v7 design section 6 applies. Every number comes from a source that was opened and is recorded in
`docs/content-review.md`. Where sources disagree the more cautious one is used and the question is logged in
`docs/decisions-for-jordan.md` section D from **number 152**. Web research uses built-in search and fetch only;
the Firecrawl and Bright Data connectors are not used; each fetched page is confirmed to be the page asked for;
nothing is written from memory when a page fails to load.

**Traditional methods (Jordan's decision).** A method goes in only from a source that was opened. Each is shown
under one of two labels: "Backed by a food-safety agency" (USDA, FDA, CDC, NCHFP) or "Traditional: from an
extension or historical source, not agency-verified", with the source named, and each traditional method
carries its own risk in plain words and what the agency sources say against it, if they do. A method with no
opened source is left out and listed for Jordan.

**Search.** New pages index after all older pages (a `land` entry in `PACKS`). Keywords follow rule 13. Before
the final review the on-screen first five for the 123 searches in `tests/fixtures/search_v77_on_screen.json`
are compared with the pre-content build of this branch; a change is fixed or ruled on, never left. The guard
list of protocol keywords may shrink, not grow. The first-search speed tests must pass without loosening.
The moved topics (`surv-traps-and-fishing`, `surv-field-dressing-game`, `surv-food-and-wild-plants`) change
category and text; searches pinned to them are re-recorded only with a ruling.

## 10. Calls made (Jordan can overrule)

1. Ships as **v7.7**. Eight new topics, three rewritten, one checklist, up to four diagrams.
2. **No mushroom is taught.** The checked sentence stays as it is: never eat a wild mushroom unless an expert
   has identified it. Text cannot teach the difference and the deadly ones kill days later.
3. **The safe plant list** is about six to ten plants, each with season, part, preparation and its look-alikes
   named, as sourced (v7 design 6.5). A plant whose look-alike can kill (the wild carrot family is the example)
   is left off the list and named on the never-eat side. A plant with a poisonous but not deadly look-alike
   (cattail and iris) may stay only if a source gives a way to tell them apart in words. If the sources support
   fewer, the list is shorter.
4. **Snares and deadfalls are taught with New York's prohibition stated** (section 7). Cost: the app describes
   methods that are unlawful in normal times.
5. **Hunting topics assume a legal firearm or bow already owned and a hunter who has had basic training.** No
   firearm choice, no marksmanship teaching, no ammunition reloading.
6. **No season or bag-limit table that will go stale**: the rules topic names the guide year, gives the
   structure (which licence, which season type, what is always illegal) and the figures a source gives as
   standing rules, and says to check the current guide.
7. **Trapping instructions come from trapper education material**, not survival manuals, wherever both exist.
8. **Butchering goes as far as quarters and boning out**; no sausage, no grinding.
9. Existing checked topics outside this pack gain at most one link block each and are not reworded, except:
   the edits named in section 7; link labels that must follow a renamed title; and a sentence a v7.5 page quotes
   word for word from one of the three rewritten topics, which is kept identical in both places (the quoted
   sentence is frozen in the rewrite unless a source forces a change, and then both change together). Fish at
   145°F stays quoted where it is; its owner becomes `surv-land-fish-cleaning`.
10. The hub is the "where to start" topic; no topic in the pack is ever hidden by a filter.
11. Questions that would have been asked of Jordan during the build are settled by the cautious option and
    logged in `docs/v7.7-rulings.md` with their cost if wrong.

## 11. Left to the builder

Section order and wording inside each topic; which candidate diagrams earn a place; test names; how the
question-number ranges are split; whether `surv-land-small-game` splits into two topics if the sources are
rich; which Where and When filter tags each topic carries (the v7 design's rules apply).

## 12. Settled after the builder check (calls, Jordan can overrule)

- **Filters:** call 10 wins. Every topic in the category is listed under every Where and When filter and joins
  the always-listed set in the tests.
- **Search index:** the three rewritten topics keep the place in the index they have today, so tie order for the
  pinned searches does not move because of a category change. The `PACKS` mechanism gains a way to name older
  topics that belong to a pack's category; only the eight new topics and the checklist index after older pages.
- **Insects** (now in the plants topic): a short section in the hub, as sourced, or dropped if the sources do
  not support it.
- **Existing figures** `trap-snare`, `trap-squirrel` and `trap-fig4` move with their text to `surv-land-trapping`
  and do not count toward the four candidates; their test follows them. Each is re-checked against the rewritten
  text and removed if it no longer matches.
- **Tests that pin the old state** are updated with the change they guard: the v7.6 ban on linking Field
  dressing game from food pages is lifted (links are added, a carried-in item); `surv-food-babies-children` is
  reworded where it says the bottle soak is not on the page; `land` is added to the category lists in
  `src/survival.js` and `tools/validate.py`.

