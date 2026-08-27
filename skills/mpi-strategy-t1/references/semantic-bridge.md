# T1.1.2 lightweight semantic restructuring

The historical reference name is retained so existing links do not break. The
current T1.1.2 capability is not a six-artifact semantic bridge. It adds one
translator-owned model invocation and lightweight substep inside existing Stage
5, but no provider role or top-level workflow stage. Existing T1.1.1 bridge
artifacts remain readable through the explicit legacy validator and are never
rewritten.

`source.dj` remains the sole Chinese authority. Semantic restructuring projects
conclusions already frozen in `source-analysis.json` into Chinese syntax that is
easier to carry into natural English. It must not interpret doctrine again, add
information, or become a replacement Chinese source.

## One artifact, existing owner

For each pilot document, T1.1.2 adds only
`semantic-restructuring.json`. GPT-5.6-Sol at `high`, in its existing
`translation_and_self_review` role, creates it immediately
before drafting English. No extra Flash generation, Pro challenge, semantic
decision, constraint-coverage, or post-concision regression stage is added.

The file is one JSON object with:

- exact SHA-256 bindings for `source.dj`, `translation-project.yaml`,
  `source-analysis.json`, and `term-map.yaml`;
- an optional SHA-256 binding for an explicitly supplied accepted-decisions
  file;
- the total number of nonblank source units in the frozen inventory;
- Sol/high role provenance;
- a source-ordered `records` array containing only lines that materially benefit
  from syntactic restructuring.

An explicit T1.1.2 run must select at least one line; a document with no useful
candidate should stay on the T1.0.1 baseline instead of producing an empty
pilot artifact. The validator accounts for the complete frozen source inventory
by comparing its line IDs with the selected record IDs; this arithmetic does not
prove that the model read every unselected line. The prompt instructs the model
to consider every line, without making it echo a decision or hash for each
unchanged line.

Every selected record binds its physical source line and exact source-analysis
paragraph hash. The model supplies only readable selected-line proposals:
indexed evidence paths or legacy field names, complete evidence scalars, the
permitted operations, a minimal subject decision, typed lexical changes,
`restructured_zh`, and sentence units.
The runner adds the frozen line, field-value, project, analysis, terminology,
and optional decision-file hashes, plus the protected terms found on that line.
If an existing source-analysis paragraph already carries `line_sha256`, it is
verified directly. Older external-v3 analyses remain usable when their global
source hash is exact and their paragraph IDs cover every nonblank source line in
source order; the runner then derives the physical line binding from that frozen
source instead of retrofitting Stage 4.

The locked Stage-4 schema is consumed directly, without asking Flash to write a
restructuring recipe. Evidence paths are restricted to
`predicates[i].participants[j]`, `relations[i]`, and
`references_and_ellipsis[i]`, with canonical nonnegative indexes. The path
family and structured item determine the evidence kind; the model cannot
relabel it. `exact_quote` must equal the item's non-null `evidence` scalar, and
the runner hashes the complete item. Free `notes`, meanings, and scalar
subpaths never authorize a lexical change.

Older external-v3 prose analyses remain a compatibility mode. A few field names
overlap the locked schema, but in legacy mode they must be complete nonempty
top-level string scalars; a
favorable substring cut from longer negative or uncertain context is invalid.
Any list-valued signature, malformed overlapping value, or non-legacy locked
signature selects structured validation and cannot downgrade to prose mode. Locked
structured and legacy prose paragraph shapes or evidence fields may not be
mixed in one analysis. Even exact structured or prose evidence proves traceability, not
doctrinal correctness. The step may not regenerate propositions, ambiguity
options, or `must_preserve` / `must_not_invent` conclusions.

## Authority and translator inputs

The translator must read all five core inputs together:

1. `source.dj` — sole authority for meaning and information;
2. `translation-project.yaml` — frozen genre, audience, register, and delivery
   context, never semantic authority;
