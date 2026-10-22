# Contributing

DF_AI is at the concept and research stage. Useful contributions include feasibility checks, reviews of existing projects, small reproducible experiments, and corrections to the design documents.

Start in [developer discussions](https://github.com/BentWorks/DF_AI/discussions/1) for architecture alternatives, integration choices, or proposed experiments. Use issues for a concrete problem or scoped task, and pull requests for reviewable changes. For a substantial implementation, describe the experiment and success criteria before building it.

## Make findings reproducible

Include the relevant details:

- Exact Dwarf Fortress, DFHack, operating system, model, and harness versions.
- Starting save or scenario description, enabled automation, and required configuration.
- Commands or steps, expected behavior, observed behavior, and relevant logs.
- What was verified, what remains an assumption, and links to primary sources.
- For comparisons: the same starting conditions, action permissions, and reported latency, usage, and cost assumptions.

Use a disposable save for write experiments. Remove credentials and private local data from reports; provide game files or saves only when you have permission to share them.

## Design direction

Keep game-control behavior independent of a particular provider or harness. Prefer typed actions, bounded execution, and observable outcomes. Document compatibility limits and failure cases alongside successful runs. Small proofs of observation accuracy, action completion, and recovery are especially useful now.

AI-assisted contributions are welcome. The submitting contributor should review the work and report what was actually tested. Opening a discussion does not start an autonomous agent or background development job.
