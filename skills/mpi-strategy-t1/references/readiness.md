# T1 readiness evidence

The managed root records non-secret, hash-bound evidence:

- `READY.json`: exact skill, runtime, repositories, dependencies, account
  confirmation, model catalog, fault injection, smoke and capability gates.
- fault-injection and public smoke reports.
- historical T1.1.2 semantic-restructuring contract evidence when PyYAML is
  available.
- T1.2 pretranslation contract evidence covering full source inventory,
  human/AI provenance separation, blocked AI fallback, Pro decision routing and
  accepted-artifact resolution.

Base `ready: true` means only the provider/T1-OMP runtime gates passed. It does
not make the separate T1-Codex package ready. A T1.2 specialized
runner additionally requires current `pretranslation_contracts.status: PASS`,
an existing report with the recorded hash, and a manifest matching the current
skill. Historical semantic runners independently require their older capability
gate. One optional failure must not be relabeled as another mode's success.

Readiness does not select a document track, prove T1-Codex release promotion,
prove AI-scale promotion, establish a comparison result for a new source, or
approve a final target.
Each document retains its own source, pretranslation, decision, review, QA and
human-approval hashes.

The Personal-workspace record stores no email, account ID or OAuth token. The
DeepSeek key remains in the T1-specific operating-system credential service and
is injected only into the child OMP process. Receipt usage counts actual locked
model invocations; unknown token counts remain null and OMP event counts are not
accepted as substitutes.
