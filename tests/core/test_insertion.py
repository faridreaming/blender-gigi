# SPDX-License-Identifier: GPL-3.0-or-later
"""Sumbu insersi, peta undercut, dan block-out (core/insertion.py) terhadap die sintetis (core/synthetic.py)."""

import numpy as np
import pytest

from core import insertion, synthetic

AXIS_TOL_DEG = 1.0  # ambang uji
UNDERCUT_IOU_MIN = 0.7  # ambang uji
SHADOWED_MARGIN = dict(finish_width_mm=0.6, undercut_deg=14.0, undercut_center_deg=120.0, undercut_halfwidth_deg=30.0)


def _context(spec, noise=0.0, seed=0, rotate=True):
    die = synthetic.make_die(spec, noise_sigma_mm=noise, rotate=rotate, seed=seed)
    return die, insertion.insertion_context(die.mesh, die.margin_curve(1024))


def _angle(a, b):
    return float(np.degrees(np.arccos(np.clip(np.dot(a, b), -1, 1))))


@pytest.mark.parametrize("finish", synthetic.FINISHES)
@pytest.mark.parametrize("noise", [0.0, 0.03])
def test_default_axis_is_the_true_axis_without_undercut(finish, noise):
    die, ctx = _context(synthetic.DieSpec(finish=finish, scallop_mm=1.0), noise, seed=4)
    result = insertion.default_axis(ctx)
    assert _angle(result.axis, die.insertion_axis) < AXIS_TOL_DEG
    assert not result.doubtful, result.reasons
    assert not result.map.undercut_faces.any()


def test_prep_region_matches_the_analytic_preparation():
    die, ctx = _context(synthetic.DieSpec(scallop_mm=1.0))
    truth = die.prep_faces()
    assert (ctx.region.faces & ~truth).sum() == 0  # tidak ada face akar yang masuk preparasi
    assert ctx.region.faces.sum() / truth.sum() > 0.9  # hanya pita di sekitar margin yang hilang


@pytest.mark.parametrize("noise", [0.0, 0.01])
def test_undercut_sector_matches_the_analytic_sector(noise):
    spec = synthetic.DieSpec(undercut_deg=8.0, undercut_center_deg=90.0)
    die, ctx = _context(spec, noise, seed=2)
    umap = insertion.undercut_map(ctx, die.insertion_axis)
    truth = die.undercut_faces()
    iou = (umap.undercut_faces & truth).sum() / (umap.undercut_faces | truth).sum()
    assert iou >= UNDERCUT_IOU_MIN
    vp = die.vertex_params
    prep = ctx.region.vertices & (vp[:, 1] > 1) & (vp[:, 1] < 3.999)
    err = np.abs(umap.vertex_depth[prep] - synthetic.undercut_depth_truth(spec, vp[prep, 0], vp[prep, 1]))
    assert err.mean() < 0.01 and np.percentile(err, 95) < 0.05


def test_depth_truth_is_zero_without_undercut():
    spec = synthetic.DieSpec(scallop_mm=1.0)
    theta = np.linspace(0, 2 * np.pi, 90)
    for t in (1.0, 1.5, 2.5, 3.5):
        assert synthetic.undercut_depth_truth(spec, theta, np.full_like(theta, t)).max() == 0.0


def test_shadowed_margin_is_flagged_and_the_view_target_is_the_axis():
    spec = synthetic.DieSpec(**SHADOWED_MARGIN)
    theta = np.linspace(0, 2 * np.pi, 360, endpoint=False)
    assert synthetic.undercut_depth_truth(spec, theta, np.ones_like(theta)).max() > 0.05  # margin benar terbayang
    die, ctx = _context(spec, seed=1)
    doubtful, reasons, umap = insertion.check_axis(ctx, die.insertion_axis)
    assert doubtful and reasons[0][0] == "margin line lies in an undercut"
    assert umap.margin_depth.max() > 0.05


def test_strongly_tilted_axis_puts_the_margin_in_an_undercut():
    die, ctx = _context(synthetic.DieSpec(), seed=3)
    u, _ = insertion._frame(die.insertion_axis)
    tilted = np.cos(np.radians(25)) * die.insertion_axis + np.sin(np.radians(25)) * u
    doubtful, reasons, _ = insertion.check_axis(ctx, tilted)
    assert doubtful and "margin line lies in an undercut" in [name for name, _ in reasons]
    assert not insertion.check_axis(ctx, die.insertion_axis)[0]


def test_separate_near_optimal_directions_are_reported(monkeypatch):
    """Logika kandidat sumbu lain: dua lembah terpisah dengan luas membelakangi yang hampir sama."""
    die, ctx = _context(synthetic.DieSpec(), seed=0, rotate=False)
    u, v = insertion._frame(ctx.start_axis)

    def two_valleys(context, directions):
        a = np.degrees(np.arctan2(directions @ u, directions @ ctx.start_axis))
        return np.minimum(np.abs(a - 12.0), np.abs(a + 12.0)) * 10.0 + 0.1 * np.abs(directions @ v) * 100

    monkeypatch.setattr(insertion, "back_facing_area", two_valleys)
    result = insertion.default_axis(ctx)
    assert result.doubtful
    assert "another axis is almost as good" in [name for name, _ in result.reasons]
    assert len(result.alternatives) == 1
    assert _angle(result.alternatives[0], result.axis) > 20


@pytest.mark.parametrize("noise", [0.0, 0.03])
def test_block_out_leaves_no_shadow_outside_the_free_zone(noise):
    spec = synthetic.DieSpec(scallop_mm=1.0, undercut_deg=8.0, undercut_center_deg=90.0)
    die, ctx = _context(spec, noise, seed=5)
    blocked = insertion.block_out(ctx, die.insertion_axis, free_zone_mm=0.1)
    assert blocked.moved.any()
    assert insertion.residual_shadow(ctx, blocked) == 0.0
    near = insertion.cKDTree(ctx.margin).query(ctx.vertices)[0] <= 0.1
    assert not (blocked.moved & near).any()
    assert np.allclose(blocked.mesh.vertices[~blocked.moved], ctx.vertices[~blocked.moved])


def test_block_out_moves_only_perpendicular_to_the_axis():
    spec = synthetic.DieSpec(undercut_deg=8.0, undercut_center_deg=90.0)
    die, ctx = _context(spec, seed=6)
    blocked = insertion.block_out(ctx, die.insertion_axis, free_zone_mm=0.1)
    delta = blocked.mesh.vertices - ctx.vertices
    assert np.abs(delta @ die.insertion_axis).max() < 1e-9


def test_no_block_out_without_undercut_on_a_clean_die():
    die, ctx = _context(synthetic.DieSpec(scallop_mm=1.0), seed=7)
    assert not insertion.block_out(ctx, die.insertion_axis, free_zone_mm=0.1).moved.any()


def test_negative_free_zone_is_rejected():
    die, ctx = _context(synthetic.DieSpec(), seed=0)
    with pytest.raises(insertion.InsertionError):
        insertion.block_out(ctx, die.insertion_axis, free_zone_mm=-0.1)
