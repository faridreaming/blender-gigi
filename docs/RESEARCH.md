# Rencana Produk dan Teknis: Add-on Dental CAD Open Source di Blender ("lebih powerful" dari B4D)

Ini layak dibangun, dengan tiga syarat. Pertama, add-on harus GPL-3.0-or-later. Blender mewajibkannya untuk add-on yang memakai bpy, dan Extensions Platform hanya menerima lisensi itu.\[1\]\[2\]\[3\] Kedua, fase pertama fokus pada crown & bridge zirkonia plus model cetak, dengan alur ekspor STL yang bisa langsung dibaca MillBox. Ketiga, "lebih powerful" berarti unggul di sisi yang tidak dimiliki B4D: alur wizard yang dipandu, pemeriksaan ketebalan dan konektor otomatis berbasis parameter pabrikan, kode terbuka yang bisa diaudit, dan pipeline yang bisa diuji. Fitur mentah saja tidak cukup untuk disebut lebih powerful.

## TL;DR
- **Celahnya nyata.** B4D adalah add-on komersial per modul berbasis skrip "kontrol manual". Open Dental CAD (patmo141) dan BDENTAL memang GPL, tetapi sudah tua atau terbatas. Belum ada add-on dental Blender yang terbuka, modern (Blender 4.5/5.x), dan punya alur kerja terpandu ala exocad. Anda bisa mengisi celah itu.
- **Mulai dari crown & bridge zirkonia dan Model Creator**, dengan parameter material dari IFU pabrikan (contoh: IPS e.max ZirCAD Prime minimal 0,8/1,0 mm, konektor 9 mm²). Ekspor STL bersih ke MillBox. Jangan meniru format proprietary seperti constructionInfo atau dentalProject.
- **Status legal:** software desain restorasi adalah alat kesehatan di EU (MDR Rule 11), di AS (21 CFR 872.3661, kode NOF, kelas II, umumnya 510(k)-exempt), dan di Indonesia (UU 17/2023, KMK HK.01.07/MENKES/951/2026). Untuk proyek mahasiswa, rilis sebagai alat riset/edukasi dengan disclaimer tegas. Jual jasa, bukan lisensi.

## Key Findings

### 1. Lanskap yang ada

| Proyek | Lisensi/model | Cakupan | Status/catatan |
|---|---|---|---|
| Blender for Dental (B4D) | Modul berbayar, sekali beli, bisa dipasang di 3 komputer, tanpa biaya tahunan\[4\] | Model Designer (wajib), Crown & Bridge, Articulator, BlockOut, WaxUp, Splint, Tray, Guide, Gum, Denture Designer, iBar, iAbutment & Bar, Components, Segmentations, EASYEDGES | Menargetkan Blender 4.5 LTS. Harga contoh: Denture Designer USD 599, iAbutment & Bar USD 349, EASYEDGES USD 49. Di distributor Australia, Crown and Bridge AUD 1.174. Halaman shop B4D menulis "Blenderfordental® listed 2462014 as Class 1 Medical Device in the EU" |
| Open Dental CAD (patmo141/odc_public) | GPL | Crown/single unit, implant, splint, alignment, segmentasi, cutback, implant temporary, guide | Versi terakhir ODC v2.0 untuk Blender 2.8. Wiki terakhir diedit 2016. Ada fork (ZAP-Wunschlachen, dentsoft-foundation). Repo pendukung: object_alignment (ICP), cut_mesh\[5\]\[6\]\[7\]\[8\] |
| BDENTAL (issamdakir) | GPL-3.0 | Visualisasi CBCT, perencanaan implant/guide, BDENTAL4D (gerak rahang nyata), BDENTAL_ALIGN | Ada repo update untuk Blender 4. Pengembang tunggal\[9\]\[10\]\[11\] |
| OrtogOnBlender (Cicero Moraes) | Gratis/terbuka | Perencanaan bedah ortognatik\[12\] | Di luar cakupan lab gigi |
| dentsoft-foundation | Terbuka | linkSlicerBlender, slicerPano (implant di 3D Slicer), SlicerModelUndercuts\[13\] | Berguna untuk jembatan ke 3D Slicer |

**Verifikasi "Blender Dental 4.0":** Saya tidak menemukan rilis resmi bernama "Blender Dental 4.0". Label "B4D 4.0.1 (Full Modules)" dan "Blender 4 Dental V5.0" muncul di situs crack/keygen dan video yang menjual versi bajakan.\[14\]\[15\]\[16\] Angka itu kemungkinan merujuk ke versi Blender, bukan versi produk B4D. Versi resmi yang tercatat adalah B4D User Interface v1.5.0 di atas Blender 4.5 LTS.\[12\] Jangan unduh atau rujuk sumber tersebut: ilegal, dan berbahaya untuk prinsip clean room Anda.

**Pembanding komersial:**