3. `source-analysis.json` — frozen roles, references, logic, scope, ambiguity,
   and doctrinal constraints;
4. `term-map.yaml` — frozen term and fixed-expression choices;
5. `semantic-restructuring.json` — non-authoritative syntactic planning aid.

When the project has an explicit accepted-accuracy-decisions file, pass it with
the optional runner flag so it is included in the call receipt. It does not
replace any of the five core inputs.

If the inputs conflict, `source.dj` remains highest authority. An explicit human
decision may choose among readings supported by that source and takes priority
over automated analysis, terminology, or restructuring, but it may not override
the source. Never translate `restructured_zh` in isolation.

## Permitted operations

A record may use only:

- `explicit_subject`: expose a subject explicitly supported by the source;
- `explicit_reference`: replace an overt controlled pronoun or reference form
  with its uniquely supported antecedent; a zero subject must instead use
  `contextual_subject` plus `explicit_subject`, while other zero-reference
  additions are deferred to the bilingual English translation and review;
- `explicit_logic`: preserve or reposition a source-visible cause, condition,
  result, contrast, or progression; a connector absent from the surface Chinese may be
  added only from the approved connector set and an exact indexed relation item
  (or the legacy compatibility gate below), immediately before the complete
  target clause;
- `split_sentence`: divide a long unit without changing proposition scope;
- `reorder`: move complete punctuation-delimited clauses into an
  English-friendly order, never freely swap words inside a clause;
- `parallelism`: clarify members through splitting, punctuation, or clause
  organization. The locked structured schema does not authorize repeating a
  shared lexical constituent; that choice is deferred to the English draft and
  bilingual review. An already-frozen legacy prose analysis may use the narrow
  compatibility gate below;
- `passive_or_impersonal`: avoid inventing an unsupported agent;
- `preserve_ambiguity`: carry forward an ambiguity not resolved upstream.

Do not add explanations, examples, historical background, parenthetical
glosses, inferred reasons, inferred conclusions, or rhetorical strengthening.
Do not weaken or strengthen negation, degree, quantity, modality, conditions,
causality, scope, quotations, questions, first-person presence, or teacher
voice.

## Subject and reference policy

The record preserves the source-analysis evidence status:

- `explicit`: the current source line names the subject or referent;
- `contextual_inference`: a unique antecedent is supported elsewhere in the
  frozen source;
- `ambiguous`: no unique subject or referent is established;
- `not_applicable`: the unit has no subject decision.

When status is `ambiguous`, use a passive, impersonal, or ambiguity-preserving
plan. Do not insert unsupported subjects such as `我们`, `人们`, `大家`,
`修行者`, `僧人`, `作者`, or `法师`. The validator checks the actual
`restructured_zh`, not just subject-strategy metadata.

Every subject or reference decision must cite the exact evidence item that
authorizes it. A locked structured current-line subject binds an explicit
agent, experiencer, or causer participant and is never inserted again. A
contextual subject insertion requires both (1) one `omitted_subject` or
`inherited_subject` item with a unique referent, role, exact context evidence,
and current predicate, and (2) one matching contextual participant item for
the same predicate and role. In the locked Stage-4 contract, that participant is
normally `null` for an omitted subject; subject identity comes from the
reference item, whose sole candidate and canonical referent must both equal the
proposed subject. Both indexed items and their own non-null evidence scalars
must be returned. The paragraph must be `clear`, have no competing
interpretation or unbound item for the same predicate/role slot, and the subject
is inserted exactly once immediately before that predicate, without another
lexical edit or reorder. If any element is absent, mismatched, or ambiguous, use
a passive, impersonal, or ambiguity-preserving plan.

