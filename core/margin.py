# SPDX-License-Identifier: GPL-3.0-or-later
"""Margin semi-otomatis berbasis curvature klasik (docs/PHASE2.md §5.1).

Alur:
1. Skor crease per vertex: variasi normal di sekitar vertex (nilai eigen terbesar kovarians normal dalam
   radius r), hanya untuk daerah cembung. Margin preparasi adalah tepi cembung yang tajam.
2. Jalur tertutup berbiaya minimum yang melewati titik klik: graf edge mesh dengan bobot
   panjang x (eps + (1 - skor)^p). Dua jalur dari klik ke titik terjauh di cincin crease yang sama, yang
   kedua dipaksa lewat sisi lain die; gabungannya adalah loop. Tidak perlu sumbu die.
3. Penyempurnaan: setiap titik sampel jalur dipindahkan ke garis potong dua bidang yang di-fit ke kedua
   sisi crease (titik tetangga dikelompokkan menurut normal), jadi posisinya tidak terikat ke vertex mesh.
4. Kurva: titik hasil dihaluskan sepanjang busur lalu diambil titik kontrol berjarak tetap; kurva akhir adalah
   spline kubik periodik yang melewati titik kontrol. Titik kontrol bisa digeser (diproyeksikan kembali ke
   permukaan) atau dihapus.

Bukan meniru metode ML (keputusan K5 Fase 2).
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace

import numpy as np
from scipy.interpolate import CubicSpline
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import dijkstra
from scipy.spatial import cKDTree

from .geometry import MeshProjector, unique_edges, vertex_normals
from .mesh_data import MeshData


@dataclass(frozen=True)
class MarginParams:
    """Parameter algoritma (bukan klinis). Nilai awal dari spike S1 terhadap data sintetis; lihat PHASE2.md."""

    # Radius curvature dan radius fit = max(minimum, faktor x sigma derau terestimasi), jadi otomatis membesar
    # pada scan berderau. Faktor dan minimum dipilih dari sapuan spike S1 (PHASE2.md §8).
    curvature_radius_min_mm: float = 0.35
    curvature_radius_per_noise: float = 12.0
    refine_radius_min_mm: float = 0.6
    refine_radius_per_noise: float = 12.0
    ridge_ratio: float = 0.35
    far_min_score: float = 0.5
    band_rings: int = 2
    cost_eps: float = 0.02
    cost_power: float = 2.0
    refine_spacing_mm: float = 0.15
    min_crease_angle_deg: float = 30.0
    smooth_sigma_mm: float = 0.4
    control_spacing_mm: float = 1.0
    # Pengaman. Ambang derau: keputusan maintainer berdasarkan presisi terburuk enam scanner intraoral untuk
    # preparasi single crown di Diker & Tak 2020 (60 um, Planmeca Emerald); lihat PHASE2.md §5.1.
    max_noise_mm: float = 0.060
    check_noise: bool = True
    # Ambang kewajaran kurva (ambang algoritma, bukan klinis), dari sapuan pada data sintetis, PHASE2.md §5.1.
    min_refined_fraction: float = 0.75
    max_click_distance_mm: float = 1.0
    max_control_gap_ratio: float = 2.5
    girth_ratio_range: tuple[float, float] = (0.90, 1.12)
    max_out_of_plane_ratio: float = 0.35
    # Penanda segmen meragukan (merah di viewport), dari sapuan pada set tuning dan tuning2 saja, PHASE2.md §5.1.
    review_max_residual_mm: float = 0.08
    review_min_angle_deg: float = 30.0
    review_min_run: int = 2


class MarginError(ValueError):
    """Margin tidak bisa dideteksi atau diedit (misalnya tidak ada jalur yang melingkari die)."""


class MarginNoiseError(MarginError):
    """Scan terlalu berderau untuk deteksi otomatis; margin harus digambar manual."""

    def __init__(self, message: str, sigma_mm: float, limit_mm: float):
        super().__init__(message)
        self.sigma_mm = sigma_mm
        self.limit_mm = limit_mm


class MarginPlausibilityError(MarginError):
    """Kurva hasil deteksi tidak wajar (misalnya melompat jauh, tidak menutup, atau ukurannya tidak cocok
    dengan die), jadi ditolak alih-alih dikembalikan tanpa pesan."""

    def __init__(self, message: str, failed: list[str] | None = None, metrics: dict | None = None):
        super().__init__(message)
        self.failed = failed or []  # nama metrik yang gagal (bahasa Inggris, untuk pesan UI)
        self.metrics = metrics or {}


# 1. Skor crease ------------------------------------------------------------------------------------

def crease_score(vertices: np.ndarray, normals: np.ndarray, radius: float) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """(skor 0..1, kecembungan, normal halus) per vertex.

    Skor = nilai eigen terbesar kovarians normal berbobot Gauss dalam radius, dinormalisasi ke persentil 99.
    Kecembungan = rata-rata berbobot (p_j - p_i) . n_i / r; negatif berarti tetangga di bawah bidang
    singgung (cembung). Normal halus = rata-rata normal berbobot yang sama, dipakai untuk mengelompokkan
    sisi crease karena jauh lebih tahan derau daripada normal vertex.
    """
    tree = cKDTree(vertices)
    pairs = tree.sparse_distance_matrix(tree, radius, output_type="coo_matrix")
    i, j, d = pairs.row, pairs.col, pairs.data
    self_pairs = np.arange(len(vertices))
    i = np.concatenate([i, self_pairs])
    j = np.concatenate([j, self_pairs])
    d = np.concatenate([d, np.zeros(len(vertices))])
    w = np.exp(-(d / (0.5 * radius)) ** 2)

    n = len(vertices)
    wsum = np.bincount(i, w, n)
    nj = normals[j]
    mean = np.stack([np.bincount(i, w * nj[:, k], n) for k in range(3)], axis=1) / wsum[:, None]
    second = np.zeros((n, 3, 3))
    for a in range(3):
        for b in range(a, 3):
            value = np.bincount(i, w * nj[:, a] * nj[:, b], n) / wsum
            second[:, a, b] = second[:, b, a] = value
    cov = second - mean[:, :, None] * mean[:, None, :]
    eig = np.linalg.eigvalsh(cov)[:, -1]

    offset = np.einsum("ij,ij->i", vertices[j] - vertices[i], normals[i])
    convexity = np.bincount(i, w * offset, n) / wsum / radius

    scale = np.percentile(eig, 99)
    score = np.clip(eig / scale, 0.0, 1.0) if scale > 0 else np.zeros(n)
    score[convexity >= 0] *= 0.1  # crease cekung (sudut dalam shoulder, busur chamfer) bukan margin
    smooth = mean / np.maximum(np.linalg.norm(mean, axis=1, keepdims=True), 1e-12)
    return score, convexity, smooth


# 2. Jalur tertutup ---------------------------------------------------------------------------------

def estimate_noise_sigma(vertices: np.ndarray, faces: np.ndarray, normals: np.ndarray) -> float:
    """Perkiraan sigma derau sepanjang normal (mm) dari operator umbrella.

    Perpindahan vertex dari rata-rata tetangga satu cincinnya, diproyeksikan ke normal, didominasi derau di
    permukaan halus (kontribusi kelengkungan jauh lebih kecil pada ukuran edge scan). MAD membuatnya tahan
    terhadap crease. Untuk derau i.i.d. sigma, perpindahan itu bersigma sigma * sqrt(1 + 1/k).
    """
    edges = unique_edges(faces)
    n = len(vertices)
    a, b = edges[:, 0], edges[:, 1]
    degree = np.bincount(a, minlength=n) + np.bincount(b, minlength=n)
    total = np.zeros_like(vertices)
    np.add.at(total, a, vertices[b])
    np.add.at(total, b, vertices[a])
    valid = degree > 0
    umbrella = np.einsum("ij,ij->i", vertices[valid] - total[valid] / degree[valid, None], normals[valid])
    mad = 1.4826 * np.median(np.abs(umbrella - np.median(umbrella)))
    k = np.median(degree[valid])
    return float(mad / np.sqrt(1.0 + 1.0 / k))


def _graph(n: int, edges: np.ndarray, cost: np.ndarray):
    return coo_matrix((cost, (edges[:, 0], edges[:, 1])), shape=(n, n)).tocsr()


def _walk(pred: np.ndarray, source: int, target: int) -> np.ndarray:
    path = [target]
    while path[-1] != source:
        step = pred[path[-1]]
        if step < 0:
            raise MarginError("jalur terputus")
        path.append(step)
    return np.array(path[::-1])


def closed_path_two_way(
    vertices: np.ndarray,
    edges: np.ndarray,
    cost: np.ndarray,
    seed: int,
    ridge_ratio: float = 0.35,
    band_rings: int = 2,
    far_candidates: np.ndarray | None = None,
) -> np.ndarray:
    """Jalur tertutup berbiaya minimum melalui seed, tanpa memerlukan sumbu die.

    1. Dijkstra dari seed. Vertex "di punggungan" = yang biaya jalurnya <= ridge_ratio x jarak Euclid-nya
       dari seed (di punggungan biaya per mm kecil; menyeberang permukaan biasa berbiaya sekitar 1 per mm).
    2. Titik jauh f = vertex punggungan terjauh (Euclid) dari seed, kira-kira di seberang cincin margin.
       Kalau far_candidates diberikan, f hanya dipilih dari vertex itu (vertex crease): kriteria punggungan
       sendiri mengizinkan simpangan sebanding jarak, sehingga tanpa batasan ini f bisa jatuh 1-2 mm di dinding
       aksial di atas puncak scallop dalam dan kedua jalur ikut naik ke sana (PHASE2.md §5.1).
    3. Jalur 1 = jalur termurah seed -> f.
    4. Jalur 2 = jalur termurah seed -> f setelah jalur 1 beserta band_rings cincin tetangganya diblokir
       (kecuali dekat seed dan f), sehingga jalur 2 harus lewat sisi lain die.
    5. Loop = jalur 1 + jalur 2 dibalik.
    """
    n = len(vertices)
    graph = _graph(n, edges, cost)
    dist, pred = dijkstra(graph, directed=False, indices=seed, return_predecessors=True)
    euclid = np.linalg.norm(vertices - vertices[seed], axis=1)
    ridge = np.isfinite(dist) & (dist <= ridge_ratio * euclid)
    if far_candidates is not None:
        ridge &= far_candidates
    edge_len = np.median(np.linalg.norm(vertices[edges[:, 0]] - vertices[edges[:, 1]], axis=1))
    if not ridge.any() or euclid[ridge].max() < 20 * edge_len:
        raise MarginError("crease di sekitar titik klik terlalu pendek untuk menjadi margin")
    far = int(np.flatnonzero(ridge)[np.argmax(euclid[ridge])])
    path1 = _walk(pred, seed, far)

    blocked = np.zeros(n, dtype=bool)
    blocked[path1] = True
    adjacency = _graph(n, edges, np.ones(len(edges)))
    adjacency = adjacency + adjacency.T
    for _ in range(band_rings):
        blocked |= (adjacency @ blocked.astype(float)) > 0
    keep_out = 4 * edge_len  # biarkan jalur 2 berangkat dari seed dan tiba di f
    near_ends = (euclid < keep_out) | (np.linalg.norm(vertices - vertices[far], axis=1) < keep_out)
    blocked &= ~near_ends
    allowed = ~(blocked[edges[:, 0]] | blocked[edges[:, 1]])
    graph2 = _graph(n, edges[allowed], cost[allowed])
    dist2, pred2 = dijkstra(graph2, directed=False, indices=seed, return_predecessors=True)
    if not np.isfinite(dist2[far]):
        raise MarginError("tidak ada jalur kedua di sisi lain die; margin tidak membentuk cincin tertutup")
    path2 = _walk(pred2, seed, far)
    loop = np.concatenate([path1, path2[::-1][1:-1]])
    _, first = np.unique(loop, return_index=True)
    if len(first) < 0.9 * len(loop):
        raise MarginError("jalur kedua menumpang jalur pertama; margin tidak membentuk cincin tertutup")
    return loop


def loop_axis(points: np.ndarray) -> np.ndarray:
    """Normal bidang fit dari loop margin (perkiraan kasar sumbu insersi, untuk diagnosis)."""
    centered = points - points.mean(axis=0)
    return np.linalg.svd(centered, full_matrices=False)[2][-1]


# 3. Penyempurnaan crease ---------------------------------------------------------------------------

def _resample_closed(points: np.ndarray, spacing: float) -> np.ndarray:
    closed = np.vstack([points, points[:1]])
    seg = np.linalg.norm(np.diff(closed, axis=0), axis=1)
    s = np.concatenate([[0.0], np.cumsum(seg)])
    count = max(int(s[-1] / spacing), 8)
    target = np.linspace(0.0, s[-1], count, endpoint=False)
    return np.stack([np.interp(target, s, closed[:, k]) for k in range(3)], axis=1)


def _fit_plane(points: np.ndarray, weights: np.ndarray, orient: np.ndarray) -> tuple[np.ndarray, float]:
    centroid = np.average(points, axis=0, weights=weights)
    _, _, vt = np.linalg.svd((points - centroid) * np.sqrt(weights)[:, None], full_matrices=False)
    normal = vt[-1] if vt[-1] @ orient >= 0 else -vt[-1]
    return normal, float(normal @ centroid)


def _plane_intersection(planes, q: np.ndarray, min_sin: float) -> tuple[np.ndarray, np.ndarray] | None:
    (n0, d0), (n1, d1) = planes
    direction = np.cross(n0, n1)
    length = np.linalg.norm(direction)
    if length < min_sin:
        return None
    direction /= length
    # Titik di garis potong yang paling dekat ke q: selesaikan [n0; n1; dir] x = [d0; d1; dir.q].
    point = np.linalg.solve(np.stack([n0, n1, direction]), np.array([d0, d1, direction @ q]))
    return point, direction


def _tangent_plane_at(points: np.ndarray, weights: np.ndarray, origin: np.ndarray, direction: np.ndarray,
                      orient: np.ndarray) -> tuple[np.ndarray, float] | None:
    """Bidang singgung di titik crease dari kuadrik z = a + bx + cy + dx^2 + exy + fy^2 yang di-fit ke satu sisi.

    Frame lokal: x sepanjang crease, z searah normal rata-rata sisi itu, asal di titik crease. Bidang singgung
    di (0, 0) lebih tepat daripada bidang sekan kalau sisi itu melengkung (misalnya busur chamfer).
    """
    if (weights > 0.05).sum() < 8:
        return None
    ez = orient - direction * (orient @ direction)
    if np.linalg.norm(ez) < 1e-6:
        return None
    ez /= np.linalg.norm(ez)
    ey = np.cross(ez, direction)
    rel = points - origin
    x, y, z = rel @ direction, rel @ ey, rel @ ez
    design = np.stack([np.ones_like(x), x, y, x * x, x * y, y * y], axis=1)
    sw = np.sqrt(weights)
    coef, *_ = np.linalg.lstsq(design * sw[:, None], z * sw, rcond=None)
    a, b, c = coef[:3]
    normal = -b * direction - c * ey + ez
    normal /= np.linalg.norm(normal)
    point = origin + a * ez
    return normal, float(normal @ point)


def refine_on_crease(
    points: np.ndarray,
    vertices: np.ndarray,
    smooth_normals: np.ndarray,
    tree: cKDTree,
    radius: float,
    min_angle_deg: float,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Pindahkan setiap titik ke garis potong dua bidang yang di-fit ke kedua sisi crease.

    Lintasan 1: tetangga dalam radius dikelompokkan dua menurut normal halus (2-means), satu bidang per
    kelompok, dan garis potongnya. Lintasan 2: bidang di-fit ulang hanya dari titik dalam pita sempit di
    sekitar garis itu (bobot Gauss jarak tegak lurus garis dan jarak sepanjang garis), sehingga bias dari
    kelengkungan permukaan (misalnya busur chamfer, akar yang melengkung) mengecil. Posisi akhir memakai
    posisi vertex saja; normal hanya untuk pengelompokan. Mengembalikan (titik, berhasil, sudut crease dalam
    derajat antara normal rata-rata kedua sisi; 0 bila tetangga tidak terbagi dua).
    """
    refined = points.copy()
    ok = np.zeros(len(points), dtype=bool)
    angle = np.zeros(len(points))
    cos_min = np.cos(np.radians(min_angle_deg))
    min_sin = np.sin(np.radians(min_angle_deg))
    band = 0.5 * radius
    for idx, q in enumerate(points):
        nb = tree.query_ball_point(q, radius)
        if len(nb) < 8:
            continue
        p, n = vertices[nb], smooth_normals[nb]
        gram = n @ n.T
        i0, i1 = np.unravel_index(np.argmin(gram), gram.shape)
        c0, c1 = n[i0], n[i1]
        for _ in range(8):
            label = (n @ c1) > (n @ c0)
            if label.all() or (~label).all():
                break
            c0 = n[~label].mean(axis=0)
            c1 = n[label].mean(axis=0)
            c0 /= np.linalg.norm(c0)
            c1 /= np.linalg.norm(c1)
        if label.sum() < 3 or (~label).sum() < 3:
            continue
        angle[idx] = np.degrees(np.arccos(np.clip(c0 @ c1, -1.0, 1.0)))
        if c0 @ c1 > cos_min:
            continue

        w = np.exp(-(np.linalg.norm(p - q, axis=1) / (0.6 * radius)) ** 2)
        planes = [_fit_plane(p[g], w[g], c) for g, c in ((~label, c0), (label, c1))]
        line = _plane_intersection(planes, q, min_sin)
        if line is None:
            continue
        for _ in range(3):
            origin, direction = line
            rel = p - origin
            along = rel @ direction
            across = np.linalg.norm(rel - along[:, None] * direction, axis=1)
            w2 = np.exp(-(across / band) ** 2 - (along / (0.6 * radius)) ** 2)
            tangents = []
            for group, orient in ((~label, c0), (label, c1)):
                plane = _tangent_plane_at(p[group], w2[group], origin, direction, orient)
                if plane is None:
                    break
                tangents.append(plane)
            if len(tangents) < 2:
                break
            better = _plane_intersection(tangents, q, min_sin)
            if better is None:
                break
            line = better
        point = line[0]
        if np.linalg.norm(point - q) > radius:
            continue
        refined[idx] = point
        ok[idx] = True
    return refined, ok, angle


