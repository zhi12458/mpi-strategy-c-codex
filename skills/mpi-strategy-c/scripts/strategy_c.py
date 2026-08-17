#!/usr/bin/env python3
"""Install and execute the audited MPI Strategy C state machine."""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import uuid
from pathlib import Path

from bootstrap import install
from runtime import (
    INSTRUCTION_RECEIPT_NAME,
    MANIFEST_NAME,
    RECEIPTS_NAME,
    StrategyCError,
    append_receipt,
    atomic_json,
    begin_project,
    file_hashes,
    load_json,
    load_lock,
    managed_root,
    read_receipts,
    reject_secret_arguments,
    run,
    sha256_bytes,
    sha256_file,
    validate_instruction_receipt,
    verify_ready,
)


STAGE_SCRIPTS = {
    "source_extraction": {"source2dj.py", "docx2dj.py"},
    "terminology": {"build-term-map.py"},
    "flash_analysis": {"deepseek-source-analysis.py"},
    "target_freeze": {"freeze-target.py"},
    "bilingual_1": {"gen-bilingual.py"},
    "pro_review_1": {"deepseek-review.py"},
    "target_refreeze": {"freeze-target.py"},
    "bilingual_final": {"gen-bilingual.py"},
    "pro_review_2": {"deepseek-review.py"},
    "translation_qa": {"check-translation.py"},
    "target_docx": {"dj2docx.py"},
    "bilingual_docx": {"dj2docx.py"},
    "target_docx_qa": {"check-docx.py"},
    "bilingual_docx_qa": {"check-docx.py"},
    "subtitle_na": {"check-subtitles.py"},
    "subtitle_generation": {"gen-subtitles.py"},
    "subtitle_qa": {"check-subtitles.py"},
}
DOCUMENT_STAGES = {
    "source_extraction", "terminology", "terminology_search", "flash_analysis", "target_freeze",
    "bilingual_1", "pro_review_1", "target_refreeze", "bilingual_final",
    "pro_review_2", "translation_qa", "target_docx", "bilingual_docx",
    "target_docx_qa", "bilingual_docx_qa", "subtitle_na",
}
MEDIA_STAGES = (DOCUMENT_STAGES - {"subtitle_na"}) | {"media_transcription", "subtitle_generation", "subtitle_qa"}
MODEL_STAGES = {"flash_model", "sol_translation", "pro_model_1", "sol_revision", "pro_model_2"}


def safe_receipt_base(stage: str, started: float, command: list[str], cwd: Path) -> dict:
    return {
        "schema_version": 1,
        "receipt_id": str(uuid.uuid4()),
        "workflow_stage": stage,
        "started_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(started)),
        "cwd": str(cwd.resolve()),
        "command": command,
    }


def deepseek_environment() -> dict[str, str]:
    try:
        import keyring
    except ImportError as exc:
        raise StrategyCError("Python keyring is required") from exc
    secret = keyring.get_password("mpi-strategy-c-deepseek", "default")
    if not secret:
        raise StrategyCError("DeepSeek credential is missing from the operating-system vault")
    return {"DEEPSEEK_API_KEY": secret}


