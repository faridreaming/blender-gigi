# Arsitektur Fase 0: Fondasi Extension (Blender 5.2 LTS)

Dokumen ini merinci Fase 0 dari roadmap di `RESEARCH.md` ("Fondasi", 4-6 minggu part-time). Lingkupnya murni fondasi teknis: skeleton Extension yang terinstal bersih, pipeline wheel, modul `core/` pertama yang bisa diuji tanpa Blender, dan jalur CI headless. **Tidak ada kode yang ditulis di sini**: dokumen ini adalah rancangan yang harus disepakati sebelum implementasi dimulai.

Nama extension: **`dentalcad`**. Lisensi: **GPL-3.0-or-later** (wajib, lihat RESEARCH.md §7).

## 1. Tujuan dan batas Fase 0

Kriteria selesai dari roadmap:
- Instal bersih di Windows, macOS, dan Linux lewat Extensions Platform (`blender --command extension validate` lolos).
- Impor scan 1 juta segitiga di bawah 5 detik.
- 10 golden case anonim dengan metrik target (watertight, jumlah segitiga, bounding box) diverifikasi otomatis di CI.

Di dalam lingkup Fase 0:
- Skeleton Extension valid (`blender_manifest.toml`, struktur folder, register/unregister).
- Wheel `manifold3d` dan `trimesh` terpaket dan tervalidasi untuk Blender 5.2 LTS (cp313). `scipy` sengaja tidak dibundel di Fase 0 (lihat §8).
- Impor STL dan PLY (termasuk vertex color PLY) menjadi representasi mesh internal.
- Workspace/panel "Dental" minimal (N-panel, bukan Workspace penuh; lihat §6.7 untuk alasannya).
- CI headless: unit test modul `core/` tanpa Blender, dan uji integrasi `blender --background` dengan golden case.

Di luar lingkup (ditunda ke Fase 1+): deteksi margin, sumbu insersi/undercut, spacer, konektor, tooth library, apa pun yang menyentuh geometri gigi secara klinis. `ops/`, `ui/`, dan `gpu_draw/` di Fase 0 hanya berisi yang cukup untuk impor mesh dan menampilkan panel kosong/placeholder.

## 2. Keputusan versi dan platform

Temuan riset yang mengubah asumsi awal RESEARCH.md ("target Blender 4.5 LTS dan 5.x" sebagai satu paket): **Blender 5.1 melompat dari Python 3.11 (cp311) ke Python 3.13 (cp313)**, tanpa generasi cp312, untuk mengikuti VFX Reference Platform CY2026. Wheel biner (misalnya `manifold3d`) yang dikompilasi untuk cp311 tidak akan ter-import di interpreter cp313, dan sebaliknya. Generasi numpy juga ikut berpindah: VFX Reference Platform CY2026 menetapkan NumPy 2.3.x (CY2025: 1.26.x), dan numpy yang terbundel di Blender 5.2 LTS sudah dicek langsung: **2.3.4** (lihat §5).

| Rilis Blender | Python embedded | schema manifest |
|---|---|---|
| 4.2 LTS sampai 5.0 | cp311 (3.11.11 di 4.4/4.5) | `schema_version = "1.0.0"` |
| 5.1, 5.2 LTS | cp313 (numpy 2.3.4 di 5.2 LTS, lihat §5) | `schema_version = "1.0.0"` (tidak berubah) |

**Keputusan Fase 0:** targetkan **hanya Blender 5.2 LTS** (`blender_version_min = "5.2.0"`, tanpa `blender_version_max`). Satu set wheel cp313. **Blender 4.5 LTS (dan seluruh generasi cp311, 4.2 LTS sampai 5.0) tidak didukung**: tidak ada wheel cp311 yang dibundel, dan `blender_version_min` mencegah instalasi di sana. Blender 5.1 juga cp313, tetapi sengaja tidak ditargetkan: bukan LTS, dan masih generasi numpy 1.x (`bpy==5.1.0` di PyPI mensyaratkan `numpy<2.0`), sehingga perilaku numpy di `core/` bisa berbeda antara 5.1 dan 5.2.

Platform rilis (field `platforms` di manifest, lihat §4): `windows-x64`, `macos-arm64`, `linux-x64`.
- **`macos-x64` dikeluarkan.** Blender 5.0 menghapus dukungan Mac Intel (release notes 5.0, bagian Compatibility), dan halaman system requirements blender.org menegaskan 4.5 LTS adalah rilis terakhir untuk Intel Mac dan macOS 11.2. Blender 5.2 LTS tidak berjalan di Mac Intel, jadi wheel `macosx_*_x86_64` tidak akan pernah dimuat.
- **macOS minimum = 13 (Ventura)** menurut system requirements Blender saat ini. Ini menentukan tag `--platform` macOS di §5: wheel bertag lebih baru dari `macosx_13_0_*` tidak boleh dipakai karena tidak bisa diinstal di macOS 13.
- Manifest Blender tidak punya opsi `linux-arm64`, jadi itu otomatis tidak didukung oleh platform extension sendiri. `windows-arm64` ada di manifest dan PyPI punya wheel `win_arm64` cp313 untuk `manifold3d`, tetapi di luar lingkup Fase 0.

## 3. Struktur folder

