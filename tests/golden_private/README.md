# Golden case privat (scan pasien asli)

Folder ini untuk scan asli yang **tidak boleh di-commit**. Semua isinya kecuali README ini diabaikan git (`.gitignore`), dan `tests/core/test_repo_rules.py` gagal kalau ada file lain di sini yang terlacak git.

Formatnya sama dengan `tests/golden/`:

```
tests/golden_private/<case_id>/
├─ input.stl | input.ply
└─ expected.json
```

`expected.json` minimal berisi `input`, `triangle_count`, `watertight`, `bbox_min`, `bbox_max`, dan `max_import_seconds`; opsional `vertex_colors` dan `mean_rgba`. Isi nilainya dari alat lain yang independen (misalnya software scanner atau MeshLab), bukan dari `core/`, supaya tes tidak memeriksa dirinya sendiri.

Kalau folder ini kosong atau tidak ada, case privat dilewati tanpa error, baik di `pytest tests/core` maupun di `scripts/run_blender_tests.py`. CI tidak pernah punya case privat.

Sebelum menaruh scan di sini:
- Hapus nama, ID pasien, dan metadata lab dari nama file dan header file (header STL 80 byte, komentar PLY).
- Pastikan ada izin tertulis dari pemilik lab dan dokter (lihat `docs/RESEARCH.md`).
- Jangan menyalin file dari sini ke `tests/golden/` atau ke tempat lain yang dilacak git.