| Aspek | exocad DentalCAD | 3Shape Dental System 2025 | B4D |
|---|---|---|---|
| Indikasi inti | Core: anatomic crown, coping, bridge framework, inlay, onlay, veneer, wax-up copy milling, telescope, attachment\[17\] | Crown & bridge lengkap. Paket Premium: Splint dan Smile Design\[18\] | Per modul |
| Modul tambahan (harga toko AS) | Implant USD 2.160, Bar 2.160, Model Creator 2.640, Bite Splint 2.160, Provisional 870, PartialCAD 2.640, Full Denture 2.640, Virtual Articulator 1.080, Jaw Motion 1.000, DICOM Viewer 840, Smile Creator 1.900\[19\] | Abutment Designer, Implant Bar & Bridge, RPD, Full Denture, Model Builder\[18\] | Sekali beli per modul |
| AI | Kurang menonjol | Automate: proposal AI untuk crown, inlay/onlay, coping anatomis, bridge cemented hingga 4 unit. Bite alignment AI. Fair use 1.200 unit/seat/tahun\[20\]\[21\] | Tidak ada (filosofi "control over automation")\[22\] |
| Ekspor CAM | STL + XML constructionInfo (margin, sumbu insersi)\[23\] | STL/DCM | STL |
| Kurva belajar | Wizard terpandu | Wizard terpandu | Curam (Blender murni)\[24\] |

**Celah tempat Anda bisa "lebih powerful":**
1. **Wizard terpandu sungguhan.** B4D mengandalkan pengguna untuk mengingat urutan langkah.\[24\] exocad dan 3Shape memandu langkah demi langkah.
2. **Validasi desain otomatis.** Peta ketebalan, luas konektor, undercut, dan jarak ke antagonis dicek terhadap tabel material terbuka yang bersumber dari IFU.
3. **Terbuka, bisa diaudit, bisa diuji.** Ini satu-satunya keunggulan yang tidak bisa disaingi B4D.
4. **Margin semi-otomatis berbasis curvature**, dengan jalur ke model ML di masa depan.
5. **Pipeline headless** (`blender --background`) untuk batch, misalnya model cetak massal.

### 2. Parameter material (dari IFU pabrikan dan literatur)

| Material | Crown min. (anterior/posterior) | Konektor bridge (anterior/posterior) | Sumber |
|---|---|---|---|
| IPS e.max ZirCAD Prime (full-contour) | 0,8 / 1,0 mm | 3 unit: 9 / 9 mm². 4+ unit, 2 pontik: 9 / 12 mm². Kantilever 12 mm² (4 mm tinggi × 3 mm lebar) | Ivoclar IFU ZirCAD labside 2023\[25\] |
| ZirCAD Prime (framework untuk layering) | 0,4 / 0,6 mm | 9 / 9 mm² | sama\[25\] |
| ZirCAD MT/MT Multi/Prime Esthetic | 0,8 / 1,0 mm | 12 / 16 mm², maksimal 3 unit, 1 pontik | sama\[25\] |
| ZirCAD LT/MO | 0,4 / 0,6 mm | 3 unit 7 / 9 mm². 4+ unit 9 / 12 mm² | sama\[25\] |
| IPS e.max Zirconia | 0,6 / 0,7 mm | Kantilever: 10 / 15 mm² | Ivoclar Technical Guide\[26\] |
| KATANA STML/UTML | 0,8 / 1,0 mm. Veneer 0,4 mm | 12 / 16 mm². Tidak untuk kantilever | Kuraray Noritake Technical Guide\[27\]\[28\]\[29\] |
| 3M Lava Esthetic | ≥0,8 mm | ≥12 / ≥14 mm², maksimal 1 pontik | 3M Quick Start Guide\[30\]\[31\] |
| IPS e.max CAD (lithium disilikat) | Standar sekitar 1,5 mm occlusal. Adhesif minimal 1 mm. Cut-back: e.max minimal 50% dari total ketebalan | 16 mm² (tinggi ≥ lebar) | Ivoclar IFU\[32\]\[33\]\[34\] |
| e.max CAD hybrid abutment / hybrid abutment crown | Dinding abutment ≥0,5 mm. HAC >1,5 mm. Lebar dibatasi 6,0 mm dari screw channel\[35\] | | Ivoclar Abutment Solutions IFU |
| Telio CAD (PMMA) | Occlusal 1,5 mm, sirkular 0,8 mm | 12 mm². Posterior 2 pontik 16 mm² | Ivoclar IFU 2025\[36\] |
| VITA CAD-Temp (PMMA) | Occlusal 1,5 mm, sirkular 0,8 mm | Anterior 12 mm². Posterior 12 mm² (1 pontik) / 16 mm² (2 pontik) | VITA IFU\[37\] |
| VITA Enamic (hybrid) | Occlusal ≥1,0 mm, sirkular ≥0,8 mm. Veneer 0,2-0,3 mm\[38\] | Single unit saja | VITA 1982E |
| Tetric CAD (komposit) | Occlusal 1,5 mm, sirkular crown 0,8 mm | Single unit saja | Ivoclar IFU\[39\]\[40\] |
| CoCr SLM (remanium star CL) | Hasil akhir ≥0,3 mm | IFU tidak memberi angka konektor. Pusat milling memakai ≥7 mm² | Dentaurum IFU 2026, CADdent\[41\]\[42\] |
| CoCr/Ti milled | Dinding ≥0,4 mm | ≥7 mm² (pedoman pusat milling, bukan IFU) | CADdent\[43\] |
| Maryland zirkonia (kantilever) | Wing ≥0,7 mm (jangan pernah <0,5) | ≥3 mm tinggi × 2 mm lebar | Kern & Gläser, J Esthet Restor Dent 2023\[44\]\[45\]\[46\] |

