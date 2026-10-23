# SPDX-License-Identifier: GPL-3.0-or-later
"""Operator Blender. Tipis: semua logika ada di core/."""

import bpy

from .coupons import DENTALCAD_OT_export_coupons
from .import_mesh import DENTALCAD_OT_import_ply, DENTALCAD_OT_import_stl
from .margin import (
    DENTALCAD_OT_margin_confirm,
    DENTALCAD_OT_margin_detect,
    DENTALCAD_OT_margin_draw,
    DENTALCAD_OT_margin_update,
    DENTALCAD_PG_margin_point,
)
from .synthetic_case import DENTALCAD_OT_load_synthetic_case

classes = (
    DENTALCAD_OT_import_stl,
    DENTALCAD_OT_import_ply,
    DENTALCAD_OT_export_coupons,
    DENTALCAD_OT_margin_detect,
    DENTALCAD_PG_margin_point,
    DENTALCAD_OT_margin_draw,
    DENTALCAD_OT_margin_update,
    DENTALCAD_OT_margin_confirm,
    DENTALCAD_OT_load_synthetic_case,
)

register, unregister = bpy.utils.register_classes_factory(classes)