def _smooth_closed(points: np.ndarray, sigma: float) -> np.ndarray:
    """Haluskan kurva tertutup dengan regresi kuadratik lokal berbobot Gauss sepanjang panjang busur.

    Berbeda dengan rata-rata Gauss biasa, regresi kuadratik tidak menyusutkan kurva ke arah pusat
    kelengkungan (rata-rata Gauss menggeser titik sekitar sigma^2 * kelengkungan / 2).
    """
    closed = np.vstack([points, points[:1]])
    seg = np.linalg.norm(np.diff(closed, axis=0), axis=1)
    s = np.concatenate([[0.0], np.cumsum(seg)])[:-1]
    total = s[-1] + seg[-1]
    diff = s[None, :] - s[:, None]
    diff = (diff + 0.5 * total) % total - 0.5 * total  # (i, j): jarak busur bertanda dari i ke j
    w = np.exp(-0.5 * (diff / sigma) ** 2)
    if np.any((w > 1e-3).sum(axis=1) < 4):
        # Regresi kuadratik butuh beberapa tetangga dalam ~3 sigma; kurang dari itu berarti ada lubang lebar.
        raise MarginPlausibilityError("titik crease terlalu jarang untuk membentuk kurva", ["gap in the curve"])
    # Untuk setiap i: minimalkan sum_j w_ij |p_j - (c0 + c1 d + c2 d^2)|^2, hasil = c0.
    m0, m1, m2 = w.sum(1), (w * diff).sum(1), (w * diff**2).sum(1)
    m3, m4 = (w * diff**3).sum(1), (w * diff**4).sum(1)
    normal = np.stack([np.stack([m0, m1, m2], -1), np.stack([m1, m2, m3], -1), np.stack([m2, m3, m4], -1)], -2)
    rhs = np.stack([w @ points, (w * diff) @ points, (w * diff**2) @ points], axis=1)  # (n, 3, 3)
    try:
        return np.linalg.solve(normal, rhs)[:, 0, :]
    except np.linalg.LinAlgError:
        # Terjadi kalau titik terlalu jarang sepanjang kurva (lubang jauh lebih lebar dari sigma).
        raise MarginPlausibilityError("titik crease terlalu jarang untuk membentuk kurva", ["gap in the curve"]) from None


