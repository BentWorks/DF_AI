# Upstream contribution plan: dfhack-mcp

- **Context:** the maintainer suggested improving dfhack-mcp and contributing the gaps DF_AI uncovers. This plan answers Q-08.
- **Upstream:** [alexanderolvera/dfhack-mcp](https://github.com/alexanderolvera/dfhack-mcp). ISC license, active, with v1.5 in review as of 2026-10-29.
- **Status:** a plan only. Nothing has been filed upstream yet.

## What upstream accepts

Read from its `CONTRIBUTING.md` and recent PRs on 2026-10-29:

- **"Facts, not advice."** Sensors report the game state. Actuators "execute, never decide", behind `DFHACK_MCP_ACTUATORS`, using preview, then token, then apply, readback and undo.
- **Its stated scope is co-pilot, not autopilot.** That is why time control, lifecycle, the ledger and run policy stay in DF_AI's controller, as R2 and DEC-002 say. We can ask whether a bounded `advance` primitive would fit, but we shouldn't assume it.
- **Every change is verified against a live fort**, using its tiered harness (T0 to T2) and invariants, with Node 24 for development. It ships a **disposable headless DF container** (`df-headless:53.15`), which may also answer DF_AI's need for unattended running.
- **Issues come first,** with priority labels (P0–P2), then PRs.

## Candidates, in suggested order

| # | Contribution | Evidence | Upstream status | Size |
|---|---|---|---|---|
| U1 | **Linux and Snap Steam note.** The game can't see a query dir under `/tmp`. Document `DFHACK_MCP_QUERY_DIR` for Snap and Flatpak, and possibly detect it when `addScriptPath` registers but scripts aren't found. | [Audit F2](reuse-audit-2026-10-29.md) | Not filed. Upstream development is Windows-first. | Small |
| U2 | **Doc fix:** `MakeTable` in the `work_order_create` schema isn't a job type on 53.16. `ConstructTable` is. | [G0 probes](g0-probes-2026-10-29.md) | Fits the open docs sweep, #72 | Tiny |
| U3 | **Reaction orders:** an optional `reaction` argument for `work_order_create` (`job_type: CustomReaction`), which brewing, smelting and soap all need. | [G0 probes](g0-probes-2026-10-29.md), [T-11](../test-plan.md#t-11-manager-and-production-paths) | Not filed. Related to #94, order conditions. | Medium |
| U4 | **Retry safety after a lost receipt.** An apply that lands while the client dies leaves the order unacknowledged, and the duplicate flag is advisory. Proposal: an optional client `request_id` remembered in-game, so a repeated apply with the same id returns the original receipt instead of acting twice. | [G0 probes](g0-probes-2026-10-29.md) | Not filed. #64 fixed a *different* double-execution path. | Medium |
| U5 | **Build and place blueprint modes**, needed for Dreamfort beyond its dig phases. | Audit F8 | Staged as a follow-up in #88 / PR #109. Offer help there. | Large |
| U6 | **`assign_position` actuator** for the manager and other administrators, pairing with the existing `nobles_and_administrators` sensor (#75). | [T-11](../test-plan.md#t-11-manager-and-production-paths) | Not filed | Medium |
| U7 | **Popup facts:** a sensor for open box popups, which block time (G0). Possibly a `dismiss_popup` actuator. | [G0 probes](g0-probes-2026-10-29.md) | Not filed | Small to medium |

**Stays in DF_AI** (strategy and run policy, outside upstream's scope):
- bounded stepping and pause attribution
- checkpoint copy-out and reload
- the action ledger and reconciliation
- goals and endings
- the lifecycle

## Process

1. **The maintainer approves filing.** Issues go out under the owner's GitHub account, signed by the AI collaborator, as in discussion #1.
2. **File U1, U3, U4 and U6 as issues.** Fold U2 into #72, and offer U5 on #88. Each issue cites DF_AI's evidence and the pinned versions.
3. **Wait for interest.** Wait for the upstream maintainer's response before writing PRs. Then develop in a fork, with Node 24, the T0 contract, and live verification on our fixture.
4. **Track each item here.** For each one, record its link and state: filed, accepted, PR open, merged, or declined. If declined, record the DF_AI-side workaround.
