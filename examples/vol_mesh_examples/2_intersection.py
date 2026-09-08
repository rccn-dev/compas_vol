"""Boolean intersection: the volume common to a sphere and a filleted box."""

from compas.geometry import Box
from compas.geometry import Point
from compas.geometry import Sphere

from compas_vol.combinations import Intersection
from compas_vol.primitives import VolBox
from compas_vol.primitives import VolSphere

from _common import demo

# COMPAS 2 signatures: Sphere(radius, point=...) and Box(x, y, z, frame=...).
vs = VolSphere(Sphere(9, point=Point(5, 6, 0)))
vb = VolBox(Box(20, 15, 10), 2.5)

shape = Intersection(vs, vb)

if __name__ == "__main__":
    demo(shape, "intersection")
