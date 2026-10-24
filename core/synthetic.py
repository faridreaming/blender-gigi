# SPDX-License-Identifier: GPL-3.0-or-later
"""Die preparasi sintetis dengan geometri analitis (docs/PHASE2.md §4).

Semua ukuran di DieSpec adalah "desain data uji", bukan parameter desain crown. Permukaan didefinisikan
lewat parameter (theta, t), sehingga jawaban benar (kurva margin, normal, daerah undercut) dihitung dari
rumus, terlepas dari tesselasi mesh.

Frame die: sumbu insersi = +Z, akar die mengikuti elips (a, b) di bidang XY. Titik permukaan:

    p(theta, t) = E(theta) + d(theta, t) * N(theta) + z(theta, t) * Z

dengan E titik elips, N normal luar elips di XY, d offset ke dalam (d <= 0), dan t profil:
    0 <= t <= 1  akar      : d = 0, z dari dasar die ke margin z_m(theta)
    1 <= t <= 2  finish    : shoulder (tangga horizontal selebar w) atau chamfer (busur cekung radius w)
    2 <= t <= 3  dinding   : menyempit ke oklusal dengan sudut taper (atau miring keluar di sektor undercut)
    3 <= t <= 4  atap      : kubah seperempat elips sampai kutub di sumbu
Margin = kurva t = 1: M(theta) = (a cos theta, b sin theta, z_m(theta)), z_m = z0 + A cos(2 theta).
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .geometry import vertex_normals  # noqa: F401  (diekspor ulang untuk tes dan pemanggil lama)
from .mesh_data import MeshData

FINISHES = ("shoulder", "chamfer")
_FD_STEP = 1e-6  # langkah beda hingga untuk normal analitis


@dataclass(frozen=True)
class DieSpec:
    finish: str = "shoulder"
    radius_x_mm: float = 5.0
    radius_y_mm: float = 4.5
    finish_width_mm: float = 1.0
    margin_z_mm: float = 0.0
    scallop_mm: float = 0.0
    taper_deg: float = 6.0
    prep_height_mm: float = 5.0
    roof_height_mm: float = 1.0
    root_depth_mm: float = 4.0
    undercut_deg: float = 0.0
    undercut_center_deg: float = 0.0
    undercut_halfwidth_deg: float = 40.0

    def __post_init__(self) -> None:
        if self.finish not in FINISHES:
            raise ValueError(f"finish wajib salah satu dari {FINISHES}, didapat {self.finish!r}")
        if min(self.radius_x_mm, self.radius_y_mm, self.finish_width_mm, self.prep_height_mm) <= 0:
            raise ValueError("ukuran die wajib > 0")
        if self.roof_height_mm < 0 or self.root_depth_mm <= 0 or self.undercut_deg < 0:
            raise ValueError("tinggi atap >= 0, kedalaman akar > 0, dan sudut undercut >= 0")
        if not 0 <= self.taper_deg < 45:
            raise ValueError("taper_deg wajib di [0, 45)")
        if abs(self.scallop_mm) >= self.prep_height_mm - self._finish_rise():
            raise ValueError("scallop terlalu besar dibanding tinggi preparasi")
        # Offset ke dalam harus lebih kecil dari jari-jari kelengkungan minimum elips (b^2/a untuk a >= b),
        # kalau tidak, kurva offset melipat diri.
        a, b = self.radius_x_mm, self.radius_y_mm
        min_curvature_radius = min(a, b) ** 2 / max(a, b)
        deepest = self.finish_width_mm + (self.prep_height_mm + abs(self.scallop_mm)) * np.tan(np.radians(self.taper_deg))
        if deepest >= 0.9 * min_curvature_radius:
            raise ValueError(f"offset dinding {deepest:.2f} mm terlalu dalam untuk elips {a} x {b} mm")

    def _finish_rise(self) -> float:
        return self.finish_width_mm if self.finish == "chamfer" else 0.0

    @property
    def top_z(self) -> float:
        return self.margin_z_mm + self.prep_height_mm

    @property
    def bottom_z(self) -> float:
        return self.margin_z_mm - abs(self.scallop_mm) - self.root_depth_mm


def _ellipse(spec: DieSpec, theta: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Titik elips dan normal luar satuan di XY."""
    a, b = spec.radius_x_mm, spec.radius_y_mm
    c, s = np.cos(theta), np.sin(theta)
    point = np.stack([a * c, b * s], axis=-1)
    normal = np.stack([b * c, a * s], axis=-1)
    normal /= np.linalg.norm(normal, axis=-1, keepdims=True)
    return point, normal


