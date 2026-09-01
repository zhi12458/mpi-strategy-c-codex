# Post-translation native-English editing

Use this route when a complete Chinese source and existing English translation
already exist. It is an editing add-on, not a request to translate the document
again. For a new full T1-Codex run, this route is the post-translation portion
of stages 16--20 in `workflow.md`. For an older manuscript, it is a resumable
entry point that avoids rerunning source analysis, English drafting, or the two
bilingual reviews unless the user explicitly requests that work.

`source.dj` remains the sole semantic authority. Natural English is necessary,
but it never licenses omission, addition, stronger or weaker meaning, or a
different teacher voice.

## Entry and evidence reuse

1. Preserve the incoming Chinese, existing English, and any bilingual or Word
   file. Record source and baseline-target SHA-256 values in
   `post-edit-baseline.json`.
2. Inventory existing T1-Codex receipts. Reuse an artifact only when its source
   and target hashes, scope, model identity, and completion status match the
   current inputs exactly. Do not rerun an upstream stage merely to make the
   post-edit record look complete.
3. If the baseline already completed the full T1-Codex gates, retain that
   provenance. If upstream evidence is missing or stale, continue only as a
   `T1-Codex post-edit AI-reviewed draft`; do not claim that the full production
   workflow has been completed.
4. Editing must occur on a derived target. Preserve the incoming target and
   record every final hash transition.

The intake receipt is fail-closed. In addition to `schema_version`,
`workflow_version`, `mode`, `source_sha256`, `baseline_target_sha256`,
`baseline_target_preserved`, `full_translation_rerun`,
`bilingual_reviews_rerun`, `upstream_t1_codex_evidence_complete`, and
`claimed_status`, retain `upstream_reuse_receipts`. It must contain exactly the
full-workflow inheritance stages locked in `production-lock.json`, once each.
For every upstream artifact relied on by a full-workflow claim, record:

- its stable `stage`;
- the project-relative `artifact` name and `artifact_sha256` recomputed from
  that actual file;
- `source_sha256` and `baseline_target_sha256` equal to the exact post-edit
  intake hashes;
- `scope: full_document` and `status: PASS`;
- `role_or_tool_identity_matches_recorded_configuration: true`, after checking
  the original provider/model/role/request receipt or deterministic tool
  configuration as applicable;
- `reused_without_rerun: true`.

The indexed artifact itself must be a JSON completion receipt with
`schema_version: 1`, `gate: t1_codex_upstream_completion`, the same `stage`,
exact source and baseline-target hashes, `scope: full_document`, `status: PASS`,
`complete: true`, and `execution_identity`. Model stages must contain the
locked provider, model, reasoning effort, role, and a nonempty request or
session ID. Deterministic QA must contain a tool name, version, and
command/configuration hash. The validator opens this inner receipt and compares
it with the lock; hashing an arbitrary file is not reusable evidence.

Do not infer validity from a filename, timestamp, summary, or nearby receipt.
An expected stage omitted from the receipts, a missing artifact, a missing or
mismatched artifact hash, an internal source/target mismatch, incomplete scope,
unacceptable completion status, or unprovable model identity makes that
artifact non-reusable and forces
`upstream_t1_codex_evidence_complete: false`. Record the gap and continue under
the downgraded status; do not call a provider or rerun translation or bilingual
review merely to fill the index.

## Source-only Chinese semantic map

Before judging the English, read the complete Chinese without using the English
to reverse-engineer its meaning. Reuse an exact-source-hash validated
`chinese-semantic-segmentation` record when available. Otherwise create the
internal `post-edit-chinese-semantic-map.jsonl`, one record per substantive
paragraph, containing:

- propositions and their order;
- subjects or experiencers, actions or states, objects, recipients, and results;
- omitted subjects, referents, modifier scope, and quotation scope;
- causal, additive, progressive, contrastive, sequential, conditional, and
  purposive relations;
- protected person, negation, degree, quantity, modality, time, doctrine,
  terminology, imagery, numbers, and teacher voice;
- ambiguities and decisions that require the commissioner.

This is an internal understanding aid. It need not rewrite the Chinese and must
not appear in the final reader-facing Word file. Add `我们` only when the source
uniquely includes both speaker and audience. Engagement or smoother English is
not source evidence; otherwise preserve the ambiguity and route the person
choice to the commissioner.

