# DF_AI design record

This folder is the project's organized record of what has been proposed,
agreed, disputed and tested. The [discussion board](https://github.com/BentWorks/DF_AI/discussions)
is where the debate happens. This folder is where its results are written down.

## Contents

| File | What it holds |
|---|---|
| [decisions/DECISION-LOG.md](decisions/DECISION-LOG.md) | Every design decision, with its status and links to the discussion. |
| [open-questions.md](open-questions.md) | Unresolved specification gaps and the experiments that would settle them. |
| [proposals/](proposals/) | Consolidated proposals and the reviews of each one. The current one is [R2](proposals/R2.md). |
| [research/](research/) | Evidence gathered from documentation and prior art, kept separate from decisions. |
| [RECORD-CHANGES.md](RECORD-CHANGES.md) | A dated list of every change to these records, so participants can see what moved. |

## Status vocabulary

These statuses are used everywhere in this folder. They keep different kinds of
agreement apart.

| Status | Meaning |
|---|---|
| **Proposed** | Someone has suggested it. No one has agreed yet. |
| **Under review** | It is in a consolidated proposal awaiting explicit replies. |
| **AI-agreed** | AI Collaborator Claude and AI Collaborator Codex have both explicitly agreed. This is **not** maintainer approval. |
| **Accepted** | The maintainer has explicitly accepted it, along with participating reviewers. Only this counts as consensus. |
| **Disputed** | At least one participant has objected, and the objection is unresolved. |
| **Superseded** | A later decision replaced it. A link points to the replacement. |

Separately, every claim about game behavior carries an evidence label:

- **Verified** means it was tested on a pinned DF/DFHack version, with a link to the report.
- **Documented** means it comes from official docs or a project's README, but has not been tested here.
- **Assumed** means no source has been found yet.

Silence never counts as agreement. Comments signed by an AI collaborator are
posted through the owner's account, but they are not the owner's approval.

## Who is participating

- **Maintainer:** the repository owner (BentWorks).
- **AI Collaborator Claude:** signed comments with the marker `dfai-claude-collaborator`.
- **AI Collaborator Codex:** signed comments with the marker `dfai-codex-collaborator`.
- **Other developers** are welcome. See [CONTRIBUTING.md](../CONTRIBUTING.md).
