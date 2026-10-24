# SPDX-License-Identifier: GPL-3.0-or-later
"""Benchmark proposal crown langkah 1 sampai 3 terhadap gigi tetangga dan antagonis sintetis (PHASE2.md §5.4).

    python scripts/crown_benchmark.py --set tuning     # dipakai saat menyetel (iterasi, campuran margin)
    python scripts/crown_benchmark.py --set ukur       # dikunci bersama kode sebelum dijalankan, lalu sekali
    python scripts/crown_benchmark.py --seeds 1 --json hasil.json

Margin analitis dan sumbu sebenarnya (galat §5.1 dan §5.2 tidak tercampur). Mesh tetangga dan antagonis memakai
generator die (jitter, derau, rotasi die); jawaban benar dari bentuk analitis:
- jarak kontak: jarak bertanda EKSAK dari vertex crown ke elipsoid tetangga (bisection Eberly) dan ke bidang atau
  silinder antagonis, dibanding target (approximal -20 um, oklusal 0 um, Nagata 2025);
- arah mesial: sudut antara arah mesial dari tetangga dan sumbu mesial die yang diketahui;
- tepi servikal: jarak tepi bawah crown ke margin yang dipakai (0 menurut konstruksi);
- lipatan: face yang berbalik dibanding template murni;
- kasus "sempit" harus berakhir dengan CrownError (error eksplisit), bukan crown yang menembus.
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

from core import crown, synthetic  # noqa: E402

NOISE_UM = (0, 10, 30)
ELLIPSOID = np.array([4.0, 4.5, 3.5])


def _rot(axis: str, deg: float) -> np.ndarray:
    c, s = np.cos(np.radians(deg)), np.sin(np.radians(deg))
    if axis == "y":
        return np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]])
    return np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]])


# Kasus: die, FDI, tetangga (celah dari tepi margin + tonjolan kontur ke permukaan dalam elipsoid, mm; None = tanpa),
# kemiringan tetangga, antagonis (jenis, jarak dari puncak preparasi, kemiringan), dan apakah error diharapkan.
TUNING = {
    "molar, tetangga simetris, antagonis datar": dict(die={}, fdi=46, gaps=(0.6, 0.6), ant=("plane", 3.6, 0.0)),
    "molar scallop PL 2, tetangga asimetris": dict(die={"scallop_mm": 1.0}, fdi=26, gaps=(1.2, 0.3), ant=("plane", 3.8, 0.0)),
    "molar, antagonis terlalu dekat (error)": dict(die={}, fdi=46, gaps=(0.6, 0.6), ant=("plane", 2.5, 0.0), expect_error=True),
    "molar, tetangga terlalu dekat (error)": dict(die={}, fdi=46, gaps=(-1.6, -1.6), ant=("plane", 3.6, 0.0), expect_error=True),
}
UJI = {
    "premolar kecil, tetangga miring 15": dict(die=dict(radius_x_mm=3.8, radius_y_mm=3.4, prep_height_mm=4.0, taper_deg=4.0,
                                                         scallop_mm=0.5), fdi=15, gaps=(0.4, 0.8), tilt=15.0,
                                                ant=("plane", 3.4, 8.0)),
    "molar besar, antagonis silinder": dict(die=dict(radius_x_mm=6.0, radius_y_mm=5.4, prep_height_mm=6.5, taper_deg=10.0,
                                                      scallop_mm=1.5), fdi=36, gaps=(0.5, 0.5), ant=("cylinder", 3.6, 0.0)),
    "insisif sentral, hanya tetangga mesial": dict(die=dict(radius_x_mm=3.6, radius_y_mm=3.2, prep_height_mm=5.5,
                                                             taper_deg=8.0, finish_width_mm=0.8, scallop_mm=1.6),
                                                    fdi=11, gaps=(0.7, None), ant=("plane", 2.6, 12.0)),
    "kaninus, tanpa tetangga dan antagonis": dict(die=dict(radius_x_mm=3.4, radius_y_mm=4.0, prep_height_mm=6.0,
                                                            taper_deg=5.0, scallop_mm=1.2), fdi=13, gaps=(None, None),
                                                   ant=None),
    "premolar, antagonis miring terlalu dekat (error)": dict(die=dict(radius_x_mm=4.0, radius_y_mm=3.6, prep_height_mm=4.5,
                                                                       taper_deg=7.0, scallop_mm=0.8), fdi=24,
                                                              gaps=(0.5, 0.5), ant=("plane", 2.0, 10.0), expect_error=True),
}
SETS = {"tuning": TUNING, "ukur": UJI}


def build_case(case: dict, finish: str, noise_um: int, seed: int):
    spec = synthetic.DieSpec(finish=finish, **case["die"])
    die = synthetic.make_die(spec, noise_sigma_mm=noise_um / 1000.0, rotate=True, seed=seed)
    R = die.rotation
    margin_die = synthetic.margin_points(spec, np.linspace(0, 2 * np.pi, 1024, endpoint=False))
    center_z = float(margin_die[:, 2].mean())
    prep_top = spec.top_z + spec.roof_height_mm - center_z
    z_k = center_z + 0.4 * spec.prep_height_mm
    bulge = crown.CrownParams().contour_bulge_mm
    x_max, x_min = float(margin_die[:, 0].max()), float(margin_die[:, 0].min())
    tilt = case.get("tilt", 0.0)
    neighbors = {}
    for name, gap, sign in (("mesial", case["gaps"][0], 1.0), ("distal", case["gaps"][1], -1.0)):
        if gap is None:
            continue
        edge = (x_max if sign > 0 else x_min) + sign * (bulge + gap)
        rot = _rot("y", sign * tilt) @ _rot("z", 0.7 * tilt)
        neighbors[name] = synthetic.Ellipsoid(np.array([edge + sign * ELLIPSOID[0], 0.0, z_k]), ELLIPSOID, rot)
    antagonist = None
    if case["ant"] is not None:
        kind, clearance, tilt_ant = case["ant"]
        height = center_z + prep_top + clearance
        if kind == "plane":
            normal = _rot("y", tilt_ant) @ np.array([0.0, 0.0, -1.0])
            antagonist = synthetic.AntagonistPlane(np.array([0.0, 0.0, height]), normal)
        else:
            radius = 14.0
            antagonist = synthetic.AntagonistCylinder(np.array([0.0, 0.0, height + radius]), np.array([0.0, 1.0, 0.0]),
                                                      radius, down=np.array([0.0, 0.0, -1.0]))
    world = lambda mesh: synthetic.MeshData(mesh.vertices @ R.T, mesh.faces)  # noqa: E731
    noise = noise_um / 1000.0
    meshes = {name: world(e.mesh(noise_sigma_mm=noise, seed=seed + k)) for k, (name, e) in enumerate(neighbors.items())}
    ant_mesh = world(antagonist.mesh(noise_sigma_mm=noise, seed=seed + 7)) if antagonist is not None else None
    return spec, die, prep_top, neighbors, antagonist, meshes, ant_mesh


def run_case(case: dict, finish: str, noise_um: int, seed: int) -> dict:
    spec, die, prep_top, neighbors, antagonist, meshes, ant_mesh = build_case(case, finish, noise_um, seed)
    R = die.rotation
    margin = die.margin_curve(1024)
    axis = die.insertion_axis
    true_mesial = R[:, 0]
    mesial = crown.mesial_from_neighbors(margin, axis, meshes.get("mesial"), meshes.get("distal"))
    out = {"expect_error": bool(case.get("expect_error", False))}
    out["mesial_error_deg"] = (float(np.degrees(np.arccos(np.clip(mesial @ true_mesial, -1, 1))))
                               if mesial is not None else None)
    start = time.perf_counter()
    try:
        fit = crown.fit_crown(case["fdi"], margin, axis, mesial if mesial is not None else true_mesial, prep_top,
                              meshes.get("mesial"), meshes.get("distal"), ant_mesh)
    except crown.CrownError as exc:
        out.update(status="error", message=str(exc), seconds=time.perf_counter() - start)
        return out
    out["seconds"] = time.perf_counter() - start
    out["status"] = "kurva"
    out["iterations"] = fit.iterations
    out["hints"] = len(fit.hints)
    v_die = fit.surface.mesh.vertices @ R  # frame die
    p = crown.CrownParams()
    for name, ellipsoid in neighbors.items():
        out[f"{name}_err_um"] = 1000 * (float(ellipsoid.signed_distance(v_die).min()) - p.approximal_distance_mm)
    if antagonist is not None:
        out["antagonist_err_um"] = 1000 * (float(antagonist.signed_distance(v_die).min()) - p.occlusal_distance_mm)
    bottom = fit.surface.frame.to_world(fit.surface.local[:, 0, :])
    out["cervical_um"] = 1000 * float(synthetic.distance_to_polyline(bottom, margin).max())
    out["flipped"] = crown.flipped_faces(fit.surface)
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--set", choices=sorted(SETS), default="tuning")
    parser.add_argument("--seeds", type=int, default=3)
    parser.add_argument("--json", type=Path)
    args = parser.parse_args(argv)
    rows = []
    for name, case in SETS[args.set].items():
        for finish in synthetic.FINISHES:
            for noise in NOISE_UM:
                runs = [run_case(case, finish, noise, seed) for seed in range(args.seeds)]
                rows.append({"case": name, "finish": finish, "noise_um": noise, "runs": runs})

    def worst_abs(runs, key):
        vals = [abs(r[key]) for r in runs if r.get(key) is not None]
        return f"{max(vals):.1f} um" if vals else "-"

    print(f"Set: {args.set}. Nilai = terburuk dari {args.seeds} seed. Target: approximal -20 um, oklusal 0 um "
          "(Nagata 2025, literatur, perlu kalibrasi).\n")
    print("| Kasus | Finish | Derau | Hasil per seed | |galat| kontak mesial | |galat| kontak distal | "
          "|galat| jarak oklusal | Galat arah mesial | Tepi servikal ke margin | Lipatan | Iterasi | Waktu |")
    print("|---|---|---|---|---|---|---|---|---|---|---|---|")
    for r in rows:
        runs = r["runs"]
        outcome = {}
        for x in runs:
            outcome[x["status"]] = outcome.get(x["status"], 0) + 1
        ok_runs = [x for x in runs if x["status"] == "kurva"]
        mes = [x["mesial_error_deg"] for x in runs if x["mesial_error_deg"] is not None]
        cells = [", ".join(f"{k} {v}" for k, v in sorted(outcome.items())),
                 worst_abs(ok_runs, "mesial_err_um"), worst_abs(ok_runs, "distal_err_um"),
                 worst_abs(ok_runs, "antagonist_err_um"),
                 f"{max(mes):.2f} deg" if mes else "- (dari pengguna)",
                 f"{max(x['cervical_um'] for x in ok_runs):.3f} um" if ok_runs else "-",
                 str(max(x["flipped"] for x in ok_runs)) if ok_runs else "-",
                 str(max(x["iterations"] for x in ok_runs)) if ok_runs else "-",
                 f"{max(x['seconds'] for x in runs):.1f} s"]
        print(f"| {r['case']} | {r['finish']} | {r['noise_um']} um | " + " | ".join(cells) + " |")
    all_runs = [x for r in rows for x in r["runs"]]
    expected = [x for x in all_runs if x["expect_error"]]
    unexpected = [x for x in all_runs if not x["expect_error"] and x["status"] == "error"]
    print(f"\nKasus sempit yang berakhir dengan error eksplisit: {sum(x['status'] == 'error' for x in expected)} "
          f"dari {len(expected)}; error di kasus yang seharusnya bisa: {len(unexpected)}")
    for x in unexpected[:5]:
        print("  error tak terduga:", x["message"])
    if args.json:
        args.json.write_text(json.dumps(rows, indent=2, default=float), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
