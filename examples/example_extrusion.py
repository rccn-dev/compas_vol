"""Extrusion of a closed polyline."""

import math

from compas_vol.primitives import VolExtrusion

# A five-pointed star.
points = []
for i in range(11):
    a = math.pi * 2 * i / 10
    r = 9.0 if i % 2 == 0 else 4.0
    points.append((r * math.cos(a), r * math.sin(a), 0))

ext = VolExtrusion(points, 8.0)

if __name__ == "__main__":
    from compas_viewer import Viewer

    viewer = Viewer()
    viewer.scene.add(ext, bounds=((-12, 12), (-12, 12), (-8, 8)), resolution=(120, 120, 80))
    viewer.show()
