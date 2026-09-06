# Repository conventions

This repository installs, schedules, and audits MPI Strategy M 1.0 and stores
the separate MPI T1 production skill. It must never
copy or reimplement translation-toolkit source extraction, MPI terminology,
Djot canonicalization, bilingual generation, DOCX generation/QA, subtitle
generation/QA, or deterministic translation checks.

Production may use verified compatibility forks when official upstream has not
merged required runtime support. The lock must record each fork's exact HTTPS
origin and SHA plus the official upstream origin and base SHA. Never describe a
fork as an official upstream release, follow `main` automatically, or change a
lock without clean cross-platform tests and disposable dependency fault
injection. Every customer installation must also pass its own non-private live
smoke before `READY.json` can become ready. Never add credentials, manuscripts,
generated translations, READY files, or model binaries to this repository.

M is a distinct strategy identity. Keep its skill name, managed root, READY,
receipts, and model stages separate from archived Strategy C. The original C
High workflow may be documented for comparison but must not be reactivated as
an implicit daily translation route.

T1 is also a distinct strategy identity. Keep `mpi-strategy-t1` separate from
M. T1-Codex is the selected default for ordinary MPI Chinese-English Buddhist
books, articles, and documents. The base T1 package remains the provider runtime
and explicit T1-OMP rollback; supporting materials use their separate workflow.
Explicit C, M, M2, T1-OMP, or user-defined workflows override the default.
T1 source files must match their
`MANIFEST.sha256`; do not treat T1's workflow adoption as human approval of any
future translation.
