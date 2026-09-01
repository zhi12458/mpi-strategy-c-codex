#!/usr/bin/env python3
"""Validate the immutable T1-Codex Skill package and production-role policy."""

from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any


SKILL_DIR = Path(__file__).resolve().parents[1]
MANIFEST = SKILL_DIR / "MANIFEST.sha256"
DEPENDENCY_LOCK = SKILL_DIR / "dependency-lock.json"
PRODUCTION_LOCK = SKILL_DIR / "references" / "production-lock.json"


class ValidationError(RuntimeError):
    """The package is incomplete or violates a production invariant."""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_object(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValidationError(f"invalid JSON: {path}") from exc
    if not isinstance(value, dict):
        raise ValidationError(f"JSON root must be an object: {path}")
    return value


def verify_manifest(skill_dir: Path = SKILL_DIR) -> dict[str, Any]:
    manifest = skill_dir / "MANIFEST.sha256"
    if not manifest.is_file():
        raise ValidationError("MANIFEST.sha256 is missing")
    listed: dict[str, str] = {}
    for number, line in enumerate(
        manifest.read_text(encoding="utf-8").splitlines(), start=1
    ):
        if not line.strip():
            continue
        match = re.fullmatch(r"([0-9a-f]{64})  (.+)", line)
        if not match:
            raise ValidationError(f"invalid manifest line {number}")
        expected, relative = match.groups()
        candidate = skill_dir / relative
        if not candidate.is_file():
            raise ValidationError(f"manifest file is missing: {relative}")
        actual = sha256_file(candidate)
        if actual != expected:
            raise ValidationError(f"manifest hash mismatch: {relative}")
        listed[relative] = expected

    required = {
        "SKILL.md",
        "agents/openai.yaml",
        "dependency-lock.json",
        "references/production-lock.json",
        "references/workflow.md",
        "references/chinese-semantic-segmentation.md",
        "references/installation.md",
        "references/readiness.md",
        "references/english-only-reader-gate.md",
        "references/post-translation-editing.md",
        "scripts/confirm_workspace.py",
        "scripts/install_runtime.py",
        "scripts/validate_semantic_segmentation.py",
        "scripts/validate_reader_gate.py",
        "scripts/validate_post_translation_editing.py",
        "scripts/validate_package.py",
    }
    if not required.issubset(listed):
        raise ValidationError(
            "manifest omits required files: " + ", ".join(sorted(required - set(listed)))
        )
    actual_files = {
        path.relative_to(skill_dir).as_posix()
        for path in skill_dir.rglob("*")
        if path.is_file()
        and path != manifest
        and "__pycache__" not in path.parts
        and path.suffix not in {".pyc", ".pyo"}
    }
    if set(listed) != actual_files:
        unlisted = sorted(actual_files - set(listed))
        stale = sorted(set(listed) - actual_files)
        details = []
        if unlisted:
            details.append("unlisted=" + ",".join(unlisted))
        if stale:
            details.append("missing=" + ",".join(stale))
        raise ValidationError("manifest coverage mismatch: " + "; ".join(details))
    return {
        "status": "PASS",
        "path": str(manifest),
        "sha256": sha256_file(manifest),
        "file_count": len(listed),
    }


def require(value: bool, message: str) -> None:
    if not value:
        raise ValidationError(message)


def validate_policy(skill_dir: Path = SKILL_DIR) -> dict[str, Any]:
    dependency = load_object(skill_dir / "dependency-lock.json")
    production = load_object(skill_dir / "references" / "production-lock.json")

    require(dependency.get("strategy_id") == "T1-CODEX", "wrong strategy_id")
    require(
        dependency.get("workflow_version") == production.get("workflow_version"),
        "workflow versions do not match",
    )
    require(
        production.get("production_default_selected") is True,
        "T1-Codex is not selected as production default",
    )
    require(
        production.get("release_ready") is False
        and dependency.get("release_ready") is False,
        "candidate must remain non-release-ready before validation",
    )
    require(
        production.get("source_authority", {}).get("sole_semantic_authority") is True,
        "source.dj is not the sole semantic authority",
    )
    require(
        production.get("source_authority", {}).get("bridge_is_authoritative") is False,
        "semantic bridge must not be authoritative",
    )
    require(
        production.get("source_authority", {}).get(
            "semantic_segmentation_is_authoritative"
        )
        is False,
        "Chinese semantic segmentation must not be authoritative",
    )

    workspace = dependency.get("openai_workspace_policy", {})
    require(
        workspace.get("allowed_workspace_kinds") == ["personal", "business"],
        "Personal and Business workspace support is not locked",
    )
    require(
        workspace.get("accepted_confirmation_tokens")
        == ["PERSONAL", "BUSINESS", "TEAM"],
        "workspace confirmation tokens are not locked",
    )
    require(
        workspace.get("team_normalizes_to") == "business",
        "the legacy Team name is not normalized to Business",
    )
    require(
        workspace.get("interactive_confirmation_script")
        == "scripts/confirm_workspace.py",
        "workspace confirmation script is not locked",
    )
    require(
        workspace.get("workspace_identifiers_recorded") is False
        and workspace.get("credentials_recorded") is False,
        "workspace confirmation privacy policy is unsafe",
    )
    production_workspace = production.get("openai_workspace_policy", {})
    require(
        production_workspace.get("allowed") == ["Personal", "ChatGPT Business"],
        "production lock does not allow Personal and Business",
    )
    runtime_installer = dependency.get("runtime_installer", {})
    require(
        runtime_installer.get("script") == "scripts/install_runtime.py",
        "fail-closed runtime installer is not locked",
    )
    require(
        runtime_installer.get("interactive") is True
        and runtime_installer.get("fail_closed") is True,
        "runtime installer must be interactive and fail closed",
    )
    require(
        runtime_installer.get("deepseek_masked_prompt_required_when_missing") is True
        and runtime_installer.get("base_ready_true_required") is True,
        "runtime installer does not require credentials and base readiness",
    )
    require(
        runtime_installer.get("static_package_validation_is_runtime_readiness") is False,
        "static validation must not imply runtime readiness",
    )

    modes = production.get("workflow_modes", {})
    require(
        modes.get("t1_codex_quality", {}).get("production_default") is True,
        "T1-Codex quality mode is not default",
    )
    require(
        modes.get("t1_omp_rollback", {}).get("production_default") is False,
        "T1-OMP rollback must not be default",
    )
    require(
        modes.get("full_pretranslation_experiments", {}).get("production_default")
        is False,
        "full pretranslation experiments must not be default",
    )
    post_edit_mode = modes.get("post_translation_native_editing", {})
    require(
        post_edit_mode.get("production_default_after_completed_translation") is True
        and post_edit_mode.get("full_translation_rerun_default") is False
        and post_edit_mode.get("bilingual_review_rerun_default") is False
        and post_edit_mode.get("exact_hash_upstream_evidence_reuse_only") is True,
        "post-translation editing does not preserve the no-retranslation boundary",
    )
    require(
        post_edit_mode.get("status_without_complete_upstream_evidence")
        == "T1-Codex post-edit AI-reviewed draft",
        "post-translation editing can overstate incomplete upstream evidence",
    )

    roles = production.get("model_roles", {})
    codex_roles = (
        "semantic_decisions",
        "chinese_semantic_segmentation",
        "post_translation_chinese_semantic_map",
        "translation_and_self_review",
        "review_application_round_1",
        "review_application_round_2",
        "title_audit",
        "concision_and_chinese_recheck",
    )
    for role in codex_roles:
        spec = roles.get(role, {})
        require(spec.get("model") == "gpt-5.6-sol", f"wrong model for {role}")
        require(spec.get("reasoning_effort") == "high", f"wrong effort for {role}")
        require(spec.get("execution_surface") == "current Codex task", f"wrong surface for {role}")

    pro_roles = (
        "semantic_bridge_challenge",
        "chinese_semantic_segmentation_review",
        "bilingual_review_round_1",
        "bilingual_review_round_2",
        "post_concision_semantic_regression",
    )
    for role in pro_roles:
        spec = roles.get(role, {})
        require(spec.get("model") == "deepseek-v4-pro", f"wrong model for {role}")
        require(spec.get("reasoning_effort") == "max", f"wrong effort for {role}")
        require("OMP" in str(spec.get("execution_surface")), f"wrong surface for {role}")

    bridge = roles.get("semantic_bridge_generation", {})
    require(bridge.get("model") == "deepseek-v4-flash", "wrong bridge model")
    require(bridge.get("reasoning_effort") == "high", "wrong bridge effort")
    require(bridge.get("scope") == "high-risk source units only", "bridge is not high-risk-only")
    require(bridge.get("writes_english") is False, "bridge must not write English")

    adoption = production.get("t1_1_2_adoption_policy", {})
    require(
        "mandatory full-document Sol semantic restructuring"
        in adoption.get("not_default", []),
        "T1.1.2 full restructuring exclusion is missing",
    )
    require(
        "fresh post-concision bidirectional semantic regression"
        in adoption.get("adopted", []),
        "post-concision semantic regression is not adopted",
    )

    segmentation = production.get("chinese_semantic_segmentation", {})
    require(segmentation.get("mandatory") is True, "Chinese semantic segmentation is not mandatory")
    require(
        segmentation.get("source_authority") == "source.dj"
        and segmentation.get("conflict_resolution") == "source.dj wins",
        "semantic segmentation does not preserve source authority",
    )
    require(
        segmentation.get("required_scope")
        == "every nonblank source line including structural lines",
        "semantic segmentation does not cover the complete source",
    )
    added_we = segmentation.get("added_we_rule", {})
    require(
        added_we.get("allowed_only_when_source_includes_speaker_and_audience")
        is True
        and added_we.get("engagement_alone_is_source_evidence") is False
        and added_we.get("commissioner_decision_required_before_application")
        is True,
        "the guarded 我们 rule is incomplete",
    )
    require(
        segmentation.get("independent_pro_review_required") is True
        and segmentation.get("translation_receives_source_and_segmentation_together")
        is True,
        "semantic segmentation review or handoff is incomplete",
    )
    require(
        segmentation.get("required_artifacts")
        == [
            "chinese-semantic-segmentation.jsonl",
            "chinese-semantic-segmentation.dj",
            "chinese-semantic-segmentation-review.jsonl",
        ],
        "semantic segmentation artifacts are not locked",
    )

    gates = set(production.get("required_document_gates", []))
    require("fresh_bilingual_review_round_1" in gates, "round one gate missing")
    require("fresh_bilingual_review_round_2" in gates, "round two gate missing")
    require(
        "fresh_post_concision_bidirectional_semantic_regression" in gates,
        "semantic regression gate missing",
    )
    require("named_human_release_gate" in gates, "human release gate missing")
    for gate in (
        "complete_source_bound_chinese_semantic_segmentation",
        "fresh_pro_max_chinese_segmentation_review",
        "resolved_subject_person_and_logic_decisions",
        "semantic_segmentation_receipt_validation",
    ):
        require(gate in gates, f"semantic segmentation gate missing: {gate}")
    reader_policy = production.get("english_only_reader_gate", {})
    require(reader_policy.get("mandatory") is True, "English-only reader gate is not mandatory")
    require(
        reader_policy.get("initial_and_final_roles")
        == ["general nonfiction editor", "English Buddhist/Dharma editor"],
        "English-only reader roles are not locked",
    )
    require(
        reader_policy.get("reader_visible_manuscripts_retained") is True
        and reader_policy.get("reader_visible_manuscripts_must_contain_no_chinese")
        is True
        and reader_policy.get(
            "reader_visible_manuscripts_bound_to_canonical_target_hash"
        )
        is True,
        "reader-visible manuscript evidence is incomplete",
    )
    require(
        reader_policy.get("translator_must_recheck_every_finding_against_full_chinese")
        is True
        and reader_policy.get(
            "source_evidence_must_be_literal_span_of_hash_bound_source"
        )
        is True,
        "reader findings are not bound to a full Chinese recheck",
    )
    require(
        reader_policy.get("commissioner_approval_categories")
        == [
            "doctrine",
            "meaning_or_degree",
            "terminology",
            "author_voice_or_tone",
            "metaphor",
            "numbers",
            "person_relation_or_ambiguous_referent",
            "information_addition_or_deletion",
            "sentence_split_or_merge",
            "paragraph_structure",
            "quotation_wording",
            "culture_specific_explanatory_translation",
        ],
        "commissioner-sensitive reader categories are incomplete",
    )
    require(
        reader_policy.get("low_risk_direct_edit_categories")
        == [
            "grammar",
            "punctuation",
            "collocation",
            "accidental_repetition",
            "unnecessary_passive",
            "uniquely_recoverable_referent",
            "meaning_neutral_simplification",
            "ordinary_english_polish",
        ],
        "low-risk reader edit categories are incomplete",
    )
    require(
        reader_policy.get("sensitive_proposal_required_fields")
        == [
            "current_english",
            "proposed_english",
            "reason",
            "fidelity_effect",
            "source_evidence",
            "commissioner_decision",
        ]
        and reader_policy.get("every_finding_risk_classified") is True,
        "sensitive reader proposal evidence is incomplete",
    )
    require(
        reader_policy.get("options_and_fidelity_tradeoffs_required_before_sensitive_change")
        is True,
        "sensitive reader changes do not require options and fidelity tradeoffs",
    )
    require(
        reader_policy.get("post_edit_full_chinese_recheck_required") is True
        and reader_policy.get("post_edit_full_document_bidirectional_regression_required")
        is True,
        "post-reader Chinese and semantic reruns are not locked",
    )
    require(
        reader_policy.get("fresh_final_reader_sessions_required") is True,
        "fresh final English-only reader sessions are not required",
    )
    reader_roles = roles
    for role in ("english_only_general_reader", "english_only_dharma_reader"):
        spec = reader_roles.get(role, {})
        require(
            "isolated English-only session" in str(spec.get("execution_surface")),
            f"{role} is not isolated and English-only",
        )
        require(
            spec.get("visible_inputs")
            == [
                "readable English-only manuscript generated from and hash-bound to current target"
            ],
            f"{role} can see extra inputs",
        )
        require(
            spec.get("raw_djot_with_chinese_anchors_forbidden") is True,
            f"{role} can see raw Djot with Chinese anchors",
        )
        forbidden = set(spec.get("forbidden_inputs", []))
        require(
            {"Chinese", "term map", "old translations", "prior feedback", "other reader output"}.issubset(forbidden),
            f"{role} isolation exclusions are incomplete",
        )
    for gate in (
        "post_translation_baseline_and_reuse_freeze",
        "source_only_post_edit_chinese_semantic_map",
        "isolated_english_only_general_reader_initial",
        "isolated_english_only_dharma_reader_initial",
        "source_based_reader_finding_adjudication",
        "reader_findings_low_risk_or_sensitive_classified",
        "human_feedback_learning_and_full_document_analogue_scan",
        "commissioner_approval_for_sensitive_reader_changes",
        "post_reader_complete_original_chinese_recheck",
        "post_reader_full_document_bidirectional_semantic_regression",
        "isolated_english_only_general_reader_final_zero_blockers",
        "isolated_english_only_dharma_reader_final_zero_blockers",
        "zero_unapproved_omissions_additions_or_sensitive_changes",
    ):
        require(gate in gates, f"document reader gate missing: {gate}")
    require(
        "clean_alternating_bilingual_docx_internal_material_exclusion" in gates,
        "clean alternating bilingual DOCX gate is missing",
    )

    post_edit = production.get("post_translation_editing", {})
    require(
        post_edit.get("reference") == "references/post-translation-editing.md"
        and post_edit.get("source_authority") == "source.dj"
        and post_edit.get("source_only_semantic_map_artifact_sha256_required")
        is True
        and post_edit.get("semantic_map_reader_facing_delivery_allowed") is False,
        "post-translation editing source or delivery boundary is incomplete",
    )
    inheritance = post_edit.get("upstream_status_inheritance", {})
    require(
        inheritance.get("boolean_declaration_sufficient") is False
        and inheritance.get("required_stages")
        == [
            "source_analysis",
            "semantic_bridge_generation",
            "semantic_bridge_challenge",
            "semantic_decisions",
            "chinese_semantic_segmentation",
            "chinese_semantic_segmentation_review",
            "translation_and_self_review",
            "bilingual_review_round_1",
            "review_application_round_1",
            "bilingual_review_round_2",
            "review_application_round_2",
            "title_audit",
            "concision_and_chinese_recheck",
            "post_concision_semantic_regression",
            "deterministic_content_qa",
        ]
        and inheritance.get("receipt_required_fields")
        == [
            "stage",
            "artifact",
            "artifact_sha256",
            "source_sha256",
            "baseline_target_sha256",
            "scope",
            "status",
            "role_or_tool_identity_matches_recorded_configuration",
            "reused_without_rerun",
        ]
        and inheritance.get("inner_completion_receipt_required") is True
        and inheritance.get(
            "inner_receipt_source_target_scope_status_and_identity_validated"
        )
        is True
        and inheritance.get("model_stage_identity_compared_with_production_lock")
        is True
        and inheritance.get("locks_loaded_from_dependency_and_production_files")
        is True,
        "post-edit upstream status inheritance can be asserted without exact receipts",
    )
    semantic_map_validation = post_edit.get("source_only_semantic_map_validation", {})
    require(
        semantic_map_validation.get("visible_input_count") == 1
        and semantic_map_validation.get("visible_input_hash_is_source_hash") is True
        and semantic_map_validation.get(
            "new_map_covers_every_nonblank_source_line_in_order"
        )
        is True
        and semantic_map_validation.get("record_source_text_and_line_hash_exact")
        is True
        and semantic_map_validation.get(
            "proposition_evidence_is_literal_source_line_span"
        )
        is True
        and semantic_map_validation.get(
            "reused_segmentation_runs_full_draft_and_review_validator"
        )
        is True
        and semantic_map_validation.get("safe_status_requires_zero_ambiguities")
        is True
        and semantic_map_validation.get(
            "ambiguity_requires_named_hash_bound_commissioner_decision"
        )
        is True
        and semantic_map_validation.get(
            "unsupported_we_requires_person_scope_evidence_and_commissioner_approval"
        )
        is True,
        "post-edit semantic map is not content- and coverage-validated",
    )
    feedback = post_edit.get("human_feedback_learning", {})
    require(
        feedback.get("artifact") == "human-feedback-learning.json"
        and feedback.get("every_item_assessed") is True
        and feedback.get("local_preference_distinguished_from_reusable_principle") is True
        and feedback.get("full_document_analogue_scan_required") is True
        and feedback.get("human_feedback_overrides_source") is False
        and feedback.get("zero_item_receipt_required_when_no_feedback") is True,
        "human-feedback learning policy is incomplete",
    )
    style = post_edit.get("oral_dharma_talk_style", {})
    require(
        style.get("genre_triggered") is True
        and style.get("one_breath_sentence_check") is True
        and style.get("sentence_split_requires_commissioner") is True
        and style.get("unsupported_we_forbidden") is True
        and style.get("unnecessary_dharma_insertion_forbidden") is True,
        "oral Dharma-talk style policy is incomplete",
    )
    terminology = post_edit.get("terminology_scope", {})
    require(
        terminology.get("same_author_or_institution_approved_usage_checked") is True
        and terminology.get("tradition_specific_variants_compared_when_material") is True
        and terminology.get("project_decisions_promoted_to_global_termbase_automatically") is False,
        "project terminology scope is incomplete",
    )
    delivery = post_edit.get("clean_alternating_bilingual_docx", {})
    require(
        delivery.get("titles_toc_and_headings_alternate") is True
        and delivery.get("incoming_english_excluded") is True
        and delivery.get("semantic_notes_feedback_decisions_and_process_excluded") is True
        and delivery.get("comments_tracked_changes_and_placeholders_forbidden") is True
        and delivery.get("actual_pair_count_and_order_verified") is True
        and delivery.get("actual_docx_zip_content_types_xml_and_text_verified")
        is True
        and delivery.get("actual_docx_paragraphs_derived_from_source_and_target")
        is True
        and delivery.get("hash_bound_rendered_page_index_required") is True
        and delivery.get("render_receipt_bound_to_final_docx_hash_and_page_index")
        is True
        and delivery.get("chinese_and_sanskrit_pali_font_coverage_required") is True
        and delivery.get("docx_zip_text_and_page_visual_qa_required") is True,
        "clean alternating bilingual DOCX profile is incomplete",
    )

    dependency_reader_policy = dependency.get("models", {}).get(
        "english_only_readers", {}
    )
    require(
        dependency_reader_policy.get("roles")
        == ["general_nonfiction_editor", "english_dharma_editor"],
        "dependency lock reader roles are incomplete",
    )
    require(
        dependency_reader_policy.get("visible_input_count") == 1
        and dependency_reader_policy.get("reader_visible_manuscript_retained")
        is True
        and dependency_reader_policy.get(
            "reader_visible_manuscript_chinese_forbidden"
        )
        is True
        and dependency_reader_policy.get("raw_djot_with_chinese_anchors_forbidden")
        is True
        and dependency_reader_policy.get("source_side_inputs_forbidden") is True
        and dependency_reader_policy.get("prior_feedback_forbidden") is True
        and dependency_reader_policy.get("mutual_isolation_required") is True,
        "dependency lock reader isolation is incomplete",
    )

    dependency_segmentation = dependency.get("models", {})
    codex_segmentation = dependency_segmentation.get(
        "chinese_semantic_segmentation", {}
    )
    pro_segmentation = dependency_segmentation.get(
        "chinese_semantic_segmentation_review", {}
    )
    post_edit_semantic_map = dependency_segmentation.get(
        "post_translation_chinese_semantic_map", {}
    )
    require(
        codex_segmentation.get("model") == "gpt-5.6-sol"
        and codex_segmentation.get("reasoning_effort") == "high"
        and codex_segmentation.get("scope") == "every nonblank source line"
        and codex_segmentation.get("writes_english") is False,
        "dependency lock semantic-segmentation role is incomplete",
    )
    require(
        pro_segmentation.get("model") == "deepseek-v4-pro"
        and pro_segmentation.get("reasoning_effort") == "max"
        and pro_segmentation.get("reads_english") is False,
        "dependency lock segmentation-review role is incomplete",
    )
    require(
        post_edit_semantic_map.get("model") == "gpt-5.6-sol"
        and post_edit_semantic_map.get("reasoning_effort") == "high"
        and post_edit_semantic_map.get("writes_english") is False
        and "without consulting existing English"
        in str(post_edit_semantic_map.get("scope")),
        "dependency lock post-edit semantic-map role is incomplete",
    )
    require(
        "post_translation_editing_policy_validation"
        in dependency.get("required_gates", []),
        "dependency lock omits post-translation editing policy validation",
    )

    return {
        "status": "PASS",
        "strategy_id": dependency["strategy_id"],
        "workflow_version": dependency["workflow_version"],
        "production_default_selected": True,
        "release_ready": False,
        "codex_roles": list(codex_roles),
        "independent_pro_roles": list(pro_roles),
        "english_only_reader_roles": [
            "general_nonfiction_editor",
            "english_dharma_editor",
        ],
    }


def validate_package(skill_dir: Path = SKILL_DIR) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "status": "PASS",
        "manifest": verify_manifest(skill_dir),
        "policy": validate_policy(skill_dir),
    }


def main() -> int:
    try:
        report = validate_package()
    except ValidationError as exc:
        print(json.dumps({"status": "FAIL", "error": str(exc)}, indent=2))
        return 1
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
