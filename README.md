# DentalCAD

Extension Blender open source untuk dental CAD (crown, bridge, model). Target: **Blender 5.2 LTS** (Windows x64, macOS arm64, Linux x64). Lisensi GPL-3.0-or-later.

> **Hanya untuk riset dan edukasi.** Restorasi dari extension ini hanya untuk uji fit di die, bukan untuk dipasang ke pasien. Semua algoritma Fase 2 sejauh ini baru terbukti pada die sintetis, belum pada scan asli.

## Status

- **Fase 0** (fondasi: impor STL/PLY, panel Dental, uji Blender headless): selesai.
- **Fase 1** (model creator, kupon kalibrasi printer): diparkir. Lihat [docs/PHASE1.md](docs/PHASE1.md).
- **Fase 2** (crown zirkonia single, validasi digital): margin semi-otomatis (§5.1), sumbu insersi dan undercut (§5.2), spacer cement gap (§5.3), dan proposal crown langkah 1 sampai 5 (§5.4: template parametrik sintetis, bukan anatomi; border IVO dan solid tertutup) terimplementasi, sejauh ini hanya teruji pada data sintetis. Kontak, ketebalan, dan ekspor belum. Lihat [docs/PHASE2.md](docs/PHASE2.md).

Rancangan teknis ada di [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md), riset dan roadmap di [docs/RESEARCH.md](docs/RESEARCH.md), dan aturan kerja di [CLAUDE.md](CLAUDE.md).

## Instalasi

Build zip per platform dengan `scripts/run_blender_tests.py` (perintah di CLAUDE.md), lalu di Blender 5.2: Edit > Preferences > Get Extensions > menu ⌄ > Install from Disk, dan pilih `dist/dentalcad-<versi>-<platform>.zip`. Panel ada di N-panel 3D Viewport, tab **Dental**.

## Catatan paten (bukan kesimpulan hukum)

Pemeriksaan undercut setelah cement gap dan **block-out kedua** untuk milling 3/4 axis (§5.3) mirip dengan klaim keluarga paten Institut Straumann AG "Method for designing a tooth replacement part":

- **Eropa:** [EP2187833B1](https://patents.google.com/patent/EP2187833B1/en) menurut Google Patents masih **aktif**, dengan perkiraan berakhir **2028-07-24**.
- **AS:** [US20100233659](https://patents.google.com/patent/US20100233659) ditinggalkan (abandoned) sejak 2014.
- **Indonesia:** tidak ada anggota keluarga menurut Google Patents.
- Ringkasan halaman Google Patents juga mencantumkan anggota Jepang sebagai "pending". Daftar keluarga ini belum dicek di Espacenet atau register resmi.

**Pengguna di Eropa sebaiknya menonaktifkan block-out kedua** sampai paten berakhir: matikan opsi "Second Block-out (3/4 axis)" di panel redo "Create Cement Spacer" (`use_second_block_out=False`), atau pakai preset `milling_axes = 5`.

Status di atas berasal dari Google Patents (dicek 2026-10-24), yang menulis: "The legal status is an assumption and is not a legal conclusion." Ini bukan nasihat hukum. Rincian klaim dan paten lain yang sudah dicek ada di [docs/PHASE2.md](docs/PHASE2.md) §2.1 dan §5.3.

## Data pasien

Scan pasien asli tidak boleh di-commit (lihat [CLAUDE.md](CLAUDE.md), bagian Data pasien).
