import hashlib
import importlib.util
import json
from pathlib import Path

import pytest

SCRIPT=Path(__file__).parents[1]/'skills/mpi-strategy-t1-codex/scripts/install_runtime.py'
spec=importlib.util.spec_from_file_location('runtime_revalidation_test',SCRIPT)
runtime=importlib.util.module_from_spec(spec)
spec.loader.exec_module(runtime)

def fixture_runtime(tmp_path, monkeypatch):
    monkeypatch.setattr(runtime,'verify_base_package',lambda p: {})
    monkeypatch.setattr(runtime,'missing_dependencies',lambda: [])
    monkeypatch.setattr(runtime.shutil,'which',lambda n: '/bin/omp')
    monkeypatch.setattr(runtime,'omp_version',lambda p: '17.3.4')
    monkeypatch.setattr(runtime,'credential_present',lambda p: True)
    monkeypatch.setattr(runtime,'managed_root',lambda: tmp_path)
    monkeypatch.setattr(runtime,'verify_existing_workspace',lambda r,o: {'confirmed':True})
    monkeypatch.setattr(runtime,'run_interactive',lambda *a: pytest.fail('must not login or reinstall'))
    ready={'ready':True,'deepseek_credential':{'present':True},'smoke_test':{'status':'PASS'},
           'fault_injection':{'status':'PASS'},'translation_toolkit':{'absolute_path':'/locked/toolkit'}}
    (tmp_path/'READY.json').write_text(json.dumps(ready))
    old=tmp_path/runtime.READY_NAME;old.write_text('{"old_receipt":true}')
    def run_json(command,cwd):
        if 'doctor' in command:return {'ok':True,'result':ready}
        assert command[-1]=='scripts/validate_package.py'
        return {'status':'PASS','manifest':{'sha256':'a'*64}}
    monkeypatch.setattr(runtime,'run_json',run_json)
    def smoke(base,path,ready):
        f=path/'smoke-test-report.json';f.write_text('{"status":"PASS"}')
        return {'status':'PASS','report_sha256':runtime.sha256_file(f)}
    monkeypatch.setattr(runtime,'refresh_public_smoke',smoke)
    return old

def test_revalidation_without_tty_preserves_base_and_old_receipt(tmp_path,monkeypatch):
    old=fixture_runtime(tmp_path,monkeypatch)
    base_bytes=(tmp_path/'READY.json').read_bytes();old_bytes=old.read_bytes()
    result=runtime.revalidate_existing_runtime(tmp_path,confirm_public_smoke=True)
    assert result['runtime_ready'] and result['repositories_replaced'] is False
    assert (tmp_path/'READY.json').read_bytes()==base_bytes
    backups=list((tmp_path/'runtime-revalidations').glob('*/previous-runtime-ready.json'))
    assert len(backups)==1 and backups[0].read_bytes()==old_bytes
    assert json.loads(old.read_text())['public_smoke_evidence']['sha256']

@pytest.mark.parametrize('failure',['smoke','doctor','credential'])
def test_failed_revalidation_does_not_overwrite_ready(tmp_path,monkeypatch,failure):
    old=fixture_runtime(tmp_path,monkeypatch);before=old.read_bytes()
    if failure=='smoke':
        monkeypatch.setattr(runtime,'refresh_public_smoke',lambda *a:{'status':'FAIL'})
    elif failure=='doctor':
        original=runtime.run_json
        monkeypatch.setattr(runtime,'run_json',lambda c,w: {'ok':False} if 'doctor' in c else original(c,w))
    else:monkeypatch.setattr(runtime,'credential_present',lambda p: False)
    with pytest.raises(runtime.RuntimeInstallError):
        runtime.revalidate_existing_runtime(tmp_path,confirm_public_smoke=True)
    assert old.read_bytes()==before

def test_revalidation_requires_authorized_public_smoke(tmp_path):
    with pytest.raises(runtime.RuntimeInstallError,match='confirm-public-smoke'):
        runtime.revalidate_existing_runtime(tmp_path,confirm_public_smoke=False)

def test_workspace_reuse_rejects_changed_selection(tmp_path,monkeypatch):
    summary={'number':1,'plan_type':'pro','workspace_label':None,'allowed':True}
    digest=hashlib.sha256(json.dumps(summary,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    confirmation={'schema_version':2,'confirmed':True,'workspace_kind':'personal',
                  'selected_report_number':1,'selected_summary_sha256':digest}
    (tmp_path/'personal-workspace-confirmation.json').write_text(json.dumps(confirmation))
    payload={'reports':[{'provider':'openai-codex','metadata':{'allowed':True,'planType':'pro'}}]}
    monkeypatch.setattr(runtime,'run_json',lambda c,w:payload)
    assert runtime.verify_existing_workspace(tmp_path,'omp')['authentication_reused']
    payload['reports'][0]['metadata']['planType']='business'
    with pytest.raises(runtime.RuntimeInstallError,match='selection changed'):
        runtime.verify_existing_workspace(tmp_path,'omp')
