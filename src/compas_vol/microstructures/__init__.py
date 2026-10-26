"""
********************************************************************************
compas_vol.microstructures
********************************************************************************

.. currentmodule:: compas_vol.microstructures

.. autosummary::
    :toctree: generated/
    :nosignatures:

    Lattice
    LatticePolar
    TPMS
    TPMSAttractor
    TPMSPolar
    TPMSSolid
    Voronoi

"""

from .lattice import LATTICE_TYPENAMES
from .lattice import Lattice
from .lattice_polar import LatticePolar
from .tpms import TPMSTYPES
from .tpms import TPMS
from .tpms import tpms_field
from .tpms_attractor import TPMSAttractor
from .tpms_polar import TPMSPolar
from .tpms_solid import TPMSMODES
from .tpms_solid import TPMSSolid
from .voronoi import Voronoi

__all__ = [
    "LATTICE_TYPENAMES",
    "TPMSMODES",
    "TPMSTYPES",
    "Lattice",
    "LatticePolar",
    "TPMS",
    "TPMSAttractor",
    "TPMSPolar",
    "TPMSSolid",
    "Voronoi",
    "tpms_field",
]
