# SPDX-License-Identifier: GPL-3.0-or-later
import numpy as np
import pytest

from core.mesh_data import MeshData
from core import mesh_validate as mv

TETRA_VERTS = np.array([[0, 0, 0], [1, 0, 0], [0, 1, 0], [0, 0, 1]], dtype=float)
TETRA_FACES = np.array([[0, 2, 1], [0, 1, 3], [1, 2, 3], [0, 3, 2]])


def tetra() -> MeshData:
    return MeshData(TETRA_VERTS, TETRA_FACES)


def test_closed_tetrahedron_is_watertight():
    mesh = tetra()
    assert mv.triangle_count(mesh) == 4
    assert mv.is_watertight(mesh)
    assert mv.boundary_edge_count(mesh) == 0
    assert mv.non_manifold_edge_count(mesh) == 0


def test_removing_a_face_opens_three_boundary_edges():
    mesh = MeshData(TETRA_VERTS, TETRA_FACES[:3])
    assert not mv.is_watertight(mesh)
    assert mv.boundary_edge_count(mesh) == 3


def test_edge_shared_by_three_faces_is_non_manifold():
    verts = np.vstack([TETRA_VERTS, [[1, 1, 1]]])
    faces = np.vstack([TETRA_FACES, [[0, 1, 4]]])  # edge 0-1 kini dipakai tiga face
    mesh = MeshData(verts, faces)
    assert mv.non_manifold_edge_count(mesh) == 1
    assert not mv.is_watertight(mesh)


def test_empty_mesh_is_not_watertight():
    mesh = MeshData(np.zeros((0, 3)), np.zeros((0, 3), dtype=int))
    assert not mv.is_watertight(mesh)
    assert mv.triangle_count(mesh) == 0
    with pytest.raises(ValueError):
        mv.bounding_box(mesh)


def test_bounding_box():
    lo, hi = mv.bounding_box(tetra())
    np.testing.assert_array_equal(lo, [0, 0, 0])
    np.testing.assert_array_equal(hi, [1, 1, 1])


def test_compare_to_expected_reports_each_mismatch():
    summary = mv.summarize(tetra())
    assert mv.compare_to_expected(summary, dict(summary)) == []

    wrong = dict(summary, triangle_count=5, bbox_max=[1, 1, 2])
    problems = mv.compare_to_expected(summary, wrong)
    assert len(problems) == 2
    assert any("triangle_count" in p for p in problems)
    assert any("bbox_max" in p for p in problems)


def test_mesh_data_rejects_out_of_range_face_index():
    with pytest.raises(ValueError):
        MeshData(TETRA_VERTS, [[0, 1, 4]])


def test_mesh_data_pads_rgb_colors_to_rgba():
    mesh = MeshData(TETRA_VERTS, TETRA_FACES, vertex_colors=np.full((4, 3), 10, dtype=np.uint8))
    assert mesh.vertex_colors.shape == (4, 4)
    assert np.all(mesh.vertex_colors[:, 3] == 255)