Controlled reference replacement accepts only one overt controlled reference
form bound to a `coreference` item with a unique earlier referent, matching
status, predicate, role, and exact evidence. The form must be the unique maximal
controlled form on the line and is replaced once in place; a substring such as
`他` inside `他们` cannot be selected. It cannot be declared as an
addition: this prevents a zero subject from bypassing `subject_strategy` and
prevents an omitted object or other ellipsis from being filled without a
mechanically verifiable grammatical role. Legacy prose subject/reference
evidence retains the complete-scalar local positive-role gate.
`sentence_units_zh` must concatenate back to the complete restructured text
(ignoring whitespace only). The English draft is then audited against this
record and the original Chinese.

A typed logic addition is narrower than a fresh interpretation. For locked
structured analysis, one indexed `relations[i]` item must have `clear`
paragraph status, no competing interpretation, a non-ambiguous status, and the
only eligible relation for that clause pair. Its `source_clause` and
`target_clause` must be the unique, adjacent, complete punctuation-delimited
clauses in the current line, in that order; its exact evidence must equal the
continuous source span covering both clauses. The fixed mapping is condition ->
`则`, cause or result -> `因此`, contrast -> `但`, and progression -> `进而`.
Any other relation on the same unordered clause pair, a pre-existing logic
marker anywhere in the target clause, or an incomplete, repeated, non-adjacent,
or reversed span defers instead of adding text.
The pre-existing-marker gate is common to structured and legacy evidence and
recognizes ordinary members of the same connector families, including `而`,
`那么`, `于是`, `由此`, and `并且`; it therefore cannot produce
stacked forms such as `但而`. Matching ignores spacing, format controls, and
combining or variation marks so invisible Unicode cannot split a connector or
make `他` appear to be a maximal reference inside `他们`. Raw source text and
hashes remain unchanged and authoritative.

Its `basis_zh` must equal the complete lexical span of one later source clause, and
the approved connector must occur at its start in `restructured_zh`. The
record may contain no other lexical change or `reorder` operation.

For legacy prose compatibility only, the bound
complete scalar must quote both that clause and its immediately preceding
source clause, then positively assign both source and target roles. It must be
the whole closed scalar, with no text before or after this form:

`“<prior clause>”<copula><source role>，“<target clause>”<copula><target role>`

Here `<copula>` is `为`, `是`, `作为`, or `充当`; the role labels are the
enumerated source/target labels accepted by the generated contract. The mapping is fixed:
conditional result -> `则`, causal result -> `因此`, contrast -> `但`, and
progression -> `进而`. Only `logic_and_scope` or `relations` may authorize this
addition. The connector is therefore a deterministic syntactic projection of
the frozen relation, not a new source-analysis conclusion. A negated,
uncertain, interrogative, hypothetical, alternative, contradictory, merely
parallel, directionless, or extra prose statement anywhere in that scalar
blocks the addition.

A locked structured `relations` or `references_and_ellipsis` item does not
encode a shared constituent, later member, insertion basis, and scope together.
It therefore cannot authorize lexical parallel completion. Conservation-safe
punctuation, splitting, and complete-clause reordering remain available.

For legacy prose compatibility only, a typed parallel completion repeats the
exact `restructured_zh` constituent,
which must already occur in the current source. Its separate `basis_zh` is the
unique span in a later parallel member immediately before which the shared
constituent is restored. The same complete roles/ellipsis scalar must directly
quote both spans inside this closed affirmative form:

`[<series count/type>；]<later member>“<basis>”[承前]<省略/共用/共享>“<shared>”，[可/可以/应/应当]在“<basis>”前<补/补出/加/恢复>“<shared>”`

The bracketed portions are the contract's narrowly enumerated optional forms;
the scalar may contain no text before or after the template. Unrelated quoted
occurrences cannot authorize a substring insertion. Any
negation, uncertainty, question, hypothesis, alternative, or contradictory
scope statement in that scalar blocks it. The repeated constituent cannot equal a complete source clause, and
parallel completion cannot be combined with a different lexical operation or
`reorder`. These restrictions keep punctuation-only organization available
while preventing a free prose expansion.