def margin_z(spec: DieSpec, theta: np.ndarray) -> np.ndarray:
    return spec.margin_z_mm + spec.scallop_mm * np.cos(2 * theta)


def _undercut_blend(spec: DieSpec, theta: np.ndarray) -> np.ndarray:
    if spec.undercut_deg == 0:
        return np.zeros_like(theta)
    delta = np.angle(np.exp(1j * (theta - np.radians(spec.undercut_center_deg))))
    x = np.abs(delta) / np.radians(spec.undercut_halfwidth_deg)
    return np.where(x < 1, np.cos(0.5 * np.pi * np.minimum(x, 1)) ** 2, 0.0)


def _wall_slope(spec: DieSpec, theta: np.ndarray) -> np.ndarray:
    """dd/du di dinding: negatif = menyempit ke oklusal, positif = undercut."""
    tan_taper = np.tan(np.radians(spec.taper_deg))
    tan_under = np.tan(np.radians(spec.undercut_deg))
    return -tan_taper + _undercut_blend(spec, theta) * (tan_taper + tan_under)


def surface_points(spec: DieSpec, theta: np.ndarray, t: np.ndarray) -> np.ndarray:
    """Titik permukaan die di frame die untuk parameter (theta, t), t di [0, 4]."""
    theta, t = np.broadcast_arrays(np.asarray(theta, float), np.asarray(t, float))
    w = spec.finish_width_mm
    zm = margin_z(spec, theta)
    rise = spec._finish_rise()
    d = np.zeros_like(t)
    z = np.zeros_like(t)

    root = t <= 1
    z[root] = spec.bottom_z + t[root] * (zm[root] - spec.bottom_z)

    finish = (t > 1) & (t <= 2)
    s = t[finish] - 1
    if spec.finish == "shoulder":
        d[finish] = -w * s
        z[finish] = zm[finish]
    else:
        phi = -0.5 * np.pi - 0.5 * np.pi * s  # busur cekung, pusat (d=0, u=w), dari (0, 0) ke (-w, w)
        d[finish] = w * np.cos(phi)
        z[finish] = zm[finish] + w + w * np.sin(phi)

    wall = (t > 2) & (t <= 3)
    s = t[wall] - 2
    u0 = zm[wall] + rise
    z[wall] = u0 + s * (spec.top_z - u0)
    d[wall] = -w + _wall_slope(spec, theta[wall]) * (z[wall] - u0)

    roof = t > 3
    s = np.minimum(t[roof] - 3, 1.0)
    top_d = -w + _wall_slope(spec, theta[roof]) * (spec.top_z - (zm[roof] + rise))
    z[roof] = spec.top_z + spec.roof_height_mm * np.sin(0.5 * np.pi * s)
    d[roof] = top_d

    e, n = _ellipse(spec, theta)
    xy = e + d[..., None] * n
    xy[roof] *= np.cos(0.5 * np.pi * s)[:, None]  # kubah: menyusut ke sumbu dengan tangen vertikal di tepi
    return np.concatenate([xy, z[..., None]], axis=-1)


def surface_normals(spec: DieSpec, theta: np.ndarray, t: np.ndarray) -> np.ndarray:
    """Normal luar analitis lewat beda hingga pada parameter (bukan dari mesh)."""
    theta, t = np.broadcast_arrays(np.asarray(theta, float), np.asarray(t, float))
    h = _FD_STEP
    dtheta = surface_points(spec, theta + h, t) - surface_points(spec, theta - h, t)
    dt = surface_points(spec, theta, t + h) - surface_points(spec, theta, t - h)
    normal = np.cross(dtheta, dt)
    return normal / np.linalg.norm(normal, axis=-1, keepdims=True)


def margin_points(spec: DieSpec, theta: np.ndarray) -> np.ndarray:
    """Kurva margin analitis M(theta) di frame die."""
    e, _ = _ellipse(spec, np.asarray(theta, float))
    return np.concatenate([e, margin_z(spec, np.asarray(theta, float))[..., None]], axis=-1)


