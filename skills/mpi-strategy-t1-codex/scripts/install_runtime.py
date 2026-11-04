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
import uuid
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
    override = os.environ.get("MPI_STRATEGY_T1_CODEX_ROOT")
    if override:
        return Path(override).expanduser().resolve()
    system = platform.system()
    if system == "Darwin":
        return (Path.home() / "Library" / "Application Support" / "MPI-Strategy-T1-Codex").resolve()
    if system == "Windows":
        base = os.environ.get("LOCALAPPDATA")
        if not base:
            raise RuntimeInstallError("LOCALAPPDATA is not defined")
        return (Path(base) / "MPI-Strategy-T1-Codex").resolve()
    if system == "Linux":
        base = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))
        return (base / "mpi-strategy-t1-codex").resolve()
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
    for line in manifest.read_text(encoding="utf-8").splitlines():
        expected, relative = line.split("  ", 1)
        candidate = (base_skill / relative).resolve()
        if not candidate.is_relative_to(base_skill) or not candidate.is_file() or sha256_file(candidate) != expected:
            raise RuntimeInstallError(f"base package content mismatch: {relative}")
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
    reported = completed.stdout.decode("utf-8", errors="replace").strip()
    if reported.startswith("omp/"):
        return reported.removeprefix("omp/")
    return reported


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


def provider_checks(base_skill: Path, root: Path, evidence: Path, *, revalidate: bool,
                    candidate_mpi: Path | None = None, candidate_toolkit: Path | None = None) -> dict:
    """Reuse immutable repository/QA helpers, never the T1-OMP installer or READY."""
    command = (sys.executable, str(Path(__file__).with_name("provider_runtime.py")),
               str(base_skill), str(root), str(evidence))
    if revalidate:
        command += ("--revalidate-existing",)
    if candidate_mpi:
        command += ("--candidate-mpi", str(candidate_mpi))
    if candidate_toolkit:
        command += ("--candidate-toolkit", str(candidate_toolkit))
    return run_json(command, base_skill)


def provision(base_skill: Path, *, revalidate: bool, confirm_public_smoke: bool,
              candidate_mpi: Path | None = None, candidate_toolkit: Path | None = None) -> dict:
    base_skill = base_skill.expanduser().resolve()
    verify_base_package(base_skill)
    skill_dir = Path(__file__).resolve().parents[1]
    package = run_json((sys.executable, "scripts/validate_package.py"), skill_dir)
    if package.get("status") != "PASS":
        raise RuntimeInstallError("T1-Codex package validation failed")
    missing = missing_dependencies()
    if missing:
        raise RuntimeInstallError("required dependencies are missing: " + ", ".join(missing))
    omp = shutil.which("omp")
    if not omp or omp_version(omp) != EXPECTED_OMP_VERSION:
        raise RuntimeInstallError("OMP must be exactly " + EXPECTED_OMP_VERSION)
    if not credential_present(base_skill):
        if revalidate or not sys.stdin.isatty():
            raise RuntimeInstallError("DeepSeek credential missing; run interactive installation for masked input")
        run_interactive((sys.executable, "scripts/credential_store.py"), base_skill)
        if not credential_present(base_skill):
            raise RuntimeInstallError("DeepSeek credential was not saved")
    if not confirm_public_smoke:
        if revalidate or not sys.stdin.isatty():
            raise RuntimeInstallError("public live smoke requires --confirm-public-smoke")
        if input(f"Flash/high and Pro/max public tests consume quota. Type {SMOKE_CONFIRMATION}: ").strip() != SMOKE_CONFIRMATION:
            raise RuntimeInstallError("public smoke was not authorized")
    root = managed_root()
    evidence = root / "attempts" / uuid.uuid4().hex
    evidence.mkdir(parents=True)
    destination = root / READY_NAME
    # A failed attempt must not leave a previous readiness flag looking current.
    if destination.exists():
        shutil.copy2(destination, evidence / "previous-runtime-ready.json")
    pending = {"schema_version": 2, "runtime_profile": "deepseek-only-v1",
               "runtime_ready": False, "provider_runtime_ready": False,
               "attempt_path": str(evidence), "strategy_release_ready": False}
    atomic_json(destination, pending)
    try:
        checked = provider_checks(base_skill, root, evidence, revalidate=revalidate,
                                  candidate_mpi=candidate_mpi, candidate_toolkit=candidate_toolkit)
        if checked.get("status") != "PASS":
            raise RuntimeInstallError("DeepSeek provider runtime checks failed")
        for name in ("smoke", "fault"):
            receipt = checked[name]
            path = Path(receipt["path"])
            if not path.is_file() or sha256_file(path) != receipt["sha256"] or receipt["status"] != "PASS":
                raise RuntimeInstallError(f"{name} receipt missing or stale")
        if not credential_present(base_skill):
            raise RuntimeInstallError("DeepSeek credential no longer available")
    except Exception:
        atomic_json(evidence / "attempt.json", {**pending, "status": "FAIL"})
        raise
    report = {**pending, "status": "PASS", "runtime_ready": True,
              "provider_runtime_ready": True, "readiness_scope": "DeepSeek provider runtime only",
              "completed_at": datetime.now(timezone.utc).isoformat(),
              "candidate_manifest_sha256": package["manifest"]["sha256"],
              "base_manifest_sha256": sha256_file(base_skill / "MANIFEST.sha256"),
              "base_ready_used": False, "omp_openai_login_required": False,
              "omp_workspace_confirmation_required": False, "gpt_smoke_required": False,
              "deepseek_credential_present": True, "public_smoke_status": "PASS",
              "codex_task_setting_still_requires_direct_verification": True,
              "credentials_recorded": False, "checks": checked}
    atomic_json(destination, report)
    return {**report, "report_path": str(destination)}


