"""Arithmetic on fields, where CSG stops being the point.

Union, intersection and subtraction all pick one of their inputs at each
point, so the result is always made of surfaces that existed already. The
arithmetic combinations do not: adding, multiplying or taking the sine of a
field produces surfaces that were in neither input.

Here ``Sine`` turns a sphere's distance field into concentric shells, and
``Overlay`` adds a little of that back onto the sphere, so the surface ripples
where it used to be smooth. Turn AMPLITUDE up past about 1.5 and the ripples
pinch off into separate rings, which is a good way to see how far a scalar
field can be pushed before its zero level set stops being one solid.

These fields are no longer metric -- the value at a point is not its distance
to anything -- so offsets and shells downstream will not behave predictably.
"""

from compas.geometry import Box
from compas.geometry import Frame
from compas.geometry import Point
from compas.geometry import Sphere

from compas_vol.combinations import Subtraction
from compas_vol.modifications import Overlay
from compas_vol.modifications import Sine
from compas_vol.primitives import VolBox
from compas_vol.primitives import VolSphere

from _common import demo

AMPLITUDE = 1.5

ball = VolSphere(Sphere(14, point=Point(0, 0, 0)))

# sin() of the radial distance field: concentric shells, one per wavelength.
ripple = Sine(ball, f=1.85)

# Add a little of the ripple to the ball, so its surface corrugates.
corrugated = Overlay(ball, ripple, AMPLITUDE)

# Bite one octant out, so the corrugations are visible in section rather than
# only from outside. The cutter sits on the +X +Y +Z corner.
cutter = VolBox(Box(20, 20, 20, frame=Frame((10, 10, 10), (1, 0, 0), (0, 1, 0))), 0)

shape = Subtraction(corrugated, cutter)

if __name__ == "__main__":
    demo(shape, "field_math")
