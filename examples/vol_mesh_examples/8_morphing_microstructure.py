"""Variable cell *type*: a gyroid on one side, a Schwartz-P on the other.

Grading cell size is common; grading the topology itself is less so. ``Blend``
interpolates between two fields under the control of a third, so feeding it a
plane makes the unit cell change type across the part, with a continuous
transition rather than a butt joint between two lattices.

Watch the slice inspector while dragging along X: the contour shape shifts
from the gyroid's interlocking curves to the Schwartz-P's tubes.
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
schwartz = TPMS(tpmstype="SchwartzP", wavelength=11.0)

# The control field. Its zero level set is the middle of the transition, and
# the blend radius sets how wide that transition is -- 34mm spans the block,
# so the change is gradual rather than an abrupt seam.
control = VolPlane(Plane((0, 0, 0), (1, 0, 0)))

# QUADRATIC eases in and out, so the two ends stay closer to pure cell types.
morphed = Blend(gyroid, schwartz, control, r=34.0, t=QUADRATIC)

shape = Intersection(Shell(morphed, 0.5), VolBox(Box(34, 30, 30), 1.0))

if __name__ == "__main__":
    demo(shape, "morphing_microstructure", axis="x")
