# SPDX-License-Identifier: GPL-3.0-or-later
"""Aturan proyek dari CLAUDE.md dan docs/ARCHITECTURE.md yang bisa dicek otomatis."""

import ast
import importlib.util
import shutil
import subprocess
import sys
import tomllib
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
FORBIDDEN_IN_CORE = {"bpy", "bmesh", "mathutils", "gpu", "bpy_extras"}
TEXT_SUFFIXES = {".py", ".md", ".toml", ".json", ".txt", ".yml", ".yaml", ".cfg", ".ini", ""}
EM_DASH, EN_DASH = chr(0x2014), chr(0x2013)
# golden_private berisi data pasien: tidak dibaca oleh tes aturan teks.
SKIP_DIRS = {".git", ".venv", ".pytest_cache", "__pycache__", "wheels", "dist", ".claude", "golden_private"}


def _manifest() -> dict:
    with (ROOT / "blender_manifest.toml").open("rb") as f:
        return tomllib.load(f)


def test_core_never_imports_blender_modules():
    for path in sorted((ROOT / "core").glob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom) and node.level == 0:
                names = [node.module or ""]
            else:
                continue
            for name in names:
                assert name.split(".")[0] not in FORBIDDEN_IN_CORE, f"{path.name} import {name}"


def test_core_imports_without_bpy_in_fresh_interpreter():
    code = (
        "import sys; sys.path.insert(0, sys.argv[1]);"
        "import core.mesh_io, core.mesh_validate, core.material_db, core.units, core.solid, core.model_presets, core.calibration, core.synthetic, core.geometry, core.margin, core.insertion, core.geodesic, core.spacer, core.template, core.crown;"
        "assert 'bpy' not in sys.modules"
    )
    subprocess.run([sys.executable, "-c", code, str(ROOT)], check=True)


def _text_files():
    for path in ROOT.rglob("*"):
        if any(part in SKIP_DIRS for part in path.relative_to(ROOT).parts):
            continue
        if path.is_file() and path.suffix.lower() in TEXT_SUFFIXES:
            yield path


def test_no_em_or_en_dash_anywhere():
    offenders = []
    for path in _text_files():
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for lineno, line in enumerate(text.splitlines(), 1):
            if EM_DASH in line or EN_DASH in line:
                offenders.append(f"{path.relative_to(ROOT)}:{lineno}")
    assert offenders == [], "em/en dash ditemukan: " + ", ".join(offenders)


def test_private_scans_are_never_tracked_by_git():
    if shutil.which("git") is None or not (ROOT / ".git").exists():
        pytest.skip("bukan checkout git")
    tracked = subprocess.run(
        ["git", "ls-files", "--", "tests/golden_private"],
        cwd=ROOT, check=True, capture_output=True, text=True,
    ).stdout.split()
    assert tracked == ["tests/golden_private/README.md"], f"scan privat terlacak git: {tracked}"


def test_manifest_wheels_match_download_script():
    spec = importlib.util.spec_from_file_location("download_wheels", ROOT / "scripts" / "download_wheels.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module  # dataclass butuh modulnya terdaftar saat dieksekusi
    spec.loader.exec_module(module)
    assert _manifest()["wheels"] == [f"./wheels/{w.filename}" for w in module.WHEELS]


def test_architecture_manifest_example_is_the_real_manifest():
    doc = (ROOT / "docs" / "ARCHITECTURE.md").read_text(encoding="utf-8")
    block = doc.split("```toml\n", 1)[1].split("```", 1)[0]
    assert block == (ROOT / "blender_manifest.toml").read_text(encoding="utf-8")


def test_manifest_fields_follow_architecture():
    m = _manifest()
    assert m["id"] == "dentalcad"
    assert m["blender_version_min"] == "5.2.0"
    assert "blender_version_max" not in m
    assert m["platforms"] == ["windows-x64", "macos-arm64", "linux-x64"]
    assert m["license"] == ["SPDX:GPL-3.0-or-later"]
    assert len(m["tagline"]) <= 64 and not m["tagline"].endswith(".")
    assert "network" not in m["permissions"]
    assert all(len(reason) <= 64 for reason in m["permissions"].values())


def test_crown_tuning_set_has_deep_scallops_and_anterior_dies():
    """CLAUDE.md: set tuning fitur crown wajib berisi scallop dalam (PL 2,5 dan 3,5 mm) dan die anterior."""
    sys.path.insert(0, str(ROOT))
    try:
        spec = importlib.util.spec_from_file_location("crown_benchmark", ROOT / "scripts" / "crown_benchmark.py")
        bench = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(bench)
        from core.template import fdi_kind
    finally:
        sys.path.remove(str(ROOT))
    cases = [c for c in bench.TUNING.values() if not c.get("expect_error")]
    peak_to_valley = {round(2 * c["die"].get("scallop_mm", 0.0), 2) for c in cases}
    assert {2.5, 3.5} <= peak_to_valley
    anterior = [c for c in cases if fdi_kind(c["fdi"]) in ("incisor", "canine")]
    assert any(2 * c["die"].get("scallop_mm", 0.0) >= 2.5 for c in anterior)
