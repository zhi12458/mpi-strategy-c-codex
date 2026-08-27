#!/usr/bin/env python3
"""Lightweight T1.1.2 semantic-restructuring contract.
The model proposes only selected Chinese syntax edits.  The runner hydrates
all frozen hashes and source-analysis evidence bindings before this validator
accepts the final artifact.  The checks below are deliberately mechanical;
they do not claim to prove doctrinal equivalence, completeness, title quality,
or English fluency.  Those remain responsibilities of the existing bilingual
reviews and the full Chinese recheck.
"""
from __future__ import annotations
import argparse
import copy
import hashlib
import json
import re
import tempfile
import unicodedata
from collections import Counter
from pathlib import Path
from typing import Any
import semantic_bridge_legacy
from t1_runtime import StrategyT1Error, atomic_json, sha256_file, utc_now
WORKFLOW_VERSION = "1.1.2"
SCHEMA_VERSION = 3
ARTIFACT_NAME = "semantic-restructuring.json"
ANALYSIS_NAME = "source-analysis.json"
TERM_MAP_NAME = "term-map.yaml"
PROJECT_NAME = "translation-project.yaml"
# Historical names remain importable; validation is delegated read-only.
RISK_NAME = semantic_bridge_legacy.RISK_NAME
BRIDGE_NAME = semantic_bridge_legacy.BRIDGE_NAME
REVIEW_NAME = semantic_bridge_legacy.REVIEW_NAME
DECISIONS_NAME = semantic_bridge_legacy.DECISIONS_NAME
COVERAGE_NAME = semantic_bridge_legacy.COVERAGE_NAME
REGRESSION_NAME = semantic_bridge_legacy.REGRESSION_NAME
OPERATIONS = set("explicit_subject explicit_reference explicit_logic split_sentence reorder parallelism passive_or_impersonal preserve_ambiguity".split())
SUBJECT_MODES = set("explicit_source_subject contextual_subject passive impersonal retained_ambiguity not_applicable".split())
EVIDENCE_STATUSES = set("explicit contextual_inference ambiguous not_applicable".split())
EVIDENCE_KINDS = {"subject", "reference", "logic", "structure"}
TYPED_CHANGE_OPERATIONS = set("explicit_subject explicit_reference explicit_logic parallelism".split())
LOGIC_MARKERS = set(
    "若 如果 假如 只要 除非 一旦 就 则 那么 便 才 方 "
    "因为 由于 缘于 所以 因此 因而 由此 故而 故 从而 于是 "
    "虽然 尽管 即使 但是 但 然而 不过 可是 却 反而 反之 相反 而 "
    "不仅 不但 而且 甚至 进而 继而 然后 再者 此外 同时 "
    "另一方面 并且 并 且 也".split()
)
LOGIC_PAIRS = tuple(tuple(item.split(":")) for item in "若:就 如果:就 假如:就 只要:就 除非:才 因为:所以 由于:因此 虽然:但是 尽管:但 即使:也 不仅:而且 不但:而且".split())
# Only connectors whose addition does not also manufacture a visible negation
# or limiter are eligible for source-analysis-bound insertion.  The value is
# the grammatical relation role that the exact evidence quote must assign to
# the source span immediately following the connector.
ADDITIVE_LOGIC_ROLES = {
    "则": "conditional_result",
    "因此": "causal_result",
    "但": "contrast",
    "进而": "progression",
}
STRUCTURED_RELATION_TYPES = {
    "则": {"condition"},
    "因此": {"cause", "result"},
    "但": {"contrast"},
    "进而": {"progression"},
}
EXPLICIT_SUBJECT_ROLES = {"agent", "experiencer", "causer"}
STRUCTURED_ROLES = {
    "agent", "experiencer", "patient", "theme", "beneficiary", "recipient",
    "instrument", "stimulus", "causer", "source", "goal", "location", "other",
}
LOGIC_ROLE_LABELS = {
    "conditional_result": ("条件后件", "条件关系后件", "条件结果", "条件关系结果"),
    "causal_result": ("因果结果", "因果关系结果", "由前因导致的结果", "后果"),
    "contrast": ("转折项", "转折分句", "转折", "对比项", "对比分句"),
    "progression": ("递进项", "递进分句", "递进", "加强项", "进一步内容"),
}
LOGIC_SOURCE_ROLE_LABELS = {
    "conditional_result": ("条件项", "条件分句", "条件", "前提"),
    "causal_result": ("原因项", "原因分句", "原因", "前因"),
    "contrast": ("转折前项", "对比前项"),
    "progression": ("递进前项", "基础项"),
}
LOGIC_EVIDENCE_FIELDS = {"logic_and_scope", "relations"}
PARALLEL_EVIDENCE_FIELDS = {
    "semantic_roles_and_references",
    "ellipsis_or_ambiguity",
    "references_and_ellipsis",
    "parallelism",
}
SUBJECT_EVIDENCE_FIELDS = {
    "actors_and_state_holders",
    "semantic_roles_and_references",
    "ellipsis_or_ambiguity",
    "references_and_ellipsis",
    "predicates",
    "roles",
    "subject",
    "subjects",
}
REFERENCE_EVIDENCE_FIELDS = {
    "semantic_roles_and_references",
    "ellipsis_or_ambiguity",
    "references_and_ellipsis",
    "predicates",
    "references",
    "reference",
}
STRUCTURE_EVIDENCE_FIELDS = {
    "semantic_roles_and_references",
    "ellipsis_or_ambiguity",
    "references_and_ellipsis",
    "logic_and_scope",
    "predicates",
    "relations",
    "parallelism",
    "structure",
}
EVIDENCE_FIELD_ALLOWLISTS = {
    "subject": SUBJECT_EVIDENCE_FIELDS,
    "reference": REFERENCE_EVIDENCE_FIELDS,
    "logic": LOGIC_EVIDENCE_FIELDS,
    "structure": STRUCTURE_EVIDENCE_FIELDS,
}
INDEXED_EVIDENCE_PATH_RE = re.compile(
    r"^(?:(relations|references_and_ellipsis)\[(0|[1-9][0-9]*)\]"
    r"|predicates\[(0|[1-9][0-9]*)\]\.participants\[(0|[1-9][0-9]*)\])$"
)
STRUCTURED_PARAGRAPH_FIELDS = {
    "predicates", "relations", "operators", "references_and_ellipsis",
    "competing_interpretations", "must_preserve", "must_not_invent", "status",
}
STRUCTURED_SIGNATURE_FIELDS = {
    "predicates", "relations", "operators", "references_and_ellipsis",
    "competing_interpretations",
}
LEGACY_SIGNATURE_SCALAR_FIELDS = {
    "predicates", "relations", "references_and_ellipsis",
}
LEGACY_TOP_LEVEL_EVIDENCE_FIELDS = (
    set().union(*EVIDENCE_FIELD_ALLOWLISTS.values()) - STRUCTURED_PARAGRAPH_FIELDS
)
AUTHORIZATION_BLOCKERS = (
    "不成立", "错误", "误判", "误认为", "并无此意", "不适用",
    "未明确", "不明确", "不确定", "尚未明确", "尚不明确",
    "无法确定", "不能确定", "未必", "不一定", "可能", "也可能",
    "或许", "也许", "大概", "似乎", "看似", "疑似", "据称",
    "据说", "待确认", "需确认",
    "尚待", "有待", "待讨论", "待定", "待考", "是否", "之一",
    "候选", "还是", "抑或", "或者", "或", "/", "？", "?", "吗",
    "存在歧义", "有歧义",
)
AUTHORIZATION_BLOCKER_PATTERNS = (
    re.compile(r"(?:^|[，,；;。.!！？?:：\n])(?:若|如果|假如|假设)"),
)
NEGATION_MARKERS = set("并非 不是 不可 不能 不应 不得 无需 未曾 没有 无 未 非 不 没 莫 勿".split())
LIMITER_MARKERS = set("只 仅 唯 都 皆 各 每 所有 任何 一定 必须 应 应当 可以 可 可能 才 未必".split())
REFERENCE_FORMS = set("这 那 此 其 他 她 它 他们 她们 它们 这些 那些 此处 这里 那里 其中 前者 后者 该".split())
CORE_BUDDHIST_TERMS = {"空", "无自性", "缘起", "受", "心", "心所", "能缘", "所缘"}
LOCKED_PROVENANCE = {
    "provider": "openai-codex",
    "model": "gpt-5.6-sol",
    "reasoning_effort": "high",
    "role": "translation_and_self_review",
}
_UNSPECIFIED = object()
TOP_FIELDS = set("schema_version workflow_version stage source_sha256 translation_project_sha256 source_analysis_sha256 term_map_sha256 accepted_decisions_sha256 source_nonblank_units selected_line_count generated_by records".split())
FINAL_RECORD_FIELDS = set("paragraph_id source_line source_line_sha256 source_excerpt source_analysis_record_sha256 source_analysis_fields_used analysis_evidence restructured_zh restructuring_operations sentence_units_zh subject_strategy typed_changes protected_terms".split())
PROPOSAL_RECORD_FIELDS = FINAL_RECORD_FIELDS - set("source_line source_line_sha256 source_excerpt source_analysis_record_sha256 source_analysis_fields_used protected_terms".split())
EVIDENCE_FIELDS = set("kind source_analysis_field source_analysis_value_sha256 exact_quote".split())
PROPOSAL_EVIDENCE_FIELDS = EVIDENCE_FIELDS - {"source_analysis_value_sha256"}
SUBJECT_FIELDS = set("mode evidence_status subject_zh antecedent_zh evidence_index".split())
TYPED_CHANGE_FIELDS = set("change operation source_zh restructured_zh evidence_status basis_zh evidence_index".split())
CJK_RE = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff]")
DIGIT_RE = re.compile(r"[0-9０-９]+(?:[.,，．][0-9０-９]+)*")
LATIN_RE = re.compile(r"[A-Za-z\u00c0-\u024f]+(?:[-'’][A-Za-z\u00c0-\u024f]+)*")
SANSKRIT_RE = re.compile(r"[\u0900-\u097f]+")
URL_RE = re.compile(r"(?:https?|ftp)://[^\s<>\"'）】]+")
LINE_ID_RE = re.compile(r"^L0*([1-9][0-9]*)$")
QUOTE_CHARS = set("“”‘’「」『』《》\"'")
QUESTION_EMPHASIS_CHARS = set("？?!！")
BRACKET_CHARS = set("（）()【】[]{}")
MARKUP_CHARS = set("#*_~`")
CLAUSE_RE = re.compile(r"[^，,；;。！？!?：:\n]+[，,；;。！？!?：:]?")
def canonical_hash(value: Any) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()
def canonical_value_hash(value: Any) -> str:
    return canonical_hash(value)
def line_hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()
def canonical_line_id(value: str) -> str:
    match = LINE_ID_RE.fullmatch(value)
    if not match:
        raise StrategyT1Error(f"invalid source paragraph_id: {value!r}")
    return f"L{int(match.group(1))}"
def load_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise StrategyT1Error(f"required T1.1.2 input is missing: {path.name}")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise StrategyT1Error(f"invalid UTF-8 JSON: {path.name}") from exc
    if not isinstance(value, dict):
        raise StrategyT1Error(f"JSON root must be an object: {path.name}")
    return value
def _exact_fields(value: dict[str, Any], expected: set[str], where: str) -> None:
    if set(value) != expected:
        extra = sorted(set(value) - expected)
        missing = sorted(expected - set(value))
        raise StrategyT1Error(
            f"{where} has unapproved fields; missing={missing}, extra={extra}"
        )
