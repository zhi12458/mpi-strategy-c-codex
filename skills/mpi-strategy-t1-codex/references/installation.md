# T1-Codex installation

The T1-Codex Skill and the locked provider runtime are separate packages. The
Skill owns routing and workflow; the base T1 runtime owns OMP, credentials,
repository doctors, fault injection, and Flash/Pro provider calls.

## Fixed candidate sources

- Repository: `https://github.com/zhi12458/mpi-strategy-c-codex.git`
- T1-Codex path: `skills/mpi-strategy-t1-codex`
- Candidate ref: `t1-codex-v1.2.0-candidate.2`
- Stable base-runtime path: `skills/mpi-strategy-t1`
- Stable base-runtime ref: `t1-v1.0.1-installer-1.0.0`
- Stable base-runtime commit: `af795df625eca95ab138094bd25172266007f24f`

Do not install from a moving branch for a validated production run. The
candidate ref remains non-release-ready until the readiness and multi-genre
program in `production-lock.json` passes.

## Required order

For an already installed runtime, first use the bounded revalidation entry:

```sh
python scripts/install_runtime.py --revalidate-existing --confirm-public-smoke
```

Use the smoke flag only when these public requests are authorized. This path
requires a valid saved Personal/Business selection, verifies the current account
and existing locked checkouts, and runs the unchanged base public smoke before
writing a new package-bound runtime report. It does not log in, install
dependencies, clone repositories, or rewrite historical base evidence. Failures
leave the prior runtime report intact. Authenticate or confirm a changed account
only when that specific check fails. The steps below remain the first-install
and missing-installation recovery path. This repair is a local runtime revision;
it does not change the immutable base release or assert a new public release.

1. Read Codex's built-in `skill-installer` instructions.
2. Inspect existing `mpi-strategy-t1` and `mpi-strategy-t1-codex` directories.
   Never overwrite an existing installation without reporting its version,
   manifest, readiness, and differences. Back up the existing package before installing this candidate.2. Preserve
   local differences and recheck readiness; never carry an old package
   readiness claim forward.
3. Install the stable base runtime files from their fixed ref, but do not run
   its Personal-only confirmation helper. The immutable base tag predates
   Business-workspace support.
4. Install `skills/mpi-strategy-t1-codex` from the fixed candidate ref.
5. Confirm that OMP is exactly `17.3.4`. If it is missing, obtain the user's
   native approval and install exactly
   `@oh-my-pi/pi-coding-agent@17.3.4`; do not substitute another version.
6. From the T1-Codex Skill directory, run the fail-closed interactive installer:

   ```sh
   python scripts/install_runtime.py
   ```

   The installer itself must open OMP login, run the redacted Personal or
   Business workspace confirmation, check the T1-specific OS credential vault,
   and—when the DeepSeek credential is absent—run the masked local
   `credential_store.py` prompt. It must then request the exact local phrase
   `RUN PUBLIC SMOKE`, run the immutable base installer and doctor, and require
   base `READY.json` to contain `ready: true`. `TEAM` remains an accepted alias
   for Business. Never paste credentials into chat or command arguments.
7. Only after the runtime installer reports `PASS`, run the separate static
   package validator:

   ```sh
   python scripts/validate_package.py
   ```

   A passing static validator without a passing runtime installer means only
   that the files are intact; it is not an installed provider runtime.
8. Confirm the selected GPT-5.6 or GPT-6 model and reasoning level are supported
   by the current Codex runtime, and record their actual values.
   This task setting is separate from the OMP OAuth account.
9. Verify the runtime report contains exact OMP `17.3.4`,
   `deepseek_credential_present: true`, `base_ready: true`, and
   `public_smoke_status: PASS`. Never send a manuscript as installation smoke.
10. Follow [readiness.md](readiness.md). Do not mark the candidate production-
   ready merely because the files copied successfully.

The runtime installer may never report `PASS` when a required command was
skipped. A Codex-only result is not T1-Codex and must be labeled `BLOCKED` or a
separate experiment.

Ordinary MPI Buddhist translation routes to this Skill. Explicit T1-OMP, C, M,
M2, media-specific, and non-Buddhist requests remain separate.
