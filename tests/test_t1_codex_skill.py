from __future__ import annotations

import base64
import importlib.util
import json
import shutil
import subprocess
import zipfile
from pathlib import Path
from xml.sax.saxutils import escape

import pytest


ROOT = Path(__file__).parents[1]
SKILL = ROOT / "skills" / "mpi-strategy-t1-codex"
SCRIPT = SKILL / "scripts" / "validate_package.py"
WORKSPACE_SCRIPT = SKILL / "scripts" / "confirm_workspace.py"
RUNTIME_SCRIPT = SKILL / "scripts" / "install_runtime.py"
READER_GATE_SCRIPT = SKILL / "scripts" / "validate_reader_gate.py"
SEGMENTATION_SCRIPT = SKILL / "scripts" / "validate_semantic_segmentation.py"
POST_EDIT_SCRIPT = SKILL / "scripts" / "validate_post_translation_editing.py"


def load_validator():
    spec = importlib.util.spec_from_file_location("t1_codex_validate_package", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


validator = load_validator()


def load_workspace_confirmation():
    spec = importlib.util.spec_from_file_location(
        "t1_codex_confirm_workspace", WORKSPACE_SCRIPT
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


workspace_confirmation = load_workspace_confirmation()


def load_runtime_installer():
    spec = importlib.util.spec_from_file_location(
        "t1_codex_install_runtime", RUNTIME_SCRIPT
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


runtime_installer = load_runtime_installer()


def load_reader_gate_validator():
    spec = importlib.util.spec_from_file_location(
        "t1_codex_validate_reader_gate", READER_GATE_SCRIPT
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


reader_gate = load_reader_gate_validator()


def load_segmentation_validator():
    spec = importlib.util.spec_from_file_location(
        "t1_codex_validate_semantic_segmentation", SEGMENTATION_SCRIPT
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


segmentation_validator = load_segmentation_validator()


def load_post_edit_validator():
    spec = importlib.util.spec_from_file_location(
        "t1_codex_validate_post_translation_editing", POST_EDIT_SCRIPT
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


post_edit_validator = load_post_edit_validator()


def test_t1_codex_package_manifest_and_policy_pass():
    report = validator.validate_package(SKILL)
    assert report["status"] == "PASS"
    assert report["manifest"]["file_count"] >= 9
    assert report["policy"]["production_default_selected"] is True
    assert report["policy"]["release_ready"] is False


def test_t1_codex_lock_selects_codex_english_and_independent_pro_roles():
    dependency = json.loads((SKILL / "dependency-lock.json").read_text(encoding="utf-8"))
    production = json.loads(
        (SKILL / "references" / "production-lock.json").read_text(encoding="utf-8")
    )
    assert dependency["strategy_id"] == "T1-CODEX"
    assert dependency["workflow_version"] == "1.2.0"
    assert dependency["installer_version"] == "1.0.2"
    assert dependency["base_runtime"]["stable_commit"] == (
        "af795df625eca95ab138094bd25172266007f24f"
    )
    assert production["default_routing"]["selected_workflow"] == "t1_codex_quality"
    assert production["model_roles"]["translation_and_self_review"] == {
        "model": "runtime-selected-gpt-5.6-or-gpt-6",
        "reasoning_effort": "runtime-supported",
        "execution_surface": "current Codex task",
        "competing_english_allowed": False,
    }
    assert production["model_roles"]["semantic_bridge_generation"]["scope"] == (
        "high-risk source units only"
    )
    assert production["model_roles"]["semantic_bridge_generation"]["writes_english"] is False
    assert production["model_roles"]["post_concision_semantic_regression"][
        "reasoning_effort"
    ] == "max"


def test_t1_codex_allows_personal_and_business_workspace_confirmations():
    dependency = json.loads((SKILL / "dependency-lock.json").read_text(encoding="utf-8"))
    policy = dependency["openai_workspace_policy"]
    assert policy["allowed_workspace_kinds"] == ["personal", "business"]
    assert policy["accepted_confirmation_tokens"] == ["PERSONAL", "BUSINESS", "TEAM"]
    assert policy["team_normalizes_to"] == "business"
    assert policy["workspace_identifiers_recorded"] is False
    assert policy["credentials_recorded"] is False


def test_t1_codex_runtime_installer_is_fail_closed():
    dependency = json.loads((SKILL / "dependency-lock.json").read_text(encoding="utf-8"))
    policy = dependency["runtime_installer"]
    assert dependency["candidate_ref"] == "t1-codex-v1.2.0-candidate.2"
    assert policy["script"] == "scripts/install_runtime.py"
    assert policy["interactive"] is True
    assert policy["fail_closed"] is True
    assert policy["deepseek_masked_prompt_required_when_missing"] is True
    assert policy["base_ready_true_required"] is True
    assert policy["static_package_validation_is_runtime_readiness"] is False


def test_runtime_installer_verifies_immutable_base_package(tmp_path, monkeypatch):
    base = tmp_path / "mpi-strategy-t1"
    (base / "scripts").mkdir(parents=True)
    (base / "dependency-lock.json").write_text(
        json.dumps(
            {
                "strategy_id": "T1",
                "workflow_version": "1.0.1",
                "installer_version": "1.0.0",
                "release_ready": True,
            }
        ),
        encoding="utf-8",
    )
    manifest = base / "MANIFEST.sha256"
    manifest.write_text("fixture\n", encoding="utf-8")
    (base / "scripts" / "strategy_t1.py").write_text("# fixture\n", encoding="utf-8")
    (base / "scripts" / "credential_store.py").write_text("# fixture\n", encoding="utf-8")
    monkeypatch.setattr(
        runtime_installer,
        "EXPECTED_BASE_MANIFEST_SHA256",
        runtime_installer.sha256_file(manifest),
    )
    assert runtime_installer.verify_base_package(base)["release_ready"] is True


def test_runtime_installer_rejects_incomplete_ready_evidence():
    with pytest.raises(runtime_installer.RuntimeInstallError, match="ready=true"):
        runtime_installer.base_ready_from_doctor({"ok": True, "result": {"ready": False}})
    with pytest.raises(runtime_installer.RuntimeInstallError, match="DeepSeek"):
        runtime_installer.base_ready_from_doctor(
            {"ok": True, "result": {"ready": True, "deepseek_credential": {}}}
        )
    with pytest.raises(runtime_installer.RuntimeInstallError, match="smoke"):
        runtime_installer.base_ready_from_doctor(
            {
                "ok": True,
                "result": {
                    "ready": True,
                    "deepseek_credential": {"present": True},
                    "smoke_test": {"status": "FAIL"},
                    "fault_injection": {"status": "PASS"},
                },
            }
        )


def test_runtime_installer_normalizes_real_omp_version_output():
    completed = subprocess.CompletedProcess(
        args=("omp", "--version"),
        returncode=0,
        stdout=b"omp/17.3.4\n",
        stderr=b"",
    )

    assert runtime_installer.omp_version(
        "omp", runner=lambda *_args, **_kwargs: completed
    ) == "17.3.4"


def test_runtime_installer_reports_missing_dependencies(monkeypatch):
    monkeypatch.setattr(runtime_installer.shutil, "which", lambda _name: None)
    monkeypatch.setattr(runtime_installer.importlib.util, "find_spec", lambda _name: None)
    missing = runtime_installer.missing_dependencies()
    assert "git" in missing
    assert "pandoc" in missing
    assert "libreoffice" in missing
    assert "python-keyring" in missing


def test_runtime_installer_accepts_complete_ready_evidence():
    ready = {
        "ready": True,
        "deepseek_credential": {"present": True},
        "smoke_test": {"status": "PASS"},
        "fault_injection": {"status": "PASS"},
    }
    assert runtime_installer.base_ready_from_doctor({"ok": True, "result": ready}) is ready


def test_runtime_installer_runs_credential_smoke_and_doctor_gates(tmp_path, monkeypatch):
    class InteractiveInput:
        @staticmethod
        def isatty():
            return True

    calls = []
    credential_states = iter((False, True))
    monkeypatch.setattr(runtime_installer.sys, "stdin", InteractiveInput())
    monkeypatch.setattr(runtime_installer, "verify_base_package", lambda _path: {})
    monkeypatch.setattr(runtime_installer, "missing_dependencies", lambda: [])
    monkeypatch.setattr(runtime_installer.shutil, "which", lambda name: "/bin/omp" if name == "omp" else None)
    monkeypatch.setattr(runtime_installer, "omp_version", lambda _path: "17.3.4")
    monkeypatch.setattr(
        runtime_installer,
        "run_interactive",
        lambda command, cwd: calls.append((command, cwd)),
    )
    monkeypatch.setattr(
        runtime_installer,
        "credential_present",
        lambda _base: next(credential_states),
    )
    monkeypatch.setattr(runtime_installer, "managed_root", lambda: tmp_path)
    monkeypatch.setattr("builtins.input", lambda _prompt: "RUN PUBLIC SMOKE")

    def fake_json(command, _cwd):
        if command[-1] == "doctor":
            return {
                "ok": True,
                "result": {
                    "ready": True,
                    "deepseek_credential": {"present": True},
                    "smoke_test": {"status": "PASS"},
                    "fault_injection": {"status": "PASS"},
                },
            }
        return {"status": "PASS", "manifest": {"sha256": "candidate-manifest"}}

    monkeypatch.setattr(runtime_installer, "run_json", fake_json)
    result = runtime_installer.install_runtime(tmp_path / "mpi-strategy-t1")

    flattened = [part for command, _cwd in calls for part in command]
    assert "login-openai" in flattened
    assert "scripts/confirm_workspace.py" in flattened
    assert "scripts/credential_store.py" in flattened
    assert "--confirm-public-smoke" in flattened
    assert result["runtime_ready"] is True
    assert result["deepseek_credential_present"] is True
    assert result["public_smoke_status"] == "PASS"
    assert result["candidate_ref"] == "t1-codex-v1.2.0-candidate.2"
    assert result["candidate_manifest_sha256"] == "candidate-manifest"
    saved = json.loads((tmp_path / "T1_CODEX_RUNTIME_READY.json").read_text(encoding="utf-8"))
    assert saved["credentials_recorded"] is False


@pytest.mark.parametrize(
    ("token", "expected_kind", "team_alias"),
    (("PERSONAL", "personal", False), ("BUSINESS", "business", False), ("TEAM", "business", True)),
)
def test_workspace_confirmation_normalizes_supported_tokens(
    token, expected_kind, team_alias
):
    usage = b'{"reports":[]}'
    reports = [
        {
            "provider": "openai-codex",
            "metadata": {"allowed": True, "planType": "redacted", "orgName": "redacted"},
        }
    ]
    record = workspace_confirmation.build_confirmation(usage, reports, 1, token)
    assert record["confirmed"] is True
    assert record["provider"] == "openai-codex"
    assert record["workspace_kind"] == expected_kind
    assert record["team_alias_normalized_to_business"] is team_alias
    assert record["email_recorded"] is False
    assert record["account_id_recorded"] is False
    assert record["workspace_label_recorded"] is False
    assert record["token_recorded"] is False


def test_workspace_confirmation_rejects_unknown_kind_and_account_number():
    usage = b'{"reports":[]}'
    reports = [
        {"provider": "openai-codex", "metadata": {"allowed": True}}
    ]
    with pytest.raises(
        workspace_confirmation.WorkspaceConfirmationError,
        match="PERSONAL or BUSINESS",
    ):
        workspace_confirmation.build_confirmation(usage, reports, 1, "ENTERPRISE")
    with pytest.raises(
        workspace_confirmation.WorkspaceConfirmationError,
        match="out of range",
    ):
        workspace_confirmation.build_confirmation(usage, reports, 2, "PERSONAL")


def test_workspace_confirmation_filters_to_enabled_openai_codex_reports():
    payload = {
        "reports": [
            {"provider": "openai-codex", "metadata": {"allowed": True}},
            {"provider": "openai-codex", "metadata": {"allowed": False}},
            {"provider": "other", "metadata": {"allowed": True}},
        ]
    }
    assert len(workspace_confirmation.enabled_reports(payload)) == 1


def test_t1_codex_adopts_bounded_segmentation_but_keeps_full_pretranslation_experimental():
    production = json.loads(
        (SKILL / "references" / "production-lock.json").read_text(encoding="utf-8")
    )
    assert production["workflow_modes"]["full_pretranslation_experiments"][
        "production_default"
    ] is False
    assert production["workflow_modes"]["t1_omp_rollback"]["production_default"] is False
    assert production["workflow_modes"]["t1_omp_rollback"][
        "automatic_prose_merging_allowed"
    ] is False
    assert "mandatory full-document Sol semantic restructuring" in production[
        "t1_1_2_adoption_policy"
    ]["not_default"]
    segmentation = production["chinese_semantic_segmentation"]
    assert segmentation["mandatory"] is True
    assert segmentation["source_authority"] == "source.dj"
    assert segmentation["conflict_resolution"] == "source.dj wins"
    assert segmentation["added_we_rule"] == {
        "subject": "我们",
        "allowed_only_when_source_includes_speaker_and_audience": True,
        "engagement_alone_is_source_evidence": False,
        "ambiguous_case_status": "review_required",
        "commissioner_decision_required_before_application": True,
    }


def test_t1_codex_adds_no_retranslation_post_edit_mode():
    production = json.loads(
        (SKILL / "references" / "production-lock.json").read_text(encoding="utf-8")
    )
    mode = production["workflow_modes"]["post_translation_native_editing"]
    assert mode["production_default_after_completed_translation"] is True
    assert mode["full_translation_rerun_default"] is False
    assert mode["bilingual_review_rerun_default"] is False
    assert mode["exact_hash_upstream_evidence_reuse_only"] is True
    assert mode["status_without_complete_upstream_evidence"] == (
        "T1-Codex post-edit AI-reviewed draft"
    )
    policy = production["post_translation_editing"]
    assert policy["source_only_semantic_map_artifact_sha256_required"] is True
    assert policy["upstream_status_inheritance"]["boolean_declaration_sufficient"] is False
    assert policy["upstream_status_inheritance"]["inner_completion_receipt_required"] is True
    assert policy["upstream_status_inheritance"][
        "locks_loaded_from_dependency_and_production_files"
    ] is True
    assert policy["source_only_semantic_map_validation"][
        "new_map_covers_every_nonblank_source_line_in_order"
    ] is True
    assert policy["source_only_semantic_map_validation"][
        "ambiguity_requires_named_hash_bound_commissioner_decision"
    ] is True
    assert policy["human_feedback_learning"]["full_document_analogue_scan_required"] is True
    assert policy["terminology_scope"][
        "project_decisions_promoted_to_global_termbase_automatically"
    ] is False
    assert policy["clean_alternating_bilingual_docx"][
        "semantic_notes_feedback_decisions_and_process_excluded"
    ] is True
    assert policy["clean_alternating_bilingual_docx"][
        "actual_docx_paragraphs_derived_from_source_and_target"
    ] is True
    assert policy["clean_alternating_bilingual_docx"][
        "render_receipt_bound_to_final_docx_hash_and_page_index"
    ] is True
    assert production["english_only_reader_gate"][
        "source_evidence_must_be_literal_span_of_hash_bound_source"
    ] is True


def test_t1_codex_release_remains_blocked_until_three_genre_validation():
    production = json.loads(
        (SKILL / "references" / "production-lock.json").read_text(encoding="utf-8")
    )
    validation = production["release_validation"]
    assert production["release_ready"] is False
    assert validation["current_status"] == "pending"
    assert validation["release_ready_allowed_before_pass"] is False
    assert validation["required_genres"] == [
        "Dharma talk",
        "written article",
        "quotation-dense Buddhist text",
    ]


def build_segmentation_fixture(project: Path, subject: str = "我") -> None:
    source = project / "source.dj"
    segmented = project / "chinese-semantic-segmentation.dj"
    source.write_text(
        "很高兴在此和大家结缘。\n\n一、何为道德\n", encoding="utf-8"
    )
    segmented.write_text(
        f"{subject}很高兴在此和大家结缘。\n\n一、何为道德\n", encoding="utf-8"
    )
    source_hash = segmentation_validator.sha256_file(source)
    source_lines = source.read_text(encoding="utf-8").splitlines()
    segmented_lines = segmented.read_text(encoding="utf-8").splitlines()
    confirmation = subject == "我们"
    records = [
        {
            "schema_version": 1,
            "workflow_version": "1.2.0",
            "source_sha256": source_hash,
            "source_line": 1,
            "paragraph_id": "L001",
            "source_line_sha256": segmentation_validator.sha256_text(source_lines[0]),
            "source_text": source_lines[0],
            "meaning_units": [
                {
                    "unit_id": "L001-U01",
                    "text": segmented_lines[0],
                    "source_evidence": [source_lines[0]],
                    "semantic_roles": {
                        "subject": subject,
                        "predicate": "很高兴并结缘",
                        "object": "大家",
                    },
                    "logic_relation": "single proposition",
                }
            ],
            "segmented_chinese": segmented_lines[0],
            "changes": [
                {
                    "type": "added_subject",
                    "subject": subject,
                    "source_evidence": ["和大家结缘"],
                    "person_scope": (
                        "speaker_and_audience" if subject == "我们" else "speaker"
                    ),
                    "human_confirmation_required": confirmation,
                }
            ],
            "protected_constraints": ["结缘", "大家"],
            "risk_items": (["新增我们须委托人确认"] if confirmation else []),
            "status": "review_required" if confirmation else "safe",
            "confidence": "high",
        },
        {
            "schema_version": 1,
            "workflow_version": "1.2.0",
            "source_sha256": source_hash,
            "source_line": 3,
            "paragraph_id": "L003",
            "source_line_sha256": segmentation_validator.sha256_text(source_lines[2]),
            "source_text": source_lines[2],
            "meaning_units": [
                {
                    "unit_id": "L003-U01",
                    "text": source_lines[2],
                    "source_evidence": [source_lines[2]],
                    "semantic_roles": {"structure": "heading"},
                    "logic_relation": "structural",
                }
            ],
            "segmented_chinese": source_lines[2],
            "changes": [],
            "protected_constraints": ["heading text"],
            "risk_items": [],
            "status": "structural",
            "confidence": "high",
        },
    ]
    (project / "chinese-semantic-segmentation.jsonl").write_text(
        "\n".join(json.dumps(record, ensure_ascii=False) for record in records) + "\n",
        encoding="utf-8",
    )
    review = {
        "schema_version": 1,
        "workflow_version": "1.2.0",
        "source_sha256": source_hash,
        "paragraph_id": "L001",
        "segmented_line_sha256": segmentation_validator.sha256_text(
            segmented_lines[0]
        ),
        "reviewer": {
            "model": "deepseek-v4-pro",
            "reasoning_effort": "max",
            "session_id": "fresh-pro-review-1",
        },
        "decision": "human_approved" if confirmation else "approved",
        "resolved_status": "safe",
        "omission_count": 0,
        "addition_count": 0,
    }
    if confirmation:
        review["commissioner_decision"] = {
            "approved": True,
            "named_approver": "Commissioner Fixture",
            "selected_subject": "我们",
        }
    (project / "chinese-semantic-segmentation-review.jsonl").write_text(
        json.dumps(review, ensure_ascii=False) + "\n", encoding="utf-8"
    )


def test_semantic_segmentation_accepts_complete_draft_and_review(tmp_path):
    build_segmentation_fixture(tmp_path)
    draft = segmentation_validator.validate_project(tmp_path, "draft")
    assert draft["status"] == "PASS"
    assert draft["covered_nonblank_lines"] == 2
    assert draft["changed_paragraph_ids"] == ["L001"]
    review = segmentation_validator.validate_project(tmp_path, "review")
    assert review["status"] == "PASS"
    assert review["reviewed_changed_records"] == 1


def test_semantic_segmentation_requires_confirmation_for_added_we(tmp_path):
    build_segmentation_fixture(tmp_path, subject="我们")
    record_path = tmp_path / "chinese-semantic-segmentation.jsonl"
    records = [json.loads(line) for line in record_path.read_text(encoding="utf-8").splitlines()]
    records[0]["changes"][0]["human_confirmation_required"] = False
    records[0]["status"] = "safe"
    record_path.write_text(
        "\n".join(json.dumps(record, ensure_ascii=False) for record in records) + "\n",
        encoding="utf-8",
    )
    with pytest.raises(
        segmentation_validator.SegmentationValidationError,
        match="adds 我们 without mandatory human confirmation",
    ):
        segmentation_validator.validate_project(tmp_path, "draft")


def test_semantic_segmentation_rejects_line_or_blank_position_drift(tmp_path):
    build_segmentation_fixture(tmp_path)
    (tmp_path / "chinese-semantic-segmentation.dj").write_text(
        "我很高兴在此和大家结缘。\n一、何为道德\n", encoding="utf-8"
    )
    with pytest.raises(
        segmentation_validator.SegmentationValidationError,
        match="physical-line counts differ|blank-line positions differ",
    ):
        segmentation_validator.validate_project(tmp_path, "draft")


def test_semantic_segmentation_rejects_unbound_source_evidence(tmp_path):
    build_segmentation_fixture(tmp_path)
    record_path = tmp_path / "chinese-semantic-segmentation.jsonl"
    records = [json.loads(line) for line in record_path.read_text(encoding="utf-8").splitlines()]
    records[0]["changes"][0]["source_evidence"] = ["这段文字不在原文中"]
    record_path.write_text(
        "\n".join(json.dumps(record, ensure_ascii=False) for record in records) + "\n",
        encoding="utf-8",
    )
    with pytest.raises(
        segmentation_validator.SegmentationValidationError,
        match="not present in the bound source line",
    ):
        segmentation_validator.validate_project(tmp_path, "draft")


def test_semantic_segmentation_added_we_cannot_borrow_other_clause(tmp_path):
    build_segmentation_fixture(tmp_path, subject="我们")
    source_text = "我们今天来到这里；很高兴在此和大家结缘。"
    segmented_text = "我们今天来到这里；我们很高兴在此和大家结缘。"
    (tmp_path / "source.dj").write_text(
        source_text + "\n\n一、何为道德\n", encoding="utf-8"
    )
    (tmp_path / "chinese-semantic-segmentation.dj").write_text(
        segmented_text + "\n\n一、何为道德\n", encoding="utf-8"
    )
    source_hash = segmentation_validator.sha256_file(tmp_path / "source.dj")
    record_path = tmp_path / "chinese-semantic-segmentation.jsonl"
    records = [json.loads(line) for line in record_path.read_text(encoding="utf-8").splitlines()]
    records[0]["source_sha256"] = source_hash
    records[0]["source_text"] = source_text
    records[0]["source_line_sha256"] = segmentation_validator.sha256_text(source_text)
    records[0]["segmented_chinese"] = segmented_text
    records[0]["meaning_units"][0]["source_evidence"] = [source_text]
    records[0]["changes"][0]["source_evidence"] = ["很高兴在此和大家结缘"]
    records[0]["changes"][0]["human_confirmation_required"] = False
    records[0]["status"] = "safe"
    records[1]["source_sha256"] = source_hash
    record_path.write_text(
        "\n".join(json.dumps(record, ensure_ascii=False) for record in records) + "\n",
        encoding="utf-8",
    )
    with pytest.raises(
        segmentation_validator.SegmentationValidationError,
        match="adds 我们 without mandatory human confirmation",
    ):
        segmentation_validator.validate_project(tmp_path, "draft")


def build_reader_gate_fixture(project: Path) -> None:
    source = project / "source.dj"
    target = project / "target.dj"
    source.write_text("佛法的道德观\n", encoding="utf-8")
    target.write_text("The Buddhist View of Morality\n", encoding="utf-8")
    source_hash = reader_gate.sha256_file(source)
    target_hash = reader_gate.sha256_file(target)
    for filename in reader_gate.READER_MANUSCRIPTS.values():
        (project / filename).write_text(target.read_text(encoding="utf-8"), encoding="utf-8")
    sessions = {
        ("initial", "general_nonfiction_editor"): "session-initial-general",
        ("initial", "english_dharma_editor"): "session-initial-dharma",
        ("final", "general_nonfiction_editor"): "session-final-general",
        ("final", "english_dharma_editor"): "session-final-dharma",
    }
    for (phase, role), filename in reader_gate.READER_FILES.items():
        (project / filename).write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "gate": "english_only_reader",
                    "phase": phase,
                    "role": role,
                    "session_id": sessions[(phase, role)],
                    "prompt_sha256": "a" * 64,
                    "target_sha256": target_hash,
                    "visible_input_count": 1,
                    "visible_input_sha256": target_hash,
                    "visible_input_derived_from_target_sha256": target_hash,
                    "visible_input_is_english_only": True,
                    "isolation": {
                        "fresh_session": True,
                        "source_side_material_visible": False,
                        "prior_feedback_visible": False,
                        "other_reader_output_visible": False,
                        "translator_context_visible": False,
                    },
                    "blocker_count": 0,
                    "unresolved_actionable_count": 0,
                    "findings": [],
                }
            ),
            encoding="utf-8",
        )
    (project / "english-reader-adjudication.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "gate": "reader_adjudication",
                "source_sha256": source_hash,
                "input_target_sha256": target_hash,
                "output_target_sha256": target_hash,
                "every_reader_finding_checked_against_full_chinese": True,
                "every_reader_finding_classified_by_risk": True,
                "low_risk_edits_checked_against_full_chinese": True,
                "unresolved_reader_blockers": 0,
                "decision_count": 0,
                "decisions": [],
            }
        ),
        encoding="utf-8",
    )
    (project / "commissioner-decisions.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "gate": "commissioner_sensitive_changes",
                "sensitive_categories": reader_gate.SENSITIVE_CATEGORIES,
                "low_risk_direct_edit_categories": reader_gate.LOW_RISK_CATEGORIES,
                "sensitive_change_count": 0,
                "options_and_fidelity_tradeoffs_presented": False,
                "unresolved_count": 0,
                "unapproved_applied_count": 0,
                "target_sha256": target_hash,
            }
        ),
        encoding="utf-8",
    )
    (project / "human-feedback-learning.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "gate": "human_feedback_learning",
                "source_sha256": source_hash,
                "input_target_sha256": target_hash,
                "feedback_item_count": 0,
                "reusable_principle_count": 0,
                "every_item_assessed": True,
                "local_preferences_separated_from_reusable_principles": True,
                "full_document_analogue_scan_completed": True,
                "sensitive_feedback_routed_to_commissioner": True,
                "unresolved_sensitive_feedback_count": 0,
            }
        ),
        encoding="utf-8",
    )
    (project / "post-reader-chinese-recheck.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "scope": "full_document",
                "status": "PASS",
                "source_sha256": source_hash,
                "target_sha256": target_hash,
            }
        ),
        encoding="utf-8",
    )
    (project / "post-reader-semantic-regression.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "scope": "full_document",
                "source_sha256": source_hash,
                "target_sha256": target_hash,
                "directions": {
                    "chinese_to_english": "PASS",
                    "english_to_chinese": "PASS",
                },
                "unapproved_omission_count": 0,
                "unapproved_addition_count": 0,
            }
        ),
        encoding="utf-8",
    )


