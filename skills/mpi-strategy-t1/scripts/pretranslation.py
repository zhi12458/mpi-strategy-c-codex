#!/usr/bin/env python3
"""Deterministic contracts for the T1.2 human and AI pretranslation tracks."""

from __future__ import annotations

import json
import tempfile
import uuid
from pathlib import Path
from typing import Any

from t1_runtime import (
    StrategyT1Error,
    atomic_json,
    sha256_bytes,
    sha256_file,
    utc_now,
)


SCHEMA_VERSION = 1
WORKFLOW_VERSION = "1.2.0"
MODES = {"human_quality", "ai_scale"}
STATUSES = {"safe", "review_required", "blocked"}
CONFIDENCES = {"high", "medium", "low"}
REVIEW_DECISIONS = {"accept", "revert_to_source", "block"}
SEVERITIES = {"none", "minor", "major", "critical"}

PROJECT_INPUTS = (
    "source.dj",
    "translation-project.yaml",
    "source-analysis.json",
    "term-map.yaml",
)
TOP_FIELDS = {
    "schema_version",
    "workflow_version",
    "stage",
    "mode",
    "source_sha256",
    "translation_project_sha256",
    "source_analysis_sha256",
    "term_map_sha256",
    "generated_by",
    "records",
}
RECORD_FIELDS = {
    "paragraph_id",
    "line_sha256",
    "source",
    "semantic_ledger",
    "rewrite",
    "changes",
    "protected_constraints",
    "risk_items",
    "status",
    "confidence",
}
PROPOSAL_RECORD_FIELDS = RECORD_FIELDS - {"line_sha256", "source"}
COMPACT_PROPOSAL_FIELDS = {"records"}
COMPACT_RECORD_FIELDS = {
    "paragraph_id",
    "action",
    "rewrite_transport",
    "transformation_types",
    "risk_summary",
    "confidence",
}
COMPACT_ACTIONS = {"rewrite", "block"}
TRANSFORMATION_TYPES = {
    "split_sentence",
    "explicit_subject",
    "explicit_reference",
    "logic_exposure",
    "modifier_scope",
    "information_reorder",
    "parallel_structure",
    "teacher_voice",
    "redundancy_reduction",
    "punctuation_only",
}
TRANSFORMATION_LABELS = {
    "split_sentence": "按原有语义边界拆句",
    "explicit_subject": "显化原文可唯一恢复的主语",
    "explicit_reference": "显化原文可唯一恢复的指代",
    "logic_exposure": "显化原文已有的逻辑关系",
    "modifier_scope": "明确修饰语或管辖范围",
    "information_reorder": "按等义信息结构重排",
    "parallel_structure": "显化并列或递进结构",
    "teacher_voice": "调整句法以保留教师口吻",
    "redundancy_reduction": "删除不承载独立语义的重复表达",
    "punctuation_only": "仅调整标点以显化句法边界",
}
QUOTE_TRANSPORT = {
    "⟦Q0⟧": '"',
    "⟦Q1⟧": "“",
    "⟦Q2⟧": "”",
}
PROVENANCE_FIELDS = {
    "kind",
    "name",
    "provider",
    "model",
    "reasoning_effort",
    "role",
}
APPROVAL_FIELDS = {
    "schema_version",
    "workflow_version",
    "stage",
    "source_sha256",
    "pretranslation_sha256",
    "decision",
    "consensus",
    "reviewers",
}
REVIEW_FIELDS = {
    "schema_version",
    "workflow_version",
    "stage",
    "source_sha256",
    "pretranslation_sha256",
    "reviewed_by",
    "decisions",
}
DECISION_FIELDS = {
    "paragraph_id",
    "decision",
    "severity",
    "issue",
    "required_revision",
}
ACCEPTED_FIELDS = {
    "schema_version",
    "workflow_version",
    "stage",
    "mode",
    "source_sha256",
    "pretranslation_sha256",
    "decision_evidence_sha256",
    "records",
}
ACCEPTED_RECORD_FIELDS = {
    "paragraph_id",
    "line_sha256",
    "source",
    "effective_text",
    "original_status",
    "resolution",
}


