from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest


ROOT = Path(__file__).parents[1]
SCRIPTS = ROOT / "skills" / "mpi-strategy-t1" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import credential_store  # noqa: E402
import omp_runtime  # noqa: E402
import t1_bootstrap  # noqa: E402
import t1_runtime  # noqa: E402
import t1_smoke_test  # noqa: E402


GIT_ENV = {
    **os.environ,
    "GIT_AUTHOR_NAME": "T1 Test",
    "GIT_AUTHOR_EMAIL": "t1-test@example.invalid",
    "GIT_COMMITTER_NAME": "T1 Test",
    "GIT_COMMITTER_EMAIL": "t1-test@example.invalid",
}


def command(cwd: Path, *args: str) -> str:
    result = subprocess.run(args, cwd=cwd, env=GIT_ENV, text=True, capture_output=True, check=False)
    assert result.returncode == 0, result.stderr
    return result.stdout.strip()


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")


def make_repo(path: Path, origin: str, files: dict[str, str]) -> str:
    path.mkdir(parents=True)
    command(path, "git", "init")
    command(path, "git", "config", "core.autocrlf", "false")
    command(path, "git", "remote", "add", "origin", origin)
    for relative, text in files.items():
        write(path / relative, text)
    command(path, "git", "add", "-A")
    command(path, "git", "commit", "-m", "fixture")
    return command(path, "git", "rev-parse", "HEAD")


def test_t1_lock_keeps_workflow_identity_and_runtime_separate_from_m():
    lock = json.loads((ROOT / "skills" / "mpi-strategy-t1" / "dependency-lock.json").read_text(encoding="utf-8"))
    assert lock["strategy_id"] == "T1"
    assert lock["workflow_version"] == "1.0.1"
    assert lock["installer_version"] == "1.0.0"
    assert lock["credential_policy"]["deepseek_service"] == "mpi-strategy-t1-deepseek"
    assert lock["omp"]["validated_version"] == "17.3.4"
    assert lock["models"]["source_analysis"]["reasoning_effort"] == "high"
    assert lock["models"]["translation_and_self_review"]["reasoning_effort"] == "high"
    assert lock["models"]["bilingual_review"]["reasoning_effort"] == "max"
    assert lock["default_routing"]["enabled"] is True
    production = json.loads(
        (ROOT / "skills" / "mpi-strategy-t1" / "references" / "production-lock.json").read_text(
            encoding="utf-8"
        )
    )
    assert production["installer_runtime"]["installer_version"] == "1.0.0"
    assert production["installer_runtime"]["required_before_production_execution"] is True
    assert "t1_installer_ready_true" in production["required_gates"]


def test_manifest_covers_new_t1_runtime_files():
    report = t1_runtime.verify_manifest()
    for relative in (
        "dependency-lock.json",
        "references/installation.md",
        "references/readiness.md",
        "scripts/strategy_t1.py",
        "scripts/t1_runtime.py",
    ):
        assert relative in report["files"]


def test_secret_flags_are_rejected_before_process_execution():
    for argument in ("--api-key", "--api-key=secret", "DEEPSEEK_API_KEY=value"):
        with pytest.raises(t1_runtime.StrategyT1Error, match="credentials are forbidden"):
            t1_runtime.reject_secret_arguments(("omp", argument))


def test_credential_normalization_strips_bearer_without_logging_value():
    assert credential_store.normalize("  Bearer sk-test-value-1234567890  ") == "sk-test-value-1234567890"
    source = (SCRIPTS / "credential_store.py").read_text(encoding="utf-8")
    assert "show=\"*\"" in source
    assert "set_password" in source


def test_omp_report_requires_exact_version_and_all_locked_efforts(monkeypatch):
    lock = json.loads((ROOT / "skills" / "mpi-strategy-t1" / "dependency-lock.json").read_text(encoding="utf-8"))
    models = {
        "models": [
            {
                "selector": spec["selector"],
                "thinking": [spec["reasoning_effort"]],
                "contextWindow": 1000,
            }
            for spec in lock["models"].values()
        ]
    }

    monkeypatch.setattr(t1_runtime, "executable", lambda _name: "/fake/omp")

    def fake_run(command, _cwd, **_kwargs):
        output = b"omp/17.3.4\n" if command[1] == "--version" else json.dumps(models).encode("utf-8")
        return SimpleNamespace(returncode=0, stdout=output, stderr=b"")

    monkeypatch.setattr(t1_runtime, "run", fake_run)
    report = t1_runtime.omp_report(lock)
    assert report["version"] == "17.3.4"
    assert set(report["models"]) == set(lock["models"])


