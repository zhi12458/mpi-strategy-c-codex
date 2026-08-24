---
name: mpi-strategy-t1
description: Default MPI production workflow for Chinese-to-English Buddhist document translation. Use automatically when the user requests such a translation without naming another strategy, and when the user requests T1, T1策略, T1方案, 按T1翻译, 用T1翻译, or invokes $mpi-strategy-t1. Do not override explicit C, M, M2, media-specific, or non-Buddhist translation requests.
---

# MPI T1 Production Strategy

T1.0.1 is the production name for the C+ workflow adopted by the user after
human adjudication. It freezes the production method, not article-specific
wording. Do not import English from the validation article into a new project.

For installation, repair, account setup, or readiness checks, read
[references/installation.md](references/installation.md) and
[references/readiness.md](references/readiness.md). Installing this skill alone
does not establish a production-ready T1 runtime. Require the T1-specific
`READY.json`; never borrow M's managed root, credentials, or receipts.

Read [references/workflow.md](references/workflow.md) before translating. Read
[references/production-lock.json](references/production-lock.json) when
checking model roles, required gates, provenance, or version identity.
When the internal termbase has no answer, sources conflict, or a wording is in
substantive doubt, read
[references/network-terminology-verification.md](references/network-terminology-verification.md)
and complete its auditable authoritative-web lookup before freezing terms.

## Non-negotiable boundaries

- T1 is the default for MPI Chinese-to-English Buddhist books, articles, and
  document translations when the user does not name another strategy. Explicit
  “C策略”, “M策略”, “M2”, or a user-defined workflow overrides this default.
  PPT, audio/video, and non-Buddhist general translation do not implicitly
  route to T1; use their relevant workflow unless T1 is explicitly requested.
- The T1 model roles are fixed: V4 Flash `high` source-only analysis;
  GPT-5.6-Sol `high` full translation, review application, title audit, and
  concision; V4 Pro `max` two independent bilingual reviews. Do not silently
  substitute another model or effort level.
- Obtain explicit consent before sending private source or draft text to an
  external provider. If consent, credentials, or a required model is missing,
  stop T1 and report the blocked stage; do not downgrade the workflow while
  retaining the T1 label.
- OMP must match the version and role selectors in `dependency-lock.json`.
  OpenAI OAuth requires the user's confirmed Personal workspace. The DeepSeek
  key must be entered locally through the masked T1 credential helper; never
  request, display, log, or pass it as a command argument.
- Freeze the Chinese source, project metadata, term map, and their SHA-256
  values before model work. Reuse source analysis only for an exact source hash
  with complete nonblank-line coverage.
- Do not silently resolve an unknown, conflicting, or substantively uncertain
  term. Search authoritative public sources, retain lookup receipts, and send
  unresolved core titles, doctrine, quotations, names, and fixed expressions
  to human judgment. Missing required lookup evidence blocks T1 completion.
- Titles and headings receive an independent accuracy pass. Concision is a
  separate full-document pass after accuracy review and must be followed by a
  Chinese recheck.
- Run deterministic content QA, regenerate the bilingual file from the final
  target, create English and bilingual DOCX deliverables when requested, and
  visually inspect every page.
- T1 workflow completion produces an `AI reviewed draft`. Each new document
  requires its own named human Buddhist/Dharma reviewer before it may be marked
  `human approved` or release-ready. Adoption of T1 does not pre-approve future
  translations.

## Completion rule

Call a run `T1 complete` only when every required stage and receipt in the
workflow reference exists, all critical/major findings are resolved or
explicitly assigned to human judgment, deterministic and visual QA pass, and
the final manifest matches the delivered files. Otherwise report the last
completed stage and use `T1 incomplete` or `T1 blocked`.