def _load_object(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise StrategyT1Error(f"invalid JSON file: {path}") from exc
    if not isinstance(value, dict):
        raise StrategyT1Error(f"JSON root must be an object: {path}")
    return value


def _exact_fields(value: dict[str, Any], expected: set[str], where: str) -> None:
    actual = set(value)
    if actual != expected:
        missing = sorted(expected - actual)
        extra = sorted(actual - expected)
        raise StrategyT1Error(
            f"{where} fields differ: missing={missing}, extra={extra}"
        )


def _string(value: Any, where: str, *, allow_empty: bool = False) -> str:
    if not isinstance(value, str) or (not allow_empty and not value.strip()):
        raise StrategyT1Error(f"{where} must be a nonempty string")
    return value


def _string_list(value: Any, where: str, *, allow_empty: bool = True) -> list[str]:
    if not isinstance(value, list):
        raise StrategyT1Error(f"{where} must be a list")
    if not allow_empty and not value:
        raise StrategyT1Error(f"{where} must not be empty")
    for index, item in enumerate(value):
        _string(item, f"{where}[{index}]")
    return value


def _project(project: Path) -> tuple[Path, dict[str, Path]]:
    project = project.expanduser().resolve()
    if not project.is_dir():
        raise StrategyT1Error(f"T1 project directory is missing: {project}")
    inputs: dict[str, Path] = {}
    for name in PROJECT_INPUTS:
        path = (project / name).resolve()
        if not path.is_file():
            raise StrategyT1Error(f"required T1.2 input is missing: {path}")
        inputs[name] = path
    return project, inputs


def source_records(source: Path) -> list[dict[str, Any]]:
    try:
        lines = source.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeDecodeError) as exc:
        raise StrategyT1Error(f"source.dj is not valid UTF-8: {source}") from exc
    records = []
    for line_number, text in enumerate(lines, start=1):
        if not text.strip():
            continue
        records.append(
            {
                "paragraph_id": f"L{line_number}",
                "line_number": line_number,
                "source": text,
                "line_sha256": sha256_bytes(text.encode("utf-8")),
            }
        )
    if not records:
        raise StrategyT1Error("source.dj has no nonblank records")
    return records


def _input_hashes(inputs: dict[str, Path]) -> dict[str, str]:
    return {name: sha256_file(path) for name, path in inputs.items()}


def proposal_contract(project: Path, mode: str = "ai_scale") -> dict[str, Any]:
    _, inputs = _project(project)
    if mode not in MODES:
        raise StrategyT1Error(f"unknown T1.2 pretranslation mode: {mode}")
    inventory = source_records(inputs["source.dj"])
    return {
        "contract": "T1.2 controlled-Chinese pretranslation proposal",
        "workflow_version": WORKFLOW_VERSION,
        "mode": mode,
        "source_nonblank_units": len(inventory),
        "paragraph_ids_in_order": [item["paragraph_id"] for item in inventory],
        "proposal_top_fields": ["records"],
        "record_fields": sorted(PROPOSAL_RECORD_FIELDS),
        "status_values": sorted(STATUSES),
        "confidence_values": sorted(CONFIDENCES),
        "requirements": [
            "return every nonblank source line exactly once and in source order",
            "leave already-clear Chinese unchanged",
            "do not translate into English",
            "do not add propositions, agents, logic, modality, doctrine, or evaluation",
            "preserve quotations, terms, numbers, negation, degree, scope, and voice",
            "mark unresolved ambiguity blocked rather than guessing",
        ],
    }


def hydrate_proposal(
    project: Path,
    proposal: dict[str, Any],
    *,
    mode: str,
    provenance: dict[str, Any],
) -> dict[str, Any]:
    _, inputs = _project(project)
    if mode not in MODES:
        raise StrategyT1Error(f"unknown T1.2 pretranslation mode: {mode}")
    _exact_fields(proposal, {"records"}, "pretranslation proposal")
    _exact_fields(provenance, PROVENANCE_FIELDS, "pretranslation provenance")
    records = proposal.get("records")
    if not isinstance(records, list):
        raise StrategyT1Error("pretranslation proposal records must be a list")
    inventory = source_records(inputs["source.dj"])
    if len(records) != len(inventory):
        raise StrategyT1Error("pretranslation proposal does not cover every nonblank source line")
    hydrated: list[dict[str, Any]] = []
    for index, (record, source) in enumerate(zip(records, inventory, strict=True)):
        if not isinstance(record, dict):
            raise StrategyT1Error(f"pretranslation proposal records[{index}] must be an object")
        _exact_fields(record, PROPOSAL_RECORD_FIELDS, f"pretranslation proposal records[{index}]")
        if record.get("paragraph_id") != source["paragraph_id"]:
            raise StrategyT1Error("pretranslation proposal paragraph order or coverage differs from source")
        hydrated.append(
            {
                "paragraph_id": source["paragraph_id"],
                "line_sha256": source["line_sha256"],
                "source": source["source"],
                **{key: record[key] for key in PROPOSAL_RECORD_FIELDS if key != "paragraph_id"},
            }
        )
    hashes = _input_hashes(inputs)
    return {
        "schema_version": SCHEMA_VERSION,
        "workflow_version": WORKFLOW_VERSION,
        "stage": "pretranslation",
        "mode": mode,
        "source_sha256": hashes["source.dj"],
        "translation_project_sha256": hashes["translation-project.yaml"],
        "source_analysis_sha256": hashes["source-analysis.json"],
        "term_map_sha256": hashes["term-map.yaml"],
        "generated_by": provenance,
        "records": hydrated,
    }