```
dentalcad/                          # root repo == root isi .zip extension
├─ blender_manifest.toml
├─ LICENSE                          # teks GPL-3.0, ikut di dalam zip
├─ README.md                        # status, instalasi, catatan paten; tidak ikut zip
├─ __init__.py                      # entry point: register_submodule_factory
├─ core/                            # murni Python+numpy, TIDAK PERNAH import bpy/bmesh/mathutils
│  ├─ __init__.py
│  ├─ mesh_data.py                  # dataclass MeshData (array numpy)
│  ├─ mesh_io.py                    # load_mesh()/save_mesh(): STL biner via numpy, STL ASCII/PLY via trimesh
│  ├─ mesh_validate.py              # watertight, triangle_count, bbox, non-manifold edges
│  ├─ material_db.py                # load+validate preset material JSON (skema IFU)
│  ├─ model_presets.py              # preset cetak per printer + resin, status per parameter (Fase 1)
│  ├─ solid.py                      # MeshData <-> manifold3d, validasi, rongga tertutup (Fase 1)
│  ├─ calibration.py                # kupon kalibrasi, lembar ukur, fit_scale (Fase 1)
│  ├─ synthetic.py                  # die preparasi sintetis dengan margin analitis (Fase 2)
│  ├─ geometry.py                   # normal, edge unik, titik terdekat di permukaan (Fase 2)
│  ├─ margin.py                     # margin semi-otomatis + kurva editable (Fase 2)
│  ├─ insertion.py                  # sumbu insersi, peta undercut, block-out (Fase 2)
│  ├─ geodesic.py                   # jarak geodesik ke kurva: fast marching + relaksasi (Fase 2)
│  ├─ spacer.py                     # permukaan dalam crown: cement gap + spacing (Fase 2)
│  └─ units.py                      # konversi mm, tabel penomoran FDI<->Universal/Palmer
├─ ops/                             # bpy.types.Operator, tipis, delegasi ke core/
│  ├─ __init__.py
│  ├─ mesh_bridge.py                # MeshData <-> bpy.types.Mesh lewat foreach_set/foreach_get
│  ├─ coupons.py                    # OT_export_coupons (Fase 1)
│  ├─ margin.py                     # OT_margin_detect / draw / update / confirm (Fase 2)
│  ├─ insertion.py                  # OT_insertion_detect / from_view / view, OT_block_out (Fase 2)
│  ├─ spacer.py                     # OT_spacer, gerbang dan status kedaluwarsa spacer (Fase 2)
│  ├─ synthetic_case.py             # OT_load_synthetic_case: die sintetis + margin benar untuk uji manual (Fase 2)
│  └─ import_mesh.py                # OT_import_stl / OT_import_ply
├─ ui/                              # panel, N-panel tab, state-machine kasus
│  ├─ __init__.py
│  ├─ panel_main.py                 # PT_dental_main, bl_category = "Dental"
│  └─ workspace.py                  # switch/append workspace "Dental" (lihat §6.7)
├─ gpu_draw/                        # stub di Fase 0 (draw handler kosong, disiapkan utk Fase 1+)
│  └─ __init__.py
├─ data/
│  ├─ model_presets/                # preset cetak per printer + resin (Fase 1, docs/PHASE1.md)
│  ├─ materials/                    # preset JSON dari IFU (contoh: zircad_prime.json)
│  │  └─ README.md                 # sumber & tanggal revisi IFU per file
│  └─ libraries/                   # kosong di Fase 0; README menegaskan isi wajib CC0/CC-BY
│     └─ README.md
├─ wheels/                          # *.whl cp313 dari PyPI, diunduh skrip §5, TIDAK di-commit (.gitignore)
├─ scripts/                         # tidak ikut zip
│  ├─ download_wheels.py            # unduh wheel + cek SHA-256 (§5)
│  ├─ run_blender_tests.py          # build, validate, instal ke profil sementara, uji integrasi (§7)
│  ├─ export_coupons.py             # kupon kalibrasi tanpa Blender (Fase 1)
│  ├─ apply_calibration.py          # lembar ukur kupon -> preset (Fase 1)
│  ├─ margin_benchmark.py           # akurasi margin vs margin analitis (Fase 2)
│  ├─ insertion_benchmark.py        # sumbu, undercut, block-out vs jawaban analitis (Fase 2)
│  ├─ spacer_benchmark.py           # spacer vs jawaban analitis die lingkaran (Fase 2)
│  └─ make_synthetic_golden.py      # pembuat golden case sintetis sementara (§7)
├─ tests/
│  ├─ pytest.ini                    # rootdir pytest = tests/ (root repo adalah paket yang butuh bpy)
│  ├─ conftest.py
│  ├─ core/                         # pytest biasa, tanpa Blender sama sekali
│  │  ├─ test_mesh_io.py
│  │  ├─ test_mesh_validate.py
│  │  ├─ test_material_db.py
│  │  ├─ test_units.py
│  │  ├─ test_repo_rules.py         # core/ tanpa bpy, tanpa em/en dash, manifest == skrip wheel
│  │  └─ test_zip_check.py          # pemeriksaan isi zip hasil build
│  ├─ blender/                      # hanya jalan di dalam `blender --background`
│  │  └─ run_integration.py         # runner: import golden case lewat ops/, cek lewat core/
│  ├─ golden_private/               # scan asli, diabaikan git kecuali README; dilewati kalau kosong
│  └─ golden/                       # target 10 case anonim; sementara 3 case sintetis syn_*
│     └─ <case_id>/
│        ├─ input.stl | input.ply
│        └─ expected.json           # {triangle_count, watertight, bbox_min, bbox_max, max_import_seconds}
├─ requirements-dev.txt             # numpy 2.3.4, trimesh, pytest (host, bukan wheel yg dibundel)
└─ .github/workflows/ci.yml
```

