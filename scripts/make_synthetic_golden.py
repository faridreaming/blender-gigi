# SPDX-License-Identifier: GPL-3.0-or-later
"""Buat golden case sintetis di tests/golden/syn_*.

Ini pengganti sementara sampai 10 scan nyata yang sudah dianonimkan tersedia. Nilai expected.json
dihitung langsung dari array yang ditulis, bukan lewat core/, supaya tes tidak memeriksa dirinya
sendiri. Jalankan ulang hanya kalau definisi case berubah.

    python scripts/make_synthetic_golden.py
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import trimesh

GOLDEN = Path(__file__).resolve().parent.parent / "tests" / "golden"


def _write_case(name: str, mesh: trimesh.Trimesh, suffix: str, watertight: bool, extra: dict) -> None:
    case = GOLDEN / name
    case.mkdir(parents=True, exist_ok=True)
    for old in case.glob("input.*"):
        old.unlink()
    mesh.export(case / f"input{suffix}")

    # STL dan Blender menyimpan koordinat float32, jadi bbox dihitung dari nilai float32.
    vertices = np.asarray(mesh.vertices, dtype=np.float32).astype(np.float64)
    expected = {
        "source": "synthetic",
        "description": extra.pop("description"),
        "input": f"input{suffix}",
        "triangle_count": int(len(mesh.faces)),
        "watertight": watertight,
        "bbox_min": vertices.min(axis=0).tolist(),
        "bbox_max": vertices.max(axis=0).tolist(),
        "max_import_seconds": 5.0,
        **extra,
    }
    (case / "expected.json").write_text(json.dumps(expected, indent=2) + "\n", encoding="utf-8")
    print(f"{name}: {expected['triangle_count']} segitiga")


def main() -> None:
    sphere = trimesh.creation.icosphere(subdivisions=3, radius=5.0)
    _write_case(
        "syn_0001_icosphere_stl", sphere, ".stl", True,
        {"description": "Icosphere radius 5 mm, tertutup (1280 segitiga)."},
    )

    box = trimesh.creation.box(extents=(10.0, 8.0, 6.0))
    box.apply_translation((5.0, 4.0, 3.0))
    # Buang dua segitiga sisi atas (+Z) supaya mesh punya lubang persegi.
    keep = ~np.all(np.isclose(box.vertices[box.faces][:, :, 2], 6.0), axis=1)
    open_box = trimesh.Trimesh(box.vertices, box.faces[keep], process=False)
    _write_case(
        "syn_0002_open_box_stl", open_box, ".stl", False,
        {"description": "Kotak 10x8x6 mm tanpa tutup atas (10 segitiga, 4 edge tepi)."},
    )

    colored = trimesh.creation.icosphere(subdivisions=2, radius=4.0)
    z = colored.vertices[:, 2]
    t = (z - z.min()) / (z.max() - z.min())
    rgba = np.stack(
        [np.round(255 * t), np.full_like(t, 128), np.round(255 * (1 - t)), np.full_like(t, 255)],
        axis=1,
    ).astype(np.uint8)
    colored.visual.vertex_colors = rgba
    _write_case(
        "syn_0003_vertex_color_ply", colored, ".ply", True,
        {
            "description": "Icosphere radius 4 mm dengan vertex color gradien Z (PLY, 320 segitiga).",
            "vertex_colors": True,
            "mean_rgba": rgba.astype(np.float64).mean(axis=0).tolist(),
        },
    )


if __name__ == "__main__":
    main()
