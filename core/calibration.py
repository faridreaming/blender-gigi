# SPDX-License-Identifier: GPL-3.0-or-later
"""Kupon kalibrasi printer + resin (docs/PHASE1.md §5.K).

Tiga kupon: dimensi per sumbu, clearance die-socket, dan hollow dengan lubang drainase di dasar.
Angka berawalan COUPON_ adalah bentuk benda uji ("desain kupon"), bukan parameter cetak model;
parameter cetak selalu diambil dari preset beserta status dan sumbernya.
"""

from __future__ import annotations

import csv
import hashlib
import json
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

import manifold3d as m3
import numpy as np

from . import mesh_io, solid
from .mesh_validate import is_watertight
from .model_presets import Preset

STL_HEADER = "DentalCAD research/education only. Not a certified medical device."
SUPPORT_NOTE = "beri support di slicer"

# Kupon 1: piramida bertingkat. Empat ukuran nominal per sumbu supaya skala dan offset terpisah.
COUPON_DIM_LEVELS_MM = (40.0, 30.0, 20.0, 10.0)
COUPON_DIM_LEVEL_HEIGHT_MM = 3.0
COUPON_NOTCH_MM = (1.0, 2.0)  # (kedalaman ke dalam sisi, lebar) takik penanda sumbu

# Kupon 2: die dan base socket.
COUPON_DIE_BODY_MM = (8.0, 5.0)  # (sisi persegi, tinggi badan di atas bahu)
COUPON_SOCKET_BOTTOM_GAP_MM = 1.0  # celah di bawah ujung peg supaya die duduk di bahu
COUPON_SOCKET_PITCH_MM = 14.0
COUPON_BASE_WIDTH_MM = 18.0
COUPON_BASE_FLOOR_MM = 2.0

# Kupon 3: kotak hollow.
COUPON_HOLLOW_BOX_MM = (30.0, 20.0, 12.0)
COUPON_HOLE_EDGE_MARGIN_MM = 1.0  # jarak tepi lubang ke dinding rongga
COUPON_HOLLOW_GAP_MM = 6.0  # jarak antar kotak saat dipratinjau
# Jumlah lubang pembanding: UNZ menyebut 1-2 lubang (docs/PHASE1.md §2); diameter memakai preset.
COUPON_ALT_HOLE_COUNTS = (2, 1)

# Penanda urutan: titik timbul (die, kotak) atau terukir (base).
COUPON_DOT_DIAMETER_MM = 1.0
COUPON_DOT_HEIGHT_MM = 0.6
COUPON_DOT_PITCH_MM = 1.8
COUPON_DOTS_PER_ROW = 3

_SEGMENTS = 48
_EPS = 0.1  # perpanjangan alat potong supaya tidak ada muka sebidang saat boolean


@dataclass
class Part:
    name: str
    solid: m3.Manifold
    print_note: str = ""


@dataclass
class Measurement:
    coupon: str
    item: str
    axis: str
    nominal_mm: float
    note: str


@dataclass
class CouponSet:
    preset: Preset
    parts: list[Part]
    measurements: list[Measurement]
    design: dict
    compensated: dict = field(default_factory=dict)


@dataclass(frozen=True)
class ScaleFit:
    axis: str
    factor: float  # kompensasi skala = 1 / slope
    slope: float
    offset_mm: float
    max_residual_mm: float
    n: int


def sweep(lower: float, upper: float, extra_steps: int = 1) -> list[float]:
    """Sapuan rentang kupon dengan langkah setengah rentang, plus langkah di luar rentang."""
    step = (upper - lower) / 2
    values = [lower + i * step for i in range(-extra_steps, 3 + extra_steps)]
    return [round(v, 6) for v in values if v > 0]


def _box(sx: float, sy: float, sz: float, x: float = 0.0, y: float = 0.0, z: float = 0.0) -> m3.Manifold:
    """Kotak berpusat di (x, y) dengan dasar di z."""
    return m3.Manifold.cube((sx, sy, sz), center=True).translate((x, y, z + sz / 2))


def _dots(count: int, x: float, y: float, z: float, height: float) -> m3.Manifold:
    """count titik dalam baris berisi paling banyak COUPON_DOTS_PER_ROW, berpusat di (x, y)."""
    dot = m3.Manifold.cylinder(height, COUPON_DOT_DIAMETER_MM / 2, -1.0, 24)
    rows = [min(COUPON_DOTS_PER_ROW, count - i) for i in range(0, count, COUPON_DOTS_PER_ROW)]
    placed = []
    for r, n in enumerate(rows):
        dy = ((len(rows) - 1) / 2 - r) * COUPON_DOT_PITCH_MM
        for dx in (np.arange(n) - (n - 1) / 2) * COUPON_DOT_PITCH_MM:
            placed.append(dot.translate((x + dx, y + dy, z)))
    return m3.Manifold.batch_boolean(placed, m3.OpType.Add)


