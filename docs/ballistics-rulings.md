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

Where the standard matters is a coefficient quoted against one standard and used as if it were the other. Dexadine's Ballistic
Explorer help and a Long Range Hunting post both give the conversion as a factor of 1.018 (Metro to ICAO, 0.982 the other way);
ballistics-engine gives 0.075126 / 0.076474 = 0.98237. Measured on the default profile at 1,000 yd:

| Coefficient used | Elevation | Wind | Velocity |
|---|---|---|---|
| 0.243 as entered | U 11.97 mil | R 3.10 mil | 1091 fps |
| x 0.982 (other standard one way) | U 12.16 mil (+0.19) | R 3.19 mil (+0.08) | 1077 fps |
| x 1.018 (the other way) | U 11.79 mil (-0.18) | R 3.02 mil (-0.08) | 1108 fps |

Report only; the solver is not changed for it. Cost if a user enters a Metro-referred coefficient as ICAO (or the reverse):
about 0.2 mil of elevation at 1,000 yd and about 0.03 mil at 500 yd.

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
| p556, p76239 | as above | retired, never reused | their numbers had no source; a stored selection falls to Custom (below) |

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
text holds no load name, so `BEFORE` was not touched again; the two tests that used `p556` use `p223`.

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
  Federal labels only its G7 (.188). Cost if wrong: at 1,000 yd the elevation differs by 0.7 mil from the old figure. A phone that
  already holds p223 keeps its stored numbers until the profile is selected again, then shows the new ones.
- **p65cm kept at G7 0.326, Hornady's Mach 2.25 value, although Hornady says the Mach 1.75 values (G7 0.310) are the ones to use
  beyond 600 yd.** 0.326 is the one Hornady says to use when comparing with other published coefficients, and it is what the load
  already held. Cost if wrong: beyond 600 yd the drop is understated; at 1,000 yd with 0.310 the elevation is U 9.11 mil against
  U 8.86 mil (0.25 mil, about 9 in), and 500 yd differs by 0.04 mil. Hornady also refers its coefficients to Army Standard Metro
  air; the solver reads every coefficient as ICAO (see "Standard atmosphere of the coefficient"), a further 1.8 % on the
  coefficient (up to about 0.2 mil at 1,000 yd).
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
  1585 against 1642 fps; the table's own value changes again beyond 600 m, which a single coefficient cannot follow. The velocity
  is RWS's 925 m/s at v10 (10 m from the muzzle), treated as the muzzle velocity; its second line, 914 m/s "assault rifle", was not
  used. Cost if wrong: a muzzle velocity a few metres per second too low (not measured).
- **p76239sb is 124 gr, not 123 gr, and G1 0.286.** Sellier & Bellot's only 7.62x39 FMJ row is 124 gr; Hornady's 123 gr SST page
  prints no coefficient, and no maker page with a labelled coefficient for a 123 gr FMJ was found. G1 was chosen for this
  flat-base bullet (S&B also prints G7 0.143); with G7 0.143 the 500 yd elevation is U 5.54 mil against U 5.45 mil (0.09 mil) and
  the velocity 1146 against 1219 fps. Cost if wrong: about 0.1 mil at 500 yd. The velocity 2421 fps is S&B's 738 m/s, the barrel
  20.5 in is 520 mm. A phone selecting the old 123 gr p76239 now meets the Custom fallback below, not a 124 gr load.
- **No 16 in barrel velocity was added.** The only 16 in figures found are PMC's (55 gr 3120 fps, 62 gr LAP 2920 fps, its
  catalogue states "Barrel Length: 16 inches"), and PMC prints its coefficients (0.243, 0.304) with no drag model anywhere; Federal's
  Fusion MSR 62 gr is 2750 fps at 16 in with no coefficient. Under the rule a coefficient with no model is unusable, so no load
  was built on them. Cost if wrong: the AR loads are all 20 to 24 in velocities; a 16 in carbine is slower, and the user must enter
  its velocity by hand.
- **No M855 or Hornady 62 gr load.** RWS's SS109 is the NATO 62 gr round with a labelled coefficient; the U.S. M855 pages
  (Winchester catalogue, Federal, an unnamed maker's data sheet) gave no model or no barrel length. Cost if wrong: none to
  existing screens.
- **A phone whose stored selection names a retired load shows "Custom (unsaved)" and keeps the numbers it had.** The existing
  code already does this (an id that is not in the list falls to Custom, and the stored field values are restored); a test covers
  both retired ids and checks that no console error is raised. The alternative, loading another built-in load, would swap the
  user's coefficient and velocity without warning. Cost if wrong: such a phone keeps showing the old p556 or p76239 numbers under
  "Custom (unsaved)" until the user picks a load; those numbers are the unsourced ones.
- **Sight height and zero left as they were** (sight height 2.6 in for the AR loads and p223, 2.0 in for p76239sb, 1.5 in for p65cm
  and p308, all zeroed at 100 yd); they are the app's own starting values, not sourced.
