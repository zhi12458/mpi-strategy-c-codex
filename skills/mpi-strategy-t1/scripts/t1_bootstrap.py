#!/usr/bin/env python3
"""Locked installation and readiness verification for MPI T1."""

from __future__ import annotations

import os
import platform
import shutil
import sys
import time
import uuid
from pathlib import Path

from t1_runtime import (
    READY_NAME,
    StrategyT1Error,
    atomic_json,
    deepseek_credential_present,
    executable,
    load_json,
    load_lock,
    load_personal_confirmation,
    managed_root,
    omp_report,
    platform_label,
    require_dependencies,
    run,
    run_doctor,
    sha256_file,
    utc_now,
    verify_manifest,
    verify_repo,
)


def install_system_dependencies() -> None:
    """Install only after the caller has obtained native administrator consent."""
    system = platform.system()
    if system == "Darwin":
        brew = executable("brew")
        if not brew:
            raise StrategyT1Error("Homebrew is required for automatic macOS dependency installation")
        for command in (
            (brew, "install", "git", "pandoc", "python@3.11"),
            (brew, "install", "--cask", "libreoffice"),
        ):
            completed = run(command, Path.cwd(), timeout=1800)
            if completed.returncode:
                raise StrategyT1Error("Homebrew dependency installation failed")
    elif system == "Windows":
        winget = executable("winget")
        if not winget:
            raise StrategyT1Error("winget is required for automatic Windows dependency installation")
        for package in (
            "Git.Git",
            "Python.Python.3.11",
            "JohnMacFarlane.Pandoc",
            "TheDocumentFoundation.LibreOffice",
        ):
            completed = run(
                (
                    winget,
                    "install",
                    "--id",
                    package,
                    "--exact",
                    "--accept-package-agreements",
                    "--accept-source-agreements",
                ),
                Path.cwd(),
                timeout=1800,
            )
            if completed.returncode:
                raise StrategyT1Error(f"winget failed to install {package}")
    else:
        raise StrategyT1Error("automatic system dependency installation is limited to macOS and Windows")
    completed = run(
        (sys.executable, "-m", "pip", "install", "keyring>=25,<27"),
        Path.cwd(),
        timeout=600,
    )
    if completed.returncode:
        raise StrategyT1Error("could not install Python keyring")
    # PyYAML enables only the explicit T1.1.2 pilot. Its installation failure
    # must not disable the T1.0.1 production baseline; readiness records the
    # pilot capability as blocked instead.
    run(
        (sys.executable, "-m", "pip", "install", "PyYAML>=6,<7"),
        Path.cwd(),
        timeout=600,
    )


def git_checked(command: tuple[str, ...], cwd: Path) -> None:
    completed = run(command, cwd, timeout=600)
    if completed.returncode:
        detail = completed.stderr.decode("utf-8", errors="replace").strip().splitlines()
        suffix = f": {detail[-1]}" if detail else ""
        raise StrategyT1Error(f"Git command failed: {' '.join(command[:3])}{suffix}")


def clone_locked(source: str, destination: Path, expected_sha: str, canonical_origin: str) -> None:
    local_source = Path(source).expanduser()
    if local_source.exists():
        command = (
            "git",
            "-c",
            "core.autocrlf=false",
            "clone",
            "--local",
            "--no-hardlinks",
            "--no-checkout",
            str(local_source.resolve()),
            str(destination),
        )
    else:
        command = (
            "git",
            "-c",
            "core.autocrlf=false",
            "clone",
            "--filter=blob:none",
            "--no-checkout",
            source,
            str(destination),
        )
    git_checked(command, destination.parent)
    git_checked(("git", "-C", str(destination), "config", "core.autocrlf", "false"), destination.parent)
    git_checked(("git", "-C", str(destination), "checkout", "--detach", expected_sha), destination.parent)
    git_checked(
        ("git", "-C", str(destination), "remote", "set-url", "origin", canonical_origin),
        destination.parent,
    )


