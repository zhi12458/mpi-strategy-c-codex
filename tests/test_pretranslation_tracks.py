from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).parents[1]
SCRIPTS = ROOT / "skills" / "mpi-strategy-t1" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import omp_runtime  # noqa: E402
import artifact_reuse  # noqa: E402
import pretranslation  # noqa: E402
import strategy_t1  # noqa: E402
import usage_metrics  # noqa: E402
from t1_runtime import StrategyT1Error, atomic_json, sha256_file  # noqa: E402


def project_fixture(tmp_path: Path) -> Path:
    project = tmp_path / "project"
    project.mkdir()
    (project / "source.dj").write_text(
        "说到道德，又和宗教相关。\n\n当面对选择时，还能坚持吗？\n\n主语不能确定。\n",
        encoding="utf-8",
    )
    (project / "translation-project.yaml").write_text(
        "genre: Dharma talk\n", encoding="utf-8"
    )
    (project / "source-analysis.json").write_text("{}\n", encoding="utf-8")
    (project / "term-map.yaml").write_text("terms: {}\n", encoding="utf-8")
    return project


def proposal(*, mode: str) -> dict:
    records = [
        {
            "paragraph_id": "L1",
            "semantic_ledger": ["道德与宗教相关"],
            "rewrite": "说到道德，道德又和宗教相关。",
            "changes": ["重复唯一的主题名词"],
            "protected_constraints": ["道德与宗教的关系"],
            "risk_items": [],
            "status": "safe",
            "confidence": "high",
        },
        {
            "paragraph_id": "L3",
            "semantic_ledger": ["面对选择时发问能否坚持"],
            "rewrite": "当我们面对选择时，还能坚持吗？",
            "changes": ["显化候选主语"],
            "protected_constraints": ["条件范围", "问句"],
            "risk_items": ["我们是否为唯一主语需要复核"],
            "status": "review_required",
            "confidence": "medium",
        },
        {
            "paragraph_id": "L5",
            "semantic_ledger": ["原文未确定主语"],
            "rewrite": "主语不能确定。",
            "changes": [],
            "protected_constraints": ["不得猜测主语"],
            "risk_items": ["多种解释"],
            "status": "blocked" if mode == "ai_scale" else "review_required",
            "confidence": "low",
        },
    ]
    return {"records": records}


def compact_proposal() -> dict:
    return {
        "records": [
            {
                "paragraph_id": "L1",
                "action": "rewrite",
                "rewrite_transport": "说到道德，道德又和宗教相关。",
                "transformation_types": ["explicit_reference"],
                "risk_summary": "重复主题名词，不新增含义",
                "confidence": "high",
            },
            {
                "paragraph_id": "L5",
                "action": "block",
                "rewrite_transport": None,
                "transformation_types": [],
                "risk_summary": "主语不能唯一确定",
                "confidence": "low",
            },
        ]
    }


def ai_provenance() -> dict:
    return {
        "kind": "model",
        "name": None,
        "provider": "deepseek",
        "model": "deepseek-v4-flash",
        "reasoning_effort": "high",
        "role": "source_analysis",
    }


def human_artifact(project: Path) -> Path:
    value = pretranslation.hydrate_proposal(
        project,
        proposal(mode="human_quality"),
        mode="human_quality",
        provenance={
            "kind": "human",
            "name": "Human Editor",
            "provider": None,
            "model": None,
            "reasoning_effort": None,
            "role": None,
        },
    )
    path = project / "pretranslation.json"
    atomic_json(path, value)
    return path


def human_approval(project: Path, pretranslation_path: Path) -> Path:
    path = project / "human-pretranslation-approval.json"
    atomic_json(
        path,
        {
            "schema_version": 1,
            "workflow_version": "1.2.0",
            "stage": "human_pretranslation_approval",
            "source_sha256": sha256_file(project / "source.dj"),
            "pretranslation_sha256": sha256_file(pretranslation_path),
            "decision": "approved",
            "consensus": "unanimous",
            "reviewers": [
                {"name": "Reviewer A", "role": "Dharma reviewer"},
                {"name": "Reviewer B", "role": "English reviewer"},
            ],
        },
    )
    return path


