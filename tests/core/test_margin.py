# SPDX-License-Identifier: GPL-3.0-or-later
"""Margin semi-otomatis (core/margin.py) diukur terhadap margin analitis die sintetis (core/synthetic.py)."""

import numpy as np
import pytest

from core import geometry, margin, synthetic
from core.mesh_data import MeshData

CRITERION_MEDIAN_MM = 0.050  # docs/PHASE2.md §7


def click_near(die: synthetic.SyntheticDie, theta: float, offset_mm: float = 0.15, seed: int = 0) -> np.ndarray:
    point = synthetic.margin_points(die.spec, np.array([theta]))[0] @ die.rotation.T
    return point + np.random.default_rng(seed).normal(0, offset_mm, 3)


def deviation(die, result, samples=1024):
    return margin.margin_deviation(result.curve.sample(samples), die.margin_curve(4096))


# Geometri dasar -------------------------------------------------------------------------------------

def test_closest_point_on_triangles_matches_brute_force():
    rng = np.random.default_rng(1)
    tri = rng.normal(size=(3, 3))
    points = rng.normal(size=(300, 3)) * 2
    got = geometry.closest_point_on_triangles(points, *[np.repeat(tri[i:i + 1], len(points), 0) for i in range(3)])
    u, v = np.meshgrid(np.linspace(0, 1, 301), np.linspace(0, 1, 301))
    keep = u + v <= 1
    dense = tri[0] + u[keep, None] * (tri[1] - tri[0]) + v[keep, None] * (tri[2] - tri[0])
    brute = np.min(np.linalg.norm(points[:, None] - dense[None], axis=2), axis=1)
    np.testing.assert_allclose(np.linalg.norm(got - points, axis=1), brute, atol=5e-3)


def test_mesh_projector_puts_points_on_the_surface():
    die = synthetic.make_die(synthetic.DieSpec(), rotate=False, seed=0)
    projector = geometry.MeshProjector(die.mesh)
    points = die.mesh.vertices[::37] + np.random.default_rng(2).normal(0, 0.2, (len(die.mesh.vertices[::37]), 3))
    projected, faces, dist = projector.closest(points)
    np.testing.assert_allclose(np.linalg.norm(projected - points, axis=1), dist)
    again, _, dist2 = projector.closest(projected)
    assert dist2.max() < 1e-9  # titik di permukaan tetap di tempat


# Skor crease dan jalur ------------------------------------------------------------------------------

def test_crease_score_is_high_at_the_margin_and_low_on_concave_corner():
    spec = synthetic.DieSpec()
    die = synthetic.make_die(spec, jitter=0.0, rotate=False, seed=0)
    v = die.mesh.vertices
    normals = geometry.vertex_normals(v, die.mesh.faces)
    score, convexity, _ = margin.crease_score(v, normals, 0.35)
    t = die.vertex_params[:, 1]
    at_margin = np.isclose(t, 1.0)
    inner_corner = np.isclose(t, 2.0)  # sudut dalam shoulder (cekung)
    flat_wall = (t > 2.3) & (t < 2.7)
    assert np.median(score[at_margin]) > 0.8
    assert np.median(convexity[at_margin]) < 0
    assert np.median(score[inner_corner]) < 0.2
    assert np.median(score[flat_wall]) < 0.1


def test_closed_path_goes_around_the_die_not_a_tiny_triangle():
    """Regresi: seed yang y-nya -1e-17 dulu menghasilkan 'lingkaran' 3 vertex."""
    die = synthetic.make_die(synthetic.DieSpec(), noise_sigma_mm=0.01, seed=0)
    result = margin.detect_margin(die.mesh, click_near(die, 1.0))
    loop = die.mesh.vertices[result.path_vertices]
    length = np.sum(np.linalg.norm(np.roll(loop, -1, 0) - loop, axis=1))
    truth = die.margin_curve(4096)
    truth_length = np.sum(np.linalg.norm(np.roll(truth, -1, 0) - truth, axis=1))
    assert len(result.path_vertices) > 50
    assert 0.9 * truth_length < length < 1.3 * truth_length


# Akurasi terhadap jawaban benar -----------------------------------------------------------------------

