# SPDX-License-Identifier: GPL-3.0-or-later
"""Metrik validasi mesh untuk golden case. Dihitung langsung dengan numpy, tanpa trimesh."""

from __future__ import annotations

import numpy as np

from .mesh_data import MeshData


def triangle_count(mesh: MeshData) -> int:
    return int(len(mesh.faces))


def bounding_box(mesh: MeshData) -> tuple[np.ndarray, np.ndarray]:
    """(min, max) per sumbu, masing-masing array (3,)."""
    if len(mesh.vertices) == 0:
        raise ValueError("mesh kosong tidak punya bounding box")
    return mesh.vertices.min(axis=0), mesh.vertices.max(axis=0)


def _edge_use_counts(mesh: MeshData) -> np.ndarray:
    """Berapa face yang memakai tiap edge unik (edge tak berarah)."""
    faces = mesh.faces
    edges = np.concatenate([faces[:, [0, 1]], faces[:, [1, 2]], faces[:, [2, 0]]])
    edges.sort(axis=1)
    # Satu kunci int64 per edge jauh lebih cepat daripada np.unique(axis=0) untuk jutaan edge.
    keys = edges[:, 0] * np.int64(len(mesh.vertices)) + edges[:, 1]
    _, counts = np.unique(keys, return_counts=True)
    return counts


def boundary_edge_count(mesh: MeshData) -> int:
    """Edge yang hanya dipakai satu face (tepi lubang)."""
    if len(mesh.faces) == 0:
        return 0
    return int(np.count_nonzero(_edge_use_counts(mesh) == 1))


def non_manifold_edge_count(mesh: MeshData) -> int:
    """Edge yang dipakai lebih dari dua face."""
    if len(mesh.faces) == 0:
        return 0
    return int(np.count_nonzero(_edge_use_counts(mesh) > 2))


def is_watertight(mesh: MeshData) -> bool:
    """True kalau setiap edge dipakai tepat dua face."""
    if len(mesh.faces) == 0:
        return False
    return bool(np.all(_edge_use_counts(mesh) == 2))


def summarize(mesh: MeshData) -> dict:
    """Ringkasan metrik dalam bentuk yang sama dengan expected.json golden case."""
    bbox_min, bbox_max = bounding_box(mesh)
    return {
        "triangle_count": triangle_count(mesh),
        "watertight": is_watertight(mesh),
        "bbox_min": bbox_min.tolist(),
        "bbox_max": bbox_max.tolist(),
        "boundary_edges": boundary_edge_count(mesh),
        "non_manifold_edges": non_manifold_edge_count(mesh),
    }


def compare_to_expected(summary: dict, expected: dict, bbox_tol_mm: float = 1e-4) -> list[str]:
    """Daftar selisih antara summary dan expected.json. List kosong berarti cocok."""
    problems = []
    for key in ("triangle_count", "watertight"):
        if summary[key] != expected[key]:
            problems.append(f"{key}: didapat {summary[key]}, diharapkan {expected[key]}")
    for key in ("bbox_min", "bbox_max"):
        got = np.asarray(summary[key])
        want = np.asarray(expected[key])
        if not np.allclose(got, want, atol=bbox_tol_mm, rtol=0.0):
            problems.append(f"{key}: didapat {got.tolist()}, diharapkan {want.tolist()}")
    return problems