def model_receipt(role: str, model: str, effort: str, provider: str) -> dict:
    return {
        "receipt_id": "receipt",
        "role": role,
        "provider": provider,
        "model": model,
        "selector": model,
        "reasoning_effort": effort,
        "exit_code": 0,
        "duration_seconds": 1.25,
        "usage": {
            "actual_model_invocations": 1,
            "cache_hits": 0,
            "retry_count": 0,
            "input_tokens": None,
            "output_tokens": None,
            "token_accounting": "not_exposed_by_locked_omp_print_transport",
        },
    }


def test_human_quality_is_hash_bound_scoring_anchor(tmp_path):
    project = project_fixture(tmp_path)
    artifact = human_artifact(project)
    approval = human_approval(project, artifact)
    report = pretranslation.validate_human_approval(project, artifact, approval)
    assert report["status"] == "PASS"
    assert report["consensus"] == "unanimous"
    accepted = project / "accepted-pretranslation.json"
    result = pretranslation.resolve_pretranslation(
        project, artifact, approval, output=accepted
    )
    assert result["accepted"]["mode"] == "human_quality"
    resolved = json.loads(accepted.read_text(encoding="utf-8"))
    assert {item["resolution"] for item in resolved["records"]} == {
        "human_approved_rewrite"
    }


def test_ai_scale_routes_review_and_blocked_records_without_guessing(tmp_path):
    project = project_fixture(tmp_path)
    artifact = pretranslation.hydrate_proposal(
        project, proposal(mode="ai_scale"), mode="ai_scale", provenance=ai_provenance()
    )
    pretranslation_path = project / "pretranslation.json"
    atomic_json(pretranslation_path, artifact)
    report = pretranslation.validate_pretranslation(project, artifact_path=pretranslation_path)
    assert report["status_counts"] == {"blocked": 1, "review_required": 1, "safe": 1}
    review = pretranslation.hydrate_ai_review(
        project,
        pretranslation_path,
        {
            "decisions": [
                {
                    "paragraph_id": "L3",
                    "decision": "revert_to_source",
                    "severity": "major",
                    "issue": "主语不唯一",
                    "required_revision": "使用原句",
                }
            ]
        },
        provenance={
            "provider": "deepseek",
            "model": "deepseek-v4-pro",
            "reasoning_effort": "max",
            "role": "bilingual_review",
        },
    )
    review_path = project / "pretranslation-review.json"
    atomic_json(review_path, review)
    accepted = project / "accepted-pretranslation.json"
    pretranslation.resolve_pretranslation(
        project, pretranslation_path, review_path, output=accepted
    )
    value = json.loads(accepted.read_text(encoding="utf-8"))
    assert [item["resolution"] for item in value["records"]] == [
        "ai_safe_rewrite",
        "reverted_to_source",
        "reverted_to_source",
    ]
    assert value["records"][1]["effective_text"] == value["records"][1]["source"]


def test_ai_blocked_record_cannot_contain_a_guessed_rewrite(tmp_path):
    project = project_fixture(tmp_path)
    value = proposal(mode="ai_scale")
    value["records"][2]["rewrite"] = "我们不能确定主语。"
    value["records"][2]["changes"] = ["猜测主语"]
    artifact = pretranslation.hydrate_proposal(
        project, value, mode="ai_scale", provenance=ai_provenance()
    )
    path = project / "pretranslation.json"
    atomic_json(path, artifact)
    with pytest.raises(StrategyT1Error, match="blocked but guesses"):
        pretranslation.validate_pretranslation(project, artifact_path=path)


def test_ai_review_cannot_accept_major_or_critical_defect(tmp_path):
    project = project_fixture(tmp_path)
    artifact = pretranslation.hydrate_proposal(
        project, proposal(mode="ai_scale"), mode="ai_scale", provenance=ai_provenance()
    )
    artifact_path = project / "pretranslation.json"
    atomic_json(artifact_path, artifact)
    review = pretranslation.hydrate_ai_review(
        project,
        artifact_path,
        {
            "decisions": [
                {
                    "paragraph_id": "L3",
                    "decision": "accept",
                    "severity": "critical",
                    "issue": "错误",
                    "required_revision": "回退",
                }
            ]
        },
        provenance={
            "provider": "deepseek",
            "model": "deepseek-v4-pro",
            "reasoning_effort": "max",
            "role": "bilingual_review",
        },
    )
    review_path = project / "pretranslation-review.json"
    atomic_json(review_path, review)
    with pytest.raises(StrategyT1Error, match="accepts a major or critical"):
        pretranslation.validate_ai_review(project, artifact_path, review_path)


