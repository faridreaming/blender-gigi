# SPDX-License-Identifier: GPL-3.0-or-later
"""Benchmark sumbu insersi, peta undercut, dan block-out terhadap die sintetis (docs/PHASE2.md §5.2).

    python scripts/insertion_benchmark.py                 # set "tuning": dipakai saat memilih parameter
    python scripts/insertion_benchmark.py --set uji       # set uji: dijalankan sekali setelah parameter dikunci
    python scripts/insertion_benchmark.py --seeds 1 --json hasil.json

Margin yang dipakai adalah margin analitis (bukan hasil Detect Margin), supaya galat §5.2 tidak tercampur
galat §5.1. Semua ukuran dibandingkan dengan jawaban benar terhadap sumbu sebenarnya (+Z die, diputar):
- sudut sumbu: sudut antara sumbu default dan sumbu sebenarnya (hanya bermakna untuk die tanpa undercut;
  pada die dengan undercut, sumbu default sengaja dimiringkan untuk mengurangi undercut);
- IoU face undercut: definisi rancangan (normal dihaluskan membelakangi sumbu dan terbayang) terhadap
  synthetic.undercut_faces() (tanda normal analitis);
- kedalaman: galat kedalaman per vertex preparasi terhadap synthetic.undercut_depth_truth();
- margin terbayang: kebenaran (kedalaman analitis titik margin > 20 um) terhadap tanda ragu "margin line lies
  in an undercut";
- block-out: kedalaman bayangan sisa pada mesh hasil block-out (tanpa penghalusan), di luar zona dekat margin.
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

from core import insertion, synthetic  # noqa: E402

NOISE_UM = (0, 10, 30, 90)
FREE_ZONE_MM = 0.1  # exocad Quick Guide: default generik "Don't block out zone near prepline" (PHASE2.md §5.2)
MARGIN_SHADOW_TRUTH_MM = 0.02

TUNING = {
    "standar": {},
    "standar + scallop PL 2": {"scallop_mm": 1.0},
    "undercut 8 di 90": dict(undercut_deg=8.0, undercut_center_deg=90.0),
    "undercut 8 di 90 + scallop PL 2": dict(scallop_mm=1.0, undercut_deg=8.0, undercut_center_deg=90.0),
}
# Set uji: didefinisikan dan dikunci bersama parameter InsertionParams SEBELUM dijalankan, lalu dijalankan sekali.
UJI = {
    "undercut 12 di puncak scallop (PL 2)": dict(scallop_mm=1.0, undercut_deg=12.0, undercut_center_deg=0.0),
    "undercut 10 di puncak CEJ (PL 3)": dict(radius_x_mm=3.8, radius_y_mm=3.4, prep_height_mm=5.5, taper_deg=7.0,
                                             finish_width_mm=0.8, scallop_mm=1.5, undercut_deg=10.0,
                                             undercut_center_deg=0.0),
    "margin terbayang (undercut 15, finish 0,5)": dict(finish_width_mm=0.5, undercut_deg=15.0,
                                                       undercut_center_deg=200.0, undercut_halfwidth_deg=35.0),
    "molar taper 10 tanpa undercut": dict(radius_x_mm=6.0, radius_y_mm=5.4, prep_height_mm=4.5, taper_deg=10.0,
                                          scallop_mm=0.6),
    "premolar undercut sempit 6": dict(radius_x_mm=4.0, radius_y_mm=3.6, prep_height_mm=4.5, taper_deg=5.0,
                                       scallop_mm=0.5, undercut_deg=6.0, undercut_center_deg=300.0,
                                       undercut_halfwidth_deg=20.0),
}
SETS = {"tuning": TUNING, "uji": UJI}


def _iou(a: np.ndarray, b: np.ndarray) -> float:
    union = (a | b).sum()
    return 1.0 if union == 0 else float((a & b).sum() / union)


def run_case(spec: synthetic.DieSpec, noise_um: int, seed: int) -> dict:
    die = synthetic.make_die(spec, noise_sigma_mm=noise_um / 1000.0, rotate=True, seed=seed)
    truth_axis = die.insertion_axis
    out = {}
    start = time.perf_counter()
    try:
        ctx = insertion.insertion_context(die.mesh, die.margin_curve(1024))
        result = insertion.default_axis(ctx)
    except insertion.InsertionError as exc:
        return {"error": str(exc)}
    out["seconds_auto"] = time.perf_counter() - start
    out["axis_error_deg"] = float(np.degrees(np.arccos(np.clip(result.axis @ truth_axis, -1, 1))))
    out["start_error_deg"] = float(np.degrees(np.arccos(np.clip(ctx.start_axis @ truth_axis, -1, 1))))
    out["doubtful"] = result.doubtful
    out["reasons"] = [name for name, _ in result.reasons]

    t0 = time.perf_counter()
    umap = insertion.undercut_map(ctx, truth_axis)
    out["seconds_map"] = time.perf_counter() - t0
    truth_faces = die.undercut_faces()
    out["iou_design"] = _iou(umap.undercut_faces, truth_faces)
    facing = ctx.region.faces & (ctx.smooth_face_normals @ truth_axis < 0)
    out["iou_normal"] = _iou(facing, truth_faces)
    out["truth_faces"] = int(truth_faces.sum())

    vp = die.vertex_params
    prep_v = ctx.region.vertices & (vp[:, 1] > 1) & (vp[:, 1] < 3.999)
    truth_depth = synthetic.undercut_depth_truth(spec, vp[prep_v, 0], vp[prep_v, 1])
    err = np.abs(umap.vertex_depth[prep_v] - truth_depth)
    out.update(depth_true_max_um=1000 * float(truth_depth.max()), depth_mae_um=1000 * float(err.mean()),
               depth_p95_um=1000 * float(np.percentile(err, 95)), depth_max_err_um=1000 * float(err.max()),
               depth_err_over_100um=int((err > 0.1).sum()), prep_vertices=int(prep_v.sum()))

    theta = np.linspace(0, 2 * np.pi, 360, endpoint=False)
    margin_truth = synthetic.undercut_depth_truth(spec, theta, np.full_like(theta, 1.0))
    out["margin_shadow_true_um"] = 1000 * float(margin_truth.max())
    out["margin_shadow_true"] = bool(margin_truth.max() > MARGIN_SHADOW_TRUTH_MM)
    doubtful, reasons, _ = insertion.check_axis(ctx, truth_axis)
    out["margin_flag_true_axis"] = any(name == "margin line lies in an undercut" for name, _ in reasons)

    blocked = insertion.block_out(ctx, truth_axis, FREE_ZONE_MM)
    out["blockout_residual_um"] = 1000 * insertion.residual_shadow(ctx, blocked)
    out["blockout_max_push_um"] = 1000 * float(blocked.displacement.max())
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--set", choices=sorted(SETS), default="tuning")
    parser.add_argument("--seeds", type=int, default=3)
    parser.add_argument("--json", type=Path)
    bench_runner.add_arguments(parser)
    args = parser.parse_args(argv)

    rows = []
    total = len(SETS[args.set]) * len(synthetic.FINISHES) * len(NOISE_UM) * args.seeds
    status = lambda r: "timeout" if r.get("timeout") else "error" if "error" in r else "ok"  # noqa: E731
    on_timeout = lambda message, seconds: {"error": message, "timeout": True}  # noqa: E731
    with bench_runner.CaseRunner(args.timeout, total, status) as runner:
        for name, overrides in SETS[args.set].items():
            for finish in synthetic.FINISHES:
                spec = synthetic.DieSpec(finish=finish, **overrides)
                for noise in NOISE_UM:
                    runs = [runner.run(f"{name} | {finish} | {noise} um | seed {seed}", run_case, (spec, noise, seed),
                                       on_timeout) for seed in range(args.seeds)]
                    rows.append({"die": name, "finish": finish, "noise_um": noise, "runs": runs})

    print(f"Set: {args.set}. Nilai = terburuk dari {args.seeds} seed (IoU: terendah; galat: tertinggi). "
          f"Margin analitis, zona tanpa block-out {FREE_ZONE_MM} mm.\n")
    print("| Die | Finish | Derau | Sudut sumbu default | Ragu (seed) | IoU face (rancangan / normal) | "
          "Kedalaman benar maks | Galat kedalaman MAE / p95 / maks | Vertex galat > 0,1 mm | "
          "Margin terbayang: benar / tertandai | Sisa bayangan setelah block-out | Waktu peta |")
    print("|---|---|---|---|---|---|---|---|---|---|---|---|")
    for r in rows:
        ok = [x for x in r["runs"] if "error" not in x]
        errors = [x["error"] for x in r["runs"] if "error" in x]
        if not ok:
            print(f"| {r['die']} | {r['finish']} | {r['noise_um']} um | error: {errors[0]} |||||||||")
            continue
        worst = lambda k: max(x[k] for x in ok)
        least = lambda k: min(x[k] for x in ok)
        doubt = sum(x["doubtful"] for x in ok)
        reasons = sorted({n for x in ok for n in x["reasons"]})
        print(f"| {r['die']} | {r['finish']} | {r['noise_um']} um | {worst('axis_error_deg'):.2f} deg | "
              f"{doubt}/{len(ok)} {'; '.join(reasons)} | {least('iou_design'):.2f} / {least('iou_normal'):.2f} | "
              f"{worst('depth_true_max_um'):.0f} um | {worst('depth_mae_um'):.1f} / {worst('depth_p95_um'):.0f} / "
              f"{worst('depth_max_err_um'):.0f} um | {worst('depth_err_over_100um')} dari {ok[0]['prep_vertices']} | "
              f"{'ya' if ok[0]['margin_shadow_true'] else 'tidak'} ({worst('margin_shadow_true_um'):.0f} um) / "
              f"{sum(x['margin_flag_true_axis'] for x in ok)}/{len(ok)} | {worst('blockout_residual_um'):.0f} um | "
              f"{worst('seconds_map'):.2f} s |" + (f" error: {len(errors)}" if errors else ""))
    print(f"\nKasus melewati batas waktu {args.timeout:g} s: {runner.timeouts}")
    if args.json:
        args.json.write_text(json.dumps(rows, indent=2, default=float), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
