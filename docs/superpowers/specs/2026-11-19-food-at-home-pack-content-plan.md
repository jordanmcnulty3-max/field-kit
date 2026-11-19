# Food at home pack: content plan (v7.5)

Date: 2026-11-19. Fourth content pack under `2026-11-17-v7-survival-knowledge-center-design.md` (the v7 design),
whose sections 5 and 6 bind everything here. Built the same way as the radiation pack
(`2026-11-18-radiation-pack-content-plan.md`, `../plans/2026-11-18-radiation-pack.md`, whose "Content contract" is
the writer and reviewer procedure). Calls made here are in section 10.

## 1. Intent

The roadmap's Food pack ("storage, hunting, trapping, fishing, plants") is split by Jordan (2026-11-19) into two
releases: **v7.5 Food at home** (this plan) and **v7.6 Food from the land** (hunting, trapping, fishing, field
dressing and butchering, preserving game and fish, wild plants, New York rules). Both get full treatment.

Jordan (2026-11-19), in the brainstorm:

- A month into a grid-down winter the group's food comes from **both** a stocked pantry and the land.
- The group's **pantries hold about a week**. Some households have a **chest freezer**. Who has a generator is
  not known; Jordan plans to buy one. **Nobody cans at home**, as far as he knows. Gardens: not known.
  **Children range from 1 to 12 years old.**
- He was shown the topic list in section 4 and said to move forward with the build. That is taken as approval
  of the pack as proposed and as "go" for the whole run; questions that would have gone to him are settled by
  the cautious option and logged.

What follows from that: no topic can make food appear on day 8, so the most useful thing this pack does is get
each household from one week of food to several **before** anything happens, and then keep what they have
edible: through the first days without power, through a winter of cooking without a kitchen, and without
poisoning anyone.

## 2. Goals, non-goals, anti-goals

- **Goals:** a person can find in seconds what to do with a fridge and freezer when the power goes out and when
  to stop trusting them; work out how much food their household needs for a given number of days and what kinds
  keep; store it so it lasts (containers, pests, rotation, shelf life); tell whether food is still good and what
  is never worth the risk; cook without a kitchen without breaking the carbon monoxide rules; keep food and
  hands clean with little water; stretch food when it is short and know who must not go short; feed a
  one-year-old and young children; preserve food without a freezer as far as official sources teach it;
  recognise food poisoning and botulism and know what to do.
- **Non-goals (v7.6 or later):** hunting, trapping, fishing, field dressing, butchering, wild plants and
  mushrooms, preserving game and fish beyond what a general preserving source says about meat; gardening,
  seed saving, livestock and root cellars (Staying put pack, only if sourced); nutrition for medical conditions;
  special diets; alcohol; food for pets beyond a line a source gives; barter and markets.
- **Anti-goals:** any sentence that lets someone eat food a source says to throw out; a temperature, time,
  shelf life, salt or acid concentration, or calorie figure nobody sourced; home canning instructions for
  low-acid food (meat, vegetables, fish) or any canning procedure at all (section 10, call 3); "it smells fine"
  as a test; advice to ration a young child, a pregnant or nursing woman or a sick person without a source
  saying so; cooking advice that could be read as permitting a camp stove, grill or generator indoors;
  treatment text in Survival that competes with an Emergency protocol; infant formula or feeding amounts
  nobody sourced; anything that names the group's home town.

## 3. Approaches

1. **A: Survival topics with a Do first box; exposure to illness handled by Emergency protocols (chosen; the
   pattern of v7.2 to v7.4).** The hub's Do first box carries the power-out actions. Food poisoning care is the
   existing `vomiting-diarrhea` and `dehydration` protocols by link. A new Emergency protocol for botulism is
   added only if the sources give steps a lay person can take without a hospital (section 5).
2. B: a guided "power is out" flow in the step player. Rejected for the reason given in the radiation plan:
   the player's Back logic failed three reviews in v6 and is not reopened for one topic.
3. C: one release with Food from the land. Rejected by Jordan: two releases, food-safety rules first so the
   second release quotes them.

One release (v7.5), built like the radiation pack.

## 4. Survival topics (category `food`, already defined in `src/survival.js` and `tools/validate.py`)

All ten are new. Ids are proposals; the builder may adjust titles but not scope.