Bind the semantic-map receipt inside `post-edit-baseline.json` to the actual
artifact with `kind`, project-relative `artifact`, `artifact_sha256`,
`source_sha256`, `full_document_scope`, and
`existing_english_visible: false`, plus one visible-input source hash, a session
ID, and prompt hash. Recompute `artifact_sha256` from the file;
do not accept a self-declared hash inside the map as proof. A missing, empty,
stale, hash-mismatched, partial-document, or English-informed map fails closed.
That failure does not authorize a model rerun: either create the source-only map
within the authorized post-edit work or stop with the gap recorded.

For a new `post-edit-chinese-semantic-map.jsonl`, retain exactly one ordered
record for every nonblank physical source line. Each record binds the full
source and line hashes, exact `source_text`, line number and `paragraph_id`,
declares the source-only visibility boundary, and records structural versus
substantive status. A substantive record has one or more propositions whose
evidence is a literal span of that exact source line, plus semantic roles,
logical relations, protected constraints, ambiguities, and closure status.
Structural anchors have no propositions. For a reused pre-draft segmentation,
run the complete segmentation and independent-review validator instead of
accepting its filename or outer hash alone.

A `safe` map record has no unresolved ambiguity and may not add `我们` when the
literal source line lacks it. A record with ambiguity or a source-absent `我们`
must be `commissioner_resolved` and point to a project-relative, SHA-256-bound
JSON decision artifact. That artifact records a named commissioner, decision
ID, exact source and line hashes, paragraph ID, every ambiguity ID, literal
source evidence, and the selected resolution; an added `我们` also requires
`person_scope_approved: true`. Whenever the map uses `我们`, retain literal
person-scope evidence and explicitly confirm that the source uniquely includes
speaker and audience. An unresolved `commissioner_required` status never
passes the post-edit gate.

## Human feedback and transferable learning

When translators or editors provide Google Docs comments, Word comments, or
other human feedback:

1. read and assess every item against the Chinese;
2. distinguish a local wording preference from a reusable editing principle;
3. record accepted principles and their evidence in
   `human-feedback-learning.json`;
4. scan the complete English manuscript for analogous instances, rather than
   changing only the commented sentence;
5. route doctrine, terminology, meaning, voice, or other sensitive effects to
   commissioner decision.

Human feedback is important evidence, not authority to override `source.dj`.
Record a zero-item receipt when no human feedback was supplied so the absence
is explicit rather than assumed.

## Isolated English readers

Follow [english-only-reader-gate.md](english-only-reader-gate.md). Use two
fresh, mutually isolated readers of the complete rendered English manuscript:

- a general native-English nonfiction reader or editor;
- a native-English reader or editor familiar with ordinary Buddhist concepts
  and English Buddhist writing.

Neither reader sees Chinese, the semantic map, terminology records, bilingual
material, old English, previous feedback, editing history, or the other
reader's output. Readers judge English naturalness; Codex separately determines
Chinese fidelity.

## English standard for a Dharma talk or public article

Prefer plain, concise, immediately understandable spoken-publication prose:

- use common concrete verbs instead of abstract nouns, support-verb phrases,
  stacked nominalizations, or grand but vague wording;
- keep the teacher's direct, warm, grounded authority rather than turning the
  talk into an academic paper;
- flag a sentence that cannot be read aloud comfortably in one breath, but do
  not split or merge it without commissioner approval;
- make openings sound like natural English speech without mechanically carrying
  over Chinese courtesies;
- use `we` only when Chinese person scope supports it;
- render rhetoric and cultural concepts naturally when the meaning survives,
  but treat explanatory cultural translation as a sensitive change;
- do not insert *Dharma* or other Buddhist coloration into an ordinary social
  expression merely to make the prose sound Buddhist.

The general reader checks immediate clarity, collocation, translation-shaped
syntax, abstraction, passives, sentence length, subject tracking, and oral
rhythm. The Buddhist reader checks readable terminology, Dharma register,
possible doctrinal misunderstanding, and whether simplification erases a
Buddhist distinction.

## Editing authority

Codex may directly apply a low-risk English repair only after checking it
against the complete source context. Low-risk categories are:

- unmistakable grammar or punctuation;
- unnatural collocation;
- accidental repetition;
- unnecessary passive voice;
- a uniquely recoverable unclear referent;
- meaning-neutral simplification or ordinary English polishing.

If a referent is not uniquely recoverable, it is not low-risk. The following
are always sensitive and must not enter the target before explicit commissioner
selection:

- Buddhist doctrine or terminology;
- meaning, degree, modality, or evaluative strength;
- author voice or tone;
- metaphor or image;
- numbers;
- person or speaker-audience relation;
- addition or deletion of information;
- sentence split or merge;
- paragraph structure;
- quotation wording;
- explanatory translation of a specific Chinese cultural person, virtue, or
  concept.

