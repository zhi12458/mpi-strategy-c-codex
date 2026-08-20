# Audit records

`READY.json` is installation evidence. It binds the absolute MPI and toolkit
paths, canonical compatibility-fork origins, exact SHAs, official-upstream
origins and base SHAs, clean status, critical-file hashes,
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

`term-decisions.json` records each uncertain term's source context hashes, MPI
hits, admissible external evidence, chosen rendering, rationale, confidence,
scope, and status. `record-term-decisions` validates it against the frozen
source and adds a receipt. A high-confidence MPI decision may omit web evidence;
all other frozen uncertain decisions require admissible external evidence.

`external-lookup-receipts.jsonl` and `allusion-decisions.json` form a separate
cultural-expression evidence chain. The former records the actual authoritative
pages opened for every Flash-declared expression; the latter binds those
receipts to the exact source line and source-analysis hash. The
`allusion_research` receipt is mandatory even when Flash reports no allusions,
so omission cannot masquerade as a skipped stage. Sol translation receipts must
include `allusion-decisions.json` as an input.

A reused `source-analysis.json` receives a `flash_analysis_reuse` receipt only
when its stored source SHA-256 exactly matches the current `source.dj`. A Sol
high receipt is valid only at `sol_fallback` and must produce a targeted
`sol-fallback-adjudication.json`.

`MANIFEST.json` includes the full receipt set and current artifact hash chain.
`pipeline_complete` may be true only when every required stage is present,
current, successful, and free of strict QA FAIL/SKIP, unresolved terminology,
and unresolved second-round review blockers. `status: ai_draft` still requires
named human Buddhist/Dharma review before publication.
