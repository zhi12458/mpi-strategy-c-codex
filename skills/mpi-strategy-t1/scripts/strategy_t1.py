#!/usr/bin/env python3
"""Install, verify, and run the audited MPI T1 runtime."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

from artifact_reuse import cache_validated_artifact, restore_validated_artifact
from t1_bootstrap import install, verify_ready
from omp_runtime import (
    T1_MODEL_STAGES,
    run_ai_pretranslation,
    run_ai_pretranslation_review,
    run_file,
    run_semantic_restructuring,
    run_translation_with_pretranslation,
    run_translation_with_restructuring,
)
from pretranslation import (
    hydrate_proposal as hydrate_pretranslation_proposal,
    resolve_pretranslation,
    validate_accepted_pretranslation,
    validate_ai_review,
    validate_human_approval,
    validate_pretranslation,
)
from semantic_bridge import validate_legacy_project, validate_project
from t1_runtime import (
    ACCOUNT_CONFIRMATION_NAME,
    StrategyT1Error,
    atomic_json,
    executable,
    load_lock,
    managed_root,
    run,
    sha256_bytes,
    utc_now,
)
from usage_metrics import summarize_receipts


def login_openai() -> dict:
    lock = load_lock()
    omp = executable(lock["omp"]["executable"])
    if not omp:
        raise StrategyT1Error("OMP is missing")
    completed = subprocess.run((omp, "auth-broker", "login", "openai-codex"), check=False)
    if completed.returncode:
        raise StrategyT1Error("OMP OpenAI OAuth login did not complete")
    return {
        "status": "oauth_callback_completed",
        "next": "run confirm-personal-workspace and inspect the account before installation",
    }


def confirm_personal_workspace() -> dict:
    lock = load_lock()
    omp = executable(lock["omp"]["executable"])
    if not omp:
        raise StrategyT1Error("OMP is missing")
    completed = run(
        (omp, "usage", "--provider", "openai-codex", "--redact", "--json"),
        Path.cwd(),
        timeout=90,
    )
    if completed.returncode:
        raise StrategyT1Error("OMP usage could not verify an OpenAI Codex account")
    try:
        payload = json.loads(completed.stdout.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise StrategyT1Error("OMP usage did not return valid JSON") from exc
    reports = [
        item for item in payload.get("reports", [])
        if isinstance(item, dict)
        and item.get("provider") == "openai-codex"
        and item.get("metadata", {}).get("allowed") is True
    ]
    if not reports:
        raise StrategyT1Error("no enabled OpenAI Codex account was found")
    summary = [
        {
            "plan_type": item.get("metadata", {}).get("planType"),
            "workspace_label": item.get("metadata", {}).get("orgName"),
            "allowed": True,
        }
        for item in reports
    ]
    print(json.dumps({"enabled_accounts": summary}, ensure_ascii=False, indent=2))
    if not sys.stdin.isatty():
        raise StrategyT1Error("Personal workspace confirmation requires an interactive terminal")
    answer = input("After verifying that the selected workspace is Personal, type PERSONAL: ").strip()
    if answer != "PERSONAL":
        raise StrategyT1Error("Personal workspace was not confirmed")
    confirmation = {
        "schema_version": 1,
        "confirmed": True,
        "provider": "openai-codex",
        "confirmed_at": utc_now(),
        "usage_response_sha256": sha256_bytes(completed.stdout),
        "enabled_account_count": len(reports),
        "email_recorded": False,
        "account_id_recorded": False,
        "token_recorded": False,
    }
    root = managed_root()
    root.mkdir(parents=True, exist_ok=True)
    atomic_json(root / ACCOUNT_CONFIRMATION_NAME, confirmation)
    return confirmation


def parser() -> argparse.ArgumentParser:
    value = argparse.ArgumentParser(description=__doc__)
    commands = value.add_subparsers(dest="command", required=True)
    for name in ("install", "repair"):
        command = commands.add_parser(name)
        command.add_argument("--install-dependencies", action="store_true")
        command.add_argument("--confirm-public-smoke", action="store_true")
    commands.add_parser("login-openai")
    commands.add_parser("confirm-personal-workspace")
    commands.add_parser("doctor")
    model = commands.add_parser("run-model")
    model.add_argument(
        "--role",
        required=True,
        choices=("source_analysis", "translation_and_self_review", "bilingual_review"),
    )
    model.add_argument("--prompt-file", type=Path, required=True)
    model.add_argument("--output", type=Path, required=True)
    model.add_argument("--cwd", type=Path, default=Path.cwd())
    model.add_argument("--timeout", type=int, default=1800)
    model.add_argument(
        "--bind-input",
        type=Path,
        action="append",
        default=[],
        help="repeat for each frozen source artifact represented in the prompt",
    )
    model.add_argument(
        "--workflow-stage",
        choices=T1_MODEL_STAGES,
        help="auditable existing T1 stage label; does not change role or prompt",
    )
    semantic_run = commands.add_parser("run-semantic-restructuring")
    semantic_run.add_argument("--project", type=Path, required=True)
    semantic_run.add_argument("--accepted-decisions", type=Path)
    semantic_run.add_argument("--output", type=Path)
    semantic_run.add_argument("--timeout", type=int, default=1800)
    translation_run = commands.add_parser("run-translation-with-restructuring")
    translation_run.add_argument("--project", type=Path, required=True)
    translation_run.add_argument("--restructuring", type=Path)
    translation_run.add_argument("--accepted-decisions", type=Path)
    translation_run.add_argument("--output", type=Path)
    translation_run.add_argument("--timeout", type=int, default=1800)
    human = commands.add_parser("hydrate-human-pretranslation")
    human.add_argument("--project", type=Path, required=True)
    human.add_argument("--proposal", type=Path, required=True)
    human.add_argument("--generator-name", required=True)
    human.add_argument("--output", type=Path)
    ai = commands.add_parser("run-ai-pretranslation")
    ai.add_argument("--project", type=Path, required=True)
    ai.add_argument("--output", type=Path)
    ai.add_argument("--timeout", type=int, default=1800)
    ai_review = commands.add_parser("run-ai-pretranslation-review")
    ai_review.add_argument("--project", type=Path, required=True)
    ai_review.add_argument("--pretranslation", type=Path)
    ai_review.add_argument("--output", type=Path)
    ai_review.add_argument("--timeout", type=int, default=1800)
    resolve = commands.add_parser("resolve-pretranslation")
    resolve.add_argument("--project", type=Path, required=True)
    resolve.add_argument("--pretranslation", type=Path, required=True)
    resolve.add_argument("--decision-evidence", type=Path, required=True)
    resolve.add_argument("--output", type=Path, required=True)
    validate_pre = commands.add_parser("validate-pretranslation")
    validate_pre.add_argument("--project", type=Path, required=True)
    validate_pre.add_argument("--artifact", type=Path)
    validate_pre.add_argument("--mode", choices=("human_quality", "ai_scale"))
    validate_accepted = commands.add_parser("validate-accepted-pretranslation")
    validate_accepted.add_argument("--project", type=Path, required=True)
    validate_accepted.add_argument("--artifact", type=Path, required=True)
    pretranslation_run = commands.add_parser("run-translation-with-pretranslation")
    pretranslation_run.add_argument("--project", type=Path, required=True)
    pretranslation_run.add_argument("--accepted-pretranslation", type=Path)
    pretranslation_run.add_argument("--pretranslation", type=Path)
    pretranslation_run.add_argument("--decision-evidence", type=Path)
    pretranslation_run.add_argument("--accepted-decisions", type=Path)
    pretranslation_run.add_argument("--output", type=Path)
    pretranslation_run.add_argument("--timeout", type=int, default=1800)
    usage = commands.add_parser("summarize-usage")
    usage.add_argument("--receipt", type=Path, action="append", required=True)
    cache = commands.add_parser("cache-validated-artifact")
    cache.add_argument("--artifact", type=Path, required=True)
    cache.add_argument("--receipt", type=Path, required=True)
    cache.add_argument("--validation", type=Path, required=True)
    cache.add_argument("--cache-root", type=Path, required=True)
    restore = commands.add_parser("restore-cached-artifact")
    restore.add_argument("--cache-root", type=Path, required=True)
    restore.add_argument("--cache-key", required=True)
    restore.add_argument("--output", type=Path, required=True)
    semantic = commands.add_parser("validate-semantic-restructuring")
    semantic.add_argument("--project", type=Path, required=True)
    semantic.add_argument("--accepted-decisions", type=Path)
    for name in ("validate-semantic-artifacts", "validate-legacy-semantic-artifacts"):
        legacy = commands.add_parser(name)
        legacy.add_argument("--project", type=Path, required=True)
        legacy.add_argument(
            "--stage",
            choices=(
                "risk",
                "bridge",
                "review",
                "decisions",
                "coverage",
                "regression",
                "all",
            ),
            default="all",
        )
    return value


def main() -> int:
    args = parser().parse_args()
    try:
        if args.command in {"install", "repair"}:
            result = install(
                install_missing=args.install_dependencies,
                confirm_public_smoke=args.confirm_public_smoke,
            )
        elif args.command == "login-openai":
            result = login_openai()
        elif args.command == "confirm-personal-workspace":
            result = confirm_personal_workspace()
        elif args.command == "doctor":
            result = verify_ready()
        elif args.command == "run-model":
            verify_ready()
            result = run_file(
                args.role,
                args.prompt_file,
                args.output,
                cwd=args.cwd.expanduser().resolve(),
                timeout=args.timeout,
                bound_inputs=args.bind_input,
                workflow_stage=args.workflow_stage,
            )
        elif args.command == "run-semantic-restructuring":
            verify_ready(require_semantic_restructuring=True)
            result = run_semantic_restructuring(
                args.project,
                accepted_decisions=args.accepted_decisions,
                output=args.output,
                timeout=args.timeout,
            )
        elif args.command == "run-translation-with-restructuring":
            verify_ready(require_semantic_restructuring=True)
            result = run_translation_with_restructuring(
                args.project,
                restructuring=args.restructuring,
                accepted_decisions=args.accepted_decisions,
                output=args.output,
                timeout=args.timeout,
            )
        elif args.command == "hydrate-human-pretranslation":
            project = args.project.expanduser().resolve()
            proposal_path = args.proposal.expanduser().resolve()
            output = (args.output or (project / "pretranslation.json")).expanduser().resolve()
            if output.exists():
                raise StrategyT1Error(f"refusing to overwrite existing T1 artifact: {output}")
            try:
                proposal = json.loads(proposal_path.read_text(encoding="utf-8"))
            except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
                raise StrategyT1Error(f"invalid pretranslation proposal: {proposal_path}") from exc
            if not isinstance(proposal, dict):
                raise StrategyT1Error("pretranslation proposal root must be an object")
            artifact = hydrate_pretranslation_proposal(
                project,
                proposal,
                mode="human_quality",
                provenance={
                    "kind": "human",
                    "name": args.generator_name,
                    "provider": None,
                    "model": None,
                    "reasoning_effort": None,
                    "role": None,
                },
            )
            atomic_json(output, artifact)
            result = validate_pretranslation(
                project, artifact_path=output, expected_mode="human_quality"
            )
        elif args.command == "run-ai-pretranslation":
            verify_ready(require_pretranslation=True)
            result = run_ai_pretranslation(
                args.project, output=args.output, timeout=args.timeout
            )
        elif args.command == "run-ai-pretranslation-review":
            verify_ready(require_pretranslation=True)
            result = run_ai_pretranslation_review(
                args.project,
                pretranslation=args.pretranslation,
                output=args.output,
                timeout=args.timeout,
            )
        elif args.command == "resolve-pretranslation":
            result = resolve_pretranslation(
                args.project,
                args.pretranslation,
                args.decision_evidence,
                output=args.output,
            )
        elif args.command == "validate-pretranslation":
            result = validate_pretranslation(
                args.project,
                artifact_path=args.artifact,
                expected_mode=args.mode,
            )
        elif args.command == "validate-accepted-pretranslation":
            result = validate_accepted_pretranslation(args.project, args.artifact)
        elif args.command == "run-translation-with-pretranslation":
            verify_ready(require_pretranslation=True)
            result = run_translation_with_pretranslation(
                args.project,
                accepted_pretranslation=args.accepted_pretranslation,
                pretranslation=args.pretranslation,
                decision_evidence=args.decision_evidence,
                accepted_decisions=args.accepted_decisions,
                output=args.output,
                timeout=args.timeout,
            )
        elif args.command == "summarize-usage":
            result = summarize_receipts(args.receipt)
        elif args.command == "cache-validated-artifact":
            result = cache_validated_artifact(
                args.artifact, args.receipt, args.validation, args.cache_root
            )
        elif args.command == "restore-cached-artifact":
            result = restore_validated_artifact(
                args.cache_root, args.cache_key, args.output
            )
        elif args.command == "validate-semantic-restructuring":
            result = validate_project(
                args.project, accepted_decisions_path=args.accepted_decisions
            )
        elif args.command in {
            "validate-semantic-artifacts",
            "validate-legacy-semantic-artifacts",
        }:
            result = validate_legacy_project(args.project, args.stage)
        else:
            raise StrategyT1Error("unknown command")
    except StrategyT1Error as exc:
        print(json.dumps({"ok": False, "status": "BLOCKED", "error": str(exc)}, ensure_ascii=False, indent=2))
        return 2
    print(json.dumps({"ok": True, "result": result}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