# 4. Kurva yang bisa diedit -------------------------------------------------------------------------

@dataclass
class MarginCurve:
    """Kurva margin tertutup: spline kubik periodik melalui titik kontrol yang terletak di permukaan."""

    control_points: np.ndarray
    projector: MeshProjector = field(repr=False)

    def __post_init__(self) -> None:
        self.control_points = np.asarray(self.control_points, float).reshape(-1, 3)
        if len(self.control_points) < 4:
            raise MarginError("kurva margin butuh minimal 4 titik kontrol")

    def sample(self, count: int = 512) -> np.ndarray:
        closed = np.vstack([self.control_points, self.control_points[:1]])
        chord = np.linalg.norm(np.diff(closed, axis=0), axis=1)
        t = np.concatenate([[0.0], np.cumsum(chord)])
        spline = CubicSpline(t, closed, bc_type="periodic")
        return spline(np.linspace(0.0, t[-1], count, endpoint=False))

    def length(self, count: int = 2048) -> float:
        pts = self.sample(count)
        return float(np.sum(np.linalg.norm(np.roll(pts, -1, axis=0) - pts, axis=1)))

    def move_point(self, index: int, position) -> None:
        """Geser titik kontrol ke posisi baru, lalu proyeksikan ke permukaan mesh."""
        projected, _, _ = self.projector.closest(np.asarray(position, float).reshape(1, 3))
        self.control_points[index] = projected[0]

    def delete_point(self, index: int) -> None:
        if len(self.control_points) <= 4:
            raise MarginError("kurva margin butuh minimal 4 titik kontrol")
        self.control_points = np.delete(self.control_points, index, axis=0)

    def apply_edit(self, points, tolerance_mm: float = 1e-4) -> dict:
        """Terapkan hasil edit pengguna (titik digeser dan/atau dihapus) ke titik kontrol.

        Titik yang posisinya masih sama dengan salah satu titik kontrol lama (dalam toleransi) dipertahankan
        apa adanya; titik lain dianggap digeser dan diproyeksikan ke permukaan mesh. Ini menjaga titik hasil
        deteksi yang tidak disentuh tetap di crease, bukan ditarik ke permukaan mesh yang memotong sudut.
        """
        points = np.asarray(points, float).reshape(-1, 3)
        if len(points) < 4:
            raise MarginError("kurva margin butuh minimal 4 titik kontrol")
        dist, _ = cKDTree(self.control_points).query(points)
        moved = dist > tolerance_mm
        if moved.any():
            points = points.copy()
            points[moved], _, _ = self.projector.closest(points[moved])
        removed = max(len(self.control_points) - len(points), 0)
        self.control_points = points
        return {"moved": int(moved.sum()), "kept": int((~moved).sum()), "removed": removed}

    def set_points(self, points) -> None:
        """Ganti semua titik kontrol (misalnya hasil edit di Blender); semuanya diproyeksikan ke permukaan."""
        points = np.asarray(points, float).reshape(-1, 3)
        if len(points) < 4:
            raise MarginError("kurva margin butuh minimal 4 titik kontrol")
        self.control_points, _, _ = self.projector.closest(points)


