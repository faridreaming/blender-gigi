# SPDX-License-Identifier: GPL-3.0-or-later
"""Uji integrasi di dalam Blender (Lapis 2). Dijalankan oleh scripts/run_blender_tests.py:

    blender --background --python-exit-code 1 --python tests/blender/run_integration.py -- \\
        tests/golden [--private tests/golden_private]

Extension harus sudah terinstal dan aktif (dari zip hasil build), supaya yang dites adalah paket
yang sama dengan yang dirilis, termasuk wheel-nya. Folder golden publik wajib berisi case; folder
privat (scan asli, tidak di-commit) boleh kosong atau tidak ada dan kalau begitu dilewati.
Exit code 1 kalau ada yang gagal.
"""

import hashlib
import importlib
import json
import sys
import tempfile
import time
from pathlib import Path

import addon_utils
import bpy

PERF_TRIANGLES_MIN = 1_000_000
PERF_MAX_SECONDS = 5.0


def find_extension() -> str:
    for mod in addon_utils.modules():
        if mod.__name__.startswith("bl_ext.") and mod.__name__.endswith(".dentalcad"):
            name = mod.__name__
            if not addon_utils.check(name)[1]:
                addon_utils.enable(name, default_set=True)
            return name
    raise RuntimeError("extension dentalcad tidak terinstal (bl_ext.*.dentalcad tidak ditemukan)")


def clear_scene() -> None:
    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj)
    for mesh in list(bpy.data.meshes):
        bpy.data.meshes.remove(mesh)


def import_file(path: Path) -> tuple[bpy.types.Object, float]:
    op = bpy.ops.dentalcad.import_ply if path.suffix.lower() == ".ply" else bpy.ops.dentalcad.import_stl
    start = time.perf_counter()
    result = op(filepath=str(path))
    seconds = time.perf_counter() - start
    if result != {"FINISHED"}:
        raise RuntimeError(f"operator mengembalikan {result}")
    return bpy.context.view_layer.objects.active, seconds


