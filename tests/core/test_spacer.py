# SPDX-License-Identifier: GPL-3.0-or-later
"""Jarak geodesik (core/geodesic.py) dan spacer cement gap (core/spacer.py) terhadap jawaban analitis."""

from pathlib import Path

import numpy as np
import pytest
from scipy.spatial import cKDTree

from core import geodesic, insertion, material_db, spacer, synthetic
from core.mesh_data import MeshData

ROOT = Path(__file__).resolve().parents[2]
PRESET = material_db.load_material_preset(ROOT / "data" / "materials" / "zircad_prime.json")


def _cylinder(radius, height, n_phi, n_z, jitter, seed):
    rng = np.random.default_rng(seed)
    phi = np.arange(n_phi) * 2 * np.pi / n_phi
    z = np.linspace(-height / 2, height / 2, n_z)
    zz, pp = np.meshgrid(z, phi, indexing="ij")
    if jitter:
        pp = pp + rng.uniform(-jitter, jitter, pp.shape) * 2 * np.pi / n_phi
        zz[1:-1] = zz[1:-1] + rng.uniform(-jitter, jitter, zz[1:-1].shape) * (z[1] - z[0])
    v = np.stack([radius * np.cos(pp.ravel()), radius * np.sin(pp.ravel()), zz.ravel()], axis=1)
    faces = []
    for i in range(n_z - 1):
        for j in range(n_phi):
            a, b = i * n_phi + j, i * n_phi + (j + 1) % n_phi
            c, d = (i + 1) * n_phi + (j + 1) % n_phi, (i + 1) * n_phi + j
            faces += [(a, b, c), (a, c, d)] if rng.integers(2) else [(a, b, d), (b, c, d)]
    return MeshData(v, np.array(faces)), pp.ravel(), zz.ravel()


def _cylinder_case(jitter, method, radius=4.5, amplitude=1.0):
    mesh, phi, z = _cylinder(radius, 8.0, 128, 40, jitter, 1)
    t = np.linspace(0, 2 * np.pi, 4096, endpoint=False)
    curve = np.stack([radius * np.cos(t), radius * np.sin(t), amplitude * np.cos(2 * t)], axis=1)
    above = z > amplitude * np.cos(2 * phi)
    d = geodesic.distance_from_curve(mesh, curve, above, method=method)
    # Jawaban eksak: silinder dibuka menjadi bidang (u = R phi); kurva berulang di u +- 2 pi R.
    u = np.concatenate([radius * t - 2 * np.pi * radius, radius * t, radius * t + 2 * np.pi * radius])
    tree = cKDTree(np.stack([u, np.tile(amplitude * np.cos(2 * t), 3)], axis=1))
    exact, _ = tree.query(np.stack([radius * (phi % (2 * np.pi)), z], axis=1))
    sel = above & (exact < 3.0)
    return d[sel] - exact[sel]


def test_fast_marching_matches_the_unrolled_cylinder():
    regular = _cylinder_case(0.0, "fmm")
    assert np.percentile(np.abs(regular), 95) < 0.02 and np.abs(regular).max() < 0.05
    jittered = _cylinder_case(0.45, "fmm")
    assert np.percentile(np.abs(jittered), 95) < 0.06 and np.abs(jittered).max() < 0.2


def test_graph_distance_never_underestimates_and_is_worse_than_fast_marching():
    graph = _cylinder_case(0.45, "graph")
    assert graph.min() > -0.002  # mesh silinder berfaset sedikit lebih pendek dari silinder mulus
    assert np.percentile(np.abs(graph), 95) > np.percentile(np.abs(_cylinder_case(0.45, "fmm")), 95)


def test_gap_profile_zones():
    p = spacer.SpacerParams(0.06, 1.0, 0.5, 0.01, 0.0)
    d = np.array([0.0, 0.99, 1.0, 1.25, 1.5, 3.0, np.inf])
    np.testing.assert_allclose(spacer.gap_profile(d, p), [0, 0, 0, 0.03, 0.06, 0.06, 0.0])
    step = spacer.SpacerParams(0.06, 1.0, 0.0, 0.01, 0.0)
    np.testing.assert_allclose(spacer.gap_profile(np.array([0.99, 1.0]), step), [0.0, 0.06])


