from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest


SCRIPTS = Path(__file__).parents[1] / "skills" / "mpi-strategy-m" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import bootstrap  # noqa: E402
import fault_injection  # noqa: E402
import runtime  # noqa: E402
import strategy_m  # noqa: E402


GIT_ENV = {
    **os.environ,
    "GIT_AUTHOR_NAME": "Test",
    "GIT_AUTHOR_EMAIL": "test@example.invalid",
    "GIT_COMMITTER_NAME": "Test",
    "GIT_COMMITTER_EMAIL": "test@example.invalid",
}


def command(cwd: Path, *args: str) -> str:
    result = subprocess.run(args, cwd=cwd, env=GIT_ENV, text=True, capture_output=True, check=False)
    assert result.returncode == 0, result.stderr
    return result.stdout.strip()


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")


def write_clear_term_decisions(project: Path) -> None:
    source = project / "source.dj"
    write(source, "原文\n")
    write(project / "target.dj", "English\n")
    runtime.atomic_json(project / "term-decisions.json", {
        "schema_version": 1,
        "source_sha256": runtime.sha256_file(source),
        "items": [],
    })
    write(project / "term-map.yaml", '{"terms": []}\n')


def make_repo(path: Path, origin: str) -> str:
    command(path.parent, "git", "init", str(path))
    command(path, "git", "config", "core.autocrlf", "false")
    command(path, "git", "remote", "add", "origin", origin)
    return origin


def commit(path: Path, message: str) -> str:
    command(path, "git", "add", "-A")
    command(path, "git", "commit", "-m", message)
    return command(path, "git", "rev-parse", "HEAD")


def test_clone_locked_uses_independent_local_clone_flags(tmp_path, monkeypatch):
    source = tmp_path / "source"
    source.mkdir()
    destination = tmp_path / "destination"
    calls = []

    def capture(arguments, cwd):
        calls.append((arguments, cwd))

    monkeypatch.setattr(bootstrap, "git_checked", capture)
    bootstrap.clone_locked(
        str(source), destination, "1" * 40,
        "https://example.invalid/canonical.git",
    )

    clone = calls[0][0]
    assert "--local" in clone
    assert "--no-hardlinks" in clone
    assert "--filter=blob:none" not in clone
    assert calls[-1][0][-2:] == ("origin", "https://example.invalid/canonical.git")


def test_clone_locked_keeps_partial_filter_for_https_sources(tmp_path, monkeypatch):
    calls = []

    def capture(arguments, cwd):
        calls.append((arguments, cwd))

    monkeypatch.setattr(bootstrap, "git_checked", capture)
    bootstrap.clone_locked(
        "https://example.invalid/source.git", tmp_path / "destination",
        "1" * 40, "https://example.invalid/canonical.git",
    )

    clone = calls[0][0]
    assert "--filter=blob:none" in clone
    assert "--local" not in clone


def test_disposable_parent_commit_changes_only_submodule_pointer(installation):
    mpi = installation["mpi"]
    toolkit = installation["toolkit"]
    write(toolkit / "fault.txt", "fault\n")
    toolkit_sha = commit(toolkit, "fault toolkit")

    parent_sha = fault_injection.commit_submodule_pointer(
        mpi, "toolkit", toolkit_sha, "point to fault toolkit",
    )

    assert command(mpi, "git", "rev-parse", "HEAD") == parent_sha
    assert toolkit_sha in command(mpi, "git", "ls-tree", "HEAD", "toolkit")
    assert command(mpi, "git", "status", "--porcelain=v1", "--untracked-files=all") == ""


