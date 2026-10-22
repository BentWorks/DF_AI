# DF_AI — Evaluation and Plan

Companion to `CONCEPT.md`. Written 2026-10-18.

> Design hypotheses and proposed milestones, not implementation results.
> Compatibility, timing, cost, and third-party capability claims require
> verification against the versions used in an experiment. See
> [README.md](README.md) for the current project scope and contribution entrypoint.

## Verdict

The idea appears buildable. DFHack gives structured access, while reliable game
integration and agent behavior still need to be demonstrated. Three things matter most:

1. **The agent should not own the game loop.** A separate runner should own it
   and call the model once per turn with fresh, compact state. If a chat CLI
   drives a long game inside one session, its context fills up and it drifts.
2. **The model should plan and a script should execute.** LLM latency is
   seconds, and a siege moves in ticks. Fast reflexes (alarms, burrows, food
   emergencies) belong in Lua or Python rules. The model sets policy and
   handles the unusual.
3. **The model should never pick raw coordinates.** Give it a site planner
   tool and a blueprint library, and let it choose among valid options.

The proposed AI-agnostic boundary is a shared game-control interface, exposed
through MCP and a direct interface, plus an optional runner. Claude Code,
Codex, Gemini, and custom harnesses are intended frontends; each client's
transport, authentication, and unattended-operation support must be validated.

## Prior art to reuse

- **dfhack-mcp** (npm). This is an MCP server over DFHack's RPC on port 5000.
  It is a read-only fortress advisor with roughly 37 tools, including
  `fort_status()` with pre-triaged alerts, game data and wiki lookups. Write
  tools are opt-in and hidden by default. It already covers the concept's first
  milestone. Try it before writing any sensors, then decide whether to fork it
  or build alongside it.
- **Dreamfort**, in the quickfort library. This is a complete, tested fortress
  blueprint set that goes from embark to a 200-dwarf mountainhome. An agent
  that can sequence Dreamfort phases well has solved most of the layout
  problem on day one.
- **df-ai** by BenLubar. It is useful as a reference for which decisions a
  fortress needs and in what order. It targets pre-v50 DF, so don't plan on
  running it.
- **Terminal and screen-reading attempts.** People have tried driving ASCII
  DF through a terminal MCP, and the grid defeated them. That confirms the
  DFHack-data approach in the concept.

## Corrections to CONCEPT.md

- **The labor tools have changed.** Older autolabor docs say it was not
  updated for v50 and that it disables work details. DFHack 53.16-r2
  reinstated labormanager as a work-detail tool and gave autolabor a
  work-detail mode. Check the changelog for the installed version before
  turning either on.
- **The `advance` tool returns immediately.** It unpauses and returns before
  any game time has passed. It needs to block or poll until the game pauses,
  then report why it paused.
- **DF pauses itself on events** such as sieges, moods, cave-ins and deaths.
  That is useful. Treat each auto-pause as an interrupt that ends the turn
  early with the triggering announcement attached.
- **`dfhack_command` splits on spaces and has no whitelist.** Quoted arguments
  break, and the docstring promises a whitelist that does not exist. Prefer
  typed operations with validated arguments. If a command wrapper is retained
  for development, parsing quoted arguments and checking the first token alone
  does not validate the command's full behavior.
- **Some Lua APIs move between versions.** `dfhack.TranslateName` and the
  stress field path are examples. Pin one DF and DFHack version pair, and add
  a startup self-test that runs every sensor once.
- **Turn speed depends on FPS.** One day is 1200 ticks. At the default FPS cap
  that is about 12 seconds of wall time. Raise the FPS cap and set graphics to
  minimal in the agent profile.

## Recommended architecture

```
        Claude Code / Codex CLI / Gemini CLI / agent-harness / local model
                         │ (interactive: MCP tools directly)
                         │ (autonomous: runner calls model each turn)
                         ▼
   runner ── turn loop, budgets, journal, checkpoints, metrics
     │
     ▼
   dfai core (Python library)
     ├── bridge      dfhack-run subprocess first, protobuf RPC later
     ├── sensors     Lua scripts that return JSON summaries
     ├── actions     validated, whitelisted, dry-run first
     ├── planner     site search, blueprint library, Dreamfort sequencing
     └── reflexes    Lua/Python watchdogs that react within ticks
     │
     ├── MCP server  (thin wrapper, for any MCP client)
     └── harness tools plugin  (thin wrapper, for agent-harness)
     ▼
   Dwarf Fortress + DFHack
```

Put all logic in the core library. The MCP server and the harness plugin
should be thin wrappers, so every frontend gets identical behavior.

### Two ways to run it

- **Interactive.** You open Claude Code or Codex with the MCP server attached.
  You and the model play together. This is good for development and advisor
  mode.
- **Autonomous.** The runner owns the loop. Each turn it pauses the game,
  builds a state packet, calls a model, executes the returned actions, and
  advances. The model can be reached through:
  - agent-harness provider adapters (Anthropic, OpenAI, Ollama). This is the
    most direct route and fits the existing project.
  - headless CLIs, such as `claude -p`, `codex exec` and `gemini -p`, each
    with the MCP config. Authentication, billing, and unattended behavior
    depend on the client and account; validate them before choosing a backend.

