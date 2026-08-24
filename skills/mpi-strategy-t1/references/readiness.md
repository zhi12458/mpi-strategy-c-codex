# T1 installation evidence

The managed root contains three non-secret audit files:

- `READY.json`: exact skill, installer, repository, dependency, account-choice,
  model-catalog, fault-injection, and smoke evidence.
- `fault-injection-report.json`: disposable tamper cases and restoration proof.
- `smoke-test-report.json`: public-only model/tool executions with exit status,
  duration, and SHA-256 hashes of logs and outputs. It contains no key or
  manuscript text.

`READY.json` may say `ready: true` only when every gate in
`dependency-lock.json` passes. Model listing alone does not establish usable
credentials, and a skill manifest pass does not establish runtime readiness.

The Personal-workspace confirmation stores only the confirmation time and a
SHA-256 of the non-secret OMP usage response. It does not store email, account
ID, organization ID, OAuth token, or API key.

The DeepSeek key remains under the T1-specific operating-system credential
service `mpi-strategy-t1-deepseek`. Runtime helpers inject it only into a child
OMP process and remove it from their local environment mapping afterward.
