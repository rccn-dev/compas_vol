"""Wall thickness in millimetres, driven by an attractor.

Any graded parameter takes two steps: a driver (a field whose distance means
something, here a capsule standing in for a load path) and ``Remap`` into the
parameter's range. Walls are 1.8 mm along the path and 0.6 mm 18 mm away. Keep
the thickest wall under a third of the cell size, or the channels close.
"""

from compas.geometry import Cylinder
from compas.geometry import Frame

from compas_vol.combinations import Intersection
from compas_vol.meshing import sample
from compas_vol.microstructures import TPMSSolid
from compas_vol.modifications import Remap
from compas_vol.primitives import VolCapsule
from compas_vol.primitives import VolCylinder

from _common import demo

# ==============================================================================
# Parameters
# ==============================================================================

CELL_SIZE = 10.0
THICK = 1.8  # wall thickness on the load path, mm
THIN = 0.6  # wall thickness far from it, mm
FALLOFF = 18.0  # distance over which the wall thins, mm
LOAD_PATH = ((-14, -6, -19), (14, 6, 19))

# ==============================================================================
# Model
# ==============================================================================

load_path = VolCapsule(LOAD_PATH, 0.5)

# "smooth" eases in and out of both ends, so there is no visible kink where
# the thickness reaches its minimum.
thickness = Remap(load_path, source=(0.0, FALLOFF), target=(THICK, THIN), ease="smooth")

lattice = TPMSSolid("Gyroid", cell_size=CELL_SIZE, thickness=thickness)

# A column, 40 mm tall, standing on the world XY plane's origin.
column = VolCylinder(Cylinder(16.0, 40.0, frame=Frame.worldXY()))

shape = Intersection(lattice, column)


def local_density(center, radius=4.0, resolution=48):
    """Solid fraction inside a small cube around ``center``."""
    x, y, z = center
    box = (x - radius, y - radius, z - radius, x + radius, y + radius, z + radius)
    field, _, _ = sample(lattice, box, resolution)
    return float((field < 0).mean())


if __name__ == "__main__":
    print("solid fraction on the load path : {:.1%}".format(local_density((0, 0, 0))))
    print("solid fraction away from it     : {:.1%}".format(local_density((-12, 12, 10))))
    demo(shape, "attractor_graded_wall", True)
