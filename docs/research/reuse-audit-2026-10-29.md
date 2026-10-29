# Reuse audit and environment check (2026-10-29)

- **Performed by:** AI Collaborator Claude on the maintainer's machine, with the maintainer present.
- **Fort:** a running fort called "Foughtmines", in year 100, with 7 citizens.
- **Mode:** **read-only.** No actuator was called. Time was not advanced, and nothing was saved.
- **Evidence label:** items marked **Verified** were observed on the pinned pair below. Everything else keeps its earlier label.

## Pinned environment (Q-09)

| Component | Value | How observed |
|---|---|---|
| Dwarf Fortress | `v0.53.16 linux64 STEAM`, Steam build 24557528 | `dfhack.getDFVersion()`, Steam manifest |
| DFHack | `53.16-r3` (git `0bf381cc`), Steam app 2346660, build 26059581 | `dfhack.getDFHackVersion()`, startup log |
| dfhack-mcp | npm `1.4.1`, gitHead `aa80ecf9fc3dae432bea14bbfd6a16f7c5ff90df` | `npm view` |
| Node | v22.20.0 | `node --version` |
| OS / Steam | Ubuntu Linux, **Snap** Steam | install paths |
| Update policy | Both Steam apps are set to update only on launch | Steam manifests show `AutoUpdateBehavior 1` |
| Remote RPC | Listens on `127.0.0.1:5000`, with `allow_remote: false` | `ss -ltn`, `remote-server.json` |

Steam can't disable updates entirely. Before each test session, record the build IDs above and compare them.

## Findings

| # | Finding | Label |
|---|---|---|
| F1 | `dfhack-run` connects over RPC from outside the Snap sandbox, and it runs Lua in the live game. | Verified |
| F2 | **Snap sandbox issue.** By default, dfhack-mcp asks DFHack to load its Lua scripts from the npm package's folder using `dfhack.internal.addScriptPath`. The game runs inside Snap, which has a private `/tmp`, so it can't see a package installed under `/tmp`. Every sensor then fails with `mcp_fortStatus is not a recognized command`. **The fix uses the existing `DFHACK_MCP_QUERY_DIR` setting:** point it at a copy of the query scripts in a folder the game can read. The home directory works, for example `~/dev/...`. The script path is registered in memory only, and nothing is written into the game install. | Verified |
| F3 | With F2 applied, all 27 argument-free dfhack-mcp sensors plus `fort_status`, `stocks`, `jobs_and_labor` and `environment` returned results with no errors. | Verified |
| F4 | **Observation accuracy, a first spot-check (Q-05).** dfhack-mcp matched direct Lua reads on population (7), idle dwarves (6), drink units (54) and the date (5th Slate, Year 100, which is tick 39296). This is a match against DFHack's own data, **not** yet against the in-game screens. | Verified (partial) |
| F5 | **Correction:** `chronicle` *does* support an event cursor. It takes a `since` argument, and its event ids are documented as monotonic and stable across save and load. Earlier records listed "no event cursor" as a gap, which was wrong. **Caveat:** it reads DF's rolling, front-pruned report window, so a controller that polls too rarely can lose events. R2 already requires gaps to be exposed. | Verified that it exists. Gap behavior is untested. |
| F6 | **Tool inventory.** Read-only mode exposes 37 tools. With actuators enabled there are 45, adding `assign_work_detail`, `blueprint_apply`, `blueprint_undo`, `civilian_alert`, `game_save`, `pull_lever`, `work_order_cancel` and `work_order_create`. The tools were listed only, never called. | Verified |
| F7 | **There is no time control.** No tool pauses or advances time. `dfhack.world.ReadPauseState()` reads the pause state correctly (`true` while paused). | Verified |
| F8 | **Construction is missing.** `blueprint_apply` accepts `#dig` and `#zone` only. The installed quickfort has `-d, --dry-run`, documented as doing "all the motions... but don't actually change any game state". dfhack-mcp's preview step uses it. | Verified (from the schema and help text) |
| F9 | **Lifecycle (Q-01).** The installed `command line.txt` documents `-gen <id> <seed> <param title>`. There is no `load-save` command in this install. `quicksave` is present. The embark helpers present are `deep-embark`, `gui/embark-anywhere`, `embark-skills`, `embark-anyone` and `points`, and none automates the embark. `gui.simulateInput` exists. | Verified present. Behavior is untested. |
| F10 | Event text contains DF color markup such as `[C:7:0:1]`. A compact observation should strip it to save tokens. | Verified |

## Coverage for DEC-012 (the minimum v1 operations), updated

| Operation | Status on the pinned pair |
|---|---|
| `observe` | Covered by dfhack-mcp sensors (F3) |
| `events_since(cursor)` | **Covered** by `chronicle(since)` (F5). The controller must detect gaps. |
| `inspect_region` | Covered by `tile_region` |
| `designate` | dfhack-mcp `blueprint_apply`, dig and zone only. The actuator is not yet called. |
| `construct` | **Gap** (F8) |
| `configure_stockpile`, `set_farm_crops`, `find_sites` | **Gap.** Read sensors exist (`stockpiles`, `farming`, `geology`), but there are no write tools. |
| work orders, `assign_work_detail` | dfhack-mcp actuators. Not yet called. |
| `pause`, `advance_until` | **Gap** (F7). The controller must build these. |
| `checkpoint`, `verify_checkpoint`, reload | **Partial.** `game_save` dispatches only. There is no `load-save` (F9). |
| `action_status`, `goal_status`, lifecycle | **Gap.** These belong to the controller. |

## Not done, and the next steps

1. **Actuator semantics (Q-04).** Calling any actuator writes to the game. Do it on a **disposable copy** of the save, with the maintainer's approval.
2. **Time control and pause attribution (Q-02).** This needs advancing time, which changes the save. Use a disposable copy.
3. **Observations against the in-game screens (Q-05).** The maintainer could compare the stocks screen with F4.
4. **Durable save (Q-03, Q-10)** and **embark automation (Q-01).** These are the next gate experiments.