**Catatan:** Untuk titanium belum ada IFU spesifik yang saya temukan. Ada juga konflik untuk KATANA STML: satu halaman produk menulis 7/9 mm², sedangkan technical guide menulis 12/16 mm².\[47\]\[48\] Pakai technical guide. Bentuk konektor tampaknya kurang menentukan dibanding luasnya: studi J Adv Prosthodont 2023 (15(4):171-178, bridge zirkonia Katana 3 unit) menemukan beban fraktur "not affected by the connector configuration when the connector had a cross-sectional area of 9 mm²" (4Y-TZP: 1.868 N untuk 4 × 2,25 mm vs 1.664 N untuk 3 × 3 mm, tidak signifikan), meski bagian diskusinya menyebut 4 × 2,25 mm sebagai konektor minimum yang lebih disukai.

**Cement gap:** literatur tidak seragam.\[49\]\[50\] Studi pada zirkonia monolitik menemukan bahwa menaikkan gap dari 30 ke 50 µm memperbaiki marginal fit.\[49\] Studi e.max dengan gap 50/100/200 µm menghasilkan marginal gap rata-rata 126/89/75 µm.\[51\] CEREC disebut merekomendasikan 100 µm untuk inlay/onlay dan 120 µm untuk crown.\[50\] Batas klinis yang lazim dipakai adalah marginal gap ≤120 µm (McLean & von Fraunhofer).\[52\] Umbrella review Dudley & Farook (J Prosthet Dent 2026) atas 17 systematic review mencatat marginal gap rata-rata 79,4 ±22,8 µm dan menyebut 120 µm sebagai batas in vitro yang dapat diterima. **Default yang disarankan:** gap 0 µm sampai 0,5-1,0 mm dari margin (distance to margin), lalu 30-60 µm aksial/occlusal. Nilainya dapat dikalibrasi per mesin dan material dengan uji fit.

## Details

### 3. Cakupan indikasi dan alur kerja (urut prioritas)

| Prioritas | Indikasi | Alur inti (langkah teknisi) | Parameter kunci |
|---|---|---|---|
| P1 | Crown anatomis penuh (zirkonia, e.max) | Impor scan → orientasi/oklusal plane → potong die → margin (auto + edit) → sumbu insersi + cek undercut → gap/spacer → proposal library + morphing → kontak proksimal/oklusal → freeform → cek ketebalan → merge/watertight → ekspor | Gap, distance to margin, min. thickness, kontak proksimal (sekitar 0,0-0,05 mm overlap), jarak oklusal |
| P1 | Bridge | Seperti crown + pontik + konektor | Tipe pontik: ovate (ekstraksi baru/estetik), modified ridge lap (paling umum anterior), sanitary/hygienic (posterior bawah, 2-3 mm clearance), conical/bullet. Luas konektor per material (tabel di atas) |
| P1 | Model cetak | Trim → base (hollow/solid) → sectioned model → removable die + ditching → pin/keying → label → plug articulator → ekspor | Clearance die-socket 0,05-0,1 mm, tebal dinding hollow 2-3 mm, lubang drainase resin |
| P2 | Coping/reduced/cutback | Anatomis lalu cutback (uniform/anatomis) | Framework ≥50% dari total (e.max), ZirCAD framework 0,4/0,6 mm\[25\]\[32\] |
| P2 | Inlay/onlay/veneer | Margin pada kavitas, sumbu insersi wajib tanpa undercut | Veneer 0,3-0,4 mm, inlay ≥1,0-1,5 mm |
| P2 | Virtual articulator | Bite registration (ICP), Bonwill/Balkwill default, condylar guidance 30°, Bennett 15°, protrusi/laterotrusi → envelope "functional generated path" | Sudut dapat diedit, kontak ditandai warna |
| P2 | Provisional/eggshell | Pre-op scan atau library → shell eggshell\[53\] | PMMA 1,5/0,8 mm, konektor 12-16 mm²\[54\] |
| P2 | Bite splint/night guard | Survey + block-out → outline → ketebalan → flat plane + ramp kaninus → ekspor cetak | 1,5-3 mm, retensi undercut 0,2-0,3 mm |
| P3 | Implant (abutment custom, screw-retained, Ti-base hybrid) | Scanbody matching (ICP) → library komponen (interface dari pabrikan) → emergence profile → screw channel (lurus/angled, umumnya hingga 25°) → crown | Batas lebar 6 mm dari channel (e.max HAC), minimum wall Ti-base ≥0,5-0,7 mm\[26\]\[35\] |
| P3 | Smile design/wax-up/mock-up | Foto 2D + scan → library → mock-up cetak | Proporsi lebar/tinggi |
| P4 | Bar implan, RPD (survey, block-out, rest, clasp, major/minor connector), full denture | Survey → block-out → rest → clasp (retentive 0,25/0,5 mm undercut untuk CoCr/akrilik) → connector | Kompleks, butuh validasi berat |
| P5 | Surgical guide (CBCT), aligner/ortho | Integrasi BDENTAL/3D Slicer, jangan dibangun dari nol | Risiko klinis tertinggi |

**Keputusan:** surgical guide dan aligner terlalu kompleks dan berisiko untuk satu developer. Integrasikan dengan proyek GPL yang sudah ada (BDENTAL, slicerPano). RPD dan full denture masuk tahun ke-2.

### 4. Konsep teknis inti

