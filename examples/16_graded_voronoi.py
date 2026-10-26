"""An aperiodic Voronoi foam, its cells graded by seed density.

Seeds packed towards the centre give small cells at the core and large ones at
the surface. No two cells are alike, which avoids the resonance of a repeating
structure. Runs at a reduced resolution: Voronoi is the most expensive field.
"""

import math
import random

from compas.geometry import Point
from compas.geometry import Sphere

from compas_vol.combinations import Intersection
from compas_vol.microstructures import Voronoi
from compas_vol.primitives import VolSphere

from _common import demo

SEEDS = 110
RADIUS = 19.0

rng = random.Random(7)
points = []
for _ in range(SEEDS):
    # Uniform direction on the sphere.
    theta = rng.uniform(0, 2 * math.pi)
    cos_phi = rng.uniform(-1, 1)
    sin_phi = math.sqrt(1 - cos_phi**2)
    # Exponent 1/3 would be volumetrically uniform; 0.85 biases inwards.
    r = RADIUS * rng.random() ** 0.85
    points.append(
        (r * sin_phi * math.cos(theta), r * sin_phi * math.sin(theta), r * cos_phi)
    )

walls = Voronoi(points, thickness=0.9)

shape = Intersection(walls, VolSphere(Sphere(16, point=Point(0, 0, 0))))

if __name__ == "__main__":
    # Voronoi is the most expensive object here: it walks the seed list twice
    # per sample. 120 is plenty to see the gradient.
    demo(shape, "graded_voronoi", resolution=120)
