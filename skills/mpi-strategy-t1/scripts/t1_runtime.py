#!/usr/bin/env python3
"""Validation and audit primitives for the MPI T1 installer."""

from __future__ import annotations

import hashlib
import json
import os
import platform
import re
import shutil
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Sequence


class StrategyT1Error(RuntimeError):
    """A T1 safety or readiness gate failed."""


SKILL_DIR = Path(__file__).resolve().parents[1]
LOCK_PATH = SKILL_DIR / "dependency-lock.json"
MANIFEST_PATH = SKILL_DIR / "MANIFEST.sha256"
READY_NAME = "READY.json"
ACCOUNT_CONFIRMATION_NAME = "personal-workspace-confirmation.json"
SECRET_FLAGS = {"--api-key", "--apikey", "--token", "--secret", "--authorization"}


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
            raise StrategyT1Error("LOCALAPPDATA is not defined")
        return (Path(base) / "MPI-Strategy-T1").resolve()
    if system == "Linux":
        base = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))
        return (base / "mpi-strategy-t1").resolve()
    raise StrategyT1Error(f"unsupported platform: {system}")


def platform_label() -> str:
    return f"{platform.system().lower()}-{platform.machine().lower()}"


def load_json(path: Path) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise StrategyT1Error(f"invalid JSON file: {path}") from exc
    if not isinstance(value, dict):
        raise StrategyT1Error(f"JSON root must be an object: {path}")
    return value


def load_lock() -> dict:
    return load_json(LOCK_PATH)


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


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


def run(
    command: Sequence[str],
    cwd: Path,
    env: dict[str, str] | None = None,
    timeout: int | None = None,
) -> subprocess.CompletedProcess[bytes]:
    reject_secret_arguments(command)
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
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise StrategyT1Error(f"command timed out: {command[0]}") from exc
    except OSError as exc:
        raise StrategyT1Error(f"could not execute: {command[0]}") from exc
    finally:
        if env:
            for key in list(env):
                env.pop(key, None)


def reject_secret_arguments(arguments: Sequence[str]) -> None:
    for argument in arguments:
        name = str(argument).split("=", 1)[0].casefold()
        if name in SECRET_FLAGS or name.endswith("api_key") or name.endswith("api-key"):
            raise StrategyT1Error("credentials are forbidden in command arguments")


