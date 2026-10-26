"""Booleans: union, intersection and difference, hard (top) and smooth (bottom).

The slice inspector shows the crease a hard boolean leaves where two surfaces
cross; the smooth version blends across it over RADIUS.
"""

from compas.geometry import Box
from compas.geometry import Frame
from compas.geometry import Point
from compas.geometry import Sphere

from compas_vol.combinations import Intersection
from compas_vol.combinations import SmoothIntersection
from compas_vol.combinations import SmoothSubtraction
from compas_vol.combinations import SmoothUnion
from compas_vol.combinations import Subtraction
from compas_vol.combinations import Union
from compas_vol.primitives import VolBox
from compas_vol.primitives import VolSphere

from _common import demo

RADIUS = 4.0  # blend radius of the smooth row


def pair(x, y):
    """The sphere and the box, placed at (x, y)."""
    sphere = VolSphere(Sphere(9, point=Point(x + 5, y + 6, 0)))
    box = VolBox(Box(20, 15, 10, frame=Frame((x, y, 0), (1, 0, 0), (0, 1, 0))), 2.5)
    return sphere, box


operations = [
    (Union, SmoothUnion),
    (Intersection, SmoothIntersection),
    (lambda a, b: Subtraction(b, a), lambda a, b, r: SmoothSubtraction(b, a, r)),  # the box, less the sphere
]
results = []
for column, (hard, smooth) in enumerate(operations):
    x = -40 + 40 * column
    results.append(hard(*pair(x, 22)))
    results.append(smooth(*pair(x, -22), RADIUS))

shape = Union(results)

if __name__ == "__main__":
    demo(shape, "booleans", bounds=(-62, -42, -16, 62, 42, 16), resolution=(200, 136, 52))
