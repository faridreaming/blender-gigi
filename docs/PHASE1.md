# Fase 1: Model Creator (rancangan)

Status: **rancangan, belum ada kode.** Keputusan K1 sampai K6 sudah diambil maintainer (§10); K5 menunggu tabel praktik lab di §9.1. Dokumen ini harus disetujui sebelum implementasi dimulai (CLAUDE.md).

Dasar dokumen ini:
- RESEARCH.md §3, baris P1 "Model cetak": alur *Trim → base (hollow/solid) → sectioned model → removable die + ditching → pin/keying → label → plug articulator → ekspor*, dengan parameter kunci *clearance die-socket 0,05-0,1 mm, tebal dinding hollow 2-3 mm, lubang drainase resin*.
- RESEARCH.md §5 (STL sebagai format ekspor utama ke slicer printer), §6 (skala 300 ribu sampai 2 juta segitiga, tanpa loop per-vertex, manifold3d untuk boolean watertight).
- RESEARCH.md Roadmap, Fase 1: deliverable *trim, base, hollow, sectioned model, removable die, ditching, label, ekspor printer*; kriteria selesai *5 model nyata tercetak, die masuk socket tanpa adjust, ditinjau teknisi senior*.
- docs/ARCHITECTURE.md (aturan `core/` tanpa bpy, Blender 5.2 LTS, wheel `manifold3d` 3.5.4 dan `trimesh` 5.1.1 yang sudah dibundel).
- Sumber pabrikan di §2, semuanya dibaca langsung pada 2026-10-23.

## 1. Aturan parameter

Setiap angka yang memengaruhi hasil cetak punya status:

| Status | Arti | Perilaku operator |
|---|---|---|
| **default pabrikan (printer lain), perlu kalibrasi** | Ada angkanya di dokumentasi pabrikan (§2), tetapi untuk printer, resin, atau software lain dari yang dipakai lab. | Jalan dengan nilai itu. Laporan ekspor mencatat bahwa nilainya belum dikalibrasi untuk printer lab. |
| **praktik lab** | Nilai dari setelan Model Creator yang dipakai lab dalam produksi (tabel §9.1, diisi maintainer). | Jalan dengan nilai itu. Laporan ekspor mencatat sumbernya. Kupon tetap memverifikasinya di printer lab: rentang kupon dipusatkan di nilai ini. |
| **perlu kalibrasi** | Tidak ada sumbernya, atau hanya rentang tanpa rujukan primer (RESEARCH.md §3). | Jalan dengan **nilai tengah rentang kupon kalibrasi** (§5.K), sambil menampilkan peringatan jelas di panel dan di laporan ekspor. Tidak menolak jalan. |
| **input pengguna** | Posisi, pilihan, atau teks yang ditentukan per kasus. | |
| **ambang uji** | Toleransi di dalam tes otomatis, bukan parameter cetak. | |

Aturan turunan:
- Preset lab `data/model_presets/<lab>.json` **tidak berisi `null`**. Setiap nilai membawa `value`, `status`, `source`, dan `source_date`; nilai "perlu kalibrasi" juga membawa `coupon_range`.
- Nilai "praktik lab" membawa `source` = "setelan Model Creator lab, <tanggal>" dan catatan definisinya di software asal, karena definisi geometri parameter yang namanya sama bisa berbeda antar software.
- Setelah kupon dicetak dan dinilai, nilai terpilih ditulis ke preset dengan `status` = "dikalibrasi" dan `source` = "kupon <tanggal>, printer <model>, resin <nama>". Peringatan untuk parameter itu hilang.
- Preset bersifat **per kombinasi printer + resin** (§3), bukan satu angka global.

## 2. Sumber pabrikan yang diverifikasi

Semua halaman di bawah dibaca langsung pada 2026-10-23. Kutipan dipendekkan.

| ID | Sumber | Isi yang dipakai |
|---|---|---|
| **MED** | Medit Help Center, "Formlab preset" (support.medit.com/hc/en-us/articles/8266196826393), diperbarui sekitar 3 tahun lalu | Model Builder, *Hollow models with drain holes*: Wall Thickness 3.0 mm, drain holes empat, diameter 4.0 mm. Juga *Solid model with extra dies*: Extra Gap from Margin 0.30 mm, Margin Trimming Depth 0.20 mm, Margin Extrusion Length 0.15 mm (lihat §5.5, belum dipakai). Preset ini untuk printer Formlabs. |
| **FLD** | Formlabs, "Application Guide: 3D Printing Diagnostic Models" (dental.formlabs.com/indications/diagnostic-models/guide/) | Bidang potong awal kira-kira 3 mm di bawah titik terendah gigi pada gingiva; slider base 3 mm menambah 3 mm material di bawah bidang potong; hollow model menghasilkan drain holes dan honeycomb otomatis; disarankan model dicetak rata di build plate. |
| **FLS** | Formlabs, "Preparing dental scans for printing with Scan to Model" (formlabs.com/support/Preparing-dental-scans-for-printing-with-Scan-to-Model/) | PreForm membuat drain holes otomatis saat model di-hollow; base ditambahkan di bawah bidang trim. **Letak lubang tidak disebut.** |
| **FLH** | Formlabs blog, "How to Hollow Out 3D Models With Meshmixer & PreForm" (formlabs.com/eu/blog/how-to-hollow-out-3d-models/) | Sisi yang paling dekat ke build platform sebaiknya sisi tempat drain hole bisa ditaruh. Artikel umum, bukan khusus dental. |
| **FLB** | Formlabs Dental blog, "PreForm Dental 3.41.0: The Latest Software Updates Powering Efficiency", 14 Okt 2024 (dental.formlabs.com/blog/preform-dental-updates/), bagian panduan hollow | Drain holes sangat disarankan untuk model hollow. **"Place the drain holes at the bottom of the model so the resin can flow out with gravity."** Terlalu banyak drain hole bisa mengurangi kekuatan struktur model. |
| **FLC** | Formlabs Support, "Cupping blowout" (formlabs.com/support/Cupping-Blowout/) | Cupping khas printer upside-down: rongga hollow atau cembung menjebak udara dan bisa jebol; Formlabs menyarankan drainage hole dan orientasi yang meminimalkan cup. |
| **UNZ** | UNIZ Support, "Detailed explanation of the restorative indication parameters" (support.uniz.com/portal/en/kb/articles/detailed-explanation-of-the-restorative-indication-parameters), diperbarui sekitar 11 bulan lalu, contoh resin zDental Model Z Tan | Hollow: dinding minimal 3 mm. Hollow implant: dicetak rata, **1-2 drainage hole di dasar model** karena tekanan vakum. Hollow removable die: support di bawah model **dan** die, kalau tidak dasar model mengalami elephant foot sehingga die sulit masuk. Solid removable die: model rata, **dasar die diberi support**. |
| **KUL** | Kulzer, "Setting Parameters exocad for cara Print 4.0" (kulzer.de, file cara_Print_Setting_Parameter_exocad_EN_10_2020.pdf, A2577 EN 11/2020, "As of 09.2020"), resin dima Print Stone beige, exocad Model Creator | DIES (Plateless Model Design): Pin height 2.5 mm, Preparation margin 0 mm, Seating width 1.5 mm, Omit die pin tidak aktif, Add concavity aktif. Base: Horizontal shaft 0 mm, Vertical shaft gap 0 mm; Ditch aktif, Ditch width 0.5 mm, Ditch depth avg. 0.5 mm; Add pin grooves aktif, Groove width 1 mm, Groove depth 0.5 mm; Hollow model aktif, Wall thickness 3 mm, Cavity fill diameter 0 mm. Catatan: "The given dimensions serve as guidelines". |
| **ANY** | Anycubic, "Standard Resin V2" (store.anycubic.com/products/standard-resin-v2) | Volume Shrinkage Rate 4.3-5.6%. Warna HD Gray tersedia. Photon P1 tercantum di tabel parameter cetak rekomendasi (layer 0,05 mm). |

