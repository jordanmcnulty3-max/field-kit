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
