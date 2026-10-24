# SPDX-License-Identifier: GPL-3.0-or-later
"""Operator spacer cement gap (docs/PHASE2.md §5.3). Logika di core/spacer.py dan core/geodesic.py.

"Create Cement Spacer" hanya jalan kalau margin sudah dikonfirmasi dan block-out (§5.2) dibuat untuk sumbu yang
sedang dipakai. Urutannya block-out dulu, lalu cement gap (konvensi exocad untuk milling 5-axis). Hasilnya
"<die> Spacer" (permukaan dalam crown). Spacer tidak punya status draf/terkonfirmasi, tetapi kedaluwarsa begitu
margin, sumbu, atau block-out berubah; require_current_spacer() adalah gerbang untuk §5.4.
"""

import bpy
import numpy as np

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
            result = core_spacer.spacer_surface(blocked, faces, ctx.margin, axis, params)
        except core_spacer.SpacerError as exc:
            self.report({"ERROR"}, f"Cement spacer not created ({exc})")
            return {"CANCELLED"}
        new_undercut = core_spacer.new_undercut_mm(result, ctx.margin)

        name = spacer_name(die)
        old = bpy.data.objects.get(name)
        if old is not None:
            data = old.data
            bpy.data.objects.remove(old)
            if data is not None and data.users == 0:
                bpy.data.meshes.remove(data)
        obj = bpy.data.objects.new(name, to_blender_mesh(name, result.mesh))
        context.collection.objects.link(obj)
        obj.matrix_world = die.matrix_world
        obj.data.materials.append(_material())
        obj.hide_select = True
        obj[KEY_DIE] = die.name
        obj[KEY_MARGIN] = list(margin_controls(die)[KEY_CONTROLS])
        obj[KEY_AXIS] = axis.tolist()
        obj[KEY_BLOCKOUT_VERSION] = int(blocked_obj.get(ops_insertion.KEY_BLOCKOUT_VERSION, 0))
        obj[KEY_FOLDED] = result.folded_faces - result.folded_slivers
        obj[KEY_SLIVERS] = result.folded_slivers
        obj[KEY_NEW_UNDERCUT] = new_undercut
        noisy, sigma = ops_insertion.noisy_scan(die)
        obj[KEY_NOISY] = noisy

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
        if new_undercut > 0:
            self.report({"WARNING"}, f"The cement gap created a new undercut of up to {1000 * new_undercut:.0f} um "
                                     "in the crown bottom")
        if noisy:
            self.report({"WARNING"}, f"Noisy scan (estimated noise {1000 * sigma:.0f} um): normals and distances "
                                     "on the spacer are approximate")
        return {"FINISHED"}
