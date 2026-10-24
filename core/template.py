# SPDX-License-Identifier: GPL-3.0-or-later
"""Template crown parametrik per jenis gigi FDI (docs/PHASE2.md §5.4 langkah 1, keputusan K2).

Bukan anatomi: semua bentuk berstatus "desain data uji". Ukuran (lebar mesiodistal, lebar bukolingual, tinggi)
selalu datang dari kasus (margin, gigi tetangga, antagonis), tidak dari tabel anatomi.

Frame template: z = sumbu insersi (oklusal), x = mesial, y = z x x. Template T(phi, v):
- phi = sudut polar di sekitar sumbu z;
- v in [0, v_wall]: dinding aksial. Penampang superelips dengan setengah lebar f(t) * W/2 dan f(t) * B/2,
  t = v / v_wall, f = 1 di height of contour (t = contour_t), jadi lebar maksimum tepat W dan B;
- v in [v_wall, 1]: meja oklusal dari tepi dinding ke titik tengah (v = 1), tinggi = z_wall + relief, dengan relief
  dari cusp gaussian per jenis gigi, dinormalisasi sehingga titik tertinggi tepat di z = height.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace

import numpy as np

KINDS = ("incisor", "canine", "premolar", "molar")


def fdi_kind(fdi: int) -> str:
    """Jenis gigi dari nomor FDI dua digit (kuadran 1 sampai 4, gigi 1 sampai 8)."""
    quadrant, tooth = divmod(int(fdi), 10)
    if quadrant not in (1, 2, 3, 4) or tooth not in range(1, 9):
        raise ValueError(f"nomor FDI tidak sah: {fdi}")
    if tooth <= 2:
        return "incisor"
    if tooth == 3:
        return "canine"
    if tooth <= 5:
        return "premolar"
    return "molar"


def fdi_is_upper(fdi: int) -> bool:
    return int(fdi) // 10 in (1, 2)


@dataclass(frozen=True)
class Shape:
    """Bentuk per jenis gigi (desain data uji, bukan anatomi)."""

    exponent: float  # eksponen superelips penampang
    cervical_f: float  # lebar di tepi servikal relatif terhadap lebar maksimum
    wall_top_f: float  # lebar di tepi atas dinding relatif terhadap lebar maksimum
    contour_t: float  # posisi height of contour di dinding (0 servikal, 1 tepi atas dinding)
    relief_mm: float  # kedalaman relief oklusal: tinggi cusp di atas tepi atas dinding
    cusps: tuple = ()  # (x, y, tinggi relatif) dalam koordinat ternormalisasi (-1..1)
    cusp_sigma: float = 0.35
    ridge: bool = False  # tepi insisal (insisif): punggung sepanjang x
    fossa: float = 0.0


SHAPES = {
    "incisor": Shape(exponent=2.2, cervical_f=0.80, wall_top_f=0.95, contour_t=0.30, relief_mm=0.8, ridge=True),
    "canine": Shape(exponent=2.2, cervical_f=0.82, wall_top_f=0.85, contour_t=0.35, relief_mm=1.8,
                    cusps=((0.0, 0.0, 1.0),), cusp_sigma=0.45),
    "premolar": Shape(exponent=2.4, cervical_f=0.85, wall_top_f=0.88, contour_t=0.40, relief_mm=1.6,
                      cusps=((0.0, 0.5, 1.0), (0.0, -0.5, 0.8)), fossa=0.3),
    "molar": Shape(exponent=2.6, cervical_f=0.88, wall_top_f=0.88, contour_t=0.40, relief_mm=1.8,
                   cusps=((0.45, 0.45, 1.0), (-0.45, 0.45, 0.95), (0.45, -0.45, 0.95), (-0.45, -0.45, 0.9)),
                   fossa=0.35),
}


@dataclass(frozen=True)
class TemplateParams:
    kind: str
    width_md: float  # lebar maksimum mesiodistal (sepanjang x), mm
    width_bl: float  # lebar maksimum bukolingual (sepanjang y), mm
    height: float  # z titik tertinggi permukaan oklusal, mm (frame template)
    base_z: float = 0.0  # z tepi servikal template
    v_wall: float = 0.6  # bagian parameter v untuk dinding
    shape: Shape = field(default=None)

    def __post_init__(self) -> None:
        if self.kind not in KINDS:
            raise ValueError(f"jenis gigi tidak dikenal: {self.kind!r}")
        if self.shape is None:
            object.__setattr__(self, "shape", SHAPES[self.kind])
        if min(self.width_md, self.width_bl) <= 0:
            raise ValueError("lebar template wajib > 0")
        if self.height - self.shape.relief_mm <= self.base_z:
            raise ValueError("tinggi template terlalu kecil untuk relief oklusalnya")

    @property
    def wall_top_z(self) -> float:
        return self.height - self.shape.relief_mm

    def with_(self, **changes) -> "TemplateParams":
        return replace(self, **changes)


def _superellipse_radius(phi: np.ndarray, a: float, b: float, n: float) -> np.ndarray:
    c, s = np.abs(np.cos(phi)), np.abs(np.sin(phi))
    return (np.power(c / a, n) + np.power(s / b, n)) ** (-1.0 / n)


def _width_factor(t: np.ndarray, shape: Shape) -> np.ndarray:
    """f(t): parabola ke 1 di height of contour, ke cervical_f di t = 0 dan wall_top_f di t = 1."""
    tc = shape.contour_t
    below = 1.0 - (1.0 - shape.cervical_f) * ((tc - t) / tc) ** 2
    above = 1.0 - (1.0 - shape.wall_top_f) * ((t - tc) / (1.0 - tc)) ** 2
    return np.where(t <= tc, below, above)


def _relief_raw(x: np.ndarray, y: np.ndarray, rim: np.ndarray, shape: Shape) -> np.ndarray:
    """Relief oklusal mentah di koordinat ternormalisasi; rim = 1 di tepi meja oklusal, 0 di tengah."""
    if shape.ridge:
        r = np.exp(-(y / 0.35) ** 2) * (1.0 - 0.15 * x ** 2)
    else:
        r = np.zeros_like(x)
        for cx, cy, h in shape.cusps:
            r = r + h * np.exp(-((x - cx) ** 2 + (y - cy) ** 2) / shape.cusp_sigma ** 2)
        r = r - shape.fossa * np.exp(-(x ** 2 + y ** 2) / 0.2 ** 2)
    # Tepi meja oklusal turun mulus ke tepi atas dinding (relief 0 di rim = 1).
    return r * np.clip(1.0 - rim ** 6, 0.0, 1.0)


_RELIEF_RANGE: dict = {}


def _relief_range(shape: Shape) -> tuple[float, float]:
    """(min, maks) relief mentah di seluruh meja oklusal, dihitung sekali per bentuk (grid rapat)."""
    key = id(shape)
    if key not in _RELIEF_RANGE:
        # Titik meja oklusal di koordinat ternormalisasi (x / a, y / b) mengisi superelips satuan yang diskalakan
        # wall_top_f, tidak bergantung pada rasio a / b; rim = norma superelips / wall_top_f.
        g = np.linspace(-1.0, 1.0, 801)
        x, y = np.meshgrid(g, g)
        norm = (np.abs(x) ** shape.exponent + np.abs(y) ** shape.exponent) ** (1.0 / shape.exponent)
        rim = norm / shape.wall_top_f
        inside = rim <= 1.0
        raw = _relief_raw(x[inside], y[inside], rim[inside], shape)
        _RELIEF_RANGE[key] = (float(raw.min()), float(raw.max()))
    return _RELIEF_RANGE[key]


def template_points(params: TemplateParams, phi: np.ndarray, v: np.ndarray) -> np.ndarray:
    """Titik template T(phi, v) di frame template (broadcast phi dan v)."""
    phi, v = np.broadcast_arrays(np.asarray(phi, float), np.asarray(v, float))
    s = params.shape
    a, b = 0.5 * params.width_md, 0.5 * params.width_bl
    r_max = _superellipse_radius(phi, a, b, s.exponent)
    out = np.empty(phi.shape + (3,))
    wall = v <= params.v_wall
    t = np.clip(v / params.v_wall, 0.0, 1.0)
    f = _width_factor(t, s)
    z_wall = params.base_z + t * (params.wall_top_z - params.base_z)
    # Meja oklusal: dari tepi atas dinding (rim = 1) ke titik tengah (rim = 0).
    rim = np.clip((1.0 - v) / (1.0 - params.v_wall), 0.0, 1.0)
    r_top = s.wall_top_f * r_max * rim
    x_n, y_n = r_top * np.cos(phi) / a, r_top * np.sin(phi) / b
    _, hi = _relief_range(s)
    relief = _relief_raw(x_n, y_n, rim, s) / hi  # 0 di tepi meja (sambung ke dinding), 1 di cusp tertinggi
    z_top = params.wall_top_z + s.relief_mm * relief
    radius = np.where(wall, f * r_max, r_top)
    z = np.where(wall, z_wall, z_top)
    out[..., 0] = radius * np.cos(phi)
    out[..., 1] = radius * np.sin(phi)
    out[..., 2] = z
    return out


def relief_floor_fraction(shape: Shape) -> float:
    """Relief ternormalisasi terendah di meja oklusal (fossa; bisa negatif, di bawah tepi atas dinding)."""
    lo, hi = _relief_range(shape)
    return float(min(lo, 0.0) / hi)
