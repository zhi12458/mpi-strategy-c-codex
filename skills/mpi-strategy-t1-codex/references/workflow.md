# T1-Codex 1.2.0 document workflow

Execute the stages in order for MPI Chinese-to-English Buddhist books,
articles, and documents. The current Codex task owns English. Locked OMP is
used only for the independent Flash/high and Pro/max roles named below.

For a complete existing Chinese-English manuscript, read
[post-translation-editing.md](post-translation-editing.md) and use its resumable
entry. Freeze and inventory the existing evidence, then enter the post-
translation stages without rerunning source analysis, English drafting, or the
two bilingual reviews unless the user asks for them. Such a result inherits a
full T1-Codex status only when every reused upstream receipt matches the exact
source and baseline target hashes; otherwise label it `T1-Codex post-edit
AI-reviewed draft` and state the missing upstream evidence.

For publication-facing prose, also execute
[semantic-style-native-reader-addendum.md](semantic-style-native-reader-addendum.md).
Read it at intake, not only after English has been drafted. Its genre-specific
voice guidance does not turn scholarly or canonical commentary into public-talk
prose.

## 1. Intake and authorization

- Before English drafting, establish `style-and-voice.md` as specified in the
  addendum and bind it to the frozen source hash at stage 2.
- Identify the sole Chinese source, genre, audience, teacher voice, reference-
  only material, delivery format, and named human decision points.
- Record whether external source analysis and review are authorized. Private
  text requires explicit consent before first transmission.
- Confirm the selected GPT-5.6 or GPT-6 Codex model and reasoning level are
  supported by the runtime; record actual values. If the task
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

## 7. Chinese semantic segmentation and review

- Read and follow
  [chinese-semantic-segmentation.md](chinese-semantic-segmentation.md).
- Codex reads the frozen original, complete source analysis, term
  evidence, and accepted bridge decisions. For every nonblank source line, it
  records the propositions, semantic roles, referents, modifier scope, logic,
  and protected constraints, then produces a clearer Chinese segmentation.
- Split only at existing semantic boundaries. Add only uniquely recoverable
  subjects or referents. Do not introduce a proposition, agency, causality,
  obligation, evaluation, person shift, or stronger condition.
- `我们` may be added only when the original proposition already includes both
  speaker and audience. Otherwise retain the ambiguity and require a recorded
  commissioner decision; reader engagement alone is not source evidence.
- Retain `chinese-semantic-segmentation.jsonl` and line-parallel
  `chinese-semantic-segmentation.dj`. A fresh Pro/max Chinese-only session
  reviews every changed record against `source.dj`; it sees no English draft.
- Validate draft and review receipts. Any omission, addition, unresolved
  subject/person choice, failed record, or source/line hash mismatch blocks
  English drafting.

## 8. Codex translation and self-review

- The current Codex task reads `source.dj`, metadata, term map,
  source analysis, accepted bridge decisions, the approved Chinese semantic
  segmentation, and no competing English. `source.dj` wins any conflict; the
  segmentation may clarify structure but is not a replacement source.
- Translate the complete document into `target-draft.dj`. Preserve line and
  blank-line parity, headings, anchors, links, emphasis, digits, quotations,
  questions, reasoning, imagery, first-person presence, and teacher voice.
- Reconstruct complete meanings and pragmatic functions in idiomatic English;
  do not draft by word substitution. Check agents, referents, abstract noun
  actions, logical connectors, metaphor mechanics, and argument rhythm. Chinese
  segmentation boundaries do not prescribe English sentence boundaries.
- Perform a translator-owned full-document accuracy, completeness, terminology,
  fluency, register, and structure review against the original Chinese.
- Write `constraint-coverage.jsonl`, mapping every frozen high-risk constraint
  to an exact target line and exact English span.

## 9. Fresh bilingual review round one

- A new Pro/max session reads the complete original Chinese, current English,
  term map, and metadata.
- It must not read source analysis, bridge artifacts, Codex self-review,
  competing translations, or future findings.
- Review the entire document for accuracy, completeness, doctrine, terminology,
  roles/reference, logic/scope, title/headings, naturalness, register, voice,
  and structure.

