from __future__ import annotations
import builtins
import copy
import hashlib
import json
import sys
from pathlib import Path
import pytest

ROOT = Path(__file__).parents[1]
SCRIPTS = ROOT / "skills" / "mpi-strategy-t1" / "scripts"
sys.path.insert(0, str(SCRIPTS))
import semantic_bridge  # noqa: E402
import semantic_bridge_legacy  # noqa: E402
from t1_runtime import StrategyT1Error  # noqa: E402

def project_fixture(tmp_path: Path) -> tuple[Path, dict]:
    return tmp_path, semantic_bridge.fixture_artifact(tmp_path)

def write(project: Path, artifact: dict) -> None:
    semantic_bridge.write_artifact(project, artifact)

def record_with_text(artifact: dict, text: str) -> dict:
    changed = copy.deepcopy(artifact)
    changed["records"][0]["restructured_zh"] = text
    changed["records"][0]["sentence_units_zh"] = [text]
    return changed

def structured_paragraph(paragraph_id: str, **updates) -> dict:
    value = {
        "paragraph_id": paragraph_id,
        "predicates": [],
        "relations": [],
        "operators": [],
        "references_and_ellipsis": [],
        "competing_interpretations": [],
        "must_preserve": [],
        "must_not_invent": [],
        "status": "clear",
    }
    value.update(updates)
    return value