| Id | Title | Covers |
|---|---|---|
| `surv-food-power-out` | Food when the power goes out | **Hub; leads the category.** Do first: keep doors shut; the fridge and freezer hold times sources give; what to eat first; when to move food outside or onto ice only as a source allows; thermometer; what to throw out by link. Running a freezer on a generator by link to Generators. Winter cold as a fridge only as a source supports. Links every other food topic |
| `surv-food-how-much` | How much food to store, and what | Building from a week to several: what official sources say to store, how many days they say, kinds of food that keep, water needed to prepare them (by link to the water pack, no number restated), children, special needs as sources list them; **calorie or weight figures only as a source states them**; the planner if section 6 allows |
| `surv-food-storage` | Store food so it lasts | Where (cool, dry, dark as sources say), containers, pests and rodents (link to Clean and disinfect for droppings), rotation and dating, shelf life of staples only as sources give it, cans that are dented, bulging or rusted, what "best by" means as a source states it, freezing weather and stored food |
| `surv-food-still-good` | Is it still good? | Owner of the throw-out rules: time and temperature limits, the foods sources say to discard after a power cut, never taste to test, mould, flood- or fire-damaged food, home-canned and commercially canned food warning signs, leftovers without refrigeration |
| `surv-food-cooking-no-power` | Cook without power | What can be cooked on what; **every flame indoors is owned by the checked carbon monoxide, heater, stove and generator topics, quoted or linked, never restated differently**; outdoor cooking; fuel by link; safe cooking temperatures (owner; must agree with the checked 165°F for game in Field dressing game and with USDA for the rest); eating food cold; boiling water for food by link |
| `surv-food-clean-kitchen` | Keep food clean with little water | Hands, surfaces, dishes and utensils with little water, raw and cooked apart, the food-surface bleach mix **by link to Clean and disinfect, not restated**, who must not prepare food when sick (must agree with Stomach illness in a group) |
| `surv-food-when-short` | When food is short | What sources say about eating less safely, who must not go short (children, pregnant and nursing women, the sick, hard physical work) only as sourced, water before food, signs someone is not getting enough only as sourced, sharing in a group; no fasting or diet claims |
| `surv-food-babies-children` | Feeding babies and young children | Breast milk and formula in an emergency (must agree with Water and food after fallout and the water pack on water for formula), ready-to-feed formula, cleaning bottles with little water, foods a one-year-old can and cannot have and choking hazards as sources list them, honey, milk; every amount sourced or absent; medical questions logged for a medical professional |
| `surv-food-preserving` | Preserve food without a freezer | Drying, salting, curing, smoking and cold storage **only as far as an official source (USDA, National Center for Home Food Preservation, a state extension service) teaches a beginner**; what each needs; **canning: why low-acid canning is not something to learn in a crisis, and what to do with home-canned food from someone else** (section 10, call 3); emptying a failing freezer |
| `surv-food-poisoning` | Food poisoning and botulism | Recognising food poisoning; botulism signs and that it is a medical emergency, as CDC states; what to do, by link to the `vomiting-diarrhea` and `dehydration` protocols and to the new protocol if section 5 adds one; infants and honey; when to throw out everything from the same batch |

**Tags.** No food topic in this pack carries a `where` or `when` tag, and all ten keys are added to the protected
`ALWAYS` list in `tests/test_survival_home.py`: food safety must never be hidden by a filter.

**Existing topics.** `surv-priorities`, `surv-stomach-illness-in-a-group`, `surv-generators`,
`surv-fallout-water-and-food`, `surv-fallout-get-ready`, `surv-water-store` and `surv-heat-out` may each gain
**one link block** to the relevant food topic. Their checked text is not reworded. The three v7 food topics under
Basics (`surv-food-and-wild-plants`, `surv-traps-and-fishing`, `surv-field-dressing-game`) are not moved or
edited in this release; `surv-food-how-much` and the hub link to them.

## 5. Emergency

- Food poisoning care is the existing checked `vomiting-diarrhea` and `dehydration` protocols, **linked, never
  edited**. Choking is the existing choking protocols by link from the children topic.