def verify_manifest() -> dict:
    if not MANIFEST_PATH.is_file():
        raise StrategyT1Error("T1 MANIFEST.sha256 is missing")
    files: dict[str, str] = {}
    for number, line in enumerate(MANIFEST_PATH.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        match = re.fullmatch(r"([0-9a-f]{64})  (.+)", line)
        if not match:
            raise StrategyT1Error(f"invalid manifest line {number}")
        expected, relative = match.groups()
        candidate = SKILL_DIR / relative
        if not candidate.is_file() or sha256_file(candidate) != expected:
            raise StrategyT1Error(f"skill manifest mismatch: {relative}")
        files[relative] = expected
    required = {"SKILL.md", "dependency-lock.json", "references/production-lock.json"}
    if not required.issubset(files):
        raise StrategyT1Error("skill manifest omits a required T1 file")
    actual = {
        path.relative_to(SKILL_DIR).as_posix()
        for path in SKILL_DIR.rglob("*")
        if path.is_file()
        and path != MANIFEST_PATH
        and "__pycache__" not in path.parts
        and path.suffix not in {".pyc", ".pyo"}
    }
    if set(files) != actual:
        missing = sorted(actual - set(files))
        stale = sorted(set(files) - actual)
        detail = []
        if missing:
            detail.append("unlisted=" + ",".join(missing))
        if stale:
            detail.append("missing=" + ",".join(stale))
        raise StrategyT1Error("skill manifest coverage mismatch: " + "; ".join(detail))
    return {"path": str(MANIFEST_PATH), "sha256": sha256_file(MANIFEST_PATH), "files": files}


def executable(name: str) -> str | None:
    value = shutil.which(name)
    if value:
        return str(Path(value).resolve())
    if name in {"libreoffice", "soffice"} and platform.system() == "Darwin":
        candidate = Path("/Applications/LibreOffice.app/Contents/MacOS/soffice")
        if candidate.is_file():
            return str(candidate)
    return None


def dependency_report(lock: dict) -> dict:
    minimum = tuple(int(item) for item in lock["python"]["minimum_version"].split("."))
    python_ok = tuple(os.sys.version_info[:2]) >= minimum
    commands = {name: executable(name) for name in lock["system_dependencies"]["required_commands"]}
    renderers = [
        executable(name) for name in lock["system_dependencies"]["docx_renderer_candidates"]
    ]
    try:
        import keyring  # noqa: F401

        keyring_ok = True
    except ImportError:
        keyring_ok = False
    try:
        import yaml  # noqa: F401

        yaml_ok = True
    except ImportError:
        yaml_ok = False
    missing = [name for name, path in commands.items() if not path]
    if not any(renderers):
        missing.append("libreoffice/soffice")
    if not python_ok:
        missing.append(f"python>={lock['python']['minimum_version']}")
    if not keyring_ok:
        missing.append("python-keyring")
    return {
        "ok": not missing,
        "python": {"version": platform.python_version(), "ok": python_ok},
        "commands": commands,
        "docx_renderer": next((item for item in renderers if item), None),
        "keyring": keyring_ok,
        "pyyaml": yaml_ok,
        "missing": missing,
    }


def require_dependencies(lock: dict) -> dict:
    report = dependency_report(lock)
    if not report["ok"]:
        raise StrategyT1Error("missing dependencies: " + ", ".join(report["missing"]))
    return report


def omp_report(lock: dict) -> dict:
    omp = executable(lock["omp"]["executable"])
    if not omp:
        raise StrategyT1Error("OMP is missing; install the exact locked version first")
    version_call = run((omp, "--version"), SKILL_DIR, timeout=30)
    version_text = version_call.stdout.decode("utf-8", errors="replace").strip()
    match = re.search(r"(\d+\.\d+\.\d+)", version_text)
    version = match.group(1) if match else ""
    if version_call.returncode or version != lock["omp"]["validated_version"]:
        raise StrategyT1Error(
            f"OMP version mismatch: expected {lock['omp']['validated_version']}, got {version or 'unknown'}"
        )
    models_call = run((omp, "models", "--json"), SKILL_DIR, timeout=60)
    if models_call.returncode:
        raise StrategyT1Error("OMP model catalog lookup failed")
    try:
        model_payload = json.loads(models_call.stdout.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise StrategyT1Error("OMP model catalog is not valid JSON") from exc
    models = model_payload.get("models", []) if isinstance(model_payload, dict) else []
    by_selector = {item.get("selector"): item for item in models if isinstance(item, dict)}
    selected: dict[str, dict] = {}
    for role, spec in lock["models"].items():
        item = by_selector.get(spec["selector"])
        if not item or spec["reasoning_effort"] not in item.get("thinking", []):
            raise StrategyT1Error(f"locked OMP model or effort is unavailable: {spec['selector']}")
        selected[role] = {
            "selector": spec["selector"],
            "thinking": item.get("thinking", []),
            "context_window": item.get("contextWindow"),
        }
    return {
        "executable": omp,
        "version": version,
        "catalog_sha256": sha256_bytes(models_call.stdout),
        "models": selected,
    }


def deepseek_credential_present(lock: dict) -> bool:
    try:
        import keyring
    except ImportError as exc:
        raise StrategyT1Error("Python keyring is required") from exc
    policy = lock["credential_policy"]
    try:
        return bool(keyring.get_password(policy["deepseek_service"], policy["deepseek_account"]))
    except Exception as exc:
        raise StrategyT1Error("the operating-system credential vault is unavailable") from exc


def load_personal_confirmation(root: Path | None = None) -> dict:
    confirmation = load_json((root or managed_root()) / ACCOUNT_CONFIRMATION_NAME)
    if confirmation.get("confirmed") is not True or confirmation.get("provider") != "openai-codex":
        raise StrategyT1Error("Personal OpenAI workspace has not been confirmed")
    return confirmation


def git(path: Path, *arguments: str) -> str:
    completed = run(("git", *arguments), path, timeout=120)
    if completed.returncode:
        raise StrategyT1Error(f"git {' '.join(arguments[:2])} failed in {path}")
    return completed.stdout.decode("utf-8", errors="replace").strip()


def verify_repo(path: Path, spec: dict, critical_hashes: dict[str, str] | None = None) -> dict:
    path = path.expanduser().resolve()
    if not (path / ".git").exists():
        raise StrategyT1Error(f"repository is missing or not a Git checkout: {path}")
    origin = git(path, "remote", "get-url", "origin")
    head = git(path, "rev-parse", "HEAD")
    if origin != spec["origin"]:
        raise StrategyT1Error(f"origin mismatch for {path}: {origin}")
    if head != spec["expected_sha"]:
        raise StrategyT1Error(f"SHA mismatch for {path}: {head}")
    if git(path, "status", "--porcelain=v1", "--untracked-files=all"):
        raise StrategyT1Error(f"locked repository is not clean: {path}")
    files: dict[str, str] = {}
    for relative in spec["required_files"]:
        candidate = path / relative
        if not candidate.is_file():
            raise StrategyT1Error(f"required locked file is missing: {candidate}")
        digest = sha256_file(candidate)
        files[relative] = digest
        if critical_hashes is not None and critical_hashes.get(relative) != digest:
            raise StrategyT1Error(f"critical file hash mismatch: {candidate}")
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


def run_doctor(repo: Path) -> dict:
    script = repo / "scripts" / "doctor.py"
    completed = run((os.sys.executable, str(script), "--strategy-c", "--json"), repo, timeout=180)
    try:
        report = json.loads(completed.stdout.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise StrategyT1Error(f"doctor did not return valid JSON: {script}") from exc
    if completed.returncode or not report.get("ok"):
        raise StrategyT1Error(f"doctor failed: {script}")
    return {
        "exit_code": completed.returncode,
        "report_sha256": sha256_bytes(completed.stdout),
    }


def utc_now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
