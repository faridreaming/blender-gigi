# SPDX-License-Identifier: GPL-3.0-or-later
"""Kasus uji sintetis di Blender (docs/PHASE2.md §4): die dengan margin analitis yang diketahui pasti."""

import bpy
import numpy as np
from bpy.props import BoolProperty, EnumProperty, FloatProperty, IntProperty

from ..core import synthetic
from .mesh_bridge import to_blender_mesh

DIE_NAME = "Synthetic Die"
CONTEXT_NAMES = ("Synthetic Mesial Neighbour", "Synthetic Distal Neighbour", "Synthetic Antagonist")
NEIGHBOUR_SEMI_AXES = (4.0, 4.5, 3.5)  # desain data uji (PHASE2.md §5.4)
NEIGHBOUR_GAP_MM = 0.6  # celah dari tepi margin + tonjolan kontur ke permukaan dalam tetangga
ANTAGONIST_CLEARANCE_MM = 3.6  # dari puncak preparasi ke bidang antagonis
KEY_TRUTH = "dentalcad_truth_margin"
TRUTH_SAMPLES = 512
TRUTH_COLOR = (0.1, 0.8, 0.2, 1.0)


def _remove(name: str) -> None:
    obj = bpy.data.objects.get(name)
    if obj is not None:
        data = obj.data
        bpy.data.objects.remove(obj)
        if data is not None and data.users == 0:
            (bpy.data.meshes if isinstance(data, bpy.types.Mesh) else bpy.data.curves).remove(data)


def _truth_material() -> bpy.types.Material:
    material = bpy.data.materials.get("DentalCAD Truth Margin")
    if material is None:
        material = bpy.data.materials.new("DentalCAD Truth Margin")
    material.diffuse_color = TRUTH_COLOR
    return material


class DENTALCAD_OT_load_synthetic_case(bpy.types.Operator):
    """Add a synthetic prepared die whose true margin is known exactly (green curve), for testing Detect Margin"""

    bl_idname = "dentalcad.load_synthetic_case"
    bl_label = "Load Synthetic Case"
    bl_options = {"REGISTER", "UNDO"}

    finish: EnumProperty(name="Finish", items=[(f, f.capitalize(), "") for f in synthetic.FINISHES], default="chamfer")
    scallop_mm: FloatProperty(name="Scallop (mm)", default=1.0, min=0.0, max=2.5)
    noise_um: FloatProperty(name="Noise (um)", default=10.0, min=0.0, max=150.0)
    undercut: BoolProperty(name="Undercut Sector", default=False)
    with_context: BoolProperty(name="Neighbours and Antagonist", default=False,
                               description="Also add synthetic mesial/distal neighbours (ellipsoids) and an antagonist "
                                           "plane with known distances, for testing Propose Crown")
    undercut_deg: FloatProperty(name="Undercut Angle", default=10.0, min=0.0, max=20.0)
    undercut_center_deg: FloatProperty(name="Undercut Direction", default=0.0, min=0.0, max=360.0,
                                       description="0 is the scallop peak (proximal side)")
    seed: IntProperty(name="Seed", default=0, min=0)
    show_truth: BoolProperty(name="Show True Margin", default=True)

    def execute(self, context):
        for name in (DIE_NAME, f"{DIE_NAME} Truth Margin", f"{DIE_NAME} Margin", f"{DIE_NAME} Margin Preview",
                     f"{DIE_NAME} Margin Review", f"{DIE_NAME} Margin Draft", f"{DIE_NAME} Insertion Axis",
                     f"{DIE_NAME} Axis Handle", f"{DIE_NAME} Block-out", f"{DIE_NAME} Spacer",
                     f"{DIE_NAME} Crown Proposal", f"{DIE_NAME} Mesial Direction", f"{DIE_NAME} Mesial Handle",
                     *CONTEXT_NAMES):
            _remove(name)
        spec = synthetic.DieSpec(finish=self.finish, scallop_mm=self.scallop_mm,
                                 undercut_deg=self.undercut_deg if self.undercut else 0.0,
                                 undercut_center_deg=self.undercut_center_deg)
        die = synthetic.make_die(spec, noise_sigma_mm=self.noise_um / 1000.0, rotate=False, seed=self.seed)

        obj = bpy.data.objects.new(DIE_NAME, to_blender_mesh(DIE_NAME, die.mesh))
        context.collection.objects.link(obj)
        truth = die.margin_curve(TRUTH_SAMPLES)
        obj[KEY_TRUTH] = truth.ravel().tolist()

        if self.show_truth:
            curve = bpy.data.curves.new(f"{DIE_NAME} Truth Margin", "CURVE")
            curve.dimensions = "3D"
            curve.bevel_depth = 0.03
            spline = curve.splines.new("POLY")
            spline.points.add(len(truth) - 1)
            spline.points.foreach_set("co", np.hstack([truth, np.ones((len(truth), 1))]).ravel())
            spline.use_cyclic_u = True
            curve.materials.append(_truth_material())
            truth_obj = bpy.data.objects.new(f"{DIE_NAME} Truth Margin", curve)
            truth_obj.hide_select = True
            context.collection.objects.link(truth_obj)

        for other in context.selected_objects:
            other.select_set(False)
        obj.select_set(True)
        context.view_layer.objects.active = obj
        scene = getattr(context.scene, "dentalcad_case", None)
        if scene is not None:
            scene.step = "MARGIN"
        if self.with_context:
            self._add_context(context, spec, die, scene)
        self.report({"INFO"}, f"Synthetic {self.finish} die, scallop {self.scallop_mm:g} mm, noise {self.noise_um:g} um")
        return {"FINISHED"}

    def _add_context(self, context, spec, die, scene) -> None:
        """Tetangga elipsoid di sumbu x die (+x = mesial) dan bidang antagonis di atas preparasi (jarak diketahui)."""
        margin = synthetic.margin_points(spec, np.linspace(0, 2 * np.pi, 1024, endpoint=False))
        zc = float(margin[:, 2].mean())
        bulge = synthetic.NEIGHBOUR_CONTOUR_ALLOWANCE_MM
        axes = np.array(NEIGHBOUR_SEMI_AXES)
        z_k = zc + 0.4 * spec.prep_height_mm
        noise = self.noise_um / 1000.0
        objects = []
        for k, (name, sign, edge) in enumerate(((CONTEXT_NAMES[0], 1.0, margin[:, 0].max()),
                                                (CONTEXT_NAMES[1], -1.0, margin[:, 0].min()))):
            inner = edge + sign * (bulge + NEIGHBOUR_GAP_MM)
            ellipsoid = synthetic.Ellipsoid(np.array([inner + sign * axes[0], 0.0, z_k]), axes, np.eye(3))
            objects.append((name, ellipsoid.mesh(noise_sigma_mm=noise, seed=self.seed + k)))
        top = spec.top_z + spec.roof_height_mm
        plane = synthetic.AntagonistPlane(np.array([0.0, 0.0, top + ANTAGONIST_CLEARANCE_MM]), np.array([0.0, 0.0, -1.0]))
        objects.append((CONTEXT_NAMES[2], plane.mesh(noise_sigma_mm=noise, seed=self.seed + 7)))
        created = []
        for name, mesh in objects:
            obj = bpy.data.objects.new(name, to_blender_mesh(name, mesh))
            obj.hide_select = True
            context.collection.objects.link(obj)
            created.append(obj)
        if scene is not None:
            scene.mesial_neighbor, scene.distal_neighbor, scene.antagonist = created
            scene.fdi = 46
