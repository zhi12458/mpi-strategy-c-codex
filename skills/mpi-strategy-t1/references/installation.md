# T1 installation and repair

T1.2.0 is the compatibility/provider runtime capability version. It supplies
the locked OMP, credential, repository, smoke, and fault-injection layer used by
the separate T1-Codex production Skill. It also retains the explicit T1-OMP
fallback, optional human-quality/AI-scale pretranslation experiments, and
historical T1.1 validation. A copied Skill is not a ready runtime.

The current T1.2 candidate lock remains `release_ready: false` until its exact
manifest, public live smoke, compatibility contracts, and default-router
validation are reviewed. Do not bypass that lock. The published
`t1-v1.0.1-installer-1.0.0` tag remains the installable fallback meanwhile.

## Required release/install order

1. Validate the exact T1.2 skill manifest and repository state; never install a
   moving `main` or relabel an uncommitted candidate as a release.
2. Use the exact OMP version and selectors in `dependency-lock.json`.
3. Install Git, Python 3.11+, Pandoc, LibreOffice and `keyring`. PyYAML remains
   required only for historical T1.1.2 semantic-restructuring validation.
4. Run `python scripts/strategy_t1.py login-openai`; the user completes OAuth
   and selects their Personal workspace.
5. Run `python scripts/strategy_t1.py confirm-personal-workspace`; the user
   inspects the redacted usage report and types `PERSONAL` locally.
6. Run `python scripts/credential_store.py`; enter the DeepSeek key only in the
   masked local prompt, never chat, command arguments, files or logs.
7. After the release flag is independently approved, run
   `python scripts/strategy_t1.py install --confirm-public-smoke`. The smoke may
   send only fixed public fixtures, never a manuscript.
8. Run `python scripts/strategy_t1.py doctor`. Require base `ready: true` before
   T1-Codex may use its Flash/Pro provider roles. Require a separate `PASS`
   pretranslation contract only for an explicitly selected T1.2 experiment.

The installer binds the complete skill manifest, exact compatibility-fork
commits, doctors, disposable fault injection, public toolkit fixture, locked
Flash/Sol/Pro marker calls, historical semantic contracts and T1.2
pretranslation contracts. Sol remains part of rollback smoke; the T1-Codex
production Skill must not use OMP/Sol for its Codex-owned stages. A failed
optional capability does not corrupt the base provider runtime, but the
associated specialized runner stays blocked.

## Repair and updates

`python scripts/strategy_t1.py repair --confirm-public-smoke` reinstalls only
the exact approved lock. It never follows a moving branch. Preserve prior
managed checkouts for recovery.

Never borrow M's managed root, credential service, receipts or READY file. OMP
OAuth state is separate from the Codex App account. A browser callback alone
does not establish the selected account, model availability or readiness.
