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
`docs/content-review.md`, "Built-in loads"). The rule used: a load stays only if its coefficient, with the drag model the page
states, and its velocity, with the barrel length the page states, both come from an opened maker page. A retailer page or a
forum post counted for nothing. **Result: two loads changed, one kept as it was, two removed.** Nothing was added.

| Id | Before | After | Why |
|---|---|---|---|
| p65cm | G7 0.326, 2710 fps | same values, name now says 24″ barrel | Hornady's coefficient page gives G7 0.326 and Hornady's cartridge page gives 2710 fps from a 24 in test barrel |
| p308 | G7 0.243, 2600 fps | G7 0.25, 2600 fps, 24″ barrel | Federal prints G7 0.25 and 2600 fps from 24 in |
| p223 | G1 0.372, 2750 fps, "77 gr OTM" | G7 0.188, 2720 fps, ".223 Rem 77 gr MatchKing, 24″ barrel" | Federal prints G7 .188 and 2720 fps from 24 in; the bullet it describes is a Sierra MatchKing, not an OTM |
| p556 | G1 0.304, 3020 fps, 20 in | removed | no opened page gives a coefficient with its model for M855, and no page gives 3020 fps with a barrel length (the Winchester catalog measures 78 ft from the muzzle) |
| p76239 | G1 0.29, 2350 fps | removed | the only maker page opened is for a 124 gr Federal load with an unlabelled .298; the one page with a labelled G1 is a retailer's |

On the screen, default inputs (59 F, sea level, 50 %, 10 mph from 3 o'clock), before and after:

| Load | Range | Before | After |
|---|---|---|---|
| p308 | 500 yd | U 3.57 mil, R 1.22 mil, 1761 fps | U 3.54 mil, R 1.18 mil, 1782 fps |
| p308 | 1,000 yd | U 11.97 mil, R 3.10 mil, 1091 fps | U 11.68 mil, R 2.97 mil, 1119 fps |
| p223 | 500 yd | U 3.26 mil, R 1.54 mil, 1661 fps | U 3.34 mil, R 1.56 mil, 1638 fps |
| p223 | 1,000 yd | U 12.80 mil, R 3.90 mil, 1030 fps | U 13.53 mil, R 4.17 mil, 983 fps |

**BEFORE changed.** The test `BEFORE` in `tests/test_tactical_layout.py` pins what the screen shows for `p308` (the default) and
for `p556`. `p308`'s numbers changed, so the default pins were captured again from the screen, read the same way the test reads
it (`#solElev`, `#solWind`, `#solSub` and the dope card text, mil and MOA). `p556` no longer exists, so the second set now
pins `p223` (300 yd, 10 mph from 9 o'clock), captured the same way; the keys were renamed `p223_mil` and `p223_moa`. A comment
beside `BEFORE` names this ruling. The two tests that used `p556` (the second-profile readout and the save and delete test)
now use `p223`.

Decisions made without Jordan:

- **Federal's own pages accepted as the source of the coefficient for p308 and p223, although Federal is not the bullet maker
  (Sierra is).** Federal builds the cartridge and prints the model ("Ballistic Coefficient G7") on its own product page; the
  Sierra pages that opened either printed no coefficient (175 gr: the ballistics tab never loaded) or printed .372 with no model
  (77 gr). Federal's .505 and .372 carry no model label, so only the labelled G7 values were used. Cost if wrong: two default
  coefficients rest on a source one step weaker than the bullet maker. If Sierra's own G7 for either bullet differs, the
  .308 elevation at 1,000 yd moves by about 0.3 mil per 0.007 of coefficient (the 0.243 to 0.25 change above) and the .223
  by more, since its coefficient is smaller. Fix: open Sierra's ballistics data for both and replace.
- **p308 moved from 0.243 to 0.25.** The 0.243 came from the earlier build, with no recorded source. Cost if wrong: the default
  profile's drop is 0.03 mil lower at 500 yd and 0.29 mil lower at 1,000 yd than the old figure; if 0.243 was right, shots to
  1,000 yd land about 0.3 mil (11 in) low.
- **p223 changed from G1 to G7 and from "OTM" to "MatchKing".** The old G1 0.372 happened to equal Federal's unlabelled .372, but
  no opened page says .372 is a G1 value, and Federal's labelled G7 is .188. The old name said OTM; the loads opened are Sierra
  MatchKing. Cost if wrong: at 1,000 yd the elevation differs by 0.7 mil from the old figure. A phone that already holds p223
  keeps its stored numbers until the profile is selected again, then shows the new ones.
- **p65cm kept at G7 0.326, Hornady's Mach 2.25 value, although Hornady says the Mach 1.75 values (G7 0.310) are the ones to use
  beyond 600 yd.** 0.326 is the one Hornady says to use when comparing with other published coefficients, and it is what the
  load already held. Cost if wrong: beyond 600 yd the drop is understated; at 1,000 yd with 0.310 the elevation is U 9.11 mil
  against U 8.86 mil (0.25 mil, about 9 in), and 500 yd differs by 0.04 mil. Hornady also refers its coefficients to Army
  Standard Metro air; the solver reads every coefficient as ICAO (see "Standard atmosphere of the coefficient"), a further
  1.8 % on the coefficient (up to about 0.2 mil at 1,000 yd).
- **p556 and p76239 removed rather than kept on weaker sources.** Both could have been kept on a retailer page or an
  unlabelled coefficient; the rule says no. Cost if wrong: two common loads lose their one-tap starting point; a user can still
  type the load into the fields and save it as a profile. If a maker page with the model and barrel length is found later, add
  it under a new id.
- **No 55 gr 5.56 load and no 16 in barrel velocity added.** The only opened pages for 55 and 62 gr 5.56 (Federal American Eagle)
  state 24 in and no drag model, and no opened page gave a 16 in velocity. Cost if wrong: none to existing screens; the AR loads
  stay missing.
- **A phone whose stored selection names a removed load shows "Custom (unsaved)" and keeps the numbers it had.** The existing
  code already does this (an id that is not in the list falls to Custom, and the stored field values are restored); a test now
  covers both removed ids and checks that no console error is raised. The alternative, loading another built-in load, would swap
  the user's coefficient and velocity without warning. Cost if wrong: such a phone keeps showing the old p556 or p76239 numbers
  under "Custom (unsaved)" until the user picks a load; those numbers are the unsourced ones.
- **Sight height and zero left as they were** (sight height 2.6 in for p223 and 1.5 in for p65cm and p308, all zeroed at 100 yd); they are the
  app's own starting values, not sourced.
