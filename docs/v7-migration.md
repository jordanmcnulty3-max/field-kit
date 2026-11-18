# v7 Survival migration log

Step 1 of the two-step migration (spec section 5.3): the 14 v6 topics converted word for word to `src/survival/*.json`,
plus the new `surv-priorities` topic. `tests/test_survival_migration.py` reads the lists below, so keep the
`id || "text" || reason` line format. Every converted topic is `draft` until source-checked (Tasks 13 to 16).

## Deletions

Content that does not apply to the Northeast, removed at conversion (spec section 5.3, step 1). Each text is removed
from the old topic text exactly once; the test requires the rest to match word for word.

- surv-shelter || " and desert" || Heading "Snow and desert" becomes "Snow": the desert half of the section is dropped.
- surv-shelter || "In the desert, shade comes first. Two layers of material with an air gap between them are much cooler than one. Stay off the hot ground." || Desert shelter does not apply to the Northeast.
- surv-shelter || "Desert shade. The air gap keeps the sun-heated top layer from heating the space below." || Caption of the `shelter-desert` diagram, which is removed with its text.
- surv-navigation-without-a-compass || "Southern Hemisphere: point 12 o’clock at the sun. North is halfway between 12 and the hour hand." || Southern Hemisphere navigation text.
- surv-navigation-without-a-compass || "Southern Cross: extend the long axis of the cross about four and a half times its length, then drop straight down to the horizon for south." || Southern Cross navigation text; the Southern Cross is not visible from the Northeast.
- surv-navigation-without-a-compass || "The two bright Pointers beside the cross help confirm you have the real one, not the dimmer “false cross.”" || Caption of the `nav-cross` (Southern Cross) diagram, which is removed with the Southern Cross text. The figure file in figs/ is not deleted.
- surv-dangerous-animals || "Grizzly (brown) bear attack: leave your pack on, lie flat on your stomach with your hands clasped behind your neck, and play dead. If the attack continues, fight back hard." || No grizzly population in the Northeast (to be confirmed against a wildlife-agency source in the checking tasks).
- surv-dangerous-animals || "Mountain lions" || Heading of the mountain-lion section; no mountain-lion population in the Northeast (to be confirmed in the checking tasks).
- surv-dangerous-animals || "Don’t run or crouch. Make yourself look big, keep eye contact and back away slowly. If attacked, fight back." || Body of the mountain-lion section.
- surv-priorities || "Check each other for frostbite: white or grey-yellow skin that feels hard or waxy. Don’t rub it, and only rewarm it if it won’t freeze again." || Frostbite care removed from the Cold-and-snow picker bullet "Cover head, hands and feet. ..."; replaced by a link block to the Emergency frostbite protocol (`p:frostbite`). The rest of the bullet ("Cover head, hands and feet.") is kept.

The `shelter-desert` and `nav-cross` figures are the only figures removed from topics; both remain in figs/.

## Dropped picker regions

The old "Your environment" picker is removed (spec section 5.1). Its Desert and Jungle (tropical) region bullets are
dropped entirely and are not in any topic. Its Forest, Cold and snow, and Coast and sea bullets, and the old
Priorities block, are kept in `surv-priorities`.

## Added headings

Old text that sat before a topic's first `<h3>` has no heading in v6. It goes into a first section whose heading is
the topic title, or, in `surv-priorities`, the old picker button labels. The migration test ignores these headings.

- surv-ten-essentials || "The ten essentials"
- surv-find-water || "Find water"
- surv-make-water-safe || "Make water safe"
- surv-food-and-wild-plants || "Food and wild plants"
- surv-traps-and-fishing || "Traps and fishing"
- surv-signal-for-rescue || "Signal for rescue"
- surv-weather-and-lightning || "Weather and lightning"
- surv-river-crossings || "River crossings"
- surv-priorities || "Forest"
- surv-priorities || "Cold and snow"
- surv-priorities || "Coast and sea"

## Other additions

