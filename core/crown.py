# SPDX-License-Identifier: GPL-3.0-or-later
"""Proposal crown berlabuh margin (docs/PHASE2.md §5.4 langkah 1 sampai 5).

Bukan morphing mesh: permukaan luar dibangun langsung sebagai S(phi, v) = T(phi, v) + (1 - w) (C(phi, v) - T(phi, v)),
dengan T template parametrik (core/template.py) yang dasarnya mengikuti tinggi margin per sudut, dan C permukaan
sepertiga servikal: dari titik margin terkonfirmasi M(phi) naik dengan sudut emergence terhadap sumbu insersi,
C = M + h (tan(alpha) n + z), n = normal mendatar kurva margin ke luar, h = tinggi di atas margin pada sudut yang sama
(C dan T sama tinggi, jadi campuran hanya menggeser mendatar). w = 0 di sepertiga servikal dinding, lalu
smoothstep sampai 1 sejauh blend_height_mm di atasnya. Jadi S(phi, 0) = M(phi) menurut konstruksi, tanpa deformasi
Laplacian dan tanpa handle/target dari perpotongan garis (paten PAT4), dan tanpa arsip kasus atau pencarian kemiripan
margin (PAT5).

Penyesuaian ke gigi tetangga dan antagonis mengubah parameter global template (tepi mesial, tepi distal, tinggi)
dengan iterasi skalar per parameter: setiap tepi digeser sejauh selisih jarak bertanda terukur terhadap target.
Langkah 4: border IVO (bagian horizontal lalu bagian bersudut) dari margin; S dimulai di ujung atas border, jadi
"margin" di rumus atas sejak langkah 4 adalah cincin B2 (crown_border). Langkah 5: assemble_crown menyatukan
permukaan dalam §5.3, strip penghubung, border, dan S menjadi solid yang divalidasi manifold3d.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from .geometry import MeshProjector, face_normals, vertex_normals
from .mesh_data import MeshData
from .spacer import SLIVER_MM
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
    min_thickness_posterior_mm: float = 1.0  # default pabrikan IVO "Minimal thickness" premolar/molar
    min_thickness_anterior_mm: float = 0.8  # default pabrikan IVO "Minimal thickness" anterior
    cement_gap_mm: float = 0.06  # default pabrikan IVO, untuk tinggi minimum
    emergence_angle_deg: float = 19.0  # literatur, perlu kalibrasi (Monaco 2026): sepertiga servikal
    cervical_fraction: float = 1.0 / 3.0  # keputusan maintainer: bagian dinding yang dibangun dari margin
    blend_height_mm: float = 1.0  # perlu kalibrasi: tinggi zona campur margin ke template di atas margin
    border_horizontal_mm: float = 0.20  # default pabrikan IVO "Horizontal margin thickness"
    border_angled_mm: float = 0.10  # default pabrikan IVO "Angled margin thickness"
    border_angle_deg: float = 65.0  # default pabrikan IVO "Crown margin angle"; terhadap sumbu: interpretasi S4
    strip_mm: float = 0.30  # ambang algoritma: jarak minimum kurva potong permukaan dalam ke margin (langkah 5)
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
    mesh: MeshData  # dunia; tepi bawah = ujung atas border (B2), titik tengah oklusal ditutup
    border: np.ndarray | None = None  # (3, N_PHI, 3) cincin M, B1, B2 di frame lokal yang sama


def margin_normals(margin_local: np.ndarray) -> np.ndarray:
    """Normal mendatar (xy) kurva margin ke luar, dari beda pusat titik tetangga (urutan sudut naik)."""
    xy = margin_local[:, :2]
    tangent = np.roll(xy, -1, axis=0) - np.roll(xy, 1, axis=0)
    normal = np.stack([tangent[:, 1], -tangent[:, 0]], axis=1)
    normal /= np.linalg.norm(normal, axis=1, keepdims=True)
    if np.mean(np.einsum("ij,ij->i", normal, xy - xy.mean(axis=0))) < 0:
        normal = -normal
    return normal


def cervical_height(template: TemplateParams, margin_local: np.ndarray, params: "CrownParams") -> np.ndarray:
    """Tinggi sepertiga servikal per sudut: cervical_fraction x tinggi dinding (margin ke tepi meja oklusal)."""
    return params.cervical_fraction * (template.wall_top_z - margin_local[:, 2])


def cervical_bulge(template: TemplateParams, margin_local: np.ndarray, params: "CrownParams") -> float:
    """Pelebaran mendatar rata-rata di puncak sepertiga servikal (tan(sudut emergence) x tingginya)."""
    return float(np.mean(cervical_height(template, margin_local, params))
                 * np.tan(np.radians(params.emergence_angle_deg)))


def crown_surface(frame: CrownFrame, template: TemplateParams, margin_local: np.ndarray, phi: np.ndarray,
                  params: "CrownParams" = None, n_v: int = N_V) -> CrownSurface:
    """S(phi, v) berlabuh margin. margin_local dari margin_by_angle (frame yang sama).

    Riwayat (§5.4): versi pertama memakai dasar rata dan zona campur sebagai fraksi v, dan terlipat di scallop dalam;
    versi kedua (dasar per sudut, zona campur dalam mm, template sampai ke margin) tanpa lipatan, tetapi sudut
    emergence 1 mm pertama 16-43° (median), karena dinding template sendiri melebar cepat di atas servikal. Sekarang
    sepertiga servikal dibangun dari margin dengan sudut emergence."""
    params = params or CrownParams()
    base = margin_local[:, 2]
    if np.any(base >= template.wall_top_z):
        raise CrownError("the margin reaches the occlusal table")
    h_c = cervical_height(template, margin_local, params)
    room = (template.wall_top_z - base) - h_c
    if np.any(room < params.blend_height_mm):
        raise CrownError(f"the crown wall above the cervical third is {room.min():.2f} mm high at the highest margin "
                         f"point, less than the blend height {params.blend_height_mm:.2f} mm")
    v = np.linspace(0.0, 1.0, n_v)
    tpl = template_points(template, phi[:, None], v[None, :], base_z=base[:, None])
    h = tpl[..., 2] - base[:, None]
    blend = params.blend_height_mm
    w = _smoothstep((h - h_c[:, None]) / blend) if blend > 0 else (h > h_c[:, None]).astype(float)
    w[:, v > template.v_wall] = 1.0  # meja oklusal: template murni (relief bisa turun di bawah tepi dinding)
    normal = margin_normals(margin_local)
    cone = np.empty_like(tpl)
    cone[..., :2] = margin_local[:, None, :2] + (h * np.tan(np.radians(params.emergence_angle_deg)))[..., None] \
        * normal[:, None, :]
    cone[..., 2] = tpl[..., 2]  # sama tinggi dengan template: campuran hanya menggeser mendatar
    local = tpl + (1.0 - w)[..., None] * (cone - tpl)
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


def _flipped_mask(surface: CrownSurface) -> tuple[np.ndarray, np.ndarray]:
    pure = template_points(surface.template, surface.phi[:, None], surface.v[None, :])
    pure[:, -1, :] = pure[0, -1, :]
    pure_vertices = np.vstack([pure[:, :-1, :].reshape(-1, 3), pure[0, -1][None]])
    f = surface.mesh.faces
    mixed = surface.frame.to_local(surface.mesh.vertices)
    n_mixed = face_normals(mixed, f, normalize=False)
    n_pure = face_normals(pure_vertices, f, normalize=False)
    corners = mixed[f]
    longest = np.max(np.stack([np.linalg.norm(corners[:, k] - corners[:, (k + 1) % 3], axis=1) for k in range(3)]),
                     axis=0)
    height = np.linalg.norm(n_mixed, axis=1) / np.maximum(longest, 1e-12)
    return np.einsum("ij,ij->i", n_mixed, n_pure) <= 0, height < SLIVER_MM


def flipped_faces(surface: CrownSurface) -> int:
    """Lipatan: face yang normalnya berbalik arah dibanding face yang sama pada template murni berdasar rata
    (topologi sama, dasar = tinggi rata-rata margin, tanpa campuran margin). Template itu sendiri tidak terlipat
    (diuji terpisah)."""
    return int(_flipped_mask(surface)[0].sum())


def non_sliver_folds(surface: CrownSurface) -> int:
    """Lipatan tanpa segitiga sliver (tinggi segitiga < SLIVER_MM, sama dengan §5.3): sliver bisa berbalik oleh beda
    normal kecil tanpa permukaan terlipat."""
    flipped, sliver = _flipped_mask(surface)
    return int(np.sum(flipped & ~sliver))


def emergence_angles(surface: CrownSurface, height_mm: float = 1.0) -> np.ndarray:
    """Sudut emergence per sudut keliling (derajat): sudut tali busur permukaan luar terhadap sumbu insersi dari tepi
    servikal sampai height_mm di atasnya, diproyeksikan ke normal mendatar kurva tepi servikal (positif bila crown
    melebar ke luar). Sampai border (langkah 4) ada, tepi servikal adalah margin; sesudahnya diukur dari tepi atas
    border. Versi kedua §5.4 memakai arah radial dari sumbu, bukan normal kurva."""
    local = surface.local
    wall = surface.v <= surface.template.v_wall
    normals = margin_normals(local[:, 0, :])
    out = np.empty(len(local))
    for i, column in enumerate(local):
        col = column[wall]
        h = col[:, 2] - col[0, 2]
        if h[-1] < height_mm:
            raise CrownError("crown wall lower than the emergence measuring height")
        top = np.array([np.interp(height_mm, h, col[:, k]) for k in range(2)])
        out[i] = np.degrees(np.arctan2((top - col[0, :2]) @ normals[i], height_mm))
    return out


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
    """Ukuran awal dari kasus: tinggi = minimum dari ketebalan IVO; lebar = lebar margin + 2 x pelebaran di puncak
    sepertiga servikal (sudut emergence), supaya template di atasnya menyambung tanpa undakan."""
    kind = fdi_kind(fdi)
    md = margin_local[:, 0].max() - margin_local[:, 0].min()
    bl = margin_local[:, 1].max() - margin_local[:, 1].min()
    base = float(margin_local[:, 2].mean())
    tpl = TemplateParams(kind, md, bl, height=base + 10.0, base_z=base)
    tpl = tpl.with_(height=minimum_height(tpl, prep_top_mm, params))
    bulge = cervical_bulge(tpl, margin_local, params)
    return tpl.with_(width_md=md + 2 * bulge, width_bl=bl + 2 * bulge)


def minimum_height(template: TemplateParams, prep_top_mm: float, params: CrownParams) -> float:
    """Tinggi terendah supaya titik terendah meja oklusal (fossa) >= puncak preparasi + gap + ketebalan minimum.
    Perkiraan kasar; cek ketebalan lengkap di §5.6."""
    s = template.shape
    floor = s.relief_mm * (1.0 - relief_floor_fraction(s))
    thickness = (params.min_thickness_anterior_mm if template.kind in ("incisor", "canine")
                 else params.min_thickness_posterior_mm)
    return prep_top_mm + params.cement_gap_mm + thickness + floor


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
    phi, margin_ring = margin_by_angle(frame, margin)
    border = crown_border(margin_ring, params)
    m_local = border[2]  # permukaan luar mulai di ujung atas border
    tpl = initial_template(fdi, frame, m_local, prep_top_mm, params)
    hints = []
    if mesial_mesh is None and distal_mesh is None:
        hints.append("no neighbouring teeth: mesial direction and width come from the margin; check them")
    if antagonist is None:
        hints.append("no antagonist: height comes from the minimum occlusal thickness; check it")
    h_min = minimum_height(tpl, prep_top_mm, params)
    w_min = float(m_local[:, 0].max() - m_local[:, 0].min())
    bulge = 0.5 * (tpl.width_md - w_min)
    x_mesial = float(m_local[:, 0].max()) + bulge
    x_distal = float(m_local[:, 0].min()) - bulge
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
        shift = np.array([center, 0.0, 0.0])
        surface = crown_surface(local_frame, tpl, m_local - shift, phi, params)
        surface.border = border - shift
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
                             f"narrower than the margin with its border ({w_min:.2f} mm)")
        if height < h_min:
            raise CrownError(f"occlusal space too narrow: the antagonist allows a crown height of {height:.2f} mm, "
                             f"below the minimum {h_min:.2f} mm for the material thickness")
    else:
        raise CrownError(f"crown fit did not converge in {params.max_iterations} iterations: "
                         + ", ".join(f"{k} {1000 * (d - targets[k]):+.0f} um" for k, d in distances.items()))
    return CrownFit(surface, iteration, distances, hints)


def crown_border(margin_local: np.ndarray, params: CrownParams) -> np.ndarray:
    """Border crown IVO di margin (langkah 4), cincin (3, N, 3): margin M, ujung bagian horizontal B1, dan ujung bagian
    bersudut B2, tempat permukaan luar mulai.

    B1 = M + w n, B2 = B1 + l (sin(a) n + cos(a) z), n = normal mendatar kurva margin ke luar, w = border horizontal,
    l = panjang bagian bersudut, a = sudut bagian bersudut terhadap sumbu insersi. Acuan sudut terhadap sumbu insersi
    adalah interpretasi (S4, PHASE2.md §5.4): IVO dan DTX tidak menyebut acuannya.

    Error eksplisit bila cincin border terlipat (kelengkungan margin lebih tajam daripada lebar border): tangen
    mendatar B1 atau B2 berbalik arah dibanding tangen margin."""
    normal = margin_normals(margin_local)
    n3 = np.concatenate([normal, np.zeros((len(normal), 1))], axis=1)
    a = np.radians(params.border_angle_deg)
    b1 = margin_local + params.border_horizontal_mm * n3
    b2 = b1 + params.border_angled_mm * (np.sin(a) * n3 + np.cos(a) * np.array([0.0, 0.0, 1.0]))

    def tangent(ring):
        return (np.roll(ring, -1, axis=0) - np.roll(ring, 1, axis=0))[:, :2]

    t_m = tangent(margin_local)
    for name, ring in (("horizontal", b1), ("angled", b2)):
        bad = np.flatnonzero(np.einsum("ij,ij->i", tangent(ring), t_m) <= 0)
        if len(bad):
            deg = np.degrees(np.arctan2(margin_local[bad[0], 1], margin_local[bad[0], 0])) % 360
            raise CrownError(f"the crown border ({name} part) folds over itself at {deg:.0f} deg around the axis: "
                             "the margin curves more tightly than the border width")
    return np.stack([margin_local, b1, b2])


def border_sections(border: np.ndarray, n_cuts: int = 64) -> dict:
    """Ukur border di n_cuts potongan: bidang yang memuat sumbu insersi dan normal mendatar margin, di tengah segmen
    margin (bukan di vertex, supaya potongan memotong segmen setiap cincin). Lebar horizontal, panjang bagian
    bersudut, dan sudutnya terhadap sumbu insersi, dari titik potong cincin M, B1, dan B2."""
    m, b1, b2 = border
    n = len(m)
    z = np.array([0.0, 0.0, 1.0])
    width, angled, angle, tilt = [], [], [], []
    for k in range(n_cuts):
        i = (k * n) // n_cuts
        p = 0.5 * (m[i] + m[(i + 1) % n])
        t = m[(i + 1) % n] - m[i]
        t[2] = 0.0
        t /= np.linalg.norm(t)
        h = np.array([t[1], -t[0], 0.0])

        def cut(ring):
            best = None
            for s in range(i - 4, i + 5):
                r0, r1 = ring[s % n], ring[(s + 1) % n]
                d0, d1 = (r0 - p) @ t, (r1 - p) @ t
                if d0 * d1 <= 0 and d0 != d1:
                    q = r0 + d0 / (d0 - d1) * (r1 - r0)
                    if best is None or np.linalg.norm(q - p) < np.linalg.norm(best - p):
                        best = q
            if best is None:
                raise CrownError(f"border section {k} does not cross the border rings")
            return best

        pm, p1, p2 = cut(m), cut(b1), cut(b2)
        width.append((p1 - pm) @ h)
        tilt.append(abs((p1 - pm) @ z))
        seg = p2 - p1
        angled.append(np.linalg.norm(seg))
        angle.append(np.degrees(np.arccos(np.clip(seg @ z / np.linalg.norm(seg), -1.0, 1.0))))
    return {"horizontal_mm": np.array(width), "horizontal_rise_mm": np.array(tilt), "angled_mm": np.array(angled),
            "angle_deg": np.array(angle)}


def boundary_loops(mesh: MeshData) -> list[np.ndarray]:
    """Loop tepi (edge yang dipakai satu face), masing-masing berurutan mengikuti arah edge di face-nya."""
    faces = np.asarray(mesh.faces)
    directed = np.concatenate([faces[:, [0, 1]], faces[:, [1, 2]], faces[:, [2, 0]]])
    key = np.sort(directed, axis=1)
    _, inverse, counts = np.unique(key, axis=0, return_inverse=True, return_counts=True)
    boundary = directed[counts[inverse.ravel()] == 1]
    following = {}
    for a, b in boundary:
        if a in following:
            raise CrownError("the inner surface boundary is not a simple loop (a vertex has two outgoing edges)")
        following[int(a)] = int(b)
    loops, seen = [], set()
    for start in following:
        if start in seen:
            continue
        loop = [start]
        seen.add(start)
        nxt = following[start]
        while nxt != start:
            if nxt in seen or nxt not in following:
                raise CrownError("the inner surface boundary is not a simple loop")
            loop.append(nxt)
            seen.add(nxt)
            nxt = following[nxt]
        loops.append(np.array(loop))
    return loops


def _arc_parameter(points: np.ndarray) -> np.ndarray:
    """Parameter 0..1 sepanjang loop tertutup (panjang busur kumulatif) mulai dari titik pertama."""
    seg = np.linalg.norm(np.diff(np.vstack([points, points[:1]]), axis=0), axis=1)
    return np.concatenate([[0.0], np.cumsum(seg)[:-1]]) / seg.sum()


def _projected_parameter(points: np.ndarray, ring: np.ndarray) -> np.ndarray:
    """Parameter panjang busur ring (0..1) dari titik terdekat di polyline ring untuk setiap titik, dibuka kontinu
    dari titik pertama (di sekitar 0) dan dibuat monoton naik."""
    closed = np.vstack([ring, ring[:1]])
    seg = np.diff(closed, axis=0)
    lengths = np.linalg.norm(seg, axis=1)
    cum = np.concatenate([[0.0], np.cumsum(lengths)])
    rel = points[:, None, :] - closed[None, :-1, :]
    s = np.clip(np.einsum("ijk,jk->ij", rel, seg) / np.maximum(lengths ** 2, 1e-24), 0.0, 1.0)
    dist = np.linalg.norm(rel - s[..., None] * seg[None], axis=2)
    j = np.argmin(dist, axis=1)
    u = (cum[j] + s[np.arange(len(points)), j] * lengths[j]) / cum[-1]
    step = np.diff(u)
    step -= np.round(step)
    u = u[0] - np.round(u[0]) + np.concatenate([[0.0], np.cumsum(step)])
    u = np.maximum.accumulate(u)
    return np.clip(u - u[0] + max(u[0], 0.0), 0.0, np.nextafter(1.0, 0.0))


STRIP_MAX_DRIFT = 0.02  # beda parameter (bagian keliling) maksimum yang boleh dibuat perbaikan lokal zipper


def strip_triangles(inner: np.ndarray, outer: np.ndarray, inner_ids: np.ndarray, outer_ids: np.ndarray,
                    inner_normals: np.ndarray) -> np.ndarray:
    """Strip zipper antara kurva potong permukaan dalam (inner) dan margin (outer), keduanya urut sudut naik dan
    inner[0] terdekat ke outer[0]. Parameter: panjang busur margin, dan untuk inner proyeksi ke margin (dibuat
    monoton). Panjang busur inner sendiri tidak dipakai: di lereng scallop margin 3D lebih panjang daripada kurva
    potong, dan kecocokan panjang busur bergeser sampai segitiga terbalik. Orientasi sama dengan baris quad (a, b, c),
    (a, c, d) permukaan luar, dengan inner sebagai baris bawah.

    Berhasil karena kurva potong mulus dan berjarak delta >= 0,3 mm dari margin (cut_inner_at_margin): langkah mundur
    kecil kurva potong (puluhan um, terukur) jauh lebih kecil daripada lebar strip. Versi pertama menyambung tepi
    mesh die yang bergerigi langsung ke margin (kadang beberapa um), dan zipper maupun poligon (u, w) lalu terlipat.

    Perbaikan lokal: bila langkah menurut parameter membuat segitiga terbalik, dipakai langkah lain; bila keduanya
    terbalik, telinga di kurva potong sendiri (inner, inner, inner) menutup tekukan kecilnya. Bila kedua langkah
    valid tetapi langkah yang dipilih membuat langkah lain tidak valid sesudahnya, langkah lain diambil dulu
    (lookahead satu langkah). Perbaikan lokal hanya boleh menggeser kedua parameter sejauh STRIP_MAX_DRIFT; tanpa batas
    ini satu langkah yang tak pernah valid lagi berkaskade menjadi fan dari satu vertex ke seluruh margin (benchmark
    tuning 2026-10-26: molar chamfer, derau 30 um, 86 segitiga terlipat). Di luar batas, langkah menurut parameter
    dipakai dan pemeriksaan akhir di bawah menjadi error eksplisit.

    Error eksplisit bila segitiga strip yang bukan sliver menghadap searah normal die (inner_normals, normal die ke
    luar di vertex inner, dirata-rata area_weighted_normals): strip adalah dinding dalam crown, jadi wajib menghadap
    ke die."""
    u_in, u_out = _projected_parameter(inner, outer), _arc_parameter(outer)
    n_out = len(outer)
    chain = list(range(len(inner))) + [0]  # loop dalam ditutup; telinga L-L-L menghapus vertex dari rantai
    u_chain = list(u_in) + [1.0]

    def valid(a, b, c, ref) -> bool:
        normal = np.cross(b - a, c - a)
        longest = max(np.linalg.norm(b - a), np.linalg.norm(c - b), np.linalg.norm(a - c))
        return float(normal @ inner_normals[ref]) < 0 or np.linalg.norm(normal) / max(longest, 1e-12) < SLIVER_MM

    tris = []
    i = j = 0
    while i < len(chain) - 1 or j < n_out:
        can_in, can_out = i < len(chain) - 1, j < n_out
        a = chain[i]
        next_out = u_out[j + 1] if j + 1 < n_out else 1.0
        prefer_in = can_in and (not can_out or u_chain[i + 1] <= next_out)
        ok_in = can_in and valid(inner[a], inner[chain[i + 1]], outer[j % n_out], a)
        ok_out = can_out and valid(inner[a], outer[(j + 1) % n_out], outer[j % n_out], a)
        lag = u_chain[i] - (u_out[j] if j < n_out else 1.0)  # > 0: kurva potong di depan margin
        may_out, may_in = lag > -STRIP_MAX_DRIFT, lag < STRIP_MAX_DRIFT
        if ok_in and ok_out and can_out and i + 1 < len(chain) - 1:
            # Lihat satu langkah ke depan: langkah yang hanya valid sekarang diambil dulu. Tanpa ini, vertex kurva
            # potong yang menonjol ke margin (derau pada chamfer landai) tidak pernah tersambung lagi setelah margin
            # maju satu langkah, dan fan dari vertex sebelumnya menghabiskan seluruh margin.
            b, b_out = chain[i + 1], (j + 1) % n_out
            if not prefer_in and may_in and not valid(inner[a], inner[b], outer[b_out], a):
                prefer_in = True
            elif prefer_in and may_out and not valid(inner[b], outer[b_out], outer[j % n_out], b):
                prefer_in = False
        elif prefer_in and not ok_in and ok_out and may_out:
            prefer_in = False
        elif not prefer_in and not ok_out and ok_in and may_in:
            prefer_in = True
        elif not ok_in and not ok_out and i + 2 < len(chain):
            b, c = chain[i + 1], chain[i + 2]
            normal = np.cross(inner[b] - inner[a], inner[c] - inner[a])
            if float(normal @ inner_normals[b]) < 0:  # telinga L-L-L menghadap die: menutup tekukan
                tris.append((inner_ids[a], inner_ids[b], inner_ids[c]))
                del chain[i + 1], u_chain[i + 1]
                continue
        if prefer_in:
            tris.append((inner_ids[a], inner_ids[chain[i + 1]], outer_ids[j % n_out]))
            i += 1
        else:
            tris.append((inner_ids[a], outer_ids[(j + 1) % n_out], outer_ids[j % n_out]))
            j += 1
    tris = np.array(tris, dtype=np.int64)
    lookup = {int(v): k for k, v in enumerate(inner_ids)}
    position = {int(v): outer[k] for k, v in enumerate(outer_ids)}
    corners = np.array([[inner[lookup[int(v)]] if int(v) in lookup else position[int(v)] for v in tri] for tri in tris])
    refs = np.array([lookup[int(tri[0])] for tri in tris])
    normal = np.cross(corners[:, 1] - corners[:, 0], corners[:, 2] - corners[:, 0])
    longest = np.max(np.stack([np.linalg.norm(corners[:, k] - corners[:, (k + 1) % 3], axis=1) for k in range(3)]),
                     axis=0)
    height = np.linalg.norm(normal, axis=1) / np.maximum(longest, 1e-12)
    facing = np.einsum("ij,ij->i", normal, inner_normals[refs])
    bad = (facing >= 0) & (height >= SLIVER_MM)
    if bad.any():
        raise CrownError(f"the strip between the cement spacer and the margin folds ({int(bad.sum())} triangles)")
    return tris


def _oriented_loop(inner: MeshData, frame: CrownFrame, margin_ring: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Satu-satunya loop tepi permukaan dalam, urut sudut naik dan mulai di vertex terdekat ke margin[0]."""
    loops = boundary_loops(inner)
    if len(loops) != 1:
        raise CrownError(f"the inner surface (cement spacer) has {len(loops)} boundary loops, expected 1")
    loop = loops[0]
    local = frame.to_local(np.asarray(inner.vertices, float)[loop])
    ang = np.unwrap(np.arctan2(local[:, 1], local[:, 0]))
    if ang[-1] < ang[0]:  # urutan searah jarum jam: balik supaya sudut naik seperti margin
        loop, local = loop[::-1], local[::-1]
    start = int(np.argmin(np.linalg.norm(local - margin_ring[0], axis=1)))
    return np.roll(loop, -start), np.roll(local, -start, axis=0)


