"""Smooth union: the same two shapes as ``3_union.py``, blended.

The radius controls how far from the seam the blend reaches. Raise it and the
fillet grows; at zero it degenerates back to a plain union.
"""

from compas.geometry import Box
from compas.geometry import Point
from compas.geometry import Sphere

from compas_vol.combinations import SmoothUnion
from compas_vol.primitives import VolBox
from compas_vol.primitives import VolSphere

from _common import demo

vs = VolSphere(Sphere(9, point=Point(5, 6, 0)))
vb = VolBox(Box(20, 15, 10), 0)

shape = SmoothUnion(vs, vb, 4.0)

if __name__ == "__main__":
    demo(shape, "smooth_union")
