# SPDX-License-Identifier: GPL-3.0-or-later
import json
from pathlib import Path

import numpy as np
import pytest

from core import mesh_io, mesh_validate
from core.mesh_data import MeshData

TESTS = Path(__file__).resolve().parent.parent
GOLDEN = TESTS / "golden"
# Scan asli, tidak di-commit. Kalau kosong atau tidak ada, case privat tidak ikut diparametrisasi.
GOLDEN_PRIVATE = TESTS / "golden_private"


def _cases(directory: Path) -> list[Path]:
    if not directory.is_dir():
        return []
    return sorted(p for p in directory.iterdir() if (p / "expected.json").exists())


GOLDEN_CASES = _cases(GOLDEN)
ALL_GOLDEN_CASES = GOLDEN_CASES + _cases(GOLDEN_PRIVATE)

VERTS = np.array([[0, 0, 0], [10, 0, 0], [0, 8, 0], [0, 0, 6]], dtype=float)
FACES = np.array([[0, 2, 1], [0, 1, 3], [1, 2, 3], [0, 3, 2]])


def test_stl_round_trip_merges_duplicate_vertices(tmp_path):
    path = tmp_path / "tetra.stl"
    mesh_io.save_mesh(MeshData(VERTS, FACES), path)
    loaded = mesh_io.load_mesh(path)
    # STL menyimpan tiap segitiga terpisah (12 vertex); load_mesh menggabungkannya kembali.
    assert len(loaded.vertices) == 4
    assert mesh_validate.triangle_count(loaded) == 4
    assert mesh_validate.is_watertight(loaded)
    assert not loaded.has_vertex_colors


def test_ply_round_trip_keeps_vertex_colors(tmp_path):
    colors = np.array([[255, 0, 0, 255], [0, 255, 0, 255], [0, 0, 255, 255], [9, 9, 9, 255]], dtype=np.uint8)
    path = tmp_path / "tetra.ply"
    mesh_io.save_mesh(MeshData(VERTS, FACES, vertex_colors=colors), path)
    loaded = mesh_io.load_mesh(path)
    assert loaded.has_vertex_colors
    # Urutan vertex bisa berubah, jadi cocokkan warna lewat posisi vertex.
    by_position = {tuple(v): tuple(c) for v, c in zip(loaded.vertices, loaded.vertex_colors)}
    for v, c in zip(VERTS, colors):
        assert by_position[tuple(v)] == tuple(c)


def test_ascii_stl_falls_back_to_trimesh(tmp_path):
    import trimesh

    path = tmp_path / "ascii.stl"
    path.write_bytes(trimesh.Trimesh(VERTS, FACES, process=False).export(file_type="stl_ascii").encode())
    loaded = mesh_io.load_mesh(path)
    assert len(loaded.vertices) == 4
    assert mesh_validate.is_watertight(loaded)


def test_merge_exact_vertices_keeps_first_occurrence_order():
    points = np.array([[1, 2, 3], [0, 0, 0], [1, 2, 3], [-0.0, 0, 0], [5, 5, 5]], dtype=np.float32)
    vertices, inverse = mesh_io.merge_exact_vertices(points)
    np.testing.assert_array_equal(vertices, [[1, 2, 3], [0, 0, 0], [5, 5, 5]])
    np.testing.assert_array_equal(inverse, [0, 1, 0, 1, 2])  # -0.0 digabung dengan 0.0


def test_merge_exact_vertices_survives_hash_collisions(monkeypatch):
    # Semua konstanta hash nol membuat setiap titik bertabrakan; hasil harus tetap benar.
    for name in ("_HASH_X", "_HASH_Y", "_HASH_Z"):
        monkeypatch.setattr(mesh_io, name, np.uint64(0))
    rng = np.random.default_rng(0)
    unique = rng.normal(size=(50, 3)).astype(np.float32)
    points = unique[rng.integers(0, 50, size=400)]
    vertices, inverse = mesh_io.merge_exact_vertices(points)
    np.testing.assert_array_equal(vertices[inverse], points)
    assert len(vertices) == len(np.unique(points, axis=0))


def test_save_stl_round_trip_with_header(tmp_path):
    path = tmp_path / "tetra.stl"
    mesh_io.save_stl(MeshData(VERTS, FACES), path, header="DentalCAD uji")
    assert path.read_bytes()[:13] == b"DentalCAD uji"
    loaded = mesh_io.load_mesh(path)
    assert len(loaded.vertices) == 4 and mesh_validate.is_watertight(loaded)
    with pytest.raises(ValueError, match="80"):
        mesh_io.save_stl(MeshData(VERTS, FACES), path, header="x" * 81)


def test_unsupported_suffix_is_rejected(tmp_path):
    with pytest.raises(ValueError, match="format tidak didukung"):
        mesh_io.load_mesh(tmp_path / "scan.obj")


@pytest.mark.parametrize("case", ALL_GOLDEN_CASES, ids=lambda p: f"{p.parent.name}/{p.name}")
def test_golden_case_matches_expected(case):
    expected = json.loads((case / "expected.json").read_text(encoding="utf-8"))
    mesh = mesh_io.load_mesh(case / expected["input"])
    summary = mesh_validate.summarize(mesh)
    assert mesh_validate.compare_to_expected(summary, expected) == []
    assert mesh.has_vertex_colors == expected.get("vertex_colors", False)
    if "mean_rgba" in expected:
        np.testing.assert_allclose(mesh.vertex_colors.mean(axis=0), expected["mean_rgba"], atol=0.5)


def test_golden_cases_exist():
    assert GOLDEN_CASES, "tests/golden kosong"