Catatan verifikasi:
- **Whitepaper Stratasys x exocad Model Creator** (wp_pjd_exocad_a4_0915_web.pdf) **tidak dicantumkan**: URL prod.stratasys.com dan salinan di stratasys.com mengarah ke halaman login Microsoft, salinan DentistryIQ (Cohen-whitepaper.pdf) mengembalikan 404, dan Wayback Machine tidak punya arsipnya (dicek 2026-10-23). Isinya tidak bisa diverifikasi.
- **Pemetaan KUL ke parameter DentalCAD:** "Ditch width" → lebar ditching, "Ditch depth avg." → kedalaman ditching, dan "Pin height" → tinggi peg punya nama dan fungsi yang jelas sepadan. "Seating width" → inset peg (lebar bahu tempat die duduk di sekeliling pin) adalah **interpretasi** saya atas istilah exocad, belum dikonfirmasi. "Horizontal shaft" dan "Vertical shaft gap" (keduanya 0 mm) **tidak** dipetakan ke clearance, karena definisinya di exocad tidak dijelaskan di dokumen ini. "Preparation margin", pin grooves, dan concavity juga tidak dipetakan.
- KUL juga menulis Wall thickness 3 mm untuk hollow, jadi tebal dinding 3,0 mm kini punya tiga sumber (MED, UNZ, KUL).
- **Letak lubang drainase di dasar** ditulis eksplisit oleh dua sumber: FLB (Formlabs PreForm Dental) dan UNZ. FLS dan FLD tidak menyebut letaknya; FLD (cetak rata) dan FLH (lubang di sisi build platform) konsisten dengan keduanya.
- FLB juga memperingatkan bahwa terlalu banyak drain hole mengurangi kekuatan model. Ini satu alasan lagi untuk membandingkan konfigurasi MED (4 lubang) dan UNZ (1-2 lubang) di kupon.
- **Jumlah lubang berbeda antar pabrikan:** MED empat, UNZ 1-2. Default mengikuti MED (keputusan K1); UNZ dicatat sebagai pembanding di kupon.
- **Penyusutan ANY adalah penyusutan volume resin**, bukan galat dimensi hasil cetak per sumbu. Angka ini tidak dipakai langsung sebagai faktor skala (§5.K).

## 3. Printer dan resin lab

| Jenis | Nama | Catatan |
|---|---|---|
| Printer | Anycubic Photon P1 | Resin MSLA, cetak terbalik (upside-down), jadi cupping (FLC) relevan. |
| Printer | Shining 3D AccuFab-F1 | Resin DLP dental, cetak terbalik. |
| Resin utama | Anycubic Standard Resin V2, HD Gray | Resin umum, **bukan resin model dental**. Penyusutan volume 4,3-5,6% (ANY). |
| Resin alternatif | Anycubic Standard Resin V2 White; Anycubic Water-Wash Resin 2.0 Gray | Belum saya verifikasi spesifikasinya; perlakukan seperti resin utama (kalibrasi sendiri). |

Konsekuensi:
- Semua sumber hollow dan die di §2 ditulis untuk printer atau resin lain (Formlabs, UNIZ zDental Model Z Tan). Karena itu statusnya "default pabrikan (printer lain), perlu kalibrasi", bukan "dikalibrasi".
- Resin umum mungkin kurang stabil dimensinya dalam jangka panjang dibanding resin model dental. UNZ mengaitkan dinding 3 mm dengan menjaga model tidak berubah bentuk dalam jangka panjang. Kupon perlu diukur ulang setelah disimpan (§5.K).
- Preset dibuat per pasangan printer + resin: minimal `photon_p1_std_v2_hd_gray` dan `accufab_f1_std_v2_hd_gray`.

## 4. Lingkup

**Di dalam lingkup Fase 1:** kupon kalibrasi (fitur pertama, K4), orientasi model, trim, base solid, base hollow dengan lubang drainase, sectioned model, removable die dengan ditching, label, dan ekspor STL untuk printer resin.

**Di luar lingkup, dengan alasan:**
- **Pin/keying fisik (dowel logam) dan plug articulator.** Ada di alur RESEARCH.md §3, tetapi tidak diminta untuk Fase 1. Keying digantikan oleh bentuk peg anti-rotasi pada segmen yang bisa dilepas (§5.5). Plug articulator menunggu Fase 4.
- **Margin semi-otomatis berbasis curvature.** Roadmap menaruhnya di Fase 2. Ditching di Fase 1 memakai margin yang digambar manual (§5.5).
- **OBJ dan 3MF.** RESEARCH.md §5 menyebut keduanya untuk printer resin; Fase 1 hanya STL, 3MF masuk backlog.
- **Generator support.** Support (termasuk support di bawah die menurut UNZ) dibuat di slicer. DentalCAD hanya memberi peringatan dan mencatatnya di laporan ekspor (§5.7).

## 5. Fitur

Kerangka data untuk semua fitur:
- Satuan mm. **Frame model:** bidang oklusal sejajar XY, +Z ke oklusal. Karena model dicetak rata di build plate (K2), dasar base = bidang build plate dan Z = arah build. Ini membuat kompensasi skala per sumbu (§5.K) bisa diterapkan langsung di frame model.
- **Permukaan terbuka** (`MeshData`, scan mentah) diolah dengan numpy murni, karena `manifold3d` menolak mesh yang tidak tertutup. **Solid** (`manifold3d.Manifold`) dipakai mulai dari base. Konversi di `core/solid.py`, yang selalu memeriksa `Manifold.status()` dan melempar error bernama.
- Tidak ada dependensi baru. `manifold3d==3.5.4` ditambahkan ke `requirements-dev.txt` untuk Lapis 1. `scipy` tetap di backlog §8 ARCHITECTURE.md.

### 5.K Kupon kalibrasi (fitur pertama)

Tujuannya mengubah status "perlu kalibrasi" dan "default pabrikan (printer lain), perlu kalibrasi" menjadi nilai yang dikalibrasi untuk tiap pasangan printer + resin lab.