- `surv-priorities` link block label "Frostbite care" (new wording; links to `p:frostbite`).
- Knots: each knot is its own section; its bold lead-in ("Bowline: a fixed loop that won’t slip or jam") is the heading and the rest is a paragraph.
- Inline formatting (bold) is dropped; blocks hold plain text. Entities are decoded.

## Corrections

Step 2 of the migration (spec section 5.3): changes made while source-checking. Each entry gives the old text, the
new text and the source. "removed-unsourced" means no opened source supported the statement. The full trace of
every statement is in `docs/content-review.md`.

### Task 13: water and priorities (2026-11-17)

**surv-make-water-safe**

- Summary. Old: "Strain cloudy water, then boil it for 1 minute, or treat it with unscented bleach." New: "Strain cloudy water, then boil it for 1 minute (3 minutes above 5,000 ft), or treat it with unscented bleach." Source: EPA Emergency Disinfection of Drinking Water.
- Cloudy water. Old: "let it settle, then strain it through a clean cloth." New: "let it settle, then filter it through a clean cloth, paper towel or coffee filter." Source: EPA.
- Boil at altitude (corrected). Old: "Boil at a rolling boil for 1 minute. Above 6,500 ft, boil for 3 minutes." New: "Bring it to a rolling boil for at least 1 minute. Above 5,000 ft, boil for 3 minutes." Source: EPA says above 5,000 ft; CDC says above 6,500 ft; ATP 3-50.21 says above 8,000 ft. The most cautious (EPA) is used: Mount Marcy and other Adirondack High Peaks are above 5,000 ft.
- Bleach (corrected). Old: "No fire? Use unscented household bleach: 8 drops of 6% bleach (or 6 drops of 8.25%) per gallon. Double it for cloudy or very cold water. Stir and wait 30 minutes." New: "No fire? Use plain, unscented household chlorine bleach (6% or 8.25%) stored at room temperature for less than a year. No scented, color-safe or added-cleaner bleach. Add 8 drops per gallon, or 2 drops per quart or liter. Double it if the water is cloudy, colored or very cold. Stir and let it stand 30 minutes. It should smell slightly of chlorine. If it doesn't, repeat the dose and wait another 15 minutes." Sources: EPA (bleach type and age, 6% = 8 drops per gallon, 2 drops per quart/liter, double for cloudy/colored/very cold, 30 minutes, smell check, repeat and 15 minutes); CDC (8 drops per gallon for any 5% to 9% bleach). EPA gives 6 drops per gallon for 8.25%; CDC's 8 drops is used for both strengths as the more cautious dose (open question in docs/decisions-for-jordan.md).
- Tablets and filters (corrected). Old: "Tablets and filters: follow the maker's directions. Most filters don't stop viruses." New: two steps. "Tablets: follow the label, as each product has a different strength. Iodine and chlorine tablets do not kill Cryptosporidium; chlorine dioxide tablets do if you follow the instructions. If you are pregnant or have thyroid problems, don't drink iodine-treated water, and no one should drink it for more than a few weeks." and "Filters: portable filters do not remove viruses. After filtering, add a chemical disinfectant such as chlorine, iodine or chlorine dioxide." Sources: EPA (label), CDC (Cryptosporidium, iodine limits, portable filters will not remove viruses, disinfect after filtering).
- Figure `water-safe` removed. Its drawn label says "3 min above 6,500 ft", which is wrong against the corrected text; the figure file stays in figs/. Its caption, "Boiling is the most reliable method. Bleach must be plain, unscented and not expired.", is replaced by the paragraph "Boiling is the best way to kill germs in water." (CDC) and by the bleach step above (EPA: less than one year old).
- Added (safety, Northeast). Warn: "Boiling, bleach and filters cannot make every water safe. Water with fuel, toxic chemicals or radioactive material cannot be made safe by boiling or disinfecting; find another source. Boiling and disinfecting also leave heavy metals, salts and most other chemicals in the water." Sources: CDC, EPA.
- Added (safety, Northeast). Warn on harmful algal blooms in New York lakes and ponds: appearance, do not drink, cook with or make ice from the water during a bloom even if treated, boiling does not remove the algae or their toxins. Source: NYS Department of Health, Harmful Blue-Green Algae Blooms.
- Keywords "algae" and "algal bloom" added so search finds the warning.

