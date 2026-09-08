"""A Voronoi wall structure over random seed points, trimmed to a box."""

import random

from compas.geometry import Box

from compas_vol.combinations import Intersection
from compas_vol.microstructures import Voronoi
from compas_vol.primitives import VolBox

rng = random.Random(42)
seeds = [(rng.uniform(-14, 14), rng.uniform(-12, 12), rng.uniform(-10, 10)) for _ in range(30)]

vor = Voronoi(seeds, thickness=0.8)
solid = Intersection(vor, VolBox(Box(24, 20, 16), 1.0))

if __name__ == "__main__":
    from compas_viewer import Viewer

    viewer = Viewer()
    viewer.scene.add(solid, bounds=((-14, 14), (-12, 12), (-10, 10)), resolution=(112, 96, 80))
    viewer.show()
