# Ballistics: checked maths, rifle profiles with sights, long range and AR tools

Date: 2026-11-21. Status: **draft, waiting for Jordan's approval.** Branch: `ballistics`.
Two releases. Release 1 takes the next free version number when it is ready to ship (7.9 if iPhone
support has not shipped first); release 2 takes the one after.

Lines marked **(call)** are choices made by the writer, not by Jordan. He can overrule any of them.

## Why

Jordan asked for a full look at Ballistics. v7.8 restyled the screen and changed no maths. He and
the group shoot **long-range precision rifles** and **AR-style rifles in 5.56 and .223**. Their
sights are a heavy mix: red dots, iron sights, low-power variable scopes, and scopes with mil
turrets and with MOA turrets. He wants the screen to be "dynamic" and to "capture as much as we
can". Deer hunting was considered and removed by him on 2026-11-21.

What is wrong today (found by reading `src/ballistics.js`, `src/app.js` lines 497 to 610 and the
tests):

1. **The maths has never been compared with an outside source.** The only test
   (`tests/test_tactical_layout.py`, `BEFORE`) confirms the numbers did not change in the restyle.
2. The solver finds the zero in **today's** air. A rifle zeroed in summer and fired in winter gets
   a card that is off, and nothing says so.
3. There is no way to correct a profile from what the rifle really did.
4. The answer is given in mil or MOA only. That is no use to a red dot, iron sights or a drop
   reticle, and it does not give clicks.
5. Spin drift is left out (the screen says so).
6. The five built-in loads have no recorded source.
7. The answer is at the top and the inputs run for several screens below it.
8. Small faults: the card can show `-0.0`; a zero range that is not a whole number loses its
   highlighted row.

## Goals

1. Every number the screen shows rests on maths that has been compared with published
   trajectories, with tests that keep it so.
2. A rifle is set up once as a profile (load, sight, zero conditions) and after that the answer
   comes in the form that rifle's sight uses.
3. A profile with no sight set still gives a full answer at once, in every unit.
4. A profile can be corrected from one real shot at distance.
5. Range and wind can be changed without the answer leaving the screen.
6. (Release 2) Long range: spin drift. AR rifles: compare zeros, and see the close-range offset.

## Not in these releases

- Deer and hunting tools (hold-dead-on range, vital zone). Removed by Jordan.
- A built-in list of named scopes or reticles (see Approaches, C).
- Coriolis and Eötvös effects. The screen keeps saying they are not included.
- Muzzle velocity changing with powder temperature. It needs data per powder that the app does
  not have. The profile editor says the velocity should be measured near the temperature it will
  be used at.
- Correcting the ballistic coefficient from shots (only the velocity is corrected).
- Moving targets, wind that differs along the flight, more than one wind value.
- Metres, m/s and grams. Ballistics stays in yards, inches, fps and grains, whatever the Tactical
  map's unit setting is. **(call)**
- Any change to Map, Position, Emergency or Survival.

## What would make this a failure even if it works

- A wrong number shown with confidence. Where the app cannot be right (past the last reticle
  mark, below the speed of sound, a correction that makes no sense) it says so and falls back to a
  plain angle; it never invents a mark or a click count.
- A screen that needs setup before it will answer.
- A sight setting that changes the trajectory. **The sight only changes how the answer is written.**
  The only things that change the trajectory are the load, the zero, the conditions and the shot.
- Text that advises action against a person (standing project rule). Wording stays "target",
  "hold", "dial".

## Constraints (from the project's standing rules)

- Work from a fresh clone, on a branch; nothing reaches `main` without Jordan's go and a
  phone-check list. Edit `src/`, `tests/`, `tools/`, `docs/` only.
- **Every number comes from a source that was actually opened**, recorded in
  `docs/content-review.md` under a "Ballistics" heading: the reference trajectories, each built-in
  load's coefficient and velocity, the spin drift and stability formulas, any constant added.
  Web research with the built-in search and fetch only; fetch only URLs a search returned.
