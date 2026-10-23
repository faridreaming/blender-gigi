# SPDX-License-Identifier: GPL-3.0-or-later
"""Solid tertutup lewat manifold3d: konversi dari/ke MeshData dan validasi.

Permukaan terbuka (scan mentah) tidak bisa menjadi Manifold; to_manifold menolaknya dengan
SolidError, bukan menghasilkan solid kosong diam-diam.
"""

from __future__ import annotations

import manifold3d as m3
import numpy as np

from .mesh_data import MeshData


class SolidError(ValueError):
    """Geometri tidak bisa menjadi, atau tidak lagi merupakan, solid manifold yang valid."""


def check_solid(solid: m3.Manifold, name: str = "solid") -> m3.Manifold:
    status = solid.status()
    if status != m3.Error.NoError:
        raise SolidError(f"{name}: manifold3d melaporkan {status.name}")
    if solid.is_empty():
        raise SolidError(f"{name}: hasilnya kosong")
    return solid


def to_manifold(mesh: MeshData, name: str = "mesh") -> m3.Manifold:
    data = m3.Mesh(
        vert_properties=np.ascontiguousarray(mesh.vertices, dtype=np.float32),
        tri_verts=np.ascontiguousarray(mesh.faces, dtype=np.uint32),
    )
    return check_solid(m3.Manifold(data), name)


def to_mesh_data(solid: m3.Manifold) -> MeshData:
    mesh = solid.to_mesh()
    vertices = np.asarray(mesh.vert_properties, dtype=np.float64)[:, :3]
    return MeshData(vertices=vertices, faces=np.asarray(mesh.tri_verts, dtype=np.int64))


def sealed_void_count(solid: m3.Manifold) -> int:
    """Jumlah rongga tertutup di dalam solid (tempat resin bisa terjebak).

    decompose() memisahkan solid per permukaan terhubung; rongga yang tidak terhubung ke luar
    muncul sebagai permukaan tersendiri yang menghadap ke dalam, sehingga volumenya negatif.
    """
    return sum(1 for part in solid.decompose() if part.volume() < 0)


def has_sealed_void(solid: m3.Manifold) -> bool:
    return sealed_void_count(solid) > 0
