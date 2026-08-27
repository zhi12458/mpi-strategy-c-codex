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
        "references/installation.md",
        "references/readiness.md",
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

    roles = production.get("model_roles", {})
    codex_roles = (
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

    gates = set(production.get("required_document_gates", []))
    require("fresh_bilingual_review_round_1" in gates, "round one gate missing")
    require("fresh_bilingual_review_round_2" in gates, "round two gate missing")
    require(
        "fresh_post_concision_bidirectional_semantic_regression" in gates,
        "semantic regression gate missing",
    )
    require("named_human_release_gate" in gates, "human release gate missing")

    return {
        "status": "PASS",
        "strategy_id": dependency["strategy_id"],
        "workflow_version": dependency["workflow_version"],
        "production_default_selected": True,
        "release_ready": False,
        "codex_roles": list(codex_roles),
        "independent_pro_roles": list(pro_roles),
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
