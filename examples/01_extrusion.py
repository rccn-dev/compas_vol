"""A star polygon extruded along a tilted frame."""

import numpy as np
from compas.geometry import Frame

from compas_vol.primitives import VolExtrusion

from _common import demo

# A ten-point star, alternating between two radii.
polyline = []
step = np.pi * 2 / 10
for i in range(10):
    r = 10 if i % 2 == 0 else 5
    polyline.append((r * np.cos(i * step), r * np.sin(i * step), 0))
polyline.append(polyline[0])

shape = VolExtrusion(
    polyline,
    height=5,
    frame=Frame((0, 0, 0), (1, 0.3, 0.1), (-0.4, 1, 0.3)),
)

if __name__ == "__main__":
    demo(shape, "extrusion")
