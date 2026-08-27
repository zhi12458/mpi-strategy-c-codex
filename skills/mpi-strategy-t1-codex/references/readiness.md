# T1-Codex readiness

Skill validity, provider-runtime readiness, strategy release readiness, and a
document's human approval are four separate states.

## Package validity

Run `python scripts/validate_package.py`. It must verify complete manifest
coverage and these locked invariants:

- `source.dj` is the sole semantic authority;
- T1-Codex is the selected production default;
- Codex owns drafting and English editing;
- OMP owns only locked Flash/high and fresh Pro/max roles;
- bridge generation is high-risk-only and writes no English;
- two bilingual reviews and post-concision regression remain independent;
- full-document pretranslation is not a silent default;
- T1-OMP remains an explicit rollback, not an automatic merge source.

## Local runtime readiness

A local, non-repository `T1_CODEX_READY.json` may say `ready: true` only when:

- the Skill manifest and candidate ref match;
- the stable base T1 `READY.json` is `ready: true` and its manifest matches;
- OMP is exactly the locked version;
- Personal-workspace confirmation and the DeepSeek OS-vault credential are
  valid without exposing identifiers or secrets;
- fixed public Flash/high and Pro/max smoke calls pass;
- the current Codex task is verifiably GPT-5.6-Sol/high;
- role-policy and bridge/regression contract tests pass;
- no private text was used for installation smoke.

Keep local readiness under a T1-Codex-specific managed root. Never commit READY,
credentials, account identifiers, smoke transcripts containing secrets, or
manuscripts.

## Strategy release readiness

The current package remains `release_ready: false`. Promotion requires blinded,
same-input human validation on:

1. a Dharma talk shaped into publication prose;
2. a written article;
3. a quotation-dense Buddhist text.

T1-Codex must win or tie T1-OMP in every genre, add no unresolved critical or
major defect, and show no recurring Chinese-understanding failure. Model scores,
backtranslation, output length, finding counts, mechanical QA, and the user's
adoption decision remain diagnostic or workflow evidence; they do not replace
the genre validation artifacts.

## Document completion

Each document has its own source, term, model, review, QA, final-target, and
human-approval hashes. A ready installation can produce only an `AI reviewed
draft`. A named Buddhist/Dharma reviewer must approve that exact final target
before human-approved or release-ready status is allowed.
