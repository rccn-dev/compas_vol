"""A strut lattice trimmed to a cube.

``Lattice`` is infinite, so it is intersected with a solid to make a part.
Types are in ``compas_vol.microstructures.LATTICE_TYPENAMES``.
"""

from compas.geometry import Box
from compas.geometry import Frame

from compas_vol.combinations import Intersection
from compas_vol.microstructures import LATTICE_TYPENAMES
from compas_vol.microstructures import Lattice
from compas_vol.primitives import VolBox

from _common import demo

print("lattice types:", LATTICE_TYPENAMES)

vb = VolBox(Box(30, 30, 30), 0)
lat = Lattice(10, 15.0, 3, frame=Frame((1, 0, 0), (1, 0.2, 0.1), (-0.3, 1, 0.2)))
print("using:", lat.lattice_type)

shape = Intersection(vb, lat)

if __name__ == "__main__":
    demo(shape, "lattice")
