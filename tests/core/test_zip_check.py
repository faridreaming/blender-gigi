# SPDX-License-Identifier: GPL-3.0-or-later
"""Pemeriksaan isi zip hasil build (scripts/run_blender_tests.py), tanpa Blender."""

import importlib.util
import sys
import zipfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = {"wheels": ["./wheels/a-1.0-py3-none-any.whl"]}
GOOD = ["blender_manifest.toml", "LICENSE", "__init__.py", "core/mesh_io.py", "wheels/a-1.0-py3-none-any.whl"]


@pytest.fixture(scope="module")
def runner():
    sys.path.insert(0, str(ROOT / "scripts"))
    spec = importlib.util.spec_from_file_location("run_blender_tests", ROOT / "scripts" / "run_blender_tests.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def make_zip(path: Path, names: list[str]) -> Path:
    with zipfile.ZipFile(path, "w") as z:
        for name in names:
            z.writestr(name, b"x")
    return path


def test_clean_zip_passes(runner, tmp_path):
    assert runner.check_zip(make_zip(tmp_path / "ok.zip", GOOD), MANIFEST) == []


def test_ci_blender_download_is_caught(runner, tmp_path):
    zip_path = make_zip(tmp_path / "bad.zip", GOOD + ["blender-download.tar.xz"])
    problems = runner.check_zip(zip_path, MANIFEST)
    assert any("blender-download.tar.xz" in p for p in problems)


def test_pycache_and_wheel_mismatch_are_caught(runner, tmp_path):
    names = GOOD + ["core/__pycache__/mesh_io.cpython-313.pyc", "wheels/stray-0.1-py3-none-any.whl"]
    problems = runner.check_zip(make_zip(tmp_path / "bad.zip", names), MANIFEST)
    assert any("cache Python" in p for p in problems)
    assert any("wheel di zip" in p for p in problems)


def test_oversized_zip_is_caught(runner, tmp_path, monkeypatch):
    monkeypatch.setattr(runner, "MAX_ZIP_BYTES", 10)
    problems = runner.check_zip(make_zip(tmp_path / "big.zip", GOOD), MANIFEST)
    assert any("ukuran zip" in p for p in problems)
