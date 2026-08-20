from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).parents[1]
SKILL = ROOT / "skills" / "mpi-strategy-m"
LOCK_PATH = SKILL / "dependency-lock.json"
LOCK = json.loads(LOCK_PATH.read_text(encoding="utf-8"))
sys.path.insert(0, str(SKILL / "scripts"))

import fault_injection  # noqa: E402
import bootstrap  # noqa: E402
import runtime  # noqa: E402


def run(*arguments: str, cwd: Path, capture: bool = True) -> str:
    result = subprocess.run(arguments, cwd=cwd, text=True, capture_output=capture, check=False)
    if result.returncode:
        print(result.stdout, file=sys.stderr)
        print(result.stderr, file=sys.stderr)
        raise SystemExit(f"failed: {' '.join(arguments)}")
    return result.stdout.strip()


def main() -> None:
    mpi_spec = LOCK["mpi_translations"]
    toolkit_spec = LOCK["translation_toolkit"]
    with tempfile.TemporaryDirectory(prefix="mpi-public-lock-") as temporary:
        installed_root = Path(temporary) / "managed"
        runtime.LOCK_PATH = LOCK_PATH
        mpi, toolkit = bootstrap.prepare_repositories(installed_root, LOCK, None, None)

        observed = {
            "mpi_origin": run("git", "remote", "get-url", "origin", cwd=mpi),
            "mpi_sha": run("git", "rev-parse", "HEAD", cwd=mpi),
            "toolkit_origin": run("git", "remote", "get-url", "origin", cwd=toolkit),
            "toolkit_sha": run("git", "rev-parse", "HEAD", cwd=toolkit),
            "mpi_status": run("git", "status", "--porcelain=v1", "--untracked-files=all", cwd=mpi),
            "toolkit_status": run("git", "status", "--porcelain=v1", "--untracked-files=all", cwd=toolkit),
        }
        expected = {
            "mpi_origin": mpi_spec["origin"],
            "mpi_sha": mpi_spec["expected_sha"],
            "toolkit_origin": toolkit_spec["origin"],
            "toolkit_sha": toolkit_spec["expected_sha"],
            "mpi_status": "",
            "toolkit_status": "",
        }
        if observed != expected:
            raise SystemExit(json.dumps({"expected": expected, "observed": observed}, indent=2))

        for repository, doctor in (
            (mpi, mpi / "scripts" / "doctor.py"),
            (toolkit, toolkit / "scripts" / "doctor.py"),
        ):
            report = json.loads(run(sys.executable, str(doctor), "--strategy-c", "--json", cwd=repository))
            if report.get("ok") is not True:
                raise SystemExit(json.dumps(report, indent=2))

        fault_injection.temporary_ready(installed_root, LOCK, mpi, toolkit)
        fault_report = fault_injection.run_fault_tests(installed_root)
        if fault_report.get("status") != "PASS" or not fault_report.get("restored_installation_verified"):
            raise SystemExit(json.dumps(fault_report, indent=2))

        print(json.dumps({
            "status": "PASS",
            **observed,
            "fault_injection_cases": [case["case"] for case in fault_report["cases"]],
            "restored_installation_verified": True,
        }, indent=2))


if __name__ == "__main__":
    main()
