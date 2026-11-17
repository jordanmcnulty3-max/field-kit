# Field Kit v7: Survival knowledge center (design)

Date: 2026-11-17. Status: awaiting Jordan's approval.
Builds on `2026-11-16-emergency-survival-overhaul-design.md` (the v6 design); where the two disagree about
Survival, this document wins.

## 1. Intent

Survival today is 14 text topics written for a lost hiker anywhere in the world. Jordan wants it to become the
group's **knowledge center for surviving a long grid-down, wartime or "apocalypse" period**, solo or as a group,
in town and in the woods, written for **Central New York** (everyone who will use it lives in or around
Liverpool, NY). It must work whether the group stays home or has to move.

His standing complaints about Survival still apply: "difficult to find something fast", content that "isn't deep
or broad enough", and "there needs to be interactive elements". "More is better": no length cap on text.

The job is far bigger than v6's content job (roughly 80 or more topics against 14 today), so it ships as a
**framework release followed by content packs**, each pack its own release Jordan can check on his phone.

## 2. Goals, non-goals, anti-goals

**Goals**
- From opening the Survival tab to the right topic in two taps or one search.
- A Survival home built around what you need: categories, tools, checklists, pinned and recent.
- Topics are checked data files (like Emergency protocols): every one has sources, a review date, and is
  validated at build time.
- Content written for Central New York: real winters and lake-effect snow, local water, local game and plants,
  ticks, town and rural settings.
- Interactive tools and tick-off checklists that scale to the group's size.
- Diagrams wherever a diagram is recognisable without its caption.
- Everything works with no connection after install.

**Non-goals (v7)**
- Recce. It goes under Tactical as its own later release (map, routes, observation posts, range cards,
  sighting reports).
- iPhone support (v7.1) and QR hand-off (later). Team map (v8).
- Guided one-step-per-screen "Situations" in the framework release (see section 5.6).
- Content for deserts, jungles and coasts.

**Anti-goals (failure even if it works)**
- A wrong or unsourced number in water treatment, food safety, radiation or medicine.
- Hand-drawn pictures of edible plants (standing decision; a wrong identification can kill).
- Instructions for improvised weapons, explosives, or traps meant for people. Survival covers staying alive,
  protecting people, moving and observing. Trapping and hunting animals for food is in.
- Losing anyone's pins, recents or saved data when v6.1 updates to v7.
- Cutting relevant information to save space.
- A 911 or phone-dial button.

## 3. Approaches considered

1. **One big v7 with all content.** Nothing to check for a long time; in v6 every content batch had defects
   its author missed, and they would pile up unseen. Rejected.
