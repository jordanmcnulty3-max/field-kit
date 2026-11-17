# Field Kit overhaul: design

Date: 2026-11-16. Status: approved by Jordan 2026-11-16 with two changes (advanced procedures included; no hard text cap). Baseline: v5 (commit 1775938).

## 1. Intent

Tactical is a tool; Emergency and Survival are reading material. Jordan's three complaints, in his words:
it is "difficult to find something fast", the content "isn't deep or broad enough", and "there needs to be
interactive elements". The overhaul turns both sections into things you act from, under stress, with no signal.

Field Kit is also becoming a shared kit for Jordan and up to about 15 close friends on a mix of Android and
iPhone, used off-grid, with the end goal of seeing each other live on the map.

## 2. Roadmap (agreed order)

| Phase | Release | What |
|---|---|---|
| 1 | v6 | Emergency rebuild, guided-protocol engine, app-wide search, favourites, back-button navigation |
| 2 | v7 | Survival rebuild (Tools, Situations, Library), iPhone support, QR hand-off sharing |
| 3 | v8 | Team map over Meshtastic radios (Android full; iPhone via Safari extension or the Meshtastic app) |
| 4 | v9 | Further Tactical improvements |

**This document specifies phase 1 in full** and fixes the shared foundations phases 2 and 3 depend on.
Phases 2 to 4 each get their own short design before they are built.

## 3. Goals, non-goals, anti-goals

**Goals (phase 1)**
- From opening the app to the first instruction of any emergency protocol in 2 taps or one search.
- About 50 emergency protocols and procedures (section 6) instead of 4 topics.
- Every protocol is guided: one step per screen, with timers, branches and tools built in.
- Everything works with no network, in night mode, one-handed.
- Every protocol names its published source and review date.

**Non-goals (phase 1)**
- Survival restructure, iPhone fixes, QR sharing (phase 2). Mesh features (phase 3).
- Diagnosis or prescription dosing.
- Mass-casualty triage (START), team medical cards. Backlog.

**Anti-goals (failure even if it works)**
- An action that is buried: the thing to do right now must be readable at a glance, with depth available beneath it.
- Cutting relevant information to save space. Jordan: "More is better."
- Any feature that needs a connection after install.
- A medical instruction that cannot be traced to a named published guideline.
- Losing running tourniquet timers or saved data when v5 updates to v6.
- A 911 or phone-dial button (standing decision).

## 4. Approaches considered

**Structure.** (A) Action-first: situation buttons, guided protocols, tools, library. (B) Better manual: same
read-it format with categories and search. (C) Tools only: bolt calculators onto the existing text.
B fixes two of three complaints, C fixes one. **Jordan picked A.**

