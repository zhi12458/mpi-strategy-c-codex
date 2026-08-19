from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).parents[1]


def test_public_release_uses_exact_verified_compatibility_forks():
    lock = json.loads((ROOT / "dependency-lock.json").read_text(encoding="utf-8"))
    installed_skill_lock = json.loads(
        (ROOT / "skills" / "mpi-strategy-c" / "dependency-lock.json").read_text(encoding="utf-8")
    )

    assert installed_skill_lock == lock
    assert lock["release_ready"] is True
    assert lock["release_status"] == "verified_compatibility_forks"
    expected = {
        "mpi_translations": (
            "https://github.com/zhi12458/mpi-translations.git",
            "https://git.sr.ht/~iacore/mpi-translations/",
        ),
        "translation_toolkit": (
            "https://github.com/zhi12458/translation-toolkit.git",
            "https://codeberg.org/eastwind/translation-toolkit.git",
        ),
    }
    for name, (fork_origin, upstream_origin) in expected.items():
        spec = lock[name]
        assert spec["origin"] == fork_origin
        assert spec["compatibility_fork"] is True
        assert spec["upstream_origin"] == upstream_origin
        assert len(spec["expected_sha"]) == 40
        assert len(spec["upstream_base_sha"]) == 40

    assert lock["compatibility_policy"]["automatic_main_updates"] is False
    assert lock["compatibility_policy"]["exact_sha_required"] is True
    assert lock["skill_version"] == "0.2.0"
    assert lock["models"]["translation"]["reasoning_effort"] == "medium"
    assert lock["models"]["translation_fallback"]["reasoning_effort"] == "high"
    assert lock["model_policy"]["translation_default"] == "provisional"
    assert lock["model_policy"]["additional_cross_genre_tests"] == 2
