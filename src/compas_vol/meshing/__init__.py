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

    generate_mesh
    generate_vertices_and_faces
    normalize_bounds
    sample

"""

from .marching import generate_mesh
from .marching import generate_vertices_and_faces
from .marching import normalize_bounds
from .marching import sample
from .octree import OctNode
from .octree import Octree

__all__ = [
    "OctNode",
    "Octree",
    "generate_mesh",
    "generate_vertices_and_faces",
    "normalize_bounds",
    "sample",
]