- **Margin line:** mulai dengan pendekatan semi-otomatis. Klik satu titik, lalu cari jalur di graf mesh dengan biaya rendah pada curvature minimum terbesar (geodesic/Dijkstra pada principal curvature). Haluskan dengan spline dan energy minimization, lalu edit dengan drag.\[55\] Riset terbaru memakai deep learning: Alsheghri et al., Comput Biol Med 2025, dengan 1.113 die.\[56\] Varian PointNet++ dengan tambahan kanal curvature (arXiv 2507.22859).\[57\] Paten lama (US 8.359.114) juga menyebut deteksi berbasis curvature dan silhouette.\[58\] **Lakukan cek paten** sebelum meniru metode spesifik.
- **Sumbu insersi dan undercut:** default rata-rata normal area preparasi. Undercut = face yang `dot(normal, axis) < 0` di bawah kontur terbesar. Visualisasikan dengan heatmap. Block-out dilakukan dengan menyapu proyeksi sepanjang sumbu.
- **Spacer:** offset permukaan internal sepanjang normal, dimodulasi oleh jarak geodesik ke margin.
- **Ketebalan:** ray-cast dari permukaan dalam ke luar (BVHTree `mathutils.bvhtree`), lalu tampilkan heatmap dan kunci minimum.
- **Konektor:** potong penampang di bidang antar-gigi, hitung luas poligon, beri warna merah di bawah ambang material.
- **Tooth library dan morphing:** library harus **dibuat sendiri** (scan model gigi sendiri, berlisensi CC0/CC-BY). Morphing memakai landmark (cusp, kontur) + deformasi RBF/Laplacian dan fit ke margin.
- **Penomoran:** FDI (ISO 3950) sebagai internal, konversi ke Universal dan Palmer di UI.
- **Milling:** kompensasi bur (offset internal, drill compensation pada sudut dalam di bawah radius bur, mis. Ø 0,6/1,0 mm), radius minimum fisur ≥ radius bur. Nesting, sprue, dan connector ke disc **tetap di MillBox**. Add-on hanya menandai ketebalan yang bisa dimilling ("anticipate milling" seperti parameter Ivoclar).\[59\]

### 5. Data dan interoperabilitas

| Format | Pakai | Catatan |
|---|---|---|
| STL | Impor/ekspor utama, ke MillBox dan slicer printer | MillBox bisa mengimpor STL tanpa metadata. Kurva margin bisa dideteksi atau digambar manual di MillBox\[60\] |
| PLY (warna vertex) | Impor scan IOS berwarna | Blender 4.x punya importer PLY native |
| OBJ, 3MF | Ekspor ke printer resin | 3MF untuk unit dan orientasi |
| DICOM | CBCT | Lewat pydicom/BDENTAL/3D Slicer |
| Format proprietary (DCM 3Shape, dentalProject, constructionInfo exocad) | **Jangan dibaca/ditulis lewat reverse engineering** | Minta pengguna mengekspor STL/PLY dari software asal (Medit Link, 3Shape, iTero menyediakan ekspor terbuka) |

**Sikap legal untuk interoperabilitas:** baca dan tulis hanya format terbuka. exocad sendiri menyebut constructionInfo sebagai "open XML format" dan MillBox membacanya.\[61\]\[62\] Meski begitu, **jangan menulis file berformat exocad** tanpa dokumentasi resmi. Jalur yang bersih ada dua: (a) STL bersih + MillBox mendeteksi margin, atau (b) minta dokumentasi format impor resmi ke CIMsystem dan ajukan integrasi sebagai mitra. Tanyakan juga ke konsultan hukum tentang pengecualian interoperabilitas di hukum hak cipta. Jangan berasumsi.

### 6. Arsitektur di Blender

- **Target:** Blender 4.5 LTS (sama seperti B4D) dan 5.x. Paketkan sebagai Extension dengan `blender_manifest.toml`. Dependensi dipaketkan sebagai wheel di `./wheels/` untuk semua platform. Wheel harus asli dari PyPI dan termasuk dependensinya.\[12\]\[63\]\[64\]
- **Library:** numpy (bawaan), `mathutils.bvhtree`/KDTree (bawaan, cepat), manifold3d (Apache-2.0, boolean watertight terjamin, juga solver boolean Blender sejak 4.5), trimesh (MIT), scipy (sparse solver untuk Laplacian), Open3D (MIT, ICP, besar).\[65\]\[66\]\[67\]\[68\] libigl/CGAL: hindari dulu (CGAL berlisensi GPL/komersial dan bundling-nya berat).
- **Performa untuk 300 ribu sampai 2 juta segitiga:** hindari loop Python per-vertex. Pakai `foreach_get/foreach_set` ke numpy, operasi vektor, BVH bawaan. Bmesh hanya untuk region kecil (die, margin). Lakukan decimate adaptif di luar ROI. Overlay interaktif memakai modul `gpu` dengan batch shader yang di-cache.
- **Tool interaktif:** modal operator (gambar margin, drag kontak, sculpt terbatas) + `gpu` draw handler + gizmo untuk sumbu insersi.
- **UX ala software dental:** workspace "Dental" khusus (viewport tanpa clutter, N-panel wizard), state machine kasus (Order → Scan → Margin → Design → Check → Export), undo per langkah, preset material dari JSON, mode "Expert" untuk membuka Blender penuh.
- **Struktur proyek:**
```
dentalcad/
  blender_manifest.toml
  __init__.py
  core/        # geometri murni numpy (bisa diuji tanpa Blender)
  ops/         # operator bpy
  ui/          # panel, workspace, wizard
  gpu_draw/
  data/materials/*.json, libraries/ (CC0)
  wheels/
tests/         # pytest (core) + blender --background (integrasi)
```
- **Testing:** fungsi `core/` murni dan diuji di CI (GitHub Actions). Tes integrasi memakai `blender --background --python`. Siapkan golden case STL anonim dengan target metrik (ketebalan min., luas konektor, watertight, deviasi margin).
- **Kerja dengan Claude Code (opusplan):** Opus menyusun spesifikasi per fitur (input, output, metrik penerimaan). Sonnet mengimplementasikan modul `core/` dengan tes lebih dulu. Wajibkan tes golden sebelum merge.

