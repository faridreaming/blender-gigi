# Preset material

Satu file JSON per material. Skema divalidasi oleh `core/material_db.py`:

| Field | Tipe | Keterangan |
|---|---|---|
| `id` | string | Unik di seluruh folder. |
| `name`, `manufacturer` | string | Nama tampilan. |
| `min_thickness_anterior_mm`, `min_thickness_posterior_mm` | angka > 0 | Ketebalan minimum crown dari IFU. |
| `connector_area_mm2` | `{anterior, posterior}` | Luas penampang konektor bridge minimum dari IFU. |
| `cement_gap_um` | angka > 0 | Gap semen default (aksial/occlusal). |
| `source` | string | Dokumen sumber angka di atas. |
| `source_date` | `YYYY`, `YYYY-MM`, atau `YYYY-MM-DD` | Revisi dokumen sumber. |

## Sumber per file

| File | Sumber | Revisi |
|---|---|---|
| `zircad_prime.json` | Ivoclar IFU IPS e.max ZirCAD (labside), RESEARCH.md §2. Ketebalan 0,8/1,0 mm dan konektor 9/9 mm² (bridge 3 unit). | 2023 |

Catatan `zircad_prime.json`: IFU tidak memberi angka gap semen. Nilai `cement_gap_um = 50` diambil dari rentang default 30-60 µm aksial/occlusal yang disarankan di RESEARCH.md §2 (literatur, bukan IFU), dan harus dikalibrasi per mesin dengan uji fit. Preset ini hanya contoh jalur kerja Fase 0; validasi ketebalan/konektor terhadap geometri baru dibangun di Fase 2-3.
