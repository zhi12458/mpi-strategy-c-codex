---
name: mpi-strategy-t1-codex
description: Default MPI production and post-translation editing workflow for Chinese-to-English Buddhist books, articles, and documents. Use automatically for ordinary MPI Buddhist document translation, existing bilingual manuscripts that need T1-Codex native-English editing, and explicit T1-Codex requests. Current Codex owns drafting and English editing; locked Flash/Pro roles provide independent source and review gates. Explicit C, M, M2, media-specific, or non-Buddhist requests override it.
---

# MPI T1-Codex Production Strategy

Package revision `codex-model-flex-1` (1.2.0 candidate.2) permits user-selected
GPT-5.6/GPT-6 Codex roles. Workflow quality gates remain 1.2.0.

T1-Codex 1.2.0 is the selected quality-first production default. It preserves
the human-adopted C+ quality chain and incorporates only the risk-reducing parts
of the T1.1 line: source-bound high-risk semantic clarification, independent
Chinese challenge, exact constraint coverage, and post-concision bidirectional
semantic regression. It also adds a full-document Chinese semantic-segmentation
stage between source analysis and English drafting so that clauses, subjects,
references, and logical relations are explicit before translation.
It also provides a resumable post-translation entry for an existing bilingual
manuscript. That entry reuses exact-hash upstream evidence and does not repeat
the complete translation or bilingual-review chain merely to perform native-
English editing.

Current Codex, using GPT-5.6 or GPT-6 at a runtime-supported reasoning level, owns the full
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
Read
[references/english-only-reader-gate.md](references/english-only-reader-gate.md)
before preparing, running, adjudicating, or validating either English-only
reader round.
Read
[references/chinese-semantic-segmentation.md](references/chinese-semantic-segmentation.md)
before creating, reviewing, validating, or delivering the Chinese semantic-
segmentation artifacts.
Read
[references/post-translation-editing.md](references/post-translation-editing.md)
when editing an existing Chinese-English manuscript or running the required
post-translation native-English stage of a new T1-Codex document.

For publication-facing Buddhist translation or revision, read
[references/semantic-style-native-reader-addendum.md](references/semantic-style-native-reader-addendum.md)
before drafting or editing, and execute its final checks after the core
workflow. Source authority, material-change decisions, and post-edit semantic
regression remain mandatory. This editorial revision is
`semantic-style-native-readers-1`; it does not refresh runtime readiness.

## Verb-led English integration

Local editorial revision `verb-led-english-1` merges the 1.1.1-local.1 rules
into the newer 1.2.0 workflow without downgrading it or changing runtime locks.
Use source-supported finite verbs for action/process meanings, with accuracy
and emphasis taking priority. The existing concision role performs the
**Independent action-verb, concision, and naturalness pass** (stage 14 here;
stage 13 in the earlier workflow), followed by stage 15 semantic regression.
Every execution must produce `verb-led-style-review.jsonl`, including decisions
to retain flagged sentences; the existing editing record must state the checked
draft SHA-256, whole-document completion and issue count. For zero issues,
retain an empty JSONL and explicitly record “已完成，零问题”. Follow the addendum’s
seven-field schema and material-change approval rules. Both English-only reader
roles and subsequent full Chinese/bilingual regression include verb-led risks;
no review round, model role, external authorization, or release approval changes.

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
- After source analysis and bridge decisions, Codex must produce
  complete source-bound Chinese semantic segmentation before drafting English.
  It may split overloaded sentences, repeat a uniquely recoverable referent,
  make an implicit subject explicit, and expose an already-supported logical
  relation. It must not add a proposition, agency, causality, obligation,
  evaluation, or person shift.
- Adding `我们` is allowed only when the original Chinese already includes the
  speaker and audience in that proposition. If that inclusion is not uniquely
  supported, retain the ambiguity, mark the item `review_required`, and require
  a recorded commissioner decision before English drafting.
- A fresh Pro/max Chinese-only session must review every changed segmentation
  record against `source.dj`. The translator receives both files, resolves any
  conflict in favor of `source.dj`, and may not draft from the segmentation
  alone. Retain and deliver the human-readable segmentation result alongside
  the final translation.
- Use the user-selected GPT-5.6 or GPT-6 Codex model at any reasoning level
  supported by that runtime; do not force Sol or high. Record the actual model,
  effort, and session identity. Follow `codex_model_policy` in the production
  lock; model permission does not replace document review or human approval.