def _analysis_inventory(path: Path) -> dict[str, dict[str, Any]]:
    """Load the frozen analysis used to hydrate compact model responses."""
    value = _load_object(path)
    paragraphs = value.get("paragraphs")
    if not isinstance(paragraphs, list):
        return {}
    inventory: dict[str, dict[str, Any]] = {}
    for item in paragraphs:
        if not isinstance(item, dict):
            continue
        paragraph_id = item.get("paragraph_id")
        if isinstance(paragraph_id, str) and paragraph_id not in inventory:
            inventory[paragraph_id] = item
    return inventory


def _ledger_from_analysis(paragraph_id: str, analysis: dict[str, Any] | None) -> list[str]:
    if not analysis:
        return [f"复用已哈希绑定的 source-analysis.json:{paragraph_id}"]
    ledger: list[str] = []
    for label, field in (
        ("语义核心", "semantic_head"),
        ("主体与状态承载者", "actors_and_state_holders"),
        ("角色与指代", "semantic_roles_and_references"),
        ("逻辑与范围", "logic_and_scope"),
        ("省略或歧义", "ellipsis_or_ambiguity"),
    ):
        value = analysis.get(field)
        if isinstance(value, str) and value.strip():
            ledger.append(f"{label}：{value.strip()}")
    return ledger or [f"复用已哈希绑定的 source-analysis.json:{paragraph_id}"]


def _constraints_from_analysis(
    paragraph_id: str, analysis: dict[str, Any] | None
) -> list[str]:
    if not analysis:
        return [f"不得超出 source-analysis.json:{paragraph_id} 的已冻结语义"]
    constraints: list[str] = []
    for value in analysis.get("must_preserve", []):
        if isinstance(value, str) and value.strip():
            constraints.append(value.strip())
    for value in analysis.get("must_not_invent", []):
        if isinstance(value, str) and value.strip():
            constraints.append(f"禁止新增：{value.strip()}")
    return constraints or [f"不得超出 source-analysis.json:{paragraph_id} 的已冻结语义"]


def _decode_rewrite_transport(value: str, source: str, where: str) -> str:
    if '"' in value or "“" in value or "”" in value:
        raise StrategyT1Error(
            f"{where} must transport every quotation mark through Q0/Q1/Q2 tokens"
        )
    decoded = value
    for token, quote in QUOTE_TRANSPORT.items():
        decoded = decoded.replace(token, quote)
    if "⟦Q" in decoded:
        raise StrategyT1Error(f"{where} contains an unknown quotation transport token")
    quote_chars = {'"', "“", "”"}
    source_quotes = [char for char in source if char in quote_chars]
    decoded_quotes = [char for char in decoded if char in quote_chars]
    if decoded_quotes != source_quotes:
        raise StrategyT1Error(f"{where} changes protected quotation-mark identity or order")
    return decoded


