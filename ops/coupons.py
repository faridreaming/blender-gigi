# SPDX-License-Identifier: GPL-3.0-or-later
"""Operator kupon kalibrasi (docs/PHASE1.md §5.K). Geometri sepenuhnya dari core/calibration."""

import tomllib
from pathlib import Path

import bpy
from bpy.props import BoolProperty, EnumProperty, StringProperty

from ..core import calibration, model_presets, solid
from .mesh_bridge import to_blender_mesh

PACKAGE_DIR = Path(__file__).resolve().parent.parent
PRESET_DIR = PACKAGE_DIR / "data" / "model_presets"
COLLECTION_NAME = "DentalCAD Coupons"
PREVIEW_GAP_MM = 10.0

# Blender meminta item EnumProperty dinamis tetap hidup selama dipakai, jadi disimpan di modul.
_preset_items: list[tuple[str, str, str]] = []


def load_presets() -> dict[str, model_presets.Preset]:
    return model_presets.load_presets(PRESET_DIR)


def preset_items(self, context):
    _preset_items.clear()
    for preset in load_presets().values():
        _preset_items.append((preset.id, f"{preset.printer} / {preset.resin}", preset.id))
    return _preset_items


def extension_version() -> str:
    with (PACKAGE_DIR / "blender_manifest.toml").open("rb") as f:
        return tomllib.load(f).get("version", "")


def add_to_scene(context, coupons: calibration.CouponSet) -> int:
    collection = bpy.data.collections.get(COLLECTION_NAME)
    if collection is None:
        collection = bpy.data.collections.new(COLLECTION_NAME)
        context.scene.collection.children.link(collection)
    for obj in list(collection.objects):
        bpy.data.objects.remove(obj)

    x = 0.0
    for part in coupons.parts:
        x0, _, _, x1, _, _ = part.solid.bounding_box()
        obj = bpy.data.objects.new(part.name, to_blender_mesh(part.name, solid.to_mesh_data(part.solid)))
        obj.location.x = x - x0
        obj["dentalcad_print_note"] = part.print_note
        collection.objects.link(obj)
        x += (x1 - x0) + PREVIEW_GAP_MM
    return len(coupons.parts)


class DENTALCAD_OT_export_coupons(bpy.types.Operator):
    """Export calibration coupon STL files, measurement sheet and report for a printer + resin preset"""

    bl_idname = "dentalcad.export_coupons"
    bl_label = "Export Calibration Coupons"
    bl_options = {"REGISTER"}

    directory: StringProperty(name="Folder", subtype="DIR_PATH")
    preset: EnumProperty(name="Preset", items=preset_items)
    add_to_scene: BoolProperty(name="Add to Scene", default=True, description="Also add the coupons to the scene for preview")

    def invoke(self, context, event):
        case = getattr(context.scene, "dentalcad_case", None)
        if case is not None and case.preset:
            self.preset = case.preset
        context.window_manager.fileselect_add(self)
        return {"RUNNING_MODAL"}

    def execute(self, context):
        if not self.directory:
            self.report({"ERROR"}, "Choose an output folder")
            return {"CANCELLED"}
        try:
            preset = load_presets()[self.preset]
            coupons = calibration.build_coupon_set(preset)
            out_dir = Path(bpy.path.abspath(self.directory)) / preset.id
            report = calibration.write_coupon_set(coupons, out_dir, version=extension_version())
        except (ValueError, KeyError, model_presets.PresetError) as exc:
            self.report({"ERROR"}, f"Cannot export coupons: {exc}")
            return {"CANCELLED"}

        if self.add_to_scene:
            add_to_scene(context, coupons)
        for warning in report["warnings"]:
            self.report({"WARNING"}, f"Not calibrated: {warning}")
        self.report({"INFO"}, f"Exported {len(report['parts'])} coupon STL files to {out_dir}")
        return {"FINISHED"}
