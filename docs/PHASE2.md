# Fase 2: Crown zirkonia single (rancangan)

Status: **langkah implementasi pertama selesai** (2026-10-23): scipy + zip per platform (§6), `zircad_prime.json` dengan angka IVO (§2), dan `core/synthetic.py` (§4). Fitur §5 belum dimulai. Keputusan K1 sampai K5 sudah diambil maintainer pada 2026-10-23 (§9). Fase 1 diparkir (docs/PHASE1.md), dan Fase 2 sengaja tidak bergantung pada bagian Fase 1 yang tertunda.

Dasar dokumen ini:
- RESEARCH.md Roadmap, Fase 2: deliverable *margin semi-auto, sumbu insersi/undercut, spacer, library CC0 + morphing, kontak, heatmap ketebalan, ekspor STL ke MillBox*; kriteria selesai *20 kasus: deviasi margin vs desain exocad ≤50 µm (median), lolos cek ketebalan, 5 crown dimilling dan dicoba di die*.
- RESEARCH.md §2 (parameter material dan cement gap), §3 baris P1 "Crown anatomis penuh", §4 (konsep teknis inti), §6 (arsitektur dan performa).
- docs/ARCHITECTURE.md (`core/` tanpa bpy, Blender 5.2 LTS, numpy 2.3.4; scipy di backlog §8).
- Pengecekan Teeth3DS+ di §3 dan sumber pabrikan di §2.1, semuanya dibaca langsung pada 2026-10-23.

## 1. Batasan maintainer dan konsekuensinya

| Batasan | Konsekuensi |
|---|---|
| Tidak ada pencetakan atau milling. Validasi hanya digital. | Kriteria roadmap "5 crown dimilling dan dicoba di die" diganti pemeriksaan digital (§7). Ekspor STL diperiksa validitasnya, tetapi impor ke MillBox tidak bisa diuji. Parameter yang hanya bisa dikalibrasi lewat milling (cement gap, kompensasi bur) dipakai sebagai default bersumber, dengan status yang menyatakan belum dikalibrasi. |
| Belum ada scan pasien. | Semua data uji sintetis (§4): die preparasi dengan margin chamfer dan shoulder yang geometrinya diketahui pasti, sehingga akurasi algoritma diukur terhadap jawaban yang benar, bukan terhadap desain exocad. |
| Teeth3DS+ tidak dipakai sebelum lisensinya jelas. | Lisensinya sekarang sudah jelas (§3) dan tidak cocok untuk sebagian besar kebutuhan proyek. Tidak ada data Teeth3DS+ yang diunduh. |

Kriteria roadmap "deviasi margin ≤50 µm (median)" dipertahankan angkanya, tetapi pembandingnya diganti: deviasi terhadap kurva margin analitis data sintetis, bukan terhadap desain exocad.

## 2. Aturan parameter

Sama dengan Fase 1 (docs/PHASE1.md §1), ditambah satu status:

| Status | Arti |
|---|---|
| **default pabrikan** | Angka dari tabel parameter resmi pabrikan material untuk software CAD lain (IVO, §2.1). Definisi geometri parameter di DentalCAD bisa berbeda dari exocad, dan nilai akhirnya bergantung pada mesin milling, jadi tetap perlu kalibrasi saat milling tersedia. Angka ini menggantikan angka literatur yang tumpang tindih (K4). |
| **bersumber (IFU)** | Angka dari IFU pabrikan yang dikutip RESEARCH.md dengan rujukan. RESEARCH.md (Caveats) meminta revisi terbaru IFU dicek di situs pabrikan sebelum dijadikan default; pengecekan itu adalah tugas S0 (§8). |
| **literatur, perlu kalibrasi** | Angka dari literatur yang dikutip RESEARCH.md; nilai klinis final bergantung pada mesin dan material, dan kalibrasinya butuh milling (tidak ada di Fase 2). |
| **perlu kalibrasi** | Tidak ada sumber, atau hanya disebut di RESEARCH.md tanpa rujukan. Berjalan dengan nilai tengah rentang yang ada, disertai peringatan (K1 Fase 1). |
| **desain data uji** | Bentuk data sintetis (ukuran die, tingkat derau). Bukan parameter desain crown. |
| **ambang uji** | Toleransi tes otomatis. |

Material: preset `data/materials/zircad_prime.json` dari Fase 0 dipakai, dengan dua perubahan pada langkah implementasi pertama: `cement_gap_um` 50 → 60 (IVO, menggantikan angka literatur), dan sumbernya ditambah IVO. Parameter crown lain dari IVO (§2.1) masuk sebagai field baru di skema preset material.

### 2.1 Sumber yang diverifikasi untuk Fase 2

