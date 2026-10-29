# Conclusion: architecture discussion (2026-10-29)

- **Outcome:** a **maintainer decision**. This is not community consensus.
- **Announced in:** [discussion #1](https://github.com/BentWorks/DF_AI/discussions/1#discussioncomment-19274432).

## Approvals

| Item | Maintainer | AI Collaborator Claude | AI Collaborator Codex |
|---|---|---|---|
| [R2](https://github.com/BentWorks/DF_AI/discussions/1#discussioncomment-19133574) ([summary](../proposals/R2.md)) | [Accepted 2026-10-28](https://github.com/BentWorks/DF_AI/discussions/1#discussioncomment-19245630) | [Accepted 2026-10-22](https://github.com/BentWorks/DF_AI/discussions/1#discussioncomment-19133921) | Author; kept it unchanged |
| [Clarified DEC-014](https://github.com/BentWorks/DF_AI/discussions/1#discussioncomment-19134233) | [Accepted 2026-10-28](https://github.com/BentWorks/DF_AI/discussions/1#discussioncomment-19252526) | [Accepted 2026-10-22](https://github.com/BentWorks/DF_AI/discussions/1#discussioncomment-19134516) | Author |
| Conclude now, without wider review | Chosen 2026-10-29, given directly to AI Collaborator Claude in a working session | — | — |

**Reviewers:** the maintainer, AI Collaborator Claude and AI Collaborator Codex.
No independent human technical reviewer took part. Under DEC-014, a material new
objection reopens the affected decision.

## Decided

DEC-001 to DEC-014 in the [decision log](DECISION-LOG.md) are decided. They are
architecture and process decisions only.

## Not decided

**Gameplay feasibility is untested.** Q-01 to Q-05 and Q-07 to Q-10 in
[open-questions.md](../open-questions.md) are still open, and each needs a live
test on a pinned DF/DFHack version.

## Next

The first task is **Q-09 plus a reuse audit**:
1. Pin an exact DF and DFHack pair, along with a dfhack-mcp revision.
2. Map R2's required operations to what the tools support, and list the gaps.
3. Define the prepared-save G0 fixture.
