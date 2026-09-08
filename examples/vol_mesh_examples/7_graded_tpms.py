"""Variable TPMS: cell size graded by distance to an attractor.

A plain TPMS has one wavelength everywhere. ``TPMSAttractor`` drives the
wavelength from another object's distance field instead, so the cells are fine
near the attractor and open up as they move away. This is the usual way to put
material where a part needs stiffness and leave it out where it does not.

The attractor is any volumetric object, so a point, a curve-like capsule or a
whole imported solid all work the same way.
"""

from compas.geometry import Box
from compas.geometry import Point
from compas.geometry import Sphere

from compas_vol.combinations import Intersection
from compas_vol.microstructures import TPMSAttractor
from compas_vol.modifications import Shell
from compas_vol.primitives import VolBox
from compas_vol.primitives import VolSphere

from _common import demo

# The attractor: a small sphere at one corner of the block.
attractor = VolSphere(Sphere(1.0, point=Point(-12, -12, 0)))

# Fine 6mm cells at the attractor, opening to 22mm at 40mm away.
graded = TPMSAttractor(
    attractor,
    tpmstype="Gyroid",
    wavelength_range=(6.0, 22.0),
    distance_range=(0.0, 40.0),
)

shape = Intersection(Shell(graded, 0.45), VolBox(Box(32, 32, 24), 1.0))

if __name__ == "__main__":
    demo(shape, "graded_tpms")
