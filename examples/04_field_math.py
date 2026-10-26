"""Arithmetic on fields: surfaces that were in neither input.

``Sine`` turns a sphere's field into concentric shells; ``Overlay`` adds some of
that back, so the sphere ripples. Past an AMPLITUDE of about 1.5 the ripples
pinch off into rings. The result is no longer a distance field, so offsets and
shells downstream are not in millimetres.
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

# Bite one octant (+X +Y +Z) out, to show the corrugations in section.
cutter = VolBox(Box(20, 20, 20, frame=Frame((10, 10, 10), (1, 0, 0), (0, 1, 0))), 0)

shape = Subtraction(corrugated, cutter)

if __name__ == "__main__":
    demo(shape, "field_math")