HOLE_FILL_MAX_VERTICES = 12  # lubang kecil di permukaan dalam (face pita margin yang terlewat §5.3) ditutup fan


def fill_small_holes(inner: MeshData) -> tuple[MeshData, int, np.ndarray]:
    """Tutup lubang kecil permukaan dalam dengan fan (orientasi mengikuti face di sekitarnya). Loop tepi terpanjang
    adalah tepi luar (dekat margin) dan dikembalikan. Lubang yang lebih besar dari HOLE_FILL_MAX_VERTICES vertex
    menjadi error eksplisit."""
    loops = sorted(boundary_loops(inner), key=len, reverse=True)
    if not loops:
        raise CrownError("the inner surface (cement spacer) has no open edge at the margin")
    # Dipanggil setelah cut_inner_at_margin: loop terpanjang adalah kurva potong, sisanya lubang.
    fill = []
    for hole in loops[1:]:
        if len(hole) > HOLE_FILL_MAX_VERTICES:
            raise CrownError(f"the inner surface (cement spacer) has a hole with {len(hole)} edges")
        fill += [(hole[0], hole[k + 1], hole[k]) for k in range(1, len(hole) - 1)]
    faces = np.asarray(inner.faces)
    if fill:
        faces = np.vstack([faces, np.array(fill, dtype=np.int64)])
    return MeshData(np.asarray(inner.vertices, float), faces), len(loops) - 1, loops[0]


