from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).parents[1]
SCRIPTS = ROOT / "skills" / "mpi-strategy-t1" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import omp_runtime  # noqa: E402
from t1_runtime import StrategyT1Error  # noqa: E402


@pytest.fixture(autouse=True)
def deterministic_prompt_contract(monkeypatch):
    monkeypatch.setattr(
        omp_runtime,
        "semantic_prompt_contract",
        lambda _project: {"contract": "fixture"},
    )
    monkeypatch.setattr(
        omp_runtime,
        "hydrate_semantic_proposal",
        lambda _project, proposal, **_kwargs: proposal,
    )


def digest(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def hydrated_bytes(value: bytes) -> bytes:
    return (
        json.dumps(json.loads(value), ensure_ascii=False, indent=2, sort_keys=True)
        + "\n"
    ).encode("utf-8")


def project_inputs(project: Path) -> dict[str, bytes]:
    values = {
        "source.dj": "原始中文。\n".encode(),
        "translation-project.yaml": "project_id: fixture\n".encode(),
        "source-analysis.json": json.dumps(
            {"source_sha256": "fixture", "paragraphs": []}
        ).encode(),
        "term-map.yaml": "terms: []\n".encode(),
    }
    for name, value in values.items():
        (project / name).write_bytes(value)
    return values


def model_receipt() -> dict:
    return {
        "role": "translation_and_self_review",
        "provider": "openai-codex",
        "model": "gpt-5.6-sol",
        "reasoning_effort": "high",
    }


def test_semantic_restructuring_uses_four_real_files_validates_temp_and_binds_hashes(
    tmp_path, monkeypatch
):
    values = project_inputs(tmp_path)
    artifact = json.dumps({"schema_version": 2, "records": []}).encode()
    hydrated = hydrated_bytes(artifact)
    captured: dict = {}

    def fake_role(role, messages, *, cwd, timeout):
        captured.update(role=role, messages=messages, cwd=cwd, timeout=timeout)
        return artifact, model_receipt()

    def fake_validate(project, *, stage, artifact_path, **kwargs):
        captured.update(
            validation_project=project,
            validation_stage=stage,
            validation_path=artifact_path,
            validation_bytes=artifact_path.read_bytes(),
            validation_kwargs=kwargs,
        )
        assert artifact_path.name.startswith(".semantic-restructuring.json.")
        assert not (tmp_path / "semantic-restructuring.json").exists()
        return {"status": "PASS", "warnings": []}

    def fake_hydrate(project, proposal, **kwargs):
        captured["hydration_project"] = project
        captured["proposal"] = proposal
        captured["hydration_kwargs"] = kwargs
        return proposal

    monkeypatch.setattr(omp_runtime, "run_role", fake_role)
    monkeypatch.setattr(omp_runtime, "hydrate_semantic_proposal", fake_hydrate)
    monkeypatch.setattr(omp_runtime, "validate_semantic_project", fake_validate)
    receipt = omp_runtime.run_semantic_restructuring(tmp_path, timeout=97)

    output = tmp_path / "semantic-restructuring.json"
    assert output.read_bytes() == hydrated
    assert captured["role"] == "translation_and_self_review"
    assert captured["cwd"] == tmp_path.resolve()
    assert captured["timeout"] == 97
    assert captured["messages"][1:5] == [
        f"@{(tmp_path / name).resolve()}"
        for name in (
            "source.dj",
            "translation-project.yaml",
            "source-analysis.json",
            "term-map.yaml",
        )
    ]
    assert len(captured["messages"]) == 6
    assert captured["messages"][5].startswith(
        f"@{tmp_path.resolve()}/.semantic-restructuring-contract."
    )
    assert "source.dj is the sole authority" in captured["messages"][0]
    assert "do not perform or record a second doctrinal interpretation" in captured[
        "messages"
    ][0]
    assert "Do not return unselected-line decisions" in captured["messages"][0]
    assert "predicates[i].participants[j]" in captured["messages"][0]
    assert "two indexed evidence items" in captured["messages"][0]
    assert "participant is normally\nnull" in captured["messages"][0]
    assert "cause\nand result mapping to 因此" in captured["messages"][0]
    assert "does not encode a shared parallel constituent" in captured["messages"][0]
    assert captured["hydration_project"] == tmp_path.resolve()
    assert captured["proposal"] == json.loads(artifact)
    assert captured["hydration_kwargs"]["provenance"] == model_receipt()
    assert captured["hydration_kwargs"]["accepted_decisions_sha256"] is None
    assert captured["validation_kwargs"]["expected_accepted_decisions_sha256"] is None
    assert captured["validation_stage"] == "restructuring"
    assert captured["validation_bytes"] == hydrated
    assert [item["name"] for item in receipt["inputs"]] == list(values)
    for item in receipt["inputs"]:
        assert item["absolute_path"] == str((tmp_path / item["name"]).resolve())
        assert item["sha256"] == digest(values[item["name"]])
    assert receipt["output"] == {
        "absolute_path": str(output.resolve()),
        "sha256": digest(hydrated),
    }
    assert receipt["semantic_restructuring_validation"]["status"] == "PASS"
    assert receipt["semantic_restructuring_proposal_sha256"] == digest(artifact)


def test_semantic_restructuring_validation_failure_never_publishes_output(
    tmp_path, monkeypatch
):
    project_inputs(tmp_path)
    monkeypatch.setattr(
        omp_runtime,
        "run_role",
        lambda *_args, **_kwargs: (b'{"invalid": true}', model_receipt()),
    )

    def reject(*_args, **_kwargs):
        raise StrategyT1Error("contract rejected")

    monkeypatch.setattr(omp_runtime, "validate_semantic_project", reject)
    with pytest.raises(StrategyT1Error, match="contract rejected"):
        omp_runtime.run_semantic_restructuring(tmp_path)
    assert not (tmp_path / "semantic-restructuring.json").exists()
    assert not list(tmp_path.glob(".semantic-restructuring.json.*.tmp"))


def test_semantic_restructuring_refuses_existing_target_before_model_call(
    tmp_path, monkeypatch
):
    project_inputs(tmp_path)
    existing = b"do not replace\n"
    (tmp_path / "semantic-restructuring.json").write_bytes(existing)

    def must_not_run(*_args, **_kwargs):
        raise AssertionError("model must not run")

    monkeypatch.setattr(omp_runtime, "run_role", must_not_run)
    with pytest.raises(StrategyT1Error, match="refusing to overwrite"):
        omp_runtime.run_semantic_restructuring(tmp_path)
    assert (tmp_path / "semantic-restructuring.json").read_bytes() == existing


def test_semantic_restructuring_atomic_publish_refuses_racing_target(
    tmp_path, monkeypatch
):
    project_inputs(tmp_path)
    candidate = b'{"candidate": true}'
    hydrated = hydrated_bytes(candidate)
    raced = b'{"other_process": true}'
    monkeypatch.setattr(
        omp_runtime,
        "run_role",
        lambda *_args, **_kwargs: (candidate, model_receipt()),
    )

    def race(_project, *, stage, artifact_path, **_kwargs):
        assert stage == "restructuring"
        assert artifact_path.read_bytes() == hydrated
        (tmp_path / "semantic-restructuring.json").write_bytes(raced)
        return {"status": "PASS"}

    monkeypatch.setattr(omp_runtime, "validate_semantic_project", race)
    with pytest.raises(StrategyT1Error, match="refusing to overwrite"):
        omp_runtime.run_semantic_restructuring(tmp_path)
    assert (tmp_path / "semantic-restructuring.json").read_bytes() == raced


def test_translation_uses_five_real_files_and_binds_complete_receipt(
    tmp_path, monkeypatch
):
    values = project_inputs(tmp_path)
    restructuring = b'{"schema_version": 2, "records": []}'
    values["semantic-restructuring.json"] = restructuring
    (tmp_path / "semantic-restructuring.json").write_bytes(restructuring)
    target = b"Natural English.\n"
    captured: dict = {}

    def fake_validate(project, *, stage, artifact_path, **kwargs):
        captured["validated_before_model"] = True
        assert project == tmp_path.resolve()
        assert stage == "restructuring"
        assert artifact_path == (tmp_path / "semantic-restructuring.json").resolve()
        assert kwargs["expected_accepted_decisions_sha256"] is None
        return {"status": "PASS", "warnings": []}

    def fake_role(role, messages, *, cwd, timeout):
        assert captured["validated_before_model"] is True
        captured.update(role=role, messages=messages, cwd=cwd, timeout=timeout)
        return target, model_receipt()

    monkeypatch.setattr(omp_runtime, "validate_semantic_project", fake_validate)
    monkeypatch.setattr(omp_runtime, "run_role", fake_role)
    receipt = omp_runtime.run_translation_with_restructuring(tmp_path, timeout=83)

    output = tmp_path / "target-draft.dj"
    assert output.read_bytes() == target
    assert captured["role"] == "translation_and_self_review"
    assert captured["messages"][1:] == [
        f"@{(tmp_path / name).resolve()}"
        for name in (
            "source.dj",
            "translation-project.yaml",
            "source-analysis.json",
            "term-map.yaml",
            "semantic-restructuring.json",
        )
    ]
    prompt = captured["messages"][0]
    assert "source.dj remains the sole authority" in prompt
    assert "must not be based on, or checked against, the restructured Chinese alone" in prompt
    assert [item["name"] for item in receipt["inputs"]] == list(values)
    for item in receipt["inputs"]:
        assert item["sha256"] == digest(values[item["name"]])
    assert receipt["output"]["sha256"] == digest(target)
    assert receipt["output_path"] == str(output.resolve())


def test_explicit_accepted_decisions_is_passed_and_hashed_by_both_calls(
    tmp_path, monkeypatch
):
    project_inputs(tmp_path)
    decisions = tmp_path / "adjudication" / "human-accepted.json"
    decisions.parent.mkdir()
    decision_bytes = b'{"accepted": ["L003"]}\n'
    decisions.write_bytes(decision_bytes)
    artifact = b'{"schema_version": 2, "records": []}'
    target = b"Accepted English.\n"
    calls: list[list[str]] = []
    hydrated_decision_hashes: list[str | None] = []
    validated_decision_hashes: list[str | None] = []

    def fake_role(_role, messages, **_kwargs):
        calls.append(messages)
        return (artifact if len(calls) == 1 else target), model_receipt()

    monkeypatch.setattr(omp_runtime, "run_role", fake_role)
    monkeypatch.setattr(
        omp_runtime,
        "hydrate_semantic_proposal",
        lambda _project, proposal, **kwargs: (
            hydrated_decision_hashes.append(
                kwargs["accepted_decisions_sha256"]
            )
            or proposal
        ),
    )
    monkeypatch.setattr(
        omp_runtime,
        "validate_semantic_project",
        lambda *_args, **kwargs: (
            validated_decision_hashes.append(
                kwargs["expected_accepted_decisions_sha256"]
            )
            or {"status": "PASS"}
        ),
    )
    semantic_receipt = omp_runtime.run_semantic_restructuring(
        tmp_path, accepted_decisions=decisions
    )
    translation_receipt = omp_runtime.run_translation_with_restructuring(
        tmp_path, accepted_decisions=decisions
    )

    accepted_argument = f"@{decisions.resolve()}"
    assert calls[0][-2] == accepted_argument
    assert calls[0][-1].startswith(
        f"@{tmp_path.resolve()}/.semantic-restructuring-contract."
    )
    assert calls[1][-1] == accepted_argument
    assert "accepted-decisions @file" in calls[0][0]
    assert "accepted-decisions @file" in calls[1][0]
    semantic_prompt = " ".join(calls[0][0].split())
    translation_prompt = " ".join(calls[1][0].split())
    assert "may correct an automated analysis or terminology aid" in semantic_prompt
    assert "may correct automated analysis or term choices" in translation_prompt
    assert "never override source.dj" in semantic_prompt
    assert "never override source.dj" in translation_prompt
    for receipt in (semantic_receipt, translation_receipt):
        accepted = receipt["inputs"][-1]
        assert accepted == {
            "name": "accepted-decisions",
            "absolute_path": str(decisions.resolve()),
            "sha256": digest(decision_bytes),
        }
    assert hydrated_decision_hashes == [digest(decision_bytes)]
    assert validated_decision_hashes == [
        digest(decision_bytes),
        digest(decision_bytes),
    ]


def test_explicit_missing_accepted_decisions_blocks_before_model(
    tmp_path, monkeypatch
):
    project_inputs(tmp_path)

    def must_not_run(*_args, **_kwargs):
        raise AssertionError("model must not run")

    monkeypatch.setattr(omp_runtime, "run_role", must_not_run)
    with pytest.raises(StrategyT1Error, match="required T1 input is missing"):
        omp_runtime.run_semantic_restructuring(
            tmp_path, accepted_decisions=tmp_path / "missing-decisions.json"
        )


def test_translation_refuses_existing_target_before_validation_or_model(
    tmp_path, monkeypatch
):
    project_inputs(tmp_path)
    (tmp_path / "semantic-restructuring.json").write_text("{}", encoding="utf-8")
    existing = b"preserve me\n"
    (tmp_path / "target-draft.dj").write_bytes(existing)

    def must_not_run(*_args, **_kwargs):
        raise AssertionError("validation/model must not run")

    monkeypatch.setattr(omp_runtime, "validate_semantic_project", must_not_run)
    monkeypatch.setattr(omp_runtime, "run_role", must_not_run)
    with pytest.raises(StrategyT1Error, match="refusing to overwrite"):
        omp_runtime.run_translation_with_restructuring(tmp_path)
    assert (tmp_path / "target-draft.dj").read_bytes() == existing


def test_translation_blocks_if_any_bound_input_changes_during_call(
    tmp_path, monkeypatch
):
    project_inputs(tmp_path)
    (tmp_path / "semantic-restructuring.json").write_text("{}", encoding="utf-8")
    monkeypatch.setattr(
        omp_runtime,
        "validate_semantic_project",
        lambda *_args, **_kwargs: {"status": "PASS"},
    )

    def mutate_source(*_args, **_kwargs):
        (tmp_path / "source.dj").write_text("changed\n", encoding="utf-8")
        return b"English.\n", model_receipt()

    monkeypatch.setattr(omp_runtime, "run_role", mutate_source)
    with pytest.raises(StrategyT1Error, match="input changed"):
        omp_runtime.run_translation_with_restructuring(tmp_path)
    assert not (tmp_path / "target-draft.dj").exists()
    assert not list(tmp_path.glob(".target-draft.dj.*.tmp"))
