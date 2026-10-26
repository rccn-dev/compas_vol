"""Every TPMS type, at one cell size and wall thickness.

``TPMSSolid`` takes ``cell_size`` and ``thickness`` in model units, and ``mode``
(``"sheet"`` or ``"network"``). With one size and thickness for all seven, the
differences are purely topological. Each formula is a nodal approximation of
the minimal surface.
"""

from compas.geometry import Box
from compas.geometry import Frame

from compas_vol.combinations import Intersection
from compas_vol.combinations import Union
from compas_vol.microstructures import TPMSTYPES
from compas_vol.microstructures import TPMSSolid
from compas_vol.primitives import VolBox

from _common import demo

# ==============================================================================
# Parameters
# ==============================================================================

CELL_SIZE = 10.0  # one unit cell, mm
THICKNESS = 1.0  # wall thickness, mm
SAMPLE = 20.0  # edge of each sample cube, mm  (= 2 x 2 x 2 cells)
GAP = 6.0  # space between samples, mm

# ==============================================================================
# Model
# ==============================================================================

samples = []
for i, tpmstype in enumerate(TPMSTYPES):
    # Every sample cube is centred on a cell corner, so all seven start their
    # pattern at the same phase and read as a like-for-like comparison.
    frame = Frame(((SAMPLE + GAP) * i, 0, 0), (1, 0, 0), (0, 1, 0))
    solid = TPMSSolid(tpmstype, cell_size=CELL_SIZE, thickness=THICKNESS, frame=frame)
    samples.append(Intersection(solid, VolBox(Box(SAMPLE, SAMPLE, SAMPLE, frame=frame), 0.0)))

shape = Union(samples)

half = SAMPLE / 2 + 1
BOUNDS = (-half, -half, -half, (SAMPLE + GAP) * (len(TPMSTYPES) - 1) + half, half, half)
RESOLUTION = (700, 90, 90)

if __name__ == "__main__":
    print("left to right:", ", ".join(TPMSTYPES))
    demo(shape, "tpms_catalogue", bounds=BOUNDS, resolution=RESOLUTION)
