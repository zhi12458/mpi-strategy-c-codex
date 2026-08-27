# MPI Strategy Skills for Codex

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

## MPI T1-Codex production skill

The selected default for ordinary MPI Chinese-English Buddhist books, articles,
and documents is stored at `skills/mpi-strategy-t1-codex/`. Current Codex owns
drafting and English editing; locked Flash/high performs source analysis and
high-risk bridge generation, while fresh Pro/max sessions independently
challenge the bridge, run two bilingual reviews, and perform post-concision
semantic regression. `source.dj` remains authoritative and every final target
still requires named Buddhist/Dharma human approval.

The existing `skills/mpi-strategy-t1/` package remains the locked provider
runtime, explicit T1-OMP rollback, installer, and historical T1.0/T1.1/T1.2
compatibility layer. Full-document controlled-Chinese pretranslation remains an
explicit experiment rather than a silent production default.

The T1-Codex 1.1.0 candidate is selected in the production lock but remains
`release_ready: false` until fixed public smoke and same-input human validation
across a Dharma talk, written article, and quotation-dense Buddhist text pass.
See `INSTALL_PROMPT-T1-CODEX.zh-CN.md`. The earlier stable T1-OMP installer
prompt remains in `INSTALL_PROMPT-T1.zh-CN.md` for rollback installations.