@pytest.mark.parametrize("noise_um", [0, 10, 30])
@pytest.mark.parametrize("scallop", [0.0, 1.0])
@pytest.mark.parametrize("finish", synthetic.FINISHES)
def test_margin_accuracy_meets_phase2_criterion(finish, scallop, noise_um):
    die = synthetic.make_die(synthetic.DieSpec(finish=finish, scallop_mm=scallop),
                             noise_sigma_mm=noise_um / 1000, rotate=True, seed=0)
    dev = deviation(die, margin.detect_margin(die.mesh, click_near(die, 2.0)))
    assert dev["median"] <= CRITERION_MEDIAN_MM, dev
    assert dev["coverage_p95"] <= 0.15, dev  # kurva menutupi seluruh margin (ambang uji)


def test_rotation_does_not_change_accuracy():
    spec = synthetic.DieSpec(finish="chamfer", scallop_mm=1.0)
    flat = synthetic.make_die(spec, noise_sigma_mm=0.01, rotate=False, seed=4)
    turned = synthetic.make_die(spec, noise_sigma_mm=0.01, rotate=True, seed=4)
    a = deviation(flat, margin.detect_margin(flat.mesh, click_near(flat, 0.5)))
    b = deviation(turned, margin.detect_margin(turned.mesh, click_near(turned, 0.5)))
    assert abs(a["median"] - b["median"]) < 0.005


def test_click_position_does_not_change_the_curve():
    die = synthetic.make_die(synthetic.DieSpec(scallop_mm=1.0), noise_sigma_mm=0.01, seed=6)
    curves = [margin.detect_margin(die.mesh, click_near(die, theta, seed=k)).curve.sample(512)
              for k, theta in enumerate((0.3, 2.0, 4.4))]
    for other in curves[1:]:
        assert np.max(synthetic.distance_to_polyline(other, curves[0])) < 0.05


# Pengaman: tidak boleh gagal diam-diam --------------------------------------------------------------

NOISY_CASES = [(f, s, seed) for f in synthetic.FINISHES for s in (0.0, 1.0) for seed in (0, 1)]


@pytest.mark.parametrize("finish, scallop, seed", NOISY_CASES)
def test_every_90um_case_stops_with_the_noise_warning(finish, scallop, seed):
    die = synthetic.make_die(synthetic.DieSpec(finish=finish, scallop_mm=scallop), noise_sigma_mm=0.090, seed=seed)
    with pytest.raises(margin.MarginNoiseError, match="gambar margin manual") as info:
        margin.detect_margin(die.mesh, click_near(die, 2.0, seed=seed))
    assert info.value.sigma_mm > info.value.limit_mm == pytest.approx(0.060)


@pytest.mark.parametrize("finish, scallop, seed", NOISY_CASES)
def test_without_noise_guard_bad_90um_curves_are_rejected_or_flagged(finish, scallop, seed):
    """Lapis kedua: dengan pengaman derau dimatikan, kurva yang melenceng harus ditolak pemeriksaan kewajaran
    atau punya segmen merah ("need review")."""
    die = synthetic.make_die(synthetic.DieSpec(finish=finish, scallop_mm=scallop), noise_sigma_mm=0.090, seed=seed)
    params = margin.MarginParams(check_noise=False)
    try:
        result = margin.detect_margin(die.mesh, click_near(die, 2.0, seed=seed), params)
    except margin.MarginError:
        return
    dev = deviation(die, result)
    bad = not (dev["median"] <= CRITERION_MEDIAN_MM and dev["coverage_p95"] <= 0.15)
    assert not bad or result.review.count > 0, f"kurva buruk tanpa pesan dan tanpa segmen merah: {dev}"


def test_noise_estimate_is_reported_on_success():
    die = synthetic.make_die(synthetic.DieSpec(), noise_sigma_mm=0.03, seed=1)
    result = margin.detect_margin(die.mesh, click_near(die, 1.0))
    assert 0.025 < result.noise_sigma_mm < 0.040
    assert set(result.metrics) == {"ok_fraction", "click_distance", "gap_ratio", "girth_ratio", "out_of_plane_ratio"}


