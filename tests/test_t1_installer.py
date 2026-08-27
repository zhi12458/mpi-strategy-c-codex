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
import strategy_t1  # noqa: E402
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


def test_t1_lock_routes_default_to_codex_and_keeps_runtime_separate_from_m():
    lock = json.loads((ROOT / "skills" / "mpi-strategy-t1" / "dependency-lock.json").read_text(encoding="utf-8"))
    assert lock["strategy_id"] == "T1"
    assert lock["workflow_version"] == "1.2.0"
    assert lock["installer_version"] == "1.2.0"
    assert lock["release_ready"] is False
    assert lock["credential_policy"]["deepseek_service"] == "mpi-strategy-t1-deepseek"
    assert lock["omp"]["validated_version"] == "17.3.4"
    assert lock["omp"]["lossless_execution_policy"] == {
        "name": "single-response-no-tools-v1",
        "required_flags": ["-p", "--no-session", "--no-tools", "--hide-thinking"],
        "model_role_change_allowed": False,
        "reasoning_effort_change_allowed": False,
        "workflow_stage_combining_allowed": False,
        "quality_gate_reduction_allowed": False,
        "exact_validated_artifact_reuse_allowed": True,
        "omp_event_count_is_model_call_evidence": False,
    }
    assert "PyYAML>=6,<7" in lock["python"]["pilot_packages"]
    assert lock["models"]["source_analysis"]["reasoning_effort"] == "high"
    assert lock["models"]["translation_and_self_review"]["reasoning_effort"] == "high"
    assert lock["models"]["bilingual_review"]["reasoning_effort"] == "max"
    assert "semantic_restructuring_contract_tests" not in lock["required_gates"]
    assert "semantic_restructuring_contract_tests" in lock["track_policy"][
        "legacy_semantic_restructuring_required_gates"
    ]
    assert "pretranslation_contract_tests" in lock["track_policy"][
        "ai_scale_required_gates"
    ]
    assert lock["track_policy"]["rollback_baseline"] == "T1-OMP 1.0.1"
    assert lock["track_policy"]["quality_mainline"] == "T1-Codex 1.1.0"
    assert lock["track_policy"]["production_skill"] == "mpi-strategy-t1-codex"
    assert lock["track_policy"]["english_owner"] == (
        "current Codex task configured as GPT-5.6-Sol/high"
    )
    assert lock["track_policy"]["full_pretranslation_default"] is False
    assert lock["default_routing"]["enabled"] is True
    assert lock["default_routing"]["selected_skill"] == "mpi-strategy-t1-codex"
    assert lock["models"]["translation_and_self_review"]["production_default"] is False
    production = json.loads(
        (ROOT / "skills" / "mpi-strategy-t1" / "references" / "production-lock.json").read_text(
            encoding="utf-8"
        )
    )
    assert production["installer_runtime"]["installer_version"] == "1.2.0"
    assert production["installer_runtime"]["required_before_t1_codex_external_roles"] is True
    assert "base_t1_installer_ready_true" in production["required_gates"]
    assert production["default_routing"]["selected_skill"] == "mpi-strategy-t1-codex"
    assert production["workflow_modes"]["t1_codex_quality"]["production_default"] is True
    assert production["workflow_modes"]["t1_omp_rollback"]["production_default"] is False
    assert production["workflow_modes"]["t1_2_ai_scale_pretranslation"]["production_default"] is False
    assert "model substitution" in production["lossless_omp_execution"][
        "forbidden_optimizations"
    ]
    assert "quality gate removal" in production["lossless_omp_execution"][
        "forbidden_optimizations"
    ]
    assert "post-concision regression removal" in production["lossless_omp_execution"][
        "forbidden_optimizations"
    ]


def test_manifest_covers_new_t1_runtime_files():
    report = t1_runtime.verify_manifest()
    for relative in (
        "dependency-lock.json",
        "references/installation.md",
        "references/readiness.md",
        "references/pretranslation-tracks.md",
        "references/semantic-bridge.md",
        "scripts/artifact_reuse.py",
        "scripts/pretranslation.py",
        "scripts/semantic_bridge.py",
        "scripts/strategy_t1.py",
        "scripts/t1_runtime.py",
        "scripts/usage_metrics.py",
    ):
        assert relative in report["files"]


