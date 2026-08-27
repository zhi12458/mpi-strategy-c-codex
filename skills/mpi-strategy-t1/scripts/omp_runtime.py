#!/usr/bin/env python3
"""Run locked T1 model roles through OMP without exposing provider secrets."""

from __future__ import annotations

import json
import os
import time
import uuid
from pathlib import Path

from pretranslation import (
    hydrate_ai_review,
    hydrate_compact_ai_proposal,
    validate_accepted_pretranslation,
    validate_ai_review,
    validate_human_approval,
    validate_pretranslation,
)
from semantic_bridge import hydrate_proposal as hydrate_semantic_proposal
from semantic_bridge import prompt_contract as semantic_prompt_contract
from semantic_bridge import validate_project as validate_semantic_project
from t1_runtime import (
    StrategyT1Error,
    load_lock,
    run,
    sha256_bytes,
    sha256_file,
)


SEMANTIC_RESTRUCTURING_PROMPT = """\
You are performing the semantic-restructuring substep inside the existing T1
translation_and_self_review role. Read the first four @file inputs in this
order: source.dj, translation-project.yaml, source-analysis.json, and
term-map.yaml. If an accepted-decisions @file is explicitly present after
those inputs, apply only its source-bound accepted decisions. It may correct an
automated analysis or terminology aid, but it can never override source.dj. If
such a correction removes the frozen analysis support for a Chinese lexical
addition, defer that addition instead of fabricating a binding. The last @file is a deterministic
compact proposal schema and rule envelope generated from the frozen project
inputs; follow it exactly, including its analysis_schema_mode and, for
legacy_prose, the exact legacy_evidence_fields_by_kind allowlist. A field
allowed for one evidence kind is not automatically allowed for another.

The original source.dj is the sole authority for meaning. Reuse the frozen
source analysis; do not perform or record a second doctrinal interpretation.
Restructure only Chinese lines that need help becoming natural English: make a
source-supported subject or reference explicit, expose an already-present
logical relation, split a long sentence, reorder a Chinese-specific structure,
or organize parallel clauses. Preserve ambiguity with passive or impersonal
wording when the source analysis does not establish an agent. Never invent
we, people, a speaker, an audience, or another agent without frozen source
evidence. Do not expand, explain Buddhist terms, add examples or background,
or change information, negation, degree, scope, conditions, logic, rhetoric,
voice, or doctrinal meaning. Preserve term-map forms and protected source terms
verbatim. The 90%-115% Chinese-length range is advisory only.

Use reorder only when the restructured line moves whole source clauses exactly
as delimited by Chinese sentence or clause punctuation. Reorder must not move
words, phrases, quotation fragments, or partial clauses within a punctuation-
bound clause. If a useful change cannot satisfy that rule, use only punctuation
and split_sentence when sufficient, or omit the record and defer the issue to
English translation and bilingual review.

Use explicit_reference only to replace an overt controlled pronoun or reference
form. If an omitted subject is uniquely established, represent it through
contextual_subject plus explicit_subject. Defer every other zero-reference
addition to the bilingual English translation and review gates; do not use
explicit_reference to bypass subject evidence.

Return only one UTF-8 JSON proposal conforming exactly to the compact schema
envelope. Consider every nonblank source line, but return only source-ordered
records for lines whose syntax you actually restructure. Do not return unselected-line decisions, hashes,
source excerpts, provenance, or aggregate counts: the runner derives and binds
those deterministically from the frozen inputs. Each selected record must bind
its minimal subject/reference/logic/structure judgments to exact quotes from
existing source-analysis fields. For the locked structured analysis, identify
one exact indexed item through `predicates[i].participants[j]`, `relations[i]`,
or `references_and_ellipsis[i]`; exact_quote must equal a complete scalar inside
that item: specifically its non-null evidence scalar, never notes. The runner
binds the whole item hash. For a legacy prose field,
exact_quote must equal the complete top-level scalar, never a favorable
substring cut from longer negative or uncertain context. Record only approved operations, and type
every lexical addition or replacement. Do not return a second doctrinal
analysis or semantic self-rating. Do not add new logic connectors or repeat
parallel text unless the compact contract expressly permits the exact typed
addition. Such an addition needs a current-line source basis, immediate
placement, and positive, non-ambiguous source-analysis items. Bind an omitted
or inherited subject to two indexed evidence items: one
`references_and_ellipsis[i]` item with a unique referent and exact current
predicate, plus one `predicates[p].participants[q]` item with the same predicate,
role, contextual status, and its own exact evidence; the participant is normally
null for a locked omitted subject. Bind an implicit connector to one indexed relation
item whose type, source clause, target clause, evidence status, and exact source
evidence all match the contract's deterministic mapping, including both cause
and result mapping to 因此. The locked structured
schema does not encode a shared parallel constituent and insertion location, so
do not make a lexical parallel completion from it; use punctuation/splitting or
defer the choice to English translation and bilingual review. Only legacy prose
analysis may use the contract's closed affirmative logic/parallel templates,
with no extra text before or after them.
For any selected record that has only structure or logic evidence, set
subject_strategy to not_applicable with evidence_status not_applicable and all
three nullable subject fields null. Never bind subject_strategy to structure or
logic evidence. In legacy_prose mode, never use semantic_head, must_preserve,
must_not_invent, doctrinal_and_cultural_terms,
quotations_allusions_fixed_expressions, or notes as authorizing evidence.
Do not wrap the JSON in Markdown.
"""