def _smooth_values(mesh: MeshData, values: np.ndarray, passes: int) -> np.ndarray:
    """Perataan nilai per vertex: setiap putaran v = (v + rata-rata tetangga) / 2."""
    from scipy.sparse import coo_matrix

    faces = np.asarray(mesh.faces)
    n = len(mesh.vertices)
    rows = np.concatenate([faces[:, 0], faces[:, 1], faces[:, 2], faces[:, 1], faces[:, 2], faces[:, 0]])
    cols = np.concatenate([faces[:, 1], faces[:, 2], faces[:, 0], faces[:, 0], faces[:, 1], faces[:, 2]])
    adjacency = coo_matrix((np.ones(len(rows)), (rows, cols)), shape=(n, n)).tocsr()
    adjacency.data[:] = 1.0
    degree = np.maximum(np.asarray(adjacency.sum(axis=1)).ravel(), 1.0)
    for _ in range(passes):
        values = 0.5 * values + 0.5 * (adjacency @ values) / degree
    return values


EDGE_REACH_MM = 0.6  # vertex tepi spacer sejauh ini dari margin dianggap tepi luar; lebih jauh = lubang


def _largest_component(mesh: MeshData) -> MeshData:
    """Komponen face terhubung terbesar (vertex yang tidak terpakai dibuang)."""
    from scipy.sparse import coo_matrix
    from scipy.sparse.csgraph import connected_components

    vertices = np.asarray(mesh.vertices, float)
    faces = np.asarray(mesh.faces)
    n_v = len(vertices)
    rows = np.concatenate([faces[:, 0], faces[:, 1], faces[:, 2]])
    cols = np.concatenate([faces[:, 1], faces[:, 2], faces[:, 0]])
    _, label = connected_components(coo_matrix((np.ones(len(rows)), (rows, cols)), shape=(n_v, n_v)), directed=False)
    face_label = label[faces[:, 0]]
    faces = faces[face_label == np.bincount(face_label).argmax()]
    used = np.zeros(n_v, dtype=bool)
    used[faces.ravel()] = True
    remap = np.full(n_v, -1)
    remap[used] = np.arange(int(used.sum()))
    return MeshData(vertices[used], remap[faces])


