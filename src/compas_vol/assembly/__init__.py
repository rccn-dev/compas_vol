"""
********************************************************************************
compas_vol.assembly
********************************************************************************

.. currentmodule:: compas_vol.assembly

Cutting one field into pieces that can each be made, and each be computed.

Everywhere else in this package a model is one object. A building is not, and
the reason is not only that a pavilion will not fit on a print bed. A field
has no size, so describing a six-metre canopy costs nothing -- but *sampling*
one at 1 mm voxels is 6000 cubed: 216 billion samples, 1.7 TB as float64. The
model is fine. It is the evaluation that cannot happen, and it cannot happen
at any resolution worth having.

Segmenting solves both at once. Cut the same canopy into 400 mm pieces and
each one is 400 cubed at the same voxel size -- 64 million samples, 512 MB,
minutes rather than never. Nothing is approximated: every piece evaluates the
same field over a smaller box. They are independent, so they can be built on
different machines, in any order, and a piece can be rebuilt without touching
its neighbours.

The pieces then need to go back together, which is where a field stops
helping. Two parts modelled touching do not assemble; a flat cut locates
nothing. :class:`Pins` adds the clearance and the registration features, and
puts them only where the model has material to hold them.

Where to cut is a construction question before it is a geometric one, so
``segment(cells=...)`` takes any layout of boxes -- the parts a structure is
built from -- and :func:`place_cuts` moves a cut to where it meets the most
material. A model made by a process is built the same way, a piece at a time:
:meth:`Piece.bake` runs the process over the piece and a halo around it, on a
lattice its neighbours share, so the pieces meet where they were cut.

.. autosummary::
    :toctree: generated/
    :nosignatures:

    segment
    place_cuts
    section_cost
    Assembly
    Piece
    Pins
    Seams

"""

from .joints import Pins
from .layout import place_cuts
from .layout import section_cost
from .partition import Assembly
from .partition import Piece
from .partition import Seams
from .partition import segment

__all__ = [
    "Assembly",
    "Piece",
    "Pins",
    "Seams",
    "place_cuts",
    "section_cost",
    "segment",
]