def test_reader_gate_accepts_complete_isolated_zero_blocker_evidence(tmp_path):
    build_reader_gate_fixture(tmp_path)
    report = reader_gate.validate_reader_gate(tmp_path)
    assert report["status"] == "PASS"
    assert report["final_reader_blockers"] == {
        "general_nonfiction_editor": 0,
        "english_dharma_editor": 0,
    }
    assert report["unapproved_omission_count"] == 0
    assert report["unapproved_addition_count"] == 0
    assert report["final_reader_actionable_findings"] == {
        "general_nonfiction_editor": 0,
        "english_dharma_editor": 0,
    }


def test_reader_gate_rejects_reader_source_visibility(tmp_path):
    build_reader_gate_fixture(tmp_path)
    path = tmp_path / "english-reader-final-general.json"
    report = json.loads(path.read_text(encoding="utf-8"))
    report["isolation"]["source_side_material_visible"] = True
    path.write_text(json.dumps(report), encoding="utf-8")
    with pytest.raises(reader_gate.ReaderGateError, match="source-side material"):
        reader_gate.validate_reader_gate(tmp_path)


def test_reader_gate_rejects_chinese_in_reader_visible_manuscript(tmp_path):
    build_reader_gate_fixture(tmp_path)
    path = tmp_path / "english-reader-initial-manuscript.txt"
    path.write_text("English title\n中文锚点\n", encoding="utf-8")
    with pytest.raises(reader_gate.ReaderGateError, match="exposes Chinese"):
        reader_gate.validate_reader_gate(tmp_path)


