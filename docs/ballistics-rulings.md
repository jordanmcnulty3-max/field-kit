# Ballistics rulings

This file records every decision made in the ballistics release without asking Jordan. Each entry says what was decided, why,
and what it costs if the decision is wrong, so any of them can be reversed later with the cost known. Sources are listed in
`docs/content-review.md` under "Ballistics".

## Solver check against published trajectories (2026-11-21)

**The solver was not changed.** Every judged reference case passes with the solver as it was. The only code changes are the
`p.dt` option (integration step, default 0.001 s, so the step-size test can run) and the `BAL.tables` export (so the drag-table
test can read the tables the solver flies). The figures in `BEFORE` (`tests/test_tactical_layout.py`) are unchanged. Default .308
profile (G7 0.243, 175 gr, 2600 fps, 1.5 in sight, 100 yd zero, 59 F, sea level, 50 %, 10 mph from 3 o'clock), before and after:
500 yd U 3.57 mil, R 1.22 mil, 1761 fps; 1,000 yd U 11.97 mil, R 3.10 mil, 1091 fps.

Largest difference from each judged source, on rows where the bullet is above Mach 1.2 (pass mark: 0.1 mil to 600 yd, 0.2 mil
to 1,000 yd, velocity 1 %):

| Case | Model | Judged rows | Elevation | Wind | Velocity |
|---|---|---|---|---|---|
| Hornady 30 cal 180 gr Spire Point | G1 | 50 to 500 yd | 0.016 mil | (none given) | 0.06 % |
| Hornady 30 cal 180 gr Round Nose | G1 | 50 to 500 yd | 0.006 mil | (none given) | 0.13 % |
| Hornady Test #1 | G1 | 100 to 500 yd | 0.007 mil | (none given) | 0.12 % |
| pyballistic QuickStart | G7 | 100 to 500 yd | 0.006 mil | 0.006 mil | 0.00 % |
| Steiner 3TR, 5.56 M855 62 gr | G1 | 200 to 650 yd | 0.004 mil | 0.006 mil | 0.17 % |
| Zdziarski program, .308 175 gr SMK | G1 | 50 to 800 yd | 0.053 mil | (spin drift only) | 0.04 % |

Below Mach 1.2 (not judged) the solver still stays close: the Steiner table to 1,000 yd (979 fps, Mach 0.88) differs by at most
0.006 mil elevation, 0.007 mil wind and 0.34 % velocity; the Zdziarski table at 1,000 yd by 0.081 mil and 0.04 %.

Decisions made in this check:

- **Steiner 3TR table taken as G1.** The page prints BC 0.304 without naming the model. As G7 the 600 yd elevation would be
  about 1.2 mil and the velocity nearly half again away from the table; as G1 it agrees to 0.01 mil. Cost if wrong: one of the
  two independent G1 sources, and the only subsonic and 5.56 case, would not count; the G1 Hornady tables and the G7 pyballistic
  table still pass.
- **Zdziarski post: pressure taken as the pressure at the firing point, and muzzle velocity as the table's 0 yd row (2606 fps).
  This reading was chosen because it passes; the other reading fails.** The post does not say whether 30.13 inHg was
  corrected to sea level. Read as the pressure at the firing point, the case passes (velocity within 0.04 %, elevation within
  0.053 mil to 800 yd). Read as a sea-level figure (29.28 inHg at 794 ft), it **fails the pass mark**: 1756 against 1734 fps at
  500 yd (+1.3 %) and 1351 against 1324 fps at 800 yd (+2.0 %), over the 1 % velocity limit; elevation at 800 yd is 7.558
  against 7.757 mil (0.199 mil, at the edge of the 0.2 mil limit). So this case, the only .308 case past 500 yd, counts only
  under an interpretation picked because it agrees. The program zeroed in standard air and fired in the stated air; this app
  zeros in the firing air, a difference inside the table's own 100 yd figure (-0.01 in). Cost if wrong: no judged .308 or
  other source would confirm a trajectory past 500 yd except the Steiner 5.56 table. A second .308 or G7 source to 1,000 yd
  with a stated atmosphere was searched for and not found (see the open item below).
- **pyballistic humidity entered as 0 %.** The library's default humidity constant is named but its value is not printed on the
  page that opened. Humidity at 59 F moves density by under 1 %; the velocities agree to 0.1 fps. Cost if wrong: none to the
  verdict.
- **Wind compared by size for pyballistic and Federal.** pyballistic prints a positive windage for a wind from 3 o'clock, its
  own convention; Federal gives no direction. The sign of this app's wind is checked by the Steiner table, whose drift for a
  wind from 3 o'clock is negative, as here.
- **Federal GM308M2 recorded but not judged.** The page states no atmosphere and does not label its .505 as G1. With Army
  Standard Metro assumed it agrees within 0.03 mil and 0.12 %, for information only.
- **Drag tables checked pair by pair (fix round 1).** Every [Mach, Cd] pair of `BAL.tables` (G1: 79 pairs, G7: 84 pairs) is
  identical to the tables printed in ballistics-engine's `data/g1.csv` and `data/g7.csv`, whose README gives their origin
  (BRL, Lowry 1965, McCoy). No pair in `BAL.tables` is missing from the source and none of the source's pairs is missing here.
  That covers the G7 transonic values (Mach 0.9 to 1.5) the default profile flies through from about 550 yd on (Mach 1.5
  at about 560 yd, 0.98 at 1,000 yd). Cost if wrong: the source is one open-source solver's copy of the BRL tables, not a BRL publication; if both copies carried the same
  error, the test would not see it.
- **Air density checked at altitude (fix round 1).** With pressure left blank, the solver works pressure out from altitude.
  At 5,000 and 10,000 ft, at the standard temperature for each height, pressure and density agree with the U.S. Standard
  Atmosphere table (Anderson, Appendix E) within 0.03 %.

### Open item for Jordan

- **No outside G7 trajectory past 500 yd.** The default profile is G7. Its drag table, the air density (sea level and
  altitude) and the integrator (G1 through the sound barrier, Steiner table) are each confirmed, but no G7 trajectory to
  1,000 yd with a stated atmosphere, zero and sight height could be opened: the pyballistic example stops at 500 yd; the RUAG
  Swiss P 175 gr sheet uses stepped coefficients; the Exbal card on rifleshooter.com uses stepped coefficients; the JBM table in
  "how to read a ballistic table" is an image; library notebooks and validation files were not returned by a search or would
  not open. Cost if the solver were wrong there: the default profile's elevation from about 600 to 1,000 yd. The size of a
  plausible error is bounded by the pieces above, but it has not been measured against a G7 table. A G7 dope card from any
  established calculator, with its inputs printed, would close it.

## Standard atmosphere of the coefficient (2026-11-21)

The solver computes drag as air density times Cd times (pi/8) over (BC x 703.07 kg/m2), with the density of the air at the
shooter. In the usual imperial form that is (density / 1.225 kg/m3) x 2.08551e-4 x Cd x v^2 / BC: the same constant that
ballistics-engine's constants page gives as the exact retardation form "normalized to ICAO sea-level air" and says most modern
published coefficients are referred to. **So the solver treats a coefficient as referred to the ICAO standard atmosphere
(59 F, 29.92 inHg, dry, 1.225 kg/m3).** The same page gives the older constant 0.000683 x 0.30 as the Army Standard Metro one;
used with the Metro density (0.075126 lb/ft3) it gives the same drag within 0.02 %, which is why the Hornady tables (Metro) and
the pyballistic and Steiner tables (ICAO) all agree with the solver unchanged.

**Corrected after the final maths review (2026-11-21).** The solver computes drag from Cd with the density of the actual air, so a
coefficient that its publisher reduced properly (from velocities measured in known air) does not depend on which standard it is
quoted against: the standard only names the reference density, and the solver's constant and density agree for both. The 1.018
factor matters only in a hypothetical case: a coefficient its publisher reduced inconsistently (measured in one air, divided by the
other standard's density). Dexadine's Ballistic Explorer help and a Long Range Hunting post both give that conversion as 1.018
(Metro to ICAO, 0.982 the other way); ballistics-engine gives 0.075126 / 0.076474 = 0.98237. What such a coefficient would cost,
measured on the default profile as it was then (G7 0.243) at 1,000 yd:

| Coefficient used | Elevation | Wind | Velocity |
|---|---|---|---|
| 0.243 as entered | U 11.97 mil | R 3.10 mil | 1091 fps |
| x 0.982 (other standard one way) | U 12.16 mil (+0.19) | R 3.19 mil (+0.08) | 1077 fps |
| x 1.018 (the other way) | U 11.79 mil (-0.18) | R 3.02 mil (-0.08) | 1108 fps |

Report only; the solver is not changed for it. Cost, only for an inconsistently reduced coefficient (no built-in load is known to
be one): about 0.2 mil of elevation at 1,000 yd and about 0.03 mil at 500 yd.

## Built-in loads sourced (2026-11-21)

The five built-in loads had no recorded source. Each was checked against pages opened on 2026-11-21 (list in
`docs/content-review.md`, "Built-in loads"). The rule used: a load stays or is added only if a maker's page for the cartridge
the load is named after gives a coefficient with its drag model stated (G1 or G7) and a velocity with its test barrel length. A
coefficient printed with no model is not used; a retailer page or a forum post counts for nothing. **Result: six loads. One is
kept as it was (p65cm), two changed (p308, p223), three are new (p556m193, p556ss109, p76239sb), and the two ids p556 and
p76239 are retired.** Names now give the maker and cartridge, so the coefficient and the velocity describe one real product.

| Id | Before | After | Why |
|---|---|---|---|
| p65cm | G7 0.326, 2710 fps | same values; named "Hornady 6.5 Creedmoor 140 gr ELD-M, 24″ barrel" | Hornady's coefficient page gives G7 0.326 and Hornady's cartridge page gives 2710 fps from a 24 in test barrel |
| p308 | G7 0.243, 2600 fps | G7 0.25, 2600 fps; "Federal Gold Medal .308 Win 175 gr SMK, 24″ barrel" | Federal prints G7 0.25 and 2600 fps from 24 in |
| p223 | G1 0.372, 2750 fps, "77 gr OTM" | G7 0.188, 2720 fps; "Federal Gold Medal .223 Rem 77 gr SMK, 24″ barrel" | Federal prints G7 .188 and 2720 fps from 24 in; the cartridge is a Sierra MatchKing load, not an OTM |
| p556m193 | (none; p556 held G1 0.304, 3020 fps) | G7 0.127, 3301 fps, 55 gr; "Sellier & Bellot 5.56×45 M193 55 gr FMJ, 23.5″ barrel" | Sellier & Bellot's page prints 3,301 fps at 23½ in with G1 0.259 and G7 0.127 |
| p556ss109 | (none) | G7 0.151, 3035 fps, 62 gr; "RWS 5.56x45 NATO Ball SS109 62 gr, 20″ barrel" | RWS prints 925 m/s from a 508 mm barrel and G1 / G7 coefficients by distance |
| p76239sb | (none; p76239 held G1 0.29, 2350 fps, 123 gr) | G1 0.286, 2421 fps, 124 gr; "Sellier & Bellot 7.62×39 124 gr FMJ, 20.5″ barrel" | Sellier & Bellot prints 738 m/s from 520 mm with G1 0.286 and G7 0.143 |
| p556, p76239 | as above | retired, never reused | their numbers had no source; a stored selection becomes an own profile named for what it was (below) |

On the screen, default inputs (59 F, sea level, 50 %, 10 mph from 3 o'clock), before and after, for the two that changed:

| Load | Range | Before | After |
|---|---|---|---|
| p308 | 500 yd | U 3.57 mil, R 1.22 mil, 1761 fps | U 3.54 mil, R 1.18 mil, 1782 fps |
| p308 | 1,000 yd | U 11.97 mil, R 3.10 mil, 1091 fps | U 11.68 mil, R 2.97 mil, 1119 fps |
| p223 | 500 yd | U 3.26 mil, R 1.54 mil, 1661 fps | U 3.34 mil, R 1.56 mil, 1638 fps |
| p223 | 1,000 yd | U 12.80 mil, R 3.90 mil, 1030 fps | U 13.53 mil, R 4.17 mil, 983 fps |

**BEFORE changed, once.** The test `BEFORE` in `tests/test_tactical_layout.py` pins what the screen shows for `p308` (the default)
and for the second starting point it used, `p556`. `p308`'s numbers changed, so the default pins were captured again from the
screen, read the same way the test reads it (`#solElev`, `#solWind`, `#solSub` and the dope card text, mil and MOA). `p556` is
retired, so the second set pins `p223` (300 yd, 10 mph from 9 o'clock), captured the same way; the keys are `p223_mil` and
`p223_moa`. A comment beside `BEFORE` names this ruling. Renaming the loads afterwards (Ruling A) changed no figure and the pinned
text holds no load name, so `BEFORE` was not touched again; the two tests that used `p556` use `p223`. The final drive changed
only the reader (R35): the dope column "Drop in" is now headed "Path in", a transonic row's yardage carries a dagger, and the
sentence reads "63.6 in low, drift 21.2 in left"; the reader maps them back, and every pinned figure is unchanged.

Decisions made without Jordan:

- **Ruling A (controller): a coefficient published by the ammunition maker for its own loaded cartridge is an acceptable source,
  provided the load's name names that maker's cartridge, so the two figures describe one real product.** Applied to p308 and
  p223, whose names now begin "Federal Gold Medal", and to p65cm ("Hornady ...", coefficient and velocity both Hornady's own).
  The Sierra pages that opened either printed no coefficient (175 gr: the ballistics tab never loaded) or printed .372 with no
  model (77 gr), so Federal's labelled "Ballistic Coefficient G7" values (0.25 and .188) were used, and Federal's unlabelled .505
  and .372 were not. Cost if wrong: the two coefficients rest on the loaded-cartridge maker rather than the bullet maker; if
  Sierra's own G7 for either bullet differs, the .308 elevation at 1,000 yd moves by about 0.3 mil per 0.007 of coefficient (the
  0.243 to 0.25 change measured below), the .223 by more since its coefficient is smaller. For the default load the 0.243 to 0.25
  change is 0.29 mil of elevation at 1,000 yd (11.97 against 11.68 mil, about 11 in) and 0.03 mil at 500 yd. Fix: open Sierra's
  data for both bullets and compare.
- **p308 moved from 0.243 to 0.25.** The 0.243 came from the earlier build with no recorded source. Cost if wrong: if 0.243 was
  right, shots to 1,000 yd land about 0.3 mil (11 in) low.
- **p223 changed from G1 to G7 and from "OTM" to Federal's Sierra MatchKing load.** No opened page says .372 is a G1 value;
  Federal labels only its G7 (.188). Cost if wrong: at 1,000 yd the elevation differs by 0.7 mil from the old figure. p223 keeps its
  id because it is the same slot (a .223 Rem 77 gr match load) now with sourced figures.
- **p65cm kept at G7 0.326, Hornady's Mach 2.25 value, although Hornady says the Mach 1.75 values (G7 0.310) are the ones to use
  beyond 600 yd.** 0.326 is the one Hornady says to use when comparing with other published coefficients, and it is what the load
  already held. Cost if wrong: beyond 600 yd the drop is understated; at 1,000 yd with 0.310 the elevation is U 9.11 mil against
  U 8.86 mil (0.25 mil, about 9 in), and 500 yd differs by 0.04 mil. (Corrected after the final maths review: this entry said
  Hornady refers its coefficients to Army Standard Metro air and claimed a further 1.8 % on the coefficient, up to 0.2 mil at
  1,000 yd. Hornady's coefficient page, hornady.com/bc, refers them to ICAO: sea level, 59 F, 29.92 inHg, 0 % humidity, the
  standard the solver uses; and a properly reduced coefficient does not depend on the standard anyway, see "Standard atmosphere
  of the coefficient". The extra cost does not apply.)
- **Ruling B (controller): look again for 5.56 and 7.62x39 loads, since the release is for AR rifles as much as long range.**
  Loads were accepted from a maker that prints both a labelled coefficient and a velocity with its test barrel length for its own
  cartridge. Hornady (Frontier 55 gr M193, 62 gr FMJ, BLACK 62 gr FMJ and 123 gr SST), Federal American Eagle, PMC, Winchester,
  Nosler, Black Hills, Fiocchi, Remington, Barnes and Norma were opened; their pages give velocities with barrels but no
  coefficient, or a coefficient with no model (list in `docs/content-review.md`). Sellier & Bellot (55 gr M193 and 124 gr 7.62x39)
  and RWS (62 gr SS109) print both. The Sellier & Bellot page says its coefficients are converted to standard ICAO air, the
  standard this solver uses.
- **p556m193: the G7 value used, not the G1.** Sellier & Bellot prints both (G1 0.259, G7 0.127). The G7 table suits a boat-tail
  bullet; the two models give nearly the same drop at 300 and 500 yd (U 0.78 and 2.58 mil with G7, 0.78 and 2.55 mil with G1;
  1610 against 1640 fps at 500 yd). Cost if wrong: about 0.03 mil at 500 yd.
- **p556ss109: one G7 value, 0.151, taken from RWS's table, which gives a different value at every distance.** G7 is 0.151 at 25 m,
  100 m and 400 m, 0.155 at 200 m, 0.153 at 300 m, 0.144 at 500 m, and 0.158 to 0.094 beyond 600 m (where the bullet is near
  Mach 1.2 and below). 0.151 is the value that holds from 25 m to 400 m, where the bullet is still above Mach 1.5. Cost if wrong:
  past 500 yd the drop is understated; with 0.144 the 500 yd elevation is U 2.96 mil against U 2.86 mil (0.10 mil, 5 in) and
  1585 against 1642 fps; the table's own value changes again beyond 600 m, which a single coefficient cannot follow (RWS's G7
  falls to 0.144 at 500 m, so the app understates elevation by about 0.1 mil near 550 yd). **The velocity 3035 fps (925 m/s) is
  the muzzle velocity RWS's own table uses.** (Corrected after the final maths review. This entry said 925 m/s is a v10 reading,
  implied a muzzle velocity of about 3071 fps, and claimed the load as shipped overstates the drop by 0.04 mil at 300 yd and
  0.09 mil at 500 yd. RWS's table lists 925 m/s at 0 m; G7 0.151 flown from 925 m/s at 0 m reproduces the table's 898 m/s at 25 m
  exactly, while from 936 m/s it gives 909. So 3035 fps agrees with the maker's table and the overstatement claim is not
  supported.) Its second line, 914 m/s "assault rifle", was not used. Sellier & Bellot's SS109 62 gr line (945 m/s) was looked at
  as a replacement but its page gives no test barrel length and no coefficient, so it could not replace this one.
- **p76239sb is 124 gr, not 123 gr, and G1 0.286.** Sellier & Bellot's only 7.62x39 FMJ row is 124 gr; Hornady's 123 gr SST page
  prints no coefficient, and no maker page with a labelled coefficient for a 123 gr FMJ was found. G1 was chosen for this
  flat-base bullet (S&B also prints G7 0.143); with G7 0.143 the 500 yd elevation is U 5.54 mil against U 5.45 mil (0.09 mil) and
  the velocity 1146 against 1219 fps. Cost if wrong: about 0.1 mil at 500 yd. The velocity 2421 fps is S&B's 738 m/s, the barrel
  20.5 in is 520 mm. A phone selecting the old 123 gr p76239 now meets the fallback below, not a 124 gr load.
- **No 16 in barrel velocity was added.** The only 16 in figures found are PMC's (55 gr 3120 fps, 62 gr LAP 2920 fps, its
  catalogue states "Barrel Length: 16 inches"), and PMC prints its coefficients (0.243, 0.304) with no drag model anywhere; Federal's
  Fusion MSR 62 gr is 2750 fps at 16 in with no coefficient. Under the rule a coefficient with no model is unusable, so no load
  was built on them. Cost if wrong: the AR loads are all 20 to 24 in velocities; a 16 in carbine is slower, and the user must enter
  its velocity by hand.
- **No M855 or Hornady 62 gr load.** RWS's SS109 is the NATO 62 gr round with a labelled coefficient; the U.S. M855 pages
  (Winchester catalogue, Federal, an unnamed maker's data sheet) gave no model or no barrel length. Cost if wrong: none to
  existing screens.
- **A phone whose stored selection names a retired load keeps the numbers it had, as one of its own profiles (corrected).** This
  entry used to say such a phone shows "Custom (unsaved)"; there is no unsaved entry any more (R12). When the stored copy holds a
  coefficient and a velocity, they become the own profile `ucustom`, named for what it was: "5.56 NATO 62 gr (old built-in)" for
  p556 and "7.62×39 123 gr (old built-in)" for p76239 (R34; a stored v7.8 "custom" still becomes "Custom"), and it is selected;
  otherwise the default built-in load is selected. A test covers both retired ids and checks that no console error is raised.
  The alternative, loading another built-in load, would swap the user's coefficient and velocity without warning. Cost if
  wrong: such a phone keeps the old, unsourced p556 or p76239 numbers until the user edits or deletes that profile.
- **Sight height and zero left as they were** (sight height 2.6 in for the AR loads and p223, 2.0 in for p76239sb, 1.5 in for p65cm
  and p308, all zeroed at 100 yd); they are the app's own starting values, not sourced.
- **A stored selection of a built-in load shows that load's current numbers (fix round 1).** On restore, when the stored
  `profile` is the id of a load in `PRESETS`, the six load fields (coefficient, drag model, weight, velocity, sight height, zero)
  are loaded from `PRESETS`; every other stored input (range, wind, conditions, card settings) is restored as stored. Reason:
  the load is not typed on the main screen (it lives in the profile, edited in the profile editor), so a stored built-in id means
  the person picked the built-in and never typed those numbers; without this a phone on the default .308 would show the new
  Federal name over the old 0.243. A stored Custom selection and a stored selection of the user's own saved profile are
  unchanged (tests cover both, and the retired ids).
  Cost: on update, a phone sitting on the default .308 sees its card move without anyone editing it (500 yd, default inputs, from
  U 3.6 to U 3.5 mil; the figures are in the table above), and a phone on p223 sees G7 0.188 and 2720 fps in place of G1 0.372 and
  2750 fps. A hand-edited backup that pairs a built-in id with other numbers has those numbers replaced.

## Correcting a profile from a real shot (2026-11-21)

A person types the distance and the elevation their rifle really needed there, and the editor finds the muzzle velocity that
reproduces it (`BAL.trueMv`, a bisection on velocity between 0.85 and 1.15 times the profile's, to within 0.5 fps). Only the
velocity moves. The figures below are the default .308 as it ships now (G7 0.25, 175 gr, 2600 fps, 1.5 in sight, 100 yd zero,
59 F, sea level, 50 %), measured with the solver; they were recomputed in the fix wave after the default moved from G7 0.243.

- **Only the velocity is corrected, never the coefficient.** One shot gives one number, and a velocity and a coefficient cannot
  both be found from it. Velocity is the figure a person is least sure of (chronograph, barrel, temperature) and the one a
  single shot at distance is most sensitive to. Cost if wrong: the velocity absorbs any error that is really in the
  coefficient, and it is right only near the distance of the shot. With a coefficient 7 % too high (0.2675 for 0.25) a shot at
  600 yd gives 2569 fps, and the card is then 0.02 mil off at 400 yd, 0.09 mil off at 800 yd and 0.28 mil off at 1,000 yd.
  Nothing on screen says the fit belongs to one distance beyond the line under the heading.
- **Refused under 300 yd.** Near the muzzle a small misreading becomes a large velocity error: a 0.1 mil misreading at 300 yd
  moves the answer by 69 fps (2.7 %), and at 200 yd it would be larger still, past what a person could judge. Cost if wrong:
  a person with a real, careful 250 yd shot is turned away and must shoot farther; a limit set lower would let wild velocities
  through as results.
- **Refused where the bullet is below Mach 1.2 at that distance, with the profile's own velocity or with the velocity found.**
  Through the transonic zone the drag table changes fast, so the same angle comes from very different velocities, and the error
  is in the coefficient curve, not the velocity. The default .308 is Mach 1.22 at 800 yd, 1.16 at 850 yd, 1.11 at 900 yd and
  1.00 at 1,000 yd, so a shot past about 815 yd is refused. The refusal now says what to do: "Use a shot at a shorter distance."
  The check at the velocity found (final maths review) is made in the editor (`src/bal-edit.js`, with `BAL.solve` at the found
  velocity), not inside `BAL.trueMv`: putting it in `BAL.trueMv` changes an existing solver test (the -14.9 % boundary case at
  600 yd is below Mach 1.2 there), and that test file is kept untouched. Cost if wrong: a person shooting a slow load far out
  cannot use this at all; a limit nearer Mach 1.0 would give them a velocity that is mostly the drag table's error; and any
  other caller of `BAL.trueMv` (there is none) would not get the second check.
- **A change over 5 % warns; a change over 15 % is refused, counted from the profile's original velocity.** 5 % of 2600 fps is
  130 fps, which is 0.61 mil at 600 yd; 15 % is 390 fps, 2.2 mil. A real chronograph difference between a box and a rifle is
  usually a few percent; more than that points at the distance, the zero or the sight height. The numbers are judgement, not
  measured. The 15 % is measured by `BAL.trueMv` against the velocity in the field and also by the editor against the original
  velocity (the profile's `mv0` if it has one, otherwise the velocity the sheet opened with), so two corrections cannot add up
  past it (final code review). Cost if wrong: a rifle that really is more than 15 % off its stated velocity (a much shorter
  barrel than the load was tested in) is refused and the person must edit the velocity by hand; a limit too wide would let a
  typing slip through as a result.
- **The shot is read level, with no wind, in today's conditions from the Ballistics screen.** The part's line says so. The
  profile's zero conditions are used as the zero air. Cost if wrong: whatever the shot had in it is folded into the velocity.
  At 600 yd on the default .308: a 20 degree incline gives 2681 fps (+3.1 %) for a rifle that is really at 2600; air at 20 F
  when the screen says 59 F gives 2568 fps (-1.2 %); a 10 mph wind along the line of fire gives 2594 fps (-0.2 %), because it
  barely moves the drop. A crosswind does not affect elevation here.
- **The original velocity is kept and can be put back.** The first correction stores the velocity the sheet opened with as
  `mv0` on the profile; later corrections leave it alone; "Put back" writes it into the velocity field and the sheet's Save
  removes it. A copy made with "Save as new profile" carries `mv0` only when a correction was applied in that sheet. Editing the
  velocity by hand never creates or removes it. Cost if wrong: a person who corrects, then hand-edits, then corrects again
  can only put back the first velocity, not an in-between one; and a profile that has been corrected keeps a second number in
  storage (and in a backup) that older copies of the app drop on their next save.
- **A worked-out velocity is never lost without a question (final drive).** "Work it out" scrolls the result (or the refusal)
  and the Use button into view above the sheet's buttons. Save or Save as new with a result that has not been used asks "Use
  the corrected velocity?" with "Use it and save" and "Save without it"; closing the question (Back, Escape, a tap outside)
  saves nothing and leaves the sheet as it was. A result is cleared only when the distance, the elevation or the unit (or the
  sheet's own numbers it was worked out from) really changes, never merely because a field lost focus. Cancel asks Keep editing
  / Discard when anything changed, as Back does (R33).
  Cost if wrong: one more question on the way out; on an iPhone (no Back button) the question is closed only by a tap outside
  it, since the ruling named exactly two choices.
- **The editor reaches the screen through two objects (fix round 1, widened in the fix wave).** `FK.bal` is the public surface
  (its keys are pinned by tests); `FK.balHost` is a read-only seam for `src/bal-edit.js` only: `find`, `newId`, and the one
  definition of each rule the editor shares with the screen (`RANGE`, `CLICK_SIZES`, `within`, `marksOk`, `parseNum`,
  `zeroAir`, `nameTaken`, `freeName`; final code review C13). The editor's range refusals are worded from `RANGE`. Cost if
  wrong: two objects to know about, and a change to the screen's profile handling must keep both in step; nothing outside
  `bal-edit.js` may use `FK.balHost`.
- **`mv0` is written only when it means something (fix round 1).** At Save, a profile without `mv0` gets the velocity the sheet
  opened with only if a correction was applied since the last Put back and the velocity being saved differs from it; a profile
  that already has `mv0` keeps it through put back and correct again; Put back then Save removes it; a copy made after Put back
  has none. Cost if wrong: a person who corrects and then types the old velocity back gets no `mv0`, so no "Put back" later
  (nothing is lost: the velocity is the same).

## Decisions recorded in the build ledger (R6 to R35)

These were made by the controller while the release was built and lived only in its ledger until the final code review. Those
that concerned only the order of the build (R1 to R5, R14) are left out. Each says what was decided, why, and its cost if wrong.

- **R6. A test that compared against a commit no longer on GitHub was replaced by a checksum.**
  `tests/test_final_fixes.py::test_v77_search_fixture_is_unchanged` compared the fixture with commit 594a3ad, removed at the v7.8
  squash, so it failed in every fresh clone; it now checks the fixture's sha256 (identical to main 22efd72). Cost if wrong: none;
  the fixture is still pinned.
- **R7. A coefficient published by the ammunition maker for its own loaded cartridge is an acceptable source**, provided the
  load's name names that cartridge (recorded above as Ruling A). Cost if wrong: Federal's rounded G7 0.25 against the commonly
  used 0.243 is 0.29 mil less elevation at 1,000 yd for the default load.
- **R8. The release carries 5.56 and 7.62x39 loads** from makers that print a labelled coefficient and a velocity with its barrel
  length (recorded above as Ruling B); the retired ids p556 and p76239 are never reused. Cost if wrong: none if sourced.
- **R9. A stored selection of a built-in load always shows that load's current numbers** (recorded above). Cost if wrong: on
  update a phone on the default .308 sees its card move (500 yd U 3.6 to U 3.5 mil) without anyone editing; it is on the
  phone-check list.
- **R10. p223 keeps its id**: it is the same slot (a .223 Rem 77 gr match load) with sourced figures; a new id would orphan every
  phone that selected it. Cost if wrong: none beyond R9.
- **R11. The exact words of the dope-card columns and cells, and "a malformed sight is no sight"**, were fixed by the controller
  because the plan only outlined them and the screen's tests needed exact strings. Cost if wrong: none (wording since changed by
  the final drive, R35).
- **R12. A stored selection of a retired built-in is handled like a stored "custom"**: with a coefficient and a velocity stored,
  the own profile `ucustom` is made from them and selected; there is no unsaved entry. Its name is now set by R34. Cost if wrong:
  none.
- **R13. The `FK.bal` method contracts** (what `save`, `select`, `remove`, `clean`, `profiles`, `selected` take and give) were
  fixed by the controller because later tasks consumed them. Cost if wrong: none.
- **R15. The editor's wording, validation messages, marks parsing, click choices, headings and guard wording** were fixed by
  the controller because the plan left them open. Cost if wrong: wording Jordan may want changed (several messages were since
  reworded by the final reviews: R26 to R32).
- **R16. The marks box is a plain text field with the full keyboard**, with the hint "Separate marks with spaces or commas, like
  1.5 3 4.6.", and a comma is a separator: a keypad that cannot type a separator makes the feature unusable on iPhone. Since the
  final drive, a box that has both spaces and a comma between two digits ("2,5 6,5") is refused with "Use a point for decimals:
  2.5, not 2,5."; "1,5" alone still reads as the marks 1 and 5. Cost if wrong: someone who types "1,5" meaning 1.5 with no other
  mark gets marks 1 and 5 accepted.
- **R17. A zero-conditions pressure must be in range when given, and `clean()` drops an out-of-range temperature, altitude or
  pressure from a stored `zeroAtm`** (a restored backup could carry them). The pressure range is now 8 to 33 inHg (R27). Cost if
  wrong: none.
- **R18. The dope card's columns** are Yd, the sight's elevation and wind columns, then the path, drift, fps, ft-lb and time; a
  reticle drops the separate drift column because its wind columns already carry the hold. Cost if wrong: none.
- **R19. The words of the sight line, the range and conditions messages, and that a new profile is made by editing a built-in
  and saving it as new** (no separate New button). Cost if wrong: wording Jordan may want changed.
- **R20. The answer card compacts only while a Ballistics input has focus and the screen is short; a message is always shown.**
  A landscape phone with nothing focused gets the full card. "Short" is now decided from the visible height (R29), not a media
  query. Cost if wrong: none.
- **R21. A blank humidity means 50 %**, as a blank temperature means 59 F. Cost if wrong: none.
- **R22. "Correct from a real shot" works on the values in the editor sheet; "Use NNNN fps" writes into the velocity field and
  the sheet's own Save stores it** (one save path, covered by the unsaved-changes guard). Cost if wrong: one more tap (Save)
  after a correction.
- **R23. `FK.balHost` is the editor's internal seam** (recorded above). Cost if wrong: two objects to know about.
- **R24. `mv0` is written only when it means something** (recorded above). Cost if wrong: none.
- **R25. A turret shows the dialled value**: clicks times click size, with the click's decimals (one for 0.1 mil, 1/2 and 1; two
  for 0.05 mil and 1/4; three for 1/8) and the direction letter whenever a click is dialled. "0.0 mil / 1 click" was possible.
  At 500 yd (drop 64.3 in) with 1/4 MOA it reads "U 12.25 MOA", "49 clicks"; 0.1 mil is unchanged. The dope card's turret cells
  follow it; "Show all units" and the no-sight form stay the true angle to one decimal. Cost if wrong: the turret line shows the
  nearest dialable value, not the exact need (at most half a click apart).
- **R26. Save and Save as new refuse a name another profile or a built-in already has** (trimmed, any case): "Give the profile
  its own name." A built-in opens with " (mine)" after its name (" (mine 2)" and on if taken, cut to fit 60 characters). Two
  entries with one name and different numbers were possible. Cost if wrong: one forced rename.
- **R27. One station-pressure range, 8 to 33 inHg, everywhere** (screen, editor, stored zero conditions): a slipped decimal
  (2.992) gave a confident wrong answer (U 2.6 mil at 500 yd where U 3.5 is right). Cost if wrong: a true reading outside it
  (none on land) is refused.
- **R28. Enter never saves the profile**; in the correction part it runs "Work it out"; elsewhere in the editor it does nothing.
  A keypad's action key could store a half-finished edit. Cost if wrong: no keyboard shortcut for Save.
- **R29. The short-screen state is decided in JavaScript from the visible height** (`visualViewport` where there is one, else
  the window), re-checked on resize and focus changes, and the focused field is kept between the pinned card and the tab bar or
  the bottom of the visible viewport. A media query cannot see a real phone keyboard. Cost if wrong: unverified until the phone
  check (see "What could not be tested").
- **R30. Incline, temperature and altitude (five fields) open the ordinary keyboard and take the typographic minus (U+2212)**,
  as the wind chill box does (v7.3 rulings, item 24): iPhone number pads have no minus. One reader parses every typed number on
  the screen and in the editor; anything unreadable is refused, never read as 0. Cost if wrong: a few more taps to reach digits.
- **R31. Plausible ranges for a load**: coefficient 0.05 to 1.2, weight blank/0 or 1 to 1,000 gr, velocity 300 to 5,000 fps,
  zero range 5 to 1,000 yd, sight height 0 to 6 in, enforced by the editor; a stored profile outside them is kept and the screen
  asks for an edit. Absurd input printed absurd numbers ("3002648 fps", "Infinity ft-lb"). Cost if wrong: an unusual but real
  load outside them is refused (the ranges are wide).
- **R32. A stored drop reticle with any bad mark, more than ten marks or marks out of order loses its whole sight** (it was
  renumbered or cut short), and the editor measures the 15 % correction limit against the original velocity. Cost if wrong: a
  hand-edited backup with one bad mark shows every unit until the sight is set again.
- **R33. In the profile editor, Cancel asks Keep editing / Discard when there are unsaved changes**, overriding "the sheet's own
  Cancel does not ask" for this sheet: a worked correction or a whole rifle set-up could be lost by one tap. The marker sheet
  keeps its own rule. Cost if wrong: one more tap to cancel.
- **R34. A migrated retired built-in is named for what it was**: "5.56 NATO 62 gr (old built-in)" for p556, "7.62×39 123 gr (old
  built-in)" for p76239; a stored "custom" still becomes "Custom"; the id stays `ucustom`. "Custom" gave no clue which rifle it
  was. Cost if wrong: none.
- **R35. The screen's words and layout from the final drive**: "Show all units" keeps the sight's own lines and adds the other
  units beneath, and reads "Hide other units" (pressed) when on; the dope card scrolls in its own box (at most 70 % of the
  visible height, at least 240 px) with a sticky heading row and yard column; headings say elevation or wind ("Elev clicks",
  "Wind hold in") and click cells carry their direction ("U 36"); transonic rows carry a dagger with the note "† Below Mach 1.2
  (transonic): less certain. Confirm these with real shots."; the sentence says "63.6 in low, drift 21.2 in left" and the Drop
  column is "Path in"; past a reticle's last mark the answer is a hold in the reticle's unit and inches; a load line under the
  picker, and for a built-in load a line asking for a chronograph reading; help under both pressure fields saying to leave them
  blank without a true station reading. Cost if wrong: wording and layout Jordan may want changed.

## Decisions made in the final fix wave (2026-11-21)

- **The question about an unused correction needs three answers**, so `FK.sheet.confirm` gained `choice: true`: it resolves
  'ok' or 'cancel' for the two buttons and null when closed any other way, and focus starts on the title so a stray Enter takes
  neither. Without it, closing the question could not be told from "Save without it". Cost if wrong: none to other callers
  (their answers are still true or false).
- **The drift column keeps its unsigned figures.** The final drive asked the hint to match the column's actual sign
  convention; the column has always been unsigned (and `BEFORE` pins it so), so the key under the card reads "Path: inches above
  the line of sight; a minus means below. Drift: inches the wind moves the bullet, shown without a sign." (the drift part is
  left out for a reticle, which has no drift column). The sentence under the answer gives the drift's direction. Cost if wrong:
  the direction of the drift is read from the sentence or the wind columns, not the drift column.
- **"Show all units" affects the answer card only** (second pass). The dope card is always built from the profile's sight: clicks
  for a turret, mark and hold for a reticle, hold for a dot; a profile with no sight shows every unit as before. The other-unit
  lines on the answer card skip any line equal to the sight's own main or sub line, case ignored ("hold 22 in right" is not
  repeated as "Hold 22 in right"). Cost if wrong: the dope card never shows mil and MOA side by side for a sighted profile.
- **While the card is pinned (keyboard up) the extra units are hidden**, like the button and the sentence, so the card stays
  short. Cost if wrong: none; they come back when focus leaves.
- **A reticle's windage with no hold reads "No hold"** (it read "0 in"), and the path at the zero reads "on the line of sight".
  Cost if wrong: wording.
- **Spacing on the main screen was tightened** (the card's padding and gaps, the lines under the picker, the shot fields'
  gaps, the card's labels) for the load line, the chronograph line and the button beneath the sentence. Measured at 360 x 640,
  the space between the bottom of the wind fields and the top of the tab bar (negative: partly under the bar): built-in .308
  load +6 px; turret 0.1 mil with zero conditions 0; red dot +10; red dot with zero conditions -10; mil reticle +20; MOA reticle
  past its last mark -29; MOA reticle with zero conditions -48; 1/8 MOA turret with zero conditions -29; built-in loads at ranges
  where the "Subsonic" sentence shows -12. So the first screen does not always hold all four shot inputs: this is an accepted
  limit on a 360 x 640 screen (the wind fields are reached with a short scroll; nothing is cut off), and the owner's phone is
  taller. It is on the phone check. Cost: on the smallest phones, one short scroll to reach the wind fields for some profiles.
- **A second, narrow fix pass was run after the final re-check found a fault in the first fix.** A velocity worked out with
  Enter was cleared by the change event the next tap fired, so Use did nothing and Save stored the old velocity with no
  question (reopening D1); a result is now cleared only when what it was worked out from really changes. The same pass made the
  dope card keep the sight's own columns with other units shown, stopped a repeated hold line, hid the load line for a profile
  the screen cannot use, and let a swipe at the end of the dope box carry on to the page. Cost: none beyond the entries above.
- **A pre-existing flaky test was fixed**: `tests/test_map_tools.py::test_navigating_away_leaves_the_mode_and_keeps_nothing`
  checked for no route mode in the two animation frames before the designed resume of an unfinished route (v7.8 rulings) and
  failed about one run in four, at the base commit too. It now waits for the resume. Cost if wrong: none.

## Accepted limits

- **The four shot inputs are not always on the first screen at 360 x 640** (measured figures under "Decisions made in the final
  fix wave"). The wind fields are a short scroll away for profiles with zero conditions, a MOA reticle past its last mark, or a
  subsonic range. Cost: one short scroll on the smallest phones.

- **The profile editor is cramped in landscape** (final drive). Not fixed in this release: the sheet's own scroll still reaches
  every field and button. Cost: more scrolling on a landscape phone.

## What could not be confirmed

- **Independent re-entry (final maths review, 2026-11-21).** Three outside cases re-entered by the reviewer agree with this
  record's figures to 0.002 mil; the sanity checks pass (vacuum limit, wind symmetry, the Didion lag rule to 0.01 in, `trueMv`
  recovering known velocities). Verdict: trustworthy to 600 yd given a correct muzzle velocity; at 1,000 yd the default .308 is
  good to about ±0.3 to 0.4 mil only (below Mach 1.2 from about 815 yd, the coefficient 0.243 against 0.25, and spin drift and
  Coriolis, about 0.4 mil sideways, not modelled).
- **The Zdziarski pressure reading** (taken as the pressure at the firing point, above) is supported by the table's velocity
  column, which the solver matches to 0.04 % at every row; the two readings differ by 2.9 % in density, which would show in the
  velocities.
- **The G7 gap past 500 yd stays open.** The closest lead is ballistics-engine's validation data,
  `data/validation/xref_g7_supersonic_308.json` and `xref_g7_transonic_reach.json` (inputs in its generator script: G7 0.243,
  800 m/s, 175 gr, ICAO, sight height 0); no search returned their URLs, so they were not opened.

## What could not be tested

- **The pinned answer card with a real phone keyboard.** The short state is decided from `visualViewport` (R29) and the tests
  stand in a fake visual viewport and shrink the window; how iOS Safari and Android Chrome move the page, the sticky card and the
  tab bar when a real keyboard opens was not seen.
- **The ordinary keyboard on the five below-zero fields** and the typographic minus on a real iPhone keyboard.
- **The dope card's own scroll box inside the page** with a finger on iOS (a scroll box inside a scrolling page).
- **The question about an unused correction on an iPhone**, where it is closed only by a tap outside it.

## Phone check for this release

1. With the keyboard up on Target range, Wind speed, Temperature and Humidity, in portrait and in landscape: the answer card
   stays at the top of what can be seen, and the field being typed in is visible below it and above the keyboard or tab bar.
2. Type a temperature below zero on an iPhone (the ordinary keyboard; its minus works) and an incline below zero.
3. In the editor of an own profile: Work it out shows the result and the Use button without scrolling by hand; Save without
   pressing Use asks first; a tap outside the question goes back to the sheet with nothing saved; Cancel after Use asks.
4. Scroll the dope card down and across with a finger: the headings and the yard column stay put, and a swipe that reaches the
   end of the card's box carries on to scroll the page.
5. With the keyboard up, scroll away from the field you are typing in: the page should let you.
6. On the smallest phone in the group, check the wind fields are reachable for a profile with zero conditions.
7. Night mode: the transonic rows carry the dagger and the note reads.
8. A turret with 1/4 MOA clicks: the angle shown is clicks times a quarter (for example U 12.25 MOA, 49 clicks).
9. The earlier list still applies: Settings shows "Version 7.10" (seven point ten, the release after 7.9); v7.8 profiles survived; set up one real rifle with its sight;
   compare the card with elevations already known at two distances; count clicks on a real turret; read a real drop reticle's
   marks from its manual; Back on the editor with typing in it.
10. On an iPhone, open a rifle profile both ways (a new one from a built-in load, and Edit on your own): the whole form shows
    with its buttons above the home bar. The sheet fills the screen with Save and Cancel at the bottom (v7.9 fixed other
    sheets that showed only as a strip at the bottom edge; the profile sheet had the same fault and the same fix).

## Release

- **Main moved during the build.** v7.9 (iPhone: Marker, Tools and list sheets) was released from another session at 21:21 on
  2026-11-21. The branch took it in by a merge, with no conflicts. Cost if wrong: none found; the full suite ran on the merged
  release build (108 content checks, 2,245 browser tests, 0 failed).
- **The profile sheet had the fault v7.9 fixed.** `#rfForm` used `flex: 1` inside an auto-height sheet, which Safari sizes to a
  strip. It now uses `flex: 1 1 auto`, and v7.9's own test covers every sheet of this kind. This one-line change was made by the
  controller at the merge and was not separately reviewed. Cost if wrong: the sheet's height on iPhone; item 10 above checks it.
- **Version 7.10.** 7.9 was taken, so this release is 7.10 (ten, not one-zero). The app compares versions as numbers, so 7.10
  is newer than 7.9 for backups and updates (`tests/test_migration.py` covers dotted versions). Cost if wrong: someone reads
  "7.10" as "7.1"; the alternative, 8.0, is reserved for the team map.


## Release 2

- **Stability bands use the paper's numbers, 1.0 and 1.4, not the expected 1.0 and 1.5.** Courtney and Miller name no
  "marginal" band: tumbling near 1.0, recommended range 1.4 to 2.0, drag rising below about 1.3. `unstableBelow` is 1.0 and
  `marginalBelow` is 1.4 (the bottom of the recommended range). Other tools use 1.5 (ballistics-engine's "adequate" comment,
  Josef's calculator). Cost if wrong: a bullet at Sg 1.4 to 1.5 shows "stable" where a stricter reader would say "marginal".
  Changing it is one constant and one fixture value.
- **The stability example is worked backwards from Wikipedia's twist.** No opened page prints a bullet's inputs and its Sg from
  the corrected formula. The one worked example (180 gr .308, 1.18 in, Sg 2.0 gives 39.2511937 calibers per turn) takes
  "Mach 2.5, about 2800 fps" as 2800 fps and standard air; the result is 1.997, tested to 0.01. The independent check is the
  formula written out again in Python (relative 1e-9). Cost if wrong: the velocity and air corrections are checked only
  against the paper's equation, not against a printed number.
- **Spin drift is confirmed by two statements that agree, not by a publisher's worked example.** ballistics-engine and a Sniper's
  Hide post (quoting Litz's estimator, with a five-row table) give the same formula and six agreeing numbers. Litz's own
  publication was not opened. Cost if wrong: the estimate follows a secondary copy of Litz's formula.
- **No bullet length or diameter entered for any built-in load.** The only lengths found were a forum member's measurement
  (175 gr SMK, 1.232 in) and no publisher figure; none of the six passed the rule "from a page I opened". `bullets` in the fixture is
  empty and every built-in asks for its bullet. Cost if wrong: the user types one more number per built-in load.
- **`grade` of a non-number is 'unstable'**, but `of` never returns it for a figure that is not a number: it returns
  `{ missing: [...] }` whenever the stability figure is not finite. The list names what is absent (twist, bullet length, bullet
  diameter, bullet weight, then muzzle velocity); when only the air is unusable the list is empty. Callers treat any `missing`,
  even an empty one, as "spin drift not applied" and never read `sg` from it. (Replaces the first version, which returned
  `sg: NaN` with grade 'unstable'.) Cost if wrong: a caller that tests only `missing.length` will treat an unusable-air result
  as "nothing missing"; the rule is to test for the key, not the length.
- **`of` reads no `twistDir` other than 'L' as left**; anything else, including absent, is right (+1). Cost if wrong: a left-twist
  rifle with a mistyped direction drifts the wrong way.
- **The ballistics-engine 8.40 in drift example is not an independent check.** Its test computes the expected value from the same
  formula, so it only shows that the formula was copied correctly. It stays in the fixture, labelled; the five Sniper's Hide rows
  are the independent check. Cost if wrong: none to the app; a reader who took 8.40 as confirmation would over-trust the formula.
- **Barrel and bullet fields are four independent optional fields; whatever is valid is stored** (a left twist with no twist rate
  is kept). Cost if wrong: a profile can hold a direction with nothing to apply it to; harmless, as nothing reads it alone.
- **Range messages for the new fields:** "Twist must be between 3 and 30 inches per turn.", "Bullet length must be between 0.2 and
  3 in.", "Bullet diameter must be between 0.17 and 0.6 in." (the editor's one `between()` helper). Cost if wrong: wording only.
- **The 2 to 7 caliber rule is inclusive and allows 1e-9 for the division** (7 x .308 = 2.156 divides to 7.000000000000001). The
  editor refuses it; `clean()` drops `blen` and keeps `bdia`, because the length is what was measured by hand. A diameter that is
  itself out of range is dropped first and then decides nothing. Cost if wrong: a length exactly at the edge is refused or kept
  by a hair; a bad diameter costs the length its check.
- **Built-in loads gain none of the four fields** (Task 1: no bullet dimension sourced), so a built-in copied with "Save as new
  profile" starts with all four blank. Cost if wrong: the user types the bullet's numbers once per saved copy.
- **The stability line uses only values that are valid on their own** (inside RANGE, and a length that fits the diameter); anything
  else hides the line, and Save's own refusal explains it. Station pressure comes from `BAL.atmosphere` (today's pressure, or
  from altitude when none is typed), so it is the figure the solver uses. Out-of-range air on the screen gives standard air
  (59 F, sea level), as the brief says. Cost if wrong: a profile with a typo shows no line instead of a wrong one.
- **Typing in the four new fields does not clear a worked-out velocity** in "Correct from a real shot" (its snapshot ignores them),
  though they do make the sheet dirty. A shot correction also ignores a bad value in them. Cost if wrong: a correction stays on
  screen after a twist change, which does not affect it.
- **The twist label says "inches per turn"; the direction select is Right / Left, Right first and the default.** Cost if wrong:
  wording only.
- **The stability figure is printed rounded DOWN to one decimal, through one helper, `BSPIN.text(sg)`** (1.38 prints "1.3", 0.97
  "0.9", 1.4 "1.4", 2.4003 "2.4"; empty for a non-finite figure; 1e-9 guards exact decimals against binary error). The grade is
  decided on the unrounded value, so rounding to nearest showed "Stability 1.4: marginal" against a 1.4 threshold. The editor
  and, in Task 3, the screen use the same helper. Cost if wrong: a shown figure can read up to 0.1 lower than other calculators give.

### Release 2, Task 3 (spin drift on the screen)

- **An unstable bullet gets no spin drift, and the line says why** (the brief's call). Its Drift column and key stay as in v7.11
  (unsigned inches). Cost if wrong: a tumbling bullet's windage is the wind alone, which is not what it would do.
- **The spin share is worked from each row's own flight time and the stability for today's air** (today's temperature and the
  station pressure the solver used, `res.atm.pIn`; the zero's air plays no part, as a gyroscope sees only the air it flies in).
  The solver is not touched: `rowFor` adds `spinIn` to `windIn` after it. Cost if wrong: a hot or high day moves stability a few
  hundredths, which moves drift by well under 0.1 in at 1,000 yd.
- **The dope card's letter says where the bullet goes, not where to hold.** `5.2 R` is a bullet 5.2 in right of the line of sight
  (as the sentence under the card says "right"); the windage answer above is the opposite hold ("L"). Cost if wrong: a reader
  takes `R` in the Drift column as a hold; the key says "inches the wind and the spin move the bullet".
- **A figure that rounds to 0.0 has no letter** in the Drift column, and a spin share that rounds to under 0.1 is not named in
  the sentence. Cost if wrong: none seen; it keeps `R 0.0` off the screen.
- **The line under the dope card on a message path** (bad range, wind, incline or conditions, a profile the screen cannot solve,
  a solver error): nothing is solved, so it never says spin drift is included. It names what the profile lacks when it lacks
  something (`BSPIN.of(p, null)` gives the list without air), otherwise `Spin drift not included. Coriolis is not included.`
  The same short text is used when `missing` is empty. After a solve that finds the target out of reach, the line is the normal one,
  since the dope card still carries spin drift. Cost if wrong: wording only.
- **Built-in loads read "add twist, bullet length and bullet diameter to the profile."** (they carry none of the four fields); the
  list is `missing` joined with commas and a final "and" (`a`, `a and b`, `a, b and c`). A profile that lacks weight or velocity
  names those too. Cost if wrong: wording only.
- **The crossing test uses a 1.2 mph wind from 3 o'clock, not 2 mph.** With this .308 load and 1:10 twist, 1 mph never leaves
  the right side, 1.5 mph and up stay left to 1,500 yd, and 1.2 mph crosses near 1,000 yd. Cost if wrong: none; the test pins
  one real crossing, found by running the card.
- **The formula test reads 600 yd and states its bounds.** The screen shows each figure to 0.1 in and the time to 0.01 s. Against
  the formula worked from the solver's unrounded flight time only display rounding differs (tolerance 0.06 in; the probe shows
  0.012). Against the printed time: 0.05 in rounding plus 1.83 x drift / tof x 0.005 s, about 0.06 in at 600 yd (tolerance 0.15).
  SPIN minus PLAIN adds a second rounded reading (tolerance 0.17). (An earlier note here said the 600 yd difference could be 0.12;
  that was wrong.) Cost if wrong: a test that fails on rounding, not on the formula.
- **When the target is out of reach the line says "The dope card includes spin drift (...)", not "Windage includes ..."**, since
  the answer card's WINDAGE shows a dash and only the dope card carries the share. Same bracket rules as the normal line. Cost if
  wrong: wording only.
- **The shot-field tests wait on the stored copy** (`localStorage['fk.bal']` holding what was typed), which `later()` writes in the
  same tick as the recalculation. No sleeps in the Task 3 tests (the older helpers are unchanged).
