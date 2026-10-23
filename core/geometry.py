# SPDX-License-Identifier: GPL-3.0-or-later
"""Operasi geometri dasar pada mesh segitiga: normal, edge unik, dan titik terdekat di permukaan."""

from __future__ import annotations

import numpy as np
from scipy.spatial import cKDTree

from .mesh_data import MeshData


def face_normals(vertices: np.ndarray, faces: np.ndarray, normalize: bool = True) -> np.ndarray:
    corners = vertices[faces]
    normals = np.cross(corners[:, 1] - corners[:, 0], corners[:, 2] - corners[:, 0])
    if not normalize:
        return normals
    lengths = np.linalg.norm(normals, axis=1, keepdims=True)
    return np.divide(normals, lengths, out=np.zeros_like(normals), where=lengths > 0)


def vertex_normals(vertices: np.ndarray, faces: np.ndarray) -> np.ndarray:
    """Normal vertex berbobot luas (jumlah normal face tak ternormalisasi)."""
    weighted = face_normals(vertices, faces, normalize=False)
    normals = np.zeros_like(vertices, dtype=float)
    for k in range(3):
        np.add.at(normals, faces[:, k], weighted)
    lengths = np.linalg.norm(normals, axis=1, keepdims=True)
    return np.divide(normals, lengths, out=np.zeros_like(normals), where=lengths > 0)


def unique_edges(faces: np.ndarray) -> np.ndarray:
    """Edge tak berarah unik (E, 2), indeks terkecil di kolom pertama."""
    edges = np.concatenate([faces[:, [0, 1]], faces[:, [1, 2]], faces[:, [2, 0]]])
    edges.sort(axis=1)
    return np.unique(edges, axis=0)


def closest_point_on_triangles(points: np.ndarray, a: np.ndarray, b: np.ndarray, c: np.ndarray) -> np.ndarray:
    """Titik terdekat di segitiga (a, b, c) untuk setiap titik; semua array (N, 3). Ericson, Real-Time
    Collision Detection, 5.1.5, divektorisasi."""
    ab, ac, ap = b - a, c - a, points - a
    d1 = np.einsum("ij,ij->i", ab, ap)
    d2 = np.einsum("ij,ij->i", ac, ap)
    bp = points - b
    d3 = np.einsum("ij,ij->i", ab, bp)
    d4 = np.einsum("ij,ij->i", ac, bp)
    cp = points - c
    d5 = np.einsum("ij,ij->i", ab, cp)
    d6 = np.einsum("ij,ij->i", ac, cp)

    va = d3 * d6 - d5 * d4
    vb = d5 * d2 - d1 * d6
    vc = d1 * d4 - d3 * d2
    denom = va + vb + vc
    with np.errstate(divide="ignore", invalid="ignore"):
        v = vb / denom
        w = vc / denom
    result = a + ab * v[:, None] + ac * w[:, None]  # di dalam segitiga

    def put(mask, value):
        result[mask] = value[mask]

    with np.errstate(divide="ignore", invalid="ignore"):
        # Tepi BC
        mask = (va <= 0) & ((d4 - d3) >= 0) & ((d5 - d6) >= 0)
        t = (d4 - d3) / ((d4 - d3) + (d5 - d6))
        put(mask, b + (c - b) * t[:, None])
        # Tepi AC
        mask = (vb <= 0) & (d2 >= 0) & (d6 <= 0)
        t = d2 / (d2 - d6)
        put(mask, a + ac * t[:, None])
        # Tepi AB
        mask = (vc <= 0) & (d1 >= 0) & (d3 <= 0)
        t = d1 / (d1 - d3)
        put(mask, a + ab * t[:, None])
    # Sudut
    put((d6 >= 0) & (d5 <= d6), c)
    put((d3 >= 0) & (d4 <= d3), b)
    put((d1 <= 0) & (d2 <= 0), a)
    return result


class MeshProjector:
    """Titik terdekat di permukaan mesh. Kandidat face dicari lewat cKDTree atas titik berat face, lalu
    jarak titik ke segitiga dihitung eksak untuk k kandidat terdekat."""

    def __init__(self, mesh: MeshData, k: int = 24):
        self.vertices = np.asarray(mesh.vertices, float)
        self.faces = np.asarray(mesh.faces)
        self.k = min(k, len(self.faces))
        self.tree = cKDTree(self.vertices[self.faces].mean(axis=1))

    def closest(self, points: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        """(titik terdekat (N, 3), indeks face (N,), jarak (N,))."""
        points = np.asarray(points, float).reshape(-1, 3)
        _, candidates = self.tree.query(points, k=self.k)
        candidates = candidates.reshape(len(points), -1)
        corners = self.vertices[self.faces[candidates]]  # (N, k, 3, 3)
        flat = closest_point_on_triangles(
            np.repeat(points, candidates.shape[1], axis=0),
            corners[:, :, 0].reshape(-1, 3), corners[:, :, 1].reshape(-1, 3), corners[:, :, 2].reshape(-1, 3),
        ).reshape(len(points), -1, 3)
        dist = np.linalg.norm(flat - points[:, None], axis=2)
        best = np.argmin(dist, axis=1)
        rows = np.arange(len(points))
        return flat[rows, best], candidates[rows, best], dist[rows, best]
