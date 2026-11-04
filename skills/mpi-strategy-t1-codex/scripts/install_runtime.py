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


def verify_existing_workspace(root: Path, omp: str) -> dict[str, Any]:
    """Verify the previous explicit selection without logging in or recording identity."""
    confirmation_path = root / "personal-workspace-confirmation.json"
    confirmation = load_object(confirmation_path)
    if (confirmation.get("schema_version") != 2
            or confirmation.get("confirmed") is not True
            or confirmation.get("workspace_kind") not in {"personal", "business"}):
        raise RuntimeInstallError("existing workspace selection needs interactive confirmation")
    script = Path(__file__).with_name("confirm_workspace.py")
    spec = importlib.util.spec_from_file_location("t1_refresh_workspace", script)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    try:
        payload = run_json((omp, "usage", "--provider", "openai-codex", "--redact", "--json"), root)
    except RuntimeInstallError as exc:
        # Do not echo usage payloads, account labels, or provider errors.
        raise RuntimeInstallError("existing OpenAI account could not be verified; check authentication") from exc
    summaries = module.public_summary(module.enabled_reports(payload))
    number = confirmation.get("selected_report_number")
    if type(number) is not int or not 1 <= number <= len(summaries):
        raise RuntimeInstallError("previous workspace is unavailable; select it interactively")
    encoded = json.dumps(summaries[number - 1], ensure_ascii=False,
                         sort_keys=True, separators=(",", ":")).encode("utf-8")
    if hashlib.sha256(encoded).hexdigest() != confirmation.get("selected_summary_sha256"):
        raise RuntimeInstallError("workspace selection changed; confirm it interactively")
    return {"confirmed": True, "workspace_kind": confirmation["workspace_kind"],
            "confirmation_sha256": sha256_file(confirmation_path),
            "current_selected_summary_sha256": hashlib.sha256(encoded).hexdigest(),
            "authentication_reused": True, "identifiers_recorded": False}


def refresh_public_smoke(base_skill: Path, evidence_root: Path, ready: dict[str, Any]) -> dict[str, Any]:
    """Run the unchanged base smoke on the already verified managed checkout."""
    program = (
        "import json,sys; from pathlib import Path; "
        "sys.path.insert(0,sys.argv[1]); "
        "from t1_smoke_test import run_smoke_test; from t1_runtime import load_lock; "
        "print(json.dumps(run_smoke_test(Path(sys.argv[2]),Path(sys.argv[3]),load_lock())))"
    )
    return run_json((sys.executable, "-c", program, str(base_skill / "scripts"),
                     str(evidence_root), ready["translation_toolkit"]["absolute_path"]), base_skill)


def revalidate_existing_runtime(base_skill: Path, *, confirm_public_smoke: bool) -> dict[str, Any]:
    """Refresh evidence without OAuth, repository replacement, or historical relabelling."""
    if not confirm_public_smoke:
        raise RuntimeInstallError("public live smoke requires --confirm-public-smoke")
    base_skill = base_skill.expanduser().resolve()
    verify_base_package(base_skill)
    skill_dir = Path(__file__).resolve().parents[1]
    candidate = load_object(skill_dir / "dependency-lock.json")
    package = run_json((sys.executable, "scripts/validate_package.py"), skill_dir)
    if package.get("status") != "PASS":
        raise RuntimeInstallError("T1-Codex package validation did not pass")
    missing = missing_dependencies()
    if missing:
        raise RuntimeInstallError("required dependencies are missing: " + ", ".join(missing))
    omp = shutil.which("omp")
    if not omp or omp_version(omp) != EXPECTED_OMP_VERSION:
        raise RuntimeInstallError("existing OMP must be exactly " + EXPECTED_OMP_VERSION)
    root = managed_root()
    ready = base_ready_from_doctor(run_json((sys.executable, "scripts/strategy_t1.py", "doctor"), base_skill))
    if not credential_present(base_skill):
        raise RuntimeInstallError("DeepSeek credential is missing; use the masked credential prompt")
    account = verify_existing_workspace(root, omp)
    evidence_root = root / "runtime-revalidations" / uuid.uuid4().hex
    evidence_root.mkdir(parents=True)
    try:
        smoke = refresh_public_smoke(base_skill, evidence_root, ready)
        smoke_path = evidence_root / "smoke-test-report.json"
        if (smoke.get("status") != "PASS" or not smoke_path.is_file()
                or sha256_file(smoke_path) != smoke.get("report_sha256")):
            raise RuntimeInstallError("fresh public smoke evidence did not pass")
        # A successful live request never substitutes for a final state check.
        ready = base_ready_from_doctor(run_json((sys.executable, "scripts/strategy_t1.py", "doctor"), base_skill))
        account = verify_existing_workspace(root, omp)
    except (RuntimeInstallError, subprocess.TimeoutExpired):
        atomic_json(evidence_root / "attempt.json", {
            "status": "FAIL", "runtime_ready_updated": False,
            "completed_at": datetime.now(timezone.utc).isoformat()})
        raise
    report = {
        "schema_version": 1, "runtime_ready": True,
        "completed_at": datetime.now(timezone.utc).isoformat(),
        "candidate_ref": candidate.get("candidate_ref"),
        "candidate_manifest_sha256": package["manifest"]["sha256"],
        "package_runtime_revision": "existing-runtime-revalidation-local-1",
        "runtime_mode": "revalidate-existing", "omp_version": EXPECTED_OMP_VERSION,
        "deepseek_credential_present": True, "base_ready": True,
        "base_ready_created_at": ready.get("created_at"),
        "base_ready_completed_at": ready.get("completed_at"),
        "base_manifest_sha256": ready.get("skill_manifest", {}).get("sha256"),
        "base_ready_sha256": sha256_file(root / "READY.json"),
        "public_smoke_status": "PASS",
        "public_smoke_evidence": {"path": str(smoke_path), "sha256": sha256_file(smoke_path)},
        "workspace_revalidation": account,
        "repositories_replaced": False, "historical_receipts_rewritten": False,
        "codex_task_setting_still_requires_direct_verification": True,
        "strategy_release_ready": False, "credentials_recorded": False,
    }
    destination = root / READY_NAME
    if destination.exists():
        shutil.copy2(destination, evidence_root / "previous-runtime-ready.json")
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
    value.add_argument("--revalidate-existing", action="store_true",
                       help="verify an existing installation and refresh evidence without OAuth or cloning")
    value.add_argument("--confirm-public-smoke", action="store_true",
                       help="authorize fixed public smoke requests for existing-runtime revalidation")
    return value


def main() -> int:
    args = parser().parse_args()
    try:
        if args.revalidate_existing:
            result = revalidate_existing_runtime(args.base_skill_dir,
                                                  confirm_public_smoke=args.confirm_public_smoke)
        else:
            result = install_runtime(args.base_skill_dir)
    except (RuntimeInstallError, subprocess.TimeoutExpired) as exc:
        print(json.dumps({"status": "BLOCKED", "error": str(exc)}, ensure_ascii=False, indent=2))
        return 2
    print(json.dumps({"status": "PASS", **result}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