AI_PRETRANSLATION_PROMPT = """\
You are the source-side controlled-Chinese pretranslation role for the T1.2
AI-scale track. Read the first four @file inputs in this order: source.dj,
translation-project.yaml, source-analysis.json, and term-map.yaml. The final
@file is the compact response contract.

Aim for the structural clarity, momentum, and teacherly cadence of excellent
human pre-editing. Be willing to restructure a paragraph substantially when the
source licenses it: split long sentences, make uniquely recoverable subjects or
references explicit, expose existing logic, reorder whole information units
when equivalence is provable, clarify parallel structure and modifier scope,
use direct verbal clauses, and remove genuinely redundant carrier wording.
The goal is not minimal editing. The goal is Chinese that gives an English
translator clear sentence architecture while retaining the speaker's warmth
and rhetorical progression.

Semantic restraint is absolute. source.dj is the sole authority. Do not add or
remove a proposition, actor, obligation, cause, certainty, evaluation,
doctrinal explanation, quotation content, term meaning, or rhetorical step.
Preserve person, voice, negation, degree, quantity, modality, time, conditions,
scope, names, numbers, quotations, Buddhist terms, and deliberate metaphors.
If an ambitious rewrite cannot preserve all of these, do not rewrite it. Use a
block record when the ambiguity itself needs human judgment.

Return one JSON object with the sole root key records. Return only lines that
you actually rewrite or block, in source order. Unlisted lines are copied from
the frozen source by the runner, and their complete meaning ledgers and
protected constraints are reused from source-analysis.json; do not repeat
either the source or that analysis. Every rewrite is automatically sent to an
independent Pro reviewer, so do not assign safe/review status yourself.

Each record has exactly: paragraph_id, action, rewrite_transport,
transformation_types, risk_summary, confidence. action is rewrite or block.
For rewrite, rewrite_transport is the complete controlled Chinese line and
transformation_types is a nonempty array chosen from the contract. For block,
rewrite_transport is null and transformation_types is empty. risk_summary is
one concise Chinese string. confidence is high, medium, or low.

Transport every quotation mark inside rewrite_transport with these literal
tokens: U+0022 as ⟦Q0⟧, U+201C as ⟦Q1⟧, U+201D as ⟦Q2⟧. Never place a raw
straight or curly quotation mark inside rewrite_transport. Preserve the source
quotation-mark sequence exactly; the runner decodes and verifies it. Never
select structural lines beginning with {#, ##, or ###. Do not wrap the JSON in
Markdown and do not use tools or artifact links.
"""


AI_PRETRANSLATION_REVIEW_PROMPT = """\
You are the fresh independent Chinese-only review role for the T1.2 AI-scale
pretranslation track. Read the frozen source, term map, and the final sanitized
review-input @file. You are not given the drafting rationale or source-analysis
artifact. Review only the listed review_required source/rewrite pairs.

Challenge omissions, additions, subject choices, person shifts, antecedents,
logic, modifier scope, negation, degree, quantity, modality, chronology,
quotations, Buddhist terminology, and voice. Return exactly one JSON object
with a decisions array. Give one decision for every listed paragraph_id and no
others. Use accept only when the rewrite is source-supported without a major or
critical defect. Use revert_to_source when the original should be used. Use
block when a human decision is needed. Do not rewrite the manuscript and do not
wrap JSON in Markdown.
"""


