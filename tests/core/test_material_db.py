# SPDX-License-Identifier: GPL-3.0-or-later
import copy
import json
from pathlib import Path

import pytest

from core.material_db import (
    REQUIRED_PARAMS,
    MaterialPresetError,
    load_material_preset,
    load_material_presets,
    parse_material_preset,
)

MATERIALS = Path(__file__).resolve().parents[2] / "data" / "materials"


def _param(value, unit, status="default_pabrikan"):
    return {"value": value, "unit": unit, "status": status, "source": "uji", "source_date": "2026-10-23"}


VALID = {
    "id": "x",
    "name": "X",
    "manufacturer": "M",
    "params": {name: _param(1.0, unit) for name, (unit, _) in REQUIRED_PARAMS.items()},
}
VALID["params"]["min_thickness_anterior_mm"] = _param(0.8, "mm")


def test_bundled_zircad_prime_matches_ivoclar_chart():
    preset = load_material_preset(MATERIALS / "zircad_prime.json")
    expected = {
        "min_thickness_anterior_mm": 0.8,
        "min_thickness_premolar_mm": 1.0,
        "min_thickness_molar_mm": 1.0,
        "connector_area_anterior_mm2": 9,
        "connector_area_posterior_mm2": 9,
        "cement_gap_um": 60,
        "cement_gap_from_margin_mm": 1.0,
        "radial_spacing_um": 10,
        "axial_spacing_um": 0,
        "margin_horizontal_mm": 0.2,
        "margin_angled_length_mm": 0.1,
        "margin_angle_deg": 65,
        "milling_tool_diameter_mm": 1.2,
    }
    assert {name: p.value for name, p in preset.params.items()} == expected
    ivo = [name for name, p in preset.params.items() if p.source.startswith("IVO")]
    assert set(ivo) == set(expected) - {"axial_spacing_um"}
    assert all(preset.get(name).source_date == "2024-02-07" for name in ivo)
    assert preset.get("axial_spacing_um").status == "perlu_kalibrasi"
    assert preset.min_thickness_mm("premolar") == 1.0
    assert len(preset.warnings()) == 1


def test_all_bundled_presets_are_valid():
    assert "ivoclar_zircad_prime_full_contour" in load_material_presets(MATERIALS)


@pytest.mark.parametrize("name", sorted(REQUIRED_PARAMS))
def test_missing_parameter_is_rejected(name):
    data = copy.deepcopy(VALID)
    del data["params"][name]
    with pytest.raises(MaterialPresetError, match=name):
        parse_material_preset(data)


@pytest.mark.parametrize(
    "name, change",
    [
        ("cement_gap_um", {"value": "60"}),
        ("cement_gap_um", {"value": 0}),
        ("radial_spacing_um", {"value": -1}),
        ("cement_gap_um", {"unit": "mm"}),
        ("cement_gap_um", {"status": "kira-kira"}),
        ("cement_gap_um", {"source": ""}),
        ("cement_gap_um", {"source_date": "Feb 2024"}),
        ("cement_gap_um", {"value": None}),
    ],
)
def test_invalid_parameter_is_rejected(name, change):
    data = copy.deepcopy(VALID)
    data["params"][name].update(change)
    with pytest.raises(MaterialPresetError):
        parse_material_preset(data)


def test_zero_is_allowed_where_it_means_off():
    data = copy.deepcopy(VALID)
    data["params"]["axial_spacing_um"] = _param(0, "um", "perlu_kalibrasi")
    assert parse_material_preset(data).value("axial_spacing_um") == 0


def test_unknown_parameter_and_identity_fields_are_rejected():
    data = copy.deepcopy(VALID)
    data["params"]["warna"] = _param(1, "")
    with pytest.raises(MaterialPresetError, match="tidak dikenal"):
        parse_material_preset(data)
    data = copy.deepcopy(VALID)
    data["name"] = ""
    with pytest.raises(MaterialPresetError, match="name"):
        parse_material_preset(data)


def test_anterior_thicker_than_posterior_is_rejected():
    data = copy.deepcopy(VALID)
    data["params"]["min_thickness_anterior_mm"] = _param(1.2, "mm")
    with pytest.raises(MaterialPresetError, match="anterior"):
        parse_material_preset(data)


def test_unknown_region_is_rejected():
    with pytest.raises(ValueError):
        parse_material_preset(VALID).min_thickness_mm("kaninus")


def test_invalid_json_and_duplicate_ids(tmp_path):
    (tmp_path / "bad.json").write_text("{", encoding="utf-8")
    with pytest.raises(MaterialPresetError, match="JSON"):
        load_material_preset(tmp_path / "bad.json")

    (tmp_path / "bad.json").unlink()
    for name in ("a.json", "b.json"):
        (tmp_path / name).write_text(json.dumps(VALID), encoding="utf-8")
    with pytest.raises(MaterialPresetError, match="sudah dipakai"):
        load_material_presets(tmp_path)