- All new overlays go through `src/sheet.js` (`FK.sheet.open/ask/confirm`). Read it whole first.
  No `prompt()`, `confirm()`, `alert()`. The unsaved-typing rule applies to the profile editor:
  Back, Escape or a backdrop tap asks "Keep editing" or "Discard".
- Fits 360 px wide, day and night mode, every control at least 44 px, nothing cut off with
  enlarged text. A table wider than the screen scrolls with the "Swipe sideways" cue.
- Works offline. No browser feature that the iPhone table in `docs/v7.8-rulings.md` lists as
  missing or doubtful.
- The repo is public: no home town, test coordinates only at 43.0, -76.0 (none are expected here).
- Run the **full** test suite after every task. Flaky tests are treated as bugs.
- Final reviews as in v7.8: whole-branch code review, then a tester who drives the built app at
  phone size from screenshots and judges from the screen.
- A ledger of every decision made without asking, each with its cost if wrong, goes to Jordan at
  the release stop (`docs/ballistics-rulings.md`).

## Approaches

Three ways to make the answer fit a mixed set of sights were put to Jordan on 2026-11-21.

- **A. The sight lives in the rifle profile** and the answer follows it. One screen, each person
  sees only their kind of answer. Cost: a little setup per rifle.
- **B. Show every unit every time** (mil, MOA, clicks, inches). No setup, least to build. Cost:
  crowded, and the number wanted is one of four; clicks and reticle marks cannot be shown at all
  without sight details.
- **C. A built-in list of named scopes and reticles.** Dropped: the mark spacing of hundreds of
  reticles cannot be sourced reliably, and a wrong mark is a miss.

**Chosen by Jordan: A and B combined.** A profile with no sight set shows everything (B). Once the
sight is set on a profile, that profile shows its own kind of answer (A) and the choice is saved
with the rifle. A "Show all units" switch is always there.

## Release 1

### 1. Check the maths

The solver is a point-mass model with the standard G1 and G7 drag tables, integrated in 1 ms
steps. A first run on 2026-11-21 gave plausible figures (.308 175 gr, G7 0.243, 2,600 fps, 100 yd
zero, standard air: 11.9 mil up and 3.1 mil for a 10 mph crosswind at 1,000 yd). That is not a
check.

The check:

- **Reference trajectories from at least two independent published sources** that were opened
  (for example an established solver's printed output, a bullet maker's published table, an army
  firing table). At least: one .308 match load to 1,000 yd, one 5.56 or .223 load to 600 yd, one
  load that goes subsonic inside the table. For each: drop, wind drift, remaining velocity and
  time of flight at several ranges, with the source's own atmosphere and zero entered exactly.
- **Pass mark (call):** while the bullet is above Mach 1.2, elevation within 0.1 mil and wind
  within 0.1 mil out to 600 yd, and within 0.2 mil out to 1,000 yd; velocity within 1 percent.
  Below Mach 1.2 the difference is recorded, not judged.
- **What counts as a reference (call):** a trajectory computed with one stated G1 or G7
  coefficient, so it is the same kind of model as this solver. Two separate published solvers of
  that kind count as independent. A maker's table or firing table built from radar data, a custom
  drag curve or stepped coefficients is recorded beside the app's figures but **not judged**
  against the pass mark, and the solver is **not** extended to match it (no stepped coefficients,
  no custom drag curves in these releases).
- **Checks that need no outside source:** with drag switched off the path is the textbook
  parabola; halving the time step moves no answer by more than 0.01 mil; air density matches the
  standard atmosphere table at sea level and at altitude; the two drag tables match their
  published values point for point.
- **Which standard air the coefficient refers to.** Makers publish G1 coefficients against one of
  two standard atmospheres that differ by about one percent in density. The code today takes the
  coefficient as given and uses the real air density. The builder states which standard is assumed,
  records the source, and measures what the other choice would change.
