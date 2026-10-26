"""One TPMS surface made solid three ways: sheet, network, inverted network.

A sheet thickens the surface and keeps both labyrinths open; it tends to be
stiffer for its weight. A network fills one labyrinth and deforms by bending;
``invert=True`` fills the other, and ``offset`` sets its density in model units.
The script prints each solid volume fraction.
"""

from compas.geometry import Box
from compas.geometry import Frame

from compas_vol.combinations import Intersection
from compas_vol.combinations import Union
from compas_vol.meshing import sample
from compas_vol.microstructures import TPMSSolid
from compas_vol.primitives import VolBox

from _common import demo

# ==============================================================================
# Parameters
# ==============================================================================

TPMSTYPE = "IWP"  # the I-WP's two labyrinths differ, so the networks differ too
CELL_SIZE = 12.0
THICKNESS = 1.2
NETWORK_OFFSET = 0.0
SAMPLE = 24.0
GAP = 8.0

# ==============================================================================
# Model
# ==============================================================================

variants = {
    "sheet": dict(mode="sheet", thickness=THICKNESS),
    "network": dict(mode="network", offset=NETWORK_OFFSET),
    "network, inverted": dict(mode="network", offset=NETWORK_OFFSET, invert=True),
}

solids = {}
parts = []
for i, (label, kwargs) in enumerate(variants.items()):
    frame = Frame(((SAMPLE + GAP) * i, 0, 0), (1, 0, 0), (0, 1, 0))
    solid = TPMSSolid(TPMSTYPE, cell_size=CELL_SIZE, frame=frame, **kwargs)
    solids[label] = solid
    parts.append(Intersection(solid, VolBox(Box(SAMPLE, SAMPLE, SAMPLE, frame=frame), 0.0)))

shape = Union(parts)

half = SAMPLE / 2 + 1
BOUNDS = (-half, -half, -half, (SAMPLE + GAP) * (len(variants) - 1) + half, half, half)
RESOLUTION = (360, 100, 100)


def volume_fractions(resolution=96):
    """Solid volume fraction of each variant over exactly one unit cell."""
    fractions = {}
    for label, solid in solids.items():
        o = solid.frame.point
        cell = (o.x, o.y, o.z, o.x + CELL_SIZE, o.y + CELL_SIZE, o.z + CELL_SIZE)
        field, _, _ = sample(solid, cell, resolution)
        fractions[label] = float((field < 0).mean())
    return fractions


if __name__ == "__main__":
    for label, fraction in volume_fractions().items():
        print("{:>18}: {:5.1%} solid".format(label, fraction))
    demo(shape, "sheet_vs_network", bounds=BOUNDS, resolution=RESOLUTION)