Catatan penting dari riset soal lokasi file: Blender mewajibkan `blender_manifest.toml` dan `__init__.py` berada di **root** arsip (atau root satu folder pembungkus tunggal, yang dideteksi/dilepas otomatis). Tidak ada direktori `src/` perantara. Nama folder repo di disk bersifat kosmetik: identitas extension berasal dari field `id` di manifest, dan saat instal Blender mengimpornya sebagai modul `bl_ext.<repository>.<id>`.

Setiap sub-paket (`core/`, `ops/`, `ui/`, `gpu_draw/`) punya `__init__.py` sendiri. Import di seluruh proyek **wajib relatif** (`from . import mesh_io`, bukan `from dentalcad.core import mesh_io`). Ini ditegaskan di dokumentasi karena setiap extension dimuat sebagai sub-modul terisolasi `bl_ext.<repo>.<id>`, jadi import absolut dengan nama sendiri tidak akan resolve.

## 4. `blender_manifest.toml`

Field manifest bersumber dari manual resmi (`getting_started.html`, `python_wheels.html`, `tags.html`, `licenses.html`). Skema manifest sendiri (`schema_version = "1.0.0"`) stabil sejak Extensions diluncurkan di 4.2 dan belum berubah hingga 5.2 LTS.

| Field | Wajib | Catatan |
|---|---|---|
| `schema_version` | ya | Versi format file manifest, selalu `"1.0.0"` saat ini. |
| `id` | ya | Identitas unik, jadi nama modul `bl_ext.<repo>.<id>`. |
| `version` | ya | SemVer milik extension sendiri. |
| `name` | ya | Nama tampilan. |
| `tagline` | ya | ≤64 karakter, tanpa titik di akhir. |
| `maintainer` | ya | `"Nama <email>"`. |
| `type` | ya | Hanya `"add-on"` atau `"theme"`. |
| `blender_version_min` | ya | `"5.2.0"` untuk Fase 0. |
| `license` | ya | Array, prefix `"SPDX:"` wajib, mis. `"SPDX:GPL-3.0-or-later"`. |
| `website` | tidak | URL repo/dokumentasi. |
| `tags` | tidak | Harus dari vokabuler tetap 28 tag add-on (lihat di bawah); nilai luar daftar ditolak platform. |
| `blender_version_max` | tidak | Batas atas eksklusif; umumnya diomit dan dikelola dari web platform saat ada regresi. |
| `copyright` | tidak | Format `"YYYY[-YYYY] Nama"`. |
| `platforms` | tidak | Dari 5 nilai: `windows-x64`, `windows-arm64`, `macos-x64`, `macos-arm64`, `linux-x64`. Tanpa field ini, extension ditawarkan di semua OS, jadi field ini **wajib diisi** begitu ada wheel platform-spesifik. |
| `wheels` | tidak | Array path relatif (`/` selalu, termasuk di Windows) ke file `.whl`, konvensi di `./wheels/`. |
| `[permissions]` | tidak | Tabel, kunci dari `files`/`network`/`clipboard`/`camera`/`microphone`, masing-masing wajib string alasan ≤64 karakter. |
| `[build]` | tidak | `paths` atau `paths_exclude_pattern` (saling eksklusif); `build.generated` **jangan ditulis manual** (reserved untuk tool build). |

Contoh di bawah identik dengan `blender_manifest.toml` di repo. `tagline` dipendekkan supaya muat batas 64 karakter, dan `website` belum diisi sampai URL repo publik ada.

Tag add-on yang relevan untuk `dentalcad`: `"Import-Export"`, `"Mesh"`, `"Modeling"` (dari 28 tag resmi; nilai di luar daftar ini ditolak server, jadi jangan menambah tag "Dental"/"Medical" yang tidak ada di vokabuler).

```toml
schema_version = "1.0.0"

id = "dentalcad"
version = "0.1.0"
name = "DentalCAD"
tagline = "Open-source dental CAD for crown, bridge, and model design"
maintainer = "Muhammad Farid Yamin <muhammad.farid.yamin@gmail.com>"
type = "add-on"

tags = ["Import-Export", "Mesh", "Modeling"]

blender_version_min = "5.2.0"
# blender_version_max diomit dengan sengaja. Fase 0 hanya menargetkan 5.2 LTS (Python 3.13);
# 4.5 LTS dan generasi cp311 lainnya tidak didukung (lihat docs/ARCHITECTURE.md §2 dan §8).

license = [
  "SPDX:GPL-3.0-or-later",
]
copyright = [
  "2026 Muhammad Farid Yamin",
]

platforms = ["windows-x64", "macos-arm64", "linux-x64"]

# Diunduh oleh scripts/download_wheels.py (dicek SHA-256), tidak di-commit.
wheels = [
  "./wheels/trimesh-5.1.1-py3-none-any.whl",
  "./wheels/manifold3d-3.5.4-cp313-cp313-win_amd64.whl",
  "./wheels/manifold3d-3.5.4-cp313-cp313-macosx_11_0_arm64.whl",
  "./wheels/manifold3d-3.5.4-cp313-cp313-manylinux_2_27_x86_64.manylinux_2_28_x86_64.whl",
  "./wheels/scipy-1.18.1-cp313-cp313-win_amd64.whl",
  "./wheels/scipy-1.18.1-cp313-cp313-macosx_12_0_arm64.whl",
  "./wheels/scipy-1.18.1-cp313-cp313-manylinux_2_27_x86_64.manylinux_2_28_x86_64.whl",
]

[permissions]
files = "Import and export STL/PLY dental scan and design files"

[build]
paths_exclude_pattern = [
  "__pycache__/",
  "/.git/",
  "/.github/",
  "/.claude/",
  "/.venv/",
  "/.pytest_cache/",
  "/*.zip",
  # Unduhan Blender dari action setup-blender di CI (.tar.xz, .dmg, .zip di root repo).
  "/blender-download.*",
  "/dist/",
  "/docs/",
  "/scripts/",
  "/tests/",
  "/.gitignore",
  "/CLAUDE.md",
  "/README.md",
  "/requirements-dev.txt",
]
```

