# SPDX-License-Identifier: GPL-3.0-or-later
"""Operator Blender. Tipis: semua logika ada di core/."""

import bpy

from .import_mesh import DENTALCAD_OT_import_ply, DENTALCAD_OT_import_stl

classes = (
    DENTALCAD_OT_import_stl,
    DENTALCAD_OT_import_ply,
)

register, unregister = bpy.utils.register_classes_factory(classes)
