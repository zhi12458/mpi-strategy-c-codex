# T1-Codex 1.1 document workflow

Execute the stages in order for MPI Chinese-to-English Buddhist books,
articles, and documents. The current Codex task owns English. Locked OMP is
used only for the independent Flash/high and Pro/max roles named below.

## 1. Intake and authorization

- Identify the sole Chinese source, genre, audience, teacher voice, reference-
  only material, delivery format, and named human decision points.
- Record whether external source analysis and review are authorized. Private
  text requires explicit consent before first transmission.
- Confirm that the Codex task is GPT-5.6-Sol with high reasoning. If the task
  setting cannot be verified, stop the production label rather than guessing.

## 2. Source and project freeze

- Preserve the original file and raw extraction.
- Produce `source.dj` without changing meaning, numbering, or physical-line
  history. Record justified removal of decorative-only lines.
- Freeze `translation-project.yaml`, source SHA-256, genre, audience, register,
  external-review policy, delivery scope, and release status.
- `source.dj` remains the sole semantic authority through final handoff.

## 3. Terminology and fixed-expression evidence

- Search the MPI termbase in priority order: DoT final, internal project terms,
  Buddhist terminology, then scripture titles.
- Include titles, names, quotations, idioms, proverbs, classical expressions,
  culturally fixed expressions, and wordplay.
- When the internal termbase has no usable result, sources conflict, or wording
  remains substantively uncertain, follow
  [network-terminology-verification.md](network-terminology-verification.md).
- Freeze `term-map.yaml` and receipts. Unresolved core doctrine, titles,
  quotations, or names require a named human decision or block drafting.

## 4. Complete source-only semantic analysis

- Flash/high reads frozen Chinese source-side inputs and no English.
- Cover every nonblank line. Preserve semantic head, roles and references,
  negation, degree, time/aspect, conditions, logic and scope, quotation scope,
  ellipsis, humor, allusions, ambiguity, and must-not-invent constraints.
- Validate schema, full coverage, source hashes, actual model/effort, and the
  provider receipt. Partial, empty, stale, or malformed output is a failed
  stage, not evidence.

## 5. High-risk semantic bridge

- Flash/high classifies every nonblank source unit as high-risk, low-risk, or
  structural in `semantic-risk-register.jsonl`.
- Generate `semantic-bridge.jsonl` only for high-risk units. Each record may
  clarify implicit Chinese meaning and describe an English sentence plan in
  Chinese; it must not contain English prose or modify `source.dj`.
- Bind each bridge record and protected constraint to exact source evidence and
  hashes. Clear and low-risk lines receive no rewritten Chinese.

## 6. Fresh Chinese-only bridge challenge

- A new Pro/max session reads frozen Chinese, project metadata, term evidence,
  risk records, and bridge records, but no English draft, source analysis, or
  competing interpretation.
- Agreed high-confidence constraints may be frozen. Disagreement, low
  confidence, doctrine, titles, quotations, names, and other core ambiguity
  require a named human decision or an explicit source-evidenced provisional
  decision that blocks human-approved/release-ready status.
- Validate decisions before English drafting. Never average model disagreement.

## 7. Codex translation and self-review

- The current GPT-5.6-Sol/high Codex task reads `source.dj`, metadata, term map,
  source analysis, accepted bridge decisions, and no competing English.
- Translate the complete document into `target-draft.dj`. Preserve line and
  blank-line parity, headings, anchors, links, emphasis, digits, quotations,
  questions, reasoning, imagery, first-person presence, and teacher voice.
- Perform a translator-owned full-document accuracy, completeness, terminology,
  fluency, register, and structure review against the original Chinese.
- Write `constraint-coverage.jsonl`, mapping every frozen high-risk constraint
  to an exact target line and exact English span.

## 8. Fresh bilingual review round one

- A new Pro/max session reads the complete original Chinese, current English,
  term map, and metadata.
- It must not read source analysis, bridge artifacts, Codex self-review,
  competing translations, or future findings.
- Review the entire document for accuracy, completeness, doctrine, terminology,
  roles/reference, logic/scope, title/headings, naturalness, register, voice,
  and structure.

## 9. Codex round-one adjudication

- Codex verifies every finding against `source.dj` and records accepted, partly
  accepted, rejected, deferred, and human-choice decisions with reasons.
- Apply all supported findings across the full target. Regenerate the bilingual
  file and rerun structural QA.

## 10. Fresh bilingual review round two

- Use a different Pro/max session. It reads the complete revised bilingual text
  but not round one, source analysis, bridge artifacts, or Codex adjudication.
- Review the full document rather than changed lines only. Critical or major
  disagreement remains an explicit human decision and blocks silent completion.

## 11. Codex round-two adjudication

- Codex verifies and applies supported findings against the original Chinese.
- Regenerate bilingual text and rerun full structural and terminology QA.

## 12. Independent title and heading audit

- Codex separately checks the main title, TOC, every body heading, and every
  callback for semantic head, modifier scope, purpose/path relation, parallel
  distinctions, concision, and exact repeated-heading identity.
- Do not add generic formal wrappers absent from the Chinese.

## 13. Independent concision and naturalness pass

- Codex removes duplicated framing, abstract carrier phrases, support-verb
  constructions, stacked qualifications, unnecessary near-synonyms, and
  academic nominalization. Prefer plain, concrete verbs.
- Recheck the entire original Chinese afterward. Preserve negation, degree,
  conditions, logic, quantities, quotations, doctrinal distinctions, speaker
  presence, questions, cadence, and titles. Do not use a deletion quota.
- Freeze `target.dj` only after this complete Chinese recheck.

## 14. Fresh post-concision semantic regression

- A new Pro/max session reads frozen Chinese, final `target.dj`, term evidence,
  and accepted high-risk decisions, but no prior English or findings.
- Verify both directions for every high-risk unit: each Chinese proposition and
  qualification appears in English, and every English assertion is supported
  by Chinese.
- Unsupported additions, failed constraints, or unresolved critical/major
  findings block completion. Refresh constraint coverage after final repairs.

## 15. Deterministic and delivery QA

- Regenerate `bilingual.dj`; never edit it by hand.
- Check nonempty inputs, physical and blank-line parity, paragraph and heading
  parity, repeated headings, anchors, emphasis, comments, digits, terminology,
  punctuation, CJK leakage, placeholders, and bilingual freshness.
- When DOCX is requested, generate canonical English and bilingual files,
  verify ZIP/text/accessibility, render every page, and inspect every page for
  clipping, overlap, font failure, broken headings/tables, missing Chinese, or
  truncation.

## 16. Manifest and handoff

- Record actual task/provider/model/effort identities; source, term, bridge,
  target, and deliverable hashes; all review and QA receipts; failed attempts;
  unresolved choices; and final status.
- `AI reviewed draft` means all AI, semantic, mechanical, and visual gates
  passed. `human approved` requires a named Buddhist/Dharma reviewer to approve
  the exact final target hash. Release-ready additionally requires package and
  production-validation gates.

## Required artifacts

Retain the original source, `source.dj`, metadata, `term-map.yaml`, term
receipts, `source-analysis.json`, risk register, bridge, bridge review and
decisions, `target-draft.dj`, constraint coverage, both bilingual reviews and
Codex adjudication logs, title and concision records, final `target.dj`,
regenerated `bilingual.dj`, semantic regression, deterministic/DOCX/visual QA,
delivery files, human approval state, and final manifest.
