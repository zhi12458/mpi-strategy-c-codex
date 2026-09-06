"""End-to-end coverage for flexible Codex identities and unchanged evidence gates."""
import hashlib
import importlib.util
import json
from pathlib import Path

import pytest

root = Path(__file__).resolve().parents[1] / "skills" / "mpi-strategy-t1-codex"
spec = importlib.util.spec_from_file_location("model_policy_postedit", root / "scripts" / "validate_post_translation_editing.py")
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
locks = m.load_upstream_model_locks()
source = "a" * 64
target = "b" * 64
matrix = json.loads((root / "dependency-lock.json").read_text(encoding="utf-8"))["codex_model_policy"]["allowed_model_efforts"]

def baseline(project, model, effort, mutation=None):
 receipts=[]
 for stage in m.UPSTREAM_INHERITANCE_STAGES:
  lock=locks.get(stage)
  if lock:
   identity={k:lock[k] for k in ['provider','model','reasoning_effort','execution_surface']};identity.update(kind='model',role=stage,request_or_session_id='synthetic-test-session')
   if 'allowed_model_efforts' in lock:identity.update(model=model,reasoning_effort=effort)
  else:identity={'kind':'tool','tool_name':'fixture','tool_version':'1','command_or_config_sha256':'c'*64}
  artifact={'schema_version':1,'gate':'t1_codex_upstream_completion','stage':stage,'source_sha256':source,'target_sha256':target,'scope':'full_document','status':'PASS','complete':True,'execution_identity':identity}
  if mutation:mutation(stage,artifact)
  p=project/(stage+'.json');p.write_text(json.dumps(artifact), encoding="utf-8");receipts.append({'stage':stage,'artifact':p.name,'artifact_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'source_sha256':source,'baseline_target_sha256':target,'scope':'full_document','status':'PASS','role_or_tool_identity_matches_recorded_configuration':True,'reused_without_rerun':True})
 return {'upstream_reuse_receipts':receipts}

@pytest.mark.parametrize("model,effort", [(model, effort) for model, efforts in matrix.items() for effort in efforts])
def test_allowed_identity_preserves_full_upstream_validation(tmp_path, model, effort):
    data = baseline(tmp_path, model, effort)
    m.validate_upstream_reuse(tmp_path, data, source_hash=source, baseline_hash=target)

@pytest.mark.parametrize("model,effort", [
    ("gpt-5.5", "high"), ("gpt-7", "high"), ("gpt-6-astra", "none"),
    ("gpt-5.6-luna", "ultra"), ("gpt-6-astra", "bogus"),
    ("runtime-selected-gpt-5.6-or-gpt-6", "runtime-supported"), ("", "high")])
def test_reject_unsupported_or_missing_actual_identity(tmp_path, model, effort):
    data = baseline(tmp_path, model, effort)
    with pytest.raises(m.PostTranslationEditingError, match="model or reasoning effort"):
        m.validate_upstream_reuse(tmp_path, data, source_hash=source, baseline_hash=target)

@pytest.mark.parametrize("stage,field,value,identity", [
    ("translation_and_self_review", "provider", "fake", True),
    ("translation_and_self_review", "request_or_session_id", "", True),
    ("translation_and_self_review", "source_sha256", "d" * 64, False),
    ("bilingual_review_round_1", "reasoning_effort", "low", True),
    ("source_analysis", "model", "gpt-6-astra", True),
])
def test_flexible_codex_policy_keeps_other_gates(tmp_path, stage, field, value, identity):
    def mutate(current, artifact):
        if current == stage:
            destination = artifact["execution_identity"] if identity else artifact
            destination[field] = value
    data = baseline(tmp_path, "gpt-6-astra", "high", mutate)
    with pytest.raises(m.PostTranslationEditingError):
        m.validate_upstream_reuse(tmp_path, data, source_hash=source, baseline_hash=target)