def run_audited_tool(project: Path, stage: str, script_name: str, arguments: list[str], inputs: list[Path], outputs: list[Path]) -> dict:
    verify_ready()
    instruction = validate_instruction_receipt(project)
    if stage not in STAGE_SCRIPTS or script_name not in STAGE_SCRIPTS[stage]:
        raise StrategyCError(f"script {script_name} is not allowed for stage {stage}")
    reject_secret_arguments(arguments)
    toolkit_info = instruction["translation_toolkit"]
    toolkit = Path(toolkit_info["absolute_path"])
    script = (toolkit / "scripts" / script_name).resolve()
    expected_hash = toolkit_info["critical_file_sha256"].get(f"scripts/{script_name}")
    if not script.is_file() or not expected_hash or sha256_file(script) != expected_hash:
        raise StrategyCError("locked toolkit script is missing or changed")
    if stage == "flash_analysis" and (project / "target.dj").exists():
        raise StrategyCError("Flash analysis must run before target.dj exists")
    if stage.startswith("pro_review") and any("source-analysis" in value for value in arguments):
        raise StrategyCError("Pro review must not receive Flash source analysis")
    command = [sys.executable, str(script), *arguments]
    started = time.time()
    receipt = safe_receipt_base(stage, started, command, project)
    receipt.update({
        "owner_repository": toolkit_info,
        "script_absolute_path": str(script),
        "script_sha256": expected_hash,
        "arguments": arguments,
        "inputs": file_hashes(inputs),
    })
    environment = deepseek_environment() if script_name in {"deepseek-source-analysis.py", "deepseek-review.py"} else None
    try:
        completed = run(command, project, env=environment)
    finally:
        if environment is not None:
            environment.pop("DEEPSEEK_API_KEY", None)
    finished = time.time()
    receipt.update({
        "finished_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(finished)),
        "duration_seconds": round(finished - started, 6),
        "exit_code": completed.returncode,
        "stdout_sha256": sha256_bytes(completed.stdout),
        "stderr_sha256": sha256_bytes(completed.stderr),
        "stdout_summary": {"bytes": len(completed.stdout), "lines": completed.stdout.count(b"\n")},
        "stderr_summary": {"bytes": len(completed.stderr), "lines": completed.stderr.count(b"\n")},
        "outputs": file_hashes(outputs, require=False),
    })
    append_receipt(project, receipt)
    if completed.returncode:
        raise StrategyCError(f"toolkit stage {stage} failed with exit code {completed.returncode}")
    if len(receipt["outputs"]) != len(outputs):
        raise StrategyCError(f"toolkit stage {stage} did not produce every declared output")
    for output in outputs:
        if output.stat().st_mtime + 1 < started:
            raise StrategyCError(f"toolkit stage {stage} produced a stale output")
    if stage == "terminology":
        receipt_files = [path for path in outputs if path.name == "term-search-receipts.jsonl"]
        if len(receipt_files) != 1:
            raise StrategyCError("terminology stage must declare term-search-receipts.jsonl as an output")
        rows = []
        for line in receipt_files[0].read_text(encoding="utf-8").splitlines():
            if line.strip():
                try:
                    rows.append(json.loads(line))
                except json.JSONDecodeError as exc:
                    raise StrategyCError("toolkit term-search receipt is invalid") from exc
        if not rows:
            raise StrategyCError("MPI terminology search was not actually called")
        search_script = toolkit / "terms-database" / "search.py"
        search_hash = toolkit_info["critical_file_sha256"].get("terms-database/search.py")
        database = toolkit / "terms-database" / "termlib.sqlite"
        for row in rows:
            if row.get("search_script") != str(search_script.resolve()) or row.get("search_script_sha256") != search_hash or row.get("exit_code") != 0:
                raise StrategyCError("MPI term-search child receipt does not match the locked toolkit")
            child_arguments = row.get("arguments")
            if not isinstance(child_arguments, list) or len(child_arguments) < 3:
                raise StrategyCError("MPI term-search child receipt omitted its full arguments")
            child = {
                "schema_version": 1,
                "receipt_id": str(uuid.uuid4()),
                "parent_receipt_id": receipt["receipt_id"],
                "workflow_stage": "terminology_search",
                "started_at": row.get("started_at"),
                "finished_at": row.get("finished_at"),
                "cwd": str(project),
                "command": [sys.executable, str(search_script), *child_arguments],
                "owner_repository": toolkit_info,
                "script_absolute_path": str(search_script),
                "script_sha256": search_hash,
                "arguments": child_arguments,
                "inputs": file_hashes([database]),
                "outputs": [],
                "exit_code": 0,
                "stdout_sha256": row.get("stdout_sha256"),
                "stdout_summary": {"result_count": row.get("result_count")},
                "stderr_sha256": sha256_bytes(b""),
                "stderr_summary": {"bytes": 0, "lines": 0},
            }
            append_receipt(project, child)
    return receipt


def record_model(project: Path, stage: str, provider: str, model: str, effort: str, prompt_sha256: str, inputs: list[Path], outputs: list[Path], metadata: Path | None) -> dict:
    verify_ready()
    validate_instruction_receipt(project)
    if stage not in MODEL_STAGES or len(prompt_sha256) != 64:
        raise StrategyCError("invalid model stage or prompt SHA-256")
    lock = load_lock()["models"]
    role = "source_analysis" if stage == "flash_model" else "review" if stage.startswith("pro_model") else "translation"
    expected = lock[role]
    if (provider, model, effort) != (expected["provider"], expected["model"], expected["reasoning_effort"]):
        raise StrategyCError("model identity or reasoning effort does not match the release lock")
    raw_metadata = load_json(metadata) if metadata else {}
    allowed_metadata = {
        key: raw_metadata.get(key)
        for key in (
            "model_fingerprint", "input_tokens", "output_tokens", "reasoning_tokens",
            "cost", "currency", "retries", "duration_seconds", "request_id",
        )
    }
    receipt = {
        "schema_version": 1,
        "receipt_id": str(uuid.uuid4()),
        "workflow_stage": stage,
        "kind": "model",
        "recorded_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "provider": provider,
        "model": model,
        "reasoning_effort": effort,
        "prompt_sha256": prompt_sha256,
        "inputs": file_hashes(inputs),
        "outputs": file_hashes(outputs),
        "model_metadata": allowed_metadata,
    }
    append_receipt(project, receipt)
    return receipt


