"""
********************************************************************************
compas_vol.utilities
********************************************************************************

.. currentmodule:: compas_vol.utilities

What is left of the COMPAS 1 interface: iso-surfacing that accepts the old
``[(min, max, n), ...]`` bounds, and sending a tree between processes as JSON.
Everything here has a better equivalent in :mod:`compas_vol.meshing`; these
exist so that scripts written against the original package keep running.

Functions
=========

.. autosummary::
    :toctree: generated/
    :nosignatures:

    dumps_tree
    get_iso_mesh
    get_iso_vfs
    get_vfs_from_tree
    loads_tree

Drawing is not handled here. Volumetric objects are registered scene objects
(see :mod:`compas_vol.scene`), so they go straight into a COMPAS scene::

    viewer.scene.add(obj, bounds=20.0, resolution=100)

"""

from .comm import dumps_tree
from .comm import get_vfs_from_tree
from .comm import loads_tree
from .utils import get_iso_mesh
from .utils import get_iso_vfs

__all__ = [
    "dumps_tree",
    "get_iso_mesh",
    "get_iso_vfs",
    "get_vfs_from_tree",
    "loads_tree",
]
