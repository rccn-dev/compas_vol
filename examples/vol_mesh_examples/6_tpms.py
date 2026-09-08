"""A TPMS shell with wall thickness graded across the part.

A TPMS is a surface, so ``Shell`` gives it thickness. Adding a sloped plane
field on top shifts that thickness through the block: thin at one corner,
thick at the opposite one. Types are in
``compas_vol.microstructures.TPMSTYPES``.
"""

from compas.geometry import Box
from compas.geometry import Plane

from compas_vol.combinations import Intersection
from compas_vol.microstructures import TPMSTYPES
from compas_vol.microstructures import TPMS
from compas_vol.modifications import Overlay
from compas_vol.modifications import Shell
from compas_vol.primitives import VolBox
from compas_vol.primitives import VolPlane

from _common import demo

print("TPMS types:", TPMSTYPES)

vb = VolBox(Box(30, 30, 30), 0)
shell = Shell(TPMS(tpmstype="FischerKoch", wavelength=18), 0.33)
graded = Overlay(shell, VolPlane(Plane((-15, -15, -15), (-1, -1, -1))), 0.005)

shape = Intersection(vb, graded)

if __name__ == "__main__":
    demo(shape, "tpms")
