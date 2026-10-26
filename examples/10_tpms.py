"""A TPMS shell, graded across the part with the low-level classes.

``Shell`` thickens the surface; ``Overlay`` with a sloped plane makes it thin at
one corner and thick at the other. ``11_tpms_catalogue.py`` does the same in
millimetres. Types are in ``compas_vol.microstructures.TPMSTYPES``.
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