def test_t1_pretranslation_is_explicit_and_default_adopts_only_risk_controls():
    skill = ROOT / "skills" / "mpi-strategy-t1"
    workflow = (skill / "references" / "workflow.md").read_text(encoding="utf-8")
    contract = (skill / "references" / "pretranslation-tracks.md").read_text(encoding="utf-8")
    production = json.loads(
        (skill / "references" / "production-lock.json").read_text(encoding="utf-8")
    )
    assert "Explicit T1-OMP rollback" in workflow
    assert "Explicit T1.2 pretranslation experiments" in workflow
    assert "default T1-Codex" in workflow
    assert "Chinese remains authoritative" in contract
    assert "AI may surface a possible conflict" in contract
    assert production["source_authority"]["sole_semantic_authority"] is True
    assert production["workflow_modes"]["t1_2_human_quality_pretranslation"][
        "production_default"
    ] is False
    assert production["workflow_modes"]["t1_2_ai_scale_pretranslation"][
        "production_default"
    ] is False
    adopted = production["t1_1_2_default_adoption"]["adopted_into_t1_codex"]
    experimental = production["t1_1_2_default_adoption"]["kept_experimental"]
    assert "high-risk-only Chinese clarification and English structure planning" in adopted
    assert "fresh post-concision bidirectional semantic regression" in adopted
    assert "mandatory full-document Sol semantic restructuring" in experimental
    assert production["scoring_policy"]["primary_judges"] == (
        "blinded human bilingual Buddhist/Dharma reviewers"
    )


def test_current_and_legacy_semantic_cli_routes_remain_distinct():
    current = strategy_t1.parser().parse_args(
        [
            "validate-semantic-restructuring",
            "--project",
            "/tmp/project",
            "--accepted-decisions",
            "/tmp/decisions.json",
        ]
    )
    historical = strategy_t1.parser().parse_args(
        ["validate-semantic-artifacts", "--project", "/tmp/project", "--stage", "risk"]
    )
    assert current.command == "validate-semantic-restructuring"
    assert current.accepted_decisions == Path("/tmp/decisions.json")
    assert historical.command == "validate-semantic-artifacts"
    assert historical.stage == "risk"


def test_specialized_semantic_cli_accepts_explicit_decision_file():
    restructuring = strategy_t1.parser().parse_args(
        [
            "run-semantic-restructuring",
            "--project",
            "/tmp/project",
            "--accepted-decisions",
            "/tmp/decisions.json",
        ]
    )
    translation = strategy_t1.parser().parse_args(
        [
            "run-translation-with-restructuring",
            "--project",
            "/tmp/project",
            "--accepted-decisions",
            "/tmp/decisions.json",
        ]
    )
    assert restructuring.accepted_decisions == Path("/tmp/decisions.json")
    assert translation.accepted_decisions == Path("/tmp/decisions.json")


def test_specialized_semantic_cli_forwards_explicit_decision_file(monkeypatch):
    seen = {}
    monkeypatch.setattr(strategy_t1, "verify_ready", lambda **_kwargs: {"ready": True})

    def fake_run(project, **kwargs):
        seen["project"] = project
        seen.update(kwargs)
        return {"status": "PASS"}

    monkeypatch.setattr(strategy_t1, "run_semantic_restructuring", fake_run)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "strategy_t1.py",
            "run-semantic-restructuring",
            "--project",
            "/tmp/project",
            "--accepted-decisions",
            "/tmp/decisions.json",
        ],
    )
    assert strategy_t1.main() == 0
    assert seen["accepted_decisions"] == Path("/tmp/decisions.json")


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
    assert captured["command"][1:5] == list(omp_runtime.LOSSLESS_OMP_FLAGS)
    assert "--continue" not in captured["command"]
    assert "--resume" not in captured["command"]
    assert captured["env_keys"] == ["DEEPSEEK_API_KEY"]
    assert receipt["secret_in_arguments"] is False
    assert receipt["execution_profile"] == {
        "name": "single-response-no-tools-v1",
        "interaction": "single_response",
        "session_saved": False,
        "tools_enabled": False,
        "workflow_stage_combining_allowed": False,
    }


def test_omp_role_blocks_if_lossless_profile_drifts(monkeypatch, tmp_path):
    lock = json.loads(
        (ROOT / "skills" / "mpi-strategy-t1" / "dependency-lock.json").read_text(
            encoding="utf-8"
        )
    )
    lock["omp"]["lossless_execution_policy"]["required_flags"] = ["-p"]
    monkeypatch.setattr(omp_runtime, "load_lock", lambda: lock)

    def must_not_run(*_args, **_kwargs):
        raise AssertionError("OMP must not run under a drifted execution profile")

    monkeypatch.setattr(omp_runtime, "run", must_not_run)
    with pytest.raises(t1_runtime.StrategyT1Error, match="profile is missing or changed"):
        omp_runtime.run_role(
            "translation_and_self_review", ["public prompt"], cwd=tmp_path
        )