These closed forms are accepted only from already-frozen legacy prose. Stage 4
is not changed to author them. If legacy evidence does not already match the
whole template, omit the lexical addition and leave the issue to the English
draft and bilingual review.

Legacy contextual-subject insertion has the same conservative status. Its
complete top-level scalar must match one of these whole closed forms, with no
text before or after it:

`<subject><承接前文/承前>，<为/是>“<predicate>”[的]省略主语`

`“<predicate>”[的]省略主语<为/是>“<subject>”，<承接前文/承前>`

The named antecedent must occur earlier in the frozen source, and the subject is
inserted once immediately before that unique predicate. Any extra, uncertain,
negative, or competing prose defers the insertion.

## Terminology and fidelity checks

Protected terms are not chosen freely by the restructuring model. The validator
derives required Chinese keys that occur on the source line from the frozen
term map, and also protects the configured Buddhist core set when present:
`空`, `无自性`, `缘起`, `受`, `心`, `心所`, `能缘`, and `所缘`.
Every required term appears in runner-derived `protected_terms` and must occur
verbatim with the same count in the source and restructured Chinese.

The validator blocks mechanically demonstrable drift:

- stale core-input, line, analysis-record, evidence-field, or accepted-decision
  hashes;
- missing, duplicated, or out-of-order selected records;
- evidence quotes absent from their named frozen source-analysis fields;
- untyped additions, omissions, or substitutions across Unicode letters,
  marks, numbers, and symbols;
- arbitrary within-clause reordering, unsupported subject/reference insertion,
  and whole-clause duplication;
- changed protected-term counts, visible negation, limitation, quantity,
  modality, or paired logic markers;
- changed digits, URLs, Latin or Sanskrit tokens, quotation/question/emphasis
  delimiters, brackets, or Markdown markers;
- sentence units that do not reconstruct `restructured_zh`.

This mechanical pass does not prove proposition completeness, doctrinal
equivalence, the correctness of an inferred logical relation, the scope of a
shared parallel constituent, title quality, English fluency, or that the model
actually attended to every unselected line. Those remain gates in the
translator's full bilingual self-review, the two independent Pro/max bilingual
reviews, the title audit, and the post-concision full Chinese recheck.

## Length diagnostic

The validator compares normalized Chinese-character counts. 90%--115% is an
inspection band only. Going outside it produces a non-blocking warning; it
never proves expansion and never excuses one.

## Locked execution and validation

Use the specialized Stage 5 runners. They are the supported path that actually
passes the four frozen core inputs to the restructuring call and all five core
inputs to the translation call:

```sh
python scripts/strategy_t1.py run-semantic-restructuring \
  --project /absolute/project

python scripts/strategy_t1.py run-translation-with-restructuring \
  --project /absolute/project
```

The first call passes `source.dj`, `translation-project.yaml`,
`source-analysis.json`, `term-map.yaml`, and a generated exact response contract
to the existing Sol/high role. The runner deterministically binds the selected
records to the frozen hashes, validates the assembled artifact, and only then
publishes it. The second validates that artifact, then passes the original
source, project metadata, and all three aids to the same role. Both return
receipts containing exact input and output hashes. Default outputs are
`semantic-restructuring.json` and `target-draft.dj`; neither command overwrites
an existing path. Preserve the JSON command response as the model receipt.

To pass an existing human or translator decision file, add
`--accepted-decisions /absolute/accepted-decisions.json` to either specialized
command. The runner hashes it, verifies that it did not change during the call,
and records it in the receipt.

Validate an already retained artifact with:

```sh
python scripts/strategy_t1.py validate-semantic-restructuring \
  --project /absolute/project
```

If the artifact binds an accepted-decisions file, add the same
`--accepted-decisions` path here to verify that binding rather than only its hash
shape.

For an existing T1.1.1 six-artifact project, use:

```sh
python scripts/strategy_t1.py validate-legacy-semantic-artifacts \
  --project /absolute/project
```
