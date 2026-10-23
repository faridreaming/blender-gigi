# SPDX-License-Identifier: GPL-3.0-or-later
"""Unduh wheel yang dibundel extension ke ./wheels/ dan cocokkan SHA-256-nya.

Pin dan hash harus sama dengan docs/ARCHITECTURE.md §5 dan daftar `wheels` di
blender_manifest.toml (dicek oleh tests/core/test_repo_rules.py).

    python scripts/download_wheels.py            # unduh yang belum ada, lalu verifikasi semua
    python scripts/download_wheels.py --check    # verifikasi saja, tanpa unduh
"""

from __future__ import annotations

import argparse
import hashlib
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DEST = ROOT / "wheels"

# Tag --platform adalah tag maksimum yang diterima pip: macosx_13_0 = minimum macOS Blender 5.2,
# manylinux_2_28 = glibc 2.28 (basis build Linux Blender).
_CP313 = ("--python-version", "313", "--implementation", "cp", "--abi", "cp313")


@dataclass(frozen=True)
class Wheel:
    filename: str
    requirement: str
    sha256: str
    platform: str | None = None

    def pip_args(self) -> list[str]:
        args = [self.requirement, "--no-deps", "--only-binary=:all:"]
        if self.platform is not None:
            args += [*_CP313, "--platform", self.platform]
        return args


WHEELS = (
    Wheel(
        "trimesh-5.1.1-py3-none-any.whl",
        "trimesh==5.1.1",
        "c5be85a3e31e9ff749f9b0aecc204e37a2cf7cca4e92cd066bb5f3d3c1127765",
    ),
    Wheel(
        "manifold3d-3.5.4-cp313-cp313-win_amd64.whl",
        "manifold3d==3.5.4",
        "76975aa4ebd18dcb0481e43dac3ed70d78066e9ad047e73a5f7dbc0df1553cf4",
        platform="win_amd64",
    ),
    Wheel(
        "manifold3d-3.5.4-cp313-cp313-macosx_11_0_arm64.whl",
        "manifold3d==3.5.4",
        "ed0736f472c3362b8084867f10a724a9a483927bdb7cbfceb564acc52a7f4273",
        platform="macosx_13_0_arm64",
    ),
    Wheel(
        "manifold3d-3.5.4-cp313-cp313-manylinux_2_27_x86_64.manylinux_2_28_x86_64.whl",
        "manifold3d==3.5.4",
        "7a5469641713f1bc291fea873cb134c435704df36828d134190fc2475b304259",
        platform="manylinux_2_28_x86_64",
    ),
    # scipy: Fase 2 (docs/PHASE2.md §6). macOS memakai macosx_12_0 (OpenBLAS) karena macosx_14_0
    # tidak bisa diinstal di macOS 13, minimum Blender 5.2.
    Wheel(
        "scipy-1.18.1-cp313-cp313-win_amd64.whl",
        "scipy==1.18.1",
        "559ed65f60c1af5a03f3912605a1b5114f522c7c32fb23c3376ae8f03219fe28",
        platform="win_amd64",
    ),
    Wheel(
        "scipy-1.18.1-cp313-cp313-macosx_12_0_arm64.whl",
        "scipy==1.18.1",
        "e6fb6a55cc0ba97b59a1f288fb86dc6fce8bdfc0fffcbfd015e3a954bf2a2d93",
        platform="macosx_13_0_arm64",
    ),
    Wheel(
        "scipy-1.18.1-cp313-cp313-manylinux_2_27_x86_64.manylinux_2_28_x86_64.whl",
        "scipy==1.18.1",
        "fdaf5ea890a6183d0565f51a61799d67081bd5b1cf03c5f4b3fd3732108625c9",
        platform="manylinux_2_28_x86_64",
    ),
)


def sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _download(wheel: Wheel, dest: Path) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        cmd = [
            sys.executable, "-m", "pip", "download", *wheel.pip_args(),
            "--dest", tmp, "--quiet", "--disable-pip-version-check",
        ]
        subprocess.run(cmd, check=True)
        got = Path(tmp) / wheel.filename
        if not got.exists():
            found = ", ".join(p.name for p in Path(tmp).iterdir()) or "(kosong)"
            raise RuntimeError(f"pip tidak menghasilkan {wheel.filename}; yang terunduh: {found}")
        shutil.move(str(got), dest / wheel.filename)


def verify(dest: Path = DEFAULT_DEST) -> list[str]:
    """Daftar masalah wheel di dest. List kosong berarti semua wheel ada dan hash-nya cocok."""
    problems = []
    for wheel in WHEELS:
        path = dest / wheel.filename
        if not path.exists():
            problems.append(f"tidak ada: {wheel.filename}")
        elif (actual := sha256_of(path)) != wheel.sha256:
            problems.append(f"SHA-256 tidak cocok: {wheel.filename} (didapat {actual})")
    expected = {w.filename for w in WHEELS}
    for path in sorted(dest.glob("*.whl")) if dest.exists() else ():
        if path.name not in expected:
            problems.append(f"wheel tak terdaftar (akan ikut ter-build): {path.name}")
    return problems


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--dest", type=Path, default=DEFAULT_DEST)
    parser.add_argument("--check", action="store_true", help="verifikasi saja, tanpa unduh")
    args = parser.parse_args(argv)

    args.dest.mkdir(parents=True, exist_ok=True)
    if not args.check:
        for wheel in WHEELS:
            path = args.dest / wheel.filename
            if path.exists() and sha256_of(path) == wheel.sha256:
                print(f"ada      {wheel.filename}")
                continue
            path.unlink(missing_ok=True)
            print(f"unduh    {wheel.filename}")
            _download(wheel, args.dest)

    problems = verify(args.dest)
    for problem in problems:
        print(f"GAGAL    {problem}", file=sys.stderr)
    if not problems:
        print(f"OK       {len(WHEELS)} wheel cocok dengan SHA-256 yang dipin")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
