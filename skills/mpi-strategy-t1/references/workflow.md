# T1 compatibility and rollback workflow

The independent `mpi-strategy-t1-codex` Skill is the selected default for
ordinary MPI Chinese-to-English Buddhist books, articles, and documents. This
package supplies its locked external-provider runtime and retains explicit
T1-OMP rollback and historical experiment support.

## Default routing

For an ordinary in-scope translation:

1. Load `mpi-strategy-t1-codex`.
2. Verify its package and local readiness.
3. Use this base runtime only for the Flash/high and fresh Pro/max roles named
   by the T1-Codex production lock.
4. Do not use this runtime's OMP/Sol translation role during a T1-Codex run.

If the independent Skill is absent or a required gate fails, stop and report
the missing component. Do not silently run T1-OMP under the default label.

## Explicit T1-OMP rollback

Use the following only when the user explicitly requests T1-OMP, the Codex role
is unavailable, a T1-Codex gate fails and the user selects rollback, or a
bounded blinded comparison requires it.

1. Freeze the original input, `source.dj`, metadata, terminology, and hashes.
2. Flash/high performs complete source-only analysis.
3. OMP/GPT-5.6-Sol/high performs full translation and self-review.
4. A fresh Pro/max performs bilingual review round one.
5. OMP/Sol adjudicates and applies supported findings.
6. A different Pro/max performs full bilingual review round two.
7. OMP/Sol adjudicates and applies supported findings.
8. OMP/Sol performs independent title/heading audit.
9. OMP/Sol performs independent concision and full original-Chinese recheck.
10. Regenerate bilingual output; run deterministic, DOCX, accessibility, and
    page-by-page visual QA; record actual roles, receipts, failures, and hashes.

T1-OMP remains an `AI reviewed draft` until target-specific named human
approval. Never merge T1-OMP and T1-Codex prose automatically.

## Historical T1.1 compatibility

Read [semantic-bridge.md](semantic-bridge.md) when validating historical T1.1
artifacts. T1.1.2 full-document Sol semantic restructuring remains an isolated
experiment. The default T1-Codex Skill adopts only:

- source-bound high-risk registration;
- high-risk-only Chinese clarification and structure planning;
- fresh Pro/max Chinese-only challenge;
- constraint-to-final-target coverage;
- fresh post-concision bidirectional semantic regression.

It does not adopt full-document restructuring or controlled Chinese as source
authority.

## Explicit T1.2 pretranslation experiments

Read [pretranslation-tracks.md](pretranslation-tracks.md) only when the user
explicitly selects `human_quality` or `ai_scale`. Keep the experiment isolated
from the default target, retain all source and decision hashes, and compare it
against a same-input control before making any promotion claim.

The pretranslation scripts and contract tests remain available for reproducible
research. Their presence or PASS status does not make them the production
default.

## Lossless OMP execution

- Use one complete existing model stage or bounded coverage segment per OMP
  print-mode call with no saved session and no tools.
- Bind every frozen input represented in the prompt. Refuse existing output,
  input mutation, empty output, invalid JSON, or incomplete coverage.
- Reuse only exact hash-bound artifacts with independent PASS validation.
- Retry only failed segments and preserve every failed receipt.
- Never substitute models/effort, combine independent reviews, reduce coverage,
  remove title/concision/human gates, or count OMP events as model calls.

The base `READY.json` proves only this provider/runtime package. T1-Codex has a
separate package/readiness state, and every document has its own human-release
state.
