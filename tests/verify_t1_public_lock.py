from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).parents[1]
SKILL = ROOT / "skills" / "mpi-strategy-t1"
sys.path.insert(0, str(SKILL / "scripts"))

import t1_bootstrap  # noqa: E402
import t1_fault_injection  # noqa: E402
import t1_runtime  # noqa: E402
import semantic_bridge  # noqa: E402
import pretranslation  # noqa: E402


def main() -> None:
    lock = t1_runtime.load_lock()
    with tempfile.TemporaryDirectory(prefix="mpi-t1-public-lock-") as temporary:
        managed = Path(temporary) / "managed"
        mpi, toolkit = t1_bootstrap.prepare_repositories(managed, lock)
        mpi_info, toolkit_info = t1_bootstrap.repository_evidence(mpi, toolkit, lock)
        try:
            semantic_contracts = semantic_bridge.run_contract_tests(managed)
        except t1_runtime.StrategyT1Error as exc:
            # T1.1.2 is an optional pilot capability. Its missing optional
            # dependency or failed contract is reported, but does not relabel
            # the independently locked T1.0.1 production baseline as failed.
            semantic_contracts = {"status": "BLOCKED", "error": str(exc)}
        pretranslation_contracts = pretranslation.run_contract_tests(managed)
        fault = t1_fault_injection.run_fault_tests(managed)
        if fault.get("status") != "PASS" or fault.get("restored_installation_verified") is not True:
            raise SystemExit(json.dumps(fault, indent=2))
        print(
            json.dumps(
                {
                    "status": "PASS",
                    "workflow_version": lock["workflow_version"],
                    "installer_version": lock["installer_version"],
                    "mpi_origin": mpi_info["origin"],
                    "mpi_sha": mpi_info["git_sha"],
                    "toolkit_origin": toolkit_info["origin"],
                    "toolkit_sha": toolkit_info["git_sha"],
                    "mpi_doctor": mpi_info["doctor"],
                    "toolkit_doctor": toolkit_info["doctor"],
                    "semantic_restructuring_pilot_status": semantic_contracts[
                        "status"
                    ],
                    "semantic_restructuring_pilot_error": semantic_contracts.get(
                        "error"
                    ),
                    "semantic_restructuring_contract_cases": [
                        item["case"] for item in semantic_contracts.get("cases", [])
                    ],
                    "pretranslation_track_status": pretranslation_contracts[
                        "status"
                    ],
                    "pretranslation_contract_cases": [
                        item["case"]
                        for item in pretranslation_contracts.get("cases", [])
                    ],
                    "fault_injection_cases": [item["case"] for item in fault["cases"]],
                    "restored_installation_verified": True,
                },
                indent=2,
            )
        )


if __name__ == "__main__":
    main()