**Kupon yang dihasilkan** (STL siap cetak, satu set per pasangan printer + resin). Kupon 1 sampai 3 sudah diimplementasikan; kupon 4 dan 5 belum (lihat di bawah). Penanda pada kupon berupa titik timbul atau takik, bukan teks, karena ukuran label belum punya sumber (§9.1). Semua ukuran bertanda "desain kupon" di bawah adalah bentuk benda uji, bukan parameter cetak model; nilainya ada di `core/calibration.py` dan dicatat di laporan kupon.
1. **Kupon dimensi dan penyusutan per sumbu:** piramida bertingkat 4 lapis, persegi 40, 30, 20, dan 10 mm, tiap lapis setinggi 3 mm (desain kupon). Satu takik vertikal di sisi +X dan dua takik di sisi +Y lapis terbawah menandai arah sumbu. Dicetak rata di build plate. Teknisi mengukur lebar X dan Y setiap lapis di tengah tinggi lapisnya (menghindari elephant foot di lapis pertama) dan tinggi Z puncak setiap lapis. Dengan empat ukuran nominal per sumbu, `fit_scale` mencocokkan *terukur = a × nominal + b* per sumbu: faktor kompensasi skala = 1/a, dan b dilaporkan sebagai offset (misalnya akibat overcure), yang tidak dikompensasi oleh skala. Ukur sekali setelah post-curing dan sekali lagi setelah disimpan (stabilitas resin umum, §3).
2. **Kupon clearance:** satu blok base dengan socket untuk setiap nilai clearance, ditambah die terpisah untuk setiap socket. Nilai clearance = sapuan rentang kupon preset (RESEARCH.md §3, 0,05-0,1 mm) dengan langkah setengah rentang, plus satu langkah di bawah dan di atas: 0,025, 0,05, 0,075, 0,1, dan 0,125 mm. Die: badan 8 × 8 × 5 mm (desain kupon), peg persegi = badan dikurangi inset peg di tiap sisi, setinggi tinggi peg (keduanya dari preset: KUL Seating width 1,5 mm dan Pin height 2,5 mm). Socket = jejak peg yang di-offset 2D sebesar clearance dengan join miter (celah tepat c di setiap sisi, √2·c di sudut; join bulat akan mendekati busur dengan segmen sehingga celah sudut sedikit di bawah c), sedalam tinggi peg + celah dasar 1,0 mm (desain kupon), supaya die duduk di bahunya. Die ke-i dan socket ke-i ditandai i titik. Base dicetak rata (socket menghadap ke atas, jauh dari build plate); **setiap die dicetak dengan support di bawahnya** (UNZ), dan ini tertulis di nama file dan laporan. Teknisi menilai setiap pasangan: masuk tanpa adjust, longgar, atau tidak masuk.
3. **Kupon hollow:** kotak 30 × 20 × 12 mm (desain kupon) dengan rongga tertutup kecuali lubang drainase di dasar. Lima kotak: dinding 2,0, 2,5, dan 3,0 mm (rentang RESEARCH.md §3, dengan 3,0 mm dari MED, UNZ, dan KUL), masing-masing dengan konfigurasi lubang preset (MED: 4 × Ø 4,0 mm), ditambah dinding 3,0 mm dengan 2 dan 1 lubang Ø 4,0 mm (jumlah dari UNZ; UNZ tidak menyebut diameter, jadi dipakai diameter MED). Kotak ke-i ditandai i titik di atasnya. Dicetak rata, lubang menempel ke build plate (K2). Teknisi mencatat cupping/blowout (FLC), resin terjebak, dan deformasi dinding.
4. **Kupon label dan ditching: belum.** Ukuran label tidak punya sumber sama sekali (§9.1 masih kosong). Ditching punya angka KUL, tetapi jarak tepi ditching ke margin belum punya sumber, dan geometri ditching baru dibangun di §5.5.
5. **Kupon peg: belum.** Celah dasar socket belum punya sumber; inset dan tinggi peg dari KUL sudah dipakai di kupon 2 sebagai titik tengah.

**Lembar ukur dan penerapan.** Bersama STL, ekspor kupon menulis `kupon_lembar_ukur.csv` (setiap ukuran nominal yang harus diukur, kolom hasil kosong) dan `kupon_laporan.json` (preset, nilai parameter beserta sumber, ukuran desain kupon, dan SHA-256 setiap STL). Setelah diisi, `scripts/apply_calibration.py` menghitung faktor skala per sumbu dari lembar ukur dan, dengan `--write`, menulisnya ke preset dengan status "dikalibrasi" beserta sumbernya. Pilihan clearance, tebal dinding, dan jumlah lubang dari kupon 2 dan 3 dicatat dengan opsi baris perintah, karena itu penilaian teknisi, bukan hasil hitungan.

**Rentang kupon** untuk parameter tanpa sumber pabrikan (margin base, kerf, bidang pisah, celah dasar peg, jarak ditching ke margin, label) dipusatkan di nilai praktik lab dari tabel §9.1 (K5). Parameter yang punya angka KUL (tinggi dan inset peg, lebar dan kedalaman ditching) memakai angka itu sampai nilai praktik lab mengisinya.

**Parameter.**

| Parameter | Status | Nilai awal | Sumber |
|---|---|---|---|
| Faktor kompensasi skala X, Y, Z | perlu kalibrasi | 1,0 (tanpa kompensasi) sampai kupon 1 diukur | Penyusutan volume ANY 4,3-5,6% hanya konteks, bukan faktor skala. |
| Ukuran benda uji (piramida, badan die, kotak hollow, celah dasar kupon, titik penanda) | desain kupon | lihat daftar kupon di atas | Bentuk benda uji, bukan parameter cetak model. |
| Sapuan clearance | dari preset | 0,025 sampai 0,125 mm, langkah 0,025 | Rentang kupon RESEARCH.md §3 (0,05-0,1 mm) + satu langkah di luar. |
| Sapuan tebal dinding | dari preset | 2,0, 2,5, 3,0 mm | Rentang kupon RESEARCH.md §3 (2-3 mm). |

Faktor skala diterapkan saat ekspor (§5.7) dan dicatat di laporan. Kalau slicer lab juga mengompensasi, salah satunya harus dimatikan supaya tidak terkompensasi dua kali. Itu tertulis di peringatan ekspor.

**Modul core/.** `core/calibration.py` (geometri kupon, lembar ukur, `fit_scale`), `core/model_presets.py` (preset printer + resin dengan status per parameter), `core/solid.py` (konversi dan validasi Manifold), `core/mesh_io.py` (`save_stl` biner dengan header disclaimer). ops/: `DENTALCAD_OT_export_coupons`. Data: `data/model_presets/*.json`. Skrip: `scripts/apply_calibration.py`.

**Pengujian.**
- Lapis 1: setiap kupon watertight dan lolos pemeriksaan siap cetak; dimensi nominal blok kupon sesuai desain (ambang uji dari toleransi manifold3d); perhitungan faktor skala dari data ukur sintetis menghasilkan faktor yang benar.
- Lapis 1: preset yang memuat nilai kalibrasi menghapus peringatan untuk parameter itu.
- Manual: cetak di kedua printer, ukur, isi preset.

### 5.0 Orientasi model (prasyarat trim dan base)

**Algoritma.**
1. Normal oklusal awal = arah sumbu varian terkecil dari PCA vertex scan (SVD 3x3 atas kovarians).
2. Tanda arah diambil dari rata-rata normal face berbobot luas: normal oklusal dibuat searah dengannya, karena permukaan scan menghadap ke alat scan, yaitu ke sisi oklusal.
3. Rotasi ke frame model (Rodrigues), lalu translasi supaya titik terendah batas scan di z = 0.
4. Pengguna bisa mengoreksi lewat gizmo di Blender; core hanya menerima matriks akhir.

**Parameter.** Tidak ada parameter cetak.

**Modul core/.** `core/orient.py` (`estimate_occlusal_frame(mesh) -> Frame`, `apply_frame`).

**Pengujian.**
- Lapis 1: lengkung sintetis (§6.1) diputar dengan rotasi acak yang diketahui; sudut antara normal hasil estimasi dan normal sebenarnya ≤ 1° (ambang uji). Tanda arah benar untuk rahang atas dan bawah.
- Lapis 2: operator orientasi di golden case menghasilkan objek dengan matriks yang sama dengan core (selisih ≤ 1e-6, ambang uji).

### 5.1 Trim

