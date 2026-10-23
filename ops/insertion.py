# SPDX-License-Identifier: GPL-3.0-or-later
"""Operator sumbu insersi, peta undercut, dan block-out (docs/PHASE2.md §5.2). Logika di core/insertion.py.

Perilaku mengikuti konvensi exocad (wiki "Setting insertion axis" dan Quick Guide "Crown Bottoms"):
- "Detect Insertion Axis" menghitung sumbu otomatis. Kalau ragu (margin line terbayang, atau ada sumbu lain
  yang hampir sama baiknya), sumbu ditandai "needs checking" dan pandangan diarahkan sepanjang sumbu.
- Sumbu diubah dengan "Set from View" (lihat preparasi dari arah insersi yang diinginkan), atau dengan
  menyeret bola di ujung panah ("<die> Axis Handle", tombol G). Peta undercut diperbarui langsung.
- "Block Out Undercuts" membuat "<die> Block-out" sejajar sumbu, dengan zona tanpa block-out di dekat
  margin dari preset material. Hasilnya dipakai §5.3 (spacer).
Semua operator hanya jalan kalau margin sudah dikonfirmasi (require_confirmed_margin).
"""

from pathlib import Path

import bpy
import numpy as np
from bpy.app.handlers import persistent
from bpy.props import BoolProperty, FloatVectorProperty
from mathutils import Matrix, Vector

from ..core import insertion as core_insertion
from ..core import margin as core_margin
from ..core.material_db import load_material_presets
from .margin import KEY_CONTROLS, die_mesh, margin_controls, require_confirmed_margin
from .mesh_bridge import to_blender_mesh

PACKAGE_DIR = Path(__file__).resolve().parent.parent
MATERIAL_DIR = PACKAGE_DIR / "data" / "materials"
DEFAULT_MATERIAL = "ivoclar_zircad_prime_full_contour"

KEY_DIE = "dentalcad_insertion_die"
KEY_AXIS = "dentalcad_insertion_axis"  # di die, koordinat lokal die
KEY_AXIS_SOURCE = "dentalcad_insertion_axis_source"  # "auto", "view", "handle"
KEY_DOUBT = "dentalcad_insertion_doubt"  # alasan ragu (bahasa Inggris), dipisah "; "
KEY_UNDERCUT_MAX = "dentalcad_undercut_max_mm"
KEY_BASE = "dentalcad_insertion_base"  # pangkal panah, koordinat lokal die
KEY_HANDLE_LAST = "dentalcad_insertion_handle_last"
KEY_BLOCKOUT_AXIS = "dentalcad_blockout_axis"
KEY_BLOCKOUT_RESIDUAL = "dentalcad_blockout_residual_mm"
KEY_BLOCKOUT_ZONE = "dentalcad_blockout_free_zone_mm"
UNDERCUT_COLOR = "DentalCAD Undercut"
UNDERCUT_DEPTH = "dentalcad_undercut_mm"
ARROW_LENGTH_MM = 6.0
HANDLE_SIZE_MM = 0.6
ARROW_GAP_MM = 1.5
COLOR_FULL_DEPTH_MM = 0.5  # merah penuh mulai kedalaman ini (skala tampilan, bukan ambang klinis)

_contexts: dict = {}  # cache InsertionContext per die (dibangun ulang kalau mesh atau margin berubah)
_updating = False


def axis_name(die) -> str:
    return f"{die.name} Insertion Axis"


def handle_name(die) -> str:
    return f"{die.name} Axis Handle"


def blockout_name(die) -> str:
    return f"{die.name} Block-out"


def material_preset():
    return load_material_presets(MATERIAL_DIR)[DEFAULT_MATERIAL]


def _margin_points(die) -> np.ndarray:
    controls = margin_controls(die)
    points = np.array(controls[KEY_CONTROLS], dtype=float).reshape(-1, 3)
    return core_margin.MarginCurve(points, None).sample(1024)


def context_for(die) -> core_insertion.InsertionContext:
    controls = margin_controls(die)
    key = (die.name, len(die.data.vertices), len(die.data.polygons), tuple(controls[KEY_CONTROLS]))
    cached = _contexts.get(die.name)
    if cached is None or cached[0] != key:
        _contexts[die.name] = (key, core_insertion.insertion_context(die_mesh(die), _margin_points(die)))
    return _contexts[die.name][1]


def _gate(operator, die) -> bool:
    ok, message = require_confirmed_margin(die)
    if not ok:
        operator.report({"ERROR"}, message)
    return ok