| ID | Sumber | Isi yang dipakai |
|---|---|---|
| **IVO** | Ivoclar, "Ivoclar Software Parameter Chart: exocad", 2024-02-07 / EN / Rev. 1, 8 halaman. Link dari maintainer (icde-fr.ivoclar.com, dokumen 43360) mengembalikan HTTP 503 saat dicek; yang dibaca adalah salinan di domain resmi ivoclar.com (`/it_IT/CMS/Ivoclar Vivadent/Technical/Service/Ivoclar-Digital-Parametri-Software-Chart-Exocad.pdf`, isi berbahasa Inggris). Belum dipastikan apakah revisinya sama dengan dokumen 43360. | Baris **IPS e.max ZirCAD Prime (Full and partial anatomical restorations), single crown**: Gap thickness of cement 0.06 mm; Add. distance x/y 0.01 mm; Beginning of cement 1.00 mm; Minimal thickness (1 elemen) anterior 0.80 mm, premolar 1.00 mm, molar 1.00 mm; Horizontal margin thickness 0.20 mm; Crown margin angle 65°; Angled margin thickness 0.10 mm; Anticipate milling Yes, Diameter 1.2 mm. Catatan dokumen: "The given dimensions for internal crown surfaces serve as guidelines and may be customized". **Jarak ke antagonis dan ke tetangga tidak tercantum.** |
| **KUL** | Kulzer, "Setting Parameters exocad for cara Print 4.0" (sama dengan PHASE1.md §2), halaman 2, resin cetak cor dima Print Cast ruby | Distance to antagonist 0.1 mm, Distance to neighbour 0 mm. **Hanya pembanding**, bukan default: materialnya resin cetak untuk dicor, bukan zirkonia (K4). |
| **DTX** | DTX Studio Lab 1.10 Help, "Crown bottoms" (helpfiles.dtxstudio.com/Help/2f5dd4d8-2a46-429b-ab87-cf4df5ddb0f1/1.10/EN/Crown_bottoms.htm), © 2019 Medicim N.V.; software lab berbasis exocad | "The From margin slider [2] defines the start of the cement gap relative to the margin line, in millimeters": dengan nilai 1, daerah dalam 1 mm dari margin line tidak punya cement gap. Additional spacing diatur terpisah untuk Radial ("mesial/distal") dan Axial, default terkunci bersama; "Additional spacing is also applied in the area where there is no cement gap" dan ditambahkan di atas cement gap di daerah yang punya gap. Border crown: Horizontal = lebar border horizontal ("for zirconia a common minimum value is 0.2 mm"), Angled = panjang bagian bersudut, Angle = sudut bagian itu, Vertical = border vertikal tambahan. |
| **EXW** | exocad wiki, "Designing the inside of the crown" (wiki.exocad.com/wiki/index.php/Designing_the_inside_of_the_crown). Server aslinya menolak koneksi saat dicek; yang dibaca adalah arsip Wayback Machine snapshot 2026-10-05 | "You can add spacing in axial direction that will be applied everywhere using the slider Axial [4]. To add horizontal spacing perpendicular to the axial direction, use the slider Radial [5]." Definisi border crown sama dengan DTX. Versi ini mengatur zona cement gap dengan kuas, tanpa slider "From margin". |
| **PAT** | Google Patents, US8359114B2 "Haptically enabled dental modeling system", DentsAble Inc (patents.google.com/patent/US8359114B2/en) | Diberikan 2013-01-22; status "Expired - Fee Related"; event "PATENT EXPIRED DUE TO NONPAYMENT OF MAINTENANCE FEES" (2017); expiration teradjust semula 2029-10-19. Google menulis: "The legal status is an assumption and is not a legal conclusion." |

## 3. Teeth3DS+: hasil pengecekan

Sumber yang dibaca: halaman proyek (crns-smartvision.github.io/teeth3ds), metadata dan `license.txt` proyek OSF xctdy (dibaca lewat API OSF; data tidak diunduh), README repo github.com/abenhamadou/3DTeethSeg22_challenge, dan paper arXiv 2210.06094 v3 (6 Jan 2026).

**Lisensi data: CC BY-NC-ND 4.0** (Attribution-NonCommercial-NoDerivatives 4.0 International).
- `license.txt` di root proyek OSF berisi teks lengkap CC BY-NC-ND 4.0. Metadata OSF sendiri hanya menulis "Other".
- README repo: dataset tersedia "for non-commercial research and educational purposes" di bawah CC BY-NC-ND 4.0; **"Commercial use requires a separate license"**, termasuk untuk "evaluation of commercial AI models, or integration into commercial products and services"; kontak contact@udini.ai.
- Lisensi CC BY-SA 4.0 di bagian bawah halaman proyek berlaku untuk **website**, bukan dataset. Repo GitHub tidak mencantumkan file lisensi.

**Gigi preparasi:** tidak bisa dipastikan tanpa mengunduh data.
- Paper v3 §2.1: 1800 scan dari 900 pasien, scanner Primescan, Trios3, iTero Element 2 Plus; "Clinical cases included 50% orthodontic and 50% prosthetic treatments"; sekitar 70% pasien di bawah 16 tahun.
- Tidak ada pernyataan bahwa dataset memuat gigi preparasi, dan anotasinya hanya label/instance gigi per vertex (FDI) serta landmark (mesial, distal, cusp, inner, outer, facial axis). **Tidak ada anotasi garis margin.**