def test_run_file_binds_inputs_and_publishes_one_new_artifact(monkeypatch, tmp_path):
    prompt = tmp_path / "stage.md"
    source = tmp_path / "source.dj"
    target = tmp_path / "input-target.dj"
    output = tmp_path / "stage.raw.json"
    prompt.write_text("complete stage prompt\n", encoding="utf-8")
    source.write_text("原文\n", encoding="utf-8")
    target.write_text("Draft.\n", encoding="utf-8")

    monkeypatch.setattr(
        omp_runtime,
        "run_role",
        lambda role, messages, **_kwargs: (
            b'{"complete": true}\n',
            {"role": role, "messages": messages},
        ),
    )
    receipt = omp_runtime.run_file(
        "translation_and_self_review",
        prompt,
        output,
        cwd=tmp_path,
        bound_inputs=[source, target],
        workflow_stage="review_application_round_1",
    )

    assert output.read_bytes() == b'{"complete": true}\n'
    assert receipt["workflow_stage"] == "review_application_round_1"
    assert [item["name"] for item in receipt["inputs"]] == [
        "prompt-file",
        "bound-input-01:source.dj",
        "bound-input-02:input-target.dj",
    ]
    assert receipt["prompt_sha256"] == t1_runtime.sha256_file(prompt)
    assert receipt["output_sha256"] == t1_runtime.sha256_file(output)


def test_run_file_refuses_existing_output_before_model_call(monkeypatch, tmp_path):
    prompt = tmp_path / "stage.md"
    output = tmp_path / "stage.raw.json"
    prompt.write_text("prompt\n", encoding="utf-8")
    output.write_text("preserve\n", encoding="utf-8")

    def must_not_run(*_args, **_kwargs):
        raise AssertionError("model must not run")

    monkeypatch.setattr(omp_runtime, "run_role", must_not_run)
    with pytest.raises(t1_runtime.StrategyT1Error, match="refusing to overwrite"):
        omp_runtime.run_file(
            "translation_and_self_review", prompt, output, cwd=tmp_path
        )
    assert output.read_text(encoding="utf-8") == "preserve\n"


def test_run_file_blocks_input_mutation_and_empty_output(monkeypatch, tmp_path):
    prompt = tmp_path / "stage.md"
    source = tmp_path / "source.dj"
    output = tmp_path / "stage.raw.json"
    prompt.write_text("prompt\n", encoding="utf-8")
    source.write_text("原文\n", encoding="utf-8")

    def mutate(*_args, **_kwargs):
        source.write_text("原文已变\n", encoding="utf-8")
        return b"valid-looking output\n", {}

    monkeypatch.setattr(omp_runtime, "run_role", mutate)
    with pytest.raises(t1_runtime.StrategyT1Error, match="input changed"):
        omp_runtime.run_file(
            "translation_and_self_review",
            prompt,
            output,
            cwd=tmp_path,
            bound_inputs=[source],
        )
    assert not output.exists()

    source.write_text("原文\n", encoding="utf-8")
    monkeypatch.setattr(
        omp_runtime, "run_role", lambda *_args, **_kwargs: (b" \n", {})
    )
    with pytest.raises(t1_runtime.StrategyT1Error, match="empty artifact"):
        omp_runtime.run_file(
            "translation_and_self_review",
            prompt,
            output,
            cwd=tmp_path,
            bound_inputs=[source],
        )
    assert not output.exists()


def test_run_model_parser_accepts_lossless_evidence_bindings(tmp_path):
    args = strategy_t1.parser().parse_args(
        [
            "run-model",
            "--role",
            "translation_and_self_review",
            "--prompt-file",
            str(tmp_path / "prompt.md"),
            "--bind-input",
            str(tmp_path / "source.dj"),
            "--bind-input",
            str(tmp_path / "target.dj"),
            "--workflow-stage",
            "concision_and_chinese_recheck",
            "--output",
            str(tmp_path / "raw.json"),
        ]
    )
    assert args.bind_input == [tmp_path / "source.dj", tmp_path / "target.dj"]
    assert args.workflow_stage == "concision_and_chinese_recheck"


def test_candidate_install_refuses_before_release_promotion():
    with pytest.raises(t1_runtime.StrategyT1Error, match="not release-ready"):
        t1_bootstrap.install(confirm_public_smoke=False)