def _hull_perimeter_2d(points: np.ndarray) -> float:
    from scipy.spatial import ConvexHull

    hull = ConvexHull(points)
    ring = points[hull.vertices]
    return float(np.sum(np.linalg.norm(np.roll(ring, -1, axis=0) - ring, axis=1)))


def plausibility_metrics(controls: np.ndarray, vertices: np.ndarray, click: np.ndarray, ok_fraction: float,
                         spacing: float) -> dict:
    """Metrik kewajaran kurva margin.

    - ok_fraction: fraksi titik jalur yang berhasil disempurnakan ke crease.
    - click_distance: jarak titik klik pengguna ke kurva (kurva harus melewati daerah yang diklik).
    - gap_ratio: jarak terbesar antar titik kontrol berurutan dibagi jarak titik kontrol yang diminta
      (lubang besar = bagian margin yang hilang dan dijembatani garis lurus).
    - girth_ratio: panjang kurva yang diproyeksikan ke bidang fit-nya dibagi keliling convex hull die di
      sekitar ketinggian kurva, diproyeksikan ke bidang yang sama (margin harus melingkari die, bukan menyusut
      ke dinding atau berzig-zag). Panjang proyeksi, bukan panjang 3D: margin ber-scallop dalam (lengkungan
      CEJ anterior sampai sekitar 3,5 mm, PHASE2.md §5.1) memang lebih panjang daripada kelilingnya.
    - out_of_plane_ratio: simpangan terbesar kurva dari bidang fit-nya dibagi diameter ekuivalen kurva
      (kurva yang terjun ke tepi dasar die atau naik ke atap menyimpang jauh dari bidang).
    """
    from .synthetic import distance_to_polyline

    closed = np.vstack([controls, controls[:1]])
    steps = np.linalg.norm(np.diff(closed, axis=0), axis=1)
    length = float(steps.sum())
    center = controls.mean(axis=0)
    _, _, vt = np.linalg.svd(controls - center, full_matrices=False)
    e1, e2, axis = vt[0], vt[1], vt[2]
    heights = (controls - center) @ axis
    rel = vertices - center
    vh = rel @ axis
    slab = (vh >= heights.min() - 1.0) & (vh <= heights.max() + 1.0)
    girth = _hull_perimeter_2d(np.stack([rel[slab] @ e1, rel[slab] @ e2], axis=1)) if slab.sum() >= 3 else np.inf
    flat = np.stack([(closed - center) @ e1, (closed - center) @ e2], axis=1)
    projected_length = float(np.linalg.norm(np.diff(flat, axis=0), axis=1).sum())
    return {
        "ok_fraction": float(ok_fraction),
        "click_distance": float(distance_to_polyline(np.asarray(click, float).reshape(1, 3), controls)[0]),
        "gap_ratio": float(steps.max() / spacing),
        "girth_ratio": float(projected_length / girth),
        "out_of_plane_ratio": float(np.abs(heights).max() / (length / np.pi)),
    }


