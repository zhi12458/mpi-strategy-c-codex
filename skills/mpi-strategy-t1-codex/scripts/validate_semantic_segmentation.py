#!/usr/bin/env python3
"""Validate T1-Codex Chinese semantic-segmentation artifacts and receipts."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any


WORKFLOW_VERSION = "1.2.0"
SEGMENTATION_JSONL = "chinese-semantic-segmentation.jsonl"
SEGMENTATION_DJ = "chinese-semantic-segmentation.dj"
REVIEW_JSONL = "chinese-semantic-segmentation-review.jsonl"
ALLOWED_STATUSES = {"safe", "review_required", "blocked", "structural"}
REVIEW_DECISIONS = {"approved", "revised_approved", "human_approved"}


class SegmentationValidationError(RuntimeError):
    """A segmentation artifact is incomplete, stale, or violates a guardrail."""


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def sha256_text(value: str) -> str:
    return sha256_bytes(value.encode("utf-8"))


def require(value: bool, message: str) -> None:
    if not value:
        raise SegmentationValidationError(message)


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    require(path.is_file(), f"missing artifact: {path.name}")
    records: list[dict[str, Any]] = []
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            value = json.loads(line)
        except json.JSONDecodeError as exc:
            raise SegmentationValidationError(
                f"invalid JSON at {path.name}:{number}"
            ) from exc
        require(isinstance(value, dict), f"JSONL record {number} is not an object")
        records.append(value)
    return records


def validate_source_evidence(
    evidence: Any,
    *,
    source_text: str,
    label: str,
) -> None:
    require(
        isinstance(evidence, list)
        and evidence
        and all(isinstance(item, str) and item.strip() for item in evidence),
        f"{label} has no exact source evidence",
    )
    require(
        all(item in source_text for item in evidence),
        f"{label} contains source evidence not present in the bound source line",
    )


def validate_meaning_units(
    record: dict[str, Any],
    paragraph_id: str,
    source_text: str,
) -> None:
    units = record.get("meaning_units")
    require(isinstance(units, list) and units, f"{paragraph_id} has no meaning units")
    seen: set[str] = set()
    for unit in units:
        require(isinstance(unit, dict), f"{paragraph_id} meaning unit is not an object")
        unit_id = unit.get("unit_id")
        require(
            isinstance(unit_id, str) and unit_id.startswith(f"{paragraph_id}-U"),
            f"{paragraph_id} has an invalid meaning-unit id",
        )
        require(unit_id not in seen, f"{paragraph_id} repeats meaning-unit id {unit_id}")
        seen.add(unit_id)
        require(
            isinstance(unit.get("text"), str) and unit["text"].strip(),
            f"{unit_id} has no Chinese unit text",
        )
        validate_source_evidence(
            unit.get("source_evidence"),
            source_text=source_text,
            label=unit_id,
        )
        roles = unit.get("semantic_roles")
        require(isinstance(roles, dict), f"{unit_id} has no semantic-role record")
        require(
            isinstance(unit.get("logic_relation"), str),
            f"{unit_id} has no logic relation",
        )


def validate_changes(
    record: dict[str, Any],
    paragraph_id: str,
    source_text: str,
) -> bool:
    changes = record.get("changes")
    require(isinstance(changes, list), f"{paragraph_id} changes must be a list")
    needs_human = False
    for change in changes:
        require(isinstance(change, dict), f"{paragraph_id} change is not an object")
        require(
            isinstance(change.get("type"), str) and change["type"].strip(),
            f"{paragraph_id} change has no type",
        )
        validate_source_evidence(
            change.get("source_evidence"),
            source_text=source_text,
            label=f"{paragraph_id} change",
        )
        if change["type"] != "added_subject":
            continue
        subject = change.get("subject")
        require(
            isinstance(subject, str) and subject.strip(),
            f"{paragraph_id} added subject is empty",
        )
        require(
            change.get("person_scope")
            in {"speaker", "audience", "speaker_and_audience", "people", "third_person", "impersonal"},
            f"{paragraph_id} added subject has invalid person scope",
        )
        confirmation = change.get("human_confirmation_required")
        require(isinstance(confirmation, bool), f"{paragraph_id} lacks subject confirmation flag")
        needs_human = needs_human or confirmation
        if subject == "我们":
            require(
                confirmation is True,
                f"{paragraph_id} adds 我们 without mandatory human confirmation",
            )
            require(
                record.get("status") in {"review_required", "blocked"},
                f"{paragraph_id} adds 我们 but is incorrectly marked safe",
            )
    if needs_human:
        require(
            record.get("status") in {"review_required", "blocked"},
            f"{paragraph_id} needs human confirmation but is incorrectly marked safe",
        )
    return needs_human


def validate_draft(project: Path) -> dict[str, Any]:
    source = project / "source.dj"
    segmented = project / SEGMENTATION_DJ
    require(source.is_file(), "missing source.dj")
    require(segmented.is_file(), f"missing {SEGMENTATION_DJ}")
    source_bytes = source.read_bytes()
    source_hash = sha256_bytes(source_bytes)
    source_lines = source.read_text(encoding="utf-8").splitlines()
    segmented_lines = segmented.read_text(encoding="utf-8").splitlines()
    require(
        len(source_lines) == len(segmented_lines),
        "source and segmentation physical-line counts differ",
    )
    require(
        [not line.strip() for line in source_lines]
        == [not line.strip() for line in segmented_lines],
        "source and segmentation blank-line positions differ",
    )

    records = read_jsonl(project / SEGMENTATION_JSONL)
    expected_lines = [index for index, line in enumerate(source_lines, 1) if line.strip()]
    actual_lines = [record.get("source_line") for record in records]
    require(actual_lines == expected_lines, "segmentation coverage or order is incomplete")

    changed_ids: list[str] = []
    human_ids: list[str] = []
    for record in records:
        line_number = record["source_line"]
        paragraph_id = f"L{line_number:03d}"
        source_text = source_lines[line_number - 1]
        segmented_text = segmented_lines[line_number - 1]
        require(record.get("schema_version") == 1, f"{paragraph_id} has wrong schema")
        require(
            record.get("workflow_version") == WORKFLOW_VERSION,
            f"{paragraph_id} has wrong workflow version",
        )
        require(record.get("source_sha256") == source_hash, f"{paragraph_id} has stale source hash")
        require(record.get("paragraph_id") == paragraph_id, f"{paragraph_id} id mismatch")
        require(record.get("source_text") == source_text, f"{paragraph_id} source text mismatch")
        require(
            record.get("source_line_sha256") == sha256_text(source_text),
            f"{paragraph_id} source-line hash mismatch",
        )
        require(
            record.get("segmented_chinese") == segmented_text,
            f"{paragraph_id} Djot and JSONL segmentation differ",
        )
        require("\n" not in segmented_text and segmented_text.strip(), f"{paragraph_id} is not line parallel")
        require(record.get("status") in ALLOWED_STATUSES, f"{paragraph_id} has invalid status")
        require(record.get("confidence") in {"high", "medium", "low"}, f"{paragraph_id} has invalid confidence")
        require(isinstance(record.get("protected_constraints"), list), f"{paragraph_id} lacks constraints")
        require(isinstance(record.get("risk_items"), list), f"{paragraph_id} lacks risk items")
        validate_meaning_units(record, paragraph_id, source_text)
        needs_human = validate_changes(record, paragraph_id, source_text)
        if record["changes"]:
            changed_ids.append(paragraph_id)
        if needs_human:
            human_ids.append(paragraph_id)
        if record.get("status") == "structural":
            require(source_text == segmented_text, f"{paragraph_id} structural text changed")

    return {
        "status": "PASS",
        "stage": "draft",
        "workflow_version": WORKFLOW_VERSION,
        "source_sha256": source_hash,
        "source_line_count": len(source_lines),
        "covered_nonblank_lines": len(records),
        "changed_paragraph_ids": changed_ids,
        "human_confirmation_paragraph_ids": human_ids,
    }


def validate_review(project: Path, draft_report: dict[str, Any]) -> dict[str, Any]:
    reviews = read_jsonl(project / REVIEW_JSONL)
    expected_ids = draft_report["changed_paragraph_ids"]
    require(
        [review.get("paragraph_id") for review in reviews] == expected_ids,
        "segmentation review coverage or order is incomplete",
    )
    human_ids = set(draft_report["human_confirmation_paragraph_ids"])
    segmentation = {
        record["paragraph_id"]: record
        for record in read_jsonl(project / SEGMENTATION_JSONL)
    }
    for review in reviews:
        paragraph_id = review["paragraph_id"]
        record = segmentation[paragraph_id]
        require(review.get("schema_version") == 1, f"{paragraph_id} review has wrong schema")
        require(
            review.get("workflow_version") == WORKFLOW_VERSION,
            f"{paragraph_id} review has wrong workflow version",
        )
        require(
            review.get("source_sha256") == draft_report["source_sha256"],
            f"{paragraph_id} review has stale source hash",
        )
        require(
            review.get("segmented_line_sha256")
            == sha256_text(record["segmented_chinese"]),
            f"{paragraph_id} review has stale segmentation hash",
        )
        reviewer = review.get("reviewer", {})
        require(reviewer.get("model") == "deepseek-v4-pro", f"{paragraph_id} review model is wrong")
        require(reviewer.get("reasoning_effort") == "max", f"{paragraph_id} review effort is wrong")
        require(
            isinstance(reviewer.get("session_id"), str) and reviewer["session_id"].strip(),
            f"{paragraph_id} review lacks a fresh session id",
        )
        require(review.get("decision") in REVIEW_DECISIONS, f"{paragraph_id} review is unresolved")
        require(review.get("resolved_status") == "safe", f"{paragraph_id} review did not close the record")
        require(review.get("omission_count") == 0, f"{paragraph_id} review found an omission")
        require(review.get("addition_count") == 0, f"{paragraph_id} review found an addition")
        if paragraph_id in human_ids:
            decision = review.get("commissioner_decision", {})
            require(decision.get("approved") is True, f"{paragraph_id} lacks commissioner approval")
            require(
                isinstance(decision.get("named_approver"), str)
                and decision["named_approver"].strip(),
                f"{paragraph_id} lacks a named commissioner",
            )
    return {
        **draft_report,
        "stage": "review",
        "reviewed_changed_records": len(reviews),
        "status": "PASS",
    }


def validate_project(project: Path, stage: str) -> dict[str, Any]:
    project = project.expanduser().resolve()
    require(project.is_dir(), f"project directory does not exist: {project}")
    draft_report = validate_draft(project)
    if stage == "review":
        return validate_review(project, draft_report)
    return draft_report


def parser() -> argparse.ArgumentParser:
    value = argparse.ArgumentParser(description=__doc__)
    value.add_argument("project", type=Path)
    value.add_argument("--stage", choices=("draft", "review"), default="draft")
    return value


def main() -> int:
    args = parser().parse_args()
    try:
        report = validate_project(args.project, args.stage)
    except SegmentationValidationError as exc:
        print(json.dumps({"status": "FAIL", "error": str(exc)}, ensure_ascii=False, indent=2))
        return 1
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
