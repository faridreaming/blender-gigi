# SPDX-License-Identifier: GPL-3.0-or-later
"""Ekspor kupon kalibrasi tanpa Blender (geometri sama dengan operator dentalcad.export_coupons).

    python scripts/export_coupons.py                      # semua preset ke dist/kupon/<preset>/
    python scripts/export_coupons.py photon_p1_std_v2_hd_gray --out dist/kupon
"""

from __future__ import annotations

import argparse
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from core import calibration, model_presets  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("presets", nargs="*", help="id preset; kosong berarti semua")
    parser.add_argument("--out", type=Path, default=ROOT / "dist" / "kupon")
    args = parser.parse_args(argv)

    presets = model_presets.load_presets(ROOT / "data" / "model_presets")
    chosen = args.presets or sorted(presets)
    unknown = [p for p in chosen if p not in presets]
    if unknown:
        print(f"GAGAL: preset tidak dikenal: {', '.join(unknown)} (ada: {', '.join(sorted(presets))})", file=sys.stderr)
        return 1
    with (ROOT / "blender_manifest.toml").open("rb") as f:
        version = tomllib.load(f)["version"]

    for preset_id in chosen:
        out_dir = args.out / preset_id
        report = calibration.write_coupon_set(calibration.build_coupon_set(presets[preset_id]), out_dir, version)
        print(f"{preset_id}: {len(report['parts'])} STL -> {out_dir}")
        for warning in report["warnings"]:
            print(f"  belum dikalibrasi: {warning}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
