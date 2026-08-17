# mpi-strategy-c-codex

Audited installer and Codex orchestration skill for the MPI Flash → Sol → Pro
Chinese-English Buddhist translation workflow. It deliberately contains no
replacement source extractor, MPI glossary, Djot generator, DOCX renderer, or
translation/subtitle QA logic; those operations must come from the locked
`translation-toolkit` Git submodule.

## Current release state

Ready through two verified compatibility forks:

- [MPI compatibility fork](https://github.com/zhi12458/mpi-translations),
  locked at `501e332f58245104a80d998dfa333a35fb6a4993`;
- [translation-toolkit compatibility fork](https://github.com/zhi12458/translation-toolkit),
  locked at `7077d962c065f85f70ad67c80daba63315279ee9`.

They are not represented as official releases. `dependency-lock.json` also
records the official SourceHut/Codeberg origins and the upstream base SHAs. The
installer never follows a moving `main`: it checks out the two exact release
SHAs, and the MPI checkout contains the toolkit as its real pinned Git
submodule.

See `INSTALL_PROMPT.zh-CN.md` for the customer one-message setup prompt and
`CUSTOMER_PROMPTS.zh-CN.md` for normal document/audio/video requests.

## What is implemented

- macOS Apple Silicon and Windows x64 managed roots, HTTPS Git locking, real
  MPI toolkit submodule initialization, atomic repair, both doctors, and
  hash-bound `READY.json`;
- native masked DeepSeek credential storage and exact SHA verification for the
  one supported Whisper model;
- natural-language document/audio/video routing, locked whisper.cpp media
  transcription, Flash `high` → GPT-5.6-Sol `high` → Pro `max` separation;
- a unified toolkit executor, append-only child receipts for every MPI term
  search, model receipts, current-artifact freshness checks, and MANIFEST;
- strict translation, bilingual, DOCX fidelity, subtitle, dependency-fault,
  and live public-fixture smoke gates.

Local validation:

```text
python -m pytest -q
python skills/mpi-strategy-c/scripts/strategy_c.py doctor
```

The installer writes `ready: true` only after exact repository verification,
both doctors, dependency fault injection, and a live non-private model smoke
all pass on that customer's computer.