def test_parameters_come_from_the_ivoclar_preset():
    p = spacer.SpacerParams.from_preset(PRESET)
    assert (p.cement_gap_mm, p.from_margin_mm, p.radial_mm, p.axial_mm) == (0.06, 1.0, 0.01, 0.0)
    assert PRESET.get("axial_spacing_um").status == "perlu_kalibrasi"
    assert PRESET.get("cement_gap_transition_mm").status == "perlu_kalibrasi"


def test_negative_parameters_are_rejected():
    with pytest.raises(spacer.SpacerError):
        spacer.SpacerParams(-0.06, 1.0, 0.5, 0.01, 0.0)


def _meridian(spec, t):
    grid = np.linspace(1.0, 3.999, 20001)
    pts = synthetic.surface_points(spec, np.zeros_like(grid), grid)
    s = np.concatenate([[0.0], np.cumsum(np.linalg.norm(np.diff(pts, axis=0), axis=1))])
    return np.interp(t, grid, s)


def _spacer_case(finish, noise=0.0, params=None, seed=0, **overrides):
    spec = synthetic.DieSpec(finish=finish, radius_x_mm=5.0, radius_y_mm=5.0, **overrides)
    die = synthetic.make_die(spec, noise_sigma_mm=noise, rotate=True, seed=seed)
    ctx = insertion.insertion_context(die.mesh, die.margin_curve(1024))
    blocked = insertion.block_out(ctx, die.insertion_axis, 0.1)
    faces = spacer.inner_faces(ctx.vertices, ctx.faces, ctx.region.faces, ctx.region.band_faces, ctx.margin)
    params = params or spacer.SpacerParams.from_preset(PRESET)
    result = spacer.spacer_surface(blocked.mesh, faces, ctx.margin, die.insertion_axis, params)
    return spec, die, result, params


@pytest.mark.parametrize("finish", synthetic.FINISHES)
def test_gap_zones_match_the_analytic_meridian_distance(finish):
    spec, die, result, p = _spacer_case(finish)
    vp = die.vertex_params[result.vertex_index]
    d_true = _meridian(spec, vp[:, 1])
    clear_zero = d_true < p.from_margin_mm - 0.15
    clear_full = (d_true > p.from_margin_mm + p.transition_mm + 0.15) & (d_true < 6.0)
    assert np.all(result.gap_mm[clear_zero] == 0.0)
    np.testing.assert_allclose(result.gap_mm[clear_full], p.cement_gap_mm)
    near = d_true < 3.0
    assert np.percentile(np.abs(result.distance_mm[near] - d_true[near]), 95) < 0.08


def test_radial_spacing_is_applied_in_the_zone_without_cement_gap():
    # Finish 0,4 mm supaya dinding (normal horizontal) sudah mulai di dalam zona tanpa cement gap (1 mm).
    spec, die, result, p = _spacer_case("shoulder", finish_width_mm=0.4)
    vp = die.vertex_params[result.vertex_index]
    zero = result.gap_mm == 0
    n_true = synthetic.surface_normals(spec, vp[:, 0], np.minimum(vp[:, 1], 3.999)) @ die.rotation.T
    h = np.linalg.norm(n_true - (n_true @ result.axis)[:, None] * result.axis, axis=1)
    wall = zero & (h > 0.95)
    offset = np.linalg.norm(result.displacement[wall], axis=1)
    assert wall.sum() > 50
    assert np.percentile(np.abs(offset - p.radial_mm * h[wall]), 95) < 0.001


def test_equal_radial_and_axial_spacing_offsets_along_the_normal():
    p = spacer.SpacerParams(0.0, 1.0, 0.5, 0.02, 0.02)
    _, _, result, _ = _spacer_case("chamfer", params=p)
    np.testing.assert_allclose(np.linalg.norm(result.displacement, axis=1), 0.02, atol=1e-9)


def test_inner_surface_does_not_include_the_root():
    for finish in synthetic.FINISHES:
        spec, die, result, _ = _spacer_case(finish)
        assert (die.vertex_params[result.vertex_index, 1] < 1).sum() == 0


def test_folds_are_only_sliver_triangles_on_a_clean_die():
    _, _, result, _ = _spacer_case("chamfer")
    assert result.folded_faces == result.folded_slivers
