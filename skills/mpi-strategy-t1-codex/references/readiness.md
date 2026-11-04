# T1-Codex readiness

Skill validity, provider-runtime readiness, strategy release readiness, and a
document's human approval are four separate states.

## Package validity

Run `python scripts/validate_package.py`. It must verify complete manifest
coverage and these locked invariants:

- `source.dj` is the sole semantic authority;
- T1-Codex is the selected production default;
- Codex owns bounded Chinese semantic segmentation, drafting, and English
  editing;
- OMP owns only locked Flash/high and fresh Pro/max roles;
- bridge generation is high-risk-only and writes no English;
- Chinese semantic segmentation covers every nonblank source line, remains
  non-authoritative, obeys the guarded `我们` rule, receives a fresh Pro/max
  Chinese-only review, and is retained as internal evidence or delivered
  separately when requested;
- two bilingual reviews and post-concision regression remain independent;
- the mandatory general-English and Dharma-English readers are mutually
  isolated and English-only in both initial and final rounds;
- reader changes require source-based adjudication, commissioner choice for
  sensitive categories, and a complete Chinese/regression rerun;
- the resumable post-translation route preserves the incoming target, does not
  rerun translation or bilingual reviews by default, distinguishes low-risk
  repairs from commissioner-sensitive changes, and cannot inherit full
  T1-Codex status from incomplete upstream evidence;
- human feedback is assessed item by item and followed by a full-document
  analogue scan, while project terminology decisions remain project-scoped;
- the clean alternating bilingual Word profile excludes all internal editing
  evidence and requires pair, font, DOCX, and page-by-page visual checks;
- full-document stylistic pretranslation is not a silent default;
- T1-OMP remains an explicit rollback, not an automatic merge source.

## Local runtime readiness

For first installation, run `python scripts/install_runtime.py` interactively.
For an existing installation with an explicitly confirmed account, run
`python scripts/install_runtime.py --revalidate-existing --confirm-public-smoke`
after authorization for the public tests. Revalidation checks the current
account against its saved selection, both base doctors, locked repositories,
credentials, OMP, and fresh public smoke. It does not open OAuth or replace
managed repositories. Missing or changed account selection needs interactive
confirmation; failed authentication needs login. A manifest change alone does
not require either. Previous READY and test evidence are retained.

A local, non-repository
`T1_CODEX_RUNTIME_READY.json` may say `runtime_ready: true` only when:

- the Skill manifest and candidate ref match;
- the stable base T1 `READY.json` is `ready: true` and its manifest matches;
- OMP is exactly the locked version;
- an explicitly selected Personal or ChatGPT Business workspace confirmation
  and the DeepSeek OS-vault credential are valid without exposing identifiers
  or secrets; `TEAM` is accepted only as the former name for Business;
- fixed public Flash/high and Pro/max smoke calls pass;
- the current Codex task uses a verified allowed GPT-5.6 or GPT-6 model and
  runtime-supported reasoning level, with its actual settings recorded;
- role-policy, bridge, semantic-segmentation, and regression contract tests
  pass;
- no private text was used for installation smoke.

`validate_package.py` proves only package integrity and role-policy consistency.
It cannot establish runtime readiness. If the runtime report is absent, any
required field is false, or the base doctor does not return `ready: true`, the
installation status is `BLOCKED`. Do not silently replace Flash/Pro stages with
Codex or describe such a run as T1-Codex.

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
human-approval hashes. Run
`python scripts/validate_semantic_segmentation.py <project> --stage review`
before English drafting and `python scripts/validate_reader_gate.py <project>`
before claiming a full new document complete. For an existing-translation
retrofit, also run
`python scripts/validate_post_translation_editing.py <project>`. A ready
installation can produce only an `AI reviewed draft`, and only when both final
English-only readers have zero blockers or actionable findings and the post-
reader full Chinese review and bidirectional regression show no unapproved
omission, addition, or sensitive change. An incomplete upstream baseline may
claim only `T1-Codex post-edit AI-reviewed draft`. A named Buddhist/Dharma
reviewer must approve the exact final target before human-approved or release-
ready status is allowed.