def plausibility_problems(metrics: dict, params: "MarginParams") -> list[tuple[str, str]]:
    """Daftar (nama metrik dalam bahasa Inggris untuk UI, penjelasan) untuk metrik yang melewati ambang."""
    problems = []
    if metrics["ok_fraction"] < params.min_refined_fraction:
        problems.append(("too few points on the crease",
                         f"hanya {metrics['ok_fraction']:.0%} titik yang menempel ke crease"))
    if metrics["click_distance"] > params.max_click_distance_mm:
        problems.append(("curve far from the clicked point",
                         f"kurva {metrics['click_distance']:.2f} mm dari titik klik"))
    if metrics["gap_ratio"] > params.max_control_gap_ratio:
        problems.append(("gap in the curve", f"ada lubang {metrics['gap_ratio']:.1f}x jarak titik kontrol di kurva"))
    low, high = params.girth_ratio_range
    if not low <= metrics["girth_ratio"] <= high:
        problems.append(("curve length does not match the die",
                         f"panjang kurva {metrics['girth_ratio']:.2f}x keliling die di ketinggian itu"))
    if metrics["out_of_plane_ratio"] > params.max_out_of_plane_ratio:
        problems.append(("curve leaves the margin plane",
                         f"kurva menyimpang {metrics['out_of_plane_ratio']:.2f}x diameter dari bidangnya"))
    return problems