class Runner:
    def __init__(self, package: str):
        self.validate = importlib.import_module(f"{package}.core.mesh_validate")
        self.bridge = importlib.import_module(f"{package}.ops.mesh_bridge")
        self.failures: list[str] = []

    def check(self, label: str, problems: list[str]) -> None:
        status = "OK  " if not problems else "GAGAL"
        print(f"[{status}] {label}")
        for problem in problems:
            print(f"         {problem}")
            self.failures.append(f"{label}: {problem}")

    def golden_case(self, case: Path) -> None:
        expected = json.loads((case / "expected.json").read_text(encoding="utf-8"))
        clear_scene()
        try:
            obj, seconds = import_file(case / expected["input"])
        except Exception as exc:
            self.check(case.name, [f"impor gagal: {exc}"])
            return
        data = self.bridge.from_blender_mesh(obj.data)
        problems = self.validate.compare_to_expected(self.validate.summarize(data), expected)
        if seconds > expected["max_import_seconds"]:
            problems.append(f"impor {seconds:.2f} s melebihi {expected['max_import_seconds']} s")
        if data.has_vertex_colors != expected.get("vertex_colors", False):
            problems.append(f"vertex color: didapat {data.has_vertex_colors}")
        if "mean_rgba" in expected and data.has_vertex_colors:
            mean = data.vertex_colors.mean(axis=0)
            if max(abs(a - b) for a, b in zip(mean, expected["mean_rgba"])) > 0.5:
                problems.append(f"rata-rata warna {mean.tolist()} != {expected['mean_rgba']}")
        self.check(f"{case.name} ({len(data.faces):,} segitiga, {seconds:.2f} s)", problems)

    def performance(self) -> None:
        import trimesh  # dari wheel yang dibundel extension

        mesh = trimesh.creation.icosphere(subdivisions=8, radius=10.0)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "perf.stl"
            mesh.export(path)
            clear_scene()
            obj, seconds = import_file(path)
            count = len(obj.data.polygons)
        problems = []
        if count < PERF_TRIANGLES_MIN:
            problems.append(f"hanya {count:,} segitiga")
        if seconds > PERF_MAX_SECONDS:
            problems.append(f"impor {seconds:.2f} s melebihi {PERF_MAX_SECONDS} s")
        self.check(f"performa impor STL ({count:,} segitiga, {seconds:.2f} s)", problems)

    def bundled_wheels(self) -> None:
        problems = []
        try:
            import manifold3d
            import trimesh

            import numpy
            import scipy
            from scipy.sparse import identity
            from scipy.spatial import cKDTree

            volume = manifold3d.Manifold.cube((2.0, 2.0, 2.0)).volume()
            if abs(volume - 8.0) > 1e-9:
                problems.append(f"volume kubus manifold3d {volume} != 8")
            points = numpy.array([[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [0.0, 2.0, 0.0]])
            distance, index = cKDTree(points).query([0.9, 0.1, 0.0])
            if index != 1 or abs(distance - numpy.hypot(0.1, 0.1)) > 1e-12:
                problems.append(f"cKDTree salah: indeks {index}, jarak {distance}")
            if identity(3, format="csr").sum() != 3:
                problems.append("scipy.sparse salah")
            if scipy.__version__ != "1.18.1":
                problems.append(f"scipy {scipy.__version__}, diharapkan 1.18.1")
            if "extensions" not in Path(scipy.__file__).parts:
                problems.append(f"scipy dimuat dari luar extension: {scipy.__file__}")
            print(f"         trimesh {trimesh.__version__}, scipy {scipy.__version__}, "
                  f"manifold3d dari {Path(manifold3d.__file__).parent}")
        except Exception as exc:
            problems.append(f"{type(exc).__name__}: {exc}")
        self.check("wheel trimesh + manifold3d + scipy termuat", problems)

    def coupons(self, package: str) -> None:
        """Operator kupon kalibrasi: file STL, lembar ukur, laporan, dan objek pratinjau."""
        mesh_io = importlib.import_module(f"{package}.core.mesh_io")
        coupons_mod = importlib.import_module(f"{package}.ops.coupons")
        presets = coupons_mod.load_presets()
        problems = []
        if set(presets) != {"photon_p1_std_v2_hd_gray", "accufab_f1_std_v2_hd_gray"}:
            problems.append(f"preset terbundel tidak sesuai: {sorted(presets)}")

        clear_scene()
        preset_id = "photon_p1_std_v2_hd_gray"
        with tempfile.TemporaryDirectory() as tmp:
            start = time.perf_counter()
            result = bpy.ops.dentalcad.export_coupons(directory=tmp, preset=preset_id, add_to_scene=True)
            seconds = time.perf_counter() - start
            out = Path(tmp) / preset_id
            if result != {"FINISHED"}:
                problems.append(f"operator mengembalikan {result}")
            else:
                report = json.loads((out / "kupon_laporan.json").read_text(encoding="utf-8"))
                parts = report["parts"]
                if len(parts) != 12:
                    problems.append(f"{len(parts)} STL, diharapkan 12")
                for entry in parts:
                    path = out / entry["file"]
                    mesh = mesh_io.load_mesh(path)
                    if not self.validate.is_watertight(mesh):
                        problems.append(f"{entry['file']} tidak watertight")
                    if hashlib.sha256(path.read_bytes()).hexdigest() != entry["sha256"]:
                        problems.append(f"{entry['file']} SHA-256 tidak cocok dengan laporan")
                    if "die" in entry["file"] and "support" not in entry["print_note"]:
                        problems.append(f"{entry['file']} tanpa catatan support")
                rows = (out / "kupon_lembar_ukur.csv").read_text(encoding="utf-8").strip().splitlines()
                if len(rows) != 23:
                    problems.append(f"lembar ukur {len(rows) - 1} baris, diharapkan 22")
                if not any("die_clearance" in w for w in report["warnings"]):
                    problems.append("peringatan die_clearance belum dikalibrasi tidak ada di laporan")
                collection = bpy.data.collections.get(coupons_mod.COLLECTION_NAME)
                count = len(collection.objects) if collection else 0
                if count != 12:
                    problems.append(f"{count} objek pratinjau di scene, diharapkan 12")
        self.check(f"kupon kalibrasi ({preset_id}, {seconds:.2f} s)", problems)

    def margin(self, package: str) -> None:
        """Operator margin: deteksi dari titik klik (koordinat dunia), lalu edit (hapus + geser) dan update."""
        import numpy as np
        from mathutils import Matrix, Vector

        synthetic = importlib.import_module(f"{package}.core.synthetic")
        core_margin = importlib.import_module(f"{package}.core.margin")
        ops_margin = importlib.import_module(f"{package}.ops.margin")
        geometry = importlib.import_module(f"{package}.core.geometry")
        problems = []

        clear_scene()
        for curve in list(bpy.data.curves):
            bpy.data.curves.remove(curve)
        die = synthetic.make_die(synthetic.DieSpec(finish="chamfer", scallop_mm=1.0), noise_sigma_mm=0.01, seed=3)
        obj = bpy.data.objects.new("die", self.bridge.to_blender_mesh("die", die.mesh))
        bpy.context.collection.objects.link(obj)
        obj.matrix_world = Matrix.Translation((5.0, -3.0, 2.0)) @ Matrix.Rotation(0.4, 4, "X")
        bpy.context.view_layer.objects.active = obj

        seed_local = synthetic.margin_points(die.spec, np.array([1.3]))[0] @ die.rotation.T
        seed_world = obj.matrix_world @ Vector(seed_local)
        start = time.perf_counter()
        result = bpy.ops.dentalcad.margin_detect(use_seed=True, seed_point=seed_world)
        seconds = time.perf_counter() - start
        controls = bpy.data.objects.get("die Margin")
        preview = bpy.data.objects.get("die Margin Preview")
        if result != {"FINISHED"} or controls is None or preview is None:
            self.check("margin: deteksi", [f"operator {result}, kurva {controls}, pratinjau {preview}"])
            return

        points = ops_margin._spline_points(controls.data)
        projector = geometry.MeshProjector(die.mesh)
        curve = core_margin.MarginCurve(points, projector)
        dev = core_margin.margin_deviation(curve.sample(1024), die.margin_curve(4096))
        if dev["median"] > 0.050 or dev["coverage_p95"] > 0.15:
            problems.append(f"deviasi median {1000 * dev['median']:.1f} um, cakupan p95 {1000 * dev['coverage_p95']:.1f} um")
        if len(preview.data.splines[0].points) != ops_margin.PREVIEW_SAMPLES:
            problems.append("kurva pratinjau tidak punya jumlah sampel yang diharapkan")
        self.check(f"margin: deteksi (median {1000 * dev['median']:.1f} um, {seconds:.2f} s)", problems)

        # Edit seperti pengguna di Edit Mode: hapus titik 2, geser titik 5 sejauh 0,3 mm.
        problems = []
        edited = np.delete(points, 2, axis=0)
        edited[4] = edited[4] + np.array([0.3, 0.0, 0.0])
        ops_margin._set_poly(controls.data, edited)
        bpy.context.view_layer.objects.active = controls
        result = bpy.ops.dentalcad.margin_update()
        after = ops_margin._spline_points(controls.data)
        if result != {"FINISHED"}:
            problems.append(f"update mengembalikan {result}")
        if len(after) != len(points) - 1:
            problems.append(f"{len(after)} titik setelah hapus, diharapkan {len(points) - 1}")
        _, _, dist = projector.closest(after[4:5])
        if dist[0] > 1e-6:
            problems.append(f"titik yang digeser {dist[0]:.4f} mm dari permukaan, seharusnya diproyeksikan")
        keep = np.ones(len(edited), dtype=bool)
        keep[4] = False
        if np.max(np.abs(after[keep] - edited[keep])) > 1e-5:
            problems.append("titik yang tidak disentuh ikut berubah")
        stored = np.array(controls[ops_margin.KEY_CONTROLS]).reshape(-1, 3)
        if not np.allclose(stored, after, atol=1e-6):
            problems.append("titik kontrol tersimpan tidak sama dengan kurva")
        self.check("margin: edit hapus + geser, lalu update", problems)

    def synthetic_case(self, package: str) -> None:
        """Load Synthetic Case lalu Detect Margin; dengan derau 90 um operator harus batal tanpa membuat kurva."""
        import numpy as np

        core_margin = importlib.import_module(f"{package}.core.margin")
        case = importlib.import_module(f"{package}.ops.synthetic_case")
        problems = []
        clear_scene()
        result = bpy.ops.dentalcad.load_synthetic_case(finish="chamfer", scallop_mm=1.0, noise_um=10.0, seed=2)
        die = bpy.data.objects.get(case.DIE_NAME)
        truth_obj = bpy.data.objects.get(f"{case.DIE_NAME} Truth Margin")
        if result != {"FINISHED"} or die is None or truth_obj is None:
            self.check("kasus sintetis: muat", [f"operator {result}, die {die}, kurva benar {truth_obj}"])
            return
        truth = np.array(die[case.KEY_TRUTH], dtype=float).reshape(-1, 3)
        if truth.shape != (case.TRUTH_SAMPLES, 3):
            problems.append(f"margin benar tersimpan {truth.shape}, diharapkan ({case.TRUTH_SAMPLES}, 3)")
        if bpy.context.view_layer.objects.active != die:
            problems.append("die tidak menjadi objek aktif")
        if bpy.context.scene.dentalcad_case.step != "MARGIN":
            problems.append(f"langkah panel {bpy.context.scene.dentalcad_case.step}, diharapkan MARGIN")
        self.check("kasus sintetis: muat die dan margin benar", problems)

        problems = []
        result = bpy.ops.dentalcad.margin_detect(use_seed=True, seed_point=tuple(truth[100] + 0.05))
        controls = bpy.data.objects.get(f"{case.DIE_NAME} Margin")
        if result != {"FINISHED"} or controls is None:
            problems.append(f"deteksi mengembalikan {result}, kurva {controls}")
        else:
            curve = core_margin.MarginCurve(np.array(controls[ops_key(package)]).reshape(-1, 3), None)
            dev = core_margin.margin_deviation(curve.sample(1024), truth)
            if dev["median"] > 0.050:
                problems.append(f"deviasi median {1000 * dev['median']:.1f} um")
        self.check("kasus sintetis: deteksi margin", problems)

        problems = []
        bpy.ops.dentalcad.load_synthetic_case(finish="shoulder", scallop_mm=0.0, noise_um=90.0, seed=0)
        die = bpy.data.objects[case.DIE_NAME]
        truth = np.array(die[case.KEY_TRUTH], dtype=float).reshape(-1, 3)
        try:
            result = bpy.ops.dentalcad.margin_detect(use_seed=True, seed_point=tuple(truth[0]))
            problems.append(f"deteksi pada derau 90 um mengembalikan {result} tanpa error")
        except RuntimeError as exc:  # bpy.ops mengubah laporan ERROR operator menjadi RuntimeError
            if "Scan too noisy" not in str(exc) or "Draw Margin" not in str(exc):
                problems.append(f"pesan error tidak mengarah ke Draw Margin: {exc}")
        for name in (f"{case.DIE_NAME} Margin", f"{case.DIE_NAME} Margin Preview"):
            if bpy.data.objects.get(name) is not None:
                problems.append(f"objek {name} dibuat padahal deteksi ditolak")
        self.check("kasus sintetis: derau 90 um ditolak tanpa kurva", problems)

        # Alur yang ditunjuk pesan error: gambar margin manual di die yang sama, dengan transformasi dunia.
        from mathutils import Matrix, Vector

        problems = []
        ops_margin = importlib.import_module(f"{package}.ops.margin")
        geometry = importlib.import_module(f"{package}.core.geometry")
        die.matrix_world = Matrix.Translation((-2.0, 4.0, 1.0)) @ Matrix.Rotation(0.6, 4, "Z")
        local_clicks = truth[::43] + np.array([0.0, 0.0, 0.05])  # 12 klik, sedikit di atas margin
        world_clicks = [tuple(die.matrix_world @ Vector(p)) for p in local_clicks]
        result = bpy.ops.dentalcad.margin_draw(points=[{"name": "", "co": p} for p in world_clicks])
        controls = bpy.data.objects.get(f"{case.DIE_NAME} Margin")
        if result != {"FINISHED"} or controls is None:
            self.check("margin gambar manual", [f"operator {result}, kurva {controls}"])
            return
        points = ops_margin._spline_points(controls.data)
        if len(points) != len(local_clicks):
            problems.append(f"{len(points)} titik kontrol, diharapkan {len(local_clicks)}")
        _, _, dist = geometry.MeshProjector(self.bridge.from_blender_mesh(die.data)).closest(points)
        if dist.max() > 1e-5:
            problems.append(f"titik kontrol {dist.max():.4f} mm dari permukaan die (koordinat lokal)")
        if controls.get(ops_margin.KEY_ROLE) != "controls" or bpy.data.objects.get(f"{case.DIE_NAME} Margin Preview") is None:
            problems.append("kurva manual tidak punya peran/pratinjau yang sama dengan hasil Detect Margin")
        if any(o.name.endswith("Margin Draft") for o in bpy.data.objects):
            problems.append("objek draf tertinggal")
        edited = points.copy()
        edited[5] = edited[5] + np.array([0.3, 0.0, 0.0])
        ops_margin._set_poly(controls.data, edited)
        bpy.context.view_layer.objects.active = controls
        result = bpy.ops.dentalcad.margin_update()
        if result != {"FINISHED"}:
            problems.append(f"Update Margin pada kurva manual mengembalikan {result}")
        bpy.context.view_layer.objects.active = die
        try:
            bpy.ops.dentalcad.margin_draw(points=[{"name": "", "co": p} for p in world_clicks[:3]])
            problems.append("3 titik seharusnya ditolak")
        except RuntimeError as exc:
            if "minimal 4" not in str(exc):
                problems.append(f"pesan untuk 3 titik tidak sesuai: {exc}")
        self.check("margin gambar manual: klik, tutup otomatis, edit, update", problems)
        self.confirm_gate(package, die)
        self.draw_magnet(package)

    def draw_magnet(self, package: str) -> None:
        """Draw Margin magnetik pada die bersih: 12 klik kasar ditarik ke crease; magnet mati tetap 12 titik."""
        import numpy as np
        from mathutils import Vector

        core_margin = importlib.import_module(f"{package}.core.margin")
        ops_margin = importlib.import_module(f"{package}.ops.margin")
        case = importlib.import_module(f"{package}.ops.synthetic_case")
        problems = []
        bpy.ops.dentalcad.load_synthetic_case(finish="chamfer", scallop_mm=1.0, noise_um=10.0, seed=1)
        die = bpy.data.objects[case.DIE_NAME]
        truth = np.array(die[case.KEY_TRUTH], dtype=float).reshape(-1, 3)
        clicks = truth[::43][:12] + np.random.default_rng(500).normal(0, 0.15, (12, 3))
        world = [{"name": "", "co": tuple(die.matrix_world @ Vector(p))} for p in clicks]
        counts = {}
        for magnet in (False, True):
            result = bpy.ops.dentalcad.margin_draw(points=world, use_magnet=magnet)
            controls = ops_margin.margin_controls(die)
            if result != {"FINISHED"} or controls is None:
                problems.append(f"Draw Margin magnet={magnet} mengembalikan {result}")
                continue
            points = ops_margin._spline_points(controls.data)
            dev = core_margin.margin_deviation(core_margin.MarginCurve(points, None).sample(1024), truth)
            counts[magnet] = (controls[ops_margin.KEY_REVIEW_COUNT], round(1000 * dev["median"]), len(points))
            if controls.get(ops_margin.KEY_STATUS) != "draft":
                problems.append(f"Draw Margin magnet={magnet} tidak berstatus draf")
        if len(counts) == 2:
            if counts[False][2] != 12:
                problems.append(f"tanpa magnet seharusnya 12 titik kontrol, didapat {counts[False][2]}")
            if counts[True][1] > 50 or counts[True][0] >= counts[False][0]:
                problems.append(f"magnet tidak memperbaiki kurva: tanpa {counts[False]}, dengan {counts[True]}")
        self.check(f"margin gambar manual magnetik (segmen merah, median um, titik): {counts}", problems)

    def confirm_gate(self, package: str, die) -> None:
        """Status draf, Confirm Margin, dan gerbang require_confirmed_margin untuk langkah crown/ekspor."""
        import numpy as np

        ops_margin = importlib.import_module(f"{package}.ops.margin")
        problems = []
        controls = ops_margin.margin_controls(die)
        ok, message = ops_margin.require_confirmed_margin(die)
        if controls.get(ops_margin.KEY_STATUS) != "draft" or ok:
            problems.append(f"margin hasil Update harus draf dan ditolak gerbang, didapat "
                            f"{controls.get(ops_margin.KEY_STATUS)} / {ok}")
        flagged = controls.get(ops_margin.KEY_REVIEW_COUNT, 0)
        review_obj = bpy.data.objects.get(f"{die.name} Margin Review")
        if bool(flagged) != (review_obj is not None):
            problems.append(f"{flagged} segmen ditandai, objek merah {review_obj}")

        bpy.context.view_layer.objects.active = controls
        # Titik digeser tanpa Update: Confirm harus menolak.
        points = ops_margin._spline_points(controls.data)
        moved = points.copy()
        moved[0] = moved[0] + np.array([0.2, 0.0, 0.0])
        ops_margin._set_poly(controls.data, moved)
        try:
            bpy.ops.dentalcad.margin_confirm()
            problems.append("Confirm menerima kurva yang diedit tanpa Update")
        except RuntimeError as exc:
            if "Update Margin first" not in str(exc):
                problems.append(f"pesan Confirm untuk kurva yang diedit tidak sesuai: {exc}")
        ops_margin._set_poly(controls.data, points)

        # Segmen merah hanya petunjuk: Confirm tidak meminta persetujuan tambahan.
        result = bpy.ops.dentalcad.margin_confirm()
        ok, message = ops_margin.require_confirmed_margin(die)
        if result != {"FINISHED"} or not ok:
            problems.append(f"Confirm mengembalikan {result}, gerbang: {ok} ({message})")

        # Edit setelah dikonfirmasi: gerbang menolak sampai Update + Confirm lagi.
        ops_margin._set_poly(controls.data, moved)
        ok, message = ops_margin.require_confirmed_margin(die)
        if ok or "edited after it was confirmed" not in message:
            problems.append(f"gerbang menerima margin yang diedit setelah dikonfirmasi: {message}")
        bpy.ops.dentalcad.margin_update()
        if controls.get(ops_margin.KEY_STATUS) != "draft" or ops_margin.require_confirmed_margin(die)[0]:
            problems.append("Update setelah konfirmasi tidak mengembalikan status draf")
        self.check(f"margin: status draf, Confirm Margin, gerbang langkah crown ({flagged} segmen merah)", problems)

    def registration(self) -> None:
        problems = []
        for name in ("DENTALCAD_PT_main", "DENTALCAD_OT_import_stl", "DENTALCAD_OT_import_ply",
                     "DENTALCAD_OT_export_coupons", "DENTALCAD_OT_margin_detect", "DENTALCAD_OT_margin_update",
                     "DENTALCAD_OT_load_synthetic_case", "DENTALCAD_OT_margin_draw"):
            if not hasattr(bpy.types, name):
                problems.append(f"{name} tidak teregistrasi")
        if not hasattr(bpy.types.Scene, "dentalcad_case"):
            problems.append("Scene.dentalcad_case tidak ada")
        self.check("registrasi panel dan operator", problems)


def ops_key(package: str) -> str:
    return importlib.import_module(f"{package}.ops.margin").KEY_CONTROLS


def golden_cases(directory: Path) -> list[Path]:
    if not directory.is_dir():
        return []
    return sorted(p for p in directory.iterdir() if (p / "expected.json").exists())


def parse_args() -> tuple[Path, Path | None]:
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    private = None
    if "--private" in argv:
        i = argv.index("--private")
        private = Path(argv[i + 1]).resolve()
        del argv[i:i + 2]
    return Path(argv[0] if argv else "tests/golden").resolve(), private


def main() -> int:
    golden, private = parse_args()

    package = find_extension()
    import numpy

    print(f"Blender {bpy.app.version_string}, Python {sys.version.split()[0]}, numpy {numpy.__version__}")
    print(f"extension: {package}")

    runner = Runner(package)
    runner.registration()
    runner.bundled_wheels()
    cases = golden_cases(golden)
    if not cases:
        runner.failures.append(f"tidak ada golden case di {golden}")
    for case in cases:
        runner.golden_case(case)

    if private is not None:
        private_cases = golden_cases(private)
        if private_cases:
            print(f"golden privat: {len(private_cases)} case di {private}")
        else:
            print(f"[SKIP] golden privat: tidak ada case di {private}")
        for case in private_cases:
            runner.golden_case(case)

    runner.performance()
    runner.coupons(package)
    runner.margin(package)
    runner.synthetic_case(package)

    print(f"\n{len(runner.failures)} kegagalan" if runner.failures else "\nSemua uji integrasi lulus")
    return 1 if runner.failures else 0


if __name__ == "__main__":
    sys.exit(main())