**Konsekuensi untuk proyek ini:**
- **NoDerivatives:** materi turunan (potongan gigi, template library, golden case hasil olahan) tidak boleh dibagikan. Jadi tidak boleh di-commit, dibundel di extension, atau dipakai sebagai tooth library, yang menurut RESEARCH.md §4 wajib CC0/CC-BY.
- **NonCommercial:** proyek ini GPL-3.0 dan RESEARCH.md §7 menyebut monetisasi lewat jasa desain. Pemakaian untuk pengembangan produk atau jasa lab berisiko termasuk komersial menurut README di atas.
- **Untuk margin:** tanpa anotasi margin, dataset ini tidak bisa menjadi ground truth akurasi margin. Paling jauh hanya untuk uji ketahanan (algoritma tidak gagal pada scan nyata), dan itu pun hanya kalau ada gigi preparasi.
- **Keputusan K3: Teeth3DS+ tidak dipakai di proyek ini.** Alasannya: (1) lisensi CC BY-NC-ND 4.0 melarang membagikan turunan dan membatasi ke pemakaian non-komersial, sedangkan proyek ini GPL dan berencana dimonetisasi lewat jasa; (2) tidak ada anotasi garis margin, jadi tidak bisa menjadi ground truth akurasi margin; (3) keberadaan gigi preparasi tidak dinyatakan di paper. Tidak ada data Teeth3DS+ yang diunduh. Kalau suatu saat dibutuhkan, jalurnya adalah lisensi komersial dari Udini.

Pembanding derau scanner: paper yang sama menyebut akurasi scanner 10-90 mikrometer. Angka ini dipakai sebagai rentang derau data sintetis (§4), bukan sebagai parameter desain.

## 4. Data uji sintetis

Modul `core/synthetic.py`, numpy murni. Semua kurva dan permukaan didefinisikan analitis, sehingga jawaban benar diketahui tepat, terlepas dari tesselasi. Modul ini juga dipakai operator "muat kasus sintetis" di Blender, supaya alur crown bisa dicoba tanpa scan pasien.

**Die preparasi** (dalam frame die: sumbu insersi sebenarnya = +Z, lalu diputar acak dengan rotasi yang diketahui):
- **Tubuh preparasi:** permukaan revolusi dengan penampang elips (jari-jari a, b), dinding menyempit ke oklusal dengan sudut konvergensi yang diketahui, dan atap oklusal membulat.
- **Garis margin analitis:** z_m(θ) = z₀ + A·cos(2θ) (scallop seperti CEJ; A = 0 untuk margin datar). Ini kurva jawaban benar.
- **Finish line shoulder:** tangga horizontal selebar w pada z_m(θ); margin = tepi luar tangga, yaitu tepi konveks 90°.
- **Finish line chamfer:** busur seperempat lingkaran berjari-jari w dari dinding preparasi ke permukaan akar; margin = titik akhir busur di permukaan akar.
- **Akar di bawah margin:** dinding hampir vertikal turun ke dasar die.
- **Varian undercut:** satu sektor sudut dengan dinding miring ke luar (taper negatif), sehingga himpunan face undercut terhadap sumbu sebenarnya diketahui analitis.

**Mesh:**
- Sampling grid parametrik (θ, s) dengan kepadatan yang bisa diatur, dipecah segitiga dengan diagonal acak.
- Vertex digeser acak di sepanjang permukaan (tetap di permukaan analitis), supaya titik grid tidak jatuh tepat di garis margin dan algoritma tidak "curang" lewat struktur grid.
- Derau normal Gaussian σ dari rentang akurasi scanner 10-90 µm (Teeth3DS+ v3). Level uji: 0, 10, 30, dan 90 µm.
- Rotasi acak yang diketahui, supaya algoritma tidak bergantung pada orientasi.

**Konteks:**
- **Gigi tetangga:** elipsoid di mesial dan distal, dengan jarak ke kontur die yang diketahui, untuk uji kontak proksimal.
- **Antagonis:** permukaan halus dengan jarak oklusal yang diketahui ke atap die.

**Crown referensi untuk uji ketebalan:** cangkang analitis (permukaan dalam = offset die + gap, permukaan luar = offset dengan peta ketebalan yang diketahui, termasuk satu daerah sengaja di bawah minimum material).

**Parameter.** Semua berstatus **desain data uji**: a, b, sudut konvergensi, w, z₀, A, kepadatan mesh, σ. Nilainya dipilih supaya ukurannya masuk akal untuk gigi posterior, dan dicatat di setiap golden case sintetis (`expected.json`). Nilai-nilai ini bukan default desain crown.

**Status:** die (shoulder, chamfer, scallop, undercut, derau, rotasi) sudah diimplementasikan di `core/synthetic.py` dengan tes di `tests/core/test_synthetic.py`. Gigi tetangga, antagonis, dan crown referensi menyusul bersama fitur yang memakainya (§5.5, §5.6).

**Temuan untuk algoritma undercut (§5.2):** pada mesh dengan jitter parameter 0,45 sel, normal face mentah bisa menyimpang lebih dari sudut taper dinding (6°), sehingga sebagian face dinding yang sebenarnya bukan undercut punya `dot(normal, sumbu) < 0`. Algoritma undercut perlu normal yang dihaluskan (misalnya rata-rata cincin), bukan tanda normal face mentah; ini akan diukur terhadap jawaban benar `undercut_faces()`.

**Pengujian generator itu sendiri (Lapis 1):**
- Titik kurva margin analitis terletak di permukaan analitis.
- Mesh tanpa derau watertight setelah dasar ditutup.
- Jarak setiap vertex tanpa derau ke permukaan analitis ≈ 0 (ambang uji presisi float).
- Daerah undercut analitis cocok dengan hitungan normal pada mesh halus.

