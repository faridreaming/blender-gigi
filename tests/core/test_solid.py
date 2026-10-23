# SPDX-License-Identifier: GPL-3.0-or-later
import manifold3d as m3
import numpy as np
import pytest

from core import solid
from core.mesh_data import MeshData
from core.mesh_validate import is_watertight

TETRA = MeshData(
    np.array([[0, 0, 0], [1, 0, 0], [0, 1, 0], [0, 0, 1]], dtype=float),
    np.array([[0, 2, 1], [0, 1, 3], [1, 2, 3], [0, 3, 2]]),
)


def test_round_trip_keeps_volume():
    s = solid.to_manifold(TETRA)
    assert s.volume() == pytest.approx(1 / 6)
    back = solid.to_mesh_data(s)
    assert is_watertight(back)
    assert len(back.faces) == 4


def test_open_surface_is_rejected():
    open_mesh = MeshData(TETRA.vertices, TETRA.faces[:3])
    with pytest.raises(solid.SolidError, match="NotManifold"):
        solid.to_manifold(open_mesh, "scan")


def test_empty_result_is_rejected():
    empty = m3.Manifold.cube((1, 1, 1)) - m3.Manifold.cube((2, 2, 2), center=True)
    with pytest.raises(solid.SolidError, match="kosong"):
        solid.check_solid(empty)


def test_sealed_void_detection():
    box = m3.Manifold.cube((10, 10, 10), center=True)
    sealed = box - m3.Manifold.cube((4, 4, 4), center=True)
    drilled = sealed - m3.Manifold.cylinder(10, 1.0).translate((0, 0, -5.5))
    assert solid.sealed_void_count(box) == 0
    assert solid.sealed_void_count(sealed) == 1
    assert solid.has_sealed_void(sealed)
    assert not solid.has_sealed_void(drilled)
