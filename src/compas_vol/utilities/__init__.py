"""
********************************************************************************
compas_vol.utilities
********************************************************************************

.. currentmodule:: compas_vol.utilities

Functions
=========

.. autosummary::
    :toctree: generated/
    :nosignatures:

    bbox_edges
    dumps_tree
    export_ipv_mesh
    export_layer
    export_ski_mesh
    get_compas_mesh
    get_iso_mesh
    get_iso_vfs
    get_random_vector_2D
    get_random_vector_3D
    get_vfs_from_tree
    loads_tree

Drawing is not handled here. Volumetric objects are registered scene objects
(see :mod:`compas_vol.scene`), so they go straight into a COMPAS scene::

    viewer.scene.add(obj, bounds=20.0, resolution=100)

"""

from .comm import dumps_tree
from .comm import get_vfs_from_tree
from .comm import loads_tree
from .utils import bbox_edges
from .utils import export_ipv_mesh
from .utils import export_layer
from .utils import export_ski_mesh
from .utils import get_compas_mesh
from .utils import get_iso_mesh
from .utils import get_iso_vfs
from .utils import get_random_vector_2D
from .utils import get_random_vector_3D

__all__ = [
    "bbox_edges",
    "dumps_tree",
    "export_ipv_mesh",
    "export_layer",
    "export_ski_mesh",
    "get_compas_mesh",
    "get_iso_mesh",
    "get_iso_vfs",
    "get_random_vector_2D",
    "get_random_vector_3D",
    "get_vfs_from_tree",
    "loads_tree",
]