def test_omp_report_blocks_version_drift(monkeypatch):
    lock = json.loads((ROOT / "skills" / "mpi-strategy-t1" / "dependency-lock.json").read_text(encoding="utf-8"))
    monkeypatch.setattr(t1_runtime, "executable", lambda _name: "/fake/omp")
    monkeypatch.setattr(
        t1_runtime,
        "run",
        lambda *_args, **_kwargs: SimpleNamespace(returncode=0, stdout=b"omp/17.4.0\n", stderr=b""),
    )
    with pytest.raises(t1_runtime.StrategyT1Error, match="version mismatch"):
        t1_runtime.omp_report(lock)


def test_omp_report_blocks_failed_model_catalog(monkeypatch):
    lock = json.loads((ROOT / "skills" / "mpi-strategy-t1" / "dependency-lock.json").read_text(encoding="utf-8"))
    monkeypatch.setattr(t1_runtime, "executable", lambda _name: "/fake/omp")
    calls = iter(
        (
            SimpleNamespace(returncode=0, stdout=b"omp/17.3.4\n", stderr=b""),
            SimpleNamespace(returncode=1, stdout=b"{}", stderr=b"catalog unavailable"),
        )
    )
    monkeypatch.setattr(t1_runtime, "run", lambda *_args, **_kwargs: next(calls))
    with pytest.raises(t1_runtime.StrategyT1Error, match="catalog lookup failed"):
        t1_runtime.omp_report(lock)


def test_omp_role_uses_locked_selector_and_never_puts_secret_in_arguments(monkeypatch, tmp_path):
    lock = json.loads((ROOT / "skills" / "mpi-strategy-t1" / "dependency-lock.json").read_text(encoding="utf-8"))
    captured = {}
    monkeypatch.setattr(omp_runtime, "load_lock", lambda: lock)
    monkeypatch.setattr(omp_runtime, "deepseek_environment", lambda _lock: {"DEEPSEEK_API_KEY": "secret-value"})

    def fake_run(command, _cwd, env=None, **_kwargs):
        captured["command"] = list(command)
        captured["env_keys"] = sorted(env or {})
        if env is not None:
            env.clear()
        return SimpleNamespace(returncode=0, stdout=b"T1_FLASH_OK\n", stderr=b"")

    monkeypatch.setattr(omp_runtime, "run", fake_run)
    _, receipt = omp_runtime.run_role("source_analysis", ["public prompt"], cwd=tmp_path)
    joined = " ".join(captured["command"])
    assert "secret-value" not in joined
    assert "--api-key" not in joined
    assert "deepseek/deepseek-v4-flash" in captured["command"]
    assert captured["env_keys"] == ["DEEPSEEK_API_KEY"]
    assert receipt["secret_in_arguments"] is False


def test_install_refuses_live_calls_without_explicit_confirmation():
    with pytest.raises(t1_runtime.StrategyT1Error, match="confirm-public-smoke"):
        t1_bootstrap.install(confirm_public_smoke=False)


@pytest.mark.parametrize(
    ("system", "environment", "suffix"),
    (
        ("Darwin", {}, ("Library", "Application Support", "MPI-Strategy-T1")),
        ("Windows", {"LOCALAPPDATA": "/tmp/t1-local-app-data"}, ("t1-local-app-data", "MPI-Strategy-T1")),
        ("Linux", {"XDG_DATA_HOME": "/tmp/t1-xdg-data"}, ("t1-xdg-data", "mpi-strategy-t1")),
    ),
)
def test_managed_root_is_strategy_specific_on_supported_platforms(
    monkeypatch, system, environment, suffix
):
    monkeypatch.delenv("MPI_STRATEGY_T1_ROOT", raising=False)
    monkeypatch.delenv("LOCALAPPDATA", raising=False)
    monkeypatch.delenv("XDG_DATA_HOME", raising=False)
    for key, value in environment.items():
        monkeypatch.setenv(key, value)
    monkeypatch.setattr(t1_runtime.platform, "system", lambda: system)
    assert t1_runtime.managed_root().parts[-len(suffix):] == suffix


