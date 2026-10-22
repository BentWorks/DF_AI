# Research: dfhack-mcp

- **Source:** the [alexanderolvera/dfhack-mcp README](https://github.com/alexanderolvera/dfhack-mcp), read 2026-10-22. It is ISC-licensed, mostly Lua and TypeScript, and was last pushed 2026-08-09.
- **Evidence label:** every point below is **Documented**. Nothing has been verified by DF_AI.

## What it provides

- **Sensors.** About 37 sensor and reference tools, which are fog-of-war honest and return "facts, not advice". They include `fort_status`, `stocks` (with days of supply), `threats`, `unmet_needs`, `jobs_and_labor`, `military`, `injuries_and_health`, `defenses`, `burrows`, `mechanisms`, `moods`, `mandates_and_justice`, `rooms_and_zones`, `trade`, `environment`, `find_unit`, `citizen`, `chronicle`, `map_overview`, `tile_region` (capped at 100×100), `geology`, `game_data`, `identify` and the `wiki_*` tools.
- **Opt-in actuators.** These are enabled with `DFHACK_MCP_ACTUATORS=1`. Each one follows preview, then a single-use token, then apply with readback, plus an undo handle.
  - Work orders: list, create and cancel.
  - Quickfort `blueprint_apply` and `blueprint_undo`, for **dig and zone only** in v1.
  - Work detail assignment.
  - `civilian_alert` and `pull_lever`. A lever pull only queues a job.
  - `game_save`, which is asynchronous. It confirms dispatch only and writes to the rotating autosave folder.
- **Transport.** DFHack Remote RPC on `127.0.0.1:5000`. A fort must be loaded.
- **Raw Lua.** `run_lua` is available only behind `DFHACK_MCP_DEV=1`.
- **Testing.** A live-fort verification harness is described in `docs/VERIFY.md`.

## Gaps relative to DF_AI

The gaps are time control, construction (build and place), stockpile and farm configuration, an event cursor, durable save confirmation, outcome tracking beyond readback, and every lifecycle step before a fort is loaded.