def random_rotation(rng: np.random.Generator) -> np.ndarray:
    q, r = np.linalg.qr(rng.normal(size=(3, 3)))
    q *= np.sign(np.diag(r))
    if np.linalg.det(q) < 0:
        q[:, 0] *= -1
    return q


@dataclass
class SyntheticDie:
    spec: DieSpec
    mesh: MeshData  # frame dunia: diputar dan berderau
    rotation: np.ndarray  # dunia = rotation @ die
    vertex_params: np.ndarray  # (N, 2) theta, t; kutub dan pusat dasar ikut dicatat
    face_params: np.ndarray  # (M, 2) theta, t di titik berat parameter tiap face
    noise_sigma_mm: float

    @property
    def insertion_axis(self) -> np.ndarray:
        return self.rotation @ np.array([0.0, 0.0, 1.0])

    def margin_curve(self, samples: int = 4096) -> np.ndarray:
        """Kurva margin analitis di frame dunia, sampel rapat (kurva tertutup)."""
        theta = np.linspace(0, 2 * np.pi, samples, endpoint=False)
        return margin_points(self.spec, theta) @ self.rotation.T

    def prep_faces(self) -> np.ndarray:
        """Face di atas margin (finish, dinding, atap)."""
        return self.face_params[:, 1] > 1

    def undercut_faces(self) -> np.ndarray:
        """Jawaban benar undercut: face di atas margin yang normal analitisnya menjauhi sumbu insersi."""
        theta, t = self.face_params[:, 0], self.face_params[:, 1]
        normal = surface_normals(self.spec, theta, np.minimum(t, 3.999))
        return self.prep_faces() & (normal[:, 2] < 0)


def _grid_rows(rows: tuple[int, int, int, int]) -> np.ndarray:
    """Nilai t untuk setiap baris grid, dari cincin dasar (t = 0) sampai sebelum kutub (t = 4)."""
    return np.concatenate([segment + np.arange(count) / count for segment, count in enumerate(rows)])


def make_die(
    spec: DieSpec,
    n_theta: int = 128,
    rows: tuple[int, int, int, int] = (12, 8, 24, 10),
    jitter: float = 0.45,
    noise_sigma_mm: float = 0.0,
    rotate: bool = True,
    seed: int = 0,
) -> SyntheticDie:
    """Mesh die tertutup dari permukaan analitis.

    jitter menggeser setiap vertex secara acak di ruang parameter (sampai jitter x satu sel grid), jadi
    vertex tetap di permukaan analitis tetapi tidak berbaris tepat di garis margin. Derau ditambahkan
    sepanjang normal vertex dengan sigma noise_sigma_mm, lalu die diputar acak kalau rotate=True.
    """
    if not 0 <= jitter < 0.5:
        raise ValueError("jitter wajib di [0, 0.5)")
    rng = np.random.default_rng(seed)
    t_rows = _grid_rows(rows)
    n_rows = len(t_rows)
    dtheta = 2 * np.pi / n_theta
    theta = np.arange(n_theta) * dtheta

    tt, th = np.meshgrid(t_rows, theta, indexing="ij")  # (n_rows, n_theta)
    if jitter > 0:
        dt = np.diff(np.concatenate([[0.0], t_rows, [4.0]]))
        cell = np.minimum(dt[:-1], dt[1:])[:, None]
        tt = tt + rng.uniform(-jitter, jitter, tt.shape) * cell
        th = th + rng.uniform(-jitter, jitter, th.shape) * dtheta
    params = np.stack([th.ravel(), tt.ravel()], axis=1)
    ring = surface_points(spec, params[:, 0], params[:, 1])

    bottom = np.array([[0.0, 0.0, spec.bottom_z]])
    pole = np.array([[0.0, 0.0, spec.top_z + spec.roof_height_mm]])
    vertices = np.vstack([bottom, ring, pole])
    vertex_params = np.vstack([[0.0, 0.0], params, [0.0, 4.0]])
    b_idx, p_idx = 0, len(vertices) - 1

    def vid(i, j):
        return 1 + i * n_theta + (j % n_theta)

    faces = []
    for j in range(n_theta):  # tutup dasar, menghadap ke bawah
        faces.append((b_idx, vid(0, j + 1), vid(0, j)))
    diag = rng.integers(0, 2, size=(n_rows - 1, n_theta))
    for i in range(n_rows - 1):
        for j in range(n_theta):
            a, b, c, d = vid(i, j), vid(i, j + 1), vid(i + 1, j + 1), vid(i + 1, j)
            if diag[i, j]:
                faces += [(a, b, c), (a, c, d)]
            else:
                faces += [(a, b, d), (b, c, d)]
    for j in range(n_theta):  # kutub atap
        faces.append((vid(n_rows - 1, j), vid(n_rows - 1, j + 1), p_idx))
    faces = np.array(faces, dtype=np.int64)

    if noise_sigma_mm > 0:
        normals = vertex_normals(vertices, faces)
        vertices = vertices + normals * rng.normal(0.0, noise_sigma_mm, (len(vertices), 1))

    rotation = random_rotation(rng) if rotate else np.eye(3)
    face_params = _face_param_centroids(vertex_params, faces, n_theta)
    return SyntheticDie(
        spec=spec,
        mesh=MeshData(vertices @ rotation.T, faces),
        rotation=rotation,
        vertex_params=vertex_params,
        face_params=face_params,
        noise_sigma_mm=noise_sigma_mm,
    )


