#!/usr/bin/env python3
"""Shared validation and receipt primitives for MPI Strategy M."""

from __future__ import annotations

import hashlib
import json
import os
import platform
import subprocess
import tempfile
import time
import uuid
from pathlib import Path
from typing import Iterable, Sequence


class StrategyMError(RuntimeError):
    pass


SKILL_DIR = Path(__file__).resolve().parents[1]
LOCK_PATH = SKILL_DIR / "dependency-lock.json"
READY_NAME = "READY.json"
RECEIPTS_NAME = "tool-execution-receipts.jsonl"
INSTRUCTION_RECEIPT_NAME = "instruction-receipt.json"
MANIFEST_NAME = "MANIFEST.json"
REQUIRED_SKILLS = (
    "skills/mpi-translation/SKILL.md",
    "skills/mpi-terms-search/SKILL.md",
    "skills/mpi-translation-review/SKILL.md",
)
SECRET_FLAGS = {"--api-key", "--apikey", "--token", "--secret", "--authorization"}


def managed_root() -> Path:
    override = os.environ.get("MPI_STRATEGY_M_ROOT")
    if override:
        return Path(override).expanduser().resolve()
    if platform.system() == "Darwin":
        return (Path.home() / "Library" / "Application Support" / "MPI-Strategy-M").resolve()
    if platform.system() == "Windows":
        base = os.environ.get("LOCALAPPDATA")
        if not base:
            raise StrategyMError("LOCALAPPDATA is not defined")
        return (Path(base) / "MPI-Strategy-M").resolve()
    raise StrategyMError("only Apple Silicon macOS and Windows 11 x64 are supported")


def platform_label() -> str:
    system = platform.system()
    machine = platform.machine().lower()
    if system == "Darwin" and machine in {"arm64", "aarch64"}:
        return "macos-arm64"
    if system == "Windows" and machine in {"amd64", "x86_64"}:
        return "windows-x64"
    return f"unsupported-{system.lower()}-{machine}"


def load_json(path: Path) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise StrategyMError(f"invalid JSON file: {path}") from exc
    if not isinstance(value, dict):
        raise StrategyMError(f"JSON root must be an object: {path}")
    return value


def load_lock() -> dict:
    return load_json(LOCK_PATH)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def file_record(path: Path) -> dict:
    resolved = path.expanduser().resolve()
    if not resolved.is_file():
        raise StrategyMError(f"required file is missing: {resolved}")
    return {
        "absolute_path": str(resolved),
        "sha256": sha256_file(resolved),
        "bytes": resolved.stat().st_size,
    }