def prepare_repositories(
    root: Path,
    lock: dict,
    candidate_mpi: Path | None = None,
    candidate_toolkit: Path | None = None,
) -> tuple[Path, Path]:
    repos = root / "repos"
    repos.mkdir(parents=True, exist_ok=True)
    staging = repos / f".install-{uuid.uuid4()}"
    staging.mkdir()
    mpi = staging / "mpi-translations"
    mpi_spec = lock["mpi_translations"]
    toolkit_spec = lock["translation_toolkit"]
    clone_locked(str(candidate_mpi or mpi_spec["origin"]), mpi, mpi_spec["expected_sha"], mpi_spec["origin"])
    pointer = run(("git", "ls-tree", "HEAD", toolkit_spec["submodule_path"]), mpi, timeout=120)
    if pointer.returncode or toolkit_spec["expected_sha"] not in pointer.stdout.decode("utf-8", errors="replace"):
        raise StrategyT1Error("MPI commit does not point to the locked toolkit SHA")
    toolkit = mpi / toolkit_spec["submodule_path"]
    git_checked(
        ("git", "config", f"submodule.{toolkit_spec['submodule_path']}.url", toolkit_spec["origin"]),
        mpi,
    )
    if candidate_toolkit:
        clone_locked(
            str(candidate_toolkit),
            toolkit,
            toolkit_spec["expected_sha"],
            toolkit_spec["origin"],
        )
        git_checked(("git", "config", f"submodule.{toolkit_spec['submodule_path']}.active", "true"), mpi)
        git_checked(("git", "submodule", "absorbgitdirs"), mpi)
    else:
        git_checked(
            (
                "git",
                "submodule",
                "update",
                "--init",
                "--checkout",
                "--depth",
                "1",
                "--filter=blob:none",
                toolkit_spec["submodule_path"],
            ),
            mpi,
        )
        git_checked(("git", "-C", str(toolkit), "checkout", "--detach", toolkit_spec["expected_sha"]), mpi)
    verify_repo(mpi, mpi_spec)
    verify_repo(toolkit, toolkit_spec)

    final = repos / "mpi-translations"
    backup: Path | None = None
    if final.exists():
        backup = repos / f"mpi-translations.previous-{int(time.time())}-{uuid.uuid4().hex[:8]}"
        os.replace(final, backup)
    try:
        os.replace(mpi, final)
    except OSError:
        if backup is not None and not final.exists():
            os.replace(backup, final)
        raise
    staging.rmdir()
    return final, final / toolkit_spec["submodule_path"]


def repository_evidence(mpi: Path, toolkit: Path, lock: dict) -> tuple[dict, dict]:
    mpi_info = verify_repo(mpi, lock["mpi_translations"])
    toolkit_info = verify_repo(toolkit, lock["translation_toolkit"])
    for info, repo in ((mpi_info, mpi), (toolkit_info, toolkit)):
        info["agents_sha256"] = sha256_file(repo / "AGENTS.md")
        info["doctor"] = run_doctor(repo)
    return mpi_info, toolkit_info


def install(
    *,
    install_missing: bool = False,
    confirm_public_smoke: bool = False,
    candidate_mpi: Path | None = None,
    candidate_toolkit: Path | None = None,
) -> dict:
    lock = load_lock()
    if lock.get("release_ready") is not True:
        raise StrategyT1Error("public T1 installer lock is not release-ready")
    if not confirm_public_smoke:
        raise StrategyT1Error("public live smoke requires --confirm-public-smoke")
    root = managed_root()
    root.mkdir(parents=True, exist_ok=True)
    if install_missing:
        install_system_dependencies()
    manifest = verify_manifest()
    dependencies = require_dependencies(lock)
    omp = omp_report(lock)
    personal = load_personal_confirmation(root)
    if not deepseek_credential_present(lock):
        raise StrategyT1Error("DeepSeek credential is missing from the T1 operating-system vault")
    mpi, toolkit = prepare_repositories(root, lock, candidate_mpi, candidate_toolkit)
    mpi_info, toolkit_info = repository_evidence(mpi, toolkit, lock)
    ready = {
        "schema_version": 1,
        "ready": False,
        "strategy_id": lock["strategy_id"],
        "workflow_version": lock["workflow_version"],
        "installer_version": lock["installer_version"],
        "created_at": utc_now(),
        "platform": platform_label(),
        "skill_manifest": manifest,
        "dependencies": dependencies,
        "omp": omp,
        "personal_workspace_confirmation": personal,
        "deepseek_credential": {
            "present": True,
            "service": lock["credential_policy"]["deepseek_service"],
            "secret_recorded": False,
        },
        "models": lock["models"],
        "mpi_translations": mpi_info,
        "translation_toolkit": toolkit_info,
    }
    atomic_json(root / READY_NAME, ready)

    from t1_fault_injection import run_fault_tests
    from t1_smoke_test import run_smoke_test

    semantic_contracts = optional_semantic_contracts(root, dependencies)
    pretranslation_contracts = optional_pretranslation_contracts(root)
    fault = run_fault_tests(root)
    smoke = run_smoke_test(root, toolkit, lock)
    ready["fault_injection"] = {
        "status": fault["status"],
        "path": fault["report_absolute_path"],
        "sha256": fault["report_sha256"],
    }
    ready["semantic_restructuring_contracts"] = {
        "status": semantic_contracts["status"],
        "path": semantic_contracts.get("report_absolute_path"),
        "sha256": semantic_contracts.get("report_sha256"),
        "error": semantic_contracts.get("error"),
        "required_for_production_baseline": False,
        "required_for_t1_1_2_pilot": True,
    }
    ready["pretranslation_contracts"] = {
        "status": pretranslation_contracts["status"],
        "path": pretranslation_contracts.get("report_absolute_path"),
        "sha256": pretranslation_contracts.get("report_sha256"),
        "error": pretranslation_contracts.get("error"),
        "required_for_production_baseline": False,
        "required_for_t1_2_tracks": True,
    }
    ready["smoke_test"] = {
        "status": smoke["status"],
        "path": smoke["report_absolute_path"],
        "sha256": smoke["report_sha256"],
    }
    ready["ready"] = fault["status"] == smoke["status"] == "PASS"
    ready["completed_at"] = utc_now()
    atomic_json(root / READY_NAME, ready)
    return ready