def _depth_colors(depth: np.ndarray) -> np.ndarray:
    """Abu-abu tanpa undercut; kuning ke merah sesuai kedalaman."""
    colors = np.tile(np.array([0.8, 0.8, 0.8, 1.0]), (len(depth), 1))
    under = depth > 0
    s = np.clip(depth[under] / COLOR_FULL_DEPTH_MM, 0.0, 1.0)[:, None]
    yellow, red = np.array([1.0, 0.85, 0.1, 1.0]), np.array([0.9, 0.05, 0.05, 1.0])
    colors[under] = (1 - s) * yellow + s * red
    return colors


def _write_map(die, umap: core_insertion.UndercutMap) -> None:
    mesh = die.data
    attr = mesh.color_attributes.get(UNDERCUT_COLOR)
    if attr is None:
        attr = mesh.color_attributes.new(UNDERCUT_COLOR, "FLOAT_COLOR", "POINT")
    attr.data.foreach_set("color", _depth_colors(umap.vertex_depth).astype(np.float32).ravel())
    mesh.color_attributes.active_color = attr
    depth_attr = mesh.attributes.get(UNDERCUT_DEPTH)
    if depth_attr is None:
        depth_attr = mesh.attributes.new(UNDERCUT_DEPTH, "FLOAT", "POINT")
    depth_attr.data.foreach_set("value", umap.vertex_depth.astype(np.float32))
    mesh.update()
    die[KEY_UNDERCUT_MAX] = float(umap.vertex_depth.max())


def _empty(context, name: str, display: str, size: float):
    obj = bpy.data.objects.get(name)
    if obj is None:
        obj = bpy.data.objects.new(name, None)
        context.collection.objects.link(obj)
    obj.empty_display_type = display
    obj.empty_display_size = size
    return obj


def _place_arrow(context, die, ctx: core_insertion.InsertionContext, axis_local: np.ndarray) -> None:
    """Panah di atas preparasi sepanjang sumbu; bola pegangan di ujungnya."""
    top = float(np.max((ctx.vertices[ctx.region.vertices] - ctx.margin.mean(axis=0)) @ axis_local))
    base_local = ctx.margin.mean(axis=0) + (top + ARROW_GAP_MM) * axis_local
    die[KEY_BASE] = base_local.tolist()
    world = die.matrix_world
    base_world = world @ Vector(base_local)
    axis_world = (world.to_3x3() @ Vector(axis_local)).normalized()
    arrow = _empty(context, axis_name(die), "SINGLE_ARROW", ARROW_LENGTH_MM)
    arrow.matrix_world = Matrix.Translation(base_world) @ axis_world.to_track_quat("Z", "Y").to_matrix().to_4x4()
    arrow.hide_select = True
    arrow[KEY_DIE] = die.name
    handle = _empty(context, handle_name(die), "SPHERE", HANDLE_SIZE_MM)
    handle.location = base_world + axis_world * ARROW_LENGTH_MM
    handle[KEY_DIE] = die.name
    die[KEY_HANDLE_LAST] = list(handle.location)


def apply_axis(context, die, axis_local, source: str,
               alternatives: list | None = None) -> tuple[bool, list, core_insertion.UndercutMap]:
    """Pakai sumbu (koordinat lokal die): cek keraguan, perbarui peta undercut dan panah."""
    global _updating
    axis_local = np.asarray(axis_local, float)
    axis_local = axis_local / np.linalg.norm(axis_local)
    ctx = context_for(die)
    doubtful, reasons, umap = core_insertion.check_axis(ctx, axis_local, alternatives)
    _updating = True
    try:
        die[KEY_AXIS] = axis_local.tolist()
        die[KEY_AXIS_SOURCE] = source
        die[KEY_DOUBT] = "; ".join(name for name, _ in reasons)
        _write_map(die, umap)
        _place_arrow(context, die, ctx, axis_local)
        blocked = bpy.data.objects.get(blockout_name(die))
        if blocked is not None and not np.allclose(blocked.get(KEY_BLOCKOUT_AXIS, [0, 0, 0]), axis_local, atol=1e-6):
            blocked["dentalcad_blockout_stale"] = True
    finally:
        _updating = False
    return doubtful, reasons, umap


