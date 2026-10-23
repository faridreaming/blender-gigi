# SPDX-License-Identifier: GPL-3.0-or-later
"""Benchmark akurasi margin terhadap margin analitis die sintetis (docs/PHASE2.md §5.1 dan §7).

    python scripts/margin_benchmark.py                       # set "tuning": die yang dipakai saat menyetel
    python scripts/margin_benchmark.py --set unseen          # varian die yang tidak pernah dipakai menyetel
    python scripts/margin_benchmark.py --seeds 1 --json hasil.json

Satu baris per kombinasi; setiap kombinasi dijalankan untuk beberapa seed (posisi klik, jitter mesh, derau,
dan rotasi acak berbeda). Tidak ada baris yang disembunyikan. Kolom "Hasil" per seed:
- kurva: kurva dihasilkan (deviasinya masuk statistik);
- derau: ditolak karena perkiraan derau di atas ambang (pesan "gambar margin manual");
- tidak wajar: kurva ditolak oleh pemeriksaan kewajaran;
- error: error lain dari deteksi.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from core import margin, synthetic  # noqa: E402

NOISE_UM = (0, 10, 30, 90)
CRITERION_MEDIAN_MM = 0.050  # PHASE2.md §7, angka roadmap
CRITERION_COVERAGE_MM = 0.150  # ambang uji: kurva menutupi seluruh margin

# Die yang dipakai selama penyetelan parameter (spike S1).
TUNING = {
    "standar": {},
    "standar + scallop 1 mm": {"scallop_mm": 1.0},
}
# Varian yang TIDAK pernah dipakai menyetel (uji overfitting): diameter, tinggi, taper, dan scallop berbeda.
UNSEEN = {
    "premolar kecil": dict(radius_x_mm=3.8, radius_y_mm=3.4, prep_height_mm=4.0, taper_deg=4.0, scallop_mm=0.5),
    "molar besar": dict(radius_x_mm=6.0, radius_y_mm=5.4, prep_height_mm=6.5, taper_deg=10.0, scallop_mm=1.5),
    "taper lebar": dict(radius_x_mm=5.0, radius_y_mm=4.4, prep_height_mm=5.0, taper_deg=14.0, scallop_mm=0.3),
    "scallop dalam": dict(radius_x_mm=4.5, radius_y_mm=4.2, prep_height_mm=6.0, taper_deg=6.0, scallop_mm=2.0),
}
SETS = {"tuning": TUNING, "unseen": UNSEEN}


def click_near_margin(die: synthetic.SyntheticDie, rng: np.random.Generator) -> np.ndarray:
    """Titik klik: titik margin analitis pada sudut acak, digeser acak (sigma 0,15 mm per sumbu)."""
    theta = rng.uniform(0, 2 * np.pi)
    point = synthetic.margin_points(die.spec, np.array([theta]))[0] @ die.rotation.T
    return point + rng.normal(0, 0.15, 3)


def run_case(spec: synthetic.DieSpec, noise_um: int, seed: int, params=margin.MarginParams()) -> dict:
    die = synthetic.make_die(spec, noise_sigma_mm=noise_um / 1000.0, rotate=True, seed=seed)
    rng = np.random.default_rng(10_000 + seed)
    start = time.perf_counter()
    out = {"outcome": "kurva", "median": np.nan, "p95": np.nan, "max": np.nan, "coverage_p95": np.nan, "message": ""}
    try:
        result = margin.detect_margin(die.mesh, click_near_margin(die, rng), params)
        out.update(margin.margin_deviation(result.curve.sample(2048), die.margin_curve(8192)))
    except margin.MarginNoiseError as exc:
        out.update(outcome="derau", message=str(exc))
    except margin.MarginPlausibilityError as exc:
        out.update(outcome="tidak wajar", message=str(exc))
    except margin.MarginError as exc:
        out.update(outcome="error", message=str(exc))
    out["seconds"] = time.perf_counter() - start
    out["ok"] = out["outcome"] == "kurva" and out["median"] <= CRITERION_MEDIAN_MM and \
        out["coverage_p95"] <= CRITERION_COVERAGE_MM
    out["silent_bad"] = out["outcome"] == "kurva" and not out["ok"]
    return out


def _worst(runs, key):
    values = [r[key] for r in runs if r["outcome"] == "kurva"]
    return 1000 * max(values) if values else float("nan")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--set", choices=sorted(SETS), default="tuning")
    parser.add_argument("--seeds", type=int, default=3)
    parser.add_argument("--json", type=Path)
    args = parser.parse_args(argv)

    rows = []
    for name, overrides in SETS[args.set].items():
        for finish in synthetic.FINISHES:
            spec = synthetic.DieSpec(finish=finish, **overrides)
            for noise in NOISE_UM:
                runs = [run_case(spec, noise, seed) for seed in range(args.seeds)]
                outcomes = {}
                for r in runs:
                    outcomes[r["outcome"]] = outcomes.get(r["outcome"], 0) + 1
                rows.append({
                    "die": name, "finish": finish, "noise_um": noise,
                    "median_um": _worst(runs, "median"), "p95_um": _worst(runs, "p95"),
                    "coverage_p95_um": _worst(runs, "coverage_p95"),
                    "outcomes": ", ".join(f"{k} {v}" for k, v in sorted(outcomes.items())),
                    "all_ok": all(r["ok"] for r in runs),
                    "silent_bad": sum(r["silent_bad"] for r in runs),
                    "runs": runs,
                })

    print(f"Set: {args.set}. Nilai = terburuk dari {args.seeds} seed, hanya dari seed yang menghasilkan kurva. "
          "Kriteria: median <= 50 um dan cakupan p95 <= 150 um.\n")
    print("| Die | Finish | Derau | Hasil per seed | Median | p95 | Cakupan p95 | Memenuhi kriteria | Kurva buruk tanpa pesan |")
    print("|---|---|---|---|---|---|---|---|---|")
    for r in rows:
        fmt = lambda v: "-" if np.isnan(v) else f"{v:.1f} um"
        print(f"| {r['die']} | {r['finish']} | {r['noise_um']} um | {r['outcomes']} | {fmt(r['median_um'])} | "
              f"{fmt(r['p95_um'])} | {fmt(r['coverage_p95_um'])} | {'ya' if r['all_ok'] else 'TIDAK'} | "
              f"{r['silent_bad']} |")
    print(f"\nTotal kurva buruk tanpa pesan: {sum(r['silent_bad'] for r in rows)}")
    if args.json:
        args.json.write_text(json.dumps(rows, indent=2, default=float), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
