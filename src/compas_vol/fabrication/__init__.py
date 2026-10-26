"""
********************************************************************************
compas_vol.fabrication
********************************************************************************

.. currentmodule:: compas_vol.fabrication

What stops a solid printing, found on the grid it was modelled on, and fixed
there too.

The checks are the ones a slicer would make, but earlier: separate pieces,
sealed cavities, overhangs, layers that start in mid-air, walls too thin for
the process. Each returns a number rather than a warning, so a design can be
held to it -- and each has a repair beside it, where a repair is possible.

The repairs change the geometry. Draining a cavity puts a hole through a wall;
making an overhang self-supporting adds material nobody drew. They are offered
as decisions, not as cleanup, and each reports what it did.

Functions
=========

.. autosummary::
    :toctree: generated/
    :nosignatures:

    inspect
    surface_normals
    largest_piece
    keep_largest
    drain_voids
    make_self_supporting

Classes
=======

.. autosummary::
    :toctree: generated/
    :nosignatures:

    Report

"""

from .analysis import Report
from .analysis import inspect
from .analysis import surface_normals
from ._grid import largest_piece
from .repair import drain_voids
from .repair import keep_largest
from .repair import make_self_supporting

__all__ = [
    "Report",
    "drain_voids",
    "inspect",
    "keep_largest",
    "largest_piece",
    "make_self_supporting",
    "surface_normals",
]