def hydrate_compact_ai_proposal(
    project: Path,
    proposal: dict[str, Any],
    *,
    provenance: dict[str, Any],
) -> dict[str, Any]:
    """Hydrate a sparse model response into the full T1.2 artifact.

    Unlisted source lines are copied deterministically. Every model rewrite is
    routed to independent review, allowing bolder structure without permitting
    the drafting role to approve its own semantic choices.
    """
    _, inputs = _project(project)
    _exact_fields(proposal, COMPACT_PROPOSAL_FIELDS, "compact pretranslation proposal")
    _exact_fields(provenance, PROVENANCE_FIELDS, "pretranslation provenance")
    compact_records = proposal.get("records")
    if not isinstance(compact_records, list):
        raise StrategyT1Error("compact pretranslation records must be a list")

    inventory = source_records(inputs["source.dj"])
    source_by_id = {item["paragraph_id"]: item for item in inventory}
    order = {item["paragraph_id"]: index for index, item in enumerate(inventory)}
    selected: dict[str, dict[str, Any]] = {}
    previous = -1
    for index, record in enumerate(compact_records):
        where = f"compact pretranslation records[{index}]"
        if not isinstance(record, dict):
            raise StrategyT1Error(f"{where} must be an object")
        _exact_fields(record, COMPACT_RECORD_FIELDS, where)
        paragraph_id = _string(record.get("paragraph_id"), f"{where}.paragraph_id")
        if paragraph_id not in source_by_id or paragraph_id in selected:
            raise StrategyT1Error(f"{where} has an unknown or duplicate paragraph_id")
        if order[paragraph_id] <= previous:
            raise StrategyT1Error("compact pretranslation records are not in source order")
        previous = order[paragraph_id]
        source = source_by_id[paragraph_id]["source"]
        if source.startswith(("{#", "##", "###")):
            raise StrategyT1Error(f"{where} must not rewrite or block structural lines")
        action = record.get("action")
        confidence = record.get("confidence")
        if action not in COMPACT_ACTIONS or confidence not in CONFIDENCES:
            raise StrategyT1Error(f"{where} has an invalid action or confidence")
        types = record.get("transformation_types")
        if not isinstance(types, list) or any(item not in TRANSFORMATION_TYPES for item in types):
            raise StrategyT1Error(f"{where}.transformation_types is invalid")
        if len(types) != len(set(types)):
            raise StrategyT1Error(f"{where}.transformation_types contains duplicates")
        risk_summary = _string(record.get("risk_summary"), f"{where}.risk_summary")
        transport = record.get("rewrite_transport")
        if action == "block":
            if transport is not None or types:
                raise StrategyT1Error(f"{where} blocked records cannot contain a rewrite")
            rewrite = source
            status = "blocked"
            changes: list[str] = []
        else:
            if not isinstance(transport, str) or not transport.strip() or not types:
                raise StrategyT1Error(f"{where} rewrite records require text and transformations")
            rewrite = _decode_rewrite_transport(transport, source, f"{where}.rewrite_transport")
            if rewrite == source:
                raise StrategyT1Error(f"{where} declares a rewrite but preserves the source")
            status = "review_required"
            changes = [TRANSFORMATION_LABELS[item] for item in types]
        selected[paragraph_id] = {
            "rewrite": rewrite,
            "changes": changes,
            "risk_items": [risk_summary],
            "status": status,
            "confidence": confidence,
        }

    analysis = _analysis_inventory(inputs["source-analysis.json"])
    full_records: list[dict[str, Any]] = []
    for source in inventory:
        paragraph_id = source["paragraph_id"]
        choice = selected.get(paragraph_id)
        full_records.append(
            {
                "paragraph_id": paragraph_id,
                "semantic_ledger": _ledger_from_analysis(paragraph_id, analysis.get(paragraph_id)),
                "rewrite": choice["rewrite"] if choice else source["source"],
                "changes": choice["changes"] if choice else [],
                "protected_constraints": _constraints_from_analysis(
                    paragraph_id, analysis.get(paragraph_id)
                ),
                "risk_items": choice["risk_items"] if choice else [],
                "status": choice["status"] if choice else "safe",
                "confidence": choice["confidence"] if choice else "high",
            }
        )
    return hydrate_proposal(
        project, {"records": full_records}, mode="ai_scale", provenance=provenance
    )


