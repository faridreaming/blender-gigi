# SPDX-License-Identifier: GPL-3.0-or-later
"""Gerbang Blender Fase 0: build, validate, instal ke profil sementara, lalu uji integrasi.

    python scripts/run_blender_tests.py --blender "C:/Program Files/Blender Foundation/Blender 5.2/blender.exe"

Path Blender juga bisa lewat env BLENDER. Instalasi memakai BLENDER_USER_RESOURCES ke folder
sementara, jadi preferensi dan extension di profil Blender pengguna tidak tersentuh.
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import download_wheels  # noqa: E402


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
    zip_path = ROOT / "dist" / f"{manifest['id']}-{manifest['version']}.zip"
    zip_path.parent.mkdir(exist_ok=True)
    zip_path.unlink(missing_ok=True)

    blender = args.blender
    try:
        run([blender, "--command", "extension", "build", "--source-dir", str(ROOT), "--output-filepath", str(zip_path)])
        run([blender, "--command", "extension", "validate", str(zip_path)])

        profile = Path(tempfile.mkdtemp(prefix="dentalcad-blender-"))
        env = dict(os.environ, BLENDER_USER_RESOURCES=str(profile))
        try:
            run([blender, "--command", "extension", "install-file", "-r", "user_default", "-e", str(zip_path)], env=env)
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

    print(f"\nLULUS. Zip: {zip_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
