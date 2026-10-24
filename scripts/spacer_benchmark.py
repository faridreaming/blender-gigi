# SPDX-License-Identifier: GPL-3.0-or-later
"""Benchmark spacer (cement gap) terhadap jawaban analitis die sintetis (docs/PHASE2.md §5.3).

    python scripts/spacer_benchmark.py                    # set "ukur": didefinisikan sebelum dijalankan
    python scripts/spacer_benchmark.py --seeds 1 --json hasil.json

Parameter spacer dari data/materials/zircad_prime.json (tidak ada yang disetel di benchmark ini). Margin analitis,
sumbu sebenarnya, block-out §5.2 dengan zona 0,1 mm, lalu spacer (urutan 5-axis exocad: block-out dulu).

Jawaban benar eksak hanya ada untuk die lingkaran tanpa scallop dan tanpa undercut: jarak geodesik ke margin =
panjang busur meridian dari margin (permukaan putar), dan offset benar = gap(d) n + s_r h(n) dari normal
analitis. Untuk die lain (elips, scallop, undercut) hanya lipatan, undercut baru di permukaan dalam, dan waktu
yang dilaporkan (kolom jawaban benar ditulis "-").
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

from core import insertion, material_db, spacer, synthetic  # noqa: E402

NOISE_UM = (0, 10, 30, 90)
FREE_ZONE_MM = 0.1
EXACT_RANGE_MM = 3.0  # galat geodesik diukur sampai jarak ini dari margin

UKUR = {
    "lingkaran r5 taper 6": dict(radius_x_mm=5.0, radius_y_mm=5.0),
    "lingkaran r4 taper 10 tinggi 4": dict(radius_x_mm=4.0, radius_y_mm=4.0, taper_deg=10.0, prep_height_mm=4.0),
    "elips + scallop PL 2": dict(scallop_mm=1.0),
    "elips + CEJ PL 3,5": dict(radius_x_mm=4.0, radius_y_mm=3.6, prep_height_mm=5.5, scallop_mm=1.75),
    "lingkaran + undercut 8": dict(radius_x_mm=5.0, radius_y_mm=5.0, undercut_deg=8.0, undercut_center_deg=90.0),
}
SETS = {"ukur": UKUR}


def _exact(spec: synthetic.DieSpec) -> bool:
    return spec.radius_x_mm == spec.radius_y_mm and spec.scallop_mm == 0 and spec.undercut_deg == 0


def meridian_distance(spec: synthetic.DieSpec, t: np.ndarray) -> np.ndarray:
    """Panjang busur profil dari margin (t = 1) sampai t, pada die lingkaran (sama untuk semua theta)."""
    grid = np.linspace(1.0, 3.999, 30001)
    pts = synthetic.surface_points(spec, np.zeros_like(grid), grid)
    s = np.concatenate([[0.0], np.cumsum(np.linalg.norm(np.diff(pts, axis=0), axis=1))])
    return np.interp(np.asarray(t, float), grid, s)


def run_case(spec: synthetic.DieSpec, noise_um: int, seed: int, params: spacer.SpacerParams) -> dict:
    die = synthetic.make_die(spec, noise_sigma_mm=noise_um / 1000.0, rotate=True, seed=seed)
    axis = die.insertion_axis
    start = time.perf_counter()
    ctx = insertion.insertion_context(die.mesh, die.margin_curve(1024))
    blocked = insertion.block_out(ctx, axis, FREE_ZONE_MM)
    faces = spacer.inner_faces(ctx.vertices, ctx.faces, ctx.region.faces, ctx.region.band_faces, ctx.margin)
    t0 = time.perf_counter()
    result = spacer.spacer_surface(blocked.mesh, faces, ctx.margin, axis, params)
    out = {"seconds_spacer": time.perf_counter() - t0, "seconds_total": time.perf_counter() - start,
           "folded": result.folded_faces - result.folded_slivers, "slivers": result.folded_slivers,
           "inner_vertices": len(result.vertex_index),
           "new_undercut_um": 1000 * spacer.new_undercut_mm(result, ctx.margin), "exact": _exact(spec)}
    if not out["exact"]:
        return out

    vp = die.vertex_params[result.vertex_index]
    d_true = meridian_distance(spec, vp[:, 1])
    n_true = synthetic.surface_normals(spec, vp[:, 0], np.minimum(vp[:, 1], 3.999)) @ die.rotation.T
    h_true = n_true - (n_true @ axis)[:, None] * axis
    gap_true = spacer.gap_profile(d_true, params)
    disp_true = gap_true[:, None] * n_true + params.radial_mm * h_true + params.axial_mm * (n_true @ axis)[:, None] * axis

    near = d_true <= EXACT_RANGE_MM
    derr = np.abs(result.distance_mm - d_true)[near]
    zero = d_true < params.from_margin_mm
    full = d_true > params.from_margin_mm + params.transition_mm
    gap_err = np.abs(result.gap_mm - gap_true)
    disp_err = np.linalg.norm(result.displacement - disp_true, axis=1)
    # Spacing radial di zona nol (gap = 0, axial = 0): panjang offset = s_r |h(n)|, dibandingkan dengan normal analitis
    # pada dinding (|h| > 0,9).
    wall = np.linalg.norm(h_true, axis=1) > 0.9
    radial_err = np.abs(np.linalg.norm(result.displacement, axis=1) - params.radial_mm * np.linalg.norm(h_true, axis=1))
    out.update(
        d_err_median_um=1000 * float(np.median(derr)), d_err_p95_um=1000 * float(np.percentile(derr, 95)),
        d_err_max_um=1000 * float(derr.max()),
        zero_zone_gap_max_um=1000 * float(result.gap_mm[zero].max()) if zero.any() else 0.0,
        zero_zone_gap_count=int(np.sum(result.gap_mm[zero] > 1e-3)), zero_zone_vertices=int(zero.sum()),
        full_zone_gap_err_max_um=1000 * float(gap_err[full].max()) if full.any() else 0.0,
        transition_gap_err_max_um=1000 * float(gap_err.max()),
        disp_err_p95_um=1000 * float(np.percentile(disp_err, 95)), disp_err_max_um=1000 * float(disp_err.max()),
        radial_err_wall_max_um=1000 * float(radial_err[wall & zero].max()) if (wall & zero).any() else 0.0,
    )
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--set", choices=sorted(SETS), default="ukur")
    parser.add_argument("--seeds", type=int, default=3)
    parser.add_argument("--json", type=Path)
    args = parser.parse_args(argv)
    preset = material_db.load_material_preset(ROOT / "data" / "materials" / "zircad_prime.json")
    params = spacer.SpacerParams.from_preset(preset)

    rows = []
    for name, overrides in SETS[args.set].items():
        for finish in synthetic.FINISHES:
            spec = synthetic.DieSpec(finish=finish, **overrides)
            for noise in NOISE_UM:
                runs = [run_case(spec, noise, seed, params) for seed in range(args.seeds)]
                rows.append({"die": name, "finish": finish, "noise_um": noise, "runs": runs})

    print(f"Set: {args.set}. Parameter: cement gap {1000 * params.cement_gap_mm:.0f} um, from margin "
          f"{params.from_margin_mm} mm, transisi {params.transition_mm} mm (linear), radial "
          f"{1000 * params.radial_mm:.0f} um, axial {1000 * params.axial_mm:.0f} um. Nilai = terburuk dari "
          f"{args.seeds} seed. Kolom jawaban benar hanya untuk die lingkaran tanpa scallop/undercut.\n")
    print("| Die | Finish | Derau | Galat jarak geodesik median / p95 / maks | Gap di zona nol (vertex, maks) | "
          "Galat gap zona penuh maks | Galat gap terbesar (transisi) | Galat spacing radial dinding maks | "
          "Galat vektor offset p95 / maks | Face terlipat (bukan sliver) | Undercut baru di permukaan dalam | Waktu spacer |")
    print("|---|---|---|---|---|---|---|---|---|---|---|---|")
    for r in rows:
        runs = r["runs"]
        worst = lambda k: max(x[k] for x in runs)
        if runs[0]["exact"]:
            cells = (f"{worst('d_err_median_um'):.0f} / {worst('d_err_p95_um'):.0f} / {worst('d_err_max_um'):.0f} um | "
                     f"{worst('zero_zone_gap_count')} dari {runs[0]['zero_zone_vertices']}, "
                     f"{worst('zero_zone_gap_max_um'):.1f} um | {worst('full_zone_gap_err_max_um'):.1f} um | "
                     f"{worst('transition_gap_err_max_um'):.1f} um | {worst('radial_err_wall_max_um'):.1f} um | "
                     f"{worst('disp_err_p95_um'):.1f} / {worst('disp_err_max_um'):.1f} um")
        else:
            cells = "- | - | - | - | - | -"
        print(f"| {r['die']} | {r['finish']} | {r['noise_um']} um | {cells} | {worst('folded')} "
              f"(+{worst('slivers')} sliver) | "
              f"{worst('new_undercut_um'):.0f} um | {worst('seconds_spacer'):.2f} s |")
    if args.json:
        args.json.write_text(json.dumps(rows, indent=2, default=float), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