TRANSLATION_WITH_PRETRANSLATION_PROMPT = """\
You are performing the locked T1 translation_and_self_review role. Read these
@file inputs in order: source.dj, translation-project.yaml,
source-analysis.json, term-map.yaml, accepted-pretranslation.json, the original
pretranslation artifact, and its human-approval or Pro-review evidence. If an
accepted-decisions file is present last, it may resolve a source-supported
choice but never override source.dj.

Translate the complete source into concise, immediately understandable,
natural publication English. source.dj is the sole authority. Use the accepted
pretranslation only to understand roles, reference, logic, scope, information
structure, and source-supported English expression direction. Never translate
from the controlled Chinese alone. Preserve physical-line and blank-line
parity, headings, anchors, links, emphasis, digits, quotations, questions,
doctrinal distinctions, speaker presence, and the teacher's voice. Return only
the complete target-draft.dj text with no fence, commentary, or preface.
"""


TRANSLATION_WITH_RESTRUCTURING_PROMPT = """\
You are performing the existing T1 translation_and_self_review role. Read the
first five @file inputs in this order: source.dj, translation-project.yaml,
source-analysis.json, term-map.yaml, and semantic-restructuring.json. If an
accepted-decisions @file is explicitly present last, apply only its
source-bound accepted decisions. They may correct automated analysis or term
choices, but they can never override source.dj.

Translate the complete source into concise, immediately understandable,
natural publication English. The original source.dj remains the sole authority
for meaning. Use the frozen source analysis and term map, and treat semantic
restructuring only as an auxiliary English-syntax plan. The final translation
must not be based on, or checked against, the restructured Chinese alone. Do not
expand, add explanations or examples, domesticate Buddhist terms, invent an
unstated subject, resolve an ambiguity that the source leaves unresolved, or
drop negation, degree, scope, conditions, logical relations, rhetoric, or the
teacher's voice. Preserve source line/paragraph positions required by T1.

Return only the complete target-draft.dj text, with no Markdown fence,
commentary, receipt, or preface.
"""


# This profile changes only OMP transport. Model identity, reasoning effort,
# prompt content, stage boundaries, and downstream quality gates remain locked.
LOSSLESS_OMP_FLAGS = (
    "-p",
    "--no-session",
    "--no-tools",
    "--hide-thinking",
)

T1_MODEL_STAGES = (
    "source_analysis",
    "ai_pretranslation",
    "ai_pretranslation_review",
    "semantic_restructuring",
    "translation_and_self_review",
    "bilingual_review_round_1",
    "review_application_round_1",
    "bilingual_review_round_2",
    "review_application_round_2",
    "title_audit",
    "concision_and_chinese_recheck",
)


def deepseek_environment(lock: dict) -> dict[str, str]:
    try:
        import keyring
    except ImportError as exc:
        raise StrategyT1Error("Python keyring is required") from exc
    policy = lock["credential_policy"]
    try:
        secret = keyring.get_password(policy["deepseek_service"], policy["deepseek_account"])
    except Exception as exc:
        raise StrategyT1Error("the operating-system credential vault is unavailable") from exc
    if not secret:
        raise StrategyT1Error("DeepSeek credential is missing from the T1 operating-system vault")
    return {"DEEPSEEK_API_KEY": secret}


def run_role(
    role: str,
    messages: list[str],
    *,
    cwd: Path,
    timeout: int | None = None,
) -> tuple[bytes, dict]:
    lock = load_lock()
    spec = lock["models"].get(role)
    if not spec:
        raise StrategyT1Error(f"unknown T1 model role: {role}")
    if not messages:
        raise StrategyT1Error("OMP role execution requires a message or @file input")
    for value in messages:
        if value.startswith("-"):
            raise StrategyT1Error("OMP message arguments may not begin with a flag")
    policy = lock["omp"].get("lossless_execution_policy")
    if not isinstance(policy, dict) or policy.get("required_flags") != list(
        LOSSLESS_OMP_FLAGS
    ):
        raise StrategyT1Error("locked OMP lossless execution profile is missing or changed")
    command = [
        lock["omp"]["executable"],
        *LOSSLESS_OMP_FLAGS,
        "--model",
        spec["selector"],
        "--thinking",
        spec["reasoning_effort"],
        "--max-time",
        str(timeout or lock["smoke_policy"]["maximum_seconds_per_model"]),
        *messages,
    ]
    environment = deepseek_environment(lock) if spec["provider"] == "deepseek" else None
    started = time.time()
    completed = run(command, cwd, env=environment, timeout=(timeout or 180) + 30)
    duration = round(time.time() - started, 6)
    receipt = {
        "receipt_id": str(uuid.uuid4()),
        "role": role,
        "provider": spec["provider"],
        "model": spec["model"],
        "selector": spec["selector"],
        "reasoning_effort": spec["reasoning_effort"],
        "exit_code": completed.returncode,
        "duration_seconds": duration,
        "stdout_sha256": sha256_bytes(completed.stdout),
        "stdout_bytes": len(completed.stdout),
        "stderr_sha256": sha256_bytes(completed.stderr),
        "stderr_bytes": len(completed.stderr),
        "secret_in_arguments": False,
        "execution_profile": {
            "name": policy["name"],
            "interaction": "single_response",
            "session_saved": False,
            "tools_enabled": False,
            "workflow_stage_combining_allowed": False,
        },
        "usage": {
            "actual_model_invocations": 1,
            "cache_hits": 0,
            "retry_count": 0,
            "input_tokens": None,
            "output_tokens": None,
            "token_accounting": "not_exposed_by_locked_omp_print_transport",
        },
    }
    if completed.returncode:
        raise StrategyT1Error(f"OMP role failed: {role}")
    return completed.stdout, receipt


