# Water and sanitation pack: content plan (v7.2)

Date: 2026-11-18. First content pack under `2026-11-17-v7-survival-knowledge-center-design.md` (the v7 design),
whose sections 5 and 6 bind everything here. Jordan said "Continue" after v7 shipped; per the v7 design a pack's
plan goes to him only if it raises a decision that is his. The calls made here are listed in section 7.

## 1. Intent

When the taps and sewers stop for weeks, in a Central New York winter or summer, at home or on the move, the group
needs to know how much water to hold, where more comes from, how to make it safe, and how to stay clean enough
that nobody gets the stomach illness that follows bad sanitation. Dirty water and poor sanitation are what make
people sick first in a long outage, which is why this pack is first.

## 2. Topics (category `water`)

Existing topics move from Basics to this category and are deepened; their ids do not change.

| Id | Title | Covers |
|---|---|---|
| `surv-water-how-much` (new) | How much water you need | Per person per day for drinking, cooking and washing; when to hold more (heat, illness, pregnancy and nursing, children, pets); how long to plan for; rationing rule (do not ration drinking water); weight and space |
| `surv-water-store` (new) | Store water at home | Containers that are safe and ones that are not; cleaning and sanitizing a container; filling, sealing, labelling, rotating; where to keep it; freezing; commercial bottled water |
| `surv-water-in-the-house` (new) | Water already in your house | Do first when the taps stop (protect what is in the pipes); water heater, pipes, ice, toilet tank; what is not drinkable (toilet bowl, radiators, waterbeds, pools and spas for drinking); shutting the main valve |
| `surv-find-water` (deepen) | Find water outside | Rain and roof catchment, snow and ice, lakes, streams, springs, wells; Northeast hazards (harmful algal blooms, flood water, farm and industrial runoff, road salt); choosing the cleanest source; carrying it |
| `surv-make-water-safe` (deepen) | Make water safe | Order of methods; boiling; bleach for small and large volumes; chlorine dioxide and iodine; filters and what each rating removes; UV and sunlight methods only as a source supports them; distillation; what no method fixes; keeping treated water clean |
| `surv-water-winter` (new) | Water in winter | Melting snow and ice (fuel cost, never eat snow), keeping stored water and containers from freezing, frozen pipes, drinking enough in the cold; tagged `when: cold` |
| `surv-wells-without-power` (new) | Wells without power | Getting water from a private well with no electricity; disinfecting a well after a flood; tagged `where: rural` |
| `surv-toilet-no-water` (new) | Toilets when the water is off | Do first; when you can still flush with carried water; when you must not (sewer backup); twin-bucket and bag toilets; storing and disposing of waste; septic systems |
| `surv-latrines` (new) | Latrines and cat holes | For camps and for moving: cat holes, trench latrines, distances from water, camp and trail, depth, closing them; group camps; winter ground |
| `surv-handwashing` (new) | Wash hands without running water | When, how, how long; a handwashing station from a jug; hand sanitizer and its limits; soap and water over sanitizer after the toilet |
| `surv-clean-and-disinfect` (new) | Clean and disinfect | Washing dishes with little water; bleach solutions for surfaces and for water containers (strengths from sources, never mixed with ammonia or acids); laundry and bedding of a sick person |
| `surv-garbage-and-greywater` (new) | Garbage and dirty water | Storing garbage when there is no collection; pests; greywater; burning (state rule in normal times); diapers and medical waste |
| `surv-stomach-illness-in-a-group` (new) | Stop stomach illness spreading | Why it follows bad water and sanitation; isolating the sick person's toilet and washing; who must not prepare food; fluids; links to the Emergency protocols for vomiting and diarrhoea and dehydration instead of restating treatment |

Each topic carries `where`/`when` tags only where it truly applies to some settings and not others; anything
safety-critical stays visible under every filter (the v7 test enforces this for the core topics; this pack adds
`surv-make-water-safe`, `surv-toilet-no-water` and `surv-handwashing` to that list).

## 3. Tool and setting

- **Group setting** (v7 design 5.4): people in the group and days to plan for, saved on the phone as `group`
  (`{ people, days }`), included in backup. Set from the water planner and from any checklist that scales.
- **Water planner** (`u:water`): people and days in, total drinking-and-cooking water out, with the extra for
  the conditions a source names (hot weather, illness, pregnancy or nursing, pets), shown in gallons and litres,
  as counts of common containers, and as weight. All its numbers live in a data file with sources
  (`src/tooldata/water.json`), validated and release-gated like a topic, so the planner cannot ship a number
  nobody sourced.

## 4. Checklists

- `home-water-store`: containers, bleach, a way to boil, a filter, and so on, with quantities that scale with
  the group setting where a source gives a per-person figure.
- `sanitation-kit`: twin-bucket toilet kit, bags, cover material, soap, sanitizer, bleach, gloves.

Checklist items gain an optional quantity (`perPersonDay` or `perPerson`, amount and unit); the page shows the
total for the saved group.

## 5. Diagrams

Drawn after the text is checked, from the checked text, and reviewed against it: the bucket toilet pair, a jug
handwashing station, latrine and cat-hole distances and depth, draining a water heater, and `water-safe`
restored with the 5,000 ft label. A diagram not recognisable without its caption is not shipped.

## 6. Sources

Primary: CDC (water, sanitation and hygiene in emergencies; making water safe; handwashing), EPA (emergency
disinfection; private wells), FEMA and Ready.gov (water storage and amounts), Red Cross, NYS Department of
Health and NYS DEC, Cornell Cooperative Extension and other extensions (wells, storage), US Forest Service and
Leave No Trace (cat holes, distances), WHO and the Sphere handbook for group sanitation where US agencies are
silent, US Army field sanitation and survival manuals as a second source only. Every rule in v7 design section 6
applies, including independent review of each batch and the v7 water decisions already made (boil 1 minute,
3 minutes above 5,000 ft; 8 drops of 5% to 9% bleach per gallon; cautious wording on chlorine dioxide).

## 7. Calls made (Jordan can overrule)

1. This pack ships as **v7.2**; v7.1 stays reserved for iPhone support.
2. Thirteen topics, two checklists, one tool, as listed. Flood water at home and long-term water infrastructure
   (rain barrels as a system, cisterns) wait for the Town hazards and Staying put packs.
3. No guided step-by-step flow in this pack; urgent topics use the Do first box.
4. Planner numbers live in a sourced data file and are release-gated.
5. Oral rehydration solution recipes are not written here; the pack links to the Emergency protocols, and any
   gap in them is logged for a medical professional.
6. The filter-rating detail deferred from v7 (1 micron absolute for parasites) is covered here.

## 8. Not in this pack

Radiation in water (pack 3), food-related hygiene beyond dishes (pack 4), long-term rain harvesting and
cisterns (pack 6), flood clean-up (pack 8).
