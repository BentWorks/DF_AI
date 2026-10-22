# DF_AI

Exploring AI-controlled Dwarf Fortress with a controller that can work with different models and agent harnesses: Claude, Codex, Gemini, local models, or a custom runner.

**Status: concept and research.** This repository contains design documents, not a working implementation. No Dwarf Fortress/DFHack version pair or agent integration has been validated by this project. Code snippets in the documents are sketches, not an installation guide.

The initial target is fortress mode on Linux, starting from a prepared save. The proposed approach uses structured game state and actions through DFHack. Models would choose goals and priorities; ordinary code would validate plans, execute actions, and handle time-sensitive conditions.

## Proposed architecture

```text
External agent harness                 Optional autonomous runner
        |                              (loop, memory, budgets, recovery)
        | MCP or direct interface                |
        +---------------------+------------------+
                              |
                   Shared game controller
              observations, validated actions,
              planning, pause/step, outcome tracking
                              |
                      DFHack integration
                              |
                       Dwarf Fortress
```

Model independence and harness independence are separate goals. The game controller should expose the same typed operations through a direct interface and an MCP adapter. Each client needs its own integration and compatibility check. An optional runner would own unattended execution and use replaceable model adapters; connecting an MCP client alone does not provide that runner.

The design should support one active writer, bounded game advancement, interrupts, and structured action results. A queued building or work order is not a completed task. The controller must track progress and explain blocked work before the agent can plan reliably.

## First experiments

1. **Validate the environment.** Record one exact DF/DFHack version pair, confirm the control channel, and use a disposable test save.
2. **Evaluate existing integrations.** Try a read-only advisor and compare its summaries with the game. Decide what to reuse, extend, or build from the evidence.
3. **Prove control and feedback.** Pause, observe, issue a small validated action, advance a bounded interval, and verify its outcome. Exercise interrupts, retries, missing materials, and restart recovery.
4. **Run a small autonomous scenario.** Complete specified construction and production goals on a prepared fortress, then attempt thirty in-game days before expanding scope.
5. **Compare approaches.** Use the same saved starts and permitted automation for each model and a rules-only baseline. Record survival, reserves, completed work, failures, latency, and compute or API cost.

Success in the early experiments means accurate observations, no overlapping steps or duplicate orders, explicit blocked-task feedback, and recovery without silently losing pending work. Fresh embark automation, combat, and general fortress autonomy come later.

## Prior art and references

- [DFHack](https://github.com/DFHack/dfhack): the proposed game integration foundation.
- [Quickfort documentation](https://dfhack.readthedocs.io/en/latest/docs/tools/quickfort.html): blueprint tooling; investigate Dreamfort for reusable layouts.
- [BenLubar/df-ai](https://github.com/BenLubar/df-ai): prior work on autonomous fortress management.
- [dfhack-mcp](https://github.com/alexanderolvera/dfhack-mcp): an integration candidate to inspect before duplicating work.

These are research references, not claims of current compatibility with this project.

## Documents and discussion

- [Original concept](CONCEPT.md): initial proposal and illustrative code.
- [Evaluation and plan](EVALUATION.md): analysis, candidate approaches, and assumptions to test.
- [Contributing](CONTRIBUTING.md): how to propose experiments and report findings.
- [Feasibility and approaches discussion](https://github.com/BentWorks/DF_AI/discussions/1): feasibility, architecture alternatives, and results.

The older design documents contain unvalidated claims and estimates. Treat them as starting points for investigation; this README describes the project's current status.
