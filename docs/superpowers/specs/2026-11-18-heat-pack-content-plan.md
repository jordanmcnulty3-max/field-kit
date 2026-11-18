# Heat, shelter and winter pack: content plan (v7.3)

Date: 2026-11-18. Second content pack under `2026-11-17-v7-survival-knowledge-center-design.md` (the v7 design),
whose sections 5 and 6 bind everything here. Built the same way as the water pack
(`2026-11-18-water-pack-content-plan.md`, `../plans/2026-11-18-water-pack.md`). The calls made here are in section 9.

## 1. Intent

A Central New York winter with no grid kills in two ways: cold, and the things people do to get warm (carbon
monoxide, house fires, fuel accidents). The group needs to keep people and houses alive through weeks without
utility heat, using what they actually own, and to stay warm outdoors when they have to move or camp.

Jordan (2026-11-18): the group's homes have a mix of furnaces, wood stoves, fireplaces, kerosene and propane
heaters, and generators. So every one of those gets its own full treatment; none is a footnote.

## 2. Goals, non-goals, anti-goals

- Goals: a person can find, in under a minute, how to run each heat source without poisoning or burning the
  house; what to do in the first hour the heat is out; how to dress, sleep and shelter in real cold.
- Non-goals: summer heat without power (Town hazards pack); walking on lake ice and winter travel on foot
  (Moving pack); cooking without power beyond what a heat source implies (Food pack); long-term wood-lot
  management, chainsaw technique, building or installing a stove or chimney.
- Anti-goals: any instruction that makes an unsafe improvisation sound acceptable (burning anything indoors that is not made and rated for indoor use,
  oven or grill as a heater, back-feeding a house from a generator, alcohol or candle "heaters" presented as
  safe); a number nobody sourced; treatment advice that competes with the Emergency protocols.

## 3. Approaches

1. **One release, built like the water pack (chosen).** All topics, the tool, checklists and diagrams ship
   together as v7.3 after batch reviews and one whole-pack read. Costs a longer build; gains the whole-pack read,
   which is what caught contradictions between topics in v7.2 (here: every topic that burns something must
   agree with the carbon monoxide topic).
2. Two releases: home heating first, outdoors second. Ships the home safety content sooner, but the whole-pack
   read would run twice and Fire and Shelter would sit half-updated in between.
3. Safety topics only (carbon monoxide, generators, heaters), the rest later. Smallest, but leaves the
   "what do I do in the first hour" and clothing topics out for the first winter.

## 4. Topics (category `heat`)

`surv-fire` and `surv-shelter` move from Basics to this category and are deepened; their ids do not change.

