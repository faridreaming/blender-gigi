# SPDX-License-Identifier: GPL-3.0-or-later
"""Gerbang Blender: build per platform, periksa dan validate setiap zip, lalu instal zip milik
platform ini ke profil sementara dan jalankan uji integrasi.

    python scripts/run_blender_tests.py --blender "C:/Program Files/Blender Foundation/Blender 5.2/blender.exe"

Path Blender juga bisa lewat env BLENDER. Instalasi memakai BLENDER_USER_RESOURCES ke folder
sementara, jadi preferensi dan extension di profil Blender pengguna tidak tersentuh.
"""

from __future__ import annotations

import argparse
import os
import platform
import shutil
import subprocess
import sys
import tempfile
import tomllib
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import download_wheels  # noqa: E402

# Isi zip yang diizinkan di tingkat teratas. Apa pun di luar ini berarti [build] membungkus file
# yang tidak seharusnya ikut (contoh nyata: unduhan Blender 385MB dari setup-blender di CI).
ALLOWED_TOP_LEVEL = {
    "blender_manifest.toml", "LICENSE", "__init__.py",
    "core", "ops", "ui", "gpu_draw", "data", "wheels",
}
# Batas efektif extensions.blender.org per zip (docs/ARCHITECTURE.md §5).
MAX_ZIP_BYTES = 200 * 1024 * 1024
# Anggaran per zip platform sebagai alarm dini. Ukuran nyata 2026-10-23: 30 sampai 38 MB
# (didominasi wheel scipy); naik ke atas anggaran berarti ada yang ikut ter-build tanpa sengaja.
PLATFORM_ZIP_BUDGET_BYTES = 60 * 1024 * 1024

# Platform manifest Blender -> potongan tag wheel yang harus ada semuanya. Wheel "-none-any" berlaku
# untuk semua platform.
PLATFORM_WHEEL_TAGS = {
    "windows-x64": ("win_amd64",),
    "macos-arm64": ("macosx_", "_arm64"),
    "linux-x64": ("manylinux", "_x86_64"),
}


def zip_platform(zip_path: Path, manifest: dict) -> str | None:
    """Platform dari sufiks nama zip --split-platforms (misalnya dentalcad-0.1.0-windows_x64.zip)."""
    stem = zip_path.stem
    for name in manifest.get("platforms", []):
        if stem.endswith("-" + name.replace("-", "_")):
            return name
    return None


def wheels_for_platform(manifest: dict, name: str | None) -> list[str]:
    wheels = [w.removeprefix("./") for w in manifest.get("wheels", [])]
    if name is None:
        return sorted(wheels)
    tags = PLATFORM_WHEEL_TAGS[name]
    return sorted(w for w in wheels if w.endswith("-none-any.whl") or all(t in w for t in tags))


def check_zip(zip_path: Path, manifest: dict) -> list[str]:
    """Daftar masalah isi satu zip hasil build. List kosong berarti isinya sesuai."""
    problems = []
    name = zip_platform(zip_path, manifest)
    size = zip_path.stat().st_size
    if size > MAX_ZIP_BYTES:
        problems.append(f"ukuran zip {size / 1e6:.1f} MB melebihi {MAX_ZIP_BYTES / 1e6:.0f} MB")
    if name is not None and size > PLATFORM_ZIP_BUDGET_BYTES:
        problems.append(f"ukuran zip {name} {size / 1e6:.1f} MB melebihi anggaran {PLATFORM_ZIP_BUDGET_BYTES / 1e6:.0f} MB")
    with zipfile.ZipFile(zip_path) as z:
        names = [n for n in z.namelist() if not n.endswith("/")]
    unexpected = sorted({n.split("/", 1)[0] for n in names} - ALLOWED_TOP_LEVEL)
    if unexpected:
        problems.append(f"isi tak terduga di zip: {', '.join(unexpected)}")
    cache = [n for n in names if "__pycache__/" in n or n.endswith(".pyc")]
    if cache:
        problems.append(f"cache Python ikut ter-build: {cache[0]} (dan {len(cache) - 1} lainnya)")
    wheels = sorted(n for n in names if n.startswith("wheels/"))
    expected = wheels_for_platform(manifest, name)
    if wheels != expected:
        problems.append(f"wheel di zip {wheels} != wheel untuk {name or 'semua platform'} {expected}")
    return problems


