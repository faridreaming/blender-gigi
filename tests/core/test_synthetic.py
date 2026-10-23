# SPDX-License-Identifier: GPL-3.0-or-later
"""Generator die sintetis (core/synthetic.py): jawaban benar harus konsisten dengan mesh yang dihasilkan."""

import numpy as np
import pytest

from core import mesh_validate, solid
from core import synthetic as sy

SPECS = {
    "shoulder": sy.DieSpec(),
    "chamfer": sy.DieSpec(finish="chamfer"),
    "shoulder_scallop": sy.DieSpec(scallop_mm=1.0),
    "chamfer_scallop": sy.DieSpec(finish="chamfer", scallop_mm=1.0),
    "undercut": sy.DieSpec(undercut_deg=10.0),
}


@pytest.mark.parametrize("name", sorted(SPECS))
def test_die_is_a_valid_closed_solid(name):
    die = sy.make_die(SPECS[name], seed=3)
    assert mesh_validate.is_watertight(die.mesh)
    s = solid.to_manifold(die.mesh, name)
    assert s.genus() == 0
    assert s.volume() > 0  # normal menghadap keluar


@pytest.mark.parametrize("finish", sy.FINISHES)
def test_margin_row_is_exactly_the_analytic_margin_without_jitter(finish):
    spec = sy.DieSpec(finish=finish, scallop_mm=0.8)
    rows = (12, 8, 24, 10)
    die = sy.make_die(spec, rows=rows, jitter=0.0, rotate=False, seed=0)
    on_margin = np.isclose(die.vertex_params[:, 1], 1.0)
    assert on_margin.sum() == 128
    expected = sy.margin_points(spec, die.vertex_params[on_margin, 0])
    np.testing.assert_allclose(die.mesh.vertices[on_margin], expected, atol=1e-12)


def test_margin_curve_has_scallop_amplitude():
    die = sy.make_die(sy.DieSpec(scallop_mm=1.2, margin_z_mm=0.5), rotate=False)
    z = die.margin_curve(4096)[:, 2]
    assert z.max() == pytest.approx(0.5 + 1.2, abs=1e-6)
    assert z.min() == pytest.approx(0.5 - 1.2, abs=1e-6)


def test_jittered_vertices_stay_on_the_root_ellipse_and_off_the_grid():
    spec = sy.DieSpec(scallop_mm=1.0)
    die = sy.make_die(spec, jitter=0.45, rotate=False, seed=7)
    v, t = die.mesh.vertices, die.vertex_params[:, 1]
    root = (t > 0) & (t < 1)
    a, b = spec.radius_x_mm, spec.radius_y_mm
    np.testing.assert_allclose((v[root, 0] / a) ** 2 + (v[root, 1] / b) ** 2, 1.0, atol=1e-12)
    assert np.all(v[root, 2] <= sy.margin_z(spec, die.vertex_params[root, 0]) + 1e-12)
    # Dengan jitter, hampir tidak ada vertex yang jatuh tepat di margin.
    distance = sy.distance_to_polyline(v, die.margin_curve(8192))
    assert np.mean(distance < 1e-3) < 0.01


@pytest.mark.parametrize("finish", sy.FINISHES)
def test_margin_is_a_right_angle_crease(finish):
    """Akar vertikal bertemu shoulder horizontal (atau busur chamfer yang bertangen horizontal) di margin."""
    die = sy.make_die(sy.DieSpec(finish=finish), rows=(12, 16, 24, 10), jitter=0.0, rotate=False)
    theta = np.linspace(0, 2 * np.pi, 64, endpoint=False)
    below = sy.surface_normals(die.spec, theta, np.full_like(theta, 0.999))
    above = sy.surface_normals(die.spec, theta, np.full_like(theta, 1.001))
    angle = np.degrees(np.arccos(np.clip(np.sum(below * above, axis=1), -1, 1)))
    np.testing.assert_allclose(angle, 90.0, atol=0.5)


def test_chamfer_profile_ends_at_finish_width():
    spec = sy.DieSpec(finish="chamfer", finish_width_mm=0.8)
    theta = np.linspace(0, 2 * np.pi, 32, endpoint=False)
    start = sy.surface_points(spec, theta, np.full_like(theta, 1.0))
    end = sy.surface_points(spec, theta, np.full_like(theta, 2.0))
    mid = sy.surface_points(spec, theta, np.full_like(theta, 1.5))
    np.testing.assert_allclose(end[:, 2] - start[:, 2], 0.8, atol=1e-12)
    # Titik tengah busur berjarak w dari pusat busur (d = 0, u = w): titik margin dinaikkan w.
    center = start.copy()
    center[:, 2] += 0.8
    np.testing.assert_allclose(np.linalg.norm(mid - center, axis=1), 0.8, atol=1e-12)


