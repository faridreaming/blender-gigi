# SPDX-License-Identifier: GPL-3.0-or-later
"""Benchmark akurasi margin terhadap margin analitis die sintetis (docs/PHASE2.md §5.1 dan §7).

    python scripts/margin_benchmark.py                 # matriks penuh, tabel markdown
    python scripts/margin_benchmark.py --seeds 1 --json hasil.json

Satu baris per kombinasi finish x scallop x derau; setiap kombinasi dijalankan untuk beberapa seed
(posisi klik, jitter mesh, derau, dan rotasi acak berbeda). Tidak ada baris yang disembunyikan: kombinasi
yang gagal atau melempar error tetap dilaporkan.
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

FINISHES = ("shoulder", "chamfer")
SCALLOPS_MM = (0.0, 1.0)
NOISE_UM = (0, 10, 30, 90)
CRITERION_MEDIAN_MM = 0.050  # PHASE2.md §7, angka roadmap


def click_near_margin(die: synthetic.SyntheticDie, rng: np.random.Generator) -> np.ndarray:
    """Titik klik: titik margin analitis pada sudut acak, digeser acak sampai 0,3 mm (klik tidak tepat)."""
    theta = rng.uniform(0, 2 * np.pi)
    point = synthetic.margin_points(die.spec, np.array([theta]))[0] @ die.rotation.T
    return point + rng.normal(0, 0.15, 3)


def run_case(finish: str, scallop: float, noise_um: int, seed: int) -> dict:
    spec = synthetic.DieSpec(finish=finish, scallop_mm=scallop)
    die = synthetic.make_die(spec, noise_sigma_mm=noise_um / 1000.0, rotate=True, seed=seed)
    rng = np.random.default_rng(10_000 + seed)
    start = time.perf_counter()
    try:
        result = margin.detect_margin(die.mesh, click_near_margin(die, rng))
        dev = margin.margin_deviation(result.curve.sample(2048), die.margin_curve(8192))
        dev["error"] = ""
    except margin.MarginError as exc:
        dev = {"median": float("nan"), "p95": float("nan"), "max": float("nan"),
               "coverage_p95": float("nan"), "coverage_max": float("nan"), "error": str(exc)}
    dev["seconds"] = time.perf_counter() - start
    return dev


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--seeds", type=int, default=3)
    parser.add_argument("--json", type=Path)
    args = parser.parse_args(argv)

    rows = []
    for finish in FINISHES:
        for scallop in SCALLOPS_MM:
            for noise in NOISE_UM:
                runs = [run_case(finish, scallop, noise, seed) for seed in range(args.seeds)]
                medians = np.array([r["median"] for r in runs])
                rows.append({
                    "finish": finish, "scallop_mm": scallop, "noise_um": noise,
                    "median_um": 1000 * float(np.nanmax(medians)) if np.isfinite(medians).any() else float("nan"),
                    "p95_um": 1000 * float(np.nanmax([r["p95"] for r in runs])),
                    "max_um": 1000 * float(np.nanmax([r["max"] for r in runs])),
                    "coverage_p95_um": 1000 * float(np.nanmax([r["coverage_p95"] for r in runs])),
                    "errors": sum(1 for r in runs if r["error"]),
                    "passes": bool(np.all(medians <= CRITERION_MEDIAN_MM)),
                    "seconds": float(np.mean([r["seconds"] for r in runs])),
                    "runs": runs,
                })

    print(f"Median deviasi: nilai terburuk dari {args.seeds} seed per kombinasi. Kriteria: median <= 50 um.\n")
    print("| Finish | Scallop | Derau | Median | p95 | Maks | Cakupan p95 | Error | Lulus median <= 50 um | Waktu |")
    print("|---|---|---|---|---|---|---|---|---|---|")
    for r in rows:
        print(f"| {r['finish']} | {r['scallop_mm']:g} mm | {r['noise_um']} um | {r['median_um']:.1f} um | "
              f"{r['p95_um']:.1f} um | {r['max_um']:.1f} um | {r['coverage_p95_um']:.1f} um | {r['errors']} | "
              f"{'ya' if r['passes'] else 'TIDAK'} | {r['seconds']:.2f} s |")
    if args.json:
        args.json.write_text(json.dumps(rows, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