- **Botulism protocol: decided after the sources are opened.** It is added (`botulism`, category and tier the
  builder's choice, never `advanced`) only if CDC or another opened medical source gives recognition signs and
  actions a lay person can take when no hospital is reachable. If the sources say only "get medical care
  immediately", there is no protocol: `surv-food-poisoning` states the signs and that statement, and the gap is
  logged for a medical professional.
- Any disagreement between a food source and a checked protocol (for example who may prepare food after
  vomiting, already D32) is logged for Jordan, not resolved in text.

## 6. Tool

**Food planner: decided after the sources are opened, not now** (the v7.3 wind chill and v7.4 shelter-time lesson).

- It ships only if a current federal source or a state extension service states **per-person amounts as text or
  a table** (calories per person per day, or weights of food groups per person for a stated period), and the
  batch reviewer confirms it by re-opening the source.
- If it ships: inputs are the existing group setting (people, days), stored as today; output is the amount of
  food by the source's own categories, from `src/tooldata/food.json` (sourced, validated and release-gated like
  `water.json`), always rounded up, with the source named under the result. It refuses to show a figure if its
  data is missing or out of range. No child-specific figure unless the source gives one.
- If no source qualifies, there is no tool: the checklist (section 8) scales what it can and
  `surv-food-how-much` carries what the sources say in words.

## 7. Rules this pack must agree with

- **Flame indoors.** `surv-carbon-monoxide`, `surv-portable-heaters`, `surv-wood-stoves-fireplaces`,
  `surv-generators`, `surv-fire` and `surv-heat-out` are checked and are not softened or reworded.
  `surv-food-cooking-no-power` must be written so that no reading of it permits a camp stove, grill, charcoal
  or generator indoors, and it quotes the owner topics word for word where it states their rules.
- **Cooking indoors on a kitchen range or a vented stove** (builder check). The checked topics forbid heating
  the house with a gas oven or range and forbid cooking on a stove or fireplace that is not vented; they do not
  say whether cooking on a gas or propane kitchen range lit by hand, or on a vented wood stove or fireplace, is
  allowed. `surv-food-cooking-no-power` becomes the owner of that rule and may say "you can cook on it" for
  either one **only where an opened source says so in words**, with every condition the source gives
  (ventilation, a working carbon monoxide alarm, never for heat), and with the two checked prohibitions quoted
  word for word beside it. If no opened source says it, the topic says cooking with flame is done outdoors and
  food is otherwise eaten cold, labels that as the app's own caution, and logs the question. Jordan's winter
  rule for a closed-up house (no-flame warmth first) applies during a fallout sheltering period only: the
  cooking topic says so in one sentence and links `surv-fallout-shelter-living`, which governs then. Whatever
  the outcome, the question is logged for Jordan as the first item of this pack.
- **Water pack.** Boiling times, bleach doses, the two household bleach mixes and the water amounts stay exactly
  as checked and are not restated: link.
- **Stomach illness.** `surv-stomach-illness-in-a-group` owns who stays away from food and for how long (D32).
- **Game temperature.** `surv-field-dressing-game` says 165°F for all wild game (D10). The cooking-temperature
  table in `surv-food-cooking-no-power` must not contradict it.
- **Fallout.** `surv-fallout-water-and-food` owns food after fallout; food topics link to it and do not restate.
- **One rule, one owner.** Fridge and freezer hold times: the hub. What to throw out: `surv-food-still-good`.
  Cooking temperatures: `surv-food-cooking-no-power`. Storage and shelf life: `surv-food-storage`. Amounts to
  store: `surv-food-how-much`. Infant feeding: `surv-food-babies-children`. Botulism signs:
  `surv-food-poisoning`. Other topics quote word for word or link.
- **No officials, no stores.** Official guidance assumes help returns in days. Each topic states the official
  rule first, then what the sources say for a longer period; anything beyond the sources is labelled as the
  app's own caution and logged.
- **Standing rules:** no 911 or dial button; New York named where state rules apply, as applying in normal
  times; never the home town; no internal wording in user-visible text.

## 8. Checklist and diagrams

- **Checklist `pantry`:** from the Ready.gov, FEMA and Red Cross "Food and Water in an Emergency", USDA and
  extension lists as opened: kinds of food, manual can opener, cooking and eating gear, fuel by link in the
  topic (checklist items carry no links), infant items. Quantities scale with people and days only where a
  source gives a per-person or per-person-per-day figure; otherwise plain text. The "Your group" box shows Days
  only if some item is per day (v7.4 behaviour).
- **Diagrams**, drawn after the text is checked and from it, each reviewed by someone who looks at the image
  before any text; one not recognisable without its caption is not shipped. Candidates, each only if the text
  supports it: fridge and freezer in a power cut (doors shut, hold times, thermometer); cans to throw out
  (bulging, leaking, badly dented) only if a source describes them precisely enough to draw; a drying setup
  only if a source describes one.