def _face_param_centroids(vertex_params: np.ndarray, faces: np.ndarray, n_theta: int) -> np.ndarray:
    """Titik berat parameter per face, dengan theta yang membungkus 2 pi ditangani dengan benar."""
    theta = vertex_params[faces, 0]
    ref = theta[:, :1]
    theta = ref + np.angle(np.exp(1j * (theta - ref)))
    t = vertex_params[faces, 1]
    return np.stack([theta.mean(axis=1) % (2 * np.pi), t.mean(axis=1)], axis=1)


def distance_to_polyline(points: np.ndarray, polyline: np.ndarray, closed: bool = True, chunk: int = 2048) -> np.ndarray:
    """Jarak terdekat setiap titik ke polyline (eksak per segmen), diproses per blok supaya hemat memori."""
    points = np.asarray(points, float).reshape(-1, 3)
    start = np.asarray(polyline, float)
    end = np.roll(start, -1, axis=0) if closed else start[1:]
    start = start if closed else start[:-1]
    seg = end - start
    seg_len2 = np.maximum(np.einsum("ij,ij->i", seg, seg), 1e-30)
    result = np.empty(len(points))
    for i in range(0, len(points), chunk):
        p = points[i : i + chunk, None, :]
        u = np.clip(np.einsum("pij,ij->pi", p - start, seg) / seg_len2, 0.0, 1.0)
        nearest = start + u[..., None] * seg
        result[i : i + chunk] = np.sqrt(np.min(np.sum((p - nearest) ** 2, axis=-1), axis=1))
    return result


def undercut_depth_truth(spec: DieSpec, theta: np.ndarray, t: np.ndarray, n_theta: int = 720,
                         rows: tuple[int, int, int, int] = (12, 48, 160, 60)) -> np.ndarray:
    """Jawaban benar kedalaman undercut terhadap sumbu sebenarnya (+Z die) di titik permukaan (theta, t).

    Dihitung dengan uji bayangan eksak (core.insertion.ShadowField) pada triangulasi permukaan analitis yang
    rapat, tanpa jitter dan tanpa derau (sel sekitar 0,03-0,05 mm), bukan dari mesh yang diuji.
    """
    from .insertion import ShadowField

    dense = make_die(spec, n_theta=n_theta, rows=rows, jitter=0.0, noise_sigma_mm=0.0, rotate=False)
    triangles = dense.mesh.vertices[dense.mesh.faces[dense.prep_faces()]]
    field = ShadowField(triangles, np.array([0.0, 0.0, 1.0]), np.zeros(3), height_eps=0.005, step=0.005,
                        max_depth=3.0)
    t = np.minimum(np.asarray(t, float), 3.999)
    return field.depth(surface_points(spec, theta, t))


# Gigi tetangga dan antagonis sintetis (docs/PHASE2.md §5.4 langkah 3) ------------------------------------------