def test_noise_follows_requested_sigma():
    clean = sy.make_die(sy.DieSpec(), rotate=False, seed=11)
    noisy = sy.make_die(sy.DieSpec(), rotate=False, seed=11, noise_sigma_mm=0.03)
    normals = sy.vertex_normals(clean.mesh.vertices, clean.mesh.faces)
    offset = np.sum((noisy.mesh.vertices - clean.mesh.vertices) * normals, axis=1)
    assert abs(offset.mean()) < 0.002
    assert offset.std() == pytest.approx(0.03, rel=0.05)
    tangential = (noisy.mesh.vertices - clean.mesh.vertices) - offset[:, None] * normals
    assert np.abs(tangential).max() < 1e-12


def test_rotation_is_rigid_and_axis_follows_it():
    flat = sy.make_die(sy.DieSpec(), rotate=False, seed=5)
    turned = sy.make_die(sy.DieSpec(), rotate=True, seed=5)
    r = turned.rotation
    np.testing.assert_allclose(r @ r.T, np.eye(3), atol=1e-12)
    assert np.linalg.det(r) == pytest.approx(1.0)
    np.testing.assert_allclose(turned.mesh.vertices, flat.mesh.vertices @ r.T, atol=1e-12)
    np.testing.assert_allclose(turned.insertion_axis, r[:, 2], atol=1e-12)
    np.testing.assert_allclose(turned.margin_curve(256), flat.margin_curve(256) @ r.T, atol=1e-12)


def test_same_seed_same_die_different_seed_different_die():
    a = sy.make_die(sy.DieSpec(), seed=1, noise_sigma_mm=0.01)
    b = sy.make_die(sy.DieSpec(), seed=1, noise_sigma_mm=0.01)
    c = sy.make_die(sy.DieSpec(), seed=2, noise_sigma_mm=0.01)
    np.testing.assert_array_equal(a.mesh.vertices, b.mesh.vertices)
    assert not np.allclose(a.mesh.vertices, c.mesh.vertices)


def _face_normals(die):
    corners = die.mesh.vertices[die.mesh.faces]
    n = np.cross(corners[:, 1] - corners[:, 0], corners[:, 2] - corners[:, 0])
    return n / np.linalg.norm(n, axis=1, keepdims=True)


def test_undercut_truth_matches_mesh_normals():
    die = sy.make_die(sy.DieSpec(undercut_deg=10.0), n_theta=256, rows=(12, 8, 48, 10), jitter=0.3, seed=4)
    truth = die.undercut_faces()
    mesh_says = die.prep_faces() & (_face_normals(die) @ die.insertion_axis < 0)
    iou = np.sum(truth & mesh_says) / np.sum(truth | mesh_says)
    assert truth.sum() > 100
    assert iou > 0.9
    # Undercut hanya di sektor yang ditentukan (pusat 0 derajat, setengah lebar 40 derajat).
    theta = np.angle(np.exp(1j * die.face_params[truth, 0]))
    assert np.all(np.abs(np.degrees(theta)) < 40.0)


@pytest.mark.parametrize("name", ["shoulder", "chamfer_scallop"])
def test_no_undercut_without_undercut_sector(name):
    assert not sy.make_die(SPECS[name], seed=9).undercut_faces().any()
    # Tanpa jitter, normal face mesh di dinding juga searah sumbu. Dengan jitter, segitiga yang miring bisa
    # menyimpang lebih dari sudut taper (6 derajat), jadi algoritma undercut nanti tidak boleh hanya
    # mengandalkan tanda normal face mentah.
    die = sy.make_die(SPECS[name], jitter=0.0, seed=9)
    wall = (die.face_params[:, 1] > 2.05) & (die.face_params[:, 1] < 2.95)
    assert np.all(_face_normals(die)[wall] @ die.insertion_axis > 0)


def test_distance_to_polyline_matches_brute_force():
    rng = np.random.default_rng(0)
    curve = rng.normal(size=(20, 3))
    points = rng.normal(size=(50, 3))
    fine = np.concatenate([a + np.linspace(0, 1, 2001)[:, None] * (b - a)
                           for a, b in zip(curve, np.roll(curve, -1, axis=0))])
    brute = np.min(np.linalg.norm(points[:, None] - fine[None], axis=2), axis=1)
    np.testing.assert_allclose(sy.distance_to_polyline(points, curve, chunk=7), brute, atol=1e-3)
    assert sy.distance_to_polyline(curve[3:4], curve)[0] == pytest.approx(0.0, abs=1e-12)


@pytest.mark.parametrize(
    "kwargs",
    [{"finish": "bevel"}, {"taper_deg": 50}, {"radius_y_mm": 0}, {"finish_width_mm": 3.5}, {"scallop_mm": 6.0}],
)
def test_invalid_specs_are_rejected(kwargs):
    with pytest.raises(ValueError):
        sy.DieSpec(**kwargs)


def test_invalid_jitter_is_rejected():
    with pytest.raises(ValueError):
        sy.make_die(sy.DieSpec(), jitter=0.5)
