# Open questions

Each question names the experiment or specification work that would close it.
As of 2026-10-29, only Q-06 is resolved. Its rule was accepted as DEC-011. Every other question still needs a live test.

| ID | Question | How it closes | Blocks |
|---|---|---|---|
| Q-01 | Can world generation and embark run unattended on the pinned version? | Run the lifecycle spike in [R1 A2](proposals/R1.md#a2-a-lifecycle-feasibility-gate-for-the-v1-boundary). Ten runs pass or fail. | DEC-006 |
| Q-02 | Can the controller distinguish its own pause from a DF auto-pause, a modal, an autosave or human input? | Run the G0 interrupt test on a disposable save. | DEC-005 |
| Q-03 | Can a save be confirmed as durable, and can its identity be checked on reload? | Run a checkpoint test that confirms the file landed and that a reload matches the expected save. | DEC-004, DEC-005 |
| Q-04 | Do dfhack-mcp's actuators behave safely when wrapped, under retries and timeouts? | Run a wrapper test that forces a timeout mid-apply and checks that reconciliation prevents duplicates. | DEC-002, DEC-003 |
| Q-05 | Do dfhack-mcp observations match the game? | Compare `stocks()` and similar sensors with the in-game screens. | DEC-002 |
| Q-06 | Which goal/loss precedence rule applies? | **Resolved:** accepted as DEC-011 on 2026-10-28. | DEC-009 |
| Q-07 | What budget numbers should G1 use? | Use G0 latency measurements, then propose numbers. | DEC-007 |
| Q-08 | Should construction, event cursors and time control go upstream to dfhack-mcp or stay in DF_AI? | Open an issue with the dfhack-mcp maintainer once the gaps are confirmed. | DEC-002 |
| Q-10 | Does save and reload work reliably, with a verified identity for the loaded session? | Run the save/reload gate from R2 A2. | DEC-012 |
| Q-09 | Which DF/DFHack version pair is pinned? | Install it, record the exact versions, and run a sensor self-test. | Everything |
