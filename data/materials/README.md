# Preset material

Satu file JSON per material, divalidasi oleh `core/material_db.py`. Setiap parameter memakai skema yang sama dengan preset cetak model (`data/model_presets/README.md`): `value`, `unit`, `status`, `source`, `source_date`.

```json
{
  "id": "ivoclar_zircad_prime_full_contour",
  "name": "IPS e.max ZirCAD Prime (full-contour)",
  "manufacturer": "Ivoclar",
  "params": {
    "cement_gap_um": {"value": 60, "unit": "um", "status": "default_pabrikan", "source": "...", "source_date": "2024-02-07"}
  }
}
```

Parameter wajib (lihat `REQUIRED_PARAMS` di `core/material_db.py`):

| Parameter | Satuan | Arti |
|---|---|---|
| `min_thickness_anterior_mm`, `min_thickness_premolar_mm`, `min_thickness_molar_mm` | mm | Ketebalan minimum crown tunggal per region. |
| `connector_area_anterior_mm2`, `connector_area_posterior_mm2` | mm2 | Luas konektor minimum bridge. |
| `cement_gap_um` | um | Gap semen. |
| `cement_gap_from_margin_mm` | mm | Jarak dari margin line tempat cement gap mulai ("From margin" di exocad). |
| `radial_spacing_um`, `axial_spacing_um` | um | Additional spacing radial (tegak lurus sumbu insersi) dan axial; berlaku juga di zona tanpa cement gap. |
| `margin_horizontal_mm`, `margin_angled_length_mm`, `margin_angle_deg` | mm, mm, deg | Border crown di margin: lebar horizontal, panjang bagian bersudut, dan sudutnya. |
| `milling_tool_diameter_mm` | mm | Diameter alat untuk antisipasi milling. |
| `blockout_free_zone_mm` | mm | Zona di dekat margin line yang tidak di-block-out ("Don't block out zone near prepline" di exocad). |

## Sumber per file

| File | Sumber | Revisi |
|---|---|---|
| `zircad_prime.json` | IVO: Ivoclar Software Parameter Chart (exocad), baris IPS e.max ZirCAD Prime (full/partial anatomical), single crown. Definisi parameter dari DTX Studio Lab Help dan wiki exocad. Detail di docs/PHASE2.md §2.1. | Rev. 1, 2024-02-07 |

Catatan `zircad_prime.json`:
- `axial_spacing_um = 0` berstatus `perlu_kalibrasi`, karena IVO hanya mencantumkan spacing x/y (radial).
- `blockout_free_zone_mm = 0.1` berstatus `perlu_kalibrasi`: tidak tercantum di IVO; 0,1 mm adalah default generik exocad menurut exocad Quick Guide: Crown Bottoms (docs/PHASE2.md §5.2), dan nilai yang tepat bergantung pada mesin milling.
- Angka sebelumnya (`cement_gap_um = 50` dari literatur RESEARCH.md §2) diganti angka Ivoclar sesuai keputusan K4 Fase 2.
- Semua nilai `default_pabrikan` adalah setelan pabrikan untuk exocad; nilai klinis final tetap perlu dikalibrasi dengan milling.
