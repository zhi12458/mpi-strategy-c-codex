---
name: mpi-strategy-t1-codex
description: Default MPI production workflow for Chinese-to-English Buddhist books, articles, and documents. Use automatically for ordinary MPI Buddhist document translation and when the user requests T1-Codex. Current Codex owns drafting and English editing; locked Flash/Pro roles provide independent source and review gates. Explicit C, M, M2, media-specific, or non-Buddhist requests override it.
---

# MPI T1-Codex Production Strategy

T1-Codex 1.1.0 is the selected quality-first production default. It preserves
the human-adopted C+ quality chain and incorporates only the risk-reducing parts
of the T1.1 line: source-bound high-risk semantic clarification, independent
Chinese challenge, exact constraint coverage, and post-concision bidirectional
semantic regression.

Current Codex, configured as GPT-5.6-Sol with high reasoning, owns the full
English draft, review adjudication, title audit, concision, and complete Chinese
recheck. DeepSeek V4 Flash/high and fresh V4 Pro/max sessions remain independent
checks. This is not a Codex-only workflow.

Read [references/workflow.md](references/workflow.md) before translating. Read
[references/production-lock.json](references/production-lock.json) when
checking roles, versions, evidence, routing, or release status. For installation
or readiness work, read [references/installation.md](references/installation.md)
and [references/readiness.md](references/readiness.md). When terminology or a
fixed expression is substantively uncertain, read
[references/network-terminology-verification.md](references/network-terminology-verification.md).

## Non-negotiable boundaries

- Freeze the original input, `source.dj`, project metadata, terminology, and
  hashes before model work. `source.dj` is the sole semantic authority.
- Flash/high performs complete source-only analysis and classifies every
  nonblank unit. It creates a Chinese explanatory bridge and Chinese English-
  structure plan only for high-risk units; it does not draft English or rewrite
  `source.dj`.
- A fresh Pro/max session challenges every high-risk bridge record without
  seeing an English draft. Disagreement, low confidence, doctrine, titles,
  quotations, names, and other core ambiguity remain human-review items or
  block drafting.
- The Codex task must be configured as GPT-5.6-Sol/high and its actual task
  settings recorded. Do not silently substitute another model or effort while
  retaining the production label.
- Two fresh Pro/max bilingual reviews remain blind to source analysis, bridge
  artifacts, competing translations, and each other. Codex adjudicates every
  finding against the original Chinese and records its disposition.
- Titles and headings receive an independent accuracy pass. Concision is a
  separate full-document pass followed by a complete original-Chinese recheck
  and a fresh Pro/max bidirectional semantic-regression gate.
- Full-document controlled-Chinese rewriting, T1.1.2 Sol restructuring, and the
  T1.2 human/AI pretranslation tracks are optional isolated experiments. They
  never enter the default workflow without explicit user selection and their
  own comparison evidence.
- Regenerate `bilingual.dj` from the final source and target. Run deterministic,
  DOCX text, accessibility, and page-by-page visual QA when applicable.
- A completed run is an `AI reviewed draft`. A named Buddhist/Dharma human must
  approve the exact final target hash before `human approved` or release-ready
  status is allowed.

## Fallback and transition

Use T1-OMP 1.0.1 only as an explicitly recorded rollback or blinded comparison
track when the Codex role is unavailable, a production gate fails, or the user
requests it. Never silently merge OMP and Codex prose or downgrade the default
while retaining the T1-Codex label.

The package lock currently remains release-candidate evidence until its public
smoke and multi-genre human validation program are complete. Report the exact
last completed stage rather than overstating readiness.