@pytest.mark.parametrize(
    "change, name",
    [
        ({"ok_fraction": 0.5}, "too few points on the crease"),
        ({"click_distance": 2.0}, "curve far from the clicked point"),
        ({"gap_ratio": 4.0}, "gap in the curve"),
        ({"girth_ratio": 0.6}, "curve length does not match the die"),
        ({"girth_ratio": 1.4}, "curve length does not match the die"),
        ({"out_of_plane_ratio": 0.5}, "curve leaves the margin plane"),
    ],
)
def test_each_plausibility_check_fires(change, name):
    good = {"ok_fraction": 1.0, "click_distance": 0.1, "gap_ratio": 1.0, "girth_ratio": 1.0, "out_of_plane_ratio": 0.1}
    assert margin.plausibility_problems(good, margin.MarginParams()) == []
    problems = margin.plausibility_problems({**good, **change}, margin.MarginParams())
    assert [n for n, _ in problems] == [name]


def test_sparse_points_raise_instead_of_crashing():
    sparse = np.array([[0, 0, 0], [10, 0, 0], [10, 10, 0], [0, 10, 0]], dtype=float)
    with pytest.raises(margin.MarginPlausibilityError, match="terlalu jarang") as info:
        margin._smooth_closed(sparse, 0.4)
    assert info.value.failed == ["gap in the curve"]


def test_flat_surface_has_no_margin():
    x, y = np.meshgrid(np.linspace(0, 10, 30), np.linspace(0, 10, 30))
    vertices = np.stack([x.ravel(), y.ravel(), np.zeros(x.size)], axis=1)
    idx = np.arange(900).reshape(30, 30)
    faces = np.concatenate([
        np.stack([idx[:-1, :-1].ravel(), idx[:-1, 1:].ravel(), idx[1:, 1:].ravel()], 1),
        np.stack([idx[:-1, :-1].ravel(), idx[1:, 1:].ravel(), idx[1:, :-1].ravel()], 1),
    ])
    with pytest.raises(margin.MarginError):
        margin.detect_margin(MeshData(vertices, faces), [5.0, 5.0, 0.0])


# Kurva yang bisa diedit -----------------------------------------------------------------------------

@pytest.fixture(scope="module")
def detected():
    die = synthetic.make_die(synthetic.DieSpec(), noise_sigma_mm=0.01, seed=8)
    return die, margin.detect_margin(die.mesh, click_near(die, 1.0))


def test_curve_passes_through_its_control_points(detected):
    _, result = detected
    curve = result.curve
    dense = curve.sample(4096)
    assert np.max(synthetic.distance_to_polyline(curve.control_points, dense)) < 0.01


def test_move_point_projects_onto_the_surface(detected):
    die, result = detected
    curve = margin.MarginCurve(result.curve.control_points.copy(), result.curve.projector)
    target = curve.control_points[3] + np.array([0.0, 0.0, 0.4]) @ die.rotation.T
    curve.move_point(3, target)
    _, _, dist = curve.projector.closest(curve.control_points[3:4])
    assert dist[0] < 1e-9
    assert np.linalg.norm(curve.control_points[3] - target) < 0.4


def test_delete_point_and_minimum_count(detected):
    _, result = detected
    curve = margin.MarginCurve(result.curve.control_points.copy(), result.curve.projector)
    count = len(curve.control_points)
    curve.delete_point(0)
    assert len(curve.control_points) == count - 1
    small = margin.MarginCurve(curve.control_points[:4], curve.projector)
    with pytest.raises(margin.MarginError):
        small.delete_point(0)


def test_apply_edit_keeps_untouched_points_and_projects_moved_ones(detected):
    die, result = detected
    curve = margin.MarginCurve(result.curve.control_points.copy(), result.curve.projector)
    original = curve.control_points.copy()
    edited = np.delete(original, 5, axis=0)
    edited[10] += np.array([0.3, 0.0, 0.0]) @ die.rotation.T
    stats = curve.apply_edit(edited)
    assert stats == {"moved": 1, "kept": len(original) - 2, "removed": 1}
    untouched = np.ones(len(edited), dtype=bool)
    untouched[10] = False
    np.testing.assert_array_equal(curve.control_points[untouched], edited[untouched])
    _, _, dist = curve.projector.closest(curve.control_points[10:11])
    assert dist[0] < 1e-9


