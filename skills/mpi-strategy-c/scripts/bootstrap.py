#!/usr/bin/env python3
"""One-time locked installation for MPI Strategy C."""

from __future__ import annotations

import os
import platform
import shutil
import subprocess
import sys
import time
import uuid
from pathlib import Path

from runtime import (
    READY_NAME,
    StrategyCError,
    atomic_json,
    load_lock,
    managed_root,
    platform_label,
    run,
    run_doctor,
    sha256_bytes,
    sha256_file,
    verify_repo,
)


def executable(name: str) -> str | None:
    return shutil.which(name)


def install_system_dependencies() -> None:
    system = platform.system()
    if system == "Darwin":
        brew = executable("brew")
        if not brew:
            raise StrategyCError("Homebrew is required for automatic macOS dependency installation")
        completed = run((brew, "install", "git", "cmake", "pandoc", "ffmpeg"), Path.cwd())
        if completed.returncode:
            raise StrategyCError("Homebrew dependency installation failed")
    elif system == "Windows":
        winget = executable("winget")
        if not winget:
            raise StrategyCError("winget is required for automatic Windows dependency installation")
        packages = ("Git.Git", "Kitware.CMake", "JohnMacFarlane.Pandoc", "Gyan.FFmpeg")
        for package in packages:
            completed = run((winget, "install", "--id", package, "--exact", "--accept-package-agreements", "--accept-source-agreements"), Path.cwd())
            if completed.returncode:
                raise StrategyCError(f"winget failed to install {package}")
        links = Path(os.environ.get("LOCALAPPDATA", "")) / "Microsoft" / "WinGet" / "Links"
        if links.is_dir():
            os.environ["PATH"] = str(links) + os.pathsep + os.environ.get("PATH", "")
    else:
        raise StrategyCError("unsupported platform")
    completed = run((sys.executable, "-m", "pip", "install", "keyring>=25,<27"), Path.cwd())
    if completed.returncode:
        raise StrategyCError("could not install Python keyring")


def require_dependencies(install_missing: bool) -> None:
    required = ("git", "cmake", "pandoc", "ffmpeg")
    missing = [name for name in required if not executable(name)]
    try:
        import keyring  # noqa: F401
    except ImportError:
        missing.append("python-keyring")
    if missing and install_missing:
        install_system_dependencies()
        missing = [name for name in required if not executable(name)]
        try:
            import keyring  # noqa: F401
        except ImportError:
            missing.append("python-keyring")
    if missing:
        raise StrategyCError("missing dependencies: " + ", ".join(sorted(set(missing))))


def git_checked(command: tuple[str, ...], cwd: Path) -> None:
    completed = run(command, cwd)
    if completed.returncode:
        raise StrategyCError(f"Git command failed: {' '.join(command[:3])}")


def clone_locked(
    source: str,
    destination: Path,
    expected_sha: str,
    canonical_origin: str,
    sparse_paths: tuple[str, ...] = (),
) -> None:
    git_checked(("git", "-c", "core.autocrlf=false", "clone", "--filter=blob:none", "--no-checkout", source, str(destination)), destination.parent)
    git_checked(("git", "-C", str(destination), "config", "core.autocrlf", "false"), destination.parent)
    if sparse_paths:
        git_checked(("git", "-C", str(destination), "sparse-checkout", "init", "--cone"), destination.parent)
        git_checked(("git", "-C", str(destination), "sparse-checkout", "set", *sparse_paths), destination.parent)
    git_checked(("git", "-C", str(destination), "checkout", "--detach", expected_sha), destination.parent)
    git_checked(("git", "-C", str(destination), "remote", "set-url", "origin", canonical_origin), destination.parent)


def prepare_repositories(root: Path, lock: dict, candidate_mpi: Path | None, candidate_toolkit: Path | None) -> tuple[Path, Path]:
    repos = root / "repos"
    repos.mkdir(parents=True, exist_ok=True)
    staging = repos / f".install-{uuid.uuid4()}"
    staging.mkdir()
    mpi = staging / "mpi-translations"
    mpi_spec = lock["mpi_translations"]
    toolkit_spec = lock["translation_toolkit"]
    clone_locked(
        str(candidate_mpi or mpi_spec["origin"]),
        mpi,
        mpi_spec["expected_sha"],
        mpi_spec["origin"],
        ("scripts", toolkit_spec["submodule_path"]),
    )
    pointer = run(("git", "ls-tree", "HEAD", toolkit_spec["submodule_path"]), mpi)
    if pointer.returncode or toolkit_spec["expected_sha"] not in pointer.stdout.decode("utf-8", errors="replace"):
        raise StrategyCError("MPI commit does not point to the locked toolkit SHA")
    toolkit = mpi / toolkit_spec["submodule_path"]
    if candidate_toolkit:
        clone_locked(str(candidate_toolkit), toolkit, toolkit_spec["expected_sha"], toolkit_spec["origin"])
        git_checked(("git", "config", f"submodule.{toolkit_spec['submodule_path']}.url", toolkit_spec["origin"]), mpi)
        git_checked(("git", "config", f"submodule.{toolkit_spec['submodule_path']}.active", "true"), mpi)
        git_checked(("git", "submodule", "absorbgitdirs"), mpi)
    else:
        git_checked(("git", "config", f"submodule.{toolkit_spec['submodule_path']}.url", toolkit_spec["origin"]), mpi)
        git_checked((
            "git", "submodule", "update", "--init", "--checkout",
            "--depth", "1", "--filter=blob:none", toolkit_spec["submodule_path"],
        ), mpi)
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


