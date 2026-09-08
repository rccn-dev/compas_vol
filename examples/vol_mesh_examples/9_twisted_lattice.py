"""Domain warping: a lattice sheared into a helix.

Everything so far combined fields. ``Twist`` instead deforms the *space* the
field is evaluated in, rotating each query point about an axis by an amount
proportional to its height. Straight struts become helical without any change
to the lattice itself.

Note the order: the lattice is twisted and *then* trimmed. Twisting the
already-trimmed solid would bend the cylinder too.

One caveat worth seeing in the slice inspector: a warped field is no longer a
true distance field. Space is stretched by the twist, so the values away from
the surface are compressed on the outside of the helix. The zero level set --
the surface itself -- is still exactly right, which is what gets meshed.
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