**Algoritma.** Satu mesin clipping umum untuk permukaan terbuka: setiap edge mesh punya parameter potong `t`, dan segitiga yang terbelah dipecah tepat di titik itu.
1. **Trim bidang:** jarak bertanda `d = n·v - c` per vertex. Edge yang ujungnya beda tanda punya `t = d_a / (d_a - d_b)`. Posisi bidang default: 3 mm di bawah titik terendah gigi pada gingiva (FLD). Fase 1 belum punya segmentasi gigi, jadi titik terendah gigi diklik pengguna; bidang lalu ditaruh 3 mm di bawahnya, sejajar bidang oklusal.
2. **Trim kurva:** pengguna menggambar poligon tertutup di viewport; ops/ mengirim poligon 2D dan matriks proyeksi view. Vertex diproyeksikan, status dalam/luar dihitung dengan uji crossing (vektorisasi numpy), dan `t` per edge yang menyeberang dihitung dari perpotongan segmen edge terproyeksi dengan sisi poligon (perpotongan pertama).
3. Vertex baru pada edge yang sama dibuat sekali (kunci edge terurut, seperti `merge_exact_vertices` di Fase 0), jadi garis potong rapat tanpa celah. Segitiga yang tersisa satu sudut menjadi 1 segitiga, yang tersisa dua sudut menjadi 2 segitiga.
4. **Bersihkan:** komponen terhubung via union-find dengan pointer jumping di numpy. Komponen terbesar dipertahankan, komponen lain dilaporkan ke pengguna untuk dikonfirmasi (bukan dihapus diam-diam), jadi tidak butuh ambang ukuran.
5. **Tutup lubang dalam:** semua loop batas kecuali loop terluar ditutup dengan ear clipping setelah diproyeksikan ke bidang rata-ratanya (`manifold3d.triangulate`). Loop terluar dibiarkan terbuka, karena itu tepi trim untuk base.

**Parameter.**

| Parameter | Status | Nilai | Sumber |
|---|---|---|---|
| Jarak bidang trim di bawah titik terendah gigi | default pabrikan (printer lain), perlu kalibrasi | 3 mm | FLD |
| Titik terendah gigi | input pengguna | klik | |
| Ukuran minimum komponen yang dibuang | tidak dipakai | | Diganti konfirmasi pengguna (langkah 4). |
| Ukuran maksimum lubang yang ditutup | tidak dipakai | | Semua lubang dalam ditutup (langkah 5). |

**Modul core/.** `core/topology.py` (pasangan edge-face, loop batas, komponen terhubung), `core/trim.py` (`clip_by_plane`, `clip_by_polygon`, `fill_inner_holes`), `core/mesh_validate.py` (sudah ada).

**Pengujian.**
- Lapis 1, analitis: icosphere radius r dipotong bidang z = h. Semua vertex hasil ada di sisi yang benar, loop batasnya satu, dan jarak titik loop ke sumbu z sama dengan √(r² - h²) ± kesalahan tali busur icosphere (ambang uji dihitung dari panjang edge). Luas permukaan mendekati luas tutup bola analitis.
- Lapis 1, sifat: hasil trim tidak punya edge non-manifold; trim dengan bidang di luar bbox tidak mengubah mesh; trim kurva berupa persegi pada heightfield datar menghasilkan luas persis persegi itu; bidang default berada tepat 3 mm di bawah titik yang diklik.
- Lapis 1, regresi: komponen kecil sintetis (pulau terpisah) dilaporkan, bukan dihapus.
- Lapis 2: operator trim pada lengkung sintetis dan golden case privat; hasil divalidasi oleh fungsi core yang sama.

### 5.2 Base solid

**Algoritma.**
1. Ambil loop batas terluar hasil trim, proyeksikan ke XY.
2. **Uji poligon sederhana:** loop terproyeksi tidak boleh memotong dirinya (uji segmen vektorisasi, dipecah per blok). Kalau gagal, berarti ada overhang di tepi trim; operator berhenti dan meminta trim ulang sedikit lebih tinggi, bukan memaksa geometri. Ini risiko S2 (§7).
3. **Skirt:** setiap vertex batas dihubungkan lurus ke bawah ke bidang trim, membentuk dinding pita segitiga; dasarnya ditutup dengan triangulasi poligon terproyeksi. Hasilnya solid tertutup yang mengikuti scan.
4. **Blok base:** `CrossSection` dari poligon terproyeksi (fill rule positif) → `offset(+margin_base, JoinType.Round)` → `simplify` → `extrude(tinggi_base)` ke bawah dari bidang trim, sesuai FLD (base ditambahkan di bawah bidang potong).
5. Model = skirt ∪ blok base (`Manifold.batch_boolean`). Periksa: `status()` tanpa error, watertight, `genus() == 0`, volume positif, tidak ada komponen terpisah (`decompose()` panjangnya 1).
6. Dasar blok base rata dan menjadi bidang kontak build plate (K2).

**Parameter.**

| Parameter | Status | Nilai | Sumber |
|---|---|---|---|
| Tinggi base di bawah bidang trim | default pabrikan (printer lain), perlu kalibrasi | 3 mm | FLD |
| Margin base di luar outline lengkung | praktik lab | §9.1 | setelan Model Creator lab (K5) |
| Tumpang tindih skirt ke dalam blok base | ambang geometri | dari `get_tolerance()` | Bukan parameter cetak; cukup > toleransi manifold3d. |

**Modul core/.** `core/solid.py` (konversi dan validasi Manifold), `core/base.py` (`build_skirt`, `build_base_block`, `build_solid_model`), `core/topology.py`.

**Pengujian.**
- Lapis 1, analitis: heightfield datar persegi a × b pada z = H menghasilkan model dengan volume `a·b·H` ditambah volume blok base dari offset bulat (luas offset `a·b + 2(a+b)·m + π·m²` dikali tinggi base) ± ambang uji relatif dari segmen lingkaran.
- Lapis 1, sifat: hasil watertight dan genus 0 untuk lengkung sintetis; dasar base rata pada z minimum; tepi trim yang sengaja dibuat overhang ditolak dengan error bernama.
- Lapis 2: operator base pada lengkung sintetis; bbox dan volume sama dengan hasil core.

### 5.3 Base hollow dengan lubang drainase

**Syarat (K6):** opsi hollow **dinonaktifkan** kalau model punya removable die atau segmen yang bisa dilepas (§5.4, §5.5). Model seperti itu selalu solid dan dicetak rata. Di UI tombolnya abu-abu dengan alasannya; di core, `build_cavity` menolak model yang punya socket dengan error bernama.

**Algoritma.** Kandidat utama, yang harus dibuktikan dulu lewat spike S1 (§7):
1. **Voxelisasi:** grid jarak h di atas bbox model plus bantalan. Okupansi dihitung per lapisan z dengan `Manifold.slice(z)` (C++, cepat dan tahan karena model sudah manifold), lalu poligonnya dirasterisasi dengan scanline: per baris y, titik silang semua edge dihitung serentak, diurutkan, dan interval di dalam diisi.
2. **Jarak ke luar:** transformasi jarak Euclidean kuadrat yang separable per sumbu, dengan jendela terbatas sebesar tebal dinding. Hasilnya eksak untuk jarak sampai tebal dinding, tanpa scipy, dan biayanya O(voxel × jendela).
3. **Rongga** = isosurface jarak = tebal dinding, dibuat dengan `Manifold.level_set` memakai interpolasi trilinear grid sebagai fungsi jaraknya. Bagian yang lebih tipis dari 2 × tebal dinding otomatis tidak berongga.
4. Model hollow = model − rongga.
5. **Lubang drainase di dasar model** (K2, FLB, UNZ): silinder vertikal (`Manifold.cylinder`) dari bidang dasar base menembus lantai ke rongga. Posisi: pilih titik di jejak rongga pada lantai dengan farthest point sampling, supaya lubang tersebar sejauh mungkin satu sama lain di sepanjang lengkung tanpa butuh angka jarak. Setiap titik harus berada cukup jauh dari tepi jejak rongga supaya silinder seluruhnya membuka ke rongga.
6. **Verifikasi:**
   - Tebal dinding tercapai = `rongga.min_gap(eksterior, cari)`, dengan eksterior = kotak bbox − model, harus ≥ tebal dinding − h.
   - Tidak ada rongga tertutup (resin terjebak, dan sumber cupping menurut FLC): `(kotak − model_hollow).decompose()` harus satu komponen.
   - Setiap lubang drainase memotong rongga: `ray_cast` sepanjang sumbu lubang.