def test_smoothing_does_not_shrink_a_circle():
    theta = np.linspace(0, 2 * np.pi, 200, endpoint=False)
    circle = np.stack([4.5 * np.cos(theta), 4.5 * np.sin(theta), np.zeros_like(theta)], axis=1)
    smoothed = margin._smooth_closed(circle, 0.8)
    shrink = 4.5 - np.linalg.norm(smoothed[:, :2], axis=1)
    # Rata-rata Gauss biasa menyusutkan sekitar sigma^2 * kelengkungan / 2 = 0,64 / 9 = 71 um.
    assert np.abs(shrink).max() < 0.001


def test_margin_deviation_of_offset_circle():
    theta = np.linspace(0, 2 * np.pi, 2000, endpoint=False)
    truth = np.stack([5 * np.cos(theta), 5 * np.sin(theta), np.zeros_like(theta)], axis=1)
    curve = truth * (5.03 / 5)
    dev = margin.margin_deviation(curve, truth)
    assert dev["median"] == pytest.approx(0.03, abs=1e-4)
    assert dev["coverage_max"] == pytest.approx(0.03, abs=1e-4)


# Scallop dalam (lengkungan CEJ anterior) ---------------------------------------------------------------

@pytest.mark.parametrize("finish", synthetic.FINISHES)
def test_deep_cej_scallop_is_not_rejected_by_the_length_check(finish):
    """Puncak-lembah 3,5 mm (Gallucci dkk. 2004, insisif sentral mesial 3,46 mm): metrik panjang 3D lama
    menolaknya sebagai "panjang kurva tidak cocok dengan die"."""
    die = synthetic.make_die(synthetic.DieSpec(finish=finish, scallop_mm=1.75), noise_sigma_mm=0.01, seed=0)
    result = margin.detect_margin(die.mesh, click_near(die, 1.0))
    assert 0.95 < result.metrics["girth_ratio"] < 1.02
    assert deviation(die, result)["median"] <= CRITERION_MEDIAN_MM


def test_length_ratio_ignores_scallop_height():
    theta = np.linspace(0, 2 * np.pi, 200, endpoint=False)
    ring = np.stack([5 * np.cos(theta), 4 * np.sin(theta), np.zeros_like(theta)], axis=1)
    wall = np.concatenate([ring + [0, 0, z] for z in np.linspace(-3, 3, 13)])
    flat = margin.plausibility_metrics(ring, wall, ring[0], 1.0, 0.16)
    wavy = ring + np.stack([0 * theta, 0 * theta, 1.75 * np.cos(2 * theta)], axis=1)
    deep = margin.plausibility_metrics(wavy, wall, wavy[0], 1.0, 0.16)
    assert deep["girth_ratio"] == pytest.approx(flat["girth_ratio"], abs=1e-6)
    assert flat["girth_ratio"] == pytest.approx(1.0, abs=0.01)


# Margin gambar manual ------------------------------------------------------------------------------------

def test_drawn_margin_projects_clicks_and_closes_the_curve():
    die = synthetic.make_die(synthetic.DieSpec(scallop_mm=1.0), noise_sigma_mm=0.01, seed=4)
    clicks = die.margin_curve(12) + np.random.default_rng(0).normal(0, 0.05, (12, 3))
    curve = margin.draw_margin(die.mesh, clicks)
    assert len(curve.control_points) == 12
    _, _, dist = geometry.MeshProjector(die.mesh).closest(curve.control_points)
    assert dist.max() < 1e-6
    sample = curve.sample(256)
    assert np.linalg.norm(sample[-1] - sample[0]) < 2 * np.linalg.norm(sample[1] - sample[0])
    assert np.median(synthetic.distance_to_polyline(sample, die.margin_curve(4096))) < 0.3


