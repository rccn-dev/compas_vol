"""Variable wall thickness, graded radially.

``Shell`` gives a constant thickness. To vary it, add a second field on top:
``Overlay`` computes ``a + f * b``, and since the shell field is
``abs(d) - t/2``, adding anything to it moves where the surface falls and so
changes the wall thickness locally.

Here the added field is a cylinder's, which grows with distance from the Z
axis, giving dense material at the core thinning towards the rim -- closer to
how a bone is built than a uniform lattice. Measured by solid volume fraction
the structure runs about 25% at the core and 12% at the rim.

Two things to watch if you retune this. The factor is easy to overdo: much
past 0.03 and the walls stop closing near the rim, leaving a hollow shell
rather than a graded one. And the gyroid's field is not metric -- its gradient
is roughly ``pi / wavelength`` rather than 1 -- so ``t`` is not a thickness in
millimetres, which is why volume fraction is the honest thing to quote.
"""

from compas.geometry import Cylinder

from compas_vol.combinations import Intersection
from compas_vol.microstructures import TPMS
from compas_vol.modifications import Overlay
from compas_vol.modifications import Shell
from compas_vol.primitives import VolCylinder

from _common import demo

tpms = TPMS(tpmstype="Gyroid", wavelength=9.0)

# A degenerate cylinder used purely as a radial ramp: its field is
# (distance from the Z axis) - 1, so it rises steadily outwards.
radial = VolCylinder(Cylinder(1.0, 200.0))

# Positive factor => the field rises outwards => walls thin with radius.
graded = Overlay(Shell(tpms, 0.9), radial, 0.02)

shape = Intersection(graded, VolCylinder(Cylinder(16, 30)))

if __name__ == "__main__":
    demo(shape, "graded_shell")