def cut_inner_at_margin(inner: MeshData, margin_world: np.ndarray, strip_mm: float,
                        smooth_passes: int = 3) -> tuple[MeshData, float]:
    """Potong permukaan dalam tepat di kurva level jarak ke margin = delta (marching triangles): face dengan semua
    vertex >= delta dipertahankan, face yang terpotong dibagi di titik potong edge, sisanya dibuang. Titik potong ada
    di edge spacer, jadi permukaan dalam tetap persis spacer untuk jarak >= delta; di bawahnya diganti strip.

    Jarak = jarak geodesik di permukaan dalam dari margin (core/geodesic.py) pada komponen terbesar. Jarak Euclid 3D
    ke kurva margin dicoba dulu: tidak monoton di mesh die, kurva level membentuk kantong kecil, dan strip terlipat.
    Jarak geodesik juga diratakan smooth_passes putaran (nilai, bukan posisi): di dalam face besar yang dilintasi
    miring, arah kurva level mengikuti galat jarak per vertex, dan kurva potong mundur sampai 0,24 mm.

    delta = max(strip_mm, jarak terjauh vertex tepi spacer asal yang masih dalam EDGE_REACH_MM dari margin + 0,05 mm),
    satu nilai untuk seluruh margin, supaya kurva potong tidak menyentuh tepi asal. Tepi asal adalah edge mesh die
    yang bergerigi (sampai 0,3 mm dari margin, kadang beberapa um, pada derau bisa melewati margin atau membentuk
    bow-tie), dan strip yang langsung ke sana terlipat (PHASE2.md §5.4). delta lokal per titik margin juga dicoba:
    medannya tidak kontinu, kurva potong berundak, dan zipper terlipat. Mengembalikan mesh dan delta."""
    from .geodesic import distance_from_curve

    inner = _largest_component(inner)
    vertices = np.asarray(inner.vertices, float)
    faces = np.asarray(inner.faces)
    dist = distance_from_curve(inner, margin_world)
    if not np.isfinite(dist).all():
        raise CrownError("the geodesic distance to the margin is undefined on part of the inner surface")
    directed = np.concatenate([faces[:, [0, 1]], faces[:, [1, 2]], faces[:, [2, 0]]])
    _, inverse, counts = np.unique(np.sort(directed, axis=1), axis=0, return_inverse=True, return_counts=True)
    edge = np.unique(directed[counts[inverse.ravel()] == 1])
    edge = edge[dist[edge] < EDGE_REACH_MM]
    if not len(edge):
        raise CrownError("the inner surface (cement spacer) has no open edge near the margin")
    delta = max(strip_mm, float(dist[edge].max()) + 0.05)
    dist = _smooth_values(inner, dist, smooth_passes)
    f = dist - delta
    f[np.abs(f) < 1e-9] = 1e-9  # tidak ada vertex tepat di kurva level
    keep = f > 0
    new_vertices = [vertices]
    cache = {}

    def cut(a, b):
        key = (min(a, b), max(a, b))
        if key not in cache:
            s = f[a] / (f[a] - f[b])
            cache[key] = len(vertices) + len(cache)
            new_vertices.append((vertices[a] + s * (vertices[b] - vertices[a]))[None])
        return cache[key]

    out = [faces[keep[faces].all(axis=1)]]
    extra = []
    for tri in faces[keep[faces].any(axis=1) & ~keep[faces].all(axis=1)]:
        k = keep[tri]
        r = int(np.flatnonzero(k)[0]) if k.sum() == 1 else int(np.flatnonzero(~k)[0])  # vertex yang sendirian
        a, b, c = tri[r], tri[(r + 1) % 3], tri[(r + 2) % 3]  # urutan siklis asal (orientasi tetap)
        if k.sum() == 1:  # a di dalam
            extra.append((a, cut(a, b), cut(a, c)))
        else:  # a di luar, b dan c di dalam
            pb, pc = cut(a, b), cut(a, c)
            extra += [(pb, b, c), (pb, c, pc)]
    if extra:
        out.append(np.array(extra, dtype=np.int64))
    faces = np.vstack(out)
    vertices = np.vstack(new_vertices)
    # Komponen terbesar saja: pulau kecil di dekat margin (derau) dibuang.
    return _largest_component(MeshData(vertices, faces)), delta