## 5. Fitur

### 5.1 Margin semi-otomatis

**Algoritma** (RESEARCH.md §4):
1. **Curvature per vertex:** normal vertex berbobot luas, lalu fit kuadrik lokal di cincin tetangga (least squares, numpy tervektorisasi per kelompok valensi) untuk mendapat curvature prinsipal κ₁ ≥ κ₂. Untuk shoulder (tepi konveks), κ₁ besar dan positif di margin.
2. **Graf biaya:** edge mesh berbobot `panjang × f(κ)`, dengan f menurun tajam saat κ₁ (searah orientasi luar) membesar. Bentuk f dan parameternya ditetapkan di spike S1.
3. **Semi-otomatis:** pengguna mengklik satu titik di dekat margin. Jalur tertutup berbiaya minimum yang melewati titik itu dicari dengan Dijkstra di sekitar cincin die (dua jalur dari titik klik ke titik di seberang, lalu digabung), dibatasi ke ROI sekitar die.
4. **Penghalusan:** polyline hasil di-fit dengan spline periodik, lalu setiap titik digeser ke posisi κ₁ maksimum di sepanjang garis potong permukaan yang tegak lurus kurva (energy minimization ringan). Pengguna bisa menggeser titik kontrol (modal operator di ops/).
5. **Paten (K5):** RESEARCH.md §4 menyebut US 8.359.114 yang memuat deteksi berbasis curvature dan silhouette. Google Patents mencatat statusnya "Expired - Fee Related" (PAT, §2.1). **Status Google bukan kesimpulan hukum**, seperti ditulis Google sendiri, dan belum ditinjau konsultan. Keputusan maintainer: margin memakai pendekatan curvature klasik (curvature prinsipal + jalur biaya minimum + penghalusan, seperti langkah 1 sampai 4), **bukan** meniru metode ML dari paten atau publikasi yang lebih baru (misalnya yang disebut RESEARCH.md §4 dan roadmap 6+).

**Parameter.**

| Parameter | Status | Catatan |
|---|---|---|
| Bentuk dan skala fungsi biaya f(κ) | perlu kalibrasi | Ditetapkan di spike S1 terhadap data sintetis; bukan parameter klinis. |
| Ukuran ROI di sekitar die | perlu kalibrasi | Dari S1. |
| Titik klik | input pengguna | |

**Modul core/.** `core/curvature.py`, `core/margin_path.py` (Dijkstra, sudah direncanakan di Fase 1 §5.5, dipakai ulang dan diperluas), `core/margin.py` (`detect_margin`, `refine_margin`, `margin_deviation`).

**Pengujian.**
- Lapis 1, akurasi: untuk setiap kombinasi finish line (shoulder, chamfer), scallop (A = 0 dan A > 0), derau (0, 10, 30, 90 µm), dan kepadatan mesh: jarak setiap titik margin terdeteksi ke kurva analitis (dihitung eksak lewat sampling rapat kurva). Laporkan median, p95, dan maksimum, serta cakupan (jarak titik kurva analitis ke polyline terdeteksi, supaya margin yang hanya menutupi sebagian kurva tidak lolos).
- **Kriteria:** median ≤ 50 µm (angka roadmap) pada semua kombinasi sampai derau 30 µm. Ambang p95 dan perilaku pada derau 90 µm ditetapkan setelah S1 sebagai ambang uji, karena tidak ada sumbernya.
- Lapis 1, invarian: rotasi acak die tidak mengubah deviasi (selisih di bawah ambang uji); titik klik yang berbeda di sepanjang margin menghasilkan kurva yang sama.
- Lapis 2: operator margin pada kasus sintetis di Blender menghasilkan kurva yang sama dengan core.

### 5.2 Sumbu insersi dan undercut

**Algoritma** (RESEARCH.md §4):
1. **Sumbu default:** rata-rata normal berbobot luas dari face preparasi (di atas margin), dinormalisasi. Pengguna bisa memutarnya lewat gizmo.
2. **Undercut:** face di atas margin dengan `dot(normal, sumbu) < 0` yang berada di bawah kontur terbesar terhadap sumbu itu. Kontur terbesar dihitung sebagai silhouette proyeksi sepanjang sumbu.
3. **Heatmap:** kedalaman undercut per vertex = jarak horizontal ke silhouette, dikirim ke ops/ sebagai atribut warna.
4. **Block-out** (untuk spacer): menyapu proyeksi sepanjang sumbu, sehingga permukaan dalam crown tidak masuk ke undercut.

**Parameter.** Tidak ada parameter klinis. Sudut toleransi untuk "hampir sejajar" adalah ambang uji.

**Modul core/.** `core/insertion.py` (`default_axis`, `undercut_faces`, `undercut_depth`, `block_out`).

**Pengujian.**
- Lapis 1: die sintetis yang diputar dengan rotasi R diketahui menghasilkan sumbu = R·Z, dengan galat sudut di bawah ambang uji untuk setiap level derau.
- Lapis 1: varian undercut menghasilkan himpunan face undercut dengan IoU terhadap sektor analitis di atas ambang uji; die tanpa undercut menghasilkan himpunan kosong.
- Lapis 1: setelah block-out, tidak ada titik permukaan dalam yang terlihat terhalang sepanjang sumbu.

