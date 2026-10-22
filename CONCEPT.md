# DF_AI — Concept

> Original design sketch. This repository is at the proposal stage; the code
> below is illustrative and has not been validated against a live game here.
> In particular, the sample command tool does not enforce its stated whitelist,
> and `advance()` returns before its scheduled pause. See [README.md](README.md)
> for the current direction and [EVALUATION.md](EVALUATION.md) for design review.

An AI agent that plays Dwarf Fortress on Linux. The agent manages a fortress by
talking to DFHack, which runs inside the game. It works from structured game
data, with no screen reading needed.

## Feasibility

This is practical today. The pieces already exist:

- **DFHack runs natively on Linux.** It supports the Steam/Premium release (v50+)
  and the classic release. Steam lists DFHack as a free add-on, or a GitHub
  release can be unpacked into the DF folder.
- **DFHack has a remote server.** It listens on `localhost:5000` (TCP with
  protobuf messages). The bundled `dfhack-run` command connects to it, runs any
  DFHack command or Lua code in the live game, and prints the output to the
  caller's terminal. This is the control channel.
- **Lua can reach nearly the whole game.** Through `df.global.world` a script
  can read units, items, buildings, jobs, map tiles and stocks.
  `require('json')` lets a script return JSON.
- **DFHack already has high-level commands an agent can use:**
  - `quickfort` places dig, build and zone blueprints from CSV-style text,
    which suits an LLM well.
  - `buildingplan` handles construction.
  - `workorder` creates manager orders.
  - `autolabor` and `labormanager` assign jobs to dwarves.
  - `autobutcher`, `autofarm`, `autonestbox`, `prioritize`, `stocks`, and others.
- **It has been done without an LLM.** `df-ai` by BenLubar is a DFHack plugin
  that plays fortress mode autonomously using hand-written rules. An LLM agent
  would replace those rules with its own decisions.

## Architecture

```
Claude Code / agent
      │  MCP tools
      ▼
dwarf-mcp (Python FastMCP server)
      │  subprocess: dfhack-run lua ...   (or protobuf RPC on :5000)
      ▼
Dwarf Fortress + DFHack (running, on localhost)
```

This is the same pattern as the `imggen` MCP server sitting in front of ComfyUI.

## Setup

### 1. Install DF and DFHack

On Steam, install Dwarf Fortress and then the free "DFHack" app. Launch DF, and
the DFHack console should appear. Load or start a fortress.

### 2. Check the remote channel

From the DF install directory:

```bash
cd ~/.steam/steam/steamapps/common/"Dwarf Fortress"
./dfhack-run help
./dfhack-run lua "print(#df.global.world.units.active)"
```

The server's settings live in `dfhack-config/remote-server.json`. Keep
`allow_remote: false` so it only listens on localhost.

### 3. Write Lua "sensor" scripts that return JSON

Put them in `dfhack-config/scripts/`. For example, `agent/summary.lua`:

```lua
local json = require('json')
local units = {}
for _, u in ipairs(df.global.world.units.active) do
  if dfhack.units.isCitizen(u) then
    table.insert(units, {
      id = u.id,
      name = dfhack.df2utf(dfhack.TranslateName(dfhack.units.getVisibleName(u))),
      job = u.job.current_job and df.job_type[u.job.current_job.job_type] or "idle",
      stress = u.status.current_soul and u.status.current_soul.personality.stress or 0,
    })
  end
end
print(json.encode({
  year = df.global.cur_year,
  tick = df.global.cur_year_tick,
  paused = df.global.pause_state,
  citizens = units,
}))
```

Call it with `./dfhack-run agent/summary`.

### 4. Build the MCP bridge

A minimal version:

```python
import subprocess
from mcp.server.fastmcp import FastMCP

DF = "/path/to/steamapps/common/Dwarf Fortress"
mcp = FastMCP("dwarf-fortress")

def run(*args: str) -> str:
    r = subprocess.run([f"{DF}/dfhack-run", *args], cwd=DF,
                       capture_output=True, text=True, timeout=60)
    return r.stdout + r.stderr

@mcp.tool()
def fortress_summary() -> str:
    return run("agent/summary")

@mcp.tool()
def dfhack_command(command: str) -> str:
    """Run a whitelisted DFHack command, e.g. 'stocks', 'workorder ...'."""
    return run(*command.split())

@mcp.tool()
def place_blueprint(csv_path: str, x: int, y: int, z: int) -> str:
    return run("quickfort", "run", csv_path, "-c", f"{x},{y},{z}")

@mcp.tool()
def advance(ticks: int = 1200) -> str:
    """Unpause, then auto-pause after N game ticks (1200 = one in-game day)."""
    return run("lua", f"df.global.pause_state=false; "
               f"dfhack.timeout({ticks},'ticks',function() df.global.pause_state=true end)")

if __name__ == "__main__":
    mcp.run()
```

Register it with Claude Code:

```bash
claude mcp add dwarf-fortress -- python /path/to/dwarf_mcp.py
```

### 5. Run it as a turn-based loop

Each turn: pause, read state, decide (dig, build, orders, labor), act, then
advance N ticks and repeat. The `advance` tool makes the real-time game behave
like turns. `dfhack.timeout` in ticks only counts while the game is unpaused, so
turns line up with game time.

## Practical issues

- **Spatial reasoning is the hard part.** The map is 3D and large. Give the
  agent an ASCII view of one z-level at a time, built from
  `dfhack.maps.getTileType` and designation data. Have it act through
  `quickfort` blueprints, not tile-by-tile commands.
- **Keep the context small.** Raw unit and item lists are huge. Write summary
  scripts (food and drink counts, idle dwarves, threats, unhappy dwarves, recent
  announcements from `df.global.world.status.reports`) instead of dumping
  objects.
- **Use a whitelist.** A free-form `lua` tool can corrupt a save. Expose curated
  commands, and keep raw Lua as a debug-only tool.
- **Automate the micromanagement.** Turn on `autolabor`, `autobutcher`,
  `seedwatch`, and `orders import library/basic` so the agent works at the
  strategic level.
- **Headless running is possible.** The game needs a display, so run it under
  `Xvfb` if it should run unattended.
- **Updates can break things.** DF and DFHack have to match versions, and a
  Steam auto-update can break DFHack until DFHack releases an update. Consider
  pinning updates.

## Suggested first milestone

Start with read-only sensor tools while a human plays, with the agent acting as
an advisor. Add the action tools after the state summaries prove useful.
