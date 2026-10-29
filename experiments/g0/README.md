# G0 probes

These are small scripts used for the first write tests on the pinned pair, DF v0.53.16 and DFHack 53.16-r3.
The results are in [docs/research/g0-probes-2026-10-29.md](../../docs/research/g0-probes-2026-10-29.md).
**Run them only on a disposable save.** They advance time, save the game and create work orders.

| File | Purpose |
|---|---|
| `df.sh` | Runs a DFHack command or Lua code in the live game, through `dfhack-run`. Set `DFHACK_DIR` if DFHack isn't in the Snap Steam location. |
| `step.lua` | An in-game bounded step: `begin <ticks>`, `status` and `cancel`. It reports elapsed ticks, timer state and pause causes, and refuses to start while a popup is open. |
| `step.py` | The step driver. It polls until paused or until the wall-clock watchdog fires, cancels a stale timer, and can inject an external pause. |
| `save_probe.py` | Triggers `quicksave` and times file changes until they settle. |
| `mcp_session.py` | Drives one dfhack-mcp stdio session from a JSON list of calls, including a mode that kills the server mid-call. |

The DFHack lookups and the DFHack Lua script need a path the game can read. On Snap Steam, that is not `/tmp`.
