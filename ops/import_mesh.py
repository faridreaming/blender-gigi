# SPDX-License-Identifier: GPL-3.0-or-later
"""Operator impor scan STL/PLY."""

import time
from pathlib import Path

import bpy
from bpy.props import StringProperty
from bpy_extras.io_utils import ImportHelper

from ..core import mesh_io
from .mesh_bridge import to_blender_mesh


class _ImportMeshBase(ImportHelper):
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        path = Path(self.filepath)
        start = time.perf_counter()
        try:
            data = mesh_io.load_mesh(path)
        except Exception as exc:  # pesan error file apa pun harus sampai ke pengguna, bukan traceback
            self.report({"ERROR"}, f"Cannot import {path.name}: {exc}")
            return {"CANCELLED"}

        mesh = to_blender_mesh(path.stem, data)
        obj = bpy.data.objects.new(path.stem, mesh)
        context.collection.objects.link(obj)
        for other in context.selected_objects:
            other.select_set(False)
        obj.select_set(True)
        context.view_layer.objects.active = obj

        seconds = time.perf_counter() - start
        self.report({"INFO"}, f"Imported {path.name}: {len(data.faces):,} triangles in {seconds:.2f} s")
        return {"FINISHED"}


class DENTALCAD_OT_import_stl(_ImportMeshBase, bpy.types.Operator):
    """Import an STL scan as a mesh object (units: mm)"""

    bl_idname = "dentalcad.import_stl"
    bl_label = "Import STL Scan"

    filename_ext = ".stl"
    filter_glob: StringProperty(default="*.stl", options={"HIDDEN"})


class DENTALCAD_OT_import_ply(_ImportMeshBase, bpy.types.Operator):
    """Import a PLY scan as a mesh object, keeping vertex colors (units: mm)"""

    bl_idname = "dentalcad.import_ply"
    bl_label = "Import PLY Scan"

    filename_ext = ".ply"
    filter_glob: StringProperty(default="*.ply", options={"HIDDEN"})
