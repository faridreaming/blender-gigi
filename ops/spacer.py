# SPDX-License-Identifier: GPL-3.0-or-later
"""Operator spacer cement gap (docs/PHASE2.md §5.3). Logika di core/spacer.py dan core/geodesic.py.

"Create Cement Spacer" hanya jalan kalau margin sudah dikonfirmasi dan block-out (§5.2) dibuat untuk sumbu yang
sedang dipakai. Urutannya block-out dulu, lalu cement gap (konvensi exocad untuk milling 5-axis). Hasilnya
"<die> Spacer" (permukaan dalam crown). Spacer tidak punya status draf/terkonfirmasi, tetapi kedaluwarsa begitu
margin, sumbu, atau block-out berubah; require_current_spacer() adalah gerbang untuk §5.4.

Preset `milling_axes`: 3 atau 4 axis menambah block-out kedua sejajar sumbu setelah cement gap (opsi
use_second_block_out, default aktif); 5 axis tidak, tetapi undercut permukaan dalam ditulis sebagai skala warna
dan ditampilkan dengan "Show Undercuts". Catatan paten EP2187833B1 di docs/PHASE2.md §5.3 dan README.md:
pengguna di Eropa sebaiknya mematikan use_second_block_out sampai paten berakhir (bukan kesimpulan hukum).
"""

import bpy
import numpy as np
from bpy.props import BoolProperty

from ..core import spacer as core_spacer
from . import insertion as ops_insertion
from .margin import KEY_CONTROLS, margin_controls, require_confirmed_margin
from .mesh_bridge import from_blender_mesh, to_blender_mesh

KEY_DIE = "dentalcad_spacer_die"
KEY_MARGIN = "dentalcad_spacer_margin"
KEY_AXIS = "dentalcad_spacer_axis"
KEY_BLOCKOUT_VERSION = "dentalcad_spacer_blockout_version"
KEY_FOLDED = "dentalcad_spacer_folded_faces"
KEY_SLIVERS = "dentalcad_spacer_folded_slivers"
KEY_NEW_UNDERCUT = "dentalcad_spacer_new_undercut_mm"
KEY_NOISY = "dentalcad_spacer_noisy"
KEY_AXES = "dentalcad_spacer_milling_axes"
KEY_SECOND = "dentalcad_spacer_second_block_out"
KEY_INNER_UNDERCUT = "dentalcad_spacer_inner_undercut_mm"
KEY_VERSION = "dentalcad_spacer_version"  # di die dan spacer: naik setiap spacer dibuat ulang  # undercut tersisa di permukaan dalam akhir
UNDERCUT_COLOR = "DentalCAD Undercut"
SPACER_COLOR = (0.35, 0.65, 0.95, 1.0)


def spacer_name(die) -> str:
    return f"{die.name} Spacer"


def _material() -> bpy.types.Material:
    material = bpy.data.materials.get("DentalCAD Spacer")
    if material is None:
        material = bpy.data.materials.new("DentalCAD Spacer")
    material.diffuse_color = SPACER_COLOR
    return material


def spacer_status(die) -> tuple[bool, str]:
    """(berlaku, pesan): spacer ada dan dibuat dari margin, sumbu, dan block-out yang sekarang dipakai."""
    obj = bpy.data.objects.get(spacer_name(die))
    if obj is None:
        return False, f"{die.name} has no cement spacer yet: run Create Cement Spacer"
    ok, message = require_confirmed_margin(die)
    if not ok:
        return False, "The margin changed after the spacer was made: " + message
    controls = margin_controls(die)
    if list(controls[KEY_CONTROLS]) != list(obj.get(KEY_MARGIN, [])):
        return False, "The margin changed after the spacer was made: run Create Cement Spacer again"
    if ops_insertion.KEY_AXIS not in die or not np.allclose(obj.get(KEY_AXIS, [0, 0, 0]), die[ops_insertion.KEY_AXIS],
                                                           atol=1e-9):
        return False, "The insertion axis changed after the spacer was made: run Block Out and the spacer again"
    blocked = bpy.data.objects.get(ops_insertion.blockout_name(die))
    if blocked is None or int(blocked.get(ops_insertion.KEY_BLOCKOUT_VERSION, -1)) != int(obj.get(KEY_BLOCKOUT_VERSION, -2)):
        return False, "The block-out changed after the spacer was made: run Create Cement Spacer again"
    ok, message = ops_insertion.require_current_block_out(die)
    if not ok:
        return False, message
    return True, "Cement spacer is current"


