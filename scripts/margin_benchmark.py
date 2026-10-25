# SPDX-License-Identifier: GPL-3.0-or-later
"""Benchmark akurasi margin terhadap margin analitis die sintetis (docs/PHASE2.md §5.1 dan §7).

    python scripts/margin_benchmark.py                       # set "tuning": die yang dipakai saat menyetel
    python scripts/margin_benchmark.py --set tuning2         # set tuning kedua (dulu "unseen", sudah terpakai)
    python scripts/margin_benchmark.py --set tuning3         # set tuning ketiga (set uji pertama, sudah terpakai)
    python scripts/margin_benchmark.py --set uji             # set uji kedua: dijalankan sekali setelah dikunci
    python scripts/margin_benchmark.py --seeds 1 --json hasil.json

Scallop ditulis sebagai tinggi puncak-lembah (PL) margin = 2 x DieSpec.scallop_mm (amplitudo cos 2 theta),
supaya sebanding dengan lengkungan CEJ di Gallucci dkk. 2004 (PHASE2.md §5.1).

Satu baris per kombinasi; setiap kombinasi dijalankan untuk beberapa seed (posisi klik, jitter mesh, derau,
dan rotasi acak berbeda). Tidak ada baris yang disembunyikan. Kolom "Hasil" per seed:
- kurva: kurva dihasilkan tanpa segmen merah (deviasinya masuk statistik);
- kurva+merah: kurva dihasilkan dengan >= 1 segmen yang ditandai "need review" (deviasinya masuk statistik);
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

from scripts import bench_runner  # noqa: E402

from core import margin, synthetic  # noqa: E402

NOISE_UM = (0, 10, 30, 90)
CRITERION_MEDIAN_MM = 0.050  # PHASE2.md §7, angka roadmap
CRITERION_COVERAGE_MM = 0.150  # ambang uji: kurva menutupi seluruh margin

# Die yang dipakai selama penyetelan parameter (spike S1), ditambah varian lengkungan CEJ anterior
# (Gallucci dkk. 2004: mesial insisif sentral 3,46 mm, lateral 2,97 mm, kaninus 2,55 mm).
TUNING = {
    "standar": {},
    "scallop PL 2,0 mm": {"scallop_mm": 1.0},
    "CEJ PL 2,5 mm": {"scallop_mm": 1.25},
    "CEJ PL 3,5 mm": {"scallop_mm": 1.75},
}
# Set tuning kedua: dulu set "unseen" untuk uji overfitting; setelah hasilnya dipakai untuk memperbaiki metrik
# panjang kurva, set ini tidak lagi "belum pernah dilihat".
TUNING2 = {
    "premolar kecil (PL 1,0)": dict(radius_x_mm=3.8, radius_y_mm=3.4, prep_height_mm=4.0, taper_deg=4.0, scallop_mm=0.5),
    "molar besar (PL 3,0)": dict(radius_x_mm=6.0, radius_y_mm=5.4, prep_height_mm=6.5, taper_deg=10.0, scallop_mm=1.5),
    "taper lebar (PL 0,6)": dict(radius_x_mm=5.0, radius_y_mm=4.4, prep_height_mm=5.0, taper_deg=14.0, scallop_mm=0.3),
    "scallop dalam (PL 4,0)": dict(radius_x_mm=4.5, radius_y_mm=4.2, prep_height_mm=6.0, taper_deg=6.0, scallop_mm=2.0),
}
# Set tuning ketiga: set uji pertama (dikunci di a351e40, dijalankan sekali). Kasus insisif sentralnya dipakai
# untuk memperbaiki pemilihan titik jauh, jadi set ini sekarang set tuning.
TUNING3 = {
    "insisif sentral (PL 3,2)": dict(radius_x_mm=3.6, radius_y_mm=3.2, prep_height_mm=5.5, taper_deg=8.0,
                                     finish_width_mm=0.8, scallop_mm=1.6),
    "kaninus (PL 2,4)": dict(radius_x_mm=3.4, radius_y_mm=4.0, prep_height_mm=6.0, taper_deg=5.0, scallop_mm=1.2),
    "molar pendek (PL 0,8)": dict(radius_x_mm=5.6, radius_y_mm=5.0, prep_height_mm=3.5, taper_deg=12.0, scallop_mm=0.4),
    "premolar elips (PL 1,6)": dict(radius_x_mm=4.4, radius_y_mm=3.1, prep_height_mm=4.5, taper_deg=7.0, scallop_mm=0.8),
    "undercut 8 derajat (PL 1,2)": dict(radius_x_mm=4.8, radius_y_mm=4.3, prep_height_mm=5.0, taper_deg=3.0,
                                        scallop_mm=0.6, undercut_deg=8.0, undercut_center_deg=90.0),
}
# Set uji kedua: didefinisikan dan dikunci bersama semua parameter, ambang kewajaran, dan ambang penanda
# SEBELUM dijalankan, lalu dijalankan sekali. Kombinasi ukuran, taper, lebar finish, scallop, dan undercut baru.
UJI = {
    "lateral (PL 2,9)": dict(radius_x_mm=3.2, radius_y_mm=2.9, prep_height_mm=5.0, taper_deg=6.0,
                             finish_width_mm=0.7, scallop_mm=1.45),
    "kaninus lebar (PL 2,5)": dict(radius_x_mm=3.6, radius_y_mm=4.4, prep_height_mm=6.5, taper_deg=9.0,
                                   scallop_mm=1.25),
    "molar lebar pendek (PL 1,4)": dict(radius_x_mm=6.4, radius_y_mm=5.8, prep_height_mm=4.0, taper_deg=8.0,
                                        finish_width_mm=1.2, scallop_mm=0.7),
    "premolar taper 16 (PL 1,0)": dict(radius_x_mm=4.0, radius_y_mm=3.6, prep_height_mm=4.5, taper_deg=16.0,
                                       scallop_mm=0.5),
    "undercut di puncak (PL 2,0)": dict(radius_x_mm=4.6, radius_y_mm=4.1, prep_height_mm=5.5, taper_deg=4.0,
                                        scallop_mm=1.0, undercut_deg=12.0, undercut_center_deg=0.0),
}
SETS = {"tuning": TUNING, "tuning2": TUNING2, "tuning3": TUNING3, "uji": UJI}


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
        out["review_segments"] = result.review.count
        if result.review.count:
            out["outcome"] = "kurva+merah"
    except margin.MarginNoiseError as exc:
        out.update(outcome="derau", message=str(exc))
    except margin.MarginPlausibilityError as exc:
        out.update(outcome="tidak wajar", message=str(exc))
    except margin.MarginError as exc:
        out.update(outcome="error", message=str(exc))
    out["seconds"] = time.perf_counter() - start
    curve = out["outcome"] in ("kurva", "kurva+merah")
    out["ok"] = curve and out["median"] <= CRITERION_MEDIAN_MM and out["coverage_p95"] <= CRITERION_COVERAGE_MM
    out["silent_bad"] = out["outcome"] == "kurva" and not out["ok"]  # buruk, tanpa pesan, tanpa segmen merah
    out["flagged_bad"] = out["outcome"] == "kurva+merah" and not out["ok"]
    out["flagged_good"] = out["outcome"] == "kurva+merah" and out["ok"]
    return out


def _worst(runs, key):
    values = [r[key] for r in runs if r["outcome"] in ("kurva", "kurva+merah")]
    return 1000 * max(values) if values else float("nan")


def _timeout_result(message: str, seconds: float) -> dict:
    nan = float("nan")
    return {"outcome": "timeout", "median": nan, "p95": nan, "max": nan, "coverage_p95": nan, "message": message,
            "seconds": seconds, "ok": False, "silent_bad": False, "flagged_bad": False, "flagged_good": False}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--set", choices=sorted(SETS), default="tuning")
    parser.add_argument("--seeds", type=int, default=3)
    parser.add_argument("--json", type=Path)
    bench_runner.add_arguments(parser)
    args = parser.parse_args(argv)

    rows = []
    total = len(SETS[args.set]) * len(synthetic.FINISHES) * len(NOISE_UM) * args.seeds
    with bench_runner.CaseRunner(args.timeout, total, lambda r: r["outcome"]) as runner:
        for name, overrides in SETS[args.set].items():
            for finish in synthetic.FINISHES:
                spec = synthetic.DieSpec(finish=finish, **overrides)
                for noise in NOISE_UM:
                    runs = [runner.run(f"{name} | {finish} | {noise} um | seed {seed}", run_case,
                                       (spec, noise, seed), _timeout_result) for seed in range(args.seeds)]
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
                        "flagged_bad": sum(r["flagged_bad"] for r in runs),
                        "flagged_good": sum(r["flagged_good"] for r in runs),
                        "runs": runs,
                    })

    print(f"Set: {args.set}. Nilai = terburuk dari {args.seeds} seed, hanya dari seed yang menghasilkan kurva. "
          "Kriteria: median <= 50 um dan cakupan p95 <= 150 um.\n")
    print("| Die | Finish | Derau | Hasil per seed | Median | p95 | Cakupan p95 | Memenuhi kriteria | "
          "Buruk, bertanda merah | Baik, bertanda merah | Kurva buruk tanpa pesan |")
    print("|---|---|---|---|---|---|---|---|---|---|---|")
    for r in rows:
        fmt = lambda v: "-" if np.isnan(v) else f"{v:.1f} um"
        print(f"| {r['die']} | {r['finish']} | {r['noise_um']} um | {r['outcomes']} | {fmt(r['median_um'])} | "
              f"{fmt(r['p95_um'])} | {fmt(r['coverage_p95_um'])} | {'ya' if r['all_ok'] else 'TIDAK'} | "
              f"{r['flagged_bad']} | {r['flagged_good']} | {r['silent_bad']} |")
    runs = [x for r in rows for x in r["runs"] if x["outcome"] in ("kurva", "kurva+merah")]
    print(f"\nTotal kurva buruk tanpa pesan dan tanpa segmen merah: {sum(r['silent_bad'] for r in rows)}")
    print(f"Kurva buruk bertanda merah: {sum(r['flagged_bad'] for r in rows)}; "
          f"kurva baik bertanda merah: {sum(r['flagged_good'] for r in rows)} dari {len(runs)} kurva")
    print(f"Kasus melewati batas waktu {args.timeout:g} s: {runner.timeouts}")
    if args.json:
        args.json.write_text(json.dumps(rows, indent=2, default=float), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
