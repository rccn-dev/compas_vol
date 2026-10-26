"""
********************************************************************************
compas_vol
********************************************************************************

.. currentmodule:: compas_vol

Volumetric modelling with signed distance functions, for COMPAS 2.

A fork of `dbt-ethz/compas_vol <https://github.com/dbt-ethz/compas_vol>`_,
originally by Mathias Bernhard at Digital Building Technologies, ETH Zurich,
updated for COMPAS 2, NumPy 2 and Python 3.13.

.. toctree::
    :maxdepth: 1

    compas_vol.primitives
    compas_vol.combinations
    compas_vol.modifications
    compas_vol.microstructures
    compas_vol.analysis
    compas_vol.meshing
    compas_vol.assembly
    compas_vol.scene
    compas_vol.nodes
    compas_vol.ghpython
    compas_vol.runtime
    compas_vol.utilities

"""

from .base import VolObject
from .base import format_number
from .base import inverse_matrix_from_frame
from .base import transform_numpy

__author__ = [
    "Mathias Bernhard <mathbern@design.upenn.edu>",
    "ChiaChing-Yen <ccyen@umich.edu>",
]
__copyright__ = (
    "2017-2021 Digital Building Technologies - ETH Zurich; "
    "2025-2026 compas_vol contributors"
)
__license__ = "MIT License"
__version__ = "0.2.0"

#: Modules COMPAS scans for plugins. COMPAS walks installed top-level packages
#: whose name starts with "compas" and reads this declaration, which is how the
#: scene object for volumetric objects gets registered without compas_vol
#: importing any viewer itself.
__all_plugins__ = ["compas_vol.scene"]

__all__ = [
    "VolObject",
    "format_number",
    "inverse_matrix_from_frame",
    "transform_numpy",
]