@pytest.fixture
def installation(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    root = tmp_path / "managed"
    mpi = root / "repos" / "mpi-translations"
    toolkit = mpi / "toolkit"
    mpi_origin = "https://git.sr.ht/~iacore/mpi-translations/"
    toolkit_origin = "https://codeberg.org/eastwind/translation-toolkit.git"
    toolkit.parent.mkdir(parents=True)
    make_repo(toolkit, toolkit_origin)
    doctor = """#!/usr/bin/env python3
import json, os, sys
ok = not bool(os.environ.get('FAIL_FAKE_DOCTOR'))
print(json.dumps({'ok': ok}))
raise SystemExit(0 if ok else 1)
"""
    copier = """#!/usr/bin/env python3
import pathlib, sys
source, output = map(pathlib.Path, sys.argv[1:3])
output.write_text(source.read_text(encoding='utf-8'), encoding='utf-8')
"""
    write(toolkit / "AGENTS.md", "# Toolkit rules\n")
    write(toolkit / "scripts" / "doctor.py", doctor)
    write(toolkit / "scripts" / "source2dj.py", copier)
    write(toolkit / "scripts" / "docx2dj.py", copier)
    write(toolkit / "scripts" / "check-translation.py", copier)
    write(toolkit / "terms-database" / "termlib.sqlite", "test database bytes\n")
    for skill in ("mpi-translation", "mpi-terms-search", "mpi-translation-review"):
        write(toolkit / "skills" / skill / "SKILL.md", f"---\nname: {skill}\ndescription: test\n---\n")
    toolkit_sha = commit(toolkit, "toolkit")

    make_repo(mpi, mpi_origin)
    write(mpi / "AGENTS.md", "# MPI rules\n")
    write(mpi / "scripts" / "doctor.py", doctor)
    write(mpi / ".gitmodules", f'[submodule "toolkit"]\n\tpath = toolkit\n\turl = {toolkit_origin}\n')
    mpi_sha = commit(mpi, "mpi")
    command(mpi, "git", "config", "submodule.toolkit.url", toolkit_origin)
    command(mpi, "git", "config", "submodule.toolkit.active", "true")

    lock = {
        "schema_version": 1,
        "strategy_id": "M",
        "workflow_version": "1.0.0",
        "skill_version": "test",
        "terminology_policy_version": "test",
        "release_ready": True,
        "mpi_translations": {
            "origin": mpi_origin,
            "expected_sha": mpi_sha,
            "compatibility_fork": True,
            "upstream_origin": "https://example.invalid/mpi-upstream",
            "upstream_base_sha": "1" * 40,
            "required_files": ["AGENTS.md", "scripts/doctor.py"],
        },
        "translation_toolkit": {
            "origin": toolkit_origin,
            "expected_sha": toolkit_sha,
            "submodule_path": "toolkit",
            "required_files": [
                "AGENTS.md", "scripts/doctor.py", "scripts/source2dj.py",
                "scripts/docx2dj.py", "scripts/check-translation.py",
                "terms-database/termlib.sqlite",
            ],
        },
        "models": {
            "source_analysis": {"provider": "deepseek", "model": "deepseek-v4-flash", "reasoning_effort": "high"},
            "translation": {"provider": "openai-codex", "model": "gpt-5.6-sol", "reasoning_effort": "medium"},
            "translation_fallback": {"provider": "openai-codex", "model": "gpt-5.6-sol", "reasoning_effort": "high"},
            "review": {"provider": "deepseek", "model": "deepseek-v4-pro", "reasoning_effort": "max"},
        },
        "model_policy": {"translation_default": "fixed"},
        "fixed_terms": {
            "济群法师": "Master Jiqun",
            "大道大商": "Great Path, Great Business",
        },
        "validation_baseline": {"name": "test"},
    }
    lock_path = tmp_path / "dependency-lock.json"
    write(lock_path, json.dumps(lock))
    monkeypatch.setattr(runtime, "LOCK_PATH", lock_path)
    monkeypatch.setattr(bootstrap, "load_lock", lambda: runtime.load_json(lock_path))
    monkeypatch.setattr(strategy_m, "load_lock", lambda: runtime.load_json(lock_path))
    monkeypatch.setenv("MPI_STRATEGY_M_ROOT", str(root))

    mpi_info = runtime.verify_repo(mpi, lock["mpi_translations"])
    toolkit_info = runtime.verify_repo(toolkit, lock["translation_toolkit"])
    ready = {
        "schema_version": 1,
        "ready": True,
        "strategy_id": "M",
        "workflow_version": "1.0.0",
        "skill_version": "test",
        "terminology_policy_version": "test",
        "models": lock["models"],
        "mpi_translations": mpi_info,
        "translation_toolkit": toolkit_info,
    }
    runtime.atomic_json(root / "READY.json", ready)
    return {"root": root, "mpi": mpi, "toolkit": toolkit, "lock": lock, "lock_path": lock_path}


def test_valid_installation_generates_complete_instruction_receipt(installation, tmp_path):
    ready, mpi, toolkit = runtime.verify_ready()
    assert ready["ready"] is True
    assert ready["strategy_id"] == "M"
    assert ready["workflow_version"] == "1.0.0"
    assert mpi["doctor_exit_code"] == toolkit["doctor_exit_code"] == 0
    assert mpi["compatibility_fork"] is True
    assert mpi["upstream_origin"] == "https://example.invalid/mpi-upstream"
    assert mpi["upstream_base_sha"] == "1" * 40

    receipt = runtime.begin_project(tmp_path / "project", "document")

    assert len(receipt["instructions"]) == 5
    assert receipt["strategy_id"] == "M"
    assert Path(receipt["instructions"][0]["absolute_path"]).name == "AGENTS.md"


def test_missing_mpi_agents_blocks_until_restored(installation):
    path = installation["mpi"] / "AGENTS.md"
    original = path.read_bytes()
    path.unlink()
    with pytest.raises(runtime.StrategyMError):
        runtime.verify_ready()
    path.write_bytes(original)
    assert runtime.verify_ready()[0]["ready"] is True


def test_wrong_origin_blocks_until_restored(installation):
    mpi = installation["mpi"]
    command(mpi, "git", "remote", "set-url", "origin", "https://example.invalid/wrong")
    with pytest.raises(runtime.StrategyMError, match="origin mismatch"):
        runtime.verify_ready()
    command(mpi, "git", "remote", "set-url", "origin", installation["lock"]["mpi_translations"]["origin"])
    assert runtime.verify_ready()[0]["ready"] is True


def test_wrong_mpi_sha_blocks_until_exact_commit_is_restored(installation):
    mpi = installation["mpi"]
    write(mpi / "unexpected.txt", "new commit\n")
    commit(mpi, "unexpected")
    with pytest.raises(runtime.StrategyMError, match="SHA mismatch"):
        runtime.verify_ready()
    command(mpi, "git", "checkout", "--detach", installation["lock"]["mpi_translations"]["expected_sha"])
    (mpi / "unexpected.txt").unlink(missing_ok=True)
    assert runtime.verify_ready()[0]["ready"] is True


@pytest.mark.parametrize(
    "relative",
    ["scripts/docx2dj.py", "terms-database/termlib.sqlite", "scripts/check-translation.py"],
)
def test_modified_critical_toolkit_file_blocks_until_restored(installation, relative):
    toolkit = installation["toolkit"]
    script = toolkit / relative
    script.write_text(script.read_text(encoding="utf-8") + "# damaged\n", encoding="utf-8")
    with pytest.raises(runtime.StrategyMError):
        runtime.verify_ready()
    command(toolkit, "git", "checkout", "--", relative)
    assert runtime.verify_ready()[0]["ready"] is True


def test_missing_toolkit_and_failing_doctor_both_block(installation, monkeypatch):
    toolkit = installation["toolkit"]
    moved = toolkit.with_name("toolkit.missing")
    toolkit.rename(moved)
    with pytest.raises(runtime.StrategyMError):
        runtime.verify_ready()
    moved.rename(toolkit)
    monkeypatch.setenv("FAIL_FAKE_DOCTOR", "1")
    with pytest.raises(runtime.StrategyMError, match="doctor failed"):
        runtime.verify_ready()
    monkeypatch.delenv("FAIL_FAKE_DOCTOR")
    assert runtime.verify_ready()[0]["ready"] is True


def test_unreleased_lock_blocks_even_forged_ready(installation):
    lock = runtime.load_json(installation["lock_path"])
    lock["release_ready"] = False
    write(installation["lock_path"], json.dumps(lock))
    with pytest.raises(runtime.StrategyMError, match="release lock"):
        runtime.verify_ready()
    with pytest.raises(runtime.StrategyMError, match="release lock"):
        bootstrap.install(Path("missing.bin"), install_missing=False)


def test_tool_call_is_receipted_with_repository_and_hashes(installation, tmp_path):
    project = tmp_path / "project"
    runtime.begin_project(project, "document")
    source = tmp_path / "input.txt"
    output = project / "source.dj"
    write(source, "原文\n")

    receipt = strategy_m.run_audited_tool(
        project, "source_extraction", "source2dj.py",
        [str(source), str(output)], [source], [output],
    )

    assert receipt["exit_code"] == 0
    assert receipt["script_sha256"] == runtime.sha256_file(installation["toolkit"] / "scripts" / "source2dj.py")
    assert receipt["owner_repository"]["git_sha"] == installation["lock"]["translation_toolkit"]["expected_sha"]
    assert runtime.read_receipts(project)[0]["outputs"][0]["sha256"] == runtime.sha256_file(output)


def test_stale_artifact_prevents_manifest_completion(installation, tmp_path):
    project = tmp_path / "project"
    runtime.begin_project(project, "document")
    write_clear_term_decisions(project)
    artifact = project / "bilingual.dj"
    write(artifact, "fresh\n")
    qa = {"status": "PASS", "checks": []}
    subtitle_qa = {"status": "not_applicable", "reason": "document input"}
    write(project / "qa-report.json", json.dumps(qa))
    write(project / "target-docx-qa-report.json", json.dumps(qa))
    write(project / "bilingual-docx-qa-report.json", json.dumps(qa))
    write(project / "subtitle-qa-report.json", json.dumps(subtitle_qa))
    write(project / "semantic-review.json", json.dumps({"status": "clear", "blocking_findings": 0}))
    output = runtime.file_record(artifact)
    for stage in sorted(strategy_m.DOCUMENT_STAGES | strategy_m.MODEL_STAGES):
        runtime.append_receipt(project, {"receipt_id": stage, "workflow_stage": stage, "exit_code": 0, "outputs": [output]})

    assert strategy_m.finalize(project, "document")["pipeline_complete"] is True
    write(artifact, "stale replacement\n")
    with pytest.raises(runtime.StrategyMError):
        strategy_m.finalize(project, "document")
    assert runtime.load_json(project / "MANIFEST.json")["pipeline_complete"] is False


def test_forged_old_qa_report_fails_freshness_chain(installation, tmp_path):
    project = tmp_path / "project"
    runtime.begin_project(project, "document")
    write_clear_term_decisions(project)
    bilingual = project / "bilingual.dj"
    qa_path = project / "qa-report.json"
    subtitle_path = project / "subtitle-qa-report.json"
    target_docx_qa = project / "target-docx-qa-report.json"
    bilingual_docx_qa = project / "bilingual-docx-qa-report.json"
    write(bilingual, "中\nEnglish\n\n")
    write(qa_path, json.dumps({"status": "PASS", "run": 1}))
    write(subtitle_path, json.dumps({"status": "not_applicable"}))
    write(target_docx_qa, json.dumps({"status": "PASS"}))
    write(bilingual_docx_qa, json.dumps({"status": "PASS"}))
    write(project / "semantic-review.json", json.dumps({"status": "clear", "blocking_findings": 0}))
    outputs = [runtime.file_record(path) for path in (bilingual, qa_path, subtitle_path, target_docx_qa, bilingual_docx_qa)]
    for stage in sorted(strategy_m.DOCUMENT_STAGES | strategy_m.MODEL_STAGES):
        runtime.append_receipt(project, {"receipt_id": stage, "workflow_stage": stage, "exit_code": 0, "outputs": outputs})
    assert strategy_m.finalize(project, "document")["pipeline_complete"] is True

    write(qa_path, json.dumps({"status": "PASS", "run": "forged-old"}))
    with pytest.raises(runtime.StrategyMError):
        strategy_m.finalize(project, "document")
    manifest = runtime.load_json(project / "MANIFEST.json")
    assert str(qa_path) in manifest["stale_or_missing_artifacts"]


def test_secret_arguments_are_rejected():
    with pytest.raises(runtime.StrategyMError):
        runtime.reject_secret_arguments(["--api-key=sk-test"])


def test_sol_medium_is_default_and_high_is_only_targeted_fallback(installation, tmp_path):
    project = tmp_path / "project"
    runtime.begin_project(project, "document")
    source = project / "source.dj"
    medium_output = project / "sol-draft.dj"
    fallback_output = project / "sol-fallback-adjudication.json"
    write(source, "原文\n")
    write(medium_output, "English\n")
    write(fallback_output, json.dumps({
        "scope": "targeted_title_or_critical_major",
        "status": "resolved",
        "unresolved_findings": 0,
    }))
    runtime.append_receipt(project, {
        "receipt_id": "flash-analysis-reuse",
        "workflow_stage": "flash_analysis_reuse",
        "exit_code": 0,
        "outputs": [],
    })

    receipt = strategy_m.record_model(
        project, "sol_translation", "openai-codex", "gpt-5.6-sol", "medium",
        "0" * 64, [source], [medium_output], None,
    )
    assert receipt["reasoning_effort"] == "medium"
    with pytest.raises(runtime.StrategyMError, match="release lock"):
        strategy_m.record_model(
            project, "sol_translation", "openai-codex", "gpt-5.6-sol", "high",
            "1" * 64, [source], [medium_output], None,
        )
    semantic_review = project / "semantic-review.json"
    write(semantic_review, json.dumps({"status": "blocking", "blocking_findings": 1}))
    runtime.append_receipt(project, {
        "receipt_id": "pro_model_2",
        "workflow_stage": "pro_model_2",
        "exit_code": 0,
        "outputs": [runtime.file_record(semantic_review)],
    })
    fallback = strategy_m.record_model(
        project, "sol_fallback", "openai-codex", "gpt-5.6-sol", "high",
        "2" * 64, [source, semantic_review], [fallback_output], None,
    )
    assert fallback["workflow_stage"] == "sol_fallback"


def test_concision_is_separate_ordered_medium_stage(installation, tmp_path):
    project = tmp_path / "project"
    runtime.begin_project(project, "document")
    source = project / "source.dj"
    revised = project / "sol-revised.dj"
    concise = project / "sol-concise.dj"
    write(source, "原文\n")
    write(revised, "Accurate English\n")
    write(concise, "Concise English\n")

    with pytest.raises(runtime.StrategyMError, match="out of order"):
        strategy_m.record_model(
            project, "sol_concision", "openai-codex", "gpt-5.6-sol", "medium",
            "4" * 64, [source, revised], [concise], None,
        )
    runtime.append_receipt(project, {
        "receipt_id": "accuracy",
        "workflow_stage": "sol_accuracy_revision",
        "exit_code": 0,
        "outputs": [runtime.file_record(revised)],
    })
    receipt = strategy_m.record_model(
        project, "sol_concision", "openai-codex", "gpt-5.6-sol", "medium",
        "5" * 64, [source, revised], [concise], None,
    )
    assert receipt["workflow_stage"] == "sol_concision"


def test_fixed_terms_ignore_djot_anchors_and_require_exact_renderings(installation, tmp_path):
    source = tmp_path / "source.dj"
    target = tmp_path / "target.dj"
    term_map = tmp_path / "term-map.yaml"
    write(source, "{#大道大商}\n大道大商\n济群法师\n")
    write(target, "{#大道大商}\nGreat Path, Great Business\nMaster Jiqun\n")
    write(term_map, json.dumps({"terms": [
        {"source": "大道大商", "preferred": "Great Path, Great Business"},
        {"source": "济群法师", "preferred": "Master Jiqun"},
    ]}, ensure_ascii=False))

    summary = strategy_m.validate_strategy_fixed_terms(source, term_map, target)
    path_term = next(item for item in summary["checked"] if item["source"] == "大道大商")
    assert path_term["source_count_excluding_structural_anchors"] == 1
    assert path_term["target_count"] == 1


def test_sol_high_fallback_is_rejected_before_blocking_second_review(installation, tmp_path):
    project = tmp_path / "project"
    runtime.begin_project(project, "document")
    source = project / "source.dj"
    output = project / "sol-fallback-adjudication.json"
    write(source, "原文\n")
    write(output, json.dumps({"scope": "targeted_title_or_critical_major", "status": "resolved", "unresolved_findings": 0}))
    with pytest.raises(runtime.StrategyMError, match="completed second Pro review"):
        strategy_m.record_model(
            project, "sol_fallback", "openai-codex", "gpt-5.6-sol", "high",
            "3" * 64, [source], [output], None,
        )


def test_fallback_resolution_is_bound_to_receipted_artifact(installation, tmp_path):
    project = tmp_path / "project"
    path = project / "sol-fallback-adjudication.json"
    write(path, json.dumps({
        "scope": "targeted_title_or_critical_major",
        "status": "resolved",
        "unresolved_findings": 0,
    }))
    assert strategy_m.fallback_resolved(project, {"sol_fallback"}) is False
    runtime.append_receipt(project, {
        "receipt_id": "fallback",
        "workflow_stage": "sol_fallback",
        "exit_code": 0,
        "outputs": [runtime.file_record(path)],
    })
    assert strategy_m.fallback_resolved(project, {"sol_fallback"}) is True
    write(path, json.dumps({
        "scope": "targeted_title_or_critical_major",
        "status": "needs_human",
        "unresolved_findings": 1,
    }))
    assert strategy_m.fallback_resolved(project, {"sol_fallback"}) is False


def test_term_decisions_accept_mpi_authority_and_detect_stale_context(installation, tmp_path):
    project = tmp_path / "project"
    runtime.begin_project(project, "document")
    source = project / "source.dj"
    term_map = project / "term-map.yaml"
    decisions = project / "term-decisions.json"
    write(source, "三轮体空\n品牌不断被贬值\n")
    write(term_map, json.dumps({"terms": [{
        "source": "三轮体空",
        "preferred": "the emptiness of the three aspects",
    }]}, ensure_ascii=False) + "\n")
    runtime.atomic_json(decisions, {
        "schema_version": 1,
        "source_sha256": runtime.sha256_file(source),
        "items": [{
            "source_term": "三轮体空",
            "candidates": ["the emptiness of the three aspects", "threefold emptiness"],
            "locations": [{
                "line": 1,
                "source_text_sha256": runtime.sha256_bytes("三轮体空".encode("utf-8")),
            }],
            "trigger": "high_risk",
            "mpi_hits": [{"source": "DoT定稿", "zh": "三轮体空", "en": "the emptiness of the three aspects", "loc": "test"}],
            "external_evidence": [],
            "selected": "the emptiness of the three aspects",
            "rationale": "Use the project-final rendering without adding an explanatory gloss.",
            "confidence": "high",
            "scope": "all occurrences",
            "resolution_basis": "mpi_authoritative",
            "status": "frozen",
        }],
    })

    receipt = strategy_m.record_term_decisions(project, source, decisions, term_map)
    assert receipt["summary"]["frozen_count"] == 1
    write(source, "三轮体空（改）\n品牌不断被贬值\n")
    with pytest.raises(runtime.StrategyMError, match="source SHA-256 is stale"):
        strategy_m.validate_term_decisions(source, decisions)


def test_non_mpi_frozen_term_requires_admissible_web_evidence(installation, tmp_path):
    source = tmp_path / "source.dj"
    decisions = tmp_path / "term-decisions.json"
    write(source, "大道大商\n")
    base_item = {
        "source_term": "大商",
        "candidates": ["Great Entrepreneurs", "Great Business"],
        "locations": [{"line": 1, "source_text_sha256": runtime.sha256_bytes("大道大商".encode("utf-8"))}],
        "trigger": "context_ambiguity",
        "mpi_hits": [],
        "external_evidence": [],
        "selected": "Great Entrepreneurs",
        "rationale": "Candidate semantic head based on this article.",
        "confidence": "high",
        "scope": "title system",
        "resolution_basis": "context_and_external_evidence",
        "status": "frozen",
    }
    runtime.atomic_json(decisions, {
        "schema_version": 1,
        "source_sha256": runtime.sha256_file(source),
        "items": [base_item],
    })
    with pytest.raises(runtime.StrategyMError, match="requires external evidence"):
        strategy_m.validate_term_decisions(source, decisions)

    base_item["external_evidence"] = [{
        "source_type": "cbeta",
        "url": "https://cbeta.org/",
        "support": "Canonical context checked; it does not independently settle the coined title.",
        "accepted": False,
    }]
    base_item["confidence"] = "low"
    base_item["status"] = "human_review"
    runtime.atomic_json(decisions, {
        "schema_version": 1,
        "source_sha256": runtime.sha256_file(source),
        "items": [base_item],
    })
    assert strategy_m.validate_term_decisions(source, decisions)["human_review_count"] == 1


def test_source_analysis_reuse_requires_exact_source_hash(installation, tmp_path):
    project = tmp_path / "project"
    runtime.begin_project(project, "document")
    source = project / "source.dj"
    analysis = project / "source-analysis.json"
    write(source, "原文\n")
    runtime.atomic_json(analysis, {
        "source_sha256": runtime.sha256_file(source),
        "model": "deepseek-v4-flash",
        "reasoning_effort": "high",
        "analyses": [],
    })
    receipt = strategy_m.reuse_source_analysis(project, source, analysis)
    assert receipt["workflow_stage"] == "flash_analysis_reuse"
    write(source, "原文已改\n")
    with pytest.raises(runtime.StrategyMError, match="source SHA-256 changed"):
        strategy_m.reuse_source_analysis(project, source, analysis)


def test_disposable_fault_suite_restores_real_installation(installation):
    report = fault_injection.run_fault_tests(installation["root"])

    assert report["status"] == "PASS"
    assert report["restored_installation_verified"] is True
    assert len(report["cases"]) == 6
    assert all(item["blocked"] for item in report["cases"])
    assert runtime.verify_ready()[0]["ready"] is True