def _grid_mesh(points: np.ndarray, wrap_u: bool, caps: tuple = ()) -> MeshData:
    """Mesh segitiga dari grid titik (n_u, n_v, 3); wrap_u menyambung u terakhir ke u pertama."""
    n_u, n_v = points.shape[:2]
    vertices = [points.reshape(-1, 3)]
    faces = []
    for i in range(n_u if wrap_u else n_u - 1):
        for j in range(n_v - 1):
            a = i * n_v + j
            b = ((i + 1) % n_u) * n_v + j
            faces += [(a, b, b + 1), (a, b + 1, a + 1)]
    offset = n_u * n_v
    for cap_point, column in caps:  # tutup kutub: (titik, indeks kolom v)
        vertices.append(np.asarray(cap_point, float)[None])
        pole = offset
        offset += 1
        for i in range(n_u):
            a, b = i * n_v + column, ((i + 1) % n_u) * n_v + column
            faces.append((a, pole, b) if column == 0 else (b, pole, a))
    return MeshData(np.vstack(vertices), np.array(faces, dtype=np.int64))


@dataclass(frozen=True)
class Ellipsoid:
    """Elipsoid di frame die: pusat, setengah sumbu, dan rotasi (kolom = sumbu elipsoid di frame die)."""

    center: np.ndarray
    semi_axes: np.ndarray
    rotation: np.ndarray

    def mesh(self, n_u: int = 96, n_v: int = 48, jitter: float = 0.3, noise_sigma_mm: float = 0.0,
             seed: int = 0) -> MeshData:
        rng = np.random.default_rng(seed)
        u = np.arange(n_u) * 2 * np.pi / n_u
        v = np.linspace(0.0, np.pi, n_v + 2)[1:-1]
        uu, vv = np.meshgrid(u, v, indexing="ij")
        if jitter:
            uu = uu + rng.uniform(-jitter, jitter, uu.shape) * (2 * np.pi / n_u)
            vv = vv + rng.uniform(-jitter, jitter, vv.shape) * (np.pi / (n_v + 1))
        a, b, c = self.semi_axes
        local = np.stack([a * np.sin(vv) * np.cos(uu), b * np.sin(vv) * np.sin(uu), c * np.cos(vv)], axis=-1)
        if noise_sigma_mm:
            normal = local / np.asarray(self.semi_axes) ** 2
            normal /= np.linalg.norm(normal, axis=-1, keepdims=True)
            local = local + normal * rng.normal(0.0, noise_sigma_mm, local.shape[:2] + (1,))
        mesh = _grid_mesh(local, True, ((np.array([0.0, 0.0, c]), 0), (np.array([0.0, 0.0, -c]), n_v - 1)))
        v, f = mesh.vertices, mesh.faces.copy()
        fn = np.cross(v[f[:, 1]] - v[f[:, 0]], v[f[:, 2]] - v[f[:, 0]])
        inward = np.einsum("ij,ij->i", fn, v[f].mean(axis=1)) < 0  # elipsoid cembung: normal menjauhi pusat
        f[inward] = f[inward][:, ::-1]
        return MeshData(v @ self.rotation.T + self.center, np.ascontiguousarray(f))

    def signed_distance(self, points: np.ndarray) -> np.ndarray:
        """Jarak bertanda eksak titik (frame die) ke elipsoid: positif di luar. Bisection Eberly pada parameter t
        dari F(t) = sum (e_i y_i / (t + e_i^2))^2 - 1, 200 iterasi (presisi float64)."""
        y = np.abs((np.asarray(points, float) - self.center) @ self.rotation)
        e = np.asarray(self.semi_axes, float)
        y = np.maximum(y, 1e-12)  # titik tepat di bidang simetri: hindari pembagian nol
        outside = np.sum((y / e) ** 2, axis=1) > 1.0
        e_min2 = float(np.min(e)) ** 2
        lo = np.full(len(y), -e_min2 + 1e-15)
        hi = np.where(outside, np.max(e) * np.linalg.norm(y, axis=1), 0.0)
        for _ in range(200):
            t = 0.5 * (lo + hi)
            f = np.sum((e * y / (t[:, None] + e ** 2)) ** 2, axis=1) - 1.0
            lo = np.where(f > 0, t, lo)
            hi = np.where(f > 0, hi, t)
        t = 0.5 * (lo + hi)
        closest = e ** 2 * y / (t[:, None] + e ** 2)
        return np.where(outside, 1.0, -1.0) * np.linalg.norm(y - closest, axis=1)


