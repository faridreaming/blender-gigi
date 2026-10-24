# SPDX-License-Identifier: GPL-3.0-or-later
"""Operator proposal crown, langkah 1 sampai 3 (docs/PHASE2.md §5.4). Logika di core/template.py dan core/crown.py.

"Propose Crown" butuh margin terkonfirmasi dan spacer yang belum kedaluwarsa (require_current_spacer). Nomor FDI,
gigi tetangga mesial/distal, dan antagonis dipilih di panel (langkah Crown); tetangga dan antagonis opsional.
Arah mesial (K9): dari tetangga bila ada; tanpa tetangga, dari panah "<die> Mesial Direction" yang bolanya
("<die> Mesial Handle") diseret pengguna dengan G. FDI hanya memberi petunjuk awal, dan status "needs checking".
Hasilnya "<die> Crown Proposal" (permukaan luar terbuka; border dan solid menyusul di langkah 4 dan 5). Proposal
kedaluwarsa bila margin, sumbu, block-out, spacer, FDI, arah mesial, tetangga, atau antagonis berubah.
"Confirm Crown" (K7) letaknya sebelum ekspor §5.7 dan belum dibuat.
"""

import bpy
import numpy as np
from mathutils import Matrix, Vector

from ..core import crown as core_crown
from ..core import margin as core_margin
from ..core import template as core_template
from ..core.mesh_data import MeshData
from . import insertion as ops_insertion
from . import spacer as ops_spacer
from .margin import KEY_CONTROLS, margin_controls
from .mesh_bridge import from_blender_mesh, to_blender_mesh

KEY_FINGERPRINT = "dentalcad_crown_fingerprint"
KEY_MESIAL = "dentalcad_mesial_dir"  # di die, frame lokal die
KEY_MESIAL_SOURCE = "dentalcad_mesial_source"  # "neighbors", "arrow", "fdi_hint"
KEY_MESIAL_BASE = "dentalcad_mesial_base"
KEY_HINTS = "dentalcad_crown_hints"
KEY_DISTANCES = "dentalcad_crown_distances_mm"
ARROW_MM = 5.0
HANDLE_MM = 0.6


def proposal_name(die) -> str:
    return f"{die.name} Crown Proposal"


def mesial_arrow_name(die) -> str:
    return f"{die.name} Mesial Direction"


def mesial_handle_name(die) -> str:
    return f"{die.name} Mesial Handle"


def crown_params() -> core_crown.CrownParams:
    preset = ops_insertion.material_preset()
    return core_crown.CrownParams(
        occlusal_distance_mm=preset.value("occlusal_distance_mm"),
        approximal_distance_mm=preset.value("approximal_distance_mm"),
        cement_gap_mm=preset.value("cement_gap_um") / 1000.0,
    )


def _local_mesh(obj, die) -> MeshData:
    """Mesh objek lain di frame lokal die."""
    mesh = from_blender_mesh(obj.data)
    matrix = np.array(die.matrix_world.inverted() @ obj.matrix_world)
    v = np.asarray(mesh.vertices, float) @ matrix[:3, :3].T + matrix[:3, 3]
    return MeshData(v, mesh.faces)


def _context_objects(context):
    case = context.scene.dentalcad_case
    return case.mesial_neighbor, case.distal_neighbor, case.antagonist


def _fingerprint(context, die) -> list:
    """Sidik semua masukan proposal: berubah = proposal kedaluwarsa."""
    case = context.scene.dentalcad_case
    parts = [float(x) for x in margin_controls(die)[KEY_CONTROLS]]
    parts += list(die.get(ops_insertion.KEY_AXIS, [0, 0, 0]))
    parts += [float(die.get(ops_insertion.KEY_BLOCKOUT_VERSION, -1)), float(die.get(ops_spacer.KEY_VERSION, -1))]
    parts += [float(case.fdi)] + list(die.get(KEY_MESIAL, [0, 0, 0]))
    if case.mesial_neighbor is None and case.distal_neighbor is None:
        # Tanpa tetangga, arah mesial dari bola pegangan: menyeretnya membuat proposal kedaluwarsa.
        handle = mesial_from_handle(die)
        parts += [0.0, 0.0, 0.0] if handle is None else [float(x) for x in np.round(handle, 9)]
    for obj in _context_objects(context):
        if obj is None:
            parts += [0.0]
        else:
            parts += [1.0, float(len(obj.data.vertices))] + [float(x) for row in obj.matrix_world for x in row]
    return parts