### 5.3 Spacer (cement gap)

**Algoritma** (RESEARCH.md §4, definisi parameter dari DTX dan EXW): permukaan dalam crown = permukaan die hasil block-out yang digeser sebesar gap(d)·n + s_r·h(n), dengan:
- d = jarak geodesik ke margin line, n = normal permukaan;
- gap(d) = 0 untuk d < "from margin", lalu naik ke gap semen (DTX: awal cement gap diukur dari margin line);
- h(n) = komponen normal yang tegak lurus sumbu insersi (arah horizontal), dan s_r = spacing radial. Spacing radial berlaku di seluruh permukaan dalam, **termasuk zona tanpa cement gap**, dan ditambahkan di atas cement gap di zona yang punya gap (DTX; arah tegak lurus sumbu dari EXW);
- spacing axial (EXW: "applied everywhere") tidak tercantum di IVO, jadi 0 sampai ada sumber.
- gap = 0 untuk d ≤ jarak ke margin.
- Transisi halus ke gap aksial/oklusal.
- Jarak geodesik dihitung dengan Dijkstra multi-sumber dari vertex margin (pendekatan di graf edge; galatnya diukur di uji).

**Parameter.**

| Parameter | Status | Nilai | Sumber |
|---|---|---|---|
| Gap semen | default pabrikan | 0,06 mm | IVO "Gap thickness of cement". Menggantikan default literatur RESEARCH.md §2 (30-60 µm, nilai lama 50 µm di `zircad_prime.json`). |
| Jarak dari margin tanpa gap ("from margin") | default pabrikan | 1,00 mm | IVO "Beginning of cement" = slider "From margin" di exocad (DTX). Menggantikan rentang literatur 0,5-1,0 mm (RESEARCH.md §2). |
| Spacing radial | default pabrikan | 0,01 mm | IVO "Add. distance x/y" = Additional spacing Radial: horizontal, tegak lurus sumbu insersi (EXW), berlaku juga di zona tanpa cement gap (DTX). |
| Spacing axial | perlu kalibrasi | 0 mm + peringatan | Tidak tercantum di IVO. Di exocad default terkunci bersama radial (DTX), tetapi IVO hanya memberi x/y, jadi tidak diasumsikan sama. |
| Bentuk transisi gap | perlu kalibrasi | linear + peringatan | Tidak ada di RESEARCH.md maupun IVO. |

Catatan: angka Kulzer untuk exocad (gap 0,08 mm, beginning of cement gap 1 mm) **tidak** dipakai. Angka itu untuk resin cetak cor dima Print Cast ruby, bukan zirkonia.

**Modul core/.** `core/geodesic.py`, `core/spacer.py` (`spacer_surface`, `verify_spacer`).

**Pengujian.**
- Lapis 1: pada die sintetis, jarak titik permukaan dalam ke die = 0 di zona margin dan = gap di luar transisi (ambang uji dari ukuran mesh); tidak ada self-intersection pada permukaan dalam.
- Lapis 1: galat jarak geodesik graf terhadap jarak geodesik analitis pada silinder (yang punya rumus tertutup) di bawah ambang uji.

### 5.4 Proposal crown: template + morphing

**Algoritma** (RESEARCH.md §4: library dibuat sendiri, CC0/CC-BY; morphing landmark + RBF/Laplacian, fit ke margin):
1. **Template:** Fase 2 belum punya tooth library nyata (tidak ada scan, dan Teeth3DS+ tidak boleh dipakai, §3). Template awal adalah **crown parametrik sintetis** (badan elips dengan cusp gaussian) yang jelas ditandai sebagai bukan anatomi nyata. Library nyata adalah keputusan K2.
2. **Penempatan:** template diskalakan dan diposisikan dari ukuran kurva margin dan sumbu insersi.
3. **Fit ke margin:** batas bawah template dipetakan ke kurva margin; deformasi Laplacian (sistem sparse) menjaga detail permukaan sambil memaksa batas tepat di margin dan permukaan dalam tepat di spacer.
4. **Jahitan:** permukaan luar dan dalam disatukan di margin menjadi solid tertutup (manifold3d).

5. **Border crown di margin** (IVO, definisi dari DTX dan EXW): dari margin line, border horizontal selebar 0,20 mm ("Horizontal"), lalu bagian bersudut sepanjang 0,10 mm ("Angled", di IVO bernama "Angled margin thickness") dengan sudut 65° ("Angle"), lalu permukaan luar crown. Border vertikal tambahan tidak dipakai (tidak ada di IVO). Acuan sudut "Angle" tidak dijelaskan di DTX maupun EXW, jadi arah sudut 65° adalah satu-satunya bagian yang masih interpretasi (S4).

**Parameter.**

| Parameter | Status | Nilai | Sumber |
|---|---|---|---|
| Border horizontal | default pabrikan | 0,20 mm | IVO "Horizontal margin thickness" = slider Horizontal (DTX, EXW) |
| Sudut bagian bersudut | default pabrikan | 65° | IVO "Crown margin angle" = slider Angle (DTX, EXW); acuan sudut masih interpretasi (S4) |
| Panjang bagian bersudut | default pabrikan | 0,10 mm | IVO "Angled margin thickness" = slider Angled, "the length of the angled part of the border" (DTX, EXW) |
| Bentuk template, bobot Laplacian, pengaturan solver | desain data uji / dari S3 | | Bukan parameter klinis. |

