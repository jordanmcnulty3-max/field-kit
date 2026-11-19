# Radiation and fallout pack: content plan (v7.4)

Date: 2026-11-18. Third content pack under `2026-11-17-v7-survival-knowledge-center-design.md` (the v7 design),
whose sections 5 and 6 bind everything here. Built the same way as the heat pack
(`2026-11-18-heat-pack-content-plan.md`, `../plans/2026-11-18-heat-pack.md`, whose "Content contract" is the
writer and reviewer procedure). Calls made here are in section 10.

## 1. Intent

Jordan (2026-11-17): radiation and fallout guidance covering **preventative measures and addressing exposure**,
inside a knowledge center for a long grid-down or wartime period in New York and the Northeast, in town and in
the woods, staying put or moving.

Jordan (2026-11-18), in the brainstorm:

- **Events covered: nuclear weapon fallout and dirty bomb.** A nuclear plant accident is **not** covered in this
  pack (section 2, deferred).
- **No one in the group is assumed to own a radiation meter.** The pack is written for people without one and
  leaves a clear place to add meter guidance later.
- **Approach A** (section 3): urgent actions sit in a topic's Do first box; exposure care is added to Emergency
  as protocols.
- The topic list in section 4 "looks good for now".

Fallout kills people who are outside or poorly sheltered in the first hours, and the protective actions are few
and simple. The pack's job is to make those few actions findable in seconds and to stop the dangerous mistakes:
going outside too early, fleeing through fallout, trusting pills, and sealing a room with something burning in it.

## 2. Goals, non-goals, anti-goals

- **Goals:** a person can find in seconds what to do when a detonation or fallout warning happens; where in a
  given building to shelter; roughly how long to stay in and what changes that; how to come in from outside
  without carrying fallout in; what water and food are usable; how to keep a closed-up house liveable in a
  Central New York winter without carbon monoxide; what a dirty bomb is and how it differs; what potassium
  iodide does and does not do; what to have ready beforehand; how to clean a contaminated person and recognise
  and care for radiation sickness when no hospital is reachable.
