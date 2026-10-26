"""From a process to a printable STL.

``Field.to_volume()`` turns a weathered rock into an object like any other: here
it gets a 2 mm skin and a graded gyroid interior, and is exported with the
checks a print needs.

    uv run --extra all python examples/24_process_to_print.py
"""

import os
import time

import numpy as np
from compas.geometry import Box
from compas.geometry import Plane

from compas_vol.combinations import Intersection
from compas_vol.combinations import Union
from compas_vol.meshing import export_stl
from compas_vol.meshing import generate_vertices_and_faces
from compas_vol.microstructures import TPMSSolid
from compas_vol.modifications import Remap
from compas_vol.modifications import Shell
from compas_vol.primitives import VolBox
from compas_vol.primitives import VolPlane
from compas_vol.processes import Field
from compas_vol.processes import abrasion
from compas_vol.processes import pitting
from compas_vol.processes import strata

from _common import demo

# ==============================================================================
# Parameters
# ==============================================================================

SIZE = 100.0  # mm
PROCESS_RESOLUTION = 150  # what the erosion runs at: sets the finest feature
EXPORT_RESOLUTION = 220  # what the STL is meshed at
BASE = -SIZE / 2 + 4  # flat base for printing, mm

SKIN = 2.0  # mm
CELL = 9.0  # mm gyroid cell inside
WALL_AT_SKIN = 1.6  # mm
WALL_AT_CORE = 0.6  # mm
DEPTH = 12.0  # mm over which the interior thins

EXPORT = False  # writing 200 MB of STL is opt-in

# ==============================================================================
# Model
# ==============================================================================


def rock():
    """A weathered mass, as a volumetric object."""
    from compas.geometry import Frame

    solid = VolBox(Box(86, 74, 72, frame=Frame((0, 0, -4), (1, 0.2, 0), (-0.2, 1, 0))), 26.0)
    field = Field.from_object(solid, bounds=SIZE / 2 + 5, resolution=PROCESS_RESOLUTION)
    field = strata(field, thickness=12.0, dip=(0.2, 0.06), depth=4.0, seed=2)
    field = pitting(field, depth=7.0, length=6.0, threshold=0.25, cell_size=24.0, seed=2)
    return abrasion(field, depth=1.5, steps=6, length=8.0)


weathered = rock()
mass = weathered.to_volume()

# Keep modelling: skin, graded interior, flat base.
skin = Shell(mass, SKIN, side=1.0)
wall = Remap(mass, source=(-DEPTH, 0.0), target=(WALL_AT_CORE, WALL_AT_SKIN), ease="smooth")
interior = Intersection(TPMSSolid("Gyroid", CELL, wall), mass)
shape = Intersection(Union(skin, interior), VolPlane(Plane((0, 0, BASE), (0, 0, -1))))

BOUNDS = (-SIZE / 2 - 5, -SIZE / 2 - 5, BASE - 5, SIZE / 2 + 5, SIZE / 2 + 5, SIZE / 2 + 5)


def checks():
    """The numbers to look at before printing."""
    vertices, faces = generate_vertices_and_faces(shape, BOUNDS, EXPORT_RESOLUTION)
    edges = np.sort(np.concatenate([faces[:, [0, 1]], faces[:, [1, 2]], faces[:, [2, 0]]]), axis=1)
    _, counts = np.unique(edges, axis=0, return_counts=True)
    size = vertices.max(axis=0) - vertices.min(axis=0)
    print("triangles      : {:,}".format(len(faces)))
    print("closed manifold: {}".format("yes" if (counts != 2).sum() == 0 else "NO"))
    print("bounding box   : {:.0f} x {:.0f} x {:.0f} mm".format(*size))
    return vertices, faces


if __name__ == "__main__":
    print(weathered.provenance(), "\n")
    start = time.perf_counter()
    checks()
    print("meshed in {:.0f}s".format(time.perf_counter() - start))

    if EXPORT:
        path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "process_to_print.stl")
        print("wrote", export_stl(shape, path, BOUNDS, EXPORT_RESOLUTION))

    demo(shape, "process_to_print", bounds=BOUNDS, resolution=EXPORT_RESOLUTION, axis="y")
