# SPDX-License-Identifier: GPL-3.0-or-later
import pytest

from core import units


@pytest.mark.parametrize(
    "fdi, universal, palmer",
    [
        (18, 1, "UR8"),
        (11, 8, "UR1"),
        (21, 9, "UL1"),
        (28, 16, "UL8"),
        (38, 17, "LL8"),
        (36, 19, "LL6"),
        (31, 24, "LL1"),
        (41, 25, "LR1"),
        (48, 32, "LR8"),
        (55, "A", "URE"),
        (51, "E", "URA"),
        (61, "F", "ULA"),
        (65, "J", "ULE"),
        (75, "K", "LLE"),
        (71, "O", "LLA"),
        (81, "P", "LRA"),
        (85, "T", "LRE"),
    ],
)
def test_known_tooth_numbers(fdi, universal, palmer):
    assert units.fdi_to_universal(fdi) == universal
    assert units.universal_to_fdi(universal) == fdi
    assert units.fdi_to_palmer(fdi) == palmer
    assert units.palmer_to_fdi(palmer) == fdi


@pytest.mark.parametrize("primary, count", [(False, 32), (True, 20)])
def test_round_trip_covers_every_tooth_once(primary, count):
    teeth = units.all_fdi(primary=primary)
    assert len(teeth) == count
    universal = [units.fdi_to_universal(t) for t in teeth]
    assert len(set(universal)) == count
    assert [units.universal_to_fdi(u) for u in universal] == teeth
    assert [units.palmer_to_fdi(units.fdi_to_palmer(t)) for t in teeth] == teeth


@pytest.mark.parametrize("bad", [10, 19, 56, 90, 0, "11", True])
def test_invalid_fdi(bad):
    with pytest.raises(ValueError):
        units.fdi_to_universal(bad)


@pytest.mark.parametrize("bad", [0, 33, "U", "AA", 1.0])
def test_invalid_universal(bad):
    with pytest.raises(ValueError):
        units.universal_to_fdi(bad)


@pytest.mark.parametrize("bad", ["XX1", "UR9", "URF", "UR", 11])
def test_invalid_palmer(bad):
    with pytest.raises(ValueError):
        units.palmer_to_fdi(bad)


def test_length_conversion():
    assert units.to_mm(1.5, "cm") == 15.0
    assert units.to_mm(50, "um") == pytest.approx(0.05)
    assert units.from_mm(25.4, "in") == pytest.approx(1.0)
    with pytest.raises(ValueError):
        units.to_mm(1, "ft")
