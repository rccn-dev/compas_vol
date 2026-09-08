"""The full pipeline, written out step by step.

This is the reference: every other example in this folder does exactly what
happens below, but hides the repeated parts in ``_common.py``. Copy this file
as a starting point when you want control over each stage.

    modelling  ->  sampling  ->  iso-surfacing  ->  viewing / export

Run with::

    uv run --extra examples python examples/vol_mesh_examples/template.py
"""

import os

import numpy as np
from compas.datastructures import Mesh
from compas.geometry import Box
from compas.geometry import Plane
from compas.geometry import Translation
from compas.geometry import Vector
from skimage.measure import marching_cubes

from compas_vol.combinations import Intersection
from compas_vol.microstructures import TPMS
from compas_vol.modifications import Overlay
from compas_vol.modifications import Shell
from compas_vol.primitives import VolBox
from compas_vol.primitives import VolPlane

# ==============================================================================
# 1. Modelling: build the CSG tree
# ==============================================================================

# COMPAS 2 puts the frame last and defaults it to worldXY, so a centred box is
# just its three sizes. In COMPAS 1 this read Box(Frame.worldXY(), 30, 30, 30).
vb = VolBox(Box(30, 30, 30), 0)

# A TPMS is a surface, not a solid. Shell() gives it a wall thickness.
shell = Shell(TPMS(tpmstype="FischerKoch", wavelength=18), 0.33)

# Adding a sloped plane field to the shell shifts the wall thickness across
# the part: thin at one corner, thick at the other.
graded = Overlay(shell, VolPlane(Plane((-15, -15, -15), (-1, -1, -1))), 0.005)

shape = Intersection(vb, graded)

# ==============================================================================
# 2. Sampling: evaluate the field on a regular grid
# ==============================================================================

LBX, UBX = -20.0, 20.0
LBY, UBY = -20.0, 20.0
LBZ, UBZ = -20.0, 20.0
NX, NY, NZ = 160, 160, 160

# ogrid gives three broadcastable arrays of shape (NX,1,1), (1,NY,1), (1,1,NZ).
x, y, z = np.ogrid[LBX : UBX : NX * 1j, LBY : UBY : NY * 1j, LBZ : UBZ : NZ * 1j]

# Spacing between samples. Note the (n - 1): there are n samples but n-1 gaps,
# and getting this wrong scales the mesh slightly.
GX = (UBX - LBX) / (NX - 1)
GY = (UBY - LBY) / (NY - 1)
GZ = (UBZ - LBZ) / (NZ - 1)

sdf = shape.get_distance_numpy(x, y, z)
print("sampled field:", type(sdf).__name__, sdf.shape)

# ==============================================================================
# 3. Iso-surfacing: extract the zero level set
# ==============================================================================

verts, faces, normals, values = marching_cubes(sdf, 0.0, spacing=(GX, GY, GZ))

# marching_cubes returns coordinates relative to the grid corner, so shift them
# back into world space. compas_vol.meshing.generate_mesh does this for you.
verts = verts + np.array([LBX, LBY, LBZ])

mesh = Mesh.from_vertices_and_faces(verts.tolist(), faces.tolist())
print("mesh:", mesh.number_of_vertices(), "vertices,", mesh.number_of_faces(), "faces")

# Optional: move the centroid to the origin, handy before sending to a printer.
mesh.transform(Translation.from_vector(-Vector(*mesh.centroid())))

# ==============================================================================
# 4. Export and view
# ==============================================================================

EXPORT = False

if __name__ == "__main__":
    if EXPORT:
        path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "template.stl")
        # COMPAS 2 takes a path here, not an open file object.
        mesh.to_stl(path, binary=True)
        print("wrote", path)

    from compas_viewer import Viewer

    viewer = Viewer()
    viewer.scene.add(mesh, show_points=False, show_lines=False)
    viewer.show()

    # Everything above could also have been written as:
    #
    #     from compas_vol.meshing import generate_mesh
    #     mesh = generate_mesh(shape, (LBX, LBY, LBZ, UBX, UBY, UBZ), (NX, NY, NZ))
    #
    # and the volumetric object can go straight into the scene without meshing
    # it yourself, because compas_vol registers a scene object for it:
    #
    #     viewer.scene.add(shape, bounds=20.0, resolution=160)

    from _common import show_field

    show_field(sdf, (LBX, LBY, LBZ, UBX, UBY, UBZ), title="template: graded FischerKoch")
