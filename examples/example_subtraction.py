"""Boolean subtraction of a sphere from a filleted box."""

from compas.geometry import Box
from compas.geometry import Point
from compas.geometry import Sphere

from compas_vol.combinations import Subtraction
from compas_vol.primitives import VolBox
from compas_vol.primitives import VolSphere

vs = VolSphere(Sphere(9, point=Point(5, 6, 0)))
vb = VolBox(Box(20, 15, 10), 2.5)
s = Subtraction(vb, vs)

if __name__ == "__main__":
    from compas_viewer import Viewer

    viewer = Viewer()
    viewer.scene.add(s, bounds=20.0, resolution=100)
    viewer.show()