def require_current_block_out(die) -> tuple[bool, str]:
    """Gerbang §5.3: block-out ada dan dibuat untuk sumbu yang sedang dipakai."""
    ok, message = require_confirmed_margin(die)
    if not ok:
        return ok, message
    blocked = bpy.data.objects.get(blockout_name(die))
    if blocked is None:
        return False, f"{die.name} has no block-out yet: run Block Out Undercuts"
    if blocked.get("dentalcad_blockout_stale") or KEY_AXIS not in die or not np.allclose(
            blocked.get(KEY_BLOCKOUT_AXIS, [0, 0, 0]), die[KEY_AXIS], atol=1e-6):
        return False, f"The insertion axis of {die.name} changed after the block-out: run Block Out Undercuts again"
    return True, "Block-out is current"


def _look_along(context, die, axis_local) -> None:
    """Arahkan viewport supaya pengguna melihat preparasi dari arah insersi."""
    axis_world = (die.matrix_world.to_3x3() @ Vector(axis_local)).normalized()
    screen = context.screen
    if screen is None:
        return
    target = die.matrix_world @ Vector(context_for(die).margin.mean(axis=0))
    for area in screen.areas:
        if area.type != "VIEW_3D":
            continue
        for space in area.spaces:
            if space.type == "VIEW_3D":
                region_3d = space.region_3d
                region_3d.view_rotation = axis_world.to_track_quat("Z", "Y")
                region_3d.view_location = target
                if space.shading.type == "SOLID":
                    space.shading.color_type = "VERTEX"


def _doubt_message(reasons) -> str:
    return "; ".join(name for name, _ in reasons)


def _report_axis(operator, die, doubtful, reasons, umap, what: str) -> None:
    depth = 1000 * float(umap.vertex_depth.max())
    if doubtful:
        operator.report({"WARNING"}, f"{what}: insertion axis needs checking ({_doubt_message(reasons)}). "
                                     f"Deepest undercut {depth:.0f} um. Rotate the view and Set from View, or drag "
                                     "the axis handle")
    else:
        operator.report({"INFO"}, f"{what}. Deepest undercut {depth:.0f} um")


class DENTALCAD_OT_insertion_detect(bpy.types.Operator):
    """Compute the insertion axis automatically and show the undercut map (needs a confirmed margin)"""

    bl_idname = "dentalcad.insertion_detect"
    bl_label = "Detect Insertion Axis"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return obj is not None and obj.type == "MESH"

    def execute(self, context):
        die = context.active_object
        if not _gate(self, die):
            return {"CANCELLED"}
        try:
            result = core_insertion.default_axis(context_for(die))
        except core_insertion.InsertionError as exc:
            self.report({"ERROR"}, f"Insertion axis not found ({exc})")
            return {"CANCELLED"}
        doubtful, reasons, umap = apply_axis(context, die, result.axis, "auto", result.alternatives)
        die["dentalcad_insertion_alternatives"] = [list(a) for a in result.alternatives]
        if doubtful:
            _look_along(context, die, result.axis)
        _report_axis(self, die, doubtful, reasons, umap, "Insertion axis detected")
        return {"FINISHED"}


class DENTALCAD_OT_insertion_from_view(bpy.types.Operator):
    """Set the insertion axis to the current view: look onto the preparation from the desired insertion direction"""

    bl_idname = "dentalcad.insertion_from_view"
    bl_label = "Set from View"
    bl_options = {"REGISTER", "UNDO"}

    direction: FloatVectorProperty(name="Direction", subtype="DIRECTION", size=3, options={"HIDDEN"})
    use_direction: BoolProperty(default=False, options={"HIDDEN", "SKIP_SAVE"})

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return obj is not None and obj.type == "MESH" and KEY_AXIS in obj

    def execute(self, context):
        die = context.active_object
        if not _gate(self, die):
            return {"CANCELLED"}
        if self.use_direction:
            axis_world = Vector(self.direction)
        else:
            region_3d = getattr(context.space_data, "region_3d", None)
            if region_3d is None:
                self.report({"ERROR"}, "Run Set from View from the 3D Viewport")
                return {"CANCELLED"}
            axis_world = region_3d.view_rotation @ Vector((0.0, 0.0, 1.0))  # dari preparasi ke arah pengamat
        if axis_world.length == 0:
            self.report({"ERROR"}, "The view direction is undefined")
            return {"CANCELLED"}
        axis_local = (die.matrix_world.inverted().to_3x3() @ axis_world).normalized()
        doubtful, reasons, umap = apply_axis(context, die, np.array(axis_local), "view")
        _report_axis(self, die, doubtful, reasons, umap, "Insertion axis set from the view")
        return {"FINISHED"}


