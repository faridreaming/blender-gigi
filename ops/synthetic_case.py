# SPDX-License-Identifier: GPL-3.0-or-later
"""Kasus uji sintetis di Blender (docs/PHASE2.md §4): die dengan margin analitis yang diketahui pasti."""

import bpy
import numpy as np
from bpy.props import BoolProperty, EnumProperty, FloatProperty, IntProperty

from ..core import synthetic
from .mesh_bridge import to_blender_mesh

DIE_NAME = "Synthetic Die"
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
    undercut_deg: FloatProperty(name="Undercut Angle", default=10.0, min=0.0, max=20.0)
    undercut_center_deg: FloatProperty(name="Undercut Direction", default=0.0, min=0.0, max=360.0,
                                       description="0 is the scallop peak (proximal side)")
    seed: IntProperty(name="Seed", default=0, min=0)
    show_truth: BoolProperty(name="Show True Margin", default=True)

    def execute(self, context):
        for name in (DIE_NAME, f"{DIE_NAME} Truth Margin", f"{DIE_NAME} Margin", f"{DIE_NAME} Margin Preview",
                     f"{DIE_NAME} Margin Review", f"{DIE_NAME} Margin Draft", f"{DIE_NAME} Insertion Axis",
                     f"{DIE_NAME} Axis Handle", f"{DIE_NAME} Block-out"):
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
        self.report({"INFO"}, f"Synthetic {self.finish} die, scallop {self.scallop_mm:g} mm, noise {self.noise_um:g} um")
        return {"FINISHED"}
