"""A lattice and a TPMS wrapped around an axis.

``LatticePolar`` and ``TPMSPolar`` repeat around a circle and along its axis,
so their cells follow a tube.
"""

from compas.geometry import Cylinder
from compas.geometry import Frame

from compas_vol.combinations import Intersection
from compas_vol.combinations import Subtraction
from compas_vol.combinations import Union
from compas_vol.microstructures import LatticePolar
from compas_vol.microstructures import TPMSPolar
from compas_vol.modifications import VolTransformation
from compas_vol.primitives import VolCylinder

from _common import demo

tube = Subtraction(VolCylinder(Cylinder(12, 16)), VolCylinder(Cylinder(4, 20)))

lattice = Intersection(LatticePolar(5, 4.0, 0.6, polarnumber=12), tube)
tpms = Intersection(TPMSPolar(tpmstype="Gyroid", wavelength=4.0, thickness=0.6, polar=8), tube)

shape = Union(
    VolTransformation(lattice, Frame((-14, 0, 0), (1, 0, 0), (0, 1, 0))),
    VolTransformation(tpms, Frame((14, 0, 0), (1, 0, 0), (0, 1, 0))),
)

if __name__ == "__main__":
    demo(shape, "polar", bounds=(-28, -14, -10, 28, 14, 10), resolution=(224, 112, 80))