`network` sengaja **tidak** dideklarasikan di Fase 0: belum ada fitur yang butuh koneksi keluar. Tambahkan nanti hanya saat fitur itu benar-benar dibangun, dan di runtime tetap wajib cek `bpy.app.online_access` sebelum membuka koneksi.

## 5. Strategi wheel

Semua pin di bawah diverifikasi di pypi.org (JSON API) pada 2026-10-23, dan nama file di manifest §4 adalah hasil nyata menjalankan perintah unduh di bawah.

| Paket | Lisensi | Pin untuk cp313 (Blender 5.2 LTS) | `requires_dist` (PyPI) | Alasan pin |
|---|---|---|---|---|
| `manifold3d` | Apache-2.0 | `3.5.4` (terbaru, rilis 2026-09-25) | `numpy>=1.26.0b1` (Python ≥3.12) | Wheel cp313 tersedia untuk `win_amd64`, `macosx_11_0_arm64`, dan `manylinux_2_27_x86_64.manylinux_2_28_x86_64`, jadi tidak perlu build dari sumber. |
| `scipy` | BSD-3-Clause | `1.18.1` (terbaru, rilis 2026-08-21; `requires_python >=3.12`; dicek ulang 2026-10-23) | `numpy>=2.0.0,<2.8` | Masuk di Fase 2 (docs/PHASE2.md §6, K1) untuk `scipy.sparse` dan `scipy.spatial`. Wheel cp313 untuk ketiga platform; macOS arm64 memakai `macosx_12_0_arm64` (OpenBLAS), bukan `macosx_14_0_arm64`, karena minimum macOS Blender adalah 13. Rentang numpy mencakup 2.3.4. |
| `trimesh` | MIT | `5.1.1` (terbaru, rilis 2026-10-02), unduh dengan `--no-deps` | `numpy>=1.21` | Wheel tunggal `py3-none-any` (pure Python, tanpa ekstensi terkompilasi): satu file berlaku untuk semua platform/OS. Dependensi wajibnya hanya `numpy`, yang sudah dibundel Blender, jadi `--no-deps` mencegah duplikasi. |

`scipy` tidak dibundel di Fase 0 dan Fase 1, dan masuk mulai Fase 2 bersama build per platform.

**Versi numpy di Blender 5.2 LTS: 2.3.4.** Dicek langsung oleh maintainer di dalam Blender 5.2 LTS (`import numpy; numpy.__version__`) pada 2026-10-23. Ini konsisten dengan VFX Reference Platform CY2026 (NumPy 2.3.x) dan metadata `bpy==5.2.0` di PyPI (`numpy>=2.2,<3.0`), dan memenuhi `requires_dist` semua wheel di atas (`manifold3d`: `>=1.26.0b1`, `scipy`: `>=2.0.0,<2.8`, `trimesh`: `>=1.21`). Metadata paket `bpy` di PyPI tidak selalu konsisten dengan numpy yang benar-benar dibundel, jadi angka 2.3.4 inilah pegangannya. Cek ulang setiap kali target dinaikkan ke rilis koreksi 5.2.x baru.

**Jangan dibundel ulang** (sudah ada di dalam Blender 5.2 LTS, membundel ulang berisiko konflik versi): `numpy` (2.3.4), serta modul intrinsik yang selalu built-in dan tidak pernah berbentuk wheel (`bpy`, `mathutils`, `bmesh`, `gpu`, `blf`, `aud`, `imbuf`, `idprop`, `freestyle`, `bpy_extras`), dan paket pip yang ikut dalam `python/lib` Blender. Metadata `bpy==5.2.0` di PyPI menyebut `cattrs`, `cython`, `numpy`, `requests`, `zstandard`; daftar persisnya (termasuk dependensi `requests` seperti `certifi`, `idna`, `urllib3`) harus dicek di `python/lib` instalasi 5.2 LTS.

**Alur unduh wheel** (dijalankan manual/CI sebelum build; `./wheels/` ada di `.gitignore` dan **tidak di-commit**, karena wheel diunduh ulang dari PyPI dengan pin persis setiap build). Implementasinya `python scripts/download_wheels.py`: menjalankan `pip download` yang setara dengan perintah di bawah, mencocokkan SHA-256 tiap file dengan tabel di bawah, dan keluar dengan exit 1 kalau ada wheel yang hilang, hash-nya beda, atau ada wheel tak terdaftar di `./wheels/` (karena akan ikut ter-build). `--check` hanya memverifikasi. Perintah manualnya:

