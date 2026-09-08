"""A triply periodic minimal surface evaluated in cylindrical coordinates."""

from compas.geometry import Cylinder

from compas_vol.combinations import Intersection
from compas_vol.combinations import Subtraction
from compas_vol.microstructures import TPMSPolar
from compas_vol.primitives import VolCylinder

tpms = TPMSPolar(tpmstype="Gyroid", wavelength=4.0, thickness=0.6, polar=8)

outer = VolCylinder(Cylinder(12, 16))
inner = VolCylinder(Cylinder(4, 20))
tube = Subtraction(outer, inner)

shape = Intersection(tpms, tube)

if __name__ == "__main__":
    from compas_viewer import Viewer

    viewer = Viewer()
    viewer.scene.add(shape, bounds=((-14, 14), (-14, 14), (-9, 9)), resolution=(112, 112, 72))
    viewer.show()