def test_reader_gate_rejects_final_blocker_and_unapproved_addition(tmp_path):
    build_reader_gate_fixture(tmp_path)
    reader_path = tmp_path / "english-reader-final-dharma.json"
    reader = json.loads(reader_path.read_text(encoding="utf-8"))
    reader["blocker_count"] = 1
    reader["unresolved_actionable_count"] = 1
    reader["findings"] = [{"id": "D1", "blocker": True, "actionable": True}]
    reader_path.write_text(json.dumps(reader), encoding="utf-8")
    with pytest.raises(reader_gate.ReaderGateError, match="final blocker"):
        reader_gate.validate_reader_gate(tmp_path)

    reader["blocker_count"] = 0
    reader["unresolved_actionable_count"] = 0
    reader["findings"] = []
    reader_path.write_text(json.dumps(reader), encoding="utf-8")
    regression_path = tmp_path / "post-reader-semantic-regression.json"
    regression = json.loads(regression_path.read_text(encoding="utf-8"))
    regression["unapproved_addition_count"] = 1
    regression_path.write_text(json.dumps(regression), encoding="utf-8")
    with pytest.raises(reader_gate.ReaderGateError, match="unapproved addition"):
        reader_gate.validate_reader_gate(tmp_path)


def test_reader_gate_rejects_blocker_count_that_hides_a_blocking_finding(tmp_path):
    build_reader_gate_fixture(tmp_path)
    path = tmp_path / "english-reader-final-general.json"
    report = json.loads(path.read_text(encoding="utf-8"))
    report["findings"] = [{"id": "G1", "blocker": True, "actionable": False}]
    path.write_text(json.dumps(report), encoding="utf-8")
    with pytest.raises(reader_gate.ReaderGateError, match="does not match findings"):
        reader_gate.validate_reader_gate(tmp_path)