- The provider runtime is `deepseek-only-v1`: OMP runs Flash/high and Pro/max,
  while GPT drafting/editing runs in the current Codex task. No OMP OpenAI
  login, Personal/Business confirmation, or GPT smoke is required.
- Install with `python scripts/install_runtime.py --base-skill-dir <immutable-base>`.
  Authorize public tests interactively or with `--confirm-public-smoke`.
  Revalidation adds `--revalidate-existing`; it does not replace repositories.
  Use the separate `MPI_STRATEGY_T1_CODEX_ROOT` managed root and schema-2
  `T1_CODEX_RUNTIME_READY.json`. This proves only the DeepSeek provider runtime;
  verify the current Codex identity separately before any production claim.
  Never read or relabel legacy T1 `READY.json` as proof of this profile.
- Preserve the frozen base package. Reuse only its verified repository, doctor,
  credential, fault-injection, mechanical/DOCX and DS public smoke helpers.
  Missing locks, dependencies, credential or checks mean `BLOCKED`.
  Static package validation alone is not runtime readiness.
- Two fresh Pro/max bilingual reviews remain blind to source analysis, bridge
  artifacts, competing translations, and each other. Codex adjudicates every
  finding against the original Chinese and records its disposition.
- Titles and headings receive an independent accuracy pass. Concision is a
  separate full-document pass followed by a complete original-Chinese recheck
  and a fresh Pro/max bidirectional semantic-regression gate.
- After that regression, two mutually isolated English-only readers---a
  general nonfiction editor and an English Buddhist/Dharma editor---must read
  the target as original English. They receive only a readable English-only
  manuscript generated from and hash-bound to the current target; raw Djot with
  Chinese anchors is forbidden. They remain blind to Chinese, terminology, old
  translations, bilingual material, prior feedback, the translator context,
  and each other.
- Codex checks every reader suggestion against the complete original Chinese.
  Meaning-neutral grammar, punctuation, collocation, repetition, passive-voice,
  and uniquely recoverable referent repairs may be applied after that check.
  Changes affecting doctrine, meaning or degree, terminology, voice, metaphor,
  numbers, person relation, information coverage, sentence or paragraph
  structure, quotation wording, or explanatory Chinese-cultural translation
  require commissioner selection from documented options and fidelity
  tradeoffs before application.
- Human comments must be assessed individually, distilled into source-supported
  reusable editing principles, and followed by a full-document search for the
  same problem. Human preference never overrides the Chinese or pre-approves a
  future document.
- After approved reader-driven edits, rerun a complete Chinese review,
  full-document bidirectional semantic regression, and both English-only
  readers in fresh isolated sessions. Both final readers must report zero
  blockers and zero unresolved actionable findings, with zero unapproved
  omission, addition, or sensitive change.
- Full-document controlled-Chinese rewriting, T1.1.2 Sol restructuring, and the
  T1.2 human/AI pretranslation tracks are optional isolated experiments. They
  never enter the default workflow without explicit user selection and their
  own comparison evidence. The mandatory segmentation stage is narrower: it
  clarifies information structure but does not stylistically rewrite, shorten,
  modernize, or replace the Chinese source.
- Regenerate `bilingual.dj` from the final source and target. Run deterministic,
  DOCX text, accessibility, and page-by-page visual QA when applicable.
- In the post-translation delivery profile, the reader-facing Word file contains
  only alternating untouched Chinese and final English paragraphs, including
  titles and headings. Keep incoming English, semantic notes, feedback,
  decisions, comments, tracked changes, and other internal material outside it.
- An existing-translation entry does not silently claim the missing upstream
  T1-Codex stages. If the baseline lacks exact-hash production receipts, label
  the result `T1-Codex post-edit AI-reviewed draft` and disclose the missing
  evidence rather than rerunning it without instruction.
- A completed run is an `AI reviewed draft`. A named Buddhist/Dharma human must
  approve the exact final target hash before `human approved` or release-ready
  status is allowed. Missing or stale English-only reader evidence is
  `T1-Codex blocked`, not a completed draft.

## Fallback and transition

Use T1-OMP 1.0.1 only as an explicitly recorded rollback or blinded comparison
track when the Codex role is unavailable, a production gate fails, or the user
requests it. Never silently merge OMP and Codex prose or downgrade the default
while retaining the T1-Codex label.

The package lock currently remains release-candidate evidence until its public
smoke and multi-genre human validation program are complete. Report the exact
last completed stage rather than overstating readiness.
