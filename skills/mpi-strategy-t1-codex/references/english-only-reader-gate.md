# Mandatory English-only reader gate

For a new full T1-Codex run, this gate runs only after Chinese understanding,
both bilingual reviews, title and concision work, the complete Chinese recheck,
and post-concision semantic regression are complete. An existing bilingual
manuscript may instead enter through the retrofit route in
[post-translation-editing.md](post-translation-editing.md): first preserve and
hash the incoming source and target, inventory upstream evidence without
rerunning missing stages, and complete or reuse an exact-source-hash source-only
semantic map. Missing, stale, or unprovable upstream evidence requires the
downgraded status `T1-Codex post-edit AI-reviewed draft`; it must never be
described as completion of the full T1-Codex production workflow. In both
routes, this gate tests whether the translation works as an original English
article. It does not replace source-based review, the final Chinese recheck, or
bidirectional semantic regression.

## Reader isolation

Create two fresh, mutually isolated reader sessions for the initial read and
two more fresh, mutually isolated sessions for the final read:

1. a general English nonfiction editor;
2. an English Buddhist/Dharma editor.

Each session receives exactly one visible manuscript: a readable English-only
rendering of the current target. Do not expose raw Djot if it contains Chinese
anchors or conversion markup that would not appear to a publication reader.
Retain the exact initial and final reader-visible files, their SHA-256 values,
and the SHA-256 of the canonical target from which each was generated. The
reader-visible file must contain no Chinese. It must not expose `source.dj`, the
term map, metadata that reveals source wording, old translations, competing
drafts, bilingual files, bridge or analysis artifacts, translator notes, either
reader's output, or any prior findings or decisions. Use distinct session
identifiers and retain a prompt hash and isolation receipt. The translator role
may not impersonate either reader.

Both readers treat the manuscript as original English prose and inspect the
whole document for:

- translation-shaped syntax or framing;
- unnatural collocation;
- nominalization and abstract carrier phrases;
- avoidable repetition;
- sentence and paragraph rhythm;
- preservation of a teacher's direct, humane voice;
- readability of Buddhist/Dharma terminology for English readers;
- paragraph density;
- natural spoken openings and read-aloud sentence length for Dharma talks;
- unnecessary passives, abstract nouns, and overly academic phrasing;
- Buddhist terminology inserted into an otherwise ordinary expression without
  source or register support.

Findings must cite the English location and wording, explain the reader impact,
offer a concrete option when useful, assign severity, and state whether the
issue is a blocker. Readers do not edit the manuscript.

## Translator adjudication and commissioner decisions

The translator checks every reader suggestion against the complete original
Chinese and records `accept`, `partly_accept`, `reject`, `defer`, or
`commissioner_choice`, with a low-risk/sensitive classification, source
evidence, and a fidelity rationale. Reader preference alone never authorizes a
change. Grammar, punctuation, collocation, accidental repetition, unnecessary
passives, uniquely recoverable referents, and meaning-neutral simplification
may be applied only after that source check. An ambiguous referent is sensitive.

Before applying any proposed change that affects doctrine, meaning or degree,
terminology, author voice or tone, metaphor, numbers, person relation,
information addition/deletion, sentence split/merge, paragraph structure,
quotation wording, or explanatory translation of a Chinese cultural person or
concept, present the commissioner with the existing English, proposed English,
reason, fidelity effect, source evidence, and viable alternatives. Record the
commissioner's decision. An unresolved decision or an applied sensitive change
without recorded approval blocks completion.

When human translator or editor feedback is in scope, assess every item,
separate local wording preferences from reusable source-supported principles,
and scan the complete manuscript for analogous instances. Retain
`human-feedback-learning.json`; a zero-item receipt is valid when no human
feedback was supplied.

## Mandatory rerun after reader-driven editing

After all approved reader-driven edits, bind a new target hash and rerun:

1. a complete line-by-line Chinese review of the whole target;
2. full-document bidirectional semantic regression, checking both Chinese-to-
   English coverage and English-to-Chinese support;
3. the general nonfiction editor final read in a fresh English-only session;
4. the English Buddhist/Dharma editor final read in another fresh English-only
   session.

Run the final reader sessions even when the first readers produced no applied
change. Any target edit invalidates all earlier final-reader certificates.

## Required artifacts and validation

Retain these JSON artifacts, all bound to source or target hashes:

- `english-reader-initial-general.json`
- `english-reader-initial-dharma.json`
- `english-reader-initial-manuscript.txt`
- `english-reader-adjudication.json`
- `commissioner-decisions.json`
- `human-feedback-learning.json`
- `post-reader-chinese-recheck.json`
- `post-reader-semantic-regression.json`
- `english-reader-final-general.json`
- `english-reader-final-dharma.json`
- `english-reader-final-manuscript.txt`

Run:

```text
python scripts/validate_reader_gate.py /absolute/path/to/project
```

The validator checks artifact shape, canonical-target and reader-visible hashes,
absence of Chinese from both reader-visible manuscripts, session separation,
declared input isolation, one adjudication decision for every initial finding,
low-risk/sensitive classification, applied-sensitive-change approval, human-
feedback learning and full-document analogue scan, complete Chinese recheck,
both semantic-regression directions, and zero final reader blockers or
actionable findings. It validates receipts, not the truth of a semantic
judgment; human and bilingual review remain indispensable.

T1-Codex completion is blocked unless both final readers report zero blockers,
all sensitive changes are resolved without unapproved application, and the
post-reader regression reports no unapproved omission or addition.
