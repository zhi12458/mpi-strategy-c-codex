#!/usr/bin/env python3
"""Run T1 dependency-tamper checks only in disposable repository copies."""

from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path

from t1_runtime import StrategyT1Error, atomic_json, load_lock, sha256_file, utc_now, verify_repo


def must_block(action, label: str, cases: list[dict]) -> None:
    try:
        action()
    except StrategyT1Error as exc:
        cases.append({"case": label, "blocked": True, "error_class": type(exc).__name__})
        return
    raise StrategyT1Error(f"fault injection did not block: {label}")


def run_fault_tests(installed_root: Path) -> dict:
    lock = load_lock()
    source = installed_root / "repos" / "mpi-translations"
    if not source.is_dir():
        raise StrategyT1Error("managed repository is missing before fault injection")
    cases: list[dict] = []
    with tempfile.TemporaryDirectory(prefix="mpi-strategy-t1-fault-") as directory:
        mpi = Path(directory) / "mpi-translations"
        shutil.copytree(source, mpi, symlinks=True)
        toolkit = mpi / lock["translation_toolkit"]["submodule_path"]
        verify_repo(mpi, lock["mpi_translations"])
        verify_repo(toolkit, lock["translation_toolkit"])

        agents = mpi / "AGENTS.md"
        agents_bytes = agents.read_bytes()
        agents.unlink()
        must_block(lambda: verify_repo(mpi, lock["mpi_translations"]), "missing_mpi_agents", cases)
        agents.write_bytes(agents_bytes)
        verify_repo(mpi, lock["mpi_translations"])

        subprocess.run(
            ("git", "remote", "set-url", "origin", "https://example.invalid/wrong"),
            cwd=mpi,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        must_block(lambda: verify_repo(mpi, lock["mpi_translations"]), "wrong_mpi_origin", cases)
        subprocess.run(
            ("git", "remote", "set-url", "origin", lock["mpi_translations"]["origin"]),
            cwd=mpi,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        verify_repo(mpi, lock["mpi_translations"])

        for relative in ("scripts/check-translation.py", "terms-database/termlib.sqlite"):
            candidate = toolkit / relative
            original = candidate.read_bytes()
            candidate.write_bytes(original + b"\nT1_FAULT")
            must_block(
                lambda: verify_repo(toolkit, lock["translation_toolkit"]),
                f"modified_{relative}",
                cases,
            )
            candidate.write_bytes(original)
            verify_repo(toolkit, lock["translation_toolkit"])

    verify_repo(source, lock["mpi_translations"])
    verify_repo(source / lock["translation_toolkit"]["submodule_path"], lock["translation_toolkit"])
    report = {
        "schema_version": 1,
        "status": "PASS",
        "created_at": utc_now(),
        "cases": cases,
        "restored_installation_verified": True,
    }
    output = installed_root / "fault-injection-report.json"
    atomic_json(output, report)
    report["report_absolute_path"] = str(output.resolve())
    report["report_sha256"] = sha256_file(output)
    return report