def _text(value: Any, where: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise StrategyT1Error(f"{where} must be a nonempty string")
    return value
def _nullable_text(value: Any, where: str) -> str | None:
    if value is None:
        return None
    return _text(value, where)
def _hash_or_none(value: Any, where: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str) or re.fullmatch(r"[0-9a-f]{64}", value) is None:
        raise StrategyT1Error(f"{where} must be null or a lowercase SHA-256")
    return value
def source_index(source: Path) -> tuple[str, list[dict[str, Any]], dict[str, dict[str, Any]]]:
    if not source.is_file():
        raise StrategyT1Error("source.dj is missing")
    rows: list[dict[str, Any]] = []
    by_id: dict[str, dict[str, Any]] = {}
    for number, text in enumerate(source.read_text(encoding="utf-8").splitlines(), 1):
        if not text.strip():
            continue
        row = {"id": f"L{number}", "line": number, "text": text, "sha256": line_hash(text)}
        rows.append(row)
        by_id[row["id"]] = row
    if not rows:
        raise StrategyT1Error("source.dj has no nonblank lines")
    return sha256_file(source), rows, by_id
def analysis_value_text(value: Any) -> str:
    if isinstance(value, str):
        return value
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
def analysis_scalar_strings(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        return [text for item in value for text in analysis_scalar_strings(item)]
    if isinstance(value, dict):
        return [text for item in value.values() for text in analysis_scalar_strings(item)]
    return []
def _analysis_field_root(field: str) -> str:
    return field.split("[", 1)[0]
def _analysis_record_mode(analysis: dict[str, Any]) -> str:
    present = STRUCTURED_SIGNATURE_FIELDS & set(analysis)
    if not present:
        return "legacy_prose"
    if all(
        field in LEGACY_SIGNATURE_SCALAR_FIELDS
        and isinstance(analysis[field], str)
        and analysis[field].strip()
        for field in present
    ):
        return "legacy_prose"
    return "locked_structured"
def _resolve_analysis_value(
    analysis: dict[str, Any], field: str, where: str
) -> tuple[str, Any, bool]:
    """Resolve a legacy top-level scalar or one locked Stage-4 object path."""
    mode = _analysis_record_mode(analysis)
    if field in analysis and "[" not in field:
        if mode == "locked_structured":
            raise StrategyT1Error(
                f"{where} must bind locked structured evidence by its exact indexed path; "
                "top-level legacy evidence is not permitted"
            )
        value = analysis[field]
        if not isinstance(value, str) or not value.strip():
            raise StrategyT1Error(
                f"{where} legacy evidence must bind one complete nonempty "
                "top-level string scalar"
            )
        return field, value, False
    match = INDEXED_EVIDENCE_PATH_RE.fullmatch(field)
    if match is None:
        raise StrategyT1Error(
            f"{where} has an unsupported source-analysis field path {field!r}"
        )
    if mode != "locked_structured":
        raise StrategyT1Error(
            f"{where} cannot use an indexed path with a legacy prose analysis record"
        )
    relation_root, relation_index, predicate_index, participant_index = match.groups()
    try:
        if relation_root:
            values = analysis[relation_root]
            if not isinstance(values, list):
                raise KeyError(relation_root)
            value = values[int(relation_index)]
            if not isinstance(value, dict):
                raise KeyError(relation_root)
            return relation_root, value, True
        predicates = analysis["predicates"]
        if not isinstance(predicates, list):
            raise KeyError("predicates")
        predicate = predicates[int(predicate_index)]
        if not isinstance(predicate, dict) or not isinstance(predicate.get("participants"), list):
            raise KeyError("participants")
        value = predicate["participants"][int(participant_index)]
        if not isinstance(value, dict):
            raise KeyError("participants")
        return "predicates", value, True
    except (KeyError, IndexError, TypeError, ValueError):
        raise StrategyT1Error(
            f"{where} references an absent source-analysis field path {field!r}"
        ) from None
def _structured_expected_kind(root: str, value: dict[str, Any], where: str) -> str:
    if root == "predicates":
        return "subject"
    if root == "relations":
        return "logic"
    item_kind = value.get("kind")
    if item_kind in {"omitted_subject", "inherited_subject"}:
        return "subject"
    if item_kind in {"coreference", "ambiguous_reference"}:
        return "reference"
    if item_kind in {"omitted_object", "other"}:
        return "structure"
    raise StrategyT1Error(f"{where} has an unsupported structured reference kind")
def _validate_structured_evidence(
    kind: str,
    root: str,
    value: dict[str, Any],
    quote: str,
    where: str,
) -> None:
    expected = _structured_expected_kind(root, value, where)
    if kind != expected:
        raise StrategyT1Error(
            f"{where} kind={kind} cannot relabel the indexed {expected} evidence item"
        )
    if not isinstance(value.get("evidence"), str) or value["evidence"] != quote:
        raise StrategyT1Error(
            f"{where}.exact_quote must equal the indexed item's non-null evidence scalar; notes never authorize restructuring"
        )
def _validate_evidence_field(kind: str, field: str, where: str) -> None:
    root = _analysis_field_root(field)
    if root not in EVIDENCE_FIELD_ALLOWLISTS[kind]:
        raise StrategyT1Error(
            f"{where} kind={kind} cannot be authorized by source-analysis.{field}"
        )
def analysis_index(
    path: Path,
    *,
    source_sha256: str,
    source_rows: list[dict[str, Any]],
    project_sha256: str,
    term_map_sha256: str,
) -> tuple[str, dict[str, dict[str, Any]], dict[str, str], str, str]:
    root = load_json(path)
    if root.get("source_sha256") != source_sha256:
        raise StrategyT1Error("source-analysis.json source_sha256 is stale")
    for key in ("translation_project_sha256", "project_sha256"):
        if key in root and root[key] != project_sha256:
            raise StrategyT1Error(f"source-analysis.json {key} is stale")
    if "term_map_sha256" in root and root["term_map_sha256"] != term_map_sha256:
        raise StrategyT1Error("source-analysis.json term_map_sha256 is stale")
    paragraphs = root.get("paragraphs")
    if not isinstance(paragraphs, list):
        raise StrategyT1Error("source-analysis.json requires a paragraphs array")
    records: dict[str, dict[str, Any]] = {}
    original_ids: dict[str, str] = {}
    ordered_ids: list[str] = []
    line_hash_presence: list[bool] = []
    record_modes: set[str] = set()
    for index, record in enumerate(paragraphs):
        if not isinstance(record, dict):
            raise StrategyT1Error(f"source-analysis paragraph {index} must be an object")
        raw_id = _text(record.get("paragraph_id"), f"source-analysis paragraph {index}.paragraph_id")
        pid = canonical_line_id(raw_id)
        if pid in records:
            raise StrategyT1Error(f"duplicate source-analysis paragraph_id: {raw_id}")
        has_line_hash = "line_sha256" in record
        if has_line_hash and not isinstance(record["line_sha256"], str):
            raise StrategyT1Error(f"source-analysis {raw_id} has invalid line_sha256")
        line_hash_presence.append(has_line_hash)
        record_mode = _analysis_record_mode(record)
        if record_mode == "locked_structured":
            missing_structured = sorted(STRUCTURED_PARAGRAPH_FIELDS - set(record))
            non_list_structured = sorted(
                field for field in STRUCTURED_SIGNATURE_FIELDS
                if not isinstance(record.get(field), list)
            )
            legacy_evidence_fields = sorted(
                LEGACY_TOP_LEVEL_EVIDENCE_FIELDS & set(record)
            )
            if missing_structured or non_list_structured or legacy_evidence_fields:
                raise StrategyT1Error(
                    f"source-analysis {raw_id} has a partial locked structured record; "
                    f"missing={missing_structured}, non_list={non_list_structured}, "
                    f"legacy_evidence_fields={legacy_evidence_fields}; locked structured "
                    "and legacy evidence cannot mix"
                )
            record_modes.add(record_mode)
        else:
            record_modes.add(record_mode)
        records[pid] = record
        original_ids[pid] = raw_id
        ordered_ids.append(pid)
    expected_ids = [row["id"] for row in source_rows]
    if ordered_ids != expected_ids:
        raise StrategyT1Error(
            "source-analysis paragraphs must cover every nonblank source line in source order"
        )
    for row in source_rows:
        if "line_sha256" in records[row["id"]] and records[row["id"]]["line_sha256"] != row["sha256"]:
            raise StrategyT1Error(f"source-analysis line_sha256 mismatch for {original_ids[row['id']]}")
    if all(line_hash_presence):
        mode = "paragraph_line_sha256_verified"
    elif any(line_hash_presence):
        mode = "mixed_verified_and_derived"
    else:
        mode = "derived_from_frozen_source_and_order"
    if len(record_modes) != 1:
        raise StrategyT1Error(
            "source-analysis paragraphs cannot mix locked structured and legacy prose records"
        )
    return sha256_file(path), records, original_ids, mode, next(iter(record_modes))
def _restricted_yaml_terms(text: str) -> Any:
    """Tiny test-only parser for standard ``terms:`` list-of-maps.
    Production YAML always requires PyYAML.  This fallback is deliberately too
    small to accept project term maps silently when that dependency is absent.
    """
    lines = [line.rstrip() for line in text.splitlines() if line.strip() and not line.lstrip().startswith("#")]
    if not lines or lines[0].strip() != "terms:":
        raise StrategyT1Error("PyYAML is required for the project term-map.yaml")
    terms: list[dict[str, str]] = []
    current: dict[str, str] | None = None
    for line in lines[1:]:
        match = re.fullmatch(r"\s*-\s+source:\s*([^#]+?)\s*", line)
        if match:
            if current:
                terms.append(current)
            current = {"source": match.group(1).strip(" \"'")}
            continue
        match = re.fullmatch(r"\s+([A-Za-z_][A-Za-z0-9_]*):\s*([^#]+?)\s*", line)
        if match and current is not None:
            current[match.group(1)] = match.group(2).strip(" \"'")
            continue
        raise StrategyT1Error("restricted term-map fallback rejected unsupported YAML")
    if current:
        terms.append(current)
    if not terms:
        raise StrategyT1Error("restricted term-map fallback found no terms")
    return {"terms": terms}
def _term_map_value(text: str, *, allow_restricted_fallback: bool = False) -> Any:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    try:
        import yaml
    except ImportError as exc:
        if allow_restricted_fallback:
            return _restricted_yaml_terms(text)
        raise StrategyT1Error(
            "T1.1.2 semantic restructuring requires Python PyYAML for term-map.yaml"
        ) from exc
    try:
        value = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        raise StrategyT1Error("term-map.yaml is not valid safe YAML") from exc
    if value is None:
        raise StrategyT1Error("term-map.yaml is empty")
    return value
def term_map_keys(text: str, *, allow_restricted_fallback: bool = False) -> set[str]:
    value = _term_map_value(text, allow_restricted_fallback=allow_restricted_fallback)
    found: set[str] = set()
    metadata = {
        "schema_version", "strategy", "version", "evidence_version", "source_authority",
        "preferred", "preferred_buddhist", "alternate_general", "alternates_by_context",
        "note", "notes", "authority_refs", "source_lines", "mode", "rejected",
        "variants_by_source_line", "target", "translation", "english",
    }
    def walk(item: Any) -> None:
        if isinstance(item, list):
            for child in item:
                walk(child)
            return
        if not isinstance(item, dict):
            return
        source = item.get("source")
        if isinstance(source, str) and CJK_RE.search(source):
            found.add(source.strip())
        for key, child in item.items():
            if key == "rejected":
                continue
            if isinstance(key, str) and key not in metadata and CJK_RE.search(key):
                found.add(key.strip())
            walk(child)
    walk(value)
    if not found:
        raise StrategyT1Error("term-map.yaml contains no recognizable Chinese source terms")
    return found
def required_protected_terms(source_line: str, term_keys: set[str]) -> list[str]:
    required = {term for term in term_keys | CORE_BUDDHIST_TERMS if term and term in source_line}
    return sorted(required, key=lambda term: (source_line.find(term), -len(term), term))
def project_context(project: Path) -> dict[str, Any]:
    project = project.expanduser().resolve()
    if not project.is_dir():
        raise StrategyT1Error(f"T1 project directory is missing: {project}")
    source = project / "source.dj"
    metadata = project / PROJECT_NAME
    analysis = project / ANALYSIS_NAME
    term_map = project / TERM_MAP_NAME
    for path in (metadata, analysis, term_map):
        if not path.is_file():
            raise StrategyT1Error(f"required T1.1.2 input is missing: {path.name}")
    source_sha, rows, rows_by_id = source_index(source)
    project_sha = sha256_file(metadata)
    term_sha = sha256_file(term_map)
    (
        analysis_sha,
        analyses,
        analysis_ids,
        analysis_line_hash_mode,
        analysis_schema_mode,
    ) = analysis_index(
        analysis,
        source_sha256=source_sha,
        source_rows=rows,
        project_sha256=project_sha,
        term_map_sha256=term_sha,
    )
    terms = term_map_keys(term_map.read_text(encoding="utf-8"))
    return {
        "project": project,
        "source_path": source,
        "source_text": source.read_text(encoding="utf-8"),
        "source_sha256": source_sha,
        "source_rows": rows,
        "source_rows_by_id": rows_by_id,
        "translation_project_sha256": project_sha,
        "source_analysis_sha256": analysis_sha,
        "analysis_records": analyses,
        "analysis_original_ids": analysis_ids,
        "analysis_line_hash_mode": analysis_line_hash_mode,
        "analysis_schema_mode": analysis_schema_mode,
        "term_map_sha256": term_sha,
        "term_keys": terms,
    }
def _nullable_string_schema() -> dict[str, Any]:
    return {"type": ["string", "null"]}
def proposal_json_schema(_context: dict[str, Any] | None = None) -> dict[str, Any]:
    evidence = {
        "type": "object",
        "additionalProperties": False,
        "required": sorted(PROPOSAL_EVIDENCE_FIELDS),
        "properties": {
            "kind": {"enum": sorted(EVIDENCE_KINDS)},
            "source_analysis_field": {"type": "string", "minLength": 1},
            "exact_quote": {"type": "string", "minLength": 1},
        },
    }
    subject = {
        "type": "object",
        "additionalProperties": False,
        "required": sorted(SUBJECT_FIELDS),
        "properties": {
            "mode": {"enum": sorted(SUBJECT_MODES)},
            "evidence_status": {"enum": sorted(EVIDENCE_STATUSES)},
            "subject_zh": _nullable_string_schema(),
            "antecedent_zh": _nullable_string_schema(),
            "evidence_index": {"type": ["integer", "null"], "minimum": 0},
        },
    }
    typed_change = {
        "type": "object",
        "additionalProperties": False,
        "required": sorted(TYPED_CHANGE_FIELDS),
        "properties": {
            "change": {"enum": ["addition", "replacement"]},
            "operation": {"enum": sorted(TYPED_CHANGE_OPERATIONS)},
            "source_zh": _nullable_string_schema(),
            "restructured_zh": {"type": "string", "minLength": 1},
            "evidence_status": {"enum": ["explicit", "contextual_inference"]},
            "basis_zh": _nullable_string_schema(),
            "evidence_index": {"type": "integer", "minimum": 0},
        },
        "allOf": [
            {
                "if": {
                    "properties": {"operation": {"const": "explicit_reference"}},
                    "required": ["operation"],
                },
                "then": {
                    "properties": {
                        "change": {"const": "replacement"},
                        "source_zh": {"enum": sorted(REFERENCE_FORMS)},
                    }
                },
            },
            {
                "if": {
                    "properties": {"operation": {"const": "explicit_logic"}},
                    "required": ["operation"],
                },
                "then": {
                    "properties": {
                        "change": {"const": "addition"},
                        "source_zh": {"type": "null"},
                        "restructured_zh": {"enum": sorted(ADDITIVE_LOGIC_ROLES)},
                    }
                },
            },
            {
                "if": {
                    "properties": {"operation": {"const": "parallelism"}},
                    "required": ["operation"],
                },
                "then": {
                    "properties": {
                        "change": {"const": "addition"},
                        "source_zh": {"type": "null"},
                    }
                },
            },
        ],
    }
    record = {
        "type": "object",
        "additionalProperties": False,
        "required": sorted(PROPOSAL_RECORD_FIELDS),
        "properties": {
            "paragraph_id": {"type": "string", "pattern": "^L0*[1-9][0-9]*$"},
            "analysis_evidence": {"type": "array", "minItems": 1, "items": evidence},
            "restructured_zh": {"type": "string", "minLength": 1},
            "restructuring_operations": {
                "type": "array", "minItems": 1, "uniqueItems": True,
                "items": {"enum": sorted(OPERATIONS)},
            },
            "sentence_units_zh": {
                "type": "array", "minItems": 1,
                "items": {"type": "string", "minLength": 1},
            },
            "subject_strategy": subject,
            "typed_changes": {"type": "array", "items": typed_change},
        },
    }
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "type": "object",
        "additionalProperties": False,
        "required": ["records"],
        "properties": {"records": {"type": "array", "minItems": 1, "items": record}},
    }
def artifact_json_schema(_context: dict[str, Any] | None = None) -> dict[str, Any]:
    """Return a compact description of runner-hydrated final fields."""
    return {
        "schema_version": SCHEMA_VERSION,
        "workflow_version": WORKFLOW_VERSION,
        "top_level_fields": sorted(TOP_FIELDS),
        "record_fields": sorted(FINAL_RECORD_FIELDS),
        "runner_added_record_fields": sorted(FINAL_RECORD_FIELDS - PROPOSAL_RECORD_FIELDS),
        "evidence_fields": sorted(EVIDENCE_FIELDS),
    }
def prompt_contract(project: Path) -> dict[str, Any]:
    # Load all inputs now so a stale analysis or unavailable YAML dependency
    # blocks before any external model call.  No source text or hashes are
    # copied into the prompt contract.
    context = project_context(project)
    return {
        "contract": "T1.1.2 lightweight semantic-restructuring proposal",
        "workflow_version": WORKFLOW_VERSION,
        "analysis_schema_mode": context["analysis_schema_mode"],
        "legacy_evidence_fields_by_kind": {
            kind: sorted(fields)
            for kind, fields in EVIDENCE_FIELD_ALLOWLISTS.items()
        } if context["analysis_schema_mode"] == "legacy_prose" else {},
        "proposal_json_schema": proposal_json_schema(),
        "runner_hydration": [
            "The runner adds all four frozen input hashes, provenance, counts, source line/excerpt/hash, analysis record/value hashes, and protected terms.",
            "Do not return hashes, source excerpts, provenance, aggregate counts, or unselected-line decisions.",
        ],
        "rules": [
            "Consider every nonblank source line; return only materially restructured selected records in source order.",
            "source.dj is the sole semantic authority; reuse source-analysis and do not interpret doctrine again.",
            "Use only approved operations. For locked structured analysis, source_analysis_field must be an exact indexed path predicates[i].participants[j], relations[i], or references_and_ellipsis[i], and exact_quote must equal that item's non-null evidence scalar; notes never authorize restructuring and the runner hashes the whole item. A list-valued or malformed/non-legacy locked signature cannot fall back to a legacy field. Genuine legacy prose evidence uses one complete nonempty top-level string scalar, including any allowed overlapping legacy name. Never crop a favorable substring.",
            "Honor analysis_schema_mode. In legacy_prose mode, every evidence item must use a source_analysis_field listed for its exact kind in legacy_evidence_fields_by_kind; semantic_head, must_preserve, must_not_invent, doctrinal_and_cultural_terms, quotations_allusions_fixed_expressions, and notes never authorize restructuring.",
            "An explicit source subject may bind an indexed explicit agent/experiencer/causer participant. A contextual subject insertion must return two indexed evidence entries: one omitted/inherited-subject references_and_ellipsis[i] item with one referent/candidate, exact context evidence, and an exact current-line predicate anchor, plus one predicates[p].participants[q] item with the same predicate, role, contextual status, and its own exact evidence. The participant is normally null for a locked omitted subject; both referent and sole candidate must equal subject_zh.",
            "subject_strategy may bind only subject or reference evidence. For a record selected only for structure or logic and with no valid subject/reference evidence, use mode=not_applicable, evidence_status=not_applicable, null subject_zh, antecedent_zh, and evidence_index; never bind subject_strategy to structure or logic evidence.",
            "If no unique subject is established, use passive_or_impersonal or preserve_ambiguity and do not add a subject.",
            "Record every CJK lexical addition or replacement as a typed change; split/reorder alone cannot rewrite words.",
            "Use reorder only to move whole source clauses exactly as delimited by Chinese sentence or clause punctuation; never reorder words, phrases, quotation fragments, or partial clauses within a punctuation-bound clause. If that cannot express the change, use punctuation and split_sentence only when sufficient, or omit the record and defer it to English translation and bilingual review.",
            "A structured overt-reference replacement must bind one indexed coreference item whose expression, unique referent, evidence status, and exact evidence match. Every reference replacement requires one unique maximal controlled overt form and replaces it once in place; legacy prose reference edits also need a local positive complete-scalar quote.",
            "Use explicit_reference only to replace an overt controlled reference form. A zero subject must use contextual_subject plus explicit_subject; other zero-reference additions are deferred to bilingual translation review.",
            "A new connector is limited to condition→则, cause/result→因此, contrast→但, progression→进而 and must prefix one complete later source clause. Locked structured analysis must bind the sole non-ambiguous relations[i] item whose exact unique adjacent source_clause, target_clause, continuous source evidence, and status match, in a clear paragraph with no competing interpretation, same-pair conflict, or existing target-clause logic marker. Legacy prose may authorize only through the closed affirmative complete-scalar template with no extra text.",
            "The locked structured Stage-4 schema does not encode both a shared parallel constituent and its insertion position, so it cannot authorize lexical parallel completion; use punctuation/splitting or defer to English translation and bilingual review. Legacy prose may authorize the narrowly closed complete-scalar template only.",
            "Do not add explanations, examples, glosses, background, conclusions, or doctrinal interpretations.",
            "Preserve terms, negation, digits, Latin/Sanskrit/URL tokens, logic direction, questions, emphasis, quotations, and markup.",
            "sentence_units_zh must concatenate to restructured_zh after whitespace removal.",
            "The 90%-115% CJK length band is a warning only.",
        ],
        "mechanical_scope": {
            "proves": "frozen-input binding and listed surface invariants only",
            "does_not_prove": "no doctrinal drift, no proposition omission, title accuracy, English fluency, or model attention to unselected lines",
            "semantic_gates": "existing two independent bilingual reviews and post-concision full Chinese recheck",
        },
    }
def _evidence_from_proposal(item: Any, analysis: dict[str, Any], where: str) -> dict[str, Any]:
    if not isinstance(item, dict):
        raise StrategyT1Error(f"{where} must be an object")
    _exact_fields(item, PROPOSAL_EVIDENCE_FIELDS, where)
    kind = item.get("kind")
    if kind not in EVIDENCE_KINDS:
        raise StrategyT1Error(f"{where}.kind is invalid")
    field = _text(item.get("source_analysis_field"), f"{where}.source_analysis_field")
    if _analysis_field_root(field) in {"paragraph_id", "line_sha256"}:
        raise StrategyT1Error(f"{where} references a non-evidence source-analysis field")
    root, bound_value, structured = _resolve_analysis_value(analysis, field, where)
    _validate_evidence_field(kind, field, where)
    quote = _text(item.get("exact_quote"), f"{where}.exact_quote")
    if quote not in analysis_scalar_strings(bound_value):
        raise StrategyT1Error(
            f"{where}.exact_quote is not verbatim as one complete frozen scalar in source-analysis.{field}"
        )
    if structured:
        _validate_structured_evidence(kind, root, bound_value, quote, where)
    return {
        "kind": kind,
        "source_analysis_field": field,
        "source_analysis_value_sha256": canonical_value_hash(bound_value),
        "exact_quote": quote,
    }
def _validate_subject_shape(item: Any, where: str) -> dict[str, Any]:
    if not isinstance(item, dict):
        raise StrategyT1Error(f"{where} must be an object")
    _exact_fields(item, SUBJECT_FIELDS, where)
    if item.get("mode") not in SUBJECT_MODES:
        raise StrategyT1Error(f"{where}.mode is invalid")
    if item.get("evidence_status") not in EVIDENCE_STATUSES:
        raise StrategyT1Error(f"{where}.evidence_status is invalid")
    _nullable_text(item.get("subject_zh"), f"{where}.subject_zh")
    _nullable_text(item.get("antecedent_zh"), f"{where}.antecedent_zh")
    index = item.get("evidence_index")
    if index is not None and (not isinstance(index, int) or isinstance(index, bool) or index < 0):
        raise StrategyT1Error(f"{where}.evidence_index must be null or a nonnegative integer")
    return copy.deepcopy(item)
def _validate_typed_change_shape(item: Any, where: str) -> dict[str, Any]:
    if not isinstance(item, dict):
        raise StrategyT1Error(f"{where} must be an object")
    _exact_fields(item, TYPED_CHANGE_FIELDS, where)
    if item.get("change") not in {"addition", "replacement"}:
        raise StrategyT1Error(f"{where}.change is invalid")
    if item.get("operation") not in TYPED_CHANGE_OPERATIONS:
        raise StrategyT1Error(f"{where}.operation is invalid")
    _nullable_text(item.get("source_zh"), f"{where}.source_zh")
    _text(item.get("restructured_zh"), f"{where}.restructured_zh")
    if item.get("evidence_status") not in {"explicit", "contextual_inference"}:
        raise StrategyT1Error(f"{where}.evidence_status is invalid")
    _nullable_text(item.get("basis_zh"), f"{where}.basis_zh")
    index = item.get("evidence_index")
    if not isinstance(index, int) or isinstance(index, bool) or index < 0:
        raise StrategyT1Error(f"{where}.evidence_index must be a nonnegative integer")
    return copy.deepcopy(item)
def _provenance(value: dict[str, Any] | None) -> dict[str, str]:
    result = copy.deepcopy(value or LOCKED_PROVENANCE)
    if set(result) != set(LOCKED_PROVENANCE) or result != LOCKED_PROVENANCE:
        raise StrategyT1Error("semantic restructuring must use the locked Sol/high translation role")
    return result
def hydrate_proposal(
    project: Path,
    proposal: dict[str, Any],
    provenance: dict[str, Any] | None = None,
    accepted_decisions_sha256: str | None = None,
) -> dict[str, Any]:
    context = project_context(project)
    if not isinstance(proposal, dict):
        raise StrategyT1Error("semantic restructuring proposal must be an object")
    _exact_fields(proposal, {"records"}, "proposal")
    records = proposal.get("records")
    if not isinstance(records, list) or not records:
        raise StrategyT1Error("an explicit T1.1.2 pilot requires at least one selected record")
    decisions_hash = _hash_or_none(accepted_decisions_sha256, "accepted_decisions_sha256")
    hydrated: list[dict[str, Any]] = []
    selected_ids: list[str] = []
    for index, item in enumerate(records):
        where = f"proposal.records[{index}]"
        if not isinstance(item, dict):
            raise StrategyT1Error(f"{where} must be an object")
        _exact_fields(item, PROPOSAL_RECORD_FIELDS, where)
        raw_id = _text(item.get("paragraph_id"), f"{where}.paragraph_id")
        pid = canonical_line_id(raw_id)
        if pid not in context["analysis_records"]:
            raise StrategyT1Error(f"{where} references unknown source line {raw_id}")
        if pid in selected_ids:
            raise StrategyT1Error(f"duplicate selected source line: {raw_id}")
        selected_ids.append(pid)
        analysis = context["analysis_records"][pid]
        evidence_raw = item.get("analysis_evidence")
        if not isinstance(evidence_raw, list) or not evidence_raw:
            raise StrategyT1Error(f"{where}.analysis_evidence must be nonempty")
        evidence = [
            _evidence_from_proposal(value, analysis, f"{where}.analysis_evidence[{i}]")
            for i, value in enumerate(evidence_raw)
        ]
        fields_used = list(dict.fromkeys(value["source_analysis_field"] for value in evidence))
        operations = item.get("restructuring_operations")
        if (
            not isinstance(operations, list)
            or not operations
            or len(set(operations)) != len(operations)
            or any(value not in OPERATIONS for value in operations)
        ):
            raise StrategyT1Error(f"{where}.restructuring_operations is invalid")
        restructured = _text(item.get("restructured_zh"), f"{where}.restructured_zh")
        units = item.get("sentence_units_zh")
        if not isinstance(units, list) or not units or any(not isinstance(v, str) or not v.strip() for v in units):
            raise StrategyT1Error(f"{where}.sentence_units_zh must be a nonempty string array")
        subject = _validate_subject_shape(item.get("subject_strategy"), f"{where}.subject_strategy")
        changes_raw = item.get("typed_changes")
        if not isinstance(changes_raw, list):
            raise StrategyT1Error(f"{where}.typed_changes must be an array")
        changes = [
            _validate_typed_change_shape(value, f"{where}.typed_changes[{i}]")
            for i, value in enumerate(changes_raw)
        ]
        row = context["source_rows_by_id"][pid]
        hydrated.append(
            {
                "paragraph_id": context["analysis_original_ids"][pid],
                "source_line": row["line"],
                "source_line_sha256": row["sha256"],
                "source_excerpt": row["text"],
                "source_analysis_record_sha256": canonical_hash(analysis),
                "source_analysis_fields_used": fields_used,
                "analysis_evidence": evidence,
                "restructured_zh": restructured,
                "restructuring_operations": operations,
                "sentence_units_zh": copy.deepcopy(units),
                "subject_strategy": subject,
                "typed_changes": changes,
                "protected_terms": required_protected_terms(row["text"], context["term_keys"]),
            }
        )
    order = {row["id"]: index for index, row in enumerate(context["source_rows"])}
    if [order[pid] for pid in selected_ids] != sorted(order[pid] for pid in selected_ids):
        raise StrategyT1Error("selected records must be in source order")
    return {
        "schema_version": SCHEMA_VERSION,
        "workflow_version": WORKFLOW_VERSION,
        "stage": "semantic_restructuring",
        "source_sha256": context["source_sha256"],
        "translation_project_sha256": context["translation_project_sha256"],
        "source_analysis_sha256": context["source_analysis_sha256"],
        "term_map_sha256": context["term_map_sha256"],
        "accepted_decisions_sha256": decisions_hash,
        "source_nonblank_units": len(context["source_rows"]),
        "selected_line_count": len(hydrated),
        "generated_by": _provenance(provenance),
        "records": hydrated,
    }
def _normalize_space(value: str) -> str:
    return re.sub(r"\s+", "", value)
def _syntax_match_view(value: str) -> str:
    """Canonical matching view; raw text still controls hashes and output."""
    return "".join(
        char for char in value
        if not char.isspace()
        and unicodedata.category(char) not in {"Cf", "Mn", "Me"}
    )
def _evidence_list(value: Any, analysis: dict[str, Any], where: str) -> list[dict[str, Any]]:
    if not isinstance(value, list) or not value:
        raise StrategyT1Error(f"{where} must be a nonempty array")
    result: list[dict[str, Any]] = []
    for index, item in enumerate(value):
        item_where = f"{where}[{index}]"
        if not isinstance(item, dict):
            raise StrategyT1Error(f"{item_where} must be an object")
        _exact_fields(item, EVIDENCE_FIELDS, item_where)
        field = _text(item.get("source_analysis_field"), f"{item_where}.source_analysis_field")
        if _analysis_field_root(field) in {"paragraph_id", "line_sha256"}:
            raise StrategyT1Error(f"{item_where} references a non-evidence source-analysis field")
        root, bound_value, structured = _resolve_analysis_value(analysis, field, item_where)
        kind = item.get("kind")
        if kind not in EVIDENCE_KINDS:
            raise StrategyT1Error(f"{item_where}.kind is invalid")
        _validate_evidence_field(kind, field, item_where)
        if item.get("source_analysis_value_sha256") != canonical_value_hash(bound_value):
            raise StrategyT1Error(f"{item_where} source-analysis value hash mismatch")
        quote = _text(item.get("exact_quote"), f"{item_where}.exact_quote")
        if quote not in analysis_scalar_strings(bound_value):
            raise StrategyT1Error(
                f"{item_where}.exact_quote is not verbatim as one complete frozen scalar in source-analysis.{field}"
            )
        if structured:
            _validate_structured_evidence(kind, root, bound_value, quote, item_where)
        validated = copy.deepcopy(item)
        if structured:
            validated["_source_analysis_root"] = root
            validated["_source_analysis_value"] = copy.deepcopy(bound_value)
            validated["_source_analysis_parent"] = copy.deepcopy(analysis)
        result.append(validated)
    return result
def _upstream_text(context: dict[str, Any], line_number: int) -> str:
    return "\n".join(row["text"] for row in context["source_rows"] if row["line"] < line_number)
def _evidence_at(evidence: list[dict[str, Any]], index: Any, where: str) -> dict[str, Any]:
    if not isinstance(index, int) or isinstance(index, bool) or not (0 <= index < len(evidence)):
        raise StrategyT1Error(f"{where} references an absent analysis_evidence index")
    return evidence[index]
def _structured_bound(bound: dict[str, Any], root: str | None = None) -> dict[str, Any] | None:
    value = bound.get("_source_analysis_value")
    actual_root = bound.get("_source_analysis_root")
    if not isinstance(value, dict) or not isinstance(actual_root, str):
        return None
    if root is not None and actual_root != root:
        return None
    return value
def _structured_paragraph(bound: dict[str, Any]) -> dict[str, Any] | None:
    value = bound.get("_source_analysis_parent")
    return value if isinstance(value, dict) else None
def _bound_parent_predicate(bound: dict[str, Any]) -> dict[str, Any] | None:
    match = INDEXED_EVIDENCE_PATH_RE.fullmatch(
        str(bound.get("source_analysis_field", ""))
    )
    paragraph = _structured_paragraph(bound)
    if match is None or paragraph is None or match.group(3) is None:
        return None
    try:
        value = paragraph["predicates"][int(match.group(3))]
    except (KeyError, IndexError, TypeError, ValueError):
        return None
    return value if isinstance(value, dict) else None
def _local_segments(quote: str, value: str) -> list[str]:
    return [segment for segment in re.split(r"[；;。.!！？?\n]", quote) if value in segment]
def _reject_uncertain_authorization(quote: str, pid: str) -> None:
    view = _syntax_match_view(quote)
    marker = next((item for item in AUTHORIZATION_BLOCKERS if item in view), None)
    pattern = next((item.pattern for item in AUTHORIZATION_BLOCKER_PATTERNS if item.search(view)), None)
    if marker or pattern:
        raise StrategyT1Error(
            f"{pid} complete frozen evidence contains a negated, erroneous, or uncertain authorization marker: {marker or pattern}"
        )
def _positive_subject_quote(subject: str, quote: str, contextual: bool, pid: str) -> None:
    _reject_uncertain_authorization(quote, pid)
    subject_view = _syntax_match_view(subject)
    segments = _local_segments(_syntax_match_view(quote), subject_view)
    negative_roles = ("对象", "宾语", "受事", "所缘", "不是主语", "不为主语", "非主语", "不是", "不得", "不可", "不能", "不指", "并非")
    if any(any(marker in segment for marker in negative_roles) for segment in segments):
        raise StrategyT1Error(f"{pid} bound quote assigns {subject} a non-subject role")
    positive_roles = ("主语", "行动者", "施事", "主体", "观察者", "讲者", "作者", "持有者", "体验者", "说法者")
    inheritance = ("承前", "承接前文", "省略主语", "先行词", "指代", "继承", "沿用")
    if contextual:
        passed = any(any(marker in segment for marker in inheritance) for segment in segments)
    else:
        passed = any(
            any(role in segment for role in positive_roles)
            and any(link in segment for link in ("为", "是", "作为", "充当"))
            for segment in segments
        )
    if not passed:
        kind = "contextual inheritance" if contextual else "positive subject role"
        raise StrategyT1Error(f"{pid} bound quote lacks a local {kind} for {subject}")
def _positive_legacy_contextual_subject(
    subject: str, predicate: str, quote: str, pid: str
) -> None:
    _reject_uncertain_authorization(quote, pid)
    compact = _canonical_quote_text(quote)
    subject_token = re.escape(_normalize_space(subject))
    predicate_token = re.escape('"' + _normalize_space(predicate) + '"')
    patterns = (
        rf"{subject_token}(?:承接前文|承前)[，,]?(?:为|是)"
        rf"{predicate_token}(?:的)?省略主语[。.]?",
        rf"{predicate_token}(?:的)?省略主语(?:为|是)"
        rf'"{subject_token}"[，,]?(?:承接前文|承前)[。.]?',
    )
    if not any(re.fullmatch(pattern, compact) for pattern in patterns):
        raise StrategyT1Error(
            f"{pid} legacy subject evidence does not match the closed affirmative "
            "contextual-subject template"
        )
def _positive_structured_subject(
    subject: str,
    bound: dict[str, Any],
    evidence: list[dict[str, Any]],
    *,
    contextual: bool,
    antecedent: str | None,
    source: str,
    upstream: str,
    pid: str,
) -> bool:
    value = _structured_bound(bound)
    if value is None:
        return False
    root = bound["_source_analysis_root"]
    quote = bound["exact_quote"]
    paragraph = _structured_paragraph(bound)
    if paragraph is None:
        raise StrategyT1Error(f"{pid} structured subject lacks its frozen paragraph binding")
    if contextual:
        if root != "references_and_ellipsis":
            raise StrategyT1Error(
                f"{pid} contextual subject requires an indexed references_and_ellipsis item"
            )
        predicate = value.get("predicate")
        role = value.get("role")
        context = f"{upstream}\n{source}"
        candidate_referents = value.get("candidate_referents")
        same_slot_references = [
            item for item in paragraph.get("references_and_ellipsis", [])
            if isinstance(item, dict)
            and isinstance(item.get("predicate"), str)
            and isinstance(predicate, str)
            and _syntax_match_view(item["predicate"])
            == _syntax_match_view(predicate)
            and item.get("role") == role
        ]
        predicate_records = [
            item for item in paragraph.get("predicates", [])
            if isinstance(item, dict)
            and isinstance(item.get("predicate"), str)
            and isinstance(predicate, str)
            and _syntax_match_view(item["predicate"])
            == _syntax_match_view(predicate)
        ]
        role_participants = []
        if len(predicate_records) == 1 and isinstance(
            predicate_records[0].get("participants"), list
        ):
            role_participants = [
                item for item in predicate_records[0]["participants"]
                if isinstance(item, dict) and item.get("role") == role
            ]
        matching_participants = []
        for candidate in evidence:
            participant = _structured_bound(candidate, "predicates")
            parent_predicate = _bound_parent_predicate(candidate)
            if (
                participant is not None
                and parent_predicate is not None
                and (
                    participant.get("participant") is None
                    or participant.get("participant") == subject
                )
                and participant.get("role") == role
                and participant.get("evidence_status") == "contextual_inference"
                and parent_predicate.get("predicate") == predicate
                and isinstance(parent_predicate.get("evidence"), str)
                and predicate in parent_predicate["evidence"]
                and parent_predicate["evidence"] in source
                and isinstance(participant.get("evidence"), str)
                and predicate in participant["evidence"]
                and participant["evidence"] in source
                and len(predicate_records) == 1
                and parent_predicate == predicate_records[0]
                and len(role_participants) == 1
                and participant == role_participants[0]
            ):
                matching_participants.append(candidate)
        predicate_context_position = (
            len(upstream) + 1 + source.index(predicate)
            if isinstance(predicate, str) and source.count(predicate) == 1
            else -1
        )
        antecedent_position = (
            context.find(antecedent) if isinstance(antecedent, str) else -1
        )
        if (
            paragraph.get("status") != "clear"
            or paragraph.get("competing_interpretations") != []
            or value.get("kind") not in {"omitted_subject", "inherited_subject"}
            or value.get("expression") is not None
            or value.get("evidence_status") != "contextual_inference"
            or not isinstance(value.get("referent"), str)
            or not isinstance(candidate_referents, list)
            or len(candidate_referents) != 1
            or not isinstance(candidate_referents[0], str)
            or value.get("referent") != subject
            or candidate_referents[0] != subject
            or value.get("evidence") != quote
            or not isinstance(predicate, str)
            or predicate not in source
            or not isinstance(role, str)
            or role not in STRUCTURED_ROLES
            or role == "other"
            or predicate not in quote
            or quote not in context
            or not antecedent
            or antecedent_position < 0
            or antecedent_position >= predicate_context_position
            or len(same_slot_references) != 1
            or same_slot_references[0] != value
            or len(matching_participants) != 1
        ):
            raise StrategyT1Error(
                f"{pid} indexed source analysis does not uniquely authorize the contextual subject {subject}"
            )
        return True
    if root != "predicates":
        raise StrategyT1Error(
            f"{pid} explicit source subject requires an indexed predicate participant"
        )
    parent_predicate = _bound_parent_predicate(bound)
    predicate = parent_predicate.get("predicate") if parent_predicate else None
    predicate_records = [
        item for item in paragraph.get("predicates", [])
        if isinstance(item, dict)
        and isinstance(item.get("predicate"), str)
        and isinstance(predicate, str)
        and _syntax_match_view(item["predicate"])
        == _syntax_match_view(predicate)
    ]
    role_participants = []
    if len(predicate_records) == 1 and isinstance(
        predicate_records[0].get("participants"), list
    ):
        role_participants = [
            item for item in predicate_records[0]["participants"]
            if isinstance(item, dict) and item.get("role") == value.get("role")
        ]
    if (
        paragraph.get("status") != "clear"
        or paragraph.get("competing_interpretations") != []
        or parent_predicate is None
        or value.get("evidence_status") != "explicit"
        or value.get("role") not in EXPLICIT_SUBJECT_ROLES
        or value.get("participant") != subject
        or value.get("evidence") != quote
        or subject not in quote
        or quote not in source
        or not isinstance(parent_predicate.get("predicate"), str)
        or not isinstance(parent_predicate.get("evidence"), str)
        or parent_predicate["predicate"] not in parent_predicate["evidence"]
        or parent_predicate["evidence"] not in source
        or len(predicate_records) != 1
        or predicate_records[0] != parent_predicate
        or len(role_participants) != 1
        or role_participants[0] != value
        or source.index(subject) > source.index(parent_predicate["evidence"])
    ):
        raise StrategyT1Error(
            f"{pid} indexed predicate participant does not authorize the explicit source subject {subject}"
        )
    return True
def _ambiguous_structured_subject(bound: dict[str, Any], pid: str) -> None:
    value = _structured_bound(bound)
    if value is None:
        return
    root = bound["_source_analysis_root"]
    if value.get("evidence_status") != "ambiguous":
        raise StrategyT1Error(f"{pid} ambiguity plan is not bound to ambiguous source analysis")
    if root == "references_and_ellipsis":
        if value.get("kind") not in {
            "omitted_subject", "inherited_subject", "ambiguous_reference"
        }:
            raise StrategyT1Error(f"{pid} ambiguity plan binds an unrelated reference item")
    elif root == "predicates":
        if value.get("participant") is not None:
            raise StrategyT1Error(f"{pid} ambiguous participant must not name a subject")
    else:
        raise StrategyT1Error(f"{pid} ambiguity plan binds an unsupported structured item")
def _positive_reference_quote(old: str, new: str, quote: str, pid: str) -> None:
    _reject_uncertain_authorization(quote, pid)
    quote_view = _syntax_match_view(quote)
    old_view = _syntax_match_view(old)
    new_view = _syntax_match_view(new)
    segments = [
        segment for segment in re.split(r"[；;。.!！？?\n]", quote_view)
        if old_view in segment and new_view in segment
    ]
    escaped = re.escape(new_view)
    negative = re.compile(rf"(?:不指|未指|并非指|不是|并非|非)[^，,；;。]{{0,8}}{escaped}")
    positive = re.compile(rf"(?<!不)(?<!未)(?<!非)(?:指代|指向|所指|指|先行词|承前)[^，,；;。]{{0,8}}{escaped}")
    reverse = re.compile(rf"{escaped}[^，,；;。]{{0,6}}(?:为|是)(?:先行词|所指|指代对象)")
    if not segments or any(negative.search(segment) for segment in segments):
        raise StrategyT1Error(f"{pid} bound quote negates or lacks the proposed antecedent {new}")
    if not any(positive.search(segment) or reverse.search(segment) for segment in segments):
        raise StrategyT1Error(f"{pid} bound quote lacks a local positive reference to {new}")
def _positive_structured_reference(
    old: str,
    new: str,
    status: str,
    bound: dict[str, Any],
    source: str,
    upstream: str,
    pid: str,
) -> bool:
    value = _structured_bound(bound)
    if value is None:
        return False
    if bound["_source_analysis_root"] != "references_and_ellipsis":
        raise StrategyT1Error(
            f"{pid} structured reference replacement requires references_and_ellipsis"
        )
    quote = bound["exact_quote"]
    paragraph = _structured_paragraph(bound)
    context = source if status == "explicit" else f"{upstream}\n{source}"
    same_expression_references = []
    if paragraph is not None and isinstance(
        paragraph.get("references_and_ellipsis"), list
    ):
        same_expression_references = [
            item for item in paragraph["references_and_ellipsis"]
            if isinstance(item, dict)
            and isinstance(item.get("expression"), str)
            and _syntax_match_view(item["expression"])
            == _syntax_match_view(old)
        ]
    if (
        paragraph is None
        or paragraph.get("status") != "clear"
        or paragraph.get("competing_interpretations") != []
        or value.get("kind") != "coreference"
        or value.get("expression") != old
        or value.get("referent") != new
        or value.get("candidate_referents") != [new]
        or value.get("evidence_status") != status
        or value.get("evidence") != quote
        or not isinstance(value.get("predicate"), str)
        or value["predicate"] not in source
        or not isinstance(value.get("role"), str)
        or value.get("role") not in STRUCTURED_ROLES
        or value["role"] == "other"
        or _syntax_match_view(source).count(_syntax_match_view(old)) != 1
        or old not in quote
        or new not in quote
        or quote not in context
        or quote.index(new) >= quote.index(old)
        or len(same_expression_references) != 1
        or same_expression_references[0] != value
    ):
        raise StrategyT1Error(
            f"{pid} indexed source analysis does not uniquely authorize {old} -> {new}"
        )
    return True
def _label_pattern(labels: tuple[str, ...]) -> str:
    return "|".join(re.escape(label) for label in sorted(labels, key=len, reverse=True))
def _closed_logic_authorization(
    prior: str,
    basis: str,
    role: str,
    quote: str,
) -> bool:
    compact = _canonical_quote_text(quote)
    prior_token = re.escape('"' + _normalize_space(prior) + '"')
    basis_token = re.escape('"' + _normalize_space(basis) + '"')
    source_labels = _label_pattern(LOGIC_SOURCE_ROLE_LABELS[role])
    target_labels = _label_pattern(LOGIC_ROLE_LABELS[role])
    copula = r"(?:为|是|作为|充当)"
    return bool(
        re.fullmatch(
            rf"{prior_token}{copula}(?:{source_labels})[，,；;]"
            rf"{basis_token}{copula}(?:{target_labels})[。.]?",
            compact,
        )
    )
def _positive_logic_evidence(
    connector: str,
    prior: str,
    basis: str,
    bound: dict[str, Any],
    source: str,
    pid: str,
) -> None:
    quote = bound["exact_quote"]
    structured = _structured_bound(bound)
    if structured is not None:
        if bound["_source_analysis_root"] != "relations":
            raise StrategyT1Error(
                f"{pid} structured logic addition requires an indexed relations item"
            )
        paragraph = _structured_paragraph(bound)
        evidence_span = _adjacent_clause_evidence_span(source, prior, basis)
        same_pair_relations = []
        prior_identity = _canonical_clause_identity(prior)
        basis_identity = _canonical_clause_identity(basis)
        if paragraph is not None and isinstance(paragraph.get("relations"), list):
            same_pair_relations = [
                item for item in paragraph["relations"]
                if isinstance(item, dict)
                and (
                    (
                        _canonical_clause_identity(item.get("source_clause"))
                        == prior_identity
                        and _canonical_clause_identity(item.get("target_clause"))
                        == basis_identity
                    )
                    or (
                        _canonical_clause_identity(item.get("source_clause"))
                        == basis_identity
                        and _canonical_clause_identity(item.get("target_clause"))
                        == prior_identity
                    )
                )
            ]
        if (
            paragraph is None
            or paragraph.get("status") != "clear"
            or paragraph.get("competing_interpretations") != []
            or len(same_pair_relations) != 1
            or same_pair_relations[0] != structured
            or structured.get("type") not in STRUCTURED_RELATION_TYPES[connector]
            or structured.get("source_clause") != prior
            or structured.get("target_clause") != basis
            or structured.get("evidence_status") not in {"explicit", "contextual_inference"}
            or structured.get("evidence") != quote
            or evidence_span is None
            or quote != evidence_span
            or bool(_greedy_markers(_syntax_match_view(basis), LOGIC_MARKERS))
        ):
            raise StrategyT1Error(
                f"{pid} indexed relation does not authorize this implicit connector, direction, and clause pair"
            )
        return
    _reject_uncertain_authorization(quote, pid)
    if _analysis_field_root(bound["source_analysis_field"]) not in LOGIC_EVIDENCE_FIELDS:
        raise StrategyT1Error(f"{pid} logic addition binds a non-authorizing analysis field")
    role = ADDITIVE_LOGIC_ROLES[connector]
    if not _closed_logic_authorization(prior, basis, role, quote):
        raise StrategyT1Error(
            f"{pid} bound quote negates or does not match the closed affirmative logic authorization template for {role}"
        )
def _positive_parallel_evidence(
    shared: str,
    basis: str,
    bound: dict[str, Any],
    pid: str,
) -> None:
    if _structured_bound(bound) is not None:
        raise StrategyT1Error(
            f"{pid} locked structured source analysis does not encode shared-constituent placement; defer lexical parallel completion to English translation and bilingual review"
        )
    quote = bound["exact_quote"]
    _reject_uncertain_authorization(quote, pid)
    if _analysis_field_root(bound["source_analysis_field"]) not in PARALLEL_EVIDENCE_FIELDS:
        raise StrategyT1Error(f"{pid} parallel completion binds a non-authorizing analysis field")
    compact = _canonical_quote_text(quote)
    quoted_shared = re.escape('"' + _normalize_space(shared) + '"')
    quoted_basis = re.escape('"' + _normalize_space(basis) + '"')
    prefix = r"(?:(?:两项|三项|四项|多项)(?:并列|排比)[；;])?"
    member = r"(?:第[一二三四五六七八九十0-9]+项|后项|后一项|末项)"
    sharing = r"(?:承前)?(?:省略|共用|共享)"
    restore = r"(?:可|可以|应|应当)?在"
    if not re.fullmatch(
        rf"{prefix}{member}{quoted_basis}{sharing}{quoted_shared}[，,]"
        rf"{restore}{quoted_basis}前(?:补|补出|加|恢复){quoted_shared}[。.]?",
        compact,
    ):
        raise StrategyT1Error(
            f"{pid} bound quote negates or does not match the closed affirmative parallel authorization template"
        )
def _clause_indexes_containing(value: str, span: str) -> list[int]:
    return [
        index for index, clause in enumerate(CLAUSE_RE.findall(value))
        if span in clause
    ]
def _clause_content(value: str) -> str:
    return value.strip().rstrip("，,；;。！？!?：:").strip()
def _canonical_clause_identity(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    content = _syntax_match_view(_clause_content(value))
    return content or None
def _logic_clause_pair(source: str, basis: str) -> tuple[str, str] | None:
    clauses = _clause_records(source)
    indexes = [
        index for index, clause in enumerate(clauses)
        if _normalize_space(clause["content"]) == _normalize_space(basis)
    ]
    if len(indexes) != 1 or indexes[0] == 0:
        return None
    index = indexes[0]
    target = clauses[index]["content"]
    prior = clauses[index - 1]["content"]
    if _normalize_space(target) != _normalize_space(basis) or not prior:
        return None
    if sum(
        _normalize_space(item["content"]) == _normalize_space(prior)
        for item in clauses
    ) != 1:
        return None
    return prior, target
def _clause_records(value: str) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for match in CLAUSE_RE.finditer(value):
        raw = match.group(0)
        content = _clause_content(raw)
        if not content:
            continue
        relative = raw.find(content)
        if relative < 0:
            continue
        start = match.start() + relative
        result.append({
            "content": content,
            "start": start,
            "end": start + len(content),
        })
    return result
def _adjacent_clause_evidence_span(
    source: str, prior: str, basis: str
) -> str | None:
    clauses = _clause_records(source)
    prior_indexes = [
        index for index, item in enumerate(clauses) if item["content"] == prior
    ]
    target_indexes = [
        index for index, item in enumerate(clauses) if item["content"] == basis
    ]
    if (
        len(prior_indexes) != 1
        or len(target_indexes) != 1
        or target_indexes[0] != prior_indexes[0] + 1
    ):
        return None
    left = clauses[prior_indexes[0]]
    right = clauses[target_indexes[0]]
    return source[left["start"] : right["end"]]
def _is_maximal_controlled_reference(source: str, old: str) -> bool:
    source_view = _syntax_match_view(source)
    old_view = _syntax_match_view(old)
    if not old_view or source_view.count(old_view) != 1:
        return False
    for form in REFERENCE_FORMS:
        form_view = _syntax_match_view(form)
        if len(form_view) <= len(old_view) or old_view not in form_view:
            continue
        if form_view in source_view:
            return False
    return True
def _canonical_quote_text(value: str) -> str:
    result = _syntax_match_view(value)
    for left, right in (("“", "”"), ("‘", "’"), ("「", "」"), ("『", "』")):
        result = result.replace(left, '"').replace(right, '"')
    return result
def _validate_parallel_addition_position(
    shared: str,
    basis: str,
    source: str,
    restructured: str,
    pid: str,
) -> None:
    shared_lexical = _lexical_sequence(shared)
    source_clauses = [
        _lexical_sequence(clause) for clause in CLAUSE_RE.findall(source)
        if _lexical_sequence(clause)
    ]
    if shared_lexical in source_clauses:
        raise StrategyT1Error(f"{pid} parallel completion cannot duplicate a complete source clause")
    source_basis_indexes = _clause_indexes_containing(source, basis)
    if len(source_basis_indexes) != 1 or source_basis_indexes[0] == 0:
        raise StrategyT1Error(f"{pid} parallel completion needs one exact basis in a later source member")
    joined = _normalize_space(shared + basis)
    if _normalize_space(source).count(joined) != 0 or _normalize_space(restructured).count(joined) != 1:
        raise StrategyT1Error(
            f"{pid} parallel completion must insert the shared constituent immediately before its unique later-member basis"
        )
def validate_subject_strategy(
    subject: dict[str, Any],
    evidence: list[dict[str, Any]],
    source: str,
    restructured: str,
    upstream: str,
    operations: list[str],
    pid: str,
) -> None:
    subject = _validate_subject_shape(subject, f"{pid}.subject_strategy")
    mode = subject["mode"]
    status = subject["evidence_status"]
    subject_zh = subject["subject_zh"]
    antecedent = subject["antecedent_zh"]
    index = subject["evidence_index"]
    if mode == "not_applicable":
        if status != "not_applicable" or any(v is not None for v in (subject_zh, antecedent, index)):
            raise StrategyT1Error(f"{pid} not_applicable subject metadata is inconsistent")
        if "explicit_subject" in operations:
            raise StrategyT1Error(f"{pid} explicit_subject requires subject evidence")
        return
    bound = _evidence_at(evidence, index, f"{pid}.subject_strategy")
    if bound["kind"] not in {"subject", "reference"}:
        raise StrategyT1Error(f"{pid} subject strategy must bind subject/reference evidence")
    if mode == "explicit_source_subject":
        if status != "explicit" or not subject_zh or antecedent is not None:
            raise StrategyT1Error(f"{pid} explicit subject metadata is inconsistent")
        if subject_zh not in source or subject_zh not in restructured:
            raise StrategyT1Error(f"{pid} explicit subject must occur in current source and restructured text")
        if not _positive_structured_subject(
            subject_zh,
            bound,
            evidence,
            contextual=False,
            antecedent=None,
            source=source,
            upstream=upstream,
            pid=pid,
        ):
            _positive_subject_quote(subject_zh, bound["exact_quote"], False, pid)
        return
    if mode == "contextual_subject":
        if status != "contextual_inference" or not subject_zh or not antecedent:
            raise StrategyT1Error(f"{pid} contextual subject metadata is inconsistent")
        structured = _structured_bound(bound) is not None
        available = f"{upstream}\n{source}" if structured else upstream
        if antecedent not in available or subject_zh not in antecedent:
            location = "source-context" if structured else "upstream"
            raise StrategyT1Error(f"{pid} contextual subject requires an exact {location} antecedent")
        if (
            (_structured_bound(bound) is None and subject_zh not in bound["exact_quote"])
            or subject_zh not in restructured
        ):
            raise StrategyT1Error(f"{pid} contextual subject is not supported by bound evidence and output")
        if not _positive_structured_subject(
            subject_zh,
            bound,
            evidence,
            contextual=True,
            antecedent=antecedent,
            source=source,
            upstream=upstream,
            pid=pid,
        ):
            _positive_subject_quote(subject_zh, bound["exact_quote"], True, pid)
        return
    if mode not in {"passive", "impersonal", "retained_ambiguity"} or status != "ambiguous":
        raise StrategyT1Error(f"{pid} ambiguous subject metadata is inconsistent")
    if subject_zh is not None or antecedent is not None:
        raise StrategyT1Error(f"{pid} ambiguous subject must not invent a subject or antecedent")
    _ambiguous_structured_subject(bound, pid)
    required = "preserve_ambiguity" if mode == "retained_ambiguity" else "passive_or_impersonal"
    if required not in operations:
        raise StrategyT1Error(f"{pid} ambiguous subject requires {required}")
def _only_cjk(value: str) -> bool:
    compact = _normalize_space(value)
    return bool(compact) and all(CJK_RE.fullmatch(char) for char in compact)
def validate_typed_changes(
    changes: list[dict[str, Any]],
    evidence: list[dict[str, Any]],
    subject: dict[str, Any],
    source: str,
    restructured: str,
    upstream: str,
    operations: list[str],
    pid: str,
) -> None:
    expected_kind = {
        "explicit_subject": "subject",
        "explicit_reference": "reference",
        "explicit_logic": "logic",
        "parallelism": "structure",
    }
    for index, change in enumerate(changes):
        where = f"{pid}.typed_changes[{index}]"
        change = _validate_typed_change_shape(change, where)
        operation = change["operation"]
        if operation not in operations:
            raise StrategyT1Error(f"{where}.operation is absent from restructuring_operations")
        bound = _evidence_at(evidence, change["evidence_index"], where)
        if bound["kind"] != expected_kind[operation]:
            raise StrategyT1Error(f"{where} binds the wrong evidence kind")
        old = change["source_zh"]
        new = change["restructured_zh"]
        if not _only_cjk(new) or (old is not None and not _only_cjk(old)):
            raise StrategyT1Error(f"{where} may account for CJK lexical text only")
        if change["change"] == "addition":
            if old is not None:
                raise StrategyT1Error(f"{where} addition requires null source_zh")
        elif not old or old not in source:
            raise StrategyT1Error(f"{where} replacement source_zh must occur in current source")
        if new not in restructured:
            raise StrategyT1Error(f"{where}.restructured_zh is absent from restructured text")
        basis = change["basis_zh"]
        status = change["evidence_status"]
        if status == "explicit" and basis is not None and basis not in source:
            raise StrategyT1Error(f"{where} explicit basis must occur in current source")
        if (
            status == "contextual_inference"
            and operation not in {"explicit_subject", "explicit_logic"}
            and (not basis or basis not in upstream)
        ):
            raise StrategyT1Error(f"{where} contextual basis must be an exact upstream span")
        if operation == "explicit_subject":
            if (
                change["change"] != "addition"
                or new != subject.get("subject_zh")
                or subject.get("mode") != "contextual_subject"
                or status != "contextual_inference"
                or len(changes) != 1
                or "reorder" in operations
                or change["evidence_index"] != subject.get("evidence_index")
            ):
                raise StrategyT1Error(
                    f"{where} must add exactly the bound subject using the same evidence item"
                )
            if status != subject.get("evidence_status"):
                raise StrategyT1Error(f"{where} subject evidence status mismatch")
            structured = _structured_bound(bound, "references_and_ellipsis")
            predicate = (
                structured.get("predicate") if structured is not None else basis
            )
            if (
                not isinstance(predicate, str)
                or basis != predicate
                or source.count(basis) != 1
                or _normalize_space(source).count(_normalize_space(new + basis)) != 0
                or _normalize_space(restructured).count(_normalize_space(new + basis)) != 1
            ):
                raise StrategyT1Error(
                    f"{where} must insert the uniquely bound subject immediately before its source predicate"
                )
            if structured is None:
                _positive_legacy_contextual_subject(
                    new, basis, bound["exact_quote"], pid
                )
        elif operation == "explicit_reference":
            if change["change"] != "replacement" or old is None:
                raise StrategyT1Error(
                    f"{where} zero-reference additions are not permitted: "
                    "a zero subject must use contextual_subject plus explicit_subject, "
                    "and other ellipsis is deferred to bilingual translation review"
                )
            if not basis or new not in basis:
                raise StrategyT1Error(f"{where} reference rendering must occur in its exact basis")
            if old not in REFERENCE_FORMS:
                raise StrategyT1Error(f"{where} source_zh is not a controlled reference form")
            if not _is_maximal_controlled_reference(source, old):
                raise StrategyT1Error(
                    f"{where} source_zh must be one unique complete maximal controlled "
                    "reference form"
                )
            expected = _lexical_sequence(source).replace(
                _lexical_sequence(old), _lexical_sequence(new), 1
            )
            if (
                len(changes) != 1
                or "reorder" in operations
                or _lexical_sequence(restructured) != expected
            ):
                raise StrategyT1Error(
                    f"{where} must replace the uniquely bound overt reference in place "
                    "without another lexical change or reorder"
                )
            if not _positive_structured_reference(
                old, new, status, bound, source, upstream, pid
            ):
                if old not in bound["exact_quote"] or new not in bound["exact_quote"]:
                    raise StrategyT1Error(f"{where} reference form and antecedent need one exact bound quote")
                _positive_reference_quote(old, new, bound["exact_quote"], pid)
        elif operation == "explicit_logic":
            if change["change"] != "addition" or old is not None:
                raise StrategyT1Error(f"{where} explicit_logic permits a typed connector addition only")
            if new not in ADDITIVE_LOGIC_ROLES:
                raise StrategyT1Error(f"{where} logic connector is not approved for evidence-bound addition")
            if basis and _greedy_markers(
                _syntax_match_view(basis), LOGIC_MARKERS
            ):
                raise StrategyT1Error(
                    f"{where} target clause already contains a visible logic marker; "
                    "defer instead of stacking another connector"
                )
            if len(changes) != 1 or "reorder" in operations:
                raise StrategyT1Error(f"{where} logic addition cannot share a record with another lexical change or reorder")
            structured_relation = _structured_bound(bound, "relations")
            status_ok = (
                status == "explicit"
                if structured_relation is None
                else status == structured_relation.get("evidence_status")
                and status in {"explicit", "contextual_inference"}
            )
            if not status_ok or not basis or source.count(basis) != 1:
                raise StrategyT1Error(
                    f"{where} logic addition requires one exact current-line basis and matching evidence status"
                )
            clause_pair = _logic_clause_pair(source, basis)
            joined = _normalize_space(new + basis)
            if (
                clause_pair is None
                or _normalize_space(source).count(joined) != 0
                or _normalize_space(restructured).count(joined) != 1
            ):
                raise StrategyT1Error(
                    f"{where} logic connector must occur once at the start of a complete unique later-clause basis"
                )
            _positive_logic_evidence(new, clause_pair[0], basis, bound, source, pid)
        elif operation == "parallelism":
            if change["change"] != "addition" or old is not None:
                raise StrategyT1Error(f"{where} parallelism permits a typed shared-constituent addition only")
            if "reorder" in operations or any(
                item.get("operation") != "parallelism" for item in changes
            ):
                raise StrategyT1Error(f"{where} parallel completion cannot share a record with another lexical operation or reorder")
            if (
                status != "explicit"
                or not basis
                or source.count(basis) != 1
                or new not in source
                or new in basis
                or sum(item.get("basis_zh") == basis for item in changes) != 1
            ):
                raise StrategyT1Error(
                    f"{where} parallel completion requires a source constituent and one separate current-line insertion basis"
                )
            _positive_parallel_evidence(new, basis, bound, pid)
            _validate_parallel_addition_position(
                new, basis, source, restructured, pid
            )
def _cjk_counter(value: str) -> Counter[str]:
    return Counter(CJK_RE.findall(value))
def _lexical_sequence(value: str) -> str:
    return "".join(char for char in value if unicodedata.category(char)[:1] in {"L", "M", "N", "S"})
def _lexical_counter(value: str) -> Counter[str]:
    return Counter(_lexical_sequence(value))
def validate_lexical_conservation(
    source: str,
    restructured: str,
    changes: list[dict[str, Any]],
    operations: list[str],
    pid: str,
) -> None:
    expected = _lexical_counter(source)
    for change in changes:
        old = change["source_zh"]
        if old:
            removed = _lexical_counter(old)
            if any(expected[char] < count for char, count in removed.items()):
                raise StrategyT1Error(f"{pid} typed replacement removes unavailable CJK content")
            expected.subtract(removed)
        expected.update(_lexical_counter(change["restructured_zh"]))
    expected += Counter()
    if expected != _lexical_counter(restructured):
        raise StrategyT1Error(f"{pid} has an unaccounted Unicode lexical addition or omission")
    if "reorder" in operations:
        if changes:
            raise StrategyT1Error(f"{pid} reorder cannot be combined with lexical typed changes")
        source_units = [_normalize_space(value) for value in CLAUSE_RE.findall(source) if value.strip()]
        target_units = [_normalize_space(value) for value in CLAUSE_RE.findall(restructured) if value.strip()]
        if len(source_units) < 2 or Counter(source_units) != Counter(target_units):
            raise StrategyT1Error(f"{pid} reorder is limited to complete punctuation-bound clauses")
        return
    # Without the explicit clause-level reorder operation, unchanged lexical
    # material must retain its order.  Remove the small typed edits and compare
    # the remaining lexical sequence; this blocks untyped role swapping.
    source_order = _lexical_sequence(source)
    target_order = _lexical_sequence(restructured)
    def positions(text: str, needle: str) -> list[int]:
        return [index for index in range(len(text) - len(needle) + 1) if text.startswith(needle, index)]
    def edits_match(left: str, right: str, index: int) -> bool:
        if index == len(changes):
            return left == right
        change = changes[index]
        old = _lexical_sequence(change["source_zh"] or "")
        new = _lexical_sequence(change["restructured_zh"])
        right_positions = positions(right, new)
        if old:
            marker = chr(0xE000 + index)
            return any(
                edits_match(
                    left[:lp] + marker + left[lp + len(old):],
                    right[:rp] + marker + right[rp + len(new):],
                    index + 1,
                )
                for lp in positions(left, old)
                for rp in right_positions
            )
        return any(
            edits_match(right=right[:rp] + right[rp + len(new):], left=left, index=index + 1)
            for rp in right_positions
        )
    if not edits_match(source_order, target_order, 0):
        raise StrategyT1Error(f"{pid} changes lexical order without clause-level reorder")
def _greedy_markers(value: str, markers: set[str]) -> list[str]:
    ordered = sorted(markers, key=lambda item: (-len(item), item))
    found: list[str] = []
    offset = 0
    while offset < len(value):
        match = next((marker for marker in ordered if value.startswith(marker, offset)), None)
        if match is None:
            offset += 1
        else:
            found.append(match)
            offset += len(match)
    return found
def validate_visible_logic_and_negation(
    source: str,
    restructured: str,
    changes: list[dict[str, Any]],
    pid: str,
) -> None:
    source_view = _syntax_match_view(source)
    target_view = _syntax_match_view(restructured)
    if _greedy_markers(source_view, NEGATION_MARKERS) != _greedy_markers(target_view, NEGATION_MARKERS):
        raise StrategyT1Error(f"{pid} changes visible negation markers")
    if _greedy_markers(source_view, LIMITER_MARKERS) != _greedy_markers(target_view, LIMITER_MARKERS):
        raise StrategyT1Error(f"{pid} changes visible limiter/quantity/modality markers")
    additions = [
        item["restructured_zh"]
        for item in changes
        if item["operation"] == "explicit_logic" and item["change"] == "addition"
    ]
    expected_logic = Counter(_greedy_markers(source_view, LOGIC_MARKERS))
    expected_logic.update(additions)
    if expected_logic != Counter(_greedy_markers(target_view, LOGIC_MARKERS)):
        raise StrategyT1Error(f"{pid} changes visible logic markers without typed evidence")
    for left, right in LOGIC_PAIRS:
        source_left = [m.start() for m in re.finditer(re.escape(left), source_view)]
        source_right = [m.start() for m in re.finditer(re.escape(right), source_view)]
        for left_pos, right_pos in zip(source_left, source_right):
            if left_pos < right_pos:
                target_left = [m.start() for m in re.finditer(re.escape(left), target_view)]
                target_right = [m.start() for m in re.finditer(re.escape(right), target_view)]
                if not target_left or not target_right or target_left[0] >= target_right[-1]:
                    raise StrategyT1Error(f"{pid} reverses a visible {left}...{right} relation")
def _char_sequence(value: str, chars: set[str]) -> list[str]:
    return [char for char in value if char in chars]
def validate_surface_invariants(source: str, restructured: str, pid: str) -> None:
    invariants = (
        (DIGIT_RE.findall(source), DIGIT_RE.findall(restructured), "numeric token/order"),
        (URL_RE.findall(source), URL_RE.findall(restructured), "URL token/order"),
        (LATIN_RE.findall(source), LATIN_RE.findall(restructured), "Latin/Sanskrit token/order"),
        (SANSKRIT_RE.findall(source), SANSKRIT_RE.findall(restructured), "Sanskrit token/order"),
        (_char_sequence(source, QUOTE_CHARS), _char_sequence(restructured, QUOTE_CHARS), "quotation delimiters"),
        (_char_sequence(source, QUESTION_EMPHASIS_CHARS), _char_sequence(restructured, QUESTION_EMPHASIS_CHARS), "question/emphasis scope"),
        (_char_sequence(source, BRACKET_CHARS), _char_sequence(restructured, BRACKET_CHARS), "brackets/parenthetical gloss"),
        (_char_sequence(source, MARKUP_CHARS), _char_sequence(restructured, MARKUP_CHARS), "Markdown/emphasis markers"),
    )
    for before, after, label in invariants:
        if before != after:
            raise StrategyT1Error(f"{pid} changes {label}")
def validate_sentence_units(units: list[Any], restructured: str, pid: str) -> None:
    if not isinstance(units, list) or not units or any(not isinstance(v, str) or not v.strip() for v in units):
        raise StrategyT1Error(f"{pid} sentence_units_zh must be a nonempty string array")
    if _normalize_space("".join(units)) != _normalize_space(restructured):
        raise StrategyT1Error(f"{pid} sentence_units_zh do not reconstruct restructured_zh")
def cjk_count(value: str) -> int:
    return len(CJK_RE.findall(value))
def length_warning(pid: str, source: str, restructured: str) -> dict[str, Any] | None:
    source_count = cjk_count(source)
    target_count = cjk_count(restructured)
    ratio = target_count / source_count if source_count else 1.0
    if 0.90 <= ratio <= 1.15:
        return None
    return {
        "paragraph_id": pid,
        "kind": "cjk_length_ratio",
        "ratio": round(ratio, 6),
        "advisory_band": [0.90, 1.15],
        "blocking": False,
    }
def source_line_inventory(context: dict[str, Any], selected_ids: list[str]) -> dict[str, Any]:
    selected = set(selected_ids)
    all_ids = [row["id"] for row in context["source_rows"]]
    return {
        "total_nonblank_lines": len(all_ids),
        "selected_count": len(selected_ids),
        "unselected_count": len(all_ids) - len(selected_ids),
        "selected_line_ids": [context["analysis_original_ids"][pid] for pid in all_ids if pid in selected],
        "unselected_line_ids": [context["analysis_original_ids"][pid] for pid in all_ids if pid not in selected],
        "inventory_status": "ACCOUNTED",
        "attention_proven": False,
    }
def validate_project(
    project: Path,
    stage: str = "all",
    artifact_path: Path | None = None,
    *,
    accepted_decisions_path: Path | None = None,
    expected_accepted_decisions_sha256: Any = _UNSPECIFIED,
) -> dict[str, Any]:
    if stage not in {"all", "restructuring"}:
        raise StrategyT1Error(f"unknown T1.1.2 validation stage: {stage}")
    context = project_context(project)
    path = artifact_path.expanduser().resolve() if artifact_path else context["project"] / ARTIFACT_NAME
    artifact = load_json(path)
    _exact_fields(artifact, TOP_FIELDS, ARTIFACT_NAME)
    if artifact.get("schema_version") != SCHEMA_VERSION or artifact.get("workflow_version") != WORKFLOW_VERSION:
        raise StrategyT1Error("semantic-restructuring artifact has a stale schema/workflow version")
    if artifact.get("stage") != "semantic_restructuring":
        raise StrategyT1Error("semantic-restructuring stage is invalid")
    for field in (
        "source_sha256", "translation_project_sha256", "source_analysis_sha256", "term_map_sha256"
    ):
        if artifact.get(field) != context[field]:
            raise StrategyT1Error(f"semantic-restructuring {field} mismatch")
    decisions_hash = _hash_or_none(artifact.get("accepted_decisions_sha256"), "accepted_decisions_sha256")
    expectation_supplied = expected_accepted_decisions_sha256 is not _UNSPECIFIED
    expected_hash = None
    if expectation_supplied:
        expected_hash = _hash_or_none(
            expected_accepted_decisions_sha256,
            "expected_accepted_decisions_sha256",
        )
    if accepted_decisions_path is not None:
        decision_path = accepted_decisions_path.expanduser().resolve()
        if not decision_path.is_file():
            raise StrategyT1Error(f"accepted decisions file is missing: {decision_path}")
        expected_hash = sha256_file(decision_path)
        expectation_supplied = True
    if expectation_supplied and decisions_hash != expected_hash:
        raise StrategyT1Error("semantic-restructuring accepted_decisions_sha256 mismatch")
    if not isinstance(artifact.get("generated_by"), dict):
        raise StrategyT1Error("semantic restructuring generated_by must be an object")
    _provenance(artifact["generated_by"])
    if artifact.get("source_nonblank_units") != len(context["source_rows"]):
        raise StrategyT1Error("source_nonblank_units does not match frozen source inventory")
    records = artifact.get("records")
    if not isinstance(records, list) or not records:
        raise StrategyT1Error("an explicit T1.1.2 pilot requires at least one selected record")
    if artifact.get("selected_line_count") != len(records):
        raise StrategyT1Error("selected_line_count does not match records")
    selected_ids: list[str] = []
    warnings: list[dict[str, Any]] = []
    for index, record in enumerate(records):
        where = f"records[{index}]"
        if not isinstance(record, dict):
            raise StrategyT1Error(f"{where} must be an object")
        _exact_fields(record, FINAL_RECORD_FIELDS, where)
        raw_id = _text(record.get("paragraph_id"), f"{where}.paragraph_id")
        pid = canonical_line_id(raw_id)
        if pid not in context["source_rows_by_id"]:
            raise StrategyT1Error(f"{where} references unknown source line {raw_id}")
        if pid in selected_ids:
            raise StrategyT1Error(f"duplicate selected source line: {raw_id}")
        selected_ids.append(pid)
        row = context["source_rows_by_id"][pid]
        analysis = context["analysis_records"][pid]
        if record.get("source_line") != row["line"]:
            raise StrategyT1Error(f"{raw_id} source_line mismatch")
        if record.get("source_line_sha256") != row["sha256"]:
            raise StrategyT1Error(f"{raw_id} source_line_sha256 mismatch")
        if record.get("source_excerpt") != row["text"]:
            raise StrategyT1Error(f"{raw_id} source_excerpt mismatch")
        if record.get("source_analysis_record_sha256") != canonical_hash(analysis):
            raise StrategyT1Error(f"{raw_id} source-analysis record hash mismatch")
        evidence = _evidence_list(record.get("analysis_evidence"), analysis, f"{raw_id}.analysis_evidence")
        fields = list(dict.fromkeys(value["source_analysis_field"] for value in evidence))
        if record.get("source_analysis_fields_used") != fields:
            raise StrategyT1Error(f"{raw_id} source_analysis_fields_used do not match bound evidence")
        operations = record.get("restructuring_operations")
        if (
            not isinstance(operations, list) or not operations or len(set(operations)) != len(operations)
            or any(value not in OPERATIONS for value in operations)
        ):
            raise StrategyT1Error(f"{raw_id} restructuring_operations are invalid")
        restructured = _text(record.get("restructured_zh"), f"{raw_id}.restructured_zh")
        if _normalize_space(restructured) == _normalize_space(row["text"]):
            raise StrategyT1Error(f"{raw_id} was selected but has no restructuring change")
        validate_sentence_units(record.get("sentence_units_zh"), restructured, raw_id)
        subject = record.get("subject_strategy")
        if not isinstance(subject, dict):
            raise StrategyT1Error(f"{raw_id}.subject_strategy must be an object")
        upstream = _upstream_text(context, row["line"])
        validate_subject_strategy(subject, evidence, row["text"], restructured, upstream, operations, raw_id)
        changes = record.get("typed_changes")
        if not isinstance(changes, list):
            raise StrategyT1Error(f"{raw_id}.typed_changes must be an array")
        validate_typed_changes(changes, evidence, subject, row["text"], restructured, upstream, operations, raw_id)
        validate_lexical_conservation(row["text"], restructured, changes, operations, raw_id)
        validate_visible_logic_and_negation(row["text"], restructured, changes, raw_id)
        validate_surface_invariants(row["text"], restructured, raw_id)
        required_terms = required_protected_terms(row["text"], context["term_keys"])
        protected = record.get("protected_terms")
        if protected != required_terms:
            raise StrategyT1Error(f"{raw_id} protected_terms do not match runner-derived requirements")
        for term in required_terms:
            if row["text"].count(term) != restructured.count(term):
                raise StrategyT1Error(f"{raw_id} protected term count changed: {term}")
        warning = length_warning(raw_id, row["text"], restructured)
        if warning:
            warnings.append(warning)
    order = {row["id"]: index for index, row in enumerate(context["source_rows"])}
    if [order[pid] for pid in selected_ids] != sorted(order[pid] for pid in selected_ids):
        raise StrategyT1Error("selected records are not in source order")
    return {
        "status": "PASS",
        "workflow_version": WORKFLOW_VERSION,
        "project": str(context["project"]),
        "source_sha256": context["source_sha256"],
        "translation_project_sha256": context["translation_project_sha256"],
        "source_analysis_sha256": context["source_analysis_sha256"],
        "analysis_line_hash_mode": context["analysis_line_hash_mode"],
        "analysis_schema_mode": context["analysis_schema_mode"],
        "term_map_sha256": context["term_map_sha256"],
        "accepted_decisions_sha256": decisions_hash,
        "source_nonblank_units": len(context["source_rows"]),
        "selected_line_count": len(records),
        "source_line_inventory": source_line_inventory(context, selected_ids),
        "warnings": warnings,
        "mechanical_scope": {
            "doctrinal_equivalence_proven": False,
            "proposition_completeness_proven": False,
            "subject_role_correctness_proven": False,
            "reference_resolution_correctness_proven": False,
            "implicit_logic_correctness_proven": False,
            "parallel_scope_correctness_proven": False,
            "unselected_line_model_attention_proven": False,
            "required_semantic_gates": [
                "independent_bilingual_review_round_1",
                "independent_bilingual_review_round_2",
                "post_concision_full_chinese_recheck",
            ],
        },
    }
def validate_legacy_project(project: Path, stage: str = "all") -> dict[str, Any]:
    """Read-only validation of existing T1.1.1 artifacts; never rewrite them."""
    result = semantic_bridge_legacy.validate_project(project, stage)
    return {**result, "legacy_workflow_version": "1.1.1", "read_only": True}
def fixture_artifact(project: Path) -> dict[str, Any]:
    """Create a disposable two-line project and one hydrated valid artifact."""
    project.mkdir(parents=True, exist_ok=True)
    metadata = project / PROJECT_NAME
    metadata.write_text("project_id: semantic-restructuring-contract\ntitle: 标题\n", encoding="utf-8")
    source = project / "source.dj"
    source.write_text(
        "# 标题\n\n若观察诸法缘起、无自性而空，就不可把受、心、心所、能缘和所缘日常化。\n",
        encoding="utf-8",
    )
    term_map = project / TERM_MAP_NAME
    term_map.write_text(
        json.dumps(
            {"terms": [{"source": term, "preferred": f"term-{index}"} for index, term in enumerate(sorted(CORE_BUDDHIST_TERMS))]},
            ensure_ascii=False,
        ) + "\n",
        encoding="utf-8",
    )
    source_sha, rows, _ = source_index(source)
    analysis = {
        "schema_version": 1,
        "source_sha256": source_sha,
        "translation_project_sha256": sha256_file(metadata),
        "term_map_sha256": sha256_file(term_map),
        "paragraphs": [
            {
                "paragraph_id": "L001",
                "line_sha256": rows[0]["sha256"],
                "semantic_head": "标题",
                "must_preserve": ["标题"],
                "must_not_invent": ["不得扩写标题"],
            },
            {
                "paragraph_id": "L003",
                "line_sha256": rows[1]["sha256"],
                "semantic_roles_and_references": "观察者未明确，保持无主或非人称结构",
                "logic_and_scope": "若...就...构成条件与结果关系",
                "must_preserve": ["条件关系、否定和全部佛教术语"],
                "must_not_invent": ["不得补出我们、人们或其他观察者"],
            },
        ],
    }
    (project / ANALYSIS_NAME).write_text(json.dumps(analysis, ensure_ascii=False) + "\n", encoding="utf-8")
    proposal = {
        "records": [
            {
                "paragraph_id": "L3",
                "analysis_evidence": [
                    {
                        "kind": "subject",
                        "source_analysis_field": "semantic_roles_and_references",
                        "exact_quote": "观察者未明确，保持无主或非人称结构",
                    },
                    {
                        "kind": "logic",
                        "source_analysis_field": "logic_and_scope",
                        "exact_quote": "若...就...构成条件与结果关系",
                    },
                ],
                "restructured_zh": "若观察诸法缘起、无自性而空；就不可把受、心、心所、能缘和所缘日常化。",
                "restructuring_operations": ["split_sentence", "passive_or_impersonal"],
                "sentence_units_zh": [
                    "若观察诸法缘起、无自性而空；",
                    "就不可把受、心、心所、能缘和所缘日常化。",
                ],
                "subject_strategy": {
                    "mode": "impersonal",
                    "evidence_status": "ambiguous",
                    "subject_zh": None,
                    "antecedent_zh": None,
                    "evidence_index": 0,
                },
                "typed_changes": [],
            }
        ]
    }
    artifact = hydrate_proposal(project, proposal)
    write_artifact(project, artifact)
    return artifact
def fixture_structured_artifact(project: Path) -> dict[str, Any]:
    """Create a disposable locked-Stage-4-shaped subject/logic fixture."""
    project.mkdir(parents=True, exist_ok=True)
    metadata = project / PROJECT_NAME
    metadata.write_text("project_id: structured-restructuring-contract\n", encoding="utf-8")
    source = project / "source.dj"
    source.write_text(
        "修行者应观察自心。\n起烦恼，就应觉察。\n勤修，得乐。\n",
        encoding="utf-8",
    )
    term_map = project / TERM_MAP_NAME
    term_map.write_text(
        '{"terms": [{"source": "修行", "preferred": "practice"}]}\n',
        encoding="utf-8",
    )
    source_sha, _, _ = source_index(source)
    def paragraph(pid: str, **updates: Any) -> dict[str, Any]:
        value = {
            "paragraph_id": pid,
            "predicates": [],
            "relations": [],
            "operators": [],
            "references_and_ellipsis": [],
            "competing_interpretations": [],
            "must_preserve": [],
            "must_not_invent": [],
            "status": "clear",
        }
        value.update(updates)
        return value
    subject_evidence = "起烦恼"
    analysis = {
        "schema_version": 1,
        "source_sha256": source_sha,
        "project_sha256": sha256_file(metadata),
        "term_map_sha256": sha256_file(term_map),
        "paragraphs": [
            paragraph("L1"),
            paragraph(
                "L2",
                predicates=[{
                    "predicate": "起烦恼",
                    "canonical_meaning": "生起烦恼",
                    "evidence": "起烦恼",
                    "participants": [{
                        "role": "experiencer",
                        "participant": None,
                        "evidence": "起烦恼",
                        "evidence_status": "contextual_inference",
                        "notes": "体验者承接上一句。",
                    }],
                }],
                references_and_ellipsis=[{
                    "kind": "inherited_subject",
                    "expression": None,
                    "predicate": "起烦恼",
                    "role": "experiencer",
                    "referent": "修行者",
                    "candidate_referents": ["修行者"],
                    "evidence": subject_evidence,
                    "evidence_status": "contextual_inference",
                    "notes": "本句沿用上一句主体。",
                }],
            ),
            paragraph(
                "L3",
                relations=[{
                    "type": "cause",
                    "source_clause": "勤修",
                    "target_clause": "得乐",
                    "evidence": "勤修，得乐",
                    "evidence_status": "contextual_inference",
                    "notes": "前项为因，后项为果。",
                }],
            ),
        ],
    }
    (project / ANALYSIS_NAME).write_text(
        json.dumps(analysis, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    proposal = {
        "records": [
            {
                "paragraph_id": "L2",
                "analysis_evidence": [
                    {
                        "kind": "subject",
                        "source_analysis_field": "references_and_ellipsis[0]",
                        "exact_quote": subject_evidence,
                    },
                    {
                        "kind": "subject",
                        "source_analysis_field": "predicates[0].participants[0]",
                        "exact_quote": "起烦恼",
                    },
                ],
                "restructured_zh": "修行者起烦恼，就应觉察。",
                "restructuring_operations": ["explicit_subject"],
                "sentence_units_zh": ["修行者起烦恼，就应觉察。"],
                "subject_strategy": {
                    "mode": "contextual_subject",
                    "evidence_status": "contextual_inference",
                    "subject_zh": "修行者",
                    "antecedent_zh": "修行者应观察自心",
                    "evidence_index": 0,
                },
                "typed_changes": [{
                    "change": "addition",
                    "operation": "explicit_subject",
                    "source_zh": None,
                    "restructured_zh": "修行者",
                    "evidence_status": "contextual_inference",
                    "basis_zh": "起烦恼",
                    "evidence_index": 0,
                }],
            },
            {
                "paragraph_id": "L3",
                "analysis_evidence": [{
                    "kind": "logic",
                    "source_analysis_field": "relations[0]",
                    "exact_quote": "勤修，得乐",
                }],
                "restructured_zh": "勤修，因此得乐。",
                "restructuring_operations": ["explicit_logic"],
                "sentence_units_zh": ["勤修，因此得乐。"],
                "subject_strategy": {
                    "mode": "not_applicable",
                    "evidence_status": "not_applicable",
                    "subject_zh": None,
                    "antecedent_zh": None,
                    "evidence_index": None,
                },
                "typed_changes": [{
                    "change": "addition",
                    "operation": "explicit_logic",
                    "source_zh": None,
                    "restructured_zh": "因此",
                    "evidence_status": "contextual_inference",
                    "basis_zh": "得乐",
                    "evidence_index": 0,
                }],
            },
        ]
    }
    artifact = hydrate_proposal(project, proposal)
    write_artifact(project, artifact)
    return artifact
def write_artifact(project: Path, artifact: dict[str, Any]) -> None:
    atomic_json(project / ARTIFACT_NAME, artifact)
def _blocked_case(project: Path, artifact: dict[str, Any], label: str, mutate: Any) -> dict[str, Any]:
    changed = copy.deepcopy(artifact)
    mutate(changed)
    write_artifact(project, changed)
    try:
        validate_project(project)
    except StrategyT1Error:
        return {"case": label, "passed": True, "blocked": True}
    raise StrategyT1Error(f"semantic restructuring contract did not block: {label}")
def run_contract_tests(root: Path) -> dict[str, Any]:
    """Run small disposable mechanical contract tests and retain the report."""
    try:
        import yaml  # noqa: F401
    except ImportError as exc:
        raise StrategyT1Error("T1.1.2 semantic restructuring requires Python PyYAML") from exc
    cases: list[dict[str, Any]] = []
    with tempfile.TemporaryDirectory(prefix="mpi-t112-restructuring-") as directory:
        project = Path(directory)
        artifact = fixture_artifact(project)
        validate_project(project)
        cases.append({"case": "valid_lightweight_artifact", "passed": True})
        cases.append(_blocked_case(project, artifact, "stale_source_hash", lambda x: x.__setitem__("source_sha256", "0" * 64)))
        cases.append(_blocked_case(project, artifact, "stale_analysis_record_binding", lambda x: x["records"][0].__setitem__("source_analysis_record_sha256", "0" * 64)))
        cases.append(_blocked_case(project, artifact, "analysis_quote_not_exact", lambda x: x["records"][0]["analysis_evidence"][0].__setitem__("exact_quote", "模型自己解释")))
        cases.append(_blocked_case(project, artifact, "unaccounted_cjk_addition", lambda x: x["records"][0].__setitem__("restructured_zh", "我们" + x["records"][0]["restructured_zh"])))
        cases.append(_blocked_case(project, artifact, "sentence_units_do_not_reconstruct", lambda x: x["records"][0].__setitem__("sentence_units_zh", ["不完整"])))
        cases.append(_blocked_case(project, artifact, "protected_term_count_changed", lambda x: x["records"][0].__setitem__("restructured_zh", x["records"][0]["restructured_zh"].replace("无自性", "固定本质"))))
        cases.append(_blocked_case(project, artifact, "question_scope_changed", lambda x: x["records"][0].__setitem__("restructured_zh", x["records"][0]["restructured_zh"] + "？")))
        neutral_subject = {
            "mode": "not_applicable", "evidence_status": "not_applicable",
            "subject_zh": None, "antecedent_zh": None, "evidence_index": None,
        }
        zero_reference = {
            "change": "addition", "operation": "explicit_reference", "source_zh": None,
            "restructured_zh": "佛陀", "evidence_status": "contextual_inference",
            "basis_zh": "佛陀受到供养", "evidence_index": 0,
        }
        zero_evidence = [{
            "kind": "reference", "source_analysis_field": "references",
            "source_analysis_value_sha256": "0" * 64,
            "exact_quote": "佛陀不是本句省略成分，也不是本句指代对象",
        }]
        try:
            validate_typed_changes(
                [zero_reference], zero_evidence, neutral_subject, "应当修行。",
                "佛陀应当修行。", "佛陀受到供养。", ["explicit_reference"], "L2",
            )
        except StrategyT1Error:
            cases.append({"case": "zero_reference_cannot_bypass_subject_strategy", "passed": True, "blocked": True})
        else:
            raise StrategyT1Error("semantic restructuring contract did not block: zero_reference_cannot_bypass_subject_strategy")
        logic_change = {
            "change": "addition", "operation": "explicit_logic", "source_zh": None,
            "restructured_zh": "因此", "evidence_status": "explicit",
            "basis_zh": "得乐", "evidence_index": 0,
        }
        logic_evidence = [{
            "kind": "logic", "source_analysis_field": "logic_and_scope",
            "source_analysis_value_sha256": "0" * 64,
            "exact_quote": "“勤修”为原因，“得乐”为因果结果",
        }]
        validate_typed_changes(
            [logic_change], logic_evidence, neutral_subject, "勤修，得乐。",
            "勤修，因此得乐。", "", ["explicit_logic"], "L1",
        )
        validate_lexical_conservation(
            "勤修，得乐。", "勤修，因此得乐。", [logic_change], ["explicit_logic"], "L1"
        )
        validate_visible_logic_and_negation(
            "勤修，得乐。", "勤修，因此得乐。", [logic_change], "L1"
        )
        cases.append({"case": "positive_evidence_bound_logic_addition", "passed": True})
        denied_logic = copy.deepcopy(logic_evidence)
        denied_logic[0]["exact_quote"] = "“勤修”与“得乐”只是并列，不是因果，不得补因此"
        try:
            validate_typed_changes(
                [logic_change], denied_logic, neutral_subject, "勤修，得乐。",
                "勤修，因此得乐。", "", ["explicit_logic"], "L1",
            )
        except StrategyT1Error:
            cases.append({"case": "negative_logic_evidence_cannot_authorize_addition", "passed": True, "blocked": True})
        else:
            raise StrategyT1Error("semantic restructuring contract did not block: negative_logic_evidence")
        try:
            validate_typed_changes(
                [{**logic_change, "basis_zh": "乐"}], logic_evidence, neutral_subject,
                "勤修，得乐。", "勤修，得因此乐。", "", ["explicit_logic"], "L1",
            )
        except StrategyT1Error:
            cases.append({"case": "truncated_logic_basis_cannot_move_connector_inside_clause", "passed": True, "blocked": True})
        else:
            raise StrategyT1Error("semantic restructuring contract did not block: truncated_logic_basis")
        uncertain_logic = copy.deepcopy(logic_evidence)
        uncertain_logic[0]["exact_quote"] = "据说得乐是因果结果或原因，尚待讨论？"
        try:
            validate_typed_changes(
                [logic_change], uncertain_logic, neutral_subject, "勤修，得乐。",
                "勤修，因此得乐。", "", ["explicit_logic"], "L1",
            )
        except StrategyT1Error:
            cases.append({"case": "uncertain_or_question_logic_evidence_cannot_authorize", "passed": True, "blocked": True})
        else:
            raise StrategyT1Error("semantic restructuring contract did not block: uncertain_logic_evidence")
        try:
            _evidence_from_proposal(
                {
                    "kind": "logic", "source_analysis_field": "logic_and_scope",
                    "exact_quote": "得乐为因果结果",
                },
                {"logic_and_scope": "得乐为因果结果的判断不成立，本句只是并列"},
                "contract.evidence",
            )
        except StrategyT1Error:
            cases.append({"case": "truncated_evidence_scalar_cannot_hide_negative_context", "passed": True, "blocked": True})
        else:
            raise StrategyT1Error("semantic restructuring contract did not block: truncated_evidence_scalar")
        parallel_change = {
            "change": "addition", "operation": "parallelism", "source_zh": None,
            "restructured_zh": "要", "evidence_status": "explicit",
            "basis_zh": "慈悲", "evidence_index": 0,
        }
        parallel_evidence = [{
            "kind": "structure", "source_analysis_field": "ellipsis_or_ambiguity",
            "source_analysis_value_sha256": "0" * 64,
            "exact_quote": "两项并列；第二项“慈悲”承前省略“要”，可在“慈悲”前补“要”",
        }]
        validate_typed_changes(
            [parallel_change], parallel_evidence, neutral_subject,
            "对自己要诚实，对他人慈悲。", "对自己要诚实，对他人要慈悲。", "",
            ["parallelism"], "L1",
        )
        validate_lexical_conservation(
            "对自己要诚实，对他人慈悲。", "对自己要诚实，对他人要慈悲。",
            [parallel_change], ["parallelism"], "L1",
        )
        cases.append({"case": "positive_evidence_bound_parallel_completion", "passed": True})
        try:
            validate_typed_changes(
                [{**parallel_change, "basis_zh": "悲"}], parallel_evidence, neutral_subject,
                "对自己要诚实，对他人慈悲。", "对自己要诚实，对他人慈要悲。", "",
                ["parallelism"], "L1",
            )
        except StrategyT1Error:
            cases.append({"case": "truncated_parallel_basis_cannot_move_shared_text_inside_member", "passed": True, "blocked": True})
        else:
            raise StrategyT1Error("semantic restructuring contract did not block: truncated_parallel_basis")
        write_artifact(project, artifact)
        warning = length_warning("L1", "短句", "这是一个明显更长且只用于比例诊断的句子")
        if not warning or warning["blocking"] is not False:
            raise StrategyT1Error("length ratio warning became a blocking gate")
        cases.append({"case": "length_ratio_warning_nonblocking", "passed": True})
        structured_project = project / "locked-structured"
        structured_artifact = fixture_structured_artifact(structured_project)
        structured_report = validate_project(structured_project)
        if structured_report.get("analysis_schema_mode") != "locked_structured":
            raise StrategyT1Error("locked structured fixture used the wrong analysis mode")
        cases.append({
            "case": "locked_structured_subject_and_logic_projection",
            "passed": True,
        })
        cases.append(_blocked_case(
            structured_project,
            structured_artifact,
            "locked_structured_top_level_fallback_rejected",
            lambda x: x["records"][0]["analysis_evidence"][0].__setitem__(
                "source_analysis_field", "references_and_ellipsis"
            ),
        ))
        cases.append(_blocked_case(
            structured_project,
            structured_artifact,
            "locked_structured_subject_plan_and_change_cannot_cross_bind",
            lambda x: x["records"][0]["typed_changes"][0].__setitem__(
                "evidence_index", 1
            ),
        ))
        structured_analysis_path = structured_project / ANALYSIS_NAME
        structured_analysis = load_json(structured_analysis_path)
        injected_analysis = copy.deepcopy(structured_analysis)
        injected_analysis["paragraphs"][0]["logic_and_scope"] = (
            "旧式顶层证据不得混入 locked structured 记录"
        )
        atomic_json(structured_analysis_path, injected_analysis)
        try:
            project_context(structured_project)
        except StrategyT1Error:
            cases.append({
                "case": "locked_structured_legacy_evidence_injection_rejected",
                "passed": True,
                "blocked": True,
            })
        else:
            raise StrategyT1Error(
                "semantic restructuring contract did not block: "
                "locked_structured_legacy_evidence_injection"
            )
        atomic_json(structured_analysis_path, structured_analysis)
        write_artifact(structured_project, structured_artifact)
        try:
            _evidence_from_proposal(
                {
                    "kind": "logic",
                    "source_analysis_field": "logic_and_scope",
                    "exact_quote": "“勤修”为原因，“得乐”为因果结果",
                },
                {
                    "logic_and_scope": [
                        "“勤修”为原因，“得乐”为因果结果",
                        "上述因果关系不成立",
                    ]
                },
                "contract.legacy_nested_evidence",
            )
        except StrategyT1Error:
            cases.append({
                "case": "legacy_nested_sibling_cannot_authorize",
                "passed": True,
                "blocked": True,
            })
        else:
            raise StrategyT1Error(
                "semantic restructuring contract did not block: "
                "legacy_nested_sibling_evidence"
            )
        legacy = project / "legacy"
        legacy.mkdir()
        legacy_records = semantic_bridge_legacy.fixture_records(legacy)
        for name, values in legacy_records.items():
            semantic_bridge_legacy.write_jsonl(legacy / name, values)
        validate_legacy_project(legacy)
        cases.append({"case": "legacy_1_1_1_read_only_delegate", "passed": True})
    report = {
        "schema_version": 1,
        "workflow_version": WORKFLOW_VERSION,
        "status": "PASS",
        "created_at": utc_now(),
        "cases": cases,
        "mechanical_scope_only": True,
    }
    root = root.expanduser().resolve()
    root.mkdir(parents=True, exist_ok=True)
    output = root / "semantic-restructuring-contract-report.json"
    atomic_json(output, report)
    report["report_absolute_path"] = str(output)
    report["report_sha256"] = sha256_file(output)
    return report
def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    validate = sub.add_parser("validate")
    validate.add_argument("--project", type=Path, required=True)
    validate.add_argument("--artifact", type=Path)
    legacy = sub.add_parser("validate-legacy")
    legacy.add_argument("--project", type=Path, required=True)
    legacy.add_argument(
        "--stage",
        choices=("risk", "bridge", "review", "decisions", "coverage", "regression", "all"),
        default="all",
    )
    contracts = sub.add_parser("contract-tests")
    contracts.add_argument("--output-root", type=Path, required=True)
    args = parser.parse_args()
    try:
        if args.command == "validate":
            result = validate_project(args.project, artifact_path=args.artifact)
        elif args.command == "validate-legacy":
            result = validate_legacy_project(args.project, args.stage)
        else:
            result = run_contract_tests(args.output_root)
    except StrategyT1Error as exc:
        print(json.dumps({"ok": False, "status": "BLOCKED", "error": str(exc)}, ensure_ascii=False, indent=2))
        return 2
    print(json.dumps({"ok": True, "result": result}, ensure_ascii=False, indent=2))
    return 0
if __name__ == "__main__":
    raise SystemExit(main())
