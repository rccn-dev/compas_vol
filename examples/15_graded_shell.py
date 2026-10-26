"""Wall thickness graded radially with ``Overlay``.

Adding a cylinder's field to a gyroid shell thickens walls at the core and
thins them at the rim: about 25% solid at the core, 12% at the rim. Past a
factor of about 0.03 the rim walls stop closing. The gyroid field is not
metric, so the thickness is not in millimetres; ``17`` does this in mm.
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