@dataclass
class MarginResult:
    curve: MarginCurve
    path_vertices: np.ndarray
    refined_points: np.ndarray
    refined_ok: np.ndarray
    axis_estimate: np.ndarray
    score: np.ndarray
    noise_sigma_mm: float = 0.0
    metrics: dict = field(default_factory=dict)
    review: "MarginReview | None" = None


def detect_margin(mesh: MeshData, seed_point, params: MarginParams = MarginParams()) -> MarginResult:
    """Deteksi margin dari satu titik klik di dekat margin."""
    vertices = np.asarray(mesh.vertices, float)
    faces = np.asarray(mesh.faces)
    normals = vertex_normals(vertices, faces)
    sigma = estimate_noise_sigma(vertices, faces, normals)
    if params.check_noise and sigma > params.max_noise_mm:
        raise MarginNoiseError(
            f"scan terlalu berderau (perkiraan derau {1000 * sigma:.0f} um > {1000 * params.max_noise_mm:.0f} um); "
            "gambar margin manual (Draw Margin)",
            sigma, params.max_noise_mm,
        )
    curvature_radius = max(params.curvature_radius_min_mm, params.curvature_radius_per_noise * sigma)
    refine_radius = max(params.refine_radius_min_mm, params.refine_radius_per_noise * sigma)
    score, _, smooth_normals = crease_score(vertices, normals, curvature_radius)

    tree = cKDTree(vertices)
    _, seed = tree.query(np.asarray(seed_point, float))
    # Klik jarang tepat di crease: geser seed ke vertex berskor tertinggi di sekitar klik.
    nearby = tree.query_ball_point(vertices[seed], 2 * curvature_radius)
    seed = int(nearby[int(np.argmax(score[nearby]))])

    edges = unique_edges(faces)
    length = np.linalg.norm(vertices[edges[:, 0]] - vertices[edges[:, 1]], axis=1)
    # Skor relatif terhadap titik klik: crease yang diklik sama murahnya dengan crease terkuat di mesh,
    # sehingga jalur tidak memutar lewat crease lain yang lebih tajam (misalnya tepi dasar die).
    relative = np.clip(score / max(score[seed], 1e-9), 0.0, 1.0)
    edge_score = 0.5 * (relative[edges[:, 0]] + relative[edges[:, 1]])
    cost = length * (params.cost_eps + (1.0 - edge_score) ** params.cost_power)

    loop = closed_path_two_way(vertices, edges, cost, seed, params.ridge_ratio, params.band_rings,
                               far_candidates=relative >= params.far_min_score)

    samples = _resample_closed(vertices[loop], params.refine_spacing_mm)
    refined, ok, _ = refine_on_crease(samples, vertices, smooth_normals, tree, refine_radius,
                                      params.min_crease_angle_deg)
    if ok.sum() < 8:
        raise MarginPlausibilityError("crease tidak jelas: hampir tidak ada titik jalur yang menempel ke crease",
                                      ["no crease found along the path"])
    smoothed = _smooth_closed(refined[ok], params.smooth_sigma_mm)
    controls = _resample_closed(smoothed, params.control_spacing_mm)
    metrics = plausibility_metrics(controls, vertices, seed_point, ok.mean(), params.control_spacing_mm)
    problems = plausibility_problems(metrics, params)
    if problems:
        raise MarginPlausibilityError("kurva margin tidak wajar: " + "; ".join(text for _, text in problems),
                                      [name for name, _ in problems], metrics)
    projector = MeshProjector(mesh)
    curve = MarginCurve(controls, projector)
    context = ReviewContext(vertices, smooth_normals, tree, refine_radius)
    # Titik kontrol hasil deteksi sengaja TIDAK diproyeksikan ke mesh: mesh memotong sudut crease di antara
    # vertex, sehingga proyeksi menarik margin ke dalam. Titik yang digeser pengguna tetap diproyeksikan.
    return MarginResult(
        curve=curve,
        path_vertices=loop,
        refined_points=refined,
        refined_ok=ok,
        axis_estimate=loop_axis(vertices[loop]),
        score=score,
        noise_sigma_mm=sigma,
        metrics=metrics,
        review=review_curve(curve, context, params),
    )