**Modul core/.** `core/template.py`, `core/morph.py` (butuh `scipy.sparse`, lihat K1), `core/crown.py` (`assemble_crown`).

**Pengujian.**
- Lapis 1: batas crown hasil morph berimpit dengan kurva margin (deviasi di bawah ambang uji); crown watertight, genus 0, tanpa self-intersection; permukaan dalam = spacer.
- Lapis 1: morph dengan target = template itu sendiri tidak mengubah geometri (uji identitas).

### 5.5 Kontak proksimal dan jarak oklusal

**Algoritma:**
- Jarak bertanda dari permukaan luar crown ke gigi tetangga dan antagonis (titik terdekat di permukaan, lihat §5.6 untuk struktur data).
- Daerah kontak = jarak ≤ target. Overlap proksimal yang diminta dibuat dengan menggeser permukaan lokal (deformasi Laplacian yang sama dengan §5.4) sampai jarak minimum = −overlap target.
- Jarak oklusal ke antagonis dilaporkan dan diwarnai.

**Parameter.**

| Parameter | Status | Nilai | Sumber |
|---|---|---|---|
| Overlap kontak proksimal | perlu kalibrasi | 0,025 mm (tengah rentang) + peringatan | RESEARCH.md §3 tabel indikasi: sekitar 0,0-0,05 mm overlap, tanpa rujukan. |
| Jarak oklusal minimum ke antagonis | tidak ada default | dilaporkan tanpa ambang | Tidak ada di IVO maupun RESEARCH.md (K4). Pembanding: KUL "Distance to antagonist" 0,1 mm untuk resin cetak cor; **bukan default**. Panel menampilkan jarak terukur dan angka pembanding itu dengan labelnya. |
| Jarak ke gigi tetangga | tidak ada default | dilaporkan | Tidak ada di IVO. Pembanding: KUL "Distance to neighbour" 0 mm untuk resin cetak cor. |

**Modul core/.** `core/proximity.py` (jarak bertanda titik ke permukaan), `core/contacts.py`.

**Pengujian.**
- Lapis 1: tetangga elipsoid sintetis pada jarak yang diketahui; jarak terukur = jarak analitis (ambang uji); setelah penyesuaian kontak, overlap = target.
- Lapis 1: antagonis pada jarak oklusal yang diketahui; jarak terukur cocok.

### 5.6 Heatmap ketebalan dan cek material

**Algoritma:**
- Ketebalan di titik permukaan luar = jarak terdekat ke permukaan dalam (bola terbesar yang muat), bukan ray-cast sepanjang normal. Ini yang relevan untuk ketebalan minimum IFU, dan tidak sensitif terhadap normal yang berderau.
- RESEARCH.md §4 menyarankan BVHTree `mathutils`, tetapi `core/` tidak boleh memakai mathutils. Penggantinya: `scipy.spatial.cKDTree` atas titik sampel rapat permukaan dalam, lalu penyempurnaan eksak jarak titik-ke-segitiga untuk kandidat terdekat. Ini juga dasar `core/proximity.py` di §5.5.
- Cek material: ketebalan minimum dibandingkan dengan preset (`zircad_prime.json`); anterior, premolar, atau molar dipilih dari nomor gigi FDI (`core/units.py`), mengikuti pembagian di IVO.
- Daerah di bawah minimum diwarnai merah dan ekspor diblokir.
- **Antisipasi milling** (RESEARCH.md §4, IVO): daerah fisur yang radiusnya lebih kecil dari radius alat ditandai, tanpa mengubah geometri. Diameter alat adalah parameter preset (1,2 mm dari IVO).

**Parameter.**

| Parameter | Status | Nilai | Sumber |
|---|---|---|---|
| Ketebalan minimum crown tunggal | default pabrikan | anterior 0,80 mm; premolar dan molar 1,00 mm | IVO "Minimal thickness" (1 elemen). Sama dengan IFU yang dikutip RESEARCH.md §2 [25] (0,8 / 1,0 mm); revisi IFU tetap dicek di S0. |
| Diameter alat untuk antisipasi milling | default pabrikan | 1,2 mm | IVO "Anticipate milling: Yes, Diameter 1.2 mm". Menggantikan contoh literatur RESEARCH.md §4 (Ø 0,6/1,0 mm). Tetap bergantung mesin milling lab. |

**Modul core/.** `core/proximity.py`, `core/thickness.py` (`thickness_map`, `check_material`), `core/material_db.py` (sudah ada).

**Pengujian.**
- Lapis 1: crown referensi sintetis dengan peta ketebalan yang diketahui; galat ketebalan terukur di bawah ambang uji yang bergantung pada kepadatan sampel; daerah yang sengaja di bawah minimum terdeteksi seluruhnya (recall 100%) dan tidak ada daerah lain yang ditandai.
- Lapis 1: jarak titik-ke-segitiga dibandingkan dengan brute force pada mesh kecil.
- Lapis 1, performa: anggaran waktu untuk crown sekitar 100 ribu segitiga ditetapkan di spike S2.

### 5.7 Ekspor STL crown