## 9. Batches and sources

**Batches** (writer, independent reviewer, fix, re-check; then diagrams, whole-pack read, final drive of the
built app at 360x640):

- **A, food safety core, first and alone:** `surv-food-power-out`, `surv-food-still-good`,
  `surv-food-cooking-no-power`, `surv-food-poisoning`. Its report also records the **Tool gate** and the
  **Botulism protocol gate** findings.
- Then in parallel in separate git worktrees, each with a reserved range of question numbers:
  - **B:** `surv-food-how-much`, `surv-food-storage`, `surv-food-when-short`, checklist `pantry`.
  - **C:** `surv-food-clean-kitchen`, `surv-food-babies-children`, `surv-food-preserving`.
  - **P (only if the gate passes):** the `botulism` protocol.

**Sources.** Primary: USDA FSIS (power outages, safe temperatures, shelf-stable food, "Keep Food Safe" pages);
FoodSafety.gov (the refrigerator and freezer charts); CDC (food safety, botulism, infant and toddler nutrition,
infant feeding in emergencies, choking hazards); FDA (food and water safety during power outages and floods,
infant formula); Ready.gov and FEMA/Red Cross *Food and Water in an Emergency*; National Center for Home Food
Preservation and USDA *Complete Guide to Home Canning* (for the warning, not a procedure); state extension
services (Cornell Cooperative Extension first, then others) for storage, shelf life and preserving; NYS
Department of Health and NYS Agriculture and Markets; WIC and American Academy of Pediatrics pages for young
children; US Army field manuals only for points civilian sources do not cover, named with their year.

Every rule in v7 design section 6 applies. Where sources disagree, the more cautious one is used and the
question is logged in `docs/decisions-for-jordan.md` section D from **number 117**. Web research uses built-in
search and fetch only; the Firecrawl and Bright Data connectors are not used; each fetched page is confirmed to
be the page asked for; nothing is written from memory when a page fails to load.

**Search (the v7.4 lesson).** New pages index after all older pages. Keywords stay narrow. Before the final
review, the on-screen first three for the 29 pinned queries and for everyday food words ("food", "water",
"cook", "fire", "stove", "burn", "sick", "vomiting", "baby", "choking", "milk", "can", "salt", "ice") are
compared with the v7.4 release and any displaced older result is fixed or ruled on. The first-search speed
tests must pass on an idle machine without loosening.

## 10. Calls made (Jordan can overrule)

1. Ships as **v7.5**. Ten new topics, one checklist, up to three diagrams; a planner and a botulism protocol
   only if their gates pass.
2. **Food from the land is v7.6** (Jordan). The three v7 food topics stay under Basics until then. Cost: the
   Food category on the home screen holds only at-home topics for one release.
3. **No canning procedure of any kind.** Nobody in the group cans; low-acid canning done wrong causes botulism;
   and a phone page is not a tested recipe. The preserving topic explains why, points to the USDA guide by
   name for someone who wants to learn in normal times, and covers handling home-canned food from others. Cost:
   a household that already owns a pressure canner gets no help from the app.
4. **Preserving is only what an official source teaches a beginner.** If the sources for salting, curing or
   smoking give no safe beginner method, those sections say so and stop. Cost: the preserving topic may be
   short.
5. **Gardening, livestock and root cellars are out** of this release (Jordan did not know whether anyone
   gardens). Logged under Deferred.
6. No food topic is ever hidden by a filter.
7. The hub is `surv-food-power-out`, because that is the moment someone opens the app in a hurry; "how much to
   store" is the topic people should read first in normal times and is linked first from the hub.
8. Existing checked topics gain at most one link block each and are not reworded.
9. Calorie and weight targets appear only as a source states them; the app derives none.
10. Questions that would have been asked of Jordan during the build are settled by the cautious option and
    logged in `docs/v7.5-rulings.md` with their cost if wrong.

11. **Cooking on a gas range or a vented wood stove is allowed only as an opened source allows it** (builder
    check; section 7). Not asked of Jordan because he had said to move forward; cost if the sources are silent:
    weeks of outdoor cooking and cold food in winter, which the app will state plainly rather than leave people
    to improvise.

## 11. Left to the builder

Section order and wording inside each topic; final ids and titles within the scope above; which optional
diagrams earn a place; test names; the planner's layout if it ships (the Water planner is the pattern); how the
reserved question-number ranges are split.
