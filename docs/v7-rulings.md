# v7 rulings and deferred items

Decisions Claude made during the v7 build without asking Jordan, each with what it costs if wrong, in the order they were made,
followed by the minor review findings that were left unfixed. Jordan can overrule any of them.
Questions that need Jordan or a medical professional are in `docs/decisions-for-jordan.md` (section D, items 1 to 14).

## Rulings

- T3 keeps the old {{fig}} substitution and diagram count; T4 removes them when it replaces survival.html — spec silent, least breakage — cost if wrong: none (transient).
- T2's word-for-word test ignores `link` blocks (needed for surv-priorities anyway), so T8's added link does not break it — cost: a stray link block is not caught by that test; validator's link check covers it.
- T6 changes search.js describe() case 's' to read FK.survival.topic(id); the rest of search stays for T7 — cost: T6 touches a T7 file by ~3 lines.
- Task 1: implemented fef9da4, DONE_WITH_CONCERNS (strict dates on topics only; sources need name+used; checklist category uses TOPIC_CATEGORIES; link_keys unused for checklists) — Ruling: accept all four, they tighten data the spec already requires — cost if wrong: a later pack has to loosen a check.
- Task 2: implemented 6ba7826 + fix 5affc5c. Ruling: drop nav-cross figure (spec deletes Southern Cross text; plan's figure test was a plan defect) — cost if wrong: one diagram to restore. Ruling: accept invented keywords/summaries/link label and where tags; re-checked in Tasks 13-16.
- Task 4: implemented 0dad894, DONE_WITH_CONCERNS (5 search tests xfail→Task 7; open() false for c:/u: until T8-10; registerPage allows several providers per segment; trailer names the model that wrote it — Ruling: leave, it is accurate).
- Task 4: minor (deferred): provider exception not contained (→ folded into Task 5 dispatch); recent.add on every render incl. Back (Ruling: keep, "recently viewed" — cost: order shifts on Back); homeY/opener captured on other tab; xfails not strict (Task 7 removes them); outline:none on programmatic-focus headings
- Task 8: implemented 08a7f66, DONE_WITH_CONCERNS (4 existing tests adjusted for the shipped checklist; Clear ticks is in-page two-step, no ignoreMs guard — Ruling: accept, low stakes; draft flag shown on checklists; provider pages focus title)
- proceed to code review and later tasks; Task 10 stays OPEN until USNO rows are added (needs Jordan to approve the fetch). v7 must not release with moon times unverified — cost if wrong: none, it only delays.
- Utqiagvik 21 Dec "does not rise" row kept as a geometric fact (71.29 N is inside polar night at the December solstice), labelled as such, not as a fetched value.
- boil time stays 1 minute (3 above 5,000 ft) per EPA/CDC, the US public-health authorities named as primary; NYS DEC/Army 5 minutes is listed for Jordan (decisions-for-jordan D1) — cost if wrong: longer boil is only more fuel; 1 min is the CDC/EPA standard.
- fix I1-I4 and M2-M4 now (all are small, sourced, safety-facing); I4 edits src/protocols/vomiting-diarrhea.json to 5,000 ft (EPA) with a content-review entry — outside the batch's file list but the app must not give two answers for one place. M1 logged for pack 1.
- fix F1-F4, F6 now; F5/F7/F8 left; F9 logged in decisions-for-jordan as a medical question (do not edit the lightning protocol in this plan).
- new Task 16b "relabel and restore four diagrams" after Task 16 — spec goal is diagrams wherever recognisable; label-only fixes are cheap; the two needing new drawings are logged for their packs — cost if wrong: one small task.
- keep "in normal times" on the NYS DEC firewood rule — it was the controller's wording and follows spec 6.1 (state that state rules apply in normal times); the app is written for grid-down use — cost if wrong: a reader treats a state-land rule as optional in ordinary camping.
- fix F1-F6, F8, F11 now; F7/F9/F10 left. Task 15: fix round 1/5 dispatched (resume a6d21717501238193).
- fix F1-F7 now, and fold in four deferred content minors from earlier batches in the same commit (bear "raise your arms" clause; D11 both irises; river hazard label wording; fire-sizes caption duplicate sentence). Task 16: fix round 1/5 dispatched (resume ac41a75ed630c1f79).
- Final whole-branch review (fable): FIX BEFORE MERGE, 0 Critical, 1 Important (Coast filter hides safety topics) + 9 should-fix minors. Upgrade from a real v6.2 build driven in browser: no data lost. Fix wave brief: final-fix-wave.md (F1-F16). Ruling: scrub home town from tracked docs (repo is public) without rewriting history — cost if wrong: none; history still has it (tell Jordan). Fix wave dispatched (opus), base aa6b602.
- main gets ONE squashed release commit (9ab1bee) instead of the 40-commit branch history — matches how v6 was released, and keeps the home town out of main's history; tree identical to v7-survival c755ea7 — cost if wrong: per-task history lives only on the v7-survival branch.

## Minor findings left unfixed (triaged "leave" by the final review unless marked)

- Task 1: minor (deferred): test_reserved_ids_are_listed asserts only "some error"; reserved-id branch is dead code for surv-* ids; no test for non-string fig/link values
- Task 2: minor (deferred): added-headings skip matches by text only; "Shadow stick (works in both hemispheres)" heading and generic bear wording to be reworded in Tasks 15/16
- Task 3: minor (deferred): figSvg test not topic-specific; no build test that link_keys is wired (bad s: link fails, c: link passes); relaxed release-gate test can pass vacuously; inject_data topics/checklists/only untested
- Task 4: minor (deferred): provider exception not contained (→ folded into Task 5 dispatch); recent.add on every render incl. Back (Ruling: keep, "recently viewed" — cost: order shifts on Back); homeY/opener captured on other tab; xfails not strict (Task 7 removes them); outline:none on programmatic-focus headings
- Task 5: minor (deferred): no RED capture; category <details> redraw can drop a focused summary once (→ folded into Task 6 dispatch); filter test could assert the empty-message; store.set failure path untested
- Task 6: minor (deferred): survival.js KEY duplicates FK.keyPattern; mid-file imports/quote styles in test_survival_home.py; no seeded test of exactly five mixed-kind v6.2 recents on Emergency home
- Task 7: minor (deferred): go() returns true even when survival.open returns false for c:/u: (→ Tasks 8-10 extend open; go should return open's result); figLabel not indexed; 10ms perf-test bound flaked once under load
- Task 8: minor (deferred): "Confirm clear" has no double-tap guard (ignoreMs); checklist notes capitalised / "Extra water" split and new summary copy → Task 16 vets; no test that Draft shows for checklist in search/Recent; migration test link-key set hardcoded; runtime does not reject duplicate item ids (validator does)
- Task 9: minor (deferred): no test for opening a topic/checklist while the light runs or for a second Start; wake lock not re-acquired if the OS releases it mid-run; Start reads "Stop SOS" after Steady
- Task 11: minor (deferred): a medical timer that expired while the app was closed leaves no trace (PRODUCT QUESTION for Jordan: show a passive "Timer ended while closed" line?); toast-absence assertion could pass vacuously; done:true stored timers also dropped at startup
- Task 10: minor (deferred): moon dash doesn't say "up all day" (now seen for real at Utqiagvik 21 Dec); phase-name rule accepts either name on a primary-phase day
- Task 12: minor (deferred): stop() and disconnect() share one try (older WebKit could skip disconnect → late click) — FIX IN FINAL WAVE; no test dispatches statechange / 'interrupted'
- Task 14: minor (deferred): rule sits a section away from the wet-weather wood advice; F5 vent "in the roof"; F7 "Ridgetops: wind" label; F8 link placement.
- Task 15: minor (deferred → FINAL WAVE): move "raise your arms" from the charge clause to the following-bear clause (NEBBTC); D11 should name both irises; "iris leaf bases are flat" for blue flag rests on genus; F7 recheck trapping guide edition (food pack); F9; F10.
- Task 16b: minor (deferred → FINAL WAVE): river label "stay well upstream" is not the topic's wording ("never cross just above them"); fire-sizes caption repeats the paragraph's sentence; debris ridgepole drawn on a forked post (topic: stump or tree); figs tests use hard-coded key words.
- Fix-wave re-review (opus): F1-F16 all addressed, no blocking breakage, READY TO RELEASE. Residual minor (parked): itemsFor accepts any keyPattern kind (no provider sends others). Task 17 started by controller.

## Product question for Jordan

- A step timer that runs out while the app is closed now leaves no trace on reopening (no vibration, no "Done" entry). The final reviewer thought a passive "Timer ended while the app was closed" line on the resumed step would be safer for a medical timer. Not built; say if you want it.
