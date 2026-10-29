# Test plan

These are concrete tests that close the [open questions](open-questions.md).
Each test names its fixture, its steps and what counts as a pass. Results go in
`docs/research/` and are linked from the question.

**Status key:**
- **Done** means it was run, and results are linked.
- **Partial** means some cases were run.
- **Planned** means not run yet.

| Test | Question | Status |
|---|---|---|
| T-02 Bounded steps and pause attribution | Q-02 | Partial ([G0 probes](research/g0-probes-2026-10-29.md)) |
| T-03 Durable checkpoint | Q-03 | Partial ([G0 probes](research/g0-probes-2026-10-29.md)) |
| T-04 Action retry and reconciliation | Q-04 | Partial ([G0 probes](research/g0-probes-2026-10-29.md)) |
| T-10 Reload a checkpoint without the UI | Q-10 | Planned |
| T-11 Manager and production paths | Q-11 | Planned |
| T-01 World generation and embark | Q-01 | Planned. This needs a non-tutorial setup. |

<a id="t-11-manager-and-production-paths"></a>
## T-11: Nobles, administrators and production paths

**Scope widened on 2026-10-29 at the maintainer's request.** The manager is the
first case. The maintainer noted that nobles and administrators as a whole are a
large part of real play, and that work orders are central for any player, AI or
human.

**Positions on the fixture** (Verified live on 2026-10-29). Of the civilization's 14 fort positions, only the
**expedition leader** is filled. Every other position is vacant. The "what it
unlocks" column is general game knowledge (Documented, not tested here). T-11
should verify each entry as it's reached.

| Position | What it unlocks or affects |
|---|---|
| Manager | Validating and handing out manager (work) orders |
| Bookkeeper | Precise stock records in the game UI. DFHack reads true counts regardless, so record any difference. |
| Broker | Trading at the depot. A caravan forced during the G0 probes arrived with **no broker**, which is a live example. |
| Chief medical dwarf | Hospital and medical care management |
| Militia commander and captain | Squads and military command |
| Sheriff or captain of the guard | Justice: punishing crimes and enforcing mandates |
| Expedition leader, later mayor | Meetings, nobles' demands, the transition as the fort grows |

**Added steps:**

7. **Every position.** For each position above, record how it gets assigned, whether by script, by simulated input, or only by hand. Also record what DF and dfhack-mcp report when it's vacant.
8. **Each unlock.** For the manager, broker and chief medical dwarf, show one before-and-after effect.
9. **Noble demands.** Observe at least one noble demand or mandate, and how it's reported, via `mandates_and_justice` and `nobles_and_administrators`.

### Original T-11: manager and production paths

**Why:** Manager orders, which is what `work_order_create` makes, are only
validated and handed out by an assigned **manager** noble. On the tutorial
fixture no manager was assigned, so a `ConstructBed` order was created, read
back as applied, and stayed `validated: false` and `active: false`. It would
never be worked. The maintainer raised this on 2026-10-29. It's the clearest
example yet of "applied is not done" (DEC-004).

**Background facts** (Documented and Verified):
- **Brewing.** Brewing is a still reaction with two recipes: `BREW_DRINK_FROM_PLANT`, "brew drink", and `BREW_DRINK_FROM_PLANT_GROWTH`, "brew drink from fruit". The player orders the *recipe*. The specific drink depends on which plant the brewer uses, and it can't be ordered by name. Verified from the installed raws.
- **Assigning a manager.** dfhack-mcp 1.4.1 reports `manager_present`. It has a `nobles_and_administrators` sensor, but no tool to assign a position. No DFHack command for assigning positions was found in this install. Verified by listing.
- **The other route.** A workshop's own job queue, which is "add a job at the still", needs no manager. This is the route the maintainer remembers from normal play.

**Steps:** on a disposable fixture, starting with no manager.
1. **Detect.** Create an order and confirm that the controller records it as `applied` with execution status `blocked: no_manager`, not as pending work.
2. **Assign a manager.** Try, in order:
   1. a Lua assignment of the manager position;
   2. simulated UI input on the nobles screen;
   3. the maintainer assigning one by hand, as a control.

   Record which methods work.
3. **Validate.** After assignment, confirm that the existing order becomes `validated: true`, and track it through to completion: the bed exists, and `amount_left` is 0.
4. **Reaction order.** Queue "brew drink" as a manager order through DFHack's `workorder` command, with the reaction name. Then confirm that it validates and produces drink.
5. **Workshop queue fallback.** With the manager removed again, add a brew job directly to a still's queue. Confirm that it runs without a manager.
6. **Blocked reasons.** With the manager present, starve one input at a time: no still, no brewable plants, no empty barrels or pots. Record what the game and dfhack-mcp report for each, so the controller can give typed blocked reasons.

**Pass when:**
- The controller can tell "no manager" apart from other blocks.
- At least one automated way to assign a manager works, or its absence is recorded as a gap that needs a human or upstream work.
- One manager order and one workshop-queue job each complete, with evidence.
- Each starved input produces a distinguishable blocked reason.

**Feeds into:** DEC-012 may need two new operations, `assign_position` and `queue_workshop_job`. Those are proposed in the decision log as DEC-015, pending review.