```bash
mkdir -p wheels
pip download trimesh==5.1.1 --dest wheels --no-deps --only-binary=:all:

# Tag --platform adalah tag MAKSIMUM yang diterima pip: macosx_13_0_arm64 = minimum macOS
# Blender 5.2 (pip memilih wheel bertag <= 13.0), manylinux_2_28 = glibc 2.28 (Rocky Linux 8,
# basis build Linux Blender).
for plat in win_amd64 macosx_13_0_arm64 manylinux_2_28_x86_64; do
  pip download manifold3d==3.5.4 --dest wheels --no-deps --only-binary=:all: \
    --python-version 313 --implementation cp --abi cp313 --platform "$plat"
  pip download scipy==1.18.1 --dest wheels --no-deps --only-binary=:all: \
    --python-version 313 --implementation cp --abi cp313 --platform "$plat"
done
```

`--only-binary=:all:` memaksa pip gagal (bukan build dari sumber) kalau wheel prebuilt tidak ada untuk kombinasi itu. `--no-deps` wajib supaya `numpy` tidak ikut terunduh/terbundel.

Hasil persis perintah di atas (diverifikasi 2026-10-23; hash scipy juga cocok dengan digest yang dipublikasikan PyPI), sama dengan daftar `wheels` di manifest §4:

| File | Ukuran | SHA-256 |
|---|---|---|
| `trimesh-5.1.1-py3-none-any.whl` | 0,7 MB | `c5be85a3e31e9ff749f9b0aecc204e37a2cf7cca4e92cd066bb5f3d3c1127765` |
| `manifold3d-3.5.4-cp313-cp313-win_amd64.whl` | 1,0 MB | `76975aa4ebd18dcb0481e43dac3ed70d78066e9ad047e73a5f7dbc0df1553cf4` |
| `manifold3d-3.5.4-cp313-cp313-macosx_11_0_arm64.whl` | 0,9 MB | `ed0736f472c3362b8084867f10a724a9a483927bdb7cbfceb564acc52a7f4273` |
| `manifold3d-3.5.4-cp313-cp313-manylinux_2_27_x86_64.manylinux_2_28_x86_64.whl` | 1,4 MB | `7a5469641713f1bc291fea873cb134c435704df36828d134190fc2475b304259` |
| `scipy-1.18.1-cp313-cp313-win_amd64.whl` | 36,6 MB | `559ed65f60c1af5a03f3912605a1b5114f522c7c32fb23c3376ae8f03219fe28` |
| `scipy-1.18.1-cp313-cp313-macosx_12_0_arm64.whl` | 28,7 MB | `e6fb6a55cc0ba97b59a1f288fb86dc6fce8bdfc0fffcbfd015e3a954bf2a2d93` |
| `scipy-1.18.1-cp313-cp313-manylinux_2_27_x86_64.manylinux_2_28_x86_64.whl` | 35,3 MB | `fdaf5ea890a6183d0565f51a61799d67081bd5b1cf03c5f4b3fd3732108625c9` |

Karena `./wheels/` tidak di-commit, hash di atas adalah pegangan reproduktibilitas: skrip unduh di CI sebaiknya mencocokkan SHA-256 ini (atau memakai `requirements` dengan `--require-hashes`) sebelum `extension build`.

Batas ukuran: extensions.blender.org menegakkan batas efektif **~200MB per zip** (HTTP 413 di atas itu). Sejak Fase 2 total wheel ±105MB (scipy ±35MB per platform), jadi build memakai `blender --command extension build --split-platforms`: satu zip per platform dengan sufiks nama platform, masing-masing hanya membawa wheel platformnya. `check_zip` memeriksa setiap zip terhadap batas 200MB dan anggaran per zip (lihat §7). Kalau fase mendatang menambah `Open3D` (disebut "besar" di RESEARCH.md), anggaran itu diukur ulang.

Gerbang validasi wajib sebelum setiap rilis (dan di CI, lihat §7): `blender --command extension build --source-dir . --output-dir dist --split-platforms` lalu `blender --command extension validate` untuk setiap zip di `dist/`. Keduanya CLI argparse biasa dengan exit code benar (0/1) tanpa perlu `--python-exit-code`.

## 6. Modul `core/` yang bisa diuji tanpa Blender

Aturan keras: **tidak ada file di `core/` yang boleh `import bpy`, `bmesh`, `mathutils`, atau `gpu`.** Semua representasi mesh di dalam `core/` adalah array `numpy` murni, dibungkus struktur ringan (misalnya `MeshData` dengan atribut `vertices: np.ndarray[N,3]`, `faces: np.ndarray[M,3]`), bukan `bpy.types.Mesh`. Ini yang membuatnya bisa diuji dengan `pytest` biasa di host mana pun (laptop developer, GitHub Actions `ubuntu-latest` tanpa Blender sama sekali).

### 6.1 `core/mesh_io.py`
- `load_mesh(path: str | Path) -> MeshData`: baca STL dan PLY (termasuk vertex color untuk scan IOS berwarna). Mengembalikan `MeshData` yang juga membawa warna vertex bila ada.
  - STL biner dibaca langsung dengan `numpy.frombuffer`, lalu sudut segitiga yang koordinat float32-nya identik digabung (`merge_exact_vertices`: hash 64-bit + `argsort`, dicek ulang dan jatuh ke `lexsort` kalau ada tabrakan). Di Blender 5.2.3 jalur ini memuat 1,31 juta segitiga dalam ±1,3 s, dibanding ±4,1 s lewat `trimesh.load(process=True)`.
  - STL ASCII dan PLY lewat `trimesh.load()`. PLY tidak digabung ulang karena formatnya sudah berindeks.
