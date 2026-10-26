"""
********************************************************************************
compas_vol.processes
********************************************************************************

.. currentmodule:: compas_vol.processes

Geometry made by process rather than by construction: erosion, growth, phase
separation. Where the rest of the package describes a shape with an
expression, these iterate on a sampled field and let the result emerge.

All of them share one operator. A process moves the surface along its normal
at a speed that varies across it::

    phi <- phi + speed * |grad phi|      then redistance

A positive speed takes material away, a negative one adds it. Weathering and
growth are the same loop with the sign flipped, which is why they are not
separate machinery, and why what distinguishes one process from another is
its speed term, not its code.

Three rules hold the subpackage together:

1. **Everything returns a valid distance field.** Redistancing is part of the
   loop, not the caller's problem, because every operation downstream --
   shells, offsets, thicknesses in millimetres -- depends on it.
2. **Everything is in model units.** Including the lengths that curvature and
   shelter are measured against. A curvature term compared against the voxel
   size instead of a real length is the difference between a coral and a ball.
3. **:class:`compas_vol.primitives.VolGrid` is the way back.** Processes are
   grid-native; wrapping the result returns it to the modelling world, where
   it can be shelled, cut, filled with a lattice and exported.

What a process may not touch is said once, on the field:
:meth:`Field.constrain` keeps a solid (a beam, a deck) and an envelope, and
because every process ends its steps by redistancing, which is where the
constraint is imposed, every process honours it.

Requires the ``processes`` extra (``pip install compas-vol[processes]``) for
scikit-fmm, which does the redistancing.

Classes
=======

.. autosummary::
    :toctree: generated/
    :nosignatures:

    Field

Functions
=========

.. autosummary::
    :toctree: generated/
    :nosignatures:

    evolve
    redistance
    lattice
    opened
    closed
    value_noise
    fbm
    hardness
    abrasion
    differential
    pitting
    strata
    runoff
    jointing
    fingering
    accretion
    diffusion_limited
    branching
    spinodal
    reaction_diffusion

"""

from .field import Field
from .field import lattice
from .field import redistance
from .evolve import evolve
from .morphology import closed
from .morphology import opened
from .noise import fbm
from .noise import value_noise
from .weathering import abrasion
from .weathering import differential
from .weathering import hardness
from .weathering import jointing
from .weathering import pitting
from .weathering import runoff
from .weathering import strata
from .growth import accretion
from .growth import branching
from .growth import diffusion_limited
from .growth import fingering
from .generators import reaction_diffusion
from .generators import spinodal
from . import terms

__all__ = [
    "Field",
    "abrasion",
    "accretion",
    "branching",
    "closed",
    "differential",
    "diffusion_limited",
    "evolve",
    "fbm",
    "fingering",
    "hardness",
    "jointing",
    "lattice",
    "opened",
    "pitting",
    "reaction_diffusion",
    "redistance",
    "runoff",
    "spinodal",
    "strata",
    "terms",
    "value_noise",
]
