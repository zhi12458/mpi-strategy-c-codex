# Audited document workflow

All paths passed to the runner must be absolute. Create a new project directory
under the managed `projects` directory and preserve the original input.

1. `doctor`, then `begin --project ... --input-type document`.
2. `run-tool --stage source_extraction` with `docx2dj.py` for DOCX or
   `source2dj.py` for TXT/Markdown/Djot. Output `source.dj`.
3. Analyze only the frozen Chinese to create `term-candidates.json`; this is a
   candidate list, not a glossary. Run `build-term-map.py` as stage
   `terminology`. It invokes the MPI database and writes the term map and search
   receipts. Resolve every `needs_human` item with the user.
4. Run toolkit `deepseek-source-analysis.py` as `flash_analysis`. It uses V4
   Flash, reasoning `high`, and must execute before `target.dj` exists.
5. Read the frozen source, term map, MPI instructions, and source analysis.
   Draft aligned English to `sol-draft.dj` using GPT-5.6-Sol `high`. Do not
   imitate English phrasing from another model. Record the model event, then run
   toolkit `freeze-target.py` as `target_freeze`.
6. Run `gen-bilingual.py` as `bilingual_1`; run `deepseek-review.py` with
   `--reasoning-effort max` as `pro_review_1`. Do not expose source analysis to
   Pro.
7. Sol validates and applies only sound findings to `sol-revised.dj`; run
   `freeze-target.py` as `target_refreeze`, regenerate as `bilingual_final`, and
   run Pro again as `pro_review_2`. Stop for any remaining critical/major
   blocker.
8. Run `check-translation.py PROJECT --strict --json --output qa-report.json`
   as `translation_qa`.
9. Run `dj2docx.py` twice as `target_docx` and `bilingual_docx`.
10. Run `check-docx.py` on both generated files as `target_docx_qa` and
    `bilingual_docx_qa`. Text fidelity and ZIP integrity must both pass.
11. Run `check-subtitles.py PROJECT --not-applicable --output
    subtitle-qa-report.json` as `subtitle_na`.
12. Run `finalize --input-type document`. Deliver source, target, bilingual,
    both DOCX files, findings, QA, receipts, and MANIFEST.

Do not write or edit `source.dj`, `target.dj`, `bilingual.dj`, term map, DOCX,
or QA reports with a substitute tool. Codex may write the intermediate Sol
draft and structured model/audit metadata only.
