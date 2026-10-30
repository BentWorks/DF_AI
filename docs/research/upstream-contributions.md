# Upstream contribution plan: dfhack-mcp

- **Context:** the maintainer suggested improving dfhack-mcp and contributing the gaps DF_AI uncovers. This plan answers Q-08.
- **Upstream:** [alexanderolvera/dfhack-mcp](https://github.com/alexanderolvera/dfhack-mcp). ISC license, active, with v1.5 in review as of 2026-10-29.
- **Status: on hold, by the maintainer's decision on 2026-10-29.** Build these capabilities inside DF_AI first. Decide later what, if anything, to contribute upstream, to avoid a stream of small upstream issues and PRs. Nothing has been filed upstream.

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

1. **Build in DF_AI first.** Implement each needed capability in DF_AI's own controller or adapter layer. Wrap dfhack-mcp where it already works, and add DF_AI-side code where it doesn't. For example, reaction orders go through DFHack's `workorder`, and retry safety comes from the controller ledger.
2. **Keep this table current.** For each candidate, note where DF_AI implemented it and whether it proved generally useful.
3. **Review upstream later as a batch.** Once DF_AI's version works, the maintainer decides whether to offer anything upstream, and how much. Only then would issues or PRs be filed, under the owner's account and signed by the AI collaborator.
