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
    bottom = fit.surface.frame.to_world(fit.surface.local[:, 0, :])
    assert synthetic.distance_to_polyline(bottom, margin).max() < 1e-9
    assert crown.flipped_faces(fit.surface) == 0
    assert len(fit.hints) == 2  # tanpa tetangga dan tanpa antagonis: keduanya "perlu dicek"


def _context(spec, die, prep_top, gaps=(0.6, 0.6), clearance=3.6):
    R = die.rotation
    margin_die = synthetic.margin_points(spec, np.linspace(0, 2 * np.pi, 1024, endpoint=False))
    zc = margin_die[:, 2].mean()
    bulge = crown.CrownParams().contour_bulge_mm
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


def test_surface_is_the_template_above_the_blend_height():
    spec, die, margin, prep_top = _die_and_margin(scallop_mm=1.5)
    p = crown.CrownParams()
    fit = crown.fit_crown(46, margin, die.insertion_axis, die.rotation[:, 0], prep_top, params=p)
    s = fit.surface
    base = s.local[:, 0, 2]
    tpl = template.template_points(s.template, s.phi[:, None], s.v[None, :], base_z=base[:, None])
    above = (tpl[..., 2] - base[:, None]) >= p.blend_height_mm
    above[:, -1] = False  # titik tengah oklusal disatukan untuk semua sudut
    np.testing.assert_allclose(s.local[above], tpl[above], atol=1e-12)
    np.testing.assert_allclose(s.local[:, 0, 2], tpl[:, 0, 2], atol=1e-12)  # tepi servikal: hanya geser mendatar


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