**surv-find-water**

- Summary. Old: "Water runs downhill: check valley bottoms, the base of cliffs and dry stream beds." New: "Water runs downhill: check low ground, the foot of cliffs and dry stream beds." Source: ATP 3-50.21 3-34; FM 21-76-1 VII-1.
- Where to look. Old: "Water runs downhill. Check valley bottoms, the base of cliffs, and dry stream beds; dig on the outside of bends where water last flowed." New: "Water runs downhill. Check valley bottoms and other low ground, the foot of cliffs or rocks, and dry stream beds; dig on the outside of bends." Sources: ATP 3-50.21 3-34, FM 21-76-1 VII-1, City of Phoenix Fire Department. "where water last flowed": removed-unsourced (explanation only).
- `water-bend` caption. Old: "Water lingers longest under the outside of a bend, where the current cut deepest." New: "Dig on the outside of a bend in a dry stream bed. If you hit wet sand, dig down into it and let water seep in." The old explanation is removed-unsourced. Sources: Phoenix Fire Department; ATP 3-50.21 Table 3-1. Figure kept: it shows digging on the outside of bends, which matches.
- Signs of water (corrected). Old: "Signs of water nearby: green vegetation, swarming insects, animal trails that join up, and birds flying low and straight at dawn and dusk." New: "Signs of water nearby: lush green vegetation, swarming insects, game trails that meet in a V, and birds flying in the early morning or late afternoon, which may show the direction to water." Source: FM 21-76-1 VII-1. "Low and straight" was not in any opened source (removed-unsourced).
- Rain. Old: "Catch rain with a tarp, poncho or large leaves." New: "Catch rain on a tarp, poncho or large leaves." Source: ATP 3-50.21 3-10, 3-11. Wording only.
- Transpiration bag. Old: "Tie a clear plastic bag over a leafy branch of a non-poisonous plant in full sun. Water collects in the bag as the leaves breathe." New: adds "and seal it". Source: ATP 3-50.21 3-27 (sealed airtight); FM 21-76-1 (clear bag, no poisonous plants).
- `water-bag` caption (corrected). Old: "A transpiration bag yields a little water over several hours. Move it to a fresh branch daily." New: "A transpiration bag. Collect the water before sundown. The same branch can be used for 3 to 5 days. The water tastes like the plant smells." Source: ATP 3-50.21 3-27 says the same limb can be used for 3 or 5 days and to collect before sundown, which contradicts "move daily"; FM 21-76-1 VII-6 (taste). "a little water over several hours": removed-unsourced. Figure kept: clear bag, tied, leafy non-poisonous branch, full sun, water in the low corner, all match.
- Added (safety, Northeast). "Skip lake or pond water that is strongly colored, looks like paint or has floating scum: it may be a harmful algal bloom, and treating it yourself does not make it safe (see Make water safe)." Source: NYS Department of Health.
- Treat. Old: "Treat all wild water before drinking (see Make water safe)." New: "Treat all wild water, rain included, before drinking (see Make water safe)." Source: CDC (rainwater must be treated). ATP 3-50.21 3-10 says fresh rain collected into containers needs no purification; CDC is the more cautious and is used (noted in docs/content-review.md).

**surv-priorities**

