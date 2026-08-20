from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).parents[1]


def test_public_release_uses_exact_verified_compatibility_forks():
    lock = json.loads((ROOT / "dependency-lock.json").read_text(encoding="utf-8"))
    installed_skill_lock = json.loads(
        (ROOT / "skills" / "mpi-strategy-m" / "dependency-lock.json").read_text(encoding="utf-8")
    )

    assert installed_skill_lock == lock
    assert lock["release_ready"] is True
    assert lock["release_status"] == "verified_compatibility_forks"
    expected = {
        "mpi_translations": (
            "https://github.com/zhi12458/mpi-translations.git",
            "https://git.sr.ht/~iacore/mpi-translations/",
        ),
        "translation_toolkit": (
            "https://github.com/zhi12458/translation-toolkit.git",
            "https://codeberg.org/eastwind/translation-toolkit.git",
        ),
    }
    for name, (fork_origin, upstream_origin) in expected.items():
        spec = lock[name]
        assert spec["origin"] == fork_origin
        assert spec["compatibility_fork"] is True
        assert spec["upstream_origin"] == upstream_origin
        assert len(spec["expected_sha"]) == 40
        assert len(spec["upstream_base_sha"]) == 40

    assert lock["compatibility_policy"]["automatic_main_updates"] is False
    assert lock["compatibility_policy"]["exact_sha_required"] is True
    assert lock["strategy_id"] == "M"
    assert lock["workflow_version"] == "1.0.12"
    assert lock["skill_version"] == "1.0.12"
    assert lock["terminology_policy_version"] == "1.1.0"
    assert lock["models"]["translation"]["reasoning_effort"] == "medium"
    assert lock["models"]["translation_fallback"]["reasoning_effort"] == "high"
    assert lock["model_policy"]["translation_default"] == "fixed"
    assert lock["model_policy"]["independent_concision_pass_required"] is True
    assert lock["model_policy"]["source_analysis_schema_version"] == 3
    assert lock["model_policy"]["source_analysis_context_mode"] == "serial-local-window-with-full-coverage"
    assert lock["model_policy"]["source_analysis_context_window_paragraphs"] == 3
    assert lock["model_policy"]["source_analysis_max_completion_tokens"] == 8192
    assert lock["model_policy"]["source_analysis_retry_limit"] == 5
    assert lock["model_policy"]["source_analysis_default_batch_size"] == 2
    assert lock["model_policy"]["source_analysis_component_mode"] == "seven-pass-merge"
    assert lock["model_policy"]["source_analysis_component_fallback_mode"] == (
        "single-paragraph-after-batch-retries"
    )
    assert lock["model_policy"]["source_analysis_completion_recovery_mode"] == (
        "omit-max-completion-tokens-after-empty-or-length"
    )
    assert lock["model_policy"]["source_analysis_transient_batch_recovery_mode"] == (
        "retry-same-batch-after-exhausted-transient-component"
    )
    assert lock["model_policy"]["source_analysis_transient_batch_retry_limit"] == 2
    assert lock["model_policy"]["source_analysis_cross_component_reconciliation_mode"] == (
        "union-validated-temporal-markers-into-must-preserve"
    )
    assert lock["model_policy"]["source_analysis_component_evidence_prevalidation_mode"] == (
        "verbatim-source-evidence-before-component-acceptance"
    )
    assert lock["model_policy"]["source_analysis_component_semantic_prevalidation_mode"] == (
        "intra-component-v3-rules-before-component-acceptance"
    )
    assert lock["model_policy"]["tool_stderr_diagnostic_mode"] == (
        "strict-provider-body-free-json"
    )
    assert lock["model_policy"]["tool_deterministic_validation_diagnostic_mode"] == (
        "structural-code-paragraph-field-category"
    )
    assert lock["model_policy"]["source_analysis_components"] == [
        "core", "temporal", "operator_negation_modality",
        "operator_quantity_degree", "operator_tense_aspect_other",
        "reference", "constraints"
    ]
    assert lock["model_policy"]["source_analysis_component_context_windows"]["reference"] == 3
    assert lock["model_policy"]["semantic_review_schema_version"] == 3
    assert lock["model_policy"]["cultural_allusions_required"] is True
    assert lock["model_policy"]["temporal_relations_required"] is True
    assert lock["model_policy"]["elliptical_subject_required"] is True
    assert lock["model_policy"]["per_paragraph_review_audits_required"] is True
    assert lock["model_policy"]["universal_model_superiority_claimed"] is False
    assert lock["fixed_terms"]["济群法师"] == "Master Jiqun"
    assert lock["fixed_terms"]["大道大商"] == "Great Path, Great Business"
    assert lock["validation_baseline"]["final_target_sha256"] == "5ca852fbbaba9ac799e01d965e38f1ed65a3dc1e0e15ccebb9629e85ac63c889"
    assert lock["validation_baseline"]["targeted_final_gate"]["status"] == "clear"


def test_skill_routing_is_explicitly_m_named_not_generic_translation():
    skill = (ROOT / "skills" / "mpi-strategy-m" / "SKILL.md").read_text(encoding="utf-8")
    for phrase in ("M方案", "M策略", "按M翻译", "用M方案翻译", "安装M策略", "$mpi-strategy-m"):
        assert phrase in skill
    assert "Use only when the user explicitly says" in skill
    assert "do not claim ordinary translation requests" in skill

    metadata = (ROOT / "skills" / "mpi-strategy-m" / "agents" / "openai.yaml").read_text(encoding="utf-8")
    assert 'default_prompt: "Use $mpi-strategy-m' in metadata
    assert "allow_implicit_invocation: true" in metadata
