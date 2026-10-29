# The DF_AI game server

This is an MCP server that lets an AI **play** Dwarf Fortress. Any MCP-capable client can use it: Claude Code, Codex,
Gemini CLI, the agent-harness project, or another harness. It runs on the pinned pair: DF v0.53.16 with DFHack 53.16-r3.

## How it fits together

```
AI client  --MCP stdio-->  dfai server (src/dfai)  --+--> dfhack-mcp 1.4.1 (vendored): observations, some actions
                                                     +--> dfhack-run + our Lua (src/dfai/lua): time, popups,
                                                          positions, state, orders (workorder), quickfort builds
                                                     +--> SQLite action ledger (runs/play/ledger.sqlite)
```

The server is the **single writer** (DEC-003). Agents only see its tools.

## Tools

| Tool | What it does |
|---|---|
| `observe` | A compact overview of about 3 KB: date, population, food and drink days, alerts, citizens and their jobs, workshops, orders, noble posts, popups, and new events since the last call |
| `sensor` | Any read-only dfhack-mcp report, such as map, geology, work details, farming, stockpiles or threats |
| `advance` | Runs N ticks, then pauses. It stops early on game interrupts and reports why. It first closes open menus, dismisses popups (returning their text) and restarts stalled order checks. |
| `designate` | Dig and zone blueprints, through dfhack-mcp's preview-then-apply |
| `build` | `#build`, `#place`, `#zone` and `#dig` blueprints through quickfort, with a dry run first |
| `order` | Manager orders for jobs or reactions, with a material category. Each order is verified in-game and recorded under an idempotency key. |
| `cancel_order` | Cancels an order, through dfhack-mcp |
| `appoint` | Assigns a noble or administrator position |
| `labor` | Adds or removes a dwarf from a work detail, through dfhack-mcp |
| `dfhack` | Runs allowed DFHack automation commands: seedwatch, autofarm, autobutcher, orders import and similar |
| `checkpoint` | Quicksaves, waits for the save to finish, and copies the save to `runs/play/checkpoints/` |
| `action_log` | Shows recent recorded actions and their outcomes |

## Setup

```sh
conda create -p ~/dev/envs/df-ai python=3.11 -y && ~/dev/envs/df-ai/bin/pip install "mcp==2.3.0"
(cd vendor/dfhack-mcp && npm ci --ignore-scripts)        # pinned dfhack-mcp; its Lua must be game-readable
./dfai-server.sh                                         # stdio MCP server
```

**Clients:**
- **Claude Code** picks the server up from the project's `.mcp.json`. To run headless:
  `claude -p "<goal>" --strict-mcp-config --mcp-config .mcp.json --allowedTools "mcp__dfai__*"`.
- **Codex CLI** (tested with codex-cli 0.160.0). In `exec` mode, MCP tools are refused unless pre-approved. `default_tools_approval_mode="approve"` works; `"auto"` and `"writes"` did not. Use `-s read-only` so Codex can only act through the game tools:
  ```sh
  codex exec -s read-only --skip-git-repo-check \
    -c 'mcp_servers.dfai.command="/path/to/DF_AI/dfai-server.sh"' \
    -c 'mcp_servers.dfai.tool_timeout_sec=300' \
    -c 'mcp_servers.dfai.default_tools_approval_mode="approve"' \
    "<goal>"
  ```
- **Gemini CLI or agent-harness:** register `./dfai-server.sh` as a stdio MCP server. These haven't been tested yet.

Paths default to Snap Steam on Linux. Override them with `DFAI_DFHACK_DIR`, `DFAI_DF_DIR`, `DFAI_SAVE_DIR` and the other variables in `src/dfai/config.py`.

## Lessons from building it on the live fixture (2026-10-29)

These are all Verified on DF v0.53.16 with DFHack 53.16-r3, on the tutorial fort.

- **Orders need a material.** A furniture order with no material shows in-game as "Make *unknown material* bed". It was never handed to a workshop in about 15 days. The same order with `material_category: wood` was built within a day. dfhack-mcp 1.4.1's `work_order_create` can't set a material category, so the server creates orders through DFHack's `workorder` instead.
- **Order checks can stall.** The game's order-check countdown (`plotinfo.manager_timer`, DF's `quota_checktime`) sat at 0 for days, so no order was processed. It started running after the maintainer opened the Work Orders screen and appointed a manager through the UI. The help topic `POPUP_WORK_ORDERS` was marked seen at the same time, which is a candidate trigger. Since then it has kept running, even with no manager, in a 7-dwarf fort. `advance` and `order` restart it if it's stuck at 0.
- **Scripted appointments match UI appointments.** Writing the assignment and the historical-figure position link produced the same data the game's own UI writes, verified by diff. The Nobles screen shows it.
- **Open menu screens block time,** just like popups. A simulated `LEAVESCREEN` closes them. Popups need removing from `world.status.popups`. Closing the Nobles screen once seemed to write the screen's cached appointments back.
- **Job names differ from the UI.** A chair is `ConstructThrone`. There's no `MakeTable`; use `ConstructTable`.
- **Labors.** In this version, labors that no work detail covers, such as carpentry, masonry and brewing, are enabled for every dwarf by default.
