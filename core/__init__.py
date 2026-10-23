# SPDX-License-Identifier: GPL-3.0-or-later
"""Logika inti DentalCAD: Python + numpy murni.

Aturan keras: tidak ada modul di paket ini yang boleh import bpy, bmesh, mathutils, atau gpu,
supaya semuanya bisa dites dengan pytest biasa tanpa Blender.
"""

from .mesh_data import MeshData

__all__ = ["MeshData"]