def validate_pretranslation(
    project: Path,
    *,
    artifact_path: Path | None = None,
    expected_mode: str | None = None,
) -> dict[str, Any]:
    _, inputs = _project(project)
    artifact_path = (artifact_path or (project / "pretranslation.json")).expanduser().resolve()
    artifact = _load_object(artifact_path)
    _exact_fields(artifact, TOP_FIELDS, "pretranslation artifact")
    if artifact.get("schema_version") != SCHEMA_VERSION:
        raise StrategyT1Error("unsupported pretranslation schema version")
    if artifact.get("workflow_version") != WORKFLOW_VERSION:
        raise StrategyT1Error("pretranslation workflow version does not match T1.2")
    if artifact.get("stage") != "pretranslation":
        raise StrategyT1Error("pretranslation artifact stage is invalid")
    mode = artifact.get("mode")
    if mode not in MODES or (expected_mode is not None and mode != expected_mode):
        raise StrategyT1Error("pretranslation mode is invalid or unexpected")
    hashes = _input_hashes(inputs)
    expected_hashes = {
        "source_sha256": hashes["source.dj"],
        "translation_project_sha256": hashes["translation-project.yaml"],
        "source_analysis_sha256": hashes["source-analysis.json"],
        "term_map_sha256": hashes["term-map.yaml"],
    }
    for field, expected in expected_hashes.items():
        if artifact.get(field) != expected:
            raise StrategyT1Error(f"pretranslation {field} does not match the frozen project")

    provenance = artifact.get("generated_by")
    if not isinstance(provenance, dict):
        raise StrategyT1Error("pretranslation generated_by must be an object")
    _exact_fields(provenance, PROVENANCE_FIELDS, "pretranslation generated_by")
    if mode == "human_quality":
        if provenance.get("kind") != "human" or not str(provenance.get("name") or "").strip():
            raise StrategyT1Error("human-quality pretranslation requires a named human generator")
        for field in ("provider", "model", "reasoning_effort", "role"):
            if provenance.get(field) is not None:
                raise StrategyT1Error("human-quality provenance must not claim a model identity")
    else:
        expected = {
            "kind": "model",
            "name": None,
            "provider": "deepseek",
            "model": "deepseek-v4-flash",
            "reasoning_effort": "high",
            "role": "source_analysis",
        }
        if provenance != expected:
            raise StrategyT1Error("AI-scale pretranslation must use the locked Flash/high source-side role")

    inventory = source_records(inputs["source.dj"])
    records = artifact.get("records")
    if not isinstance(records, list) or len(records) != len(inventory):
        raise StrategyT1Error("pretranslation artifact must cover every nonblank source line")
    counts = {status: 0 for status in sorted(STATUSES)}
    changed = 0
    for index, (record, source) in enumerate(zip(records, inventory, strict=True)):
        where = f"pretranslation records[{index}]"
        if not isinstance(record, dict):
            raise StrategyT1Error(f"{where} must be an object")
        _exact_fields(record, RECORD_FIELDS, where)
        if (
            record.get("paragraph_id") != source["paragraph_id"]
            or record.get("line_sha256") != source["line_sha256"]
            or record.get("source") != source["source"]
        ):
            raise StrategyT1Error(f"{where} is not exactly bound to source.dj")
        for field in ("semantic_ledger", "changes", "protected_constraints", "risk_items"):
            _string_list(record.get(field), f"{where}.{field}")
        rewrite = _string(record.get("rewrite"), f"{where}.rewrite")
        status = record.get("status")
        confidence = record.get("confidence")
        if status not in STATUSES or confidence not in CONFIDENCES:
            raise StrategyT1Error(f"{where} has an invalid status or confidence")
        counts[status] += 1
        is_changed = rewrite != source["source"]
        if is_changed:
            changed += 1
            if not record["changes"]:
                raise StrategyT1Error(f"{where} changed text without a change record")
        elif record["changes"]:
            raise StrategyT1Error(f"{where} declares changes but preserves the source exactly")
        if mode == "ai_scale" and status == "blocked" and is_changed:
            raise StrategyT1Error(f"{where} is blocked but guesses a rewritten reading")
    return {
        "status": "PASS",
        "workflow_version": WORKFLOW_VERSION,
        "mode": mode,
        "artifact_sha256": sha256_file(artifact_path),
        "source_nonblank_units": len(inventory),
        "changed_units": changed,
        "unchanged_units": len(inventory) - changed,
        "status_counts": counts,
        "semantic_safety_proven": False,
    }


