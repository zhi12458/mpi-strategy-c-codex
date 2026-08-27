#!/usr/bin/env python3
"""Validate T1.1 semantic-bridge artifacts and run disposable contract tests."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import tempfile
from pathlib import Path
from typing import Any

from t1_runtime import StrategyT1Error, atomic_json, sha256_file, utc_now


WORKFLOW_VERSION = "1.1.1"
RISK_NAME = "semantic-risk-register.jsonl"
BRIDGE_NAME = "semantic-bridge.jsonl"
REVIEW_NAME = "semantic-bridge-review.jsonl"
DECISIONS_NAME = "semantic-decisions.jsonl"
COVERAGE_NAME = "constraint-coverage.jsonl"
REGRESSION_NAME = "semantic-regression.jsonl"


def canonical_hash(value: dict[str, Any]) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def line_hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        raise StrategyT1Error(f"required T1.1 artifact is missing: {path.name}")
    records: list[dict[str, Any]] = []
    for number, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not raw.strip():
            continue
        try:
            value = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise StrategyT1Error(f"invalid JSONL at {path.name}:{number}") from exc
        if not isinstance(value, dict):
            raise StrategyT1Error(f"JSONL record must be an object at {path.name}:{number}")
        records.append(value)
    return records


def require_text(record: dict[str, Any], field: str, where: str) -> str:
    value = record.get(field)
    if not isinstance(value, str) or not value.strip():
        raise StrategyT1Error(f"{where} requires nonempty {field}")
    return value


def require_list(record: dict[str, Any], field: str, where: str, *, nonempty: bool = False) -> list[Any]:
    value = record.get(field)
    if not isinstance(value, list) or (nonempty and not value):
        suffix = " nonempty" if nonempty else ""
        raise StrategyT1Error(f"{where} requires{suffix} list {field}")
    return value


def record_ids(records: list[dict[str, Any]], name: str) -> list[str]:
    ids = [require_text(item, "paragraph_id", name) for item in records]
    if len(ids) != len(set(ids)):
        raise StrategyT1Error(f"duplicate paragraph_id in {name}")
    return ids


def source_index(source: Path) -> tuple[str, dict[str, tuple[int, str]]]:
    if not source.is_file():
        raise StrategyT1Error("source.dj is missing")
    rows: dict[str, tuple[int, str]] = {}
    for number, value in enumerate(source.read_text(encoding="utf-8").splitlines(), start=1):
        if value.strip():
            rows[f"L{number:03d}"] = (number, value)
    if not rows:
        raise StrategyT1Error("source.dj has no nonblank units")
    return sha256_file(source), rows


def validate_source_binding(
    record: dict[str, Any],
    paragraph_id: str,
    source_sha256: str,
    source_rows: dict[str, tuple[int, str]],
    where: str,
) -> None:
    if record.get("schema_version") != 1 or record.get("workflow_version") != WORKFLOW_VERSION:
        raise StrategyT1Error(f"{where} has stale schema or workflow version")
    if record.get("source_sha256") != source_sha256:
        raise StrategyT1Error(f"{where} source hash mismatch")
    if paragraph_id not in source_rows:
        raise StrategyT1Error(f"{where} references unknown source unit {paragraph_id}")
    number, text = source_rows[paragraph_id]
    if record.get("source_line") != number or record.get("source_line_sha256") != line_hash(text):
        raise StrategyT1Error(f"{where} source-line binding mismatch for {paragraph_id}")
    if "source_excerpt" in record and record.get("source_excerpt") != text:
        raise StrategyT1Error(f"{where} source excerpt mismatch for {paragraph_id}")


def validate_project(project: Path, stage: str = "all") -> dict[str, Any]:
    project = project.expanduser().resolve()
    source = project / "source.dj"
    source_sha256, source_rows = source_index(source)
    stages = ["risk", "bridge", "review", "decisions", "coverage", "regression"]
    if stage not in {*stages, "all"}:
        raise StrategyT1Error(f"unknown semantic validation stage: {stage}")
    stop = len(stages) - 1 if stage == "all" else stages.index(stage)
    evidence: dict[str, Any] = {
        "schema_version": 1,
        "workflow_version": WORKFLOW_VERSION,
        "project": str(project),
        "source_sha256": source_sha256,
        "source_nonblank_units": len(source_rows),
    }

    risk = load_jsonl(project / RISK_NAME)
    risk_ids = record_ids(risk, RISK_NAME)
    if risk_ids != list(source_rows):
        raise StrategyT1Error("semantic risk register must cover every nonblank source unit in order")
    high_ids: list[str] = []
    for record in risk:
        pid = record["paragraph_id"]
        validate_source_binding(record, pid, source_sha256, source_rows, RISK_NAME)
        level = record.get("risk_level")
        if level not in {"high", "low", "structural"}:
            raise StrategyT1Error(f"invalid risk_level for {pid}")
        reasons = require_list(record, "risk_reasons", RISK_NAME)
        requires_bridge = record.get("requires_bridge")
        if not isinstance(requires_bridge, bool):
            raise StrategyT1Error(f"requires_bridge must be boolean for {pid}")
        if (level == "high") != requires_bridge:
            raise StrategyT1Error(f"only high-risk units may require a bridge: {pid}")
        if level == "high" and not reasons:
            raise StrategyT1Error(f"high-risk unit has no risk evidence: {pid}")
        if requires_bridge:
            high_ids.append(pid)
    evidence["risk_register"] = {"records": len(risk), "high_risk": len(high_ids)}
    if stop == 0:
        return evidence

    bridge = load_jsonl(project / BRIDGE_NAME)
    bridge_ids = record_ids(bridge, BRIDGE_NAME)
    if bridge_ids != high_ids:
        raise StrategyT1Error("semantic bridge records must exactly match high-risk units in source order")
    bridge_by_id: dict[str, dict[str, Any]] = {}
    constraint_keys: list[tuple[str, str]] = []
    for record in bridge:
        pid = record["paragraph_id"]
        validate_source_binding(record, pid, source_sha256, source_rows, BRIDGE_NAME)
        require_text(record, "meaning_explication_zh", BRIDGE_NAME)
        require_list(record, "risk_reasons", BRIDGE_NAME, nonempty=True)
        roles = record.get("explicit_roles")
        if not isinstance(roles, dict):
            raise StrategyT1Error(f"explicit_roles must be an object for {pid}")
        require_list(record, "propositions", BRIDGE_NAME, nonempty=True)
        require_list(record, "logic_relations", BRIDGE_NAME)
        require_list(record, "scope_and_modifiers", BRIDGE_NAME)
        require_list(record, "rhetoric_and_voice", BRIDGE_NAME)
        require_list(record, "english_structure_plan_zh", BRIDGE_NAME, nonempty=True)
        constraints = require_list(record, "constraints", BRIDGE_NAME, nonempty=True)
        require_list(record, "must_not_add", BRIDGE_NAME)
        require_list(record, "ambiguity_options", BRIDGE_NAME)
        if record.get("confidence") not in {"high", "medium", "low"}:
            raise StrategyT1Error(f"invalid bridge confidence for {pid}")
        generator = record.get("generated_by")
        if not isinstance(generator, dict) or not all(generator.get(key) for key in ("provider", "model", "reasoning_effort")):
            raise StrategyT1Error(f"missing bridge provenance for {pid}")
        seen: set[str] = set()
        for constraint in constraints:
            if not isinstance(constraint, dict):
                raise StrategyT1Error(f"constraint must be an object for {pid}")
            cid = require_text(constraint, "constraint_id", BRIDGE_NAME)
            require_text(constraint, "kind", BRIDGE_NAME)
            require_text(constraint, "requirement_zh", BRIDGE_NAME)
            require_text(constraint, "source_evidence", BRIDGE_NAME)
            if cid in seen:
                raise StrategyT1Error(f"duplicate constraint_id for {pid}: {cid}")
            seen.add(cid)
            constraint_keys.append((pid, cid))
        bridge_by_id[pid] = record
    evidence["bridge"] = {"records": len(bridge), "constraints": len(constraint_keys)}
    if stop == 1:
        return evidence

    reviews = load_jsonl(project / REVIEW_NAME)
    if record_ids(reviews, REVIEW_NAME) != high_ids:
        raise StrategyT1Error("bridge review must cover every bridge record in order")
    review_by_id: dict[str, dict[str, Any]] = {}
    for record in reviews:
        pid = record["paragraph_id"]
        validate_source_binding(record, pid, source_sha256, source_rows, REVIEW_NAME)
        if record.get("bridge_record_sha256") != canonical_hash(bridge_by_id[pid]):
            raise StrategyT1Error(f"bridge review hash mismatch for {pid}")
        decision = record.get("decision")
        if decision not in {"agree", "partial", "disagree"}:
            raise StrategyT1Error(f"invalid bridge review decision for {pid}")
        require_text(record, "rationale_zh", REVIEW_NAME)
        require_text(record, "source_evidence", REVIEW_NAME)
        require_list(record, "issues", REVIEW_NAME)
        requires_human = record.get("requires_human")
        if not isinstance(requires_human, bool):
            raise StrategyT1Error(f"requires_human must be boolean for {pid}")
        if (decision != "agree" or bridge_by_id[pid].get("confidence") != "high") and not requires_human:
            raise StrategyT1Error(f"disputed or low-confidence bridge must require human review: {pid}")
        reviewer = record.get("reviewed_by")
        if not isinstance(reviewer, dict) or not all(reviewer.get(key) for key in ("provider", "model", "reasoning_effort")):
            raise StrategyT1Error(f"missing bridge-review provenance for {pid}")
        review_by_id[pid] = record
    evidence["bridge_review"] = {"records": len(reviews), "human_queue": sum(bool(item["requires_human"]) for item in reviews)}
    if stop == 2:
        return evidence

    decisions = load_jsonl(project / DECISIONS_NAME)
    if record_ids(decisions, DECISIONS_NAME) != high_ids:
        raise StrategyT1Error("semantic decisions must cover every bridge record in order")
    decision_by_id: dict[str, dict[str, Any]] = {}
    final_constraint_keys: list[tuple[str, str]] = []
    for record in decisions:
        pid = record["paragraph_id"]
        validate_source_binding(record, pid, source_sha256, source_rows, DECISIONS_NAME)
        if record.get("bridge_record_sha256") != canonical_hash(bridge_by_id[pid]):
            raise StrategyT1Error(f"semantic decision bridge hash mismatch for {pid}")
        if record.get("review_record_sha256") != canonical_hash(review_by_id[pid]):
            raise StrategyT1Error(f"semantic decision review hash mismatch for {pid}")
        status = record.get("status")
        if status not in {"auto_selected", "model_provisional", "human_selected", "blocked"}:
            raise StrategyT1Error(f"invalid semantic decision status for {pid}")
        if status == "blocked":
            raise StrategyT1Error(f"unresolved semantic decision blocks translation: {pid}")
        if review_by_id[pid]["requires_human"]:
            if status == "human_selected":
                if not str(record.get("human_approver", "")).strip():
                    raise StrategyT1Error(f"human-selected semantic decision lacks named approver: {pid}")
            elif status == "model_provisional":
                provisional = record.get("provisional_by")
                if not isinstance(provisional, dict) or not all(
                    provisional.get(key) for key in ("provider", "model", "reasoning_effort")
                ):
                    raise StrategyT1Error(f"model-provisional decision lacks provenance: {pid}")
                if record.get("human_review_required") is not True or record.get("release_block") is not True:
                    raise StrategyT1Error(f"model-provisional decision must retain the final human release block: {pid}")
                require_text(record, "provisional_resolution_basis", DECISIONS_NAME)
            else:
                raise StrategyT1Error(f"human-required semantic decision is unresolved: {pid}")
        elif status != "auto_selected":
            raise StrategyT1Error(f"agreed high-confidence bridge should be auto-selected: {pid}")
        require_text(record, "final_explication_zh", DECISIONS_NAME)
        require_text(record, "rationale_zh", DECISIONS_NAME)
        constraints = require_list(record, "final_constraints", DECISIONS_NAME, nonempty=True)
        for constraint in constraints:
            cid = require_text(constraint, "constraint_id", DECISIONS_NAME)
            require_text(constraint, "kind", DECISIONS_NAME)
            require_text(constraint, "requirement_zh", DECISIONS_NAME)
            require_text(constraint, "source_evidence", DECISIONS_NAME)
            final_constraint_keys.append((pid, cid))
        decision_by_id[pid] = record
    if len(final_constraint_keys) != len(set(final_constraint_keys)):
        raise StrategyT1Error("final semantic constraints are not unique")
    evidence["semantic_decisions"] = {
        "records": len(decisions),
        "constraints": len(final_constraint_keys),
        "model_provisional": sum(item.get("status") == "model_provisional" for item in decisions),
        "final_human_review_required": any(item.get("status") == "model_provisional" for item in decisions),
    }
    if stop == 3:
        return evidence

    target = project / "target.dj"
    target_sha256, target_rows = source_index(target)
    if list(target_rows) != list(source_rows):
        raise StrategyT1Error("target.dj nonblank line positions do not match source.dj")
    coverage = load_jsonl(project / COVERAGE_NAME)
    coverage_keys: list[tuple[str, str]] = []
    for record in coverage:
        pid = require_text(record, "paragraph_id", COVERAGE_NAME)
        cid = require_text(record, "constraint_id", COVERAGE_NAME)
        if record.get("schema_version") != 1 or record.get("workflow_version") != WORKFLOW_VERSION:
            raise StrategyT1Error("constraint coverage has stale schema or workflow version")
        if record.get("source_sha256") != source_sha256 or record.get("target_sha256") != target_sha256:
            raise StrategyT1Error(f"constraint coverage hash mismatch for {pid}/{cid}")
        if record.get("status") != "covered":
            raise StrategyT1Error(f"semantic constraint is not covered: {pid}/{cid}")
        require_text(record, "target_span", COVERAGE_NAME)
        require_text(record, "explanation_zh", COVERAGE_NAME)
        if pid not in target_rows or record.get("target_line") != target_rows[pid][0]:
            raise StrategyT1Error(f"constraint coverage target line mismatch for {pid}/{cid}")
        if record["target_span"] not in target_rows[pid][1]:
            raise StrategyT1Error(f"constraint target span is not present for {pid}/{cid}")
        coverage_keys.append((pid, cid))
    if coverage_keys != final_constraint_keys:
        raise StrategyT1Error("constraint coverage must match every frozen constraint exactly in order")
    evidence["constraint_coverage"] = {"records": len(coverage), "target_sha256": target_sha256}
    if stop == 4:
        return evidence

    regression = load_jsonl(project / REGRESSION_NAME)
    if record_ids(regression, REGRESSION_NAME) != high_ids:
        raise StrategyT1Error("semantic regression must cover every high-risk unit in order")
    for record in regression:
        pid = record["paragraph_id"]
        validate_source_binding(record, pid, source_sha256, source_rows, REGRESSION_NAME)
        if record.get("target_sha256") != target_sha256:
            raise StrategyT1Error(f"semantic regression target hash mismatch for {pid}")
        if record.get("source_to_target") != "pass" or record.get("target_to_source") != "pass":
            raise StrategyT1Error(f"bidirectional semantic regression failed for {pid}")
        if require_list(record, "unsupported_additions", REGRESSION_NAME):
            raise StrategyT1Error(f"unsupported target addition remains for {pid}")
        findings = require_list(record, "findings", REGRESSION_NAME)
        if any(isinstance(item, dict) and item.get("severity") in {"critical", "major"} for item in findings):
            raise StrategyT1Error(f"critical or major semantic finding remains for {pid}")
        if record.get("status") != "pass":
            raise StrategyT1Error(f"semantic regression is not passing for {pid}")
        reviewer = record.get("reviewed_by")
        if not isinstance(reviewer, dict) or not all(reviewer.get(key) for key in ("provider", "model", "reasoning_effort")):
            raise StrategyT1Error(f"missing semantic-regression provenance for {pid}")
    evidence["semantic_regression"] = {"records": len(regression), "status": "PASS"}
    evidence["status"] = "PASS"
    return evidence


def write_jsonl(path: Path, records: list[dict[str, Any]]) -> None:
    path.write_text("".join(json.dumps(item, ensure_ascii=False, sort_keys=True) + "\n" for item in records), encoding="utf-8")


def fixture_records(project: Path) -> dict[str, list[dict[str, Any]]]:
    source = project / "source.dj"
    source.write_text("# 标题\n\n我们为什么要有这样的担当？\n", encoding="utf-8")
    (project / "target.dj").write_text("# Title\n\nWhy should we take on this responsibility?\n", encoding="utf-8")
    source_sha = sha256_file(source)
    target_sha = sha256_file(project / "target.dj")
    rows = source_index(source)[1]
    base = lambda pid: {
        "schema_version": 1,
        "workflow_version": WORKFLOW_VERSION,
        "paragraph_id": pid,
        "source_line": rows[pid][0],
        "source_sha256": source_sha,
        "source_line_sha256": line_hash(rows[pid][1]),
        "source_excerpt": rows[pid][1],
    }
    risk = [
        {**base("L001"), "risk_level": "structural", "risk_reasons": [], "requires_bridge": False},
        {**base("L003"), "risk_level": "high", "risk_reasons": ["责任义", "问句语气"], "requires_bridge": True},
    ]
    constraint = {
        "constraint_id": "L003-C01",
        "kind": "semantic_role",
        "requirement_zh": "担当必须保留承担责任的含义",
        "source_evidence": "这样的担当",
    }
    bridge = [{
        **base("L003"),
        "risk_reasons": ["责任义", "问句语气"],
        "meaning_explication_zh": "我们为什么应当承担这样的责任？",
        "explicit_roles": {"subjects": ["我们"], "predicates": ["承担"], "objects": ["责任"], "references": ["这样"]},
        "propositions": [{"proposition_id": "L003-P01", "text_zh": "我们应当承担这种责任"}],
        "logic_relations": [],
        "scope_and_modifiers": ["这样的修饰担当"],
        "rhetoric_and_voice": ["保留问句"],
        "english_structure_plan_zh": ["使用直接问句；以we作主语；使用承担责任的谓语"],
        "constraints": [constraint],
        "must_not_add": ["不得弱化为只有决心"],
        "ambiguity_options": [],
        "confidence": "high",
        "generated_by": {"provider": "deepseek", "model": "deepseek-v4-flash", "reasoning_effort": "high"},
    }]
    review = [{
        **base("L003"),
        "bridge_record_sha256": canonical_hash(bridge[0]),
        "decision": "agree",
        "rationale_zh": "释义准确保留责任义和问句。",
        "source_evidence": "担当、为什么",
        "issues": [],
        "requires_human": False,
        "reviewed_by": {"provider": "deepseek", "model": "deepseek-v4-pro", "reasoning_effort": "max"},
    }]
    decisions = [{
        **base("L003"),
        "bridge_record_sha256": canonical_hash(bridge[0]),
        "review_record_sha256": canonical_hash(review[0]),
        "status": "auto_selected",
        "human_approver": None,
        "final_explication_zh": bridge[0]["meaning_explication_zh"],
        "final_constraints": [constraint],
        "rationale_zh": "独立复核一致且置信度高。",
    }]
    coverage = [{
        "schema_version": 1,
        "workflow_version": WORKFLOW_VERSION,
        "paragraph_id": "L003",
        "constraint_id": "L003-C01",
        "source_sha256": source_sha,
        "target_sha256": target_sha,
        "target_line": 3,
        "target_span": "take on this responsibility",
        "status": "covered",
        "explanation_zh": "明确承载担当的责任义。",
    }]
    regression = [{
        **base("L003"),
        "target_sha256": target_sha,
        "source_to_target": "pass",
        "target_to_source": "pass",
        "unsupported_additions": [],
        "findings": [],
        "status": "pass",
        "reviewed_by": {"provider": "deepseek", "model": "deepseek-v4-pro", "reasoning_effort": "max"},
    }]
    return {RISK_NAME: risk, BRIDGE_NAME: bridge, REVIEW_NAME: review, DECISIONS_NAME: decisions, COVERAGE_NAME: coverage, REGRESSION_NAME: regression}


def run_contract_tests(root: Path) -> dict[str, Any]:
    cases: list[dict[str, Any]] = []
    with tempfile.TemporaryDirectory(prefix="mpi-t11-semantic-contract-") as directory:
        project = Path(directory)
        records = fixture_records(project)
        for name, value in records.items():
            write_jsonl(project / name, value)
        validate_project(project)
        cases.append({"case": "valid_complete_artifacts", "passed": True})

        provisional = copy.deepcopy(records)
        provisional_review = provisional[REVIEW_NAME][0]
        provisional_review.update({
            "decision": "partial",
            "issues": [{"severity": "major", "description_zh": "需暂定裁决"}],
            "requires_human": True,
        })
        provisional_decision = provisional[DECISIONS_NAME][0]
        provisional_decision.update({
            "review_record_sha256": canonical_hash(provisional_review),
            "status": "model_provisional",
            "human_approver": None,
            "human_review_required": True,
            "release_block": True,
            "provisional_resolution_basis": "采用独立 Pro 中文复核建议继续生成 AI 草稿。",
            "provisional_by": {"provider": "deepseek", "model": "deepseek-v4-pro", "reasoning_effort": "max"},
        })
        for name, value in provisional.items():
            write_jsonl(project / name, value)
        validate_project(project)
        cases.append({"case": "model_provisional_allows_drafting_but_retains_release_block", "passed": True})

        mutations = [
            ("wrong_source_hash", RISK_NAME, lambda values: values[1].__setitem__("source_sha256", "0" * 64)),
            ("missing_high_risk_bridge", BRIDGE_NAME, lambda values: values.clear()),
            ("bridge_without_evidence", BRIDGE_NAME, lambda values: values[0]["constraints"][0].__setitem__("source_evidence", "")),
            ("unresolved_disagreement", REVIEW_NAME, lambda values: values[0].update({"decision": "disagree", "requires_human": False})),
            ("uncovered_constraint", COVERAGE_NAME, lambda values: values[0].__setitem__("status", "uncovered")),
            ("failed_bidirectional_regression", REGRESSION_NAME, lambda values: values[0].__setitem__("source_to_target", "fail")),
        ]
        for label, filename, mutate in mutations:
            changed = copy.deepcopy(records)
            mutate(changed[filename])
            for name, value in changed.items():
                write_jsonl(project / name, value)
            try:
                validate_project(project)
            except StrategyT1Error:
                cases.append({"case": label, "passed": True, "blocked": True})
            else:
                raise StrategyT1Error(f"semantic contract test did not block: {label}")

        known_error_patterns = (
            "担当_to_resolve",
            "生命提升_to_generic_development",
            "苍生_to_all_people",
            "weakened_superlative",
            "question_to_statement",
            "unsupported_strengthening",
            "singular_plural_drift",
        )
        for label in known_error_patterns:
            changed = copy.deepcopy(records)
            changed[REGRESSION_NAME][0].update({
                "source_to_target": "fail",
                "findings": [{"severity": "major", "category": "known_error_replay", "pattern": label}],
                "status": "fail",
            })
            for name, value in changed.items():
                write_jsonl(project / name, value)
            try:
                validate_project(project)
            except StrategyT1Error:
                cases.append({"case": f"known_error_replay_{label}", "passed": True, "blocked": True})
            else:
                raise StrategyT1Error(f"known-error replay did not block: {label}")

    report = {
        "schema_version": 1,
        "workflow_version": WORKFLOW_VERSION,
        "status": "PASS",
        "created_at": utc_now(),
        "cases": cases,
    }
    output = root / "semantic-bridge-contract-report.json"
    atomic_json(output, report)
    report["report_absolute_path"] = str(output.resolve())
    report["report_sha256"] = sha256_file(output)
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    validate = sub.add_parser("validate")
    validate.add_argument("--project", type=Path, required=True)
    validate.add_argument("--stage", choices=("risk", "bridge", "review", "decisions", "coverage", "regression", "all"), default="all")
    contracts = sub.add_parser("contract-tests")
    contracts.add_argument("--output-root", type=Path, required=True)
    args = parser.parse_args()
    try:
        if args.command == "validate":
            result = validate_project(args.project, args.stage)
        else:
            args.output_root.mkdir(parents=True, exist_ok=True)
            result = run_contract_tests(args.output_root)
    except StrategyT1Error as exc:
        print(json.dumps({"ok": False, "status": "BLOCKED", "error": str(exc)}, ensure_ascii=False, indent=2))
        return 2
    print(json.dumps({"ok": True, "result": result}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
