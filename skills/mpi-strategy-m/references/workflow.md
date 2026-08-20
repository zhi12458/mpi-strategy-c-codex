# Audited M document workflow

Use absolute paths. Create each project under the M managed root and preserve
the original input.

1. Run `doctor`, then `begin --input-type document`.
2. Extract `source.dj` with the locked toolkit and freeze project metadata.
3. Build the MPI-backed term map, investigate only uncertain/high-risk terms,
   and receipt `term-decisions.json`. Pass every source-present M-wide fixed
   term to the locked toolkit as an explicit `--fixed-term SOURCE=PREFERRED`
   argument so the search and override share one audited receipt. The fixed
   terms are `济群法师` → `Master Jiqun`; `大道大商` → `Great Path, Great Business`.
4. Run V4 Flash `high` on frozen Chinese before English exists. Reuse an
   earlier source analysis only through `reuse-source-analysis`, which requires
   the exact source SHA-256 and schema v3. Flash must separately record
   `temporal_relations` and `elliptical_subject`. Every time/aspect marker such
   as `时`, `后`, `才`, `已`, `仍`, and `再` must occur verbatim in
   `must_preserve`; compact Buddhist/classical clauses must distinguish agent,
   cause, instrument, and state holder.
   Flash must also record `cultural_allusions` for every idiom, proverb,
   classical/canonical/scriptural quotation, fixed classical expression, and
   historical reference. `独善其身` is a release regression and may not be
   omitted.
5. Research every Flash-declared cultural expression using the evidence order
   in `terminology-verification.md`. Write `external-lookup-receipts.jsonl` and
   `allusion-decisions.json`, then run `record-allusion-decisions`. Even when an
   MPI candidate exists, this cultural-expression gate requires at least one
   accepted external source. Missing, stale, duplicated, unrelated, or
   unreferenced evidence blocks the pipeline. Unresolved competing senses stop
   for human judgment.
6. GPT-5.6-Sol `medium` reads frozen Chinese, the term map, Flash analysis, and
   `allusion-decisions.json`, then drafts `sol-draft.dj`; record `sol_translation`, freeze
   it as `target.dj`, and generate `bilingual-round1.dj`.
7. Run V4 Pro `max` as `pro_review_1`, without Flash analysis or allusion
   decisions. It must independently identify the source expressions and return
   schema-v3 paragraph audits covering every nonblank source line and separately
   check temporal/aspect, condition, negation, degree, elliptical subject, and
   cultural allusions and semantic roles. Record `pro_model_1`.
8. Sol Medium applies only sound accuracy findings to `sol-revised.dj`; record
   `sol_accuracy_revision`, freeze it, and generate `bilingual-round2.dj`.
9. In a separate Sol Medium pass, remove duplicated framing, abstract carrier
   phrases, support-verb constructions, stacked qualifications, unnecessary
   near-synonyms, and avoidable translationese. Recheck Chinese for negation,
   degree, logical relations, quantities, qualifications, Buddhist meaning,
   title distinctions, humor, and each speaker's voice. Record
   `sol_concision`, then freeze `sol-concise.dj` as final `target.dj` and
   regenerate `bilingual.dj`. The pass must not compress away a recorded
   temporal relation or promote a recorded cause/instrument to the English
   subject.
10. Run V4 Pro `max` as `pro_review_2`, again without Flash analysis and with the
   same complete paragraph-audit contract. It must reverse-check “who acts or
   bears the state, and why/by what” for every compressed or elliptical clause.
   If a title,
   critical, or major blocker remains, use Sol `high` only on those findings
   and record `sol_fallback`; otherwise High is forbidden. Stop for human
   judgment if the targeted adjudication remains unresolved.
11. Run strict translation QA, generate English and bilingual DOCX, run DOCX
    fidelity/ZIP QA, and receipt subtitle N/A for document input.
12. Run `finalize`. Deliver source, target, bilingual, both DOCX files, term
    evidence, review artifacts, QA, receipts, and MANIFEST.

The toolkit owns extraction, freezing, bilingual generation, DOCX generation,
and mechanical QA. Codex writes only Sol drafts/revisions and structured model
or audit metadata.
