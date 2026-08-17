from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest


SCRIPTS = Path(__file__).parents[1] / "skills" / "mpi-strategy-c" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import bootstrap  # noqa: E402
import fault_injection  # noqa: E402
import runtime  # noqa: E402
import strategy_c  # noqa: E402


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


def make_repo(path: Path, origin: str) -> str:
    command(path.parent, "git", "init", str(path))
    command(path, "git", "config", "core.autocrlf", "false")
    command(path, "git", "remote", "add", "origin", origin)
    return origin


def commit(path: Path, message: str) -> str:
    command(path, "git", "add", "-A")
    command(path, "git", "commit", "-m", message)
    return command(path, "git", "rev-parse", "HEAD")


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
        "skill_version": "test",
        "release_ready": True,
        "mpi_translations": {
            "origin": mpi_origin,
            "expected_sha": mpi_sha,
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
            "translation": {"provider": "openai-codex", "model": "gpt-5.6-sol", "reasoning_effort": "high"},
            "review": {"provider": "deepseek", "model": "deepseek-v4-pro", "reasoning_effort": "max"},
        },
    }
    lock_path = tmp_path / "dependency-lock.json"
    write(lock_path, json.dumps(lock))
    monkeypatch.setattr(runtime, "LOCK_PATH", lock_path)
    monkeypatch.setattr(bootstrap, "load_lock", lambda: runtime.load_json(lock_path))
    monkeypatch.setattr(strategy_c, "load_lock", lambda: runtime.load_json(lock_path))
    monkeypatch.setenv("MPI_STRATEGY_C_ROOT", str(root))

    mpi_info = runtime.verify_repo(mpi, lock["mpi_translations"])
    toolkit_info = runtime.verify_repo(toolkit, lock["translation_toolkit"])
    ready = {
        "schema_version": 1,
        "ready": True,
        "skill_version": "test",
        "mpi_translations": mpi_info,
        "translation_toolkit": toolkit_info,
    }
    runtime.atomic_json(root / "READY.json", ready)
    return {"root": root, "mpi": mpi, "toolkit": toolkit, "lock": lock, "lock_path": lock_path}


def test_valid_installation_generates_complete_instruction_receipt(installation, tmp_path):
    ready, mpi, toolkit = runtime.verify_ready()
    assert ready["ready"] is True
    assert mpi["doctor_exit_code"] == toolkit["doctor_exit_code"] == 0

    receipt = runtime.begin_project(tmp_path / "project", "document")

    assert len(receipt["instructions"]) == 5
    assert Path(receipt["instructions"][0]["absolute_path"]).name == "AGENTS.md"


def test_missing_mpi_agents_blocks_until_restored(installation):
    path = installation["mpi"] / "AGENTS.md"
    original = path.read_bytes()
    path.unlink()
    with pytest.raises(runtime.StrategyCError):
        runtime.verify_ready()
    path.write_bytes(original)
    assert runtime.verify_ready()[0]["ready"] is True


def test_wrong_origin_blocks_until_restored(installation):
    mpi = installation["mpi"]
    command(mpi, "git", "remote", "set-url", "origin", "https://example.invalid/wrong")
    with pytest.raises(runtime.StrategyCError, match="origin mismatch"):
        runtime.verify_ready()
    command(mpi, "git", "remote", "set-url", "origin", installation["lock"]["mpi_translations"]["origin"])
    assert runtime.verify_ready()[0]["ready"] is True


def test_wrong_mpi_sha_blocks_until_exact_commit_is_restored(installation):
    mpi = installation["mpi"]
    write(mpi / "unexpected.txt", "new commit\n")
    commit(mpi, "unexpected")
    with pytest.raises(runtime.StrategyCError, match="SHA mismatch"):
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
    with pytest.raises(runtime.StrategyCError):
        runtime.verify_ready()
    command(toolkit, "git", "checkout", "--", relative)
    assert runtime.verify_ready()[0]["ready"] is True


def test_missing_toolkit_and_failing_doctor_both_block(installation, monkeypatch):
    toolkit = installation["toolkit"]
    moved = toolkit.with_name("toolkit.missing")
    toolkit.rename(moved)
    with pytest.raises(runtime.StrategyCError):
        runtime.verify_ready()
    moved.rename(toolkit)
    monkeypatch.setenv("FAIL_FAKE_DOCTOR", "1")
    with pytest.raises(runtime.StrategyCError, match="doctor failed"):
        runtime.verify_ready()
    monkeypatch.delenv("FAIL_FAKE_DOCTOR")
    assert runtime.verify_ready()[0]["ready"] is True


def test_unreleased_lock_blocks_even_forged_ready(installation):
    lock = runtime.load_json(installation["lock_path"])
    lock["release_ready"] = False
    write(installation["lock_path"], json.dumps(lock))
    with pytest.raises(runtime.StrategyCError, match="release lock"):
        runtime.verify_ready()
    with pytest.raises(runtime.StrategyCError, match="official upstream"):
        bootstrap.install(Path("missing.bin"), install_missing=False)


def test_tool_call_is_receipted_with_repository_and_hashes(installation, tmp_path):
    project = tmp_path / "project"
    runtime.begin_project(project, "document")
    source = tmp_path / "input.txt"
    output = project / "source.dj"
    write(source, "原文\n")

    receipt = strategy_c.run_audited_tool(
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
    for stage in sorted(strategy_c.DOCUMENT_STAGES | strategy_c.MODEL_STAGES):
        runtime.append_receipt(project, {"receipt_id": stage, "workflow_stage": stage, "exit_code": 0, "outputs": [output]})

    assert strategy_c.finalize(project, "document")["pipeline_complete"] is True
    write(artifact, "stale replacement\n")
    with pytest.raises(runtime.StrategyCError):
        strategy_c.finalize(project, "document")
    assert runtime.load_json(project / "MANIFEST.json")["pipeline_complete"] is False


def test_forged_old_qa_report_fails_freshness_chain(installation, tmp_path):
    project = tmp_path / "project"
    runtime.begin_project(project, "document")
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
    for stage in sorted(strategy_c.DOCUMENT_STAGES | strategy_c.MODEL_STAGES):
        runtime.append_receipt(project, {"receipt_id": stage, "workflow_stage": stage, "exit_code": 0, "outputs": outputs})
    assert strategy_c.finalize(project, "document")["pipeline_complete"] is True

    write(qa_path, json.dumps({"status": "PASS", "run": "forged-old"}))
    with pytest.raises(runtime.StrategyCError):
        strategy_c.finalize(project, "document")
    manifest = runtime.load_json(project / "MANIFEST.json")
    assert str(qa_path) in manifest["stale_or_missing_artifacts"]


def test_secret_arguments_are_rejected():
    with pytest.raises(runtime.StrategyCError):
        runtime.reject_secret_arguments(["--api-key=sk-test"])


def test_disposable_fault_suite_restores_real_installation(installation):
    report = fault_injection.run_fault_tests(installation["root"])

    assert report["status"] == "PASS"
    assert report["restored_installation_verified"] is True
    assert len(report["cases"]) == 6
    assert all(item["blocked"] for item in report["cases"])
    assert runtime.verify_ready()[0]["ready"] is True
