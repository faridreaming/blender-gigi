# SPDX-License-Identifier: GPL-3.0-or-later
"""Operator Blender. Tipis: semua logika ada di core/."""

import bpy

from .coupons import DENTALCAD_OT_export_coupons
from .import_mesh import DENTALCAD_OT_import_ply, DENTALCAD_OT_import_stl
from .insertion import (
    DENTALCAD_OT_block_out,
    DENTALCAD_OT_insertion_detect,
    DENTALCAD_OT_insertion_from_view,
    DENTALCAD_OT_insertion_view,
    register_handlers,
    unregister_handlers,
)
from .margin import (
    DENTALCAD_OT_margin_confirm,
    DENTALCAD_OT_margin_detect,
    DENTALCAD_OT_margin_draw,
    DENTALCAD_OT_margin_update,
    DENTALCAD_PG_margin_point,
)
from .spacer import DENTALCAD_OT_spacer, DENTALCAD_OT_spacer_show_undercuts
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
    DENTALCAD_OT_insertion_detect,
    DENTALCAD_OT_insertion_from_view,
    DENTALCAD_OT_insertion_view,
    DENTALCAD_OT_block_out,
    DENTALCAD_OT_spacer,
    DENTALCAD_OT_spacer_show_undercuts,
)

_register_classes, _unregister_classes = bpy.utils.register_classes_factory(classes)


def register():
    _register_classes()
    register_handlers()


def unregister():
    unregister_handlers()
    _unregister_classes()
