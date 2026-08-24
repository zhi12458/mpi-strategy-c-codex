# T1.0.1 document workflow

T1 is the production form of the validated C+ workflow. Execute these stages
in order for books, articles, transcripts shaped into publication prose, and
other Chinese-English Buddhist documents.

## 1. Intake and authorization

- Identify the sole authoritative Chinese source, genre, audience, voice,
  reference-only material, delivery format, and named human decision points.
- Treat English material marked reference-only as terminology, style, or
  layout guidance; never use it as source authority.
- Record whether external semantic analysis and review are authorized. Ask for
  explicit consent before the first external transmission of private content.

## 2. Source and project freeze

- Preserve the original file and raw extraction.
- Produce `source.dj` without changing Chinese meaning, numbering, or physical
  line history. Document any removal of purely decorative image lines.
- Create `translation-project.yaml` with genre, audience, register, delivery,
  external-review policy, and release status.
- Record SHA-256 for the source and project metadata.

## 3. Terminology and fixed-expression evidence

- Load the repository's `mpi-terms-search` guidance and search project terms
  in priority order: DoT final, internal project terms, Buddhist terminology,
  then scripture titles.
- Query titles, names, quotations, idioms, proverbs, culturally fixed
  expressions, and wordplay as well as Buddhist technical terms.
- If the internal termbase has no result, credible sources conflict, or the
  correct sense or English wording remains in substantive doubt, read and
  execute
  [network-terminology-verification.md](network-terminology-verification.md).
  Authoritative web verification and its receipt are mandatory before the term
  may be frozen.
- Freeze `term-map.yaml` and retain query receipts. Mark unresolved wording for
  human choice instead of inventing certainty.

## 4. Source-only semantic analysis

- V4 Flash `high` reads frozen Chinese only and produces `source-analysis.json`.
- Cover every nonblank source line. For each paragraph preserve semantic head,
  roles and references, negation, degree, time/aspect, conditions, logic,
  quotation scope, ellipsis, humor, allusions, and must-not-invent constraints.
- Validate coverage, schema, source hash, provider/model identity, and receipt.
  An empty result, partial checkpoint, stale schema, or hash mismatch blocks T1.

## 5. Full independent translation

- GPT-5.6-Sol `high` reads the frozen Chinese, project metadata, term map,
  source analysis, and accepted accuracy decisions, but no competing English.
- Translate the entire document into `target-draft.dj`. Preserve physical-line
  and blank-line parity, headings, anchors, links, emphasis, digits, quotation
  boundaries, first-person presence, questions, reasoning, imagery, and the
  teacher's voice.
- Run a translator-owned whole-document accuracy and fluency self-review.

## 6. Independent bilingual review round one

- V4 Pro `max` reads Chinese, the complete draft, term map, and project
  metadata, but not Flash analysis or competing translations.
- Review the entire document for accuracy, completeness, doctrine, terminology,
  title/heading fidelity, readability, register, and structure.
- Emit supported critical, major, minor, discussion, and human-choice findings.

## 7. Translator adjudication and application

- Sol `high` verifies every finding against Chinese and records accepted,
  partly accepted, rejected, and deferred items with reasons.
- Apply valid findings across the whole document. Regenerate the bilingual file
  and rerun structural QA.

## 8. Independent bilingual review round two

- A fresh V4 Pro `max` review repeats the full bilingual inspection on the
  revised target. Do not limit it to changed lines.
- Sol `high` verifies and applies supported findings. Critical or major
  disagreements remain explicit human decisions; never average them away.

## 9. Independent title and heading audit

- Sol `high` separately checks the main title, TOC, every body heading, and
  every title callback for semantic head, modifier scope, path/purpose relation,
  parallel distinctions, concision, and exact repeated-heading identity.
- Do not add generic formal wrappers absent from the Chinese.

## 10. Independent concision and naturalness pass

- Sol `high` reads the complete reviewed target and Chinese. Remove duplicated
  framing, abstract carrier phrases, support-verb constructions, stacked
  qualifications, and unnecessary near-synonyms. Prefer plain concrete verbs.
- Preserve negation, degree, conditions, logic, quantities, quotations,
  doctrinal distinctions, speaker presence, and cadence. Do not impose a word
  target or reward deletion by itself.
- Recheck the entire Chinese after concision and freeze `target.dj`.

## 11. Deterministic QA

- Regenerate `bilingual.dj` from `source.dj` and final `target.dj`; never edit
  the bilingual output by hand.
- Run the repository checker for nonempty inputs, line and blank-line parity,
  paragraph and heading parity, repeated headings, emphasis, comments, digits,
  terminology, punctuation, CJK leakage, and bilingual freshness.
- Investigate warnings; mechanical pass does not prove semantic or stylistic
  approval.

## 12. DOCX and visual QA

- When DOCX delivery is requested, generate canonical English and bilingual
  files from the frozen final text.
- Verify ZIP integrity and text fidelity, render every page, and inspect all
  pages for clipping, overlap, font failure, broken headings, tables, page
  breaks, missing Chinese, and truncation.
- For media-bearing formats, preserve every audio/video asset byte-for-byte and
  verify relationships and SHA-256; otherwise stop rather than claim T1
  completion.

## 13. Manifest and handoff

- Write a manifest containing T1 version, actual toolkit and termbase hashes,
  model identities and efforts, source/target/deliverable hashes, review and QA
  receipts, unresolved human choices, and final status.
- `AI reviewed draft`: all T1 AI, mechanical, and visual gates complete.
- `human approved`: a named human Buddhist/Dharma reviewer has approved this
  exact target hash and all open decisions.
- `release-ready`: human approval plus final delivery hashes and package QA.

## Required artifacts

At minimum retain the original source, `source.dj`, `translation-project.yaml`,
`term-map.yaml`, internal term receipts, required
`external-lookup-receipts.jsonl`, unresolved-term decisions,
`source-analysis.json`, `target-draft.dj`, both review rounds and application
logs, title-audit record, concision record, `target.dj`, regenerated
`bilingual.dj`, QA reports, delivery files, visual-QA record, and final
manifest.
