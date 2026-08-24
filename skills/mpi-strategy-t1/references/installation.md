# T1 installation and repair

T1.0.1 is the workflow version. The separately versioned installer is 1.0.0.
Installing the Codex skill alone does not make the runtime production-ready.

## Required order

1. Install the pinned T1 skill from the public strategy repository. The Codex
   skill installer source is repository `zhi12458/mpi-strategy-c-codex`, path
   `skills/mpi-strategy-t1`, ref `t1-v1.0.1-installer-1.0.0`. Do not install
   from moving `main`.
2. Install OMP 17.3.4 from its official package. The reproducible Bun command is
   `bun install -g @oh-my-pi/pi-coding-agent@17.3.4`. If Bun is absent, obtain
   Bun only from its official distribution after native user consent. Do not
   silently accept a different OMP version as validated.
3. Install Git, Python 3.11+, Pandoc, LibreOffice, and Python keyring support.
   System package installation requires the user's native administrator
   confirmation; never ask for a password in chat.
4. Run `python scripts/strategy_t1.py login-openai`. The user completes the
   browser flow and selects their **Personal account**, not an organization
   workspace.
5. Run `python scripts/strategy_t1.py confirm-personal-workspace`. The user
   inspects the non-secret OMP usage summary and types `PERSONAL` locally.
6. Run `python scripts/credential_store.py`. The user enters the DeepSeek API
   key in the masked native/local prompt. Never paste the key into Codex chat,
   a command argument, a repository file, or a log.
7. Run `python scripts/strategy_t1.py install --confirm-public-smoke`. The live
   smoke sends only fixed public test strings and consumes a small amount of
   model quota. It never transmits a manuscript.
8. Run `python scripts/strategy_t1.py doctor` and require `ready: true`.

The installer checks the skill manifest, OMP version and model catalog, clones
the exact verified MPI and toolkit compatibility-fork commits over HTTPS, runs
both repository doctors, runs fault injection in a disposable copy, exercises
the public toolkit fixture, and calls Flash/high, Sol/high, and Pro/max with
public marker prompts. `READY.json` is written atomically and remains false if
any gate fails.

## Repair and updates

`python scripts/strategy_t1.py repair --confirm-public-smoke` reinstalls only
the exact commits and versions in `dependency-lock.json`; it never follows a
moving `main`. Backups of a replaced managed checkout remain under the managed
`repos` directory for recovery.

Do not borrow M's managed root, credential service, receipts, or READY file.
OMP OAuth state is also separate from the Codex App account. A successful
browser callback is not sufficient: the usage check, Personal confirmation,
model catalog, and live public smoke must all pass.
