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

            volume = manifold3d.Manifold.cube((2.0, 2.0, 2.0)).volume()
            if abs(volume - 8.0) > 1e-9:
                problems.append(f"volume kubus manifold3d {volume} != 8")
            print(f"         trimesh {trimesh.__version__}, manifold3d dari {Path(manifold3d.__file__).parent}")
        except Exception as exc:
            problems.append(f"{type(exc).__name__}: {exc}")
        self.check("wheel trimesh + manifold3d termuat", problems)

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

    def registration(self) -> None:
        problems = []
        for name in ("DENTALCAD_PT_main", "DENTALCAD_OT_import_stl", "DENTALCAD_OT_import_ply",
                     "DENTALCAD_OT_export_coupons"):
            if not hasattr(bpy.types, name):
                problems.append(f"{name} tidak teregistrasi")
        if not hasattr(bpy.types.Scene, "dentalcad_case"):
            problems.append("Scene.dentalcad_case tidak ada")
        self.check("registrasi panel dan operator", problems)


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

    print(f"\n{len(runner.failures)} kegagalan" if runner.failures else "\nSemua uji integrasi lulus")
    return 1 if runner.failures else 0


if __name__ == "__main__":
    sys.exit(main())
