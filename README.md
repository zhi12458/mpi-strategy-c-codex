# mpi-strategy-m-codex

Audited installer and Codex skill for MPI M Strategy Chinese-English Buddhist
translation. M 1.0.7 fixes the model roles as V4 Flash source analysis,
GPT-5.6-Sol Medium drafting/accuracy/concision, two V4 Pro bilingual reviews,
and Sol High targeted fallback after review two only.

M 1.0.7 retains cultural allusions as an audited hard gate: Flash enumerates
them, authoritative web evidence is receipted before Sol starts, and Pro checks
their contextual meaning independently. `独善其身` is a release regression.

M 1.0.7 also retains the temporal/aspect, compressed-clause implicit
subjects, semantic-role separation, and per-paragraph Pro audit coverage
machine-enforced release gates.

The installer delegates all extraction, terminology, Djot, bilingual, DOCX,
subtitle, and mechanical QA work to exact locked compatibility-fork commits:

- `mpi-translations` at `bffed8072cc6ff3c066a74abdbb3e142ec60b1ca`;
- `translation-toolkit` at `e083d5b2614b60a1e16bc55a8c22fcd4e67860b0`.

M 1.0.7 retains the fixed-term provenance gate: the locked toolkit
searches MPI first and accepts explicit, auditable `--fixed-term` arguments,
so release terms such as `济群法师` → `Master Jiqun` are created by toolkit
rather than by an unreceipted edit.

M 1.0.7 bounds long-document Flash requests without reducing semantic
coverage. Each serial batch carries the exact requested text plus three
neighbouring paragraphs on each side, preserves physical blank lines, and
includes only terms present in that window. Every frozen nonblank paragraph is
still analyzed exactly once across the checkpointed run. The full local v3
schema remains the acceptance gate, and primary requests reserve 8192
completion tokens. If Flash returns empty final content or reaches that cap,
the next retry keeps Flash `high` and the exact Chinese/component/schema but
omits the explicit cap, matching the verified C provider envelope. Other
validation failures stay capped. Each two-paragraph batch is generated in seven smaller source-only
Flash high components—core, temporal, three bounded operator groups, reference,
and constraints—then merged by paragraph ID and accepted only after the
complete v3 validator passes. Successful components are retained in memory
while only a failed component is retried. If unchanged retries are exhausted,
the locked toolkit retries that component one paragraph at a time and applies
the same schema, evidence, coverage, and full-source validators before the
batch may be checkpointed. M 1.0.7 also adds the previously missing schema
properties for component fallback and completion recovery metadata, so a valid
Flash run cannot fail only when its final artifact is atomically written.

They are verified forks, not official upstream releases. Moving branches are
never followed. Every installation must pass repository verification, both
doctors, disposable fault injection, and a public live smoke before its
M-specific `READY.json` becomes ready.

M is invoked only by explicit wording such as “M方案”, “M策略”, “按M翻译”, or
`$mpi-strategy-m`. Generic translation requests are outside its trigger.

Validation:

```text
python -m pytest -q
python skills/mpi-strategy-m/scripts/strategy_m.py doctor
```

See `INSTALL_PROMPT.zh-CN.md`, `CUSTOMER_PROMPTS.zh-CN.md`, and
`M-vs-C-vs-A.zh-CN.md`.
