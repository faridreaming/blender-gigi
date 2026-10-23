# SPDX-License-Identifier: GPL-3.0-or-later
"""Baca/tulis STL dan PLY. Satu-satunya modul yang tahu soal format file.

STL biner dibaca langsung dengan numpy (jalur cepat untuk scan besar); STL ASCII dan PLY lewat trimesh.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import trimesh

from .mesh_data import MeshData

SUPPORTED_SUFFIXES = (".stl", ".ply")

_STL_HEADER = 80
_STL_TRIANGLE = np.dtype([("normal", "<f4", (3,)), ("vertices", "<f4", (3, 3)), ("attribute", "<u2")])

# Konstanta multiplikatif 64-bit (golden ratio, murmur3, xxhash) untuk mencampur bit koordinat.
_HASH_X = np.uint64(0x9E3779B97F4A7C15)
_HASH_Y = np.uint64(0xC2B2AE3D27D4EB4F)
_HASH_Z = np.uint64(0x165667B19E3779F9)


def _check_suffix(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix not in SUPPORTED_SUFFIXES:
        raise ValueError(f"format tidak didukung: {path.name} (hanya {', '.join(SUPPORTED_SUFFIXES)})")
    return suffix[1:]


def _read_binary_stl(path: Path) -> np.ndarray | None:
    """Sudut segitiga (M*3, 3) float32, atau None kalau file bukan STL biner."""
    data = path.read_bytes()
    if len(data) < _STL_HEADER + 4:
        return None
    count = int(np.frombuffer(data, dtype="<u4", count=1, offset=_STL_HEADER)[0])
    # Header STL ASCII juga bisa diawali "solid", jadi ukuran file adalah penentu yang andal.
    if len(data) != _STL_HEADER + 4 + count * _STL_TRIANGLE.itemsize:
        return None
    triangles = np.frombuffer(data, dtype=_STL_TRIANGLE, count=count, offset=_STL_HEADER + 4)
    return triangles["vertices"].reshape(-1, 3)


def _group_rows_lexsort(bits: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """(urutan, awal grup) dengan pengurutan leksikografis penuh. Lebih lambat, tanpa risiko tabrakan."""
    order = np.lexsort((bits[:, 2], bits[:, 1], bits[:, 0]))
    sorted_bits = bits[order]
    starts = np.empty(len(order), dtype=bool)
    starts[0] = True
    np.any(sorted_bits[1:] != sorted_bits[:-1], axis=1, out=starts[1:])
    return order, starts


def merge_exact_vertices(points: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Gabungkan titik yang koordinat float32-nya identik.

    Mengembalikan (vertices unik dengan urutan kemunculan pertama, inverse) sehingga
    vertices[inverse] == points. Tidak memakai toleransi: sudut STL yang bersebelahan memang
    ditulis dengan bit yang sama, jadi penggabungan eksak cukup dan tidak memindahkan geometri.
    """
    points = np.ascontiguousarray(points, dtype=np.float32) + np.float32(0.0)  # -0.0 menjadi 0.0
    if len(points) == 0:
        return points.reshape(0, 3), np.zeros(0, dtype=np.int64)
    bits = points.view(np.uint32)

    x, y, z = (bits[:, i].astype(np.uint64) for i in range(3))
    keys = (x * _HASH_X) ^ ((y * _HASH_Y) << np.uint64(1)) ^ (z * _HASH_Z)
    order = np.argsort(keys)
    sorted_keys = keys[order]
    starts = np.empty(len(order), dtype=bool)
    starts[0] = True
    np.not_equal(sorted_keys[1:], sorted_keys[:-1], out=starts[1:])

    group_of_sorted = np.cumsum(starts) - 1
    representative = order[starts]
    group = np.empty(len(order), dtype=np.int64)
    group[order] = group_of_sorted
    if not np.array_equal(bits[representative][group], bits):
        # Dua koordinat berbeda jatuh ke hash yang sama: ulangi dengan pengurutan penuh.
        order, starts = _group_rows_lexsort(bits)
        group_of_sorted = np.cumsum(starts) - 1
        group = np.empty(len(order), dtype=np.int64)
        group[order] = group_of_sorted

    # Nomori ulang grup menurut kemunculan pertama supaya urutan vertex mengikuti file.
    first_seen = np.minimum.reduceat(order, np.flatnonzero(starts))
    rank = np.empty(len(first_seen), dtype=np.int64)
    rank[np.argsort(first_seen)] = np.arange(len(first_seen))
    vertices = points[np.sort(first_seen)]
    return vertices, rank[group]


def load_mesh(path: str | Path) -> MeshData:
    """Baca STL/PLY menjadi MeshData. Vertex duplikat STL digabung; PLY sudah berindeks."""
    path = Path(path)
    file_type = _check_suffix(path)

    if file_type == "stl":
        corners = _read_binary_stl(path)
        if corners is not None:
            vertices, inverse = merge_exact_vertices(corners)
            return MeshData(vertices=vertices, faces=inverse.reshape(-1, 3))

    mesh = trimesh.load(path, file_type=file_type, force="mesh", process=(file_type == "stl"))
    if not isinstance(mesh, trimesh.Trimesh):
        raise ValueError(f"{path.name} tidak berisi mesh segitiga")

    colors = None
    if mesh.visual.kind == "vertex":
        colors = np.asarray(mesh.visual.vertex_colors, dtype=np.uint8)
    return MeshData(vertices=mesh.vertices, faces=mesh.faces, vertex_colors=colors)


def save_stl(mesh: MeshData, path: str | Path, header: str = "") -> None:
    """Tulis STL biner langsung dengan numpy, dengan header ASCII hingga 80 byte."""
    raw = header.encode("ascii")
    if len(raw) > _STL_HEADER:
        raise ValueError(f"header STL maksimal {_STL_HEADER} byte, didapat {len(raw)}")
    corners = mesh.vertices[mesh.faces].astype(np.float64)
    normals = np.cross(corners[:, 1] - corners[:, 0], corners[:, 2] - corners[:, 0])
    lengths = np.linalg.norm(normals, axis=1, keepdims=True)
    normals = np.divide(normals, lengths, out=np.zeros_like(normals), where=lengths > 0)

    triangles = np.zeros(len(mesh.faces), dtype=_STL_TRIANGLE)
    triangles["normal"] = normals
    triangles["vertices"] = corners
    with Path(path).open("wb") as f:
        f.write(raw.ljust(_STL_HEADER, b" "))
        f.write(np.uint32(len(triangles)).astype("<u4").tobytes())
        f.write(triangles.tobytes())


def save_mesh(mesh: MeshData, path: str | Path) -> None:
    """Tulis MeshData ke STL (biner) atau PLY (biner, membawa vertex color bila ada)."""
    path = Path(path)
    file_type = _check_suffix(path)
    out = trimesh.Trimesh(
        vertices=mesh.vertices,
        faces=mesh.faces,
        vertex_colors=mesh.vertex_colors,
        process=False,
    )
    out.export(path, file_type=file_type)
