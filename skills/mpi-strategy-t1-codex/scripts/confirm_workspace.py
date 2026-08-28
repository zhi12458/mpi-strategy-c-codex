#!/usr/bin/env python3
"""Confirm a Personal or ChatGPT Business workspace for the locked T1 runtime."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


LEGACY_CONFIRMATION_NAME = "personal-workspace-confirmation.json"
ALLOWED_TOKENS = {
    "PERSONAL": "personal",
    "BUSINESS": "business",
    "TEAM": "business",
}


class WorkspaceConfirmationError(RuntimeError):
    """The selected OpenAI workspace could not be safely confirmed."""


def managed_root() -> Path:
    override = os.environ.get("MPI_STRATEGY_T1_ROOT")
    if override:
        return Path(override).expanduser().resolve()
    system = platform.system()
    if system == "Darwin":
        return (Path.home() / "Library" / "Application Support" / "MPI-Strategy-T1").resolve()
    if system == "Windows":
        base = os.environ.get("LOCALAPPDATA")
        if not base:
            raise WorkspaceConfirmationError("LOCALAPPDATA is not defined")
        return (Path(base) / "MPI-Strategy-T1").resolve()
    if system == "Linux":
        base = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))
        return (base / "mpi-strategy-t1").resolve()
    raise WorkspaceConfirmationError(f"unsupported platform: {system}")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def atomic_json(path: Path, value: dict[str, Any]) -> None:
    path = path.expanduser().resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    data = (json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode()
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            "wb", dir=path.parent, prefix=f".{path.name}.", delete=False
        ) as handle:
            temporary = Path(handle.name)
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
        temporary = None
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def enabled_reports(payload: dict[str, Any]) -> list[dict[str, Any]]:
    reports = payload.get("reports", [])
    if not isinstance(reports, list):
        return []
    return [
        item
        for item in reports
        if isinstance(item, dict)
        and item.get("provider") == "openai-codex"
        and isinstance(item.get("metadata"), dict)
        and item["metadata"].get("allowed") is True
    ]


def public_summary(reports: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "number": number,
            "plan_type": item["metadata"].get("planType"),
            "workspace_label": item["metadata"].get("orgName"),
            "allowed": True,
        }
        for number, item in enumerate(reports, start=1)
    ]


def build_confirmation(
    usage_response: bytes,
    reports: list[dict[str, Any]],
    selected_number: int,
    confirmation_token: str,
) -> dict[str, Any]:
    if not 1 <= selected_number <= len(reports):
        raise WorkspaceConfirmationError("selected account number is out of range")
    normalized = confirmation_token.strip().upper()
    workspace_kind = ALLOWED_TOKENS.get(normalized)
    if not workspace_kind:
        raise WorkspaceConfirmationError(
            "workspace was not confirmed as PERSONAL or BUSINESS (TEAM is accepted as an alias)"
        )
    selected = public_summary(reports)[selected_number - 1]
    selected_bytes = json.dumps(
        selected, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return {
        "schema_version": 2,
        "confirmed": True,
        "provider": "openai-codex",
        "confirmed_at": datetime.now(timezone.utc).isoformat(),
        "workspace_kind": workspace_kind,
        "team_alias_normalized_to_business": normalized == "TEAM",
        "selected_report_number": selected_number,
        "selected_summary_sha256": sha256_bytes(selected_bytes),
        "usage_response_sha256": sha256_bytes(usage_response),
        "enabled_account_count": len(reports),
        "legacy_base_runtime_filename": LEGACY_CONFIRMATION_NAME,
        "selection_requires_model_catalog_and_public_smoke": True,
        "email_recorded": False,
        "account_id_recorded": False,
        "workspace_label_recorded": False,
        "token_recorded": False,
    }


def confirm_workspace(root: Path | None = None) -> dict[str, Any]:
    omp = shutil.which("omp")
    if not omp:
        raise WorkspaceConfirmationError("OMP is missing")
    completed = subprocess.run(
        (omp, "usage", "--provider", "openai-codex", "--redact", "--json"),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=90,
        check=False,
    )
    if completed.returncode:
        raise WorkspaceConfirmationError("OMP usage could not verify an OpenAI Codex account")
    try:
        payload = json.loads(completed.stdout.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise WorkspaceConfirmationError("OMP usage did not return valid JSON") from exc
    if not isinstance(payload, dict):
        raise WorkspaceConfirmationError("OMP usage JSON root is not an object")
    reports = enabled_reports(payload)
    if not reports:
        raise WorkspaceConfirmationError("no enabled OpenAI Codex account was found")
    summary = public_summary(reports)
    print(json.dumps({"enabled_accounts": summary}, ensure_ascii=False, indent=2))
    if not sys.stdin.isatty():
        raise WorkspaceConfirmationError("workspace confirmation requires an interactive terminal")
    try:
        selected_number = int(input("Select the enabled account number to confirm: ").strip())
    except ValueError as exc:
        raise WorkspaceConfirmationError("account selection must be a number") from exc
    token = input(
        "Type PERSONAL for a Personal workspace, or BUSINESS for ChatGPT Business "
        "(TEAM is accepted as the former name): "
    )
    confirmation = build_confirmation(
        completed.stdout, reports, selected_number, token
    )
    destination = (root or managed_root()) / LEGACY_CONFIRMATION_NAME
    atomic_json(destination, confirmation)
    return {
        **confirmation,
        "confirmation_path": str(destination.resolve()),
    }


def parser() -> argparse.ArgumentParser:
    value = argparse.ArgumentParser(description=__doc__)
    value.add_argument(
        "--managed-root",
        type=Path,
        help="override the T1 managed root; intended for isolated validation",
    )
    return value


def main() -> int:
    args = parser().parse_args()
    try:
        result = confirm_workspace(args.managed_root)
    except (WorkspaceConfirmationError, subprocess.TimeoutExpired) as exc:
        print(json.dumps({"status": "FAIL", "error": str(exc)}, indent=2))
        return 1
    print(json.dumps({"status": "PASS", **result}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
