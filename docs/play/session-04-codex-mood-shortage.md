# Play session 4: Codex recovers from a strange-mood shortage (2026-10-30)

This is the mood experiment agreed with AI Collaborator Codex. The test: can an agent detect what a strange mood demands, find that the fort lacks it, set up a supply the dwarves can reach, and get the artifact made?

## Setup

| Item | Value |
|---|---|
| Fixture | The tutorial fort "Foughtmines", continuing from sessions 1–3. It is not a fresh embark. |
| Inherited interventions | 1. After session 3, Claude forced a secretive mood on the expedition leader as a sensor probe. Its materials were already collected, and he made "Tileshîtat, a rock salt crown". 2. Claude advanced about 2 days outside any AI session so that mood could finish. 3. **The setup for this experiment:** `strangemood --force --id 8071 --type fey --skill leatherworker`. The game set the demand at **2 SKIN_TANNED**. The fort had **0** tanned skins, and no leather works or tannery. |
| Start checkpoint | `runs/play/checkpoints/mood-shortage-start_313097`: 9 Moonstone, year 100 |
| Server | DF_AI on PR #6, after v0.8. Tool results are plain JSON, with 25 tools. |
| Harness | codex-cli 0.160.0, `codex exec -s read-only`, with DF_AI tools pre-approved |
| Model | gpt-6.1-sol, reasoning effort medium (from `~/.codex/config.toml`) |
| Automation | `advance` closes menus, dismisses popups and restarts the order timer. Automatic replay off. DFHack automation from earlier sessions stays enabled. |
| Interventions during the session | None |
| Transcript | `runs/play/sessions/codex-20261030-014859.jsonl`, kept locally |

## Outcome

**The mood was satisfied.** At 22 Moonstone, tick 328,441, the game announced: "Zuglar Lelgasustuth, Miner has created Vathemlibad, a mule leather shoe! He claims it as a family heirloom."

| Measure | Value |
|---|---|
| Game time | 9 Moonstone (tick 313,097) to 1 Opal (tick 336,846). That is 23,744 ticks over 11 advances. |
| Dwarves | 24 at the start and 24 at the end. No deaths in the session. |
| Death history | Unchanged: one fort death since founding (STRUCK_DOWN, in session 3). None from starvation or dehydration. |
| Food / drink at the end | 276 / 267 items, about 483 and 186 days |
| Wall time | 6 minutes 40 seconds in total. Advancing took 3 minutes 59 seconds. |
| Tool calls | 109, with 0 errors |
| Tokens | 2,081,337 input (2,004,864 cached), 6,268 output (1,285 reasoning) |

## The supply chain, with evidence

1. **The demand.** `moods` showed 2 SKIN_TANNED, with 0 collected. `find_items` found no skins.
2. **The workshops.** Codex built a butcher's shop (47), tanneries (48 and 49), a leather stockpile (50) and a leather works (51). All were verified as built with `buildings`.
3. **The labors.** It enabled BUTCHER and TANNER for two dwarves with `set_labor`.
4. **The hides.** It marked two mules for slaughter with autobutcher. The game announced the slaughters on 13 and 15 Moonstone. By 16 Moonstone, `find_items` showed 2 mule leather.
5. **The mood.** Zuglar claimed the leather works on 17 Moonstone, collected 2 of 2, and started work on 18 Moonstone. The game announced the artifact on 22 Moonstone. Afterwards `moods` was empty, and `find_items` found the artifact shoe.

**About the evidence.** Butchering and tanning ran as automatic jobs, not manager orders, so `progress` has no record of them. The chain is supported by the game's announcements and item counts, not by order receipts. That's how Codex reported it too.

## Other work

- **Dining.** 5 tables and 5 chairs placed, taking dining seats from 3 to 8.
- **Bedrooms.** Four dug out, furnished with beds, and assigned to four dwarves with `assign_owner`.
- **Barrels.** Order 99 is in progress at 9 of 12, with 7 empty barrels at the end.
- **Cleanup.** The mules were taken off the slaughter list afterwards.

## Gaps found

| Gap | Fix |
|---|---|
| `build` returned `applied` when quickfort placed **0** buildings, because every tile was unsuitable | **Fixed:** `build` now refuses when the dry run would place nothing, and quotes the reason (for example "Unsuitable tiles for building: 9") |
| `find_items` doesn't match an artifact's proper name, only its item description | Open: add artifact names to the search |
| Automatic jobs, such as butchering and tanning, have no progress tracking | Open: track job completion through announcements and item deltas |
