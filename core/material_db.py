# SPDX-License-Identifier: GPL-3.0-or-later
"""Preset material restorasi (JSON). Setiap parameter membawa nilai, status, dan sumbernya.

Skema parameter sama dengan preset cetak model (core/model_presets.Param). Status
"default_pabrikan" di sini berarti angka dari tabel resmi pabrikan material untuk software CAD lain
(docs/PHASE2.md §2).
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from .model_presets import Param, PresetError, parse_param

# Parameter wajib dan satuannya. Nilai harus angka >= 0; yang ditandai True wajib > 0.
REQUIRED_PARAMS: dict[str, tuple[str, bool]] = {
    "min_thickness_anterior_mm": ("mm", True),
    "min_thickness_premolar_mm": ("mm", True),
    "min_thickness_molar_mm": ("mm", True),
    "connector_area_anterior_mm2": ("mm2", True),
    "connector_area_posterior_mm2": ("mm2", True),
    "cement_gap_um": ("um", True),
    "cement_gap_from_margin_mm": ("mm", False),
    "cement_gap_transition_mm": ("mm", False),
    "radial_spacing_um": ("um", False),
    "axial_spacing_um": ("um", False),
    "margin_horizontal_mm": ("mm", False),
    "margin_angled_length_mm": ("mm", False),
    "margin_angle_deg": ("deg", False),
    "milling_tool_diameter_mm": ("mm", True),
    "blockout_free_zone_mm": ("mm", False),
}


class MaterialPresetError(PresetError):
    """Preset material tidak memenuhi skema."""


@dataclass(frozen=True)
class MaterialPreset:
    id: str
    name: str
    manufacturer: str
    params: dict[str, Param]

    def get(self, name: str) -> Param:
        try:
            return self.params[name]
        except KeyError:
            raise MaterialPresetError(f"preset {self.id}: parameter '{name}' tidak ada") from None

    def value(self, name: str) -> float:
        return float(self.get(name).value)

    def min_thickness_mm(self, region: str) -> float:
        """Ketebalan minimum untuk 'anterior', 'premolar', atau 'molar'."""
        if region not in ("anterior", "premolar", "molar"):
            raise ValueError(f"region tidak dikenal: {region!r}")
        return self.value(f"min_thickness_{region}_mm")

    def warnings(self) -> list[str]:
        return [f"{p.name} = {p.value} {p.unit} belum dikalibrasi ({p.source})"
                for p in self.params.values() if p.status == "perlu_kalibrasi"]


def _text(data: dict, key: str, where: str) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value.strip():
        raise MaterialPresetError(f"{where}: '{key}' wajib string tidak kosong")
    return value


def parse_material_preset(data: dict, where: str = "preset") -> MaterialPreset:
    if not isinstance(data, dict):
        raise MaterialPresetError(f"{where}: isi preset wajib objek JSON")
    raw = data.get("params")
    if not isinstance(raw, dict):
        raise MaterialPresetError(f"{where}: 'params' wajib objek")

    params = {}
    for name, (unit, positive) in REQUIRED_PARAMS.items():
        if name not in raw:
            raise MaterialPresetError(f"{where}: parameter '{name}' wajib ada")
        try:
            param = parse_param(name, raw[name], where)
        except PresetError as exc:
            raise MaterialPresetError(str(exc)) from None
        if isinstance(param.value, str):
            raise MaterialPresetError(f"{where}.{name}: wajib angka, didapat {param.value!r}")
        if param.value < 0 or (positive and param.value == 0):
            raise MaterialPresetError(f"{where}.{name}: wajib {'> 0' if positive else '>= 0'}, didapat {param.value}")
        if param.unit != unit:
            raise MaterialPresetError(f"{where}.{name}: satuan wajib '{unit}', didapat '{param.unit}'")
        params[name] = param
    unknown = sorted(set(raw) - set(REQUIRED_PARAMS))
    if unknown:
        raise MaterialPresetError(f"{where}: parameter tidak dikenal: {', '.join(unknown)}")

    preset = MaterialPreset(
        id=_text(data, "id", where),
        name=_text(data, "name", where),
        manufacturer=_text(data, "manufacturer", where),
        params=params,
    )
    anterior = preset.min_thickness_mm("anterior")
    if anterior > min(preset.min_thickness_mm("premolar"), preset.min_thickness_mm("molar")):
        raise MaterialPresetError(f"{where}: ketebalan minimum anterior melebihi posterior")
    return preset


def load_material_preset(path: str | Path) -> MaterialPreset:
    path = Path(path)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise MaterialPresetError(f"{path.name}: JSON tidak valid ({exc})") from exc
    return parse_material_preset(data, where=path.name)


def load_material_presets(directory: str | Path) -> dict[str, MaterialPreset]:
    """Semua *.json di satu folder, dikunci dengan id preset."""
    presets: dict[str, MaterialPreset] = {}
    for path in sorted(Path(directory).glob("*.json")):
        preset = load_material_preset(path)
        if preset.id in presets:
            raise MaterialPresetError(f"{path.name}: id '{preset.id}' sudah dipakai preset lain")
        presets[preset.id] = preset
    return presets