- Summary (corrected). Old: "If you're lost, STOP: Stop, Think, Observe, Plan." New: "If you're lost, STOP: Sit down, Think, Observe, Plan." Source: NYS DEC, Lost in the woods.
- Rule of threes (reworded as a rough guide). Old: "In harsh conditions a person can last roughly 3 minutes without air, 3 hours without shelter, 3 days without water and 3 weeks without food. Work the problem in that order." New: "A rough guide, not an exact limit: a person can survive about 3 minutes in unsafe air, about 3 hours at a dangerous temperature, about 3 days without water and about 3 weeks without food. Work the problem in that order." Source: Tooele County Health Department, Rule of Three ("not absolute").
- Lost (corrected). Old: "If you're lost, STOP: Stop, Think, Observe, Plan. If someone knows your route and when you're due back, staying put usually gets you found faster than wandering." New: "If you're lost, STOP: Sit down and stay calm, Think, Observe, Plan. If you left a trip plan with someone, stay put: moving makes it harder for searchers to find you. Move only if your life is under immediate threat." Sources: NYS DEC (STOP); NPS Outdoor Emergency Plan (stay put, move only under immediate threat, trip plan). "usually gets you found faster": removed-unsourced, replaced by the NPS reason.
- Forest, hypothermia (corrected). Old: "The biggest killer here is hypothermia in wet, windy weather between 30 and 50°F, not extreme cold. Get out of wind and rain early, before you're soaked." New: "Hypothermia can kill above freezing. Most cases happen between 30 and 50°F, and wind and wet clothes chill you fast. Get out of wind and rain early, before you're soaked." Sources: NYS DEC; Alaska State Parks (30 to 50°F); US Forest Service. "The biggest killer here ... not extreme cold": removed-unsourced. Link to `p:hypothermia` added.
- Forest, water. Old: "Water is usually plentiful. Treat all of it." New: "Treat all water from streams, ponds and lakes before drinking." Source: CDC. "Water is usually plentiful": removed-unsourced.
- Forest, fire (corrected). Old: "Dead and downed wood is everywhere, so fire is usually achievable. Look for standing dead wood when the ground is wet." New: "Burn dead and down wood. On New York state land, cutting standing trees is prohibited." Source: NYS DEC State Land Camping Rules. "fire is usually achievable" and "look for standing dead wood": removed-unsourced (the latter also conflicts with the DEC rule).
- Forest, ticks (corrected). Old: "Check your skin for ticks every day." New: "Check your whole body for ticks after time in the woods: under the arms, in and around the ears, belly button, backs of the knees, hair, between the legs and around the waist." Source: CDC Preventing Tick Bites ("every day" was not in the source). Link to `p:tick` added.
- Cold, COLD. Old: "...avoid Overheating (sweat soaks insulation)..." New: "...avoid Overheating (take layers off before hard work so sweat doesn't soak them)...". Sources: army.mil Fight the Freeze (acronym); FM 21-76-1 (remove layers before strenuous activities; keep clothing dry to keep insulation); Alaska State Parks (remove layers when you start to sweat).
- Cold, snow (corrected). Old: "Melt snow before drinking it. Eating it lowers your core temperature." New: "Don't eat snow or ice: it lowers your body temperature. Melt it, then treat it like any other wild water." Sources: FM 21-76-1 VII-1 ("lowers body temperature"; "core" was not in the source); ATP 3-50.21 3-13 and Table 3-1 (snow and ice no purer than their source; melt and purify).
- Cold, carbon monoxide (corrected). Old: "Never run a stove or fire in a sealed tent or snow shelter. Carbon monoxide kills without warning." New: "Never use a stove, heater or lantern while sleeping in a tent or snow shelter. Any flame inside an enclosed shelter needs an air vent. Carbon monoxide kills people every year this way." Sources: CPSC Portable Heaters & Camping Equipment; FM 21-76-1 VI-4. "kills without warning": replaced (the CO protocol lists warning symptoms). Link to `p:carbon-monoxide` added.
- Cold, snow blindness. Old: "cut thin slits" New: "cut thin horizontal slits". Source: FM 21-76-1 VI-3.
- Coast, seawater. Old: "Never drink seawater. It dehydrates you faster." New: "Never drink seawater. It can kill you: you dehydrate even as you get thirstier." Source: NOAA National Ocean Service.
- Coast, beach water (corrected). Old: "Collect rain and dew. On a beach, dig behind the first dune where plants grow; fresh water often collects there." New: "Collect rain and dew. On a beach, dig a hole behind the first group of sand dunes, deep enough to reach the water table, and treat what collects." Source: ATP 3-50.21 3-33 and Table 3-1; CDC (treat). "where plants grow" and "fresh water often collects there": removed-unsourced.
- Coast, shellfish (corrected). Old: "Only eat mussels and clams that were alive and closed before cooking, and skip them entirely during red tide warnings." New: "Only eat clams and mussels with unbroken shells that close when tapped, and throw out any that don't open in cooking. Never take shellfish from an area closed to shellfishing or during a red tide: cooking does not destroy the toxin, and the water may look normal." Sources: FDA; Massachusetts DPH Red Tide.
- Coast, tides (corrected). Old: "Know the tide times. Rising water can cut you off on points and tidal flats." New: "Check a tide chart before you go out. The rising tide can trap you, for example on a land bridge out to an island; at Acadia in Maine the tide range reaches about 12 ft." Source: NPS How Tides Work at Acadia. "points and tidal flats": not in the source, replaced by the sourced example.
- Coast, sun. Old: "Cover up. Sun reflected off water and sand burns fast." New: "Cover up. Water and sand reflect the sun and increase your chance of sunburn." Source: EPA Sun Safety Tips.

