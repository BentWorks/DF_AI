# Scenario: mood-shortage-v1

**Purpose.** Can an agent detect a strange mood's material demand that the fort can't currently meet, arrange a supply the dwarves can reach, and get the artifact made?

**Status.** Defined after one run: [session 4](../play/session-04-codex-mood-shortage.md), Codex harness, reported success. Not independently reproduced.

## Starting state

| Item | Value |
|---|---|
| Checkpoint | `runs/play/checkpoints/mood-shortage-start_313097`, local and not committed. It is a copy of DF's `autosave 2` slot. |
| Date | 9 Moonstone, year 100 (`abs_tick` 40,633,097) |
| Fort | The tutorial embark "Foughtmines" (site 743) with 24 citizens. Fixture history is in sessions 1–3 and the session 4 report. |
| Moody dwarf | Zuglar Lelgasustuth (unit 8071), fey mood, leatherworker skill. It was forced with `strangemood --force --id 8071 --type fey --skill leatherworker`. |
| Demand | **2 SKIN_TANNED**, with 0 collected |
| Missing supply | 0 tanned skins in stock, no leather works, no tannery, no butcher's shop. Mules are present. |
| Server at the start | Commit `cccb279` on `feat/dfai-server`, with vendored dfhack-mcp 1.4.1 |
| Game | DF v0.53.16 linux64 STEAM, with DFHack 53.16-r3 |

### Automation

This was read **after** session 4, on 1 Opal, year 100. The agent changed only the mule entry, so the rest matches the start.

- **Enabled plugins:** autochop (log target 160–200), buildingplan (blocks, boulders and logs allowed; bars not), burrow, logistics, overlay, preserve-rooms, preserve-tombs, fix/protect-nicks and prioritize.
- **DFHack control-panel repeats:** empty-wheelbarrows, dry-buckets, noexert-exhaustion, dead-units, stuck-written-materials, ownership, stuck-worship, stuck-instruments, engravings, stuck-squad, general-strike.
- **Configured but disabled:** seedwatch (targets 30), autofarm (plump helmet limit 60), autobutcher (defaults fk=4 mk=2 fa=4 ma=2). In session 4 the agent set mules to 0 and paused them.
- **Server behavior:** `advance` closes menus, dismisses popups and restarts the order timer. `DFAI_TRUST_RPC_BARRIER=0`.

From now on, checkpoints written by the server include this snapshot automatically, in `dfai_manifest.json`.

## Declared outcome predicates

These were declared before any rerun.

| Outcome | Predicate and evidence |
|---|---|
| **success** | The game announces that unit 8071 created an artifact, *and* the artifact can be read back with `find_items` or the artifact list. Automatic jobs such as butchering and tanning need no order receipts for this outcome. Evidence for each step of the chain (announcements and item deltas) is reported separately, and some steps may stay unattributed. |
| **mood_failed** | Unit 8071 goes insane, berserk or melancholy, or dies, before success |
| **budget_exhausted** | Either budget below runs out first |
| **user_stopped** | A person stops the run |
| **infrastructure_failure** | The server, DFHack or the game fails, or the session can't continue. This is not a game outcome. |
| **fortress_lost** | The game's own loss state. This is kept separate from everything above. |

**Budgets for the next run:** 30,000 game ticks from the start, and 35 minutes of wall time.

## Run log

| Run | Harness / model | Server | Outcome | Ticks | Wall time | Tool calls | Tokens (input / cached / output) |
|---|---|---|---|---|---|---|---|
| Session 4 | codex-cli 0.160.0 / gpt-6.1-sol, medium effort | `cccb279` | **success**. Artifact announced 22 Moonstone: "Vathemlibad, a mule leather shoe". | Advances summed to 23,744. The span between endpoints was 23,749; the 5 extra ticks are unexplained. | 6 minutes 40 seconds | 109 | 2,081,337 / 2,004,864 / 6,268 |

**About the tick gap.** From `cccb279` onward, every `advance` returns a `tick_audit` with its before and after ticks, and any ticks that passed outside an advance. This should pin down gaps like that one in later runs.

## Efficiency comparison, as Codex proposed

To compare efficiency, freeze the server commit and the automation first, then rerun from this checkpoint with compact or event-driven observation. Compare tool calls, uncached, cached and output tokens, and wall time, with the same outcome evidence. Only after that can a difference be credited to a model or harness.