def test_clone_locked_keeps_https_filter_and_canonical_origin(tmp_path, monkeypatch):
    calls = []
    monkeypatch.setattr(t1_bootstrap, "git_checked", lambda command, cwd: calls.append((command, cwd)))
    t1_bootstrap.clone_locked(
        "https://example.invalid/source.git",
        tmp_path / "destination",
        "1" * 40,
        "https://example.invalid/canonical.git",
    )
    assert "--filter=blob:none" in calls[0][0]
    assert "--local" not in calls[0][0]
    assert calls[-1][0][-2:] == ("origin", "https://example.invalid/canonical.git")


def test_verify_repo_blocks_tamper_and_wrong_origin(tmp_path):
    origin = "https://example.invalid/t1-fixture.git"
    repo = tmp_path / "repo"
    sha = make_repo(repo, origin, {"AGENTS.md": "rules\n", "required.txt": "value\n"})
    spec = {"origin": origin, "expected_sha": sha, "required_files": ["AGENTS.md", "required.txt"]}
    record = t1_runtime.verify_repo(repo, spec)
    assert record["git_sha"] == sha
    write(repo / "required.txt", "tampered\n")
    with pytest.raises(t1_runtime.StrategyT1Error, match="not clean"):
        t1_runtime.verify_repo(repo, spec)
    command(repo, "git", "restore", "required.txt")
    command(repo, "git", "remote", "set-url", "origin", "https://example.invalid/wrong")
    with pytest.raises(t1_runtime.StrategyT1Error, match="origin mismatch"):
        t1_runtime.verify_repo(repo, spec)


def test_public_smoke_uses_only_fixture_and_all_three_roles(tmp_path, monkeypatch):
    toolkit = tmp_path / "toolkit"
    fixture = toolkit / "examples" / "minimal-article"
    for name in (
        "source.dj",
        "target.dj",
        "translation-project.yaml",
        "term-map.yaml",
        "source-analysis.json",
        "review-findings.jsonl",
        "semantic-review.json",
    ):
        write(fixture / name, "public fixture\n")
    generic = """#!/usr/bin/env python3
import json, pathlib, sys
name = pathlib.Path(sys.argv[0]).name
if name == 'gen-bilingual.py':
    pathlib.Path(sys.argv[sys.argv.index('--output') + 1]).write_text('public bilingual\\n')
elif name == 'check-translation.py':
    pathlib.Path(sys.argv[sys.argv.index('--output') + 1]).write_text('{}\\n')
elif name == 'dj2docx.py':
    pathlib.Path(sys.argv[2]).write_bytes(b'PK-public-docx')
elif name == 'check-docx.py':
    pathlib.Path(sys.argv[sys.argv.index('--output') + 1]).write_text('{}\\n')
"""
    for name in ("gen-bilingual.py", "check-translation.py", "dj2docx.py", "check-docx.py"):
        write(toolkit / "scripts" / name, generic)
    lock = json.loads((ROOT / "skills" / "mpi-strategy-t1" / "dependency-lock.json").read_text(encoding="utf-8"))
    seen = []

    def fake_role(role, messages, **_kwargs):
        seen.append(role)
        marker = lock["smoke_policy"]["markers"][role]
        return marker.encode("utf-8"), {"role": role, "exit_code": 0}

    monkeypatch.setattr(t1_smoke_test, "run_role", fake_role)
    root = tmp_path / "managed"
    root.mkdir()
    report = t1_smoke_test.run_smoke_test(root, toolkit, lock)
    assert report["status"] == "PASS"
    assert set(seen) == set(lock["models"])
    saved = json.loads((root / "smoke-test-report.json").read_text(encoding="utf-8"))
    assert saved["contains_private_content"] is False
    assert "secret" not in json.dumps(saved).casefold()


def test_install_prompt_forbids_secret_chat_and_requires_ready_true():
    prompt = (ROOT / "INSTALL_PROMPT-T1.zh-CN.md").read_text(encoding="utf-8")
    assert "不能让我把 Key 发到 Codex 对话" in prompt
    assert "Personal account" in prompt
    assert "ready=true" in prompt
    assert "t1-v1.0.1-installer-1.0.0" in prompt
    assert "--repo zhi12458/mpi-strategy-c-codex" in prompt
    assert "--path skills/mpi-strategy-t1" in prompt
    assert "--ref t1-v1.0.1-installer-1.0.0" in prompt
