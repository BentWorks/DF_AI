# Play session 1: Claude, headless (2026-10-29)

- **Client:** `claude -p` (Claude Code, default model), `--strict-mcp-config --mcp-config .mcp.json --allowedTools "mcp__dfai__*"`.
- **Prompt:** [runs/play/session1_prompt.md](../../runs/play/session1_prompt.md), which is not committed. It gave Claude about two in-game weeks to move the tutorial fort toward self-sufficiency, keep everyone alive, and finish with a report.
- **Server:** the first version, with 12 tools. The transcript is `runs/play/sessions/claude-20261029-165636.jsonl`, kept locally.

| Measure | Value |
|---|---|
| Game time played | 21,000 ticks, about 17.5 days (19 Felsite to 9 Hematite, year 100) |
| Dwarves alive | 7 of 7 |
| Model turns / tool calls | 87 / 85 |
| Wall time | 7.6 minutes |
| Reported cost | US$1.91 |

## What the AI did

**Built and organized:**
- **Digging:** a workshop hall, a dormitory and a farm room.
- **Workshops:** a still, a kitchen, a farmer's workshop and a mason's workshop.
- **Stockpiles:** refuse, food and wood, plus 22 trees marked for chopping.
- **Rooms:** 5 beds with a dormitory zone, an office and a dining room.

**Ran the fort:**
- **Nobles:** appointed a bookkeeper, a broker and a chief medical dwarf.
- **Furniture:** queued and largely built beds, tables, chairs, barrels and doors.
- **Drink:** brewed it up from 39 to 128 units, then cancelled brewing once the plants ran out.
- **Farming:** planted plump helmets, with seedwatch protecting the seeds.
- **Checkpoints:** saved at the start and end of the session.

## Problems it reported, and the fixes in server v0.2

| # | Problem | Fix |
|---|---|---|
| 1 | Wrong building keys in the instructions: `ws`, `wk` and `wf` built the wrong workshops | Rewrote every key list from quickfort's source: workshops, furnaces, furniture, zones and stockpiles |
| 2 | No way to remove a building | New `remove_building` and `buildings` tools |
| 3 | `dfhack enable ...` was blocked | `enable` and `disable` now work for allowed tools |
| 4 | `material_category: stone` was rejected | The docs now say `material='INORGANIC'` for stone |
| 5 | Wrong job names, such as `ConstructBarrel` | New `job_types` lookup. The barrel job is `MakeBarrel`. |
| 6 | `sensor('citizen')` always errored | dfhack-mcp's schema wants a *string* id; the server now converts argument types to each upstream schema. Tool errors are returned as readable JSON. |
| 7 | No way to count tools like picks | New `find_items`. It shows the fort has **3** iron picks, not 1, so the dig bottleneck was labor, not picks. |
| 8 | No way to assign rooms; no single-dwarf labor | New `assign_owner` and `set_labor`. Dig priority is still missing. |