Alternatif kalau S1 gagal: erosi dengan `minkowski_difference` terhadap bola, pada salinan model yang disederhanakan (`simplify`). Dokumentasi manifold3d memperingatkan biayanya naik dengan perkalian jumlah face untuk bentuk non-konveks, jadi ini hanya cadangan.

**Parameter.**

| Parameter | Status | Nilai | Sumber |
|---|---|---|---|
| Tebal dinding hollow | default pabrikan (printer lain), perlu kalibrasi | 3,0 mm | MED; UNZ (minimal 3 mm); KUL. RESEARCH.md §3 menyebut 2-3 mm tanpa rujukan. |
| Jumlah lubang drainase | default pabrikan (printer lain), perlu kalibrasi | 4 | MED. UNZ menyebut 1-2; dibandingkan di kupon. |
| Diameter lubang drainase | default pabrikan (printer lain), perlu kalibrasi | 4,0 mm | MED |
| Letak lubang drainase | default pabrikan | dasar model | FLB dan UNZ (keduanya eksplisit); konsisten dengan FLD dan FLH |
| Sebaran lubang | algoritma | farthest point sampling | Tanpa angka jarak. |
| Jarak voxel h | perlu kalibrasi (akurasi vs waktu) | dari spike S1 | Parameter komputasi, bukan klinis; syaratnya h jauh lebih kecil dari tebal dinding. |

**Modul core/.** `core/voxel.py` (okupansi per lapisan, EDT berjendela), `core/hollow.py` (`build_cavity`, `place_drain_holes`, `verify_hollow`), `core/solid.py`.

**Pengujian.**
- Lapis 1, analitis: kotak a × b × c dengan tebal dinding w menghasilkan rongga ≈ kotak (a-2w)(b-2w)(c-2w); volume rongga dan `min_gap` sesuai dalam ambang uji yang bergantung pada h. Bola radius R menghasilkan rongga bola radius R - w.
- Lapis 1, K6: model yang punya socket removable die ditolak oleh `build_cavity` dengan error bernama.
- Lapis 1, sifat: bagian yang lebih tipis dari 2w tetap solid; tanpa lubang drainase, pemeriksaan rongga tertutup **gagal** (tes negatif); dengan 4 lubang Ø 4,0 mm di dasar, lulus; semua lubang ada di bidang dasar dan masing-masing memotong rongga.
- Lapis 1, performa: anggaran waktu ditetapkan setelah spike S1, lalu dikunci sebagai tes.
- Kupon hollow (§5.K) untuk dinding, jumlah dan diameter lubang, dan cupping.

### 5.4 Sectioned model

**Algoritma.**
1. Pengguna menaruh bidang potong di antara gigi. Bidang default: vertikal, normalnya searah garis singgung lengkung di titik klik. Garis lengkung diambil dari kurva tengah outline base (titik tengah pasangan sisi bukal dan lingual hasil `slice` setinggi bidang base).
2. Model dipecah dua secara horizontal di bidang pisah (`split_by_plane`): bagian atas (dentition) dan bawah (base).
3. Bagian atas dipecah di setiap bidang potong; celah potong (kerf) dibuat dengan mengurangkan lempeng setebal kerf, supaya segmen lepas tanpa saling menempel.
4. Setiap segmen yang ditandai "bisa dilepas" diberi peg dan socket dengan mekanisme yang sama dengan die (§5.5). Segmen yang tidak dilepas disatukan kembali dengan base.
5. Karena mekanismenya sama dengan removable die, aturan K6 juga berlaku: model yang punya segmen bisa dilepas selalu solid, dan segmen itu diekspor sebagai bagian terpisah dengan catatan support (§5.7).

**Parameter.**

| Parameter | Status | Nilai | Sumber |
|---|---|---|---|
| Lebar kerf antar segmen | praktik lab | §9.1 | setelan Model Creator lab (K5) |
| Tinggi bidang pisah horizontal | praktik lab | §9.1 | setelan Model Creator lab (K5) |
| Posisi bidang potong | input pengguna | | |

**Modul core/.** `core/section.py` (`arch_curve`, `default_cut_plane`, `split_sections`), `core/solid.py`.

**Pengujian.**
- Lapis 1: lengkung sintetis dengan k bidang potong menghasilkan k+1 segmen; jumlah volume segmen + volume kerf = volume bagian atas (ambang uji relatif); setiap segmen watertight; dua segmen bertetangga punya `min_gap` = kerf (ambang uji dari toleransi manifold3d).
- Lapis 2: operator section pada lengkung sintetis; objek hasil satu per segmen, nama mengikuti nomor FDI kalau pengguna mengisinya (`core/units.py`).

### 5.5 Removable die dengan ditching

Die adalah segmen yang bisa dilepas (§5.4) yang berisi gigi preparasi, ditambah ditching di bawah margin.

**Algoritma, peg dan socket.**
1. Jejak segmen = `slice` di bidang pisah → `CrossSection`.
2. Peg = jejak.`offset(-inset_peg)` → `extrude(tinggi_peg)` ke bawah. Bentuk jejak gigi tidak bulat, jadi peg sudah anti-rotasi. Kalau jejaknya mendekati lingkaran (diukur dari rasio luas terhadap lingkaran luar), satu sisi dipotong datar supaya tetap anti-rotasi; ini pengganti pin/keying di §4.
3. Socket di base = base − (jejak.`offset(-inset_peg + clearance)` → `extrude(tinggi_peg + celah_dasar)`). Clearance dibuat di 2D, jadi tepat sama di seluruh keliling. Celah dasar memastikan die duduk di bahunya (bidang pisah), bukan di ujung peg, sehingga posisi vertikal ditentukan oleh bahu. Celah dasar juga memberi ruang untuk support di bawah die (UNZ).
4. Taper peg: versi pertama lurus. Taper baru ditambahkan kalau kupon menunjukkan die sulit dipasang, karena `extrude(scale_top=...)` menskala terhadap titik asal, bukan offset seragam, sehingga clearance jadi tidak seragam.
5. **Verifikasi:** `peg.min_gap(socket_base, cari)` sama dengan clearance (ambang uji dari toleransi manifold3d); die dan base tidak saling tumpang (volume interseksi 0).

**Algoritma, margin manual dan ditching.**
1. **Margin manual:** pengguna mengklik titik di permukaan die; antar titik disambung jalur terpendek di graf edge mesh (Dijkstra dengan bobot panjang edge, `heapq`, hanya di region die). Ini bukan margin semi-otomatis Fase 2, karena biayanya panjang edge, bukan curvature.
2. **Alat ditching:** sapuan profil sepanjang loop margin, di bawah margin. Dibuat sebagai `Manifold.batch_hull` per pasangan titik berurutan (dua silinder kecil per segmen), lalu disatukan dengan `batch_boolean`.
3. Die = die − alat ditching.
4. **Verifikasi:** titik-titik margin tetap berada di permukaan die setelah ditching (jarak ke permukaan ≈ 0, ambang uji), artinya margin tidak ikut terkikis; region di bawah margin sedalam ditching benar-benar terkikis (sampel ray cast).

**Catatan cetak (UNZ, keputusan K6).** UNZ membedakan dua kasus: *solid + removable die* (model dicetak rata di build plate, hanya die yang diberi support) dan *hollow + removable die* (model dan die perlu support). Keputusan K6 memakai kasus pertama, jadi tidak ada konflik dengan K2:
- Model yang punya removable die **selalu solid** dan dicetak rata di build plate. Opsi hollow dinonaktifkan (§5.3).
- Die diekspor sebagai **bagian terpisah** dengan catatan "beri support di slicer" di nama bagian, panel ekspor, dan laporan (§5.7), supaya elephant foot tidak mengubah ukuran dasar die.

