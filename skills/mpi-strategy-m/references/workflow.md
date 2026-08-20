# Audited M document workflow

Use absolute paths. Create each project under the M managed root and preserve
the original input.

1. Run `doctor`, then `begin --input-type document`.
2. Extract `source.dj` with the locked toolkit and freeze project metadata.
3. Build the MPI-backed term map, investigate only uncertain/high-risk terms,
   and receipt `term-decisions.json`. The M-wide fixed terms apply whenever
   present: `济群法师` → `Master Jiqun`; `大道大商` → `Great Path, Great Business`.
4. Run V4 Flash `high` on frozen Chinese before English exists. Reuse an
   earlier source analysis only through `reuse-source-analysis`, which requires
   the exact source SHA-256 and schema v2. Flash must separately record
   `temporal_relations` and `elliptical_subject`. Every time/aspect marker such
   as `时`, `后`, `才`, `已`, `仍`, and `再` must occur verbatim in
   `must_preserve`; compact Buddhist/classical clauses must distinguish agent,
   cause, instrument, and state holder.
5. GPT-5.6-Sol `medium` drafts `sol-draft.dj`; record `sol_translation`, freeze
   it as `target.dj`, and generate `bilingual-round1.dj`.
6. Run V4 Pro `max` as `pro_review_1`, without Flash analysis. It must return
   schema-v2 paragraph audits covering every nonblank source line and separately
   check temporal/aspect, condition, negation, degree, elliptical subject, and
   semantic roles. Record `pro_model_1`.
7. Sol Medium applies only sound accuracy findings to `sol-revised.dj`; record
   `sol_accuracy_revision`, freeze it, and generate `bilingual-round2.dj`.
8. In a separate Sol Medium pass, remove duplicated framing, abstract carrier
   phrases, support-verb constructions, stacked qualifications, unnecessary
   near-synonyms, and avoidable translationese. Recheck Chinese for negation,
   degree, logical relations, quantities, qualifications, Buddhist meaning,
   title distinctions, humor, and each speaker's voice. Record
   `sol_concision`, then freeze `sol-concise.dj` as final `target.dj` and
   regenerate `bilingual.dj`. The pass must not compress away a recorded
   temporal relation or promote a recorded cause/instrument to the English
   subject.
9. Run V4 Pro `max` as `pro_review_2`, again without Flash analysis and with the
   same complete paragraph-audit contract. It must reverse-check “who acts or
   bears the state, and why/by what” for every compressed or elliptical clause.
   If a title,
   critical, or major blocker remains, use Sol `high` only on those findings
   and record `sol_fallback`; otherwise High is forbidden. Stop for human
   judgment if the targeted adjudication remains unresolved.
10. Run strict translation QA, generate English and bilingual DOCX, run DOCX
    fidelity/ZIP QA, and receipt subtitle N/A for document input.
11. Run `finalize`. Deliver source, target, bilingual, both DOCX files, term
    evidence, review artifacts, QA, receipts, and MANIFEST.

The toolkit owns extraction, freezing, bilingual generation, DOCX generation,
and mechanical QA. Codex writes only Sol drafts/revisions and structured model
or audit metadata.
