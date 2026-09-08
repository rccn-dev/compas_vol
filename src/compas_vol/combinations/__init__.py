"""
********************************************************************************
compas_vol.combinations
********************************************************************************

.. currentmodule:: compas_vol.combinations

.. autosummary::
    :toctree: generated/
    :nosignatures:

    Addition
    Blend
    Division
    Intersection
    Morph
    Multiplication
    SmoothIntersection
    SmoothSubtraction
    SmoothUnion
    SmoothUnionList
    Subtraction
    Union

"""

from .addition import Addition
from .blend import LINEAR
from .blend import QUADRATIC
from .blend import Blend
from .division import Division
from .intersection import Intersection
from .morph import Morph
from .multiplication import Multiplication
from .smoothintersection import SmoothIntersection
from .smoothsubtraction import SmoothSubtraction
from .smoothunion import SmoothUnion
from .smoothunionlist import SmoothUnionList
from .subtraction import Subtraction
from .union import Union

__all__ = [
    "LINEAR",
    "QUADRATIC",
    "Addition",
    "Blend",
    "Division",
    "Intersection",
    "Morph",
    "Multiplication",
    "SmoothIntersection",
    "SmoothSubtraction",
    "SmoothUnion",
    "SmoothUnionList",
    "Subtraction",
    "Union",
]