def crown_status(context, die) -> tuple[bool, str]:
    obj = bpy.data.objects.get(proposal_name(die))
    if obj is None:
        return False, f"{die.name} has no crown proposal yet: run Propose Crown"
    ok, message = ops_spacer.require_current_spacer(die)
    if not ok:
        return False, "Inputs changed after the crown proposal: " + message
    stored = list(obj.get(KEY_FINGERPRINT, []))
    current = _fingerprint(context, die)
    if len(stored) != len(current) or not np.allclose(stored, current, atol=1e-9):
        return False, ("The margin, axis, block-out, spacer, FDI, mesial direction, neighbours, or antagonist changed: "
                       "run Propose Crown again")
    return True, "Crown proposal is current"


def require_current_crown(context, die) -> tuple[bool, str]:
    """Gerbang untuk §5.5 sampai §5.7."""
    return crown_status(context, die)


def _fdi_hint(die, margin_local: np.ndarray, axis: np.ndarray, kind: str) -> np.ndarray:
    """Petunjuk awal arah mesial tanpa tetangga: sumbu utama elips fit margin (insisif dan molar) atau sumbu minor
    (premolar dan kaninus). Arah lengkung tidak diketahui, jadi tandanya sembarang dan statusnya "needs checking"."""
    z = axis / np.linalg.norm(axis)
    rel = margin_local - margin_local.mean(axis=0)
    flat = rel - (rel @ z)[:, None] * z
    _, _, vt = np.linalg.svd(flat, full_matrices=False)
    direction = vt[0] if kind in ("incisor", "molar") else vt[1]
    return direction - (direction @ z) * z


def _place_mesial_arrow(context, die, margin_local, axis_local, mesial_local) -> None:
    world = die.matrix_world
    base_local = margin_local.mean(axis=0)
    die[KEY_MESIAL_BASE] = base_local.tolist()
    base = world @ Vector(base_local)
    direction = (world.to_3x3() @ Vector(mesial_local)).normalized()
    arrow = ops_insertion._empty(context, mesial_arrow_name(die), "SINGLE_ARROW", ARROW_MM)
    arrow.matrix_world = Matrix.Translation(base) @ direction.to_track_quat("Z", "Y").to_matrix().to_4x4()
    arrow.hide_select = True
    arrow[ops_insertion.KEY_DIE] = die.name
    handle = ops_insertion._empty(context, mesial_handle_name(die), "SPHERE", HANDLE_MM)
    handle.location = base + direction * ARROW_MM
    handle[ops_insertion.KEY_DIE] = die.name


def mesial_from_handle(die) -> np.ndarray | None:
    """Arah mesial dari bola pegangan yang diseret pengguna (frame lokal die), tegak lurus sumbu."""
    handle = bpy.data.objects.get(mesial_handle_name(die))
    if handle is None or KEY_MESIAL_BASE not in die or ops_insertion.KEY_AXIS not in die:
        return None
    base = die.matrix_world @ Vector(die[KEY_MESIAL_BASE])
    direction = np.array(die.matrix_world.inverted().to_3x3() @ (handle.location - base))
    axis = np.array(die[ops_insertion.KEY_AXIS], dtype=float)
    direction = direction - (direction @ axis) * axis
    norm = np.linalg.norm(direction)
    return direction / norm if norm > 1e-6 else None


