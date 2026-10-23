# SPDX-License-Identifier: GPL-3.0-or-later
"""N-panel "Dental" di 3D Viewport. Fase 0: impor scan dan placeholder langkah kasus."""

import bpy
from bpy.props import EnumProperty, PointerProperty

# Urutan langkah kasus. Hanya "SCAN" yang punya fungsi di Fase 0.
CASE_STEPS = (
    ("ORDER", "Order", "Case details (not available in Phase 0)"),
    ("SCAN", "Scan", "Import the scan meshes"),
)


class DENTALCAD_PG_case(bpy.types.PropertyGroup):
    step: EnumProperty(name="Step", items=CASE_STEPS, default="SCAN")


class DENTALCAD_PT_main(bpy.types.Panel):
    bl_label = "DentalCAD"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Dental"

    def draw(self, context):
        layout = self.layout
        case = context.scene.dentalcad_case

        layout.row().prop(case, "step", expand=True)

        if case.step == "ORDER":
            layout.label(text="Case details are not available yet", icon="INFO")
            return

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