**Algoritma:**
- Satu STL biner per crown, memakai `mesh_io.save_stl` dan header disclaimer dari Fase 1.
- Pemeriksaan sebelum ekspor: watertight, `status()` manifold3d tanpa error, tanpa rongga tertutup, ketebalan ≥ minimum material, margin tertutup, kontak dalam toleransi.
- Laporan JSON dengan parameter, status, sumber, metrik, dan SHA-256 (pola yang sama dengan kupon Fase 1).
- Tanpa XML constructionInfo atau format exocad lain (RESEARCH.md §5: hanya format terbuka; MillBox bisa mengimpor STL tanpa metadata).

**Batas validasi:** impor ke MillBox dan milling tidak diuji (batasan maintainer). Laporan ekspor menyatakan ini secara eksplisit.

**Modul core/.** `core/export.py` (direncanakan di Fase 1 §5.7; bagian crown dibuat di sini, bagian model cetak tetap diparkir).

**Pengujian.**
- Lapis 1: round trip STL; ekspor ditolak untuk crown di bawah ketebalan minimum atau dengan margin terbuka; laporan JSON cocok dengan file.
- Lapis 2: alur penuh di Blender pada kasus sintetis (muat kasus → margin → sumbu → spacer → proposal → kontak → ketebalan → ekspor).

## 6. Dependensi

**Keputusan K1: scipy masuk di Fase 2, dan build beralih ke zip per platform.** Ini dikerjakan sebagai **langkah implementasi pertama**, sebelum fitur apa pun, supaya CI sudah hijau dengan scipy sebelum kode yang memakainya ditulis.
- **Kegunaan:** `scipy.sparse` (Laplacian, §5.4) dan `scipy.spatial.cKDTree` (jarak ke permukaan, §5.5 dan §5.6). Ini persis kasus "fase yang benar-benar memakainya" di backlog ARCHITECTURE.md §8.
- **Pin:** `scipy==1.18.1`, `requires_dist` `numpy>=2.0.0,<2.8`, cocok dengan numpy 2.3.4 di Blender 5.2 LTS. Wheel cp313 yang diunduh dan di-hash pada 2026-10-23:
  - `scipy-1.18.1-cp313-cp313-win_amd64.whl`: `559ed65f60c1af5a03f3912605a1b5114f522c7c32fb23c3376ae8f03219fe28`
  - `scipy-1.18.1-cp313-cp313-macosx_12_0_arm64.whl`: `e6fb6a55cc0ba97b59a1f288fb86dc6fce8bdfc0fffcbfd015e3a954bf2a2d93`
  - `scipy-1.18.1-cp313-cp313-manylinux_2_27_x86_64.manylinux_2_28_x86_64.whl`: `fdaf5ea890a6183d0565f51a61799d67081bd5b1cf03c5f4b3fd3732108625c9`

  Saat implementasi, cek ulang di PyPI apakah masih ada versi lebih baru dengan wheel cp313 untuk ketiga platform. Kalau tetap 1.18.1, hash di atas dicocokkan lagi saat unduh.
- **Perubahan yang direncanakan:**
  - `blender_manifest.toml`: tiga wheel scipy ditambahkan ke `wheels`.
  - `scripts/download_wheels.py`: tiga entri scipy dengan hash di atas.
  - `requirements-dev.txt`: `scipy==1.18.1`.
  - ARCHITECTURE.md §5 dan §8: scipy pindah dari backlog ke tabel wheel.
- **Build per platform:** `blender --command extension build --split-platforms --output-dir dist`. Blender menambahkan nama platform sebagai sufiks nama file, sehingga ada satu zip per platform di `platforms` (`windows-x64`, `macos-arm64`, `linux-x64`), masing-masing hanya membawa wheel platformnya.
- **Pemeriksaan zip (`check_zip`), dijalankan untuk setiap zip:**
  - Daftar wheel di zip = wheel manifest yang tag platformnya cocok dengan sufiks zip, ditambah wheel `py3-none-any`.
  - Batas ukuran tetap 200 MB per zip. Ditambah anggaran per zip ±60 MB sebagai alarm dini (perkiraan ±38 MB per zip; angkanya ditetapkan dari ukuran nyata saat implementasi).
  - Tes Lapis 1 untuk kasus zip platform yang membawa wheel platform lain.
- **CI:**
  - Setiap job `blender` (Windows, macOS, Linux) membangun semua zip, menjalankan `check_zip` dan `extension validate` untuk semuanya, lalu menginstal dan menguji **zip milik platform runner itu sendiri**. Dengan begitu wheel scipy tiap platform benar-benar dimuat dan diuji di OS-nya.
  - Job Ubuntu mengunggah ketiga zip sebagai artifact.

## 7. Kriteria selesai Fase 2 (digital)

Pengganti kriteria roadmap, karena tidak ada milling dan tidak ada kasus pasien:

