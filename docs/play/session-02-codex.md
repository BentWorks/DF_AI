# Play session 2: Codex, headless (2026-10-29)

- **Client:** `codex exec` (codex-cli 0.160.0, default model), `-s read-only`, with the DF_AI server attached via `-c mcp_servers.dfai...` and `default_tools_approval_mode="approve"`.
- **Server:** v0.2, with 18 tools.
- **Prompt:** the same goal as session 1, picking up from the fort Claude left behind.
- **Transcript:** `runs/play/sessions/codex-20261029-170757.jsonl`, kept locally.

**Two failed attempts came first.** With no approval mode set, and then with `"auto"`, Codex exec refused every MCP call: "MCP tool call requires approval, but approval policy is never". `"approve"` fixed it. This is now in [server.md](../server.md).

| Measure | Value |
|---|---|
| Game time played | 16,800 ticks, exactly two weeks (9 to 23 Hematite, year 100) |
| Dwarves alive | 7 of 7, with no injuries or hostiles |
| Tool calls | 87 |
| Wall time | about 5 minutes |
| Tokens | 866k input (809k cached), 4.8k output |

## What the AI did

- **Food:** built a working fishery. Food rose from 28 to 70.
- **Housing:** finished a seven-bed dormitory and a three-seat dining hall.
- **Farming and storage:** added underground food storage and a second farm, with summer plump helmets assigned to both.
- **Protection:** stopped seeds, brewing plants and alcohol from being cooked, and expanded barrel production.
- **Cleanup and checks:** used the v0.2 tools to remove the 3 workshops session 1 built by mistake, assigned an owner, and counted items.
- **Checkpoints:** saved two.

## Gaps it reported

| Gap | Next step |
|---|---|
| No tool to set crops; it used `autofarm runonce` | Add a `set_crops(plot_id, season, plant)` tool |
| `lua` is blocked by the allowlist | This is deliberate (DEC-003 and the safety rules). Keep it blocked, and add specific tools as needs show up. |
| A dig preview was refused because 9 tiles overlapped existing furniture or designations | The behavior is correct. Improve the message so it lists the conflicting tiles. |
| Brewing stalled: no brewable plants | Gameplay, not tooling. It needs farming or gathering of brewable crops. |

## Comparison with session 1

Both AIs used the same server, the same tools and the same fort. Session 1 ran first on v0.1; session 2 continued from where it ended, on v0.2.

**Both kept all 7 dwarves alive and made sensible priority calls.** Claude focused on infrastructure and drink. Codex fixed the food trend and housing. These are single sessions, so they aren't a benchmark.
