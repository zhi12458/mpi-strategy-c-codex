# mpi-strategy-m-codex

Audited installer and Codex skill for MPI M Strategy Chinese-English Buddhist
translation. M 1.0.4 fixes the model roles as V4 Flash source analysis,
GPT-5.6-Sol Medium drafting/accuracy/concision, two V4 Pro bilingual reviews,
and Sol High targeted fallback after review two only.

M 1.0.4 also makes cultural allusions an audited hard gate: Flash enumerates
them, authoritative web evidence is receipted before Sol starts, and Pro checks
their contextual meaning independently. `独善其身` is a release regression.

M 1.0.4 also retains the temporal/aspect, compressed-clause implicit
subjects, semantic-role separation, and per-paragraph Pro audit coverage
machine-enforced release gates.

The installer delegates all extraction, terminology, Djot, bilingual, DOCX,
subtitle, and mechanical QA work to exact locked compatibility-fork commits:

- `mpi-translations` at `fda001ae477d7fbb0a17082c0f338e983d2eb96f`;
- `translation-toolkit` at `b80ceb03c0b076228106c71367478cd93e8fa769`.

M 1.0.4 also closes the fixed-term provenance gap: the locked toolkit now
searches MPI first and accepts explicit, auditable `--fixed-term` arguments,
so release terms such as `济群法师` → `Master Jiqun` are created by toolkit
rather than by an unreceipted edit.

M 1.0.4 bounds long-document Flash requests without reducing semantic
coverage. Each serial batch carries the exact requested text plus three
neighbouring paragraphs on each side, preserves physical blank lines, and
includes only terms present in that window. Every frozen nonblank paragraph is
still analyzed exactly once across the checkpointed run. The full local v3
schema remains the acceptance gate, 8192 completion tokens are reserved, and
empty final content receives at most five unchanged technical retries. Each
batch is generated in four smaller source-only Flash high components—core,
scope, reference, and constraints—then merged by paragraph ID and accepted
only after the complete v3 validator passes.

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
