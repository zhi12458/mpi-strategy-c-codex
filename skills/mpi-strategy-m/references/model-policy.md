# M 1.0.10 model policy

M is a stable workflow contract, not a claim that Sol Medium is universally
better than every model or reasoning level.

- V4 Flash `high`: source-only semantic analysis; exact-source-hash reuse;
  paragraph-level temporal, elliptical-subject, and cultural-allusion gates.
  Long-document requests use an exact three-neighbour local window with
  physical blank lines preserved and relevant term entries only. All frozen
  nonblank paragraphs are covered exactly once across the checkpointed serial
  run. The primary request reserves 8192 completion tokens for thinking plus
  final JSON. If Flash returns empty final content or reaches that limit, the
  next retry keeps Flash `high` and the exact same Chinese/component/schema but
  omits the explicit completion cap, matching the verified C provider envelope.
  Other validation failures remain capped. This changes request recovery, not
  full-document coverage or local v3 validation.
  If all component and single-paragraph retries end in a confirmed transient
  provider failure, the toolkit performs two additional bounded retries of the
  exact same batch. It does not change the model, `high`, Chinese window,
  component, term map, or schema, and existing 1.0.7 batch checkpoints remain
  reusable because their locked request configuration is unchanged.
  Each two-paragraph batch uses seven Flash high components—core, temporal,
  negation/modality, quantity/degree, tense/aspect/other,
  reference/elliptical subject, and allusions/constraints. Time and operator
  components read only the current paragraph; reference keeps a three-neighbour
  window. Toolkit retries only the failed component, merges all components by
  paragraph ID, and accepts only the complete v3 object. The v3 configuration
  schema explicitly accepts both component fallback and completion recovery
  metadata, preventing a valid Flash run from failing during atomic write.
  After the seven independently validated components merge, the toolkit
  deterministically adds each validated temporal marker to the same
  paragraph's `must_preserve` list when absent. This cross-component
  reconciliation does not generate new semantics, change the model or window,
  or emit source text to logs. It runs before the complete v3 full-source
  validator and is recorded in the final artifact configuration. Existing
  1.0.7 and 1.0.8 partial checkpoints remain compatible because the checkpoint
  request configuration is unchanged.
  Audited tool receipts may retain only strict provider-body-free diagnostics:
  an allowlisted error code, component, paragraph ID, retryability, and bounded
  transport or completion counters. Provider bodies and reasoning text remain
  excluded.
  A deterministic final validation failure is also receipted as non-retryable
  structural metadata: a fixed code, paragraph ID, allowlisted schema field
  path, and allowlisted category. The original message, source marker,
  evidence value, source text, provider body, and reasoning remain excluded.
- GPT-5.6-Sol `medium`: full draft, accuracy revision, independent concision.
- V4 Pro `max`: two bilingual reviews, isolated from Flash analysis.
- GPT-5.6-Sol `high`: targeted title/critical/major fallback only after the
  second Pro review reports a blocker.

The Great Path, Great Business M3 experiment supports the independent
concision gate: both blind judges preferred M3 over the accuracy-only M2 draft.
Those pairwise scores do not establish a universal model ranking. Historical
five-way scores predate the final fixed-title policy and must be labelled as
historical evidence.