def test_reader_gate_requires_commissioner_tradeoff_and_approval(tmp_path):
    build_reader_gate_fixture(tmp_path)
    path = tmp_path / "commissioner-decisions.json"
    decisions = json.loads(path.read_text(encoding="utf-8"))
    decisions["sensitive_change_count"] = 1
    decisions["unapproved_applied_count"] = 1
    path.write_text(json.dumps(decisions), encoding="utf-8")
    with pytest.raises(reader_gate.ReaderGateError, match="options and fidelity tradeoffs"):
        reader_gate.validate_reader_gate(tmp_path)

    decisions["options_and_fidelity_tradeoffs_presented"] = True
    path.write_text(json.dumps(decisions), encoding="utf-8")
    with pytest.raises(reader_gate.ReaderGateError, match="does not match applied decisions"):
        reader_gate.validate_reader_gate(tmp_path)


def test_reader_gate_rejects_final_nonblocking_actionable_finding(tmp_path):
    build_reader_gate_fixture(tmp_path)
    path = tmp_path / "english-reader-final-general.json"
    report = json.loads(path.read_text(encoding="utf-8"))
    report["unresolved_actionable_count"] = 1
    report["findings"] = [{"id": "G1", "blocker": False, "actionable": True}]
    path.write_text(json.dumps(report), encoding="utf-8")
    with pytest.raises(reader_gate.ReaderGateError, match="final actionable finding"):
        reader_gate.validate_reader_gate(tmp_path)


