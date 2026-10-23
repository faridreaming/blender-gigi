# SPDX-License-Identifier: GPL-3.0-or-later
"""Satuan panjang (mm) dan konversi penomoran gigi FDI (ISO 3950), Universal, dan Palmer.

Format yang dipakai:
- FDI: int dua digit. Permanen 11-18, 21-28, 31-38, 41-48. Desidui 51-55, 61-65, 71-75, 81-85.
- Universal: permanen int 1-32, desidui huruf "A"-"T".
- Palmer: string kuadran + gigi, mis. "UR6" (permanen, angka 1-8) atau "LLD" (desidui, huruf A-E).
  Kuadran: UR (kanan atas), UL (kiri atas), LL (kiri bawah), LR (kanan bawah), dari sisi pasien.
"""

from __future__ import annotations

_MM_PER_UNIT = {"mm": 1.0, "cm": 10.0, "m": 1000.0, "um": 0.001, "in": 25.4}


def to_mm(value: float, unit: str) -> float:
    try:
        return value * _MM_PER_UNIT[unit]
    except KeyError:
        raise ValueError(f"satuan tidak dikenal: {unit!r}") from None


def from_mm(value_mm: float, unit: str) -> float:
    try:
        return value_mm / _MM_PER_UNIT[unit]
    except KeyError:
        raise ValueError(f"satuan tidak dikenal: {unit!r}") from None


# Kuadran FDI -> kuadran Palmer. 1-4 permanen, 5-8 desidui (urutan kuadran sama).
_PALMER_QUADRANT = {1: "UR", 2: "UL", 3: "LL", 4: "LR"}
_FDI_QUADRANT = {name: q for q, name in _PALMER_QUADRANT.items()}
_PRIMARY_LETTERS = "ABCDE"


def _split_fdi(fdi: int) -> tuple[int, int, bool]:
    """(kuadran permanen 1-4, posisi dari garis tengah, desidui?)."""
    if isinstance(fdi, bool) or not isinstance(fdi, int):
        raise ValueError(f"nomor FDI wajib int, didapat {fdi!r}")
    quadrant, position = divmod(fdi, 10)
    if 1 <= quadrant <= 4 and 1 <= position <= 8:
        return quadrant, position, False
    if 5 <= quadrant <= 8 and 1 <= position <= 5:
        return quadrant - 4, position, True
    raise ValueError(f"nomor FDI tidak valid: {fdi}")


def fdi_to_universal(fdi: int) -> int | str:
    quadrant, position, primary = _split_fdi(fdi)
    n = 5 if primary else 8
    # Universal berjalan searah jarum jam dari kanan atas pasien: UR distal->mesial,
    # UL mesial->distal, LL distal->mesial, LR mesial->distal.
    if quadrant == 1:
        index = n - position
    elif quadrant == 2:
        index = n + position - 1
    elif quadrant == 3:
        index = 3 * n - position
    else:
        index = 3 * n + position - 1
    return chr(ord("A") + index) if primary else index + 1


def universal_to_fdi(universal: int | str) -> int:
    if isinstance(universal, str):
        if len(universal) != 1 or not "A" <= universal.upper() <= "T":
            raise ValueError(f"nomor Universal desidui tidak valid: {universal!r}")
        index, n, base = ord(universal.upper()) - ord("A"), 5, 4
    elif isinstance(universal, int) and not isinstance(universal, bool) and 1 <= universal <= 32:
        index, n, base = universal - 1, 8, 0
    else:
        raise ValueError(f"nomor Universal tidak valid: {universal!r}")
    quadrant, offset = divmod(index, n)
    position = n - offset if quadrant in (0, 2) else offset + 1
    return (base + quadrant + 1) * 10 + position


def fdi_to_palmer(fdi: int) -> str:
    quadrant, position, primary = _split_fdi(fdi)
    tooth = _PRIMARY_LETTERS[position - 1] if primary else str(position)
    return _PALMER_QUADRANT[quadrant] + tooth


def palmer_to_fdi(palmer: str) -> int:
    if not isinstance(palmer, str) or len(palmer) != 3:
        raise ValueError(f"notasi Palmer tidak valid: {palmer!r}")
    quadrant_name, tooth = palmer[:2].upper(), palmer[2].upper()
    if quadrant_name not in _FDI_QUADRANT:
        raise ValueError(f"kuadran Palmer tidak valid: {palmer!r}")
    quadrant = _FDI_QUADRANT[quadrant_name]
    if tooth in "12345678":
        return quadrant * 10 + int(tooth)
    if tooth in _PRIMARY_LETTERS:
        return (quadrant + 4) * 10 + _PRIMARY_LETTERS.index(tooth) + 1
    raise ValueError(f"gigi Palmer tidak valid: {palmer!r}")


def all_fdi(primary: bool = False) -> list[int]:
    """Semua nomor FDI permanen (32) atau desidui (20), urut per kuadran."""
    if primary:
        return [q * 10 + p for q in range(5, 9) for p in range(1, 6)]
    return [q * 10 + p for q in range(1, 5) for p in range(1, 9)]