**Parameter.**

| Parameter | Status | Nilai | Sumber |
|---|---|---|---|
| Clearance die-socket | perlu kalibrasi | 0,075 mm (tengah rentang kupon) + peringatan | Rentang kupon dari RESEARCH.md §3 (0,05-0,1 mm, tanpa rujukan primer). |
| Inset peg dari jejak segmen | default pabrikan (printer lain), perlu kalibrasi | 1,5 mm | KUL "Seating width" (pemetaan interpretasi, §2); praktik lab §9.1 menimpanya |
| Tinggi peg | default pabrikan (printer lain), perlu kalibrasi | 2,5 mm | KUL "Pin height"; praktik lab §9.1 menimpanya |
| Celah dasar socket | praktik lab | §9.1 | setelan Model Creator lab (K5) |
| Sudut taper peg | perlu kalibrasi | tidak dipakai (lurus) | Langkah 4. |
| Kedalaman ditching | default pabrikan (printer lain), perlu kalibrasi | 0,5 mm | KUL "Ditch depth avg."; praktik lab §9.1 menimpanya. MED "Margin Trimming Depth" tidak dipakai (lihat bawah). |
| Lebar ditching | default pabrikan (printer lain), perlu kalibrasi | 0,5 mm | KUL "Ditch width"; praktik lab §9.1 menimpanya |
| Jarak tepi atas ditching ke margin | praktik lab | §9.1 | setelan Model Creator lab (K5); MED "Extra Gap from Margin" tidak dipakai (lihat bawah). |

**Kandidat sumber dari MED, belum dipakai.** Preset Medit untuk Formlabs, bagian *Solid model with extra dies*, mengisi Extra Gap from Margin 0.30 mm, Margin Trimming Depth 0.20 mm, dan Margin Extrusion Length 0.15 mm. Namanya mirip parameter ditching, tetapi artikel itu tidak menjelaskan definisi geometrinya, dan algoritma Medit tidak terbuka. Memetakannya ke parameter di atas berarti menebak, jadi angka ini **tidak** dipakai. Keputusan K5: parameter ditching memakai nilai praktik lab (§9.1).

**Modul core/.** `core/die.py` (`build_peg`, `cut_socket`, `verify_fit`), `core/margin_path.py` (`shortest_path`, `close_loop`), `core/ditch.py` (`ditch_tool`, `apply_ditch`, `verify_ditch`), `core/solid.py`.

**Pengujian.**
- Lapis 1, analitis: segmen kotak dengan clearance c menghasilkan `min_gap` = c; volume socket − volume peg = keliling × tinggi × c + luas × celah dasar (pendekatan orde pertama, ambang uji relatif).
- Lapis 1, margin: pada silinder dengan chamfer sintetis, jalur terpendek antara titik di tepi chamfer mengikuti tepi chamfer (panjang ≈ busur lingkaran, ambang uji dari panjang edge).
- Lapis 1, ditching: die sintetis (silinder dengan bahu chamfer) setelah ditching; titik margin tetap di permukaan, dan volume terkikis ≈ panjang loop × luas profil (ambang uji relatif).
- Lapis 1, negatif: clearance negatif atau peg lebih besar dari socket ditolak dengan error bernama.
- Lapis 1, peringatan: menjalankan die dengan clearance tengah rentang kupon menghasilkan peringatan untuk clearance; parameter praktik lab tercatat sumbernya di laporan tanpa peringatan "belum dikalibrasi".
- Kupon clearance dan peg (§5.K), lalu kriteria roadmap "die masuk socket tanpa adjust" (§6.3).

### 5.6 Label

**Algoritma.**
1. ops/ membuat objek teks Blender dengan font bawaan Blender, mengonversinya ke mesh, lalu mengirim **poligon 2D** (loop batas glyph) ke core. core tidak tahu soal font.
2. **Posisi default: dinding samping base, bagian posterior/lingual (K3)**, bukan dasar. Dasar base adalah bidang kontak build plate dan tempat lubang drainase (K2). core mencari patch dinding samping yang cukup datar untuk teks: kandidat diambil dari dinding blok base di sisi lingual pada region posterior lengkung, dengan kerataan diperiksa lewat fit bidang (penyimpangan maksimum ≤ kedalaman label, sebagai ambang geometri). Kalau tidak ada patch yang cukup datar, label ditaruh di ujung posterior base, dan pengguna diberi tahu.
3. core: poligon → `CrossSection` (fill rule even-odd untuk lubang huruf seperti "O") → skala ke tinggi teks → `extrude(kedalaman)` → ditempatkan di patch terpilih.
4. Mode ukir (model − teks) atau timbul (model ∪ teks).
5. **Verifikasi:** model tetap watertight; volume yang berubah ≈ luas teks × kedalaman (ambang uji); teks tidak menembus ke rongga hollow (`min_gap` teks ke rongga > 0); teks tidak mencapai bidang dasar.
6. **Privasi:** isi label default adalah nomor kasus, bukan nama pasien. UI memperingatkan kalau isi label mirip nama, sejalan dengan aturan anonimisasi di CLAUDE.md dan RESEARCH.md.

**Parameter.**

| Parameter | Status | Nilai | Sumber |
|---|---|---|---|
| Posisi default | keputusan maintainer | dinding samping base, posterior/lingual | K3 |
| Tinggi huruf | praktik lab | §9.1 | setelan Model Creator lab (K5) |
| Kedalaman ukir/timbul | praktik lab | §9.1 | setelan Model Creator lab (K5) |
| Mode ukir/timbul | input pengguna | | |

**Modul core/.** `core/label.py` (`find_wall_patch`, `polygons_to_solid`, `place_on_patch`, `apply_label`, `verify_label`), `core/solid.py`.

**Pengujian.**
- Lapis 1: poligon sintetis (persegi, dan persegi dengan lubang seperti huruf "O") diukir pada kotak; volume yang hilang = (luas luar − luas lubang) × kedalaman (ambang uji dari toleransi); hasil watertight.
- Lapis 1, posisi: pada base lengkung sintetis, patch default berada di dinding samping sisi lingual region posterior, tidak di bidang dasar; base tanpa patch datar memakai fallback ujung posterior.
- Lapis 1, negatif: label yang menembus rongga hollow ditolak.
- Lapis 2: operator label memakai font bawaan Blender; jumlah loop poligon untuk teks "A1" sesuai bentuk glyph (3 loop: badan "A", lubang "A", dan "1").
- Kupon label (§5.K) untuk tinggi dan kedalaman yang terbaca.

### 5.7 Ekspor STL untuk printer resin

**Algoritma.**
1. Satu STL biner per bagian (base, setiap segmen atau die), ditambah opsi satu file gabungan. Nama file: `<nomor_kasus>_<bagian>.stl`, tanpa data pasien. Die dan segmen yang bisa dilepas selalu menjadi file sendiri, tidak pernah digabung dengan base.
2. **Frame ekspor:** frame model, dengan dasar base di z = 0 (rata di build plate, K2).
3. **Kompensasi skala:** faktor X, Y, Z dari preset printer + resin (§5.K) diterapkan terhadap titik asal di tengah dasar model. Faktor 1,0 berarti tidak ada kompensasi.
4. Header STL 80 byte berisi disclaimer singkat sesuai RESEARCH.md §7, misalnya `DentalCAD research/education only. Not a certified medical device.`.
5. **Pemeriksaan siap cetak** sebelum menulis file. Kalau ada yang gagal, ekspor ditolak dengan daftar alasannya:
   - setiap bagian watertight, tanpa edge non-manifold, `status()` tanpa error, volume positif;
   - kalau hollow: tidak ada rongga tertutup, tebal dinding tercapai, dan semua lubang drainase di dasar memotong rongga (§5.3);
   - kalau ada die/segmen: clearance terukur (`min_gap`) sesuai preset, dan model tidak hollow (K6).
