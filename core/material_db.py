# SPDX-License-Identifier: GPL-3.0-or-later
"""Loader dan validasi skema preset material (JSON, angka dari IFU pabrikan)."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

# Tanggal sumber boleh sepresisi yang tercantum di IFU: tahun, tahun-bulan, atau tanggal penuh.
_SOURCE_DATE = re.compile(r"^\d{4}(-\d{2}(-\d{2})?)?$")


class MaterialPresetError(ValueError):
    """Preset material tidak memenuhi skema."""


@dataclass(frozen=True)
class ConnectorArea:
    anterior_mm2: float
    posterior_mm2: float


@dataclass(frozen=True)
class MaterialPreset:
    id: str
    name: str
    manufacturer: str
    min_thickness_anterior_mm: float
    min_thickness_posterior_mm: float
    connector_area_mm2: ConnectorArea
    cement_gap_um: float
    source: str
    source_date: str


def _positive_number(data: dict, key: str, where: str) -> float:
    value = data.get(key)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise MaterialPresetError(f"{where}: '{key}' wajib angka, didapat {value!r}")
    if value <= 0:
        raise MaterialPresetError(f"{where}: '{key}' wajib lebih dari 0, didapat {value}")
    return float(value)


def _non_empty_str(data: dict, key: str, where: str) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value.strip():
        raise MaterialPresetError(f"{where}: '{key}' wajib string tidak kosong")
    return value


def parse_material_preset(data: dict, where: str = "preset") -> MaterialPreset:
    if not isinstance(data, dict):
        raise MaterialPresetError(f"{where}: isi preset wajib objek JSON")

    connector = data.get("connector_area_mm2")
    if not isinstance(connector, dict):
        raise MaterialPresetError(f"{where}: 'connector_area_mm2' wajib objek {{anterior, posterior}}")

    source_date = _non_empty_str(data, "source_date", where)
    if not _SOURCE_DATE.match(source_date):
        raise MaterialPresetError(f"{where}: 'source_date' wajib YYYY, YYYY-MM, atau YYYY-MM-DD")

    preset = MaterialPreset(
        id=_non_empty_str(data, "id", where),
        name=_non_empty_str(data, "name", where),
        manufacturer=_non_empty_str(data, "manufacturer", where),
        min_thickness_anterior_mm=_positive_number(data, "min_thickness_anterior_mm", where),
        min_thickness_posterior_mm=_positive_number(data, "min_thickness_posterior_mm", where),
        connector_area_mm2=ConnectorArea(
            anterior_mm2=_positive_number(connector, "anterior", f"{where}.connector_area_mm2"),
            posterior_mm2=_positive_number(connector, "posterior", f"{where}.connector_area_mm2"),
        ),
        cement_gap_um=_positive_number(data, "cement_gap_um", where),
        source=_non_empty_str(data, "source", where),
        source_date=source_date,
    )
    if preset.min_thickness_anterior_mm > preset.min_thickness_posterior_mm:
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
