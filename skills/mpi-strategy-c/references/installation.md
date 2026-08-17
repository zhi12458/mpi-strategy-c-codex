# Installation and repair

Run from the installed skill directory:

```text
python scripts/strategy_c.py install
```

The command uses the repository `dependency-lock.json`, installs or verifies
Git, Python 3.11+, Pandoc, FFmpeg, whisper.cpp, and Python keyring support,
clones MPI over SourceHut HTTPS, initializes the real `toolkit` submodule with a
local Codeberg HTTPS override, checks exact SHAs and origins, runs both doctors,
performs disposable dependency fault injection, and runs a non-private live
smoke using V4 Flash `high`, V4 Pro `max`, the public toolkit fixture, strict
mechanical QA, DOCX fidelity QA, and the document subtitle N/A gate. It writes
`READY.json` atomically only after those checks pass.

System package installation can require a native administrator confirmation.
Ask for that confirmation in the operating system, never for a password in
chat. Use `credential_store.py` to open a masked native key dialog and store the
DeepSeek key in macOS Keychain or Windows Credential Manager. Use
`select_whisper_model.py` to open the file picker and verify the exact model
SHA-256.

If the lock says `release_ready: false`, stop. That state means the candidate
commits have not both reached their official upstream branches. A maintainer
may use `--development-candidate` only for public-fixture tests; it writes
`ready: false` and cannot unlock a real translation.

Repair never checks out a nearby latest commit. It fetches the exact locked
commits into a temporary directory, validates them, and atomically replaces the
managed repository only after both doctors pass.