def run_media(project: Path, media: Path) -> dict:
    instruction = validate_instruction_receipt(project)
    ready, _, _ = verify_ready()
    script = Path(__file__).with_name("transcribe_media.py").resolve()
    command = [sys.executable, str(script), str(media.resolve()), "--project", str(project.resolve())]
    started = time.time()
    receipt = safe_receipt_base("media_transcription", started, command, project)
    receipt.update({
        "owner_repository": {"absolute_path": str(Path(__file__).resolve().parents[3]), "skill_version": ready["skill_version"]},
        "script_absolute_path": str(script),
        "script_sha256": sha256_file(script),
        "inputs": file_hashes([media, Path(ready["whisper"]["model_absolute_path"]), Path(ready["whisper"]["executable_absolute_path"])]),
    })
    completed = run(command, project)
    finished = time.time()
    outputs = [project / "whisper-raw.txt", project / "source-map.json", project / "transcription-ambiguities.json"]
    receipt.update({
        "finished_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(finished)),
        "duration_seconds": round(finished - started, 6),
        "exit_code": completed.returncode,
        "stdout_sha256": sha256_bytes(completed.stdout),
        "stderr_sha256": sha256_bytes(completed.stderr),
        "stdout_summary": {"bytes": len(completed.stdout), "lines": completed.stdout.count(b"\n")},
        "stderr_summary": {"bytes": len(completed.stderr), "lines": completed.stderr.count(b"\n")},
        "outputs": file_hashes(outputs, require=False),
        "instruction_receipt_id": instruction["receipt_id"],
    })
    append_receipt(project, receipt)
    if completed.returncode or len(receipt["outputs"]) != 3:
        raise StrategyCError("media transcription failed")
    return receipt


def forbidden_qa_status(value: object) -> bool:
    if isinstance(value, dict):
        for key, item in value.items():
            if key.casefold() in {"status", "result"} and isinstance(item, str) and item.upper() in {"FAIL", "SKIP"}:
                return True
            if forbidden_qa_status(item):
                return True
    elif isinstance(value, list):
        return any(forbidden_qa_status(item) for item in value)
    return False


