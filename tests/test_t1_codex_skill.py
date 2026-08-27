from __future__ import annotations

import importlib.util
import json
import shutil
from pathlib import Path

import pytest


ROOT = Path(__file__).parents[1]
SKILL = ROOT / "skills" / "mpi-strategy-t1-codex"
SCRIPT = SKILL / "scripts" / "validate_package.py"


def load_validator():
    spec = importlib.util.spec_from_file_location("t1_codex_validate_package", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


validator = load_validator()


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
    assert dependency["workflow_version"] == "1.1.0"
    assert dependency["base_runtime"]["stable_commit"] == (
        "af795df625eca95ab138094bd25172266007f24f"
    )
    assert production["default_routing"]["selected_workflow"] == "t1_codex_quality"
    assert production["model_roles"]["translation_and_self_review"] == {
        "model": "gpt-5.6-sol",
        "reasoning_effort": "high",
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


def test_t1_codex_keeps_full_pretranslation_experimental_and_omp_as_rollback():
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


def test_manifest_detects_a_modified_skill_file(tmp_path):
    copy = tmp_path / "mpi-strategy-t1-codex"
    shutil.copytree(SKILL, copy)
    (copy / "SKILL.md").write_text("modified\n", encoding="utf-8")
    with pytest.raises(validator.ValidationError, match="manifest hash mismatch"):
        validator.verify_manifest(copy)
