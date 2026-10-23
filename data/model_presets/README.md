# Preset cetak model

Satu file JSON per pasangan printer + resin (docs/PHASE1.md §1 dan §3). Skema divalidasi oleh `core/model_presets.py`.

```json
{
  "id": "photon_p1_std_v2_hd_gray",
  "printer": "Anycubic Photon P1",
  "resin": "Anycubic Standard Resin V2, HD Gray",
  "params": {
    "<nama>": {"value": 3.0, "unit": "mm", "status": "default_pabrikan", "source": "...", "source_date": "2026-10-23"}
  }
}
```

| Field | Keterangan |
|---|---|
| `value` | Angka atau string. Tidak boleh `null`: parameter yang belum punya nilai tidak dicantumkan sama sekali. |
| `status` | `default_pabrikan` (printer lain, perlu kalibrasi), `perlu_kalibrasi`, `praktik_lab`, atau `dikalibrasi`. |
| `source` | Sumber nilai, dengan ID sumber dari docs/PHASE1.md §2 bila ada. |
| `source_date` | Tanggal dokumen sumber kalau diketahui (misalnya KUL "As of 09.2020" ditulis `2020-09`); kalau tidak diketahui, tanggal sumber itu diverifikasi. Untuk nilai `dikalibrasi`, tanggal kupon diukur. |
| `coupon_range` | Opsional, `[bawah, atas]`. Kalau ada, nilai wajib di dalamnya; kupon menyapu rentang ini. |

Nilai `dikalibrasi` ditulis oleh `scripts/apply_calibration.py` dari lembar ukur kupon, bukan diedit tangan.