def area_weighted_normals(mesh: MeshData, points: np.ndarray, radius_mm: float = 0.4) -> np.ndarray:
    """Normal acuan di titik: jumlah normal face (berbobot luas) yang titik beratnya dalam radius_mm, dinormalkan.
    Satu sliver terlipat (spacer §5.3 pada scallop dalam) tidak membalik acuan, sedangkan normal vertex di kurva potong
    bisa didominasi sliver itu karena face baik di sebelahnya ikut terpotong kecil."""
    from scipy.spatial import cKDTree

    vertices = np.asarray(mesh.vertices, float)
    faces = np.asarray(mesh.faces)
    weighted = face_normals(vertices, faces, normalize=False)  # panjang = 2 x luas
    centroids = vertices[faces].mean(axis=1)
    out = np.zeros((len(points), 3))
    for k, near in enumerate(cKDTree(centroids).query_ball_point(points, radius_mm)):
        if near:
            out[k] = weighted[near].sum(axis=0)
    norm = np.linalg.norm(out, axis=1, keepdims=True)
    if np.any(norm[:, 0] == 0):
        raise CrownError("no inner surface near the strip to orient it")
    return out / norm


@dataclass
class CrownSolid:
    mesh: MeshData  # dunia: permukaan luar, border, strip, permukaan dalam (dibalik)
    volume_mm3: float
    genus: int
    components: int
    sealed_voids: int
    inner_vertices: slice  # bagian mesh.vertices dari permukaan dalam: vertex spacer + titik potong di edge spacer
    strip_width_max_mm: float  # edge segitiga strip terpanjang (kurva potong permukaan dalam ke margin)
    strip_delta_mm: float  # jarak kurva potong permukaan dalam ke margin (delta)
    strip_faces: slice  # bagian mesh.faces yang menjadi strip (untuk ukur penetrasi ke die di benchmark)
    holes_filled: int  # lubang kecil permukaan dalam yang ditutup fan (deviasi dari spacer hanya di sana dan strip)


