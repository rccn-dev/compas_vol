"""A 6 m canopy cut into pieces that fit a print bed and memory.

A closed mesh becomes a field; a gyroid is conformed to its skin; the result
is cut into pinned pieces; one piece is built and checked. The whole canopy at
1 mm is about 130 billion samples; one 400 mm piece is 64 million.

    uv run --extra examples python examples/25_pavilion_assembly.py
"""

import time

from compas.datastructures import Mesh
from compas.geometry import Box, Frame, Sphere

from compas_vol.assembly import Pins, segment
from compas_vol.combinations import Intersection
from compas_vol.fabrication import inspect
from compas_vol.microstructures import TPMSSolid
from compas_vol.modifications import Conform, Shell
from compas_vol.primitives import VolBox, VolGrid

# ==============================================================================
# Parameters -- everything in millimetres
# ==============================================================================

RADIUS = 3000.0        # the canopy's sphere
HEIGHT = 3200.0        # cut off above this
WALL = 240.0           # thickness of the shell the lattice lives in
CELL = 160.0           # gyroid cell
STRUT = 26.0           # gyroid wall

PIECE = 400.0          # what fits the bed
CLEARANCE = 0.4        # gap between neighbours
RESOLUTION = 160       # samples per axis, per piece


# ==============================================================================
# 1. A mesh becomes a field
# ==============================================================================

start = time.time()
mesh = Mesh.from_shape(Sphere(RADIUS), u=28, v=28)
skin = VolGrid.from_mesh(mesh, resolution=64)
print("mesh -> field : {} faces, {:.1f}s".format(mesh.number_of_faces(), time.time() - start))

# ==============================================================================
# 2. A lattice that follows the skin
# ==============================================================================

clip = VolBox(Box(2 * RADIUS + 400, 2 * RADIUS + 400, HEIGHT,
                  frame=Frame((0, 0, HEIGHT / 2), (1, 0, 0), (0, 1, 0))), 0.0)
dome = Intersection(skin, clip)

# Conform uses the dome's distance as Z, so the gyroid's layers follow the canopy.
lattice = Conform(TPMSSolid("Gyroid", cell_size=CELL, thickness=STRUT), dome, axis=2)
canopy = Intersection(Shell(dome, WALL), lattice)

# ==============================================================================
# 3. Cut it into pieces
# ==============================================================================

start = time.time()
assembly = segment(
    canopy,
    bounds=(-RADIUS - 200, -RADIUS - 200, -50, RADIUS + 200, RADIUS + 200, HEIGHT - 50),
    piece=PIECE,
    clearance=CLEARANCE,
    joint=Pins(diameter=10.0, depth=6.0, fit=0.15, spacing=120.0, limit=3),
)
print("segment       : {} in {:.1f}s".format(assembly, time.time() - start))
print("pins placed   : {}".format(sum(len(p.joints) for p in assembly) // 2))
print()

cost = assembly.cost(resolution=RESOLUTION)
print("at {:.1f} mm voxels".format(cost["voxel"]))
print("  one piece   : {:>15,} samples  {:>8.0f} MB".format(cost["per_piece"], cost["per_piece_bytes"] / 1e6))
print("  whole model : {:>15,} samples  {:>8.0f} GB".format(cost["whole_model"], cost["whole_model_bytes"] / 1e9))
print("  ratio       : {:,.0f}x".format(cost["whole_model"] / cost["per_piece"]))
print()

# ==============================================================================
# 4. Build and check one piece
# ==============================================================================

# The most connected piece.
busiest = max(assembly, key=lambda piece: len(piece.joints))
print("building {} : {:.0f} x {:.0f} x {:.0f} mm, {} joint(s)".format(
    busiest.name, *busiest.size, len(busiest.joints)))

start = time.time()
field = busiest.sample(RESOLUTION, redistanced=True)
print("  sampled {} in {:.1f}s, {:.1%} solid".format(field.shape, time.time() - start, (field.values < 0).mean()))

report = inspect(field.values, spacing=field.spacing, origin=field.origin, angle=45.0, min_wall=STRUT / 2)
print()
print(report)
print()

# A lattice piece is often several parts: struts held from outside the box come
# loose. keep_largest drops them; if it drops a tenth of the piece, move the cut.
if report.pieces > 1:
    from compas_vol.fabrication import keep_largest

    cleaned, dropped = keep_largest(field)
    print("keep_largest  : dropped {} fragment(s) holding {:.2%} of the material".format(
        dropped["pieces_removed"], dropped["material_removed"]))

# busiest.export_stl("piece.stl", resolution=RESOLUTION)   # about 40 MB