def build_whisper(root: Path, lock: dict) -> Path:
    spec = lock["whisper"]
    source = root / "whisper.cpp"
    if not source.exists():
        clone_locked(spec["engine_origin"], source, spec["engine_sha"], spec["engine_origin"])
    build = source / "build"
    completed = run(("cmake", "-S", str(source), "-B", str(build), "-DWHISPER_BUILD_TESTS=OFF", "-DWHISPER_BUILD_EXAMPLES=ON"), source)
    if completed.returncode:
        raise StrategyCError("whisper.cpp configuration failed")
    completed = run(("cmake", "--build", str(build), "--config", "Release", "--parallel", "2"), source)
    if completed.returncode:
        raise StrategyCError("whisper.cpp build failed")
    candidates = (build / "bin" / "whisper-cli", build / "bin" / "Release" / "whisper-cli.exe")
    for candidate in candidates:
        if candidate.is_file():
            return candidate.resolve()
    raise StrategyCError("whisper-cli was not produced")


def install(
    model_path: Path,
    install_missing: bool = True,
    development_candidate: bool = False,
    candidate_mpi: Path | None = None,
    candidate_toolkit: Path | None = None,
    skip_credential_for_smoke: bool = False,
) -> dict:
    lock = load_lock()
    if not lock.get("release_ready") and not development_candidate:
        raise StrategyCError("public installation blocked: the verified release lock is not ready")
    root = managed_root()
    root.mkdir(parents=True, exist_ok=True)
    require_dependencies(install_missing)
    if model_path.name != lock["whisper"]["model_filename"] or sha256_file(model_path) != lock["whisper"]["model_sha256"]:
        raise StrategyCError("selected Whisper model does not match the locked filename and SHA-256")
    if not skip_credential_for_smoke:
        try:
            import keyring
        except ImportError as exc:
            raise StrategyCError("Python keyring is missing") from exc
        if not keyring.get_password("mpi-strategy-c-deepseek", "default"):
            raise StrategyCError("DeepSeek credential is not present in the operating-system vault")
    mpi, toolkit = prepare_repositories(root, lock, candidate_mpi, candidate_toolkit)
    whisper_cli = build_whisper(root, lock)
    mpi_code, mpi_report, _ = run_doctor(mpi, mpi / "scripts" / "doctor.py")
    toolkit_code, toolkit_report, _ = run_doctor(toolkit, toolkit / "scripts" / "doctor.py")
    mpi_info = verify_repo(mpi, lock["mpi_translations"])
    toolkit_info = verify_repo(toolkit, lock["translation_toolkit"])
    for info, repo, report, code in ((mpi_info, mpi, mpi_report, mpi_code), (toolkit_info, toolkit, toolkit_report, toolkit_code)):
        info.update({
            "agents_path": str((repo / "AGENTS.md").resolve()),
            "agents_sha256": sha256_file(repo / "AGENTS.md"),
            "doctor_exit_code": code,
            "doctor_report_sha256": sha256_bytes(report),
        })
    ready = {
        "schema_version": 1,
        "ready": False,
        "candidate_installation": development_candidate,
        "platform": platform_label(),
        "skill_version": lock["skill_version"],
        "mpi_translations": mpi_info,
        "translation_toolkit": toolkit_info,
        "whisper": {
            "model_absolute_path": str(model_path.resolve()),
            "model_sha256": sha256_file(model_path),
            "executable_absolute_path": str(whisper_cli),
            "executable_sha256": sha256_file(whisper_cli),
            "engine_origin": lock["whisper"]["engine_origin"],
            "engine_sha": lock["whisper"]["engine_sha"],
        },
    }
    atomic_json(root / READY_NAME, ready)
    from fault_injection import run_fault_tests

    fault_report = run_fault_tests(root)
    ready["fault_injection_report_path"] = fault_report["report_absolute_path"]
    ready["fault_injection_report_sha256"] = fault_report["report_sha256"]
    if development_candidate and skip_credential_for_smoke:
        ready["smoke_test_status"] = "SKIPPED_DEVELOPMENT_CANDIDATE"
    else:
        from smoke_test import run_smoke_test

        smoke_report = run_smoke_test(root, toolkit)
        ready["smoke_test_report_path"] = smoke_report["report_absolute_path"]
        ready["smoke_test_report_sha256"] = smoke_report["report_sha256"]
        ready["smoke_test_status"] = smoke_report["status"]
    ready["ready"] = (
        bool(lock.get("release_ready"))
        and not development_candidate
        and ready.get("smoke_test_status") == "PASS"
    )
    atomic_json(root / READY_NAME, ready)
    return ready
