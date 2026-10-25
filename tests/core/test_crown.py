# SPDX-License-Identifier: GPL-3.0-or-later
"""Template parametrik (core/template.py) dan proposal crown berlabuh margin (core/crown.py), PHASE2.md §5.4."""

import numpy as np
import pytest

from core import crown, synthetic, template

ELLIPSOID = np.array([4.0, 4.5, 3.5])


@pytest.mark.parametrize("fdi, kind", [(11, "incisor"), (23, "canine"), (35, "premolar"), (46, "molar"),
                                       (18, "molar"), (42, "incisor")])
def test_fdi_kind(fdi, kind):
    assert template.fdi_kind(fdi) == kind


@pytest.mark.parametrize("fdi", [9, 19, 51, 40, 100])
def test_invalid_fdi_is_rejected(fdi):
    with pytest.raises(ValueError):
        template.fdi_kind(fdi)


@pytest.mark.parametrize("kind", template.KINDS)
@pytest.mark.parametrize("widths", [(9.0, 8.0), (6.0, 8.5)])
def test_template_has_the_requested_widths_and_height(kind, widths):
    p = template.TemplateParams(kind, widths[0], widths[1], 6.0)
    phi = np.linspace(0, 2 * np.pi, 1440, endpoint=False)
    v = np.linspace(0, 1, 801)
    pts = template.template_points(p, phi[:, None], v[None, :]).reshape(-1, 3)
    assert np.ptp(pts[:, 0]) == pytest.approx(widths[0], abs=1e-3)
    assert np.ptp(pts[:, 1]) == pytest.approx(widths[1], abs=1e-3)
    assert pts[:, 2].max() == pytest.approx(6.0, abs=1e-3)


def _die_and_margin(**spec_kw):
    spec = synthetic.DieSpec(**spec_kw)
    die = synthetic.make_die(spec, rotate=True, seed=3)
    margin = die.margin_curve(1024)
    prep_top = crown.prep_top_height(die.mesh.vertices, margin, die.insertion_axis)
    return spec, die, margin, prep_top


def test_cervical_edge_is_the_margin_by_construction():
    spec, die, margin, prep_top = _die_and_margin(scallop_mm=1.0)
    fit = crown.fit_crown(46, margin, die.insertion_axis, die.rotation[:, 0], prep_top)
    s = fit.surface
    assert synthetic.distance_to_polyline(s.frame.to_world(s.border[0]), margin).max() < 1e-9
    np.testing.assert_allclose(s.local[:, 0, :], s.border[2], atol=1e-12)  # permukaan luar mulai di ujung border
    assert crown.flipped_faces(fit.surface) == 0
    assert len(fit.hints) == 2  # tanpa tetangga dan tanpa antagonis: keduanya "perlu dicek"


def _context(spec, die, prep_top, gaps=(0.6, 0.6), clearance=3.6):
    R = die.rotation
    margin_die = synthetic.margin_points(spec, np.linspace(0, 2 * np.pi, 1024, endpoint=False))
    zc = margin_die[:, 2].mean()
    bulge = synthetic.NEIGHBOUR_CONTOUR_ALLOWANCE_MM
    mes = synthetic.Ellipsoid(np.array([margin_die[:, 0].max() + bulge + gaps[0] + 4.0, 0, zc + 2.0]), ELLIPSOID,
                              np.eye(3))
    dis = synthetic.Ellipsoid(np.array([margin_die[:, 0].min() - bulge - gaps[1] - 4.0, 0, zc + 2.0]), ELLIPSOID,
                              np.eye(3))
    ant = synthetic.AntagonistPlane(np.array([0, 0, zc + prep_top + clearance]), np.array([0, 0, -1.0]))
    world = lambda m: synthetic.MeshData(m.vertices @ R.T, m.faces)  # noqa: E731
    return mes, dis, ant, world(mes.mesh()), world(dis.mesh()), world(ant.mesh())


