# SPDX-License-Identifier: GPL-3.0-or-later
"""Pemeriksaan isi zip hasil build per platform (scripts/run_blender_tests.py), tanpa Blender."""

import importlib.util
import sys
import tomllib
import zipfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
WIN = "wheels/scipy-1.18.1-cp313-cp313-win_amd64.whl"
MAC = "wheels/scipy-1.18.1-cp313-cp313-macosx_12_0_arm64.whl"
LINUX = "wheels/scipy-1.18.1-cp313-cp313-manylinux_2_27_x86_64.manylinux_2_28_x86_64.whl"
ANY = "wheels/trimesh-5.1.1-py3-none-any.whl"
MANIFEST = {
    "platforms": ["windows-x64", "macos-arm64", "linux-x64"],
    "wheels": [f"./{w}" for w in (ANY, WIN, MAC, LINUX)],
}
CODE = ["blender_manifest.toml", "LICENSE", "__init__.py", "core/mesh_io.py"]


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


@pytest.mark.parametrize(
    "suffix, platform, own",
    [("windows_x64", "windows-x64", WIN), ("macos_arm64", "macos-arm64", MAC), ("linux_x64", "linux-x64", LINUX)],
)
def test_platform_zip_with_only_its_wheels_passes(runner, tmp_path, suffix, platform, own):
    zip_path = make_zip(tmp_path / f"dentalcad-0.1.0-{suffix}.zip", CODE + [ANY, own])
    assert runner.zip_platform(zip_path, MANIFEST) == platform
    assert runner.check_zip(zip_path, MANIFEST) == []


def test_platform_zip_carrying_another_platforms_wheel_is_caught(runner, tmp_path):
    zip_path = make_zip(tmp_path / "dentalcad-0.1.0-windows_x64.zip", CODE + [ANY, WIN, LINUX])
    problems = runner.check_zip(zip_path, MANIFEST)
    assert any("windows-x64" in p and "wheel di zip" in p for p in problems)


def test_platform_zip_missing_its_wheel_is_caught(runner, tmp_path):
    zip_path = make_zip(tmp_path / "dentalcad-0.1.0-macos_arm64.zip", CODE + [ANY])
    assert any("wheel di zip" in p for p in runner.check_zip(zip_path, MANIFEST))


def test_universal_zip_expects_all_wheels(runner, tmp_path):
    zip_path = make_zip(tmp_path / "dentalcad-0.1.0.zip", CODE + [ANY, WIN, MAC, LINUX])
    assert runner.zip_platform(zip_path, MANIFEST) is None
    assert runner.check_zip(zip_path, MANIFEST) == []


def test_ci_blender_download_is_caught(runner, tmp_path):
    zip_path = make_zip(tmp_path / "dentalcad-0.1.0-linux_x64.zip", CODE + [ANY, LINUX, "blender-download.tar.xz"])
    assert any("blender-download.tar.xz" in p for p in runner.check_zip(zip_path, MANIFEST))


def test_pycache_is_caught(runner, tmp_path):
    names = CODE + [ANY, LINUX, "core/__pycache__/mesh_io.cpython-313.pyc"]
    zip_path = make_zip(tmp_path / "dentalcad-0.1.0-linux_x64.zip", names)
    assert any("cache Python" in p for p in runner.check_zip(zip_path, MANIFEST))


def test_size_limits_are_caught(runner, tmp_path, monkeypatch):
    zip_path = make_zip(tmp_path / "dentalcad-0.1.0-linux_x64.zip", CODE + [ANY, LINUX])
    monkeypatch.setattr(runner, "PLATFORM_ZIP_BUDGET_BYTES", 10)
    assert any("anggaran" in p for p in runner.check_zip(zip_path, MANIFEST))
    monkeypatch.setattr(runner, "MAX_ZIP_BYTES", 10)
    assert any("melebihi 0 MB" in p for p in runner.check_zip(zip_path, MANIFEST))


def test_every_real_manifest_wheel_belongs_to_exactly_one_platform_or_all(runner):
    with (ROOT / "blender_manifest.toml").open("rb") as f:
        manifest = tomllib.load(f)
    per_platform = {p: set(runner.wheels_for_platform(manifest, p)) for p in manifest["platforms"]}
    universal = set.intersection(*per_platform.values())
    assert all(w.endswith("-none-any.whl") for w in universal)
    for wheel in (w.removeprefix("./") for w in manifest["wheels"]):
        owners = [p for p, wheels in per_platform.items() if wheel in wheels]
        assert len(owners) in (1, len(manifest["platforms"])), (wheel, owners)
