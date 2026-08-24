#!/usr/bin/env python3
"""Run locked T1 model roles through OMP without exposing provider secrets."""

from __future__ import annotations

import os
import time
import uuid
from pathlib import Path

from t1_runtime import StrategyT1Error, load_lock, run, sha256_bytes


def deepseek_environment(lock: dict) -> dict[str, str]:
    try:
        import keyring
    except ImportError as exc:
        raise StrategyT1Error("Python keyring is required") from exc
    policy = lock["credential_policy"]
    try:
        secret = keyring.get_password(policy["deepseek_service"], policy["deepseek_account"])
    except Exception as exc:
        raise StrategyT1Error("the operating-system credential vault is unavailable") from exc
    if not secret:
        raise StrategyT1Error("DeepSeek credential is missing from the T1 operating-system vault")
    return {"DEEPSEEK_API_KEY": secret}


def run_role(
    role: str,
    messages: list[str],
    *,
    cwd: Path,
    timeout: int | None = None,
) -> tuple[bytes, dict]:
    lock = load_lock()
    spec = lock["models"].get(role)
    if not spec:
        raise StrategyT1Error(f"unknown T1 model role: {role}")
    if not messages:
        raise StrategyT1Error("OMP role execution requires a message or @file input")
    for value in messages:
        if value.startswith("-"):
            raise StrategyT1Error("OMP message arguments may not begin with a flag")
    command = [
        lock["omp"]["executable"],
        "-p",
        "--no-session",
        "--no-tools",
        "--hide-thinking",
        "--model",
        spec["selector"],
        "--thinking",
        spec["reasoning_effort"],
        "--max-time",
        str(timeout or lock["smoke_policy"]["maximum_seconds_per_model"]),
        *messages,
    ]
    environment = deepseek_environment(lock) if spec["provider"] == "deepseek" else None
    started = time.time()
    completed = run(command, cwd, env=environment, timeout=(timeout or 180) + 30)
    duration = round(time.time() - started, 6)
    receipt = {
        "receipt_id": str(uuid.uuid4()),
        "role": role,
        "provider": spec["provider"],
        "model": spec["model"],
        "selector": spec["selector"],
        "reasoning_effort": spec["reasoning_effort"],
        "exit_code": completed.returncode,
        "duration_seconds": duration,
        "stdout_sha256": sha256_bytes(completed.stdout),
        "stdout_bytes": len(completed.stdout),
        "stderr_sha256": sha256_bytes(completed.stderr),
        "stderr_bytes": len(completed.stderr),
        "secret_in_arguments": False,
    }
    if completed.returncode:
        raise StrategyT1Error(f"OMP role failed: {role}")
    return completed.stdout, receipt


def run_file(role: str, prompt_file: Path, output: Path, *, cwd: Path, timeout: int = 1800) -> dict:
    prompt_file = prompt_file.expanduser().resolve()
    output = output.expanduser().resolve()
    if not prompt_file.is_file():
        raise StrategyT1Error(f"prompt file is missing: {prompt_file}")
    stdout, receipt = run_role(role, [f"@{prompt_file}"], cwd=cwd, timeout=timeout)
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_name(f".{output.name}.{uuid.uuid4().hex}.tmp")
    try:
        temporary.write_bytes(stdout)
        os.replace(temporary, output)
    finally:
        temporary.unlink(missing_ok=True)
    receipt["prompt_path"] = str(prompt_file)
    receipt["prompt_sha256"] = sha256_bytes(prompt_file.read_bytes())
    receipt["output_path"] = str(output)
    receipt["output_sha256"] = sha256_bytes(stdout)
    return receipt
