#!/usr/bin/env python3
"""Fail closed on missing or inconsistent T1-Codex English-reader evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any


READER_FILES = {
    ("initial", "general_nonfiction_editor"): "english-reader-initial-general.json",
    ("initial", "english_dharma_editor"): "english-reader-initial-dharma.json",
    ("final", "general_nonfiction_editor"): "english-reader-final-general.json",
    ("final", "english_dharma_editor"): "english-reader-final-dharma.json",
}
READER_MANUSCRIPTS = {
    "initial": "english-reader-initial-manuscript.txt",
    "final": "english-reader-final-manuscript.txt",
}
SENSITIVE_CATEGORIES = [
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
]
LOW_RISK_CATEGORIES = [
    "grammar",
    "punctuation",
    "collocation",
    "accidental_repetition",
    "unnecessary_passive",
    "uniquely_recoverable_referent",
    "meaning_neutral_simplification",
    "ordinary_english_polish",
]
ALLOWED_DISPOSITIONS = {
    "accept",
    "partly_accept",
    "reject",
    "commissioner_choice",
}


class ReaderGateError(RuntimeError):
    """The document lacks valid evidence for the mandatory reader gate."""


def require(value: bool, message: str) -> None:
    if not value:
        raise ReaderGateError(message)


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
        raise ReaderGateError(f"invalid or missing JSON: {path.name}") from exc
    if not isinstance(value, dict):
        raise ReaderGateError(f"JSON root must be an object: {path.name}")
    return value


def contains_han(text: str) -> bool:
    return any(
        "\u3400" <= character <= "\u4dbf"
        or "\u4e00" <= character <= "\u9fff"
        or "\uf900" <= character <= "\ufaff"
        for character in text
    )


def validate_reader(
    report: dict[str, Any],
    *,
    phase: str,
    role: str,
    expected_target_hash: str | None,
    expected_visible_hash: str,
) -> tuple[str, dict[str, dict[str, Any]]]:
    label = f"{phase} {role}"
    require(report.get("schema_version") == 1, f"{label}: wrong schema_version")
    require(report.get("gate") == "english_only_reader", f"{label}: wrong gate")
    require(report.get("phase") == phase, f"{label}: wrong phase")
    require(report.get("role") == role, f"{label}: wrong role")
    target_hash = report.get("target_sha256")
    require(
        isinstance(target_hash, str) and len(target_hash) == 64,
        f"{label}: invalid target_sha256",
    )
    if expected_target_hash is not None:
        require(target_hash == expected_target_hash, f"{label}: stale target hash")
    require(report.get("visible_input_count") == 1, f"{label}: reader saw extra inputs")
    require(
        report.get("visible_input_sha256") == expected_visible_hash,
        f"{label}: reader-visible manuscript hash mismatch",
    )
    require(
        report.get("visible_input_derived_from_target_sha256") == target_hash,
        f"{label}: reader-visible manuscript is not bound to the target",
    )
    require(
        report.get("visible_input_is_english_only") is True,
        f"{label}: reader-visible manuscript is not declared English-only",
    )
    isolation = report.get("isolation", {})
    require(isolation.get("fresh_session") is True, f"{label}: session is not fresh")
    require(
        isolation.get("source_side_material_visible") is False,
        f"{label}: source-side material was visible",
    )
    require(
        isolation.get("prior_feedback_visible") is False,
        f"{label}: prior feedback was visible",
    )
    require(
        isolation.get("other_reader_output_visible") is False,
        f"{label}: other reader output was visible",
    )
    require(
        isolation.get("translator_context_visible") is False,
        f"{label}: translator context was visible",
    )
    session_id = report.get("session_id")
    require(isinstance(session_id, str) and session_id.strip(), f"{label}: session_id missing")
    require(
        isinstance(report.get("prompt_sha256"), str)
        and len(report["prompt_sha256"]) == 64,
        f"{label}: prompt_sha256 missing",
    )
    blocker_count = report.get("blocker_count")
    require(
        isinstance(blocker_count, int) and blocker_count >= 0,
        f"{label}: invalid blocker_count",
    )
    findings = report.get("findings")
    require(isinstance(findings, list), f"{label}: findings must be an array")
    counted_blockers = 0
    counted_actionable = 0
    indexed_findings: dict[str, dict[str, Any]] = {}
    for index, finding in enumerate(findings, start=1):
        require(isinstance(finding, dict), f"{label}: finding {index} is not an object")
        finding_id = finding.get("id")
        require(
            isinstance(finding_id, str) and finding_id.strip(),
            f"{label}: finding {index} has no id",
        )
        require(
            finding_id not in indexed_findings,
            f"{label}: duplicate finding id {finding_id}",
        )
        require(
            isinstance(finding.get("blocker"), bool),
            f"{label}: finding {index} has no boolean blocker field",
        )
        require(
            isinstance(finding.get("actionable"), bool),
            f"{label}: finding {index} has no boolean actionable field",
        )
        if finding["blocker"]:
            counted_blockers += 1
        if finding["actionable"]:
            counted_actionable += 1
        indexed_findings[finding_id] = finding
    require(
        blocker_count == counted_blockers,
        f"{label}: blocker_count does not match findings",
    )
    require(
        report.get("unresolved_actionable_count") == counted_actionable,
        f"{label}: unresolved_actionable_count does not match findings",
    )
    if phase == "final":
        require(counted_blockers == 0, f"{label}: final blocker remains")
        require(counted_actionable == 0, f"{label}: final actionable finding remains")
    return session_id, indexed_findings


def validate_adjudication_decision(
    decision: dict[str, Any],
    *,
    expected_role: str,
    expected_finding_id: str,
    source_text: str,
) -> bool:
    label = f"adjudication {expected_role}:{expected_finding_id}"
    require(decision.get("reader_role") == expected_role, f"{label}: wrong reader role")
    require(decision.get("finding_id") == expected_finding_id, f"{label}: wrong finding id")
    risk_class = decision.get("risk_class")
    require(risk_class in {"low_risk", "sensitive"}, f"{label}: invalid risk class")
    category = decision.get("category")
    allowed_categories = LOW_RISK_CATEGORIES if risk_class == "low_risk" else SENSITIVE_CATEGORIES
    require(category in allowed_categories, f"{label}: category does not match risk class")
    require(
        decision.get("disposition") in ALLOWED_DISPOSITIONS,
        f"{label}: unresolved or invalid disposition",
    )
    evidence = decision.get("source_evidence")
    require(
        isinstance(evidence, list)
        and evidence
        and all(isinstance(item, str) and item.strip() for item in evidence),
        f"{label}: source evidence is missing",
    )
    for item in evidence:
        literal = item.strip()
        require(
            len(literal) >= 2 and literal in source_text,
            f"{label}: source evidence is not a literal span of source.dj",
        )
    require(
        isinstance(decision.get("fidelity_rationale"), str)
        and decision["fidelity_rationale"].strip(),
        f"{label}: fidelity rationale is missing",
    )
    applied = decision.get("applied")
    require(isinstance(applied, bool), f"{label}: applied flag is missing")
    if risk_class == "low_risk":
        require(
            decision.get("checked_against_full_chinese") is True,
            f"{label}: low-risk edit lacks complete Chinese check",
        )
        return False

    if not applied:
        return False
    for field in ("current_english", "proposed_english", "reason", "fidelity_effect"):
        require(
            isinstance(decision.get(field), str) and decision[field].strip(),
            f"{label}: sensitive applied change lacks {field}",
        )
    commissioner = decision.get("commissioner_decision")
    require(isinstance(commissioner, dict), f"{label}: commissioner decision is missing")
    require(commissioner.get("approved") is True, f"{label}: commissioner approval is missing")
    require(
        isinstance(commissioner.get("named_commissioner"), str)
        and commissioner["named_commissioner"].strip(),
        f"{label}: named commissioner is missing",
    )
    require(
        isinstance(commissioner.get("selected_option"), str)
        and commissioner["selected_option"].strip(),
        f"{label}: selected option is missing",
    )
    return True


def validate_reader_gate(project: Path) -> dict[str, Any]:
    source = project / "source.dj"
    target = project / "target.dj"
    require(source.is_file(), "source.dj is missing")
    require(target.is_file(), "target.dj is missing")
    try:
        source_text = source.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise ReaderGateError("source.dj is not valid UTF-8") from exc
    source_hash = sha256_file(source)
    final_target_hash = sha256_file(target)

    reports: dict[tuple[str, str], dict[str, Any]] = {}
    sessions: list[str] = []
    initial_findings: dict[tuple[str, str], dict[str, Any]] = {}
    initial_hashes: set[str] = set()
    visible_hashes: dict[str, str] = {}
    for phase, filename in READER_MANUSCRIPTS.items():
        manuscript = project / filename
        require(manuscript.is_file(), f"{filename} is missing")
        try:
            visible_text = manuscript.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            raise ReaderGateError(f"invalid reader-visible manuscript: {filename}") from exc
        require(visible_text.strip() != "", f"{filename} is empty")
        require(not contains_han(visible_text), f"{filename} exposes Chinese")
        visible_hashes[phase] = sha256_file(manuscript)
    for key, filename in READER_FILES.items():
        phase, role = key
        report = load_object(project / filename)
        expected_hash = final_target_hash if phase == "final" else None
        session_id, indexed_findings = validate_reader(
            report,
            phase=phase,
            role=role,
            expected_target_hash=expected_hash,
            expected_visible_hash=visible_hashes[phase],
        )
        sessions.append(session_id)
        if phase == "initial":
            initial_hashes.add(str(report["target_sha256"]))
            for finding_id, finding in indexed_findings.items():
                initial_findings[(role, finding_id)] = finding
        else:
            require(report["blocker_count"] == 0, f"{filename}: final blocker remains")
        reports[key] = report
    require(len(initial_hashes) == 1, "initial readers did not read the same target hash")
    require(len(set(sessions)) == 4, "reader sessions are not mutually isolated")
    initial_target_hash = next(iter(initial_hashes))

    adjudication = load_object(project / "english-reader-adjudication.json")
    require(adjudication.get("schema_version") == 1, "adjudication: wrong schema_version")
    require(adjudication.get("gate") == "reader_adjudication", "adjudication: wrong gate")
    require(adjudication.get("source_sha256") == source_hash, "adjudication: stale source")
    require(
        adjudication.get("input_target_sha256") == initial_target_hash,
        "adjudication: wrong input target hash",
    )
    require(
        adjudication.get("output_target_sha256") == final_target_hash,
        "adjudication: wrong output target hash",
    )
    require(
        adjudication.get("every_reader_finding_checked_against_full_chinese") is True,
        "adjudication: reader findings were not all checked against Chinese",
    )
    require(
        adjudication.get("every_reader_finding_classified_by_risk") is True,
        "adjudication: reader findings were not all classified by risk",
    )
    require(
        adjudication.get("low_risk_edits_checked_against_full_chinese") is True,
        "adjudication: low-risk edits were not checked against Chinese",
    )
    require(
        adjudication.get("unresolved_reader_blockers") == 0,
        "adjudication: unresolved reader blocker",
    )
    decisions_list = adjudication.get("decisions")
    require(isinstance(decisions_list, list), "adjudication: decisions must be an array")
    indexed_decisions: dict[tuple[str, str], dict[str, Any]] = {}
    applied_sensitive_count = 0
    for index, decision in enumerate(decisions_list, start=1):
        require(isinstance(decision, dict), f"adjudication: decision {index} is not an object")
        key = (str(decision.get("reader_role")), str(decision.get("finding_id")))
        require(key not in indexed_decisions, f"adjudication: duplicate decision {key[0]}:{key[1]}")
        require(key in initial_findings, f"adjudication: decision has no matching reader finding {key[0]}:{key[1]}")
        applied_sensitive_count += int(
            validate_adjudication_decision(
                decision,
                expected_role=key[0],
                expected_finding_id=key[1],
                source_text=source_text,
            )
        )
        indexed_decisions[key] = decision
    require(
        set(indexed_decisions) == set(initial_findings),
        "adjudication: reader finding coverage is incomplete",
    )
    require(
        adjudication.get("decision_count") == len(decisions_list),
        "adjudication: decision_count does not match decisions",
    )

    decisions = load_object(project / "commissioner-decisions.json")
    require(decisions.get("schema_version") == 1, "commissioner decisions: wrong schema")
    require(decisions.get("gate") == "commissioner_sensitive_changes", "commissioner decisions: wrong gate")
    require(
        decisions.get("sensitive_categories") == SENSITIVE_CATEGORIES,
        "commissioner decisions: sensitive categories are incomplete",
    )
    require(
        decisions.get("low_risk_direct_edit_categories") == LOW_RISK_CATEGORIES,
        "commissioner decisions: low-risk categories are incomplete",
    )
    sensitive_count = decisions.get("sensitive_change_count")
    require(
        isinstance(sensitive_count, int) and sensitive_count >= 0,
        "commissioner decisions: invalid sensitive_change_count",
    )
    if sensitive_count:
        require(
            decisions.get("options_and_fidelity_tradeoffs_presented") is True,
            "commissioner decisions: options and fidelity tradeoffs were not presented",
        )
    require(
        sensitive_count == applied_sensitive_count,
        "commissioner decisions: sensitive_change_count does not match applied decisions",
    )
    require(decisions.get("unresolved_count") == 0, "commissioner decision unresolved")
    require(
        decisions.get("unapproved_applied_count") == 0,
        "unapproved sensitive change was applied",
    )
    require(
        decisions.get("target_sha256") == final_target_hash,
        "commissioner decisions: stale target hash",
    )

    human_feedback = load_object(project / "human-feedback-learning.json")
    require(human_feedback.get("schema_version") == 1, "human feedback: wrong schema")
    require(human_feedback.get("gate") == "human_feedback_learning", "human feedback: wrong gate")
    require(human_feedback.get("source_sha256") == source_hash, "human feedback: stale source")
    require(
        human_feedback.get("input_target_sha256") == initial_target_hash,
        "human feedback: wrong input target hash",
    )
    feedback_count = human_feedback.get("feedback_item_count")
    principle_count = human_feedback.get("reusable_principle_count")
    require(
        isinstance(feedback_count, int) and feedback_count >= 0,
        "human feedback: invalid feedback_item_count",
    )
    require(
        isinstance(principle_count, int) and principle_count >= 0,
        "human feedback: invalid reusable_principle_count",
    )
    require(human_feedback.get("every_item_assessed") is True, "human feedback: item assessment incomplete")
    require(
        human_feedback.get("local_preferences_separated_from_reusable_principles") is True,
        "human feedback: local and reusable guidance were not separated",
    )
    require(
        human_feedback.get("full_document_analogue_scan_completed") is True,
        "human feedback: full-document analogue scan is incomplete",
    )
    require(
        human_feedback.get("sensitive_feedback_routed_to_commissioner") is True,
        "human feedback: sensitive items were not routed to the commissioner",
    )
    require(
        human_feedback.get("unresolved_sensitive_feedback_count") == 0,
        "human feedback: unresolved sensitive feedback remains",
    )
    if feedback_count == 0:
        require(principle_count == 0, "human feedback: zero-item receipt contains reusable principles")

    chinese_recheck = load_object(project / "post-reader-chinese-recheck.json")
    require(chinese_recheck.get("schema_version") == 1, "Chinese recheck: wrong schema")
    require(chinese_recheck.get("scope") == "full_document", "Chinese recheck is not complete")
    require(chinese_recheck.get("status") == "PASS", "Chinese recheck did not pass")
    require(chinese_recheck.get("source_sha256") == source_hash, "Chinese recheck: stale source")
    require(
        chinese_recheck.get("target_sha256") == final_target_hash,
        "Chinese recheck: stale target",
    )

    regression = load_object(project / "post-reader-semantic-regression.json")
    require(regression.get("schema_version") == 1, "semantic regression: wrong schema")
    require(regression.get("scope") == "full_document", "semantic regression is not full-document")
    require(regression.get("source_sha256") == source_hash, "semantic regression: stale source")
    require(
        regression.get("target_sha256") == final_target_hash,
        "semantic regression: stale target",
    )
    directions = regression.get("directions", {})
    require(
        directions.get("chinese_to_english") == "PASS"
        and directions.get("english_to_chinese") == "PASS",
        "semantic regression did not pass both directions",
    )
    require(
        regression.get("unapproved_omission_count") == 0,
        "semantic regression found an unapproved omission",
    )
    require(
        regression.get("unapproved_addition_count") == 0,
        "semantic regression found an unapproved addition",
    )

    return {
        "schema_version": 1,
        "status": "PASS",
        "source_sha256": source_hash,
        "target_sha256": final_target_hash,
        "initial_target_sha256": initial_target_hash,
        "final_reader_blockers": {
            "general_nonfiction_editor": reports[("final", "general_nonfiction_editor")]["blocker_count"],
            "english_dharma_editor": reports[("final", "english_dharma_editor")]["blocker_count"],
        },
        "final_reader_actionable_findings": {
            "general_nonfiction_editor": reports[("final", "general_nonfiction_editor")]["unresolved_actionable_count"],
            "english_dharma_editor": reports[("final", "english_dharma_editor")]["unresolved_actionable_count"],
        },
        "human_feedback_item_count": feedback_count,
        "reusable_human_feedback_principle_count": principle_count,
        "unapproved_omission_count": 0,
        "unapproved_addition_count": 0,
        "unapproved_sensitive_change_count": 0,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("project", type=Path)
    args = parser.parse_args()
    try:
        report = validate_reader_gate(args.project.resolve())
    except ReaderGateError as exc:
        print(json.dumps({"status": "FAIL", "error": str(exc)}, indent=2))
        return 1
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