def atomic_json(path: Path, value: dict) -> None:
    path = path.expanduser().resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    data = (json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile("wb", dir=path.parent, prefix=f".{path.name}.", delete=False) as handle:
            temporary = Path(handle.name)
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
        temporary = None
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def atomic_text(path: Path, value: str) -> None:
    path = path.expanduser().resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", newline="\n", dir=path.parent, prefix=f".{path.name}.", delete=False) as handle:
            temporary = Path(handle.name)
            handle.write(value)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
        temporary = None
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def run(command: Sequence[str], cwd: Path, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[bytes]:
    process_env = os.environ.copy()
    process_env["PYTHONDONTWRITEBYTECODE"] = "1"
    if env:
        process_env.update(env)
    try:
        return subprocess.run(
            [str(item) for item in command],
            cwd=cwd,
            env=process_env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
    except OSError as exc:
        raise StrategyMError(f"could not execute: {command[0]}") from exc


def git(path: Path, *arguments: str) -> str:
    completed = run(("git", *arguments), path)
    if completed.returncode:
        raise StrategyMError(f"git {' '.join(arguments[:2])} failed in {path}")
    return completed.stdout.decode("utf-8", errors="replace").strip()


def verify_repo(path: Path, spec: dict, critical_hashes: dict[str, str] | None = None) -> dict:
    path = path.expanduser().resolve()
    if not path.is_absolute() or not (path / ".git").exists():
        raise StrategyMError(f"repository is missing or not a Git checkout: {path}")
    origin = git(path, "remote", "get-url", "origin")
    head = git(path, "rev-parse", "HEAD")
    if origin != spec["origin"]:
        raise StrategyMError(f"origin mismatch for {path}: {origin}")
    if head != spec["expected_sha"]:
        raise StrategyMError(f"SHA mismatch for {path}: {head}")
    status = git(path, "status", "--porcelain=v1", "--untracked-files=all")
    if status:
        raise StrategyMError(f"locked repository is not clean: {path}")
    files: dict[str, str] = {}
    for relative in spec["required_files"]:
        candidate = path / relative
        if not candidate.is_file():
            raise StrategyMError(f"required locked file is missing: {candidate}")
        digest = sha256_file(candidate)
        files[relative] = digest
        if critical_hashes is not None and critical_hashes.get(relative) != digest:
            raise StrategyMError(f"critical file hash mismatch: {candidate}")
    result = {
        "absolute_path": str(path),
        "origin": origin,
        "git_sha": head,
        "expected_sha": spec["expected_sha"],
        "clean_worktree": True,
        "critical_file_sha256": files,
    }
    for key in ("compatibility_fork", "upstream_origin", "upstream_base_sha"):
        if key in spec:
            result[key] = spec[key]
    return result


def run_doctor(repo: Path, script: Path) -> tuple[int, bytes, bytes]:
    completed = run((os.fspath(Path(os.sys.executable)), os.fspath(script), "--strategy-c", "--json"), repo)
    try:
        report = json.loads(completed.stdout.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise StrategyMError(f"doctor did not return valid JSON: {script}") from exc
    if completed.returncode or not report.get("ok"):
        raise StrategyMError(f"doctor failed: {script}")
    return completed.returncode, completed.stdout, completed.stderr


def load_ready(root: Path | None = None, require_ready: bool = True) -> dict:
    root = (root or managed_root()).resolve()
    ready = load_json(root / READY_NAME)
    if require_ready and ready.get("ready") is not True:
        raise StrategyMError("installation is not production-ready")
    return ready


def verify_ready(root: Path | None = None, require_ready: bool = True) -> tuple[dict, dict, dict]:
    root = (root or managed_root()).resolve()
    lock = load_lock()
    if require_ready and lock.get("release_ready") is not True:
        raise StrategyMError("public release lock is not ready")
    ready = load_ready(root, require_ready=require_ready)
    if ready.get("schema_version") != 1 or ready.get("skill_version") != lock["skill_version"]:
        raise StrategyMError("READY schema or skill version mismatch")
    for field in ("strategy_id", "workflow_version", "terminology_policy_version"):
        if ready.get(field) != lock.get(field):
            raise StrategyMError(f"READY {field} does not match the release lock")
    if ready.get("models") != lock.get("models"):
        raise StrategyMError("READY model roles do not match the release lock")
    mpi_ready = ready.get("mpi_translations", {})
    toolkit_ready = ready.get("translation_toolkit", {})
    mpi = verify_repo(Path(mpi_ready.get("absolute_path", "")), lock["mpi_translations"], mpi_ready.get("critical_file_sha256"))
    toolkit = verify_repo(Path(toolkit_ready.get("absolute_path", "")), lock["translation_toolkit"], toolkit_ready.get("critical_file_sha256"))
    if Path(toolkit["absolute_path"]).parent != Path(mpi["absolute_path"]):
        raise StrategyMError("toolkit is not the real MPI submodule checkout")
    submodule = run(("git", "submodule", "status", "--", lock["translation_toolkit"]["submodule_path"]), Path(mpi["absolute_path"]))
    status = submodule.stdout.decode("utf-8", errors="replace").rstrip("\r\n")
    marker = status[:1]
    actual = status[1:41] if marker in {" ", "-", "+", "U"} else status.split()[0] if status else ""
    if submodule.returncode or marker in {"-", "+", "U"} or actual != toolkit["git_sha"]:
        raise StrategyMError("toolkit is not an initialized, exact MPI Git submodule")
    mpi_code, mpi_out, _ = run_doctor(Path(mpi["absolute_path"]), Path(mpi["absolute_path"]) / "scripts" / "doctor.py")
    toolkit_code, toolkit_out, _ = run_doctor(Path(toolkit["absolute_path"]), Path(toolkit["absolute_path"]) / "scripts" / "doctor.py")
    mpi["doctor_exit_code"] = mpi_code
    mpi["doctor_report_sha256"] = sha256_bytes(mpi_out)
    toolkit["doctor_exit_code"] = toolkit_code
    toolkit["doctor_report_sha256"] = sha256_bytes(toolkit_out)
    return ready, mpi, toolkit


def instruction_files(mpi: Path, toolkit: Path) -> list[Path]:
    return [mpi / "AGENTS.md", toolkit / "AGENTS.md", *(toolkit / item for item in REQUIRED_SKILLS)]


def begin_project(project: Path, input_type: str, root: Path | None = None, require_ready: bool = True) -> dict:
    ready, mpi_info, toolkit_info = verify_ready(root, require_ready=require_ready)
    project = project.expanduser().resolve()
    project.mkdir(parents=True, exist_ok=True)
    if (project / "target.dj").exists():
        raise StrategyMError("target.dj exists before instruction receipt; use a new project or validated resume")
    mpi = Path(mpi_info["absolute_path"])
    toolkit = Path(toolkit_info["absolute_path"])
    timestamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    records = []
    for path in instruction_files(mpi, toolkit):
        record = file_record(path)
        record.update({"repository_sha": mpi_info["git_sha"] if path == mpi / "AGENTS.md" else toolkit_info["git_sha"], "read_at": timestamp})
        records.append(record)
    receipt = {
        "schema_version": 1,
        "receipt_id": str(uuid.uuid4()),
        "strategy_id": ready["strategy_id"],
        "workflow_version": ready["workflow_version"],
        "terminology_policy_version": ready["terminology_policy_version"],
        "input_type": input_type,
        "created_at": timestamp,
        "ready_sha256": sha256_file((root or managed_root()).resolve() / READY_NAME),
        "mpi_translations": mpi_info,
        "translation_toolkit": toolkit_info,
        "instructions": records,
    }
    atomic_json(project / INSTRUCTION_RECEIPT_NAME, receipt)
    return receipt


def validate_instruction_receipt(project: Path) -> dict:
    project = project.expanduser().resolve()
    receipt = load_json(project / INSTRUCTION_RECEIPT_NAME)
    for item in receipt.get("instructions", []):
        path = Path(item["absolute_path"])
        if not path.is_file() or sha256_file(path) != item["sha256"] or path.stat().st_size != item["bytes"]:
            raise StrategyMError(f"instruction changed after receipt: {path}")
    if len(receipt.get("instructions", [])) != 5:
        raise StrategyMError("instruction receipt is incomplete")
    return receipt


def file_hashes(paths: Iterable[Path], require: bool = True) -> list[dict]:
    records = []
    for path in paths:
        resolved = path.expanduser().resolve()
        if not resolved.exists() and not require:
            continue
        records.append(file_record(resolved))
    return records


def append_receipt(project: Path, receipt: dict) -> None:
    path = project.expanduser().resolve() / RECEIPTS_NAME
    path.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(receipt, ensure_ascii=False, sort_keys=True) + "\n"
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(line)
        handle.flush()
        os.fsync(handle.fileno())


def read_receipts(project: Path) -> list[dict]:
    path = project.expanduser().resolve() / RECEIPTS_NAME
    if not path.is_file():
        return []
    receipts = []
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        try:
            item = json.loads(line)
        except json.JSONDecodeError as exc:
            raise StrategyMError(f"invalid receipt JSON at line {number}") from exc
        receipts.append(item)
    return receipts


def reject_secret_arguments(arguments: Sequence[str]) -> None:
    for argument in arguments:
        name = argument.split("=", 1)[0].casefold()
        if name in SECRET_FLAGS or name.endswith("api_key") or name.endswith("api-key"):
            raise StrategyMError("credentials are forbidden in command arguments")
