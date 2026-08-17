# mpi-strategy-c-codex

Audited installer and Codex orchestration skill for the MPI Flash → Sol → Pro
Chinese-English Buddhist translation workflow. It deliberately contains no
replacement source extractor, MPI glossary, Djot generator, DOCX renderer, or
translation/subtitle QA logic; those operations must come from the locked
`translation-toolkit` Git submodule.

## Current release state

Pre-release and intentionally blocked. The Codeberg toolkit candidate is under
[PR #3](https://codeberg.org/eastwind/translation-toolkit/pulls/3), and the MPI
SourceHut candidate cannot be pushed by the current account. Therefore
`dependency-lock.json` has `release_ready: false`, and production installation
must refuse to write a ready installation.

See `INSTALL_PROMPT.zh-CN.md` for the eventual one-message setup prompt.

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

The second command is expected to say `BLOCKED` in this pre-release because
the official upstream pair is not yet published. This is the intended safety
behavior, not an installation error.
