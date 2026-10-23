# SPDX-License-Identifier: GPL-3.0-or-later
"""Panel dan state kasus di UI Blender."""

from . import panel_main


def register():
    panel_main.register()


def unregister():
    panel_main.unregister()
