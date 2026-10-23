# SPDX-License-Identifier: GPL-3.0-or-later
"""Operator margin semi-otomatis (docs/PHASE2.md §5.1). Logika di core/margin.py.

Alur pengguna:
1. Pilih objek die, jalankan "Detect Margin", klik sekali di dekat margin di viewport.
2. Kurva "<die> Margin" (titik kontrol, bisa diedit) dan "<die> Margin Preview" (kurva halus) dibuat.
3. Edit titik kontrol di Edit Mode (geser G, hapus X), lalu jalankan "Update Margin": titik yang digeser
   diproyeksikan ke permukaan die, titik lain dipertahankan.

Kalau deteksi ditolak (scan berderau, kurva tidak wajar), "Draw Margin" membuat kurva yang sama dari titik
yang diklik pengguna satu per satu; kurva ditutup otomatis dan diedit dengan cara yang sama.
"""

import bpy
import numpy as np
from bpy.props import BoolProperty, CollectionProperty, FloatVectorProperty
from bpy_extras import view3d_utils
from mathutils import Matrix, Vector

from ..core import margin as core_margin
from ..core.geometry import MeshProjector
from .synthetic_case import KEY_TRUTH
from .mesh_bridge import from_blender_mesh

KEY_DIE = "dentalcad_margin_die"
KEY_CONTROLS = "dentalcad_margin_controls"
KEY_ROLE = "dentalcad_margin_role"
PREVIEW_SAMPLES = 512
PREVIEW_BEVEL_MM = 0.05
DRAFT_BEVEL_MM = 0.04
MANUAL_HINT = "Use Draw Margin to place the margin by hand."


def _spline_points(curve: bpy.types.Curve) -> np.ndarray:
    spline = curve.splines[0]
    co = np.empty(len(spline.points) * 4, dtype=np.float64)
    spline.points.foreach_get("co", co)
    return co.reshape(-1, 4)[:, :3]


def _set_poly(curve: bpy.types.Curve, points: np.ndarray) -> None:
    curve.splines.clear()
    spline = curve.splines.new("POLY")
    spline.points.add(len(points) - 1)
    spline.points.foreach_set("co", np.hstack([points, np.ones((len(points), 1))]).ravel())
    spline.use_cyclic_u = True


def _curve_object(context, name: str, matrix: Matrix) -> bpy.types.Object:
    obj = bpy.data.objects.get(name)
    if obj is None or obj.type != "CURVE":
        curve = bpy.data.curves.new(name, "CURVE")
        curve.dimensions = "3D"
        obj = bpy.data.objects.new(name, curve)
        context.collection.objects.link(obj)
    obj.matrix_world = matrix
    return obj


def write_margin(context, die: bpy.types.Object, curve: core_margin.MarginCurve) -> bpy.types.Object:
    """Buat atau perbarui objek kurva margin (titik kontrol) dan pratinjau (kurva halus) untuk die."""
    controls = _curve_object(context, f"{die.name} Margin", die.matrix_world)
    _set_poly(controls.data, curve.control_points)
    controls[KEY_DIE] = die.name
    controls[KEY_ROLE] = "controls"
    controls[KEY_CONTROLS] = curve.control_points.ravel().tolist()

    preview = _curve_object(context, f"{die.name} Margin Preview", die.matrix_world)
    _set_poly(preview.data, curve.sample(PREVIEW_SAMPLES))
    preview.data.bevel_depth = PREVIEW_BEVEL_MM
    preview[KEY_DIE] = die.name
    preview[KEY_ROLE] = "preview"
    preview.hide_select = True
    return controls


def ray_hit(context, event, obj: bpy.types.Object):
    """Titik dunia tempat sinar dari kursor mengenai obj, atau None."""
    region, rv3d = context.region, context.region_data
    coord = (event.mouse_region_x, event.mouse_region_y)
    origin = view3d_utils.region_2d_to_origin_3d(region, rv3d, coord)
    direction = view3d_utils.region_2d_to_vector_3d(region, rv3d, coord)
    inverse = obj.matrix_world.inverted()
    local_origin = inverse @ origin
    local_dir = (inverse.to_3x3() @ direction).normalized()
    found, location, _, _ = obj.ray_cast(local_origin, local_dir)
    return (obj.matrix_world @ location) if found else None


