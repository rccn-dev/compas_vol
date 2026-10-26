"""Grading cell size two ways, with the cost of each measured.

* **Warping** (``TPMSAttractor``) keeps one continuous sheet but distorts cells:
  up to ~50% stretch near the attractor here, and worse far from the origin.
* **Blending** two uniform ``TPMSSolid`` keeps cells undistorted but leaves
  defects in the transition band: loose crumbs a cleanup pass removes.

The script reports local cell size, body count and crumbs for both.
"""

from math import pi

import numpy as np
from compas.geometry import Box
from compas.geometry import Frame
from compas.geometry import Point
from compas.geometry import Sphere

from compas_vol.combinations import Blend
from compas_vol.combinations import Intersection
from compas_vol.combinations import Union
from compas_vol.meshing import sample
from compas_vol.microstructures import TPMSAttractor
from compas_vol.microstructures import TPMSSolid
from compas_vol.modifications import Shell
from compas_vol.modifications import VolTransformation
from compas_vol.primitives import VolBox
from compas_vol.primitives import VolSphere

from _common import demo

# ==============================================================================
# Parameters
# ==============================================================================

FINE = 6.0  # cell size at the attractor, mm
COARSE = 12.0  # cell size far away, mm
BLOCK = (48.0, 24.0, 24.0)  # each test block, mm
ATTRACTOR = Point(-20, 0, 0)  # at the left end of each block
REACH = 36.0  # distance over which the warp goes from FINE to COARSE
BAND = 3.0  # transition band of the blend, mm
THICKNESS = 0.8
SPACING = 34.0  # distance between the two blocks, along Y

# ==============================================================================
# Model -- both variants built around the local origin, then moved apart
# ==============================================================================

attractor = VolSphere(Sphere(0.5, point=ATTRACTOR))
block = VolBox(Box(*BLOCK), 0.0)

# Warp. TPMSAttractor's wavelength is half a cell, so halve the cell sizes.
# Its raw field is not metric; the gyroid's gradient is ~pi / wavelength, so
# scaling the shell by that keeps the wall roughly THICKNESS thick.
warped_field = TPMSAttractor(attractor, "Gyroid", (FINE / 2, COARSE / 2), (0.0, REACH))
warped = Intersection(Shell(warped_field, THICKNESS * pi / (FINE / 2)), block)

# Blend. Inside a sphere around the attractor use the fine lattice, outside
# the coarse one, with a band of width BAND between.
fine = TPMSSolid("Gyroid", FINE, THICKNESS)
coarse = TPMSSolid("Gyroid", COARSE, THICKNESS)
region = VolSphere(Sphere(REACH / 2, point=ATTRACTOR))
blended = Intersection(Blend(fine, coarse, region, r=BAND), block)

frame_warp = Frame((0, -SPACING / 2, 0), (1, 0, 0), (0, 1, 0))
frame_blend = Frame((0, SPACING / 2, 0), (1, 0, 0), (0, 1, 0))
shape = Union(VolTransformation(warped, frame_warp), VolTransformation(blended, frame_blend))

bx, by, bz = (v / 2 + 1 for v in BLOCK)
BOUNDS = (-bx, -SPACING / 2 - by, -bz, bx, SPACING / 2 + by, bz)
RESOLUTION = (200, 240, 100)

# ==============================================================================
# Measurements
# ==============================================================================


def warp_cell_sizes(point, attractor_point=ATTRACTOR, h=1e-4):
    """Intended and actual local cell sizes of the warp at a point.

    The warp maps a point p to the phase ``pi * p / w(p)``. The lattice
    repeats every 2 pi of phase, so the local cell size along each principal
    direction is ``2 pi / sigma`` for each singular value of the Jacobian.
    """
    p = np.asarray(point, dtype=float)
    a = np.asarray(attractor_point, dtype=float)

    def phase(q):
        d = np.linalg.norm(q - a) - 0.5
        t = min(max(d / REACH, 0.0), 1.0)
        w = FINE / 2 + t * (COARSE / 2 - FINE / 2)
        return pi * q / w, 2 * w

    _, intended = phase(p)
    jacobian = np.column_stack([(phase(p + h * e)[0] - phase(p - h * e)[0]) / (2 * h) for e in np.eye(3)])
    sigma = np.linalg.svd(jacobian, compute_uv=False)
    actual = 2 * pi / sigma
    return intended, actual.min(), actual.max()


def bodies_and_crumbs(obj, resolution=120, crumb=50):
    """Count solid bodies, and crumbs smaller than ``crumb`` voxels."""
    from scipy.ndimage import label

    hx, hy, hz = (v / 2 for v in BLOCK)
    field, _, _ = sample(obj, (-hx, -hy, -hz, hx, hy, hz), resolution)
    labels, count = label(field < 0)
    sizes = np.bincount(labels.ravel())[1:]
    return int((sizes >= crumb).sum()), int((sizes < crumb).sum())


if __name__ == "__main__":
    print("warp: intended vs actual local cell size (min..max over directions)")
    for x in (-20, -10, 0, 10, 20):
        intended, lo, hi = warp_cell_sizes((x, 8.0, 8.0))
        print("  x = {:>4}: intended {:5.1f} mm, actual {:5.1f} .. {:5.1f} mm".format(x, intended, lo, hi))
    print("the same set-up moved 400 mm along X, away from the world origin:")
    shifted = (ATTRACTOR.x + 400.0, ATTRACTOR.y, ATTRACTOR.z)
    for x in (-10, 10):
        intended, lo, hi = warp_cell_sizes((x + 400.0, 8.0, 8.0), shifted)
        print("  x = {:>4}: intended {:5.1f} mm, actual {:5.1f} .. {:5.1f} mm".format(x + 400, intended, lo, hi))
    print("solid bodies and loose crumbs:")
    print("  warp : {} body, {} crumbs".format(*bodies_and_crumbs(warped)))
    print("  blend: {} body, {} crumbs".format(*bodies_and_crumbs(blended)))
    demo(shape, "cell_size_grading", bounds=BOUNDS, resolution=RESOLUTION)
