# SPDX-License-Identifier: GPL-3.0-or-later
"""N-panel "Dental" di 3D Viewport: kalibrasi printer, impor scan, dan placeholder langkah kasus."""

import bpy
from bpy.props import EnumProperty, PointerProperty

from ..ops.coupons import load_presets, preset_items

# Urutan langkah. "ORDER" belum punya fungsi.
CASE_STEPS = (
    ("CALIBRATE", "Calibrate", "Printer + resin calibration coupons"),
    ("ORDER", "Order", "Case details (not available yet)"),
    ("SCAN", "Scan", "Import the scan meshes"),
    ("MARGIN", "Margin", "Detect and edit the preparation margin"),
)


class DENTALCAD_PG_case(bpy.types.PropertyGroup):
    step: EnumProperty(name="Step", items=CASE_STEPS, default="SCAN")
    preset: EnumProperty(name="Printer + Resin", items=preset_items)


class DENTALCAD_PT_main(bpy.types.Panel):
    bl_label = "DentalCAD"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Dental"

    def draw(self, context):
        layout = self.layout
        case = context.scene.dentalcad_case

        layout.row().prop(case, "step", expand=True)

        if case.step == "CALIBRATE":
            self.draw_calibrate(layout, case)
        elif case.step == "ORDER":
            layout.label(text="Case details are not available yet", icon="INFO")
        elif case.step == "MARGIN":
            self.draw_margin(layout, context)
        else:
            self.draw_scan(layout, context)

    def draw_calibrate(self, layout, case):
        layout.prop(case, "preset", text="")
        preset = load_presets().get(case.preset)
        if preset is None:
            return
        warnings = preset.warnings()
        box = layout.box()
        if warnings:
            box.label(text=f"{len(warnings)} parameters not calibrated", icon="ERROR")
            for param in preset.params.values():
                if param.status == "perlu_kalibrasi":
                    box.label(text=f"{param.name}: {param.value} {param.unit}")
        else:
            box.label(text="All coupon parameters calibrated", icon="CHECKMARK")
        layout.operator("dentalcad.export_coupons", icon="EXPORT")
        layout.label(text="Print each die with supports under it", icon="INFO")

    def draw_margin(self, layout, context):
        obj = context.active_object
        layout.operator("dentalcad.load_synthetic_case", icon="MESH_CYLINDER")
        col = layout.column(align=True)
        col.operator("dentalcad.margin_detect", icon="CURVE_BEZCIRCLE")
        col.operator("dentalcad.margin_draw", icon="GREASEPENCIL")
        col.operator("dentalcad.margin_update", icon="FILE_REFRESH")
        layout.operator("dentalcad.margin_confirm", icon="CHECKMARK")
        if obj is not None and obj.get("dentalcad_margin_role") == "controls":
            box = layout.box()
            box.label(text=f"Die: {obj.get('dentalcad_margin_die', '?')}", icon="MESH_DATA")
            box.label(text=f"{len(obj.data.splines[0].points)} control points")
            flagged = obj.get("dentalcad_margin_review_segments", 0)
            if obj.get("dentalcad_margin_status") == "confirmed":
                box.label(text="Status: confirmed", icon="CHECKMARK")
            else:
                box.label(text="Status: draft, not usable for the crown yet", icon="ERROR")
            if flagged:
                box.label(text=f"{flagged} segments to review (red)", icon="INFO")
            box.label(text="Edit Mode: move (G) or delete (X) points, then Update", icon="INFO")
        else:
            layout.label(text="Select the die, Detect Margin, click near the margin", icon="INFO")
            layout.label(text="Or Draw Margin: click points around the die, Enter to close")

    def draw_scan(self, layout, context):
        col = layout.column(align=True)
        col.operator("dentalcad.import_stl", icon="IMPORT")
        col.operator("dentalcad.import_ply", icon="IMPORT")

        obj = context.active_object
        if obj is not None and obj.type == "MESH":
            box = layout.box()
            box.label(text=obj.name, icon="MESH_DATA")
            box.label(text=f"{len(obj.data.polygons):,} triangles")


classes = (
    DENTALCAD_PG_case,
    DENTALCAD_PT_main,
)

_register_classes, _unregister_classes = bpy.utils.register_classes_factory(classes)


def register():
    _register_classes()
    bpy.types.Scene.dentalcad_case = PointerProperty(type=DENTALCAD_PG_case)


def unregister():
    del bpy.types.Scene.dentalcad_case
    _unregister_classes()
