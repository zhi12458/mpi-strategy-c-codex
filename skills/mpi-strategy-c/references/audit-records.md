# Audit records

`READY.json` is installation evidence. It binds the absolute MPI and toolkit
paths, canonical origins, exact SHAs, clean status, critical-file hashes,
AGENTS hashes, both doctor results, the Whisper executable and model hashes,
the disposable fault-test report, and the non-private live smoke report.

`instruction-receipt.json` is project-start evidence. It binds the current
READY file and the bytes actually read from MPI `AGENTS.md`, toolkit
`AGENTS.md`, `mpi-translation`, `mpi-terms-search`, and
`mpi-translation-review`. It must predate every model call and `target.dj`.

`tool-execution-receipts.jsonl` is append-only. A toolkit receipt contains its
stage, absolute executable/script path, repository origin/SHA, script hash,
arguments, input/output hashes, exit, duration, and hashed non-content logs.
The terminology parent receipt expands each actual `search.py` subprocess into
its own child receipt. Model receipts bind role, exact model/effort, prompt
hash, input/output hashes, fingerprint/tokens/cost/retries when available.

`MANIFEST.json` includes the full receipt set and current artifact hash chain.
`pipeline_complete` may be true only when every required stage is present,
current, successful, and free of strict QA FAIL/SKIP and second-round review
blockers. `status: ai_draft` still requires named human Buddhist/Dharma review
before publication.
