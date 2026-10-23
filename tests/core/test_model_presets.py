# SPDX-License-Identifier: GPL-3.0-or-later
import copy
import json
from pathlib import Path

import pytest

from core.model_presets import PresetError, load_preset, load_presets, parse_preset, save_preset

PRESETS = Path(__file__).resolve().parents[2] / "data" / "model_presets"

VALID = {
    "id": "p",
    "printer": "Printer",
    "resin": "Resin",
    "params": {
        "wall": {"value": 3.0, "unit": "mm", "status": "default_pabrikan", "source": "MED", "source_date": "2026-10-23"},
        "gap": {"value": 0.075, "unit": "mm", "status": "perlu_kalibrasi", "source": "RESEARCH",
                "source_date": "2026", "coupon_range": [0.05, 0.1]},
        "where": {"value": "bottom", "unit": "", "status": "default_pabrikan", "source": "UNZ", "source_date": "2026-10"},
    },
}


def test_bundled_presets_are_valid_and_match_phase1():
    presets = load_presets(PRESETS)
    assert set(presets) == {"photon_p1_std_v2_hd_gray", "accufab_f1_std_v2_hd_gray"}
    for preset in presets.values():
        assert preset.value("hollow_wall_thickness") == 3.0
        assert preset.value("drain_hole_count") == 4
        assert preset.value("drain_hole_diameter") == 4.0
        assert preset.value("drain_hole_location") == "bottom"
        assert preset.value("die_clearance") == 0.075
        assert preset.get("die_clearance").coupon_range == (0.05, 0.1)
        assert preset.value("peg_height") == 2.5
        assert {preset.value(f"scale_{a}") for a in "xyz"} == {1.0}


def test_warnings_and_notes_follow_status():
    preset = parse_preset(VALID)
    assert len(preset.warnings()) == 1 and "gap = 0.075 mm" in preset.warnings()[0]
    assert len(preset.notes()) == 2
    assert preset.get("gap").status_label == "perlu kalibrasi"


def test_missing_parameter_points_to_lab_practice_table():
    with pytest.raises(PresetError, match="§9.1"):
        parse_preset(VALID).value("kerf")


def test_with_value_marks_calibrated_and_clears_warning():
    preset = parse_preset(VALID).with_value("gap", 0.1, "dikalibrasi", "kupon 2026-11-02", "2026-11-02")
    assert preset.value("gap") == 0.1
    assert preset.get("gap").unit == "mm"
    assert preset.warnings() == []


@pytest.mark.parametrize(
    "mutate",
    [
        lambda d: d["params"]["wall"].update(value=None),
        lambda d: d["params"]["wall"].pop("value"),
        lambda d: d["params"]["wall"].update(status="kira-kira"),
        lambda d: d["params"]["wall"].update(source=""),
        lambda d: d["params"]["wall"].update(source_date="Okt 2026"),
        lambda d: d["params"]["wall"].update(value=True),
        lambda d: d["params"]["gap"].update(coupon_range=[0.1, 0.05]),
        lambda d: d["params"]["gap"].update(value=0.2),
        lambda d: d.update(params={}),
        lambda d: d.pop("printer"),
    ],
)
def test_invalid_presets_are_rejected(mutate):
    data = copy.deepcopy(VALID)
    mutate(data)
    with pytest.raises(PresetError):
        parse_preset(data)


def test_save_and_reload(tmp_path):
    preset = parse_preset(VALID)
    save_preset(preset, tmp_path / "p.json")
    assert load_preset(tmp_path / "p.json") == preset
    assert "null" not in (tmp_path / "p.json").read_text(encoding="utf-8")


def test_duplicate_ids_are_rejected(tmp_path):
    for name in ("a.json", "b.json"):
        (tmp_path / name).write_text(json.dumps(VALID), encoding="utf-8")
    with pytest.raises(PresetError, match="sudah dipakai"):
        load_presets(tmp_path)
