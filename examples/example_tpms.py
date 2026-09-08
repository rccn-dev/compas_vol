"""A triply periodic minimal surface, thickened and trimmed to a box."""

from compas.geometry import Box

from compas_vol.combinations import Intersection
from compas_vol.microstructures import TPMS
from compas_vol.modifications import Shell
from compas_vol.primitives import VolBox

tpms = TPMS(tpmstype="SchwartzP", wavelength=5.0)
print(tpms.typename)

# The raw TPMS field is a surface; give it a thickness and trim it.
solid = Intersection(Shell(tpms, 0.4, 0.5), VolBox(Box(24, 20, 16), 1.0))

if __name__ == "__main__":
    from compas_viewer import Viewer

    viewer = Viewer()
    viewer.scene.add(solid, bounds=((-14, 14), (-12, 12), (-10, 10)), resolution=(112, 96, 80))
    viewer.show()
