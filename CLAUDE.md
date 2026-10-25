# CLAUDE.md

Aturan proyek `dentalcad`: extension Blender open source untuk dental CAD (crown, bridge, model). Rancangan teknis ada di `docs/ARCHITECTURE.md`, riset dan roadmap di `docs/RESEARCH.md`. Kalau aturan di sini bertentangan dengan dokumen itu, aturan di sini yang berlaku, lalu dokumen diperbarui.

## Gaya penulisan

- **Jangan pakai em dash (U+2014) atau en dash (U+2013)** di mana pun: kode, komentar, docstring, teks UI, dokumen, dan pesan commit. Ganti dengan koma, titik dua, tanda kurung, atau pecah jadi dua kalimat. Untuk rentang, tulis "sampai" (`4.2 LTS sampai 5.0`) atau tanda hubung biasa `-` untuk angka (`4-6 minggu`).
- Dokumen proyek ditulis dalam Bahasa Indonesia. Teks UI di dalam Blender dan isi `blender_manifest.toml` (`tagline`, alasan `[permissions]`) ditulis dalam Bahasa Inggris.
- Pesan commit memakai format Conventional Commits dengan deskripsi Bahasa Indonesia, misalnya `docs: arsitektur fase 0`, `feat(core): loader preset material`.

## Alur kerja

- Jangan menulis kode untuk fase berikutnya sebelum rancangannya di `docs/` disetujui maintainer.
- Versi paket, nama file wheel, dan fakta platform Blender **wajib diverifikasi** (pypi.org, docs.blender.org, developer.blender.org), tidak boleh ditebak. Catat tanggal verifikasi di dokumen.
- Fakta yang sudah dicek langsung oleh maintainer di dalam Blender (misalnya versi numpy) dicatat di `docs/ARCHITECTURE.md` dan menjadi pegangan, di atas metadata PyPI.

## Target dan dependensi

- Target tunggal: **Blender 5.2 LTS** (Python 3.13, cp313), `blender_version_min = "5.2.0"`. Blender 4.5 LTS dan generasi cp311 lainnya tidak didukung.
- Platform: `windows-x64`, `macos-arm64`, `linux-x64`. Tidak ada `macos-x64` (Blender 5.x tidak mendukung Mac Intel).
- numpy bawaan Blender 5.2 LTS: 2.3.4. Jangan bundel ulang numpy atau paket lain yang sudah ada di Blender.
- Wheel di `./wheels/` diunduh dengan perintah di `docs/ARCHITECTURE.md` §5 dan **tidak di-commit**. Nama file di `wheels = [...]` manifest harus sama persis dengan hasil unduhan, dan hash SHA-256 dicatat di §5.
- Dependensi baru hanya ditambahkan di fase yang benar-benar memakainya (contoh: `scipy` ditunda ke backlog §8).
- Lisensi proyek GPL-3.0-or-later. Dependensi dan data (tooth library, preset) harus kompatibel; data library wajib CC0/CC-BY.

## Aturan kode

- `core/` murni Python + numpy: **tidak boleh** `import bpy`, `bmesh`, `mathutils`, atau `gpu`. Semua logika geometri dan validasi ada di sini dan dites dengan `pytest` tanpa Blender.
- `ops/` dan `ui/` tipis: hanya menjembatani bpy dan `core/`. Transfer data mesh lewat `foreach_set`/`foreach_get`, bukan loop per-vertex.
- Import di dalam paket selalu relatif (`from . import mesh_io`). Nama paket sendiri lewat `__package__`, bukan string literal.
- Nama class Blender pakai prefix `DENTALCAD_` (`DENTALCAD_OT_import_stl`), `bl_idname` operator pakai kategori `dentalcad.*`.

## Perintah

```bash
python -m venv .venv && .venv/Scripts/python -m pip install -r requirements-dev.txt   # sekali
.venv/Scripts/python -m pytest tests/core                                           # Lapis 1
.venv/Scripts/python scripts/download_wheels.py                                     # wheel + SHA-256
.venv/Scripts/python scripts/run_blender_tests.py --blender "C:/Program Files/Blender Foundation/Blender 5.2/blender.exe"
.venv/Scripts/python scripts/export_coupons.py                                      # kupon kalibrasi -> dist/kupon/
.venv/Scripts/python scripts/apply_calibration.py <preset.json> <lembar_ukur.csv> --date YYYY-MM-DD [--write]
.venv/Scripts/python scripts/margin_benchmark.py --set tuning --seeds 3           # akurasi margin (Fase 2); set: tuning, tuning2, tuning3, uji
.venv/Scripts/python scripts/insertion_benchmark.py --set tuning --seeds 3        # sumbu insersi + undercut (Fase 2); set: tuning, uji
.venv/Scripts/python scripts/spacer_benchmark.py --seeds 3                        # spacer cement gap (Fase 2)
.venv/Scripts/python scripts/crown_benchmark.py --set tuning --seeds 3            # proposal crown (Fase 2); set: tuning, ukur
```

`run_blender_tests.py` adalah gerbang Fase 0 lengkap: build `dist/dentalcad-<version>.zip`, validate, instal ke profil Blender sementara (`BLENDER_USER_RESOURCES`, profil pengguna tidak tersentuh), lalu Lapis 2.

## Testing

- Lapis 1: `pytest tests/core` dengan Python 3.13, tanpa Blender. rootdir pytest adalah `tests/` (lihat `tests/pytest.ini`), karena root repo adalah paket yang `__init__.py`-nya butuh bpy.
- Lapis 2: `blender --background --python-exit-code 1 --python tests/blender/run_integration.py -- tests/golden`, terhadap extension yang terinstal dari zip. Flag `--python-exit-code 1` wajib ada sebelum `--python`, kalau tidak exception di skrip tetap menghasilkan exit code 0.
- `tests/core/test_repo_rules.py` menegakkan sebagian aturan di file ini (tanpa bpy di `core/`, tanpa em/en dash, manifest sama dengan skrip wheel dan contoh di ARCHITECTURE.md). Jangan melemahkan tes itu untuk meloloskan perubahan.
- Kalau menulis karakter em/en dash di kode tes (misalnya untuk mendeteksinya), pakai `chr(0x2014)` / `chr(0x2013)`, jangan literal atau escape `\u` yang bisa tersimpan sebagai karakter asli.

## Data pasien

- **Scan pasien asli tidak boleh di-commit**, sekalipun sudah dianonimkan. Tempatnya hanya `tests/golden_private/` (diabaikan git kecuali README-nya). Jangan pakai `git add -f` di folder itu, jangan menyalin isinya ke `tests/golden/` atau folder lain yang dilacak, dan jangan menempelkan isinya ke issue, PR, log CI, atau layanan luar. `test_private_scans_are_never_tracked_by_git` gagal kalau ada file di sana yang terlacak.
- Isi `tests/golden_private/` jangan dibaca, diringkas, atau dikutip kecuali untuk menjalankan tes yang memang memakainya.
- `tests/golden/` (di-commit) hanya untuk data sintetis atau data yang dirilis pemiliknya dengan lisensi terbuka.
- Golden case dan file uji harus anonim: hapus nama, ID pasien, dan metadata lab sebelum dipakai.
- Restorasi dari extension ini hanya untuk riset/edukasi dan uji fit di die, bukan untuk dipasang ke pasien.
