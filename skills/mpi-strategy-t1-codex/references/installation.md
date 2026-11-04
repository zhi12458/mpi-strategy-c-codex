# T1-Codex DeepSeek-only provider installation

Read the dependency and production locks. The current Codex task owns GPT
translation/editing. OMP owns DeepSeek Flash/high and Pro/max only. Do not run
OMP OpenAI login, workspace confirmation, GPT smoke, the legacy T1 installer,
or its full doctor/READY gate. `confirm_workspace.py` is retained only as a
legacy compatibility helper, not part of this installation path.

## Dependencies and immutable helpers

Use Python >=3.11, Git, Pandoc (Djot/DOCX support), keyring>=25,<27,
LibreOffice/soffice, required fonts and exact OMP 17.3.4. Install the complete
T1-Codex package. Keep the base T1 package from commit
`af795df625eca95ab138094bd25172266007f24f` in a separate directory;
its manifest hash must be
`765bec51ed736a6e505e0e1bf6ef2f5a9dd7ce3eb4db7e2cc99dd29cb3ebd47e`.
Every listed base file is verified before helper execution. Never modify it.
Repository/toolkit origins and commits remain those in its dependency lock.

## First installation

From the T1-Codex skill directory run:

```sh
python scripts/install_runtime.py --base-skill-dir <immutable-base>
```

Only a missing DeepSeek key needs masked local credential entry. The existing
OS vault service/account is reused; no credentials are copied from other users.
The installer asks for `RUN PUBLIC SMOKE`; previously authorized automation may
use `--confirm-public-smoke`. No TTY is required if the credential is present
and that explicit flag is supplied. Never send private content as smoke.
Optional `--candidate-mpi` and `--candidate-toolkit` accept local clone sources;
origin, exact SHA, submodule and content verification are still mandatory.

The new managed root is `MPI-Strategy-T1-Codex` under the platform application
data directory (Linux: `mpi-strategy-t1-codex`); override with
`MPI_STRATEGY_T1_CODEX_ROOT`, never the legacy T1 variable.
The installer prepares missing repositories only. Existing ones must verify;
no reset/replacement is performed on revalidation.

## Revalidation

```sh
python scripts/install_runtime.py --base-skill-dir <immutable-base> --revalidate-existing --confirm-public-smoke
```

Each attempt preserves the previous runtime receipt, marks current readiness
false before live checks and writes success only after repository doctors,
DS-only model catalog, disposable fault injection, mechanical/DOCX and both
DeepSeek public smoke calls pass. Failure leaves a non-ready current receipt.
Legacy T1 READY and historical receipts are never rewritten or reused.
No OpenAI account/usage lookup is performed.

Schema-2 `T1_CODEX_RUNTIME_READY.json` records `runtime_profile: deepseek-only-v1`,
provider readiness, exact package/base hashes, repository and QA evidence.
`runtime_ready` covers only the provider runtime, not the current Codex identity,
full document gates or human approval. `codex_task_setting_still_requires_direct_verification`
remains true. Follow readiness.md before making any broader claim.