### 7. Lisensi dan regulasi

| Aspek | Fakta | Implikasi |
|---|---|---|
| GPL Blender | Situs Blender menyatakan skrip yang memakai API Python Blender, bila dipublikasikan, harus GPL-compliant. Extensions Platform mewajibkan add-on GPL-3.0-or-later, aset CC0, tanpa registrasi/pembayaran/kunci yang memblokir fungsi, tanpa kode remote\[1\]\[2\]\[69\] | Kode wajib terbuka. Monetisasi lewat jasa desain, pelatihan, support, kustomisasi lab, dan hosting. Aset library bisa dijual terpisah di luar Extensions Platform (lisensi aset berbeda dari kode, tapi tetap konsultasikan)\[70\] |
| FDA | 21 CFR 872.3661 (kode NOF, "CAD/CAM of dental restorations") kelas II, exempt dari 510(k) dengan batasan 872.9. Software desain abutment implan biasanya masuk 510(k) (contoh K171466, kode NHA 872.3630)\[71\]\[72\]\[73\] | Modul implant/abutment adalah area risiko regulasi tertinggi |
| EU MDR | Software diklasifikasikan lewat Rule 11 (default IIa untuk informasi keputusan diagnosis/terapi, sisanya kelas I). Lab adalah produsen custom-made device (Annex XIII).\[74\]\[75\]\[76\] Ada draf Komisi Eropa Desember 2025 untuk merevisi Rule 11 (masih usulan)\[77\]\[78\]\[79\] | B4D mengklaim terdaftar kelas I di EU\[80\] (listing 2462014, menurut halaman shop B4D) |
| Indonesia | UU 17/2023 memasukkan perangkat lunak dalam definisi alat kesehatan.\[81\] Izin edar diatur Permenkes 62/2017 (kelas A-D) via Regalkes, dengan IDAK untuk distributor.\[82\]\[83\] KMK HK.01.07/MENKES/951/2026 (ditetapkan 7 September 2026) adalah pedoman izin edar alat kesehatan berbasis perangkat lunak (SaMD, SiMD, AI).\[81\]\[84\] Menurut ringkasan Pure Global (Oktober 2026), KMK 951/2026 mewajibkan dokumentasi siklus hidup software sesuai IEC 62304 atau standar setara, dengan rujukan standar lain seperti ISO 13485, ISO 14971, IEC 62366-1 dan IEC 82304 | Distribusi komersial sebagai alat kesehatan butuh NIE.\[82\]\[85\] Rilis riset/edukasi tetap berisiko bila dipasarkan untuk pasien |

**Disclaimer minimal (di README, splash, ekspor):** "Perangkat lunak riset dan edukasi. Bukan alat kesehatan bersertifikat. Tanpa jaminan (GPL bagian 15-16). Setiap restorasi harus diverifikasi oleh teknisi/dokter gigi berkualifikasi sesuai IFU material. Pengguna bertanggung jawab sebagai produsen custom-made device."

## Recommendations: Roadmap

| Fase | Durasi (part-time) | Deliverable | Kriteria selesai |
|---|---|---|---|
| 0. Fondasi | 4-6 minggu | Skeleton Extension, wheels (manifold3d, scipy), impor STL/PLY, workspace Dental, CI, 10 golden case anonim | Instal bersih di Win/Mac/Linux. Impor scan 1 juta segitiga di bawah 5 detik |
| 1. Model Creator | 6-8 minggu | Trim, base, hollow, sectioned model, removable die, ditching, label, ekspor printer | 5 model nyata tercetak, die masuk socket tanpa adjust, ditinjau teknisi senior |
| 2. Crown zirkonia single | 10-12 minggu | Margin semi-auto, sumbu insersi/undercut, spacer, library CC0 + morphing, kontak, heatmap ketebalan, ekspor STL ke MillBox | 20 kasus: deviasi margin vs desain exocad ≤50 µm (median), lolos cek ketebalan, 5 crown dimilling dan dicoba di die |
| 3. Bridge + material DB | 8 minggu | Pontik (4 tipe), konektor dengan pengukur mm², preset Ivoclar/Kuraray/3M/VITA dari IFU | Semua konektor teruji otomatis. 5 bridge nyata dimilling |
| 4. Articulator + provisional + splint | 10 minggu | Artikulator semi-adjustable, eggshell PMMA, night guard | Kontak dinamis konsisten dengan exocad pada kasus yang sama |
| 5. Implant (riset) | 12+ minggu | Scanbody ICP, library terbuka (hanya data yang dirilis pabrikan secara sah), Ti-base hybrid, screw channel | Hanya untuk uji lab. Belum untuk pasien tanpa jalur regulasi |
| 6+. RPD, denture, integrasi BDENTAL/Slicer, margin ML | Tahun ke-2 | | |

**Validasi dengan kasus nyata:** minta izin tertulis dari pemilik lab dan dokter. Anonimkan data (hapus nama dan ID dari file serta metadata). Lakukan desain paralel: kasus yang sama didesain di exocad (produksi tetap dari exocad) dan di add-on Anda. Bandingkan dengan deviasi mesh (Hausdorff), ketebalan, dan luas konektor. Restorasi dari add-on hanya dimilling untuk uji fit di die, **bukan** dipasang ke pasien sampai ada QMS dan jalur regulasi.

