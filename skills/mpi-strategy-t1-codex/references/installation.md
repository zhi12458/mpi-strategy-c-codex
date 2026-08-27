# T1-Codex installation

The T1-Codex Skill and the locked provider runtime are separate packages. The
Skill owns routing and workflow; the base T1 runtime owns OMP, credentials,
repository doctors, fault injection, and Flash/Pro provider calls.

## Fixed candidate sources

- Repository: `https://github.com/zhi12458/mpi-strategy-c-codex.git`
- T1-Codex path: `skills/mpi-strategy-t1-codex`
- Candidate ref: `t1-codex-v1.1.0-candidate.1`
- Stable base-runtime path: `skills/mpi-strategy-t1`
- Stable base-runtime ref: `t1-v1.0.1-installer-1.0.0`
- Stable base-runtime commit: `af795df625eca95ab138094bd25172266007f24f`

Do not install from a moving branch for a validated production run. The
candidate ref remains non-release-ready until the readiness and multi-genre
program in `production-lock.json` passes.

## Required order

1. Read Codex's built-in `skill-installer` instructions.
2. Inspect existing `mpi-strategy-t1` and `mpi-strategy-t1-codex` directories.
   Never overwrite an existing installation without reporting its version,
   manifest, readiness, and differences.
3. Install the stable base runtime from its fixed ref. Run its documented
   manifest, dependency, OAuth Personal-workspace, masked DeepSeek credential,
   fault-injection, public smoke, and doctor gates. Never paste credentials into
   chat or command arguments.
4. Install `skills/mpi-strategy-t1-codex` from the fixed candidate ref.
5. Run:

   ```sh
   python scripts/validate_package.py
   ```

6. Confirm the Codex task is configured as GPT-5.6-Sol with high reasoning.
   This task setting is separate from the OMP OAuth account.
7. Run only fixed public Flash/high and Pro/max markers when the user explicitly
   authorizes the small quota use. Never send a manuscript as installation
   smoke.
8. Follow [readiness.md](readiness.md). Do not mark the candidate production-
   ready merely because the files copied successfully.

Ordinary MPI Buddhist translation routes to this Skill. Explicit T1-OMP, C, M,
M2, media-specific, and non-Buddhist requests remain separate.
