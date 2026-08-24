#!/usr/bin/env python3
"""Install, verify, and run the audited MPI T1 runtime."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

from t1_bootstrap import install, verify_ready
from omp_runtime import run_file
from t1_runtime import (
    ACCOUNT_CONFIRMATION_NAME,
    StrategyT1Error,
    atomic_json,
    executable,
    load_lock,
    managed_root,
    run,
    sha256_bytes,
    utc_now,
)


def login_openai() -> dict:
    lock = load_lock()
    omp = executable(lock["omp"]["executable"])
    if not omp:
        raise StrategyT1Error("OMP is missing")
    completed = subprocess.run((omp, "auth-broker", "login", "openai-codex"), check=False)
    if completed.returncode:
        raise StrategyT1Error("OMP OpenAI OAuth login did not complete")
    return {
        "status": "oauth_callback_completed",
        "next": "run confirm-personal-workspace and inspect the account before installation",
    }


def confirm_personal_workspace() -> dict:
    lock = load_lock()
    omp = executable(lock["omp"]["executable"])
    if not omp:
        raise StrategyT1Error("OMP is missing")
    completed = run(
        (omp, "usage", "--provider", "openai-codex", "--redact", "--json"),
        Path.cwd(),
        timeout=90,
    )
    if completed.returncode:
        raise StrategyT1Error("OMP usage could not verify an OpenAI Codex account")
    try:
        payload = json.loads(completed.stdout.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise StrategyT1Error("OMP usage did not return valid JSON") from exc
    reports = [
        item for item in payload.get("reports", [])
        if isinstance(item, dict)
        and item.get("provider") == "openai-codex"
        and item.get("metadata", {}).get("allowed") is True
    ]
    if not reports:
        raise StrategyT1Error("no enabled OpenAI Codex account was found")
    summary = [
        {
            "plan_type": item.get("metadata", {}).get("planType"),
            "workspace_label": item.get("metadata", {}).get("orgName"),
            "allowed": True,
        }
        for item in reports
    ]
    print(json.dumps({"enabled_accounts": summary}, ensure_ascii=False, indent=2))
    if not sys.stdin.isatty():
        raise StrategyT1Error("Personal workspace confirmation requires an interactive terminal")
    answer = input("After verifying that the selected workspace is Personal, type PERSONAL: ").strip()
    if answer != "PERSONAL":
        raise StrategyT1Error("Personal workspace was not confirmed")
    confirmation = {
        "schema_version": 1,
        "confirmed": True,
        "provider": "openai-codex",
        "confirmed_at": utc_now(),
        "usage_response_sha256": sha256_bytes(completed.stdout),
        "enabled_account_count": len(reports),
        "email_recorded": False,
        "account_id_recorded": False,
        "token_recorded": False,
    }
    root = managed_root()
    root.mkdir(parents=True, exist_ok=True)
    atomic_json(root / ACCOUNT_CONFIRMATION_NAME, confirmation)
    return confirmation


def parser() -> argparse.ArgumentParser:
    value = argparse.ArgumentParser(description=__doc__)
    commands = value.add_subparsers(dest="command", required=True)
    for name in ("install", "repair"):
        command = commands.add_parser(name)
        command.add_argument("--install-dependencies", action="store_true")
        command.add_argument("--confirm-public-smoke", action="store_true")
    commands.add_parser("login-openai")
    commands.add_parser("confirm-personal-workspace")
    commands.add_parser("doctor")
    model = commands.add_parser("run-model")
    model.add_argument(
        "--role",
        required=True,
        choices=("source_analysis", "translation_and_self_review", "bilingual_review"),
    )
    model.add_argument("--prompt-file", type=Path, required=True)
    model.add_argument("--output", type=Path, required=True)
    model.add_argument("--cwd", type=Path, default=Path.cwd())
    model.add_argument("--timeout", type=int, default=1800)
    return value


def main() -> int:
    args = parser().parse_args()
    try:
        if args.command in {"install", "repair"}:
            result = install(
                install_missing=args.install_dependencies,
                confirm_public_smoke=args.confirm_public_smoke,
            )
        elif args.command == "login-openai":
            result = login_openai()
        elif args.command == "confirm-personal-workspace":
            result = confirm_personal_workspace()
        elif args.command == "doctor":
            result = verify_ready()
        elif args.command == "run-model":
            verify_ready()
            result = run_file(
                args.role,
                args.prompt_file,
                args.output,
                cwd=args.cwd.expanduser().resolve(),
                timeout=args.timeout,
            )
        else:
            raise StrategyT1Error("unknown command")
    except StrategyT1Error as exc:
        print(json.dumps({"ok": False, "status": "BLOCKED", "error": str(exc)}, ensure_ascii=False, indent=2))
        return 2
    print(json.dumps({"ok": True, "result": result}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