**Diferensiasi utama vs B4D:** (1) gratis dan GPL tanpa paywall modul; (2) wizard terpandu; (3) quality gate otomatis berbasis IFU; (4) dapat diuji dan headless; (5) basis data material yang terbuka dan bisa ditambah komunitas; (6) jalur ke margin/proposal berbasis AI yang terbuka.

## Caveats
- Banyak IFU yang dikutip adalah salinan dari distributor. Cek revisi terbaru di situs pabrikan sebelum dijadikan default.
- Harga B4D dan exocad berubah. Angka di atas adalah snapshot dari toko online.
- Default cement gap dan parameter artikulator adalah titik awal yang harus dikalibrasi, bukan nilai klinis final.
- Saya tidak memverifikasi teks lengkap KMK 951/2026. Ringkasan berasal dari JDIH Kemenkes dan ulasan pihak ketiga. Baca dokumen resminya.
- Klaim "lebih powerful" baru valid setelah validasi berbasis kasus. Sampai saat itu, posisikan sebagai alat riset dan edukasi.

## Sources

1. [Extension Licenses - Blender 5.2 LTS Manual](https://docs.blender.org/manual/en/latest/advanced/extensions/licenses.html)
2. [docs(repo): evaluate licence alternatives to GPL-3.0-or-later and record the decision · Issue #26 · scenario-labs/blender-plugin · GitHub](https://github.com/scenario-labs/blender-plugin/issues/26)
3. [Relicense to GPL-3.0-or-later for the Extensions Platform by iamahsanmehmood · Pull Request #6 · iamahsanmehmood/blender-openskp · GitHub](https://github.com/iamahsanmehmood/blender-openskp/pull/6)
4. [Crown & Bridge now available!](https://www.blenderfordental.com/post/crown-bridge-now-available)
5. [Home · patmo141/odc\_public Wiki · GitHub](https://github.com/patmo141/odc_public/wiki)
6. [GitHub - ZAP-Wunschlachen/odc\_public: Addon for Blender meant to streamline dental CAD and design workflows · GitHub](https://github.com/ZAP-Wunschlachen/odc_public)
7. [patmo141 - Overview](https://github.com/patmo141)
8. [odc\_public/\_\_init\_\_.py at master · patmo141/odc\_public · GitHub](https://github.com/patmo141/odc_public/blob/master/__init__.py)
9. [GitHub - issamdakir/BDENTAL4D-WIN: Blender addon for Digital Dentistry with real 4D motion · GitHub](https://github.com/issamdakir/BDENTAL4D-WIN)
10. [BDENTAL](https://kandi.openweaver.com/python/issamdakir/BDENTAL)
11. [issamdakir (Dr issam Dakir) · GitHub](https://github.com/issamdakir)
12. [Blender (Dental add-ons) - Dentiit.com](https://dentiit.com/program/blender-dental-add-ons/)
13. [dentsoft-foundation - Overview](https://github.com/dentsoft-foundation)
14. [Blender 4 Dental V5.0 (B4D) The Complete Guide For Dental Labs Ready To Move Beyond Exocad - TeamArmaan](https://teamarmaan.com/blender-4-dental/)
15. [🦷 Blender For Dental 4.0.1 (Full Modules) 🦷 - YouTube](https://www.youtube.com/watch?v=yOvNDJeAiMk)
16. [blender for dental (B4D) 4.0.1 - dental software crack](https://dentalsoftcrack.net/product/blender-for-dental-b4d-4-0-1/)
17. [exoCAD®](https://www.go3dpro.com/exocad-dental-cad-software.html)
18. [3Shape Dental System — Functionality and Efficiency Always](https://esmdigitalsolutions.com/dental-system/)
19. [DentalCAD add-on modules](https://shop.exocad.com/us_en/dentalcad-add-on-module.html)
20. [3Shape Automate in Dental System - 3Shape](https://support.3shape.com/lab-dental-system-setup-how-to/3shape-automate-in-dental-system)
21. [3Shape Introduces AI-Powered Workflows for Dental Laboratories](https://compendiumlive.com/news/?newsID=104786)
22. [The Check Before the Cut: Mastering Upper Bridge Design in B4D](https://www.blenderfordental.com/post/the-check-before-the-cut-mastering-upper-bridge-design-in-b4d)
23. [Merge and Save restorations - exocad](https://wiki.exocad.com/wiki/index.php/Merge_and_Save_restorations)
24. [Blender for Dental: An Honest Review of the Free Dental CAD](https://exoinstall.com/en/blog/blender-for-dental/)
25. <https://www.caddent.de/fileadmin/PDF/DEU/Datenblaetter/Fraesen/747728_emax_ZirCAD_lab_GI_WW_REV1_9Oct23__1_.pdf>
26. [IPS e.max® Zirconia — Technical Guide](https://content.ivoclar.com/en/digital-dentistry-and-dental-technology-the-dental-world-in-transition)
27. [KATANA™ ZIRCONIA RESTORATION SYSTEM - Abicart](https://cdn.abicart.com/shop/19433/art95/177817095-1a7832-20709_1%20Katana%20material%20brochure.pdf)
28. [MULTI-LAYERED SERIES TECHNICAL GUIDE KATANA™ ZIRCONIA](https://www.bego.com/fileadmin/user_downloads/Mediathek/Medical/en_Keramik/KATANA_Zirconia/KATANA-stml-utml-technical-guide-en.pdf)
29. [Kuraray Noritake KATANA™ Zirconia UTML](https://katanazirconia.com/katana-zirconia-utml/)
30. [Technical Product Profile 3M™ Lava™ Esthetic](https://multimedia.3m.com/mws/media/1587012O/3m-lava-esthetic-zirconia-technical-product-profile.pdf)
31. [3M™ Lava™ Esthetic Esthetic Fluorescent Full-Contour Zirconia](https://multimedia.3m.com/mws/media/1374888O/3m-lava-esthetic.pdf)
32. [CAD Monolithic Solutions LABSIDE Instructions for Use all ceramic all you need](https://ivodent.hu/__docs/874_25e427eebe65d0b2a7f79bdd4e0269ad.pdf)
33. [IPS e.max® CAD bridge CAD all ceramic all you need Date information prepared:](https://ivodent.hu/__docs/669_bd3e3daa0737e94aee7e125c8da377e2.pdf)
34. [Minimally invasive crown preparation for lithium disilicate glass-ceramic](https://www.ivoclar.com/medias/sys_master/celum-connect2-assets/celum-connect2-assets/h95/h71/10112665124894/IPS-emax-CAD-Press-Adhesive-1mm-Crown.pdf)
35. [CAD Abutment Solutions Instructions for Use IPS e.max ® all ceramic](https://www.cadmill.de/wp-content/uploads/IPS-e.max-CAD_Instructions-for-Use_English_V00_13022.pdf)
36. [Telio® CAD Date information prepared: 2025-07-16 / Rev. 0 Manufacturer:](https://www.dt-shop.com/fileadmin/media/ga/1549_ga_enu.pdf)
37. [VITA CAD-Temp® VITA](https://mam.vita-zahnfabrik.com/portal/ecms_mdb_download.php?id=126756&sprache=en&fallback=en-de&neuste_version=1)
38. [VITA ENAMIC ® VITA](https://us-store.vitanorthamerica.com/en-us/product/attachment/EN1EC4122885/vita_enamic_instruction_for_use_1982e_v10.pdf)
39. [Tetric ® CAD Instructions for Use](https://ivodent.hu/__docs/714_43401012ee9a338d903ddae5d3636ed9.pdf)
40. [Tetric® CAD Scientific Documentation](https://www.ivoclar.com/medias/tetric-cad-scidocs-us-en.pdf?context=bWFzdGVyfGNlbHVtLWNvbm5lY3QyLWFzc2V0c3wyMDM0NTUwfGFwcGxpY2F0aW9uL3BkZnxjZWx1bS1jb25uZWN0Mi1hc3NldHMvaGUxL2gyNS8xMDM3MTQ5NDM0Njc4Mi5wZGZ8MmFiYzAwNzdmNGY3Zjk2Y2ZjY2QyYjExZTk4MGI0YzU2Yjc0ODUxOTdmNjlmMmI0Mjk3YzdjMmY5NDQ0NTE5MQ)
41. [Parameter recommendation 3Shape W W W . C A D D E N T . E U LASERMELTING](https://www.caddent.de/fileadmin/PDF/ENG/Parameterempfehlungen/Parameter-Empfehlung_3Shape_ENG.pdf)
42. [Gebrauchsanweisung · Instructions for use ·](https://www.dentaurum.com/files/989-803-35_2026-04.pdf)
43. [Parameter recommendation Exocad W W W . C A D D E N T . E U SERVICE 3D-PRINTING](https://www.caddent.de/fileadmin/PDF/ENG/Parameterempfehlungen/Parameter-Empfehlung_ExoCad_ENG.pdf)
44. [Single‐retainer all‐ceramic resin‐bonded fixed dental prostheses: Long‐term outcomes in the esthetic zone - Kern - 2023 - Journal of Esthetic and Restorative Dentistry - Wiley Online Library](https://onlinelibrary.wiley.com/doi/full/10.1111/jerd.13001)
45. [Long-term outcome of anterior cantilever zirconia ceramic resin-bonded fixed dental prostheses: Influence of the pontic location - The Journal of Prosthetic Dentistry](<https://www.thejpd.org/article/S0022-3913(25)00071-X/fulltext>)
46. [(PDF) All-ceramic resin-bonded fixed dental prostheses: Treatment planning, clinical procedures, and outcome](https://www.researchgate.net/publication/260382683_All-ceramic_resin-bonded_fixed_dental_prostheses_Treatment_planning_clinical_procedures_and_outcome)
47. [Kuraray Noritake KATANA™ Zirconia STML](https://kuraraydental.com/product/katana-zirconia-stml/)
48. [UTML Ultra Translucent Multi-Layered STML Super Translucent Multi-Layered](https://www.kuraraynoritake.com/world/product/cad_materials/pdf/katana_zircinia_technical_guide.pdf)
49. [Effect of cement space on the marginal fit of CAD-CAM-fabricated monolithic zirconia crowns](https://www.researchgate.net/publication/305664337_Effect_of_cement_space_on_the_marginal_fit_of_CAD-CAM-fabricated_monolithic_zirconia_crowns)
50. [The Effect of Cement Space Parameters on the Marginal Adaptation of Milled Endocrowns: An In Vitro Study](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC10246932/)
51. [The influence of different cement spaces on the marginal gap of CAD/CAM all-ceramic crowns - PubMed](https://pubmed.ncbi.nlm.nih.gov/30883797/)
52. [Influence of tooth preparation design on margin discrepancy and internal gap in digitally fabricated fixed complete coverage zirconia prostheses: A systematic review of in vitro studies - ScienceDirect](https://www.sciencedirect.com/science/article/pii/S0022391325003853)
53. [exocad DentalCAD Provisional Module](https://www.3dprimetech.com/cad-cam-software/exocad/provisional-module)
54. [Technical data sheet PMMA Disc TELIO CAD® Manufacturer Ivoclar Vivadent AG](https://www.cadstar.dental/download/151/materialdokumentation-en/5667017/cadstar-pmma-telio-cad-2.pdf)
55. [Deep learning-based automated detection of the dental crown finish line: An accuracy study](https://www.researchgate.net/publication/376497919_Deep_learning-based_automated_detection_of_the_dental_crown_finish_line_An_accuracy_study)
56. [Automatic margin line extraction using 3D deep learning on digital surface models of prepared teeth for crown generation - ScienceDirect](https://www.sciencedirect.com/science/article/abs/pii/S0010482525013125)
57. [Pre-print Mesh-based segmentation for automated margin line](https://arxiv.org/pdf/2507.22859)
58. [Haptically enabled dental modeling system](https://image-ppubs.uspto.gov/dirsearch-public/print/downloadPdf/8359114)
59. [ivoclardigital.com IVOCLAR DIGITAL\_SOFTWARE PARAMETER CHART\_EXOCAD IPS e.max](https://ivodent.hu/__docs/537_70224e7253c2b4afca6ef3d949adef91.pdf)
60. [MillBox](https://www.cimsystem.com/dental/products/millbox-release-notes/)
61. [CAM integration - exocad](https://exocad.com/integration/cam-integration)
62. [exocad.com Performance Specifications Dental Software 03/2019 exocad GmbH](https://shop.exocad.com/media/sales/Perf-Spec-Dental-CAD-Module-en.pdf)
63. [Python Wheels - Blender 5.2 LTS Manual](https://docs.blender.org/manual/en/latest/advanced/extensions/python_wheels.html)
64. [How to Create Extensions - Blender 5.2 LTS Manual](https://docs.blender.org/manual/en/latest/advanced/extensions/getting_started.html)
65. [trimesh · PyPI](https://pypi.org/project/trimesh/)
66. [Manifold Boolean feedback - Feature & Design Feedback - Developer Forum](https://devtalk.blender.org/t/manifold-boolean-feedback/40150)
67. [manifold3d 3.5.2 on PyPI - Libraries.io - security & maintenance data for open source software](https://libraries.io/pypi/manifold3d)
68. [Library for geometric robustness](https://pypi.org/project/manifold3d/)
69. [Terms of Service — Blender Extensions](https://extensions.blender.org/terms-of-service/)
70. [The GPL and the Legal Limits of What You Can Do with Blender - CG Cookie](https://cgcookie.com/posts/the-gpl-and-the-legal-limits-of-blender)
71. [U.S. Food & Drug Administration 10903 New Hampshire Avenue](https://www.accessdata.fda.gov/cdrh_docs/pdf17/K171466.pdf)
72. [GHTF & MDD Risk Rule FDA GHTF MDD Rule # Measurer, gingival fluid 872.1500 JEO](https://webgate.ec.europa.eu/circabc-ewpp/rest/download/fd305127-a2c4-45c6-8448-f9f0f0fca09d)
73. [21 CFR § 872.3661 - Optical Impression Systems for CAD/CAM.](https://www.law.cornell.edu/cfr/text/21/872.3661)
74. [Classification of Medical Devices Under EU MDR (2025)](https://decomplix.com/medical-device-classification-eu-mdr/)
75. [EU MDR and IVDR: Classifying Medical Device Software (MDSW) - NAMSA](https://namsa.com/resources/blog/eu-mdr-and-ivdr-classifying-medical-device-software-mdsw/)
76. [Dental Devices Under EU MDR: Clinical Evaluation and PMCF](https://www.celegence.com/dental-medical-devices-eu-mdr-clinical-evaluation-pmcf/)
77. [Frontiers](https://www.frontiersin.org/journals/dental-medicine/articles/10.3389/fdmed.2023.1155820/full)
78. [MDR Classification Rule 11: The classification nightmare?](https://blog.johner-institute.com/regulatory-affairs/mdr-rule-11/)
79. [Software as a Medical Device （SaMD): MDR Certification & Classification](https://www.dqsglobal.com/en/explore/dqs-knowledge-center/medical-device-software-mdr-certification-guide)
80. [SHOP](https://www.blenderfordental.com/shop)
81. [Regulasi Alat Kesehatan Berbasis Perangkat Lunak di Indonesia](https://legawa.com/2026/09/10/kmk-951-2026-alat-kesehatan-perangkat-lunak/)
82. [Registrasi Perangkat Lunak Alat Kesehatan di Indonesia](https://insightof.id/registrasi-perangkat-lunak-alat-kesehatan-di-indonesia/)
83. [Registering Medical Device Software in Indonesia - ICI - INSIGHTOF Consulting Indonesia](https://insightof.id/registering-medical-device-software-in-indonesia/)
84. [JDIH Kementerian Kesehatan RI](https://jdih.kemkes.go.id/documents/keputusan-menteri-kesehatan-republik-indonesia-nomor-hk0107menkes9512026)
85. [Legalitas Software AI Alat Kesehatan: Tanggung Jawab & Perlindungan](https://siplawfirm.id/resources/legalitas-software-ai-alat-kesehatan-tanggung-jawab-perlindungan-pasien)