def require_current_spacer(die) -> tuple[bool, str]:
    """Gerbang untuk §5.4 dan seterusnya."""
    return spacer_status(die)


class DENTALCAD_OT_spacer(bpy.types.Operator):
    """Create the inner crown surface: cement gap and spacing on the blocked-out die (needs a current block-out)"""

    bl_idname = "dentalcad.spacer"
    bl_label = "Create Cement Spacer"
    bl_options = {"REGISTER", "UNDO"}

    use_second_block_out: BoolProperty(
        name="Second Block-out (3/4 axis)", default=True,
        description="For 3 or 4 axis milling, block out the crown bottom again parallel to the insertion axis after "
                    "the cement gap. In Europe, see the patent note in README.md before using this",
    )

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return obj is not None and obj.type == "MESH" and ops_insertion.KEY_AXIS in obj

    def execute(self, context):
        die = context.active_object
        ok, message = ops_insertion.require_current_block_out(die)  # termasuk gerbang margin terkonfirmasi
        if not ok:
            self.report({"ERROR"}, message)
            return {"CANCELLED"}
        preset = ops_insertion.material_preset()
        params = core_spacer.SpacerParams.from_preset(preset)
        ctx = ops_insertion.context_for(die)
        blocked_obj = bpy.data.objects[ops_insertion.blockout_name(die)]
        blocked = from_blender_mesh(blocked_obj.data)
        axis = np.array(die[ops_insertion.KEY_AXIS], dtype=float)
        faces = core_spacer.inner_faces(blocked.vertices.astype(float), blocked.faces, ctx.region.faces,
                                        ctx.region.band_faces, ctx.margin)
        try:
            result = core_spacer.spacer_surface(blocked, faces, ctx.margin, axis, params, ctx.noise_sigma_mm)
        except core_spacer.SpacerError as exc:
            self.report({"ERROR"}, f"Cement spacer not created ({exc})")
            return {"CANCELLED"}
        new_undercut = core_spacer.new_undercut_mm(result, ctx.margin)
        axes_param = preset.get("milling_axes")
        axes = int(axes_param.value)
        second = None
        inner_mesh = result.mesh
        if axes in (3, 4) and self.use_second_block_out:
            second = core_spacer.second_block_out(result, ctx.margin)
            inner_mesh = second.mesh
        depth = core_spacer.inner_undercut_depth(inner_mesh, axis, ctx.margin)

        name = spacer_name(die)
        old = bpy.data.objects.get(name)
        if old is not None:
            data = old.data
            bpy.data.objects.remove(old)
            if data is not None and data.users == 0:
                bpy.data.meshes.remove(data)
        obj = bpy.data.objects.new(name, to_blender_mesh(name, inner_mesh))
        context.collection.objects.link(obj)
        obj.matrix_world = die.matrix_world
        obj.data.materials.append(_material())
        obj.hide_select = True
        obj[KEY_DIE] = die.name
        obj[KEY_MARGIN] = list(margin_controls(die)[KEY_CONTROLS])
        obj[KEY_AXIS] = axis.tolist()
        obj[KEY_BLOCKOUT_VERSION] = int(blocked_obj.get(ops_insertion.KEY_BLOCKOUT_VERSION, 0))
        die[KEY_VERSION] = int(die.get(KEY_VERSION, 0)) + 1
        obj[KEY_VERSION] = die[KEY_VERSION]
        obj[KEY_FOLDED] = result.folded_faces - result.folded_slivers
        obj[KEY_SLIVERS] = result.folded_slivers
        obj[KEY_NEW_UNDERCUT] = new_undercut
        noisy, sigma = ops_insertion.noisy_scan(die)
        obj[KEY_NOISY] = noisy
        obj[KEY_AXES] = axes
        obj[KEY_SECOND] = second is not None
        obj[KEY_INNER_UNDERCUT] = float(depth.max()) if len(depth) else 0.0
        attr = obj.data.color_attributes.new(UNDERCUT_COLOR, "FLOAT_COLOR", "POINT")
        attr.data.foreach_set("color", ops_insertion._depth_colors(depth).astype(np.float32).ravel())
        obj.data.color_attributes.active_color = attr

        self.report({"INFO"}, f"Cement spacer: gap {1000 * params.cement_gap_mm:.0f} um from "
                              f"{params.from_margin_mm:g} mm (linear over {params.transition_mm:g} mm), radial "
                              f"{1000 * params.radial_mm:.0f} um, axial {1000 * params.axial_mm:.0f} um on "
                              f"{len(result.vertex_index)} vertices")
        uncalibrated = [p for p in preset.params.values()
                        if p.status == "perlu_kalibrasi" and p.name in ("axial_spacing_um", "cement_gap_transition_mm")]
        if uncalibrated:
            self.report({"WARNING"}, "Not calibrated: " + ", ".join(f"{p.name} = {p.value} {p.unit}" for p in uncalibrated))
        if result.folded_faces - result.folded_slivers > 0:
            self.report({"WARNING"}, f"{result.folded_faces - result.folded_slivers} inner faces are folded")
        if second is not None:
            self.report({"INFO"}, f"{axes}-axis milling ({axes_param.status_label}): second block-out after the cement "
                                  f"gap moved {int(second.moved.sum())} vertices, up to "
                                  f"{1000 * float(second.displacement.max()):.0f} um; remaining undercut "
                                  f"{1000 * obj[KEY_INNER_UNDERCUT]:.0f} um")
        elif new_undercut > 0:
            reason = "5-axis milling, no second block-out" if axes == 5 else "second block-out turned off"
            self.report({"WARNING"}, f"The cement gap created a new undercut of up to {1000 * new_undercut:.0f} um "
                                     f"in the crown bottom ({reason}); use Show Undercuts")
        if noisy:
            self.report({"WARNING"}, f"Noisy scan (estimated noise {1000 * sigma:.0f} um): normals and distances "
                                     "on the spacer are approximate")
        return {"FINISHED"}


class DENTALCAD_OT_spacer_show_undercuts(bpy.types.Operator):
    """Show the undercuts of the crown bottom (cement spacer) with a colour scale"""

    bl_idname = "dentalcad.spacer_show_undercuts"
    bl_label = "Show Undercuts"

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return obj is not None and bpy.data.objects.get(spacer_name(obj)) is not None

    def execute(self, context):
        die = context.active_object
        obj = bpy.data.objects[spacer_name(die)]
        attr = obj.data.color_attributes.get(UNDERCUT_COLOR)
        if attr is None:
            self.report({"ERROR"}, "Run Create Cement Spacer again to compute the undercut map")
            return {"CANCELLED"}
        obj.data.color_attributes.active_color = attr
        screen = context.screen
        if screen is not None:
            for area in screen.areas:
                for space in area.spaces:
                    if space.type == "VIEW_3D" and space.shading.type == "SOLID":
                        space.shading.color_type = "VERTEX"
        axes = obj.get(KEY_AXES, 0)
        self.report({"INFO"}, f"Crown bottom: deepest undercut {1000 * obj.get(KEY_INNER_UNDERCUT, 0.0):.0f} um "
                              f"({axes}-axis milling)")
        return {"FINISHED"}
