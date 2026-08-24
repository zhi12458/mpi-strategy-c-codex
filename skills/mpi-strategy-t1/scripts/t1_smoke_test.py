#!/usr/bin/env python3
"""Run public-only T1 model and toolkit smoke tests."""

from __future__ import annotations

import os
import shutil
import tempfile
import time
import uuid
from pathlib import Path

from omp_runtime import run_role
from t1_runtime import StrategyT1Error, atomic_json, run, sha256_bytes, sha256_file, utc_now


def execute(records: list[dict], cwd: Path, command: list[str], label: str, timeout: int = 180) -> None:
    started = time.time()
    completed = run(command, cwd, timeout=timeout)
    record = {
        "receipt_id": str(uuid.uuid4()),
        "label": label,
        "executable": command[0],
        "exit_code": completed.returncode,
        "duration_seconds": round(time.time() - started, 6),
        "stdout_sha256": sha256_bytes(completed.stdout),
        "stdout_bytes": len(completed.stdout),
        "stderr_sha256": sha256_bytes(completed.stderr),
        "stderr_bytes": len(completed.stderr),
    }
    records.append(record)
    if completed.returncode:
        raise StrategyT1Error(f"public fixture smoke stage failed: {label}")


def copy_fixture(source: Path, destination: Path, names: tuple[str, ...]) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    for name in names:
        shutil.copy2(source / name, destination / name)


def run_smoke_test(root: Path, toolkit: Path, lock: dict) -> dict:
    fixture = toolkit / "examples" / "minimal-article"
    if not fixture.is_dir():
        raise StrategyT1Error("toolkit public smoke fixture is missing")
    records: list[dict] = []
    model_records: list[dict] = []
    evidence: dict[str, str] = {}
    with tempfile.TemporaryDirectory(prefix="mpi-strategy-t1-smoke-") as directory:
        project = Path(directory) / "public-fixture"
        copy_fixture(
            fixture,
            project,
            (
                "source.dj",
                "target.dj",
                "translation-project.yaml",
                "term-map.yaml",
                "source-analysis.json",
                "review-findings.jsonl",
                "semantic-review.json",
            ),
        )
        scripts = toolkit / "scripts"
        execute(
            records,
            project,
            [
                os.sys.executable,
                str(scripts / "gen-bilingual.py"),
                str(project / "source.dj"),
                str(project / "target.dj"),
                "--output",
                str(project / "bilingual.dj"),
            ],
            "gen-bilingual",
        )
        execute(
            records,
            project,
            [
                os.sys.executable,
                str(scripts / "check-translation.py"),
                str(project),
                "--strict",
                "--json",
                "--output",
                str(project / "qa-report.json"),
            ],
            "check-translation",
        )
        for kind, input_name in (("target", "target.dj"), ("bilingual", "bilingual.dj")):
            docx = project / f"{kind}.docx"
            qa = project / f"{kind}-docx-qa.json"
            execute(
                records,
                project,
                [os.sys.executable, str(scripts / "dj2docx.py"), str(project / input_name), str(docx), "--kind", kind],
                f"dj2docx-{kind}",
            )
            execute(
                records,
                project,
                [os.sys.executable, str(scripts / "check-docx.py"), str(project / input_name), str(docx), "--output", str(qa)],
                f"check-docx-{kind}",
            )
            evidence[f"{kind}_docx_qa_sha256"] = sha256_file(qa)
        evidence["mechanical_qa_sha256"] = sha256_file(project / "qa-report.json")

        for role, marker in lock["smoke_policy"]["markers"].items():
            prompt = f"This is a public MPI T1 installation check. Return exactly: {marker}"
            stdout, receipt = run_role(role, [prompt], cwd=project)
            if marker.encode("utf-8") not in stdout:
                raise StrategyT1Error(f"public OMP smoke marker was not returned: {role}")
            receipt["public_prompt_sha256"] = sha256_bytes(prompt.encode("utf-8"))
            receipt["marker"] = marker
            model_records.append(receipt)

    report = {
        "schema_version": 1,
        "status": "PASS",
        "created_at": utc_now(),
        "fixture": "translation-toolkit/examples/minimal-article",
        "contains_private_content": False,
        "workflow_version": lock["workflow_version"],
        "model_executions": model_records,
        "tool_executions": records,
        "evidence": evidence,
    }
    output = root / "smoke-test-report.json"
    atomic_json(output, report)
    report["report_absolute_path"] = str(output.resolve())
    report["report_sha256"] = sha256_file(output)
    return report
