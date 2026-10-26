"""Three ways to make one field from others: Morph, Blend and Offset.

Morph interpolates two fields. Blend switches between them across a third
field's surface. Offset grows a shape by a distance that can itself be a field:
here a box that swells towards the top.
"""

from compas.geometry import Box
from compas.geometry import Frame
from compas.geometry import Plane
from compas.geometry import Point
from compas.geometry import Sphere

from compas_vol.combinations import Blend
from compas_vol.combinations import Morph
from compas_vol.combinations import Union
from compas_vol.modifications import Offset
from compas_vol.modifications import Remap
from compas_vol.primitives import VolBox
from compas_vol.primitives import VolPlane
from compas_vol.primitives import VolSphere

from _common import demo


def at(x):
    """A sphere and a box at x."""
    return (VolSphere(Sphere(10, point=Point(x, 0, 0))),
            VolBox(Box(18, 18, 18, frame=Frame((x, 0, 0), (1, 0, 0), (0, 1, 0))), 1.0))


sphere, box = at(-30)
morphed = Morph(sphere, box, 0.5)

sphere, box = at(0)
split = VolPlane(Plane((0, 0, 0), (1, 0, 1)))         # sphere on one side of a tilted plane, box on the other
blended = Blend(sphere, box, split, 8.0)

_, box = at(30)
swell = Remap(VolPlane(Plane((0, 0, 0), (0, 0, 1))), (-9.0, 9.0), (-2.0, 4.0))   # -2 mm at the bottom, +4 at the top
offset = Offset(box, swell)

shape = Union([morphed, blended, offset])

if __name__ == "__main__":
    demo(shape, "blending", bounds=(-46, -16, -16, 46, 16, 16), resolution=(180, 64, 64), axis="y")