### Task 13 fix round 1 (2026-11-17)

- surv-make-water-safe, bleach step. Added: "Bleach, chlorine and iodine kill bacteria and viruses but do not work well against parasites such as Giardia and Cryptosporidium: boil if you can, or filter first." Source: CDC, About Water Treatment Options When Hiking, Camping, or Traveling.
- surv-make-water-safe, bleach strength. Old: "(6% or 8.25%)". New: "(5% to 9%, such as 6% or 8.25%)". Source: CDC, How to Make Water Safe in an Emergency (same dose for 5% to 9%).
- surv-make-water-safe, chlorine dioxide. Old: "Iodine and chlorine tablets do not kill Cryptosporidium; chlorine dioxide tablets do if you follow the instructions." New: "Iodine and chlorine tablets do not kill Cryptosporidium. Chlorine dioxide tablets kill Giardia and work better against Cryptosporidium, but not fully; follow the label exactly." Source: CDC hiking page ("somewhat effective"), more cautious than CDC's emergency page.
- surv-make-water-safe, iodine. Old: "If you are pregnant or have thyroid problems, don't drink iodine-treated water". New: "If you are pregnant, have thyroid problems or are hypersensitive (allergic) to iodine, don't drink iodine-treated water". Source: CDC (both pages).
- surv-priorities, carbon monoxide. Old: "Never use a stove, heater or lantern while sleeping in a tent or snow shelter. Any flame inside an enclosed shelter needs an air vent. Carbon monoxide kills people every year this way." New: "Never use a charcoal grill, lantern or portable camping stove inside a tent or snow shelter, and never use fuel-burning heaters or lanterns while sleeping in one. Carbon monoxide kills people every year this way." Sources: CDC Carbon Monoxide Poisoning Prevention; CPSC. Vent sentence removed (read it only through a summarising fetch; the reviewer could not read it; contradicts CDC).
- surv-priorities, lost. Old: "If you left a trip plan with someone, stay put: moving makes it harder for searchers to find you. Move only if your life is under immediate threat." New: "Then stay put: moving makes it harder for searchers to find you. Move only if your life is under immediate threat. Before any trip, leave word with someone about where you're going and when you'll be back, so a search starts in the right place." Sources: NPS Outdoor Emergency Plan; NYS DEC Lost in the woods.
- vomiting-diarrhea protocol (outside the batch, controller ruling). Old: "boil water 1 minute (3 minutes above 6,500 feet) (CDC)." and in s8 detail "(3 minutes above 6,500 feet)". New: "boil water 1 minute (3 minutes above 5,000 feet) (CDC, EPA)." and "(3 minutes above 5,000 feet: EPA; CDC says above 6,500 feet, and the app uses the lower height)". Source: EPA Emergency Disinfection of Drinking Water, added to the protocol's sources. Reason: one boiling altitude across the app, matching surv-make-water-safe.