def optional_semantic_contracts(root: Path, dependencies: dict) -> dict:
    """Isolate the optional pilot gate from T1.0.1 baseline readiness."""
    if not dependencies.get("pyyaml"):
        return {
            "status": "BLOCKED",
            "error": "T1.1.2 semantic restructuring requires Python PyYAML",
        }
    try:
        from semantic_bridge import run_contract_tests

        return run_contract_tests(root)
    except StrategyT1Error as exc:
        return {
            "status": "BLOCKED",
            "error": str(exc),
        }
    except Exception as exc:
        return {
            "status": "BLOCKED",
            "error": f"{type(exc).__name__}: {exc}",
        }


def optional_pretranslation_contracts(root: Path) -> dict:
    """Keep T1.2 track readiness separate from the T1.0.1 fallback baseline."""
    try:
        from pretranslation import run_contract_tests

        return run_contract_tests(root)
    except StrategyT1Error as exc:
        return {"status": "BLOCKED", "error": str(exc)}
    except Exception as exc:
        return {
            "status": "BLOCKED",
            "error": f"{type(exc).__name__}: {exc}",
        }


def verify_ready(
    root: Path | None = None,
    require_ready: bool = True,
    require_semantic_restructuring: bool = False,
    require_pretranslation: bool = False,
) -> dict:
    root = (root or managed_root()).resolve()
    lock = load_lock()
    ready = load_json(root / READY_NAME)
    if require_ready and ready.get("ready") is not True:
        raise StrategyT1Error("T1 installation is not production-ready")
    for field in ("strategy_id", "workflow_version", "installer_version"):
        if ready.get(field) != lock.get(field):
            raise StrategyT1Error(f"READY {field} does not match the lock")
    manifest = verify_manifest()
    if ready.get("skill_manifest", {}).get("sha256") != manifest["sha256"]:
        raise StrategyT1Error("READY skill manifest is stale")
    dependencies = require_dependencies(lock)
    if require_semantic_restructuring and not dependencies.get("pyyaml"):
        raise StrategyT1Error(
            "T1.1.2 semantic restructuring requires Python PyYAML"
        )
    current_omp = omp_report(lock)
    if ready.get("omp", {}).get("version") != current_omp["version"]:
        raise StrategyT1Error("READY OMP version is stale")
    load_personal_confirmation(root)
    if not deepseek_credential_present(lock):
        raise StrategyT1Error("DeepSeek credential is missing")
    mpi_info = ready.get("mpi_translations", {})
    toolkit_info = ready.get("translation_toolkit", {})
    mpi = Path(mpi_info.get("absolute_path", ""))
    toolkit = Path(toolkit_info.get("absolute_path", ""))
    verify_repo(mpi, lock["mpi_translations"], mpi_info.get("critical_file_sha256"))
    verify_repo(toolkit, lock["translation_toolkit"], toolkit_info.get("critical_file_sha256"))
    if toolkit.parent != mpi:
        raise StrategyT1Error("toolkit is not the managed MPI submodule checkout")
    run_doctor(mpi)
    run_doctor(toolkit)
    for name in ("fault_injection", "smoke_test"):
        evidence = ready.get(name, {})
        path = Path(evidence.get("path", ""))
        if evidence.get("status") != "PASS" or not path.is_file() or sha256_file(path) != evidence.get("sha256"):
            raise StrategyT1Error(f"READY {name} evidence is missing or stale")
    if require_semantic_restructuring:
        evidence = ready.get("semantic_restructuring_contracts", {})
        path = Path(evidence.get("path") or "")
        if (
            evidence.get("status") != "PASS"
            or not path.is_file()
            or sha256_file(path) != evidence.get("sha256")
        ):
            raise StrategyT1Error(
                "T1.1.2 semantic-restructuring capability is unavailable or stale"
            )
    if require_pretranslation:
        evidence = ready.get("pretranslation_contracts", {})
        path = Path(evidence.get("path") or "")
        if (
            evidence.get("status") != "PASS"
            or not path.is_file()
            or sha256_file(path) != evidence.get("sha256")
        ):
            raise StrategyT1Error(
                "T1.2 pretranslation-track capability is unavailable or stale"
            )
    return ready