## 10. Codex round-one adjudication

- Codex verifies every finding against `source.dj` and records accepted, partly
  accepted, rejected, deferred, and human-choice decisions with reasons.
- Apply all supported findings across the full target. Regenerate the bilingual
  file and rerun structural QA.

## 11. Fresh bilingual review round two

- Use a different Pro/max session. It reads the complete revised bilingual text
  but not round one, source analysis, bridge artifacts, or Codex adjudication.
- Review the full document rather than changed lines only. Critical or major
  disagreement remains an explicit human decision and blocks silent completion.

## 12. Codex round-two adjudication

- Codex verifies and applies supported findings against the original Chinese.
- Regenerate bilingual text and rerun full structural and terminology QA.

## 13. Independent title and heading audit

- Codex separately checks the main title, TOC, every body heading, and every
  callback for semantic head, modifier scope, purpose/path relation, parallel
  distinctions, concision, and exact repeated-heading identity.
- Do not add generic formal wrappers absent from the Chinese.

## 14. Independent concision and naturalness pass

- Codex removes duplicated framing, abstract carrier phrases, support-verb
  constructions, stacked qualifications, unnecessary near-synonyms, and
  academic nominalization. Prefer plain, concrete verbs.
- Recheck the entire original Chinese afterward. Preserve negation, degree,
  conditions, logic, quantities, quotations, doctrinal distinctions, speaker
  presence, questions, cadence, and titles. Do not use a deletion quota.
- Judge sentences by clear hierarchy, modifier scope and natural pauses, with
  varied lengths. No word-count, short-sentence or one-breath quality target.
  Preserve purposeful repetition. Retain the addendum's read-aloud record and
  apply the existing commissioner gate to material editing changes.
- Freeze `target.dj` only after this complete Chinese recheck.

## 15. Fresh post-concision semantic regression

- A new Pro/max session reads frozen Chinese, final `target.dj`, term evidence,
  and accepted high-risk decisions, but no prior English or findings.
- Verify both directions for every high-risk unit: each Chinese proposition and
  qualification appears in English, and every English assertion is supported
  by Chinese.
- Unsupported additions, failed constraints, or unresolved critical/major
  findings block completion. Refresh constraint coverage after final repairs.

## 16. Initial English-only reader gate

- Read and follow
  [post-translation-editing.md](post-translation-editing.md) and
  [english-only-reader-gate.md](english-only-reader-gate.md). Create two fresh,
  mutually isolated sessions: a general native-English nonfiction editor and a
  native-English Buddhist/Dharma editor.
- Give each reader exactly one readable English-only manuscript, generated from
  and hash-bound to the current target. Retain that exact reader-visible file
  and verify that it contains no Chinese; do not expose raw Djot with Chinese
  anchors or conversion markup. Do not expose terminology, old translations,
  competing drafts, bilingual files, semantic artifacts, translator notes,
  prior feedback, or the other reader's output.
- Each reader treats the translation as original English and checks the whole
  document for translation-shaped prose, collocation, nominalization,
  repetition, rhythm, teacher voice, readable Dharma terminology, and paragraph
  density. For Dharma talks, also check natural spoken openings, concrete verbs,
  read-aloud logical structure and rhythm, unnecessary passives, and needless Buddhist
  coloration in ordinary expressions. Readers report findings and blockers but
  do not edit the target.

## 17. Source-based reader adjudication and commissioner choice

- Codex checks every reader suggestion against the complete `source.dj` and
  records its disposition, risk class, source evidence, and fidelity rationale.
- Apply low-risk grammar, punctuation, collocation, repetition, unnecessary
  passive-voice, uniquely recoverable referent, and meaning-neutral simplification
  repairs only when the complete Chinese check proves that they preserve meaning.
- Before applying a change that affects doctrine, meaning or degree,
  terminology, author voice, metaphor, numbers, person relation, information
  addition/deletion, sentence split/merge, paragraph structure, quotation
  wording, or an explanatory translation of a Chinese cultural person or
  concept, give the commissioner `current_english`, `proposed_english`,
  `reason`, and `fidelity_effect`, plus source evidence. Apply only the recorded
  selection. Unresolved or unapproved sensitive changes block.
