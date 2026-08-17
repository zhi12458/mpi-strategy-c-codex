# Repository conventions

This repository installs, schedules, and audits MPI Strategy C. It must never
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