class DENTALCAD_OT_crown_propose(bpy.types.Operator):
    """Propose a crown from the parametric template: fitted to the margin, neighbours, and antagonist"""

    bl_idname = "dentalcad.crown_propose"
    bl_label = "Propose Crown"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return obj is not None and obj.type == "MESH" and ops_insertion.KEY_AXIS in obj

    def execute(self, context):
        die = context.active_object
        ok, message = ops_spacer.require_current_spacer(die)
        if not ok:
            self.report({"ERROR"}, message)
            return {"CANCELLED"}
        case = context.scene.dentalcad_case
        fdi = int(case.fdi)
        try:
            kind = core_template.fdi_kind(fdi)
        except ValueError:
            self.report({"ERROR"}, f"FDI {fdi} is not a valid tooth number (11 to 48, teeth 1 to 8)")
            return {"CANCELLED"}
        margin_local = core_margin.MarginCurve(
            np.array(margin_controls(die)[KEY_CONTROLS], dtype=float).reshape(-1, 3), None).sample(1024)
        axis = np.array(die[ops_insertion.KEY_AXIS], dtype=float)
        ctx = ops_insertion.context_for(die)
        prep_top = core_crown.prep_top_height(ctx.vertices[ctx.region.vertices], margin_local, axis)
        mesial_obj, distal_obj, antagonist_obj = _context_objects(context)
        meshes = [None if o is None else _local_mesh(o, die) for o in (mesial_obj, distal_obj, antagonist_obj)]
        mesial = core_crown.mesial_from_neighbors(margin_local, axis, meshes[0], meshes[1])
        if mesial is not None:
            source = "neighbors"
        else:
            mesial = mesial_from_handle(die)
            source = "arrow"
            if mesial is None:
                mesial = _fdi_hint(die, margin_local, axis, kind)
                source = "fdi_hint"
        die[KEY_MESIAL] = (mesial / np.linalg.norm(mesial)).tolist()
        die[KEY_MESIAL_SOURCE] = source
        _place_mesial_arrow(context, die, margin_local, axis, np.array(die[KEY_MESIAL]))
        try:
            fit = core_crown.fit_crown(fdi, margin_local, axis, np.array(die[KEY_MESIAL]), prep_top, *meshes,
                                       params=crown_params())
        except core_crown.CrownError as exc:
            self.report({"ERROR"}, f"Crown not proposed: {exc}")
            return {"CANCELLED"}
        name = proposal_name(die)
        old = bpy.data.objects.get(name)
        if old is not None:
            data = old.data
            bpy.data.objects.remove(old)
            if data is not None and data.users == 0:
                bpy.data.meshes.remove(data)
        obj = bpy.data.objects.new(name, to_blender_mesh(name, fit.surface.mesh))
        context.collection.objects.link(obj)
        obj.matrix_world = die.matrix_world
        obj.hide_select = True
        obj[ops_insertion.KEY_DIE] = die.name
        hints = list(fit.hints)
        if source != "neighbors":
            hints.append("mesial direction from " + ("the arrow" if source == "arrow" else "the FDI hint")
                         + "; check it and drag the mesial handle (G)")
        obj[KEY_HINTS] = "; ".join(hints)
        obj[KEY_DISTANCES] = {k: float(v) for k, v in fit.distances.items()}
        obj["dentalcad_crown_fdi"] = fdi
        obj[KEY_FINGERPRINT] = _fingerprint(context, die)
        t = fit.surface.template
        distances = ", ".join(f"{k} {1000 * v:+.0f} um" for k, v in fit.distances.items()) or "no contacts"
        self.report({"INFO"}, f"Crown proposal ({kind}, FDI {fdi}): {t.width_md:.2f} x {t.width_bl:.2f} mm, "
                              f"{fit.iterations} iterations; {distances}. Parametric template, not anatomy")
        if hints:
            self.report({"WARNING"}, "Needs checking: " + "; ".join(hints))
        return {"FINISHED"}