def test_ai_pretranslation_runner_uses_flash_and_validates_before_publish(
    tmp_path, monkeypatch
):
    project = project_fixture(tmp_path)
    seen = {}

    def fake_role(role, messages, **_kwargs):
        seen["role"] = role
        seen["messages"] = messages
        return json.dumps(compact_proposal(), ensure_ascii=False).encode(), model_receipt(
            "source_analysis", "deepseek-v4-flash", "high", "deepseek"
        )

    monkeypatch.setattr(omp_runtime, "run_role", fake_role)
    receipt = omp_runtime.run_ai_pretranslation(project)
    assert seen["role"] == "source_analysis"
    assert receipt["pretranslation_validation"]["status"] == "PASS"
    assert receipt["workflow_stage"] == "ai_pretranslation"
    assert receipt["pretranslation_transport_version"] == "compact-changes-v1"
    assert (project / "pretranslation.json").is_file()


def test_compact_ai_proposal_hydrates_full_coverage_and_routes_every_rewrite(tmp_path):
    project = project_fixture(tmp_path)
    artifact = pretranslation.hydrate_compact_ai_proposal(
        project, compact_proposal(), provenance=ai_provenance()
    )
    path = project / "pretranslation.json"
    atomic_json(path, artifact)
    report = pretranslation.validate_pretranslation(
        project, artifact_path=path, expected_mode="ai_scale"
    )
    assert report["changed_units"] == 1
    assert report["status_counts"] == {"blocked": 1, "review_required": 1, "safe": 1}
    assert artifact["records"][1]["rewrite"] == artifact["records"][1]["source"]
    assert artifact["records"][0]["status"] == "review_required"


def test_compact_quote_transport_is_decoded_and_quote_drift_is_rejected(tmp_path):
    project = project_fixture(tmp_path)
    (project / "source.dj").write_text('他说道："善。”\n', encoding="utf-8")
    value = {
        "records": [
            {
                "paragraph_id": "L1",
                "action": "rewrite",
                "rewrite_transport": "他说：⟦Q0⟧善。⟦Q2⟧",
                "transformation_types": ["redundancy_reduction"],
                "risk_summary": "删除不承载独立语义的载体词",
                "confidence": "high",
            }
        ]
    }
    artifact = pretranslation.hydrate_compact_ai_proposal(
        project, value, provenance=ai_provenance()
    )
    assert artifact["records"][0]["rewrite"] == '他说："善。”'
    value["records"][0]["rewrite_transport"] = "他说：⟦Q1⟧善。⟦Q2⟧"
    with pytest.raises(StrategyT1Error, match="quotation-mark identity"):
        pretranslation.hydrate_compact_ai_proposal(
            project, value, provenance=ai_provenance()
        )


def test_translation_runner_binds_human_evidence_and_preserves_line_parity(
    tmp_path, monkeypatch
):
    project = project_fixture(tmp_path)
    artifact = human_artifact(project)
    approval = human_approval(project, artifact)
    accepted = project / "accepted-pretranslation.json"
    pretranslation.resolve_pretranslation(project, artifact, approval, output=accepted)

    def fake_role(role, _messages, **_kwargs):
        assert role == "translation_and_self_review"
        return b"Morality is related to religion.\n\nCan we persevere when choices arise?\n\nThe subject is uncertain.\n", model_receipt(
            role, "gpt-5.6-sol", "high", "openai-codex"
        )

    monkeypatch.setattr(omp_runtime, "run_role", fake_role)
    receipt = omp_runtime.run_translation_with_pretranslation(project)
    assert receipt["pretranslation_mode"] == "human_quality"
    assert receipt["target_line_parity"] == {"status": "PASS", "physical_lines": 5}
    assert receipt["decision_evidence_validation"]["consensus"] == "unanimous"


