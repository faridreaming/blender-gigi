# SPDX-License-Identifier: GPL-3.0-or-later
"""Benchmark proposal crown langkah 1 sampai 5 terhadap gigi tetangga dan antagonis sintetis (PHASE2.md §5.4).

    python scripts/crown_benchmark.py --set tuning     # dipakai saat menyetel (iterasi, zona campur margin)
    python scripts/crown_benchmark.py --set ukur       # dikunci bersama kode sebelum dijalankan, lalu sekali
    python scripts/crown_benchmark.py --seeds 1 --json hasil.json

Margin analitis dan sumbu sebenarnya (galat §5.1 dan §5.2 tidak tercampur). Mesh tetangga dan antagonis memakai
generator die (jitter, derau, rotasi die); jawaban benar dari bentuk analitis:
- jarak kontak: jarak bertanda EKSAK dari vertex crown ke elipsoid tetangga (bisection Eberly) dan ke bidang atau
  silinder antagonis, dibanding target (approximal -20 um, oklusal 0 um, Nagata 2025);
- arah mesial: sudut antara arah mesial dari tetangga dan sumbu mesial die yang diketahui;
- tepi servikal: jarak cincin dalam border ke margin yang dipakai (0 menurut konstruksi);
- border IVO: lebar horizontal, panjang bagian bersudut, dan sudutnya terhadap sumbu di 64 potongan;
- solid: manifold3d (watertight, satu komponen, genus 0, tanpa rongga), dari spacer §5.3 preset (block-out lalu
  cement gap, 5 axis); penetrasi strip ke die analitis (mesh rapat zona finish, bukan mesh die berderau);
- lipatan: face yang berbalik dibanding template murni berdasar rata; "non-sliver" tanpa segitiga dengan tinggi
  < 0,01 mm (SLIVER_MM, sama dengan §5.3);
- sudut emergence: sudut permukaan luar terhadap sumbu insersi pada 1 mm pertama di atas ujung border, per sudut
  keliling. Kolom median = median per seed yang terburuk. Kriteria set ukur ketiga: median <= 21 derajat untuk
  anterior dan premolar (rentang Monaco 2026); molar hanya dilaporkan;
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

from scripts import bench_runner  # noqa: E402

from core import crown, insertion, material_db, spacer, synthetic  # noqa: E402
from core.template import fdi_kind  # noqa: E402

NOISE_UM = (0, 10, 30)
EMERGENCE_MEDIAN_MAX_DEG = 21.0  # ambang sementara anterior dan premolar (PHASE2.md §5.4); molar hanya dilaporkan
PRESET = material_db.load_material_preset(ROOT / "data" / "materials" / "zircad_prime.json")
ELLIPSOID = np.array([4.0, 4.5, 3.5])


def _rot(axis: str, deg: float) -> np.ndarray:
    c, s = np.cos(np.radians(deg)), np.sin(np.radians(deg))
    if axis == "y":
        return np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]])
    return np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]])


# Kasus: die, FDI, tetangga (celah dari tepi margin + tonjolan kontur ke permukaan dalam elipsoid, mm; None = tanpa),
# kemiringan tetangga, antagonis (jenis, jarak dari puncak preparasi, kemiringan), dan apakah error diharapkan.
# Scallop ditulis sebagai puncak-lembah PL = 2 x scallop_mm. Aturan CLAUDE.md: set tuning wajib berisi scallop dalam
# (PL 2,5 dan 3,5 mm) dan die anterior (ditegakkan tests/core/test_repo_rules.py).
TUNING = {
    "molar, tetangga simetris, antagonis datar": dict(die={}, fdi=46, gaps=(0.6, 0.6), ant=("plane", 3.6, 0.0)),
    "molar scallop PL 2, tetangga asimetris": dict(die={"scallop_mm": 1.0}, fdi=26, gaps=(1.2, 0.3), ant=("plane", 3.8, 0.0)),
    "molar, antagonis terlalu dekat (error)": dict(die={}, fdi=46, gaps=(0.6, 0.6), ant=("plane", 2.5, 0.0), expect_error=True),
    "molar, tetangga terlalu dekat (error)": dict(die={}, fdi=46, gaps=(-1.6, -1.6), ant=("plane", 3.6, 0.0), expect_error=True),
    # Set ukur pertama (commit 931ae46, dijalankan sekali) menjadi bagian set tuning sejak perbaikan lipatan.
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
    # Scallop dalam PL 2,5 dan 3,5 mm (lengkungan CEJ GLC, §5.1) dan die anterior, ditambahkan bersama perbaikan.
    "lateral atas PL 2,5, tetangga dua sisi": dict(die=dict(radius_x_mm=3.2, radius_y_mm=2.9, prep_height_mm=5.0,
                                                             taper_deg=6.0, finish_width_mm=0.7, scallop_mm=1.25),
                                                    fdi=12, gaps=(0.5, 0.5), ant=("plane", 2.6, 12.0)),
    "insisif bawah PL 3,5, antagonis miring": dict(die=dict(radius_x_mm=2.8, radius_y_mm=3.0, prep_height_mm=5.0,
                                                             taper_deg=6.0, finish_width_mm=0.7, scallop_mm=1.75),
                                                    fdi=41, gaps=(0.4, 0.4), ant=("plane", 2.6, 10.0)),
    "molar PL 3,5, antagonis datar": dict(die=dict(prep_height_mm=5.5, scallop_mm=1.75), fdi=36, gaps=(0.6, 0.6),
                                           ant=("plane", 3.6, 0.0)),
    # Set ukur kedua (commit f633091, dijalankan sekali) menjadi bagian set tuning sejak sudut emergence (Monaco).
    "lateral atas PL 3,4, antagonis miring 15": dict(die=dict(radius_x_mm=3.0, radius_y_mm=2.7, prep_height_mm=5.2,
                                                               taper_deg=7.0, finish_width_mm=0.7, scallop_mm=1.7),
                                                      fdi=22, gaps=(0.5, 0.7), ant=("plane", 2.8, 15.0)),
    "kaninus bawah PL 3,0, antagonis silinder": dict(die=dict(radius_x_mm=3.5, radius_y_mm=3.9, prep_height_mm=6.0,
                                                               taper_deg=6.0, scallop_mm=1.5),
                                                      fdi=43, gaps=(0.6, 0.4), ant=("cylinder", 3.0, 0.0)),
    "insisif sentral bawah PL 2,6, tanpa antagonis": dict(die=dict(radius_x_mm=2.6, radius_y_mm=2.9, prep_height_mm=4.6,
                                                                    taper_deg=5.0, finish_width_mm=0.6, scallop_mm=1.3),
                                                           fdi=31, gaps=(0.4, 0.4), ant=None),
    "premolar PL 2,8, tetangga miring 10": dict(die=dict(radius_x_mm=4.0, radius_y_mm=3.6, prep_height_mm=5.0,
                                                          taper_deg=8.0, scallop_mm=1.4),
                                                 fdi=34, gaps=(0.5, 0.6), tilt=10.0, ant=("plane", 3.2, 6.0)),
    "molar PL 3,8, hanya tetangga distal": dict(die=dict(radius_x_mm=5.4, radius_y_mm=4.8, prep_height_mm=6.0,
                                                          taper_deg=9.0, scallop_mm=1.9),
                                                 fdi=47, gaps=(None, 0.6), ant=("plane", 3.6, 0.0)),
    "insisif PL 3,2, tetangga terlalu dekat (error)": dict(die=dict(radius_x_mm=3.6, radius_y_mm=3.2, prep_height_mm=5.5,
                                                                     taper_deg=8.0, finish_width_mm=0.8, scallop_mm=1.6),
                                                            fdi=21, gaps=(-1.4, -1.4), ant=("plane", 2.8, 10.0),
                                                            expect_error=True),
    # Set ukur ketiga (commit 76aed0e, dijalankan sekali) menjadi bagian set tuning sejak border dan solid.
    "kaninus atas PL 2,6, antagonis miring 10": dict(die=dict(radius_x_mm=3.6, radius_y_mm=4.2, prep_height_mm=6.2,
                                                               taper_deg=7.0, scallop_mm=1.3),
                                                      fdi=23, gaps=(0.5, 0.5), ant=("plane", 3.0, 10.0)),
    "lateral bawah PL 3,0, tanpa tetangga": dict(die=dict(radius_x_mm=2.5, radius_y_mm=2.8, prep_height_mm=4.8,
                                                           taper_deg=6.0, finish_width_mm=0.6, scallop_mm=1.5),
                                                  fdi=42, gaps=(None, None), ant=("plane", 2.4, 8.0)),
    "insisif sentral atas PL 3,6, tetangga asimetris": dict(die=dict(radius_x_mm=3.8, radius_y_mm=3.3,
                                                                      prep_height_mm=5.8, taper_deg=7.0,
                                                                      finish_width_mm=0.8, scallop_mm=1.8),
                                                             fdi=21, gaps=(0.9, 0.3), ant=("plane", 2.8, 14.0)),
    "premolar atas PL 2,2, antagonis silinder": dict(die=dict(radius_x_mm=4.2, radius_y_mm=3.8, prep_height_mm=5.2,
                                                               taper_deg=6.0, scallop_mm=1.1),
                                                      fdi=14, gaps=(0.6, 0.6), ant=("cylinder", 3.3, 0.0)),
    "premolar bawah PL 3,0, hanya tetangga mesial": dict(die=dict(radius_x_mm=3.9, radius_y_mm=3.7, prep_height_mm=4.6,
                                                                   taper_deg=9.0, scallop_mm=1.5),
                                                          fdi=45, gaps=(0.5, None), ant=("plane", 3.0, 4.0)),
    "molar atas PL 3,2, antagonis miring 6": dict(die=dict(radius_x_mm=5.6, radius_y_mm=5.2, prep_height_mm=5.6,
                                                            taper_deg=8.0, scallop_mm=1.6),
                                                   fdi=16, gaps=(0.7, 0.5), ant=("plane", 3.8, 6.0)),
    "premolar PL 2,4, antagonis terlalu dekat (error)": dict(die=dict(radius_x_mm=4.0, radius_y_mm=3.6,
                                                                       prep_height_mm=4.5, taper_deg=7.0,
                                                                       scallop_mm=1.2),
                                                              fdi=35, gaps=(0.5, 0.5), ant=("plane", 1.9, 0.0),
                                                              expect_error=True),
}
# Set ukur keempat: didefinisikan dan dikunci bersama kode SEBELUM dijalankan, lalu dijalankan sekali. Kriteria: solid
# valid (watertight, satu komponen, genus 0, tanpa rongga) di semua kasus yang seharusnya bisa, border sesuai IVO di 64
# potongan, median emergence <= 21 derajat untuk anterior dan premolar (ambang sementara; molar dilaporkan), dan error
# eksplisit di kasus sempit. Wajib berisi anterior dengan scallop dalam.
UKUR = {
    "insisif sentral atas PL 3,6, hanya tetangga distal": dict(die=dict(radius_x_mm=3.7, radius_y_mm=3.2,
                                                                         prep_height_mm=5.6, taper_deg=7.0,
                                                                         finish_width_mm=0.8, scallop_mm=1.8),
                                                                fdi=11, gaps=(None, 0.5), ant=("plane", 2.9, 13.0)),
    "lateral bawah PL 3,2, tetangga dua sisi": dict(die=dict(radius_x_mm=2.6, radius_y_mm=2.9, prep_height_mm=4.9,
                                                              taper_deg=6.0, finish_width_mm=0.6, scallop_mm=1.6),
                                                     fdi=32, gaps=(0.4, 0.5), ant=("plane", 2.5, 9.0)),
    "kaninus atas PL 3,4, tanpa tetangga": dict(die=dict(radius_x_mm=3.5, radius_y_mm=4.1, prep_height_mm=6.3,
                                                          taper_deg=6.0, scallop_mm=1.7),
                                                 fdi=13, gaps=(None, None), ant=("cylinder", 3.1, 0.0)),
    "premolar bawah PL 2,4, antagonis miring 8": dict(die=dict(radius_x_mm=3.9, radius_y_mm=3.6, prep_height_mm=4.7,
                                                                taper_deg=8.0, scallop_mm=1.2),
                                                       fdi=44, gaps=(0.6, 0.5), ant=("plane", 3.1, 8.0)),
    "molar bawah PL 2,8, tetangga miring 12": dict(die=dict(radius_x_mm=5.5, radius_y_mm=5.0, prep_height_mm=5.4,
                                                             taper_deg=9.0, scallop_mm=1.4),
                                                    fdi=37, gaps=(0.6, 0.7), tilt=12.0, ant=("plane", 3.7, 4.0)),
    "lateral PL 3,0, tetangga terlalu dekat (error)": dict(die=dict(radius_x_mm=3.0, radius_y_mm=2.8, prep_height_mm=5.0,
                                                                     taper_deg=6.0, finish_width_mm=0.7, scallop_mm=1.5),
                                                            fdi=22, gaps=(-1.6, -1.6), ant=("plane", 2.8, 10.0),
                                                            expect_error=True),
}
SETS = {"tuning": TUNING, "ukur": UKUR}


def build_case(case: dict, finish: str, noise_um: int, seed: int):
    spec = synthetic.DieSpec(finish=finish, **case["die"])
    die = synthetic.make_die(spec, noise_sigma_mm=noise_um / 1000.0, rotate=True, seed=seed)
    R = die.rotation
    margin_die = synthetic.margin_points(spec, np.linspace(0, 2 * np.pi, 1024, endpoint=False))
    center_z = float(margin_die[:, 2].mean())
    prep_top = spec.top_z + spec.roof_height_mm - center_z
    z_k = center_z + 0.4 * spec.prep_height_mm
    bulge = synthetic.NEIGHBOUR_CONTOUR_ALLOWANCE_MM
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


def finish_zone_truth(spec: synthetic.DieSpec, rotation: np.ndarray, n_theta: int = 1440, n_t: int = 120):
    """Mesh analitis rapat zona finish die (t 0,9 sampai 2,0: sedikit akar, margin, seluruh finish) dan normal luar
    analitis per face, untuk mengukur penetrasi strip ke die sebenarnya. Mesh die berderau tidak dipakai: titik margin
    analitis bisa sampai 0,1 mm di luar mesh die, karena mesh memotong sudut garis finish dengan tali busur."""
    theta = np.linspace(0, 2 * np.pi, n_theta, endpoint=False)
    t_grid = np.linspace(0.9, 2.0, n_t)
    points = synthetic.surface_points(spec, theta[:, None], t_grid[None, :]) @ rotation.T
    mesh = synthetic._grid_mesh(points, wrap_u=True)
    faces = np.asarray(mesh.faces)
    i_face, j_face = np.divmod(faces[:, 0], n_t)
    normals = synthetic.surface_normals(spec, theta[i_face] + np.pi / n_theta, t_grid[j_face] + 0.5 * (t_grid[1] - t_grid[0]))
    return mesh, normals @ rotation.T


def strip_penetration_um(solid, truth_mesh, truth_normals) -> float:
    """Penetrasi terdalam titik strip (titik berat dan tengah edge) ke die analitis, um (0 = tidak masuk)."""
    from core.geometry import MeshProjector

    corners = solid.mesh.vertices[solid.mesh.faces[solid.strip_faces]]
    samples = np.concatenate([corners.mean(axis=1)] + [0.5 * (corners[:, k] + corners[:, (k + 1) % 3])
                                                       for k in range(3)])
    closest, face, _ = MeshProjector(truth_mesh).closest(samples)
    signed = np.einsum("ij,ij->i", samples - closest, truth_normals[face])
    return 1000 * float(max(0.0, -signed.min()))


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
    # Spacer dari preset (§5.3): block-out lalu cement gap, milling 5 axis (tanpa block-out kedua).
    ctx = insertion.insertion_context(die.mesh, margin)
    blocked = insertion.block_out(ctx, axis, PRESET.value("blockout_free_zone_mm"))
    faces = spacer.inner_faces(ctx.vertices, ctx.faces, ctx.region.faces, ctx.region.band_faces, ctx.margin)
    inner = spacer.spacer_surface(blocked.mesh, faces, ctx.margin, axis, spacer.SpacerParams.from_preset(PRESET),
                                  ctx.noise_sigma_mm).mesh
    params = crown.CrownParams()
    start = time.perf_counter()
    try:
        fit = crown.fit_crown(case["fdi"], margin, axis, mesial if mesial is not None else true_mesial, prep_top,
                              meshes.get("mesial"), meshes.get("distal"), ant_mesh, params)
    except crown.CrownError as exc:
        out.update(status="error", message=str(exc), seconds=time.perf_counter() - start)
        return out
    out["seconds_fit"] = time.perf_counter() - start
    out["iterations"] = fit.iterations
    out["hints"] = len(fit.hints)
    v_die = fit.surface.mesh.vertices @ R  # frame die
    for name, ellipsoid in neighbors.items():
        out[f"{name}_err_um"] = 1000 * (float(ellipsoid.signed_distance(v_die).min()) - params.approximal_distance_mm)
    if antagonist is not None:
        out["antagonist_err_um"] = 1000 * (float(antagonist.signed_distance(v_die).min()) - params.occlusal_distance_mm)
    s = fit.surface
    out["cervical_um"] = 1000 * float(synthetic.distance_to_polyline(s.frame.to_world(s.border[0]), margin).max())
    out["flipped"] = crown.flipped_faces(s)
    out["folds"] = crown.non_sliver_folds(s)
    out["emergence_deg"] = [float(a) for a in crown.emergence_angles(s)]
    out["emergence_median_deg"] = float(np.median(out["emergence_deg"]))
    sections = crown.border_sections(s.border, 64)
    out["border_horizontal_err_um"] = 1000 * float(np.abs(sections["horizontal_mm"] - params.border_horizontal_mm).max())
    out["border_rise_um"] = 1000 * float(sections["horizontal_rise_mm"].max())
    out["border_angled_err_um"] = 1000 * float(np.abs(sections["angled_mm"] - params.border_angled_mm).max())
    out["border_angle_err_deg"] = float(np.abs(sections["angle_deg"] - params.border_angle_deg).max())
    start = time.perf_counter()
    try:
        solid = crown.assemble_crown(s, inner, params)
    except crown.CrownError as exc:
        out.update(status="error", message="solid: " + str(exc), seconds=out["seconds_fit"] + time.perf_counter() - start)
        return out
    out["seconds_solid"] = time.perf_counter() - start
    out["seconds"] = out["seconds_fit"] + out["seconds_solid"]
    out["status"] = "solid"
    out["genus"], out["components"], out["voids"] = solid.genus, solid.components, solid.sealed_voids
    out["volume_mm3"] = solid.volume_mm3
    out["strip_delta_mm"] = solid.strip_delta_mm
    out["strip_width_mm"] = solid.strip_width_max_mm
    out["holes_filled"] = solid.holes_filled
    truth_mesh, truth_normals = finish_zone_truth(spec, R)
    out["strip_penetration_um"] = strip_penetration_um(solid, truth_mesh, truth_normals)
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
    with bench_runner.CaseRunner(args.timeout, total, lambda r: r["status"]) as runner:
        for name, case in SETS[args.set].items():
            def on_timeout(message, seconds, case=case):
                return {"status": "timeout", "message": message, "seconds": seconds, "mesial_error_deg": None,
                        "expect_error": bool(case.get("expect_error", False))}

            for finish in synthetic.FINISHES:
                for noise in NOISE_UM:
                    runs = [runner.run(f"{name} | {finish} | {noise} um | seed {seed}", run_case,
                                       (case, finish, noise, seed), on_timeout) for seed in range(args.seeds)]
                    rows.append({"case": name, "finish": finish, "noise_um": noise, "runs": runs})

    def worst(runs, key, fmt):
        vals = [abs(r[key]) for r in runs if r.get(key) is not None]
        return fmt.format(max(vals)) if vals else "-"

    print(f"Set: {args.set}. Nilai = terburuk dari {args.seeds} seed. Target: approximal -20 um, oklusal 0 um "
          "(Nagata 2025, literatur, perlu kalibrasi). Border IVO 0,20 mm / 0,10 mm / 65 deg, diukur di 64 potongan.\n")
    print("| Kasus | Finish | Derau | Hasil per seed | |galat| kontak mesial | |galat| kontak distal | "
          "|galat| jarak oklusal | Emergence median | Emergence maks | "
          f"Median <= {EMERGENCE_MEDIAN_MAX_DEG:g} deg | Border: galat horizontal / bersudut / sudut | "
          "Solid (genus, komponen, rongga) | Delta strip | Penetrasi strip ke die | Iterasi | Waktu proposal + solid |")
    print("|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|")
    for r in rows:
        runs = r["runs"]
        outcome = {}
        for x in runs:
            outcome[x["status"]] = outcome.get(x["status"], 0) + 1
        ok_runs = [x for x in runs if x["status"] == "solid"]
        medians = [x["emergence_median_deg"] for x in ok_runs]
        molar = fdi_kind(SETS[args.set][r["case"]]["fdi"]) == "molar"
        if not medians:
            verdict = "-"
        elif molar:
            verdict = "- (molar, dilaporkan)"
        else:
            verdict = "ya" if max(medians) <= EMERGENCE_MEDIAN_MAX_DEG else "TIDAK"
        r["emergence_ok"] = verdict
        cells = [", ".join(f"{k} {v}" for k, v in sorted(outcome.items())),
                 worst(ok_runs, "mesial_err_um", "{:.1f} um"), worst(ok_runs, "distal_err_um", "{:.1f} um"),
                 worst(ok_runs, "antagonist_err_um", "{:.1f} um"),
                 f"{max(medians):.1f} deg" if ok_runs else "-",
                 f"{max(a for x in ok_runs for a in x['emergence_deg']):.1f} deg" if ok_runs else "-",
                 verdict,
                 (worst(ok_runs, "border_horizontal_err_um", "{:.3f} um") + " / "
                  + worst(ok_runs, "border_angled_err_um", "{:.3f} um") + " / "
                  + worst(ok_runs, "border_angle_err_deg", "{:.3f} deg")) if ok_runs else "-",
                 (f"{max(x['genus'] for x in ok_runs)}, {max(x['components'] for x in ok_runs)}, "
                  f"{max(x['voids'] for x in ok_runs)}") if ok_runs else "-",
                 worst(ok_runs, "strip_delta_mm", "{:.2f} mm"),
                 worst(ok_runs, "strip_penetration_um", "{:.1f} um"),
                 str(max(x["iterations"] for x in ok_runs)) if ok_runs else "-",
                 (f"{max(x['seconds_fit'] for x in ok_runs):.1f} + {max(x['seconds_solid'] for x in ok_runs):.1f} s"
                  if ok_runs else f"{max(x['seconds'] for x in runs):.1f} s")]
        print(f"| {r['case']} | {r['finish']} | {r['noise_um']} um | " + " | ".join(cells) + " |")
    all_runs = [x for r in rows for x in r["runs"]]
    expected = [x for x in all_runs if x["expect_error"]]
    unexpected = [x for x in all_runs if not x["expect_error"] and x["status"] in ("error", "timeout")]
    print(f"\nKasus sempit yang berakhir dengan error eksplisit: {sum(x['status'] == 'error' for x in expected)} "
          f"dari {len(expected)}; error di kasus yang seharusnya bisa: {len(unexpected)}")
    for x in unexpected[:8]:
        print("  error tak terduga:", x["message"])
    solids = [x for x in all_runs if x["status"] == "solid"]
    print(f"Solid valid (manifold3d: watertight, 1 komponen, genus 0, tanpa rongga): {len(solids)} dari "
          f"{len(all_runs) - len(expected)} kasus yang seharusnya bisa")
    if solids:
        print(f"Lipatan non-sliver permukaan luar: {sum(x['folds'] > 0 for x in solids)} solid; tepi servikal ke margin "
              f"maks {max(x['cervical_um'] for x in solids):.3f} um; galat arah mesial maks "
              f"{max((x['mesial_error_deg'] for x in solids if x['mesial_error_deg'] is not None), default=0):.3f} deg; "
              f"lubang spacer yang ditutup: {sum(x['holes_filled'] for x in solids)}")
    judged = [r for r in rows if r["emergence_ok"] in ("ya", "TIDAK")]
    print(f"Baris anterior/premolar dengan median emergence <= {EMERGENCE_MEDIAN_MAX_DEG:g} deg di semua seed: "
          f"{sum(r['emergence_ok'] == 'ya' for r in judged)} dari {len(judged)}")
    print(f"Kasus melewati batas waktu {args.timeout:g} s: {runner.timeouts}")
    if args.json:
        args.json.write_text(json.dumps(rows, indent=2, default=float), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