Present each sensitive proposal with exactly these substantive fields:
`current_english`, `proposed_english`, `reason`, and `fidelity_effect`, plus its
Chinese location, source evidence, category, and decision status. Do not apply
it until the commissioner records a selection.

## Terminology and fixed expressions

Search the project term record first. Then follow
[network-terminology-verification.md](network-terminology-verification.md),
including same-author and same-institution approved usage, reliable canonical
translations, recognized Buddhist translation institutions, specialist
dictionaries, and academic publications. Compare materially different
tradition-specific renderings and explain the distinction. A core term with no
unique source-supported decision remains a commissioner choice.

Article-specific human decisions belong in a project-local terminology or
decision profile. Do not promote them into the global termbase or silently
reuse them in another article.

## Whole-document closure and final readers

After all commissioner decisions are recorded:

1. apply them throughout the complete target;
2. scan for every analogous wording pattern and check terminology consistency;
3. recheck every paragraph against Chinese, including person, degree, negation,
   conditions, causality, numbers, quotations, names, and titles;
4. verify that concision removed neither information nor qualification and that
   added logic has Chinese support;
5. verify main title, TOC, and repeated body headings independently and make
   repeated English headings identical after numbering and markup are removed;
6. run full bidirectional semantic regression;
7. run both reader roles again in fresh English-only sessions on the final
   target hash.

Low-risk issues found in the final read may be repaired only with the same
source check, and any later edit invalidates both final-reader certificates.
A newly found sensitive issue returns to commissioner decision.

## Final Word profile

The reader-facing final Word file contains only alternating pairs: one untouched
Chinese paragraph followed immediately by its final English paragraph. Apply
the same order to the title, TOC, and every heading. Keep all internal evidence
outside that file, including the incoming English, semantic map, comments,
reader feedback, proposed wording, decisions, and process notes.

Before delivery:

- verify the actual full source/target pair count and order;
- remove comments, tracked changes, placeholders, and internal instructions;
- use fonts that cover Chinese and required Sanskrit/Pali transliteration;
- verify DOCX structure, ZIP integrity, and text fidelity;
- render every page and inspect missing glyphs, boxes, clipping, overlap,
  truncation, abnormal page breaks, and font substitution.

All delivery checks apply to the actual DOCX that will be handed to the user,
not to a prior render, a differently named copy, or a declarative checklist.
In `post-edit-delivery-record.json`, bind the real `final_docx_path` and its
recomputed `final_docx_sha256` to the actual `source.dj` and final `target.dj`
hashes. Derive `actual_pair_count`, alternating order, title/TOC/heading order,
comment and tracked-change absence, text fidelity, font coverage, DOCX
structure, and ZIP integrity from that same hashed file. Render that exact file,
record a nonempty `forbidden_placeholder_strings` list, and retain a
`rendered_pages` entry for every page with its project-relative PNG artifact,
recomputed SHA-256, the exact rendered DOCX hash, and `inspected: true`. Also
retain a hash-bound JSON `render_receipt_artifact` with the renderer and version,
command/configuration hash, timestamps, exit status, exact final DOCX SHA-256,
page count, output format, and the same page artifact/hash index. The validator
opens the actual ZIP,
checks its content types and document XML, rejects comments/tables/tracked
changes, derives the expected visible paragraph sequence from `source.dj` and
`target.dj`, compares it with the actual Word body, and validates every indexed
PNG structure and hash. A missing file, hash mismatch, pair-count mismatch,
render from another DOCX, or fewer inspected pages than rendered pages blocks
delivery; boolean fields alone are not evidence of the underlying check.

The final file remains an `AI reviewed draft` until a named Buddhist/Dharma
human approves its exact target and deliverable hashes.

Retain the unedited baseline as `target-pre-postedit.dj`, the intake and reuse
receipt as `post-edit-baseline.json`, and the final delivery receipt as
`post-edit-delivery-record.json`. Validate the complete retrofit evidence with:

```text
python scripts/validate_post_translation_editing.py /absolute/path/to/project
```

The validator checks provenance, the no-retranslation boundary, source-only
semantic-map receipt, English-reader gate, human-feedback learning, claimed
status, pair-count and clean-delivery receipts, the actual final DOCX path and
recomputed file hash, and page-by-page visual coverage. It validates evidence
consistency, not semantic truth; the production operator must still preserve
the underlying structural, text, font, render, and visual-inspection evidence.
