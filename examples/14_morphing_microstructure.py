"""Cell type graded across a part: gyroid on one side, Schwarz P on the other.

``Blend`` interpolates two fields under a third, here a plane, so the cell type
changes continuously across the part. Drag the slice along X to watch it.
"""

from compas.geometry import Box
from compas.geometry import Plane

from compas_vol.combinations import QUADRATIC
from compas_vol.combinations import Blend
from compas_vol.combinations import Intersection
from compas_vol.microstructures import TPMS
from compas_vol.modifications import Shell
from compas_vol.primitives import VolBox
from compas_vol.primitives import VolPlane

from _common import demo

gyroid = TPMS(tpmstype="Gyroid", wavelength=11.0)
schwarz = TPMS(tpmstype="SchwarzP", wavelength=11.0)

# The control field. Its zero level set is the middle of the transition, and
# the blend radius sets how wide that transition is -- 34mm spans the block,
# so the change is gradual.
control = VolPlane(Plane((0, 0, 0), (1, 0, 0)))

# QUADRATIC eases in and out, so the two ends stay closer to pure cell types.
morphed = Blend(gyroid, schwarz, control, r=34.0, t=QUADRATIC)

shape = Intersection(Shell(morphed, 0.5), VolBox(Box(34, 30, 30), 1.0))

if __name__ == "__main__":
    demo(shape, "morphing_microstructure", axis="x")