- `save_mesh(mesh: MeshData, path) -> None`: tulis STL/PLY lewat `trimesh`.
- Lapisan ini adalah satu-satunya tempat yang tahu soal format file. `ops/import_mesh.py` memanggil ini, lalu menuang hasilnya ke `bpy.data.meshes` lewat `foreach_set` (lihat §6.5), bukan sebaliknya.

### 6.2 `core/mesh_validate.py`
- `is_watertight(mesh: MeshData) -> bool`
- `triangle_count(mesh: MeshData) -> int`
- `bounding_box(mesh: MeshData) -> tuple[np.ndarray, np.ndarray]`
- `non_manifold_edge_count(mesh: MeshData) -> int`
- Fungsi-fungsi ini adalah mesin verifikasi golden case di §7: ditulis sekali di `core/`, dipakai ulang baik dari `pytest tests/core/` maupun dari skrip integrasi `blender --background`.

### 6.3 `core/material_db.py`
- `load_material_preset(path) -> MaterialPreset` dan validasi skema (field minimal: `min_thickness_anterior_mm`, `min_thickness_posterior_mm`, `connector_area_mm2`, `cement_gap_um`, `source`, `source_date`) sesuai tabel parameter IFU di RESEARCH.md §2.
- Fase 0 hanya menyiapkan loader + skema + 1-2 file JSON contoh (`data/materials/zircad_prime.json`) sebagai bukti jalur kerja. Validasi otomatis ketebalan/konektor terhadap geometri nyata adalah Fase 2-3, **bukan** Fase 0. Tetapi loader data harus berdiri lebih dulu karena ini murni data, tidak tergantung bpy sama sekali, dan dites sekarang supaya skema tidak berubah lagi saat fase berikutnya butuh.

### 6.4 `core/units.py`
- Konversi satuan (mm Blender), dan tabel penomoran gigi FDI (ISO 3950) ↔ Universal ↔ Palmer. Data statis + fungsi murni, disiapkan lebih awal karena UI akan memakainya lintas fase, dan tidak ada alasan menunggu bpy untuk ini.

### 6.5 Lapisan `ops/` (bpy, tipis)
`ops/import_mesh.py` berisi `DENTALCAD_OT_import_stl` dan `DENTALCAD_OT_import_ply`: baca file lewat `core.mesh_io.load_mesh()`, lalu bangun `bpy.data.meshes` baru dengan `foreach_set` dari array numpy (bukan loop per-vertex Python; lihat catatan performa RESEARCH.md §6). Operator ini tidak punya logika geometri sendiri; semua logika ada di `core/` dan sudah diuji di sana.

### 6.6 Registrasi dan namespacing
- `__init__.py` root memakai `bpy.utils.register_submodule_factory(__name__, ["ops", "ui", "gpu_draw"])`; `core/` tidak diregistrasi (bukan bpy classes).
- Setiap submodul (`ops/__init__.py`, `ui/__init__.py`) mendefinisikan `classes = (...)` sendiri dan `register()/unregister()` sendiri, lazimnya lewat `bpy.utils.register_classes_factory(classes)`.
- Penamaan class wajib pola `UPPER_CASE_{OT|PT|MT|HT|UL}_snake_case` (ditegakkan oleh `register_class`); prefix proyek `DENTALCAD_` dipakai konsisten untuk menghindari kolisi dengan extension lain (`DENTALCAD_OT_import_stl`, `DENTALCAD_PT_main`).
- `bl_idname` operator: `dentalcad.import_stl` (lowercase, satu titik, kategori milik sendiri, bukan kategori generik `import_mesh.*`).
- Modul terinstal sebagai `bl_ext.<repo>.dentalcad`; setiap tempat yang butuh nama paket sendiri (misalnya `AddonPreferences.bl_idname`) **wajib** memakai `__package__`, tidak boleh string literal.

### 6.7 Workspace "Dental": keterbatasan yang ditemukan riset
Riset mengonfirmasi `bpy.types.WorkSpace` adalah **ID data-block**, bukan class yang bisa di-`register_class()`. Tidak ada mekanisme resmi bagi add-on/extension untuk mendefinisikan Workspace baru secara terprogram. Opsi nyata yang didokumentasikan hanya:
1. Mengaktifkan Workspace yang sudah ada (`bpy.context.window.workspace = ...`).
2. Append dari `.blend` yang dibundel lewat `bpy.ops.workspace.append_activate(...)`.
3. Mekanisme "Application Template": artefak yang sepenuhnya berbeda dari add-on/extension (`type = "add-on"` tidak menghasilkan ini).

**Keputusan Fase 0:** jangan kejar Workspace terpisah. Implementasikan `ui/panel_main.py` sebagai N-panel biasa (`bl_space_type='VIEW_3D'`, `bl_region_type='UI'`, `bl_category="Dental"`) di workspace default. Ini cukup untuk placeholder state machine (Order → Scan, langkah selanjutnya belum ada fungsinya di Fase 0). `ui/workspace.py` disiapkan sebagai tempat nanti menambahkan opsi (2), yaitu append `.blend` berisi layout viewport custom, **hanya jika** kebutuhan nyata muncul di fase mendatang. Catat ini sebagai keputusan yang disengaja, bukan kelalaian.

## 7. Strategi testing headless

Dua lapis, sesuai pembagian `core/` vs `ops/` di atas:

### Lapis 1: `pytest tests/core/`, tanpa Blender sama sekali
Python biasa (matrix CI `ubuntu-latest`, Python 3.13, sama dengan interpreter Blender 5.2 LTS), cepat, tidak butuh men-download Blender. Menjalankan semua test `mesh_io`, `mesh_validate`, `material_db`, `units` terhadap fixture mesh sintetis dan golden STL. Ini mayoritas test suite.

### Lapis 2: `blender --background`, untuk `ops/` dan integrasi penuh
Yang dites adalah **zip hasil build**, bukan folder repo, supaya wheel dan aturan `[build]` ikut teruji. Satu perintah menjalankan seluruh gerbang:
```bash
python scripts/run_blender_tests.py --blender "<path ke blender>"
```
Urutannya: cek wheel (`download_wheels.verify`), `extension build --split-platforms` ke `dist/dentalcad-<version>-<platform>.zip` (satu zip per platform di manifest), pemeriksaan setiap zip (`check_zip`: hanya `blender_manifest.toml`, `LICENSE`, `__init__.py`, `core/`, `ops/`, `ui/`, `gpu_draw/`, `data/`, `wheels/` di tingkat teratas, tanpa `__pycache__`, wheel sama persis dengan wheel manifest untuk platform zip itu ditambah wheel `-none-any`, ukuran di bawah 200MB dan di bawah anggaran per zip 60MB), `extension validate` untuk setiap zip, lalu `extension install-file -r user_default -e` untuk **zip milik platform host** ke profil Blender sementara (env `BLENDER_USER_RESOURCES` diarahkan ke folder temp, jadi preferensi dan extension di profil pengguna tidak tersentuh), lalu:
```bash
blender --background --python-exit-code 1 --python tests/blender/run_integration.py -- tests/golden
```
Profil sementara dihapus di akhir (`--keep-profile` untuk menyimpannya saat debugging).

Dua hal krusial dari riset yang **wajib** dipegang:
- **`--python-exit-code 1` harus ditulis sebelum `--python`.** Tanpanya, exception Python yang tidak tertangkap di dalam skrip tetap membuat proses Blender keluar dengan kode 0, sehingga CI akan melaporkan sukses palsu. Ini bug/perilaku lama Blender yang dikonfirmasi di tracker resminya dan berulang kali menjebak proyek add-on lain.
- `sys.exit(code)` di dalam skrip tetap diteruskan sebagai exit code proses Blender sungguhan (dengan flag di atas terpasang). Ini mekanisme yang dipakai untuk menjalankan `pytest.main([...])` di dalam sesi Blender dan meneruskan hasilnya: `sys.exit(pytest.main(["-v", "tests/blender"]))`.
- `fake-bpy-module-5.2` (paket PyPI) **hanya stub tipe untuk editor/IDE** (autocomplete, type checking): tidak eksekutabel, tidak bisa dipakai menjalankan test di luar Blender. Jangan dicoba sebagai pengganti layer 2.

`run_integration.py` memeriksa registrasi panel/operator, memuat wheel `trimesh`, `manifold3d`, dan `scipy` dari extension yang terinstal (scipy wajib dimuat dari folder extension, bukan dari tempat lain), lalu untuk setiap folder di `tests/golden/<case_id>/`: panggil operator `DENTALCAD_OT_import_stl` (atau `_ply`) pada file input, lalu baca balik hasilnya jadi `MeshData` (lewat `foreach_get` dari `bpy.data.meshes` aktif) dan jalankan fungsi `core.mesh_validate` yang **sama** yang sudah dites di Lapis 1, bandingkan dengan `expected.json`. Ini sengaja memakai ulang fungsi `core/` yang sama, tidak menulis logika validasi kedua di sisi Blender.

### Gerbang manifest/packaging
```bash
blender --command extension build --source-dir . --output-dir dist --split-platforms
blender --command extension validate dist/dentalcad-0.1.0-windows_x64.zip   # dan setiap zip platform lain
```
Keduanya subcommand argparse biasa dengan exit code benar secara native (0/1), tanpa butuh `--python-exit-code`. Jalankan di setiap PR sebagai gerbang terpisah dari test suite.

### Matriks CI (GitHub Actions)
- Job `core-tests`: `ubuntu-latest`, Python 3.13, tanpa Blender. `pip install -r requirements-dev.txt && pytest tests/core`.
- Job `blender`: matrix `os: [ubuntu-latest, windows-latest, macos-latest]`, `bradyajohnston/setup-blender@v5` versi `"5.2"`, lalu `python scripts/download_wheels.py` dan `python scripts/run_blender_tests.py`. Setiap runner membangun dan memeriksa ketiga zip, lalu menginstal dan menguji zip milik OS-nya sendiri, sehingga wheel platform (scipy, manifold3d) teruji di OS masing-masing. Ketiga zip dari runner Ubuntu diunggah sebagai artifact.

### Golden case
`tests/golden/<case_id>/input.stl` atau `input.ply` (anonim: nama/ID pasien dan metadata lab dihapus sebelum commit, sesuai RESEARCH.md §7) + `expected.json` berisi `{triangle_count, watertight, bbox_min, bbox_max, max_import_seconds}`, opsional `vertex_colors` dan `mean_rgba`. Target Fase 0: 10 case dari scan nyata. Sampai scan itu tersedia, `scripts/make_synthetic_golden.py` membuat 3 case sintetis (`syn_*`: icosphere tertutup, kotak terbuka, PLY berwarna) yang nilai expected-nya dihitung dari array yang ditulis, bukan lewat `core/`. Case yang sama juga dites di Lapis 1 (`test_mesh_io.py`).

