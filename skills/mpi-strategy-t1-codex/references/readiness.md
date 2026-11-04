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

Use the DS-only installation and revalidation commands in installation.md.
Only schema-2 evidence with `runtime_profile: deepseek-only-v1` is accepted for
this runtime. Its `runtime_ready`/`provider_runtime_ready` means only:
- exact skill and immutable helper hashes;
- OMP 17.3.4 with Flash/high and Pro/max catalog support;
- DeepSeek OS-vault credential;
- exact repository/toolkit commits, submodule and both repository doctors;
- fresh disposable fault injection;
- fresh public mechanical/DOCX smoke and exactly two DeepSeek model calls.

No OMP OpenAI login, workspace confirmation, GPT smoke or legacy base READY is
required. Do not relabel old receipts; use the separate T1-Codex managed root.
A new attempt backs up prior evidence and writes non-ready state before checks.
Failure cannot leave an old ready flag looking current.

The current Codex model/effort/session identity must still be verified against
`codex_model_policy` in the current task. Provider readiness cannot prove it.
Do not claim document completion, human approval or release readiness from
installation success. External private-text authorization remains mandatory.

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