### The turn packet

The runner sends the same small structure every turn, so any model can use it:

- Date, season, population, and why the game paused.
- Alerts first: threats, hunger and thirst, stress, deaths, moods, idle count.
- Stock summary as counts against targets, for food, drink, wood, stone,
  bars and cloth.
- Progress on the current plan, such as which Dreamfort phase is done and
  which orders are queued.
- The journal: a short, model-written running plan and lessons learned.
- On request only: an ASCII z-level map, unit details, or item searches.

Aim for 5–15k tokens per turn. Fetch detail through tools, not by default.

## Improvements over the concept

- **Hierarchical cadence.** Run a strategic call each season to set goals,
  a tactical call each day or on interrupt, and continuous reflexes in code.
  This cuts cost and keeps the model out of real-time combat.
- **Event-driven turns.** Advance until N ticks pass or an interrupt fires,
  whichever comes first. Quiet stretches get long turns and crises get short
  ones.
- **Act, then verify.** Every action returns what changed. Use quickfort's
  dry-run or preview mode before placing a blueprint, and confirm the flag
  with `quickfort help`. Report designations placed, jobs created and errors.
- **Checkpoints.** Save with DFHack's `quicksave` before risky actions and on
  a schedule. Checkpoints allow rollback, and they enable fair evaluation.
- **A benchmark mode.** This turns a toy into something worth publishing.
  Start every model from the same embark save, run a fixed number of game
  years, and score the result:

  | Metric | Why |
  |---|---|
  | Years survived | Basic competence |
  | Population and deaths | Safety |
  | Created wealth | Productivity |
  | Average stress | Management quality |
  | Tokens and wall time | Cost |

  Compare supported hosted models and a local model on available hardware,
  recording the model, harness, and automation settings separately.
- **Skip the embark screen.** UI automation is the most fragile part. Start
  from a hand-made embark save and add embark automation later, or never.
- **A chronicle.** Have the model write a short in-character entry for each
  notable event. Optionally pipe major events to the imggen MCP for
  illustrations. This costs little and makes the project fun to watch and
  share.
- **Safety.** Keep raw Lua behind a debug flag. Keep the RPC server on
  localhost only. Cap actions per turn and tokens per run.

## Cost sense-check

One game year has 403,200 ticks, which is 336 days. With daily turns at about
10k tokens each, that is roughly 3–4M input tokens per game year. Prompt
caching of the static rules and tool definitions lowers this a lot. Seasonal
strategy plus interrupt-driven turns can cut the turn count several times
over. A local model avoids per-token hosted API fees, but still uses hardware
and electricity; it is a useful baseline if suitable hardware is available.

## Roadmap

**M0 — Environment (half a day).**
Install DF (Steam) and DFHack. Pin the versions and turn off auto-update.
Confirm that `dfhack-run` works. Make a test embark save. Evaluate a virtual
display such as Xvfb only if the chosen unattended setup requires it.

**M1 — Advisor, using prior art (one evening).**
Install dfhack-mcp and connect it to Claude Code and Codex. Play a human-run
fort with the model as advisor. Note which information was missing or noisy.

**M2 — dfai core and control.**
Build the Python bridge, the summary sensors you found missing, pause and
advance with interrupts, a whitelisted command tool, and quicksave
checkpoints. Wrap them in an MCP server. Test from Claude Code interactively.

**M3 — Planner.**
Add a Dreamfort phase sequencer, site search for open areas and stone, and a
z-level ASCII view. Use dry-run before every placement. The goal is a model
that builds Dreamfort's first few phases without human help.

**M4 — Autonomous runner.**
Build the turn loop, the journal, budgets and the reflex rules. Run it
through agent-harness provider adapters first, then add headless CLI
backends.

**M5 — Benchmark and chronicle.**
Add fixed-seed runs, the scoring table, multi-model comparison and the event
chronicle.

## Risks

- **Spatial reasoning.** This remains the weakest area for current models.
  The planner and blueprint library are the mitigation. Don't try to fix it
  with bigger maps in the prompt.
- **Version drift.** A Steam update can break DFHack for days. Pin versions,
  and run the sensor self-test at startup.
- **Long-horizon drift.** Models forget plans across many turns. The journal
  plus seasonal strategy calls are the mitigation.
- **Wall-clock time.** Model latency multiplied by turn count is slow. A game
  year could take hours. Interrupt-driven turns help the most.

## Sources

- dfhack-mcp: https://github.com/alexanderolvera/dfhack-mcp
- "Teaching an AI to play Dwarf Fortress": https://dev.to/rpmiller/teaching-an-ai-to-play-dwarf-fortress-the-idea-2o6i
- autolabor docs: https://dfhack.readthedocs.io/en/latest/docs/tools/autolabor.html
- labormanager docs: https://dfhack.readthedocs.io/en/stable/docs/tools/labormanager.html
- DFHack 53.16-r2 release: https://newreleases.io/project/github/DFHack/dfhack/release/53.16-r2
- quickfort docs: https://dfhack.readthedocs.io/en/latest/docs/tools/quickfort.html
- quickfort user guide: https://dfhack.readthedocs.io/en/stable/docs/guides/quickfort-user-guide.html