def test_reader_gate_requires_full_document_human_feedback_learning_scan(tmp_path):
    build_reader_gate_fixture(tmp_path)
    path = tmp_path / "human-feedback-learning.json"
    record = json.loads(path.read_text(encoding="utf-8"))
    record["feedback_item_count"] = 1
    record["reusable_principle_count"] = 1
    record["full_document_analogue_scan_completed"] = False
    path.write_text(json.dumps(record), encoding="utf-8")
    with pytest.raises(reader_gate.ReaderGateError, match="analogue scan is incomplete"):
        reader_gate.validate_reader_gate(tmp_path)


def test_reader_gate_requires_named_approval_for_applied_sensitive_change(tmp_path):
    build_reader_gate_fixture(tmp_path)
    reader_path = tmp_path / "english-reader-initial-general.json"
    reader = json.loads(reader_path.read_text(encoding="utf-8"))
    reader["findings"] = [{"id": "G1", "blocker": False, "actionable": True}]
    reader["unresolved_actionable_count"] = 1
    reader_path.write_text(json.dumps(reader), encoding="utf-8")

    adjudication_path = tmp_path / "english-reader-adjudication.json"
    adjudication = json.loads(adjudication_path.read_text(encoding="utf-8"))
    adjudication["decision_count"] = 1
    adjudication["decisions"] = [
        {
            "reader_role": "general_nonfiction_editor",
            "finding_id": "G1",
            "risk_class": "sensitive",
            "category": "person_relation_or_ambiguous_referent",
            "disposition": "commissioner_choice",
            "source_evidence": ["佛法的道德观"],
            "fidelity_rationale": "The change selects a person relation.",
            "applied": True,
            "current_english": "People can see this.",
            "proposed_english": "We can see this.",
            "reason": "More direct spoken English.",
            "fidelity_effect": "Changes the implied subject.",
        }
    ]
    adjudication_path.write_text(json.dumps(adjudication), encoding="utf-8")
    with pytest.raises(reader_gate.ReaderGateError, match="commissioner decision is missing"):
        reader_gate.validate_reader_gate(tmp_path)


def test_reader_gate_rejects_source_evidence_not_found_in_source(tmp_path):
    build_reader_gate_fixture(tmp_path)
    reader_path = tmp_path / "english-reader-initial-general.json"
    reader = json.loads(reader_path.read_text(encoding="utf-8"))
    reader["findings"] = [{"id": "G1", "blocker": False, "actionable": True}]
    reader["unresolved_actionable_count"] = 1
    reader_path.write_text(json.dumps(reader), encoding="utf-8")
    adjudication_path = tmp_path / "english-reader-adjudication.json"
    adjudication = json.loads(adjudication_path.read_text(encoding="utf-8"))
    adjudication["decision_count"] = 1
    adjudication["decisions"] = [
        {
            "reader_role": "general_nonfiction_editor",
            "finding_id": "G1",
            "risk_class": "low_risk",
            "category": "collocation",
            "disposition": "reject",
            "source_evidence": ["这段文字不在原文中"],
            "fidelity_rationale": "The proposed change lacks source support.",
            "applied": False,
            "checked_against_full_chinese": True,
        }
    ]
    adjudication_path.write_text(json.dumps(adjudication), encoding="utf-8")
    with pytest.raises(
        reader_gate.ReaderGateError,
        match="source evidence is not a literal span of source.dj",
    ):
        reader_gate.validate_reader_gate(tmp_path)


