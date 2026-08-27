# T1.2 isolated pretranslation tracks

These modes are explicit experiments, not the default T1-Codex production
workflow. Each uses the T1-OMP experimental English engine so its controlled-
Chinese variable remains isolated. The mode changes who creates the aid; it
does not change source authority, review independence, title/concision gates,
or final human approval. Never combine either full pretranslation artifact with
the default T1-Codex high-risk bridge unless a new controlled experiment
explicitly authorizes and evaluates that combination.

## Shared inputs and artifact shape

Freeze these files before creating either aid:

- `source.dj`
- `translation-project.yaml`
- `source-analysis.json`
- `term-map.yaml`

`pretranslation.json` covers every nonblank physical source line in order. Each
record binds its `paragraph_id`, original line and SHA-256, meaning ledger,
controlled rewrite, change list, protected constraints, risk items, status, and
confidence. An unchanged clear line has an identical rewrite and an empty
change list. This full inventory preserves the human decision not to edit and
prevents the AI track from measuring activity by rewrite count.

The accepted translation input is `accepted-pretranslation.json`. It is derived
deterministically from the full artifact plus either human approval or Pro
review evidence. Sol must receive the accepted artifact, the original full
artifact, its decision evidence, and all shared source-side inputs; the original
Chinese remains authoritative.

## Human-quality track

The human preprocessor prepares a proposal with the `records` array described
above. Hydrate and bind it without model intervention:

```sh
python scripts/strategy_t1.py hydrate-human-pretranslation \
  --project /absolute/project \
  --proposal /absolute/project/human-pretranslation-proposal.json \
  --generator-name "Named human" \
  --output /absolute/project/pretranslation.json
```

Record approval in `human-pretranslation-approval.json`. It must contain:

- schema/workflow identity and `stage: human_pretranslation_approval`;
- exact `source_sha256` and `pretranslation_sha256`;
- `decision: approved`;
- `consensus`: `single_reviewer`, `unanimous`, or `adjudicated`;
- one or more named `{name, role}` reviewer records.

This evidence authorizes use of the human aid; it does not authorize changing
the original Chinese or mark the future English target human-approved. AI may surface a possible conflict for the final reviewer but must not silently edit,
reject, or replace a human-approved pretranslation.

Resolve the accepted artifact:

```sh
python scripts/strategy_t1.py resolve-pretranslation \
  --project /absolute/project \
  --pretranslation /absolute/project/pretranslation.json \
  --decision-evidence /absolute/project/human-pretranslation-approval.json \
  --output /absolute/project/accepted-pretranslation.json
```

## AI-scale track

Flash/high reads the frozen source-side inputs and returns controlled Chinese,
not English. Its style target is deliberately ambitious: it may split, reorder,
make uniquely recoverable roles explicit, clarify parallel structure, and
remove genuinely redundant carrier wording to approach strong human
pre-editing. The semantic contract remains strict: it must leave unsupported or
ambiguous meaning unchanged and mark risk rather than guess.

The model response uses the sparse `compact-changes-v1` transport. It returns
only rewritten or blocked paragraph IDs; the runner copies every unlisted line
from `source.dj` and deterministically hydrates the full meaning ledger and
protected constraints from the frozen `source-analysis.json`. This avoids
repeating the full source and large analysis objects in one response. Straight
and curly quotation marks use explicit transport tokens and are decoded only
after their identity and order match the source. Every actual rewrite is routed
to Pro review, even when Flash is confident.

Run it with:

```sh
python scripts/strategy_t1.py run-ai-pretranslation \
  --project /absolute/project
```

`safe` changes are accepted. Every `review_required` record is sent, without
the AI drafting rationale or source analysis, to a fresh Pro/max Chinese-only
review. If there are no such records, the runtime records zero model calls and
creates the empty review evidence deterministically.

```sh
python scripts/strategy_t1.py run-ai-pretranslation-review \
  --project /absolute/project

python scripts/strategy_t1.py resolve-pretranslation \
  --project /absolute/project \
  --pretranslation /absolute/project/pretranslation.json \
  --decision-evidence /absolute/project/pretranslation-review.json \
  --output /absolute/project/accepted-pretranslation.json
```

Pro may `accept`, `revert_to_source`, or `block`. A major/critical item cannot
be accepted. `blocked` generation records and all rejected or blocked review
records deterministically use the original line. If a document contains a
concentrated pattern of doctrinal, quotation-attribution, subject/reference,
negation/degree, or logic/scope blocks, stop the AI-scale track and route the
document to human-quality rather than weakening the contract.

## Translation handoff

Both modes use the same runner and the same downstream T1 stages:

```sh
python scripts/strategy_t1.py run-translation-with-pretranslation \
  --project /absolute/project
```

The runner revalidates the original pretranslation, its human or Pro decision
evidence, the accepted artifact, every hash, and target line/blank-line parity.
It refuses existing outputs and any input that changes during the call.

## Human-quality scoring anchor

The final English produced from a human-approved pretranslation plus T1-OMP is
the fixed quality anchor for strategy scoring. Bind the exact source, target,
pretranslation, approval, model and workflow hashes. The anchor is not assigned
an automatic perfect score; reviewers still report any defect in that concrete
target.

Score AI-scale and the unchanged T1.0.1 fallback against the same anonymized
anchor and original Chinese. Human review is primary; model judges are
diagnostic. Evaluate accuracy, roles/reference, logic/scope, Buddhist terms,
teacher voice, naturalness/concision, title/headings, and publication-review
usefulness. Show provenance and colored differences only after blinded scoring.

AI-scale promotion does not require equality with the human anchor. It requires
consistent improvement over the no-pretranslation fallback, no critical/major
final defects, and no recurring Chinese-understanding failure across the three
locked genres. Report its measured gap from the human anchor explicitly.

## Human-to-AI comparison set

Retain source/human pairs, including unchanged records, as the controlled
reference set. Classify changes by subject/reference clarification, sentence
splitting, logic exposure, information order, paragraph structure, teacher
voice, redundancy removal, and title/heading structure. Record counterexamples
where a fluent rewrite changed meaning. Use the set to revise prompts and risk
rules, never to copy article-specific wording into a new translation.

Every prompt or rule revision must rerun the frozen set and compare with the
previous AI version, the unchanged T1 baseline, and the human-quality anchor.

## Call-efficiency policy

- Reuse a validated source analysis only when the source, project metadata,
  term map, model selector, prompt, and workflow hashes match exactly.
- Do not begin with a verbose whole-document response and split only after it
  fails. Use the compact sparse response from the first attempt.
- Treat source analysis as the sole meaning ledger. Pretranslation references
  and hydrates it but does not ask Flash to restate it.
- One AI-pretranslation call and, when changes exist, one Pro challenge are the
  normal budget for a short document. Retry only the failed stage.
- Preserve both bilingual reviews, the title audit, concision pass, and final
  source regression. Call reduction must not merge these quality gates.
