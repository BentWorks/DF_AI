# Decision log

Statuses and evidence labels are defined in [docs/README.md](../README.md).
As of 2026-10-22, **nothing here is Accepted.** No maintainer approval has been
given, and no gameplay test has been run.

| ID | Decision | Status | Source |
|---|---|---|---|
| DEC-001 | A complete run covers launch, world setup, embark, fortress management, events, bounded time, recovery and a verified ending. Prepared-save runs are milestones only and must not be labeled full-lifecycle. | AI-agreed | Codex [D1](https://github.com/BentWorks/DF_AI/discussions/1#discussioncomment-19132226), Claude [reply](https://github.com/BentWorks/DF_AI/discussions/1#discussioncomment-19132246) |
| DEC-002 | Reuse dfhack-mcp for observation and its current actuators, behind a separate DF_AI controller. The controller owns time, lifecycle, reconciliation and outcome records. Reuse depends on compatibility and ownership tests. | AI-agreed | Claude D4a, Codex [response](https://github.com/BentWorks/DF_AI/discussions/1#discussioncomment-19132290) |
| DEC-003 | **One writer.** During a run, agents talk only to the controller. The controller alone calls downstream write tools and the step operation. It wraps dfhack-mcp's actuators so their preview, apply and readback safety is kept. | AI-agreed | Codex response, Claude R1 review |
| DEC-004 | **Execution and goals are tracked separately.** An action record has `execution_status`, optional observed work completion, and a separate `goal_status`, each with evidence, tick and uncertainty. `blocked` is recoverable. `unknown` is a real state after a disconnect, and it is reconciled before any retry. Records are keyed to save and session identity. | AI-agreed | Claude D2 contract, Codex refinement |
| DEC-005 | **Time control.** Steps are serialized and bounded. Each step records requested and actual ticks, pause state, stop evidence and a wall-clock watchdog. Pause cause may be `unknown` or have multiple contributors. | AI-agreed | Claude D2 time contract, Codex refinement |
| DEC-006 | **v1 success boundary.** A fixed-profile path covers launch, world setup and embark, then reaches G1, first winter. A separate fixture must prove real fortress-loss detection and termination. A lifecycle feasibility gate is added; see Q-01. | Under review (R1 plus Claude amendment A2) | [R1](../proposals/R1.md) |
| DEC-007 | The G0–G4 ladder is a scenario progression. Each scenario fixes start date, supplies, difficulty, visibility, reflexes and budgets. Reserves must hold over a sustained interval with a trend. G3 needs a fixture that actually triggers a hostile event. | AI-agreed | Claude ladder, Codex refinement |
| DEC-008 | **Spatial planning.** Code validates terrain, reachability, materials and layout. The model chooses among candidates and blueprint phases. Freeform layouts get the same validation and preview. Runs record visibility policy and blueprint assistance. | AI-agreed | Claude, Codex R1 |
| DEC-009 | **Endings.** The terminal states are `objective_achieved`, `fortress_lost`, `budget_exhausted`, `user_stopped` and `infrastructure_failure`. DF's own loss state is the primary evidence. Citizen count is a diagnostic. | AI-agreed | Codex D3, Claude reply |
| DEC-010 | **Validation order.** Pin a version pair and assess reuse. Then G0, then prepared-save brewing, then two harnesses on an unchanged controller, then full startup plus G1 and the loss fixture, then G2–G4. | AI-agreed | Codex D5 and R1, Claude step 0 |
| DEC-011 | **Goal/loss precedence.** A goal counts as achieved only once its full sustained interval completes with the fortress alive. Loss evidence at or before that tick makes the outcome `fortress_lost`. | Proposed (Claude amendment A1) | [R1 review](../proposals/R1.md#claude-review) |
| DEC-012 | The minimum G1 tool catalogue is the list in [R1 review A3](../proposals/R1.md#a3-minimum-g1-tool-catalogue). | Proposed (Claude amendment A3) | [R1 review](../proposals/R1.md#claude-review) |

## Disagreements

There are no open disputes between the AI collaborators as of 2026-10-22.
Earlier differences were resolved by refinement:

- **Completion semantics.** Claude's first contract treated an outcome predicate as proof that an action completed. Codex pointed out that a stock threshold can be met by trade or another order. Claude accepted the split into execution and goal status, recorded as DEC-004.
- **Pause attribution.** Claude proposed a single pause reason. Codex noted that pause causes can overlap. Claude accepted `unknown` and multiple causes, recorded as DEC-005.

## What consensus requires

Consensus requires an explicit **Accepted** from the maintainer on a consolidated
proposal, plus agreement from the participating reviewers. When that happens,
this log is updated, and the conclusion is posted in the discussion.
