"""A rock weathered by four processes, in the order a rock meets them.

    strata    hard and soft beds               -> ledges, overhangs
    jointing  a Voronoi joint set              -> blocks, open seams
    pitting   weak spots that deepen           -> honeycombing
    abrasion  convex parts wear first          -> softened edges

About a minute at RESOLUTION 160; use 96 while tuning.

    uv run --extra all python examples/20_weathered_rock.py
"""

import math

from compas.geometry import Frame

from compas_vol.combinations import SmoothUnion
from compas_vol.primitives import VolEllipsoid
from compas_vol.processes import Field
from compas_vol.processes import abrasion
from compas_vol.processes import hardness
from compas_vol.processes import jointing
from compas_vol.processes import pitting
from compas_vol.processes import strata

from _common import demo

# ==============================================================================
# Parameters
# ==============================================================================

RESOLUTION = 160  # samples per axis: the finest feature any process can make
BOUNDS = 58.0  # half-size of the sampled domain, mm

BED_THICKNESS = 15.0  # mm between bedding planes
BED_DIP = (0.22, 0.08)  # how the beds tilt, along X and Y
BED_DEPTH = 3.0  # mm the softest beds lose. Much past a fifth of the bed
#                  thickness, and the rock reads as a stack of discs.

JOINT_BLOCKS = 10  # how many blocks the mass breaks into
JOINT_OPENING = 1.6  # mm of open seam at the surface
JOINT_REACH = 10.0  # mm the seams stay open before closing. Carried all the
#                     way through, they would cut the rock into loose blocks;
#                     the report below says whether that has happened.

PIT_DEPTH = 6.0  # mm at the weakest, deepest hollow
PIT_LENGTH = 6.0  # mm: roughly how wide the pits get
PIT_THRESHOLD = 0.25  # how much of the rock is weak enough to pit at all

WEAR_DEPTH = 2.0  # mm off a flat face at the end

GRAIN = 26.0  # mm: the scale of the rock's hard and soft patches
SEED = 3

# ==============================================================================
# Model
# ==============================================================================


def massing():
    """Three tilted ellipsoids blended into one boulder."""

    def lump(rx, ry, rz, centre, degrees):
        angle = math.radians(degrees)
        frame = Frame(centre, (math.cos(angle), math.sin(angle), 0), (-math.sin(angle), math.cos(angle), 0))
        return VolEllipsoid(rx, ry, rz, frame=frame)

    mass = lump(46, 34, 30, (-4, 0, -12), 12)
    mass = SmoothUnion(mass, lump(34, 30, 28, (10, 6, 12), -50), 12.0)
    return SmoothUnion(mass, lump(26, 24, 26, (-14, -10, 22), 30), 10.0)


def weather():
    """Sample the massing, then run the four processes over it."""
    field = Field.from_object(massing(), bounds=BOUNDS, resolution=RESOLUTION)
    # One hardness field, shared: the same rock is soft in the same places
    # whichever process is asking.
    rock = hardness(field, cell_size=GRAIN, seed=SEED)

    field = strata(field, thickness=BED_THICKNESS, dip=BED_DIP, depth=BED_DEPTH, seed=SEED)
    field = jointing(field, count=JOINT_BLOCKS, opening=JOINT_OPENING, reach=JOINT_REACH, seed=SEED)
    field = pitting(field, resistance=rock, depth=PIT_DEPTH, length=PIT_LENGTH, threshold=PIT_THRESHOLD)
    return abrasion(field, depth=WEAR_DEPTH, steps=8, length=8.0)


def report(field):
    """Is it still one rock?

    Weathering can quietly cut a mass into loose pieces -- wide joints and
    deep pitting between them will do it -- and a pile of rubble looks fine
    in a render right up until someone tries to build or print it.
    """
    from scipy import ndimage

    labels, count = ndimage.label(field.values < 0)
    sizes = ndimage.sum(field.values < 0, labels, range(1, count + 1))
    print("solid fraction: {:.1%} of the sampled box".format(field.solid_fraction()))
    print("pieces        : {}, the largest holding {:.1%} of the material".format(count, sizes.max() / sizes.sum()))
    if sizes.max() / sizes.sum() < 0.95:
        print("  -> it has broken up: narrow JOINT_OPENING or reduce PIT_DEPTH")


if __name__ == "__main__":
    import time

    start = time.perf_counter()
    weathered = weather()
    print("weathered in {:.0f}s".format(time.perf_counter() - start))
    report(weathered)
    print("\nhow it was made:")
    print(weathered.provenance())

    demo(weathered.to_volume(), "weathered_rock", bounds=BOUNDS, resolution=RESOLUTION, axis="y")