def test_fit_reaches_the_target_contacts_on_exact_surfaces():
    spec, die, margin, prep_top = _die_and_margin()
    mes, dis, ant, m_mesh, d_mesh, a_mesh = _context(spec, die, prep_top, gaps=(1.0, 0.4))
    mesial = crown.mesial_from_neighbors(margin, die.insertion_axis, m_mesh, d_mesh)
    assert np.degrees(np.arccos(np.clip(mesial @ die.rotation[:, 0], -1, 1))) < 0.1
    fit = crown.fit_crown(46, margin, die.insertion_axis, mesial, prep_top, m_mesh, d_mesh, a_mesh)
    v = fit.surface.mesh.vertices @ die.rotation
    p = crown.CrownParams()
    assert abs(mes.signed_distance(v).min() - p.approximal_distance_mm) < 0.006
    assert abs(dis.signed_distance(v).min() - p.approximal_distance_mm) < 0.006
    assert abs(ant.signed_distance(v).min() - p.occlusal_distance_mm) < 0.002
    assert crown.flipped_faces(fit.surface) == 0


def test_too_little_occlusal_space_is_an_explicit_error():
    spec, die, margin, prep_top = _die_and_margin()
    *_, m_mesh, d_mesh, a_mesh = _context(spec, die, prep_top, clearance=2.0)
    with pytest.raises(crown.CrownError, match="occlusal space too narrow"):
        crown.fit_crown(46, margin, die.insertion_axis, die.rotation[:, 0], prep_top, m_mesh, d_mesh, a_mesh)


def test_too_little_mesiodistal_space_is_an_explicit_error():
    spec, die, margin, prep_top = _die_and_margin()
    *_, m_mesh, d_mesh, a_mesh = _context(spec, die, prep_top, gaps=(-1.6, -1.6))
    with pytest.raises(crown.CrownError, match="mesiodistal space too narrow"):
        crown.fit_crown(46, margin, die.insertion_axis, die.rotation[:, 0], prep_top, m_mesh, d_mesh, a_mesh)


def test_margin_must_wind_around_the_axis():
    spec, die, margin, prep_top = _die_and_margin()
    tilted = np.cross(die.insertion_axis, die.rotation[:, 0])  # sumbu tegak lurus sumbu insersi
    with pytest.raises(crown.CrownError, match="tidak melingkari"):
        crown.fit_crown(46, margin, tilted, die.insertion_axis, prep_top)


def test_ellipsoid_signed_distance_matches_known_points():
    e = synthetic.Ellipsoid(np.array([8.0, 0.0, 1.0]), np.array([4.0, 4.5, 3.5]), np.eye(3))
    np.testing.assert_allclose(e.signed_distance(np.array([[3.0, 0, 1.0], [8, 0, 5.5], [8, 6.0, 1.0]])),
                               [1.0, 1.0, 1.5], atol=1e-9)


def test_template_base_can_follow_the_margin_height_per_angle():
    p = template.TemplateParams("molar", 9.0, 8.0, 7.0)
    phi = np.linspace(0, 2 * np.pi, 96, endpoint=False)
    base = 1.5 * np.cos(2 * phi)
    pts = template.template_points(p, phi[:, None], np.linspace(0, 1, 33)[None, :], base_z=base[:, None])
    np.testing.assert_allclose(pts[:, 0, 2], base, atol=1e-12)
    assert np.all(np.diff(pts[:, :20, 2], axis=1) > 0)  # dinding tetap naik di setiap sudut
    with pytest.raises(ValueError, match="di bawah tepi atas dinding"):
        template.template_points(p, phi, 0.0, base_z=p.wall_top_z + 0.1)


@pytest.mark.parametrize("fdi, spec_kw", [
    (41, dict(radius_x_mm=2.8, radius_y_mm=3.0, prep_height_mm=5.0, finish_width_mm=0.7, scallop_mm=1.75)),
    (11, dict(radius_x_mm=3.6, radius_y_mm=3.2, prep_height_mm=5.5, taper_deg=8.0, finish_width_mm=0.8,
              scallop_mm=1.6)),
    (13, dict(radius_x_mm=3.4, radius_y_mm=4.0, prep_height_mm=6.0, taper_deg=5.0, scallop_mm=1.25)),
    (36, dict(prep_height_mm=5.5, scallop_mm=1.75)),
])
def test_deep_scallop_does_not_fold(fdi, spec_kw):
    """Set ukur pertama §5.4: dasar rata dan zona campur sebagai fraksi v melipat permukaan di puncak scallop."""
    spec, die, margin, prep_top = _die_and_margin(**spec_kw)
    fit = crown.fit_crown(fdi, margin, die.insertion_axis, die.rotation[:, 0], prep_top)
    assert crown.non_sliver_folds(fit.surface) == 0
    assert crown.flipped_faces(fit.surface) == 0


