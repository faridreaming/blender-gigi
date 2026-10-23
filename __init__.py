# SPDX-License-Identifier: GPL-3.0-or-later
"""DentalCAD: extension Blender untuk alur kerja dental CAD (Fase 0: fondasi)."""

import bpy

# core/ sengaja tidak diregistrasi: isinya Python + numpy murni, bukan class bpy.
register, unregister = bpy.utils.register_submodule_factory(
    __name__,
    ("ops", "ui", "gpu_draw"),
)
