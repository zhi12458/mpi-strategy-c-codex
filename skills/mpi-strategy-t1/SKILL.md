---
name: mpi-strategy-t1
description: Compatibility router and locked provider runtime for MPI T1. Use when the user explicitly requests T1-OMP, needs T1 installation or repair, validates historical T1.0/T1.1/T1.2 artifacts, or invokes $mpi-strategy-t1. Ordinary MPI Chinese-to-English Buddhist document translation now routes to the separate mpi-strategy-t1-codex production Skill.
---

# MPI T1 Compatibility Runtime

The selected quality-first production default is the separate
`mpi-strategy-t1-codex` Skill. This package remains the locked OMP/provider
runtime, T1-OMP rollback implementation, installer, and compatibility layer for
historical T1 artifacts and isolated pretranslation experiments.

For an ordinary MPI Chinese-to-English Buddhist book, article, or document,
load the sibling `mpi-strategy-t1-codex` Skill and follow its production lock.
If it is missing, report the missing package; do not silently run T1-OMP while
retaining the T1-Codex or default-T1 label.

Use this Skill directly for:

- explicit T1-OMP translation or rollback;
- base runtime installation, repair, readiness, credentials, or public smoke;
- historical T1.0.1, T1.1.1, or T1.1.2 validation;
- explicitly requested T1.2 human-quality or AI-scale pretranslation pilots;
- bounded blinded comparisons against T1-Codex.

Read [references/production-lock.json](references/production-lock.json) for
routing and status. Read [references/installation.md](references/installation.md)
and [references/readiness.md](references/readiness.md) for runtime work. Read
[references/workflow.md](references/workflow.md) for rollback and compatibility
execution. Read [references/pretranslation-tracks.md](references/pretranslation-tracks.md)
only for an explicitly selected pretranslation experiment, and
[references/semantic-bridge.md](references/semantic-bridge.md) for historical
T1.1 validation.

## Boundaries

- `source.dj` is always the sole semantic authority.
- T1-OMP prose is a rollback or comparison artifact, not an automatic source
  of sentences for T1-Codex. Never merge the two drafts without an explicit,
  source-checked editorial decision.
- The base runtime retains Flash/high, Sol/high, and Pro/max selectors for
  stable T1-OMP execution and public smoke. In the default T1-Codex workflow,
  OMP must not execute Codex-owned drafting, adjudication, title, or concision
  roles.
- T1.1.2 full-document Sol restructuring and T1.2 full pretranslation remain
  isolated experiments. The default T1-Codex workflow adopts only high-risk
  source-bound clarification, fresh Pro challenge, exact constraint coverage,
  and post-concision semantic regression.
- A runtime `READY.json`, mechanical QA, model review, or strategy adoption does
  not approve a document. Every final target remains an `AI reviewed draft`
  until a named Buddhist/Dharma human approves its exact hash.
