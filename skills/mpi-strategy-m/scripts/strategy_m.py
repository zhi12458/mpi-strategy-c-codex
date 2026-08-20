#!/usr/bin/env python3
"""Install and execute the audited MPI Strategy M state machine."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
import uuid
from pathlib import Path

from bootstrap import install
from runtime import (
    INSTRUCTION_RECEIPT_NAME,
    MANIFEST_NAME,
    RECEIPTS_NAME,
    StrategyMError,
    append_receipt,
    atomic_json,
    begin_project,
    file_hashes,
    load_json,
    load_lock,
    managed_root,
    read_receipts,
    reject_secret_arguments,
    run,
    sha256_bytes,
    sha256_file,
    validate_instruction_receipt,
    verify_ready,
)


STAGE_SCRIPTS = {
    "source_extraction": {"source2dj.py", "docx2dj.py"},
    "terminology": {"build-term-map.py"},
    "flash_analysis": {"deepseek-source-analysis.py"},
    "target_freeze": {"freeze-target.py"},
    "bilingual_1": {"gen-bilingual.py"},
    "pro_review_1": {"deepseek-review.py"},
    "target_accuracy_refreeze": {"freeze-target.py"},
    "bilingual_2": {"gen-bilingual.py"},
    "target_concision_refreeze": {"freeze-target.py"},
    "bilingual_final": {"gen-bilingual.py"},
    "pro_review_2": {"deepseek-review.py"},
    "translation_qa": {"check-translation.py"},
    "target_docx": {"dj2docx.py"},
    "bilingual_docx": {"dj2docx.py"},
    "target_docx_qa": {"check-docx.py"},
    "bilingual_docx_qa": {"check-docx.py"},
    "subtitle_na": {"check-subtitles.py"},
    "subtitle_generation": {"gen-subtitles.py"},
    "subtitle_qa": {"check-subtitles.py"},
}
DOCUMENT_STAGES = {
    "source_extraction", "terminology", "terminology_search", "terminology_decisions", "flash_analysis", "allusion_research", "target_freeze",
    "bilingual_1", "pro_review_1", "target_accuracy_refreeze", "bilingual_2",
    "target_concision_refreeze", "bilingual_final",
    "pro_review_2", "translation_qa", "target_docx", "bilingual_docx",
    "target_docx_qa", "bilingual_docx_qa", "subtitle_na",
}
MEDIA_STAGES = (DOCUMENT_STAGES - {"subtitle_na"}) | {"media_transcription", "subtitle_generation", "subtitle_qa"}
REQUIRED_MODEL_STAGES = {
    "flash_model", "sol_translation", "pro_model_1",
    "sol_accuracy_revision", "sol_concision", "pro_model_2",
}
OPTIONAL_MODEL_STAGES = {"sol_fallback"}
MODEL_STAGES = REQUIRED_MODEL_STAGES | OPTIONAL_MODEL_STAGES
TERM_TRIGGERS = {"mpi_missing", "mpi_conflict", "context_ambiguity", "high_risk", "model_uncertain"}
MPI_TERM_SOURCES = {"DoT定稿", "内部特色词", "佛教术语", "经论名"}
EXTERNAL_TERM_SOURCES = {"cbeta", "bdk", "nti_reader", "84000", "academic", "university", "buddhist_institution"}
STRUCTURAL_RE = re.compile(r"\{#[^{}]*\}|\(\s*#?[^{}\n]*\)")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
PARAGRAPH_ID_RE = re.compile(r"^L[1-9][0-9]*$")
TOOL_DIAGNOSTIC_PREFIX = b"diagnostic-json:"
TOOL_DIAGNOSTIC_CODES = {
    "deepseek_completion_recovery",
    "deepseek_http_transient",
    "deepseek_rate_limit",
    "deepseek_source_analysis_validation",
    "deepseek_transport_failure",
}
TOOL_DIAGNOSTIC_COMPONENTS = {
    "core",
    "temporal",
    "operator_negation_modality",
    "operator_quantity_degree",
    "operator_tense_aspect_other",
    "reference",
    "constraints",
}
TOOL_DIAGNOSTIC_KEYS = {
    "schema_version",
    "code",
    "retryable",
    "component",
    "paragraph_id",
    "fallback",
    "transport_kind",
    "http_status",
    "finish_reason",
    "reasoning_bytes",
    "completion_tokens",
    "field",
    "category",
}
TOOL_VALIDATION_FIELD_RE = re.compile(
    r"^[a-z_]+(?:\[[0-9]+\])?(?:\.[a-z_]+(?:\[[0-9]+\])?)*$"
)
TOOL_VALIDATION_FIELD_SEGMENTS = {
    "candidate_referents",
    "canonical_meaning",
    "clause",
    "competing_interpretations",
    "competing_senses",
    "contextual_meaning",
    "counterevidence",
    "cultural_allusions",
    "elliptical_subject",
    "event_or_scope",
    "evidence",
    "evidence_status",
    "expression",
    "external_research_required",
    "interpretation",
    "kind",
    "linked_event",
    "marker",
    "must_not_invent",
    "must_preserve",
    "notes",
    "operators",
    "paragraph_id",
    "participant",
    "participants",
    "predicate",
    "predicates",
    "reference",
    "references_and_ellipsis",
    "referent",
    "relation",
    "relations",
    "research_trigger",
    "role",
    "role_bindings",
    "scope",
    "source_clause",
    "source_or_origin",
    "status",
    "subject_evidence",
    "subject_resolution",
    "supporting_evidence",
    "target_clause",
    "temporal_relations",
    "translation_constraint",
    "type",
}
TOOL_VALIDATION_CATEGORIES = {
    "item_limit",
    "minimum_length",
    "maximum_length",
    "invalid_format",
    "minimum_value",
    "exclusive_minimum",
    "nonverbatim_evidence",
    "analysis_language",
    "null_explicit_participant",
    "null_explicit_referent",
    "explicit_role_evidence",
    "explicit_relation_evidence",
    "explicit_operator_marker",
    "explicit_reference_evidence",
    "participant_evidence_support",
    "temporal_relation_coverage",
    "temporal_preservation_coverage",
    "causal_role_promotion",
    "actor_state_holder_coverage",
    "compressed_clause_coverage",
    "causal_role_separation",
    "known_allusion_coverage",
    "allusion_preservation_coverage",
    "field_validation",
}


def safe_validation_field(field: object) -> bool:
    if not isinstance(field, str) or TOOL_VALIDATION_FIELD_RE.fullmatch(field) is None:
        return False
    return all(
        re.sub(r"\[[0-9]+\]$", "", segment) in TOOL_VALIDATION_FIELD_SEGMENTS
        for segment in field.split(".")
    )


def safe_tool_diagnostics(stderr: bytes) -> list[dict]:
    """Extract only strict, provider-body-free diagnostics emitted by locked tools."""
    diagnostics: list[dict] = []
    for line in stderr.splitlines():
        if not line.startswith(TOOL_DIAGNOSTIC_PREFIX) or len(line) > 2048:
            continue
        try:
            value = json.loads(line[len(TOOL_DIAGNOSTIC_PREFIX) :].decode("ascii"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            continue
        if not isinstance(value, dict) or not set(value) <= TOOL_DIAGNOSTIC_KEYS:
            continue
        code = value.get("code")
        if value.get("schema_version") != 1 or code not in TOOL_DIAGNOSTIC_CODES:
            continue
        if code == "deepseek_source_analysis_validation":
            paragraph_id = value.get("paragraph_id")
            field = value.get("field")
            category = value.get("category")
            if (
                value.get("retryable") is not False
                or not isinstance(paragraph_id, str)
                or PARAGRAPH_ID_RE.fullmatch(paragraph_id) is None
                or not safe_validation_field(field)
                or category not in TOOL_VALIDATION_CATEGORIES
                or set(value)
                != {
                    "schema_version",
                    "code",
                    "retryable",
                    "paragraph_id",
                    "field",
                    "category",
                }
            ):
                continue
            diagnostics.append(value)
            continue
        if value.get("retryable") is not True:
            continue
        component = value.get("component")
        paragraph_id = value.get("paragraph_id")
        fallback = value.get("fallback")
        transport_kind = value.get("transport_kind")
        finish_reason = value.get("finish_reason")
        http_status = value.get("http_status")
        reasoning_bytes = value.get("reasoning_bytes")
        completion_tokens = value.get("completion_tokens")
        if component is not None and component not in TOOL_DIAGNOSTIC_COMPONENTS:
            continue
        if paragraph_id is not None and (
            not isinstance(paragraph_id, str)
            or PARAGRAPH_ID_RE.fullmatch(paragraph_id) is None
        ):
            continue
        if fallback is not None and fallback != "single-paragraph":
            continue
        if transport_kind is not None and transport_kind not in {
            "connection",
            "network",
            "timeout",
            "tls",
        }:
            continue
        if finish_reason is not None and finish_reason not in {"length", "stop"}:
            continue
        if http_status is not None and (
            not isinstance(http_status, int)
            or isinstance(http_status, bool)
            or not 100 <= http_status <= 599
        ):
            continue
        for number in (reasoning_bytes, completion_tokens):
            if number is not None and (
                not isinstance(number, int) or isinstance(number, bool) or number < 0
            ):
                break
        else:
            diagnostics.append(value)
    return diagnostics


def safe_receipt_base(stage: str, started: float, command: list[str], cwd: Path) -> dict:
    return {
        "schema_version": 1,
        "receipt_id": str(uuid.uuid4()),
        "workflow_stage": stage,
        "started_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(started)),
        "cwd": str(cwd.resolve()),
        "command": command,
    }


def deepseek_environment() -> dict[str, str]:
    try:
        import keyring
    except ImportError as exc:
        raise StrategyMError("Python keyring is required") from exc
    secret = keyring.get_password("mpi-strategy-m-deepseek", "default")
    if not secret:
        raise StrategyMError("DeepSeek credential is missing from the operating-system vault")
    return {"DEEPSEEK_API_KEY": secret}


def expected_paragraph_ids(source: Path) -> tuple[str, ...]:
    return tuple(
        f"L{index}"
        for index, line in enumerate(source.read_text(encoding="utf-8").splitlines(), start=1)
        if line.strip()
    )


def validate_source_analysis_contract(source: Path, analysis: Path) -> dict:
    value = load_json(analysis)
    expected = load_lock()["models"]["source_analysis"]
    configuration = value.get("configuration")
    paragraphs = value.get("paragraphs")
    if value.get("schema_version") != 3:
        raise StrategyMError("source-analysis schema_version 3 is required")
    if value.get("source_sha256") != sha256_file(source):
        raise StrategyMError("source-analysis source SHA-256 is stale")
    if (
        value.get("provider") != expected["provider"]
        or value.get("model") != expected["model"]
        or not isinstance(configuration, dict)
        or configuration.get("reasoning_effort") != expected["reasoning_effort"]
    ):
        raise StrategyMError("source-analysis model identity does not match the release lock")
    if not isinstance(paragraphs, list):
        raise StrategyMError("source-analysis paragraphs are missing")
    paragraph_ids = []
    for paragraph in paragraphs:
        if not isinstance(paragraph, dict) or not {
            "paragraph_id", "temporal_relations", "elliptical_subject",
            "cultural_allusions", "must_preserve"
        } <= set(paragraph):
            raise StrategyMError("source-analysis semantic gates are missing")
        paragraph_ids.append(paragraph["paragraph_id"])
    if tuple(paragraph_ids) != expected_paragraph_ids(source):
        raise StrategyMError("source-analysis paragraph coverage is incomplete")
    return value


def validate_semantic_review_contract(source: Path, certificate_path: Path) -> dict:
    value = load_json(certificate_path)
    audits = value.get("paragraph_audits")
    if value.get("schema_version") != 3 or not isinstance(audits, list):
        raise StrategyMError("semantic-review schema_version 3 paragraph audits are required")
    audit_ids = []
    required = {
        "paragraph_id", "temporal_relations", "conditions", "negation", "degree",
        "elliptical_subject", "cultural_allusions", "semantic_roles",
        "actor_or_state_holder", "cause_or_instrument",
        "allusion_or_quotation", "finding_ids",
    }
    for audit in audits:
        if not isinstance(audit, dict) or set(audit) != required:
            raise StrategyMError("semantic-review paragraph audit is incomplete")
        audit_ids.append(audit["paragraph_id"])
    if tuple(audit_ids) != expected_paragraph_ids(source):
        raise StrategyMError("semantic-review paragraph audits do not cover the frozen source")
    return value


def run_audited_tool(project: Path, stage: str, script_name: str, arguments: list[str], inputs: list[Path], outputs: list[Path]) -> dict:
    verify_ready()
    instruction = validate_instruction_receipt(project)
    if stage not in STAGE_SCRIPTS or script_name not in STAGE_SCRIPTS[stage]:
        raise StrategyMError(f"script {script_name} is not allowed for stage {stage}")
    reject_secret_arguments(arguments)
    toolkit_info = instruction["translation_toolkit"]
    toolkit = Path(toolkit_info["absolute_path"])
    script = (toolkit / "scripts" / script_name).resolve()
    expected_hash = toolkit_info["critical_file_sha256"].get(f"scripts/{script_name}")
    if not script.is_file() or not expected_hash or sha256_file(script) != expected_hash:
        raise StrategyMError("locked toolkit script is missing or changed")
    if stage == "flash_analysis" and (project / "target.dj").exists():
        raise StrategyMError("Flash analysis must run before target.dj exists")
    if stage.startswith("pro_review") and any("source-analysis" in value for value in arguments):
        raise StrategyMError("Pro review must not receive Flash source analysis")
    command = [sys.executable, str(script), *arguments]
    started = time.time()
    receipt = safe_receipt_base(stage, started, command, project)
    receipt.update({
        "owner_repository": toolkit_info,
        "script_absolute_path": str(script),
        "script_sha256": expected_hash,
        "arguments": arguments,
        "inputs": file_hashes(inputs),
    })
    environment = deepseek_environment() if script_name in {"deepseek-source-analysis.py", "deepseek-review.py"} else None
    try:
        completed = run(command, project, env=environment)
    finally:
        if environment is not None:
            environment.pop("DEEPSEEK_API_KEY", None)
    finished = time.time()
    stderr_diagnostics = safe_tool_diagnostics(completed.stderr)
    receipt.update({
        "finished_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(finished)),
        "duration_seconds": round(finished - started, 6),
        "exit_code": completed.returncode,
        "stdout_sha256": sha256_bytes(completed.stdout),
        "stderr_sha256": sha256_bytes(completed.stderr),
        "stdout_summary": {"bytes": len(completed.stdout), "lines": completed.stdout.count(b"\n")},
        "stderr_summary": {"bytes": len(completed.stderr), "lines": completed.stderr.count(b"\n")},
        "stderr_diagnostics": stderr_diagnostics,
        "outputs": file_hashes(outputs, require=False),
    })
    append_receipt(project, receipt)
    if completed.returncode:
        context = ""
        if stderr_diagnostics:
            diagnostic = stderr_diagnostics[-1]
            location = "/".join(
                str(diagnostic[key])
                for key in ("component", "paragraph_id")
                if key in diagnostic
            )
            context = f" ({diagnostic['code']}" + (
                f" at {location})" if location else ")"
            )
        raise StrategyMError(
            f"toolkit stage {stage} failed with exit code {completed.returncode}{context}"
        )
    if len(receipt["outputs"]) != len(outputs):
        raise StrategyMError(f"toolkit stage {stage} did not produce every declared output")
    for output in outputs:
        if output.stat().st_mtime + 1 < started:
            raise StrategyMError(f"toolkit stage {stage} produced a stale output")
    if stage == "flash_analysis":
        analyses = [path for path in outputs if path.name == "source-analysis.json"]
        if len(analyses) != 1:
            raise StrategyMError("flash_analysis must declare source-analysis.json")
        validate_source_analysis_contract(project / "source.dj", analyses[0])
    if stage in {"pro_review_1", "pro_review_2"}:
        certificates = [path for path in outputs if path.name == "semantic-review.json"]
        if len(certificates) != 1:
            raise StrategyMError(f"{stage} must declare semantic-review.json")
        validate_semantic_review_contract(project / "source.dj", certificates[0])
    if stage == "terminology":
        receipt_files = [path for path in outputs if path.name == "term-search-receipts.jsonl"]
        if len(receipt_files) != 1:
            raise StrategyMError("terminology stage must declare term-search-receipts.jsonl as an output")
        rows = []
        for line in receipt_files[0].read_text(encoding="utf-8").splitlines():
            if line.strip():
                try:
                    rows.append(json.loads(line))
                except json.JSONDecodeError as exc:
                    raise StrategyMError("toolkit term-search receipt is invalid") from exc
        if not rows:
            raise StrategyMError("MPI terminology search was not actually called")
        search_script = toolkit / "terms-database" / "search.py"
        search_hash = toolkit_info["critical_file_sha256"].get("terms-database/search.py")
        database = toolkit / "terms-database" / "termlib.sqlite"
        for row in rows:
            if row.get("search_script") != str(search_script.resolve()) or row.get("search_script_sha256") != search_hash or row.get("exit_code") != 0:
                raise StrategyMError("MPI term-search child receipt does not match the locked toolkit")
            child_arguments = row.get("arguments")
            if not isinstance(child_arguments, list) or len(child_arguments) < 3:
                raise StrategyMError("MPI term-search child receipt omitted its full arguments")
            child = {
                "schema_version": 1,
                "receipt_id": str(uuid.uuid4()),
                "parent_receipt_id": receipt["receipt_id"],
                "workflow_stage": "terminology_search",
                "started_at": row.get("started_at"),
                "finished_at": row.get("finished_at"),
                "cwd": str(project),
                "command": [sys.executable, str(search_script), *child_arguments],
                "owner_repository": toolkit_info,
                "script_absolute_path": str(search_script),
                "script_sha256": search_hash,
                "arguments": child_arguments,
                "inputs": file_hashes([database]),
                "outputs": [],
                "exit_code": 0,
                "stdout_sha256": row.get("stdout_sha256"),
                "stdout_summary": {"result_count": row.get("result_count")},
                "stderr_sha256": sha256_bytes(b""),
                "stderr_summary": {"bytes": 0, "lines": 0},
            }
            append_receipt(project, child)
    return receipt


def record_model(project: Path, stage: str, provider: str, model: str, effort: str, prompt_sha256: str, inputs: list[Path], outputs: list[Path], metadata: Path | None) -> dict:
    verify_ready()
    validate_instruction_receipt(project)
    if stage not in MODEL_STAGES or len(prompt_sha256) != 64:
        raise StrategyMError("invalid model stage or prompt SHA-256")
    lock = load_lock()["models"]
    if stage == "flash_model":
        role = "source_analysis"
    elif stage.startswith("pro_model"):
        role = "review"
    elif stage == "sol_fallback":
        role = "translation_fallback"
    else:
        role = "translation"
    expected = lock[role]
    if (provider, model, effort) != (expected["provider"], expected["model"], expected["reasoning_effort"]):
        raise StrategyMError("model identity or reasoning effort does not match the release lock")
    successful = {
        item.get("workflow_stage")
        for item in read_receipts(project)
        if item.get("exit_code", 0) == 0
    }
    prerequisites = {
        "sol_translation": (
            {"flash_model", "allusion_research"},
            {"flash_analysis_reuse", "allusion_research"},
        ),
        "pro_model_1": ({"sol_translation", "pro_review_1"},),
        "sol_accuracy_revision": ({"pro_model_1"},),
        "sol_concision": ({"sol_accuracy_revision"},),
        "pro_model_2": ({"sol_concision", "pro_review_2"},),
    }
    alternatives = prerequisites.get(stage)
    if alternatives and not any(required <= successful for required in alternatives):
        raise StrategyMError(f"model stage {stage} is out of order")
    if stage == "sol_translation":
        resolved_inputs = {path.expanduser().resolve() for path in inputs}
        required_inputs = {
            (project / "source.dj").resolve(),
            (project / "source-analysis.json").resolve(),
            (project / "term-map.yaml").resolve(),
            (project / "allusion-decisions.json").resolve(),
        }
        if not required_inputs <= resolved_inputs:
            raise StrategyMError(
                "Sol translation must read frozen source, term map, Flash analysis, and allusion decisions"
            )
        decisions_path = (project / "allusion-decisions.json").resolve()
        decisions_hash = sha256_file(decisions_path)
        allusion_evidence_is_current = any(
            receipt.get("workflow_stage") == "allusion_research"
            and any(
                output.get("absolute_path") == str(decisions_path)
                and output.get("sha256") == decisions_hash
                for output in receipt.get("outputs", [])
            )
            for receipt in read_receipts(project)
        )
        if not allusion_evidence_is_current:
            raise StrategyMError("Sol translation requires current receipted allusion decisions")
    if stage == "sol_concision":
        input_names = {path.name for path in inputs}
        if "source.dj" not in input_names or not input_names.intersection({"sol-revised.dj", "target.dj"}):
            raise StrategyMError("Sol concision must recheck source.dj against the accuracy-revised English")
    if stage == "sol_fallback":
        second_review = project / "semantic-review.json"
        if "pro_model_2" not in successful or not second_review.is_file():
            raise StrategyMError("Sol high fallback requires a completed second Pro review")
        certificate = load_json(second_review)
        blocking = certificate.get("status") == "blocking" or int(certificate.get("blocking_findings", 0)) > 0
        if not blocking:
            raise StrategyMError("Sol high fallback is allowed only for remaining critical/major blockers")
        resolved_inputs = {path.expanduser().resolve() for path in inputs}
        if second_review.resolve() not in resolved_inputs:
            raise StrategyMError("Sol high fallback must be bound to semantic-review.json")
    raw_metadata = load_json(metadata) if metadata else {}
    allowed_metadata = {
        key: raw_metadata.get(key)
        for key in (
            "model_fingerprint", "input_tokens", "output_tokens", "reasoning_tokens",
            "cost", "currency", "retries", "duration_seconds", "request_id",
        )
    }
    receipt = {
        "schema_version": 1,
        "receipt_id": str(uuid.uuid4()),
        "workflow_stage": stage,
        "kind": "model",
        "recorded_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "provider": provider,
        "model": model,
        "reasoning_effort": effort,
        "prompt_sha256": prompt_sha256,
        "inputs": file_hashes(inputs),
        "outputs": file_hashes(outputs),
        "model_metadata": allowed_metadata,
    }
    append_receipt(project, receipt)
    return receipt


def source_text_sha256(lines: list[str], line_number: int) -> str:
    if line_number < 1 or line_number > len(lines):
        raise StrategyMError(f"term-decision line is outside source.dj: {line_number}")
    return sha256_bytes(lines[line_number - 1].encode("utf-8"))


def validate_term_decisions(source: Path, decisions: Path) -> dict:
    source = source.expanduser().resolve()
    decisions = decisions.expanduser().resolve()
    value = load_json(decisions)
    if value.get("schema_version") != 1:
        raise StrategyMError("term-decisions schema_version must be 1")
    current_source_hash = sha256_file(source)
    if value.get("source_sha256") != current_source_hash:
        raise StrategyMError("term-decisions source SHA-256 is stale")
    try:
        lines = source.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        raise StrategyMError(f"could not read frozen source: {source}") from exc
    items = value.get("items")
    if not isinstance(items, list):
        raise StrategyMError("term-decisions items must be an array")
    frozen = []
    human_review = []
    seen: set[tuple[str, tuple[int, ...]]] = set()
    for index, item in enumerate(items, start=1):
        if not isinstance(item, dict):
            raise StrategyMError(f"term-decisions item {index} must be an object")
        source_term = item.get("source_term")
        if not isinstance(source_term, str) or not source_term.strip():
            raise StrategyMError(f"term-decisions item {index} has no source_term")
        trigger = item.get("trigger")
        if trigger not in TERM_TRIGGERS:
            raise StrategyMError(f"term-decisions item {index} has an invalid trigger")
        candidates = item.get("candidates")
        if not isinstance(candidates, list) or not candidates or not all(
            isinstance(candidate, str) and candidate.strip() for candidate in candidates
        ):
            raise StrategyMError(f"term-decisions item {index} has no candidate renderings")
        locations = item.get("locations")
        if not isinstance(locations, list) or not locations:
            raise StrategyMError(f"term-decisions item {index} has no source locations")
        line_numbers = []
        for location in locations:
            if not isinstance(location, dict) or not isinstance(location.get("line"), int):
                raise StrategyMError(f"term-decisions item {index} has an invalid source location")
            line_number = location["line"]
            line_numbers.append(line_number)
            if location.get("source_text_sha256") != source_text_sha256(lines, line_number):
                raise StrategyMError(f"term-decisions item {index} has stale context at line {line_number}")
        identity = (source_term, tuple(sorted(line_numbers)))
        if identity in seen:
            raise StrategyMError(f"duplicate term-decision for {source_term} at {line_numbers}")
        seen.add(identity)
        external_evidence = item.get("external_evidence", [])
        if not isinstance(external_evidence, list):
            raise StrategyMError(f"term-decisions item {index} external_evidence must be an array")
        for evidence in external_evidence:
            if not isinstance(evidence, dict) or evidence.get("source_type") not in EXTERNAL_TERM_SOURCES:
                raise StrategyMError(f"term-decisions item {index} has inadmissible external evidence")
            url = evidence.get("url")
            if not isinstance(url, str) or not url.startswith(("https://", "http://")):
                raise StrategyMError(f"term-decisions item {index} has an invalid evidence URL")
            if not isinstance(evidence.get("support"), str) or not evidence["support"].strip():
                raise StrategyMError(f"term-decisions item {index} has evidence without a support note")
        for field in ("rationale", "scope", "resolution_basis"):
            if not isinstance(item.get(field), str) or not item[field].strip():
                raise StrategyMError(f"term-decisions item {index} is missing {field}")
        confidence = item.get("confidence")
        if confidence not in {"high", "medium", "low"}:
            raise StrategyMError(f"term-decisions item {index} has invalid confidence")
        status = item.get("status")
        if status == "human_review":
            if confidence == "high":
                raise StrategyMError(f"term-decisions item {index} cannot be high-confidence human_review")
            human_review.append({"source_term": source_term, "lines": line_numbers})
            continue
        if status != "frozen" or confidence != "high":
            raise StrategyMError(f"term-decisions item {index} must be high-confidence frozen or human_review")
        if not isinstance(item.get("selected"), str) or not item["selected"].strip():
            raise StrategyMError(f"term-decisions item {index} is missing selected")
        if item["resolution_basis"] == "mpi_authoritative":
            mpi_hits = item.get("mpi_hits")
            if not isinstance(mpi_hits, list) or not any(
                isinstance(hit, dict) and hit.get("source") in MPI_TERM_SOURCES for hit in mpi_hits
            ):
                raise StrategyMError(f"term-decisions item {index} lacks an authoritative MPI hit")
        elif not item.get("external_evidence"):
            raise StrategyMError(f"term-decisions item {index} requires external evidence before freezing")
        frozen.append({"source_term": source_term, "selected": item["selected"], "lines": line_numbers})
    return {
        "source_sha256": current_source_hash,
        "item_count": len(items),
        "frozen_count": len(frozen),
        "human_review_count": len(human_review),
        "frozen": frozen,
        "human_review": human_review,
    }


def source_analysis_allusions(source: Path, analysis: Path) -> list[dict]:
    """Return every Flash-declared cultural expression bound to frozen source bytes."""
    value = validate_source_analysis_contract(source, analysis)
    lines = source.read_text(encoding="utf-8").splitlines()
    allusions: list[dict] = []
    seen: set[tuple[str, str]] = set()
    for paragraph in value["paragraphs"]:
        paragraph_id = paragraph["paragraph_id"]
        if not isinstance(paragraph_id, str) or re.fullmatch(r"L[1-9][0-9]*", paragraph_id) is None:
            raise StrategyMError("source-analysis cultural allusion has an invalid paragraph_id")
        line_number = int(paragraph_id[1:])
        if line_number > len(lines):
            raise StrategyMError("source-analysis cultural allusion is outside source.dj")
        line = lines[line_number - 1]
        for allusion in paragraph["cultural_allusions"]:
            expression = allusion.get("expression") if isinstance(allusion, dict) else None
            if not isinstance(expression, str) or not expression or expression not in line:
                raise StrategyMError("source-analysis cultural allusion lacks verbatim source evidence")
            identity = (paragraph_id, expression)
            if identity in seen:
                raise StrategyMError("source-analysis contains a duplicate cultural allusion")
            seen.add(identity)
            allusions.append({
                "paragraph_id": paragraph_id,
                "line": line_number,
                "source_expression": expression,
                "source_text_sha256": sha256_bytes(line.encode("utf-8")),
                "research_trigger": allusion.get("research_trigger"),
                "contextual_meaning": allusion.get("contextual_meaning"),
                "translation_constraint": allusion.get("translation_constraint"),
            })
    return allusions


def load_external_lookup_receipts(path: Path, source: Path) -> dict[str, dict]:
    if not path.is_file():
        raise StrategyMError("external-lookup-receipts.jsonl is missing")
    current_source_hash = sha256_file(source)
    receipts: dict[str, dict] = {}
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            receipt = json.loads(line)
        except json.JSONDecodeError as exc:
            raise StrategyMError(
                f"external lookup receipt {line_number} is invalid JSON"
            ) from exc
        required = {
            "schema_version", "receipt_id", "source_sha256", "paragraph_id",
            "source_expression", "query", "url", "source_type", "title",
            "retrieved_at", "support", "content_sha256", "accepted",
        }
        if not isinstance(receipt, dict) or not required <= set(receipt):
            raise StrategyMError(f"external lookup receipt {line_number} is incomplete")
        receipt_id = receipt["receipt_id"]
        if receipt.get("schema_version") != 1 or not isinstance(receipt_id, str) or not receipt_id:
            raise StrategyMError(f"external lookup receipt {line_number} has invalid identity")
        if receipt_id in receipts:
            raise StrategyMError("external lookup receipts contain a duplicate receipt_id")
        if receipt["source_sha256"] != current_source_hash:
            raise StrategyMError("external lookup receipt source SHA-256 is stale")
        if receipt["source_type"] not in EXTERNAL_TERM_SOURCES:
            raise StrategyMError("external lookup receipt has an inadmissible source type")
        if not isinstance(receipt["url"], str) or not receipt["url"].startswith(("https://", "http://")):
            raise StrategyMError("external lookup receipt has an invalid URL")
        for field in (
            "paragraph_id", "source_expression", "query", "title", "retrieved_at", "support"
        ):
            if not isinstance(receipt[field], str) or not receipt[field].strip():
                raise StrategyMError(f"external lookup receipt has an empty {field}")
        if not isinstance(receipt["accepted"], bool):
            raise StrategyMError("external lookup receipt accepted must be boolean")
        if not isinstance(receipt["content_sha256"], str) or SHA256_RE.fullmatch(receipt["content_sha256"]) is None:
            raise StrategyMError("external lookup receipt has an invalid content SHA-256")
        receipts[receipt_id] = receipt
    return receipts


def validate_allusion_decisions(
    source: Path,
    analysis: Path,
    decisions: Path,
    lookup_receipts: Path,
) -> dict:
    source = source.expanduser().resolve()
    analysis = analysis.expanduser().resolve()
    for label, path in (
        ("source.dj", source),
        ("source-analysis.json", analysis),
        ("allusion-decisions.json", decisions.expanduser().resolve()),
        ("external-lookup-receipts.jsonl", lookup_receipts.expanduser().resolve()),
    ):
        if not path.is_file():
            raise StrategyMError(f"{label} is missing")
    decisions = decisions.expanduser().resolve()
    lookup_receipts = lookup_receipts.expanduser().resolve()
    value = load_json(decisions)
    current_source_hash = sha256_file(source)
    current_analysis_hash = sha256_file(analysis)
    if value.get("schema_version") != 1:
        raise StrategyMError("allusion-decisions schema_version must be 1")
    if value.get("source_sha256") != current_source_hash:
        raise StrategyMError("allusion-decisions source SHA-256 is stale")
    if value.get("source_analysis_sha256") != current_analysis_hash:
        raise StrategyMError("allusion-decisions source-analysis SHA-256 is stale")
    if value.get("lookup_receipts_sha256") != sha256_file(lookup_receipts):
        raise StrategyMError("allusion-decisions lookup receipt hash is stale")
    expected = source_analysis_allusions(source, analysis)
    expected_by_key = {
        (item["paragraph_id"], item["source_expression"]): item for item in expected
    }
    receipts = load_external_lookup_receipts(lookup_receipts, source)
    items = value.get("items")
    if not isinstance(items, list):
        raise StrategyMError("allusion-decisions items must be an array")
    seen: set[tuple[str, str]] = set()
    frozen: list[dict] = []
    human_review: list[dict] = []
    for index, item in enumerate(items, start=1):
        if not isinstance(item, dict):
            raise StrategyMError(f"allusion-decisions item {index} must be an object")
        key = (item.get("paragraph_id"), item.get("source_expression"))
        expected_item = expected_by_key.get(key)
        if expected_item is None or key in seen:
            raise StrategyMError(f"allusion-decisions item {index} is extra or duplicated")
        seen.add(key)
        if item.get("source_text_sha256") != expected_item["source_text_sha256"]:
            raise StrategyMError(f"allusion-decisions item {index} has stale source context")
        if item.get("trigger") not in TERM_TRIGGERS:
            raise StrategyMError(f"allusion-decisions item {index} has an invalid trigger")
        candidates = item.get("candidates")
        if not isinstance(candidates, list) or not candidates or not all(
            isinstance(candidate, str) and candidate.strip() for candidate in candidates
        ):
            raise StrategyMError(f"allusion-decisions item {index} has no candidate renderings")
        for field in ("contextual_meaning", "translation_constraint", "rationale"):
            if not isinstance(item.get(field), str) or not item[field].strip():
                raise StrategyMError(f"allusion-decisions item {index} is missing {field}")
        for field in ("contextual_meaning", "translation_constraint"):
            if item[field] != expected_item[field]:
                raise StrategyMError(
                    f"allusion-decisions item {index} does not match the Flash semantic constraint"
                )
        receipt_ids = item.get("external_lookup_receipt_ids")
        if not isinstance(receipt_ids, list) or not receipt_ids or len(receipt_ids) != len(set(receipt_ids)):
            raise StrategyMError(f"allusion-decisions item {index} lacks external lookup receipts")
        matched = []
        for receipt_id in receipt_ids:
            receipt = receipts.get(receipt_id)
            if (
                receipt is None
                or receipt["paragraph_id"] != key[0]
                or receipt["source_expression"] != key[1]
            ):
                raise StrategyMError(f"allusion-decisions item {index} references unrelated evidence")
            matched.append(receipt)
        if not any(receipt["accepted"] for receipt in matched):
            raise StrategyMError(f"allusion-decisions item {index} has no accepted external evidence")
        confidence = item.get("confidence")
        status = item.get("status")
        if confidence not in {"high", "medium", "low"}:
            raise StrategyMError(f"allusion-decisions item {index} has invalid confidence")
        if status == "human_review":
            if confidence == "high":
                raise StrategyMError(f"allusion-decisions item {index} cannot be high-confidence human_review")
            human_review.append({"source_expression": key[1], "paragraph_id": key[0]})
            continue
        if status != "frozen" or confidence != "high":
            raise StrategyMError(f"allusion-decisions item {index} must be high-confidence frozen or human_review")
        selected = item.get("selected")
        if not isinstance(selected, str) or not selected.strip() or selected not in candidates:
            raise StrategyMError(f"allusion-decisions item {index} has an invalid selected rendering")
        frozen.append({
            "source_expression": key[1],
            "paragraph_id": key[0],
            "selected": selected,
            "evidence_receipt_ids": receipt_ids,
        })
    missing = sorted(set(expected_by_key) - seen)
    if missing:
        raise StrategyMError("Flash cultural allusions are missing from allusion-decisions.json")
    referenced_ids = {
        receipt_id for item in items for receipt_id in item.get("external_lookup_receipt_ids", [])
    }
    unreferenced = sorted(set(receipts) - referenced_ids)
    if unreferenced:
        raise StrategyMError("external lookup receipts contain unreferenced evidence")
    return {
        "source_sha256": current_source_hash,
        "source_analysis_sha256": current_analysis_hash,
        "allusion_count": len(expected),
        "frozen_count": len(frozen),
        "human_review_count": len(human_review),
        "lookup_receipt_count": len(receipts),
        "frozen": frozen,
        "human_review": human_review,
    }


def validate_frozen_terms_in_map(term_map: Path, summary: dict) -> None:
    value = load_json(term_map)
    terms = value.get("terms")
    if not isinstance(terms, list):
        raise StrategyMError("term map must contain a terms array")
    indexed = {
        item.get("source"): item.get("preferred")
        for item in terms
        if isinstance(item, dict) and isinstance(item.get("source"), str)
    }
    missing = [
        item["source_term"] for item in summary["frozen"]
        if indexed.get(item["source_term"]) != item["selected"]
    ]
    if missing:
        raise StrategyMError(f"frozen term decisions are missing from term map: {', '.join(missing)}")


def validate_strategy_fixed_terms(source: Path, term_map: Path, target: Path | None = None) -> dict:
    """Enforce M-wide terms while ignoring Chinese inside structural Djot anchors."""
    lock = load_lock()
    fixed_terms = lock.get("fixed_terms", {})
    if not isinstance(fixed_terms, dict) or not fixed_terms:
        raise StrategyMError("release lock has no fixed M terminology policy")
    value = load_json(term_map)
    terms = value.get("terms")
    if not isinstance(terms, list):
        raise StrategyMError("term map must contain a terms array")
    indexed = {
        item.get("source"): item.get("preferred")
        for item in terms
        if isinstance(item, dict)
    }
    source_text = "\n".join(
        STRUCTURAL_RE.sub("", line)
        for line in source.read_text(encoding="utf-8").splitlines()
    )
    target_text = target.read_text(encoding="utf-8") if target else None
    checked = []
    for source_term, preferred in fixed_terms.items():
        source_count = source_text.count(source_term)
        if source_count == 0:
            continue
        if indexed.get(source_term) != preferred:
            raise StrategyMError(f"M fixed term is missing or changed: {source_term} -> {preferred}")
        target_count = target_text.count(preferred) if target_text is not None else None
        if target_count is not None and target_count < source_count:
            raise StrategyMError(
                f"M fixed term coverage is incomplete: {source_term} {source_count} -> {preferred} {target_count}"
            )
        checked.append({
            "source": source_term,
            "preferred": preferred,
            "source_count_excluding_structural_anchors": source_count,
            "target_count": target_count,
        })
    return {"terminology_policy_version": lock["terminology_policy_version"], "checked": checked}


def record_term_decisions(project: Path, source: Path, decisions: Path, term_map: Path) -> dict:
    verify_ready()
    instruction = validate_instruction_receipt(project)
    summary = validate_term_decisions(source, decisions)
    validate_frozen_terms_in_map(term_map, summary)
    fixed_term_summary = validate_strategy_fixed_terms(source, term_map)
    receipt = {
        "schema_version": 1,
        "receipt_id": str(uuid.uuid4()),
        "workflow_stage": "terminology_decisions",
        "kind": "terminology_evidence",
        "recorded_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "instruction_receipt_id": instruction["receipt_id"],
        "inputs": file_hashes([source, term_map]),
        "outputs": file_hashes([decisions]),
        "summary": {**summary, "strategy_fixed_terms": fixed_term_summary},
        "exit_code": 0,
    }
    append_receipt(project, receipt)
    return receipt


def record_allusion_decisions(
    project: Path,
    source: Path,
    analysis: Path,
    decisions: Path,
    lookup_receipts: Path,
) -> dict:
    verify_ready()
    instruction = validate_instruction_receipt(project)
    analysis_hash = sha256_file(analysis)
    prior_receipts = read_receipts(project)
    analysis_was_receipted = any(
        receipt.get("workflow_stage") in {"flash_analysis", "flash_analysis_reuse"}
        and any(
            output.get("absolute_path") == str(analysis.resolve())
            and output.get("sha256") == analysis_hash
            for output in receipt.get("outputs", [])
        )
        for receipt in prior_receipts
    )
    if not analysis_was_receipted:
        raise StrategyMError("allusion research requires a current receipted Flash analysis")
    summary = validate_allusion_decisions(
        source, analysis, decisions, lookup_receipts
    )
    receipt = {
        "schema_version": 1,
        "receipt_id": str(uuid.uuid4()),
        "workflow_stage": "allusion_research",
        "kind": "external_cultural_evidence",
        "recorded_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "instruction_receipt_id": instruction["receipt_id"],
        "inputs": file_hashes([source, analysis, lookup_receipts]),
        "outputs": file_hashes([decisions]),
        "summary": summary,
        "exit_code": 0,
    }
    append_receipt(project, receipt)
    return receipt


def reuse_source_analysis(project: Path, source: Path, analysis: Path) -> dict:
    verify_ready()
    instruction = validate_instruction_receipt(project)
    try:
        value = validate_source_analysis_contract(source, analysis)
    except StrategyMError as exc:
        if "source SHA-256" in str(exc):
            raise StrategyMError(
                "source-analysis cannot be reused because source SHA-256 changed"
            ) from exc
        raise
    receipt = {
        "schema_version": 1,
        "receipt_id": str(uuid.uuid4()),
        "workflow_stage": "flash_analysis_reuse",
        "kind": "reused_model_artifact",
        "recorded_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "instruction_receipt_id": instruction["receipt_id"],
        "inputs": file_hashes([source, analysis]),
        "outputs": file_hashes([analysis]),
        "exit_code": 0,
    }
    append_receipt(project, receipt)
    return receipt


def fallback_resolved(project: Path, successful: set[str]) -> bool:
    if "sol_fallback" not in successful:
        return False
    path = project / "sol-fallback-adjudication.json"
    if not path.is_file():
        return False
    current_hash = sha256_file(path)
    receipted = any(
        receipt.get("workflow_stage") == "sol_fallback"
        and any(
            output.get("absolute_path") == str(path.resolve()) and output.get("sha256") == current_hash
            for output in receipt.get("outputs", [])
        )
        for receipt in read_receipts(project)
    )
    if not receipted:
        return False
    value = load_json(path)
    return (
        value.get("scope") == "targeted_title_or_critical_major"
        and value.get("status") == "resolved"
        and value.get("unresolved_findings") == 0
    )


def run_media(project: Path, media: Path) -> dict:
    instruction = validate_instruction_receipt(project)
    ready, _, _ = verify_ready()
    script = Path(__file__).with_name("transcribe_media.py").resolve()
    command = [sys.executable, str(script), str(media.resolve()), "--project", str(project.resolve())]
    started = time.time()
    receipt = safe_receipt_base("media_transcription", started, command, project)
    receipt.update({
        "owner_repository": {"absolute_path": str(Path(__file__).resolve().parents[3]), "skill_version": ready["skill_version"]},
        "script_absolute_path": str(script),
        "script_sha256": sha256_file(script),
        "inputs": file_hashes([media, Path(ready["whisper"]["model_absolute_path"]), Path(ready["whisper"]["executable_absolute_path"])]),
    })
    completed = run(command, project)
    finished = time.time()
    outputs = [project / "whisper-raw.txt", project / "source-map.json", project / "transcription-ambiguities.json"]
    receipt.update({
        "finished_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(finished)),
        "duration_seconds": round(finished - started, 6),
        "exit_code": completed.returncode,
        "stdout_sha256": sha256_bytes(completed.stdout),
        "stderr_sha256": sha256_bytes(completed.stderr),
        "stdout_summary": {"bytes": len(completed.stdout), "lines": completed.stdout.count(b"\n")},
        "stderr_summary": {"bytes": len(completed.stderr), "lines": completed.stderr.count(b"\n")},
        "outputs": file_hashes(outputs, require=False),
        "instruction_receipt_id": instruction["receipt_id"],
    })
    append_receipt(project, receipt)
    if completed.returncode or len(receipt["outputs"]) != 3:
        raise StrategyMError("media transcription failed")
    return receipt


def forbidden_qa_status(value: object) -> bool:
    if isinstance(value, dict):
        for key, item in value.items():
            if key.casefold() in {"status", "result"} and isinstance(item, str) and item.upper() in {"FAIL", "SKIP"}:
                return True
            if forbidden_qa_status(item):
                return True
    elif isinstance(value, list):
        return any(forbidden_qa_status(item) for item in value)
    return False


def finalize(project: Path, input_type: str) -> dict:
    verify_ready()
    instruction = validate_instruction_receipt(project)
    receipts = read_receipts(project)
    successful = {item.get("workflow_stage") for item in receipts if item.get("exit_code", 0) == 0}
    required = (DOCUMENT_STAGES if input_type == "document" else MEDIA_STAGES) | REQUIRED_MODEL_STAGES
    if "flash_analysis_reuse" in successful:
        required -= {"flash_analysis", "flash_model"}
    missing = sorted(required - successful)
    current_artifacts: dict[str, dict] = {}
    stale = []
    for item in receipts:
        for output in item.get("outputs", []):
            current_artifacts[output["absolute_path"]] = output
    for path_text, output in current_artifacts.items():
        path = Path(path_text)
        if not path.is_file() or sha256_file(path) != output["sha256"]:
            stale.append(str(path))
    qa_paths = [
        project / "qa-report.json",
        project / "target-docx-qa-report.json",
        project / "bilingual-docx-qa-report.json",
        project / "subtitle-qa-report.json",
    ]
    qa_failures = [str(path) for path in qa_paths if not path.is_file() or forbidden_qa_status(load_json(path))]
    second_review = project / "semantic-review.json"
    blockers = False
    semantic_contract_error = None
    if second_review.is_file():
        try:
            certificate = validate_semantic_review_contract(
                project / "source.dj", second_review
            )
            blockers = certificate.get("status") == "blocking" or int(certificate.get("blocking_findings", 0)) > 0
        except StrategyMError as exc:
            semantic_contract_error = str(exc)
    else:
        semantic_contract_error = "semantic-review.json is missing"
    fallback_cleared = blockers and fallback_resolved(project, successful)
    unresolved_review_blockers = blockers and not fallback_cleared
    term_validation_error = None
    term_summary = None
    fixed_term_summary = None
    try:
        term_summary = validate_term_decisions(project / "source.dj", project / "term-decisions.json")
        validate_frozen_terms_in_map(project / "term-map.yaml", term_summary)
        fixed_term_summary = validate_strategy_fixed_terms(
            project / "source.dj", project / "term-map.yaml", project / "target.dj"
        )
    except StrategyMError as exc:
        term_validation_error = str(exc)
    unresolved_terms = bool(term_validation_error or (term_summary and term_summary["human_review_count"]))
    allusion_validation_error = None
    allusion_summary = None
    try:
        allusion_summary = validate_allusion_decisions(
            project / "source.dj",
            project / "source-analysis.json",
            project / "allusion-decisions.json",
            project / "external-lookup-receipts.jsonl",
        )
    except StrategyMError as exc:
        allusion_validation_error = str(exc)
    unresolved_allusions = bool(
        allusion_validation_error
        or (allusion_summary and allusion_summary["human_review_count"])
    )
    pipeline_complete = (
        not missing and not stale and not qa_failures and not semantic_contract_error
        and not unresolved_review_blockers and not unresolved_terms
        and not unresolved_allusions
    )
    status = (
        "needs_human"
        if unresolved_review_blockers or unresolved_terms or unresolved_allusions
        else "ai_draft" if pipeline_complete else "blocked"
    )
    manifest = {
        "schema_version": 1,
        "strategy_id": "M",
        "workflow_version": load_lock()["workflow_version"],
        "pipeline_complete": pipeline_complete,
        "status": status,
        "input_type": input_type,
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "mpi_translations": instruction["mpi_translations"],
        "translation_toolkit": instruction["translation_toolkit"],
        "instruction_receipt": load_json(project / INSTRUCTION_RECEIPT_NAME),
        "tool_execution_receipts_path": str((project / RECEIPTS_NAME).resolve()),
        "receipts_sha256": sha256_file(project / RECEIPTS_NAME),
        "receipts": receipts,
        "artifacts": list(current_artifacts.values()),
        "missing_stages": missing,
        "stale_or_missing_artifacts": sorted(set(stale)),
        "qa_failures": qa_failures,
        "remaining_review_blockers": unresolved_review_blockers,
        "semantic_review_contract_error": semantic_contract_error,
        "sol_high_fallback_cleared": fallback_cleared,
        "term_decisions": term_summary,
        "strategy_fixed_terms": fixed_term_summary,
        "term_decisions_error": term_validation_error,
        "allusion_decisions": allusion_summary,
        "allusion_decisions_error": allusion_validation_error,
        "transcription_ambiguities": load_json(project / "transcription-ambiguities.json").get("items", []) if (project / "transcription-ambiguities.json").is_file() else [],
        "human_approval": None,
    }
    atomic_json(project / MANIFEST_NAME, manifest)
    if not pipeline_complete:
        raise StrategyMError("pipeline is not complete; inspect MANIFEST.json")
    return manifest


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser()
    sub = root.add_subparsers(dest="command", required=True)
    install_parser = sub.add_parser("install")
    install_parser.add_argument("--model", type=Path, required=True)
    install_parser.add_argument("--no-install-dependencies", action="store_true")
    install_parser.add_argument("--development-candidate", action="store_true")
    install_parser.add_argument("--candidate-mpi", type=Path)
    install_parser.add_argument("--candidate-toolkit", type=Path)
    install_parser.add_argument("--skip-credential-for-smoke", action="store_true")
    repair = sub.add_parser("repair")
    repair.add_argument("--model", type=Path)
    repair.add_argument("--no-install-dependencies", action="store_true")
    sub.add_parser("doctor")
    begin = sub.add_parser("begin")
    begin.add_argument("--project", type=Path, required=True)
    begin.add_argument("--input-type", choices=("document", "media"), required=True)
    tool = sub.add_parser("run-tool")
    tool.add_argument("--project", type=Path, required=True)
    tool.add_argument("--stage", required=True)
    tool.add_argument("--script", required=True)
    tool.add_argument("--input", type=Path, action="append", default=[])
    tool.add_argument("--output", type=Path, action="append", default=[])
    tool.add_argument("arguments", nargs=argparse.REMAINDER)
    media = sub.add_parser("run-media")
    media.add_argument("--project", type=Path, required=True)
    media.add_argument("--media", type=Path, required=True)
    model = sub.add_parser("record-model")
    model.add_argument("--project", type=Path, required=True)
    model.add_argument("--stage", required=True)
    model.add_argument("--provider", required=True)
    model.add_argument("--model", required=True)
    model.add_argument("--effort", required=True)
    model.add_argument("--prompt-sha256", required=True)
    model.add_argument("--input", type=Path, action="append", default=[])
    model.add_argument("--output", type=Path, action="append", default=[])
    model.add_argument("--metadata", type=Path)
    terms = sub.add_parser("record-term-decisions")
    terms.add_argument("--project", type=Path, required=True)
    terms.add_argument("--source", type=Path, required=True)
    terms.add_argument("--decisions", type=Path, required=True)
    terms.add_argument("--term-map", type=Path, required=True)
    allusions = sub.add_parser("record-allusion-decisions")
    allusions.add_argument("--project", type=Path, required=True)
    allusions.add_argument("--source", type=Path, required=True)
    allusions.add_argument("--analysis", type=Path, required=True)
    allusions.add_argument("--decisions", type=Path, required=True)
    allusions.add_argument("--lookup-receipts", type=Path, required=True)
    reuse = sub.add_parser("reuse-source-analysis")
    reuse.add_argument("--project", type=Path, required=True)
    reuse.add_argument("--source", type=Path, required=True)
    reuse.add_argument("--analysis", type=Path, required=True)
    final = sub.add_parser("finalize")
    final.add_argument("--project", type=Path, required=True)
    final.add_argument("--input-type", choices=("document", "media"), required=True)
    return root


def main() -> int:
    args = parser().parse_args()
    try:
        if args.command == "install":
            value = install(args.model.resolve(), not args.no_install_dependencies, args.development_candidate, args.candidate_mpi, args.candidate_toolkit, args.skip_credential_for_smoke)
        elif args.command == "repair":
            model_path = args.model
            if model_path is None:
                existing = load_json(managed_root() / "READY.json")
                model_path = Path(existing.get("whisper", {}).get("model_absolute_path", ""))
            if not model_path.is_file():
                raise StrategyMError("repair requires the locked Whisper model path")
            value = install(model_path.resolve(), not args.no_install_dependencies)
        elif args.command == "doctor":
            value = {"ready": verify_ready()[0]}
        elif args.command == "begin":
            value = begin_project(args.project, args.input_type)
        elif args.command == "run-tool":
            arguments = args.arguments[1:] if args.arguments[:1] == ["--"] else args.arguments
            value = run_audited_tool(args.project.resolve(), args.stage, args.script, arguments, args.input, args.output)
        elif args.command == "run-media":
            value = run_media(args.project.resolve(), args.media.resolve())
        elif args.command == "record-model":
            value = record_model(args.project.resolve(), args.stage, args.provider, args.model, args.effort, args.prompt_sha256, args.input, args.output, args.metadata)
        elif args.command == "record-term-decisions":
            value = record_term_decisions(args.project.resolve(), args.source.resolve(), args.decisions.resolve(), args.term_map.resolve())
        elif args.command == "record-allusion-decisions":
            value = record_allusion_decisions(
                args.project.resolve(), args.source.resolve(), args.analysis.resolve(),
                args.decisions.resolve(), args.lookup_receipts.resolve(),
            )
        elif args.command == "reuse-source-analysis":
            value = reuse_source_analysis(args.project.resolve(), args.source.resolve(), args.analysis.resolve())
        else:
            value = finalize(args.project.resolve(), args.input_type)
        print(json.dumps(value, ensure_ascii=False, indent=2))
        return 0
    except StrategyMError as exc:
        print(f"BLOCKED: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