def assemble_crown(surface: CrownSurface, inner: MeshData, params: CrownParams = CrownParams()) -> CrownSolid:
    """Langkah 5: permukaan dalam §5.3 (dipotong di jarak delta dari margin, dibalik), strip dari kurva potong ke
    margin, border, dan permukaan luar menjadi satu solid, divalidasi manifold3d (watertight, satu komponen, genus 0,
    tanpa rongga, volume > 0). Loop dicocokkan lewat parameter sepanjang margin, tanpa Boolean. Setiap kegagalan
    menjadi CrownError."""
    from .solid import SolidError, sealed_void_count, to_manifold

    if surface.border is None:
        raise CrownError("the crown surface has no border")
    folds = non_sliver_folds(surface)
    if folds:
        raise CrownError(f"the outer crown surface folds ({folds} faces)")
    frame = surface.frame
    outer = surface.mesh
    n_phi = len(surface.phi)
    n_rows = len(surface.v) - 1
    m_world = frame.to_world(surface.border[0])
    b1_world = frame.to_world(surface.border[1])
    base = len(outer.vertices)
    m_ids = base + np.arange(n_phi)
    b1_ids = base + n_phi + np.arange(n_phi)
    b2_ids = np.arange(n_phi) * n_rows  # baris 0 permukaan luar
    faces = [np.asarray(outer.faces)]
    for lower, upper in ((m_ids, b1_ids), (b1_ids, b2_ids)):
        a, b = lower, np.roll(lower, -1)
        c, d = np.roll(upper, -1), upper
        faces.append(np.stack([a, b, c], axis=1))
        faces.append(np.stack([a, c, d], axis=1))

    reference = inner
    inner, delta = cut_inner_at_margin(inner, m_world, params.strip_mm)
    inner, holes, _ = fill_small_holes(inner)
    inner_v = np.asarray(inner.vertices, float)
    inner_base = base + 2 * n_phi
    loop, local = _oriented_loop(inner, frame, surface.border[0])
    inner_normals = frame.to_local(area_weighted_normals(reference, inner_v[loop]) + frame.origin)
    strip = strip_triangles(local, surface.border[0], inner_base + loop, m_ids, inner_normals)
    inner_faces = np.asarray(inner.faces)[:, ::-1] + inner_base  # normal die ke luar: dibalik untuk crown

    vertices = np.vstack([outer.vertices, m_world, b1_world, inner_v])
    corners = vertices[strip]
    strip_width = float(max(np.linalg.norm(corners[:, k] - corners[:, (k + 1) % 3], axis=1).max() for k in range(3)))
    strip_start = sum(len(f) for f in faces)
    mesh = MeshData(vertices, np.vstack(faces + [strip, inner_faces]).astype(np.int64))
    try:
        solid = to_manifold(mesh, "crown")
    except SolidError as exc:
        raise CrownError(f"the crown is not a closed solid: {exc}") from exc
    components = len(solid.decompose())
    voids = sealed_void_count(solid)
    genus = int(solid.genus())
    volume = float(solid.volume())
    if components != 1 or voids or genus != 0 or volume <= 0:
        raise CrownError(f"the crown solid is not valid: {components} components, genus {genus}, "
                         f"{voids} sealed voids, volume {volume:.2f} mm3")
    return CrownSolid(mesh, volume, genus, components, voids, slice(inner_base, inner_base + len(inner_v)),
                      strip_width, delta, slice(strip_start, strip_start + len(strip)), holes)


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
