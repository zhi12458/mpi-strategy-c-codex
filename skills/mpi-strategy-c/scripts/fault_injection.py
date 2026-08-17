#!/usr/bin/env python3
"""Run dependency destruction/recovery checks only in disposable clones."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
import time
from pathlib import Path

import runtime
from runtime import StrategyCError, atomic_json, sha256_file, verify_repo, verify_ready


def must_block(action, label: str, cases: list[dict]) -> None:
    try:
        action()
    except StrategyCError as exc:
        cases.append({"case": label, "blocked": True, "error_class": type(exc).__name__})
        return
    raise StrategyCError(f"fault injection did not block: {label}")


def git_commit(repo: Path, message: str) -> str:
    environment = {
        **os.environ,
        "GIT_AUTHOR_NAME": "MPI Strategy C self-test",
        "GIT_AUTHOR_EMAIL": "self-test@example.invalid",
        "GIT_COMMITTER_NAME": "MPI Strategy C self-test",
        "GIT_COMMITTER_EMAIL": "self-test@example.invalid",
    }
    for command in (("git", "add", "-A"), ("git", "commit", "-m", message)):
        completed = subprocess.run(command, cwd=repo, env=environment, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
        if completed.returncode:
            raise StrategyCError("could not create disposable fault-test commit")
    return subprocess.check_output(("git", "rev-parse", "HEAD"), cwd=repo, text=True).strip()


def temporary_ready(root: Path, lock: dict, mpi: Path, toolkit: Path) -> None:
    mpi_info = verify_repo(mpi, lock["mpi_translations"])
    toolkit_info = verify_repo(toolkit, lock["translation_toolkit"])
    atomic_json(
        root / "READY.json",
        {
            "schema_version": 1,
            "ready": False,
            "candidate_installation": True,
            "skill_version": lock["skill_version"],
            "mpi_translations": mpi_info,
            "translation_toolkit": toolkit_info,
        },
    )


def run_fault_tests(installed_root: Path) -> dict:
    original_lock_path = runtime.LOCK_PATH
    lock = runtime.load_lock()
    mpi_source = installed_root / "repos" / "mpi-translations"
    cases: list[dict] = []
    with tempfile.TemporaryDirectory(prefix="mpi-strategy-c-fault-") as directory:
        root = Path(directory).resolve()
        mpi = root / "repos" / "mpi-translations"
        mpi.parent.mkdir(parents=True)
        shutil.copytree(mpi_source, mpi)
        toolkit = mpi / lock["translation_toolkit"]["submodule_path"]
        temporary_ready(root, lock, mpi, toolkit)
        verify_ready(root, require_ready=False)

        agents = mpi / "AGENTS.md"
        agents_bytes = agents.read_bytes()
        agents.unlink()
        must_block(lambda: verify_ready(root, require_ready=False), "missing_mpi_agents", cases)
        agents.write_bytes(agents_bytes)
        verify_ready(root, require_ready=False)

        subprocess.run(("git", "remote", "set-url", "origin", "https://example.invalid/wrong"), cwd=mpi, check=True)
        must_block(lambda: verify_ready(root, require_ready=False), "wrong_mpi_origin", cases)
        subprocess.run(("git", "remote", "set-url", "origin", lock["mpi_translations"]["origin"]), cwd=mpi, check=True)
        verify_ready(root, require_ready=False)

        for relative in ("scripts/docx2dj.py", "terms-database/termlib.sqlite", "scripts/check-translation.py"):
            path = toolkit / relative
            original = path.read_bytes()
            path.write_bytes(original + b"\nFAULT")
            must_block(lambda: verify_ready(root, require_ready=False), f"modified_{relative}", cases)
            path.write_bytes(original)
            verify_ready(root, require_ready=False)

        failing_lock = json.loads(json.dumps(lock))
        toolkit_doctor = toolkit / "scripts" / "doctor.py"
        toolkit_doctor.write_text("import json\nprint(json.dumps({'ok': False}))\nraise SystemExit(1)\n", encoding="utf-8")
        failing_toolkit_sha = git_commit(toolkit, "force doctor failure")
        failing_lock["translation_toolkit"]["expected_sha"] = failing_toolkit_sha
        subprocess.run(("git", "add", "toolkit"), cwd=mpi, check=True)
        failing_mpi_sha = git_commit(mpi, "point to failing doctor")
        failing_lock["mpi_translations"]["expected_sha"] = failing_mpi_sha
        failing_lock_path = root / "fault-lock.json"
        atomic_json(failing_lock_path, failing_lock)
        runtime.LOCK_PATH = failing_lock_path
        try:
            temporary_ready(root, failing_lock, mpi, toolkit)
            must_block(lambda: verify_ready(root, require_ready=False), "doctor_failure", cases)
        finally:
            runtime.LOCK_PATH = original_lock_path

    verify_ready(installed_root, require_ready=False)
    report = {
        "schema_version": 1,
        "status": "PASS",
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "cases": cases,
        "restored_installation_verified": True,
    }
    output = installed_root / "fault-injection-report.json"
    atomic_json(output, report)
    report["report_absolute_path"] = str(output)
    report["report_sha256"] = sha256_file(output)
    return report


if __name__ == "__main__":
    try:
        print(json.dumps(run_fault_tests(runtime.managed_root()), ensure_ascii=False, indent=2))
    except StrategyCError as exc:
        print(f"BLOCKED: {exc}")
        raise SystemExit(2)
