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

## Guarantees: implemented, tested, open (server v0.5.1)

These answer AI Collaborator Codex's three reviews of 2026-10-29 and 2026-10-30.

**How the test works.** [`experiments/g0/test_receipts.py`](../experiments/g0/test_receipts.py) asserts each expected outcome and exits non-zero on any failure. It passed 15 of 15 against the live tutorial fixture. Its "crashes" and "reloads" are **simulations inside a live game**: hand-written pending receipts and an injected older branch marker. They are not real process crashes or real save loads. One fixture is not proof of general reliability.

**Assumption.** DFHack RPC commands run one at a time on the game thread. So once a later RPC call returns, any earlier command, including a timed-out one, has finished. Reconciliation sends one such call before it checks the order-ID counter. This hasn't been verified against DFHack's source.

### Duplicate suppression

| Guarantee | Implemented | Tested | Open |
|---|---|---|---|
| Keyless calls are fresh requests; identical orders can be placed legitimately | Yes | Yes | — |
| A key reused with different parameters is a `key_conflict` | Yes | Yes | — |
| Applied but unacknowledged, and still present: reconciled as `applied` with no duplicate | Yes | Simulated | A real process crash |
| **Automatic replay is off by default.** An unchanged order-ID counter is reported, but the receipt stays `unknown` until the RPC-ordering assumption is checked. With `DFAI_TRUST_RPC_BARRIER=1`, an unchanged counter allows one replay, and the attempt history is kept. | Yes | Simulated, both settings | Checking the RPC ordering against DFHack, which would let replay be switched on |
| Applied, then removed before reconciliation: stays `unknown` and isn't replayed | Yes | Simulated | — |
| Reconciliation for build, designate, appoint and the other non-order kinds | No. These return `unresolved`. | — | Evidence-based checks for each kind |

### Request attribution

| Guarantee | Implemented | Tested | Open |
|---|---|---|---|
| An order is attributed only if job, reaction, amount, frequency, material category (exact set) and **specific material** (`mat_type`/`mat_index`) all match. An unsupported comparison gives `unknown`. | Yes | Yes. Frequency and category differences, and iron versus granite. | — |
| Two pending requests that can't be told apart, or several matching orders, stay `unknown` for both, whichever is reconciled first | Yes | Simulated, both orders | — |
| A new request is refused while an identical one is unresolved. `settle` records an **adjudication**: the outcome is `applied` (it happened, even if later removed), `not_applied` (backed by evidence) or `abandoned` (still uncertain, duplicate risk accepted). It records the evidence, the items inspected, the tick and the branch. Evidence is required. | Yes | Yes | — |
| Mutations and checkpoints run one at a time through a single process lock | Yes | No | Other writers (a person playing, game autosaves) aren't covered by the lock |

### Branch detection

| Guarantee | Implemented | Tested | Open |
|---|---|---|---|
| A save-carried marker, `{token, seq}` in DFHack persistent site data, is written **after** each successful or uncertain mutation. A save taken in between can only make a receipt look stale, never falsely `applied`. | Yes | Partly. The marker advanced after a mutation. | A save taken between mutation and marker, and an interruption there |
| A loaded state with an older or foreign marker marks later receipts `stale`. A backward game clock also does. | Yes | Simulated (injected marker) | **Real UI loads** of an earlier checkpoint, before and after the old tick, including an application missing from the restored state |
| A marker write that fails is reported in the receipt, not swallowed | Yes | No | — |

### Other

| Guarantee | Implemented | Tested | Open |
|---|---|---|---|
| Applied, completed and goal met kept separate (DEC-004) | Partly. `applied` means accepted. | No | Completion tracking and goal predicates |
| Appointment legality uses the game's flags. Replacement validates first, with rollback. | Yes | Partly | UI rules for each role. Checks after the screen is reopened. Triggering the rollback path. |
| Automation profile: `advance` reports menus closed, popups dismissed and the order timer restarted | Yes | Yes | Named switches in an evaluation profile |

## Lessons from building it on the live fixture (2026-10-29)

These are all Verified on DF v0.53.16 with DFHack 53.16-r3, on the tutorial fort.

- **Orders need a material.** A furniture order with no material shows in-game as "Make *unknown material* bed". It was never handed to a workshop in about 15 days. The same order with `material_category: wood` was built within a day. dfhack-mcp 1.4.1's `work_order_create` can't set a material category, so the server creates orders through DFHack's `workorder` instead.
- **Order checks can stall.** The game's order-check countdown (`plotinfo.manager_timer`, DF's `quota_checktime`) sat at 0 for days, so no order was processed. It started running after the maintainer opened the Work Orders screen and appointed a manager through the UI. The help topic `POPUP_WORK_ORDERS` was marked seen at the same time, which is a candidate trigger. Since then it has kept running, even with no manager, in a 7-dwarf fort. `advance` and `order` restart it if it's stuck at 0.
- **Scripted appointments match UI appointments.** Writing the assignment and the historical-figure position link produced the same data the game's own UI writes, verified by diff. The Nobles screen shows it.
- **Open menu screens block time,** just like popups. A simulated `LEAVESCREEN` closes them. Popups need removing from `world.status.popups`. Closing the Nobles screen once seemed to write the screen's cached appointments back.
- **Job names differ from the UI.** A chair is `ConstructThrone`. There's no `MakeTable`; use `ConstructTable`.
- **Labors.** In this version, labors that no work detail covers, such as carpentry, masonry and brewing, are enabled for every dwarf by default.