| Id | Title | Covers |
|---|---|---|
| `surv-heat-out` (new) | Stay warm when the heat is out | Do first; pick one room and close off the rest; windows, doors, floors; body heat and bedding; when the house is too cold to stay and where to go; who is most at risk (infants, older people); what a furnace needs to run (power, fuel) and bringing it back; links to every heat-source topic |
| `surv-carbon-monoxide` (new) | Carbon monoxide and burning fuel indoors | What makes it; never-indoors list (generator, grill, camp stove, oven as heater); alarms (where, battery backup, what to do when one sounds); symptoms only as a pointer; links to the Emergency protocol instead of restating treatment |
| `surv-wood-stoves-fireplaces` (new) | Wood stoves and fireplaces | Before lighting (chimney, damper, clearances); what to burn and never burn; running it overnight; creosote and chimney fires and what to do in one; ash disposal; screens, children; a fireplace as a net heat source |
| `surv-portable-heaters` (new) | Kerosene and propane heaters | Indoor-rated only; the right fuel (grade, never gasoline); ventilation as the source gives it; clearances; refuelling; never while asleep or unattended as sources state; tip-over and low-oxygen shut-offs; cylinders indoors |
| `surv-generators` (new) | Generators | Where to run it (distance, direction); never in a garage, basement or porch; back-feeding and transfer switches; running a furnace or well pump from one; cords and loads; refuelling; rain and snow; rationing run time |
| `surv-store-fuel` (new) | Store fuel safely | Gasoline, kerosene, propane, heating oil: containers, where, how much the sources allow, shelf life and stabiliser only as sources support, keeping them apart, fire extinguisher |
| `surv-firewood` (new) | Firewood | Seasoned and green; drying time and moisture as sources give them; species common in the Northeast; splitting and stacking; where to keep it; how much a source says a winter takes; New York's firewood movement rule (normal times) |
| `surv-unheated-house` (new) | Protect an unheated house | Pipes: keep, drip or drain; shutting off and draining the system; traps; water heater; stored water and food that must not freeze (the item carried from v7.2: only what a source supports); ice dams and roof snow only as sources support; coming back (links Water in winter, Water already in your house) |
| `surv-dress-for-cold` (new) | Dress for the cold | Layers and what each does; cotton; hands, feet, head; staying dry, venting before sweating; wet clothes; children; improvising insulation |
| `surv-sleep-warm` (new) | Sleep warm | Ground insulation first; bags and blankets; sharing a room or shelter; hot water bottle; eating and drinking before sleep as sources support; what not to do (burners in a closed tent or room); indoors and outdoors |
| `surv-fire` (deepen) | Fire | Existing checked text kept; adds wet-weather and snow fires, fire on snow, fire lays for heat and for cooking, reflectors, carrying fire-starting kit; ferro rod text unchanged (push the striker down) |
| `surv-shelter` (deepen) | Shelter | Existing checked text kept; adds tarp lean-to in detail, debris shelter, snow shelters (trench, quinzhee or cave only as far as a source gives dimensions and ventilation), vehicle and building as shelter; fire and stove dangers in shelters |
| `surv-winter-storms` (new) | Winter storms | Northeast types (lake-effect snow, nor'easter, ice storm, blizzard); watches and warnings; before, during, after; shovelling and exertion; downed lines; stranded in a vehicle (stay with it, exhaust pipe, running the engine as the source gives it) |
| `surv-wind-chill` (new) | Wind chill and cold danger | What wind chill is and is not; the National Weather Service chart and frostbite times; wet and wind; who is at risk; links to the tool and to the Emergency protocols for hypothermia and frostbite |

**Tags.** Home-heating topics carry no `where` or `when` tag: a wrong filter must never hide them.
`surv-shelter` keeps its existing `where` tags. `when: cold` is used only on `surv-wind-chill`,
`surv-winter-storms`, `surv-dress-for-cold` and `surv-unheated-house`, and only if the whole-pack reviewer agrees
nothing safety-critical is hidden under Warm. Added to the protected `ALWAYS` list in
`tests/test_survival_home.py`: `surv-heat-out`, `surv-carbon-monoxide`, `surv-wood-stoves-fireplaces`,
`surv-portable-heaters`, `surv-generators`, `surv-store-fuel`.

**Batches** (writer, independent reviewer, fix, re-check; v7 design section 6):
A carbon-monoxide, generators, portable-heaters, store-fuel ·
B heat-out, wood-stoves-fireplaces, firewood, unheated-house ·
C dress-for-cold, sleep-warm, wind-chill, winter-storms ·
D fire, shelter.
Batch A goes first because every later topic must agree with it.

## 5. Tool

**Wind chill** (`u:windchill`): air temperature (°F) and wind (mph) in; wind chill and the National Weather
Service frostbite-time band out, plus a link to the topic and the two Emergency protocols.

- Wind chill is computed with the NWS 2001 formula, only inside the range NWS states for it; outside it the
  tool says so and shows nothing. Tests check the formula against every cell of the NWS chart.
- Frostbite bands come from a table transcribed from the NWS chart into `src/tooldata/windchill.json` (sourced,
  validated and release-gated like `water.json`), not from a fitted formula. Between chart cells the tool uses
  the colder temperature and the higher wind, so it never understates danger.
- The tool accepts only what the NWS chart covers (its temperature and wind range, read from the chart when it
  is opened). Outside that it says "Off the National Weather Service chart" and shows no figure and no band, so
  an unsourced band can never appear. `validate_tooldata` is extended to accept the band table.
- If the reviewer cannot confirm the band boundaries from the chart itself, the bands are dropped and the tool
  shows wind chill with NWS's written thresholds only.
- No °C input and no fuel planner in this pack (section 9).

## 6. Checklists

- `home-heat-kit`: carbon monoxide alarms with battery backup, smoke alarms, fire extinguisher, fuel by type in
  approved containers, spare wicks and mantles only if a source lists them, blankets and sleeping bags, plastic
  sheeting and tape, flashlights, and so on. Quantities scale with the group
  (`qty: { amount, unit, per }`) only where a source gives a per-person figure.
- `vehicle-winter-kit`: from the NWS, Ready.gov and NYS lists.

## 7. Diagrams

Drawn after the text is checked, from the checked text, each reviewed against it; one not recognisable without
its caption is not shipped.

- Redraw `shelter-tarp` as a lean-to and `fire-ferro` as push-the-striker-down (both removed in v7).
- New, if the text supports them: generator placement (distance, exhaust direction, never in the garage);
  heater and stove clearance; one warm room; layering; snow trench or quinzhee with its vent; exhaust pipe
  clear on a stranded car.

## 8. Sources

Primary: CDC (winter weather, carbon monoxide, generators, power outages), CPSC (generators, portable heaters,
CO alarms), NFPA and the US Fire Administration (heating fires, clearances, chimneys, ashes), FEMA and Ready.gov
(winter weather, power outages), National Weather Service (wind chill, winter storm terms, vehicles), Red Cross,
EPA Burn Wise (wood stoves, firewood), US Department of Energy, OSHA and NIOSH (cold stress, clothing), NYS DEC
(firewood movement, open burning), NYS DHSES and NYS Department of Health, NYSERDA, Cornell Cooperative Extension
and other northern extensions (firewood, pipes, unheated houses), US Army cold-weather and survival manuals
(public domain) for outdoor shelter, clothing and fire. Manufacturer manuals only to confirm that an instruction
is "follow the manual", never as the source of a general number.

Every rule in v7 design section 6 applies. Where sources disagree, the more cautious one is used and the question
is logged in `docs/decisions-for-jordan.md` section D from number 37. Web research uses built-in search and fetch
only; the Firecrawl connector is not used.

## 9. Calls made (Jordan can overrule)

1. Ships as **v7.3**; v7.1 stays reserved for iPhone support.
2. Fourteen topics (twelve new, two deepened), one tool, two checklists.
3. Home-heating topics are never hidden by a filter.
4. No fuel planner (how much wood, kerosene or gasoline for N days): consumption depends on the appliance and
   the house, and no agency prints a per-day figure. Cost if wrong: the group estimates its own burn rate.
5. Wind chill tool is °F and mph only, matching the NWS chart. Cost: metric users convert by hand.
6. Summer heat, lake ice and winter foot travel wait for their packs (section 2).
7. Hypothermia, frostbite, carbon monoxide poisoning and burns are links to the Emergency protocols; any
   conflict found with a checked protocol is logged, not edited (standing rule).
8. No guided flow in this pack; urgent topics use the Do first box.
9. Existing checked text in Fire, Shelter, Priorities and Water in winter is not reworded unless a source
   requires it; new topics must agree with it or log the conflict.

10. **Kerosene and propane heaters get operating guidance, not a blanket "don't"** (pending Jordan, see below).
    The group owns them. The topic states the strictest conditions any opened agency source sets (indoor-rated
    only, fuel, ventilation, never asleep or unattended), names any agency that says not to use them indoors at
    all and any New York restriction found, and never softens the existing Shelter line about heaters and sleep.
11. Shelter stays an outdoor topic with its `where` tags. Sheltering in a building or a vehicle is written in
    `surv-heat-out` and `surv-winter-storms`, which no filter hides.
12. Heat sources Jordan did not name: a natural gas furnace is covered under "what a furnace needs" in
    `surv-heat-out`; electric heaters on a generator get a short section in `surv-generators`; pellet stoves (need
    power) and vent-free gas fireplaces get a short note in `surv-wood-stoves-fireplaces` and
    `surv-carbon-monoxide`. Gas leaks and shutting off gas wait for the Town hazards pack.

## 10. Left to the builder

Section order and wording inside each topic; which optional diagrams earn a place; test names; whether the tool
uses sliders or typed fields (typed fields with steppers is the existing planner's pattern).