6. **Peringatan (tidak menolak ekspor):**
   - setiap parameter berstatus "perlu kalibrasi" atau "default pabrikan (printer lain), perlu kalibrasi", dengan nilai yang dipakai;
   - faktor skala masih 1,0 (belum dikalibrasi), atau sudah dikalibrasi tetapi slicer mungkin juga mengompensasi;
   - setiap die dan segmen yang bisa dilepas: catatan "beri support di slicer" di bawah dasarnya (UNZ, K6). Ini catatan cetak, bukan tanda ada yang salah.
7. **Laporan ekspor** `<nomor_kasus>_report.json`: versi DentalCAD, printer dan resin preset, nilai setiap parameter beserta `status`/`source`, faktor skala, metrik pemeriksaan, daftar peringatan, dan hash SHA-256 setiap STL. Ini jejak dokumentasi untuk lab sebagai produsen custom-made device (RESEARCH.md §7).

**Parameter.** Faktor skala dari §5.K. Format STL biner dan satuan mm mengikuti RESEARCH.md §5 dan ARCHITECTURE.md.

**Modul core/.** `core/export.py` (`check_print_ready`, `collect_warnings`, `apply_scale_compensation`, `write_parts`, `write_report`), `core/mesh_io.py` (penulis STL biner diperluas dengan header khusus), `core/mesh_validate.py`.

**Pengujian.**
- Lapis 1: round trip ekspor → `load_mesh` → metrik sama; header berisi disclaimer; laporan JSON valid dan hash-nya cocok dengan file.
- Lapis 1, skala: kubus dengan faktor (sx, sy, sz) menghasilkan bbox yang terskala tepat per sumbu dan dasar tetap di z = 0.
- Lapis 1, negatif: model dengan rongga tertutup atau clearance di luar preset ditolak, dan tidak ada file yang ditulis.
- Lapis 1, peringatan: preset dengan nilai belum dikalibrasi menghasilkan peringatan yang tepat, dan ekspor tetap jalan.
- Lapis 2: alur penuh di Blender (impor → orientasi → trim → base → section/die → label → ekspor) pada lengkung sintetis dan golden case privat; zip extension tetap lolos `check_zip`.

## 6. Strategi uji keseluruhan

### 6.1 Data uji
- **Lengkung sintetis** (dibuat oleh `scripts/make_synthetic_golden.py`, diperluas): heightfield berbentuk tapal kuda dengan tonjolan gigi, sebagai permukaan terbuka seperti scan. Varian: rahang atas, rahang bawah, satu gigi preparasi (silinder dengan bahu chamfer) untuk die, dan satu varian dengan overhang di tepi trim (tes negatif base). Nilai expected dihitung dari definisi analitis, bukan lewat `core/`.
- **Scan nyata** di `tests/golden_private/` (tidak di-commit), dengan expected dari alat independen seperti di Fase 0.

### 6.2 Kalibrasi
Kupon (§5.K) dicetak di Anycubic Photon P1 dan Shining 3D AccuFab-F1 dengan resin utama. Hasilnya mengisi preset per pasangan printer + resin.

### 6.3 Kriteria selesai Fase 1
Dari roadmap:
- 5 model nyata tercetak.
- Die masuk socket tanpa adjust.
- Ditinjau teknisi senior.

Ditambah:
- Preset untuk kedua printer lab sudah dikalibrasi lewat kupon: faktor skala X/Y/Z, clearance, dan hollow (dinding, lubang). Parameter lain boleh masih "perlu kalibrasi" asalkan muncul di peringatan.
- Semua tes Lapis 1 dan Lapis 2 lulus di CI (Windows, macOS, Linux).
- Alur penuh pada lengkung sintetis selesai di Blender 5.2 LTS dalam anggaran waktu yang ditetapkan dari spike S1.
- Setiap STL ekspor lolos pemeriksaan siap cetak dan punya laporan JSON.

## 7. Spike dan risiko (dikerjakan sebelum fitur terkait)

| ID | Pertanyaan | Cara menjawab | Kalau gagal |
|---|---|---|---|
| S1 | Apakah hollow berbasis voxel + `level_set` cukup cepat dan akurat untuk model lengkung penuh? | Ukur waktu dan memori untuk beberapa jarak voxel pada lengkung sintetis dan satu scan privat; catat tebal dinding tercapai. | Coba `minkowski_difference` pada model yang disederhanakan; kalau keduanya gagal, hollow hanya untuk bagian base (bukan dentition). |
| S2 | Seberapa sering tepi trim scan nyata menghasilkan proyeksi yang memotong dirinya (overhang)? | Jalankan uji poligon sederhana (§5.2 langkah 2) pada scan privat. | Tambah opsi "rapikan tepi trim" (trim ulang otomatis sedikit lebih tinggi, dengan konfirmasi pengguna). |
| S3 | Apakah `Manifold` dari skirt scan nyata selalu valid (tanpa self-intersection yang membuat boolean gagal)? | Bangun base untuk semua scan privat, periksa `status()` dan genus. | Perbaiki self-intersection lokal di tepi trim sebelum skirt, atau perbesar tumpang tindih skirt. |
| R1 | Scan 1-2 juta segitiga membuat boolean dan Dijkstra lambat. | Ukur di S1/S3; Dijkstra dibatasi ke region die. | Sederhanakan (`simplify`) hanya di luar region kerja, sesuai saran RESEARCH.md §6. |
| R2 | Clearance hasil cetak menyimpang dari desain karena printer dan resin. | Kupon clearance dan dimensi (§5.K). | Preset per printer + resin. |
| R3 | Cupping atau blowout pada model hollow rata di plate dengan lubang di dasar, di printer terbalik lab (FLC). | Kupon hollow (§5.K) di kedua printer. | Ubah konfigurasi lubang (jumlah/diameter, bandingkan MED dan UNZ) atau tambah lubang ventilasi; dicatat di preset. |
| R4 | Elephant foot di dasar die atau socket membuat die sulit masuk (UNZ). | Kupon clearance: model solid rata, die dengan support (K6). | Kalau socket ikut terdampak elephant foot, tambah chamfer kecil di mulut socket sebagai parameter kupon. |
| R5 | Resin umum (bukan resin model dental) berubah dimensi seiring waktu. | Ukur ulang kupon dimensi setelah disimpan (§5.K). | Catat di preset dan laporan; pertimbangkan resin model dental. |

## 8. Ringkasan modul core/ baru

| Modul | Isi | Dipakai oleh |
|---|---|---|
| `core/model_presets.py` | loader preset printer + resin dengan `value`/`status`/`source`/`coupon_range`, nilai tengah kupon, daftar peringatan | semua |
| `core/calibration.py` | geometri kupon, faktor skala dari ukuran terukur | 5.K |
| `core/topology.py` | pasangan edge-face, loop batas, komponen terhubung (union-find numpy) | 5.1, 5.2 |
| `core/orient.py` | estimasi frame oklusal (PCA + normal berbobot luas) | 5.0 |
| `core/trim.py` | clipping umum berbasis parameter potong per edge, tutup lubang dalam | 5.1 |
| `core/solid.py` | konversi `MeshData` ↔ `Manifold`, validasi `status`, genus, rongga tertutup | 5.K, 5.2 sampai 5.7 |
| `core/base.py` | skirt, blok base, model solid | 5.2 |
| `core/voxel.py` | okupansi per lapisan, EDT berjendela | 5.3 |
| `core/hollow.py` | rongga, lubang drainase di dasar, verifikasi | 5.3 |
| `core/section.py` | kurva lengkung, bidang potong default, pemecahan segmen | 5.4 |
| `core/die.py` | peg, socket, verifikasi clearance | 5.4, 5.5 |
| `core/margin_path.py` | jalur terpendek di graf edge (Dijkstra) | 5.5 |
| `core/ditch.py` | alat ditching, verifikasi margin utuh | 5.5 |
| `core/label.py` | patch dinding samping, poligon teks → solid, verifikasi | 5.6 |
| `core/export.py` | pemeriksaan siap cetak, peringatan, kompensasi skala, STL per bagian, laporan JSON | 5.7 |