- **If the solver fails the pass mark:** fix the solver, not the pass mark, and tell Jordan what
  changed in the numbers he has been seeing. If it passes, the default profile's figures in
  `BEFORE` stay exactly as they are; that test may change only with a ruling that gives the before
  and after.
- The reference cases become permanent tests. The solver must be testable on its own, without
  driving the screen.

### 2. Rifle profiles

A profile today is `{ id, name, bc, model, w, mv, sight (height), zero }`, kept in the `profiles`
list and carried in backups. It gains the fields below. **All are optional**, so every existing
profile, every stored input and every v7.8 backup loads unchanged and behaves as it does now.

**Sight** (how the answer is written; never changes the trajectory):

| Sight | Extra detail | Answer for elevation | Answer for wind |
|---|---|---|---|
| Not set | none | mil, MOA and inches together | mil, MOA and inches |
| Scope with turrets | unit: mil, MOA, or inches per 100 yd; click size: 0.1 or 0.05 mil, or 1/4, 1/8, 1/2 or 1 in the other two | the angle in the turret's unit, and clicks | the angle in that unit, and clicks |
| Drop reticle (low-power scope) | unit of the marks; each mark's distance below the centre, as the scope's manual gives it (up to 10 marks) | the nearest mark, then how far to hold high or low of it in inches | the angle in the reticle's unit, and inches |
| Red dot or iron sights | none | hold high or low, in inches | hold left or right, in inches |

**MOA means true MOA (1.047 in at 100 yd).** Some scopes sold as "MOA" really move 1 in per
100 yd; the two differ by 4.7 percent, which is five or six quarter-clicks on a long shot. So
turrets and reticle marks offer a third unit, "Inches per 100 yd", and the editor says to check
the manual for which one the scope is. With no sight set, the answer shows true MOA. **(call)**

Rules for the drop reticle:
- The owner types the marks from their own manual. The app ships none.
- Before the first mark: "Centre" and the hold in inches. Past the last mark: the app says the
  target is past the last mark and gives the plain angle in the reticle's unit.
- The editor carries one line: on a scope whose reticle does not grow with magnification, the
  marks are true at one magnification only (the manual says which).
- Marks must increase down the list; a list that does not is refused with the reason.
- **Marks are entered as angles only (call).** Many low-power scope manuals label the marks by
  yardage for one stated load and also print a table of their angles; the angles are what is
  typed. A manual that gives yardages and nothing else is not supported in release 1, and the
  editor says so. Entering marks by yardage, with the app working out what distance each mark is
  really true at for the owner's load, is a candidate for release 2 if the group's manuals need it.

**Zero conditions** (optional): temperature and either altitude or station pressure at the time
the rifle was zeroed. When given, the zero is solved in that air and the shot in today's air. When
blank the app behaves as now and the profile editor says "Zero conditions not set: assumed the
same as today".

**Editing.** Load, sight height, zero, sight and zero conditions move off the main screen into a
profile editor (a sheet). Saving a profile of your own changes it in place. A built-in load cannot
be changed; editing one offers "Save as new profile". Delete stays, with the existing confirmation.
The "Custom (unsaved)" entry goes away: there is always a selected profile. Stored inputs from
v7.8 that were on "Custom" become a profile named "Custom" on first open. **(call)**

**Built-in loads.** Each one's coefficient and velocity is re-checked against a source that was
opened, with the barrel length the velocity is for in its name. One that cannot be sourced is
removed. AR loads are added where a source exists (at least a 55 gr 5.56 load, and 16 in barrel
velocities). Built-in loads have no sight, so they show every unit.

### 3. Correct a profile from a real shot

