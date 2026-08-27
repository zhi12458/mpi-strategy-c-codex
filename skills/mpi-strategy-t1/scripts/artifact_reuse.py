#!/usr/bin/env python3
"""Content-addressed reuse for already validated T1 model artifacts."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any

from t1_runtime import (
    StrategyT1Error,
    atomic_json,
    load_lock,
    sha256_bytes,
    sha256_file,
    utc_now,
)


def _object(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise StrategyT1Error(f"invalid JSON evidence: {path}") from exc
    if isinstance(value, dict) and isinstance(value.get("result"), dict):
        value = value["result"]
    if not isinstance(value, dict):
        raise StrategyT1Error(f"JSON evidence root must be an object: {path}")
    return value


def _validation_passed(value: dict[str, Any]) -> bool:
    if value.get("status") == "PASS":
        return True
    return any(
        isinstance(item, dict) and item.get("status") == "PASS"
        for key, item in value.items()
        if key.endswith("validation")
    )


def _cache_key(receipt: dict[str, Any], inputs: list[dict[str, Any]]) -> str:
    lock = load_lock()
    material = {
        "strategy_id": lock["strategy_id"],
        "workflow_version": lock["workflow_version"],
        "role": receipt.get("role"),
        "workflow_stage": receipt.get("workflow_stage"),
        "provider": receipt.get("provider"),
        "model": receipt.get("model"),
        "selector": receipt.get("selector"),
        "reasoning_effort": receipt.get("reasoning_effort"),
        "prompt_sha256": receipt.get("prompt_sha256"),
        "execution_profile": receipt.get("execution_profile"),
        "inputs": [
            {"name": item.get("name"), "sha256": item.get("sha256")}
            for item in inputs
        ],
    }
    encoded = json.dumps(material, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return sha256_bytes(encoded.encode("utf-8"))


def cache_validated_artifact(
    artifact_path: Path,
    receipt_path: Path,
    validation_path: Path,
    cache_root: Path,
) -> dict[str, Any]:
    artifact_path = artifact_path.expanduser().resolve()
    receipt_path = receipt_path.expanduser().resolve()
    validation_path = validation_path.expanduser().resolve()
    cache_root = cache_root.expanduser().resolve()
    if not artifact_path.is_file():
        raise StrategyT1Error(f"validated T1 artifact is missing: {artifact_path}")
    receipt = _object(receipt_path)
    validation = _object(validation_path)
    if not _validation_passed(validation):
        raise StrategyT1Error("T1 artifact cache requires explicit PASS validation evidence")
    artifact_sha = sha256_file(artifact_path)
    output = receipt.get("output")
    receipt_sha = output.get("sha256") if isinstance(output, dict) else receipt.get("output_sha256")
    if receipt_sha != artifact_sha:
        raise StrategyT1Error("T1 receipt output hash does not match the artifact")
    inputs = receipt.get("inputs")
    if not isinstance(inputs, list) or not inputs:
        raise StrategyT1Error("T1 receipt has no frozen input evidence")
    for index, item in enumerate(inputs):
        if not isinstance(item, dict):
            raise StrategyT1Error(f"T1 receipt input[{index}] is invalid")
        path = Path(str(item.get("absolute_path") or ""))
        if not path.is_file() or sha256_file(path) != item.get("sha256"):
            raise StrategyT1Error(f"T1 receipt input[{index}] is missing or stale")
    key = _cache_key(receipt, inputs)
    destination = cache_root / key
    artifact_destination = destination / "artifact.bin"
    metadata_destination = destination / "metadata.json"
    if destination.exists():
        if (
            not artifact_destination.is_file()
            or sha256_file(artifact_destination) != artifact_sha
            or not metadata_destination.is_file()
        ):
            raise StrategyT1Error("existing T1 cache entry is incomplete or corrupt")
        return {
            "status": "PASS",
            "cache_key": key,
            "cache_hit": True,
            "artifact_sha256": artifact_sha,
        }
    cache_root.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=f".{key}.", dir=cache_root) as temporary:
        staging = Path(temporary)
        (staging / "artifact.bin").write_bytes(artifact_path.read_bytes())
        metadata = {
            "schema_version": 1,
            "cache_key": key,
            "created_at": utc_now(),
            "artifact_sha256": artifact_sha,
            "receipt_sha256": sha256_file(receipt_path),
            "validation_sha256": sha256_file(validation_path),
            "receipt_identity": {
                "receipt_id": receipt.get("receipt_id"),
                "role": receipt.get("role"),
                "workflow_stage": receipt.get("workflow_stage"),
                "model": receipt.get("model"),
                "reasoning_effort": receipt.get("reasoning_effort"),
            },
            "inputs": inputs,
        }
        atomic_json(staging / "metadata.json", metadata)
        try:
            os.rename(staging, destination)
        except FileExistsError:
            pass
    if not artifact_destination.is_file() or sha256_file(artifact_destination) != artifact_sha:
        raise StrategyT1Error("T1 cache entry publication failed")
    return {
        "status": "PASS",
        "cache_key": key,
        "cache_hit": False,
        "artifact_sha256": artifact_sha,
    }


def restore_validated_artifact(
    cache_root: Path,
    cache_key: str,
    output: Path,
) -> dict[str, Any]:
    if len(cache_key) != 64 or any(character not in "0123456789abcdef" for character in cache_key):
        raise StrategyT1Error("invalid T1 cache key")
    cache_root = cache_root.expanduser().resolve()
    entry = cache_root / cache_key
    metadata_path = entry / "metadata.json"
    artifact_path = entry / "artifact.bin"
    metadata = _object(metadata_path)
    if metadata.get("cache_key") != cache_key:
        raise StrategyT1Error("T1 cache metadata key mismatch")
    if not artifact_path.is_file() or sha256_file(artifact_path) != metadata.get("artifact_sha256"):
        raise StrategyT1Error("T1 cached artifact is missing or corrupt")
    inputs = metadata.get("inputs")
    if not isinstance(inputs, list):
        raise StrategyT1Error("T1 cache metadata has no input evidence")
    for index, item in enumerate(inputs):
        path = Path(str(item.get("absolute_path") or ""))
        if not path.is_file() or sha256_file(path) != item.get("sha256"):
            raise StrategyT1Error(f"T1 cached input[{index}] is missing or stale")
    output = output.expanduser().resolve()
    if os.path.lexists(os.fspath(output)):
        raise StrategyT1Error(f"refusing to overwrite existing T1 artifact: {output}")
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_name(f".{output.name}.{os.getpid()}.tmp")
    try:
        temporary.write_bytes(artifact_path.read_bytes())
        os.link(temporary, output)
    except FileExistsError as exc:
        raise StrategyT1Error(f"refusing to overwrite existing T1 artifact: {output}") from exc
    finally:
        temporary.unlink(missing_ok=True)
    return {
        "status": "PASS",
        "cache_key": cache_key,
        "artifact_sha256": sha256_file(output),
        "output_path": str(output),
        "usage": {
            "actual_model_invocations": 0,
            "cache_hits": 1,
            "retry_count": 0,
            "input_tokens": 0,
            "output_tokens": 0,
            "token_accounting": "not_applicable_cached_artifact",
        },
    }
