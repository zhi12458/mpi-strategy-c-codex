#!/usr/bin/env python3
"""Summarize T1 receipt usage without treating OMP events as model calls."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from t1_runtime import StrategyT1Error, sha256_file


def _receipt(path: Path) -> dict[str, Any]:
    path = path.expanduser().resolve()
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise StrategyT1Error(f"invalid T1 receipt JSON: {path}") from exc
    if isinstance(value, dict) and isinstance(value.get("result"), dict):
        value = value["result"]
    if not isinstance(value, dict) or not isinstance(value.get("usage"), dict):
        raise StrategyT1Error(f"T1 receipt has no usage evidence: {path}")
    return value


def summarize_receipts(paths: list[Path]) -> dict[str, Any]:
    if not paths:
        raise StrategyT1Error("at least one T1 receipt is required")
    rows = []
    input_tokens = 0
    output_tokens = 0
    token_complete = True
    for path in paths:
        resolved = path.expanduser().resolve()
        receipt = _receipt(resolved)
        usage = receipt["usage"]
        for field in ("actual_model_invocations", "cache_hits", "retry_count"):
            value = usage.get(field)
            if not isinstance(value, int) or value < 0:
                raise StrategyT1Error(f"invalid {field} in T1 receipt: {resolved}")
        current_input = usage.get("input_tokens")
        current_output = usage.get("output_tokens")
        if not isinstance(current_input, int) or not isinstance(current_output, int):
            token_complete = False
        else:
            input_tokens += current_input
            output_tokens += current_output
        rows.append(
            {
                "path": str(resolved),
                "sha256": sha256_file(resolved),
                "receipt_id": receipt.get("receipt_id"),
                "workflow_stage": receipt.get("workflow_stage"),
                "role": receipt.get("role"),
                "duration_seconds": float(receipt.get("duration_seconds") or 0.0),
                "actual_model_invocations": usage["actual_model_invocations"],
                "cache_hits": usage["cache_hits"],
                "retry_count": usage["retry_count"],
                "input_tokens": current_input,
                "output_tokens": current_output,
                "token_accounting": usage.get("token_accounting"),
            }
        )
    return {
        "status": "PASS",
        "receipt_count": len(rows),
        "actual_model_invocations": sum(item["actual_model_invocations"] for item in rows),
        "cache_hits": sum(item["cache_hits"] for item in rows),
        "retry_count": sum(item["retry_count"] for item in rows),
        "duration_seconds": round(sum(item["duration_seconds"] for item in rows), 6),
        "input_tokens": input_tokens if token_complete else None,
        "output_tokens": output_tokens if token_complete else None,
        "token_accounting_complete": token_complete,
        "omp_event_count_used_as_model_call_count": False,
        "receipts": rows,
    }