def test_cervical_third_rises_from_the_margin_at_the_emergence_angle_then_blends_into_the_template():
    spec, die, margin, prep_top = _die_and_margin(scallop_mm=1.5)
    p = crown.CrownParams()
    fit = crown.fit_crown(46, margin, die.insertion_axis, die.rotation[:, 0], prep_top, params=p)
    s = fit.surface
    base = s.local[:, 0, 2]
    tpl = template.template_points(s.template, s.phi[:, None], s.v[None, :], base_z=base[:, None])
    h = tpl[..., 2] - base[:, None]
    h_c = crown.cervical_height(s.template, s.local[:, 0, :], p)
    np.testing.assert_allclose(s.local[..., 2], tpl[..., 2], atol=1e-12)  # campuran hanya menggeser mendatar
    cervical = h <= h_c[:, None]
    normal = crown.margin_normals(s.local[:, 0, :])
    cone = s.local[:, :1, :2] + (h * np.tan(np.radians(p.emergence_angle_deg)))[..., None] * normal[:, None, :]
    np.testing.assert_allclose(s.local[..., :2][cervical], cone[cervical], atol=1e-12)
    above = h >= h_c[:, None] + p.blend_height_mm
    above[:, -1] = False  # titik tengah oklusal disatukan untuk semua sudut
    np.testing.assert_allclose(s.local[above], tpl[above], atol=1e-12)


@pytest.mark.parametrize("fdi, spec_kw", [
    (41, dict(radius_x_mm=2.8, radius_y_mm=3.0, prep_height_mm=5.0, finish_width_mm=0.7, scallop_mm=1.75)),
    (24, dict(radius_x_mm=4.0, radius_y_mm=3.6, prep_height_mm=4.5, taper_deg=7.0, scallop_mm=1.25)),
])
@pytest.mark.parametrize("angle", [15.0, 19.0])
def test_emergence_angle_parameter_sets_the_first_millimetre(fdi, spec_kw, angle):
    spec, die, margin, prep_top = _die_and_margin(**spec_kw)
    fit = crown.fit_crown(fdi, margin, die.insertion_axis, die.rotation[:, 0], prep_top,
                          params=crown.CrownParams(emergence_angle_deg=angle))
    assert crown.cervical_height(fit.surface.template, fit.surface.local[:, 0, :], crown.CrownParams()).min() > 1.0
    np.testing.assert_allclose(crown.emergence_angles(fit.surface), angle, atol=0.05)
    assert crown.non_sliver_folds(fit.surface) == 0


@pytest.mark.parametrize("alpha", [-5.0, 0.0, 12.0, 20.0])
def test_emergence_angle_of_a_cone(alpha):
    p = template.TemplateParams("molar", 9.0, 8.0, 7.0)
    phi = np.linspace(0, 2 * np.pi, 64, endpoint=False)
    v = np.linspace(0, 1, 65)
    z = np.clip(v / p.v_wall, 0, 1) * 5.0 + 0.3 * np.cos(2 * phi)[:, None]
    r = 4.0 + (z - z[:, :1]) * np.tan(np.radians(alpha))
    local = np.stack([r * np.cos(phi)[:, None], r * np.sin(phi)[:, None], z], axis=-1)
    surface = crown.CrownSurface(None, p, phi, v, local, None)
    np.testing.assert_allclose(crown.emergence_angles(surface), alpha, atol=1e-9)


def test_border_matches_ivo_in_64_sections():
    spec, die, margin, prep_top = _die_and_margin(radius_x_mm=2.8, radius_y_mm=3.0, prep_height_mm=5.0,
                                                  finish_width_mm=0.7, scallop_mm=1.75)
    fit = crown.fit_crown(41, margin, die.insertion_axis, die.rotation[:, 0], prep_top)
    sections = crown.border_sections(fit.surface.border, 64)
    p = crown.CrownParams()
    assert np.abs(sections["horizontal_mm"] - p.border_horizontal_mm).max() < 0.001
    assert sections["horizontal_rise_mm"].max() < 0.001
    assert np.abs(sections["angled_mm"] - p.border_angled_mm).max() < 0.001
    assert np.abs(sections["angle_deg"] - p.border_angle_deg).max() < 0.1