**Live team map.** (1) Use Meshtastic/ATAK/iTAK alongside Field Kit. (2) Field Kit talks to Meshtastic radios
itself. (3) Rebuild as a native app. **Jordan picked 2, as phase 3**, accepting that iPhone is partial
(Safari has no Web Bluetooth; needs a third-party extension, or the friend uses the Meshtastic app and still
appears on everyone's map) and that it can only be proven with real radios in hand.

**Content storage (Claude's call).** Protocols as JSON data rendered by one engine, not hand-written HTML.
Reason: one renderer means consistent UX, the build can validate every protocol, search indexes it for free,
and phase 2 Situations and phase 3 report-sharing reuse the same data.

## 5. Phase 1 design

### 5.1 Emergency home

```
┌──────────────────────────────┐
│ Emergency              🔍  ☾ │
│ ┌──────────────────────────┐ │
│ │ ▶ Resume: Bleeding, 3/7  │ │  only if a protocol is in progress
│ └──────────────────────────┘ │
│ ┌────────┐┌────────┐┌──────┐ │
│ │BLEEDING││  NOT   ││CHOK- │ │  life threats, always on top
│ │        ││BREATHNG││ ING  │ │
│ └────────┘└────────┘└──────┘ │
│ Active: TQ left leg 00:14:32 │  running timers, tap to open
│ ★ Pinned                     │
│ Injuries        ›            │
│ Heat, cold, environment ›    │
│ Bites, stings, poison   ›    │
│ Sudden illness          ›    │
│ Advanced procedures     ›    │
│ Tools                   ›    │
│ Reports (MEDEVAC, MIST) ›    │
└──────────────────────────────┘
```

Category rows expand in place to a grid of protocol buttons. No protocol is more than 2 taps from this screen.

### 5.2 Protocol player

```
┌──────────────────────────────┐
│ ‹ Severe bleeding   ★   ☰   │  ☰ = all steps on one page
│ ● ● ● ○ ○ ○ ○        3 of 7 │
│                              │
│  Put the tourniquet 2–3 in   │
│  above the wound. Not on a   │
│  joint. Tighten until the    │
│  bleeding stops.             │
│                              │
│  [ diagram ]                 │
│  ⚠ Do not loosen it later.   │
│                              │
│  [ Start tourniquet timer ]  │
│                              │
│  Back      [     NEXT     ]  │
└──────────────────────────────┘
```

- One step per screen. Each step has two layers:
  - **Action**: the thing to do now, in large type (at least 20px), written as one or two short sentences.
  - **Detail**: everything else relevant to that step (how, why, what to watch for, variations, common
    mistakes), with no length limit. Shown directly under the action and scrolls if long.
  Nothing is cut to fit. The build warns, but does not fail, if an action runs past about 200 characters,
  as a prompt to move the extra into detail.
- A step may carry: a warning, a diagram, a countdown or stopwatch, a tool (metronome, tourniquet timer,
  rate counter), or a yes/no question that branches.
- NEXT is full width at the bottom for one-handed use. Screen stays awake while a protocol is open.
- "All steps" view lists the whole protocol for training and quick scanning, with "Do not" and
  "Evacuate when" blocks and the sources.
- Progress is saved on every step. If the app is closed or killed, the home screen offers Resume.
- Help wording, since the group works off-grid: "Call 911 if you have signal. If not, send someone for help
  and prepare to move the casualty." Text only; no dial button.

### 5.3 Tools

| Tool | Behaviour |
|---|---|
| Tourniquet timers | As v5, moved into Tools, also startable from inside a protocol. Existing running timers survive the update. |
| CPR coach | Adult, child, infant modes. Metronome at 110/min, counts 30, prompts 2 breaths, counts cycles, prompts rescuer swap every 2 minutes. Compression-only option. |
| Rate counter | Tap along to a pulse or breathing for 15 seconds; shows per-minute rate and saves to the patient log. |
| Burn area | Tap regions on a body outline (adult or child proportions); shows % of body area and what that means for evacuation. |
| Patient log | Per casualty: timestamped notes, pulse, breathing, responsiveness (AVPU), treatments given. Protocol events (tourniquet on, CPR started) log automatically. Exports as text. |
| MEDEVAC 9-line and MIST | Form that pre-fills position (MGRS) from GPS and details from the patient log. Copy or share as text. Phase 2 adds QR, phase 3 sends it over the mesh. |

### 5.4 Find fast

- **App-wide search** from a magnifier in the header on every tab. Indexes protocol titles, keywords and
  step text, the existing survival topics, and app screens (ballistics, compass, saved areas). Results open
  the exact protocol or topic. Keyword synonyms per protocol ("heimlich" finds Choking, "bee" finds Stings).
- **Pinned** (star any protocol, tool or topic) and **Recent** (last 5) on each section's home.
- **Back button** works: every screen has an address (`#/emergency/bleeding/3`), so Android back steps out
  of a protocol instead of closing the app.

### 5.5 Look and feel

- Keep the existing dark theme, colour tokens and red night mode. No new visual language.
- Touch targets at least 56px in Emergency. Life-threat buttons use the danger colour; nothing else does.
- No decorative animation. Step changes are instant. Honour reduced-motion.
- Timers announce through `aria-live`; focus moves to the step text on each step change.

## 6. Protocol list (phase 1)

- **Life threats:** severe bleeding (tourniquet, wound packing, pressure); CPR adult, child, infant;
  choking adult/child, infant; unresponsive but breathing (recovery position); severe allergic reaction;
  open chest wound; shock.
- **Injuries:** trauma check (MARCH); head injury; suspected spine injury; broken bone and splinting;
  sprain or dislocation; burns; eye injury; amputation; impaled object; abdominal wound; wound cleaning and
  infection signs; blisters.
- **Heat, cold, environment:** hypothermia; frostbite; heat exhaustion and heat stroke; dehydration;
  altitude sickness; lightning strike; drowning; carbon monoxide.
- **Bites, stings, poison:** snakebite; tick removal; bee and wasp stings; spider and scorpion; animal bite;
  swallowed poison; poison ivy and oak.
- **Sudden illness:** chest pain or heart attack; stroke; seizure; low blood sugar; asthma attack;
  opioid overdose; fainting; severe vomiting or diarrhoea.

- **Advanced procedures (Jordan's decision to include):** nasal airway (NPA); needle decompression of the
  chest; surgical airway (cricothyrotomy); hemostatic gauze wound packing; junctional bleeding; pelvic
  binder; traction splint; tourniquet conversion; improvised wound closure; dislocation reduction where
  wilderness guidelines describe it. See section 7 for how these are presented.

Final count may move by a few if sources do not support a safe lay-responder protocol for an item.

## 7. Medical content rules

1. Sources, in order of authority for each topic: American Heart Association CPR and ECC guidelines; American
   Red Cross first aid guidelines; Stop the Bleed; Committee on Tactical Combat Casualty Care (all-service-member
   level only); Wilderness Medical Society clinical practice guidelines. Use the current edition at build time;
   look it up, do not write from memory.
2. Every protocol stores its sources and a review date, shown in the "All steps" view.
3. Standard protocols are written at lay-responder level. Medicines appear only where those guidelines give
   them to lay responders (aspirin for chest pain, epinephrine auto-injector, naloxone, sugar for low blood sugar).
   That list is illustrative: v6 also names over-the-counter pain medicine, without a dose, where the AHA
   2024 first aid guideline recommends it to lay responders (ruling recorded in `docs/v6-rulings.md`).
3a. Advanced procedures are a separate category, written from the TCCC guidelines and skill sheets and the
   Wilderness Medical Society guidelines, at the highest tier those sources publish. Each one:
   - opens with **When to do this** and **When not to** before any step, taken from the source;
   - states the equipment required and the training level the source assigns it;
   - lists what goes wrong and how to recognise it;
   - is reachable from the related standard protocol (open chest wound links to needle decompression) and
     from search, behind a one-time acknowledgement that these can kill if done wrong or when not indicated.
   No drug dosing beyond rule 3. No procedure is included that the sources do not describe.
4. Where two sources disagree, do not pick silently: list the item for Jordan with both positions.
5. After drafting, a second pass checks every number (depths, rates, times, temperatures) against the source.
6. The footer stays: reference only, not a substitute for training.

## 8. Technical design

**Files**

| File | Purpose |
|---|---|
| `src/protocols/*.json` | One file per protocol (new) |
| `src/emergency.html` | Emergency home markup, replaces the block in `shell.html` |
| `src/protocol.js` | Player engine: render, navigation, branching, resume. Section-agnostic so phase 2 reuses it |
| `src/emergency-tools.js` | Tools from 5.3; tourniquet and CPR code moves here out of `app.js` |
| `src/search.js` | Index build and search overlay |
| `src/router.js` | Hash routing and history |
| `build.py` | Validates and inlines protocols as `window.FK_DATA`; adds the new scripts |

**Protocol schema**

```json
{
  "id": "bleeding", "title": "Severe bleeding", "category": "life",
  "keywords": ["tourniquet", "hemorrhage", "blood"],
  "summary": "Stop the bleeding before anything else.",
  "steps": [
    { "id": "s1", "text": "…action…", "detail": "…unlimited…", "warn": "…", "fig": "tq-placement",
      "timer": { "seconds": 600, "label": "Hold pressure" },
      "tool": "tq",
      "ask": { "q": "Is the wound on an arm or leg?", "yes": "s3", "no": "s5" },
      "log": "Tourniquet applied" }
  ],
  "donts": ["…"], "evacuate": ["…"],
  "sources": [{ "name": "…", "year": 2025, "url": "…" }], "reviewed": "2026-11-16"
}
```

Only `id`, `title`, `category`, `steps[].id`, `steps[].text`, `sources` and `reviewed` are required.
Advanced procedures add `"tier": "advanced"`, `"indications"`, `"contraindications"`, `"equipment"` and
`"complications"`, all required for that tier.

**Build-time validation (build fails on any):** duplicate ids; branch target that does not exist; step
unreachable from the first step; missing sources or review date; `fig` name
not in `figs.F`; unknown `tool`.

**Storage (localStorage via the existing `store`):** `pins`, `recent`, `proto.active` (protocol id, step,
started time), `patients` (array of logs). Tourniquet key is unchanged so running timers carry over.
All new keys are added to backup and restore.

**Constraints**
- Still one self-contained `index.html`, vanilla JS, no framework, no network calls. Expected growth
  roughly 150 to 200 KB on today's 219 KB.
- Nothing Android-only without a fallback, so phase 2 iPhone work is not blocked (vibration and wake lock
  are optional enhancements).
- Protocol and patient-log objects are plain JSON so phase 2 can put them in a QR code and phase 3 can send
  them over the mesh without reshaping.
- Version bump to 6 in both `src/app.js` and `src/sw.js`; new source files added to the service-worker
  asset list only if they are separate files at runtime (they are not; everything is inlined).

**Testing**
- Build validation above.
- A scripted headless-browser pass over the built file: open every protocol, walk every branch to an end,
  start and stop each tool, confirm resume after reload, confirm search finds each protocol by title and by
  one keyword, confirm v5 stored data (waypoints, tourniquet timers, rifle profiles) loads unchanged.
- Jordan checks on the S22 Ultra before release: night mode, one-handed reach, metronome audio.

## 9. Standing decisions carried forward

No 911 or dial button. No edible-plant drawings. Clove hitch, taut-line, square knot and sheet bend stay
text-only until verified. OpenTopoMap online-only. Edit `src/` and `figs/` only; root files are build output.

## 10. Known risks

- **Advanced procedures performed without hands-on training can kill** (a misplaced chest needle or a failed
  surgical airway). The app can describe them accurately; it cannot make anyone competent. Mitigation is
  rule 3a and the footer; the residual risk is Jordan's accepted decision.
- **Medical accuracy** is the highest-stakes part. Mitigation is section 7; residual risk is real and the
  app must not present itself as more than a reference.
- **"Closed system" is not true today.** The app is served from a public address and public repo. No personal
  data is stored there, but anyone with the link can use it. Fixing that needs a hosting decision; not in phase 1.
- **Phase 3 cannot be tested without hardware.** Two GPS-equipped Meshtastic radios are needed before it starts.
- **Single-file size.** Fine through phase 2; revisit if the file passes about 1 MB.

## 11. Left to the builder

Exact CSS within the existing tokens; search ranking details; which protocols get new diagrams (simple
positioning diagrams only: recovery position, hand placement, back blows, splint, tourniquet placement);
internal structure of the engine.

## 12. Calls Claude made (Jordan can overrule any)

1. Protocols stored as JSON and rendered by one engine.
2. App-wide search and back-button navigation ship in phase 1, not phase 2, because finding things fast was the first complaint.
3. ~~Lay-responder level only; invasive procedures excluded.~~ Overruled by Jordan: advanced procedures are
   included. Claude's call within that: they sit in their own category with indications first and a one-time
   acknowledgement.
4. Off-grid help wording replaces "Call 911" as the automatic first step.
5. Mass-casualty triage and team medical cards deferred.
6. Simple positioning diagrams added for Emergency; no anatomy or wound illustrations.
7. ~~280-character limit per step.~~ Overruled by Jordan: no cap. Claude's call within that: each step
   splits into a short action and unlimited detail.
