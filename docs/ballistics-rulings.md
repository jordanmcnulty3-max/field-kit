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
- **Zdziarski post: pressure taken as the pressure at the firing point, and muzzle velocity as the table's 0 yd row (2606 fps).**
  The post does not say whether 30.13 inHg was corrected to sea level. As station pressure the velocities agree to 0.04 %; as
  sea-level pressure they would be about 1.2 % fast at 500 yd. The program zeroed in standard air and fired in the stated air;
  this app zeros in the firing air, a difference inside the table's own 100 yd figure (-0.01 in). Cost if wrong: the only .308
  case past 500 yd would not count; it is the case closest to the default profile.
- **pyballistic humidity entered as 0 %.** The library's default humidity constant is named but its value is not printed on the
  page that opened. Humidity at 59 F moves density by under 1 %; the velocities agree to 0.1 fps. Cost if wrong: none to the
  verdict.
- **Wind compared by size for pyballistic and Federal.** pyballistic prints a positive windage for a wind from 3 o'clock, its
  own convention; Federal gives no direction. The sign of this app's wind is checked by the Steiner table, whose drift for a
  wind from 3 o'clock is negative, as here.
- **Federal GM308M2 recorded but not judged.** The page states no atmosphere and does not label its .505 as G1. With Army
  Standard Metro assumed it agrees within 0.03 mil and 0.12 %, for information only.
- **Drag tables: only part could be checked against a printed source.** No page that opened prints every G1 and G7 pair
  (Sierra, Wikipedia and the JBM table image would not open or were not readable; the sources that opened give a few values or
  plots). The test checks the G1 values at Mach 0, 0.05 and 0.10 (ballistics-engine data README) and both curves at Mach 3
  (Applied Ballistics, two decimals), and checks the rest of each curve through the trajectories: G1 across the sound barrier
  (Steiner) and G7 to Mach 1.5 (pyballistic). Cost if a G7 value below Mach 1.5 were wrong: G7 trajectories past about 500 yd
  for the default profile would not be confirmed by any source here.

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