def test_border_that_folds_over_itself_is_an_explicit_error():
    phi = np.linspace(0, 2 * np.pi, crown.N_PHI, endpoint=False)
    radius = 4.0 - 0.6 * (np.abs(np.sin(6 * phi)) ** 8)  # takik tajam: kelengkungan lebih rapat dari lebar border
    ring = np.stack([radius * np.cos(phi), radius * np.sin(phi), 0.5 * np.cos(2 * phi)], axis=1)
    with pytest.raises(crown.CrownError, match="folds over itself"):
        crown.crown_border(ring, crown.CrownParams())


def _spacer(die, margin):
    from core import insertion, spacer

    params = spacer.SpacerParams(cement_gap_mm=0.06, from_margin_mm=1.0, transition_mm=0.5, radial_mm=0.01,
                                 axial_mm=0.0)
    ctx = insertion.insertion_context(die.mesh, margin)
    blocked = insertion.block_out(ctx, die.insertion_axis, 0.1)
    faces = spacer.inner_faces(ctx.vertices, ctx.faces, ctx.region.faces, ctx.region.band_faces, ctx.margin)
    return spacer.spacer_surface(blocked.mesh, faces, ctx.margin, die.insertion_axis, params, ctx.noise_sigma_mm)


@pytest.mark.parametrize("fdi, spec_kw, noise, seed", [
    (46, dict(scallop_mm=1.0), 0.0, 1),
    (41, dict(radius_x_mm=2.8, radius_y_mm=3.0, prep_height_mm=5.0, finish_width_mm=0.7, scallop_mm=1.75), 0.01, 1),
    (36, dict(finish="shoulder", prep_height_mm=5.5, scallop_mm=1.75), 0.03, 1),
    # Regresi benchmark tuning 2026-10-26: vertex kurva potong menonjol ke margin di chamfer landai, zipper tanpa
    # lookahead dan batas drift menjadi fan dari satu vertex ke seluruh margin (86 segitiga terlipat).
    (46, dict(finish="chamfer"), 0.03, 2),
])
def test_crown_is_a_closed_solid_and_keeps_the_spacer(fdi, spec_kw, noise, seed):
    spec = synthetic.DieSpec(**spec_kw)
    die = synthetic.make_die(spec, noise_sigma_mm=noise, rotate=True, seed=seed)
    margin = die.margin_curve(1024)
    prep_top = crown.prep_top_height(die.mesh.vertices, margin, die.insertion_axis)
    fit = crown.fit_crown(fdi, margin, die.insertion_axis, die.rotation[:, 0], prep_top)
    inner = _spacer(die, margin).mesh
    solid = crown.assemble_crown(fit.surface, inner)
    assert (solid.components, solid.genus, solid.sealed_voids) == (1, 0, 0)
    assert solid.volume_mm3 > 0
    from core.solid import to_manifold
    assert to_manifold(solid.mesh).genus() == 0
    # Permukaan dalam: vertex spacer yang dipertahankan tidak bergeser, titik potong ada di permukaan spacer.
    kept = solid.mesh.vertices[solid.inner_vertices]
    from core.geometry import MeshProjector
    _, _, dist = MeshProjector(inner).closest(kept)
    assert dist.max() < 1e-9
    assert solid.strip_delta_mm >= crown.CrownParams().strip_mm


def test_inner_surface_with_a_large_hole_is_an_explicit_error():
    spec = synthetic.DieSpec(scallop_mm=1.0)
    die = synthetic.make_die(spec, rotate=True, seed=1)
    margin = die.margin_curve(1024)
    prep_top = crown.prep_top_height(die.mesh.vertices, margin, die.insertion_axis)
    fit = crown.fit_crown(46, margin, die.insertion_axis, die.rotation[:, 0], prep_top)
    inner = _spacer(die, margin).mesh
    centroids = inner.vertices[inner.faces].mean(axis=1)
    top = centroids @ die.insertion_axis
    keep = top < np.percentile(top, 97)  # buang atap: lubang besar jauh dari margin
    holed = synthetic.MeshData(inner.vertices, inner.faces[keep])
    with pytest.raises(crown.CrownError, match="hole"):
        crown.assemble_crown(fit.surface, holed)