def test_baseline_ready_is_not_blocked_by_optional_pilot_contract(monkeypatch, tmp_path):
    lock = json.loads(
        (ROOT / "skills" / "mpi-strategy-t1" / "dependency-lock.json").read_text(
            encoding="utf-8"
        )
    )
    fault = tmp_path / "fault.json"
    smoke = tmp_path / "smoke.json"
    fault.write_text("{}\n", encoding="utf-8")
    smoke.write_text("{}\n", encoding="utf-8")
    mpi = tmp_path / "repos" / "mpi-translations"
    toolkit = mpi / "toolkit"
    ready = {
        "ready": True,
        "strategy_id": lock["strategy_id"],
        "workflow_version": lock["workflow_version"],
        "installer_version": lock["installer_version"],
        "skill_manifest": {"sha256": "manifest"},
        "omp": {"version": lock["omp"]["validated_version"]},
        "mpi_translations": {"absolute_path": str(mpi)},
        "translation_toolkit": {"absolute_path": str(toolkit)},
        "fault_injection": {
            "status": "PASS",
            "path": str(fault),
            "sha256": t1_runtime.sha256_file(fault),
        },
        "smoke_test": {
            "status": "PASS",
            "path": str(smoke),
            "sha256": t1_runtime.sha256_file(smoke),
        },
        "semantic_restructuring_contracts": {
            "status": "BLOCKED",
            "path": None,
            "sha256": None,
        },
        "pretranslation_contracts": {
            "status": "BLOCKED",
            "path": None,
            "sha256": None,
        },
    }
    (tmp_path / t1_runtime.READY_NAME).write_text(
        json.dumps(ready), encoding="utf-8"
    )
    monkeypatch.setattr(t1_bootstrap, "load_lock", lambda: lock)
    monkeypatch.setattr(t1_bootstrap, "verify_manifest", lambda: {"sha256": "manifest"})
    monkeypatch.setattr(
        t1_bootstrap, "require_dependencies", lambda _lock: {"pyyaml": True}
    )
    monkeypatch.setattr(
        t1_bootstrap,
        "omp_report",
        lambda _lock: {"version": lock["omp"]["validated_version"]},
    )
    monkeypatch.setattr(t1_bootstrap, "load_personal_confirmation", lambda _root: {})
    monkeypatch.setattr(t1_bootstrap, "deepseek_credential_present", lambda _lock: True)
    monkeypatch.setattr(t1_bootstrap, "verify_repo", lambda *_args, **_kwargs: {})
    monkeypatch.setattr(t1_bootstrap, "run_doctor", lambda _repo: {})

    assert t1_bootstrap.verify_ready(tmp_path)["ready"] is True
    with pytest.raises(t1_runtime.StrategyT1Error, match="capability is unavailable"):
        t1_bootstrap.verify_ready(tmp_path, require_semantic_restructuring=True)
    with pytest.raises(t1_runtime.StrategyT1Error, match="pretranslation-track capability"):
        t1_bootstrap.verify_ready(tmp_path, require_pretranslation=True)

    monkeypatch.setattr(
        t1_bootstrap, "require_dependencies", lambda _lock: {"pyyaml": False}
    )
    assert t1_bootstrap.verify_ready(tmp_path)["ready"] is True
    with pytest.raises(t1_runtime.StrategyT1Error, match="requires Python PyYAML"):
        t1_bootstrap.verify_ready(tmp_path, require_semantic_restructuring=True)


def test_unexpected_optional_pilot_contract_failure_does_not_abort_baseline(
    monkeypatch, tmp_path
):
    import semantic_bridge

    def fail(_root):
        raise ValueError("pilot-only failure")

    monkeypatch.setattr(semantic_bridge, "run_contract_tests", fail)
    report = t1_bootstrap.optional_semantic_contracts(
        tmp_path, {"pyyaml": True}
    )
    assert report == {
        "status": "BLOCKED",
        "error": "ValueError: pilot-only failure",
    }
    assert t1_bootstrap.optional_semantic_contracts(
        tmp_path, {"pyyaml": False}
    )["status"] == "BLOCKED"


def test_unexpected_pretranslation_contract_failure_does_not_abort_baseline(
    monkeypatch, tmp_path
):
    import pretranslation

    monkeypatch.setattr(
        pretranslation,
        "run_contract_tests",
        lambda _root: (_ for _ in ()).throw(ValueError("track-only failure")),
    )
    assert t1_bootstrap.optional_pretranslation_contracts(tmp_path) == {
        "status": "BLOCKED",
        "error": "ValueError: track-only failure",
    }


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
