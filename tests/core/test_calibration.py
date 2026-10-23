# SPDX-License-Identifier: GPL-3.0-or-later
import csv
import importlib.util
import json
import math
import shutil
import sys
from pathlib import Path

import manifold3d as m3
import pytest

from core import calibration as cal
from core import mesh_io, solid
from core.mesh_validate import is_watertight
from core.model_presets import load_preset

ROOT = Path(__file__).resolve().parents[2]
PRESET_PATH = ROOT / "data" / "model_presets" / "photon_p1_std_v2_hd_gray.json"


@pytest.fixture(scope="module")
def preset():
    return load_preset(PRESET_PATH)


@pytest.fixture(scope="module")
def coupons(preset):
    return cal.build_coupon_set(preset)


def test_sweep_covers_range_plus_one_step_outside():
    assert cal.sweep(0.05, 0.1, extra_steps=1) == [0.025, 0.05, 0.075, 0.1, 0.125]
    assert cal.sweep(2.0, 3.0, extra_steps=0) == [2.0, 2.5, 3.0]


def test_dimension_coupon_levels(preset):
    parts, measurements = cal.dimension_coupon()
    body = parts[0].solid
    notch = cal.COUPON_NOTCH_MM[0] * cal.COUPON_NOTCH_MM[1]
    h = cal.COUPON_DIM_LEVEL_HEIGHT_MM
    sizes = cal.COUPON_DIM_LEVELS_MM
    assert body.volume() == pytest.approx(sum(s * s * h for s in sizes) - 3 * notch * h, rel=1e-9)
    assert body.bounding_box() == pytest.approx((-20, -20, 0, 20, 20, 12))
    # Luas penampang di tengah setiap lapis sama dengan persegi nominalnya (lapis 1 dikurangi 3 takik).
    for i, s in enumerate(sizes):
        expected = s * s - (3 * notch if i == 0 else 0)
        assert body.slice((i + 0.5) * h).area() == pytest.approx(expected, rel=1e-9)
    by_axis = {a: sorted(m.nominal_mm for m in measurements if m.axis == a) for a in "XYZ"}
    assert by_axis["X"] == by_axis["Y"] == sorted(sizes)
    assert by_axis["Z"] == [3.0, 6.0, 9.0, 12.0]


def test_clearance_coupon_gap_equals_each_clearance(preset):
    parts, measurements, clearances = cal.clearance_coupon(preset)
    base = parts[0].solid
    side = 8.0 - 2 * preset.value("peg_inset")
    peg_height = preset.value("peg_height")
    top = cal.COUPON_BASE_FLOOR_MM + peg_height + cal.COUPON_SOCKET_BOTTOM_GAP_MM
    xs = [(i - (len(clearances) - 1) / 2) * cal.COUPON_SOCKET_PITCH_MM for i in range(len(clearances))]
    for c, x in zip(clearances, xs):
        # Peg duduk dengan bahu die tepat di permukaan base: celah samping = c, celah dasar = 1 mm.
        peg = m3.Manifold.cube((side, side, peg_height), center=True).translate((x, 0, top - peg_height / 2))
        assert peg.min_gap(base, 1.0) == pytest.approx(c, abs=1e-4)
    assert len(parts) == 1 + len(clearances)
    assert [m.nominal_mm for m in measurements] == clearances


def test_dies_have_support_note_and_identical_peg(preset):
    parts, _, _ = cal.clearance_coupon(preset)
    dies = parts[1:]
    assert all(cal.SUPPORT_NOTE == d.print_note for d in dies)
    assert all("support" in d.name for d in dies)
    side = 8.0 - 2 * preset.value("peg_inset")
    for d in dies:
        section = d.solid.slice(preset.value("peg_height") / 2)
        assert section.area() == pytest.approx(side * side, rel=1e-9)
        assert d.solid.bounding_box()[3] <= 4.0 + 1e-9  # titik penanda tidak melewati badan die


@pytest.mark.parametrize("index", range(5))
def test_hollow_boxes(preset, coupons, index):
    _, _, configs = cal.hollow_coupon(preset)
    wall, holes = configs[index]
    box = cal.hollow_box(wall, holes, preset.value("drain_hole_diameter"), index + 1)
    sx, sy, sz = cal.COUPON_HOLLOW_BOX_MM
    r = preset.value("drain_hole_diameter") / 2
    cavity = (sx - 2 * wall) * (sy - 2 * wall) * (sz - 2 * wall)
    expected = sx * sy * sz - cavity - holes * math.pi * r * r * wall
    assert box.volume() == pytest.approx(expected, rel=5e-3)  # selisih dari titik penanda dan segmen lingkaran
    assert not solid.has_sealed_void(box)
    floor = box.slice(wall / 2)  # semua lubang ada di lantai (dasar model)
    assert floor.num_contour() == 1 + holes
    assert box.slice(sz - wall / 2).num_contour() == 1  # dinding atas tanpa lubang