def dimension_coupon() -> tuple[list[Part], list[Measurement]]:
    h = COUPON_DIM_LEVEL_HEIGHT_MM
    # Lapis di atas lapis pertama sedikit masuk ke lapis bawahnya; tinggi puncak tetap tepat i * h.
    levels = [
        _box(s, s, h + (_EPS if i else 0.0), z=i * h - (_EPS if i else 0.0))
        for i, s in enumerate(COUPON_DIM_LEVELS_MM)
    ]
    body = m3.Manifold.batch_boolean(levels, m3.OpType.Add)

    # Takik vertikal di lapis terbawah: satu di sisi +X, dua di sisi +Y, jauh dari tengah sisi
    # supaya rahang jangka sorong (yang mengukur di tengah) tidak jatuh di takik.
    half = COUPON_DIM_LEVELS_MM[0] / 2
    depth, width = COUPON_NOTCH_MM
    off = half * 0.6
    notches = [
        _box(2 * depth, width, h + 2 * _EPS, x=half, y=off, z=-_EPS),
        _box(width, 2 * depth, h + 2 * _EPS, x=-off, y=half, z=-_EPS),
        _box(width, 2 * depth, h + 2 * _EPS, x=-off + 2 * width, y=half, z=-_EPS),
    ]
    body = body - m3.Manifold.batch_boolean(notches, m3.OpType.Add)

    measurements = []
    for i, s in enumerate(COUPON_DIM_LEVELS_MM, start=1):
        note = f"lapis {i}: ukur di tengah tinggi lapis, di tengah sisi (jauh dari takik)"
        measurements.append(Measurement("dimensi", f"lapis {i}", "X", s, note))
        measurements.append(Measurement("dimensi", f"lapis {i}", "Y", s, note))
    for i in range(1, len(COUPON_DIM_LEVELS_MM) + 1):
        measurements.append(
            Measurement("dimensi", f"puncak lapis {i}", "Z", i * h, f"tinggi dari dasar ke atas lapis {i}")
        )
    return [Part("kupon_1_dimensi", body)], measurements


def _peg_side(preset: Preset) -> float:
    body, _ = COUPON_DIE_BODY_MM
    side = body - 2 * float(preset.value("peg_inset"))
    if side <= 0:
        raise ValueError(f"peg_inset {preset.value('peg_inset')} mm terlalu besar untuk badan die {body} mm")
    return side


def die_part(preset: Preset, index: int) -> m3.Manifold:
    """Die kupon: peg persegi di bawah, badan di atas bahu (z = tinggi peg), i titik di atas."""
    body, body_height = COUPON_DIE_BODY_MM
    peg_height = float(preset.value("peg_height"))
    peg = _box(_peg_side(preset), _peg_side(preset), peg_height + _EPS)  # masuk sedikit ke badan
    top = peg_height + body_height
    die = peg + _box(body, body, body_height, z=peg_height)
    return die + _dots(index, 0.0, 0.0, top - _EPS, COUPON_DOT_HEIGHT_MM + _EPS)


def socket_tool(preset: Preset, clearance: float, x: float, top: float) -> m3.Manifold:
    """Rongga socket: jejak peg yang di-offset sebesar clearance di 2D, sedalam peg + celah dasar.

    Join miter membuat celah tepat sama dengan clearance di setiap sisi dan √2 x clearance di sudut.
    Join bulat akan mendekati busur dengan segmen, sehingga celah di sudut sedikit di bawah clearance.
    """
    side = _peg_side(preset)
    depth = float(preset.value("peg_height")) + COUPON_SOCKET_BOTTOM_GAP_MM
    outline = m3.CrossSection.square((side, side), center=True).offset(clearance, m3.JoinType.Miter, 2.0)
    return outline.extrude(depth + _EPS).translate((x, 0.0, top - depth))