@dataclass(frozen=True)
class AntagonistPlane:
    """Bidang (frame die) dengan normal menghadap crown: jarak bertanda = (p - titik) . normal."""

    point: np.ndarray
    normal: np.ndarray  # satuan, menghadap ke crown (ke -sumbu insersi untuk antagonis di atas)
    size_mm: float = 24.0

    def mesh(self, n: int = 49, noise_sigma_mm: float = 0.0, seed: int = 0) -> MeshData:
        rng = np.random.default_rng(seed)
        nrm = np.asarray(self.normal, float)
        helper = np.array([1.0, 0.0, 0.0]) if abs(nrm[0]) < 0.9 else np.array([0.0, 1.0, 0.0])
        u = np.cross(nrm, helper)
        u /= np.linalg.norm(u)
        w = np.cross(nrm, u)
        g = np.linspace(-0.5, 0.5, n) * self.size_mm
        gu, gw = np.meshgrid(g, g, indexing="ij")
        pts = self.point + gu[..., None] * u + gw[..., None] * w
        if noise_sigma_mm:
            pts = pts + nrm * rng.normal(0.0, noise_sigma_mm, pts.shape[:2] + (1,))
        mesh = _grid_mesh(pts, False)
        # Orientasi: normal face searah normal bidang.
        f = mesh.faces
        fn = np.cross(mesh.vertices[f[:, 1]] - mesh.vertices[f[:, 0]], mesh.vertices[f[:, 2]] - mesh.vertices[f[:, 0]])
        if np.mean(fn @ nrm) < 0:
            f = f[:, ::-1]
        return MeshData(mesh.vertices, np.ascontiguousarray(f))

    def signed_distance(self, points: np.ndarray) -> np.ndarray:
        return (np.asarray(points, float) - self.point) @ np.asarray(self.normal, float)


@dataclass(frozen=True)
class AntagonistCylinder:
    """Permukaan silinder cembung ke arah crown (frame die): sumbu silinder lewat axis_point sepanjang axis_dir,
    jari-jari radius; crown berada di luar silinder."""

    axis_point: np.ndarray
    axis_dir: np.ndarray
    radius: float
    length_mm: float = 24.0
    span_deg: float = 70.0
    down: np.ndarray = None  # arah dari sumbu silinder ke crown

    def mesh(self, n_u: int = 72, n_v: int = 49, noise_sigma_mm: float = 0.0, seed: int = 0) -> MeshData:
        rng = np.random.default_rng(seed)
        d = np.asarray(self.axis_dir, float)
        down = np.asarray(self.down, float)
        side = np.cross(d, down)
        ang = np.radians(np.linspace(-0.5, 0.5, n_u) * self.span_deg)
        s = np.linspace(-0.5, 0.5, n_v) * self.length_mm
        aa, ss = np.meshgrid(ang, s, indexing="ij")
        radial = np.cos(aa)[..., None] * down + np.sin(aa)[..., None] * side
        r = self.radius + (rng.normal(0.0, noise_sigma_mm, aa.shape) if noise_sigma_mm else np.zeros(aa.shape))
        pts = self.axis_point + ss[..., None] * d + r[..., None] * radial
        mesh = _grid_mesh(pts, False)
        f = mesh.faces
        v = mesh.vertices
        fn = np.cross(v[f[:, 1]] - v[f[:, 0]], v[f[:, 2]] - v[f[:, 0]])
        centers = v[f].mean(axis=1)
        rel = centers - self.axis_point
        outward = rel - (rel @ d)[:, None] * d
        if np.mean(np.einsum("ij,ij->i", fn, outward)) < 0:
            f = f[:, ::-1]
        return MeshData(v, np.ascontiguousarray(f))

    def signed_distance(self, points: np.ndarray) -> np.ndarray:
        rel = np.asarray(points, float) - self.axis_point
        d = np.asarray(self.axis_dir, float)
        return np.linalg.norm(rel - (rel @ d)[:, None] * d, axis=1) - self.radius
