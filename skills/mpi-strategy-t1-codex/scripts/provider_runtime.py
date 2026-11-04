#!/usr/bin/env python3
"""T1-Codex DS-only adapter over verified immutable T1 repository and QA helpers."""
from __future__ import annotations
import argparse
import copy
import json
import sys
from pathlib import Path


PHASE = "initialization"


def ds_lock(base: dict) -> dict:
    result = copy.deepcopy(base)
    roles = ('source_analysis', 'bilingual_review')
    result['models'] = {role: base['models'][role] for role in roles}
    result['smoke_policy']['markers'] = {role: base['smoke_policy']['markers'][role] for role in roles}
    if any(spec['provider'] != 'deepseek' for spec in result['models'].values()):
        raise ValueError('provider runtime must contain DeepSeek roles only')
    return result


def run_checks(base: Path, root: Path, evidence: Path, revalidate=False,
               candidate_mpi=None, candidate_toolkit=None) -> dict:
    global PHASE
    PHASE = "immutable base verification"
    from install_runtime import verify_base_package
    verify_base_package(base)
    sys.path.insert(0, str(base / 'scripts'))
    from t1_runtime import (load_lock, verify_manifest, require_dependencies, omp_report,
                            sha256_file, atomic_json)
    from t1_bootstrap import prepare_repositories, repository_evidence
    from t1_fault_injection import run_fault_tests
    from t1_smoke_test import run_smoke_test
    # Verifies every byte before importing helpers which may perform mutations.
    verify_manifest()
    lock = load_lock()
    provider_lock = ds_lock(lock)
    PHASE = "dependencies and DS model catalog"
    require_dependencies(lock)
    omp = omp_report(provider_lock)
    PHASE = "locked repository preparation"
    mpi = root / 'repos' / 'mpi-translations'
    toolkit = mpi / lock['translation_toolkit']['submodule_path']
    if not mpi.exists():
        if revalidate:
            raise RuntimeError('DS-only managed repositories absent; perform initial installation')
        mpi, toolkit = prepare_repositories(root, lock, candidate_mpi, candidate_toolkit)
    PHASE = "repository identity and doctors"
    mpi_info, toolkit_info = repository_evidence(mpi, toolkit, lock)
    PHASE = "disposable fault injection"
    fault = run_fault_tests(root)
    # Move new evidence into this attempt; no legacy T1 READY is read or produced.
    fault_path = evidence / 'fault-injection-report.json'
    (root / 'fault-injection-report.json').replace(fault_path)
    PHASE = "public mechanical DOCX and DS smoke"
    smoke = run_smoke_test(evidence, toolkit, provider_lock)
    expected = set(provider_lock['models'])
    executed = smoke.get('model_executions', [])
    if len(executed) != 2 or {item['role'] for item in executed} != expected:
        raise RuntimeError('public smoke must execute exactly Flash/high and Pro/max')
    if any(item.get('provider') != 'deepseek' or item.get('exit_code') != 0 for item in executed):
        raise RuntimeError('DeepSeek smoke identity or execution mismatch')
    PHASE = "repository identity and doctors"
    mpi_info, toolkit_info = repository_evidence(mpi, toolkit, lock)
    result = {'status': 'PASS', 'runtime_profile': 'deepseek-only-v1', 'omp': omp,
              'mpi_translations': mpi_info, 'translation_toolkit': toolkit_info,
              'fault': {'status': fault['status'], 'path': str(fault_path), 'sha256': sha256_file(fault_path)},
              'smoke': {'status': smoke['status'], 'path': smoke['report_absolute_path'],
                        'sha256': smoke['report_sha256']}}
    atomic_json(evidence / 'provider-checks.json', result)
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('base', 'root', 'evidence'):
        parser.add_argument(name, type=Path)
    parser.add_argument('--revalidate-existing', action='store_true')
    parser.add_argument('--candidate-mpi', type=Path)
    parser.add_argument('--candidate-toolkit', type=Path)
    args = parser.parse_args()
    try:
        result = run_checks(args.base.resolve(), args.root.resolve(), args.evidence.resolve(),
                            args.revalidate_existing, args.candidate_mpi, args.candidate_toolkit)
    except Exception as exc:
        # Do not print provider stderr, credential values or account metadata.
        print(json.dumps({'status': 'FAIL', 'error_type': type(exc).__name__, 'stage': PHASE,
                          'error': 'provider runtime verification failed; no ready receipt issued'}))
        sys.exit(1)
    print(json.dumps(result))
