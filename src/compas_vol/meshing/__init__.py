"""
********************************************************************************
compas_vol.meshing
********************************************************************************

.. currentmodule:: compas_vol.meshing

Classes
=======

.. autosummary::
    :toctree: generated/
    :nosignatures:

    OctNode
    Octree

Functions
=========

.. autosummary::
    :toctree: generated/
    :nosignatures:

    export_stl
    generate_mesh
    generate_vertices_and_faces
    iso_surface
    is_watertight
    normalize_bounds
    sample
    write_stl

"""

from .marching import generate_mesh
from .marching import generate_vertices_and_faces
from .marching import is_watertight
from .marching import iso_surface
from .marching import normalize_bounds
from .marching import sample
from .stl import export_stl
from .stl import write_stl
from .octree import OctNode
from .octree import Octree

__all__ = [
    "OctNode",
    "Octree",
    "export_stl",
    "generate_mesh",
    "generate_vertices_and_faces",
    "is_watertight",
    "iso_surface",
    "normalize_bounds",
    "sample",
    "write_stl",
]
