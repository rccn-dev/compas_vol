"""A porous rock in one field: massing, skin, graded interior, niches.

Smooth-unioned massing; a closed skin; a gyroid whose walls thicken towards the
skin; pockets cut through the skin for planting or drainage. Every parameter
is a number at the top of the file, in millimetres.
"""

import math

from compas.geometry import Frame
from compas.geometry import Plane
from compas.geometry import Point
from compas.geometry import Sphere

from compas_vol.combinations import Intersection
from compas_vol.combinations import SmoothUnion
from compas_vol.combinations import Subtraction
from compas_vol.combinations import Union
from compas_vol.microstructures import TPMSSolid
from compas_vol.modifications import Remap
from compas_vol.modifications import Shell
from compas_vol.primitives import VolEllipsoid
from compas_vol.primitives import VolPlane
from compas_vol.primitives import VolSphere

from _common import demo

# ==============================================================================
# Parameters
# ==============================================================================

# Massing: (radii, centre, rotation about Z in degrees) for each rock.
ROCKS = [
    ((17.0, 12.0, 10.0), (-5, 0, -8), 10),
    ((13.0, 10.0, 9.0), (6, 3, 7), -60),
    ((9.0, 8.0, 7.0), (-7, -4, 13), 45),
]
BLEND = 5.0  # how softly the rocks merge, mm

SKIN = 1.2  # skin thickness, mm

CELL_SIZE = 7.0  # interior gyroid, mm
WALL_AT_SKIN = 1.4  # interior wall thickness just inside the skin, mm
WALL_AT_CORE = 0.5  # ... and deep inside, mm
DEPTH = 8.0  # depth over which the walls thin, mm
# Tilt the lattice so its channels do not all line up with the print axis.
LATTICE_FRAME = Frame((0, 0, 0), (1, 0.25, 0.1), (-0.2, 1, 0.3))

# Cut away everything in front of this plane, so the interior is visible.
# Set to None for the closed rock.
SECTION = ((0, 2, 0), (0, -1, 0))

# Niches: (centre, radius).
NICHES = [
    ((-19, -6, -6), 5.0),
    ((10, -8, 10), 4.0),
    ((2, 12, -4), 4.5),
    ((-4, -2, 20), 3.5),
]

# ==============================================================================
# Model
# ==============================================================================



def rotated_frame(centre, degrees):
    a = math.radians(degrees)
    return Frame(centre, (math.cos(a), math.sin(a), 0), (-math.sin(a), math.cos(a), 0))


rocks = [VolEllipsoid(*radii, frame=rotated_frame(centre, degrees)) for radii, centre, degrees in ROCKS]

mass = rocks[0]
for rock in rocks[1:]:
    mass = SmoothUnion(mass, rock, BLEND)

# Inside the mass the distance is negative: 0 at the skin, -DEPTH deep inside.
wall = Remap(mass, source=(-DEPTH, 0.0), target=(WALL_AT_CORE, WALL_AT_SKIN), ease="smooth")
interior = Intersection(TPMSSolid("Gyroid", CELL_SIZE, wall, frame=LATTICE_FRAME), mass)

skin = Shell(mass, SKIN, side=1.0)  # side=1: offset inwards, outer surface unchanged

niches = Union([VolSphere(Sphere(r, point=Point(*c))) for c, r in NICHES])

shape = Subtraction(Union(skin, interior), niches)

if SECTION is not None:
    shape = Intersection(shape, VolPlane(Plane(*SECTION)))

BOUNDS = (-26, -18, -22, 24, 18, 26)
RESOLUTION = (250, 180, 240)

if __name__ == "__main__":
    demo(shape, "porous_rock", bounds=BOUNDS, resolution=RESOLUTION, axis="y", export=True)