- When human comments were supplied, assess every comment, extract only
  source-supported reusable principles, and search the whole target for
  analogous instances before binding the revised target hash.

## 18. Mandatory post-reader Chinese and semantic rerun

- Recheck the entire revised target line by line against the complete original
  Chinese; do not review changed lines only.
- Run a new full-document bidirectional semantic regression: every Chinese
  proposition, qualification, degree, scope, logic, image, number, and voice
  feature must appear in English, and every English assertion must be supported
  by Chinese.
- Any unapproved omission or addition, failed direction, unresolved decision,
  or stale hash blocks completion.

## 19. Fresh English-only final readers

- Run both reader roles again in two new, mutually isolated English-only
  sessions, even if the initial reader round produced no applied change.
- The final sessions see only the current English manuscript and none of the
  initial feedback, adjudication, commissioner decisions, Chinese-side
  evidence, translator context, or each other's output.
- Both final readers must report zero blockers and zero unresolved actionable
  findings on the exact final target hash. Any later target edit invalidates
  both final-reader certificates and requires stages 18 and 19 again.

## 20. Deterministic and delivery QA

- Regenerate `bilingual.dj`; never edit it by hand.
- Check nonempty inputs, physical and blank-line parity, paragraph and heading
  parity, repeated headings, anchors, emphasis, comments, digits, terminology,
  punctuation, CJK leakage, placeholders, and bilingual freshness.
- When DOCX is requested, generate canonical English and bilingual files,
  verify ZIP/text/accessibility, render every page, and inspect every page for
  clipping, overlap, font failure, broken headings/tables, missing Chinese, or
  truncation.
- For the post-translation delivery profile, the final reader-facing Word file
  contains only one untouched Chinese paragraph followed by its final English
  paragraph, including the title, TOC, and headings. Exclude the incoming
  English, semantic-map explanations, proposed changes, feedback, decisions,
  comments, tracked changes, placeholders, and process notes. Verify the actual
  full pair count and font coverage for Chinese and Sanskrit/Pali transliteration.

## 21. Manifest and handoff

- Retain the addendum's final-hash read-aloud record and publication fact and
  quotation checklist, with unresolved publication items and responsible editor.
  Index these records and `style-and-voice.md` by path and SHA-256. They do not
  replace full bilingual review, title audit or named publication approval.
- Record actual task/provider/model/effort identities; source, term, bridge,
  target, and deliverable hashes; all review and QA receipts; failed attempts;
  unresolved choices; and final status.
- `AI reviewed draft` means all AI, semantic, English-reader, mechanical, and
  visual gates passed, both final readers have zero blockers and zero
  unresolved actionable findings, and there is no unapproved omission, addition, or
  sensitive change. `human approved`
  requires a named Buddhist/Dharma reviewer to approve the exact final target
  hash. Release-ready additionally requires package and production-validation
  gates.
- Deliver the human-readable Chinese semantic-segmentation report alongside the
  final translation when the commissioner requested analysis delivery.

## Required artifacts

Retain the original source, `source.dj`, metadata, `term-map.yaml`, term
receipts, `source-analysis.json`, risk register, bridge, bridge review and
decisions, Chinese semantic-segmentation JSONL, line-parallel Djot, independent
segmentation review, requested human-readable segmentation report,
`target-draft.dj`, constraint coverage, both bilingual reviews and Codex
adjudication logs, title and concision records, final `target.dj`,
regenerated `bilingual.dj`, exact initial and final English-only reader-visible
manuscripts, initial general and Dharma reader reports, reader isolation
receipts, reader adjudication, commissioner decisions, post-reader complete
Chinese recheck and bidirectional semantic regression, both final reader
reports, deterministic/DOCX/visual QA, delivery files, human approval state,
and final manifest.

For the resumable post-translation entry, additionally retain
`post-edit-baseline.json`, the exact-hash reused segmentation receipt or
`post-edit-chinese-semantic-map.jsonl`, `human-feedback-learning.json` (including
a zero-feedback receipt when applicable), and the final post-edit delivery
record. Keep them outside the reader-facing Word file.
