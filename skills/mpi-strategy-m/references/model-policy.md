# M 1.0.4 model policy

M is a stable workflow contract, not a claim that Sol Medium is universally
better than every model or reasoning level.

- V4 Flash `high`: source-only semantic analysis; exact-source-hash reuse;
  paragraph-level temporal, elliptical-subject, and cultural-allusion gates.
  Long-document requests use an exact three-neighbour local window with
  physical blank lines preserved and relevant term entries only. All frozen
  nonblank paragraphs are covered exactly once across the checkpointed serial
  run. 8192 completion tokens are reserved for thinking plus final JSON, and an
  empty final response gets at most five unchanged technical retries. This
  changes request packaging, not full-document coverage or local v3 validation.
  Each batch uses four smaller Flash high components—core predicates/relations,
  time/scope, reference/elliptical subject, and allusions/constraints. Toolkit
  merges them by paragraph ID and accepts only the complete v3 object.
- GPT-5.6-Sol `medium`: full draft, accuracy revision, independent concision.
- V4 Pro `max`: two bilingual reviews, isolated from Flash analysis.
- GPT-5.6-Sol `high`: targeted title/critical/major fallback only after the
  second Pro review reports a blocker.

The Great Path, Great Business M3 experiment supports the independent
concision gate: both blind judges preferred M3 over the accuracy-only M2 draft.
Those pairwise scores do not establish a universal model ranking. Historical
five-way scores predate the final fixed-title policy and must be labelled as
historical evidence.
