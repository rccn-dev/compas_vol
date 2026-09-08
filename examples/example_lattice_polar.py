"""A strut lattice tiled in cylindrical coordinates, trimmed to a tube."""

from compas.geometry import Cylinder

from compas_vol.combinations import Intersection
from compas_vol.combinations import Subtraction
from compas_vol.microstructures import LatticePolar
from compas_vol.primitives import VolCylinder

lat = LatticePolar(5, 4.0, 0.6, polarnumber=12)

outer = VolCylinder(Cylinder(12, 16))
inner = VolCylinder(Cylinder(5, 20))
tube = Subtraction(outer, inner)

shape = Intersection(lat, tube)

if __name__ == "__main__":
    from compas_viewer import Viewer

    viewer = Viewer()
    viewer.scene.add(shape, bounds=((-14, 14), (-14, 14), (-9, 9)), resolution=(112, 112, 72))
    viewer.show()
