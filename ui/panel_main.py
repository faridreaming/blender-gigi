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
