#!/usr/bin/env python3
"""Fail-closed interactive installer for the locked T1-Codex provider runtime."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import platform
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable


EXPECTED_OMP_VERSION = "17.3.4"
EXPECTED_BASE_WORKFLOW = "1.0.1"
EXPECTED_BASE_INSTALLER = "1.0.0"
EXPECTED_BASE_MANIFEST_SHA256 = (
    "765bec51ed736a6e505e0e1bf6ef2f5a9dd7ce3eb4db7e2cc99dd29cb3ebd47e"
)
READY_NAME = "T1_CODEX_RUNTIME_READY.json"
SMOKE_CONFIRMATION = "RUN PUBLIC SMOKE"


class RuntimeInstallError(RuntimeError):
    """A required T1-Codex runtime gate did not pass."""


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
        raise RuntimeInstallError(f"invalid JSON: {path}") from exc
    if not isinstance(value, dict):
        raise RuntimeInstallError(f"JSON root must be an object: {path}")
    return value


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
            raise RuntimeInstallError("LOCALAPPDATA is not defined")
        return (Path(base) / "MPI-Strategy-T1").resolve()
    if system == "Linux":
        base = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))
        return (base / "mpi-strategy-t1").resolve()
    raise RuntimeInstallError(f"unsupported platform: {system}")


def atomic_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = (json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode()
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            "wb", dir=path.parent, prefix=f".{path.name}.", delete=False
        ) as handle:
            temporary = Path(handle.name)
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
        temporary = None
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def verify_base_package(base_skill: Path) -> dict[str, Any]:
    base_skill = base_skill.expanduser().resolve()
    lock = load_object(base_skill / "dependency-lock.json")
    if lock.get("strategy_id") != "T1":
        raise RuntimeInstallError("the selected base Skill is not MPI T1")
    if lock.get("workflow_version") != EXPECTED_BASE_WORKFLOW:
        raise RuntimeInstallError("base T1 workflow version does not match the fixed runtime")
    if lock.get("installer_version") != EXPECTED_BASE_INSTALLER:
        raise RuntimeInstallError("base T1 installer version does not match the fixed runtime")
    if lock.get("release_ready") is not True:
        raise RuntimeInstallError("base T1 installer is not release-ready")
    manifest = base_skill / "MANIFEST.sha256"
    if not manifest.is_file() or sha256_file(manifest) != EXPECTED_BASE_MANIFEST_SHA256:
        raise RuntimeInstallError("base T1 manifest does not match the immutable release")
    for relative in (
        "scripts/strategy_t1.py",
        "scripts/credential_store.py",
    ):
        if not (base_skill / relative).is_file():
            raise RuntimeInstallError(f"base T1 file is missing: {relative}")
    return lock


def missing_dependencies() -> list[str]:
    missing = [name for name in ("git", "pandoc") if not shutil.which(name)]
    if not (shutil.which("libreoffice") or shutil.which("soffice")):
        missing.append("libreoffice")
    if sys.version_info < (3, 11):
        missing.append("python>=3.11")
    if importlib.util.find_spec("keyring") is None:
        missing.append("python-keyring")
    return missing


def omp_version(executable: str, runner: Callable[..., subprocess.CompletedProcess] = subprocess.run) -> str:
    completed = runner(
        (executable, "--version"),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        timeout=30,
    )
    if completed.returncode:
        raise RuntimeInstallError("OMP version check failed")
    return completed.stdout.decode("utf-8", errors="replace").strip()


def run_interactive(command: tuple[str, ...], cwd: Path) -> None:
    completed = subprocess.run(command, cwd=cwd, check=False)
    if completed.returncode:
        raise RuntimeInstallError(f"required command failed: {Path(command[1]).name if len(command) > 1 else command[0]}")


def run_json(command: tuple[str, ...], cwd: Path) -> dict[str, Any]:
    completed = subprocess.run(
        command,
        cwd=cwd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if completed.returncode:
        detail = completed.stdout or completed.stderr
        message = detail.decode("utf-8", errors="replace").strip()
        raise RuntimeInstallError(message or "required JSON command failed")
    try:
        value = json.loads(completed.stdout.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RuntimeInstallError("required command did not return valid JSON") from exc
    if not isinstance(value, dict):
        raise RuntimeInstallError("required command JSON root is not an object")
    return value


def credential_present(base_skill: Path) -> bool:
    completed = subprocess.run(
        (sys.executable, "scripts/credential_store.py", "--check"),
        cwd=base_skill,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if completed.returncode not in (0, 1):
        raise RuntimeInstallError("DeepSeek credential vault check failed")
    return completed.returncode == 0 and completed.stdout.strip() == b"present"


def base_ready_from_doctor(report: dict[str, Any]) -> dict[str, Any]:
    if report.get("ok") is not True:
        raise RuntimeInstallError("base T1 doctor did not pass")
    ready = report.get("result")
    if not isinstance(ready, dict) or ready.get("ready") is not True:
        raise RuntimeInstallError("base T1 READY.json is not ready=true")
    deepseek = ready.get("deepseek_credential", {})
    if not isinstance(deepseek, dict) or deepseek.get("present") is not True:
        raise RuntimeInstallError("base READY lacks DeepSeek credential evidence")
    smoke = ready.get("smoke_test", {})
    if not isinstance(smoke, dict) or smoke.get("status") != "PASS":
        raise RuntimeInstallError("base READY lacks passing public smoke evidence")
    fault = ready.get("fault_injection", {})
    if not isinstance(fault, dict) or fault.get("status") != "PASS":
        raise RuntimeInstallError("base READY lacks passing fault-injection evidence")
    return ready


def install_runtime(base_skill: Path) -> dict[str, Any]:
    if not sys.stdin.isatty():
        raise RuntimeInstallError("runtime installation requires an interactive terminal")
    base_skill = base_skill.expanduser().resolve()
    verify_base_package(base_skill)
    skill_dir = Path(__file__).resolve().parents[1]
    candidate_lock = load_object(skill_dir / "dependency-lock.json")
    package = run_json((sys.executable, "scripts/validate_package.py"), skill_dir)
    if package.get("status") != "PASS":
        raise RuntimeInstallError("T1-Codex package validation did not pass")
    missing = missing_dependencies()
    if missing:
        raise RuntimeInstallError(
            "required dependencies are missing: "
            + ", ".join(missing)
            + "; install them with user approval and rerun"
        )
    omp = shutil.which("omp")
    if not omp:
        raise RuntimeInstallError(
            "OMP is missing; after user approval install exactly "
            "@oh-my-pi/pi-coding-agent@17.3.4 and rerun"
        )
    actual_omp = omp_version(omp)
    if actual_omp != EXPECTED_OMP_VERSION:
        raise RuntimeInstallError(
            f"OMP version mismatch: expected {EXPECTED_OMP_VERSION}, got {actual_omp or 'unknown'}"
        )

    print("Opening the OMP OpenAI login. Complete the browser flow locally.")
    run_interactive((sys.executable, "scripts/strategy_t1.py", "login-openai"), base_skill)

    print("Confirm the actual Personal or ChatGPT Business workspace locally.")
    run_interactive((sys.executable, "scripts/confirm_workspace.py"), skill_dir)

    if not credential_present(base_skill):
        print("DeepSeek credential is missing. Enter it in the masked local prompt.")
        run_interactive((sys.executable, "scripts/credential_store.py"), base_skill)
    if not credential_present(base_skill):
        raise RuntimeInstallError("DeepSeek credential was not saved")

    print(
        "The next step sends fixed public markers through OMP to Flash/high, "
        "Sol/high, and Pro/max and consumes a small amount of quota."
    )
    answer = input(f"Type {SMOKE_CONFIRMATION} to authorize it: ").strip()
    if answer != SMOKE_CONFIRMATION:
        raise RuntimeInstallError("public smoke was not authorized")

    run_interactive(
        (sys.executable, "scripts/strategy_t1.py", "install", "--confirm-public-smoke"),
        base_skill,
    )
    doctor = run_json((sys.executable, "scripts/strategy_t1.py", "doctor"), base_skill)
    ready = base_ready_from_doctor(doctor)
    report = {
        "schema_version": 1,
        "runtime_ready": True,
        "completed_at": datetime.now(timezone.utc).isoformat(),
        "candidate_ref": candidate_lock.get("candidate_ref"),
        "candidate_manifest_sha256": package.get("manifest", {}).get("sha256"),
        "omp_version": actual_omp,
        "deepseek_credential_present": True,
        "base_ready": True,
        "base_ready_created_at": ready.get("created_at"),
        "base_ready_completed_at": ready.get("completed_at"),
        "base_manifest_sha256": ready.get("skill_manifest", {}).get("sha256"),
        "public_smoke_status": "PASS",
        "locked_role_summary": {
            "codex": [
                "Chinese semantic segmentation",
                "English draft",
                "adjudication",
                "title audit",
                "concision",
                "reader-finding source adjudication",
            ],
            "omp_deepseek_flash_high": ["source analysis", "high-risk bridge"],
            "omp_deepseek_pro_max": [
                "bridge challenge",
                "Chinese semantic-segmentation review",
                "two bilingual reviews",
                "post-concision semantic regression",
            ],
            "isolated_english_only_readers": [
                "general nonfiction editor initial and final",
                "English Buddhist/Dharma editor initial and final",
            ],
        },
        "codex_task_setting_still_requires_direct_verification": True,
        "strategy_release_ready": False,
        "credentials_recorded": False,
    }
    destination = managed_root() / READY_NAME
    atomic_json(destination, report)
    return {**report, "report_path": str(destination)}


def parser() -> argparse.ArgumentParser:
    value = argparse.ArgumentParser(description=__doc__)
    value.add_argument(
        "--base-skill-dir",
        type=Path,
        default=Path(__file__).resolve().parents[2] / "mpi-strategy-t1",
        help="path to the immutable mpi-strategy-t1 Skill",
    )
    return value


def main() -> int:
    args = parser().parse_args()
    try:
        result = install_runtime(args.base_skill_dir)
    except (RuntimeInstallError, subprocess.TimeoutExpired) as exc:
        print(json.dumps({"status": "BLOCKED", "error": str(exc)}, ensure_ascii=False, indent=2))
        return 2
    print(json.dumps({"status": "PASS", **result}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
