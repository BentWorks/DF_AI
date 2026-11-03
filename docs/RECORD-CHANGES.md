# Record changes

Newest entries are first. Each entry names who changed what, and links the
pull request or commit.

## 2026-10-30: AI Collaborator Claude

- **DEC-015 revision B is Accepted.** The maintainer accepted it [explicitly](https://github.com/BentWorks/DF_AI/discussions/1#discussioncomment-19298906) on 2026-10-30, and both AI collaborators had agreed. It is recorded as a maintainer decision, not community consensus.
- Q-11 remains open as validation work, tracked by T-11.

## 2026-10-29 (sixth entry): AI Collaborator Claude

- Replaced DEC-015 with Codex's **revision B** wording and staging. It is now AI-agreed; the maintainer's acceptance of the exact wording is pending.

## 2026-10-29 (fifth entry): AI Collaborator Claude

- Added the T-11 findings so far. Orders with no material, not the missing manager, were the main reason the tutorial's orders never ran. A stalled order-check timer was a second cause. Scripted appointments match UI appointments.

## 2026-10-29 (fourth entry): AI Collaborator Claude

- Added `test-plan.md`, with a test-to-question index and the full test T-11 for the manager and production paths. The maintainer raised the missing manager.
- Widened T-11 and DEC-015 from the manager to **all nobles and administrators**, at the maintainer's request, with a live table of the 14 positions; only the expedition leader is filled. DEC-015 is noted as favored by the maintainer, pending Codex.
- Added Q-11, and DEC-015 as Proposed: new `assign_position` and `queue_workshop_job` operations, and manager presence as a precondition.
- Added `research/upstream-contributions.md`, at the maintainer's suggestion: dfhack-mcp contribution candidates U1–U7, and Q-08 updated to match. **On hold** by the maintainer's decision: build in DF_AI first, and review upstream later.
- Recorded that brewing is ordered by recipe, "brew drink" or "brew drink from fruit", never by specific drink.

## 2026-10-29 (third entry): AI Collaborator Claude

- Added `research/g0-probes-2026-10-29.md`, the first **write** tests on the disposable tutorial fixture. It covers bounded stepping (10 out of 10 exact), pause attribution, popup blocking and dismissal, controller-crash recovery, quicksave completion and slot rotation, and dfhack-mcp work-order retry behavior. The retry tests showed that a crash mid-apply can create duplicates.
- Added the probe scripts in `experiments/g0/`.
- Updated Q-02, Q-03 and Q-04, and noted a new gap: dfhack-mcp can't create reaction orders such as brewing.

## 2026-10-29 (second entry): AI Collaborator Claude

- Added `research/reuse-audit-2026-10-29.md`, the first live, read-only checks on the maintainer's machine. It records the pinned versions and findings F1–F10, including a Snap sandbox issue and its fix, and an updated coverage table for DEC-012.
- Corrected `research/dfhack-mcp.md`: `chronicle` does support an event cursor.
- Updated Q-05 to partial and Q-09 to recorded.

## 2026-10-29: AI Collaborator Claude

- Recorded the maintainer's acceptance of [R2](https://github.com/BentWorks/DF_AI/discussions/1#discussioncomment-19245630) and [DEC-014](https://github.com/BentWorks/DF_AI/discussions/1#discussioncomment-19252526), given on 2026-10-28. DEC-001 to DEC-014 are now Accepted, and R2 is marked Accepted.
- Q-06 is marked resolved. Every other open question still needs a live test.
- Noted that this is not community consensus, since no independent human reviewer took part.
- Added `decisions/CONCLUSION-2026-10-29.md`. The maintainer chose to conclude now, so the result is labeled a **maintainer decision**. It was announced in [discussion #1](https://github.com/BentWorks/DF_AI/discussions/1#discussioncomment-19274432).

## 2026-10-22 (third entry): AI Collaborator Claude

- DEC-014 was replaced with Codex's clarified wording and moved to AI-agreed. Missing replies are not agreement, and a conclusion without wider review is labeled a maintainer decision.
- Rewrote "What consensus requires" in the decision log to match.
- Part of [PR #2](https://github.com/BentWorks/DF_AI/pull/2).

## 2026-10-22 (second entry): AI Collaborator Claude

- Added `proposals/R2.md`, summarizing Codex's R2. R1 is marked Superseded.
- In the decision log, DEC-006, DEC-011 and DEC-012 moved to AI-agreed. DEC-013 (budgets) was added as AI-agreed, and DEC-014 (consensus process) as Proposed.
- Added Q-10 (save/reload gate). Q-06 is now waiting only on the maintainer.
- Part of [PR #2](https://github.com/BentWorks/DF_AI/pull/2).

## 2026-10-22: AI Collaborator Claude

- Created the `docs/` design record: an index and status vocabulary, the decision log (DEC-001 to DEC-012), open questions (Q-01 to Q-09), a summary of R1 with Claude's review and amendments A1–A4, and the dfhack-mcp research notes.
- Source discussion: [#1](https://github.com/BentWorks/DF_AI/discussions/1).
