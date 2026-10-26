"""Differential growth: a surface that folds as it grows.

Speed rises with curvature, so bulges outgrow the surface beside them and
become lobes. Two lengths control it: ``length``, what curvature is measured
against (against the voxel size, the seed just inflates into a ball), and
``wavelength``, the smoothing that sets the fold width. Start from a small
seed. The script grows the seed twice, folding and uniform, and prints each
shape index (4.84 for a sphere).

    uv run --extra all python examples/22_coral_growth.py
"""

from compas.geometry import Point
from compas.geometry import Sphere

from compas_vol.primitives import VolSphere
from compas_vol.processes import Field
from compas_vol.processes import fingering

from _common import demo

# ==============================================================================
# Parameters
# ==============================================================================

BOUNDS = 55.0  # mm: leave room, the surface grows outward
RESOLUTION = 150
SEED_RADIUS_MM = 8.0
HEIGHT = 30.0  # mm the fastest part of the surface advances
LENGTH = 9.0  # mm, what curvature is measured against
GAIN = 1.4  # strength of the instability; past ~1.5 lobes pinch off
WAVELENGTH = 4.0  # mm, the width of a fold

# ==============================================================================
# Model
# ==============================================================================

seed = Field.from_object(
    VolSphere(Sphere(SEED_RADIUS_MM, point=Point(0, 0, 0))), bounds=BOUNDS, resolution=RESOLUTION
)
coral = fingering(seed, height=HEIGHT, length=LENGTH, gain=GAIN, wavelength=WAVELENGTH)


def compare():
    """Folded growth against the same loop with the instability switched off."""
    import numpy as np
    from skimage.measure import marching_cubes

    def shape_index(field):
        """Area over volume^(2/3): 4.84 for a sphere of any size, more if folded."""
        vertices, triangles, _, _ = marching_cubes(field.values, 0.0, spacing=field.spacing)
        a, b, c = vertices[triangles[:, 0]], vertices[triangles[:, 1]], vertices[triangles[:, 2]]
        area = float(np.linalg.norm(np.cross(b - a, c - a), axis=1).sum() / 2)
        volume = float((field.values < 0).sum()) * np.prod(field.spacing)
        return area / volume ** (2 / 3)

    plain = fingering(seed, height=HEIGHT, length=LENGTH, gain=0.0)   # same advance, no instability

    print("shape index (4.84 is a sphere, whatever its size):")
    print("  seed          {:6.2f}".format(shape_index(seed)))
    print("  uniform       {:6.2f}   <- the control: growth without the instability".format(shape_index(plain)))
    print("  folded        {:6.2f}   <- if this is not well above 4.84, check `length`".format(shape_index(coral)))
    print("solid fraction: {:.1%} of the sampled box".format(coral.solid_fraction()))


if __name__ == "__main__":
    compare()
    demo(coral.to_volume(), "coral_growth", bounds=BOUNDS, resolution=RESOLUTION)
