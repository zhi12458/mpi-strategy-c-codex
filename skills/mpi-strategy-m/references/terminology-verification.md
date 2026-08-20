# Uncertain terminology verification

MPI terminology remains the first authority. Search in this order:
`DoT定稿`, `内部特色词`, `佛教术语`, then `经论名`. Do not browse every
specialized word. Trigger external research only when an MPI search is missing
or conflicting, the context supports competing senses, the item is a doctrinal
term/title/name/quotation, or a translator or reviewer explicitly marks it
uncertain.

Flash-declared `cultural_allusions` are the exception to the ordinary
"do not browse every term" rule: each declared idiom, proverb, quotation,
allusion, fixed classical expression, or historical reference requires an
external lookup even when MPI has a candidate. This evidence establishes the
source and contextual sense; it does not force a literal or fixed English
idiom.

## Evidence order

1. CBETA for the Chinese canonical context: <https://cbeta.org/>.
2. BDK English Tripitaka and aligned Chinese-English resources:
   <https://www.bdkamerica.org/the-translation-project/>.
3. NTI Reader's Chinese-English Buddhist dictionary and corpus:
   <https://www.ntireader.org/>.
4. 84000's Tibetan-Sanskrit-English glossary as supporting Indic-language
   evidence: <https://84000.co/tools-for-translators>.
5. Academic publishers, universities, and established Buddhist institutions.

Blogs, SEO pages, general encyclopedias, and search snippets may locate a
source but cannot be decisive evidence. Record a short paraphrase and URL; do
not copy long source passages. External usage is evidence, not authority over
the Chinese context or the teacher's intended sense. Author-specific concepts
such as a coined title remain `human_review` when research cannot establish the
semantic head.

## `term-decisions.json`

The file is a JSON object with `schema_version: 1`, the current
`source_sha256`, and an `items` array. Each item contains:

- `source_term`, `locations` (`line` and `source_text_sha256`), `trigger`;
- `candidates`, containing every seriously considered English rendering;
- `mpi_hits` with the MPI `source`, Chinese, English, and location fields;
- `external_evidence` with `source_type`, URL, short support note, and whether
  the evidence was accepted;
- `selected`, `rationale`, `confidence`, `scope`, `resolution_basis`, and
  `status`.

Allowed triggers are `mpi_missing`, `mpi_conflict`, `context_ambiguity`,
`high_risk`, and `model_uncertain`. A frozen decision must be high confidence.
If `resolution_basis` is `mpi_authoritative`, it needs an MPI hit from the
priority list and does not require web evidence. Every other frozen decision
requires admissible external evidence. Unresolved or conflicting items use
`status: human_review` and may not enter the frozen term map.

Run `strategy_m.py record-term-decisions` after creating or updating the file.
When the source changes, recalculate the file-level hash and every affected
line hash. Unchanged context hashes permit individual decisions to be reused;
stale contexts must be researched again. Add each frozen decision to the
project term map with the selected rendering as `preferred`; the recorder and
finalizer reject frozen decisions that are absent or different in the term map.

## Cultural-allusion evidence

For every Flash `cultural_allusions` item, write one or more JSONL records to
`external-lookup-receipts.jsonl`. Each record binds a unique `receipt_id`, the
source and paragraph, exact source SHA-256, query, URL, admissible source type,
title, retrieval time, short support note, captured-content SHA-256, and an
`accepted` boolean. Search snippets may locate a page but the captured evidence
must come from the opened authoritative page.

`allusion-decisions.json` binds the exact source-analysis and lookup-receipt
hashes. It must cover every Flash item exactly once and reference only matching
receipts. Each decision records candidates, the contextual meaning, translation
constraint, selected rendering, rationale, confidence, and status. At least one
matching receipt must be accepted. Use `human_review` when old and modern
senses remain genuinely unresolved. Run `strategy_m.py
record-allusion-decisions` before any Sol translation call.