def validate_human_approval(
    project: Path,
    pretranslation_path: Path,
    approval_path: Path,
) -> dict[str, Any]:
    report = validate_pretranslation(
        project, artifact_path=pretranslation_path, expected_mode="human_quality"
    )
    approval_path = approval_path.expanduser().resolve()
    approval = _load_object(approval_path)
    _exact_fields(approval, APPROVAL_FIELDS, "human pretranslation approval")
    if (
        approval.get("schema_version") != SCHEMA_VERSION
        or approval.get("workflow_version") != WORKFLOW_VERSION
        or approval.get("stage") != "human_pretranslation_approval"
        or approval.get("decision") != "approved"
    ):
        raise StrategyT1Error("human pretranslation approval identity is invalid")
    if approval.get("source_sha256") != sha256_file((project / "source.dj").resolve()):
        raise StrategyT1Error("human pretranslation approval source hash is invalid")
    if approval.get("pretranslation_sha256") != report["artifact_sha256"]:
        raise StrategyT1Error("human pretranslation approval does not bind the candidate artifact")
    if approval.get("consensus") not in {"single_reviewer", "unanimous", "adjudicated"}:
        raise StrategyT1Error("human pretranslation approval consensus is invalid")
    reviewers = approval.get("reviewers")
    if not isinstance(reviewers, list) or not reviewers:
        raise StrategyT1Error("human pretranslation approval requires a named reviewer")
    for index, reviewer in enumerate(reviewers):
        if not isinstance(reviewer, dict) or set(reviewer) != {"name", "role"}:
            raise StrategyT1Error(f"human pretranslation reviewer[{index}] is invalid")
        _string(reviewer.get("name"), f"human pretranslation reviewer[{index}].name")
        _string(reviewer.get("role"), f"human pretranslation reviewer[{index}].role")
    return {
        "status": "PASS",
        "pretranslation": report,
        "approval_sha256": sha256_file(approval_path),
        "reviewer_count": len(reviewers),
        "consensus": approval["consensus"],
    }


def hydrate_ai_review(
    project: Path,
    pretranslation_path: Path,
    proposal: dict[str, Any],
    *,
    provenance: dict[str, Any],
) -> dict[str, Any]:
    report = validate_pretranslation(
        project, artifact_path=pretranslation_path, expected_mode="ai_scale"
    )
    _exact_fields(proposal, {"decisions"}, "AI pretranslation review proposal")
    return {
        "schema_version": SCHEMA_VERSION,
        "workflow_version": WORKFLOW_VERSION,
        "stage": "ai_pretranslation_review",
        "source_sha256": sha256_file((project / "source.dj").resolve()),
        "pretranslation_sha256": report["artifact_sha256"],
        "reviewed_by": provenance,
        "decisions": proposal["decisions"],
    }


def validate_ai_review(
    project: Path,
    pretranslation_path: Path,
    review_path: Path,
) -> dict[str, Any]:
    pretranslation_report = validate_pretranslation(
        project, artifact_path=pretranslation_path, expected_mode="ai_scale"
    )
    artifact = _load_object(pretranslation_path)
    review_path = review_path.expanduser().resolve()
    review = _load_object(review_path)
    _exact_fields(review, REVIEW_FIELDS, "AI pretranslation review")
    if (
        review.get("schema_version") != SCHEMA_VERSION
        or review.get("workflow_version") != WORKFLOW_VERSION
        or review.get("stage") != "ai_pretranslation_review"
    ):
        raise StrategyT1Error("AI pretranslation review identity is invalid")
    if review.get("source_sha256") != sha256_file((project / "source.dj").resolve()):
        raise StrategyT1Error("AI pretranslation review source hash is stale")
    if review.get("pretranslation_sha256") != pretranslation_report["artifact_sha256"]:
        raise StrategyT1Error("AI pretranslation review does not bind the candidate artifact")
    reviewer = review.get("reviewed_by")
    expected_reviewer = {
        "provider": "deepseek",
        "model": "deepseek-v4-pro",
        "reasoning_effort": "max",
        "role": "bilingual_review",
    }
    required_ids = {
        item["paragraph_id"]
        for item in artifact["records"]
        if item["status"] == "review_required"
    }
    no_review_required = {
        "provider": None,
        "model": None,
        "reasoning_effort": None,
        "role": "not_required",
    }
    if reviewer != expected_reviewer and not (
        not required_ids and reviewer == no_review_required
    ):
        raise StrategyT1Error("AI pretranslation review must use the locked independent Pro/max role")
    decisions = review.get("decisions")
    if not isinstance(decisions, list):
        raise StrategyT1Error("AI pretranslation review decisions must be a list")
    seen: set[str] = set()
    for index, decision in enumerate(decisions):
        where = f"AI pretranslation review decisions[{index}]"
        if not isinstance(decision, dict):
            raise StrategyT1Error(f"{where} must be an object")
        _exact_fields(decision, DECISION_FIELDS, where)
        paragraph_id = decision.get("paragraph_id")
        if paragraph_id not in required_ids or paragraph_id in seen:
            raise StrategyT1Error(f"{where} is duplicate or outside review_required scope")
        seen.add(paragraph_id)
        if decision.get("decision") not in REVIEW_DECISIONS:
            raise StrategyT1Error(f"{where}.decision is invalid")
        if decision.get("severity") not in SEVERITIES:
            raise StrategyT1Error(f"{where}.severity is invalid")
        _string(decision.get("issue"), f"{where}.issue", allow_empty=True)
        _string(decision.get("required_revision"), f"{where}.required_revision", allow_empty=True)
        if decision["decision"] == "accept" and decision["severity"] in {"major", "critical"}:
            raise StrategyT1Error(f"{where} accepts a major or critical defect")
    if seen != required_ids:
        raise StrategyT1Error("AI pretranslation review does not cover every review_required record")
    return {
        "status": "PASS",
        "pretranslation": pretranslation_report,
        "review_sha256": sha256_file(review_path),
        "reviewed_units": len(required_ids),
    }