def host_platform() -> str:
    machine = platform.machine().lower()
    if sys.platform == "win32" and machine in ("amd64", "x86_64"):
        return "windows-x64"
    if sys.platform == "darwin" and machine == "arm64":
        return "macos-arm64"
    if sys.platform.startswith("linux") and machine in ("x86_64", "amd64"):
        return "linux-x64"
    raise RuntimeError(f"platform host tidak didukung: {sys.platform} {machine}")


def run(cmd: list[str], env: dict | None = None) -> None:
    print("$ " + " ".join(f'"{c}"' if " " in c else c for c in cmd), flush=True)
    subprocess.run(cmd, check=True, env=env)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--blender", default=os.environ.get("BLENDER", "blender"))
    parser.add_argument("--keep-profile", action="store_true", help="jangan hapus profil Blender sementara")
    args = parser.parse_args(argv)

    problems = download_wheels.verify()
    if problems:
        for problem in problems:
            print(f"GAGAL wheel: {problem}", file=sys.stderr)
        print("Jalankan dulu: python scripts/download_wheels.py", file=sys.stderr)
        return 1

    with (ROOT / "blender_manifest.toml").open("rb") as f:
        manifest = tomllib.load(f)
    dist = ROOT / "dist"
    dist.mkdir(exist_ok=True)
    for old in dist.glob(f"{manifest['id']}-*.zip"):
        old.unlink()

    blender = args.blender
    try:
        run([blender, "--command", "extension", "build", "--source-dir", str(ROOT),
             "--output-dir", str(dist), "--split-platforms"])
        zips = sorted(dist.glob(f"{manifest['id']}-{manifest['version']}-*.zip"))
        built = {zip_platform(z, manifest): z for z in zips}
        missing = sorted(set(manifest["platforms"]) - set(built))
        if missing or None in built:
            print(f"GAGAL zip: platform tanpa zip {missing}, zip tak dikenal {built.get(None)}", file=sys.stderr)
            return 1
        failed = False
        for name, zip_path in sorted(built.items()):
            for problem in check_zip(zip_path, manifest):
                print(f"GAGAL zip {zip_path.name}: {problem}", file=sys.stderr)
                failed = True
            print(f"isi zip {zip_path.name}: {zip_path.stat().st_size / 1e6:.1f} MB")
        if failed:
            return 1
        for zip_path in built.values():
            run([blender, "--command", "extension", "validate", str(zip_path)])

        own_zip = built[host_platform()]
        profile = Path(tempfile.mkdtemp(prefix="dentalcad-blender-"))
        env = dict(os.environ, BLENDER_USER_RESOURCES=str(profile))
        try:
            run([blender, "--command", "extension", "install-file", "-r", "user_default", "-e", str(own_zip)], env=env)
            run(
                [
                    blender, "--background", "--python-exit-code", "1",
                    "--python", str(ROOT / "tests" / "blender" / "run_integration.py"),
                    "--", str(ROOT / "tests" / "golden"),
                    "--private", str(ROOT / "tests" / "golden_private"),
                ],
                env=env,
            )
        finally:
            if args.keep_profile:
                print(f"profil sementara disimpan di {profile}")
            else:
                shutil.rmtree(profile, ignore_errors=True)
    except subprocess.CalledProcessError as exc:
        print(f"\nGAGAL (exit {exc.returncode}): {exc.cmd[1:4]}", file=sys.stderr)
        return 1

    print(f"\nLULUS. Diuji: {own_zip.name}. Semua zip: {', '.join(z.name for z in zips)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