def build_post_edit_fixture(project: Path) -> None:
    build_reader_gate_fixture(project)
    baseline_target = project / "target-pre-postedit.dj"
    baseline_target.write_text((project / "target.dj").read_text(encoding="utf-8"), encoding="utf-8")
    source_hash = post_edit_validator.sha256_file(project / "source.dj")
    baseline_hash = post_edit_validator.sha256_file(baseline_target)
    semantic_map_path = project / "post-edit-chinese-semantic-map.jsonl"
    source_text = (project / "source.dj").read_text(encoding="utf-8").strip()
    semantic_map_path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "workflow_version": "1.2.0",
                "paragraph_id": "L001",
                "source_line": 1,
                "source_sha256": source_hash,
                "source_text": source_text,
                "source_line_sha256": post_edit_validator.sha256_text(source_text),
                "source_only": True,
                "existing_english_visible": False,
                "record_kind": "substantive",
                "propositions": [
                    {
                        "meaning": "文章讨论佛法中的道德观。",
                        "source_evidence": [source_text],
                    }
                ],
                "semantic_roles": {},
                "logical_relations": [],
                "protected_constraints": [],
                "ambiguities": [],
                "status": "safe",
            },
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    (project / "post-edit-baseline.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "workflow_version": "1.2.0",
                "mode": "retrofit_existing_translation",
                "source_sha256": source_hash,
                "baseline_target_sha256": baseline_hash,
                "baseline_target_preserved": True,
                "full_translation_rerun": False,
                "bilingual_reviews_rerun": False,
                "upstream_t1_codex_evidence_complete": False,
                "claimed_status": "T1-Codex post-edit AI-reviewed draft",
                "source_only_semantic_map": {
                    "kind": "post_edit_source_only_map",
                    "artifact": "post-edit-chinese-semantic-map.jsonl",
                    "artifact_sha256": post_edit_validator.sha256_file(
                        semantic_map_path
                    ),
                    "source_sha256": source_hash,
                    "full_document_scope": True,
                    "existing_english_visible": False,
                    "visible_input_count": 1,
                    "visible_input_sha256": source_hash,
                    "session_id": "post-edit-source-only-semantic-map-session",
                    "prompt_sha256": "b" * 64,
                },
            }
        ),
        encoding="utf-8",
    )
    docx = project / "final-bilingual.docx"
    write_minimal_docx(
        docx,
        [
            (project / "source.dj").read_text(encoding="utf-8").strip(),
            (project / "target.dj").read_text(encoding="utf-8").strip(),
        ],
    )
    rendered_dir = project / "post-edit-rendered"
    rendered_dir.mkdir()
    rendered_page = rendered_dir / "page-001.png"
    rendered_page.write_bytes(
        base64.b64decode(
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
        )
    )
    docx_hash = post_edit_validator.sha256_file(docx)
    rendered_page_hash = post_edit_validator.sha256_file(rendered_page)
    render_receipt_path = project / "post-edit-render-receipt.json"
    render_receipt_path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "gate": "final_docx_render",
                "status": "PASS",
                "exit_code": 0,
                "rendered_from_docx_sha256": docx_hash,
                "page_count": 1,
                "output_format": "png",
                "renderer": "fixture-renderer",
                "renderer_version": "1.0",
                "started_at": "2026-09-01T00:00:00Z",
                "completed_at": "2026-09-01T00:00:01Z",
                "command_or_config_sha256": "c" * 64,
                "pages": [
                    {
                        "artifact": "post-edit-rendered/page-001.png",
                        "sha256": rendered_page_hash,
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    (project / "post-edit-delivery-record.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "gate": "clean_alternating_bilingual_docx",
                "source_sha256": source_hash,
                "target_sha256": post_edit_validator.sha256_file(project / "target.dj"),
                "expected_pair_count": 1,
                "actual_pair_count": 1,
                "alternating_source_then_target": True,
                "titles_toc_and_headings_alternating": True,
                "incoming_english_excluded": True,
                "internal_material_excluded": True,
                "comments_absent": True,
                "tracked_changes_absent": True,
                "placeholders_absent": True,
                "font_coverage_pass": True,
                "docx_structure_pass": True,
                "zip_integrity_pass": True,
                "text_fidelity_pass": True,
                "rendered_page_count": 1,
                "visually_inspected_page_count": 1,
                "rendered_pages": [
                    {
                        "artifact": "post-edit-rendered/page-001.png",
                        "sha256": rendered_page_hash,
                        "rendered_from_docx_sha256": docx_hash,
                        "inspected": True,
                    }
                ],
                "render_receipt_artifact": render_receipt_path.name,
                "render_receipt_sha256": post_edit_validator.sha256_file(
                    render_receipt_path
                ),
                "forbidden_placeholder_strings": ["TODO", "TBD", "{{", "}}"],
                "final_docx_path": str(docx),
                "final_docx_sha256": docx_hash,
            }
        ),
        encoding="utf-8",
    )


def write_minimal_docx(path: Path, paragraphs: list[str]) -> None:
    body = "".join(
        f'<w:p><w:r><w:t xml:space="preserve">{escape(text)}</w:t></w:r></w:p>'
        for text in paragraphs
    )
    content_types = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
</Types>"""
    relationships = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
</Relationships>"""
    document = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:body>{body}<w:sectPr/></w:body>
