# SPDX-License-Identifier: GPL-3.0-or-later
"""Spacer (cement gap): permukaan dalam crown dari die hasil block-out (docs/PHASE2.md §5.3).

Urutan mengikuti konvensi exocad untuk milling 5-axis (EXQ: "the cement gap is applied after doing the
block-out"): block-out dulu (core/insertion.py), lalu setiap vertex permukaan dalam digeser

    gap(d) * n + s_r * h(n) + s_a * (n . a) a

dengan d = jarak geodesik ke margin line (core/geodesic.py), n = normal vertex die hasil block-out yang
dihaluskan (radius max(0,5 mm, 10 sigma), sama dengan peta undercut §5.2), a = sumbu insersi, dan h(n) =
komponen n yang tegak lurus sumbu. gap(d) = 0 sampai "from margin", naik linear sepanjang
lebar transisi, lalu sama dengan cement gap. Spacing radial s_r dan axial s_a berlaku di seluruh permukaan dalam,
termasuk zona tanpa cement gap, dan cement gap ditambahkan di atasnya (EXQ: "independent of the cement gap";
DTX). Bila s_r = s_a, offset spacing = s * n.

Untuk produksi 3 atau 4 axis (`milling_axes` di preset), block-out kedua sejajar sumbu diterapkan pada
permukaan dalam setelah cement gap (EXQ: "material configurations typically define an additional block-out being
applied after generating the cement gap"), sampai margin (zona 0). Untuk 5 axis tidak ada block-out kedua;
undercut di permukaan dalam hanya ditampilkan ("Show undercuts").

Pemeriksaan undercut setelah spacing lalu menghapusnya mirip klaim EP2187833B1 (Straumann), yang menurut Google
Patents masih aktif di Eropa sampai perkiraan 2028-07-24; lihat docs/PHASE2.md §5.3. Bukan kesimpulan hukum.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.spatial import cKDTree

from .geodesic import distance_from_curve
from .geometry import face_normals, vertex_normals
from .margin import crease_score
from .mesh_data import MeshData

SMOOTH_RADIUS_MIN_MM = 0.5  # sama dengan InsertionParams (PHASE2.md §5.2)
SMOOTH_RADIUS_PER_NOISE = 10.0
MILLING_AXES = (3, 4, 5)


SLIVER_MM = 0.01  # segitiga dengan tinggi di bawah ini terbalik oleh beda normal kecil; bukan lipatan permukaan


class SpacerError(ValueError):
    """Spacer tidak bisa dihitung."""


@dataclass(frozen=True)
class SpacerParams:
    cement_gap_mm: float
    from_margin_mm: float
    transition_mm: float
    radial_mm: float
    axial_mm: float

    def __post_init__(self) -> None:
        if min(self.cement_gap_mm, self.from_margin_mm, self.transition_mm) < 0:
            raise SpacerError("cement gap, from margin, dan lebar transisi wajib >= 0")

    @classmethod
    def from_preset(cls, preset) -> "SpacerParams":
        """Dari preset material (core/material_db.MaterialPreset)."""
        return cls(
            cement_gap_mm=preset.value("cement_gap_um") / 1000.0,
            from_margin_mm=preset.value("cement_gap_from_margin_mm"),
            transition_mm=preset.value("cement_gap_transition_mm"),
            radial_mm=preset.value("radial_spacing_um") / 1000.0,
            axial_mm=preset.value("axial_spacing_um") / 1000.0,
        )


def gap_profile(distance: np.ndarray, params: SpacerParams) -> np.ndarray:
    """Cement gap sebagai fungsi jarak geodesik ke margin: 0, transisi linear, lalu penuh."""
    d = np.asarray(distance, float)
    if params.transition_mm == 0:
        ramp = (d >= params.from_margin_mm).astype(float)
    else:
        ramp = np.clip((d - params.from_margin_mm) / params.transition_mm, 0.0, 1.0)
    ramp[~np.isfinite(d)] = 0.0
    return params.cement_gap_mm * ramp


def inner_faces(vertices: np.ndarray, faces: np.ndarray, prep_faces: np.ndarray, band_faces: np.ndarray,
                margin_points: np.ndarray, reach_mm: float = 1.0) -> np.ndarray:
    """Face permukaan dalam: preparasi ditambah face pita margin yang semua vertexnya di sisi preparasi.

    Untuk setiap titik margin m: u_p = arah dari m ke rata-rata vertex preparasi dalam reach_mm, u_r = arah ke
    rata-rata vertex akar dalam reach_mm. Vertex pita v di sisi preparasi bila (v - m) . (u_p - u_r) > 0 untuk
    titik margin terdekat. Satu arah saja tidak cukup: pada shoulder u_p horizontal (ledge) sedangkan vertex akar
    tepat di bawah margin bergeser vertikal, jadi tandanya acak. Face yang dilewati margin tidak ikut; tepi
    crown di margin dirancang di langkah border.
    """
    prep_v = np.zeros(len(vertices), dtype=bool)
    prep_v[faces[prep_faces].ravel()] = True
    root_v = np.zeros(len(vertices), dtype=bool)
    root_v[faces[~prep_faces & ~band_faces].ravel()] = True
    root_v &= ~prep_v
    band_v = np.zeros(len(vertices), dtype=bool)
    band_v[faces[band_faces].ravel()] = True
    candidates = np.flatnonzero(band_v & ~prep_v)
    side = prep_v.copy()
    margin_points = np.asarray(margin_points, float)
    if len(candidates) and prep_v.any() and root_v.any():
        def mean_direction(points):
            tree = cKDTree(points)
            out = np.zeros_like(margin_points)
            for k, nb in enumerate(tree.query_ball_point(margin_points, reach_mm)):
                if nb:
                    out[k] = points[nb].mean(axis=0) - margin_points[k]
            return out / np.maximum(np.linalg.norm(out, axis=1, keepdims=True), 1e-12)

        inward = mean_direction(vertices[prep_v]) - mean_direction(vertices[root_v])
        _, nearest = cKDTree(margin_points).query(vertices[candidates])
        rel = vertices[candidates] - margin_points[nearest]
        side[candidates] = np.einsum("ij,ij->i", rel, inward[nearest]) > 0
    return prep_faces | (band_faces & side[faces].all(axis=1))


@dataclass
class SpacerResult:
    mesh: MeshData  # permukaan dalam (hanya face permukaan dalam, vertex dipetakan ulang)
    face_index: np.ndarray  # indeks face di mesh die asal
    vertex_index: np.ndarray  # indeks vertex di mesh die asal, urutan sama dengan mesh.vertices
    distance_mm: np.ndarray  # jarak geodesik ke margin per vertex permukaan dalam
    gap_mm: np.ndarray  # komponen cement gap per vertex
    displacement: np.ndarray  # (N, 3) vektor offset per vertex
    folded_faces: int  # face permukaan dalam yang terbalik terhadap face die
    folded_slivers: int  # bagian dari folded_faces yang segitiga sliver (tinggi < SLIVER_MM) di die
    params: SpacerParams
    axis: np.ndarray


def smoothed_normals(vertices: np.ndarray, faces: np.ndarray, noise_sigma_mm: float) -> np.ndarray:
    """Normal vertex dihaluskan (rata-rata Gauss dalam radius max(0,5 mm, 10 sigma)), seperti peta undercut §5.2."""
    radius = max(SMOOTH_RADIUS_MIN_MM, SMOOTH_RADIUS_PER_NOISE * noise_sigma_mm)
    _, _, smooth = crease_score(vertices, vertex_normals(vertices, faces), radius)
    return smooth


def spacer_surface(blocked: MeshData, faces_mask: np.ndarray, margin_points: np.ndarray, axis,
                   params: SpacerParams, noise_sigma_mm: float = 0.0, smooth: bool = True) -> SpacerResult:
    """Permukaan dalam crown dari mesh die hasil block-out (topologi sama dengan die asal).

    smooth=True: arah offset dari normal yang dihaluskan (versi pertama memakai normal mentah, yang pada derau
    >= 10 um membuat lipatan di atap dan undercut baru di dinding; PHASE2.md §5.3)."""
    vertices = np.asarray(blocked.vertices, float)
    faces = np.asarray(blocked.faces)
    faces_mask = np.asarray(faces_mask, bool)
    if not faces_mask.any():
        raise SpacerError("tidak ada face permukaan dalam")
    axis = np.asarray(axis, float)
    axis = axis / np.linalg.norm(axis)
    used = np.zeros(len(vertices), dtype=bool)
    used[faces[faces_mask].ravel()] = True
    distance = distance_from_curve(blocked, np.asarray(margin_points, float), used)
    if not np.isfinite(distance[used]).any():
        raise SpacerError("jarak ke margin tidak bisa dihitung di permukaan dalam")

    if smooth:
        normals = smoothed_normals(vertices, faces[faces_mask], noise_sigma_mm)
    else:
        normals = vertex_normals(vertices, faces[faces_mask])
    along = normals @ axis
    horizontal = normals - along[:, None] * axis
    gap = gap_profile(distance, params)
    displacement = (gap[:, None] * normals + params.radial_mm * horizontal
                    + params.axial_mm * along[:, None] * axis)

    vertex_index = np.flatnonzero(used)
    remap = np.full(len(vertices), -1)
    remap[vertex_index] = np.arange(len(vertex_index))
    face_index = np.flatnonzero(faces_mask)
    inner_v = vertices[vertex_index] + displacement[vertex_index]
    inner_f = remap[faces[face_index]]
    before = face_normals(vertices, faces[face_index], normalize=False)
    after = face_normals(inner_v, inner_f, normalize=False)
    flipped = np.einsum("ij,ij->i", before, after) <= 0
    corners = vertices[faces[face_index]]
    longest = np.max(np.stack([np.linalg.norm(corners[:, k] - corners[:, (k + 1) % 3], axis=1) for k in range(3)]),
                     axis=0)
    height = np.linalg.norm(before, axis=1) / np.maximum(longest, 1e-12)
    slivers = int(np.sum(flipped & (height < SLIVER_MM)))
    return SpacerResult(MeshData(inner_v, inner_f), face_index, vertex_index, distance[vertex_index],
                        gap[vertex_index], displacement[vertex_index], int(flipped.sum()), slivers, params, axis)


def inner_undercut_depth(mesh: MeshData, axis, margin_points: np.ndarray, height_eps_mm: float = 0.02,
                         step_mm: float = 0.02) -> np.ndarray:
    """Kedalaman undercut per vertex permukaan dalam terhadap sumbu (untuk "Show undercuts")."""
    from .insertion import ShadowField

    vertices = np.asarray(mesh.vertices, float)
    tri = vertices[np.asarray(mesh.faces)]
    field = ShadowField(tri, np.asarray(axis, float), np.asarray(margin_points, float).mean(axis=0), height_eps_mm,
                        step_mm, 3.0)
    return field.depth(vertices)


def new_undercut_mm(result: SpacerResult, margin_points: np.ndarray, height_eps_mm: float = 0.02,
                    step_mm: float = 0.02) -> float:
    """Kedalaman bayangan terbesar pada permukaan dalam (EXQ: cement gap setelah block-out bisa menimbulkan
    undercut baru pada preparasi curam)."""
    depth = inner_undercut_depth(result.mesh, result.axis, margin_points, height_eps_mm, step_mm)
    return float(depth.max()) if len(depth) else 0.0


def second_block_out(result: SpacerResult, margin_points: np.ndarray, max_passes: int = 16):
    """Block-out kedua sejajar sumbu pada permukaan dalam setelah cement gap, sampai margin (zona 0), untuk produksi
    3 atau 4 axis (EXQ). Mengembalikan core.insertion.BlockOut dengan mesh permukaan dalam yang baru."""
    from .insertion import block_out_mesh

    mesh = result.mesh
    faces = np.asarray(mesh.faces)
    return block_out_mesh(mesh, np.ones(len(faces), dtype=bool), np.arange(len(mesh.vertices)), result.axis,
                          np.asarray(margin_points, float).mean(axis=0), 0.0, max_passes=max_passes)
