"""Remove requirements with a fresh manifest so policy, not stale hashes, rejects them."""
import hashlib
import importlib.util
import json
import shutil
from pathlib import Path

import pytest

PACKAGE = Path(__file__).parents[1] / 'skills/mpi-strategy-t1-codex'
spec = importlib.util.spec_from_file_location('verb_led_validator', PACKAGE / 'scripts/validate_package.py')
validator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(validator)


def leaves(value, path=()):
    if isinstance(value, dict):
        for key, item in value.items():
            yield from leaves(item, path + (key,))
    elif isinstance(value, list):
        for index in range(len(value)):
            yield path + (index,)
    else:
        yield path


def manifest(root):
    files = sorted(p for p in root.rglob('*') if p.is_file() and p.name != 'MANIFEST.sha256'
                   and '__pycache__' not in p.parts and p.suffix != '.pyc')
    (root / 'MANIFEST.sha256').write_text(''.join(
        hashlib.sha256(p.read_bytes()).hexdigest() + '  ' + p.relative_to(root).as_posix() + '\n'
        for p in files), encoding='utf-8')


@pytest.mark.parametrize('lock', ['dependency-lock.json', 'references/production-lock.json'])
@pytest.mark.parametrize('path', list(leaves(validator.VERB_LED_REQUIRED)))
def test_missing_contract_requirement(tmp_path, lock, path):
    root = tmp_path / 'package'
    shutil.copytree(PACKAGE, root)
    file = root / lock
    obj = json.loads(file.read_text(encoding='utf-8'))
    node = obj['verb_led_english']
    for key in path[:-1]:
        node = node[key]
    del node[path[-1]]
    file.write_text(json.dumps(obj, ensure_ascii=False), encoding='utf-8')
    manifest(root)
    with pytest.raises(validator.ValidationError, match='verb-led'):
        validator.validate_package(root)


@pytest.mark.parametrize('relative,old', [
    ('SKILL.md', 'verb-led-style-review.jsonl'),
    ('references/workflow.md', 'verb-led-style-review.jsonl'),
    ('references/semantic-style-native-reader-addendum.md', 'checked_target_sha256'),
    ('references/english-only-reader-gate.md', 'Reader B'),
    ('references/production-lock.json', 'whole_document_clause_check_required'),
])
def test_missing_declaration_or_role(tmp_path, relative, old):
    root = tmp_path / 'package'
    shutil.copytree(PACKAGE, root)
    file = root / relative
    file.write_text(file.read_text(encoding='utf-8').replace(old, 'removed_requirement'), encoding='utf-8')
    manifest(root)
    with pytest.raises(validator.ValidationError, match='verb-led'):
        validator.validate_package(root)
