# SPDX-License-Identifier: GPL-3.0-or-later
"""Proposal crown berlabuh margin (docs/PHASE2.md §5.4 langkah 1 sampai 3).

Bukan morphing mesh: permukaan luar dibangun langsung sebagai S(phi, v) = T(phi, v) + (1 - w(v)) (M(phi) - T(phi, 0)),
dengan M(phi) titik margin terkonfirmasi pada sudut polar phi di sekitar sumbu insersi, T template parametrik
(core/template.py), dan w fungsi campuran smoothstep yang mencapai 1 sebelum height of contour. Jadi S(phi, 0) =
M(phi) menurut konstruksi, tanpa deformasi Laplacian dan tanpa handle/target dari perpotongan garis (paten PAT4),
dan tanpa arsip kasus atau pencarian kemiripan margin (PAT5).

Penyesuaian ke gigi tetangga dan antagonis mengubah parameter global template (tepi mesial, tepi distal, tinggi)
dengan iterasi skalar per parameter: setiap tepi digeser sejauh selisih jarak bertanda terukur terhadap target.
Border Ivoclar (langkah 4) dan solid tertutup (langkah 5) belum ada: sampai langkah 4, tepi bawah S adalah margin.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from .geometry import MeshProjector, face_normals, vertex_normals
from .mesh_data import MeshData
from .template import TemplateParams, fdi_kind, relief_floor_fraction, template_points

N_PHI = 192
N_V = 64


class CrownError(ValueError):
    """Proposal crown tidak bisa dibuat (ruang terlalu sempit, margin tidak bisa dipetakan, dan sebagainya)."""


@dataclass(frozen=True)
class CrownParams:
    """Parameter langkah 1 sampai 3. Status dan sumber di PHASE2.md §5.4."""

    occlusal_distance_mm: float = 0.0  # literatur, perlu kalibrasi (Nagata 2025)
    approximal_distance_mm: float = -0.02  # literatur, perlu kalibrasi (Nagata 2025); negatif = overlap
    min_occlusal_thickness_mm: float = 1.0  # default pabrikan IVO (molar/premolar 1,00; anterior 0,80)
    cement_gap_mm: float = 0.06  # default pabrikan IVO, untuk tinggi minimum
    contour_bulge_mm: float = 0.5  # perlu kalibrasi, tanpa sumber
    blend_fraction: float = 0.5  # bagian dinding di bawah height of contour tempat margin dicampur (algoritma)
    tolerance_mm: float = 0.001  # konvergensi iterasi (ambang algoritma)
    max_iterations: int = 40


@dataclass(frozen=True)
class CrownFrame:
    origin: np.ndarray
    x: np.ndarray  # mesial
    y: np.ndarray
    z: np.ndarray  # sumbu insersi (oklusal)

    def to_local(self, points: np.ndarray) -> np.ndarray:
        rel = np.asarray(points, float) - self.origin
        return np.stack([rel @ self.x, rel @ self.y, rel @ self.z], axis=-1)

    def to_world(self, local: np.ndarray) -> np.ndarray:
        local = np.asarray(local, float)
        return self.origin + local[..., :1] * self.x + local[..., 1:2] * self.y + local[..., 2:3] * self.z

    def shifted(self, dx: float) -> "CrownFrame":
        return CrownFrame(self.origin + dx * self.x, self.x, self.y, self.z)


def make_frame(margin: np.ndarray, axis, mesial) -> CrownFrame:
    """Frame crown: z = sumbu insersi, x = arah mesial yang diproyeksikan tegak lurus sumbu, origin di sumbu
    melewati titik berat margin pada tinggi rata-rata margin."""
    z = np.asarray(axis, float)
    z = z / np.linalg.norm(z)
    x = np.asarray(mesial, float)
    x = x - (x @ z) * z
    if np.linalg.norm(x) < 1e-9:
        raise CrownError("arah mesial sejajar sumbu insersi")
    x /= np.linalg.norm(x)
    return CrownFrame(np.asarray(margin, float).mean(axis=0), x, np.cross(z, x), z)


def margin_by_angle(frame: CrownFrame, margin: np.ndarray, n_phi: int = N_PHI) -> tuple[np.ndarray, np.ndarray]:
    """Titik margin pada n_phi sudut polar yang sama rata (frame lokal). Gagal bila sudut polar margin tidak
    monoton (margin tidak "melingkari" sumbu)."""
    local = frame.to_local(margin)
    ang = np.arctan2(local[:, 1], local[:, 0])
    step = np.angle(np.exp(1j * np.diff(np.concatenate([ang, ang[:1]]))))
    total = step.sum()
    if abs(abs(total) - 2 * np.pi) > 1e-3 or np.any(np.sign(step) != np.sign(total)):
        raise CrownError("margin tidak melingkari sumbu insersi secara monoton; proposal crown tidak bisa dibuat")
    if total < 0:  # urutan margin searah jarum jam: balik supaya sudut naik
        local = local[::-1]
        ang = np.arctan2(local[:, 1], local[:, 0])
        step = np.angle(np.exp(1j * np.diff(np.concatenate([ang, ang[:1]]))))
    cum = np.concatenate([[0.0], np.cumsum(step)]) + ang[0]
    closed = np.vstack([local, local[:1]])
    phi = np.linspace(0.0, 2 * np.pi, n_phi, endpoint=False)
    target = ang[0] + np.mod(phi - ang[0], 2 * np.pi)
    pts = np.stack([np.interp(target, cum, closed[:, k]) for k in range(3)], axis=1)
    return phi, pts


def _smoothstep(x: np.ndarray) -> np.ndarray:
    x = np.clip(x, 0.0, 1.0)
    return x * x * (3.0 - 2.0 * x)


@dataclass
class CrownSurface:
    frame: CrownFrame
    template: TemplateParams
    phi: np.ndarray
    v: np.ndarray
    local: np.ndarray  # (N_PHI, N_V, 3) titik frame lokal
    mesh: MeshData  # dunia; tepi bawah = margin, titik tengah oklusal ditutup


def crown_surface(frame: CrownFrame, template: TemplateParams, margin_local: np.ndarray, phi: np.ndarray,
                  blend_fraction: float = 0.5, n_v: int = N_V) -> CrownSurface:
    """S(phi, v) berlabuh margin. margin_local dari margin_by_angle (frame yang sama)."""
    v = np.linspace(0.0, 1.0, n_v)
    tpl = template_points(template, phi[:, None], v[None, :])
    v_blend = blend_fraction * template.shape.contour_t * template.v_wall
    w = _smoothstep(v / v_blend) if v_blend > 0 else np.ones_like(v)
    offset = margin_local - tpl[:, 0, :]
    local = tpl + (1.0 - w)[None, :, None] * offset[:, None, :]
    local[:, -1, :] = local[0, -1, :]  # titik tengah oklusal sama untuk semua sudut
    n_phi = len(phi)
    grid = local[:, :-1, :].reshape(-1, 3)
    vertices = np.vstack([grid, local[0, -1][None]])
    pole = len(vertices) - 1

    def vid(i, j):
        return (i % n_phi) * (n_v - 1) + j

    faces = []
    for i in range(n_phi):
        for j in range(n_v - 2):
            a, b, c, d = vid(i, j), vid(i + 1, j), vid(i + 1, j + 1), vid(i, j + 1)
            faces += [(a, b, c), (a, c, d)]
        faces.append((vid(i, n_v - 2), vid(i + 1, n_v - 2), pole))
    mesh = MeshData(frame.to_world(vertices), np.array(faces, dtype=np.int64))
    return CrownSurface(frame, template, phi, v, local, mesh)


def flipped_faces(surface: CrownSurface) -> int:
    """Lipatan akibat pencampuran margin: face yang normalnya berbalik arah dibanding face yang sama pada template
    murni (topologi sama, tanpa campuran margin). Template sendiri tidak terlipat (diuji terpisah)."""
    pure = template_points(surface.template, surface.phi[:, None], surface.v[None, :])
    pure[:, -1, :] = pure[0, -1, :]
    pure_vertices = np.vstack([pure[:, :-1, :].reshape(-1, 3), pure[0, -1][None]])
    f = surface.mesh.faces
    mixed = surface.frame.to_local(surface.mesh.vertices)
    n_mixed = face_normals(mixed, f, normalize=False)
    n_pure = face_normals(pure_vertices, f, normalize=False)
    return int(np.sum(np.einsum("ij,ij->i", n_mixed, n_pure) <= 0))


def signed_distance(points: np.ndarray, mesh: MeshData, projector: MeshProjector | None = None) -> np.ndarray:
    """Jarak bertanda titik ke permukaan mesh (positif di luar).

    Tanda dari jumlah normal vertex (berbobot luas) face terdekat, bukan normal face itu saja: bila titik terdekat
    jatuh di edge atau vertex mesh berderau, normal satu face bisa salah sisi dan jarak minimum melompat (terukur
    di benchmark §5.4: lebar berubah 2 um, jarak minimum berubah dari +83 ke -244 um)."""
    projector = projector or MeshProjector(mesh)
    closest, face, dist = projector.closest(np.asarray(points, float))
    vertices = np.asarray(mesh.vertices, float)
    faces = np.asarray(mesh.faces)
    cache = getattr(projector, "_vertex_normals", None)
    if cache is None or len(cache) != len(vertices):
        cache = vertex_normals(vertices, faces)
        projector._vertex_normals = cache
    normals = cache[faces[face]].sum(axis=1)
    sign = np.sign(np.einsum("ij,ij->i", np.asarray(points, float) - closest, normals))
    sign[sign == 0] = 1.0
    return sign * dist


@dataclass
class CrownFit:
    surface: CrownSurface
    iterations: int
    distances: dict  # nama -> jarak bertanda minimum terakhir (mm)
    hints: list = field(default_factory=list)  # catatan "perlu dicek" (bahasa Inggris untuk UI)


def initial_template(fdi: int, frame: CrownFrame, margin_local: np.ndarray, prep_top_mm: float,
                     params: CrownParams = CrownParams()) -> TemplateParams:
    """Ukuran awal dari kasus: lebar = lebar margin + tonjolan kontur, tinggi = minimum dari ketebalan IVO."""
    kind = fdi_kind(fdi)
    md = margin_local[:, 0].max() - margin_local[:, 0].min() + 2 * params.contour_bulge_mm
    bl = margin_local[:, 1].max() - margin_local[:, 1].min() + 2 * params.contour_bulge_mm
    base = float(margin_local[:, 2].mean())
    tpl = TemplateParams(kind, md, bl, height=base + 10.0, base_z=base)
    return tpl.with_(height=minimum_height(tpl, prep_top_mm, params))


def minimum_height(template: TemplateParams, prep_top_mm: float, params: CrownParams) -> float:
    """Tinggi terendah supaya titik terendah meja oklusal (fossa) >= puncak preparasi + gap + ketebalan minimum.
    Perkiraan kasar; cek ketebalan lengkap di §5.6."""
    s = template.shape
    floor = s.relief_mm * (1.0 - relief_floor_fraction(s))
    return prep_top_mm + params.cement_gap_mm + params.min_occlusal_thickness_mm + floor


def _min_distance(surface: CrownSurface, mesh: MeshData, projector: MeshProjector) -> float:
    return float(signed_distance(surface.mesh.vertices, mesh, projector).min())


def fit_crown(fdi: int, margin: np.ndarray, axis, mesial, prep_top_mm: float, mesial_mesh: MeshData | None = None,
              distal_mesh: MeshData | None = None, antagonist: MeshData | None = None,
              params: CrownParams = CrownParams()) -> CrownFit:
    """Langkah 1 sampai 3: template per FDI, penempatan dari margin dan sumbu, penyesuaian ke tetangga dan antagonis.

    Tepi mesial (x = c + W/2), tepi distal (x = c - W/2), dan tinggi H digeser sejauh selisih jarak bertanda
    terukur terhadap target (dengan peredam yang mengecil bila tanda selisih berbalik), berulang sampai semua
    selisih <= toleransi. Ruang yang memaksa lebar di bawah lebar
    margin atau tinggi di bawah minimum ketebalan berakhir dengan CrownError, bukan crown yang menembus tetangga."""
    frame = make_frame(margin, axis, mesial)
    phi, m_local = margin_by_angle(frame, margin)
    tpl = initial_template(fdi, frame, m_local, prep_top_mm, params)
    hints = []
    if mesial_mesh is None and distal_mesh is None:
        hints.append("no neighbouring teeth: mesial direction and width come from the margin; check them")
    if antagonist is None:
        hints.append("no antagonist: height comes from the minimum occlusal thickness; check it")
    h_min = minimum_height(tpl, prep_top_mm, params)
    w_min = float(m_local[:, 0].max() - m_local[:, 0].min())
    x_mesial = float(m_local[:, 0].max()) + params.contour_bulge_mm
    x_distal = float(m_local[:, 0].min()) - params.contour_bulge_mm
    height = tpl.height
    projectors = {name: MeshProjector(mesh) for name, mesh in
                  (("mesial", mesial_mesh), ("distal", distal_mesh), ("antagonist", antagonist)) if mesh is not None}
    meshes = {"mesial": mesial_mesh, "distal": distal_mesh, "antagonist": antagonist}
    targets = {"mesial": params.approximal_distance_mm, "distal": params.approximal_distance_mm,
               "antagonist": params.occlusal_distance_mm}
    distances = {}
    surface = None
    previous = {}
    damping = {name: 1.0 for name in projectors}
    for iteration in range(1, params.max_iterations + 1):
        center = 0.5 * (x_mesial + x_distal)
        width = x_mesial - x_distal
        local_frame = frame.shifted(center)
        tpl = tpl.with_(width_md=width, height=height)
        surface = crown_surface(local_frame, tpl, m_local - np.array([center, 0.0, 0.0]), phi, params.blend_fraction)
        distances = {name: _min_distance(surface, meshes[name], proj) for name, proj in projectors.items()}
        errors = {name: d - targets[name] for name, d in distances.items()}
        if all(abs(e) <= params.tolerance_mm for e in errors.values()):
            break
        # Langkah = selisih x faktor peredam; faktor dibagi dua setiap kali tanda selisih berbalik. Pada permukaan
        # berderau jarak minimum bisa berpindah antar titik kontak, dan langkah penuh lalu berosilasi.
        for name, e in errors.items():
            if name in previous and np.sign(e) != np.sign(previous[name]):
                damping[name] *= 0.5
        previous = errors
        if "mesial" in errors:
            x_mesial += damping["mesial"] * errors["mesial"]
        if "distal" in errors:
            x_distal -= damping["distal"] * errors["distal"]
        if "antagonist" in errors:
            height += damping["antagonist"] * errors["antagonist"]
        if x_mesial - x_distal < w_min:
            raise CrownError(f"mesiodistal space too narrow: the crown would be {x_mesial - x_distal:.2f} mm wide, "
                             f"narrower than the margin ({w_min:.2f} mm)")
        if height < h_min:
            raise CrownError(f"occlusal space too narrow: the antagonist allows a crown height of {height:.2f} mm, "
                             f"below the minimum {h_min:.2f} mm for the material thickness")
    else:
        raise CrownError(f"crown fit did not converge in {params.max_iterations} iterations: "
                         + ", ".join(f"{k} {1000 * (d - targets[k]):+.0f} um" for k, d in distances.items()))
    return CrownFit(surface, iteration, distances, hints)


def prep_top_height(vertices: np.ndarray, margin: np.ndarray, axis) -> float:
    """Tinggi puncak preparasi di atas titik berat margin, sepanjang sumbu insersi (frame crown)."""
    z = np.asarray(axis, float)
    z = z / np.linalg.norm(z)
    return float(np.max((np.asarray(vertices, float) - np.asarray(margin, float).mean(axis=0)) @ z))


def mesial_from_neighbors(margin: np.ndarray, axis, mesial_mesh: MeshData | None,
                          distal_mesh: MeshData | None) -> np.ndarray | None:
    """Arah mesial dari gigi tetangga (titik berat mesh): dari tetangga distal ke mesial, atau dari pusat margin ke
    tetangga yang ada. None bila tidak ada tetangga (arah ditentukan pengguna lewat panah, K9)."""
    center = np.asarray(margin, float).mean(axis=0)
    if mesial_mesh is not None and distal_mesh is not None:
        direction = np.asarray(mesial_mesh.vertices).mean(axis=0) - np.asarray(distal_mesh.vertices).mean(axis=0)
    elif mesial_mesh is not None:
        direction = np.asarray(mesial_mesh.vertices).mean(axis=0) - center
    elif distal_mesh is not None:
        direction = center - np.asarray(distal_mesh.vertices).mean(axis=0)
    else:
        return None
    z = np.asarray(axis, float) / np.linalg.norm(axis)
    direction = direction - (direction @ z) * z
    return direction / np.linalg.norm(direction)