</w:document>"""
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", content_types)
        archive.writestr("_rels/.rels", relationships)
        archive.writestr("word/document.xml", document)


def test_post_translation_editing_accepts_no_retranslation_retrofit(tmp_path):
    build_post_edit_fixture(tmp_path)
    report = post_edit_validator.validate_post_translation_editing(tmp_path)
    assert report["status"] == "PASS"
    assert report["mode"] == "retrofit_existing_translation"
    assert report["claimed_status"] == "T1-Codex post-edit AI-reviewed draft"


def test_post_translation_editing_rejects_overstated_status_and_rerun(tmp_path):
    build_post_edit_fixture(tmp_path)
    path = tmp_path / "post-edit-baseline.json"
    baseline = json.loads(path.read_text(encoding="utf-8"))
    baseline["claimed_status"] = "AI reviewed draft"
    path.write_text(json.dumps(baseline), encoding="utf-8")
    with pytest.raises(
        post_edit_validator.PostTranslationEditingError,
        match="overstated as full T1-Codex completion",
    ):
        post_edit_validator.validate_post_translation_editing(tmp_path)

    baseline["claimed_status"] = "T1-Codex post-edit AI-reviewed draft"
    baseline["full_translation_rerun"] = True
    path.write_text(json.dumps(baseline), encoding="utf-8")
    with pytest.raises(
        post_edit_validator.PostTranslationEditingError,
        match="unexpectedly reran translation",
    ):
        post_edit_validator.validate_post_translation_editing(tmp_path)


def test_post_translation_editing_rejects_boolean_only_upstream_completion(tmp_path):
    build_post_edit_fixture(tmp_path)
    path = tmp_path / "post-edit-baseline.json"
    baseline = json.loads(path.read_text(encoding="utf-8"))
    baseline["upstream_t1_codex_evidence_complete"] = True
    baseline["claimed_status"] = "AI reviewed draft"
    path.write_text(json.dumps(baseline), encoding="utf-8")
    with pytest.raises(
        post_edit_validator.PostTranslationEditingError,
        match="complete upstream evidence lacks reuse receipts",
    ):
        post_edit_validator.validate_post_translation_editing(tmp_path)


def test_post_edit_upstream_model_identity_is_derived_from_both_locks(tmp_path):
    skill_copy = tmp_path / "skill"
    references = skill_copy / "references"
    references.mkdir(parents=True)
    shutil.copy2(SKILL / "dependency-lock.json", skill_copy / "dependency-lock.json")
    shutil.copy2(
        SKILL / "references" / "production-lock.json",
        references / "production-lock.json",
    )
    locks = post_edit_validator.load_upstream_model_locks(skill_copy)
    assert locks["translation_and_self_review"]["provider"] == "openai-codex"
    assert "semantic_bridge_generation" in locks
    assert "semantic_bridge_challenge" in locks

    dependency_path = skill_copy / "dependency-lock.json"
    dependency = json.loads(dependency_path.read_text(encoding="utf-8"))
    dependency["models"]["semantic_bridge_generation"]["model"] = "wrong-model"
    dependency_path.write_text(json.dumps(dependency), encoding="utf-8")
    with pytest.raises(
        post_edit_validator.PostTranslationEditingError,
        match="dependency/production drift for semantic_bridge_generation",
    ):
        post_edit_validator.load_upstream_model_locks(skill_copy)


def test_post_translation_editing_accepts_hash_bound_complete_upstream_index(tmp_path):
    build_post_edit_fixture(tmp_path)
    path = tmp_path / "post-edit-baseline.json"
    baseline = json.loads(path.read_text(encoding="utf-8"))
    receipts = []
    model_locks = post_edit_validator.load_upstream_model_locks()
    for stage in post_edit_validator.UPSTREAM_INHERITANCE_STAGES:
        artifact = tmp_path / f"upstream-{stage}.json"
        if stage in model_locks:
            lock = model_locks[stage]
            execution_identity = {
                "kind": "model",
                "provider": lock["provider"],
                "model": "gpt-6-astra" if "allowed_model_efforts" in lock else lock["model"],
                "reasoning_effort": "high" if "allowed_model_efforts" in lock else lock["reasoning_effort"],
                "role": stage,
                "execution_surface": lock["execution_surface"],
                "request_or_session_id": f"fixture-{stage}",
            }
        else:
            execution_identity = {
                "kind": "tool",
                "tool_name": "fixture-deterministic-qa",
                "tool_version": "1.0",
                "command_or_config_sha256": "d" * 64,
            }
        artifact.write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "gate": "t1_codex_upstream_completion",
                    "stage": stage,
                    "source_sha256": baseline["source_sha256"],
                    "target_sha256": baseline["baseline_target_sha256"],
                    "scope": "full_document",
                    "status": "PASS",
                    "complete": True,
                    "execution_identity": execution_identity,
                }
            ),
            encoding="utf-8",
        )
        receipts.append(
            {
                "stage": stage,
                "artifact": artifact.name,
                "artifact_sha256": post_edit_validator.sha256_file(artifact),
                "source_sha256": baseline["source_sha256"],
                "baseline_target_sha256": baseline["baseline_target_sha256"],
                "scope": "full_document",
                "status": "PASS",
                "role_or_tool_identity_matches_recorded_configuration": True,
                "reused_without_rerun": True,
            }
        )
    baseline["upstream_t1_codex_evidence_complete"] = True
    baseline["claimed_status"] = "AI reviewed draft"
    baseline["upstream_reuse_receipts"] = receipts
    path.write_text(json.dumps(baseline), encoding="utf-8")
    report = post_edit_validator.validate_post_translation_editing(tmp_path)
    assert report["claimed_status"] == "AI reviewed draft"

    first_artifact = tmp_path / receipts[0]["artifact"]
    internal = json.loads(first_artifact.read_text(encoding="utf-8"))
    internal["source_sha256"] = "e" * 64
    first_artifact.write_text(json.dumps(internal), encoding="utf-8")
    receipts[0]["artifact_sha256"] = post_edit_validator.sha256_file(first_artifact)
    baseline["upstream_reuse_receipts"] = receipts
    path.write_text(json.dumps(baseline), encoding="utf-8")
    with pytest.raises(
        post_edit_validator.PostTranslationEditingError,
        match="internal source hash mismatch",
    ):
        post_edit_validator.validate_post_translation_editing(tmp_path)


def test_post_translation_editing_rejects_unbound_semantic_map(tmp_path):
    build_post_edit_fixture(tmp_path)
    (tmp_path / "post-edit-chinese-semantic-map.jsonl").write_text(
        '{"paragraph_id":"forged"}\n', encoding="utf-8"
    )
    with pytest.raises(
        post_edit_validator.PostTranslationEditingError,
        match="semantic map: artifact hash mismatch",
    ):
        post_edit_validator.validate_post_translation_editing(tmp_path)


def test_post_translation_editing_rejects_hash_bound_invalid_semantic_map_content(tmp_path):
    build_post_edit_fixture(tmp_path)
    semantic_path = tmp_path / "post-edit-chinese-semantic-map.jsonl"
    record = json.loads(semantic_path.read_text(encoding="utf-8"))
    record["source_text"] = "伪造的原文"
    semantic_path.write_text(json.dumps(record, ensure_ascii=False) + "\n", encoding="utf-8")
    baseline_path = tmp_path / "post-edit-baseline.json"
    baseline = json.loads(baseline_path.read_text(encoding="utf-8"))
    baseline["source_only_semantic_map"]["artifact_sha256"] = (
        post_edit_validator.sha256_file(semantic_path)
    )
    baseline_path.write_text(json.dumps(baseline), encoding="utf-8")
    with pytest.raises(
        post_edit_validator.PostTranslationEditingError,
        match="source text mismatch",
    ):
        post_edit_validator.validate_post_translation_editing(tmp_path)


def test_post_edit_semantic_map_requires_complete_nonblank_source_coverage(tmp_path):
    source = tmp_path / "source.dj"
    source.write_text("第一段原文\n第二段原文\n", encoding="utf-8")
    source_hash = post_edit_validator.sha256_file(source)
    first_line = "第一段原文"
    artifact = tmp_path / "post-edit-chinese-semantic-map.jsonl"
    artifact.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "workflow_version": "1.2.0",
                "paragraph_id": "L001",
                "source_line": 1,
                "source_sha256": source_hash,
                "source_text": first_line,
                "source_line_sha256": post_edit_validator.sha256_text(first_line),
                "source_only": True,
                "existing_english_visible": False,
                "record_kind": "substantive",
                "propositions": [
                    {"meaning": "第一段。", "source_evidence": [first_line]}
                ],
                "semantic_roles": {},
                "logical_relations": [],
                "protected_constraints": [],
                "ambiguities": [],
                "status": "safe",
            },
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    with pytest.raises(
        post_edit_validator.PostTranslationEditingError,
        match="full nonblank source coverage or order is incomplete",
    ):
        post_edit_validator.validate_post_edit_semantic_map(
            source,
            artifact,
            source_hash=source_hash,
        )


def test_post_edit_semantic_map_rejects_safe_ambiguity_and_unsupported_we(tmp_path):
    build_post_edit_fixture(tmp_path)
    semantic_path = tmp_path / "post-edit-chinese-semantic-map.jsonl"
    baseline_path = tmp_path / "post-edit-baseline.json"

    record = json.loads(semantic_path.read_text(encoding="utf-8"))
    record["ambiguities"] = [
        {
            "id": "A1",
            "description": "The person scope needs a decision.",
            "source_evidence": [record["source_text"]],
        }
    ]
    semantic_path.write_text(json.dumps(record, ensure_ascii=False) + "\n", encoding="utf-8")
    baseline = json.loads(baseline_path.read_text(encoding="utf-8"))
    baseline["source_only_semantic_map"]["artifact_sha256"] = (
        post_edit_validator.sha256_file(semantic_path)
    )
    baseline_path.write_text(json.dumps(baseline), encoding="utf-8")
    with pytest.raises(
        post_edit_validator.PostTranslationEditingError,
        match="safe record retains unresolved ambiguities",
    ):
        post_edit_validator.validate_post_translation_editing(tmp_path)

    record["ambiguities"] = []
    record["propositions"][0]["meaning"] = "我们讨论佛法中的道德观。"
    record["person_scope"] = {
        "uniquely_includes_speaker_and_audience": True,
        "source_evidence": [record["source_text"]],
    }
    semantic_path.write_text(json.dumps(record, ensure_ascii=False) + "\n", encoding="utf-8")
    baseline["source_only_semantic_map"]["artifact_sha256"] = (
        post_edit_validator.sha256_file(semantic_path)
    )
    baseline_path.write_text(json.dumps(baseline), encoding="utf-8")
    with pytest.raises(
        post_edit_validator.PostTranslationEditingError,
        match="safe record adds 我们 without commissioner approval",
    ):
        post_edit_validator.validate_post_translation_editing(tmp_path)


def test_post_edit_semantic_map_accepts_hash_bound_named_commissioner_resolution(tmp_path):
    build_post_edit_fixture(tmp_path)
    semantic_path = tmp_path / "post-edit-chinese-semantic-map.jsonl"
    record = json.loads(semantic_path.read_text(encoding="utf-8"))
    record["status"] = "commissioner_resolved"
    record["ambiguities"] = [
        {
            "id": "A1",
            "description": "The title scope was confirmed.",
            "source_evidence": [record["source_text"]],
        }
    ]
    decision_path = tmp_path / "semantic-map-commissioner-L001.json"
    decision_path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "gate": "post_edit_semantic_map_commissioner_decision",
                "status": "approved",
                "approved": True,
                "named_commissioner": "Named commissioner",
                "decision_id": "DEC-L001",
                "source_sha256": record["source_sha256"],
                "source_line_sha256": record["source_line_sha256"],
                "paragraph_id": "L001",
                "ambiguity_ids": ["A1"],
                "selected_resolution": "Retain the source-bounded title scope.",
                "source_evidence": [record["source_text"]],
                "person_scope_approved": False,
            }
        ),
        encoding="utf-8",
    )
    record["commissioner_decision"] = {
        "artifact": decision_path.name,
        "artifact_sha256": post_edit_validator.sha256_file(decision_path),
    }
    semantic_path.write_text(json.dumps(record, ensure_ascii=False) + "\n", encoding="utf-8")
    baseline_path = tmp_path / "post-edit-baseline.json"
    baseline = json.loads(baseline_path.read_text(encoding="utf-8"))
    baseline["source_only_semantic_map"]["artifact_sha256"] = (
        post_edit_validator.sha256_file(semantic_path)
    )
    baseline_path.write_text(json.dumps(baseline), encoding="utf-8")
    report = post_edit_validator.validate_post_translation_editing(tmp_path)
    assert report["status"] == "PASS"


def test_post_translation_editing_rejects_render_receipt_for_another_docx(tmp_path):
    build_post_edit_fixture(tmp_path)
    receipt_path = tmp_path / "post-edit-render-receipt.json"
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    receipt["rendered_from_docx_sha256"] = "f" * 64
    receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
    delivery_path = tmp_path / "post-edit-delivery-record.json"
    delivery = json.loads(delivery_path.read_text(encoding="utf-8"))
    delivery["render_receipt_sha256"] = post_edit_validator.sha256_file(receipt_path)
    delivery_path.write_text(json.dumps(delivery), encoding="utf-8")
    with pytest.raises(
        post_edit_validator.PostTranslationEditingError,
        match="rendered DOCX hash mismatch",
    ):
        post_edit_validator.validate_post_translation_editing(tmp_path)


def test_post_translation_editing_rejects_corrupt_docx_even_with_matching_receipt_hash(tmp_path):
    build_post_edit_fixture(tmp_path)
    docx = tmp_path / "final-bilingual.docx"
    docx.write_bytes(b"not a docx")
    delivery_path = tmp_path / "post-edit-delivery-record.json"
    delivery = json.loads(delivery_path.read_text(encoding="utf-8"))
    delivery["final_docx_sha256"] = post_edit_validator.sha256_file(docx)
    delivery_path.write_text(json.dumps(delivery), encoding="utf-8")
    with pytest.raises(
        post_edit_validator.PostTranslationEditingError,
        match="not a DOCX ZIP package",
    ):
        post_edit_validator.validate_post_translation_editing(tmp_path)


def test_post_translation_editing_rejects_reversed_docx_pair_order(tmp_path):
    build_post_edit_fixture(tmp_path)
    docx = tmp_path / "final-bilingual.docx"
    write_minimal_docx(
        docx,
        [
            (tmp_path / "target.dj").read_text(encoding="utf-8").strip(),
            (tmp_path / "source.dj").read_text(encoding="utf-8").strip(),
        ],
    )
    delivery_path = tmp_path / "post-edit-delivery-record.json"
    delivery = json.loads(delivery_path.read_text(encoding="utf-8"))
    delivery["final_docx_sha256"] = post_edit_validator.sha256_file(docx)
    delivery_path.write_text(json.dumps(delivery), encoding="utf-8")
    with pytest.raises(
        post_edit_validator.PostTranslationEditingError,
        match="actual DOCX paragraph order or text fidelity mismatch",
    ):
        post_edit_validator.validate_post_translation_editing(tmp_path)


def test_t1_codex_install_prompt_supports_personal_and_business_without_secrets():
    prompt = (ROOT / "INSTALL_PROMPT-T1-CODEX.zh-CN.md").read_text(encoding="utf-8")
    assert "https://github.com/zhi12458/mpi-strategy-c-codex.git" in prompt
    assert "t1-codex-v1.2.0-candidate.2" in prompt
    assert "python scripts/install_runtime.py" in prompt
    assert "PERSONAL" in prompt
    assert "BUSINESS" in prompt
    assert "旧称 TEAM" in prompt
    assert "不得要求我在聊天中发送密码、验证码、Key 或 token" in prompt
    assert "python scripts/credential_store.py" not in prompt
    assert "deepseek_credential_present: true" in prompt
    assert "base_ready: true" in prompt
    assert "public_smoke_status: PASS" in prompt
    assert "全部使用 Codex" in prompt


def test_manifest_detects_a_modified_skill_file(tmp_path):
    copy = tmp_path / "mpi-strategy-t1-codex"
    shutil.copytree(SKILL, copy)
    (copy / "SKILL.md").write_text("modified\n", encoding="utf-8")
    with pytest.raises(validator.ValidationError, match="manifest hash mismatch"):
        validator.verify_manifest(copy)
