---
name: mpi-strategy-c
description: Install, repair, or run the audited MPI Strategy C Chinese-to-English Buddhist translation workflow for DOCX, TXT, Markdown, Djot, audio, or video. Use when the user says to translate, organize and translate, make bilingual files, or create bilingual subtitles. Enforces locked mpi-translations and translation-toolkit dependencies, whisper-medium-2512-ft-best transcription, Flash source analysis, GPT-5.6-Sol English drafting, V4 Pro review, toolkit QA, and complete receipts.
---

# MPI Strategy C

Translate only through the locked MPI and toolkit runtime. Never substitute
Codex-side extraction, terminology, Djot, DOCX, subtitle, or QA code.

## Route the request

- For installation or repair, read `references/installation.md`, then run the
  shipped bootstrap. Do not claim installation success unless `READY.json`
  contains `ready: true`.
- For DOCX/TXT/Markdown/Djot translation, read `references/workflow.md` and use
  its document route.
- For audio/video, also read `references/media.md`. Use only the selected,
  hash-verified `whisper-medium-2512-ft-best-ggml.bin`; do not use a cloud ASR or
  another Whisper model.
- For “继续刚才的翻译”, locate the most recent incomplete project under the
  managed root, rerun preflight, verify receipt hashes, and resume only from a
  valid checkpoint.

## Non-negotiable gates

1. Run `strategy_c.py doctor` and `strategy_c.py begin` before creating
   `target.dj` or calling Flash, Sol, or Pro.
   If doctor fails, run `strategy_c.py repair` before doing anything else. The
   repair must fetch the exact lock into a temporary directory and pass every
   gate; if repair fails, stop without a model call.
2. Confirm this Codex task is using GPT-5.6-Sol with reasoning `high`. If that
   cannot be established, stop and tell the user how to select it.
3. Read the current task's `instruction-receipt.json` inputs yourself: locked
   MPI `AGENTS.md`, toolkit `AGENTS.md`, and the three required MPI skills.
4. Run every toolkit entry point through `strategy_c.py run-tool`. Never invoke
   a mandatory script directly because that would omit its audit receipt.
5. Flash reads only toolkit-frozen Chinese, term map, and MPI metadata. Pro
   reads Chinese, English, and term map but never Flash analysis. Sol alone
   decides English wording.
6. If terminology is unresolved or the second Pro review contains a critical
   or major blocker, stop for human judgment. Never conceal or average it away.
7. Run `strategy_c.py finalize`; report completion only if it writes
   `pipeline_complete: true`. Every delivery remains marked `ai_draft` until a
   named human Buddhist/Dharma reviewer approves it.

The public lock intentionally refuses production setup while either upstream
candidate is unmerged. Do not bypass `release_ready: false` for an end user.