# Penanda segmen meragukan --------------------------------------------------------------------------

REVIEW_SAMPLES = 256


@dataclass
class ReviewContext:
    """Analisis mesh yang dipakai ulang untuk memeriksa kurva (hasil deteksi, gambar manual, atau edit)."""

    vertices: np.ndarray
    smooth_normals: np.ndarray
    tree: cKDTree
    refine_radius: float

    @classmethod
    def from_mesh(cls, mesh: MeshData, params: "MarginParams" = None) -> "ReviewContext":
        params = params or MarginParams()
        vertices = np.asarray(mesh.vertices, float)
        faces = np.asarray(mesh.faces)
        normals = vertex_normals(vertices, faces)
        sigma = estimate_noise_sigma(vertices, faces, normals)
        curvature_radius = max(params.curvature_radius_min_mm, params.curvature_radius_per_noise * sigma)
        _, _, smooth_normals = crease_score(vertices, normals, curvature_radius)
        refine_radius = max(params.refine_radius_min_mm, params.refine_radius_per_noise * sigma)
        return cls(vertices, smooth_normals, cKDTree(vertices), refine_radius)


@dataclass
class MarginReview:
    """Hasil pemeriksaan per titik sampel kurva (REVIEW_SAMPLES titik, urutan sama dengan curve.sample).

    - residual: jarak titik kurva ke crease lokal (titik kurva disempurnakan ulang ke crease); inf bila tidak
      ada crease di sekitarnya.
    - angle: sudut crease lokal dalam derajat (0 bila tetangga tidak terbagi dua sisi).
    - flagged: titik yang meragukan (residual > ambang atau crease lemah), setelah run pendek dibuang.
    - segments: daftar (awal, akhir) indeks run flagged, akhir eksklusif; run yang melewati indeks 0 ditulis
      dengan akhir > REVIEW_SAMPLES.
    """

    samples: np.ndarray
    residual: np.ndarray
    angle: np.ndarray
    flagged: np.ndarray
    segments: list

    @property
    def count(self) -> int:
        return len(self.segments)