| Roadmap | Pengganti di Fase 2 |
|---|---|
| 20 kasus, deviasi margin vs exocad ≤ 50 µm (median) | **Matriks 20 kasus sintetis** (shoulder/chamfer × scallop × 4 level derau, ditambah varian kepadatan mesh dan rotasi): deviasi margin terhadap kurva analitis ≤ 50 µm (median) untuk derau sampai 30 µm; p95 dan perilaku derau 90 µm sesuai ambang dari S1. |
| Lolos cek ketebalan | Crown referensi sintetis: semua daerah di bawah minimum terdeteksi, dan crown hasil alur penuh lolos ketebalan minimum ZirCAD Prime. |
| 5 crown dimilling dan dicoba di die | **Tidak bisa** tanpa milling. Diganti: 5 crown hasil alur penuh pada kasus sintetis berbeda lolos semua pemeriksaan ekspor (watertight, ketebalan, margin tertutup, spacer sesuai, kontak sesuai). Kriteria fisik roadmap tetap terbuka sampai ada akses milling. |

Ditambah:
- Semua tes Lapis 1 dan Lapis 2 lulus di CI (Windows, macOS, Linux).
- Zip extension tetap lolos `check_zip` (atau versi per platform kalau K1 memilih split).

## 8. Spike dan risiko

| ID | Pertanyaan | Cara menjawab | Kalau gagal |
|---|---|---|---|
| S0 | Apakah angka IFU ZirCAD Prime (0,8/1,0 mm) masih sesuai revisi terbaru, dan apakah dokumen IVO yang dibaca sama dengan dokumen 43360 yang ditautkan maintainer? | Baca IFU terbaru di situs Ivoclar (RESEARCH.md Caveats); coba lagi link icde-fr saat servernya pulih dan bandingkan revisinya. | Perbarui `zircad_prime.json` dan catat revisinya. |
| S4 | Bagaimana exocad mendefinisikan "Add. distance x/y", "Beginning of cement", dan parameter border crown? | **Sebagian besar terjawab** (2026-10-23) dari DTX dan EXW: "Beginning of cement" = "From margin"; "Add. distance x/y" = spacing Radial, tegak lurus sumbu, berlaku juga di zona tanpa gap; Horizontal, Angled, dan Angle didefinisikan di kedua sumber. **Tersisa:** acuan sudut "Angle" (diukur terhadap apa). | Uji visual dengan kasus sintetis saat §5.4 dikerjakan; tandai sebagai interpretasi di laporan ekspor. |
| S1 | Seberapa akurat curvature + Dijkstra pada data sintetis berderau? | Jalankan matriks §7 dengan beberapa bentuk f(κ); ukur median dan p95. | Tambah penghalusan permukaan lokal sebelum estimasi curvature, atau fit kuadrik pada cincin yang lebih lebar. |
| S2 | Apakah cKDTree + penyempurnaan titik-ke-segitiga cukup cepat untuk crown sekitar 100 ribu segitiga? | Ukur di host dan di Blender. | Kurangi sampel dengan sampling adaptif, atau batasi penyempurnaan eksak ke daerah dekat ambang. |
| S3 | Apakah Laplacian dengan batas margin stabil (tanpa self-intersection) untuk scallop besar? | Uji pada varian A > 0. | Bobot cotangent dan pembatas lokal, atau iterasi kecil bertahap. |
| R1 | Data sintetis terlalu "bersih" dibanding scan nyata (lubang, artefak, gingiva menutupi margin). | Tidak bisa dijawab tanpa scan nyata. | Dicatat sebagai keterbatasan validasi. Uji ketahanan pada scan nyata menunggu data (golden_private) atau keputusan K3. |
| R2 | Paten metode deteksi margin (RESEARCH.md §4). | K5. | Pilih metode alternatif yang tidak tercakup, misalnya biaya berbasis sudut dihedral, bukan curvature. |

## 9. Keputusan (maintainer, 2026-10-23)

- **K1:** scipy masuk, dan build memakai zip per platform (`--split-platforms`). CI dan pemeriksaan ukuran zip disesuaikan sebagai langkah implementasi pertama (§6).
- **K2:** Template parametrik sintetis dulu. Library nyata diputuskan nanti.
- **K3:** Teeth3DS+ tidak dipakai: CC BY-NC-ND 4.0 (tanpa turunan yang dibagikan, non-komersial) dan tanpa anotasi margin. Alasan lengkap di §3.
- **K4:** Parameter crown memakai tabel resmi Ivoclar untuk exocad (IVO, §2.1) sebagai "default pabrikan", menggantikan angka literatur yang tumpang tindih: gap semen 0,06 mm, extra x/y 0,01 mm, jarak bebas dari margin 1,00 mm, ketebalan minimum 0,80/1,00 mm, margin crown 0,20 mm / 65° / 0,10 mm, dan diameter alat 1,2 mm. Jarak ke antagonis dan tetangga tidak ada di IVO, jadi tidak ada default; angka Kulzer cara Print (antagonis 0,1 mm, tetangga 0 mm, resin cetak cor) dicatat hanya sebagai pembanding.
- **K5:** US 8.359.114 berstatus "Expired - Fee Related" di Google Patents (PAT, §2.1); status Google bukan kesimpulan hukum. Margin memakai pendekatan curvature klasik, bukan meniru metode ML dari paten yang lebih baru.

## 10. Di luar lingkup Fase 2

- Memotong die dari scan lengkung penuh. Data sintetis sudah berupa die terisolasi; pemotongan die dari lengkung terkait sectioned model Fase 1, yang diparkir.
- Margin berbasis ML (RESEARCH.md roadmap 6+).
- Bridge, konektor, dan pontik (Fase 3).
- Milling, impor MillBox, dan uji fit fisik (batasan maintainer).
