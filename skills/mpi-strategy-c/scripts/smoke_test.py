#!/usr/bin/env python3
"""Run a live, non-private release smoke test against the locked toolkit."""

from __future__ import annotations

import os
import shutil
import tempfile
import time
import uuid
from pathlib import Path

from runtime import StrategyCError, atomic_json, atomic_text, run, sha256_bytes, sha256_file


def deepseek_key() -> str:
    try:
        import keyring
    except ImportError as exc:
        raise StrategyCError("Python keyring is required for live smoke testing") from exc
    value = keyring.get_password("mpi-strategy-c-deepseek", "default")
    if not value:
        raise StrategyCError("DeepSeek credential is missing for live smoke testing")
    return value


def execute(records: list[dict], toolkit: Path, project: Path, script: str, arguments: list[str], deepseek: bool = False) -> None:
    path = toolkit / "scripts" / script
    command = [os.sys.executable, str(path), *arguments]
    environment = {"DEEPSEEK_API_KEY": deepseek_key()} if deepseek else None
    started = time.time()
    try:
        completed = run(command, project, env=environment)
    finally:
        if environment is not None:
            environment.pop("DEEPSEEK_API_KEY", None)
    finished = time.time()
    record = {
        "receipt_id": str(uuid.uuid4()),
        "script": script,
        "script_absolute_path": str(path.resolve()),
        "script_sha256": sha256_file(path),
        "exit_code": completed.returncode,
        "duration_seconds": round(finished - started, 6),
        "stdout_sha256": sha256_bytes(completed.stdout),
        "stderr_sha256": sha256_bytes(completed.stderr),
    }
    records.append(record)
    if completed.returncode:
        raise StrategyCError(f"public fixture smoke stage failed: {script}")


def copy_files(source: Path, destination: Path, names: tuple[str, ...]) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    for name in names:
        shutil.copy2(source / name, destination / name)


def run_smoke_test(root: Path, toolkit: Path) -> dict:
    fixture = toolkit / "examples" / "minimal-article"
    if not fixture.is_dir():
        raise StrategyCError("toolkit public smoke fixture is missing")
    records: list[dict] = []
    with tempfile.TemporaryDirectory(prefix="mpi-strategy-c-smoke-") as directory:
        base = Path(directory)

        mechanical = base / "mechanical"
        copy_files(
            fixture,
            mechanical,
            (
                "source.dj", "target.dj", "translation-project.yaml", "term-map.yaml",
                "source-analysis.json", "review-findings.jsonl", "semantic-review.json",
            ),
        )
        execute(records, toolkit, mechanical, "gen-bilingual.py", [str(mechanical / "source.dj"), str(mechanical / "target.dj"), "--output", str(mechanical / "bilingual.dj")])
        execute(records, toolkit, mechanical, "check-translation.py", [str(mechanical), "--strict", "--json", "--output", str(mechanical / "qa-report.json")])
        shutil.copy2(mechanical / "target.dj", mechanical / "sol-draft.dj")
        execute(records, toolkit, mechanical, "freeze-target.py", [str(mechanical / "source.dj"), str(mechanical / "sol-draft.dj"), "--output", str(mechanical / "target-frozen.dj")])
        execute(records, toolkit, mechanical, "dj2docx.py", [str(mechanical / "target.dj"), str(mechanical / "target.docx"), "--kind", "target"])
        execute(records, toolkit, mechanical, "check-docx.py", [str(mechanical / "target.dj"), str(mechanical / "target.docx"), "--output", str(mechanical / "target-docx-qa-report.json")])
        execute(records, toolkit, mechanical, "dj2docx.py", [str(mechanical / "bilingual.dj"), str(mechanical / "bilingual.docx"), "--kind", "bilingual"])
        execute(records, toolkit, mechanical, "check-docx.py", [str(mechanical / "bilingual.dj"), str(mechanical / "bilingual.docx"), "--output", str(mechanical / "bilingual-docx-qa-report.json")])
        execute(records, toolkit, mechanical, "check-subtitles.py", [str(mechanical), "--not-applicable", "--output", str(mechanical / "subtitle-qa-report.json")])

        terminology = base / "terminology"
        terminology.mkdir()
        execute(records, toolkit, terminology, "source2dj.py", [str(fixture / "source.dj"), str(terminology / "source.dj")])
        atomic_text(terminology / "term-candidates.json", '{"terms":[{"source":"正念","sense":"佛法修习"}]}\n')
        execute(records, toolkit, terminology, "build-term-map.py", [str(terminology / "source.dj"), str(terminology / "term-candidates.json"), "--output", str(terminology / "term-map.yaml"), "--receipts", str(terminology / "term-search-receipts.jsonl")])

        flash = base / "flash"
        copy_files(fixture, flash, ("source.dj", "translation-project.yaml", "term-map.yaml"))
        execute(records, toolkit, flash, "deepseek-source-analysis.py", [str(flash)], deepseek=True)

        pro = base / "pro"
        copy_files(fixture, pro, ("source.dj", "target.dj", "translation-project.yaml", "term-map.yaml"))
        execute(records, toolkit, pro, "deepseek-review.py", [str(pro), "--reasoning-effort", "max"], deepseek=True)

        evidence = {
            "mechanical_qa_sha256": sha256_file(mechanical / "qa-report.json"),
            "target_docx_qa_sha256": sha256_file(mechanical / "target-docx-qa-report.json"),
            "bilingual_docx_qa_sha256": sha256_file(mechanical / "bilingual-docx-qa-report.json"),
            "subtitle_qa_sha256": sha256_file(mechanical / "subtitle-qa-report.json"),
            "term_search_receipts_sha256": sha256_file(terminology / "term-search-receipts.jsonl"),
            "flash_analysis_sha256": sha256_file(flash / "source-analysis.json"),
            "pro_review_sha256": sha256_file(pro / "semantic-review.json"),
        }
    report = {
        "schema_version": 1,
        "status": "PASS",
        "fixture": "translation-toolkit/examples/minimal-article",
        "contains_private_content": False,
        "live_models": ["deepseek-v4-flash:high", "deepseek-v4-pro:max"],
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "executions": records,
        "evidence": evidence,
    }
    output = root / "smoke-test-report.json"
    atomic_json(output, report)
    report["report_absolute_path"] = str(output.resolve())
    report["report_sha256"] = sha256_file(output)
    return report