def resolve_pretranslation(
    project: Path,
    pretranslation_path: Path,
    decision_evidence_path: Path,
    *,
    output: Path,
) -> dict[str, Any]:
    pretranslation_path = pretranslation_path.expanduser().resolve()
    artifact = _load_object(pretranslation_path)
    mode = artifact.get("mode")
    if mode == "human_quality":
        evidence = validate_human_approval(project, pretranslation_path, decision_evidence_path)
        decisions: dict[str, str] = {}
    elif mode == "ai_scale":
        evidence = validate_ai_review(project, pretranslation_path, decision_evidence_path)
        review = _load_object(decision_evidence_path.expanduser().resolve())
        decisions = {item["paragraph_id"]: item["decision"] for item in review["decisions"]}
    else:
        raise StrategyT1Error("pretranslation mode is invalid")
    records = []
    for item in artifact["records"]:
        status = item["status"]
        if mode == "human_quality":
            effective = item["rewrite"]
            resolution = "human_approved_rewrite"
        elif status == "safe":
            effective = item["rewrite"]
            resolution = "ai_safe_rewrite"
        elif status == "review_required" and decisions[item["paragraph_id"]] == "accept":
            effective = item["rewrite"]
            resolution = "pro_reviewed_rewrite"
        else:
            effective = item["source"]
            resolution = "reverted_to_source"
        records.append(
            {
                "paragraph_id": item["paragraph_id"],
                "line_sha256": item["line_sha256"],
                "source": item["source"],
                "effective_text": effective,
                "original_status": status,
                "resolution": resolution,
            }
        )
    accepted = {
        "schema_version": SCHEMA_VERSION,
        "workflow_version": WORKFLOW_VERSION,
        "stage": "accepted_pretranslation",
        "mode": mode,
        "source_sha256": sha256_file((project / "source.dj").resolve()),
        "pretranslation_sha256": sha256_file(pretranslation_path),
        "decision_evidence_sha256": sha256_file(decision_evidence_path.expanduser().resolve()),
        "records": records,
    }
    output = output.expanduser().resolve()
    if output.exists():
        raise StrategyT1Error(f"refusing to overwrite existing T1 artifact: {output}")
    atomic_json(output, accepted)
    validation = validate_accepted_pretranslation(project, output)
    return {"status": "PASS", "decision_evidence": evidence, "accepted": validation}


