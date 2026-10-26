"""A porous solid grown by phase separation.

Both phases stay connected, with no unit cell and no preferred direction: an
aperiodic alternative to a TPMS. Two parameters: the volume fraction, and how
long to let it coarsen.

    uv run --extra all python examples/21_spinodal_foam.py
"""

from compas.geometry import Box

from compas_vol.combinations import Intersection
from compas_vol.primitives import VolBox
from compas_vol.processes import spinodal

from _common import demo

# ==============================================================================
# Parameters
# ==============================================================================

SIZE = 100.0  # mm cube
RESOLUTION = 160
FEATURE = 9.0  # mm: wall thickness and pore size
FRACTION = 0.42  # solid share. Below ~0.3 the solid stops percolating.
STEPS = 500  # separation is quick, coarsening is slow
SEED = 1

# ==============================================================================
# Model
# ==============================================================================

foam = spinodal(bounds=SIZE / 2 + 4, resolution=RESOLUTION, feature=FEATURE, fraction=FRACTION, steps=STEPS, seed=SEED)
shape = Intersection(foam.to_volume(), VolBox(Box(SIZE, SIZE, SIZE), 12.0))


def report():
    from scipy import ndimage

    print("solid fraction: {:.1%} (asked for {:.0%})".format(foam.solid_fraction(), FRACTION))
    for name, phase in (("solid", foam.values < 0), ("void", foam.values > 0)):
        labels, count = ndimage.label(phase)
        sizes = ndimage.sum(phase, labels, range(1, count + 1))
        # Bicontinuous means one piece holds essentially all of each phase.
        print("  {:>5}: {} piece(s), the largest holds {:.1%} of it".format(name, count, sizes.max() / sizes.sum()))


if __name__ == "__main__":
    report()
    demo(shape, "spinodal_foam", bounds=SIZE / 2 + 4, resolution=RESOLUTION)
