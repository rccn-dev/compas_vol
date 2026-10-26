# r: scikit-image>=0.24
"""
Sample a volumetric object over a box and build the surface as a Rhino mesh.

A distance field has no extent of its own, so bounds is required: it is the
window the model is cut to. resolution is samples per axis over that window,
and it sets the finest feature that can appear -- below about two voxels,
nothing survives.

Keep the resolution modest here. Handing the triangles to Rhino costs far
more than generating them, so this path is for design iteration; export the
final model headless with compas_vol.meshing.export_stl.

    Args:
        vol: The object to mesh.
        bounds: The box to sample over. Only its axis-aligned extent is used.
        resolution: Samples per axis. Defaults to 64.
        level: Iso-value. 0 is the surface; positive offsets outward.
    Returns:
        mesh: A Rhino mesh.
        seconds: How long it took, to calibrate the resolution.
"""
# Rhino 8 annotates RunScript with each input's type -- Rhino.Geometry.Box,
# System.Collections.Generic.List -- and evaluates the annotations when it
# defines the class, so both names must exist even though nothing here uses them.
import System  # noqa: F401
import Rhino  # noqa: F401
import time

from ghpythonlib.componentbase import executingcomponent as component


class CompasVolMesh(component):
    def RunScript(self, vol, bounds, resolution: int, level: float):
        from compas_vol import nodes
        from compas_vol.ghpython import box_to_bounds, mesh_to_rhino

        # Timed here rather than in the node: handing the triangles to Rhino
        # is most of the cost, and it is the cost this output is for.
        started = time.time()
        vertices, faces = nodes.mesh(vol, box_to_bounds(bounds), resolution, level)
        mesh = mesh_to_rhino(vertices, faces)
        return mesh, None if mesh is None else round(time.time() - started, 2)
