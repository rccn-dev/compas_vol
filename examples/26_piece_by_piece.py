"""A processed model built one piece at a time.

Three pieces meet in a T, with clearance and pins on their shared faces.
``Assembly.build`` weathers each with a halo on a shared lattice, so only one
piece is in memory; ``Seams`` checks that neighbours meet.
"""

from compas.geometry import Box

from compas_vol.assembly import Pins
from compas_vol.assembly import Seams
from compas_vol.assembly import segment
from compas_vol.combinations import Intersection
from compas_vol.combinations import Union
from compas_vol.meshing import is_watertight
from compas_vol.meshing import iso_surface
from compas_vol.microstructures import TPMSSolid
from compas_vol.modifications import Shell
from compas_vol.primitives import VolBox
from compas_vol.processes import abrasion

from _common import demo

VOXEL, HALO = 1.0, 8.0
block = VolBox(Box(120.0, 60.0, 24.0), 2.0)
model = Union(Shell(block, 4.0, 1.0), Intersection(TPMSSolid("Gyroid", 20.0, 5.0), block))

cells = [
    {"bounds": (-60, -30, -12, 0, 30, 12), "name": "long"},
    {"bounds": (0, -30, -12, 60, 0, 12), "name": "front"},
    {"bounds": (0, 0, -12, 60, 30, 12), "name": "back"},
]
assembly = segment(model, (-60, -30, -12, 60, 30, 12), cells=cells, clearance=0.4,
                   joint=Pins(diameter=3.0, depth=3.0, fit=0.15, spacing=8.0, margin=0.5, limit=3))


def weather(field):
    return abrasion(field, depth=0.8, steps=6, length=4.0)


cost = assembly.cost(voxel=VOXEL, halo=HALO)
print("{} pieces; largest {:,} samples, the whole block {:,}".format(len(assembly), cost["per_piece"],
                                                                     cost["whole_model"]))
seams, finished = Seams(assembly, VOXEL), []
for piece, field, _ in assembly.build(weather, VOXEL, HALO, seams=seams):
    vertices, faces = iso_surface(field.values, field.origin, field.spacing)
    print("{:<6} {:>2} pin(s)/socket(s), {:>7,} triangles, watertight {}".format(
        piece.name, len(piece.joints), len(faces), is_watertight(vertices, faces)))
    finished.append(field.to_volume())
print("seams: {faces} faces, surfaces within {offset:.2f} mm, {disagreement:.2%} solid on one side only".format(
    **seams.summary()))

shape = Union(finished)

if __name__ == "__main__":
    demo(shape, "piece_by_piece", bounds=(-64, -34, -16, 64, 34, 16), resolution=(160, 85, 40))