def run_file(
    role: str,
    prompt_file: Path,
    output: Path,
    *,
    cwd: Path,
    timeout: int = 1800,
    bound_inputs: list[Path] | None = None,
    workflow_stage: str | None = None,
) -> dict:
    """Run one complete model stage without an interactive agent loop.

    ``bound_inputs`` are evidence bindings, not extra prompt arguments. The
    prompt must still contain or @attach every input the model is meant to read.
    """
    prompt_file = prompt_file.expanduser().resolve()
    cwd = cwd.expanduser().resolve()
    if not prompt_file.is_file():
        raise StrategyT1Error(f"prompt file is missing: {prompt_file}")
    if not cwd.is_dir():
        raise StrategyT1Error(f"OMP working directory is missing: {cwd}")
    if workflow_stage is not None and workflow_stage not in T1_MODEL_STAGES:
        raise StrategyT1Error(f"unknown T1 workflow stage: {workflow_stage}")
    output = _new_output(output)
    inputs = [_explicit_input(prompt_file, "prompt-file")]
    seen = {prompt_file}
    for index, path in enumerate(bound_inputs or (), start=1):
        resolved = path.expanduser().resolve()
        if resolved in seen:
            raise StrategyT1Error(f"duplicate OMP bound input: {resolved}")
        seen.add(resolved)
        inputs.append(_explicit_input(resolved, f"bound-input-{index:02d}:{resolved.name}"))
    stdout, receipt = run_role(role, [f"@{prompt_file}"], cwd=cwd, timeout=timeout)
    _verify_inputs_unchanged(inputs)
    if not stdout.strip():
        raise StrategyT1Error(f"OMP role returned an empty artifact: {role}")
    temporary = _temporary_output(output)
    try:
        temporary.write_bytes(stdout)
        _commit_new_artifact(temporary, output)
    finally:
        temporary.unlink(missing_ok=True)
    receipt["prompt_path"] = str(prompt_file)
    receipt["prompt_sha256"] = inputs[0]["sha256"]
    if workflow_stage is not None:
        receipt["workflow_stage"] = workflow_stage
    return _attach_file_evidence(receipt, inputs, output)


def _exists_including_broken_symlink(path: Path) -> bool:
    return os.path.lexists(os.fspath(path))


def _new_output(path: Path) -> Path:
    candidate = path.expanduser()
    if not candidate.is_absolute():
        candidate = Path.cwd() / candidate
    if _exists_including_broken_symlink(candidate):
        raise StrategyT1Error(f"refusing to overwrite existing T1 artifact: {candidate}")
    resolved = candidate.resolve()
    resolved.parent.mkdir(parents=True, exist_ok=True)
    return resolved


def _required_inputs(project: Path, names: tuple[str, ...]) -> list[dict[str, str]]:
    inputs: list[dict[str, str]] = []
    for name in names:
        path = (project / name).resolve()
        if not path.is_file():
            raise StrategyT1Error(f"required T1 input is missing: {path}")
        inputs.append(
            {
                "name": name,
                "absolute_path": str(path),
                "sha256": sha256_file(path),
            }
        )
    return inputs


def _explicit_input(path: Path, name: str) -> dict[str, str]:
    resolved = path.expanduser().resolve()
    if not resolved.is_file():
        raise StrategyT1Error(f"required T1 input is missing: {resolved}")
    return {
        "name": name,
        "absolute_path": str(resolved),
        "sha256": sha256_file(resolved),
    }


def _verify_inputs_unchanged(inputs: list[dict[str, str]]) -> None:
    for item in inputs:
        path = Path(item["absolute_path"])
        if not path.is_file() or sha256_file(path) != item["sha256"]:
            raise StrategyT1Error(
                f"T1 input changed during model execution: {item['name']}"
            )


def _temporary_output(output: Path) -> Path:
    return output.with_name(f".{output.name}.{uuid.uuid4().hex}.tmp")


