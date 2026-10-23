# SPDX-License-Identifier: GPL-3.0-or-later
import json
from pathlib import Path

import pytest

from core.material_db import (
    MaterialPresetError,
    load_material_preset,
    load_material_presets,
    parse_material_preset,
)

MATERIALS = Path(__file__).resolve().parents[2] / "data" / "materials"

VALID = {
    "id": "x",
    "name": "X",
    "manufacturer": "M",
    "min_thickness_anterior_mm": 0.8,
    "min_thickness_posterior_mm": 1.0,
    "connector_area_mm2": {"anterior": 9, "posterior": 12},
    "cement_gap_um": 50,
    "source": "IFU",
    "source_date": "2023-05",
}


def test_bundled_zircad_prime_preset():
    preset = load_material_preset(MATERIALS / "zircad_prime.json")
    assert preset.min_thickness_anterior_mm == 0.8
    assert preset.min_thickness_posterior_mm == 1.0
    assert preset.connector_area_mm2.anterior_mm2 == 9.0
    assert preset.connector_area_mm2.posterior_mm2 == 9.0


def test_all_bundled_presets_are_valid():
    presets = load_material_presets(MATERIALS)
    assert "ivoclar_zircad_prime_full_contour" in presets


@pytest.mark.parametrize("field", sorted(VALID))
def test_missing_field_is_rejected(field):
    data = {k: v for k, v in VALID.items() if k != field}
    with pytest.raises(MaterialPresetError, match=field):
        parse_material_preset(data)


@pytest.mark.parametrize(
    "field, value",
    [
        ("min_thickness_anterior_mm", "0.8"),
        ("min_thickness_posterior_mm", 0),
        ("cement_gap_um", -5),
        ("cement_gap_um", True),
        ("source_date", "Mei 2023"),
        ("connector_area_mm2", 9),
    ],
)
def test_invalid_value_is_rejected(field, value):
    with pytest.raises(MaterialPresetError):
        parse_material_preset(dict(VALID, **{field: value}))


def test_anterior_thicker_than_posterior_is_rejected():
    with pytest.raises(MaterialPresetError, match="anterior"):
        parse_material_preset(dict(VALID, min_thickness_anterior_mm=1.2))


def test_invalid_json_and_duplicate_ids(tmp_path):
    (tmp_path / "bad.json").write_text("{", encoding="utf-8")
    with pytest.raises(MaterialPresetError, match="JSON"):
        load_material_preset(tmp_path / "bad.json")

    (tmp_path / "bad.json").unlink()
    for name in ("a.json", "b.json"):
        (tmp_path / name).write_text(json.dumps(VALID), encoding="utf-8")
    with pytest.raises(MaterialPresetError, match="sudah dipakai"):
        load_material_presets(tmp_path)
