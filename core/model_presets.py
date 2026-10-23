# SPDX-License-Identifier: GPL-3.0-or-later
"""Preset cetak model per pasangan printer + resin (docs/PHASE1.md §1).

Setiap parameter membawa nilai, satuan, status, dan sumbernya. Tidak ada nilai null: parameter
yang belum punya nilai sama sekali tidak ada di preset, dan memintanya menghasilkan error yang
menunjuk ke tabel praktik lab di PHASE1.md §9.1.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, replace
from pathlib import Path

# Kunci status di JSON -> label di dokumen dan UI.
STATUSES = {
    "default_pabrikan": "default pabrikan (printer lain), perlu kalibrasi",
    "perlu_kalibrasi": "perlu kalibrasi",
    "praktik_lab": "praktik lab",
    "dikalibrasi": "dikalibrasi",
}
_SOURCE_DATE = re.compile(r"^\d{4}(-\d{2}(-\d{2})?)?$")


class PresetError(ValueError):
    """Preset tidak memenuhi skema, atau parameter yang diminta belum punya nilai."""


@dataclass(frozen=True)
class Param:
    name: str
    value: float | int | str
    unit: str
    status: str
    source: str
    source_date: str
    coupon_range: tuple[float, float] | None = None

    @property
    def status_label(self) -> str:
        return STATUSES[self.status]

    def to_dict(self) -> dict:
        data = {
            "value": self.value,
            "unit": self.unit,
            "status": self.status,
            "source": self.source,
            "source_date": self.source_date,
        }
        if self.coupon_range is not None:
            data["coupon_range"] = list(self.coupon_range)
        return data


@dataclass(frozen=True)
class Preset:
    id: str
    printer: str
    resin: str
    params: dict[str, Param]

    def get(self, name: str) -> Param:
        try:
            return self.params[name]
        except KeyError:
            raise PresetError(
                f"preset {self.id}: parameter '{name}' belum punya nilai; "
                "isi tabel praktik lab di docs/PHASE1.md §9.1"
            ) from None

    def value(self, name: str):
        return self.get(name).value

    def warnings(self) -> list[str]:
        """Parameter berstatus 'perlu kalibrasi': ditampilkan sebagai peringatan jelas."""
        return [
            f"{p.name} = {_fmt(p)} belum dikalibrasi ({p.source})"
            for p in self.params.values()
            if p.status == "perlu_kalibrasi"
        ]

    def notes(self) -> list[str]:
        """Parameter berstatus 'default pabrikan': dicatat di laporan, bukan peringatan."""
        return [
            f"{p.name} = {_fmt(p)} adalah default pabrikan untuk printer lain ({p.source})"
            for p in self.params.values()
            if p.status == "default_pabrikan"
        ]

    def with_value(self, name: str, value, status: str, source: str, source_date: str) -> "Preset":
        """Salinan preset dengan satu parameter diganti (misalnya hasil kalibrasi kupon)."""
        old = self.params.get(name)
        unit = old.unit if old is not None else ""
        param = _parse_param(
            name,
            {"value": value, "unit": unit, "status": status, "source": source, "source_date": source_date},
            where=self.id,
        )
        return replace(self, params={**self.params, name: param})

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "printer": self.printer,
            "resin": self.resin,
            "params": {name: p.to_dict() for name, p in sorted(self.params.items())},
        }


def _fmt(param: Param) -> str:
    return f"{param.value} {param.unit}" if param.unit else f"{param.value}"


def _text(data: dict, key: str, where: str) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value.strip():
        raise PresetError(f"{where}: '{key}' wajib string tidak kosong")
    return value


def _parse_param(name: str, data: dict, where: str) -> Param:
    where = f"{where}.{name}"
    if not isinstance(data, dict):
        raise PresetError(f"{where}: wajib objek JSON")
    if "value" not in data or data["value"] is None:
        raise PresetError(f"{where}: 'value' wajib ada dan tidak boleh null")
    value = data["value"]
    if isinstance(value, bool) or not isinstance(value, (int, float, str)):
        raise PresetError(f"{where}: 'value' wajib angka atau string, didapat {value!r}")

    status = _text(data, "status", where)
    if status not in STATUSES:
        raise PresetError(f"{where}: status '{status}' tidak dikenal ({', '.join(STATUSES)})")
    source_date = _text(data, "source_date", where)
    if not _SOURCE_DATE.match(source_date):
        raise PresetError(f"{where}: 'source_date' wajib YYYY, YYYY-MM, atau YYYY-MM-DD")
    unit = data.get("unit", "")
    if not isinstance(unit, str):
        raise PresetError(f"{where}: 'unit' wajib string")

    coupon_range = data.get("coupon_range")
    if coupon_range is not None:
        if (
            not isinstance(coupon_range, list)
            or len(coupon_range) != 2
            or not all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in coupon_range)
            or coupon_range[0] >= coupon_range[1]
        ):
            raise PresetError(f"{where}: 'coupon_range' wajib [bawah, atas] dengan bawah < atas")
        if isinstance(value, str) or not coupon_range[0] <= value <= coupon_range[1]:
            raise PresetError(f"{where}: nilai {value} di luar coupon_range {coupon_range}")
        coupon_range = (float(coupon_range[0]), float(coupon_range[1]))

    return Param(
        name=name,
        value=value,
        unit=unit,
        status=status,
        source=_text(data, "source", where),
        source_date=source_date,
        coupon_range=coupon_range,
    )


def parse_preset(data: dict, where: str = "preset") -> Preset:
    if not isinstance(data, dict):
        raise PresetError(f"{where}: isi preset wajib objek JSON")
    params = data.get("params")
    if not isinstance(params, dict) or not params:
        raise PresetError(f"{where}: 'params' wajib objek yang tidak kosong")
    preset_id = _text(data, "id", where)
    return Preset(
        id=preset_id,
        printer=_text(data, "printer", where),
        resin=_text(data, "resin", where),
        params={name: _parse_param(name, p, preset_id) for name, p in params.items()},
    )


def load_preset(path: str | Path) -> Preset:
    path = Path(path)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise PresetError(f"{path.name}: JSON tidak valid ({exc})") from exc
    return parse_preset(data, where=path.name)


def load_presets(directory: str | Path) -> dict[str, Preset]:
    presets: dict[str, Preset] = {}
    for path in sorted(Path(directory).glob("*.json")):
        preset = load_preset(path)
        if preset.id in presets:
            raise PresetError(f"{path.name}: id '{preset.id}' sudah dipakai preset lain")
        presets[preset.id] = preset
    return presets


def save_preset(preset: Preset, path: str | Path) -> None:
    text = json.dumps(preset.to_dict(), indent=2, ensure_ascii=False) + "\n"
    Path(path).write_text(text, encoding="utf-8", newline="\n")
