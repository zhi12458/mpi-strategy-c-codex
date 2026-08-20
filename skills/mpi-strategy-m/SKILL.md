---
name: mpi-strategy-m
description: Install, repair, or run the audited MPI M Strategy Chinese-to-English Buddhist translation workflow. Use only when the user explicitly says “M方案”, “M策略”, “按M翻译”, “用M方案翻译”, “安装M策略”, or invokes $mpi-strategy-m; do not claim ordinary translation requests as M Strategy work.
---

# MPI M Strategy

Use only the locked MPI/toolkit runtime. Never substitute Codex-side source
extraction, terminology, Djot, DOCX, subtitle, or deterministic QA code.

## Route the request

- For installation or repair, read `references/installation.md`. Installation
  is complete only when the M-specific `READY.json` says `ready: true`.
- For documents, read `references/workflow.md`; for audio/video, also read
  `references/media.md`.
- Before freezing terms, read `references/terminology-verification.md`.
- For “继续刚才的 M 翻译”, resume only the newest incomplete M project whose
  instruction and artifact hashes remain valid.

## Required gates

1. Run `strategy_m.py doctor` and `strategy_m.py begin` before model work.
2. GPT-5.6-Sol `medium` owns the full draft, accuracy revision, and a separate
   concision pass. The concision pass must recheck Chinese for lost negation,
   degree, logic, quantities, qualifications, and speaker voice.
3. V4 Flash `high` reads frozen Chinese only. Reuse its analysis only when the
   frozen Chinese SHA-256 is identical. V4 Pro `max` reads Chinese, English,
   and the term map, but never the Flash analysis.
4. Run two independent Pro bilingual reviews. Sol `high` is allowed only for
   targeted title/critical/major findings that remain after review two; never
   use it for a full-document M translation.
5. Run every toolkit entry point through `strategy_m.py run-tool` so receipts
   remain complete. Freeze `Great Path, Great Business` and `Master Jiqun`
   whenever their Chinese source terms occur.
6. Unresolved terms or review blockers require human judgment. Never average
   away a disagreement.
7. Run `strategy_m.py finalize`. Deliver only if `pipeline_complete` is true;
   every result remains `ai_draft` until a named Buddhist/Dharma reviewer
   approves it.

The lock identifies verified compatibility forks and exact SHAs; do not follow
moving branches or silently replace them with upstream or nearby commits.