def clearance_coupon(preset: Preset) -> tuple[list[Part], list[Measurement], list[float]]:
    param = preset.get("die_clearance")
    if param.coupon_range is None:
        raise ValueError("die_clearance di preset wajib punya coupon_range untuk kupon clearance")
    clearances = sweep(*param.coupon_range, extra_steps=1)

    peg_height = float(preset.value("peg_height"))
    height = COUPON_BASE_FLOOR_MM + peg_height + COUPON_SOCKET_BOTTOM_GAP_MM
    length = COUPON_SOCKET_PITCH_MM * len(clearances)
    xs = (np.arange(len(clearances)) - (len(clearances) - 1) / 2) * COUPON_SOCKET_PITCH_MM

    base = _box(length, COUPON_BASE_WIDTH_MM, height)
    cutters = [socket_tool(preset, c, x, height) for c, x in zip(clearances, xs)]
    dot_y = -(COUPON_BASE_WIDTH_MM / 2 - 2.0)
    marks = [
        _dots(i, x, dot_y, height - COUPON_DOT_HEIGHT_MM, COUPON_DOT_HEIGHT_MM + _EPS)
        for i, x in enumerate(xs, start=1)
    ]
    base = base - m3.Manifold.batch_boolean(cutters + marks, m3.OpType.Add)

    parts = [Part("kupon_2_clearance_base", base, "cetak rata di build plate, socket menghadap ke atas")]
    measurements = []
    for i, c in enumerate(clearances, start=1):
        parts.append(Part(f"kupon_2_die_{i}_{SUPPORT_NOTE.replace(' ', '_')}", die_part(preset, i), SUPPORT_NOTE))
        measurements.append(
            Measurement(
                "clearance", f"socket {i} ({i} titik)", "fit", c,
                "hasil: pas tanpa adjust / longgar / tidak masuk; pakai die mana saja, semua die identik",
            )
        )
    return parts, measurements, clearances


def drain_hole_positions(count: int, cavity_x: float, cavity_y: float, diameter: float) -> list[tuple[float, float]]:
    inset = diameter / 2 + COUPON_HOLE_EDGE_MARGIN_MM
    hx, hy = cavity_x / 2 - inset, cavity_y / 2 - inset
    if hx < 0 or hy < 0:
        raise ValueError(f"lubang Ø {diameter} mm tidak muat di rongga {cavity_x} x {cavity_y} mm")
    corners = [(-hx, -hy), (hx, hy), (hx, -hy), (-hx, hy)]
    if count == 1:
        return [(0.0, 0.0)]
    if 2 <= count <= 4:
        return corners[:count]
    raise ValueError(f"kupon hollow mendukung 1 sampai 4 lubang, didapat {count}")


def hollow_box(wall: float, holes: int, diameter: float, index: int) -> m3.Manifold:
    sx, sy, sz = COUPON_HOLLOW_BOX_MM
    cx, cy, cz = sx - 2 * wall, sy - 2 * wall, sz - 2 * wall
    if min(cx, cy, cz) <= 0:
        raise ValueError(f"dinding {wall} mm terlalu tebal untuk kotak {COUPON_HOLLOW_BOX_MM}")
    box = _box(sx, sy, sz) - _box(cx, cy, cz, z=wall)
    hole = m3.Manifold.cylinder(wall + 2 * _EPS, diameter / 2, -1.0, _SEGMENTS)
    drills = [hole.translate((x, y, -_EPS)) for x, y in drain_hole_positions(holes, cx, cy, diameter)]
    box = box - m3.Manifold.batch_boolean(drills, m3.OpType.Add)
    return box + _dots(index, 0.0, 0.0, sz - _EPS, COUPON_DOT_HEIGHT_MM + _EPS)


def hollow_coupon(preset: Preset) -> tuple[list[Part], list[Measurement], list[tuple[float, int]]]:
    wall_param = preset.get("hollow_wall_thickness")
    walls = sweep(*wall_param.coupon_range, extra_steps=0) if wall_param.coupon_range else [float(wall_param.value)]
    holes = int(preset.value("drain_hole_count"))
    diameter = float(preset.value("drain_hole_diameter"))
    if preset.value("drain_hole_location") != "bottom":
        raise ValueError("kupon hollow hanya mendukung lubang drainase di dasar (K2)")

    configs = [(w, holes) for w in walls]
    configs += [(float(wall_param.value), n) for n in COUPON_ALT_HOLE_COUNTS if n != holes]
    parts, measurements = [], []
    for i, (wall, n) in enumerate(configs, start=1):
        name = f"kupon_3_hollow_{i}_dinding_{wall:g}mm_{n}_lubang"
        parts.append(Part(name, hollow_box(wall, n, diameter, i), "cetak rata, lubang drainase menempel ke build plate"))
        measurements.append(
            Measurement(
                "hollow", f"kotak {i} ({i} titik): dinding {wall:g} mm, {n} x Ø {diameter:g} mm", "hasil", wall,
                "hasil: utuh / cupping / blowout / resin terjebak / dinding berubah bentuk",
            )
        )
    return parts, measurements, configs


