"""DS-only installation never requires OMP OpenAI or legacy readiness."""
import importlib.util
import json
from pathlib import Path
import pytest

PACKAGE = Path(__file__).parents[1] / 'skills/mpi-strategy-t1-codex'
def load(name):
    spec = importlib.util.spec_from_file_location(name, PACKAGE / 'scripts' / (name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
runtime = load('install_runtime')
adapter = load('provider_runtime')


def fixture(tmp_path, monkeypatch):
    (tmp_path / 'MANIFEST.sha256').write_text('base fixture', encoding='utf-8')
    monkeypatch.setattr(runtime, 'verify_base_package', lambda p: {})
    monkeypatch.setattr(runtime, 'missing_dependencies', lambda: [])
    monkeypatch.setattr(runtime.shutil, 'which', lambda n: '/bin/omp')
    monkeypatch.setattr(runtime, 'omp_version', lambda p: '17.3.4')
    monkeypatch.setattr(runtime, 'credential_present', lambda p: True)
    monkeypatch.setattr(runtime, 'managed_root', lambda: tmp_path)
    monkeypatch.setattr(runtime, 'run_interactive', lambda *a: pytest.fail('no login or interaction required'))
    def run_json(command, cwd):
        assert command[-1] == 'scripts/validate_package.py'
        return {'status': 'PASS', 'manifest': {'sha256': 'a'*64}}
    monkeypatch.setattr(runtime, 'run_json', run_json)
    def checks(base, root, evidence, **kwargs):
        result = {'status': 'PASS'}
        for name in ['fault', 'smoke']:
            f = evidence / (name + '.json'); f.write_text('{"status":"PASS"}', encoding='utf-8')
            result[name] = {'status': 'PASS', 'path': str(f), 'sha256': runtime.sha256_file(f)}
        return result
    monkeypatch.setattr(runtime, 'provider_checks', checks)


@pytest.mark.parametrize('revalidate', [False, True])
def test_no_openai_or_legacy_ready_needed(tmp_path, monkeypatch, revalidate):
    fixture(tmp_path, monkeypatch)
    result = runtime.provision(tmp_path, revalidate=revalidate, confirm_public_smoke=True)
    assert result['runtime_profile'] == 'deepseek-only-v1'
    assert result['provider_runtime_ready'] and result['base_ready_used'] is False
    assert result['gpt_smoke_required'] is False
    assert result['codex_task_setting_still_requires_direct_verification'] is True
    assert not (tmp_path / 'READY.json').exists()


@pytest.mark.parametrize('failure', ['smoke', 'fault', 'exception'])
def test_failure_invalidates_current_ready_but_preserves_history(tmp_path, monkeypatch, failure):
    fixture(tmp_path, monkeypatch)
    path = tmp_path / runtime.READY_NAME
    path.write_text('{"runtime_ready":true,"old":true}', encoding='utf-8')
    before = path.read_bytes()
    original = runtime.provider_checks
    def fail(*args, **kwargs):
        if failure == 'exception': raise runtime.RuntimeInstallError('doctor failed')
        result = original(*args, **kwargs)
        Path(result[failure]['path']).write_text('tampered', encoding='utf-8')
        return result
    monkeypatch.setattr(runtime, 'provider_checks', fail)
    with pytest.raises(runtime.RuntimeInstallError):
        runtime.provision(tmp_path, revalidate=True, confirm_public_smoke=True)
    assert json.loads(path.read_text())['runtime_ready'] is False
    assert list((tmp_path/'attempts').glob('*/previous-runtime-ready.json'))[0].read_bytes() == before


def test_requires_explicit_smoke_authorization(tmp_path, monkeypatch):
    fixture(tmp_path, monkeypatch)
    with pytest.raises(runtime.RuntimeInstallError, match='confirm-public-smoke'):
        runtime.revalidate_existing_runtime(tmp_path, confirm_public_smoke=False)


def test_missing_credential_blocks_unattended_run(tmp_path, monkeypatch):
    fixture(tmp_path, monkeypatch)
    monkeypatch.setattr(runtime, 'credential_present', lambda p: False)
    with pytest.raises(runtime.RuntimeInstallError, match='credential missing'):
        runtime.revalidate_existing_runtime(tmp_path, confirm_public_smoke=True)


def test_ds_profile_filters_gpt_without_mutating_frozen_lock():
    base = {'models': {'source_analysis': {'provider':'deepseek'}, 'bilingual_review': {'provider':'deepseek'}, 'translation_and_self_review': {'provider':'openai-codex'}}, 'smoke_policy': {'markers': {'source_analysis':'FLASH','bilingual_review':'PRO','translation_and_self_review':'GPT'}}}
    profile = adapter.ds_lock(base)
    assert set(profile['models']) == set(profile['smoke_policy']['markers']) == {'source_analysis','bilingual_review'}
    assert 'translation_and_self_review' in base['models']


def test_root_separate_from_legacy(monkeypatch):
    monkeypatch.delenv('MPI_STRATEGY_T1_CODEX_ROOT', raising=False)
    monkeypatch.setenv('MPI_STRATEGY_T1_ROOT', '/legacy-do-not-use')
    assert 'legacy-do-not-use' not in str(runtime.managed_root())