def finalize(project: Path, input_type: str) -> dict:
    verify_ready()
    instruction = validate_instruction_receipt(project)
    receipts = read_receipts(project)
    successful = {item.get("workflow_stage") for item in receipts if item.get("exit_code", 0) == 0}
    required = (DOCUMENT_STAGES if input_type == "document" else MEDIA_STAGES) | MODEL_STAGES
    missing = sorted(required - successful)
    current_artifacts: dict[str, dict] = {}
    stale = []
    for item in receipts:
        for output in item.get("outputs", []):
            current_artifacts[output["absolute_path"]] = output
    for path_text, output in current_artifacts.items():
        path = Path(path_text)
        if not path.is_file() or sha256_file(path) != output["sha256"]:
            stale.append(str(path))
    qa_paths = [
        project / "qa-report.json",
        project / "target-docx-qa-report.json",
        project / "bilingual-docx-qa-report.json",
        project / "subtitle-qa-report.json",
    ]
    qa_failures = [str(path) for path in qa_paths if not path.is_file() or forbidden_qa_status(load_json(path))]
    second_review = project / "semantic-review.json"
    blockers = False
    if second_review.is_file():
        certificate = load_json(second_review)
        blockers = certificate.get("status") == "blocking" or int(certificate.get("blocking_findings", 0)) > 0
    pipeline_complete = not missing and not stale and not qa_failures and not blockers
    status = "needs_human" if blockers else "ai_draft" if pipeline_complete else "blocked"
    manifest = {
        "schema_version": 1,
        "pipeline_complete": pipeline_complete,
        "status": status,
        "input_type": input_type,
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "mpi_translations": instruction["mpi_translations"],
        "translation_toolkit": instruction["translation_toolkit"],
        "instruction_receipt": load_json(project / INSTRUCTION_RECEIPT_NAME),
        "tool_execution_receipts_path": str((project / RECEIPTS_NAME).resolve()),
        "receipts_sha256": sha256_file(project / RECEIPTS_NAME),
        "receipts": receipts,
        "artifacts": list(current_artifacts.values()),
        "missing_stages": missing,
        "stale_or_missing_artifacts": sorted(set(stale)),
        "qa_failures": qa_failures,
        "remaining_review_blockers": blockers,
        "transcription_ambiguities": load_json(project / "transcription-ambiguities.json").get("items", []) if (project / "transcription-ambiguities.json").is_file() else [],
        "human_approval": None,
    }
    atomic_json(project / MANIFEST_NAME, manifest)
    if not pipeline_complete:
        raise StrategyCError("pipeline is not complete; inspect MANIFEST.json")
    return manifest


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser()
    sub = root.add_subparsers(dest="command", required=True)
    install_parser = sub.add_parser("install")
    install_parser.add_argument("--model", type=Path, required=True)
    install_parser.add_argument("--no-install-dependencies", action="store_true")
    install_parser.add_argument("--development-candidate", action="store_true")
    install_parser.add_argument("--candidate-mpi", type=Path)
    install_parser.add_argument("--candidate-toolkit", type=Path)
    install_parser.add_argument("--skip-credential-for-smoke", action="store_true")
    repair = sub.add_parser("repair")
    repair.add_argument("--model", type=Path)
    repair.add_argument("--no-install-dependencies", action="store_true")
    sub.add_parser("doctor")
    begin = sub.add_parser("begin")
    begin.add_argument("--project", type=Path, required=True)
    begin.add_argument("--input-type", choices=("document", "media"), required=True)
    tool = sub.add_parser("run-tool")
    tool.add_argument("--project", type=Path, required=True)
    tool.add_argument("--stage", required=True)
    tool.add_argument("--script", required=True)
    tool.add_argument("--input", type=Path, action="append", default=[])
    tool.add_argument("--output", type=Path, action="append", default=[])
    tool.add_argument("arguments", nargs=argparse.REMAINDER)
    media = sub.add_parser("run-media")
    media.add_argument("--project", type=Path, required=True)
    media.add_argument("--media", type=Path, required=True)
    model = sub.add_parser("record-model")
    model.add_argument("--project", type=Path, required=True)
    model.add_argument("--stage", required=True)
    model.add_argument("--provider", required=True)
    model.add_argument("--model", required=True)
    model.add_argument("--effort", required=True)
    model.add_argument("--prompt-sha256", required=True)
    model.add_argument("--input", type=Path, action="append", default=[])
    model.add_argument("--output", type=Path, action="append", default=[])
    model.add_argument("--metadata", type=Path)
    final = sub.add_parser("finalize")
    final.add_argument("--project", type=Path, required=True)
    final.add_argument("--input-type", choices=("document", "media"), required=True)
    return root


def main() -> int:
    args = parser().parse_args()
    try:
        if args.command == "install":
            value = install(args.model.resolve(), not args.no_install_dependencies, args.development_candidate, args.candidate_mpi, args.candidate_toolkit, args.skip_credential_for_smoke)
        elif args.command == "repair":
            model_path = args.model
            if model_path is None:
                existing = load_json(managed_root() / "READY.json")
                model_path = Path(existing.get("whisper", {}).get("model_absolute_path", ""))
            if not model_path.is_file():
                raise StrategyCError("repair requires the locked Whisper model path")
            value = install(model_path.resolve(), not args.no_install_dependencies)
        elif args.command == "doctor":
            value = {"ready": verify_ready()[0]}
        elif args.command == "begin":
            value = begin_project(args.project, args.input_type)
        elif args.command == "run-tool":
            arguments = args.arguments[1:] if args.arguments[:1] == ["--"] else args.arguments
            value = run_audited_tool(args.project.resolve(), args.stage, args.script, arguments, args.input, args.output)
        elif args.command == "run-media":
            value = run_media(args.project.resolve(), args.media.resolve())
        elif args.command == "record-model":
            value = record_model(args.project.resolve(), args.stage, args.provider, args.model, args.effort, args.prompt_sha256, args.input, args.output, args.metadata)
        else:
            value = finalize(args.project.resolve(), args.input_type)
        print(json.dumps(value, ensure_ascii=False, indent=2))
        return 0
    except StrategyCError as exc:
        print(f"BLOCKED: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