Semua modul di atas Python + numpy + manifold3d, tanpa bpy, dan diuji di Lapis 1. ops/ hanya berisi operator tipis dan alat interaktif (gambar kurva trim, klik titik terendah gigi, taruh bidang potong, klik titik margin) dengan `gpu` draw handler. ui/ menambah langkah wizard Model: Kalibrasi → Scan → Orientasi → Trim → Base → Section/Die → Label → Ekspor, dengan panel peringatan parameter yang belum dikalibrasi.

## 9. Ringkasan parameter

| Parameter | Fitur | Status | Nilai awal | Sumber |
|---|---|---|---|---|
| Faktor skala X, Y, Z | 5.K, 5.7 | perlu kalibrasi | 1,0 | ANY hanya konteks (volume 4,3-5,6%) |
| Jarak bidang trim di bawah gigi terendah | 5.1 | default pabrikan (printer lain), perlu kalibrasi | 3 mm | FLD |
| Tinggi base | 5.2 | default pabrikan (printer lain), perlu kalibrasi | 3 mm | FLD |
| Margin base di luar outline | 5.2 | praktik lab | §9.1 | setelan Model Creator lab |
| Tebal dinding hollow | 5.3 | default pabrikan (printer lain), perlu kalibrasi | 3,0 mm | MED, UNZ, KUL |
| Jumlah lubang drainase | 5.3 | default pabrikan (printer lain), perlu kalibrasi | 4 | MED (UNZ: 1-2) |
| Diameter lubang drainase | 5.3 | default pabrikan (printer lain), perlu kalibrasi | 4,0 mm | MED |
| Letak lubang drainase | 5.3 | default pabrikan | dasar model | FLB, UNZ |
| Jarak voxel | 5.3 | perlu kalibrasi | dari spike S1 | tidak ada (komputasi) |
| Lebar kerf antar segmen | 5.4 | praktik lab | §9.1 | setelan Model Creator lab |
| Tinggi bidang pisah | 5.4 | praktik lab | §9.1 | setelan Model Creator lab |
| Clearance die-socket | 5.5 | perlu kalibrasi | 0,075 mm | tengah rentang RESEARCH.md §3 |
| Inset peg | 5.5 | default pabrikan (printer lain), perlu kalibrasi | 1,5 mm | KUL (interpretasi "Seating width") |
| Tinggi peg | 5.5 | default pabrikan (printer lain), perlu kalibrasi | 2,5 mm | KUL "Pin height" |
| Celah dasar socket | 5.5 | praktik lab | §9.1 | setelan Model Creator lab |
| Taper peg | 5.5 | perlu kalibrasi | tidak dipakai | tidak ada |
| Kedalaman dan lebar ditching | 5.5 | default pabrikan (printer lain), perlu kalibrasi | 0,5 mm dan 0,5 mm | KUL |
| Jarak tepi atas ditching ke margin | 5.5 | praktik lab | §9.1 | setelan Model Creator lab (kandidat MED tidak dipakai) |
| Posisi label | 5.6 | keputusan maintainer | dinding samping posterior/lingual | K3 |
| Hollow untuk model dengan removable die | 5.3, 5.5 | keputusan maintainer | dinonaktifkan | K6 |
| Tinggi dan kedalaman label | 5.6 | praktik lab | §9.1 | setelan Model Creator lab |

Sampai tabel §9.1 terisi, parameter berstatus "praktik lab" belum punya nilai, jadi fitur yang memakainya (margin base, section, celah dasar peg, jarak ditching ke margin, label) belum bisa diimplementasikan. Nilai praktik lab yang diisi di §9.1 menimpa angka KUL untuk parameter yang sama. Kupon kalibrasi 1 sampai 3 tidak terhambat dan sudah diimplementasikan.

### 9.1 Nilai praktik lab (K5, diisi maintainer)

Sumber: setelan Model Creator yang dipakai lab. Kolom "catatan" untuk definisi parameter di software asal (misalnya diukur dari mana ke mana), karena definisi itu menentukan cara memetakannya ke parameter DentalCAD. Satuan diisi sesuai software asal.

| Parameter | Nilai praktik lab | Satuan | Catatan |
|---|---|---|---|
| Margin base di luar outline lengkung (§5.2) | | | |
| Lebar kerf antar segmen (§5.4) | | | |
| Tinggi bidang pisah horizontal (§5.4) | | | |
| Clearance die-socket (§5.5, saat ini tengah rentang RESEARCH.md) | | | |
| Inset peg dari jejak segmen (§5.5) | | | |
| Tinggi peg (§5.5) | | | |
| Celah dasar socket (§5.5) | | | |
| Kedalaman ditching (§5.5) | | | |
| Lebar ditching (§5.5) | | | |
| Jarak tepi atas ditching ke margin (§5.5) | | | |
| Tinggi huruf label (§5.6) | | | |
| Kedalaman ukir/timbul label (§5.6) | | | |

## 10. Keputusan

**Sudah diputuskan (maintainer, 2026-10-23):**
- **K1:** Preset tidak berisi `null`. Parameter yang punya sumber pabrikan diisi nilai itu dengan status "default pabrikan (printer lain), perlu kalibrasi". Parameter tanpa sumber berjalan dengan nilai tengah rentang kupon sambil menampilkan peringatan, tidak menolak jalan.
- **K2:** Orientasi acuan: model dicetak rata di build plate, lubang drainase di dasar.
- **K3:** Label default di dinding samping base, posterior/lingual, bukan di dasar.
- **K4:** Kupon kalibrasi jadi fitur pertama, termasuk pengukuran penyusutan per sumbu dan faktor kompensasi skala di preset. Die di kupon dicetak dengan support di bawahnya (UNZ).
- **K5:** Parameter tanpa sumber pabrikan memakai sumber baru berstatus "praktik lab": setelan Model Creator yang dipakai lab, diisi maintainer di tabel §9.1. Nilai itu menjadi default dan titik tengah rentang kupon. Angka MED *extra dies* tidak dipakai. **Menunggu:** tabel §9.1 diisi.
- **K6:** Tidak ada konflik dengan K2. UNZ membedakan solid + removable die (model rata, hanya die diberi support) dan hollow + removable die (model dan die perlu support). Model dengan removable die selalu solid dan dicetak rata; die diekspor sebagai bagian terpisah dengan catatan "beri support di slicer"; opsi hollow dinonaktifkan untuk model seperti itu; peringatan ekspor untuk kombinasi hollow + die dihapus karena kombinasinya tidak bisa terjadi.

## 11. Backlog untuk fase lain

- **Fase 4 (provisional):** lab punya **JAMG HE C&B Resin**, shade A1, A2, A3, untuk provisional. IFU belum ada, dan produk ini tidak saya temukan lewat pencarian web pada 2026-10-23. Ketebalan minimum dan luas konektor **wajib** dari supplier (IFU atau dokumen teknis tertulis) sebelum resin ini dipakai sebagai preset material. Jangan memakai angka PMMA di RESEARCH.md §2 (Telio CAD, VITA CAD-Temp) sebagai pengganti, karena itu material lain.
- **3MF:** ekspor dengan unit dan orientasi (RESEARCH.md §5).
