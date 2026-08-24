# mpi-strategy-m-codex

Audited installer and Codex skill for MPI M Strategy Chinese-English Buddhist
translation. M 1.0 fixes the model roles as V4 Flash source analysis,
GPT-5.6-Sol Medium drafting/accuracy/concision, two V4 Pro bilingual reviews,
and Sol High targeted fallback after review two only.

The installer delegates all extraction, terminology, Djot, bilingual, DOCX,
subtitle, and mechanical QA work to exact locked compatibility-fork commits:

- `mpi-translations` at `f3e7ad8868954b2dbc9258ef179394a1e26210e9`;
- `translation-toolkit` at `2805cc742100b1bf294780572c2f65a1ab31567a`.

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

## MPI T1 production skill

The T1.0.1 production skill is stored at `skills/mpi-strategy-t1/`. T1 is the
default for MPI Chinese-English Buddhist books, articles, and documents when
the user does not name another strategy. It is the human-adopted production
name for the validated C+ workflow and is not an alias for M, M2, or historical
C. Its source-only analysis, Sol High translation, two independent Pro reviews,
title audit, concision recheck, terminology web-verification gate, QA, and human
release boundary are frozen in the skill's production lock and manifest.
