from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
HOOK_SCRIPT = REPO_ROOT / "tools" / "on_version_bump.py"


def _build_synthetic_repo(tmp_path: Path) -> Path:
    (tmp_path / "tools").mkdir()
    shutil.copy(HOOK_SCRIPT, tmp_path / "tools" / "on_version_bump.py")

    (tmp_path / "VERSION").write_text("0.1.0\n", encoding="utf-8")
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "little-meals"\nversion = "0.1.0"\ndescription = "x"\n', encoding="utf-8"
    )
    (tmp_path / "MODULE.bazel").write_text(
        'module(\n    name = "little_meals",\n    version = "0.1.0",\n)\n', encoding="utf-8"
    )
    (tmp_path / "src" / "little_meals").mkdir(parents=True)
    (tmp_path / "src" / "little_meals" / "BUILD.bazel").write_text(
        'py_wheel(\n    name = "wheel",\n    version = "0.1.0",\n)\n', encoding="utf-8"
    )
    (tmp_path / "src" / "little_meals" / "__init__.py").write_text('__version__ = "0.1.0"\n', encoding="utf-8")
    return tmp_path


@pytest.mark.requirement("REQ-000000009")
def test_hook_updates_all_version_bearing_files(tmp_path: Path):
    repo = _build_synthetic_repo(tmp_path)

    result = subprocess.run(
        [sys.executable, str(repo / "tools" / "on_version_bump.py"), "9.9.9"],
        cwd=repo,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    assert 'version = "9.9.9"' in (repo / "pyproject.toml").read_text(encoding="utf-8")
    assert 'version = "9.9.9"' in (repo / "MODULE.bazel").read_text(encoding="utf-8")
    assert 'version = "9.9.9"' in (repo / "src" / "little_meals" / "BUILD.bazel").read_text(encoding="utf-8")
    assert '__version__ = "9.9.9"' in (repo / "src" / "little_meals" / "__init__.py").read_text(encoding="utf-8")


def test_hook_reads_lvx_new_version_env_var_when_no_arg(tmp_path: Path):
    repo = _build_synthetic_repo(tmp_path)

    import os

    env = dict(os.environ, LVX_NEW_VERSION="7.7.7")
    result = subprocess.run(
        [sys.executable, str(repo / "tools" / "on_version_bump.py")],
        cwd=repo,
        capture_output=True,
        text=True,
        env=env,
    )

    assert result.returncode == 0, result.stderr
    assert 'version = "7.7.7"' in (repo / "pyproject.toml").read_text(encoding="utf-8")


def test_hook_exits_1_when_a_pattern_is_missing(tmp_path: Path):
    repo = _build_synthetic_repo(tmp_path)
    (repo / "pyproject.toml").write_text('[project]\nname = "little-meals"\n', encoding="utf-8")

    result = subprocess.run(
        [sys.executable, str(repo / "tools" / "on_version_bump.py"), "9.9.9"],
        cwd=repo,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1
    assert "ERROR" in result.stderr