def test_hollow_configs_compare_med_and_unz(preset):
    _, _, configs = cal.hollow_coupon(preset)
    assert configs == [(2.0, 4), (2.5, 4), (3.0, 4), (3.0, 2), (3.0, 1)]


def test_hollow_without_drain_holes_would_trap_resin():
    sx, sy, sz = cal.COUPON_HOLLOW_BOX_MM
    sealed = cal._box(sx, sy, sz) - cal._box(sx - 6, sy - 6, sz - 6, z=3)
    assert solid.has_sealed_void(sealed)


def test_scale_applies_to_all_but_dimension_coupon(preset):
    scaled = preset
    for axis, factor in zip("xyz", (1.01, 1.02, 0.99)):
        scaled = scaled.with_value(f"scale_{axis}", factor, "dikalibrasi", "kupon uji", "2026-11-02")
    coupons = cal.build_coupon_set(scaled)
    by_name = {p.name: p for p in coupons.parts}
    assert by_name["kupon_1_dimensi"].solid.bounding_box() == pytest.approx((-20, -20, 0, 20, 20, 12))
    hollow = by_name["kupon_3_hollow_1_dinding_2mm_4_lubang"].solid.bounding_box()
    assert hollow[3] - hollow[0] == pytest.approx(30 * 1.01)
    assert hollow[4] - hollow[1] == pytest.approx(20 * 1.02)
    assert coupons.compensated["kupon_1_dimensi"] == [1.0, 1.0, 1.0]


def test_write_coupon_set(coupons, tmp_path):
    report = cal.write_coupon_set(coupons, tmp_path, version="0.1.0")
    assert len(report["parts"]) == len(coupons.parts) == 12
    for entry in report["parts"]:
        path = tmp_path / entry["file"]
        assert path.read_bytes()[:80].decode("ascii").startswith(cal.STL_HEADER)
        mesh = mesh_io.load_mesh(path)
        assert is_watertight(mesh)
        assert len(mesh.faces) == entry["triangles"]
        assert cal._sha256(path) == entry["sha256"]
    with (tmp_path / "kupon_lembar_ukur.csv").open(encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    assert len(rows) == len(coupons.measurements) == 22
    assert all(row["hasil"] == "" for row in rows)
    saved = json.loads((tmp_path / "kupon_laporan.json").read_text(encoding="utf-8"))
    assert saved["preset"]["id"] == "photon_p1_std_v2_hd_gray"
    assert any("die_clearance" in w for w in saved["warnings"])
    assert saved["design"]["clearance_sweep_mm"] == [0.025, 0.05, 0.075, 0.1, 0.125]


def _rows(slope: float, offset: float, axes: str = "XYZ") -> list[dict]:
    rows = []
    for axis in axes:
        for nominal in (10.0, 20.0, 30.0, 40.0) if axis != "Z" else (3.0, 6.0, 9.0, 12.0):
            rows.append({"kupon": "dimensi", "sumbu": axis, "nominal_mm": str(nominal),
                         "hasil": f"{slope * nominal + offset:.4f}".replace(".", ",")})
    rows.append({"kupon": "clearance", "sumbu": "fit", "nominal_mm": "0.05", "hasil": "pas"})
    return rows


def test_fit_scale_separates_scale_from_offset():
    fits = cal.fit_scale(_rows(0.99, 0.08))
    for axis in "XYZ":
        assert fits[axis].slope == pytest.approx(0.99, abs=1e-4)
        assert fits[axis].offset_mm == pytest.approx(0.08, abs=1e-3)
        assert fits[axis].factor == pytest.approx(1 / 0.99, abs=1e-4)
        assert fits[axis].n == 4


def test_fit_scale_skips_empty_rows_and_single_nominal():
    rows = [{"kupon": "dimensi", "sumbu": "X", "nominal_mm": "40", "hasil": "39.6"},
            {"kupon": "dimensi", "sumbu": "Y", "nominal_mm": "40", "hasil": ""}]
    fits = cal.fit_scale(rows)
    assert set(fits) == {"X"}
    assert fits["X"].factor == pytest.approx(40 / 39.6)


def test_apply_calibration_script_writes_preset(tmp_path):
    preset_copy = tmp_path / "preset.json"
    shutil.copy(PRESET_PATH, preset_copy)
    sheet = tmp_path / "sheet.csv"
    with sheet.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["kupon", "item", "sumbu", "nominal_mm", "hasil", "catatan"])
        writer.writeheader()
        for row in _rows(0.98, 0.0):
            writer.writerow({**row, "item": "", "catatan": ""})

    spec = importlib.util.spec_from_file_location("apply_calibration", ROOT / "scripts" / "apply_calibration.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    assert module.main([str(preset_copy), str(sheet), "--date", "2026-11-02", "--clearance", "0.075", "--write"]) == 0

    updated = load_preset(preset_copy)
    assert updated.value("scale_x") == pytest.approx(1 / 0.98, abs=1e-5)
    assert updated.get("scale_z").status == "dikalibrasi"
    assert updated.get("die_clearance").status == "dikalibrasi"
    assert updated.warnings() == []
