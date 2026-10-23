# SPDX-License-Identifier: GPL-3.0-or-later
"""Jembatan MeshData <-> bpy.types.Mesh lewat foreach_set/foreach_get (tanpa loop per-vertex)."""

import bpy
import numpy as np

from ..core.mesh_data import MeshData

COLOR_ATTRIBUTE_NAME = "Scan Color"


def to_blender_mesh(name: str, data: MeshData) -> bpy.types.Mesh:
    n_verts = len(data.vertices)
    n_faces = len(data.faces)

    mesh = bpy.data.meshes.new(name)
    mesh.vertices.add(n_verts)
    mesh.vertices.foreach_set("co", data.vertices.astype(np.float32).ravel())

    mesh.loops.add(n_faces * 3)
    mesh.loops.foreach_set("vertex_index", data.faces.astype(np.int32).ravel())

    mesh.polygons.add(n_faces)
    mesh.polygons.foreach_set("loop_start", np.arange(0, n_faces * 3, 3, dtype=np.int32))

    if data.vertex_colors is not None:
        attr = mesh.color_attributes.new(COLOR_ATTRIBUTE_NAME, "BYTE_COLOR", "POINT")
        attr.data.foreach_set("color_srgb", (data.vertex_colors.astype(np.float32) / 255.0).ravel())
        mesh.color_attributes.active_color = attr
        mesh.color_attributes.render_color_index = mesh.color_attributes.active_color_index

    mesh.update()
    return mesh


def from_blender_mesh(mesh: bpy.types.Mesh) -> MeshData:
    """Baca balik mesh segitiga dari Blender (dipakai uji integrasi)."""
    n_verts = len(mesh.vertices)
    co = np.empty(n_verts * 3, dtype=np.float32)
    mesh.vertices.foreach_get("co", co)

    sizes = np.empty(len(mesh.polygons), dtype=np.int32)
    mesh.polygons.foreach_get("loop_total", sizes)
    if np.any(sizes != 3):
        raise ValueError("mesh berisi polygon non-segitiga")
    corners = np.empty(len(mesh.loops), dtype=np.int32)
    mesh.loops.foreach_get("vertex_index", corners)

    colors = None
    attr = mesh.color_attributes.get(COLOR_ATTRIBUTE_NAME)
    if attr is not None:
        rgba = np.empty(n_verts * 4, dtype=np.float32)
        attr.data.foreach_get("color_srgb", rgba)
        colors = np.round(rgba.reshape(-1, 4) * 255.0).astype(np.uint8)

    return MeshData(vertices=co.reshape(-1, 3), faces=corners.reshape(-1, 3), vertex_colors=colors)