def validate_accepted_pretranslation(project: Path, artifact_path: Path) -> dict[str, Any]:
    _, inputs = _project(project)
    artifact_path = artifact_path.expanduser().resolve()
    artifact = _load_object(artifact_path)
    _exact_fields(artifact, ACCEPTED_FIELDS, "accepted pretranslation")
    if (
        artifact.get("schema_version") != SCHEMA_VERSION
        or artifact.get("workflow_version") != WORKFLOW_VERSION
        or artifact.get("stage") != "accepted_pretranslation"
        or artifact.get("mode") not in MODES
    ):
        raise StrategyT1Error("accepted pretranslation identity is invalid")
    if artifact.get("source_sha256") != sha256_file(inputs["source.dj"]):
        raise StrategyT1Error("accepted pretranslation source hash is stale")
    records = artifact.get("records")
    inventory = source_records(inputs["source.dj"])
    if not isinstance(records, list) or len(records) != len(inventory):
        raise StrategyT1Error("accepted pretranslation coverage differs from source")
    resolutions: dict[str, int] = {}
    for index, (record, source) in enumerate(zip(records, inventory, strict=True)):
        where = f"accepted pretranslation records[{index}]"
        if not isinstance(record, dict):
            raise StrategyT1Error(f"{where} must be an object")
        _exact_fields(record, ACCEPTED_RECORD_FIELDS, where)
        if (
            record.get("paragraph_id") != source["paragraph_id"]
            or record.get("line_sha256") != source["line_sha256"]
            or record.get("source") != source["source"]
        ):
            raise StrategyT1Error(f"{where} is not exactly bound to source.dj")
        _string(record.get("effective_text"), f"{where}.effective_text")
        if record.get("original_status") not in STATUSES:
            raise StrategyT1Error(f"{where}.original_status is invalid")
        resolution = _string(record.get("resolution"), f"{where}.resolution")
        resolutions[resolution] = resolutions.get(resolution, 0) + 1
    return {
        "status": "PASS",
        "mode": artifact["mode"],
        "artifact_sha256": sha256_file(artifact_path),
        "source_nonblank_units": len(inventory),
        "resolutions": resolutions,
        "source_authority": "source.dj",
    }


def run_contract_tests(root: Path) -> dict[str, Any]:
    root = root.expanduser().resolve()
    root.mkdir(parents=True, exist_ok=True)
    cases: list[dict[str, str]] = []
    with tempfile.TemporaryDirectory(prefix="t1-pretranslation-", dir=root) as temporary:
        project = Path(temporary)
        (project / "source.dj").write_text("清楚的句子。\n\n需要显化主语。\n", encoding="utf-8")
        (project / "translation-project.yaml").write_text("genre: test\n", encoding="utf-8")
        (project / "source-analysis.json").write_text("{}\n", encoding="utf-8")
        (project / "term-map.yaml").write_text("terms: {}\n", encoding="utf-8")
        proposal = {
            "records": [
                {
                    "paragraph_id": "L1",
                    "semantic_ledger": ["句子已经清楚"],
                    "rewrite": "清楚的句子。",
                    "changes": [],
                    "protected_constraints": ["陈述语气"],
                    "risk_items": [],
                    "status": "safe",
                    "confidence": "high",
                },
                {
                    "paragraph_id": "L3",
                    "semantic_ledger": ["省略主语，需要确认"],
                    "rewrite": "需要显化主语。",
                    "changes": [],
                    "protected_constraints": ["不得猜测主语"],
                    "risk_items": ["主语未确定"],
                    "status": "blocked",
                    "confidence": "low",
                },
            ]
        }
        provenance = {
            "kind": "model",
            "name": None,
            "provider": "deepseek",
            "model": "deepseek-v4-flash",
            "reasoning_effort": "high",
            "role": "source_analysis",
        }
        artifact = hydrate_proposal(project, proposal, mode="ai_scale", provenance=provenance)
        pretranslation = project / "pretranslation.json"
        atomic_json(pretranslation, artifact)
        validation = validate_pretranslation(project, artifact_path=pretranslation)
        cases.append({"case": "ai_full_coverage_and_blocked_fallback", "status": validation["status"]})
        review = hydrate_ai_review(
            project,
            pretranslation,
            {"decisions": []},
            provenance={
                "provider": "deepseek",
                "model": "deepseek-v4-pro",
                "reasoning_effort": "max",
                "role": "bilingual_review",
            },
        )
        review_path = project / "pretranslation-review.json"
        atomic_json(review_path, review)
        validate_ai_review(project, pretranslation, review_path)
        accepted_path = project / "accepted-pretranslation.json"
        resolved = resolve_pretranslation(
            project, pretranslation, review_path, output=accepted_path
        )
        cases.append({"case": "ai_deterministic_resolution", "status": resolved["status"]})
    report = {
        "status": "PASS",
        "workflow_version": WORKFLOW_VERSION,
        "created_at": utc_now(),
        "cases": cases,
    }
    evidence = root / "evidence" / f"pretranslation-contracts-{uuid.uuid4().hex}.json"
    atomic_json(evidence, report)
    report["report_absolute_path"] = str(evidence)
    report["report_sha256"] = sha256_file(evidence)
    return report
