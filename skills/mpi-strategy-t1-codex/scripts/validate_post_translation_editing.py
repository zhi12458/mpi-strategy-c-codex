#!/usr/bin/env python3
"""Validate the resumable T1-Codex post-translation editing evidence."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import re
import struct
import sys
import unicodedata
import zipfile
import zlib
from pathlib import Path
from typing import Any
from xml.etree import ElementTree


WORKFLOW_VERSION = "1.2.0"
SCRIPT_DIR = Path(__file__).resolve().parent
UPSTREAM_INHERITANCE_STAGES = (
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
)
UPSTREAM_STAGE_DEPENDENCY_MODEL_KEYS = {
    "source_analysis": "source_analysis",
    "semantic_bridge_generation": "semantic_bridge_generation",
    "semantic_bridge_challenge": "independent_review",
    "semantic_decisions": "codex_translation_and_editing",
    "chinese_semantic_segmentation": "chinese_semantic_segmentation",
    "chinese_semantic_segmentation_review": "chinese_semantic_segmentation_review",
    "translation_and_self_review": "codex_translation_and_editing",
    "bilingual_review_round_1": "independent_review",
    "review_application_round_1": "codex_translation_and_editing",
    "bilingual_review_round_2": "independent_review",
    "review_application_round_2": "codex_translation_and_editing",
    "title_audit": "codex_translation_and_editing",
    "concision_and_chinese_recheck": "codex_translation_and_editing",
    "post_concision_semantic_regression": "independent_review",
}
WORD_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
CONTENT_TYPES_NS = "http://schemas.openxmlformats.org/package/2006/content-types"
DOCX_MAIN_CONTENT_TYPE = (
    "application/vnd.openxmlformats-officedocument."
    "wordprocessingml.document.main+xml"
)
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


class PostTranslationEditingError(RuntimeError):
    """The post-translation editing evidence is missing, stale, or unsafe."""


def require(value: bool, message: str) -> None:
    if not value:
        raise PostTranslationEditingError(message)


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
        raise PostTranslationEditingError(f"invalid or missing JSON: {path.name}") from exc
    require(isinstance(value, dict), f"JSON root must be an object: {path.name}")
    return value


def load_reader_gate_module():
    script = SCRIPT_DIR / "validate_reader_gate.py"
    spec = importlib.util.spec_from_file_location("t1_codex_reader_gate", script)
    require(spec is not None and spec.loader is not None, "reader-gate validator is unavailable")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_semantic_segmentation_module():
    script = SCRIPT_DIR / "validate_semantic_segmentation.py"
    spec = importlib.util.spec_from_file_location("t1_codex_semantic_segmentation", script)
    require(spec is not None and spec.loader is not None, "segmentation validator is unavailable")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_upstream_model_locks(
    skill_dir: Path | None = None,
) -> dict[str, dict[str, str]]:
    skill_dir = skill_dir or SCRIPT_DIR.parent
    dependency = load_object(skill_dir / "dependency-lock.json")
    production = load_object(skill_dir / "references" / "production-lock.json")
    require(
        dependency.get("workflow_version") == WORKFLOW_VERSION
        and production.get("workflow_version") == WORKFLOW_VERSION,
        "post-edit upstream locks: workflow version drift",
    )
    dependency_models = dependency.get("models")
    production_roles = production.get("model_roles")
    require(isinstance(dependency_models, dict), "post-edit upstream locks: models missing")
    require(isinstance(production_roles, dict), "post-edit upstream locks: roles missing")
    locks: dict[str, dict[str, str]] = {}
    for stage, dependency_key in UPSTREAM_STAGE_DEPENDENCY_MODEL_KEYS.items():
        dependency_spec = dependency_models.get(dependency_key)
        production_spec = production_roles.get(stage)
        require(
            isinstance(dependency_spec, dict),
            f"post-edit upstream locks: dependency model missing for {stage}",
        )
        require(
            isinstance(production_spec, dict),
            f"post-edit upstream locks: production role missing for {stage}",
        )
        require(
            dependency_spec.get("model") == production_spec.get("model")
            and dependency_spec.get("reasoning_effort")
            == production_spec.get("reasoning_effort"),
            f"post-edit upstream locks: dependency/production drift for {stage}",
        )
        for field in ("provider", "model", "reasoning_effort"):
            require(
                isinstance(dependency_spec.get(field), str)
                and dependency_spec[field].strip(),
                f"post-edit upstream locks: {field} missing for {stage}",
            )
        require(
            isinstance(production_spec.get("execution_surface"), str)
            and production_spec["execution_surface"].strip(),
            f"post-edit upstream locks: execution surface missing for {stage}",
        )
        locks[stage] = {
            "provider": dependency_spec["provider"],
            "model": dependency_spec["model"],
            "reasoning_effort": dependency_spec["reasoning_effort"],
            "execution_surface": production_spec["execution_surface"],
        }
    return locks


def project_artifact(project: Path, value: Any, label: str) -> Path:
    require(isinstance(value, str) and value.strip(), f"{label}: artifact path is missing")
    relative = Path(value)
    require(not relative.is_absolute(), f"{label}: artifact path must be project-relative")
    require(".." not in relative.parts, f"{label}: artifact path escapes the project")
    path = (project / relative).resolve()
    require(project == path or project in path.parents, f"{label}: artifact path escapes the project")
    require(path.is_file(), f"{label}: artifact is missing")
    return path


def validate_upstream_reuse(
    project: Path,
    baseline: dict[str, Any],
    *,
    source_hash: str,
    baseline_hash: str,
) -> None:
    receipts = baseline.get("upstream_reuse_receipts")
    model_locks = load_upstream_model_locks()
    require(
        isinstance(receipts, list),
        "post-edit baseline: complete upstream evidence lacks reuse receipts",
    )
    indexed: dict[str, dict[str, Any]] = {}
    for index, receipt in enumerate(receipts, start=1):
        label = f"upstream reuse receipt {index}"
        require(isinstance(receipt, dict), f"{label}: receipt is not an object")
        stage = receipt.get("stage")
        require(stage in UPSTREAM_INHERITANCE_STAGES, f"{label}: invalid stage")
        require(stage not in indexed, f"{label}: duplicate stage {stage}")
        artifact = project_artifact(project, receipt.get("artifact"), label)
        require(
            receipt.get("artifact_sha256") == sha256_file(artifact),
            f"{label}: artifact hash mismatch",
        )
        artifact_receipt = load_object(artifact)
        require(artifact_receipt.get("schema_version") == 1, f"{label}: wrong internal schema")
        require(
            artifact_receipt.get("gate") == "t1_codex_upstream_completion",
            f"{label}: wrong internal gate",
        )
        require(artifact_receipt.get("stage") == stage, f"{label}: internal stage mismatch")
        require(
            artifact_receipt.get("source_sha256") == source_hash,
            f"{label}: internal source hash mismatch",
        )
        require(
            artifact_receipt.get("target_sha256") == baseline_hash,
            f"{label}: internal target hash mismatch",
        )
        require(
            artifact_receipt.get("scope") == "full_document",
            f"{label}: internal scope is incomplete",
        )
        require(artifact_receipt.get("status") == "PASS", f"{label}: internal status did not pass")
        require(
            artifact_receipt.get("complete") is True,
            f"{label}: internal completion is not established",
        )
        identity = artifact_receipt.get("execution_identity")
        require(isinstance(identity, dict), f"{label}: execution identity is missing")
        if stage in model_locks:
            locked_identity = model_locks[stage]
            require(identity.get("kind") == "model", f"{label}: execution kind is wrong")
            require(
                identity.get("provider") == locked_identity["provider"],
                f"{label}: provider is wrong",
            )
            require(
                identity.get("model") == locked_identity["model"],
                f"{label}: model is wrong",
            )
            require(
                identity.get("reasoning_effort")
                == locked_identity["reasoning_effort"],
                f"{label}: reasoning effort is wrong",
            )
            require(identity.get("role") == stage, f"{label}: model role is wrong")
            require(
                identity.get("execution_surface")
                == locked_identity["execution_surface"],
                f"{label}: execution surface is wrong",
            )
            require(
                isinstance(identity.get("request_or_session_id"), str)
                and identity["request_or_session_id"].strip(),
                f"{label}: model request or session identity is missing",
            )
        else:
            require(identity.get("kind") == "tool", f"{label}: execution kind is wrong")
            require(
                isinstance(identity.get("tool_name"), str)
                and identity["tool_name"].strip(),
                f"{label}: tool name is missing",
            )
            require(
                isinstance(identity.get("tool_version"), str)
                and identity["tool_version"].strip(),
                f"{label}: tool version is missing",
            )
            configuration_hash = identity.get("command_or_config_sha256")
            require(
                isinstance(configuration_hash, str) and len(configuration_hash) == 64,
                f"{label}: tool configuration hash is missing",
            )
        require(receipt.get("source_sha256") == source_hash, f"{label}: stale source")
        require(
            receipt.get("baseline_target_sha256") == baseline_hash,
            f"{label}: stale baseline target",
        )
        require(receipt.get("scope") == "full_document", f"{label}: incomplete scope")
        require(receipt.get("status") == "PASS", f"{label}: stage did not pass")
        require(
            receipt.get("role_or_tool_identity_matches_recorded_configuration") is True,
            f"{label}: execution identity or configuration is unverified",
        )
        require(receipt.get("reused_without_rerun") is True, f"{label}: stage was rerun")
        indexed[str(stage)] = receipt
    require(
        set(indexed) == set(UPSTREAM_INHERITANCE_STAGES),
        "post-edit baseline: upstream reuse receipt coverage is incomplete",
    )


def normalize_visible_text(value: str) -> str:
    return " ".join(unicodedata.normalize("NFC", value).replace("\u00a0", " ").split())


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def djot_visible_line(value: str) -> str | None:
    text = value.strip()
    if not text or re.fullmatch(r"\{#[^{}]+\}", text):
        return None
    text = re.sub(r"^#{1,6}\s+", "", text)
    text = re.sub(r"^[-+*]\s+", "", text)
    text = re.sub(r"(?<!\\)([*_])(?=\S)(.+?)(?<=\S)\1", r"\2", text)
    text = re.sub(r"\\([\\`*_{}\[\]()#+\-.!])", r"\1", text)
    normalized = normalize_visible_text(text)
    return normalized or None


def read_jsonl(path: Path, label: str) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeDecodeError) as exc:
        raise PostTranslationEditingError(f"{label}: invalid UTF-8 JSONL") from exc
    for line_number, line in enumerate(lines, start=1):
        require(line.strip() != "", f"{label}: blank JSONL record at line {line_number}")
        try:
            record = json.loads(line)
        except json.JSONDecodeError as exc:
            raise PostTranslationEditingError(
                f"{label}: invalid JSON at line {line_number}"
            ) from exc
        require(isinstance(record, dict), f"{label}: record {line_number} is not an object")
        records.append(record)
    require(records, f"{label}: no records")
    return records


def literal_source_evidence(value: Any, source_text: str, label: str) -> list[str]:
    require(
        isinstance(value, list)
        and value
        and all(
            isinstance(item, str)
            and len(item.strip()) >= 2
            and item.strip() in source_text
            for item in value
        ),
        f"{label}: evidence is not bound to the source line",
    )
    return [item.strip() for item in value]


def nested_strings(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, dict):
        return [text for item in value.values() for text in nested_strings(item)]
    if isinstance(value, list):
        return [text for item in value for text in nested_strings(item)]
    return []


def validate_semantic_map_commissioner_decision(
    project: Path,
    record: dict[str, Any],
    *,
    source_hash: str,
    source_text: str,
    source_line_hash: str,
    ambiguity_ids: list[str],
    requires_person_scope_approval: bool,
    label: str,
) -> None:
    reference = record.get("commissioner_decision")
    require(isinstance(reference, dict), f"{label}: commissioner decision is missing")
    decision_path = project_artifact(
        project,
        reference.get("artifact"),
        f"{label} commissioner decision",
    )
    require(
        reference.get("artifact_sha256") == sha256_file(decision_path),
        f"{label}: commissioner decision artifact hash mismatch",
    )
    decision = load_object(decision_path)
    require(decision.get("schema_version") == 1, f"{label}: commissioner decision schema is wrong")
    require(
        decision.get("gate") == "post_edit_semantic_map_commissioner_decision",
        f"{label}: commissioner decision gate is wrong",
    )
    require(
        decision.get("status") == "approved" and decision.get("approved") is True,
        f"{label}: commissioner decision is not approved",
    )
    require(
        isinstance(decision.get("named_commissioner"), str)
        and decision["named_commissioner"].strip(),
        f"{label}: named commissioner is missing",
    )
    require(
        isinstance(decision.get("decision_id"), str) and decision["decision_id"].strip(),
        f"{label}: commissioner decision id is missing",
    )
    require(decision.get("source_sha256") == source_hash, f"{label}: decision source is stale")
    require(
        decision.get("source_line_sha256") == source_line_hash,
        f"{label}: decision source line is stale",
    )
    require(
        decision.get("paragraph_id") == record.get("paragraph_id"),
        f"{label}: decision paragraph is wrong",
    )
    require(
        decision.get("ambiguity_ids") == ambiguity_ids,
        f"{label}: decision ambiguity coverage is incomplete",
    )
    require(
        isinstance(decision.get("selected_resolution"), str)
        and decision["selected_resolution"].strip(),
        f"{label}: selected resolution is missing",
    )
    literal_source_evidence(
        decision.get("source_evidence"),
        source_text,
        f"{label} commissioner decision",
    )
    if requires_person_scope_approval:
        require(
            decision.get("person_scope_approved") is True,
            f"{label}: added 我们 lacks commissioner person-scope approval",
        )


def validate_post_edit_semantic_map(
    source: Path,
    artifact: Path,
    *,
    source_hash: str,
) -> None:
    try:
        source_lines = source.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeDecodeError) as exc:
        raise PostTranslationEditingError("post-edit semantic map: invalid source UTF-8") from exc
    expected_lines = [index for index, line in enumerate(source_lines, start=1) if line.strip()]
    records = read_jsonl(artifact, "post-edit semantic map")
    require(
        [record.get("source_line") for record in records] == expected_lines,
        "post-edit semantic map: full nonblank source coverage or order is incomplete",
    )
    for record in records:
        line_number = record["source_line"]
        label = f"post-edit semantic map L{line_number:03d}"
        source_text = source_lines[line_number - 1]
        require(record.get("schema_version") == 1, f"{label}: wrong schema")
        require(record.get("workflow_version") == WORKFLOW_VERSION, f"{label}: wrong workflow")
        require(record.get("paragraph_id") == f"L{line_number:03d}", f"{label}: wrong id")
        require(record.get("source_sha256") == source_hash, f"{label}: stale source")
        require(record.get("source_text") == source_text, f"{label}: source text mismatch")
        require(
            record.get("source_line_sha256") == sha256_text(source_text),
            f"{label}: source line hash mismatch",
        )
        require(record.get("source_only") is True, f"{label}: source-only boundary missing")
        require(
            record.get("existing_english_visible") is False,
            f"{label}: existing English was visible",
        )
        record_kind = record.get("record_kind")
        require(record_kind in {"structural", "substantive"}, f"{label}: invalid record kind")
        require(isinstance(record.get("semantic_roles"), dict), f"{label}: semantic roles missing")
        require(
            isinstance(record.get("logical_relations"), list),
            f"{label}: logical relations missing",
        )
        require(
            isinstance(record.get("protected_constraints"), list),
            f"{label}: protected constraints missing",
        )
        ambiguities = record.get("ambiguities")
        require(isinstance(ambiguities, list), f"{label}: ambiguities missing")
        status = record.get("status")
        require(status in {"safe", "commissioner_resolved"}, f"{label}: invalid status")
        propositions = record.get("propositions")
        require(isinstance(propositions, list), f"{label}: propositions missing")
        if record_kind == "structural":
            require(
                djot_visible_line(source_text) is None,
                f"{label}: substantive source was mislabeled structural",
            )
            require(not propositions, f"{label}: structural record contains propositions")
            require(status == "safe", f"{label}: structural record is not closed safe")
            require(not ambiguities, f"{label}: structural record retains ambiguity")
            require(
                record.get("commissioner_decision") is None,
                f"{label}: structural record carries an unexpected decision",
            )
            continue
        require(
            djot_visible_line(source_text) is not None,
            f"{label}: anchor was mislabeled substantive",
        )
        require(propositions, f"{label}: substantive record has no propositions")
        for proposition_index, proposition in enumerate(propositions, start=1):
            proposition_label = f"{label} proposition {proposition_index}"
            require(
                isinstance(proposition, dict),
                f"{proposition_label}: proposition is not an object",
            )
            require(
                isinstance(proposition.get("meaning"), str)
                and proposition["meaning"].strip(),
                f"{proposition_label}: meaning is missing",
            )
            literal_source_evidence(
                proposition.get("source_evidence"),
                source_text,
                proposition_label,
            )
        ambiguity_ids: list[str] = []
        for ambiguity_index, ambiguity in enumerate(ambiguities, start=1):
            ambiguity_label = f"{label} ambiguity {ambiguity_index}"
            require(isinstance(ambiguity, dict), f"{ambiguity_label}: not an object")
            ambiguity_id = ambiguity.get("id")
            require(
                isinstance(ambiguity_id, str)
                and ambiguity_id.strip()
                and ambiguity_id not in ambiguity_ids,
                f"{ambiguity_label}: invalid or duplicate id",
            )
            require(
                isinstance(ambiguity.get("description"), str)
                and ambiguity["description"].strip(),
                f"{ambiguity_label}: description is missing",
            )
            literal_source_evidence(
                ambiguity.get("source_evidence"),
                source_text,
                ambiguity_label,
            )
            ambiguity_ids.append(ambiguity_id)

        semantic_payload = {
            "propositions": propositions,
            "semantic_roles": record["semantic_roles"],
            "logical_relations": record["logical_relations"],
        }
        uses_we = any("我们" in text for text in nested_strings(semantic_payload))
        added_we = uses_we and "我们" not in source_text
        if uses_we:
            person_scope = record.get("person_scope")
            require(isinstance(person_scope, dict), f"{label}: 我们 lacks person-scope evidence")
            require(
                person_scope.get("uniquely_includes_speaker_and_audience") is True,
                f"{label}: 我们 person scope is not uniquely supported",
            )
            literal_source_evidence(
                person_scope.get("source_evidence"),
                source_text,
                f"{label} person scope",
            )

        if status == "safe":
            require(not ambiguities, f"{label}: safe record retains unresolved ambiguities")
            require(not added_we, f"{label}: safe record adds 我们 without commissioner approval")
            require(
                record.get("commissioner_decision") is None
                or record.get("commissioner_decision") is False,
                f"{label}: safe record carries an unexpected commissioner decision",
            )
        else:
            require(
                ambiguities or added_we,
                f"{label}: commissioner-resolved record has no decision point",
            )
            validate_semantic_map_commissioner_decision(
                source.parent,
                record,
                source_hash=source_hash,
                source_text=source_text,
                source_line_hash=sha256_text(source_text),
                ambiguity_ids=ambiguity_ids,
                requires_person_scope_approval=added_we,
                label=label,
            )


def expected_alternating_paragraphs(source: Path, target: Path) -> tuple[list[str], int]:
    try:
        source_lines = source.read_text(encoding="utf-8").splitlines()
        target_lines = target.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeDecodeError) as exc:
        raise PostTranslationEditingError("source or target Djot is not valid UTF-8") from exc
    require(len(source_lines) == len(target_lines), "post-edit delivery: source/target line parity failed")
    paragraphs: list[str] = []
    pair_count = 0
    for line_number, (source_line, target_line) in enumerate(
        zip(source_lines, target_lines, strict=True), start=1
    ):
        source_visible = djot_visible_line(source_line)
        target_visible = djot_visible_line(target_line)
        require(
            (source_visible is None) == (target_visible is None),
            f"post-edit delivery: source/target visible-unit mismatch at line {line_number}",
        )
        if source_visible is None:
            continue
        paragraphs.extend((source_visible, target_visible or ""))
        pair_count += 1
    require(pair_count > 0, "post-edit delivery: no bilingual pairs were found")
    return paragraphs, pair_count


def validate_docx_and_extract_paragraphs(path: Path) -> list[str]:
    require(zipfile.is_zipfile(path), "post-edit delivery: final file is not a DOCX ZIP package")
    try:
        with zipfile.ZipFile(path) as archive:
            names = set(archive.namelist())
            require(archive.testzip() is None, "post-edit delivery: corrupt DOCX ZIP member")
            require(
                {"[Content_Types].xml", "_rels/.rels", "word/document.xml"}.issubset(names),
                "post-edit delivery: required DOCX parts are missing",
            )
            require(
                not any(name.startswith("word/comments") for name in names),
                "post-edit delivery: comments part remains",
            )
            content_types = ElementTree.fromstring(archive.read("[Content_Types].xml"))
            overrides = {
                node.get("PartName"): node.get("ContentType")
                for node in content_types.findall(f"{{{CONTENT_TYPES_NS}}}Override")
            }
            require(
                overrides.get("/word/document.xml") == DOCX_MAIN_CONTENT_TYPE,
                "post-edit delivery: main document content type is invalid",
            )
            document = ElementTree.fromstring(archive.read("word/document.xml"))
    except (OSError, zipfile.BadZipFile, ElementTree.ParseError, RuntimeError) as exc:
        raise PostTranslationEditingError("post-edit delivery: invalid DOCX structure") from exc
    require(
        not document.findall(f".//{{{WORD_NS}}}tbl"),
        "post-edit delivery: final body uses a table instead of alternating paragraphs",
    )
    for local_name in ("ins", "del", "moveFrom", "moveTo"):
        require(
            not document.findall(f".//{{{WORD_NS}}}{local_name}"),
            "post-edit delivery: tracked changes remain",
        )
    paragraphs: list[str] = []
    for paragraph in document.findall(f".//{{{WORD_NS}}}body/{{{WORD_NS}}}p"):
        fragments: list[str] = []
        for node in paragraph.iter():
            if node.tag == f"{{{WORD_NS}}}t" and node.text:
                fragments.append(node.text)
            elif node.tag == f"{{{WORD_NS}}}tab":
                fragments.append("\t")
            elif node.tag in {f"{{{WORD_NS}}}br", f"{{{WORD_NS}}}cr"}:
                fragments.append("\n")
        visible = normalize_visible_text("".join(fragments))
        if visible:
            paragraphs.append(visible)
    require(paragraphs, "post-edit delivery: final DOCX body is empty")
    return paragraphs


def validate_png(path: Path, label: str) -> None:
    data = path.read_bytes()
    require(data.startswith(PNG_SIGNATURE), f"{label}: rendered page is not PNG")
    offset = len(PNG_SIGNATURE)
    saw_ihdr = False
    saw_iend = False
    while offset + 12 <= len(data):
        length = struct.unpack(">I", data[offset : offset + 4])[0]
        chunk_type = data[offset + 4 : offset + 8]
        end = offset + 12 + length
        require(end <= len(data), f"{label}: truncated PNG chunk")
        payload = data[offset + 8 : offset + 8 + length]
        expected_crc = struct.unpack(">I", data[offset + 8 + length : end])[0]
        require(
            zlib.crc32(chunk_type + payload) & 0xFFFFFFFF == expected_crc,
            f"{label}: PNG CRC mismatch",
        )
        if chunk_type == b"IHDR":
            require(not saw_ihdr and length == 13, f"{label}: invalid PNG IHDR")
            width, height = struct.unpack(">II", payload[:8])
            require(width > 0 and height > 0, f"{label}: invalid PNG dimensions")
            saw_ihdr = True
        if chunk_type == b"IEND":
            saw_iend = True
            require(end == len(data), f"{label}: trailing data after PNG IEND")
            break
        offset = end
    require(saw_ihdr and saw_iend, f"{label}: incomplete PNG structure")


def validate_post_translation_editing(project: Path) -> dict[str, Any]:
    source = project / "source.dj"
    baseline_target = project / "target-pre-postedit.dj"
    final_target = project / "target.dj"
    require(source.is_file(), "source.dj is missing")
    require(baseline_target.is_file(), "target-pre-postedit.dj is missing")
    require(final_target.is_file(), "target.dj is missing")
    source_hash = sha256_file(source)
    baseline_hash = sha256_file(baseline_target)
    final_hash = sha256_file(final_target)

    baseline = load_object(project / "post-edit-baseline.json")
    require(baseline.get("schema_version") == 1, "post-edit baseline: wrong schema")
    require(baseline.get("workflow_version") == WORKFLOW_VERSION, "post-edit baseline: wrong workflow version")
    require(baseline.get("mode") == "retrofit_existing_translation", "post-edit baseline: wrong mode")
    require(baseline.get("source_sha256") == source_hash, "post-edit baseline: stale source")
    require(
        baseline.get("baseline_target_sha256") == baseline_hash,
        "post-edit baseline: stale target",
    )
    require(baseline.get("baseline_target_preserved") is True, "incoming target was not preserved")
    require(baseline.get("full_translation_rerun") is False, "retrofit unexpectedly reran translation")
    require(baseline.get("bilingual_reviews_rerun") is False, "retrofit unexpectedly reran bilingual reviews")

    semantic_map = baseline.get("source_only_semantic_map")
    require(isinstance(semantic_map, dict), "post-edit baseline: semantic-map receipt is missing")
    require(
        semantic_map.get("kind")
        in {"validated_pre_draft_segmentation", "post_edit_source_only_map"},
        "post-edit baseline: invalid semantic-map kind",
    )
    require(semantic_map.get("source_sha256") == source_hash, "post-edit semantic map: stale source")
    require(semantic_map.get("full_document_scope") is True, "post-edit semantic map is not full-document")
    require(semantic_map.get("existing_english_visible") is False, "post-edit semantic map saw existing English")
    require(
        semantic_map.get("visible_input_count") == 1
        and semantic_map.get("visible_input_sha256") == source_hash,
        "post-edit semantic map: source-only visible input is not hash-bound",
    )
    require(
        isinstance(semantic_map.get("session_id"), str)
        and semantic_map["session_id"].strip(),
        "post-edit semantic map: session identity is missing",
    )
    require(
        isinstance(semantic_map.get("prompt_sha256"), str)
        and len(semantic_map["prompt_sha256"]) == 64,
        "post-edit semantic map: prompt hash is missing",
    )
    semantic_artifact = semantic_map.get("artifact")
    require(
        isinstance(semantic_artifact, str)
        and semantic_artifact
        and Path(semantic_artifact).name == semantic_artifact,
        "post-edit semantic map: invalid artifact name",
    )
    artifact_path = project / semantic_artifact
    require(artifact_path.is_file() and artifact_path.stat().st_size > 0, "post-edit semantic map artifact is missing or empty")
    require(
        semantic_map.get("artifact_sha256") == sha256_file(artifact_path),
        "post-edit semantic map: artifact hash mismatch",
    )
    if semantic_map["kind"] == "validated_pre_draft_segmentation":
        require(
            semantic_artifact == "chinese-semantic-segmentation.jsonl",
            "post-edit semantic map: validated segmentation artifact name is wrong",
        )
        segmentation_validator = load_semantic_segmentation_module()
        try:
            segmentation_report = segmentation_validator.validate_project(project, "review")
        except segmentation_validator.SegmentationValidationError as exc:
            raise PostTranslationEditingError(
                f"post-edit semantic map: validated segmentation failed: {exc}"
            ) from exc
        require(
            segmentation_report.get("source_sha256") == source_hash,
            "post-edit semantic map: validated segmentation is stale",
        )
    else:
        validate_post_edit_semantic_map(
            source,
            artifact_path,
            source_hash=source_hash,
        )

    upstream_complete = baseline.get("upstream_t1_codex_evidence_complete")
    require(isinstance(upstream_complete, bool), "post-edit baseline: upstream evidence status is missing")
    claimed_status = baseline.get("claimed_status")
    if upstream_complete:
        validate_upstream_reuse(
            project,
            baseline,
            source_hash=source_hash,
            baseline_hash=baseline_hash,
        )
        require(
            claimed_status in {"AI reviewed draft", "T1-Codex post-edit AI-reviewed draft"},
            "post-edit baseline: invalid completed status",
        )
    else:
        require(
            claimed_status == "T1-Codex post-edit AI-reviewed draft",
            "incomplete upstream evidence was overstated as full T1-Codex completion",
        )

    reader_gate = load_reader_gate_module()
    try:
        reader_report = reader_gate.validate_reader_gate(project)
    except reader_gate.ReaderGateError as exc:
        raise PostTranslationEditingError(f"reader gate failed: {exc}") from exc

    delivery = load_object(project / "post-edit-delivery-record.json")
    require(delivery.get("schema_version") == 1, "post-edit delivery: wrong schema")
    require(delivery.get("gate") == "clean_alternating_bilingual_docx", "post-edit delivery: wrong gate")
    require(delivery.get("source_sha256") == source_hash, "post-edit delivery: stale source")
    require(delivery.get("target_sha256") == final_hash, "post-edit delivery: stale target")
    expected_pairs = delivery.get("expected_pair_count")
    actual_pairs = delivery.get("actual_pair_count")
    require(
        isinstance(expected_pairs, int)
        and expected_pairs > 0
        and actual_pairs == expected_pairs,
        "post-edit delivery: Chinese-English pair count mismatch",
    )
    for field in (
        "alternating_source_then_target",
        "titles_toc_and_headings_alternating",
        "incoming_english_excluded",
        "internal_material_excluded",
        "comments_absent",
        "tracked_changes_absent",
        "placeholders_absent",
        "font_coverage_pass",
        "docx_structure_pass",
        "zip_integrity_pass",
        "text_fidelity_pass",
    ):
        require(delivery.get(field) is True, f"post-edit delivery: {field} did not pass")
    rendered_pages = delivery.get("rendered_page_count")
    inspected_pages = delivery.get("visually_inspected_page_count")
    require(
        isinstance(rendered_pages, int)
        and rendered_pages > 0
        and inspected_pages == rendered_pages,
        "post-edit delivery: page-by-page visual inspection is incomplete",
    )
    docx_path_value = delivery.get("final_docx_path")
    require(isinstance(docx_path_value, str) and docx_path_value, "post-edit delivery: final DOCX path is missing")
    docx_path = Path(docx_path_value).expanduser()
    if not docx_path.is_absolute():
        docx_path = project / docx_path
    require(docx_path.is_file(), "post-edit delivery: final DOCX is missing")
    final_docx_hash = sha256_file(docx_path)
    require(
        delivery.get("final_docx_sha256") == final_docx_hash,
        "post-edit delivery: final DOCX hash mismatch",
    )
    expected_paragraphs, derived_pair_count = expected_alternating_paragraphs(
        source, final_target
    )
    require(
        expected_pairs == derived_pair_count,
        "post-edit delivery: expected pair count is not derived from source and target",
    )
    actual_paragraphs = validate_docx_and_extract_paragraphs(docx_path)
    require(
        actual_paragraphs == expected_paragraphs,
        "post-edit delivery: actual DOCX paragraph order or text fidelity mismatch",
    )
    require(
        actual_pairs == len(actual_paragraphs) // 2,
        "post-edit delivery: actual pair count is not derived from the DOCX",
    )
    forbidden_markers = delivery.get("forbidden_placeholder_strings")
    require(
        isinstance(forbidden_markers, list)
        and forbidden_markers
        and all(isinstance(item, str) and item for item in forbidden_markers),
        "post-edit delivery: forbidden placeholder marker list is missing",
    )
    body_text = "\n".join(actual_paragraphs)
    for marker in forbidden_markers:
        require(marker not in body_text, f"post-edit delivery: placeholder remains: {marker}")

    rendered_pages = delivery.get("rendered_pages")
    require(isinstance(rendered_pages, list), "post-edit delivery: rendered page index is missing")
    require(
        len(rendered_pages) == delivery.get("rendered_page_count"),
        "post-edit delivery: rendered page index count mismatch",
    )
    render_receipt_path = project_artifact(
        project,
        delivery.get("render_receipt_artifact"),
        "post-edit render receipt",
    )
    require(
        delivery.get("render_receipt_sha256") == sha256_file(render_receipt_path),
        "post-edit render receipt: artifact hash mismatch",
    )
    render_receipt = load_object(render_receipt_path)
    require(render_receipt.get("schema_version") == 1, "post-edit render receipt: wrong schema")
    require(
        render_receipt.get("gate") == "final_docx_render",
        "post-edit render receipt: wrong gate",
    )
    require(render_receipt.get("status") == "PASS", "post-edit render receipt did not pass")
    require(render_receipt.get("exit_code") == 0, "post-edit render command failed")
    require(
        render_receipt.get("rendered_from_docx_sha256") == final_docx_hash,
        "post-edit render receipt: rendered DOCX hash mismatch",
    )
    require(
        render_receipt.get("page_count") == delivery.get("rendered_page_count"),
        "post-edit render receipt: page count mismatch",
    )
    require(render_receipt.get("output_format") == "png", "post-edit render receipt: wrong format")
    for field in ("renderer", "renderer_version", "started_at", "completed_at"):
        require(
            isinstance(render_receipt.get(field), str) and render_receipt[field].strip(),
            f"post-edit render receipt: {field} is missing",
        )
    render_config_hash = render_receipt.get("command_or_config_sha256")
    require(
        isinstance(render_config_hash, str) and len(render_config_hash) == 64,
        "post-edit render receipt: command or configuration hash is missing",
    )
    receipt_pages = render_receipt.get("pages")
    require(isinstance(receipt_pages, list), "post-edit render receipt: page index is missing")
    require(
        receipt_pages
        == [
            {"artifact": page.get("artifact"), "sha256": page.get("sha256")}
            for page in rendered_pages
            if isinstance(page, dict)
        ],
        "post-edit render receipt: page index does not match delivery evidence",
    )
    inspected_count = 0
    for index, page in enumerate(rendered_pages, start=1):
        label = f"post-edit rendered page {index}"
        require(isinstance(page, dict), f"{label}: index entry is not an object")
        require(
            page.get("rendered_from_docx_sha256") == final_docx_hash,
            f"{label}: rendered DOCX hash mismatch",
        )
        image_path = project_artifact(project, page.get("artifact"), label)
        require(
            page.get("sha256") == sha256_file(image_path),
            f"{label}: image hash mismatch",
        )
        validate_png(image_path, label)
        require(page.get("inspected") is True, f"{label}: visual inspection is not recorded")
        inspected_count += 1
    require(
        inspected_count == delivery.get("visually_inspected_page_count"),
        "post-edit delivery: visual inspection index count mismatch",
    )

    return {
        "schema_version": 1,
        "status": "PASS",
        "workflow_version": WORKFLOW_VERSION,
        "mode": "retrofit_existing_translation",
        "source_sha256": source_hash,
        "baseline_target_sha256": baseline_hash,
        "final_target_sha256": final_hash,
        "claimed_status": claimed_status,
        "reader_gate_status": reader_report["status"],
        "final_docx_sha256": delivery["final_docx_sha256"],
        "visually_inspected_page_count": inspected_pages,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("project", type=Path)
    args = parser.parse_args()
    try:
        report = validate_post_translation_editing(args.project.resolve())
    except PostTranslationEditingError as exc:
        print(json.dumps({"status": "FAIL", "error": str(exc)}, indent=2))
        return 1
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
