"""Boolean union: a hard seam where the two fields meet.

Compare the slice inspector here with ``4_smooth_union.py``. A union takes the
minimum of the two fields, so the zero contour has a crease where they cross.
"""

from compas.geometry import Box
from compas.geometry import Point
from compas.geometry import Sphere

from compas_vol.combinations import Union
from compas_vol.primitives import VolBox
from compas_vol.primitives import VolSphere

from _common import demo

vs = VolSphere(Sphere(9, point=Point(5, 6, 0)))
vb = VolBox(Box(20, 15, 10), 2.5)

shape = Union(vs, vb)

if __name__ == "__main__":
    demo(shape, "union")