def test_usage_summary_counts_receipts_not_omp_events(tmp_path):
    receipt_path = tmp_path / "receipt.json"
    value = model_receipt("source_analysis", "deepseek-v4-flash", "high", "deepseek")
    value["workflow_stage"] = "source_analysis"
    value["omp_event_count"] = 570
    atomic_json(receipt_path, value)
    report = usage_metrics.summarize_receipts([receipt_path])
    assert report["actual_model_invocations"] == 1
    assert report["input_tokens"] is None
    assert report["token_accounting_complete"] is False
    assert report["omp_event_count_used_as_model_call_count"] is False


def test_content_addressed_reuse_requires_pass_validation_and_fresh_inputs(tmp_path):
    source = tmp_path / "source.dj"
    source.write_text("原文\n", encoding="utf-8")
    artifact = tmp_path / "artifact.json"
    artifact.write_text('{"value": 1}\n', encoding="utf-8")
    receipt_path = tmp_path / "receipt.json"
    receipt = model_receipt("source_analysis", "deepseek-v4-flash", "high", "deepseek")
    receipt.update(
        {
            "workflow_stage": "source_analysis",
            "prompt_sha256": "1" * 64,
            "execution_profile": {"name": "single-response-no-tools-v1"},
            "inputs": [
                {
                    "name": "source.dj",
                    "absolute_path": str(source),
                    "sha256": sha256_file(source),
                }
            ],
            "output": {
                "absolute_path": str(artifact),
                "sha256": sha256_file(artifact),
            },
        }
    )
    atomic_json(receipt_path, receipt)
    validation_path = tmp_path / "validation.json"
    atomic_json(validation_path, {"status": "PASS"})
    cache_root = tmp_path / "cache"
    cached = artifact_reuse.cache_validated_artifact(
        artifact, receipt_path, validation_path, cache_root
    )
    assert cached["cache_hit"] is False
    restored = artifact_reuse.restore_validated_artifact(
        cache_root, cached["cache_key"], tmp_path / "restored.json"
    )
    assert restored["usage"]["actual_model_invocations"] == 0
    assert restored["usage"]["cache_hits"] == 1
    source.write_text("已变化\n", encoding="utf-8")
    with pytest.raises(StrategyT1Error, match="missing or stale"):
        artifact_reuse.restore_validated_artifact(
            cache_root, cached["cache_key"], tmp_path / "stale.json"
        )


def test_content_addressed_reuse_rejects_unvalidated_raw_output(tmp_path):
    source = tmp_path / "source.dj"
    source.write_text("原文\n", encoding="utf-8")
    artifact = tmp_path / "artifact.json"
    artifact.write_text("{}\n", encoding="utf-8")
    receipt_path = tmp_path / "receipt.json"
    receipt = model_receipt("source_analysis", "deepseek-v4-flash", "high", "deepseek")
    receipt["inputs"] = [
        {"name": "source.dj", "absolute_path": str(source), "sha256": sha256_file(source)}
    ]
    receipt["output"] = {"absolute_path": str(artifact), "sha256": sha256_file(artifact)}
    atomic_json(receipt_path, receipt)
    validation = tmp_path / "validation.json"
    atomic_json(validation, {"status": "FAIL"})
    with pytest.raises(StrategyT1Error, match="requires explicit PASS"):
        artifact_reuse.cache_validated_artifact(
            artifact, receipt_path, validation, tmp_path / "cache"
        )


def test_t1_2_cli_routes_are_explicit():
    human = strategy_t1.parser().parse_args(
        [
            "hydrate-human-pretranslation",
            "--project",
            "/tmp/project",
            "--proposal",
            "/tmp/proposal.json",
            "--generator-name",
            "Editor",
        ]
    )
    ai = strategy_t1.parser().parse_args(
        ["run-ai-pretranslation", "--project", "/tmp/project"]
    )
    translation = strategy_t1.parser().parse_args(
        ["run-translation-with-pretranslation", "--project", "/tmp/project"]
    )
    assert human.command == "hydrate-human-pretranslation"
    assert ai.command == "run-ai-pretranslation"
    assert translation.command == "run-translation-with-pretranslation"
    cache = strategy_t1.parser().parse_args(
        [
            "restore-cached-artifact",
            "--cache-root",
            "/tmp/cache",
            "--cache-key",
            "1" * 64,
            "--output",
            "/tmp/output",
        ]
    )
    assert cache.command == "restore-cached-artifact"
