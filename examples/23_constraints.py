"""Weathering a slab that must keep its rib.

The slab is weathered twice, freely and with ``Field.constrain(keep=rib)``. The
constraint holds through pitting, abrasion and opening; ``margin`` fades the
erosion out near the rib. The script prints how much of the rib each version
lost.
"""

from compas.geometry import Box
from compas.geometry import Frame

from compas_vol.combinations import Union
from compas_vol.primitives import VolBox
from compas_vol.processes import Field
from compas_vol.processes import abrasion
from compas_vol.processes import opened
from compas_vol.processes import pitting

from _common import demo

slab = VolBox(Box(80, 50, 8, frame=Frame((0, 0, 6), (1, 0, 0), (0, 1, 0))), 0.5)
rib = VolBox(Box(10, 50, 20, frame=Frame((0, 0, 0), (1, 0, 0), (0, 1, 0))), 0.5)
BOUNDS = (-44, -29, -14, 44, 29, 14)


def weather(field):
    field = pitting(field, depth=4.0, length=4.0, threshold=0.0, cell_size=12.0, seed=2)
    field = abrasion(field, depth=1.5, length=6.0)
    return opened(field, 0.8)


field = Field.from_object(Union(slab, rib), BOUNDS, resolution=(132, 87, 42))
free = weather(field)
kept = weather(field.constrain(keep=rib, margin=4.0))


def rib_lost(result):
    """How deep into the rib material is missing, in mm: the constraint's own measure."""
    probe = result.copy()
    probe.keep = kept.keep          # the rib, sampled on the same grid
    return probe.violation()["keep"]


print("rib lost, weathered freely : {:.1f} mm deep".format(rib_lost(free)))
print("rib lost, weathered kept   : {:.1f} mm deep  (under a voxel, {:.1f} mm, is the grid)".format(
    rib_lost(kept), kept.voxel))

shape = kept.to_volume()

if __name__ == "__main__":
    demo(shape, "constraints", bounds=BOUNDS, resolution=(132, 87, 42), axis="y")
