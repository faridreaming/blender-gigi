# Fase 2: Crown zirkonia single (rancangan)

Status: **langkah implementasi pertama selesai** (2026-10-23): scipy + zip per platform (§6), `zircad_prime.json` dengan angka IVO (§2), dan `core/synthetic.py` (§4). **§5.1 margin semi-otomatis ditutup** (2026-10-24) dengan ringkasan status di akhir §5.1: terbukti pada data sintetis saja, dan **belum divalidasi dengan scan asli**. Hasil Detect dan Draw selalu berstatus **draf**, hanya margin yang sudah di-**Confirm** yang boleh dipakai langkah crown dan ekspor, dan segmen merah hanya petunjuk ringan. **§5.2 sumbu insersi dan undercut terimplementasi** (2026-10-24), juga hanya terbukti pada data sintetis (hasil di §5.2). **§5.3 spacer terimplementasi** (2026-10-24) dengan normal dihaluskan dan block-out kedua untuk milling 3/4 axis, sama-sama hanya terbukti pada data sintetis (hasil di §5.3). Catatan paten: EP2187833B1 (Institut Straumann AG) masih aktif di Eropa menurut Google Patents (perkiraan berakhir 2028-07-24). Versi AS US20100233659 ditinggalkan sejak 2014. Pengguna di Eropa sebaiknya mematikan block-out kedua (`use_second_block_out`) sampai paten berakhir. Ini bukan kesimpulan hukum. **§5.4 langkah 1 sampai 3 terimplementasi** (2026-10-25): template parametrik, penempatan, dan penyesuaian ke tetangga dan antagonis sintetis; lipatan pada scallop dalam dari set ukur pertama diperbaiki (dasar template mengikuti margin, zona campur dalam mm), dan set ukur kedua tanpa lipatan non-sliver. Sejak itu sepertiga servikal dibangun dari margin dengan sudut emergence 19° (Monaco 2026), dan set ukur ketiga lulus kriteria median ≤ 21° untuk anterior dan premolar (hasil di §5.4). Langkah 4 dan 5 (border, solid) serta §5.5 sampai §5.7 belum dimulai. Keputusan K1 sampai K5 sudah diambil maintainer pada 2026-10-23 (§9). Fase 1 diparkir (docs/PHASE1.md), dan Fase 2 sengaja tidak bergantung pada bagian Fase 1 yang tertunda.

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
| **DKT** | Diker B, Tak Ö. "Comparing the accuracy of six intraoral scanners on prepared teeth and effect of scanning sequence." J Adv Prosthodont 2020;12(5):299-306 (PMC7604233). Halaman PMC menampilkan reCAPTCHA yang tidak dilewati; teks lengkap yang sama dibaca lewat API resmi Europe PMC. Halaman akhir 306 berasal dari permintaan maintainer, belum dicek sendiri. | In vitro, preparasi single crown, analisis 3D di Geomagic Studio 12. Abstrak, presisi: Primescan 10, Trios 11, iTero 12, Omnicam 18, Virtuo Vivo 37, **Emerald 60 µm** (terburuk dari enam scanner). Bagian diskusi menulis Emerald 64 ± 27 µm, tidak sama dengan abstrak. Dipakai sebagai ambang pengaman derau §5.1. |
| **GLC** | Gallucci GO, Belser UC, Bernard JP, Magne P. "Modeling and Characterization of the CEJ for Optimization of Esthetic Implant Design." Int J Periodontics Restorative Dent 2004;24(1):19-29. Link dari maintainer (admin.quintessence-publishing.com) mengarah ke halaman login; yang dibaca adalah abstrak di halaman publik quintessence-publishing.com/usa/en/article/853057 (dicek 2026-10-23). Teks lengkap berbayar, tidak dibaca. | 137 gigi anterior rahang atas hasil ekstraksi (45 insisif sentral, 46 lateral, 46 kaninus), citra digital terstandar tampak proksimal. Lengkungan CEJ mesial vs distal: insisif sentral 3,46 vs 3,13 mm, lateral 2,97 vs 2,38 mm, kaninus 2,55 vs 1,60 mm. Dipakai sebagai rentang tinggi puncak-lembah scallop di set tuning §5.1. Catatan: ini CEJ gigi asli, bukan garis finish preparasi, dan die sintetis memakai scallop simetris (mesial = distal). |
| **JPM** | Badar SB, Zafar K, Ghafoor R, Khan FR. "Radiographic evaluation of the margins of clinically acceptable metal-ceramic crowns." JPMA 2022;72(2 Suppl 1):S-35, doi:10.47391/JPMA.AKU-08 (archive.jpma.org.pk/supplement-article-details/735, teks lengkap HTML, dicek 2026-10-23). | Studi prospektif, 115 crown metal-keramik, 230 sisi interproksimal, radiografi bitewing sebelum sementasi. Metode: "A marginal discrepancy >0.05mm on the proximal sites was labelled as a 'deficiency'"; abstrak menulis >0.5mm, jadi **ada ketidaksesuaian di paper**. 49,1% sisi proksimal crown yang lolos pemeriksaan klinis punya diskrepansi. Pendahuluan: pemeriksaan margin interproksimal dan subgingiva "poses a clinical challege". Paper juga mengutip Schaefer dkk. (0,05-0,15 mm dianggap dapat diterima). Yang diukur adalah celah crown di radiografi, bukan galat garis margin desain; dipakai sebagai alasan klinis untuk penanda segmen dan status draf §5.1, bukan sebagai ambang. |
| **ANC** | Ancker JS, Edwards A, Nosal S, Hauser D, Mauer E, Kaushal R, HITEC Investigators. "Effects of workload, work complexity, and repeated alerts on alert fatigue in a clinical decision support system." BMC Med Inform Decis Mak 2017;17(1):36, doi:10.1186/s12911-017-0430-8 (PMC5387195). Halaman PMC menampilkan reCAPTCHA; abstrak dibaca lewat API resmi Europe PMC (dicek 2026-10-24), teks lengkap tidak dibaca. | Kohort retrospektif rekam medis elektronik 112 klinisi layanan primer (alert obat dan reminder klinis, 2010-2013). Penerimaan alert turun seiring makin banyak alert, terutama alert berulang: peluang reminder diterima turun 30% untuk setiap tambahan reminder per kunjungan, dan 10% untuk setiap kenaikan 5 poin persentase proporsi reminder berulang. Hipotesis desensitisasi seiring waktu **tidak** didukung. Konteksnya obat/reminder, bukan CAD; dipakai sebagai alasan menjadikan segmen merah petunjuk ringan (§5.1), bukan sebagai angka. |
| **EXI** | exocad wiki, "Setting insertion axis" (wiki.exocad.com/wiki/index.php/Setting_Insertion_axis). Server aslinya menolak koneksi saat dicek (2026-10-24); yang dibaca adalah arsip Wayback Machine snapshot 2024-02-23, oldid 12143, dokumentasi rilis 2020 ke atas. | Sumbu dideteksi otomatis; pengguna diminta mengecek "When the software has doubts about the insertion axis it auto-detected", biasanya "when the margin line lies within an undercut area". Software menyajikan sumbu "by adjusting the viewpoint so that you look onto the preparation(s) from the insertion direction" dan menandai undercut dengan skala warna. Mengubah sumbu: putar pandangan lalu "Set current view as insertion axis", atau seret bola di ujung panah; visualisasi undercut diperbarui. |
| **EXQ** | "exocad Quick Guide: Crown Bottoms", transkrip video di voicetube.com/videos/46150. Halaman aslinya hanya memuat "Loading..." saat dicek; yang dibaca adalah transkrip di arsip Wayback snapshot 2024-02-25. Video aslinya dari exocad; tanggal rilis video dan versi exocad yang ditunjukkan tidak tercantum di transkrip. | "A red arrow indicates that the insertion axis for this tooth might not be optimally defined"; "While rotating, undercuts are marked in red"; "Undercuts are always blocked out parallel to the insertion axis" kecuali sudut dipilih. "Don't block out zone near prepline" = "untouchable zone" di sekitar margin yang tidak pernah di-block-out; "The default value in our generic version is 0.1 mm"; 3-axis biasanya 0; 5-axis disarankan sama dengan jarak cement gap. Urutan: "In most material configurations for 5-axis milling, the cement gap is applied after doing the block-out", dan "for steep preparations, generating the cement gap itself may cause new undercuts" ("a 5-axis machine can produce these"). "Additional Spacing" ditambahkan "to the entire crown bottom, independent of the cement gap", cement gap "applied on top of the additional spacing"; "Radial" = offset "perpendicular to the occlusal direction". Bentuk atau lebar transisi zona tidak disebut. |
| **PAT2** | Google Patents, DE102006044215A1 / DE102006044215B4 "Dental prosthesis part's (e.g. crown) insertion axial direction optimizing method", Sirona Dental Systems GmbH, penemu Frank Seibert (dicek 2026-10-24). | Prioritas dan pengajuan 2006-09-15, publikasi A1 2008-03-27, diberikan B4 2014-02-20. Status "Expired - Fee Related"; event R119 2024-04-03 "Application deemed withdrawn, or ip right lapsed, due to non-payment of renewal fee". Halaman yang sama masih menulis "Anticipated expiration" 2026-09-16, jadi status perlu dicek di register DPMA. Isi: daerah terbayang dari arah pandang ditandai, sumbu disesuaikan dengan arah pandang yang diubah pengguna, dan kandidat arah di bola dinilai dengan kriteria kualitas, dioptimalkan pengguna atau otomatis. Google: "The legal status is an assumption and is not a legal conclusion." |
| **PAT3** | Google Patents, US20100233659A1 dan EP2187833B1 "Method for designing a tooth replacement part", Institut Straumann AG, penemu Stephan Holzner dan Gerhard Weber (dicek 2026-10-24). Klaim EP dibaca dari dokumen B1 di server publikasi EPO (data.epo.org); teks klaim bahasa Inggris terpotong, jadi yang dibaca teks Jerman. EP Register menolak akses (HTTP 403). | **US20100233659A1:** prioritas 2007-07-25, pengajuan 2008-07-24, publikasi 2010-09-16, status "Abandoned"; event "ABANDONED -- FAILURE TO RESPOND TO AN OFFICE ACTION" 2014-04-03 (dari ringkasan halaman, belum dicek di USPTO). **EP2187833B1:** diberikan 2019-05-22, status "Active", "2028-07-24 Anticipated expiration". Menurut ringkasan halaman (belum dicek di register), tidak ada oposisi, banyak negara gugur karena tidak membayar biaya atau tidak menyerahkan terjemahan, dan biaya tahunan 2025 dibayar untuk DE, ES, FR, GB, CH. Daftar keluarga di ringkasan halaman: US dan CA ditinggalkan, DE dan WO berhenti, ES aktif, JP tercantum "pending"; tidak ada anggota Indonesia. Daftar keluarga ini belum dicek di Espacenet. **Klaim 1 (EP, teks Jerman):** metode komputer: menyediakan spacing antara bagian prostesis dan sisa gigi, lalu memeriksa apakah ada undercut terhadap arah insersi. Spacing punya dua atau lebih zona tebal berbeda dengan zona transisi di antaranya, dan bentuk transisinya dibatasi supaya tidak melewati bidang yang sejajar arah insersi, "so dass ein Hinterschnitt vermieden wird". Klaim 4: undercut dihapus, atau spacing diubah otomatis sampai tidak ada undercut; klaim 9: pemeriksaan otomatis setelah setiap perubahan. Google: "The legal status is an assumption and is not a legal conclusion." |
| **PAT4** | Keluarga Straumann Holding AG "Computer-implemented method for digitally designing a dental restoration" (penemu Manzer, Lawitschka, Meier, Welge; prioritas 2010-08-31), dicek 2026-10-25. Klaim EP dibaca dari dokumen B1 di server publikasi EPO, klaim US dari Google Patents. | **EP2422741B1** (diberikan 2013-01-23): "Active", "2030-08-31 Anticipated expiration". Klaim 1: "automatically deforming the tooth template (7) by means of Laplacian surface deformation" dengan garis "directed along the normal direction" lewat titik di permukaan; perpotongannya dengan template menjadi handle, dan dengan gigi menjadi target. **EP2422742B1** (diberikan 2013-05-22): "Active", "2031-03-18 Anticipated expiration". Klaim 1: Laplacian surface deformation; di daerah margin garis "orthogonally intersects the axis" (sumbu gigi atau sumbu template), di daerah lain garis normal, dengan handle/target dari perpotongan. **US9396291B2**: "Active, expires 2033-01-01"; klaim 1 sama dengan EP2422741 ditambah handle di dalam poligon mesh. **US9286417B2**: "Active, expires 2032-09-23"; klaim 1 sama dengan EP2422742. Klaim turunan: bobot handle iteratif, potong template di margin, gabungkan dengan permukaan gigi di dalam margin, tambah cement gap. Menurut ringkasan halaman (belum dicek di register): kedua EP gugur di FR dan IE, dan biaya tahunan 2025/2026 dibayar untuk DE, GB, CH. **Dibaca 2026-10-25 (K6):** EP2422740B1 ("Active", "2030-08-31 Anticipated expiration"): klaim 1 = Laplacian surface deformation dengan "angle weighting function" untuk handle; EP2468212B1 ("Active", "2031-03-18 Anticipated expiration"): klaim 1 = Laplacian surface deformation dengan garis yang "orthogonally intersects the axis", handle/target dari perpotongan, untuk "full crown" (klaim turunan 8: penskalaan bukal dan mesiodistal menurut lebar permukaan preparasi, bergantung pada klaim 1); US9330205B2 ("Active, expires 2032-12-30"): klaim 1 dan 12 = Laplacian surface deformation dengan angle weighting function. Tidak ada klaim independen yang mencakup konstruksi berlabuh margin tanpa deformasi Laplacian. |
| **PAT5** | Keluarga James R Glidewell Dental Ceramics "shape analysis, storage and retrieval of 3d models" (penemu Azernikov, Nikolskiy; prioritas 2013-03-15), dicek 2026-10-25 di Google Patents. | **WO2014144373A1**: "Ceased"; event 2016-04-06 "pct application non-entry in european phase" (tidak ada paten EP). **US10157330B2**: "Active, expires 2037-03-10". Klaim 1: margin line preparasi dikodekan sebagai "chain code", "measuring similarity" terhadap chain code kasus di "case repository", model 3D yang mirip diambil sebagai proposal, dan restorasi dibentuk dengan CAM. **US10248885B2**: "Active, expires 2037-01-01"; klaim 1: kurva karakteristik dikodekan sebagai string dan dicari kemiripannya di database kasus. **DE112014001417B4**: "Active", "2034-03-15 Anticipated expiration"; klaim 1 sama dengan klaim chain code WO. |
| **NAG** | Nagata K, Inoue E, Nakashizu T, Seimiya K, Atsumi M, Kimoto K, Kuroda S, Hoshi N. "Verification of the accuracy and design time of crowns designed with artificial intelligence." J Adv Prosthodont 2025;17(1):1-10, doi:10.4047/jap.2025.17.1.1, PMID 40061025 (PMC11886404, CC BY-NC). Halaman PMC memakai reCAPTCHA; teks lengkap dibaca lewat API Europe PMC (2026-10-25). | Studi in vitro (5 teknisi, #15 dan #26, 3Shape Dental System dan Dentbird). Metode: "The design parameters were set as follows: margin width, 80 µm; margin angle, 50°; occlusal distance, 0 µm; approximal distance, −20 µm; cement gap, 40 µm; and adaptive extra gap, 50 µm based on the design of Cho et al." Ini setelan desain studi, bukan rekomendasi klinis. Dipakai untuk jarak oklusal dan approximal §5.4 (status literatur, perlu kalibrasi). |
| **YOT** | Yotnuengnit B, Yotnuengnit P, Laohapand P, Athipanyakom S. "Emergence angles in natural anterior teeth: Influence on periodontal status." Quintessence Int 2008;39(3):e126-e133. Abstrak dibaca di repositori Mahidol University (https://repository.li.mahidol.ac.th/handle/123456789/19168, 2026-10-25). | 50 gigi anterior bercrown dan gigi kontralateral alami; potongan model dipindai. Rata-rata sudut emergence supragingiva gigi alami 11,13 ± 7,92° (fasial) dan 15,58 ± 9,16° (lingual); subgingiva 9,93 ± 5,68° dan 14,35 ± 8,44°. Pada gigi bercrown, sudut lingual subgingiva berkorelasi dengan kedalaman poket, dan sudut lingual supra- maupun subgingiva berkorelasi dengan attachment loss. Acuan sudut tidak disebut di abstrak. Pembanding metrik emergence §5.4. |
| **MON** | Monaco C, Silvestri D, Felice TD, Arena A, Bonvicini M, Di Fiore A, Zicari F. "A New Digital Technique to Analyze the Inclination of Tooth Emergence Profile and Distance from the Bone Crest to the Cementoenamel Junction." Int J Prosthodont 2026;39(1):37-45 (terbit 2026-01-22; preprint 2025), doi:10.11607/ijp.9272, PMID 40388572. Abstrak dibaca lewat API Europe PMC dan halaman Quintessence (2026-10-25). Tautan research.unipd.it yang diberikan maintainer terhalang verifikasi bot. Teks lengkap berbayar dan tidak dibaca. | CBCT 24 pasien; 57 gigi untuk inklinasi profil emergence dan 206 gigi untuk jarak puncak tulang ke CEJ. "an increase in emergence profile angle from an average value of 13 to 19 degrees when simulating prosthetic chamfer preparation". **Acuan sudut tidak disebut di abstrak**, dan jenis gigi yang diukur juga tidak disebut. Sebuah ringkasan sekunder (bukan sumber primer, tidak diverifikasi) menyebut 57 gigi rahang atas dan sudut sekitar 16° (premolar) sampai 21° (insisif sentral) dengan acuan 1 mm di atas CEJ; kemungkinan dari situ batas 21°. Sumber `emergence_angle_deg` §5.4. |
| **DU** | Du JK, Li HY, Wu JH, Lee HE, Wang CH. "Emergence angles of the cementoenamel junction in natural maxillary anterior teeth." J Esthet Restor Dent 2011;23(6):362-369, doi:10.1111/j.1708-8240.2011.00471.x, PMID 22142293. Abstrak dibaca di PubMed (2026-10-25); tautan wicri-demo.istex.fr yang diberikan maintainer sedang dalam pemeliharaan saat dicek. | 148 gigi anterior rahang atas alami (74 insisif sentral, 59 lateral, 15 kaninus), dipindai 3D; sudut emergence di CEJ pada zenith labial, palatal, mesial, dan distal "within a narrow range from 11.30° to 15.26°", tanpa beda bermakna. Kesimpulan penulis: 15° "from the root surface". Pembanding metrik emergence §5.4. |
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

**Status: selesai** (2026-10-23). Implementasi di `core/margin.py` dan `core/geometry.py`, operator di `ops/margin.py`, benchmark di `scripts/margin_benchmark.py`.

**Algoritma yang diimplementasikan** (curvature klasik, RESEARCH.md §4; tidak meniru metode ML, K5). Beberapa langkah berbeda dari rancangan awal; perbedaannya dicatat karena masing-masing lahir dari kegagalan terukur di spike S1.
1. **Skor crease per vertex:** nilai eigen terbesar kovarians normal vertex dalam radius r (bobot Gauss), hanya di daerah cembung; crease cekung (sudut dalam shoulder, busur chamfer) diredam.
   - *Beda dari rancangan:* bukan fit kuadrik curvature prinsipal per cincin, karena variasi normal dalam radius lebih tahan derau dan langsung mengukur "ketajaman crease".
   - Radius r = max(0,35 mm, 12 × σ), dengan σ derau yang diestimasi dari mesh (MAD perpindahan umbrella sepanjang normal; akurat 13/33/89 µm untuk derau 10/30/90 µm).
2. **Graf biaya:** bobot edge = panjang × (0,02 + (1 − s)²), dengan s = skor **relatif terhadap titik klik** (dipotong di 1).
   - *Alasan:* tepi dasar die adalah crease yang lebih tajam daripada margin chamfer. Dengan skor absolut, jalur memutar 4 mm ke tepi dasar (terukur di S1).
3. **Loop tertutup tanpa sumbu:** Dijkstra dari klik; titik jauh f = vertex "di punggungan" (biaya jalur ≤ 0,35 × jarak Euclid) **dan di crease (skor relatif ≥ 0,5)** yang terjauh dari klik. Jalur 1 = klik → f; jalur 2 = klik → f setelah jalur 1 dan dua cincin tetangganya diblokir, jadi lewat sisi lain die. Loop = jalur 1 + jalur 2.
   - *Beda dari rancangan:* versi pertama memakai seam berbasis sumbu perkiraan. Sumbu yang miring (margin scallop, crease lain) menghasilkan "loop" 3 sampai 34 vertex di sekitar titik tembus sumbu, jadi diganti metode dua jalur ini.
   - *Syarat crease untuk f* (ditambahkan setelah set uji pertama): kriteria punggungan sendiri mengizinkan simpangan yang sebanding dengan jarak. Pada insisif sentral (radius 3,6 / 3,2 mm, PL 3,2 mm), f jatuh 1,7 mm di dinding aksial di atas puncak proksimal (skor relatif 0,03-0,07, sementara di margin sekitar 1). Kedua jalur ikut naik ke sana, dan puncak proksimal terpotong sekitar 0,7 mm. Nilai 0,5: persentil 10 skor relatif vertex di margin benar dekat puncak adalah 0,52-0,65 pada kasus itu.
4. **Penyempurnaan ke crease:** setiap titik sampel loop (jarak 0,15 mm) dipindah ke garis potong dua permukaan di kedua sisi crease.
   - Tetangga dalam radius max(0,6 mm, 12σ) dikelompokkan dengan 2-means pada normal halus.
   - Lintasan 1 memakai bidang; lintasan 2 (3 iterasi) memakai **bidang singgung kuadrik per sisi** di dalam pita sempit sekitar garis, supaya busur chamfer tidak membiaskan hasil (bidang sekan memberi bias sekitar 40 µm pada chamfer).
5. **Kurva:** titik hasil dihaluskan dengan **regresi kuadratik lokal** sepanjang panjang busur (σ 0,4 mm), lalu diambil titik kontrol tiap 1,0 mm; kurva = spline kubik periodik melalui titik kontrol.
   - *Alasan:* rata-rata Gauss biasa menyusutkan kurva sekitar σ²κ/2 (18 µm terukur).
6. **Titik kontrol hasil deteksi tidak diproyeksikan ke mesh.** Mesh memotong sudut crease di antara vertex, jadi proyeksi menarik margin ke dalam (17 → 46 µm terukur). Titik yang **digeser pengguna** diproyeksikan ke permukaan; titik lain dipertahankan (`MarginCurve.apply_edit`).

**Edit di Blender.** "Detect Margin" (modal: klik satu titik di die) membuat kurva `<die> Margin` (titik kontrol, bisa diedit) dan `<die> Margin Preview` (kurva halus). Pengguna menggeser (G) atau menghapus (X) titik kontrol di Edit Mode, lalu "Update Margin". Jalur klik modal (ray cast dari viewport) tidak bisa diuji headless; logika deteksi dan edit diuji lewat properti `seed_point`.

**Parameter** (semua parameter algoritma, bukan klinis; nilai dari sapuan S1 terhadap data sintetis):

| Parameter | Nilai | Catatan |
|---|---|---|
| Radius skor crease | max(0,35 mm, 12σ) | Faktor 12 satu-satunya yang lolos semua kasus derau 30 µm di sapuan (8, 12, 16, 20). |
| Radius penyempurnaan | max(0,6 mm, 12σ) | Tidak sensitif di rentang 8 sampai 16. |
| Rasio punggungan | 0,35 | 0,25 gagal pada chamfer berderau 30 µm; 0,45 mulai menarik tepi dasar. |
| Bobot biaya | 0,02 + (1 − s)² | |
| Pita blokir jalur 2 | 2 cincin | |
| Jarak sampel penyempurnaan / σ penghalusan / jarak titik kontrol | 0,15 / 0,4 / 1,0 mm | |
| Titik klik | input pengguna | Tidak harus tepat di margin; seed digeser ke vertex berskor tertinggi dalam 2r. |

**Pengaman: tidak boleh gagal diam-diam.** Deteksi hanya punya dua hasil: kurva yang lolos semua pemeriksaan, atau error eksplisit. Operator Blender menampilkan error itu dan tidak membuat objek kurva apa pun.
1. **Pengaman derau** (`MarginNoiseError`): bila σ hasil estimasi > 60 µm, deteksi berhenti sebelum mencari jalur, dengan pesan "scan terlalu berderau ... gambar margin manual (Draw Margin)" (UI: "Scan too noisy ..., no curve was created. Use Draw Margin to place the margin by hand."). Pesan penolakan kewajaran juga mengarah ke Draw Margin.
   - Sumber ambang: DKT (§2.1), presisi scanner terburuk dari enam yang diuji (Emerald, 60 µm). Artinya: derau di atas presisi scanner intraoral terburuk di studi itu dianggap bukan scan yang wajar.
   - Batasan sumber: (a) 60 µm adalah angka terburuk yang terukur, bukan batas yang direkomendasikan paper; (b) abstrak menulis 60 µm, diskusi 64 ± 27 µm; (c) presisi di paper adalah deviasi antar-scan berulang setelah superimposisi, **bukan** σ derau per vertex yang diestimasi di sini. Kedua besaran berhubungan tetapi tidak sama, jadi ambang ini perlu dicek ulang dengan scan nyata.
   - Estimator σ terukur 13/33/89 µm untuk derau 10/30/90 µm, jadi kasus 90 µm jauh di atas ambang dan kasus 30 µm jauh di bawahnya.
2. **Pemeriksaan kewajaran kurva** (`MarginPlausibilityError`; nama pemeriksaan yang gagal ikut dilaporkan ke UI):

| Pemeriksaan | Ambang | Arti |
|---|---|---|
| Fraksi titik yang menempel ke crease | ≥ 0,75 | Penyempurnaan menemukan dua permukaan yang berpotongan dengan sudut ≥ 30°. |
| Jarak kurva ke titik klik | ≤ 1,0 mm | Kurva tidak melompat jauh dari tempat pengguna mengeklik. |
| Lubang terbesar antar titik kontrol | ≤ 2,5 × jarak titik kontrol | Loop tertutup tanpa loncatan. |
| Panjang kurva **yang diproyeksikan ke bidangnya** / keliling die di ketinggian kurva | 0,90 sampai 1,12 | Keliling = keliling convex hull 2D vertex die dalam pita ±1 mm di sekitar bidang kurva. Versi pertama memakai panjang 3D dan menolak semua margin scallop puncak-lembah 4 mm (rasio 1,16 sampai 1,18), padahal margin yang naik-turun memang lebih panjang daripada kelilingnya. |
| Simpangan dari bidang kurva / diameter | ≤ 0,35 | Kurva tidak keluar jauh dari bidang margin. |
| Titik crease cukup rapat untuk dihaluskan | ≥ 4 tetangga berbobot berarti | Sebelumnya bisa berakhir sebagai error aljabar linear yang tidak jelas. |

   Semua ambang di atas adalah ambang algoritma tanpa sumber klinis, dipilih dari sapuan pada **set tuning saja**. Setelah metrik panjang diganti, sapuan ulang pada set tuning dan tuning2 (semua ambang dibuka, 3 seed, derau 0 sampai 90 µm) memberi rasio 0,980 sampai 0,996 untuk semua 139 kurva baik. Rentang yang lebih sempit (0,93 sampai 1,05, 0,95 sampai 1,03, 0,96 sampai 1,02) tidak menangkap satu pun kurva buruk tambahan, jadi rentang 0,90 sampai 1,12 dipertahankan. Set uji di bawah tidak dipakai untuk memilih apa pun.
3. **Penanda segmen meragukan** (`review_curve`, merah di viewport, "N segments to review" di panel dan laporan, petunjuk ringan): lihat bagian "Draf, penanda merah, dan konfirmasi" di bawah.
4. **Bukti:** tes `test_every_90um_case_stops_with_the_noise_warning` (8 kasus derau 90 µm: shoulder/chamfer × scallop 0/1 mm × 2 seed) mewajibkan `MarginNoiseError`. Benchmark menghitung "Kurva buruk tanpa pesan" = kurva dikembalikan, median > 50 µm atau cakupan p95 > 150 µm, **dan** tanpa segmen merah.
5. **Lapis kedua (pengaman derau dimatikan, `check_noise=False`), 48 kasus derau 90 µm:** pemeriksaan kewajaran saja meloloskan 3 kurva buruk (shoulder; median 184, 208, 247 µm), karena kurva itu tertutup, panjangnya wajar, dan dekat titik klik. Dengan segmen merah ikut dihitung: **0 dari 48** lolos tanpa pesan dan tanpa merah. Tes `test_without_noise_guard_bad_90um_curves_are_rejected_or_flagged` (8 kasus) mewajibkannya. Pengaman derau tetap pelindung utama.

**Scallop: definisi.** `DieSpec.scallop_mm` adalah amplitudo A pada z = z0 + A·cos 2θ, jadi tinggi **puncak-lembah (PL) = 2A**. Lengkungan CEJ di GLC (§2.1) diukur dari titik terdalam ke puncak proksimal, jadi sebanding dengan PL. Tabel di bawah menulis PL. Varian "scallop 2 mm" di laporan lama adalah A = 2 mm, atau PL 4 mm, di atas lengkungan CEJ rata-rata terbesar di GLC (3,46 mm).

**Draf, penanda merah, dan konfirmasi.** Alasan klinis (JPM, §2.1): pada crown yang lolos pemeriksaan klinis, hampir separuh sisi proksimal masih punya diskrepansi di radiografi, dan sisi interproksimal paling sulit diperiksa dokter. Jadi kurva otomatis tidak boleh langsung dipakai.
- **Penanda segmen** (`core.margin.review_curve`): kurva diambil 256 titik sampel; tiap titik disempurnakan ulang ke crease lokal (cara yang sama dengan langkah 4). Titik ditandai bila **residual** (jarak titik kurva ke crease lokal) > 0,08 mm, tidak ada crease di sekitarnya, atau **sudut crease** < 30°. Run tertanda sepanjang ≥ 2 sampel menjadi satu segmen. Fungsi ini bekerja untuk kurva apa pun (Detect, Draw, setelah Update), karena hanya butuh mesh dan kurva.
- **Ambang dipilih dari set tuning dan tuning2 saja** (140 kurva, 3 seed, derau 0/10/30 µm, `review_sweep`): residual kurva baik p50 12 µm, p99 92 µm, maks 278 µm; sudut crease kurva baik p0,1 37°. Hanya ada satu kurva buruk di kedua set (CEJ PL 3,5, chamfer 30 µm, median 53 µm), dengan residual maksimum 104 µm.

| Residual | Run | Kurva baik bertanda | Kurva buruk bertanda |
|---|---|---|---|
| 0,06 mm | 2 | 51% | 1/1 |
| **0,08 mm** | **2** | **32%** (derau 0: 6%, 10: 19%, 30: 74%) | **1/1** |
| 0,10 mm | 2 | 17% (derau 0: 2%, 10: 10%, 30: 42%) | 1/1, hanya selisih 4 µm |
| 0,12 mm | 2 | 11% | 0/1 |

  Dipilih 0,08 mm (sensitivitas di atas kenyamanan, sesuai alasan klinis). Harganya: pada derau 30 µm, kebanyakan kurva baik juga punya segmen merah. Sudut 30° tidak mengubah apa pun di data tuning (sama dengan sudut minimum penyempurnaan).
- **Keterbatasan yang terukur:** penanda ini lemah dalam menunjuk **lokasi** kesalahan. Di tuning dan tuning2, hanya 83 dari 367 titik sampel yang galatnya > 0,1 mm berada di dalam atau di sebelah segmen merah. Pada satu-satunya kurva buruk di set tuning (CEJ PL 3,5), segmen merahnya berjarak sekitar 7,5 mm dari bagian yang melenceng; kurva itu tertangkap karena kebetulan. Pada kurva buruk di set uji (premolar taper 16°), segmen merahnya berada di bagian yang melenceng (median 0,17 mm). Jadi segmen merah adalah tanda "periksa kurva ini", bukan peta galat yang lengkap.
- **Segmen merah = petunjuk ringan** (keputusan maintainer 2026-10-24): tetap tampil di viewport dan disebut di panel dan laporan ("N segments to review"), tetapi **tidak** menghalangi Confirm Margin dan tidak memunculkan dialog atau peringatan. Alasannya, alarm palsunya tinggi (chamfer 30 µm: 38 dari 40 kurva baik bertanda merah), dan alert yang sering tidak informatif cenderung diabaikan (ANC, §2.1). **Penanda ini perlu dikalibrasi dengan scan asli sebelum dijadikan peringatan keras.**
- **Status draf:** setiap Detect, Draw, dan Update menulis `dentalcad_margin_status = "draft"`. **Confirm Margin** tetap wajib. Ia mengubah status ke "confirmed" dan menolak kurva yang titiknya diedit tanpa Update. Jumlah segmen merah hanya dicatat di laporan.
- **Gerbang:** `ops.margin.require_confirmed_margin(die)` hanya lolos untuk margin berstatus confirmed yang titik kontrolnya sama dengan saat dikonfirmasi. **Operator §5.2 sampai §5.7 (sumbu insersi, spacer, crown, ekspor STL crown) wajib memanggil gerbang ini dan menolak jalan untuk margin draf.** Operator itu belum ada, jadi yang diuji sekarang adalah gerbangnya sendiri. Ekspor kupon Fase 1 tidak memakai margin dan tidak terpengaruh.

**Riwayat set.**
- **tuning**: die standar (5,0 / 4,5 mm, tinggi 5 mm, taper 6°) tanpa scallop, PL 2,0 mm, dan varian lengkungan CEJ dari GLC (PL 2,5 dan 3,5 mm).
- **tuning2**: set "unseen" pertama; dipakai untuk memperbaiki metrik panjang.
- **tuning3**: set uji pertama, dikunci di commit `a351e40` dan dijalankan sekali. Hasilnya saat itu: 3 kurva buruk tanpa pesan, semuanya insisif sentral (median 20-27 µm, tetapi cakupan p95 266-304 µm, puncak proksimal terpotong 660-690 µm). Kasus itu dipakai untuk memperbaiki pemilihan titik jauh, jadi set ini sekarang set tuning.
- **uji**: set uji kedua, didefinisikan dan dikunci bersama semua parameter, ambang kewajaran, dan ambang penanda di commit `3e17128`, lalu dijalankan sekali.

| Set uji kedua | Radius x/y | Tinggi | Taper | Lebar finish | PL scallop | Lainnya |
|---|---|---|---|---|---|---|
| lateral | 3,2 / 2,9 mm | 5,0 mm | 6° | 0,7 mm | 2,9 mm | |
| kaninus lebar | 3,6 / 4,4 mm | 6,5 mm | 9° | 1,0 mm | 2,5 mm | sumbu panjang di y |
| molar lebar pendek | 6,4 / 5,8 mm | 4,0 mm | 8° | 1,2 mm | 1,4 mm | |
| premolar taper 16 | 4,0 / 3,6 mm | 4,5 mm | 16° | 1,0 mm | 1,0 mm | |
| undercut di puncak | 4,6 / 4,1 mm | 5,5 mm | 4° | 1,0 mm | 2,0 mm | sektor undercut 12° tepat di puncak proksimal (0°) |

Semua tabel: `python scripts/margin_benchmark.py --set <set> --seeds 3`, 2026-10-23, parameter dari `3e17128`, pengaman aktif. Die sintetis dengan rotasi acak, mesh ber-jitter, titik klik acak di sekitar margin (simpangan 0,15 mm). Nilai per baris = **nilai terburuk dari 3 seed**, hanya dari seed yang menghasilkan kurva. Kriteria: median ≤ 50 µm dan cakupan p95 ≤ 150 µm. "kurva+merah" = kurva dengan ≥ 1 segmen merah. Tidak ada baris yang disembunyikan.

**Set tuning:**

| Die | Finish | Derau | Hasil per seed | Median | p95 | Cakupan p95 | Memenuhi kriteria | Buruk, bertanda merah | Baik, bertanda merah | Kurva buruk tanpa pesan |
|---|---|---|---|---|---|---|---|---|---|---|
| standar | shoulder | 0 µm | kurva 3 | 14,7 µm | 24,6 µm | 24,6 µm | ya | 0 | 0 | 0 |
| standar | shoulder | 10 µm | kurva 3 | 18,7 µm | 29,7 µm | 29,6 µm | ya | 0 | 0 | 0 |
| standar | shoulder | 30 µm | kurva 1, kurva+merah 2 | 34,7 µm | 81,6 µm | 80,9 µm | ya | 0 | 2 | 0 |
| standar | shoulder | 90 µm | derau 3 | - | - | - | **tidak** | 0 | 0 | 0 |
| standar | chamfer | 0 µm | kurva 3 | 26,4 µm | 64,0 µm | 64,1 µm | ya | 0 | 0 | 0 |
| standar | chamfer | 10 µm | kurva 3 | 28,9 µm | 71,4 µm | 70,7 µm | ya | 0 | 0 | 0 |
| standar | chamfer | 30 µm | kurva+merah 3 | 41,0 µm | 123,9 µm | 121,8 µm | ya | 0 | 3 | 0 |
| standar | chamfer | 90 µm | derau 3 | - | - | - | **tidak** | 0 | 0 | 0 |
| scallop PL 2,0 mm | shoulder | 0 µm | kurva 3 | 15,9 µm | 30,2 µm | 30,9 µm | ya | 0 | 0 | 0 |
| scallop PL 2,0 mm | shoulder | 10 µm | kurva 3 | 18,2 µm | 35,8 µm | 35,9 µm | ya | 0 | 0 | 0 |
| scallop PL 2,0 mm | shoulder | 30 µm | kurva 1, kurva+merah 2 | 30,0 µm | 75,0 µm | 73,1 µm | ya | 0 | 2 | 0 |
| scallop PL 2,0 mm | shoulder | 90 µm | derau 3 | - | - | - | **tidak** | 0 | 0 | 0 |
| scallop PL 2,0 mm | chamfer | 0 µm | kurva 2, kurva+merah 1 | 31,8 µm | 54,9 µm | 55,1 µm | ya | 0 | 1 | 0 |
| scallop PL 2,0 mm | chamfer | 10 µm | kurva 2, kurva+merah 1 | 33,1 µm | 69,7 µm | 68,7 µm | ya | 0 | 1 | 0 |
| scallop PL 2,0 mm | chamfer | 30 µm | kurva+merah 3 | 49,5 µm | 100,2 µm | 100,0 µm | ya | 0 | 3 | 0 |
| scallop PL 2,0 mm | chamfer | 90 µm | derau 3 | - | - | - | **tidak** | 0 | 0 | 0 |
| CEJ PL 2,5 mm | shoulder | 0 µm | kurva 3 | 15,2 µm | 31,6 µm | 32,0 µm | ya | 0 | 0 | 0 |
| CEJ PL 2,5 mm | shoulder | 10 µm | kurva 3 | 17,4 µm | 33,3 µm | 33,7 µm | ya | 0 | 0 | 0 |
| CEJ PL 2,5 mm | shoulder | 30 µm | kurva 1, kurva+merah 2 | 27,5 µm | 63,4 µm | 63,0 µm | ya | 0 | 2 | 0 |
| CEJ PL 2,5 mm | shoulder | 90 µm | derau 3 | - | - | - | **tidak** | 0 | 0 | 0 |
| CEJ PL 2,5 mm | chamfer | 0 µm | kurva 2, kurva+merah 1 | 32,4 µm | 61,3 µm | 61,4 µm | ya | 0 | 1 | 0 |
| CEJ PL 2,5 mm | chamfer | 10 µm | kurva 1, kurva+merah 2 | 37,5 µm | 63,9 µm | 64,3 µm | ya | 0 | 2 | 0 |
| CEJ PL 2,5 mm | chamfer | 30 µm | kurva+merah 3 | 45,3 µm | 107,5 µm | 109,6 µm | ya | 0 | 3 | 0 |
| CEJ PL 2,5 mm | chamfer | 90 µm | derau 3 | - | - | - | **tidak** | 0 | 0 | 0 |
| CEJ PL 3,5 mm | shoulder | 0 µm | kurva 3 | 15,5 µm | 33,8 µm | 34,6 µm | ya | 0 | 0 | 0 |
| CEJ PL 3,5 mm | shoulder | 10 µm | kurva 2, kurva+merah 1 | 17,8 µm | 29,9 µm | 31,1 µm | ya | 0 | 1 | 0 |
| CEJ PL 3,5 mm | shoulder | 30 µm | kurva 1, kurva+merah 2 | 27,4 µm | 71,3 µm | 71,3 µm | ya | 0 | 2 | 0 |
| CEJ PL 3,5 mm | shoulder | 90 µm | derau 3 | - | - | - | **tidak** | 0 | 0 | 0 |
| CEJ PL 3,5 mm | chamfer | 0 µm | kurva 3 | 36,7 µm | 69,7 µm | 70,4 µm | ya | 0 | 0 | 0 |
| CEJ PL 3,5 mm | chamfer | 10 µm | kurva 2, kurva+merah 1 | 40,4 µm | 69,2 µm | 69,6 µm | ya | 0 | 1 | 0 |
| CEJ PL 3,5 mm | chamfer | 30 µm | kurva+merah 3 | 52,7 µm | 106,1 µm | 107,6 µm | **tidak** | 1 | 2 | 0 |
| CEJ PL 3,5 mm | chamfer | 90 µm | derau 3 | - | - | - | **tidak** | 0 | 0 | 0 |

**Set tuning2:**

| Die | Finish | Derau | Hasil per seed | Median | p95 | Cakupan p95 | Memenuhi kriteria | Buruk, bertanda merah | Baik, bertanda merah | Kurva buruk tanpa pesan |
|---|---|---|---|---|---|---|---|---|---|---|
| premolar kecil (PL 1,0) | shoulder | 0 µm | kurva 3 | 14,3 µm | 29,1 µm | 29,2 µm | ya | 0 | 0 | 0 |
| premolar kecil (PL 1,0) | shoulder | 10 µm | kurva 3 | 17,7 µm | 31,7 µm | 31,8 µm | ya | 0 | 0 | 0 |
| premolar kecil (PL 1,0) | shoulder | 30 µm | kurva 1, kurva+merah 2 | 32,5 µm | 73,6 µm | 73,7 µm | ya | 0 | 2 | 0 |
| premolar kecil (PL 1,0) | shoulder | 90 µm | derau 3 | - | - | - | **tidak** | 0 | 0 | 0 |
| premolar kecil (PL 1,0) | chamfer | 0 µm | kurva 3 | 21,9 µm | 46,6 µm | 46,6 µm | ya | 0 | 0 | 0 |
| premolar kecil (PL 1,0) | chamfer | 10 µm | kurva 3 | 26,1 µm | 47,8 µm | 48,0 µm | ya | 0 | 0 | 0 |
| premolar kecil (PL 1,0) | chamfer | 30 µm | error 1, kurva+merah 2 | 44,5 µm | 118,9 µm | 117,9 µm | **tidak** | 0 | 2 | 0 |
| premolar kecil (PL 1,0) | chamfer | 90 µm | derau 3 | - | - | - | **tidak** | 0 | 0 | 0 |
| molar besar (PL 3,0) | shoulder | 0 µm | kurva 3 | 15,8 µm | 29,1 µm | 29,6 µm | ya | 0 | 0 | 0 |
| molar besar (PL 3,0) | shoulder | 10 µm | kurva 2, kurva+merah 1 | 16,2 µm | 29,9 µm | 30,0 µm | ya | 0 | 1 | 0 |
| molar besar (PL 3,0) | shoulder | 30 µm | kurva 1, kurva+merah 2 | 25,4 µm | 53,2 µm | 53,2 µm | ya | 0 | 2 | 0 |
| molar besar (PL 3,0) | shoulder | 90 µm | derau 3 | - | - | - | **tidak** | 0 | 0 | 0 |
| molar besar (PL 3,0) | chamfer | 0 µm | kurva 2, kurva+merah 1 | 40,8 µm | 69,5 µm | 69,6 µm | ya | 0 | 1 | 0 |
| molar besar (PL 3,0) | chamfer | 10 µm | kurva 3 | 43,7 µm | 77,2 µm | 77,2 µm | ya | 0 | 0 | 0 |
| molar besar (PL 3,0) | chamfer | 30 µm | kurva 2, kurva+merah 1 | 48,3 µm | 106,1 µm | 107,3 µm | ya | 0 | 1 | 0 |
| molar besar (PL 3,0) | chamfer | 90 µm | derau 3 | - | - | - | **tidak** | 0 | 0 | 0 |
| taper lebar (PL 0,6) | shoulder | 0 µm | kurva 3 | 14,0 µm | 25,3 µm | 25,6 µm | ya | 0 | 0 | 0 |
| taper lebar (PL 0,6) | shoulder | 10 µm | kurva 3 | 18,6 µm | 32,0 µm | 32,0 µm | ya | 0 | 0 | 0 |
| taper lebar (PL 0,6) | shoulder | 30 µm | kurva 1, kurva+merah 2 | 33,7 µm | 89,7 µm | 89,0 µm | ya | 0 | 2 | 0 |
| taper lebar (PL 0,6) | shoulder | 90 µm | derau 3 | - | - | - | **tidak** | 0 | 0 | 0 |
| taper lebar (PL 0,6) | chamfer | 0 µm | kurva 3 | 26,0 µm | 53,2 µm | 53,5 µm | ya | 0 | 0 | 0 |
| taper lebar (PL 0,6) | chamfer | 10 µm | kurva 1, kurva+merah 2 | 32,4 µm | 66,8 µm | 66,8 µm | ya | 0 | 2 | 0 |
| taper lebar (PL 0,6) | chamfer | 30 µm | error 1, kurva+merah 2 | 43,9 µm | 113,0 µm | 110,3 µm | **tidak** | 0 | 2 | 0 |
| taper lebar (PL 0,6) | chamfer | 90 µm | derau 3 | - | - | - | **tidak** | 0 | 0 | 0 |
| scallop dalam (PL 4,0) | shoulder | 0 µm | kurva 3 | 14,7 µm | 35,4 µm | 36,1 µm | ya | 0 | 0 | 0 |
| scallop dalam (PL 4,0) | shoulder | 10 µm | kurva 3 | 18,4 µm | 35,8 µm | 36,2 µm | ya | 0 | 0 | 0 |
| scallop dalam (PL 4,0) | shoulder | 30 µm | kurva 2, kurva+merah 1 | 28,6 µm | 65,8 µm | 65,8 µm | ya | 0 | 1 | 0 |
| scallop dalam (PL 4,0) | shoulder | 90 µm | derau 3 | - | - | - | **tidak** | 0 | 0 | 0 |
| scallop dalam (PL 4,0) | chamfer | 0 µm | kurva 3 | 34,0 µm | 67,6 µm | 66,9 µm | ya | 0 | 0 | 0 |
| scallop dalam (PL 4,0) | chamfer | 10 µm | kurva 2, kurva+merah 1 | 36,8 µm | 76,7 µm | 77,6 µm | ya | 0 | 1 | 0 |
| scallop dalam (PL 4,0) | chamfer | 30 µm | error 1, kurva+merah 1, tidak wajar 1 | 45,6 µm | 96,3 µm | 99,7 µm | **tidak** | 0 | 1 | 0 |
| scallop dalam (PL 4,0) | chamfer | 90 µm | derau 3 | - | - | - | **tidak** | 0 | 0 | 0 |

**Set tuning3:**

| Die | Finish | Derau | Hasil per seed | Median | p95 | Cakupan p95 | Memenuhi kriteria | Buruk, bertanda merah | Baik, bertanda merah | Kurva buruk tanpa pesan |
|---|---|---|---|---|---|---|---|---|---|---|
| insisif sentral (PL 3,2) | shoulder | 0 µm | kurva 3 | 11,6 µm | 27,7 µm | 27,9 µm | ya | 0 | 0 | 0 |
| insisif sentral (PL 3,2) | shoulder | 10 µm | kurva 3 | 14,3 µm | 29,4 µm | 30,1 µm | ya | 0 | 0 | 0 |
| insisif sentral (PL 3,2) | shoulder | 30 µm | kurva 2, kurva+merah 1 | 27,2 µm | 61,1 µm | 61,2 µm | ya | 0 | 1 | 0 |
| insisif sentral (PL 3,2) | shoulder | 90 µm | derau 3 | - | - | - | **tidak** | 0 | 0 | 0 |
| insisif sentral (PL 3,2) | chamfer | 0 µm | kurva 3 | 19,3 µm | 44,9 µm | 45,8 µm | ya | 0 | 0 | 0 |
| insisif sentral (PL 3,2) | chamfer | 10 µm | kurva 3 | 24,5 µm | 46,7 µm | 46,8 µm | ya | 0 | 0 | 0 |
| insisif sentral (PL 3,2) | chamfer | 30 µm | kurva+merah 2, tidak wajar 1 | 46,1 µm | 95,2 µm | 95,2 µm | **tidak** | 0 | 2 | 0 |
| insisif sentral (PL 3,2) | chamfer | 90 µm | derau 3 | - | - | - | **tidak** | 0 | 0 | 0 |
| kaninus (PL 2,4) | shoulder | 0 µm | kurva 3 | 14,7 µm | 30,5 µm | 30,6 µm | ya | 0 | 0 | 0 |
| kaninus (PL 2,4) | shoulder | 10 µm | kurva 3 | 18,4 µm | 31,4 µm | 31,4 µm | ya | 0 | 0 | 0 |
| kaninus (PL 2,4) | shoulder | 30 µm | kurva 2, kurva+merah 1 | 32,2 µm | 78,3 µm | 79,8 µm | ya | 0 | 1 | 0 |
| kaninus (PL 2,4) | shoulder | 90 µm | derau 3 | - | - | - | **tidak** | 0 | 0 | 0 |
| kaninus (PL 2,4) | chamfer | 0 µm | kurva 3 | 26,5 µm | 50,5 µm | 50,5 µm | ya | 0 | 0 | 0 |
| kaninus (PL 2,4) | chamfer | 10 µm | kurva 3 | 28,6 µm | 54,4 µm | 54,5 µm | ya | 0 | 0 | 0 |
| kaninus (PL 2,4) | chamfer | 30 µm | error 1, kurva+merah 2 | 42,4 µm | 93,7 µm | 94,0 µm | **tidak** | 0 | 2 | 0 |
| kaninus (PL 2,4) | chamfer | 90 µm | derau 3 | - | - | - | **tidak** | 0 | 0 | 0 |
| molar pendek (PL 0,8) | shoulder | 0 µm | kurva 3 | 15,5 µm | 26,9 µm | 27,3 µm | ya | 0 | 0 | 0 |
| molar pendek (PL 0,8) | shoulder | 10 µm | kurva 3 | 17,1 µm | 30,4 µm | 30,4 µm | ya | 0 | 0 | 0 |
| molar pendek (PL 0,8) | shoulder | 30 µm | kurva 1, kurva+merah 2 | 29,7 µm | 66,8 µm | 66,5 µm | ya | 0 | 2 | 0 |
| molar pendek (PL 0,8) | shoulder | 90 µm | derau 3 | - | - | - | **tidak** | 0 | 0 | 0 |
| molar pendek (PL 0,8) | chamfer | 0 µm | kurva 2, kurva+merah 1 | 33,5 µm | 74,5 µm | 74,6 µm | ya | 0 | 1 | 0 |
| molar pendek (PL 0,8) | chamfer | 10 µm | kurva 2, kurva+merah 1 | 34,7 µm | 73,4 µm | 73,3 µm | ya | 0 | 1 | 0 |
| molar pendek (PL 0,8) | chamfer | 30 µm | kurva+merah 3 | 47,7 µm | 104,3 µm | 104,3 µm | ya | 0 | 3 | 0 |
| molar pendek (PL 0,8) | chamfer | 90 µm | derau 3 | - | - | - | **tidak** | 0 | 0 | 0 |
| premolar elips (PL 1,6) | shoulder | 0 µm | kurva 3 | 15,1 µm | 29,5 µm | 31,9 µm | ya | 0 | 0 | 0 |
| premolar elips (PL 1,6) | shoulder | 10 µm | kurva 3 | 19,2 µm | 34,2 µm | 34,5 µm | ya | 0 | 0 | 0 |
| premolar elips (PL 1,6) | shoulder | 30 µm | kurva 2, kurva+merah 1 | 31,2 µm | 100,4 µm | 96,3 µm | ya | 0 | 1 | 0 |
| premolar elips (PL 1,6) | shoulder | 90 µm | derau 3 | - | - | - | **tidak** | 0 | 0 | 0 |
| premolar elips (PL 1,6) | chamfer | 0 µm | kurva 3 | 22,9 µm | 48,9 µm | 49,0 µm | ya | 0 | 0 | 0 |
| premolar elips (PL 1,6) | chamfer | 10 µm | kurva 1, kurva+merah 2 | 27,2 µm | 58,2 µm | 58,0 µm | ya | 0 | 2 | 0 |
| premolar elips (PL 1,6) | chamfer | 30 µm | error 1, kurva+merah 2 | 42,7 µm | 135,3 µm | 128,2 µm | **tidak** | 0 | 2 | 0 |
| premolar elips (PL 1,6) | chamfer | 90 µm | derau 3 | - | - | - | **tidak** | 0 | 0 | 0 |
| undercut 8 derajat (PL 1,2) | shoulder | 0 µm | kurva 3 | 14,9 µm | 27,2 µm | 27,3 µm | ya | 0 | 0 | 0 |
| undercut 8 derajat (PL 1,2) | shoulder | 10 µm | kurva 3 | 19,3 µm | 30,4 µm | 30,6 µm | ya | 0 | 0 | 0 |
| undercut 8 derajat (PL 1,2) | shoulder | 30 µm | kurva 1, kurva+merah 2 | 31,5 µm | 83,3 µm | 84,4 µm | ya | 0 | 2 | 0 |
| undercut 8 derajat (PL 1,2) | shoulder | 90 µm | derau 3 | - | - | - | **tidak** | 0 | 0 | 0 |
| undercut 8 derajat (PL 1,2) | chamfer | 0 µm | kurva 3 | 28,5 µm | 46,5 µm | 46,6 µm | ya | 0 | 0 | 0 |
| undercut 8 derajat (PL 1,2) | chamfer | 10 µm | kurva 1, kurva+merah 2 | 30,5 µm | 64,4 µm | 63,5 µm | ya | 0 | 2 | 0 |
| undercut 8 derajat (PL 1,2) | chamfer | 30 µm | kurva+merah 3 | 44,4 µm | 130,7 µm | 126,8 µm | ya | 0 | 3 | 0 |
| undercut 8 derajat (PL 1,2) | chamfer | 90 µm | derau 3 | - | - | - | **tidak** | 0 | 0 | 0 |

**Set uji kedua (dijalankan sekali):**

| Die | Finish | Derau | Hasil per seed | Median | p95 | Cakupan p95 | Memenuhi kriteria | Buruk, bertanda merah | Baik, bertanda merah | Kurva buruk tanpa pesan |
|---|---|---|---|---|---|---|---|---|---|---|
| lateral (PL 2,9) | shoulder | 0 µm | kurva 3 | 8,7 µm | 22,2 µm | 22,9 µm | ya | 0 | 0 | 0 |
| lateral (PL 2,9) | shoulder | 10 µm | kurva 3 | 12,9 µm | 22,3 µm | 22,9 µm | ya | 0 | 0 | 0 |
| lateral (PL 2,9) | shoulder | 30 µm | kurva 3 | 21,6 µm | 47,4 µm | 47,5 µm | ya | 0 | 0 | 0 |
| lateral (PL 2,9) | shoulder | 90 µm | derau 3 | - | - | - | **tidak** | 0 | 0 | 0 |
| lateral (PL 2,9) | chamfer | 0 µm | kurva 1, kurva+merah 2 | 17,8 µm | 40,5 µm | 41,0 µm | ya | 0 | 2 | 0 |
| lateral (PL 2,9) | chamfer | 10 µm | kurva 1, kurva+merah 2 | 23,5 µm | 44,9 µm | 45,4 µm | ya | 0 | 2 | 0 |
| lateral (PL 2,9) | chamfer | 30 µm | kurva+merah 3 | 39,2 µm | 71,9 µm | 71,1 µm | ya | 0 | 3 | 0 |
| lateral (PL 2,9) | chamfer | 90 µm | derau 3 | - | - | - | **tidak** | 0 | 0 | 0 |
| kaninus lebar (PL 2,5) | shoulder | 0 µm | kurva 3 | 16,6 µm | 30,0 µm | 30,0 µm | ya | 0 | 0 | 0 |
| kaninus lebar (PL 2,5) | shoulder | 10 µm | kurva 3 | 18,9 µm | 31,4 µm | 31,3 µm | ya | 0 | 0 | 0 |
| kaninus lebar (PL 2,5) | shoulder | 30 µm | kurva 2, kurva+merah 1 | 30,0 µm | 72,3 µm | 72,2 µm | ya | 0 | 1 | 0 |
| kaninus lebar (PL 2,5) | shoulder | 90 µm | derau 3 | - | - | - | **tidak** | 0 | 0 | 0 |
| kaninus lebar (PL 2,5) | chamfer | 0 µm | kurva 3 | 30,4 µm | 58,4 µm | 58,2 µm | ya | 0 | 0 | 0 |
| kaninus lebar (PL 2,5) | chamfer | 10 µm | kurva 1, kurva+merah 2 | 31,6 µm | 56,5 µm | 56,4 µm | ya | 0 | 2 | 0 |
| kaninus lebar (PL 2,5) | chamfer | 30 µm | error 1, kurva+merah 2 | 48,0 µm | 107,9 µm | 108,2 µm | **tidak** | 0 | 2 | 0 |
| kaninus lebar (PL 2,5) | chamfer | 90 µm | derau 3 | - | - | - | **tidak** | 0 | 0 | 0 |
| molar lebar pendek (PL 1,4) | shoulder | 0 µm | kurva 3 | 17,8 µm | 30,9 µm | 31,0 µm | ya | 0 | 0 | 0 |
| molar lebar pendek (PL 1,4) | shoulder | 10 µm | kurva 3 | 17,9 µm | 33,8 µm | 33,9 µm | ya | 0 | 0 | 0 |
| molar lebar pendek (PL 1,4) | shoulder | 30 µm | kurva 2, kurva+merah 1 | 28,9 µm | 57,3 µm | 57,3 µm | ya | 0 | 1 | 0 |
| molar lebar pendek (PL 1,4) | shoulder | 90 µm | derau 3 | - | - | - | **tidak** | 0 | 0 | 0 |
| molar lebar pendek (PL 1,4) | chamfer | 0 µm | kurva 3 | 42,2 µm | 84,0 µm | 84,2 µm | ya | 0 | 0 | 0 |
| molar lebar pendek (PL 1,4) | chamfer | 10 µm | kurva 3 | 44,8 µm | 86,0 µm | 86,0 µm | ya | 0 | 0 | 0 |
| molar lebar pendek (PL 1,4) | chamfer | 30 µm | error 1, tidak wajar 2 | - | - | - | **tidak** | 0 | 0 | 0 |
| molar lebar pendek (PL 1,4) | chamfer | 90 µm | derau 3 | - | - | - | **tidak** | 0 | 0 | 0 |
| premolar taper 16 (PL 1,0) | shoulder | 0 µm | kurva 3 | 15,0 µm | 29,2 µm | 29,3 µm | ya | 0 | 0 | 0 |
| premolar taper 16 (PL 1,0) | shoulder | 10 µm | kurva 3 | 19,0 µm | 31,8 µm | 31,8 µm | ya | 0 | 0 | 0 |
| premolar taper 16 (PL 1,0) | shoulder | 30 µm | kurva+merah 3 | 34,2 µm | 78,1 µm | 78,0 µm | ya | 0 | 3 | 0 |
| premolar taper 16 (PL 1,0) | shoulder | 90 µm | derau 3 | - | - | - | **tidak** | 0 | 0 | 0 |
| premolar taper 16 (PL 1,0) | chamfer | 0 µm | kurva 3 | 22,2 µm | 47,3 µm | 47,4 µm | ya | 0 | 0 | 0 |
| premolar taper 16 (PL 1,0) | chamfer | 10 µm | kurva 3 | 29,2 µm | 54,6 µm | 54,5 µm | ya | 0 | 0 | 0 |
| premolar taper 16 (PL 1,0) | chamfer | 30 µm | error 1, kurva+merah 2 | 41,0 µm | 158,0 µm | 152,7 µm | **tidak** | 1 | 1 | 0 |
| premolar taper 16 (PL 1,0) | chamfer | 90 µm | derau 3 | - | - | - | **tidak** | 0 | 0 | 0 |
| undercut di puncak (PL 2,0) | shoulder | 0 µm | kurva 3 | 15,1 µm | 31,3 µm | 31,6 µm | ya | 0 | 0 | 0 |
| undercut di puncak (PL 2,0) | shoulder | 10 µm | kurva 3 | 18,9 µm | 32,6 µm | 32,7 µm | ya | 0 | 0 | 0 |
| undercut di puncak (PL 2,0) | shoulder | 30 µm | kurva 1, kurva+merah 2 | 32,7 µm | 75,3 µm | 75,2 µm | ya | 0 | 2 | 0 |
| undercut di puncak (PL 2,0) | shoulder | 90 µm | derau 3 | - | - | - | **tidak** | 0 | 0 | 0 |
| undercut di puncak (PL 2,0) | chamfer | 0 µm | kurva 3 | 26,9 µm | 46,8 µm | 46,9 µm | ya | 0 | 0 | 0 |
| undercut di puncak (PL 2,0) | chamfer | 10 µm | kurva 1, kurva+merah 2 | 32,1 µm | 60,0 µm | 59,4 µm | ya | 0 | 2 | 0 |
| undercut di puncak (PL 2,0) | chamfer | 30 µm | kurva+merah 3 | 47,4 µm | 125,5 µm | 122,4 µm | ya | 0 | 3 | 0 |
| undercut di puncak (PL 2,0) | chamfer | 90 µm | derau 3 | - | - | - | **tidak** | 0 | 0 | 0 |

Kesimpulan:
- **Kriteria maintainer terpenuhi:** kurva buruk tanpa pesan dan tanpa segmen merah = **0** di keempat set (tuning, tuning2, tuning3, uji). Kurva buruk yang tersisa: 1 di tuning (CEJ PL 3,5, chamfer 30 µm, median 52,7 µm) dan 1 di set uji (premolar taper 16°, chamfer 30 µm, cakupan p95 152,7 µm); keduanya bertanda merah.
- **Perbaikan titik jauh** menghapus ketiga kurva buruk insisif sentral di tuning3 tanpa memperburuk tuning dan tuning2.
- **Alarm palsu:** kurva baik bertanda merah 26/72 (tuning), 18/68 (tuning2), 25/87 (tuning3), dan 24/85 (uji). Per derau dan finish (keempat set digabung): derau 0 µm shoulder 0/54, chamfer 6/54; 10 µm shoulder 2/54, chamfer 18/54; 30 µm shoulder 29/54, chamfer 38/40.
- **Error eksplisit** masih paling sering pada chamfer + derau 30 µm. Di set uji, molar lebar pendek chamfer 30 µm gagal di ketiga seed (1 error, 2 ditolak kewajaran), jadi pengguna harus memakai Draw Margin di kasus itu.
- **Lokasi penanda belum andal** (lihat keterbatasan di atas): jangan anggap bagian tanpa merah pasti benar. Sisi proksimal tetap harus diperiksa.
- p95 dan maksimum bisa beberapa kali median, karena kurva bisa melenceng lokal. Ambang p95 belum ditetapkan karena tidak ada sumbernya.
- Catatan: akurasi scanner 10-90 µm di paper Teeth3DS+ adalah akurasi rekonstruksi, bukan derau per vertex. Derau 90 µm per vertex adalah skenario uji terburuk, bukan kondisi scan tipikal.

**Draw Margin (margin gambar manual).** Untuk kasus yang ditolak deteksi, atau kalau pengguna tidak percaya hasilnya:
- Operator `dentalcad.margin_draw` (modal): klik titik di permukaan die sesuai urutan di sekeliling margin, Backspace menghapus titik terakhir, Enter menutup kurva, Esc membatalkan. Draf garis tampil selama menggambar.
- `core.margin.draw_margin` memproyeksikan titik ke permukaan die, lalu membuang klik ganda (< 0,05 mm dari titik sebelumnya) dan klik penutup yang jatuh di titik pertama. Butuh minimal 4 titik berbeda.
- Hasilnya objek `<die> Margin` dan `<die> Margin Preview` yang sama persis dengan hasil Detect Margin, juga berstatus draf dengan segmen merah, jadi diedit dan dikonfirmasi dengan cara yang sama.
- **Magnet** (opsi `use_magnet`, default aktif, tombol M saat menggambar): kurva melalui klik diambil rapat (0,15 mm), setiap titiknya ditarik ke crease terdekat dengan `refine_on_crease` yang sama seperti deteksi, titik tanpa crease di sekitarnya tetap di kurva klik, lalu dihaluskan dan diambil titik kontrol tiap 1,0 mm. Titik kontrol hasilnya tidak lagi sama dengan titik klik.
- **Magnet otomatis mati bila perkiraan derau > 60 µm** (ambang yang sama dengan pengaman deteksi), dengan peringatan "magnet off because the scan is too noisy". `core.margin.draw_margin(magnet=True)` pada scan seperti itu memberi `MarginNoiseError`. Alasan terukur: pada die derau 90 µm, magnet menarik kurva ke crease palsu dari derau (median 33 → 198 µm).
- **Pengukuran alur 12 klik** (2026-10-24, sebelum → sesudah magnet; segmen merah dari 256 sampel, deviasi terhadap margin benar):

| Alur | Tanpa magnet | Dengan magnet |
|---|---|---|
| Uji headless lama: die derau 90 µm yang ditolak Detect, 12 klik di margin + 0,05 mm | 22 segmen, median 33 µm, cakupan p95 79 µm | magnet otomatis mati (bila dipaksa: 17 segmen, median 198 µm, cakupan p95 379 µm) |
| Uji headless baru: Load Synthetic Case chamfer, scallop 1 mm, derau 10 µm, seed 1, 12 klik dengan simpangan acak 0,15 mm | 8 segmen, median 109 µm | 0 segmen, median 39 µm |
| Chamfer, scallop 1 mm, derau 10 µm, seed 2, 12 klik di margin + 0,05 mm | 8 segmen, median 56 µm, cakupan p95 108 µm | 0 segmen, median 34 µm, cakupan p95 59 µm |
| 54 kasus: shoulder/chamfer × scallop 0/1,0/1,6 mm × derau 0/10/30 µm × 3 seed, 12 klik dengan simpangan acak 0,15 mm | segmen merah median 6 (maks 12), 0% tanpa merah; median deviasi: median 102 µm, maks 136 µm; cakupan p95 maks 311 µm | segmen merah median 0 (maks 7), 57% tanpa merah; median deviasi: median 30 µm, maks 49 µm; cakupan p95 maks 109 µm |
- Jalur klik modal tidak bisa diuji headless; logikanya diuji lewat properti `points`.

**Uji manual di Blender.** Tombol "Load Synthetic Case" di panel Dental (langkah Margin) membuat `Synthetic Die` (finish, scallop amplitudo, derau, sektor undercut, dan seed bisa diubah di panel redo) beserta kurva hijau `Synthetic Die Truth Margin` (margin benar, tidak bisa dipilih). Margin benar juga disimpan di properti `dentalcad_truth_margin`, sehingga "Detect Margin" melaporkan deviasi "vs true margin".

**Ringkasan status §5.1** (ditutup 2026-10-24). Semua angka di bawah berasal dari die sintetis (§4). Belum ada satu pun scan asli yang diuji.

*Yang terbukti (data sintetis):*
- Detect Margin memenuhi median ≤ 50 µm dan cakupan p95 ≤ 150 µm untuk sebagian besar kombinasi shoulder/chamfer, scallop puncak-lembah 0 sampai 4 mm, dan derau 0 sampai 30 µm, termasuk di set uji kedua yang dikunci (commit `3e17128`) dan hanya dijalankan sekali.
- Tidak gagal diam-diam: semua kasus derau 90 µm berhenti dengan peringatan derau. Di keempat set benchmark, kurva buruk tanpa pesan dan tanpa segmen merah = 0. Dengan pengaman derau dimatikan pun, 0 dari 48 kasus 90 µm lolos tanpa pesan atau merah.
- Kegagalan yang tidak bisa diselesaikan otomatis muncul sebagai error eksplisit yang mengarah ke Draw Margin.
- Draw Margin dengan magnet mengubah 12 klik kasar (simpangan 0,15 mm) menjadi kurva bermedian ≤ 49 µm di 54 kasus derau 0 sampai 30 µm.
- Alur kerja aman: hasil Detect, Draw, dan Update selalu draf; Confirm Margin wajib; gerbang `require_confirmed_margin` menolak draf dan margin yang diedit setelah dikonfirmasi.
- Operator, edit, Confirm, dan gerbang lulus uji headless di Blender 5.2 pada Windows, macOS, dan Linux (CI).

*Keterbatasan:*
- Chamfer + derau 30 µm adalah kombinasi terlemah: paling sering error, paling dekat ke batas 50 µm, dan alarm palsu penanda tertinggi. Molar lebar pendek chamfer 30 µm di set uji kedua gagal di ketiga seed.
- Satu kurva di set tuning (CEJ PL 3,5, chamfer 30 µm) bermedian 52,7 µm; satu kurva di set uji kedua (premolar taper 16°, chamfer 30 µm) bercakupan p95 152,7 µm. Keduanya bertanda merah.
- Penanda merah lemah dalam menunjuk lokasi galat (83 dari 367 titik bergalat > 0,1 mm berada di dekat segmen merah) dan alarm palsunya tinggi. Karena itu statusnya petunjuk ringan.
- Die sintetis lebih sederhana daripada gigi asli: scallop simetris (mesial = distal, padahal di GLC mesial lebih tinggi), derau Gauss per vertex, tidak ada gusi, retraksi, darah/saliva, lubang scan, margin subgingiva, atau gigi tetangga. Ambang derau 60 µm (DKT) adalah presisi scanner, bukan σ derau per vertex.
- Lapis kewajaran tanpa pengaman derau meloloskan 3 dari 48 kurva buruk 90 µm; yang menangkapnya adalah segmen merah, yang justru lemah dalam lokasi.
- Draw Margin magnetik tidak tersedia pada scan dengan derau > 60 µm, yaitu kasus yang paling membutuhkan gambar manual.
- Klik modal di viewport (Detect dan Draw, termasuk tombol M) tidak diuji headless.

*Yang perlu diuji ulang dengan scan asli* (di `tests/golden_private/`, tidak pernah di-commit):
- Estimator derau: σ terukur pada scan intraoral dan model nyata dibandingkan dengan ambang 60 µm; apakah scan yang wajar lolos dan scan yang buruk tertolak.
- Akurasi Detect Margin terhadap margin yang digambar dokter atau teknisi (bukan margin analitis), terutama sisi proksimal dan margin subgingiva.
- Ambang kewajaran (fraksi crease, rasio panjang 0,90 sampai 1,12, simpangan bidang) dan syarat crease untuk titik jauh (0,5) pada morfologi asli.
- Kalibrasi penanda merah (residual 0,08 mm, sudut 30°, run 2): sensitivitas dan alarm palsu terhadap koreksi dokter, sebelum penanda boleh menjadi peringatan keras.
- Magnet Draw Margin pada scan asli, dan apakah ambang derau untuk mematikan magnet perlu berbeda dari ambang deteksi.
- Waktu proses pada mesh scan asli (jumlah segitiga lebih besar daripada die sintetis).

**Modul core/.** `core/geometry.py` (normal, edge unik, `MeshProjector` titik terdekat di permukaan), `core/margin.py` (`crease_score`, `estimate_noise_sigma`, `closed_path_two_way`, `refine_on_crease`, `MarginCurve`, `detect_margin`, `draw_margin`, `ReviewContext`, `review_curve`, `margin_deviation`).

**Pengujian.**
- Lapis 1 (`tests/core/test_margin.py`, 64 kasus tes):
  - akurasi 12 kombinasi (shoulder/chamfer × scallop 0/1 mm × derau 0/10/30 µm, rotasi acak) dengan median ≤ 50 µm dan cakupan p95 ≤ 150 µm (ambang uji);
  - invarian rotasi dan invarian posisi klik;
  - regresi loop 3 vertex;
  - permukaan datar ditolak;
  - proyeksi titik terdekat dibandingkan dengan brute force;
  - skor crease tinggi di margin dan rendah di sudut cekung;
  - edit kurva (geser, hapus, `apply_edit`);
  - penghalusan yang tidak menyusutkan kurva;
  - pengaman: semua kasus derau 90 µm berhenti dengan peringatan derau, setiap pemeriksaan kewajaran bisa memicu error, titik jarang memberi error eksplisit, dan batas lapis kedua (xfail ketat);
  - scallop CEJ PL 3,5 mm tidak ditolak pemeriksaan panjang, dan rasio panjang tidak bergantung pada tinggi scallop;
  - Draw Margin: proyeksi ke permukaan, kurva tertutup, klik ganda dan klik penutup dibuang, minimal 4 titik, edit seperti hasil deteksi;
  - titik jauh tetap di crease pada insisif sentral (regresi tuning3); penanda: deteksi bersih tanpa segmen merah, kurva yang digeser 0,35 mm ditandai di bagian yang digeser, margin gambar kasar ditandai, run melingkar;
  - magnet: 12 klik kasar menjadi median ≤ 50 µm dengan lebih sedikit segmen merah (shoulder dan chamfer), dan magnet ditolak pada derau 90 µm.
- Lapis 2 (`run_integration.py`): die chamfer + scallop dengan transformasi dunia (geser + putar) → deteksi lewat operator (median dibandingkan dengan margin analitis) → edit (hapus satu titik, geser satu titik) → Update; titik yang digeser terproyeksi, titik lain tidak berubah. Ditambah: "Load Synthetic Case" → "Detect Margin" (median dibandingkan dengan margin benar yang tersimpan), dan kasus derau 90 µm yang harus berakhir dengan error "Scan too noisy" yang menyebut Draw Margin, tanpa objek kurva. Lalu Draw Margin pada die yang sama dengan transformasi dunia: 12 klik → kurva tertutup 12 titik di permukaan, peran dan pratinjau sama dengan hasil deteksi, tanpa objek draf tertinggal, bisa di-Update; 3 klik ditolak. Terakhir: status draf, gerbang menolak draf, Confirm menolak kurva yang diedit tanpa Update, menerima kurva dengan segmen merah tanpa persetujuan tambahan, gerbang menolak lagi setelah titik diedit, dan Update mengembalikan status ke draf. Draw Margin pada die derau 90 µm: magnet otomatis mati (12 titik kontrol). Draw Margin magnetik pada die bersih: segmen merah dan median lebih kecil daripada tanpa magnet.

### 5.2 Sumbu insersi dan undercut

**Gerbang margin (berlaku untuk §5.2 sampai §5.7):** setiap operator wajib memanggil `require_confirmed_margin(die)` dan menolak jalan bila margin masih draf (§5.1). Operator §5.3 juga wajib memanggil `require_current_block_out(die)`: block-out harus ada dan dibuat untuk sumbu yang sedang dipakai.

**Status: terimplementasi** (2026-10-24). Kode di `core/insertion.py`, operator di `ops/insertion.py`, benchmark di `scripts/insertion_benchmark.py`. Semua hasil berasal dari die sintetis.

**Perilaku (konvensi exocad, EXI dan EXQ, §2.1).**
- **Detect Insertion Axis** menghitung sumbu otomatis dan peta undercut. Bila ragu, sumbu ditandai "needs checking" (panel dan laporan), lalu pandangan diarahkan sepanjang sumbu (EXI: software "adjusting the viewpoint"). Ada dua alasan ragu:
  - margin line terbayang ("margin line lies in an undercut");
  - ada kelompok arah lain yang terpisah ≥ 10° tetapi hampir sama baiknya ("another axis is almost as good").
- **Set from View**: sumbu = arah dari preparasi ke pengamat pada pandangan saat ini (EXI: "Set current view as insertion axis").
- **Bola pegangan** `<die> Axis Handle` di ujung panah `<die> Insertion Axis` diseret dengan G. Handler `depsgraph_update_post` menghitung ulang sumbu, tanda ragu, dan peta undercut (EXI: "The Undercut visualization will be updated"). Satu pembaruan peta 0,1-0,2 s pada mesh sintetis sekitar 14 ribu segitiga.
- **Peta undercut**: atribut warna `DentalCAD Undercut` (abu-abu = tidak ada undercut; kuning ke merah sampai 0,5 mm, skala tampilan saja) dan atribut `dentalcad_undercut_mm`.
- **Block Out Undercuts** membuat `<die> Block-out`, sejajar sumbu (EXQ: "always blocked out parallel to the insertion axis"), dengan zona tanpa block-out di dekat margin dari preset material. Block-out lama ditandai kedaluwarsa begitu sumbu berubah.

**Algoritma** (`core/insertion.py`):
1. **Daerah preparasi:** pita face yang dilewati margin terkonfirmasi (ditambah satu cincin) dibuang, lalu komponen terhubung di sisi margin yang permukaannya menyempit ke dalam (median jarak radial vertex dalam 1 mm dari margin, relatif terhadap margin) dipilih sebagai preparasi.
   - *Beda dari versi pertama:* kriteria "di dalam lingkar margin" untuk seluruh komponen memilih akar pada die dengan overhang yang melewati margin, karena dinding akar tepat di lingkar dan tutup dasar juga di dalam lingkar.
2. **Normal dan posisi dihaluskan** (rata-rata Gauss dalam radius max(0,5 mm, 10σ)), karena normal mentah pada mesh ber-jitter menyimpang lebih dari sudut taper (temuan §4).
3. **Sumbu default:** mulai dari luas vektor preparasi (jumlah normal face berbobot luas, sama dengan luas vektor lingkar margin), lalu dicari di grid arah 1° dalam kerucut 20° arah yang meminimalkan luas face membelakangi sumbu. Di antara arah yang hampir sama baiknya (selisih ≤ 0,2% luas preparasi), dipilih yang paling dekat ke arah awal. Kelompok arah hampir optimal lain yang terpisah ≥ 10° menjadi "kandidat sumbu lain".
4. **Kedalaman undercut, uji bayangan eksak:** untuk titik x, permukaan pertama di atasnya (sepanjang sumbu) menentukan keadaannya:
   - tidak ada: bebas;
   - membelakangi sumbu (sisi bawah overhang): terbayang;
   - menghadap sumbu: x di dalam material.
   Kedalaman di titik permukaan = jarak berjalan keluar tegak lurus sumbu selama titiknya terbayang (langkah berlipat lalu bagi dua, resolusi 0,02 mm). Titik yang tidak terbayang di tempatnya diuji lagi satu langkah keluar, untuk dinding overhang itu sendiri dan sudut cekung di kakinya.
   - *Beda dari dua versi pertama:* maksimum jari-jari per sektor sudut, lalu "ada permukaan di atas", sama-sama memberi kedalaman palsu sampai 1 mm di ledge ber-scallop. Penampang die di sana tidak berbentuk bintang, dan berjalan di bawah ledge yang naik berarti masuk ke dalam material. Jawaban benar pertama ikut salah karena memakai definisi yang sama; diperbaiki bersamaan.
5. **Face undercut** (definisi rancangan): face preparasi dengan normal dihaluskan membelakangi sumbu **dan** vertex terbayang dengan kedalaman di atas ambang derau max(0,01 mm, 1σ).
6. **Margin terbayang:** kedalaman titik margin > max(0,02 mm, 2σ).
7. **Scan berderau** (perkiraan σ > 60 µm, ambang yang sama dengan §5.1; margin scan seperti ini dibuat lewat Draw Margin): Detect Insertion Axis dan Block Out tetap jalan, tetapi menampilkan peringatan bahwa peta undercut hanya perkiraan dan block-out pada scan berderau bisa menyisakan bayangan. Sisa bayangan yang terukur selalu dilaporkan (juga bila 0, resolusi uji 20 µm) dan disimpan di objek block-out (`dentalcad_blockout_residual_mm`, `dentalcad_blockout_noisy`). Pada benchmark derau 90 µm sisanya 0 sampai 30 µm.
8. **Block-out:** dihitung pada mesh **mentah** tanpa ambang derau, karena ini geometri yang dipakai crown. Setiap vertex preparasi yang terbayang digeser keluar tegak lurus sumbu sejauh kedalamannya, diulang sampai 16 kali sampai tidak ada yang bergeser. Vertex dalam zona tanpa block-out tidak digeser. Peta tampilan tetap memakai posisi yang dihaluskan supaya tidak berbintik.

**Parameter.**

| Parameter | Status | Nilai | Sumber/asal |
|---|---|---|---|
| Zona tanpa block-out dekat margin (`blockout_free_zone_mm`, preset material) | perlu kalibrasi | 0,1 mm | EXQ: default generik exocad. Bukan angka material (tidak ada di IVO); 3-axis biasanya 0, 5-axis disarankan = cement gap (0,06 mm IVO). Bergantung mesin milling, yang tidak ada di Fase 2. |
| Radius penghalusan | ambang algoritma | max(0,5 mm, 10σ) | Sapuan set tuning: 0,3 / 0,5 / 0,8 mm × ambang 1/2/3σ. 0,5 mm + 1σ memberi IoU rata-rata 0,826 (min 0,747) tanpa luas undercut palsu pada die tanpa undercut; 0,3 mm memberi luas palsu sampai 0,165 mm². |
| Ambang kedalaman (derau) | ambang algoritma | max(0,01 mm, 1σ) | Sapuan yang sama. |
| Kerucut pencarian / langkah grid | ambang algoritma | 20° / 1° | Pilihan awal, tidak disapu. |
| Hampir sama baik | ambang algoritma | 0,2% luas preparasi | Pilihan awal, tidak disapu. |
| Pemisahan kandidat lain | ambang uji | 10° | Pilihan awal. |
| Margin terbayang | ambang algoritma | max(0,02 mm, 2σ) | Pilihan awal. |
| ε tinggi bayangan / resolusi kedalaman | ambang algoritma | 0,02 mm / 0,02 mm | Pilihan awal. |

**Benchmark** (`python scripts/insertion_benchmark.py --set <set> --seeds 3`, 2026-10-24).
- Margin yang dipakai adalah margin analitis, supaya galat §5.2 tidak tercampur galat §5.1.
- Die diputar acak dan mesh ber-jitter. Nilai per baris = terburuk dari 3 seed: IoU terendah, galat tertinggi.
- Sudut sumbu default dibandingkan dengan sumbu die sebenarnya. Angka ini hanya bermakna untuk die tanpa undercut: pada die dengan undercut, sumbu default sengaja dimiringkan untuk mengurangi undercut.
- IoU, kedalaman, dan margin terbayang diukur pada sumbu sebenarnya, terhadap `synthetic.undercut_faces()` (tanda normal analitis) dan `synthetic.undercut_depth_truth()` (uji bayangan eksak pada triangulasi analitis rapat, sel sekitar 0,03-0,05 mm).
- "Sisa bayangan" = kedalaman bayangan terbesar pada mesh hasil block-out, di luar zona dekat margin; 30 µm adalah nilai terkecil yang bisa dilaporkan selain 0.
- **Set uji** didefinisikan dan dikunci bersama `InsertionParams` di commit `dd3f901`, lalu dijalankan sekali. Varian undercut tepat di puncak scallop termasuk di dalamnya.

**Set tuning:**

| Die | Finish | Derau | Sudut sumbu default | Ragu (seed) | IoU face (rancangan / normal) | Kedalaman benar maks | Galat kedalaman MAE / p95 / maks | Vertex galat > 0,1 mm | Margin terbayang: benar / tertandai | Sisa bayangan setelah block-out | Waktu peta |
|---|---|---|---|---|---|---|---|---|---|---|---|
| standar | shoulder | 0 µm | 0,00° | 0/3  | 1,00 / 1,00 | 0 µm | 0,0 / 0 / 0 µm | 0 dari 5147 | tidak (0 µm) / 0/3 | 0 µm | 0,14 s |
| standar | shoulder | 10 µm | 0,02° | 0/3  | 1,00 / 1,00 | 0 µm | 0,0 / 0 / 0 µm | 0 dari 5142 | tidak (0 µm) / 0/3 | 0 µm | 0,15 s |
| standar | shoulder | 30 µm | 0,08° | 0/3  | 1,00 / 0,00 | 0 µm | 0,0 / 0 / 0 µm | 0 dari 5140 | tidak (0 µm) / 0/3 | 0 µm | 0,12 s |
| standar | shoulder | 90 µm | 0,18° | 0/3  | 1,00 / 0,00 | 0 µm | 0,0 / 0 / 0 µm | 0 dari 5137 | tidak (0 µm) / 0/3 | 0 µm | 0,18 s |
| standar | chamfer | 0 µm | 0,08° | 0/3  | 1,00 / 1,00 | 0 µm | 0,0 / 0 / 0 µm | 0 dari 5154 | tidak (0 µm) / 0/3 | 0 µm | 0,20 s |
| standar | chamfer | 10 µm | 0,06° | 0/3  | 1,00 / 1,00 | 0 µm | 0,0 / 0 / 0 µm | 0 dari 5148 | tidak (0 µm) / 0/3 | 0 µm | 0,17 s |
| standar | chamfer | 30 µm | 0,10° | 0/3  | 1,00 / 0,00 | 0 µm | 0,0 / 0 / 0 µm | 0 dari 5142 | tidak (0 µm) / 0/3 | 0 µm | 0,16 s |
| standar | chamfer | 90 µm | 0,13° | 0/3  | 1,00 / 0,00 | 0 µm | 0,0 / 0 / 0 µm | 0 dari 5144 | tidak (0 µm) / 0/3 | 0 µm | 0,19 s |
| standar + scallop PL 2 | shoulder | 0 µm | 0,03° | 0/3  | 1,00 / 1,00 | 0 µm | 0,0 / 0 / 0 µm | 0 dari 5142 | tidak (0 µm) / 0/3 | 0 µm | 0,17 s |
| standar + scallop PL 2 | shoulder | 10 µm | 0,04° | 0/3  | 1,00 / 1,00 | 0 µm | 0,0 / 0 / 0 µm | 0 dari 5139 | tidak (0 µm) / 0/3 | 0 µm | 0,17 s |
| standar + scallop PL 2 | shoulder | 30 µm | 0,08° | 0/3  | 1,00 / 0,00 | 0 µm | 0,0 / 0 / 0 µm | 0 dari 5139 | tidak (0 µm) / 0/3 | 0 µm | 0,19 s |
| standar + scallop PL 2 | shoulder | 90 µm | 0,26° | 0/3  | 1,00 / 0,00 | 0 µm | 0,0 / 0 / 0 µm | 0 dari 5134 | tidak (0 µm) / 0/3 | 0 µm | 0,20 s |
| standar + scallop PL 2 | chamfer | 0 µm | 0,07° | 0/3  | 1,00 / 1,00 | 0 µm | 0,0 / 0 / 0 µm | 0 dari 5147 | tidak (0 µm) / 0/3 | 0 µm | 0,13 s |
| standar + scallop PL 2 | chamfer | 10 µm | 0,07° | 0/3  | 1,00 / 1,00 | 0 µm | 0,0 / 0 / 0 µm | 0 dari 5144 | tidak (0 µm) / 0/3 | 0 µm | 0,12 s |
| standar + scallop PL 2 | chamfer | 30 µm | 0,09° | 0/3  | 1,00 / 0,00 | 0 µm | 0,0 / 0 / 0 µm | 0 dari 5141 | tidak (0 µm) / 0/3 | 0 µm | 0,14 s |
| standar + scallop PL 2 | chamfer | 90 µm | 0,18° | 0/3  | 1,00 / 0,00 | 0 µm | 0,0 / 0 / 0 µm | 0 dari 5140 | tidak (0 µm) / 0/3 | 0 µm | 0,22 s |
| undercut 8 di 90 | shoulder | 0 µm | 6,00° | 0/3  | 0,81 / 0,86 | 701 µm | 2,5 / 24 / 271 µm | 9 dari 5148 | tidak (0 µm) / 0/3 | 0 µm | 0,19 s |
| undercut 8 di 90 | shoulder | 10 µm | 5,02° | 0/3  | 0,79 / 0,84 | 701 µm | 2,4 / 24 / 281 µm | 8 dari 5143 | tidak (0 µm) / 0/3 | 0 µm | 0,18 s |
| undercut 8 di 90 | shoulder | 30 µm | 3,58° | 0/3  | 0,70 / 0,76 | 701 µm | 2,4 / 21 / 204 µm | 6 dari 5139 | tidak (0 µm) / 0/3 | 0 µm | 0,19 s |
| undercut 8 di 90 | shoulder | 90 µm | 3,17° | 0/3  | 0,55 / 0,69 | 701 µm | 5,3 / 36 / 701 µm | 77 dari 5138 | tidak (0 µm) / 0/3 | 30 µm | 0,17 s |
| undercut 8 di 90 | chamfer | 0 µm | 5,83° | 0/3  | 0,87 / 0,92 | 561 µm | 2,2 / 23 / 496 µm | 2 dari 5151 | tidak (0 µm) / 0/3 | 0 µm | 0,20 s |
| undercut 8 di 90 | chamfer | 10 µm | 5,04° | 0/3  | 0,82 / 0,90 | 561 µm | 2,2 / 24 / 214 µm | 2 dari 5152 | tidak (0 µm) / 0/3 | 0 µm | 0,20 s |
| undercut 8 di 90 | chamfer | 30 µm | 3,20° | 0/3  | 0,74 / 0,82 | 561 µm | 2,2 / 19 / 221 µm | 1 dari 5145 | tidak (0 µm) / 0/3 | 0 µm | 0,21 s |
| undercut 8 di 90 | chamfer | 90 µm | 3,09° | 0/3  | 0,57 / 0,75 | 561 µm | 4,4 / 38 / 294 µm | 54 dari 5144 | tidak (0 µm) / 0/3 | 30 µm | 0,19 s |
| undercut 8 di 90 + scallop PL 2 | shoulder | 0 µm | 5,85° | 0/3  | 0,83 / 0,86 | 841 µm | 2,6 / 26 / 391 µm | 8 dari 5140 | tidak (0 µm) / 0/3 | 0 µm | 0,17 s |
| undercut 8 di 90 + scallop PL 2 | shoulder | 10 µm | 5,02° | 0/3  | 0,81 / 0,84 | 841 µm | 2,6 / 26 / 129 µm | 5 dari 5137 | tidak (0 µm) / 0/3 | 0 µm | 0,15 s |
| undercut 8 di 90 + scallop PL 2 | shoulder | 30 µm | 4,05° | 0/3  | 0,72 / 0,78 | 841 µm | 2,6 / 24 / 318 µm | 8 dari 5139 | tidak (0 µm) / 0/3 | 0 µm | 0,14 s |
| undercut 8 di 90 + scallop PL 2 | shoulder | 90 µm | 3,17° | 0/3  | 0,58 / 0,69 | 841 µm | 5,7 / 38 / 841 µm | 87 dari 5135 | tidak (0 µm) / 0/3 | 30 µm | 0,16 s |
| undercut 8 di 90 + scallop PL 2 | chamfer | 0 µm | 5,99° | 0/3  | 0,88 / 0,93 | 704 µm | 2,4 / 26 / 294 µm | 4 dari 5149 | tidak (0 µm) / 0/3 | 0 µm | 0,22 s |
| undercut 8 di 90 + scallop PL 2 | chamfer | 10 µm | 5,05° | 0/3  | 0,85 / 0,90 | 704 µm | 2,3 / 26 / 71 µm | 0 dari 5146 | tidak (0 µm) / 0/3 | 0 µm | 0,19 s |
| undercut 8 di 90 + scallop PL 2 | chamfer | 30 µm | 3,58° | 0/3  | 0,77 / 0,82 | 704 µm | 2,3 / 21 / 101 µm | 1 dari 5141 | tidak (0 µm) / 0/3 | 0 µm | 0,20 s |
| undercut 8 di 90 + scallop PL 2 | chamfer | 90 µm | 3,14° | 0/3  | 0,61 / 0,74 | 704 µm | 4,6 / 39 / 406 µm | 51 dari 5140 | tidak (0 µm) / 0/3 | 0 µm | 0,21 s |

**Set uji (dijalankan sekali):**

| Die | Finish | Derau | Sudut sumbu default | Ragu (seed) | IoU face (rancangan / normal) | Kedalaman benar maks | Galat kedalaman MAE / p95 / maks | Vertex galat > 0,1 mm | Margin terbayang: benar / tertandai | Sisa bayangan setelah block-out | Waktu peta |
|---|---|---|---|---|---|---|---|---|---|---|---|
| undercut 12 di puncak scallop (PL 2) | shoulder | 0 µm | 5,98° | 0/3  | 0,83 / 0,85 | 844 µm | 3,2 / 31 / 129 µm | 10 dari 5140 | tidak (0 µm) / 0/3 | 0 µm | 0,19 s |
| undercut 12 di puncak scallop (PL 2) | shoulder | 10 µm | 5,00° | 0/3  | 0,80 / 0,83 | 844 µm | 3,0 / 29 / 464 µm | 9 dari 5140 | tidak (0 µm) / 0/3 | 0 µm | 0,15 s |
| undercut 12 di puncak scallop (PL 2) | shoulder | 30 µm | 3,00° | 0/3  | 0,75 / 0,79 | 844 µm | 3,3 / 29 / 364 µm | 12 dari 5139 | tidak (0 µm) / 0/3 | 0 µm | 0,15 s |
| undercut 12 di puncak scallop (PL 2) | shoulder | 90 µm | 3,54° | 0/3  | 0,59 / 0,68 | 844 µm | 7,2 / 56 / 836 µm | 108 dari 5135 | tidak (0 µm) / 0/3 | 10 µm | 0,17 s |
| undercut 12 di puncak scallop (PL 2) | chamfer | 0 µm | 5,95° | 0/3  | 0,88 / 0,93 | 636 µm | 2,9 / 31 / 69 µm | 0 dari 5147 | tidak (0 µm) / 0/3 | 0 µm | 0,20 s |
| undercut 12 di puncak scallop (PL 2) | chamfer | 10 µm | 4,97° | 0/3  | 0,85 / 0,90 | 636 µm | 2,7 / 28 / 239 µm | 1 dari 5146 | tidak (0 µm) / 0/3 | 0 µm | 0,24 s |
| undercut 12 di puncak scallop (PL 2) | chamfer | 30 µm | 2,93° | 0/3  | 0,78 / 0,85 | 636 µm | 2,8 / 27 / 104 µm | 1 dari 5143 | tidak (0 µm) / 0/3 | 0 µm | 0,22 s |
| undercut 12 di puncak scallop (PL 2) | chamfer | 90 µm | 3,47° | 0/3  | 0,63 / 0,77 | 636 µm | 5,6 / 46 / 554 µm | 69 dari 5142 | tidak (0 µm) / 0/3 | 0 µm | 0,18 s |
| undercut 10 di puncak CEJ (PL 3) | shoulder | 0 µm | 6,95° | 0/3  | 0,82 / 0,85 | 701 µm | 2,7 / 24 / 299 µm | 16 dari 5139 | tidak (0 µm) / 0/3 | 0 µm | 0,12 s |
| undercut 10 di puncak CEJ (PL 3) | shoulder | 10 µm | 6,41° | 0/3  | 0,79 / 0,84 | 701 µm | 2,7 / 24 / 284 µm | 15 dari 5138 | tidak (0 µm) / 0/3 | 0 µm | 0,10 s |
| undercut 10 di puncak CEJ (PL 3) | shoulder | 30 µm | 5,05° | 0/3  | 0,73 / 0,78 | 701 µm | 2,9 / 26 / 229 µm | 17 dari 5134 | tidak (0 µm) / 0/3 | 0 µm | 0,10 s |
| undercut 10 di puncak CEJ (PL 3) | shoulder | 90 µm | 5,66° | 0/3  | 0,59 / 0,68 | 701 µm | 6,1 / 46 / 611 µm | 84 dari 5131 | tidak (0 µm) / 0/3 | 10 µm | 0,12 s |
| undercut 10 di puncak CEJ (PL 3) | chamfer | 0 µm | 6,97° | 0/3  | 0,88 / 0,93 | 564 µm | 2,4 / 26 / 231 µm | 1 dari 5147 | tidak (0 µm) / 0/3 | 0 µm | 0,11 s |
| undercut 10 di puncak CEJ (PL 3) | chamfer | 10 µm | 5,98° | 0/3  | 0,85 / 0,90 | 564 µm | 2,4 / 26 / 71 µm | 0 dari 5145 | tidak (0 µm) / 0/3 | 0 µm | 0,11 s |
| undercut 10 di puncak CEJ (PL 3) | chamfer | 30 µm | 5,00° | 0/3  | 0,78 / 0,85 | 564 µm | 2,6 / 24 / 94 µm | 0 dari 5139 | tidak (0 µm) / 0/3 | 0 µm | 0,11 s |
| undercut 10 di puncak CEJ (PL 3) | chamfer | 90 µm | 4,97° | 0/3  | 0,64 / 0,77 | 564 µm | 4,9 / 41 / 484 µm | 60 dari 5136 | tidak (0 µm) / 0/3 | 0 µm | 0,11 s |
| margin terbayang (undercut 15, finish 0,5) | shoulder | 0 µm | 6,00° | 3/3 margin line lies in an undercut | 0,86 / 0,87 | 1338 µm | 3,9 / 35 / 169 µm | 30 dari 5145 | ya (841 µm) / 3/3 | 0 µm | 0,14 s |
| margin terbayang (undercut 15, finish 0,5) | shoulder | 10 µm | 5,02° | 3/3 margin line lies in an undercut | 0,84 / 0,86 | 1338 µm | 3,9 / 36 / 207 µm | 30 dari 5139 | ya (841 µm) / 3/3 | 0 µm | 0,15 s |
| margin terbayang (undercut 15, finish 0,5) | shoulder | 30 µm | 2,26° | 3/3 margin line lies in an undercut | 0,81 / 0,81 | 1338 µm | 4,3 / 37 / 1182 µm | 33 dari 5129 | ya (841 µm) / 3/3 | 10 µm | 0,14 s |
| margin terbayang (undercut 15, finish 0,5) | shoulder | 90 µm | 2,29° | 3/3 margin line lies in an undercut | 0,66 / 0,70 | 1338 µm | 10,2 / 71 / 1322 µm | 170 dari 5109 | ya (841 µm) / 3/3 | 30 µm | 0,15 s |
| margin terbayang (undercut 15, finish 0,5) | chamfer | 0 µm | 5,68° | 3/3 margin line lies in an undercut | 0,91 / 0,93 | 1203 µm | 3,4 / 34 / 104 µm | 1 dari 5148 | ya (706 µm) / 3/3 | 0 µm | 0,16 s |
| margin terbayang (undercut 15, finish 0,5) | chamfer | 10 µm | 4,47° | 3/3 margin line lies in an undercut | 0,90 / 0,91 | 1203 µm | 3,5 / 36 / 104 µm | 2 dari 5141 | ya (706 µm) / 3/3 | 0 µm | 0,15 s |
| margin terbayang (undercut 15, finish 0,5) | chamfer | 30 µm | 2,29° | 3/3 margin line lies in an undercut | 0,86 / 0,86 | 1203 µm | 3,8 / 36 / 1066 µm | 8 dari 5140 | ya (706 µm) / 3/3 | 0 µm | 0,16 s |
| margin terbayang (undercut 15, finish 0,5) | chamfer | 90 µm | 2,30° | 3/3 margin line lies in an undercut | 0,71 / 0,77 | 1203 µm | 8,0 / 74 / 1182 µm | 173 dari 5135 | ya (706 µm) / 3/3 | 10 µm | 0,14 s |
| molar taper 10 tanpa undercut | shoulder | 0 µm | 0,01° | 0/3  | 1,00 / 1,00 | 0 µm | 0,0 / 0 / 0 µm | 0 dari 5145 | tidak (0 µm) / 0/3 | 0 µm | 0,08 s |
| molar taper 10 tanpa undercut | shoulder | 10 µm | 0,02° | 0/3  | 1,00 / 1,00 | 0 µm | 0,0 / 0 / 0 µm | 0 dari 5141 | tidak (0 µm) / 0/3 | 0 µm | 0,08 s |
| molar taper 10 tanpa undercut | shoulder | 30 µm | 0,06° | 0/3  | 1,00 / 1,00 | 0 µm | 0,0 / 0 / 0 µm | 0 dari 5139 | tidak (0 µm) / 0/3 | 0 µm | 0,08 s |
| molar taper 10 tanpa undercut | shoulder | 90 µm | 0,17° | 0/3  | 1,00 / 1,00 | 0 µm | 0,0 / 0 / 0 µm | 0 dari 5135 | tidak (0 µm) / 0/3 | 0 µm | 0,09 s |
| molar taper 10 tanpa undercut | chamfer | 0 µm | 0,06° | 0/3  | 1,00 / 1,00 | 0 µm | 0,0 / 0 / 0 µm | 0 dari 5150 | tidak (0 µm) / 0/3 | 0 µm | 0,09 s |
| molar taper 10 tanpa undercut | chamfer | 10 µm | 0,05° | 0/3  | 1,00 / 1,00 | 0 µm | 0,0 / 0 / 0 µm | 0 dari 5145 | tidak (0 µm) / 0/3 | 0 µm | 0,09 s |
| molar taper 10 tanpa undercut | chamfer | 30 µm | 0,09° | 0/3  | 1,00 / 1,00 | 0 µm | 0,0 / 0 / 0 µm | 0 dari 5141 | tidak (0 µm) / 0/3 | 0 µm | 0,09 s |
| molar taper 10 tanpa undercut | chamfer | 90 µm | 0,15° | 0/3  | 1,00 / 1,00 | 0 µm | 0,0 / 0 / 0 µm | 0 dari 5140 | tidak (0 µm) / 0/3 | 0 µm | 0,10 s |
| premolar undercut sempit 6 | shoulder | 0 µm | 5,01° | 0/3  | 0,80 / 0,84 | 494 µm | 1,2 / 0 / 214 µm | 9 dari 5146 | tidak (0 µm) / 0/3 | 0 µm | 0,11 s |
| premolar undercut sempit 6 | shoulder | 10 µm | 4,23° | 0/3  | 0,77 / 0,81 | 494 µm | 1,3 / 0 / 214 µm | 10 dari 5143 | tidak (0 µm) / 0/3 | 0 µm | 0,11 s |
| premolar undercut sempit 6 | shoulder | 30 µm | 2,16° | 0/3  | 0,64 / 0,72 | 494 µm | 1,6 / 0 / 224 µm | 10 dari 5139 | tidak (0 µm) / 0/3 | 0 µm | 0,12 s |
| premolar undercut sempit 6 | shoulder | 90 µm | 2,08° | 0/3  | 0,48 / 0,59 | 494 µm | 2,8 / 0 / 446 µm | 55 dari 5137 | tidak (0 µm) / 0/3 | 10 µm | 0,10 s |
| premolar undercut sempit 6 | chamfer | 0 µm | 5,01° | 0/3  | 0,85 / 0,90 | 396 µm | 1,1 / 0 / 81 µm | 0 dari 5151 | tidak (0 µm) / 0/3 | 0 µm | 0,11 s |
| premolar undercut sempit 6 | chamfer | 10 µm | 4,17° | 0/3  | 0,78 / 0,87 | 396 µm | 1,2 / 0 / 81 µm | 0 dari 5148 | tidak (0 µm) / 0/3 | 0 µm | 0,12 s |
| premolar undercut sempit 6 | chamfer | 30 µm | 2,18° | 0/3  | 0,64 / 0,74 | 396 µm | 1,3 / 0 / 112 µm | 2 dari 5143 | tidak (0 µm) / 0/3 | 0 µm | 0,12 s |
| premolar undercut sempit 6 | chamfer | 90 µm | 3,02° | 0/3  | 0,52 / 0,63 | 396 µm | 2,6 / 0 / 354 µm | 55 dari 5143 | tidak (0 µm) / 0/3 | 0 µm | 0,13 s |

Kesimpulan:
- **Sumbu default pada die tanpa undercut:** galat ≤ 0,26° di set tuning dan ≤ 0,17° di set uji (molar taper 10°), sampai derau 90 µm. Tanpa tanda ragu palsu.
- **Kedalaman undercut:** MAE 1-10 µm, p95 ≤ 74 µm di semua kasus. Tetapi ada beberapa vertex dengan galat besar (sampai 1,3 mm pada "margin terbayang" derau 30-90 µm), semuanya di sudut cekung antara ledge dan dinding overhang:
  - derau 0-30 µm: 0 sampai 33 vertex per die;
  - derau 90 µm: 51 sampai 173 vertex per die.
- **IoU face undercut (definisi rancangan):** 0,77-0,91 pada derau 0-10 µm, 0,64-0,86 pada 30 µm, dan 0,48-0,71 pada 90 µm. Selisihnya terutama di tepi atas dinding overhang (kedalaman bayangan mendekati 0 tetapi normalnya membelakangi) dan di sudut cekung (normal tercampur). Jadi definisi rancangan dan jawaban benar tanda-normal berbeda di tempat itu, bukan hanya karena galat.
- **Undercut tepat di puncak scallop:** IoU 0,59-0,88 dan kedalaman MAE ≤ 7 µm, setara dengan sektor lain. Margin tidak terbayang di varian ini, dan memang tidak ditandai.
- **Margin terbayang:** tertandai di 24/24 run (shoulder dan chamfer, derau 0 sampai 90 µm), juga pada sumbu default (yang dimiringkan 2-6°). Tidak ada tanda ragu palsu di 192 run lain (tuning dan uji).
- **"Another axis is almost as good" tidak pernah muncul** di kedua set. Logikanya hanya diuji dengan lanskap buatan (`test_separate_near_optimal_directions_are_reported`). Die sintetis dengan satu sektor undercut tidak punya dua lembah terpisah, jadi pendeteksiannya pada data realistis belum terbukti.
- **Block-out:** sisa bayangan 0 pada derau 0-30 µm di semua kasus, dan ≤ 30 µm (satu langkah uji) pada sebagian kasus 90 µm (batas 16 putaran tercapai).
- **Sumbu default pada die dengan undercut** miring 2-7° dari sumbu die. Ini disengaja (luas membelakangi minimum), tetapi belum dibandingkan dengan pilihan dokter atau teknisi. Pada derau tinggi kemiringannya lebih kecil, karena normal yang dihaluskan meremehkan undercut.

**Tambalan scan berderau (2026-10-24).** Tes core `test_block_out_on_a_noisy_scan_reports_a_small_residual_shadow` (derau 90 µm, undercut 8°: block-out jalan, sisa bayangan diukur dan ≤ 50 µm). Tes headless: scan derau 90 µm → Draw Margin (magnet otomatis mati) → Confirm → Detect Insertion Axis → Block Out. Keduanya jalan, perkiraan derau > 60 µm tersimpan, block-out ditandai berderau, dan sisa bayangannya tercatat.

**Keterbatasan dan yang perlu diuji ulang dengan scan asli:**
- Bentuk die sintetis sederhana: satu sektor undercut, simetris, tanpa gigi tetangga atau gusi. Undercut alami (kontur servikal, preparasi miring) belum diuji.
- Pemisahan preparasi dari akar bergantung pada margin terkonfirmasi yang menutup dan pada sisi preparasi yang menyempit ke dalam. Preparasi dengan margin di bawah kontur yang melebar (emergence negatif) belum diuji.
- Zona tanpa block-out 0,1 mm adalah default software, bukan angka klinis.
- Klik dan seret di viewport (Set from View dengan pandangan nyata, bola pegangan dengan G) tidak diuji headless. Logikanya diuji lewat properti `direction` dan perpindahan lokasi bola.
- Paten PAT2 (penandaan daerah terbayang dan optimasi arah) menurut Google Patents sudah gugur (R119, 2024-04-03). Ini bukan kesimpulan hukum; status perlu dicek di register DPMA sebelum rilis.

**Pengujian.**
- Lapis 1 (`tests/core/test_insertion.py`, 16 kasus tes):
  - sumbu default = sumbu sebenarnya tanpa undercut (shoulder/chamfer, derau 0/30 µm);
  - daerah preparasi tanpa face akar;
  - IoU sektor undercut ≥ 0,7 dan galat kedalaman (MAE < 10 µm, p95 < 50 µm);
  - kebenaran kedalaman 0 tanpa undercut;
  - margin terbayang tertandai, dan sumbu yang dimiringkan 25° membuat margin terbayang;
  - logika kandidat sumbu lain (lanskap buatan);
  - block-out tanpa sisa bayangan di luar zona, zona tidak digeser, gerakan hanya tegak lurus sumbu;
  - tanpa block-out pada die tanpa undercut; zona negatif ditolak.
- Lapis 2 (`run_integration.py`):
  - gerbang menolak margin draf;
  - Detect Insertion Axis pada die dengan undercut 12° di puncak scallop;
  - seret bola 25°: handler depsgraph memperbarui sumbu, peta, dan tanda "margin line lies in an undercut";
  - Set from View, lalu Block Out: sisa bayangan 0, zona 0,1 mm dari preset, gerbang block-out lolos lalu menolak setelah sumbu berubah;
  - setelah margin diubah, semua operator §5.2 ditolak lagi.

**Modul core/.** `core/insertion.py` (`prep_region`, `insertion_context`, `ShadowField`, `undercut_map`, `default_axis`, `check_axis`, `block_out`, `residual_shadow`); `core/synthetic.py` (`undercut_depth_truth`).

### 5.3 Spacer (cement gap)

**Gerbang:** margin terkonfirmasi dan block-out yang belum kedaluwarsa (`require_current_block_out`). Spacer tidak punya status draf/terkonfirmasi. Hasilnya `<die> Spacer` kedaluwarsa begitu margin, sumbu insersi, atau block-out berubah (`spacer_status`, juga dipakai sebagai gerbang §5.4 lewat `require_current_spacer`).

**Status: terimplementasi** (2026-10-24). Kode di `core/geodesic.py` dan `core/spacer.py`, operator di `ops/spacer.py`, benchmark di `scripts/spacer_benchmark.py`. Semua hasil berasal dari die sintetis.

**Urutan** (EXQ, §2.1): block-out §5.2 dulu, lalu cement gap, sesuai konfigurasi milling 5-axis di transkrip.

**Algoritma.** Setiap vertex permukaan dalam (die hasil block-out) digeser

    gap(d) · n + s_r · h(n) + s_a · (n·a) a

- **d** = jarak geodesik ke margin line.
- **n** = normal vertex die hasil block-out yang **dihaluskan** (rata-rata Gauss dalam radius max(0,5 mm, 10σ), sama dengan peta undercut §5.2), **a** = sumbu insersi.
  - *Beda dari versi pertama:* normal mentah. Pada derau ≥ 10 µm itu membuat 19-144 lipatan non-sliver (di atap dekat kutub) dan undercut baru sampai 1,1 mm di dinding (set ukur pertama, sekarang set tuning).
  - Konsekuensi yang diukur: di dalam radius penghalusan dari crease, normal dinding tercampur dengan normal ledge, jadi spacing radial di sana lebih kecil (sekitar 4,7 µm alih-alih 9,9 µm di dinding 0,4 mm dari crease shoulder; `test_smoothing_reduces_radial_spacing_next_to_a_crease`).
- **h(n)** = komponen n yang tegak lurus sumbu (radial = "perpendicular to the occlusal direction", EXQ).
- **gap(d)** = 0 sampai "from margin", lalu naik linear sepanjang lebar transisi sampai cement gap penuh.
- **Spacing** radial s_r dan axial s_a berlaku di seluruh permukaan dalam, termasuk zona tanpa cement gap. Cement gap ditambahkan di atasnya (EXQ, DTX). Bila s_r = s_a, offset spacing = s·n (diuji).
- **Permukaan dalam** = face preparasi ditambah face pita margin yang semua vertexnya di sisi preparasi. Sisi ditentukan oleh (v − m)·(u_p − u_r) > 0, dengan u_p dan u_r arah dari titik margin ke vertex preparasi dan ke vertex akar di dekatnya.
  - *Beda dari versi pertama:* "vertex preparasi terdekat lebih dekat daripada vertex akar terdekat" memasukkan vertex akar sampai 0,78 mm di bawah margin shoulder. Satu arah u_p saja juga tidak cukup, karena pada shoulder u_p horizontal sedangkan vertex akar di bawah margin bergeser vertikal.
  - Face yang dilewati margin tidak ikut. Tepi crown di margin dirancang di langkah border (§5.4).
- **Jarak geodesik** (`core/geodesic.py`): fast marching di segitiga (Kimmel dan Sethian 1998). Sumbernya vertex di sekitar margin dengan jarak awal = jarak eksak ke kurva margin. Setelah itu relaksasi tervektorisasi dengan "segitiga maya" dari pasangan tetangga cincin-1 bersudut < 120°, untuk menutup celah segitiga tumpul pada mesh ber-jitter.
  - *Beda dari rancangan:* rancangan menyebut Dijkstra di graf edge. Pada silinder ber-scallop yang dibuka menjadi bidang (jawaban tertutup), Dijkstra meleset p95 185-202 µm. Fast marching saja meleset p95 6 µm (grid teratur) dan 69 µm (jitter 0,45); dengan relaksasi segitiga maya, 16 µm dan 50 µm.
  - Batas sudut 150° memberi p95 lebih kecil pada mesh ber-jitter (40 µm) tetapi taksiran terlalu kecil sampai 87 µm di grid teratur. 120° membatasi taksiran terlalu kecil ke 32 µm, dan letaknya jauh dari batas zona.
- **Pemeriksaan:** face permukaan dalam yang terbalik terhadap face die dihitung, dengan segitiga sliver (tinggi < 10 µm) dipisah. Undercut baru di permukaan dalam diukur dengan uji bayangan §5.2.
- **Milling 3/4 axis vs 5 axis** (`milling_axes` di preset):
  - **3 atau 4 axis:** block-out kedua sejajar sumbu pada permukaan dalam setelah cement gap, sampai margin (zona 0), dengan algoritma yang sama dengan block-out §5.2 (`core.insertion.block_out_mesh`). Sumber EXQ: "For 3- or 4-axis production, material configurations typically define an additional block-out being applied after generating the cement gap", "to avoid any undercuts that 4-axis machines cannot mill", dan "undercuts are very often blocked out all the way down to the margin using a value set to 0".
  - **5 axis:** tidak ada block-out kedua (EXQ: "a 5-axis machine can produce these"). Undercut permukaan dalam ditulis sebagai atribut warna `DentalCAD Undercut` di `<die> Spacer` dan ditampilkan dengan **Show Undercuts** (EXQ: "The button "Show undercuts" leads to the cement gap undercuts being displayed with a color scale").
  - Opsi operator `use_second_block_out` (default aktif) mematikan block-out kedua. Peta undercut tetap ditulis.
- **Catatan paten (PAT3, §2.1):** "periksa undercut setelah spacing" bersinggungan dengan langkah di klaim 1 EP2187833B1, dan "hapus undercut atau ubah spacing otomatis" dengan klaim 4/9. EP2187833B1 (Institut Straumann AG) masih aktif di Eropa menurut Google Patents (perkiraan berakhir 2028-07-24). Versi AS US20100233659 ditinggalkan sejak 2014. Pengguna di Eropa sebaiknya mematikan block-out kedua (`use_second_block_out`) sampai paten berakhir. Ini bukan kesimpulan hukum. Pemeriksaan undercut setelah spacing yang sudah ada sejak `3f931af` dibiarkan atas keputusan maintainer (2026-10-24) dan perlu ditinjau ahli paten sebelum rilis.

**Parameter** (`data/materials/zircad_prime.json`):

| Parameter | Status | Nilai | Sumber |
|---|---|---|---|
| Gap semen | default pabrikan | 0,06 mm | IVO "Gap thickness of cement". |
| Jarak dari margin tanpa gap ("from margin") | default pabrikan | 1,00 mm | IVO "Beginning of cement" = slider "From margin" (DTX, EXQ). |
| Spacing radial | default pabrikan | 0,01 mm | IVO "Add. distance x/y" = Additional spacing Radial (EXW, DTX, EXQ). |
| Spacing axial | perlu kalibrasi | 0 mm + peringatan | Tidak tercantum di IVO. Di exocad default terkunci bersama radial (DTX, EXQ: "Both sliders are locked"), tetapi IVO hanya memberi x/y, jadi tidak diasumsikan sama. |
| Lebar transisi (`cement_gap_transition_mm`) | perlu kalibrasi | 0,5 mm, linear + peringatan | Tidak ada di IVO, DTX, EXW, maupun EXQ. |
| Jumlah sumbu mesin milling (`milling_axes`) | praktik lab | 5 (isian sementara) | Diisi dari mesin lab: 3, 4, atau 5. Fase 2 belum punya mesin milling, jadi nilai 5 hanya isian. 3/4 axis menambah block-out kedua (EXQ). |

Catatan: angka Kulzer untuk exocad (gap 0,08 mm, beginning of cement gap 1 mm) **tidak** dipakai, karena itu untuk resin cetak cor dima Print Cast ruby, bukan zirkonia.

**Benchmark** (`python scripts/spacer_benchmark.py --set <set> --seeds 3`, 2026-10-24).
- Margin analitis, sumbu sebenarnya, block-out §5.2 dengan zona 0,1 mm, lalu spacer. Setiap kasus diukur untuk 5 axis (undercut permukaan dalam setelah spacing) dan 3/4 axis (block-out kedua, lalu sisa undercut).
- **Jawaban benar eksak** hanya ada untuk die lingkaran tanpa scallop dan tanpa undercut: jarak geodesik ke margin = panjang busur meridian (permukaan putar), dan offset benar = gap(d)·n + s_r·h(n) dari normal analitis. Untuk die elips, ber-scallop, atau ber-undercut hanya lipatan, undercut, dan waktu yang dilaporkan.
- "Gap di zona nol" = vertex dengan jarak benar < 1 mm yang mendapat cement gap > 1 µm.
- Galat jarak geodesik pada derau tinggi sebagian adalah efek yang nyata, bukan galat metode: permukaan berderau memang lebih panjang daripada permukaan analitis yang dijadikan acuan.
- **Riwayat set:**
  - *tuning*: set ukur pertama, dikunci di `09e4c7e` dan dijalankan sekali dengan normal mentah. Hasilnya saat itu: lipatan non-sliver 0-5 tanpa derau dan 19-144 dengan derau; undercut baru di permukaan dalam 30-50 µm (derau 10 µm), 125-365 µm (30 µm), dan 605-1145 µm (90 µm). Hasil itu dipakai untuk memperbaiki arah offset dan menambah block-out kedua, jadi set ini sekarang set tuning. Tabelnya di bawah adalah hasil ulang dengan kode baru.
  - *ukur*: set ukur kedua, didefinisikan dan dikunci bersama kode di commit `7b2e009`, lalu dijalankan sekali.
- **Kriteria maintainer:** untuk 3/4 axis, nol undercut di permukaan dalam pada derau 0-30 µm (resolusi uji 20 µm). Lipatan non-sliver dilaporkan apa adanya.

**Set tuning (kode baru):**

| Die | Finish | Derau | Galat jarak geodesik median / p95 / maks | Gap di zona nol (vertex, maks) | Galat gap zona penuh maks | Galat gap terbesar (transisi) | Galat spacing radial dinding maks | Galat vektor offset p95 / maks | Face terlipat (bukan sliver) | Undercut permukaan dalam, 5 axis | 3/4 axis: block-out kedua (vertex, maks) | 3/4 axis: sisa undercut | Waktu spacer + block-out kedua |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| lingkaran r5 taper 6 | shoulder | 0 µm | 10 / 56 / 171 µm | 35 dari 1011, 12,1 µm | 3,4 µm | 13,9 µm | 9,9 µm | 7,2 / 18,0 µm | 0 (+1 sliver) | 10 µm | 27, 20 µm | 0 µm | 0,96 + 0,37 s |
| lingkaran r5 taper 6 | shoulder | 10 µm | 11 / 60 / 184 µm | 39 dari 1008, 20,7 µm | 3,2 µm | 20,7 µm | 9,6 µm | 7,3 / 24,7 µm | 0 (+2 sliver) | 50 µm | 85, 50 µm | 0 µm | 0,99 + 0,49 s |
| lingkaran r5 taper 6 | shoulder | 30 µm | 29 / 91 / 199 µm | 58 dari 1005, 22,5 µm | 2,3 µm | 22,5 µm | 9,7 µm | 9,2 / 26,7 µm | 0 (+3 sliver) | 65 µm | 179, 65 µm | 0 µm | 0,85 + 0,50 s |
| lingkaran r5 taper 6 | shoulder | 90 µm | 130 / 260 / 519 µm | 163 dari 988, 40,1 µm | 1,0 µm | 45,5 µm | 9,8 µm | 19,8 / 45,0 µm | 0 (+1 sliver) | 275 µm | 313, 275 µm | 0 µm | 1,05 + 1,05 s |
| lingkaran r5 taper 6 | chamfer | 0 µm | 9 / 57 / 162 µm | 5 dari 647, 6,9 µm | 0,0 µm | 16,6 µm | 8,4 µm | 5,7 / 17,6 µm | 0 (+2 sliver) | 0 µm | 0, 0 µm | 0 µm | 0,88 + 0,25 s |
| lingkaran r5 taper 6 | chamfer | 10 µm | 10 / 62 / 172 µm | 4 dari 649, 7,6 µm | 0,0 µm | 12,8 µm | 8,7 µm | 5,9 / 19,5 µm | 0 (+1 sliver) | 30 µm | 11, 30 µm | 0 µm | 1,13 + 0,49 s |
| lingkaran r5 taper 6 | chamfer | 30 µm | 21 / 79 / 189 µm | 8 dari 647, 8,5 µm | 0,0 µm | 13,3 µm | 9,1 µm | 8,0 / 25,4 µm | 0 (+2 sliver) | 65 µm | 69, 65 µm | 0 µm | 0,97 + 0,52 s |
| lingkaran r5 taper 6 | chamfer | 90 µm | 71 / 200 / 421 µm | 45 dari 637, 25,7 µm | 0,5 µm | 32,1 µm | 8,0 µm | 11,8 / 32,3 µm | 0 (+1 sliver) | 150 µm | 259, 150 µm | 0 µm | 0,98 + 0,86 s |
| lingkaran r4 taper 10 tinggi 4 | shoulder | 0 µm | 10 / 38 / 120 µm | 21 dari 1012, 7,0 µm | 3,7 µm | 10,0 µm | 0,0 µm | 6,3 / 15,6 µm | 0 (+1 sliver) | 0 µm | 0, 0 µm | 0 µm | 0,94 + 0,13 s |
| lingkaran r4 taper 10 tinggi 4 | shoulder | 10 µm | 8 / 42 / 107 µm | 23 dari 1009, 11,2 µm | 3,2 µm | 11,2 µm | 9,8 µm | 6,3 / 16,6 µm | 0 (+0 sliver) | 30 µm | 20, 30 µm | 0 µm | 1,00 + 0,35 s |
| lingkaran r4 taper 10 tinggi 4 | shoulder | 30 µm | 27 / 75 / 136 µm | 53 dari 1005, 13,2 µm | 1,4 µm | 13,2 µm | 9,7 µm | 7,5 / 21,3 µm | 0 (+1 sliver) | 50 µm | 121, 60 µm | 0 µm | 0,87 + 0,43 s |
| lingkaran r4 taper 10 tinggi 4 | shoulder | 90 µm | 118 / 236 / 484 µm | 145 dari 989, 36,9 µm | 3,4 µm | 39,9 µm | 9,7 µm | 17,5 / 40,9 µm | 0 (+1 sliver) | 125 µm | 294, 125 µm | 0 µm | 1,11 + 0,61 s |
| lingkaran r4 taper 10 tinggi 4 | chamfer | 0 µm | 6 / 38 / 113 µm | 1 dari 646, 3,4 µm | 0,0 µm | 11,3 µm | 0,0 µm | 3,8 / 15,6 µm | 0 (+0 sliver) | 0 µm | 0, 0 µm | 0 µm | 1,05 + 0,16 s |
| lingkaran r4 taper 10 tinggi 4 | chamfer | 10 µm | 9 / 47 / 121 µm | 2 dari 648, 3,6 µm | 0,0 µm | 8,0 µm | 8,4 µm | 3,9 / 16,6 µm | 0 (+1 sliver) | 30 µm | 11, 30 µm | 0 µm | 0,93 + 0,25 s |
| lingkaran r4 taper 10 tinggi 4 | chamfer | 30 µm | 20 / 77 / 146 µm | 4 dari 646, 4,8 µm | 0,0 µm | 9,3 µm | 8,4 µm | 6,4 / 21,4 µm | 0 (+1 sliver) | 50 µm | 64, 50 µm | 0 µm | 0,98 + 0,41 s |
| lingkaran r4 taper 10 tinggi 4 | chamfer | 90 µm | 75 / 228 / 459 µm | 35 dari 638, 24,9 µm | 1,5 µm | 29,1 µm | 8,1 µm | 9,8 / 29,2 µm | 0 (+1 sliver) | 150 µm | 268, 150 µm | 0 µm | 1,40 + 0,79 s |
| elips + scallop PL 2 | shoulder | 0 µm | - | - | - | - | - | - | 0 (+1 sliver) | 10 µm | 37, 20 µm | 0 µm | 0,95 + 0,40 s |
| elips + scallop PL 2 | shoulder | 10 µm | - | - | - | - | - | - | 0 (+1 sliver) | 50 µm | 102, 50 µm | 0 µm | 0,84 + 0,53 s |
| elips + scallop PL 2 | shoulder | 30 µm | - | - | - | - | - | - | 0 (+2 sliver) | 65 µm | 184, 75 µm | 0 µm | 0,91 + 0,55 s |
| elips + scallop PL 2 | shoulder | 90 µm | - | - | - | - | - | - | 0 (+2 sliver) | 135 µm | 342, 135 µm | 0 µm | 1,09 + 0,93 s |
| elips + scallop PL 2 | chamfer | 0 µm | - | - | - | - | - | - | 0 (+2 sliver) | 10 µm | 2, 10 µm | 0 µm | 0,88 + 0,31 s |
| elips + scallop PL 2 | chamfer | 10 µm | - | - | - | - | - | - | 0 (+1 sliver) | 30 µm | 17, 30 µm | 0 µm | 1,00 + 0,35 s |
| elips + scallop PL 2 | chamfer | 30 µm | - | - | - | - | - | - | 0 (+2 sliver) | 65 µm | 79, 65 µm | 0 µm | 0,98 + 0,48 s |
| elips + scallop PL 2 | chamfer | 90 µm | - | - | - | - | - | - | 0 (+2 sliver) | 245 µm | 281, 245 µm | 0 µm | 1,04 + 1,02 s |
| elips + CEJ PL 3,5 | shoulder | 0 µm | - | - | - | - | - | - | 0 (+1 sliver) | 10 µm | 30, 20 µm | 0 µm | 1,08 + 0,38 s |
| elips + CEJ PL 3,5 | shoulder | 10 µm | - | - | - | - | - | - | 0 (+2 sliver) | 30 µm | 78, 40 µm | 0 µm | 1,01 + 0,48 s |
| elips + CEJ PL 3,5 | shoulder | 30 µm | - | - | - | - | - | - | 0 (+3 sliver) | 65 µm | 162, 70 µm | 0 µm | 0,92 + 0,42 s |
| elips + CEJ PL 3,5 | shoulder | 90 µm | - | - | - | - | - | - | 1 (+1 sliver) | 255 µm | 355, 255 µm | 0 µm | 1,02 + 1,01 s |
| elips + CEJ PL 3,5 | chamfer | 0 µm | - | - | - | - | - | - | 0 (+2 sliver) | 10 µm | 5, 20 µm | 0 µm | 0,89 + 0,33 s |
| elips + CEJ PL 3,5 | chamfer | 10 µm | - | - | - | - | - | - | 1 (+1 sliver) | 30 µm | 31, 30 µm | 0 µm | 0,85 + 0,40 s |
| elips + CEJ PL 3,5 | chamfer | 30 µm | - | - | - | - | - | - | 0 (+1 sliver) | 75 µm | 102, 75 µm | 0 µm | 0,88 + 0,53 s |
| elips + CEJ PL 3,5 | chamfer | 90 µm | - | - | - | - | - | - | 0 (+2 sliver) | 385 µm | 323, 385 µm | 0 µm | 1,09 + 1,13 s |
| lingkaran + undercut 8 | shoulder | 0 µm | - | - | - | - | - | - | 0 (+5 sliver) | 95 µm | 185, 105 µm | 0 µm | 0,97 + 1,31 s |
| lingkaran + undercut 8 | shoulder | 10 µm | - | - | - | - | - | - | 0 (+2 sliver) | 85 µm | 211, 105 µm | 0 µm | 1,01 + 0,97 s |
| lingkaran + undercut 8 | shoulder | 30 µm | - | - | - | - | - | - | 0 (+3 sliver) | 85 µm | 280, 120 µm | 0 µm | 0,98 + 1,26 s |
| lingkaran + undercut 8 | shoulder | 90 µm | - | - | - | - | - | - | 0 (+1 sliver) | 275 µm | 395, 275 µm | 10 µm | 1,01 + 2,38 s |
| lingkaran + undercut 8 | chamfer | 0 µm | - | - | - | - | - | - | 0 (+2 sliver) | 85 µm | 83, 95 µm | 0 µm | 0,99 + 0,91 s |
| lingkaran + undercut 8 | chamfer | 10 µm | - | - | - | - | - | - | 0 (+1 sliver) | 75 µm | 86, 85 µm | 0 µm | 0,94 + 1,08 s |
| lingkaran + undercut 8 | chamfer | 30 µm | - | - | - | - | - | - | 0 (+2 sliver) | 85 µm | 176, 105 µm | 0 µm | 0,93 + 1,73 s |
| lingkaran + undercut 8 | chamfer | 90 µm | - | - | - | - | - | - | 0 (+1 sliver) | 150 µm | 350, 150 µm | 0 µm | 1,07 + 1,79 s |

**Set ukur kedua (dijalankan sekali):**

| Die set ukur | Radius x/y | Tinggi | Taper | Lebar finish | PL scallop | Lainnya |
|---|---|---|---|---|---|---|
| lingkaran r4,5 | 4,5 / 4,5 mm | 5,5 mm | 8° | 1,0 mm | 0 | |
| lingkaran r6 | 6,0 / 6,0 mm | 5,0 mm | 4° | 0,7 mm | 0 | |
| elips taper 12 | 5,2 / 4,6 mm | 5,0 mm | 12° | 1,0 mm | 1,2 mm | |
| insisif sentral | 3,6 / 3,2 mm | 5,5 mm | 8° | 0,8 mm | 3,2 mm | |
| elips + undercut | 4,8 / 4,3 mm | 5,0 mm | 6° | 1,0 mm | 1,6 mm | undercut 10° di 200° |

| Die | Finish | Derau | Galat jarak geodesik median / p95 / maks | Gap di zona nol (vertex, maks) | Galat gap zona penuh maks | Galat gap terbesar (transisi) | Galat spacing radial dinding maks | Galat vektor offset p95 / maks | Face terlipat (bukan sliver) | Undercut permukaan dalam, 5 axis | 3/4 axis: block-out kedua (vertex, maks) | 3/4 axis: sisa undercut | Waktu spacer + block-out kedua |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| lingkaran r4,5 taper 8 tinggi 5,5 | shoulder | 0 µm | 11 / 48 / 141 µm | 27 dari 1012, 9,6 µm | 5,5 µm | 11,4 µm | 10,0 µm | 6,6 / 16,9 µm | 0 (+1 sliver) | 10 µm | 3, 10 µm | 0 µm | 0,83 + 0,24 s |
| lingkaran r4,5 taper 8 tinggi 5,5 | shoulder | 10 µm | 9 / 48 / 138 µm | 28 dari 1009, 15,1 µm | 5,3 µm | 15,1 µm | 9,8 µm | 6,5 / 19,1 µm | 0 (+1 sliver) | 30 µm | 24, 30 µm | 0 µm | 0,83 + 0,28 s |
| lingkaran r4,5 taper 8 tinggi 5,5 | shoulder | 30 µm | 23 / 75 / 145 µm | 54 dari 1005, 15,5 µm | 4,4 µm | 15,5 µm | 9,7 µm | 8,3 / 23,2 µm | 0 (+1 sliver) | 65 µm | 104, 65 µm | 0 µm | 0,93 + 0,37 s |
| lingkaran r4,5 taper 8 tinggi 5,5 | shoulder | 90 µm | 109 / 229 / 457 µm | 157 dari 989, 38,1 µm | 8,9 µm | 43,2 µm | 9,8 µm | 18,6 / 41,5 µm | 0 (+2 sliver) | 170 µm | 257, 170 µm | 0 µm | 1,04 + 0,66 s |
| lingkaran r4,5 taper 8 tinggi 5,5 | chamfer | 0 µm | 6 / 37 / 117 µm | 3 dari 645, 4,7 µm | 0,0 µm | 13,8 µm | 8,2 µm | 4,6 / 16,8 µm | 0 (+1 sliver) | 0 µm | 0, 0 µm | 0 µm | 0,83 + 0,15 s |
| lingkaran r4,5 taper 8 tinggi 5,5 | chamfer | 10 µm | 7 / 41 / 121 µm | 3 dari 648, 5,0 µm | 0,0 µm | 10,2 µm | 0,0 µm | 4,8 / 18,5 µm | 0 (+1 sliver) | 30 µm | 10, 30 µm | 0 µm | 1,08 + 0,23 s |
| lingkaran r4,5 taper 8 tinggi 5,5 | chamfer | 30 µm | 15 / 61 / 146 µm | 6 dari 646, 6,1 µm | 0,0 µm | 11,0 µm | 8,4 µm | 7,1 / 23,6 µm | 0 (+1 sliver) | 50 µm | 57, 50 µm | 0 µm | 0,91 + 0,39 s |
| lingkaran r4,5 taper 8 tinggi 5,5 | chamfer | 90 µm | 59 / 160 / 381 µm | 40 dari 637, 25,3 µm | 0,0 µm | 30,7 µm | 8,0 µm | 10,7 / 30,8 µm | 0 (+2 sliver) | 195 µm | 247, 195 µm | 0 µm | 0,99 + 0,73 s |
| lingkaran r6 taper 4 finish 0,7 | shoulder | 0 µm | 38 / 121 / 294 µm | 18 dari 1203, 12,1 µm | 1,6 µm | 26,5 µm | 11,5 µm | 7,2 / 26,5 µm | 0 (+3 sliver) | 30 µm | 196, 30 µm | 0 µm | 1,05 + 0,71 s |
| lingkaran r6 taper 4 finish 0,7 | shoulder | 10 µm | 43 / 125 / 310 µm | 23 dari 1198, 12,2 µm | 0,9 µm | 26,2 µm | 11,6 µm | 7,5 / 26,2 µm | 0 (+3 sliver) | 50 µm | 299, 60 µm | 0 µm | 0,89 + 0,80 s |
| lingkaran r6 taper 4 finish 0,7 | shoulder | 30 µm | 77 / 160 / 330 µm | 47 dari 1197, 17,2 µm | 0,0 µm | 25,8 µm | 16,7 µm | 10,8 / 32,0 µm | 0 (+3 sliver) | 75 µm | 361, 75 µm | 0 µm | 0,81 + 0,88 s |
| lingkaran r6 taper 4 finish 0,7 | shoulder | 90 µm | 233 / 422 / 694 µm | 173 dari 1164, 52,0 µm | 0,0 µm | 55,9 µm | 50,6 µm | 21,9 / 55,4 µm | 0 (+2 sliver) | 230 µm | 446, 230 µm | 0 µm | 0,91 + 1,45 s |
| lingkaran r6 taper 4 finish 0,7 | chamfer | 0 µm | 35 / 123 / 286 µm | 28 dari 918, 18,8 µm | 0,4 µm | 19,7 µm | 18,4 µm | 7,4 / 21,2 µm | 0 (+1 sliver) | 30 µm | 132, 40 µm | 0 µm | 0,91 + 0,74 s |
| lingkaran r6 taper 4 finish 0,7 | chamfer | 10 µm | 42 / 130 / 292 µm | 29 dari 918, 19,2 µm | 0,0 µm | 20,3 µm | 18,9 µm | 7,6 / 24,2 µm | 1 (+2 sliver) | 50 µm | 259, 60 µm | 0 µm | 0,89 + 0,89 s |
| lingkaran r6 taper 4 finish 0,7 | chamfer | 30 µm | 58 / 153 / 312 µm | 47 dari 913, 18,3 µm | 0,0 µm | 22,5 µm | 18,2 µm | 10,3 / 31,5 µm | 1 (+3 sliver) | 65 µm | 351, 90 µm | 0 µm | 0,82 + 0,96 s |
| lingkaran r6 taper 4 finish 0,7 | chamfer | 90 µm | 141 / 343 / 593 µm | 99 dari 897, 37,1 µm | 0,0 µm | 50,2 µm | 36,6 µm | 17,1 / 50,2 µm | 0 (+2 sliver) | 230 µm | 505, 230 µm | 0 µm | 0,99 + 1,30 s |
| elips taper 12 scallop PL 1,2 | shoulder | 0 µm | - | - | - | - | - | - | 0 (+1 sliver) | 0 µm | 0, 0 µm | 0 µm | 0,92 + 0,13 s |
| elips taper 12 scallop PL 1,2 | shoulder | 10 µm | - | - | - | - | - | - | 0 (+2 sliver) | 30 µm | 4, 30 µm | 0 µm | 0,88 + 0,21 s |
| elips taper 12 scallop PL 1,2 | shoulder | 30 µm | - | - | - | - | - | - | 0 (+1 sliver) | 85 µm | 62, 85 µm | 0 µm | 0,87 + 0,37 s |
| elips taper 12 scallop PL 1,2 | shoulder | 90 µm | - | - | - | - | - | - | 0 (+2 sliver) | 195 µm | 187, 195 µm | 0 µm | 1,03 + 0,55 s |
| elips taper 12 scallop PL 1,2 | chamfer | 0 µm | - | - | - | - | - | - | 0 (+2 sliver) | 0 µm | 0, 0 µm | 0 µm | 0,85 + 0,14 s |
| elips taper 12 scallop PL 1,2 | chamfer | 10 µm | - | - | - | - | - | - | 0 (+1 sliver) | 30 µm | 6, 30 µm | 0 µm | 0,84 + 0,22 s |
| elips taper 12 scallop PL 1,2 | chamfer | 30 µm | - | - | - | - | - | - | 0 (+1 sliver) | 50 µm | 49, 60 µm | 0 µm | 0,92 + 0,30 s |
| elips taper 12 scallop PL 1,2 | chamfer | 90 µm | - | - | - | - | - | - | 0 (+3 sliver) | 170 µm | 226, 175 µm | 0 µm | 1,05 + 0,58 s |
| insisif sentral PL 3,2 | shoulder | 0 µm | - | - | - | - | - | - | 0 (+2 sliver) | 10 µm | 1, 10 µm | 0 µm | 0,94 + 0,18 s |
| insisif sentral PL 3,2 | shoulder | 10 µm | - | - | - | - | - | - | 0 (+1 sliver) | 30 µm | 27, 40 µm | 0 µm | 0,88 + 0,25 s |
| insisif sentral PL 3,2 | shoulder | 30 µm | - | - | - | - | - | - | 0 (+2 sliver) | 95 µm | 147, 95 µm | 0 µm | 1,06 + 0,42 s |
| insisif sentral PL 3,2 | shoulder | 90 µm | - | - | - | - | - | - | 0 (+1 sliver) | 230 µm | 356, 230 µm | 0 µm | 1,02 + 1,07 s |
| insisif sentral PL 3,2 | chamfer | 0 µm | - | - | - | - | - | - | 0 (+2 sliver) | 10 µm | 6, 10 µm | 0 µm | 0,92 + 0,22 s |
| insisif sentral PL 3,2 | chamfer | 10 µm | - | - | - | - | - | - | 1 (+0 sliver) | 50 µm | 53, 50 µm | 0 µm | 0,86 + 0,38 s |
| insisif sentral PL 3,2 | chamfer | 30 µm | - | - | - | - | - | - | 0 (+1 sliver) | 50 µm | 183, 80 µm | 0 µm | 0,96 + 0,37 s |
| insisif sentral PL 3,2 | chamfer | 90 µm | - | - | - | - | - | - | 1 (+2 sliver) | 245 µm | 437, 245 µm | 0 µm | 1,05 + 0,85 s |
| elips + undercut 10 di 200 | shoulder | 0 µm | - | - | - | - | - | - | 0 (+4 sliver) | 95 µm | 202, 115 µm | 0 µm | 0,86 + 1,14 s |
| elips + undercut 10 di 200 | shoulder | 10 µm | - | - | - | - | - | - | 0 (+1 sliver) | 95 µm | 224, 105 µm | 0 µm | 1,42 + 0,85 s |
| elips + undercut 10 di 200 | shoulder | 30 µm | - | - | - | - | - | - | 0 (+2 sliver) | 95 µm | 287, 120 µm | 0 µm | 0,90 + 1,27 s |
| elips + undercut 10 di 200 | shoulder | 90 µm | - | - | - | - | - | - | 0 (+2 sliver) | 195 µm | 471, 205 µm | 10 µm | 0,96 + 2,16 s |
| elips + undercut 10 di 200 | chamfer | 0 µm | - | - | - | - | - | - | 0 (+2 sliver) | 95 µm | 95, 105 µm | 0 µm | 0,92 + 0,95 s |
| elips + undercut 10 di 200 | chamfer | 10 µm | - | - | - | - | - | - | 0 (+1 sliver) | 85 µm | 115, 105 µm | 0 µm | 0,85 + 1,03 s |
| elips + undercut 10 di 200 | chamfer | 30 µm | - | - | - | - | - | - | 0 (+2 sliver) | 85 µm | 186, 95 µm | 0 µm | 0,90 + 1,47 s |
| elips + undercut 10 di 200 | chamfer | 90 µm | - | - | - | - | - | - | 0 (+1 sliver) | 185 µm | 395, 185 µm | 0 µm | 0,98 + 1,43 s |

Kesimpulan:
- **Kriteria terpenuhi:** 3/4 axis tanpa sisa undercut di permukaan dalam pada derau 0-30 µm, 90 dari 90 run di set ukur (dan 90 dari 90 di set tuning). Pada derau 90 µm sisa 10 µm muncul di 1 run set tuning dan 2 run set ukur (die dengan undercut, shoulder). Block-out kedua menggeser 0-361 vertex sampai 120 µm pada derau 0-30 µm.
- **Lipatan non-sliver:** 0-1 face di semua kasus kedua set (normal mentah: 19-144).
- **Undercut permukaan dalam pada 5 axis (tanpa block-out kedua):**
  - die tanpa undercut: 0-30 µm tanpa derau, 10-50 µm pada derau 10 µm, 30-95 µm pada 30 µm, dan 50-385 µm pada 90 µm;
  - die dengan undercut: 75-95 µm pada derau 0-30 µm, di ledge di bawah dinding hasil block-out.
  - Ini sesuai peringatan EXQ untuk 5-axis, dan memang hanya ditampilkan, tidak dihapus.
- **Akurasi spacer** (die lingkaran, derau 0-30 µm):
  - galat gap di zona penuh ≤ 5,5 µm;
  - galat vektor offset p95 4-11 µm dan maks 15-32 µm (normal mentah: maks sampai 90 µm);
  - galat spacing radial dinding sampai 9,9 µm pada die r4,5/r5, tetapi 16,7-18,9 µm pada die r6 finish 0,7. Di sana galat jarak geodesik membuat vertex dinding di zona nol ikut mendapat gap.
- **Galat jarak geodesik** tetap terbatas oleh mesh:
  - p95 37-91 µm pada die r4/r4,5/r5 derau 0-30 µm;
  - **121-160 µm pada die r6** (segitiga lebih besar: n_theta 128 pada jari-jari 6 mm);
  - akibatnya sampai 58 dari sekitar 1.000 vertex zona nol mendapat cement gap (maks 23 µm), dan galat gap di transisi sampai 26,5 µm.
- **Waktu:** spacer 0,7-1,4 s, block-out kedua 0,1-2,4 s.

**Keterbatasan dan yang perlu diuji ulang dengan scan asli:**
- Jawaban benar eksak hanya pada die lingkaran tanpa scallop. Akurasi jarak pada margin ber-scallop hanya diuji di silinder yang dibuka.
- Normal dihaluskan mengecilkan spacing radial dalam radius penghalusan dari crease.
- Galat jarak geodesik naik dengan ukuran segitiga (die r6), jadi batas zona "from margin" pada scan kasar bisa bergeser sekitar 0,1-0,3 mm.
- Lebar transisi 0,5 mm dan spacing axial 0 berstatus perlu kalibrasi; `milling_axes` = 5 hanya isian sampai lab mengisi. Nilai akhir semua parameter spacer bergantung pada mesin milling, yang tidak ada di Fase 2.
- Pita margin yang dilewati margin tidak masuk permukaan dalam. Tepi crown di margin menjadi tugas §5.4.
- Status paten EP2187833B1 (PAT3) belum dicek di register EPO maupun register nasional. Daftar keluarganya belum dicek di Espacenet.

**Pengujian.**
- Lapis 1 (`tests/core/test_spacer.py`, 16 kasus tes):
  - fast marching terhadap silinder yang dibuka (grid teratur dan jitter);
  - graf tidak pernah di bawah eksak (kecuali efek faset) dan lebih buruk dari fast marching;
  - profil gap; parameter dari preset Ivoclar; parameter negatif ditolak;
  - zona gap terhadap jarak meridian analitis (shoulder dan chamfer);
  - spacing radial di dinding zona nol yang jauh dari crease, dan pengecilannya di dekat crease;
  - radial = axial memberi offset sepanjang normal; permukaan dalam tanpa akar;
  - lipatan di die bersih hanya sliver, dan tidak ada lipatan non-sliver pada derau 30 µm;
  - block-out kedua menghapus undercut permukaan dalam (derau 0 dan 30 µm) dengan gerakan hanya tegak lurus sumbu;
  - `milling_axes` dari preset berstatus praktik lab.
- Lapis 1 (`tests/core/test_material_db.py`): `milling_axes` wajib 3, 4, atau 5.
- Lapis 2 (`run_integration.py`):
  - gerbang, pembuatan, dan kedaluwarsa spacer seperti sebelumnya;
  - 5 axis: peta undercut ditulis, tanpa block-out kedua, Show Undercuts jalan;
  - 3 axis (preset diganti di memori): block-out kedua jalan dengan sisa undercut 0; `use_second_block_out=False` mematikannya.

**Modul core/.** `core/geodesic.py` (`distance_from_curve`), `core/spacer.py` (`SpacerParams`, `gap_profile`, `inner_faces`, `smoothed_normals`, `spacer_surface`, `inner_undercut_depth`, `new_undercut_mm`, `second_block_out`), `core/insertion.py` (`block_out_mesh`).

### 5.4 Proposal crown: template + konstruksi berlabuh margin (langkah 1 sampai 3 terimplementasi 2026-10-25)

**Gerbang:** margin terkonfirmasi, block-out dan spacer yang belum kedaluwarsa (`require_current_spacer`), serta nomor gigi FDI yang dipilih di panel. Gigi tetangga dan antagonis opsional: tanpa objek itu, langkah 3 hanya memakai ukuran dari margin, dan panel menyebutnya.

**Status kedaluwarsa** (seperti spacer): `<die> Crown` menyimpan sidik margin, sumbu, versi block-out, versi spacer, nomor FDI, parameter template, dan transformasi plus jumlah vertex objek tetangga dan antagonis. Crown kedaluwarsa begitu salah satunya berubah, dan `require_current_crown()` menjadi gerbang §5.5 sampai §5.7. Tidak ada status draf/terkonfirmasi di §5.4. Usulan untuk ekspor ada di keputusan terbuka K7.

**Cek paten (PAT4, PAT5, §2.1; bukan kesimpulan hukum).**

| Keluarga | Wilayah dan status (Google Patents, 2026-10-25) | Inti klaim independen | Dihindari dengan |
|---|---|---|---|
| Straumann: EP2422741B1, EP2422742B1, US9396291B2, US9286417B2 | EP aktif sampai perkiraan 2030-08-31 / 2031-03-18 (menurut ringkasan masih dibayar di DE, GB, CH; gugur di FR, IE). US aktif sampai 2033-01-01 / 2032-09-23. | Template gigi dideformasi dengan **Laplacian surface deformation**. Handle dan target adalah **titik potong garis** (garis normal, atau garis tegak lurus sumbu di daerah margin) dengan template dan dengan gigi. | Tidak ada deformasi Laplacian dan tidak ada handle/target dari perpotongan garis. Permukaan luar **dibangun** langsung dari kurva margin dan template parametrik dengan korespondensi parameter sudut. |
| Glidewell: US10157330B2, US10248885B2, DE112014001417B4 (WO2014144373 berhenti, tanpa EP) | US aktif sampai 2037-03-10 / 2037-01-01; DE aktif sampai perkiraan 2034-03-15. | Margin line (atau kurva karakteristik) **dikodekan sebagai chain code/string**, lalu **dicari kemiripannya** di arsip kasus atau database restorasi sebelumnya, dan yang mirip diambil sebagai proposal. | Tidak ada arsip kasus dan tidak ada pencarian kemiripan margin. Template berasal dari parameter per jenis gigi FDI (K2), bukan dipilih dari kasus lain. |

- Anggota keluarga Straumann EP2422740B1, EP2468212B1, dan US9330205B2 **sudah dibaca** (K6, PAT4): semua klaim independennya mensyaratkan deformasi Laplacian, jadi tidak bersinggungan dengan konstruksi berlabuh margin. Klaim turunan EP2468212 tentang penskalaan bukal/mesiodistal bergantung pada klaim 1 yang Laplacian.
- Klaim turunan Straumann tentang "potong template di margin, gabungkan dengan permukaan gigi di dalam margin, tambah cement gap" mirip langkah 5 di bawah. Klaim turunan hanya relevan bila klaim independennya terpenuhi, dan itu yang dihindari.
- Pencarian paten lain (misalnya untuk template parametrik yang dibangun dari margin) **tidak dilakukan**. Ini bukan analisis kebebasan beroperasi.

**Metode yang dipilih: konstruksi berlabuh margin** (bukan morphing mesh). Permukaan luar crown adalah permukaan parametrik S(u, v):
- u ∈ [0, 1) = sudut di sekitar sumbu insersi (sudut polar titik margin pada bidang tegak lurus sumbu, dibuat monoton);
- v ∈ [0, 1] = dari tepi atas border (v = 0) ke titik oklusal (v = 1).

Kurva bawah S(u, 0) diturunkan **langsung** dari margin terkonfirmasi lewat border Ivoclar (langkah 4), jadi tepi servikal berimpit dengan margin karena konstruksinya, bukan karena dideformasi. Di atasnya, S dicampur dari kurva itu ke kontur template T(u, v) dengan fungsi campuran Hermite w(v): interpolasi transfinit antara kurva dan permukaan, tanpa sistem persamaan, handle, atau titik potong. Penyesuaian ke tetangga dan antagonis mengubah **parameter global template** (lebar mesiodistal, lebar bukolingual, tinggi oklusal) dengan pencarian skalar, bukan menggeser vertex.

Alasan memilih metode ini:
1. Klaim independen Straumann memerlukan deformasi Laplacian **dan** handle/target dari perpotongan garis. Metode ini tidak memakai keduanya.
2. Klaim Glidewell memerlukan arsip kasus dan pencarian kemiripan margin. Di sini tidak ada.
3. Akurasi tepi servikal tidak bergantung pada konvergensi solver: deviasinya dari margin terkonfirmasi 0 menurut konstruksi, jadi yang diukur tinggal deviasi margin itu sendiri (§5.1).
4. Template parametrik sesuai K2 dan tidak butuh library.
5. Kelemahannya: tidak ada "detail anatomi" yang dipertahankan dari library nyata, karena memang belum ada library (K2). Bentuknya jelas ditandai sintetis.

**Alur dan rancangan per langkah.**

**Langkah 1. Template parametrik per FDI (K2).**
- Jenis dari nomor FDI: insisif (11, 12, 21, 22, 31, 32, 41, 42), kaninus (13, 23, 33, 43), premolar (14, 15, 24, 25, 34, 35, 44, 45), molar (16 sampai 18, 26 sampai 28, 36 sampai 38, 46 sampai 48). Kuadran menentukan arah mesial, dan rahang atas/bawah menentukan arah oklusal relatif terhadap antagonis.
- Kontur aksial: superelips dengan lebar MD dan BL, eksponen bentuk n, dan garis kontur terbesar (height of contour) di fraksi tinggi h_c.
- Permukaan oklusal: insisif/kaninus = tepi insisal (kaninus dengan satu puncak). Premolar dan molar = meja oklusal dengan cusp gaussian di posisi relatif tetap (premolar 2, molar 4) dan fossa sentral.
- Semua parameter bentuk berstatus **desain data uji**. Bukan anatomi: tidak ada sumber yang diverifikasi untuk dimensi gigi per FDI, dan angka buku anatomi tidak boleh ditebak (aturan proyek). Ukuran awal **tidak** diambil dari tabel anatomi, tetapi dari kasus: lebar dari margin dan tetangga, tinggi dari antagonis (langkah 3).
- Metrik sintetis: (a) evaluasi template dengan parameter yang diketahui memberi lebar MD/BL dan tinggi yang tepat (galat numerik < 1 µm); (b) S(u, v) tanpa self-intersection untuk rentang parameter yang diizinkan (uji acak parameter); (c) determinisme: parameter yang sama memberi mesh yang identik.
- Risiko: bentuk tidak anatomis, sehingga kontak dan oklusi hanya bermakna geometris; dan rentang parameter yang menghasilkan permukaan terlipat (misalnya eksponen superelips kecil dengan cusp tinggi).

**Langkah 2. Penempatan awal dari margin dan sumbu insersi.**
- Sumbu template = sumbu insersi §5.2. Pusat = titik berat margin pada bidang tegak lurus sumbu. Arah mesial = arah ke tetangga mesial bila ada; tanpa tetangga, arah sumbu utama elips fit margin yang terdekat ke arah mesial lengkung (dari kuadran FDI; tanpa model lengkung, ini ditandai perlu dicek).
- Lebar awal: MD dan BL = lebar margin sepanjang arah itu, ditambah pelebaran di puncak sepertiga servikal dari sudut emergence (`emergence_angle_deg`, sejak 2026-10-25; sebelumnya tonjolan kontur `contour_bulge_mm`). Tinggi awal = tinggi preparasi di atas margin ditambah ketebalan minimum oklusal material (IVO, `min_thickness_*_mm`).
- Metrik sintetis: sudut sumbu template terhadap sumbu sebenarnya (die tanpa undercut: sama dengan galat §5.2); jarak pusat ke sumbu die sebenarnya; galat arah mesial terhadap arah tetangga yang diketahui.
- Risiko: tanpa tetangga, arah mesial lemah. Preparasi miring membuat sumbu insersi berbeda dari sumbu gigi anatomis; crown dibangun di sumbu insersi, jadi bisa tampak miring.

**Langkah 3. Penyesuaian ke ruang mesiodistal (tetangga) dan tinggi oklusal (antagonis).**
- Jarak bertanda dari S ke mesh tetangga dan antagonis (titik terdekat di permukaan, sama dengan §5.5).
- Lebar MD dicari (bisection satu dimensi) sampai kontak di kedua sisi sama dengan target overlap proksimal (§5.5, 0,025 mm, perlu kalibrasi). Bila ruang tidak simetris, pusat MD digeser dulu (pencarian skalar kedua).
- Tinggi oklusal dicari sampai jarak minimum ke antagonis = jarak oklusal target. Jarak itu **tidak punya default** (K4); lihat keputusan terbuka K8.
- Ketebalan minimum material (IVO) dicek sebagai batas bawah: tinggi tidak boleh turun sampai ketebalan di bawah minimum. Cek lengkapnya di §5.6.
- **Gigi tetangga dan antagonis sintetis** (perluasan `core/synthetic.py`, jawaban benar analitis):
  - **Tetangga:** dua elipsoid (setengah sumbu a, b, c) di sisi mesial dan distal. Pusatnya di garis MD template pada tinggi kontak z_k, sehingga titik terdekat ke crown berada di sumbu MD. Jarak titik ke elipsoid dihitung eksak dengan metode bisection Eberly (bukan dari mesh). Lebar benar: W* = (jarak antar permukaan dalam kedua elipsoid sepanjang sumbu MD di z_k) + 2 × overlap target. Varian: elipsoid diputar (titik kontak keluar dari sumbu; jawaban benar dihitung numerik dengan presisi tinggi dari permukaan analitis) dan ruang asimetris.
  - **Antagonis:** bidang dengan normal −sumbu pada tinggi H, atau bidang miring dengan sudut β yang diketahui. Jawaban benar: tinggi oklusal benar = H − jarak target (bidang datar); untuk bidang miring, dari fungsi tumpu (support function) template yang dievaluasi analitis. Varian: permukaan silinder lengkung dengan jari-jari diketahui.
  - Mesh tetangga dan antagonis ber-jitter dan ber-derau dengan generator yang sama dengan die. Jawaban benar tetap dari bentuk analitis.
- Metrik sintetis: |W − W*| dan |tinggi − tinggi*|; jarak kontak terukur (titik terdekat crown ke elipsoid analitis) dibanding target; jumlah iterasi; kasus tanpa solusi (ruang terlalu sempit untuk ketebalan minimum) harus berakhir dengan **error eksplisit**, bukan crown yang menembus tetangga.
- Risiko: kontak hanya di satu titik (tetangga tidak sejajar); oklusi nyata butuh registrasi gigitan, dan antagonis sintetis tidak mewakilinya; penyesuaian global tidak bisa membentuk kontak lokal yang anatomis (itu tugas §5.5).

**Langkah 4. Border crown di margin (IVO, definisi DTX/EXW).**
- Di setiap titik margin m(u), dengan normal permukaan die n dan arah ke luar horizontal (tegak lurus sumbu) h:
  - border horizontal selebar 0,20 mm dari margin line ke luar;
  - bagian bersudut sepanjang 0,10 mm dengan sudut 65°;
  - lalu kurva S(u, 0) tempat permukaan luar mulai.
  - Bagian dalam border bersambung ke tepi permukaan dalam §5.3. Pita margin yang tidak masuk permukaan dalam diisi strip penghubung (langkah 5).
- Acuan sudut 65° masih interpretasi (S4): diusulkan diukur antara bagian bersudut dan sumbu insersi, dan dicatat sebagai interpretasi.
- Metrik sintetis: di potongan meridian pada 64 sudut, ukur lebar horizontal, panjang bagian bersudut, dan sudutnya terhadap nilai IVO (galat numerik; target < 1 µm dan < 0,1°, karena dibangun langsung). Ukur juga jarak titik awal border ke margin terkonfirmasi (0 menurut konstruksi) dan ke margin analitis (= galat §5.1).
- Risiko: pada scallop dalam, border yang konstan bisa saling memotong di puncak proksimal. Itu harus terdeteksi (langkah 5) dan dilaporkan, bukan disembunyikan.

**Langkah 5. Penyatuan menjadi solid watertight (manifold3d).**
- Komponennya:
  - permukaan dalam §5.3 (orientasi dibalik, karena normalnya menghadap die);
  - strip penghubung dari tepi permukaan dalam ke tepi dalam border (triangulasi zipper dua loop berdasarkan parameter u);
  - border;
  - permukaan luar S(u, v) yang ditutup di titik oklusal.
- Loop tepi dicocokkan dengan parameter u, jadi tidak perlu Boolean. Hasilnya divalidasi dengan `core/solid.py` (manifold3d): watertight, satu komponen, genus 0, volume > 0, tanpa rongga tertutup.
- Metrik sintetis: status manifold3d di semua kasus; jumlah kasus gagal; deviasi permukaan dalam akhir terhadap spacer (harus 0 di luar strip); lebar strip; volume terhadap volume analitis selubung (pemeriksaan kasar); waktu.
- Risiko: tepi permukaan dalam tidak beraturan (pita margin §5.3); strip yang terlipat di scallop dalam; self-intersection antara border dan permukaan luar bila crown lebih sempit dari margin. Semua harus berakhir sebagai error dari validasi manifold3d, bukan solid yang rusak.

**Parameter.**

| Parameter | Status | Nilai | Sumber |
|---|---|---|---|
| Border horizontal | default pabrikan | 0,20 mm | IVO "Horizontal margin thickness" = slider Horizontal (DTX, EXW) |
| Sudut bagian bersudut | default pabrikan | 65° | IVO "Crown margin angle" = slider Angle (DTX, EXW); acuan sudut masih interpretasi (S4) |
| Panjang bagian bersudut | default pabrikan | 0,10 mm | IVO "Angled margin thickness" = slider Angled, "the length of the angled part of the border" (DTX, EXW) |
| Ketebalan minimum (batas bawah tinggi) | default pabrikan | anterior 0,80 mm, premolar dan molar 1,00 mm | IVO "Minimal thickness" (`zircad_prime.json`) |
| Jarak approximal ke tetangga (target, `approximal_distance_mm`) | literatur, perlu kalibrasi | −0,020 mm (overlap 20 µm) | NAG "approximal distance, −20 µm" (setelan desain studi in vitro). Menggantikan 0,025 mm dari RESEARCH.md §3 yang tanpa rujukan. |
| Jarak oklusal ke antagonis (target, `occlusal_distance_mm`) | literatur, perlu kalibrasi | 0 mm | K8: NAG "occlusal distance, 0 µm". Diisi praktik lab nanti. |
| Sudut emergence sepertiga servikal (`emergence_angle_deg`) | literatur, perlu kalibrasi | 19° terhadap sumbu insersi | MON: rata-rata 19° pada simulasi preparasi chamfer (acuan sudut MON belum terbaca). Menggantikan `contour_bulge_mm` (0,5 mm, tanpa sumber). |
| Bagian dinding yang dibangun dari margin (`cervical_fraction`) | keputusan maintainer | 1/3 tinggi dinding | "Sepertiga servikal" (permintaan maintainer 2026-10-25) |
| Tinggi zona campur margin ke template (`blend_height_mm`) | perlu kalibrasi | 1,0 mm | Tidak ada sumber; menggantikan `blend_fraction` (fraksi v) setelah lipatan di set ukur pertama |
| Bentuk template (eksponen superelips, height of contour, posisi dan tinggi cusp, lebar fossa) | desain data uji | per jenis gigi | K2: bukan anatomi |
| Resolusi u, v dan fungsi campuran w | ambang algoritma | 192 sudut × 64 baris v; w = smoothstep dalam tinggi di atas margin | |

**Modul core/** (rencana): `core/template.py` (template parametrik per FDI), `core/crown.py` (penempatan, border, permukaan luar, penyatuan, `assemble_crown`), `core/proximity.py` (jarak bertanda, dipakai juga §5.5), dan perluasan `core/synthetic.py` (tetangga elipsoid, antagonis bidang/silinder, jawaban benar). `core/morph.py` dan deformasi Laplacian **dihapus dari rencana**.

**Pengujian** (rencana): semua metrik di atas sebagai benchmark `scripts/crown_benchmark.py` (set tuning dan set ukur yang dikunci, seperti §5.1 sampai §5.3), ditambah Lapis 1: identitas template, tepi servikal = margin terkonfirmasi, border sesuai IVO di potongan, lebar dan tinggi hasil penyesuaian terhadap jawaban analitis, solid lolos manifold3d, error eksplisit untuk ruang terlalu sempit. Lapis 2: gerbang (spacer kedaluwarsa menolak), kedaluwarsa bila tetangga, antagonis, atau FDI berubah.

**Keputusan maintainer (2026-10-25).**
- **K6:** tiga anggota keluarga Straumann yang tersisa dibaca dulu. Hasilnya tidak ada yang bersinggungan (PAT4).
- **K7:** "Confirm Crown" ada, letaknya sebelum ekspor §5.7, bukan sebelum §5.6. Peta ketebalan dan kontak §5.6 harus bisa dilihat sebelum konfirmasi. Belum diimplementasikan (bagian §5.7).
- **K8:** jarak oklusal ke antagonis default 0 µm, status "literatur, perlu kalibrasi" (NAG). Jarak approximal −20 µm dari sumber yang sama dipakai dengan status yang sama.
- **K9:** tanpa gigi tetangga, arah mesial ditentukan pengguna lewat panah ("<die> Mesial Direction", bola "<die> Mesial Handle" diseret dengan G). FDI hanya petunjuk awal (sumbu elips margin), dan statusnya "needs checking".

**Implementasi langkah 1 sampai 3** (`core/template.py`, `core/crown.py`, `ops/crown.py`, benchmark `scripts/crown_benchmark.py`).
- **Template:** jenis dari FDI; penampang superelips dengan lebar maksimum tepat di height of contour; meja oklusal dengan cusp gaussian dinormalisasi supaya titik tertinggi tepat di tinggi yang diminta. Galat lebar dan tinggi < 1 µm (tes).
- **Permukaan:** S(φ, v) = T(φ, v) + (1 − w(v))·(M(φ) − T(φ, 0)), M = margin terkonfirmasi yang di-resample pada sudut polar yang sama rata (192 sudut). Versi pertama: dasar template rata dan w = smoothstep dalam parameter v (`blend_fraction` 0,5). Sejak perbaikan lipatan: dasar template mengikuti tinggi margin per sudut dan w diukur dalam mm (lihat "Perbaikan lipatan" di bawah). Tepi bawah = margin menurut konstruksi; border (langkah 4) belum ada.
- **Penyesuaian:** tepi mesial, tepi distal, dan tinggi digeser sejauh selisih jarak bertanda terhadap target, sampai semua selisih ≤ 1 µm.
  - Peredam dibagi dua setiap kali tanda selisih berbalik.
  - *Beda dari versi pertama:* langkah penuh berosilasi pada mesh berderau. Penyebab utamanya tanda jarak bertanda dari normal satu face: bila titik terdekat jatuh di edge atau vertex, tandanya bisa salah, dan jarak minimum melompat (lebar berubah 2 µm, jarak berubah dari +83 ke −244 µm). Tanda sekarang dari normal vertex face terdekat.
- **Error eksplisit:** ruang mesiodistal lebih sempit dari lebar margin, atau ruang oklusal di bawah tinggi minimum dari ketebalan IVO (anterior 0,80 mm, premolar/molar 1,00 mm, ditambah cement gap dan relief), berakhir dengan pesan ("mesiodistal space too narrow", "occlusal space too narrow"), bukan crown yang menembus.
- **Gigi tetangga dan antagonis sintetis** (`core/synthetic.py`): `Ellipsoid` (jarak bertanda eksak, bisection Eberly), `AntagonistPlane`, `AntagonistCylinder`.
- **Blender:**
  - langkah **Crown** di panel: nomor FDI, objek tetangga mesial/distal, antagonis, dan tombol **Propose Crown** (gerbang `require_current_spacer`);
  - hasilnya `<die> Crown Proposal`, permukaan luar terbuka;
  - `crown_status` dan `require_current_crown` (gerbang §5.5 sampai §5.7): proposal kedaluwarsa bila margin, sumbu, versi block-out, versi spacer, FDI, arah mesial (termasuk posisi bola mesial tanpa tetangga), atau transformasi/vertex tetangga dan antagonis berubah;
  - Load Synthetic Case punya opsi **Neighbours and Antagonist**.

**Benchmark** (`python scripts/crown_benchmark.py --set <set> --seeds 3`, 2026-10-25).
- Margin analitis dan sumbu sebenarnya. Mesh tetangga dan antagonis ber-jitter dan ber-derau sama dengan die.
- **Jawaban benar:** jarak bertanda eksak dari vertex crown ke elipsoid, bidang, atau silinder analitis. "|galat| kontak" = |jarak eksak − target|.
- Arah mesial dibandingkan dengan sumbu mesial die yang diketahui.
- Lipatan = face yang berbalik dibanding template murni bertopologi sama.
- Set ukur didefinisikan di commit `a9cd683` dan dikunci ulang di `931ae46` (perbaikan ketebalan minimum anterior IVO yang ditemukan sebelum run mana pun), lalu dijalankan sekali.

**Set tuning:**

| Kasus | Finish | Derau | Hasil per seed | |galat| kontak mesial | |galat| kontak distal | |galat| jarak oklusal | Galat arah mesial | Tepi servikal ke margin | Lipatan | Iterasi | Waktu |
|---|---|---|---|---|---|---|---|---|---|---|---|
| molar, tetangga simetris, antagonis datar | shoulder | 0 µm | kurva 3 | 3,9 µm | 3,6 µm | 0,4 µm | 0,00° | 0,000 µm | 0 | 3 | 2,9 s |
| molar, tetangga simetris, antagonis datar | shoulder | 10 µm | kurva 3 | 9,7 µm | 4,3 µm | 10,5 µm | 0,00° | 0,000 µm | 0 | 4 | 3,7 s |
| molar, tetangga simetris, antagonis datar | shoulder | 30 µm | kurva 3 | 32,0 µm | 20,2 µm | 18,0 µm | 0,00° | 0,000 µm | 0 | 4 | 4,0 s |
| molar, tetangga simetris, antagonis datar | chamfer | 0 µm | kurva 3 | 3,9 µm | 3,6 µm | 0,4 µm | 0,00° | 0,000 µm | 0 | 3 | 3,3 s |
| molar, tetangga simetris, antagonis datar | chamfer | 10 µm | kurva 3 | 9,7 µm | 4,3 µm | 10,5 µm | 0,00° | 0,000 µm | 0 | 4 | 3,9 s |
| molar, tetangga simetris, antagonis datar | chamfer | 30 µm | kurva 3 | 32,0 µm | 20,2 µm | 18,0 µm | 0,00° | 0,000 µm | 0 | 4 | 4,5 s |
| molar scallop PL 2, tetangga asimetris | shoulder | 0 µm | kurva 3 | 3,5 µm | 2,9 µm | 0,4 µm | 0,00° | 0,000 µm | 0 | 3 | 3,6 s |
| molar scallop PL 2, tetangga asimetris | shoulder | 10 µm | kurva 3 | 10,9 µm | 5,8 µm | 6,8 µm | 0,00° | 0,000 µm | 0 | 6 | 6,6 s |
| molar scallop PL 2, tetangga asimetris | shoulder | 30 µm | kurva 3 | 37,0 µm | 22,4 µm | 25,0 µm | 0,00° | 0,000 µm | 0 | 7 | 7,5 s |
| molar scallop PL 2, tetangga asimetris | chamfer | 0 µm | kurva 3 | 3,5 µm | 2,9 µm | 0,4 µm | 0,00° | 0,000 µm | 0 | 3 | 3,7 s |
| molar scallop PL 2, tetangga asimetris | chamfer | 10 µm | kurva 3 | 10,9 µm | 5,8 µm | 6,8 µm | 0,00° | 0,000 µm | 0 | 6 | 6,6 s |
| molar scallop PL 2, tetangga asimetris | chamfer | 30 µm | kurva 3 | 37,0 µm | 22,4 µm | 25,0 µm | 0,00° | 0,000 µm | 0 | 7 | 7,6 s |
| molar, antagonis terlalu dekat (error) | shoulder | 0 µm | error 3 | - | - | - | 0,00° | - | - | - | 1,0 s |
| molar, antagonis terlalu dekat (error) | shoulder | 10 µm | error 3 | - | - | - | 0,00° | - | - | - | 1,0 s |
| molar, antagonis terlalu dekat (error) | shoulder | 30 µm | error 3 | - | - | - | 0,00° | - | - | - | 1,1 s |
| molar, antagonis terlalu dekat (error) | chamfer | 0 µm | error 3 | - | - | - | 0,00° | - | - | - | 1,2 s |
| molar, antagonis terlalu dekat (error) | chamfer | 10 µm | error 3 | - | - | - | 0,00° | - | - | - | 1,1 s |
| molar, antagonis terlalu dekat (error) | chamfer | 30 µm | error 3 | - | - | - | 0,00° | - | - | - | 1,1 s |
| molar, tetangga terlalu dekat (error) | shoulder | 0 µm | error 3 | - | - | - | 0,01° | - | - | - | 1,1 s |
| molar, tetangga terlalu dekat (error) | shoulder | 10 µm | error 3 | - | - | - | 0,01° | - | - | - | 1,1 s |
| molar, tetangga terlalu dekat (error) | shoulder | 30 µm | error 3 | - | - | - | 0,01° | - | - | - | 1,2 s |
| molar, tetangga terlalu dekat (error) | chamfer | 0 µm | error 3 | - | - | - | 0,01° | - | - | - | 1,2 s |
| molar, tetangga terlalu dekat (error) | chamfer | 10 µm | error 3 | - | - | - | 0,01° | - | - | - | 1,1 s |
| molar, tetangga terlalu dekat (error) | chamfer | 30 µm | error 3 | - | - | - | 0,01° | - | - | - | 1,2 s |

**Set ukur (dijalankan sekali):**

| Kasus | Finish | Derau | Hasil per seed | |galat| kontak mesial | |galat| kontak distal | |galat| jarak oklusal | Galat arah mesial | Tepi servikal ke margin | Lipatan | Iterasi | Waktu |
|---|---|---|---|---|---|---|---|---|---|---|---|
| premolar kecil, tetangga miring 15 | shoulder | 0 µm | kurva 3 | 5,9 µm | 1,6 µm | 0,0 µm | 0,01° | 0,000 µm | 0 | 4 | 4,4 s |
| premolar kecil, tetangga miring 15 | shoulder | 10 µm | kurva 3 | 8,6 µm | 2,0 µm | 10,0 µm | 0,00° | 0,000 µm | 0 | 4 | 4,2 s |
| premolar kecil, tetangga miring 15 | shoulder | 30 µm | kurva 3 | 22,6 µm | 33,5 µm | 20,6 µm | 0,00° | 0,000 µm | 0 | 5 | 5,1 s |
| premolar kecil, tetangga miring 15 | chamfer | 0 µm | kurva 3 | 5,9 µm | 1,6 µm | 0,0 µm | 0,01° | 0,000 µm | 0 | 4 | 4,2 s |
| premolar kecil, tetangga miring 15 | chamfer | 10 µm | kurva 3 | 8,6 µm | 2,0 µm | 10,0 µm | 0,00° | 0,000 µm | 0 | 4 | 4,4 s |
| premolar kecil, tetangga miring 15 | chamfer | 30 µm | kurva 3 | 22,6 µm | 33,5 µm | 20,6 µm | 0,00° | 0,000 µm | 0 | 5 | 4,8 s |
| molar besar, antagonis silinder | shoulder | 0 µm | kurva 3 | 4,1 µm | 4,1 µm | 0,3 µm | 0,00° | 0,000 µm | 41 | 4 | 4,7 s |
| molar besar, antagonis silinder | shoulder | 10 µm | kurva 3 | 3,5 µm | 1,9 µm | 7,1 µm | 0,00° | 0,000 µm | 47 | 4 | 4,3 s |
| molar besar, antagonis silinder | shoulder | 30 µm | kurva 3 | 25,3 µm | 25,7 µm | 28,3 µm | 0,00° | 0,000 µm | 48 | 4 | 4,3 s |
| molar besar, antagonis silinder | chamfer | 0 µm | kurva 3 | 4,1 µm | 4,1 µm | 0,3 µm | 0,00° | 0,000 µm | 41 | 4 | 4,2 s |
| molar besar, antagonis silinder | chamfer | 10 µm | kurva 3 | 3,5 µm | 1,9 µm | 7,1 µm | 0,00° | 0,000 µm | 47 | 4 | 4,3 s |
| molar besar, antagonis silinder | chamfer | 30 µm | kurva 3 | 25,3 µm | 25,7 µm | 28,3 µm | 0,00° | 0,000 µm | 48 | 4 | 4,4 s |
| insisif sentral, hanya tetangga mesial | shoulder | 0 µm | kurva 3 | 3,6 µm | - | 0,5 µm | 0,01° | 0,000 µm | 303 | 10 | 7,0 s |
| insisif sentral, hanya tetangga mesial | shoulder | 10 µm | kurva 3 | 6,1 µm | - | 8,5 µm | 0,01° | 0,000 µm | 305 | 10 | 7,4 s |
| insisif sentral, hanya tetangga mesial | shoulder | 30 µm | kurva 3 | 23,6 µm | - | 28,8 µm | 0,01° | 0,000 µm | 311 | 10 | 7,0 s |
| insisif sentral, hanya tetangga mesial | chamfer | 0 µm | kurva 3 | 3,6 µm | - | 0,5 µm | 0,01° | 0,000 µm | 303 | 10 | 7,1 s |
| insisif sentral, hanya tetangga mesial | chamfer | 10 µm | kurva 3 | 6,1 µm | - | 8,5 µm | 0,01° | 0,000 µm | 305 | 10 | 6,7 s |
| insisif sentral, hanya tetangga mesial | chamfer | 30 µm | kurva 3 | 23,6 µm | - | 28,8 µm | 0,01° | 0,000 µm | 311 | 10 | 7,0 s |
| kaninus, tanpa tetangga dan antagonis | shoulder | 0 µm | kurva 3 | - | - | - | - (dari pengguna) | 0,000 µm | 100 | 1 | 0,1 s |
| kaninus, tanpa tetangga dan antagonis | shoulder | 10 µm | kurva 3 | - | - | - | - (dari pengguna) | 0,000 µm | 100 | 1 | 0,0 s |
| kaninus, tanpa tetangga dan antagonis | shoulder | 30 µm | kurva 3 | - | - | - | - (dari pengguna) | 0,000 µm | 100 | 1 | 0,0 s |
| kaninus, tanpa tetangga dan antagonis | chamfer | 0 µm | kurva 3 | - | - | - | - (dari pengguna) | 0,000 µm | 100 | 1 | 0,0 s |
| kaninus, tanpa tetangga dan antagonis | chamfer | 10 µm | kurva 3 | - | - | - | - (dari pengguna) | 0,000 µm | 100 | 1 | 0,0 s |
| kaninus, tanpa tetangga dan antagonis | chamfer | 30 µm | kurva 3 | - | - | - | - (dari pengguna) | 0,000 µm | 100 | 1 | 0,0 s |
| premolar, antagonis miring terlalu dekat (error) | shoulder | 0 µm | error 3 | - | - | - | 0,01° | - | - | - | 1,0 s |
| premolar, antagonis miring terlalu dekat (error) | shoulder | 10 µm | error 3 | - | - | - | 0,01° | - | - | - | 1,1 s |
| premolar, antagonis miring terlalu dekat (error) | shoulder | 30 µm | error 3 | - | - | - | 0,00° | - | - | - | 1,1 s |
| premolar, antagonis miring terlalu dekat (error) | chamfer | 0 µm | error 3 | - | - | - | 0,01° | - | - | - | 0,9 s |
| premolar, antagonis miring terlalu dekat (error) | chamfer | 10 µm | error 3 | - | - | - | 0,01° | - | - | - | 0,9 s |
| premolar, antagonis miring terlalu dekat (error) | chamfer | 30 µm | error 3 | - | - | - | 0,00° | - | - | - | 0,9 s |

Kesimpulan:
- **Kontak:**
  - galat jarak eksak ke tetangga ≤ 6 µm tanpa derau, ≤ 11 µm pada derau 10 µm, dan ≤ 37 µm pada derau 30 µm (set tuning ≤ 37, set ukur ≤ 34);
  - galat jarak oklusal ≤ 0,5 µm tanpa derau, ≤ 11 µm pada 10 µm, dan ≤ 29 µm pada 30 µm;
  - galat pada derau tinggi adalah bias derau: jarak minimum diambil pada mesh tetangga yang berderau, sedangkan jawaban benar dari permukaan analitis.
- **Arah mesial dari tetangga:** galat ≤ 0,012° (termasuk tetangga miring 15°).
- **Tepi servikal = margin** (0 µm menurut konstruksi) di semua kasus.
- **Error eksplisit:** semua kasus sempit berakhir dengan pesan, 36 dari 36 di set tuning dan 18 dari 18 di set ukur, dan tidak ada error di kasus yang seharusnya bisa.
- **Gagal: lipatan pada scallop dalam (set ukur).** Molar besar PL 3 mm: 41-48 face; kaninus PL 2,4 mm: 100 face; insisif sentral PL 3,2 mm: 303-311 face. Set tuning (scallop ≤ PL 2 mm) tidak punya lipatan.
  - Diagnosis setelah run (tanpa mengubah kode): lipatan ada di baris v 1-4 di dalam zona campur, pada sudut puncak scallop. Di sana margin 0,85-1,6 mm di atas dasar template (tinggi rata-rata margin), sedangkan zona campur hanya 9-12% dari parameter v. Permukaan dipaksa naik lebih cepat daripada template di atasnya, jadi terlipat.
  - Perbaikan: dasar template mengikuti tinggi margin per sudut, dan zona campur dalam mm. Set ini masuk set tuning. Hasilnya ada di "Perbaikan lipatan" di bawah.
- **Waktu:** 3-8 s per proposal dengan tetangga dan antagonis, ≤ 0,1 s tanpa keduanya.

**Keterbatasan dan yang perlu diuji ulang dengan scan asli:**
- Template sintetis, bukan anatomi (K2).
- Kontak hanya diatur lewat lebar mesiodistal global.
- Antagonis sintetis tidak mewakili oklusi nyata (registrasi gigitan).
- Arah mesial tanpa tetangga sepenuhnya dari pengguna.
- Lipatan pada scallop dalam sudah diperbaiki (set ukur kedua tanpa lipatan non-sliver), tetapi sudut emergence 1 mm pertama masih 16-43° (median per kasus), jauh di atas gigi alami.
- Sudut emergence diukur terhadap sumbu insersi, bukan terhadap permukaan akar seperti DU, dan diukur dari margin, bukan dari border.
- Sejak sudut emergence Monaco: sepertiga servikal tepat 19°, tetapi acuan sudut MON belum dipastikan. Untuk molar belum ada acuan.
- Border (langkah 4) dan solid tertutup (langkah 5) belum ada, jadi proposal belum bisa dicek ketebalannya (§5.6) maupun diekspor.

**Perbaikan lipatan pada scallop dalam (2026-10-25).**
- **Perubahan** (`core/template.py`, `core/crown.py`):
  - dasar template mengikuti tinggi margin per sudut: T(φ, 0) setinggi M(φ), jadi campuran margin hanya menggeser mendatar;
  - zona campur diukur dalam mm: w = smoothstep(h / `blend_height_mm`), h = tinggi titik template di atas margin pada sudut yang sama. Default 1,0 mm, status **perlu kalibrasi** (tabel parameter di atas). Tidak lagi bergantung pada tinggi crown;
  - error eksplisit bila titik margin tertinggi kurang dari `blend_height_mm` di bawah meja oklusal.
- **Lipatan non-sliver:** face yang berbalik dibanding template murni berdasar rata, tanpa segitiga dengan tinggi < 0,01 mm (`SLIVER_MM`, sama dengan §5.3). Kolom "Lipatan" di tabel menulis semua face berbalik, lalu yang non-sliver dalam kurung.
- **Metrik sudut emergence** (dilaporkan, belum ada ambang lulus):
  - sudut tali busur permukaan luar terhadap sumbu insersi dari tepi servikal sampai 1 mm di atasnya, per sudut keliling (192 sudut), positif bila crown melebar ke luar;
  - per kasus: median dan maksimum dari semua sudut keliling dan semua seed;
  - sampai border (langkah 4) ada, tepi servikal adalah margin; sesudahnya diukur dari tepi atas border.
- **Acuan pembanding** (YOT, DU di §2.1):
  - YOT: rata-rata emergence supragingiva gigi anterior alami 11,13 ± 7,92° (fasial) dan 15,58 ± 9,16° (lingual); subgingiva 9,93° dan 14,35°;
  - YOT, pada gigi bercrown: sudut emergence lingual subgingiva berkorelasi dengan kedalaman poket, dan sudut lingual supra- maupun subgingiva berkorelasi dengan attachment loss;
  - DU: 148 gigi anterior rahang atas alami (74 insisif sentral, 59 lateral, 15 kaninus), sudut emergence di CEJ 11,30-15,26°, tanpa beda bermakna antar lokasi;
  - **acuannya berbeda:** DU mengukur "from the root surface", dan abstrak YOT tidak menyebut acuannya. Metrik di sini diukur terhadap sumbu insersi. Jadi angka di bawah tidak bisa dibandingkan langsung.
- **Aturan baru (CLAUDE.md):** setiap set tuning fitur crown dan margin wajib berisi scallop dalam (PL 2,5 dan 3,5 mm) dan die anterior. Untuk crown, aturan ini ditegakkan `test_crown_tuning_set_has_deep_scallops_and_anterior_dies`.
- **Set tuning baru** = set tuning lama + set ukur pertama (`931ae46`) + tiga kasus: lateral atas PL 2,5, insisif bawah PL 3,5, molar PL 3,5.
- **Set ukur kedua:**
  - didefinisikan dan dikunci bersama kode di commit `f633091` sebelum dijalankan, lalu dijalankan sekali;
  - kriteria: nol lipatan non-sliver;
  - isi: lateral atas PL 3,4, kaninus bawah PL 3,0 dengan antagonis silinder, insisif sentral bawah PL 2,6 tanpa antagonis, premolar PL 2,8 dengan tetangga miring 10°, molar PL 3,8 dengan hanya tetangga distal, dan insisif PL 3,2 dengan tetangga terlalu dekat (error).
- **Sensitivitas lebar zona campur** (set tuning saja, derau 0, 1 seed, chamfer):
  - nol lipatan pada 0,5, 1,0, 1,5, dan 2,0 mm;
  - median emergence molar 40,3 / 40,1 / 36,2 / 32,0°, dan maksimum seluruh set 59,4 / 59,4 / 53,8 / 47,2°;
  - default tetap 1,0 mm, karena belum ada ambang emergence untuk memilih nilai lain.

**Set tuning (setelah perbaikan):**

| Kasus | Finish | Derau | Hasil per seed | |galat| kontak mesial | |galat| kontak distal | |galat| jarak oklusal | Galat arah mesial | Tepi servikal ke margin | Lipatan (non-sliver) | Emergence median | Emergence maks | Iterasi | Waktu |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| molar, tetangga simetris, antagonis datar | shoulder | 0 µm | kurva 3 | 3,9 µm | 3,6 µm | 0,4 µm | 0,00° | 0,000 µm | 0 (0) | 40,1° | 46,1° | 3 | 2,6 s |
| molar, tetangga simetris, antagonis datar | shoulder | 10 µm | kurva 3 | 9,7 µm | 4,3 µm | 10,5 µm | 0,00° | 0,000 µm | 0 (0) | 40,0° | 46,1° | 4 | 3,4 s |
| molar, tetangga simetris, antagonis datar | shoulder | 30 µm | kurva 3 | 32,0 µm | 20,2 µm | 18,0 µm | 0,00° | 0,000 µm | 0 (0) | 39,7° | 45,9° | 4 | 4,9 s |
| molar, tetangga simetris, antagonis datar | chamfer | 0 µm | kurva 3 | 3,9 µm | 3,6 µm | 0,4 µm | 0,00° | 0,000 µm | 0 (0) | 40,1° | 46,1° | 3 | 2,6 s |
| molar, tetangga simetris, antagonis datar | chamfer | 10 µm | kurva 3 | 9,7 µm | 4,3 µm | 10,5 µm | 0,00° | 0,000 µm | 0 (0) | 40,0° | 46,1° | 4 | 3,2 s |
| molar, tetangga simetris, antagonis datar | chamfer | 30 µm | kurva 3 | 32,0 µm | 20,2 µm | 18,0 µm | 0,00° | 0,000 µm | 0 (0) | 39,7° | 45,9° | 4 | 3,4 s |
| molar scallop PL 2, tetangga asimetris | shoulder | 0 µm | kurva 3 | 2,7 µm | 2,4 µm | 0,4 µm | 0,00° | 0,000 µm | 0 (0) | 36,8° | 59,4° | 4 | 3,5 s |
| molar scallop PL 2, tetangga asimetris | shoulder | 10 µm | kurva 3 | 11,5 µm | 8,7 µm | 4,3 µm | 0,00° | 0,000 µm | 0 (0) | 36,8° | 59,5° | 6 | 4,8 s |
| molar scallop PL 2, tetangga asimetris | shoulder | 30 µm | kurva 3 | 24,0 µm | 19,2 µm | 19,8 µm | 0,00° | 0,000 µm | 0 (0) | 36,7° | 59,2° | 6 | 5,0 s |
| molar scallop PL 2, tetangga asimetris | chamfer | 0 µm | kurva 3 | 2,7 µm | 2,4 µm | 0,4 µm | 0,00° | 0,000 µm | 0 (0) | 36,8° | 59,4° | 4 | 3,5 s |
| molar scallop PL 2, tetangga asimetris | chamfer | 10 µm | kurva 3 | 11,5 µm | 8,7 µm | 4,3 µm | 0,00° | 0,000 µm | 0 (0) | 36,8° | 59,5° | 6 | 5,2 s |
| molar scallop PL 2, tetangga asimetris | chamfer | 30 µm | kurva 3 | 24,0 µm | 19,2 µm | 19,8 µm | 0,00° | 0,000 µm | 0 (0) | 36,7° | 59,2° | 6 | 5,2 s |
| molar, antagonis terlalu dekat (error) | shoulder | 0 µm | error 3 | - | - | - | 0,00° | - | - | - | - | - | 0,8 s |
| molar, antagonis terlalu dekat (error) | shoulder | 10 µm | error 3 | - | - | - | 0,00° | - | - | - | - | - | 0,9 s |
| molar, antagonis terlalu dekat (error) | shoulder | 30 µm | error 3 | - | - | - | 0,00° | - | - | - | - | - | 0,8 s |
| molar, antagonis terlalu dekat (error) | chamfer | 0 µm | error 3 | - | - | - | 0,00° | - | - | - | - | - | 0,9 s |
| molar, antagonis terlalu dekat (error) | chamfer | 10 µm | error 3 | - | - | - | 0,00° | - | - | - | - | - | 0,9 s |
| molar, antagonis terlalu dekat (error) | chamfer | 30 µm | error 3 | - | - | - | 0,00° | - | - | - | - | - | 0,8 s |
| molar, tetangga terlalu dekat (error) | shoulder | 0 µm | error 3 | - | - | - | 0,01° | - | - | - | - | - | 0,9 s |
| molar, tetangga terlalu dekat (error) | shoulder | 10 µm | error 3 | - | - | - | 0,01° | - | - | - | - | - | 0,9 s |
| molar, tetangga terlalu dekat (error) | shoulder | 30 µm | error 3 | - | - | - | 0,01° | - | - | - | - | - | 0,9 s |
| molar, tetangga terlalu dekat (error) | chamfer | 0 µm | error 3 | - | - | - | 0,01° | - | - | - | - | - | 0,9 s |
| molar, tetangga terlalu dekat (error) | chamfer | 10 µm | error 3 | - | - | - | 0,01° | - | - | - | - | - | 0,8 s |
| molar, tetangga terlalu dekat (error) | chamfer | 30 µm | error 3 | - | - | - | 0,01° | - | - | - | - | - | 0,9 s |
| premolar kecil, tetangga miring 15 | shoulder | 0 µm | kurva 3 | 3,0 µm | 3,6 µm | 0,1 µm | 0,01° | 0,000 µm | 0 (0) | 35,1° | 50,0° | 4 | 3,4 s |
| premolar kecil, tetangga miring 15 | shoulder | 10 µm | kurva 3 | 9,5 µm | 12,7 µm | 9,6 µm | 0,00° | 0,000 µm | 0 (0) | 35,1° | 50,1° | 4 | 3,2 s |
| premolar kecil, tetangga miring 15 | shoulder | 30 µm | kurva 3 | 29,0 µm | 56,6 µm | 22,1 µm | 0,00° | 0,000 µm | 0 (0) | 34,8° | 49,6° | 4 | 3,2 s |
| premolar kecil, tetangga miring 15 | chamfer | 0 µm | kurva 3 | 3,0 µm | 3,6 µm | 0,1 µm | 0,01° | 0,000 µm | 0 (0) | 35,1° | 50,0° | 4 | 3,3 s |
| premolar kecil, tetangga miring 15 | chamfer | 10 µm | kurva 3 | 9,5 µm | 12,7 µm | 9,6 µm | 0,00° | 0,000 µm | 0 (0) | 35,1° | 50,1° | 4 | 3,3 s |
| premolar kecil, tetangga miring 15 | chamfer | 30 µm | kurva 3 | 29,0 µm | 56,6 µm | 22,1 µm | 0,00° | 0,000 µm | 0 (0) | 34,8° | 49,6° | 4 | 3,2 s |
| molar besar, antagonis silinder | shoulder | 0 µm | kurva 3 | 2,3 µm | 2,8 µm | 0,3 µm | 0,00° | 0,000 µm | 0 (0) | 40,3° | 46,8° | 4 | 3,7 s |
| molar besar, antagonis silinder | shoulder | 10 µm | kurva 3 | 7,1 µm | 6,7 µm | 10,1 µm | 0,00° | 0,000 µm | 0 (0) | 40,3° | 46,9° | 5 | 4,3 s |
| molar besar, antagonis silinder | shoulder | 30 µm | kurva 3 | 28,6 µm | 23,4 µm | 38,0 µm | 0,00° | 0,000 µm | 0 (0) | 39,7° | 47,0° | 5 | 4,6 s |
| molar besar, antagonis silinder | chamfer | 0 µm | kurva 3 | 2,3 µm | 2,8 µm | 0,3 µm | 0,00° | 0,000 µm | 0 (0) | 40,3° | 46,8° | 4 | 5,1 s |
| molar besar, antagonis silinder | chamfer | 10 µm | kurva 3 | 7,1 µm | 6,7 µm | 10,1 µm | 0,00° | 0,000 µm | 0 (0) | 40,3° | 46,9° | 5 | 4,2 s |
| molar besar, antagonis silinder | chamfer | 30 µm | kurva 3 | 28,6 µm | 23,4 µm | 38,0 µm | 0,00° | 0,000 µm | 0 (0) | 39,7° | 47,0° | 5 | 4,5 s |
| insisif sentral, hanya tetangga mesial | shoulder | 0 µm | kurva 3 | 3,0 µm | - | 0,6 µm | 0,01° | 0,000 µm | 0 (0) | 17,6° | 50,0° | 10 | 5,7 s |
| insisif sentral, hanya tetangga mesial | shoulder | 10 µm | kurva 3 | 7,0 µm | - | 7,6 µm | 0,01° | 0,000 µm | 0 (0) | 17,6° | 50,1° | 10 | 5,7 s |
| insisif sentral, hanya tetangga mesial | shoulder | 30 µm | kurva 3 | 24,3 µm | - | 26,1 µm | 0,01° | 0,000 µm | 0 (0) | 17,6° | 49,9° | 10 | 6,0 s |
| insisif sentral, hanya tetangga mesial | chamfer | 0 µm | kurva 3 | 3,0 µm | - | 0,6 µm | 0,01° | 0,000 µm | 0 (0) | 17,6° | 50,0° | 10 | 5,8 s |
| insisif sentral, hanya tetangga mesial | chamfer | 10 µm | kurva 3 | 7,0 µm | - | 7,6 µm | 0,01° | 0,000 µm | 0 (0) | 17,6° | 50,1° | 10 | 5,5 s |
| insisif sentral, hanya tetangga mesial | chamfer | 30 µm | kurva 3 | 24,3 µm | - | 26,1 µm | 0,01° | 0,000 µm | 0 (0) | 17,6° | 49,9° | 10 | 6,0 s |
| kaninus, tanpa tetangga dan antagonis | shoulder | 0 µm | kurva 3 | - | - | - | - (dari pengguna) | 0,000 µm | 0 (0) | 16,3° | 18,5° | 1 | 0,2 s |
| kaninus, tanpa tetangga dan antagonis | shoulder | 10 µm | kurva 3 | - | - | - | - (dari pengguna) | 0,000 µm | 0 (0) | 16,3° | 18,5° | 1 | 0,0 s |
| kaninus, tanpa tetangga dan antagonis | shoulder | 30 µm | kurva 3 | - | - | - | - (dari pengguna) | 0,000 µm | 0 (0) | 16,3° | 18,5° | 1 | 0,0 s |
| kaninus, tanpa tetangga dan antagonis | chamfer | 0 µm | kurva 3 | - | - | - | - (dari pengguna) | 0,000 µm | 0 (0) | 16,3° | 18,5° | 1 | 0,0 s |
| kaninus, tanpa tetangga dan antagonis | chamfer | 10 µm | kurva 3 | - | - | - | - (dari pengguna) | 0,000 µm | 0 (0) | 16,3° | 18,5° | 1 | 0,0 s |
| kaninus, tanpa tetangga dan antagonis | chamfer | 30 µm | kurva 3 | - | - | - | - (dari pengguna) | 0,000 µm | 0 (0) | 16,3° | 18,5° | 1 | 0,0 s |
| premolar, antagonis miring terlalu dekat (error) | shoulder | 0 µm | error 3 | - | - | - | 0,01° | - | - | - | - | - | 1,2 s |
| premolar, antagonis miring terlalu dekat (error) | shoulder | 10 µm | error 3 | - | - | - | 0,01° | - | - | - | - | - | 1,1 s |
| premolar, antagonis miring terlalu dekat (error) | shoulder | 30 µm | error 3 | - | - | - | 0,00° | - | - | - | - | - | 1,3 s |
| premolar, antagonis miring terlalu dekat (error) | chamfer | 0 µm | error 3 | - | - | - | 0,01° | - | - | - | - | - | 1,2 s |
| premolar, antagonis miring terlalu dekat (error) | chamfer | 10 µm | error 3 | - | - | - | 0,01° | - | - | - | - | - | 1,1 s |
| premolar, antagonis miring terlalu dekat (error) | chamfer | 30 µm | error 3 | - | - | - | 0,00° | - | - | - | - | - | 1,1 s |
| lateral atas PL 2,5, tetangga dua sisi | shoulder | 0 µm | kurva 3 | 3,0 µm | 4,5 µm | 0,6 µm | 0,01° | 0,000 µm | 0 (0) | 31,9° | 44,0° | 9 | 10,4 s |
| lateral atas PL 2,5, tetangga dua sisi | shoulder | 10 µm | kurva 3 | 11,1 µm | 11,0 µm | 14,2 µm | 0,01° | 0,000 µm | 0 (0) | 32,0° | 44,2° | 9 | 10,2 s |
| lateral atas PL 2,5, tetangga dua sisi | shoulder | 30 µm | kurva 3 | 24,3 µm | 23,5 µm | 41,6 µm | 0,01° | 0,000 µm | 0 (0) | 31,8° | 44,3° | 9 | 10,3 s |
| lateral atas PL 2,5, tetangga dua sisi | chamfer | 0 µm | kurva 3 | 3,0 µm | 4,5 µm | 0,6 µm | 0,01° | 0,000 µm | 0 (0) | 31,9° | 44,0° | 9 | 10,4 s |
| lateral atas PL 2,5, tetangga dua sisi | chamfer | 10 µm | kurva 3 | 11,1 µm | 11,0 µm | 14,2 µm | 0,01° | 0,000 µm | 0 (0) | 32,0° | 44,2° | 9 | 10,4 s |
| lateral atas PL 2,5, tetangga dua sisi | chamfer | 30 µm | kurva 3 | 24,3 µm | 23,5 µm | 41,6 µm | 0,01° | 0,000 µm | 0 (0) | 31,8° | 44,3° | 9 | 10,2 s |
| insisif bawah PL 3,5, antagonis miring | shoulder | 0 µm | kurva 3 | 3,9 µm | 2,7 µm | 0,5 µm | 0,01° | 0,000 µm | 0 (0) | 34,8° | 45,2° | 9 | 10,4 s |
| insisif bawah PL 3,5, antagonis miring | shoulder | 10 µm | kurva 3 | 11,8 µm | 10,6 µm | 17,3 µm | 0,01° | 0,000 µm | 0 (0) | 34,8° | 45,4° | 9 | 10,4 s |
| insisif bawah PL 3,5, antagonis miring | shoulder | 30 µm | kurva 3 | 48,1 µm | 23,9 µm | 54,8 µm | 0,01° | 0,000 µm | 0 (0) | 34,5° | 45,6° | 9 | 10,5 s |
| insisif bawah PL 3,5, antagonis miring | chamfer | 0 µm | kurva 3 | 3,9 µm | 2,7 µm | 0,5 µm | 0,01° | 0,000 µm | 0 (0) | 34,8° | 45,2° | 9 | 10,2 s |
| insisif bawah PL 3,5, antagonis miring | chamfer | 10 µm | kurva 3 | 11,8 µm | 10,6 µm | 17,3 µm | 0,01° | 0,000 µm | 0 (0) | 34,8° | 45,4° | 9 | 10,3 s |
| insisif bawah PL 3,5, antagonis miring | chamfer | 30 µm | kurva 3 | 48,1 µm | 23,9 µm | 54,8 µm | 0,01° | 0,000 µm | 0 (0) | 34,5° | 45,6° | 9 | 10,2 s |
| molar PL 3,5, antagonis datar | shoulder | 0 µm | kurva 3 | 2,9 µm | 2,5 µm | 0,4 µm | 0,00° | 0,000 µm | 0 (0) | 42,7° | 51,5° | 4 | 4,9 s |
| molar PL 3,5, antagonis datar | shoulder | 10 µm | kurva 3 | 7,0 µm | 9,8 µm | 16,3 µm | 0,00° | 0,000 µm | 0 (0) | 42,7° | 51,6° | 6 | 6,9 s |
| molar PL 3,5, antagonis datar | shoulder | 30 µm | kurva 3 | 45,9 µm | 35,1 µm | 9,1 µm | 0,00° | 0,000 µm | 0 (0) | 42,5° | 51,8° | 6 | 7,5 s |
| molar PL 3,5, antagonis datar | chamfer | 0 µm | kurva 3 | 2,9 µm | 2,5 µm | 0,4 µm | 0,00° | 0,000 µm | 0 (0) | 42,7° | 51,5° | 4 | 5,0 s |
| molar PL 3,5, antagonis datar | chamfer | 10 µm | kurva 3 | 7,0 µm | 9,8 µm | 16,3 µm | 0,00° | 0,000 µm | 0 (0) | 42,7° | 51,6° | 6 | 6,8 s |
| molar PL 3,5, antagonis datar | chamfer | 30 µm | kurva 3 | 45,9 µm | 35,1 µm | 9,1 µm | 0,00° | 0,000 µm | 0 (0) | 42,5° | 51,8° | 6 | 7,4 s |

**Set ukur kedua (dijalankan sekali, `f633091`):**

| Kasus | Finish | Derau | Hasil per seed | |galat| kontak mesial | |galat| kontak distal | |galat| jarak oklusal | Galat arah mesial | Tepi servikal ke margin | Lipatan (non-sliver) | Emergence median | Emergence maks | Iterasi | Waktu |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| lateral atas PL 3,4, antagonis miring 15 | shoulder | 0 µm | kurva 3 | 4,8 µm | 3,4 µm | 0,9 µm | 0,01° | 0,000 µm | 0 (0) | 33,3° | 51,5° | 9 | 10,3 s |
| lateral atas PL 3,4, antagonis miring 15 | shoulder | 10 µm | kurva 3 | 3,5 µm | 12,4 µm | 16,3 µm | 0,01° | 0,000 µm | 0 (0) | 33,2° | 51,7° | 9 | 10,3 s |
| lateral atas PL 3,4, antagonis miring 15 | shoulder | 30 µm | kurva 3 | 19,2 µm | 23,4 µm | 36,6 µm | 0,01° | 0,000 µm | 0 (0) | 33,1° | 51,8° | 10 | 10,9 s |
| lateral atas PL 3,4, antagonis miring 15 | chamfer | 0 µm | kurva 3 | 4,8 µm | 3,4 µm | 0,9 µm | 0,01° | 0,000 µm | 0 (0) | 33,3° | 51,5° | 9 | 10,5 s |
| lateral atas PL 3,4, antagonis miring 15 | chamfer | 10 µm | kurva 3 | 3,5 µm | 12,4 µm | 16,3 µm | 0,01° | 0,000 µm | 0 (0) | 33,2° | 51,7° | 9 | 10,3 s |
| lateral atas PL 3,4, antagonis miring 15 | chamfer | 30 µm | kurva 3 | 19,2 µm | 23,4 µm | 36,6 µm | 0,01° | 0,000 µm | 0 (0) | 33,1° | 51,8° | 10 | 10,7 s |
| kaninus bawah PL 3,0, antagonis silinder | shoulder | 0 µm | kurva 3 | 2,7 µm | 3,8 µm | 0,2 µm | 0,01° | 0,000 µm | 0 (0) | 32,4° | 45,2° | 4 | 4,9 s |
| kaninus bawah PL 3,0, antagonis silinder | shoulder | 10 µm | kurva 3 | 10,8 µm | 10,5 µm | 20,8 µm | 0,01° | 0,000 µm | 0 (0) | 32,3° | 45,4° | 5 | 5,9 s |
| kaninus bawah PL 3,0, antagonis silinder | shoulder | 30 µm | kurva 3 | 24,7 µm | 21,9 µm | 64,5 µm | 0,00° | 0,000 µm | 0 (0) | 32,3° | 45,0° | 6 | 7,1 s |
| kaninus bawah PL 3,0, antagonis silinder | chamfer | 0 µm | kurva 3 | 2,7 µm | 3,8 µm | 0,2 µm | 0,01° | 0,000 µm | 0 (0) | 32,4° | 45,2° | 4 | 5,0 s |
| kaninus bawah PL 3,0, antagonis silinder | chamfer | 10 µm | kurva 3 | 10,8 µm | 10,5 µm | 20,8 µm | 0,01° | 0,000 µm | 0 (0) | 32,3° | 45,4° | 5 | 5,9 s |
| kaninus bawah PL 3,0, antagonis silinder | chamfer | 30 µm | kurva 3 | 24,7 µm | 21,9 µm | 64,5 µm | 0,00° | 0,000 µm | 0 (0) | 32,3° | 45,0° | 6 | 7,1 s |
| insisif sentral bawah PL 2,6, tanpa antagonis | shoulder | 0 µm | kurva 3 | 2,8 µm | 3,3 µm | - | 0,01° | 0,000 µm | 0 (0) | 35,8° | 43,3° | 4 | 2,8 s |
| insisif sentral bawah PL 2,6, tanpa antagonis | shoulder | 10 µm | kurva 3 | 10,6 µm | 9,2 µm | - | 0,01° | 0,000 µm | 0 (0) | 35,9° | 43,5° | 3 | 2,2 s |
| insisif sentral bawah PL 2,6, tanpa antagonis | shoulder | 30 µm | kurva 3 | 24,5 µm | 23,6 µm | - | 0,01° | 0,000 µm | 0 (0) | 35,7° | 43,6° | 4 | 3,0 s |
| insisif sentral bawah PL 2,6, tanpa antagonis | chamfer | 0 µm | kurva 3 | 2,8 µm | 3,3 µm | - | 0,01° | 0,000 µm | 0 (0) | 35,8° | 43,3° | 4 | 2,8 s |
| insisif sentral bawah PL 2,6, tanpa antagonis | chamfer | 10 µm | kurva 3 | 10,6 µm | 9,2 µm | - | 0,01° | 0,000 µm | 0 (0) | 35,9° | 43,5° | 3 | 2,2 s |
| insisif sentral bawah PL 2,6, tanpa antagonis | chamfer | 30 µm | kurva 3 | 24,5 µm | 23,6 µm | - | 0,01° | 0,000 µm | 0 (0) | 35,7° | 43,6° | 4 | 2,9 s |
| premolar PL 2,8, tetangga miring 10 | shoulder | 0 µm | kurva 3 | 4,9 µm | 4,2 µm | 0,1 µm | 0,01° | 0,000 µm | 0 (0) | 35,7° | 47,5° | 4 | 4,5 s |
| premolar PL 2,8, tetangga miring 10 | shoulder | 10 µm | kurva 3 | 8,8 µm | 17,0 µm | 10,6 µm | 0,00° | 0,000 µm | 0 (0) | 35,7° | 47,8° | 4 | 4,5 s |
| premolar PL 2,8, tetangga miring 10 | shoulder | 30 µm | kurva 3 | 28,1 µm | 24,4 µm | 23,8 µm | 0,00° | 0,000 µm | 0 (0) | 35,4° | 47,7° | 6 | 6,9 s |
| premolar PL 2,8, tetangga miring 10 | chamfer | 0 µm | kurva 3 | 4,9 µm | 4,2 µm | 0,1 µm | 0,01° | 0,000 µm | 0 (0) | 35,7° | 47,5° | 4 | 4,5 s |
| premolar PL 2,8, tetangga miring 10 | chamfer | 10 µm | kurva 3 | 8,8 µm | 17,0 µm | 10,6 µm | 0,00° | 0,000 µm | 0 (0) | 35,7° | 47,8° | 4 | 4,6 s |
| premolar PL 2,8, tetangga miring 10 | chamfer | 30 µm | kurva 3 | 28,1 µm | 24,4 µm | 23,8 µm | 0,00° | 0,000 µm | 0 (0) | 35,4° | 47,7° | 6 | 7,0 s |
| molar PL 3,8, hanya tetangga distal | shoulder | 0 µm | kurva 3 | - | 2,2 µm | 0,2 µm | 0,01° | 0,000 µm | 0 (0) | 23,1° | 52,1° | 4 | 3,6 s |
| molar PL 3,8, hanya tetangga distal | shoulder | 10 µm | kurva 3 | - | 9,3 µm | 18,2 µm | 0,01° | 0,000 µm | 0 (0) | 23,1° | 52,2° | 6 | 5,1 s |
| molar PL 3,8, hanya tetangga distal | shoulder | 30 µm | kurva 3 | - | 33,9 µm | 52,9 µm | 0,01° | 0,000 µm | 0 (0) | 23,1° | 51,7° | 7 | 5,7 s |
| molar PL 3,8, hanya tetangga distal | chamfer | 0 µm | kurva 3 | - | 2,2 µm | 0,2 µm | 0,01° | 0,000 µm | 0 (0) | 23,1° | 52,1° | 4 | 3,5 s |
| molar PL 3,8, hanya tetangga distal | chamfer | 10 µm | kurva 3 | - | 9,3 µm | 18,2 µm | 0,01° | 0,000 µm | 0 (0) | 23,1° | 52,2° | 6 | 5,0 s |
| molar PL 3,8, hanya tetangga distal | chamfer | 30 µm | kurva 3 | - | 33,9 µm | 52,9 µm | 0,01° | 0,000 µm | 0 (0) | 23,1° | 51,7° | 7 | 5,5 s |
| insisif PL 3,2, tetangga terlalu dekat (error) | shoulder | 0 µm | error 3 | - | - | - | 0,01° | - | - | - | - | - | 1,2 s |
| insisif PL 3,2, tetangga terlalu dekat (error) | shoulder | 10 µm | error 3 | - | - | - | 0,01° | - | - | - | - | - | 1,2 s |
| insisif PL 3,2, tetangga terlalu dekat (error) | shoulder | 30 µm | error 3 | - | - | - | 0,01° | - | - | - | - | - | 1,2 s |
| insisif PL 3,2, tetangga terlalu dekat (error) | chamfer | 0 µm | error 3 | - | - | - | 0,01° | - | - | - | - | - | 1,2 s |
| insisif PL 3,2, tetangga terlalu dekat (error) | chamfer | 10 µm | error 3 | - | - | - | 0,01° | - | - | - | - | - | 1,2 s |
| insisif PL 3,2, tetangga terlalu dekat (error) | chamfer | 30 µm | error 3 | - | - | - | 0,01° | - | - | - | - | - | 1,2 s |

Kesimpulan perbaikan:
- **Lipatan: lulus.**
  - Set ukur kedua: 0 lipatan non-sliver di 90 kurva (dan 0 face berbalik sama sekali). Ini termasuk anterior dengan scallop dalam (lateral PL 3,4, kaninus PL 3,0, insisif PL 2,6) dan molar PL 3,8.
  - Set tuning: 0 dari 162, termasuk tiga kasus set ukur pertama yang dulu terlipat (41-311 face).
- **Sudut emergence** (terhadap sumbu insersi, 1 mm pertama di atas margin):
  - median per kasus 16-43° (tuning) dan 23-36° (ukur); maksimum 59,5° (tuning) dan 52,2° (ukur); tidak ada yang negatif;
  - jauh di atas 11-15° dari YOT dan DU, walaupun acuannya berbeda;
  - lebar zona campur hanya sedikit mengubahnya (sensitivitas di atas). Yang menentukan adalah bentuk dinding template (lebar servikal 80-88% dari lebar maksimum, height of contour di 30-40% dinding) dan `contour_bulge_mm` 0,5 mm. Keduanya desain data uji atau perlu kalibrasi, tanpa sumber;
  - jadi profil emergence proposal saat ini **terlalu cembung** dibanding gigi alami. Ini dicatat dan tidak diperbaiki di sini, karena belum ada ambang lulus. Diperbaiki sesudahnya dengan sudut emergence Monaco (bagian berikut).
- **Kontak** (galat jarak eksak):
  - tanpa derau ≤ 4,9 µm ke tetangga dan ≤ 0,9 µm ke antagonis (ukur);
  - pada derau 10 µm ≤ 17 µm dan ≤ 21 µm;
  - pada derau 30 µm ≤ 34 µm dan ≤ 65 µm (ukur). Di set tuning sampai 57 µm dan 55 µm, lebih besar daripada sebelum perbaikan (≤ 37 µm dan ≤ 29 µm). Bentuk dinding yang berubah memindahkan titik kontak, dan bias derau mesh tetangga atau antagonis bergantung pada titik itu. Tanpa derau, galatnya tetap kecil.
- **Lainnya:**
  - arah mesial ≤ 0,012°; tepi servikal = margin (0 µm);
  - error eksplisit 54 dari 54 (tuning) dan 18 dari 18 (ukur), tanpa error di kasus yang seharusnya bisa;
  - waktu ≤ 11 s per proposal (insisif dan lateral sampai 9-10 iterasi).

**Sudut emergence dari Monaco: sepertiga servikal dibangun dari margin (2026-10-25).**
- **Perubahan** (`core/crown.py`, preset `zircad_prime.json`):
  - `contour_bulge_mm` dihapus. Penggantinya `emergence_angle_deg` = 19°, status **literatur, perlu kalibrasi** (MON), disimpan di preset material sehingga muncul di peringatan "belum dikalibrasi";
  - sepertiga servikal dinding (`cervical_fraction` 1/3, keputusan maintainer; tinggi dinding = margin ke tepi meja oklusal pada sudut yang sama) dibangun dari margin: C = M + h·(tan α·n + z), n = normal mendatar kurva margin ke luar;
  - di atasnya dicampur ke template dengan smoothstep sejauh `blend_height_mm` (1,0 mm). C dan template sama tinggi, jadi campuran tetap hanya menggeser mendatar, dan tepi servikal tetap = margin menurut konstruksi;
  - lebar awal template = lebar margin + 2 × pelebaran di puncak sepertiga servikal, supaya template menyambung tanpa undakan;
  - error eksplisit bila dinding di atas sepertiga servikal lebih pendek dari `blend_height_mm`;
  - metrik emergence sekarang memproyeksikan ke normal kurva tepi servikal, bukan ke arah radial dari sumbu seperti versi sebelumnya. Pada margin lingkaran keduanya sama.
- **Kriteria baru set ukur:** median sudut emergence per kasus ≤ 21° untuk anterior dan premolar, dengan median per seed yang terburuk. Molar hanya dilaporkan.
  - Batas 21° adalah rentang yang diminta maintainer. Abstrak MON hanya memuat rata-rata 13° dan 19°, tanpa rentang dan tanpa daftar jenis gigi. Jadi angka 21° dan "molar tidak termasuk" belum terverifikasi dari sumber primer.
- **Catatan:** kriteria ini hampir terpenuhi menurut konstruksi. Di mana sepertiga servikal ≥ 1 mm, 1 mm pertama memang dibangun dengan α. Yang diuji benchmark adalah bahwa konstruksi itu bertahan di semua kasus: scallop dalam memperpendek dinding di puncak proksimal, ada iterasi lebar dan tinggi, dan ada derau. Apakah 19° terhadap sumbu insersi sama dengan 19° di MON belum bisa dipastikan (acuan sudut MON tidak terbaca).
- **Batas waktu benchmark** (`scripts/bench_runner.py`, keempat skrip benchmark):
  - setiap kasus jalan di proses pekerja dengan `--timeout` (default 300 s). Kasus yang melewati batas dicatat sebagai error "timeout", pekerja diganti, dan benchmark lanjut;
  - log progres per kasus ke stderr (`[n/total] kasus | finish | derau | seed: hasil (waktu)`);
  - waktu start pekerja tidak dihitung ke batas waktu;
  - Lapis 1: `tests/core/test_bench_runner.py`.
- **Penyebab "macet" sebelumnya:**
  - run tuning pertama perbaikan lipatan berjalan 07:47 sampai 10:15 tanpa output. Log sistem Windows mencatat laptop bangun dari tidur pada 10:15;
  - di set ukur ketiga, satu run (kaninus atas, chamfer, 10 µm, seed 0) tercatat 28908 s. Laptop tidur dari 12:37 sampai 20:38 (event Kernel-Power 42 dan 507), tepat selama run itu;
  - hasil run itu normal ("kurva"; seed lain 7-10 s), hanya waktunya yang tidak valid. Batas waktu tidak memicu selama laptop tidur, dan waktu tidur ikut terhitung di `perf_counter`;
  - jadi "macet" itu kemungkinan besar tidur, bukan kode. Untuk run panjang berikutnya, laptop sebaiknya dijaga tetap menyala.
- **Set tuning** = set tuning sebelumnya + set ukur kedua (`f633091`).
- **Set ukur ketiga:**
  - didefinisikan dan dikunci bersama kode di commit `76aed0e` sebelum dijalankan, lalu dijalankan sekali;
  - isi: kaninus atas PL 2,6 dengan antagonis miring 10°, lateral bawah PL 3,0 tanpa tetangga, insisif sentral atas PL 3,6 dengan tetangga asimetris, premolar atas PL 2,2 dengan antagonis silinder, premolar bawah PL 3,0 dengan hanya tetangga mesial, molar atas PL 3,2 dengan antagonis miring 6°, dan premolar PL 2,4 dengan antagonis terlalu dekat (error).

**Set tuning (sepertiga servikal 19°):**

| Kasus | Finish | Derau | Hasil per seed | |galat| kontak mesial | |galat| kontak distal | |galat| jarak oklusal | Galat arah mesial | Tepi servikal ke margin | Lipatan (non-sliver) | Emergence median | Emergence maks | Median ≤ 21° | Iterasi | Waktu |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| molar, tetangga simetris, antagonis datar | shoulder | 0 µm | kurva 3 | 4,3 µm | 4,6 µm | 0,4 µm | 0,00° | 0,000 µm | 0 (0) | 19,0° | 19,0° | - (molar, dilaporkan) | 7 | 9,8 s |
| molar, tetangga simetris, antagonis datar | shoulder | 10 µm | kurva 3 | 3,3 µm | 10,3 µm | 7,0 µm | 0,00° | 0,000 µm | 0 (0) | 19,0° | 19,0° | - (molar, dilaporkan) | 7 | 9,2 s |
| molar, tetangga simetris, antagonis datar | shoulder | 30 µm | kurva 3 | 12,1 µm | 30,3 µm | 29,3 µm | 0,00° | 0,000 µm | 0 (0) | 19,0° | 19,0° | - (molar, dilaporkan) | 9 | 10,9 s |
| molar, tetangga simetris, antagonis datar | chamfer | 0 µm | kurva 3 | 4,3 µm | 4,6 µm | 0,4 µm | 0,00° | 0,000 µm | 0 (0) | 19,0° | 19,0° | - (molar, dilaporkan) | 7 | 9,2 s |
| molar, tetangga simetris, antagonis datar | chamfer | 10 µm | kurva 3 | 3,3 µm | 10,3 µm | 7,0 µm | 0,00° | 0,000 µm | 0 (0) | 19,0° | 19,0° | - (molar, dilaporkan) | 7 | 9,1 s |
| molar, tetangga simetris, antagonis datar | chamfer | 30 µm | kurva 3 | 12,1 µm | 30,3 µm | 29,3 µm | 0,00° | 0,000 µm | 0 (0) | 19,0° | 19,0° | - (molar, dilaporkan) | 9 | 9,9 s |
| molar scallop PL 2, tetangga asimetris | shoulder | 0 µm | kurva 3 | 1,6 µm | 1,8 µm | 0,5 µm | 0,00° | 0,000 µm | 0 (0) | 19,0° | 19,0° | - (molar, dilaporkan) | 9 | 10,7 s |
| molar scallop PL 2, tetangga asimetris | shoulder | 10 µm | kurva 3 | 8,3 µm | 10,4 µm | 2,4 µm | 0,00° | 0,000 µm | 0 (0) | 19,0° | 19,0° | - (molar, dilaporkan) | 9 | 10,8 s |
| molar scallop PL 2, tetangga asimetris | shoulder | 30 µm | kurva 3 | 7,6 µm | 34,4 µm | 5,4 µm | 0,00° | 0,000 µm | 0 (0) | 19,0° | 19,0° | - (molar, dilaporkan) | 11 | 13,0 s |
| molar scallop PL 2, tetangga asimetris | chamfer | 0 µm | kurva 3 | 1,6 µm | 1,8 µm | 0,5 µm | 0,00° | 0,000 µm | 0 (0) | 19,0° | 19,0° | - (molar, dilaporkan) | 9 | 10,9 s |
| molar scallop PL 2, tetangga asimetris | chamfer | 10 µm | kurva 3 | 8,3 µm | 10,4 µm | 2,4 µm | 0,00° | 0,000 µm | 0 (0) | 19,0° | 19,0° | - (molar, dilaporkan) | 9 | 10,7 s |
| molar scallop PL 2, tetangga asimetris | chamfer | 30 µm | kurva 3 | 7,6 µm | 34,4 µm | 5,4 µm | 0,00° | 0,000 µm | 0 (0) | 19,0° | 19,0° | - (molar, dilaporkan) | 11 | 13,1 s |
| molar, antagonis terlalu dekat (error) | shoulder | 0 µm | error 3 | - | - | - | 0,00° | - | - | - | - | - | - | 1,2 s |
| molar, antagonis terlalu dekat (error) | shoulder | 10 µm | error 3 | - | - | - | 0,00° | - | - | - | - | - | - | 1,2 s |
| molar, antagonis terlalu dekat (error) | shoulder | 30 µm | error 3 | - | - | - | 0,00° | - | - | - | - | - | - | 1,2 s |
| molar, antagonis terlalu dekat (error) | chamfer | 0 µm | error 3 | - | - | - | 0,00° | - | - | - | - | - | - | 1,2 s |
| molar, antagonis terlalu dekat (error) | chamfer | 10 µm | error 3 | - | - | - | 0,00° | - | - | - | - | - | - | 1,2 s |
| molar, antagonis terlalu dekat (error) | chamfer | 30 µm | error 3 | - | - | - | 0,00° | - | - | - | - | - | - | 1,2 s |
| molar, tetangga terlalu dekat (error) | shoulder | 0 µm | error 3 | - | - | - | 0,01° | - | - | - | - | - | - | 1,2 s |
| molar, tetangga terlalu dekat (error) | shoulder | 10 µm | error 3 | - | - | - | 0,01° | - | - | - | - | - | - | 1,2 s |
| molar, tetangga terlalu dekat (error) | shoulder | 30 µm | error 3 | - | - | - | 0,01° | - | - | - | - | - | - | 1,2 s |
| molar, tetangga terlalu dekat (error) | chamfer | 0 µm | error 3 | - | - | - | 0,01° | - | - | - | - | - | - | 1,2 s |
| molar, tetangga terlalu dekat (error) | chamfer | 10 µm | error 3 | - | - | - | 0,01° | - | - | - | - | - | - | 1,2 s |
| molar, tetangga terlalu dekat (error) | chamfer | 30 µm | error 3 | - | - | - | 0,01° | - | - | - | - | - | - | 1,2 s |
| premolar kecil, tetangga miring 15 | shoulder | 0 µm | kurva 3 | 1,9 µm | 4,2 µm | 1,0 µm | 0,01° | 0,000 µm | 0 (0) | 19,0° | 19,0° | ya | 7 | 8,1 s |
| premolar kecil, tetangga miring 15 | shoulder | 10 µm | kurva 3 | 8,1 µm | 1,9 µm | 9,6 µm | 0,00° | 0,000 µm | 0 (0) | 19,0° | 19,0° | ya | 7 | 7,9 s |
| premolar kecil, tetangga miring 15 | shoulder | 30 µm | kurva 3 | 29,2 µm | 22,0 µm | 22,8 µm | 0,00° | 0,000 µm | 0 (0) | 19,0° | 19,0° | ya | 9 | 10,2 s |
| premolar kecil, tetangga miring 15 | chamfer | 0 µm | kurva 3 | 1,9 µm | 4,2 µm | 1,0 µm | 0,01° | 0,000 µm | 0 (0) | 19,0° | 19,0° | ya | 7 | 8,1 s |
| premolar kecil, tetangga miring 15 | chamfer | 10 µm | kurva 3 | 8,1 µm | 1,9 µm | 9,6 µm | 0,00° | 0,000 µm | 0 (0) | 19,0° | 19,0° | ya | 7 | 8,0 s |
| premolar kecil, tetangga miring 15 | chamfer | 30 µm | kurva 3 | 29,2 µm | 22,0 µm | 22,8 µm | 0,00° | 0,000 µm | 0 (0) | 19,0° | 19,0° | ya | 9 | 10,2 s |
| molar besar, antagonis silinder | shoulder | 0 µm | kurva 3 | 1,9 µm | 1,6 µm | 0,1 µm | 0,00° | 0,000 µm | 0 (0) | 19,0° | 19,0° | - (molar, dilaporkan) | 11 | 14,3 s |
| molar besar, antagonis silinder | shoulder | 10 µm | kurva 3 | 7,8 µm | 7,1 µm | 6,9 µm | 0,00° | 0,000 µm | 0 (0) | 19,0° | 19,0° | - (molar, dilaporkan) | 11 | 13,4 s |
| molar besar, antagonis silinder | shoulder | 30 µm | kurva 3 | 32,4 µm | 22,8 µm | 30,9 µm | 0,00° | 0,000 µm | 0 (0) | 19,0° | 19,0° | - (molar, dilaporkan) | 12 | 14,0 s |
| molar besar, antagonis silinder | chamfer | 0 µm | kurva 3 | 1,9 µm | 1,6 µm | 0,1 µm | 0,00° | 0,000 µm | 0 (0) | 19,0° | 19,0° | - (molar, dilaporkan) | 11 | 13,9 s |
| molar besar, antagonis silinder | chamfer | 10 µm | kurva 3 | 7,8 µm | 7,1 µm | 6,9 µm | 0,00° | 0,000 µm | 0 (0) | 19,0° | 19,0° | - (molar, dilaporkan) | 11 | 13,4 s |
| molar besar, antagonis silinder | chamfer | 30 µm | kurva 3 | 32,4 µm | 22,8 µm | 30,9 µm | 0,00° | 0,000 µm | 0 (0) | 19,0° | 19,0° | - (molar, dilaporkan) | 12 | 14,2 s |
| insisif sentral, hanya tetangga mesial | shoulder | 0 µm | kurva 3 | 3,7 µm | - | 0,3 µm | 0,01° | 0,000 µm | 0 (0) | 19,0° | 19,0° | ya | 14 | 11,3 s |
| insisif sentral, hanya tetangga mesial | shoulder | 10 µm | kurva 3 | 6,4 µm | - | 6,7 µm | 0,01° | 0,000 µm | 0 (0) | 19,0° | 19,0° | ya | 14 | 11,0 s |
| insisif sentral, hanya tetangga mesial | shoulder | 30 µm | kurva 3 | 20,4 µm | - | 21,2 µm | 0,01° | 0,000 µm | 0 (0) | 19,0° | 19,0° | ya | 17 | 13,4 s |
| insisif sentral, hanya tetangga mesial | chamfer | 0 µm | kurva 3 | 3,7 µm | - | 0,3 µm | 0,01° | 0,000 µm | 0 (0) | 19,0° | 19,0° | ya | 14 | 11,1 s |
| insisif sentral, hanya tetangga mesial | chamfer | 10 µm | kurva 3 | 6,4 µm | - | 6,7 µm | 0,01° | 0,000 µm | 0 (0) | 19,0° | 19,0° | ya | 14 | 11,1 s |
| insisif sentral, hanya tetangga mesial | chamfer | 30 µm | kurva 3 | 20,4 µm | - | 21,2 µm | 0,01° | 0,000 µm | 0 (0) | 19,0° | 19,0° | ya | 17 | 13,6 s |
| kaninus, tanpa tetangga dan antagonis | shoulder | 0 µm | kurva 3 | - | - | - | - (dari pengguna) | 0,000 µm | 0 (0) | 19,0° | 19,0° | ya | 1 | 0,1 s |
| kaninus, tanpa tetangga dan antagonis | shoulder | 10 µm | kurva 3 | - | - | - | - (dari pengguna) | 0,000 µm | 0 (0) | 19,0° | 19,0° | ya | 1 | 0,0 s |
| kaninus, tanpa tetangga dan antagonis | shoulder | 30 µm | kurva 3 | - | - | - | - (dari pengguna) | 0,000 µm | 0 (0) | 19,0° | 19,0° | ya | 1 | 0,0 s |
| kaninus, tanpa tetangga dan antagonis | chamfer | 0 µm | kurva 3 | - | - | - | - (dari pengguna) | 0,000 µm | 0 (0) | 19,0° | 19,0° | ya | 1 | 0,0 s |
| kaninus, tanpa tetangga dan antagonis | chamfer | 10 µm | kurva 3 | - | - | - | - (dari pengguna) | 0,000 µm | 0 (0) | 19,0° | 19,0° | ya | 1 | 0,0 s |
| kaninus, tanpa tetangga dan antagonis | chamfer | 30 µm | kurva 3 | - | - | - | - (dari pengguna) | 0,000 µm | 0 (0) | 19,0° | 19,0° | ya | 1 | 0,0 s |
| premolar, antagonis miring terlalu dekat (error) | shoulder | 0 µm | error 3 | - | - | - | 0,01° | - | - | - | - | - | - | 1,1 s |
| premolar, antagonis miring terlalu dekat (error) | shoulder | 10 µm | error 3 | - | - | - | 0,01° | - | - | - | - | - | - | 1,1 s |
| premolar, antagonis miring terlalu dekat (error) | shoulder | 30 µm | error 3 | - | - | - | 0,00° | - | - | - | - | - | - | 1,1 s |
| premolar, antagonis miring terlalu dekat (error) | chamfer | 0 µm | error 3 | - | - | - | 0,01° | - | - | - | - | - | - | 1,1 s |
| premolar, antagonis miring terlalu dekat (error) | chamfer | 10 µm | error 3 | - | - | - | 0,01° | - | - | - | - | - | - | 1,1 s |
| premolar, antagonis miring terlalu dekat (error) | chamfer | 30 µm | error 3 | - | - | - | 0,00° | - | - | - | - | - | - | 1,1 s |
| lateral atas PL 2,5, tetangga dua sisi | shoulder | 0 µm | kurva 3 | 3,4 µm | 3,9 µm | 0,1 µm | 0,01° | 0,000 µm | 0 (0) | 19,0° | 19,0° | ya | 13 | 15,7 s |
| lateral atas PL 2,5, tetangga dua sisi | shoulder | 10 µm | kurva 3 | 9,7 µm | 6,1 µm | 8,4 µm | 0,01° | 0,000 µm | 0 (0) | 19,0° | 19,0° | ya | 13 | 16,2 s |
| lateral atas PL 2,5, tetangga dua sisi | shoulder | 30 µm | kurva 3 | 8,5 µm | 31,2 µm | 25,0 µm | 0,01° | 0,000 µm | 0 (0) | 19,0° | 19,0° | ya | 14 | 16,0 s |
| lateral atas PL 2,5, tetangga dua sisi | chamfer | 0 µm | kurva 3 | 3,4 µm | 3,9 µm | 0,1 µm | 0,01° | 0,000 µm | 0 (0) | 19,0° | 19,0° | ya | 13 | 15,0 s |
| lateral atas PL 2,5, tetangga dua sisi | chamfer | 10 µm | kurva 3 | 9,7 µm | 6,1 µm | 8,4 µm | 0,01° | 0,000 µm | 0 (0) | 19,0° | 19,0° | ya | 13 | 14,9 s |
| lateral atas PL 2,5, tetangga dua sisi | chamfer | 30 µm | kurva 3 | 8,5 µm | 31,2 µm | 25,0 µm | 0,01° | 0,000 µm | 0 (0) | 19,0° | 19,0° | ya | 14 | 15,9 s |
| insisif bawah PL 3,5, antagonis miring | shoulder | 0 µm | kurva 3 | 3,1 µm | 3,6 µm | 0,0 µm | 0,01° | 0,000 µm | 0 (0) | 19,0° | 19,0° | ya | 13 | 14,6 s |
| insisif bawah PL 3,5, antagonis miring | shoulder | 10 µm | kurva 3 | 3,0 µm | 3,7 µm | 10,5 µm | 0,01° | 0,000 µm | 0 (0) | 19,0° | 19,0° | ya | 13 | 14,4 s |
| insisif bawah PL 3,5, antagonis miring | shoulder | 30 µm | kurva 3 | 31,8 µm | 17,8 µm | 32,1 µm | 0,01° | 0,000 µm | 0 (0) | 19,0° | 19,0° | ya | 16 | 17,7 s |
| insisif bawah PL 3,5, antagonis miring | chamfer | 0 µm | kurva 3 | 3,1 µm | 3,6 µm | 0,0 µm | 0,01° | 0,000 µm | 0 (0) | 19,0° | 19,0° | ya | 13 | 14,5 s |
| insisif bawah PL 3,5, antagonis miring | chamfer | 10 µm | kurva 3 | 3,0 µm | 3,7 µm | 10,5 µm | 0,01° | 0,000 µm | 0 (0) | 19,0° | 19,0° | ya | 13 | 14,6 s |
| insisif bawah PL 3,5, antagonis miring | chamfer | 30 µm | kurva 3 | 31,8 µm | 17,8 µm | 32,1 µm | 0,01° | 0,000 µm | 0 (0) | 19,0° | 19,0° | ya | 16 | 17,6 s |
| molar PL 3,5, antagonis datar | shoulder | 0 µm | kurva 3 | 1,9 µm | 0,9 µm | 0,3 µm | 0,00° | 0,000 µm | 0 (0) | 19,0° | 19,0° | - (molar, dilaporkan) | 10 | 12,9 s |
| molar PL 3,5, antagonis datar | shoulder | 10 µm | kurva 3 | 8,1 µm | 5,7 µm | 6,6 µm | 0,00° | 0,000 µm | 0 (0) | 19,0° | 19,0° | - (molar, dilaporkan) | 10 | 12,0 s |
| molar PL 3,5, antagonis datar | shoulder | 30 µm | kurva 3 | 27,8 µm | 25,6 µm | 20,2 µm | 0,00° | 0,000 µm | 0 (0) | 19,0° | 19,0° | - (molar, dilaporkan) | 10 | 11,9 s |
| molar PL 3,5, antagonis datar | chamfer | 0 µm | kurva 3 | 1,9 µm | 0,9 µm | 0,3 µm | 0,00° | 0,000 µm | 0 (0) | 19,0° | 19,0° | - (molar, dilaporkan) | 10 | 12,1 s |
| molar PL 3,5, antagonis datar | chamfer | 10 µm | kurva 3 | 8,1 µm | 5,7 µm | 6,6 µm | 0,00° | 0,000 µm | 0 (0) | 19,0° | 19,0° | - (molar, dilaporkan) | 10 | 12,0 s |
| molar PL 3,5, antagonis datar | chamfer | 30 µm | kurva 3 | 27,8 µm | 25,6 µm | 20,2 µm | 0,00° | 0,000 µm | 0 (0) | 19,0° | 19,0° | - (molar, dilaporkan) | 10 | 12,1 s |
| lateral atas PL 3,4, antagonis miring 15 | shoulder | 0 µm | kurva 3 | 3,2 µm | 2,5 µm | 0,4 µm | 0,01° | 0,000 µm | 0 (0) | 19,0° | 19,0° | ya | 15 | 17,1 s |
| lateral atas PL 3,4, antagonis miring 15 | shoulder | 10 µm | kurva 3 | 10,5 µm | 6,2 µm | 7,9 µm | 0,01° | 0,000 µm | 0 (0) | 19,0° | 19,0° | ya | 15 | 17,0 s |
| lateral atas PL 3,4, antagonis miring 15 | shoulder | 30 µm | kurva 3 | 45,0 µm | 27,4 µm | 23,0 µm | 0,01° | 0,000 µm | 0 (0) | 19,0° | 19,0° | ya | 16 | 18,1 s |
| lateral atas PL 3,4, antagonis miring 15 | chamfer | 0 µm | kurva 3 | 3,2 µm | 2,5 µm | 0,4 µm | 0,01° | 0,000 µm | 0 (0) | 19,0° | 19,0° | ya | 15 | 17,2 s |
| lateral atas PL 3,4, antagonis miring 15 | chamfer | 10 µm | kurva 3 | 10,5 µm | 6,2 µm | 7,9 µm | 0,01° | 0,000 µm | 0 (0) | 19,0° | 19,0° | ya | 15 | 17,0 s |
| lateral atas PL 3,4, antagonis miring 15 | chamfer | 30 µm | kurva 3 | 45,0 µm | 27,4 µm | 23,0 µm | 0,01° | 0,000 µm | 0 (0) | 19,0° | 19,0° | ya | 16 | 18,1 s |
| kaninus bawah PL 3,0, antagonis silinder | shoulder | 0 µm | kurva 3 | 1,9 µm | 2,5 µm | 0,1 µm | 0,01° | 0,000 µm | 0 (0) | 19,0° | 19,0° | ya | 8 | 9,9 s |
| kaninus bawah PL 3,0, antagonis silinder | shoulder | 10 µm | kurva 3 | 7,0 µm | 8,9 µm | 22,2 µm | 0,01° | 0,000 µm | 0 (0) | 19,0° | 19,0° | ya | 8 | 9,6 s |
| kaninus bawah PL 3,0, antagonis silinder | shoulder | 30 µm | kurva 3 | 8,0 µm | 35,1 µm | 66,6 µm | 0,00° | 0,000 µm | 0 (0) | 19,0° | 19,0° | ya | 10 | 11,8 s |
| kaninus bawah PL 3,0, antagonis silinder | chamfer | 0 µm | kurva 3 | 1,9 µm | 2,5 µm | 0,1 µm | 0,01° | 0,000 µm | 0 (0) | 19,0° | 19,0° | ya | 8 | 10,1 s |
| kaninus bawah PL 3,0, antagonis silinder | chamfer | 10 µm | kurva 3 | 7,0 µm | 8,9 µm | 22,2 µm | 0,01° | 0,000 µm | 0 (0) | 19,0° | 19,0° | ya | 8 | 9,6 s |
| kaninus bawah PL 3,0, antagonis silinder | chamfer | 30 µm | kurva 3 | 8,0 µm | 35,1 µm | 66,6 µm | 0,00° | 0,000 µm | 0 (0) | 19,0° | 19,0° | ya | 10 | 11,9 s |
| insisif sentral bawah PL 2,6, tanpa antagonis | shoulder | 0 µm | kurva 3 | 2,5 µm | 2,5 µm | - | 0,01° | 0,000 µm | 0 (0) | 19,0° | 19,0° | ya | 8 | 5,8 s |
| insisif sentral bawah PL 2,6, tanpa antagonis | shoulder | 10 µm | kurva 3 | 9,2 µm | 6,0 µm | - | 0,01° | 0,000 µm | 0 (0) | 19,0° | 19,0° | ya | 8 | 5,9 s |
| insisif sentral bawah PL 2,6, tanpa antagonis | shoulder | 30 µm | kurva 3 | 15,5 µm | 26,0 µm | - | 0,01° | 0,000 µm | 0 (0) | 19,0° | 19,0° | ya | 9 | 6,7 s |
| insisif sentral bawah PL 2,6, tanpa antagonis | chamfer | 0 µm | kurva 3 | 2,5 µm | 2,5 µm | - | 0,01° | 0,000 µm | 0 (0) | 19,0° | 19,0° | ya | 8 | 5,7 s |
| insisif sentral bawah PL 2,6, tanpa antagonis | chamfer | 10 µm | kurva 3 | 9,2 µm | 6,0 µm | - | 0,01° | 0,000 µm | 0 (0) | 19,0° | 19,0° | ya | 8 | 5,8 s |
| insisif sentral bawah PL 2,6, tanpa antagonis | chamfer | 30 µm | kurva 3 | 15,5 µm | 26,0 µm | - | 0,01° | 0,000 µm | 0 (0) | 19,0° | 19,0° | ya | 9 | 6,6 s |
| premolar PL 2,8, tetangga miring 10 | shoulder | 0 µm | kurva 3 | 2,5 µm | 3,5 µm | 0,8 µm | 0,01° | 0,000 µm | 0 (0) | 19,0° | 19,0° | ya | 9 | 10,3 s |
| premolar PL 2,8, tetangga miring 10 | shoulder | 10 µm | kurva 3 | 8,3 µm | 5,3 µm | 9,1 µm | 0,00° | 0,000 µm | 0 (0) | 19,0° | 19,0° | ya | 9 | 10,6 s |
| premolar PL 2,8, tetangga miring 10 | shoulder | 30 µm | kurva 3 | 36,0 µm | 23,1 µm | 24,7 µm | 0,00° | 0,000 µm | 0 (0) | 19,0° | 19,0° | ya | 9 | 10,4 s |
| premolar PL 2,8, tetangga miring 10 | chamfer | 0 µm | kurva 3 | 2,5 µm | 3,5 µm | 0,8 µm | 0,01° | 0,000 µm | 0 (0) | 19,0° | 19,0° | ya | 9 | 10,1 s |
| premolar PL 2,8, tetangga miring 10 | chamfer | 10 µm | kurva 3 | 8,3 µm | 5,3 µm | 9,1 µm | 0,00° | 0,000 µm | 0 (0) | 19,0° | 19,0° | ya | 9 | 10,4 s |
| premolar PL 2,8, tetangga miring 10 | chamfer | 30 µm | kurva 3 | 36,0 µm | 23,1 µm | 24,7 µm | 0,00° | 0,000 µm | 0 (0) | 19,0° | 19,0° | ya | 9 | 10,4 s |
| molar PL 3,8, hanya tetangga distal | shoulder | 0 µm | kurva 3 | - | 3,0 µm | 0,1 µm | 0,01° | 0,000 µm | 0 (0) | 19,0° | 19,0° | - (molar, dilaporkan) | 10 | 8,7 s |
| molar PL 3,8, hanya tetangga distal | shoulder | 10 µm | kurva 3 | - | 9,0 µm | 19,8 µm | 0,01° | 0,000 µm | 0 (0) | 19,0° | 19,0° | - (molar, dilaporkan) | 10 | 8,4 s |
| molar PL 3,8, hanya tetangga distal | shoulder | 30 µm | kurva 3 | - | 23,9 µm | 64,6 µm | 0,01° | 0,000 µm | 0 (0) | 19,0° | 19,0° | - (molar, dilaporkan) | 13 | 11,0 s |
| molar PL 3,8, hanya tetangga distal | chamfer | 0 µm | kurva 3 | - | 3,0 µm | 0,1 µm | 0,01° | 0,000 µm | 0 (0) | 19,0° | 19,0° | - (molar, dilaporkan) | 10 | 8,7 s |
| molar PL 3,8, hanya tetangga distal | chamfer | 10 µm | kurva 3 | - | 9,0 µm | 19,8 µm | 0,01° | 0,000 µm | 0 (0) | 19,0° | 19,0° | - (molar, dilaporkan) | 10 | 8,4 s |
| molar PL 3,8, hanya tetangga distal | chamfer | 30 µm | kurva 3 | - | 23,9 µm | 64,6 µm | 0,01° | 0,000 µm | 0 (0) | 19,0° | 19,0° | - (molar, dilaporkan) | 13 | 11,3 s |
| insisif PL 3,2, tetangga terlalu dekat (error) | shoulder | 0 µm | error 3 | - | - | - | 0,01° | - | - | - | - | - | - | 1,2 s |
| insisif PL 3,2, tetangga terlalu dekat (error) | shoulder | 10 µm | error 3 | - | - | - | 0,01° | - | - | - | - | - | - | 1,1 s |
| insisif PL 3,2, tetangga terlalu dekat (error) | shoulder | 30 µm | error 3 | - | - | - | 0,01° | - | - | - | - | - | - | 1,1 s |
| insisif PL 3,2, tetangga terlalu dekat (error) | chamfer | 0 µm | error 3 | - | - | - | 0,01° | - | - | - | - | - | - | 1,1 s |
| insisif PL 3,2, tetangga terlalu dekat (error) | chamfer | 10 µm | error 3 | - | - | - | 0,01° | - | - | - | - | - | - | 1,1 s |
| insisif PL 3,2, tetangga terlalu dekat (error) | chamfer | 30 µm | error 3 | - | - | - | 0,01° | - | - | - | - | - | - | 1,1 s |

**Set ukur ketiga (dijalankan sekali, `76aed0e`):**

| Kasus | Finish | Derau | Hasil per seed | |galat| kontak mesial | |galat| kontak distal | |galat| jarak oklusal | Galat arah mesial | Tepi servikal ke margin | Lipatan (non-sliver) | Emergence median | Emergence maks | Median ≤ 21° | Iterasi | Waktu |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| kaninus atas PL 2,6, antagonis miring 10 | shoulder | 0 µm | kurva 3 | 3,0 µm | 1,2 µm | 0,8 µm | 0,01° | 0,000 µm | 0 (0) | 19,0° | 19,0° | ya | 7 | 8,6 s |
| kaninus atas PL 2,6, antagonis miring 10 | shoulder | 10 µm | kurva 3 | 16,9 µm | 6,2 µm | 5,6 µm | 0,01° | 0,000 µm | 0 (0) | 19,0° | 19,0° | ya | 10 | 11,7 s |
| kaninus atas PL 2,6, antagonis miring 10 | shoulder | 30 µm | kurva 3 | 25,5 µm | 18,1 µm | 6,5 µm | 0,00° | 0,000 µm | 0 (0) | 19,0° | 19,0° | ya | 11 | 12,9 s |
| kaninus atas PL 2,6, antagonis miring 10 | chamfer | 0 µm | kurva 3 | 3,0 µm | 1,2 µm | 0,8 µm | 0,01° | 0,000 µm | 0 (0) | 19,0° | 19,0° | ya | 7 | 8,6 s |
| kaninus atas PL 2,6, antagonis miring 10 | chamfer | 10 µm | kurva 3 | 16,9 µm | 6,2 µm | 5,6 µm | 0,01° | 0,000 µm | 0 (0) | 19,0° | 19,0° | ya | 10 | 28908,0 s (laptop tidur, catatan di bawah) |
| kaninus atas PL 2,6, antagonis miring 10 | chamfer | 30 µm | kurva 3 | 25,5 µm | 18,1 µm | 6,5 µm | 0,00° | 0,000 µm | 0 (0) | 19,0° | 19,0° | ya | 11 | 9,2 s |
| lateral bawah PL 3,0, tanpa tetangga | shoulder | 0 µm | kurva 3 | - | - | 0,1 µm | - (dari pengguna) | 0,000 µm | 0 (0) | 19,0° | 19,0° | ya | 3 | 1,0 s |
| lateral bawah PL 3,0, tanpa tetangga | shoulder | 10 µm | kurva 3 | - | - | 9,8 µm | - (dari pengguna) | 0,000 µm | 0 (0) | 19,0° | 19,0° | ya | 3 | 0,9 s |
| lateral bawah PL 3,0, tanpa tetangga | shoulder | 30 µm | kurva 3 | - | - | 37,1 µm | - (dari pengguna) | 0,000 µm | 0 (0) | 19,0° | 19,0° | ya | 3 | 1,0 s |
| lateral bawah PL 3,0, tanpa tetangga | chamfer | 0 µm | kurva 3 | - | - | 0,1 µm | - (dari pengguna) | 0,000 µm | 0 (0) | 19,0° | 19,0° | ya | 3 | 0,9 s |
| lateral bawah PL 3,0, tanpa tetangga | chamfer | 10 µm | kurva 3 | - | - | 9,8 µm | - (dari pengguna) | 0,000 µm | 0 (0) | 19,0° | 19,0° | ya | 3 | 1,0 s |
| lateral bawah PL 3,0, tanpa tetangga | chamfer | 30 µm | kurva 3 | - | - | 37,1 µm | - (dari pengguna) | 0,000 µm | 0 (0) | 19,0° | 19,0° | ya | 3 | 1,0 s |
| insisif sentral atas PL 3,6, tetangga asimetris | shoulder | 0 µm | kurva 3 | 3,1 µm | 2,4 µm | 0,7 µm | 0,01° | 0,000 µm | 0 (0) | 19,0° | 19,0° | ya | 15 | 16,5 s |
| insisif sentral atas PL 3,6, tetangga asimetris | shoulder | 10 µm | kurva 3 | 10,1 µm | 12,0 µm | 7,8 µm | 0,01° | 0,000 µm | 0 (0) | 19,0° | 19,0° | ya | 16 | 19,4 s |
| insisif sentral atas PL 3,6, tetangga asimetris | shoulder | 30 µm | kurva 3 | 46,5 µm | 42,8 µm | 25,2 µm | 0,00° | 0,000 µm | 0 (0) | 19,0° | 19,0° | ya | 15 | 25,0 s |
| insisif sentral atas PL 3,6, tetangga asimetris | chamfer | 0 µm | kurva 3 | 3,1 µm | 2,4 µm | 0,7 µm | 0,01° | 0,000 µm | 0 (0) | 19,0° | 19,0° | ya | 15 | 21,5 s |
| insisif sentral atas PL 3,6, tetangga asimetris | chamfer | 10 µm | kurva 3 | 10,1 µm | 12,0 µm | 7,8 µm | 0,01° | 0,000 µm | 0 (0) | 19,0° | 19,0° | ya | 16 | 21,9 s |
| insisif sentral atas PL 3,6, tetangga asimetris | chamfer | 30 µm | kurva 3 | 46,5 µm | 42,8 µm | 25,2 µm | 0,00° | 0,000 µm | 0 (0) | 19,0° | 19,0° | ya | 15 | 21,9 s |
| premolar atas PL 2,2, antagonis silinder | shoulder | 0 µm | kurva 3 | 2,3 µm | 2,7 µm | 0,5 µm | 0,01° | 0,000 µm | 0 (0) | 19,0° | 19,0° | ya | 8 | 11,0 s |
| premolar atas PL 2,2, antagonis silinder | shoulder | 10 µm | kurva 3 | 12,0 µm | 7,0 µm | 4,4 µm | 0,00° | 0,000 µm | 0 (0) | 19,0° | 19,0° | ya | 8 | 10,6 s |
| premolar atas PL 2,2, antagonis silinder | shoulder | 30 µm | kurva 3 | 6,4 µm | 31,2 µm | 10,4 µm | 0,00° | 0,000 µm | 0 (0) | 19,0° | 19,0° | ya | 10 | 14,7 s |
| premolar atas PL 2,2, antagonis silinder | chamfer | 0 µm | kurva 3 | 2,3 µm | 2,7 µm | 0,5 µm | 0,01° | 0,000 µm | 0 (0) | 19,0° | 19,0° | ya | 8 | 7,0 s |
| premolar atas PL 2,2, antagonis silinder | chamfer | 10 µm | kurva 3 | 12,0 µm | 7,0 µm | 4,4 µm | 0,00° | 0,000 µm | 0 (0) | 19,0° | 19,0° | ya | 8 | 6,8 s |
| premolar atas PL 2,2, antagonis silinder | chamfer | 30 µm | kurva 3 | 6,4 µm | 31,2 µm | 10,4 µm | 0,00° | 0,000 µm | 0 (0) | 19,0° | 19,0° | ya | 10 | 8,3 s |
| premolar bawah PL 3,0, hanya tetangga mesial | shoulder | 0 µm | kurva 3 | 2,9 µm | - | 0,9 µm | 0,01° | 0,000 µm | 0 (0) | 19,0° | 19,0° | ya | 9 | 5,1 s |
| premolar bawah PL 3,0, hanya tetangga mesial | shoulder | 10 µm | kurva 3 | 8,4 µm | - | 12,7 µm | 0,01° | 0,000 µm | 0 (0) | 19,0° | 19,0° | ya | 10 | 5,7 s |
| premolar bawah PL 3,0, hanya tetangga mesial | shoulder | 30 µm | kurva 3 | 23,5 µm | - | 44,7 µm | 0,01° | 0,000 µm | 0 (0) | 19,0° | 19,0° | ya | 10 | 5,7 s |
| premolar bawah PL 3,0, hanya tetangga mesial | chamfer | 0 µm | kurva 3 | 2,9 µm | - | 0,9 µm | 0,01° | 0,000 µm | 0 (0) | 19,0° | 19,0° | ya | 9 | 5,1 s |
| premolar bawah PL 3,0, hanya tetangga mesial | chamfer | 10 µm | kurva 3 | 8,4 µm | - | 12,7 µm | 0,01° | 0,000 µm | 0 (0) | 19,0° | 19,0° | ya | 10 | 5,7 s |
| premolar bawah PL 3,0, hanya tetangga mesial | chamfer | 30 µm | kurva 3 | 23,5 µm | - | 44,7 µm | 0,01° | 0,000 µm | 0 (0) | 19,0° | 19,0° | ya | 10 | 5,7 s |
| molar atas PL 3,2, antagonis miring 6 | shoulder | 0 µm | kurva 3 | 2,6 µm | 1,9 µm | 0,7 µm | 0,00° | 0,000 µm | 0 (0) | 19,0° | 19,0° | - (molar, dilaporkan) | 10 | 8,5 s |
| molar atas PL 3,2, antagonis miring 6 | shoulder | 10 µm | kurva 3 | 8,7 µm | 6,5 µm | 4,0 µm | 0,00° | 0,000 µm | 0 (0) | 19,0° | 19,0° | - (molar, dilaporkan) | 10 | 12,2 s |
| molar atas PL 3,2, antagonis miring 6 | shoulder | 30 µm | kurva 3 | 33,9 µm | 23,5 µm | 14,3 µm | 0,00° | 0,000 µm | 0 (0) | 19,0° | 19,0° | - (molar, dilaporkan) | 11 | 9,3 s |
| molar atas PL 3,2, antagonis miring 6 | chamfer | 0 µm | kurva 3 | 2,6 µm | 1,9 µm | 0,7 µm | 0,00° | 0,000 µm | 0 (0) | 19,0° | 19,0° | - (molar, dilaporkan) | 10 | 9,0 s |
| molar atas PL 3,2, antagonis miring 6 | chamfer | 10 µm | kurva 3 | 8,7 µm | 6,5 µm | 4,0 µm | 0,00° | 0,000 µm | 0 (0) | 19,0° | 19,0° | - (molar, dilaporkan) | 10 | 8,9 s |
| molar atas PL 3,2, antagonis miring 6 | chamfer | 30 µm | kurva 3 | 33,9 µm | 23,5 µm | 14,3 µm | 0,00° | 0,000 µm | 0 (0) | 19,0° | 19,0° | - (molar, dilaporkan) | 11 | 9,3 s |
| premolar PL 2,4, antagonis terlalu dekat (error) | shoulder | 0 µm | error 3 | - | - | - | 0,01° | - | - | - | - | - | - | 0,8 s |
| premolar PL 2,4, antagonis terlalu dekat (error) | shoulder | 10 µm | error 3 | - | - | - | 0,01° | - | - | - | - | - | - | 0,8 s |
| premolar PL 2,4, antagonis terlalu dekat (error) | shoulder | 30 µm | error 3 | - | - | - | 0,00° | - | - | - | - | - | - | 0,8 s |
| premolar PL 2,4, antagonis terlalu dekat (error) | chamfer | 0 µm | error 3 | - | - | - | 0,01° | - | - | - | - | - | - | 0,8 s |
| premolar PL 2,4, antagonis terlalu dekat (error) | chamfer | 10 µm | error 3 | - | - | - | 0,01° | - | - | - | - | - | - | 0,8 s |
| premolar PL 2,4, antagonis terlalu dekat (error) | chamfer | 30 µm | error 3 | - | - | - | 0,00° | - | - | - | - | - | - | 0,8 s |

Kesimpulan:
- **Emergence: lulus.**
  - Set ukur: 30 dari 30 baris anterior dan premolar dengan median ≤ 21°.
  - Semua sudut keliling di kedua set tepat 19,0° (minimum dan maksimum 19,0°, termasuk molar). Sepertiga servikal ≥ 1 mm di semua kasus, termasuk puncak scallop PL 3,6.
- **Lipatan:** 0 non-sliver dan 0 face berbalik, di 108 kurva (ukur) dan 252 kurva (tuning).
- **Kontak** (galat jarak eksak):
  - tanpa derau ≤ 3,1 µm ke tetangga dan ≤ 0,9 µm ke antagonis (ukur);
  - pada derau 10 µm ≤ 17 µm dan ≤ 13 µm;
  - pada derau 30 µm ≤ 47 µm dan ≤ 45 µm (ukur). Di set tuning sampai 45 µm dan 67 µm. Ini masih bias derau mesh tetangga atau antagonis, sama seperti sebelumnya.
- **Lainnya:**
  - error eksplisit 18 dari 18 (ukur) dan 72 dari 72 (tuning), tanpa error di kasus yang seharusnya bisa, dan tanpa timeout;
  - arah mesial ≤ 0,012°; tepi servikal = margin (0 µm).
- **Lebih lambat:**
  - iterasi penyesuaian naik dari 3-10 menjadi 3-17, dan waktu per proposal sampai 25 s (ukur, insisif sentral atas). Sebelumnya ≤ 11 s;
  - dugaan: kontak tetangga jatuh di zona campur, tempat perubahan lebar template hanya berpengaruh sebagian, sehingga langkah iterasi kurang dari satu dan butuh lebih banyak putaran. Ini belum dibuktikan.

**Pengujian.**
- Lapis 1 (`tests/core/test_crown.py`, 39 kasus tes):
  - jenis FDI dan FDI tidak sah ditolak;
  - lebar dan tinggi template tepat (4 jenis × 2 ukuran);
  - tepi servikal = margin dan tanpa lipatan;
  - kontak mencapai target pada permukaan eksak;
  - ruang oklusal dan mesiodistal sempit menjadi error eksplisit;
  - margin yang tidak melingkari sumbu ditolak;
  - jarak elipsoid eksak di titik yang diketahui;
  - dasar template per sudut (tepi servikal setinggi dasar, dinding tetap naik, dasar di atas dinding ditolak);
  - scallop dalam tanpa lipatan (insisif bawah PL 3,5, insisif sentral PL 3,2, kaninus PL 2,5, molar PL 3,5);
  - sepertiga servikal tepat kerucut dari margin dengan sudut emergence, dan permukaan = template murni di atas sepertiga servikal + `blend_height_mm`;
  - parameter sudut emergence (15° dan 19°) menentukan 1 mm pertama pada insisif bawah PL 3,5 dan premolar PL 2,5, tanpa lipatan;
  - sudut emergence kerucut −5, 0, 12, dan 20° tepat.
- Lapis 1 (`tests/core/test_repo_rules.py`): set tuning crown berisi scallop PL 2,5 dan 3,5 mm serta die anterior.
- Lapis 1 (`tests/core/test_bench_runner.py`): kasus lambat menjadi timeout, dan kasus berikutnya tetap jalan.
- Lapis 1 (`tests/core/test_material_db.py`): hanya jarak bertanda yang boleh negatif.
- Lapis 2 (`run_integration.py`):
  - gerbang spacer;
  - proposal pada kasus sintetis dengan tetangga dan antagonis (kontak −20 µm, oklusal 0 µm, arah mesial dari tetangga);
  - kedaluwarsa bila antagonis digeser atau FDI berubah;
  - tanpa tetangga: arah mesial dari panah dengan catatan "needs checking", bola yang diseret membuat proposal kedaluwarsa, dan proposal ulang mengikuti bola.

### 5.5 Kontak proksimal dan jarak oklusal

**Algoritma:**
- Jarak bertanda dari permukaan luar crown ke gigi tetangga dan antagonis (titik terdekat di permukaan, lihat §5.6 untuk struktur data).
- Daerah kontak = jarak ≤ target. Overlap proksimal yang diminta dibuat lewat parameter template (§5.4 langkah 3). Bentuk kontak lokal di luar parameter global **tidak** memakai deformasi Laplacian (paten PAT4, §5.4); metodenya dirancang ulang saat §5.5 direncanakan.
- Jarak oklusal ke antagonis dilaporkan dan diwarnai.

**Parameter.**

| Parameter | Status | Nilai | Sumber |
|---|---|---|---|
| Jarak approximal | literatur, perlu kalibrasi | −0,020 mm | NAG (sama dengan §5.4); menggantikan 0,025 mm RESEARCH.md §3 yang tanpa rujukan. |
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
- **Kegunaan:** `scipy.sparse` (graf margin §5.1 dan komponen terhubung §5.2; deformasi Laplacian §5.4 dihapus dari rencana karena paten PAT4) dan `scipy.spatial.cKDTree` (jarak ke permukaan, §5.5 dan §5.6). Ini persis kasus "fase yang benar-benar memakainya" di backlog ARCHITECTURE.md §8.
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
| S1 | Seberapa akurat curvature + Dijkstra pada data sintetis berderau? | **Dijawab** (2026-10-23): lolos untuk derau sampai 30 µm, gagal di 90 µm; detail, perubahan algoritma, dan tabel di §5.1. Pengaman derau dan kewajaran ditambahkan; metrik panjang diperbaiki. Set uji pertama: 3 kurva buruk tanpa pesan (puncak proksimal insisif sentral), diperbaiki dengan syarat crease untuk titik jauh. Penanda merah + status draf ditambahkan; set uji kedua: 0 kurva buruk tanpa pesan atau merah. | Penanda merah belum andal menunjuk lokasi galat; alarm palsu tinggi pada derau 30 µm. Segmen merah dijadikan petunjuk ringan; semua ambang perlu diuji ulang dengan scan asli (ringkasan status §5.1). |
| S2 | Apakah cKDTree + penyempurnaan titik-ke-segitiga cukup cepat untuk crown sekitar 100 ribu segitiga? | Ukur di host dan di Blender. | Kurangi sampel dengan sampling adaptif, atau batasi penyempurnaan eksak ke daerah dekat ambang. |
| S3 | ~~Apakah Laplacian dengan batas margin stabil untuk scallop besar?~~ **Gugur** (2026-10-25): deformasi Laplacian tidak dipakai (paten PAT4, §5.4). | - | - |
| S5 | Apakah permukaan luar berlabuh margin (interpolasi transfinit) dan strip penghubung bebas self-intersection pada scallop dalam (PL sampai 4 mm) dan die kecil? | Uji acak parameter template dan varian die §5.1 sampai §5.3, validasi manifold3d. | Fungsi campuran w(v) yang lebih landai, resolusi u adaptif, atau error eksplisit untuk kombinasi yang tidak bisa dibangun. |
| R1 | Data sintetis terlalu "bersih" dibanding scan nyata (lubang, artefak, gingiva menutupi margin). | Tidak bisa dijawab tanpa scan nyata. | Dicatat sebagai keterbatasan validasi. Uji ketahanan pada scan nyata menunggu data (golden_private) atau keputusan K3. |
| R2 | Paten metode deteksi margin (RESEARCH.md §4). | K5. | Pilih metode alternatif yang tidak tercakup, misalnya biaya berbasis sudut dihedral, bukan curvature. |

## 9. Keputusan (maintainer, 2026-10-23; K6 sampai K9 2026-10-25 di §5.4)

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