def _commit_new_artifact(temporary: Path, output: Path) -> None:
    """Atomically publish a complete file without ever replacing a target."""
    try:
        os.link(temporary, output)
    except FileExistsError as exc:
        raise StrategyT1Error(
            f"refusing to overwrite existing T1 artifact: {output}"
        ) from exc
    except OSError as exc:
        raise StrategyT1Error(f"could not atomically publish T1 artifact: {output}") from exc


def _attach_file_evidence(
    receipt: dict,
    inputs: list[dict[str, str]],
    output: Path,
) -> dict:
    output_sha256 = sha256_file(output)
    receipt["inputs"] = inputs
    receipt["output"] = {
        "absolute_path": str(output),
        "sha256": output_sha256,
    }
    # Preserve the established flat output fields for existing receipt readers.
    receipt["output_path"] = str(output)
    receipt["output_sha256"] = output_sha256
    return receipt


def _json_object(stdout: bytes, label: str) -> dict:
    try:
        value = json.loads(stdout.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise StrategyT1Error(f"{label} did not return one valid UTF-8 JSON object") from exc
    if not isinstance(value, dict):
        raise StrategyT1Error(f"{label} JSON root must be an object")
    return value


def _json_bytes(value: dict) -> bytes:
    return (json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode(
        "utf-8"
    )


def _target_line_parity(source: Path, target: bytes) -> dict:
    try:
        source_lines = source.read_text(encoding="utf-8").splitlines()
        target_lines = target.decode("utf-8").splitlines()
    except (OSError, UnicodeDecodeError) as exc:
        raise StrategyT1Error("source or target draft is not valid UTF-8") from exc
    if len(source_lines) != len(target_lines):
        raise StrategyT1Error(
            "translation output does not preserve source physical-line parity"
        )
    for index, (source_line, target_line) in enumerate(
        zip(source_lines, target_lines, strict=True), start=1
    ):
        if bool(source_line.strip()) != bool(target_line.strip()):
            raise StrategyT1Error(
                f"translation output does not preserve blank-line parity at line {index}"
            )
    return {"status": "PASS", "physical_lines": len(source_lines)}


def run_ai_pretranslation(
    project: Path,
    *,
    output: Path | None = None,
    timeout: int = 1800,
) -> dict:
    """Generate the full-coverage AI-scale controlled-Chinese artifact."""
    project = project.expanduser().resolve()
    if not project.is_dir():
        raise StrategyT1Error(f"T1 project directory is missing: {project}")
    output = _new_output(output or (project / "pretranslation.json"))
    inputs = _required_inputs(project, (
        "source.dj",
        "translation-project.yaml",
        "source-analysis.json",
        "term-map.yaml",
    ))
    contract_bytes = _json_bytes(
        {
            "contract": "T1.2 compact bold controlled-Chinese pretranslation",
            "transport_version": "compact-changes-v1",
            "root_fields": ["records"],
            "record_fields": [
                "paragraph_id",
                "action",
                "rewrite_transport",
                "transformation_types",
                "risk_summary",
                "confidence",
            ],
            "action_values": ["rewrite", "block"],
            "transformation_types": [
                "split_sentence",
                "explicit_subject",
                "explicit_reference",
                "logic_exposure",
                "modifier_scope",
                "information_reorder",
                "parallel_structure",
                "teacher_voice",
                "redundancy_reduction",
                "punctuation_only",
            ],
            "confidence_values": ["high", "medium", "low"],
            "quotation_transport": {
                "⟦Q0⟧": "U+0022",
                "⟦Q1⟧": "U+201C",
                "⟦Q2⟧": "U+201D",
            },
        }
    )
    contract_path = project / f".pretranslation-contract.{uuid.uuid4().hex}.json"
    try:
        contract_path.write_bytes(contract_bytes)
        stdout, receipt = run_role(
            "source_analysis",
            [
                AI_PRETRANSLATION_PROMPT,
                *(f"@{item['absolute_path']}" for item in inputs),
                f"@{contract_path}",
            ],
            cwd=project,
            timeout=timeout,
        )
    finally:
        contract_path.unlink(missing_ok=True)
    proposal = _json_object(stdout, "AI pretranslation")
    artifact = hydrate_compact_ai_proposal(
        project,
        proposal,
        provenance={
            "kind": "model",
            "name": None,
            "provider": receipt["provider"],
            "model": receipt["model"],
            "reasoning_effort": receipt["reasoning_effort"],
            "role": receipt["role"],
        },
    )
    temporary = _temporary_output(output)
    try:
        temporary.write_bytes(_json_bytes(artifact))
        validation = validate_pretranslation(
            project, artifact_path=temporary, expected_mode="ai_scale"
        )
        _verify_inputs_unchanged(inputs)
        _commit_new_artifact(temporary, output)
    finally:
        temporary.unlink(missing_ok=True)
    receipt["workflow_stage"] = "ai_pretranslation"
    receipt["pretranslation_transport_version"] = "compact-changes-v1"
    receipt["pretranslation_contract_sha256"] = sha256_bytes(contract_bytes)
    receipt["pretranslation_proposal_sha256"] = sha256_bytes(stdout)
    receipt["pretranslation_validation"] = validation
    return _attach_file_evidence(receipt, inputs, output)


def run_ai_pretranslation_review(
    project: Path,
    *,
    pretranslation: Path | None = None,
    output: Path | None = None,
    timeout: int = 1800,
) -> dict:
    """Review only AI records routed as review_required and publish decisions."""
    project = project.expanduser().resolve()
    if not project.is_dir():
        raise StrategyT1Error(f"T1 project directory is missing: {project}")
    pretranslation = (
        pretranslation.expanduser().resolve()
        if pretranslation is not None
        else (project / "pretranslation.json").resolve()
    )
    validation = validate_pretranslation(
        project, artifact_path=pretranslation, expected_mode="ai_scale"
    )
    output = _new_output(output or (project / "pretranslation-review.json"))
    artifact = json.loads(pretranslation.read_text(encoding="utf-8"))
    review_records = [
        {
            "paragraph_id": item["paragraph_id"],
            "source": item["source"],
            "rewrite": item["rewrite"],
        }
        for item in artifact["records"]
        if item["status"] == "review_required"
    ]
    inputs = _required_inputs(project, ("source.dj", "term-map.yaml"))
    inputs.append(_explicit_input(pretranslation, "pretranslation.json"))
    if review_records:
        review_input = _json_bytes({"records": review_records})
        contract = _json_bytes(
            {
                "workflow_version": "1.2.0",
                "decision_fields": [
                    "paragraph_id",
                    "decision",
                    "severity",
                    "issue",
                    "required_revision",
                ],
                "decision_values": ["accept", "revert_to_source", "block"],
                "severity_values": ["none", "minor", "major", "critical"],
                "paragraph_ids": [item["paragraph_id"] for item in review_records],
            }
        )
        review_input_path = project / f".pretranslation-review-input.{uuid.uuid4().hex}.json"
        contract_path = project / f".pretranslation-review-contract.{uuid.uuid4().hex}.json"
        try:
            review_input_path.write_bytes(review_input)
            contract_path.write_bytes(contract)
            stdout, receipt = run_role(
                "bilingual_review",
                [
                    AI_PRETRANSLATION_REVIEW_PROMPT,
                    f"@{inputs[0]['absolute_path']}",
                    f"@{inputs[1]['absolute_path']}",
                    f"@{review_input_path}",
                    f"@{contract_path}",
                ],
                cwd=project,
                timeout=timeout,
            )
        finally:
            review_input_path.unlink(missing_ok=True)
            contract_path.unlink(missing_ok=True)
        proposal = _json_object(stdout, "AI pretranslation review")
        provenance = {
            "provider": receipt["provider"],
            "model": receipt["model"],
            "reasoning_effort": receipt["reasoning_effort"],
            "role": receipt["role"],
        }
        receipt["review_input_sha256"] = sha256_bytes(review_input)
        receipt["review_contract_sha256"] = sha256_bytes(contract)
        receipt["review_proposal_sha256"] = sha256_bytes(stdout)
    else:
        proposal = {"decisions": []}
        provenance = {
            "provider": None,
            "model": None,
            "reasoning_effort": None,
            "role": "not_required",
        }
        receipt = {
            "receipt_id": str(uuid.uuid4()),
            "role": "bilingual_review",
            "provider": None,
            "model": None,
            "selector": None,
            "reasoning_effort": None,
            "exit_code": 0,
            "duration_seconds": 0.0,
            "secret_in_arguments": False,
            "execution_profile": {"name": "deterministic-no-review-required"},
            "usage": {
                "actual_model_invocations": 0,
                "cache_hits": 0,
                "retry_count": 0,
                "input_tokens": 0,
                "output_tokens": 0,
                "token_accounting": "not_applicable",
            },
        }
    review = hydrate_ai_review(
        project,
        pretranslation,
        proposal,
        provenance=provenance,
    )
    temporary = _temporary_output(output)
    try:
        temporary.write_bytes(_json_bytes(review))
        review_validation = validate_ai_review(project, pretranslation, temporary)
        _verify_inputs_unchanged(inputs)
        _commit_new_artifact(temporary, output)
    finally:
        temporary.unlink(missing_ok=True)
    receipt["workflow_stage"] = "ai_pretranslation_review"
    receipt["pretranslation_validation"] = validation
    receipt["pretranslation_review_validation"] = review_validation
    return _attach_file_evidence(receipt, inputs, output)


def run_translation_with_pretranslation(
    project: Path,
    *,
    accepted_pretranslation: Path | None = None,
    pretranslation: Path | None = None,
    decision_evidence: Path | None = None,
    accepted_decisions: Path | None = None,
    output: Path | None = None,
    timeout: int = 1800,
) -> dict:
    """Translate with a fully validated human-quality or AI-scale aid."""
    project = project.expanduser().resolve()
    if not project.is_dir():
        raise StrategyT1Error(f"T1 project directory is missing: {project}")
    accepted_pretranslation = (
        accepted_pretranslation.expanduser().resolve()
        if accepted_pretranslation is not None
        else (project / "accepted-pretranslation.json").resolve()
    )
    accepted_validation = validate_accepted_pretranslation(project, accepted_pretranslation)
    accepted_value = json.loads(accepted_pretranslation.read_text(encoding="utf-8"))
    pretranslation = (
        pretranslation.expanduser().resolve()
        if pretranslation is not None
        else (project / "pretranslation.json").resolve()
    )
    if decision_evidence is None:
        name = (
            "human-pretranslation-approval.json"
            if accepted_value["mode"] == "human_quality"
            else "pretranslation-review.json"
        )
        decision_evidence = (project / name).resolve()
    else:
        decision_evidence = decision_evidence.expanduser().resolve()
    if accepted_value["mode"] == "human_quality":
        decision_validation = validate_human_approval(
            project, pretranslation, decision_evidence
        )
    else:
        decision_validation = validate_ai_review(
            project, pretranslation, decision_evidence
        )
    if accepted_value["pretranslation_sha256"] != sha256_file(pretranslation):
        raise StrategyT1Error("accepted pretranslation does not bind the supplied pretranslation")
    if accepted_value["decision_evidence_sha256"] != sha256_file(decision_evidence):
        raise StrategyT1Error("accepted pretranslation does not bind its decision evidence")
    output = _new_output(output or (project / "target-draft.dj"))
    inputs = _required_inputs(project, (
        "source.dj",
        "translation-project.yaml",
        "source-analysis.json",
        "term-map.yaml",
    ))
    inputs.extend(
        [
            _explicit_input(accepted_pretranslation, "accepted-pretranslation.json"),
            _explicit_input(pretranslation, "pretranslation.json"),
            _explicit_input(decision_evidence, "pretranslation-decision-evidence"),
        ]
    )
    if accepted_decisions is not None:
        inputs.append(_explicit_input(accepted_decisions, "accepted-decisions"))
    stdout, receipt = run_role(
        "translation_and_self_review",
        [
            TRANSLATION_WITH_PRETRANSLATION_PROMPT,
            *(f"@{item['absolute_path']}" for item in inputs),
        ],
        cwd=project,
        timeout=timeout,
    )
    parity = _target_line_parity(Path(inputs[0]["absolute_path"]), stdout)
    temporary = _temporary_output(output)
    try:
        temporary.write_bytes(stdout)
        _verify_inputs_unchanged(inputs)
        _commit_new_artifact(temporary, output)
    finally:
        temporary.unlink(missing_ok=True)
    receipt["workflow_stage"] = "translation_and_self_review"
    receipt["pretranslation_mode"] = accepted_value["mode"]
    receipt["accepted_pretranslation_validation"] = accepted_validation
    receipt["decision_evidence_validation"] = decision_validation
    receipt["target_line_parity"] = parity
    return _attach_file_evidence(receipt, inputs, output)


def run_semantic_restructuring(
    project: Path,
    *,
    accepted_decisions: Path | None = None,
    output: Path | None = None,
    timeout: int = 1800,
) -> dict:
    """Run the translator-owned restructuring substep and publish its JSON.

    This deliberately reuses ``translation_and_self_review``. It does not add a
    model role or let restructuring replace the frozen source as authority.
    """
    project = project.expanduser().resolve()
    if not project.is_dir():
        raise StrategyT1Error(f"T1 project directory is missing: {project}")
    output = _new_output(output or (project / "semantic-restructuring.json"))
    inputs = _required_inputs(
        project,
        (
            "source.dj",
            "translation-project.yaml",
            "source-analysis.json",
            "term-map.yaml",
        ),
    )
    if accepted_decisions is not None:
        inputs.append(_explicit_input(accepted_decisions, "accepted-decisions"))
    contract_bytes = (
        json.dumps(
            semantic_prompt_contract(project),
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n"
    ).encode("utf-8")
    contract_path = project / f".semantic-restructuring-contract.{uuid.uuid4().hex}.json"
    try:
        contract_path.write_bytes(contract_bytes)
        messages = [
            SEMANTIC_RESTRUCTURING_PROMPT,
            *(f"@{item['absolute_path']}" for item in inputs),
            f"@{contract_path}",
        ]
        stdout, receipt = run_role(
            "translation_and_self_review", messages, cwd=project, timeout=timeout
        )
    finally:
        contract_path.unlink(missing_ok=True)
    try:
        decoded = stdout.decode("utf-8")
        value = json.loads(decoded)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise StrategyT1Error(
            "semantic restructuring did not return one valid UTF-8 JSON object"
        ) from exc
    if not isinstance(value, dict):
        raise StrategyT1Error("semantic restructuring JSON root must be an object")
    accepted_hash = next(
        (item["sha256"] for item in inputs if item["name"] == "accepted-decisions"),
        None,
    )
    hydrated = hydrate_semantic_proposal(
        project,
        value,
        provenance={
            "provider": receipt["provider"],
            "model": receipt["model"],
            "reasoning_effort": receipt["reasoning_effort"],
            "role": receipt["role"],
        },
        accepted_decisions_sha256=accepted_hash,
    )
    hydrated_bytes = (
        json.dumps(hydrated, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")

    temporary = _temporary_output(output)
    try:
        temporary.write_bytes(hydrated_bytes)
        validation = validate_semantic_project(
            project,
            stage="restructuring",
            artifact_path=temporary,
            expected_accepted_decisions_sha256=accepted_hash,
        )
        _verify_inputs_unchanged(inputs)
        _commit_new_artifact(temporary, output)
    finally:
        temporary.unlink(missing_ok=True)
    receipt["semantic_restructuring_validation"] = validation
    receipt["semantic_restructuring_contract_sha256"] = sha256_bytes(contract_bytes)
    receipt["semantic_restructuring_proposal_sha256"] = sha256_bytes(stdout)
    return _attach_file_evidence(receipt, inputs, output)


def run_translation_with_restructuring(
    project: Path,
    *,
    restructuring: Path | None = None,
    accepted_decisions: Path | None = None,
    output: Path | None = None,
    timeout: int = 1800,
) -> dict:
    """Translate with the source, analysis, terms, and validated syntax aid."""
    project = project.expanduser().resolve()
    if not project.is_dir():
        raise StrategyT1Error(f"T1 project directory is missing: {project}")
    output = _new_output(output or (project / "target-draft.dj"))
    restructuring = (
        restructuring.expanduser().resolve()
        if restructuring is not None
        else (project / "semantic-restructuring.json").resolve()
    )
    if not restructuring.is_file():
        raise StrategyT1Error(
            f"required T1 input is missing: {restructuring}"
        )
    inputs = _required_inputs(
        project,
        (
            "source.dj",
            "translation-project.yaml",
            "source-analysis.json",
            "term-map.yaml",
        ),
    )
    inputs.append(
        _explicit_input(restructuring, "semantic-restructuring.json")
    )
    if accepted_decisions is not None:
        inputs.append(_explicit_input(accepted_decisions, "accepted-decisions"))
    accepted_hash = next(
        (item["sha256"] for item in inputs if item["name"] == "accepted-decisions"),
        None,
    )
    validation = validate_semantic_project(
        project,
        stage="restructuring",
        artifact_path=restructuring,
        expected_accepted_decisions_sha256=accepted_hash,
    )
    _verify_inputs_unchanged(inputs)
    messages = [TRANSLATION_WITH_RESTRUCTURING_PROMPT, *(
        f"@{item['absolute_path']}" for item in inputs
    )]
    stdout, receipt = run_role(
        "translation_and_self_review", messages, cwd=project, timeout=timeout
    )
    try:
        decoded = stdout.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise StrategyT1Error("target draft is not valid UTF-8") from exc
    if not decoded.strip():
        raise StrategyT1Error("translation_and_self_review returned an empty target draft")

    temporary = _temporary_output(output)
    try:
        temporary.write_bytes(stdout)
        _verify_inputs_unchanged(inputs)
        _commit_new_artifact(temporary, output)
    finally:
        temporary.unlink(missing_ok=True)
    receipt["semantic_restructuring_validation"] = validation
    return _attach_file_evidence(receipt, inputs, output)
