# SPDX-License-Identifier: GPL-3.0-or-later
"""Sumbu insersi, peta undercut, dan block-out (docs/PHASE2.md §5.2).

Alur:
1. Daerah preparasi: face di sisi oklusal margin yang sudah dikonfirmasi. Margin dipakai sebagai batas
   (pita face yang dilewati margin dibuang), lalu komponen terhubung yang berada di dalam lingkar margin
   dipilih sebagai preparasi.
2. Sumbu default: arah luas vektor preparasi (jumlah normal face berbobot luas, sama dengan luas vektor
   lingkar margin), lalu dicari arah di sekitarnya yang meminimalkan luas face membelakangi sumbu
   (normal dihaluskan). Di antara arah yang hampir sama baiknya, dipilih yang paling dekat ke arah awal.
3. Ragu ("perlu dicek"): margin line terbayang (ada titik margin yang tertutup bagian preparasi di
   atasnya sepanjang sumbu), atau ada kelompok arah lain yang terpisah jauh tetapi hampir sama baiknya.
4. Kedalaman undercut per vertex: jarak horizontal (tegak lurus sumbu) ke kontur terbesar di atasnya,
   dihitung per sektor sudut di sekitar sumbu dengan maksimum berjalan dari atas ke bawah, pada posisi
   vertex yang dihaluskan (normal dan posisi mentah berderau; temuan jitter PHASE2.md §4).
5. Block-out sejajar sumbu: vertex preparasi digeser keluar sebesar kedalaman undercut, kecuali di zona
   dekat margin ("Don't block out zone near prepline" di exocad).

Pendekatan visibilitas/bayangan untuk sumbu insersi juga ada di paten DE102006044215 (Sirona), yang
menurut Google Patents sudah gugur (PHASE2.md §5.2, bukan kesimpulan hukum).
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components
from scipy.spatial import cKDTree

from .geometry import MeshProjector, face_normals, vertex_normals
from .margin import crease_score, estimate_noise_sigma
from .mesh_data import MeshData


@dataclass(frozen=True)
class InsertionParams:
    """Parameter algoritma (bukan klinis). Asal setiap nilai di PHASE2.md §5.2."""

    smooth_radius_min_mm: float = 0.5
    smooth_radius_per_noise: float = 10.0
    cone_deg: float = 20.0
    grid_step_deg: float = 1.0
    near_optimal_area_fraction: float = 0.002
    ambiguity_deg: float = 10.0
    margin_shadow_min_mm: float = 0.02
    margin_shadow_per_noise: float = 2.0
    depth_floor_min_mm: float = 0.01
    depth_floor_per_noise: float = 1.0
    shadow_height_eps_mm: float = 0.02
    depth_step_mm: float = 0.02


class InsertionError(ValueError):
    """Sumbu insersi atau undercut tidak bisa dihitung (misalnya preparasi tidak terpisah dari akar)."""


# 1. Daerah preparasi ---------------------------------------------------------------------------------

def _resample_closed(points: np.ndarray, spacing: float) -> np.ndarray:
    closed = np.vstack([points, points[:1]])
    seg = np.linalg.norm(np.diff(closed, axis=0), axis=1)
    s = np.concatenate([[0.0], np.cumsum(seg)])
    t = np.arange(0.0, s[-1], spacing)
    return np.stack([np.interp(t, s, closed[:, k]) for k in range(3)], axis=1)


def _face_adjacency(faces: np.ndarray) -> coo_matrix:
    """Face yang berbagi edge."""
    n = len(faces)
    edges = np.concatenate([faces[:, [0, 1]], faces[:, [1, 2]], faces[:, [2, 0]]])
    edges.sort(axis=1)
    owner = np.tile(np.arange(n), 3)
    order = np.lexsort((edges[:, 1], edges[:, 0]))
    e, o = edges[order], owner[order]
    same = np.all(e[1:] == e[:-1], axis=1)
    a, b = o[1:][same], o[:-1][same]
    return coo_matrix((np.ones(len(a)), (a, b)), shape=(n, n))


def _plane_frame(points: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    center = points.mean(axis=0)
    _, _, vt = np.linalg.svd(points - center, full_matrices=False)
    return center, vt[0], vt[1], vt[2]


@dataclass
class PrepRegion:
    faces: np.ndarray  # bool per face: preparasi (di atas margin), tanpa pita margin
    vertices: np.ndarray  # bool per vertex: dipakai face preparasi
    band_faces: np.ndarray  # bool per face: pita yang dilewati margin
    margin: np.ndarray  # titik margin rapat (frame mesh)


def prep_region(mesh: MeshData, margin_points: np.ndarray) -> PrepRegion:
    """Pisahkan preparasi dari akar dengan margin sebagai batas."""
    vertices = np.asarray(mesh.vertices, float)
    faces = np.asarray(mesh.faces)
    edge_len = float(np.median(np.linalg.norm(vertices[faces[:, 0]] - vertices[faces[:, 1]], axis=1)))
    margin = _resample_closed(np.asarray(margin_points, float), 0.25 * edge_len)
    _, band, _ = MeshProjector(mesh).closest(margin)
    band_faces = np.zeros(len(faces), dtype=bool)
    band_faces[band] = True
    # Satu cincin face di sekitar pita supaya batasnya pasti menutup, juga kalau margin lewat tepat di vertex.
    band_vertices = np.zeros(len(vertices), dtype=bool)
    band_vertices[faces[band_faces].ravel()] = True
    band_faces |= band_vertices[faces].any(axis=1)

    adjacency = _face_adjacency(faces).tocsr()
    keep = ~band_faces
    sub = adjacency[keep][:, keep]
    count, labels = connected_components(sub, directed=False)
    if count < 2:
        raise InsertionError("margin tidak memisahkan mesh menjadi preparasi dan akar")
    # Sisi preparasi: permukaan dekat margin bergerak KE DALAM (ledge shoulder, busur chamfer, dinding yang
    # menyempit); sisi akar tetap di lingkar margin atau keluar (emergence). Kriteria "di dalam lingkar" untuk
    # seluruh komponen gagal pada overhang yang melewati margin, karena dinding akar tepat di lingkar dan tutup
    # dasar juga di dalam lingkar.
    center, e1, e2, _ = _plane_frame(margin)
    flat_margin = np.stack([(margin - center) @ e1, (margin - center) @ e2], axis=1)
    margin_tree = cKDTree(margin)
    kept_idx = np.flatnonzero(keep)
    areas = 0.5 * np.linalg.norm(face_normals(vertices, faces, normalize=False), axis=1)
    near_mm = max(1.0, 4 * edge_len)
    best, best_score = None, -np.inf
    for label in range(count):
        idx = kept_idx[labels == label]
        if areas[idx].sum() < 0.01 * areas.sum():
            continue
        vid = np.unique(faces[idx].ravel())
        dist, nearest = margin_tree.query(vertices[vid])
        near = dist <= near_mm
        if not near.any():
            continue
        rel = vertices[vid[near]] - center
        r_vertex = np.hypot(rel @ e1, rel @ e2)
        r_margin = np.linalg.norm(flat_margin[nearest[near]], axis=1)
        score = float(-np.median(r_vertex - r_margin))  # > 0: ke dalam
        if score > best_score:
            best, best_score = idx, score
    if best is None or best_score <= 0.0:
        raise InsertionError("daerah preparasi tidak jelas: tidak ada sisi margin yang menyempit ke dalam")
    prep_faces = np.zeros(len(faces), dtype=bool)
    prep_faces[best] = True
    prep_vertices = np.zeros(len(vertices), dtype=bool)
    prep_vertices[faces[prep_faces].ravel()] = True
    return PrepRegion(prep_faces, prep_vertices, band_faces, margin)


# 2. Geometri yang dihaluskan -------------------------------------------------------------------------

@dataclass
class InsertionContext:
    """Analisis mesh yang dipakai ulang setiap kali sumbu diubah (peta undercut diperbarui langsung)."""

    vertices: np.ndarray
    faces: np.ndarray
    region: PrepRegion
    smooth_vertices: np.ndarray
    smooth_vertex_normals: np.ndarray
    smooth_face_normals: np.ndarray
    face_areas: np.ndarray
    noise_sigma_mm: float
    start_axis: np.ndarray  # luas vektor preparasi
    params: InsertionParams = field(default_factory=InsertionParams)

    @property
    def margin(self) -> np.ndarray:
        return self.region.margin


def insertion_context(mesh: MeshData, margin_points: np.ndarray,
                      params: InsertionParams = InsertionParams()) -> InsertionContext:
    vertices = np.asarray(mesh.vertices, float)
    faces = np.asarray(mesh.faces)
    region = prep_region(mesh, margin_points)
    normals = vertex_normals(vertices, faces)
    sigma = estimate_noise_sigma(vertices, faces, normals)
    radius = max(params.smooth_radius_min_mm, params.smooth_radius_per_noise * sigma)
    _, _, smooth_normals = crease_score(vertices, normals, radius)
    face_n = smooth_normals[faces].sum(axis=1)
    face_n /= np.maximum(np.linalg.norm(face_n, axis=1, keepdims=True), 1e-12)

    # Posisi dihaluskan: rata-rata berbobot Gauss tetangga dalam radius (penyusutan ~ r^2 kappa / 8, kecil
    # dibanding kedalaman undercut yang diukur, dan seragam di dinding).
    tree = cKDTree(vertices)
    pairs = tree.sparse_distance_matrix(tree, radius, output_type="coo_matrix")
    i = np.concatenate([pairs.row, np.arange(len(vertices))])
    j = np.concatenate([pairs.col, np.arange(len(vertices))])
    d = np.concatenate([pairs.data, np.zeros(len(vertices))])
    w = np.exp(-(d / (0.5 * radius)) ** 2)
    wsum = np.bincount(i, w, len(vertices))
    smooth_vertices = np.stack([np.bincount(i, w * vertices[j, k], len(vertices)) for k in range(3)], axis=1)
    smooth_vertices /= wsum[:, None]

    raw = face_normals(vertices, faces, normalize=False)
    areas = 0.5 * np.linalg.norm(raw, axis=1)
    start = raw[region.faces].sum(axis=0)
    start /= np.linalg.norm(start)
    return InsertionContext(vertices, faces, region, smooth_vertices, smooth_normals, face_n, areas, sigma, start,
                            params)


# 3. Kedalaman undercut -------------------------------------------------------------------------------

def _frame(axis: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    helper = np.array([1.0, 0.0, 0.0]) if abs(axis[0]) < 0.9 else np.array([0.0, 1.0, 0.0])
    u = np.cross(axis, helper)
    u /= np.linalg.norm(u)
    return u, np.cross(axis, u)


class ShadowField:
    """Uji bayangan sejajar sumbu terhadap segitiga preparasi (eksak, bukan pendekatan per sektor).

    Untuk titik x, permukaan pertama di atasnya (lebih tinggi dari x lebih dari height_eps) menentukan
    keadaannya: tidak ada = bebas; segitiga membelakangi sumbu (sisi bawah overhang) = x di luar material
    tetapi terbayang; segitiga menghadap sumbu = x di dalam material (misalnya di bawah ledge ber-scallop
    yang naik), bukan undercut. Kedalaman undercut di p = jarak berjalan keluar tegak lurus sumbu selama
    titiknya terbayang: itu tebal block-out sejajar sumbu di p. Penampang die tidak harus berbentuk bintang.
    """

    def __init__(self, triangles: np.ndarray, axis: np.ndarray, center: np.ndarray, height_eps: float,
                 step: float, max_depth: float):
        self.axis = axis / np.linalg.norm(axis)
        self.u, self.v = _frame(self.axis)
        self.center = center
        self.height_eps = height_eps
        self.step = step
        self.max_depth = max_depth
        rel = triangles - center
        self.tri_xy = np.stack([rel @ self.u, rel @ self.v], axis=-1)  # (F, 3, 2)
        self.tri_h = rel @ self.axis  # (F, 3)
        # Segitiga yang hampir sejajar sumbu (dinding vertikal) tidak bisa menutupi garis sejajar sumbu.
        e1, e2 = self.tri_xy[:, 1] - self.tri_xy[:, 0], self.tri_xy[:, 2] - self.tri_xy[:, 0]
        self.det = e1[:, 0] * e2[:, 1] - e1[:, 1] * e2[:, 0]
        self.tri_top = self.tri_h.max(axis=1)
        self._build_grid()

    def _build_grid(self) -> None:
        """Grid sel 2D: setiap segitiga didaftarkan ke semua sel yang dilewati bounding box-nya."""
        lo, hi = self.tri_xy.min(axis=1), self.tri_xy.max(axis=1)
        extent = np.max(hi - lo, axis=1)
        self.cell = max(float(np.median(extent)), 1e-3)
        self.origin = lo.min(axis=0)
        c0 = np.floor((lo - self.origin) / self.cell).astype(np.int64)
        c1 = np.floor((hi - self.origin) / self.cell).astype(np.int64)
        self.ncols = int(c1[:, 0].max()) + 2
        span = (c1 - c0 + 1)
        counts = span[:, 0] * span[:, 1]
        tri = np.repeat(np.arange(len(lo)), counts)
        offset = np.arange(counts.sum()) - np.repeat(np.cumsum(counts) - counts, counts)
        sx = np.repeat(span[:, 0], counts)
        cx = np.repeat(c0[:, 0], counts) + offset % sx
        cy = np.repeat(c0[:, 1], counts) + offset // sx
        key = cy * self.ncols + cx
        order = np.argsort(key, kind="stable")
        self.cell_key = key[order]
        self.cell_tri = tri[order]

    def _candidates(self, xy: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        c = np.floor((xy - self.origin) / self.cell).astype(np.int64)
        key = c[:, 1] * self.ncols + c[:, 0]
        valid = (c[:, 0] >= 0) & (c[:, 1] >= 0) & (c[:, 0] < self.ncols)
        start = np.searchsorted(self.cell_key, key, side="left")
        stop = np.searchsorted(self.cell_key, key, side="right")
        counts = np.where(valid, stop - start, 0)
        q = np.repeat(np.arange(len(xy)), counts)
        offset = np.arange(counts.sum()) - np.repeat(np.cumsum(counts) - counts, counts)
        f = self.cell_tri[np.repeat(start, counts) + offset]
        return q, f

    def to_local(self, points: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        rel = np.asarray(points, float) - self.center
        return np.stack([rel @ self.u, rel @ self.v], axis=1), rel @ self.axis

    def first_hit(self, xy: np.ndarray, h: np.ndarray) -> np.ndarray:
        """Keadaan per titik: 0 bebas, -1 terbayang (permukaan pertama di atas membelakangi sumbu),
        +1 di dalam material (permukaan pertama di atas menghadap sumbu)."""
        state = np.zeros(len(xy), dtype=np.int8)
        if not len(xy):
            return state
        q, f = self._candidates(xy)
        if not len(q):
            return state
        # Hanya segitiga yang titik tertingginya di atas titik kueri yang bisa membayangi.
        good = (np.abs(self.det[f]) > 1e-14) & (self.tri_top[f] > h[q] + self.height_eps)
        q, f = q[good], f[good]
        det = self.det[f]
        a = self.tri_xy[f, 0]
        e1 = self.tri_xy[f, 1] - a
        e2 = self.tri_xy[f, 2] - a
        d = xy[q] - a
        l1 = (d[:, 0] * e2[:, 1] - d[:, 1] * e2[:, 0]) / det
        l2 = (e1[:, 0] * d[:, 1] - e1[:, 1] * d[:, 0]) / det
        l0 = 1 - l1 - l2
        inside = (l0 >= -1e-9) & (l1 >= -1e-9) & (l2 >= -1e-9)
        height = l0 * self.tri_h[f, 0] + l1 * self.tri_h[f, 1] + l2 * self.tri_h[f, 2]
        hit = inside & (height > h[q] + self.height_eps)
        q, f, height = q[hit], f[hit], height[hit]
        if not len(q):
            return state
        order = np.lexsort((height, q))  # per titik, segitiga terendah di atasnya lebih dulu
        q, f = q[order], f[order]
        first = np.concatenate([[True], q[1:] != q[:-1]])
        # det > 0: segitiga menghadap sumbu (frame u, v, sumbu bertangan kanan dan mesh berorientasi keluar).
        state[q[first]] = np.where(self.det[f[first]] > 0, 1, -1)
        return state

    def shadowed(self, xy: np.ndarray, h: np.ndarray) -> np.ndarray:
        return self.first_hit(xy, h) == -1

    def depth(self, points: np.ndarray) -> np.ndarray:
        """Tebal block-out di setiap titik permukaan. Titik yang tidak terbayang di tempatnya diuji lagi satu
        langkah keluar: titik di dinding overhang itu sendiri (dan di sudut cekung di kakinya) berada di dalam
        material tepat di atasnya, tetapi ruang tepat di luarnya terbayang. Tidak memakai normal, karena normal
        yang dihaluskan di sudut cekung tercampur dengan normal ledge."""
        xy, h = self.to_local(points)
        depth = np.zeros(len(xy))
        radial_all = xy / np.maximum(np.linalg.norm(xy, axis=1, keepdims=True), 1e-12)
        start = np.zeros(len(xy))
        is_shadowed = self.shadowed(xy, h)
        probe = np.flatnonzero(~is_shadowed)
        outside = self.shadowed(xy[probe] + radial_all[probe] * self.step, h[probe])
        is_shadowed[probe[outside]] = True
        start[probe[outside]] = self.step
        active = np.flatnonzero(is_shadowed)
        if not len(active):
            return depth
        radial = radial_all[active]
        pa, ha = xy[active], h[active]

        def covered_at(idx, dist):
            return self.shadowed(pa[idx] + radial[idx] * dist[:, None], ha[idx])

        # Langkah berlipat selama masih terbayang, lalu bagi dua sampai selang <= step.
        lo = start[active].copy()
        hi = lo + self.step
        open_ = np.ones(len(active), dtype=bool)
        while open_.any():
            idx = np.flatnonzero(open_)
            still = covered_at(idx, hi[idx]) & (hi[idx] < self.max_depth)
            lo[idx[still]] = hi[idx[still]]
            hi[idx[still]] = np.minimum(2 * hi[idx[still]], self.max_depth)
            open_[idx[~still]] = False
        while True:
            idx = np.flatnonzero(hi - lo > self.step)
            if not len(idx):
                break
            mid = 0.5 * (lo[idx] + hi[idx])
            still = covered_at(idx, mid)
            lo[idx[still]] = mid[still]
            hi[idx[~still]] = mid[~still]
        depth[active] = 0.5 * (lo + hi)  # titik tengah selang terakhir
        return depth


def shadow_field(context: InsertionContext, axis) -> ShadowField:
    axis = np.asarray(axis, float)
    p = context.params
    edge_len = float(np.median(np.linalg.norm(
        context.vertices[context.faces[:, 0]] - context.vertices[context.faces[:, 1]], axis=1)))
    triangles = context.smooth_vertices[context.faces[context.region.faces]]
    return ShadowField(triangles, axis, context.margin.mean(axis=0), p.shadow_height_eps_mm,
                       step=p.depth_step_mm, max_depth=max(3.0, 10 * edge_len))


def depth_floor(context: InsertionContext) -> float:
    """Kedalaman di bawah ini dianggap derau (bukan undercut)."""
    p = context.params
    return max(p.depth_floor_min_mm, p.depth_floor_per_noise * context.noise_sigma_mm)


@dataclass
class UndercutMap:
    axis: np.ndarray
    vertex_depth: np.ndarray  # per vertex mesh (0 di luar preparasi), mm
    undercut_faces: np.ndarray  # bool per face
    margin_depth: np.ndarray  # per titik margin rapat, mm
    back_area_mm2: float  # luas face preparasi yang membelakangi sumbu (normal dihaluskan)


def undercut_map(context: InsertionContext, axis) -> UndercutMap:
    """Peta undercut untuk satu sumbu: dipanggil ulang setiap kali sumbu diubah."""
    axis = np.asarray(axis, float)
    axis = axis / np.linalg.norm(axis)
    field_ = shadow_field(context, axis)
    depth = np.zeros(len(context.vertices))
    prep_v = context.region.vertices
    depth[prep_v] = field_.depth(context.smooth_vertices[prep_v])
    floor = depth_floor(context)
    depth[depth < floor] = 0.0
    facing_away = context.smooth_face_normals @ axis < 0
    under = context.region.faces & facing_away & (depth[context.faces].max(axis=1) > 0)
    back = float(context.face_areas[context.region.faces & facing_away].sum())
    return UndercutMap(axis, depth, under, field_.depth(context.margin), back)


# 4. Sumbu default dan keraguan -----------------------------------------------------------------------

def _cone_directions(axis: np.ndarray, cone_deg: float, step_deg: float) -> tuple[np.ndarray, np.ndarray]:
    """Grid arah dalam kerucut di sekitar axis (koordinat sudut kecil), plus indeks grid 2D."""
    u, v = _frame(axis)
    steps = np.arange(-cone_deg, cone_deg + 1e-9, step_deg)
    gx, gy = np.meshgrid(steps, steps, indexing="ij")
    inside = np.hypot(gx, gy) <= cone_deg + 1e-9
    ax, ay = np.radians(gx[inside]), np.radians(gy[inside])
    dirs = axis[None] + np.tan(ax)[:, None] * u[None] + np.tan(ay)[:, None] * v[None]
    dirs /= np.linalg.norm(dirs, axis=1, keepdims=True)
    grid = np.stack(np.nonzero(inside), axis=1)
    return dirs, grid


def back_facing_area(context: InsertionContext, directions: np.ndarray) -> np.ndarray:
    """Luas face preparasi yang membelakangi setiap arah (normal dihaluskan), mm^2."""
    n = context.smooth_face_normals[context.region.faces]
    a = context.face_areas[context.region.faces]
    out = np.empty(len(directions))
    for k in range(0, len(directions), 256):
        dots = n @ directions[k:k + 256].T
        out[k:k + 256] = a @ (dots < 0)
    return out


@dataclass
class AxisResult:
    axis: np.ndarray
    start_axis: np.ndarray
    doubtful: bool
    reasons: list  # (nama bahasa Inggris untuk UI, penjelasan)
    alternatives: list  # sumbu kandidat lain yang hampir sama baiknya
    map: UndercutMap
    candidates: np.ndarray = field(repr=False, default=None)
    candidate_area: np.ndarray = field(repr=False, default=None)


def check_axis(context: InsertionContext, axis, alternatives: list | None = None) -> tuple[bool, list, UndercutMap]:
    """Keraguan untuk sumbu yang sedang dipakai (otomatis atau dari pengguna)."""
    umap = undercut_map(context, axis)
    p = context.params
    reasons = []
    shadow_tol = max(p.margin_shadow_min_mm, p.margin_shadow_per_noise * context.noise_sigma_mm)
    shadowed = umap.margin_depth > shadow_tol
    if shadowed.any():
        reasons.append(("margin line lies in an undercut",
                        f"{shadowed.mean():.0%} titik margin terbayang, sampai {1000 * umap.margin_depth.max():.0f} um"))
    if alternatives:
        reasons.append(("another axis is almost as good",
                        f"{len(alternatives)} arah lain yang terpisah >= {p.ambiguity_deg:g} derajat hampir sama baiknya"))
    return bool(reasons), reasons, umap


def default_axis(context: InsertionContext) -> AxisResult:
    p = context.params
    start = context.start_axis
    dirs, grid = _cone_directions(start, p.cone_deg, p.grid_step_deg)
    area = back_facing_area(context, dirs)
    prep_area = float(context.face_areas[context.region.faces].sum())
    near = area <= area.min() + p.near_optimal_area_fraction * prep_area
    near_idx = np.flatnonzero(near)
    angles = np.degrees(np.arccos(np.clip(dirs @ start, -1, 1)))
    chosen = int(near_idx[np.argmin(angles[near_idx])])

    # Kelompok arah hampir optimal yang terhubung di grid; kelompok lain yang jauh = kandidat sumbu lain.
    lookup = {tuple(g): k for k, g in enumerate(grid)}
    rows, cols = [], []
    for k in near_idx:
        gx, gy = grid[k]
        for dx, dy in ((1, 0), (0, 1), (1, 1), (1, -1)):
            m = lookup.get((gx + dx, gy + dy))
            if m is not None and near[m]:
                rows.append(k)
                cols.append(m)
    graph = coo_matrix((np.ones(len(rows)), (rows, cols)), shape=(len(dirs), len(dirs)))
    _, labels = connected_components(graph, directed=False)
    own = labels[chosen]
    alternatives = []
    for label in np.unique(labels[near_idx]):
        if label == own:
            continue
        members = near_idx[labels[near_idx] == label]
        best = int(members[np.argmin(area[members])])
        if np.degrees(np.arccos(np.clip(dirs[best] @ dirs[chosen], -1, 1))) >= p.ambiguity_deg:
            alternatives.append(dirs[best])
    doubtful, reasons, umap = check_axis(context, dirs[chosen], alternatives)
    return AxisResult(dirs[chosen], start, doubtful, reasons, alternatives, umap, dirs, area)


# 5. Block-out ----------------------------------------------------------------------------------------

@dataclass
class BlockOut:
    """Permukaan die hasil block-out sejajar sumbu (input §5.3 spacer)."""

    mesh: MeshData
    axis: np.ndarray
    free_zone_mm: float
    moved: np.ndarray  # bool per vertex: digeser keluar
    displacement: np.ndarray  # mm per vertex


def block_out(context: InsertionContext, axis, free_zone_mm: float, max_passes: int = 16) -> BlockOut:
    """Block-out sejajar sumbu pada mesh MENTAH (input §5.3 spacer).

    Peta undercut untuk tampilan memakai posisi yang dihaluskan dan ambang derau supaya tidak berbintik, tetapi
    block-out adalah geometri yang benar-benar dipakai crown, jadi dihitung dari segitiga mentah tanpa ambang:
    setiap vertex preparasi yang terbayang digeser keluar tegak lurus sumbu sejauh kedalaman bayangannya, lalu
    diulang (segitiga di antara vertex yang digeser bisa menyisakan bayangan kecil) sampai tidak ada yang
    bergeser lagi atau max_passes tercapai. Vertex dalam free_zone_mm dari margin line tidak digeser
    ("Don't block out zone near prepline" exocad), jadi bayangan di zona itu sengaja dibiarkan.
    """
    if free_zone_mm < 0:
        raise InsertionError("zona tanpa block-out wajib >= 0")
    prep_v = np.flatnonzero(context.region.vertices)
    near_margin = cKDTree(context.margin).query(context.vertices[prep_v])[0] <= free_zone_mm
    return block_out_mesh(MeshData(context.vertices, context.faces), context.region.faces, prep_v[~near_margin],
                          axis, context.margin.mean(axis=0), free_zone_mm, context.params, max_passes)


def block_out_mesh(mesh: MeshData, caster_faces: np.ndarray, movable: np.ndarray, axis, center: np.ndarray,
                   free_zone_mm: float, params: InsertionParams = InsertionParams(), max_passes: int = 16) -> BlockOut:
    """Block-out sejajar sumbu pada mesh apa pun: vertex `movable` yang terbayang oleh face `caster_faces` digeser
    keluar tegak lurus sumbu (menjauhi garis sumbu lewat `center`), diulang sampai tidak ada yang bergeser.
    Dipakai untuk die (§5.2) dan untuk block-out kedua pada permukaan dalam crown setelah cement gap (§5.3)."""
    axis = np.asarray(axis, float)
    axis = axis / np.linalg.norm(axis)
    vertices = np.asarray(mesh.vertices, float).copy()
    faces = np.asarray(mesh.faces)
    movable = np.asarray(movable)
    displacement = np.zeros(len(vertices))
    tri_faces = faces[caster_faces]
    for _ in range(max_passes):
        field_ = ShadowField(vertices[tri_faces], axis, center, params.shadow_height_eps_mm, params.depth_step_mm, 3.0)
        push = field_.depth(vertices[movable])
        sel = push > 0
        if not sel.any():
            break
        idx = movable[sel]
        rel = vertices[idx] - center
        radial = rel - (rel @ axis)[:, None] * axis
        radial /= np.maximum(np.linalg.norm(radial, axis=1, keepdims=True), 1e-12)
        vertices[idx] += push[sel][:, None] * radial
        displacement[idx] += push[sel]
    moved = displacement > 0
    return BlockOut(MeshData(vertices, faces.copy()), axis, free_zone_mm, moved, displacement)


def residual_shadow(context: InsertionContext, blocked: BlockOut, margin_clearance_mm: float = 0.05) -> float:
    """Kedalaman bayangan terbesar yang tersisa pada mesh hasil block-out, di luar zona dekat margin."""
    p = context.params
    v = blocked.mesh.vertices
    field_ = ShadowField(v[context.faces[context.region.faces]], blocked.axis, context.margin.mean(axis=0),
                         p.shadow_height_eps_mm, p.depth_step_mm, 3.0)
    prep = np.flatnonzero(context.region.vertices)
    far = cKDTree(context.margin).query(v[prep])[0] > blocked.free_zone_mm + margin_clearance_mm
    depth = field_.depth(v[prep[far]])
    return float(depth.max()) if len(depth) else 0.0
