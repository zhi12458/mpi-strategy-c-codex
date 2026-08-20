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
