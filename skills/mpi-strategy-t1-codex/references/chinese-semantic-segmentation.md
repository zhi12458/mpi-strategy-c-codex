# Mandatory Chinese semantic segmentation

This stage runs after complete source-only analysis and accepted high-risk
semantic decisions, and before the first English draft. Its purpose is to make
the Chinese information structure explicit without changing what the source
says. `source.dj` remains the sole semantic authority.

## Permitted operations

For every nonblank source paragraph or structural line:

- divide an overloaded sentence at semantic boundaries already present in the
  source;
- identify each proposition and its subject or experiencer, action or state,
  object, result, referent, modifier scope, and logical relation;
- make a uniquely recoverable omitted subject or referent explicit;
- repeat a source-supported noun when a pronoun would otherwise be ambiguous;
- expose a causal, conditional, concessive, contrastive, sequential, or
  purposive relation only when the source already encodes it;
- leave already-clear Chinese unchanged.

Preserve paragraph order, headings, quotations, rhetorical questions, speaker
voice, audience scope, negation, degree, quantity, modality, chronology,
doctrine, terminology, names, numbers, examples, and deliberate imagery.

## Person and subject rule

Do not add a subject merely to make the prose more engaging. In particular,
`我们` may be added only when the proposition already includes both speaker and
audience, as shown by the local clause, a uniquely controlling sentence, or an
unambiguous discourse frame. A generic zero subject, `人们`, an impersonal
claim, or an event is not automatically `我们`.

If more than one subject or person choice is materially plausible:

- keep the ambiguity in the segmented Chinese when possible;
- set `status` to `review_required` or `blocked`;
- record the alternatives and source evidence;
- require commissioner approval before applying `我们` or another person shift.

## Prohibited operations

Do not summarize, beautify, modernize doctrine, improve the author's argument,
delete examples, add reader advice, add intention or obligation, strengthen a
condition, change a statement into a question, change a possibility into a
fact, or replace a Buddhist/classical expression with an ordinary paraphrase.
The segmentation is not a new source, a translation, or a full controlled-
Chinese rewrite.

## Required artifacts

Retain these source-hash-bound artifacts:

- `chinese-semantic-segmentation.jsonl`: one ordered record for every nonblank
  source line, including structural lines;
- `chinese-semantic-segmentation.dj`: readable segmented Chinese with the same
  physical lines and blank positions as `source.dj`;
- `chinese-semantic-segmentation-review.jsonl`: a fresh Pro/max Chinese-only
  review of every changed record;
- `chinese-semantic-segmentation-report.docx` when a human-readable analysis
  deliverable is requested.

Each JSONL record contains `schema_version`, `workflow_version`, source and line
hashes, `source_line`, `paragraph_id`, `source_text`, `meaning_units`,
`segmented_chinese`, `changes`, `protected_constraints`, `risk_items`,
`status`, and `confidence`. Each meaning unit records exact source evidence,
its semantic role structure, and its relation to adjacent units. Every added
subject records the subject text, source basis, person scope, and whether human
confirmation is required.

The report must pair the untouched original with the segmented Chinese, explain
subject/referent choices, list meaning units in logical order, and expose every
review item. It is delivered alongside the final English and bilingual files;
it does not replace either.

## Independent review and translation handoff

A fresh DeepSeek V4 Pro/max Chinese-only session receives `source.dj`, the
candidate segmentation, frozen terminology, and relevant accepted high-risk
decisions, but no English draft or competing translation. It challenges
omission, addition, subject choice, person shift, reference, logic, scope,
negation, degree, quantity, modality, chronology, quotation, and doctrine.

English drafting is blocked until every changed record is approved, corrected,
or carried as an explicit human decision. The translator receives the original
and approved segmentation together, must resolve conflicts in favor of the
original, and must map each English span to the original source line rather
than treating the segmented Chinese as authority.

Run the deterministic receipt validator during drafting and after review:

```text
python scripts/validate_semantic_segmentation.py /absolute/project --stage draft
python scripts/validate_semantic_segmentation.py /absolute/project --stage review
```

The validator proves structure, hashes, coverage, line parity, review closure,
and the special `我们` approval rule. It cannot prove semantic truth; complete
Chinese review and named human approval remain separate gates.
