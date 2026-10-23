# SPDX-License-Identifier: GPL-3.0-or-later
"""Representasi mesh internal: array numpy, bukan bpy.types.Mesh."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass
class MeshData:
    """Mesh segitiga.

    vertices: float64 (N, 3), satuan mm.
    faces: int64 (M, 3), indeks ke vertices.
    vertex_colors: uint8 (N, 4) RGBA sRGB, atau None kalau file tidak membawa warna.
    """

    vertices: np.ndarray
    faces: np.ndarray
    vertex_colors: np.ndarray | None = None

    def __post_init__(self) -> None:
        self.vertices = np.ascontiguousarray(self.vertices, dtype=np.float64).reshape(-1, 3)
        self.faces = np.ascontiguousarray(self.faces, dtype=np.int64).reshape(-1, 3)
        if self.vertex_colors is not None:
            colors = np.asarray(self.vertex_colors)
            if colors.ndim != 2 or colors.shape[1] not in (3, 4):
                raise ValueError(f"vertex_colors harus (N, 3) atau (N, 4), didapat {colors.shape}")
            if colors.shape[1] == 3:
                alpha = np.full((colors.shape[0], 1), 255, dtype=np.uint8)
                colors = np.hstack([colors.astype(np.uint8), alpha])
            self.vertex_colors = np.ascontiguousarray(colors, dtype=np.uint8)
            if len(self.vertex_colors) != len(self.vertices):
                raise ValueError("jumlah vertex_colors tidak sama dengan jumlah vertices")
        if len(self.faces) and (self.faces.min() < 0 or self.faces.max() >= len(self.vertices)):
            raise ValueError("faces berisi indeks di luar rentang vertices")

    @property
    def has_vertex_colors(self) -> bool:
        return self.vertex_colors is not None