def _closed_runs(mask: np.ndarray) -> list:
    n = len(mask)
    if mask.all():
        return [(0, n)]
    if not mask.any():
        return []
    start = int(np.flatnonzero(~mask)[0]) + 1  # mulai setelah titik yang tidak ditandai
    runs, run_start = [], None
    for k in range(n):
        i = (start + k) % n
        if mask[i] and run_start is None:
            run_start = start + k
        elif not mask[i] and run_start is not None:
            runs.append((run_start, start + k))
            run_start = None
    if run_start is not None:
        runs.append((run_start, start + n))
    return [(a % n, a % n + (b - a)) for a, b in runs]


def review_curve(curve: MarginCurve, context: ReviewContext, params: "MarginParams" = None) -> MarginReview:
    """Tandai segmen kurva yang meragukan: kurva jauh dari crease lokal, atau crease-nya lemah/tidak ada."""
    params = params or MarginParams()
    samples = curve.sample(REVIEW_SAMPLES)
    crease, ok, angle = refine_on_crease(samples, context.vertices, context.smooth_normals, context.tree,
                                         context.refine_radius, params.min_crease_angle_deg)
    residual = np.where(ok, np.linalg.norm(crease - samples, axis=1), np.inf)
    raw = (residual > params.review_max_residual_mm) | (angle < params.review_min_angle_deg)
    segments = [(a, b) for a, b in _closed_runs(raw) if b - a >= params.review_min_run]
    flagged = np.zeros(len(samples), dtype=bool)
    for a, b in segments:
        flagged[np.arange(a, b) % len(samples)] = True
    return MarginReview(samples, residual, angle, flagged, segments)


MIN_DRAWN_POINTS = 4


def draw_margin(mesh: MeshData, points, min_spacing_mm: float = 0.05) -> MarginCurve:
    """Margin gambar manual: titik yang diklik pengguna (berurutan) diproyeksikan ke permukaan die dan
    ditutup otomatis menjadi kurva yang sama dengan hasil deteksi (bisa diedit dengan cara yang sama).

    Titik yang lebih dekat dari min_spacing_mm ke titik sebelumnya (klik ganda) dibuang, termasuk titik
    terakhir yang menutup ke titik pertama.
    """
    points = np.asarray(points, float).reshape(-1, 3)
    projector = MeshProjector(mesh)
    if len(points):
        points, _, _ = projector.closest(points)
    kept = []
    for p in points:
        if not kept or np.linalg.norm(p - kept[-1]) >= min_spacing_mm:
            kept.append(p)
    if len(kept) > 1 and np.linalg.norm(kept[-1] - kept[0]) < min_spacing_mm:
        kept.pop()
    if len(kept) < MIN_DRAWN_POINTS:
        raise MarginError(f"margin manual butuh minimal {MIN_DRAWN_POINTS} titik berbeda, didapat {len(kept)}")
    return MarginCurve(np.array(kept), projector)


def margin_deviation(curve_points: np.ndarray, truth_points: np.ndarray) -> dict:
    """Deviasi kurva terdeteksi terhadap kurva benar (keduanya sampel rapat kurva tertutup), dalam mm.

    Arah 1 (akurasi): jarak titik terdeteksi ke kurva benar. Arah 2 (cakupan): jarak titik kurva benar ke
    kurva terdeteksi, supaya kurva yang hanya menutupi sebagian margin tidak lolos.
    """
    from .synthetic import distance_to_polyline

    to_truth = distance_to_polyline(curve_points, truth_points)
    to_curve = distance_to_polyline(truth_points, curve_points)
    return {
        "median": float(np.median(to_truth)),
        "p95": float(np.percentile(to_truth, 95)),
        "max": float(to_truth.max()),
        "coverage_p95": float(np.percentile(to_curve, 95)),
        "coverage_max": float(to_curve.max()),
    }
