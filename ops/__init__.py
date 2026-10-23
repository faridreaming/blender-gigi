# SPDX-License-Identifier: GPL-3.0-or-later
"""Operator Blender. Tipis: semua logika ada di core/."""

import bpy

from .coupons import DENTALCAD_OT_export_coupons
from .import_mesh import DENTALCAD_OT_import_ply, DENTALCAD_OT_import_stl
from .margin import DENTALCAD_OT_margin_detect, DENTALCAD_OT_margin_update

classes = (
    DENTALCAD_OT_import_stl,
    DENTALCAD_OT_import_ply,
    DENTALCAD_OT_export_coupons,
    DENTALCAD_OT_margin_detect,
    DENTALCAD_OT_margin_update,
)

register, unregister = bpy.utils.register_classes_factory(classes)
