"""Domain warping: a lattice twisted into a helix.

``Twist`` rotates each query point about an axis in proportion to its height,
so straight struts become helical. Twist first, then trim, or the trimming
cylinder bends too. The warped field is no longer metric away from the
surface, but the surface itself is exact.
"""

from compas.geometry import Cylinder
from compas.geometry import Frame

from compas_vol.combinations import Intersection
from compas_vol.microstructures import Lattice
from compas_vol.modifications import Twist
from compas_vol.primitives import VolCylinder

from _common import demo

lat = Lattice(5, 9.0, 1.6)  # octet cells

# 0.05 radians per unit of height: a bit under a full turn over 40mm.
twisted = Twist(lat, Frame.worldXY(), angle=0.05)

shape = Intersection(twisted, VolCylinder(Cylinder(14, 34)))

if __name__ == "__main__":
    demo(shape, "twisted_lattice")