In the profile editor: "Correct from a real shot". The shooter enters the distance and what the
rifle really needed there (in the profile's sight unit, or the drop in inches), with the
conditions on the day. The app finds the muzzle velocity that reproduces it and shows the old
velocity, the new one and the change, then asks before saving.

Guard rails **(call)**:
- Refused under 300 yd, and at any distance where the bullet is below Mach 1.2 (a small error
  there gives a wild velocity; past that point the coefficient, not the velocity, is the thing in
  doubt). The message says why.
- A change over 5 percent shows a warning ("check the distance, the zero and the sight height
  first"). A change over 15 percent is refused.
- The profile keeps its original velocity, and the editor can put it back.

### 4. The screen

At 360 x 640, with no scrolling, the first screen holds the rifle, the answer and the four shot
inputs:

```
[ Tikka .308  ·  mil turrets            Edit ]

  ELEVATION            WINDAGE
  U 3.6 mil            R 1.2 mil
  36 clicks            12 clicks
  At 500 yd: drop 64.3 in, drift 21.9 in,
  1761 fps, 1205 ft-lb, 0.70 s flight.
                         [ Show all units ]

  Range (yd) [ 500 ]   Incline (°) [ 0 ]
  Wind (mph) [ 10  ]   Wind from   [ 3, right ]

  CONDITIONS   59°F · 0 ft · 50%        Change
  DOPE CARD    out to 1000, every 50
```

- The same card for a red dot reads "Hold 9 in high / Hold 3 in right"; for a drop reticle "Mark
  3, hold 2 in high"; with no sight set it shows mil, MOA and inches on three short lines.
- The MIL / MOA switch is replaced by "Show all units". The unit now comes from the sight.
- Conditions collapse to one line that opens to the four fields it has today.
- The dope card's columns follow the sight: turrets get the angle and clicks; a drop reticle gets
  the mark and hold; a red dot gets the hold in inches; no sight gets mil, MOA and inches. Drop,
  drift, velocity, energy and time stay. Rows below Mach 1.2 stay orange.
- Very short ranges are allowed in the Range box (down to 1 yd), so a red dot profile already
  shows the close-range hold in this release.
- Fixes: no `-0.0`; the zero row is highlighted whatever the zero range is.

## Release 2

### 5. Spin drift (long range)

Optional profile fields: barrel twist (inches per turn), twist direction (right by default),
bullet length and bullet diameter. When all are present, spin drift is added to the windage answer
and the card, using a published stability formula and a published spin drift approximation, each
from a source that was opened and each checked against that source's worked example. The answer
line says how much of the windage is spin drift. When the fields are missing the screen says
"Spin drift not included: add twist and bullet length to the profile".

If the stability figure is marginal by the source's own threshold, the profile editor says so
(for example a long, heavy bullet in a slow twist). It is a warning, not a block.

### 6. Compare zeros (AR rifles)

For the selected profile, pick two or three zero distances from 25, 36, 50, 100 and 200 yd or a
typed one. The app shows, side by side, the bullet's height above or below the line of sight from
5 to 300 yd, where each zero crosses the line of sight a second time, and the highest point of
each path. A small chart if it reads clearly at phone width in night mode; otherwise the table
alone. "Use this zero" writes it to the profile, with a line saying the rifle itself still has to
be re-zeroed at the range.

### 7. Close-range offset

A short table for the selected profile: how far below the sight the bullet strikes at 3, 5, 7, 10,
15 and 25 yd, written as a hold in inches. It is the same solver with short ranges; the work is in
presenting it.

## Left to the builder

- The layout of the profile editor and how its sections fold; field limits and messages.
- How the tests reach the solver (it is a top-level `BAL` object in `src/ballistics.js`).
- Which reference sources are used, within the rule that they were opened and are recorded.
- Table column widths and the swipe cue; the chart in section 6.
- Whether "Show all units" is remembered per profile; the humidity assumed for zero conditions.
- The order of tasks. Section 1 comes first: nothing is built on maths that has not been checked.

## What cannot be tested in a build session

No rifle is fired. The last check is Jordan's: the app's card for a rifle whose real elevations he
already knows, the reticle marks of a real low-power scope, and click counts on real turrets. The
phone-check list for each release says exactly what to compare.