def die_mesh(die: bpy.types.Object):
    return from_blender_mesh(die.data)


def detect_on(context, die: bpy.types.Object, seed_world) -> core_margin.MarginResult:
    seed_local = die.matrix_world.inverted() @ Vector(seed_world)
    result = core_margin.detect_margin(die_mesh(die), np.array(seed_local))
    write_margin(context, die, result.curve)
    return result


class DENTALCAD_OT_margin_detect(bpy.types.Operator):
    """Click once near the preparation margin to detect it as an editable closed curve"""

    bl_idname = "dentalcad.margin_detect"
    bl_label = "Detect Margin"
    bl_options = {"REGISTER", "UNDO"}

    seed_point: FloatVectorProperty(name="Seed Point", subtype="XYZ", size=3)
    use_seed: BoolProperty(name="Use Seed Point", default=False, options={"HIDDEN"})

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return obj is not None and obj.type == "MESH"

    def execute(self, context):
        die = context.active_object
        try:
            result = detect_on(context, die, self.seed_point)
        except core_margin.MarginNoiseError as exc:
            self.report({"ERROR"}, f"Scan too noisy (estimated noise {1000 * exc.sigma_mm:.0f} um, limit "
                                   f"{1000 * exc.limit_mm:.0f} um), no curve was created. " + MANUAL_HINT)
            return {"CANCELLED"}
        except core_margin.MarginPlausibilityError as exc:
            self.report({"ERROR"}, "Margin rejected, the detected curve is implausible: "
                                   + ", ".join(exc.failed) + ". Click closer to the margin, or " + MANUAL_HINT[0].lower() + MANUAL_HINT[1:])
            return {"CANCELLED"}
        except core_margin.MarginError as exc:
            self.report({"ERROR"}, f"Margin not found ({exc}). Click closer to the margin, or " + MANUAL_HINT[0].lower() + MANUAL_HINT[1:])
            return {"CANCELLED"}
        message = f"Margin: {len(result.curve.control_points)} control points, {result.curve.length():.1f} mm"
        if KEY_TRUTH in die:
            truth = np.array(die[KEY_TRUTH], dtype=float).reshape(-1, 3)
            dev = core_margin.margin_deviation(result.curve.sample(1024), truth)
            message += f"; vs true margin: median {1000 * dev['median']:.0f} um, p95 {1000 * dev['p95']:.0f} um"
        self.report({"INFO"}, message)
        return {"FINISHED"}

    def invoke(self, context, event):
        if self.use_seed:
            return self.execute(context)
        if context.area is None or context.area.type != "VIEW_3D":
            self.report({"ERROR"}, "Run Detect Margin from the 3D Viewport")
            return {"CANCELLED"}
        context.window_manager.modal_handler_add(self)
        context.area.header_text_set("Click near the margin of the active object (Esc to cancel)")
        return {"RUNNING_MODAL"}

    def modal(self, context, event):
        if event.type in {"ESC", "RIGHTMOUSE"}:
            context.area.header_text_set(None)
            return {"CANCELLED"}
        if event.type == "LEFTMOUSE" and event.value == "PRESS":
            hit = ray_hit(context, event, context.active_object)
            if hit is None:
                self.report({"WARNING"}, "Click on the active object")
                return {"RUNNING_MODAL"}
            context.area.header_text_set(None)
            self.seed_point = hit
            return self.execute(context)
        return {"PASS_THROUGH"}


class DENTALCAD_PG_margin_point(bpy.types.PropertyGroup):
    co: FloatVectorProperty(name="Point", subtype="XYZ", size=3)


