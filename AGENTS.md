# Repository conventions

This repository installs, schedules, and audits MPI Strategy C. It must never
copy or reimplement translation-toolkit source extraction, MPI terminology,
Djot canonicalization, bilingual generation, DOCX generation/QA, subtitle
generation/QA, or deterministic translation checks.

Keep production locked while `dependency-lock.json` has `release_ready: false`.
Changing it to true requires official upstream commits, clean cross-platform
tests, disposable dependency fault injection, and the live public-fixture smoke
test. Never add credentials, manuscripts, generated translations, READY files,
or model binaries to this repository.