class DENTALCAD_OT_insertion_view(bpy.types.Operator):
    """Look onto the preparation along the insertion axis"""

    bl_idname = "dentalcad.insertion_view"
    bl_label = "View Along Axis"

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return obj is not None and KEY_AXIS in obj

    def execute(self, context):
        die = context.active_object
        if not _gate(self, die):
            return {"CANCELLED"}
        _look_along(context, die, np.array(die[KEY_AXIS], dtype=float))
        return {"FINISHED"}


class DENTALCAD_OT_block_out(bpy.types.Operator):
    """Block out the undercuts parallel to the insertion axis (input for the cement spacer)"""

    bl_idname = "dentalcad.block_out"
    bl_label = "Block Out Undercuts"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return obj is not None and obj.type == "MESH" and KEY_AXIS in obj

    def execute(self, context):
        die = context.active_object
        if not _gate(self, die):
            return {"CANCELLED"}
        param = material_preset().get("blockout_free_zone_mm")
        axis_local = np.array(die[KEY_AXIS], dtype=float)
        ctx = context_for(die)
        result = core_insertion.block_out(ctx, axis_local, float(param.value))
        residual = core_insertion.residual_shadow(ctx, result)
        name = blockout_name(die)
        old = bpy.data.objects.get(name)
        if old is not None:
            data = old.data
            bpy.data.objects.remove(old)
            if data is not None and data.users == 0:
                bpy.data.meshes.remove(data)
        obj = bpy.data.objects.new(name, to_blender_mesh(name, result.mesh))
        context.collection.objects.link(obj)
        obj.matrix_world = die.matrix_world
        obj.display_type = "WIRE"
        obj.hide_select = True
        obj[KEY_DIE] = die.name
        obj[KEY_BLOCKOUT_AXIS] = axis_local.tolist()
        obj[KEY_BLOCKOUT_RESIDUAL] = residual
        obj[KEY_BLOCKOUT_ZONE] = float(param.value)
        obj["dentalcad_blockout_stale"] = False
        moved = int(result.moved.sum())
        message = (f"Block-out: {moved} vertices moved, up to {1000 * float(result.displacement.max()):.0f} um; "
                   f"no block-out within {param.value} mm of the margin")
        if param.status == "perlu_kalibrasi":
            self.report({"WARNING"}, message + f". Not calibrated: blockout_free_zone_mm = {param.value} mm "
                                               "(exocad generic default)")
        else:
            self.report({"INFO"}, message)
        if residual > 0:
            self.report({"WARNING"}, f"Block-out left a shadow of {1000 * residual:.0f} um outside the free zone")
        return {"FINISHED"}


def handle_moved(context, die) -> bool:
    """Kalau bola pegangan digeser, sumbu = arah dari pangkal panah ke bola. Mengembalikan True bila diperbarui."""
    handle = bpy.data.objects.get(handle_name(die))
    if handle is None or KEY_BASE not in die or not require_confirmed_margin(die)[0]:
        return False
    last = Vector(die.get(KEY_HANDLE_LAST, [0.0, 0.0, 0.0]))
    if (handle.location - last).length < 1e-4:
        return False
    base_world = die.matrix_world @ Vector(die[KEY_BASE])
    direction = handle.location - base_world
    if direction.length < 1e-3:
        return False
    axis_local = (die.matrix_world.inverted().to_3x3() @ direction).normalized()
    apply_axis(context, die, np.array(axis_local), "handle")
    return True


@persistent
def _on_depsgraph_update(scene, depsgraph):
    if _updating:
        return
    for obj in scene.objects:
        die_name = obj.get(KEY_DIE)
        if die_name and obj.name.endswith(" Axis Handle"):
            die = bpy.data.objects.get(die_name)
            if die is not None:
                try:
                    handle_moved(bpy.context, die)
                except (core_insertion.InsertionError, core_margin.MarginError, KeyError):
                    pass


def register_handlers() -> None:
    if _on_depsgraph_update not in bpy.app.handlers.depsgraph_update_post:
        bpy.app.handlers.depsgraph_update_post.append(_on_depsgraph_update)


def unregister_handlers() -> None:
    if _on_depsgraph_update in bpy.app.handlers.depsgraph_update_post:
        bpy.app.handlers.depsgraph_update_post.remove(_on_depsgraph_update)
    _contexts.clear()