- **Non-goals:** nuclear power plant accidents, emergency planning zones and official plant alerts (deferred;
  Jordan's decision, logged in the rulings file with its cost); potassium iodide doses (see section 10, call 3);
  building purpose-made or dug fallout shelters; blast and fire effects beyond the few "during" actions current
  federal guidance gives; electromagnetic pulse and protecting electronics (Comms pack); long-term farming,
  soil and livestock after fallout (Food pack, only if sourced); radiation meters as a built feature (section 6).
- **Anti-goals:** any wording that tells someone it is "safe" to go out on the strength of a time rule alone;
  a dose, exposure limit or pill dose nobody sourced; presenting potassium iodide, masks or any product as
  protection against fallout radiation; advice to seal a room that could be read as overriding the carbon
  monoxide rules; treatment text in Survival that competes with an Emergency protocol; anything that names the
  group's home town or its distance from a target or plant.

## 3. Approaches

1. **A: Survival topics with a Do first box, plus two Emergency protocols (chosen by Jordan).** The Fallout
   warning topic opens with up to five numbered actions, the pattern the carbon monoxide topic uses.
   Decontamination and radiation sickness are step-by-step Emergency protocols. No change to the step player.
   Cost: the warning reads as a short list, not one step per screen.
2. B: as A, and "Fallout warning" also exists as an Emergency protocol. One step per screen and visible on the
   Emergency home, but the same rules would live in two places (how the stranded-car rule drifted in v7.3) and
   Emergency would stop being purely medical.
3. C: make the step player work inside Survival. Cleanest long-term, but its Back-button logic failed three
   reviews in v6 and reopening it puts 54 protocols at risk for one topic.

One release (v7.4), built like the heat pack: all topics, protocols, checklist and diagrams ship together after
batch reviews and one whole-pack read.

## 4. Survival topics (category `radiation`, already defined in `src/survival.js` and `tools/validate.py`)

All ten are new. Ids are proposals; the builder may adjust wording of titles but not scope.

| Id | Title | Covers |
|---|---|---|
| `surv-fallout-warning` | Fallout warning: what to do now | **Hub; leads the category.** Do first: the few actions (get inside, deepest or most central place, stay in, clean off, listen). The "during" actions current guidance gives for the flash and blast. How long you have before fallout arrives, as sources state it. Do not flee by car or on foot through fallout; family stays where it is. Links to every other topic and both protocols |
| `surv-fallout-where-to-shelter` | Where to shelter from fallout | What makes a good shelter (mass and distance from roofs and outer walls); ranking of places a source ranks (basement, middle floors of large buildings, wood-frame house, vehicle); best spot inside a house; moving once to better shelter only as sources allow; caught outdoors, in a car, or in the woods with no building |
| `surv-fallout-how-long` | How long to stay in | Why time matters (fallout weakens fast); the sheltering period sources give; what to do when **no official instruction ever comes** (only as a source supports it, otherwise the app's own caution, labelled and logged); short necessary trips outside; the decay rule as text or table if section 6 allows; "If you have a meter" (section 6) |
| `surv-fallout-shelter-living` | Living in a closed-up house | Closing windows, doors, dampers, fans and vents as sources give it; **air and anything that burns** (owner of the sealing rule, section 7); heat in winter; light; toilets and water use inside (links to water pack topics); pets; sleeping; keeping out dust when someone must go out |
| `surv-fallout-coming-inside` | Coming in from outside | Where to undress; bagging clothes; washing; what not to use; pets; people who cannot shower; keeping the shelter area clean. A summary that links to the Decontamination protocol for the steps |
| `surv-fallout-water-and-food` | Water and food after fallout | What is usable (sealed, covered, indoors) and what is not; wiping containers; stored water (must agree with Store water at home and Water already in your house); what boiling and bleach do **not** do for fallout, only as a source states; wells, rain and surface water; garden produce, milk and game only as sources support |
| `surv-fallout-leaving` | Leaving and moving after fallout | When leaving beats staying, as sources give it; picking a direction and route; covering up and cleaning off after; travelling on foot or by vehicle through a contaminated area; arriving at another household (decontaminate first) |
| `surv-dirty-bomb` | Dirty bomb | What it is and how it differs from a nuclear weapon; the danger is mostly the blast; what to do near one and farther away; cleaning off; it does not create fallout over a region |
| `surv-potassium-iodide` | Potassium iodide: what it does and does not do | Protects only the thyroid, only from radioactive iodine; what the CDC says about its use after a nuclear detonation; who it is meant for and its risks as sources state; **no dose table** (section 10, call 3); not a substitute for shelter; iodised salt and iodine products are not substitutes if a source says so |
| `surv-fallout-get-ready` | Get ready for fallout | Choosing the shelter spot in each home now; supplies (links to the checklist, water store and heat kit); a radio; a family plan for being apart; what is not worth buying, only as sources support |

**Tags.** No radiation topic carries a `where` or `when` tag, and all ten keys are added to the protected
`ALWAYS` list in `tests/test_survival_home.py`: a filter must never hide any of them.

**Existing topics.** `surv-priorities`, `surv-shelter`, `surv-heat-out`, `surv-carbon-monoxide`,
`surv-water-store` and `surv-water-in-the-house` may each gain **one link block** to the relevant radiation
topic. Their checked text is not reworded (section 7).

## 5. Emergency protocols

Two new protocols under the Emergency content rules (v6 design and `tools/validate.py`), written and reviewed
as their own batch. Both are medical content: every step, number and "never" comes from an opened source (CDC
radiation emergencies, HHS REMM, FDA, NYS Department of Health, Red Cross), and every judgement the sources
leave open goes to `docs/decisions-for-jordan.md` marked for a medical professional.

| Id | Title | Covers |
|---|---|---|
| `radiation-decontamination` | Radiation decontamination | Cleaning yourself and cleaning another person: clothing off, bagging, washing with and without a shower, wounds, eyes and hair, what never to do, children, pets, the helper's own protection. Life-saving care is never delayed for decontamination, if the sources say so |
| `radiation-sickness` | Radiation sickness | Recognising it (what the sources list, and the meaning of early vomiting only as a source states it); what a lay person can do without a hospital (fluids, infection precautions, burns and wound care by link); what needs medical care; that a person who was exposed is not themselves dangerous to others once cleaned, if a source says so |

- Category and tier are the builder's choice within the existing set; neither is `advanced` unless the
  sources describe a procedure.
- `burns`, `vomiting-diarrhea`, `wound-care`, `dehydration` and `shock` are **linked, never edited**. Any
  disagreement between a radiation source and a checked protocol is logged for Jordan, not resolved in text.
- Survival topics link to these protocols instead of restating care (v7 design 6.4).

## 6. Tool and meter

**Shelter-time guide: decided after the sources are opened, not now.**

- It ships only if a current federal source (FEMA, HHS REMM, CDC, EPA or a national laboratory document FEMA
  publishes) states the fallout decay rule **as text or a table**, and the batch reviewer confirms it.
- If it ships: input is hours since the detonation; output is how much weaker fallout radiation is than at one
  hour, from a table in `src/tooldata/fallout.json` (sourced, validated and release-gated like `water.json`),
  rounded so it never overstates the drop. It shows a fraction, never a dose, never the word "safe", and always
  the line that only a meter or an official can say what the level actually is. Outside the range the source
  gives, it shows nothing.
- If the rule cannot be confirmed as text, there is no tool, and `surv-fallout-how-long` carries only the
  sheltering periods the sources state. This is the v7.3 wind chill lesson.

**Meter.** No meter input anywhere in v7.4. `surv-fallout-how-long` gets a section "If you have a meter" only if
an official source gives readings a member of the public can act on; otherwise the section says a meter is the
only way to know the level and that the app does not yet cover reading one, and the gap is logged as deferred.

## 7. Rules this pack must agree with

- **Sealing against fallout versus carbon monoxide.** `surv-carbon-monoxide`, `surv-portable-heaters`,
  `surv-wood-stoves-fireplaces`, `surv-generators` and `surv-heat-out` are checked and are not softened or
  reworded. `surv-fallout-shelter-living` owns the rule for a closed-up house and must be written so that no
  reading of it permits burning anything in a sealed room. Where a radiation source and a combustion source
  cannot both be followed (for example, heating a closed-up house in winter with a kerosene heater), the topic
  states both, takes the reading that cannot kill by carbon monoxide, and the question is logged for Jordan.
  It is written and reviewed in the first batch because every later topic leans on it.
- **Water pack.** Stored water, the water heater tank, bleach doses and boiling times stay exactly as checked.
  The radiation topics add only what sources say about fallout and water.
- **One rule, one owner.** Sheltering period: `surv-fallout-how-long`. Where to shelter:
  `surv-fallout-where-to-shelter`. Cleaning-off steps: the `radiation-decontamination` protocol. Closed-house
  air: `surv-fallout-shelter-living`. Other topics quote word for word or link.
- **"Stay tuned" with nobody broadcasting.** Federal guidance ends each step with "unless officials say
  otherwise". The pack is for a period when there may be no officials to hear. Each topic states the official
  rule first, then what the sources say when no instruction comes; anything beyond the sources is labelled as
  the app's own caution and logged.
- **Standing rules:** no 911 or dial button; no instructions for weapons or devices (the dirty bomb topic
  describes effects and response only, nothing about construction or materials); New York named where state
  rules apply, as applying in normal times; never the home town; no internal wording in user-visible text.

## 8. Checklist and diagrams

- **Checklist `fallout-shelter-kit`:** from the Ready.gov, CDC and NYS lists as opened: radio (battery or
  crank) and batteries, water and food by link to the existing lists, plastic bags for clothing, soap, clean
  clothes, plastic sheeting and tape only if a source lists them for this purpose, flashlights, medicines,
  and so on. Quantities scale with the group only where a source gives a per-person figure. Potassium iodide
  appears only if a source lists it for this event, with the topic's caveat.
- **Diagrams**, drawn after the text is checked and from it, each reviewed by someone who looks at the image
  before the caption; one not recognisable without its caption is not shipped:
  - where to shelter in a house and in a larger building (best and worst places);
  - coming inside: undress, bag, wash;
  - fallout weakening over time, only if the decay rule is confirmed for section 6.

## 9. Batches and sources

**Batches** (writer, independent reviewer, fix, re-check; then diagrams, whole-pack read, final drive of the
built app at 360x640):

- **A, safety core, first and alone:** `surv-fallout-warning`, `surv-fallout-where-to-shelter`,
  `surv-fallout-how-long`, `surv-fallout-shelter-living`.
- Then in parallel in separate git worktrees, each with a reserved range of question numbers:
  - **B:** `surv-fallout-coming-inside`, `surv-fallout-water-and-food`, `surv-fallout-leaving`.
  - **C:** `surv-dirty-bomb`, `surv-potassium-iodide`, `surv-fallout-get-ready`, checklist.
  - **P:** the two Emergency protocols. `surv-fallout-coming-inside` is finalised after P so its summary
    matches the protocol.

**Sources.** Primary: Ready.gov (nuclear explosion, radiation emergencies, radiological dispersion device) and
its nuclear detonation safety flyers; FEMA *Planning Guidance for Response to a Nuclear Detonation*, third
edition; CDC radiation emergencies (sheltering, self-decontamination, potassium iodide, acute radiation
syndrome, dirty bomb FAQs); HHS REMM; FDA (potassium iodide); EPA (protective action guides, radiation
basics); NRC (dirty bomb fact sheet); NYS Department of Health and NYS DHSES; Red Cross. Older civil defence
publications (for example FEMA's 1985 *Protection in the Nuclear Age*) may be used only for points current
guidance does not cover, are named with their year in the source line, and never override a current source.

Every rule in v7 design section 6 applies. Where sources disagree, the more cautious one is used and the
question is logged in `docs/decisions-for-jordan.md` section D from **number 68**. Web research uses built-in
search and fetch only; the Firecrawl connector is not used; each fetched page is confirmed to be the page asked
for; nothing is written from memory when a page fails to load.

## 10. Calls made (Jordan can overrule)

1. Ships as **v7.4**. Ten new topics, two new protocols, one checklist, up to three diagrams, a tool only if
   section 6's condition is met.
2. **Nuclear plant accidents are deferred** by Jordan's choice of events. Cost: nothing in the app on plant
   alerts, evacuation zones or the one event where potassium iodide matters most. Logged in
   `docs/v7.4-rulings.md` under Deferred.
3. **Potassium iodide gets one short topic and no dose table.** CDC states that it will not protect against a
   nuclear detonation's health effects, and a medicine dose does not belong in Survival text. Cost if wrong: a
   group that holds the pills must read the package for the dose. If the opened FDA and CDC pages say fallout
   calls for it, this is reopened with Jordan before writing.
4. **No meter input in the tool or anywhere else** (Jordan: build so one can be added). Cost: a group that
   buys a meter gets no help reading it until a later release.
5. No radiation topic is ever hidden by a filter.
6. The hub is `surv-fallout-warning`, not a separate overview topic.
7. Existing checked topics gain at most one link block each and are not reworded.
8. Dug or purpose-built shelters are out. Cost: nothing for someone with days of warning and no basement.
9. Blast, heat and flash get only the "during" actions current guidance gives; no effects tables or distances.
10. The dirty bomb is one topic, with cleaning-off handled by link to the protocol.
11. **Caught outdoors with no building** (builder check): the US Army survival manuals may be used for that one
    case, named in the source line, including improvised cover they describe. Call 8 still excludes multi-day
    construction plans for purpose-built shelters. If no opened source covers it, the section says only to get
    to a building.
12. **What reopens call 3** (builder check): only an opened CDC or FDA page that tells the public to take
    potassium iodide after a nuclear detonation. General FDA dosing guidance for radioactive iodine does not.
    If the result is mixed, batch C proceeds with no dose table and the question is logged; it does not wait.
13. **If Ready.gov will not load** (it failed all through v7.3): the FEMA-hosted PDFs of the same guidance, the
    FEMA planning guidance, CDC and REMM stand in. A government-run web archive copy of a Ready.gov page is
    accepted only when a current CDC or FEMA page says the same thing, and its capture date goes in the source
    line. Otherwise the affected text shrinks to what the pages that did load state.
14. **Leaving shelter for a medical or other life-threatening emergency** is owned by `surv-fallout-leaving`,
    from whatever the sources say about fire, collapse and medical need. Both new protocols point to it and do
    not carry a competing rule of their own; existing protocols' evacuate lists are not edited, and any
    conflict is logged for Jordan.
15. **Checklist items carry no links** (the schema does not allow them and is not extended). Water and food
    links sit in `surv-fallout-get-ready`; food items a source lists appear in the checklist as plain text.

## 11. Left to the builder

Section order and wording inside each topic; final ids and titles within the scope above; protocol category;
which optional diagrams earn a place; test names; the tool's layout if it ships (typed field with steppers is
the existing pattern); how the reserved question-number ranges are split.