def install_runtime(base_skill: Path, *, confirm_public_smoke: bool = False,
                    candidate_mpi: Path | None = None, candidate_toolkit: Path | None = None) -> dict:
    return provision(base_skill, revalidate=False, confirm_public_smoke=confirm_public_smoke,
                     candidate_mpi=candidate_mpi, candidate_toolkit=candidate_toolkit)


def revalidate_existing_runtime(base_skill: Path, *, confirm_public_smoke: bool) -> dict:
    return provision(base_skill, revalidate=True, confirm_public_smoke=confirm_public_smoke)


def parser() -> argparse.ArgumentParser:
    value = argparse.ArgumentParser(description=__doc__)
    value.add_argument(
        "--base-skill-dir",
        type=Path,
        default=Path(__file__).resolve().parents[2] / "mpi-strategy-t1",
        help="path to the immutable mpi-strategy-t1 Skill",
    )
    value.add_argument("--revalidate-existing", action="store_true",
                       help="verify an existing installation and refresh evidence without OAuth or cloning")
    value.add_argument("--confirm-public-smoke", action="store_true",
                       help="authorize fixed public smoke requests for existing-runtime revalidation")
    value.add_argument("--candidate-mpi", type=Path, help="optional local source; exact origin/SHA still enforced")
    value.add_argument("--candidate-toolkit", type=Path)
    return value


def main() -> int:
    args = parser().parse_args()
    try:
        if args.revalidate_existing:
            result = revalidate_existing_runtime(args.base_skill_dir,
                                                  confirm_public_smoke=args.confirm_public_smoke)
        else:
            result = install_runtime(args.base_skill_dir, confirm_public_smoke=args.confirm_public_smoke,
                                     candidate_mpi=args.candidate_mpi, candidate_toolkit=args.candidate_toolkit)
    except (RuntimeInstallError, subprocess.TimeoutExpired) as exc:
        print(json.dumps({"status": "BLOCKED", "error": str(exc)}, ensure_ascii=False, indent=2))
        return 2
    print(json.dumps({"status": "PASS", **result}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