class DENTALCAD_OT_margin_draw(bpy.types.Operator):
    """Draw the margin by hand: click points on the die in order; the curve closes automatically"""

    bl_idname = "dentalcad.margin_draw"
    bl_label = "Draw Margin"
    bl_options = {"REGISTER", "UNDO"}

    points: CollectionProperty(type=DENTALCAD_PG_margin_point, options={"HIDDEN", "SKIP_SAVE"})

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return obj is not None and obj.type == "MESH"

    def execute(self, context):
        die = context.active_object
        inverse = die.matrix_world.inverted()
        local = np.array([tuple(inverse @ Vector(p.co)) for p in self.points], dtype=float).reshape(-1, 3)
        try:
            curve = core_margin.draw_margin(die_mesh(die), local)
        except core_margin.MarginError as exc:
            self.report({"ERROR"}, f"Margin not drawn: {exc}")
            return {"CANCELLED"}
        write_margin(context, die, curve)
        self.report({"INFO"}, f"Margin drawn: {len(curve.control_points)} control points, {curve.length():.1f} mm")
        return {"FINISHED"}

    def invoke(self, context, event):
        if context.area is None or context.area.type != "VIEW_3D":
            self.report({"ERROR"}, "Run Draw Margin from the 3D Viewport")
            return {"CANCELLED"}
        self.points.clear()
        self._die = context.active_object
        self._draft = None
        context.window_manager.modal_handler_add(self)
        self._header(context)
        return {"RUNNING_MODAL"}

    def _header(self, context):
        context.area.header_text_set(
            f"Draw Margin: {len(self.points)} points. Click on the die to add, Backspace to undo the last point, "
            f"Enter to close the curve (at least {core_margin.MIN_DRAWN_POINTS}), Esc to cancel")

    def _update_draft(self, context):
        if self._draft is None:
            curve = bpy.data.curves.new(f"{self._die.name} Margin Draft", "CURVE")
            curve.dimensions = "3D"
            curve.bevel_depth = DRAFT_BEVEL_MM
            self._draft = bpy.data.objects.new(curve.name, curve)
            self._draft.hide_select = True
            context.collection.objects.link(self._draft)
        curve = self._draft.data
        curve.splines.clear()
        if len(self.points):
            spline = curve.splines.new("POLY")
            spline.points.add(len(self.points) - 1)
            co = np.array([tuple(p.co) for p in self.points], dtype=float)
            spline.points.foreach_set("co", np.hstack([co, np.ones((len(co), 1))]).ravel())
            spline.use_cyclic_u = len(self.points) >= 3

    def _finish(self, context):
        context.area.header_text_set(None)
        if self._draft is not None:
            curve = self._draft.data
            bpy.data.objects.remove(self._draft)
            bpy.data.curves.remove(curve)
            self._draft = None

    def modal(self, context, event):
        if event.type in {"ESC", "RIGHTMOUSE"} and event.value == "PRESS":
            self._finish(context)
            return {"CANCELLED"}
        if event.type in {"RET", "NUMPAD_ENTER"} and event.value == "PRESS":
            self._finish(context)
            return self.execute(context)
        if event.type == "BACK_SPACE" and event.value == "PRESS":
            if len(self.points):
                self.points.remove(len(self.points) - 1)
                self._update_draft(context)
                self._header(context)
            return {"RUNNING_MODAL"}
        if event.type == "LEFTMOUSE" and event.value == "PRESS":
            hit = ray_hit(context, event, self._die)
            if hit is None:
                self.report({"WARNING"}, "Click on the die")
            else:
                self.points.add().co = hit
                self._update_draft(context)
                self._header(context)
            return {"RUNNING_MODAL"}
        return {"PASS_THROUGH"}


class DENTALCAD_OT_margin_update(bpy.types.Operator):
    """Apply edits of the margin control points: moved points are projected onto the die surface"""

    bl_idname = "dentalcad.margin_update"
    bl_label = "Update Margin"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return obj is not None and obj.get(KEY_ROLE) == "controls"

    def execute(self, context):
        controls = context.active_object
        if controls.mode == "EDIT":
            bpy.ops.object.mode_set(mode="OBJECT")
        die = bpy.data.objects.get(controls.get(KEY_DIE, ""))
        if die is None or die.type != "MESH":
            self.report({"ERROR"}, "The die object of this margin no longer exists")
            return {"CANCELLED"}
        previous = np.array(controls[KEY_CONTROLS], dtype=float).reshape(-1, 3)
        curve = core_margin.MarginCurve(previous, MeshProjector(die_mesh(die)))
        try:
            stats = curve.apply_edit(_spline_points(controls.data))
        except core_margin.MarginError as exc:
            self.report({"ERROR"}, str(exc))
            return {"CANCELLED"}
        write_margin(context, die, curve)
        self.report({"INFO"}, f"Margin updated: {stats['moved']} moved, {stats['kept']} kept, {stats['removed']} removed")
        return {"FINISHED"}