2. **Add topics to the existing page.** Cheap, but it keeps the long scrolling page (does not fix "hard to find
   fast"), and nothing validates the content. Rejected.
3. **Framework first, then content packs.** Picked by Jordan on 2026-11-17 ("go"). v7.0 rebuilds the Survival
   tab and moves the existing topics into checked data files; each pack after that is a release of its own
   with its own content plan and independent review.

## 4. Releases

Version numbers are taken in the order things ship; `build.py` already accepts dotted versions.

| Release | What |
|---|---|
| **v7** | Survival framework (section 5), existing 14 topics migrated, three tools, checklists, the v6 backlog fixes (section 9) |
| **v7.1** | iPhone support (own short design). Ships as soon as a friend with a real iPhone can test; if no tester is ready it waits and the packs go ahead. |
| Packs, next free numbers | In this order: 1 Water and sanitation · 2 Heat, shelter and winter · 3 Radiation and fallout · 4 Food: storage, hunting, trapping, fishing, plants · 5 Comms: Meshtastic, radios, signals · 6 Staying put: home, group roles, watch schedule · 7 Moving: bags, routes, rally points, travelling on foot · 8 Town hazards and long-term health |
| Later | QR hand-off, Recce under Tactical, v8 team map |

**This document specifies v7 (the framework) in full** and fixes the rules every pack follows (sections 6 to 8).
Each pack gets a short content plan (topic list, sources, tools, diagrams) before it is written; that plan is
shown to Jordan only if it raises a decision that is his.

## 5. v7 design: the Survival framework

### 5.1 Survival home

```
┌──────────────────────────────┐
│ Survival               🔍  ☾ │
│ Where: [Any][Town][Rural][Woods]
│ When:  [Any][Cold][Warm]     │  filters; remembered
│ ★ Pinned                     │  survival items only
│ [Make water safe] [Knots]    │
│ Recent                 Clear │
│ [Fire] [Shelter]             │
│ ── Topics ─────────────────  │
│ Basics                     + │  categories open in place
│ Water and sanitation       + │
│ Heat, shelter, winter      + │
│ …                            │
│ ── Tools ──────────────────  │
│ [Daylight and moon] [SOS light]
│ ── Checklists ─────────────  │
│ [Ten essentials  4/10]       │
└──────────────────────────────┘
```

- The old "Your environment" picker (Forest, Desert, Cold and snow, Jungle, Coast) is removed. The Forest and
  Cold-and-snow advice is kept inside the migrated topics; desert, jungle and coast text is dropped.
- **Filters:** Where (Any, Town, Rural, Woods) and When (Any, Cold, Warm). A topic lists the settings and
  seasons it applies to; a topic with none listed always shows. Filters hide non-matching topics in the home
  lists only. **Search ignores the filters** (finding fast beats filtering). A category with nothing left shows
  "No topics for this filter" rather than vanishing.
- **Categories** are the eight packs plus **Basics** (the migrated topics that belong to no pack yet). A
  category with no topics is not shown, so v7 shows only the categories that have content.
- The Survival tab's own search box is removed; the header magnifier (app-wide search) replaces it.
- Pinned and Recent on the Survival home show survival items only (topics, survival tools, checklists). The
  Emergency home keeps showing everything, as today. Recent stays one shared list: the stored list grows from
  5 to 20 entries, the Emergency home shows the newest 5 of all kinds (unchanged), and the Survival home shows
  the newest 5 survival items. Clear on either home empties the whole list.
- "Priorities" (rule of threes, STOP) becomes a new topic, `surv-priorities`, listed first in Basics. The old
  picker's Forest and Cold-and-snow bullets move into it under their own headings; its frostbite line becomes
  a link to the Emergency frostbite protocol.

### 5.2 Topic page

Address `#/survival/<topic-id>`; Android Back returns to the Survival home. A topic opened from search behaves
as every search result does today: Back goes to the screen that was open before search, not to search.
The pin star on topics is new (today only protocols and tools can be pinned).

- Title, pin star, then an optional **Do first** box: up to about five short numbered actions, for topics where
  something must happen before reading (for example "Fallout warning"). This is how Survival stays
  action-first without the step player.
- Then sections, each a heading with blocks: paragraph, bullet list, numbered steps, warning, table, diagram
  (tap to enlarge, as today), and link to another topic, protocol, tool or checklist.
- Sections are all open by default (reference text is scanned, not stepped through), with a jump list at the
  top when a topic has four or more sections.
- Footer: sources (name, and what each was used for), "Reviewed <date>", and for fast-dating content an
  "As of <date>" line (radio and Meshtastic topics).
- A topic still marked draft shows a Draft tag, as protocols do, and blocks a release build.

### 5.3 Topic data

One file per topic, `src/survival/<id>.json`, validated at build and inlined with the protocols.

```
id          "surv-<slug>"   existing ids are kept exactly, so current pins, recents and search keys still work
title, category, keywords[], summary
where[]     any of town, rural, woods   (optional)
when[]      any of cold, warm           (optional)
doFirst[]   optional short actions
sections[]  { h, blocks[] }   block = { p } | { list[] } | { steps[] } | { warn } | { table: { head[], rows[][] } }
                                    | { fig, cap } | { link: "<key>", label }
sources[]   { name, used }   at least one
reviewed    date
asOf        optional date
draft       optional true
```

Validator rules (added to `tools/validate.py`): unknown keys are errors; ids unique across topics and distinct
from protocol ids; category, where and when from fixed lists; every `fig` exists in `figs.F`; every `link` key
resolves to a real protocol, topic, tool, checklist or screen (wrong cross-references were a repeated v6
defect); at least one source; a draft topic fails `--release`.

**Migration.** The 14 existing topics are converted to this format word for word, then tagged with
where/when. The only changes allowed are deletions of content that does not apply to Central New York, each
listed in `docs/v7-migration.md` with the reason: the desert half of Shelter's "Snow and desert" section and
the `shelter-desert` diagram, Southern Hemisphere and Southern Cross navigation text, grizzly-bear and
mountain-lion sections of Dangerous animals, and the seawater line in Find water. A test checks that each
migrated topic's text equals the old text minus exactly the listed deletions.

**Sources for migrated topics.** The existing topics have no recorded sources. See section 12 (open question
for Jordan).

### 5.4 Tools (v7)

Only tools that need no sourced survival numbers ship in v7; the planners arrive with the pack that sources them.

- **Daylight and moon:** sunrise, sunset, first and last light (civil twilight), day length, moon phase and
  moonrise/moonset for today and the next six days, computed on the phone from the last GPS fix (or a typed
  position). No network. Tests check Syracuse, NY on the two solstices, the two equinoxes and the days either
  side of both clock changes: sun times within 2 minutes and moon times within 5 minutes of US Naval
  Observatory values, which are looked up while planning and recorded in `docs/content-review.md`.
- **SOS light:** flashes the screen white in Morse SOS at standard timing, with a steady-light option. Keeps
  the screen awake. A warning that a flashing screen gives away your position.

Nothing in v7 needs a group-size setting, so it is not built now; it arrives with the water planner in pack 1,
together with checklist quantities that scale.

Tools arriving with packs: water planner and food planner (packs 1 and 4), fallout shelter-time guide (pack 3),
watch-rotation scheduler (pack 6). Each pack's content plan specifies its tools.

Survival tools are ordinary Survival pages at `#/survival/tool/<name>`, drawn by the Survival code like a
topic page, with key `u:<name>` for pins, recents and search. They do **not** go through the Emergency tools
overlay (`FK.tools` in `src/emergency-tools.js`): that code is fixed to Emergency addresses, closes back to
the Emergency home and drives the Emergency strip, and changing its history logic is the same risk section
5.6 avoids for the player.

### 5.5 Checklists

- Data: `src/checklists/<id>.json` (id, title, category, items, sources). Address `#/survival/list/<id>`; key `c:<id>` (a new key letter for pins, recents and search).
- Tick state is saved on the phone, shown as "4/10" on the home, has a "Clear ticks" button with an in-app
  confirm, and is included in backup and restore.
- v7 ships one checklist, **Ten essentials**. The Ten essentials topic stays (it explains each item) and
  links to the checklist; search lists them as a Survival topic and a Checklist. Packs add more lists (home
  water store, go-bag, vehicle kit, and so on) and, from pack 1, quantities that scale with group size.

### 5.6 Guided flows: not in v7

The v6 design expected Survival "Situations" to reuse the step player. The player is still tied to Emergency
(its section name, reserved addresses, the home strip), and its back-button logic failed three reviews before
it settled. A knowledge center is mostly studied, not stepped through, so v7 does **not** generalise the
player. The "Do first" box covers urgent openings. If a pack turns out to need a true guided flow (the likely
case is pack 3, "fallout warning: what to do now"), that pack's plan proposes making the player
section-agnostic then, as its own reviewed task.

### 5.7 Search, pins, recents

- Search indexes topics from the data (title, keywords, summary, Do first, section headings and text) instead
  of reading the page, plus survival tools and checklists. Result groups gain "Checklist". Existing `s:surv-…`
  keys keep working.
- Opening a topic, survival tool or checklist adds it to Recent.

### 5.8 Look and feel

Same theme, colour tokens and red night mode as the rest of the app. Touch targets at least 48px in Survival.
No decorative animation. Text selectable. Tables scroll sideways inside their own box rather than the page.

## 6. Content rules for every pack

1. **Central New York first.** Cold-season content assumes real winter. Hunting, trapping and fishing topics
   name local species and state that New York seasons, licences and trap rules apply in normal times.
2. **Every number comes from a source that was actually opened**, recorded in `docs/content-review.md` with
   the page or section. Preferred sources: FEMA and Ready.gov, CDC, EPA (water disinfection), HHS REMM, NRC
   and FDA (radiation, potassium iodide), Red Cross, National Weather Service, NYS DEC, Cornell Cooperative
   Extension, US Army survival manuals (public domain), Meshtastic's own documentation. Two-column PDFs are
   checked by hand for step order.
3. **Independent review of every pack** by a reviewer that did not write it, looking for: a number that does
   not match its source, a step that contradicts another topic or an Emergency protocol, a link into the wrong
   place, advice that is wrong for the season or setting it is tagged with.
4. **Medical overlap:** Survival links to the Emergency protocol instead of restating treatment (hypothermia,
   frostbite, heat illness, bites). Radiation exposure care that Emergency lacks is added as Emergency
   protocols in pack 3, under the Emergency content rules.
5. **Plants:** text only, a short list of local species that are hard to confuse, each with its dangerous
   look-alikes named. No drawings. Photographs only if they are public-domain or CC0, from a botanical
   authority, show the plant beside its look-alike, and are credited in `docs/photo-credits.md`. The build
   environment cannot download from the likely photo sources, so photos need Jordan to add the files from a
   list Claude provides; without them plants stay text-only. Decided at pack 4.
6. **Not written:** improvised weapons, explosives, traps or harm aimed at people.
7. **Radio content** carries an "As of" date and names the firmware or app version it was checked against.
8. **Diagrams:** added wherever one is recognisable without its caption; otherwise left out (standing rule).
   The four unverified knot diagrams stay text-only.

## 7. Technical notes

- New files: `src/survival/*.json`, `src/checklists/*.json`, `src/survival-tools.js`; `src/survival.html`
  shrinks to the home skeleton; `src/survival.js` is rewritten (home, filters, topic page, checklists).
- `build.py` validates and inlines topics and checklists next to protocols (`window.FK_DATA.topics`,
  `.checklists`), injecting diagram SVGs as it does for protocol steps.
- `src/router.js` needs no new tab; Survival gains sub-addresses (`<topic-id>`, `tool/<name>`, `list/<id>`).
  `tool` and `list` are reserved topic ids.
- Storage keys added: `survFilter`, `checks`. Stored key letters gain `c:` and `u:`. All are in backup and restore. Unknown or malformed
  stored values are ignored, never rendered (the existing rule).
- **Size:** `index.html` is 1.04 MB now and will grow with every pack, to perhaps 3 to 4 MB by pack 8. That is
  accepted for a one-time install. If `index.html` passes 3 MB, topic data moves to its own precached file.
- **Versions.** v6.1 was the first dotted version and exposed a defect: restore refused any backup whose
  version was not all digits, so a v6.1 backup could not be restored. Fixed in v6.2 (versions are
  `major[.minor]` and compare as numbers). Every later release keeps that format.
- Tests (Playwright, 360×640, any console error fails): home and filters, topic rendering for every block
  type, migrated text equals old text, old pins/recents/search keys still open their topics, checklists and
  backup, both tools, search over the new index, Back from topic/tool/checklist.

## 8. Risks

- **Scale.** Eight packs is many releases, and content review is the slow part. The order in section 4 puts
  the things that kill fastest in a Central New York grid-down first (water, cold, fallout).
- **Fix rounds create new defects** (v6 experience). Fix scopes stay tight and every fix is re-reviewed.
- **Radiation and potassium iodide numbers** are medical. They follow the Emergency sourcing rules and go on
  the list of questions for a medical professional.
- **Meshtastic guidance dates quickly** and cannot be field-tested until Jordan has radios.
- **Daylight and moon maths** is easy to get subtly wrong (time zones, daylight saving, polar edge cases);
  tests pin it to almanac values.
- **The app is public on GitHub Pages.** A wartime knowledge center for a closed group is still readable by
  anyone with the address. The hosting decision is open.

## 9. v6 backlog fixes folded into v7

- A running step timer stopped by opening another protocol (or re-opening from the home tile) gets a notice.
- Queued CPR clicks are cancelled when sound is interrupted, so the beat does not stumble after a phone call.
- The update banner no longer covers the search screen.
- A step timer that ran out while the app was closed no longer tries to vibrate at startup and clears from
  the home strip.
- The search screen's Recent list gets a Clear control.

## 10. Left to the builder

File and function layout inside `src/survival.js`; exact markup and CSS; how filters are drawn; the astronomy
algorithm (any published method that passes the almanac tests); how old topic HTML is converted to JSON; test
names; whether checklists and topics share one renderer.

## 11. Calls Claude made (Jordan can overrule any)

1. No guided step-by-step flows in v7; a "Do first" box instead (5.6). Cost if wrong: urgent survival actions
   read as a short list rather than one step per screen until a pack adds the player.
2. v7 ships only three tools; planners wait for the pack that sources their numbers (5.4).
3. Desert, jungle and coast advice is deleted, not hidden (5.1).
4. The Survival tab's own search box is removed in favour of the header search (5.1).
5. Survival home shows only survival pins and recents; Emergency home is unchanged (5.1).
6. Filters do not affect search (5.1).
7. QR hand-off moves behind the content packs; iPhone support keeps the name v7.1 but waits for a tester (4).
8. Radiation exposure care is added to Emergency as protocols, not written into Survival (6.4).
9. Plant photos depend on Jordan supplying the files; otherwise text-only (6.5).
10. Growth to 3 to 4 MB is accepted (7).
11. Recent becomes one stored list of 20, shown five at a time per home (5.1).
12. Survival tools are plain pages with their own key letter, not the Emergency tools overlay (5.4).
13. No group-size setting until pack 1 (5.4).
14. Migrated topics lose their non-local content (5.3).

## 12. Open question for Jordan

The 14 existing topics have never been source-checked, and some carry numbers (water treatment above all).
Two ways to handle them in v7:

- **A (recommended):** move them over as they are, each showing a visible "Not yet source-checked" label, and
  let a release build ship them with that label. Each one is checked, corrected and loses the label when its
  pack arrives (water first). v7 stays a framework release.
- **B:** source-check and independently review all 14 before v7 ships. Nothing unchecked survives, but v7
  becomes a content job about the size of a pack and arrives much later.