def test_drawn_margin_drops_double_clicks_and_the_closing_click():
    die = synthetic.make_die(synthetic.DieSpec(), rotate=False, seed=1)
    clicks = die.margin_curve(6)
    with_repeats = np.vstack([clicks[:3], clicks[2:3] + 0.01, clicks[3:], clicks[:1] + 0.01])
    assert len(margin.draw_margin(die.mesh, with_repeats).control_points) == 6


def test_drawn_margin_needs_four_points():
    die = synthetic.make_die(synthetic.DieSpec(), rotate=False, seed=1)
    with pytest.raises(margin.MarginError, match="minimal 4"):
        margin.draw_margin(die.mesh, die.margin_curve(3))
    with pytest.raises(margin.MarginError):
        margin.draw_margin(die.mesh, np.empty((0, 3)))


def test_drawn_margin_is_edited_like_a_detected_one():
    die = synthetic.make_die(synthetic.DieSpec(), rotate=False, seed=1)
    curve = margin.draw_margin(die.mesh, die.margin_curve(8))
    edited = np.delete(curve.control_points, 1, axis=0)
    edited[3] += [0.4, 0.0, 0.0]
    assert curve.apply_edit(edited) == {"moved": 1, "kept": 6, "removed": 1}


# Titik jauh di crease, penanda segmen meragukan ----------------------------------------------------------

def test_far_point_stays_on_the_crease_for_a_small_deep_scallop():
    """Regresi set uji pertama (sekarang tuning3): insisif sentral, puncak proksimal terpotong sekitar 0,7 mm
    karena titik jauh f jatuh di dinding aksial di atas puncak."""
    spec = synthetic.DieSpec(finish="chamfer", radius_x_mm=3.6, radius_y_mm=3.2, prep_height_mm=5.5, taper_deg=8.0,
                             finish_width_mm=0.8, scallop_mm=1.6)
    die = synthetic.make_die(spec, noise_sigma_mm=0.0, rotate=True, seed=1)
    rng = np.random.default_rng(10_001)
    theta = rng.uniform(0, 2 * np.pi)
    click = synthetic.margin_points(spec, np.array([theta]))[0] @ die.rotation.T + rng.normal(0, 0.15, 3)
    dev = deviation(die, margin.detect_margin(die.mesh, click))
    assert dev["median"] <= CRITERION_MEDIAN_MM and dev["coverage_p95"] <= 0.15, dev


def test_closed_runs_wrap_around():
    mask = np.array([1, 1, 0, 0, 1, 0, 1, 1], dtype=bool)
    assert margin._closed_runs(mask) == [(4, 5), (6, 10)]
    assert margin._closed_runs(np.zeros(4, bool)) == []
    assert margin._closed_runs(np.ones(3, bool)) == [(0, 3)]


def _clean_detection():
    die = synthetic.make_die(synthetic.DieSpec(scallop_mm=1.0), noise_sigma_mm=0.0, rotate=False, seed=2)
    return die, margin.detect_margin(die.mesh, click_near(die, 0.7))


def test_clean_detection_has_no_review_segments():
    _, result = _clean_detection()
    assert result.review.count == 0, result.review.segments
    assert len(result.review.samples) == margin.REVIEW_SAMPLES


def test_curve_pushed_off_the_crease_is_flagged_where_it_moved():
    die, result = _clean_detection()
    curve = result.curve
    moved = curve.control_points.copy()
    moved[5:8] += [0.0, 0.0, 0.35]  # tiga titik kontrol 0,35 mm di atas margin
    curve.control_points = moved
    review = margin.review_curve(curve, margin.ReviewContext.from_mesh(die.mesh))
    assert review.count >= 1
    near = synthetic.distance_to_polyline(review.samples[review.flagged], moved[5:8])
    assert np.median(near) < 1.0  # segmen merah berada di bagian yang digeser


def test_coarse_drawn_margin_is_flagged_between_clicks():
    die = synthetic.make_die(synthetic.DieSpec(scallop_mm=1.0), noise_sigma_mm=0.0, rotate=False, seed=2)
    curve = margin.draw_margin(die.mesh, die.margin_curve(5))
    review = margin.review_curve(curve, margin.ReviewContext.from_mesh(die.mesh))
    assert review.count >= 1