def structured_project(tmp_path: Path) -> Path:
    project = tmp_path
    metadata = project / semantic_bridge.PROJECT_NAME
    metadata.write_text("project_id: locked-stage4-interface\n", encoding="utf-8")
    source = project / "source.dj"
    source.write_text(
        "修行者应观察自心。\n"
        "起烦恼，就应觉察。\n"
        "勤修，得乐。\n"
        "佛陀入座。\n"
        "他开始说法。\n"
        "对自己要诚实，对他人慈悲。\n",
        encoding="utf-8",
    )
    term_map = project / semantic_bridge.TERM_MAP_NAME
    term_map.write_text(
        '{"terms": [{"source": "佛陀", "preferred": "the Buddha"}]}\n',
        encoding="utf-8",
    )
    source_sha, _, _ = semantic_bridge.source_index(source)
    analysis = {
        "schema_version": 1,
        "source_sha256": source_sha,
        "project_sha256": semantic_bridge.sha256_file(metadata),
        "term_map_sha256": semantic_bridge.sha256_file(term_map),
        "paragraphs": [
            structured_paragraph("L1"),
            structured_paragraph(
                "L2",
                predicates=[{
                    "predicate": "起烦恼",
                    "canonical_meaning": "生起烦恼",
                    "evidence": "起烦恼",
                    "participants": [{
                        "role": "experiencer",
                        "participant": None,
                        "evidence": "起烦恼",
                        "evidence_status": "contextual_inference",
                        "notes": "体验者承接上一句。",
                    }],
                }],
                references_and_ellipsis=[{
                    "kind": "inherited_subject",
                    "expression": None,
                    "predicate": "起烦恼",
                    "role": "experiencer",
                    "referent": "修行者",
                    "candidate_referents": ["修行者"],
                    "evidence": "起烦恼",
                    "evidence_status": "contextual_inference",
                    "notes": "本句沿用上一句主体。",
                }],
            ),
            structured_paragraph(
                "L3",
                relations=[{
                    "type": "cause",
                    "source_clause": "勤修",
                    "target_clause": "得乐",
                    "evidence": "勤修，得乐",
                    "evidence_status": "contextual_inference",
                    "notes": "前项为因，后项为果。",
                }],
            ),
            structured_paragraph("L4"),
            structured_paragraph(
                "L5",
                references_and_ellipsis=[{
                    "kind": "coreference",
                    "expression": "他",
                    "predicate": "开始说法",
                    "role": "agent",
                    "referent": "佛陀",
                    "candidate_referents": ["佛陀"],
                    "evidence": "佛陀入座。\n他",
                    "evidence_status": "contextual_inference",
                    "notes": "代词承接上一句唯一人物。",
                }],
            ),
            structured_paragraph(
                "L6",
                references_and_ellipsis=[{
                    "kind": "other",
                    "expression": "慈悲",
                    "predicate": "慈悲",
                    "role": "other",
                    "referent": "要",
                    "candidate_referents": ["要"],
                    "evidence": "对自己要诚实，对他人慈悲",
                    "evidence_status": "contextual_inference",
                    "notes": "现有结构没有共享成分或插入位置字段。",
                }],
            ),
        ],
    }
    (project / semantic_bridge.ANALYSIS_NAME).write_text(
        json.dumps(analysis, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return project

def structured_logic_project(
    tmp_path: Path,
    source_text: str,
    relations: list[dict],
    *,
    basis: str,
    target_text: str,
) -> tuple[Path, dict]:
    project = tmp_path
    metadata = project / semantic_bridge.PROJECT_NAME
    metadata.write_text("project_id: structured-logic-case\n", encoding="utf-8")
    source = project / "source.dj"
    source.write_text(source_text + "\n", encoding="utf-8")
    term_map = project / semantic_bridge.TERM_MAP_NAME
    term_map.write_text(
        '{"terms": [{"source": "勤修", "preferred": "practice diligently"}]}\n',
        encoding="utf-8",
    )
    source_sha, _, _ = semantic_bridge.source_index(source)
    analysis = {
        "schema_version": 1,
        "source_sha256": source_sha,
        "project_sha256": semantic_bridge.sha256_file(metadata),
        "term_map_sha256": semantic_bridge.sha256_file(term_map),
        "paragraphs": [structured_paragraph("L1", relations=relations)],
    }
    (project / semantic_bridge.ANALYSIS_NAME).write_text(
        json.dumps(analysis, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    proposal = {
        "records": [{
            "paragraph_id": "L1",
            "analysis_evidence": [{
                "kind": "logic",
                "source_analysis_field": "relations[0]",
                "exact_quote": relations[0]["evidence"],
            }],
            "restructured_zh": target_text,
            "restructuring_operations": ["explicit_logic"],
            "sentence_units_zh": [target_text],
            "subject_strategy": {
                "mode": "not_applicable",
                "evidence_status": "not_applicable",
                "subject_zh": None,
                "antecedent_zh": None,
                "evidence_index": None,
            },
            "typed_changes": [{
                "change": "addition",
                "operation": "explicit_logic",
                "source_zh": None,
                "restructured_zh": "因此",
                "evidence_status": relations[0]["evidence_status"],
                "basis_zh": basis,
                "evidence_index": 0,
            }],
        }]
    }
    return project, proposal

def test_valid_selected_record_is_lightweight_and_inventory_is_honest(tmp_path):
    project, artifact = project_fixture(tmp_path)
    report = semantic_bridge.validate_project(project)
    assert report["status"] == "PASS"
    assert report["analysis_schema_mode"] == "legacy_prose"
    assert report["source_nonblank_units"] == 2
    assert report["selected_line_count"] == 1
    assert report["source_line_inventory"] == {
        "total_nonblank_lines": 2,
        "selected_count": 1,
        "unselected_count": 1,
        "selected_line_ids": ["L003"],
        "unselected_line_ids": ["L001"],
        "inventory_status": "ACCOUNTED",
        "attention_proven": False,
    }
    assert report["mechanical_scope"]["doctrinal_equivalence_proven"] is False
    assert report["mechanical_scope"]["implicit_logic_correctness_proven"] is False
    assert report["mechanical_scope"]["parallel_scope_correctness_proven"] is False
    assert artifact["accepted_decisions_sha256"] is None
    assert artifact["generated_by"] == semantic_bridge.LOCKED_PROVENANCE
    record = artifact["records"][0]
    assert "meaning_explication_zh" not in record
    assert "structure_plan" not in record
    assert "restructuring_checks" not in record
    assert "predicates" not in json.dumps(record, ensure_ascii=False)

def test_prompt_contract_is_compact_and_model_does_not_copy_hashes_or_source(tmp_path):
    project, _ = project_fixture(tmp_path)
    contract = semantic_bridge.prompt_contract(project)
    encoded = json.dumps(contract, ensure_ascii=False, indent=2).encode()
    assert len(encoded) < 100_000
    assert set(contract) == {
        "contract",
        "workflow_version",
        "analysis_schema_mode",
        "legacy_evidence_fields_by_kind",
        "proposal_json_schema",
        "runner_hydration",
        "rules",
        "mechanical_scope",
    }
    serialized = json.dumps(contract, ensure_ascii=False)
    for forbidden in (
        "source_excerpt",
        "source_line_sha256",
        "source_analysis_record_sha256",
        "source_analysis_value_sha256",
        "line_catalog",
        "line_decisions",
        "formal item",
    ):
        assert forbidden not in serialized
    assert "does_not_prove" in contract["mechanical_scope"]
    rules = "\n".join(contract["rules"])
    assert "two indexed evidence entries" in rules
    assert "participant is normally null" in rules
    assert "cause/result→因此" in rules
    assert contract["analysis_schema_mode"] == "legacy_prose"
    assert "semantic_head" not in contract["legacy_evidence_fields_by_kind"]["structure"]
    assert "subject_strategy may bind only subject or reference evidence" in rules
    assert "reorder only to move whole source clauses exactly" in rules

def test_proposal_hydration_adds_all_deterministic_bindings(tmp_path):
    project, artifact = project_fixture(tmp_path)
    record = artifact["records"][0]
    proposal_record = {
        key: copy.deepcopy(value)
        for key, value in record.items()
        if key in semantic_bridge.PROPOSAL_RECORD_FIELDS
    }
    for evidence in proposal_record["analysis_evidence"]:
        evidence.pop("source_analysis_value_sha256")
    decisions_hash = hashlib.sha256(b"accepted\n").hexdigest()
    hydrated = semantic_bridge.hydrate_proposal(
        project,
        {"records": [proposal_record]},
        provenance=semantic_bridge.LOCKED_PROVENANCE,
        accepted_decisions_sha256=decisions_hash,
    )
    expected = copy.deepcopy(artifact)
    expected["accepted_decisions_sha256"] = decisions_hash
    assert hydrated == expected
    assert hydrated["records"][0]["source_analysis_fields_used"] == [
        "semantic_roles_and_references",
        "logic_and_scope",
    ]
    bad = {"records": [copy.deepcopy(proposal_record)]}
    bad["records"][0]["source_excerpt"] = "模型不应回抄"
    with pytest.raises(StrategyT1Error, match="unapproved fields"):
        semantic_bridge.hydrate_proposal(project, bad)

def test_locked_stage4_indexed_subject_is_reused_without_second_analysis(tmp_path):
    project = structured_project(tmp_path)
    proposal = {
        "records": [{
            "paragraph_id": "L2",
            "analysis_evidence": [{
                "kind": "subject",
                "source_analysis_field": "references_and_ellipsis[0]",
                "exact_quote": "起烦恼",
            }, {
                "kind": "subject",
                "source_analysis_field": "predicates[0].participants[0]",
                "exact_quote": "起烦恼",
            }],
            "restructured_zh": "修行者起烦恼，就应觉察。",
            "restructuring_operations": ["explicit_subject"],
            "sentence_units_zh": ["修行者起烦恼，就应觉察。"],
            "subject_strategy": {
                "mode": "contextual_subject",
                "evidence_status": "contextual_inference",
                "subject_zh": "修行者",
                "antecedent_zh": "修行者应观察自心",
                "evidence_index": 0,
            },
            "typed_changes": [{
                "change": "addition",
                "operation": "explicit_subject",
                "source_zh": None,
                "restructured_zh": "修行者",
                "evidence_status": "contextual_inference",
                "basis_zh": "起烦恼",
                "evidence_index": 0,
            }],
        }]
    }
    artifact = semantic_bridge.hydrate_proposal(project, proposal)
    evidence = artifact["records"][0]["analysis_evidence"][0]
    analysis = json.loads((project / semantic_bridge.ANALYSIS_NAME).read_text())
    assert evidence["source_analysis_value_sha256"] == semantic_bridge.canonical_hash(
        analysis["paragraphs"][1]["references_and_ellipsis"][0]
    )
    write(project, artifact)
    report = semantic_bridge.validate_project(project)
    assert report["status"] == "PASS"
    assert report["analysis_schema_mode"] == "locked_structured"
    bad_path = copy.deepcopy(proposal)
    bad_path["records"][0]["analysis_evidence"][0][
        "source_analysis_field"
    ] = "references_and_ellipsis[1]"
    with pytest.raises(StrategyT1Error, match="absent source-analysis field path"):
        semantic_bridge.hydrate_proposal(project, bad_path)
    for field, kind, quote, message in (
        (
            "references_and_ellipsis[00]",
            "subject",
            "起烦恼",
            "unsupported source-analysis field path",
        ),
        (
            "references_and_ellipsis[0]",
            "reference",
            "起烦恼",
            "cannot relabel",
        ),
        (
            "references_and_ellipsis[0]",
            "subject",
            "本句沿用上一句主体。",
            "notes never authorize",
        ),
    ):
        bad_evidence = copy.deepcopy(proposal)
        selected = bad_evidence["records"][0]["analysis_evidence"][0]
        selected.update(
            {"source_analysis_field": field, "kind": kind, "exact_quote": quote}
        )
        with pytest.raises(StrategyT1Error, match=message):
            semantic_bridge.hydrate_proposal(project, bad_evidence)
    cross_analysis = copy.deepcopy(analysis)
    cross_analysis["paragraphs"][1]["references_and_ellipsis"].append({
        "kind": "inherited_subject",
        "expression": None,
        "predicate": "觉察",
        "role": "experiencer",
        "referent": "修行者",
        "candidate_referents": ["修行者"],
        "evidence": "修行者应观察自心。\n起烦恼，就应觉察",
        "evidence_status": "contextual_inference",
        "notes": "另一谓词的主语承接。",
    })
    (project / semantic_bridge.ANALYSIS_NAME).write_text(
        json.dumps(cross_analysis, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    cross_bound = copy.deepcopy(proposal)
    cross_record = cross_bound["records"][0]
    cross_record["analysis_evidence"].append({
        "kind": "subject",
        "source_analysis_field": "references_and_ellipsis[1]",
        "exact_quote": "修行者应观察自心。\n起烦恼，就应觉察",
    })
    cross_record["restructured_zh"] = "起烦恼，就应修行者觉察。"
    cross_record["sentence_units_zh"] = ["起烦恼，就应修行者觉察。"]
    cross_record["typed_changes"][0]["basis_zh"] = "觉察"
    cross_record["typed_changes"][0]["evidence_index"] = 2
    write(project, semantic_bridge.hydrate_proposal(project, cross_bound))
    with pytest.raises(StrategyT1Error, match="same evidence item"):
        semantic_bridge.validate_project(project)
    (project / semantic_bridge.ANALYSIS_NAME).write_text(
        json.dumps(analysis, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    analysis["paragraphs"][1]["references_and_ellipsis"][0][
        "candidate_referents"
    ] = ["修行者", "佛陀"]
    (project / semantic_bridge.ANALYSIS_NAME).write_text(
        json.dumps(analysis, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    rejected = semantic_bridge.hydrate_proposal(project, proposal)
    write(project, rejected)
    with pytest.raises(StrategyT1Error, match="uniquely authorize"):
        semantic_bridge.validate_project(project)

def test_locked_contextual_subject_uses_unique_slot_and_valid_predicate_anchor(tmp_path):
    project = tmp_path
    artifact = semantic_bridge.fixture_structured_artifact(project)
    subject_record = artifact["records"][0]
    proposal_record = {
        key: copy.deepcopy(value)
        for key, value in subject_record.items()
        if key in semantic_bridge.PROPOSAL_RECORD_FIELDS
    }
    for evidence in proposal_record["analysis_evidence"]:
        evidence.pop("source_analysis_value_sha256")
    proposal = {"records": [proposal_record]}
    analysis_path = project / semantic_bridge.ANALYSIS_NAME
    original = json.loads(analysis_path.read_text())

    alias = copy.deepcopy(original)
    alias_ref = alias["paragraphs"][1]["references_and_ellipsis"][0]
    alias_ref["referent"] = "讲者"
    alias_ref["candidate_referents"] = ["修行者"]
    analysis_path.write_text(json.dumps(alias, ensure_ascii=False) + "\n")
    write(project, semantic_bridge.hydrate_proposal(project, proposal))
    with pytest.raises(StrategyT1Error, match="uniquely authorize"):
        semantic_bridge.validate_project(project)

    mutations = []
    overt = copy.deepcopy(original)
    overt["paragraphs"][1]["references_and_ellipsis"][0]["expression"] = "他"
    mutations.append(overt)
    wrong_anchor = copy.deepcopy(original)
    wrong_anchor["paragraphs"][1]["predicates"][0]["evidence"] = "就应觉察"
    mutations.append(wrong_anchor)
    conflicting_ref = copy.deepcopy(original)
    conflicting_ref["paragraphs"][1]["references_and_ellipsis"].append({
        "kind": "omitted_subject",
        "expression": None,
        "predicate": "起烦恼",
        "role": "experiencer",
        "referent": "佛陀",
        "candidate_referents": ["佛陀"],
        "evidence": "起烦恼",
        "evidence_status": "contextual_inference",
        "notes": "冲突候选。",
    })
    mutations.append(conflicting_ref)
    conflicting_participant = copy.deepcopy(original)
    conflicting_participant["paragraphs"][1]["predicates"][0][
        "participants"
    ].append({
        "role": "experiencer",
        "participant": "佛陀",
        "evidence": "起烦恼",
        "evidence_status": "contextual_inference",
        "notes": "冲突参与者。",
    })
    mutations.append(conflicting_participant)
    for changed in mutations:
        analysis_path.write_text(json.dumps(changed, ensure_ascii=False) + "\n")
        write(project, semantic_bridge.hydrate_proposal(project, proposal))
        with pytest.raises(StrategyT1Error, match="uniquely authorize"):
            semantic_bridge.validate_project(project)

def test_locked_and_legacy_source_analysis_records_cannot_mix(tmp_path):
    project = structured_project(tmp_path)
    analysis_path = project / semantic_bridge.ANALYSIS_NAME
    analysis = json.loads(analysis_path.read_text())
    analysis["paragraphs"][0] = {
        "paragraph_id": "L1",
        "semantic_roles_and_references": "修行者为当前行主语",
    }
    analysis_path.write_text(json.dumps(analysis, ensure_ascii=False) + "\n")
    with pytest.raises(StrategyT1Error, match="cannot mix"):
        semantic_bridge.project_context(project)

@pytest.mark.parametrize("field", ["logic_and_scope", "parallelism"])
def test_locked_structured_record_rejects_injected_legacy_evidence(tmp_path, field):
    project = structured_project(tmp_path)
    analysis_path = project / semantic_bridge.ANALYSIS_NAME
    analysis = json.loads(analysis_path.read_text())
    analysis["paragraphs"][5][field] = (
        "两项并列；第二项“慈悲”承前省略“要”，可在“慈悲”前补“要”"
    )
    analysis_path.write_text(json.dumps(analysis, ensure_ascii=False) + "\n")
    with pytest.raises(StrategyT1Error, match="legacy evidence cannot mix"):
        semantic_bridge.project_context(project)

def test_malformed_locked_signature_cannot_downgrade_to_legacy_mode(tmp_path):
    assert semantic_bridge._analysis_record_mode({"relations": "完整旧式标量"}) == (
        "legacy_prose"
    )
    assert semantic_bridge._analysis_record_mode({"relations": {}}) == (
        "locked_structured"
    )
    project = structured_project(tmp_path)
    analysis_path = project / semantic_bridge.ANALYSIS_NAME
    analysis = json.loads(analysis_path.read_text())
    record = analysis["paragraphs"][2]
    for field in semantic_bridge.STRUCTURED_SIGNATURE_FIELDS:
        record[field] = {}
    record["logic_and_scope"] = "“勤修”为原因，“得乐”为因果结果"
    analysis_path.write_text(json.dumps(analysis, ensure_ascii=False) + "\n")
    with pytest.raises(
        StrategyT1Error,
        match="non_list|legacy_evidence_fields|cannot mix",
    ):
        semantic_bridge.project_context(project)

def test_locked_stage4_indexed_relation_projects_only_bound_implicit_logic(tmp_path):
    project = structured_project(tmp_path)
    proposal = {
        "records": [{
            "paragraph_id": "L3",
            "analysis_evidence": [{
                "kind": "logic",
                "source_analysis_field": "relations[0]",
                "exact_quote": "勤修，得乐",
            }],
            "restructured_zh": "勤修，因此得乐。",
            "restructuring_operations": ["explicit_logic"],
            "sentence_units_zh": ["勤修，因此得乐。"],
            "subject_strategy": {
                "mode": "not_applicable",
                "evidence_status": "not_applicable",
                "subject_zh": None,
                "antecedent_zh": None,
                "evidence_index": None,
            },
            "typed_changes": [{
                "change": "addition",
                "operation": "explicit_logic",
                "source_zh": None,
                "restructured_zh": "因此",
                "evidence_status": "contextual_inference",
                "basis_zh": "得乐",
                "evidence_index": 0,
            }],
        }]
    }
    artifact = semantic_bridge.hydrate_proposal(project, proposal)
    write(project, artifact)
    assert semantic_bridge.validate_project(project)["status"] == "PASS"
    analysis_path = project / semantic_bridge.ANALYSIS_NAME
    analysis = json.loads(analysis_path.read_text())
    analysis["paragraphs"][2]["relations"][0]["type"] = "coordination"
    analysis_path.write_text(json.dumps(analysis, ensure_ascii=False) + "\n")
    rejected = semantic_bridge.hydrate_proposal(project, proposal)
    write(project, rejected)
    with pytest.raises(StrategyT1Error, match="does not authorize"):
        semantic_bridge.validate_project(project)

def test_locked_stage4_result_relation_can_project_causal_result_connector(tmp_path):
    relation = {
        "type": "result",
        "source_clause": "勤修",
        "target_clause": "得乐",
        "evidence": "勤修，得乐",
        "evidence_status": "explicit",
        "notes": "后项是前项结果。",
    }
    project, proposal = structured_logic_project(
        tmp_path,
        "勤修，得乐。",
        [relation],
        basis="得乐",
        target_text="勤修，因此得乐。",
    )
    write(project, semantic_bridge.hydrate_proposal(project, proposal))
    assert semantic_bridge.validate_project(project)["status"] == "PASS"

@pytest.mark.parametrize(
    ("source_text", "basis", "evidence"),
    (
        ("勤修，就得乐。", "就得乐", "勤修，就得乐"),
        ("勤修，后来所以得乐。", "后来所以得乐", "勤修，后来所以得乐"),
        ("勤修，后来所 以得乐。", "后来所 以得乐", "勤修，后来所 以得乐"),
        ("勤修，后来所　以得乐。", "后来所　以得乐", "勤修，后来所　以得乐"),
        ("勤修，后来所\u200b以得乐。", "后来所\u200b以得乐", "勤修，后来所\u200b以得乐"),
        ("勤修，后来所\u200d以得乐。", "后来所\u200d以得乐", "勤修，后来所\u200d以得乐"),
        ("勤修，后来所\ufe0f以得乐。", "后来所\ufe0f以得乐", "勤修，后来所\ufe0f以得乐"),
        ("外在结果暂时，而心灵结果长久。", "而心灵结果长久", "外在结果暂时，而心灵结果长久"),
        ("勤修，休息，得乐。", "得乐", "勤修，休息，得乐"),
        ("勤修，休息，勤修，得乐。", "得乐", "勤修，休息，勤修，得乐"),
    ),
)
def test_locked_stage4_logic_defers_existing_marker_or_nonunique_nonadjacent_pair(
    tmp_path, source_text, basis, evidence
):
    relation = {
        "type": "cause",
        "source_clause": "勤修",
        "target_clause": basis,
        "evidence": evidence,
        "evidence_status": "contextual_inference",
        "notes": "因果关系。",
    }
    target = source_text.replace(basis, "因此" + basis, 1)
    project, proposal = structured_logic_project(
        tmp_path, source_text, [relation], basis=basis, target_text=target
    )
    write(project, semantic_bridge.hydrate_proposal(project, proposal))
    with pytest.raises(
        StrategyT1Error,
        match="complete unique later-clause|does not authorize|already contains a visible logic marker",
    ):
        semantic_bridge.validate_project(project)

@pytest.mark.parametrize(
    "conflict",
    (
        {
            "type": "coordination",
            "source_clause": "勤修",
            "target_clause": "得乐",
            "evidence": "勤修，得乐",
            "evidence_status": "contextual_inference",
            "notes": "同向冲突。",
        },
        {
            "type": "contrast",
            "source_clause": "勤修",
            "target_clause": "得乐",
            "evidence": "勤修，得乐",
            "evidence_status": "ambiguous",
            "notes": "关系未定。",
        },
        {
            "type": "cause",
            "source_clause": "得乐",
            "target_clause": "勤修",
            "evidence": "勤修，得乐",
            "evidence_status": "contextual_inference",
            "notes": "反向冲突。",
        },
        {
            "type": "coordination",
            "source_clause": "勤修",
            "target_clause": "得乐 ",
            "evidence": "勤修，得乐",
            "evidence_status": "contextual_inference",
            "notes": "尾空格不能隐藏冲突。",
        },
        {
            "type": "coordination",
            "source_clause": "勤修，",
            "target_clause": "得乐",
            "evidence": "勤修，得乐",
            "evidence_status": "contextual_inference",
            "notes": "尾标点不能隐藏冲突。",
        },
    ),
)
def test_locked_stage4_logic_defers_any_same_pair_conflict(tmp_path, conflict):
    selected = {
        "type": "cause",
        "source_clause": "勤修",
        "target_clause": "得乐",
        "evidence": "勤修，得乐",
        "evidence_status": "contextual_inference",
        "notes": "前因后果。",
    }
    project, proposal = structured_logic_project(
        tmp_path,
        "勤修，得乐。",
        [selected, conflict],
        basis="得乐",
        target_text="勤修，因此得乐。",
    )
    write(project, semantic_bridge.hydrate_proposal(project, proposal))
    with pytest.raises(StrategyT1Error, match="does not authorize"):
        semantic_bridge.validate_project(project)

def test_locked_stage4_indexed_coreference_can_replace_only_unique_overt_form(tmp_path):
    project = structured_project(tmp_path)
    proposal = {
        "records": [{
            "paragraph_id": "L5",
            "analysis_evidence": [{
                "kind": "reference",
                "source_analysis_field": "references_and_ellipsis[0]",
                "exact_quote": "佛陀入座。\n他",
            }],
            "restructured_zh": "佛陀开始说法。",
            "restructuring_operations": ["explicit_reference"],
            "sentence_units_zh": ["佛陀开始说法。"],
            "subject_strategy": {
                "mode": "not_applicable",
                "evidence_status": "not_applicable",
                "subject_zh": None,
                "antecedent_zh": None,
                "evidence_index": None,
            },
            "typed_changes": [{
                "change": "replacement",
                "operation": "explicit_reference",
                "source_zh": "他",
                "restructured_zh": "佛陀",
                "evidence_status": "contextual_inference",
                "basis_zh": "佛陀入座",
                "evidence_index": 0,
            }],
        }]
    }
    artifact = semantic_bridge.hydrate_proposal(project, proposal)
    write(project, artifact)
    assert semantic_bridge.validate_project(project)["status"] == "PASS"
    moved = copy.deepcopy(proposal)
    moved_record = moved["records"][0]
    moved_record["restructured_zh"] = "开始佛陀说法。"
    moved_record["sentence_units_zh"] = ["开始佛陀说法。"]
    write(project, semantic_bridge.hydrate_proposal(project, moved))
    with pytest.raises(StrategyT1Error, match="in place"):
        semantic_bridge.validate_project(project)
    write(project, artifact)
    analysis_path = project / semantic_bridge.ANALYSIS_NAME
    analysis = json.loads(analysis_path.read_text())
    invalid_role = copy.deepcopy(analysis)
    invalid_role["paragraphs"][4]["references_and_ellipsis"][0]["role"] = "bogus"
    conflicting_reference = copy.deepcopy(analysis)
    conflicting_reference["paragraphs"][4]["references_and_ellipsis"].append({
        "kind": "coreference",
        "expression": "他",
        "predicate": "入座",
        "role": "patient",
        "referent": "阿难",
        "candidate_referents": ["阿难"],
        "evidence": "佛陀入座。\n他",
        "evidence_status": "contextual_inference",
        "notes": "同一表层形式的冲突所指。",
    })
    for changed in (invalid_role, conflicting_reference):
        analysis_path.write_text(json.dumps(changed, ensure_ascii=False) + "\n")
        rejected = semantic_bridge.hydrate_proposal(project, proposal)
        write(project, rejected)
        with pytest.raises(StrategyT1Error, match="does not uniquely authorize"):
            semantic_bridge.validate_project(project)
    analysis_path.write_text(json.dumps(analysis, ensure_ascii=False) + "\n")
    analysis["paragraphs"][4]["references_and_ellipsis"][0]["referent"] = "阿难"
    analysis["paragraphs"][4]["references_and_ellipsis"][0][
        "candidate_referents"
    ] = ["阿难"]
    analysis_path.write_text(json.dumps(analysis, ensure_ascii=False) + "\n")
    rejected = semantic_bridge.hydrate_proposal(project, proposal)
    write(project, rejected)
    with pytest.raises(StrategyT1Error, match="does not uniquely authorize"):
        semantic_bridge.validate_project(project)

@pytest.mark.parametrize("separator", (" ", "　", "\u200b", "\u200d", "\ufe0f"))
def test_locked_coreference_conflict_cannot_hide_behind_unicode(separator, tmp_path):
    project = structured_project(tmp_path)
    source_path = project / "source.dj"
    source_text = source_path.read_text(encoding="utf-8").replace(
        "他开始说法。", f"他{separator}开始说法。"
    )
    source_path.write_text(source_text, encoding="utf-8")
    analysis_path = project / semantic_bridge.ANALYSIS_NAME
    analysis = json.loads(analysis_path.read_text(encoding="utf-8"))
    analysis["source_sha256"] = semantic_bridge.sha256_file(source_path)
    analysis["paragraphs"][4]["references_and_ellipsis"].append({
        "kind": "coreference",
        "expression": f"他{separator}",
        "predicate": "开始说法",
        "role": "agent",
        "referent": "阿难",
        "candidate_referents": ["阿难"],
        "evidence": f"佛陀入座。\n他{separator}",
        "evidence_status": "contextual_inference",
        "notes": "同一表层形式的冲突所指。",
    })
    analysis_path.write_text(
        json.dumps(analysis, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    target = f"佛陀{separator}开始说法。"
    proposal = {
        "records": [{
            "paragraph_id": "L5",
            "analysis_evidence": [{
                "kind": "reference",
                "source_analysis_field": "references_and_ellipsis[0]",
                "exact_quote": "佛陀入座。\n他",
            }],
            "restructured_zh": target,
            "restructuring_operations": ["explicit_reference"],
            "sentence_units_zh": [target],
            "subject_strategy": {
                "mode": "not_applicable",
                "evidence_status": "not_applicable",
                "subject_zh": None,
                "antecedent_zh": None,
                "evidence_index": None,
            },
            "typed_changes": [{
                "change": "replacement",
                "operation": "explicit_reference",
                "source_zh": "他",
                "restructured_zh": "佛陀",
                "evidence_status": "contextual_inference",
                "basis_zh": "佛陀入座",
                "evidence_index": 0,
            }],
        }]
    }
    write(project, semantic_bridge.hydrate_proposal(project, proposal))
    with pytest.raises(StrategyT1Error, match="does not uniquely authorize"):
        semantic_bridge.validate_project(project)

def test_locked_stage4_parallel_lexical_completion_defers_without_scope_field(tmp_path):
    project = structured_project(tmp_path)
    proposal = {
        "records": [{
            "paragraph_id": "L6",
            "analysis_evidence": [{
                "kind": "structure",
                "source_analysis_field": "references_and_ellipsis[0]",
                "exact_quote": "对自己要诚实，对他人慈悲",
            }],
            "restructured_zh": "对自己要诚实，对他人要慈悲。",
            "restructuring_operations": ["parallelism"],
            "sentence_units_zh": ["对自己要诚实，对他人要慈悲。"],
            "subject_strategy": {
                "mode": "not_applicable",
                "evidence_status": "not_applicable",
                "subject_zh": None,
                "antecedent_zh": None,
                "evidence_index": None,
            },
            "typed_changes": [{
                "change": "addition",
                "operation": "parallelism",
                "source_zh": None,
                "restructured_zh": "要",
                "evidence_status": "explicit",
                "basis_zh": "慈悲",
                "evidence_index": 0,
            }],
        }]
    }
    artifact = semantic_bridge.hydrate_proposal(project, proposal)
    write(project, artifact)
    with pytest.raises(StrategyT1Error, match="does not encode shared-constituent placement"):
        semantic_bridge.validate_project(project)

def test_analysis_must_be_complete_ordered_and_fresh(tmp_path):
    project, artifact = project_fixture(tmp_path)
    analysis_path = project / semantic_bridge.ANALYSIS_NAME
    original = json.loads(analysis_path.read_text())
    for mutate, message in (
        (lambda value: value["paragraphs"].pop(), "cover every nonblank"),
        (lambda value: value["paragraphs"].reverse(), "cover every nonblank"),
        (lambda value: value.__setitem__("source_sha256", "0" * 64), "source_sha256 is stale"),
        (lambda value: value["paragraphs"][1].__setitem__("line_sha256", "0" * 64), "line_sha256 mismatch"),
    ):
        changed = copy.deepcopy(original)
        mutate(changed)
        analysis_path.write_text(json.dumps(changed, ensure_ascii=False) + "\n")
        with pytest.raises(StrategyT1Error, match=message):
            semantic_bridge.validate_project(project)
    analysis_path.write_text(json.dumps(original, ensure_ascii=False) + "\n")
    write(project, artifact)
def test_analysis_without_paragraph_line_hash_uses_frozen_source_order(tmp_path):
    project, artifact = project_fixture(tmp_path)
    proposal_record = {
        key: copy.deepcopy(value) for key, value in artifact["records"][0].items()
        if key in semantic_bridge.PROPOSAL_RECORD_FIELDS
    }
    for evidence in proposal_record["analysis_evidence"]:
        evidence.pop("source_analysis_value_sha256")
    path = project / semantic_bridge.ANALYSIS_NAME
    analysis = json.loads(path.read_text())
    for paragraph in analysis["paragraphs"]:
        paragraph.pop("line_sha256")
    path.write_text(json.dumps(analysis, ensure_ascii=False) + "\n")
    hydrated = semantic_bridge.hydrate_proposal(project, {"records": [proposal_record]})
    write(project, hydrated)
    report = semantic_bridge.validate_project(project)
    assert report["analysis_line_hash_mode"] == "derived_from_frozen_source_and_order"
    assert hydrated["records"][0]["source_line_sha256"] == semantic_bridge.line_hash(
        hydrated["records"][0]["source_excerpt"]
    )

def test_l1_and_l001_are_compatible_but_duplicates_are_not(tmp_path):
    project, _ = project_fixture(tmp_path)
    analysis_path = project / semantic_bridge.ANALYSIS_NAME
    analysis = json.loads(analysis_path.read_text())
    analysis["paragraphs"][0]["paragraph_id"] = "L1"
    analysis["paragraphs"][1]["paragraph_id"] = "L3"
    analysis_path.write_text(json.dumps(analysis, ensure_ascii=False) + "\n")
    artifact = semantic_bridge.fixture_artifact(project)
    assert semantic_bridge.validate_project(project)["status"] == "PASS"
    analysis = json.loads(analysis_path.read_text())
    analysis["paragraphs"][1]["paragraph_id"] = "L003"
    analysis["paragraphs"][0]["paragraph_id"] = "L0003"
    analysis_path.write_text(json.dumps(analysis, ensure_ascii=False) + "\n")
    with pytest.raises(StrategyT1Error, match="duplicate|cover every"):
        semantic_bridge.validate_project(project)
    write(project, artifact)

@pytest.mark.parametrize(
    ("mutate", "message"),
    (
        (lambda record: record["analysis_evidence"][0].__setitem__("exact_quote", "不存在的引文"), "not verbatim"),
        (lambda record: record["analysis_evidence"][0].__setitem__("source_analysis_value_sha256", "0" * 64), "value hash mismatch"),
        (lambda record: record.__setitem__("source_analysis_record_sha256", "0" * 64), "record hash mismatch"),
        (lambda record: record.__setitem__("source_analysis_fields_used", ["must_preserve"]), "do not match bound evidence"),
    ),
)
def test_analysis_evidence_is_exactly_bound(tmp_path, mutate, message):
    project, artifact = project_fixture(tmp_path)
    changed = copy.deepcopy(artifact)
    mutate(changed["records"][0])
    write(project, changed)
    with pytest.raises(StrategyT1Error, match=message):
        semantic_bridge.validate_project(project)

@pytest.mark.parametrize(
    ("mutate", "message"),
    (
        (lambda value: value["records"][0].__setitem__("source_excerpt", "错行"), "source_excerpt mismatch"),
        (lambda value: value["records"][0].__setitem__("source_line_sha256", "0" * 64), "source_line_sha256 mismatch"),
        (lambda value: value["records"][0].__setitem__("paragraph_id", "L999"), "unknown source line"),
        (lambda value: value["records"].append(copy.deepcopy(value["records"][0])), "duplicate selected"),
        (lambda value: value["records"][0].__setitem__("restructured_zh", ""), "nonempty string"),
    ),
)
def test_selected_records_are_exact_nonempty_unique_source_bindings(
    tmp_path, mutate, message
):
    project, artifact = project_fixture(tmp_path)
    changed = copy.deepcopy(artifact)
    mutate(changed)
    changed["selected_line_count"] = len(changed["records"])
    write(project, changed)
    with pytest.raises(StrategyT1Error, match=message):
        semantic_bridge.validate_project(project)

def test_ambiguous_subject_requires_impersonal_or_preserved_ambiguity(tmp_path):
    project, artifact = project_fixture(tmp_path)
    record = artifact["records"][0]
    assert record["subject_strategy"]["evidence_status"] == "ambiguous"
    changed = copy.deepcopy(artifact)
    changed["records"][0]["subject_strategy"].update(
        {"subject_zh": "我们", "antecedent_zh": "我们"}
    )
    write(project, changed)
    with pytest.raises(StrategyT1Error, match="must not invent"):
        semantic_bridge.validate_project(project)
    changed = copy.deepcopy(artifact)
    changed["records"][0]["restructuring_operations"].remove("passive_or_impersonal")
    write(project, changed)
    with pytest.raises(StrategyT1Error, match="requires passive_or_impersonal"):
        semantic_bridge.validate_project(project)

def test_explicit_subject_must_be_current_and_contextual_subject_upstream():
    evidence = [
        {
            "kind": "subject",
            "source_analysis_field": "roles",
            "source_analysis_value_sha256": "0" * 64,
            "exact_quote": "佛陀为说法者；修行者承接前文",
        }
    ]
    semantic_bridge.validate_subject_strategy(
        {
            "mode": "explicit_source_subject",
            "evidence_status": "explicit",
            "subject_zh": "佛陀",
            "antecedent_zh": None,
            "evidence_index": 0,
        },
        evidence,
        "佛陀开示正法。",
        "佛陀开示正法。",
        "",
        ["split_sentence"],
        "L1",
    )
    with pytest.raises(StrategyT1Error, match="current source"):
        semantic_bridge.validate_subject_strategy(
            {
                "mode": "explicit_source_subject",
                "evidence_status": "explicit",
                "subject_zh": "我们",
                "antecedent_zh": None,
                "evidence_index": 0,
            },
            evidence,
            "佛陀开示正法。",
            "我们聆听正法。",
            "",
            ["explicit_subject"],
            "L1",
        )
    semantic_bridge.validate_subject_strategy(
        {
            "mode": "contextual_subject",
            "evidence_status": "contextual_inference",
            "subject_zh": "修行者",
            "antecedent_zh": "修行者应观察自心",
            "evidence_index": 0,
        },
        evidence,
        "若起烦恼，就应觉察。",
        "若修行者起烦恼，就应觉察。",
        "修行者应观察自心。",
        ["explicit_subject"],
        "L2",
    )
    with pytest.raises(StrategyT1Error, match="upstream antecedent"):
        semantic_bridge.validate_subject_strategy(
            {
                "mode": "contextual_subject",
                "evidence_status": "contextual_inference",
                "subject_zh": "修行者",
                "antecedent_zh": "并不存在的承接句",
                "evidence_index": 0,
            },
            evidence,
            "若起烦恼，就应觉察。",
            "若修行者起烦恼，就应觉察。",
            "修行者应观察自心。",
            ["explicit_subject"],
            "L2",
        )

def test_local_role_gate_blocks_object_as_contextual_subject():
    evidence = [{
        "kind": "subject",
        "source_analysis_field": "roles",
        "source_analysis_value_sha256": "0" * 64,
        "exact_quote": "菩萨为行动者；众生为救度对象",
    }]
    with pytest.raises(StrategyT1Error, match="non-subject role"):
        semantic_bridge.validate_subject_strategy(
            {
                "mode": "contextual_subject",
                "evidence_status": "contextual_inference",
                "subject_zh": "众生",
                "antecedent_zh": "菩萨与众生同在",
                "evidence_index": 0,
            },
            evidence,
            "救度老人。",
            "众生救度老人。",
            "菩萨与众生同在。",
            ["explicit_subject"],
            "L2",
        )

def test_local_reference_gate_blocks_negated_candidate_and_accepts_positive_one():
    quote = "他不指佛陀，而指阿难"
    evidence = [{
        "kind": "reference",
        "source_analysis_field": "references",
        "source_analysis_value_sha256": "0" * 64,
        "exact_quote": quote,
    }]
    subject = {
        "mode": "not_applicable",
        "evidence_status": "not_applicable",
        "subject_zh": None,
        "antecedent_zh": None,
        "evidence_index": None,
    }
    base = {
        "change": "replacement",
        "operation": "explicit_reference",
        "source_zh": "他",
        "restructured_zh": "佛陀",
        "evidence_status": "contextual_inference",
        "basis_zh": "佛陀与阿难在座",
        "evidence_index": 0,
    }
    with pytest.raises(StrategyT1Error, match="negates"):
        semantic_bridge.validate_typed_changes(
            [base], evidence, subject, "他应修行。", "佛陀应修行。",
            "佛陀与阿难在座。", ["explicit_reference"], "L2"
        )
    accepted = copy.deepcopy(base)
    accepted["restructured_zh"] = "阿难"
    semantic_bridge.validate_typed_changes(
        [accepted], evidence, subject, "他应修行。", "阿难应修行。",
        "佛陀与阿难在座。", ["explicit_reference"], "L2"
    )
    erroneous = copy.deepcopy(evidence)
    erroneous[0]["exact_quote"] = "他指阿难的判断错误"
    with pytest.raises(StrategyT1Error, match="authorization marker"):
        semantic_bridge.validate_typed_changes(
            [accepted], erroneous, subject, "他应修行。", "阿难应修行。",
            "佛陀与阿难在座。", ["explicit_reference"], "L2"
        )

def test_reference_replacement_requires_one_complete_maximal_overt_form():
    evidence = [{
        "kind": "reference",
        "source_analysis_field": "references",
        "source_analysis_value_sha256": "0" * 64,
        "exact_quote": "“他”指代“佛陀”",
    }]
    subject = {
        "mode": "not_applicable",
        "evidence_status": "not_applicable",
        "subject_zh": None,
        "antecedent_zh": None,
        "evidence_index": None,
    }
    base = {
        "change": "replacement",
        "operation": "explicit_reference",
        "source_zh": "他",
        "restructured_zh": "佛陀",
        "evidence_status": "contextual_inference",
        "basis_zh": "佛陀入座",
        "evidence_index": 0,
    }
    for source, target, old in (
        ("他看见他。", "他看见佛陀。", "他"),
        ("他们开始说法。", "佛陀们开始说法。", "他"),
        ("他\u200b们开始说法。", "佛陀\u200b们开始说法。", "他"),
        ("他\u200d们开始说法。", "佛陀\u200d们开始说法。", "他"),
        ("他\ufe0f们开始说法。", "佛陀\ufe0f们开始说法。", "他"),
        ("其中有疑问。", "佛陀中有疑问。", "其"),
    ):
        change = dict(base, source_zh=old)
        with pytest.raises(StrategyT1Error, match="unique complete maximal"):
            semantic_bridge.validate_typed_changes(
                [change], evidence, subject, source, target, "佛陀入座。",
                ["explicit_reference"], "L2"
            )

def test_zero_reference_cannot_bypass_subject_strategy_in_full_artifact(tmp_path):
    project = tmp_path
    metadata = project / semantic_bridge.PROJECT_NAME
    metadata.write_text("project_id: zero-reference-regression\n", encoding="utf-8")
    source = project / "source.dj"
    source.write_text("佛陀受到供养。\n应当修行。\n", encoding="utf-8")
    term_map = project / semantic_bridge.TERM_MAP_NAME
    term_map.write_text(
        '{"terms": [{"source": "佛陀", "preferred": "the Buddha"}]}\n',
        encoding="utf-8",
    )
    source_sha, rows, _ = semantic_bridge.source_index(source)
    analysis = {
        "schema_version": 1,
        "source_sha256": source_sha,
        "translation_project_sha256": semantic_bridge.sha256_file(metadata),
        "term_map_sha256": semantic_bridge.sha256_file(term_map),
        "paragraphs": [
            {"paragraph_id": "L1", "roles": "佛陀为受供养者"},
            {
                "paragraph_id": "L2",
                "references": "佛陀不是本句省略成分，也不是本句指代对象",
            },
        ],
    }
    (project / semantic_bridge.ANALYSIS_NAME).write_text(
        json.dumps(analysis, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    proposal = {
        "records": [
            {
                "paragraph_id": "L2",
                "analysis_evidence": [
                    {
                        "kind": "reference",
                        "source_analysis_field": "references",
                        "exact_quote": "佛陀不是本句省略成分，也不是本句指代对象",
                    }
                ],
                "restructured_zh": "佛陀应当修行。",
                "restructuring_operations": ["explicit_reference"],
                "sentence_units_zh": ["佛陀应当修行。"],
                "subject_strategy": {
                    "mode": "not_applicable",
                    "evidence_status": "not_applicable",
                    "subject_zh": None,
                    "antecedent_zh": None,
                    "evidence_index": None,
                },
                "typed_changes": [
                    {
                        "change": "addition",
                        "operation": "explicit_reference",
                        "source_zh": None,
                        "restructured_zh": "佛陀",
                        "evidence_status": "contextual_inference",
                        "basis_zh": "佛陀受到供养",
                        "evidence_index": 0,
                    }
                ],
            }
        ]
    }
    artifact = semantic_bridge.hydrate_proposal(project, proposal)
    semantic_bridge.write_artifact(project, artifact)
    with pytest.raises(StrategyT1Error, match="zero-reference additions"):
        semantic_bridge.validate_project(project)

def test_legacy_contextual_subject_uses_only_closed_complete_scalar(tmp_path):
    project = tmp_path
    metadata = project / semantic_bridge.PROJECT_NAME
    metadata.write_text("project_id: legacy-subject-compatibility\n", encoding="utf-8")
    source = project / "source.dj"
    source.write_text("佛陀入座。\n开始说法。\n", encoding="utf-8")
    term_map = project / semantic_bridge.TERM_MAP_NAME
    term_map.write_text(
        '{"terms": [{"source": "佛陀", "preferred": "the Buddha"}]}\n',
        encoding="utf-8",
    )
    source_sha, _, _ = semantic_bridge.source_index(source)
    quote = "佛陀承接前文，为“开始说法”的省略主语"
    analysis = {
        "schema_version": 1,
        "source_sha256": source_sha,
        "project_sha256": semantic_bridge.sha256_file(metadata),
        "term_map_sha256": semantic_bridge.sha256_file(term_map),
        "paragraphs": [
            {"paragraph_id": "L1", "actors_and_state_holders": "佛陀为行动者"},
            {"paragraph_id": "L2", "semantic_roles_and_references": quote},
        ],
    }
    analysis_path = project / semantic_bridge.ANALYSIS_NAME
    analysis_path.write_text(json.dumps(analysis, ensure_ascii=False) + "\n")
    proposal = {
        "records": [{
            "paragraph_id": "L2",
            "analysis_evidence": [{
                "kind": "subject",
                "source_analysis_field": "semantic_roles_and_references",
                "exact_quote": quote,
            }],
            "restructured_zh": "佛陀开始说法。",
            "restructuring_operations": ["explicit_subject"],
            "sentence_units_zh": ["佛陀开始说法。"],
            "subject_strategy": {
                "mode": "contextual_subject",
                "evidence_status": "contextual_inference",
                "subject_zh": "佛陀",
                "antecedent_zh": "佛陀入座",
                "evidence_index": 0,
            },
            "typed_changes": [{
                "change": "addition",
                "operation": "explicit_subject",
                "source_zh": None,
                "restructured_zh": "佛陀",
                "evidence_status": "contextual_inference",
                "basis_zh": "开始说法",
                "evidence_index": 0,
            }],
        }]
    }
    write(project, semantic_bridge.hydrate_proposal(project, proposal))
    assert semantic_bridge.validate_project(project)["status"] == "PASS"
    analysis["paragraphs"][1]["semantic_roles_and_references"] = (
        quote + "；但这一判断尚待确认"
    )
    proposal["records"][0]["analysis_evidence"][0]["exact_quote"] = analysis[
        "paragraphs"
    ][1]["semantic_roles_and_references"]
    analysis_path.write_text(json.dumps(analysis, ensure_ascii=False) + "\n")
    write(project, semantic_bridge.hydrate_proposal(project, proposal))
    with pytest.raises(StrategyT1Error, match="authorization marker|closed affirmative"):
        semantic_bridge.validate_project(project)

def test_complete_scalar_evidence_blocks_truncated_negative_context(tmp_path):
    project = tmp_path
    metadata = project / semantic_bridge.PROJECT_NAME
    metadata.write_text("project_id: complete-evidence-regression\n", encoding="utf-8")
    source = project / "source.dj"
    source.write_text("勤修，得乐。\n", encoding="utf-8")
    term_map = project / semantic_bridge.TERM_MAP_NAME
    term_map.write_text(
        '{"terms": [{"source": "勤修", "preferred": "practice diligently"}]}\n',
        encoding="utf-8",
    )
    source_sha, _, _ = semantic_bridge.source_index(source)
    full_evidence = "得乐为因果结果的判断不成立，本句只是并列，不是因果，不得补因此"
    analysis = {
        "schema_version": 1,
        "source_sha256": source_sha,
        "translation_project_sha256": semantic_bridge.sha256_file(metadata),
        "term_map_sha256": semantic_bridge.sha256_file(term_map),
        "paragraphs": [{"paragraph_id": "L1", "logic_and_scope": full_evidence}],
    }
    (project / semantic_bridge.ANALYSIS_NAME).write_text(
        json.dumps(analysis, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    proposal = {
        "records": [{
            "paragraph_id": "L1",
            "analysis_evidence": [{
                "kind": "logic",
                "source_analysis_field": "logic_and_scope",
                "exact_quote": "得乐为因果结果",
            }],
            "restructured_zh": "勤修，因此得乐。",
            "restructuring_operations": ["explicit_logic"],
            "sentence_units_zh": ["勤修，", "因此得乐。"],
            "subject_strategy": {
                "mode": "not_applicable",
                "evidence_status": "not_applicable",
                "subject_zh": None,
                "antecedent_zh": None,
                "evidence_index": None,
            },
            "typed_changes": [{
                "change": "addition",
                "operation": "explicit_logic",
                "source_zh": None,
                "restructured_zh": "因此",
                "evidence_status": "explicit",
                "basis_zh": "得乐",
                "evidence_index": 0,
            }],
        }]
    }
    with pytest.raises(StrategyT1Error, match="complete frozen scalar"):
        semantic_bridge.hydrate_proposal(project, proposal)
    proposal["records"][0]["analysis_evidence"][0]["exact_quote"] = full_evidence
    artifact = semantic_bridge.hydrate_proposal(project, proposal)
    semantic_bridge.write_artifact(project, artifact)
    with pytest.raises(StrategyT1Error, match="authorization marker"):
        semantic_bridge.validate_project(project)
    positive = "“勤修”为原因，“得乐”为因果结果"
    proposal["records"][0]["analysis_evidence"][0]["exact_quote"] = positive
    for nested in (
        [positive, "上述因果关系不成立"],
        {"claim": positive, "status": "上述因果关系不成立"},
    ):
        nested_analysis = copy.deepcopy(analysis)
        nested_analysis["paragraphs"][0]["logic_and_scope"] = nested
        (project / semantic_bridge.ANALYSIS_NAME).write_text(
            json.dumps(nested_analysis, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        with pytest.raises(StrategyT1Error, match="top-level string scalar"):
            semantic_bridge.hydrate_proposal(project, proposal)

def test_evidence_kind_cannot_relabel_terms_or_quotations_as_syntax():
    for kind, field in (
        ("subject", "doctrinal_and_cultural_terms"),
        ("reference", "quotations_allusions_fixed_expressions"),
    ):
        analysis = {field: "佛陀为主语；他指阿难"}
        with pytest.raises(StrategyT1Error, match="cannot be authorized"):
            semantic_bridge._evidence_from_proposal(
                {
                    "kind": kind,
                    "source_analysis_field": field,
                    "exact_quote": analysis[field],
                },
                analysis,
                "evidence",
            )

def test_term_map_uses_safe_yaml_and_test_fallback_is_explicit(monkeypatch):
    yaml_text = (
        "terms:\n"
        "  - source: 佛性\n"
        "    preferred: Buddha-nature\n"
        "  - source: 缘起\n"
        "    preferred: dependent arising\n"
    )
    try:
        import yaml  # noqa: F401
    except ImportError:
        with pytest.raises(StrategyT1Error, match="requires Python PyYAML"):
            semantic_bridge.term_map_keys(yaml_text)
    else:
        assert semantic_bridge.term_map_keys(yaml_text) == {"佛性", "缘起"}
    real_import = builtins.__import__
    def no_yaml(name, *args, **kwargs):
        if name == "yaml":
            raise ImportError("test")
        return real_import(name, *args, **kwargs)
    monkeypatch.setattr(builtins, "__import__", no_yaml)
    assert semantic_bridge.term_map_keys(
        yaml_text, allow_restricted_fallback=True
    ) == {"佛性", "缘起"}
    with pytest.raises(StrategyT1Error, match="PyYAML"):
        semantic_bridge.term_map_keys("doctrine:\n  佛性: Buddha-nature\n")

def test_protected_buddhist_terms_are_derived_and_exact_counted(tmp_path):
    project, artifact = project_fixture(tmp_path)
    expected = {"空", "无自性", "缘起", "受", "心", "心所", "能缘", "所缘"}
    assert set(artifact["records"][0]["protected_terms"]) == expected
    changed = copy.deepcopy(artifact)
    changed["records"][0]["protected_terms"].remove("空")
    write(project, changed)
    with pytest.raises(StrategyT1Error, match="protected_terms"):
        semantic_bridge.validate_project(project)
    changed = record_with_text(
        artifact, artifact["records"][0]["restructured_zh"].replace("无自性", "固定本质")
    )
    write(project, changed)
    with pytest.raises(StrategyT1Error, match="Unicode lexical|protected term"):
        semantic_bridge.validate_project(project)

@pytest.mark.parametrize(
    ("source", "changed", "message"),
    (
        ("每天修习3次。", "每天修习30次。", "numeric"),
        ("修习 śamatha 与 vipaśyanā。", "修习 samatha 与 vipaśyanā。", "Latin/Sanskrit"),
        ("诵读 धर्म。", "诵读 धम्म。", "Sanskrit"),
        ("见 https://example.org/a。", "见 https://example.org/b。", "URL"),
        ("为何修行？", "为何修行。", "question/emphasis"),
        ("佛说：“应如实知。”", "佛说：应如实知。", "quotation"),
        ("空（śūnyatā）", "空（śūnyatā）（一般心理）", "brackets"),
        ("# *标题*", "## 标题", "Markdown/emphasis"),
    ),
)
def test_surface_tokens_and_rhetoric_are_invariant(source, changed, message):
    with pytest.raises(StrategyT1Error, match=message):
        semantic_bridge.validate_surface_invariants(source, changed, "L1")

def test_unaccounted_cjk_addition_omission_and_subject_object_swap_block():
    for source, target in (
        ("只有这样才可以修行。", "只有这样可以修行。"),
        ("正念帮助我们观察身心。", "正念帮助身心观察我们。"),
        ("这是修行的次第。", "这是修行次第。"),
    ):
        with pytest.raises(StrategyT1Error, match="Unicode lexical|lexical order"):
            semantic_bridge.validate_lexical_conservation(
                source, target, [], ["split_sentence"], "L1"
            )

def test_reorder_only_moves_complete_clause_units():
    semantic_bridge.validate_lexical_conservation(
        "先观察自心；再处理境界。",
        "再处理境界。先观察自心；",
        [],
        ["reorder"],
        "L1",
    )
    with pytest.raises(StrategyT1Error, match="punctuation-bound clauses"):
        semantic_bridge.validate_lexical_conservation(
            "正念帮助我们观察身心。",
            "正念帮助身心观察我们。",
            [],
            ["reorder"],
            "L1",
        )

def test_sentence_units_logic_negation_and_new_brackets_are_mechanical_gates():
    with pytest.raises(StrategyT1Error, match="do not reconstruct"):
        semantic_bridge.validate_sentence_units(["若观察。"], "若观察，就明白。", "L1")
    with pytest.raises(StrategyT1Error, match="negation"):
        semantic_bridge.validate_visible_logic_and_negation(
            "不可执著。", "可以执著。", [], "L1"
        )
    with pytest.raises(StrategyT1Error, match="relation|logic"):
        semantic_bridge.validate_visible_logic_and_negation(
            "若观察，就明白。", "就观察，若明白。", [], "L1"
        )
    with pytest.raises(StrategyT1Error, match="brackets"):
        semantic_bridge.validate_surface_invariants("缘起", "缘起（即因果）", "L1")

def test_typed_changes_cannot_self_authorize_logic_roles_or_whole_clause_copy():
    evidence = [
        {
            "kind": "logic",
            "source_analysis_field": "logic_and_scope",
            "source_analysis_value_sha256": "0" * 64,
            "exact_quote": "“勤修”与“得乐”只是并列，不是因果，不得补因此",
        },
        {
            "kind": "reference",
            "source_analysis_field": "references",
            "source_analysis_value_sha256": "0" * 64,
            "exact_quote": "只和佛陀都在分析字段中",
        },
        {
            "kind": "structure",
            "source_analysis_field": "parallelism",
            "source_analysis_value_sha256": "0" * 64,
            "exact_quote": "菩萨救度众生",
        },
        {
            "kind": "subject",
            "source_analysis_field": "roles",
            "source_analysis_value_sha256": "0" * 64,
            "exact_quote": "佛陀为当前行显式主语",
        },
    ]
    subject = {
        "mode": "not_applicable",
        "evidence_status": "not_applicable",
        "subject_zh": None,
        "antecedent_zh": None,
        "evidence_index": None,
    }
    logic = {
        "change": "addition",
        "operation": "explicit_logic",
        "source_zh": None,
        "restructured_zh": "因此",
        "evidence_status": "explicit",
        "basis_zh": "得乐",
        "evidence_index": 0,
    }
    with pytest.raises(StrategyT1Error, match="negates|locally authorize"):
        semantic_bridge.validate_typed_changes(
            [logic], evidence, subject, "勤修，得乐。", "勤修，因此得乐。", "",
            ["explicit_logic"], "L1"
        )
    reference = {
        "change": "replacement",
        "operation": "explicit_reference",
        "source_zh": "只",
        "restructured_zh": "佛陀",
        "evidence_status": "explicit",
        "basis_zh": "佛陀",
        "evidence_index": 1,
    }
    with pytest.raises(StrategyT1Error, match="controlled reference form"):
        semantic_bridge.validate_typed_changes(
            [reference], evidence, subject, "只让佛陀修行。", "佛陀让佛陀修行。", "",
            ["explicit_reference"], "L1"
        )
    parallel = {
        "change": "addition",
        "operation": "parallelism",
        "source_zh": None,
        "restructured_zh": "菩萨救度众生",
        "evidence_status": "explicit",
        "basis_zh": "众生",
        "evidence_index": 2,
    }
    with pytest.raises(
        StrategyT1Error,
        match="non-authorizing|positive parallel|exact quoted|closed affirmative",
    ):
        semantic_bridge.validate_typed_changes(
            [parallel], evidence, subject, "菩萨救度众生。", "菩萨救度众生菩萨救度众生。", "",
            ["parallelism"], "L1"
        )
    explicit = {
        "mode": "explicit_source_subject",
        "evidence_status": "explicit",
        "subject_zh": "佛陀",
        "antecedent_zh": None,
        "evidence_index": 3,
    }
    duplicate = {
        "change": "addition",
        "operation": "explicit_subject",
        "source_zh": None,
        "restructured_zh": "佛陀",
        "evidence_status": "explicit",
        "basis_zh": "佛陀",
        "evidence_index": 3,
    }
    with pytest.raises(StrategyT1Error, match="bound subject"):
        semantic_bridge.validate_typed_changes(
            [duplicate], evidence, explicit, "佛陀说法。", "佛陀佛陀说法。", "",
            ["explicit_subject"], "L1"
        )

def test_controlled_logic_addition_requires_exact_positive_role_and_placement():
    subject = {
        "mode": "not_applicable",
        "evidence_status": "not_applicable",
        "subject_zh": None,
        "antecedent_zh": None,
        "evidence_index": None,
    }
    evidence = [{
        "kind": "logic",
        "source_analysis_field": "logic_and_scope",
        "source_analysis_value_sha256": "0" * 64,
        "exact_quote": "“勤修”为原因，“得乐”为因果结果",
    }]
    change = {
        "change": "addition",
        "operation": "explicit_logic",
        "source_zh": None,
        "restructured_zh": "因此",
        "evidence_status": "explicit",
        "basis_zh": "得乐",
        "evidence_index": 0,
    }
    semantic_bridge.validate_typed_changes(
        [change], evidence, subject, "勤修，得乐。", "勤修，因此得乐。", "",
        ["explicit_logic"], "L1"
    )
    semantic_bridge.validate_lexical_conservation(
        "勤修，得乐。", "勤修，因此得乐。", [change], ["explicit_logic"], "L1"
    )
    semantic_bridge.validate_visible_logic_and_negation(
        "勤修，得乐。", "勤修，因此得乐。", [change], "L1"
    )
    for quote, message in (
        ("“勤修”与“得乐”只是并列，不是因果；不得补因此", "negates"),
        ("“得乐”为原因，“勤修”为因果结果", "closed affirmative"),
    ):
        rejected = copy.deepcopy(evidence)
        rejected[0]["exact_quote"] = quote
        with pytest.raises(StrategyT1Error, match=message):
            semantic_bridge.validate_typed_changes(
                [change], rejected, subject, "勤修，得乐。", "勤修，因此得乐。", "",
                ["explicit_logic"], "L1"
            )
    conditional = dict(change, restructured_zh="则")
    with pytest.raises(StrategyT1Error, match="source role|conditional_result"):
        semantic_bridge.validate_typed_changes(
            [conditional], evidence, subject, "勤修，得乐。", "勤修，则得乐。", "",
            ["explicit_logic"], "L1"
        )
    with pytest.raises(StrategyT1Error, match="later-clause basis"):
        semantic_bridge.validate_typed_changes(
            [dict(change, basis_zh="勤修")], evidence, subject,
            "勤修，得乐。", "因此勤修，得乐。", "", ["explicit_logic"], "L1"
        )
    with pytest.raises(StrategyT1Error, match="complete unique later-clause"):
        semantic_bridge.validate_typed_changes(
            [dict(change, basis_zh="乐")], evidence, subject,
            "勤修，得乐。", "勤修，得因此乐。", "", ["explicit_logic"], "L1"
        )
    for uncertain_quote in (
        "“勤修”为原因，“得乐”未必是因果结果",
        "“勤修”为原因，“得乐”不一定是因果结果",
        "“勤修”为原因，“得乐”并不作为因果结果",
        "“勤修”为原因，“得乐”也许是因果结果",
        "“勤修”为原因，“得乐”是因果结果？",
        "“勤修”为原因，“得乐”是因果结果吗",
        "“勤修”为原因；若“得乐”是因果结果",
        "“勤修”为原因；如果“得乐”是因果结果",
        "“勤修”为原因；假设“得乐”是因果结果",
        "“勤修”为原因，据说“得乐”是因果结果",
        "“勤修”为原因，“得乐”是因果结果或原因",
        "“勤修”为原因，“得乐”是因果结果/原因",
        "“勤修”为原因，“得乐”是因果结果尚待讨论",
        "“勤修”为原因，“得乐”为因果结果，但上述标注并不是正确的",
        "“勤修”为原因，“得乐”为因果结果；前述关系并非真实分析结论",
        "“勤修”为原因，“得乐”为因果结果；但这并非事实",
        "“勤修”为原因，“得乐”为因果结果；上述说法不是事实",
        "问：“勤修”为原因，“得乐”为因果结果",
        "在假设中，“勤修”为原因，“得乐”为因果结果",
        "二选一：“勤修”为原因，“得乐”为因果结果",
    ):
        uncertain = copy.deepcopy(evidence)
        uncertain[0]["exact_quote"] = uncertain_quote
        with pytest.raises(
            StrategyT1Error,
            match="authorization marker|positively assign|closed affirmative",
        ):
            semantic_bridge.validate_typed_changes(
                [change], uncertain, subject, "勤修，得乐。", "勤修，因此得乐。", "",
                ["explicit_logic"], "L1"
            )
    wrong_field = copy.deepcopy(evidence)
    wrong_field[0]["source_analysis_field"] = "must_not_invent"
    with pytest.raises(StrategyT1Error, match="non-authorizing"):
        semantic_bridge.validate_typed_changes(
            [change], wrong_field, subject, "勤修，得乐。", "勤修，因此得乐。", "",
            ["explicit_logic"], "L1"
        )
    for contradictory_quote, message in (
        ("“得乐”为因果结果；“勤修”不是原因", "negates"),
        ("“布施”为原因，“得乐”为因果结果", "closed affirmative"),
    ):
        contradictory = copy.deepcopy(evidence)
        contradictory[0]["exact_quote"] = contradictory_quote
        with pytest.raises(StrategyT1Error, match=message):
            semantic_bridge.validate_typed_changes(
                [change], contradictory, subject, "勤修，得乐。", "勤修，因此得乐。", "",
                ["explicit_logic"], "L1"
            )

@pytest.mark.parametrize(
    "basis",
    (
        "就得乐",
        "后来所以得乐",
        "后来所 以得乐",
        "后来所　以得乐",
        "后来所\u200b以得乐",
        "后来所\u200d以得乐",
        "后来所\ufe0f以得乐",
    ),
)
def test_legacy_logic_defers_when_target_clause_already_has_marker(basis):
    evidence = [{
        "kind": "logic",
        "source_analysis_field": "logic_and_scope",
        "source_analysis_value_sha256": "0" * 64,
        "exact_quote": f"“勤修”为原因，“{basis}”为因果结果",
    }]
    subject = {
        "mode": "not_applicable",
        "evidence_status": "not_applicable",
        "subject_zh": None,
        "antecedent_zh": None,
        "evidence_index": None,
    }
    change = {
        "change": "addition",
        "operation": "explicit_logic",
        "source_zh": None,
        "restructured_zh": "因此",
        "evidence_status": "explicit",
        "basis_zh": basis,
        "evidence_index": 0,
    }
    source = f"勤修，{basis}。"
    target = f"勤修，因此{basis}。"
    with pytest.raises(StrategyT1Error, match="already contains a visible logic marker"):
        semantic_bridge.validate_typed_changes(
            [change], evidence, subject, source, target, "",
            ["explicit_logic"], "L1"
        )

def test_structured_contrast_does_not_stack_but_before_existing_er(tmp_path):
    relation = {
        "type": "contrast",
        "source_clause": "外在结果暂时",
        "target_clause": "而心灵结果长久",
        "evidence": "外在结果暂时，而心灵结果长久",
        "evidence_status": "explicit",
        "notes": "对比。",
    }
    project, proposal = structured_logic_project(
        tmp_path,
        "外在结果暂时，而心灵结果长久。",
        [relation],
        basis="而心灵结果长久",
        target_text="外在结果暂时，但而心灵结果长久。",
    )
    record = proposal["records"][0]
    record["typed_changes"][0]["restructured_zh"] = "但"
    write(project, semantic_bridge.hydrate_proposal(project, proposal))
    with pytest.raises(StrategyT1Error, match="already contains a visible logic marker"):
        semantic_bridge.validate_project(project)

def test_controlled_parallel_completion_repeats_only_bound_shared_constituent():
    subject = {
        "mode": "not_applicable",
        "evidence_status": "not_applicable",
        "subject_zh": None,
        "antecedent_zh": None,
        "evidence_index": None,
    }
    evidence = [{
        "kind": "structure",
        "source_analysis_field": "ellipsis_or_ambiguity",
        "source_analysis_value_sha256": "0" * 64,
        "exact_quote": "两项并列；第二项“慈悲”承前省略“要”，可在“慈悲”前补“要”",
    }]
    change = {
        "change": "addition",
        "operation": "parallelism",
        "source_zh": None,
        "restructured_zh": "要",
        "evidence_status": "explicit",
        "basis_zh": "慈悲",
        "evidence_index": 0,
    }
    semantic_bridge.validate_typed_changes(
        [change], evidence, subject,
        "对自己要诚实，对他人慈悲。", "对自己要诚实，对他人要慈悲。", "",
        ["parallelism"], "L1"
    )
    semantic_bridge.validate_lexical_conservation(
        "对自己要诚实，对他人慈悲。", "对自己要诚实，对他人要慈悲。",
        [change], ["parallelism"], "L1"
    )
    semantic_bridge.validate_visible_logic_and_negation(
        "对自己要诚实，对他人慈悲。", "对自己要诚实，对他人要慈悲。",
        [change], "L1"
    )
    negative = copy.deepcopy(evidence)
    negative[0]["exact_quote"] = "两项各自完整，第二项“慈悲”并未省略“要”，不得补“要”"
    with pytest.raises(StrategyT1Error, match="negates"):
        semantic_bridge.validate_typed_changes(
            [change], negative, subject,
            "对自己要诚实，对他人慈悲。", "对自己要诚实，对他人要慈悲。", "",
            ["parallelism"], "L1"
        )
    contradictory = copy.deepcopy(evidence)
    contradictory[0]["exact_quote"] = (
        "第二项“慈悲”承前省略“要”；但“要”只支配第一项"
    )
    with pytest.raises(StrategyT1Error, match="negates"):
        semantic_bridge.validate_typed_changes(
            [change], contradictory, subject,
            "对自己要诚实，对他人慈悲。", "对自己要诚实，对他人要慈悲。", "",
            ["parallelism"], "L1"
        )
    wrong_place = dict(change, basis_zh="对自己")
    wrong_place_evidence = copy.deepcopy(evidence)
    wrong_place_evidence[0]["exact_quote"] = (
        "两项并列；第一项“对自己”承前省略“要”，可在“对自己”前补“要”"
    )
    with pytest.raises(StrategyT1Error, match="later source member"):
        semantic_bridge.validate_typed_changes(
            [wrong_place], wrong_place_evidence, subject,
            "对自己要诚实，对他人慈悲。", "要对自己要诚实，对他人慈悲。", "",
            ["parallelism"], "L1"
        )
    with pytest.raises(StrategyT1Error, match="exact quoted|closed affirmative"):
        semantic_bridge.validate_typed_changes(
            [dict(change, basis_zh="悲")], evidence, subject,
            "对自己要诚实，对他人慈悲。", "对自己要诚实，对他人慈要悲。", "",
            ["parallelism"], "L1"
        )
    for truncated_basis, target, quote in (
        (
            "悲",
            "对自己要诚实，对他人慈要悲。",
            "两项并列；第二项“慈悲”承前省略“要”；另记“悲”",
        ),
        (
            "他人",
            "对自己要诚实，对要他人慈悲。",
            "两项并列；第二项“对他人慈悲”承前省略“要”；另记“他人”",
        ),
    ):
        separated_quote = copy.deepcopy(evidence)
        separated_quote[0]["exact_quote"] = quote
        with pytest.raises(StrategyT1Error, match="positive parallel|closed affirmative"):
            semantic_bridge.validate_typed_changes(
                [dict(change, basis_zh=truncated_basis)], separated_quote, subject,
                "对自己要诚实，对他人慈悲。", target, "", ["parallelism"], "L1"
            )
    for uncertain_quote in (
        "两项并列；第二项“慈悲”未必承前省略“要”",
        "两项并列；第二项“慈悲”不一定承前省略“要”",
        "两项并列；第二项“慈悲”并不省略“要”",
        "两项并列；第二项“慈悲”也许承前省略“要”",
        "两项并列；第二项“慈悲”承前省略“要”吗？",
        "若第二项“慈悲”承前省略“要”",
        "假设第二项“慈悲”承前省略“要”",
        "据说第二项“慈悲”承前省略“要”",
        "第二项“慈悲”承前省略“要”或“应”",
        "第二项“慈悲”承前省略“要”尚待讨论",
        "两项并列；第二项“慈悲”并没有承前省略“要”",
        "两项并列；第二项“慈悲”承前省略“要”，可在“慈悲”前补“要”；“要”并未作用于第二项",
        "两项并列；第二项“慈悲”承前省略“要”，可在“慈悲”前补“要”；后项未由“要”修饰",
        "问：两项并列；第二项“慈悲”承前省略“要”，可在“慈悲”前补“要”",
        "在假设中，两项并列；第二项“慈悲”承前省略“要”，可在“慈悲”前补“要”",
        "二选一：两项并列；第二项“慈悲”承前省略“要”，可在“慈悲”前补“要”",
    ):
        uncertain = copy.deepcopy(evidence)
        uncertain[0]["exact_quote"] = uncertain_quote
        with pytest.raises(
            StrategyT1Error,
            match="authorization marker|negates|closed affirmative",
        ):
            semantic_bridge.validate_typed_changes(
                [change], uncertain, subject,
                "对自己要诚实，对他人慈悲。", "对自己要诚实，对他人要慈悲。", "",
                ["parallelism"], "L1"
            )
    whole_clause = dict(change, restructured_zh="对自己要诚实", basis_zh="慈悲")
    whole_evidence = copy.deepcopy(evidence)
    whole_evidence[0]["exact_quote"] = (
        "两项并列；第二项“慈悲”承前省略“对自己要诚实”，"
        "可在“慈悲”前补“对自己要诚实”"
    )
    with pytest.raises(StrategyT1Error, match="complete source clause"):
        semantic_bridge.validate_typed_changes(
            [whole_clause], whole_evidence, subject,
            "对自己要诚实，对他人慈悲。", "对自己要诚实，对他人对自己要诚实慈悲。", "",
            ["parallelism"], "L1"
        )

def test_unicode_and_limiter_conservation_close_non_cjk_bypasses():
    with pytest.raises(StrategyT1Error, match="Unicode lexical"):
        semantic_bridge.validate_lexical_conservation(
            "修行。", "修行🙂。", [], ["split_sentence"], "L1"
        )
    with pytest.raises(StrategyT1Error, match="limiter"):
        semantic_bridge.validate_visible_logic_and_negation(
            "只让佛陀修行。", "佛陀让佛陀修行。", [], "L1"
        )

def test_false_or_unapproved_semantic_claim_fields_are_rejected(tmp_path):
    project, artifact = project_fixture(tmp_path)
    for field, value in (
        ("restructuring_checks", {"no_new_information": True}),
        ("meaning_explication_zh", "这是二次法义解释"),
        ("propositions", ["模型新命题"]),
    ):
        changed = copy.deepcopy(artifact)
        changed["records"][0][field] = value
        write(project, changed)
        with pytest.raises(StrategyT1Error, match="unapproved fields"):
            semantic_bridge.validate_project(project)

def test_invalid_provenance_empty_selection_and_decision_hash_block(tmp_path):
    project, artifact = project_fixture(tmp_path)
    for generated in (None, "gpt-5.6-sol", {"provider": "openai-codex"}):
        changed = copy.deepcopy(artifact)
        changed["generated_by"] = generated
        write(project, changed)
        with pytest.raises(StrategyT1Error, match="generated_by|locked Sol"):
            semantic_bridge.validate_project(project)
    changed = copy.deepcopy(artifact)
    changed["records"] = []
    changed["selected_line_count"] = 0
    write(project, changed)
    with pytest.raises(StrategyT1Error, match="at least one selected"):
        semantic_bridge.validate_project(project)
    write(project, artifact)
    with pytest.raises(StrategyT1Error, match="accepted_decisions"):
        semantic_bridge.validate_project(
            project, expected_accepted_decisions_sha256="0" * 64
        )
    changed = copy.deepcopy(artifact)
    changed["accepted_decisions_sha256"] = "1" * 64
    write(project, changed)
    with pytest.raises(StrategyT1Error, match="accepted_decisions"):
        semantic_bridge.validate_project(
            project, expected_accepted_decisions_sha256=None
        )

def test_length_ratio_warning_is_nonblocking():
    warning = semantic_bridge.length_warning(
        "L1", "短句", "这是一个明显更长且只用于比例诊断的句子"
    )
    assert warning and warning["blocking"] is False
    assert warning["advisory_band"] == [0.90, 1.15]

def test_contract_suite_and_legacy_validator(tmp_path):
    try:
        import yaml  # noqa: F401
    except ImportError:
        with pytest.raises(StrategyT1Error, match="requires Python PyYAML"):
            semantic_bridge.run_contract_tests(tmp_path / "report")
    else:
        result = semantic_bridge.run_contract_tests(tmp_path / "report")
        assert result["status"] == "PASS"
        assert result["mechanical_scope_only"] is True
    legacy = tmp_path / "legacy-separate"
    legacy.mkdir()
    records = semantic_bridge_legacy.fixture_records(legacy)
    for name, values in records.items():
        semantic_bridge_legacy.write_jsonl(legacy / name, values)
    direct = semantic_bridge_legacy.validate_project(legacy)
    delegated = semantic_bridge.validate_legacy_project(legacy)
    for key, value in direct.items():
        assert delegated[key] == value
    assert delegated["legacy_workflow_version"] == "1.1.1"
    assert delegated["read_only"] is True

def test_real_legacy_project_remains_readable_if_present():
    project = Path(
        "/Users/jingzhi/puti/mpi-translations/translation-results/"
        "lesson-57-buddhist-ethics-t11-two-page-dualtrack-20260824"
    )
    if not project.is_dir():
        pytest.skip("local retained T1.1.1 fixture is unavailable")
    before = {
        path.name: hashlib.sha256(path.read_bytes()).hexdigest()
        for path in project.iterdir()
        if path.is_file()
    }
    assert semantic_bridge.validate_legacy_project(project)["read_only"] is True
    after = {
        path.name: hashlib.sha256(path.read_bytes()).hexdigest()
        for path in project.iterdir()
        if path.is_file()
    }
    assert after == before
