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
    ("AXIS", "Axis", "Insertion axis, undercuts, and block-out"),
    ("SPACER", "Spacer", "Cement gap and spacing on the blocked-out die"),
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
        elif case.step == "AXIS":
            self.draw_axis(layout, context)
        elif case.step == "SPACER":
            self.draw_spacer(layout, context)
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

    def draw_axis(self, layout, context):
        from ..ops import insertion, margin

        die = context.active_object
        if die is None or die.type != "MESH":
            layout.label(text="Select the die", icon="INFO")
            return
        ok, message = margin.require_confirmed_margin(die)
        if not ok:
            layout.label(text=message, icon="ERROR")
            return
        col = layout.column(align=True)
        col.operator("dentalcad.insertion_detect", icon="EMPTY_SINGLE_ARROW")
        col.operator("dentalcad.insertion_from_view", icon="VIEW_CAMERA")
        col.operator("dentalcad.insertion_view", icon="HIDE_OFF")
        if insertion.KEY_AXIS not in die:
            layout.label(text="Detect the insertion axis first", icon="INFO")
            return
        box = layout.box()
        source = {"auto": "automatic", "view": "set from view", "handle": "dragged"}.get(
            die.get(insertion.KEY_AXIS_SOURCE, ""), "?")
        box.label(text=f"Axis: {source}", icon="EMPTY_SINGLE_ARROW")
        doubt = die.get(insertion.KEY_DOUBT, "")
        if doubt:
            box.label(text="Axis needs checking:", icon="ERROR")
            for reason in doubt.split("; "):
                box.label(text=reason)
        box.label(text=f"Deepest undercut: {1000 * die.get(insertion.KEY_UNDERCUT_MAX, 0.0):.0f} um")
        box.label(text="Drag the sphere at the arrow tip (G) to tilt the axis", icon="INFO")
        layout.operator("dentalcad.block_out", icon="MOD_SOLIDIFY")
        blocked = bpy.data.objects.get(insertion.blockout_name(die))
        param = insertion.material_preset().get("blockout_free_zone_mm")
        box = layout.box()
        box.label(text=f"No block-out zone near margin: {param.value} mm ({param.status_label})")
        if blocked is None:
            box.label(text="No block-out yet")
        elif insertion.require_current_block_out(die)[0]:
            box.label(text="Block-out matches the current axis", icon="CHECKMARK")
        else:
            box.label(text="Block-out is outdated: run Block Out again", icon="ERROR")

    def draw_spacer(self, layout, context):
        from ..ops import insertion, spacer

        die = context.active_object
        if die is None or die.type != "MESH":
            layout.label(text="Select the die", icon="INFO")
            return
        ok, message = insertion.require_current_block_out(die)
        if not ok:
            layout.label(text=message, icon="ERROR")
            return
        layout.operator("dentalcad.spacer", icon="MOD_SHRINKWRAP")
        preset = insertion.material_preset()
        box = layout.box()
        box.label(text=preset.name, icon="MATERIAL")
        for name in ("cement_gap_um", "cement_gap_from_margin_mm", "cement_gap_transition_mm", "radial_spacing_um",
                     "axial_spacing_um"):
            p = preset.get(name)
            box.label(text=f"{name}: {p.value} {p.unit} ({p.status_label})",
                      icon="ERROR" if p.status == "perlu_kalibrasi" else "NONE")
        current, status = spacer.spacer_status(die)
        obj = bpy.data.objects.get(spacer.spacer_name(die))
        box = layout.box()
        if obj is None:
            box.label(text="No spacer yet")
        else:
            box.label(text=status, icon="CHECKMARK" if current else "ERROR")
            box.label(text=f"Folded faces: {obj.get(spacer.KEY_FOLDED, 0)} (+{obj.get(spacer.KEY_SLIVERS, 0)} slivers)")
            box.label(text=f"New undercut in crown bottom: {1000 * obj.get(spacer.KEY_NEW_UNDERCUT, 0.0):.0f} um")

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