def build_coupon_set(preset: Preset) -> CouponSet:
    dim_parts, dim_meas = dimension_coupon()
    clr_parts, clr_meas, clearances = clearance_coupon(preset)
    hol_parts, hol_meas, configs = hollow_coupon(preset)

    # Kupon dimensi selalu tanpa kompensasi (itu yang diukur); kupon lain memakai skala preset.
    scale = tuple(float(preset.value(f"scale_{a}")) for a in "xyz")
    compensated = {}
    for part in clr_parts + hol_parts:
        if scale != (1.0, 1.0, 1.0):
            part.solid = part.solid.scale(scale)
        compensated[part.name] = list(scale)
    compensated[dim_parts[0].name] = [1.0, 1.0, 1.0]

    parts = dim_parts + clr_parts + hol_parts
    for part in parts:
        solid.check_solid(part.solid, part.name)

    design = {
        name: value
        for name, value in globals().items()
        if name.startswith("COUPON_") and isinstance(value, (int, float, tuple))
    }
    design["clearance_sweep_mm"] = clearances
    design["hollow_configs"] = [{"wall_mm": w, "holes": n} for w, n in configs]
    return CouponSet(preset, parts, dim_meas + clr_meas + hol_meas, design, compensated)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_coupon_set(coupons: CouponSet, out_dir: str | Path, version: str = "") -> dict:
    """Tulis STL per bagian, lembar ukur CSV, dan laporan JSON. Mengembalikan isi laporan."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    parts = []
    for part in coupons.parts:
        mesh = solid.to_mesh_data(part.solid)
        if not is_watertight(mesh) or solid.has_sealed_void(part.solid):
            raise solid.SolidError(f"{part.name}: tidak siap cetak (tidak watertight atau ada rongga tertutup)")
        path = out_dir / f"{part.name}.stl"
        mesh_io.save_stl(mesh, path, header=STL_HEADER)
        parts.append({
            "file": path.name,
            "sha256": _sha256(path),
            "triangles": int(len(mesh.faces)),
            "volume_mm3": round(part.solid.volume(), 3),
            "scale_applied": coupons.compensated.get(part.name, [1.0, 1.0, 1.0]),
            "print_note": part.print_note,
        })

    sheet = out_dir / "kupon_lembar_ukur.csv"
    with sheet.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["kupon", "item", "sumbu", "nominal_mm", "hasil", "catatan"])
        for m in coupons.measurements:
            writer.writerow([m.coupon, m.item, m.axis, f"{m.nominal_mm:g}", "", m.note])

    preset = coupons.preset
    report = {
        "dentalcad_version": version,
        "generated": date.today().isoformat(),
        "preset": {"id": preset.id, "printer": preset.printer, "resin": preset.resin},
        "params": {
            name: {**p.to_dict(), "status_label": p.status_label} for name, p in sorted(preset.params.items())
        },
        "warnings": preset.warnings(),
        "notes": preset.notes() + [
            "kupon_1_dimensi tidak dikompensasi skala; kupon lain memakai faktor skala preset",
            f"setiap die kupon: {SUPPORT_NOTE} di bawah dasarnya (UNZ, K6)",
        ],
        "design": {k: list(v) if isinstance(v, tuple) else v for k, v in coupons.design.items()},
        "parts": parts,
        "measurement_sheet": sheet.name,
        "stl_header": STL_HEADER,
    }
    (out_dir / "kupon_laporan.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return report


def read_measurement_sheet(path: str | Path) -> list[dict]:
    with Path(path).open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def fit_scale(rows: list[dict]) -> dict[str, ScaleFit]:
    """Cocokkan terukur = slope * nominal + offset per sumbu dari baris kupon dimensi yang terisi."""
    fits = {}
    for axis in "XYZ":
        pairs = []
        for row in rows:
            if row.get("kupon") != "dimensi" or row.get("sumbu") != axis:
                continue
            measured = (row.get("hasil") or "").strip().replace(",", ".")
            if measured:
                pairs.append((float(row["nominal_mm"]), float(measured)))
        if not pairs:
            continue
        nominal = np.array([p[0] for p in pairs])
        measured = np.array([p[1] for p in pairs])
        if len(np.unique(nominal)) >= 2:
            slope, offset = np.polyfit(nominal, measured, 1)
        else:
            slope, offset = float(np.mean(measured / nominal)), 0.0
        residual = measured - (slope * nominal + offset)
        fits[axis] = ScaleFit(
            axis=axis,
            factor=float(1.0 / slope),
            slope=float(slope),
            offset_mm=float(offset),
            max_residual_mm=float(np.max(np.abs(residual))),
            n=len(pairs),
        )
    return fits
