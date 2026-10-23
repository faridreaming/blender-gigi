# SPDX-License-Identifier: GPL-3.0-or-later
"""Terapkan lembar ukur kupon ke preset printer + resin (docs/PHASE1.md §5.K).

    python scripts/apply_calibration.py data/model_presets/photon_p1_std_v2_hd_gray.json \\
        dist/kupon/photon_p1_std_v2_hd_gray/kupon_lembar_ukur.csv --date 2026-11-02

Tanpa --write hanya menampilkan hasil. Faktor skala dihitung dari baris kupon dimensi.
Clearance, tebal dinding, dan jumlah lubang adalah penilaian teknisi atas kupon 2 dan 3, jadi
diberikan lewat opsi, bukan dihitung.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from core import calibration, model_presets  # noqa: E402


def calibrate(preset: model_presets.Preset, rows: list[dict], when: str, args) -> tuple[model_presets.Preset, list[str]]:
    lines = []
    source = f"kupon {when}, printer {preset.printer}, resin {preset.resin}"
    fits = calibration.fit_scale(rows)
    for axis, fit in fits.items():
        lines.append(
            f"{axis}: faktor {fit.factor:.5f} (slope {fit.slope:.5f}, offset {fit.offset_mm:+.3f} mm, "
            f"residu maks {fit.max_residual_mm:.3f} mm, n={fit.n})"
        )
        preset = preset.with_value(f"scale_{axis.lower()}", round(fit.factor, 6), "dikalibrasi",
                                   f"{source}; offset {fit.offset_mm:+.3f} mm tidak dikompensasi", when)
    missing = [a for a in "XYZ" if a not in fits]
    if missing:
        lines.append(f"belum diukur: sumbu {', '.join(missing)} (faktor tetap {', '.join(missing)})")

    for option, name in (("clearance", "die_clearance"), ("wall", "hollow_wall_thickness"), ("holes", "drain_hole_count")):
        value = getattr(args, option)
        if value is not None:
            preset = preset.with_value(name, value, "dikalibrasi", f"{source}; dipilih teknisi", when)
            lines.append(f"{name} = {value} (dipilih teknisi)")
    return preset, lines


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("preset", type=Path)
    parser.add_argument("sheet", type=Path)
    parser.add_argument("--date", required=True, help="tanggal kupon diukur, YYYY-MM-DD")
    parser.add_argument("--clearance", type=float, help="clearance yang lolos uji kupon 2 (mm)")
    parser.add_argument("--wall", type=float, help="tebal dinding hollow yang lolos uji kupon 3 (mm)")
    parser.add_argument("--holes", type=int, help="jumlah lubang drainase yang lolos uji kupon 3")
    parser.add_argument("--write", action="store_true", help="tulis hasil ke file preset")
    args = parser.parse_args(argv)

    preset = model_presets.load_preset(args.preset)
    rows = calibration.read_measurement_sheet(args.sheet)
    try:
        updated, lines = calibrate(preset, rows, args.date, args)
    except (ValueError, model_presets.PresetError) as exc:
        print(f"GAGAL: {exc}", file=sys.stderr)
        return 1

    for line in lines:
        print(line)
    for warning in updated.warnings():
        print(f"masih belum dikalibrasi: {warning}")
    if args.write:
        model_presets.save_preset(updated, args.preset)
        print(f"ditulis ke {args.preset}")
    else:
        print("(belum ditulis; tambahkan --write)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