Scan nyata disimpan di `tests/golden_private/<case_id>/` dengan format yang sama. Folder itu diabaikan git kecuali README-nya (scan pasien asli tidak pernah di-commit, lihat CLAUDE.md), tidak ikut zip karena `/tests/` dikecualikan dari build, dan tidak ada di CI. Lapis 1 dan Lapis 2 (`run_integration.py ... --private tests/golden_private`) menjalankan case privat kalau ada, dan melewatinya tanpa error kalau folder kosong atau tidak ada. `test_repo_rules.py` gagal kalau ada file selain README di folder itu yang terlacak git.

Kriteria "impor 1 juta segitiga di bawah 5 detik" diuji terpisah di `run_integration.py`: icosphere 1.310.720 segitiga dibuat saat tes (file ±65MB, tidak di-commit), lalu operator impor diukur dari awal sampai selesai. Hasil di Blender 5.2.3 LTS (Windows x64): 2,24 s.

## 8. Keputusan terbuka dan risiko dibawa ke fase berikutnya

- **`scipy`**: sudah masuk di Fase 2 (docs/PHASE2.md §6, K1), lihat tabel wheel di §5. Setiap menaikkan versinya, cek di PyPI bahwa masih ada wheel cp313 untuk ketiga platform dan bahwa rentang `numpy` di `requires_dist` masih mencakup numpy Blender target.
- **Blender 4.5 LTS (cp311) tidak didukung**, dan tidak ada rencana backport. Kalau suatu saat dibutuhkan, itu berarti set wheel cp311 kedua dan rilis extension terpisah, bukan pekerjaan Fase 0.
- **Mac Intel tidak didukung** karena Blender 5.x sendiri tidak berjalan di sana (lihat §2). `windows-arm64` mungkin ditambahkan nanti (wheel `win_arm64` cp313 tersedia untuk `manifold3d`).
- **Workspace "Dental" penuh** (bukan sekadar N-panel) butuh pendekatan append `.blend` atau Application Template. Belum diputuskan, lihat §6.7. Jangan dikerjakan sebelum ada kebutuhan konkret dari Fase 1/2.
- **Anggaran ukuran extension** terhadap batas ~200MB `extensions.blender.org`: aman di Fase 0 (±4MB). `scipy` (±100MB) dan `Open3D` (disebut "besar", untuk fase ICP mendatang) perlu diukur ulang saat ditambahkan, dengan `--split-platforms` sebagai jalan keluar.
- **numpy 2.3.4** sudah dicek langsung di Blender 5.2 LTS (lihat §5). Cek ulang (`import numpy; numpy.__version__`) setiap kali target dinaikkan ke rilis koreksi 5.2.x baru, karena metadata PyPI paket `bpy` tidak konsisten mem-pin ini.

## Referensi utama

- Blender Manual, Extensions: [Getting Started](https://docs.blender.org/manual/en/latest/advanced/extensions/getting_started.html), [Python Wheels](https://docs.blender.org/manual/en/latest/advanced/extensions/python_wheels.html), [Tags](https://docs.blender.org/manual/en/latest/advanced/extensions/tags.html), [Licenses](https://docs.blender.org/manual/en/latest/advanced/extensions/licenses.html), [Extension command-line arguments](https://docs.blender.org/manual/en/latest/advanced/command_line/extension_arguments.html)
- Blender Developer Docs: [Add-on dev setup](https://developer.blender.org/docs/handbook/extensions/addon_dev_setup/), [Python testing handbook](https://developer.blender.org/docs/handbook/testing/python/), [Manifest schema 1.0.0](https://developer.blender.org/docs/features/extensions/schema/1.0.0/), [5.0 release notes](https://developer.blender.org/docs/release_notes/5.0/) (Intel Mac dihapus), [5.1 release notes](https://developer.blender.org/docs/release_notes/5.1/) (Python 3.13)
- Blender: [System requirements](https://www.blender.org/download/requirements/) (minimum macOS 13), [VFX Reference Platform](https://vfxplatform.com/) (CY2026: Python 3.13.x, NumPy 2.3.x)
- Blender API: [`bpy.utils`](https://docs.blender.org/api/current/bpy.utils.html), [`bpy.types.Panel`](https://docs.blender.org/api/current/bpy.types.Panel.html), [`bpy.types.WorkSpace`](https://docs.blender.org/api/current/bpy.types.WorkSpace.html), [`bpy.types.WorkSpaceTool`](https://docs.blender.org/api/current/bpy.types.WorkSpaceTool.html)
- PyPI: [`manifold3d`](https://pypi.org/project/manifold3d/#files), [`trimesh`](https://pypi.org/project/trimesh/#files), [`scipy`](https://pypi.org/project/scipy/#files) (backlog §8), [`bpy`](https://pypi.org/project/bpy/5.2.0/), [`fake-bpy-module-5.2`](https://pypi.org/project/fake-bpy-module-5.2/)
- Tooling: [`pytest-blender`](https://github.com/mondeja/pytest-blender), [`blender-addon-tester`](https://pypi.org/project/blender-addon-tester/), [`setup-blender` GitHub Action](https://github.com/BradyAJohnston/setup-blender)
- `docs/RESEARCH.md` §6 (Arsitektur di Blender) dan §Roadmap (Fase 0): dasar keputusan lingkup di dokumen ini.
